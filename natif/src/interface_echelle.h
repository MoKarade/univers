// Appli PC « Univers » : échelle de zoom, sur le bord gauche (refonte de l'interface, 20/11/2026).
// Cinq crans, du système solaire à l'univers lointain (les touches 1 à 5). Un repère ambre montre où se trouve la vue
// entre deux crans (distance de la caméra à l'astre suivi, en échelle logarithmique). Clic sur un cran : on y vole.
// Au repos, seul le nom du cran le plus proche est écrit ; au survol, tous.
#pragma once
#include "interface_base.h"
#include "interface_recherche.h"

namespace {

const char* const kScaleShort[kScaleCount] = {"Système solaire", "Étoiles voisines", "Étoiles mesurées", "Groupe local", "Univers lointain"};

void drawScaleLadder(Sim& sim, UiState& ui, float h, ImGuiWindowFlags fixed) {
    double dists[kScaleCount];
    for (int k = 0; k < kScaleCount; ++k) dists[k] = kScales[k].distLy;
    const double pos = ui_outils::positionEchelle(sim.dist, dists, kScaleCount);
    const int nearest = static_cast<int>(std::lround(pos));
    const float step = px(ui, 44), dot = px(ui, 5);
    const float trackH = step * (kScaleCount - 1);

    ImGui::SetNextWindowPos({px(ui, 16), h * 0.5f}, 0, {0, 0.5f});
    ImGui::SetNextWindowBgAlpha(0.0f);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowBorderSize, 0.0f);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, {px(ui, 6), px(ui, 10)});
    ImGui::Begin("echelle", nullptr, fixed);
    const bool hov = ImGui::IsWindowHovered(ImGuiHoveredFlags_ChildWindows | ImGuiHoveredFlags_AllowWhenBlockedByPopup);
    ImDrawList* dl = ImGui::GetWindowDrawList();
    const ImVec2 o = ImGui::GetCursorScreenPos();
    const float cx = o.x + px(ui, 10);
    // Cran du haut = le plus loin (on « monte » en s'éloignant).
    auto yOf = [&](double p) { return o.y + trackH - static_cast<float>(p) * step; };
    dl->AddLine({cx, yOf(0)}, {cx, yOf(kScaleCount - 1)}, IM_COL32(255, 255, 255, 40), 2.0f * ui.s);
    float labelW = 0;
    for (int k = 0; k < kScaleCount; ++k) labelW = std::max(labelW, ImGui::CalcTextSize(kScaleShort[k]).x);
    for (int k = 0; k < kScaleCount; ++k) {
        const float y = yOf(k);
        ImGui::SetCursorScreenPos({o.x, y - step * 0.5f});
        ImGui::PushID(k);
        const bool hit = ImGui::InvisibleButton("cran", {px(ui, 24) + (hov ? labelW + px(ui, 12) : 0), step});
        const bool hovK = ImGui::IsItemHovered();
        ImGui::PopID();
        if (hit) {
            ui.tour = -1;
            ui.welcome = false;
            sim.flyTo(scaleCenter(sim), kScales[k].distLy);
        }
        if (hovK) ImGui::SetTooltip("%s  (touche %d)", kScales[k].label, k + 1);
        dl->AddCircleFilled({cx, y}, dot, hovK ? theme::kText : IM_COL32(150, 160, 185, 200), 20);
        if (hov || k == nearest) {
            const ImU32 col = k == nearest ? theme::kText : theme::kMuted;
            const ImVec2 ts = ImGui::CalcTextSize(kScaleShort[k]);
            const ImVec2 tp{cx + px(ui, 14), y - ts.y * 0.5f};
            dl->AddText({tp.x + 1, tp.y + 1}, IM_COL32(0, 0, 0, 200), kScaleShort[k]);
            dl->AddText(tp, col, kScaleShort[k]);
        }
    }
    // Repère : où est la vue.
    const float ym = yOf(pos);
    dl->AddCircleFilled({cx, ym}, dot + px(ui, 3), theme::alpha(theme::kAccent, 0.25f), 24);
    dl->AddCircleFilled({cx, ym}, dot, theme::kAccent, 24);
    ImGui::SetCursorScreenPos({o.x, o.y + trackH + step * 0.5f});
    ImGui::Dummy({px(ui, 24), 0});
    ImGui::End();
    ImGui::PopStyleVar(2);
}

}  // namespace
