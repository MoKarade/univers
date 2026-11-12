// Appli PC « Univers » : les objets MESURÉS qui tracent les bras spiraux de la Voie lactée, sur toute la Galaxie.
//
// Retour de Marc (12 novembre 2026) : « la spirale devrait avoir 2 ou 4 bras ; tu n'as pas utilisé les vraies données ».
// Gaia ne mesure bien que le voisinage du Soleil. Les bras sont tracés par d'autres mesures publiées, lues dans
// traceurs_bras.tsv (pipeline/natif/traceurs_bras.py, qui cite ses sources) : masers à parallaxe radio (Reid et al.
// 2019) et amas ouverts datés (Hunt & Reffert 2023). Ici, un point par objet, à sa place mesurée :
//   - masers : rose (régions où naissent des étoiles massives : elles jalonnent les bras) ;
//   - amas de moins de 100 millions d'années : bleu-blanc (trop jeunes pour avoir quitté leur bras) ;
//   - amas plus vieux : gris, plus faibles (ils se sont déjà dispersés dans le disque).
// Les couleurs sont un code de légende, pas une mesure ; la taille est fixe à l'écran ; vus d'au moins 1 000 al.
// Dans le temps (choix de Marc, 12 novembre 2026 : « 1 et 2 ») : le dessin des bras est une onde qui tourne d'un bloc
// autour du centre de la Galaxie, à la vitesse mesurée de 28,2 ± 2,1 km/s par kpc (Dias et al. 2019, MNRAS 486, 5726,
// arXiv:1905.08133, d'après les amas jeunes de Gaia DR2). Les traceurs mesurés aujourd'hui tournent donc ensemble à
// cette vitesse : c'est CALCULÉ (le dessin d'aujourd'hui, tourné), montré tel quel jusqu'à 200 millions d'années, puis
// éteint progressivement jusqu'à 400 millions (au-delà, le dessin se déforme : c'est le calcul complet de la Galaxie,
// fait par le fil physique, qui prend le relais).
#pragma once
#include <algorithm>
#include <cmath>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "simulation.h"

namespace {

struct ArmTracerPoints {
    Buffer vb[StarRenderer::kCols];
    float* cols[StarRenderer::kCols] = {};
    uint32_t capacity = 0, count = 0;
    std::vector<ArmTracer> tracers;
    std::vector<Vec3> world;               // places à l'écran à la date montrée (années-lumière), pour les noms et le clic
    std::vector<phys::Vec3> galactic;      // places d'aujourd'hui par rapport au centre de la Galaxie (kpc)
    static constexpr double kPatternKmsKpc = 28.2, kPatternErrorKmsKpc = 2.1;      // Dias et al. 2019
    static constexpr double kFullYears = 2.0e8, kEndYears = 4.0e8;
    bool ready = false;

    bool create(const Gpu& g, const std::string& path) {
        std::ifstream f(path);
        for (std::string line; std::getline(f, line);) {
            std::vector<std::string> c;
            std::stringstream ss(line);
            for (std::string cell; std::getline(ss, cell, '\t');) c.push_back(cell);
            if (c.size() < 8) continue;
            ArmTracer t;
            t.name = c[0];
            t.pos = {std::atof(c[1].c_str()), std::atof(c[2].c_str()), std::atof(c[3].c_str())};
            t.maser = c[4] == "maser";
            t.arm = c[5];
            t.ageMyr = std::atof(c[6].c_str());
            t.distanceError = std::atof(c[7].c_str());
            tracers.push_back(t);
        }
        if (tracers.empty()) return false;
        capacity = static_cast<uint32_t>(tracers.size());
        for (int i = 0; i < StarRenderer::kCols; ++i) {
            vb[i] = createBuffer(g, static_cast<VkDeviceSize>(capacity) * 4, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                                 VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            void* p = nullptr;
            check(vkMapMemory(g.dev, vb[i].mem, 0, static_cast<VkDeviceSize>(capacity) * 4, 0, &p), "tampon des traceurs des bras");
            cols[i] = static_cast<float*>(p);
            std::memset(p, 0, static_cast<size_t>(capacity) * 4);
        }
        static const uint8_t maser[4] = {255, 120, 170, 255}, young[4] = {170, 205, 255, 255}, old[4] = {150, 150, 150, 255};
        for (uint32_t i = 0; i < capacity; ++i) {
            const ArmTracer& t = tracers[i];
            std::memcpy(&cols[4][i], t.maser ? maser : t.ageMyr < 100.0 ? young : old, 4);
            cols[0][i] = static_cast<float>(t.pos.x);
            cols[1][i] = static_cast<float>(t.pos.y);
            cols[2][i] = static_cast<float>(t.pos.z);
        }
        const phys::Vec3 s = phys::galaxie::soleilPos();
        galactic.resize(capacity);
        world.resize(capacity);
        for (uint32_t i = 0; i < capacity; ++i) {
            const phys::Vec3 g = orbite::versGalactique(tracers[i].pos);
            galactic[i] = {g.x / orbite::kKpcLy + s.x, g.y / orbite::kKpcLy + s.y, g.z / orbite::kKpcLy + s.z};
        }
        ready = true;
        return true;
    }

    // Part montrée : pleine jusqu'à 200 millions d'années d'aujourd'hui, nulle au-delà de 400 millions.
    static double shareAt(double yearsFromToday) { return std::clamp((kEndYears - std::fabs(yearsFromToday)) / (kEndYears - kFullYears), 0.0, 1.0); }

    // centre : place à l'écran du centre de la Galaxie à cette date (années-lumière).
    void update(const Camera& cam, Vec3 centre, double yearsFromToday, double viewDistLy, float exposure) {
        count = 0;
        if (!ready) return;
        const double share = shareAt(yearsFromToday) * std::clamp(std::log10(std::max(viewDistLy, 1.0)) - 3.0, 0.0, 1.0);
        if (share <= 0) return;
        // Rotation d'un bloc autour de l'axe de la Galaxie, dans le sens de la rotation des étoiles (angle décroissant dans
        // ce repère, comme le Soleil).
        const double angle = -kPatternKmsKpc * phys::galaxie::kKmsKpcToRadGa * yearsFromToday / 1.0e9, ca = std::cos(angle), sa = std::sin(angle);
        for (uint32_t i = 0; i < capacity; ++i) {
            const ArmTracer& t = tracers[i];
            const phys::Vec3& g0 = galactic[i];
            const Vec3 e = orbite::versEcliptique({(g0.x * ca - g0.y * sa) * orbite::kKpcLy, (g0.x * sa + g0.y * ca) * orbite::kKpcLy, g0.z * orbite::kKpcLy});
            const Vec3 w{centre.x + e.x, centre.y + e.y, centre.z + e.z};
            world[i] = w;
            cols[0][i] = static_cast<float>(w.x);
            cols[1][i] = static_cast<float>(w.y);
            cols[2][i] = static_cast<float>(w.z);
            const Vec3 d = w - cam.pos;
            const double dist = std::max(std::sqrt(dot(d, d)), 1e-9);
            const double flux = (t.maser ? 8.0 : t.ageMyr < 100.0 ? 0.6 : 0.03) * share;      // éclat d'affichage, pas une mesure
            cols[3][i] = static_cast<float>(-2.5 * std::log10(flux / exposure) - 5.0 * std::log10(dist / 3.2615638) + 5.0);
        }
        count = capacity;
    }

    // À appeler quand le dessin des étoiles est lié avec un temps écoulé nul (comme les scénarios du Groupe local).
    void draw(VkCommandBuffer cmd) const {
        if (!count) return;
        VkBuffer bufs[StarRenderer::kCols];
        VkDeviceSize offs[StarRenderer::kCols];
        for (int i = 0; i < StarRenderer::kCols; ++i) {
            bufs[i] = vb[i].buf;
            offs[i] = 0;
        }
        vkCmdBindVertexBuffers(cmd, 0, StarRenderer::kCols, bufs, offs);
        vkCmdDraw(cmd, count, 1, 0, 0);
    }

    void release(const Gpu& g) {
        if (!ready) return;
        for (auto& b : vb) {
            vkUnmapMemory(g.dev, b.mem);
            destroy(g, b);
        }
        ready = false;
    }
};

}  // namespace
