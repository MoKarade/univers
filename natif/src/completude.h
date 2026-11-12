// Appli PC « Univers » : ce qui est présent à chaque échelle, comparé à ce qui est connu (complétude, précision, part
// mesurée). Méthode, sources et liste de ce qui manque : docs/completude.md.
//
// Règle de Marc : à l'écran, une donnée est mesurée, calculée ou inconnue. Une estimation publiée (nombre d'étoiles de la
// Voie lactée, de galaxies de l'univers observable) n'est pas une mesure : elle est dite « estimation » à l'écran.
//
// Usage (fil natif et fil interface) :
//   1. au chargement, une fois : completude::Comptes c = completude::compter(sim, galaxies.count);
//                                const auto rapport = completude::rapport(c);
//   2. à chaque image : completude::echellePour(sim.dist) donne l'échelle regardée ; si <imgui.h> est inclus avant ce
//      fichier, completude::ligneCourte(rapport[e]) donne la ligne du coin de l'écran et completude::detail(rapport[e])
//      dessine le détail (à appeler dans une fenêtre ImGui ouverte par l'interface).
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace completude {

enum class Nature { Mesure, Calcule, Ajuste, Suppose, Estimation, Inconnu };

inline const char* motNature(Nature n) {
    switch (n) {
    case Nature::Mesure: return "mesuré";
    case Nature::Calcule: return "calculé";
    case Nature::Ajuste: return "ajusté sur des mesures";
    case Nature::Suppose: return "supposé";
    case Nature::Estimation: return "estimation publiée, non mesurée";
    default: return "inconnu";
    }
}

// ---------------------------------------------------------------- références publiées (relevées le 12 novembre 2026)

constexpr double kAnneeLumiereParParsec = 3.26156;
constexpr double kRayonVoisinageLy = 10.0 * kAnneeLumiereParParsec;          // 10 parsecs
constexpr double kRayonGroupeLocalLy = 1.0e6 * kAnneeLumiereParParsec;       // 1 Mpc, bord habituel du Groupe local
constexpr double kDoublonLy = 0.02;      // deux points de catalogues différents plus proches que ça : probablement la même étoile

// Lunes connues, par planète (JPL, « Planetary Satellite Discovery Circumstances », ssd.jpl.nasa.gov/sats/discovery.html,
// relevé le 12/11/2026 : 460 lunes hors celle de la Terre). Indice : code NAIF du système (3 Terre … 9 Pluton).
constexpr int kLunesConnues[10] = {0, 0, 0, 1, 2, 115, 293, 29, 16, 5};
constexpr int kPlanetesConnues = 9;                       // 8 planètes et Pluton (UAI)
constexpr double kAsteroidesConnus = 1580289;              // JPL SBDB, requête sb-kind=a du 12/11/2026
constexpr double kCometesConnues = 4088;                   // JPL SBDB, requête sb-kind=c du 12/11/2026
constexpr int kSondesSortie = 5;                           // NASA : Pioneer 10 et 11, Voyager 1 et 2, New Horizons (sortie du système solaire)
constexpr double kObjets10pc = 540;                        // Reylé et al. 2021, A&A 650 A201 : étoiles, naines brunes, exoplanètes
constexpr double kSourcesGaiaDr3 = 1811709771;             // ESA, Gaia DR3 (cosmos.esa.int/web/gaia/dr3)
constexpr double kGaiaVitessesRadiales = 25878867;         // gaia.bin du 12/11/2026 : vitesses radiales mesurées (docs/gaia-voie-lactee.md)
constexpr double kEtoilesVoieLacteeMin = 1.0e11, kEtoilesVoieLacteeMax = 4.0e11;   // NASA Goddard (Blueshift) : estimation
constexpr double kGalaxiesGroupeLocal = 113;               // Local Volume Database v1.1.2 (Pace, 04/11/2026) : confirmées, < 1 Mpc
constexpr double kGalaxiesMin = 2.0e11, kGalaxiesMax = 2.0e12;     // Lauer et al. 2021 (centaines de milliards) ; Conselice et al. 2016

// Précision du fichier d'étoiles et de galaxies (pipeline/natif/etoiles.py, galaxies.py) : entiers de 16 bits.
constexpr double kPasLongitudeArcsec = 360.0 * 3600.0 / 65535.0;    // 19,8″
constexpr double kPasLatitudeArcsec = 180.0 * 3600.0 / 65535.0;     // 9,9″
constexpr double kPasDistanceRelatif = 5.5 / 65535.0 * 2.302585093; // log10 sur 5,5 décades (pire des deux catalogues) : 0,019 %
constexpr double kPasDecalageRelatif = 2.0794415417 / 65535.0;       // ln(1 + 7) sur 65 535 pas : Δz = 3,2e-5 × (1 + z)
constexpr double kLumiereKmS = 299792.458;

// ---------------------------------------------------------------- comptes (lus dans ce que l'appli a réellement chargé)

struct Comptes {
    int planetes = 0;                  // planètes et Pluton présents
    int lunes[10] = {};                // lunes présentes, par code NAIF du système (la Lune : indice 3)
    uint64_t asteroides = 0;
    int sondes = 0;                    // sondes dont la trajectoire réelle est chargée
    uint64_t etoiles = 0;
    uint64_t etoilesCatalogue[3] = {}; // principal (HYG / Hipparcos), Gaia embarqué, Gaia en flux
    uint64_t etoilesGaia = 0;          // gaia.bin (Gaia DR3, parallaxe > 10 fois son erreur) quand il est chargé ; 0 sinon
    bool voieLactee = false;           // Voie lactée dessinée en volume (voie_lactee.bin)
    uint64_t etoiles10pc = 0;
    uint64_t doublons10pc = 0;         // paires de deux catalogues différents à moins de kDoublonLy
    uint64_t principalSansVitesseRadiale = 0;      // composante radiale nulle (< 0,2 km/s) : vitesse radiale non mesurée
    int galaxiesGroupeLocal = 0;       // galaxies nommées à moins de 1 Mpc du Soleil
    uint64_t galaxiesReleves = 0;      // galaxies et quasars des relevés (galaxies.bin)
};

inline int lunesPresentes(const Comptes& c) {
    int n = 0;
    for (int v : c.lunes) n += v;
    return n;
}

inline int lunesConnues() {
    int n = 0;
    for (int v : kLunesConnues) n += v;
    return n;
}

// Étoiles : x, y, z en années-lumière, vitesses en km/s, n étoiles ; comptes par catalogue lus dans l'en-tête du fichier.
inline Comptes compterEtoiles(Comptes c, const float* x, const float* y, const float* z, const float* vx, const float* vy, const float* vz,
                              uint64_t n, const uint64_t parCatalogue[3]) {
    c.etoiles = n;
    for (int k = 0; k < 3; ++k) c.etoilesCatalogue[k] = parCatalogue[k];
    std::vector<uint64_t> proches;
    for (uint64_t i = 0; i < n; ++i) {
        const double d = std::sqrt(double(x[i]) * x[i] + double(y[i]) * y[i] + double(z[i]) * z[i]);
        if (d < kRayonVoisinageLy) proches.push_back(i);
        if (i < parCatalogue[0] && d > 0) {
            const double vr = (double(x[i]) * vx[i] + double(y[i]) * vy[i] + double(z[i]) * vz[i]) / d;
            if (std::fabs(vr) < 0.2) ++c.principalSansVitesseRadiale;
        }
    }
    c.etoiles10pc = proches.size();
    const auto catalogue = [&](uint64_t i) { return i < parCatalogue[0] ? 0 : i < parCatalogue[0] + parCatalogue[1] ? 1 : 2; };
    for (size_t a = 0; a < proches.size(); ++a)
        for (size_t b = a + 1; b < proches.size(); ++b) {
            const uint64_t i = proches[a], j = proches[b];
            if (catalogue(i) == catalogue(j)) continue;
            const double dx = x[i] - x[j], dy = y[i] - y[j], dz = z[i] - z[j];
            if (dx * dx + dy * dy + dz * dz < kDoublonLy * kDoublonLy) ++c.doublons10pc;
        }
    return c;
}

// Astres de l'appli (Sim de simulation.h, gardé en paramètre pour ne pas dépendre de ses détails) et fichier d'étoiles.
// etoilesGaia : nombre d'étoiles de gaia.bin (GaiaRenderer::count) ; pris seulement si sim.hasGaia.
template <class SimT>
Comptes compter(const SimT& sim, uint64_t galaxiesReleves, uint64_t etoilesGaia = 0) {
    Comptes c;
    c.etoilesGaia = sim.hasGaia ? etoilesGaia : 0;
    c.voieLactee = sim.hasMilkyWay;
    c.asteroides = sim.asteroidCount;
    c.galaxiesReleves = galaxiesReleves;
    for (const auto& b : sim.bodies) {
        using K = decltype(b.kind);
        // Planète : tourne autour du Soleil (parent -1 ou l'astre Soleil) ; lune : tourne autour d'une planète.
        const bool autourDuSoleil = b.parent < 0 || sim.bodies[static_cast<size_t>(b.parent)].kind == K::Sun;
        if (b.kind == K::Planet && autourDuSoleil) ++c.planetes;
        if (b.kind == K::Planet && !autourDuSoleil) {
            const int systeme = b.naif == 301 ? 3 : b.naif / 100;
            if (systeme >= 0 && systeme < 10) ++c.lunes[systeme];
        }
        if (b.kind == K::Probe) ++c.sondes;
        if (b.kind == K::Galaxy && b.natureText.rfind("centre", 0) != 0) {
            const double d = std::sqrt(b.fixedPos.x * b.fixedPos.x + b.fixedPos.y * b.fixedPos.y + b.fixedPos.z * b.fixedPos.z);
            if (d > 0 && d < kRayonGroupeLocalLy) ++c.galaxiesGroupeLocal;
        }
    }
    if (sim.stars && sim.stars->base) {
        int32_t cat[3];
        std::memcpy(cat, sim.stars->base + 16, sizeof(cat));
        const uint64_t parCatalogue[3] = {uint64_t(cat[0]), uint64_t(cat[1]), uint64_t(cat[2])};
        const auto* s = sim.stars;
        c = compterEtoiles(c, s->x(), s->y(), s->z(), s->vel(0), s->vel(1), s->vel(2), s->n, parCatalogue);
    }
    return c;
}

// ---------------------------------------------------------------- rapport par échelle

struct Ligne {
    std::string quoi, valeur;
    Nature nature;
    std::string source;
};

struct Echelle {
    const char* nom;
    double part = -1;                 // part des objets connus présents (0 à 1) ; -1 : rapportée à une estimation seulement
    std::string complet, precision, mesure;      // les trois chiffres, en une ligne chacun
    std::vector<Ligne> lignes;
    std::vector<std::string> manques;
};

// Nombres écrits à la française : 1 580 289 ; 0,34 %.
inline std::string entier(double v) {
    char b[32];
    std::snprintf(b, sizeof(b), "%.0f", v);
    std::string s = b, out;
    const size_t start = s[0] == '-' ? 1 : 0;
    for (size_t i = 0; i < s.size(); ++i) {
        if (i > start && (s.size() - i) % 3 == 0) out += " ";
        out += s[i];
    }
    return out;
}

inline std::string pourcent(double part) {
    char b[32];
    const double p = part * 100.0;
    if (p >= 10) std::snprintf(b, sizeof(b), "%.0f %%", p);
    else if (p >= 1) std::snprintf(b, sizeof(b), "%.1f %%", p);
    else if (p > 0) std::snprintf(b, sizeof(b), "%.*f %%", std::min(9, int(std::ceil(-std::log10(p))) + 1), p);      /* deux chiffres utiles */
    else std::snprintf(b, sizeof(b), "0 %%");
    std::string s = b;
    for (char& ch : s) if (ch == '.') ch = ',';
    return s;
}

inline std::string sur(double present, double connu) { return entier(present) + " sur " + entier(connu) + " (" + pourcent(present / connu) + ")"; }

inline Echelle systemeSolaire(const Comptes& c) {
    Echelle e;
    e.nom = "Système solaire";
    const double present = c.planetes + lunesPresentes(c) + double(c.asteroides) + c.sondes;
    const double connu = kPlanetesConnues + lunesConnues() + kAsteroidesConnus + kCometesConnues + kSondesSortie;
    e.part = present / connu;
    e.complet = pourcent(e.part) + " des objets connus (" + entier(present) + " sur " + entier(connu) + ")";
    e.precision = "planètes et Soleil < 1 mm ; astéroïdes 25 000 à 93 000 km";
    e.mesure = "positions : éphémérides de la NASA (planètes, lunes) ; calculées ici (astéroïdes)";
    e.lignes = {
        {"Planètes et Pluton", sur(c.planetes, kPlanetesConnues), Nature::Mesure, "UAI"},
        {"Lunes", sur(lunesPresentes(c), lunesConnues()), Nature::Mesure, "JPL, Planetary Satellite Discovery Circumstances, 12/11/2026"},
        {"Astéroïdes", sur(double(c.asteroides), kAsteroidesConnus), Nature::Mesure, "JPL Small-Body Database, 12/11/2026"},
        {"Comètes", sur(0, kCometesConnues), Nature::Mesure, "JPL Small-Body Database, 12/11/2026"},
        {"Sondes qui quittent le système solaire", sur(c.sondes, kSondesSortie), Nature::Mesure, "NASA (Pioneer 10 et 11, Voyager 1 et 2, New Horizons)"},
        {"Écart des planètes et du Soleil", "< 1 mm ; Terre 3,5 m ; Lune 282 m", Nature::Mesure, "essai_ephem contre JPL Horizons, 112 valeurs de 1650 à 2026"},
        {"Écart des lunes", "14 lunes < 1 mm ; Triton 255 km", Nature::Mesure, "essai_ephem contre JPL Horizons"},
        {"Écart des sondes", "0,7 km au plus (survols compris)", Nature::Mesure, "essai_sondes contre JPL Horizons, 8 dates"},
        {"Écart des astéroïdes", "25 000 à 93 000 km après 154 jours", Nature::Mesure, "asteroides.py --controle contre JPL Horizons (3 astéroïdes)"},
        {"Planètes et lunes, 1550 à 2650", "positions lues dans les fichiers de la NASA, ajustés aux mesures", Nature::Calcule, "DE440, jup365, sat441…"},
        {"Sondes", "trajectoires du JPL reconstruites d'après le suivi radio, puis prolongées par calcul (Pioneer : contact perdu)", Nature::Calcule, "JPL Horizons (sondes.bin)"},
        {"Astéroïdes", "position calculée ici d'après l'orbite mesurée, sans l'attraction des planètes", Nature::Calcule, "équation de Kepler"},
    };
    e.manques = {
        entier(lunesConnues() - lunesPresentes(c)) + " lunes : les fichiers légers du NAIF n'en contiennent pas ; les 5 grandes lunes d'Uranus sont dans un fichier de 5,6 Go",
        entier(kAsteroidesConnus - double(c.asteroides)) + " astéroïdes du JPL pas encore chargés",
        "Les " + entier(kCometesConnues) + " comètes du JPL",
        "Les autres sondes (en orbite autour des planètes, en route) : pas encore chargées",
        "Orbites des astéroïdes : ajouter l'attraction des planètes (écart actuel jusqu'à 93 000 km en 154 jours)",
        "Mesurer l'écart de Triton avec un fichier plus récent (255 km aujourd'hui)",
    };
    return e;
}

inline Echelle voisinage(const Comptes& c) {
    Echelle e;
    e.nom = "Étoiles voisines (10 parsecs)";
    const double uniques = double(c.etoiles10pc) - double(c.doublons10pc);
    e.part = uniques / kObjets10pc;
    e.complet = pourcent(e.part) + " des objets connus à moins de 10 pc (" + entier(uniques) + " sur " + entier(kObjets10pc) + ")";
    const double pasUa = kPasLongitudeArcsec / 206264.806 * kRayonVoisinageLy * 63241.077;
    e.precision = "place arrondie par pas de " + entier(pasUa) + " UA à 10 pc (fichier)";
    e.mesure = "positions mesurées ; mouvement : " + entier(double(c.principalSansVitesseRadiale)) + " étoiles sans vitesse radiale";
    e.lignes = {
        {"Points à moins de 10 pc", entier(double(c.etoiles10pc)), Nature::Mesure, "etoiles.bin (compté au chargement)"},
        {"Dont paires en double probables", entier(double(c.doublons10pc)) + " (deux catalogues, moins de 0,02 al d'écart)", Nature::Calcule, "compté au chargement"},
        {"Objets connus à moins de 10 pc", entier(kObjets10pc) + " étoiles, naines brunes et exoplanètes", Nature::Mesure, "Reylé et al. 2021, A&A 650, A201"},
        {"Arrondi du fichier", "direction 19,8″ × 9,9″, distance 0,019 %", Nature::Calcule, "entiers de 16 bits (pipeline/natif/etoiles.py)"},
        {"Vitesse radiale absente (mise à zéro)", entier(double(c.principalSansVitesseRadiale)) + " étoiles du catalogue principal", Nature::Calcule,
         "composante radiale < 0,2 km/s dans etoiles.bin ; Gaia : indiscernable dans le fichier"},
    };
    e.manques = {
        "Retirer les doublons entre catalogues (garder la mesure Gaia)",
        "Les naines brunes et exoplanètes du recensement de Reylé et al. absentes",
        "Garder la direction complète dans le fichier (l'arrondi à 20″ est bien plus grossier que Gaia)",
        "Marquer dans le fichier les étoiles dont la vitesse radiale n'est pas mesurée (elle vaut zéro aujourd'hui)",
    };
    return e;
}

// Étoiles de la Voie lactée réellement dessinées : avec gaia.bin, le catalogue principal (noms, fiches ; Gaia en a retiré
// les doublons) et les 98 millions d'étoiles Gaia ; sans lui, tout etoiles.bin.
inline double etoilesDessinees(const Comptes& c) {
    return c.etoilesGaia ? double(c.etoilesCatalogue[0] + c.etoilesGaia) : double(c.etoiles);
}

inline Echelle voieLactee(const Comptes& c) {
    Echelle e;
    e.nom = "Voie lactée";
    const double n = etoilesDessinees(c);
    e.part = n / kSourcesGaiaDr3;
    e.complet = pourcent(e.part) + " des sources de Gaia DR3 (" + entier(n) + " étoiles)";
    e.precision = c.etoilesGaia ? "distance à mieux que 10 % (Gaia : parallaxe 10 fois son erreur)"
                                : "distance à mieux que 20 % (Gaia : parallaxe 5 fois son erreur)";
    e.mesure = c.voieLactee ? "étoiles mesurées ; galaxie dessinée par un modèle ajusté sur des mesures (3 hypothèses)"
                            : "étoiles mesurées ; la Voie lactée elle-même n'est pas dessinée";
    if (c.etoilesGaia) {
        e.lignes = {
            {"Étoiles présentes", entier(n) + " (Gaia " + entier(double(c.etoilesGaia)) + ", catalogue principal " + entier(double(c.etoilesCatalogue[0])) + ")",
             Nature::Mesure, "gaia.bin (Gaia DR3) et etoiles.bin"},
            {"Sources de Gaia DR3", sur(n, kSourcesGaiaDr3), Nature::Mesure, "ESA, Gaia DR3"},
            {"Erreur de distance, Gaia", "< 10 % (1 σ)", Nature::Mesure, "sélection parallaxe > 10 fois son erreur (pipeline/natif/gaia_telecharger.py)"},
            {"Vitesse radiale mesurée", sur(kGaiaVitessesRadiales, double(c.etoilesGaia)) + " ; les autres : comptée nulle", Nature::Mesure,
             "gaia.bin du 12/11/2026 (docs/gaia-voie-lactee.md)"},
        };
    } else {
        e.lignes = {
            {"Étoiles présentes", entier(n) + " (principal " + entier(double(c.etoilesCatalogue[0])) + ", Gaia " +
                                      entier(double(c.etoilesCatalogue[1] + c.etoilesCatalogue[2])) + ")", Nature::Mesure, "etoiles.bin"},
            {"Sources de Gaia DR3", sur(n, kSourcesGaiaDr3), Nature::Mesure, "ESA, Gaia DR3"},
            {"Erreur de distance, Gaia", "< 20 % en flux, < 17 % embarqué (1 σ)", Nature::Mesure, "sélection parallax_over_error > 5 et > 6 (pipeline/fetch_*.py)"},
        };
    }
    e.lignes.push_back({"Étoiles de la Voie lactée", pourcent(n / kEtoilesVoieLacteeMax) + " à " + pourcent(n / kEtoilesVoieLacteeMin) + " de 100 à 400 milliards",
                        Nature::Estimation, "NASA Goddard (estimation, aucun recensement)"});
    e.lignes.push_back({"Erreur de distance, catalogue principal", "non gardée dans le fichier", Nature::Inconnu, "HYG (Hipparcos)"});
    if (c.voieLactee) {
        e.lignes.push_back({"Galaxie dessinée (disques, bulbe, barres, poussière)", "modèle publié, ajusté par d'autres sur des mesures", Nature::Ajuste,
                            "Bland-Hawthorn et Gerhard 2016 ; Licquia et al. 2015 ; Reid et al. 2019 ; Edenhofer et al. 2024"});
        e.lignes.push_back({"Partage de la lumière entre composantes", "au prorata des masses", Nature::Suppose, "docs/gaia-voie-lactee.md"});
        e.lignes.push_back({"Lumière ajoutée par les bras", "disque doublé sur leur axe", Nature::Suppose, "docs/gaia-voie-lactee.md"});
        e.lignes.push_back({"Largeur de la barre longue", "0,5 kpc", Nature::Suppose, "docs/gaia-voie-lactee.md"});
    }
    e.manques = {"Le reste de Gaia DR3 (" + entier(kSourcesGaiaDr3 - n) + " sources, dont celles à parallaxe moins sûre)",
                 "Garder l'erreur de distance de chaque étoile dans le fichier"};
    if (c.voieLactee) e.manques.push_back("Remplacer les trois hypothèses du modèle de la galaxie par des mesures");
    else e.manques.push_back("Dessiner la Voie lactée (disque, bras, gaz) d'après des cartes mesurées");
    return e;
}

inline Echelle groupeLocal(const Comptes& c) {
    Echelle e;
    e.nom = "Groupe local";
    e.part = c.galaxiesGroupeLocal / kGalaxiesGroupeLocal;
    e.complet = pourcent(e.part) + " des galaxies connues à moins de 1 Mpc (" + entier(c.galaxiesGroupeLocal) + " sur " + entier(kGalaxiesGroupeLocal) + ")";
    e.precision = "erreur de distance de chaque galaxie : non gardée";
    e.mesure = "positions mesurées aujourd'hui ; calculées dans le temps profond";
    e.lignes = {
        {"Galaxies nommées à moins de 1 Mpc", sur(c.galaxiesGroupeLocal, kGalaxiesGroupeLocal), Nature::Mesure, "Local Volume Database v1.1.2 (Pace), 04/11/2026"},
        {"Erreur de distance", "non gardée dans galaxies_noms.tsv", Nature::Inconnu, ""},
        {"Positions au-delà de 3 millions d'années", "calcul de la fusion (300 000 particules)", Nature::Calcule, "pipeline/fusion/calcul.py"},
    };
    e.manques = {
        entier(kGalaxiesGroupeLocal - c.galaxiesGroupeLocal) + " galaxies naines de la Local Volume Database",
        "Garder l'erreur de distance de chaque galaxie",
        "Formes et étoiles des galaxies proches",
    };
    return e;
}

inline Echelle lointain(const Comptes& c) {
    Echelle e;
    e.nom = "Univers lointain";
    const double g = double(c.galaxiesReleves);
    e.complet = entier(g) + " galaxies et quasars ; " + pourcent(g / kGalaxiesMax) + " à " + pourcent(g / kGalaxiesMin) + " d'une estimation";
    const double pasKmS = kPasDecalageRelatif * kLumiereKmS;
    char b[96];
    std::snprintf(b, sizeof(b), "décalage arrondi à %.1f km/s × (1 + z) ; direction 19,8″", pasKmS);
    std::string arrondi = b;
    for (char& ch : arrondi) if (ch == '.') ch = ',';
    e.precision = arrondi;
    e.mesure = "direction et décalage mesurés ; distance 100 % calculée";
    e.lignes = {
        {"Galaxies et quasars", entier(g), Nature::Mesure, "relevés 2MRS, 6dF, 2dF, SDSS, DESI (galaxies.bin)"},
        {"Galaxies de l'univers observable", "200 milliards à 2 000 milliards", Nature::Estimation, "Lauer et al. 2021 ; Conselice et al. 2016"},
        {"Arrondi du fichier", arrondi, Nature::Calcule, "entiers de 16 bits (pipeline/natif/galaxies.py)"},
        {"Distance", "calculée d'après le décalage et la cosmologie réglable", Nature::Calcule, "cosmologie.h"},
        {"Mouvement propre des galaxies", "ignoré dans la distance ; erreur non chiffrée", Nature::Inconnu, ""},
    };
    e.manques = {
        "Distances mesurées sans le décalage (céphéides, supernovæ : catalogue Cosmicflows)",
        "Éclat et forme de chaque galaxie",
        "Relevés plus récents (DESI après la DR1)",
    };
    return e;
}

inline std::array<Echelle, 5> rapport(const Comptes& c) { return {systemeSolaire(c), voisinage(c), voieLactee(c), groupeLocal(c), lointain(c)}; }

// Échelle regardée, d'après la distance de la caméra à l'astre suivi (années-lumière).
inline int echellePour(double distLy) {
    if (distLy < 0.05) return 0;          // ~3 000 UA : système solaire
    if (distLy < 100) return 1;
    if (distLy < 2.0e5) return 2;
    if (distLy < 2.0e7) return 3;
    return 4;
}

#ifdef IMGUI_VERSION
// Une ligne pour le coin de l'écran.
inline std::string ligneCourte(const Echelle& e) { return std::string(e.nom) + " : " + e.complet; }

// Le détail, dans la fenêtre ImGui déjà ouverte par l'interface.
inline void detail(const Echelle& e) {
    ImGui::TextUnformatted(e.nom);
    ImGui::Separator();
    ImGui::Text("Présent : %s", e.complet.c_str());
    ImGui::Text("Précision : %s", e.precision.c_str());
    ImGui::Text("Mesuré ou calculé : %s", e.mesure.c_str());
    if (ImGui::BeginTable("completude", 3, ImGuiTableFlags_RowBg | ImGuiTableFlags_SizingStretchProp)) {
        for (const Ligne& l : e.lignes) {
            ImGui::TableNextRow();
            ImGui::TableNextColumn();
            ImGui::TextUnformatted(l.quoi.c_str());
            ImGui::TableNextColumn();
            ImGui::TextUnformatted(l.valeur.c_str());
            ImGui::TableNextColumn();
            ImGui::TextDisabled("%s", motNature(l.nature));
            if (!l.source.empty() && ImGui::IsItemHovered()) ImGui::SetTooltip("Source : %s", l.source.c_str());
        }
        ImGui::EndTable();
    }
    ImGui::TextUnformatted("Ce qui manque :");
    for (const std::string& m : e.manques) ImGui::BulletText("%s", m.c_str());
}
#endif

}  // namespace completude
