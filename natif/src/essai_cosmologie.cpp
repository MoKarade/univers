// Contrôle de cosmologie.h contre astropy.
//
// Référence : app/test/cone.test.js (astropy, LambdaCDM, H0 = 67,4, Omega_m = 0,315, Omega_Lambda = 0,685, photons à
// 2,7255 K, 3,046 neutrinos sans masse ; calculé le 12/11/2026) : distance comobile transverse en Mpc.
// Tolérance : 0,1 %. Second contrôle : âge de l'univers pour ces paramètres, 13,79 milliards d'années (Planck 2018
// donne 13,797 ± 0,023 pour son modèle de base) ; tolérance 0,05.
// Troisième contrôle, de cohérence : avec w0 = -1 et wa = 0, la formule de l'énergie noire variable redonne
// exactement la constante cosmologique ; avec w0 = -0,9, les distances diminuent (énergie noire plus « diluée »).
#include <cstdio>

#include "cosmologie.h"

int main() {
    const cosmo::Params planck;
    const double zMax = 7.0;
    const int steps = 4096;
    const auto table = cosmo::distanceTable(planck, zMax, steps);
    auto at = [&](const std::vector<double>& t, double z) {
        const double x = std::log(1.0 + z) / std::log(1.0 + zMax) * steps;
        const int k = static_cast<int>(x);
        return t[static_cast<size_t>(k)] + (t[static_cast<size_t>(k) + 1] - t[static_cast<size_t>(k)]) * (x - k);
    };
    const double ref[][2] = {{0.1, 434.1}, {0.5, 1951.3}, {1.0, 3401.0}, {2.0, 5311.2}, {3.0, 6504.6}};
    bool ok = true;
    for (const auto& r : ref) {
        const double got = at(table, r[0]);
        const bool good = std::fabs(got / r[1] - 1.0) < 1e-3;
        ok &= good;
        std::printf("z = %.1f : %.1f Mpc (astropy %.1f) -> %s\n", r[0], got, r[1], good ? "PASSE" : "ECHEC");
    }
    const double age = cosmo::ageGyr(planck);
    const bool ageOk = std::fabs(age - 13.79) < 0.05;
    ok &= ageOk;
    std::printf("age de l'univers : %.3f milliards d'annees (attendu 13,79) -> %s\n", age, ageOk ? "PASSE" : "ECHEC");
    cosmo::Params w = planck;
    w.w0 = -0.9;
    const double d1 = at(table, 1.0), d2 = at(cosmo::distanceTable(w, zMax, steps), 1.0);
    const bool wOk = d2 < d1 && d2 > 0.9 * d1;
    ok &= wOk;
    std::printf("energie noire w0 = -0,9 : distance a z = 1 de %.1f Mpc contre %.1f -> %s\n", d2, d1, wOk ? "PASSE" : "ECHEC");
    std::printf(ok ? "PASSE\n" : "ECHEC\n");
    return ok ? 0 : 1;
}
