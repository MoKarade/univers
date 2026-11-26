// Appli PC « Univers » : les astéroïdes (asteroides.bin, pipeline/natif/asteroides.py). Chaque orbite est calculée
// par la carte graphique à chaque image (équation de Kepler), d'après les éléments mesurés du JPL.
#pragma once
#include "commun.h"

namespace univers {

struct AsteroidPush {
    float viewProj[16];
    float camHi[4];
    float camLo[4];
    float par[4];
};

class AsteroidRenderer {
public:
    bool ready = false;
    uint64_t count = 0;
    double epochJd = 0;      // date des éléments (jour julien)

    // Rend false si le fichier manque (le simulateur continue sans astéroïdes).
    bool create(const Gpu& g, const std::string& path, VkFormat hdrFormat) {
        const HANDLE file = CreateFileA(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file == INVALID_HANDLE_VALUE) return false;
        LARGE_INTEGER size;
        GetFileSizeEx(file, &size);
        const HANDLE mapping = CreateFileMappingA(file, nullptr, PAGE_READONLY, 0, 0, nullptr);
        const auto* base = mapping ? static_cast<const uint8_t*>(MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 0)) : nullptr;
        if (!base || std::memcmp(base, "UNIVAST1", 8) != 0) return false;
        std::memcpy(&count, base + 8, 8);
        std::memcpy(&epochJd, base + 16, 8);
        const size_t column = (count * 4 + kAlign - 1) / kAlign * kAlign;
        if (static_cast<uint64_t>(size.QuadPart) < kAlign + kCols * column) return false;
        for (int i = 0; i < kCols; ++i) vb_[i] = uploadVertices(g, base + kAlign + i * column, count * 4);
        UnmapViewOfFile(base);
        CloseHandle(mapping);
        CloseHandle(file);

        const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(AsteroidPush)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement des astéroïdes");
        vs_ = shader(g, "asteroides.vert.spv");
        fs_ = shader(g, "etoiles.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
        VkVertexInputBindingDescription binds[kCols];
        VkVertexInputAttributeDescription attrs[kCols];
        for (uint32_t i = 0; i < kCols; ++i) {
            binds[i] = {i, 4, VK_VERTEX_INPUT_RATE_VERTEX};
            attrs[i] = {i, i, VK_FORMAT_R32_SFLOAT, 0};
        }
        VkPipelineVertexInputStateCreateInfo vin{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        vin.vertexBindingDescriptionCount = kCols;
        vin.pVertexBindingDescriptions = binds;
        vin.vertexAttributeDescriptionCount = kCols;
        vin.pVertexAttributeDescriptions = attrs;
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
        VkPipelineColorBlendAttachmentState att{};      // les lumières s'additionnent
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
        rci.pColorAttachmentFormats = &hdrFormat;
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
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline_), "pipeline des astéroïdes");
        ready = true;
        return true;
    }

    // camAu : position de la caméra en UA (écliptique, centre : Soleil) ; days : jours écoulés depuis l'époque des éléments.
    void draw(VkCommandBuffer cmd, const Camera& cam, Vec3 camAu, double days, uint32_t width, uint32_t height, float gain) const {
        if (!ready || gain <= 0) return;
        AsteroidPush pc{};
        const auto m = cam.viewProj();
        std::memcpy(pc.viewProj, m.data(), sizeof(pc.viewProj));
        const double p[3] = {camAu.x, camAu.y, camAu.z};
        for (int a = 0; a < 3; ++a) {
            pc.camHi[a] = static_cast<float>(p[a]);
            pc.camLo[a] = static_cast<float>(p[a] - static_cast<double>(pc.camHi[a]));
        }
        pc.par[0] = gain;
        pc.par[1] = static_cast<float>(height);
        pc.par[2] = static_cast<float>(days);
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        const VkRect2D sc{{0, 0}, {width, height}};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        VkBuffer bufs[kCols];
        VkDeviceSize offs[kCols];
        for (int i = 0; i < kCols; ++i) {
            bufs[i] = vb_[i].buf;
            offs[i] = 0;
        }
        vkCmdBindVertexBuffers(cmd, 0, kCols, bufs, offs);
        vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(pc), &pc);
        vkCmdDraw(cmd, static_cast<uint32_t>(count), 1, 0, 0);
    }

    void release(const Gpu& g) {
        if (!ready) return;
        for (auto& b : vb_) destroy(g, b);
        vkDestroyPipeline(g.dev, pipeline_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
    }

private:
    static constexpr int kCols = 10;
    Buffer vb_[kCols];
    VkPipelineLayout layout_{};
    VkPipeline pipeline_{};
    VkShaderModule vs_{}, fs_{};
};

}  // namespace univers