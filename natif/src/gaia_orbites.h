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
#include <atomic>
#include <thread>
#include <vector>
#include "commun.h"
#include "orbites_gpu.h"

namespace {

class GaiaOrbits {
public:
    static constexpr double kStepYears = 1.0e6;
    uint32_t count = 0;          // étoiles + le Soleil (dernier)
    long stepAt = 0;             // l'état est au pas stepAt (années depuis les mesures de Gaia / 1 Ma)
    long lagSteps = 0;           // pas restant pour rejoindre la date montrée
    Buffer state;

    bool readyToDraw() const { return uploaded_ && lagSteps == 0; }
    bool initialReady() const { return initDone_.load(); }
    const std::vector<float>& initial() const { return initial_; }
    // Contrôle : relit les n premiers états (8 flottants par étoile).
    std::vector<float> readBack(const Gpu& g, uint32_t n) const {
        const VkDeviceSize bytes = static_cast<VkDeviceSize>(n) * 32;
        Buffer host = createBuffer(g, bytes, VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        VkCommandBuffer c = beginOnce(g);
        const VkBufferCopy region{0, 0, bytes};
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
    void create(const Gpu& g, const uint8_t* stars, const uint8_t* vel, uint64_t n) {
        count = static_cast<uint32_t>(n + 1);
        state = createBuffer(g, static_cast<VkDeviceSize>(count) * 32, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                             VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        worker_ = std::thread([this, stars, vel, n] { computeInitial(stars, vel, n); });
        createPipeline(g);
    }

    // Avance l'état vers la date montrée, `budget` pas au plus. Hors d'une passe de dessin.
    // since : années depuis les mesures de Gaia.
    void advance(const Gpu& g, VkCommandBuffer cmd, double since, long budget) {
        if (!initDone_.load()) { lagSteps = 1; return; }
        if (!uploaded_) { upload(g); uploaded_ = true; stepAt = 0; }
        const long target = static_cast<long>(std::floor(since / kStepYears));
        if (target != stepAt && std::labs(target) < std::labs(target - stepAt) && std::labs(target - stepAt) > budget) {
            upload(g);      // plus court en repartant d'aujourd'hui (les états mesurés)
            stepAt = 0;
        }
        if (target != stepAt) {
            vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe_);
            vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, layout_, 0, 1, &set_, 0, nullptr);
        }
        while (target != stepAt && budget-- > 0) {
            const double dir = target > stepAt ? 1.0 : -1.0;
            const OrbitGpu::StepPush p{static_cast<float>(stepAt * 1.0e-3), static_cast<float>(dir * 1.0e-3), 0, count};
            vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(p), &p);
            vkCmdDispatch(cmd, (count + 255) / 256, 1, 1);
            VkMemoryBarrier b{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
            b.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
            b.dstAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
            vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT | VK_PIPELINE_STAGE_VERTEX_SHADER_BIT, 0, 1, &b,
                                 0, nullptr, 0, nullptr);
            stepAt += static_cast<long>(dir);
        }
        lagSteps = std::labs(target - stepAt);
    }

    // Part du pas écoulée depuis l'état (0 à 1).
    float fraction(double since) const { return static_cast<float>(std::clamp(since / kStepYears - static_cast<double>(stepAt), 0.0, 1.0)); }

    void release(const Gpu& g) {
        if (worker_.joinable()) worker_.join();
        vkDestroyPipeline(g.dev, pipe_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroyShaderModule(g.dev, cs_, nullptr);
        destroy(g, state);
    }

private:
    std::thread worker_;
    std::atomic<bool> initDone_{false};
    bool uploaded_ = false;
    std::vector<float> initial_;
    VkPipeline pipe_{};
    VkPipelineLayout layout_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet set_{};
    VkShaderModule cs_{};

    void computeInitial(const uint8_t* stars, const uint8_t* vel, uint64_t n) {
        initial_.assign(static_cast<size_t>(n + 1) * 8, 0.0f);
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
        fill(n, {0, 0, 0}, {0, 0, 0});      // le Soleil
        initDone_.store(true);
    }

    void upload(const Gpu& g) {
        constexpr VkDeviceSize kChunk = 256ull << 20;
        const VkDeviceSize size = static_cast<VkDeviceSize>(count) * 32;
        Buffer staging = createBuffer(g, std::min(size, kChunk), VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, VK_WHOLE_SIZE, 0, &p), "états Gaia");
        for (VkDeviceSize off = 0; off < size; off += kChunk) {
            const VkDeviceSize m = std::min(kChunk, size - off);
            std::memcpy(p, reinterpret_cast<const uint8_t*>(initial_.data()) + off, m);
            VkCommandBuffer c = beginOnce(g);
            const VkBufferCopy region{0, off, m};
            vkCmdCopyBuffer(c, staging.buf, state.buf, 1, &region);
            endOnce(g, c);
        }
        vkUnmapMemory(g.dev, staging.mem);
        destroy(g, staging);
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
