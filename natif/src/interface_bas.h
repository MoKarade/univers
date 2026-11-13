// Appli PC « Univers » : bas de l'écran, accueil, visite guidée, aide et complétude (partie de l'interface, voir interface.h).
#pragma once
#include "interface_base.h"
#include "interface_temps.h"

namespace {

// ---------------------------------------------------------------- bas de l'écran

// Un à un ou en somme (demande de Marc, 12/11 : « quand on augmente les distances on généralise au fur et à mesure ») :
// de près chaque point est un objet mesuré ; en s'éloignant, chaque pixel additionne la lumière de plus en plus d'étoiles
// mesurées (éclat par pixel constant au-delà de 300 al, simulation.h). La vue lointaine est leur somme, jamais un modèle.
const char* grainLine(const Sim& sim) {
    if (sim.starShare() <= 0) return nullptr;      // seul le calcul de la fusion est montré : voir la ligne suivante
    if (sim.dist < 0.05) {
        if (sim.asteroidCount && sim.asteroidGain(sim.asteroidEpochJd) > 0 && sim.dist > 8.0 * kAuInLy)
            return "Ici, planètes et lunes sont montrées une par une ; les astéroïdes s'additionnent par pixel.";
        return "Ici, chaque point ou disque est un astre mesuré, un par un.";
    }
    if (sim.dist < 300.0) return "Ici, chaque point est une étoile mesurée, une par une.";
    if (sim.dist < 6.0e5)
        return "Ici, chaque pixel additionne la lumière d'étoiles mesurées, de plus en plus nombreuses en s'éloignant : c'est leur somme, rien n'est ajouté.";
    return "Ici, chaque point lointain est une galaxie mesurée, une par une.";
}

// Les rayons autour du Soleil, vus de loin (fil Gaia, mesure du 12/11/2026, docs/gaia-rayons.md) : Gaia ne mesure pas aussi
// loin dans toutes les directions. Une ligne courte ; le survol explique.
void raysNote(const Sim& sim) {
    if (sim.bestLook && sim.gaiaRebalancedCount)
        ImGui::TextDisabled("Meilleur rendu : étoiles Gaia floutées de 3° et éclat rééquilibré d'une direction à l'autre (%s de la lumière) : hypothèses (survol).",
                            (frNum(100.0 * sim.gaiaRebalancedShift, 2) + " %").c_str());
    else
        ImGui::TextDisabled("Rayons autour du Soleil : là où Gaia voit loin ou non (poussière, balayage), pas une vraie structure (survol : pourquoi).");
    if (!ImGui::IsItemHovered()) return;
    ImGui::BeginTooltip();
    ImGui::PushTextWrapPos(ImGui::GetFontSize() * 32.0f);
    ImGui::TextUnformatted("Pourquoi des rayons autour du Soleil ?");
    ImGui::Separator();
    ImGui::TextWrapped("%s", "On ne voit ici que les étoiles dont Gaia a mesuré la distance depuis la Terre. Selon la direction, Gaia en mesure "
                       "plus ou moins loin : la poussière proche cache les étoiles faibles, et le satellite n'a pas regardé toutes les "
                       "parties du ciel le même nombre de fois. Vu de loin, ces différences dessinent des rayons qui partent du Soleil. "
                       "Ce n'est ni le flou des distances ni une vraie structure (mesuré : un tri plus strict ne les change pas).");
    if (sim.gaiaRebalancedCount)
        ImGui::TextWrapped("En vue « meilleur rendu » (bouton Vue, touche F4), l'éclat de %s étoiles est rééquilibré vu de loin : chaque morceau "
                           "de ciel, à une distance donnée, est ramené à la moyenne de ses voisins sur 15°. HYPOTHÈSE : à même distance, le "
                           "nombre d'étoiles varie lentement d'une direction à l'autre. Chaque étoile est aussi dessinée décalée d'un petit angle "
                           "au hasard (3° en moyenne, autant que l'incertitude de sa distance, 5 %). Aucune étoile n'est ajoutée ; vu du "
                           "Soleil, le ciel reste celui mesuré. En vue « 100 % mesuré », rien n'est corrigé.",
                           frInt(static_cast<double>(sim.gaiaRebalancedCount)).c_str());
    ImGui::TextDisabled("Source : Gaia DR3 (Gaia Collaboration 2023).");
    ImGui::PopTextWrapPos();
    ImGui::EndTooltip();
}

void armLegend(const Sim& sim);      // interface_bras.h

void whatYouSee(const Sim& sim) {
    if (const char* grain = grainLine(sim)) ImGui::TextUnformatted(grain);
    const double boost = sim.brightnessBoost();
    if (boost > 1.5 && sim.dist < 1.0e5) ImGui::TextDisabled("Éclat des étoiles multiplié par %s pour qu'elles restent visibles de si loin.", frNum(boost, 2).c_str());
    if (sim.asteroidCount && sim.asteroidGain(sim.asteroidEpochJd) > 0 && sim.dist < 0.05)
        ImGui::TextDisabled("Les petits points sont %s astéroïdes, chacun sur son orbite mesurée (JPL), grossis pour être visibles%s",
                            frInt(static_cast<double>(sim.asteroidCount)).c_str(), sim.dist <= 8.0 * kAuInLy ? " ; clic sur l'un d'eux : sa fiche." : ".");
    if (sim.replay && sim.starShare() < 1)
        ImGui::TextDisabled(sim.starShare() > 0 ? "Les points qui apparaissent sont les étoiles-tests du calcul complet de la rencontre avec Andromède (un scénario, pas une mesure)."
                                                : "Les points sont les étoiles-tests du calcul complet de la rencontre avec Andromède (un scénario, pas une mesure).");
    if (sim.starShare() <= 0) return;
    // Voie lactée en volume (fil Gaia, docs/gaia-voie-lactee.md) : un modèle, dit comme tel dès qu'on la voit de loin.
    // Choix de Marc (13/11) : la Galaxie entière dès aujourd'hui en vue réaliste ; en « 100 % mesuré », seulement les étoiles mesurées.
    if (sim.hasMilkyWay && sim.milkyWayModelShare > 0 && sim.dist > 3000.0) {
        ImGui::TextDisabled("Voie lactée : étoiles Gaia mesurées une à une près du Soleil ; au-delà (pas de distance mesurée), lueur d'un modèle ajusté sur des mesures.");
        ImGui::TextDisabled("Supposés dans ce modèle : partage de la lumière au prorata des masses, lumière ajoutée par les bras, largeur de la barre longue.");
    } else if (sim.dist > 3000.0) {
        // gaia_agrege.bin (fil Gaia, docs/gaia-voie-lactee.md) : la lumière des autres sources Gaia, additionnée par case.
        if (sim.hasGaia && sim.gaiaCount) {
            if (sim.hasGaiaAggregate && std::fabs(sim.years - kStartYears) >= 1.0) {      // la lumière additionnée suit aussi les orbites (9f77e33)
                // Orbite fiable (fil Gaia, docs/gaia-rayons.md) : seules ces étoiles avancent ; les autres s'effacent en quelques Ma.
                if (sim.gaiaReliableCount) {
                    ImGui::TextDisabled("Voie lactée : %s étoiles Gaia à orbite fiable (vitesse mesurée, %s de la lumière), sur leur orbite ;",
                                        frInt(static_cast<double>(sim.gaiaReliableCount)).c_str(), (frNum(100.0 * sim.gaiaReliableLight, 2) + " %").c_str());
                    ImGui::TextDisabled("les autres sources Gaia, sans vitesse sûre, ne sont montrées qu'autour d'aujourd'hui : elles s'effacent en quelques millions d'années.");
                } else {
                    ImGui::TextDisabled("Voie lactée : %s étoiles mesurées par Gaia, une par une, sur leur orbite ;", frInt(static_cast<double>(sim.gaiaCount)).c_str());
                    ImGui::TextDisabled("le reste des sources Gaia, additionné par cases, avance à la vitesse moyenne de chaque case.");
                }
            } else if (sim.hasGaiaAggregate) {
                ImGui::TextDisabled("Voie lactée : %s étoiles mesurées par Gaia, une par une ; le reste des sources Gaia est additionné par pixel, sans modèle.",
                                    frInt(static_cast<double>(sim.gaiaCount)).c_str());
            } else {
                ImGui::TextDisabled("Voie lactée : seules les %s étoiles mesurées par Gaia sont montrées ; la lumière des autres sources Gaia n'est pas chargée.",
                                    frInt(static_cast<double>(sim.gaiaCount)).c_str());
            }
            // Rayons : visibles avec les seules étoiles une à une aussi (captures du 12/11/2026, docs/gaia-rayons.md).
            if (!sim.deepTime()) raysNote(sim);
        } else {
            ImGui::TextDisabled("Voie lactée : seules ses étoiles mesurées près du Soleil sont montrées ; sa lumière d'ensemble n'est pas dessinée,");
            ImGui::TextDisabled("car elle demanderait un modèle.");
        }
    }
    if (sim.galaxyGain() > 0.005) {
        ImGui::TextDisabled("Chaque point lointain est une galaxie ou un quasar, placé d'après son décalage vers le rouge mesuré");
        ImGui::TextDisabled("(relevés 2MRS, 6dF, 2dF, SDSS, DESI). Son éclat n'est pas mesuré ici : le point a une taille fixe,");
        ImGui::TextDisabled("qui s'efface avec la distance pour garder l'image lisible (réglage d'affichage, pas une mesure).");
    }
}

void drawStatus(const Sim& sim, const UiState& ui, float h, ImGuiWindowFlags fixed) {
    ImGui::SetNextWindowPos({px(ui, 16), h - px(ui, 16)}, 0, {0, 1});
    ImGui::Begin("aide", nullptr, fixed);
    const Body& fb = sim.bodies[static_cast<size_t>(sim.focus)];
    const std::string where = sim.flying ? "En route vers « " + fb.name + " »…" : "Tu regardes « " + fb.name + " » depuis " + frDistance(sim.dist) + ".";
    ImGui::TextUnformatted(where.c_str());
    if (const int k = eclipseNow(sim.years); k >= 0) ImGui::TextDisabled("%s, de Soleil : %s.", kEclipses[k].label, kEclipseStatus);
    if (!ui.details) {      // interface minimaliste : seules les hypothèses du « meilleur rendu » restent toujours écrites
        if (sim.bestLook && !sim.deepTime()) raysNote(sim);
        ImGui::End();
        return;
    }
    whatYouSee(sim);
    armLegend(sim);
    ImGui::TextDisabled("Clic sur un astre : y aller   •   Molette : zoomer   •   Glisser : tourner   •   Tape un nom : chercher   •   F1 : aide");
    ImGui::End();
}

// En bas à droite, quand on regarde l'univers lointain : les réglages de l'expansion, recalculés en direct.
void drawCosmology(Sim& sim, const UiState& ui, float w, float h, ImGuiWindowFlags fixed) {
    if (sim.dist <= 2.0e6) return;
    cosmo::Params& c = sim.cosmology;
    float h0 = static_cast<float>(c.h0), om = static_cast<float>(c.om), ode = static_cast<float>(c.ode), w0 = static_cast<float>(c.w0), wa = static_cast<float>(c.wa);
    ImGui::SetNextWindowPos({w - px(ui, 16), h - px(ui, 16)}, 0, {1, 1});
    ImGui::Begin("cosmologie", nullptr, fixed);
    const double ok = c.omegaK();
    if (!ImGui::CollapsingHeader("L'univers en expansion : réglages")) {
        ImGui::TextDisabled("Âge de l'univers : %s milliards d'années (calculé).", frNum(cosmo::ageGyr(c), 4).c_str());
        ImGui::End();
        return;
    }
    ImGui::PushItemWidth(px(ui, 240));
    bool changed = false;
    changed |= ImGui::SliderFloat("Vitesse d'expansion (km/s par Mpc)", &h0, 60.0f, 80.0f, "%.1f");
    changed |= ImGui::SliderFloat("Part de matière", &om, 0.05f, 0.60f, "%.3f");
    changed |= ImGui::SliderFloat("Part d'énergie noire", &ode, 0.30f, 0.95f, "%.3f");
    changed |= ImGui::SliderFloat("Énergie noire : w0", &w0, -1.6f, -0.4f, "%.2f");
    changed |= ImGui::SliderFloat("Énergie noire : wa", &wa, -2.0f, 1.0f, "%.2f");
    ImGui::PopItemWidth();
    if (ImGui::Button("Valeurs mesurées (Planck 2018)")) {
        c = cosmo::Params{};
        sim.cosmologyDirty = true;
    } else if (changed) {
        c.h0 = h0; c.om = om; c.ode = ode; c.w0 = w0; c.wa = wa;
        sim.cosmologyDirty = true;
    }
    ImGui::TextDisabled("Âge de l'univers : %s milliards d'années (calculé).", frNum(cosmo::ageGyr(c), 4).c_str());
    ImGui::TextDisabled("Forme de l'espace : %s (calculé).", std::fabs(ok) < 0.005 ? "plat" : ok > 0 ? "ouvert (courbure négative)" : "fermé (courbure positive)");
    ImGui::TextDisabled("Bouge un curseur : toutes les galaxies se replacent aussitôt.");
    ImGui::End();
}

// ---------------------------------------------------------------- accueil, visite, aide

void drawWelcome(Sim& sim, UiState& ui, float w, float h, ImGuiWindowFlags fixed) {
    if (!ui.welcome) return;
    ImGui::SetNextWindowPos({w * 0.5f, h - px(ui, 120)}, 0, {0.5f, 1});
    ImGui::Begin("accueil", nullptr, fixed);
    ImGui::PushFont(ui.big);
    ImGui::TextUnformatted("Bienvenue dans Univers");
    ImGui::PopFont();
    ImGui::TextUnformatted("Tout ce que tu vois est placé d'après des mesures réelles : planètes, étoiles, galaxies.");
    ImGui::TextDisabled("Clique sur un astre pour y aller. Molette pour zoomer, glisser pour tourner, tape un nom pour chercher.");
    ImGui::Spacing();
    if (ImGui::Button("  Visite guidée (une minute et demie)  ")) startTour(sim, ui, 0);
    ImGui::SameLine();
    if (ImGui::Button("  Explorer seul  ")) {
        ui.welcome = false;
        sim.touched = true;
    }
    ImGui::End();
}

std::string tourCaption(const Sim& sim, int step) {
    switch (step) {
        case 0: return "La Terre, éclairée par le Soleil à la date affichée.";
        case 1: return "La Lune, à la place donnée par les éphémérides de la NASA.";
        case 2:
            if (!sim.ephemValid) return "Le système solaire : planètes placées par le calcul de gravité mutuelle (hors de la plage de la NASA).";
            return "Le système solaire : orbites tirées des éphémérides de la NASA" +
                   (sim.asteroidCount ? ", et " + frInt(static_cast<double>(sim.asteroidCount)) + " astéroïdes sur leurs orbites mesurées." : std::string("."));
        case 3: return "Jupiter, la plus grande planète, et ses lunes.";
        case 4: return "Saturne et ses anneaux.";
        case 5: return "Les étoiles voisines du Soleil, à leur distance mesurée (Hipparcos, Gaia).";
        case 6:
            if (sim.hasGaia) return "Les étoiles mesurées autour du Soleil : Hipparcos, et Gaia DR3 pour celles dont la distance est sûre à 10 % près.";
            return frInt(static_cast<double>(sim.stars->n)) + " étoiles mesurées autour du Soleil (Hipparcos, Gaia DR3).";
        case 7: return "Andromède, la grande galaxie voisine, à sa distance mesurée.";
        default: return "Des millions de galaxies et de quasars, placés d'après leur décalage vers le rouge mesuré.";
    }
}

void drawTour(Sim& sim, UiState& ui, float w, float h, ImGuiWindowFlags fixed) {
    if (ui.tour < 0) return;
    ImGuiIO& io = ImGui::GetIO();
    // La main reprend la visite : un clic, la molette ou un glisser sur l'image l'arrête.
    if (!io.WantCaptureMouse && (io.MouseWheel != 0 || ImGui::IsMouseClicked(ImGuiMouseButton_Left) || ImGui::IsMouseClicked(ImGuiMouseButton_Right))) {
        ui.tour = -1;
        return;
    }
    ui.tourClock += io.DeltaTime;
    if (!sim.flying) sim.yaw += 0.05 * io.DeltaTime;      // lent tour autour de l'étape
    const double total = Sim::kFlySeconds + kTourHoldSeconds;
    if (ui.tourClock >= total) {
        startTour(sim, ui, ui.tour + 1);
        if (ui.tour < 0) return;
    }
    ImGui::SetNextWindowPos({w * 0.5f, h - px(ui, 120)}, 0, {0.5f, 1});
    ImGui::Begin("visite", nullptr, fixed);
    ImGui::TextDisabled("Visite guidée   •   étape %d sur %d", ui.tour + 1, kTourCount);
    ImGui::PushFont(ui.big);
    ImGui::TextUnformatted(sim.bodies[static_cast<size_t>(sim.focus)].name.c_str());
    ImGui::PopFont();
    ImGui::TextUnformatted(tourCaption(sim, ui.tour).c_str());
    ImGui::ProgressBar(static_cast<float>(ui.tourClock / total), {px(ui, 520), px(ui, 4)}, "");
    if (ImGui::Button("← Précédente") && ui.tour > 0) startTour(sim, ui, ui.tour - 1);
    ImGui::SameLine();
    if (ImGui::Button("Suivante →")) startTour(sim, ui, ui.tour + 1);
    ImGui::SameLine();
    if (ImGui::Button("Arrêter la visite")) ui.tour = -1;
    ImGui::End();
}

void helpLine(const UiState& ui, const char* key, const char* what) {
    ImGui::TextUnformatted(key);
    ImGui::SameLine(px(ui, 220));
    ImGui::TextDisabled("%s", what);
}

void drawHelp(UiState& ui, float w, float h) {
    if (!ui.help) return;
    ImGui::SetNextWindowBgAlpha(0.97f);
    ImGui::SetNextWindowPos({w * 0.5f, h * 0.5f}, 0, {0.5f, 0.5f});
    ImGui::Begin("Commandes", &ui.help, ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_AlwaysAutoResize |
                                             ImGuiWindowFlags_NoSavedSettings);
    ImGui::TextUnformatted("Souris");
    helpLine(ui, "Clic sur un astre", "y aller (son point ou son nom) ; encore un clic : s'en approcher");
    helpLine(ui, "Glisser", "tourner autour de l'astre suivi");
    helpLine(ui, "Molette", "zoomer, dézoomer");
    ImGui::Separator();
    ImGui::TextUnformatted("Clavier");
    helpLine(ui, "Taper un nom", "chercher un astre ; flèches et Entrée pour choisir");
    helpLine(ui, "1  2  3  4  5", "échelles : système solaire … univers lointain");
    helpLine(ui, "+  −", "zoomer, dézoomer");
    helpLine(ui, "Flèches", "tourner autour de l'astre suivi");
    helpLine(ui, "Retour arrière", "revenir à la vue précédente");
    helpLine(ui, "Origine", "revenir au Soleil");
    helpLine(ui, "Espace", "arrêter ou faire avancer le temps");
    helpLine(ui, "Page préc. / suiv.", "temps plus rapide / plus lent");
    helpLine(ui, "F2  F3", "lumière du ciel précédente / suivante (radio … gamma)");
    helpLine(ui, "F1", "afficher ou cacher cette aide");
    helpLine(ui, "Échap", "fermer la recherche ou un menu ; sinon quitter");
    ImGui::Spacing();
    if (ImGui::Button("Fermer")) ui.help = false;
    ImGui::End();
}

// ---------------------------------------------------------------- complétude (choix de Marc : toujours visible, détail au clic)

// En haut à droite : ce qui est présent à l'échelle regardée, comparé à ce qui est connu. Un clic ouvre le détail.
void drawCompleteness(const Sim& sim, UiState& ui, float w, ImGuiWindowFlags fixed) {
    if (!sim.completeness) return;
    const completude::Echelle& e = (*sim.completeness)[static_cast<size_t>(completude::echellePour(sim.dist))];
    // En haut à droite ; si la place manque à côté de la barre du temps, juste en dessous d'elle.
    const bool roomOnTop = ui.searchRight + ui.timeW + ui.completenessW + px(ui, 48) <= w;
    ImGui::SetNextWindowPos({w - px(ui, 16), roomOnTop ? px(ui, 16) : ui.timeBottom + px(ui, 12)}, 0, {1, 0});
    ImGui::Begin("completude-ligne", nullptr, fixed);
    std::string line = completude::ligneCourte(e);
    if (!ui.details && line.find('%') != std::string::npos) line = line.substr(0, line.find('%') + 1) + " de ce qui est connu";      // minimaliste : le chiffre, le détail au clic
    if (ImGui::Selectable(line.c_str(), ui.completeness)) ui.completeness = !ui.completeness;
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Clic : ce qui est montré ici, comparé à ce qui est connu");
    ui.completenessBottom = ImGui::GetWindowPos().y + ImGui::GetWindowHeight();
    ui.completenessW = ImGui::GetWindowWidth();
    ImGui::End();
    if (!ui.completeness) return;
    ImGui::SetNextWindowPos({w * 0.5f, ImGui::GetIO().DisplaySize.y * 0.5f}, 0, {0.5f, 0.5f});
    ImGui::SetNextWindowBgAlpha(0.97f);
    ImGui::Begin("Ce qui est montré ici", &ui.completeness,
                 ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_NoSavedSettings);
    completude::detail(e);
    ImGui::Spacing();
    if (ImGui::Button("Fermer")) ui.completeness = false;
    ImGui::End();
}

// Clic sur l'image, hors d'un astre nommé : l'astéroïde le plus proche à moins de 12 pixels (environ 10 ms, au clic seulement).
void clickAsteroid(Sim& sim, UiState& ui, const Camera& cam, float w, float h, int hovered) {
    if (hovered >= 0 || ImGui::GetIO().WantCaptureMouse || !sim.asteroidCat || sim.asteroidGain(sim.asteroidEpochJd) <= 0.01) return;
    const ImVec2 drag = ImGui::GetMouseDragDelta(ImGuiMouseButton_Left, 4.0f);
    if (!ImGui::IsMouseReleased(ImGuiMouseButton_Left) || drag.x != 0 || drag.y != 0) return;
    const ImVec2 m = ImGui::GetIO().MousePos;
    const int k = sim.nearestAsteroid(cam, m.x, m.y, w, h, 12.0 * ui.s);
    if (k < 0) return;
    const int i = sim.selectAsteroid(k);
    if (i >= 0 && sim.visible(i)) goToBody(sim, ui, i);
}

}  // namespace
