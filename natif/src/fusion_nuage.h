// Appli PC « Univers » : les étoiles du calcul de la rencontre avec Andromède, jusqu'à un million de points par image.
//
// Remplace fusion_points.h (30 000 points placés par le processeur) : ici les images du calcul (kf_NNN.bin, entiers
// 16 bits, pas de 0,025 kpc, 20 millions d'années entre deux images) sont lues telles quelles dans les fichiers ; les deux
// images qui encadrent la date montrée sont sur la carte graphique, qui trace la ligne droite entre elles
// (shaders/fusion_nuage.vert).
// Marier les données (décision de Marc, 12 novembre 2026 : « que toutes les données se marient parfaitement, avec les
// vraies équations ») : chaque point reçoit la magnitude absolue de la lumière qu'il représente (sa masse divisée par
// le rapport masse/lumière sourcé de sa galaxie) et la teinte de la couleur mesurée de sa galaxie ; il est alors dessiné
// par la même loi en 1/d² et la même exposition que les étoiles mesurées. Ces valeurs viennent de particules.bin
// (pipeline/natif/fusion_particules.py, qui cite ses sources). Sans ce fichier, ou sans rapport masse/lumière sourcé :
// éclat d'affichage fixe et blanc, comme avant, et physical vaut faux (l'écran le dit).
// Positions : repère du centre de masse du calcul ; on retranche le centre de la Voie lactée de la même image.
#pragma once
#include <algorithm>
#include <condition_variable>
#include <mutex>
#include <thread>
#include <cmath>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

#include "commun.h"
#include "orbite_galactique.h"

struct FusionCloud {
    bool ready = false, physical = false;
    uint32_t n = 0;
    long frames = 0;
    double stepGa = 0, quantumKpc = 0;
    uint32_t count = 0;      // points à dessiner à cette image (0 : rien)
    uint32_t milkyWayPoints = 0;      // les premiers points du fichier sont ceux de la Voie lactée

    bool create(const Gpu& g, const std::string& dir, VkFormat fmt) {
        std::ifstream f(dir + "/fusion_centres.bin", std::ios::binary | std::ios::ate);
        if (!f) return false;
        std::vector<char> b(static_cast<size_t>(f.tellg()));
        f.seekg(0);
        f.read(b.data(), static_cast<std::streamsize>(b.size()));
        if (b.size() < 12 * 8) return false;
        const double* h = reinterpret_cast<const double*>(b.data());
        frames = static_cast<long>(h[1]);
        stepGa = h[2];
        const int tracers = static_cast<int>(h[4]);
        quantumKpc = h[5];
        n = static_cast<uint32_t>(h[8] + h[9] + h[10] + h[11]);
        milkyWayPoints = static_cast<uint32_t>(h[8]);      // points rangés par galaxie : Voie lactée d'abord, puis M31, M33, LMC
        size_t o = 12 * 8;
        if (!n || frames < 2 || b.size() < o + (static_cast<size_t>(frames) * 12 + static_cast<size_t>(frames) * tracers * 3 + 1) * 8) return false;
        centres_.assign(reinterpret_cast<const double*>(b.data() + o), reinterpret_cast<const double*>(b.data() + o) + static_cast<size_t>(frames) * 12);
        o += (static_cast<size_t>(frames) * 12 + static_cast<size_t>(frames) * tracers * 3) * 8;
        double nf = 0;
        std::memcpy(&nf, b.data() + o, 8);
        o += 8;
        long first = 0;
        for (int k = 0; k < static_cast<int>(nf); ++k) {      // les fichiers d'images, ouverts sans être chargés en mémoire
            char name[17] = {};
            double images = 0;
            std::memcpy(name, b.data() + o, 16);
            std::memcpy(&images, b.data() + o + 16, 8);
            o += 24;
            File file;
            file.first = first;
            file.frames = static_cast<long>(images);
            file.handle = CreateFileA((dir + "/" + name).c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
            if (file.handle == INVALID_HANDLE_VALUE) break;
            LARGE_INTEGER size;
            GetFileSizeEx(file.handle, &size);
            if (static_cast<uint64_t>(size.QuadPart) < static_cast<uint64_t>(file.frames) * n * 6) {
                CloseHandle(file.handle);
                break;
            }
            file.mapping = CreateFileMappingA(file.handle, nullptr, PAGE_READONLY, 0, 0, nullptr);
            file.base = file.mapping ? static_cast<const int16_t*>(MapViewOfFile(file.mapping, FILE_MAP_READ, 0, 0, 0)) : nullptr;
            if (!file.base) break;
            files_.push_back(file);
            first += file.frames;
        }
        available_ = first;      // images réellement là (un calcul en cours n'a pas encore tout écrit)
        if (available_ < 2) return false;
        // Par point : magnitude absolue et indice de couleur B-V (particules.bin), sinon éclat fixe et blanc.
        std::vector<float> mag(n, 0.0f);
        std::vector<std::array<uint8_t, 4>> col(n, std::array<uint8_t, 4>{255, 255, 255, 255});
        std::ifstream pf(dir + "/particules.bin", std::ios::binary);
        char head[64] = {};
        if (pf.read(head, 64) && std::memcmp(head, "UNIVFPT1", 8) == 0) {
            uint32_t pn = 0, phys = 0;
            std::memcpy(&pn, head + 8, 4);
            std::memcpy(&phys, head + 12, 4);
            std::vector<float> bv(n);
            if (pn == n && pf.read(reinterpret_cast<char*>(mag.data()), n * 4) && pf.read(reinterpret_cast<char*>(bv.data()), n * 4)) {
                physical = phys != 0;
                for (uint32_t i = 0; i < n; ++i)
                    if (std::isfinite(bv[i])) col[i] = colorOfBv(bv[i]);
            }
        }
        mag_ = uploadVertices(g, mag.data(), static_cast<VkDeviceSize>(n) * 4);
        col_ = uploadVertices(g, col.data(), static_cast<VkDeviceSize>(n) * 4);
        for (int k = 0; k < kBufs; ++k) {
            pos_[k] = createBuffer(g, static_cast<VkDeviceSize>(n) * 12, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            void* p = nullptr;
            check(vkMapMemory(g.dev, pos_[k].mem, 0, static_cast<VkDeviceSize>(n) * 12, 0, &p), "images du calcul de la fusion");
            mapped_[k] = static_cast<float*>(p);
        }
        createPipeline(g, fmt);
        worker_ = std::thread([this] { work(); });
        ready = true;
        return true;
    }

    double endGa() const { return (available_ - 1) * stepGa; }

    // À appeler avant le dessin : met sur la carte les deux images qui encadrent tGa (milliards d'années depuis aujourd'hui).
    // Appelée APRÈS l'attente de la barrière de l'image précédente (fenetre.cpp) : la carte ne lit alors plus aucun tampon,
    // on peut en réécrire sans vkDeviceWaitIdle. Quatre tampons : les deux images qui encadrent la date, et de la place pour
    // qu'un fil à part prépare l'image suivante dans le sens du temps (lire une image dans les fichiers, au moment même,
    // coûtait ~25 ms au fil principal). Une image absente est écrite tout de suite, comme avant ; mêmes valeurs.
    void update(const Gpu& g, double tGa, double share) {
        (void)g;
        count = 0;
        if (!ready || share <= 0 || tGa < 0 || tGa > endGa()) return;
        const double x = tGa / stepGa;
        const long i = std::min(static_cast<long>(x), available_ - 2);
        frac_ = static_cast<float>(x - static_cast<double>(i));
        const int dir = tGa > lastT_ ? 1 : (tGa < lastT_ ? -1 : 0);
        lastT_ = tGa;
        std::unique_lock<std::mutex> l(m_);
        a_ = obtain(l, i, find(i + 1));      // sans réécrire le tampon qui tient déjà i + 1
        b_ = obtain(l, i + 1, a_);
        // Lecture d'avance : l'image suivante dans le sens du temps, dans un tampon qui ne sert pas à cette image.
        const long next = dir >= 0 ? i + 2 : i - 1;
        if (dir != 0 && next >= 0 && next < available_ && jobImage_ < 0 && find(next) < 0) {
            const int k = freeBuffer();
            if (k >= 0) {
                held_[k] = -1;
                jobImage_ = next;
                jobBuf_ = k;
                cv_.notify_all();
            }
        }
        count = n;
    }

    // Dans la passe en grande dynamique. centre : place du centre de la Voie lactée à l'écran (années-lumière) ;
    // exposure : celle des étoiles (éclat multiplié compris) ; fixedFlux : éclat d'affichage sans rapport masse/lumière.
    // first : premier point dessiné (milkyWayPoints : seulement les autres galaxies, la Voie lactée étant montrée autrement).
    void draw(VkCommandBuffer cmd, const Camera& cam, Vec3 centre, float exposure, float fixedFlux, double share, uint32_t width, uint32_t height,
              uint32_t first = 0, uint32_t last = 0) const {      // last : premier point NON dessiné (0 : jusqu'au bout)
        const uint32_t end = last ? std::min(last, count) : count;
        if (!count || first >= end || share <= 0) return;
        Push p{};
        const PushConstants base = pushConstants(cam, exposure, height);
        std::memcpy(p.viewProj, base.viewProj, sizeof(p.viewProj));
        p.origin[0] = static_cast<float>(centre.x - cam.pos.x);
        p.origin[1] = static_cast<float>(centre.y - cam.pos.y);
        p.origin[2] = static_cast<float>(centre.z - cam.pos.z);
        p.origin[3] = frac_;
        p.par[0] = exposure;
        p.par[1] = static_cast<float>(height);
        p.par[2] = physical ? 0.0f : fixedFlux;
        p.par[3] = static_cast<float>(share);
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        const VkRect2D sc{{0, 0}, {width, height}};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        const VkBuffer bufs[4] = {pos_[a_].buf, pos_[b_].buf, mag_.buf, col_.buf};
        const VkDeviceSize offs[4] = {0, 0, 0, 0};
        vkCmdBindVertexBuffers(cmd, 0, 4, bufs, offs);
        vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(p), &p);
        vkCmdDraw(cmd, end - first, 1, first, 0);
    }

    void release(const Gpu& g) {
        {
            std::lock_guard<std::mutex> l(m_);
            stop_ = true;
        }
        cv_.notify_all();
        if (worker_.joinable()) worker_.join();
        if (ready) {
            vkDestroyPipeline(g.dev, pipeline_, nullptr);
            vkDestroyPipelineLayout(g.dev, layout_, nullptr);
            vkDestroyShaderModule(g.dev, vs_, nullptr);
            vkDestroyShaderModule(g.dev, fs_, nullptr);
            for (auto& b : pos_) {
                vkUnmapMemory(g.dev, b.mem);
                destroy(g, b);
            }
            destroy(g, mag_);
            destroy(g, col_);
        }
        for (File& f : files_) {
            if (f.base) UnmapViewOfFile(f.base);
            if (f.mapping) CloseHandle(f.mapping);
            if (f.handle != INVALID_HANDLE_VALUE) CloseHandle(f.handle);
        }
        files_.clear();
        ready = false;
    }

private:
    struct File {
        HANDLE handle = INVALID_HANDLE_VALUE, mapping = nullptr;
        const int16_t* base = nullptr;
        long first = 0, frames = 0;
    };
    struct Push {
        float viewProj[16];
        float origin[4];
        float par[4];
    };
    std::vector<File> files_;
    std::vector<double> centres_;      // images x 4 galaxies x 3 (kpc, repère du centre de masse)
    long available_ = 0;
    static constexpr int kBufs = 4;
    Buffer pos_[kBufs], mag_, col_;
    float* mapped_[kBufs] = {};
    long held_[kBufs] = {-1, -1, -1, -1};      // image tenue par chaque tampon (-1 : aucune, ou en cours d'écriture)
    int a_ = 0, b_ = 1;                          // tampons des images i et i + 1 à cette image
    double lastT_ = -1.0;
    // Fil de lecture d'avance : une image à la fois (jobImage_ dans le tampon jobBuf_), sous m_.
    std::thread worker_;
    std::mutex m_;
    std::condition_variable cv_;
    long jobImage_ = -1;
    int jobBuf_ = -1;
    bool stop_ = false;

    int find(long frame) const {
        for (int k = 0; k < kBufs; ++k)
            if (held_[k] == frame) return k;
        return -1;
    }
    // Tampon libre : ni en cours d'écriture, ni tenant une image de cette image affichée.
    int freeBuffer() const {
        int best = -1;
        for (int k = 0; k < kBufs; ++k) {
            if (k == jobBuf_ || k == a_ || k == b_) continue;
            if (best < 0 || held_[k] < 0) best = k;
        }
        return best;
    }
    // Tampon tenant l'image `frame` : déjà là, en cours de lecture par le fil (on l'attend), ou écrite tout de suite.
    int obtain(std::unique_lock<std::mutex>& l, long frame, int keep) {
        cv_.wait(l, [&] { return jobImage_ != frame; });
        const int k = find(frame);
        if (k >= 0) return k;
        int best = -1;
        for (int c = 0; c < kBufs; ++c) {
            if (c == jobBuf_ || c == keep) continue;
            if (best < 0 || held_[c] < 0) best = c;
        }
        fill(best, frame);
        return best;
    }
    void work() {
        std::unique_lock<std::mutex> l(m_);
        for (;;) {
            cv_.wait(l, [this] { return stop_ || (jobImage_ >= 0 && held_[jobBuf_] != jobImage_); });
            if (stop_) return;
            const long frame = jobImage_;
            const int k = jobBuf_;
            l.unlock();
            fillInto(k, frame);
            l.lock();
            held_[k] = frame;
            jobImage_ = -1;
            jobBuf_ = -1;
            cv_.notify_all();
        }
    }
    float frac_ = 0;
    VkPipeline pipeline_{};
    VkPipelineLayout layout_{};
    VkShaderModule vs_{}, fs_{};

    // Écrit l'image `frame` dans le tampon k : kpc, par rapport au centre de la Voie lactée de cette image.
    void fill(int k, long frame) {
        held_[k] = -1;
        if (fillInto(k, frame)) held_[k] = frame;
    }
    // Écrit l'image dans le tampon k (sans toucher à held_) ; false si l'image n'est dans aucun fichier.
    bool fillInto(int k, long frame) const {
        for (const File& f : files_) {
            if (frame < f.first || frame >= f.first + f.frames) continue;
            const int16_t* src = f.base + static_cast<size_t>(frame - f.first) * n * 3;
            const double* c = &centres_[static_cast<size_t>(frame) * 12];      // galaxie 0 : la Voie lactée
            const float q = static_cast<float>(quantumKpc), cx = static_cast<float>(c[0]), cy = static_cast<float>(c[1]), cz = static_cast<float>(c[2]);
            float* dst = mapped_[k];
            for (uint32_t i = 0; i < n; ++i) {
                dst[i * 3] = src[i * 3] * q - cx;
                dst[i * 3 + 1] = src[i * 3 + 1] * q - cy;
                dst[i * 3 + 2] = src[i * 3 + 2] * q - cz;
            }
            return true;
        }
        return false;
    }

    void createPipeline(const Gpu& g, VkFormat fmt) {
        vs_ = shader(g, "fusion_nuage.vert.spv");
        fs_ = shader(g, "etoiles.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs_;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs_;
        stages[1].pName = "main";
        const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(Push)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "agencement du nuage de la fusion");
        const VkVertexInputBindingDescription binds[4] = {{0, 12, VK_VERTEX_INPUT_RATE_VERTEX}, {1, 12, VK_VERTEX_INPUT_RATE_VERTEX}, {2, 4, VK_VERTEX_INPUT_RATE_VERTEX}, {3, 4, VK_VERTEX_INPUT_RATE_VERTEX}};
        const VkVertexInputAttributeDescription attrs[4] = {{0, 0, VK_FORMAT_R32G32B32_SFLOAT, 0}, {1, 1, VK_FORMAT_R32G32B32_SFLOAT, 0}, {2, 2, VK_FORMAT_R32_SFLOAT, 0}, {3, 3, VK_FORMAT_R8G8B8A8_UNORM, 0}};
        VkPipelineVertexInputStateCreateInfo vin{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        vin.vertexBindingDescriptionCount = 4;
        vin.pVertexBindingDescriptions = binds;
        vin.vertexAttributeDescriptionCount = 4;
        vin.pVertexAttributeDescriptions = attrs;
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
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline_), "dessin du nuage de la fusion");
    }
};
