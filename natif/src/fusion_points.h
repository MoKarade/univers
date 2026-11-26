// Appli PC « Univers » : les étoiles du calcul de la fusion avec Andromède (phys::fusion::Rejeu), montrées seulement dans
// l'avenir (au-delà de 3 millions d'années) : c'est une évolution calculée, pas un état mesuré.
// Chaque particule du calcul est un point d'éclat fixe (transmis dans pc.par.w à etoiles.vert, ce n'est pas une étoile
// mesurée) : les positions ne sont recopiées en VRAM que lorsque la date change.
#pragma once
#include "simulation.h"

namespace univers {

struct FusionPoints {
    Buffer vb[StarRenderer::kCols]{};
    float* cols[StarRenderer::kCols] = {};
    uint32_t capacity = 0, count = 0;
    float flux = 0.0f;
    std::vector<phys::Vec3> scratch;
    double worldAtGa = -1;

    void create(const Gpu& g, uint32_t n) {
        capacity = n;
        if (!n) return;
        scratch.resize(n);
        for (int i = 0; i < StarRenderer::kCols; ++i) {
            vb[i] = createBuffer(g, static_cast<VkDeviceSize>(n) * 4, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                                 VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            void* p = nullptr;
            check(vkMapMemory(g.dev, vb[i].mem, 0, static_cast<VkDeviceSize>(n) * 4, 0, &p),
                  "tampon des étoiles de la fusion");
            cols[i] = static_cast<float*>(p);
            std::memset(p, 0, static_cast<size_t>(n) * 4);
        }
        const uint8_t white[4] = {255, 255, 255, 255};  // aucune teinte n'est avancée
        for (uint32_t i = 0; i < n; ++i) std::memcpy(&cols[4][i], white, 4);
    }

    void update(const Sim& sim) {
        count = 0;
        flux = 0.0f;
        if (!capacity || !sim.replay || !sim.deepTime()) return;
        // Éclat d'affichage : 0,35 par point, éteint progressivement quand on regarde de trop près (moins de 3 000 al).
        const double fade = std::clamp((std::log10(std::max(sim.dist, 1.0)) - 3.5) / 1.0, 0.0, 1.0);
        if (fade <= 0.0) return;
        const double tGa = sim.replayGa();
        if (tGa != worldAtGa) {
            if (!sim.replay->etoilesA(tGa, scratch)) {
                worldAtGa = -1;
                return;
            }
            for (uint32_t i = 0; i < capacity; ++i) {
                const Vec3 w = Sim::fromGalactocentric(scratch[i]);
                cols[0][i] = static_cast<float>(w.x);
                cols[1][i] = static_cast<float>(w.y);
                cols[2][i] = static_cast<float>(w.z);
            }
            worldAtGa = tGa;
        }
        flux = static_cast<float>(0.35 * fade);
        count = capacity;
    }

    // À appeler quand le dessin des étoiles est lié, avec par[2] = 0 et par[3] = flux (voir fenetre.cpp).
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
        capacity = 0;
        count = 0;
        flux = 0.0f;
        worldAtGa = -1;
    }
};

}  // namespace univers
