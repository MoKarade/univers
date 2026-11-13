// Appli PC « Univers » : galaxies de forme MESURÉE, faites de particules (Marc, 13/11/2026 : « plus de galaxies images »).
//
// Données : galaxies_formes.bin (pipeline/natif/galaxies_formes.py) : 532 427 galaxies du Siena Galaxy Atlas 2020 et
// d'HyperLEDA, avec diamètre D26, rapport d'axes, angle de position, type, magnitude r et couleur g - r mesurés quand ils
// existent, distance de Cosmicflows-4 ou décalage vers le rouge. Leurs points du grand catalogue (galaxies.bin) sont
// marqués : galaxies.vert ne les dessine plus, ce module prend leur place.
// Dessin (shaders/galaxie_formes.vert) : de loin, un point au vrai éclat ; dès que la galaxie dépasse 2 pixels à l'écran,
// une galaxie de particules générées à la volée sur la carte graphique (graine fixe par galaxie, rien n'est stocké), en
// fondu jusqu'à 8 pixels, la lumière totale conservée. Nombre de particules selon la taille à l'écran, plafonné.
#pragma once
#include "gaia.h"
#include "galaxies.h"

namespace {

class GalaxyShapes {
public:
    bool ready = false;
    uint32_t count = 0, shown = 0;      // galaxies, galaxies montrées en particules à la dernière image
    uint64_t particles = 0;
    double maxSurface = 0;
    float ageing[4] = {1, 1, 1, 1};      // vieillissement : lumière disque (comp. 1), bulbe et elliptiques (comp. 2), puis températures
      // brillance de surface moyenne la plus forte des galaxies résolues (flux par pixel, exposition 1)

    bool create(const Gpu& g, const std::string& path, VkFormat hdrFormat) {
        std::ifstream f(path, std::ios::binary | std::ios::ate);
        if (!f) return false;
        const size_t bytes = static_cast<size_t>(f.tellg());
        if (bytes < 64) return false;
        std::vector<char> b(bytes);
        f.seekg(0);
        f.read(b.data(), static_cast<std::streamsize>(bytes));
        if (std::memcmp(b.data(), "UNIVGFM1", 8) != 0) return false;
        std::memcpy(&count, b.data() + 8, 4);
        if (bytes < 64 + static_cast<size_t>(count) * sizeof(Rec)) return false;
        recs_.resize(count);
        std::memcpy(recs_.data(), b.data() + 64, static_cast<size_t>(count) * sizeof(Rec));
        recBuf_ = uploadStorage(g, recs_.data(), static_cast<VkDeviceSize>(count) * sizeof(Rec));
        for (int r = 0; r < kRing; ++r) {
            pos_[r] = createBuffer(g, static_cast<VkDeviceSize>(count) * 16, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            check(vkMapMemory(g.dev, pos_[r].mem, 0, VK_WHOLE_SIZE, 0, &posMap_[r]), "galaxies : positions");
            np_[r] = createBuffer(g, static_cast<VkDeviceSize>(count) * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            check(vkMapMemory(g.dev, np_[r].mem, 0, VK_WHOLE_SIZE, 0, &npMap_[r]), "galaxies : particules");
            ind_[r] = createBuffer(g, static_cast<VkDeviceSize>(kMaxShown) * 16, VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            check(vkMapMemory(g.dev, ind_[r].mem, 0, VK_WHOLE_SIZE, 0, &indMap_[r]), "galaxies : dessins");
        }
        world_.resize(count);
        createPipeline(g, hdrFormat);
        ready = true;
        return true;
    }

    // À chaque image, avant le dessin : place de chaque galaxie (distance mesurée, ou décalage vers le rouge par la table de
    // l'appli) et choix de celles assez grandes à l'écran pour être montrées en particules.
    void prepare(const Camera& cam, const GalaxyRenderer& cat, uint32_t height) {
        if (!ready) return;
        ring_ = (ring_ + 1) % kRing;
        if (cat.tableVersion != version_) {
            version_ = cat.tableVersion;
            for (uint32_t i = 0; i < count; ++i) {
                const Rec& r = recs_[i];
                const double d = r.d > 0 ? r.d : cat.distanceLy(r.z);
                world_[i] = {r.ux * d, r.uy * d, r.uz * d, d};
            }
        }
        const double pxPerRad = height / (2.0 * cam.tanHalf);
        pxPerRad_ = pxPerRad;
        auto* pos = static_cast<float*>(posMap_[ring_]);
        auto* np = static_cast<uint32_t*>(npMap_[ring_]);
        auto* ind = static_cast<VkDrawIndirectCommand*>(indMap_[ring_]);
        const double tx = cam.tanHalf * cam.aspect * 1.05, ty = cam.tanHalf * 1.05;
        shown = 0;
        particles = 0;
        maxSurface = 0;
        for (uint32_t i = 0; i < count; ++i) {
            const W& w = world_[i];
            const double rx = w.x - cam.pos.x, ry = w.y - cam.pos.y, rz = w.z - cam.pos.z;
            pos[i * 4] = static_cast<float>(rx);
            pos[i * 4 + 1] = static_cast<float>(ry);
            pos[i * 4 + 2] = static_cast<float>(rz);
            pos[i * 4 + 3] = static_cast<float>(w.d);
            np[i] = 0;
            const double dc = std::sqrt(rx * rx + ry * ry + rz * rz);
            const double size = recs_[i].diam * 2.9088821e-4 * w.d;      // diamètre (al)
            const double px = size / std::max(dc, 1.0) * pxPerRad;
            if (px < 2.0 || shown >= kMaxShown) continue;
            if (px > 40.0) {      // galaxie bien résolue (plus de 40 pixels) : flux vu de la caméra / surface de son disque à l'écran
                const double fl = std::pow(10.0, -0.4 * recs_[i].r) * (w.d / std::max(dc, 1.0)) * (w.d / std::max(dc, 1.0));
                maxSurface = std::max(maxSurface, fl / (0.785398 * px * px * std::max(static_cast<double>(recs_[i].ba), 0.2)));
            }
            // dans le champ (avec la marge de la taille de la galaxie)
            const double f = rx * cam.fwd.x + ry * cam.fwd.y + rz * cam.fwd.z;
            if (f < -size) continue;
            const double x = rx * cam.right.x + ry * cam.right.y + rz * cam.right.z, y = rx * cam.up.x + ry * cam.up.y + rz * cam.up.z;
            const double fz = std::max(f, 1.0);
            if (std::fabs(x) > fz * tx + size || std::fabs(y) > fz * ty + size) continue;
            const uint32_t n = static_cast<uint32_t>(std::clamp(px * px * 0.3, 64.0, 30000.0));
            if (particles + n > kMaxParticles) continue;
            np[i] = n;
            particles += n;
            ind[shown++] = {n, 1, 0, i};      // une instance : la galaxie i (gl_InstanceIndex)
        }
    }

    void draw(VkCommandBuffer cmd, const Camera& cam, uint32_t width, uint32_t height, float exposure) {
        if (!ready) return;
        Push p{};
        const auto m = cam.viewProj();
        std::memcpy(p.viewProj, m.data(), sizeof(p.viewProj));
        p.par[0] = exposure;
        p.par[1] = static_cast<float>(height);
        p.par[2] = static_cast<float>(pxPerRad_);
        for (int k = 0; k < 4; ++k) p.par2[k] = ageing[k];
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        const VkRect2D sc{{0, 0}, {width, height}};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &set_[ring_], 0, nullptr);
        p.par[3] = 0.0f;      // points
        vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(p), &p);
        vkCmdDraw(cmd, count, 1, 0, 0);
        if (shown) {      // particules
            p.par[3] = 1.0f;
            vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(p), &p);
            vkCmdDrawIndirect(cmd, ind_[ring_].buf, 0, shown, sizeof(VkDrawIndirectCommand));
        }
    }

    void release(const Gpu& g) {
        if (!ready) return;
        for (int r = 0; r < kRing; ++r) {
            vkUnmapMemory(g.dev, pos_[r].mem); destroy(g, pos_[r]);
            vkUnmapMemory(g.dev, np_[r].mem); destroy(g, np_[r]);
            vkUnmapMemory(g.dev, ind_[r].mem); destroy(g, ind_[r]);
        }
        destroy(g, recBuf_);
        vkDestroyPipeline(g.dev, pipeline_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
        ready = false;
    }

private:
    static constexpr int kRing = 3;
    static constexpr uint32_t kMaxShown = 20000;
    static constexpr uint64_t kMaxParticles = 6000000;      // particules par image, toutes galaxies (~100 Mo de sommets générés, rien de stocké)
    struct Rec { float ux, uy, uz, z, d, diam, ba, pa, T, r, gr; uint32_t f; };
    static_assert(sizeof(Rec) == 48, "fiche de galaxies_formes.bin : 48 octets");
    struct W { double x, y, z, d; };
    struct Push { float viewProj[16]; float par[4]; float par2[4]; };

    void createPipeline(const Gpu& g, VkFormat fmt) {
        VkDescriptorSetLayoutBinding binds[3];
        for (uint32_t i = 0; i < 3; ++i) binds[i] = {i, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_VERTEX_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 3;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement des galaxies de forme");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 3 * kRing};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = kRing;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve des galaxies de forme");
        for (int r = 0; r < kRing; ++r) {
            VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
            da.descriptorPool = pool_;
            da.descriptorSetCount = 1;
            da.pSetLayouts = &setLayout_;
            check(vkAllocateDescriptorSets(g.dev, &da, &set_[r]), "jeu des galaxies de forme");
            const VkDescriptorBufferInfo infos[3] = {{recBuf_.buf, 0, VK_WHOLE_SIZE}, {pos_[r].buf, 0, VK_WHOLE_SIZE}, {np_[r].buf, 0, VK_WHOLE_SIZE}};
            VkWriteDescriptorSet w[3];
            for (uint32_t i = 0; i < 3; ++i) {
                w[i] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
                w[i].dstSet = set_[r];
                w[i].dstBinding = i;
                w[i].descriptorCount = 1;
                w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
                w[i].pBufferInfo = &infos[i];
            }
            vkUpdateDescriptorSets(g.dev, 3, w, 0, nullptr);
        }
        const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(Push)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement des galaxies de forme");
        vs_ = shader(g, "galaxie_formes.vert.spv");
        fs_ = shader(g, "etoiles.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
        VkPipelineVertexInputStateCreateInfo vin{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        VkPipelineInputAssemblyStateCreateInfo ia{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};
        ia.topology = VK_PRIMITIVE_TOPOLOGY_POINT_LIST;
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
        VkPipelineColorBlendAttachmentState att{};
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
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline_), "dessin des galaxies de forme");
    }

    std::vector<Rec> recs_;
    std::vector<W> world_;
    uint64_t version_ = ~0ull;
    double pxPerRad_ = 1;
    int ring_ = 0;
    Buffer recBuf_, pos_[kRing], np_[kRing], ind_[kRing];
    void* posMap_[kRing] = {};
    void* npMap_[kRing] = {};
    void* indMap_[kRing] = {};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet set_[kRing]{};
    VkPipelineLayout layout_{};
    VkPipeline pipeline_{};
    VkShaderModule vs_{}, fs_{};
};

}  // namespace
