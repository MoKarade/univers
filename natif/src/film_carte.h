// Appli PC « Univers » : le film du Groupe local relu SUR LA CARTE GRAPHIQUE, à la date exacte de chaque image affichée.
//
// Avant (film_etoiles.h, FilmStars::states) : à chaque pas d'un million d'années, le processeur interpolait les ~4 M
// d'étoiles une à une et renvoyait ~128 Mo à la carte. À 200 Ma/s, c'était 200 fois par seconde : l'appli tombait à ~2
// images/s et la date était bridée sur ce travail. Entre deux pas, l'état était prolongé par gaia.vert : l'image dépendait
// donc du pas, pas seulement de la date.
//
// Maintenant :
//   - les images BRUTES du film (nombres sur 16 bits, telles qu'écrites sur le disque) sont envoyées à la carte une seule
//     fois chacune, dans des cases (kSlots) ; un fil à part lit d'avance les images suivantes dans le sens du temps
//     (« deux images en vol », revue P2) ;
//   - à chaque image affichée, un petit calcul sur la carte (shaders/film_etat.comp) écrit l'état de chaque étoile à la
//     date EXACTE (même courbe qu'avant : Catmull-Rom sur les quatre images voisines, vitesse = sa pente), directement dans
//     le tampon d'états que gaia.vert lit, sans prolongement (fraction 0).
// Résultat : l'état montré ne dépend que de la date, jamais de la vitesse du temps ni du chemin pris pour y arriver.
//
// Format v3 (traceurs à identifiant stable, positions entières à 0,01 pc, vitesses entières à 0,05 km/s, courbe de
// Hermite sur deux images) : seul le décodage d'une image change. Le partage reste le même (cases d'images brutes sur la
// carte, un calcul par image affichée qui écrit l'état à la date exacte) : il faudra une variante de film_etat.comp et
// la taille d'une image dans brutMots().
#pragma once
#include <array>
#include <climits>
#include <cstdio>
#include <condition_variable>
#include <deque>
#include <future>
#include <cmath>
#include <map>
#include <set>
#include <mutex>
#include <thread>

#include "film_etoiles.h"
#include "gaia_orbites.h"

namespace {

class FilmGpu {
public:
    // Lecture d'avance selon la vitesse du temps : environ un quart de seconde de film (à 200 Ma/s, 5 images de 10 Ma), au
    // moins 2, au plus kMaxAhead. Chaque case pèse la part de ces étoiles dans une image (Voie lactée ~24 Mo).
    static constexpr int kMaxAhead = 8;
    static constexpr int kSlots = 4 + kMaxAhead;      // 4 images voisines de la date + celles lues d'avance
    static constexpr double kAheadSeconds = 0.25;
    static constexpr int kWorkers = 2;               // fils de lecture par film (le disque suit mieux à plusieurs)
    // Envois d'images par image affichée sans attente : 4 voulues + 2 lues d'avance ; deux jeux, car la carte peut encore lire
    // ceux de l'image précédente quand on prépare la suivante (une image en vol : barrière attendue avant chaque image).
    static constexpr int kUploadsPerFrame = 6;
    static constexpr int kStagingSets = 2;
    bool ok = false;
    long uploads = 0;                     // images envoyées à la carte depuis le départ (contrôle)

    // fs : film déjà chargé (ordre, gain) ; orb : états que gaia.vert lit (étoiles puis le Soleil en dernier).
    bool create(const Gpu& g, FilmStars& fs, GaiaOrbits& orb) {
        if (!fs.ready || orb.count != fs.ordre.size() + 1) return false;
        n_ = static_cast<uint32_t>(fs.ordre.size());
        base_ = fs.base();
        total_ = fs.film.total();
        slotWords_ = (static_cast<VkDeviceSize>(n_) * 3 + 1) / 2;
        slotBytes_ = (slotWords_ * 4 + 255) & ~VkDeviceSize(255);
        raw_ = createBuffer(g, slotBytes_ * kSlots, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        ordre_ = uploadStorage(g, fs.ordre.data(), static_cast<VkDeviceSize>(n_) * 4);
        hasGain_ = fs.gain.size() == n_;
        const float one = 1.0f;
        gain_ = hasGain_ ? uploadStorage(g, fs.gain.data(), static_cast<VkDeviceSize>(n_) * 4) : uploadStorage(g, &one, 4);
        staging_ = createBuffer(g, slotBytes_ * kUploadsPerFrame * kStagingSets, VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                                VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        stateBuf_ = orb.state.buf;
        check(vkMapMemory(g.dev, staging_.mem, 0, VK_WHOLE_SIZE, 0, &stagingMap_), "film sur la carte");
        createPipeline(g, orb.state.buf);
        slot_.fill(-1);
        used_.fill(0);
        dossier_ = fs.dossier;
        for (std::thread& w : workers_) w = std::thread([this] { work(); });
        ok = true;
        return true;
    }

    // Écrit sur la carte l'état de chaque étoile à tGa (Ga depuis aujourd'hui, dans le film) ; dir : sens du temps (+1, -1,
    // 0 à l'arrêt) et gaPerSecond (vitesse du temps, Ga par seconde) pour lire d'avance. sun, sunVel : Soleil selon l'appli (kpc, km/s), écrit en dernier comme avant.
    // gaiaOff : comme FilmStars::gaiaOff. Rend false si une image manque : l'état d'avant reste alors.
    bool update(const Gpu& g, FilmStars& fs, GaiaOrbits& orb, double tGa, int dir, double gaPerSecond, phys::Vec3 sun, phys::Vec3 sunVel, double gaiaOff, long step) {
        if (!ok) return false;
        const phys::film::FilmV2& f = fs.film;
        const int n = f.images();
        int i = 0;
        while (i + 2 < n && f.date(i + 1) <= tGa) ++i;      // image juste avant la date (comme FilmStars::states)
        const double span = f.date(i + 1) - f.date(i), u = std::clamp((tGa - f.date(i)) / span, 0.0, 1.0);
        const int want[4] = {std::max(i - 1, 0), i, i + 1, std::min(i + 2, n - 1)};
        // Lecture d'avance (les fils à part) : dans le sens du temps, autant d'images qu'en parcourt un quart de seconde ; à
        // l'arrêt, une de chaque côté. Jamais plus que les cases libres (sinon elles se chassent l'une l'autre et sont
        // renvoyées à la carte à chaque image affichée).
        aheadCount_ = 0;
        if (dir == 0) {
            ahead_[static_cast<size_t>(aheadCount_++)] = std::min(i + 3, n - 1);
            ahead_[static_cast<size_t>(aheadCount_++)] = std::max(i - 2, 0);
        } else {
            const int m = std::clamp(static_cast<int>(std::ceil(gaPerSecond * kAheadSeconds / span)), 2, kMaxAhead);
            for (int a = 0; a < m; ++a) ahead_[static_cast<size_t>(aheadCount_++)] = dir > 0 ? std::min(i + 3 + a, n - 1) : std::max(i - 2 - a, 0);
        }
        requestAhead();
        ++clock_;
        // Images voulues absentes des cases : prises parmi celles lues d'avance, sinon lues tout de suite, toutes en même temps
        // (à basse cadence, la date saute plusieurs images d'un coup : quatre lectures à la suite doublaient la durée d'une image).
        std::vector<uint16_t> img[4];
        std::future<bool> reading[4];
        bool missing[4] = {};
        for (int j = 0; j < 4; ++j) {
            if (find(want[j]) >= 0 || std::find(want, want + j, want[j]) != want + j) continue;
            missing[j] = true;
            if (!take(want[j], img[j])) reading[j] = std::async(std::launch::async, [this, &want, &img, j] { return loadNow(want[j], img[j]); });
        }
        bool complete = true;
        for (int j = 0; j < 4; ++j)
            if (reading[j].valid() && !reading[j].get()) complete = false;
        if (!complete) return false;
        int slotOf[4];
        for (int j = 0; j < 4; ++j)
            if (missing[j]) place(g, want[j], img[j], want, false);
        for (int j = 0; j < 4; ++j) {
            slotOf[j] = find(want[j]);
            used_[static_cast<size_t>(slotOf[j])] = clock_;
        }
        // Au plus deux images lues d'avance envoyées par image affichée, dans une case libre ou qui ne sert plus : elles seront
        // prêtes quand la date les atteindra. Les images lues pour une date déjà quittée sont jetées.
        for (int sent = 0; sent < 2; ++sent) {
            std::vector<uint16_t> pre;
            int ahead = -1;
            {
                std::lock_guard<std::mutex> l(m_);
                for (auto it = done_.begin(); it != done_.end();) {
                    const bool useful = isAhead(it->first) || std::find(want, want + 4, it->first) != want + 4;
                    if (!useful) { it = done_.erase(it); continue; }
                    if (ahead < 0 && find(it->first) < 0) { ahead = it->first; pre = std::move(it->second); it = done_.erase(it); continue; }
                    ++it;
                }
            }
            if (ahead < 0 || place(g, ahead, pre, want, true) < 0) break;
        }
        const double u2 = u * u, u3 = u2 * u, k = phys::film::FilmV2::kKpcGaEnKms / span;      // Catmull-Rom et sa pente (kpc/Ga -> km/s)
        Push p{};
        for (int j = 0; j < 4; ++j) p.slot[j] = static_cast<uint32_t>(slotOf[j] * (slotBytes_ / 4));
        p.w[0] = static_cast<float>(0.5 * (-u + 2 * u2 - u3));
        p.w[1] = static_cast<float>(0.5 * (2 - 5 * u2 + 3 * u3));
        p.w[2] = static_cast<float>(0.5 * (u + 4 * u2 - 3 * u3));
        p.w[3] = static_cast<float>(0.5 * (-u2 + u3));
        p.d[0] = static_cast<float>(0.5 * (-1 + 4 * u - 3 * u2) * k);
        p.d[1] = static_cast<float>(0.5 * (-10 * u + 9 * u2) * k);
        p.d[2] = static_cast<float>(0.5 * (1 + 8 * u - 9 * u2) * k);
        p.d[3] = static_cast<float>(0.5 * (-2 * u + 3 * u2) * k);
        p.sunP[0] = static_cast<float>(sun.x); p.sunP[1] = static_cast<float>(sun.y); p.sunP[2] = static_cast<float>(sun.z); p.sunP[3] = 1.0f;
        p.sunV[0] = static_cast<float>(sunVel.x); p.sunV[1] = static_cast<float>(sunVel.y); p.sunV[2] = static_cast<float>(sunVel.z);
        p.n = n_;
        p.gaiaOff = static_cast<float>(gaiaOff);
        p.hasGain = hasGain_ ? 1u : 0u;
        // Le calcul est enregistré dans les commandes de l'image (record), avant le dessin qui lit ces états : aucune attente
        // de la carte ici. L'état écrit est celui de la date de CETTE image.
        push_ = p;
        hasDispatch_ = true;
        orb.markExternalExact(step);
        return true;
    }

    // À appeler au début des commandes de l'image, hors de toute passe de dessin : envois des images du film en attente
    // (zone d'envoi -> cases), puis calcul des états à la date de l'image, avec les barrières envoi -> calcul -> sommets.
    void record(VkCommandBuffer cmd) {
        if (!ok) return;
        if (!copies_.empty()) {
            vkCmdCopyBuffer(cmd, staging_.buf, raw_.buf, static_cast<uint32_t>(copies_.size()), copies_.data());
            VkBufferMemoryBarrier b{VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER};
            b.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
            b.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
            b.srcQueueFamilyIndex = b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            b.buffer = raw_.buf;
            b.size = VK_WHOLE_SIZE;
            vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0, 0, nullptr, 1, &b, 0, nullptr);
            copies_.clear();
        }
        stagingUsed_ = 0;
        stagingSet_ = 1 - stagingSet_;      // l'image suivante écrit dans l'autre jeu (celui-ci peut encore être lu par la carte)
        if (!hasDispatch_) return;
        hasDispatch_ = false;
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe_);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, layout_, 0, 1, &set_, 0, nullptr);
        vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(push_), &push_);
        vkCmdDispatch(cmd, (n_ + 1 + 255) / 256, 1, 1);
        VkBufferMemoryBarrier b{VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER};
        b.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
        b.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
        b.srcQueueFamilyIndex = b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        b.buffer = stateBuf_;
        b.size = VK_WHOLE_SIZE;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_VERTEX_SHADER_BIT, 0, 0, nullptr, 1, &b, 0, nullptr);
    }

    // Le film s'est allongé (FilmStars::reload) : les images gardées restent justes (mêmes fichiers), rien à faire ici.

    void release(const Gpu& g) {
        if (!ok) return;
        {
            std::lock_guard<std::mutex> l(m_);
            stop_ = true;
        }
        cv_.notify_all();
        for (std::thread& w : workers_)
            if (w.joinable()) w.join();
        vkUnmapMemory(g.dev, staging_.mem);
        destroy(g, staging_);
        destroy(g, raw_);
        destroy(g, ordre_);
        destroy(g, gain_);
        vkDestroyPipeline(g.dev, pipe_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroyShaderModule(g.dev, cs_, nullptr);
        ok = false;
    }

private:
    struct Push {
        uint32_t slot[4];
        float w[4], d[4], sunP[4], sunV[4];
        uint32_t n;
        float gaiaOff;
        uint32_t hasGain, pad;
    };
    uint32_t n_ = 0;
    uint64_t base_ = 0, total_ = 0;      // première étoile de ces galaxies dans le film ; étoiles de tout le film
    std::array<int, kMaxAhead> ahead_{};      // images lues d'avance pour la date actuelle (update, place)
    int aheadCount_ = 0;
    VkDeviceSize slotWords_ = 0, slotBytes_ = 0;
    bool hasGain_ = false;
    Buffer raw_{}, ordre_{}, gain_{}, staging_{};
    VkBuffer stateBuf_ = VK_NULL_HANDLE;      // états lus par gaia.vert (écrits par le calcul du film)
    Push push_{};
    bool hasDispatch_ = false;
    std::vector<VkBufferCopy> copies_;        // envois en attente pour les commandes de la prochaine image
    int stagingSet_ = 0, stagingUsed_ = 0;
    void* stagingMap_ = nullptr;
    std::array<int, kSlots> slot_{};
    std::array<long, kSlots> used_{};
    long clock_ = 0;
    VkPipeline pipe_{};
    VkPipelineLayout layout_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet set_{};
    VkShaderModule cs_{};

    // Fil de lecture d'avance : il lit lui-même la part utile des fichiers d'images (readSlice), sans le cache de FilmV2.
    std::string dossier_;
    std::array<std::thread, kWorkers> workers_;
    std::mutex m_;
    std::condition_variable cv_;
    std::deque<int> asked_;
    std::map<int, std::vector<uint16_t>> done_;
    std::set<int> reading_;      // images en cours de lecture par un fil (pas de double demande)
    bool stop_ = false;

    int find(int image) const {
        for (int s = 0; s < kSlots; ++s)
            if (slot_[static_cast<size_t>(s)] == image) return s;
        return -1;
    }
    bool isAhead(int image) const { return std::find(ahead_.begin(), ahead_.begin() + aheadCount_, image) != ahead_.begin() + aheadCount_; }
    // Demandes aux fils de lecture : les images lues d'avance pas encore là, la plus proche d'abord ; les demandes d'une date
    // déjà quittée sont retirées.
    void requestAhead() {
        bool added = false;
        {
            std::lock_guard<std::mutex> l(m_);
            asked_.erase(std::remove_if(asked_.begin(), asked_.end(), [this](int a) { return !isAhead(a); }), asked_.end());
            for (int a = 0; a < aheadCount_; ++a) {
                const int image = ahead_[static_cast<size_t>(a)];
                if (find(image) >= 0 || done_.count(image) || reading_.count(image) || std::find(asked_.begin(), asked_.end(), image) != asked_.end()) continue;
                asked_.push_back(image);
                added = true;
            }
        }
        if (added) cv_.notify_all();
    }
    bool take(int image, std::vector<uint16_t>& out) {
        std::lock_guard<std::mutex> l(m_);
        auto it = done_.find(image);
        if (it == done_.end()) return false;
        out = std::move(it->second);
        done_.erase(it);
        return true;
    }
    // Lit sur le disque SEULEMENT la part de l'image qui concerne ces étoiles (galaxies firstGalaxy..., dans l'ordre du film),
    // droit dans out. Avant : l'image entière (51 Mo, toutes les galaxies) était lue puis copiée deux fois, ~51 ms par image,
    // et chaque film (Voie lactée, voisines) relisait tout : à 200 Ma/s, la lecture seule faisait tomber l'appli à 2 images/s.
    // Fichier de taille inattendue (en cours d'écriture, tronqué) : rien n'est lu.
    bool readSlice(int image, std::vector<uint16_t>& out) const {
        char nom[32];
        std::snprintf(nom, sizeof(nom), "/img_%05d.f16", image);
        FILE* f = std::fopen((dossier_ + nom).c_str(), "rb");
        if (!f) return false;
        std::fseek(f, 0, SEEK_END);
        bool good = film_ftell64(f) == static_cast<long long>(total_ * 6) && std::fseek(f, static_cast<long>(base_ * 6), SEEK_SET) == 0;
        if (good) {
            out.resize(static_cast<size_t>(n_) * 3);
            good = std::fread(out.data(), 6, n_, f) == n_;
        }
        std::fclose(f);
        return good;
    }
    bool loadNow(int image, std::vector<uint16_t>& out) const { return readSlice(image, out); }
    void work() {
        for (;;) {
            int image;
            {
                std::unique_lock<std::mutex> l(m_);
                cv_.wait(l, [this] { return stop_ || !asked_.empty(); });
                if (stop_) return;
                image = asked_.front();
                asked_.pop_front();
                reading_.insert(image);
            }
            std::vector<uint16_t> img;
            const bool good = readSlice(image, img);
            std::lock_guard<std::mutex> l(m_);
            reading_.erase(image);
            if (!good) continue;
            done_[image] = std::move(img);
            while (done_.size() > static_cast<size_t>(kMaxAhead) + 4) {      // on garde la plus récente ; on jette la plus éloignée d'elle
                auto loin = done_.begin();
                for (auto it = done_.begin(); it != done_.end(); ++it)
                    if (std::abs(it->first - image) > std::abs(loin->first - image)) loin = it;
                done_.erase(loin);
            }
        }
    }
    // Envoie l'image dans une case qui ne sert pas aux quatre images voulues. Ordre de choix : une case vide ; sinon une image
    // qui ne sert plus (ni voulue ni lue d'avance), la plus loin des voulues ; sinon (image voulue seulement) une image lue
    // d'avance, la moins récemment utilisée. Une image lue d'avance ne chasse jamais une autre image utile : rend -1, rien
    // n'est envoyé. Avant, une image lue d'avance était souvent la première jetée, puis relue et renvoyée.
    int place(const Gpu& g, int image, const std::vector<uint16_t>& img, const int want[4], bool forAhead) {
        int best = -1;
        long bestKey = 0;
        for (int s = 0; s < kSlots; ++s) {
            const int h = slot_[static_cast<size_t>(s)];
            if (h >= 0 && std::find(want, want + 4, h) != want + 4) continue;
            const bool aheadImage = h >= 0 && isAhead(h);
            if (forAhead && aheadImage) continue;
            long key;
            if (h < 0) key = LONG_MIN;
            else if (!aheadImage) key = LONG_MIN / 2 - std::min(std::abs(h - want[0]), std::abs(h - want[3]));
            else key = used_[static_cast<size_t>(s)];
            if (best < 0 || key < bestKey) { best = s; bestKey = key; }
        }
        if (best < 0) return -1;
        const VkDeviceSize bytes = (img.size() * 2 + 3) & ~size_t(3);
        if (stagingUsed_ < kUploadsPerFrame) {
            // Envoi sans attente : copie dans la zone d'envoi de cette image, faite par la carte au début de ses commandes (record).
            const VkDeviceSize off = (static_cast<VkDeviceSize>(stagingSet_) * kUploadsPerFrame + static_cast<VkDeviceSize>(stagingUsed_)) * slotBytes_;
            std::memcpy(static_cast<char*>(stagingMap_) + off, img.data(), img.size() * 2);
            copies_.push_back({off, static_cast<VkDeviceSize>(best) * slotBytes_, bytes});
            ++stagingUsed_;
        } else {
            // Zone d'envoi pleine pour cette image (cas rare) : envoi immédiat, avec attente. Il passe par la dernière case du
            // jeu en cours : aucune copie en attente ne la lit encore, car elle est envoyée tout de suite.
            vkQueueWaitIdle(g.queue);      // la case visée peut encore être lue par l'image précédente
            const VkDeviceSize off = (static_cast<VkDeviceSize>(stagingSet_) * kUploadsPerFrame + kUploadsPerFrame - 1) * slotBytes_;
            flushNow(g);
            std::memcpy(static_cast<char*>(stagingMap_) + off, img.data(), img.size() * 2);
            VkCommandBuffer c = beginOnce(g);
            const VkBufferCopy region{off, static_cast<VkDeviceSize>(best) * slotBytes_, bytes};
            vkCmdCopyBuffer(c, staging_.buf, raw_.buf, 1, &region);
            endOnce(g, c);
        }
        slot_[static_cast<size_t>(best)] = image;
        used_[static_cast<size_t>(best)] = clock_;
        ++uploads;
        return best;
    }
    // Copies en attente envoyées tout de suite (zone d'envoi pleine) : la carte les fait avant de rendre la main.
    void flushNow(const Gpu& g) {
        if (copies_.empty()) return;
        VkCommandBuffer c = beginOnce(g);
        vkCmdCopyBuffer(c, staging_.buf, raw_.buf, static_cast<uint32_t>(copies_.size()), copies_.data());
        endOnce(g, c);
        copies_.clear();
        stagingUsed_ = 0;
    }
    static Buffer uploadStorage(const Gpu& g, const void* data, VkDeviceSize size) {
        Buffer staging = createBuffer(g, size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, size, 0, &p), "film sur la carte");
        std::memcpy(p, data, size);
        vkUnmapMemory(g.dev, staging.mem);
        Buffer dst = createBuffer(g, size, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        VkCommandBuffer c = beginOnce(g);
        const VkBufferCopy region{0, 0, size};
        vkCmdCopyBuffer(c, staging.buf, dst.buf, 1, &region);
        endOnce(g, c);
        destroy(g, staging);
        return dst;
    }
    void createPipeline(const Gpu& g, VkBuffer states) {
        VkDescriptorSetLayoutBinding binds[4];
        for (uint32_t i = 0; i < 4; ++i) binds[i] = {i, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 4;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement du film");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 4};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 1;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve du film");
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = 1;
        da.pSetLayouts = &setLayout_;
        check(vkAllocateDescriptorSets(g.dev, &da, &set_), "jeu du film");
        const VkDescriptorBufferInfo info[4] = {{raw_.buf, 0, VK_WHOLE_SIZE}, {ordre_.buf, 0, VK_WHOLE_SIZE}, {gain_.buf, 0, VK_WHOLE_SIZE}, {states, 0, VK_WHOLE_SIZE}};
        VkWriteDescriptorSet w[4];
        for (uint32_t i = 0; i < 4; ++i) {
            w[i] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
            w[i].dstSet = set_;
            w[i].dstBinding = i;
            w[i].descriptorCount = 1;
            w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            w[i].pBufferInfo = &info[i];
        }
        vkUpdateDescriptorSets(g.dev, 4, w, 0, nullptr);
        cs_ = shader(g, "film_etat.comp.spv");
        const VkPushConstantRange pcr{VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(Push)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement du calcul du film");
        VkComputePipelineCreateInfo cp{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
        cp.stage = {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO};
        cp.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        cp.stage.module = cs_;
        cp.stage.pName = "main";
        cp.layout = layout_;
        check(vkCreateComputePipelines(g.dev, VK_NULL_HANDLE, 1, &cp, nullptr, &pipe_), "calcul du film");
    }
};

}  // namespace
