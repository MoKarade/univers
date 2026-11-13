// Appli PC « Univers » : les 1,62 milliard de sources Gaia DR3 SANS distance mesurée (parallaxe sous 5 sigma ou absente),
// une à une, sur le ciel vu du Soleil (plan : docs/plan-gaia-complet.md ; tuiles : pipeline/natif/gaia_tuiles.py).
//
// Leur direction est mesurée, pas leur distance : elles sont donc dessinées à l'infini, comme une carte du ciel, et
// seulement près du Soleil (à moins de 100 années-lumière, aujourd'hui), d'où le ciel est celui que Gaia a vu.
// Elles s'allument quand on grossit (champ de 20° ou moins, Ctrl + molette) : c'est alors la vue « à la lunette », et la
// lumière additionnée par case de ces mêmes sources (gaia.h, « ciel seul ») est retirée pour ne pas compter deux fois.
//
// Lecture à la demande : index sur le PC (gaia_tuiles.idx, 3 Mo), paquets sur le Google Drive (lecteur G:, Drive les
// télécharge et les garde en cache ; racine : première ligne de tuiles_dossier.txt, sous-dossier « gaia »). Quatre fils
// de lecture ; dans une tuile, étoiles de la plus brillante à la plus faible : on ne lit que le début utile.
// La limite d'éclat est choisie pour tenir dans kBudget étoiles à l'écran ; elle est dite à l'écran.
#pragma once
#include "commun.h"
#include "ciel_tuiles.h"
#include <atomic>
#include <condition_variable>
#include <deque>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <thread>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace {

class GaiaSkyTiles {
public:
    static constexpr double kFovOnDeg = 20.0;          // champ à partir duquel les sources s'allument une à une
    static constexpr double kRadiusLy = 100.0;         // même limite que le « ciel seul » de gaia.h
    static constexpr uint32_t kBudget = 8'000'000;     // étoiles à l'écran au plus (192 Mo par tampon)
    static constexpr int kOrder = 6, kPackShift = 2 * (kOrder - 3);
    static constexpr uint32_t kStride = 24;            // octets par étoile (gaia_tuiles.py)

    bool ready = false, active = false;
    uint32_t shownStars = 0, pendingTiles = 0;
    float gLimit = 0;

    bool create(const Gpu& g, const std::string& dataDir, VkFormat hdrFormat, VkBuffer colors) {
        namespace fs = std::filesystem;
        if (!readIndex(dataDir + "/gaia_tuiles.idx") || !readCentres(dataDir + "/gaia_tuiles_centres.bin")) return false;
        std::ifstream f(fs::path(dataDir) / "tuiles_dossier.txt");
        std::string root;
        if (!f || !std::getline(f, root)) return false;
        while (!root.empty() && (root.back() == '\r' || root.back() == ' ')) root.pop_back();
        if (root.size() >= 3 && static_cast<unsigned char>(root[0]) == 0xEF) root = root.substr(3);      // marque UTF-8
        root_ = utf8Path(root) / "gaia";
        for (int k = 0; k < 2; ++k) {
            buf_[k] = createBuffer(g, static_cast<VkDeviceSize>(kBudget) * kStride, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,
                                   VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            check(vkMapMemory(g.dev, buf_[k].mem, 0, VK_WHOLE_SIZE, 0, &map_[k]), "étoiles Gaia du ciel");
        }
        createPipeline(g, hdrFormat, colors);
        for (int i = 0; i < 4; ++i) workers_.emplace_back([this] { work(); });
        ready = true;
        return true;
    }

    // À chaque image, après l'attente de la barrière de l'image (le tampon écrit n'est plus lu par la carte graphique).
    void update(const Camera& cam, double fovDeg, bool today) {
        active = ready && today && fovDeg <= kFovOnDeg && std::sqrt(dot(cam.pos, cam.pos)) < kRadiusLy;
        if (!active) { shownStars = 0; pendingTiles = 0; return; }
        // Tuiles dans le champ (cercle qui contient l'écran, plus le rayon d'une tuile).
        const double half = std::atan(cam.tanHalf * std::sqrt(1.0 + cam.aspect * cam.aspect)) + 0.9 * kPi / 180.0;
        const double cosHalf = std::cos(half);
        std::vector<uint32_t> vis;
        for (uint32_t n = 0; n < count_.size(); ++n)
            if (count_[n] && centre_[3 * n] * cam.fwd.x + centre_[3 * n + 1] * cam.fwd.y + centre_[3 * n + 2] * cam.fwd.z > cosHalf) vis.push_back(n);
        // Limite d'éclat : le seuil le plus faible qui tient dans le budget.
        int lev = static_cast<int>(thresholds_.size());      // = tout
        auto total = [&](int l) { uint64_t s = 0; for (uint32_t n : vis) s += l == static_cast<int>(thresholds_.size()) ? count_[n] : prefix_[n * thresholds_.size() + l]; return s; };
        while (lev > 0 && total(lev) > kBudget) --lev;
        gLimit = lev == static_cast<int>(thresholds_.size()) ? 99.0f : thresholds_[static_cast<size_t>(lev)];
        // Demandes de lecture, puis tampon refait si l'ensemble montré a changé.
        std::vector<std::pair<uint32_t, uint32_t>> want;      // tuile, étoiles voulues
        uint32_t pending = 0;
        {
            std::lock_guard<std::mutex> lk(m_);
            for (uint32_t n : vis) {
                const uint32_t need = lev == static_cast<int>(thresholds_.size()) ? count_[n] : prefix_[n * thresholds_.size() + lev];
                if (!need) continue;
                auto it = cache_.find(n);
                const uint32_t have = it == cache_.end() ? 0 : static_cast<uint32_t>(it->second.size() / kStride);
                if (have < need) {
                    ++pending;
                    if (!queued_.count(n)) { queued_.insert(n); queue_.push_back({n, need}); }
                }
                want.push_back({n, std::min(have, need)});
            }
            cv_.notify_all();
        }
        pendingTiles = pending;
        uint64_t key = want.size() * 1469598103934665603ull;
        for (const auto& [n, c] : want) key = (key ^ n) * 1099511628211ull ^ c;
        if (key == shownKey_) return;
        shownKey_ = key;
        cur_ ^= 1;
        auto* dst = static_cast<uint8_t*>(map_[cur_]);
        uint64_t at = 0;
        std::lock_guard<std::mutex> lk(m_);
        for (const auto& [n, c] : want) {
            if (!c || at + c > kBudget) continue;
            std::memcpy(dst + at * kStride, cache_[n].data(), static_cast<size_t>(c) * kStride);
            at += c;
        }
        shownStars = static_cast<uint32_t>(at);
        trimCache(vis);
    }

    void draw(VkCommandBuffer cmd, const Camera& cam, uint32_t height, float exposure) {
        if (!active || !shownStars) return;
        struct { std::array<float, 16> viewProj; float par[4]; } pc{};
        pc.viewProj = cam.viewProj();
        pc.par[0] = exposure;
        pc.par[1] = static_cast<float>(height);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout_, 0, 1, &set_[cur_], 0, nullptr);
        vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(pc), &pc);
        vkCmdDraw(cmd, shownStars, 1, 0, 0);
    }

    void destroy(const Gpu& g) {
        {
            std::lock_guard<std::mutex> lk(m_);
            stop_ = true;
        }
        cv_.notify_all();
        for (auto& t : workers_) t.join();
        workers_.clear();
        if (!ready) return;
        vkDestroyPipeline(g.dev, pipeline_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroyShaderModule(g.dev, vs_, nullptr);
        vkDestroyShaderModule(g.dev, fs_, nullptr);
        for (auto& b : buf_) destroy(g, b);
        ready = false;
    }

private:
    std::vector<uint64_t> offset_;
    std::vector<uint32_t> count_, prefix_;
    std::vector<float> thresholds_, centre_;
    std::filesystem::path root_;
    std::mutex m_;
    std::condition_variable cv_;
    std::deque<std::pair<uint32_t, uint32_t>> queue_;
    std::unordered_set<uint32_t> queued_;
    std::unordered_map<uint32_t, std::vector<uint8_t>> cache_;
    std::vector<std::thread> workers_;
    bool stop_ = false;
    Buffer buf_[2];
    void* map_[2] = {nullptr, nullptr};
    int cur_ = 0;
    uint64_t shownKey_ = 0;
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet set_[2]{};
    VkPipelineLayout layout_{};
    VkPipeline pipeline_{};
    VkShaderModule vs_{}, fs_{};

    static void destroy(const Gpu& g, Buffer& b) { ::destroy(g, b); }

    bool readIndex(const std::string& path) {
        std::ifstream f(path, std::ios::binary);
        char magic[8];
        uint32_t head[4];
        if (!f.read(magic, 8) || std::string(magic, 8) != "UNIVGTU1" || !f.read(reinterpret_cast<char*>(head), 16)) return false;
        const uint32_t n = head[1], ns = head[2];
        if (head[0] != kOrder || n != 12u * (1u << (2 * kOrder)) || ns == 0 || ns > 64) return false;
        thresholds_.resize(ns);
        f.read(reinterpret_cast<char*>(thresholds_.data()), ns * 4);
        offset_.resize(n);
        count_.resize(n);
        prefix_.resize(static_cast<size_t>(n) * ns);
        std::vector<uint32_t> row(1 + ns);
        for (uint32_t i = 0; i < n; ++i) {
            if (!f.read(reinterpret_cast<char*>(&offset_[i]), 8) || !f.read(reinterpret_cast<char*>(row.data()), row.size() * 4)) return false;
            count_[i] = row[0];
            std::copy(row.begin() + 1, row.end(), prefix_.begin() + static_cast<std::ptrdiff_t>(i) * ns);
        }
        return true;
    }

    bool readCentres(const std::string& path) {
        std::ifstream f(path, std::ios::binary);
        centre_.resize(count_.size() * 3);
        return static_cast<bool>(f.read(reinterpret_cast<char*>(centre_.data()), static_cast<std::streamsize>(centre_.size() * 4)));
    }

    // Fil de lecture : prend une tuile, lit le début utile de son paquet sur le Drive, la range dans le cache.
    void work() {
        for (;;) {
            std::pair<uint32_t, uint32_t> job;
            {
                std::unique_lock<std::mutex> lk(m_);
                cv_.wait(lk, [&] { return stop_ || !queue_.empty(); });
                if (stop_) return;
                job = queue_.front();
                queue_.pop_front();
            }
            const auto [n, need] = job;
            char name[16];
            std::snprintf(name, sizeof name, "p%03u.bin", n >> kPackShift);
            std::vector<uint8_t> data(static_cast<size_t>(need) * kStride);
            std::ifstream f(root_ / name, std::ios::binary);
            const bool ok = f && f.seekg(static_cast<std::streamoff>(offset_[n])) && f.read(reinterpret_cast<char*>(data.data()), static_cast<std::streamsize>(data.size()));
            std::lock_guard<std::mutex> lk(m_);
            queued_.erase(n);
            if (ok) cache_[n] = std::move(data);
        }
    }

    // Cache en mémoire : au-delà de 4 fois le budget, on oublie les tuiles hors du champ.
    void trimCache(const std::vector<uint32_t>& vis) {
        size_t total = 0;
        for (const auto& [n, d] : cache_) total += d.size() / kStride;
        if (total <= 4ull * kBudget) return;
        const std::unordered_set<uint32_t> keep(vis.begin(), vis.end());
        for (auto it = cache_.begin(); it != cache_.end();) it = keep.count(it->first) ? std::next(it) : cache_.erase(it);
    }

    void createPipeline(const Gpu& g, VkFormat fmt, VkBuffer colors) {
        VkDescriptorSetLayoutBinding binds[2] = {{0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_VERTEX_BIT, nullptr},
                                                 {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_VERTEX_BIT, nullptr}};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 2;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "agencement Gaia ciel");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 4};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 2;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "réserve Gaia ciel");
        const VkDescriptorSetLayout layouts[2] = {setLayout_, setLayout_};
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = 2;
        da.pSetLayouts = layouts;
        check(vkAllocateDescriptorSets(g.dev, &da, set_), "jeux Gaia ciel");
        for (int k = 0; k < 2; ++k) {
            const VkDescriptorBufferInfo infos[2] = {{buf_[k].buf, 0, VK_WHOLE_SIZE}, {colors, 0, VK_WHOLE_SIZE}};
            VkWriteDescriptorSet w[2];
            for (uint32_t i = 0; i < 2; ++i) {
                w[i] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
                w[i].dstSet = set_[k];
                w[i].dstBinding = i;
                w[i].descriptorCount = 1;
                w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
                w[i].pBufferInfo = &infos[i];
            }
            vkUpdateDescriptorSets(g.dev, 2, w, 0, nullptr);
        }
        vs_ = shader(g, "gaia_ciel.vert.spv");
        fs_ = shader(g, "etoiles.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
        const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT, 0, 80};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement Gaia ciel");
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
        att.blendEnable = VK_TRUE;      // lumière additionnée, comme les autres étoiles
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
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline_), "pipeline Gaia ciel");
    }
};

}  // namespace
