// Appli PC « Univers » : ce qui est écrit et cliquable à l'écran (Dear ImGui). Point d'entrée : drawInterface.
// Le code est rangé en quatre fichiers, dans l'ordre où ils s'appuient l'un sur l'autre :
//   interface_base.h (style, état, échelle, orbites et noms, clavier), interface_recherche.h (recherche, « Aller à »),
//   interface_temps.h (barre du temps, fiche), interface_bas.h (bas de l'écran, accueil, visite, aide, complétude).
#pragma once
#include "interface_bas.h"

namespace {

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
    clickAsteroid(sim, ui, cam, w, h, hovered);
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
    drawCompleteness(sim, ui, w, fixed);
    drawCard(sim, ui, cam, w, fixed);
    drawStatus(sim, ui, h, fixed);
    drawCosmology(sim, ui, w, h, fixed);
    drawWelcome(sim, ui, w, h, fixed);
    drawHelp(ui, w, h);
    return -1;
}

}  // namespace
