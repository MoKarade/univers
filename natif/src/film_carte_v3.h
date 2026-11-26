// Appli PC « Univers » : le film du Groupe local au FORMAT 3 (natif/physique/film_v3.h) relu SUR LA CARTE GRAPHIQUE, à la
// date exacte de chaque image affichée. Même partage que film_carte.h (format 2) : les images brutes vont sur la carte
// dans des cases, des fils à part lisent d'avance dans le sens du temps, et un petit calcul (shaders/film_etat_v3.comp)
// écrit l'état de chaque étoile dans le tampon que gaia.vert lit.
//
// Ce qui change avec le format 3 :
//   - une image P (tous les traceurs, toutes les 20 Ma) ne se lit que pour la tranche de ces galaxies ;
//   - les traceurs qui tournent vite ont des images à eux entre deux dates P (classes C, M, L : tous les 2, 4, 10 Ma). Pour
//     chaque classe, on ne lit que la tranche de ses traceurs qui sont des étoiles de ces galaxies (les fichiers des classes
//     sont rangés dans l'ordre du film) ;
//   - chaque traceur a ses deux images voisines (dates P, ou dates P et de sa classe) : Hermite sur ces deux images, avec
//     les vitesses écrites, comme FilmV3::etats. Les quatre familles (P seuls, C, M, L) ont chacune leur paire d'images.
// Une case par image et par famille : P, C, M et L ont leurs propres cases (tailles différentes).
#pragma once
#include <algorithm>
#include <array>
#include <climits>
#include <cmath>
#include <condition_variable>
#include <cstdio>
#include <deque>
#include <future>
#include <map>
#include <mutex>
#include <set>
#include <thread>
#include <vector>

#include "film_etoiles.h"
#include "gaia_orbites.h"

namespace {

class FilmGpuV3 {
public:
    using Film = phys::film::FilmV3;
    static constexpr int kFam = 4;                          // 0 : P seuls ; 1 : C ; 2 : M ; 3 : L
    static constexpr int kSlots[kFam] = {6, 8, 8, 6};      // cases par famille : 2 images voulues + celles lues d'avance
    static constexpr int kMaxAhead = 5;
    static constexpr double kAheadSeconds = 0.25;
    static constexpr int kWorkers = 2;
    bool ok = false;
    long uploads = 0;

    bool create(const Gpu& g, FilmStars& fs, GaiaOrbits& orb) {
        if (!fs.ready || !fs.v3 || orb.count != fs.ordre.size() + 1) return false;
        const Film& f = fs.film3;
        n_ = static_cast<uint32_t>(fs.ordre.size());
        base_ = fs.base();
        total_[0] = f.traceursP();
        lo_[0] = base_; hi_[0] = base_ + n_;
        const auto& cl = f.classes();
        const auto& rc = f.rangsDansClasse();
        const Film::Famille fam[kFam] = {Film::P, Film::C, Film::M, Film::L};
        for (int k = 1; k < kFam; ++k) {
            total_[k] = f.traceursClasse(fam[k]);
            uint64_t lo = UINT64_MAX, hi = 0;
            for (uint64_t i = base_; i < base_ + n_; ++i)
                if (cl[i] == fam[k]) { lo = std::min<uint64_t>(lo, rc[i]); hi = std::max<uint64_t>(hi, rc[i] + 1ull); }
            lo_[k] = hi ? lo : 0; hi_[k] = hi;
        }
        // Pour chaque étoile de l'appli : sa famille et son rang dans la tranche de sa classe.
        std::vector<uint32_t> info(n_);
        for (uint32_t s = 0; s < n_; ++s) {
            const uint64_t R = base_ + fs.ordre[s];
            int k = 0;
            for (int j = 1; j < kFam; ++j) if (cl[R] == fam[j]) k = j;
            const uint64_t idx = k ? rc[R] - lo_[k] : 0;
            if (idx >= (1u << 30)) return false;
            info[s] = static_cast<uint32_t>(k) << 30 | static_cast<uint32_t>(idx);
        }
        VkDeviceSize offK = 0, half = 0;
        for (int k = 0; k < kFam; ++k) {
            slotBytes_[k] = std::max<VkDeviceSize>(((hi_[k] - lo_[k]) * Film::kEnreg + 255) & ~VkDeviceSize(255), 256);
            if (k) { offK_[k] = offK; offK += slotBytes_[k] * kSlots[k]; }
            half += slotBytes_[k] * (k ? 2 : 1);
        }
        rawP_ = createBuffer(g, slotBytes_[0] * kSlots[0], VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        rawK_ = createBuffer(g, std::max<VkDeviceSize>(offK, 256), VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        ordre_ = uploadStorage(g, fs.ordre.data(), static_cast<VkDeviceSize>(n_) * 4);
        info_ = uploadStorage(g, info.data(), static_cast<VkDeviceSize>(n_) * 4);
        // Gain de lumière (revue F1) ; une valeur négative marque une étoile écartée (ignorer.bin) : lumière nulle.
        hasGain_ = fs.gain.size() == n_;
        std::vector<float> gain(n_, 1.0f);
        if (hasGain_) gain = fs.gain;
        if (fs.hidden.size() == n_)
            for (uint32_t s = 0; s < n_; ++s) if (fs.hidden[s]) gain[s] = -1.0f;
        gain_ = uploadStorage(g, gain.data(), static_cast<VkDeviceSize>(n_) * 4);
        // Zone d'envoi : deux jeux (la carte peut encore lire celui de l'image précédente), chacun assez grand pour une image P
        // et deux images de chaque classe ; au-delà, envoi immédiat avec attente (cas rare).
        stagingHalf_ = half;
        staging_ = createBuffer(g, stagingHalf_ * 2, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        check(vkMapMemory(g.dev, staging_.mem, 0, VK_WHOLE_SIZE, 0, &stagingMap_), "film v3 sur la carte");
        stateBuf_ = orb.state.buf;
        createPipeline(g, orb.state.buf);
        for (auto& sl : slot_) sl.fill(-1);
        for (auto& u : used_) u.fill(0);
        dossier_ = fs.dossier;
        for (std::thread& w : workers_) w = std::thread([this] { work(); });
        std::printf("film v3 sur la carte : %u etoiles (rangs %llu a %llu) ; classes C %llu, M %llu, L %llu ; cases %.0f Mo\n", n_,
                    static_cast<unsigned long long>(base_), static_cast<unsigned long long>(base_ + n_), static_cast<unsigned long long>(hi_[1] - lo_[1]),
                    static_cast<unsigned long long>(hi_[2] - lo_[2]), static_cast<unsigned long long>(hi_[3] - lo_[3]),
                    static_cast<double>(slotBytes_[0] * kSlots[0] + offK) / 1.0e6);
        ok = true;
        return true;
    }

    bool update(const Gpu& g, FilmStars& fs, GaiaOrbits& orb, double tGa, int dir, double gaPerSecond, phys::Vec3 sun, phys::Vec3 sunVel, double gaiaOff, long step) {
        if (!ok) return false;
        const Film& f = fs.film3;
        const Film::Famille fam[kFam] = {Film::P, Film::C, Film::M, Film::L};
        Film::Noeuds nd[kFam];
        bool has[kFam] = {};
        for (int k = 0; k < kFam; ++k) {
            if (hi_[k] <= lo_[k]) continue;
            if (!f.noeudsDe(fam[k], tGa, nd[k])) return false;
            has[k] = true;
        }
        if (!has[0]) return false;
        // Images voulues : pour chaque famille, ses deux nœuds (une date P se lit dans la case P).
        Key want[kFam][2];
        std::vector<Key> wanted;
        for (int k = 0; k < kFam; ++k) {
            if (!has[k]) continue;
            want[k][0] = keyOf(f, k, nd[k].a);
            want[k][1] = keyOf(f, k, nd[k].b);
            for (const Key& x : want[k])
                if (std::find(wanted.begin(), wanted.end(), x) == wanted.end()) wanted.push_back(x);
        }
        // Lecture d'avance : dans le sens du temps, les dates suivantes de chaque famille (autant qu'en parcourt un quart de
        // seconde, au moins une, au plus kMaxAhead) ; à l'arrêt, une de chaque côté pour P.
        ahead_.clear();
        for (int k = 0; k < kFam; ++k) {
            if (!has[k]) continue;
            const uint32_t bit = k == 0 ? 1u : k == 1 ? 2u : k == 2 ? 8u : 16u;
            const double span = std::max(f.date(nd[k].b) - f.date(nd[k].a), 1.0e-6);
            const int m = dir == 0 ? (k == 0 ? 1 : 0) : std::clamp(static_cast<int>(std::ceil(gaPerSecond * kAheadSeconds / span)), 1, std::min(kMaxAhead, kSlots[k] - 2));
            for (int sens : {+1, -1}) {
                if (dir != 0 && sens != dir) continue;
                int d = sens > 0 ? nd[k].b : nd[k].a, got = 0;
                for (int j = d + sens; j >= 0 && j < f.dates() && got < m; j += sens)
                    if (f.famillesA(j) & bit) { ahead_.push_back({k, j}); ++got; }
            }
        }
        requestAhead();
        ++clock_;
        // Images voulues absentes des cases : prises parmi celles lues d'avance, sinon lues tout de suite, en même temps.
        const size_t nw = wanted.size();
        std::vector<std::vector<uint8_t>> img(nw);
        std::vector<std::future<bool>> reading(nw);
        std::vector<char> missing(nw, 0);
        for (size_t j = 0; j < nw; ++j) {
            if (find(wanted[j]) >= 0) continue;
            missing[j] = 1;
            if (!take(wanted[j], img[j])) reading[j] = std::async(std::launch::async, [this, &wanted, &img, j] { return readSlice(wanted[j], img[j]); });
        }
        bool complete = true;
        for (size_t j = 0; j < nw; ++j)
            if (reading[j].valid() && !reading[j].get()) complete = false;
        if (!complete) return false;
        for (size_t j = 0; j < nw; ++j)
            if (missing[j] && place(g, wanted[j], img[j], wanted, false) < 0) return false;
        for (const Key& x : wanted) used_[static_cast<size_t>(x.k)][static_cast<size_t>(find(x))] = clock_;
        // Au plus deux images lues d'avance envoyées par image affichée, dans une case libre ou qui ne sert plus.
        for (int sent = 0; sent < 2; ++sent) {
            std::vector<uint8_t> pre;
            Key a{-1, -1};
            {
                std::lock_guard<std::mutex> l(m_);
                for (auto it = done_.begin(); it != done_.end();) {
                    const bool useful = isAhead(it->first) || std::find(wanted.begin(), wanted.end(), it->first) != wanted.end();
                    if (!useful) { it = done_.erase(it); continue; }
                    if (a.k < 0 && find(it->first) < 0) { a = it->first; pre = std::move(it->second); it = done_.erase(it); continue; }
                    ++it;
                }
            }
            if (a.k < 0 || place(g, a, pre, wanted, true) < 0) break;
        }
        Push p{};
        for (int k = 0; k < kFam; ++k) {
            if (!has[k]) continue;
            for (int e = 0; e < 2; ++e) {
                const Key& x = want[k][e];
                const uint32_t off = static_cast<uint32_t>(((x.k ? offK_[x.k] : 0) + static_cast<VkDeviceSize>(find(x)) * slotBytes_[x.k]) / 4);
                (e ? p.offB : p.offA)[k] = off;
                if (x.k == 0) p.flags |= 1u << (2 * k + e);
            }
            p.h[k] = static_cast<float>(nd[k].h);
            p.u[k] = static_cast<float>(nd[k].u);
        }
        p.sunP[0] = static_cast<float>(sun.x); p.sunP[1] = static_cast<float>(sun.y); p.sunP[2] = static_cast<float>(sun.z); p.sunP[3] = 1.0f;
        p.sunV[0] = static_cast<float>(sunVel.x); p.sunV[1] = static_cast<float>(sunVel.y); p.sunV[2] = static_cast<float>(sunVel.z);
        p.n = n_;
        p.gaiaOff = static_cast<float>(gaiaOff);
        p.hasGain = hasGain_ ? 1u : 0u;
        const bool same = lastValid_ && copies_.empty() && std::memcmp(&p, &push_, sizeof(Push)) == 0;
        push_ = p;
        hasDispatch_ = !same;
        ledThisFrame_ = true;
        orb.markExternalExact(step);
        return true;
    }

    // Comme FilmGpu::record : envois en attente, puis calcul des états, avec leurs barrières.
    void record(VkCommandBuffer cmd) {
        if (!ok) return;
        for (int b = 0; b < 2; ++b) {
            std::vector<VkBufferCopy>& c = b ? copiesK_ : copies_;
            if (c.empty()) continue;
            vkCmdCopyBuffer(cmd, staging_.buf, b ? rawK_.buf : rawP_.buf, static_cast<uint32_t>(c.size()), c.data());
            c.clear();
        }
        if (copied_) {
            VkMemoryBarrier mb{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
            mb.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
            mb.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
            vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0, 1, &mb, 0, nullptr, 0, nullptr);
            copied_ = false;
        }
        stagingUsed_ = 0;
        stagingSet_ = 1 - stagingSet_;
        lastValid_ = ledThisFrame_;
        ledThisFrame_ = false;
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
        destroy(g, rawP_);
        destroy(g, rawK_);
        destroy(g, ordre_);
        destroy(g, info_);
        destroy(g, gain_);
        vkDestroyPipeline(g.dev, pipe_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroyShaderModule(g.dev, cs_, nullptr);
        ok = false;
    }

private:
    struct Key {
        int k = -1, date = -1;      // famille de la case (0 : P) et date dans le film
        bool operator==(const Key& o) const { return k == o.k && date == o.date; }
        bool operator<(const Key& o) const { return k != o.k ? k < o.k : date < o.date; }
    };
    struct Push {
        uint32_t offA[4], offB[4];
        float h[4], u[4], sunP[4], sunV[4];
        uint32_t flags, n;
        float gaiaOff;
        uint32_t hasGain;
    };
    static_assert(sizeof(Push) == 112, "film_etat_v3.comp : constantes de 112 octets");

    uint32_t n_ = 0;
    uint64_t base_ = 0;
    std::array<uint64_t, kFam> lo_{}, hi_{}, total_{};      // tranche lue de chaque fichier (P : étoiles de ces galaxies)
    std::array<VkDeviceSize, kFam> slotBytes_{}, offK_{};
    VkDeviceSize stagingHalf_ = 0, stagingUsed_ = 0;
    int stagingSet_ = 0;
    bool hasGain_ = false, copied_ = false;
    Buffer rawP_{}, rawK_{}, ordre_{}, info_{}, gain_{}, staging_{};
    VkBuffer stateBuf_ = VK_NULL_HANDLE;
    Push push_{};
    bool hasDispatch_ = false, lastValid_ = false, ledThisFrame_ = false;
    std::vector<VkBufferCopy> copies_, copiesK_;
    void* stagingMap_ = nullptr;
    std::array<std::array<int, 8>, kFam> slot_{};      // date dans chaque case (-1 : vide)
    std::array<std::array<long, 8>, kFam> used_{};
    long clock_ = 0;
    std::vector<Key> ahead_;
    VkPipeline pipe_{};
    VkPipelineLayout layout_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet set_{};
    VkShaderModule cs_{};

    std::string dossier_;
    std::array<std::thread, kWorkers> workers_;
    std::mutex m_;
    std::condition_variable cv_;
    std::deque<Key> asked_;
    std::map<Key, std::vector<uint8_t>> done_;
    std::set<Key> reading_;
    bool stop_ = false;

    static Key keyOf(const Film& f, int k, int date) { return f.estDateP(date) ? Key{0, date} : Key{k, date}; }
    int find(const Key& x) const {
        for (int s = 0; s < kSlots[x.k]; ++s)
            if (slot_[static_cast<size_t>(x.k)][static_cast<size_t>(s)] == x.date) return s;
        return -1;
    }
    bool isAhead(const Key& x) const { return std::find(ahead_.begin(), ahead_.end(), x) != ahead_.end(); }
    void requestAhead() {
        bool added = false;
        {
            std::lock_guard<std::mutex> l(m_);
            asked_.erase(std::remove_if(asked_.begin(), asked_.end(), [this](const Key& a) { return !isAhead(a); }), asked_.end());
            for (const Key& a : ahead_) {
                if (find(a) >= 0 || done_.count(a) || reading_.count(a) || std::find(asked_.begin(), asked_.end(), a) != asked_.end()) continue;
                asked_.push_back(a);
                added = true;
            }
        }
        if (added) cv_.notify_all();
    }
    bool take(const Key& x, std::vector<uint8_t>& out) {
        std::lock_guard<std::mutex> l(m_);
        auto it = done_.find(x);
        if (it == done_.end()) return false;
        out = std::move(it->second);
        done_.erase(it);
        return true;
    }
    // Tranche utile du fichier de l'image (P : ces galaxies ; classe : ses traceurs de ces galaxies). Fichier de taille
    // inattendue (en cours d'écriture, tronqué) : rien n'est lu.
    bool readSlice(const Key& x, std::vector<uint8_t>& out) const {
        static const char lettre[kFam] = {'p', 'c', 'm', 'l'};
        const size_t k = static_cast<size_t>(x.k);
        return Film::lireTranche(dossier_, lettre[k], x.date, lo_[k], hi_[k] - lo_[k], total_[k], out);
    }
    void work() {
        for (;;) {
            Key x;
            {
                std::unique_lock<std::mutex> l(m_);
                cv_.wait(l, [this] { return stop_ || !asked_.empty(); });
                if (stop_) return;
                x = asked_.front();
                asked_.pop_front();
                reading_.insert(x);
            }
            std::vector<uint8_t> img;
            const bool good = readSlice(x, img);
            std::lock_guard<std::mutex> l(m_);
            reading_.erase(x);
            if (!good) continue;
            done_[x] = std::move(img);
            while (done_.size() > 3u * kMaxAhead + 4u) {      // on garde la plus récente ; on jette une image qui ne sert plus
                auto loin = done_.begin();
                for (auto it = done_.begin(); it != done_.end(); ++it)
                    if (!isAhead(it->first)) { loin = it; break; }
                done_.erase(loin);
            }
        }
    }
    // Case pour l'image x de sa famille : une case vide ; sinon une image qui ne sert plus (ni voulue ni lue d'avance), la
    // moins récemment utilisée ; sinon (image voulue seulement) une image lue d'avance, la moins récente. Rend -1 sinon.
    int place(const Gpu& g, const Key& x, const std::vector<uint8_t>& img, const std::vector<Key>& wanted, bool forAhead) {
        const size_t k = static_cast<size_t>(x.k);
        int best = -1;
        long bestKey = 0;
        for (int s = 0; s < kSlots[k]; ++s) {
            const int h = slot_[k][static_cast<size_t>(s)];
            const Key hk{x.k, h};
            if (h >= 0 && std::find(wanted.begin(), wanted.end(), hk) != wanted.end()) continue;
            const bool aheadImage = h >= 0 && isAhead(hk);
            if (forAhead && aheadImage) continue;
            const long key = h < 0 ? LONG_MIN : !aheadImage ? LONG_MIN / 2 + used_[k][static_cast<size_t>(s)] : used_[k][static_cast<size_t>(s)];
            if (best < 0 || key < bestKey) { best = s; bestKey = key; }
        }
        if (best < 0) return -1;
        const VkDeviceSize bytes = (img.size() + 3) & ~VkDeviceSize(3);
        const VkDeviceSize dst = (k ? offK_[k] : 0) + static_cast<VkDeviceSize>(best) * slotBytes_[k];
        std::vector<VkBufferCopy>& copies = k ? copiesK_ : copies_;
        if (stagingUsed_ + bytes <= stagingHalf_) {
            const VkDeviceSize off = static_cast<VkDeviceSize>(stagingSet_) * stagingHalf_ + stagingUsed_;
            std::memcpy(static_cast<char*>(stagingMap_) + off, img.data(), img.size());
            copies.push_back({off, dst, bytes});
            stagingUsed_ += (bytes + 255) & ~VkDeviceSize(255);
            copied_ = true;
        } else {
            // Zone d'envoi pleine pour cette image : envois en attente faits tout de suite, puis celui-ci, avec attente.
            vkQueueWaitIdle(g.queue);
            flushNow(g);
            const VkDeviceSize off = static_cast<VkDeviceSize>(stagingSet_) * stagingHalf_;
            std::memcpy(static_cast<char*>(stagingMap_) + off, img.data(), img.size());
            VkCommandBuffer c = beginOnce(g);
            const VkBufferCopy region{off, dst, bytes};
            vkCmdCopyBuffer(c, staging_.buf, k ? rawK_.buf : rawP_.buf, 1, &region);
            endOnce(g, c);
        }
        slot_[k][static_cast<size_t>(best)] = x.date;
        used_[k][static_cast<size_t>(best)] = clock_;
        ++uploads;
        return best;
    }
    void flushNow(const Gpu& g) {
        if (copies_.empty() && copiesK_.empty()) return;
        VkCommandBuffer c = beginOnce(g);
        if (!copies_.empty()) vkCmdCopyBuffer(c, staging_.buf, rawP_.buf, static_cast<uint32_t>(copies_.size()), copies_.data());
        if (!copiesK_.empty()) vkCmdCopyBuffer(c, staging_.buf, rawK_.buf, static_cast<uint32_t>(copiesK_.size()), copiesK_.data());
        endOnce(g, c);
        copies_.clear();
        copiesK_.clear();
        stagingUsed_ = 0;
    }
    static Buffer uploadStorage(const Gpu& g, const void* data, VkDeviceSize size) {
        Buffer staging = createBuffer(g, size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, size, 0, &p), "film v3 sur la carte");
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
        constexpr uint32_t kB = 6;
        VkDescriptorSetLayoutBinding binds[kB];
        for (uint32_t i = 0; i < kB; ++i) binds[i] = {i, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = kB;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement du film v3");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, kB};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 1;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve du film v3");
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = 1;
        da.pSetLayouts = &setLayout_;
        check(vkAllocateDescriptorSets(g.dev, &da, &set_), "jeu du film v3");
        const VkDescriptorBufferInfo info[kB] = {{rawP_.buf, 0, VK_WHOLE_SIZE}, {rawK_.buf, 0, VK_WHOLE_SIZE}, {ordre_.buf, 0, VK_WHOLE_SIZE},
                                                 {info_.buf, 0, VK_WHOLE_SIZE}, {gain_.buf, 0, VK_WHOLE_SIZE}, {states, 0, VK_WHOLE_SIZE}};
        VkWriteDescriptorSet w[kB];
        for (uint32_t i = 0; i < kB; ++i) {
            w[i] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
            w[i].dstSet = set_;
            w[i].dstBinding = i;
            w[i].descriptorCount = 1;
            w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            w[i].pBufferInfo = &info[i];
        }
        vkUpdateDescriptorSets(g.dev, kB, w, 0, nullptr);
        cs_ = shader(g, "film_etat_v3.comp.spv");
        const VkPushConstantRange pcr{VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(Push)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement du calcul du film v3");
        VkComputePipelineCreateInfo cp{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
        cp.stage = {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO};
        cp.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        cp.stage.module = cs_;
        cp.stage.pName = "main";
        cp.layout = layout_;
        check(vkCreateComputePipelines(g.dev, VK_NULL_HANDLE, 1, &cp, nullptr, &pipe_), "calcul du film v3");
    }
};

}  // namespace
