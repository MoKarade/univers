// Appli PC « Univers » : la lumière déviée par la gravité (relativité générale), appliquée à toute l'image des étoiles,
// galaxies et astéroïdes, avant le dessin des planètes et du Soleil (qui sont les masses elles-mêmes).
//
// Masses prises en compte (choix validé par Marc le 13/11/2026 : seulement ce qui se voit) :
//   - le Soleil, Jupiter et Saturne : champ faible, angle exact pour une source à l'infini. Les positions Gaia sont publiées
//     SANS la déviation du Soleil : l'ajouter est donc juste, sans double compte. Visible seulement près du bord du Soleil
//     au champ le plus serré (1,75″ au bord : ~4 pixels à 0,5°) ;
//   - des trous noirs à masse et distance mesurées : rayon suivi pas à pas autour d'un trou noir sans rotation
//     (Schwarzschild), table recalculée quand la caméra se déplace ; ombre noire là où la lumière est capturée.
// Pas fait sur chaque point (dit à l'écran) : lentille faible des grandes structures (déformation ~1 %, 0,1 pixel) et
// micro-lentilles d'étoile à étoile (1/200 de pixel au plus fort) : invisibles à l'écran.
#pragma once
#include "commun.h"
#include "rendu_fenetre.h"
#include "trous_noirs.h"
#include "deviation.h"
#include <string>
#include <vector>

namespace lentille {

constexpr double kLyM = 9.4607304725808e15;
constexpr int kMaxLenses = 6;
constexpr int kTable = 2048;      // déviations par table de trou noir
constexpr int kMaxHoles = 2;      // tables de trous noirs actives à la fois

struct Mass {
    Vec3 pos;            // al
    double massSun;
    double radiusLy;     // rayon du corps (0 : trou noir)
    bool hole;
    int holeIndex;
};

// Pipeline d'un triangle plein écran (ecran.vert) vers une image du format donné, sans mélange.
inline VkPipeline fullScreenPipeline(const Gpu& g, VkPipelineLayout layout, VkShaderModule vs, VkShaderModule fs, VkFormat format) {
    VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
    stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
    stages[0].module = vs;
    stages[0].pName = "main";
    stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
    stages[1].module = fs;
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
    att.colorWriteMask = 0xF;
    VkPipelineColorBlendStateCreateInfo cb{VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO};
    cb.attachmentCount = 1;
    cb.pAttachments = &att;
    VkPipelineRenderingCreateInfo rci{VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO};
    rci.colorAttachmentCount = 1;
    rci.pColorAttachmentFormats = &format;
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
    pci.layout = layout;
    VkPipeline p{};
    check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &p), "pipeline plein écran");
    return p;
}

class LensPass {
public:
    bool ready = false;
    int activeCount = 0;          // masses appliquées à la dernière image
    std::string activeNames;      // pour l'écran
    std::vector<Mass> masses;

    void create(const Gpu& g, VkExtent2D extent) {
        target.create(g, HdrTarget::kFormat, extent, VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_SAMPLED_BIT);
        VkSamplerCreateInfo sci{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
        sci.magFilter = sci.minFilter = VK_FILTER_NEAREST;      // une étoile reste un point : pas de mélange de pixels
        sci.addressModeU = sci.addressModeV = sci.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        check(vkCreateSampler(g.dev, &sci, nullptr, &sampler_), "lentille : échantillonneur");
        for (int i = 0; i < kRing; ++i) {
            tables_[i] = createBuffer(g, sizeof(float) * kTable * kMaxHoles, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,
                                      VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            check(vkMapMemory(g.dev, tables_[i].mem, 0, VK_WHOLE_SIZE, 0, &mapped_[i]), "lentille : tables");
        }
        VkDescriptorSetLayoutBinding binds[2] = {{0, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr},
                                                 {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr}};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 2;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "lentille : agencement");
        const VkDescriptorPoolSize ps[2] = {{VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, kRing}, {VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, kRing}};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = kRing;
        dp.poolSizeCount = 2;
        dp.pPoolSizes = ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "lentille : réserve");
        for (int i = 0; i < kRing; ++i) {
            VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
            da.descriptorPool = pool_;
            da.descriptorSetCount = 1;
            da.pSetLayouts = &setLayout_;
            check(vkAllocateDescriptorSets(g.dev, &da, &sets_[i]), "lentille : jeu");
        }
        const VkPushConstantRange pcr{VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(Push)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "lentille : agencement du dessin");
        vs_ = shader(g, "ecran.vert.spv");
        fs_ = shader(g, "lentille.frag.spv");
        pipeline_ = fullScreenPipeline(g, layout_, vs_, fs_, HdrTarget::kFormat);
        ready = true;
    }
    // L'image source (étoiles, galaxies) : à rappeler après chaque changement de taille.
    void bindSource(const Gpu& g, VkImageView hdr) {
        for (int i = 0; i < kRing; ++i) {
            const VkDescriptorImageInfo img{sampler_, hdr, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL};
            const VkDescriptorBufferInfo buf{tables_[i].buf, 0, VK_WHOLE_SIZE};
            VkWriteDescriptorSet w[2] = {{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET}, {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET}};
            w[0].dstSet = w[1].dstSet = sets_[i];
            w[0].dstBinding = 0;
            w[0].descriptorCount = 1;
            w[0].descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
            w[0].pImageInfo = &img;
            w[1].dstBinding = 1;
            w[1].descriptorCount = 1;
            w[1].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            w[1].pBufferInfo = &buf;
            vkUpdateDescriptorSets(g.dev, 2, w, 0, nullptr);
        }
    }
    void resize(const Gpu& g, VkExtent2D extent) {
        target.release(g);
        target.create(g, HdrTarget::kFormat, extent, VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_SAMPLED_BIT);
    }

    // Choisit les masses dont l'effet dépasse un dixième de pixel dans le champ, et prépare leurs constantes.
    // Rend true si la passe doit être faite à cette image.
    bool prepare(const Camera& cam, uint32_t height) {
        const double pix = 2.0 * cam.tanHalf / height;      // un pixel, en radians
        const double halfDiag = std::atan(cam.tanHalf * std::sqrt(1.0 + cam.aspect * cam.aspect));
        push_ = Push{};
        push_.cam[0] = static_cast<float>(cam.tanHalf);
        push_.cam[1] = static_cast<float>(cam.aspect);
        push_.cam[3] = static_cast<float>(kTable);
        int n = 0, holes = 0;
        activeNames.clear();
        float* tab = static_cast<float*>(mapped_[ring_]);
        for (const Mass& m : masses) {
            if (n >= kMaxLenses) break;
            const Vec3 rel = m.pos - cam.pos;
            const double D = std::sqrt(dot(rel, rel));
            if (D <= m.radiusLy * 1.0001 || D <= 0) continue;
            const Vec3 l{rel.x / D, rel.y / D, rel.z / D};
            const double cosv = dot(l, cam.fwd);
            const double toLens = std::acos(std::clamp(cosv, -1.0, 1.0));
            const double gm = m.massSun * kGmSunOverC2M / kLyM;      // G M / c² en années-lumière
            const double twoGmD = 2.0 * gm / D;
            // plus forte déviation visible dans le champ : au bord du disque, ou à un pixel de la masse, ou au bord du champ
            const double bodyAngle = m.radiusLy > 0 ? std::asin(std::min(1.0, m.radiusLy / D)) : 0.0;
            const double chiNear = toLens <= halfDiag ? std::max(bodyAngle, pix) : toLens - halfDiag;
            const double alphaMax = twoGmD * 2.0 / std::max(std::sin(std::min(chiNear, kPi / 2)), 1e-30);
            if (!(alphaMax > 0.1 * pix)) continue;
            Lens& L = push_.lens[n];
            L.dir[0] = static_cast<float>(dot(l, cam.right));
            L.dir[1] = static_cast<float>(dot(l, cam.up));
            L.dir[2] = static_cast<float>(cosv);
            L.par[0] = static_cast<float>(twoGmD);
            L.par[1] = static_cast<float>(bodyAngle);
            if (m.hole && holes < kMaxHoles) {
                // table : de 0 à chiMax (200 G M / c² de paramètre d'impact, ou tout le ciel de près)
                const double r0 = D / gm;
                const double chiMax = r0 < 400.0 ? kPi : std::min(kPi, 200.0 / r0);
                float* t = tab + static_cast<size_t>(holes) * kTable;
                fillTable(holes, r0, chiMax, t);
                L.dir[3] = 1.0f;
                L.par[2] = static_cast<float>(holes * kTable);
                L.par[3] = static_cast<float>(chiMax);
                ++holes;
            }
            if (!activeNames.empty()) activeNames += ", ";
            activeNames += m.hole ? kHoles[m.holeIndex].name : nameOf(m);
            ++n;
        }
        push_.cam[2] = static_cast<float>(n);
        activeCount = n;
        return n > 0;
    }
    // Dans une passe de dessin sur `target`, l'image source déjà en lecture.
    void draw(VkCommandBuffer cmd, VkExtent2D extent) {
        const VkViewport vp{0, 0, static_cast<float>(extent.width), static_cast<float>(extent.height), 0, 1};
        const VkRect2D sc{{0, 0}, extent};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &sets_[ring_], 0, nullptr);
        vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(Push), &push_);
        vkCmdDraw(cmd, 3, 1, 0, 0);
        ring_ = (ring_ + 1) % kRing;
    }
    void release(const Gpu& g) {
        if (!ready) return;
        target.release(g);
        for (int i = 0; i < kRing; ++i) {
            vkUnmapMemory(g.dev, tables_[i].mem);
            destroy(g, tables_[i]);
        }
        vkDestroyPipeline(g.dev, pipeline_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroySampler(g.dev, sampler_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
        ready = false;
    }
    Target target;
    std::vector<std::string> bodyNames;      // nom de chaque masse non trou noir (même ordre que masses)

private:
    static constexpr int kRing = 4;
    struct Lens { float dir[4]; float par[4]; };
    struct Push { float cam[4]; Lens lens[kMaxLenses]; };
    static_assert(sizeof(Push) <= 256, "constantes de la lentille : 256 octets au plus");
    Push push_{};
    VkSampler sampler_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet sets_[kRing]{};
    VkPipelineLayout layout_{};
    VkPipeline pipeline_{};
    VkShaderModule vs_{}, fs_{};
    Buffer tables_[kRing];
    void* mapped_[kRing]{};
    int ring_ = 0;
    // Dernière table calculée par emplacement, pour ne pas la refaire si la caméra a peu bougé (moins de 0,5 %).
    double lastR0_[kMaxHoles]{}, lastChiMax_[kMaxHoles]{};
    std::vector<float> cache_[kMaxHoles];
    void fillTable(int slot, double r0, double chiMax, float* out) {
        if (cache_[slot].size() != kTable || std::fabs(r0 / lastR0_[slot] - 1.0) > 0.005 || chiMax != lastChiMax_[slot]) {
            cache_[slot].resize(kTable);
            for (int i = 0; i < kTable; ++i) {
                const double chi = chiMax * i / (kTable - 1.0);
                cache_[slot][i] = static_cast<float>(i == 0 ? -1.0 : traceRay(r0, chi));
            }
            lastR0_[slot] = r0;
            lastChiMax_[slot] = chiMax;
        }
        std::memcpy(out, cache_[slot].data(), sizeof(float) * kTable);
    }
    std::string nameOf(const Mass& m) const {
        for (size_t i = 0; i < masses.size(); ++i)
            if (&masses[i] == &m && i < bodyNames.size()) return bodyNames[i];
        return "masse";
    }
};

}  // namespace lentille
