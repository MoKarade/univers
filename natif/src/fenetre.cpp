// Appli PC « Univers » : la fenêtre interactive (jalon N1).
//
// Souris : glisser pour tourner la tête ; molette pour avancer ou reculer (comme le zoom de la page).
// Clavier (disposition du Québec) : W A S D ou les flèches pour avancer, reculer, aller de côté ; E / Q ou
// Page haut / Page bas pour monter et descendre ; Origine pour revenir au Soleil ; Échap pour quitter.
// Plus on est loin du Soleil, plus on va vite : un cran de molette vaut un quart de la distance déjà parcourue.
// Tant que personne ne touche à rien, la vue fait un lent tour d'horizon.
// En bas à gauche : où l'on est, et le rappel des commandes (texte dessiné par Windows, posé sur l'image).
//
// Chaque image : les étoiles sont additionnées dans une image en grande dynamique, puis cette image est
// convertie pour l'écran (shaders ecran.vert / ecran.frag).
#include "commun.h"

namespace {

struct Input {
    bool keys[256] = {};
    bool dragging = false;
    int lastX = 0, lastY = 0;
    double yaw = 0, pitch = 0;      // radians
    double wheel = 0;               // crans de molette en attente
    bool touched = false;           // quelqu'un a pris la main : fin du tour d'horizon
    bool resized = false, quit = false, home = false;
};

LRESULT CALLBACK wndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    auto* in = reinterpret_cast<Input*>(GetWindowLongPtrA(hwnd, GWLP_USERDATA));
    if (!in) return DefWindowProcA(hwnd, msg, wp, lp);
    switch (msg) {
        case WM_CLOSE: in->quit = true; return 0;
        case WM_SIZE: in->resized = true; return 0;
        case WM_KEYDOWN:
            if (wp == VK_ESCAPE) in->quit = true;
            if (wp == VK_HOME) in->home = true;
            if (wp < 256) in->keys[wp] = true;
            in->touched = true;
            return 0;
        case WM_KEYUP:
            if (wp < 256) in->keys[wp] = false;
            return 0;
        case WM_KILLFOCUS: std::memset(in->keys, 0, sizeof(in->keys)); in->dragging = false; return 0;
        case WM_LBUTTONDOWN:
            in->dragging = true;
            in->touched = true;
            in->lastX = static_cast<short>(LOWORD(lp));
            in->lastY = static_cast<short>(HIWORD(lp));
            SetCapture(hwnd);
            return 0;
        case WM_LBUTTONUP: in->dragging = false; ReleaseCapture(); return 0;
        case WM_MOUSEMOVE:
            if (in->dragging) {
                const int x = static_cast<short>(LOWORD(lp)), y = static_cast<short>(HIWORD(lp));
                in->yaw -= (x - in->lastX) * 0.0025;
                in->pitch = std::clamp(in->pitch - (y - in->lastY) * 0.0025, -1.55, 1.55);
                in->lastX = x;
                in->lastY = y;
            }
            return 0;
        case WM_MOUSEWHEEL:
            in->wheel += GET_WHEEL_DELTA_WPARAM(wp) / 120.0;
            in->touched = true;
            return 0;
        default: return DefWindowProcA(hwnd, msg, wp, lp);
    }
}

struct Swapchain {
    VkSwapchainKHR chain{};
    VkFormat format{};
    VkExtent2D extent{};
    std::vector<VkImage> images;
    std::vector<VkImageView> views;
};

void destroySwapchain(const Gpu& g, Swapchain& s) {
    for (auto v : s.views) vkDestroyImageView(g.dev, v, nullptr);
    s.views.clear();
    if (s.chain) vkDestroySwapchainKHR(g.dev, s.chain, nullptr);
    s.chain = VK_NULL_HANDLE;
}

// Rend false si la fenêtre n'a pas de surface à dessiner (réduite) : on ne dessine pas.
bool createSwapchain(const Gpu& g, VkSurfaceKHR surface, bool fastest, Swapchain& s) {
    VkSurfaceCapabilitiesKHR caps;
    check(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(g.pd, surface, &caps), "capacités de la surface");
    if (caps.currentExtent.width == 0 || caps.currentExtent.height == 0) return false;
    uint32_t n = 0;
    vkGetPhysicalDeviceSurfaceFormatsKHR(g.pd, surface, &n, nullptr);
    std::vector<VkSurfaceFormatKHR> formats(n);
    vkGetPhysicalDeviceSurfaceFormatsKHR(g.pd, surface, &n, formats.data());
    VkSurfaceFormatKHR chosen = formats[0];
    for (const auto& f : formats)
        if (f.format == VK_FORMAT_B8G8R8A8_SRGB && f.colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR) chosen = f;
    vkGetPhysicalDeviceSurfacePresentModesKHR(g.pd, surface, &n, nullptr);
    std::vector<VkPresentModeKHR> modes(n);
    vkGetPhysicalDeviceSurfacePresentModesKHR(g.pd, surface, &n, modes.data());
    // Par défaut : au rythme de l'écran (pas de carte qui chauffe pour rien). Pour la mesure : au plus vite.
    VkPresentModeKHR mode = VK_PRESENT_MODE_FIFO_KHR;
    if (fastest)
        for (auto m : modes)
            if (m == VK_PRESENT_MODE_IMMEDIATE_KHR) mode = m;
    VkSwapchainCreateInfoKHR ci{VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR};
    ci.surface = surface;
    ci.minImageCount = std::max(caps.minImageCount + 1, 3u);
    if (caps.maxImageCount) ci.minImageCount = std::min(ci.minImageCount, caps.maxImageCount);
    ci.imageFormat = chosen.format;
    ci.imageColorSpace = chosen.colorSpace;
    ci.imageExtent = caps.currentExtent;
    ci.imageArrayLayers = 1;
    ci.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
    ci.imageSharingMode = VK_SHARING_MODE_EXCLUSIVE;
    ci.preTransform = caps.currentTransform;
    ci.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
    ci.presentMode = mode;
    ci.clipped = VK_TRUE;
    check(vkCreateSwapchainKHR(g.dev, &ci, nullptr, &s.chain), "chaîne d'images");
    s.format = chosen.format;
    s.extent = caps.currentExtent;
    vkGetSwapchainImagesKHR(g.dev, s.chain, &n, nullptr);
    s.images.resize(n);
    vkGetSwapchainImagesKHR(g.dev, s.chain, &n, s.images.data());
    for (auto img : s.images) {
        VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
        vi.image = img;
        vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
        vi.format = s.format;
        vi.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        VkImageView v;
        check(vkCreateImageView(g.dev, &vi, nullptr, &v), "vue d'écran");
        s.views.push_back(v);
    }
    return true;
}

// Bandeau de texte : dessiné par Windows (GDI) dans une petite image, envoyée à la carte quand le texte change.
struct TextOverlay {
    static constexpr uint32_t kW = 1100, kH = 64;
    HDC dc{};
    HBITMAP bmp{};
    HFONT font{};
    uint8_t* bits = nullptr;
    VkImage image{};
    VkDeviceMemory mem{};
    VkImageView view{};
    Buffer staging;
    bool first = true;

    void create(const Gpu& g) {
        BITMAPINFO bi{};
        bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
        bi.bmiHeader.biWidth = kW;
        bi.bmiHeader.biHeight = -static_cast<LONG>(kH);      // première ligne en haut
        bi.bmiHeader.biPlanes = 1;
        bi.bmiHeader.biBitCount = 32;
        bi.bmiHeader.biCompression = BI_RGB;
        dc = CreateCompatibleDC(nullptr);
        void* p = nullptr;
        bmp = CreateDIBSection(dc, &bi, DIB_RGB_COLORS, &p, nullptr, 0);
        if (!bmp) fail("image du texte");
        bits = static_cast<uint8_t*>(p);
        SelectObject(dc, bmp);
        font = CreateFontW(-20, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, ANTIALIASED_QUALITY,
                           DEFAULT_PITCH, L"Segoe UI");
        SelectObject(dc, font);
        SetBkMode(dc, TRANSPARENT);
        SetTextColor(dc, RGB(255, 255, 255));

        VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
        ii.imageType = VK_IMAGE_TYPE_2D;
        ii.format = VK_FORMAT_B8G8R8A8_UNORM;
        ii.extent = {kW, kH, 1};
        ii.mipLevels = 1;
        ii.arrayLayers = 1;
        ii.samples = VK_SAMPLE_COUNT_1_BIT;
        ii.usage = VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
        check(vkCreateImage(g.dev, &ii, nullptr, &image), "image du texte");
        VkMemoryRequirements mr;
        vkGetImageMemoryRequirements(g.dev, image, &mr);
        VkMemoryAllocateInfo mai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        mai.allocationSize = mr.size;
        mai.memoryTypeIndex = memoryType(g, mr.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        check(vkAllocateMemory(g.dev, &mai, nullptr, &mem), "mémoire du texte");
        vkBindImageMemory(g.dev, image, mem, 0);
        VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
        vi.image = image;
        vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
        vi.format = ii.format;
        vi.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        check(vkCreateImageView(g.dev, &vi, nullptr, &view), "vue du texte");
        staging = createBuffer(g, kW * kH * 4, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    }

    // Deux lignes : où l'on est, puis les commandes. À appeler entre deux images (attend la carte).
    void set(const Gpu& g, const std::wstring& line1, const std::wstring& line2) {
        std::memset(bits, 0, kW * kH * 4);
        TextOutW(dc, 2, 2, line1.c_str(), static_cast<int>(line1.size()));
        TextOutW(dc, 2, 32, line2.c_str(), static_cast<int>(line2.size()));
        GdiFlush();
        void* p = nullptr;
        check(vkMapMemory(g.dev, staging.mem, 0, kW * kH * 4, 0, &p), "accès au texte");
        std::memcpy(p, bits, kW * kH * 4);
        vkUnmapMemory(g.dev, staging.mem);
        VkCommandBuffer cmd = beginOnce(g);
        transition(cmd, image, first ? VK_IMAGE_LAYOUT_UNDEFINED : VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 0,
                   VK_ACCESS_TRANSFER_WRITE_BIT, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT);
        VkBufferImageCopy region{};
        region.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
        region.imageExtent = {kW, kH, 1};
        vkCmdCopyBufferToImage(cmd, staging.buf, image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &region);
        transition(cmd, image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_ACCESS_TRANSFER_WRITE_BIT,
                   VK_ACCESS_SHADER_READ_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        endOnce(g, cmd);
        first = false;
    }

    void release(const Gpu& g) {
        vkDestroyImageView(g.dev, view, nullptr);
        vkDestroyImage(g.dev, image, nullptr);
        vkFreeMemory(g.dev, mem, nullptr);
        destroy(g, staging);
        DeleteObject(font);
        DeleteObject(bmp);
        DeleteDC(dc);
    }
};

// Nombre écrit à la française : virgule décimale, trois chiffres utiles.
std::wstring frNumber(double v) {
    wchar_t buf[64];
    if (v >= 100) std::swprintf(buf, 64, L"%.0f", v);
    else if (v >= 10) std::swprintf(buf, 64, L"%.1f", v);
    else std::swprintf(buf, 64, L"%.2f", v);
    std::wstring s(buf);
    for (auto& c : s)
        if (c == L'.') c = L',';
    return s;
}

// Conversion de l'image en grande dynamique vers l'écran.
struct ScreenPass {
    VkDescriptorSetLayout setLayout{};
    VkDescriptorPool pool{};
    VkDescriptorSet set{};
    VkSampler sampler{};
    VkPipelineLayout layout{};
    VkPipeline pipeline{};
    VkShaderModule vs{}, fs{};

    void create(const Gpu& g, VkFormat screenFormat) {
        VkSamplerCreateInfo sci{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
        sci.magFilter = sci.minFilter = VK_FILTER_NEAREST;
        sci.addressModeU = sci.addressModeV = sci.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        check(vkCreateSampler(g.dev, &sci, nullptr, &sampler), "échantillonneur");
        const VkDescriptorSetLayoutBinding bind[2] = {{0, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr},
                                                      {1, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr}};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 2;
        dl.pBindings = bind;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout), "agencement des ressources");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 2};
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
        const VkPushConstantRange pcr{VK_SHADER_STAGE_FRAGMENT_BIT, 0, 16};      // tailles de la fenêtre et du bandeau
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout), "agencement de l'écran");
        vs = shader(g, "ecran.vert.spv");
        fs = shader(g, "ecran.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
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
        rci.pColorAttachmentFormats = &screenFormat;
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

    void bindSource(const Gpu& g, VkImageView hdr, VkImageView text) {
        const VkDescriptorImageInfo info[2] = {{sampler, hdr, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL}, {sampler, text, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL}};
        VkWriteDescriptorSet w[2] = {{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET}, {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET}};
        for (uint32_t i = 0; i < 2; ++i) {
            w[i].dstSet = set;
            w[i].dstBinding = i;
            w[i].descriptorCount = 1;
            w[i].descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
            w[i].pImageInfo = &info[i];
        }
        vkUpdateDescriptorSets(g.dev, 2, w, 0, nullptr);
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

void beginPass(VkCommandBuffer cmd, VkImageView view, VkExtent2D extent) {
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

}  // namespace

// testFrames > 0 : fenêtre cachée, ce nombre d'images au plus vite, puis sortie (contrôle sans rien montrer à l'écran).
int runWindow(const char* starsPath, uint64_t lookAtIndex, int testFrames) {
    const bool test = testFrames > 0;
    gWindowMode = !test;      // dès le début : même un fichier d'étoiles absent est dit à l'écran
    const Stars stars = openStars(starsPath);
    if (lookAtIndex >= stars.n) fail("--regarde : numero hors du catalogue");

    Input input;
    WNDCLASSA wc{};
    wc.lpfnWndProc = wndProc;
    wc.hInstance = GetModuleHandleA(nullptr);
    wc.lpszClassName = "UniversFenetre";
    wc.hCursor = LoadCursorA(nullptr, IDC_ARROW);
    RegisterClassA(&wc);
    RECT r{0, 0, 1600, 900};
    AdjustWindowRect(&r, WS_OVERLAPPEDWINDOW, FALSE);
    HWND hwnd = CreateWindowExA(0, wc.lpszClassName, "Univers", WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, r.right - r.left, r.bottom - r.top, nullptr,
                                nullptr, wc.hInstance, nullptr);
    if (!hwnd) fail("création de la fenêtre");
    SetWindowLongPtrA(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(&input));
    if (!test) {
        // Deux appels : Windows impose au premier l'état demandé par le lanceur (un raccourci « réduit » donnait une
        // fenêtre réduite, sans surface à dessiner : l'appli s'arrêtait sans rien montrer). Le second s'applique toujours.
        ShowWindow(hwnd, SW_SHOWNORMAL);
        ShowWindow(hwnd, SW_SHOWNORMAL);
        SetForegroundWindow(hwnd);
    }

    const Gpu g = createGpu(true);
    VkWin32SurfaceCreateInfoKHR sci{VK_STRUCTURE_TYPE_WIN32_SURFACE_CREATE_INFO_KHR};
    sci.hinstance = wc.hInstance;
    sci.hwnd = hwnd;
    VkSurfaceKHR surface;
    check(vkCreateWin32SurfaceKHR(g.instance, &sci, nullptr, &surface), "surface de la fenêtre");
    VkBool32 canPresent = VK_FALSE;
    vkGetPhysicalDeviceSurfaceSupportKHR(g.pd, g.family, surface, &canPresent);
    if (!canPresent) fail("la carte ne peut pas afficher dans cette fenêtre");

    Swapchain sc;
    while (!createSwapchain(g, surface, test, sc)) {      // fenêtre réduite : on attend qu'elle ait une surface
        if (test) fail("fenêtre sans surface");
        MSG m;
        while (PeekMessageA(&m, nullptr, 0, 0, PM_REMOVE)) {
            TranslateMessage(&m);
            DispatchMessageA(&m);
        }
        if (input.quit) return 0;
        Sleep(50);
    }
    StarRenderer sr;
    sr.create(g, stars, HdrTarget::kFormat);
    HdrTarget hdr;
    hdr.create(g, sc.extent.width, sc.extent.height, VK_IMAGE_USAGE_SAMPLED_BIT);
    ScreenPass screen;
    screen.create(g, sc.format);
    TextOverlay text;
    text.create(g);
    const std::wstring help = L"Glisse la souris : tourner   \u2022   Molette : avancer, reculer   \u2022   W A S D : se d\u00e9placer   \u2022   Origine : retour au Soleil   \u2022   \u00c9chap : quitter";
    text.set(g, L"Au Soleil", help);
    if (test) {      // contrôle sans écran : le bandeau tel que Windows l'a dessiné, avec des accents et un nombre
        text.set(g, L"\u00c0 " + frNumber(12.345) + L" ann\u00e9es-lumi\u00e8re du Soleil", help);
        std::ofstream out(exeDir() + "/texte.ppm", std::ios::binary);
        out << "P6\n" << TextOverlay::kW << " " << TextOverlay::kH << "\n255\n";
        for (uint32_t i = 0; i < TextOverlay::kW * TextOverlay::kH; ++i) out.write(reinterpret_cast<const char*>(text.bits + 4 * i), 3);
    }
    screen.bindSource(g, hdr.view, text.view);

    VkCommandBufferAllocateInfo cai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
    cai.commandPool = g.pool;
    cai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    cai.commandBufferCount = 1;
    VkCommandBuffer cmd;
    check(vkAllocateCommandBuffers(g.dev, &cai, &cmd), "tampon de commandes");
    VkSemaphoreCreateInfo semi{VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
    VkSemaphore acquired, rendered;
    check(vkCreateSemaphore(g.dev, &semi, nullptr, &acquired), "sémaphore");
    check(vkCreateSemaphore(g.dev, &semi, nullptr, &rendered), "sémaphore");
    VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
    fi.flags = VK_FENCE_CREATE_SIGNALED_BIT;
    VkFence fence;
    check(vkCreateFence(g.dev, &fi, nullptr, &fence), "barrière");

    // Départ : au Soleil, tourné vers l'étoile demandée.
    Vec3 pos{0, 0, 0};
    {
        const Vec3 d = unit(Vec3{stars.x()[lookAtIndex], stars.y()[lookAtIndex], stars.z()[lookAtIndex]});
        input.yaw = std::atan2(d.y, d.x);
        input.pitch = std::asin(std::clamp(d.z, -1.0, 1.0));
    }
    const double yaw0 = input.yaw, pitch0 = input.pitch;

    auto rebuild = [&]() {
        vkDeviceWaitIdle(g.dev);
        destroySwapchain(g, sc);
        hdr.release(g);
        hdr = HdrTarget{};
        if (!createSwapchain(g, surface, test, sc)) return false;
        hdr.create(g, sc.extent.width, sc.extent.height, VK_IMAGE_USAGE_SAMPLED_BIT);
        screen.bindSource(g, hdr.view, text.view);
        return true;
    };

    auto last = std::chrono::steady_clock::now();
    const auto start = last;
    int frame = 0, shown = 0;
    double titleTimer = 0;
    bool drawable = true;
    while (!input.quit) {
        MSG msg;
        while (PeekMessageA(&msg, nullptr, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessageA(&msg);
        }
        if (input.resized || !drawable) {
            input.resized = false;
            drawable = rebuild();
            if (!drawable) { Sleep(50); continue; }
        }
        const auto now = std::chrono::steady_clock::now();
        const double dt = std::min(0.1, std::chrono::duration<double>(now - last).count());
        last = now;

        // Déplacement : dans le repère de la tête.
        const Vec3 fwd{std::cos(input.pitch) * std::cos(input.yaw), std::cos(input.pitch) * std::sin(input.yaw), std::sin(input.pitch)};
        const Vec3 right = unit(cross(fwd, Vec3{0, 0, 1}));
        const Vec3 up = cross(right, fwd);
        auto key = [&](int a, int b = 0, int c = 0) { return input.keys[a] || (b && input.keys[b]) || (c && input.keys[c]); };
        const double f = (key('W', VK_UP) ? 1 : 0) - (key('S', VK_DOWN) ? 1 : 0);
        const double s = (key('D', VK_RIGHT) ? 1 : 0) - (key('A', VK_LEFT) ? 1 : 0);
        const double u = (key('E', VK_PRIOR) ? 1 : 0) - (key('Q', VK_NEXT) ? 1 : 0);
        // Plus on est loin du Soleil, plus on va vite : l'échelle est la distance déjà parcourue (au moins 2 années-lumière).
        const double scale = std::sqrt(dot(pos, pos)) + 2.0;
        const double step = 0.6 * scale * dt;                     // touches : 60 % de l'échelle par seconde
        const double zoom = 0.25 * scale * input.wheel;           // molette : un quart de l'échelle par cran
        input.wheel = 0;
        pos = {pos.x + step * (f * fwd.x + s * right.x + u * up.x) + zoom * fwd.x, pos.y + step * (f * fwd.y + s * right.y + u * up.y) + zoom * fwd.y,
               pos.z + step * (f * fwd.z + s * right.z + u * up.z) + zoom * fwd.z};
        if (!input.touched && !test) input.yaw += 0.035 * dt;      // lent tour d'horizon (2 degrés par seconde) tant que personne ne touche
        if (input.home) {
            input.home = false;
            pos = {0, 0, 0};
            input.yaw = yaw0;
            input.pitch = pitch0;
        }
        Camera cam;
        cam.pos = pos;
        cam.fwd = fwd;
        cam.right = right;
        cam.up = up;
        cam.tanHalf = std::tan(60.0 * kPi / 360.0);
        cam.aspect = static_cast<double>(sc.extent.width) / sc.extent.height;
        const PushConstants pc = pushConstants(cam, kExposure, sc.extent.height);

        vkWaitForFences(g.dev, 1, &fence, VK_TRUE, UINT64_MAX);
        uint32_t index = 0;
        VkResult ar = vkAcquireNextImageKHR(g.dev, sc.chain, UINT64_MAX, acquired, VK_NULL_HANDLE, &index);
        if (ar == VK_ERROR_OUT_OF_DATE_KHR) { input.resized = true; continue; }
        if (ar != VK_SUCCESS && ar != VK_SUBOPTIMAL_KHR) fail("image d'écran", ar);
        vkResetFences(g.dev, 1, &fence);

        vkResetCommandBuffer(cmd, 0);
        VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        vkBeginCommandBuffer(cmd, &begin);
        transition(cmd, hdr.image, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, 0, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                   VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT);
        beginPass(cmd, hdr.view, sc.extent);
        sr.draw(cmd, pc, sc.extent.width, sc.extent.height);
        vkCmdEndRendering(cmd);
        transition(cmd, hdr.image, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                   VK_ACCESS_SHADER_READ_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        transition(cmd, sc.images[index], VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, 0, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                   VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT);
        beginPass(cmd, sc.views[index], sc.extent);
        const VkViewport vp{0, 0, static_cast<float>(sc.extent.width), static_cast<float>(sc.extent.height), 0, 1};
        const VkRect2D scissor{{0, 0}, sc.extent};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &scissor);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, screen.pipeline);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, screen.layout, 0, 1, &screen.set, 0, nullptr);
        const float dim[4] = {static_cast<float>(sc.extent.width), static_cast<float>(sc.extent.height), static_cast<float>(TextOverlay::kW),
                              static_cast<float>(TextOverlay::kH)};
        vkCmdPushConstants(cmd, screen.layout, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(dim), dim);
        vkCmdDraw(cmd, 3, 1, 0, 0);
        vkCmdEndRendering(cmd);
        transition(cmd, sc.images[index], VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_PRESENT_SRC_KHR, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT, 0,
                   VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT);
        check(vkEndCommandBuffer(cmd), "fin des commandes");

        const VkPipelineStageFlags waitStage = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};
        submit.waitSemaphoreCount = 1;
        submit.pWaitSemaphores = &acquired;
        submit.pWaitDstStageMask = &waitStage;
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &cmd;
        submit.signalSemaphoreCount = 1;
        submit.pSignalSemaphores = &rendered;
        check(vkQueueSubmit(g.queue, 1, &submit, fence), "envoi");
        VkPresentInfoKHR present{VK_STRUCTURE_TYPE_PRESENT_INFO_KHR};
        present.waitSemaphoreCount = 1;
        present.pWaitSemaphores = &rendered;
        present.swapchainCount = 1;
        present.pSwapchains = &sc.chain;
        present.pImageIndices = &index;
        const VkResult pr = vkQueuePresentKHR(g.queue, &present);
        if (pr == VK_ERROR_OUT_OF_DATE_KHR || pr == VK_SUBOPTIMAL_KHR) input.resized = true;
        else if (pr != VK_SUCCESS) fail("affichage", pr);

        ++frame;
        ++shown;
        titleTimer += dt;
        if (!test && titleTimer > 0.25) {      // quatre fois par seconde : la ligne « où l'on est » et le titre
            const double d = std::sqrt(dot(pos, pos));
            const std::wstring where = d < 1e-3 ? L"Au Soleil" : L"\u00c0 " + frNumber(d) + L" ann\u00e9es-lumi\u00e8re du Soleil";
            char title[120];
            std::snprintf(title, sizeof(title), "Univers  |  %.0f images par seconde", shown / titleTimer);
            SetWindowTextA(hwnd, title);
            vkWaitForFences(g.dev, 1, &fence, VK_TRUE, UINT64_MAX);
            text.set(g, where, help);
            titleTimer = 0;
            shown = 0;
        }
        if (test && frame >= testFrames) break;
    }
    vkDeviceWaitIdle(g.dev);
    if (test) {
        const double total = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        std::printf("fenetre cachee %ux%u : %d images affichees en %.3f s, soit %.1f images par seconde\nPASSE\n", sc.extent.width, sc.extent.height, frame, total,
                    frame / total);
    }

    vkDestroyFence(g.dev, fence, nullptr);
    vkDestroySemaphore(g.dev, acquired, nullptr);
    vkDestroySemaphore(g.dev, rendered, nullptr);
    screen.release(g);
    text.release(g);
    sr.release(g);
    hdr.release(g);
    destroySwapchain(g, sc);
    vkDestroySurfaceKHR(g.instance, surface, nullptr);
    vkDestroyCommandPool(g.dev, g.pool, nullptr);
    vkDestroyDevice(g.dev, nullptr);
    vkDestroyInstance(g.instance, nullptr);
    DestroyWindow(hwnd);
    return 0;
}
