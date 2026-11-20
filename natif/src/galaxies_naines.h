// Appli PC « Univers » : les galaxies naines nommées qui n'avaient rien à l'écran (Marc, 20/11/2026 : « je clique sur une
// galaxie, je zoome et je vois rien »).
//
// Paramètres MESURÉS (naines.tsv, pipeline/natif/naines.py, Local Volume Database de Pace 2024 et ses références) : rayon de
// demi-lumière, ellipticité, angle de position sur le ciel, magnitude absolue V. Nuage d'étoiles tiré de ces paramètres
// [MODÈLE, dit à l'écran] : profil de Plummer (Plummer 1911) dont le rayon de demi-lumière projeté est celui mesuré ;
// aplati sur le ciel selon l'ellipticité et l'angle mesurés ; épaisseur le long de la ligne de visée égale au petit axe
// [supposé] ; couleur d'une population vieille (B - V = 0,7) [supposé] ; la lumière totale est celle mesurée, partagée
// également entre les points. Chaque galaxie est posée à la place de l'astre de l'appli (Sim::position).
#pragma once
#include <cmath>
#include <fstream>
#include <random>
#include <sstream>
#include <string>
#include <vector>

#include "simulation.h"

namespace {

struct DwarfGalaxies {
    // Points par galaxie : 3 000, jusqu'à 30 000 pour les plus brillantes (moins de lumière par point, grain plus fin).
    static uint32_t pointsFor(double absMagV) { return static_cast<uint32_t>(std::clamp(3000.0 * std::pow(10.0, -0.4 * (absMagV + 10.0)), 3000.0, 30000.0)); }
    struct Dwarf {
        int body = -1;
        double rhLy, ellipticity, paDeg, absMagV;
        std::string refs;
    };
    std::vector<Dwarf> dwarfs;
    Buffer vb[StarRenderer::kCols];
    float* cols[StarRenderer::kCols] = {};
    uint32_t capacity = 0, count = 0;
    std::vector<Vec3> placedAt;      // place de chaque naine lors du dernier remplissage (repère du simulateur)

    // Lit naines.tsv et relie chaque ligne à l'astre de même nom. false si le fichier manque.
    bool load(const Gpu& g, const std::string& path, Sim& sim) {
        std::ifstream f(path);
        if (!f) return false;
        for (std::string line; std::getline(f, line);) {
            if (line.empty() || line[0] == '#') continue;
            std::vector<std::string> c;
            std::stringstream ss(line);
            for (std::string x; std::getline(ss, x, '\t');) c.push_back(x);
            if (c.size() < 5) continue;
            Dwarf d{-1, std::atof(c[1].c_str()), std::atof(c[2].c_str()), std::atof(c[3].c_str()), std::atof(c[4].c_str()),
                    c.size() >= 8 ? c[5] + " ; " + c[6] + " ; " + c[7] : ""};
            for (size_t i = 0; i < sim.bodies.size(); ++i)
                if (sim.bodies[i].kind == Kind::Galaxy && !sim.bodies[i].merged && sim.bodies[i].name == c[0]) d.body = static_cast<int>(i);
            if (d.body >= 0 && d.rhLy > 0) {
                sim.bodies[static_cast<size_t>(d.body)].dwarfModel = static_cast<int>(dwarfs.size());
                sim.bodies[static_cast<size_t>(d.body)].shapeRadiusLy = d.rhLy;
                sim.bodies[static_cast<size_t>(d.body)].shapeNote =
                    "Forme dessinée : MODÈLE (profil de Plummer, " + frInt(pointsFor(d.absMagV)) + " points) tiré de valeurs MESURÉES : rayon de demi-lumière " +
                    frDistance(d.rhLy) + ", ellipticité " + frNum(d.ellipticity, 2) + ", magnitude absolue " + frNum(d.absMagV, 3) +
                    (d.absMagV > -5 ? ". Galaxie ultra-pâle : sa lumière totale est celle de quelques centaines de soleils, à peine visible même de près" : "") + ". Épaisseur et couleur supposées. Sources : " + d.refs + " (Local Volume Database, Pace 2024).";
                dwarfs.push_back(d);
            }
        }
        if (dwarfs.empty()) return false;
        capacity = 0;
        for (const Dwarf& d : dwarfs) capacity += pointsFor(d.absMagV);
        for (int i = 0; i < StarRenderer::kCols; ++i) {
            vb[i] = createBuffer(g, capacity * 4ull, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            void* p = nullptr;
            check(vkMapMemory(g.dev, vb[i].mem, 0, capacity * 4ull, 0, &p), "tampon des galaxies naines");
            cols[i] = static_cast<float*>(p);
        }
        placedAt.assign(dwarfs.size(), {1e300, 1e300, 1e300});
        return true;
    }

    // Remplit le tampon quand une naine a bougé (ou est apparue / disparue). Les galaxies ne bougent qu'aux dates lointaines.
    void update(const Sim& sim) {
        if (dwarfs.empty()) return;
        bool moved = false;
        for (size_t k = 0; k < dwarfs.size() && !moved; ++k) {
            const Vec3 p = sim.visible(dwarfs[k].body) ? sim.position(dwarfs[k].body) : Vec3{1e300, 1e300, 1e300};
            const Vec3 d = p - placedAt[k];
            moved = !(dot(d, d) < 1.0);
        }
        if (!moved) return;
        count = 0;
        // Pôle nord de l'équateur céleste dans le repère de l'appli (écliptique J2000, obliquité 23,4393°, UAI 2006).
        const double eps = 23.4392911 * kPi / 180.0;
        const Vec3 pole{0.0, -std::sin(eps), std::cos(eps)};
        for (size_t k = 0; k < dwarfs.size(); ++k) {
            const Dwarf& w = dwarfs[k];
            if (!sim.visible(w.body)) {
                placedAt[k] = {1e300, 1e300, 1e300};
                continue;
            }
            const Vec3 c = sim.position(w.body);
            placedAt[k] = c;
            const double dist = std::sqrt(dot(c, c));
            if (dist <= 0) continue;
            const Vec3 los{c.x / dist, c.y / dist, c.z / dist};
            const Vec3 east = unit(cross(pole, los)), north = cross(los, east);
            const double pa = w.paDeg * kPi / 180.0;
            const Vec3 major{std::cos(pa) * north.x + std::sin(pa) * east.x, std::cos(pa) * north.y + std::sin(pa) * east.y, std::cos(pa) * north.z + std::sin(pa) * east.z};
            const Vec3 minor = cross(los, major);
            const double q = std::clamp(1.0 - w.ellipticity, 0.05, 1.0);
            // Plummer : rayon de demi-lumière projeté = a (rayon d'échelle) ; on garde le rayon moyen géométrique
            // (a_maj · a_min = rh²), comme les mesures de rayon elliptique (rh sur le grand axe : a_maj = rh).
            const double aMaj = w.rhLy, aMin = w.rhLy * q;
            const uint32_t npts = pointsFor(w.absMagV);
            const float mag = static_cast<float>(w.absMagV + 2.5 * std::log10(static_cast<double>(npts)));
            const auto col = colorOfBv(0.7);
            std::mt19937 rng(static_cast<uint32_t>(k) * 2654435761u + 7u);
            std::uniform_real_distribution<double> U(1e-9, 1.0);
            for (uint32_t i = 0; i < npts && count < capacity; ++i) {
                const double u = U(rng), r = 1.0 / std::sqrt(std::pow(u, -2.0 / 3.0) - 1.0);      // Plummer, a = 1 ; coupé plus bas
                if (r > 10.0) { --i; continue; }
                const double cz = 2.0 * U(rng) - 1.0, ph = 2.0 * kPi * U(rng), s = std::sqrt(1.0 - cz * cz);
                const double x = r * s * std::cos(ph) * aMaj, y = r * s * std::sin(ph) * aMin, z = r * cz * aMin;
                cols[0][count] = static_cast<float>(c.x + x * major.x + y * minor.x + z * los.x);
                cols[1][count] = static_cast<float>(c.y + x * major.y + y * minor.y + z * los.y);
                cols[2][count] = static_cast<float>(c.z + x * major.z + y * minor.z + z * los.z);
                cols[3][count] = mag;
                std::memcpy(&cols[4][count], col.data(), 4);
                cols[5][count] = cols[6][count] = cols[7][count] = 0;
                ++count;
            }
        }
    }

    // À appeler après StarRenderer::bind (même pipeline que les étoiles ; constantes sans mouvement propre).
    void draw(VkCommandBuffer cmd) const {
        if (!count) return;
        VkBuffer bufs[StarRenderer::kCols];
        VkDeviceSize offs[StarRenderer::kCols] = {};
        for (int i = 0; i < StarRenderer::kCols; ++i) bufs[i] = vb[i].buf;
        vkCmdBindVertexBuffers(cmd, 0, StarRenderer::kCols, bufs, offs);
        vkCmdDraw(cmd, count, 1, 0, 0);
    }

    void release(const Gpu& g) {
        if (!capacity) return;
        for (auto& b : vb) {
            vkUnmapMemory(g.dev, b.mem);
            destroy(g, b);
        }
    }
};

}  // namespace
