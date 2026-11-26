// Appli PC « Univers » : le nuage des 10 000 scénarios (« clones ») du Groupe local, calculés par le fil physique.
//
// La rencontre de la Voie lactée et d'Andromède n'est pas certaine : elle dépend de mesures entachées d'incertitude
// (distances, vitesses, masses). Le fil physique a tiré 10 000 jeux de valeurs dans ces incertitudes et calculé à
// l'avance la route des quatre galaxies (Voie lactée, Andromède, Triangle, Grand Nuage) pour chacun
// (clones_groupe_local.bin, format décrit dans pipeline/fusion/clones_bin.py). Ici : à la date montrée, un point par
// scénario et par galaxie, placé par rapport au centre de la Voie lactée de l'écran. Le nuage dit l'incertitude : serré
// aujourd'hui (mesures), de plus en plus étalé dans l'avenir. C'est précalculé, pas mesuré : l'écran le dit.
// Montré dans l'avenir seulement (le calcul part d'aujourd'hui) et vu d'assez loin (au-delà de 100 000 années-lumière).
#pragma once
#include <algorithm>
#include <cmath>

#include "simulation.h"

namespace univers {

struct ClonePoints {
    Buffer vb[StarRenderer::kCols];
    float* cols[StarRenderer::kCols] = {};
    uint32_t capacity = 0, count = 0;
    HANDLE file = INVALID_HANDLE_VALUE, mapping = nullptr;
    const uint8_t* base = nullptr;
    uint32_t n = 0, galaxies = 0, images = 0;
    float stepGa = 0, quantumKpc = 0, probability = 0;
    const int16_t* positions = nullptr;      // images x n x galaxies x 3
    const float* absorbed = nullptr;         // n x galaxies : date (Ga) où la galaxie est absorbée dans ce scénario, NaN sinon
    double t16 = 0, t50 = 0, t84 = 0;        // date de la fusion Voie lactée-Andromède : 16e, 50e, 84e centile (Ga), parmi les scénarios qui fusionnent
    bool ready = false;

    bool create(const Gpu& g, const std::string& path) {
        file = CreateFileA(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file == INVALID_HANDLE_VALUE) return false;
        LARGE_INTEGER size;
        GetFileSizeEx(file, &size);
        mapping = CreateFileMappingA(file, nullptr, PAGE_READONLY, 0, 0, nullptr);
        base = mapping ? static_cast<const uint8_t*>(MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 0)) : nullptr;
        if (!base || size.QuadPart < 64) return false;
        const bool v2 = std::memcmp(base, "UNIVCLN2", 8) == 0;      // v2 : dates d'absorption (clones_bin.py)
        if (!v2 && std::memcmp(base, "UNIVCLN1", 8) != 0) return false;
        std::memcpy(&n, base + 8, 4);
        std::memcpy(&galaxies, base + 12, 4);
        std::memcpy(&images, base + 16, 4);
        std::memcpy(&stepGa, base + 20, 4);
        std::memcpy(&quantumKpc, base + 24, 4);
        std::memcpy(&probability, base + 28, 4);
        const uint64_t absorbedAt = 64 + 8ull * galaxies + 4ull * n + 4ull * n * galaxies;
        const uint64_t head = absorbedAt + (v2 ? 4ull * n * galaxies : 0);
        if (galaxies < 2 || !n || !images || static_cast<uint64_t>(size.QuadPart) < head + 6ull * images * n * galaxies) return false;
        positions = reinterpret_cast<const int16_t*>(base + head);
        absorbed = v2 ? reinterpret_cast<const float*>(base + absorbedAt) : nullptr;
        std::vector<float> t;
        for (uint32_t k = 0; k < n; ++k) {
            float v;
            std::memcpy(&v, base + 64 + 8ull * galaxies + 4ull * k, 4);
            if (std::isfinite(v)) t.push_back(v);
        }
        std::sort(t.begin(), t.end());
        if (!t.empty()) {
            t16 = t[t.size() * 16 / 100];
            t50 = t[t.size() / 2];
            t84 = t[t.size() * 84 / 100];
        }
        capacity = n * (galaxies - 1);
        for (int i = 0; i < StarRenderer::kCols; ++i) {
            vb[i] = createBuffer(g, static_cast<VkDeviceSize>(capacity) * 4, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                                 VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            void* p = nullptr;
            check(vkMapMemory(g.dev, vb[i].mem, 0, static_cast<VkDeviceSize>(capacity) * 4, 0, &p), "tampon des scénarios");
            cols[i] = static_cast<float*>(p);
            std::memset(p, 0, static_cast<size_t>(capacity) * 4);
        }
        // Une teinte par galaxie, pour suivre chaque nuage : Andromède bleutée, Triangle verte, Grand Nuage orangée.
        static const uint8_t tint[3][4] = {{150, 190, 255, 255}, {150, 255, 170, 255}, {255, 190, 120, 255}};
        for (uint32_t k = 0; k < n; ++k)
            for (uint32_t gal = 1; gal < galaxies; ++gal) std::memcpy(&cols[4][k * (galaxies - 1) + gal - 1], tint[(gal - 1) % 3], 4);
        ready = true;
        return true;
    }

    // centre : place à l'écran du centre de la Voie lactée (années-lumière) ; tGa : milliards d'années depuis aujourd'hui.
    void update(const Camera& cam, Vec3 centre, double tGa, double viewDistLy, float exposure) {
        count = 0;
        if (!ready || tGa < 0 || tGa > (images - 1) * static_cast<double>(stepGa)) return;
        const double fade = std::clamp((std::log10(std::max(viewDistLy, 1.0)) - 5.0) / 0.7, 0.0, 1.0);      // de 100 000 à 500 000 al
        if (fade <= 0) return;
        const double x = tGa / stepGa;
        const uint32_t i = std::min(static_cast<uint32_t>(x), images - 2);
        const double f = x - i;
        const int16_t* a = positions + static_cast<size_t>(i) * n * galaxies * 3;
        const int16_t* b = a + static_cast<size_t>(n) * galaxies * 3;
        const double q = static_cast<double>(quantumKpc) * orbite::kKpcLy;
        const double mApp = -2.5 * std::log10(0.25 * fade / exposure);
        for (uint32_t k = 0; k < n; ++k) {
            const int16_t* pa = a + static_cast<size_t>(k) * galaxies * 3;
            const int16_t* pb = b + static_cast<size_t>(k) * galaxies * 3;
            double mw[3];
            for (int c = 0; c < 3; ++c) mw[c] = pa[c] + (pb[c] - pa[c]) * f;
            for (uint32_t gal = 1; gal < galaxies; ++gal) {
                phys::Vec3 rel;
                double r[3];
                for (int c = 0; c < 3; ++c) r[c] = (pa[gal * 3 + c] + (pb[gal * 3 + c] - pa[gal * 3 + c]) * f - mw[c]) * q;
                rel = {r[0], r[1], r[2]};
                const Vec3 e = orbite::versEcliptique(rel);
                const Vec3 w{centre.x + e.x, centre.y + e.y, centre.z + e.z};
                const Vec3 d = w - cam.pos;
                const double dist = std::max(std::sqrt(dot(d, d)), 1e-9);
                const uint32_t o = k * (galaxies - 1) + gal - 1;
                cols[0][o] = static_cast<float>(w.x);
                cols[1][o] = static_cast<float>(w.y);
                cols[2][o] = static_cast<float>(w.z);
                // Galaxie absorbée dans ce scénario (centres à moins de 20 kpc, règle de Sawala et al. 2025) : le point
                // n'est plus montré, au lieu d'être recollé en ligne droite au centre de celle qui l'absorbe.
                const float ta = absorbed ? absorbed[static_cast<size_t>(k) * galaxies + gal] : NAN;
                const bool gone = std::isfinite(ta) && tGa >= static_cast<double>(ta) - stepGa;
                cols[3][o] = gone ? 99.0f : static_cast<float>(mApp - 5.0 * std::log10(dist / 3.2615638) + 5.0);
            }
        }
        count = capacity;
    }

    // À appeler quand le dessin des étoiles est lié avec un temps écoulé nul (comme FusionPoints).
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
        if (ready)
            for (auto& b : vb) {
                vkUnmapMemory(g.dev, b.mem);
                destroy(g, b);
            }
        if (base) UnmapViewOfFile(base);
        if (mapping) CloseHandle(mapping);
        if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
        ready = false;
    }
};

}  // namespace univers