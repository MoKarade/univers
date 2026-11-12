// Appli PC « Univers », bibliothèque univers_physique : la Lune hors de la plage DE440.
// Théorie de Meeus (Astronomical Algorithms, chap. 47, d'après ELP-2000/82 de Chapront), la même que la page
// (app/src/20_physics.js, moonMeeus) ; coordonnées de la date ramenées à l'écliptique J2000 par la précession UAI 1976.
// Plage : de −2000 à +6000 (±4 000 ans autour de J2000) ; au-delà, false : l'accélération de marée de la Lune et l'écart
// entre temps des éphémérides et temps civil rendent sa position inconnue. Contrôle : essai_lune (contre DE440).
#pragma once
#include <cmath>

#include "lune_donnees.h"
#include "phys.h"

namespace phys::lune {

constexpr double kJd2000 = 2451545.0;
constexpr double kSiecles = 40.0;      // ±4 000 ans
// Fraction de la masse du système Terre-Lune portée par la Lune (DE440) : Terre = barycentre − f · (Lune − Terre).
constexpr double kFractionLune = 1.0931894624024351e-11 / (8.8876924467071033e-10 + 1.0931894624024351e-11);

// Précession UAI 1976 : écliptique de la date -> écliptique J2000 (matrice 3 × 3).
inline void precession(double T, double m[9]) {
    constexpr double as = 3.14159265358979323846 / 648000, e0 = 84381.448 * as;
    const double ze = (2306.2181 * T + 0.30188 * T * T + 0.017998 * T * T * T) * as, z = (2306.2181 * T + 1.09468 * T * T + 0.018203 * T * T * T) * as, th = (2004.3109 * T - 0.42665 * T * T - 0.041833 * T * T * T) * as;
    const double cz = std::cos(ze), sz = std::sin(ze), cZ = std::cos(z), sZ = std::sin(z), ct = std::cos(th), st = std::sin(th);
    const double P[9] = {cz * ct * cZ - sz * sZ, -sz * ct * cZ - cz * sZ, -st * cZ, cz * ct * sZ + sz * cZ, -sz * ct * sZ + cz * cZ, -st * sZ, cz * st, -sz * st, ct};
    const double ed = (84381.448 - 46.8150 * T - 0.00059 * T * T + 0.001813 * T * T * T) * as, ce = std::cos(ed), se = std::sin(ed), c0 = std::cos(e0), s0 = std::sin(e0);
    const double A[9] = {P[0], P[3] * ce + P[6] * se, -P[3] * se + P[6] * ce, P[1], P[4] * ce + P[7] * se, -P[4] * se + P[7] * ce, P[2], P[5] * ce + P[8] * se, -P[5] * se + P[8] * ce};
    m[0] = A[0]; m[1] = A[1]; m[2] = A[2]; m[3] = c0 * A[3] + s0 * A[6]; m[4] = c0 * A[4] + s0 * A[7]; m[5] = c0 * A[5] + s0 * A[8]; m[6] = -s0 * A[3] + c0 * A[6]; m[7] = -s0 * A[4] + c0 * A[7]; m[8] = -s0 * A[5] + c0 * A[8];
}

// Position géocentrique de la Lune (km, écliptique J2000) à jd (TDB). false hors de ±4 000 ans.
inline bool geocentrique(double jd, Vec3& out) {
    const double T = (jd - kJd2000) / 36525; if (!(std::fabs(T) <= kSiecles)) return false;
    constexpr double D2R = 3.14159265358979323846 / 180;
    const double T2 = T * T, T3 = T2 * T, T4 = T3 * T; auto r = [](double x) { return std::fmod(x, 360.0) * D2R; };
    const double Lp = 218.3164477 + 481267.88123421 * T - 0.0015786 * T2 + T3 / 538841 - T4 / 65194000;
    const double D = 297.8501921 + 445267.1114034 * T - 0.0018819 * T2 + T3 / 545868 - T4 / 113065000;
    const double M = 357.5291092 + 35999.0502909 * T - 0.0001536 * T2 + T3 / 24490000;
    const double Mp = 134.9633964 + 477198.8675055 * T + 0.0087414 * T2 + T3 / 69699 - T4 / 14712000;
    const double F = 93.2720950 + 483202.0175233 * T - 0.0036539 * T2 - T3 / 3526000 + T4 / 863310000;
    const double A1 = 119.75 + 131.849 * T, A2 = 53.09 + 479264.290 * T, A3 = 313.45 + 481266.484 * T, E = 1 - 0.002516 * T - 0.0000074 * T2, E2 = E * E;
    double sl = 0, sr = 0, sb = 0;
    for (size_t i = 0; i < sizeof(lune_donnees::kLr) / sizeof(double); i += 6) {
        const double* t = &lune_donnees::kLr[i]; const double a = r(t[0] * D + t[1] * M + t[2] * Mp + t[3] * F); const int m = (int)std::fabs(t[1]); const double ef = m == 1 ? E : m == 2 ? E2 : 1;
        sl += t[4] * ef * std::sin(a); sr += t[5] * ef * std::cos(a);
    }
    for (size_t i = 0; i < sizeof(lune_donnees::kB) / sizeof(double); i += 5) {
        const double* t = &lune_donnees::kB[i]; const double a = r(t[0] * D + t[1] * M + t[2] * Mp + t[3] * F); const int m = (int)std::fabs(t[1]); const double ef = m == 1 ? E : m == 2 ? E2 : 1;
        sb += t[4] * ef * std::sin(a);
    }
    sl += 3958 * std::sin(r(A1)) + 1962 * std::sin(r(Lp - F)) + 318 * std::sin(r(A2));
    sb += -2235 * std::sin(r(Lp)) + 382 * std::sin(r(A3)) + 175 * std::sin(r(A1 - F)) + 175 * std::sin(r(A1 + F)) + 127 * std::sin(r(Lp - Mp)) - 115 * std::sin(r(Lp + Mp));
    const double lam = r(Lp + sl / 1e6), bet = (sb / 1e6) * D2R, d = 385000.56 + sr / 1000, cb = std::cos(bet);
    const double x = d * cb * std::cos(lam), y = d * cb * std::sin(lam), z = d * std::sin(bet);
    double P[9]; precession(T, P);
    out = {P[0] * x + P[1] * y + P[2] * z, P[3] * x + P[4] * y + P[5] * z, P[6] * x + P[7] * y + P[8] * z};
    return true;
}

}  // namespace phys::lune
