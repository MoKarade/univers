// Appli PC « Univers » : grandes structures et nuage d'Oort (demande de Marc, 19/11/2026 : « il manque le nuage d'Oort,
// Laniakea avec le Grand Attracteur et tous les vides cosmiques »).
//
// Trois couches, dessinées par-dessus la lumière (addition, sans tampon de profondeur, comme le reste de l'appli) :
//  1. Laniakea et ses voisins : frontière du bassin d'attraction (Dupuy et Courtois 2023) et lignes de courant du champ de
//     vitesses Cosmicflows-4, qui finissent sur les attracteurs (structures.bin, pipeline/natif/structures.py).
//  2. Vides cosmiques, généralisés en s'éloignant : forme publiée des 100 vides du voisinage (Malandrino et al. 2026,
//     moins de 200 Mpc/h), union des sphères de VoidFinder (SDSS DR7, 200 à 330 Mpc/h), sphère de même volume (BOSS DR12,
//     z = 0,2 à 0,7).
//  3. Nuage d'Oort : MODÈLE (aucune comète du nuage n'a jamais été vue là-bas). Un million de comètes tirées au chargement,
//     chacune sur son orbite képlérienne autour du Soleil, avancée à la date montrée par la carte graphique (oort.vert).
//
// Ces couches ne sont pas de la lumière : un vide est noir, une frontière de bassin ne se voit pas, une comète du nuage
// d'Oort est bien trop faible. Elles sont dessinées en repères colorés ; l'interface le dit.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <random>
#include <string>
#include <vector>

#include "commun.h"

namespace structures {

// ---------------------------------------------------------------- modèle du nuage d'Oort (pas de mesure possible)
// Références (valeurs relevées le 19/11/2026) :
// - densité en r^-3,5 entre 3 000 et 100 000 UA : Duncan, Quinn et Tremaine 1987 (AJ 94, 1330), modèle de formation ;
//   bord extérieur vers 100 000 UA (Oort 1950 ; NASA). Avec des excentricités « thermiques » (f(e) = 2e), une densité en
//   r^-g s'obtient en tirant les demi-grands axes selon dN/da ∝ a^(2-g).
// - nuage extérieur isotrope (comètes à longue période venues de toutes les directions : mesuré, Oort 1950) ; nuage
//   intérieur (de Hills) aplati vers l'écliptique [supposé : allure des modèles de Duncan et al. 1987 et Kaib et Quinn
//   2008 ; dispersion de 20° à 3 000 UA, isotrope dès 20 000 UA].
// - nombre de comètes du nuage : de l'ordre de 10^11 à 10^12 (estimation publiée, NASA) : un point dessiné en vaut ~10^5.
// - ignorés : marée galactique, étoiles qui passent (l'orbite est une ellipse fixe autour du Soleil).
constexpr uint32_t kOortComets = 1000000;
constexpr double kAuInLyApprox = 1.495978707e11 / 9.4607304725808e15;      // UA -> années-lumière (définitions UAI)
constexpr double kOortAMin = 3000.0, kOortAMax = 100000.0;      // UA
constexpr double kOortDensitySlope = 3.5;
constexpr double kOortIsotropicAu = 20000.0, kOortInnerSigmaDeg = 20.0;

struct OortElements {      // par comète, pour oort.vert
    float a, e, inc, node;      // UA, -, rad, rad
    float peri, m0, n, pad;     // rad, anomalie moyenne à J2000 (rad), mouvement moyen (rad/an)
};

inline std::vector<OortElements> oortModel(uint32_t n, uint32_t seed = 19112026u) {
    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<double> U(0.0, 1.0);
    std::normal_distribution<double> N(0.0, 1.0);
    std::vector<OortElements> out(n);
    const double p = 3.0 - kOortDensitySlope;      // dN/da ∝ a^(2-g) : intégrale ∝ a^(3-g)
    const double lo = std::pow(kOortAMin, p), hi = std::pow(kOortAMax, p);
    const double twoPi = 6.283185307179586;
    for (uint32_t i = 0; i < n; ++i) {
        const double a = std::pow(lo + (hi - lo) * U(rng), 1.0 / p);
        const double e = std::min(std::sqrt(U(rng)), 0.98);      // thermique ; 0,98 au plus (pas de passage dans le Soleil)
        // aplatissement intérieur : part isotrope croissant de 0 (3 000 UA) à 1 (20 000 UA), en logarithme
        const double iso = std::clamp(std::log(a / kOortAMin) / std::log(kOortIsotropicAu / kOortAMin), 0.0, 1.0);
        double inc;
        if (U(rng) < iso) inc = std::acos(1.0 - 2.0 * U(rng));
        else {
            inc = std::fabs(N(rng)) * kOortInnerSigmaDeg * 3.141592653589793 / 180.0;
            if (U(rng) < 0.5) inc = 3.141592653589793 - inc;      // sens de rotation au hasard
        }
        out[i] = {static_cast<float>(a), static_cast<float>(e), static_cast<float>(inc), static_cast<float>(twoPi * U(rng)),
                  static_cast<float>(twoPi * U(rng)), static_cast<float>(twoPi * U(rng)),
                  static_cast<float>(twoPi / std::pow(a, 1.5)), 0.0f};      // période en années = a^1,5 (UA), masse du Soleil
    }
    return out;
}

// ---------------------------------------------------------------- fichier structures.bin

struct Mesh {
    uint32_t kind = 0;      // 1 Laniakea, 2 vides du voisinage, 3 vides SDSS, 4 vides BOSS
    std::vector<float> verts;      // x, y, z (al), nx, ny, nz
    std::vector<uint32_t> idx;
};

struct FlowLine {
    uint32_t basin = 0;      // 1 Laniakea … 6 Shapley (Dupuy et Courtois 2023)
    std::vector<float> pts;  // x, y, z (al), vitesse (km/s)
};

struct File {
    std::vector<Mesh> meshes;
    std::vector<FlowLine> lines;
};

inline bool readFile(const std::string& path, File& f) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return false;
    char magic[8];
    in.read(magic, 8);
    if (!in || std::memcmp(magic, "UNIVSTR1", 8) != 0) return false;
    uint32_t ns = 0;
    in.read(reinterpret_cast<char*>(&ns), 4);
    if (!in || ns > 16) return false;
    for (uint32_t s = 0; s < ns; ++s) {
        uint32_t h[3];
        in.read(reinterpret_cast<char*>(h), 12);
        if (!in || h[1] > 50000000u || h[2] > 150000000u) return false;
        Mesh m;
        m.kind = h[0];
        m.verts.resize(size_t(h[1]) * 6);
        m.idx.resize(h[2]);
        in.read(reinterpret_cast<char*>(m.verts.data()), static_cast<std::streamsize>(m.verts.size() * 4));
        in.read(reinterpret_cast<char*>(m.idx.data()), static_cast<std::streamsize>(m.idx.size() * 4));
        if (!in) return false;
        for (uint32_t v : m.idx)
            if (v >= h[1]) return false;
        f.meshes.push_back(std::move(m));
    }
    uint32_t nl = 0;
    in.read(reinterpret_cast<char*>(&nl), 4);
    if (!in || nl > 1000000u) return false;
    f.lines.resize(nl);
    std::vector<uint32_t> counts(nl);
    for (uint32_t i = 0; i < nl; ++i) {
        uint32_t h[2];
        in.read(reinterpret_cast<char*>(h), 8);
        if (!in || h[1] > 100000u) return false;
        f.lines[i].basin = h[0];
        counts[i] = h[1];
    }
    for (uint32_t i = 0; i < nl; ++i) {
        f.lines[i].pts.resize(size_t(counts[i]) * 4);
        in.read(reinterpret_cast<char*>(f.lines[i].pts.data()), static_cast<std::streamsize>(f.lines[i].pts.size() * 4));
        if (!in) return false;
    }
    return true;
}

// Ligne de courant -> segments (deux sommets chacun) : x, y, z, vitesse, chemin parcouru depuis le départ (Mpc), bassin.
inline std::vector<float> lineSegments(const std::vector<FlowLine>& lines) {
    constexpr double kMpcLy = 3.2615637771674333e6;
    std::vector<float> out;
    for (const FlowLine& l : lines) {
        const size_t n = l.pts.size() / 4;
        double s = 0;
        for (size_t k = 0; k + 1 < n; ++k) {
            const float* a = &l.pts[k * 4];
            const float* b = &l.pts[(k + 1) * 4];
            const double ds = std::sqrt(double(b[0] - a[0]) * (b[0] - a[0]) + double(b[1] - a[1]) * (b[1] - a[1]) + double(b[2] - a[2]) * (b[2] - a[2])) / kMpcLy;
            const float row[12] = {a[0], a[1], a[2], a[3], static_cast<float>(s), static_cast<float>(l.basin),
                                   b[0], b[1], b[2], b[3], static_cast<float>(s + ds), static_cast<float>(l.basin)};
            out.insert(out.end(), row, row + 12);
            s += ds;
        }
    }
    return out;
}

// Parts montrées selon l'échelle regardée (distance de la caméra à l'astre suivi, al) et la place de la caméra.
inline double ramp(double x, double a, double b) {
    const double t = std::clamp((x - a) / (b - a), 0.0, 1.0);
    return t * t * (3 - 2 * t);
}
// Nuage d'Oort : quand la caméra est entre ~1 000 UA et ~30 al du Soleil.
inline double oortShare(double camFromSunLy) {
    const double l = std::log10(std::max(camFromSunLy, 1e-9));
    return ramp(l, std::log10(0.005), std::log10(0.05)) * (1.0 - ramp(l, std::log10(15.0), std::log10(60.0)));
}
// Grandes structures : dès que l'on regarde à l'échelle de dizaines de millions d'années-lumière.
inline double largeShare(double viewDistLy) {
    const double l = std::log10(std::max(viewDistLy, 1.0));
    return ramp(l, 6.5, 7.4);
}

}  // namespace structures

namespace {

class StructureRenderer {
public:
    bool ready = false, oortReady = false;
    uint32_t meshTriangles[9] = {}, flowLines = 0, oortCount = 0;      // par genre (1 à 8) : comptés au chargement
    uint32_t flowLinesPerBasin[7] = {};

    // Shaders : structures_maille.vert/frag (surfaces), structures_flot.vert/frag (lignes), oort.vert/frag (points).
    bool create(const Gpu& g, const std::string& dataDir, VkFormat fmt) {
        createPipelines(g, fmt);
        // nuage d'Oort : modèle, toujours là
        const auto el = structures::oortModel(structures::kOortComets);
        oortBuf_ = upload(g, el.data(), el.size() * sizeof(structures::OortElements), VK_BUFFER_USAGE_VERTEX_BUFFER_BIT);
        oortCount = static_cast<uint32_t>(el.size());
        oortReady = true;
        structures::File f;
        if (!structures::readFile(dataDir + "/structures.bin", f)) return false;
        // Superstructures et univers observable (pipeline/natif/superstructures_bin.py), même format, facultatif.
        structures::File sup;
        if (structures::readFile(dataDir + "/superstructures.bin", sup))
            for (auto& m : sup.meshes) f.meshes.push_back(std::move(m));
        for (const auto& m : f.meshes) {
            if (m.kind < 1 || m.kind > 8 || m.idx.empty()) continue;
            Part p;
            p.kind = m.kind;
            p.vb = upload(g, m.verts.data(), m.verts.size() * 4, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT);
            p.ib = upload(g, m.idx.data(), m.idx.size() * 4, VK_BUFFER_USAGE_INDEX_BUFFER_BIT);
            p.count = static_cast<uint32_t>(m.idx.size());
            meshTriangles[m.kind] = p.count / 3;
            parts_.push_back(p);
        }
        for (const auto& l : f.lines)
            if (l.basin < 7) ++flowLinesPerBasin[l.basin];
        flowLines = static_cast<uint32_t>(f.lines.size());
        const auto seg = structures::lineSegments(f.lines);
        if (!seg.empty()) {
            lineBuf_ = upload(g, seg.data(), seg.size() * 4, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT);
            lineVerts_ = static_cast<uint32_t>(seg.size() / 6);
        }
        ready = true;
        return true;
    }

    // oort, large : parts montrées (0 à 1) ; years : date (années depuis J2000) ; clock : temps réel (s) pour le sens du flot ;
    // viewDistLy : distance de la caméra à l'astre suivi (les structures bien plus loin que cette échelle s'estompent).
    void draw(VkCommandBuffer cmd, const Camera& cam, uint32_t width, uint32_t height, double oort, double large, double years, double clock,
              double viewDistLy) {
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
        pc.cam[3] = static_cast<float>(std::max(viewDistLy, 1.0));      // échelle regardée : au-delà, détail estompé
        if (oortReady && oort > 0.002) {
            // dates : l'anomalie moyenne avance de n × années ; gardée en double ici, envoyée réduite pour la simple précision
            pc.par[0] = static_cast<float>(oort);
            pc.par[1] = static_cast<float>(height);
            pc.par[2] = static_cast<float>(std::fmod(years, 1.0e9));      // > 1 Ga : période la plus longue ~31,6 Ma, avance réduite
            pc.par[3] = static_cast<float>(structures::kAuInLyApprox);      // UA -> al
            vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, oortPipe_);
            vkCmdPushConstants(cmd, oortLayout_, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(pc), &pc);
            const VkDeviceSize off = 0;
            vkCmdBindVertexBuffers(cmd, 0, 1, &oortBuf_.buf, &off);
            vkCmdDraw(cmd, oortCount, 1, 0, 0);
        }
        if (!ready || large <= 0.002) return;
        pc.par[0] = static_cast<float>(large);
        pc.par[1] = static_cast<float>(height);
        pc.par[2] = static_cast<float>(std::fmod(clock, 1000.0));
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, meshPipe_);
        for (const Part& p : parts_) {
            pc.par[3] = static_cast<float>(p.kind);
            vkCmdPushConstants(cmd, meshLayout_, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(pc), &pc);
            const VkDeviceSize off = 0;
            vkCmdBindVertexBuffers(cmd, 0, 1, &p.vb.buf, &off);
            vkCmdBindIndexBuffer(cmd, p.ib.buf, 0, VK_INDEX_TYPE_UINT32);
            vkCmdDrawIndexed(cmd, p.count, 1, 0, 0, 0);
        }
        if (lineVerts_) {
            vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, linePipe_);
            vkCmdPushConstants(cmd, lineLayout_, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(pc), &pc);
            const VkDeviceSize off = 0;
            vkCmdBindVertexBuffers(cmd, 0, 1, &lineBuf_.buf, &off);
            vkCmdDraw(cmd, lineVerts_, 1, 0, 0);
        }
    }

    void release(const Gpu& g) {
        for (Part& p : parts_) {
            destroy(g, p.vb);
            destroy(g, p.ib);
        }
        parts_.clear();
        if (lineVerts_) destroy(g, lineBuf_);
        if (oortReady) destroy(g, oortBuf_);
        for (VkPipeline p : {meshPipe_, linePipe_, oortPipe_}) vkDestroyPipeline(g.dev, p, nullptr);
        for (VkPipelineLayout l : {meshLayout_, lineLayout_, oortLayout_}) vkDestroyPipelineLayout(g.dev, l, nullptr);
        for (VkShaderModule m : modules_) vkDestroyShaderModule(g.dev, m, nullptr);
        modules_.clear();
    }

private:
    struct Push { float viewProj[16]; float cam[4]; float par[4]; };
    struct Part { uint32_t kind = 0, count = 0; Buffer vb, ib; };
    std::vector<Part> parts_;
    Buffer lineBuf_, oortBuf_;
    uint32_t lineVerts_ = 0;
    VkPipeline meshPipe_{}, linePipe_{}, oortPipe_{};
    VkPipelineLayout meshLayout_{}, lineLayout_{}, oortLayout_{};
    std::vector<VkShaderModule> modules_;

    static Buffer upload(const Gpu& g, const void* data, VkDeviceSize size, VkBufferUsageFlags usage) {
        Buffer staging = createBuffer(g, size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, size, 0, &p), "structures : accès au tampon");
        std::memcpy(p, data, size);
        vkUnmapMemory(g.dev, staging.mem);
        Buffer dst = createBuffer(g, size, usage | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        VkCommandBuffer cmd = beginOnce(g);
        const VkBufferCopy region{0, 0, size};
        vkCmdCopyBuffer(cmd, staging.buf, dst.buf, 1, &region);
        endOnce(g, cmd);
        destroy(g, staging);
        return dst;
    }

    // Un pipeline additif (même mélange que les étoiles) ; attrs : formats des colonnes d'un seul tampon entrelacé.
    void pipeline(const Gpu& g, VkFormat fmt, const char* vsName, const char* fsName, VkPrimitiveTopology topo,
                  const std::vector<VkFormat>& attrs, uint32_t stride, VkPipeline& pipe, VkPipelineLayout& layout) {
        VkShaderModule vs = shader(g, vsName), fs = shader(g, fsName);
        modules_.push_back(vs);
        modules_.push_back(fs);
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs;
        stages[1].pName = "main";
        const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(Push)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout), "structures : agencement");
        const VkVertexInputBindingDescription bind{0, stride, VK_VERTEX_INPUT_RATE_VERTEX};
        std::vector<VkVertexInputAttributeDescription> ad;
        uint32_t off = 0;
        for (uint32_t i = 0; i < attrs.size(); ++i) {
            ad.push_back({i, 0, attrs[i], off});
            off += attrs[i] == VK_FORMAT_R32G32B32A32_SFLOAT ? 16 : attrs[i] == VK_FORMAT_R32G32B32_SFLOAT ? 12 : 8;
        }
        VkPipelineVertexInputStateCreateInfo vin{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        vin.vertexBindingDescriptionCount = 1;
        vin.pVertexBindingDescriptions = &bind;
        vin.vertexAttributeDescriptionCount = static_cast<uint32_t>(ad.size());
        vin.pVertexAttributeDescriptions = ad.data();
        VkPipelineInputAssemblyStateCreateInfo ia{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};
        ia.topology = topo;
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
        pci.layout = layout;
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipe), "structures : pipeline");
    }

    void createPipelines(const Gpu& g, VkFormat fmt) {
        pipeline(g, fmt, "structures_maille.vert.spv", "structures_maille.frag.spv", VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST,
                 {VK_FORMAT_R32G32B32_SFLOAT, VK_FORMAT_R32G32B32_SFLOAT}, 24, meshPipe_, meshLayout_);
        pipeline(g, fmt, "structures_flot.vert.spv", "structures_flot.frag.spv", VK_PRIMITIVE_TOPOLOGY_LINE_LIST,
                 {VK_FORMAT_R32G32B32A32_SFLOAT, VK_FORMAT_R32G32_SFLOAT}, 24, linePipe_, lineLayout_);
        pipeline(g, fmt, "oort.vert.spv", "oort.frag.spv", VK_PRIMITIVE_TOPOLOGY_POINT_LIST,
                 {VK_FORMAT_R32G32B32A32_SFLOAT, VK_FORMAT_R32G32B32A32_SFLOAT}, 32, oortPipe_, oortLayout_);
    }
};

}  // namespace
