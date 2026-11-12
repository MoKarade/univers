// Précalcul sur la carte graphique, sans fenêtre, avec le calcul EXACT des orbites de l'appli (shaders/orbites_pas.comp) :
//
//   precalcul_clones controle <etoiles.bin>
//       Contrôle du shader contre la bibliothèque en double précision (phys::galaxie::Orbites), sur 20 000 vraies étoiles
//       tirées comme dans essai_epicycles, à ±10, ±100 et ±500 Ma. Critère (plan-precalcul.md) : écart médian < 1 pc,
//       99ᵉ centile < 10 pc. Code de sortie 0 si le critère tient.
//
//   precalcul_clones ecarts <etats.f32> <K> <sortie.f32>
//       etats.f32 : n × K clones de 8 flottants (position galactocentrique kpc, sous-pas, vitesse km/s, 0), les K clones
//       d'une étoile à la suite (pipeline/natif/clones_etoiles.py). Pour chaque étoile, écart quadratique moyen des
//       positions de ses clones autour de leur moyenne (kpc), à 11 dates vers le futur puis 11 vers le passé :
//       10, 30, 100, 300 milliers d'années (un seul pas depuis aujourd'hui, la trajectoire est alors presque droite)
//       et 1, 3, 10, 30, 100, 300, 1 000 millions d'années (pas de 1 Ma, comme l'appli). Sortie : n × 22 flottants.
#include "commun.h"

#include <random>
#include <thread>

#include "galaxie_orbites.h"
#include "orbite_galactique.h"

namespace {

struct StepPush { float t0, dt; uint32_t first, count; };

struct Calcul {
    Gpu g;
    Buffer state, host;
    uint32_t count = 0;
    VkDescriptorSetLayout setLayout{};
    VkDescriptorPool pool{};
    VkDescriptorSet set{};
    VkPipelineLayout layout{};
    VkPipeline pipe{};
    VkShaderModule cs{};

    explicit Calcul(uint32_t n) : g(createGpu(false)), count(n) {
        const VkDeviceSize bytes = static_cast<VkDeviceSize>(n) * 32;
        state = createBuffer(g, bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        host = createBuffer(g, bytes, VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        VkDescriptorSetLayoutBinding binds[2];
        for (uint32_t i = 0; i < 2; ++i) binds[i] = {i, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 2;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout), "agencement");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 2};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 1;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool), "réserve");
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool;
        da.descriptorSetCount = 1;
        da.pSetLayouts = &setLayout;
        check(vkAllocateDescriptorSets(g.dev, &da, &set), "jeu");
        const VkDescriptorBufferInfo info{state.buf, 0, VK_WHOLE_SIZE};      // calcul en place, comme gaia_orbites.h
        VkWriteDescriptorSet w[2];
        for (uint32_t i = 0; i < 2; ++i) {
            w[i] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
            w[i].dstSet = set;
            w[i].dstBinding = i;
            w[i].descriptorCount = 1;
            w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            w[i].pBufferInfo = &info;
        }
        vkUpdateDescriptorSets(g.dev, 2, w, 0, nullptr);
        cs = shader(g, "orbites_pas.comp.spv");
        const VkPushConstantRange pcr{VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(StepPush)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout), "agencement du calcul");
        VkComputePipelineCreateInfo cp{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
        cp.stage = {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO};
        cp.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        cp.stage.module = cs;
        cp.stage.pName = "main";
        cp.layout = layout;
        check(vkCreateComputePipelines(g.dev, VK_NULL_HANDLE, 1, &cp, nullptr, &pipe), "calcul");
    }
    void envoyer(const std::vector<float>& s) {
        const VkDeviceSize bytes = static_cast<VkDeviceSize>(count) * 32;
        void* p = nullptr;
        check(vkMapMemory(g.dev, host.mem, 0, bytes, 0, &p), "envoi");
        std::memcpy(p, s.data(), bytes);
        vkUnmapMemory(g.dev, host.mem);
        VkCommandBuffer c = beginOnce(g);
        const VkBufferCopy r{0, 0, bytes};
        vkCmdCopyBuffer(c, host.buf, state.buf, 1, &r);
        endOnce(g, c);
    }
    void lire(std::vector<float>& s) {
        const VkDeviceSize bytes = static_cast<VkDeviceSize>(count) * 32;
        VkCommandBuffer c = beginOnce(g);
        const VkBufferCopy r{0, 0, bytes};
        vkCmdCopyBuffer(c, state.buf, host.buf, 1, &r);
        endOnce(g, c);
        s.resize(static_cast<size_t>(count) * 8);
        void* p = nullptr;
        check(vkMapMemory(g.dev, host.mem, 0, bytes, 0, &p), "relecture");
        std::memcpy(s.data(), p, bytes);
        vkUnmapMemory(g.dev, host.mem);
    }
    // n pas de dt (Ga) à partir de t0 (Ga), envoyés par paquets de 50 (une soumission par paquet).
    void pas(double t0, double dt, long n) {
        for (long k = 0; k < n;) {
            VkCommandBuffer c = beginOnce(g);
            vkCmdBindPipeline(c, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
            vkCmdBindDescriptorSets(c, VK_PIPELINE_BIND_POINT_COMPUTE, layout, 0, 1, &set, 0, nullptr);
            for (int b = 0; b < 50 && k < n; ++b, ++k) {
                const StepPush p{static_cast<float>(t0 + k * dt), static_cast<float>(dt), 0, count};
                vkCmdPushConstants(c, layout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(p), &p);
                vkCmdDispatch(c, (count + 255) / 256, 1, 1);
                VkMemoryBarrier mb{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
                mb.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
                mb.dstAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
                vkCmdPipelineBarrier(c, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0, 1, &mb, 0, nullptr, 0, nullptr);
            }
            endOnce(g, c);
        }
    }
};

float sousPas(const phys::galaxie::Potentiel& P, const double x[3], const double v[3]) {      // règle de Orbites::sousPas
    const double E = P.energie(x[0], x[1], x[2], v[0], v[1], v[2]);
    const double L2 = std::pow(x[1] * v[2] - x[2] * v[1], 2) + std::pow(x[2] * v[0] - x[0] * v[2], 2) + std::pow(x[0] * v[1] - x[1] * v[0], 2);
    auto f = [&](double r) { return 2 * (E - P.energie(r, 0, 0, 0, 0, 0)) * r * r - L2; };
    double a = 1e-3, b = std::max(std::sqrt(x[0] * x[0] + x[1] * x[1] + x[2] * x[2]), 2e-3);
    if (f(a) < 0) {
        for (int it = 0; it < 40; ++it) { const double m = 0.5 * (a + b); if (f(m) < 0) a = m; else b = m; }
    } else b = a;
    return b < 0.7 ? 32.0f : b < 2 ? 8.0f : b < 4 ? 2.0f : 1.0f;
}

int controle(const char* chemin) {
    std::ifstream f(chemin, std::ios::binary);
    char tete[64];
    if (!f.read(tete, 64) || std::string(tete, 8) != "UNIVSTR1") fail(std::string("lecture de ") + chemin);
    int64_t n = 0;
    std::memcpy(&n, tete + 8, 8);
    auto col = [&](int k) {
        std::vector<float> c(n);
        f.seekg(64 + k * ((n * 4 + 63) / 64 * 64));
        f.read(reinterpret_cast<char*>(c.data()), n * 4);
        return c;
    };
    const auto X = col(0), Y = col(1), Z = col(2), VX = col(5), VY = col(6), VZ = col(7);
    std::vector<size_t> idx;
    for (int64_t k = 0; k < n; ++k) if (VX[k] != 0 || VY[k] != 0 || VZ[k] != 0) idx.push_back(k);
    std::mt19937_64 h(20261112);
    std::shuffle(idx.begin(), idx.end(), h);
    idx.resize(std::min<size_t>(20000, idx.size()));
    namespace G = phys::galaxie;
    const phys::Vec3 s = G::soleilPos(), sv = G::soleilVit();
    std::vector<phys::Vec3> P, V;
    std::vector<float> etats;
    const G::Potentiel pot;
    for (size_t k : idx) {
        const phys::Vec3 pg = orbite::versGalactique({X[k], Y[k], Z[k]}), vg = orbite::versGalactique({VX[k], VY[k], VZ[k]});
        const double x[3] = {pg.x / orbite::kKpcLy + s.x, pg.y / orbite::kKpcLy + s.y, pg.z / orbite::kKpcLy + s.z}, v[3] = {vg.x + sv.x, vg.y + sv.y, vg.z + sv.z};
        // Départ commun : les valeurs float32 envoyées à la carte, relues en double pour la référence.
        float e[8] = {float(x[0]), float(x[1]), float(x[2]), sousPas(pot, x, v), float(v[0]), float(v[1]), float(v[2]), 0};
        etats.insert(etats.end(), e, e + 8);
        P.push_back({e[0], e[1], e[2]});
        V.push_back({e[4], e[5], e[6]});
    }
    Calcul c(static_cast<uint32_t>(P.size()));
    bool ok = true;
    for (const double sens : {1.0, -1.0}) {
        c.envoyer(etats);
        G::Orbites ref(P, V);
        long fait = 0;
        for (const long cible : {10L, 100L, 500L}) {
            const auto t0 = std::chrono::steady_clock::now();
            c.pas(sens * fait * 1e-3, sens * 1e-3, cible - fait);
            std::vector<float> out;
            c.lire(out);
            const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
            ref.avance(sens * cible * 1e-3);
            fait = cible;
            std::vector<double> d(P.size());
            for (size_t k = 0; k < P.size(); ++k) {
                const phys::Vec3 r = ref.position(k);
                d[k] = 1000 * std::hypot(out[k * 8] - r.x, out[k * 8 + 1] - r.y, out[k * 8 + 2] - r.z);      // pc
            }
            std::sort(d.begin(), d.end());
            const double med = d[d.size() / 2], q99 = d[d.size() * 99 / 100];
            const bool bon = med < 1 && q99 < 10;
            ok &= bon;
            std::printf("%s  %+5ld Ma : écart carte - double, médiane %.3f pc, 99 %% %.3f pc, max %.3f pc (%.0f ms)\n", bon ? "PASSE" : "ECHEC", long(sens) * cible, med, q99, d.back(), ms);
        }
    }
    std::printf(ok ? "PASSE\n" : "ECHEC\n");
    return ok ? 0 : 1;
}

int ecarts(const char* entree, int K, const char* sortie) {
    std::ifstream f(entree, std::ios::binary | std::ios::ate);
    if (!f) fail(std::string("lecture de ") + entree);
    const size_t octets = static_cast<size_t>(f.tellg());
    const size_t nc = octets / 32, n = nc / K;
    std::vector<float> init(nc * 8);
    f.seekg(0);
    f.read(reinterpret_cast<char*>(init.data()), static_cast<std::streamsize>(octets));
    Calcul c(static_cast<uint32_t>(nc));
    std::vector<float> res(n * 22, 0.0f), cur;
    const unsigned nt = std::max(1u, std::min(32u, std::thread::hardware_concurrency()));
    auto mesurer = [&](int col) {
        c.lire(cur);
        std::vector<std::thread> th;
        for (unsigned t = 0; t < nt; ++t)
            th.emplace_back([&, t] {
                for (size_t i = n * t / nt; i < n * (t + 1) / nt; ++i) {
                    double m[3] = {0, 0, 0}, s2 = 0;
                    for (int k = 0; k < K; ++k) for (int a = 0; a < 3; ++a) m[a] += cur[(i * K + k) * 8 + a];
                    for (int a = 0; a < 3; ++a) m[a] /= K;
                    for (int k = 0; k < K; ++k) for (int a = 0; a < 3; ++a) { const double d = cur[(i * K + k) * 8 + a] - m[a]; s2 += d * d; }
                    res[i * 22 + col] = static_cast<float>(std::sqrt(s2 / K));
                }
            });
        for (auto& x : th) x.join();
    };
    const double courts[4] = {1e-5, 3e-5, 1e-4, 3e-4};      // Ga
    const long longs[7] = {1, 3, 10, 30, 100, 300, 1000};     // Ma
    const auto t0 = std::chrono::steady_clock::now();
    for (int sens = 0; sens < 2; ++sens) {
        const double sg = sens ? -1.0 : 1.0;
        for (int j = 0; j < 4; ++j) {
            c.envoyer(init);
            c.pas(0, sg * courts[j], 1);
            mesurer(sens * 11 + j);
        }
        c.envoyer(init);
        long fait = 0;
        for (int j = 0; j < 7; ++j) {
            c.pas(sg * fait * 1e-3, sg * 1e-3, longs[j] - fait);
            fait = longs[j];
            mesurer(sens * 11 + 4 + j);
        }
    }
    std::ofstream o(sortie, std::ios::binary);
    o.write(reinterpret_cast<const char*>(res.data()), static_cast<std::streamsize>(res.size() * 4));
    std::printf("%zu étoiles × %d clones : %.1f s\n", n, K, std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc >= 3 && std::string(argv[1]) == "controle") return controle(argv[2]);
    if (argc >= 5 && std::string(argv[1]) == "ecarts") return ecarts(argv[2], std::atoi(argv[3]), argv[4]);
    std::printf("usage : precalcul_clones controle <etoiles.bin> | ecarts <etats.f32> <K> <sortie.f32>\n");
    return 2;
}
