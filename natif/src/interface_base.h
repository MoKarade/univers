// Appli PC « Univers » : ce qui est écrit et cliquable à l'écran (Dear ImGui), habillé aux couleurs de la page.
// Tout ce qu'il faut savoir pour s'en servir est écrit à l'écran : rien n'est à lire ailleurs.
//
// Prise en main :
//  - au premier lancement, un mot d'accueil propose une visite guidée ou d'explorer seul ;
//  - cliquer sur un astre (son point ou son nom) y fait voler la caméra ; « Retour » refait le chemin inverse ;
//  - taper un nom n'importe quand ouvre la recherche ; flèches et Entrée choisissent ;
//  - « Aller à » rassemble les échelles (touches 1 à 5), le système solaire, les étoiles et les galaxies nommées ;
//  - F1 ou « ? » : toutes les commandes.
#pragma once
#include <imgui.h>

#include "interface_outils.h"
#include "simulation.h"
#include "interface_theme.h"

namespace {

// Projection sans rejet des points hors de l'écran (pour les tracés) ; false si le point est derrière la caméra.
bool projectLoose(const Camera& cam, Vec3 p, float w, float h, ImVec2& out) {
    const Vec3 d = p - cam.pos;
    const double z = dot(d, cam.fwd);
    if (z <= 0) return false;
    out = {static_cast<float>((dot(d, cam.right) / (z * cam.tanHalf * cam.aspect) * 0.5 + 0.5) * w),
           static_cast<float>((-dot(d, cam.up) / (z * cam.tanHalf) * 0.5 + 0.5) * h)};
    return std::fabs(out.x) < 1.0e5f && std::fabs(out.y) < 1.0e5f;
}

// Rayon apparent du disque d'un astre, en pixels (0 pour une étoile lointaine).
double discRadiusPx(const Sim& sim, const Camera& cam, int i, float h) {
    const Vec3 d = sim.position(i) - cam.pos;
    const double dist = std::max(std::sqrt(dot(d, d)), 1e-30);
    return (sim.bodies[static_cast<size_t>(i)].radiusKm / kLyInKm) / dist / (2.0 * cam.tanHalf / h);
}

double distBetween(Vec3 a, Vec3 b) {
    const Vec3 d = a - b;
    return std::sqrt(dot(d, d));
}

// Orbites : la trajectoire réelle lue dans les éphémérides sur un tour centré sur la date courante.
struct OrbitCache {
    static constexpr int kPoints = 240;
    struct Track {
        double atYears = 1e300;
        bool valid = false;
        std::vector<Vec3> pts;      // positions relatives à l'astre parent (Soleil, ou Terre pour la Lune)
    };
    std::vector<Track> tracks;

    void update(const Sim& sim) {
        tracks.resize(sim.bodies.size());
        for (size_t i = 0; i < sim.bodies.size(); ++i) {
            const Body& b = sim.bodies[i];
            if (b.kind != Kind::Planet) continue;
            Track& t = tracks[i];
            // Tracé centré sur la date arrondie à une grille fixe (1/240 de tour) : il ne dépend que de la date montrée, pas du
            // chemin suivi pour y arriver (avant : centré sur la dernière date recalculée, d'où un léger retard après un défilement).
            const double step = b.periodYears / 240.0;
            const double at0 = step > 0 ? std::round(sim.years / step) * step : sim.years;
            if (t.atYears == at0) continue;
            t.atYears = at0;
            t.pts.resize(kPoints + 1);
            t.valid = true;
            for (int k = 0; k <= kPoints && t.valid; ++k) {
                const double at = at0 + (static_cast<double>(k) / kPoints - 0.5) * b.periodYears;
                Vec3 p, parent{0, 0, 0};
                t.valid = sim.planetAt(b.posNaif, at, p) && (b.parent <= 0 || sim.planetAt(sim.bodies[static_cast<size_t>(b.parent)].posNaif, at, parent));
                t.pts[static_cast<size_t>(k)] = p - parent;
            }
        }
    }
};

// Échelles : le Soleil vu de plus en plus loin (touches 1 à 5).
struct Scale {
    const char* label;
    double distLy;
};
const Scale kScales[] = {{"Système solaire", 45.0 * kAuInLy},
                         {"Étoiles voisines du Soleil", 30.0},
                         {"Étoiles mesurées autour du Soleil", 300.0},
                         {"Groupe local de galaxies", 5.0e6},
                         {"Univers lointain", 5.0e9}};
constexpr int kScaleCount = 5;

// Visite guidée : chaque étape vole vers un astre, puis reste quelques secondes avec une légende.
struct TourStop {
    const char* body;
    double distLy;      // 0 : distance d'arrivée habituelle
};
const TourStop kTour[] = {{"Terre", 0},          {"Lune", 0},
                          {"Soleil", 45.0 * kAuInLy}, {"Jupiter", 0},
                          {"Saturne", 0},        {"Soleil", 30.0},
                          {"Soleil", 300.0},    {"Andromède (M31)", 0},
                          {"Soleil", 5.0e9}};
constexpr int kTourCount = static_cast<int>(sizeof(kTour) / sizeof(kTour[0]));
constexpr double kTourHoldSeconds = 7.0;

struct UiState {
    char search[64] = "";
    int searchSel = 0;
    bool focusSearch = false, cursorToEnd = false;
    char dateText[32] = "";
    bool dateError = false;
    ImFont* normal = nullptr;
    ImFont* big = nullptr;
    OrbitCache orbits;
    float s = 1.0f;                 // échelle de l'interface (1 pour un écran de 1080 lignes)
    bool started = false;
    bool welcome = false, help = false, openGoTo = false;
    bool keepGoTo = false;
    bool completeness = false;      // détail de la complétude ouvert
    bool openNotes = false;
    bool howOpen = false;           // tableau « Comment c'est obtenu » ouvert
    bool tasksOpen = false;         // détail des calculs de fond ouvert
    float timeRight = 0, howW = 0;  // bord droit de la barre du temps, largeur de la ligne « Comment c'est obtenu »         // contrôle : « Ce qui est mesuré, calculé ou supposé » déplié
    std::string astQuery;           // recherche d'astéroïdes : dernier texte cherché (123 530 noms : on ne refait pas à chaque image)
    std::vector<int> astFound;
    ui_outils::NameIndex astIndex;  // construit à la première recherche
    ImVec2 goToAnchor{0, 0};
    float searchRight = 0, timeW = 0, timeBottom = 0;
    float completenessBottom = 0, completenessW = 0;      // place prise par la ligne de complétude      // place prise par la recherche et la barre du temps (image précédente)        // le menu « Aller à » s'ouvre sous son bouton          // contrôle : le menu « Aller à » reste ouvert pour la capture
    int cardClosedFor = -1;         // fiche fermée pour cet astre
    int armSel = -1;                // traceur de bras spiral choisi au clic (-1 : aucun)
    int tour = -1;                  // étape de la visite guidée (-1 : pas de visite)
    int gwCount = 0;                // ondes gravitationnelles chargées (interface_ondes.h)
    bool gwOpen = false;            // leur fenêtre est ouverte
    bool details = false;           // interface minimaliste (Marc, 13/11/2026) : textes détaillés à l'écran seulement sur demande
    bool openDate = false;          // « Aller à une date… » choisi dans le menu « … » de la barre du temps
    double tourClock = 0;
    float dockTop = 1e9f, dockLeft = 1e9f;
    float statusW = 0, toolbarBottom = 0;      // largeur de « tu regardes », bas de la barre d'outils (image précédente)      // haut et bord gauche du lecteur de temps (image précédente)
    bool keepNotes = false;         // contrôle : la bulle « mesuré, calculé ou supposé à cette date » reste ouverte
};

float px(const UiState& ui, float v) { return v * ui.s; }

// ---------------------------------------------------------------- échelle et départ

void applyScale(UiState& ui, float h) {
    const float s = std::clamp(h / 1000.0f, 1.0f, gFontMaxScale);
    ImGui::GetIO().FontGlobalScale = s / gFontMaxScale;
    if (std::fabs(s - ui.s) < 0.01f && ui.started) return;
    ui.s = s;
    ImGuiStyle fresh;
    ImGui::GetStyle() = fresh;
    applyStyle();
    ImGui::GetStyle().ScaleAllSizes(s);
}

int bodyByName(const Sim& sim, const char* name) {
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
        if (sim.bodies[static_cast<size_t>(i)].name == name) return i;
    return -1;
}

// Centre des échelles : le Soleil ; quand il n'a plus de position (temps profond), le centre de la Voie lactée.
int scaleCenter(const Sim& sim) {
    if (sim.visible(0)) return 0;
    const int c = bodyByName(sim, "Centre de la Voie lactée");
    return c >= 0 ? c : 0;
}

// Éclipses de Soleil : maximum de chacune (années juliennes depuis J2000, temps universel), calculé d'après les
// éphémérides de la NASA et contrôlé contre le catalogue des éclipses de la NASA (lignes 09565 à 09570, axe de
// l'ombre à moins de 1,5° du point du maximum ; essai_eclipse, fil du rendu).
struct Eclipse {
    const char* label;
    double years;
};
const Eclipse kEclipses[] = {{"Éclipse annulaire du 17 février 2026", 26.13007063}, {"Éclipse totale du 12 août 2026", 26.61256739},
                             {"Éclipse annulaire du 6 février 2027", 27.09970273},  {"Éclipse totale du 2 août 2027", 27.58363123},
                             {"Éclipse annulaire du 26 janvier 2028", 28.06880339}, {"Éclipse totale du 22 juillet 2028", 28.55474849}};
constexpr int kEclipseCount = static_cast<int>(sizeof(kEclipses) / sizeof(kEclipses[0]));
const char* const kEclipseStatus = "calculé d'après les éphémérides de la NASA ; contrôlé contre le catalogue des éclipses de la NASA";

// La prochaine après la date affichée (-1 : aucune dans la liste).
int nextEclipse(double years) {
    for (int k = 0; k < kEclipseCount; ++k)
        if (kEclipses[k].years > years + 1.0 / 365.25) return k;
    return -1;
}
// L'éclipse en cours à la date affichée (à 4 heures près du maximum), ou -1.
int eclipseNow(double years) {
    for (int k = 0; k < kEclipseCount; ++k)
        if (std::fabs(kEclipses[k].years - years) < 4.0 / 24.0 / 365.25) return k;
    return -1;
}

// La caméra suit la Terre et regarde dans l'axe Soleil-Lune, pour voir l'ombre de la Lune ; le temps est arrêté au maximum.
void showEclipse(Sim& sim, UiState& ui, int k) {
    if (k < 0 || k >= kEclipseCount) return;
    const int earth = bodyByName(sim, "Terre");
    ui.tour = -1;
    ui.welcome = false;
    sim.years = kEclipses[k].years;
    sim.paused = true;
    sim.backward = false;
    sim.rate = 1;      // 1 heure par seconde : l'ombre traverse la Terre en quelques secondes
    sim.speed = 0;
    sim.refreshEphemeris();
    if (earth < 0 || !sim.visible(earth)) return;
    sim.flyTo(earth);
    // Regard au-dessus de l'ombre : là où l'axe Soleil-Lune touche la Terre (à défaut, le point de l'axe le plus proche).
    const Vec3 e = sim.position(earth);
    Vec3 look{-e.x, -e.y, -e.z};      // sans la Lune : regard depuis le Soleil
    const int moon = bodyByName(sim, "Lune");
    if (moon >= 0 && sim.visible(moon)) {
        const Vec3 m = sim.position(moon);
        const double ml = std::max(std::sqrt(dot(m, m)), 1e-30);
        const Vec3 d{m.x / ml, m.y / ml, m.z / ml};      // du Soleil vers la Lune, prolongé vers la Terre
        const Vec3 me = m - e;
        const double b = dot(me, d), c = dot(me, me), rE = sim.bodies[static_cast<size_t>(earth)].radiusKm / kLyInKm;
        const double disc = b * b - (c - rE * rE);
        const double t = disc >= 0 ? -b - std::sqrt(disc) : -b;      // première rencontre avec la sphère, ou point le plus proche
        look = {me.x + t * d.x, me.y + t * d.y, me.z + t * d.z};
    }
    const double r = std::max(std::sqrt(dot(look, look)), 1e-30);
    sim.yaw = std::atan2(look.y, look.x);
    sim.pitch = std::asin(std::clamp(look.z / r, -1.0, 1.0));
}

void startTour(Sim& sim, UiState& ui, int step) {
    ui.welcome = false;
    for (; step < kTourCount; ++step) {
        const int i = bodyByName(sim, kTour[step].body);
        if (i >= 0 && sim.visible(i)) {
            ui.tour = step;
            ui.tourClock = 0;
            sim.flyTo(i, kTour[step].distLy);
            return;
        }
    }
    ui.tour = -1;      // plus d'étape possible : fin de la visite
}

void showVoyagerJupiter(Sim& sim, UiState& ui);

// Au premier dessin : mot d'accueil, et réglages de contrôle (variable UNIVERS_ECRAN, pour les captures sans fenêtre).
void firstFrame(Sim& sim, UiState& ui) {
    if (ui.started) return;
    ui.started = true;
    ui.welcome = !sim.touched;
    const char* env = std::getenv("UNIVERS_ECRAN");
    const std::string e = env ? env : "";
    if (e == "accueil") ui.welcome = true;
    if (e == "aide") ui.help = true;
    if (e == "completude") ui.completeness = true;
    if (e == "notes") ui.openNotes = true;
    if (e == "methode") ui.howOpen = true;
    if (e == "calculs") ui.tasksOpen = true;
    if (e == "menu") ui.keepGoTo = true;
    if (e == "details") ui.details = true;
    if (e != "fiche") ui.cardClosedFor = sim.focus;      // minimaliste : la fiche s'ouvre au clic sur un astre, pas au départ
    if (e.rfind("recherche:", 0) == 0) std::snprintf(ui.search, sizeof(ui.search), "%s", e.substr(10).c_str());
    if (e.rfind("visite:", 0) == 0) {
        startTour(sim, ui, std::atoi(e.substr(7).c_str()));
        sim.stepFlight(Sim::kFlySeconds);      // capture : l'étape est atteinte
    }
    if (e.rfind("asteroide:", 0) == 0) {      // asteroide:<texte cherché> : le premier trouvé
        const std::vector<int> k = sim.asteroidCat ? sim.asteroidCat->search(e.substr(10), 1) : std::vector<int>{};
        const int i = k.empty() ? -1 : sim.selectAsteroid(k[0]);
        if (i >= 0) {
            sim.flyTo(i);
            sim.stepFlight(Sim::kFlySeconds);
        }
    }
    if (e == "voyager") {
        showVoyagerJupiter(sim, ui);
        sim.stepFlight(Sim::kFlySeconds);
    }
    if (e.rfind("eclipse", 0) == 0) {      // eclipse ou eclipse:<rang dans la liste>
        showEclipse(sim, ui, e.size() > 8 ? std::atoi(e.substr(8).c_str()) : nextEclipse(kStartYears));
        sim.stepFlight(Sim::kFlySeconds);
    }
    if (e.rfind("vol:", 0) == 0) {      // vol:<nom>:<avancement 0 à 1>
        const size_t cut = e.rfind(':');
        const int i = bodyByName(sim, e.substr(4, cut - 4).c_str());
        if (i >= 0) {
            sim.flyTo(i);
            sim.stepFlight(std::atof(e.substr(cut + 1).c_str()) * Sim::kFlySeconds);
        }
    }
}

// ---------------------------------------------------------------- orbites, noms, survol

void drawOrbits(Sim& sim, UiState& ui, const Camera& cam, float w, float h) {
    if (!sim.ephemValid) {      // au-delà de 10 millions d'années : seule l'orbite de la Terre est connue (chaos.h)
        double e = 0, peri = 0, spread = 0;
        const double after = sim.years - chaos::kStartYears;
        if (after < 1.0e7 || !sim.chaosRun.orbit(after, e, peri, spread)) return;
        ImDrawList* dl = ImGui::GetBackgroundDrawList();
        ImVec2 prev;
        bool hasPrev = false;
        for (int k = 0; k <= 180; ++k) {
            const double nu = 2.0 * kPi * k / 180.0, r = (1.0 - e * e) / (1.0 + e * std::cos(nu)) * kAuInLy;
            ImVec2 at;
            const bool ok = projectLoose(cam, {r * std::cos(nu + peri), r * std::sin(nu + peri), 0.0}, w, h, at);
            if (ok && hasPrev) dl->AddLine(prev, at, IM_COL32(255, 196, 110, 150), 1.2f * ui.s);
            prev = at;
            hasPrev = ok;
        }
        return;
    }
    ImDrawList* dl = ImGui::GetBackgroundDrawList();
    ui.orbits.update(sim);
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i) {
        const Body& b = sim.bodies[static_cast<size_t>(i)];
        if (b.kind != Kind::Planet || !sim.visible(i) || !ui.orbits.tracks[static_cast<size_t>(i)].valid) continue;
        // Lunes de moins de 100 km de rayon, ou au rayon non mesuré (des centaines depuis le fichier complet du JPL) : leur
        // orbite n'est tracée que si on les suit, sinon les traits cachent la planète.
        if (b.parent > 0 && b.naif != eph::kMoon && b.radiusKm < 100 && i != sim.focus) continue;
        const Vec3 parent = b.parent > 0 ? sim.position(b.parent) : Vec3{0, 0, 0};
        const auto& pts = ui.orbits.tracks[static_cast<size_t>(i)].pts;
        // Taille apparente de l'orbite : ni un point, ni un trait qui traverse tout l'écran.
        const double size = std::sqrt(dot(pts[0], pts[0])) / std::max(distBetween(parent, cam.pos), 1e-30) * h;
        if (size < 6 || size > 60.0 * h) continue;
        if (discRadiusPx(sim, cam, i, h) > 14) continue;      // l'astre est vu de près : son orbite ne lui passe pas sur le visage
        ImVec2 prev;
        bool hasPrev = false;
        for (const Vec3& rel : pts) {
            ImVec2 at;
            const bool ok = projectLoose(cam, {parent.x + rel.x, parent.y + rel.y, parent.z + rel.z}, w, h, at);
            if (ok && hasPrev) dl->AddLine(prev, at, i == sim.focus ? IM_COL32(255, 196, 110, 150) : kOrbit, 1.2f * ui.s);
            prev = at;
            hasPrev = ok;
        }
    }
}

bool labelWanted(const Sim& sim, const UiState& ui, const Camera& cam, int i, float w, float h, double px0, double py0, double boostMag);

// L'astre sous la souris : le point le plus proche à moins de 16 pixels (ou sur son disque), ou -1.
int pickBody(const Sim& sim, const UiState& ui, const Camera& cam, float w, float h, ImVec2 mouse) {
    int best = -1;
    double bestD = 1e30;
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i) {
        if (!sim.visible(i)) continue;
        const Body& b = sim.bodies[static_cast<size_t>(i)];
        if (b.kind == Kind::Star && sim.dist < 0.02 && i != sim.focus) continue;      // dans le système solaire, les étoiles ne se cliquent pas
        double x = 0, y = 0;
        if (!cam.project(sim.position(i), w, h, x, y)) continue;
        // audit B1 : une galaxie dont le nom est caché à cette échelle (55 000 de Cosmicflows-4, naines vues de loin) ne se
        // clique pas non plus ; sinon un clic dans le vide faisait voler vers un point invisible.
        if (b.kind == Kind::Galaxy && b.priority >= 9 && i != sim.focus && !labelWanted(sim, ui, cam, i, w, h, x, y, 0.0)) continue;
        const double d = std::hypot(x - mouse.x, y - mouse.y) - std::min(discRadiusPx(sim, cam, i, h), 2000.0);
        if (d < 16.0 * ui.s && d < bestD) {
            bestD = d;
            best = i;
        }
    }
    return best;
}

bool labelWanted(const Sim& sim, const UiState& ui, const Camera& cam, int i, float w, float h, double px0, double py0, double boostMag) {
    const Body& b = sim.bodies[static_cast<size_t>(i)];
    if (i == sim.focus) return discRadiusPx(sim, cam, i, h) <= 14;      // vu de près : la fiche porte déjà son nom
    if (b.kind == Kind::Star && b.priority >= 9 && sim.apparentMag(i, cam.pos) - boostMag > 1.0) return false;      // hôtes de planètes : seulement les plus brillants
    if (b.kind == Kind::Star && (sim.dist < 0.02 || sim.dist > 3000.0 || sim.apparentMag(i, cam.pos) - boostMag > 4.5)) return false;
    if (b.kind == Kind::Planet && sim.dist > 0.05) return false;
    if (b.kind == Kind::Planet && b.parent > 0 && b.naif != eph::kMoon && b.radiusKm < 100 && !ui.details) return false;      // minimaliste : petites lunes nommées au survol
    if (b.kind == Kind::Probe) return sim.dist < 0.3;
    if (b.kind == Kind::Asteroid) return sim.dist < 0.05;
    if (b.kind == Kind::Galaxy && b.priority >= 9) {      // Cosmicflows-4 (55 637) : seulement quand on est tout près
        const Vec3 p = sim.position(i);
        const Vec3 d{p.x - cam.pos.x, p.y - cam.pos.y, p.z - cam.pos.z};
        return std::sqrt(dot(d, d)) < 3.0e6;
    }
    // balayage du zoom (20/11/2026) : à 1,5 Mal, une trentaine de noms de naines apparaissaient d'un coup ; les naines
    // (rang 5) sont nommées au survol, comme les petites lunes, sauf en mode détaillé
    if (b.kind == Kind::Galaxy && (b.priority >= 5 || b.natureText == "galaxie naine") && b.priority < 9 && i != sim.focus && !ui.details) return false;
    if (b.kind == Kind::Galaxy && (sim.dist < 2.0e4 || sim.dist > 3.0e9 || (b.priority > 1 && sim.dist < 1.5e6))) return false;
    if (b.kind == Kind::Planet) {      // un nom par planète seulement quand elle se détache de son astre parent
        double qx = 0, qy = 0;
        const int par = std::max(b.parent, 0);
        const bool parentOn = cam.project(sim.position(par), w, h, qx, qy);
        if (parentOn && std::hypot(px0 - qx, py0 - qy) < 22) return false;
        // audit D2 : une lune derrière le disque de sa planète ne montre pas son nom (« Rhéa » écrit sur Saturne)
        if (parentOn && par > 0) {
            const Vec3 pm = sim.position(i), pp = sim.position(par);
            const Vec3 dm{pm.x - cam.pos.x, pm.y - cam.pos.y, pm.z - cam.pos.z}, dp{pp.x - cam.pos.x, pp.y - cam.pos.y, pp.z - cam.pos.z};
            if (dot(dm, dm) > dot(dp, dp) && std::hypot(px0 - qx, py0 - qy) < discRadiusPx(sim, cam, par, h)) return false;
        }
    }
    return true;
}

// Repère de l'astre suivi : quatre coins, comme un viseur (on voit l'astre au milieu, sans le cacher).
void focusBrackets(ImDrawList* dl, ImVec2 c, float r, float s) {
    const float k = std::max(5.0f * s, r * 0.38f), t = 1.8f * s;
    for (int sx = -1; sx <= 1; sx += 2)
        for (int sy = -1; sy <= 1; sy += 2) {
            const ImVec2 corner{c.x + sx * r, c.y + sy * r};
            dl->AddLine(corner, {corner.x - sx * k, corner.y}, kAccent, t);
            dl->AddLine(corner, {corner.x, corner.y - sy * k}, kAccent, t);
        }
}

// Noms posés sur l'image (jamais l'un sur l'autre) et astre survolé mis en valeur.
void drawLabels(const Sim& sim, const UiState& ui, const Camera& cam, float w, float h, int hovered) {
    ImDrawList* dl = ImGui::GetBackgroundDrawList();
    const int count = static_cast<int>(sim.bodies.size());
    const double boostMag = 2.5 * std::log10(sim.brightnessBoost());
    std::vector<ImVec4> placed;
    // L'astre suivi d'abord, puis le survolé : ils gardent toujours leur nom, les autres s'effacent devant eux.
    std::vector<int> order{sim.focus};
    if (hovered >= 0 && hovered != sim.focus) order.push_back(hovered);
    for (int i = 0; i < count; ++i)
        if (i != sim.focus && i != hovered) order.push_back(i);
    for (const int i : order) {
        if (!sim.visible(i)) continue;
        const Body& b = sim.bodies[static_cast<size_t>(i)];
        double x = 0, y = 0;
        if (!cam.project(sim.position(i), w, h, x, y)) continue;
        const bool isFocus = i == sim.focus, isHover = i == hovered;
        const ImVec2 p{static_cast<float>(x), static_cast<float>(y)};
        const float discR = static_cast<float>(std::min(discRadiusPx(sim, cam, i, h), 3000.0));
        if (isHover && !isFocus) {      // survol : anneau fin et halo doux
            const float r = std::max(11.0f * ui.s, discR + 6.0f * ui.s);
            dl->AddCircleFilled(p, r, theme::alpha(theme::kAccent, 0.10f), 48);
            dl->AddCircle(p, r, theme::alpha(theme::kAccent, 0.85f), 48, 1.4f * ui.s);
        }
        if (!isHover && !labelWanted(sim, ui, cam, i, w, h, x, y, boostMag)) continue;
        const char* name = b.name.c_str();
        const ImVec2 size = ImGui::CalcTextSize(name);
        const ImVec2 at{p.x + 10 * ui.s, p.y - size.y * 0.5f};
        const ImVec4 box{at.x - 14 * ui.s, at.y - 3, at.x + size.x + 6, at.y + size.y + 3};
        if (!isFocus && !isHover) {
            bool overlaps = false;
            for (const ImVec4& r : placed) overlaps |= box.x < r.z && box.z > r.x && box.y < r.w && box.w > r.y;
            if (overlaps) continue;
        }
        placed.push_back(box);
        if (isFocus) focusBrackets(dl, p, std::max(10.0f * ui.s, discR + 7.0f * ui.s), ui.s);
        // Lune sans éclat renseigné : un petit repère marque son emplacement mesuré (ce n'est pas sa lumière).
        if ((b.kind == Kind::Planet && !b.hasPhotometry) || b.kind == Kind::Probe || b.kind == Kind::Asteroid) dl->AddCircle(p, 3 * ui.s, IM_COL32(200, 214, 240, 200), 12, 1.2f * ui.s);
        if (isFocus || isHover) {      // nom de l'astre suivi ou survolé : sur une pastille sombre, en gras
            ImFont* f = gFontBold ? gFontBold : ImGui::GetFont();
            const float fs = ImGui::GetFontSize();
            const ImVec2 ts = f->CalcTextSizeA(fs, FLT_MAX, 0, name);
            const ImVec2 lp{p.x + std::max(14.0f * ui.s, discR * 0.7f + 10.0f * ui.s), p.y - ts.y * 0.5f};
            dl->AddRectFilled({lp.x - 7 * ui.s, lp.y - 2 * ui.s}, {lp.x + ts.x + 7 * ui.s, lp.y + ts.y + 2 * ui.s}, IM_COL32(8, 11, 20, 190), ts.y);
            dl->AddText(f, fs, lp, kAccent, name);
            continue;
        }
        dl->AddText(ImGui::GetFont(), ImGui::GetFontSize(), {at.x + 1, at.y + 1}, IM_COL32(0, 0, 0, 200), name);
        dl->AddText(ImGui::GetFont(), ImGui::GetFontSize(), at, b.kind == Kind::Star ? kInkSoft : kInk, name);
    }
}

std::string natureOf(const Body& b) { return b.natureLabel(); }

void hoverTooltip(const Sim& sim, const Camera& cam, int i) {
    const Body& b = sim.bodies[static_cast<size_t>(i)];
    ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, {12 * ImGui::GetIO().FontGlobalScale * gFontMaxScale, 10 * ImGui::GetIO().FontGlobalScale * gFontMaxScale});
    ImGui::BeginTooltip();
    ImGui::PushFont(gFontBold ? gFontBold : ImGui::GetFont());
    ImGui::TextUnformatted(b.name.c_str());
    ImGui::PopFont();
    ImGui::TextDisabled("%s  ·  à %s d'ici", natureOf(b).c_str(), frDistance(distBetween(sim.position(i), cam.pos)).c_str());
    ImGui::PushFont(gFontSmall ? gFontSmall : ImGui::GetFont());
    ImGui::TextColored(theme::v4(theme::kAccent), "%s", i == sim.focus ? "Clic : s'en approcher" : "Clic : y aller et ouvrir sa fiche");
    ImGui::PopFont();
    ImGui::EndTooltip();
    ImGui::PopStyleVar();
}

// ---------------------------------------------------------------- clavier

void openSearchWith(UiState& ui, const std::string& typed) {
    const size_t len = std::strlen(ui.search);
    if (len + typed.size() < sizeof(ui.search)) std::memcpy(ui.search + len, typed.c_str(), typed.size() + 1);
    ui.focusSearch = true;
    ui.cursorToEnd = true;
    ui.searchSel = 0;
}

void handleKeys(Sim& sim, UiState& ui) {
    ImGuiIO& io = ImGui::GetIO();
    if (ImGui::IsKeyPressed(ImGuiKey_F1, false)) ui.help = !ui.help;
    if (io.WantTextInput) return;      // on écrit dans un champ : les touches lui appartiennent
    if (io.KeyCtrl && ImGui::IsKeyPressed(ImGuiKey_F, false)) {
        ui.focusSearch = true;
        return;
    }
    // Une lettre tapée ouvre la recherche ; un chiffre de 1 à 5 choisit une échelle ; + et - zooment.
    std::string typed;
    for (const ImWchar c : io.InputQueueCharacters) {
        if (io.KeyCtrl || io.KeyAlt) break;
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= 0xC0 && c <= 0xFF && c != 0xD7 && c != 0xF7)) {
            if (c < 0x80) typed += static_cast<char>(c);
            else {
                typed += static_cast<char>(0xC0 | (c >> 6));
                typed += static_cast<char>(0x80 | (c & 0x3F));
            }
        } else if (c >= '1' && c < '1' + kScaleCount) {
            ui.tour = -1;
            sim.flyTo(scaleCenter(sim), kScales[c - '1'].distLy);
        } else if (c == '+' || c == '=') sim.zoom(1.5);
        else if (c == '-' || c == '_') sim.zoom(-1.5);
    }
    if (!typed.empty()) openSearchWith(ui, typed);
    if (ImGui::IsKeyPressed(ImGuiKey_Backspace, false)) {
        ui.tour = -1;
        sim.back();
    }
    if (ImGui::IsKeyPressed(ImGuiKey_PageUp)) sim.stepRate(+1);
    if (ImGui::IsKeyPressed(ImGuiKey_PageDown)) sim.stepRate(-1);
    // Flèches : tourner autour de l'astre suivi (un demi-tour en un peu plus de 3 secondes).
    const double step = 190.0 * io.DeltaTime;
    double dx = 0, dy = 0;
    if (ImGui::IsKeyDown(ImGuiKey_LeftArrow)) dx -= step;
    if (ImGui::IsKeyDown(ImGuiKey_RightArrow)) dx += step;
    if (ImGui::IsKeyDown(ImGuiKey_UpArrow)) dy += step;
    if (ImGui::IsKeyDown(ImGuiKey_DownArrow)) dy -= step;
    if (dx != 0 || dy != 0) {
        sim.touched = true;
        sim.orbit(dx, dy);
    }
}

}  // namespace
