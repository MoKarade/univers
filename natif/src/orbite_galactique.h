// Appli PC « Univers » : le mouvement de chaque étoile autour du centre de la Galaxie, à toute date, sans coupure.
//
// Demande de Marc (12 novembre 2026) : « je veux voir tout le temps pour chaque astre ce qu'il fait réellement, peu
// importe le temps ». Avant : ligne droite à la vitesse mesurée jusqu'à 3 millions d'années, puis les étoiles
// disparaissaient au profit du calcul de la fusion. Maintenant, une seule formule pour toute date :
//   - départ : la position et la vitesse MESURÉES de l'étoile ;
//   - ensuite : son orbite CALCULÉE dans la Galaxie (méthode des épicycles : un cercle autour du centre, plus une petite
//     oscillation en distance et en hauteur), avec les fréquences de phys::galaxie::frequences (potentiel [modèle] du fil
//     physique : bulbe + disque + halo, 232,8 km/s au Soleil) ;
//   - raccord sans seuil : poids 1 − exp(−(t / 300 000 ans)²) entre la ligne droite mesurée (exacte aux temps courts) et
//     l'orbite (qui prend le relais ensuite). À aucune date le mouvement ne s'arrête ni ne saute.
// Limites, dites à l'écran : la méthode vaut pour les étoiles du disque sur orbite presque ronde ; l'oscillation est bornée
// à 80 % du rayon de l'orbite pour les autres (halo, bulbe) ; la barre centrale n'est pas prise en compte ici.
// Repère : le monde du simulateur reste centré sur le Soleil (qui tourne lui aussi) ; ce qui est fixe par rapport au
// centre de la Galaxie se déplace donc en sens inverse du Soleil (decalageSoleil).
// Le même calcul est écrit pour la carte graphique dans shaders/orbite_galactique.glsl ; essai_orbite.cpp contrôle que les
// constantes des deux sont les mêmes et mesure l'écart avec l'intégration exacte du fil physique.
#pragma once
#include <algorithm>
#include <cmath>

#include "commun.h"
#include "galaxie_orbites.h"

namespace orbite {

constexpr double kKpcLy = 3261.5637769;
constexpr double kRaccordAns = 3.0e5;      // échelle du raccord ligne droite -> orbite
constexpr double kAmplitudeMax = 0.8;      // oscillation radiale bornée à cette part du rayon de l'orbite
// Repère galactocentrique -> écliptique (DATA.M_GAL2ECL de la page), comme Sim::fromGalactocentric.
constexpr double kM[3][3] = {{-0.0548756577, 0.4941094372, -0.8676661376}, {-0.993821367, -0.1109908412, -0.0003515418}, {-0.0964766946, 0.8622858559, 0.4971472117}};

inline phys::Vec3 versGalactique(Vec3 e) {      // écliptique -> axes galactocentriques (matrice transposée)
    return {kM[0][0] * e.x + kM[1][0] * e.y + kM[2][0] * e.z, kM[0][1] * e.x + kM[1][1] * e.y + kM[2][1] * e.z, kM[0][2] * e.x + kM[1][2] * e.y + kM[2][2] * e.z};
}
inline Vec3 versEcliptique(phys::Vec3 g) {
    return {kM[0][0] * g.x + kM[0][1] * g.y + kM[0][2] * g.z, kM[1][0] * g.x + kM[1][1] * g.y + kM[1][2] * g.z, kM[2][0] * g.x + kM[2][1] * g.y + kM[2][2] * g.z};
}

// Position galactocentrique (kpc) à tGa d'une étoile partie de g (kpc) à la vitesse v (km/s) : épicycles.
inline phys::Vec3 epicycle(phys::Vec3 g, phys::Vec3 v, double tGa) {
    const double R = std::max(std::sqrt(g.x * g.x + g.y * g.y), 1e-6);
    const double lz = g.x * v.y - g.y * v.x, sens = lz < 0 ? -1.0 : 1.0;
    double vR = (g.x * v.x + g.y * v.y) / R;
    double rg = R;
    for (int i = 0; i < 6; ++i) rg = std::max(std::fabs(lz) / phys::galaxie::frequences(rg).vc, 0.05);      // rayon du cercle de même moment
    const phys::galaxie::Frequences f = phys::galaxie::frequences(rg);
    double x = R - rg;
    const double amp = std::sqrt(x * x + (vR / f.kappa) * (vR / f.kappa)), maxAmp = kAmplitudeMax * rg;
    if (amp > maxAmp) {
        x *= maxAmp / amp;
        vR *= maxAmp / amp;
    }
    const double a = std::min(amp, maxAmp), alpha = std::atan2(-vR / f.kappa, x);
    const double k = phys::galaxie::kKmsKpcToRadGa * tGa, psi = f.kappa * k + alpha;
    const double Rt = rg + a * std::cos(psi);
    // Angle autour du centre : le moment cinétique se conserve, donc dφ/dt = Lz / R(t)² ; avec R(t) = rg (1 + e cos ψ),
    // l'intégrale est exacte (même forme que le mouvement d'une planète) : la vitesse de départ est celle mesurée.
    const double e = a / rg, q = 1.0 - e * e, beta = e / (1.0 + std::sqrt(q));
    const auto F = [&](double u) {
        const double E = u - 2.0 * std::atan2(beta * std::sin(u), 1.0 + beta * std::cos(u));
        return E / (q * std::sqrt(q)) - e * std::sin(u) / (q * (1.0 + e * std::cos(u)));
    };
    const double phi = std::atan2(g.y, g.x) + sens * (f.omega / f.kappa) * (F(psi) - F(alpha));
    const double z = g.z * std::cos(f.nu * k) + v.z / f.nu * std::sin(f.nu * k);
    return {Rt * std::cos(phi), Rt * std::sin(phi), z};
}

inline double poidsOrbite(double years) { return 1.0 - std::exp(-(years / kRaccordAns) * (years / kRaccordAns)); }

// Le Soleil à tGa moins le Soleil aujourd'hui (kpc, axes galactocentriques).
inline phys::Vec3 soleilDeplace(double tGa) {
    const phys::Vec3 s = phys::galaxie::soleilPos(), p = epicycle(s, phys::galaxie::soleilVit(), tGa);
    return {p.x - s.x, p.y - s.y, p.z - s.z};
}

// Déplacement (années-lumière, repère du simulateur centré sur le Soleil) d'une étoile depuis aujourd'hui, à `years` ans.
// pos : sa position aujourd'hui (al, par rapport au Soleil) ; vel : sa vitesse mesurée par rapport au Soleil (km/s).
inline Vec3 deplacement(Vec3 pos, Vec3 vel, double years) {
    const double kt = years * kKmsToLyPerYear;
    const Vec3 droit{vel.x * kt, vel.y * kt, vel.z * kt};
    const double w = poidsOrbite(years);
    if (w < 1e-9) return droit;
    const phys::Vec3 s = phys::galaxie::soleilPos(), sv = phys::galaxie::soleilVit();
    const phys::Vec3 pg = versGalactique(pos), vg = versGalactique(vel);
    const phys::Vec3 g{pg.x / kKpcLy + s.x, pg.y / kKpcLy + s.y, pg.z / kKpcLy + s.z}, v{vg.x + sv.x, vg.y + sv.y, vg.z + sv.z};
    const double tGa = years / 1.0e9;
    const phys::Vec3 e = epicycle(g, v, tGa), d = soleilDeplace(tGa);
    const Vec3 orb = versEcliptique({(e.x - g.x - d.x) * kKpcLy, (e.y - g.y - d.y) * kKpcLy, (e.z - g.z - d.z) * kKpcLy});
    return {droit.x * (1.0 - w) + orb.x * w, droit.y * (1.0 - w) + orb.y * w, droit.z * (1.0 - w) + orb.z * w};
}

// Déplacement de ce qui est fixe par rapport au centre de la Galaxie (son centre, les galaxies voisines) : l'opposé du
// chemin du Soleil.
inline Vec3 decalageSoleil(double years) {
    const phys::Vec3 d = soleilDeplace(years / 1.0e9);
    return versEcliptique({-d.x * kKpcLy, -d.y * kKpcLy, -d.z * kKpcLy});
}

}  // namespace orbite
