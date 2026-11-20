// Appli PC « Univers » : pose automatique contre la saturation (audit A2, 20 novembre 2026).
//
// Avant : l'éclat de toutes les étoiles est multiplié selon la distance à l'astre suivi (Sim::brightnessBoost, ×100 dès
// 300 al) ; vue de 20 000 al d'Andromède, 47 % de l'image sortait blanche (mesuré, docs/plan-corrections.md). Ici, comme
// l'œil ou un appareil photo : on mesure à chaque image l'histogramme de luminance de tous ses pixels (shaders/pose.comp,
// lu à l'image suivante sans attendre la carte), on en déduit la pose qui garde moins de 0,5 % de l'image blanche et un
// éclat moyen dans la bande visée, et la pose y glisse (adaptation en logarithme, voir suivante). La pose ne monte jamais au-dessus de 1 : ce qui était juste reste
// identique ; aucune lumière n'est ajoutée ni retirée, seule la pose change. Elle est dite à l'écran (interface_bas.h).
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>

#include "commun.h"

namespace pose_auto {
constexpr float kSeuil = 3.0f;          // luminance après pose au-delà de laquelle un point sort presque blanc (Reinhard : 0,75)
constexpr double kPartMax = 0.005;      // part saturée tolérée (les étoiles brillantes saturent toujours un peu)
// Pose réglée sur une nébuleuse autour d'une étoile : comme sur les photos de nébuleuses planétaires, les étoiles du fond
// saturent ; on en tolère 2 % de l'image (sinon elles ramenaient la pose à ×10 et l'anneau ne se voyait plus, capture du
// 20/11) [Supposition : réglage d'affichage].
constexpr double kPartMaxNebuleuse = 0.02;
constexpr double kPoseMin = 1.0e-3;     // au plus ×1/1000
// Relever la pose, seulement aux échelles des galaxies (Marc, 20/11/2026 : « Laniakea quasi aucune galaxie, c'est vide ») :
// vues de centaines de millions d'années-lumière, les galaxies des relevés sont des points très faibles (éclat réel en 1/d²).
// Comme une longue pose photo, on relève la pose tant que moins de 0,1 % de l'écran est bien visible, jusqu'à ×1000.
constexpr double kPartVisible = 0.001;
constexpr double kPoseMaxGalaxies = 1000.0;
// Éclat moyen visé à l'écran (Y/(1+Y), lumière linéaire) : au-dessus de kMoyHaute, la pose baisse ; en dessous du seuil bas
// (kMoyBasse aux échelles des étoiles, kMoyBasseGalaxies à celles des galaxies), elle monte. Entre les deux : pose de base.
// 0,003 ne relève pas un ciel étoilé ordinaire (balayage du zoom du 20/11/2026). 0,05 en haut : l'ancienne pose, qui
// gardait la mémoire de son chemin, s'arrêtait vers 0,05 au-dessus de la Voie lactée (vue à 30 000 al, mesuré) ; à 0,15
// puis 0,08, la nouvelle laissait le bulbe et le fond d'étoiles nettement plus clairs (Marc : « parfois trop de lumière »).
constexpr double kMoyHaute = 0.05, kMoyBasse = 0.003, kMoyBasseGalaxies = 0.010;
constexpr int kCases = 128;             // histogramme de shaders/pose.comp
constexpr double kLog2Min = -30.0, kPas = 0.375;

// Luminance représentative d'une case (avant la pose) : milieu de la case en logarithme ; case 0 : noir.
inline double luminanceCase(int b) { return b <= 0 ? 0.0 : std::exp2(kLog2Min + kPas * (b - 0.5)); }

struct Stats {
    double sat = 0, vis = 0, moy = 0;
};

// Ce que donnerait la pose p sur l'image mesurée : part saturée, part bien visible, éclat moyen.
// Valeur à l'écran (0 à 1, lumière linéaire) d'une luminance y après la pose, avec la courbe de l'écran (ecran.frag) :
// Reinhard y / (1 + y), fondue (photo, 0 à 1) avec l'étirement asinh (Lupton et al. 2004). La mesure suit la courbe
// réellement montrée : avant, la pose « photo » (asinh) blanchissait l'image à des luminances que la mesure croyait encore
// sombres (fond d'étoiles tout blanc autour de la nébuleuse du Soleil, capture du 20/11).
inline double ecran(double y, double photo) {
    const double nu = y / (1.0 + y);
    if (photo <= 0) return nu;
    const double ph = y > 0 ? std::min(1.0, std::asinh(y / 0.05) / std::asinh(1.0 / 0.05)) : 0.0;
    return nu + (ph - nu) * std::min(photo, 1.0);
}

// Ce que donnerait la pose p sur l'image mesurée : part saturée (écran > 0,75, soit y > 3 en Reinhard), part bien visible
// (écran > 1/3, soit y > 0,5 en Reinhard), éclat moyen à l'écran.
inline Stats statsPour(const uint32_t* h, double p, double photo = 0.0) {
    double n = 0;
    Stats s;
    for (int b = 0; b < kCases; ++b) {
        if (!h[b]) continue;
        const double d = ecran(p * luminanceCase(b), photo), c = h[b];
        n += c;
        if (d > 0.75) s.sat += c;
        if (d > 1.0 / 3.0) s.vis += c;
        s.moy += c * d;
    }
    if (n > 0) s.sat /= n, s.vis /= n, s.moy /= n;
    return s;
}

// Plus petite pose (en logarithme, de lo à hi) pour laquelle f(pose) devient vrai ; hi si jamais (f croissante).
template <class F>
double premierePose(F f, double lo, double hi) {
    if (f(lo)) return lo;
    if (!f(hi)) return hi;
    double a = std::log(lo), b = std::log(hi);
    for (int k = 0; k < 40; ++k) {
        const double m = 0.5 * (a + b);
        if (f(std::exp(m))) b = m;
        else a = m;
    }
    return std::exp(b);
}

// Pose visée pour l'image mesurée, sans mémoire du chemin : la même vue donne la même pose, qu'on y arrive en zoomant ou
// en reculant (avant, des règles par paliers gardaient la pose là où elle s'était arrêtée : le même endroit pouvait sortir
// clair ou sombre selon le geste). poseMax : plafond de la pose relevée, de 4 (étoiles) à 1 000 (galaxies) ; les seuils
// glissent avec lui au lieu de basculer.
// nebuleuse : part de la pose réglée par une nébuleuse (0 à 1) : la part saturée tolérée passe de 0,5 % à 2 %.
inline double cible(const uint32_t* h, double poseMax, double photo = 0.0, double nebuleuse = 0.0) {
    const double partMax = kPartMax + (kPartMaxNebuleuse - kPartMax) * std::clamp(nebuleuse, 0.0, 1.0);
    const double g = std::clamp(std::log(poseMax / 4.0) / std::log(10.0), 0.0, 1.0);      // 0 : étoiles (×4) ; 1 : galaxies (×40 et plus)
    const double basse = std::exp((1.0 - g) * std::log(kMoyBasse) + g * std::log(kMoyBasseGalaxies));
    const double plancher = std::exp((1.0 - g) * std::log(0.1));      // image trop claire : pas sous ×0,1 (étoiles), ×1 (galaxies)
    const Stats s1 = statsPour(h, 1.0, photo);
    double p = 1.0;
    if (s1.moy > kMoyHaute)      // trop claire : on baisse jusqu'à l'éclat visé
        p = std::max(plancher, 1.0 / premierePose([&](double q) { return statsPour(h, 1.0 / q, photo).moy <= kMoyHaute; }, 1.0, 1.0 / kPoseMin));
    else if (s1.moy < basse && s1.vis < kPartVisible)      // trop sombre : on relève jusqu'au seuil bas ou 0,1 % bien visible
        p = premierePose([&](double q) { const Stats t = statsPour(h, q, photo); return t.moy >= basse || t.vis >= kPartVisible; }, 1.0, std::max(poseMax, 1.0));
    // jamais plus de 0,5 % de l'image blanche
    if (statsPour(h, p, photo).sat > partMax) p = 1.0 / premierePose([&](double q) { return statsPour(h, 1.0 / q, photo).sat <= partMax; }, 1.0 / p, 1.0 / kPoseMin);
    return std::clamp(p, kPoseMin, kPoseMaxGalaxies);
}

// Adaptation dans le temps, en logarithme (crans d'IL), comme l'œil et les appareils photo : vers une image plus sombre
// (lumière qui arrive, saturation) demi-temps 0,1 s et au plus 16 IL par seconde ; vers une image plus claire, demi-temps
// 0,4 s et au plus 4 IL par seconde (l'œil s'adapte plus vite à la lumière qu'à l'obscurité : Pattanaik et al. 2000,
// « Time-dependent visual adaptation for fast realistic image display », SIGGRAPH ; vitesses de l'ancienne pose
// automatique : ×10 en 0,2 s vers le sombre, en 1 s vers le clair). instant : contrôles sans fenêtre.
inline double suivante(double pose, double vise, double dt, bool instant) {
    if (instant) return vise;
    const double t = std::clamp(dt, 0.0, 0.5);
    const bool sombre = vise < pose;
    const double k = 1.0 - std::exp2(-t / (sombre ? 0.1 : 0.4));
    const double pas = (std::log2(vise) - std::log2(pose)) * k, pasMax = (sombre ? 16.0 : 4.0) * t;
    return std::exp2(std::log2(pose) + std::clamp(pas, -pasMax, pasMax));
}
}  // namespace pose_auto

namespace {

class PoseAuto {
public:
    double pose = 1.0;        // facteur appliqué à l'écran (ecran.frag)
    double partSaturee = 0, partVisible = 0, moyenne = 0;   // dernière mesure, avec la pose retenue
    double vise = 1.0;        // pose visée pour la dernière image mesurée
    bool ready = false;

    void create(const Gpu& g) {
        out_ = createBuffer(g, kBytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        check(vkMapMemory(g.dev, out_.mem, 0, kBytes, 0, &mapped_), "pose automatique : accès au tampon");
        std::memset(mapped_, 0, kBytes);
        VkSamplerCreateInfo sci{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
        sci.magFilter = sci.minFilter = VK_FILTER_NEAREST;
        sci.addressModeU = sci.addressModeV = sci.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        check(vkCreateSampler(g.dev, &sci, nullptr, &sampler_), "pose automatique : échantillonneur");
        const VkDescriptorSetLayoutBinding b[2] = {{0, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr},
                                                   {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr}};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 2;
        dl.pBindings = b;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "pose automatique : agencement");
        const VkDescriptorPoolSize ps[2] = {{VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1}, {VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1}};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 1;
        dp.poolSizeCount = 2;
        dp.pPoolSizes = ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "pose automatique : réserve");
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = 1;
        da.pSetLayouts = &setLayout_;
        check(vkAllocateDescriptorSets(g.dev, &da, &set_), "pose automatique : jeu");
        const VkDescriptorBufferInfo bi{out_.buf, 0, kBytes};
        VkWriteDescriptorSet w{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
        w.dstSet = set_;
        w.dstBinding = 1;
        w.descriptorCount = 1;
        w.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        w.pBufferInfo = &bi;
        vkUpdateDescriptorSets(g.dev, 1, &w, 0, nullptr);
        cs_ = shader(g, "pose.comp.spv");
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "pose automatique : agencement du calcul");
        VkComputePipelineCreateInfo cp{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
        cp.stage = {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO};
        cp.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        cp.stage.module = cs_;
        cp.stage.pName = "main";
        cp.layout = layout_;
        check(vkCreateComputePipelines(g.dev, VK_NULL_HANDLE, 1, &cp, nullptr, &pipe_), "pose automatique : calcul");
        ready = true;
    }
    // À chaque création ou changement de taille de l'image en grande dynamique.
    void bindSource(const Gpu& g, VkImageView hdr) {
        if (!ready) return;
        const VkDescriptorImageInfo info{sampler_, hdr, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL};
        VkWriteDescriptorSet w{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
        w.dstSet = set_;
        w.dstBinding = 0;
        w.descriptorCount = 1;
        w.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
        w.pImageInfo = &info;
        vkUpdateDescriptorSets(g.dev, 1, &w, 0, nullptr);
    }
    // Après l'attente de la barrière de l'image précédente : lit son histogramme et règle la pose. actif = faux : pose 1.
    // photo : part de l'étirement « photo » dans la courbe de l'écran (0 à 1, comme ecran.frag).
    void update(double dt, bool instant, bool actif, double poseMax = 1.0, double photo = 0.0, double nebuleuse = 0.0) {
        if (!ready || !actif) {
            pose = 1.0;
            return;
        }
        uint32_t h[pose_auto::kCases];
        std::memcpy(h, mapped_, sizeof(h));
        uint64_t n = 0;
        for (uint32_t c : h) n += c;
        if (n == 0) return;      // pas encore de mesure
        vise = pose_auto::cible(h, poseMax, photo, nebuleuse);
        pose = pose_auto::suivante(pose, vise, dt, instant);
        const pose_auto::Stats s = pose_auto::statsPour(h, pose, photo);      // ce que montre l'écran avec la pose retenue
        partSaturee = s.sat;
        partVisible = s.vis;
        moyenne = s.moy;
    }
    // Dans le tampon de commandes, quand l'image en grande dynamique est en lecture (après sa passe).
    void measure(VkCommandBuffer cmd, VkExtent2D extent) const {
        if (!ready) return;
        vkCmdFillBuffer(cmd, out_.buf, 0, kBytes, 0);
        VkMemoryBarrier clear{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
        clear.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        clear.dstAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0, 1, &clear, 0, nullptr, 0, nullptr);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe_);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, layout_, 0, 1, &set_, 0, nullptr);
        vkCmdDispatch(cmd, (extent.width + 31) / 32, (extent.height + 31) / 32, 1);      // 32 x 32 pixels par équipe
        VkMemoryBarrier mb{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
        mb.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
        mb.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_HOST_BIT, 0, 1, &mb, 0, nullptr, 0, nullptr);
    }
    void release(const Gpu& g) {
        if (!ready) return;
        vkDestroyPipeline(g.dev, pipe_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyShaderModule(g.dev, cs_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroySampler(g.dev, sampler_, nullptr);
        vkUnmapMemory(g.dev, out_.mem);
        destroy(g, out_);
        ready = false;
    }

private:
    static constexpr VkDeviceSize kBytes = sizeof(uint32_t) * pose_auto::kCases;
    Buffer out_;
    void* mapped_ = nullptr;
    VkSampler sampler_{};
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkDescriptorSet set_{};
    VkPipelineLayout layout_{};
    VkPipeline pipe_{};
    VkShaderModule cs_{};
};

}  // namespace
