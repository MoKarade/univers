// Appli PC « Univers », jalon N1 (docs/plan-natif.md) : les étoiles de la page, dessinées par Vulkan 1.3.
//
// Deux modes :
//   univers                                                 fenêtre interactive, etoiles.bin pris à côté du programme
//   univers <etoiles.bin> --fenetre                          le simulateur (fenetre.cpp)
//   univers <etoiles.bin> --fenetre-test n [--capture f.ppm] [--cible Nom] [--distance al] [--date annees]
//                                                           même chemin, fenêtre cachée, n images, image finale écrite, puis sortie
//   univers <etoiles.bin> <image.ppm> [options]              image hors écran, sans fenêtre (contrôles)
// Options du mode image :
//   --regarde i   : la caméra, au Soleil, regarde l'étoile numéro i (défaut : étoile 0)
//   --verifie ... : contrôle que chaque étoile citée éclaire l'endroit calculé, avec l'éclat attendu
//   --images n    : dessine n fois l'image et mesure la cadence
//   --taille LxH, --champ degres
#include "commun.h"

#include "fenetre.h"

namespace {

std::vector<uint64_t> parseList(const char* s) {
    std::vector<uint64_t> out;
    for (const char* p = s; *p;) {
        char* end = nullptr;
        out.push_back(std::strtoull(p, &end, 10));
        if (end == p) break;
        p = (*end == ',') ? end + 1 : end;
    }
    return out;
}

}  // namespace

int main(int argc, char** argv) {
    WindowOptions wopt;
    if (argc == 1) {      // double-clic : le simulateur, avec les étoiles rangées à côté du programme
        wopt.starsPath = exeDir() + "/etoiles.bin";
        return runWindow(wopt);
    }
    if (argc < 3) fail("usage : univers <etoiles.bin> <image.ppm | --fenetre | --fenetre-test n> [--regarde i] [--verifie i,j] [--images n] [--taille LxH] [--champ degres]");
    uint64_t lookIndex = 0;
    std::vector<uint64_t> verify;
    int frames = 1, testFrames = 0;
    bool window = false;
    uint32_t width = 1920, height = 1080;
    double fovDeg = 60.0;
    const char* imagePath = nullptr;
    for (int i = 2; i < argc; ++i) {
        const std::string k = argv[i];
        const char* v = i + 1 < argc ? argv[i + 1] : "";
        if (k == "--fenetre") window = true;
        else if (k == "--fenetre-test") { window = true; testFrames = std::max(1, std::atoi(v)); ++i; }
        else if (k == "--capture") { wopt.capture = v; ++i; }
        else if (k == "--cible") { wopt.target = v; ++i; }
        else if (k == "--distance") { wopt.dist = std::atof(v); ++i; }
        else if (k == "--date") { wopt.years = std::atof(v); wopt.hasYears = true; ++i; }
        else if (k == "--regarde") { lookIndex = std::strtoull(v, nullptr, 10); ++i; }
        else if (k == "--verifie") { verify = parseList(v); ++i; }
        else if (k == "--images") { frames = std::max(1, std::atoi(v)); ++i; }
        else if (k == "--taille") { std::sscanf(v, "%ux%u", &width, &height); ++i; }
        else if (k == "--champ") { fovDeg = std::atof(v); ++i; }
        else if (k.rfind("--", 0) == 0) fail("option inconnue : " + k);
        else imagePath = argv[i];
    }
    if (window) {
        wopt.starsPath = argv[1];
        wopt.testFrames = testFrames;
        return runWindow(wopt);
    }
    if (!imagePath) fail("il manque le nom de l'image a ecrire");

    const Stars stars = openStars(argv[1]);
    std::printf("%llu etoiles\n", static_cast<unsigned long long>(stars.n));
    if (lookIndex >= stars.n) fail("--regarde : numero hors du catalogue");

    const Gpu g = createGpu();
    StarRenderer sr;
    sr.create(g, stars, HdrTarget::kFormat);
    HdrTarget target;
    target.create(g, width, height, VK_IMAGE_USAGE_TRANSFER_SRC_BIT);
    const VkDeviceSize imgBytes = static_cast<VkDeviceSize>(width) * height * 8;
    Buffer readback = createBuffer(g, imgBytes, VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);

    const Camera cam = lookAt({0, 0, 0}, {stars.x()[lookIndex], stars.y()[lookIndex], stars.z()[lookIndex]}, fovDeg, static_cast<double>(width) / height);
    const PushConstants pc = pushConstants(cam, kExposure, height);

    auto draw = [&](bool copy) {
        VkCommandBuffer cmd = beginOnce(g);
        transition(cmd, target.image, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, 0, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                   VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT);
        VkRenderingAttachmentInfo color{VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO};
        color.imageView = target.view;
        color.imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        color.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        color.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        VkRenderingInfo ri{VK_STRUCTURE_TYPE_RENDERING_INFO};
        ri.renderArea = {{0, 0}, {width, height}};
        ri.layerCount = 1;
        ri.colorAttachmentCount = 1;
        ri.pColorAttachments = &color;
        vkCmdBeginRendering(cmd, &ri);
        sr.draw(cmd, pc, width, height);
        vkCmdEndRendering(cmd);
        if (copy) {
            transition(cmd, target.image, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                       VK_ACCESS_TRANSFER_READ_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT);
            VkBufferImageCopy region{};
            region.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
            region.imageExtent = {width, height, 1};
            vkCmdCopyImageToBuffer(cmd, target.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, readback.buf, 1, &region);
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
        std::ofstream out(imagePath, std::ios::binary);
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
        double sum = 0;      // lumière dans un carré de 17 pixels autour de la position attendue
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

    sr.release(g);
    destroy(g, readback);
    target.release(g);
    vkDestroyCommandPool(g.dev, g.pool, nullptr);
    vkDestroyDevice(g.dev, nullptr);
    vkDestroyInstance(g.instance, nullptr);
    std::printf(ok ? "PASSE\n" : "ECHEC\n");
    return ok ? 0 : 1;
}
