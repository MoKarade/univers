// Appli PC « Univers » : section « Vie de l'étoile » du panneau (onglet Astre) pour le Soleil et les étoiles nommées.
// Étape à la date montrée, valeurs calculées, où est passée sa matière, et un bouton par étape pour y aller et la voir
// défiler (vitesse choisie pour que l'étape dure une trentaine de secondes à l'écran).
#pragma once
#include "cycle_appli.h"

namespace {

CycleAppli* gCycle = nullptr;
void note(const char* fmt, ...);      // interface_panneau.h

std::string dureeAns(double ans) {
    const double a = std::fabs(ans);
    if (a >= 1e9) return frNum(a / 1e9, 3) + " milliards d'années";
    if (a >= 1e6) return frNum(a / 1e6, 3) + " millions d'années";
    if (a >= 1e3) return frNum(a / 1e3, 3) + " milliers d'années";
    if (a >= 1.0) return frNum(a, 3) + " ans";
    return frNum(a * 365.25, 2) + " jours";
}
std::string quandAns(double ans) { return std::fabs(ans) < 0.5 / 365.25 ? "maintenant" : (ans > 0 ? "dans " : "il y a ") + dureeAns(ans); }

struct EtapeBouton {
    cycle::Etape e;
    const char* label;
    double vueAl;      // distance de la caméra pour la voir (années-lumière) ; 0 : d'après le rayon de l'étoile
};

void cycleSection(Sim& sim, UiState& ui, int f) {
    if (!gCycle) return;
    const CycleAppli::Astre* a = gCycle->of(f);
    if (!a) return;
    if (!ImGui::CollapsingHeader("Vie de l'étoile", ImGuiTreeNodeFlags_DefaultOpen)) return;
    const cycle::Vie& v = a->vie;
    const cycle::Etat& s = a->vu.modele;
    const double now = sim.years - kStartYears;
    const bool massive = v.massive();
    row("Étape", cycle::nomEtape(s.etape, massive, a->vu.teff), "modèle", ui.s);
    if (s.age >= 0) row("Âge", dureeAns(s.age), v.source == 1 ? "mesuré aujourd'hui, puis calculé" : "calculé, modèle", ui.s);
    if (s.masse > 0) row("Masse", frNum(s.masse, 3) + " M☉ (née avec " + frNum(v.m0, 3) + " M☉)", "calculé, modèle", ui.s);
    if (a->vu.rayonKm > 0) {
        const double rs = a->vu.rayonKm / cycle::kRsunKm;
        std::string t = s.trouNoir ? frNum(a->vu.rayonKm, 3) + " km (ombre du trou noir)" : rs >= 0.01 ? frNum(rs, 3) + " R☉" : frNum(a->vu.rayonKm, 3) + " km";
        if (rs > 30) t += ", " + frNum(a->vu.rayonKm / 1.495978707e8, 3) + " UA";
        row("Rayon", t, std::fabs(now) < 1e-6 ? "mesuré" : "calculé", ui.s);
    }
    if (a->vu.teff > 0) row("Température de surface", frNum(a->vu.teff, 3) + " K", std::fabs(now) < 1e-6 ? "mesuré" : "calculé", ui.s);
    if (s.lum > 0) row("Éclat (toute la lumière)", frNum(s.lum, 3) + " fois le Soleil d'aujourd'hui", "calculé, modèle", ui.s);
    // Où est la matière : tout ce que le cœur de nuage contenait est quelque part.
    const cycle::Bilan& b = a->bilan;
    if (a->profilOk || b.coeur > 0) {
        std::string m = "étoile " + frNum(b.etoile, 3) + " M☉";
        if (b.nuage > 1e-4) m += ", nuage " + frNum(b.nuage, 3);
        if (b.vents > 1e-4) m += ", vents et nébuleuse " + frNum(b.vents, 3);
        if (b.ejecta > 1e-4) m += ", éjecta de la supernova " + frNum(b.ejecta, 3);
        if (b.milieu > 1e-4) m += ", déjà mêlée au milieu " + frNum(b.milieu, 3);
        if (b.neutrinos > 1e-4) m += ", partie en neutrinos " + frNum(b.neutrinos, 3);
        row("Masse du nuage de départ", frNum(b.coeur, 3) + " M☉ : " + m, "calculé, conservé", ui.s);
        if (a->profilOk && a->profil.ionise > 1e-4) row("Gaz ionisé (qui brille)", frNum(a->profil.ionise, 3) + " M☉", "calculé, modèle", ui.s);
    }
    // Sa fin.
    std::string fin;
    if (v.fin == 2) fin = v.reste.explose ? std::string("supernova, puis ") + (v.reste.trouNoir ? "trou noir de " : "étoile à neutrons de ") + frNum(v.reste.gravite, 3) + " M☉"
                                          : "effondrement sans explosion : trou noir de " + frNum(v.reste.gravite, 3) + " M☉";
    else if (v.fin == 3) fin = "brille encore bien après 10 milliards d'années (au-delà du modèle)";
    else fin = "nébuleuse planétaire, puis naine blanche de " + frNum(v.masseNaine, 3) + " M☉";
    row("Sa fin", fin, "modèle", ui.s);
    if (v.fin != 3) {
        const double mort = v.ageMort() - v.ageAujourdhui;
        std::string q = quandAns(mort);
        if (v.source == 2 && v.finHaut > v.finBas) q += " (de " + dureeAns(v.finBas) + " à " + dureeAns(v.finHaut) + " à partir d'aujourd'hui)";
        row(mort > now ? "Elle meurt" : "Morte", q, "calculé, modèle", ui.s);
    }
    if (v.source == 2)
        note("Masse et âge placés d'après son éclat et sa couleur mesurés (le modèle le plus probable ; masse de %s à %s M☉). Une étoile peut "
             "avoir le même éclat et la même couleur à deux étapes de sa vie : ce placement est une estimation.",
             frNum(v.mBas, 3).c_str(), frNum(v.mHaut, 3).c_str());
    if (!a->sourceTeff.empty()) note("Température de surface mesurée par spectroscopie : %s (au lieu de celle tirée de sa couleur).", a->sourceTeff.c_str());
    if (v.source == 1) note("Âge du Soleil mesuré (4,568 milliards d'années, météorites) ; sa vie ensuite : calculée.");
    if (f == 0 && sim.starShare() <= 0)
        note("À cette date, la place du Soleil dans la Galaxie n'est pas calculée (après le passage d'Andromède) : il est montré "
             "à l'endroit d'où l'on regarde. Seule sa vie est montrée.");
    note("Modèles publiés : trajectoires MIST v1.2 (Choi et al. 2016), naines blanches de Montréal (Bédard et al. 2020), "
         "restes des supernovas (Fryer et al. 2012), courbe moyenne des supernovas (Anderson et al. 2014). Nuage de naissance, "
         "vents et nébuleuse : modèles simples, valeurs typiques publiées. Teintes du gaz : supposées.");

    // Boutons : une étape, une date ; la vitesse fait durer l'étape une trentaine de secondes.
    ImGui::Spacing();
    ImGui::TextUnformatted("Voir une étape :");
    static const EtapeBouton kBoutons[] = {
        {cycle::Etape::Nuage, "Nuage", 1.5},           {cycle::Etape::Enfouie, "Naissance", 1.5},
        {cycle::Etape::Sequence, "Séquence principale", 0}, {cycle::Etape::Geante, "Géante", 0},
        {cycle::Etape::Helium, "Hélium", 0},           {cycle::Etape::AGB, "Dernière géante", 0},
        {cycle::Etape::Nebuleuse, "Nébuleuse", 1.2},   {cycle::Etape::NaineBlanche, "Naine blanche", 0},
        {cycle::Etape::Supernova, "Supernova", 0},     {cycle::Etape::EtoileNeutrons, "Étoile à neutrons", 6.0},
        {cycle::Etape::TrouNoir, "Trou noir", 6.0},
    };
    const double lo = sim.minYears() - kStartYears;
    const double hi = (f == 0 ? sim.maxYears() - kStartYears : sim.starEraEndYears);
    bool line = false;
    for (size_t k = 0; k < sizeof(kBoutons) / sizeof(kBoutons[0]); ++k) {
        const EtapeBouton& eb = kBoutons[k];
        const double debut = v.debutEtape(eb.e);
        if (debut < 0 && eb.e != cycle::Etape::Nuage && eb.e != cycle::Etape::Enfouie) continue;
        // fin de l'étape : début de l'étape suivante qui existe
        double suite = -1;
        for (size_t j = k + 1; j < sizeof(kBoutons) / sizeof(kBoutons[0]) && suite < 0; ++j) {
            const double d = v.debutEtape(kBoutons[j].e);
            if (d > debut) suite = d;
        }
        const double duree = suite > debut ? suite - debut : 1.0e4;
        const double date = debut - v.ageAujourdhui;
        const bool ok = date >= lo && date <= hi;
        if (line && ImGui::GetContentRegionAvail().x > 160.0f * ui.s) ImGui::SameLine();
        line = true;
        ImGui::BeginDisabled(!ok);
        ImGui::PushID(static_cast<int>(k));
        if (ImGui::Button(eb.label)) {
            sim.years = kStartYears + date;
            sim.speed = std::max(duree / 30.0, 1.0e-3);
            sim.paused = false;
            sim.backward = false;
            sim.touched = true;
            // distance pour la voir : plusieurs fois le plus grand rayon de l'étape, ou la taille de la matière autour
            double vue = eb.vueAl;
            if (vue <= 0) {
                double r = 0;
                for (int i = 0; i <= 40; ++i) r = std::max(r, cycle::vuA(v, date + duree * i / 40.0).rayonKm);
                vue = std::max(8.0 * r / kLyInKm, 30.0 * 695700.0 / kLyInKm);
            }
            sim.flyTo(f, vue);
        }
        ImGui::PopID();
        ImGui::EndDisabled();
        if (ImGui::IsItemHovered(ImGuiHoveredFlags_AllowWhenDisabled))
            ImGui::SetTooltip("%s", ok ? (quandAns(date) + ", pendant " + dureeAns(duree)).c_str()
                                       : (quandAns(date) + " : hors des dates que l'appli montre pour cet astre").c_str());
    }
}

}  // namespace
