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
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>

#include "groupe_local_scenario.h"
#include "interface_cosmo_courbes.h"

namespace {
bool check(const char* what, double got, double want, double tol) {
    const bool good = std::fabs(got / want - 1.0) < tol;
    std::printf("%-44s %10.4f (attendu %10.4f) -> %s\n", what, got, want, good ? "PASSE" : "ECHEC");
    return good;
}
}  // namespace

int main(int argc, char** argv) {
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
    // 5. Rencontre du Groupe local rejouée (groupe_local_scenario.h) avec les valeurs mesurées : elle doit retomber sur la
    //    référence de l'appli (centres_reference.npz, « resume » : passage d'Andromède à 5,543 Ga et 29,8 kpc, fusion à
    //    6,902 Ga) et sur ses positions (écart d'Andromède sur 0 à 5 Ga). Puis plus d'énergie noire : fusion plus tardive.
    if (argc > 1) {
        CentresReference ref;
        if (!ref.load(std::string(argv[1]) + "/centres_reference.bin")) {
            std::printf("centres_reference.bin illisible -> ECHEC\n");
            ok = false;
        } else {
            const scenario::Result r = scenario::run(ref, scenario::Settings{});
            ok &= check("rejeu : premier passage d'Andromède (Ga)", r.periM31Ga, 5.543, 4e-3);
            ok &= check("rejeu : distance au passage (kpc)", r.periM31Kpc, 29.8, 3e-2);
            ok &= check("rejeu : fusion Voie lactée-Andromède (Ga)", r.mergeM31Ga, 6.902, 4e-3);
            double worst = 0;
            for (size_t i = 0; i < r.tGa.size(); ++i) {
                if (r.tGa[i] > 5.0) break;
                phys::Vec3 g;
                if (!ref.centre(1, r.tGa[i], g)) continue;
                const phys::Vec3 q = r.pos[i][1];
                worst = std::max(worst, std::sqrt((q.x - g.x) * (q.x - g.x) + (q.y - g.y) * (q.y - g.y) + (q.z - g.z) * (q.z - g.z)));
            }
            const bool good = worst < 2.0;
            std::printf("%-44s %10.3f (attendu < 2 kpc) -> %s\n", "rejeu : écart d'Andromède 0-5 Ga (kpc)", worst, good ? "PASSE" : "ECHEC");
            ok &= good;
            scenario::Settings more;
            more.K *= 3.0;
            const scenario::Result r3 = scenario::run(ref, more);
            const bool later = r3.mergeM31Ga < 0 || r3.mergeM31Ga > r.mergeM31Ga;
            std::printf("%-44s %10.3f (plus tard que %.3f, ou jamais) -> %s\n", "énergie noire x 3 : fusion (Ga)", r3.mergeM31Ga, r.mergeM31Ga, later ? "PASSE" : "ECHEC");
            ok &= later;
        }
    } else {
        std::printf("Sans dossier de données : rejeu du Groupe local non contrôlé.\n");
    }
    std::printf("%s\n", ok ? "PASSE" : "ECHEC");
    return ok ? 0 : 1;
}
