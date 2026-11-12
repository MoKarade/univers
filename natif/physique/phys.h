// Appli PC « Univers », bibliothèque univers_physique : types communs de l'interface (convenus avec le fil de l'appli).
// Temps : jour julien TDB (double). Repère : écliptique J2000 (obliquité 84 381,448″), héliocentrique, km et km/s.
// Corps : codes NAIF. Une fonction répond false quand la position est inconnue : jamais d'extrapolation silencieuse.
#pragma once

namespace phys {

struct Vec3 {
    double x = 0, y = 0, z = 0;
};

// Mesure : donné par une mesure (éphéméride publiée) ; Calcule : calculé ici à partir des mesures.
enum class Statut { Mesure, Calcule };

struct Plage {
    double debut = 0, fin = 0;      // jours juliens TDB
    bool contient(double jd) const { return jd >= debut && jd <= fin; }
};

constexpr double kAuKm = 149597870.7;
constexpr double kJourS = 86400.0;

// Codes NAIF des corps du calcul du système solaire.
enum Naif : int {
    kSoleil = 10, kMercure = 1, kVenus = 2, kTerreLune = 3, kMars = 4, kJupiter = 5, kSaturne = 6, kUranus = 7, kNeptune = 8, kPluton = 9,
    kCeres = 2000001, kPallas = 2000002, kVesta = 2000004, kHygie = 2000010
};

}  // namespace phys
