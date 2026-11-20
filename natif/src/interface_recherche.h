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

void faceOnGalaxy(Sim& sim, UiState& ui);     // interface_bras.h

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

// Couleur du petit rond devant un résultat : la famille de l'astre, la même partout dans l'interface.
ImU32 kindColor(const Body& b) {
    switch (b.kind) {
        case Kind::Sun: return theme::kAccent;
        case Kind::Planet: return b.parent > 0 ? IM_COL32(170, 182, 205, 255) : IM_COL32(110, 170, 255, 255);
        case Kind::Star: return IM_COL32(255, 236, 200, 255);
        case Kind::Galaxy: return IM_COL32(186, 146, 255, 255);
        case Kind::Probe: return theme::kMesure;
        default: return IM_COL32(150, 150, 160, 255);
    }
}

// Une ligne de résultat : rond de couleur, nom, puis en petit gris sa nature et sa distance (calée à droite).
bool richRow(const UiState& ui, const char* id, const std::string& name, const std::string& detail, ImU32 dot, bool selected) {
    ImGui::PushID(id);
    const float wRow = std::max(ImGui::GetContentRegionAvail().x, px(ui, 380));
    const ImVec2 p = ImGui::GetCursorScreenPos();
    const float hRow = ImGui::GetTextLineHeight() + px(ui, 10);
    const bool hit = ImGui::Selectable("##r", selected, ImGuiSelectableFlags_None, {wRow, hRow});
    ImDrawList* dl = ImGui::GetWindowDrawList();
    const float cy = p.y + hRow * 0.5f;
    dl->AddCircleFilled({p.x + px(ui, 10), cy}, px(ui, 4), dot);
    dl->AddText({p.x + px(ui, 24), cy - ImGui::GetTextLineHeight() * 0.5f}, theme::kText, name.c_str());
    if (!detail.empty()) {
        ImFont* f = gFontSmall ? gFontSmall : ImGui::GetFont();
        const float fs = f->FontSize * ImGui::GetIO().FontGlobalScale;
        const ImVec2 ds = f->CalcTextSizeA(fs, FLT_MAX, 0, detail.c_str());
        const float nameRight = p.x + px(ui, 24) + ImGui::CalcTextSize(name.c_str()).x + px(ui, 16);
        const float dx = std::max(nameRight, p.x + wRow - ds.x - px(ui, 8));
        dl->AddText(f, fs, {dx, cy - fs * 0.5f}, theme::kMuted, detail.c_str());
    }
    ImGui::PopID();
    return hit;
}

bool asteroidRow(const Sim& sim, const UiState& ui, int k, bool selected) {
    const asteroides::Catalogue& c = *sim.asteroidCat;
    const char* what = c.isComet(static_cast<size_t>(k)) ? "comète" : "astéroïde";
    const std::string detail = c.eccentricity(static_cast<size_t>(k)) >= 1.0 ? std::string(what) + ", orbite ouverte"
                                                                              : std::string(what) + ", à " + frNum(c.semiMajorAxisAu(static_cast<size_t>(k))) + " UA du Soleil";
    return richRow(ui, ("a" + std::to_string(k)).c_str(), sim.asteroidCat->label(static_cast<size_t>(k)), detail, IM_COL32(150, 150, 160, 255), selected);
}

bool resultRow(const Sim& sim, const UiState& ui, int i, bool selected) {
    if (i < 0) return asteroidRow(sim, ui, -i - 2, selected);
    const Body& b = sim.bodies[static_cast<size_t>(i)];
    const std::string where = b.kind == Kind::Sun ? std::string("notre étoile") : natureOf(b) + "  ·  " + frDistance(std::sqrt(dot(sim.position(i), sim.position(i))));
    return richRow(ui, std::to_string(i).c_str(), b.name, where, kindColor(b), selected);
}

// Raccourcis montrés quand le champ de recherche est vide et choisi : les astres les plus demandés.
const char* const kSuggestions[] = {"Soleil", "Terre", "Lune", "Mars", "Jupiter", "Saturne", "Centre de la Voie lactée", "Andromède (M31)"};

void drawSuggestions(Sim& sim, UiState& ui) {
    sectionLabel("Raccourcis");
    for (const char* n : kSuggestions) {
        const int i = bodyByName(sim, n);
        if (i < 0 || !sim.visible(i)) continue;
        if (resultRow(sim, ui, i, false)) {
            goToBody(sim, ui, i);
            return;
        }
    }
    smallNote("Tape un nom : planète, lune, étoile, galaxie, sonde, astéroïde ou comète.", theme::kFaint);
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
    ImGui::Spacing();
    for (int k = 0; k < n; ++k)
        if (resultRow(sim, ui, found[static_cast<size_t>(k)], k == ui.searchSel)) {
            goToResult(sim, ui, found[static_cast<size_t>(k)]);
            return;
        }
    if (!n) smallNote("Aucun astre ne porte ce nom ici.");
    else smallNote("Entrée : y aller   ·   ↑ ↓ : choisir   ·   Échap : effacer", theme::kFaint);
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
            if (ImGui::MenuItem(sim.bodies[static_cast<size_t>(i)].name.c_str(), sim.visible(i) ? frDistance(d).c_str() : "pas à cette date", false, sim.visible(i)))
                goToBody(sim, ui, i);      // audit B5 : grisé quand l'astre n'a pas de position à cette date
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
    sim.speed = 0;
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

// Ouvre un menu sous le bouton qu'on vient de dessiner.
void popupUnder(UiState& ui, const char* id) {
    ui.goToAnchor = {ImGui::GetItemRectMin().x, ImGui::GetItemRectMax().y + px(ui, 8)};
    ImGui::OpenPopup(id);
}

void drawGoToMenu(Sim& sim, UiState& ui) {
    if (ui.openGoTo || ui.keepGoTo) {
        ImGui::OpenPopup("aller");
        ui.openGoTo = false;
    }
    ImGui::SetNextWindowPos(ui.goToAnchor, ImGuiCond_Appearing);
    if (!ImGui::BeginPopup("aller")) return;
    sectionLabel(sim.visible(0) ? "Échelles, vues depuis le Soleil" : "Échelles, vues depuis le centre de la Voie lactée");
    for (int k = 0; k < kScaleCount; ++k) {
        const char key[2] = {static_cast<char>('1' + k), 0};
        if (ImGui::MenuItem(kScales[k].label, key)) {
            ui.tour = -1;
            ui.welcome = false;
            sim.flyTo(scaleCenter(sim), kScales[k].distLy);
        }
    }
    ImGui::Separator();
    sectionLabel("Astres");
    goToMenuBodies(sim, ui);
    goToMenuProbes(sim, ui);
    ImGui::Separator();
    sectionLabel("Moments et vues");
    if (ImGui::BeginMenu("Éclipses de Soleil")) {
        const int next = nextEclipse(kStartYears);
        for (int k = 0; k < kEclipseCount; ++k)
            if (ImGui::MenuItem(kEclipses[k].label, k == next ? "la prochaine" : nullptr)) showEclipse(sim, ui, k);
        ImGui::Separator();
        smallNote("Calculées d'après les éphémérides de la NASA, contrôlées contre le catalogue des éclipses de la NASA.");
        ImGui::EndMenu();
    }
    if (ImGui::MenuItem("Voie lactée vue de face")) faceOnGalaxy(sim, ui);
    if (ui.gwCount > 0 && ImGui::MenuItem("Ondes gravitationnelles détectées", std::to_string(ui.gwCount).c_str())) ui.gwOpen = true;
    ImGui::EndPopup();
}

// Ce qu'on affiche par-dessus le ciel : structures, nuage d'Oort, routes possibles, textes détaillés.
void drawLayersMenu(Sim& sim, UiState& ui) {
    ImGui::SetNextWindowPos(ui.goToAnchor, ImGuiCond_Appearing);
    if (!ImGui::BeginPopup("couches")) return;
    sectionLabel("Afficher par-dessus le ciel");
    if (sim.structures.loaded && ImGui::MenuItem("Laniakea, son flot et les vides cosmiques", nullptr, sim.structures.showLarge))
        sim.structures.showLarge = !sim.structures.showLarge;
    if (sim.structures.loaded && sim.structures.showLarge &&
        ImGui::MenuItem("Vides et superamas lointains (formes approchées en sphères)", nullptr, sim.structures.showSpheres))
        sim.structures.showSpheres = !sim.structures.showSpheres;
    if (ImGui::MenuItem("Nuage d'Oort (modèle)", nullptr, sim.structures.showOort)) sim.structures.showOort = !sim.structures.showOort;
    if (ImGui::MenuItem("Gaz ionisé de la Voie lactée (régions HII)", nullptr, sim.showGas)) sim.showGas = !sim.showGas;
    if (sim.cloneCount && ImGui::MenuItem("Incertitude : routes possibles des galaxies", nullptr, sim.showClones)) sim.showClones = !sim.showClones;
    ImGui::Separator();
    if (ImGui::MenuItem("Explications détaillées à l'écran", nullptr, ui.details)) ui.details = !ui.details;
    ImGui::EndPopup();
}

// La lumière dans laquelle on voit le ciel (de la radio au gamma).
void drawLightMenu(Sim& sim, UiState& ui) {
    ImGui::SetNextWindowPos(ui.goToAnchor, ImGuiCond_Appearing);
    if (!ImGui::BeginPopup("lumiere")) return;
    if (ImGui::MenuItem("Visible (étoiles mesurées)", nullptr, sim.skyBand < 0)) sim.skyBand = -1;
    ImGui::Separator();
    sectionLabel("Cartes du ciel mesurées, vues depuis la Terre");
    for (int k = 0; k < static_cast<int>(sim.skyBandLabels.size()); ++k)
        if (ImGui::MenuItem(sim.skyBandLabels[static_cast<size_t>(k)].c_str(), nullptr, sim.skyBand == k)) sim.skyBand = k;
    ImGui::Separator();
    smallNote("F2 / F3 : lumière précédente / suivante", theme::kFaint);
    ImGui::EndPopup();
}

// Exposition de l'image (le mode « 100 % mesuré / meilleur rendu » est en haut à droite).
void drawExposureMenu(Sim& sim, UiState& ui) {
    ImGui::SetNextWindowPos(ui.goToAnchor, ImGuiCond_Appearing);
    if (!ImGui::BeginPopup("exposition")) return;
    sectionLabel("Exposition de l'image");
    if (ImGui::MenuItem("Exposition photo automatique", nullptr, sim.photoExposure)) sim.photoExposure = !sim.photoExposure;
    if (ImGui::MenuItem("Plus claire (+1 IL)")) sim.exposureEv += 1.0;
    if (ImGui::MenuItem("Plus sombre (−1 IL)")) sim.exposureEv -= 1.0;
    if (sim.exposureEv != 0 && ImGui::MenuItem("Revenir à la pose normale")) sim.exposureEv = 0;
    ImGui::Separator();
    smallNote("Change seulement l'affichage : l'éclat calculé des astres reste le même.", theme::kFaint);
    ImGui::EndPopup();
}

// Séparateur vertical fin entre deux groupes de la barre d'outils.
void toolbarDivider(const UiState& ui) {
    ImGui::SameLine(0, px(ui, 8));
    const ImVec2 p = ImGui::GetCursorScreenPos();
    const float hh = ImGui::GetFrameHeight();
    ImGui::GetWindowDrawList()->AddLine({p.x, p.y + hh * 0.2f}, {p.x, p.y + hh * 0.8f}, theme::kLine, 1.0f);
    ImGui::Dummy({1, hh});
    ImGui::SameLine(0, px(ui, 8));
}

// En haut à gauche : la barre d'outils. Recherche (avec ses résultats en dessous), puis des boutons-icônes : retour,
// aller à, affichage, lumière, exposition, visite guidée, aide. Chaque bouton ouvre son menu juste en dessous.
void drawTopLeft(Sim& sim, UiState& ui, ImGuiWindowFlags fixed) {
    ImGui::SetNextWindowPos({px(ui, 16), px(ui, 16)});
    ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, {px(ui, 8), px(ui, 8)});
    ImGui::PushStyleVar(ImGuiStyleVar_ItemSpacing, {px(ui, 4), px(ui, 6)});
    ImGui::Begin("chercher", nullptr, fixed);
    cardShadow();
    // Champ de recherche, la loupe dessinée dedans.
    const ImVec2 at = ImGui::GetCursorScreenPos();
    ImGui::SetNextItemWidth(px(ui, 330));
    if (ui.focusSearch) {
        ImGui::SetKeyboardFocusHere();
        ui.focusSearch = false;
    }
    ImGui::PushStyleVar(ImGuiStyleVar_FramePadding, {px(ui, gIcons ? 36 : 12), ImGui::GetStyle().FramePadding.y});
    ImGui::PushStyleVar(ImGuiStyleVar_FrameRounding, ImGui::GetFrameHeight() * 0.5f);
    const bool entered = ImGui::InputTextWithHint("##q", "Rechercher un astre…", ui.search, sizeof(ui.search),
                                                  ImGuiInputTextFlags_EnterReturnsTrue | ImGuiInputTextFlags_EscapeClearsAll | ImGuiInputTextFlags_CallbackAlways, moveCursorToEnd, &ui);
    ImGui::PopStyleVar(2);
    const bool active = ImGui::IsItemActive();
    if (ImGui::IsItemEdited()) ui.searchSel = 0;
    if (!active && ImGui::IsKeyPressed(ImGuiKey_Escape, false)) ui.search[0] = 0;
    if (gIcons)
        ImGui::GetWindowDrawList()->AddText({at.x + px(ui, 13), at.y + ImGui::GetStyle().FramePadding.y}, active ? theme::kAccent : theme::kMuted, ico::kSearch);

    // Boutons-icônes.
    ImGui::SameLine(0, px(ui, 8));
    ImGui::BeginDisabled(sim.history.empty());
    if (iconButton("retour", ico::kBack, "Retour", "Revenir à la vue précédente (Retour arrière)")) {
        ui.tour = -1;
        sim.back();
    }
    ImGui::EndDisabled();
    toolbarDivider(ui);
    if (iconButton("aller", ico::kLocation, "Aller à", "Aller à : échelles, système solaire, étoiles, galaxies, sondes, éclipses", ImGui::IsPopupOpen("aller")))
        popupUnder(ui, "aller");
    if (ui.keepGoTo) ui.goToAnchor = {ImGui::GetItemRectMin().x, ImGui::GetItemRectMax().y + px(ui, 8)};
    ImGui::SameLine();
    if (iconButton("couches", ico::kLayers, "Afficher", "Afficher : Laniakea et les vides, nuage d'Oort, routes possibles, explications", ImGui::IsPopupOpen("couches")))
        popupUnder(ui, "couches");
    if (!sim.skyBandLabels.empty()) {
        ImGui::SameLine();
        if (iconButton("lumiere", ico::kGlobe, "Lumière", "Voir le ciel dans une autre lumière : radio, infrarouge, X, gamma… (F2 / F3)", sim.skyBand >= 0))
            popupUnder(ui, "lumiere");
    }
    ImGui::SameLine();
    if (iconButton("expo", ico::kSun, "Exposition", "Exposition de l'image : plus claire, plus sombre, automatique", sim.exposureEv != 0)) popupUnder(ui, "exposition");
    toolbarDivider(ui);
    if (iconButton("visite", ico::kTour, "Découvrir", ui.tour >= 0 ? "Arrêter la visite guidée" : "Découvrir : visites guidées et moments à revivre", ui.tour >= 0 || ui.discover)) {
        if (ui.tour >= 0) ui.tour = -1;
        else ui.discover = !ui.discover;
    }
    ImGui::SameLine();
    if (iconButton("aide", ico::kHelp, "Aide", "Toutes les commandes (F1)", ui.help)) ui.help = !ui.help;
    ui.searchRight = ImGui::GetItemRectMax().x;
    if (!ImGui::GetIO().WantTextInput && ImGui::IsKeyPressed(ImGuiKey_F4, false)) sim.bestLook = !sim.bestLook;

    drawGoToMenu(sim, ui);
    drawLayersMenu(sim, ui);
    drawLightMenu(sim, ui);
    drawExposureMenu(sim, ui);
    // Résultats sous la barre ; raccourcis quand le champ est vide et choisi.
    if (ui.search[0]) drawSearchResults(sim, ui, active, entered);
    else if (active) drawSuggestions(sim, ui);
    ui.toolbarBottom = ImGui::GetWindowPos().y + ImGui::GetWindowHeight();
    ImGui::End();
    ImGui::PopStyleVar(2);
}

}  // namespace
