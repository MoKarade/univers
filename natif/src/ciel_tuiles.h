// Appli PC « Univers » : tuiles fines des cartes du ciel, lues en flux depuis le disque (ciel_bandes.h).
//
// Une carte entière tient sur la carte graphique jusqu'à Nside 4096 (pixel de 51″). Les relevés plus fins (WISE, GALEX,
// eROSITA : pixel de 6,4″ à l'ordre HiPS 6) font des centaines de Go : on ne charge que les tuiles qui sont à l'écran,
// au niveau de finesse qu'un pixel de l'écran peut montrer. Le reste du ciel reste sur la carte entière, plus grossière.
//
// Fichiers (pipeline/natif/tuiles_bandes.py). Les tuiles font des centaines de Go : elles sont sur le Google Drive de
// l'utilisateur (lecteur G:, en diffusion : Drive les télécharge à la demande et les garde en cache). Sur le PC, seul
// un index par ordre :
//   index (PC)   : <dossier de la carte>/tuiles/<relevé>/ordre_K.idx = « UNIVTIL2 », 4 entiers 32 bits (K, largeur w
//                  d'une tuile, nombre de tuiles 12·4^K, g), puis 12·4^K entiers 32 bits : rang de la tuile dans son
//                  paquet + 1, ou 0 si la tuile est absente (rien de mesuré là).
//   paquets      : <racine>/<relevé>/ordre_K/p######.bin, ###### = numéro de tuile >> 2g (les 4^g tuiles d'un paquet
//                  sont voisines sur le ciel) ; les tuiles présentes bout à bout, sans en-tête.
// Une tuile = w² valeurs float16 dans l'ordre HEALPix emboîté : c'est exactement le morceau [n·w², (n+1)·w²) de la
// carte Nside = w·2^K. NaN = pas de mesure. Les ordres plus grossiers que le dernier sont la moyenne des 4 enfants
// mesurés (somme du mesuré).
//
// Sur la carte graphique : une réserve de N emplacements de tuile, et une table de pages (un entier par tuile possible de
// chaque ordre : 0 = pas chargée, sinon emplacement + 1). Le shader descend du niveau voulu vers le plus grossier chargé,
// puis vers la carte entière : tant qu'une tuile fine n'est pas arrivée, on voit la mesure plus grossière, jamais rien
// d'inventé.
#pragma once
#include "commun.h"
#include <condition_variable>
#include <deque>
#include <filesystem>
#include <mutex>
#include <thread>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iterator>
#include <unordered_map>

namespace {

// HEALPix emboîté en double précision : face (0 à 11) et coordonnées (ix, iy) dans la face, pour Nside quelconque
// (même calcul que ang2pixNest dans ciel_bandes.frag ; Górski et al. 2005).
inline void healpixFaceXY(uint32_t nside, double x, double y, double z, int& face, int& ix, int& iy) {
    const double kPi = 3.14159265358979323846;
    const double za = std::fabs(z);
    double phi = std::atan2(y, x);
    if (phi < 0) phi += 2 * kPi;
    const double tt = phi / (0.5 * kPi);
    const int ns = static_cast<int>(nside);
    if (za <= 2.0 / 3.0) {
        const double t1 = ns * (0.5 + tt), t2 = ns * z * 0.75;
        const int jp = static_cast<int>(t1 - t2), jm = static_cast<int>(t1 + t2);
        const int ifp = jp / ns, ifm = jm / ns;
        face = ifp == ifm ? (ifp | 4) : (ifp < ifm ? ifp : ifm + 8);
        ix = jm & (ns - 1);
        iy = ns - (jp & (ns - 1)) - 1;
    } else {
        const int ntt = std::min(static_cast<int>(tt), 3);
        const double tp = tt - ntt;
        const double tmp = ns * std::sqrt(3.0 * (x * x + y * y) / (1.0 + za));      // = Nside·√(3(1−|z|)), sans perte près du pôle
        const int jp = std::min(static_cast<int>(tp * tmp), ns - 1), jm = std::min(static_cast<int>((1.0 - tp) * tmp), ns - 1);
        if (z >= 0) { face = ntt; ix = ns - jm - 1; iy = ns - jp - 1; }
        else { face = ntt + 8; ix = jp; iy = jm; }
    }
}

inline uint64_t healpixInterleave(uint32_t x, uint32_t y) {
    uint64_t r = 0;
    for (int b = 0; b < 32; ++b) r |= (static_cast<uint64_t>((x >> b) & 1u) << (2 * b)) | (static_cast<uint64_t>((y >> b) & 1u) << (2 * b + 1));
    return r;
}

// Chemin écrit en UTF-8 (le Google Drive de l'utilisateur a des noms avec « · » ou des accents). Sous Windows, une
// std::string serait lue dans la page de code ANSI : on passe par les caractères larges.
inline std::filesystem::path utf8Path(const std::string& s) {
    return std::filesystem::path(std::u8string(reinterpret_cast<const char8_t*>(s.data()), s.size()));
}

class SkyTileStream {
public:
    bool active = false;          // des tuiles fines existent pour la carte chargée
    uint32_t width = 0, logWidth = 0, orderMin = 0, orderMax = 0;
    std::string dir, root;
    uint32_t shownOrder = 0;
    double scale = 1;             // valeurs stockées × facteur_float16 (fiche.json) : float16 ne va que de 6e-8 à 65504      // ordre le plus fin chargé au centre de l'écran (0 : aucune tuile fine)
    uint32_t pending() const { return static_cast<uint32_t>(inFlight_); }

    // Cherche les index ordre_K.idx du relevé dans indexDir ; les paquets sont dans bundleRoot. On ne garde que les ordres
    // plus fins que la carte entière (Nside > baseNside).
    bool open(const Gpu& g, const std::string& indexDir, const std::string& bundleRoot, uint32_t baseNside, uint32_t slots = 1024) {
        close(g);
        std::error_code ec;
        if (!std::filesystem::is_directory(indexDir, ec)) return false;
        std::vector<Level> lv;
        uint32_t w = 0;
        for (uint32_t k = 0; k <= 12; ++k) {
            std::ifstream f(indexDir + "/ordre_" + std::to_string(k) + ".idx", std::ios::binary);
            if (!f) continue;
            char magic[8];
            uint32_t h[4];
            f.read(magic, 8);
            f.read(reinterpret_cast<char*>(h), sizeof h);
            if (!f || std::memcmp(magic, "UNIVTIL2", 8) != 0 || h[0] != k || h[1] == 0 || (h[1] & (h[1] - 1)) != 0 || h[3] > k) continue;
            if (static_cast<uint64_t>(h[1]) << k <= baseNside) continue;
            if (w && h[1] != w) continue;      // une seule largeur de tuile par relevé
            Level L;
            L.order = k;
            L.group = h[3];
            L.path = bundleRoot + "/ordre_" + std::to_string(k);
            L.rank.resize(12ull << (2 * k));
            if (h[2] != L.rank.size()) continue;
            f.read(reinterpret_cast<char*>(L.rank.data()), static_cast<std::streamsize>(L.rank.size() * 4));
            if (!f) continue;
            w = h[1];
            lv.push_back(std::move(L));
        }
        if (lv.empty()) return false;
        {      // facteur des float16 (pipeline/natif/tuiles_bandes.py) : valeur mesurée = valeur stockée / facteur
            std::ifstream fj(indexDir + "/fiche.json", std::ios::binary);
            std::string js((std::istreambuf_iterator<char>(fj)), std::istreambuf_iterator<char>());
            const std::string k = "\"facteur_float16\": ";
            const size_t p = js.find(k);
            scale = p == std::string::npos ? 1.0 : std::atof(js.c_str() + p + k.size());
            if (!(scale > 0)) return false;      // facteur illisible : mieux vaut pas de tuiles que des valeurs fausses
        }
        // Les ordres doivent se suivre (la table de pages les met bout à bout, ordre par ordre).
        for (size_t i = 1; i < lv.size(); ++i)
            if (lv[i].order != lv[i - 1].order + 1) { lv.resize(i); break; }
        levels_ = std::move(lv);
        width = w;
        logWidth = 0;
        while ((1u << logWidth) < w) ++logWidth;
        orderMin = levels_.front().order;
        orderMax = levels_.back().order;
        dir = indexDir;
        root = bundleRoot;
        tileBytes_ = static_cast<VkDeviceSize>(w) * w * 2;
        slots_ = slots;
        pages_ = 4ull * ((1ull << (2 * (orderMax + 1))) - (1ull << (2 * orderMin)));      // Σ 12·4^k, k = orderMin … orderMax
        page_ = createBuffer(g, pages_ * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        check(vkMapMemory(g.dev, page_.mem, 0, pages_ * 4, 0, reinterpret_cast<void**>(&pageMap_)), "table des tuiles du ciel");
        std::memset(pageMap_, 0, pages_ * 4);
        pool_ = createBuffer(g, tileBytes_ * slots_, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        staging_ = createBuffer(g, tileBytes_ * kBatch, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        check(vkMapMemory(g.dev, staging_.mem, 0, tileBytes_ * kBatch, 0, &stagingMap_), "tuiles du ciel");
        slotKey_.assign(slots_, kNone);
        slotSeen_.assign(slots_, 0);
        state_.clear();
        stop_ = false;
        for (auto& t : workers_) t = std::thread([this] { run(); });
        active = true;
        return true;
    }

    VkDescriptorBufferInfo pageInfo() const { return {page_.buf, 0, pages_ * 4}; }
    VkDescriptorBufferInfo poolInfo() const { return {pool_.buf, 0, tileBytes_ * slots_}; }

    // Ordre de tuile voulu pour un pixel de l'écran d'angle « screen » (radians) : le plus fin dont le pixel HEALPix n'est
    // pas plus petit que le pixel de l'écran. Peut être hors de [orderMin, orderMax].
    int wantedOrder(double screen) const {
        const double hpx0 = std::sqrt(3.14159265358979323846 / 3.0);      // pixel HEALPix de Nside 1 (radians)
        const double ns = hpx0 / std::max(screen, 1e-12);
        return static_cast<int>(std::floor(std::log2(std::max(ns, 1.0)))) - static_cast<int>(logWidth);
    }

    // À chaque image, avant de dessiner. dirs : directions (repère du relevé) échantillonnées sur l'écran ; center : la
    // direction du centre ; screen : angle d'un pixel de l'écran au centre. Demande les tuiles visibles (et leurs parents,
    // pour qu'un niveau plus grossier soit là pendant le chargement), envoie sur la carte graphique celles qui sont lues.
    void update(const Gpu& g, const std::vector<Vec3>& dirs, const Vec3& center, double screen) {
        if (!active) return;
        ++frame_;
        const int want = wantedOrder(screen);
        std::vector<uint64_t> need;
        if (want >= static_cast<int>(orderMin)) {
            const uint32_t top = std::min<uint32_t>(static_cast<uint32_t>(want), orderMax);
            std::unordered_map<uint64_t, bool> seen;
            for (uint32_t k = orderMin; k <= top; ++k)      // du plus grossier au plus fin : priorité au grossier
                for (const Vec3& d : dirs) {
                    const uint64_t key = tileKey(k, d);
                    if (seen.emplace(key, true).second) need.push_back(key);
                }
        }
        // Tuiles voulues déjà en place : marquées vues (on ne les remplace pas). Les autres : à lire, sauf si absentes du fichier.
        std::unordered_map<uint64_t, bool> needSet;
        for (uint64_t key : need) {
            needSet[key] = true;
            auto it = state_.find(key);
            if (it == state_.end()) {
                const Level& L = level(keyOrder(key));
                state_[key] = L.rank[keyTile(key)] == 0 ? kAbsent : kLoading;      // absente : rien de mesuré là
            } else if (it->second >= 0) {
                slotSeen_[it->second] = frame_;
            }
        }
        {
            std::lock_guard<std::mutex> lk(mu_);
            // Les lectures demandées avant et plus à l'écran sont abandonnées (on a bougé) ; la file est refaite dans
            // l'ordre de « need » (le grossier d'abord).
            for (auto it = state_.begin(); it != state_.end();)
                it = it->second == kLoading && !needSet.count(it->first) ? state_.erase(it) : std::next(it);
            queue_.clear();
            for (uint64_t key : need) {
                auto it = state_.find(key);
                if (it == state_.end() || it->second != kLoading) continue;
                if (std::find(runningKeys_.begin(), runningKeys_.end(), key) != runningKeys_.end()) continue;
                bool read = false;
                for (const Read& r : done_)
                    if (r.key == key) { read = true; break; }
                if (!read) queue_.push_back(key);
            }
            inFlight_ = static_cast<int>(queue_.size() + done_.size()) + running_;
        }
        cv_.notify_one();
        upload(g);
        // Ordre le plus fin réellement montré au centre (pour la légende).
        shownOrder = 0;
        for (int k = std::min<int>(want, orderMax); k >= static_cast<int>(orderMin); --k) {
            auto it = state_.find(tileKey(static_cast<uint32_t>(k), center));
            if (it != state_.end() && it->second >= 0) { shownOrder = static_cast<uint32_t>(k); break; }
        }
    }

    // Pour les essais hors écran : attend que toutes les tuiles demandées soient chargées.
    void finish(const Gpu& g, const std::vector<Vec3>& dirs, const Vec3& center, double screen) {
        for (int i = 0; i < 100000; ++i) {
            update(g, dirs, center, screen);
            std::unique_lock<std::mutex> lk(mu_);
            if (queue_.empty() && running_ == 0 && done_.empty()) break;
            lk.unlock();
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
        }
        update(g, dirs, center, screen);
    }

    void close(const Gpu& g) {
        if (!active) return;
        {
            std::lock_guard<std::mutex> lk(mu_);
            stop_ = true;
        }
        cv_.notify_all();
        for (auto& t : workers_)
            if (t.joinable()) t.join();
        vkDeviceWaitIdle(g.dev);
        vkUnmapMemory(g.dev, page_.mem);
        vkUnmapMemory(g.dev, staging_.mem);
        destroy(g, page_);
        destroy(g, pool_);
        destroy(g, staging_);
        levels_.clear();
        queue_.clear();
        done_.clear();
        runningKeys_.clear();
        state_.clear();
        running_ = inFlight_ = 0;
        active = false;
        shownOrder = 0;
    }

private:
    struct Level {
        uint32_t order = 0, group = 0;
        std::string path;                 // dossier des paquets de cet ordre
        std::vector<uint32_t> rank;       // rang dans le paquet + 1 ; 0 = absente
    };
    struct Read {
        uint64_t key;
        std::vector<uint16_t> data;      // vide : lecture ratée
    };
    static constexpr uint32_t kBatch = 32;              // tuiles envoyées au plus par image
    static constexpr int kAbsent = -2, kLoading = -1;
    static constexpr uint64_t kNone = ~0ull;

    std::vector<Level> levels_;
    VkDeviceSize tileBytes_ = 0;
    uint32_t slots_ = 0;
    uint64_t pages_ = 0;
    Buffer page_{}, pool_{}, staging_{};
    uint32_t* pageMap_ = nullptr;
    void* stagingMap_ = nullptr;
    std::vector<uint64_t> slotKey_, slotSeen_;
    std::unordered_map<uint64_t, int> state_;      // clé → emplacement (≥ 0), kLoading ou kAbsent
    uint64_t frame_ = 0;

    std::thread workers_[4];      // plusieurs lectures en même temps : chacune peut attendre le réseau (Drive)
    std::mutex mu_;
    std::condition_variable cv_;
    std::deque<uint64_t> queue_;
    std::vector<Read> done_;
    std::vector<uint64_t> runningKeys_;
    int running_ = 0, inFlight_ = 0;
    bool stop_ = false;

    // Clé d'une tuile : ordre dans les 8 bits du haut, numéro de tuile en dessous.
    static uint64_t makeKey(uint32_t k, uint64_t tile) { return (static_cast<uint64_t>(k) << 56) | tile; }
    static uint32_t keyOrder(uint64_t key) { return static_cast<uint32_t>(key >> 56); }
    static uint64_t keyTile(uint64_t key) { return key & ((1ull << 56) - 1); }
    const Level& level(uint32_t k) const { return levels_[k - orderMin]; }
    uint64_t pageIndex(uint64_t key) const {
        const uint32_t k = keyOrder(key);
        return 4ull * ((1ull << (2 * k)) - (1ull << (2 * orderMin))) + keyTile(key);
    }
    uint64_t tileKey(uint32_t k, const Vec3& d) const {
        int face, ix, iy;
        const double n = std::sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
        healpixFaceXY(1u << k, d.x / n, d.y / n, d.z / n, face, ix, iy);      // la tuile est le pixel HEALPix de Nside 2^k
        return makeKey(k, (static_cast<uint64_t>(face) << (2 * k)) + healpixInterleave(static_cast<uint32_t>(ix), static_cast<uint32_t>(iy)));
    }

    // Fils de lecture : une tuile à la fois chacun, lue dans son paquet (sur le Drive : Drive la télécharge si besoin).
    void run() {
        while (true) {
            uint64_t key;
            {
                std::unique_lock<std::mutex> lk(mu_);
                cv_.wait(lk, [&] { return stop_ || !queue_.empty(); });
                if (stop_) return;
                key = queue_.front();
                queue_.pop_front();
                runningKeys_.push_back(key);
                ++running_;
            }
            Read r{key, {}};
            const Level& L = levels_[keyOrder(key) - orderMin];
            const uint64_t tile = keyTile(key);
            char name[32];
            std::snprintf(name, sizeof name, "/p%06llu.bin", static_cast<unsigned long long>(tile >> (2 * L.group)));
            std::ifstream f(utf8Path(L.path + name), std::ios::binary);
            if (f) {
                f.seekg(static_cast<std::streamoff>((L.rank[tile] - 1ull) * tileBytes_));
                r.data.resize(static_cast<size_t>(width) * width);
                f.read(reinterpret_cast<char*>(r.data.data()), static_cast<std::streamsize>(tileBytes_));
                if (!f) r.data.clear();
            }
            {
                std::lock_guard<std::mutex> lk(mu_);
                done_.push_back(std::move(r));
                runningKeys_.erase(std::find(runningKeys_.begin(), runningKeys_.end(), key));
                --running_;
            }
        }
    }

    // Tuiles lues → emplacements de la réserve. On attend que la carte graphique ait fini les images en cours avant de
    // réécrire un emplacement (une image en vol pourrait encore le lire) : vkQueueWaitIdle, puis copie, puis table.
    void upload(const Gpu& g) {
        std::vector<Read> got;
        {
            std::lock_guard<std::mutex> lk(mu_);
            const size_t n = std::min<size_t>(done_.size(), kBatch);
            got.assign(std::make_move_iterator(done_.begin()), std::make_move_iterator(done_.begin() + static_cast<std::ptrdiff_t>(n)));
            done_.erase(done_.begin(), done_.begin() + static_cast<std::ptrdiff_t>(n));
            inFlight_ = static_cast<int>(queue_.size() + done_.size()) + running_;
        }
        if (got.empty()) return;
        std::vector<std::pair<uint64_t, uint32_t>> placed;
        std::vector<VkBufferCopy> copies;
        uint32_t used = 0;
        for (Read& r : got) {
            auto it = state_.find(r.key);
            if (it == state_.end() || it->second != kLoading) continue;      // abandonnée entre-temps
            if (r.data.empty()) { it->second = kAbsent; continue; }          // lecture ratée : on garde le niveau grossier
            const int slot = victim();
            if (slot < 0) { state_.erase(it); continue; }                   // réserve pleine de tuiles visibles
            if (slotKey_[slot] != kNone) {
                pageMap_[pageIndex(slotKey_[slot])] = 0;      // les images en vol retombent sur le niveau grossier
                state_.erase(slotKey_[slot]);
            }
            slotKey_[slot] = r.key;
            slotSeen_[slot] = frame_;
            it->second = slot;
            std::memcpy(static_cast<char*>(stagingMap_) + used * tileBytes_, r.data.data(), tileBytes_);
            copies.push_back({used * tileBytes_, static_cast<VkDeviceSize>(slot) * tileBytes_, tileBytes_});
            placed.push_back({r.key, static_cast<uint32_t>(slot)});
            ++used;
        }
        if (copies.empty()) return;
        check(vkQueueWaitIdle(g.queue), "tuiles du ciel");
        VkCommandBuffer cmd = beginOnce(g);
        vkCmdCopyBuffer(cmd, staging_.buf, pool_.buf, static_cast<uint32_t>(copies.size()), copies.data());
        endOnce(g, cmd);
        for (const auto& [key, slot] : placed) pageMap_[pageIndex(key)] = slot + 1;
    }

    // Emplacement à réécrire : un libre, sinon le moins récemment vu qui n'est pas à l'écran à cette image.
    int victim() {
        int best = -1;
        uint64_t oldest = ~0ull;
        for (uint32_t s = 0; s < slots_; ++s) {
            if (slotKey_[s] == kNone) return static_cast<int>(s);
            if (slotSeen_[s] < frame_ && slotSeen_[s] < oldest) { oldest = slotSeen_[s]; best = static_cast<int>(s); }
        }
        return best;
    }
};

}  // namespace
