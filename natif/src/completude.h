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
#include <fstream>
#include <string>
#include <vector>

#include "completude_groupe_local.h"

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
constexpr double kAsteroidesConnus = 1580368;              // JPL SBDB, requête sb-kind=a du 12/11/2026 à 18 h 25 UTC (grandit chaque jour)
constexpr double kCometesConnues = 4088;                   // JPL SBDB, requête sb-kind=c du 12/11/2026
// Comètes de la base du JPL écartées par pipeline/natif/cometes_horizons.py (docs/plan-natif.md, 12/11/2026).
constexpr int kCometesDisparues = 39, kCometesOrbiteOuverte = 2244, kCometesSansOrbiteAJour = 27;
constexpr int kSondesSortie = 5;                           // NASA : Pioneer 10 et 11, Voyager 1 et 2, New Horizons (sortie du système solaire)
constexpr double kObjets10pc = 540;                        // Reylé et al. 2021, A&A 650 A201 : étoiles, naines brunes, exoplanètes
constexpr double kSourcesGaiaDr3 = 1811709771;             // ESA, Gaia DR3 (cosmos.esa.int/web/gaia/dr3)
constexpr double kGaiaSourcesAdditionnees = 1707918961;
constexpr double kGaiaJeuB = 93861853;                      // gaia_tuiles.py du 13/11/2026 : parallaxe entre 5 et 10 erreurs    // gaia_agreger.py du 12/11/2026 : toutes les autres sources avec magnitude G
constexpr double kGaiaVitessesRadiales = 25878867;         // gaia.bin du 12/11/2026 : vitesses radiales mesurées (docs/gaia-voie-lactee.md)
constexpr double kEtoilesVoieLacteeMin = 1.0e11, kEtoilesVoieLacteeMax = 4.0e11;   // NASA Goddard (Blueshift) : estimation
constexpr double kGalaxiesGroupeLocal = 113;               // Local Volume Database v1.1.2 (Pace, 04/11/2026) : confirmées, < 1 Mpc
constexpr double kGalaxiesMin = 2.0e11, kGalaxiesMax = 2.0e12;     // Lauer et al. 2021 (centaines de milliards) ; Conselice et al. 2016
// Grandes structures (structures.bin, pipeline/natif/structures.py, 19/11/2026).
constexpr int kVidesVoisinage = 100;        // Malandrino et al. 2026 (A&A 705, A160) : vides à 5 sigma, moins de 200 Mpc/h
constexpr int kVidesSdss = 1163, kVidesSdssMontres = 899;      // Douglass et al. 2023 (VoidFinder, Planck 2018) ; montrés : au-delà de 200 Mpc/h
constexpr int kVidesBoss = 1228;            // Mao et al. 2017 (ApJ 835, 161), VizieR J/ApJ/835/161
constexpr int kBassinsPublies = 6;          // Dupuy et Courtois 2023, table 1 : Laniakea et 5 voisins
constexpr double kCometesOortMin = 1.0e11, kCometesOortMax = 1.0e12;      // estimation publiée (NASA), aucune vue sur place

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
    uint64_t cometes = 0;              // comètes du catalogue des petits corps (asteroides::Catalogue::isComet)
    uint64_t etoiles = 0;
    uint64_t etoilesCatalogue[3] = {}; // principal (HYG / Hipparcos), Gaia embarqué, Gaia en flux
    uint64_t etoilesGaia = 0;          // gaia.bin (Gaia DR3, parallaxe > 10 fois son erreur) quand il est chargé ; 0 sinon
    bool voieLactee = false;           // Voie lactée dessinée en volume (voie_lactee.bin)
    bool agrege = false;               // lumière additionnée des autres sources Gaia chargée (gaia_agrege.bin)
    uint64_t additionneesPlacees = 0;  // sources additionnées dans une case placée à sa distance (compté dans le fichier)
    double lumiereSansDistance = 0;    // part de la lumière additionnée sans distance mesurée (en-tête du fichier)
    uint64_t etoiles10pc = 0;
    uint64_t etoiles10pcCatalogue[3] = {};      // par catalogue d'etoiles.bin
    bool voisinageGaia = false;        // gaia.bin lu près du Soleil (ce que l'appli dessine quand Gaia est chargé)
    uint64_t gaia10pc = 0, gaia10pcVitesseRadiale = 0;      // étoiles de gaia.bin à moins de 10 pc, dont vitesse radiale mesurée
    uint64_t doublons10pc = 0;         // paires de deux catalogues différents à moins de kDoublonLy
    uint64_t principalSansVitesseRadiale = 0;      // catalogue principal : vitesse radiale non mesurée
    bool sansVitesseRadialeLu = false; // true : nombre lu dans etoiles_sans_vr.txt (exact) ; false : repéré par la composante
                                       // radiale nulle (< 0,2 km/s) dans etoiles.bin (ancien fichier, approché)
    int galaxiesGroupeLocal = 0;       // galaxies nommées à moins de 1 Mpc du Soleil
    uint64_t galaxiesReleves = 0;      // galaxies et quasars des relevés (galaxies.bin)
    bool structures = false;           // structures.bin chargé (Laniakea, flot, vides)
    uint32_t lignesFlot = 0;           // lignes de courant du champ de vitesses Cosmicflows-4
    uint64_t cometesOortModele = 0;    // comètes du MODÈLE du nuage d'Oort dessinées (structures.h)
};

inline int lunesPresentes(const Comptes& c) {
    int n = 0;
    for (int v : c.lunes) n += v;
    return n;
}

// Lunes présentes parmi les connues : par système, au plus le nombre reconnu (une trajectoire de la NASA peut exister pour
// une lune pas encore dans la liste de l'UAI ; elle est dite à part, jamais comptée au-delà de 100 %).
inline int lunesPresentesConnues(const Comptes& c) {
    int n = 0;
    for (int s = 0; s < 10; ++s) n += std::min(c.lunes[s], kLunesConnues[s]);
    return n;
}

// Système d'une lune d'après son code NAIF : premier chiffre (301 -> 3, 502 -> 5, 55501 -> 5, 65067 -> 6).
inline int systemeDeLaLune(int naif) {
    int s = naif < 0 ? -naif : naif;
    while (s >= 10) s /= 10;
    return s;
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
    for (uint64_t i : proches) ++c.etoiles10pcCatalogue[i < parCatalogue[0] ? 0 : i < parCatalogue[0] + parCatalogue[1] ? 1 : 2];
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
// gaia_agrege.bin (gaia.h, pipeline/natif/gaia_agrege_convertir.py) : en-tête de 64 octets (« UNIVGAG1 », cases (u64),
// pixels du ciel (u32), niveau (u32), lumière des cases et lumière sans distance (f64)), puis cases de 32 octets dont
// le dernier entier (u32) est le nombre de sources. Rend c inchangé si le fichier manque ou ne se lit pas.
inline Comptes lireAgrege(Comptes c, const std::string& chemin) {
    std::ifstream f(chemin, std::ios::binary);
    char h[64] = {};
    f.read(h, 64);
    // Deux formats : « UNIVGAG1 » (cases de 32 octets) et « UNIVGAG2 » (cases de 48 octets, avec leur vitesse moyenne) ;
    // dans les deux, le nombre de sources d'une case est à l'octet 28 de la case.
    const bool v1 = std::memcmp(h, "UNIVGAG1", 8) == 0, v2 = std::memcmp(h, "UNIVGAG2", 8) == 0;
    if (!f || (!v1 && !v2)) return c;
    const size_t taille = v2 ? 48 : 32;
    uint64_t cases = 0;
    double lumiere3d = 0, lumiereCiel = 0;
    std::memcpy(&cases, h + 8, 8);
    std::memcpy(&lumiere3d, h + 24, 8);
    std::memcpy(&lumiereCiel, h + 32, 8);
    std::vector<char> bloc(taille * 65536);
    uint64_t sources = 0;
    for (uint64_t lu = 0; lu < cases;) {
        const uint64_t k = std::min<uint64_t>(65536, cases - lu);
        if (!f.read(bloc.data(), static_cast<std::streamsize>(k * taille))) return c;
        for (uint64_t i = 0; i < k; ++i) {
            uint32_t n = 0;
            std::memcpy(&n, bloc.data() + i * taille + 28, 4);
            sources += n;
        }
        lu += k;
    }
    c.agrege = true;
    c.additionneesPlacees = sources;
    c.lumiereSansDistance = lumiere3d + lumiereCiel > 0 ? lumiereCiel / (lumiere3d + lumiereCiel) : 0;
    return c;
}

// gaia.bin (pipeline/natif/gaia_convertir.py) : en-tête de 4096 octets (« UNIVGAI1 », n (u64), feuilles (u32)), feuilles de
// 48 octets (min x,y,z f32, nombre u32, max x,y,z f32, réservé u32, première étoile u64, réservé u64), puis étoiles de 16
// octets (x, y, z f32 en al, magnitude f16, couleur u8, drapeaux u8 : 1 = vitesse radiale mesurée). Seules les feuilles qui
// touchent la sphère de 10 pc sont lues (8 feuilles, 55 000 étoiles, mesuré le 12/11/2026).
inline Comptes lireGaiaVoisinage(Comptes c, const std::string& chemin) {
    std::ifstream f(chemin, std::ios::binary);
    char h[4096] = {};
    f.read(h, sizeof(h));
    if (!f || std::memcmp(h, "UNIVGAI1", 8) != 0) return c;
    uint32_t feuilles = 0;
    std::memcpy(&feuilles, h + 16, 4);
    std::vector<char> lv(static_cast<size_t>(feuilles) * 48);
    if (!f.read(lv.data(), static_cast<std::streamsize>(lv.size()))) return c;
    const uint64_t debutEtoiles = 4096 + (uint64_t(feuilles) * 48 + 63) / 64 * 64;
    const double r2 = kRayonVoisinageLy * kRayonVoisinageLy;
    uint64_t n10 = 0, vr10 = 0;
    std::vector<char> e;
    for (uint32_t k = 0; k < feuilles; ++k) {
        const char* q = lv.data() + size_t(k) * 48;
        float mn[3], mx[3];
        uint32_t n = 0;
        uint64_t premiere = 0;
        std::memcpy(mn, q, 12);
        std::memcpy(&n, q + 12, 4);
        std::memcpy(mx, q + 16, 12);
        std::memcpy(&premiere, q + 32, 8);
        double d2 = 0;
        for (int a = 0; a < 3; ++a) {
            const double v = std::clamp(0.0, double(mn[a]), double(mx[a]));
            d2 += v * v;
        }
        if (d2 >= r2 || n == 0) continue;
        e.resize(size_t(n) * 16);
        f.seekg(static_cast<std::streamoff>(debutEtoiles + premiere * 16));
        if (!f.read(e.data(), static_cast<std::streamsize>(e.size()))) return c;
        for (uint32_t i = 0; i < n; ++i) {
            float p[3];
            std::memcpy(p, e.data() + size_t(i) * 16, 12);
            if (double(p[0]) * p[0] + double(p[1]) * p[1] + double(p[2]) * p[2] >= r2) continue;
            ++n10;
            if (e[size_t(i) * 16 + 15] & 1) ++vr10;
        }
    }
    c.voisinageGaia = true;
    c.gaia10pc = n10;
    c.gaia10pcVitesseRadiale = vr10;
    return c;
}

// etoilesGaia : nombre d'étoiles de gaia.bin (GaiaRenderer::count) ; pris seulement si sim.hasGaia.
// etoiles_sans_vr.txt (pipeline/natif/etoiles_hyg.py), à côté de etoiles.bin : une ligne, le nombre exact d'étoiles du
// catalogue principal sans vitesse radiale mesurée (ni HYG ni SIMBAD). Rend c inchangé si le fichier manque.
inline Comptes lireSansVitesseRadiale(Comptes c, const std::string& chemin) {
    std::ifstream f(chemin);
    unsigned long long n = 0;
    if (!(f >> n)) return c;
    c.principalSansVitesseRadiale = n;
    c.sansVitesseRadialeLu = true;
    return c;
}

// fichierGaia : chemin de gaia.bin quand gaia.h l'a chargé ; vide sinon (le voisinage est alors compté dans etoiles.bin).
// fichierAgrege : chemin de gaia_agrege.bin quand gaia.h l'a chargé (GaiaRenderer::cellCount > 0) ; vide sinon.
template <class SimT>
Comptes compter(const SimT& sim, uint64_t galaxiesReleves, uint64_t etoilesGaia = 0, const std::string& fichierAgrege = "", const std::string& fichierGaia = "",
                const std::string& dossierDonnees = "") {
    Comptes c;
    c.etoilesGaia = sim.hasGaia ? etoilesGaia : 0;
    c.voieLactee = sim.hasMilkyWay;
    if (sim.hasGaia && !fichierAgrege.empty()) c = lireAgrege(c, fichierAgrege);
    if (sim.hasGaia && !fichierGaia.empty()) c = lireGaiaVoisinage(c, fichierGaia);
    c.asteroides = sim.asteroidCount;
    c.structures = sim.structures.loaded;
    c.lignesFlot = sim.structures.flowLines;
    c.cometesOortModele = sim.structures.oortComets;
    if (sim.asteroidCat) {      // les comètes, quand le catalogue en contient, ne sont pas des astéroïdes
        uint64_t k = 0;
        for (uint64_t i = 0; i < sim.asteroidCat->n; ++i) k += sim.asteroidCat->isComet(static_cast<size_t>(i)) ? 1 : 0;
        c.cometes = k;
        c.asteroides = sim.asteroidCount >= k ? sim.asteroidCount - k : 0;
    }
    c.galaxiesReleves = galaxiesReleves;
    for (const auto& b : sim.bodies) {
        using K = decltype(b.kind);
        // Planète : tourne autour du Soleil (parent -1 ou l'astre Soleil) ; lune : tourne autour d'une planète.
        const bool autourDuSoleil = b.parent < 0 || sim.bodies[static_cast<size_t>(b.parent)].kind == K::Sun;
        if (b.kind == K::Planet && autourDuSoleil) ++c.planetes;
        if (b.kind == K::Planet && !autourDuSoleil) {
            const int systeme = systemeDeLaLune(b.naif);
            if (systeme >= 0 && systeme < 10) ++c.lunes[systeme];
        }
        if (b.kind == K::Probe) ++c.sondes;
        if (b.kind == K::Galaxy && b.natureText.rfind("centre", 0) != 0 && !b.unplaced && !b.merged && !b.structure && !b.nebula) {      // ni les galaxies sans distance, ni les doublons fondus, ni les repères
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
    if (!dossierDonnees.empty()) c = lireSansVitesseRadiale(c, dossierDonnees + "/etoiles_sans_vr.txt");      // après le comptage d'etoiles.bin
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
    std::string court;                // ligne du coin en affichage réduit ; vide : début de `complet`
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
    if (p < 100 && p >= 99.5) {      /* jamais « 100 % » pour ce qui n'est pas complet : chiffres tronqués, pas arrondis */
        const int d = std::clamp(int(std::ceil(-std::log10(100 - p))), 1, 6);
        const double k = std::pow(10.0, d);
        std::snprintf(b, sizeof(b), "%.*f %%", d, std::floor(p * k) / k);
    } else if (p >= 10) std::snprintf(b, sizeof(b), "%.0f %%", p);
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
    const double present = c.planetes + lunesPresentesConnues(c) + double(c.asteroides) + double(c.cometes) + c.sondes;
    const double connu = kPlanetesConnues + lunesConnues() + kAsteroidesConnus + kCometesConnues + kSondesSortie;
    e.part = present / connu;
    e.complet = pourcent(e.part) + " des objets connus (" + entier(present) + " sur " + entier(connu) + ") ; lunes " +
                pourcent(double(lunesPresentesConnues(c)) / lunesConnues()) + ", comètes " + pourcent(double(c.cometes) / kCometesConnues);
    e.precision = "planètes et Soleil < 1 mm ; sondes < 1 km ; astéroïdes < 300 000 km";
    e.mesure = "positions : éphémérides de la NASA (planètes, lunes) ; calculées ici (astéroïdes)";
    e.lignes = {
        {"Planètes et Pluton", sur(c.planetes, kPlanetesConnues), Nature::Mesure, "UAI"},
        {"Lunes", sur(lunesPresentesConnues(c), lunesConnues()) +
                      (lunesPresentes(c) > lunesPresentesConnues(c) ? " ; plus " + entier(lunesPresentes(c) - lunesPresentesConnues(c)) +
                                                                          " pas encore reconnue(s) par l'UAI" : std::string()),
         Nature::Mesure, "JPL, Planetary Satellite Discovery Circumstances, 12/11/2026 ; trajectoires du NAIF"},
        {"Astéroïdes", sur(double(c.asteroides), kAsteroidesConnus), Nature::Mesure, "JPL Small-Body Database, 12/11/2026"},
        {"Comètes", sur(double(c.cometes), kCometesConnues), Nature::Mesure, "JPL Small-Body Database, 12/11/2026"},
        {"Sondes qui quittent le système solaire", sur(c.sondes, kSondesSortie), Nature::Mesure, "NASA (Pioneer 10 et 11, Voyager 1 et 2, New Horizons)"},
        {"Écart des planètes et du Soleil", "< 1 mm ; Terre 3,5 m ; Lune 282 m", Nature::Mesure, "essai_ephem contre JPL Horizons, 112 valeurs de 1650 à 2026"},
        {"Écart des lunes", "14 lunes < 1 mm ; Triton 255 km", Nature::Mesure, "essai_ephem contre JPL Horizons"},
        {"Écart des sondes", "0,7 km au plus (survols compris)", Nature::Mesure, "essai_sondes contre JPL Horizons, 8 dates"},
        {"Écart des comètes", "moins de 150 000 km (0,001 UA) pour 8 comètes 157 jours après ; Halley 16 000 km", Nature::Mesure,
         "contrôle de cometes_horizons.py contre JPL Horizons"},
        {"Écart des astéroïdes", "moins de 300 000 km (0,002 UA) pour 10 corps dont Cérès et Vesta ; 25 000 à 93 000 km pour 3 autres après 154 jours",
         Nature::Mesure, "asteroides_jpl.py --controle et asteroides.py --controle, contre JPL Horizons"},
        {"Planètes et lunes, 1550 à 2650", "positions lues dans les fichiers de la NASA, ajustés aux mesures", Nature::Calcule, "DE440, jup365, sat441…"},
        {"Sondes", "trajectoires du JPL reconstruites d'après le suivi radio, puis prolongées par calcul (Pioneer : contact perdu)", Nature::Calcule, "JPL Horizons (sondes.bin)"},
        {"Astéroïdes", "position calculée ici d'après l'orbite mesurée, sans l'attraction des planètes", Nature::Calcule, "équation de Kepler"},
    };
    const double asteroidesAbsents = kAsteroidesConnus - double(c.asteroides);
    e.manques = {
        entier(lunesConnues() - lunesPresentesConnues(c)) + " lunes connues sans trajectoire publiée par la NASA (fichiers du NAIF)",
        entier(kCometesConnues - double(c.cometes)) + " comètes : " + entier(kCometesOrbiteOuverte) + " passées une seule fois sur une orbite ouverte, " +
            entier(kCometesDisparues) + " disparues, " + entier(kCometesSansOrbiteAJour) + " sans orbite à jour",
        "Les autres sondes (en orbite autour des planètes, en route) : pas encore chargées",
        "Orbites des astéroïdes : ajouter l'attraction des planètes (écart actuel jusqu'à 300 000 km)",
        "Mesurer l'écart de Triton avec un fichier plus récent (255 km aujourd'hui)",
    };
    if (c.cometesOortModele) {
        e.lignes.push_back({"Nuage d'Oort", entier(double(c.cometesOortModele)) + " comètes d'un modèle (densité en r^-3,5 de 3 000 à 100 000 UA, nuage intérieur aplati), "
                            "chacune sur son orbite ; on en estime 100 à 1 000 milliards", Nature::Suppose,
                            "modèle : Duncan, Quinn et Tremaine 1987 ; Oort 1950 ; aplatissement intérieur supposé (Kaib et Quinn 2008)"});
        e.manques.push_back("Nuage d'Oort : aucune de ses comètes n'a été vue sur place ; le modèle ignore la marée de la Galaxie et les étoiles qui passent");
    }
    if (asteroidesAbsents > 0)
        e.manques.insert(e.manques.begin() + 1, entier(asteroidesAbsents) +
                         " astéroïdes de la base du JPL absents (orbite non elliptique, ou découverts depuis le téléchargement : retélécharger)");
    return e;
}

// Étoiles du catalogue principal sans vitesse radiale mesurée (leur mouvement le long de la ligne de visée est compté nul).
inline Ligne ligneSansVitesseRadiale(const Comptes& c) {
    if (c.sansVitesseRadialeLu)
        return {"Vitesse radiale absente (mise à zéro), catalogue principal", sur(double(c.principalSansVitesseRadiale), double(c.etoilesCatalogue[0])),
                Nature::Mesure, "etoiles_sans_vr.txt : ni HYG v4.1 ni SIMBAD n'en ont (pipeline/natif/etoiles_hyg.py)"};
    return {"Vitesse radiale absente (mise à zéro), catalogue principal", entier(double(c.principalSansVitesseRadiale)) + " (repérées, nombre approché)",
            Nature::Calcule, "composante radiale < 0,2 km/s dans etoiles.bin (etoiles_sans_vr.txt absent)"};
}

// Avec gaia.bin : ce qui est dessiné, c'est le catalogue principal (dont Gaia a retiré ses copies : même direction à 40″,
// magnitude à 2 près) et les étoiles de gaia.bin. Sans lui : etoiles.bin, doublons entre catalogues repérés à 0,02 al.
inline Echelle voisinageGaia(const Comptes& c) {
    Echelle e;
    e.nom = "Étoiles voisines (10 parsecs)";
    const uint64_t principal = c.etoiles10pcCatalogue[0];
    const double present = double(principal + c.gaia10pc);
    e.part = present / kObjets10pc;
    e.complet = pourcent(e.part) + " des objets connus à moins de 10 pc (" + entier(present) + " sur " + entier(kObjets10pc) + ")";
    e.precision = "Gaia : distance à mieux que 10 % ; catalogue principal : place arrondie par pas de " +
                  entier(kPasLongitudeArcsec / 206264.806 * kRayonVoisinageLy * 63241.077) + " UA";
    const uint64_t sansVr = c.gaia10pc - c.gaia10pcVitesseRadiale;
    e.mesure = "positions mesurées ; vitesse radiale mesurée pour " + entier(double(c.gaia10pcVitesseRadiale)) + " des " +
               entier(double(c.gaia10pc)) + " étoiles Gaia";
    e.lignes = {
        {"Étoiles Gaia à moins de 10 pc", entier(double(c.gaia10pc)), Nature::Mesure, "gaia.bin (compté au chargement)"},
        {"Étoiles du catalogue principal à moins de 10 pc", entier(double(principal)), Nature::Mesure, "etoiles.bin (HYG ; copies Gaia retirées)"},
        {"Objets connus à moins de 10 pc", entier(kObjets10pc) + " étoiles, naines brunes et exoplanètes", Nature::Mesure, "Reylé et al. 2021, A&A 650, A201"},
        {"Vitesse radiale mesurée (Gaia)", sur(double(c.gaia10pcVitesseRadiale), double(c.gaia10pc)), Nature::Mesure, "drapeau de gaia.bin"},
        {"Vitesse radiale absente (mise à zéro), Gaia", entier(double(sansVr)) + " étoiles", Nature::Mesure, "drapeau de gaia.bin"},
        ligneSansVitesseRadiale(c),
        {"Arrondi du fichier, catalogue principal", "direction 19,8″ × 9,9″, distance 0,019 %", Nature::Calcule, "entiers de 16 bits (pipeline/natif/etoiles.py)"},
    };
    e.manques = {
        entier(kObjets10pc - present) + " objets du recensement de Reylé et al. (surtout naines brunes et exoplanètes, trop faibles pour Gaia)",
        "Vitesse radiale des " + entier(double(sansVr)) + " étoiles Gaia proches qui n'en ont pas (catalogues au sol)",
        "Garder la direction complète du catalogue principal dans le fichier (arrondi à 20″)",
    };
    return e;
}

inline Echelle voisinage(const Comptes& c) {
    if (c.voisinageGaia) return voisinageGaia(c);
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
        ligneSansVitesseRadiale(c),
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
    // Depuis le 13/11/2026, les sources à parallaxe entre 5 et 10 erreurs sont dessinées une à une (gaia_b.bin) : elles sont
    // dans etoilesGaia et ne sont plus additionnées (gaia_agrege.bin sans cases en volume). Les additionnées sont alors
    // celles sans distance mesurée seulement.
    const bool jeuB = c.agrege && c.additionneesPlacees == 0 && double(c.etoilesGaia) > 1.5e8;
    const double additionnees = c.agrege ? kGaiaSourcesAdditionnees - (jeuB ? kGaiaJeuB : 0.0) : 0;
    e.part = (c.agrege ? double(c.etoilesGaia) + additionnees : n) / kSourcesGaiaDr3;      /* additionnées : Gaia seul (le catalogue principal y est déjà) */
    if (c.agrege)
        // Depuis gaia_agrege v2 : seules les sources dont la distance est mesurée (parallaxe supérieure à 5 fois son erreur)
        // sont additionnées à leur place ; les autres n'ont pas de distance mesurée et ne sont montrées que dans le ciel
        // d'aujourd'hui, vu du Soleil.
        e.complet = pourcent(e.part) + " des sources de Gaia DR3 : " + entier(double(c.etoilesGaia)) + " vues une à une, " +
                    (jeuB ? std::string() : entier(double(c.additionneesPlacees)) + " additionnées à leur distance, ") +
                    entier(additionnees - double(c.additionneesPlacees)) + " sans distance mesurée (ciel d'aujourd'hui seulement)";
    else
        e.complet = pourcent(e.part) + " des sources de Gaia DR3 (" + entier(n) + " étoiles)";
    // Ligne réduite : la part des ÉTOILES DE LA GALAXIE (estimation), pas la part du catalogue Gaia. « 99,6 % de ce qui
    // est connu » laissait croire que presque toute la Galaxie est là, alors que Gaia en voit environ 1 %.
    {
        const double montrees = e.part * kSourcesGaiaDr3;
        e.court = pourcent(montrees / kEtoilesVoieLacteeMax) + " à " + pourcent(montrees / kEtoilesVoieLacteeMin) + " des étoiles de la Galaxie (estimation)";
    }
    e.precision = c.agrege ? "une à une : distance à mieux que 10 % ; additionnées : " + pourcent(c.lumiereSansDistance) +
                                 " de leur lumière sans distance mesurée"
                : c.etoilesGaia ? "distance à mieux que 10 % (Gaia : parallaxe 10 fois son erreur)"
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
            ligneSansVitesseRadiale(c),
        };
        if (c.agrege) {
            e.lignes.push_back({"Autres sources, additionnées par case (pas vues une à une)", entier(additionnees) + " sources", Nature::Mesure,
                                "gaia_agreger.py (archive de l'ESA), 12/11/2026"});
            e.lignes.push_back({"Dont placées à leur distance", entier(double(c.additionneesPlacees)) + " (case de 0,21 deg² × un dixième de décade en distance)",
                                Nature::Mesure, "gaia_agrege.bin (compté au chargement)"});
            e.lignes.push_back({"Lumière additionnée sans distance mesurée", pourcent(c.lumiereSansDistance) + " (montrée seulement vue du Soleil)",
                                Nature::Inconnu, "gaia_agrege.bin : parallaxe absente, négative, ou erreur > 100 %"});
        }
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
    if (c.agrege)
        e.manques = {"Distance des sources additionnées sans parallaxe utilisable (" + pourcent(c.lumiereSansDistance) + " de leur lumière)",
                     "Voir une à une les " + entier(additionnees) + " sources additionnées",
                     "Les " + entier(kSourcesGaiaDr3 - double(c.etoilesGaia) - additionnees) + " sources de Gaia DR3 sans magnitude G ni couleur",
                     "Garder l'erreur de distance de chaque étoile dans le fichier"};
    else
        e.manques = {"Le reste de Gaia DR3 (" + entier(kSourcesGaiaDr3 - n) + " sources, dont celles à parallaxe moins sûre)",
                     "Garder l'erreur de distance de chaque étoile dans le fichier"};
    if (c.voieLactee) e.manques.push_back("Remplacer les trois hypothèses du modèle de la galaxie par des mesures");
    else e.manques.push_back("Dessiner la Voie lactée (disque, bras, gaz) d'après des cartes mesurées");
    return e;
}

inline Echelle groupeLocal(const Comptes& c) {
    namespace gl = groupe_local;
    Echelle e;
    e.nom = "Groupe local";
    // Recoupement nom par nom (pipeline/natif/completude_groupe_local.py) : valable tant que l'appli a les mêmes galaxies
    // nommées qu'au moment du recoupement ; sinon, simple comparaison des nombres, et le recoupement est à refaire.
    const bool recoupe = c.galaxiesGroupeLocal == gl::kNommeesAuRecoupement;
    const double present = recoupe ? gl::kAppariees : c.galaxiesGroupeLocal;
    e.part = std::min(1.0, present / kGalaxiesGroupeLocal);
    e.complet = pourcent(e.part) + " des galaxies connues à moins de 1 Mpc (" + entier(present) + " sur " + entier(kGalaxiesGroupeLocal) + ")";
    e.precision = "erreur de distance de chaque galaxie : non gardée";
    e.mesure = "positions mesurées aujourd'hui ; calculées dans le temps profond";
    e.lignes = {
        {"Galaxies de la Local Volume Database présentes", sur(present, kGalaxiesGroupeLocal), Nature::Mesure,
         recoupe ? "recoupement par direction avec la LVDB v1.1.2 (Pace), 12/11/2026" : "nombres seulement : recoupement à refaire"},
        {"Erreur de distance", "non gardée dans galaxies_noms.tsv", Nature::Inconnu, ""},
        {"Positions au-delà de 3 millions d'années", "calcul de la fusion (300 000 particules)", Nature::Calcule, "pipeline/fusion/calcul.py"},
    };
    if (recoupe && gl::kHorsLvdbN > 0) {
        std::string hors;
        for (int i = 0; i < gl::kHorsLvdbN; ++i) hors += std::string(i ? ", " : "") + gl::kHorsLvdb[i];
        e.lignes.push_back({"Montrées ici, absentes de la LVDB à moins de 1 Mpc", hors, Nature::Mesure, "nature débattue ou distance différente"});
    }
    e.manques.clear();
    if (recoupe && gl::kManquantesN > 0) {
        std::string noms;
        for (int i = 0; i < gl::kManquantesN; ++i) noms += std::string(i ? ", " : "") + gl::kManquantes[i].nom;
        e.manques.push_back(entier(gl::kManquantesN) + " galaxies naines, de la plus proche à la plus lointaine : " + noms);
    } else if (!recoupe) {
        e.manques.push_back(entier(std::max(0.0, kGalaxiesGroupeLocal - present)) +
                            " galaxies de la Local Volume Database, peut-être (relancer completude_groupe_local.py pour les nommer)");
    }
    e.manques.push_back("Garder l'erreur de distance de chaque galaxie");
    e.manques.push_back("Formes et étoiles des galaxies proches");
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
    if (c.structures) {
        e.lignes.push_back({"Laniakea et ses 5 bassins voisins", "frontières publiées (" + entier(kBassinsPublies) + " sur " + entier(kBassinsPublies) +
                            ")", Nature::Ajuste, "Dupuy et Courtois 2023, bassins d'attraction du champ de vitesses Cosmicflows-4"});
        e.lignes.push_back({"Flot vers les attracteurs", entier(c.lignesFlot) + " lignes de courant ; chaque bassin finit sur un seul point, à 17 à 33 Mpc/h "
                            "de l'attracteur publié", Nature::Calcule, "champ de vitesses Cosmicflows-4 (Courtois et al. 2023), pipeline/natif/structures.py"});
        e.lignes.push_back({"Vides du voisinage (< 200 Mpc/h, tout le ciel)", sur(kVidesVoisinage, kVidesVoisinage) + ", forme publiée, dont le Vide local",
                            Nature::Ajuste, "Malandrino et al. 2026, reconstruction Manticore du relevé 2M++"});
        e.lignes.push_back({"Vides SDSS DR7 (200 à 330 Mpc/h, ciel du Nord)", entier(kVidesSdssMontres) + " (les " + entier(kVidesSdss - kVidesSdssMontres) +
                            " plus proches sont déjà dans le voisinage), forme publiée", Nature::Calcule, "Douglass et al. 2023, VoidFinder sur les galaxies mesurées"});
        e.lignes.push_back({"Vides BOSS DR12 (z = 0,2 à 0,7)", sur(kVidesBoss, kVidesBoss) + " ; sphère de même volume (forme non publiée)", Nature::Calcule,
                            "Mao et al. 2017, VIDE sur les galaxies mesurées"});
    }
    e.manques = {
        "Distances mesurées sans le décalage (céphéides, supernovæ : catalogue Cosmicflows)",
        "Éclat et forme de chaque galaxie",
        "Relevés plus récents (DESI après la DR1)",
    };
    if (c.structures) {
        e.manques.push_back("Vides entre 330 Mpc/h et z = 0,2, et au-delà de 200 Mpc/h dans le ciel du Sud : aucun catalogue chargé");
        e.manques.push_back("Superamas au-delà des bassins voisins de Laniakea (le champ de Cosmicflows-4 s'arrête vers z = 0,08)");
        e.manques.push_back("Forme réelle des vides BOSS (sphère de même volume aujourd'hui)");
    } else {
        e.manques.push_back("Laniakea, son flot et les vides cosmiques : structures.bin absent");
    }
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
// Affichage réduit : la même phrase, coupée avant ses précisions (parenthèse, deux-points, point-virgule), jamais
// reformulée. Une échelle peut fournir sa propre ligne (`court`).
inline std::string ligneReduite(const Echelle& e) {
    if (!e.court.empty()) return std::string(e.nom) + " : " + e.court;
    size_t cut = e.complet.size();
    for (const char* sep : {" (", " : ", " ; "}) cut = std::min(cut, e.complet.find(sep));
    return std::string(e.nom) + " : " + e.complet.substr(0, cut);
}

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
    for (const std::string& m : e.manques) {
        ImGui::Bullet();
        ImGui::TextWrapped("%s", m.c_str());      /* une liste de noms peut être longue */
    }
}
#endif

}  // namespace completude
