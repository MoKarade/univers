// Contrôle des outils de texte de l'interface (recherche sans accents, dates tapées). Aucune carte graphique.
#include <cmath>
#include <cstdio>

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
    expect(fold("Alnilam, dans la ceinture d\xE2\x80\x99Orion") == "alnilam, dans la ceinture d'orion",
           "apostrophe typographique");
    expect(fold("Ha\xC3\xBF") == "hay", "ÿ -> y");
    expect(fold("Stra\xC3\x9F" "e") == "strase", "ß -> s");
    expect(fold("C\xC5\x93" "ur de l'\xC5\x92" "il") == "coeur de l'oeil", "œ / Œ -> oe");
    expect(fold("\xC3\x86" "ther \xC3\xA6" "on") == "aether aeon", "Æ / æ -> ae");
    expect(fold("\xC5\xB8") == "y", "Ÿ -> y");
    expect(matchRank("N\xC5\x93" "ud lunaire", fold("noeud")) == 0, "recherche avec ligature œ");
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
    expect(parseDate("5000000000", y) && near(y, 4999998000.0), "5000000000 -> temps profond (+5 Ga)");
    expect(parseDate("\xE2\x88\x92" "10000", y) && near(y, -12000.0), "signe moins typographique");
    expect(!parseDate("demain", y), "texte refusé");
    expect(!parseDate("32/01/2000", y), "jour impossible refusé");
    expect(parseDate("2024-02-29", y), "2024-02-29 bissextile acceptée");
    expect(!parseDate("2023-02-29", y), "2023-02-29 non bissextile refusée");
    expect(!parseDate("31/02/2023", y), "31/02/2023 impossible refusée");
    expect(!parseDate("1/1/99999999999999999999999", y), "débordement entier dans D/M/Y refusé");
    expect(!parseDate("99999999999999999999999-01-01", y), "débordement entier dans Y-M-D refusé");
    double y4800Jan = 0, y4800Mar = 0;
    expect(parseDate("-4800-01-01", y4800Jan) && parseDate("-4800-03-01", y4800Mar) &&
               near((y4800Mar - y4800Jan) * 365.25, 60.0) &&
               near(julianDay(-4800, 3, 1) - julianDay(-4800, 1, 1), 60.0),
           "-4800 bissextile (60 jours exacts entre 01-01 et 03-01)");
    double yNegIso = 0, yNegSlash = 0, yNegOnly = 0;
    expect(parseDate("-500-01-01", yNegIso) && parseDate("1/1/-500", yNegSlash) && parseDate("-500", yNegOnly) &&
               near(yNegIso, yNegSlash) && near(yNegIso, yNegOnly),
           "-500-01-01 et 1/1/-500 acceptés et cohérents");
    expect(!parseDate("99999999999999999999999", y), "débordement entier positif refusé");
    expect(!parseDate("-99999999999999999999999", y), "débordement entier négatif refusé");
    expect(parseDate("-9223372036854775808", y) && std::isfinite(y), "LLONG_MIN sans UB");
    std::printf(failures ? "ECHEC (%d)\n" : "PASSE\n", failures);
    return failures ? 1 : 0;
}
