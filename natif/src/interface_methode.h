// Appli PC « Univers » : comment est obtenu ce qui est à l'écran, famille par famille (partie de l'interface, voir
// interface.h). Demande de Marc (12/11/2026) : « je veux voir quand ça montre ce qui a été calculé en amont sur carte
// graphique ou approximation ». Une ligne permanente en haut à droite, sous la complétude ; le tableau au clic.
#pragma once
#include "interface_lumiere.h"

namespace {

enum class How { Measured, Exact, Precomputed, Approx, Hidden };

struct HowRow {
    const char* family;
    How how;
    std::string text;
};

const char* howWord(How h) {
    switch (h) {
        case How::Measured: return "mesuré";
        case How::Exact: return "calculé";
        case How::Precomputed: return "précalculé";
        case How::Approx: return "approximation";
        default: return "non montré";
    }
}

ImU32 howColor(How h) {
    switch (h) {
        case How::Measured: return IM_COL32(140, 210, 150, 255);
        case How::Exact: return IM_COL32(140, 180, 240, 255);
        case How::Precomputed: return IM_COL32(120, 200, 200, 255);
        case How::Approx: return IM_COL32(255, 196, 110, 255);
        default: return IM_COL32(150, 160, 178, 255);
    }
}

// Ce qui sert à l'image en ce moment, famille par famille. Rien n'est supposé : chaque ligne suit un champ de Sim.
std::vector<HowRow> howRows(const Sim& sim) {
    std::vector<HowRow> r;
    const bool today = std::fabs(sim.years - kStartYears) < 1.0;
    const bool starsShown = sim.starShare() > 0;
    // Étoiles du catalogue principal (orbites exactes pas à pas sur la carte graphique, 345c11d).
    if (!starsShown) r.push_back({"Étoiles mesurées", How::Hidden, "remplacées par le calcul de la fusion à cette date"});
    else if (today) r.push_back({"Étoiles (catalogue principal)", How::Measured, "position et vitesse mesurées (Hipparcos, Gaia)"});
    else if (sim.orbitLagSteps > 0)
        r.push_back({"Étoiles (catalogue principal)", How::Approx,
                     "épicycles en attendant le calcul exact (encore " + frInt(static_cast<double>(sim.orbitLagSteps)) + " millions d'années à parcourir)"});
    else r.push_back({"Étoiles (catalogue principal)", How::Exact, "orbite exacte, calculée pas à pas sur la carte graphique, potentiel [modèle]"});
    // Étoiles Gaia : épicycles tant que le fil Gaia n'a pas basculé sur le calcul exact.
    if (sim.hasGaia && starsShown) {
        if (today) r.push_back({"Étoiles Gaia", How::Measured, "position mesurée par Gaia DR3"});
        else r.push_back({"Étoiles Gaia", How::Approx, "épicycles (orbite approchée), calculés sur la carte graphique"});
    }
    if (sim.hasGaiaAggregate)
        r.push_back(sim.deepTime() ? HowRow{"Lumière additionnée Gaia", How::Hidden, "montrée seulement au présent"}
                                   : HowRow{"Lumière additionnée Gaia", How::Measured, "somme des sources mesurées, par case, sans modèle"});
    // Planètes, Lune, autres lunes.
    if (!sim.spk) r.push_back({"Planètes", How::Hidden, "fichier de la NASA absent"});
    else if (sim.ephemValid) {
        r.push_back({"Planètes et Lune", How::Precomputed, "éphémérides de la NASA (DE440, calculées d'avance par le JPL), lues telles quelles"});
        r.push_back({"Autres lunes", How::Precomputed, "éphémérides des satellites du JPL, lues telles quelles"});
    } else {
        bool planets = false, moon = false;
        for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i) {
            const Body& b = sim.bodies[static_cast<size_t>(i)];
            if (b.kind != Kind::Planet || !sim.visible(i)) continue;
            planets |= b.parent == 0;
            moon |= b.naif == eph::kMoon;
        }
        if (!sim.outer) r.push_back({"Planètes", How::Hidden, "calcul en préparation"});
        else if (planets) r.push_back({"Planètes", How::Exact, "calculées ici : gravité mutuelle partie de la NASA, puis table des orbites"});
        else r.push_back({"Planètes", How::Hidden, "hors des 10 millions d'années calculés"});
        if (moon) r.push_back({"Lune", How::Approx, "théorie de Meeus (formule approchée)"});
        r.push_back({"Autres lunes", How::Hidden, "position inconnue hors de 1550-2650"});
    }
    // Astéroïdes et comètes (Kepler sur la carte graphique, sans l'attraction des planètes).
    if (sim.asteroidCount) {
        if (sim.asteroidGain(sim.asteroidEpochJd) > 0)
            r.push_back({"Astéroïdes et comètes", How::Approx, "orbites mesurées (JPL), suivies sur la carte graphique sans l'attraction des planètes"});
        else r.push_back({"Astéroïdes et comètes", How::Hidden, "à plus de 300 ans de la date de leurs orbites"});
    }
    // Galaxies, et calcul de la fusion.
    if (!sim.deepTime()) r.push_back({"Galaxies", How::Measured, "positions mesurées (distances et décalages vers le rouge)"});
    else r.push_back({"Galaxies du Groupe local", How::Precomputed, "calcul complet de la rencontre avec Andromède (fait d'avance, scénario), rejoué"});
    if (sim.replay && sim.starShare() < 1)
        r.push_back({"Étoiles-tests de la fusion", How::Precomputed, "300 000 particules calculées d'avance, rejouées image par image (scénario)"});
    return r;
}

// La ligne permanente : les approximations en cours s'il y en a, sinon « mesuré ou calculé exactement ».
std::string howSummary(const std::vector<HowRow>& rows) {
    std::string approx;
    for (const HowRow& h : rows)
        if (h.how == How::Approx) approx += (approx.empty() ? "" : ", ") + std::string(h.family);
    if (approx.empty()) return "Comment c'est obtenu : mesuré, lu ou calculé exactement (clic : détail)";
    return "Comment c'est obtenu : approximation pour " + approx + " (clic : détail)";
}

void drawHow(const Sim& sim, UiState& ui, float w, ImGuiWindowFlags fixed) {
    const std::vector<HowRow> rows = howRows(sim);
    bool approx = false;
    for (const HowRow& h : rows) approx |= h.how == How::Approx;
    // Sous la complétude ; si elle mordrait sur la barre du temps, sous celle-ci.
    float y = ui.completenessBottom + px(ui, 8);
    if (w - px(ui, 16) - ui.howW < ui.timeRight + px(ui, 8)) y = std::max(y, ui.timeBottom + px(ui, 8));
    ImGui::SetNextWindowPos({w - px(ui, 16), y}, 0, {1, 0});
    ImGui::Begin("methode-ligne", nullptr, fixed);
    const std::string line = howSummary(rows);
    ImGui::PushStyleColor(ImGuiCol_Text, approx ? ImGui::ColorConvertU32ToFloat4(howColor(How::Approx)) : ImGui::GetStyle().Colors[ImGuiCol_Text]);
    if (ImGui::Selectable(line.c_str(), ui.howOpen)) ui.howOpen = !ui.howOpen;
    ImGui::PopStyleColor();
    ui.completenessBottom = ImGui::GetWindowPos().y + ImGui::GetWindowHeight();      // la fiche se place en dessous
    ui.howW = ImGui::GetWindowWidth();
    ImGui::End();
    if (!ui.howOpen) return;
    ImGui::SetNextWindowPos({w * 0.5f, ImGui::GetIO().DisplaySize.y * 0.5f}, 0, {0.5f, 0.5f});
    ImGui::SetNextWindowBgAlpha(0.97f);
    ImGui::SetNextWindowFocus();
    ImGui::Begin("Comment c'est obtenu", &ui.howOpen, ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_NoSavedSettings);
    ImGui::TextDisabled("À la date et à l'échelle affichées, pour chaque famille d'objets :");
    if (ImGui::BeginTable("methode", 3, ImGuiTableFlags_RowBg | ImGuiTableFlags_SizingFixedFit | ImGuiTableFlags_NoHostExtendX)) {
        for (const HowRow& h : rows) {
            ImGui::TableNextRow();
            ImGui::TableNextColumn();
            ImGui::TextUnformatted(h.family);
            ImGui::TableNextColumn();
            ImGui::PushStyleColor(ImGuiCol_Text, ImGui::ColorConvertU32ToFloat4(howColor(h.how)));
            ImGui::TextUnformatted(howWord(h.how));
            ImGui::PopStyleColor();
            ImGui::TableNextColumn();
            ImGui::TextDisabled("%s", h.text.c_str());
        }
        ImGui::EndTable();
    }
    ImGui::Spacing();
    ImGui::TextDisabled("mesuré : lu dans un catalogue d'observations   •   précalculé : calculé d'avance (NASA, JPL, ou ici) puis lu");
    ImGui::TextDisabled("calculé : calculé ici pendant que tu regardes   •   approximation : formule ou méthode approchée, plus rapide");
    if (ImGui::Button("Fermer")) ui.howOpen = false;
    ImGui::End();
}

}  // namespace
