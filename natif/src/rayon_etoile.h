// Appli PC « Univers » : rayon d'une étoile CALCULÉ d'après son éclat et sa couleur (audit E3, 20/11/2026 : une étoile vue
// de près restait un point de 14 px, alors que la caméra peut s'en approcher à 1 000 km). Sans dépendance au reste de
// l'appli, contrôlé par essai_interface.
//
//   Température : d'après l'indice B-V, formule de Ballesteros (2012, EPL 97, 34009), déjà utilisée pour la couleur (commun.h).
//   Correction bolométrique BC_V(T) : polynômes de Flower (1996), coefficients corrigés de Torres (2010, AJ 140, 1158).
//   Luminosité : M_bol = M_V + BC_V, L/L☉ = 10^(-0,4 (M_bol - 4,74)) (UAI 2015, M_bol☉ = 4,74).
//   Rayon : loi de Stefan-Boltzmann, R/R☉ = √(L/L☉) (5 772 K / T)² (T☉ : UAI 2015).
// Approché : la couleur B-V donne mal la température des étoiles rougies par la poussière ou très froides ; l'écran dit
// « calculé, approché ».
#pragma once
#include <algorithm>
#include <cmath>

namespace rayon_etoile {

constexpr double kTsoleil = 5772.0;       // K (UAI 2015, résolution B3)
constexpr double kMbolSoleil = 4.74;      // UAI 2015, résolution B2
constexpr double kRsoleilKm = 695700.0;   // UAI 2015, résolution B3

inline double temperatureBv(double bv) { return 4600.0 * (1.0 / (0.92 * bv + 1.7) + 1.0 / (0.92 * bv + 0.62)); }

inline double correctionBolometrique(double teff) {
    const double l = std::log10(teff);
    if (l < 3.70) return -0.190537291496456e5 + l * (0.155144866764412e5 + l * (-0.421278819301717e4 + l * 0.381476328422343e3));
    if (l < 3.90)
        return -0.370510203809015e5 + l * (0.385672629965804e5 + l * (-0.150651486316025e5 + l * (0.261724637119416e4 + l * -0.170623810323864e3)));
    return -0.118115450538963e6 +
           l * (0.137145973583929e6 + l * (-0.636233812100225e5 + l * (0.147412923562646e5 + l * (-0.170587278406872e4 + l * 0.788731721804990e2))));
}

// Rayon (km) d'une étoile de magnitude absolue V et d'indice B-V donnés ; 0 si les valeurs n'ont pas de sens.
inline double rayonKm(double absMagV, double bv) {
    if (!std::isfinite(absMagV) || !std::isfinite(bv) || bv < -0.5 || bv > 3.5) return 0.0;
    const double t = temperatureBv(bv);
    const double mbol = absMagV + correctionBolometrique(t);
    const double l = std::pow(10.0, -0.4 * (mbol - kMbolSoleil));
    const double r = std::sqrt(l) * (kTsoleil / t) * (kTsoleil / t);
    return r > 0 && r < 5000.0 ? r * kRsoleilKm : 0.0;
}

}  // namespace rayon_etoile
