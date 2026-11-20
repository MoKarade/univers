// Appli PC « Univers » : le trou noir au centre des galaxies (Marc, 20/11/2026 : « je veux voir le trou noir si je zoome
// sur la Voie lactée ou toute autre galaxie »).
//
// Masses MESURÉES (trous_noirs.tsv, pipeline/natif/trous_noirs.py) : Sagittarius A* (GRAVITY Collaboration 2022, orbites
// d'étoiles), M87* (Event Horizon Telescope 2019, ombre du trou noir) et la compilation de van den Bosch 2016 (ApJ 831, 134 :
// orbites stellaires, gaz, masers, réverbération). Chaque trou noir est relié à la galaxie de l'appli qui porte le même
// numéro Messier, NGC ou IC ; il est posé à la place de cette galaxie.
//
// Ce qui est dessiné (repère, pas sa lumière) : l'anneau de photons, à √27/2 ≈ 2,6 rayons de Schwarzschild du centre
// (relativité générale : rayon apparent de l'ombre d'un trou noir sans rotation) ; c'est la taille de l'anneau mesurée par
// l'Event Horizon Telescope pour M87* (42 ± 3 µas, EHT 2019, papier I) et Sgr A* (51,8 ± 2,3 µas, EHT 2022). Le centre reste
// noir : rien n'y est dessiné. L'éclat de l'anneau est un réglage d'affichage [supposé], pas une mesure.
// Les points sont donnés relativement à la caméra, calculés en double précision : le rayon de Schwarzschild de Sgr A* (0,08 UA)
// est bien plus petit que l'arrondi d'une position en simple précision à 26 000 années-lumière (~100 UA).
#pragma once
#include <cctype>
#include <cmath>
#include <fstream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include "simulation.h"

namespace {

// Numéros Messier, NGC, IC, UGC d'un nom (« Andromède (M31) » -> {« M31 »} ; « M87 (NGC 4486) » -> {« M87 », « NGC4486 »}).
inline std::set<std::string> catalogueKeys(const std::string& name) {
    std::set<std::string> out;
    const std::string pre[] = {"NGC", "IC", "UGC", "M"};
    for (size_t i = 0; i < name.size(); ++i) {
        if (i > 0 && std::isalpha(static_cast<unsigned char>(name[i - 1]))) continue;
        for (const std::string& p : pre) {
            if (name.compare(i, p.size(), p) != 0) continue;
            size_t j = i + p.size();
            while (j < name.size() && name[j] == ' ') ++j;
            size_t k = j;
            while (k < name.size() && std::isdigit(static_cast<unsigned char>(name[k]))) ++k;
            if (k > j && (k == name.size() || !std::isalnum(static_cast<unsigned char>(name[k])))) out.insert(p + name.substr(j, k - j));
            break;
        }
    }
    return out;
}

struct BlackHoles {
    struct Hole {
        int body = -1;
        double logMass = 0, errUp = 0, errDown = 0;
        bool upperLimit = false;
        std::string name, method, source;
        double rsLy() const { return 2.0 * 6.67430e-11 * std::pow(10.0, logMass) * 1.98892e30 / (299792458.0 * 299792458.0) / 9.4607304725808e15; }
    };
    std::vector<Hole> holes;
    static constexpr uint32_t kRingPoints = 720;
    Buffer vb[StarRenderer::kCols];
    float* cols[StarRenderer::kCols] = {};
    uint32_t count = 0;
    bool gpu = false;

    bool load(const std::string& path, Sim& sim) {
        std::ifstream f(path);
        if (!f) return false;
        std::string line;
        std::getline(f, line);      // en-tête
        int milkyWay = -1;
        for (size_t i = 0; i < sim.bodies.size(); ++i)
            if (sim.bodies[i].name == "Centre de la Voie lactée") milkyWay = static_cast<int>(i);
        while (std::getline(f, line)) {
            std::vector<std::string> c;
            std::stringstream ss(line);
            for (std::string x; std::getline(ss, x, '\t');) c.push_back(x);
            if (c.size() < 18 || c[14] != "1") continue;      // une seule valeur retenue par trou noir (colonne « prefere »)
            Hole h;
            h.name = c[0];
            h.logMass = std::atof(c[6].c_str());
            h.errUp = std::atof(c[7].c_str());
            h.errDown = std::atof(c[8].c_str());
            h.upperLimit = c[9] == "1";
            h.method = c[10];
            h.source = c[17];
            if (!(h.logMass > 2.0) || c[13] != "smbh") continue;
            if (h.name == "Sagittarius A*") h.body = milkyWay;
            else {
                const auto keys = catalogueKeys(c[1] + " " + c[0]);
                for (size_t i = 0; i < sim.bodies.size() && h.body < 0 && !keys.empty(); ++i) {
                    const Body& b = sim.bodies[i];
                    if (b.kind != Kind::Galaxy || b.structure || b.merged) continue;      // jamais un double fondu (caché)
                    for (const std::string& k : catalogueKeys(b.name))
                        if (keys.count(k)) { h.body = static_cast<int>(i); break; }
                }
            }
            if (h.body < 0) continue;
            Body& b = sim.bodies[static_cast<size_t>(h.body)];
            if (b.blackHole >= 0) continue;      // déjà relié
            b.blackHole = static_cast<int>(holes.size());
            b.blackHoleRsLy = h.rsLy();
            const double m = std::pow(10.0, h.logMass);
            const std::string mText = m >= 1e9 ? frNum(m / 1e9, 3) + " milliards de" : m >= 1e6 ? frNum(m / 1e6, 3) + " millions de" : frNum(m, 3);
            b.blackHoleText = (h.upperLimit ? "moins de " : "") + mText + " masses solaires (" + h.method + " ; " + h.source +
                              ") ; anneau de photons dessiné à 2,6 rayons de Schwarzschild (" + frDistance(2.6 * h.rsLy()) + "), éclat de l'anneau : réglage d'affichage";
            holes.push_back(h);
        }
        return !holes.empty();
    }

    void create(const Gpu& g) {
        for (int i = 0; i < StarRenderer::kCols; ++i) {
            vb[i] = createBuffer(g, kRingPoints * 4ull, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            void* p = nullptr;
            check(vkMapMemory(g.dev, vb[i].mem, 0, kRingPoints * 4ull, 0, &p), "tampon des trous noirs");
            cols[i] = static_cast<float*>(p);
        }
        gpu = true;
    }

    // Anneau du trou noir de l'astre suivi, tourné vers la caméra, si la caméra est à moins de 10⁶ rayons de Schwarzschild.
    void update(const Sim& sim, const Camera& cam) {
        count = 0;
        if (!gpu || sim.focus < 0) return;
        const Body& b = sim.bodies[static_cast<size_t>(sim.focus)];
        if (b.blackHole < 0 || !sim.visible(sim.focus)) return;
        const double rs = b.blackHoleRsLy;
        const Vec3 c = sim.position(sim.focus), rel{c.x - cam.pos.x, c.y - cam.pos.y, c.z - cam.pos.z};
        const double d = std::sqrt(dot(rel, rel));
        if (d > 1.0e6 * rs || d <= 0) return;
        const Vec3 v{rel.x / d, rel.y / d, rel.z / d};
        const Vec3 a = unit(cross(v, std::fabs(v.z) < 0.9 ? Vec3{0, 0, 1} : Vec3{1, 0, 0})), bb = cross(v, a);
        const double ring = std::sqrt(27.0) / 2.0 * rs;
        // Éclat : chaque point vu de la caméra garde la même magnitude apparente (repère, réglage d'affichage).
        const auto col = colorOfTemperature(4500.0);
        for (uint32_t i = 0; i < kRingPoints; ++i) {
            const double t = 2.0 * kPi * i / kRingPoints;
            const Vec3 p{rel.x + ring * (std::cos(t) * a.x + std::sin(t) * bb.x), rel.y + ring * (std::cos(t) * a.y + std::sin(t) * bb.y),
                         rel.z + ring * (std::cos(t) * a.z + std::sin(t) * bb.z)};
            const double dp = std::max(std::sqrt(dot(p, p)), 1e-15);
            cols[0][i] = static_cast<float>(p.x);
            cols[1][i] = static_cast<float>(p.y);
            cols[2][i] = static_cast<float>(p.z);
            cols[3][i] = static_cast<float>(1.0 - 5.0 * std::log10(dp / 3.2615638) + 5.0);      // magnitude apparente 1 [supposé]
            std::memcpy(&cols[4][i], col.data(), 4);
            cols[5][i] = cols[6][i] = cols[7][i] = 0;
        }
        count = kRingPoints;
    }

    // Constantes du dessin : positions relatives à la caméra (caméra à l'origine).
    void draw(VkCommandBuffer cmd, const StarRenderer& sr, PushConstants pc, uint32_t w, uint32_t h) const {
        if (!count) return;
        for (int a = 0; a < 3; ++a) pc.camHi[a] = pc.camLo[a] = 0.0f;
        pc.par[2] = 0.0f;
        sr.bind(cmd, pc, w, h);
        VkBuffer bufs[StarRenderer::kCols];
        VkDeviceSize offs[StarRenderer::kCols] = {};
        for (int i = 0; i < StarRenderer::kCols; ++i) bufs[i] = vb[i].buf;
        vkCmdBindVertexBuffers(cmd, 0, StarRenderer::kCols, bufs, offs);
        vkCmdDraw(cmd, count, 1, 0, 0);
    }

    void release(const Gpu& g) {
        if (!gpu) return;
        for (auto& b : vb) {
            vkUnmapMemory(g.dev, b.mem);
            destroy(g, b);
        }
    }
};

}  // namespace
