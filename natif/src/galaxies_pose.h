// Appli PC « Univers » : pose propre aux galaxies, aux échelles des amas et des superamas (20 novembre 2026).
//
// Marc, 20/11/2026 : « Laniakea, quasi aucune galaxie, c'est vide ». Mesuré (captures avant, docs/espace-peuple.md) : les
// 18,3 millions de galaxies et quasars de galaxies.bin sont bien dessinés, mais avec leur éclat réel en 1/d² sous la pose
// des étoiles. Vues de 100 millions d'années-lumière, une galaxie comme la Voie lactée est un point de magnitude ~11 :
// presque noir à l'écran. La pose automatique de l'écran (pose_auto.h) ne suffit pas : elle s'arrête dès que les repères
// (Laniakea, vides, noms) éclairent un peu l'écran.
//
// Comme une longue pose photo réservée aux galaxies : la pose des galaxies monte avec la distance de vue (distance de la
// caméra à l'astre suivi), voir gain(). Les éclats RELATIFS restent les vrais (luminosité, distance, 1/d²) : une
// galaxie deux fois plus loin que le point regardé reste quatre fois plus faible. Rien n'est ajouté ni déplacé ; seule la
// pose change, et elle est écrite à l'écran (interface_bas.h).
#pragma once
#include <algorithm>

namespace galaxies_pose {

// Réglage d'après les captures du 20/11 (docs/espace-peuple.md), gains essayés 30 à 30 000 : la pose monte comme le carré
// de la distance de vue à partir de 10 millions d'années-lumière (au-delà du Groupe local, où l'éclat réel des galaxies
// voisines est déjà bien visible), jusqu'à ×150 vers 120 millions d'années-lumière, puis ne monte plus : de plus loin,
// le nombre de galaxies dans le champ suffit à les montrer (à ×300 et plus, la vue de Laniakea et celle de l'univers
// entier saturaient en blanc).
constexpr double kDebut = 1.0e7;
constexpr double kMax = 150.0;

// Pose voulue pour les galaxies à cette distance de vue (1 jusqu'à kDebut).
inline double gain(double dist) {
    const double r = dist / kDebut;
    return std::clamp(r * r, 1.0, kMax);
}

// Facteur à appliquer à l'exposition des galaxies, en plus de la pose de l'écran (qui multiplie toute l'image) : la pose
// totale des galaxies vaut max(pose de l'écran, gain), ou pose × gain quand la pose de l'écran est baissée. Près de la
// Voie lactée, gain = 1 : rien ne change.
inline double facteur(double dist, double poseEcran) {
    // Pose de l'écran baissée (image saturée) : les galaxies baissent avec elle, sinon leur part montait d'autant et
    // l'image ne cessait de saturer (mesuré : pose de l'écran ×0,001, galaxies ×134 000 vues de Laniakea).
    const double g = gain(dist);
    return std::max(1.0, g / std::max(poseEcran, 1.0));
}

}  // namespace galaxies_pose
