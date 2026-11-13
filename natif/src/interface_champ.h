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
        ImGui::TextDisabled("%s", ("Éclat ×" + frInt(sim.fieldGain()) + " : pose plus longue, comme à la lunette (affichage seulement)").c_str());
        if (sim.gaiaSkyActive) {
            const std::string lim = sim.gaiaSkyLimit > 50 ? "toutes" : "jusqu'à la magnitude " + frNum(sim.gaiaSkyLimit, 2);
            ImGui::TextDisabled("%s", ("Gaia une à une : " + frInt(sim.gaiaSkyStars) + " sources sans distance mesurée (" + lim + "), direction mesurée").c_str());
            if (sim.gaiaSkyPending > 0) {
                ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(1.0f, 0.77f, 0.43f, 1.0f));
                ImGui::Text("Chargement depuis le Drive : %u morceaux du ciel…", sim.gaiaSkyPending);
                ImGui::PopStyleColor();
            }
        }
    } else {
        ImGui::TextDisabled("Ctrl + molette : grossir la carte");
    }
    ImGui::End();
}

}  // namespace
