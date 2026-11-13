// Appli PC « Univers » : le ciel dans toutes les longueurs d'onde (radio, micro-ondes, infrarouge, UV, X, gamma).
//
// Chaque bande est une carte MESURÉE du ciel entier, publiée par l'équipe d'un relevé (fiche dans le fichier) :
// fichiers ciel_<nom>.bin écrits par pipeline/natif/ciel_bandes.py depuis les tuiles HiPS en FITS (valeurs physiques,
// sans retouche). Rien n'est modélisé : un pixel que le relevé n'a pas mesuré reste vide et s'affiche hachuré.
//
// Ce qu'une carte du ciel est, et n'est pas : c'est le ciel vu depuis la Terre, sans profondeur. Elle n'est donc montrée
// que depuis le voisinage du Soleil ; elle s'efface entre 0,1 et 1 parsec (au-delà, le décalage de parallaxe des nuages
// proches dépasserait la résolution des relevés). L'écran le dit (legende()).
//
// Format de ciel_<nom>.bin : « UNIVSKY1 », puis 4 entiers 32 bits (Nside, 1 si repère galactique sinon équatorial ICRS,
// longueur de la fiche JSON, 0), la fiche JSON (UTF-8), des zéros jusqu'à un multiple de 16 octets, puis 12 × Nside²
// flottants 32 bits dans l'ordre HEALPix emboîté (NaN = pas de mesure).
#pragma once
#include "commun.h"
#include "ciel_tuiles.h"
#include <filesystem>
#include <limits>

namespace {

struct SkyBandUbo {      // std140 : tout en vec4
    float right[4], up[4], fwd[4];
    float scale[4];      // bas, haut, logarithmique (1) ou linéaire (0), opacité
    float grid[4];       // Nside, nombre de niveaux de la pyramide, angle d'un pixel de l'écran au centre (rad), échelle des points
    float eqRight[4], eqUp[4], eqFwd[4];      // vecteurs de la caméra en équatorial ICRS (catalogues de sources), unitaires
    float proj[4];       // 1 / (tan(champ/2) × rapport largeur/hauteur), 1 / tan(champ/2), rien, 1
    float fine[4];       // tuiles fines (ciel_tuiles.h) : ordre le plus grossier, le plus fin, log2(largeur), 1 si présentes
    float cut[4];        // par catalogue : grandeur relative (à la médiane) sous laquelle une source n'est pas dessinée
};

// Catalogue de sources de la bande (sources_<bande>.bin, pipeline/natif/sources_bandes.py) : directions mesurées.
struct SkySourcesInfo {
    std::string label, reference, quantity, unit;
    std::vector<std::pair<std::string, int>> groups;      // nom du groupe, nombre de sources
    uint32_t count = 0;
    double median = 0, minimum = 0, maximum = 0;
    uint32_t firstColor = 0;     // couleur du premier groupe (les suivants prennent les couleurs suivantes)
    bool fixedSize = false;      // tous les cercles de même taille (la grandeur n'est pas un éclat, par exemple un décalage vers le rouge)
    std::vector<float> sortedRel;      // grandeurs relatives, de la plus forte à la plus faible (seuil selon le champ)
    float cut = 0;                     // seuil de la dernière image (0 : toutes dessinées)
    uint32_t shown = 0;                // nombre de sources au-dessus du seuil, sur tout le ciel
};

// Fiche d'une bande, lue dans le JSON du fichier. Les textes sont ceux du script : source, mesure, unité, référence.
struct SkyBandInfo {
    std::string path, key, label, band, measure, unit, wavelength, reference, publishedCoverage, survey, scaleKind;
    double resolutionArcmin = 0, mapResolutionArcmin = 0, coverage = 0, lo = 0, hi = 0, median = 0;
    double softness = 1;      // échelle asinh : en dessous, l'échelle devient linéaire (autour de zéro)
    uint32_t nside = 0;
    bool galactic = false;
};

// Lecture d'un champ dans le JSON écrit par ciel_bandes.py (plat, sauf « stats » dont les clés sont uniques).
inline std::string jsonString(const std::string& js, const std::string& key) {
    const std::string k = "\"" + key + "\": \"";
    size_t p = js.find(k);
    if (p == std::string::npos) return {};
    p += k.size();
    std::string out;
    for (; p < js.size() && js[p] != '"'; ++p) {
        if (js[p] == '\\' && p + 1 < js.size()) ++p;
        out += js[p];
    }
    return out;
}
inline double jsonNumber(const std::string& js, const std::string& key, double fallback = 0) {
    const std::string k = "\"" + key + "\": ";
    const size_t p = js.find(k);
    if (p == std::string::npos) return fallback;
    return std::atof(js.c_str() + p + k.size());
}

inline bool readSkyBandHeader(const std::string& path, SkyBandInfo& info, std::streamoff& dataOffset) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return false;
    char magic[8];
    uint32_t h[4];
    f.read(magic, 8);
    f.read(reinterpret_cast<char*>(h), sizeof(h));
    if (!f || std::memcmp(magic, "UNIVSKY1", 8) != 0 || h[0] == 0 || (h[0] & (h[0] - 1)) != 0) return false;
    std::string js(h[2], '\0');
    f.read(js.data(), h[2]);
    if (!f) return false;
    info.path = path;
    info.nside = h[0];
    info.galactic = h[1] == 1;
    info.key = jsonString(js, "nom");
    info.label = jsonString(js, "libelle");
    info.band = jsonString(js, "bande");
    info.measure = jsonString(js, "mesure");
    info.unit = jsonString(js, "unite");
    info.wavelength = jsonString(js, "longueur_onde");
    info.reference = jsonString(js, "reference");
    info.publishedCoverage = jsonString(js, "couverture_publiee");
    info.survey = jsonString(js, "hips");
    info.scaleKind = jsonString(js, "echelle");
    info.resolutionArcmin = jsonNumber(js, "resolution_arcmin");
    info.mapResolutionArcmin = jsonNumber(js, "resolution_carte_arcmin");
    info.coverage = jsonNumber(js, "couverture_mesuree");
    info.lo = jsonNumber(js, "p01");
    info.hi = jsonNumber(js, "p999");
    info.median = jsonNumber(js, "p50");
    if (info.scaleKind.empty()) info.scaleKind = "log";
    // Échelle logarithmique demandée mais des valeurs mesurées ≤ 0 (carte dont le niveau moyen a été retiré, comme Planck
    // PR4) : asinh, logarithmique pour les fortes valeurs et linéaire autour de zéro. Ces pixels gardent leur valeur
    // au lieu de tomber au noir.
    if (info.scaleKind == "log" && info.lo <= 0) {
        info.scaleKind = "asinh";
        info.softness = std::max(std::fabs(info.median) * 0.1, (info.hi - info.lo) * 1e-4);
        if (!(info.softness > 0)) info.softness = 1;
    }
    dataOffset = static_cast<std::streamoff>((24 + h[2] + 15) / 16 * 16);
    return true;
}

// Toutes les bandes présentes dans le dossier des données, rangées de la radio vers le gamma.
inline std::vector<SkyBandInfo> listSkyBands(const std::string& dir) {
    static const char* order[] = {"radio", "micro-ondes", "infrarouge", "visible", "ultraviolet", "X", "gamma"};
    std::vector<SkyBandInfo> out;
    std::error_code ec;
    for (const auto& e : std::filesystem::directory_iterator(dir, ec)) {
        const std::string name = e.path().filename().string();
        if (name.rfind("ciel_", 0) != 0 || e.path().extension() != ".bin") continue;
        SkyBandInfo info;
        std::streamoff off;
        if (readSkyBandHeader(e.path().string(), info, off)) out.push_back(info);
    }
    auto rank = [&](const SkyBandInfo& b) {
        for (int i = 0; i < 7; ++i)
            if (b.band == order[i]) return i;
        return 7;
    };
    std::stable_sort(out.begin(), out.end(), [&](const SkyBandInfo& a, const SkyBandInfo& b) {
        return rank(a) != rank(b) ? rank(a) < rank(b) : a.key < b.key;
    });
    return out;
}

class SkyBandRenderer {
public:
    bool ready = false;      // pipeline prêt
    bool loaded = false;     // une carte est sur la carte graphique
    SkyBandInfo info;

    // Opacité selon la distance au Soleil (années-lumière) : 1 jusqu'à 0,1 pc, 0 à partir de 1 pc, en échelle log.
    static double opacityAt(double distLy) {
        constexpr double kPc = 3.26156;
        const double d = distLy / kPc;
        if (d <= 0.1) return 1.0;
        if (d >= 1.0) return 0.0;
        return 1.0 - std::log10(d / 0.1);
    }

    bool create(const Gpu& g, VkFormat hdrFormat) {
        gpu_ = &g;
        for (auto& u : ubo_) u = createBuffer(g, sizeof(SkyBandUbo), VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        for (int i = 0; i < kRing; ++i) check(vkMapMemory(g.dev, ubo_[i].mem, 0, sizeof(SkyBandUbo), 0, &mapped_[i]), "ciel par bande");
        dummy_ = createBuffer(g, 32, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        createPipeline(g, hdrFormat);
        ready = true;
        return true;
    }

    // Charge une bande (remplace la précédente). Attend que la carte graphique ait fini avec l'ancienne.
    bool load(const Gpu& g, const std::string& path) {
        SkyBandInfo in;
        std::streamoff off = 0;
        if (!readSkyBandHeader(path, in, off)) return false;
        const size_t n = 12ull * in.nside * in.nside;
        // Pyramide « somme du mesuré » : niveau 0 = la carte ; chaque niveau suivant donne à un pixel la moyenne de ses
        // 4 enfants mesurés (ordre emboîté : les 4 enfants se suivent). Un pixel sans aucun enfant mesuré reste vide.
        // Le shader lit le niveau dont le pixel a la taille d'un pixel de l'écran : de loin on voit la moyenne de ce qui
        // est mesuré dans le pixel, pas un pixel du relevé pris au hasard (ce qui donnait un grain artificiel).
        size_t total = 0;
        uint32_t levels = 0;
        for (uint32_t ns = in.nside; ns >= 1; ns /= 2) {
            total += 12ull * ns * ns;
            ++levels;
        }
        std::ifstream f(path, std::ios::binary);
        f.seekg(off);
        Buffer staging = createBuffer(g, total * 4, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, total * 4, 0, &p), "carte du ciel");
        f.read(static_cast<char*>(p), static_cast<std::streamsize>(n * 4));
        const bool ok = static_cast<bool>(f);
        if (ok) {
            float* v = static_cast<float*>(p);
            size_t src = 0, dst = n, count = n;
            for (uint32_t l = 1; l < levels; ++l) {
                for (size_t i = 0; i < count / 4; ++i) {
                    double sum = 0;
                    int k = 0;
                    for (int c = 0; c < 4; ++c) {
                        const float x = v[src + 4 * i + c];
                        if (std::isfinite(x)) { sum += x; ++k; }
                    }
                    v[dst + i] = k ? static_cast<float>(sum / k) : std::numeric_limits<float>::quiet_NaN();
                }
                src = dst;
                dst += count / 4;
                count /= 4;
            }
        }
        vkUnmapMemory(g.dev, staging.mem);
        if (!ok) {
            destroy(g, staging);
            return false;
        }
        levels_ = levels;
        vkDeviceWaitIdle(g.dev);
        if (loaded) destroy(g, map_);
        map_ = createBuffer(g, total * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        VkCommandBuffer cmd = beginOnce(g);
        const VkBufferCopy region{0, 0, total * 4};
        vkCmdCopyBuffer(cmd, staging.buf, map_.buf, 1, &region);
        endOnce(g, cmd);
        destroy(g, staging);
        info = in;
        loadSources(g, path);
        tiles_.close(g);
        std::string tindex, troot;
        if (tileDirs(path, in.key, tindex, troot)) tiles_.open(g, tindex, troot, in.nside);
        writeSets(g, total * 4);
        loaded = true;
        return true;
    }

    // Catalogues de sources faits pour cette carte, dans le même dossier : les fichiers sources_*.bin dont la fiche nomme
    // la carte dans « cartes » (facultatif ; plusieurs possibles, mis bout à bout dans un seul tampon). Chaque groupe de
    // chaque catalogue reçoit sa couleur (8 au plus) ; la grandeur est rapportée à la médiane de son catalogue.
    void loadSources(const Gpu& g, const std::string& mapPath) {
        if (srcCount_) destroy(g, src_);
        srcCount_ = 0;
        catalogs.clear();
        std::vector<uint32_t> all;
        // chemin relatif sans dossier (« ciel_fermi3.bin ») : parent_path() est vide ; on cherche alors à côté, pas à la racine
        std::filesystem::path dir = std::filesystem::path(mapPath).parent_path();
        if (dir.empty()) dir = ".";
        std::vector<std::string> files;
        std::error_code ec;
        for (const auto& e : std::filesystem::directory_iterator(dir, ec)) {
            const std::string name = e.path().filename().string();
            if (name.rfind("sources_", 0) == 0 && e.path().extension() == ".bin") files.push_back(e.path().string());
        }
        std::sort(files.begin(), files.end());
        uint32_t color = 0;
        for (const auto& path : files) readSources(path, all, color);
        if (all.empty()) return;
        src_ = uploadStorage(g, all.data(), all.size() * 4);
        srcCount_ = static_cast<uint32_t>(all.size() / 8);
    }

    bool readSources(const std::string& path, std::vector<uint32_t>& all, uint32_t& color) {
        std::ifstream f(path, std::ios::binary);
        if (!f) return false;
        char magic[8];
        uint32_t h[4];
        f.read(magic, 8);
        f.read(reinterpret_cast<char*>(h), sizeof(h));
        if (!f || std::memcmp(magic, "UNIVSRC1", 8) != 0 || h[0] == 0) return false;
        std::string js(h[1], '\0');
        f.read(js.data(), h[1]);
        const size_t cp = js.find("\"cartes\": [");
        if (cp == std::string::npos || js.find("\"" + info.key + "\"", cp) > js.find(']', cp)) return false;
        f.seekg(static_cast<std::streamoff>((24 + h[1] + 15) / 16 * 16));
        std::vector<uint32_t> rec(static_cast<size_t>(h[0]) * 8);
        f.read(reinterpret_cast<char*>(rec.data()), static_cast<std::streamsize>(rec.size() * 4));
        if (!f) return false;
        SkySourcesInfo c;
        c.label = jsonString(js, "libelle");
        c.reference = jsonString(js, "reference");
        c.quantity = jsonString(js, "grandeur");
        c.unit = jsonString(js, "unite");
        c.median = jsonNumber(js, "grandeur_p50", 1.0);
        c.minimum = jsonNumber(js, "grandeur_min");
        c.maximum = jsonNumber(js, "grandeur_max");
        c.fixedSize = jsonString(js, "taille") == "fixe";
        c.count = h[0];
        c.firstColor = color;
        const size_t gp = js.find("\"groupes\": [");
        if (gp != std::string::npos) {      // noms des groupes, dans l'ordre des numéros, puis leurs nombres dans « comptes »
            size_t p = gp + 12;
            const size_t end = js.find(']', p);
            const size_t counts = js.find("\"comptes\"");
            while (true) {
                const size_t a = js.find('"', p);
                if (a == std::string::npos || a > end) break;
                const size_t b = js.find('"', a + 1);
                const std::string name = js.substr(a + 1, b - a - 1);
                c.groups.push_back({name, counts == std::string::npos ? 0 : static_cast<int>(jsonNumber(js.substr(counts), name))});
                p = b + 1;
            }
        }
        const float med = static_cast<float>(c.median > 0 ? c.median : 1.0);
        for (size_t i = 0; i < c.count; ++i) {
            float v;
            std::memcpy(&v, &rec[i * 8 + 3], 4);
            v /= med;
            std::memcpy(&rec[i * 8 + 3], &v, 4);
            rec[i * 8 + 4] = std::min<uint32_t>(rec[i * 8 + 4] + color, 7);      // couleur
            rec[i * 8 + 5] = c.fixedSize ? 1 : 0;                                 // taille fixe
            rec[i * 8 + 6] = static_cast<uint32_t>(std::min<size_t>(catalogs.size(), 3));      // numéro du catalogue (seuil)
            if (!c.fixedSize) c.sortedRel.push_back(v);
        }
        color += static_cast<uint32_t>(std::max<size_t>(c.groups.size(), 1));
        all.insert(all.end(), rec.begin(), rec.end());
        std::sort(c.sortedRel.begin(), c.sortedRel.end(), std::greater<float>());
        c.shown = c.count;
        catalogs.push_back(std::move(c));
        return true;
    }

    // Tuiles fines d'une bande : index dans « tuiles/<nom> » à côté de la carte ; paquets dans <racine>/<nom>, la racine
    // étant la première ligne de « tuiles_dossier.txt » à côté de la carte (le Google Drive), sinon à côté de l'index.
    static bool tileDirs(const std::string& mapPath, const std::string& key, std::string& index, std::string& root) {
        if (key.empty()) return false;
        const std::filesystem::path dir = std::filesystem::path(mapPath).parent_path();
        std::error_code ec;
        if (!std::filesystem::is_directory(dir / "tuiles" / key, ec)) return false;
        index = (dir / "tuiles" / key).string();
        root = index;
        std::ifstream f(dir / "tuiles_dossier.txt");
        std::string line;
        if (f && std::getline(f, line)) {
            if (line.size() >= 3 && static_cast<unsigned char>(line[0]) == 0xEF) line = line.substr(3);      // BOM UTF-8
            while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
            /* le fichier est en UTF-8 (le chemin du Drive contient « · ») : on le garde en UTF-8 jusqu'à l'ouverture */
            if (!line.empty()) root = line + "/" + key;
        }
        return true;
    }

    void writeSets(const Gpu& g, VkDeviceSize mapBytes) {
        for (int i = 0; i < kRing; ++i) {
            const VkDescriptorBufferInfo bi[5] = {{ubo_[i].buf, 0, sizeof(SkyBandUbo)}, {map_.buf, 0, mapBytes},
                                                  srcCount_ ? VkDescriptorBufferInfo{src_.buf, 0, srcCount_ * 32ull} : VkDescriptorBufferInfo{dummy_.buf, 0, 32},
                                                  tiles_.active ? tiles_.pageInfo() : VkDescriptorBufferInfo{dummy_.buf, 0, 32},
                                                  tiles_.active ? tiles_.poolInfo() : VkDescriptorBufferInfo{dummy_.buf, 0, 32}};
            VkWriteDescriptorSet w[5];
            for (uint32_t b = 0; b < 5; ++b) {
                w[b] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
                w[b].dstSet = sets_[i];
                w[b].dstBinding = b;
                w[b].descriptorCount = 1;
                w[b].descriptorType = b == 0 ? VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER : VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
                w[b].pBufferInfo = &bi[b];
            }
            vkUpdateDescriptorSets(g.dev, 5, w, 0, nullptr);
        }
    }

    static Buffer uploadStorage(const Gpu& g, const void* data, size_t bytes) {
        Buffer staging = createBuffer(g, bytes, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, bytes, 0, &p), "sources du ciel");
        std::memcpy(p, data, bytes);
        vkUnmapMemory(g.dev, staging.mem);
        Buffer b = createBuffer(g, bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        VkCommandBuffer cmd = beginOnce(g);
        const VkBufferCopy region{0, 0, bytes};
        vkCmdCopyBuffer(cmd, staging.buf, b.buf, 1, &region);
        endOnce(g, cmd);
        destroy(g, staging);
        return b;
    }

    bool showSources = true;     // cercles du catalogue de la bande (s'il y en a un)
    std::vector<SkySourcesInfo> catalogs;      // catalogues de sources dessinés avec la carte (vide s'il n'y en a pas)

    // Texte à afficher avec la bande : d'où vient la carte, ce qu'elle mesure, sa finesse, sa couverture, l'échelle.
    std::vector<std::string> legend(double distLy) const {
        std::vector<std::string> l;
        if (!loaded) return l;
        char b[512];
        l.push_back(info.label + (info.wavelength.empty() ? "" : " (" + info.wavelength + ")"));
        l.push_back(info.measure + ", en " + info.unit + ".");
        l.push_back("Relevé : " + info.reference + ".");
        std::snprintf(b, sizeof b, "Finesse : %.3g minute(s) d'arc (relevé) ; carte chargée : %.2g. Couverture mesurée : %.1f %% du ciel.",
                      info.resolutionArcmin, info.mapResolutionArcmin, info.coverage * 100.0);
        l.push_back(b);
        if (tiles_.active) {      // ce qui est réellement montré au centre de l'écran, pas ce qui pourrait l'être
            const double finest = 206264.806 * std::sqrt(kPi / 3.0) / (static_cast<double>(tiles_.width) * (1u << tiles_.orderMax));
            if (tiles_.shownOrder) {
                const double shown = 206264.806 * std::sqrt(kPi / 3.0) / (static_cast<double>(tiles_.width) * (1u << tiles_.shownOrder));
                std::snprintf(b, sizeof b, "Tuiles fines : pixel de %.2g″ au centre (le plus fin : %.2g″)%s.", shown, finest,
                              tiles_.pending() ? ", lecture en cours" : "");
            } else {
                std::snprintf(b, sizeof b, "Tuiles fines disponibles jusqu'à %.2g″ par pixel : resserrer le champ pour les voir.", finest);
            }
            l.push_back(b);
        }
        std::snprintf(b, sizeof b, "Fausses couleurs, échelle %s de %.3g à %.3g %s. Hachures : pas de mesure.",
                      info.scaleKind == "log" ? "logarithmique" : (info.scaleKind == "asinh" ? "asinh (log au-dessus du seuil de douceur, linéaire autour de zéro)" : "linéaire"),
                      info.lo, info.hi, info.unit.c_str());
        l.push_back(b);
        static const char* colors[] = {"blanc", "cyan", "vert", "rose", "bleu", "orange", "jaune", "violet"};
        for (const SkySourcesInfo& c : catalogs) {
            if (c.fixedSize)
                std::snprintf(b, sizeof b, "Cercles : %u sources, %s (%s) ; %s mesuré de %.3g à %.3g. Direction mesurée, distance non montrée ici.",
                              c.count, c.label.c_str(), c.reference.c_str(), c.quantity.c_str(), c.minimum, c.maximum);
            else if (c.cut > 0)
                std::snprintf(b, sizeof b, "Cercles : les %u plus fortes des %u sources, %s (%s), %s au-dessus de %.3g %s ; resserrer le champ pour voir les plus faibles.",
                              c.shown, c.count, c.label.c_str(), c.reference.c_str(), c.quantity.c_str(), c.cut * c.median, c.unit.c_str());
            else
                std::snprintf(b, sizeof b, "Cercles : %u sources, %s (%s) ; taille selon le %s. Direction mesurée, distance non montrée.",
                              c.count, c.label.c_str(), c.reference.c_str(), c.quantity.c_str());
            l.push_back(b);
            std::string gs;
            for (size_t k = 0; k < c.groups.size(); ++k) {
                if (!gs.empty()) gs += " ; ";
                gs += std::string(colors[std::min<size_t>(c.firstColor + k, 7)]) + " : " + c.groups[k].first + " (" + std::to_string(c.groups[k].second) + ")";
            }
            if (!gs.empty()) l.push_back(gs + ".");
        }
        const double a = opacityAt(distLy);
        if (a >= 1.0) l.push_back("Vu depuis la Terre : une carte du ciel n'a pas de profondeur.");
        else if (a > 0.0) l.push_back("On s'éloigne du Soleil : la carte, vue depuis la Terre, s'efface (plus du tout au-delà de 1 parsec).");
        else l.push_back("Trop loin du Soleil pour cette carte (vue depuis la Terre, sans profondeur) : rien n'est montré.");
        return l;
    }

    // Dans la passe en grande dynamique, en premier (fond du ciel). Rien n'est dessiné loin du Soleil.
    void draw(VkCommandBuffer cmd, const Camera& cam, uint32_t width, uint32_t height) {
        if (!ready || !loaded) return;
        const double distLy = std::sqrt(cam.pos.x * cam.pos.x + cam.pos.y * cam.pos.y + cam.pos.z * cam.pos.z);
        const double alpha = opacityAt(distLy);
        if (alpha <= 0.0) return;
        // Écliptique J2000 (repère de l'appli) vers équatorial : rotation d'axe x de l'obliquité (IAU 2006 : 84 381,406″).
        const double eps = 84381.406 / 3600.0 * kPi / 180.0, ce = std::cos(eps), se = std::sin(eps);
        // Équatorial ICRS vers galactique : matrice de Hipparcos (ESA 1997, vol. 1, § 1.5.3).
        static const double G[3][3] = {{-0.0548755604162154, -0.8734370902348850, -0.4838350155487132},
                                       {+0.4941094278755837, -0.4448296299600112, +0.7469822444972189},
                                       {-0.8676661490190047, -0.1980763734312015, +0.4559837761750669}};
        auto toEq = [&](Vec3 v) { return Vec3{v.x, ce * v.y - se * v.z, se * v.y + ce * v.z}; };
        auto toSurvey = [&](Vec3 v) {
            const Vec3 e = toEq(v);
            if (!info.galactic) return e;
            return Vec3{G[0][0] * e.x + G[0][1] * e.y + G[0][2] * e.z, G[1][0] * e.x + G[1][1] * e.y + G[1][2] * e.z,
                        G[2][0] * e.x + G[2][1] * e.y + G[2][2] * e.z};
        };
        SkyBandUbo u{};
        const Vec3 r = toSurvey(cam.right), up = toSurvey(cam.up), fw = toSurvey(cam.fwd);
        const double tx = cam.tanHalf * cam.aspect, ty = cam.tanHalf;
        const float rr[4] = {static_cast<float>(r.x * tx), static_cast<float>(r.y * tx), static_cast<float>(r.z * tx), 0};
        const float uu[4] = {static_cast<float>(up.x * ty), static_cast<float>(up.y * ty), static_cast<float>(up.z * ty), 0};
        const float ff[4] = {static_cast<float>(fw.x), static_cast<float>(fw.y), static_cast<float>(fw.z), 0};
        std::memcpy(u.right, rr, 16);
        std::memcpy(u.up, uu, 16);
        std::memcpy(u.fwd, ff, 16);
        u.scale[0] = static_cast<float>(info.lo);
        u.scale[1] = static_cast<float>(info.hi);
        u.scale[2] = info.scaleKind == "asinh" ? 2.0f : (info.scaleKind == "log" ? 1.0f : 0.0f);
        u.scale[3] = static_cast<float>(alpha);
        u.grid[0] = static_cast<float>(info.nside);
        u.grid[1] = static_cast<float>(levels_);
        u.grid[2] = static_cast<float>(2.0 * cam.tanHalf / height);
        const Vec3 er = toEq(cam.right), eu = toEq(cam.up), ef = toEq(cam.fwd);
        const Vec3* eqv[3] = {&er, &eu, &ef};
        float* dst[3] = {u.eqRight, u.eqUp, u.eqFwd};
        for (int k = 0; k < 3; ++k) {
            dst[k][0] = static_cast<float>(eqv[k]->x);
            dst[k][1] = static_cast<float>(eqv[k]->y);
            dst[k][2] = static_cast<float>(eqv[k]->z);
        }
        u.proj[0] = static_cast<float>(1.0 / (cam.tanHalf * cam.aspect));
        u.proj[1] = static_cast<float>(1.0 / cam.tanHalf);
        u.proj[2] = static_cast<float>(info.softness);
        u.proj[3] = 1.0f;      // grandeurs déjà rapportées à la médiane de leur catalogue (loadSources)
        // Seuil des sources selon le champ : environ kSourcesOnScreen par catalogue à l'écran, en supposant les sources
        // réparties sur tout le ciel ; on garde les plus fortes (flux mesuré), jamais un tirage au hasard.
        {
            const double a = std::atan(tx), bb = std::atan(ty);
            const double omega = 4.0 * std::asin(std::sin(a) * std::sin(bb));      // angle solide du champ (rectangle)
            const double keep = kSourcesOnScreen * 4.0 * kPi / std::max(omega, 1e-12);
            for (size_t k = 0; k < catalogs.size(); ++k) {
                SkySourcesInfo& c = catalogs[k];
                c.cut = 0;
                c.shown = c.count;
                if (!c.fixedSize && keep < c.sortedRel.size()) {
                    c.cut = c.sortedRel[static_cast<size_t>(keep)];
                    c.shown = static_cast<uint32_t>(keep);
                }
                if (k < 4) u.cut[k] = c.cut;
            }
        }
        u.grid[3] = static_cast<float>(height / 1080.0);
        if (tiles_.active) {      // tuiles fines : celles de l'écran sont demandées, celles qui sont lues sont envoyées
            requestTiles(cam, width, height, false);
            u.fine[0] = static_cast<float>(tiles_.orderMin);
            u.fine[1] = static_cast<float>(tiles_.orderMax);
            u.fine[2] = static_cast<float>(tiles_.logWidth);
            u.fine[3] = 1.0f;
        }
        std::memcpy(mapped_[ring_], &u, sizeof(u));
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        const VkRect2D sc{{0, 0}, {width, height}};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &sets_[ring_], 0, nullptr);
        vkCmdDraw(cmd, 3, 1, 0, 0);
        if (srcCount_ && showSources) {      // catalogue de la bande : un cercle par source, à sa direction mesurée
            vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipelineSrc_);
            vkCmdDraw(cmd, srcCount_, 1, 0, 0);
        }
        ring_ = (ring_ + 1) % kRing;
    }

    // Tuiles fines de cette vue : demandées (et envoyées si déjà lues) ; wait : attendre qu'elles soient toutes là
    // (essais hors écran). Les directions sont échantillonnées tous les 1/32 de largeur : une tuile au niveau voulu
    // couvre au moins « largeur » pixels de l'écran (512), aucune ne passe entre deux échantillons.
    void requestTiles(const Camera& cam, uint32_t width, uint32_t height, bool wait) {
        if (!tiles_.active || !gpu_) return;
        const Vec3 r = toSurvey(cam.right), up = toSurvey(cam.up), fw = toSurvey(cam.fwd);
        const double tx = cam.tanHalf * cam.aspect, ty = cam.tanHalf;
        std::vector<Vec3> dirs;
        const int nx = 32, ny = std::max(2, static_cast<int>(32.0 * height / std::max<uint32_t>(width, 1)));
        for (int j = 0; j <= ny; ++j)
            for (int i = 0; i <= nx; ++i) {
                const double x = -1.0 + 2.0 * i / nx, y = -1.0 + 2.0 * j / ny;
                dirs.push_back(Vec3{fw.x + x * r.x * tx - y * up.x * ty, fw.y + x * r.y * tx - y * up.y * ty, fw.z + x * r.z * tx - y * up.z * ty});
            }
        if (wait) tiles_.finish(*gpu_, dirs, fw, 2.0 * cam.tanHalf / height);
        else tiles_.update(*gpu_, dirs, fw, 2.0 * cam.tanHalf / height);
    }

    // Repère de l'appli (écliptique J2000) vers celui du relevé (équatorial ICRS ou galactique).
    Vec3 toSurvey(Vec3 v) const {
        const double eps = 84381.406 / 3600.0 * kPi / 180.0, ce = std::cos(eps), se = std::sin(eps);
        const Vec3 e{v.x, ce * v.y - se * v.z, se * v.y + ce * v.z};
        if (!info.galactic) return e;
        static const double G[3][3] = {{-0.0548755604162154, -0.8734370902348850, -0.4838350155487132},
                                       {+0.4941094278755837, -0.4448296299600112, +0.7469822444972189},
                                       {-0.8676661490190047, -0.1980763734312015, +0.4559837761750669}};
        return Vec3{G[0][0] * e.x + G[0][1] * e.y + G[0][2] * e.z, G[1][0] * e.x + G[1][1] * e.y + G[1][2] * e.z,
                    G[2][0] * e.x + G[2][1] * e.y + G[2][2] * e.z};
    }

    void release(const Gpu& g) {
        if (!ready) return;
        vkDeviceWaitIdle(g.dev);
        tiles_.close(g);
        if (loaded) destroy(g, map_);
        if (srcCount_) destroy(g, src_);
        destroy(g, dummy_);
        vkDestroyPipeline(g.dev, pipelineSrc_, nullptr);
        vkDestroyShaderModule(g.dev, vsSrc_, nullptr);
        vkDestroyShaderModule(g.dev, fsSrc_, nullptr);
        vkDestroyPipeline(g.dev, pipeline_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
        for (int i = 0; i < kRing; ++i) {
            vkUnmapMemory(g.dev, ubo_[i].mem);
            destroy(g, ubo_[i]);
        }
        ready = loaded = false;
    }

private:
    static constexpr int kRing = 4;
    static constexpr double kSourcesOnScreen = 1000.0;      // sources d'un catalogue à l'écran, à peu près, en champ large
    const Gpu* gpu_ = nullptr;
    SkyTileStream tiles_;
    uint32_t levels_ = 1;
    uint32_t srcCount_ = 0;
    Buffer map_{}, src_{}, dummy_{};
    VkPipeline pipelineSrc_{};
    VkShaderModule vsSrc_{}, fsSrc_{};
    Buffer ubo_[kRing];
    void* mapped_[kRing]{};
    VkDescriptorSet sets_[kRing]{};
    int ring_ = 0;
    VkPipeline pipeline_{};
    VkPipelineLayout layout_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkShaderModule vs_{}, fs_{};

    void createPipeline(const Gpu& g, VkFormat fmt) {
        const VkDescriptorSetLayoutBinding binds[5] = {{0, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 1, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, nullptr},
                                                       {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr},
                                                       {2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_VERTEX_BIT, nullptr},
                                                       {3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr},
                                                       {4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr}};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 5;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement du ciel par bande");
        const VkDescriptorPoolSize ps[2] = {{VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, kRing}, {VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 4 * kRing}};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = kRing;
        dp.poolSizeCount = 2;
        dp.pPoolSizes = ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve du ciel par bande");
        VkDescriptorSetLayout layouts[kRing];
        for (auto& l : layouts) l = setLayout_;
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = kRing;
        da.pSetLayouts = layouts;
        check(vkAllocateDescriptorSets(g.dev, &da, sets_), "jeux du ciel par bande");
        vs_ = shader(g, "ecran.vert.spv");      // un triangle qui couvre l'écran
        fs_ = shader(g, "ciel_bandes.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement du ciel par bande");
        VkPipelineVertexInputStateCreateInfo vin{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        VkPipelineInputAssemblyStateCreateInfo ia{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};
        ia.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
        VkPipelineViewportStateCreateInfo vps{VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO};
        vps.viewportCount = 1;
        vps.scissorCount = 1;
        const VkDynamicState dyn[2] = {VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR};
        VkPipelineDynamicStateCreateInfo ds{VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO};
        ds.dynamicStateCount = 2;
        ds.pDynamicStates = dyn;
        VkPipelineRasterizationStateCreateInfo rs{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO};
        rs.polygonMode = VK_POLYGON_MODE_FILL;
        rs.cullMode = VK_CULL_MODE_NONE;
        rs.lineWidth = 1.0f;
        VkPipelineMultisampleStateCreateInfo ms{VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO};
        ms.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;
        VkPipelineColorBlendAttachmentState att{};      // ajouté à ce qui est déjà là (fond noir : la carte seule)
        att.blendEnable = VK_TRUE;
        att.srcColorBlendFactor = VK_BLEND_FACTOR_ONE;
        att.dstColorBlendFactor = VK_BLEND_FACTOR_ONE;
        att.colorBlendOp = VK_BLEND_OP_ADD;
        att.srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
        att.dstAlphaBlendFactor = VK_BLEND_FACTOR_ZERO;
        att.alphaBlendOp = VK_BLEND_OP_ADD;
        att.colorWriteMask = 0xF;
        VkPipelineColorBlendStateCreateInfo cb{VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO};
        cb.attachmentCount = 1;
        cb.pAttachments = &att;
        VkPipelineRenderingCreateInfo rci{VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO};
        rci.colorAttachmentCount = 1;
        rci.pColorAttachmentFormats = &fmt;
        VkGraphicsPipelineCreateInfo pci{VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO, &rci};
        pci.stageCount = 2;
        pci.pStages = stages;
        pci.pVertexInputState = &vin;
        pci.pInputAssemblyState = &ia;
        pci.pViewportState = &vps;
        pci.pRasterizationState = &rs;
        pci.pMultisampleState = &ms;
        pci.pColorBlendState = &cb;
        pci.pDynamicState = &ds;
        pci.layout = layout_;
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline_), "pipeline du ciel par bande");
        // Même agencement pour les sources : des points (cercles) au lieu du triangle plein écran.
        vsSrc_ = shader(g, "ciel_sources.vert.spv");
        fsSrc_ = shader(g, "ciel_sources.frag.spv");
        stages[0].module = vsSrc_;
        stages[1].module = fsSrc_;
        ia.topology = VK_PRIMITIVE_TOPOLOGY_POINT_LIST;
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipelineSrc_), "pipeline des sources du ciel");
    }
};

}  // namespace
