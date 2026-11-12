// Appli PC « Univers » : la fenêtre du simulateur.
//
// Chaque image : (1) les étoiles sont additionnées dans une image en grande dynamique ; (2) cette image est
// convertie pour l'écran et l'interface (interface.h) est dessinée par-dessus, dans une image finale ;
// (3) l'image finale est copiée dans la fenêtre. En contrôle (`--fenetre-test`), la fenêtre reste cachée et
// l'image finale peut être écrite dans un fichier (`--capture`) : c'est exactement ce que Marc verrait.
#include <imgui.h>
#include <imgui_impl_vulkan.h>
#include <imgui_impl_win32.h>

#include "asteroides.h"
#include "fenetre.h"
#include "fusion_points.h"
#include "galaxies.h"
#include "interface.h"
#include "points_planetes.h"
#include "spheres.h"
#include "rendu_fenetre.h"

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

namespace {

struct Input {
    bool dragging = false, resized = false, quit = false, home = false, space = false;
    int lastX = 0, lastY = 0;
    double dragX = 0, dragY = 0, wheel = 0;
    bool touched = false;
};

LRESULT CALLBACK wndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    if (ImGui::GetCurrentContext() && ImGui_ImplWin32_WndProcHandler(hwnd, msg, wp, lp)) return 1;
    auto* in = reinterpret_cast<Input*>(GetWindowLongPtrA(hwnd, GWLP_USERDATA));
    if (!in) return DefWindowProcA(hwnd, msg, wp, lp);
    const bool uiMouse = ImGui::GetCurrentContext() && ImGui::GetIO().WantCaptureMouse;
    const bool uiKeys = ImGui::GetCurrentContext() && ImGui::GetIO().WantCaptureKeyboard;
    switch (msg) {
        case WM_CLOSE: in->quit = true; return 0;
        case WM_SIZE: in->resized = true; return 0;
        case WM_KEYDOWN:
            if (wp == VK_ESCAPE && !uiKeys) in->quit = true;      // dans la recherche ou un menu, Échap ferme d'abord la recherche ou le menu
            if (!uiKeys && wp == VK_HOME) in->home = true;
            if (!uiKeys && wp == VK_SPACE && !(lp & (1 << 30))) in->space = true;
            in->touched = true;
            return 0;
        case WM_KILLFOCUS: in->dragging = false; return 0;
        case WM_LBUTTONDOWN:
            if (uiMouse) return 0;
            in->dragging = true;
            in->touched = true;
            in->lastX = static_cast<short>(LOWORD(lp));
            in->lastY = static_cast<short>(HIWORD(lp));
            SetCapture(hwnd);
            return 0;
        case WM_LBUTTONUP:
            in->dragging = false;
            ReleaseCapture();
            return 0;
        case WM_MOUSEMOVE:
            if (in->dragging) {
                const int x = static_cast<short>(LOWORD(lp)), y = static_cast<short>(HIWORD(lp));
                in->dragX += x - in->lastX;
                in->dragY += y - in->lastY;
                in->lastX = x;
                in->lastY = y;
            }
            return 0;
        case WM_MOUSEWHEEL:
            if (!uiMouse) {
                in->wheel += GET_WHEEL_DELTA_WPARAM(wp) / 120.0;
                in->touched = true;
            }
            return 0;
        default: return DefWindowProcA(hwnd, msg, wp, lp);
    }
}

void imguiCheck(VkResult r) {
    if (r != VK_SUCCESS) fail("interface (Dear ImGui)", r);
}

void pumpMessages() {
    MSG msg;
    while (PeekMessageA(&msg, nullptr, 0, 0, PM_REMOVE)) {
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }
}

}  // namespace

int runWindow(const WindowOptions& opt) {
    const bool test = opt.testFrames > 0;
    gWindowMode = !test;      // dès le début : même un fichier d'étoiles absent est dit à l'écran
    const Stars stars = openStars(opt.starsPath.c_str());

    // Les données sont rangées à côté du fichier d'étoiles : noms des étoiles, éphémérides de la NASA.
    const size_t cut = opt.starsPath.find_last_of("\\/");
    const std::string dataDir = cut == std::string::npos ? std::string(".") : opt.starsPath.substr(0, cut);
    eph::Set spk;
    std::string spkError;
    const bool hasSpk = spk.add(dataDir + "/de440.bsp", spkError);      // absent : le simulateur le dit à l'écran et montre les étoiles
    if (hasSpk)      // lunes : chaque fichier présent ajoute les siennes ; un fichier absent ne bloque rien
        for (const char* f : {"mar099s.bsp", "jup365.bsp", "sat441.bsp", "nep097.bsp", "plu060.bsp"}) {
            std::string ignored;
            spk.add(dataDir + "/" + f, ignored);
        }
    std::vector<sondes::Probe> probes;
    const bool hasProbes = sondes::load(dataDir + "/sondes.bin", probes);      // facultatif
    Sim sim;
    sim.probes = hasProbes ? &probes : nullptr;
    sim.stars = &stars;
    sim.spk = hasSpk ? &spk : nullptr;
    // Système solaire hors de la plage de la NASA : préparé dans un fil à part (quelques dizaines de secondes), branché
    // dès qu'il est prêt. En attendant, hors de 1550-2650, les planètes restent cachées et l'écran le dit.
    phys::SystemeSolaire outer;
    std::atomic<bool> outerReady{false};
    std::thread outerThread;
    if (hasSpk)
        outerThread = std::thread([&]() {
            const phys::SourceDe440 source = [&](int naif, double jd, phys::Vec3& p, phys::Vec3& v) {
                eph::Vec a, w;
                if (!spk.state(naif, eph::etOfJd(jd), a, w)) return false;
                a = eph::toEcliptic(a);
                w = eph::toEcliptic(w);
                p = {a.x, a.y, a.z};
                v = {w.x, w.y, w.z};
                return true;
            };
            if (outer.construire(source, 20000.0)) {
                outer.chargerTable(dataDir + "/orbites_planetes.bin");      // facultatif : au-delà de ±20 000 ans
                outerReady = true;
            }
        });
    sim.loadBodies(dataDir + "/etoiles_noms.tsv", dataDir + "/galaxies_noms.tsv", dataDir + "/planetes.tsv", dataDir + "/lunes.tsv");
    if (!opt.target.empty()) {
        bool found = false;
        for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
            if (sim.bodies[static_cast<size_t>(i)].name == opt.target) {
                sim.focus = i;
                found = true;
            }
        if (!found) fail("--cible : astre inconnu : " + opt.target);
    }
    // Calcul complet de la rencontre avec Andromède (dossier fusion/ à côté des données) : facultatif.
    phys::fusion::Rejeu replay;
    const bool hasReplay = replay.charger(dataDir + "/fusion/fusion_centres.bin", dataDir + "/fusion");
    sim.linkReplay(hasReplay ? &replay : nullptr, dataDir + "/fusion/fusion_noms.tsv");
    if (opt.hasYears) sim.years = opt.years;
    sim.refreshEphemeris();
    if (sim.focus != 0) sim.follow(sim.focus);
    if (opt.dist > 0) sim.dist = opt.dist;
    if (test) {
        sim.paused = true;
        sim.touched = true;      // contrôle : image fixe, reproductible
    }

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
        // fenêtre réduite, sans surface à dessiner). Le second s'applique toujours. En contrôle, rien ne s'ouvre.
        ShowWindow(hwnd, SW_SHOWMAXIMIZED);
        ShowWindow(hwnd, SW_SHOWMAXIMIZED);
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
        pumpMessages();
        if (input.quit) return 0;
        Sleep(50);
    }
    StarRenderer sr;
    sr.create(g, stars, HdrTarget::kFormat);
    PlanetPoints planets;
    planets.create(g);
    GalaxyFile galaxyFile;
    GalaxyRenderer galaxies;
    if (openGalaxies(dataDir + "/galaxies.bin", galaxyFile)) galaxies.create(g, galaxyFile, HdrTarget::kFormat);
    AsteroidRenderer asteroids;
    asteroids.create(g, dataDir + "/asteroides.bin", HdrTarget::kFormat);
    sim.asteroidEpochJd = asteroids.ready ? asteroids.epochJd : 0;
    sim.asteroidCount = asteroids.ready ? asteroids.count : 0;
    FusionPoints fusionPoints;
    fusionPoints.create(g, hasReplay ? static_cast<uint32_t>(replay.nombreEtoiles()) : 0);
    double galaxyScaleAt = 1e300;      // date (années) du dernier calcul du facteur d'échelle de l'univers
    SphereRenderer spheres;
    spheres.create(g, HdrTarget::kFormat, dataDir + "/textures");
    std::vector<bool> asSphere;
    if (test)      // contrôle : on attend les cartes de surface, pour une image reproductible
        for (int tries = 0; tries < 3000 && !spheres.allLoaded(); ++tries) {
            spheres.uploadPending(g);
            Sleep(10);
        }
    Target hdr, final;
    auto createTargets = [&]() {
        hdr.create(g, HdrTarget::kFormat, sc.extent, VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_SAMPLED_BIT);
        final.create(g, kFinalFormat, sc.extent, VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT);
    };
    createTargets();
    ScreenPass screen;
    screen.create(g);
    screen.bindSource(g, hdr.view);

    // Interface.
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGui::GetIO().IniFilename = nullptr;      // aucun fichier de réglages écrit sur le disque
    UiState ui;
    loadFonts(ui.normal, ui.big);
    applyStyle();
    ImGui_ImplWin32_Init(hwnd);
    const VkDescriptorPoolSize uiPoolSize{VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 16};
    VkDescriptorPoolCreateInfo uiPoolInfo{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
    uiPoolInfo.flags = VK_DESCRIPTOR_POOL_CREATE_FREE_DESCRIPTOR_SET_BIT;
    uiPoolInfo.maxSets = 16;
    uiPoolInfo.poolSizeCount = 1;
    uiPoolInfo.pPoolSizes = &uiPoolSize;
    VkDescriptorPool uiPool;
    check(vkCreateDescriptorPool(g.dev, &uiPoolInfo, nullptr, &uiPool), "réserve de l'interface");
    ImGui_ImplVulkan_InitInfo ii{};
    ii.Instance = g.instance;
    ii.PhysicalDevice = g.pd;
    ii.Device = g.dev;
    ii.QueueFamily = g.family;
    ii.Queue = g.queue;
    ii.DescriptorPool = uiPool;
    ii.MinImageCount = 2;
    ii.ImageCount = 2;
    ii.MSAASamples = VK_SAMPLE_COUNT_1_BIT;
    ii.UseDynamicRendering = true;
    ii.PipelineRenderingCreateInfo = {VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO};
    ii.PipelineRenderingCreateInfo.colorAttachmentCount = 1;
    ii.PipelineRenderingCreateInfo.pColorAttachmentFormats = &kFinalFormat;
    ii.CheckVkResultFn = imguiCheck;
    if (!ImGui_ImplVulkan_Init(&ii)) fail("interface (Dear ImGui)");

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

    auto rebuild = [&]() {
        vkDeviceWaitIdle(g.dev);
        destroySwapchain(g, sc);
        hdr.release(g);
        final.release(g);
        if (!createSwapchain(g, surface, test, sc)) return false;
        createTargets();
        screen.bindSource(g, hdr.view);
        return true;
    };

    if (test && hasSpk && !sim.ephemValid && outerThread.joinable()) {      // contrôle à une date hors de la plage de la NASA : on attend le calcul
        outerThread.join();
        if (outerReady) sim.outer = &outer;
        sim.refreshEphemeris();
        if (!opt.target.empty())      // l'astre demandé n'avait pas encore de position : on le suit maintenant
            for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
                if (sim.bodies[static_cast<size_t>(i)].name == opt.target && sim.visible(i)) {
                    sim.follow(i);
                    if (opt.dist > 0) sim.dist = opt.dist;
                }
    }
    if (opt.hasView) {
        sim.yaw = opt.yawDeg * kPi / 180.0;
        sim.pitch = opt.pitchDeg * kPi / 180.0;
    }
    auto last = std::chrono::steady_clock::now();
    const auto start = last;
    int frame = 0, shown = 0;
    double titleTimer = 0;
    bool drawable = true;
    while (!input.quit) {
        pumpMessages();
        if (input.resized || !drawable) {
            input.resized = false;
            drawable = rebuild();
            if (!drawable) {
                Sleep(50);
                continue;
            }
        }
        const auto now = std::chrono::steady_clock::now();
        const double dt = std::min(0.1, std::chrono::duration<double>(now - last).count());
        last = now;

        // Gestes -> simulateur.
        if (input.touched) sim.touched = true;
        sim.orbit(input.dragX, input.dragY);
        sim.zoom(input.wheel);
        input.dragX = input.dragY = input.wheel = 0;
        if (input.space) sim.paused = !sim.paused;
        if (input.home) sim.follow(0);
        input.space = input.home = false;
        if (!sim.outer && outerReady) sim.outer = &outer;
        sim.advance(dt);
        const Camera cam = sim.camera(static_cast<double>(sc.extent.width) / sc.extent.height);
        const PushConstants pc = pushConstants(cam, kExposure * static_cast<float>(sim.brightnessBoost()), sc.extent.height, sim.years);

        vkWaitForFences(g.dev, 1, &fence, VK_TRUE, UINT64_MAX);
        // Distances des galaxies des relevés : recalculées quand la cosmologie change, et quand la date s'éloigne
        // d'aujourd'hui (l'univers grandit : facteur d'échelle calculé, mis à jour tous les millions d'années).
        if (sim.cosmologyDirty || std::fabs(sim.years - galaxyScaleAt) > 1.0e6) {
            galaxies.setCosmology(sim.cosmology, cosmo::scaleFactorAt(sim.cosmology, (sim.years - kStartYears) / 1.0e9));
            galaxyScaleAt = sim.years;
            sim.cosmologyDirty = false;
        }
        fusionPoints.update(sim, cam, pc.par[0]);
        spheres.uploadPending(g);      // au plus une carte de surface par image, dès qu'elle est décodée
        spheres.prepare(sim, cam, sc.extent.width, sc.extent.height, asSphere);
        planets.update(sim, cam, asSphere);

        ImGui_ImplVulkan_NewFrame();
        ImGui_ImplWin32_NewFrame();
        if (test) ImGui::GetIO().DisplaySize = {static_cast<float>(sc.extent.width), static_cast<float>(sc.extent.height)};
        ImGui::NewFrame();
        const int clicked = drawInterface(sim, ui, cam, static_cast<float>(sc.extent.width), static_cast<float>(sc.extent.height));
        if (clicked >= 0) {
            sim.follow(clicked);
            sim.touched = true;
        }
        ImGui::Render();

        vkWaitForFences(g.dev, 1, &fence, VK_TRUE, UINT64_MAX);
        uint32_t index = 0;
        const VkResult ar = vkAcquireNextImageKHR(g.dev, sc.chain, UINT64_MAX, acquired, VK_NULL_HANDLE, &index);
        if (ar == VK_ERROR_OUT_OF_DATE_KHR) {
            input.resized = true;
            continue;
        }
        if (ar != VK_SUCCESS && ar != VK_SUBOPTIMAL_KHR) fail("image d'écran", ar);
        vkResetFences(g.dev, 1, &fence);

        vkResetCommandBuffer(cmd, 0);
        VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        vkBeginCommandBuffer(cmd, &begin);
        // 1. Les étoiles, en grande dynamique.
        transition(cmd, hdr.image, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, 0, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                   VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT);
        beginPass(cmd, hdr.view, sc.extent);
        galaxies.draw(cmd, cam, sc.extent.width, sc.extent.height, static_cast<float>(sim.galaxyGain()), static_cast<float>(25.0 * sim.dist));
        if (!sim.deepTime()) sr.draw(cmd, pc, sc.extent.width, sc.extent.height);      // étoiles mesurées : à moins de 3 millions d'années d'aujourd'hui
        if (fusionPoints.count) {
            PushConstants still = pc;      // les étoiles du calcul sont déjà à leur place : pas de mouvement propre à ajouter
            still.par[2] = 0;
            sr.bind(cmd, still, sc.extent.width, sc.extent.height);
            fusionPoints.draw(cmd);
        }
        asteroids.draw(cmd, cam, {cam.pos.x / kAuInLy, cam.pos.y / kAuInLy, cam.pos.z / kAuInLy}, 2451545.0 + sim.years * 365.25 - asteroids.epochJd,
                       sc.extent.width, sc.extent.height, asteroids.ready ? static_cast<float>(sim.asteroidGain(asteroids.epochJd)) : 0.0f);
        // (l'ordre compte : après les astéroïdes, le dessin des étoiles n'est plus lié ; les planètes le relient)
        sr.bind(cmd, pc, sc.extent.width, sc.extent.height);
        planets.draw(cmd);
        spheres.draw(cmd, sc.extent.width, sc.extent.height);
        vkCmdEndRendering(cmd);
        transition(cmd, hdr.image, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                   VK_ACCESS_SHADER_READ_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        // 2. Conversion pour l'écran, puis l'interface par-dessus.
        transition(cmd, final.image, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, 0, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                   VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT);
        beginPass(cmd, final.view, sc.extent);
        screen.draw(cmd, sc.extent);
        ImGui_ImplVulkan_RenderDrawData(ImGui::GetDrawData(), cmd);
        vkCmdEndRendering(cmd);
        // 3. Copie dans la fenêtre.
        transition(cmd, final.image, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                   VK_ACCESS_TRANSFER_READ_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT);
        transition(cmd, sc.images[index], VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 0, VK_ACCESS_TRANSFER_WRITE_BIT,
                   VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT);
        VkImageBlit blit{};
        blit.srcSubresource = blit.dstSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
        blit.srcOffsets[1] = blit.dstOffsets[1] = {static_cast<int32_t>(sc.extent.width), static_cast<int32_t>(sc.extent.height), 1};
        vkCmdBlitImage(cmd, final.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, sc.images[index], VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &blit, VK_FILTER_NEAREST);
        transition(cmd, sc.images[index], VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_PRESENT_SRC_KHR, VK_ACCESS_TRANSFER_WRITE_BIT, 0,
                   VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT);
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
        if (!test && titleTimer > 0.5) {
            char title[120];
            std::snprintf(title, sizeof(title), "Univers  |  %.0f images par seconde", shown / titleTimer);
            SetWindowTextA(hwnd, title);
            titleTimer = 0;
            shown = 0;
        }
        if (test && frame >= opt.testFrames) break;
    }
    vkDeviceWaitIdle(g.dev);
    if (outerThread.joinable()) outerThread.join();
    if (test) {
        const double total = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        if (!opt.capture.empty()) writeCapture(g, final, sc.extent, opt.capture);
        std::printf("fenetre cachee %ux%u : %d images en %.3f s, soit %.1f images par seconde ; astre suivi : %s ; date : %s ; ephemerides : %s\nPASSE\n",
                    sc.extent.width, sc.extent.height, frame, total, frame / total, sim.bodies[static_cast<size_t>(sim.focus)].name.c_str(),
                    frDate(sim.years).c_str(), !hasSpk ? spkError.c_str() : sim.ephemValid ? "lues" : "hors plage");
    }

    ImGui_ImplVulkan_Shutdown();
    ImGui_ImplWin32_Shutdown();
    ImGui::DestroyContext();
    vkDestroyDescriptorPool(g.dev, uiPool, nullptr);
    vkDestroyFence(g.dev, fence, nullptr);
    vkDestroySemaphore(g.dev, acquired, nullptr);
    vkDestroySemaphore(g.dev, rendered, nullptr);
    screen.release(g);
    planets.release(g);
    fusionPoints.release(g);
    asteroids.release(g);
    galaxies.release(g);
    spheres.release(g);
    sr.release(g);
    hdr.release(g);
    final.release(g);
    destroySwapchain(g, sc);
    vkDestroySurfaceKHR(g.instance, surface, nullptr);
    vkDestroyCommandPool(g.dev, g.pool, nullptr);
    vkDestroyDevice(g.dev, nullptr);
    vkDestroyInstance(g.instance, nullptr);
    DestroyWindow(hwnd);
    return 0;
}
