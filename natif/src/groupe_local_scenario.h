// Appli PC « Univers » : la rencontre du Groupe local REJOUÉE EN DIRECT avec les réglages du bac à sable (énergie noire,
// matière noire des galaxies). Demande de Marc, 18/11/2026 : « plus d'énergie noire, etc. » doit changer ce qu'on voit.
//
// C'est la même physique que les centres de référence de l'appli (pipeline/fusion/groupe_local_reference.py, fonction
// `reference`, d'après Sawala et al. 2025) portée telle quelle en C++ : cinq galaxies indéformables (Voie lactée,
// Andromède, Triangle, Grand et Petit Nuage), forces adoucies de 20 kpc (pour une paire avec le Petit Nuage : la moyenne
// des rayons d'échelle des deux halos, au plus 20 kpc), frottement de Chandrasekhar dans les halos NFW (dispersion de
// Zentner et Bullock 2003), énergie noire a = K (x − x_cm), saute-mouton au pas de 0,97779 Ma, sans fusion instantanée ;
// date de fusion = premier passage des centres sous 20 kpc.
// Départ : l'état d'AUJOURD'HUI lu dans centres_reference.bin (positions et vitesses relatives à la Voie lactée ; un
// changement de vitesse commun à tous ne change rien à cette physique). Masses et concentrations : celles écrites dans
// l'en-tête de centres_reference.npz (table unique pipeline/constantes/univers.json), recopiées ci-dessous.
// Contrôle : essai_bac_a_sable rejoue la référence avec les valeurs mesurées et la compare au fichier (dates du passage
// d'Andromède et de la fusion, écart de position).
// Statut à l'écran : « calculé », modèle simplifié (centres seulement, pas les formes des galaxies), jamais une mesure.
#pragma once
#include <array>
#include <cmath>
#include <vector>

#include "centres_reference.h"

namespace scenario {

constexpr int kN = 5;
constexpr double kG = 43007.0;                                    // kpc (km/s)² / 10^10 M☉
constexpr double kUnitGa = 3.0856775814913673e16 / 3.15576e16;    // kpc/(km/s) en Ga
constexpr double kRhoC = 277.536627 * 0.674 * 0.674;              // M☉/kpc³ (H0 = 67,4, comme la table)
constexpr double kStepGa = 0.00097779;                            // pas de la référence
// Masses (10^10 M☉) et concentrations : en-tête de centres_reference.npz, ordre du fichier.
constexpr double kMass[kN] = {134.3, 106.5, 40.81, 13.79, 0.3};
constexpr double kConc[kN] = {11.908, 13.093, 9.396, 10.0, 10.0};
constexpr double kSoftKpc = 20.0, kMergeKpc = 20.0;
constexpr int kSmc = 4;

struct Settings {
    double massFactor = 1.0;      // masses des halos (surtout de la matière noire), en fois les valeurs de la table
    double K = 0.0674 * 0.0674 * 0.685;      // énergie noire H0² Ω_Λ, (km/s)²/kpc²
};

struct Result {
    std::vector<double> tGa;                          // depuis aujourd'hui
    std::vector<std::array<phys::Vec3, kN>> pos;      // relatives à la Voie lactée, kpc
    double mergeM31Ga = -1;                           // fusion Voie lactée–Andromède ; -1 : pas avant la fin
    double periM31Ga = -1, periM31Kpc = 0;            // premier passage au plus près
    bool ok = false;
};

namespace detail {
struct Halo { double rs, r200, vmax; };
inline Halo nfw(double m, double c) {
    const double M = m * 1e10, r200 = std::cbrt(3 * M / (4 * 3.14159265358979323846 * 200 * kRhoC)), rs = r200 / c;
    auto g = [](double x) { return std::log1p(x) - x / (1 + x); };
    const double xm = 2.1625815870646098;
    return {rs, r200, std::sqrt(4.30091727e-6 * M / r200 * c * g(xm) / (g(c) * xm))};
}
}  // namespace detail

// Rejoue de aujourd'hui à `untilGa` (au plus la fin du fichier) ; un point gardé tous les `keepEvery` pas.
inline Result run(const CentresReference& ref, const Settings& s, double untilGa = 10.0, int keepEvery = 10) {
    using phys::Vec3;
    Result out;
    if (!ref.ready) return out;
    double x[kN][3], v[kN][3], a[kN][3], m[kN];
    detail::Halo halo[kN];
    for (int i = 0; i < kN; ++i) {
        phys::Vec3 p{0, 0, 0}, w{0, 0, 0};
        if (i > 0 && !ref.today(i, p, w)) return out;
        x[i][0] = p.x; x[i][1] = p.y; x[i][2] = p.z;
        v[i][0] = w.x; v[i][1] = w.y; v[i][2] = w.z;
        m[i] = kMass[i] * s.massFactor;
        halo[i] = detail::nfw(m[i], kConc[i]);
    }
    double soft[kN][kN], merge[kN][kN];
    for (int i = 0; i < kN; ++i)
        for (int j = 0; j < kN; ++j) {
            const bool smc = i == kSmc || j == kSmc;
            // Comme matrice_paires : rayons d'échelle des masses de la table (pas des masses réglées), pour que le seul
            // changement soit celui demandé.
            const double rsMean = 0.5 * (detail::nfw(kMass[i], kConc[i]).rs + detail::nfw(kMass[j], kConc[j]).rs);
            soft[i][j] = smc ? std::min(kSoftKpc, rsMean) : kSoftKpc;
            merge[i][j] = smc ? std::min(kMergeKpc, rsMean) : kMergeKpc;
        }
    auto accel = [&]() {
        double mt = 0, cm[3] = {0, 0, 0};
        for (int i = 0; i < kN; ++i) { mt += m[i]; for (int k = 0; k < 3; ++k) cm[k] += m[i] * x[i][k]; }
        for (int i = 0; i < kN; ++i) {
            for (int k = 0; k < 3; ++k) a[i][k] = s.K * (x[i][k] - cm[k] / mt);
            for (int j = 0; j < kN; ++j) {
                if (j == i) continue;
                const double d[3] = {x[j][0] - x[i][0], x[j][1] - x[i][1], x[j][2] - x[i][2]};
                const double r2 = d[0] * d[0] + d[1] * d[1] + d[2] * d[2] + soft[i][j] * soft[i][j], f = kG * m[j] / (r2 * std::sqrt(r2));
                for (int k = 0; k < 3; ++k) a[i][k] += f * d[k];
            }
        }
        // Frottement de Chandrasekhar : la plus légère des deux freine dans le halo de la plus lourde.
        for (int i = 0; i < kN; ++i)
            for (int j = 0; j < kN; ++j) {
                if (i == j || !(m[j] > m[i])) continue;
                const double dr[3] = {x[i][0] - x[j][0], x[i][1] - x[j][1], x[i][2] - x[j][2]};
                const double r = std::max(10.0, std::sqrt(dr[0] * dr[0] + dr[1] * dr[1] + dr[2] * dr[2]));
                if (r >= halo[j].r200) continue;
                const double dv[3] = {v[i][0] - v[j][0], v[i][1] - v[j][1], v[i][2] - v[j][2]};
                const double vv = std::sqrt(dv[0] * dv[0] + dv[1] * dv[1] + dv[2] * dv[2]);
                const double c = kConc[j], gc = std::log1p(c) - c / (1 + c), rs = halo[j].rs;
                const double rho = m[j] / (4 * 3.14159265358979323846 * gc * r * (r + rs) * (r + rs));
                const double xx = r / rs, sig = halo[j].vmax * 1.4393 * std::pow(xx, 0.354) / (1 + 1.1756 * std::pow(xx, 0.725));
                const double y = vv / (std::sqrt(2.0) * sig);
                const double integ = std::erf(y) - 2 * y / std::sqrt(3.14159265358979323846) * std::exp(-y * y);
                const double rsi = halo[i].rs, eps = rsi > 8.0 ? 2.2 * rsi - 14 : 0.45 * rsi;
                const double mag = 4 * 3.14159265358979323846 * kG * kG * std::log(std::max(r / eps, 1.0)) * m[i] * rho * integ / std::pow(std::max(vv, 5.0), 3);
                const double tot = m[i] + m[j];
                for (int k = 0; k < 3; ++k) {
                    a[i][k] -= dv[k] * mag * m[j] / tot;
                    a[j][k] += dv[k] * mag * m[i] / tot;
                }
            }
    };
    const double h = kStepGa / kUnitGa;
    const long steps = static_cast<long>(std::lround(std::min(untilGa, ref.lastGa()) / kStepGa));
    auto keep = [&](double t) {
        std::array<Vec3, kN> p;
        for (int i = 0; i < kN; ++i) p[i] = {x[i][0] - x[0][0], x[i][1] - x[0][1], x[i][2] - x[0][2]};
        out.tGa.push_back(t);
        out.pos.push_back(p);
    };
    accel();
    keep(0.0);
    double prevD = 1e300, prevPrevD = 1e300;
    for (long n = 1; n <= steps; ++n) {
        for (int i = 0; i < kN; ++i) for (int k = 0; k < 3; ++k) { v[i][k] += a[i][k] * h / 2; x[i][k] += v[i][k] * h; }
        accel();
        for (int i = 0; i < kN; ++i) for (int k = 0; k < 3; ++k) v[i][k] += a[i][k] * h / 2;
        const double t = n * kStepGa;
        const double d = std::sqrt((x[1][0] - x[0][0]) * (x[1][0] - x[0][0]) + (x[1][1] - x[0][1]) * (x[1][1] - x[0][1]) + (x[1][2] - x[0][2]) * (x[1][2] - x[0][2]));
        if (out.mergeM31Ga < 0 && d < merge[1][0]) out.mergeM31Ga = t;
        if (out.periM31Ga < 0 && prevD <= prevPrevD && prevD < d) { out.periM31Ga = t - kStepGa; out.periM31Kpc = prevD; }
        prevPrevD = prevD;
        prevD = d;
        if (n % keepEvery == 0) keep(t);
    }
    out.ok = true;
    return out;
}

}  // namespace scenario
