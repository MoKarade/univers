// Appli PC « Univers » : les étoiles de Gaia DR3 dont la distance est mesurée à mieux que 10 % (environ 98 millions).
// Fichier gaia.bin écrit par pipeline/natif/gaia_convertir.py (format décrit dans ce script).
//
// Dessin : les étoiles sont rangées dans un arbre en huit, et dans chaque feuille de la plus brillante à la plus faible.
// À chaque image, le processeur garde les feuilles dans le champ de vue et, pour chacune, le nombre d'étoiles assez
// brillantes pour compter à l'écran vues de la caméra (seuil de flux fluxMin, bien sous ce que l'écran montre). La carte
// graphique dessine ces débuts de feuilles en un seul appel (dessin indirect multiple). Les étoiles sont lues
// directement dans des tampons de stockage (16 octets par étoile ; la vitesse, 8 octets, n'est lue que si le temps bouge).
#pragma once
#include "commun.h"

namespace {

struct GaiaLeaf {
    float mn[3];
    uint32_t n;
    float mx[3];
    uint32_t reserve0;
    uint64_t first;
    uint64_t reserve1;
};
static_assert(sizeof(GaiaLeaf) == 48, "feuille de gaia.bin : 48 octets");

struct GaiaFile {
    const uint8_t* base = nullptr;
    uint64_t n = 0;
    uint32_t leafCount = 0;
    float epoch = 2016.0f;      // année des positions (Gaia DR3 : J2016,0)
    const float* temperature = nullptr;      // 256 pas de couleur BP-RP -> température (K)
    const GaiaLeaf* leaves = nullptr;
    const uint8_t* stars = nullptr;      // 16 octets par étoile
    const uint8_t* velocities = nullptr;      // 8 octets par étoile
    float magnitude(uint64_t i) const {
        uint16_t h;
        std::memcpy(&h, stars + i * 16 + 12, 2);
        return halfToFloat(h);
    }
};

inline size_t gaiaAlign(size_t v) { return (v + kAlign - 1) / kAlign * kAlign; }

// Rend false si le fichier manque ou n'est pas complet.
bool openGaia(const std::string& path, GaiaFile& out) {
    const HANDLE file = CreateFileA(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) return false;
    LARGE_INTEGER size;
    GetFileSizeEx(file, &size);
    const HANDLE mapping = CreateFileMappingA(file, nullptr, PAGE_READONLY, 0, 0, nullptr);
    out.base = mapping ? static_cast<const uint8_t*>(MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 0)) : nullptr;
    if (!out.base || std::memcmp(out.base, "UNIVGAI1", 8) != 0) return false;
    std::memcpy(&out.n, out.base + 8, 8);
    std::memcpy(&out.leafCount, out.base + 16, 4);
    std::memcpy(&out.epoch, out.base + 20, 4);
    out.temperature = reinterpret_cast<const float*>(out.base + 32);
    const size_t leafBytes = gaiaAlign(out.leafCount * sizeof(GaiaLeaf)), starBytes = gaiaAlign(out.n * 16);
    out.leaves = reinterpret_cast<const GaiaLeaf*>(out.base + 4096);
    out.stars = out.base + 4096 + leafBytes;
    out.velocities = out.stars + starBytes;
    return static_cast<uint64_t>(size.QuadPart) >= 4096 + leafBytes + starBytes + out.n * 8;
}

// Copie vers un tampon de stockage de la carte, par morceaux (pas de tampon intermédiaire de plusieurs gigaoctets).
Buffer uploadStorage(const Gpu& g, const void* data, VkDeviceSize size) {
    constexpr VkDeviceSize kChunk = 256ull << 20;
    Buffer dst = createBuffer(g, size, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    Buffer staging = createBuffer(g, std::min(size, kChunk), VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    void* p = nullptr;
    check(vkMapMemory(g.dev, staging.mem, 0, VK_WHOLE_SIZE, 0, &p), "accès au tampon");
    for (VkDeviceSize off = 0; off < size; off += kChunk) {
        const VkDeviceSize n = std::min(kChunk, size - off);
        std::memcpy(p, static_cast<const uint8_t*>(data) + off, n);
        VkCommandBuffer cmd = beginOnce(g);
        const VkBufferCopy region{0, off, n};
        vkCmdCopyBuffer(cmd, staging.buf, dst.buf, 1, &region);
        endOnce(g, cmd);
    }
    vkUnmapMemory(g.dev, staging.mem);
    destroy(g, staging);
    return dst;
}

class GaiaRenderer {
public:
    bool ready = false;
    uint64_t count = 0;      // étoiles dans le fichier
    uint64_t drawn = 0;      // étoiles dessinées à la dernière image
    // Flux le plus faible dessiné, dans l'unité de l'image en grande dynamique (l'écran commence à montrer vers 4e-4).
    // Les étoiles plus faibles sont sautées une à une ; leur lumière cumulée n'est pas encore ajoutée [À faire].
    float fluxMin = 1e-6f;

    bool create(const Gpu& g, const std::string& path, VkFormat hdrFormat) {
        if (!openGaia(path, file_)) return false;
        VkPhysicalDeviceProperties props;
        vkGetPhysicalDeviceProperties(g.pd, &props);
        if (file_.n * 16 > props.limits.maxStorageBufferRange) return false;
        count = file_.n;
        stars_ = uploadStorage(g, file_.stars, file_.n * 16);
        velocities_ = uploadStorage(g, file_.velocities, file_.n * 8);
        // Couleur de chaque pas BP-RP : corps noir de la température du fichier, vu par l'observateur CIE (commun.h).
        std::array<float, 256 * 4> colors{};
        for (int i = 0; i < 256; ++i) {
            const float T = file_.temperature[i];
            const auto c = std::isfinite(T) ? colorOfTemperature(T) : std::array<uint8_t, 4>{255, 255, 255, 255};      // couleur non mesurée : blanc
            for (int k = 0; k < 3; ++k) colors[i * 4 + k] = c[k] / 255.0f;
            colors[i * 4 + 3] = 1.0f;
        }
        colors_ = uploadStorage(g, colors.data(), sizeof(colors));
        for (auto& r : indirect_) {
            r = createBuffer(g, std::max<VkDeviceSize>(16, file_.leafCount * 16ull), VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT,
                             VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        }
        for (int i = 0; i < kRing; ++i) check(vkMapMemory(g.dev, indirect_[i].mem, 0, VK_WHOLE_SIZE, 0, &mapped_[i]), "dessins indirects");
        createPipeline(g, hdrFormat);
        ready = true;
        return true;
    }

    // Dans la passe en grande dynamique (additive, sans profondeur). years : années depuis J2000,0.
    void draw(VkCommandBuffer cmd, const Camera& cam, uint32_t width, uint32_t height, float exposure, double years) {
        if (!ready) return;
        const double since = years - (static_cast<double>(file_.epoch) - 2000.0);      // années depuis les mesures de Gaia
        const PushConstants pc = pushConstants(cam, exposure, height, since);
        const uint32_t n = selectLeaves(cam, exposure, since, static_cast<VkDrawIndirectCommand*>(mapped_[ring_]));
        if (n > 0) {
            const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
            const VkRect2D sc{{0, 0}, {width, height}};
            vkCmdSetViewport(cmd, 0, 1, &vp);
            vkCmdSetScissor(cmd, 0, 1, &sc);
            vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
            vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &set_, 0, nullptr);
            vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(pc), &pc);
            vkCmdDrawIndirect(cmd, indirect_[ring_].buf, 0, n, sizeof(VkDrawIndirectCommand));
        }
        ring_ = (ring_ + 1) % kRing;
    }

    void release(const Gpu& g) {
        if (!ready) return;
        vkDestroyPipeline(g.dev, pipeline_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
        for (int i = 0; i < kRing; ++i) {
            vkUnmapMemory(g.dev, indirect_[i].mem);
            destroy(g, indirect_[i]);
        }
        destroy(g, stars_);
        destroy(g, velocities_);
        destroy(g, colors_);
        ready = false;
    }

private:
    static constexpr int kRing = 4;      // plus que le nombre d'images en vol : la carte ne lit jamais une liste en cours d'écriture
    static constexpr double kMaxSpeedKms = 1000.0;      // borne des vitesses du fichier (pour élargir les feuilles quand le temps bouge)
    GaiaFile file_;
    Buffer stars_, velocities_, colors_, indirect_[kRing];
    void* mapped_[kRing]{};
    int ring_ = 0;
    VkPipeline pipeline_{};
    VkPipelineLayout layout_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet set_{};
    VkShaderModule vs_{}, fs_{};

    // Feuilles visibles et, pour chacune, le nombre d'étoiles à dessiner (les plus brillantes d'abord).
    uint32_t selectLeaves(const Camera& cam, float exposure, double since, VkDrawIndirectCommand* out) {
        const double mLim = 2.5 * std::log10(static_cast<double>(exposure) / fluxMin);      // magnitude apparente la plus faible dessinée
        const double grow = kMaxSpeedKms * std::fabs(since) * kKmsToLyPerYear;
        const double tx = cam.tanHalf * cam.aspect * 1.02, ty = cam.tanHalf * 1.02;      // 2 % de marge : les points ont une taille
        const Vec3 planes[4] = {{cam.fwd.x * tx - cam.right.x, cam.fwd.y * tx - cam.right.y, cam.fwd.z * tx - cam.right.z},
                                {cam.fwd.x * tx + cam.right.x, cam.fwd.y * tx + cam.right.y, cam.fwd.z * tx + cam.right.z},
                                {cam.fwd.x * ty - cam.up.x, cam.fwd.y * ty - cam.up.y, cam.fwd.z * ty - cam.up.z},
                                {cam.fwd.x * ty + cam.up.x, cam.fwd.y * ty + cam.up.y, cam.fwd.z * ty + cam.up.z}};
        uint32_t k = 0;
        drawn = 0;
        for (uint32_t i = 0; i < file_.leafCount; ++i) {
            const GaiaLeaf& L = file_.leaves[i];
            const double lo[3] = {L.mn[0] - grow - cam.pos.x, L.mn[1] - grow - cam.pos.y, L.mn[2] - grow - cam.pos.z};
            const double hi[3] = {L.mx[0] + grow - cam.pos.x, L.mx[1] + grow - cam.pos.y, L.mx[2] + grow - cam.pos.z};
            bool inside = true;
            for (const Vec3& p : planes) {      // coin le plus avancé du côté intérieur du plan
                const double s = (p.x > 0 ? hi[0] : lo[0]) * p.x + (p.y > 0 ? hi[1] : lo[1]) * p.y + (p.z > 0 ? hi[2] : lo[2]) * p.z;
                if (s < 0) { inside = false; break; }
            }
            if (!inside) continue;
            double d2 = 0;
            for (int a = 0; a < 3; ++a) {
                const double c = lo[a] > 0 ? lo[a] : (hi[a] < 0 ? hi[a] : 0.0);
                d2 += c * c;
            }
            uint32_t take = L.n;
            if (d2 > 0) {
                const double dPc = std::sqrt(d2) / 3.2615638;
                const double absLim = mLim - 5.0 * std::log10(dPc / 10.0);      // magnitude absolue la plus faible qui compte
                uint32_t a = 0, b = L.n;      // première étoile trop faible (les magnitudes croissent dans la feuille)
                while (a < b) {
                    const uint32_t m = (a + b) / 2;
                    if (file_.magnitude(L.first + m) <= absLim) a = m + 1;
                    else b = m;
                }
                take = a;
            }
            if (take == 0) continue;
            out[k++] = {take, 1, static_cast<uint32_t>(L.first), 0};
            drawn += take;
        }
        return k;
    }

    void createPipeline(const Gpu& g, VkFormat fmt) {
        VkDescriptorSetLayoutBinding binds[3];
        for (uint32_t i = 0; i < 3; ++i) binds[i] = {i, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_VERTEX_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 3;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement Gaia");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 3};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 1;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve Gaia");
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = 1;
        da.pSetLayouts = &setLayout_;
        check(vkAllocateDescriptorSets(g.dev, &da, &set_), "jeu Gaia");
        const VkDescriptorBufferInfo infos[3] = {{stars_.buf, 0, VK_WHOLE_SIZE}, {velocities_.buf, 0, VK_WHOLE_SIZE}, {colors_.buf, 0, VK_WHOLE_SIZE}};
        VkWriteDescriptorSet w[3];
        for (uint32_t i = 0; i < 3; ++i) {
            w[i] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
            w[i].dstSet = set_;
            w[i].dstBinding = i;
            w[i].descriptorCount = 1;
            w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            w[i].pBufferInfo = &infos[i];
        }
        vkUpdateDescriptorSets(g.dev, 3, w, 0, nullptr);

        vs_ = shader(g, "gaia.vert.spv");
        fs_ = shader(g, "etoiles.frag.spv");      // même tache ronde que les étoiles du catalogue principal
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
        const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(PushConstants)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement Gaia");
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
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline_), "pipeline Gaia");
    }
};

}  // namespace
