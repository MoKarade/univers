// Appli PC « Univers » : la lueur de la Voie lactée (disque, bras, bulbe, barre) et sa poussière.
// Fichier voie_lactee.bin écrit par pipeline/natif/voie_lactee.py, qui décrit les sources et ce qui est supposé.
//
// Rendu : pour chaque pixel, un rayon traverse la grille (192 pas, décalés au hasard d'un pixel à l'autre) ; la lumière de
// chaque pas est atténuée par la poussière rencontrée avant lui. La grille ne contient que la lumière qui manque aux étoiles
// dessinées une à une (Gaia DR3, catalogue principal) : rien n'est compté deux fois. Le bulbe et la barre sont calculés
// dans le shader, tournés de l'angle du moment (phys::galaxie::barAngleAt, natif/physique/galaxie_orbites.h).
// Les étoiles ne sont pas assombries ici : leurs magnitudes mesurées contiennent déjà la poussière vue du Soleil.
#pragma once
#include "commun.h"
#include "../physique/galaxie_orbites.h"

namespace {

struct MilkyWayParams {      // copie de l'en-tête de voie_lactee.bin (voir ENTETE dans le script)
    float nx, ny, nz, halfXY, halfZ, r0, sun[3], gal2ecl[9];
    float bulgeLum, bulgeH[3];
    float barLum, barHalfLength, barH, barHFine, barFineShare;
    float barAngle2000, barOmega, armContrast;
    float lnx, lny, lnz, lcell;
};

struct MilkyWayUbo {      // std140 : tout en vec4
    float camGrid[4];      // position de la caméra dans le repère de la grille (kpc) ; w : rien
    float right[4];        // vecteurs de la caméra dans le repère galactique, déjà multipliés par tan(champ/2)
    float up[4];
    float fwd[4];
    float color[4];        // couleur de la lumière intégrée ; w : facteur (exposition × constantes, voir draw)
    float grid[4];         // demi-côté xy, demi-hauteur z (kpc) ; Soleil x, y
    float sunZ[4];         // Soleil z ; côté d'une case locale (pc) ; nombre de cases locales x, y
    float bulge[4];        // luminosité / (8π hx hy hz), en L_sol/pc³ ; puis hx, hy, hz (kpc)
    float bar[4];          // luminosité de la barre longue ; demi-longueur ; hauteur mince ; hauteur très mince
    float bar2[4];         // part très mince ; cos et sin de l'angle de la barre ; nombre de cases locales z
    float frame[4];        // hauteur de l'image en pixels ; tan(champ/2) ; aléa de l'image ; rien
};

class MilkyWayRenderer {
public:
    bool ready = false;
    MilkyWayParams par{};

    bool create(const Gpu& g, const std::string& path, VkFormat hdrFormat) {
        std::ifstream f(path, std::ios::binary);
        if (!f) return false;
        char magic[8];
        f.read(magic, 8);
        if (!f || std::memcmp(magic, "UNIVMW01", 8) != 0) return false;
        f.read(reinterpret_cast<char*>(&par), sizeof(par));
        f.seekg(1024);
        const size_t nBig = static_cast<size_t>(par.nx) * static_cast<size_t>(par.ny) * static_cast<size_t>(par.nz);
        const size_t nLoc = static_cast<size_t>(par.lnx) * static_cast<size_t>(par.lny) * static_cast<size_t>(par.lnz);
        std::vector<uint16_t> big(nBig * 2), loc(nLoc);
        f.read(reinterpret_cast<char*>(big.data()), static_cast<std::streamsize>(big.size() * 2));
        f.read(reinterpret_cast<char*>(loc.data()), static_cast<std::streamsize>(loc.size() * 2));
        if (!f) return false;
        big_ = createVolume(g, VK_FORMAT_R16G16_SFLOAT, static_cast<uint32_t>(par.nx), static_cast<uint32_t>(par.ny), static_cast<uint32_t>(par.nz), big.data(), big.size() * 2);
        local_ = createVolume(g, VK_FORMAT_R16_SFLOAT, static_cast<uint32_t>(par.lnx), static_cast<uint32_t>(par.lny), static_cast<uint32_t>(par.lnz), loc.data(), loc.size() * 2);
        for (auto& u : ubo_) {
            u = createBuffer(g, sizeof(MilkyWayUbo), VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        }
        for (int i = 0; i < kRing; ++i) check(vkMapMemory(g.dev, ubo_[i].mem, 0, sizeof(MilkyWayUbo), 0, &mapped_[i]), "Voie lactée");
        // Couleur intégrée de la Galaxie : B-V = 0,744 (Licquia, Newman et Bershady 2015, table 3), même conversion que les étoiles.
        const auto c = colorOfBv(0.744);
        for (int k = 0; k < 3; ++k) color_[k] = c[k] / 255.0f;
        createPipeline(g, hdrFormat);
        ready = true;
        return true;
    }

    // Angle de la barre (rad, depuis l'axe x galactique vers y), years : années depuis J2000,0. Même fonction que les
    // orbites des étoiles du fil de la gravité (natif/physique/galaxie_orbites.h).
    double barAngle(double years) const { return phys::galaxie::barAngleAt(years * 1e-9); }

    // Dans la passe en grande dynamique, avant les étoiles. exposure : la même que pour les étoiles.
    void draw(VkCommandBuffer cmd, const Camera& cam, uint32_t width, uint32_t height, float exposure, double years) {
        if (!ready) return;
        auto toGal = [&](Vec3 v) {      // écliptique -> galactique : transposée de gal2ecl
            const float* m = par.gal2ecl;
            return Vec3{m[0] * v.x + m[3] * v.y + m[6] * v.z, m[1] * v.x + m[4] * v.y + m[7] * v.z, m[2] * v.x + m[5] * v.y + m[8] * v.z};
        };
        constexpr double kLyPerKpc = 3261.5638;
        MilkyWayUbo u{};
        const Vec3 p = toGal(cam.pos);
        u.camGrid[0] = static_cast<float>(p.x / kLyPerKpc + par.sun[0]);
        u.camGrid[1] = static_cast<float>(p.y / kLyPerKpc + par.sun[1]);
        u.camGrid[2] = static_cast<float>(p.z / kLyPerKpc + par.sun[2]);
        const Vec3 r = toGal(cam.right), up = toGal(cam.up), fw = toGal(cam.fwd);
        const double tx = cam.tanHalf * cam.aspect, ty = cam.tanHalf;
        const float rr[4] = {static_cast<float>(r.x * tx), static_cast<float>(r.y * tx), static_cast<float>(r.z * tx), 0};
        const float uu[4] = {static_cast<float>(up.x * ty), static_cast<float>(up.y * ty), static_cast<float>(up.z * ty), 0};
        const float ff[4] = {static_cast<float>(fw.x), static_cast<float>(fw.y), static_cast<float>(fw.z), 0};
        std::memcpy(u.right, rr, 16);
        std::memcpy(u.up, uu, 16);
        std::memcpy(u.fwd, ff, 16);
        // Lumière d'un volume vue dans un pixel : exposition × 10^(-0,4 × 4,83) × 100 × angle solide du pixel × ∫ j ds
        // (j en L_sol/pc³, s en pc) : c'est la loi des étoiles (etoiles.vert) appliquée à chaque élément de volume.
        const double pix = 2.0 * cam.tanHalf / height;
        const double k = exposure * std::pow(10.0, -0.4 * 4.83) * 100.0 * pix * pix;
        for (int i = 0; i < 3; ++i) u.color[i] = color_[i];
        u.color[3] = static_cast<float>(k);
        u.grid[0] = par.halfXY;
        u.grid[1] = par.halfZ;
        u.grid[2] = par.sun[0];
        u.grid[3] = par.sun[1];
        u.sunZ[0] = par.sun[2];
        u.sunZ[1] = par.lcell;
        u.sunZ[2] = par.lnx;
        u.sunZ[3] = par.lny;
        u.bulge[0] = static_cast<float>(par.bulgeLum / (8.0 * kPi * par.bulgeH[0] * par.bulgeH[1] * par.bulgeH[2] * 1e9));
        for (int i = 0; i < 3; ++i) u.bulge[1 + i] = par.bulgeH[i];
        u.bar[0] = par.barLum;
        u.bar[1] = par.barHalfLength;
        u.bar[2] = par.barH;
        u.bar[3] = par.barHFine;
        const double a = barAngle(years);
        u.bar2[0] = par.barFineShare;
        u.bar2[1] = static_cast<float>(std::cos(a));
        u.bar2[2] = static_cast<float>(std::sin(a));
        u.bar2[3] = par.lnz;
        u.frame[0] = static_cast<float>(height);
        u.frame[1] = static_cast<float>(cam.tanHalf);
        u.frame[2] = static_cast<float>(frame_++ % 64);
        std::memcpy(mapped_[ring_], &u, sizeof(u));

        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        const VkRect2D sc{{0, 0}, {width, height}};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &sets_[ring_], 0, nullptr);
        vkCmdDraw(cmd, 3, 1, 0, 0);
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
        vkDestroySampler(g.dev, sampler_, nullptr);
        for (Volume* v : {&big_, &local_}) {
            vkDestroyImageView(g.dev, v->view, nullptr);
            vkDestroyImage(g.dev, v->image, nullptr);
            vkFreeMemory(g.dev, v->mem, nullptr);
        }
        for (int i = 0; i < kRing; ++i) {
            vkUnmapMemory(g.dev, ubo_[i].mem);
            destroy(g, ubo_[i]);
        }
        ready = false;
    }

private:
    struct Volume {
        VkImage image{};
        VkDeviceMemory mem{};
        VkImageView view{};
    };
    static constexpr int kRing = 4;
    Volume big_, local_;
    Buffer ubo_[kRing];
    void* mapped_[kRing]{};
    VkDescriptorSet sets_[kRing]{};
    int ring_ = 0;
    uint32_t frame_ = 0;
    float color_[3]{1, 1, 1};
    VkSampler sampler_{};
    VkPipeline pipeline_{};
    VkPipelineLayout layout_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkShaderModule vs_{}, fs_{};

    static Volume createVolume(const Gpu& g, VkFormat fmt, uint32_t w, uint32_t h, uint32_t d, const void* data, size_t bytes) {
        Volume v;
        VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
        ii.imageType = VK_IMAGE_TYPE_3D;
        ii.format = fmt;
        ii.extent = {w, h, d};
        ii.mipLevels = 1;
        ii.arrayLayers = 1;
        ii.samples = VK_SAMPLE_COUNT_1_BIT;
        ii.usage = VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
        check(vkCreateImage(g.dev, &ii, nullptr, &v.image), "volume");
        VkMemoryRequirements mr;
        vkGetImageMemoryRequirements(g.dev, v.image, &mr);
        VkMemoryAllocateInfo mai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        mai.allocationSize = mr.size;
        mai.memoryTypeIndex = memoryType(g, mr.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        check(vkAllocateMemory(g.dev, &mai, nullptr, &v.mem), "mémoire du volume");
        vkBindImageMemory(g.dev, v.image, v.mem, 0);
        Buffer staging = createBuffer(g, bytes, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, bytes, 0, &p), "accès au volume");
        std::memcpy(p, data, bytes);
        vkUnmapMemory(g.dev, staging.mem);
        VkCommandBuffer cmd = beginOnce(g);
        transition(cmd, v.image, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 0, VK_ACCESS_TRANSFER_WRITE_BIT,
                   VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT);
        VkBufferImageCopy region{};
        region.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
        region.imageExtent = {w, h, d};
        vkCmdCopyBufferToImage(cmd, staging.buf, v.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &region);
        transition(cmd, v.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_ACCESS_TRANSFER_WRITE_BIT,
                   VK_ACCESS_SHADER_READ_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        endOnce(g, cmd);
        destroy(g, staging);
        VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
        vi.image = v.image;
        vi.viewType = VK_IMAGE_VIEW_TYPE_3D;
        vi.format = fmt;
        vi.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        check(vkCreateImageView(g.dev, &vi, nullptr, &v.view), "vue du volume");
        return v;
    }

    void createPipeline(const Gpu& g, VkFormat fmt) {
        VkSamplerCreateInfo sci{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
        sci.magFilter = sci.minFilter = VK_FILTER_LINEAR;
        sci.addressModeU = sci.addressModeV = sci.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER;
        sci.borderColor = VK_BORDER_COLOR_FLOAT_TRANSPARENT_BLACK;      // hors de la grille : ni lumière ni poussière
        check(vkCreateSampler(g.dev, &sci, nullptr, &sampler_), "échantillonneur de la Voie lactée");
        const VkDescriptorSetLayoutBinding binds[3] = {{0, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr},
                                                       {1, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr},
                                                       {2, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr}};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 3;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement de la Voie lactée");
        const VkDescriptorPoolSize ps[2] = {{VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, kRing}, {VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 2 * kRing}};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = kRing;
        dp.poolSizeCount = 2;
        dp.pPoolSizes = ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve de la Voie lactée");
        VkDescriptorSetLayout layouts[kRing];
        for (auto& l : layouts) l = setLayout_;
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = kRing;
        da.pSetLayouts = layouts;
        check(vkAllocateDescriptorSets(g.dev, &da, sets_), "jeux de la Voie lactée");
        for (int i = 0; i < kRing; ++i) {
            const VkDescriptorBufferInfo bi{ubo_[i].buf, 0, sizeof(MilkyWayUbo)};
            const VkDescriptorImageInfo im[2] = {{sampler_, big_.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL},
                                                 {sampler_, local_.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL}};
            VkWriteDescriptorSet w[3];
            for (uint32_t b = 0; b < 3; ++b) {
                w[b] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
                w[b].dstSet = sets_[i];
                w[b].dstBinding = b;
                w[b].descriptorCount = 1;
                w[b].descriptorType = b == 0 ? VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER : VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
                if (b == 0) w[b].pBufferInfo = &bi;
                else w[b].pImageInfo = &im[b - 1];
            }
            vkUpdateDescriptorSets(g.dev, 3, w, 0, nullptr);
        }
        vs_ = shader(g, "ecran.vert.spv");      // un triangle qui couvre l'écran
        fs_ = shader(g, "voie_lactee.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement de la Voie lactée");
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
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline_), "pipeline de la Voie lactée");
    }
};

}  // namespace
