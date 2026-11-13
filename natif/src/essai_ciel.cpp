// Contrôle sans fenêtre du ciel par bande (ciel_bandes.h) : image hors écran d'une carte mesurée, et valeur lue par le
// processeur (même calcul HEALPix que le shader) dans quelques directions connues.
//
//   essai_ciel <ciel_x.bin> <image.ppm> [--vers l,b] [--champ degres] [--taille LxH] [--camera x,y,z]
// --vers : direction regardée en coordonnées galactiques (degrés). --camera : position (années-lumière, écliptique J2000).
#include "commun.h"
#include "ciel_bandes.h"

namespace {
uint64_t spread(uint64_t x) {
    uint64_t r = 0;
    for (int b = 0; b < 32; ++b) r |= ((x >> b) & 1ull) << (2 * b);
    return r;
}
// Même calcul que ciel_bandes.frag, en double précision.
uint64_t ang2pixNest(int64_t nside, double x, double y, double z) {
    const double n = std::sqrt(x * x + y * y + z * z);
    z /= n;
    const double za = std::fabs(z);
    double phi = std::atan2(y, x);
    if (phi < 0) phi += 2 * kPi;
    const double tt = phi / (0.5 * kPi);
    int64_t face, ix, iy;
    if (za <= 2.0 / 3.0) {
        const double t1 = nside * (0.5 + tt), t2 = nside * z * 0.75;
        const int64_t jp = static_cast<int64_t>(t1 - t2), jm = static_cast<int64_t>(t1 + t2);
        const int64_t ifp = jp / nside, ifm = jm / nside;
        face = ifp == ifm ? (ifp | 4) : (ifp < ifm ? ifp : ifm + 8);
        ix = jm & (nside - 1);
        iy = nside - (jp & (nside - 1)) - 1;
    } else {
        const int64_t ntt = std::min<int64_t>(static_cast<int64_t>(tt), 3);
        const double tp = tt - ntt, tmp = nside * std::sqrt(3 * (1 - za));
        const int64_t jp = std::min<int64_t>(static_cast<int64_t>(tp * tmp), nside - 1), jm = std::min<int64_t>(static_cast<int64_t>((1 - tp) * tmp), nside - 1);
        if (z >= 0) { face = ntt; ix = nside - jm - 1; iy = nside - jp - 1; }
        else { face = ntt + 8; ix = jp; iy = jm; }
    }
    return static_cast<uint64_t>(face * nside * nside) + spread(static_cast<uint64_t>(ix)) + 2 * spread(static_cast<uint64_t>(iy));
}
const double G[3][3] = {{-0.0548755604162154, -0.8734370902348850, -0.4838350155487132},
                        {+0.4941094278755837, -0.4448296299600112, +0.7469822444972189},
                        {-0.8676661490190047, -0.1980763734312015, +0.4559837761750669}};
// Galactique (l, b en degrés) vers écliptique J2000 (repère de l'appli).
Vec3 galToEcl(double l, double b) {
    l *= kPi / 180;
    b *= kPi / 180;
    const double g[3] = {std::cos(b) * std::cos(l), std::cos(b) * std::sin(l), std::sin(b)};
    double e[3];
    for (int i = 0; i < 3; ++i) e[i] = G[0][i] * g[0] + G[1][i] * g[1] + G[2][i] * g[2];      // transposée : galactique -> équatorial
    const double eps = 84381.406 / 3600.0 * kPi / 180.0;
    return {e[0], std::cos(eps) * e[1] + std::sin(eps) * e[2], -std::sin(eps) * e[1] + std::cos(eps) * e[2]};
}
}  // namespace

int main(int argc, char** argv) {
    if (argc < 3) fail("usage : essai_ciel <ciel_x.bin> <image.ppm> [--vers l,b] [--champ degres] [--taille LxH] [--camera x,y,z]");
    double l0 = 0, b0 = 0, fov = 90;
    uint32_t width = 1920, height = 1080;
    Vec3 eye{0, 0, 0};
    for (int i = 3; i + 1 < argc; i += 2) {
        const std::string k = argv[i];
        if (k == "--vers") std::sscanf(argv[i + 1], "%lf,%lf", &l0, &b0);
        else if (k == "--champ") fov = std::atof(argv[i + 1]);
        else if (k == "--taille") std::sscanf(argv[i + 1], "%ux%u", &width, &height);
        else if (k == "--camera") std::sscanf(argv[i + 1], "%lf,%lf,%lf", &eye.x, &eye.y, &eye.z);
        else fail("option inconnue : " + k);
    }
    SkyBandInfo info;
    std::streamoff off = 0;
    if (!readSkyBandHeader(argv[1], info, off)) fail("carte du ciel illisible");
    std::printf("%s : Nside %u, repere %s, couverture %.2f %%, echelle %s %.4g a %.4g %s\n", info.label.c_str(), info.nside,
                info.galactic ? "galactique" : "equatorial", info.coverage * 100, info.scaleKind.c_str(), info.lo, info.hi, info.unit.c_str());

    // Valeurs lues par le processeur dans des directions connues (à comparer à la littérature du relevé).
    {
        std::ifstream f(argv[1], std::ios::binary);
        struct Dir { const char* name; double l, b; };
        const Dir dirs[] = {{"Centre galactique (l 0, b 0)", 0, 0}, {"Cassiopee A (l 111,74, b -2,13)", 111.74, -2.13},
                            {"Cygnus A (l 76,19, b 5,76)", 76.19, 5.76}, {"Pole nord galactique (b 90)", 0, 90},
                            {"Pole sud galactique (b -90)", 0, -90}, {"Anticentre (l 180, b 0)", 180, 0},
                            {"Grand Nuage de Magellan (l 280,47, b -32,89)", 280.47, -32.89}};
        for (const Dir& d : dirs) {
            double v[3];
            const double lr = d.l * kPi / 180, br = d.b * kPi / 180;
            const double g[3] = {std::cos(br) * std::cos(lr), std::cos(br) * std::sin(lr), std::sin(br)};
            if (info.galactic) for (int i = 0; i < 3; ++i) v[i] = g[i];
            else for (int i = 0; i < 3; ++i) v[i] = G[0][i] * g[0] + G[1][i] * g[1] + G[2][i] * g[2];
            const uint64_t p = ang2pixNest(info.nside, v[0], v[1], v[2]);
            float val = 0;
            f.seekg(off + static_cast<std::streamoff>(p * 4));
            f.read(reinterpret_cast<char*>(&val), 4);
            std::printf("  %-46s pixel %llu : %.5g %s\n", d.name, static_cast<unsigned long long>(p), static_cast<double>(val), info.unit.c_str());
        }
    }

    const Gpu g = createGpu();
    SkyBandRenderer sky;
    sky.create(g, HdrTarget::kFormat);
    auto t0 = std::chrono::steady_clock::now();
    if (!sky.load(g, argv[1])) fail("chargement de la carte");
    std::printf("chargee en %.2f s\n", std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
    for (const auto& s : sky.legend(std::sqrt(eye.x * eye.x + eye.y * eye.y + eye.z * eye.z)))
        if (s.rfind("Tuiles fines", 0) != 0) std::printf("  | %s\n", s.c_str());      /* état des tuiles : après leur lecture */

    HdrTarget target;
    target.create(g, width, height, VK_IMAGE_USAGE_TRANSFER_SRC_BIT);
    const VkDeviceSize imgBytes = static_cast<VkDeviceSize>(width) * height * 8;
    Buffer readback = createBuffer(g, imgBytes, VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    const Vec3 d = galToEcl(l0, b0);
    // « haut » de l'image : le pôle nord galactique, pour que le plan de la Galaxie soit horizontal
    Camera cam = lookAt(eye, Vec3{eye.x + d.x, eye.y + d.y, eye.z + d.z}, fov, static_cast<double>(width) / height);
    const Vec3 ngp = galToEcl(0, 90);
    cam.right = unit(cross(cam.fwd, ngp));
    cam.up = cross(cam.right, cam.fwd);
    {      // tuiles fines (s'il y en a) : toutes celles de la vue, avant de dessiner
        auto t1 = std::chrono::steady_clock::now();
        sky.requestTiles(cam, width, height, true);
        std::printf("tuiles fines lues en %.2f s\n", std::chrono::duration<double>(std::chrono::steady_clock::now() - t1).count());
        for (const auto& s : sky.legend(std::sqrt(eye.x * eye.x + eye.y * eye.y + eye.z * eye.z)))
            if (s.rfind("Tuiles fines", 0) == 0 || s.rfind("Haut de l'échelle", 0) == 0) std::printf("  | %s\n", s.c_str());
    }
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
    sky.draw(cmd, cam, width, height);
    vkCmdEndRendering(cmd);
    transition(cmd, target.image, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
               VK_ACCESS_TRANSFER_READ_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT);
    VkBufferImageCopy region{};
    region.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
    region.imageExtent = {width, height, 1};
    vkCmdCopyImageToBuffer(cmd, target.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, readback.buf, 1, &region);
    endOnce(g, cmd);

    void* mapped = nullptr;
    check(vkMapMemory(g.dev, readback.mem, 0, imgBytes, 0, &mapped), "lecture de l'image");
    const auto* h16 = static_cast<const uint16_t*>(mapped);
    std::vector<uint8_t> rgb(static_cast<size_t>(width) * height * 3);
    for (size_t i = 0; i < static_cast<size_t>(width) * height; ++i)
        for (int k = 0; k < 3; ++k) {
            const float c = halfToFloat(h16[i * 4 + k]);
            const float v = c / (1.0f + c);      // même passage que ecran.frag (Reinhard puis sRGB)
            const float s = v <= 0.0031308f ? 12.92f * v : 1.055f * std::pow(v, 1.0f / 2.4f) - 0.055f;
            rgb[i * 3 + k] = static_cast<uint8_t>(std::lround(255.0f * std::clamp(s, 0.0f, 1.0f)));
        }
    vkUnmapMemory(g.dev, readback.mem);
    std::ofstream out(argv[2], std::ios::binary);
    out << "P6\n" << width << " " << height << "\n255\n";
    out.write(reinterpret_cast<const char*>(rgb.data()), static_cast<std::streamsize>(rgb.size()));
    std::printf("image ecrite : %s\n", argv[2]);
    destroy(g, readback);
    target.release(g);
    sky.release(g);
    return 0;
}
