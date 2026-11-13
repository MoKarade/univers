// Appli PC « Univers » : Andromède, le Triangle et les deux Nuages de Magellan d'après leurs VRAIES photos.
//
// Photos : Digitized Sky Survey 2 (plaques bleue et rouge), préparées par pipeline/natif/galaxies_images.py
// (fond du ciel retiré, étoiles de premier plan retirées, bord adouci) et décrites dans galaxies_images.tsv.
// Mise en place en 3D : chaque point de la photo est une direction du ciel vue du Soleil ; on la prolonge jusqu'au plan
// du disque de la galaxie, défini par son angle de position et son inclinaison MESURÉS, à la distance de l'astre dans
// l'appli. Vue d'ici, on retrouve donc exactement la photo ; vue d'ailleurs, le disque est vu de biais ou de face.
// Limites : le disque est supposé mince (pas d'épaisseur) ; le côté proche du disque n'est pas mesuré pour toutes
// [à vérifier pour M33] ; le Petit Nuage, épais et irrégulier, est posé face à nous [modèle].
// Éclat : la somme de la photo est recalée sur la magnitude absolue V publiée, avec la même loi que les étoiles ;
// l'éclat de surface d'un disque mince vu sous l'angle θ de sa normale vaut celui vu de face divisé par |cos θ|.
#pragma once
#include <stb_image.h>

#include <fstream>
#include <sstream>

#include "simulation.h"

namespace {

class GalaxyImages {
public:
    bool ready = false;
    int count = 0;

    // dir : dossier des données (galaxies_images.tsv et les photos). Lit tout tout de suite (quelques Mo).
    void create(const Gpu& g, VkFormat hdrFormat, const std::string& dir, const Sim& sim) {
        std::ifstream f(dir + "/galaxies_images.tsv");
        if (!f) return;
        std::string line;
        while (std::getline(f, line)) {
            std::istringstream in(line);
            std::string name, file, num[6];
            if (!std::getline(in, name, '\t') || !std::getline(in, file, '\t')) continue;
            bool ok = true;
            for (auto& s : num) ok = ok && static_cast<bool>(std::getline(in, s, '\t'));
            if (!ok) continue;
            int body = -1;
            for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
                if (sim.bodies[static_cast<size_t>(i)].name == name) body = i;
            if (body < 0) continue;      // astre absent de l'appli : rien à poser
            Item it{};
            it.body = body;
            const double ra = std::atof(num[0].c_str()), dec = std::atof(num[1].c_str()), fov = std::atof(num[2].c_str());
            const double pa = std::atof(num[3].c_str()), incl = std::atof(num[4].c_str()), mv = std::atof(num[5].c_str());
            int w = 0, h = 0, comp = 0;
            unsigned char* px = stbi_load((dir + "/" + file).c_str(), &w, &h, &comp, 4);
            if (!px) continue;
            // Somme de la lumière de la photo (pixels en racine carrée de la lumière) : sert au recalage de l'éclat.
            double sum = 0;
            for (int k = 0; k < w * h; ++k) {
                const double r = px[k * 4] / 255.0, gg = px[k * 4 + 1] / 255.0, b = px[k * 4 + 2] / 255.0;
                sum += 0.2126 * r * r + 0.7152 * gg * gg + 0.0722 * b * b;
            }
            const Vec3 pos = sim.position(body);
            const double distPc = std::sqrt(dot(pos, pos)) / 3.2615638;
            buildMesh(it, ra, dec, fov, pa, incl, distPc * 3.2615638);
            // Aire (pc²) du disque vue par un pixel de la photo : angle solide du pixel × distance² / cos(inclinaison).
            const double pixRad = fov * kPi / 180.0 / w;
            const double area = pixRad * pixRad * distPc * distPc / std::max(std::cos(incl * kPi / 180.0), 0.05);
            it.gain = static_cast<float>(std::pow(10.0, -0.4 * mv) * 100.0 / std::max(sum * area, 1e-30));
            uploadTexture(g, it, px, w, h);
            stbi_image_free(px);
            items_.push_back(it);
        }
        if (items_.empty()) return;
        createPipeline(g, hdrFormat);
        count = static_cast<int>(items_.size());
        ready = true;
    }

    // share : part montrée (0 à 1), comme la lueur de la Voie lactée. exposure : celle des étoiles.
    void draw(VkCommandBuffer cmd, const Camera& cam, const Sim& sim, uint32_t width, uint32_t height, float exposure, double share) const {
        if (!ready || share <= 0) return;
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        const VkRect2D sc{{0, 0}, {width, height}};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        const PushConstants base = pushConstants(cam, exposure, height);
        const double pix = 2.0 * cam.tanHalf / height;
        for (const Item& it : items_) {
            if (!sim.visible(it.body)) continue;
            Push p{};
            std::memcpy(p.viewProj, base.viewProj, sizeof(p.viewProj));
            const Vec3 c = sim.position(it.body) - cam.pos;
            p.centre[0] = static_cast<float>(c.x);
            p.centre[1] = static_cast<float>(c.y);
            p.centre[2] = static_cast<float>(c.z);
            p.normal[0] = it.normal[0];
            p.normal[1] = it.normal[1];
            p.normal[2] = it.normal[2];
            p.par[0] = static_cast<float>(exposure * it.gain * pix * pix * share);
            const VkDeviceSize off = 0;
            vkCmdBindVertexBuffers(cmd, 0, 1, &it.mesh.buf, &off);
            vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &it.set, 0, nullptr);
            vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(p), &p);
            vkCmdDraw(cmd, it.vertices, 1, 0, 0);
        }
    }

    // Vrai si l'astre est montré par sa photo (les points du calcul de la fusion ne le montrent alors pas en double).
    bool shows(int body) const {
        for (const Item& it : items_)
            if (it.body == body) return true;
        return false;
    }

    void release(const Gpu& g) {
        if (!ready) return;
        for (Item& it : items_) {
            destroy(g, it.mesh);
            vkDestroyImageView(g.dev, it.view, nullptr);
            vkDestroyImage(g.dev, it.image, nullptr);
            vkFreeMemory(g.dev, it.mem, nullptr);
        }
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroySampler(g.dev, sampler_, nullptr);
        vkDestroyPipeline(g.dev, pipeline_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
        ready = false;
    }

private:
    static constexpr int kGrid = 48;      // maillage du disque : 48 × 48 cases (le passage ciel -> plan n'est pas linéaire)
    struct Item {
        int body = -1;
        float gain = 0;
        float normal[3] = {0, 0, 1};
        Buffer mesh;
        uint32_t vertices = 0;
        VkImage image{};
        VkDeviceMemory mem{};
        VkImageView view{};
        VkDescriptorSet set{};
    };
    struct Push {
        float viewProj[16];
        float centre[4];      // centre de la galaxie par rapport à la caméra (années-lumière)
        float normal[4];      // normale du disque (écliptique)
        float par[4];         // gain d'éclat (exposition × recalage × angle solide d'un pixel × part montrée)
    };

    // Directions du ciel en équatorial J2000 -> écliptique J2000 (repère de l'appli).
    static Vec3 eqToEcl(Vec3 v) {
        const double e = 84381.448 / 3600.0 * kPi / 180.0, ce = std::cos(e), se = std::sin(e);
        return {v.x, ce * v.y + se * v.z, -se * v.y + ce * v.z};
    }

    void buildMesh(Item& it, double raDeg, double decDeg, double fovDeg, double paDeg, double inclDeg, double distLy) {
        const double ra = raDeg * kPi / 180.0, dec = decDeg * kPi / 180.0, pa = paDeg * kPi / 180.0, inc = inclDeg * kPi / 180.0;
        const Vec3 u0{std::cos(dec) * std::cos(ra), std::cos(dec) * std::sin(ra), std::sin(dec)};      // vers la galaxie
        const Vec3 east = unit(Vec3{-std::sin(ra), std::cos(ra), 0});
        const Vec3 north = cross(u0, east);
        // Grand axe à l'angle PA (du nord vers l'est) ; le bord du petit axe du côté PA + 90° est le plus loin de nous.
        const Vec3 major{std::cos(pa) * north.x + std::sin(pa) * east.x, std::cos(pa) * north.y + std::sin(pa) * east.y, std::cos(pa) * north.z + std::sin(pa) * east.z};
        const Vec3 minor{-std::sin(pa) * north.x + std::cos(pa) * east.x, -std::sin(pa) * north.y + std::cos(pa) * east.y, -std::sin(pa) * north.z + std::cos(pa) * east.z};
        const Vec3 tilt{std::cos(inc) * minor.x + std::sin(inc) * u0.x, std::cos(inc) * minor.y + std::sin(inc) * u0.y, std::cos(inc) * minor.z + std::sin(inc) * u0.z};
        const Vec3 n = unit(cross(major, tilt));
        const Vec3 ne = eqToEcl(n);
        it.normal[0] = static_cast<float>(ne.x);
        it.normal[1] = static_cast<float>(ne.y);
        it.normal[2] = static_cast<float>(ne.z);
        const Vec3 centre{u0.x * distLy, u0.y * distLy, u0.z * distLy};
        const double half = std::tan(fovDeg * kPi / 360.0);
        auto vertex = [&](int i, int j, std::vector<float>& out) {
            const double s = static_cast<double>(i) / kGrid, t = static_cast<double>(j) / kGrid;      // s vers la droite (ouest), t vers le bas (sud)
            const double xi = (0.5 - s) * 2.0 * half, eta = (0.5 - t) * 2.0 * half;      // plan tangent : est, nord
            const Vec3 d = unit(Vec3{u0.x + xi * east.x + eta * north.x, u0.y + xi * east.y + eta * north.y, u0.z + xi * east.z + eta * north.z});
            const double dn = dot(d, n);
            const double k = std::fabs(dn) > 1e-3 ? dot(centre, n) / dn : distLy;
            const Vec3 p = eqToEcl(Vec3{d.x * k - centre.x, d.y * k - centre.y, d.z * k - centre.z});
            out.insert(out.end(), {static_cast<float>(p.x), static_cast<float>(p.y), static_cast<float>(p.z), static_cast<float>(s), static_cast<float>(t)});
        };
        std::vector<float> v;
        for (int j = 0; j < kGrid; ++j)
            for (int i = 0; i < kGrid; ++i) {
                vertex(i, j, v); vertex(i + 1, j, v); vertex(i + 1, j + 1, v);
                vertex(i, j, v); vertex(i + 1, j + 1, v); vertex(i, j + 1, v);
            }
        it.vertices = static_cast<uint32_t>(v.size() / 5);
        meshes_.push_back(std::move(v));
    }

    void uploadTexture(const Gpu& g, Item& it, const unsigned char* px, int w, int h) {
        VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
        ii.imageType = VK_IMAGE_TYPE_2D;
        ii.format = VK_FORMAT_R8G8B8A8_UNORM;      // racine carrée de la lumière : le shader met au carré
        ii.extent = {static_cast<uint32_t>(w), static_cast<uint32_t>(h), 1};
        ii.mipLevels = 1;
        ii.arrayLayers = 1;
        ii.samples = VK_SAMPLE_COUNT_1_BIT;
        ii.usage = VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
        check(vkCreateImage(g.dev, &ii, nullptr, &it.image), "photo de galaxie");
        VkMemoryRequirements mr;
        vkGetImageMemoryRequirements(g.dev, it.image, &mr);
        VkMemoryAllocateInfo mai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        mai.allocationSize = mr.size;
        mai.memoryTypeIndex = memoryType(g, mr.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        check(vkAllocateMemory(g.dev, &mai, nullptr, &it.mem), "mémoire de la photo");
        vkBindImageMemory(g.dev, it.image, it.mem, 0);
        const VkDeviceSize bytes = static_cast<VkDeviceSize>(w) * h * 4;
        Buffer staging = createBuffer(g, bytes, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, bytes, 0, &p), "accès à la photo");
        std::memcpy(p, px, bytes);
        vkUnmapMemory(g.dev, staging.mem);
        VkCommandBuffer cmd = beginOnce(g);
        transition(cmd, it.image, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 0, VK_ACCESS_TRANSFER_WRITE_BIT, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                   VK_PIPELINE_STAGE_TRANSFER_BIT);
        VkBufferImageCopy region{};
        region.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
        region.imageExtent = {static_cast<uint32_t>(w), static_cast<uint32_t>(h), 1};
        vkCmdCopyBufferToImage(cmd, staging.buf, it.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &region);
        transition(cmd, it.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_ACCESS_TRANSFER_WRITE_BIT, VK_ACCESS_SHADER_READ_BIT,
                   VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        endOnce(g, cmd);
        destroy(g, staging);
        VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
        vi.image = it.image;
        vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
        vi.format = ii.format;
        vi.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        check(vkCreateImageView(g.dev, &vi, nullptr, &it.view), "vue de la photo");
        it.mesh = uploadVertices(g, meshes_.back().data(), static_cast<VkDeviceSize>(meshes_.back().size()) * 4);
    }

    void createPipeline(const Gpu& g, VkFormat hdrFormat) {
        VkSamplerCreateInfo sci{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
        sci.magFilter = sci.minFilter = VK_FILTER_LINEAR;
        sci.addressModeU = sci.addressModeV = sci.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER;
        sci.borderColor = VK_BORDER_COLOR_FLOAT_TRANSPARENT_BLACK;
        check(vkCreateSampler(g.dev, &sci, nullptr, &sampler_), "échantillonneur des photos");
        const VkDescriptorSetLayoutBinding bind{0, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 1;
        dl.pBindings = &bind;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement des photos");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, static_cast<uint32_t>(items_.size())};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = static_cast<uint32_t>(items_.size());
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve des photos");
        for (Item& it : items_) {
            VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
            da.descriptorPool = pool_;
            da.descriptorSetCount = 1;
            da.pSetLayouts = &setLayout_;
            check(vkAllocateDescriptorSets(g.dev, &da, &it.set), "ressources de la photo");
            const VkDescriptorImageInfo info{sampler_, it.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL};
            VkWriteDescriptorSet wr{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
            wr.dstSet = it.set;
            wr.dstBinding = 0;
            wr.descriptorCount = 1;
            wr.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
            wr.pImageInfo = &info;
            vkUpdateDescriptorSets(g.dev, 1, &wr, 0, nullptr);
        }
        const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(Push)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement des photos");
        vs_ = shader(g, "galaxie_image.vert.spv");
        fs_ = shader(g, "galaxie_image.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
        const VkVertexInputBindingDescription vb{0, 20, VK_VERTEX_INPUT_RATE_VERTEX};
        const VkVertexInputAttributeDescription va[2] = {{0, 0, VK_FORMAT_R32G32B32_SFLOAT, 0}, {1, 0, VK_FORMAT_R32G32_SFLOAT, 12}};
        VkPipelineVertexInputStateCreateInfo vin{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        vin.vertexBindingDescriptionCount = 1;
        vin.pVertexBindingDescriptions = &vb;
        vin.vertexAttributeDescriptionCount = 2;
        vin.pVertexAttributeDescriptions = va;
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
        VkPipelineColorBlendAttachmentState att{};      // lumière ajoutée (une galaxie est transparente)
        att.blendEnable = VK_TRUE;
        att.srcColorBlendFactor = VK_BLEND_FACTOR_ONE;
        att.dstColorBlendFactor = VK_BLEND_FACTOR_ONE;
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
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline_), "pipeline des photos de galaxies");
    }

    std::vector<Item> items_;
    std::vector<std::vector<float>> meshes_;
    VkSampler sampler_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkPipelineLayout layout_{};
    VkPipeline pipeline_{};
    VkShaderModule vs_{}, fs_{};
};

}  // namespace
