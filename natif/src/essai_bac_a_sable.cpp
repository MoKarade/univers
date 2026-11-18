// Contrôle de l'histoire de l'expansion utilisée par le panneau « Univers » et la frise (interface_cosmo_courbes.h).
//
// 1. Âge : même valeur que cosmo::ageGyr (même intégrale, autre grille) à 0,05 % près, pour trois réglages.
// 2. Univers fermé sans énergie noire (Ωm = 2) : solution exacte connue (cycloïde, Friedmann 1922) :
//    a = A (1 - cos θ), t = B (θ - sin θ), A = Ωm / (2 (Ωm - 1)), B = Ωm / (2 H0 (Ωm - 1)^1,5).
//    Durée de vie 2πB ; reste à vivre = 2πB - âge. Tolérance 1 % (le rayonnement, absent de la formule, est dans le calcul).
// 3. Énergie noire fantôme (w = -1,5, univers plat) : la Grande Déchirure arrive environ
//    2 / (3 |1 + w| H0 √(1 - Ωm)) après aujourd'hui (Caldwell, Kamionkowski et Weinberg 2003, formule approchée qui
//    néglige la matière dans l'avenir) ; tolérance 5 %.
// 4. Planck 2018 : 380 000 ans après le Big Bang, l'univers était environ 1 100 fois plus petit (décalage du fond
//    diffus z* = 1 090, Planck 2018) : 1 / a entre 1 050 et 1 120.
#include <cmath>
#include <cstdio>

#include "interface_cosmo_courbes.h"

namespace {
bool check(const char* what, double got, double want, double tol) {
    const bool good = std::fabs(got / want - 1.0) < tol;
    std::printf("%-44s %10.4f (attendu %10.4f) -> %s\n", what, got, want, good ? "PASSE" : "ECHEC");
    return good;
}
}  // namespace

int main() {
    bool ok = true;
    const cosmo::Params planck;
    cosmo::Params dense = planck, phantom = planck, closed = planck;
    dense.om = 0.1; dense.ode = 0.9;
    phantom.w0 = -1.5;
    closed.om = 2.0; closed.ode = 0.0;
    for (const cosmo::Params& p : {planck, dense, phantom}) {
        CosmoHistory h;
        h.update(p);
        ok &= check("âge (Ga) contre cosmo::ageGyr", h.ageGa, cosmo::ageGyr(p), 5e-4);
    }
    {
        CosmoHistory h;
        h.update(closed);
        const double invH0 = 977.7922216807891 / closed.h0, A = closed.om / (2 * (closed.om - 1)), B = closed.om / (2 * std::pow(closed.om - 1, 1.5)) * invH0;
        const double th0 = std::acos(1.0 - 1.0 / A), age = B * (th0 - std::sin(th0)), rest = 2 * 3.14159265358979323846 * B - age;
        ok &= check("univers fermé : âge (Ga)", h.ageGa, age, 1e-2);
        ok &= check("univers fermé : fin dans (Ga)", h.crunch ? h.endGa : -1, rest, 1e-2);
    }
    {
        CosmoHistory h;
        h.update(phantom);
        const double invH0 = 977.7922216807891 / phantom.h0, want = 2.0 / (3.0 * 0.5) * invH0 / std::sqrt(1.0 - phantom.om);
        ok &= check("w = -1,5 : Grande Déchirure dans (Ga)", h.rip ? h.endGa : -1, want, 5e-2);
    }
    {
        CosmoHistory h;
        h.update(planck);
        const double inv = 1.0 / h.aAtSinceBigBang(380000.0 / 1e9);
        const bool good = inv > 1050 && inv < 1120;
        std::printf("%-44s %10.1f (attendu 1050 à 1120) -> %s\n", "Planck : 1/a à 380 000 ans", inv, good ? "PASSE" : "ECHEC");
        ok &= good;
    }
    std::printf("%s\n", ok ? "PASSE" : "ECHEC");
    return ok ? 0 : 1;
}
