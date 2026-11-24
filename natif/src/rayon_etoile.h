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
//
// Naines rouges (M0V à M9,5V : B-V > 1,3 et M_V ≥ 8,8) : sous 3 500 K, la correction bolométrique de Flower est faible et
// le calcul ci-dessus sous-estimait le rayon de moitié (Proxima : 0,075 R☉ contre 0,154 mesuré). Pour elles, le rayon est
// lu dans la séquence moyenne des naines de Pecaut et Mamajek (2013, ApJS 208, 9, table 5 ; version 2022.04.16 de la table
// d'E. Mamajek, colonnes Mv et R_Rsun), interpolé sur M_V.
#pragma once
#include <algorithm>
#include <cmath>

namespace rayon_etoile {

constexpr double kTsoleil = 5772.0;       // K (UAI 2015, résolution B3)
constexpr double kMbolSoleil = 4.74;      // UAI 2015, résolution B2
constexpr double kRsoleilKm = 695700.0;   // UAI 2015, résolution B3

// Séquence des naines M (Mamajek 2022.04.16) : magnitude absolue V et rayon (R☉), de M0V à M9,5V.
constexpr double kNainesMv[] = {8.80, 9.20, 9.64, 9.85, 10.21, 10.61, 11.15, 12.10, 12.61, 13.58, 14.15, 15.30, 16.32, 17.10, 17.70, 18.16, 18.60, 19.20, 19.40, 19.75};
constexpr double kNainesR[] = {0.588, 0.544, 0.501, 0.482, 0.446, 0.421, 0.361, 0.300, 0.274, 0.217, 0.196, 0.156, 0.137, 0.126, 0.120, 0.116, 0.114, 0.104, 0.102, 0.101};
inline double rayonNaineM(double mv) {
    constexpr int n = sizeof(kNainesMv) / sizeof(kNainesMv[0]);
    if (mv >= kNainesMv[n - 1]) return kNainesR[n - 1];
    for (int k = 1; k < n; ++k)
        if (mv <= kNainesMv[k]) {
            const double f = (mv - kNainesMv[k - 1]) / (kNainesMv[k] - kNainesMv[k - 1]);
            return kNainesR[k - 1] + f * (kNainesR[k] - kNainesR[k - 1]);
        }
    return kNainesR[0];
}

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
    if (bv > 1.3 && absMagV >= kNainesMv[0]) return rayonNaineM(absMagV) * kRsoleilKm;      // naine rouge : séquence mesurée
    const double t = temperatureBv(bv);
    const double mbol = absMagV + correctionBolometrique(t);
    const double l = std::pow(10.0, -0.4 * (mbol - kMbolSoleil));
    const double r = std::sqrt(l) * (kTsoleil / t) * (kTsoleil / t);
    return r > 0 && r < 5000.0 ? r * kRsoleilKm : 0.0;
}

}  // namespace rayon_etoile
