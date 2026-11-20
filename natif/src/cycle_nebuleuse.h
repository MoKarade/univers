// Appli PC « Univers » : dessin de la matière autour des étoiles (nuage de naissance, vents, nébuleuse planétaire, reste
// de supernova), d'après les profils de cycle_appli.h. Un triangle plein écran limité au rectangle de la nébuleuse, une
// passe d'extinction (poussière) puis une passe de lumière, après les sphères. Éclat : la même échelle que les points des
// étoiles (une nébuleuse de luminosité L donne, sommée sur ses pixels, l'éclat d'une étoile de luminosité L).
#pragma once
#include "cycle_appli.h"

namespace {

class NebuleuseRenderer {
public:
    static constexpr int kMax = 16;
    static constexpr int kFloats = 2 * cycle::kCouchesMax + 1 + 3 * cycle::kCouchesMax + 3;      // r (n + 1), teintes (3 n), extinction (n), arrondi
    int shown = 0;      // nébuleuses dessinées à la dernière image

    void create(const Gpu& g, VkFormat hdrFormat) {
        buf_ = createBuffer(g, sizeof(float) * kFloats * kMax, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,
                            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        check(vkMapMemory(g.dev, buf_.mem, 0, VK_WHOLE_SIZE, 0, reinterpret_cast<void**>(&map_)), "tampon des nébuleuses");
        const VkDescriptorSetLayoutBinding bind{0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 1;
        dl.pBindings = &bind;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement des nébuleuses");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 1;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve des nébuleuses");
        VkDescriptorSetAllocateInfo ai{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        ai.descriptorPool = pool_;
        ai.descriptorSetCount = 1;
        ai.pSetLayouts = &setLayout_;
        check(vkAllocateDescriptorSets(g.dev, &ai, &set_), "ensemble des nébuleuses");
        const VkDescriptorBufferInfo bi{buf_.buf, 0, VK_WHOLE_SIZE};
        VkWriteDescriptorSet wr{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
        wr.dstSet = set_;
        wr.dstBinding = 0;
        wr.descriptorCount = 1;
        wr.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        wr.pBufferInfo = &bi;
        vkUpdateDescriptorSets(g.dev, 1, &wr, 0, nullptr);
        const VkPushConstantRange pcr{VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(Push)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement des nébuleuses");
        vs_ = shader(g, "ecran.vert.spv");
        fs_ = shader(g, "nebuleuse.frag.spv");
        absorb_ = pipeline(g, hdrFormat, false);
        emit_ = pipeline(g, hdrFormat, true);
    }

    // À appeler pendant l'enregistrement de l'image (la carte a fini l'image précédente : le tampon peut être réécrit).
    void draw(VkCommandBuffer cmd, const CycleAppli& cy, const Sim& sim, const Camera& cam, uint32_t width, uint32_t height, float exposure) {
        shown = 0;
        if (!cy.ready()) return;
        struct Item { Push pc; VkRect2D sc; };
        std::vector<Item> items;
        const double pixel = 2.0 * cam.tanHalf / height;
        // éclat : exposition × 10^(-0,4 M☉V) × (10 pc en al)² × angle solide d'un pixel (même échelle que etoiles.vert)
        const double scale = exposure * std::pow(10.0, -0.4 * 4.83) * 32.6156 * 32.6156 * pixel * pixel;
        for (const CycleAppli::Astre& a : cy.astres) {
            if (!a.profilOk || static_cast<int>(items.size()) >= kMax) continue;
            const cycle::Profil& p = a.profil;
            const double rMax = p.r[p.n];
            float extMax = 0;
            for (int k = 0; k < p.n; ++k) extMax = std::max(extMax, p.ext[k] * (p.r[k + 1] - p.r[k]));
            if (p.lumiere <= 0 && extMax < 1e-4f) continue;
            const Vec3 c = sim.position(a.body) - cam.pos;
            const double dist = std::sqrt(dot(c, c));
            if (dist <= 0) continue;
            const double rho = rMax / dist, z = dot(c, cam.fwd);
            const bool inside = rho >= 0.95;
            if (!inside && (z <= 0 || rho / pixel < 1.0)) continue;
            VkRect2D sc{{0, 0}, {width, height}};
            if (!inside) {
                const double cx = (dot(c, cam.right) / (z * cam.tanHalf * cam.aspect) * 0.5 + 0.5) * width, cy2 = (-dot(c, cam.up) / (z * cam.tanHalf) * 0.5 + 0.5) * height;
                const double tx = (cx / width * 2.0 - 1.0) * cam.tanHalf * cam.aspect, ty = (cy2 / height * 2.0 - 1.0) * cam.tanHalf;
                const double rpx = std::tan(std::asin(std::min(rho, 0.999))) / pixel * 1.15 * (1.0 + tx * tx + ty * ty) + 3;
                const double x0 = std::clamp(cx - rpx, 0.0, static_cast<double>(width)), x1 = std::clamp(cx + rpx, 0.0, static_cast<double>(width));
                const double y0 = std::clamp(cy2 - rpx, 0.0, static_cast<double>(height)), y1 = std::clamp(cy2 + rpx, 0.0, static_cast<double>(height));
                if (x1 - x0 < 1 || y1 - y0 < 1) continue;
                sc = {{static_cast<int32_t>(x0), static_cast<int32_t>(y0)}, {static_cast<uint32_t>(x1 - x0), static_cast<uint32_t>(y1 - y0)}};
            }
            // profil dans le tampon : r[0..n], rgb[n][3], ext[n]
            const int slot = static_cast<int>(items.size());
            float* dst = map_ + static_cast<size_t>(slot) * kFloats;
            for (int k = 0; k <= p.n; ++k) dst[k] = p.r[k];
            for (int k = 0; k < p.n; ++k)
                for (int j = 0; j < 3; ++j) dst[p.n + 1 + 3 * k + j] = p.rgb[k][j];
            for (int k = 0; k < p.n; ++k) dst[p.n + 1 + 3 * p.n + k] = p.ext[k];
            const Vec3 u = unit(c);
            Item it;
            it.pc = Push{{static_cast<float>(u.x), static_cast<float>(u.y), static_cast<float>(u.z), static_cast<float>(dist)},
                         {static_cast<float>(cam.right.x), static_cast<float>(cam.right.y), static_cast<float>(cam.right.z), static_cast<float>(cam.tanHalf * cam.aspect)},
                         {static_cast<float>(cam.up.x), static_cast<float>(cam.up.y), static_cast<float>(cam.up.z), static_cast<float>(cam.tanHalf)},
                         {static_cast<float>(cam.fwd.x), static_cast<float>(cam.fwd.y), static_cast<float>(cam.fwd.z), 0},
                         {static_cast<float>(slot * kFloats), static_cast<float>(p.n), static_cast<float>(scale), 0}};
            it.sc = sc;
            items.push_back(it);
        }
        if (items.empty()) return;
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        for (int mode = 0; mode < 2; ++mode) {
            vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, mode ? emit_ : absorb_);
            vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &set_, 0, nullptr);
            for (Item& it : items) {
                it.pc.par[3] = static_cast<float>(mode);
                vkCmdSetScissor(cmd, 0, 1, &it.sc);
                vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(Push), &it.pc);
                vkCmdDraw(cmd, 3, 1, 0, 0);
            }
        }
        shown = static_cast<int>(items.size());
    }

    void release(const Gpu& g) {
        vkDestroyPipeline(g.dev, absorb_, nullptr);
        vkDestroyPipeline(g.dev, emit_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkUnmapMemory(g.dev, buf_.mem);
        destroy(g, buf_);
    }

private:
    struct Push {
        float centre[4], droite[4], haut[4], avant[4], par[4];
    };
    Buffer buf_{};
    float* map_ = nullptr;
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet set_{};
    VkPipelineLayout layout_{};
    VkShaderModule vs_{}, fs_{};
    VkPipeline absorb_{}, emit_{};

    VkPipeline pipeline(const Gpu& g, VkFormat fmt, bool emit) {
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
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
        VkPipelineColorBlendAttachmentState att{};
        att.blendEnable = VK_TRUE;
        // extinction : ce qui est derrière × exp(-τ) ; lumière : ajoutée
        att.srcColorBlendFactor = emit ? VK_BLEND_FACTOR_ONE : VK_BLEND_FACTOR_ZERO;
        att.dstColorBlendFactor = emit ? VK_BLEND_FACTOR_ONE : VK_BLEND_FACTOR_SRC_COLOR;
        att.colorBlendOp = VK_BLEND_OP_ADD;
        att.srcAlphaBlendFactor = VK_BLEND_FACTOR_ZERO;
        att.dstAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
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
        VkPipeline p{};
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &p), "pipeline des nébuleuses");
        return p;
    }
};

}  // namespace
