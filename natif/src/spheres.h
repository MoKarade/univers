// Appli PC « Univers » : les astres vus de près, comme de vraies sphères portant leur carte de surface.
//
// Cartes : Solar System Scope (https://www.solarsystemscope.com/textures/, licence CC BY 4.0), les mêmes que la page
// mais en haute définition (8192 x 4096 pour la Terre, la Lune, Mars, Jupiter, Saturne, Mercure et le Soleil).
// Elles sont décodées dans un fil à part pendant que la fenêtre s'affiche déjà ; tant qu'une carte n'est pas prête,
// l'astre reste un point. Orientation : orientation.h. Éclairage : le Soleil, surface mate ; la nuit est noire.
#pragma once
#include <stb_image.h>

#include <atomic>
#include <mutex>
#include <thread>

#include "orientation.h"
#include "simulation.h"

namespace univers {

struct SphereMap {
    int naif;
    const char* file;
};
constexpr SphereMap kSphereMaps[] = {
    {eph::kSun, "8k_sun.jpg"},         {eph::kMercury, "8k_mercury.jpg"},     {eph::kVenus, "4k_venus_atmosphere.jpg"}, {eph::kEarth, "8k_earth_daymap.jpg"},
    {eph::kMoon, "8k_moon.jpg"},       {eph::kMarsBary, "8k_mars.jpg"},       {eph::kJupiterBary, "8k_jupiter.jpg"},    {eph::kSaturnBary, "8k_saturn.jpg"},
    {eph::kUranusBary, "2k_uranus.jpg"}, {eph::kNeptuneBary, "2k_neptune.jpg"},
    {-1, "8k_saturn_ring_alpha.png"},      // anneaux de Saturne (couleur et opacité selon la distance au centre) : aucun astre à lui seul
    {-2, "8k_earth_nightmap.jpg"},         // lumières de nuit de la Terre (composite de mesures par satellite, NASA « Black Marble », via Solar System Scope)
};
constexpr int kRingMap = 10, kNightMap = 11;
// Étendue de l'image des anneaux, en km du centre de Saturne : 72 650 à 140 150. [Calé ici sur deux repères lus dans
// l'image : la division de Cassini (vers 119 900 km) et le bord extérieur de l'anneau A (136 775 km) ; la source ne
// documente pas cette étendue : À vérifier.]
constexpr double kRingInnerKm = 72650.0, kRingOuterKm = 140150.0;
constexpr int kSphereMapCount = static_cast<int>(sizeof(kSphereMaps) / sizeof(kSphereMaps[0]));

struct SpherePush {
    float centre[4], droite[4], haut[4], avant[4], soleil[4], rot0[4], rot1[4], rot2[4], ombre[4], ombre2[4];
};

class SphereRenderer {
public:
    void create(const Gpu& g, VkFormat hdrFormat, const std::string& textureDir) {
        VkSamplerCreateInfo sci{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
        sci.magFilter = sci.minFilter = VK_FILTER_LINEAR;
        sci.mipmapMode = VK_SAMPLER_MIPMAP_MODE_LINEAR;
        sci.addressModeU = VK_SAMPLER_ADDRESS_MODE_REPEAT;
        sci.addressModeV = sci.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        sci.anisotropyEnable = VK_TRUE;
        sci.maxAnisotropy = 8.0f;
        sci.maxLod = VK_LOD_CLAMP_NONE;
        check(vkCreateSampler(g.dev, &sci, nullptr, &sampler_), "échantillonneur des cartes");
        const VkDescriptorSetLayoutBinding bind[2] = {{0, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr},
                                                      {1, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr}};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 2;
        dl.pBindings = bind;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement des cartes");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 2 * kSphereMapCount};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = kSphereMapCount;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve des cartes");
        const VkPushConstantRange pcr{VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(SpherePush)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement des sphères");
        vs_ = shader(g, "ecran.vert.spv");
        fs_ = shader(g, "sphere.frag.spv");
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
        VkPipelineColorBlendAttachmentState att{};      // la sphère cache ce qui est derrière ; son bord est adouci
        att.blendEnable = VK_TRUE;
        att.srcColorBlendFactor = VK_BLEND_FACTOR_SRC_ALPHA;
        att.dstColorBlendFactor = VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
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
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline_), "pipeline des sphères");

        // Décodage des cartes dans un fil à part : la fenêtre n'attend pas.
        loader_ = std::thread([this, textureDir]() {
            for (int i = 0; i < kSphereMapCount && !stop_; ++i) {
                int w = 0, h = 0, comp = 0;
                unsigned char* px = stbi_load((textureDir + "/" + kSphereMaps[i].file).c_str(), &w, &h, &comp, 4);
                if (!px) continue;      // carte absente : l'astre reste un point
                std::lock_guard<std::mutex> lock(mutex_);
                decoded_.push_back({i, w, h, px});
            }
        });
    }

    // À appeler entre deux images : envoie à la carte graphique au plus une carte décodée.
    void uploadPending(const Gpu& g) {
        Decoded d{};
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (decoded_.empty()) return;
            d = decoded_.back();
            decoded_.pop_back();
        }
        Texture& t = textures_[d.index];
        const auto w = static_cast<uint32_t>(d.w), h = static_cast<uint32_t>(d.h);
        const uint32_t mips = 1 + static_cast<uint32_t>(std::floor(std::log2(static_cast<double>(std::max(w, h)))));
        VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
        ii.imageType = VK_IMAGE_TYPE_2D;
        ii.format = VK_FORMAT_R8G8B8A8_SRGB;      // la carte est une image pour écran : la carte graphique la ramène en lumière linéaire
        ii.extent = {w, h, 1};
        ii.mipLevels = mips;
        ii.arrayLayers = 1;
        ii.samples = VK_SAMPLE_COUNT_1_BIT;
        ii.usage = VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
        check(vkCreateImage(g.dev, &ii, nullptr, &t.image), "carte de surface");
        VkMemoryRequirements mr;
        vkGetImageMemoryRequirements(g.dev, t.image, &mr);
        VkMemoryAllocateInfo mai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        mai.allocationSize = mr.size;
        mai.memoryTypeIndex = memoryType(g, mr.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        check(vkAllocateMemory(g.dev, &mai, nullptr, &t.mem), "mémoire de la carte");
        vkBindImageMemory(g.dev, t.image, t.mem, 0);
        const VkDeviceSize bytes = static_cast<VkDeviceSize>(w) * h * 4;
        Buffer staging = createBuffer(g, bytes, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, bytes, 0, &p), "accès à la carte");
        std::memcpy(p, d.pixels, bytes);
        vkUnmapMemory(g.dev, staging.mem);
        stbi_image_free(d.pixels);

        VkCommandBuffer cmd = beginOnce(g);
        auto barrier = [&](uint32_t level, VkImageLayout from, VkImageLayout to, VkAccessFlags sa, VkAccessFlags da, VkPipelineStageFlags ss, VkPipelineStageFlags ds2) {
            VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
            b.oldLayout = from;
            b.newLayout = to;
            b.srcAccessMask = sa;
            b.dstAccessMask = da;
            b.srcQueueFamilyIndex = b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            b.image = t.image;
            b.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, level, 1, 0, 1};
            vkCmdPipelineBarrier(cmd, ss, ds2, 0, 0, nullptr, 0, nullptr, 1, &b);
        };
        for (uint32_t l = 0; l < mips; ++l)
            barrier(l, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 0, VK_ACCESS_TRANSFER_WRITE_BIT, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                    VK_PIPELINE_STAGE_TRANSFER_BIT);
        VkBufferImageCopy region{};
        region.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
        region.imageExtent = {w, h, 1};
        vkCmdCopyBufferToImage(cmd, staging.buf, t.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &region);
        // Niveaux réduits (pour les vues lointaines) : chaque niveau est la moitié du précédent.
        int32_t mw = static_cast<int32_t>(w), mh = static_cast<int32_t>(h);
        for (uint32_t l = 1; l < mips; ++l) {
            barrier(l - 1, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, VK_ACCESS_TRANSFER_WRITE_BIT, VK_ACCESS_TRANSFER_READ_BIT,
                    VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT);
            VkImageBlit blit{};
            blit.srcSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, l - 1, 0, 1};
            blit.dstSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, l, 0, 1};
            blit.srcOffsets[1] = {mw, mh, 1};
            mw = std::max(mw / 2, 1);
            mh = std::max(mh / 2, 1);
            blit.dstOffsets[1] = {mw, mh, 1};
            vkCmdBlitImage(cmd, t.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, t.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &blit, VK_FILTER_LINEAR);
            barrier(l - 1, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_ACCESS_TRANSFER_READ_BIT, VK_ACCESS_SHADER_READ_BIT,
                    VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        }
        barrier(mips - 1, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_ACCESS_TRANSFER_WRITE_BIT, VK_ACCESS_SHADER_READ_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        endOnce(g, cmd);
        destroy(g, staging);

        VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
        vi.image = t.image;
        vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
        vi.format = ii.format;
        vi.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, mips, 0, 1};
        check(vkCreateImageView(g.dev, &vi, nullptr, &t.view), "vue de la carte");
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = 1;
        da.pSetLayouts = &setLayout_;
        check(vkAllocateDescriptorSets(g.dev, &da, &t.set), "ressources de la carte");
        t.ready = true;
        // Chaque carte prête : sa propre image aux deux emplacements, sauf Saturne qui reçoit l'image de ses anneaux
        // dès qu'elle est prête elle aussi.
        for (int k = 0; k < kSphereMapCount; ++k) {
            const Texture& own = textures_[k];
            if (!own.ready) continue;
            const bool ringed = kSphereMaps[k].naif == eph::kSaturnBary && textures_[kRingMap].ready;
            const bool lit = kSphereMaps[k].naif == eph::kEarth && textures_[kNightMap].ready;
            const VkDescriptorImageInfo info[2] = {{sampler_, own.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL},
                                                   {sampler_, ringed ? textures_[kRingMap].view : lit ? textures_[kNightMap].view : own.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL}};
            VkWriteDescriptorSet wr[2] = {{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET}, {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET}};
            for (uint32_t j = 0; j < 2; ++j) {
                wr[j].dstSet = own.set;
                wr[j].dstBinding = j;
                wr[j].descriptorCount = 1;
                wr[j].descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
                wr[j].pImageInfo = &info[j];
            }
            vkUpdateDescriptorSets(g.dev, 2, wr, 0, nullptr);
        }
    }

    // Distance de la sphère la plus proche dessinée à cette image (infinie s'il n'y en a pas).
    double nearestDist() const {
        double d = 1e300;
        for (const Draw& x : draws_) d = std::min(d, x.dist);
        return d;
    }

    bool allLoaded() const {
        for (const auto& t : textures_)
            if (!t.ready) return false;
        return true;
    }

    // Choisit les astres assez gros à l'écran pour être dessinés en sphère (au moins 1,5 pixel de rayon), du plus
    // lointain au plus proche. Rend, pour chaque astre du simulateur, s'il est dessiné en sphère.
    void prepare(const Sim& sim, const Camera& cam, uint32_t width, uint32_t height, std::vector<bool>& asSphere) {
        draws_.clear();
        asSphere.assign(sim.bodies.size(), false);
        const double pixel = 2.0 * cam.tanHalf / height;      // taille angulaire d'un pixel
        const double days = sim.years * 365.25 + kTdbMinusUtc / 86400.0;
        for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i) {
            const Body& b = sim.bodies[static_cast<size_t>(i)];
            // rayon à la date montrée : celui du cycle de vie (cycle_appli.h) pour le Soleil et les étoiles nommées
            const double radiusKm = b.lifeOn ? b.lifeRadiusKm : b.radiusKm;
            if (((b.kind == Kind::Star || b.kind == Kind::Sun) && radiusKm <= 0) || !sim.visible(i)) continue;
            // étoile (audit E3) : disque de son rayon calculé et de sa couleur, sans carte de surface (aucune n'est mesurée) ;
            // la carte du Soleil sert seulement à remplir l'emplacement de la ressource, elle n'est pas lue
            const bool star = b.kind == Kind::Star;
            const int naif = b.kind == Kind::Sun || star ? static_cast<int>(eph::kSun) : b.naif;
            int map = -1;
            for (int k = 0; k < kSphereMapCount; ++k)
                if (kSphereMaps[k].naif == naif && textures_[k].ready) map = k;
            if (map < 0) continue;
            const Vec3 p = sim.position(i), c = p - cam.pos;
            const double dist = std::sqrt(dot(c, c)), z = dot(c, cam.fwd);
            const double rho = (radiusKm / kLyInKm) / dist;
            if (z <= 0 || rho >= 0.95 || rho / pixel < 1.5) continue;
            ori::Mat3 m;
            if (!ori::eclipticToBody(naif, days, m)) continue;
            const bool ringed = naif == eph::kSaturnBary && textures_[kRingMap].ready;
            Draw d{};
            d.map = map;
            d.dist = dist;
            const Vec3 u = unit(c);
            const float fx = static_cast<float>(u.x), fy = static_cast<float>(u.y), fz = static_cast<float>(u.z);
            d.pc = SpherePush{{fx, fy, fz, static_cast<float>(rho)},
                              {static_cast<float>(cam.right.x), static_cast<float>(cam.right.y), static_cast<float>(cam.right.z), static_cast<float>(cam.tanHalf * cam.aspect)},
                              {static_cast<float>(cam.up.x), static_cast<float>(cam.up.y), static_cast<float>(cam.up.z), static_cast<float>(cam.tanHalf)},
                              {static_cast<float>(cam.fwd.x), static_cast<float>(cam.fwd.y), static_cast<float>(cam.fwd.z), static_cast<float>(pixel)},
                              {0, 0, 0, b.kind == Kind::Sun || star ? -kSunGain : kSurfaceGain},
                              {static_cast<float>(m.m[0][0]), static_cast<float>(m.m[0][1]), static_cast<float>(m.m[0][2]), ringed ? static_cast<float>(kRingInnerKm / b.radiusKm) : 0.0f},
                              {static_cast<float>(m.m[1][0]), static_cast<float>(m.m[1][1]), static_cast<float>(m.m[1][2]), ringed ? static_cast<float>(kRingOuterKm / b.radiusKm) : 0.0f},
                              {static_cast<float>(m.m[2][0]), static_cast<float>(m.m[2][1]), static_cast<float>(m.m[2][2]), 0},
                              {0, 0, 0, 0},
                              {0, 0, 0, 0}};
            const bool uniform = star || (b.kind == Kind::Sun && b.lifeOn && !b.lifeMapped);
            if (b.lifeOn && b.lifeBlack) {      // trou noir : disque noir de son ombre (2,6 rayons de Schwarzschild)
                d.pc.ombre[0] = d.pc.ombre[1] = d.pc.ombre[2] = 0.0f;
                d.pc.ombre[3] = -1.0f;
                d.pc.soleil[3] = -1e-6f;
            } else if (uniform) {      // couleur de l'étoile (lumière linéaire, plus grande composante 1) ; éclat de surface en (T / T☉)⁴
                const double bvNow = b.lifeOn ? b.lifeBv : b.bv;
                const auto c = colorOfBv(bvNow);
                const double r = std::pow(c[0] / 255.0, 2.2), gr = std::pow(c[1] / 255.0, 2.2), bl = std::pow(c[2] / 255.0, 2.2);
                const double mx = std::max({r, gr, bl, 1e-6});
                const double t = (b.lifeOn && b.lifeTeff > 0 ? b.lifeTeff : rayon_etoile::temperatureBv(bvNow)) / rayon_etoile::kTsoleil;
                d.pc.ombre[0] = static_cast<float>(r / mx);
                d.pc.ombre[1] = static_cast<float>(gr / mx);
                d.pc.ombre[2] = static_cast<float>(bl / mx);
                d.pc.ombre[3] = -1.0f;      // drapeau : pas de carte, cette couleur
                d.pc.soleil[3] = static_cast<float>(-kSunGain * std::clamp(t * t * t * t, 0.05, 20.0));
            } else if (b.kind == Kind::Sun) {
                if (b.lifeOn) {      // le Soleil à la date montrée : sa carte teintée par sa température, éclat de surface en (T / T☉)⁴
                    const auto c = colorOfBv(b.lifeBv), c0 = colorOfBv(kSunBv);
                    for (int k = 0; k < 3; ++k) d.pc.ombre[k] = static_cast<float>(std::pow(c[k] / 255.0, 2.2) / std::max(std::pow(c0[k] / 255.0, 2.2), 1e-4));
                    const float mx = std::max({d.pc.ombre[0], d.pc.ombre[1], d.pc.ombre[2], 1e-6f});
                    for (int k = 0; k < 3; ++k) d.pc.ombre[k] /= mx;
                    d.pc.ombre[3] = -2.0f;      // drapeau : la carte, teintée
                    const double t = b.lifeTeff / rayon_etoile::kTsoleil;
                    d.pc.soleil[3] = static_cast<float>(-kSunGain * std::clamp(t * t * t * t, 0.05, 20.0));
                }
            } else {
                const Vec3 toSun = unit(Vec3{-p.x, -p.y, -p.z});
                d.pc.soleil[0] = static_cast<float>(toSun.x);
                d.pc.soleil[1] = static_cast<float>(toSun.y);
                d.pc.soleil[2] = static_cast<float>(toSun.z);
                if (naif == eph::kEarth && textures_[kNightMap].ready) {
                    d.pc.rot2[3] = 1.0f;
                    d.pc.ombre2[1] = kNightGain;
                }
                // Éclipses : parmi la planète de cet astre et ses lunes, celui qui est le mieux aligné devant le Soleil.
                const double radius = b.radiusKm / kLyInKm, sunDist = std::sqrt(dot(p, p));
                d.pc.ombre2[0] = static_cast<float>(std::asin(std::min(1.0, (sim.bodies[0].lifeOn ? sim.bodies[0].lifeRadiusKm : 695700.0) / kLyInKm / sunDist)));
                double best = 1e300;
                for (int j = 0; j < static_cast<int>(sim.bodies.size()); ++j) {
                    const Body& o = sim.bodies[static_cast<size_t>(j)];
                    if (j == i || o.kind != Kind::Planet || !sim.visible(j) || o.radiusKm <= 0) continue;
                    if (o.parent != i && b.parent != j && !(b.parent > 0 && o.parent == b.parent)) continue;      // lune, planète, ou lune sœur
                    const Vec3 v = sim.position(j) - p;
                    const double along = dot(v, toSun);
                    if (along <= 0) continue;
                    const Vec3 perp{v.x - along * toSun.x, v.y - along * toSun.y, v.z - along * toSun.z};
                    const double miss = std::sqrt(dot(perp, perp)) - o.radiusKm / kLyInKm - radius;      // écart à l'alignement, en longueur
                    if (miss < best && miss < 4.0 * radius) {
                        best = miss;
                        d.pc.ombre[0] = static_cast<float>(v.x / radius);
                        d.pc.ombre[1] = static_cast<float>(v.y / radius);
                        d.pc.ombre[2] = static_cast<float>(v.z / radius);
                        d.pc.ombre[3] = static_cast<float>(o.radiusKm / b.radiusKm);
                    }
                }
            }
            // Rectangle de l'écran qui contient le disque.
            const double cx = (dot(c, cam.right) / (z * cam.tanHalf * cam.aspect) * 0.5 + 0.5) * width, cy = (-dot(c, cam.up) / (z * cam.tanHalf) * 0.5 + 0.5) * height;
            // marge : la perspective agrandit le disque de 1/cos²θ loin du centre de l'image (θ : angle hors de l'axe) ; avant, une
            // marge fixe de 1,6 coupait le disque d'un bord droit dans les coins (jusqu'à 2,06 à 16:9, audit E1)
            const double tx = (cx / width * 2.0 - 1.0) * cam.tanHalf * cam.aspect, ty = (cy / height * 2.0 - 1.0) * cam.tanHalf;
            const double rpx = rho / pixel * 1.15 * (1.0 + tx * tx + ty * ty) * (ringed ? kRingOuterKm / b.radiusKm : 1.0) + 3;
            const double x0 = std::clamp(cx - rpx, 0.0, static_cast<double>(width)), x1 = std::clamp(cx + rpx, 0.0, static_cast<double>(width));
            const double y0 = std::clamp(cy - rpx, 0.0, static_cast<double>(height)), y1 = std::clamp(cy + rpx, 0.0, static_cast<double>(height));
            if (x1 - x0 < 1 || y1 - y0 < 1) continue;
            d.scissor = {{static_cast<int32_t>(x0), static_cast<int32_t>(y0)}, {static_cast<uint32_t>(x1 - x0), static_cast<uint32_t>(y1 - y0)}};
            draws_.push_back(d);
            asSphere[static_cast<size_t>(i)] = true;
        }
        std::sort(draws_.begin(), draws_.end(), [](const Draw& a, const Draw& b) { return a.dist > b.dist; });
    }

    // À appeler dans la passe en grande dynamique, après les étoiles.
    void draw(VkCommandBuffer cmd, uint32_t width, uint32_t height) const {
        if (draws_.empty()) return;
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        for (const Draw& d : draws_) {
            vkCmdSetScissor(cmd, 0, 1, &d.scissor);
            vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &textures_[d.map].set, 0, nullptr);
            vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(SpherePush), &d.pc);
            vkCmdDraw(cmd, 3, 1, 0, 0);
        }
    }

    void release(const Gpu& g) {
        stop_ = true;
        if (loader_.joinable()) loader_.join();
        for (auto& d : decoded_) stbi_image_free(d.pixels);
        for (auto& t : textures_) {
            if (!t.ready) continue;
            vkDestroyImageView(g.dev, t.view, nullptr);
            vkDestroyImage(g.dev, t.image, nullptr);
            vkFreeMemory(g.dev, t.mem, nullptr);
        }
        vkDestroyPipeline(g.dev, pipeline_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroySampler(g.dev, sampler_, nullptr);
    }

private:
    // Réglage d'exposition des surfaces : choisi pour que le côté jour soit lisible à l'écran. En vraie lumière, une
    // planète proche serait des milliers de fois plus brillante que les étoiles et l'image serait blanche.
    static constexpr float kSurfaceGain = 2.6f, kSunGain = 9.0f;
    // Les lumières de nuit sont, en vrai, des dizaines de milliers de fois plus faibles que le côté jour : cet éclat est
    // un réglage d'affichage pour qu'elles se voient.
    static constexpr float kNightGain = 1.6f;

    struct Texture {
        VkImage image{};
        VkDeviceMemory mem{};
        VkImageView view{};
        VkDescriptorSet set{};
        bool ready = false;
    };
    struct Decoded {
        int index, w, h;
        unsigned char* pixels;
    };
    struct Draw {
        int map;
        double dist;
        SpherePush pc;
        VkRect2D scissor;
    };

    VkSampler sampler_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkPipelineLayout layout_{};
    VkPipeline pipeline_{};
    VkShaderModule vs_{}, fs_{};
    Texture textures_[kSphereMapCount];
    std::vector<Draw> draws_;
    std::thread loader_;
    std::mutex mutex_;
    std::vector<Decoded> decoded_;
    std::atomic<bool> stop_{false};
};

}  // namespace univers