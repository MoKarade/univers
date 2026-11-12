// Appli PC « Univers », jalon N1 (docs/plan-natif.md) : les étoiles de la page, dessinées par Vulkan 1.3.
//
// Pour l'instant sans fenêtre : l'image est rendue hors écran en grande dynamique (16 bits flottants par couleur),
// relue, convertie et écrite en .ppm. C'est aussi le mode des contrôles automatiques (aucune fenêtre sur le PC).
//
// Usage : univers <etoiles.bin> <image.ppm> [--regarde i] [--verifie i,j,k] [--images n] [--taille LxH] [--champ degres]
//   --regarde i   : la caméra, au Soleil, regarde l'étoile numéro i (défaut : étoile 0)
//   --verifie ... : contrôle que chaque étoile citée tombe sur un pixel lumineux à l'endroit calculé
//   --images n    : dessine n fois l'image et mesure la cadence
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

[[noreturn]] void fail(const std::string& what, VkResult r = VK_SUCCESS) {
    std::fprintf(stderr, "ECHEC : %s (code %d)\n", what.c_str(), static_cast<int>(r));
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

Gpu createGpu() {
    Gpu g;
    check(volkInitialize(), "chargement de Vulkan");
    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
    app.pApplicationName = "univers";
    app.apiVersion = VK_API_VERSION_1_3;
    VkInstanceCreateInfo ici{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    ici.pApplicationInfo = &app;
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

std::vector<uint32_t> readSpv(const std::string& name) {
    std::ifstream f(std::string(SPV_DIR) + "/" + name, std::ios::binary | std::ios::ate);
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
    float cam[4];
    float par[4];
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

std::vector<uint64_t> parseList(const char* s) {
    std::vector<uint64_t> out;
    for (const char* p = s; *p;) {
        char* end = nullptr;
        out.push_back(std::strtoull(p, &end, 10));
        p = (*end == ',') ? end + 1 : end;
        if (end == p && *p) break;
    }
    return out;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 3) fail("usage : univers <etoiles.bin> <image.ppm> [--regarde i] [--verifie i,j] [--images n] [--taille LxH] [--champ degres]");
    uint64_t lookAt = 0;
    std::vector<uint64_t> verify;
    int frames = 1;
    uint32_t width = 1920, height = 1080;
    double fovDeg = 60.0;
    for (int i = 3; i + 1 < argc; i += 2) {
        const std::string k = argv[i];
        if (k == "--regarde") lookAt = std::strtoull(argv[i + 1], nullptr, 10);
        else if (k == "--verifie") verify = parseList(argv[i + 1]);
        else if (k == "--images") frames = std::max(1, std::atoi(argv[i + 1]));
        else if (k == "--taille") std::sscanf(argv[i + 1], "%ux%u", &width, &height);
        else if (k == "--champ") fovDeg = std::atof(argv[i + 1]);
        else fail("option inconnue : " + k);
    }

    const Stars stars = openStars(argv[1]);
    std::printf("%llu etoiles\n", static_cast<unsigned long long>(stars.n));
    if (lookAt >= stars.n) fail("--regarde : numero hors du catalogue");
    const auto count = static_cast<uint32_t>(stars.n);

    // Couleur : table de 512 pas sur B-V (de -0,5 à 2,7 : l'étendue du codage de la page), appliquée à chaque étoile.
    std::vector<std::array<uint8_t, 4>> lut(512);
    for (int i = 0; i < 512; ++i) lut[i] = colorOfBv(-0.5 + 3.2 * i / 511.0);
    std::vector<std::array<uint8_t, 4>> colors(stars.n);
    for (uint64_t i = 0; i < stars.n; ++i) {
        const double t = (static_cast<double>(stars.bv()[i]) + 0.5) / 3.2 * 511.0;
        colors[i] = lut[static_cast<size_t>(std::clamp(t, 0.0, 511.0))];
    }

    const Gpu g = createGpu();
    const VkDeviceSize colBytes = static_cast<VkDeviceSize>(stars.n) * 4;
    Buffer vb[5] = {uploadVertices(g, stars.x(), colBytes), uploadVertices(g, stars.y(), colBytes), uploadVertices(g, stars.z(), colBytes),
                    uploadVertices(g, stars.mag(), colBytes), uploadVertices(g, colors.data(), colBytes)};

    // Image hors écran, 16 bits flottants par couleur (grande dynamique), addition des lumières.
    const VkFormat fmt = VK_FORMAT_R16G16B16A16_SFLOAT;
    VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
    ii.imageType = VK_IMAGE_TYPE_2D;
    ii.format = fmt;
    ii.extent = {width, height, 1};
    ii.mipLevels = 1;
    ii.arrayLayers = 1;
    ii.samples = VK_SAMPLE_COUNT_1_BIT;
    ii.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    VkImage image;
    check(vkCreateImage(g.dev, &ii, nullptr, &image), "image");
    VkMemoryRequirements mr;
    vkGetImageMemoryRequirements(g.dev, image, &mr);
    VkMemoryAllocateInfo mai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    mai.allocationSize = mr.size;
    mai.memoryTypeIndex = memoryType(g, mr.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    VkDeviceMemory imageMem;
    check(vkAllocateMemory(g.dev, &mai, nullptr, &imageMem), "mémoire de l'image");
    vkBindImageMemory(g.dev, image, imageMem, 0);
    VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
    vi.image = image;
    vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
    vi.format = fmt;
    vi.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
    VkImageView view;
    check(vkCreateImageView(g.dev, &vi, nullptr, &view), "vue de l'image");
    const VkDeviceSize imgBytes = static_cast<VkDeviceSize>(width) * height * 8;
    Buffer readback = createBuffer(g, imgBytes, VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);

    // Pipeline : points, cinq colonnes de sommets, addition.
    const VkShaderModule vs = shader(g, "etoiles.vert.spv"), fs = shader(g, "etoiles.frag.spv");
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
    VkPipelineLayout layout;
    check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout), "agencement");
    VkVertexInputBindingDescription binds[5];
    VkVertexInputAttributeDescription attrs[5];
    for (uint32_t i = 0; i < 5; ++i) {
        binds[i] = {i, 4, VK_VERTEX_INPUT_RATE_VERTEX};
        attrs[i] = {i, i, i < 4 ? VK_FORMAT_R32_SFLOAT : VK_FORMAT_R8G8B8A8_UNORM, 0};
    }
    VkPipelineVertexInputStateCreateInfo vin{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
    vin.vertexBindingDescriptionCount = 5;
    vin.pVertexBindingDescriptions = binds;
    vin.vertexAttributeDescriptionCount = 5;
    vin.pVertexAttributeDescriptions = attrs;
    VkPipelineInputAssemblyStateCreateInfo ia{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};
    ia.topology = VK_PRIMITIVE_TOPOLOGY_POINT_LIST;
    const VkViewport vp{0, 0, static_cast<float>(width), static_cast<float>(height), 0, 1};
    const VkRect2D sc{{0, 0}, {width, height}};
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
    pci.layout = layout;
    VkPipeline pipeline;
    check(vkCreateGraphicsPipelines(g.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &pipeline), "pipeline");

    // Caméra : au Soleil, tournée vers l'étoile demandée ; « haut » = pôle nord de l'écliptique.
    Camera cam;
    cam.pos = {0, 0, 0};
    cam.fwd = unit(Vec3{stars.x()[lookAt], stars.y()[lookAt], stars.z()[lookAt]} - cam.pos);
    cam.right = unit(cross(cam.fwd, Vec3{0, 0, 1}));
    cam.up = cross(cam.right, cam.fwd);
    cam.tanHalf = std::tan(fovDeg * kPi / 360.0);
    cam.aspect = static_cast<double>(width) / height;
    PushConstants pc{};
    const auto m = cam.viewProj();
    std::memcpy(pc.viewProj, m.data(), sizeof(pc.viewProj));
    pc.cam[0] = static_cast<float>(cam.pos.x);
    pc.cam[1] = static_cast<float>(cam.pos.y);
    pc.cam[2] = static_cast<float>(cam.pos.z);
    pc.par[0] = 40.0f;      // exposition : une étoile de magnitude apparente 0 vaut 40 (avant conversion pour l'écran)
    pc.par[1] = static_cast<float>(height);

    auto draw = [&](bool copy) {
        VkCommandBuffer cmd = beginOnce(g);
        VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
        b.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        b.newLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        b.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
        b.srcQueueFamilyIndex = b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        b.image = image;
        b.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, 0, 0, nullptr, 0, nullptr, 1, &b);
        VkRenderingAttachmentInfo color{VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO};
        color.imageView = view;
        color.imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        color.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        color.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        VkRenderingInfo ri{VK_STRUCTURE_TYPE_RENDERING_INFO};
        ri.renderArea = sc;
        ri.layerCount = 1;
        ri.colorAttachmentCount = 1;
        ri.pColorAttachments = &color;
        vkCmdBeginRendering(cmd, &ri);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
        const VkBuffer bufs[5] = {vb[0].buf, vb[1].buf, vb[2].buf, vb[3].buf, vb[4].buf};
        const VkDeviceSize offs[5] = {0, 0, 0, 0, 0};
        vkCmdBindVertexBuffers(cmd, 0, 5, bufs, offs);
        vkCmdPushConstants(cmd, layout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(pc), &pc);
        vkCmdDraw(cmd, count, 1, 0, 0);
        vkCmdEndRendering(cmd);
        if (copy) {
            b.oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
            b.newLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
            b.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
            b.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
            vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, nullptr, 0, nullptr, 1, &b);
            VkBufferImageCopy region{};
            region.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
            region.imageExtent = {width, height, 1};
            vkCmdCopyImageToBuffer(cmd, image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, readback.buf, 1, &region);
        }
        endOnce(g, cmd);      // attend la fin du dessin sur la carte
    };

    if (frames > 1) {
        draw(false);
        const auto t0 = std::chrono::steady_clock::now();
        for (int i = 0; i < frames; ++i) draw(false);
        const double dt = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        std::printf("cadence : %d images de %ux%u en %.3f s, soit %.1f images par seconde (%.2f ms par image)\n", frames, width, height, dt,
                    frames / dt, 1000.0 * dt / frames);
    }
    draw(true);

    void* mapped = nullptr;
    check(vkMapMemory(g.dev, readback.mem, 0, imgBytes, 0, &mapped), "lecture de l'image");
    const auto* h16 = static_cast<const uint16_t*>(mapped);
    std::vector<float> lum(static_cast<size_t>(width) * height);
    std::vector<uint8_t> rgb(static_cast<size_t>(width) * height * 3);
    for (size_t i = 0; i < lum.size(); ++i) {
        float c[3];
        for (int k = 0; k < 3; ++k) c[k] = halfToFloat(h16[i * 4 + k]);
        lum[i] = std::max({c[0], c[1], c[2]});
        for (int k = 0; k < 3; ++k) {
            const float v = c[k] / (1.0f + c[k]);      // compression de Reinhard, puis courbe sRGB approchée (gamma 2,2)
            rgb[i * 3 + k] = static_cast<uint8_t>(std::lround(255.0f * std::pow(std::clamp(v, 0.0f, 1.0f), 1.0f / 2.2f)));
        }
    }
    vkUnmapMemory(g.dev, readback.mem);
    {
        std::ofstream out(argv[2], std::ios::binary);
        out << "P6\n" << width << " " << height << "\n255\n";
        out.write(reinterpret_cast<const char*>(rgb.data()), static_cast<std::streamsize>(rgb.size()));
    }

    // Contrôle : chaque étoile citée doit éclairer l'endroit où le calcul en double précision la place.
    bool ok = true;
    for (uint64_t i : verify) {
        if (i >= stars.n) fail("--verifie : numero hors du catalogue");
        double px = 0, py = 0;
        const Vec3 p{stars.x()[i], stars.y()[i], stars.z()[i]};
        if (!cam.project(p, width, height, px, py)) {
            std::printf("etoile %llu : hors du champ\n", static_cast<unsigned long long>(i));
            continue;
        }
        const double d = std::sqrt(dot(p - cam.pos, p - cam.pos));
        const double mApp = stars.mag()[i] + 5.0 * std::log10(d / 3.2615638) - 5.0;
        const double flux = pc.par[0] * std::pow(10.0, -0.4 * mApp);
        // somme de la lumière dans un carré de 17 pixels autour de la position attendue
        double sum = 0;
        for (int dy = -8; dy <= 8; ++dy)
            for (int dx = -8; dx <= 8; ++dx) {
                const int X = static_cast<int>(px) + dx, Y = static_cast<int>(py) + dy;
                if (X >= 0 && Y >= 0 && X < static_cast<int>(width) && Y < static_cast<int>(height)) sum += lum[static_cast<size_t>(Y) * width + X];
            }
        const bool good = sum > 0.5 * flux && sum < 3.0 * flux;
        ok &= good;
        std::printf("etoile %llu : pixel attendu (%.1f, %.1f), magnitude apparente %.2f, lumiere attendue %.2f, mesuree %.2f -> %s\n",
                    static_cast<unsigned long long>(i), px, py, mApp, flux, sum, good ? "PASSE" : "ECHEC");
    }

    vkDestroyPipeline(g.dev, pipeline, nullptr);
    vkDestroyPipelineLayout(g.dev, layout, nullptr);
    vkDestroyShaderModule(g.dev, vs, nullptr);
    vkDestroyShaderModule(g.dev, fs, nullptr);
    Buffer rb = readback;
    destroy(g, rb);
    for (auto& b : vb) destroy(g, b);
    vkDestroyImageView(g.dev, view, nullptr);
    vkDestroyImage(g.dev, image, nullptr);
    vkFreeMemory(g.dev, imageMem, nullptr);
    vkDestroyCommandPool(g.dev, g.pool, nullptr);
    vkDestroyDevice(g.dev, nullptr);
    vkDestroyInstance(g.instance, nullptr);
    std::printf(ok ? "PASSE\n" : "ECHEC\n");
    return ok ? 0 : 1;
}
