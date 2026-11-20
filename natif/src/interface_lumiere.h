// Appli PC « Univers » : choix de la lumière du ciel (partie de l'interface, voir interface.h).
//
// « Visible (étoiles mesurées) » par défaut ; sinon une des cartes du ciel mesurées dans une autre lumière (radio, micro-ondes,
// infrarouge, ultraviolet, X, gamma), chargées par fenetre.cpp quand sim.skyBand change. Une carte active garde un encadré
// permanent : son texte (sim.skyLegend, écrit par ciel_bandes.h) dit d'où elle vient, ce qu'elle mesure et ses limites.
#pragma once
#include "interface_bas.h"

namespace {

// Nom court de la lumière choisie, pour le bouton.
std::string lightLabel(const Sim& sim) {
    if (sim.skyBand < 0 || static_cast<size_t>(sim.skyBand) >= sim.skyBandLabels.size()) return "Visible";
    return sim.skyBandLabels[static_cast<size_t>(sim.skyBand)];
}

// Passer à la lumière suivante (+1) ou précédente (-1), de la radio au gamma, en passant par le visible.
void stepLight(Sim& sim, int step) {
    const int n = static_cast<int>(sim.skyBandLabels.size());
    if (n == 0) return;
    const int at = sim.skyBand + 1;      // 0 : visible, puis les cartes
    sim.skyBand = (at + step + n + 1) % (n + 1) - 1;
}

void lightKeys(Sim& sim) {
    if (ImGui::GetIO().WantTextInput) return;
    if (ImGui::IsKeyPressed(ImGuiKey_F3, false)) stepLight(sim, +1);
    if (ImGui::IsKeyPressed(ImGuiKey_F2, false)) stepLight(sim, -1);
}

// Encadré permanent en bas à droite tant qu'une carte est choisie : le texte de la carte, ligne par ligne.
void drawLightLegend(Sim& sim, const UiState& ui, float w, float h, ImGuiWindowFlags fixed) {
    if (sim.skyBand < 0 || sim.skyLegend.empty()) return;
    ImGui::SetNextWindowPos({w - px(ui, 16), std::min(h - px(ui, 16), ui.dockTop - px(ui, 12))}, 0, {1, 1});      /* au-dessus du temps, à gauche du panneau */
    ImGui::Begin("lumiere-legende", nullptr, fixed);
    cardShadow();
    ImGui::PushTextWrapPos(ImGui::GetCursorPosX() + px(ui, 560));
    for (size_t i = 0; i < sim.skyLegend.size(); ++i) {
        if (i == 0) ImGui::TextUnformatted(sim.skyLegend[i].c_str());
        else ImGui::TextDisabled("%s", sim.skyLegend[i].c_str());
    }
    ImGui::PopTextWrapPos();
    if (ImGui::Button("Revenir au visible")) sim.skyBand = -1;
    ImGui::SameLine();
    ImGui::TextDisabled("F2 / F3 : lumière précédente / suivante");
    ImGui::End();
}

}  // namespace
