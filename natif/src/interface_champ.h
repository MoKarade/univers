// Champ de vision (Ctrl + molette, Sim::zoomField) : petite pastille en bas au centre tant qu'on a grossi, avec le
// champ en degrés et un bouton pour revenir à 60°. Quand une carte « Lumière » est affichée, la pastille rappelle aussi
// comment grossir (une carte du ciel n'a pas de profondeur : se rapprocher ne la grossit pas).
#pragma once
#include "interface_ondes.h"

namespace {

void drawFieldChip(Sim& sim, const UiState& ui, float w, float h, ImGuiWindowFlags fixed) {
    const bool zoomed = sim.fovDeg < Sim::kFovMax - 0.01;
    if (!zoomed && sim.skyBand < 0) return;
    ImGui::SetNextWindowPos({w * 0.5f, h - px(ui, 16)}, ImGuiCond_Always, {0.5f, 1.0f});
    ImGui::SetNextWindowBgAlpha(0.6f);
    ImGui::Begin("champ", nullptr, fixed);
    const double f = sim.fovDeg;
    const std::string deg = f >= 10 ? frInt(f) : frNum(f, 2);
    if (zoomed) {
        ImGui::TextUnformatted(("Champ de vision : " + deg + "°").c_str());
        ImGui::SameLine();
        if (ImGui::SmallButton("60°")) sim.fovDeg = Sim::kFovMax;
    } else {
        ImGui::TextDisabled("Ctrl + molette : grossir la carte");
    }
    ImGui::End();
}

}  // namespace
