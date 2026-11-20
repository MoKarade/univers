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

// (b) Scénarios du Groupe local (clones.h, fil physique) : part qui fusionne et date (16e, 50e, 84e centiles).
void cloneNote(const Sim& sim) {
    if (!sim.cloneCount || sim.cloneMergeProbability <= 0) return;
    ImGui::TextDisabled("Sur %s scénarios tirés de l'incertitude des mesures : %s %% de chances que la Voie lactée et Andromède fusionnent, "
                        "entre %s et %s milliards d'années (valeur centrale %s) [calculé].",
                        frInt(static_cast<double>(sim.cloneCount)).c_str(), frInt(100.0 * sim.cloneMergeProbability).c_str(),
                        frNum(sim.cloneMergeGa[0], 2).c_str(), frNum(sim.cloneMergeGa[2], 2).c_str(), frNum(sim.cloneMergeGa[1], 2).c_str());
}

// Loin d'aujourd'hui : ce qui est montré, et d'où cela vient (fil natif, 87c910e : orbites des étoiles jusqu'à 1 milliard
// d'années, puis fondu vers le calcul de la fusion entre 800 millions et 1 milliard d'années, Sim::starShare).
// Hors d'aujourd'hui, ce qui est supposé dans le mouvement des étoiles Gaia (texte du fil Gaia, PR #77).
void gaiaMotionNote(const Sim& sim) {
    if (std::fabs(sim.years - kStartYears) < 1.0) return;
    if (sim.hasGaia && sim.gaiaCount > completude::kGaiaVitessesRadiales && sim.starShare() > 0)
        ImGui::TextDisabled("%s millions d'étoiles Gaia n'ont pas de vitesse mesurée le long de la ligne de visée : pour leur mouvement dans le temps, "
                            "elle est comptée nulle (supposition). Leur position d'aujourd'hui reste mesurée.",
                            frInt((static_cast<double>(sim.gaiaCount) - completude::kGaiaVitessesRadiales) / 1.0e6).c_str());
    if (sim.hasGaiaAggregate) {
        ImGui::TextDisabled("Lumière additionnée des autres sources Gaia : chaque case avance à la vitesse moyenne mesurée de ses étoiles, "
                            "sur son orbite calculée autour de la Galaxie.");
        if (sim.gaiaCellDispersionKms > 0)
            ImGui::TextDisabled("Dans une case, les étoiles ne vont pas toutes à cette vitesse : elles s'en écartent d'environ %s km/s (valeur typique mesurée). "
                                "Avec le temps, une vraie case s'étalerait ; ici elle reste groupée.",
                                frInt(sim.gaiaCellDispersionKms).c_str());
        ImGui::TextDisabled("La part sans distance mesurée (vue seulement comme un ciel) n'est montrée qu'au présent.");
    }
}

// Au-delà de la table des orbites (10 millions d'années) : ce que le calcul du chaos du fil physique dit de la Terre.
void chaosNote(const Sim& sim) {
    const double after = sim.years - chaos::kStartYears;
    if (!sim.chaosRun.ready() || after < 1.0e7) return;
    double e = 0, w = 0, spread = 0;
    if (!sim.chaosRun.orbit(after, e, w, spread)) {
        ImGui::TextDisabled("Terre : même son orbite est inconnue au-delà d'environ 60 millions d'années (chaos du système solaire, mesuré par 32 copies).");
        return;
    }
    const std::string ecc = frNum(e, 3), deg = frInt(spread * 180.0 / kPi);
    if (after <= chaos::kPositionHorizonYears)
        ImGui::TextDisabled("Terre : orbite calculée ici (excentricité %s, trait orange) ; sa place sur l'orbite n'est pas gardée par le calcul ; "
                            "écart entre 32 copies parties à 15 m près : %s°.", ecc.c_str(), deg.c_str());
    else
        ImGui::TextDisabled("Terre : orbite encore calculable (excentricité %s) ; sa place sur l'orbite est inconnue au-delà de 45 millions "
                            "d'années : 32 copies parties à 15 m près s'écartent de %s° (chaos, mesuré).", ecc.c_str(), deg.c_str());
    ImGui::TextDisabled("Orbite tracée dans le plan de l'écliptique : son inclinaison de quelques degrés n'est pas gardée par le calcul.");
}

void deepTimeNote(const Sim& sim) {
    gaiaMotionNote(sim);
    if (!sim.deepTime()) return;
    if (sim.starShare() > 0) {
        // 345c11d : orbite exacte (intégrée pas à pas sur la carte graphique) pour le catalogue principal ; Gaia en épicycles
        // tant que le fil Gaia n'a pas basculé. Limite mesurée par le fil physique : le modèle de la Galaxie (±2,5 % sur la
        // rotation, soit 1,6 kpc et 10 degrés d'écart à 100 millions d'années).
        ImGui::TextDisabled("Étoiles du catalogue principal : position de départ mesurée, orbite exacte calculée dans un potentiel de la Galaxie [modèle].");
        if (sim.hasGaia) ImGui::TextDisabled("Étoiles Gaia : départ mesuré, orbite approchée (épicycles) dans le même potentiel.");
        ImGui::TextDisabled("Au-delà d'environ 100 millions d'années, la limite est ce modèle de la Galaxie : ±2,5 %% sur la rotation, "
                            "soit environ 5 000 années-lumière et 10 degrés d'écart à 100 millions d'années.");
        if (sim.yearsPerSecond() < 1.0e7 && !sim.paused)
            ImGui::TextDisabled("Un tour de la Galaxie prend environ 230 millions d'années : à cette vitesse, la rotation est réelle mais invisible.");
    }
    if (sim.starShare() < 1 && sim.years < kStartYears)
        ImGui::TextDisabled("Passé : les étoiles mesurées s'effacent entre %s et %s millions d'années avant aujourd'hui. Au-delà, rien n'est calculé : "
                            "l'écran est vide.", frNum(kOrbitFadeYears / 1.0e6, 0).c_str(), frNum(kOrbitLimitYears / 1.0e6, 0).c_str());
    if (sim.starShare() < 1 && sim.years >= kStartYears) {
        ImGui::TextDisabled("Entre %s et %s milliards d'années, les étoiles mesurées s'effacent et les points du calcul de la rencontre avec "
                            "Andromède (un scénario) les remplacent : ce ne sont pas les mêmes étoiles.",
                            frNum(sim.starEraFadeYears / 1.0e9, 2).c_str(), frNum(sim.starEraEndYears / 1.0e9, 2).c_str());
        if (sim.replay)
            ImGui::TextDisabled("Dans ce calcul, la Voie lactée et Andromède fusionnent dans %s milliards d'années (énergie conservée à %s %% près).",
                                frNum(sim.replay->fusionGa(), 3).c_str(), frNum(100.0 * sim.replay->deriveEnergie(), 2).c_str());
        else ImGui::TextDisabled("Ce calcul n'est pas chargé.");
        cloneNote(sim);
    }
}

// Planètes : montrées seulement si au moins une a une position à la date affichée.
bool anyPlanetShown(const Sim& sim) {
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
        if (sim.bodies[static_cast<size_t>(i)].kind == Kind::Planet && sim.bodies[static_cast<size_t>(i)].parent == 0 && sim.visible(i)) return true;
    return false;
}

// Vitesse du temps en mots : « 37 millions d'années par seconde », « 2,5 jours par seconde », « temps réel »…
std::string rateText(double yearsPerSecond) {
    const double s = yearsPerSecond * kYearSeconds;      // secondes de temps simulé par seconde
    if (std::fabs(s - 1.0) < 0.05) return "Temps réel";
    struct Unit { double years; const char* one; const char* many; };
    static const Unit units[] = {{1.0e9, "milliard d'années", "milliards d'années"}, {1.0e6, "million d'années", "millions d'années"},
                                 {1.0e3, "millier d'années", "milliers d'années"},   {1.0, "an", "ans"},
                                 {1.0 / 365.25, "jour", "jours"},                    {1.0 / 8766.0, "heure", "heures"},
                                 {1.0 / 525960.0, "minute", "minutes"},              {1.0 / kYearSeconds, "seconde", "secondes"}};
    for (const Unit& u : units)
        if (yearsPerSecond >= u.years * 0.9999 || &u == &units[7]) {
            const double v = yearsPerSecond / u.years;
            const int digits = v < 10 ? 2 : v < 100 ? 1 : 0;
            return frNum(v, digits) + " " + (v < 2 ? u.one : u.many) + " par seconde";
        }
    return "";
}

void drawTimeBar(Sim& sim, UiState& ui, float w, ImGuiWindowFlags fixed) {
    // Centrée, sauf si elle mordrait sur la recherche : elle se décale alors vers la droite.
    const float minX = ui.searchRight + px(ui, 12) + ui.timeW * 0.5f;
    const bool roomForAll = ui.searchRight + ui.timeW + ui.completenessW + px(ui, 48) <= w;
    const float maxX = roomForAll ? w - px(ui, 28) - ui.completenessW - ui.timeW * 0.5f : w;
    ImGui::SetNextWindowPos({std::clamp(w * 0.5f, minX, std::max(minX, maxX)), px(ui, 16)}, 0, {0.5f, 0});
    ImGui::Begin("temps", nullptr, fixed);
    ImGui::PushFont(ui.big);
    const std::string date = frDate(sim.years, sim.yearsPerSecond() < 0.02);
    const float rowW = ui.details ? px(ui, 600) : std::max(px(ui, 360), ImGui::CalcTextSize(frDate(sim.years, sim.yearsPerSecond() < 0.02).c_str()).x * 1.25f);
    ImGui::SetCursorPosX(std::max(px(ui, 14), (rowW - ImGui::CalcTextSize(date.c_str()).x) * 0.5f + px(ui, 14)));
    ImGui::TextUnformatted(date.c_str());
    ImGui::PopFont();
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Clic : aller à une date");
    if (ImGui::IsItemClicked()) ImGui::OpenPopup("date");
    const std::string rel = relativeToToday(sim.years) + (sim.paused ? "   •   temps arrêté" : sim.backward ? "   •   le temps recule" : "");
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("%s\nClic : aller à une date", rel.c_str());
    if (ui.details) {
        ImGui::SetCursorPosX(std::max(px(ui, 14), (rowW - ImGui::CalcTextSize(rel.c_str()).x) * 0.5f + px(ui, 14)));
        ImGui::TextDisabled("%s", rel.c_str());
    }

    // Interface minimaliste (Marc, 13/11/2026) : lecture, vitesse et « … » (sens, plus lent, plus rapide, maintenant, date).
    ImGui::SetCursorPosX(std::max(px(ui, 14), (rowW - px(ui, 330)) * 0.5f + px(ui, 14)));
    if (playButton(ui, sim.paused)) sim.paused = !sim.paused;
    ImGui::SameLine();
    ImGui::SetNextItemWidth(px(ui, 240));
    const std::string rateNow = sim.speed > 0 ? rateText(sim.speed) : std::string(kRates[sim.rate].label);
    if (ImGui::BeginCombo("##vitesse", rateNow.c_str())) {
        for (int i = 0; i < kRateCount; ++i)
            if (ImGui::Selectable(kRates[i].label, sim.speed <= 0 && i == sim.rate)) {
                sim.rate = i;
                sim.speed = 0;
            }
        ImGui::EndCombo();
    }
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Vitesse du temps (Page précédente : plus vite, Page suivante : plus lent)");
    ImGui::SameLine();
    if (ImGui::Button(" … ")) ImGui::OpenPopup("temps-plus");
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Sens du temps, maintenant, aller à une date");
    if (ImGui::BeginPopup("temps-plus")) {
        if (ImGui::MenuItem(sim.backward ? "Faire avancer le temps" : "Faire reculer le temps")) sim.backward = !sim.backward;
        if (ImGui::MenuItem("Plus lent", "Page suivante", false, sim.yearsPerSecond() > kRates[0].yearsPerSecond * 1.0001)) sim.stepRate(-1);
        if (ImGui::MenuItem("Plus rapide", "Page précédente", false, sim.yearsPerSecond() < Sim::kMaxYearsPerSecond * 0.9999)) sim.stepRate(+1);
        if (ImGui::MenuItem("Maintenant")) {
            sim.years = kStartYears;
            sim.backward = false;
        }
        if (ImGui::MenuItem("Aller à une date…")) ui.openDate = true;
        ImGui::EndPopup();
    }
    if (ui.openDate) {
        ImGui::OpenPopup("date");
        ui.openDate = false;
    }
    // Curseur de vitesse, libre (Marc, 18/11/2026) : échelle logarithmique, du temps réel à 1 milliard d'années par seconde.
    // Le résultat ne dépend pas de la vitesse : à une date donnée, l'image est la même (fenetre.cpp, film_carte.h).
    {
        const float lo = static_cast<float>(std::log10(kRates[0].yearsPerSecond)), hi = static_cast<float>(std::log10(Sim::kMaxYearsPerSecond));
        float lg = static_cast<float>(std::log10(sim.yearsPerSecond()));
        const std::string label = rateText(sim.yearsPerSecond());
        ImGui::SetCursorPosX(px(ui, 14));
        ImGui::SetNextItemWidth(rowW);
        if (ImGui::SliderFloat("##curseur-vitesse", &lg, lo, hi, label.c_str(), ImGuiSliderFlags_NoRoundToFormat | ImGuiSliderFlags_AlwaysClamp))
            sim.speed = std::clamp(std::pow(10.0, static_cast<double>(lg)), kRates[0].yearsPerSecond, Sim::kMaxYearsPerSecond);
        if (ImGui::IsItemHovered()) ImGui::SetTooltip("Vitesse du temps, au choix : glisser (Ctrl + clic pour taper une valeur)");
    }
    dateJumpPopup(sim, ui);
    ImGui::PushTextWrapPos(ImGui::GetCursorPosX() + rowW);      // les remarques passent à la ligne : la barre garde sa largeur
    if (!sim.spk) ImGui::TextDisabled("Planètes absentes : le fichier d'éphémérides de la NASA (de440.bsp) manque à côté du programme.");
    // Ce qui ne vaut qu'à une autre date qu'aujourd'hui : rangé sous un titre qui se déplie (la barre restait sinon
    // haute de sept paragraphes en temps profond). Seul ce qui est en cours reste toujours visible.
    if (sim.filmEdgeYears != 0) {
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(1.0f, 0.77f, 0.43f, 1.0f));
        ImGui::TextUnformatted(("Fin du film calculé : " + frDate(sim.filmEdgeYears) + ". Le grand calcul continue ; la date ira plus loin à mesure qu'il avance.").c_str());
        ImGui::PopStyleColor();
    } else if (sim.timeHeld) {
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(1.0f, 0.77f, 0.43f, 1.0f));
        ImGui::TextUnformatted(("Calcul exact en cours : date demandée " + frDate(sim.yearsGoal) + " ; la date montrée avance au rythme du calcul.").c_str());
        ImGui::PopStyleColor();
    } else if (sim.orbitLagSteps > 0) {
        ImGui::TextDisabled("Calcul exact des orbites en cours : encore %s millions d'années à parcourir.", frInt(static_cast<double>(sim.orbitLagSteps)).c_str());
    }
    if (ui.openNotes) ImGui::SetNextItemOpen(true, ImGuiCond_Always);
    if (std::fabs(sim.years - kStartYears) >= 1.0 && ImGui::CollapsingHeader("Ce qui est mesuré, calculé ou supposé à cette date")) {
        if (!sim.ephemValid && sim.outer && !anyPlanetShown(sim)) {
            ImGui::TextDisabled("Planètes non montrées à cette date : leur calcul couvre 10 millions d'années avant et après aujourd'hui.");
            chaosNote(sim);
        }
        else if (!sim.ephemValid && !sim.outer) ImGui::TextDisabled("Hors de 1550-2650 (plage des éphémérides de la NASA) : calcul des planètes en préparation.");
        else if (!sim.ephemValid)
            ImGui::TextDisabled("Hors de 1550-2650 : planètes calculées ici (gravité mutuelle partie des éphémérides de la NASA) ; lunes et orbites non montrées.");
        else ImGui::TextDisabled("Planètes, Lune et lunes : éphémérides de la NASA, lues telles quelles.");
        deepTimeNote(sim);
    }
    ImGui::PopTextWrapPos();
    ui.timeW = ImGui::GetWindowWidth();
    ui.timeRight = ImGui::GetWindowPos().x + ImGui::GetWindowWidth();
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
        // Source : orbite à jour de JPL Horizons pour une comète, JPL Small-Body Database pour un astéroïde (fil du rendu).
        const char* jpl = c.isComet(k) ? "mesuré (orbite à jour de JPL Horizons)" : "mesuré (JPL Small-Body Database)";
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
        if (comet) ImGui::TextDisabled("(moins de 150 000 km d'écart avec le JPL après 157 jours).");
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
        row("Distance au Soleil", frDistance(dSun), today ? "mesuré" : "calculé : départ mesuré, orbite calculée autour de la Galaxie", s);
        row("Éclat vu de la Terre", "magnitude " + frNum(sim.apparentMag(f, {0, 0, 0})), "calculé", s);
        if (fb.radiusKm > 0)      // audit E3 : rayon tiré de l'éclat et de la couleur (rayon_etoile.h), pas mesuré
            row("Rayon", frNum(fb.radiusKm / rayon_etoile::kRsoleilKm, fb.radiusKm > 1.0e7 ? 0 : 2) + " fois le Soleil",
                "calculé, approché (éclat et couleur, loi de Stefan-Boltzmann)", s);
        row(today ? "Vitesse" : "Vitesse aujourd'hui", frNum(sim.speedKms(f)) + " km/s par rapport au Soleil", "mesuré", s);
        if (!fb.planetLines.empty()) {
            ImGui::TextUnformatted("Planètes connues (NASA Exoplanet Archive, valeurs mesurées) :");
            for (const std::string& l : fb.planetLines) ImGui::BulletText("%s", l.c_str());
            ImGui::TextDisabled("Dessin : orbites mesurées ; inclinaison inconnue -> 60°, orientation sur le ciel inconnue (supposées) ; points = repères, pas leur lumière.");
        }
    } else if (fb.kind == Kind::Galaxy) {
        // En temps profond, la place vient du calcul de la rencontre avec Andromède (sauf le centre de la Voie lactée, origine du repère).
        // audit D1 : loin d'aujourd'hui, c'est la distance au Soleil de la date montrée, et la place du Soleil est calculée.
        if (fb.structure && fb.name == "Univers observable")      // sphère centrée sur nous : son rayon, pas une distance au Soleil
            row("Rayon aujourd'hui", "46,2 milliards d'années-lumière", "calculé (Planck 2018)", s);
        else
        row(sim.deepTime() ? "Distance au Soleil à cette date" : "Distance au Soleil", frDistance(dSun), sim.deepTime() ? "calculé" : fb.structure ? "publié, catalogue cité" : "mesuré", s);
        if (!fb.blackHoleText.empty()) row("Trou noir central", fb.blackHoleText, "mesuré", s);
        if (!fb.shapeNote.empty()) ImGui::TextWrapped("%s", fb.shapeNote.c_str());
        else if (!fb.structure) ImGui::TextDisabled("Sa forme et sa photo ne sont pas encore dessinées ici.");
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
    else if (fb.kind == Kind::Asteroid && sim.asteroidCat && sim.asteroidSel >= 0 && sim.asteroidCat->isComet(static_cast<size_t>(sim.asteroidSel)))
        ImGui::TextDisabled("Source : orbite à jour de JPL Horizons (NASA).");
    else if (fb.kind == Kind::Asteroid) ImGui::TextDisabled("Source : JPL Small-Body Database (NASA).");
    else if (fb.kind == Kind::Galaxy && sim.deepTime() && fb.name != "Centre de la Voie lactée")
        ImGui::TextDisabled("Position : calcul complet de la rencontre avec Andromède (scénario), parti des mesures de McConnachie 2012.");
    else if (fb.kind == Kind::Galaxy && fb.structure) ImGui::TextDisabled("Sources : voir la description (place publiée, ramenée en années-lumière avec h = 0,674).");
    else if (fb.kind == Kind::Galaxy && fb.priority >= 9) ImGui::TextDisabled("Sources : Cosmicflows-4 (Tully et al. 2023, distances) ; OpenNGC (noms).");
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
