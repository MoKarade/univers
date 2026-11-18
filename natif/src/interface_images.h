// Appli PC « Univers » : images montrées dans le panneau d'information (cartes de surface des astres).
//
// Les images sont celles déjà installées pour dessiner les astres (dossier textures, Solar System Scope, CC BY 4.0) :
// aucune image n'est ajoutée ni inventée. Elles sont décodées dans un fil à part, réduites à 768 pixels de large au plus
// (moyenne des pixels regroupés), puis envoyées à la carte graphique une par image affichée, comme les cartes des sphères.
// Une image absente ou illisible n'est simplement pas montrée.
#pragma once
#include <imgui.h>
#include <imgui_impl_vulkan.h>
#include <stb_image.h>

#include <atomic>
#include <cstring>
#include <map>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "commun.h"

namespace {

class UiImages {
public:
    struct Entry {
        VkImage image{};
        VkDeviceMemory mem{};
        VkImageView view{};
        VkDescriptorSet set{};
        int w = 0, h = 0;
        bool ready = false;
    };

    UiImages() = default;
    UiImages(const UiImages&) = delete;
    UiImages& operator=(const UiImages&) = delete;
    // Sortie anticipée (erreur avant release) : le fil de décodage est arrêté proprement.
    ~UiImages() {
        stop_ = true;
        if (loader_.joinable()) loader_.join();
        for (Decoded& d : decoded_) d.px.clear();
    }

    // Lance le décodage des fichiers demandés (noms relatifs au dossier `dir`).
    void start(const std::string& dir, const std::vector<std::string>& files) {
        loader_ = std::thread([this, dir, files]() {
            for (const std::string& f : files) {
                if (stop_) return;
                int w = 0, h = 0, comp = 0;
                unsigned char* px = stbi_load((dir + "/" + f).c_str(), &w, &h, &comp, 4);
                if (!px) continue;
                Decoded d = shrink(f, px, w, h);
                stbi_image_free(px);
                std::lock_guard<std::mutex> lock(mutex_);
                decoded_.push_back(std::move(d));
            }
        });
    }

    // Entre deux images : envoie au plus une image décodée à la carte graphique.
    void uploadPending(const Gpu& g) {
        if (!sampler_) createSampler(g);
        Decoded d;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (decoded_.empty()) return;
            d = std::move(decoded_.back());
            decoded_.pop_back();
        }
        Entry& e = entries_[d.name];
        e.w = d.w;
        e.h = d.h;
        upload(g, e, d);
        e.set = ImGui_ImplVulkan_AddTexture(sampler_, e.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
        e.ready = e.set != VK_NULL_HANDLE;
    }

    // Image prête, ou nullptr.
    const Entry* get(const std::string& name) const {
        const auto it = entries_.find(name);
        return it != entries_.end() && it->second.ready ? &it->second : nullptr;
    }

    void release(const Gpu& g) {
        stop_ = true;
        if (loader_.joinable()) loader_.join();
        for (auto& [name, e] : entries_) {
            if (e.set) ImGui_ImplVulkan_RemoveTexture(e.set);
            if (e.view) vkDestroyImageView(g.dev, e.view, nullptr);
            if (e.image) vkDestroyImage(g.dev, e.image, nullptr);
            if (e.mem) vkFreeMemory(g.dev, e.mem, nullptr);
        }
        entries_.clear();
        if (sampler_) vkDestroySampler(g.dev, sampler_, nullptr);
        sampler_ = VK_NULL_HANDLE;
    }

private:
    static constexpr int kMaxWidth = 768;
    struct Decoded {
        std::string name;
        int w = 0, h = 0;
        std::vector<unsigned char> px;
    };

    // Réduction par moyenne de blocs entiers (facteur entier) : aucune couleur n'est inventée.
    static Decoded shrink(const std::string& name, const unsigned char* src, int w, int h) {
        Decoded d;
        d.name = name;
        const int f = std::max(1, (w + kMaxWidth - 1) / kMaxWidth);
        d.w = std::max(1, w / f);
        d.h = std::max(1, h / f);
        d.px.assign(static_cast<size_t>(d.w) * d.h * 4, 0);
        for (int y = 0; y < d.h; ++y)
            for (int x = 0; x < d.w; ++x) {
                unsigned sum[4] = {0, 0, 0, 0};
                for (int j = 0; j < f; ++j)
                    for (int i = 0; i < f; ++i) {
                        const unsigned char* p = src + (static_cast<size_t>(y * f + j) * w + (x * f + i)) * 4;
                        for (int c = 0; c < 4; ++c) sum[c] += p[c];
                    }
                unsigned char* o = d.px.data() + (static_cast<size_t>(y) * d.w + x) * 4;
                for (int c = 0; c < 4; ++c) o[c] = static_cast<unsigned char>(sum[c] / static_cast<unsigned>(f * f));
            }
        return d;
    }

    void createSampler(const Gpu& g) {
        VkSamplerCreateInfo si{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
        si.magFilter = si.minFilter = VK_FILTER_LINEAR;
        si.addressModeU = si.addressModeV = si.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        check(vkCreateSampler(g.dev, &si, nullptr, &sampler_), "échantillonneur des images de l'interface");
    }

    // Image pour écran (UNORM) : l'interface écrit des couleurs déjà prêtes pour l'écran (kFinalFormat).
    static void upload(const Gpu& g, Entry& e, const Decoded& d) {
        VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
        ii.imageType = VK_IMAGE_TYPE_2D;
        ii.format = VK_FORMAT_R8G8B8A8_UNORM;
        ii.extent = {static_cast<uint32_t>(d.w), static_cast<uint32_t>(d.h), 1};
        ii.mipLevels = 1;
        ii.arrayLayers = 1;
        ii.samples = VK_SAMPLE_COUNT_1_BIT;
        ii.usage = VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
        check(vkCreateImage(g.dev, &ii, nullptr, &e.image), "image de l'interface");
        VkMemoryRequirements mr;
        vkGetImageMemoryRequirements(g.dev, e.image, &mr);
        VkMemoryAllocateInfo mai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        mai.allocationSize = mr.size;
        mai.memoryTypeIndex = memoryType(g, mr.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        check(vkAllocateMemory(g.dev, &mai, nullptr, &e.mem), "mémoire de l'image de l'interface");
        vkBindImageMemory(g.dev, e.image, e.mem, 0);
        const VkDeviceSize bytes = d.px.size();
        Buffer staging = createBuffer(g, bytes, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, bytes, 0, &p), "accès à l'image de l'interface");
        std::memcpy(p, d.px.data(), bytes);
        vkUnmapMemory(g.dev, staging.mem);
        VkCommandBuffer cmd = beginOnce(g);
        VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
        b.srcQueueFamilyIndex = b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        b.image = e.image;
        b.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        b.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        b.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
        b.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, nullptr, 0, nullptr, 1, &b);
        VkBufferImageCopy region{};
        region.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
        region.imageExtent = ii.extent;
        vkCmdCopyBufferToImage(cmd, staging.buf, e.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &region);
        b.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
        b.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        b.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        b.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0, 0, nullptr, 0, nullptr, 1, &b);
        endOnce(g, cmd);
        destroy(g, staging);
        VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
        vi.image = e.image;
        vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
        vi.format = ii.format;
        vi.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        check(vkCreateImageView(g.dev, &vi, nullptr, &e.view), "vue de l'image de l'interface");
    }

    std::map<std::string, Entry> entries_;
    std::vector<Decoded> decoded_;
    std::mutex mutex_;
    std::thread loader_;
    std::atomic<bool> stop_{false};
    VkSampler sampler_ = VK_NULL_HANDLE;
};

// Posé par fenetre.cpp ; nul dans les contrôles sans images.
UiImages* gUiImages = nullptr;

}  // namespace
