// Appli PC « Univers » : pose automatique contre la saturation (audit A2, 20 novembre 2026).
//
// Avant : l'éclat de toutes les étoiles est multiplié selon la distance à l'astre suivi (Sim::brightnessBoost, ×100 dès
// 300 al) ; vue de 20 000 al d'Andromède, 47 % de l'image sortait blanche (mesuré, docs/plan-corrections.md). Ici, comme
// l'œil ou un appareil photo : on mesure à chaque image la part de l'écran qui sature (shaders/pose.comp, grille de
// 128 × 72 points, lue à l'image suivante sans attendre la carte) et l'on baisse la pose tant qu'elle dépasse 0,5 % ; on la
// rend doucement quand l'image ne sature plus. La pose ne monte jamais au-dessus de 1 : ce qui était juste reste
// identique ; aucune lumière n'est ajoutée ni retirée, seule la pose change. Elle est dite à l'écran (interface_bas.h).
#pragma once
#include <algorithm>
#include <cmath>
#include <cstring>

#include "commun.h"

namespace pose_auto {
constexpr float kSeuil = 3.0f;          // luminance après pose au-delà de laquelle un point sort presque blanc (Reinhard : 0,75)
constexpr double kPartMax = 0.005;      // part saturée tolérée (les étoiles brillantes saturent toujours un peu)
constexpr double kPartBasse = 0.001;    // en dessous : on rend de la pose (écart large avec kPartMax : pas de pompage)
constexpr double kPoseMin = 1.0e-3;     // au plus ×1/1000
// Relever la pose, seulement aux échelles des galaxies (Marc, 20/11/2026 : « Laniakea quasi aucune galaxie, c'est vide ») :
// vues de centaines de millions d'années-lumière, les galaxies des relevés sont des points très faibles (éclat réel en 1/d²).
// Comme une longue pose photo, on relève la pose tant que moins de 0,1 % de l'écran est bien visible, jusqu'à ×1000.
constexpr double kPartVisible = 0.001;
constexpr double kPoseMaxGalaxies = 1000.0;

// Nouvelle pose d'après la part saturée mesurée (dt : secondes depuis l'image précédente ; instant : contrôle sans fenêtre,
// où chaque image compte comme six).
// Éclat moyen visé à l'écran (Y/(1+Y), lumière linéaire) : Marc, 20/11/2026 soir : « parfois je vois rien, trop de lumière,
// parfois pas assez ». Mesuré au balayage du zoom : de 1 à 115 sur 255 selon l'échelle. Au-dessus de kMoyHaute (≈ 75/255 à
// l'écran ; 0,15 depuis le contrôle en image), la pose baisse doucement ; en dessous de kMoyBasse (≈ 25/255) sans rien de bien visible, elle remonte (jusqu'à
// poseMax). Entre les deux, rien ne bouge : la pose ne « pompe » pas.
constexpr double kMoyHaute = 0.15, kMoyBasse = 0.010;      // 0,15 : une galaxie qui remplit l'écran garde son éclat (contrôle du 20/11 : 0,075 la ternissait ×0,09)

// poseMax : plafond de la pose relevée ; partVisible : part bien visible ; moy : éclat moyen à l'écran.
inline double suivante(double pose, double partSaturee, double partVisible, double moy, double dt, bool instant, double poseMax) {
    const double frames = instant ? 6.0 : std::clamp(dt * 60.0, 0.0, 6.0);      // vitesse réglée pour 60 images par seconde
    if (partSaturee > kPartMax) pose *= std::pow(0.8, frames);                      // ~0,2 s pour un facteur 1/10
    else if (moy > kMoyHaute) pose *= std::pow(0.97, frames);                       // image trop claire : ~1,3 s pour un facteur 1/10
    else if (pose < poseMax && moy < kMoyBasse && partVisible < kPartVisible && partSaturee < kPartBasse)
        pose = std::min(poseMax, pose * std::pow(1.04, frames));                   // trop sombre : ~1 s pour un facteur 10
    else if (pose < 1.0 && partSaturee < kPartBasse && moy < 0.6 * kMoyHaute) pose = std::min(1.0, pose * std::pow(1.02, frames));      // retour doux vers la pose de base
    else if (pose > poseMax) pose *= std::pow(0.96, frames);                        // le plafond a baissé : retour doux
    return std::clamp(pose, kPoseMin, std::max(poseMax, std::min(pose, kPoseMaxGalaxies)));
}
}  // namespace pose_auto

namespace {

class PoseAuto {
public:
    double pose = 1.0;        // facteur appliqué à l'écran (ecran.frag)
    double partSaturee = 0, partVisible = 0, moyenne = 0;   // dernière mesure
    bool ready = false;

    void create(const Gpu& g) {
        out_ = createBuffer(g, 16, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        check(vkMapMemory(g.dev, out_.mem, 0, 16, 0, &mapped_), "pose automatique : accès au tampon");
        std::memset(mapped_, 0, 16);
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
        const VkDescriptorBufferInfo bi{out_.buf, 0, 16};
        VkWriteDescriptorSet w{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
        w.dstSet = set_;
        w.dstBinding = 1;
        w.descriptorCount = 1;
        w.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        w.pBufferInfo = &bi;
        vkUpdateDescriptorSets(g.dev, 1, &w, 0, nullptr);
        cs_ = shader(g, "pose.comp.spv");
        const VkPushConstantRange pcr{VK_SHADER_STAGE_COMPUTE_BIT, 0, 16};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
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
    // Après l'attente de la barrière de l'image précédente : lit sa mesure et règle la pose. actif = faux : pose 1.
    void update(double dt, bool instant, bool actif, double poseMax = 1.0) {
        if (!ready || !actif) {
            pose = 1.0;
            return;
        }
        float m[4];
        std::memcpy(m, mapped_, sizeof(m));
        if (!(m[2] > 0)) return;      // pas encore de mesure
        partSaturee = m[0];
        partVisible = m[1];
        moyenne = m[3];
        pose = pose_auto::suivante(pose, partSaturee, partVisible, moyenne, dt, instant, poseMax);
    }
    // Dans le tampon de commandes, quand l'image en grande dynamique est en lecture (après sa passe).
    void measure(VkCommandBuffer cmd) const {
        if (!ready) return;
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe_);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, layout_, 0, 1, &set_, 0, nullptr);
        const float p[4] = {static_cast<float>(pose), pose_auto::kSeuil, 0, 0};
        vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(p), p);
        vkCmdDispatch(cmd, 1, 1, 1);
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
