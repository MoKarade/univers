// Contrôle de la lumière déviée par la gravité (deviation.h), contre des valeurs mesurées ou publiées, sans carte graphique.
//   1. Soleil : 1,75″ au bord (Dyson, Eddington et Davidson 1920 ; valeur de la relativité générale 1,7512″).
//   2. Champ faible contre rayon suivi pas à pas : même déviation à 0,5 % près loin du trou noir.
//   3. Ombre d'un trou noir sans rotation : paramètre d'impact critique 3√3 G M / c² (Synge 1966).
//   4. Ombres vues de la Terre : Sgr A* 51,8 ± 2,3 µas (EHT 2022), M87* 42 ± 3 µas (EHT 2019).
// Usage : essai_lentille     -> PASSE ou ÉCHEC pour chaque point.
#include <cstdio>
#include "deviation.h"

using namespace lentille;

static int echecs = 0;
static void controle(const char* nom, bool ok, const char* detail) {
    std::printf("%s  %s : %s\n", ok ? "PASSE" : "ECHEC", nom, detail);
    if (!ok) ++echecs;
}

int main() {
    char buf[256];
    const double kRad2As = 180.0 / kPiD * 3600.0;
    // 1. Soleil vu de la Terre, rayon au bord
    const double au = 149597870700.0, rSun = 695700000.0;
    const double chi = std::asin(rSun / au);
    const double a = weakDeflection(kGmSunOverC2M, au, chi) * kRad2As;
    std::snprintf(buf, sizeof buf, "%.4f″ (relativité générale : 1,7512″ pour un rayon au ras du Soleil vu de loin)", a);
    controle("Soleil, au bord", std::fabs(a - 1.7512) < 0.01, buf);
    // 2. Champ faible contre rayon suivi, caméra à 10⁸ G M / c², paramètres d'impact 1 000 et 10 000 G M / c²
    for (double b : {1000.0, 10000.0}) {
        const double r0 = 1e8, c = std::asin(b / r0);
        const double exact = traceRay(r0, c), weak = weakDeflection(1.0, r0, c);
        std::snprintf(buf, sizeof buf, "b = %.0f : suivi %.6e rad, champ faible %.6e rad, écart %.3f %%", b, exact, weak, 100.0 * (exact / weak - 1.0));
        controle("Champ faible", std::fabs(exact / weak - 1.0) < 0.005, buf);
    }
    // 3. Ombre : plus grand angle capturé, caméra très loin (10⁶ G M / c²)
    {
        const double r0 = 1e6;
        double lo = 0, hi = 20.0 / r0;      // capturé en lo, échappe en hi
        for (int i = 0; i < 60; ++i) {
            const double m = 0.5 * (lo + hi);
            (traceRay(r0, m) < 0 ? lo : hi) = m;
        }
        const double bc = r0 * std::sin(lo) / std::sqrt(1.0 - 2.0 / r0);
        std::snprintf(buf, sizeof buf, "paramètre d'impact critique %.4f G M / c² (3√3 = 5,1962)", bc);
        controle("Ombre", std::fabs(bc / 5.196152 - 1.0) < 0.002, buf);
    }
    // 4. Diamètre de l'ombre vu de la Terre : 2 × 3√3 G M / (c² D)
    const double pc = 3.0856775814913673e16;
    struct { const char* nom; double masse, distPc, mesure, err; } ombres[] = {
        {"Sgr A* (4,297 M M☉, 8,277 kpc)", 4.297e6, 8277.0, 51.8, 2.3},
        {"M87* (6,5 G M☉, 16,8 Mpc)", 6.5e9, 16.8e6, 42.0, 3.0},
    };
    for (const auto& o : ombres) {
        const double d = 2.0 * 5.196152 * o.masse * kGmSunOverC2M / (o.distPc * pc) * kRad2As * 1e6;
        std::snprintf(buf, sizeof buf, "%.1f µas calculés, %.1f ± %.1f µas mesurés par l'EHT", d, o.mesure, o.err);
        controle(o.nom, std::fabs(d - o.mesure) < 2.0 * o.err, buf);
    }
    std::printf(echecs ? "ECHEC\n" : "PASSE\n");
    return echecs ? 1 : 0;
}
