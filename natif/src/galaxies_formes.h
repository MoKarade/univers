// Appli PC « Univers » : galaxies de forme MESURÉE, faites de particules (Marc, 13/11/2026 : « plus de galaxies images »).
//
// Données : galaxies_formes.bin (pipeline/natif/galaxies_formes.py) : 532 427 galaxies du Siena Galaxy Atlas 2020 et
// d'HyperLEDA, avec diamètre D26, rapport d'axes, angle de position, type, magnitude r et couleur g - r mesurés quand ils
// existent, distance de Cosmicflows-4 ou décalage vers le rouge. Leurs points du grand catalogue (galaxies.bin) sont
// marqués : galaxies.vert ne les dessine plus, ce module prend leur place.
// Dessin (shaders/galaxie_formes.vert) : de loin, un point au vrai éclat ; dès que la galaxie dépasse 2 pixels à l'écran,
// une galaxie de particules générées à la volée sur la carte graphique (graine fixe par galaxie, rien n'est stocké), en
// fondu jusqu'à 8 pixels, la lumière totale conservée. Nombre de particules selon la taille à l'écran, plafonné.
#pragma once
#include "gaia.h"
#include "galaxies.h"
#include <unordered_map>

namespace {

class GalaxyShapes {
public:
    bool ready = false;
    uint32_t count = 0, shown = 0;      // galaxies, galaxies montrées en particules à la dernière image
    uint64_t particles = 0;
    // Mesure pour la pose « photo » (fenetre.cpp, voir photoMetering) : poids le plus fort des galaxies résolues dans
    // l'image (0 à 1) et brillance de surface moyenne (flux par pixel, exposition 1) pondérée, en logarithme.
    double photoWeight = 0, photoSurface = 0;
    float ageing[4] = {1, 1, 1, 1};      // vieillissement : lumière disque (comp. 1), bulbe et elliptiques (comp. 2), puis températures
      // brillance de surface moyenne la plus forte des galaxies résolues (flux par pixel, exposition 1)

    // Lecture des fiches seulement (sans carte graphique) : sert aussi aux contrôles (essai_selection).
    bool loadRecords(const std::string& path) {
        std::ifstream f(path, std::ios::binary | std::ios::ate);
        if (!f) return false;
        const size_t bytes = static_cast<size_t>(f.tellg());
        if (bytes < 64) return false;
        std::vector<char> b(bytes);
        f.seekg(0);
        f.read(b.data(), static_cast<std::streamsize>(bytes));
        if (std::memcmp(b.data(), "UNIVGFM1", 8) != 0) return false;
        std::memcpy(&count, b.data() + 8, 4);
        if (bytes < 64 + static_cast<size_t>(count) * sizeof(Rec)) return false;
        recs_.resize(count);
        std::memcpy(recs_.data(), b.data() + 64, static_cast<size_t>(count) * sizeof(Rec));
        return true;
    }

    bool create(const Gpu& g, const std::string& path, VkFormat hdrFormat) {
        if (!loadRecords(path)) return false;
        recBuf_ = uploadStorage(g, recs_.data(), static_cast<VkDeviceSize>(count) * sizeof(Rec));
        for (int r = 0; r < kRing; ++r) {
            pos_[r] = createBuffer(g, static_cast<VkDeviceSize>(count) * 16, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            check(vkMapMemory(g.dev, pos_[r].mem, 0, VK_WHOLE_SIZE, 0, &posMap_[r]), "galaxies : positions");
            np_[r] = createBuffer(g, static_cast<VkDeviceSize>(count) * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            check(vkMapMemory(g.dev, np_[r].mem, 0, VK_WHOLE_SIZE, 0, &npMap_[r]), "galaxies : particules");
            ind_[r] = createBuffer(g, static_cast<VkDeviceSize>(kMaxShown) * 16, VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            check(vkMapMemory(g.dev, ind_[r].mem, 0, VK_WHOLE_SIZE, 0, &indMap_[r]), "galaxies : dessins");
        }
        world_.resize(count);
        for (uint32_t i = 0; i < count; ++i)
            if (!(recs_[i].d > 0)) byZ_.push_back({i, GalaxyRenderer::zPlace(recs_[i].z)});
        createPipeline(g, hdrFormat);
        ready = true;
        return true;
    }

    // À chaque image, avant le dessin : place de chaque galaxie (distance mesurée, ou décalage vers le rouge par la table de
    // l'appli) et choix de celles assez grandes à l'écran pour être montrées en particules.
    bool deepTime = false;      // date montrée au-delà de ±3 Ma (posé par la fenêtre, Sim::deepTime)
    void prepare(const Camera& cam, const GalaxyRenderer& cat, uint32_t height) {
        if (!ready) return;
        ring_ = (ring_ + 1) % kRing;
        if (cat.tableVersion != version_) {
            // La table change à chaque million d'années (l'univers grandit) : seules les galaxies placées par leur décalage
            // vers le rouge bougent alors ; celles à distance mesurée sont placées une fois. Leur place dans la table (case,
            // fraction) est calculée une fois (byZ_) : mêmes opérations que distanceLy, mêmes distances, 10 ms -> ~1 ms.
            const bool first = version_ == ~0ull;
            version_ = cat.tableVersion;
            // Distance mesurée : agrandie elle aussi par l'expansion au-delà de 10 Mal, comme le nom et le point de la galaxie
            // (simulation.h, refreshGalaxies). Avant, la forme restait à sa place d'aujourd'hui pendant que son nom et son
            // point s'éloignaient avec l'univers : M77 « se baladait » (Marc, 20/11/2026).
            const double k = cat.scale;
            for (uint32_t i = 0; i < count; ++i) {
                const Rec& r = recs_[i];
                if (r.d <= 0) continue;
                const double d = r.d > 1.0e7 ? r.d * k : r.d;
                world_[i] = {r.ux * d, r.uy * d, r.uz * d, d};
            }
            if (first) {
                for (uint32_t i = 0; i < count; ++i) {
                    const Rec& r = recs_[i];
                    if (r.d > 0) continue;
                    const double d = cat.distanceLy(r.z);
                    world_[i] = {r.ux * d, r.uy * d, r.uz * d, d};
                }
            } else {
                for (const ByZ& b : byZ_) {
                    const Rec& r = recs_[b.i];
                    const double d = cat.distanceAt(b.p);
                    world_[b.i] = {r.ux * d, r.uy * d, r.uz * d, d};
                }
            }
        }
        const double pxPerRad = height / (2.0 * cam.tanHalf);
        pxPerRad_ = pxPerRad;
        auto* pos = static_cast<float*>(posMap_[ring_]);
        auto* np = static_cast<uint32_t*>(npMap_[ring_]);
        auto* ind = static_cast<VkDrawIndirectCommand*>(indMap_[ring_]);
        const double tx = cam.tanHalf * cam.aspect * 1.05, ty = cam.tanHalf * 1.05;
        shown = 0;
        particles = 0;
        double wMax = 0, wSum = 0, logSum = 0;
        for (uint32_t i = 0; i < count; ++i) {
            const W& w = world_[i];
            const double rx = w.x - cam.pos.x, ry = w.y - cam.pos.y, rz = w.z - cam.pos.z;
            pos[i * 4] = static_cast<float>(rx);
            pos[i * 4 + 1] = static_cast<float>(ry);
            pos[i * 4 + 2] = static_cast<float>(rz);
            pos[i * 4 + 3] = static_cast<float>(w.d);
            np[i] = 0;
            // Loin d'aujourd'hui (au-delà de ±3 Ma), une galaxie à moins de 10 Mal n'a pas de place calculée ici (son nom est
            // caché, simulation.h refreshGalaxies) : sa forme n'est pas laissée à sa place d'aujourd'hui (inventaire du 20/11 :
            // forme dessinée mais impossible à cliquer).
            if ((!hidden_.empty() && hidden_[i]) || (deepTime && recs_[i].d > 0 && recs_[i].d <= 1.0e7)) {      // ni point ni forme (flux nul : P.w = 0)
                pos[i * 4 + 3] = 0.0f;
                continue;
            }
            const double dc = std::sqrt(rx * rx + ry * ry + rz * rz);
            const double size = recs_[i].diam * 2.9088821e-4 * w.d;      // diamètre (al)
            const double px = size / std::max(dc, 1.0) * pxPerRad;
            if (px < 2.0 || shown >= kMaxShown) continue;
            // dans le champ (avec la marge de la taille de la galaxie)
            const double f = rx * cam.fwd.x + ry * cam.fwd.y + rz * cam.fwd.z;
            if (f < -size) continue;
            const double x = rx * cam.right.x + ry * cam.right.y + rz * cam.right.z, y = rx * cam.up.x + ry * cam.up.y + rz * cam.up.z;
            const double fz = std::max(f, 1.0);
            if (std::fabs(x) > fz * tx + size || std::fabs(y) > fz * ty + size) continue;
            // Mesure « photo » : galaxie résolue et dans l'image. Avant (Marc, 20/11/2026 : « parfois trop clair, parfois trop
            // sombre ») : toute galaxie de plus de 40 pixels, même hors de l'image, faisait basculer la pose d'un coup (×3
            // d'éclat d'un degré de défilement au suivant, mesuré). Maintenant son poids monte en continu de 40 à 160 pixels
            // et suit la part de son disque dans l'image : la pose glisse au lieu de sauter.
            if (px > 40.0 && f > 0) {
                const double fl = std::pow(10.0, -0.4 * recs_[i].r) * (w.d / std::max(dc, 1.0)) * (w.d / std::max(dc, 1.0));
                const double surf = fl / (0.785398 * px * px * std::max(static_cast<double>(recs_[i].ba), 0.2));
                const double r = 0.5 * size / fz;      // rayon du disque, en tangente
                const double inX = std::clamp((cam.tanHalf * cam.aspect - std::fabs(x / fz) + r) / (2.0 * r), 0.0, 1.0);
                const double inY = std::clamp((cam.tanHalf - std::fabs(y / fz) + r) / (2.0 * r), 0.0, 1.0);
                const double wt = std::clamp(std::log(px / 40.0) / std::log(4.0), 0.0, 1.0) * inX * inY;
                if (wt > 0 && surf > 0) {
                    wMax = std::max(wMax, wt);
                    wSum += wt;
                    logSum += wt * std::log(surf);
                }
            }
            const uint32_t n = static_cast<uint32_t>(std::clamp(px * px * 0.3, 64.0, 30000.0));
            if (particles + n > kMaxParticles) continue;
            np[i] = n;
            particles += n;
            ind[shown++] = {n, 1, 0, i};      // une instance : la galaxie i (gl_InstanceIndex)
        }
        photoWeight = wMax;
        photoSurface = wSum > 0 ? std::exp(logSum / wSum) : 0.0;
    }

    // Galaxies proches placées d'après leur décalage vers le rouge : sous cz ≈ 1 500 km/s, la vitesse propre de la galaxie
    // domine et la distance tirée de z est fausse (NGC 2976 posée à 68 000 al, en satellite de la Voie lactée, alors que
    // Cosmicflows-4 la mesure à 3,6 Mpc). Quand une galaxie de Cosmicflows-4 (distance mesurée : Tully-Fisher, céphéides,
    // pointe des géantes rouges…) est dans la même direction (moins de 0,1°), sa distance mesurée remplace celle de z.
    // À appeler avant snapNames. Rend le nombre de distances remplacées.
    static constexpr double kZInconnue = 0.001;

    // Formes rangées par cases de 0,5° du ciel, pour retrouver vite celles d'une direction.
    using Grid = std::unordered_map<uint64_t, std::vector<uint32_t>>;
    static uint64_t cellKey(double ux, double uy, double uz, int dl, int db) {
        constexpr double kBin = 0.5 * 3.14159265358979 / 180.0;      // cases de 0,5° en latitude et longitude
        const long b = static_cast<long>(std::floor(std::asin(std::clamp(uz, -1.0, 1.0)) / kBin)) + db;
        const long l = static_cast<long>(std::floor((std::atan2(uy, ux) + 3.14159265358979) / kBin)) + dl;
        return static_cast<uint64_t>((b + 1000) * 4000 + ((l % 720) + 720) % 720);
    }
    Grid makeGrid() const {
        Grid grid;
        for (uint32_t i = 0; i < count; ++i) grid[cellKey(recs_[i].ux, recs_[i].uy, recs_[i].uz, 0, 0)].push_back(i);
        return grid;
    }
    // Décalage vers le rouge écrit dans la fiche (« z = 0.0038 ») ; 0 s'il n'y en a pas.
    static double zOfText(const std::string& t) {
        const size_t k = t.rfind("z = ");
        return k == std::string::npos ? 0.0 : std::atof(t.c_str() + k + 4);
    }
    // La forme d'une galaxie nommée, dans la direction (ux, uy, uz) : parmi les formes à moins de 0,1°, celle dont le centre
    // est le plus près EN UNITÉS DE SON PROPRE RAYON ; une forme dont le z (à 0,002 près) ou la distance mesurée (à 2 %)
    // contredit la fiche passe après. Avant : la plus proche en angle, si bien qu'une petite galaxie de fond posée sur une
    // grande prenait son nom (IC 3546 nommée sur une galaxie à z = 0,17, à 2,4 milliards d'al ; essai_selection, 20/11/2026).
    int bestRec(const Grid& grid, double ux, double uy, double uz, double zName, double dName) const {
        constexpr double kCos = 0.99999847691, kArcmin = 2.9088821e-4;      // cos(0,1°) ; une minute d'arc en radians
        double best = 1e300;
        int bi = -1;
        for (int db = -1; db <= 1; ++db)
            for (int dl = -1; dl <= 1; ++dl) {
                const auto it = grid.find(cellKey(ux, uy, uz, dl, db));
                if (it == grid.end()) continue;
                for (uint32_t i : it->second) {
                    const Rec& r = recs_[i];
                    const double nu = std::sqrt(double(r.ux) * r.ux + double(r.uy) * r.uy + double(r.uz) * r.uz);      // simple précision : renormalisée
                    const double c = (ux * r.ux + uy * r.uy + uz * r.uz) / nu;
                    if (c < kCos) continue;
                    const double ang = std::sqrt(std::max(2.0 * (1.0 - c), 0.0));
                    double score = ang / std::max(0.5 * static_cast<double>(r.diam) * kArcmin, 1e-6);
                    if (zName > 0 && r.z > 0 && std::fabs(r.z - zName) > 0.002) score += 100.0;
                    if (dName > 0 && r.d > 0 && std::fabs(r.d / dName - 1.0) > 0.02) score += 100.0;
                    if (score < best) { best = score; bi = static_cast<int>(i); }
                }
            }
        return bi;
    }

    int fixNearbyDistances(const std::vector<Body>& bodies) {
        if (recs_.empty()) return 0;
        constexpr double kZMax = 0.005, kCos = 0.99999847691;      // cos(0,1°)
        // sous z = 0,001 (cz < 300 km/s), z ne dit rien de la distance (vitesses propres et chute vers le Groupe local)
        std::vector<std::pair<Vec3, double>> cf4;
        for (const Body& b : bodies)
            if (b.kind == Kind::Galaxy && b.natureText.find("Cosmicflows-4") != std::string::npos) {
                const double n = std::sqrt(dot(b.fixedPos, b.fixedPos));
                if (n > 0) cf4.push_back({{b.fixedPos.x / n, b.fixedPos.y / n, b.fixedPos.z / n}, n});
            }
        int fixed = 0;
        for (uint32_t i = 0; i < count; ++i) {
            Rec& r = recs_[i];
            if (r.d > 0 || !(r.z < kZMax)) continue;
            double best = kCos, d = 0;
            for (const auto& [u, n] : cf4) {
                const double c = u.x * r.ux + u.y * r.uy + u.z * r.uz;
                if (c > best) { best = c; d = n; }
            }
            if (d > 0) {
                r.d = static_cast<float>(d);
                ++fixed;
            } else if (r.z < kZInconnue) {      // ni distance mesurée ni z exploitable : distance inconnue, non dessinée
                if (hidden_.empty()) hidden_.assign(count, 0);
                hidden_[i] = 1;
            }
        }
        // Plus loin (z ≥ 0,005) : seulement LA forme de la galaxie nommée qui a reçu la distance mesurée de la même galaxie, sous
        // le même nom (simulation.h, loadBodies : M77, NGC 1646…), choisie comme pour son nom (bestRec) : une petite galaxie
        // de fond dans la même direction garde sa propre distance.
        const Grid grid = makeGrid();
        for (const Body& b : bodies) {
            if (b.kind != Kind::Galaxy || b.merged || b.natureText.find("SGA-2020") == std::string::npos || b.natureText.find("Cosmicflows-4") == std::string::npos) continue;
            const double n = std::sqrt(dot(b.fixedPos, b.fixedPos));
            if (n <= 0) continue;
            const int k = bestRec(grid, b.fixedPos.x / n, b.fixedPos.y / n, b.fixedPos.z / n, zOfText(b.natureText), 0.0);
            if (k < 0 || recs_[static_cast<size_t>(k)].d > 0) continue;
            recs_[static_cast<size_t>(k)].d = static_cast<float>(n);
            ++fixed;
        }
        if (fixed) {      // les distances remplacées ne suivent plus la table des décalages vers le rouge
            byZ_.erase(std::remove_if(byZ_.begin(), byZ_.end(), [&](const ByZ& b) { return recs_[b.i].d > 0; }), byZ_.end());
            version_ = ~0ull;
        }
        return fixed;
    }

    // Le nom d'une galaxie de forme (galaxies_formes_noms.tsv) est posé exactement au centre de sa forme : sa place
    // d'aujourd'hui devient celle de la forme (même direction, même distance que le dessin). Avant, le nom et la caméra
    // visaient un point décalé d'environ un tiers du rayon (M77 : ~20 000 al à 55 Mal ; Marc, 20/11/2026). Rend le nombre
    // de noms posés.
    int snapNames(std::vector<Body>& bodies, const GalaxyRenderer& cat) const {
        if (!ready) return 0;
        return snapNamesWith(bodies, [&](float z) { return cat.distanceLy(z); });
    }
    // distanceOfZ : distance (al) d'un décalage vers le rouge, comme la table de l'appli.
    template <class DistanceOfZ>
    int snapNamesWith(std::vector<Body>& bodies, DistanceOfZ&& distanceOfZ) const {
        if (recs_.empty()) return 0;
        const Grid grid = makeGrid();
        int snapped = 0;
        for (Body& b : bodies) {
            if (b.kind != Kind::Galaxy || b.merged || b.natureText.find("SGA-2020") == std::string::npos) continue;
            const double n = std::sqrt(dot(b.fixedPos, b.fixedPos));
            if (n <= 0) continue;
            const bool measured = b.natureText.find("Cosmicflows-4") != std::string::npos;
            const int bi = bestRec(grid, b.fixedPos.x / n, b.fixedPos.y / n, b.fixedPos.z / n, zOfText(b.natureText), measured ? n : 0.0);
            if (bi < 0) continue;
            const Rec& r = recs_[static_cast<size_t>(bi)];
            const double d = r.d > 0 ? r.d : distanceOfZ(r.z);
            if (!(d > 0)) continue;
            b.fixedPos = {r.ux * d, r.uy * d, r.uz * d};
            // rayon de la forme dessinée (diamètre mesuré en minutes d'arc × distance, comme prepare) : la galaxie se clique sur
            // toute sa forme, pas seulement en son centre (inventaire du 20/11/2026)
            b.drawnRadiusLy = 0.5 * r.diam * 2.9088821e-4 * d;
            ++snapped;
        }
        return snapped;
    }

    void draw(VkCommandBuffer cmd, const Camera& cam, uint32_t width, uint32_t height, float exposure) {
        if (!ready) return;
        Push p{};
        const auto m = cam.viewProj();
        std::memcpy(p.viewProj, m.data(), sizeof(p.viewProj));
        p.par[0] = exposure;
        p.par[1] = static_cast<float>(height);
        p.par[2] = static_cast<float>(pxPerRad_);
        for (int k = 0; k < 4; ++k) p.par2[k] = ageing[k];
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        const VkRect2D sc{{0, 0}, {width, height}};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &set_[ring_], 0, nullptr);
        p.par[3] = 0.0f;      // points
        vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(p), &p);
        vkCmdDraw(cmd, count, 1, 0, 0);
        if (shown) {      // particules
            p.par[3] = 1.0f;
            vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(p), &p);
            vkCmdDrawIndirect(cmd, ind_[ring_].buf, 0, shown, sizeof(VkDrawIndirectCommand));
        }
    }

    void release(const Gpu& g) {
        if (!ready) return;
        for (int r = 0; r < kRing; ++r) {
            vkUnmapMemory(g.dev, pos_[r].mem); destroy(g, pos_[r]);
            vkUnmapMemory(g.dev, np_[r].mem); destroy(g, np_[r]);
            vkUnmapMemory(g.dev, ind_[r].mem); destroy(g, ind_[r]);
        }
        destroy(g, recBuf_);
        vkDestroyPipeline(g.dev, pipeline_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
        ready = false;
    }

private:
    static constexpr int kRing = 3;
    static constexpr uint32_t kMaxShown = 20000;
    static constexpr uint64_t kMaxParticles = 6000000;      // particules par image, toutes galaxies (~100 Mo de sommets générés, rien de stocké)
    struct Rec { float ux, uy, uz, z, d, diam, ba, pa, T, r, gr; uint32_t f; };
    static_assert(sizeof(Rec) == 48, "fiche de galaxies_formes.bin : 48 octets");
    struct W { double x, y, z, d; };
    struct Push { float viewProj[16]; float par[4]; float par2[4]; };

    void createPipeline(const Gpu& g, VkFormat fmt) {
        VkDescriptorSetLayoutBinding binds[3];
        for (uint32_t i = 0; i < 3; ++i) binds[i] = {i, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_VERTEX_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 3;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement des galaxies de forme");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 3 * kRing};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = kRing;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve des galaxies de forme");
        for (int r = 0; r < kRing; ++r) {
            VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
            da.descriptorPool = pool_;
            da.descriptorSetCount = 1;
            da.pSetLayouts = &setLayout_;
            check(vkAllocateDescriptorSets(g.dev, &da, &set_[r]), "jeu des galaxies de forme");
            const VkDescriptorBufferInfo infos[3] = {{recBuf_.buf, 0, VK_WHOLE_SIZE}, {pos_[r].buf, 0, VK_WHOLE_SIZE}, {np_[r].buf, 0, VK_WHOLE_SIZE}};
            VkWriteDescriptorSet w[3];
            for (uint32_t i = 0; i < 3; ++i) {
                w[i] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
                w[i].dstSet = set_[r];
                w[i].dstBinding = i;
                w[i].descriptorCount = 1;
                w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
                w[i].pBufferInfo = &infos[i];
            }
            vkUpdateDescriptorSets(g.dev, 3, w, 0, nullptr);
        }
        const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(Push)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement des galaxies de forme");
        vs_ = shader(g, "galaxie_formes.vert.spv");
        fs_ = shader(g, "etoiles.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
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
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline_), "dessin des galaxies de forme");
    }

    std::vector<Rec> recs_;
    std::vector<W> world_;
    struct ByZ { uint32_t i; GalaxyRenderer::ZPlace p; };
    std::vector<ByZ> byZ_;      // galaxies placées par leur décalage vers le rouge, et leur place dans la table des distances
    uint64_t version_ = ~0ull;
    double pxPerRad_ = 1;
    int ring_ = 0;
    Buffer recBuf_, pos_[kRing], np_[kRing], ind_[kRing];
    std::vector<char> hidden_;      // galaxies de distance inconnue (fixNearbyDistances), non dessinées
    void* posMap_[kRing] = {};
    void* npMap_[kRing] = {};
    void* indMap_[kRing] = {};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet set_[kRing]{};
    VkPipelineLayout layout_{};
    VkPipeline pipeline_{};
    VkShaderModule vs_{}, fs_{};
};

}  // namespace
