// Appli PC « Univers » : la fiche complète de l'astre choisi, dans l'onglet Astre du panneau (interface_panneau.h).
// Demande de Marc (20/11/2026) : toutes les données disponibles, valeurs mesurées avec incertitudes, catalogue et
// référence, modèles et hypothèses dits comme tels, grandeurs dérivées.
//   - Les données publiées viennent de fiches/*.tsv (fiches.h, docs/fiches-format.md) ;
//   - quelques grandeurs sont calculées ici, à la date montrée (coordonnées sur le ciel, temps de trajet de la lumière),
//     et marquées « calculé ».
// Rendu : un titre repliable par groupe (ImGui::CollapsingHeader), une ligne par grandeur (row() de interface_base.h,
// restylé par le fil de l'interface : le premier mot du statut devient une pastille).
#pragma once
#include "fiches.h"
// row(), frDistance… : déjà inclus par interface_panneau.h, qui inclut ce fichier.

namespace {

fiches::Index gFiches;      // démarré par fenetre.cpp dès que le dossier des données est connu

// Remarque en gris qui revient à la ligne (même allure que note() du panneau).
void noteFiche(const char* texte) {
    ImGui::PushStyleColor(ImGuiCol_Text, ImGui::GetStyleColorVec4(ImGuiCol_TextDisabled));
    ImGui::TextWrapped("%s", texte);
    ImGui::PopStyleColor();
}

// ---------------------------------------------------------------- grandeurs calculées ici

// Coordonnées sur le ciel d'une direction (repère écliptique J2000 de l'appli) : ascension droite, déclinaison
// (équatorial J2000) et longitude, latitude galactiques (matrice ICRS -> galactique, Hipparcos 1997, vol. 1, § 1.5.3).
void ciel(Vec3 d, double& ad, double& dec, double& l, double& b) {
    const double eps = 84381.448 / 3600.0 * kPi / 180.0;
    const Vec3 q{d.x, d.y * std::cos(eps) - d.z * std::sin(eps), d.y * std::sin(eps) + d.z * std::cos(eps)};
    const double r = std::sqrt(dot(q, q));
    ad = std::atan2(q.y, q.x);
    if (ad < 0) ad += 2 * kPi;
    dec = std::asin(std::clamp(q.z / r, -1.0, 1.0));
    static const double T[3][3] = {{-0.0548755604162154, -0.8734370902348850, -0.4838350155487132},
                                   {0.4941094278755837, -0.4448296299600112, 0.7469822444972189},
                                   {-0.8676661490190047, -0.1980763734312015, 0.4559837761750669}};
    const double g[3] = {T[0][0] * q.x + T[0][1] * q.y + T[0][2] * q.z, T[1][0] * q.x + T[1][1] * q.y + T[1][2] * q.z,
                         T[2][0] * q.x + T[2][1] * q.y + T[2][2] * q.z};
    l = std::atan2(g[1], g[0]);
    if (l < 0) l += 2 * kPi;
    b = std::asin(std::clamp(g[2] / r, -1.0, 1.0));
}

std::string heuresFr(double rad) {
    const double h = rad * 12.0 / kPi;
    const int hh = static_cast<int>(h), mm = static_cast<int>((h - hh) * 60.0);
    const double ss = ((h - hh) * 60.0 - mm) * 60.0;
    char buf[64];
    std::snprintf(buf, sizeof buf, "%d h %02d min %04.1f s", hh, mm, ss);
    std::string s = buf;
    std::replace(s.begin(), s.end(), '.', ',');
    return s;
}

std::string degresFr(double rad) { return frNum(rad * 180.0 / kPi, 6) + "°"; }

// Durée écrite dans l'unité qui parle.
std::string dureeFr(double secondes) {
    if (secondes < 120) return frNum(secondes, 3) + " secondes";
    if (secondes < 7200) return frNum(secondes / 60.0, 3) + " minutes";
    if (secondes < 172800) return frNum(secondes / 3600.0, 3) + " heures";
    const double ans = secondes / kYearSeconds;
    if (ans < 2) return frNum(secondes / 86400.0, 3) + " jours";
    if (ans < 1e6) return frNum(ans, 3) + " ans";
    if (ans < 1e9) return frNum(ans / 1e6, 3) + " millions d'années";
    return frNum(ans / 1e9, 3) + " milliards d'années";
}

void groupeCalcule(const Sim& sim, const UiState& ui, int f) {
    const Body& b = sim.bodies[static_cast<size_t>(f)];
    if (b.structure && (b.name == "Univers observable" || b.name == "Fond diffus cosmologique")) return;      // sphère centrée sur nous : pas de direction
    const bool proche = b.kind == Kind::Planet || b.kind == Kind::Asteroid || b.kind == Kind::Probe;
    int terre = -1;
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
        if (sim.bodies[static_cast<size_t>(i)].naif == eph::kEarth && sim.bodies[static_cast<size_t>(i)].kind == Kind::Planet) terre = i;
    if (terre == f) return;
    const bool depuisTerre = (proche || b.kind == Kind::Sun) && terre >= 0 && sim.visible(terre);
    const Vec3 d = depuisTerre ? sim.position(f) - sim.position(terre) : sim.position(f);
    const double r = std::sqrt(dot(d, d));
    if (r <= 0) return;
    if (!ImGui::CollapsingHeader("Sur le ciel, à la date montrée##fiche-calc")) return;
    double ad, dec, l, bb;
    ciel(d, ad, dec, l, bb);
    const char* st = depuisTerre ? "calculé — vu du centre de la Terre, position de l'appli, repère J2000" : "calculé — vu du Soleil, position de l'appli, repère J2000";
    row("Ascension droite", heuresFr(ad), st, ui.s);
    row("Déclinaison", degresFr(dec), st, ui.s);
    row("Longitude galactique", degresFr(l), st, ui.s);
    row("Latitude galactique", degresFr(bb), st, ui.s);
    row(depuisTerre ? "Distance à la Terre" : "Distance au Soleil", frDistance(r), "calculé — position de l'appli", ui.s);
    row("Temps mis par sa lumière", dureeFr(r * kYearSeconds), "calculé — distance / vitesse de la lumière", ui.s);
    if (b.kind == Kind::Galaxy) noteFiche("Les grandes distances (galaxies) sont celles du catalogue ; ici, elles ne tiennent pas compte de l'expansion de l'univers pendant le trajet de la lumière.");
}

// ---------------------------------------------------------------- la fiche

struct FicheCache {
    std::string cle;
    bool pret = false;
    std::vector<fiches::Ligne> lignes;
};
FicheCache gFicheCache;

// Les groupes de la fiche, chacun repliable, dans l'ordre des fichiers.
// Contrôle sans fenêtre : UNIVERS_FICHE=tout ouvre tous les groupes et fait défiler le panneau jusqu'à la fiche (captures).
bool ficheTout() {
    static const bool tout = std::getenv("UNIVERS_FICHE") != nullptr;
    return tout;
}

void drawFicheRows(const std::vector<fiches::Ligne>& lignes, const UiState& ui) {
    std::vector<std::string> groupes;
    for (const auto& l : lignes)
        if (std::find(groupes.begin(), groupes.end(), l.groupe) == groupes.end()) groupes.push_back(l.groupe);
    for (size_t g = 0; g < groupes.size(); ++g) {
        const std::string titre = (groupes[g].empty() ? std::string("Autres données") : groupes[g]) + "##fiche-" + std::to_string(g);
        if (ficheTout()) ImGui::SetNextItemOpen(true, ImGuiCond_Always);
        if (!ImGui::CollapsingHeader(titre.c_str(), g == 0 ? ImGuiTreeNodeFlags_DefaultOpen : 0)) continue;
        ImGui::PushID(static_cast<int>(g));
        for (const auto& l : lignes)
            if (l.groupe == groupes[g]) row(l.libelle.c_str(), fiches::valeurFr(l), fiches::statutFr(l).c_str(), ui.s);
        ImGui::PopID();
    }
}

void drawFiche(const Sim& sim, const UiState& ui, int f) {
    const Body& b = sim.bodies[static_cast<size_t>(f)];
    // Relue seulement quand l'astre change (ou quand le parcours des fichiers vient de finir).
    if (gFicheCache.cle != b.name || gFicheCache.pret != gFiches.pret()) {
        gFicheCache.cle = b.name;
        gFicheCache.pret = gFiches.pret();
        gFicheCache.lignes = gFiches.lire(b.name);
    }
    if (ficheTout()) {
        ImGui::SetScrollHereY(0.0f);
        ImGui::SetNextItemOpen(true, ImGuiCond_Always);
    }
    groupeCalcule(sim, ui, f);
    if (!gFiches.pret()) {
        noteFiche("Lecture des fiches en cours…");
        return;
    }
    if (gFicheCache.lignes.empty()) {
        noteFiche("Pas encore de fiche détaillée pour cet astre (dossier fiches à côté du programme).");
        return;
    }
    drawFicheRows(gFicheCache.lignes, ui);
    noteFiche("Mesuré : observation publiée. Calculé : déduit de mesures (formule dans la source). Modèle : sortie d'un modèle ou "
         "d'une hypothèse. Publié : valeur de catalogue. Incertitudes telles que publiées (± 1 écart type sauf mention).");
}

}  // namespace
