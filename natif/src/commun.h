// Appli PC « Univers » : briques communes (fichier d'étoiles, couleur, caméra, Vulkan, dessin des étoiles).
// Inclus par univers.cpp (image hors écran, contrôles) et fenetre.cpp (fenêtre interactive).
#pragma once
#define VOLK_IMPLEMENTATION_NONE
#include <volk.h>
#include <windows.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr size_t kAlign = 64;

// Mode fenêtre : une erreur est montrée à l'écran (boîte de message) et écrite dans univers.log à côté du
// programme, au lieu de disparaître avec une console que personne ne voit.
inline bool gWindowMode = false;

[[noreturn]] void fail(const std::string& what, VkResult r = VK_SUCCESS) {
    const std::string msg = "ECHEC : " + what + " (code " + std::to_string(static_cast<int>(r)) + ")";
    std::fprintf(stderr, "%s\n", msg.c_str());
    if (gWindowMode) {
        char path[MAX_PATH];
        const DWORD n = GetModuleFileNameA(nullptr, path, MAX_PATH);
        std::string dir(path, n);
        const size_t cut = dir.find_last_of("\\/");
        if (cut != std::string::npos) dir.resize(cut);
        if (FILE* f = std::fopen((dir + "/univers.log").c_str(), "a")) {
            std::fprintf(f, "%s\n", msg.c_str());
            std::fclose(f);
        }
        MessageBoxA(nullptr, msg.c_str(), "Univers", MB_OK | MB_ICONERROR);
    }
    std::exit(1);
}
void check(VkResult r, const char* what) {
    if (r != VK_SUCCESS) fail(what, r);
}

// ---------------------------------------------------------------- fichier d'étoiles (pipeline/natif/etoiles.py)
struct Stars {
    HANDLE file = INVALID_HANDLE_VALUE, mapping = nullptr;
    const uint8_t* base = nullptr;
    uint64_t n = 0;
    size_t column = 0;      // taille d'une colonne, arrondie à 64 octets
    const float* col(int k) const { return reinterpret_cast<const float*>(base + kAlign + k * column); }
    const float* x() const { return col(0); }
    const float* y() const { return col(1); }
    const float* z() const { return col(2); }
    const float* mag() const { return col(3); }
    const float* bv() const { return col(4); }
    const float* vel(int axis) const { return col(5 + axis); }      // km/s
};

Stars openStars(const char* path) {
    Stars s;
    s.file = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (s.file == INVALID_HANDLE_VALUE) fail(std::string("fichier introuvable : ") + path);
    LARGE_INTEGER size;
    GetFileSizeEx(s.file, &size);
    s.mapping = CreateFileMappingA(s.file, nullptr, PAGE_READONLY, 0, 0, nullptr);
    if (!s.mapping) fail("projection du fichier en mémoire");
    s.base = static_cast<const uint8_t*>(MapViewOfFile(s.mapping, FILE_MAP_READ, 0, 0, 0));
    if (!s.base) fail("vue du fichier en mémoire");
    if (std::memcmp(s.base, "UNIVSTR1", 8) != 0) fail("ce n'est pas un fichier d'étoiles (UNIVSTR1)");
    std::memcpy(&s.n, s.base + 8, 8);
    s.column = (s.n * 4 + kAlign - 1) / kAlign * kAlign;
    if (static_cast<uint64_t>(size.QuadPart) < kAlign + 8 * s.column) fail("fichier d'étoiles tronqué");
    return s;
}

// ---------------------------------------------------------------- couleur d'une étoile
// Température d'après l'indice B-V : Ballesteros 2012 (EPL 97, 34008). Couleur : spectre de Planck intégré sur
// l'observateur CIE 1931, par l'ajustement analytique de Wyman, Sloan et Shirley 2013 (JCGT 2(2), 1), puis
// passage en sRGB linéaire. [Probable : coefficients recopiés ; la page utilise les tables CIE elles-mêmes (S1).]
double lobe(double l, double mu, double s1, double s2) {
    const double t = (l - mu) / (l < mu ? s1 : s2);
    return std::exp(-0.5 * t * t);
}
std::array<uint8_t, 4> colorOfBv(double bv) {
    const double T = 4600.0 * (1.0 / (0.92 * bv + 1.7) + 1.0 / (0.92 * bv + 0.62));
    double X = 0, Y = 0, Z = 0;
    for (double l = 380; l <= 780; l += 5) {
        const double m = l * 1e-9;
        const double B = 1.0 / (std::pow(m, 5) * (std::exp(1.438776877e-2 / (m * T)) - 1.0));      // Planck, à un facteur près
        X += B * (1.056 * lobe(l, 599.8, 37.9, 31.0) + 0.362 * lobe(l, 442.0, 16.0, 26.7) - 0.065 * lobe(l, 501.1, 20.4, 26.2));
        Y += B * (0.821 * lobe(l, 568.8, 46.9, 40.5) + 0.286 * lobe(l, 530.9, 16.3, 31.1));
        Z += B * (1.217 * lobe(l, 437.0, 11.8, 36.0) + 0.681 * lobe(l, 459.0, 26.0, 13.8));
    }
    double r = 3.2406 * X - 1.5372 * Y - 0.4986 * Z, g = -0.9689 * X + 1.8758 * Y + 0.0415 * Z, b = 0.0557 * X - 0.2040 * Y + 1.0570 * Z;
    r = std::max(r, 0.0); g = std::max(g, 0.0); b = std::max(b, 0.0);
    const double mx = std::max({r, g, b, 1e-30});
    auto q = [&](double v) { return static_cast<uint8_t>(std::lround(255.0 * v / mx)); };
    return {q(r), q(g), q(b), 255};
}

// ---------------------------------------------------------------- un peu d'algèbre (double précision côté processeur)
struct Vec3 { double x, y, z; };
Vec3 operator-(Vec3 a, Vec3 b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
double dot(Vec3 a, Vec3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
Vec3 cross(Vec3 a, Vec3 b) { return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x}; }
Vec3 unit(Vec3 a) { const double l = std::sqrt(dot(a, a)); return {a.x / l, a.y / l, a.z / l}; }

struct Camera {
    Vec3 pos, right, up, fwd;
    double tanHalf, aspect;
    // Vulkan : x à droite, y vers le bas, profondeur 0 à 1. Pas de tampon de profondeur ici : z fixé à 0,5.
    std::array<float, 16> viewProj() const {
        const double sx = 1.0 / (tanHalf * aspect), sy = 1.0 / tanHalf;
        const double rows[4][4] = {{sx * right.x, sx * right.y, sx * right.z, 0},
                                   {-sy * up.x, -sy * up.y, -sy * up.z, 0},
                                   {0.5 * fwd.x, 0.5 * fwd.y, 0.5 * fwd.z, 0},
                                   {fwd.x, fwd.y, fwd.z, 0}};
        std::array<float, 16> m{};
        for (int r = 0; r < 4; ++r)
            for (int c = 0; c < 4; ++c) m[c * 4 + r] = static_cast<float>(rows[r][c]);      // colonnes d'abord (GLSL)
        return m;
    }
    bool project(Vec3 p, double w, double h, double& px, double& py) const {
        const Vec3 d = p - pos;
        const double z = dot(d, fwd);
        if (z <= 0) return false;
        px = (dot(d, right) / (z * tanHalf * aspect) * 0.5 + 0.5) * w;
        py = (-dot(d, up) / (z * tanHalf) * 0.5 + 0.5) * h;
        return px >= 0 && px < w && py >= 0 && py < h;
    }
};

// ---------------------------------------------------------------- Vulkan
struct Gpu {
    VkInstance instance{};
    VkPhysicalDevice pd{};
    VkDevice dev{};
    uint32_t family = 0;
    VkQueue queue{};
    VkCommandPool pool{};
};

uint32_t memoryType(const Gpu& g, uint32_t bits, VkMemoryPropertyFlags want) {
    VkPhysicalDeviceMemoryProperties mp;
    vkGetPhysicalDeviceMemoryProperties(g.pd, &mp);
    for (uint32_t i = 0; i < mp.memoryTypeCount; ++i)
        if ((bits & (1u << i)) && (mp.memoryTypes[i].propertyFlags & want) == want) return i;
    fail("aucun type de mémoire convenable");
}

// window : ajoute ce qu'il faut pour dessiner dans une fenêtre Windows (surface, chaîne d'images).
Gpu createGpu(bool window = false) {
    Gpu g;
    check(volkInitialize(), "chargement de Vulkan");
    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
    app.pApplicationName = "univers";
    app.apiVersion = VK_API_VERSION_1_3;
    VkInstanceCreateInfo ici{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    ici.pApplicationInfo = &app;
    const char* instExt[] = {"VK_KHR_surface", "VK_KHR_win32_surface"};
    if (window) {
        ici.enabledExtensionCount = 2;
        ici.ppEnabledExtensionNames = instExt;
    }
    check(vkCreateInstance(&ici, nullptr, &g.instance), "instance");
    volkLoadInstance(g.instance);
    uint32_t n = 0;
    vkEnumeratePhysicalDevices(g.instance, &n, nullptr);
    std::vector<VkPhysicalDevice> pds(n);
    vkEnumeratePhysicalDevices(g.instance, &n, pds.data());
    if (pds.empty()) fail("aucune carte graphique Vulkan");
    g.pd = pds[0];
    VkPhysicalDeviceProperties props;
    for (auto c : pds) {
        vkGetPhysicalDeviceProperties(c, &props);
        if (props.deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU) { g.pd = c; break; }
    }
    vkGetPhysicalDeviceProperties(g.pd, &props);
    std::printf("carte : %s\n", props.deviceName);
    uint32_t qn = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(g.pd, &qn, nullptr);
    std::vector<VkQueueFamilyProperties> qf(qn);
    vkGetPhysicalDeviceQueueFamilyProperties(g.pd, &qn, qf.data());
    g.family = UINT32_MAX;
    for (uint32_t i = 0; i < qn; ++i)
        if (qf[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) { g.family = i; break; }
    if (g.family == UINT32_MAX) fail("aucune file graphique");
    const float prio = 1.0f;
    VkDeviceQueueCreateInfo qci{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
    qci.queueFamilyIndex = g.family;
    qci.queueCount = 1;
    qci.pQueuePriorities = &prio;
    VkPhysicalDeviceVulkan13Features on13{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES};
    on13.dynamicRendering = VK_TRUE;
    VkPhysicalDeviceFeatures feats{};
    feats.largePoints = VK_TRUE;
    VkDeviceCreateInfo dci{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO, &on13};
    dci.queueCreateInfoCount = 1;
    dci.pQueueCreateInfos = &qci;
    dci.pEnabledFeatures = &feats;
    const char* devExt[] = {"VK_KHR_swapchain"};
    if (window) {
        dci.enabledExtensionCount = 1;
        dci.ppEnabledExtensionNames = devExt;
    }
    check(vkCreateDevice(g.pd, &dci, nullptr, &g.dev), "périphérique");
    volkLoadDevice(g.dev);
    vkGetDeviceQueue(g.dev, g.family, 0, &g.queue);
    VkCommandPoolCreateInfo cpi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
    cpi.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    cpi.queueFamilyIndex = g.family;
    check(vkCreateCommandPool(g.dev, &cpi, nullptr, &g.pool), "réserve de commandes");
    return g;
}

struct Buffer {
    VkBuffer buf{};
    VkDeviceMemory mem{};
};

Buffer createBuffer(const Gpu& g, VkDeviceSize size, VkBufferUsageFlags usage, VkMemoryPropertyFlags props) {
    Buffer b;
    VkBufferCreateInfo bi{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
    bi.size = size;
    bi.usage = usage;
    check(vkCreateBuffer(g.dev, &bi, nullptr, &b.buf), "tampon");
    VkMemoryRequirements mr;
    vkGetBufferMemoryRequirements(g.dev, b.buf, &mr);
    VkMemoryAllocateInfo mai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    mai.allocationSize = mr.size;
    mai.memoryTypeIndex = memoryType(g, mr.memoryTypeBits, props);
    check(vkAllocateMemory(g.dev, &mai, nullptr, &b.mem), "mémoire du tampon");
    vkBindBufferMemory(g.dev, b.buf, b.mem, 0);
    return b;
}
void destroy(const Gpu& g, Buffer& b) {
    vkDestroyBuffer(g.dev, b.buf, nullptr);
    vkFreeMemory(g.dev, b.mem, nullptr);
}

VkCommandBuffer beginOnce(const Gpu& g) {
    VkCommandBufferAllocateInfo cai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
    cai.commandPool = g.pool;
    cai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    cai.commandBufferCount = 1;
    VkCommandBuffer cmd;
    check(vkAllocateCommandBuffers(g.dev, &cai, &cmd), "tampon de commandes");
    VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    vkBeginCommandBuffer(cmd, &begin);
    return cmd;
}
void endOnce(const Gpu& g, VkCommandBuffer cmd) {
    check(vkEndCommandBuffer(cmd), "fin des commandes");
    VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &cmd;
    check(vkQueueSubmit(g.queue, 1, &submit, VK_NULL_HANDLE), "envoi");
    check(vkQueueWaitIdle(g.queue), "attente");
    vkFreeCommandBuffers(g.dev, g.pool, 1, &cmd);
}

// Copie des octets vers un tampon de sommets en mémoire de la carte.
Buffer uploadVertices(const Gpu& g, const void* data, VkDeviceSize size) {
    Buffer staging = createBuffer(g, size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    void* p = nullptr;
    check(vkMapMemory(g.dev, staging.mem, 0, size, 0, &p), "accès au tampon");
    std::memcpy(p, data, size);
    vkUnmapMemory(g.dev, staging.mem);
    Buffer dst = createBuffer(g, size, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    VkCommandBuffer cmd = beginOnce(g);
    const VkBufferCopy region{0, 0, size};
    vkCmdCopyBuffer(cmd, staging.buf, dst.buf, 1, &region);
    endOnce(g, cmd);
    destroy(g, staging);
    return dst;
}

// Dossier du programme : les shaders compilés (spv/) et, par défaut, etoiles.bin sont rangés à côté de lui.
std::string exeDir() {
    char path[MAX_PATH];
    const DWORD n = GetModuleFileNameA(nullptr, path, MAX_PATH);
    std::string s(path, n);
    const size_t cut = s.find_last_of("\\/");
    return cut == std::string::npos ? "." : s.substr(0, cut);
}

std::vector<uint32_t> readSpv(const std::string& name) {
    std::ifstream f(exeDir() + "/spv/" + name, std::ios::binary | std::ios::ate);
    if (!f) fail("shader introuvable : " + name);
    const auto size = static_cast<size_t>(f.tellg());
    std::vector<uint32_t> code(size / 4);
    f.seekg(0);
    f.read(reinterpret_cast<char*>(code.data()), static_cast<std::streamsize>(size));
    return code;
}
VkShaderModule shader(const Gpu& g, const char* name) {
    const auto code = readSpv(name);
    VkShaderModuleCreateInfo si{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
    si.codeSize = code.size() * 4;
    si.pCode = code.data();
    VkShaderModule m;
    check(vkCreateShaderModule(g.dev, &si, nullptr, &m), name);
    return m;
}

struct PushConstants {
    float viewProj[16];
    float camHi[4];      // position de la caméra, partie principale (années-lumière)
    float camLo[4];      // reste de la position (ce que la simple précision a perdu)
    float par[4];        // exposition ; hauteur de l'image en pixels ; temps écoulé, en années-lumière par (km/s)
};

// Demi-flottant IEEE 754 -> flottant.
float halfToFloat(uint16_t h) {
    const uint32_t s = (h >> 15) & 1, e = (h >> 10) & 0x1f, m = h & 0x3ff;
    uint32_t bits;
    if (e == 0) {
        if (m == 0) bits = s << 31;
        else {
            int sh = 0;
            uint32_t mm = m;
            while (!(mm & 0x400)) { mm <<= 1; ++sh; }
            bits = (s << 31) | ((127 - 15 - sh + 1) << 23) | ((mm & 0x3ff) << 13);
        }
    } else if (e == 31) bits = (s << 31) | 0x7f800000u | (m << 13);
    else bits = (s << 31) | ((e - 15 + 127) << 23) | (m << 13);
    float f;
    std::memcpy(&f, &bits, 4);
    return f;
}

// ---------------------------------------------------------------- dessin des étoiles
// Points additionnés en grande dynamique ; huit colonnes de sommets (x, y, z, magnitude, couleur, vitesse).
// Le Soleil, absent du catalogue, est ajouté en dernier : à l'origine, magnitude absolue 4,83, B-V 0,653
// (valeurs nominales de l'UAI 2015 et de Ramírez et al. 2012 [Probable : recopiées de mémoire]).
constexpr float kSunAbsMag = 4.83f, kSunBv = 0.653f;
constexpr double kKmsToLyPerYear = 1.0 / 299792.458;

struct StarRenderer {
    static constexpr int kCols = 8;
    VkPipeline pipeline{};
    VkPipelineLayout layout{};
    VkShaderModule vs{}, fs{};
    Buffer vb[kCols];
    uint32_t count = 0;

    void create(const Gpu& g, const Stars& stars, VkFormat fmt) {
        const size_t n = static_cast<size_t>(stars.n) + 1;      // + le Soleil
        count = static_cast<uint32_t>(n);
        // Couleur : table de 512 pas sur B-V (de -0,5 à 2,7 : étendue du codage de la page), appliquée à chaque étoile.
        std::vector<std::array<uint8_t, 4>> lut(512);
        for (int i = 0; i < 512; ++i) lut[i] = colorOfBv(-0.5 + 3.2 * i / 511.0);
        auto colorOf = [&](double bv) { return lut[static_cast<size_t>(std::clamp((bv + 0.5) / 3.2 * 511.0, 0.0, 511.0))]; };
        std::vector<std::array<uint8_t, 4>> colors(n);
        for (uint64_t i = 0; i < stars.n; ++i) colors[i] = colorOf(stars.bv()[i]);
        colors[n - 1] = colorOf(kSunBv);
        std::vector<float> tmp(n);
        auto column = [&](const float* src, float sun) {
            std::memcpy(tmp.data(), src, static_cast<size_t>(stars.n) * 4);
            tmp[n - 1] = sun;
            return uploadVertices(g, tmp.data(), n * 4);
        };
        vb[0] = column(stars.x(), 0);
        vb[1] = column(stars.y(), 0);
        vb[2] = column(stars.z(), 0);
        vb[3] = column(stars.mag(), kSunAbsMag);
        vb[4] = uploadVertices(g, colors.data(), n * 4);
        for (int a = 0; a < 3; ++a) vb[5 + a] = column(stars.vel(a), 0);

        vs = shader(g, "etoiles.vert.spv");
        fs = shader(g, "etoiles.frag.spv");
        VkPipelineShaderStageCreateInfo stages[2] = {{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}, {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO}};
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vs;
        stages[0].pName = "main";
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fs;
        stages[1].pName = "main";
        const VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(PushConstants)};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout), "agencement");
        VkVertexInputBindingDescription binds[kCols];
        VkVertexInputAttributeDescription attrs[kCols];
        for (uint32_t i = 0; i < kCols; ++i) {
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
        const VkDynamicState dyn[2] = {VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR};      // taille donnée au moment du dessin
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
        pci.layout = layout;
        check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline), "pipeline des étoiles");
    }

    // À appeler entre vkCmdBeginRendering et vkCmdEndRendering, sur une image en grande dynamique vidée.
    void draw(VkCommandBuffer cmd, const PushConstants& pc, uint32_t width, uint32_t height) const {
        const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
        const VkRect2D sc{{0, 0}, {width, height}};
        vkCmdSetViewport(cmd, 0, 1, &vp);
        vkCmdSetScissor(cmd, 0, 1, &sc);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
        VkBuffer bufs[kCols];
        VkDeviceSize offs[kCols];
        for (int i = 0; i < kCols; ++i) {
            bufs[i] = vb[i].buf;
            offs[i] = 0;
        }
        vkCmdBindVertexBuffers(cmd, 0, kCols, bufs, offs);
        vkCmdPushConstants(cmd, layout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(pc), &pc);
        vkCmdDraw(cmd, count, 1, 0, 0);
    }

    void release(const Gpu& g) {
        vkDestroyPipeline(g.dev, pipeline, nullptr);
        vkDestroyPipelineLayout(g.dev, layout, nullptr);
        vkDestroyShaderModule(g.dev, vs, nullptr);
        vkDestroyShaderModule(g.dev, fs, nullptr);
        for (auto& b : vb) destroy(g, b);
    }
};

// Image de rendu en grande dynamique (16 bits flottants par couleur).
struct HdrTarget {
    VkImage image{};
    VkDeviceMemory mem{};
    VkImageView view{};
    uint32_t width = 0, height = 0;
    static constexpr VkFormat kFormat = VK_FORMAT_R16G16B16A16_SFLOAT;

    void create(const Gpu& g, uint32_t w, uint32_t h, VkImageUsageFlags extraUsage) {
        width = w;
        height = h;
        VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
        ii.imageType = VK_IMAGE_TYPE_2D;
        ii.format = kFormat;
        ii.extent = {w, h, 1};
        ii.mipLevels = 1;
        ii.arrayLayers = 1;
        ii.samples = VK_SAMPLE_COUNT_1_BIT;
        ii.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | extraUsage;
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
        vi.format = kFormat;
        vi.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        check(vkCreateImageView(g.dev, &vi, nullptr, &view), "vue de l'image");
    }
    void release(const Gpu& g) {
        vkDestroyImageView(g.dev, view, nullptr);
        vkDestroyImage(g.dev, image, nullptr);
        vkFreeMemory(g.dev, mem, nullptr);
    }
};

// Changement d'état d'une image entre deux usages.
void transition(VkCommandBuffer cmd, VkImage image, VkImageLayout from, VkImageLayout to, VkAccessFlags sa, VkAccessFlags da, VkPipelineStageFlags ss,
                VkPipelineStageFlags ds) {
    VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
    b.oldLayout = from;
    b.newLayout = to;
    b.srcAccessMask = sa;
    b.dstAccessMask = da;
    b.srcQueueFamilyIndex = b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    b.image = image;
    b.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
    vkCmdPipelineBarrier(cmd, ss, ds, 0, 0, nullptr, 0, nullptr, 1, &b);
}

// Caméra placée en pos, tournée vers la cible ; « haut » = pôle nord de l'écliptique.
Camera lookAt(Vec3 pos, Vec3 target, double fovDeg, double aspect) {
    Camera cam;
    cam.pos = pos;
    cam.fwd = unit(target - pos);
    cam.right = unit(cross(cam.fwd, Vec3{0, 0, 1}));
    cam.up = cross(cam.right, cam.fwd);
    cam.tanHalf = std::tan(fovDeg * kPi / 360.0);
    cam.aspect = aspect;
    return cam;
}

// years : années écoulées depuis l'époque du catalogue (les étoiles avancent en ligne droite à leur vitesse mesurée).
PushConstants pushConstants(const Camera& cam, float exposure, uint32_t height, double years = 0.0) {
    PushConstants pc{};
    const auto m = cam.viewProj();
    std::memcpy(pc.viewProj, m.data(), sizeof(pc.viewProj));
    const double p[3] = {cam.pos.x, cam.pos.y, cam.pos.z};
    for (int a = 0; a < 3; ++a) {
        pc.camHi[a] = static_cast<float>(p[a]);
        pc.camLo[a] = static_cast<float>(p[a] - static_cast<double>(pc.camHi[a]));
    }
    pc.par[0] = exposure;
    pc.par[1] = static_cast<float>(height);
    pc.par[2] = static_cast<float>(years * kKmsToLyPerYear);
    return pc;
}

constexpr float kExposure = 40.0f;      // une étoile de magnitude apparente 0 vaut 40 avant conversion pour l'écran

}  // namespace
