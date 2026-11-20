// Appli PC « Univers » : l'orbite EXACTE de chaque étoile autour du centre de la Galaxie, calculée sur la carte graphique.
//
// Pourquoi : les épicycles (orbite_galactique.h) ne tiennent qu'une dizaine de millions d'années (mesuré par le fil
// physique sur 20 000 vraies étoiles : 1,1 kpc d'écart médian à 100 millions d'années). Marc veut le vrai placement.
// Comment : shaders/orbites_pas.comp porte tel quel le calcul de la bibliothèque de physique (Potentiel::acc avec la barre,
// saut de grenouille, sous-pas par étoile), pas de 1 million d'années. La carte garde deux états : celui du pas d'avant
// la date montrée et celui du pas d'après ; shaders/etoiles_orbite.vert trace une courbe de Hermite entre les deux et la
// raccorde sans seuil à la ligne droite mesurée, exacte près d'aujourd'hui.
// Quand la date saute loin, la carte rattrape `budget` pas par image ; lagSteps dit combien il en reste (l'interface
// l'affiche). Remonter le temps : les mêmes pas, à l'envers (le schéma est réversible).
// Les étoiles sont celles de StarRenderer (mêmes tampons de sommets), le Soleil en dernier : son état sert d'origine.
#pragma once
#include <cmath>
#include <thread>
#include <vector>

#include "commun.h"
#include "galaxie_orbites.h"
#include "orbite_galactique.h"

struct OrbitGpu {
    static constexpr double kStepYears = 1.0e6;
    bool ready = false;
    uint32_t count = 0;
    long stepLo = 0;                 // l'état `lo` est au pas stepLo, l'autre au pas stepLo + 1
    int lo = 0;
    long lagSteps = 0;               // pas restant à calculer pour rejoindre la date montrée
    Buffer state[2], init;
    std::vector<float> initial;      // copie des états de départ (contrôle)
    VkDescriptorSetLayout setLayout{};
    VkDescriptorPool pool{};
    VkDescriptorSet sets[2]{};       // sets[k] : tampon 0 = state[k], tampon 1 = state[1 - k]
    VkPipelineLayout computeLayout{}, drawLayout{};
    VkPipeline computePipe{}, drawPipe{};
    VkShaderModule cs{}, vs{}, fs{};
    struct StepPush { float t0, dt; uint32_t first, count; };

    // Nombre de sous-pas d'une étoile : la même règle que phys::galaxie::Orbites::sousPas (péricentre estimé).
    static float subSteps(const phys::galaxie::Potentiel& P, const double x[3], const double v[3]) {
        const double E = P.energie(x[0], x[1], x[2], v[0], v[1], v[2]);
        const double L2 = std::pow(x[1] * v[2] - x[2] * v[1], 2) + std::pow(x[2] * v[0] - x[0] * v[2], 2) + std::pow(x[0] * v[1] - x[1] * v[0], 2);
        auto f = [&](double r) { return 2 * (E - P.energie(r, 0, 0, 0, 0, 0)) * r * r - L2; };
        double a = 1e-3, b = std::max(std::sqrt(x[0] * x[0] + x[1] * x[1] + x[2] * x[2]), 2e-3);
        if (f(a) < 0) {
            for (int it = 0; it < 40; ++it) {
                const double m = 0.5 * (a + b);
                if (f(m) < 0) a = m;
                else b = m;
            }
        } else {
            b = a;
        }
        return b < 0.7 ? 32.0f : b < 2 ? 8.0f : b < 4 ? 2.0f : 1.0f;
    }

    // États de départ (8 flottants par étoile : position kpc + sous-pas, vitesse km/s + 0) des n premières étoiles du
    // fichier, puis du Soleil. Positions et vitesses mesurées, passées dans le repère galactocentrique.
    static std::vector<float> initialStates(const Stars& stars, size_t nCat) {
        std::vector<float> out((nCat + 1) * 8, 0.0f);
        const phys::galaxie::Potentiel P;
        const phys::Vec3 s = phys::galaxie::soleilPos(), sv = phys::galaxie::soleilVit();
        auto fill = [&](size_t i, Vec3 pos, Vec3 vel) {
            const phys::Vec3 pg = orbite::versGalactique(pos), vg = orbite::versGalactique(vel);
            const double x[3] = {pg.x / orbite::kKpcLy + s.x, pg.y / orbite::kKpcLy + s.y, pg.z / orbite::kKpcLy + s.z}, v[3] = {vg.x + sv.x, vg.y + sv.y, vg.z + sv.z};
            float* o = &out[i * 8];
            for (int a = 0; a < 3; ++a) {
                o[a] = static_cast<float>(x[a]);
                o[4 + a] = static_cast<float>(v[a]);
            }
            o[3] = subSteps(P, x, v);
        };
        const unsigned nt = std::max(1u, std::min(32u, std::thread::hardware_concurrency()));
        std::vector<std::thread> th;
        for (unsigned t = 0; t < nt; ++t)
            th.emplace_back([&, t] {
                for (size_t i = nCat * t / nt; i < nCat * (t + 1) / nt; ++i)
                    fill(i, {stars.x()[i], stars.y()[i], stars.z()[i]}, {stars.vel(0)[i], stars.vel(1)[i], stars.vel(2)[i]});
            });
        for (auto& x : th) x.join();
        fill(nCat, {0, 0, 0}, {0, 0, 0});      // le Soleil
        return out;
    }

    void create(const Gpu& g, const Stars& stars, const StarRenderer& sr, VkFormat fmt) {
        count = sr.count;
        initial = initialStates(stars, count - 1);
        const VkDeviceSize bytes = static_cast<VkDeviceSize>(count) * 32;
        const VkBufferUsageFlags use = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT;
        for (auto& b : state) b = createBuffer(g, bytes, use, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        init = createBuffer(g, bytes, VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        {
            Buffer staging = createBuffer(g, bytes, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            void* p = nullptr;
            check(vkMapMemory(g.dev, staging.mem, 0, bytes, 0, &p), "états de départ");
            std::memcpy(p, initial.data(), bytes);
            vkUnmapMemory(g.dev, staging.mem);
            VkCommandBuffer cmd = beginOnce(g);
            const VkBufferCopy region{0, 0, bytes};
            vkCmdCopyBuffer(cmd, staging.buf, init.buf, 1, &region);
            endOnce(g, cmd);
            destroy(g, staging);
        }
        // Agencement commun au calcul et au dessin : deux tampons d'états.
        VkDescriptorSetLayoutBinding binds[2];
        for (uint32_t i = 0; i < 2; ++i) binds[i] = {i, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_COMPUTE_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 2;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout), "agencement des orbites");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 4};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 2;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool), "réserve des orbites");
        for (int k = 0; k < 2; ++k) {
            VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
            da.descriptorPool = pool;
            da.descriptorSetCount = 1;
            da.pSetLayouts = &setLayout;
            check(vkAllocateDescriptorSets(g.dev, &da, &sets[k]), "jeu des orbites");
            const VkDescriptorBufferInfo infos[2] = {{state[k].buf, 0, VK_WHOLE_SIZE}, {state[1 - k].buf, 0, VK_WHOLE_SIZE}};
            VkWriteDescriptorSet w[2];
            for (uint32_t i = 0; i < 2; ++i) {
                w[i] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
                w[i].dstSet = sets[k];
                w[i].dstBinding = i;
                w[i].descriptorCount = 1;
                w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
                w[i].pBufferInfo = &infos[i];
            }
            vkUpdateDescriptorSets(g.dev, 2, w, 0, nullptr);
        }
        // Calcul.
        cs = shader(g, "orbites_pas.comp.spv");
        const VkPushConstantRange cpr{VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(StepPush)};
        VkPipelineLayoutCreateInfo cl{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        cl.setLayoutCount = 1;
        cl.pSetLayouts = &setLayout;
        cl.pushConstantRangeCount = 1;
        cl.pPushConstantRanges = &cpr;
        check(vkCreatePipelineLayout(g.dev, &cl, nullptr, &computeLayout), "agencement du calcul des orbites");
        VkComputePipelineCreateInfo cp{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
        cp.stage = {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO};
        cp.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        cp.stage.module = cs;
        cp.stage.pName = "main";
        cp.layout = computeLayout;
        check(vkCreateComputePipelines(g.dev, VK_NULL_HANDLE, 1, &cp, nullptr, &computePipe), "calcul des orbites");
        createDrawPipeline(g, fmt);
        // Départ : état 0 au pas 0, état 1 au pas 1.
        VkCommandBuffer cmd = beginOnce(g);
        reset(cmd);
        endOnce(g, cmd);
        ready = true;
    }

    // Avance le calcul vers la date montrée, de `budget` pas au plus. À appeler hors d'une passe de dessin.
    void advance(VkCommandBuffer cmd, double years, long budget) {
        if (!ready) return;
        const long target = static_cast<long>(std::floor(years / kStepYears));
        if (target != stepLo && std::labs(target) + 1 < std::labs(target - stepLo)) reset(cmd);      // plus court en repartant d'aujourd'hui
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, computePipe);
        while (stepLo != target && budget-- > 0) {
            if (target > stepLo) {      // (n, n+1) -> (n+1, n+2) : le pas n+2 s'écrit sur le tampon du pas n
                step(cmd, 1 - lo, static_cast<double>(stepLo + 1), +1.0);
                lo = 1 - lo;
                ++stepLo;
            } else {                    // (n, n+1) -> (n-1, n) : le pas n-1 s'écrit sur le tampon du pas n+1
                step(cmd, lo, static_cast<double>(stepLo), -1.0);
                lo = 1 - lo;
                --stepLo;
            }
        }
        lagSteps = std::labs(target - stepLo);
    }

    // Part du pas écoulée à la date montrée (0 à 1) ; pendant un rattrapage, l'état calculé le plus proche.
    float fraction(double years) const { return static_cast<float>(std::clamp(years / kStepYears - static_cast<double>(stepLo), 0.0, 1.0)); }

    // Dans la passe en grande dynamique. pc : constantes des étoiles (pushConstants) ; weight : poids de l'orbite dans le
    // raccord avec la ligne droite mesurée (orbite::poidsOrbite).
    // focus : étoile suivie par la caméra (rang dans le catalogue, -1 : aucune) et sa place relative à la caméra, calculée
    // en double précision par le processeur (Sim::position). Les orbites de la carte sont en simple précision et en kpc
    // galactocentriques : à 8 kpc du centre, un arrondi vaut environ 100 UA. Vue de quelques UA, l'étoile suivie sautait
    // à chaque image ou sortait de l'écran (Marc, 20/11/2026 : « elle gigote sur place ») ; elle est donc posée là où
    // la caméra la vise, exactement (etoiles_orbite.vert).
    struct Push {
        PushConstants pc;
        float focus[4];      // xyz : place relative à la caméra (années-lumière) ; w : rang (bits d'un entier)
    };
    void draw(VkCommandBuffer cmd, const StarRenderer& sr, PushConstants pc0, uint32_t width, uint32_t height, double years, double weight,
              int focusStar = -1, Vec3 focusRel = {0, 0, 0}) const {
        if (!ready) return;
        Push push{pc0, {static_cast<float>(focusRel.x), static_cast<float>(focusRel.y), static_cast<float>(focusRel.z), 0.0f}};
        std::memcpy(&push.focus[3], &focusStar, 4);
        PushConstants& pc = push.pc;
        pc.par[3] = fraction(years);
        pc.camHi[3] = static_cast<float>(weight);
        pc.camLo[3] = static_cast<float>(count - 1);      // rang du Soleil
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        const VkRect2D sc{{0, 0}, {width, height}};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, drawPipe);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, drawLayout, 0, 1, &sets[lo], 0, nullptr);
        VkBuffer bufs[StarRenderer::kCols];
        VkDeviceSize offs[StarRenderer::kCols];
        for (int i = 0; i < StarRenderer::kCols; ++i) {
            bufs[i] = sr.vb[i].buf;
            offs[i] = 0;
        }
        vkCmdBindVertexBuffers(cmd, 0, StarRenderer::kCols, bufs, offs);
        vkCmdPushConstants(cmd, drawLayout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
        vkCmdDraw(cmd, count, 1, 0, 0);
    }

    // Contrôle : relit les n premiers états du pas stepLo (8 flottants par étoile).
    std::vector<float> readBack(const Gpu& g, uint32_t n) const {
        n = std::min(n, count);
        const VkDeviceSize bytes = static_cast<VkDeviceSize>(n) * 32;
        Buffer host = createBuffer(g, bytes, VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        VkCommandBuffer cmd = beginOnce(g);
        const VkBufferCopy region{0, 0, bytes};
        vkCmdCopyBuffer(cmd, state[lo].buf, host.buf, 1, &region);
        endOnce(g, cmd);
        std::vector<float> out(static_cast<size_t>(n) * 8);
        void* p = nullptr;
        check(vkMapMemory(g.dev, host.mem, 0, bytes, 0, &p), "relecture des orbites");
        std::memcpy(out.data(), p, bytes);
        vkUnmapMemory(g.dev, host.mem);
        destroy(g, host);
        return out;
    }

    void release(const Gpu& g) {
        if (!ready) return;
        vkDestroyPipeline(g.dev, computePipe, nullptr);
        vkDestroyPipeline(g.dev, drawPipe, nullptr);
        vkDestroyPipelineLayout(g.dev, computeLayout, nullptr);
        vkDestroyPipelineLayout(g.dev, drawLayout, nullptr);
        vkDestroyDescriptorPool(g.dev, pool, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout, nullptr);
        vkDestroyShaderModule(g.dev, cs, nullptr);
        vkDestroyShaderModule(g.dev, vs, nullptr);
        vkDestroyShaderModule(g.dev, fs, nullptr);
        for (auto& b : state) destroy(g, b);
        destroy(g, init);
        ready = false;
    }

private:
    static void barrier(VkCommandBuffer cmd, VkAccessFlags from, VkPipelineStageFlags stageFrom) {
        VkMemoryBarrier b{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
        b.srcAccessMask = from;
        b.dstAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT | VK_ACCESS_TRANSFER_READ_BIT | VK_ACCESS_TRANSFER_WRITE_BIT;
        vkCmdPipelineBarrier(cmd, stageFrom, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT | VK_PIPELINE_STAGE_VERTEX_SHADER_BIT | VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 1, &b, 0, nullptr, 0,
                             nullptr);
    }
    // Un pas pour toutes les étoiles : lit state[from], écrit state[1 - from]. tMa : temps au début du pas ; sens : +1 ou -1.
    void step(VkCommandBuffer cmd, int from, double tMa, double sens) const {
        const StepPush p{static_cast<float>(tMa * 1.0e-3), static_cast<float>(sens * 1.0e-3), 0, count};
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, computeLayout, 0, 1, &sets[from], 0, nullptr);
        vkCmdPushConstants(cmd, computeLayout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(p), &p);
        vkCmdDispatch(cmd, (count + 255) / 256, 1, 1);
        barrier(cmd, VK_ACCESS_SHADER_WRITE_BIT, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT);
    }
    // Repart d'aujourd'hui : état 0 au pas 0 (copie des états de départ), état 1 au pas 1.
    void reset(VkCommandBuffer cmd) {
        const VkBufferCopy region{0, 0, static_cast<VkDeviceSize>(count) * 32};
        vkCmdCopyBuffer(cmd, init.buf, state[0].buf, 1, &region);
        barrier(cmd, VK_ACCESS_TRANSFER_WRITE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, computePipe);
        lo = 0;
        stepLo = 0;
        step(cmd, 0, 0.0, +1.0);
    }

    void createDrawPipeline(const Gpu& g, VkFormat fmt) {
        vs = shader(g, "etoiles_orbite.vert.spv");
        fs = shader(g, "etoiles.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs;
        stages[1].pName = "main";
        const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(Push)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &drawLayout), "agencement du dessin des orbites");
        constexpr int kCols = StarRenderer::kCols;
        VkVertexInputBindingDescription binds[kCols];
        VkVertexInputAttributeDescription attrs[kCols];
        for (uint32_t i = 0; i < static_cast<uint32_t>(kCols); ++i) {
            binds[i] = {i, 4, VK_VERTEX_INPUT_RATE_VERTEX};
            attrs[i] = {i, i, i == 4 ? VK_FORMAT_R8G8B8A8_UNORM : VK_FORMAT_R32_SFLOAT, 0};
        }
        VkPipelineVertexInputStateCreateInfo vin{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        vin.vertexBindingDescriptionCount = kCols;
        vin.pVertexBindingDescriptions = binds;
        vin.vertexAttributeDescriptionCount = kCols;
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
        pci.layout = drawLayout;
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &drawPipe), "dessin des orbites");
    }
};
