// Contrôle de cosmologie.h contre astropy.
//
// Référence : app/test/cone.test.js (astropy, LambdaCDM, H0 = 67,4, Omega_m = 0,315, Omega_Lambda = 0,685, photons à
// 2,7255 K, 3,046 neutrinos sans masse ; calculé le 12/11/2026) : distance comobile transverse en Mpc.
// Tolérance : 0,1 %. Second contrôle : âge de l'univers pour ces paramètres, 13,79 milliards d'années (Planck 2018
// donne 13,797 ± 0,023 pour son modèle de base) ; tolérance 0,05.
// Troisième contrôle, de cohérence : avec w0 = -1 et wa = 0, la formule de l'énergie noire variable redonne
// exactement la constante cosmologique ; avec w0 = -0,9, les distances diminuent (énergie noire plus « diluée »).
// Quatrième contrôle : sûreté numérique de scaleFactorAt() près du Big Bang et pour de l'énergie noire fantôme.
#include <cmath>
#include <cstdio>
#include <limits>

#include "cosmologie.h"

int main() {
    const cosmo::Params planck;
    const double zMax = 7.0;
    const int steps = 4096;
    const auto table = cosmo::distanceTable(planck, zMax, steps);
    auto at = [&](const std::vector<double>& t, double z) {
        const double x = std::log1p(z) / std::log1p(zMax) * steps;
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

    // Contrôles de sûreté numérique (scaleFactorAt, distanceTable(steps <= 0), operator==).
    const double aNow = cosmo::scaleFactorAt(planck, 0.0);
    const double aFut = cosmo::scaleFactorAt(planck, 5.0);
    const double aBb = cosmo::scaleFactorAt(planck, -age);
    const double aPast = cosmo::scaleFactorAt(planck, -20.0);
    cosmo::Params nonInt = planck;
    nonInt.w0 = -0.9;
    nonInt.wa = 0.3;
    const double aNonIntPast = cosmo::scaleFactorAt(nonInt, -20.0);
    cosmo::Params phantom = planck;
    phantom.w0 = -1.6;
    phantom.wa = -2.0;
    const double aPhantom = cosmo::scaleFactorAt(phantom, 10.0);
    cosmo::Params bigRip = planck;
    bigRip.w0 = -1.6;
    bigRip.wa = 1.0;
    const double aRip10 = cosmo::scaleFactorAt(bigRip, 10.0);
    const double aRip20 = cosmo::scaleFactorAt(bigRip, 20.0);
    // E(a) doit rester finie, positive et croissante en traversant le débordement de exp() (a ~ 234 pour ce coin).
    bool ripMonotone = true;
    double ePrev = 0.0;
    for (int ai = 150; ai <= 400; ++ai) {
        const double eNow = bigRip.e(1.0 / ai - 1.0);
        ripMonotone &= std::isfinite(eNow) && eNow > 0.0 && eNow >= ePrev;
        ePrev = eNow;
    }

    cosmo::Params badH0 = planck;
    badH0.h0 = 0.0;
    cosmo::Params negH0 = planck;
    negH0.h0 = -67.4;
    cosmo::Params nanH0 = planck;
    nanH0.h0 = std::numeric_limits<double>::quiet_NaN();
    const double kNan = std::numeric_limits<double>::quiet_NaN();
    const bool guardOk = (aRip10 == 1e30) && (aRip20 == 1e30) && ripMonotone &&
                         cosmo::distanceTable(badH0, zMax, 64).size() == 1 &&
                         cosmo::distanceTable(badH0, zMax, 64)[0] == 0.0 &&
                         cosmo::distanceTable(negH0, zMax, 64).size() == 1 &&
                         cosmo::distanceTable(nanH0, zMax, 64).size() == 1 &&
                         cosmo::distanceTable(planck, 0.0, 64).size() == 1 &&
                         cosmo::distanceTable(planck, -2.0, 64).size() == 1 &&
                         cosmo::distanceTable(planck, kNan, 64).size() == 1 &&
                         cosmo::ageGyr(badH0) == 0.0 && cosmo::ageGyr(negH0) == 0.0 && cosmo::ageGyr(nanH0) == 0.0 &&
                         cosmo::scaleFactorAt(badH0, 5.0) == 1.0 && cosmo::scaleFactorAt(negH0, 5.0) == 1.0 &&
                         cosmo::scaleFactorAt(nanH0, 5.0) == 1.0;

    const double aNan = cosmo::scaleFactorAt(planck, kNan);
    const bool safeOk = (aNow == 1.0) && std::isfinite(aFut) && aFut > 1.3 && aFut < 1.5 &&
                        std::isfinite(aBb) && aBb >= 1e-6 && aPast == 1e-6 &&
                        std::isfinite(aNonIntPast) && aNonIntPast == 1e-6 &&
                        std::isfinite(aPhantom) && aPhantom > 1.0 && aNan == 1.0 &&
                        cosmo::distanceTable(planck, zMax, 0).size() == 1 && (planck == cosmo::Params{}) && !(planck == w) &&
                        guardOk;
    ok &= safeOk;
    std::printf(
        "cas limites scaleFactorAt (a(+5 Ga)=%.3f, a(-age)=%.2e, a(-20 Ga)=%.1e, fantome=%.3g, bigRip=%.1e) -> %s\n",
        aFut, aBb, aNonIntPast, aPhantom, aRip10, safeOk ? "PASSE" : "ECHEC");

    std::printf(ok ? "PASSE\n" : "ECHEC\n");
    return ok ? 0 : 1;
}
