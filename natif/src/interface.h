// Appli PC « Univers » : ce qui est écrit et cliquable à l'écran (Dear ImGui), habillé aux couleurs de la page.
// Tout ce qu'il faut savoir pour s'en servir est écrit à l'écran : rien n'est à lire ailleurs.
#pragma once
#include <imgui.h>

#include "simulation.h"

namespace {

const ImU32 kInk = IM_COL32(232, 236, 244, 255), kInkSoft = IM_COL32(150, 160, 178, 255), kAccent = IM_COL32(255, 196, 110, 255);

void applyStyle() {
    ImGuiStyle& st = ImGui::GetStyle();
    st.WindowRounding = 10;
    st.FrameRounding = 7;
    st.GrabRounding = 7;
    st.PopupRounding = 8;
    st.WindowBorderSize = 1;
    st.WindowPadding = {14, 12};
    st.FramePadding = {10, 6};
    st.ItemSpacing = {8, 7};
    ImVec4* c = st.Colors;
    c[ImGuiCol_WindowBg] = {0.035f, 0.045f, 0.075f, 0.86f};
    c[ImGuiCol_Border] = {0.30f, 0.36f, 0.50f, 0.35f};
    c[ImGuiCol_Text] = {0.91f, 0.93f, 0.96f, 1.0f};
    c[ImGuiCol_TextDisabled] = {0.59f, 0.63f, 0.70f, 1.0f};
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
}

// Police de Windows avec les accents et les signes utilisés ; à défaut, la police intégrée (sans accents).
void loadFonts(ImFont*& normal, ImFont*& big) {
    ImGuiIO& io = ImGui::GetIO();
    static const ImWchar ranges[] = {0x0020, 0x00FF, 0x2010, 0x2027, 0x2212, 0x2212, 0};
    const char* path = "C:\\Windows\\Fonts\\segoeui.ttf";
    if (std::ifstream(path).good()) {
        normal = io.Fonts->AddFontFromFileTTF(path, 18.0f, nullptr, ranges);
        big = io.Fonts->AddFontFromFileTTF(path, 26.0f, nullptr, ranges);
    }
    if (!normal) normal = big = io.Fonts->AddFontDefault();
}

bool containsNoCase(const std::string& hay, const char* needle) {
    if (!needle[0]) return true;
    auto low = [](unsigned char c) { return static_cast<char>(std::tolower(c)); };
    std::string h(hay.size(), ' '), n(needle);
    std::transform(hay.begin(), hay.end(), h.begin(), low);
    std::transform(n.begin(), n.end(), n.begin(), low);
    return h.find(n) != std::string::npos;
}

void row(const char* label, const std::string& value, const char* status) {
    ImGui::TextDisabled("%s", label);
    ImGui::SameLine(190);
    ImGui::TextUnformatted(value.c_str());
    if (status[0]) {
        ImGui::SameLine();
        ImGui::TextDisabled("(%s)", status);
    }
}

struct UiState {
    char search[64] = "";
    ImFont* normal = nullptr;
    ImFont* big = nullptr;
};

// Dessine toute l'interface pour cette image. Rend le numéro de l'objet dont le nom a été cliqué, ou -1.
int drawInterface(Sim& sim, UiState& ui, const Camera& cam, float w, float h) {
    int clicked = -1;
    const ImGuiWindowFlags fixed = ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_NoTitleBar |
                                   ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_NoSavedSettings;

    // Noms des astres, posés sur l'image ; un clic sur un nom le fait suivre.
    ImDrawList* dl = ImGui::GetBackgroundDrawList();
    const ImVec2 mouse = ImGui::GetIO().MousePos;
    const bool click = ImGui::IsMouseReleased(ImGuiMouseButton_Left) && !ImGui::GetIO().WantCaptureMouse &&
                       ImGui::GetMouseDragDelta(ImGuiMouseButton_Left, 4.0f).x == 0 && ImGui::GetMouseDragDelta(ImGuiMouseButton_Left, 4.0f).y == 0;
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i) {
        double px = 0, py = 0;
        if (!cam.project(sim.position(i), w, h, px, py)) continue;
        const bool isFocus = i == sim.focus;
        const double mag = sim.apparentMag(i, cam.pos) - 2.5 * std::log10(sim.brightnessBoost());
        if (!isFocus && mag > 4.5) continue;      // trop pâle d'ici pour mériter un nom
        const char* name = sim.bodies[static_cast<size_t>(i)].name.c_str();
        const ImVec2 size = ImGui::CalcTextSize(name);
        const ImVec2 at{static_cast<float>(px) + 10, static_cast<float>(py) - size.y * 0.5f};
        const bool hover = mouse.x >= at.x - 14 && mouse.x <= at.x + size.x + 4 && mouse.y >= at.y - 4 && mouse.y <= at.y + size.y + 4;
        if (isFocus) dl->AddCircle({static_cast<float>(px), static_cast<float>(py)}, 9, kAccent, 32, 1.5f);
        dl->AddText({at.x + 1, at.y + 1}, IM_COL32(0, 0, 0, 200), name);
        dl->AddText(at, isFocus || hover ? kAccent : kInkSoft, name);
        if (hover && click) clicked = i;
    }

    // En haut à gauche : chercher un astre.
    ImGui::SetNextWindowPos({16, 16});
    ImGui::Begin("chercher", nullptr, fixed);
    ImGui::SetNextItemWidth(260);
    ImGui::InputTextWithHint("##q", "Chercher un astre (ex. Sirius)", ui.search, sizeof(ui.search));
    if (ui.search[0]) {
        int shown = 0;
        for (int i = 0; i < static_cast<int>(sim.bodies.size()) && shown < 8; ++i) {
            if (!containsNoCase(sim.bodies[static_cast<size_t>(i)].name, ui.search)) continue;
            ++shown;
            if (ImGui::Selectable(sim.bodies[static_cast<size_t>(i)].name.c_str(), i == sim.focus, 0, {260, 0})) {
                clicked = i;
                ui.search[0] = 0;
            }
        }
        if (!shown) ImGui::TextDisabled("Aucun astre nommé ne correspond.");
    }
    ImGui::End();

    // En haut au centre : la date et le temps.
    ImGui::SetNextWindowPos({w * 0.5f, 16}, 0, {0.5f, 0});
    ImGui::Begin("temps", nullptr, fixed);
    ImGui::PushFont(ui.big);
    const std::string date = frDate(sim.years);
    ImGui::SetCursorPosX((ImGui::GetWindowSize().x - ImGui::CalcTextSize(date.c_str()).x) * 0.5f);
    ImGui::TextUnformatted(date.c_str());
    ImGui::PopFont();
    if (ImGui::Button(sim.paused ? "Reprendre" : "Pause")) sim.paused = !sim.paused;
    ImGui::SameLine();
    if (ImGui::Button(sim.backward ? "Le temps recule" : "Le temps avance")) sim.backward = !sim.backward;
    ImGui::SameLine();
    ImGui::SetNextItemWidth(230);
    if (ImGui::BeginCombo("##vitesse", kRates[sim.rate].label)) {
        for (int i = 0; i < kRateCount; ++i)
            if (ImGui::Selectable(kRates[i].label, i == sim.rate)) sim.rate = i;
        ImGui::EndCombo();
    }
    ImGui::SameLine();
    if (ImGui::Button("Aujourd'hui")) sim.years = kStartYears;
    if (std::fabs(sim.years - kStartYears) >= kLinearLimitYears * 0.999)
        ImGui::TextDisabled("Limite : au-delà de 3 millions d'années, les étoiles ne vont plus en ligne droite (à venir).");
    ImGui::End();

    // À droite : la fiche de l'astre suivi.
    const int f = sim.focus;
    const Vec3 p = sim.position(f);
    const double dSun = std::sqrt(dot(p, p));
    ImGui::SetNextWindowPos({w - 16, 16}, 0, {1, 0});
    ImGui::Begin("fiche", nullptr, fixed);
    ImGui::PushFont(ui.big);
    ImGui::TextUnformatted(sim.bodies[static_cast<size_t>(f)].name.c_str());
    ImGui::PopFont();
    ImGui::Separator();
    if (f == 0) {
        row("Nature", "notre étoile", "");
        row("Éclat propre", "magnitude absolue " + frNum(sim.absMag(f)), "mesuré");
    } else {
        // Aujourd'hui la distance est une mesure ; à une autre date, c'est la mesure prolongée en ligne droite.
        row("Distance au Soleil", frDistance(dSun), std::fabs(sim.years - kStartYears) < 1.0 ? "mesuré" : "calculé : mouvement mesuré, prolongé en ligne droite");
        row("Éclat vu de la Terre", "magnitude " + frNum(sim.apparentMag(f, {0, 0, 0})), "calculé");
        row("Éclat propre", "magnitude absolue " + frNum(sim.absMag(f)), "mesuré");
        row("Vitesse", frNum(sim.speedKms(f)) + " km/s par rapport au Soleil", "mesuré");
    }
    const double bv = sim.bv(f);
    row("Température", frNum(4600.0 * (1.0 / (0.92 * bv + 1.7) + 1.0 / (0.92 * bv + 0.62)), 2) + " K en surface", "calculé d'après la couleur");
    row("Vue d'ici", "magnitude " + frNum(sim.apparentMag(f, cam.pos)), "calculé");
    ImGui::Separator();
    ImGui::TextDisabled("Sources : catalogues Hipparcos (HYG) et Gaia DR3.");
    if (f != 0 && ImGui::Button("Revenir au Soleil")) clicked = 0;
    ImGui::End();

    // En bas à gauche : où l'on est, et comment s'en servir.
    ImGui::SetNextWindowPos({16, h - 16}, 0, {0, 1});
    ImGui::Begin("aide", nullptr, fixed);
    const std::string where = "Tu regardes « " + sim.bodies[static_cast<size_t>(f)].name + " » depuis " + frDistance(sim.dist) + ".";
    ImGui::TextUnformatted(where.c_str());
    const double boost = sim.brightnessBoost();
    if (boost > 1.5) ImGui::TextDisabled("Éclat des étoiles multiplié par %s pour qu'elles restent visibles de si loin.", frNum(boost, 2).c_str());
    ImGui::TextDisabled("Molette : zoomer   •   Glisser : tourner autour   •   Clic sur un nom : le suivre   •   Espace : pause   •   Échap : quitter");
    ImGui::End();
    return clicked;
}

}  // namespace
