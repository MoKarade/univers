// GÉNÉRÉ par pipeline/constantes/construire.py depuis pipeline/constantes/table_source.py : ne pas éditer.
// Table unique des constantes (étape 0 du plan B+, docs/refonte-simulations-pro.md ; sources dans univers.json).
// Pas encore branché dans l'appli : galaxie_orbites.h garde kR0 et kV0 (voir docs/table-unique.md).
#pragma once

namespace univers::constantes {

constexpr double kR0 = 8.2;
constexpr double kV0 = 232.8;
constexpr double kSgra[3] = {0.9999992, -0.00097327, -0.00080564};
constexpr double kSoleilPos[3] = {-8.199993, 0.007981, 0.006606};
constexpr double kSoleilVit[3] = {11.1, 245.04, 7.25};

constexpr double kH0 = 67.4;
constexpr double kOmegaM = 0.315;
constexpr double kOmegaLambda = 0.685;
constexpr double kKLambda = 0.00311179;      // (km/s)²/kpc²

struct Galaxie {
    const char* cle;
    double masse;            // M☉, centre de la loi de masse (= masse du modèle quand il existe)
    double masseSigma;
    double pos[3], vit[3];   // aujourd'hui, repère phys::galaxie (kpc, km/s)
    double axe[3];           // moment cinétique du disque (unitaire) ; 0 si inconnu
};

constexpr int kNbGalaxies = 5;
constexpr Galaxie kGalaxies[kNbGalaxies] = {
    {"voie_lactee", 1343000000000.0, 300000000000.0, {0.0, 0.0, 0.0}, {0.0, 0.0, 0.0}, {0.0, 0.0, -1.0}},
    {"andromede", 1065000000000.0, 250000000000.0, {-374.5444, 605.5266, -279.8164}, {31.921, -103.866, 43.602}, {-0.4102, -0.7623, -0.5007}},
    {"triangle", 408100000000.0, 100000000000.0, {-514.3047, 531.2809, -446.6603}, {3.068, 97.67, 185.697}, {0.1886, 0.968, -0.1654}},
    {"grand_nuage", 137900000000.0, 25000000000.0, {-0.6361, -40.9421, -26.9214}, {-39.656, -226.468, 227.159}, {-0.2778, -0.949, -0.1489}},
    {"petit_nuage", 3000000000.0, 1000000000.0, {16.0026, -37.5514, -43.5956}, {3.136, -160.06, 143.312}, {0.0, 0.0, 0.0}},
};

}  // namespace univers::constantes
