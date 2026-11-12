// Appli PC « Univers » : recherche et menu « Aller à » (partie de l'interface, voir interface.h).
#pragma once
#include "interface_base.h"

namespace {

// ---------------------------------------------------------------- recherche et « Aller à »

int kindRank(const Body& b) {
    if (b.kind == Kind::Sun) return 0;
    if (b.kind == Kind::Planet) return b.parent == 0 ? 0 : 1;
    if (b.kind == Kind::Probe || b.kind == Kind::Asteroid) return 1;
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

// Astéroïdes du catalogue dont le nom ou le numéro contient le texte (au plus 6), rangés après les astres nommés.
// Codés -(k + 2) dans la liste des résultats (k : rang dans le catalogue).
void addAsteroidResults(const Sim& sim, UiState& ui, std::vector<int>& found) {
    if (!sim.asteroidCat || sim.asteroidBody < 0) return;
    const std::string q = ui.search;
    if (q != ui.astQuery) {
        ui.astQuery = q;
        if (!ui.astIndex.built) {      // comètes en tête : « halley » donne 1P/Halley avant l'astéroïde Halley (2688)
            std::vector<char> comets(sim.asteroidCat->names.size(), 0);
            for (size_t k = 0; k < comets.size(); ++k) comets[k] = sim.asteroidCat->isComet(k) ? 1 : 0;
            ui.astIndex.build(sim.asteroidCat->names, comets);
        }
        ui.astFound = ui.astIndex.find(q, 6);
    }
    for (const int k : ui.astFound) found.push_back(-(k + 2));
}

void lightButton(Sim& sim, UiState& ui);      // interface_lumiere.h
void faceOnButton(Sim& sim, UiState& ui);     // interface_bras.h

// Aller à un résultat : un astre de la liste, ou un astéroïde du catalogue (désigné d'abord).
void goToResult(Sim& sim, UiState& ui, int r);

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
bool asteroidRow(const Sim& sim, const UiState& ui, int k, bool selected) {
    const std::string name = sim.asteroidCat->label(static_cast<size_t>(k));
    ImGui::PushID(-k - 2);
    const float x0 = ImGui::GetCursorPosX();
    const bool hit = ImGui::Selectable(name.c_str(), selected, ImGuiSelectableFlags_AllowOverlap, {px(ui, 440), 0});
    ImGui::SameLine(x0 + ImGui::CalcTextSize(name.c_str()).x + px(ui, 12));
    const asteroides::Catalogue& c = *sim.asteroidCat;
    const char* what = c.isComet(static_cast<size_t>(k)) ? "comète" : "astéroïde";
    if (c.eccentricity(static_cast<size_t>(k)) >= 1.0) ImGui::TextDisabled("%s, orbite ouverte", what);
    else ImGui::TextDisabled("%s, orbite à %s fois la distance Terre-Soleil", what, frNum(c.semiMajorAxisAu(static_cast<size_t>(k))).c_str());
    ImGui::PopID();
    return hit;
}

bool resultRow(const Sim& sim, const UiState& ui, int i, bool selected) {
    if (i < 0) return asteroidRow(sim, ui, -i - 2, selected);
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
    std::vector<int> found = searchResults(sim, ui.search);
    addAsteroidResults(sim, ui, found);
    const int n = static_cast<int>(found.size());
    if (inputActive && n) {
        if (ImGui::IsKeyPressed(ImGuiKey_DownArrow)) ui.searchSel = (ui.searchSel + 1) % n;
        if (ImGui::IsKeyPressed(ImGuiKey_UpArrow)) ui.searchSel = (ui.searchSel + n - 1) % n;
    }
    ui.searchSel = std::clamp(ui.searchSel, 0, std::max(n - 1, 0));
    if (entered && n) {
        goToResult(sim, ui, found[static_cast<size_t>(ui.searchSel)]);
        return;
    }
    for (int k = 0; k < n; ++k)
        if (resultRow(sim, ui, found[static_cast<size_t>(k)], k == ui.searchSel)) {
            goToResult(sim, ui, found[static_cast<size_t>(k)]);
            return;
        }
    if (!n) ImGui::TextDisabled("Aucun astre nommé ne correspond.");
    else ImGui::TextDisabled("Entrée : y aller   •   flèches : choisir   •   Échap : fermer");
}

void goToResult(Sim& sim, UiState& ui, int r) {
    if (r >= 0) {
        goToBody(sim, ui, r);
        return;
    }
    const int i = sim.selectAsteroid(-r - 2);
    if (i >= 0 && sim.visible(i)) goToBody(sim, ui, i);
    else ui.search[0] = 0;      // hors des 300 ans autour de la date des orbites : position inconnue
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

// Voyager 1 au plus près de Jupiter, le 5 mars 1979 (sim.years = -20,826, donnée par le fil du rendu).
void showVoyagerJupiter(Sim& sim, UiState& ui) {
    const int v = bodyByName(sim, "Voyager 1");
    ui.tour = -1;
    ui.welcome = false;
    sim.years = -20.826;
    sim.paused = true;
    sim.backward = false;
    sim.rate = 1;      // 1 heure par seconde : le survol se déroule en quelques secondes
    sim.refreshEphemeris();
    if (v >= 0 && sim.visible(v)) sim.flyTo(v);
}

void goToMenuProbes(Sim& sim, UiState& ui) {
    bool any = false;
    for (const Body& b : sim.bodies) any |= b.kind == Kind::Probe;
    if (!any || !ImGui::BeginMenu("Sondes")) return;
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i) {
        const Body& b = sim.bodies[static_cast<size_t>(i)];
        if (b.kind != Kind::Probe) continue;
        // Une sonde n'a de position qu'aux dates fournies par le JPL : grisée sinon.
        if (ImGui::MenuItem(b.name.c_str(), sim.visible(i) ? nullptr : "pas à cette date", false, sim.visible(i))) goToBody(sim, ui, i);
    }
    ImGui::Separator();
    if (ImGui::MenuItem("Voyager 1 survole Jupiter (5 mars 1979)")) showVoyagerJupiter(sim, ui);
    ImGui::EndMenu();
}

void drawGoToMenu(Sim& sim, UiState& ui) {
    if (ui.openGoTo || ui.keepGoTo) {
        ImGui::OpenPopup("aller");
        ui.openGoTo = false;
    }
    ImGui::SetNextWindowPos(ui.goToAnchor, ImGuiCond_Appearing);
    if (!ImGui::BeginPopup("aller")) return;
    ImGui::TextDisabled(sim.visible(0) ? "Échelles (vues depuis le Soleil)" : "Échelles (vues depuis le centre de la Voie lactée)");
    for (int k = 0; k < kScaleCount; ++k) {
        const char key[2] = {static_cast<char>('1' + k), 0};
        if (ImGui::MenuItem(kScales[k].label, key)) {
            ui.tour = -1;
            ui.welcome = false;
            sim.flyTo(scaleCenter(sim), kScales[k].distLy);
        }
    }
    ImGui::Separator();
    goToMenuBodies(sim, ui);
    goToMenuProbes(sim, ui);
    ImGui::Separator();
    if (ImGui::MenuItem("Visite guidée")) startTour(sim, ui, 0);
    if (ImGui::BeginMenu("Éclipses de Soleil")) {
        const int next = nextEclipse(kStartYears);
        for (int k = 0; k < kEclipseCount; ++k)
            if (ImGui::MenuItem(kEclipses[k].label, k == next ? "la prochaine" : nullptr)) showEclipse(sim, ui, k);
        ImGui::Separator();
        ImGui::TextDisabled("Calculées d'après les éphémérides de la NASA,");
        ImGui::TextDisabled("contrôlées contre le catalogue des éclipses de la NASA.");
        ImGui::EndMenu();
    }
    if (ui.gwCount > 0 && ImGui::MenuItem("Ondes gravitationnelles détectées", std::to_string(ui.gwCount).c_str())) ui.gwOpen = true;
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
    ui.searchRight = ImGui::GetItemRectMax().x;
    lightButton(sim, ui);
    faceOnButton(sim, ui);
    drawGoToMenu(sim, ui);
    drawSearchResults(sim, ui, active, entered);
    ImGui::End();
}

}  // namespace
