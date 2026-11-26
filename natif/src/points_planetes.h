// Appli PC « Univers » : les planètes et la Lune vues comme des points lumineux (avant les surfaces).
// Elles passent par le même dessin que les étoiles : on donne à chacune, à chaque image, la magnitude « absolue »
// qui, vue de la caméra, redonne exactement son éclat calculé (lumière du Soleil renvoyée, phase comprise).
#pragma once
#include "simulation.h"

namespace univers {

struct PlanetPoints {
    static constexpr uint32_t kMax = 32;
    Buffer vb[StarRenderer::kCols];
    float* cols[StarRenderer::kCols] = {};
    uint32_t count = 0, backCount = 0;      // les backCount premiers : derrière la sphère la plus proche (dessinés avant elle)

    void create(const Gpu& g) {
        for (int i = 0; i < StarRenderer::kCols; ++i) {
            vb[i] = createBuffer(g, kMax * 4, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            void* p = nullptr;
            check(vkMapMemory(g.dev, vb[i].mem, 0, kMax * 4, 0, &p), "tampon des planètes");
            cols[i] = static_cast<float*>(p);
            std::memset(p, 0, kMax * 4);
        }
    }

    // asSphere : astres déjà dessinés en sphère cette image (spheres.h) ; ils ne sont pas redessinés en point.
    // frontDist : distance de la sphère la plus proche ; les points plus proches qu'elle sont rangés à la fin et dessinés
    // après les sphères (audit E2 : une lune passant devant sa planète était cachée par le disque).
    void update(const Sim& sim, const Camera& cam, const std::vector<bool>& asSphere, double frontDist = 1e300) {
        count = 0;
        std::vector<std::pair<bool, int>> order;
        for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i) {
            const Body& b = sim.bodies[static_cast<size_t>(i)];
            if (b.kind != Kind::Planet || !b.hasPhotometry || asSphere[static_cast<size_t>(i)] || !sim.visible(i)) continue;      // visible : place connue (éphémérides) ou calculée
            const Vec3 d = sim.position(i) - cam.pos;
            order.push_back({std::sqrt(dot(d, d)) < frontDist, i});
        }
        std::stable_sort(order.begin(), order.end(), [](const auto& a, const auto& c) { return a.first < c.first; });
        backCount = 0;
        for (const auto& [front, i] : order) {
            if (count >= kMax) break;
            if (!front) ++backCount;
            const Body& b = sim.bodies[static_cast<size_t>(i)];
            const Vec3 p = sim.position(i), d = p - cam.pos;
            const double dist = std::max(std::sqrt(dot(d, d)), 1e-15);
            cols[0][count] = static_cast<float>(p.x);
            cols[1][count] = static_cast<float>(p.y);
            cols[2][count] = static_cast<float>(p.z);
            cols[3][count] = static_cast<float>(sim.apparentMag(i, cam.pos) - 5.0 * std::log10(dist / 3.2615638) + 5.0);
            // Teinte moyenne de la carte de surface ; sans carte (Pluton) : blanc, aucune teinte n'est avancée.
            const uint8_t c[4] = {static_cast<uint8_t>(b.tint[0] < 0 ? 255 : b.tint[0]), static_cast<uint8_t>(b.tint[1] < 0 ? 255 : b.tint[1]),
                                  static_cast<uint8_t>(b.tint[2] < 0 ? 255 : b.tint[2]), 255};
            std::memcpy(&cols[4][count], c, 4);
            cols[5][count] = cols[6][count] = cols[7][count] = 0;
            ++count;
        }
        // Le Soleil au-delà de l'ère des étoiles mesurées (cycle_appli.h, sunAlways) : le catalogue ne le dessine plus ; son
        // point, à l'éclat et à la couleur de la date montrée, quand il n'est pas déjà une sphère.
        const Body& sun = sim.bodies[0];
        if (count < kMax && sim.sunAlways && sim.starShare() <= 0 && sun.lifeOn && sun.lifeAbsMag < 90 && !asSphere[0]) {
            cols[0][count] = cols[1][count] = cols[2][count] = 0;
            cols[3][count] = static_cast<float>(sun.lifeAbsMag);
            const auto c = colorOfBv(sun.lifeBv);
            std::memcpy(&cols[4][count], c.data(), 4);
            cols[5][count] = cols[6][count] = cols[7][count] = 0;
            ++count;
        }
    }

    // À appeler juste après StarRenderer::draw (même pipeline, mêmes constantes). front : les points devant les sphères.
    void draw(VkCommandBuffer cmd, bool front = false) const {
        const uint32_t first = front ? backCount : 0, n = front ? count - backCount : backCount;
        if (!n) return;
        VkBuffer bufs[StarRenderer::kCols];
        VkDeviceSize offs[StarRenderer::kCols];
        for (int i = 0; i < StarRenderer::kCols; ++i) {
            bufs[i] = vb[i].buf;
            offs[i] = 0;
        }
        vkCmdBindVertexBuffers(cmd, 0, StarRenderer::kCols, bufs, offs);
        vkCmdDraw(cmd, n, 1, first, 0);
    }

    void release(const Gpu& g) {
        for (auto& b : vb) {
            vkUnmapMemory(g.dev, b.mem);
            destroy(g, b);
        }
    }
};

}  // namespace univers