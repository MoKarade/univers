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

// Bouton « Lumière » de la barre du haut (à côté de « Aller à »), et sa liste.
void lightButton(Sim& sim, UiState& ui) {
    if (sim.skyBandLabels.empty()) return;
    ImGui::SameLine();
    const std::string label = "Lumière : " + lightLabel(sim) + "##lumiere";
    if (ImGui::Button(label.c_str())) ImGui::OpenPopup("lumiere");
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Voir le ciel dans une autre lumière (F2 : précédente, F3 : suivante)");
    const ImVec2 anchor{ImGui::GetItemRectMin().x, ImGui::GetItemRectMax().y + px(ui, 6)};
    ui.searchRight = ImGui::GetItemRectMax().x;
    ImGui::SetNextWindowPos(anchor, ImGuiCond_Appearing);
    if (!ImGui::BeginPopup("lumiere")) return;
    if (ImGui::MenuItem("Visible (étoiles mesurées)", nullptr, sim.skyBand < 0)) sim.skyBand = -1;
    ImGui::Separator();
    ImGui::TextDisabled("Cartes du ciel mesurées, de la radio au gamma (vues depuis la Terre)");
    for (int k = 0; k < static_cast<int>(sim.skyBandLabels.size()); ++k)
        if (ImGui::MenuItem(sim.skyBandLabels[static_cast<size_t>(k)].c_str(), nullptr, sim.skyBand == k)) sim.skyBand = k;
    ImGui::EndPopup();
}

void lightKeys(Sim& sim) {
    if (ImGui::GetIO().WantTextInput) return;
    if (ImGui::IsKeyPressed(ImGuiKey_F3, false)) stepLight(sim, +1);
    if (ImGui::IsKeyPressed(ImGuiKey_F2, false)) stepLight(sim, -1);
}

// Encadré permanent en bas à droite tant qu'une carte est choisie : le texte de la carte, ligne par ligne.
void drawLightLegend(Sim& sim, const UiState& ui, float w, float h, ImGuiWindowFlags fixed) {
    if (sim.skyBand < 0 || sim.skyLegend.empty()) return;
    ImGui::SetNextWindowPos({w - px(ui, 16), h - px(ui, 16)}, 0, {1, 1});
    ImGui::Begin("lumiere-legende", nullptr, fixed);
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
