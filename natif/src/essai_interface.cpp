// Contrôle des outils de texte de l'interface (recherche sans accents, dates tapées). Aucune carte graphique.
#include <cstdio>
#include <vector>

#include "arrivee.h"
#include "interface_outils.h"

namespace {
int failures = 0;
void expect(bool ok, const char* what) {
    std::printf("%s  %s\n", ok ? "ok   " : "ECHEC", what);
    if (!ok) ++failures;
}
bool near(double a, double b) { return a - b < 1e-9 && b - a < 1e-9; }
}  // namespace

int main() {
    using namespace ui_outils;
    expect(fold("Vénus") == "venus", "Vénus -> venus");
    expect(fold("ÉTOILE polaire") == "etoile polaire", "majuscule accentuée");
    expect(fold("Alnilam, dans la ceinture d\xE2\x80\x99Orion") == "alnilam, dans la ceinture d'orion", "apostrophe typographique");
    expect(matchRank("Saturne", "sat") == 0, "début du nom");
    expect(matchRank("Andromède (M31)", "m31") == 1, "début d'un mot");
    expect(matchRank("Bételgeuse", "geuse") == 2, "au milieu");
    expect(matchRank("Mars", "venus") == -1, "pas de correspondance");
    double y = 0;
    // J2000,0 = 1er janvier 2000 à 12 h TU : le 1er janvier 2000 à 0 h est un demi-jour avant.
    expect(parseDate("1/1/2000", y) && near(y, -0.5 / 365.25), "1/1/2000");
    expect(parseDate("2000-01-01", y) && near(y, -0.5 / 365.25), "2000-01-01");
    // 21 juillet 1969 à 0 h TU = jour julien 2440423,5 (USNO).
    expect(parseDate("21/07/1969", y) && near(y, (2440423.5 - 2451545.0) / 365.25), "21/07/1969");
    expect(parseDate("1969", y) && near(y, (2440222.5 - 2451545.0) / 365.25), "1969 -> 1er janvier 1969");
    expect(parseDate("250000", y) && near(y, 248000.0), "250000 -> année seule");
    expect(parseDate("\xE2\x88\x92" "10000", y) && near(y, -12000.0), "signe moins typographique");
    expect(!parseDate("demain", y), "texte refusé");
    expect(!parseDate("32/01/2000", y), "jour impossible refusé");
    NameIndex idx;
    idx.build({"Ceres~1", "Pallas~2", "Vesta~4", "Rosavestal~34366", "~2000 CM104", "Éros~433", "Tatata~7"});
    const std::vector<int> v = idx.find("vesta", 6);
    expect(v.size() == 2 && v[0] == 2 && v[1] == 3, "index : vesta -> Vesta puis Rosavestal");
    expect(idx.find("eros", 6) == std::vector<int>{5}, "index : sans accents");
    expect(idx.find("2000 cm", 6) == std::vector<int>{4}, "index : désignation");
    expect(idx.find("tat", 6) == std::vector<int>{6}, "index : un nom ne compte qu'une fois");
    expect(idx.find("s\nr", 6).empty() && idx.find("c", 6).empty(), "index : retour à la ligne ou 1 caractère refusés");
    NameIndex first;
    first.build({"Halley~2688", "Ceres~1", "Halley~1P~c"}, {0, 0, 1});
    expect(first.find("halley", 6) == std::vector<int>{2, 0}, "index : la comète passe devant (rangs d'origine)");
    // Distance d'arrivée sur une structure (arrivee.h) : textes réels de structures_noms.tsv et superstructures_noms.tsv.
    const double lan = arrivee::structureSizeLy("superamas ; bassin dâattraction de la Voie lactÃ©e, 1.9 millions de (Mpc/h)Â³ (Dupuy et Courtois 2023)");
    // sphère de 1,9 × 10⁶ (Mpc/h)³ : rayon 76,8 Mpc/h = 114 Mpc ; diamètre 228 Mpc = 7,43 × 10⁸ al
    expect(lan > 7.3e8 && lan < 7.6e8, "Laniakea : diamètre de 7,4 × 10^8 al");
    const double vide = arrivee::structureSizeLy("vide ; rayon 33 Mpc/h, centre à 160 Mpc/h (Malandrino et al. 2026)");
    expect(vide > 3.18e8 && vide < 3.21e8, "vide de rayon 33 Mpc/h : diamètre 3,19 × 10^8 al (le centre à 160 Mpc/h n'est pas pris)");
    const double mur = arrivee::structureSizeLy("superstructure ; 13 amas ; taille publiée : 1.37 milliard d'années-lumière (Gott et al. 2005) ; 1.14 milliards dâannées-lumière ; source");
    expect(mur > 1.13e9 && mur < 1.15e9, "Grand Mur de Sloan : 1,14 × 10^9 al");
    expect(arrivee::structureSizeLy("Grand Attracteur") == arrivee::kDefautLy, "sans taille : 3 × 10^8 al");
    std::printf(failures ? "ECHEC (%d)\n" : "PASSE\n", failures);
    return failures ? 1 : 0;
}
