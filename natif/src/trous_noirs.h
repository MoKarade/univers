// Appli PC « Univers » : trous noirs à masse et distance mesurées (lentille.h pour la lumière déviée, simulation.h pour
// les trouver et y aller). Rien d'autre ici que les valeurs publiées et leur source.
#pragma once
#include "commun.h"

namespace lentille {

constexpr double kPcLy = 3.2615637769;
// Trous noirs à masse mesurée. Coordonnées ICRS lues dans SIMBAD (miroir simbad.harvard.edu, 13/11/2026).
struct Hole {
    const char* name;
    double raDeg, decDeg, distPc, massSun;
    const char* source;
};
inline const Hole kHoles[] = {
    {"Sgr A* (centre de la Voie lactée)", 266.41683, -29.00782, 8277.0, 4.297e6, "GRAVITY Collaboration 2022 : 4,297 millions de masses solaires, 8,277 kpc"},
    {"M87* (galaxie M87)", 187.70593, 12.39112, 16.8e6, 6.5e9, "Event Horizon Telescope 2019 : 6,5 milliards de masses solaires, 16,8 Mpc"},
    {"Gaia BH1", 262.17124, -0.58098, 480.0, 9.62, "El-Badry et al. 2023 : 9,62 masses solaires, 480 pc"},
    {"Gaia BH2", 207.56978, -59.23898, 1160.0, 8.94, "El-Badry et al. 2023 : 8,94 masses solaires, 1,16 kpc"},
    {"Gaia BH3", 294.82797, 14.93167, 590.0, 32.70, "Gaia Collaboration 2024 : 32,7 masses solaires, 590 pc"},
    {"Cygnus X-1", 299.59032, 35.20161, 2220.0, 21.2, "Miller-Jones et al. 2021 : 21,2 masses solaires, 2,22 kpc"},
};

// Repère de l'appli : écliptique J2000, années-lumière, origine au Soleil (obliquité 84 381,448″, comme ephemeride.h).
inline Vec3 icrsToEcl(double raDeg, double decDeg, double distLy) {
    const double a = raDeg * kPi / 180.0, d = decDeg * kPi / 180.0, e = 84381.448 / 3600.0 * kPi / 180.0;
    const double x = std::cos(d) * std::cos(a), y = std::cos(d) * std::sin(a), z = std::sin(d);
    return {distLy * x, distLy * (std::cos(e) * y + std::sin(e) * z), distLy * (-std::sin(e) * y + std::cos(e) * z)};
}

}  // namespace lentille
