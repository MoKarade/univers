// Appli PC « Univers » : nébuleuses en 3D (demande de Marc, 20/11/2026 : « l'espace paraît trop vide, il manque du gaz,
// des nébuleuses, de la poussière »). Fichier nebuleuses.bin écrit par pipeline/natif/nebuleuses.py, qui dit les sources :
// nébuleuses planétaires de Chornay et Walton 2021 (distance de leur étoile centrale par Gaia, rayon angulaire mesuré) et
// nuages moléculaires de Zucker et al. 2020 (distances mesurées sur des lignes de visée).
//
// Dessin (shaders/nebuleuse.vert, nebuleuse.frag) : une tache ronde tournée vers la caméra, de la taille mesurée.
// - Nébuleuses planétaires : repère lumineux, ajouté à l'image (leur éclat n'est pas dans les données retenues).
// - Nuages moléculaires : poussière qui ASSOMBRIT ce qui est déjà dessiné (mélange multiplicatif), après les étoiles et
//   les galaxies, avant l'interface [approché : une étoile devant le nuage est assombrie elle aussi ; opacité supposée].
// Montrées tant que la caméra est à moins de 30 000 al du Soleil (au-delà, elles font moins d'un pixel) et autour
// d'aujourd'hui (fondu de 1 à 3 Ma : leur place est celle d'aujourd'hui).
#pragma once
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

#include "commun.h"

namespace {

class NebulaRenderer {
public:
    bool ready = false;
    uint32_t planetary = 0, clouds = 0;

    bool create(const Gpu& g, const std::string& path, VkFormat fmt) {
        std::ifstream f(path, std::ios::binary);
        char magic[8];
        uint32_t h[2] = {};
        f.read(magic, 8);
        f.read(reinterpret_cast<char*>(h), sizeof(h));
        if (!f || std::memcmp(magic, "UNIVNEB1", 8) != 0 || h[0] == 0 || h[0] > 1000000) return false;
        std::vector<uint32_t> raw(static_cast<size_t>(h[0]) * 8);
        if (!f.read(reinterpret_cast<char*>(raw.data()), static_cast<std::streamsize>(raw.size() * 4))) return false;
        for (uint32_t i = 0; i < h[0]; ++i) (raw[i * 8 + 4] == 1 ? planetary : clouds) += 1;
        count_ = h[0];
        Buffer staging = createBuffer(g, raw.size() * 4, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, raw.size() * 4, 0, &p), "nébuleuses : accès au tampon");
        std::memcpy(p, raw.data(), raw.size() * 4);
        vkUnmapMemory(g.dev, staging.mem);
        vb_ = createBuffer(g, raw.size() * 4, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        VkCommandBuffer cmd = beginOnce(g);
        const VkBufferCopy region{0, 0, raw.size() * 4};
        vkCmdCopyBuffer(cmd, staging.buf, vb_.buf, 1, &region);
        endOnce(g, cmd);
        destroy(g, staging);
        vs_ = shader(g, "nebuleuse.vert.spv");
        fs_ = shader(g, "nebuleuse.frag.spv");
        pipeline(g, fmt, false, addPipe_);
        pipeline(g, fmt, true, mulPipe_);
        ready = true;
        return true;
    }

    // part : 0 à 1 (fondus en temps et en distance, fenetre.cpp) ; deux passes : poussière (multiplie) puis repères (ajoute).
    void draw(VkCommandBuffer cmd, const Camera& cam, uint32_t width, uint32_t height, double part) const {
        if (!ready || part <= 0.002) return;
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        const VkRect2D sc{{0, 0}, {width, height}};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        Push pc{};
        const auto vpm = cam.viewProj();
        std::memcpy(pc.viewProj, vpm.data(), sizeof(pc.viewProj));
        pc.cam[0] = static_cast<float>(cam.pos.x);
        pc.cam[1] = static_cast<float>(cam.pos.y);
        pc.cam[2] = static_cast<float>(cam.pos.z);
        pc.par[0] = static_cast<float>(part);
        pc.par[1] = static_cast<float>(height);
        pc.par[2] = static_cast<float>(height / (2.0 * cam.tanHalf));
        const VkDeviceSize off = 0;
        // les nuages moléculaires (genre 2) ne sont plus dessinés en taches : leur étendue venait des seules lignes de visée,
        // bien plus petite que les nuages ; la poussière est maintenant la carte 3D mesurée (voie_lactee.h, dustOnly)
        for (const int genre : {1}) {
            pc.par[3] = static_cast<float>(genre);
            vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, genre == 2 ? mulPipe_ : addPipe_);
            vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(pc), &pc);
            vkCmdBindVertexBuffers(cmd, 0, 1, &vb_.buf, &off);
            vkCmdDraw(cmd, count_, 1, 0, 0);
        }
    }

    void release(const Gpu& g) {
        if (!ready) return;
        vkDestroyPipeline(g.dev, addPipe_, nullptr);
        vkDestroyPipeline(g.dev, mulPipe_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
        destroy(g, vb_);
        ready = false;
    }

private:
    struct Push { float viewProj[16]; float cam[4]; float par[4]; };
    Buffer vb_;
    uint32_t count_ = 0;
    VkShaderModule vs_{}, fs_{};
    VkPipelineLayout layout_{};
    VkPipeline addPipe_{}, mulPipe_{};

    void pipeline(const Gpu& g, VkFormat fmt, bool multiply, VkPipeline& pipe) {
        if (!layout_) {
            const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(Push)};
            VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
            li.pushConstantRangeCount = 1;
            li.pPushConstantRanges = &pcr;
            check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "nébuleuses : agencement");
        }
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
        const VkVertexInputBindingDescription bind{0, 32, VK_VERTEX_INPUT_RATE_VERTEX};
        const VkVertexInputAttributeDescription ad[2] = {{0, 0, VK_FORMAT_R32G32B32A32_SFLOAT, 0}, {1, 0, VK_FORMAT_R32G32B32A32_UINT, 16}};
        VkPipelineVertexInputStateCreateInfo vin{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        vin.vertexBindingDescriptionCount = 1;
        vin.pVertexBindingDescriptions = &bind;
        vin.vertexAttributeDescriptionCount = 2;
        vin.pVertexAttributeDescriptions = ad;
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
        // ajout : couleur + image ; poussière : image × couleur (la couleur est la transmission)
        att.srcColorBlendFactor = multiply ? VK_BLEND_FACTOR_ZERO : VK_BLEND_FACTOR_ONE;
        att.dstColorBlendFactor = multiply ? VK_BLEND_FACTOR_SRC_COLOR : VK_BLEND_FACTOR_ONE;
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
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipe), "nébuleuses : pipeline");
    }
};

}  // namespace
