// Appli PC « Univers » : ce qui est écrit et cliquable à l'écran (Dear ImGui). Point d'entrée : drawInterface.
// Le code est rangé en fichiers, dans l'ordre où ils s'appuient l'un sur l'autre :
//   interface_base.h (style, état, échelle, orbites et noms, clavier), interface_recherche.h (recherche, « Aller à »),
//   interface_temps.h (barre du temps, valeurs d'un astre), interface_bas.h (bas de l'écran, accueil, visite, aide, complétude),
//   interface_panneau.h (panneau d'information à droite : astre, univers, réglages) et interface_frise.h (frise du temps).
#pragma once
#include "interface_champ.h"
#include "interface_frise.h"

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
    // Bas de l'écran : la frise prend une bande ; les fenêtres posées en bas se calent au-dessus.
    const float friseH = ImGui::GetFontSize() * 2.0f + px(ui, 42);
    const float hUp = h - friseH - px(ui, 10);

    drawOrbits(sim, ui, cam, w, h);
    drawObjectOrbit(sim, ui, cam, w, h);
    const bool dragging = ImGui::IsMouseDragging(ImGuiMouseButton_Left, 4.0f);
    const int hovered = io.WantCaptureMouse || dragging ? -1 : pickBody(sim, ui, cam, w, h, io.MousePos);
    drawLabels(sim, ui, cam, w, h, hovered);
    drawArmLabels(sim, ui, cam, w, h);
    clickArmTracer(sim, ui, cam, w, h, hovered);
    clickAsteroid(sim, ui, cam, w, h, hovered);
    if (hovered >= 0) {
        ImGui::SetMouseCursor(ImGuiMouseCursor_Hand);
        hoverTooltip(sim, cam, hovered);
        const ImVec2 drag = ImGui::GetMouseDragDelta(ImGuiMouseButton_Left, 4.0f);
        if (ImGui::IsMouseReleased(ImGuiMouseButton_Left) && drag.x == 0 && drag.y == 0) {
            goToBody(sim, ui, hovered);
            gBac.open = true;      // un astre choisi : son panneau s'ouvre
            gBac.tab = 0;
        }
    }
    handleKeys(sim, ui);
    drawTour(sim, ui, w, hUp, fixed);
    drawTopLeft(sim, ui, fixed);
    drawTimeBar(sim, ui, w, fixed);
    lightKeys(sim);
    drawLightLegend(sim, ui, w, hUp, fixed);
    drawCompleteness(sim, ui, w, fixed);
    drawHow(sim, ui, w, fixed);
    const float panelTop = std::max({px(ui, 150), ui.timeBottom + px(ui, 12), ui.completenessBottom + px(ui, 12)});
    drawPanel(sim, ui, cam, w, h, panelTop, hUp);
    drawFrise(sim, ui, h, friseH);
    drawArmCard(sim, ui, cam, std::min(gBac.panelLeft, w), hUp, fixed);
    drawStatus(sim, ui, hUp, fixed);
    drawWelcome(sim, ui, std::min(gBac.panelLeft, w), hUp, fixed);
    drawHelp(ui, w, h);
    drawGravWaves(ui, w, hUp);
    drawFieldChip(sim, ui, std::min(gBac.panelLeft, w), hUp, fixed);
    return -1;
}

}  // namespace
