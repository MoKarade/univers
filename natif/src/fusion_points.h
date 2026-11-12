// Appli PC « Univers » : les étoiles du calcul de la fusion avec Andromède (phys::fusion::Rejeu), montrées seulement dans
// l'avenir (au-delà de 3 millions d'années) : c'est une évolution calculée, pas un état mesuré.
// Chaque particule du calcul est un point de taille d'affichage fixe (ce n'est pas une étoile mesurée) ; elles passent
// par le dessin des étoiles, avec la magnitude qui donne ce même éclat à l'écran quelle que soit la distance.
#pragma once
#include "simulation.h"

namespace {

struct FusionPoints {
    Buffer vb[StarRenderer::kCols];
    float* cols[StarRenderer::kCols] = {};
    uint32_t capacity = 0, count = 0;
    std::vector<phys::Vec3> scratch;
    std::vector<Vec3> world;      // positions du simulateur (années-lumière), recalculées quand la date change
    double worldAtGa = -1;

    void create(const Gpu& g, uint32_t n) {
        capacity = n;
        if (!n) return;
        scratch.resize(n);
        world.resize(n);
        for (int i = 0; i < StarRenderer::kCols; ++i) {
            vb[i] = createBuffer(g, static_cast<VkDeviceSize>(n) * 4, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                                 VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            void* p = nullptr;
            check(vkMapMemory(g.dev, vb[i].mem, 0, static_cast<VkDeviceSize>(n) * 4, 0, &p), "tampon des étoiles de la fusion");
            cols[i] = static_cast<float*>(p);
            std::memset(p, 0, static_cast<size_t>(n) * 4);
        }
        const uint8_t white[4] = {255, 255, 255, 255};      // aucune teinte n'est avancée
        for (uint32_t i = 0; i < n; ++i) std::memcpy(&cols[4][i], white, 4);
    }

    // exposure : celle du dessin des étoiles pour cette image (éclat multiplié compris).
    void update(const Sim& sim, const Camera& cam, float exposure) {
        count = 0;
        const double share = 1.0 - sim.starShare();      // les étoiles mesurées occupent le reste (Sim::starShare)
        if (!capacity || !sim.replay || share <= 0) return;
        const Vec3 shift = sim.sunShift();
        const double tGa = sim.replayGa();
        if (tGa != worldAtGa) {
            if (!sim.replay->etoilesA(tGa, scratch)) { worldAtGa = -1; return; }
            for (uint32_t i = 0; i < capacity; ++i) world[i] = Sim::fromGalactocentric(scratch[i]);
            worldAtGa = tGa;
        }
        // Éclat d'affichage : 0,35 par point, éteint progressivement quand on regarde de trop près (moins de 3 000 al).
        const double fade = std::clamp((std::log10(std::max(sim.dist, 1.0)) - 3.5) / 1.0, 0.0, 1.0);
        if (fade <= 0) return;
        const double mApp = -2.5 * std::log10(0.35 * fade * share / exposure);
        for (uint32_t i = 0; i < capacity; ++i) {
            const Vec3 w{world[i].x + shift.x, world[i].y + shift.y, world[i].z + shift.z};
            const Vec3 d = w - cam.pos;
            const double dist = std::max(std::sqrt(dot(d, d)), 1e-9);
            cols[0][i] = static_cast<float>(w.x);
            cols[1][i] = static_cast<float>(w.y);
            cols[2][i] = static_cast<float>(w.z);
            cols[3][i] = static_cast<float>(mApp - 5.0 * std::log10(dist / 3.2615638) + 5.0);
        }
        count = capacity;
    }

    // À appeler quand le dessin des étoiles est lié, avec des constantes dont le temps écoulé vaut 0 (voir fenetre.cpp).
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
        if (!capacity) return;
        for (auto& b : vb) {
            vkUnmapMemory(g.dev, b.mem);
            destroy(g, b);
        }
    }
};

}  // namespace
