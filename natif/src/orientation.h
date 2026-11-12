// Appli PC « Univers » : orientation des astres dans l'espace (axe de rotation et méridien d'origine).
//
// Modèle de l'UAI (Working Group on Cartographic Coordinates and Rotational Elements ; Archinal et al. 2018,
// Celestial Mechanics and Dynamical Astronomy 130, 22) : direction du pôle nord (ascension droite a0, déclinaison
// d0, repère ICRF) et angle W du méridien d'origine, fonctions linéaires du temps. Les petits termes périodiques
// (nutation, librations) ne sont pas repris : quelques degrés au plus pour la Lune, bien moins pour les planètes.
// [Probable : coefficients recopiés de mémoire. Contrôlés ici pour la Terre (point où le Soleil est au zénith)
//  et pour la Lune (face tournée vers la Terre) par essai_orientation ; les autres astres ne sont pas contrôlés.]
#pragma once
#include <cmath>

#include "ephemeride.h"

namespace ori {

constexpr double kDeg = 3.14159265358979323846 / 180.0;

struct Elements {
    int naif;
    double a0, a0Rate;      // degrés, degrés par siècle julien
    double d0, d0Rate;
    double w0, wRate;       // degrés, degrés par jour
};

constexpr Elements kElements[] = {
    {eph::kSun, 286.13, 0, 63.87, 0, 84.176, 14.1844000},
    {eph::kMercury, 281.0103, -0.0328, 61.4155, -0.0049, 329.5988, 6.1385108},
    {eph::kVenus, 272.76, 0, 67.16, 0, 160.20, -1.4813688},
    {eph::kEarth, 0.0, -0.641, 90.0, -0.557, 190.147, 360.9856235},
    {eph::kMoon, 269.9949, 0.0031, 66.5392, 0.0130, 38.3213, 13.17635815},
    {eph::kMarsBary, 317.269202, -0.10927547, 54.432516, -0.05827105, 176.049863, 350.891982443297},
    {eph::kJupiterBary, 268.056595, -0.006499, 64.495303, 0.002413, 284.95, 870.5360000},
    {eph::kSaturnBary, 40.589, -0.036, 83.537, -0.004, 38.90, 810.7939024},
    {eph::kUranusBary, 257.311, 0, -15.175, 0, 203.81, -501.1600928},
    {eph::kNeptuneBary, 299.36, 0, 43.46, 0, 249.978, 541.1397757},
    {eph::kPlutoBary, 132.993, 0, -6.163, 0, 302.695, 56.3625225},
};

struct Mat3 {
    double m[3][3];
};

// Matrice qui fait passer du repère écliptique J2000 au repère lié à l'astre (x : méridien d'origine sur l'équateur,
// z : pôle nord). days : jours TDB depuis J2000,0. Rend false si l'astre n'a pas d'éléments.
inline bool eclipticToBody(int naif, double days, Mat3& out) {
    for (const auto& e : kElements) {
        if (e.naif != naif) continue;
        const double T = days / 36525.0;
        const double a = (e.a0 + e.a0Rate * T) * kDeg, d = (e.d0 + e.d0Rate * T) * kDeg, w = std::fmod(e.w0 + e.wRate * days, 360.0) * kDeg;
        // Axes de l'astre exprimés dans le repère ICRF : pôle, puis nœud de l'équateur de l'astre sur l'équateur ICRF.
        const double pole[3] = {std::cos(d) * std::cos(a), std::cos(d) * std::sin(a), std::sin(d)};
        const double node[3] = {-std::sin(a), std::cos(a), 0};                                          // direction a0 + 90°
        const double third[3] = {pole[1] * node[2] - pole[2] * node[1], pole[2] * node[0] - pole[0] * node[2], pole[0] * node[1] - pole[1] * node[0]};
        double x[3], y[3];
        for (int k = 0; k < 3; ++k) {
            x[k] = std::cos(w) * node[k] + std::sin(w) * third[k];      // méridien d'origine : W compté depuis le nœud, vers l'est
            y[k] = -std::sin(w) * node[k] + std::cos(w) * third[k];
        }
        // ICRF -> écliptique pour chaque axe, puis lignes de la matrice = axes de l'astre.
        const double c = std::cos(eph::kObliquityJ2000), s = std::sin(eph::kObliquityJ2000);
        auto ecl = [&](const double* v, double* o) {
            o[0] = v[0];
            o[1] = c * v[1] + s * v[2];
            o[2] = -s * v[1] + c * v[2];
        };
        ecl(x, out.m[0]);
        ecl(y, out.m[1]);
        ecl(pole, out.m[2]);
        return true;
    }
    return false;
}

// Longitude (est positif) et latitude, en degrés, du point de l'astre situé sous une direction donnée (repère écliptique).
inline void subPoint(const Mat3& m, double dx, double dy, double dz, double& lonDeg, double& latDeg) {
    const double bx = m.m[0][0] * dx + m.m[0][1] * dy + m.m[0][2] * dz, by = m.m[1][0] * dx + m.m[1][1] * dy + m.m[1][2] * dz,
                 bz = m.m[2][0] * dx + m.m[2][1] * dy + m.m[2][2] * dz;
    const double n = std::sqrt(bx * bx + by * by + bz * bz);
    lonDeg = std::atan2(by, bx) / kDeg;
    latDeg = std::asin(bz / n) / kDeg;
}

}  // namespace ori
