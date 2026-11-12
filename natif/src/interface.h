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

namespace {

const ImU32 kInkSoft = IM_COL32(150, 160, 178, 255), kAccent = IM_COL32(255, 196, 110, 255), kOrbit = IM_COL32(110, 140, 200, 110);
const ImU32 kInk = IM_COL32(200, 214, 240, 255);

// Échelle de l'interface : la police est chargée pour le plus grand écran du PC, puis réduite pour une fenêtre plus petite.
float gFontMaxScale = 1.0f;

void applyStyle() {
    ImGuiStyle& st = ImGui::GetStyle();
    st.WindowRounding = 10;
    st.FrameRounding = 7;
    st.GrabRounding = 7;
    st.PopupRounding = 8;
    st.WindowBorderSize = 1;
    st.PopupBorderSize = 1;
    st.WindowPadding = {14, 12};
    st.FramePadding = {10, 6};
    st.ItemSpacing = {8, 7};
    ImVec4* c = st.Colors;
    c[ImGuiCol_WindowBg] = {0.035f, 0.045f, 0.075f, 0.88f};
    c[ImGuiCol_PopupBg] = {0.05f, 0.065f, 0.11f, 0.98f};
    c[ImGuiCol_Border] = {0.30f, 0.36f, 0.50f, 0.35f};
    c[ImGuiCol_Text] = {0.91f, 0.93f, 0.96f, 1.0f};
    c[ImGuiCol_TextDisabled] = {0.62f, 0.66f, 0.73f, 1.0f};
    c[ImGuiCol_FrameBg] = {0.10f, 0.13f, 0.20f, 0.9f};
    c[ImGuiCol_FrameBgHovered] = {0.16f, 0.20f, 0.30f, 1.0f};
    c[ImGuiCol_FrameBgActive] = {0.20f, 0.25f, 0.36f, 1.0f};
    c[ImGuiCol_Button] = {0.11f, 0.14f, 0.22f, 0.95f};
    c[ImGuiCol_ButtonHovered] = {0.20f, 0.25f, 0.38f, 1.0f};
    c[ImGuiCol_ButtonActive] = {0.80f, 0.58f, 0.25f, 1.0f};
    c[ImGuiCol_Header] = {0.16f, 0.20f, 0.30f, 0.9f};
    c[ImGuiCol_HeaderHovered] = {0.22f, 0.28f, 0.42f, 1.0f};
    c[ImGuiCol_HeaderActive] = {0.80f, 0.58f, 0.25f, 1.0f};
    c[ImGuiCol_Separator] = {0.30f, 0.36f, 0.50f, 0.35f};
    c[ImGuiCol_TitleBg] = {0.05f, 0.065f, 0.11f, 1.0f};
    c[ImGuiCol_TitleBgActive] = {0.09f, 0.12f, 0.19f, 1.0f};
    c[ImGuiCol_PlotHistogram] = {1.0f, 0.77f, 0.43f, 0.9f};
}

// Police de Windows avec les accents et les signes utilisés ; à défaut, la police intégrée (sans accents).
// Elle est chargée à la taille voulue pour la hauteur de l'écran principal (1 à 2 fois la taille de base de 1080 lignes).
void loadFonts(ImFont*& normal, ImFont*& big) {
    ImGuiIO& io = ImGui::GetIO();
    static const ImWchar ranges[] = {0x0020, 0x00FF, 0x2010, 0x2027, 0x2190, 0x2193, 0x2212, 0x2212, 0x2318, 0x2318, 0};
    gFontMaxScale = std::clamp(static_cast<float>(GetSystemMetrics(SM_CYSCREEN)) / 1080.0f, 1.0f, 2.5f);
    const char* path = "C:\\Windows\\Fonts\\segoeui.ttf";
    if (std::ifstream(path).good()) {
        normal = io.Fonts->AddFontFromFileTTF(path, 18.0f * gFontMaxScale, nullptr, ranges);
        big = io.Fonts->AddFontFromFileTTF(path, 26.0f * gFontMaxScale, nullptr, ranges);
    }
    if (!normal) {
        gFontMaxScale = 1.0f;
        normal = big = io.Fonts->AddFontDefault();
    }
}

void row(const char* label, const std::string& value, const char* status, float s) {
    ImGui::TextDisabled("%s", label);
    ImGui::SameLine(176 * s);
    ImGui::TextUnformatted(value.c_str());
    if (status[0]) {
        ImGui::SameLine();
        ImGui::TextDisabled("(%s)", status);
    }
}

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
            if (std::fabs(sim.years - t.atYears) < b.periodYears / 240.0) continue;      // encore bon à l'écran
            t.atYears = sim.years;
            t.pts.resize(kPoints + 1);
            t.valid = true;
            for (int k = 0; k <= kPoints && t.valid; ++k) {
                const double at = sim.years + (static_cast<double>(k) / kPoints - 0.5) * b.periodYears;
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
    ImVec2 goToAnchor{0, 0};        // le menu « Aller à » s'ouvre sous son bouton          // contrôle : le menu « Aller à » reste ouvert pour la capture
    int cardClosedFor = -1;         // fiche fermée pour cet astre
    int tour = -1;                  // étape de la visite guidée (-1 : pas de visite)
    double tourClock = 0;
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

// Au premier dessin : mot d'accueil, et réglages de contrôle (variable UNIVERS_ECRAN, pour les captures sans fenêtre).
void firstFrame(Sim& sim, UiState& ui) {
    if (ui.started) return;
    ui.started = true;
    ui.welcome = !sim.touched;
    const char* env = std::getenv("UNIVERS_ECRAN");
    const std::string e = env ? env : "";
    if (e == "accueil") ui.welcome = true;
    if (e == "aide") ui.help = true;
    if (e == "menu") ui.keepGoTo = true;
    if (e.rfind("recherche:", 0) == 0) std::snprintf(ui.search, sizeof(ui.search), "%s", e.substr(10).c_str());
    if (e.rfind("visite:", 0) == 0) {
        startTour(sim, ui, std::atoi(e.substr(7).c_str()));
        sim.stepFlight(Sim::kFlySeconds);      // capture : l'étape est atteinte
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
    if (!sim.ephemValid) return;
    ImDrawList* dl = ImGui::GetBackgroundDrawList();
    ui.orbits.update(sim);
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i) {
        const Body& b = sim.bodies[static_cast<size_t>(i)];
        if (b.kind != Kind::Planet || !sim.visible(i) || !ui.orbits.tracks[static_cast<size_t>(i)].valid) continue;
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
        const double d = std::hypot(x - mouse.x, y - mouse.y) - std::min(discRadiusPx(sim, cam, i, h), 2000.0);
        if (d < 16.0 * ui.s && d < bestD) {
            bestD = d;
            best = i;
        }
    }
    return best;
}

bool labelWanted(const Sim& sim, const Camera& cam, int i, float w, float h, double px0, double py0, double boostMag) {
    const Body& b = sim.bodies[static_cast<size_t>(i)];
    if (i == sim.focus) return discRadiusPx(sim, cam, i, h) <= 14;      // vu de près : la fiche porte déjà son nom
    if (b.kind == Kind::Star && (sim.dist < 0.02 || sim.dist > 3000.0 || sim.apparentMag(i, cam.pos) - boostMag > 4.5)) return false;
    if (b.kind == Kind::Planet && sim.dist > 0.05) return false;
    if (b.kind == Kind::Galaxy && (sim.dist < 2.0e4 || sim.dist > 3.0e9 || (b.priority > 1 && sim.dist < 1.5e6))) return false;
    if (b.kind == Kind::Planet) {      // un nom par planète seulement quand elle se détache de son astre parent
        double qx = 0, qy = 0;
        const bool parentOn = cam.project(sim.position(std::max(b.parent, 0)), w, h, qx, qy);
        if (parentOn && std::hypot(px0 - qx, py0 - qy) < 22) return false;
    }
    return true;
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
        if (isHover) dl->AddCircle(p, std::max(11.0f * ui.s, static_cast<float>(std::min(discRadiusPx(sim, cam, i, h), 3000.0)) + 6.0f * ui.s), kAccent, 48, 1.5f * ui.s);
        if (!isHover && !labelWanted(sim, cam, i, w, h, x, y, boostMag)) continue;
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
        if (isFocus) dl->AddCircle(p, 9 * ui.s, kAccent, 32, 1.5f * ui.s);
        // Lune sans éclat renseigné : un petit repère marque son emplacement mesuré (ce n'est pas sa lumière).
        if (b.kind == Kind::Planet && !b.hasPhotometry) dl->AddCircle(p, 3 * ui.s, IM_COL32(200, 214, 240, 200), 12, 1.2f * ui.s);
        dl->AddText(ImGui::GetFont(), ImGui::GetFontSize(), {at.x + 1, at.y + 1}, IM_COL32(0, 0, 0, 200), name);
        dl->AddText(ImGui::GetFont(), ImGui::GetFontSize(), at, isFocus || isHover ? kAccent : (b.kind == Kind::Star ? kInkSoft : kInk), name);
    }
}

std::string natureOf(const Body& b) { return b.natureLabel(); }

void hoverTooltip(const Sim& sim, const Camera& cam, int i) {
    const Body& b = sim.bodies[static_cast<size_t>(i)];
    ImGui::BeginTooltip();
    ImGui::TextUnformatted(b.name.c_str());
    ImGui::TextDisabled("%s, à %s d'ici", natureOf(b).c_str(), frDistance(distBetween(sim.position(i), cam.pos)).c_str());
    ImGui::TextDisabled(i == sim.focus ? "Clic : s'en approcher" : "Clic : y aller");
    ImGui::EndTooltip();
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
            sim.flyTo(0, kScales[c - '1'].distLy);
        } else if (c == '+' || c == '=') sim.zoom(1.5);
        else if (c == '-' || c == '_') sim.zoom(-1.5);
    }
    if (!typed.empty()) openSearchWith(ui, typed);
    if (ImGui::IsKeyPressed(ImGuiKey_Backspace, false)) {
        ui.tour = -1;
        sim.back();
    }
    if (ImGui::IsKeyPressed(ImGuiKey_PageUp)) sim.rate = std::min(sim.rate + 1, kRateCount - 1);
    if (ImGui::IsKeyPressed(ImGuiKey_PageDown)) sim.rate = std::max(sim.rate - 1, 0);
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

// ---------------------------------------------------------------- recherche et « Aller à »

int kindRank(const Body& b) {
    if (b.kind == Kind::Sun) return 0;
    if (b.kind == Kind::Planet) return b.parent == 0 ? 0 : 1;
    return b.kind == Kind::Star ? 2 : 3;
}

std::vector<int> searchResults(const Sim& sim, const char* text) {
    const std::string q = ui_outils::fold(text);
    std::vector<std::pair<int, int>> scored;      // (rang, numéro)
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i) {
        if (!sim.visible(i)) continue;
        const Body& b = sim.bodies[static_cast<size_t>(i)];
        const int r = ui_outils::matchRank(b.name, q);
        if (r >= 0) scored.push_back({r * 10 + kindRank(b), i});
    }
    std::stable_sort(scored.begin(), scored.end(), [](auto& a, auto& b) { return a.first < b.first; });
    std::vector<int> out;
    for (size_t k = 0; k < scored.size() && k < 10; ++k) out.push_back(scored[k].second);
    return out;
}

int moveCursorToEnd(ImGuiInputTextCallbackData* d) {
    auto* ui = static_cast<UiState*>(d->UserData);
    if (ui->cursorToEnd) {
        d->CursorPos = d->SelectionStart = d->SelectionEnd = d->BufTextLen;
        ui->cursorToEnd = false;
    }
    return 0;
}

void goToBody(Sim& sim, UiState& ui, int i, double distLy = 0) {
    ui.tour = -1;
    ui.welcome = false;
    ui.search[0] = 0;
    sim.flyTo(i, distLy);
}

// Une ligne de résultat : le nom, puis en gris sa nature et sa distance au Soleil.
bool resultRow(const Sim& sim, const UiState& ui, int i, bool selected) {
    const Body& b = sim.bodies[static_cast<size_t>(i)];
    ImGui::PushID(i);
    const float x0 = ImGui::GetCursorPosX();
    const bool hit = ImGui::Selectable(b.name.c_str(), selected, ImGuiSelectableFlags_AllowOverlap, {px(ui, 440), 0});
    ImGui::SameLine(x0 + ImGui::CalcTextSize(b.name.c_str()).x + px(ui, 12));
    const std::string where = b.kind == Kind::Sun ? std::string("notre étoile") : natureOf(b) + ", " + frDistance(std::sqrt(dot(sim.position(i), sim.position(i))));
    ImGui::TextDisabled("%s", where.c_str());
    ImGui::PopID();
    return hit;
}

void drawSearchResults(Sim& sim, UiState& ui, bool inputActive, bool entered) {
    if (!ui.search[0]) return;
    const std::vector<int> found = searchResults(sim, ui.search);
    const int n = static_cast<int>(found.size());
    if (inputActive && n) {
        if (ImGui::IsKeyPressed(ImGuiKey_DownArrow)) ui.searchSel = (ui.searchSel + 1) % n;
        if (ImGui::IsKeyPressed(ImGuiKey_UpArrow)) ui.searchSel = (ui.searchSel + n - 1) % n;
    }
    ui.searchSel = std::clamp(ui.searchSel, 0, std::max(n - 1, 0));
    if (entered && n) {
        goToBody(sim, ui, found[static_cast<size_t>(ui.searchSel)]);
        return;
    }
    for (int k = 0; k < n; ++k)
        if (resultRow(sim, ui, found[static_cast<size_t>(k)], k == ui.searchSel)) {
            goToBody(sim, ui, found[static_cast<size_t>(k)]);
            return;
        }
    if (!n) ImGui::TextDisabled("Aucun astre nommé ne correspond.");
    else ImGui::TextDisabled("Entrée : y aller   •   flèches : choisir   •   Échap : fermer");
}

void goToMenuBodies(Sim& sim, UiState& ui) {
    const int count = static_cast<int>(sim.bodies.size());
    if (ImGui::BeginMenu("Système solaire")) {
        if (ImGui::MenuItem("Soleil")) goToBody(sim, ui, 0);
        for (int i = 0; i < count; ++i) {
            const Body& b = sim.bodies[static_cast<size_t>(i)];
            if (b.kind != Kind::Planet || b.parent != 0 || !sim.visible(i)) continue;
            bool hasMoons = false;
            for (const Body& m : sim.bodies) hasMoons |= m.kind == Kind::Planet && m.parent == i;
            if (!hasMoons) {
                if (ImGui::MenuItem(b.name.c_str())) goToBody(sim, ui, i);
                continue;
            }
            if (!ImGui::BeginMenu(b.name.c_str())) continue;
            if (ImGui::MenuItem(b.name.c_str())) goToBody(sim, ui, i);
            ImGui::Separator();
            for (int j = 0; j < count; ++j)
                if (sim.bodies[static_cast<size_t>(j)].parent == i && sim.visible(j) && ImGui::MenuItem(sim.bodies[static_cast<size_t>(j)].name.c_str()))
                    goToBody(sim, ui, j);
            ImGui::EndMenu();
        }
        ImGui::EndMenu();
    }
    // Étoiles et galaxies nommées, de la plus proche à la plus lointaine, avec leur distance au Soleil.
    for (const Kind kind : {Kind::Star, Kind::Galaxy}) {
        if (!ImGui::BeginMenu(kind == Kind::Star ? "Étoiles nommées" : "Galaxies nommées")) continue;
        std::vector<std::pair<double, int>> list;
        for (int i = 0; i < count; ++i)
            if (sim.bodies[static_cast<size_t>(i)].kind == kind && (kind == Kind::Star || sim.bodies[static_cast<size_t>(i)].priority <= 4))
                list.push_back({std::sqrt(dot(sim.position(i), sim.position(i))), i});
        std::sort(list.begin(), list.end());
        for (const auto& [d, i] : list)
            if (ImGui::MenuItem(sim.bodies[static_cast<size_t>(i)].name.c_str(), frDistance(d).c_str())) goToBody(sim, ui, i);
        ImGui::EndMenu();
    }
}

void drawGoToMenu(Sim& sim, UiState& ui) {
    if (ui.openGoTo || ui.keepGoTo) {
        ImGui::OpenPopup("aller");
        ui.openGoTo = false;
    }
    ImGui::SetNextWindowPos(ui.goToAnchor, ImGuiCond_Appearing);
    if (!ImGui::BeginPopup("aller")) return;
    ImGui::TextDisabled("Échelles (vues depuis le Soleil)");
    for (int k = 0; k < kScaleCount; ++k) {
        const char key[2] = {static_cast<char>('1' + k), 0};
        if (ImGui::MenuItem(kScales[k].label, key)) {
            ui.tour = -1;
            ui.welcome = false;
            sim.flyTo(0, kScales[k].distLy);
        }
    }
    ImGui::Separator();
    goToMenuBodies(sim, ui);
    ImGui::Separator();
    if (ImGui::MenuItem("Visite guidée")) startTour(sim, ui, 0);
    if (ImGui::MenuItem("Revenir à la vue précédente", "Retour arrière", false, !sim.history.empty())) {
        ui.tour = -1;
        sim.back();
    }
    ImGui::EndPopup();
}

// En haut à gauche : recherche, « Aller à », aide.
void drawTopLeft(Sim& sim, UiState& ui, ImGuiWindowFlags fixed) {
    ImGui::SetNextWindowPos({px(ui, 16), px(ui, 16)});
    ImGui::Begin("chercher", nullptr, fixed);
    ImGui::SetNextItemWidth(px(ui, 300));
    if (ui.focusSearch) {
        ImGui::SetKeyboardFocusHere();
        ui.focusSearch = false;
    }
    const bool entered = ImGui::InputTextWithHint("##q", "Chercher : tape un nom (ex. Saturne)", ui.search, sizeof(ui.search),
                                                  ImGuiInputTextFlags_EnterReturnsTrue | ImGuiInputTextFlags_EscapeClearsAll | ImGuiInputTextFlags_CallbackAlways, moveCursorToEnd, &ui);
    const bool active = ImGui::IsItemActive();
    if (ImGui::IsItemEdited()) ui.searchSel = 0;
    if (!active && ImGui::IsKeyPressed(ImGuiKey_Escape, false)) ui.search[0] = 0;
    ImGui::SameLine();
    if (ImGui::Button("Aller à…")) ui.openGoTo = true;
    ui.goToAnchor = {ImGui::GetItemRectMin().x, ImGui::GetItemRectMax().y + px(ui, 6)};
    ImGui::SameLine();
    if (ImGui::Button(" ? ")) ui.help = !ui.help;
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Toutes les commandes (F1)");
    drawGoToMenu(sim, ui);
    drawSearchResults(sim, ui, active, entered);
    ImGui::End();
}

// ---------------------------------------------------------------- temps

// Bouton dessiné : lecture (triangle) ou pause (deux barres).
bool playButton(const UiState& ui, bool paused) {
    const float sz = ImGui::GetFrameHeight();
    const ImVec2 p = ImGui::GetCursorScreenPos();
    const bool hit = ImGui::Button("##play", {sz * 1.4f, sz});
    const bool hov = ImGui::IsItemHovered();
    ImDrawList* dl = ImGui::GetWindowDrawList();
    const ImVec2 c{p.x + sz * 0.7f, p.y + sz * 0.5f};
    const float r = sz * 0.26f;
    const ImU32 col = hov ? kAccent : IM_COL32(235, 238, 245, 255);
    if (paused) dl->AddTriangleFilled({c.x - r * 0.8f, c.y - r}, {c.x - r * 0.8f, c.y + r}, {c.x + r, c.y}, col);
    else {
        dl->AddRectFilled({c.x - r * 0.85f, c.y - r}, {c.x - r * 0.25f, c.y + r}, col, 1.5f * ui.s);
        dl->AddRectFilled({c.x + r * 0.25f, c.y - r}, {c.x + r * 0.85f, c.y + r}, col, 1.5f * ui.s);
    }
    if (hov) ImGui::SetTooltip(paused ? "Faire avancer le temps (Espace)" : "Arrêter le temps (Espace)");
    return hit;
}

// Écart à aujourd'hui, en mots : « aujourd'hui », « dans 3 jours », « il y a 250 ans ».
std::string relativeToToday(double years) {
    const double d = years - kStartYears, a = std::fabs(d);
    std::string span;
    if (a < 1.0 / 365.25) return "aujourd'hui";
    if (a < 1.0 / 12.0) span = frInt(a * 365.25) + (a * 365.25 >= 1.5 ? " jours" : " jour");
    else if (a < 1.0) span = frInt(a * 12.0) + (a * 12.0 >= 1.5 ? " mois" : " mois");
    else if (a < 1.0e6) span = frInt(a) + (a >= 1.5 ? " ans" : " an");
    else span = frNum(a / 1.0e6) + " millions d'années";
    return d > 0 ? "dans " + span : "il y a " + span;
}

void dateJumpPopup(Sim& sim, UiState& ui) {
    if (!ImGui::BeginPopup("date")) return;
    ImGui::TextUnformatted("Aller à une date");
    ImGui::TextDisabled("Exemples : 1969   •   21/07/1969   •   -3000   •   250000");
    if (ImGui::IsWindowAppearing()) ImGui::SetKeyboardFocusHere();
    ImGui::SetNextItemWidth(px(ui, 220));
    bool go = ImGui::InputText("##d", ui.dateText, sizeof(ui.dateText), ImGuiInputTextFlags_EnterReturnsTrue);
    ImGui::SameLine();
    go |= ImGui::Button("Y aller");
    if (go) {
        double y = 0;
        ui.dateError = !ui_outils::parseDate(ui.dateText, y);
        if (!ui.dateError) {
            sim.years = std::clamp(y, kStartYears - kLinearLimitYears, kStartYears + kLinearLimitYears);
            ImGui::CloseCurrentPopup();
        }
    }
    if (ui.dateError) ImGui::TextDisabled("Date non comprise. Écris une année, ou jour/mois/année.");
    ImGui::TextDisabled("Limite : 3 millions d'années avant ou après aujourd'hui.");
    ImGui::EndPopup();
}

void drawTimeBar(Sim& sim, UiState& ui, float w, ImGuiWindowFlags fixed) {
    ImGui::SetNextWindowPos({w * 0.5f, px(ui, 16)}, 0, {0.5f, 0});
    ImGui::Begin("temps", nullptr, fixed);
    ImGui::PushFont(ui.big);
    const std::string date = frDate(sim.years, kRates[sim.rate].yearsPerSecond < 0.02);
    const float rowW = px(ui, 560);
    ImGui::SetCursorPosX(std::max(px(ui, 14), (rowW - ImGui::CalcTextSize(date.c_str()).x) * 0.5f + px(ui, 14)));
    ImGui::TextUnformatted(date.c_str());
    ImGui::PopFont();
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Clic : aller à une date");
    if (ImGui::IsItemClicked()) ImGui::OpenPopup("date");
    const std::string rel = relativeToToday(sim.years) + (sim.paused ? "   •   temps arrêté" : sim.backward ? "   •   le temps recule" : "");
    ImGui::SetCursorPosX(std::max(px(ui, 14), (rowW - ImGui::CalcTextSize(rel.c_str()).x) * 0.5f + px(ui, 14)));
    ImGui::TextDisabled("%s", rel.c_str());

    if (playButton(ui, sim.paused)) sim.paused = !sim.paused;
    ImGui::SameLine();
    if (ImGui::Button(sim.backward ? "← Recule" : "Avance →")) sim.backward = !sim.backward;
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Changer le sens du temps");
    ImGui::SameLine();
    ImGui::BeginDisabled(sim.rate == 0);
    if (ImGui::Button(" − ")) sim.rate = std::max(sim.rate - 1, 0);
    ImGui::EndDisabled();
    if (ImGui::IsItemHovered(ImGuiHoveredFlags_AllowWhenDisabled)) ImGui::SetTooltip("Plus lent (Page suivante)");
    ImGui::SameLine();
    ImGui::SetNextItemWidth(px(ui, 200));
    if (ImGui::BeginCombo("##vitesse", kRates[sim.rate].label)) {
        for (int i = 0; i < kRateCount; ++i)
            if (ImGui::Selectable(kRates[i].label, i == sim.rate)) sim.rate = i;
        ImGui::EndCombo();
    }
    ImGui::SameLine();
    ImGui::BeginDisabled(sim.rate == kRateCount - 1);
    if (ImGui::Button(" + ")) sim.rate = std::min(sim.rate + 1, kRateCount - 1);
    ImGui::EndDisabled();
    if (ImGui::IsItemHovered(ImGuiHoveredFlags_AllowWhenDisabled)) ImGui::SetTooltip("Plus rapide (Page précédente)");
    ImGui::SameLine();
    if (ImGui::Button("Maintenant")) {
        sim.years = kStartYears;
        sim.backward = false;
    }
    ImGui::SameLine();
    if (ImGui::Button("Date…")) ImGui::OpenPopup("date");
    dateJumpPopup(sim, ui);
    ImGui::PushTextWrapPos(ImGui::GetCursorPosX() + rowW);      // les remarques passent à la ligne : la barre garde sa largeur
    if (!sim.spk) ImGui::TextDisabled("Planètes absentes : le fichier d'éphémérides de la NASA (de440.bsp) manque à côté du programme.");
    else if (!sim.ephemValid && !sim.outer) ImGui::TextDisabled("Hors de 1550-2650 (plage des éphémérides de la NASA) : calcul des planètes en préparation.");
    else if (!sim.ephemValid)
        ImGui::TextDisabled("Hors de 1550-2650 : planètes calculées ici (gravité mutuelle partie des éphémérides de la NASA) ; lunes et orbites non montrées.");
    if (std::fabs(sim.years - kStartYears) >= kLinearLimitYears * 0.999)
        ImGui::TextDisabled("Limite : au-delà de 3 millions d'années, les étoiles ne vont plus en ligne droite (à venir).");
    ImGui::PopTextWrapPos();
    ImGui::End();
}

// ---------------------------------------------------------------- fiche de l'astre suivi

void cardRows(const Sim& sim, const UiState& ui, const Camera& cam, int f) {
    const Body& fb = sim.bodies[static_cast<size_t>(f)];
    const Vec3 p = sim.position(f);
    const double dSun = std::sqrt(dot(p, p));
    const bool today = std::fabs(sim.years - kStartYears) < 1.0;
    const float s = ui.s;
    // Source de la position : éphéméride de la NASA dans sa plage, calcul ici au-delà.
    const bool computed = static_cast<size_t>(f) < sim.planetComputed.size() && sim.planetComputed[static_cast<size_t>(f)];
    const char* src = computed ? "calculé" : "éphémérides NASA";
    row("Nature", natureOf(fb), "", s);
    if (fb.kind == Kind::Planet) {
        row("Distance au Soleil", frDistance(dSun), src, s);
        for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
            if (sim.bodies[static_cast<size_t>(i)].naif == eph::kEarth && i != f) row("Distance à la Terre", frDistance(distBetween(p, sim.position(i))), src, s);
        if (fb.parent > 0)
            row(("Distance à " + sim.bodies[static_cast<size_t>(fb.parent)].name).c_str(), frDistance(distBetween(p, sim.position(fb.parent))), src, s);
        const double days = fb.periodYears * 365.25;
        row("Durée d'un tour", fb.periodYears >= 1 ? frNum(fb.periodYears) + " ans" : days >= 2 ? frNum(days) + " jours" : frNum(days * 24.0) + " heures",
            fb.parent > 0 && fb.naif != eph::kMoon ? "calculé d'après les éphémérides" : "mesuré", s);
        row("Rayon", (fb.radiusKm >= 100 ? frInt(fb.radiusKm) : frNum(fb.radiusKm)) + " km", "mesuré", s);
        if (!fb.hasPhotometry) ImGui::TextDisabled("Son éclat et sa surface ne sont pas renseignés ici : un repère marque sa place.");
    } else if (fb.kind == Kind::Star) {
        // Aujourd'hui la distance est une mesure ; à une autre date, c'est la mesure prolongée en ligne droite.
        row("Distance au Soleil", frDistance(dSun), today ? "mesuré" : "calculé : mouvement mesuré, prolongé en ligne droite", s);
        row("Éclat vu de la Terre", "magnitude " + frNum(sim.apparentMag(f, {0, 0, 0})), "calculé", s);
        row("Vitesse", frNum(sim.speedKms(f)) + " km/s par rapport au Soleil", "mesuré", s);
    } else if (fb.kind == Kind::Galaxy) {
        row("Distance au Soleil", frDistance(dSun), "mesuré", s);
        ImGui::TextDisabled("Sa forme et sa photo ne sont pas encore dessinées ici.");
    } else {
        row("Rayon", frInt(fb.radiusKm) + " km", "mesuré", s);
    }
    if (fb.kind == Kind::Sun || fb.kind == Kind::Star)
        row("Température", frInt(4600.0 * (1.0 / (0.92 * fb.bv + 1.7) + 1.0 / (0.92 * fb.bv + 0.62))) + " K en surface", "calculé d'après la couleur", s);
    if (fb.kind != Kind::Galaxy && (fb.kind != Kind::Planet || fb.hasPhotometry)) row("Vue d'ici", "magnitude " + frNum(sim.apparentMag(f, cam.pos)), "calculé", s);
    ImGui::Separator();
    if (fb.kind == Kind::Planet && computed) ImGui::TextDisabled("Position : calculée ici (gravité mutuelle, partie des éphémérides JPL DE440 de la NASA).");
    else if (fb.kind == Kind::Planet) ImGui::TextDisabled("Position : éphémérides JPL DE440 de la NASA, lues telles quelles.");
    else if (fb.kind == Kind::Galaxy) ImGui::TextDisabled("Sources : Karachentsev et al. 2013 ; McConnachie 2012.");
    else ImGui::TextDisabled("Sources : catalogues Hipparcos (HYG) et Gaia DR3.");
}

void drawCard(Sim& sim, UiState& ui, const Camera& cam, float w, ImGuiWindowFlags fixed) {
    const int f = sim.focus;
    if (ui.cardClosedFor == f) return;
    ui.cardClosedFor = -1;
    ImGui::SetNextWindowPos({w - px(ui, 16), px(ui, 150)}, 0, {1, 0});      // sous la barre du temps : les deux ne se recouvrent jamais
    ImGui::Begin("fiche", nullptr, fixed);
    ImGui::PushFont(ui.big);
    ImGui::TextUnformatted(sim.bodies[static_cast<size_t>(f)].name.c_str());
    ImGui::PopFont();
    // Bouton de fermeture juste après le nom (une position calée sur le bord droit ferait grandir la fiche sans fin).
    ImGui::SameLine(0, px(ui, 24));
    if (ImGui::SmallButton(" × ")) ui.cardClosedFor = f;
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Fermer la fiche");
    ImGui::Separator();
    cardRows(sim, ui, cam, f);
    const bool isFar = sim.dist > 1.5 * sim.arriveDist(f, 1e300) && !sim.flying;
    if (isFar && ImGui::Button("S'en approcher")) goToBody(sim, ui, f);
    if (isFar) ImGui::SameLine();
    if (!sim.history.empty() && ImGui::Button("← Retour")) {
        ui.tour = -1;
        sim.back();
    }
    if (!sim.history.empty()) ImGui::SameLine();
    if (f != 0 && ImGui::Button("Revenir au Soleil")) goToBody(sim, ui, 0, 45.0 * kAuInLy);
    ImGui::End();
}

// ---------------------------------------------------------------- bas de l'écran

void whatYouSee(const Sim& sim) {
    const double boost = sim.brightnessBoost();
    if (boost > 1.5 && sim.dist < 1.0e5) ImGui::TextDisabled("Éclat des étoiles multiplié par %s pour qu'elles restent visibles de si loin.", frNum(boost, 2).c_str());
    if (sim.asteroidCount && sim.asteroidGain(sim.asteroidEpochJd) > 0.01)
        ImGui::TextDisabled("Les petits points sont %s astéroïdes, chacun sur son orbite mesurée (JPL), grossis pour être visibles.", frInt(static_cast<double>(sim.asteroidCount)).c_str());
    if (sim.galaxyGain() > 0.005) {
        ImGui::TextDisabled("Chaque point lointain est une galaxie ou un quasar, placé d'après son décalage vers le rouge mesuré");
        ImGui::TextDisabled("(relevés 2MRS, 6dF, 2dF, SDSS, DESI). Son éclat n'est pas mesuré ici : le point a une taille fixe,");
        ImGui::TextDisabled("qui s'efface avec la distance pour garder l'image lisible (réglage d'affichage, pas une mesure).");
        ImGui::TextDisabled("La Voie lactée elle-même n'est pas encore dessinée : seules ses étoiles mesurées près du Soleil le sont.");
    }
}

void drawStatus(const Sim& sim, const UiState& ui, float h, ImGuiWindowFlags fixed) {
    ImGui::SetNextWindowPos({px(ui, 16), h - px(ui, 16)}, 0, {0, 1});
    ImGui::Begin("aide", nullptr, fixed);
    const Body& fb = sim.bodies[static_cast<size_t>(sim.focus)];
    const std::string where = sim.flying ? "En route vers « " + fb.name + " »…" : "Tu regardes « " + fb.name + " » depuis " + frDistance(sim.dist) + ".";
    ImGui::TextUnformatted(where.c_str());
    whatYouSee(sim);
    ImGui::TextDisabled("Clic sur un astre : y aller   •   Molette : zoomer   •   Glisser : tourner   •   Tape un nom : chercher   •   F1 : aide");
    ImGui::End();
}

// En bas à droite, quand on regarde l'univers lointain : les réglages de l'expansion, recalculés en direct.
void drawCosmology(Sim& sim, const UiState& ui, float w, float h, ImGuiWindowFlags fixed) {
    if (sim.dist <= 2.0e6) return;
    cosmo::Params& c = sim.cosmology;
    float h0 = static_cast<float>(c.h0), om = static_cast<float>(c.om), ode = static_cast<float>(c.ode), w0 = static_cast<float>(c.w0), wa = static_cast<float>(c.wa);
    ImGui::SetNextWindowPos({w - px(ui, 16), h - px(ui, 16)}, 0, {1, 1});
    ImGui::Begin("cosmologie", nullptr, fixed);
    ImGui::TextUnformatted("L'univers en expansion");
    ImGui::Separator();
    ImGui::PushItemWidth(px(ui, 240));
    bool changed = false;
    changed |= ImGui::SliderFloat("Vitesse d'expansion (km/s par Mpc)", &h0, 60.0f, 80.0f, "%.1f");
    changed |= ImGui::SliderFloat("Part de matière", &om, 0.05f, 0.60f, "%.3f");
    changed |= ImGui::SliderFloat("Part d'énergie noire", &ode, 0.30f, 0.95f, "%.3f");
    changed |= ImGui::SliderFloat("Énergie noire : w0", &w0, -1.6f, -0.4f, "%.2f");
    changed |= ImGui::SliderFloat("Énergie noire : wa", &wa, -2.0f, 1.0f, "%.2f");
    ImGui::PopItemWidth();
    if (ImGui::Button("Valeurs mesurées (Planck 2018)")) {
        c = cosmo::Params{};
        sim.cosmologyDirty = true;
    } else if (changed) {
        c.h0 = h0; c.om = om; c.ode = ode; c.w0 = w0; c.wa = wa;
        sim.cosmologyDirty = true;
    }
    const double ok = c.omegaK();
    ImGui::TextDisabled("Âge de l'univers : %s milliards d'années (calculé).", frNum(cosmo::ageGyr(c), 4).c_str());
    ImGui::TextDisabled("Forme de l'espace : %s (calculé).", std::fabs(ok) < 0.005 ? "plat" : ok > 0 ? "ouvert (courbure négative)" : "fermé (courbure positive)");
    ImGui::TextDisabled("Bouge un curseur : toutes les galaxies se replacent aussitôt.");
    ImGui::End();
}

// ---------------------------------------------------------------- accueil, visite, aide

void drawWelcome(Sim& sim, UiState& ui, float w, float h, ImGuiWindowFlags fixed) {
    if (!ui.welcome) return;
    ImGui::SetNextWindowPos({w * 0.5f, h - px(ui, 120)}, 0, {0.5f, 1});
    ImGui::Begin("accueil", nullptr, fixed);
    ImGui::PushFont(ui.big);
    ImGui::TextUnformatted("Bienvenue dans Univers");
    ImGui::PopFont();
    ImGui::TextUnformatted("Tout ce que tu vois est placé d'après des mesures réelles : planètes, étoiles, galaxies.");
    ImGui::TextDisabled("Clique sur un astre pour y aller. Molette pour zoomer, glisser pour tourner, tape un nom pour chercher.");
    ImGui::Spacing();
    if (ImGui::Button("  Visite guidée (une minute et demie)  ")) startTour(sim, ui, 0);
    ImGui::SameLine();
    if (ImGui::Button("  Explorer seul  ")) {
        ui.welcome = false;
        sim.touched = true;
    }
    ImGui::End();
}

std::string tourCaption(const Sim& sim, int step) {
    switch (step) {
        case 0: return "La Terre, éclairée par le Soleil à la date affichée.";
        case 1: return "La Lune, à la place donnée par les éphémérides de la NASA.";
        case 2:
            if (!sim.ephemValid) return "Le système solaire : planètes placées par le calcul de gravité mutuelle (hors de la plage de la NASA).";
            return "Le système solaire : orbites tirées des éphémérides de la NASA" +
                   (sim.asteroidCount ? ", et " + frInt(static_cast<double>(sim.asteroidCount)) + " astéroïdes sur leurs orbites mesurées." : std::string("."));
        case 3: return "Jupiter, la plus grande planète, et ses lunes.";
        case 4: return "Saturne et ses anneaux.";
        case 5: return "Les étoiles voisines du Soleil, à leur distance mesurée (Hipparcos, Gaia).";
        case 6: return frInt(static_cast<double>(sim.stars->n)) + " étoiles mesurées autour du Soleil (Hipparcos, Gaia DR3).";
        case 7: return "Andromède, la grande galaxie voisine, à sa distance mesurée.";
        default: return "Des millions de galaxies et de quasars, placés d'après leur décalage vers le rouge mesuré.";
    }
}

void drawTour(Sim& sim, UiState& ui, float w, float h, ImGuiWindowFlags fixed) {
    if (ui.tour < 0) return;
    ImGuiIO& io = ImGui::GetIO();
    // La main reprend la visite : un clic, la molette ou un glisser sur l'image l'arrête.
    if (!io.WantCaptureMouse && (io.MouseWheel != 0 || ImGui::IsMouseClicked(ImGuiMouseButton_Left) || ImGui::IsMouseClicked(ImGuiMouseButton_Right))) {
        ui.tour = -1;
        return;
    }
    ui.tourClock += io.DeltaTime;
    if (!sim.flying) sim.yaw += 0.05 * io.DeltaTime;      // lent tour autour de l'étape
    const double total = Sim::kFlySeconds + kTourHoldSeconds;
    if (ui.tourClock >= total) {
        startTour(sim, ui, ui.tour + 1);
        if (ui.tour < 0) return;
    }
    ImGui::SetNextWindowPos({w * 0.5f, h - px(ui, 120)}, 0, {0.5f, 1});
    ImGui::Begin("visite", nullptr, fixed);
    ImGui::TextDisabled("Visite guidée   •   étape %d sur %d", ui.tour + 1, kTourCount);
    ImGui::PushFont(ui.big);
    ImGui::TextUnformatted(sim.bodies[static_cast<size_t>(sim.focus)].name.c_str());
    ImGui::PopFont();
    ImGui::TextUnformatted(tourCaption(sim, ui.tour).c_str());
    ImGui::ProgressBar(static_cast<float>(ui.tourClock / total), {px(ui, 520), px(ui, 4)}, "");
    if (ImGui::Button("← Précédente") && ui.tour > 0) startTour(sim, ui, ui.tour - 1);
    ImGui::SameLine();
    if (ImGui::Button("Suivante →")) startTour(sim, ui, ui.tour + 1);
    ImGui::SameLine();
    if (ImGui::Button("Arrêter la visite")) ui.tour = -1;
    ImGui::End();
}

void helpLine(const UiState& ui, const char* key, const char* what) {
    ImGui::TextUnformatted(key);
    ImGui::SameLine(px(ui, 220));
    ImGui::TextDisabled("%s", what);
}

void drawHelp(UiState& ui, float w, float h) {
    if (!ui.help) return;
    ImGui::SetNextWindowBgAlpha(0.97f);
    ImGui::SetNextWindowPos({w * 0.5f, h * 0.5f}, 0, {0.5f, 0.5f});
    ImGui::Begin("Commandes", &ui.help, ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_AlwaysAutoResize |
                                             ImGuiWindowFlags_NoSavedSettings);
    ImGui::TextUnformatted("Souris");
    helpLine(ui, "Clic sur un astre", "y aller (son point ou son nom) ; encore un clic : s'en approcher");
    helpLine(ui, "Glisser", "tourner autour de l'astre suivi");
    helpLine(ui, "Molette", "zoomer, dézoomer");
    ImGui::Separator();
    ImGui::TextUnformatted("Clavier");
    helpLine(ui, "Taper un nom", "chercher un astre ; flèches et Entrée pour choisir");
    helpLine(ui, "1  2  3  4  5", "échelles : système solaire … univers lointain");
    helpLine(ui, "+  −", "zoomer, dézoomer");
    helpLine(ui, "Flèches", "tourner autour de l'astre suivi");
    helpLine(ui, "Retour arrière", "revenir à la vue précédente");
    helpLine(ui, "Origine", "revenir au Soleil");
    helpLine(ui, "Espace", "arrêter ou faire avancer le temps");
    helpLine(ui, "Page préc. / suiv.", "temps plus rapide / plus lent");
    helpLine(ui, "F1", "afficher ou cacher cette aide");
    helpLine(ui, "Échap", "fermer la recherche ou un menu ; sinon quitter");
    ImGui::Spacing();
    if (ImGui::Button("Fermer")) ui.help = false;
    ImGui::End();
}

// ---------------------------------------------------------------- tout

// Dessine toute l'interface pour cette image et applique ce qu'on y fait. Rend toujours -1 : les vols vers un astre
// sont lancés ici (Sim::flyTo), pas par l'appelant.
int drawInterface(Sim& sim, UiState& ui, const Camera& cam, float w, float h) {
    applyScale(ui, h);
    firstFrame(sim, ui);
    if (sim.touched && ui.welcome && ui.tour < 0 && std::getenv("UNIVERS_ECRAN") == nullptr) ui.welcome = false;      // on a pris la main
    const ImGuiWindowFlags fixed = ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_NoTitleBar |
                                   ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_NoSavedSettings;
    ImGuiIO& io = ImGui::GetIO();

    drawOrbits(sim, ui, cam, w, h);
    const bool dragging = ImGui::IsMouseDragging(ImGuiMouseButton_Left, 4.0f);
    const int hovered = io.WantCaptureMouse || dragging ? -1 : pickBody(sim, ui, cam, w, h, io.MousePos);
    drawLabels(sim, ui, cam, w, h, hovered);
    if (hovered >= 0) {
        ImGui::SetMouseCursor(ImGuiMouseCursor_Hand);
        hoverTooltip(sim, cam, hovered);
        const ImVec2 drag = ImGui::GetMouseDragDelta(ImGuiMouseButton_Left, 4.0f);
        if (ImGui::IsMouseReleased(ImGuiMouseButton_Left) && drag.x == 0 && drag.y == 0) goToBody(sim, ui, hovered);
    }
    handleKeys(sim, ui);
    drawTour(sim, ui, w, h, fixed);
    drawTopLeft(sim, ui, fixed);
    drawTimeBar(sim, ui, w, fixed);
    drawCard(sim, ui, cam, w, fixed);
    drawStatus(sim, ui, h, fixed);
    drawCosmology(sim, ui, w, h, fixed);
    drawWelcome(sim, ui, w, h, fixed);
    drawHelp(ui, w, h);
    return -1;
}

}  // namespace
