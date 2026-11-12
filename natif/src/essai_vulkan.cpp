// Essai N0 (docs/plan-natif.md) : prouve que le PC sait fabriquer et faire tourner un programme Vulkan 1.3,
// sans ouvrir de fenêtre. Dessine un triangle orange dans une image hors écran, relit l'image, vérifie deux
// pixels, écrit essai.ppm. Sortie 0 si tout est conforme.
#define VOLK_IMPLEMENTATION_NONE
#include <volk.h>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

namespace {

constexpr uint32_t kWidth = 640, kHeight = 360;

[[noreturn]] void fail(const char* what, VkResult r = VK_SUCCESS) {
    std::fprintf(stderr, "ECHEC : %s (code %d)\n", what, static_cast<int>(r));
    std::exit(1);
}
void check(VkResult r, const char* what) {
    if (r != VK_SUCCESS) fail(what, r);
}

std::vector<uint32_t> readSpv(const std::string& name) {
    std::ifstream f(std::string(SPV_DIR) + "/" + name, std::ios::binary | std::ios::ate);
    if (!f) fail(("shader introuvable : " + name).c_str());
    const auto size = static_cast<size_t>(f.tellg());
    std::vector<uint32_t> code(size / 4);
    f.seekg(0);
    f.read(reinterpret_cast<char*>(code.data()), static_cast<std::streamsize>(size));
    return code;
}

uint32_t memoryType(VkPhysicalDevice pd, uint32_t bits, VkMemoryPropertyFlags want) {
    VkPhysicalDeviceMemoryProperties mp;
    vkGetPhysicalDeviceMemoryProperties(pd, &mp);
    for (uint32_t i = 0; i < mp.memoryTypeCount; ++i)
        if ((bits & (1u << i)) && (mp.memoryTypes[i].propertyFlags & want) == want) return i;
    fail("aucun type de mémoire convenable");
}

}  // namespace

int main() {
    check(volkInitialize(), "chargement de Vulkan (vulkan-1.dll)");

    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
    app.pApplicationName = "univers-essai";
    app.apiVersion = VK_API_VERSION_1_3;
    VkInstanceCreateInfo ici{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    ici.pApplicationInfo = &app;
    VkInstance instance;
    check(vkCreateInstance(&ici, nullptr, &instance), "création de l'instance");
    volkLoadInstance(instance);

    // Carte graphique : la carte dédiée si elle existe.
    uint32_t n = 0;
    vkEnumeratePhysicalDevices(instance, &n, nullptr);
    std::vector<VkPhysicalDevice> pds(n);
    vkEnumeratePhysicalDevices(instance, &n, pds.data());
    if (pds.empty()) fail("aucune carte graphique Vulkan");
    VkPhysicalDevice pd = pds[0];
    VkPhysicalDeviceProperties props;
    for (auto c : pds) {
        vkGetPhysicalDeviceProperties(c, &props);
        if (props.deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU) { pd = c; break; }
    }
    vkGetPhysicalDeviceProperties(pd, &props);
    std::printf("carte : %s, Vulkan %u.%u.%u\n", props.deviceName, VK_API_VERSION_MAJOR(props.apiVersion),
                VK_API_VERSION_MINOR(props.apiVersion), VK_API_VERSION_PATCH(props.apiVersion));

    // Ce que le cahier des charges demande à la carte : on le lit, on ne le suppose pas.
    VkPhysicalDeviceMeshShaderFeaturesEXT mesh{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_MESH_SHADER_FEATURES_EXT};
    VkPhysicalDeviceVulkan13Features f13{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES, &mesh};
    VkPhysicalDeviceVulkan12Features f12{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES, &f13};
    VkPhysicalDeviceFeatures2 f2{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2, &f12};
    vkGetPhysicalDeviceFeatures2(pd, &f2);
    std::printf("rendu dynamique : %d | ressources sans liaison fixe : %d | dessin indirect compte : %d | mesh shaders : %d | double precision dans les shaders : %d\n",
                f13.dynamicRendering, f12.runtimeDescriptorArray && f12.descriptorBindingPartiallyBound, f12.drawIndirectCount,
                mesh.meshShader, f2.features.shaderFloat64);
    if (!f13.dynamicRendering) fail("rendu dynamique absent");

    uint32_t qn = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(pd, &qn, nullptr);
    std::vector<VkQueueFamilyProperties> qf(qn);
    vkGetPhysicalDeviceQueueFamilyProperties(pd, &qn, qf.data());
    uint32_t family = UINT32_MAX;
    for (uint32_t i = 0; i < qn; ++i)
        if (qf[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) { family = i; break; }
    if (family == UINT32_MAX) fail("aucune file graphique");

    const float prio = 1.0f;
    VkDeviceQueueCreateInfo qci{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
    qci.queueFamilyIndex = family;
    qci.queueCount = 1;
    qci.pQueuePriorities = &prio;
    VkPhysicalDeviceVulkan13Features on13{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES};
    on13.dynamicRendering = VK_TRUE;
    VkDeviceCreateInfo dci{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO, &on13};
    dci.queueCreateInfoCount = 1;
    dci.pQueueCreateInfos = &qci;
    VkDevice dev;
    check(vkCreateDevice(pd, &dci, nullptr, &dev), "création du périphérique");
    volkLoadDevice(dev);
    VkQueue queue;
    vkGetDeviceQueue(dev, family, 0, &queue);

    // Image hors écran.
    const VkFormat fmt = VK_FORMAT_R8G8B8A8_UNORM;
    VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
    ii.imageType = VK_IMAGE_TYPE_2D;
    ii.format = fmt;
    ii.extent = {kWidth, kHeight, 1};
    ii.mipLevels = 1;
    ii.arrayLayers = 1;
    ii.samples = VK_SAMPLE_COUNT_1_BIT;
    ii.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    VkImage image;
    check(vkCreateImage(dev, &ii, nullptr, &image), "création de l'image");
    VkMemoryRequirements mr;
    vkGetImageMemoryRequirements(dev, image, &mr);
    VkMemoryAllocateInfo mai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    mai.allocationSize = mr.size;
    mai.memoryTypeIndex = memoryType(pd, mr.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    VkDeviceMemory imageMem;
    check(vkAllocateMemory(dev, &mai, nullptr, &imageMem), "mémoire de l'image");
    vkBindImageMemory(dev, image, imageMem, 0);
    VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
    vi.image = image;
    vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
    vi.format = fmt;
    vi.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
    VkImageView view;
    check(vkCreateImageView(dev, &vi, nullptr, &view), "vue de l'image");

    // Tampon de relecture.
    const VkDeviceSize bytes = static_cast<VkDeviceSize>(kWidth) * kHeight * 4;
    VkBufferCreateInfo bi{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
    bi.size = bytes;
    bi.usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT;
    VkBuffer buf;
    check(vkCreateBuffer(dev, &bi, nullptr, &buf), "tampon de relecture");
    vkGetBufferMemoryRequirements(dev, buf, &mr);
    mai.allocationSize = mr.size;
    mai.memoryTypeIndex = memoryType(pd, mr.memoryTypeBits, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    VkDeviceMemory bufMem;
    check(vkAllocateMemory(dev, &mai, nullptr, &bufMem), "mémoire du tampon");
    vkBindBufferMemory(dev, buf, bufMem, 0);

    // Pipeline.
    auto module = [&](const char* name) {
        const auto code = readSpv(name);
        VkShaderModuleCreateInfo si{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
        si.codeSize = code.size() * 4;
        si.pCode = code.data();
        VkShaderModule m;
        check(vkCreateShaderModule(dev, &si, nullptr, &m), name);
        return m;
    };
    const VkShaderModule vs = module("essai.vert.spv"), fs = module("essai.frag.spv");
    VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
    stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
    stages[0].module = vs;
    stages[0].pName = "main";
    stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
    stages[1].module = fs;
    stages[1].pName = "main";
    VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
    VkPipelineLayout layout;
    check(vkCreatePipelineLayout(dev, &li, nullptr, &layout), "agencement du pipeline");
    VkPipelineVertexInputStateCreateInfo vin{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
    VkPipelineInputAssemblyStateCreateInfo ia{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};
    ia.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    const VkViewport vp{0, 0, static_cast<float>(kWidth), static_cast<float>(kHeight), 0, 1};
    const VkRect2D sc{{0, 0}, {kWidth, kHeight}};
    VkPipelineViewportStateCreateInfo vps{VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO};
    vps.viewportCount = 1;
    vps.pViewports = &vp;
    vps.scissorCount = 1;
    vps.pScissors = &sc;
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
    pci.layout = layout;
    VkPipeline pipeline;
    check(vkCreateGraphicsPipelines(dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline), "création du pipeline");

    // Commandes : dessiner, puis copier l'image dans le tampon.
    VkCommandPoolCreateInfo cpi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
    cpi.queueFamilyIndex = family;
    VkCommandPool pool;
    check(vkCreateCommandPool(dev, &cpi, nullptr, &pool), "réserve de commandes");
    VkCommandBufferAllocateInfo cai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
    cai.commandPool = pool;
    cai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    cai.commandBufferCount = 1;
    VkCommandBuffer cmd;
    check(vkAllocateCommandBuffers(dev, &cai, &cmd), "tampon de commandes");
    VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    vkBeginCommandBuffer(cmd, &begin);
    auto transition = [&](VkImageLayout from, VkImageLayout to, VkAccessFlags sa, VkAccessFlags da, VkPipelineStageFlags ss, VkPipelineStageFlags ds) {
        VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
        b.oldLayout = from;
        b.newLayout = to;
        b.srcAccessMask = sa;
        b.dstAccessMask = da;
        b.srcQueueFamilyIndex = b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        b.image = image;
        b.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        vkCmdPipelineBarrier(cmd, ss, ds, 0, 0, nullptr, 0, nullptr, 1, &b);
    };
    transition(VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, 0, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
               VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT);
    VkRenderingAttachmentInfo color{VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO};
    color.imageView = view;
    color.imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    color.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    color.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    color.clearValue.color = {{0.0f, 0.0f, 0.2f, 1.0f}};
    VkRenderingInfo ri{VK_STRUCTURE_TYPE_RENDERING_INFO};
    ri.renderArea = sc;
    ri.layerCount = 1;
    ri.colorAttachmentCount = 1;
    ri.pColorAttachments = &color;
    vkCmdBeginRendering(cmd, &ri);
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
    vkCmdDraw(cmd, 3, 1, 0, 0);
    vkCmdEndRendering(cmd);
    transition(VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
               VK_ACCESS_TRANSFER_READ_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT);
    VkBufferImageCopy region{};
    region.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
    region.imageExtent = {kWidth, kHeight, 1};
    vkCmdCopyImageToBuffer(cmd, image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, buf, 1, &region);
    check(vkEndCommandBuffer(cmd), "fin des commandes");
    VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &cmd;
    check(vkQueueSubmit(queue, 1, &submit, VK_NULL_HANDLE), "envoi");
    check(vkQueueWaitIdle(queue), "attente");

    void* mapped = nullptr;
    check(vkMapMemory(dev, bufMem, 0, bytes, 0, &mapped), "lecture du tampon");
    const auto* px = static_cast<const uint8_t*>(mapped);
    auto at = [&](uint32_t x, uint32_t y) { return px + 4 * (static_cast<size_t>(y) * kWidth + x); };
    const uint8_t* mid = at(kWidth / 2, kHeight / 2);
    const uint8_t* corner = at(2, 2);
    std::printf("pixel du centre : %u %u %u (attendu 255 128 0) | pixel du coin : %u %u %u (attendu 0 0 51)\n", mid[0], mid[1], mid[2],
                corner[0], corner[1], corner[2]);
    const bool ok = mid[0] == 255 && mid[1] >= 127 && mid[1] <= 128 && mid[2] == 0 && corner[0] == 0 && corner[1] == 0 && corner[2] == 51;
    {
        std::ofstream out("essai.ppm", std::ios::binary);
        out << "P6\n" << kWidth << " " << kHeight << "\n255\n";
        for (size_t i = 0; i < static_cast<size_t>(kWidth) * kHeight; ++i) out.write(reinterpret_cast<const char*>(px + 4 * i), 3);
    }
    vkUnmapMemory(dev, bufMem);

    vkDestroyPipeline(dev, pipeline, nullptr);
    vkDestroyPipelineLayout(dev, layout, nullptr);
    vkDestroyShaderModule(dev, vs, nullptr);
    vkDestroyShaderModule(dev, fs, nullptr);
    vkDestroyCommandPool(dev, pool, nullptr);
    vkDestroyBuffer(dev, buf, nullptr);
    vkFreeMemory(dev, bufMem, nullptr);
    vkDestroyImageView(dev, view, nullptr);
    vkDestroyImage(dev, image, nullptr);
    vkFreeMemory(dev, imageMem, nullptr);
    vkDestroyDevice(dev, nullptr);
    vkDestroyInstance(instance, nullptr);
    std::printf(ok ? "PASSE\n" : "ECHEC\n");
    return ok ? 0 : 1;
}
