// Appli PC « Univers » : la fenêtre du simulateur.
//
// Chaque image : (1) les étoiles sont additionnées dans une image en grande dynamique ; (2) cette image est
// convertie pour l'écran et l'interface (interface.h) est dessinée par-dessus, dans une image finale ;
// (3) l'image finale est copiée dans la fenêtre. En contrôle (`--fenetre-test`), la fenêtre reste cachée et
// l'image finale peut être écrite dans un fichier (`--capture`) : c'est exactement ce que Marc verrait.
#include <chrono>
#include <imgui.h>
#include <imgui_impl_vulkan.h>
#include <imgui_impl_win32.h>

#include "asteroides.h"
#include "ciel_bandes.h"
#include "clones.h"
#include "fenetre.h"
#include "orbites_gpu.h"
#include "fusion_nuage.h"
#include "fusion_points.h"
#include "gaia.h"
#include "gaia_ciel.h"
#include "gaia_points.h"
#include "galaxies.h"
#include "interface.h"
#include "points_planetes.h"
#include "galaxies_naines.h"
#include "trous_noirs.h"
#include "exoplanetes.h"
#include "spheres.h"
#include "cycle_nebuleuse.h"
#include "traceurs_bras.h"
#include "voie_lactee.h"
#include "galaxies_formes.h"
#include "galaxies_pose.h"
#include "structures.h"
#include "chrono.h"
#include "vieillissement.h"
#include "film_etoiles.h"
#include "film_carte.h"
#include "rendu_fenetre.h"
#include "pose_auto.h"
#include "chargement.h"
#include "nebuleuses.h"

using namespace univers;      // en-têtes de l'appli (natif/src), autrefois en espace de noms anonyme

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

namespace {

struct Input {
    bool dragging = false, resized = false, quit = false, home = false, space = false;
    int lastX = 0, lastY = 0;
    double dragX = 0, dragY = 0, wheel = 0, wheelField = 0;      // wheelField : Ctrl + molette (champ de vision)
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
                (GET_KEYSTATE_WPARAM(wp) & MK_CONTROL ? in->wheelField : in->wheel) += GET_WHEEL_DELTA_WPARAM(wp) / 120.0;
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

// Nom sans accents, pour --cible depuis une console qui ne passe pas les accents (« Centre de la Voie lactee »).
static std::string sansAccents(const std::string& t) {
    static const char* const from[] = {"é", "è", "ê", "ë", "à", "â", "î", "ï", "ô", "û", "ù", "ç", "É"};
    static const char* const to[] = {"e", "e", "e", "e", "a", "a", "i", "i", "o", "u", "u", "c", "E"};
    std::string out = t;
    for (size_t k = 0; k < sizeof(from) / sizeof(from[0]); ++k)
        for (size_t at = out.find(from[k]); at != std::string::npos; at = out.find(from[k], at)) out.replace(at, std::strlen(from[k]), to[k]);
    return out;
}

int runWindow(const WindowOptions& opt) {
    const bool test = opt.testFrames > 0;
    gWindowMode = !test;      // dès le début : même un fichier d'étoiles absent est dit à l'écran
    chargement::Ecran ecran;      // écran de chargement (chargement.h) : rien ne s'ouvre en contrôle
    ecran.ouvrir(!test);
    ecran.etape(L"Catalogue d'étoiles", 0.01f);
    const Stars stars = openStars(opt.starsPath.c_str());

    // Les données sont rangées à côté du fichier d'étoiles : noms des étoiles, éphémérides de la NASA.
    const size_t cut = opt.starsPath.find_last_of("\\/");
    const std::string dataDir = cut == std::string::npos ? std::string(".") : opt.starsPath.substr(0, cut);
    eph::Set spk;
    std::string spkError;
    ecran.etape(L"Éphémérides de la NASA", 0.04f);
    const bool hasSpk = spk.add(dataDir + "/de440.bsp", spkError);      // absent : le simulateur le dit à l'écran et montre les étoiles
    if (hasSpk)      // lunes : chaque fichier présent ajoute les siennes ; un fichier absent ne bloque rien
        for (const char* f : {"mar099s.bsp", "jup365.bsp", "sat441.bsp", "nep097.bsp", "plu060.bsp",      // grandes lunes
                              "ura184_part-3.bsp", "ura116xl.bsp", "sat415.bsp", "nep104.bsp", "nep105.bsp",      // lunes d'Uranus, petites lunes proches
                              "jup347.bsp", "jup348.bsp", "jup349.bsp", "sat455.bsp", "sat456.bsp", "sat457.bsp", "sat459.bsp"}) {      // lunes lointaines
            std::string ignored;
            spk.add(dataDir + "/" + f, ignored);
        }
    std::vector<sondes::Probe> probes;
    const bool hasProbes = sondes::load(dataDir + "/sondes.bin", probes);      // facultatif
    asteroides::Catalogue asteroidCat;
    const bool hasAsteroidCat = asteroidCat.load(dataDir + "/asteroides.bin", dataDir + "/asteroides_noms.txt");      // facultatif
    Sim sim;
    sim.asteroidCat = hasAsteroidCat ? &asteroidCat : nullptr;
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
            // Réserve sur disque (quelques millisecondes) ; sinon le calcul (une quinzaine de secondes), gardé pour la fois suivante.
            const std::string reserve = dataDir + "/reserve_systeme_solaire.bin";
            if (outer.chargerReserve(reserve, source, 20000.0) || (outer.construire(source, 20000.0) && (outer.sauver(reserve), true))) {
                outer.chargerTable(dataDir + "/orbites_planetes.bin");      // facultatif : au-delà de ±20 000 ans
                outerReady = true;
            }
        });
    gFiches.demarrer(dataDir);      // fiches complètes des astres (fiches/*.tsv), lues en tâche de fond
    ecran.etape(L"Planètes, lunes, étoiles et galaxies nommées", 0.08f);
    sim.loadBodies(dataDir + "/etoiles_noms.tsv", dataDir + "/galaxies_noms.tsv", dataDir + "/planetes.tsv", dataDir + "/lunes.tsv");
    // Cycle de vie du Soleil et des étoiles nommées (cycle_appli.h) : facultatif, sans vie_cycle.bin rien ne change.
    static CycleAppli cycleApp;
    cycleApp.build(dataDir + "/vie_cycle.bin", sim, dataDir + "/etoiles_cycle.tsv");
    gCycle = &cycleApp;
    loadGravWaves(dataDir + "/ondes_gravitationnelles.tsv");
    sim.chaosRun.load(dataDir + "/chaos_futur_60ma.bin");      // orbite de la Terre de 10 à 60 millions d'années (fil physique)      // ondes gravitationnelles (GWOSC) : fenêtre ouverte depuis « Aller à »
    if (!opt.target.empty()) {
        bool found = false;
        for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
            if (sim.bodies[static_cast<size_t>(i)].name == opt.target || sansAccents(sim.bodies[static_cast<size_t>(i)].name) == opt.target) {
                sim.focus = i;
                found = true;
            }
        if (!found && sim.asteroidCat) {      // sinon : un astéroïde du catalogue (ex. Ceres)
            const std::vector<int> k = sim.asteroidCat->search(opt.target, 50);
            int pick = k.empty() ? -1 : k[0];
            for (int c : k)      // une comète passe devant un astéroïde du même nom (1P/Halley avant Halley (2688))
                if (sim.asteroidCat->isComet(static_cast<size_t>(c))) {
                    pick = c;
                    break;
                }
            const int body = pick < 0 ? -1 : sim.selectAsteroid(pick);
            if (body >= 0) {
                sim.focus = body;
                found = true;
            }
        }
        if (!found) fail("--cible : astre inconnu : " + opt.target);
    }
    // Calcul complet de la rencontre avec Andromède (dossier fusion/ à côté des données) : facultatif.
    phys::fusion::Rejeu replay;
    // Calcul de la fusion : celui à 3 millions de particules (dossier fusion-3m) s'il est là, sinon celui à 300 000.
    // Dans l'ordre : le calcul à un million d'étoiles affichées (fusion-toutes), celui à 3 millions de particules, le premier.
    const std::string fusionDir = dataDir + (std::filesystem::exists(dataDir + "/fusion-toutes/fusion_centres.bin") ? "/fusion-toutes"
                                             : std::filesystem::exists(dataDir + "/fusion-3m/fusion_centres.bin") ? "/fusion-3m" : "/fusion");
    const bool hasReplay = replay.charger(fusionDir + "/fusion_centres.bin", "");      // centres et traceurs ; les étoiles : fusion_nuage.h
    // Centres de référence des galaxies du Groupe local (centres_reference.h, PR 97) : chaque galaxie se déplace en bloc.
    CentresReference centresRef;
    if (centresRef.load(dataDir + "/centres_reference.bin")) sim.centres = &centresRef;
    sim.linkReplay(hasReplay ? &replay : nullptr, fusionDir + "/fusion_noms.tsv");
    if (sim.centres) {      // contrôle chiffré : place d'aujourd'hui des centres contre la place mesurée du catalogue
        for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i) {
            const int ci = CentresReference::indexOf(sim.bodies[static_cast<size_t>(i)].name);
            phys::Vec3 c;
            if (ci < 0 || !centresRef.centre(ci, 0.0, c)) continue;
            const Vec3 w = Sim::fromGalactocentric(c), f0 = sim.bodies[static_cast<size_t>(i)].fixedPos;
            const Vec3 d = w - f0;
            std::printf("centres de reference : %s a t = 0, ecart au catalogue %.3f kpc\n", sim.bodies[static_cast<size_t>(i)].name.c_str(), std::sqrt(dot(d, d)) / 3261.5637769);
        }
    }
    if (opt.hasYears) sim.years = opt.years;
    if (opt.fovDeg > 0) sim.fovDeg = std::clamp(opt.fovDeg, Sim::kFovMin, Sim::kFovMax);
    sim.refreshEphemeris();
    if (sim.focus != 0) sim.follow(sim.focus);
    if (opt.dist > 0) sim.dist = opt.dist;
    if (const char* vue = std::getenv("UNIVERS_VUE")) sim.bestLook = std::string(vue) == "meilleur";      // contrôle : vue choisie au départ
    if (test) {
        sim.paused = true;
        sim.touched = true;      // contrôle : image fixe, reproductible
    }
    bool pathActive = test && opt.hasPath && opt.hasYears;      // contrôle : aller à la date en laissant défiler le temps
    if (pathActive) {
        sim.years = opt.pathStart;
        sim.rate = std::clamp(opt.pathRate, 0, kRateCount - 1);
        sim.speed = opt.pathSpeed > 0 ? std::min(opt.pathSpeed, Sim::kMaxYearsPerSecond) : 0;
        sim.backward = opt.years < opt.pathStart;
        sim.paused = false;
        sim.refreshEphemeris();
    }
    int loops = 0;
    bool holdOn = false;             // la date demandée n'est pas encore calculée : la date montrée la rejoint
    double holdGoal = 0, lastShown = sim.years;

    Input input;
    WNDCLASSA wc{};
    wc.lpfnWndProc = wndProc;
    wc.hInstance = GetModuleHandleA(nullptr);
    wc.lpszClassName = "UniversFenetre";
    wc.hCursor = LoadCursorA(nullptr, IDC_ARROW);
    RegisterClassA(&wc);
    RECT r{0, 0, 1600, 900};
    if (const char* sz = std::getenv("UNIVERS_TAILLE"); sz && test) std::sscanf(sz, "%ldx%ld", &r.right, &r.bottom);      /* contrôle : taille de l'écran mesuré */
    AdjustWindowRect(&r, WS_OVERLAPPEDWINDOW, FALSE);
    HWND hwnd = CreateWindowExA(0, wc.lpszClassName, "Univers", WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, r.right - r.left, r.bottom - r.top, nullptr,
                                nullptr, wc.hInstance, nullptr);
    if (!hwnd) fail("création de la fenêtre");
    SetWindowLongPtrA(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(&input));

    ecran.etape(L"Carte graphique", 0.14f);
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
    // Étoiles Gaia (98 millions) et Voie lactée en volume (fil « Voie lactée et étoiles Gaia ») : facultatifs. Quand Gaia est
    // là, le dessin d'origine ne garde que le catalogue principal (Gaia en a retiré les doublons).
    ecran.etape(L"Étoiles Gaia : 98 millions, une par une", 0.20f);
    GaiaRenderer gaia;
    const bool gaiaOk = gaia.create(g, dataDir + "/gaia.bin", HdrTarget::kFormat);
    ecran.etape(L"Étoiles Gaia : 94 millions de plus", 0.36f);
    GaiaRenderer gaiaB;      // 93,9 M étoiles à parallaxe entre 5 et 10 erreurs (gaia_b.bin), si le fichier est là
    const bool gaiaBOk = gaiaOk && gaiaB.create(g, dataDir + "/gaia_b.bin", HdrTarget::kFormat, false);
    // Voie lactée faite d'étoiles (Marc, 13/11/2026 : « pas une image ») : 4 M étoiles visibles du modèle
    // (pipeline/natif/etoiles_visibles.py, contrat docs/contrat-etoiles-visibles.md), au format de Gaia : niveaux de
    // détail par l'arbre en huit, orbites exactes sur la carte graphique, sans lumière additionnée en double.
    ecran.etape(L"Voie lactée : étoiles du modèle", 0.50f);
    GaiaRenderer milkyWayStars;
    const bool milkyWayStarsOk = milkyWayStars.create(g, dataDir + "/vl_etoiles.bin", HdrTarget::kFormat, true, false);
    sim.milkyWayStarCount = milkyWayStarsOk ? milkyWayStars.count : 0;
    // Vieillissement de la lumière des étoiles du modèle (vieillissement.h) : facteurs par composante, 1 aujourd'hui.
    Vieillissement vieillissement;
    vieillissement.load(dataDir + "/vieillissement.tsv");
    if (milkyWayStarsOk) milkyWayStars.enableSubClouds(16);      // chaque traceur : 16 étoiles en s'approchant (gaia.vert)
    if (milkyWayStarsOk) milkyWayStars.enableCache(g);      /* précalcul par étoile du modèle (gaia_traceur.comp) */
    // Film du Groupe local (film_etoiles.h) : s'il est là, ces étoiles le suivent aux dates qu'il couvre.
    ecran.etape(L"Film de la rencontre avec Andromède", 0.62f);
    FilmStars filmStars;
    std::vector<float> filmStates;
    const bool filmStarsOk = milkyWayStarsOk && milkyWayStars.externalStatesFit() && filmStars.load(dataDir, milkyWayStars.starCount());
    if (filmStarsOk) sim.film = filmStars.vue();
    // Ancres des voisines (pipeline/natif/ancres_film.py) : le point que suivent l'étiquette et la caméra quand une galaxie se déchire.
    static FilmAnchors filmAnchors;
    // Ancres : calculées sur un film au format 2 (ancres_film.py) ; pas pour un film v3 (le centre écrit sert alors).
    if (filmStarsOk && !filmStars.v3 && filmAnchors.load(dataDir + "/film_ancres.bin", filmStars.film)) sim.anchors = &filmAnchors;
    std::printf("ancres des galaxies voisines dans le film : %s\n", sim.anchors ? "lues" : "absentes (centre ecrit par le calcul)");
    // Lumière entière des étoiles (vl_etoiles.lum) : sans elle, Gaia reste montré quand le film mène (revue F1).
    const bool filmLumOk = filmStarsOk && filmStars.loadLum(dataDir, "vl_etoiles.lum", [&](size_t i) { return milkyWayStars.starMagnitude(i); });
    std::printf("lumiere entiere des etoiles visibles : %s\n", filmLumOk ? "lue, Gaia cede au film loin d'aujourd'hui" : "absente, Gaia reste montre");
    std::printf("film du Groupe local : %s\n", filmStarsOk ? "lu, les etoiles visibles le suivent" : "absent ou incomplet, orbites de reference");
    // Andromède, Triangle, Nuages faits de leurs étoiles visibles (tirées des vraies photos, pipeline/natif/etoiles_visibles_photos.py),
    // autour d'aujourd'hui : sans orbite exacte (le potentiel de l'appli ne contient que la Voie lactée), elles s'effacent en
    // quelques millions d'années (gaia_fiable.glsl) et la photo déplacée en bloc prend le relais, sans double lumière.
    GaiaRenderer neighbourStars;
    // Avec le film du Groupe local, ces étoiles aussi suivent le calcul unique (leur état vient du film, jamais d'un calcul
    // d'orbites de l'appli) : il leur faut donc la table des états, d'où « full ». Sans film : le bloc qui tourne, comme avant.
    const bool neighbourFilmWanted = filmStarsOk && std::ifstream(dataDir + "/voisines_etoiles.ordre").good();
    const bool neighbourStarsOk = neighbourStars.create(g, dataDir + "/voisines_etoiles.bin", HdrTarget::kFormat, neighbourFilmWanted, false);
    if (neighbourStarsOk) neighbourStars.enableSubClouds(16);
    if (neighbourStarsOk) neighbourStars.enableCache(g);      /* précalcul par étoile du modèle (gaia_traceur.comp) */
    FilmStars filmNeighbours;
    std::vector<float> filmNeighbourStates;
    const bool filmNeighboursOk = neighbourFilmWanted && neighbourStarsOk && neighbourStars.externalStatesFit() &&
                                  filmNeighbours.load(dataDir, neighbourStars.starCount(), "voisines_etoiles.ordre", 1, 4);
    if (filmNeighboursOk) filmNeighbours.loadLum(dataDir, "voisines_etoiles.lum", [&](size_t i) { return neighbourStars.starMagnitude(i); });
    std::printf("film du Groupe local, galaxies voisines : %s\n", filmNeighboursOk ? "lu, leurs etoiles le suivent" : "non (bloc qui tourne)");
    // Film relu sur la carte graphique à la date exacte de chaque image (film_carte.h) : fluide, et le même résultat quelle
    // que soit la vitesse du temps. Sans lui (échec de création), l'ancien chemin par le processeur reste.
    FilmGpu filmGpu, filmGpuNeighbours;
    double filmGpuT = -1, filmGpuNeighboursT = -1;      // dernière date écrite sur la carte par le film (contrôle --controle-film)
    const bool filmGpuOk = filmStarsOk && filmGpu.create(g, filmStars, milkyWayStars.orbitsForFilm());
    const bool filmGpuNeighboursOk = filmNeighboursOk && filmGpuNeighbours.create(g, filmNeighbours, neighbourStars.orbitsForFilm());
    std::printf("film sur la carte graphique : %s\n", filmGpuOk ? "oui" : "non (relu par le processeur)");
    GaiaSkyTiles gaiaSky;      // 1,62 milliard de sources sans distance, lues à la demande sur le Drive (gaia_ciel.h)
    if (gaiaOk) gaiaSky.create(g, dataDir, HdrTarget::kFormat, gaia.colorBuffer());
    // Décision de Marc (13 novembre 2026, « je veux le plus proche possible de la réalité, pas seulement le mesuré ») : la
    // Galaxie entière est montrée dès aujourd'hui. Gaia ne mesure les distances que sur quelques milliers d'années-lumière ;
    // le reste de la lueur vient du modèle ajusté sur des mesures (docs/gaia-voie-lactee.md), qui ne garde que la lumière
    // qui manque aux étoiles dessinées une à une (gaia.bin + gaia_b.bin, voie_lactee.py). Montré en vue « réaliste »
    // (Sim::bestLook), éteint en vue « 100 % mesuré ».
    MilkyWayRenderer milkyWay;
    milkyWay.create(g, dataDir + "/voie_lactee.bin", HdrTarget::kFormat);
    // Poussière 3D pour les étoiles du modèle ; liée aussi aux jeux Gaia pour que tous les jeux de ressources soient
    // complets (leurs étoiles mesurées n'ont pas le drapeau 16 : elles ne la lisent pas).
    if (milkyWayStarsOk) milkyWayStars.attachDust(g, milkyWay.gridView(), milkyWay.gridSampler());
    if (gaiaOk) gaia.attachDust(g, milkyWay.gridView(), milkyWay.gridSampler());
    if (gaiaBOk) gaiaB.attachDust(g, milkyWay.gridView(), milkyWay.gridSampler());
    // Étoiles Gaia calculées dans une somme par pixel plutôt que tracées en points (gaia_points.h ; cadence, 20/11/2026) :
    // seulement avec UNIVERS_POINTS=calcul. Mesuré : à peine plus rapide carte libre (10 à 30 %), mais quand un autre
    // programme calcule sur la carte (le grand calcul), ce calcul-ci passe après lui et l'image tombe à 0,3 image/s contre 4
    // pour le tracé de points. Le tracé de points reste donc la règle.
    GaiaPointsSum gaiaSum;
    if (std::getenv("UNIVERS_POINTS") && std::string(std::getenv("UNIVERS_POINTS")) == "calcul") gaiaSum.create(g, HdrTarget::kFormat);
    if (neighbourStarsOk) neighbourStars.attachDust(g, milkyWay.gridView(), milkyWay.gridSampler());
    // Galaxies voisines faites de leurs étoiles (Marc, 13/11/2026 : « plus aucune galaxie en image ») : table par galaxie pour
    // gaia.vert (centre à t = 0 et à la date montrée, axe et vitesse de rotation) ; rang = ordre de etoiles_visibles_photos.py.
    // Axes : table unique (pipeline/constantes/univers.json) ; Petit Nuage : ligne de visée (pas d'axe mesuré).
    // vrot, rrot : courbe de rotation (km/s, kpc) ; agit : agitation / vitesse de rotation (mêmes valeurs que etoiles_visibles_photos.py)
    struct Voisine { const char* nom; double axe[3]; float vrot, rrot, agit; int body; Vec3 c0; };
    Voisine voisines[4] = {{"Andromède (M31)", {-0.4102, -0.7623, -0.5007}, 250.0f, 6.0f, 30.0f / 250.0f, -1, {}},
                           {"Galaxie du Triangle (M33)", {0.1886, 0.968, -0.1654}, 120.0f, 8.0f, 15.0f / 120.0f, -1, {}},
                           {"Grand Nuage de Magellan", {-0.2778, -0.949, -0.1489}, 92.0f, 4.0f, 20.0f / 92.0f, -1, {}},
                           {"Petit Nuage de Magellan", {0.388, -0.602, -0.698}, 25.0f, 3.0f, 1.0f, -1, {}}};
    sim.neighbourStarCount = neighbourStarsOk ? neighbourStars.count : 0;
    for (Voisine& v : voisines) {
        for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
            if (sim.bodies[static_cast<size_t>(i)].name == v.nom) v.body = i;
        const int ci = CentresReference::indexOf(v.nom);
        phys::Vec3 c;
        if (ci >= 0 && centresRef.centre(ci, 0.0, c)) v.c0 = Sim::fromGalactocentric(c);
        else if (v.body >= 0) v.c0 = sim.bodies[static_cast<size_t>(v.body)].fixedPos;
    }
    sim.hasGaia = gaiaOk;
    sim.gaiaCellDispersionKms = gaiaOk ? gaia.cellDispersionKms : 0;
    sim.hasGaiaAggregate = gaiaOk && gaia.cellCount > 0;      // gaia_agrege.bin chargé : lumière additionnée des autres sources
    sim.gaiaCount = gaiaOk ? gaia.count + (gaiaBOk ? gaiaB.count : 0) : 0;
    // Clic sur une étoile de Gaia : recherche dans les deux fichiers projetés en mémoire, au clic seulement (rien par image).
    if (gaiaOk)
        sim.gaiaPick = [&gaia, &gaiaB, gaiaBOk, &sim](const Camera& c, double px, double py, double w, double h, double maxPx, double mLim, GaiaHit& hit, bool& setB) {
            bool found = pickGaiaStar(gaia.file(), c, px, py, w, h, maxPx, mLim, sim.years, hit);
            setB = false;
            if (gaiaBOk && pickGaiaStar(gaiaB.file(), c, px, py, w, h, maxPx, mLim, sim.years, hit)) { found = true; setB = true; }
            return found;
        };
    sim.gaiaReliableCount = gaiaOk ? gaia.reliableCount : 0;
    sim.gaiaReliableLight = gaiaOk ? gaia.reliableLight : 0;
    sim.gaiaRebalancedCount = gaiaOk ? gaia.rebalancedCount : 0;
    sim.gaiaRebalancedShift = gaiaOk ? gaia.rebalancedShift : 0;
    sim.hasMilkyWay = milkyWay.ready;
    StarRenderer sr;
    std::vector<int64_t> starDoublesHidden;
    for (const auto& [gaiaIdx, mainIdx] : sim.starDoubles) starDoublesHidden.push_back(gaiaIdx);
    std::printf("etoiles en double (hotes d'exoplanetes) : %zu points Gaia caches\n", starDoublesHidden.size());
    sr.create(g, stars, HdrTarget::kFormat, gaiaOk, &starDoublesHidden);
    // Ciel dans une autre lumière (radio, infrarouge, X…) : cartes mesurées ciel_NOM.bin, une à la fois (fil longueurs d'onde).
    SkyBandRenderer sky;
    sky.create(g, HdrTarget::kFormat);
    const std::vector<SkyBandInfo> skyBands = listSkyBands(dataDir);
    for (const SkyBandInfo& b : skyBands) sim.skyBandLabels.push_back(b.label);
    sim.skyBandInfos = &skyBands;
    int skyLoaded = -1;
    if (opt.skyBand >= 0) sim.skyBand = opt.skyBand;
    if (opt.wholeGalaxy) sim.wholeGalaxy = true;
    if (opt.uncertainty) sim.showClones = true;
    OrbitGpu orbits;      // orbite exacte de chaque étoile, calculée sur la carte graphique
    orbits.create(g, stars, sr, HdrTarget::kFormat);
    PlanetPoints planets;
    planets.create(g);
    // Galaxies naines nommées sans forme ni photo : nuage tiré de leurs paramètres mesurés (galaxies_naines.h).
    // Planètes des autres étoiles (exoplanetes.h) : liste dans la fiche de leur étoile, dessin quand on s'en approche.
    Exoplanets exoplanets;
    ecran.etape(L"Exoplanètes, trous noirs, galaxies naines", 0.76f);
    if (exoplanets.load(dataDir + "/exoplanetes_app.tsv")) {
        exoplanets.mergeDoubles(sim.starDoubles);      // planètes d'un double rangées sous l'étoile du catalogue principal
        exoplanets.create(g);
        for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
            if (const auto* ps = exoplanets.of(sim, i)) {
                Body& b = sim.bodies[static_cast<size_t>(i)];
                b.planetsReachLy = Exoplanets::largestOrbitLy(*ps);
                for (const Exoplanet& p : *ps) {
                    std::string l = p.name;
                    if (std::isfinite(p.aAu)) l += " : " + frNum(p.aAu, 3) + " UA";
                    if (std::isfinite(p.periodDays)) l += ", un tour en " + (p.periodDays < 1000 ? frNum(p.periodDays, 3) + " jours" : frNum(p.periodDays / 365.25, 3) + " ans");
                    if (std::isfinite(p.massEarth)) l += ", " + frNum(p.massEarth, 3) + " masses terrestres" + (p.massKind == "M-R relationship" ? " (modèle masse-rayon)" : p.massKind == "Msini" ? " (minimum)" : "");
                    if (std::isfinite(p.radiusEarth)) l += ", rayon " + frNum(p.radiusEarth, 3) + " fois la Terre";
                    l += " ; " + p.method + " " + std::to_string(p.year);
                    b.planetLines.push_back(l);
                }
            }
    }
    // Trous noirs centraux de masse mesurée (trous_noirs.h).
    BlackHoles blackHoles;
    if (blackHoles.load(dataDir + "/trous_noirs.tsv", sim)) blackHoles.create(g);
    std::printf("trous noirs de masse mesuree relies a une galaxie : %zu\n", blackHoles.holes.size());
    DwarfGalaxies dwarfGalaxies;
    const bool dwarfsOk = dwarfGalaxies.load(g, dataDir + "/naines.tsv", sim);
    std::printf("galaxies naines dessinees d'apres leurs mesures : %zu\n", dwarfsOk ? dwarfGalaxies.dwarfs.size() : size_t{0});
    GalaxyFile galaxyFile;
    GalaxyRenderer galaxies;
    if (openGalaxies(dataDir + "/galaxies.bin", galaxyFile)) galaxies.create(g, galaxyFile, HdrTarget::kFormat);
    // Galaxies de forme mesurée faites de particules (galaxies_formes.h) : 532 427 du SGA-2020 et d'HyperLEDA.
    GalaxyShapes galaxyShapes;
    ecran.etape(L"Galaxies : formes et tailles mesurées", 0.85f);
    galaxyShapes.create(g, dataDir + "/galaxies_formes.bin", HdrTarget::kFormat);
    sim.galaxyShapeCount = galaxyShapes.count;
    galaxies.setCosmology(sim.cosmology, 1.0);      // table d'aujourd'hui, pour poser les noms sur les formes
    std::printf("galaxies proches : distance de z remplacee par Cosmicflows-4 : %d\n", galaxyShapes.fixNearbyDistances(sim.bodies));
    std::printf("noms poses au centre de leur forme : %d\n", galaxyShapes.snapNames(sim.bodies, galaxies));
    // Grandes structures (Laniakea, flot, vides) et nuage d'Oort (modèle) : structures.h, structures.bin.
    StructureRenderer structuresR;
    const bool structuresOk = structuresR.create(g, dataDir, HdrTarget::kFormat);
    sim.structures.loaded = structuresOk;
    NebulaRenderer nebulae;      // nébuleuses planétaires et nuages moléculaires à distance publiée (nebuleuses.h)
    if (nebulae.create(g, dataDir + "/nebuleuses.bin", HdrTarget::kFormat))
        std::printf("nebuleuses : %u planetaires, %u nuages moleculaires\n", nebulae.planetary, nebulae.clouds);
    sim.structures.oortComets = structuresR.oortCount;
    sim.structures.flowLines = structuresR.flowLines;
    for (int k = 0; k < 9; ++k) sim.structures.triangles[k] = structuresR.meshTriangles[k];
    double structuresClock = 0;
    AsteroidRenderer asteroids;
    asteroids.create(g, dataDir + "/asteroides.bin", HdrTarget::kFormat);
    sim.asteroidEpochJd = asteroids.ready ? asteroids.epochJd : 0;
    sim.asteroidCount = asteroids.ready ? asteroids.count : 0;
    // Complétude par échelle : comptée une fois sur les données réellement chargées (après les astéroïdes, pour qu'ils
    // soient comptés), lue ensuite par l'interface.
    const auto rapportCompletude = completude::rapport(completude::compter(sim, galaxies.count, gaia.count + (gaiaBOk ? gaiaB.count : 0), gaia.cellCount + gaia.skyCount ? dataDir + "/gaia_agrege.bin" : "", gaiaOk ? dataDir + "/gaia.bin" : "", dataDir));
    sim.completeness = &rapportCompletude;
    FusionPoints fusionPoints;
    fusionPoints.create(g, 0);      // remplacé par fusionCloud (les images du calcul ne sont plus chargées en mémoire)
    FusionCloud fusionCloud;
    if (hasReplay) fusionCloud.create(g, fusionDir, HdrTarget::kFormat);
    double fusionShare = 0;
    double companionShare = 0;      // Andromède, Triangle et Grand Nuage du calcul, montrés seuls dès aujourd'hui
    // Voie lactée seule, calculée en entier par le fil physique (toutes ses étoiles s'attirent : les bras naissent d'eux-mêmes).
    // Elle apparaît entre 200 et 400 millions d'années, quand le dessin mesuré des bras s'efface, et cède la place au calcul
    // de la rencontre avec Andromède en même temps que les étoiles mesurées (Sim::starShare). Bras calculés : leur place
    // n'est pas prévisible, l'écran le dit.
    FusionCloud loneGalaxy;
    const bool hasLoneGalaxy = loneGalaxy.create(g, dataDir + "/voie-lactee-seule", HdrTarget::kFormat);
    double loneShare = 0;
    ArmTracerPoints armTracers;      // masers et amas mesurés qui tracent les bras spiraux
    if (armTracers.create(g, dataDir + "/traceurs_bras.tsv")) {
        sim.armTracers = &armTracers.tracers;
        sim.armTracerWorld = &armTracers.world;
    }
    ClonePoints clones;      // nuage des 10 000 scénarios du Groupe local (précalculés par le fil physique)
    if (clones.create(g, dataDir + "/clones_groupe_local.bin")) {
        sim.cloneCount = clones.n;
        sim.cloneMergeProbability = clones.probability;
        sim.cloneMergeGa[0] = clones.t16;
        sim.cloneMergeGa[1] = clones.t50;
        sim.cloneMergeGa[2] = clones.t84;
    }
    int milkyWayCentre = -1;
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
        if (sim.bodies[static_cast<size_t>(i)].name == "Centre de la Voie lactée") milkyWayCentre = i;
    double tasksTimer = 10;
    double galaxyScaleAt = 1e300;      // date (années) du dernier calcul du facteur d'échelle de l'univers
    SphereRenderer spheres;
    spheres.create(g, HdrTarget::kFormat, dataDir + "/textures");
    NebuleuseRenderer starMatter;      // matière autour des étoiles (cycle_nebuleuse.h)
    starMatter.create(g, HdrTarget::kFormat);
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
    PoseAuto autoPose;      // pose qui baisse quand l'image sature (audit A2, pose_auto.h)
    autoPose.create(g);
    autoPose.bindSource(g, hdr.view);

    // Interface.
    ecran.etape(L"Interface", 0.95f);
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGui::GetIO().IniFilename = nullptr;      // aucun fichier de réglages écrit sur le disque
    UiState ui;
    loadFonts(ui.normal, ui.big);
    applyStyle();
    ImGui_ImplWin32_Init(hwnd);
    const VkDescriptorPoolSize uiPoolSize{VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 48};      /* police + images du panneau (interface_images.h) */
    VkDescriptorPoolCreateInfo uiPoolInfo{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
    uiPoolInfo.flags = VK_DESCRIPTOR_POOL_CREATE_FREE_DESCRIPTOR_SET_BIT;
    uiPoolInfo.maxSets = 48;
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
    // Images du panneau d'information : les cartes de surface déjà installées (interface_images.h).
    UiImages uiImages;
    {
        std::vector<std::string> files;
        for (const BodyText& t : kBodyTexts)
            if (t.image) files.emplace_back(t.image);
        uiImages.start(dataDir + "/textures", files);
        gUiImages = &uiImages;
    }

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
    Chrono chrono;      /* UNIVERS_CHRONO=<fichier.csv> : temps par image et par étape (chrono.h) */
    chrono.init(g);

    auto rebuild = [&]() {
        vkDeviceWaitIdle(g.dev);
        destroySwapchain(g, sc);
        hdr.release(g);
        final.release(g);
        if (!createSwapchain(g, surface, test, sc)) return false;
        createTargets();
        screen.bindSource(g, hdr.view);
        autoPose.bindSource(g, hdr.view);
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
    // Contrôle : balayage du zoom dans un seul lancement (UNIVERS_BALAYAGE=<d0>:<d1>:<n>:<dossier>) : n vues de d0 à d1
    // années-lumière (pas égaux en logarithme), chacune après opt.testFrames images, écrites en dossier/b_NNN.ppm, avec une
    // ligne par vue (distance, pose automatique). Sert à trouver les sauts de vue et d'éclat au zoom (audit, 20/11/2026).
    struct Sweep {
        double d0 = 0, d1 = 0;
        int n = 0, k = -1;
        std::string dir;
        std::vector<double> dates;      // balayage dans le temps (UNIVERS_BALAYAGE_DATES) : une vue par date, distance fixe
        bool yawSweep = false;          // balayage en lacet (UNIVERS_BALAYAGE_LACET) : d0 et d1 en degrés, distance fixe
        bool next(const Gpu& gg, const Target& img, VkExtent2D ext, Sim& s) {
            if (n <= 0) return false;
            if (k >= 0) {
                if (dir != "-") vkDeviceWaitIdle(gg.dev);
                char name[32];
                std::snprintf(name, sizeof(name), "/b_%03d.ppm", k);
                if (dir != "-") writeCapture(gg, img, ext, dir + name);      /* « - » : zoom continu sans images (mesure des saccades) */
                std::printf("balayage %d : distance %.4g al, date %.6g, lacet %.4g, pose automatique %.4g, part saturee %.5f, part visible %.5f, eclat moyen %.5f\n",
                            k, s.dist, s.years, s.yaw * 180.0 / kPi, s.autoPose, s.metreSat, s.metreVis, s.metreMoy);
            }
            if (++k >= n) return false;
            if (!dates.empty()) s.years = dates[static_cast<size_t>(k)];
            else if (yawSweep) {
                s.touched = true;      // pas de tour d'horizon automatique pendant le balayage
                s.yaw = (n > 1 ? d0 + (d1 - d0) * k / (n - 1) : d0) * kPi / 180.0;
            }
            else s.dist = n > 1 ? d0 * std::pow(d1 / d0, static_cast<double>(k) / (n - 1)) : d0;
            return true;
        }
    } sweep;
    // UNIVERS_BALAYAGE_DATES=<dossier>|<date>,<date>,... : une vue par date (années depuis J2000), à la distance de départ
    if (const char* b = std::getenv("UNIVERS_BALAYAGE_DATES"); b && test) {
        const std::string s = b;
        const size_t bar = s.find('|');
        if (bar != std::string::npos) {
            sweep.dir = s.substr(0, bar);
            for (size_t from = bar + 1; from < s.size();) {
                const size_t c = s.find(',', from);
                sweep.dates.push_back(std::atof(s.substr(from, c == std::string::npos ? std::string::npos : c - from).c_str()));
                if (c == std::string::npos) break;
                from = c + 1;
            }
            sweep.n = static_cast<int>(sweep.dates.size());
            sweep.next(g, final, sc.extent, sim);
        }
    }
    // UNIVERS_BALAYAGE_LACET=<degrés début>:<degrés fin>:<n>:<dossier> : n vues en tournant la tête (défilement), distance
    // fixe. Sert à vérifier que l'éclat ne saute pas quand on fait défiler la vue (Marc, 20/11/2026).
    if (const char* b = std::getenv("UNIVERS_BALAYAGE_LACET"); b && test) {
        char dir[512] = {};
        if (std::sscanf(b, "%lf:%lf:%d:%511s", &sweep.d0, &sweep.d1, &sweep.n, dir) == 4) {
            sweep.dir = dir;
            sweep.yawSweep = true;
            sweep.next(g, final, sc.extent, sim);
        } else sweep.n = 0;
    }
    if (const char* b = std::getenv("UNIVERS_BALAYAGE"); b && test && !sweep.yawSweep) {
        char dir[512] = {};
        if (std::sscanf(b, "%lf:%lf:%d:%511s", &sweep.d0, &sweep.d1, &sweep.n, dir) == 4 && sweep.d0 > 0 && sweep.d1 > 0) {
            sweep.dir = dir;
            sweep.next(g, final, sc.extent, sim);      // première distance, avant la première image
        } else sweep.n = 0;
    }
    // Contrôle du mouvement (Marc, 20/11/2026 : « trop clair ou trop sombre quand je zoome ou défile ») :
    // UNIVERS_GESTE=<zoom|lacet>:<début>:<fin>:<secondes>:<journal> rejoue un geste à 60 images par seconde (pas fixe), avec
    // la pose automatique à sa vraie vitesse (pas le régime instantané des contrôles), et écrit une ligne par image :
    // temps, distance, lacet, pose photo, pose automatique, éclat moyen mesuré, part saturée.
    struct Geste {
        bool on = false, zoom = false;
        double a = 0, b = 0, secondes = 0, t = 0;
        FILE* log = nullptr;
    } geste;
    if (const char* gs = std::getenv("UNIVERS_GESTE"); gs && test) {
        char mode[16] = {}, file[512] = {};
        if (std::sscanf(gs, "%15[^:]:%lf:%lf:%lf:%511s", mode, &geste.a, &geste.b, &geste.secondes, file) == 5 && geste.secondes > 0) {
            geste.zoom = std::string(mode) == "zoom";
            geste.log = std::fopen(file, "w");
            geste.on = geste.log != nullptr;
            sim.touched = true;
        }
    }
    const bool instant = test && !geste.on;      // contrôles : pose réglée tout de suite ; geste rejoué : vraie vitesse
    bool gaiaLiveNow = true;            // le calcul en direct de Gaia sert-il à cette image ? (non quand le film mène et que Gaia y est éteint)
    double pathYears0 = 0, pathWall = 0;      // contrôle --horloge-reelle : date et durée du trajet
    long pathFrames = 0;
    double titleTimer = 0;
    bool drawable = true;
    uint32_t pendingIndex = 0;
    bool hasPending = false;      // image envoyée, pas encore affichée (affichage remis après le travail suivant du processeur)
    auto presentPending = [&]() {
        if (!hasPending) return;
        hasPending = false;
        VkPresentInfoKHR present{VK_STRUCTURE_TYPE_PRESENT_INFO_KHR};
        present.waitSemaphoreCount = 1;
        present.pWaitSemaphores = &rendered;
        present.swapchainCount = 1;
        present.pSwapchains = &sc.chain;
        present.pImageIndices = &pendingIndex;
        const VkResult pr = vkQueuePresentKHR(g.queue, &present);
        if (pr == VK_ERROR_OUT_OF_DATE_KHR || pr == VK_SUBOPTIMAL_KHR) input.resized = true;
        else if (pr != VK_SUCCESS) fail("affichage", pr);
    };
    // Tout est chargé : l'écran de chargement se ferme, la fenêtre de l'appli apparaît à sa place.
    ecran.etape(L"Prêt", 1.0f);
    ecran.fermer();
    if (!test) {
        // Deux appels : Windows impose au premier l'état demandé par le lanceur (un raccourci « réduit » donnait une
        // fenêtre réduite, sans surface à dessiner). Le second s'applique toujours. En contrôle, rien ne s'ouvre.
        ShowWindow(hwnd, SW_SHOWMAXIMIZED);
        ShowWindow(hwnd, SW_SHOWMAXIMIZED);
        SetForegroundWindow(hwnd);
        input.resized = true;      // la fenêtre a pris sa vraie taille : refaire la surface de dessin
    }
    while (!input.quit) {
        pumpMessages();
        if (input.resized || !drawable) {
            presentPending();      // avant de refaire la chaîne d'images
            input.resized = false;
            drawable = rebuild();
            if (!drawable) {
                Sleep(50);
                continue;
            }
        }
        const auto now = std::chrono::steady_clock::now();
        // Le temps suit l'horloge réelle : à 200 Ma/s, la date avance de 200 Ma par seconde quelle que soit la cadence d'images
        // (le plafond de 0,1 s par image la ralentissait dès que l'appli passait sous 10 images/s). Plafond de 0,5 s
        // gardé pour un arrêt de la fenêtre (déplacement, mise en veille). Contrôle d'un trajet : pas fixe.
        const double frameWallMs = std::chrono::duration<double, std::milli>(now - last).count();
        const double dt = (test && opt.hasPath && !opt.realClock) || geste.on ? 1.0 / 60.0 : std::min(0.5, std::chrono::duration<double>(now - last).count());
        chrono.cpu("messages");
        last = now;

        if (geste.on) {      // geste rejoué : la caméra suit le geste, image par image
            const double u = std::clamp(geste.t / geste.secondes, 0.0, 1.0);
            if (geste.zoom) sim.dist = geste.a * std::pow(geste.b / geste.a, u);
            else sim.yaw = (geste.a + (geste.b - geste.a) * u) * kPi / 180.0;
        }
        // Gestes -> simulateur.
        if (input.touched) sim.touched = true;
        sim.orbit(input.dragX, input.dragY);
        sim.zoom(input.wheel);
        sim.zoomField(input.wheelField);
        input.dragX = input.dragY = input.wheel = input.wheelField = 0;
        if (input.space) sim.paused = !sim.paused;
        if (input.home) sim.follow(0);
        input.space = input.home = false;
        if (!sim.outer && outerReady) sim.outer = &outer;
        sim.advance(dt);
        chrono.cpu("gestes");
        // Le temps ne dépasse jamais le calcul exact des orbites : la date montrée est toujours une date calculée, quelle
        // que soit la vitesse du temps ou la façon d'y arriver. Si la date demandée est en avance sur le calcul, la carte
        // graphique calcule (étoiles Gaia : 1 pas d'un million d'années par image) et la date montrée suit.
        {
            double wanted = sim.years;
            if (holdOn && std::fabs((sim.years - lastShown) - sim.lastAdvance) < 0.5) wanted = holdGoal + sim.lastAdvance;      // sinon : date choisie à la main
            if (pathActive && (sim.backward ? wanted <= opt.years : wanted >= opt.years)) {      // contrôle : arrivé
                wanted = opt.years;
                sim.paused = true;
                pathActive = false;
            }
            wanted = std::clamp(wanted, sim.minYears(), sim.maxYears());
            // Au-delà de ce que le film du Groupe local a déjà calculé, la date s'arrête au bord du film (décision de Marc,
            // 18/11/2026) : rien n'est inventé, et le bord avance tout seul à mesure que le calcul tourne (FilmStars::reload).
            sim.filmEdgeYears = 0;
            if (filmStarsOk && sim.film.pret() && wanted > kStartYears) {
                const double edge = kStartYears + filmStars.endGa() * 1.0e9;
                if (wanted > edge) {
                    wanted = edge;
                    sim.filmEdgeYears = edge;
                }
            }
            double shownYears = wanted;
            const double off = gaiaOk ? gaia.orbitEpochYears() : 0.0;
            // Le film mène-t-il à la date voulue ? Alors les étoiles visibles ne demandent aucun calcul d'orbite (film_carte.h),
            // et, quand Gaia y est entièrement éteint (vue « meilleur rendu », plus de 10 Ma d'aujourd'hui), le calcul en direct
            // de Gaia n'a plus lieu : la date n'attend plus rien.
            const double tWanted = (wanted - kStartYears) / 1.0e9;
            const bool filmAtWanted = filmGpuOk && tWanted > -1.0e-6 && filmStars.covers(std::max(tWanted, 0.0));
            const bool gaiaGone = filmAtWanted && !filmStars.gain.empty() && sim.bestLook && std::fabs(tWanted) * 1.0e3 >= 10.0;
            const bool gaiaLive = gaiaOk && !gaiaGone;
            gaiaLiveNow = gaiaLive;
            const bool need = static_cast<long>(std::floor(wanted / OrbitGpu::kStepYears)) != orbits.stepLo ||
                              (gaiaLive && (static_cast<long>(std::floor((wanted - off) / OrbitGpu::kStepYears)) != gaia.orbitStep() || gaia.orbitLagSteps() != 0)) ||
                              // étoiles visibles du modèle : leurs orbites exactes rattrapent la date même quand Gaia est à jour
                              (milkyWayStarsOk && !filmAtWanted &&
                               (static_cast<long>(std::floor((wanted - off) / OrbitGpu::kStepYears)) != milkyWayStars.orbitStep() || milkyWayStars.orbitLagSteps() != 0));
            chrono.cpu("dates (preparation)");
            if (need) {
                VkCommandBuffer once = beginOnce(g);
                if (gaiaLive) {
                    gaia.advance(g, once, wanted, test && !opt.hasPath && !geste.on ? 1000000 : 64);      // le fil Gaia borne lui-même le travail par image
                    const double lo = static_cast<double>(gaia.orbitStep()) * OrbitGpu::kStepYears + off;
                    shownYears = std::clamp(wanted, lo, lo + OrbitGpu::kStepYears - 1.0);
                    gaia.advance(g, once, shownYears, 0);      // retard recompté pour la date réellement montrée
                    // Les états de départ de Gaia se préparent pendant les premières secondes : d'ici là, la date reste à moins de
                    // 30 000 ans d'aujourd'hui, où le mouvement est la ligne droite mesurée (l'orbite y pèse moins de 1 %).
                    if (!gaia.orbitReady()) shownYears = std::clamp(shownYears, off - 3.0e4, off + 3.0e4);
                }
                orbits.advance(once, shownYears, gaiaOk || test ? 1000000 : 64);
                const double lo = static_cast<double>(orbits.stepLo) * OrbitGpu::kStepYears;
                if (orbits.lagSteps) shownYears = std::clamp(shownYears, lo, lo + OrbitGpu::kStepYears - 1.0);
                endOnce(g, once);
            }
            chrono.cpu("orbites (rattrapage)");
            // Étoiles visibles du modèle : leurs orbites exactes avancent à CHAQUE image (le calcul ne fait que les feuilles
            // dessinées à l'image d'avant, et retombe à « à jour » dès qu'il n'en voit pas) ; tant qu'une feuille n'a pas
            // rattrapé la date, elle est dessinée en épicycles, valables seulement près d'aujourd'hui.
            if (milkyWayStarsOk) {
                // Quand le film du Groupe local couvre la date, les étoiles visibles le suivent (film_etoiles.h) : l'état de chaque
                // étoile au pas d'un million d'années de la date montrée vient du film, plus du calcul d'orbites de l'appli.
                filmStars.reload(dt);
                const long step = milkyWayStars.stepOf(shownYears);
                const double tRaw = (milkyWayStars.yearsOfStep(step) - kStartYears) / 1.0e9, tStep = std::max(tRaw, 0.0);
                // Le pas d'aujourd'hui commence à l'époque de Gaia (2016), dix ans avant le départ du film : seul cet écart de
                // quelques années est ramené à t = 0. Le pas d'avant (de −1 Ma à 0) reste sur les orbites de l'appli (revue F7).
                const bool byFilm = filmStarsOk && tRaw > -1.0e-6 && filmStars.covers(tStep);
                // Revue F1 : quand le film mène, Gaia s'éteint entre 1 et 10 Ma d'aujourd'hui [choix : d'ici là, les orbites de
                // l'appli et le film restent proches] ; les étoiles du film reprennent la lumière que Gaia portait (gain, .lum).
                // Constant dans un pas d'un million d'années : il suit l'état donné à la carte.
                // Film sur la carte : la part de Gaia éteinte suit la date exacte (et non plus le pas d'un million d'années).
                const double tExact = std::max((shownYears - kStartYears) / 1.0e9, 0.0);
                const double gaiaOff = byFilm && !filmStars.gain.empty() && sim.bestLook
                                           ? std::clamp(((filmGpuOk ? tExact : std::fabs(tStep)) * 1.0e3 - 1.0) / 9.0, 0.0, 1.0) : 0.0;
                filmStars.gaiaOff = gaiaOff;
                filmNeighbours.gaiaOff = gaiaOff;
                const int dir = sim.paused ? 0 : sim.backward ? -1 : 1;
                const double gaPerSecond = sim.yearsPerSecond() / 1.0e9;      // pour lire le film d'avance selon la vitesse
                if (byFilm && filmGpuOk) {
                    // État de chaque étoile écrit sur la carte à la date exacte montrée, à chaque image : rien ne dépend du
                    // pas d'un million d'années ni de la vitesse du temps. Le Soleil (hors du film) : son orbite selon l'appli.
                    sim.ensureExact();
                    const double y = shownYears, h = 1.0e3;
                    const phys::Vec3 s0 = sim.exact.position(0, y - h), s1 = sim.exact.position(0, y + h), s = sim.exact.position(0, y);
                    const double k = 3.0856775814913673e16 / (2.0 * h * kYearSeconds);      // kpc par an -> km/s
                    if (filmGpu.update(g, filmStars, milkyWayStars.orbitsForFilm(), tExact, dir, gaPerSecond, s, {(s1.x - s0.x) * k, (s1.y - s0.y) * k, (s1.z - s0.z) * k}, gaiaOff, step)) {
                        filmStars.lastStep = step;
                        filmGpuT = tExact;
                    }
                } else if (byFilm) {
                    if (step != filmStars.lastStep || !milkyWayStars.externalStates()) {
                        sim.ensureExact();      // le Soleil : son orbite selon l'appli (il n'est pas dans le film)
                        const double y = milkyWayStars.yearsOfStep(step), h = 1.0e3;
                        const phys::Vec3 s0 = sim.exact.position(0, y - h), s1 = sim.exact.position(0, y + h), s = sim.exact.position(0, y);
                        const double k = 3.0856775814913673e16 / (2.0 * h * kYearSeconds);      // kpc par an -> km/s
                        if (filmStars.states(tStep, s, {(s1.x - s0.x) * k, (s1.y - s0.y) * k, (s1.z - s0.z) * k}, filmStates)) {
                            milkyWayStars.setExternalStates(g, filmStates, step);
                            filmStars.lastStep = step;
                        }
                    }
                } else {
                    if (milkyWayStars.externalStates()) {      // on sort du film : retour aux orbites de référence
                        milkyWayStars.leaveExternalStates();
                        filmStars.lastStep = LONG_MIN;
                    }
                    VkCommandBuffer once = beginOnce(g);
                    milkyWayStars.advance(g, once, shownYears, test && !opt.hasPath && !geste.on ? 1000000 : 64);
                    endOnce(g, once);
                }
                sim.filmLeads = byFilm && milkyWayStars.externalStates();
                sim.gaiaFilmOff = sim.filmLeads ? gaiaOff : 0.0;
                // Mêmes dates, même film pour les étoiles d'Andromède, du Triangle et des Nuages (positions autour du centre de
                // leur galaxie ; le centre lui-même suit déjà le film, simulation.h).
                if (filmNeighboursOk) {
                    filmNeighbours.reload(dt);
                    if (byFilm && filmGpuNeighboursOk && filmNeighbours.covers(tExact)) {
                        if (filmGpuNeighbours.update(g, filmNeighbours, neighbourStars.orbitsForFilm(), tExact, dir, gaPerSecond, {}, {}, gaiaOff, step)) {
                            filmNeighbours.lastStep = step;
                            filmGpuNeighboursT = tExact;
                        }
                    } else if (byFilm && filmNeighbours.covers(tStep)) {
                        if (step != filmNeighbours.lastStep || !neighbourStars.externalStates()) {
                            if (filmNeighbours.states(tStep, {}, {}, filmNeighbourStates)) {
                                neighbourStars.setExternalStates(g, filmNeighbourStates, step);
                                filmNeighbours.lastStep = step;
                            }
                        }
                    } else if (neighbourStars.externalStates()) {
                        neighbourStars.leaveExternalStates();
                        filmNeighbours.lastStep = LONG_MIN;
                    }
                }
            }
            chrono.cpu("film et etoiles visibles");
            holdOn = shownYears != wanted;
            holdGoal = wanted;
            if (shownYears != sim.years) {
                sim.years = shownYears;
                sim.refreshEphemeris();
                sim.refreshGalaxies();
            }
            lastShown = sim.years;
            sim.timeHeld = holdOn;
            sim.yearsGoal = wanted;
            sim.orbitLagSteps = holdOn ? std::max(1L, std::labs(std::lround((wanted - shownYears) / OrbitGpu::kStepYears))) : 0;
            sim.gaiaOrbitLagSteps = gaiaOk ? (gaia.orbitReady() ? 0 : std::max(1L, gaia.orbitLagSteps())) : -1;
            // Comment c'est obtenu, famille par famille.
            const double w = orbite::poidsOrbite(sim.years), share = sim.starShare();
            sim.calcStates.clear();
            {
                // Éphémérides : un calcul de la NASA ajusté sur les mesures, lu tel quel (précalculé). Hors éphémérides : suivi pas
                // à pas (calculé ici), puis table d'orbites (précalculée, approchée), puis rien.
                const std::string method = sim.planetMethod;
                const bool table = method == "table précalculée", direct = method == "suivi pas à pas";
                sim.calcStates.push_back({"Planètes et lunes",
                                          sim.ephemValid ? CalcMode::Precomputed : !sim.outer ? CalcMode::Hidden : direct ? CalcMode::Exact : table ? CalcMode::Approx : CalcMode::Hidden, 0,
                                          sim.ephemValid ? "éphémérides de la NASA (calcul ajusté sur les mesures), lues telles quelles"
                                          : !sim.outer ? "hors des dates connues"
                                          : direct ? "calculé ici (gravité mutuelle), parti des positions des éphémérides de la NASA, vitesses recalées pour retrouver leurs longitudes 400 ans plus loin ; les autres lunes ne sont pas montrées"
                                          : table ? "table d'orbites calculée à l'avance, relue entre ses points : place sur l'orbite de moins en moins sûre"
                                                  : "non montrées : au-delà de ce qui est calculé"});
            }
            if (asteroids.ready)
                sim.calcStates.push_back({"Astéroïdes et comètes", sim.asteroidGain(asteroids.epochJd) > 0 ? CalcMode::Approx : CalcMode::Hidden, 0,
                                          "orbite mesurée, suivie sans l'attraction des planètes ; montrés à moins de 300 ans de leurs mesures"});
            if (hasProbes) sim.calcStates.push_back({"Sondes", CalcMode::Precomputed, 0, "trajectoires publiées par la NASA : reconstituées pour le passé, prévues pour l'avenir"});
            sim.calcStates.push_back({"Étoiles principales", share <= 0 ? CalcMode::Hidden : w < 0.01 ? CalcMode::Measured : CalcMode::Exact, sim.orbitLagSteps,
                                      w < 0.01 ? "position et vitesse mesurées, ligne droite ; sans vitesse radiale mesurée, elle compte pour zéro"
                                               : "départ mesuré ; orbite calculée pas à pas sur la carte graphique dans un modèle de la Galaxie (écart d'environ 5 000 al à 100 millions d'années)"});
            if (gaiaOk)
                sim.calcStates.push_back({"Étoiles Gaia", share <= 0 ? CalcMode::Hidden : w < 0.01 ? CalcMode::Measured : gaia.orbitReady() ? CalcMode::Exact : CalcMode::Approx,
                                          sim.gaiaOrbitLagSteps > 0 ? sim.gaiaOrbitLagSteps : 0,
                                          w < 0.01 ? "position et vitesse mesurées, ligne droite ; deux étoiles sur trois sans vitesse radiale mesurée (comptée zéro)"
                                          : gaia.orbitReady() ? "départ mesuré ; orbite calculée pas à pas sur la carte graphique dans un modèle de la Galaxie (écart d'environ 5 000 al à 100 millions d'années)"
                                                                                                                      : "épicycles (approché) pendant la préparation du calcul exact"});
            if (sim.hasGaiaAggregate)
                sim.calcStates.push_back({"Lumière additionnée des autres sources Gaia", share <= 0 ? CalcMode::Hidden : w < 0.01 ? CalcMode::Measured : gaia.orbitReady() ? CalcMode::Exact : CalcMode::Approx,
                                          sim.gaiaOrbitLagSteps > 0 ? sim.gaiaOrbitLagSteps : 0,
                                          "somme de sources mesurées, rangée par cases ; chaque case suit l'orbite de la vitesse moyenne mesurée de ses sources"});
            {
                const bool past = sim.years < kStartYears;      // le calcul de la rencontre ne couvre que l'avenir
                sim.calcStates.push_back({"Galaxies du Groupe local", !sim.deepTime() ? CalcMode::Measured : sim.replay && !past ? CalcMode::Precomputed : CalcMode::Hidden, 0,
                                          !sim.deepTime() ? "positions mesurées"
                                          : past ? "non montrées : leur passé n'est pas calculé"
                                          : sim.replay ? "rejeu du calcul de la rencontre avec Andromède (fait à l'avance, un scénario) ; les galaxies hors de ce calcul ne sont pas montrées"
                                                       : "non montrées : calcul de la rencontre absent"});
            }
            if (sim.filmLeads)
                    sim.calcStates.push_back({"Étoiles visibles de la Voie lactée", CalcMode::Precomputed, 0,
                                              std::string("film du calcul unique du Groupe local (cinq galaxies qui s'attirent, énergie noire) : les mêmes étoiles qu'aujourd'hui, emportées par ce calcul ; un scénario ; ") +
                                                  (filmStars.note.empty() ? std::string("sans barre dans la masse") : filmStars.note)});
            if (sim.replay)
                sim.calcStates.push_back({"Étoiles du calcul de la fusion", share < 1 ? CalcMode::Precomputed : CalcMode::Hidden, 0,
                                          fusionCloud.physical ? "points du calcul fait à l'avance (un scénario) ; éclat : masse de chaque point divisée par le rapport masse/lumière de sa galaxie, même échelle que les étoiles mesurées"
                                                               : "points du calcul fait à l'avance (un scénario) ; éclat d'affichage fixe, pas encore à l'échelle des étoiles mesurées"});
            if (hasLoneGalaxy)
                sim.calcStates.push_back({"Voie lactée entière calculée", loneGalaxy.count ? CalcMode::Precomputed : CalcMode::Hidden, 0,
                                          "calcul fait à l'avance où toutes les étoiles de la Galaxie s'attirent : bras calculés, position non prévisible"});
            if (sim.armTracers)
                sim.calcStates.push_back({"Traceurs des bras spiraux", !armTracers.count ? CalcMode::Hidden : std::fabs(sim.years - kStartYears) < 3.0e4 ? CalcMode::Measured : CalcMode::Approx, 0,
                                          milkyWayStarsOk && sim.bestLook && std::fabs(sim.years - kStartYears) > kLinearLimitYears
                                              ? "non montrés loin d'aujourd'hui : les bras sont alors portés par les étoiles visibles, qui tournent chacune à sa vitesse"
                                          : std::fabs(sim.years - kStartYears) < 3.0e4
                                              ? "masers à parallaxe radio (Reid et al. 2019) et amas ouverts datés (Hunt & Reffert 2023) : positions mesurées"
                                              : "dessin mesuré aujourd'hui, tourné d'un bloc à la vitesse mesurée des bras (28,2 ± 2,1 km/s par kpc, Dias et al. 2019) : approché, les bras se déforment aussi"});
            if (sim.cloneCount)
                sim.calcStates.push_back({"Scénarios du Groupe local", clones.count ? CalcMode::Precomputed : CalcMode::Hidden, 0,
                                          "10 000 routes possibles des galaxies voisines, calculées à l'avance d'après l'incertitude des mesures"});
            sim.calcStates.push_back({"Galaxies lointaines", CalcMode::Exact, 0,
                                      "direction et décalage vers le rouge mesurés ; distance calculée d'après le modèle d'univers (réglable), agrandie avec l'expansion"});
        }
        chrono.cpu("dates et orbites");
        const Camera cam = sim.camera(static_cast<double>(sc.extent.width) / sc.extent.height);
        // Exposition « photo » : temps de pose choisi pour que la galaxie résolue la plus brillante à l'écran ait une brillance
        // moyenne de 0,3 (avant l'étirement asinh) ; la même pose pour tout ce qui est à l'écran (les étoiles saturent, comme
        // sur une photo). Aucune lumière n'est ajoutée ni retirée : seule la pose change. Réglable par crans (exposureEv).
        {
            // Galaxies résolues et nébuleuses autour des étoiles (Marc, 20/11/2026 : la nébuleuse planétaire du Soleil ne se
            // voyait pas) : chacune pèse de 0 à 1 selon sa taille à l'écran et sa part dans l'image ; la pose visée est
            // la pose « photo » élevée à ce poids (en logarithme), si bien qu'elle glisse quand un objet entre, grandit ou
            // sort, au lieu de basculer. Même règle qu'avant une fois l'objet bien installé (poids 1).
            const double base = kExposure * sim.brightnessBoost() * sim.fieldGain();
            double wg = galaxyShapes.photoWeight, sg = galaxyShapes.photoSurface, wn = 0, sn = 0;
            cycleApp.photoMetering(sim, cam, 2.0 * cam.tanHalf / sc.extent.height, wn, sn);
            const double weight = std::max(wg, wn);
            double want = 1.0, wantWeight = 0.0;
            if (sim.bestLook && sim.photoExposure && weight > 0) {
                const double logS = ((wg > 0 ? wg * std::log(sg) : 0.0) + (wn > 0 ? wn * std::log(sn) : 0.0)) / (wg + wn);
                // plafond ×10⁶ (galaxies, comme avant) ; ×10⁴ quand seule une nébuleuse règle la pose (10 magnitudes : de
                // quoi montrer une nébuleuse planétaire comme celle de l'Hélice, 23 mag par seconde d'arc carrée)
                const double cap = wg > 0 ? 1.0e6 : 1.0e4;
                want = std::exp(weight * std::log(std::clamp(0.3 / (std::exp(logS) * base), 1.0, cap)));
                wantWeight = weight;
            }
            // Adaptation : en logarithme (en crans d'IL, comme l'œil et les appareils photo), demi-temps 0,35 s. Avant, la
            // pose courait en linéaire vers sa cible : de ×1 à ×1 000, elle montait de ×250 dès la première image.
            const double k = instant ? 1.0 : 1.0 - std::exp(-dt / 0.5);
            sim.photoGain = std::exp(std::log(sim.photoGain) + (std::log(want) - std::log(sim.photoGain)) * k);
            sim.photoWeight += (wantWeight - sim.photoWeight) * k;
            sim.photoNebula += ((wantWeight > 0 && wn > wg ? wantWeight : 0.0) - sim.photoNebula) * k;
            if (!(sim.bestLook && sim.photoExposure)) sim.photoGain = 1.0, sim.photoWeight = 0.0, sim.photoNebula = 0.0;
        }
        const PushConstants pc = pushConstants(cam, kExposure * static_cast<float>(sim.brightnessBoost() * sim.fieldGain() * sim.photoGain * std::pow(2.0, sim.exposureEv)), sc.extent.height, sim.years);

        chrono.cpu("camera");
        // Choix des étoiles Gaia et des étoiles visibles du modèle (processeur, tous les cœurs) AVANT l'attente de la carte : il
        // remplit des listes que l'image en vol ne lit pas (anneau de gaia.h), pendant que la carte finit l'image d'avant. Mêmes
        // valeurs que leur dessin plus bas, qui reprend ce choix (sinon il le refait : rien ne change à l'écran).
        {
            const bool skyOnlyNow = sim.skyBand >= 0 && sky.loaded && sim.skyBand == skyLoaded;
            gaia.improved = sim.bestLook;
            gaiaB.improved = sim.bestLook;
            const double gaiaLeftNow = sim.starShare() * (1.0 - sim.gaiaFilmOff);
            if (!skyOnlyNow && sim.starShare() > 0 && gaiaLeftNow > 0) {
                gaia.select(cam, pc.par[0] * static_cast<float>(gaiaLeftNow), sc.extent.height, sim.years);
                if (gaiaBOk) gaiaB.select(cam, pc.par[0] * static_cast<float>(gaiaLeftNow), sc.extent.height, sim.years);
            }
            if (milkyWayStarsOk && !skyOnlyNow && sim.bestLook) milkyWayStars.select(cam, pc.par[0], sc.extent.height, sim.years);
        }
        chrono.cpu("choix des etoiles (avant l'attente)");
        presentPending();      // image d'avant, envoyée au tour précédent
        chrono.cpu("affichage");
        vkWaitForFences(g.dev, 1, &fence, VK_TRUE, UINT64_MAX);
        chrono.cpu("attente de la carte");
        chrono.gpuCollect(g);
        // mesure de l'image précédente, lue sans attente (la barrière vient d'être passée) ; relevée seulement aux échelles des
        // galaxies (au-delà de 10 millions d'al regardés), jamais pour les étoiles ; balayage du zoom du 20/11 : un plafond fixe
        // dès 10 Mal donnait ×2,1 d'éclat d'un cran de molette au suivant
        // plafond : ×4 pour les étoiles, puis comme l'échelle regardée (10 à 100 Mal, 1 000 à 10 Gal) : au plus ×1,26 d'un cran de
        // molette au suivant (en carré, le balayage mesurait ×1,6 par cran)
        autoPose.update(dt, instant, true, std::clamp(sim.dist / 1.0e7, 4.0, pose_auto::kPoseMaxGalaxies),
                       sim.bestLook && sim.photoExposure ? (sim.exposureEv > 0 ? 1.0 : std::clamp(sim.photoWeight, 0.0, 1.0)) : 0.0, sim.photoNebula);      // ×4 au plus pour les étoiles
        sim.autoPose = autoPose.pose;
        sim.metreSat = autoPose.partSaturee;
        sim.metreVis = autoPose.partVisible;
        sim.metreMoy = autoPose.moyenne;
        if (geste.on) {
            std::fprintf(geste.log, "%.4f %.6g %.4f %.6g %.6g %.6g %.6g\n", geste.t, sim.dist, sim.yaw * 180.0 / kPi, sim.photoGain,
                         autoPose.pose, autoPose.moyenne, autoPose.partSaturee);
            geste.t += dt;
        }
        // Distances des galaxies des relevés : recalculées quand la cosmologie change, et quand la date s'éloigne
        // d'aujourd'hui (l'univers grandit : facteur d'échelle calculé, mis à jour tous les millions d'années).
        // Tous les 100 000 ans (avant : un million) : M77, à 44 millions d'al, avance alors d'environ 300 al par pas au lieu
        // de 3 000 ; le nom et la caméra prennent le même facteur (sim.galaxyScale), ils ne glissent plus sur la forme.
        if (sim.cosmologyDirty || std::fabs(sim.years - galaxyScaleAt) > 1.0e5) {
            galaxies.setCosmology(sim.cosmology, cosmo::scaleFactorAt(sim.cosmology, (sim.years - kStartYears) / 1.0e9));
            sim.galaxyScale = galaxies.scale;
            sim.refreshGalaxies();
            galaxyScaleAt = sim.years;
            sim.cosmologyDirty = false;
        }
        if (sim.skyBand != skyLoaded) {      // changement de lumière : charger la carte (0,2 à 0,5 s), ou revenir au visible
            if (sim.skyBand >= static_cast<int>(skyBands.size())) sim.skyBand = -1;
            if (sim.skyBand >= 0) sky.load(g, skyBands[static_cast<size_t>(sim.skyBand)].path);
            skyLoaded = sim.skyBand;
        }
        sim.skyLegend = sim.skyBand >= 0 ? sky.legend(std::sqrt(dot(cam.pos, cam.pos))) : std::vector<std::string>{};
        fusionPoints.update(sim, cam, pc.par[0]);
        // Étoiles du calcul de la fusion : la part que les étoiles mesurées leur laissent (Sim::starShare), éteinte quand on
        // regarde de trop près (moins de 3 000 années-lumière : un point du calcul n'est pas une étoile).
        fusionShare = (sim.wholeGalaxy ? 1.0 : 1.0 - sim.starShare()) * std::clamp(std::log10(std::max(sim.dist, 1.0)) - 3.5, 0.0, 1.0);
        // Les autres galaxies du Groupe local dès aujourd'hui (Marc, 13/11/2026 : « une seule galaxie, sa vraie forme, à sa
        // place la plus probable ») : les points de M31, M33 et du Grand Nuage, au départ du calcul (positions et vitesses
        // mesurées, galaxies modèles tirées des paramètres publiés), pendant que la Voie lactée est montrée par Gaia et sa lueur.
        // Vue « meilleur rendu » seulement : ce sont des galaxies modèles, pas des étoiles mesurées une à une.
        companionShare = sim.bestLook && !sim.wholeGalaxy ? sim.starShare() * std::clamp(std::log10(std::max(sim.dist, 1.0)) - 3.5, 0.0, 1.0) : 0.0;
        sim.companionShare = companionShare;
        // Le nuage n'est dessiné que si les étoiles visibles de la Voie lactée ne sont pas montrées avec celles des voisines
        // (même condition que son dessin, plus bas : sim.milkyWayStarShare > 0 && neighbourStarsOk). Sinon il n'est pas lu du tout :
        // en vue « meilleur rendu », le relire à chaque image coûtait ~25 ms par image nouvelle du nuage pendant un trajet.
        const bool fusionCloudDrawn = milkyWayCentre >= 0 && !((milkyWayStarsOk && sim.bestLook) && neighbourStarsOk);
        fusionCloud.update(g, sim.replayGa(), fusionCloudDrawn ? std::max(fusionShare, companionShare) : 0.0);
        loneShare = hasLoneGalaxy ? std::clamp((sim.years - kStartYears - ArmTracerPoints::kFullYears) / (ArmTracerPoints::kEndYears - ArmTracerPoints::kFullYears), 0.0, 1.0) *
                                        sim.starShare() * std::clamp(std::log10(std::max(sim.dist, 1.0)) - 3.5, 0.0, 1.0)
                                  : 0.0;
        loneGalaxy.update(g, sim.replayGa(), loneShare);
        sim.loneGalaxyShare = loneGalaxy.count ? loneShare : 0.0;
        if (milkyWayCentre >= 0 && sim.showClones) clones.update(cam, sim.position(milkyWayCentre), (sim.years - kStartYears) / 1.0e9, sim.dist, pc.par[0]);
        else clones.count = 0;
        // Traceurs mesurés des bras (masers, amas) : à leur place mesurée près d'aujourd'hui. Plus loin dans le temps, ce calque
        // les fait tourner d'un bloc, alors que les étoiles visibles de la Voie lactée tournent chacune à sa vitesse (film ou
        // orbites) : les deux se contredisaient à l'écran (contrôle du premier film, docs/premier-film.md, défaut 6). Quand les
        // étoiles visibles sont dessinées, le calque n'est donc montré qu'à moins de 3 millions d'années d'aujourd'hui.
        // audit C5 : fondu de 1 à 3 Ma au lieu d'une coupure nette à 3 Ma (meilleur rendu)
        const double armAgree = !(milkyWayStarsOk && sim.bestLook) ? 1.0
                                : std::clamp((kLinearLimitYears - std::fabs(sim.years - kStartYears)) / (kLinearLimitYears - 1.0e6), 0.0, 1.0);
        if (milkyWayCentre >= 0 && armAgree > 0)
            armTracers.update(cam, sim.position(milkyWayCentre), sim.years - kStartYears, sim.dist, pc.par[0] * static_cast<float>(armAgree));
        else armTracers.count = 0;
        sim.armTracersShown = armTracers.count > 0;
        tasksTimer += dt;
        if (tasksTimer > 2.0) {      // calculs de fond du PC : relus toutes les 2 secondes
            tasksTimer = 0;
            sim.tasks = readTasks(dataDir + "/avancement");
        }
        chrono.cpu("couches (preparation)");
        spheres.uploadPending(g);      // au plus une carte de surface par image, dès qu'elle est décodée
        uiImages.uploadPending(g);      // au plus une image du panneau par image affichée
        chrono.cpu("envois (surfaces, images)");
        cycleApp.update(sim, cam);      // rayon, teinte, éclat et matière des étoiles à cette date (avant les sphères)
        chrono.cpu("astres : cycle de vie");
        spheres.prepare(sim, cam, sc.extent.width, sc.extent.height, asSphere);
        chrono.cpu("astres : spheres");
        planets.update(sim, cam, asSphere, spheres.nearestDist());
        chrono.cpu("astres : planetes");
        dwarfGalaxies.update(sim);
        blackHoles.update(sim, cam);
        exoplanets.update(sim, cam);
        chrono.cpu("astres (preparation)");

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
        chrono.cpu("interface");

        vkWaitForFences(g.dev, 1, &fence, VK_TRUE, UINT64_MAX);
        uint32_t index = 0;
        const VkResult ar = vkAcquireNextImageKHR(g.dev, sc.chain, UINT64_MAX, acquired, VK_NULL_HANDLE, &index);
        if (ar == VK_ERROR_OUT_OF_DATE_KHR) {
            input.resized = true;
            continue;
        }
        if (ar != VK_SUCCESS && ar != VK_SUBOPTIMAL_KHR) fail("image d'écran", ar);
        vkResetFences(g.dev, 1, &fence);
        chrono.cpu("image d'ecran");

        if (gaiaSum.resize(g, sc.extent.width, sc.extent.height)) {      // taille de l'image changée : somme refaite, reliée aux étoiles
            gaia.attachPointsSum(g, gaiaSum.sum.buf);
            if (gaiaBOk) gaiaB.attachPointsSum(g, gaiaSum.sum.buf);
        }
        vkResetCommandBuffer(cmd, 0);
        VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        vkBeginCommandBuffer(cmd, &begin);
        chrono.gpuBegin(cmd);
        gaiaSum.clear(cmd);      // somme par pixel des étoiles Gaia remise à zéro
        // Film du Groupe local : envois et calcul des états à la date de cette image, avant le dessin (film_carte.h).
        if (filmGpuOk) filmGpu.record(cmd);
        cycleApp.recordPoints(cmd, sim, sr);      // éclat et couleur des points du Soleil et des étoiles nommées à cette date
        if (filmGpuNeighboursOk) filmGpuNeighbours.record(cmd);
        chrono.gpu(cmd, "film (etats)");
        // 1. Les étoiles, en grande dynamique.
        transition(cmd, hdr.image, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, 0, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                   VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT);
        // Orbites exactes : la carte rattrape la date montrée (tout d'un coup pendant un contrôle, 64 pas par image sinon).
        const bool skyOnly = sim.skyBand >= 0 && sky.loaded;
        // Étoiles du modèle (Voie lactée, voisines) : leur partie propre à chaque étoile, calculée une fois avant le dessin
        // (gaia.h, precompute) ; mêmes conditions que leur dessin plus bas.
        // Table des galaxies voisines (centres, axes, film) : posée avant le choix des feuilles du précalcul, qui la lit.
        if (!skyOnly && neighbourStarsOk && sim.bestLook) {
            float table[4 * 16] = {};
            for (int k = 0; k < 4; ++k) {
                const Voisine& v = voisines[k];
                Vec3 ct = v.body >= 0 && sim.visible(v.body) ? sim.position(v.body) : v.c0;
                // Film : base = centre écrit par la courbe des étoiles (Sim::filmStarBase), pas l'ancre que suit la caméra ;
                // sinon une galaxie déchirée, au centre écrit bruité, faisait trembler toutes ses étoiles (Marc, 20/11/2026).
                if (neighbourStars.externalStates()) sim.filmStarBase(v.nom, ct);
                const Vec3 a = orbite::versEcliptique({v.axe[0], v.axe[1], v.axe[2]});      // axe galactique -> écliptique
                const float row[16] = {static_cast<float>(v.c0.x), static_cast<float>(v.c0.y), static_cast<float>(v.c0.z), 0,
                                       static_cast<float>(ct.x), static_cast<float>(ct.y), static_cast<float>(ct.z), 0,
                                       static_cast<float>(a.x), static_cast<float>(a.y), static_cast<float>(a.z), v.vrot,
                                       v.rrot, v.agit, neighbourStars.externalStates() ? 1.0f : 0.0f, 0};      // 1 : le film mène (gaia.vert)
                std::memcpy(table + k * 16, row, sizeof(row));
            }
            neighbourStars.setGalaxies(table, 4);
            neighbourStars.setFreeNeighbours(neighbourStars.externalStates());
        }
        if (milkyWayStarsOk) milkyWayStars.precompute(cmd, cam, sc.extent.width, sc.extent.height, pc.par[0], sim.years, !skyOnly && sim.bestLook);
        if (neighbourStarsOk) neighbourStars.precompute(cmd, cam, sc.extent.width, sc.extent.height, pc.par[0], sim.years, !skyOnly && sim.bestLook);
        chrono.gpu(cmd, "precalcul des etoiles du modele");
        {      // étoile suivie de près : ses copies Gaia cachées autour de sa place exacte (gaia.h, setHide ; audit A1)
            Vec3 rel{0, 0, 0};
            double r = 0;
            if (sim.focus >= 0 && sim.bodies[static_cast<size_t>(sim.focus)].kind == Kind::Star && sim.visible(sim.focus) && sim.dist < 0.5) {
                const Vec3 fp = sim.position(sim.focus);
                rel = {fp.x - cam.pos.x, fp.y - cam.pos.y, fp.z - cam.pos.z};
                r = 0.01;      // 630 UA : plus que l'arrondi des orbites de la carte (~200 UA à 8 kpc du centre)
            }
            gaia.setHide(rel, r);
            gaiaB.setHide(rel, r);
        }
        // Étoiles Gaia et Gaia B calculées dans la somme par pixel (gaia_points.h), mêmes conditions et mêmes valeurs que leur dessin.
        {
            const double gaiaLeftNow = sim.starShare() * (1.0 - sim.gaiaFilmOff);
            if (!skyOnly && sim.starShare() > 0 && gaiaLeftNow > 0) {
                bool any = gaia.splat(cmd, cam, sc.extent.width, sc.extent.height, pc.par[0] * static_cast<float>(gaiaLeftNow), sim.years);
                if (gaiaBOk) any = gaiaB.splat(cmd, cam, sc.extent.width, sc.extent.height, pc.par[0] * static_cast<float>(gaiaLeftNow), sim.years) || any;
                if (any) gaiaSum.markUsed();
            }
            gaiaSum.ready(cmd);
        }
        chrono.gpu(cmd, "Gaia (calcul des points)");
        beginPass(cmd, hdr.view, sc.extent);
        if (skyOnly) sky.draw(cmd, cam, sc.extent.width, sc.extent.height);      // fond du ciel dans la lumière choisie, à la place des étoiles et des galaxies
        // Pose propre aux galaxies aux grandes échelles (galaxies_pose.h) : la pose totale des galaxies vaut
        // max(pose de l'écran, gain de la distance de vue) ; près de la Voie lactée, rien ne change.
        const float galFactor = static_cast<float>(galaxies_pose::facteur(sim.dist, sim.autoPose));
        sim.galaxyPose = galaxies_pose::gain(sim.dist);
        if (!skyOnly) galaxies.draw(cmd, cam, sc.extent.width, sc.extent.height, pc.par[0], galFactor, sim.dist);      // exposition des étoiles, relevée aux grandes échelles
        chrono.gpu(cmd, "ciel et galaxies lointaines");
        if (!skyOnly && galaxyShapes.ready) {
            galaxyShapes.deepTime = sim.deepTime();
            galaxyShapes.prepare(cam, galaxies, sc.extent.height);
            float aL[16], aT[16];
            vieillissement.factors(sim.replayGa(), aL, aT);
            galaxyShapes.ageing[0] = aL[1]; galaxyShapes.ageing[1] = aL[2]; galaxyShapes.ageing[2] = aT[1]; galaxyShapes.ageing[3] = aT[2];
            galaxyShapes.draw(cmd, cam, sc.extent.width, sc.extent.height, pc.par[0] * galFactor);
            sim.galaxyShapesShown = galaxyShapes.shown;
        }
        chrono.gpu(cmd, "formes des galaxies");
        // Grandes structures et nuage d'Oort : repères dessinés par-dessus la lumière des galaxies, selon l'échelle regardée.
        structuresClock += dt;
        {
            const double camSun = std::sqrt(cam.pos.x * cam.pos.x + cam.pos.y * cam.pos.y + cam.pos.z * cam.pos.z);
            sim.structures.oortShare = sim.structures.showOort ? structures::oortShare(camSun) : 0.0;
            sim.structures.largeShare = sim.structures.showLarge && structuresOk ? structures::largeShare(sim.dist) : 0.0;
            if (!skyOnly && (sim.structures.oortShare > 0 || sim.structures.largeShare > 0))
                // repères (pas de la lumière) : divisés par la pose automatique, pour garder le même aspect quand elle change
                structuresR.draw(cmd, cam, sc.extent.width, sc.extent.height, sim.structures.oortShare / sim.autoPose, sim.structures.largeShare / sim.autoPose,
                                 sim.years, structuresClock, sim.dist,
                                sim.structures.showSpheres);
        }
        chrono.gpu(cmd, "structures et Oort");
        float ageLum[16], ageTeff[16];
        vieillissement.factors(sim.replayGa(), ageLum, ageTeff);
        sim.ageingShown = vieillissement.ready && std::fabs(sim.replayGa()) > 0.05;
        if (milkyWayStarsOk) { milkyWayStars.setAgeing(ageLum, ageTeff); milkyWayStars.setSunGalacto(sim.sunGalacto()); }
        if (neighbourStarsOk) neighbourStars.setAgeing(ageLum, ageTeff);
        if (!skyOnly && neighbourStarsOk && sim.bestLook) {      // galaxies voisines faites d'étoiles, à toute date (gaia.vert, drapeau 32)
            neighbourStars.draw(cmd, cam, sc.extent.width, sc.extent.height, pc.par[0], sim.years);
        }
        chrono.gpu(cmd, "etoiles des voisines");
        if (!skyOnly && sim.starShare() > 0) {      // étoiles Gaia sur leur orbite calculée ; part qui baisse quand le calcul de la fusion prend le relais
            // Même facteur d'éclat pour la lueur de la Galaxie et pour les étoiles : la lueur est le complément exact des
            // étoiles dessinées (fil Gaia) ; le facteur revient à 1 entre 3 000 et 30 000 années-lumière (Sim::brightnessBoost).
            // Lueur du modèle : cède la place à la Voie lactée calculée en entier quand celle-ci entre (200 à 400 Ma), pour
            // ne pas compter deux fois la même lumière.
            const double loneTime = hasLoneGalaxy ? std::clamp((sim.years - kStartYears - ArmTracerPoints::kFullYears) / (ArmTracerPoints::kEndYears - ArmTracerPoints::kFullYears), 0.0, 1.0) : 0.0;
            // Avec les étoiles visibles du modèle, plus de lueur : la Voie lactée est faite d'étoiles.
            sim.milkyWayModelShare = sim.bestLook && !milkyWayStarsOk ? sim.starShare() * (1.0 - loneTime) : 0.0;
            // vraies photos : tant que les étoiles mesurées sont montrées ; à toute date si les centres de référence les déplacent
            // avec leurs étoiles visibles (autour d'aujourd'hui), la photo n'a que la part qu'elles laissent
            if (sim.milkyWayModelShare > 0)
                milkyWay.draw(cmd, cam, sc.extent.width, sc.extent.height, pc.par[0] * static_cast<float>(sim.milkyWayModelShare), sim.years);
            // Avec les étoiles du modèle : leur gaz ionisé (régions HII) seulement, autour d'aujourd'hui (les bras de la grille
            // sont ceux d'aujourd'hui ; fondu de 1 à 3 Ma comme les traceurs des bras)
            sim.gasShare = sim.showGas && milkyWayStarsOk && sim.milkyWayModelShare <= 0
                               ? sim.starShare() * std::clamp((kLinearLimitYears - std::fabs(sim.years - kStartYears)) / (kLinearLimitYears - 1.0e6), 0.0, 1.0)
                               : 0.0;
            if (sim.gasShare > 0)
                milkyWay.draw(cmd, cam, sc.extent.width, sc.extent.height, pc.par[0] * static_cast<float>(0.3 * sim.gasShare), sim.years, true);      // 0,3 : sans quoi le gaz couvrait les étoiles de taches roses (contrôle en image)
            chrono.gpu(cmd, "lueur de la Voie lactee");
            gaia.improved = sim.bestLook;
            gaiaSky.update(cam, sim.fovDeg, !sim.deepTime());
            gaia.hideSkyOnly = gaiaSky.active && gaiaSky.shownStars > 0;
            sim.gaiaSkyActive = gaiaSky.active;
            sim.gaiaSkyStars = gaiaSky.shownStars;
            sim.gaiaSkyPending = gaiaSky.pendingTiles;
            sim.gaiaSkyLimit = gaiaSky.gLimit;
            const double gaiaLeft = sim.starShare() * (1.0 - sim.gaiaFilmOff);      // revue F1 : Gaia cède au film
            // Gaia entièrement éteint (le film mène, loin d'aujourd'hui) : rien à dessiner, et ses 192 M d'étoiles ne coûtent
            // plus le tri des feuilles à chaque image.
            if (gaiaLeft > 0) gaia.draw(cmd, cam, sc.extent.width, sc.extent.height, pc.par[0] * static_cast<float>(gaiaLeft), sim.years);
            gaiaSum.resolve(cmd);      // étoiles Gaia (et Gaia B) calculées avant la passe : leur somme par pixel
            chrono.gpu(cmd, "Gaia");
            if (sim.gaiaFilmOff < 1.0) gaiaSky.draw(cmd, cam, sc.extent.height, pc.par[0] * static_cast<float>(1.0 - sim.gaiaFilmOff));
            chrono.gpu(cmd, "Gaia (ciel)");
            if (gaiaBOk && gaiaLeft > 0) {
                gaiaB.improved = sim.bestLook;
                gaiaB.draw(cmd, cam, sc.extent.width, sc.extent.height, pc.par[0] * static_cast<float>(gaiaLeft), sim.years);
            }
            chrono.gpu(cmd, "Gaia B");
        }
        // Étoiles visibles de la Voie lactée (contrat docs/contrat-etoiles-visibles.md : toujours dessinées, à toute date) : sur
        // leur orbite exacte, leur lumière vieillie (vieillissement.h). Elles remplacent alors les points du calcul de la fusion
        // et de la « Voie lactée seule » pour la Voie lactée (aucune lumière comptée deux fois).
        sim.milkyWayStarShare = milkyWayStarsOk && sim.bestLook ? 1.0 : 0.0;
        if (!skyOnly && sim.milkyWayStarShare > 0)
            milkyWayStars.draw(cmd, cam, sc.extent.width, sc.extent.height, pc.par[0] * static_cast<float>(sim.milkyWayStarShare), sim.years);
        chrono.gpu(cmd, "etoiles visibles (modele)");
        if (!skyOnly && sim.starShare() > 0) {      // étoiles mesurées, chacune sur son orbite calculée autour de la Galaxie (orbite_galactique.glsl)
            PushConstants orbiting = pc;
            orbiting.par[0] *= static_cast<float>(sim.starShare());
            // Étoile suivie : posée à sa place calculée en double précision (orbites_gpu.h, Push::focus), là où la caméra la vise.
            int focusStar = -1;
            Vec3 focusRel{0, 0, 0};
            if (sim.focus >= 0 && sim.bodies[static_cast<size_t>(sim.focus)].kind == Kind::Star && sim.visible(sim.focus)) {
                const Vec3 fp = sim.position(sim.focus);
                focusStar = static_cast<int>(sim.bodies[static_cast<size_t>(sim.focus)].star);
                focusRel = {fp.x - cam.pos.x, fp.y - cam.pos.y, fp.z - cam.pos.z};
            }
            orbits.draw(cmd, sr, orbiting, sc.extent.width, sc.extent.height, sim.years, orbite::poidsOrbite(sim.years), focusStar, focusRel);      // années depuis J2000, date des positions
        }
        chrono.gpu(cmd, "etoiles principales");
        if (!skyOnly && loneGalaxy.count && milkyWayCentre >= 0 && sim.milkyWayStarShare <= 0)
            loneGalaxy.draw(cmd, cam, sim.position(milkyWayCentre), pc.par[0], 0.35f, loneShare, sc.extent.width, sc.extent.height);
        if (!skyOnly && fusionCloud.count && milkyWayCentre >= 0 && !(sim.milkyWayStarShare > 0 && neighbourStarsOk))
        {
            // avec les centres de référence, les autres galaxies sont leurs photos déplacées en bloc : seuls les points de la Voie lactée
            fusionCloud.draw(cmd, cam, sim.position(milkyWayCentre), pc.par[0], 0.35f, fusionShare, sc.extent.width, sc.extent.height, 0,
                             sim.centres && neighbourStarsOk ? fusionCloud.milkyWayPoints : 0u);
            if (!neighbourStarsOk)      // sans les étoiles des voisines : les points du calcul montrent les autres galaxies
                fusionCloud.draw(cmd, cam, sim.position(milkyWayCentre), pc.par[0], 0.35f, companionShare, sc.extent.width, sc.extent.height, fusionCloud.milkyWayPoints);
        }
        if (!skyOnly && (fusionPoints.count || clones.count || armTracers.count)) {
            PushConstants still = pc;      // les étoiles du calcul sont déjà à leur place : pas de mouvement propre à ajouter
            still.par[2] = 0;
            sr.bind(cmd, still, sc.extent.width, sc.extent.height);
            fusionPoints.draw(cmd);
            clones.draw(cmd);
            armTracers.draw(cmd);
        }
        if (!skyOnly && sim.showNebulae) {      // après les étoiles et les galaxies (la poussière les assombrit), avant les planètes
            const double camSun = std::sqrt(dot(cam.pos, cam.pos));
            const double part = std::clamp((kLinearLimitYears - std::fabs(sim.years - kStartYears)) / (kLinearLimitYears - 1.0e6), 0.0, 1.0) *
                                std::clamp((6.0e4 - camSun) / 3.0e4, 0.0, 1.0);
            nebulae.draw(cmd, cam, sc.extent.width, sc.extent.height, part);
            // Poussière MESURÉE en 3D (Edenhofer et al. 2024, grille locale de voie_lactee.bin) : vue de loin (plus de 4 000 al
            // du Soleil, fondu jusqu'à 6 500), ses nuages assombrissent les étoiles derrière eux. Pas de près : les magnitudes
            // mesurées contiennent déjà la poussière vue du Soleil, elle serait comptée deux fois.
            const double dustPart = std::clamp((camSun - 4000.0) / 2500.0, 0.0, 1.0) * std::clamp((2.0e5 - camSun) / 1.0e5, 0.0, 1.0) *
                                    std::clamp((kLinearLimitYears - std::fabs(sim.years - kStartYears)) / (kLinearLimitYears - 1.0e6), 0.0, 1.0);
            if (dustPart > 0.002) milkyWay.draw(cmd, cam, sc.extent.width, sc.extent.height, static_cast<float>(dustPart), sim.years, false, true);
            sr.bind(cmd, pc, sc.extent.width, sc.extent.height);      // le dessin des étoiles reprend ensuite
        }
        chrono.gpu(cmd, "fusion, clones, traceurs");
        asteroids.draw(cmd, cam, {cam.pos.x / kAuInLy, cam.pos.y / kAuInLy, cam.pos.z / kAuInLy}, 2451545.0 + sim.years * 365.25 - asteroids.epochJd,
                       sc.extent.width, sc.extent.height, asteroids.ready && !skyOnly ? pc.par[0] * static_cast<float>(sim.asteroidGain(asteroids.epochJd)) : 0.0f);      // pose des étoiles × fondu en temps (audit A6, C4) ; seulement en lumière visible
        chrono.gpu(cmd, "asteroides");
        // (l'ordre compte : après les astéroïdes, le dessin des étoiles n'est plus lié ; les planètes le relient)
        sr.bind(cmd, pc, sc.extent.width, sc.extent.height);
        planets.draw(cmd);
        if (!skyOnly) dwarfGalaxies.draw(cmd);
        if (!skyOnly) blackHoles.draw(cmd, sr, pc, sc.extent.width, sc.extent.height);
        if (!skyOnly) exoplanets.draw(cmd, sr, pc, sc.extent.width, sc.extent.height);
        chrono.gpu(cmd, "planetes, naines, trous noirs, exoplanetes");
        spheres.draw(cmd, sc.extent.width, sc.extent.height);
        if (!skyOnly) starMatter.draw(cmd, cycleApp, sim, cam, sc.extent.width, sc.extent.height, pc.par[0]);      // nuage, vents, nébuleuse, reste de supernova
        chrono.gpu(cmd, "spheres");
        if (planets.count > planets.backCount) {      // lunes et planètes devant la sphère la plus proche (audit E2)
            sr.bind(cmd, pc, sc.extent.width, sc.extent.height);
            planets.draw(cmd, true);
        }
        vkCmdEndRendering(cmd);
        transition(cmd, hdr.image, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                   VK_ACCESS_SHADER_READ_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        // 2. Conversion pour l'écran, puis l'interface par-dessus.
        transition(cmd, final.image, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, 0, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
                   VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT);
        beginPass(cmd, final.view, sc.extent);
        screen.draw(cmd, sc.extent, sim.bestLook && sim.photoExposure ? static_cast<float>(sim.exposureEv > 0 ? 1.0 : std::clamp(sim.photoWeight, 0.0, 1.0)) : 0.0f,
                    static_cast<float>(autoPose.pose));      // étirement « photo » fondu avec le poids des objets qui règlent la pose
        chrono.gpu(cmd, "conversion pour l'ecran");
        ImGui_ImplVulkan_RenderDrawData(ImGui::GetDrawData(), cmd);
        vkCmdEndRendering(cmd);
        chrono.gpu(cmd, "interface (dessin)");
        autoPose.measure(cmd, sc.extent);      // histogramme de cette image, lu à la suivante
        chrono.gpu(cmd, "pose automatique");
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
        chrono.gpu(cmd, "copie dans la fenetre");
        check(vkEndCommandBuffer(cmd), "fin des commandes");
        chrono.cpu("enregistrement des commandes");

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
        chrono.cpu("envoi");
        // Affichage remis au tour suivant, après le travail du processeur qui ne touche pas à la carte (gestes, date, caméra,
        // choix des étoiles) : ce travail se fait pendant que la carte dessine cette image (cadence, 20/11/2026 : l'affichage
        // attendait la fin du dessin, et tout ce travail venait après). Affichée au plus quelques ms plus tard.
        pendingIndex = index;
        hasPending = true;
        chrono.gpuSubmitted();
        chrono.endFrame(frameWallMs, sim.dist, sim.years);

        ++frame;
        if (test && pathActive) {      // mesure du trajet : années parcourues et images, à l'horloge réelle
            if (pathFrames == 0) pathYears0 = sim.years;
            ++pathFrames;
            pathWall += dt;
        }
        if (test && (holdOn || pathActive || (gaiaOk && gaiaLiveNow && gaia.orbitLagSteps() != 0))) frame = 0;
        if (test && opt.stopAfter > 0 && ++loops >= opt.stopAfter) break;      // contrôle : image prise en route, calcul en cours compris      // contrôle : les images ne comptent qu'une fois la date atteinte et calculée
        ++shown;
        titleTimer += dt;
        if (!test && titleTimer > 0.5) {
            char title[120];
            std::snprintf(title, sizeof(title), "Univers  |  %.0f images par seconde", shown / titleTimer);
            SetWindowTextA(hwnd, title);
            titleTimer = 0;
            shown = 0;
        }
        if (geste.on) {      // geste rejoué : on s'arrête à sa fin
            if (geste.t > geste.secondes + 1.0) break;
            frame = 0;
        }
        if (test && frame >= opt.testFrames && sweep.next(g, final, sc.extent, sim)) frame = 0;      // balayage : vue suivante
        else if (test && frame >= opt.testFrames) break;
    }
    presentPending();
    vkDeviceWaitIdle(g.dev);
    if (opt.checkFilm) {      // contrôle : états écrits sur la carte par le film, comparés au lecteur du processeur (même date) ; AVANT toute libération : le tampon relu appartient à milkyWayStars / neighbourStars
        vkDeviceWaitIdle(g.dev);
        auto controle = [&](const char* nom, FilmStars& fs, GaiaRenderer& r, double t) {
            if (t < 0 || !fs.ready || fs.ordre.empty()) { std::printf("controle du film (%s) : le film n'a pas mene sur la carte -> SANS OBJET\n", nom); return; }
            const uint32_t n = static_cast<uint32_t>(fs.ordre.size());
            const std::vector<float> got = r.orbitsForFilm().readBack(g, n);
            std::vector<float> ref;
            if (!fs.states(t, {}, {}, ref)) { std::printf("controle du film (%s) : lecture du processeur impossible -> ECHEC\n", nom); return; }
            std::vector<double> err(n), errV(n);
            for (uint32_t k = 0; k < n; ++k) {
                const float* a = &got[k * 8]; const float* b = &ref[k * 8];
                err[k] = std::sqrt(double(a[0] - b[0]) * (a[0] - b[0]) + double(a[1] - b[1]) * (a[1] - b[1]) + double(a[2] - b[2]) * (a[2] - b[2])) * 1000.0;
                errV[k] = std::sqrt(double(a[4] - b[4]) * (a[4] - b[4]) + double(a[5] - b[5]) * (a[5] - b[5]) + double(a[6] - b[6]) * (a[6] - b[6]));
            }
            std::sort(err.begin(), err.end());
            std::sort(errV.begin(), errV.end());
            const bool ok = err[n * 99 / 100] < 0.1 && errV[n * 99 / 100] < 0.5;
            std::printf("controle du film (%s, format %d) a %.6f milliards d'annees, %u etoiles : ecart carte - processeur : position mediane %.5f pc, 99e centile %.4f pc, "
                        "maximum %.3f pc ; vitesse 99e centile %.4f km/s, maximum %.3f km/s -> %s\n", nom, fs.v3 ? 3 : 2, t, n, err[n / 2], err[n * 99 / 100], err[n - 1],
                        errV[n * 99 / 100], errV[n - 1], ok ? "PASSE" : "ECHEC");
        };
        if (filmStarsOk && milkyWayStarsOk) controle("Voie lactee", filmStars, milkyWayStars, filmGpuT);
        if (filmNeighboursOk && neighbourStarsOk) controle("voisines", filmNeighbours, neighbourStars, filmGpuNeighboursT);
    }
    if (geste.log) std::fclose(geste.log);
    if (outerThread.joinable()) outerThread.join();
    if (test) {
        const double total = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        if (opt.hasPath && pathFrames > 1 && pathWall > 0)
            std::printf("trajet : %.4g annees en %.3f s (%ld images) : %.4g annees par seconde, %.1f images par seconde\n", std::fabs(sim.years - pathYears0), pathWall,
                        pathFrames, std::fabs(sim.years - pathYears0) / pathWall, pathFrames / pathWall);
        // Contrôle « même date, même résultat » : empreinte des états des étoiles visibles à la date finale (à comparer entre
        // un saut direct et des trajets à différentes vitesses).
        if (milkyWayStarsOk && milkyWayStars.externalStates()) {
            const GaiaOrbits& o = milkyWayStars.orbits();
            const uint32_t m = std::min<uint32_t>(o.count, 1000000);
            const std::vector<float> e = o.readBack(g, m);
            double sx = 0, sy = 0, sz = 0, sv = 0;
            for (uint32_t i = 0; i + 1 < m; ++i) { sx += e[i * 8]; sy += e[i * 8 + 1]; sz += e[i * 8 + 2]; sv += std::fabs(e[i * 8 + 4]) + std::fabs(e[i * 8 + 5]); }
            std::printf("empreinte des etats (film, %u etoiles) a l'an %.3f : x %.9g  y %.9g  z %.9g  |v| %.9g ; etoile 12345 : %.7g %.7g %.7g\n", m - 1, sim.years, sx, sy, sz, sv,
                        e[12345 * 8], e[12345 * 8 + 1], e[12345 * 8 + 2]);
        }
        if (filmGpuOk) std::printf("film sur la carte : %ld images envoyees\n", filmGpu.uploads);
        std::printf("etoiles dessinees a la derniere image : Gaia %llu, Gaia B %llu, modele %llu, voisines %llu\n", static_cast<unsigned long long>(gaia.drawn),
                    static_cast<unsigned long long>(gaiaB.drawn), static_cast<unsigned long long>(milkyWayStars.drawn), static_cast<unsigned long long>(neighbourStars.drawn));
        if (!opt.capture.empty()) writeCapture(g, final, sc.extent, opt.capture);
        if (!opt.capture.empty() && sim.asteroidCat) {      // mesure : durée d'une recherche de l'astéroïde sous un clic
            const auto t0 = std::chrono::steady_clock::now();
            const int k = sim.nearestAsteroid(sim.camera(static_cast<double>(sc.extent.width) / sc.extent.height), sc.extent.width * 0.5, sc.extent.height * 0.5, sc.extent.width, sc.extent.height, 12.0);
            const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
            std::printf("clic sur un asteroide : %.1f ms pour %llu orbites (trouve : %d)\n", ms, static_cast<unsigned long long>(sim.asteroidCat->n), k);
        }
        if (!opt.capture.empty() && sim.stars) {      // mesure : durée d'une recherche de l'étoile sous un clic au centre de l'image
            const auto t0 = std::chrono::steady_clock::now();
            const int64_t k = sim.nearestCatalogStar(sim.camera(static_cast<double>(sc.extent.width) / sc.extent.height), sc.extent.width * 0.5,
                                                     sc.extent.height * 0.5, sc.extent.width, sc.extent.height, 12.0, 99.0);
            const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
            std::printf("clic sur une etoile : %.1f ms pour %llu etoiles (trouvee : %lld)\n", ms, static_cast<unsigned long long>(sim.stars->n), static_cast<long long>(k));
        }
        std::printf("premier passage d'Andromede : %.3f milliards d'annees ; etoiles mesurees montrees jusqu'a %.3f (fondu depuis %.3f) ; part des etoiles mesurees a cette date : %.2f\n",
                    sim.firstPassageGa, sim.starEraEndYears / 1.0e9, sim.starEraFadeYears / 1.0e9, sim.starShare());
        if (milkyWayStarsOk)
        {
            std::printf("film du Groupe local a cette date : %s (film de %.3f a %.3f milliards d'annees, %d images)\n", sim.filmLeads ? "il mene les etoiles visibles" : "non",
                        filmStarsOk ? filmStars.startGa() : 0.0, filmStarsOk ? filmStars.endGa() : 0.0, filmStarsOk ? filmStars.imageCount() : 0);
            std::printf("etoiles du modele : orbites exactes au pas %ld, retard %ld pas, pretes %d ; feuilles en epicycles %u sur %u ; sous-nuages replies %llu\n", milkyWayStars.orbitStep(),
                        milkyWayStars.orbitLagSteps(), milkyWayStars.orbitReady() ? 1 : 0, milkyWayStars.epicycleLeaves(), milkyWayStars.leafCount(),
                        static_cast<unsigned long long>(milkyWayStars.collapsedLeaves));
            // contrôle du repère : Soleil selon l'appli (CPU), Soleil selon la carte graphique (dernier état), centre des étoiles
            const phys::Vec3 suc = sim.sunGalacto();
            const auto& ob = milkyWayStars.orbits();
            const auto sg = ob.readBack(g, 1, ob.count - 1);
            const uint32_t m = std::min<uint32_t>(ob.count - 1, 400000);
            const auto st = ob.readBack(g, m, 0);
            double cx = 0, cy = 0, cz = 0;
            for (uint32_t i = 0; i < m; ++i) { cx += st[i * 8]; cy += st[i * 8 + 1]; cz += st[i * 8 + 2]; }
            std::printf("repere : Soleil appli (%.3f, %.3f, %.3f) kpc ; Soleil carte (%.3f, %.3f, %.3f) ; centre des etoiles (%.3f, %.3f, %.3f)\n",
                        suc.x, suc.y, suc.z, sg[0], sg[1], sg[2], cx / m, cy / m, cz / m);
        }
        std::printf("fenetre cachee %ux%u : %d images en %.3f s, soit %.1f images par seconde ; astre suivi : %s ; date : %s ; ephemerides : %s\nPASSE\n",
                    sc.extent.width, sc.extent.height, frame, total, frame / total, sim.bodies[static_cast<size_t>(sim.focus)].name.c_str(),
                    frDate(sim.years).c_str(), !hasSpk ? spkError.c_str() : sim.ephemValid ? "lues" : "hors plage");
    }

    gUiImages = nullptr;
    uiImages.release(g);      /* avant l'arrêt de l'interface : ses images y sont inscrites */
    ImGui_ImplVulkan_Shutdown();
    ImGui_ImplWin32_Shutdown();
    ImGui::DestroyContext();
    vkDestroyDescriptorPool(g.dev, uiPool, nullptr);
    vkDestroyFence(g.dev, fence, nullptr);
    chrono.summary();
    chrono.release(g);
    vkDestroySemaphore(g.dev, acquired, nullptr);
    vkDestroySemaphore(g.dev, rendered, nullptr);
    screen.release(g);
    gaiaSum.release(g);
    autoPose.release(g);
    nebulae.release(g);
    planets.release(g);
    dwarfGalaxies.release(g);
    blackHoles.release(g);
    exoplanets.release(g);
    gaiaSky.destroy(g);
    if (gaiaBOk) gaiaB.release(g);
    filmGpu.release(g);
    filmGpuNeighbours.release(g);
    if (milkyWayStarsOk) milkyWayStars.release(g);
    if (neighbourStarsOk) neighbourStars.release(g);
    gaia.release(g);
    milkyWay.release(g);
    fusionPoints.release(g);
    fusionCloud.release(g);
    loneGalaxy.release(g);
    clones.release(g);
    armTracers.release(g);
    asteroids.release(g);
    galaxies.release(g);
    galaxyShapes.release(g);
    structuresR.release(g);
    spheres.release(g);
    starMatter.release(g);
    if (opt.checkOrbits) {      // contrôle : états relus sur la carte, comparés au calcul en double précision (bibliothèque de physique)
        const uint32_t n = std::min<uint32_t>(20000, orbits.count);
        const std::vector<float> got = orbits.readBack(g, n);
        std::vector<phys::Vec3> p0(n), v0(n);
        for (uint32_t k = 0; k < n; ++k) {
            p0[k] = {orbits.initial[k * 8], orbits.initial[k * 8 + 1], orbits.initial[k * 8 + 2]};
            v0[k] = {orbits.initial[k * 8 + 4], orbits.initial[k * 8 + 5], orbits.initial[k * 8 + 6]};
        }
        phys::galaxie::Orbites ref(p0, v0);
        ref.avance(static_cast<double>(orbits.stepLo) * 1.0e-3);
        std::vector<double> err(n);
        for (uint32_t k = 0; k < n; ++k) {
            const phys::Vec3 r = ref.position(k);
            const double dx = got[k * 8] - r.x, dy = got[k * 8 + 1] - r.y, dz = got[k * 8 + 2] - r.z;
            err[k] = std::sqrt(dx * dx + dy * dy + dz * dz) * 1000.0;      // parsecs
        }
        std::sort(err.begin(), err.end());
        const double med = err[n / 2], p99 = err[n * 99 / 100];
        const bool ok = med < 1.0 && p99 < 10.0;
        std::printf("orbites sur la carte graphique, pas %ld (%.0f millions d'annees), %u etoiles : ecart avec le calcul en double precision : mediane %.4f pc, 99e centile %.3f pc, maximum %.2f pc -> %s\n",
                    orbits.stepLo, static_cast<double>(orbits.stepLo), n, med, p99, err[n - 1], ok ? "PASSE" : "ECHEC");
    }
    orbits.release(g);
    sky.release(g);
    sr.release(g);
    hdr.release(g);
    final.release(g);
    destroySwapchain(g, sc);
    vkDestroySurfaceKHR(g.instance, surface, nullptr);
    vkDestroyCommandPool(g.dev, g.pool, nullptr);
    vkDestroyDevice(g.dev, nullptr);
    destroyInstance(g);      // et les messages de validation (--validation)
    DestroyWindow(hwnd);
    return 0;
}
