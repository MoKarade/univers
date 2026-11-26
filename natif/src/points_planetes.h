// Appli PC « Univers » : les planètes et la Lune vues comme des points lumineux (avant les surfaces).
// Elles passent par le même dessin que les étoiles : on donne à chacune, à chaque image, la magnitude « absolue »
// qui, vue de la caméra, redonne exactement son éclat calculé (lumière du Soleil renvoyée, phase comprise).
#pragma once
#include "simulation.h"

namespace univers {

// Convertit une composante sRGB 8 bits (planetes.tsv, CEI 61966-2-1) en lumière linéaire 8 bits pour etoiles.vert.
// Valeur négative (astre sans carte, ex. Pluton) : blanc (255).
inline uint8_t srgbByteToLinear(int v) {
    if (v < 0) return 255;
    const double s = std::clamp(static_cast<double>(v), 0.0, 255.0) / 255.0;
    const double lin = s <= 0.04045 ? s / 12.92 : std::pow((s + 0.055) / 1.055, 2.4);
    return static_cast<uint8_t>(std::lround(255.0 * std::clamp(lin, 0.0, 1.0)));
}

struct PlanetPoints {
    static constexpr uint32_t kMax = 32;
    Buffer vb[StarRenderer::kCols]{};
    float* cols[StarRenderer::kCols] = {};
    uint32_t count = 0;

    void create(const Gpu& g) {
        for (int i = 0; i < StarRenderer::kCols; ++i) {
            vb[i] = createBuffer(g, kMax * 4, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                                 VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            void* p = nullptr;
            check(vkMapMemory(g.dev, vb[i].mem, 0, kMax * 4, 0, &p), "tampon des planètes");
            cols[i] = static_cast<float*>(p);
            std::memset(p, 0, kMax * 4);
        }
    }

    // asSphere : astres déjà dessinés en sphère cette image (spheres.h) ; ils ne sont pas redessinés en point.
    void update(const Sim& sim, const Camera& cam, const std::vector<bool>& asSphere) {
        count = 0;
        for (int i = 0; i < static_cast<int>(sim.bodies.size()) && count < kMax; ++i) {
            const Body& b = sim.bodies[static_cast<size_t>(i)];
            if (b.kind != Kind::Planet || !b.hasPhotometry || !sim.visible(i) ||
                (static_cast<size_t>(i) < asSphere.size() && asSphere[static_cast<size_t>(i)])) {
                continue;
            }
            const Vec3 p = sim.position(i), d = p - cam.pos;
            const double dist = std::max(std::sqrt(dot(d, d)), 1e-15);
            cols[0][count] = static_cast<float>(p.x);
            cols[1][count] = static_cast<float>(p.y);
            cols[2][count] = static_cast<float>(p.z);
            cols[3][count] = static_cast<float>(sim.apparentMag(i, cam.pos) - 5.0 * std::log10(dist / 3.2615638) + 5.0);
            // Teinte moyenne de la carte de surface (sRGB -> linéaire) ; sans carte (Pluton) : blanc, aucune teinte n'est avancée.
            const uint8_t c[4] = {srgbByteToLinear(b.tint[0]), srgbByteToLinear(b.tint[1]), srgbByteToLinear(b.tint[2]),
                                  255};
            std::memcpy(&cols[4][count], c, 4);
            cols[5][count] = cols[6][count] = cols[7][count] = 0;
            ++count;
        }
    }

    // À appeler juste après StarRenderer::draw (même pipeline, mêmes constantes).
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
        for (auto& b : vb) {
            vkUnmapMemory(g.dev, b.mem);
            destroy(g, b);
        }
    }
};

}  // namespace univers
