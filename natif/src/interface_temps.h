// Appli PC « Univers » : barre du temps et fiche de l'astre suivi (partie de l'interface, voir interface.h).
#pragma once
#include "interface_base.h"
#include "interface_recherche.h"

namespace {

// ---------------------------------------------------------------- temps

// Bouton dessiné : lecture (triangle) ou pause (deux barres).
bool playButton(const UiState& ui, bool paused) {
    const float sz = ImGui::GetFrameHeight();
    const ImVec2 p = ImGui::GetCursorScreenPos();
    const bool hit = ImGui::Button("##play", {sz * 1.4f, sz});
    const bool hov = ImGui::IsItemHovered();
    ImDrawList* dl = ImGui::GetWindowDrawList();
    const ImVec2 c{p.x + sz * 0.7f, p.y + sz * 0.5f};
    const float r = sz * 0.26f;
    const ImU32 col = hov ? kAccent : IM_COL32(235, 238, 245, 255);
    if (paused) dl->AddTriangleFilled({c.x - r * 0.8f, c.y - r}, {c.x - r * 0.8f, c.y + r}, {c.x + r, c.y}, col);
    else {
        dl->AddRectFilled({c.x - r * 0.85f, c.y - r}, {c.x - r * 0.25f, c.y + r}, col, 1.5f * ui.s);
        dl->AddRectFilled({c.x + r * 0.25f, c.y - r}, {c.x + r * 0.85f, c.y + r}, col, 1.5f * ui.s);
    }
    if (hov) ImGui::SetTooltip(paused ? "Faire avancer le temps (Espace)" : "Arrêter le temps (Espace)");
    return hit;
}

// Écart à aujourd'hui, en mots : « aujourd'hui », « dans 3 jours », « il y a 250 ans ».
std::string relativeToToday(double years) {
    const double d = years - kStartYears, a = std::fabs(d);
    std::string span;
    if (a < 1.0 / 365.25) return "aujourd'hui";
    if (a < 1.0 / 12.0) span = frInt(a * 365.25) + (a * 365.25 >= 1.5 ? " jours" : " jour");
    else if (a < 1.0) span = frInt(a * 12.0) + (a * 12.0 >= 1.5 ? " mois" : " mois");
    else if (a < 1.0e6) span = frInt(a) + (a >= 1.5 ? " ans" : " an");
    else if (a < 1.0e9) span = frNum(a / 1.0e6) + " millions d'années";
    else span = frNum(a / 1.0e9) + (a >= 1.5e9 ? " milliards d'années" : " milliard d'années");
    return d > 0 ? "dans " + span : "il y a " + span;
}

void dateJumpPopup(Sim& sim, UiState& ui) {
    if (!ImGui::BeginPopup("date")) return;
    ImGui::TextUnformatted("Aller à une date");
    ImGui::TextDisabled("Exemples : 1969   •   21/07/1969   •   -3000   •   250000   •   5000000000");
    if (ImGui::IsWindowAppearing()) ImGui::SetKeyboardFocusHere();
    ImGui::SetNextItemWidth(px(ui, 220));
    bool go = ImGui::InputText("##d", ui.dateText, sizeof(ui.dateText), ImGuiInputTextFlags_EnterReturnsTrue);
    ImGui::SameLine();
    go |= ImGui::Button("Y aller");
    if (go) {
        double y = 0;
        ui.dateError = !ui_outils::parseDate(ui.dateText, y);
        if (!ui.dateError) {
            sim.years = std::clamp(y, sim.minYears(), sim.maxYears());
            ImGui::CloseCurrentPopup();
        }
    }
    if (ui.dateError) ImGui::TextDisabled("Date non comprise. Écris une année, ou jour/mois/année.");
    ImGui::TextDisabled("Plage : de %s à %s.", relativeToToday(sim.minYears()).c_str(), relativeToToday(sim.maxYears()).c_str());
    ImGui::EndPopup();
}

// Au-delà de 3 millions d'années : ce qui est montré, et d'où cela vient.
void deepTimeNote(const Sim& sim) {
    if (sim.deepTime()) {
        ImGui::TextDisabled("Au-delà de 3 millions d'années : seules les galaxies du Groupe local dont le mouvement est calculé sont montrées "
                            "(calcul complet de la rencontre avec Andromède, un scénario).");
        if (sim.replay)
            ImGui::TextDisabled("Dans ce calcul, la Voie lactée et Andromède fusionnent dans %s milliards d'années (énergie conservée à %s %% près).",
                                frNum(sim.replay->fusionGa(), 3).c_str(), frNum(100.0 * sim.replay->deriveEnergie(), 2).c_str());
        return;
    }
    if (std::fabs(sim.years - kStartYears) >= kLinearLimitYears * 0.999) {
        if (sim.replay) ImGui::TextDisabled("Au-delà de 3 millions d'années, les étoiles ne vont plus en ligne droite : seules les galaxies calculées restent.");
        else ImGui::TextDisabled("Limite : au-delà de 3 millions d'années, il faut le calcul de la rencontre avec Andromède, qui n'est pas chargé.");
    }
}

void drawTimeBar(Sim& sim, UiState& ui, float w, ImGuiWindowFlags fixed) {
    // Centrée, sauf si elle mordrait sur la recherche : elle se décale alors vers la droite.
    const float minX = ui.searchRight + px(ui, 12) + ui.timeW * 0.5f;
    const bool roomForAll = ui.searchRight + ui.timeW + ui.completenessW + px(ui, 48) <= w;
    const float maxX = roomForAll ? w - px(ui, 28) - ui.completenessW - ui.timeW * 0.5f : w;
    ImGui::SetNextWindowPos({std::clamp(w * 0.5f, minX, std::max(minX, maxX)), px(ui, 16)}, 0, {0.5f, 0});
    ImGui::Begin("temps", nullptr, fixed);
    ImGui::PushFont(ui.big);
    const std::string date = frDate(sim.years, kRates[sim.rate].yearsPerSecond < 0.02);
    const float rowW = px(ui, 600);
    ImGui::SetCursorPosX(std::max(px(ui, 14), (rowW - ImGui::CalcTextSize(date.c_str()).x) * 0.5f + px(ui, 14)));
    ImGui::TextUnformatted(date.c_str());
    ImGui::PopFont();
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Clic : aller à une date");
    if (ImGui::IsItemClicked()) ImGui::OpenPopup("date");
    const std::string rel = relativeToToday(sim.years) + (sim.paused ? "   •   temps arrêté" : sim.backward ? "   •   le temps recule" : "");
    ImGui::SetCursorPosX(std::max(px(ui, 14), (rowW - ImGui::CalcTextSize(rel.c_str()).x) * 0.5f + px(ui, 14)));
    ImGui::TextDisabled("%s", rel.c_str());

    if (playButton(ui, sim.paused)) sim.paused = !sim.paused;
    ImGui::SameLine();
    if (ImGui::Button(sim.backward ? "← Recule" : "Avance →")) sim.backward = !sim.backward;
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Changer le sens du temps");
    ImGui::SameLine();
    ImGui::BeginDisabled(sim.rate == 0);
    if (ImGui::Button(" − ")) sim.rate = std::max(sim.rate - 1, 0);
    ImGui::EndDisabled();
    if (ImGui::IsItemHovered(ImGuiHoveredFlags_AllowWhenDisabled)) ImGui::SetTooltip("Plus lent (Page suivante)");
    ImGui::SameLine();
    ImGui::SetNextItemWidth(px(ui, 270));
    if (ImGui::BeginCombo("##vitesse", kRates[sim.rate].label)) {
        for (int i = 0; i < kRateCount; ++i)
            if (ImGui::Selectable(kRates[i].label, i == sim.rate)) sim.rate = i;
        ImGui::EndCombo();
    }
    ImGui::SameLine();
    ImGui::BeginDisabled(sim.rate == kRateCount - 1);
    if (ImGui::Button(" + ")) sim.rate = std::min(sim.rate + 1, kRateCount - 1);
    ImGui::EndDisabled();
    if (ImGui::IsItemHovered(ImGuiHoveredFlags_AllowWhenDisabled)) ImGui::SetTooltip("Plus rapide (Page précédente)");
    ImGui::SameLine();
    if (ImGui::Button("Maintenant")) {
        sim.years = kStartYears;
        sim.backward = false;
    }
    ImGui::SameLine();
    if (ImGui::Button("Date…")) ImGui::OpenPopup("date");
    dateJumpPopup(sim, ui);
    ImGui::PushTextWrapPos(ImGui::GetCursorPosX() + rowW);      // les remarques passent à la ligne : la barre garde sa largeur
    if (!sim.spk) ImGui::TextDisabled("Planètes absentes : le fichier d'éphémérides de la NASA (de440.bsp) manque à côté du programme.");
    else if (sim.deepTime() && !sim.visible(0)) {
    }      // temps profond : le système solaire n'est plus suivi, la remarque ci-dessous le dit
    else if (!sim.ephemValid && !sim.outer) ImGui::TextDisabled("Hors de 1550-2650 (plage des éphémérides de la NASA) : calcul des planètes en préparation.");
    else if (!sim.ephemValid)
        ImGui::TextDisabled("Hors de 1550-2650 : planètes calculées ici (gravité mutuelle partie des éphémérides de la NASA) ; lunes et orbites non montrées.");
    deepTimeNote(sim);
    ImGui::PopTextWrapPos();
    ui.timeW = ImGui::GetWindowWidth();
    ui.timeBottom = ImGui::GetWindowPos().y + ImGui::GetWindowHeight();
    ImGui::End();
}

// ---------------------------------------------------------------- fiche de l'astre suivi

// Rayon : 0 dans les données veut dire « pas mesuré » (384 des 437 lunes du JPL) : ne jamais écrire « 0 km (mesuré) ».
void radiusRow(const Body& b, float s) {
    if (b.radiusKm <= 0) {
        row("Rayon", "non mesuré", "", s);
        return;
    }
    row("Rayon", (b.radiusKm >= 100 ? frInt(b.radiusKm) : frNum(b.radiusKm)) + " km", "mesuré", s);
}

void cardRows(const Sim& sim, const UiState& ui, const Camera& cam, int f) {
    const Body& fb = sim.bodies[static_cast<size_t>(f)];
    const Vec3 p = sim.position(f);
    const double dSun = std::sqrt(dot(p, p));
    const bool today = std::fabs(sim.years - kStartYears) < 1.0;
    const float s = ui.s;
    // Source de la position : éphéméride de la NASA dans sa plage, calcul ici au-delà.
    const bool computed = static_cast<size_t>(f) < sim.planetComputed.size() && sim.planetComputed[static_cast<size_t>(f)];
    const char* src = computed ? "calculé" : "éphémérides NASA";
    row("Nature", natureOf(fb), "", s);
    if (fb.kind == Kind::Planet) {
        row("Distance au Soleil", frDistance(dSun), src, s);
        for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
            if (sim.bodies[static_cast<size_t>(i)].naif == eph::kEarth && i != f) row("Distance à la Terre", frDistance(distBetween(p, sim.position(i))), src, s);
        if (fb.parent > 0)
            row(("Distance à " + sim.bodies[static_cast<size_t>(fb.parent)].name).c_str(), frDistance(distBetween(p, sim.position(fb.parent))), src, s);
        const double days = fb.periodYears * 365.25;
        row("Durée d'un tour", fb.periodYears >= 1 ? frNum(fb.periodYears) + " ans" : days >= 2 ? frNum(days) + " jours" : frNum(days * 24.0) + " heures",
            fb.parent > 0 && fb.naif != eph::kMoon ? "calculé d'après les éphémérides" : "mesuré", s);
        radiusRow(fb, s);
        if (!fb.hasPhotometry) ImGui::TextDisabled("Son éclat et sa surface ne sont pas renseignés ici : un repère marque sa place.");
        if (fb.naif == eph::kEarth) row("Lumières de nuit", "vues par satellite (NASA), grossies pour être visibles", "mesuré", s);
    } else if (fb.kind == Kind::Asteroid && sim.asteroidCat && sim.asteroidSel >= 0) {
        const size_t k = static_cast<size_t>(sim.asteroidSel);
        const asteroides::Catalogue& c = *sim.asteroidCat;
        const char* jpl = "mesuré (JPL Small-Body Database)";
        row("Distance au Soleil", frDistance(dSun), "calculé d'après son orbite", s);
        const int earth = bodyByName(sim, "Terre");
        if (earth >= 0 && sim.visible(earth)) row("Distance à la Terre", frDistance(distBetween(p, sim.position(earth))), "calculé d'après son orbite", s);
        const bool comet = c.isComet(k), open = c.eccentricity(k) >= 1.0;
        // Orbite ouverte (excentricité 1 ou plus) : pas de demi-grand axe ni de durée de tour, l'objet ne revient pas.
        if (!open) row("Orbite : demi-grand axe", frNum(c.semiMajorAxisAu(k)) + " fois la distance Terre-Soleil", jpl, s);
        row("Excentricité", frNum(c.eccentricity(k)) + (open ? " (orbite ouverte : ne revient pas)" : ""), jpl, s);
        if (!open) row("Durée d'un tour", frNum(c.periodYears(k)) + " ans", jpl, s);
        // Comètes : la dernière colonne n'est pas la magnitude H des astéroïdes ; elle n'est pas montrée tant que sa nature n'est pas confirmée.
        if (!comet) row("Magnitude absolue H", frNum(c.magnitudeH(k)), jpl, s);
        ImGui::TextDisabled("Position calculée d'après son orbite, sans l'attraction des planètes");
        if (comet) ImGui::TextDisabled("(écart avec le JPL non contrôlé pour les comètes, que le dégazage fait aussi dévier).");
        else ImGui::TextDisabled("(moins de 100 000 km d'écart avec le JPL après 154 jours).");
    } else if (fb.kind == Kind::Probe) {
        const char* traj = sim.years <= kStartYears ? "mesuré : trajectoire reconstruite par le JPL" : "calculé : trajectoire prévue par le JPL";
        row("Distance au Soleil", frDistance(dSun), traj, s);
        const int earth = bodyByName(sim, "Terre");
        if (earth >= 0 && sim.visible(earth)) row("Distance à la Terre", frDistance(distBetween(p, sim.position(earth))), traj, s);
        if (sim.probes && fb.probe >= 0 && static_cast<size_t>(fb.probe) < sim.probes->size()) {
            const sondes::Probe& pr = (*sim.probes)[static_cast<size_t>(fb.probe)];
            row("Position connue", "du " + frDate((pr.firstJd() - 2451545.0) / 365.25) + " au " + frDate((pr.lastJd() - 2451545.0) / 365.25), "", s);
        }
    } else if (fb.kind == Kind::Star) {
        // Aujourd'hui la distance est une mesure ; à une autre date, c'est la mesure prolongée en ligne droite.
        row("Distance au Soleil", frDistance(dSun), today ? "mesuré" : "calculé : mouvement mesuré, prolongé en ligne droite", s);
        row("Éclat vu de la Terre", "magnitude " + frNum(sim.apparentMag(f, {0, 0, 0})), "calculé", s);
        row("Vitesse", frNum(sim.speedKms(f)) + " km/s par rapport au Soleil", "mesuré", s);
    } else if (fb.kind == Kind::Galaxy) {
        // En temps profond, la place vient du calcul de la rencontre avec Andromède (sauf le centre de la Voie lactée, origine du repère).
        const bool deepCalc = sim.deepTime() && fb.name != "Centre de la Voie lactée";
        row(sim.deepTime() ? "Distance à la place actuelle du Soleil" : "Distance au Soleil", frDistance(dSun), deepCalc ? "calculé" : "mesuré", s);
        ImGui::TextDisabled("Sa forme et sa photo ne sont pas encore dessinées ici.");
    } else {
        radiusRow(fb, s);
    }
    if (fb.kind == Kind::Sun || fb.kind == Kind::Star)
        row("Température", frInt(4600.0 * (1.0 / (0.92 * fb.bv + 1.7) + 1.0 / (0.92 * fb.bv + 0.62))) + " K en surface", "calculé d'après la couleur", s);
    if (fb.kind != Kind::Galaxy && fb.kind != Kind::Probe && fb.kind != Kind::Asteroid && (fb.kind != Kind::Planet || fb.hasPhotometry)) row("Vue d'ici", "magnitude " + frNum(sim.apparentMag(f, cam.pos)), "calculé", s);
    ImGui::Separator();
    if (fb.kind == Kind::Planet && computed) ImGui::TextDisabled("Position : calculée ici (gravité mutuelle, partie des éphémérides JPL DE440 de la NASA).");
    else if (fb.kind == Kind::Planet && fb.parent > 0 && fb.naif != eph::kMoon)      // lunes des autres planètes : fichiers de satellites du JPL
        ImGui::TextDisabled("Position : éphémérides des satellites du JPL (NASA), lues telles quelles.");
    else if (fb.kind == Kind::Planet) ImGui::TextDisabled("Position : éphémérides JPL DE440 de la NASA, lues telles quelles.");
    else if (fb.kind == Kind::Probe) ImGui::TextDisabled("Source : trajectoire JPL Horizons (NASA).");
    else if (fb.kind == Kind::Asteroid) ImGui::TextDisabled("Source : JPL Small-Body Database (NASA).");
    else if (fb.kind == Kind::Galaxy && sim.deepTime() && fb.name != "Centre de la Voie lactée")
        ImGui::TextDisabled("Position : calcul complet de la rencontre avec Andromède (scénario), parti des mesures de McConnachie 2012.");
    else if (fb.kind == Kind::Galaxy) ImGui::TextDisabled("Sources : Karachentsev et al. 2013 ; McConnachie 2012.");
    else ImGui::TextDisabled("Sources : catalogues Hipparcos (HYG) et Gaia DR3.");
}

void drawCard(Sim& sim, UiState& ui, const Camera& cam, float w, ImGuiWindowFlags fixed) {
    const int f = sim.focus;
    if (ui.cardClosedFor == f) return;
    ui.cardClosedFor = -1;
    ImGui::SetNextWindowPos({w - px(ui, 16), std::max({px(ui, 150), ui.timeBottom + px(ui, 12), ui.completenessBottom + px(ui, 12)})}, 0, {1, 0});      // sous la barre du temps : les deux ne se recouvrent jamais
    ImGui::Begin("fiche", nullptr, fixed);
    ImGui::PushFont(ui.big);
    ImGui::TextUnformatted(sim.bodies[static_cast<size_t>(f)].name.c_str());
    ImGui::PopFont();
    // Bouton de fermeture juste après le nom (une position calée sur le bord droit ferait grandir la fiche sans fin).
    ImGui::SameLine(0, px(ui, 24));
    if (ImGui::SmallButton(" × ")) ui.cardClosedFor = f;
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Fermer la fiche");
    ImGui::Separator();
    cardRows(sim, ui, cam, f);
    const bool isFar = sim.dist > 1.5 * sim.arriveDist(f, 1e300) && !sim.flying;
    if (isFar && ImGui::Button("S'en approcher")) goToBody(sim, ui, f);
    if (isFar) ImGui::SameLine();
    if (!sim.history.empty() && ImGui::Button("← Retour")) {
        ui.tour = -1;
        sim.back();
    }
    if (!sim.history.empty()) ImGui::SameLine();
    const uint32_t naifF = static_cast<uint32_t>(sim.bodies[static_cast<size_t>(f)].naif);
    if ((naifF == eph::kEarth || naifF == eph::kMoon) && sim.bodies[static_cast<size_t>(f)].kind == Kind::Planet) {
        const int next = nextEclipse(sim.years);
        if (next >= 0 && ImGui::Button("Prochaine éclipse de Soleil")) showEclipse(sim, ui, next);
        if (next >= 0 && ImGui::IsItemHovered()) ImGui::SetTooltip("%s", kEclipses[next].label);
        if (next >= 0) ImGui::SameLine();
    }
    if (f != 0 && sim.visible(0) && ImGui::Button("Revenir au Soleil")) goToBody(sim, ui, 0, 45.0 * kAuInLy);
    ImGui::End();
}

}  // namespace
