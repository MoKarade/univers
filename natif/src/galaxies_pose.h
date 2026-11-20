// Appli PC « Univers » : pose propre aux galaxies, aux échelles des amas et des superamas (20 novembre 2026).
//
// Marc, 20/11/2026 : « Laniakea, quasi aucune galaxie, c'est vide ». Mesuré (captures avant, docs/espace-peuple.md) : les
// 18,3 millions de galaxies et quasars de galaxies.bin sont bien dessinés, mais avec leur éclat réel en 1/d² sous la pose
// des étoiles. Vues de 100 millions d'années-lumière, une galaxie comme la Voie lactée est un point de magnitude ~11 :
// presque noir à l'écran. La pose automatique de l'écran (pose_auto.h) ne suffit pas : elle s'arrête dès que les repères
// (Laniakea, vides, noms) éclairent un peu l'écran.
//
// Comme une longue pose photo réservée aux galaxies : la pose des galaxies monte comme le carré de la distance de vue
// (distance de la caméra à l'astre suivi), à partir de kDebut. Une galaxie placée au point regardé garde donc à peu près
// le même éclat quelle que soit l'échelle, et les éclats RELATIFS restent les vrais (luminosité, distance, 1/d²) : une
// galaxie deux fois plus loin que le point regardé reste quatre fois plus faible. Rien n'est ajouté ni déplacé ; seule la
// pose change, et elle est écrite à l'écran (interface_bas.h).
#pragma once
#include <algorithm>
#include <cstdlib>

namespace galaxies_pose {

// Distance de vue (al) à partir de laquelle la pose des galaxies monte : celle du Groupe local, où l'éclat réel des
// galaxies voisines (Andromède, le Triangle) est déjà bien visible sous la pose des étoiles (captures du 20/11).
constexpr double kDebut = 3.0e6;
constexpr double kMax = 1.0e7;      // plafond (vue de 1e11 al : galaxies à z ~ 1, encore visibles en points faibles)

inline double debut() {      // réglable pour les essais (UNIVERS_GAL_D0) ; la valeur retenue est kDebut
    static const double d = [] { const char* e = std::getenv("UNIVERS_GAL_D0"); return e ? std::atof(e) : kDebut; }();
    return d > 0 ? d : kDebut;
}

// Pose voulue pour les galaxies à cette distance de vue (1 jusqu'à kDebut).
inline double gain(double dist) {
    const double r = dist / debut();
    return std::clamp(r * r, 1.0, kMax);
}

// Facteur à appliquer à l'exposition des galaxies, en plus de la pose de l'écran (qui multiplie toute l'image) : la pose
// totale des galaxies vaut max(pose de l'écran, gain). Près de la Voie lactée, gain = 1 : rien ne change.
inline double facteur(double dist, double poseEcran) {
    const double g = gain(dist);
    return poseEcran >= g ? 1.0 : g / std::max(poseEcran, 1.0e-6);
}

}  // namespace galaxies_pose
