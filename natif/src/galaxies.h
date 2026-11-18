// Appli PC « Univers » : les galaxies et quasars des relevés (galaxies.bin, pipeline/natif/galaxies.py).
// Direction et décalage vers le rouge mesurés ; distance calculée en direct d'après la cosmologie (cosmologie.h).
#pragma once
#include "commun.h"
#include "cosmologie.h"

namespace {

constexpr double kGalaxyZMax = 7.0;      // borne de la table des distances (DATA.SURV_ZMAX de la page)

struct GalaxyFile {
    const uint8_t* base = nullptr;
    uint64_t n = 0;
    size_t column = 0;
    const void* col(int k) const { return base + kAlign + k * column; }
};

// Rend false si le fichier manque (le simulateur le dit et continue sans galaxies).
bool openGalaxies(const std::string& path, GalaxyFile& out) {
    const HANDLE file = CreateFileA(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) return false;
    LARGE_INTEGER size;
    GetFileSizeEx(file, &size);
    const HANDLE mapping = CreateFileMappingA(file, nullptr, PAGE_READONLY, 0, 0, nullptr);
    out.base = mapping ? static_cast<const uint8_t*>(MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 0)) : nullptr;
    if (!out.base || std::memcmp(out.base, "UNIVGAL1", 8) != 0) return false;
    std::memcpy(&out.n, out.base + 8, 8);
    out.column = (out.n * 4 + kAlign - 1) / kAlign * kAlign;
    return static_cast<uint64_t>(size.QuadPart) >= kAlign + 5 * out.column;
}

struct GalaxyPush {
    float viewProj[16];
    float cam[4];
    float par[4];
};

class GalaxyRenderer {
public:
    bool ready = false;
    uint64_t count = 0;

    void create(const Gpu& g, const GalaxyFile& file, VkFormat hdrFormat) {
        count = file.n;
        for (int i = 0; i < 5; ++i) vb_[i] = uploadVertices(g, file.col(i), file.n * 4);
        table_ = createBuffer(g, 65 * 16, VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, table_.mem, 0, 65 * 16, 0, &p), "table des distances");
        mapped_ = static_cast<float*>(p);
        const VkDescriptorSetLayoutBinding bind{0, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 1, VK_SHADER_STAGE_VERTEX_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 1;
        dl.pBindings = &bind;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement des galaxies");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 1};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 1;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve des galaxies");
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = 1;
        da.pSetLayouts = &setLayout_;
        check(vkAllocateDescriptorSets(g.dev, &da, &set_), "ressources des galaxies");
        const VkDescriptorBufferInfo bi{table_.buf, 0, 65 * 16};
        VkWriteDescriptorSet w{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
        w.dstSet = set_;
        w.descriptorCount = 1;
        w.descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        w.pBufferInfo = &bi;
        vkUpdateDescriptorSets(g.dev, 1, &w, 0, nullptr);

        const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(GalaxyPush)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement des galaxies");
        vs_ = shader(g, "galaxies.vert.spv");
        fs_ = shader(g, "etoiles.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
        VkVertexInputBindingDescription binds[5];
        VkVertexInputAttributeDescription attrs[5];
        for (uint32_t i = 0; i < 5; ++i) {
            binds[i] = {i, 4, VK_VERTEX_INPUT_RATE_VERTEX};
            attrs[i] = {i, i, i == 4 ? VK_FORMAT_R8G8B8A8_UNORM : VK_FORMAT_R32_SFLOAT, 0};
        }
        VkPipelineVertexInputStateCreateInfo vin{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        vin.vertexBindingDescriptionCount = 5;
        vin.pVertexBindingDescriptions = binds;
        vin.vertexAttributeDescriptionCount = 5;
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
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline_), "pipeline des galaxies");
        ready = true;
    }

    // Distance (années-lumière) d'un décalage vers le rouge, par la même table que le shader (galaxies_formes.h) ; version :
    // change à chaque nouvelle table.
    double distanceLy(double z) const {
        if (!mapped_) return 0;
        const double u = std::clamp(std::log(1.0 + z) / std::log(1.0 + kGalaxyZMax), 0.0, 1.0) * 256.0;
        const int k = std::min(static_cast<int>(u), 255);
        return mapped_[k] + (mapped_[k + 1] - mapped_[k]) * (u - k);
    }
    uint64_t tableVersion = 0;

    // Recalcule la table des distances pour une cosmologie : toutes les galaxies sont replacées à l'image suivante.
    // scale : facteur d'échelle de l'univers à la date montrée (1 aujourd'hui) : les distances grandissent avec lui.
    void setCosmology(const cosmo::Params& p, double scale = 1.0) {
        if (!ready) return;
        const auto t = cosmo::distanceTable(p, kGalaxyZMax, 256);
        for (int k = 0; k < 260; ++k) mapped_[k] = static_cast<float>(t[static_cast<size_t>(std::min(k, 256))] * cosmo::kMpcInLy * scale);
        ++tableVersion;
    }

    // À appeler dans la passe en grande dynamique. exposure : celle des étoiles (même loi d'éclat, galaxies.vert).
    void draw(VkCommandBuffer cmd, const Camera& cam, uint32_t width, uint32_t height, float exposure) const {
        if (!ready || exposure <= 0) return;
        GalaxyPush pc{};
        const auto m = cam.viewProj();
        std::memcpy(pc.viewProj, m.data(), sizeof(pc.viewProj));
        pc.cam[0] = static_cast<float>(cam.pos.x);
        pc.cam[1] = static_cast<float>(cam.pos.y);
        pc.cam[2] = static_cast<float>(cam.pos.z);
        pc.cam[3] = 0.0f;
        pc.par[0] = exposure;
        pc.par[1] = static_cast<float>(height);
        pc.par[2] = static_cast<float>(1.0 / std::log(1.0 + kGalaxyZMax));
        pc.par[3] = 2.0f;
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        const VkRect2D sc{{0, 0}, {width, height}};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &set_, 0, nullptr);
        VkBuffer bufs[5];
        VkDeviceSize offs[5];
        for (int i = 0; i < 5; ++i) {
            bufs[i] = vb_[i].buf;
            offs[i] = 0;
        }
        vkCmdBindVertexBuffers(cmd, 0, 5, bufs, offs);
        vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(pc), &pc);
        vkCmdDraw(cmd, static_cast<uint32_t>(count), 1, 0, 0);
    }

    void release(const Gpu& g) {
        if (!ready) return;
        vkUnmapMemory(g.dev, table_.mem);
        destroy(g, table_);
        for (auto& b : vb_) destroy(g, b);
        vkDestroyPipeline(g.dev, pipeline_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
    }

private:
    Buffer vb_[5];
    Buffer table_;
    float* mapped_ = nullptr;
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet set_{};
    VkPipelineLayout layout_{};
    VkPipeline pipeline_{};
    VkShaderModule vs_{}, fs_{};
};

}  // namespace
