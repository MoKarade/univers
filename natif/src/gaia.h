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
#include "orbite_galactique.h"
#include "gaia_orbites.h"

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
    // Résumé de chaque feuille (absent des fichiers anciens : bins = 0) : centre de lumière, puis par tranche de magnitude
    // absolue la lumière 10^(-0,4 M) et le pas de couleur moyen.
    uint32_t bins = 0;
    float bin0 = 0, binWidth = 1;
    const float* summaries = nullptr;      // (4 + 2 × bins) flottants par feuille
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
    std::memcpy(&out.bins, out.base + 1056, 4);
    std::memcpy(&out.bin0, out.base + 1060, 4);
    std::memcpy(&out.binWidth, out.base + 1064, 4);
    const size_t velBytes = gaiaAlign(out.n * 8);
    out.summaries = reinterpret_cast<const float*>(out.velocities + velBytes);
    const uint64_t need = 4096 + leafBytes + starBytes + velBytes + static_cast<uint64_t>(out.leafCount) * (4 + 2 * out.bins) * 4;
    if (out.bins == 0 || out.bins > 256) out.bins = 0;
    return static_cast<uint64_t>(size.QuadPart) >= (out.bins ? need : 4096 + leafBytes + starBytes + out.n * 8);
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

// Constantes des étoiles Gaia : celles de toutes les étoiles, plus l'orbite exacte (gaia_orbites.h). 128 octets.
struct GaiaPush {
    PushConstants base;
    uint32_t sun;        // rang du Soleil dans les états d'orbite
    float frac;          // part du pas d'un million d'années écoulée depuis l'état
    float exact;         // 1 : orbite exacte (états calculés à jour) ; 0 : épicycles
    uint32_t cellBase;   // rang du premier état des cases de lumière additionnée
};
static_assert(sizeof(GaiaPush) == 128, "constantes Gaia : 128 octets");

class GaiaRenderer {
public:
    bool ready = false;
    uint64_t count = 0;      // étoiles dans le fichier
    uint64_t drawn = 0;      // étoiles dessinées à la dernière image
    // Flux le plus faible dessiné, dans l'unité de l'image en grande dynamique (l'écran commence à montrer vers 4e-4).
    // Les étoiles plus faibles sont sautées une à une ; leur lumière cumulée est rendue par un point par feuille, au centre
    // de lumière de la feuille, étalé sur la taille de la feuille à l'écran (résumé des feuilles de gaia.bin).
    float fluxMin = 3e-5f;
    uint32_t restPoints = 0;      // points de lumière cumulée à la dernière image
    // Lumière additionnée des autres sources Gaia (gaia_agrege.bin, facultatif, à côté de gaia.bin) : cases placées à
    // leur distance, et lumière sans distance (« ciel seul ») montrée seulement près du Soleil.
    uint32_t cellCount = 0, skyCount = 0;
    float cellDispersionKms = 0;      // dispersion médiane des vitesses sur le ciel dans une case (à dire à l'écran)
    static constexpr double kSkyOnlyRadiusLy = 100.0;
    static constexpr uint32_t kCellSpread = 8;
    static constexpr double kAggregateYears = 3.0e6;      // lumière additionnée montrée à moins de 3 millions d'années des mesures      // même valeur que SPREAD dans gaia_agrege.vert

    bool create(const Gpu& g, const std::string& path, VkFormat hdrFormat) {
        if (!openGaia(path, file_)) return false;
        VkPhysicalDeviceProperties props;
        vkGetPhysicalDeviceProperties(g.pd, &props);
        if (file_.n * 16 > props.limits.maxStorageBufferRange) return false;
        count = file_.n;
        stars_ = uploadStorage(g, file_.stars, file_.n * 16);
        velocities_ = uploadStorage(g, file_.velocities, file_.n * 8);
        // Centre et vitesse moyenne de chaque feuille : la feuille suit l'orbite de son centre quand le temps avance.
        centre_.resize(file_.leafCount);
        meanVel_.resize(file_.leafCount);
        shift_.assign(file_.leafCount, Vec3{0, 0, 0});
        for (uint32_t i = 0; i < file_.leafCount; ++i) {
            const GaiaLeaf& L = file_.leaves[i];
            centre_[i] = {0.5 * (L.mn[0] + L.mx[0]), 0.5 * (L.mn[1] + L.mx[1]), 0.5 * (L.mn[2] + L.mx[2])};
            double v[3] = {0, 0, 0};
            const auto* q = reinterpret_cast<const int16_t*>(file_.velocities) + L.first * 4;
            for (uint32_t j = 0; j < L.n; ++j)
                for (int a = 0; a < 3; ++a) v[a] += q[j * 4 + a];
            meanVel_[i] = {v[0] * 0.05 / std::max(1u, L.n), v[1] * 0.05 / std::max(1u, L.n), v[2] * 0.05 / std::max(1u, L.n)};
        }
        // Couleur de chaque pas BP-RP : corps noir de la température du fichier, vu par l'observateur CIE (commun.h).
        std::array<float, 256 * 4> colors{};
        for (int i = 0; i < 256; ++i) {
            const float T = file_.temperature[i];
            const auto c = std::isfinite(T) ? colorOfTemperature(T) : std::array<uint8_t, 4>{255, 255, 255, 255};      // couleur non mesurée : blanc
            for (int k = 0; k < 3; ++k) colors[i * 4 + k] = c[k] / 255.0f;
            colors[i * 4 + 3] = 1.0f;
        }
        colors_ = uploadStorage(g, colors.data(), sizeof(colors));
        for (int i = 0; i < 256; ++i)
            for (int k = 0; k < 3; ++k) lut_[i][k] = colors[i * 4 + k];
        if (file_.bins) {
            for (int i = 0; i < kRing; ++i) {
                rest_[i] = createBuffer(g, std::max<VkDeviceSize>(32, file_.leafCount * 32ull), VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                                        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
                check(vkMapMemory(g.dev, rest_[i].mem, 0, VK_WHOLE_SIZE, 0, &restMapped_[i]), "lumière cumulée");
            }
        }
        for (auto& r : indirect_) {
            r = createBuffer(g, std::max<VkDeviceSize>(16, file_.leafCount * 16ull), VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT,
                             VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        }
        for (int i = 0; i < kRing; ++i) check(vkMapMemory(g.dev, indirect_[i].mem, 0, VK_WHOLE_SIZE, 0, &mapped_[i]), "dessins indirects");
        loadAggregate(g, path.substr(0, path.find_last_of("\\/") + 1) + "gaia_agrege.bin");
        std::vector<std::pair<uint32_t, uint32_t>> leafRanges(file_.leafCount);
        for (uint32_t i = 0; i < file_.leafCount; ++i) leafRanges[i] = {static_cast<uint32_t>(file_.leaves[i].first), file_.leaves[i].n};
        orbits_.create(g, file_.stars, file_.velocities, file_.n, std::move(leafRanges), cellPos_, cellVel_);      // étoiles, puis cases, puis le Soleil      // orbites exactes : états de départ calculés dans un fil à part
        createPipeline(g, hdrFormat);
        ready = true;
        return true;
    }

    // Dans la passe en grande dynamique (additive, sans profondeur). years : années depuis J2000,0.
    void draw(VkCommandBuffer cmd, const Camera& cam, uint32_t width, uint32_t height, float exposure, double years) {
        if (!ready) return;
        const double since = years - (static_cast<double>(file_.epoch) - 2000.0);      // années depuis les mesures de Gaia
        PushConstants pc = pushConstants(cam, exposure, height, since);
        pc.par[3] = static_cast<float>(since / 1.0e9);      // orbite autour de la Galaxie (gaia.vert)
        const GaiaPush gp{pc, orbits_.count - 1, orbits_.fraction(since), orbits_.readyToDraw() ? 1.0f : 0.0f, static_cast<uint32_t>(file_.n)};
        const uint32_t n = selectLeaves(cam, exposure, since, height, static_cast<VkDrawIndirectCommand*>(mapped_[ring_]),
                                        file_.bins ? static_cast<float*>(restMapped_[ring_]) : nullptr);
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        const VkRect2D sc{{0, 0}, {width, height}};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        if (restPoints > 0) {
            vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, restPipeline_);
            vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(pc), &pc);
            const VkDeviceSize off = 0;
            vkCmdBindVertexBuffers(cmd, 0, 1, &rest_[ring_].buf, &off);
            vkCmdDraw(cmd, restPoints, 1, 0, 0);
        }
        // Lumière additionnée : les cases en volume suivent le même mouvement que les étoiles (vitesse moyenne mesurée de
        // leurs sources) ; le ciel seul (sans distance ni vitesse) n'existe qu'au présent mesuré (kAggregateYears).
        if (cellCount + skyCount > 0) {
            GaiaPush pa = gp;
            pa.base.camHi[3] = static_cast<float>(cam.tanHalf);
            vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, aggPipeline_);
            vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &aggSet_, 0, nullptr);
            vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(pa), &pa);
            if (cellCount) vkCmdDraw(cmd, cellCount, kCellSpread, 0, 0);      // kCellSpread points par case (gaia_agrege.vert)
            if (skyCount && std::fabs(since) < kAggregateYears && std::sqrt(dot(cam.pos, cam.pos)) < kSkyOnlyRadiusLy) {
                pa.base.camLo[3] = 1.0f;
                vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(pa), &pa);
                vkCmdDraw(cmd, skyCount, 1, cellCount, 0);
            }
        }
        if (n + epicycleLeaves_ > 0) {
            vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
            vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &set_, 0, nullptr);
            if (n > 0) {
                vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(gp), &gp);
                vkCmdDrawIndirect(cmd, indirect_[ring_].buf, 0, n, sizeof(VkDrawIndirectCommand));
            }
            if (epicycleLeaves_ > 0) {
                GaiaPush ge = gp;
                ge.exact = 0.0f;
                vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(ge), &ge);
                vkCmdDrawIndirect(cmd, indirect_[ring_].buf, static_cast<VkDeviceSize>(file_.leafCount - epicycleLeaves_) * sizeof(VkDrawIndirectCommand),
                                  epicycleLeaves_, sizeof(VkDrawIndirectCommand));
            }
        }
        ring_ = (ring_ + 1) % kRing;
    }

    // Avance les orbites exactes vers la date montrée (budget : pas d'un million d'années au plus). Hors d'une passe de dessin,
    // avant draw. years : années depuis J2000,0. Sans cet appel, les étoiles suivent les épicycles (comme avant).
    void advance(const Gpu& g, VkCommandBuffer cmd, double years, long budget) {
        if (ready) orbits_.advance(g, cmd, years - (static_cast<double>(file_.epoch) - 2000.0), budget, visible_);
    }
    long orbitLagSteps() const { return orbits_.lagSteps; }
    // Contrôle : la prochaine avance porte sur toutes les feuilles, pas seulement les visibles.
    void wantAllLeaves() { visible_.resize(file_.leafCount); for (uint32_t i = 0; i < file_.leafCount; ++i) visible_[i] = i; }
    const GaiaOrbits& orbits() const { return orbits_; }

    void release(const Gpu& g) {
        if (!ready) return;
        orbits_.release(g);
        vkDestroyPipeline(g.dev, pipeline_, nullptr);
        if (restPipeline_) vkDestroyPipeline(g.dev, restPipeline_, nullptr);
        if (aggPipeline_) vkDestroyPipeline(g.dev, aggPipeline_, nullptr);
        if (aggVs_) vkDestroyShaderModule(g.dev, aggVs_, nullptr);
        if (cellCount + skyCount) destroy(g, cells_);
        if (restVs_) vkDestroyShaderModule(g.dev, restVs_, nullptr);
        for (int i = 0; i < kRing && file_.bins; ++i) {
            vkUnmapMemory(g.dev, rest_[i].mem);
            destroy(g, rest_[i]);
        }
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
    static constexpr double kDispersionKms = 100.0;     // écart des vitesses dans une feuille, une fois sur orbite (marge large)
    static constexpr double kMaxGrowLy = 1.5e5;         // au-delà, la feuille couvre la Galaxie entière
    std::vector<Vec3> centre_, meanVel_, shift_;
    double shiftYears_ = 0;
    GaiaFile file_;
    GaiaOrbits orbits_;
    std::vector<uint32_t> visible_;      // feuilles dessinées à la dernière image : ce sont elles que les orbites exactes avancent
    uint32_t epicycleLeaves_ = 0;        // feuilles dessinées en épicycles à la dernière image (orbite exacte pas encore rattrapée)
    Buffer stars_, velocities_, colors_, indirect_[kRing];
    void* mapped_[kRing]{};
    Buffer rest_[kRing];
    void* restMapped_[kRing]{};
    float lut_[256][3]{};
    int ring_ = 0;
    VkPipeline pipeline_{}, restPipeline_{}, aggPipeline_{};
    VkShaderModule restVs_{}, aggVs_{};
    Buffer cells_;
    std::vector<Vec3> cellPos_, cellVel_;      // centre (al) et vitesse moyenne (km/s) des cases, pour leurs orbites
    VkDescriptorSet aggSet_{};

    void loadAggregate(const Gpu& g, const std::string& path) {
        std::ifstream f(path, std::ios::binary | std::ios::ate);
        if (!f) return;
        const auto size = static_cast<size_t>(f.tellg());
        char head[64];
        f.seekg(0);
        f.read(head, 64);
        if (!f || std::memcmp(head, "UNIVGAG2", 8) != 0) return;      // cases de 48 octets, avec leur vitesse moyenne
        uint64_t nc = 0;
        uint32_t ns = 0;
        std::memcpy(&nc, head + 8, 8);
        std::memcpy(&ns, head + 16, 4);
        std::memcpy(&cellDispersionKms, head + 40, 4);
        if (size < 64 + (nc + ns) * 48) return;
        std::vector<char> data((nc + ns) * 48);
        f.read(data.data(), static_cast<std::streamsize>(data.size()));
        if (!f) return;
        cellPos_.resize(nc);
        cellVel_.resize(nc);
        for (uint64_t i = 0; i < nc; ++i) {
            float c[12];
            std::memcpy(c, data.data() + i * 48, 48);
            cellPos_[i] = {c[0], c[1], c[2]};
            cellVel_[i] = {c[8], c[9], c[10]};
        }
        cells_ = uploadStorage(g, data.data(), data.size());
        cellCount = static_cast<uint32_t>(nc);
        skyCount = ns;
    }
    VkPipelineLayout layout_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet set_{};
    VkShaderModule vs_{}, fs_{};

    // Feuilles visibles et, pour chacune, le nombre d'étoiles à dessiner (les plus brillantes d'abord).
    // rest : 8 flottants par feuille (position relative à la caméra, magnitude absolue de la lumière sautée ; couleur, taille en pixels).
    uint32_t selectLeaves(const Camera& cam, float exposure, double since, uint32_t height, VkDrawIndirectCommand* out, float* rest) {
        const double pxPerRad = height / (2.0 * cam.tanHalf);
        const double mLim = 2.5 * std::log10(static_cast<double>(exposure) / fluxMin);      // magnitude apparente la plus faible dessinée
        // Feuilles déplacées avec le temps : chacune suit l'orbite de son centre (vitesse moyenne de ses étoiles) ; sa boîte
        // grandit de l'écart des vitesses (ligne droite : borne des vitesses ; orbite : dispersion du disque).
        const double w = orbite::poidsOrbite(since);
        const double grow = std::min(((1.0 - w) * kMaxSpeedKms + w * kDispersionKms) * std::fabs(since) * kKmsToLyPerYear, kMaxGrowLy);
        if (w > 1e-9 && since != shiftYears_) {
            for (uint32_t i = 0; i < file_.leafCount; ++i) shift_[i] = orbite::deplacement(centre_[i], meanVel_[i], since);
            shiftYears_ = since;
        }
        const bool moved = w > 1e-9;
        const double tx = cam.tanHalf * cam.aspect * 1.02, ty = cam.tanHalf * 1.02;      // 2 % de marge : les points ont une taille
        const Vec3 planes[4] = {{cam.fwd.x * tx - cam.right.x, cam.fwd.y * tx - cam.right.y, cam.fwd.z * tx - cam.right.z},
                                {cam.fwd.x * tx + cam.right.x, cam.fwd.y * tx + cam.right.y, cam.fwd.z * tx + cam.right.z},
                                {cam.fwd.x * ty - cam.up.x, cam.fwd.y * ty - cam.up.y, cam.fwd.z * ty - cam.up.z},
                                {cam.fwd.x * ty + cam.up.x, cam.fwd.y * ty + cam.up.y, cam.fwd.z * ty + cam.up.z}};
        uint32_t k = 0, kb = 0;      // feuilles en orbite exacte (début de la liste) et en épicycles (fin de la liste)
        drawn = 0;
        restPoints = 0;
        visible_.clear();
        for (uint32_t i = 0; i < file_.leafCount; ++i) {
            const GaiaLeaf& L = file_.leaves[i];
            const Vec3 o = moved ? shift_[i] : Vec3{0, 0, 0};
            const double lo[3] = {L.mn[0] + o.x - grow - cam.pos.x, L.mn[1] + o.y - grow - cam.pos.y, L.mn[2] + o.z - grow - cam.pos.z};
            const double hi[3] = {L.mx[0] + o.x + grow - cam.pos.x, L.mx[1] + o.y + grow - cam.pos.y, L.mx[2] + o.z + grow - cam.pos.z};
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
                if (rest && take < L.n) addRest(i, L, cam, absLim, dPc, pxPerRad, rest, o);
            }
            if (take == 0) continue;
            visible_.push_back(i);
            const VkDrawIndirectCommand c{take, 1, static_cast<uint32_t>(L.first), 0};
            if (!moved || orbits_.rangeReady(i)) out[k++] = c;      // à jour (ou temps proche : ligne droite)
            else out[file_.leafCount - 1 - kb++] = c;               // pas encore rattrapée : épicycles en attendant
            drawn += take;
        }
        epicycleLeaves_ = kb;
        return k;
    }

    // Lumière des étoiles de la feuille i plus faibles que absLim : somme des tranches de magnitude (la tranche coupée
    // compte au prorata de la part de sa largeur sous la limite), en un point au centre de lumière de la feuille.
    void addRest(uint32_t i, const GaiaLeaf& L, const Camera& cam, double absLim, double dPc, double pxPerRad, float* rest, Vec3 o) {
        const float* s = file_.summaries + static_cast<size_t>(i) * (4 + 2 * file_.bins);
        const float* lum = s + 4;
        const float* col = lum + file_.bins;
        double sum = 0, colSum = 0, colW = 0;
        for (uint32_t b = 0; b < file_.bins; ++b) {
            const double lo = file_.bin0 + b * file_.binWidth;
            const double part = std::clamp((lo + file_.binWidth - absLim) / file_.binWidth, 0.0, 1.0);
            if (part <= 0 || lum[b] <= 0) continue;
            const double l = lum[b] * part;
            sum += l;
            if (col[b] < 254.5f) { colSum += l * col[b]; colW += l; }
        }
        if (sum <= 0) return;
        // taille de la feuille à l'écran : la lumière y est étalée (au moins la taille d’une étoile, au plus 512 pixels)
        const double ext = std::sqrt((L.mx[0] - L.mn[0]) * (L.mx[0] - L.mn[0]) + (L.mx[1] - L.mn[1]) * (L.mx[1] - L.mn[1]) + (L.mx[2] - L.mn[2]) * (L.mx[2] - L.mn[2]));
        const double sizePx = ext / (dPc * 3.2615638) * pxPerRad;
        if (sizePx > 512.0) return;      // feuille trop grande à l'écran : sa lumière sautée, étalée, n'est pas rendue (part mesurée : docs/gaia-voie-lactee.md)
        float* v = rest + restPoints * 8;
        v[0] = static_cast<float>(s[0] + o.x - cam.pos.x);
        v[1] = static_cast<float>(s[1] + o.y - cam.pos.y);
        v[2] = static_cast<float>(s[2] + o.z - cam.pos.z);
        v[3] = static_cast<float>(-2.5 * std::log10(sum));
        const int ci = colW > 0 ? static_cast<int>(std::lround(colSum / colW)) : 255;
        for (int a = 0; a < 3; ++a) v[4 + a] = lut_[std::clamp(ci, 0, 255)][a];
        v[7] = static_cast<float>(std::max(sizePx, 1.0));
        ++restPoints;
    }

    void createPipeline(const Gpu& g, VkFormat fmt) {
        VkDescriptorSetLayoutBinding binds[4];      // 3 : états des orbites exactes
        for (uint32_t i = 0; i < 4; ++i) binds[i] = {i, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_VERTEX_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 4;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement Gaia");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 8};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 2;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve Gaia");
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = 1;
        da.pSetLayouts = &setLayout_;
        check(vkAllocateDescriptorSets(g.dev, &da, &set_), "jeu Gaia");
        const VkDescriptorBufferInfo infos[4] = {{stars_.buf, 0, VK_WHOLE_SIZE}, {velocities_.buf, 0, VK_WHOLE_SIZE}, {colors_.buf, 0, VK_WHOLE_SIZE},
                                                 {orbits_.state.buf, 0, VK_WHOLE_SIZE}};
        VkWriteDescriptorSet w[4];
        for (uint32_t i = 0; i < 4; ++i) {
            w[i] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
            w[i].dstSet = set_;
            w[i].dstBinding = i;
            w[i].descriptorCount = 1;
            w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            w[i].pBufferInfo = &infos[i];
        }
        vkUpdateDescriptorSets(g.dev, 4, w, 0, nullptr);
        if (cellCount + skyCount) {      // même agencement : 0 = cases, 1 = vitesses (inutiles), 2 = couleurs
            check(vkAllocateDescriptorSets(g.dev, &da, &aggSet_), "jeu Gaia (lumière additionnée)");
            const VkDescriptorBufferInfo agg{cells_.buf, 0, VK_WHOLE_SIZE};
            for (auto& x : w) x.dstSet = aggSet_;
            w[0].pBufferInfo = &agg;
            vkUpdateDescriptorSets(g.dev, 4, w, 0, nullptr);
        }

        vs_ = shader(g, "gaia.vert.spv");
        fs_ = shader(g, "etoiles.frag.spv");      // même tache ronde que les étoiles du catalogue principal
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
        const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(GaiaPush)};
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
        if (cellCount + skyCount) {
            aggVs_ = shader(g, "gaia_agrege.vert.spv");
            stages[0].module = aggVs_;
            check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &aggPipeline_), "pipeline Gaia (lumière additionnée)");
            stages[0].module = vs_;
        }
        if (!file_.bins) return;
        // Lumière cumulée des étoiles sautées : un point par feuille, sommets ordinaires (8 flottants).
        restVs_ = shader(g, "gaia_reste.vert.spv");
        stages[0].module = restVs_;
        const VkVertexInputBindingDescription bind{0, 32, VK_VERTEX_INPUT_RATE_VERTEX};
        const VkVertexInputAttributeDescription attrs[2] = {{0, 0, VK_FORMAT_R32G32B32A32_SFLOAT, 0}, {1, 0, VK_FORMAT_R32G32B32A32_SFLOAT, 16}};
        VkPipelineVertexInputStateCreateInfo vin2{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        vin2.vertexBindingDescriptionCount = 1;
        vin2.pVertexBindingDescriptions = &bind;
        vin2.vertexAttributeDescriptionCount = 2;
        vin2.pVertexAttributeDescriptions = attrs;
        pci.pVertexInputState = &vin2;
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &restPipeline_), "pipeline Gaia (lumière cumulée)");
    }
};

}  // namespace
