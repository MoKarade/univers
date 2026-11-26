// Appli PC « Univers » : les briques d'affichage propres à la fenêtre (chaîne d'images de la fenêtre, images de
// rendu, conversion pour l'écran, capture de l'image finale).
#pragma once
#include "commun.h"

namespace univers {

inline constexpr VkFormat kFinalFormat = VK_FORMAT_B8G8R8A8_UNORM;  // l'interface écrit des couleurs déjà prêtes pour l'écran

struct Swapchain {
    VkSwapchainKHR chain{};
    VkExtent2D extent{};
    std::vector<VkImage> images;
};

inline void destroySwapchain(const Gpu& g, Swapchain& s) {
    if (s.chain) vkDestroySwapchainKHR(g.dev, s.chain, nullptr);
    s.chain = VK_NULL_HANDLE;
    s.images.clear();
}

// Rend false si la fenêtre n'a pas de surface à dessiner (réduite) : on ne dessine pas.
inline bool createSwapchain(const Gpu& g, VkSurfaceKHR surface, bool fastest, Swapchain& s) {
    VkSurfaceCapabilitiesKHR caps;
    check(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(g.pd, surface, &caps), "capacités de la surface");
    if (caps.currentExtent.width == 0 || caps.currentExtent.height == 0) return false;
    uint32_t n = 0;
    vkGetPhysicalDeviceSurfaceFormatsKHR(g.pd, surface, &n, nullptr);
    if (n == 0) return false;
    std::vector<VkSurfaceFormatKHR> formats(n);
    vkGetPhysicalDeviceSurfaceFormatsKHR(g.pd, surface, &n, formats.data());
    VkSurfaceFormatKHR chosen = formats[0];
    for (const auto& f : formats) {
        if (f.format == kFinalFormat && f.colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR) chosen = f;
    }
    vkGetPhysicalDeviceSurfacePresentModesKHR(g.pd, surface, &n, nullptr);
    std::vector<VkPresentModeKHR> modes(n);
    vkGetPhysicalDeviceSurfacePresentModesKHR(g.pd, surface, &n, modes.data());
    // Par défaut : au rythme de l'écran (pas de carte qui chauffe pour rien). Pour la mesure : au plus vite.
    VkPresentModeKHR mode = VK_PRESENT_MODE_FIFO_KHR;
    if (fastest) {
        for (auto m : modes) {
            if (m == VK_PRESENT_MODE_IMMEDIATE_KHR) mode = m;
        }
    }
    VkSwapchainCreateInfoKHR ci{VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR};
    ci.surface = surface;
    ci.minImageCount = std::max(caps.minImageCount + 1, 3u);
    if (caps.maxImageCount) ci.minImageCount = std::min(ci.minImageCount, caps.maxImageCount);
    ci.imageFormat = chosen.format;
    ci.imageColorSpace = chosen.colorSpace;
    ci.imageExtent = caps.currentExtent;
    ci.imageArrayLayers = 1;
    ci.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
    ci.imageSharingMode = VK_SHARING_MODE_EXCLUSIVE;
    ci.preTransform = caps.currentTransform;
    ci.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
    ci.presentMode = mode;
    ci.clipped = VK_TRUE;
    check(vkCreateSwapchainKHR(g.dev, &ci, nullptr, &s.chain), "chaîne d'images");
    s.extent = caps.currentExtent;
    vkGetSwapchainImagesKHR(g.dev, s.chain, &n, nullptr);
    s.images.resize(n);
    vkGetSwapchainImagesKHR(g.dev, s.chain, &n, s.images.data());
    return true;
}

// Image simple (rendu en grande dynamique, ou image finale).
struct Target {
    VkImage image{};
    VkDeviceMemory mem{};
    VkImageView view{};

    void create(const Gpu& g, VkFormat format, VkExtent2D extent, VkImageUsageFlags usage) {
        VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
        ii.imageType = VK_IMAGE_TYPE_2D;
        ii.format = format;
        ii.extent = {extent.width, extent.height, 1};
        ii.mipLevels = 1;
        ii.arrayLayers = 1;
        ii.samples = VK_SAMPLE_COUNT_1_BIT;
        ii.usage = usage;
        check(vkCreateImage(g.dev, &ii, nullptr, &image), "image");
        VkMemoryRequirements mr;
        vkGetImageMemoryRequirements(g.dev, image, &mr);
        VkMemoryAllocateInfo mai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        mai.allocationSize = mr.size;
        mai.memoryTypeIndex = memoryType(g, mr.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        check(vkAllocateMemory(g.dev, &mai, nullptr, &mem), "mémoire de l'image");
        vkBindImageMemory(g.dev, image, mem, 0);
        VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
        vi.image = image;
        vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
        vi.format = format;
        vi.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        check(vkCreateImageView(g.dev, &vi, nullptr, &view), "vue de l'image");
    }
    void release(const Gpu& g) {
        vkDestroyImageView(g.dev, view, nullptr);
        vkDestroyImage(g.dev, image, nullptr);
        vkFreeMemory(g.dev, mem, nullptr);
        *this = Target{};
    }
};

// Conversion de l'image en grande dynamique vers l'image finale (shaders ecran.vert / ecran.frag).
struct ScreenPass {
    VkDescriptorSetLayout setLayout{};
    VkDescriptorPool pool{};
    VkDescriptorSet set{};
    VkSampler sampler{};
    VkPipelineLayout layout{};
    VkPipeline pipeline{};
    VkShaderModule vs{}, fs{};

    void create(const Gpu& g) {
        VkSamplerCreateInfo sci{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
        sci.magFilter = sci.minFilter = VK_FILTER_NEAREST;
        sci.addressModeU = sci.addressModeV = sci.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        check(vkCreateSampler(g.dev, &sci, nullptr, &sampler), "échantillonneur");
        const VkDescriptorSetLayoutBinding bind{0, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1,
                                                VK_SHADER_STAGE_FRAGMENT_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 1;
        dl.pBindings = &bind;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout), "agencement des ressources");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 1;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool), "réserve de ressources");
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool;
        da.descriptorSetCount = 1;
        da.pSetLayouts = &setLayout;
        check(vkAllocateDescriptorSets(g.dev, &da, &set), "ressources");
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout), "agencement de l'écran");
        vs = shader(g, "ecran.vert.spv");
        fs = shader(g, "ecran.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO},
                                                     {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs;
        stages[1].pName = "main";
        VkPipelineVertexInputStateCreateInfo vin{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        VkPipelineInputAssemblyStateCreateInfo ia{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};
        ia.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
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
        att.colorWriteMask = 0xF;
        VkPipelineColorBlendStateCreateInfo cb{VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO};
        cb.attachmentCount = 1;
        cb.pAttachments = &att;
        VkPipelineRenderingCreateInfo rci{VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO};
        rci.colorAttachmentCount = 1;
        rci.pColorAttachmentFormats = &kFinalFormat;
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
        pci.layout = layout;
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline), "pipeline de l'écran");
    }

    void bindSource(const Gpu& g, VkImageView hdr) {
        const VkDescriptorImageInfo info{sampler, hdr, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL};
        VkWriteDescriptorSet w{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
        w.dstSet = set;
        w.dstBinding = 0;
        w.descriptorCount = 1;
        w.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
        w.pImageInfo = &info;
        vkUpdateDescriptorSets(g.dev, 1, &w, 0, nullptr);
    }

    // À appeler dans la passe de l'image finale.
    void draw(VkCommandBuffer cmd, VkExtent2D extent) const {
        const VkViewport vp{0, 0, static_cast<float>(extent.width), static_cast<float>(extent.height), 0, 1};
        const VkRect2D scissor{{0, 0}, extent};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &scissor);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout, 0, 1, &set, 0, nullptr);
        vkCmdDraw(cmd, 3, 1, 0, 0);
    }

    void release(const Gpu& g) {
        vkDestroyPipeline(g.dev, pipeline, nullptr);
        vkDestroyPipelineLayout(g.dev, layout, nullptr);
        vkDestroyShaderModule(g.dev, vs, nullptr);
        vkDestroyShaderModule(g.dev, fs, nullptr);
        vkDestroyDescriptorPool(g.dev, pool, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout, nullptr);
        vkDestroySampler(g.dev, sampler, nullptr);
    }
};

inline void beginPass(VkCommandBuffer cmd, VkImageView view, VkExtent2D extent) {
    VkRenderingAttachmentInfo color{VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO};
    color.imageView = view;
    color.imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    color.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    color.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    VkRenderingInfo ri{VK_STRUCTURE_TYPE_RENDERING_INFO};
    ri.renderArea = {{0, 0}, extent};
    ri.layerCount = 1;
    ri.colorAttachmentCount = 1;
    ri.pColorAttachments = &color;
    vkCmdBeginRendering(cmd, &ri);
}

// Écrit l'image finale (BGRA 8 bits, déjà dans l'état « source de copie ») dans un fichier .ppm.
inline void writeCapture(const Gpu& g, const Target& final, VkExtent2D extent, const std::string& path) {
    const size_t pixels = static_cast<size_t>(extent.width) * extent.height;
    const VkDeviceSize bytes = static_cast<VkDeviceSize>(pixels) * 4;
    Buffer rb = createBuffer(g, bytes, VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                             VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    VkCommandBuffer cmd = beginOnce(g);
    VkBufferImageCopy region{};
    region.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
    region.imageExtent = {extent.width, extent.height, 1};
    vkCmdCopyImageToBuffer(cmd, final.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, rb.buf, 1, &region);
    endOnce(g, cmd);
    void* p = nullptr;
    check(vkMapMemory(g.dev, rb.mem, 0, bytes, 0, &p), "lecture de l'image finale");
    const auto* srcPx = static_cast<const uint8_t*>(p);
    std::vector<uint8_t> rgb(pixels * 3);
    for (size_t i = 0; i < pixels; ++i) {
        rgb[i * 3] = srcPx[i * 4 + 2];
        rgb[i * 3 + 1] = srcPx[i * 4 + 1];
        rgb[i * 3 + 2] = srcPx[i * 4];
    }
    vkUnmapMemory(g.dev, rb.mem);
    destroy(g, rb);
    std::ofstream out(path, std::ios::binary);
    out << "P6\n" << extent.width << " " << extent.height << "\n255\n";
    out.write(reinterpret_cast<const char*>(rgb.data()), static_cast<std::streamsize>(rgb.size()));
    if (!out) fail("écriture de la capture impossible : " + path);
}

}  // namespace univers
