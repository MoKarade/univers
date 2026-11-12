// Contrôle sans fenêtre des étoiles Gaia DR3 (gaia.h) avec le catalogue principal de la page (commun.h).
// Dessine une image hors écran, mesure la cadence, écrit l'image (PPM) et compte les étoiles dessinées.
//
//   essai_gaia <gaia.bin> <etoiles.bin> <image.ppm> [--camera x,y,z] [--vers x,y,z] [--images n] [--flux-min f]
//              [--champ degres] [--taille LxH] [--expo e] [--date annees depuis J2000] [--voie-lactee voie_lactee.bin]
// gaia.bin peut valoir « - » : sans étoiles Gaia (catalogue de la page complet).
// Positions en années-lumière, repère écliptique J2000 centré sur le Soleil.
#include "commun.h"
#include "gaia.h"
#include "voie_lactee.h"

namespace {
Vec3 parseVec(const char* s) {
    Vec3 v{0, 0, 0};
    std::sscanf(s, "%lf,%lf,%lf", &v.x, &v.y, &v.z);
    return v;
}
}  // namespace

int main(int argc, char** argv) {
    if (argc < 4) fail("usage : essai_gaia <gaia.bin> <etoiles.bin> <image.ppm> [options]");
    Vec3 eye{0, 0, 0}, to{-8000, 0, 0};
    int frames = 1;
    float fluxMin = 1e-6f, exposure = kExposure;
    double fov = 60.0, years = 26.0;
    uint32_t width = 1920, height = 1080;
    bool toSet = false;
    std::string mwPath;
    for (int i = 4; i + 1 < argc; i += 2) {
        const std::string k = argv[i];
        const char* v = i + 1 < argc ? argv[i + 1] : "";
        if (k == "--camera") eye = parseVec(v);
        else if (k == "--vers") { to = parseVec(v); toSet = true; }
        else if (k == "--images") frames = std::max(1, std::atoi(v));
        else if (k == "--flux-min") fluxMin = static_cast<float>(std::atof(v));
        else if (k == "--champ") fov = std::atof(v);
        else if (k == "--taille") std::sscanf(v, "%ux%u", &width, &height);
        else if (k == "--expo") exposure = static_cast<float>(std::atof(v));
        else if (k == "--date") years = std::atof(v);
        else if (k == "--voie-lactee") mwPath = v;
        else fail("option inconnue : " + k);
    }
    if (!toSet) {      // par défaut : vers le centre galactique (l = 0, b = 0), d'après la direction connue en écliptique
        const double lam = 266.8517 * kPi / 180.0, bet = -5.6077 * kPi / 180.0;      // Sgr A* (ICRS 17 h 45 min 40,04 s, -29° 00′ 28,1″) tourné en écliptique J2000
        to = {eye.x + std::cos(bet) * std::cos(lam), eye.y + std::cos(bet) * std::sin(lam), eye.z + std::sin(bet)};
    }
    const Gpu g = createGpu();
    GaiaRenderer gaia;
    gaia.fluxMin = fluxMin;
    auto t0 = std::chrono::steady_clock::now();
    const bool withGaia = std::string(argv[1]) != "-";
    if (withGaia && !gaia.create(g, argv[1], HdrTarget::kFormat)) fail("gaia.bin absent, incomplet ou trop grand pour un tampon");
    MilkyWayRenderer mw;
    if (!mwPath.empty() && !mw.create(g, mwPath, HdrTarget::kFormat)) fail("voie_lactee.bin absent ou illisible");
    std::printf("gaia : %llu etoiles chargees en %.1f s\n", static_cast<unsigned long long>(gaia.count),
                std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
    const Stars stars = openStars(argv[2]);
    StarRenderer sr;
    sr.create(g, stars, HdrTarget::kFormat, withGaia);
    std::printf("catalogue principal : %u etoiles (avec le Soleil)\n", sr.count);

    HdrTarget target;
    target.create(g, width, height, VK_IMAGE_USAGE_TRANSFER_SRC_BIT);
    const VkDeviceSize imgBytes = static_cast<VkDeviceSize>(width) * height * 8;
    Buffer readback = createBuffer(g, imgBytes, VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    const Camera cam = lookAt(eye, to, fov, static_cast<double>(width) / height);
    const PushConstants pc = pushConstants(cam, exposure, height, years);

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
        mw.draw(cmd, cam, width, height, exposure, years);
        gaia.draw(cmd, cam, width, height, exposure, years);
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
        endOnce(g, cmd);
    };
    if (frames > 1) {
        draw(false);
        const auto t1 = std::chrono::steady_clock::now();
        for (int i = 0; i < frames; ++i) draw(false);
        const double dt = std::chrono::duration<double>(std::chrono::steady_clock::now() - t1).count();
        std::printf("cadence : %.1f images par seconde (%.2f ms par image, %ux%u)\n", frames / dt, 1000.0 * dt / frames, width, height);
    }
    draw(true);
    std::printf("etoiles Gaia dessinees : %llu sur %llu (flux minimal %g)\n", static_cast<unsigned long long>(gaia.drawn),
                static_cast<unsigned long long>(gaia.count), static_cast<double>(fluxMin));

    void* mapped = nullptr;
    check(vkMapMemory(g.dev, readback.mem, 0, imgBytes, 0, &mapped), "lecture de l'image");
    const auto* h16 = static_cast<const uint16_t*>(mapped);
    std::vector<uint8_t> rgb(static_cast<size_t>(width) * height * 3);
    double sum = 0;
    for (size_t i = 0; i < static_cast<size_t>(width) * height; ++i)
        for (int k = 0; k < 3; ++k) {
            const float c = halfToFloat(h16[i * 4 + k]);
            sum += c;
            const float v = c / (1.0f + c);      // même passage que ecran.frag (Reinhard puis sRGB)
            const float s = v <= 0.0031308f ? 12.92f * v : 1.055f * std::pow(v, 1.0f / 2.4f) - 0.055f;
            rgb[i * 3 + k] = static_cast<uint8_t>(std::lround(255.0f * std::clamp(s, 0.0f, 1.0f)));
        }
    vkUnmapMemory(g.dev, readback.mem);
    std::printf("lumiere totale de l'image : %.4g\n", sum);
    std::ofstream out(argv[3], std::ios::binary);
    out << "P6\n" << width << " " << height << "\n255\n";
    out.write(reinterpret_cast<const char*>(rgb.data()), static_cast<std::streamsize>(rgb.size()));
    destroy(g, readback);
    target.release(g);
    sr.release(g);
    gaia.release(g);
    mw.release(g);
    return 0;
}
