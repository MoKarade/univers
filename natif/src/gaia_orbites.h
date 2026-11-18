// Appli PC « Univers » : l'orbite EXACTE des 98 millions d'étoiles Gaia, calculée sur la carte graphique avec le même
// shader que les étoiles du catalogue principal (shaders/orbites_pas.comp, fil natif, contrôlé contre la bibliothèque de
// physique en double précision).
//
// Différences avec OrbitGpu (orbites_gpu.h), pour tenir en mémoire (98 M étoiles × 32 octets = 3,15 Go par état) :
//   - un seul état, avancé EN PLACE (les étoiles ne s'attirent pas : chacune ne lit et n'écrit que la sienne) ;
//   - entre deux pas d'un million d'années, la position est prolongée par un développement au second ordre
//     (x + h v + h² a / 2, accélération du même potentiel) dans gaia.vert : écart de l'ordre du parsec ;
//   - retour à aujourd'hui : les états de départ, gardés en mémoire vive (3,15 Go), sont recopiés sur la carte.
// Les états de départ (position et vitesse MESURÉES, passées en galactocentrique ; nombre de sous-pas par la même règle
// que OrbitGpu::subSteps) sont calculés dans un fil à part au chargement ; tant qu'ils ne sont pas prêts, ou pendant un
// rattrapage, gaia.vert prend les épicycles (orbite_galactique.glsl).
// Le Soleil est le dernier état : le monde du simulateur reste centré sur lui.
#pragma once
#include <algorithm>
#include <atomic>
#include <thread>
#include <vector>
#include "commun.h"
#include "orbites_gpu.h"

namespace {

class GaiaOrbits {
public:
    static constexpr double kStepYears = 1.0e6;
    static constexpr double kStarStepsPerFrame = 4.0e7;      // au plus 40 M étoiles × pas par image (environ 10 ms mesurés)
    uint32_t count = 0;          // étoiles + cases + le Soleil (dernier)
    long target = 0;             // pas de la date montrée (années depuis les mesures de Gaia / 1 Ma, arrondi vers le bas)
    long lagSteps = 0;           // retard du plus en retard des morceaux voulus
    long stepAt = 0;             // pas du dernier morceau (cases et Soleil) : sert au contrôle
    Buffer state;

    // Un morceau est prêt à dessiner en orbite exacte s'il est au pas de la date montrée, ainsi que le dernier morceau
    // (cases et Soleil, origine du repère).
    bool rangeReady(size_t r) const { return uploaded_ && step_[r] == target && step_.back() == target; }
    bool readyToDraw() const { return uploaded_ && step_.back() == target; }
    bool initialReady() const { return initDone_.load(); }
    const std::vector<float>& initial() const { return initial_; }
    // Contrôle : relit les n premiers états (8 flottants par étoile).
    // Contrôle : relit n états à partir du rang first (8 flottants chacun : position kpc, réservé, vitesse km/s, réservé).
    std::vector<float> readBack(const Gpu& g, uint32_t n, uint32_t first = 0) const {
        const VkDeviceSize bytes = static_cast<VkDeviceSize>(n) * 32;
        Buffer host = createBuffer(g, bytes, VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        VkCommandBuffer c = beginOnce(g);
        const VkBufferCopy region{static_cast<VkDeviceSize>(first) * 32, 0, bytes};
        vkCmdCopyBuffer(c, state.buf, host.buf, 1, &region);
        endOnce(g, c);
        std::vector<float> out(static_cast<size_t>(n) * 8);
        void* q = nullptr;
        check(vkMapMemory(g.dev, host.mem, 0, bytes, 0, &q), "relecture des orbites Gaia");
        std::memcpy(out.data(), q, bytes);
        vkUnmapMemory(g.dev, host.mem);
        destroy(g, host);
        return out;
    }

    // stars : 16 octets par étoile (x, y, z en al, ...) ; vel : 8 octets par étoile (i16, pas de 0,05 km/s).
    // ranges : morceaux d'étoiles avancés chacun à son rythme (les feuilles de l'arbre) ; un dernier morceau est ajouté
    // pour les autres corps (extraPos, extraVel : cases de lumière additionnée) et le Soleil, avancé à chaque image.
    void create(const Gpu& g, const uint8_t* stars, const uint8_t* vel, uint64_t n, std::vector<std::pair<uint32_t, uint32_t>> ranges,
                std::vector<Vec3> extraPos = {}, std::vector<Vec3> extraVel = {}) {
        extraPos_ = std::move(extraPos);
        extraVel_ = std::move(extraVel);
        count = static_cast<uint32_t>(n + extraPos_.size() + 1);
        ranges_ = std::move(ranges);
        ranges_.push_back({static_cast<uint32_t>(n), static_cast<uint32_t>(extraPos_.size() + 1)});
        step_.assign(ranges_.size(), 0);
        state = createBuffer(g, static_cast<VkDeviceSize>(count) * 32, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                             VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        worker_ = std::thread([this, stars, vel, n] { computeInitial(stars, vel, n); });
        createPipeline(g);
    }

    // Avance vers la date montrée les morceaux voulus (wanted : les feuilles dessinées) et toujours le dernier (cases et
    // Soleil). Les autres feuilles attendent : elles rattraperont quand elles seront voulues (même calcul, différé).
    // budget : pas d'un million d'années au plus par morceau et par image. Hors d'une passe de dessin. since : années
    // depuis les mesures de Gaia.
    void advance(const Gpu& g, VkCommandBuffer cmd, double since, long budget, const std::vector<uint32_t>& wanted) {
        target = static_cast<long>(std::floor(since / kStepYears));
        if (!initDone_.load()) { lagSteps = 1; return; }
        if (!uploaded_) { upload(g, 0, count); uploaded_ = true; }
        // Par tours : à chaque tour, un pas pour chaque morceau en retard ; les morceaux voisins au même pas partent en un
        // seul calcul ; une seule barrière par tour. Équitable : aucun morceau voulu n'attend derrière les autres.
        std::vector<uint32_t> want;
        want.reserve(wanted.size() + 1);
        for (uint32_t r : wanted)
            if (r + 1 < ranges_.size()) want.push_back(r);
        std::sort(want.begin(), want.end());
        want.push_back(static_cast<uint32_t>(ranges_.size() - 1));      // cases et Soleil : toujours
        for (uint32_t r : want) {
            long& at = step_[r];
            if (at != target && std::labs(target) < std::labs(target - at) && std::labs(target - at) > budget) {
                upload(g, ranges_[r].first, ranges_[r].second);      // plus court en repartant d'aujourd'hui (états mesurés)
                at = 0;
            }
        }
        double starSteps = 0;
        bool bound = false;
        for (long round = 0; round < budget; ++round) {
            double roundStars = 0;
            for (uint32_t r : want)
                if (step_[r] != target) roundStars += ranges_[r].second;
            if (roundStars == 0 || (round > 0 && starSteps + roundStars > kStarStepsPerFrame)) break;
            if (!bound) {
                vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe_);
                vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, layout_, 0, 1, &set_, 0, nullptr);
                bound = true;
            }
            size_t k = 0;
            while (k < want.size()) {
                const uint32_t r = want[k];
                if (step_[r] == target) { ++k; continue; }
                const long at = step_[r];
                uint32_t first = ranges_[r].first, n = ranges_[r].second;
                size_t e = k + 1;      // voisins contigus, au même pas : un seul calcul
                while (e < want.size() && step_[want[e]] == at && ranges_[want[e]].first == first + n) { n += ranges_[want[e]].second; ++e; }
                const double dir = target > at ? 1.0 : -1.0;
                const OrbitGpu::StepPush p{static_cast<float>(at * 1.0e-3), static_cast<float>(dir * 1.0e-3), first, n};
                vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(p), &p);
                vkCmdDispatch(cmd, (n + 255) / 256, 1, 1);
                for (size_t q = k; q < e; ++q) step_[want[q]] += static_cast<long>(dir);
                k = e;
            }
            VkMemoryBarrier mb{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
            mb.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
            mb.dstAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
            vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT | VK_PIPELINE_STAGE_VERTEX_SHADER_BIT, 0, 1, &mb, 0,
                                 nullptr, 0, nullptr);
            starSteps += roundStars;
        }
        lagSteps = 0;
        for (uint32_t r : want) lagSteps = std::max(lagSteps, std::labs(target - step_[r]));
        stepAt = step_.back();
    }

    // FILM : les états ne sont plus calculés ici, ils viennent du film du Groupe local (film_etoiles.h). etats : 8 flottants
    // par corps, comme l'état de la carte (position galactocentrique en kpc, réservé, vitesse en km/s, réservé), pour TOUS
    // les corps dans l'ordre du tampon (étoiles, autres corps, puis le Soleil). step : pas d'un million d'années de ces
    // états. Tous les morceaux sont alors « à jour » à ce pas ; advance() ne doit pas être appelé tant que le film mène.
    void setExternal(const Gpu& g, const std::vector<float>& etats, long step) {
        if (etats.size() != static_cast<size_t>(count) * 8) return;
        uploadFrom(g, reinterpret_cast<const uint8_t*>(etats.data()), 0, count);
        uploaded_ = true;
        external_ = true;
        exactDate_ = false;
        std::fill(step_.begin(), step_.end(), step);
        target = step;
        stepAt = step;
        lagSteps = 0;
    }
    // FILM SUR LA CARTE (film_carte.h) : les états viennent d'être écrits sur la carte à la date EXACTE montrée ; gaia.vert
    // ne les prolonge pas (fraction 0). step : pas d'un million d'années de cette date (pour le contrôle et la sortie du film).
    void markExternalExact(long step) {
        uploaded_ = true;
        external_ = true;
        exactDate_ = true;
        std::fill(step_.begin(), step_.end(), step);
        target = step;
        stepAt = step;
        lagSteps = 0;
    }
    // Fin du film : au prochain advance(), les états repartent des états de départ (mesurés ou du modèle).
    void leaveExternal() {
        if (!external_) return;
        external_ = false;
        exactDate_ = false;
        uploaded_ = false;
        std::fill(step_.begin(), step_.end(), 0L);
    }
    bool external() const { return external_; }

    // Part du pas écoulée depuis l'état (0 à 1).
    float fraction(double since) const {
        if (external_ && exactDate_) return 0.0f;      // état déjà à la date exacte (film sur la carte)
        return static_cast<float>(std::clamp(since / kStepYears - static_cast<double>(target), 0.0, 1.0));
    }

    void release(const Gpu& g) {
        if (worker_.joinable()) worker_.join();
        vkDestroyPipeline(g.dev, pipe_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroyShaderModule(g.dev, cs_, nullptr);
        releaseStaging(g);
        destroy(g, state);
    }

private:
    Buffer staging_{};
    void* stagingMap_ = nullptr;
    VkDeviceSize stagingSize_ = 0;
    std::thread worker_;
    std::atomic<bool> initDone_{false};
    bool uploaded_ = false, external_ = false, exactDate_ = false;
    std::vector<float> initial_;
    std::vector<Vec3> extraPos_, extraVel_;
    std::vector<std::pair<uint32_t, uint32_t>> ranges_;      // (première étoile, nombre)
    std::vector<long> step_;                                 // pas où en est chaque morceau
    VkPipeline pipe_{};
    VkPipelineLayout layout_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet set_{};
    VkShaderModule cs_{};

    void computeInitial(const uint8_t* stars, const uint8_t* vel, uint64_t n) {
        initial_.assign(static_cast<size_t>(count) * 8, 0.0f);
        const phys::galaxie::Potentiel P;
        const phys::Vec3 s = phys::galaxie::soleilPos(), sv = phys::galaxie::soleilVit();
        auto fill = [&](size_t i, Vec3 pos, Vec3 v) {
            const phys::Vec3 pg = orbite::versGalactique(pos), vg = orbite::versGalactique(v);
            const double x[3] = {pg.x / orbite::kKpcLy + s.x, pg.y / orbite::kKpcLy + s.y, pg.z / orbite::kKpcLy + s.z};
            const double w[3] = {vg.x + sv.x, vg.y + sv.y, vg.z + sv.z};
            float* o = &initial_[i * 8];
            for (int a = 0; a < 3; ++a) {
                o[a] = static_cast<float>(x[a]);
                o[4 + a] = static_cast<float>(w[a]);
            }
            o[3] = OrbitGpu::subSteps(P, x, w);
        };
        const unsigned nt = std::max(1u, std::min(32u, std::thread::hardware_concurrency()));
        std::vector<std::thread> th;
        for (unsigned t = 0; t < nt; ++t)
            th.emplace_back([&, t] {
                for (uint64_t i = n * t / nt; i < n * (t + 1) / nt; ++i) {
                    float p[3];
                    int16_t q[3];
                    std::memcpy(p, stars + i * 16, 12);
                    std::memcpy(q, vel + i * 8, 6);
                    fill(i, {p[0], p[1], p[2]}, {q[0] * 0.05, q[1] * 0.05, q[2] * 0.05});
                }
            });
        for (auto& x : th) x.join();
        for (size_t k = 0; k < extraPos_.size(); ++k) fill(n + k, extraPos_[k], extraVel_[k]);
        fill(count - 1, {0, 0, 0}, {0, 0, 0});      // le Soleil
        initDone_.store(true);
    }

    void upload(const Gpu& g, uint32_t first, uint32_t n) { uploadFrom(g, reinterpret_cast<const uint8_t*>(initial_.data()), first, n); }

    void uploadFrom(const Gpu& g, const uint8_t* source, uint32_t first, uint32_t n) {
        constexpr VkDeviceSize kChunk = 256ull << 20;
        const VkDeviceSize base = static_cast<VkDeviceSize>(first) * 32, size = static_cast<VkDeviceSize>(n) * 32;
        // Tampon d'envoi gardé d'un appel à l'autre (revue P1 : le film en envoie un à chaque pas de temps), agrandi au besoin.
        const VkDeviceSize need = std::min(size, kChunk);
        if (need > stagingSize_) {
            releaseStaging(g);
            staging_ = createBuffer(g, need, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            check(vkMapMemory(g.dev, staging_.mem, 0, VK_WHOLE_SIZE, 0, &stagingMap_), "états Gaia");
            stagingSize_ = need;
        }
        for (VkDeviceSize off = 0; off < size; off += kChunk) {
            const VkDeviceSize m = std::min(kChunk, size - off);
            std::memcpy(stagingMap_, source + base + off, m);
            VkCommandBuffer c = beginOnce(g);
            const VkBufferCopy region{0, base + off, m};
            vkCmdCopyBuffer(c, staging_.buf, state.buf, 1, &region);
            endOnce(g, c);      // attend la copie : le tampon d'envoi peut resservir aussitôt
        }
    }

    void releaseStaging(const Gpu& g) {
        if (!stagingSize_) return;
        vkUnmapMemory(g.dev, staging_.mem);
        destroy(g, staging_);
        staging_ = {}; stagingMap_ = nullptr; stagingSize_ = 0;
    }

    void createPipeline(const Gpu& g) {
        VkDescriptorSetLayoutBinding binds[2];
        for (uint32_t i = 0; i < 2; ++i) binds[i] = {i, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 2;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement des orbites Gaia");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 2};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 1;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve des orbites Gaia");
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = 1;
        da.pSetLayouts = &setLayout_;
        check(vkAllocateDescriptorSets(g.dev, &da, &set_), "jeu des orbites Gaia");
        const VkDescriptorBufferInfo info{state.buf, 0, VK_WHOLE_SIZE};      // même tampon en lecture et en écriture : calcul en place
        VkWriteDescriptorSet w[2];
        for (uint32_t i = 0; i < 2; ++i) {
            w[i] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
            w[i].dstSet = set_;
            w[i].dstBinding = i;
            w[i].descriptorCount = 1;
            w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            w[i].pBufferInfo = &info;
        }
        vkUpdateDescriptorSets(g.dev, 2, w, 0, nullptr);
        cs_ = shader(g, "orbites_pas.comp.spv");
        const VkPushConstantRange pcr{VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(OrbitGpu::StepPush)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement du calcul Gaia");
        VkComputePipelineCreateInfo cp{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
        cp.stage = {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO};
        cp.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        cp.stage.module = cs_;
        cp.stage.pName = "main";
        cp.layout = layout_;
        check(vkCreateComputePipelines(g.dev, VK_NULL_HANDLE, 1, &cp, nullptr, &pipe_), "calcul des orbites Gaia");
    }
};

}  // namespace
