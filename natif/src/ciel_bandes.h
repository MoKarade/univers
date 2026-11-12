// Appli PC « Univers » : le ciel dans toutes les longueurs d'onde (radio, micro-ondes, infrarouge, UV, X, gamma).
//
// Chaque bande est une carte MESURÉE du ciel entier, publiée par l'équipe d'un relevé (fiche dans le fichier) :
// fichiers ciel_<nom>.bin écrits par pipeline/natif/ciel_bandes.py depuis les tuiles HiPS en FITS (valeurs physiques,
// sans retouche). Rien n'est modélisé : un pixel que le relevé n'a pas mesuré reste vide et s'affiche hachuré.
//
// Ce qu'une carte du ciel est, et n'est pas : c'est le ciel vu depuis la Terre, sans profondeur. Elle n'est donc montrée
// que depuis le voisinage du Soleil ; elle s'efface entre 0,1 et 1 parsec (au-delà, le décalage de parallaxe des nuages
// proches dépasserait la résolution des relevés). L'écran le dit (legende()).
//
// Format de ciel_<nom>.bin : « UNIVSKY1 », puis 4 entiers 32 bits (Nside, 1 si repère galactique sinon équatorial ICRS,
// longueur de la fiche JSON, 0), la fiche JSON (UTF-8), des zéros jusqu'à un multiple de 16 octets, puis 12 × Nside²
// flottants 32 bits dans l'ordre HEALPix emboîté (NaN = pas de mesure).
#pragma once
#include "commun.h"
#include <filesystem>

namespace {

struct SkyBandUbo {      // std140 : tout en vec4
    float right[4], up[4], fwd[4];
    float scale[4];      // bas, haut, logarithmique (1) ou linéaire (0), opacité
    float grid[4];       // Nside, hauteur de l'image, rien, rien
};

// Fiche d'une bande, lue dans le JSON du fichier. Les textes sont ceux du script : source, mesure, unité, référence.
struct SkyBandInfo {
    std::string path, key, label, band, measure, unit, wavelength, reference, publishedCoverage, survey, scaleKind;
    double resolutionArcmin = 0, mapResolutionArcmin = 0, coverage = 0, lo = 0, hi = 0, median = 0;
    uint32_t nside = 0;
    bool galactic = false;
};

// Lecture d'un champ dans le JSON écrit par ciel_bandes.py (plat, sauf « stats » dont les clés sont uniques).
inline std::string jsonString(const std::string& js, const std::string& key) {
    const std::string k = "\"" + key + "\": \"";
    size_t p = js.find(k);
    if (p == std::string::npos) return {};
    p += k.size();
    std::string out;
    for (; p < js.size() && js[p] != '"'; ++p) {
        if (js[p] == '\\' && p + 1 < js.size()) ++p;
        out += js[p];
    }
    return out;
}
inline double jsonNumber(const std::string& js, const std::string& key, double fallback = 0) {
    const std::string k = "\"" + key + "\": ";
    const size_t p = js.find(k);
    if (p == std::string::npos) return fallback;
    return std::atof(js.c_str() + p + k.size());
}

inline bool readSkyBandHeader(const std::string& path, SkyBandInfo& info, std::streamoff& dataOffset) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return false;
    char magic[8];
    uint32_t h[4];
    f.read(magic, 8);
    f.read(reinterpret_cast<char*>(h), sizeof(h));
    if (!f || std::memcmp(magic, "UNIVSKY1", 8) != 0 || h[0] == 0 || (h[0] & (h[0] - 1)) != 0) return false;
    std::string js(h[2], '\0');
    f.read(js.data(), h[2]);
    if (!f) return false;
    info.path = path;
    info.nside = h[0];
    info.galactic = h[1] == 1;
    info.key = jsonString(js, "nom");
    info.label = jsonString(js, "libelle");
    info.band = jsonString(js, "bande");
    info.measure = jsonString(js, "mesure");
    info.unit = jsonString(js, "unite");
    info.wavelength = jsonString(js, "longueur_onde");
    info.reference = jsonString(js, "reference");
    info.publishedCoverage = jsonString(js, "couverture_publiee");
    info.survey = jsonString(js, "hips");
    info.scaleKind = jsonString(js, "echelle");
    info.resolutionArcmin = jsonNumber(js, "resolution_arcmin");
    info.mapResolutionArcmin = jsonNumber(js, "resolution_carte_arcmin");
    info.coverage = jsonNumber(js, "couverture_mesuree");
    info.lo = jsonNumber(js, "p01");
    info.hi = jsonNumber(js, "p999");
    info.median = jsonNumber(js, "p50");
    if (info.scaleKind.empty()) info.scaleKind = "log";
    if (info.scaleKind == "log" && info.lo <= 0) info.lo = info.median > 0 ? info.median * 1e-2 : 1e-30;
    dataOffset = static_cast<std::streamoff>((24 + h[2] + 15) / 16 * 16);
    return true;
}

// Toutes les bandes présentes dans le dossier des données, rangées de la radio vers le gamma.
inline std::vector<SkyBandInfo> listSkyBands(const std::string& dir) {
    static const char* order[] = {"radio", "micro-ondes", "infrarouge", "visible", "ultraviolet", "X", "gamma"};
    std::vector<SkyBandInfo> out;
    std::error_code ec;
    for (const auto& e : std::filesystem::directory_iterator(dir, ec)) {
        const std::string name = e.path().filename().string();
        if (name.rfind("ciel_", 0) != 0 || e.path().extension() != ".bin") continue;
        SkyBandInfo info;
        std::streamoff off;
        if (readSkyBandHeader(e.path().string(), info, off)) out.push_back(info);
    }
    auto rank = [&](const SkyBandInfo& b) {
        for (int i = 0; i < 7; ++i)
            if (b.band == order[i]) return i;
        return 7;
    };
    std::stable_sort(out.begin(), out.end(), [&](const SkyBandInfo& a, const SkyBandInfo& b) {
        return rank(a) != rank(b) ? rank(a) < rank(b) : a.key < b.key;
    });
    return out;
}

class SkyBandRenderer {
public:
    bool ready = false;      // pipeline prêt
    bool loaded = false;     // une carte est sur la carte graphique
    SkyBandInfo info;

    // Opacité selon la distance au Soleil (années-lumière) : 1 jusqu'à 0,1 pc, 0 à partir de 1 pc, en échelle log.
    static double opacityAt(double distLy) {
        constexpr double kPc = 3.26156;
        const double d = distLy / kPc;
        if (d <= 0.1) return 1.0;
        if (d >= 1.0) return 0.0;
        return 1.0 - std::log10(d / 0.1);
    }

    bool create(const Gpu& g, VkFormat hdrFormat) {
        for (auto& u : ubo_) u = createBuffer(g, sizeof(SkyBandUbo), VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        for (int i = 0; i < kRing; ++i) check(vkMapMemory(g.dev, ubo_[i].mem, 0, sizeof(SkyBandUbo), 0, &mapped_[i]), "ciel par bande");
        createPipeline(g, hdrFormat);
        ready = true;
        return true;
    }

    // Charge une bande (remplace la précédente). Attend que la carte graphique ait fini avec l'ancienne.
    bool load(const Gpu& g, const std::string& path) {
        SkyBandInfo in;
        std::streamoff off = 0;
        if (!readSkyBandHeader(path, in, off)) return false;
        const size_t n = 12ull * in.nside * in.nside;
        std::ifstream f(path, std::ios::binary);
        f.seekg(off);
        Buffer staging = createBuffer(g, n * 4, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, n * 4, 0, &p), "carte du ciel");
        f.read(static_cast<char*>(p), static_cast<std::streamsize>(n * 4));
        const bool ok = static_cast<bool>(f);
        vkUnmapMemory(g.dev, staging.mem);
        if (!ok) {
            destroy(g, staging);
            return false;
        }
        vkDeviceWaitIdle(g.dev);
        if (loaded) destroy(g, map_);
        map_ = createBuffer(g, n * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        VkCommandBuffer cmd = beginOnce(g);
        const VkBufferCopy region{0, 0, n * 4};
        vkCmdCopyBuffer(cmd, staging.buf, map_.buf, 1, &region);
        endOnce(g, cmd);
        destroy(g, staging);
        for (int i = 0; i < kRing; ++i) {
            const VkDescriptorBufferInfo bi[2] = {{ubo_[i].buf, 0, sizeof(SkyBandUbo)}, {map_.buf, 0, n * 4}};
            VkWriteDescriptorSet w[2];
            for (uint32_t b = 0; b < 2; ++b) {
                w[b] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
                w[b].dstSet = sets_[i];
                w[b].dstBinding = b;
                w[b].descriptorCount = 1;
                w[b].descriptorType = b == 0 ? VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER : VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
                w[b].pBufferInfo = &bi[b];
            }
            vkUpdateDescriptorSets(g.dev, 2, w, 0, nullptr);
        }
        info = in;
        loaded = true;
        return true;
    }

    // Texte à afficher avec la bande : d'où vient la carte, ce qu'elle mesure, sa finesse, sa couverture, l'échelle.
    std::vector<std::string> legend(double distLy) const {
        std::vector<std::string> l;
        if (!loaded) return l;
        char b[512];
        l.push_back(info.label + (info.wavelength.empty() ? "" : " (" + info.wavelength + ")"));
        l.push_back(info.measure + ", en " + info.unit + ".");
        l.push_back("Relevé : " + info.reference + ".");
        std::snprintf(b, sizeof b, "Finesse : %.3g minute(s) d'arc (relevé) ; carte chargée : %.2g. Couverture mesurée : %.1f %% du ciel.",
                      info.resolutionArcmin, info.mapResolutionArcmin, info.coverage * 100.0);
        l.push_back(b);
        std::snprintf(b, sizeof b, "Fausses couleurs, échelle %s de %.3g à %.3g %s. Hachures : pas de mesure.",
                      info.scaleKind == "log" ? "logarithmique" : "linéaire", info.lo, info.hi, info.unit.c_str());
        l.push_back(b);
        const double a = opacityAt(distLy);
        if (a >= 1.0) l.push_back("Vu depuis la Terre : une carte du ciel n'a pas de profondeur.");
        else if (a > 0.0) l.push_back("On s'éloigne du Soleil : la carte, vue depuis la Terre, s'efface (plus du tout au-delà de 1 parsec).");
        else l.push_back("Trop loin du Soleil pour cette carte (vue depuis la Terre, sans profondeur) : rien n'est montré.");
        return l;
    }

    // Dans la passe en grande dynamique, en premier (fond du ciel). Rien n'est dessiné loin du Soleil.
    void draw(VkCommandBuffer cmd, const Camera& cam, uint32_t width, uint32_t height) {
        if (!ready || !loaded) return;
        const double distLy = std::sqrt(cam.pos.x * cam.pos.x + cam.pos.y * cam.pos.y + cam.pos.z * cam.pos.z);
        const double alpha = opacityAt(distLy);
        if (alpha <= 0.0) return;
        // Écliptique J2000 (repère de l'appli) vers équatorial : rotation d'axe x de l'obliquité (IAU 2006 : 84 381,406″).
        const double eps = 84381.406 / 3600.0 * kPi / 180.0, ce = std::cos(eps), se = std::sin(eps);
        // Équatorial ICRS vers galactique : matrice de Hipparcos (ESA 1997, vol. 1, § 1.5.3).
        static const double G[3][3] = {{-0.0548755604162154, -0.8734370902348850, -0.4838350155487132},
                                       {+0.4941094278755837, -0.4448296299600112, +0.7469822444972189},
                                       {-0.8676661490190047, -0.1980763734312015, +0.4559837761750669}};
        auto toSurvey = [&](Vec3 v) {
            const Vec3 e{v.x, ce * v.y - se * v.z, se * v.y + ce * v.z};
            if (!info.galactic) return e;
            return Vec3{G[0][0] * e.x + G[0][1] * e.y + G[0][2] * e.z, G[1][0] * e.x + G[1][1] * e.y + G[1][2] * e.z,
                        G[2][0] * e.x + G[2][1] * e.y + G[2][2] * e.z};
        };
        SkyBandUbo u{};
        const Vec3 r = toSurvey(cam.right), up = toSurvey(cam.up), fw = toSurvey(cam.fwd);
        const double tx = cam.tanHalf * cam.aspect, ty = cam.tanHalf;
        const float rr[4] = {static_cast<float>(r.x * tx), static_cast<float>(r.y * tx), static_cast<float>(r.z * tx), 0};
        const float uu[4] = {static_cast<float>(up.x * ty), static_cast<float>(up.y * ty), static_cast<float>(up.z * ty), 0};
        const float ff[4] = {static_cast<float>(fw.x), static_cast<float>(fw.y), static_cast<float>(fw.z), 0};
        std::memcpy(u.right, rr, 16);
        std::memcpy(u.up, uu, 16);
        std::memcpy(u.fwd, ff, 16);
        u.scale[0] = static_cast<float>(info.lo);
        u.scale[1] = static_cast<float>(info.hi);
        u.scale[2] = info.scaleKind == "log" ? 1.0f : 0.0f;
        u.scale[3] = static_cast<float>(alpha);
        u.grid[0] = static_cast<float>(info.nside);
        u.grid[1] = static_cast<float>(height);
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
        vkDeviceWaitIdle(g.dev);
        if (loaded) destroy(g, map_);
        vkDestroyPipeline(g.dev, pipeline_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
        for (int i = 0; i < kRing; ++i) {
            vkUnmapMemory(g.dev, ubo_[i].mem);
            destroy(g, ubo_[i]);
        }
        ready = loaded = false;
    }

private:
    static constexpr int kRing = 4;
    Buffer map_{};
    Buffer ubo_[kRing];
    void* mapped_[kRing]{};
    VkDescriptorSet sets_[kRing]{};
    int ring_ = 0;
    VkPipeline pipeline_{};
    VkPipelineLayout layout_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkShaderModule vs_{}, fs_{};

    void createPipeline(const Gpu& g, VkFormat fmt) {
        const VkDescriptorSetLayoutBinding binds[2] = {{0, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr},
                                                       {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr}};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 2;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement du ciel par bande");
        const VkDescriptorPoolSize ps[2] = {{VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, kRing}, {VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, kRing}};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = kRing;
        dp.poolSizeCount = 2;
        dp.pPoolSizes = ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve du ciel par bande");
        VkDescriptorSetLayout layouts[kRing];
        for (auto& l : layouts) l = setLayout_;
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = kRing;
        da.pSetLayouts = layouts;
        check(vkAllocateDescriptorSets(g.dev, &da, sets_), "jeux du ciel par bande");
        vs_ = shader(g, "ecran.vert.spv");      // un triangle qui couvre l'écran
        fs_ = shader(g, "ciel_bandes.frag.spv");
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
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement du ciel par bande");
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
        VkPipelineColorBlendAttachmentState att{};      // ajouté à ce qui est déjà là (fond noir : la carte seule)
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
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline_), "pipeline du ciel par bande");
    }
};

}  // namespace
