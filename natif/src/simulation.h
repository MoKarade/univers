// Appli PC « Univers » : l'état du simulateur (temps, astres, objet suivi, caméra), sans rien qui dépende de l'affichage.
#pragma once
#include "asteroides_catalogue.h"
#include <thread>
#include "avancement.h"
#include "centres_reference.h"
#include "film_v2.h"
#include "ciel_bandes.h"
#include "commun.h"
#include "completude.h"
#include "cosmologie.h"
#include "ephemeride.h"
#include "galaxie_orbites.h"
#include "orbite_galactique.h"
#include "groupe_local.h"
#include "lune.h"
#include "sondes.h"
#include "systeme_solaire.h"
#include "chaos.h"

namespace {

constexpr double kLyInMeters = 9.4607304725808e15;      // année-lumière julienne (UAI)
constexpr double kLyInKm = kLyInMeters / 1000.0;
constexpr double kAuInLy = 149597870700.0 / kLyInMeters;
constexpr double kYearSeconds = 365.25 * 86400.0;
// Aujourd'hui, lu sur l'horloge du PC, en années juliennes depuis J2000,0 (1er janvier 2000, 12 h TU = 946 728 000 s Unix).
inline const double kStartYears =
    (std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count() - 946728000.0) / kYearSeconds;
// Étoiles mesurées : suivies sur leur orbite calculée autour du centre de la Galaxie jusqu'à 1 milliard d'années
// d'aujourd'hui, dans le passé comme dans le futur (orbite_galactique.h) ; elles s'effacent progressivement entre 800
// millions et 1 milliard d'années, où le calcul de la fusion des galaxies prend le relais.
constexpr double kOrbitLimitYears = 1.0e9;
constexpr double kOrbitFadeYears = 0.8e9;
constexpr double kLinearLimitYears = 3.0e6;      // au-delà, la ligne droite ne vaut plus pour les étoiles (page : épicycles puis orbites) : étape E5
// Temps des éphémérides (TDB) moins temps civil (UTC) : 69,184 s depuis 2017 (32,184 s + 37 secondes intercalaires).
// [Approximation assumée : appliquée à toute date ; l'écart réel a varié de quelques dizaines de secondes par siècle.]
constexpr double kTdbMinusUtc = 69.184;

enum class Kind { Sun, Star, Planet, Galaxy, Probe, Asteroid };

// Un astre que l'on peut suivre, chercher, nommer à l'écran.
struct Body {
    std::string name;
    Kind kind = Kind::Star;
    int64_t star = -1;          // étoile : numéro dans le catalogue
    int probe = -1;             // sonde : son rang dans le fichier des trajectoires
    int naif = 0;               // planète : code du corps dans les éphémérides de la NASA (clé de sa carte et de son orientation)
    int posNaif = 0;            // code utilisé pour sa position : le centre de la planète quand un fichier de lunes le donne
    int parent = -1;            // lune : numéro de l'astre autour duquel elle tourne (pour le tracé de l'orbite)
    double h = 0;               // planète : magnitude V(1,0), à 1 UA du Soleil et de l'observateur, pleine phase (fiche NASA)
    bool hasPhotometry = false; // planète : éclat lu dans planetes.tsv ; sinon elle n'est pas dessinée en point
    int tint[3] = {-1, -1, -1}; // planète : teinte moyenne de sa carte de surface (valeurs d'écran) ; -1 : pas de carte
    double bv = 0.65;           // étoile : indice de couleur B-V
    double periodYears = 0;     // planète : durée d'un tour (pour tracer l'orbite)
    double radiusKm = 0;        // rayon moyen
    const char* nature = "";
    std::string natureText;     // galaxie : genre lu dans le fichier
    Vec3 fixedPos{0, 0, 0};     // galaxie : position mesurée (années-lumière), immobile pour l'instant
    int priority = 1;           // galaxie : 1 = nom montré dès qu'on sort de la Voie lactée
    const char* natureLabel() const { return natureText.empty() ? nature : natureText.c_str(); }
};

// Planètes : rayon moyen et durée d'un tour, relus contre la fiche « Planetary Fact Sheet » de la NASA
// (docs/plan-natif.md). L'éclat (magnitude V(1,0)) et la teinte ne sont pas écrits ici : ils sont lus dans
// planetes.tsv, que pipeline/natif/planetes.py tire des fiches de la NASA et des cartes de surface.
struct PlanetRow {
    const char* name;
    int naif;
    double periodYears, radiusKm;
    const char* nature;
};
constexpr PlanetRow kPlanets[] = {
    {"Mercure", eph::kMercury, 0.2408467, 2439.4, "planète rocheuse"},
    {"Vénus", eph::kVenus, 0.61519726, 6051.8, "planète rocheuse"},
    {"Terre", eph::kEarth, 1.0000174, 6371.0, "planète rocheuse"},
    {"Mars", eph::kMarsBary, 1.8808476, 3389.5, "planète rocheuse"},
    {"Jupiter", eph::kJupiterBary, 11.862615, 69911.0, "géante gazeuse"},
    {"Saturne", eph::kSaturnBary, 29.447498, 58232.0, "géante gazeuse"},
    {"Uranus", eph::kUranusBary, 84.016846, 25362.0, "géante de glace"},
    {"Neptune", eph::kNeptuneBary, 164.79132, 24622.0, "géante de glace"},
    {"Pluton", eph::kPlutoBary, 247.92065, 1188.3, "planète naine"},
};
constexpr PlanetRow kMoon = {"Lune", eph::kMoon, 27.321661 / 365.25, 1737.4, "satellite de la Terre"};

struct Rate {
    const char* label;
    double yearsPerSecond;
};
constexpr Rate kRates[] = {{"Temps réel", 1.0 / kYearSeconds},        {"1 heure par seconde", 3600.0 / kYearSeconds}, {"1 jour par seconde", 1.0 / 365.25},
                           {"1 mois par seconde", 1.0 / 12.0},         {"1 an par seconde", 1.0},                      {"100 ans par seconde", 100.0},
                           {"10 000 ans par seconde", 1.0e4},          {"100 000 ans par seconde", 1.0e5},
                           {"10 millions d'années par seconde", 1.0e7}, {"200 millions d'années par seconde", 2.0e8}};
constexpr int kRateCount = static_cast<int>(sizeof(kRates) / sizeof(kRates[0]));

// Orbites exactes (double précision, bibliothèque de physique) du Soleil et des étoiles nommées : le même calcul que
// celui de la carte graphique (orbites_gpu.h), pour que les noms et le point visé suivent les étoiles dessinées.
// Deux états par étoile, au pas d'avant et au pas d'après la date (1 million d'années), reliés par une courbe de Hermite.
// Un objet mesuré qui trace un bras spiral (traceurs_bras.h) : maser à parallaxe radio ou amas ouvert daté.
struct ArmTracer {
    std::string name, arm;      // arm : code du bras donné par Reid et al. 2019 (masers) ; vide pour les amas
    Vec3 pos{0, 0, 0};          // années-lumière, repère du simulateur, aujourd'hui
    bool maser = false;
    double ageMyr = -1;         // amas : âge en millions d'années ; -1 pour un maser
    double distanceError = 0;   // erreur relative de la distance
};

// Comment ce qui est montré est obtenu, famille par famille (demande de Marc, 12 novembre 2026 : « je veux voir quand ça
// montre ce qui a été calculé en amont sur carte graphique ou approximation »). Rempli à chaque image par fenetre.cpp.
enum class CalcMode { Measured, Exact, Precomputed, Approx, Hidden };      // mesuré, calculé exactement, précalculé, approché, non montré
struct CalcState {
    std::string family;      // « Étoiles Gaia », « Planètes et lunes »…
    CalcMode mode;
    long lagSteps;           // pas de calcul encore à faire pour la date demandée (0 : à jour)
    std::string detail;      // une phrase : d'où ça vient
};

struct ExactOrbits {
    std::vector<phys::Vec3> g0, v0;      // départ : position (kpc) et vitesse (km/s) galactocentriques ; rang 0 : le Soleil
    mutable phys::galaxie::Orbites o;
    mutable bool built = false;
    mutable long idx = 0, at = 0;        // idx : pas des états gardés ; at : pas où se trouve `o`
    mutable std::vector<phys::Vec3> pa, va, pb, vb;

    int add(Vec3 pos, Vec3 vel) {
        const phys::Vec3 s = phys::galaxie::soleilPos(), sv = phys::galaxie::soleilVit(), pg = orbite::versGalactique(pos), vg = orbite::versGalactique(vel);
        g0.push_back({pg.x / orbite::kKpcLy + s.x, pg.y / orbite::kKpcLy + s.y, pg.z / orbite::kKpcLy + s.z});
        v0.push_back({vg.x + sv.x, vg.y + sv.y, vg.z + sv.z});
        built = false;
        return static_cast<int>(g0.size()) - 1;
    }
    void read(std::vector<phys::Vec3>& p, std::vector<phys::Vec3>& v) const {
        p.resize(g0.size());
        v.resize(g0.size());
        for (size_t k = 0; k < g0.size(); ++k) {
            p[k] = o.position(k);
            v[k] = o.vitesse(k);
        }
    }
    void ensure(double years) const {
        const long n = static_cast<long>(std::floor(years / 1.0e6));
        if (built && n == idx) return;
        if (!built || std::labs(n) + 1 < std::labs(n - at)) {      // premier appel, ou plus court en repartant d'aujourd'hui
            o = phys::galaxie::Orbites(g0, v0);
            at = 0;
            built = true;
        }
        o.avance(static_cast<double>(n) * 1.0e-3, 1);
        read(pa, va);
        o.avance(static_cast<double>(n + 1) * 1.0e-3, 1);
        read(pb, vb);
        at = n + 1;
        idx = n;
    }
    // Position galactocentrique (kpc) de l'étoile k à `years` ans de la date des positions.
    phys::Vec3 position(int k, double years) const {
        ensure(years);
        const double f = years / 1.0e6 - static_cast<double>(idx), f2 = f * f, f3 = f2 * f, T = 1.0e-3 * phys::galaxie::kKmsKpcToRadGa;
        const double h00 = 2 * f3 - 3 * f2 + 1, h10 = (f3 - 2 * f2 + f) * T, h01 = -2 * f3 + 3 * f2, h11 = (f3 - f2) * T;
        const phys::Vec3 &a = pa[static_cast<size_t>(k)], &u = va[static_cast<size_t>(k)], &b = pb[static_cast<size_t>(k)], &w = vb[static_cast<size_t>(k)];
        return {h00 * a.x + h10 * u.x + h01 * b.x + h11 * w.x, h00 * a.y + h10 * u.y + h01 * b.y + h11 * w.y, h00 * a.z + h10 * u.z + h01 * b.z + h11 * w.z};
    }
};

struct Sim {
    mutable ExactOrbits exact;
    mutable std::vector<int> exactOf;      // rang dans `exact` de chaque astre (-1 : pas une étoile)
    void ensureExact() const {
        if (exactOf.size() == bodies.size() && !exact.g0.empty()) return;
        exact = ExactOrbits{};
        exact.add({0, 0, 0}, {0, 0, 0});      // le Soleil
        exactOf.assign(bodies.size(), -1);
        for (size_t i = 0; i < bodies.size(); ++i)
            if (bodies[i].kind == Kind::Star && stars)
                exactOf[i] = exact.add({stars->x()[bodies[i].star], stars->y()[bodies[i].star], stars->z()[bodies[i].star]},
                                       {stars->vel(0)[bodies[i].star], stars->vel(1)[bodies[i].star], stars->vel(2)[bodies[i].star]});
    }
    const Stars* stars = nullptr;
    const eph::Set* spk = nullptr;       // éphémérides de la NASA (planètes, puis lunes) ; nul si le fichier des planètes manque
    std::vector<Body> bodies;            // 0 : le Soleil ; puis planètes et Lune ; puis les étoiles nommées de la page
    std::vector<Vec3> planetPos;         // position de chaque astre de type planète à la date courante (années-lumière, centre : Soleil)
    bool ephemValid = false;             // la date courante est dans la plage des éphémérides des planètes
    std::vector<char> planetValid;       // pour chaque astre de type planète ou lune : sa position est connue à la date courante
    std::vector<char> planetComputed;    // sa position vient du calcul (hors des fichiers de la NASA), pas d'une éphéméride : à dire à l'écran
    chaos::Run chaosRun;      // orbite de la Terre au-delà de 10 millions d'années (calcul du chaos, chaos.h)
    const phys::SystemeSolaire* outer = nullptr;      // calcul du système solaire hors de la plage de la NASA (bibliothèque univers_physique) ; nul tant qu'il n'est pas prêt
    int focus = 0;
    double years = kStartYears;          // années juliennes depuis J2000,0
    int rate = 2;
    // Vitesse libre choisie au curseur (Marc, 18/11/2026 : « mettre ce que je veux comme temps par seconde »), en années par
    // seconde ; 0 : c'est le cran kRates[rate] qui vaut. Plafond : 1 milliard d'années par seconde.
    double speed = 0;
    static constexpr double kMaxYearsPerSecond = 1.0e9;
    double yearsPerSecond() const { return speed > 0 ? speed : kRates[rate].yearsPerSecond; }
    // Cran suivant (d = +1) ou précédent (d = -1) à partir de la vitesse actuelle, même si elle vient du curseur.
    void stepRate(int d) {
        const double v = yearsPerSecond();
        int i = d > 0 ? kRateCount - 1 : 0;
        if (d > 0) {
            for (int k = 0; k < kRateCount; ++k)
                if (kRates[k].yearsPerSecond > v * 1.0001) { i = k; break; }
        } else {
            for (int k = kRateCount - 1; k >= 0; --k)
                if (kRates[k].yearsPerSecond < v * 0.9999) { i = k; break; }
        }
        rate = i;
        speed = 0;
    }
    bool paused = false, backward = false;
    double yaw = -1.2, pitch = 0.55;     // direction d'où l'on regarde l'astre suivi (radians)
    double dist = 45.0 * kAuInLy;        // distance de la caméra à l'astre suivi (années-lumière) : au départ, tout le système solaire
    bool touched = false;                // quelqu'un a pris la main : fin du lent tour d'horizon
    // Lumière choisie pour le ciel : -1 = visible (étoiles et galaxies mesurées) ; sinon rang dans skyBandLabels (cartes du
    // ciel mesurées dans une autre lumière, fenetre.cpp). skyLegend : texte de la carte montrée, à afficher en permanence.
    int skyBand = -1;
    // Choix de Marc (12/11/2026) : « 100 % mesuré » ou « meilleur rendu ». En meilleur rendu, des corrections NON mesurées
    // peuvent s'appliquer (éclat Gaia rééquilibré, lueur de la Galaxie au-delà de Gaia) ; chacune le dit à l'écran.
    bool bestLook = true;      // vue réaliste par défaut (Marc, 13/11/2026) : « 100 % mesuré » reste au menu (F4)
    double milkyWayModelShare = 0;      // part de la lueur du modèle de la Voie lactée montrée à cette image (fenetre.cpp)
    // Sources Gaia sans distance, une à une à la lunette (gaia_ciel.h) : état pour l'écran.
    bool gaiaSkyActive = false;
    uint32_t gaiaSkyStars = 0, gaiaSkyPending = 0;
    float gaiaSkyLimit = 0;
    std::vector<std::string> skyBandLabels, skyLegend;
    const std::vector<SkyBandInfo>* skyBandInfos = nullptr;      // fiches des cartes (famille, échelle, unité), pour l'interface
    // Proposition faite à Marc le 12 novembre 2026 (en attente de sa réponse, donc coupé par défaut) : montrer à toutes les
    // dates, aujourd'hui compris, la Galaxie entière du calcul (les mêmes points jusqu'à la fusion), dans les teintes des
    // étoiles, avec les étoiles mesurées par-dessus : plus de bascule entre l'ère des mesures et celle de la fusion.
    const std::vector<ArmTracer>* armTracers = nullptr;      // traceurs mesurés des bras spiraux (nul : fichier absent)
    double armPatternKmsKpc = 28.2, armPatternErrorKmsKpc = 2.1;      // vitesse de rotation du dessin des bras (Dias et al. 2019)
    const std::vector<Vec3>* armTracerWorld = nullptr;      // place à l'écran de chaque traceur à la date montrée (même ordre) ; valable quand armTracersShown
    bool armTracersShown = false;
    double loneGalaxyShare = 0;      // part montrée de la Voie lactée entière calculée (0 : pas montrée ou fichier absent)                            // dessinés à cette image (près d'aujourd'hui, vus d'assez loin)
    bool wholeGalaxy = false;
    std::vector<TaskProgress> tasks;     // calculs de fond du PC (avancement.h), relus toutes les 2 secondes
    // Scénarios du Groupe local (clones.h) : nombre, part qui finit par une fusion Voie lactée-Andromède, et date de cette
    // fusion (16e, 50e, 84e centile, en milliards d'années) ; 0 scénario : fichier absent.
    uint32_t cloneCount = 0;
    double companionShare = 0;    // part montrée d'Andromède, du Triangle et du Grand Nuage du calcul aujourd'hui (fenetre.cpp)
    const CentresReference* centres = nullptr;      // centres de référence des galaxies (fenetre.cpp), sinon le calcul de la fusion
    // Film du Groupe local (film_etoiles.h) : quand il couvre la date montrée, c'est lui qui donne le centre des galaxies
    // voisines et la place des étoiles visibles de la Voie lactée ; sinon les centres et les orbites de référence.
    const phys::film::FilmV2* film = nullptr;
    bool filmLeads = false;      // à cette image, les étoiles visibles suivent le film
    double filmEdgeYears = 0;    // non nul : la date voulue dépasse le film calculé ; elle est arrêtée à ce bord (fenetre.cpp)
    double gaiaFilmOff = 0;      // part de Gaia éteinte parce que le film mène (0 à 1, revue F1 ; fenetre.cpp)
    bool filmCovers(double tGa) const { return film && film->images() >= 5 && tGa >= film->debutGa() && tGa <= film->date(film->images() - 2); }
    uint64_t milkyWayStarCount = 0;   // étoiles visibles du modèle de la Voie lactée (vl_etoiles.bin)
    double milkyWayStarShare = 0;     // part montrée à cette image
    // Exposition (Marc, 13/11/2026) : « photo » (meilleur rendu) = exposition automatique sur la galaxie la plus brillante
    // à l'écran + étirement asinh ; « œil nu » = éclat physique, compression de Reinhard. exposureEv : réglage à la main
    // (crans de 1 IL = ×2). photoGain : gain calculé à cette image.
    bool ageingShown = false;      // vieillissement de la lumière du modèle appliqué à cette date (vieillissement.h)
    bool photoExposure = true;
    double exposureEv = 0, photoGain = 1;
    uint32_t galaxyShapeCount = 0, galaxyShapesShown = 0;      // galaxies de forme mesurée (galaxies_formes.h), montrées en particules
    uint64_t neighbourStarCount = 0;   // étoiles des galaxies voisines (voisines_etoiles.bin), montrées à toute date
    bool showClones = false;      // nuage des scénarios : seulement sur demande (Menu), il ne montre pas des galaxies mais leurs routes possibles
    double cloneMergeProbability = 0, cloneMergeGa[3] = {0, 0, 0};
    std::vector<CalcState> calcStates;
    double gaiaCellDispersionKms = 0;    // dispersion médiane des vitesses dans une case de lumière additionnée (fil Gaia), à dire à l'écran
    long gaiaOrbitLagSteps = -1;         // -1 : pas d'orbites exactes pour Gaia (fichier absent) ; sinon pas restant à calculer
    const char* planetMethod = "";       // hors des éphémérides de la NASA : « suivi pas à pas » ou « table précalculée »
    // Le temps ne dépasse jamais le calcul exact des orbites : quand la date demandée (yearsGoal) n'est pas encore
    // calculée, la date montrée (years) avance aussi vite que la carte graphique calcule, et timeHeld vaut vrai.
    // Fin de l'ère des étoiles mesurées, dans l'avenir (années après aujourd'hui). Décision de Marc (12 novembre 2026) :
    // un passage « bien fait », où les données se marient par les vraies équations. Chaque étoile mesurée suit son orbite
    // exacte dans la Galaxie tant que la Galaxie est seule : jusqu'au premier passage d'Andromède, lu dans le calcul de la
    // fusion (premier minimum de la distance entre les deux centres). Dans les 300 millions d'années qui précèdent, les
    // étoiles mesurées cèdent la place aux points du calcul (firstPassageGa : 0 si le calcul de la fusion manque ; la
    // limite reste alors à 1 milliard d'années).
    double starEraEndYears = kOrbitLimitYears, starEraFadeYears = kOrbitFadeYears, firstPassageGa = 0;
    bool timeHeld = false;
    double yearsGoal = 0;
    double lastAdvance = 0;              // années ajoutées par le dernier advance() (le temps qui défile)
    long orbitLagSteps = 0;              // pas d'orbite (1 million d'années) que la carte graphique doit encore calculer
    double asteroidEpochJd = 0;          // date des orbites des astéroïdes (0 : pas d'astéroïdes)
    uint64_t asteroidCount = 0;
    cosmo::Params cosmology;             // paramètres de l'univers en expansion (réglables à l'écran)
    bool cosmologyDirty = true;          // les distances des galaxies sont à recalculer

    // Le Soleil, les planètes (si les éphémérides sont là), puis les étoiles nommées (etoiles_noms.tsv).
    void loadBodies(const std::string& namesPath, const std::string& galaxiesPath, const std::string& photometryPath, const std::string& moonsPath) {
        bodies.clear();
        Body sun;
        sun.name = "Soleil";
        sun.kind = Kind::Sun;
        sun.bv = kSunBv;
        sun.radiusKm = 695700.0;
        sun.nature = "notre étoile";
        bodies.push_back(sun);
        if (spk) {
            auto add = [&](const PlanetRow& r, int parent) {
                Body b;
                b.name = r.name;
                b.kind = Kind::Planet;
                b.naif = r.naif;
                b.posNaif = r.naif;
                // Planètes à lunes : de440.bsp donne le centre de masse planète + lunes ; le fichier des lunes donne le centre
                // de la planète elle-même (code x99). Pour Pluton l'écart dépasse son rayon.
                Vec3 probe;
                if (r.naif >= 4 && r.naif <= 9 && planetAt(r.naif * 100 + 99, years, probe)) b.posNaif = r.naif * 100 + 99;
                b.parent = parent;
                b.periodYears = r.periodYears;
                b.radiusKm = r.radiusKm;
                b.nature = r.nature;
                bodies.push_back(b);
                return static_cast<int>(bodies.size()) - 1;
            };
            int earth = -1;
            for (const auto& r : kPlanets) {
                const int i = add(r, 0);
                if (r.naif == eph::kEarth) earth = i;
            }
            add(kMoon, earth);
            if (asteroidCat) {      // place de l'astéroïde désigné (vide au départ)
                Body a;
                a.name = "Astéroïde";
                a.kind = Kind::Asteroid;
                a.parent = 0;
                a.natureText = "astéroïde";
                bodies.push_back(a);
                asteroidBody = static_cast<int>(bodies.size()) - 1;
            }
            // Sondes : trajectoires réelles (sondes.bin). Montrées seulement aux dates où le JPL donne leur position.
            for (size_t k = 0; probes && k < probes->size(); ++k) {
                Body p;
                p.name = (*probes)[k].name;
                p.kind = Kind::Probe;
                p.probe = static_cast<int>(k);
                p.parent = 0;
                p.natureText = "sonde spatiale";
                bodies.push_back(p);
            }
            // Lunes des autres planètes (lunes.tsv : code NAIF, nom, code du centre de la planète, rayon moyen en km).
            std::ifstream mf(moonsPath);
            std::string ml;
            while (std::getline(mf, ml)) {
                int code = 0, planet = 0;
                char name[64] = "";
                double radius = 0;
                if (std::sscanf(ml.c_str(), "%d\t%63[^\t]\t%d\t%lf", &code, name, &planet, &radius) != 4) continue;
                int parent = -1;
                for (size_t i = 0; i < bodies.size(); ++i)
                    if (bodies[i].kind == Kind::Planet && bodies[i].naif == planet / 100) parent = static_cast<int>(i);
                Vec3 a, pa, b2, pb;
                const double step = 0.25 / 24.0 / 365.25;      // un quart d'heure
                if (parent < 0 || !planetAt(code, years, a) || !planetAt(bodies[static_cast<size_t>(parent)].posNaif, years, pa) ||
                    !planetAt(code, years + step, b2) || !planetAt(bodies[static_cast<size_t>(parent)].posNaif, years + step, pb))
                    continue;      // fichier d'éphémérides de cette lune absent : elle n'est pas montrée
                // Une même lune peut figurer deux fois dans les fichiers de la NASA (code provisoire, puis code définitif) :
                // si une lune déjà chargée de la même planète est à moins de 1 000 km, c'est elle, on ne la double pas.
                bool twin = false;
                for (size_t j = 0; j < bodies.size() && !twin; ++j) {
                    Vec3 o;
                    if (bodies[j].kind != Kind::Planet || bodies[j].parent != parent || !planetAt(bodies[j].posNaif, years, o)) continue;
                    const Vec3 gap = o - a;
                    twin = std::sqrt(dot(gap, gap)) * kLyInKm < 1000.0;
                }
                if (twin) continue;
                Body m;
                m.name = name;
                m.kind = Kind::Planet;
                m.naif = code;
                m.posNaif = code;
                m.parent = parent;
                m.radiusKm = radius;
                m.natureText = "lune de " + bodies[static_cast<size_t>(parent)].name;
                // Durée d'un tour, pour tracer l'orbite : angle parcouru autour de la planète en un quart d'heure.
                const Vec3 r1 = a - pa, r2 = b2 - pb;
                const double angle = std::acos(std::clamp(dot(r1, r2) / std::sqrt(dot(r1, r1) * dot(r2, r2)), -1.0, 1.0));
                m.periodYears = angle > 0 ? 2.0 * kPi / angle * step : 0;
                // Orbite allongée : la vitesse du moment ne donne pas la durée du tour (Callirrhoé : 3,09 ans au lieu de 2).
                // On suit donc la lune dans les éphémérides jusqu'à ce qu'elle ait fait un tour complet (360 degrés cumulés).
                if (m.periodYears > 0) {
                    const double ds = m.periodYears / 400.0;
                    double turned = 0, t = years;
                    Vec3 prev = r1;
                    bool whole = true;
                    for (int k = 0; k < 4000 && turned < 2.0 * kPi && whole; ++k) {
                        Vec3 q, pq;
                        t += ds;
                        whole = planetAt(code, t, q) && planetAt(bodies[static_cast<size_t>(parent)].posNaif, t, pq);
                        if (!whole) break;
                        const Vec3 cur = q - pq;
                        const double da = std::acos(std::clamp(dot(prev, cur) / std::sqrt(dot(prev, prev) * dot(cur, cur)), -1.0, 1.0));
                        if (turned + da >= 2.0 * kPi) {      // fin du tour à l'intérieur de ce pas
                            t -= ds * (turned + da - 2.0 * kPi) / da;
                            turned = 2.0 * kPi;
                            break;
                        }
                        turned += da;
                        prev = cur;
                    }
                    if (whole && turned >= 2.0 * kPi) m.periodYears = t - years;
                }
                if (m.periodYears > 0) bodies.push_back(m);
            }
        }
        std::string line;
        // Éclat et teinte des planètes (planetes.tsv : code NAIF, magnitude V(1,0), rouge, vert, bleu).
        std::ifstream pf(photometryPath);
        while (std::getline(pf, line)) {
            int naif = 0, r = -1, g = -1, bl = -1;
            double h = 0;
            if (std::sscanf(line.c_str(), "%d %lf %d %d %d", &naif, &h, &r, &g, &bl) != 5) continue;
            for (Body& b : bodies)
                if (b.kind == Kind::Planet && b.naif == naif) {
                    b.h = h;
                    b.hasPhotometry = true;
                    b.tint[0] = r;
                    b.tint[1] = g;
                    b.tint[2] = bl;
                }
        }
        std::ifstream f(namesPath);
        while (std::getline(f, line)) {
            const size_t a = line.find('\t'), b = line.find('\t', a + 1);
            if (a == std::string::npos) continue;
            Body body;
            body.star = std::strtoll(line.substr(0, a).c_str(), nullptr, 10);
            body.name = line.substr(a + 1, b == std::string::npos ? std::string::npos : b - a - 1);
            body.nature = "étoile";
            if (body.star >= 0 && static_cast<uint64_t>(body.star) < stars->n) {
                body.bv = stars->bv()[body.star];
                bodies.push_back(body);
            }
        }
        // Galaxies nommées (galaxies_noms.tsv : nom, x, y, z en années-lumière, genre, priorité).
        // Puis, s'il est à côté, galaxies_cf4.tsv : 55 637 galaxies à distance mesurée (Cosmicflows-4, noms OpenNGC),
        // écrit par pipeline/natif/galaxies_cf4.py ; priorité 9 : nom montré seulement de près ou au survol.
        const std::string cf4Path = galaxiesPath.substr(0, galaxiesPath.find_last_of("/\\") + 1) + "galaxies_cf4.tsv";
        // Puis galaxies_formes_noms.tsv : Messier, NGC et IC de forme mesurée (pipeline/natif/galaxies_formes.py), cherchables.
        const std::string formesPath = galaxiesPath.substr(0, galaxiesPath.find_last_of("/\\") + 1) + "galaxies_formes_noms.tsv";
        for (const std::string& path : {galaxiesPath, cf4Path, formesPath})
        for (std::ifstream gf(path); std::getline(gf, line);) {
            std::vector<std::string> cols;
            size_t from = 0;
            for (size_t tab; (tab = line.find('\t', from)) != std::string::npos; from = tab + 1) cols.push_back(line.substr(from, tab - from));
            cols.push_back(line.substr(from));
            if (cols.size() < 6) continue;
            Body body;
            body.name = cols[0];
            body.kind = Kind::Galaxy;
            body.fixedPos = {std::atof(cols[1].c_str()), std::atof(cols[2].c_str()), std::atof(cols[3].c_str())};
            body.natureText = cols[4];
            body.priority = std::atoi(cols[5].c_str());
            bodies.push_back(body);
        }
        // Le centre de notre galaxie : Sagittarius A*, à 8,2 kpc dans la direction mesurée (mêmes valeurs que la page).
        Body centre;
        centre.name = "Centre de la Voie lactée";
        centre.kind = Kind::Galaxy;
        centre.fixedPos = fromGalactocentric({0, 0, 0});
        centre.natureText = "centre de notre galaxie (Sagittarius A*)";
        bodies.push_back(centre);
        planetPos.assign(bodies.size(), {0, 0, 0});
        replayRef.assign(bodies.size(), -1);
        replayRef.back() = -2;
        refreshEphemeris();
        refreshGalaxies();
    }

    // Position héliocentrique d'un corps des éphémérides à une date donnée (années-lumière, écliptique J2000). false : hors de la plage.
    bool planetAt(int naif, double atYears, Vec3& out) const {
        if (!spk) return false;
        const double et = atYears * kYearSeconds + kTdbMinusUtc;
        eph::Vec p, v, s, sv;
        if (!spk->state(naif, et, p, v) || !spk->state(eph::kSun, et, s, sv)) return false;      // hors de la plage, ou fichier absent
        const eph::Vec e = eph::toEcliptic({p.x - s.x, p.y - s.y, p.z - s.z});
        out = {e.x / kLyInKm, e.y / kLyInKm, e.z / kLyInKm};
        return true;
    }

    void refreshEphemeris() {
        ephemValid = spk != nullptr;
        planetValid.assign(bodies.size(), 0);
        planetComputed.assign(bodies.size(), 0);
        for (size_t i = 0; i < bodies.size(); ++i) {
            if (bodies[i].kind == Kind::Asteroid) {      // astéroïde désigné : son orbite mesurée, à moins de 300 ans de sa date
                const double jd = 2451545.0 + years * 365.25 + kTdbMinusUtc / 86400.0;
                if (asteroidCat && asteroidSel >= 0 && std::fabs(jd - asteroidCat->epochJd) < 300.0 * 365.25) {
                    double au[3];
                    asteroidCat->position(static_cast<size_t>(asteroidSel), jd, au);
                    planetPos[i] = {au[0] * kAuInLy, au[1] * kAuInLy, au[2] * kAuInLy};
                    planetValid[i] = 1;
                }
                continue;
            }
            if (bodies[i].kind == Kind::Probe) {      // sonde : sa trajectoire réelle, ou rien hors des dates fournies
                double pos[3], vel[3];
                if (probes && (*probes)[static_cast<size_t>(bodies[i].probe)].at(2451545.0 + years * 365.25 + kTdbMinusUtc / 86400.0, pos, vel)) {
                    planetPos[i] = {pos[0] / kLyInKm, pos[1] / kLyInKm, pos[2] / kLyInKm};
                    planetValid[i] = 1;
                }
                continue;
            }
            if (bodies[i].kind != Kind::Planet) continue;
            // Le centre de la planète vient du fichier de ses lunes, dont la plage de dates est plus courte que celle de
            // de440.bsp : hors de cette plage, on revient au centre de masse planète + lunes, toujours donné par de440.bsp.
            planetValid[i] = (planetAt(bodies[i].posNaif, years, planetPos[i]) || planetAt(bodies[i].naif, years, planetPos[i])) ? 1 : 0;
            if (bodies[i].naif == eph::kEarth && !planetValid[i]) ephemValid = false;      // la Terre sans position : hors de la plage de de440.bsp
        }
        // Hors des éphémérides de la NASA : suivi pas à pas dans les plages de calcul direct du fil physique (20 000 ans de
        // chaque côté de DE440), table précalculée au-delà, rien hors de la table.
        planetMethod = "";
        if (!ephemValid && outer) {
            const double jdNow = 2451545.0 + years * 365.25;
            const phys::Plage av = outer->plageAvant(), ap = outer->plageApres(), tb = outer->plageTable();
            if ((jdNow >= av.debut && jdNow <= av.fin) || (jdNow >= ap.debut && jdNow <= ap.fin)) planetMethod = "suivi pas à pas";
            else if (jdNow >= tb.debut && jdNow <= tb.fin) planetMethod = "table précalculée";
        }
        if (ephemValid || !outer) return;
        // Hors de la plage de la NASA : positions calculées (gravité mutuelle partie de l'état DE440 aux bornes, puis table
        // des orbites sur des millions d'années). Le suivi avance pas à pas avec le temps qui défile. La Lune vient de la
        // théorie de Meeus (lune.h, de -2000 à +6000) ; les autres lunes restent cachées : leur position est inconnue.
        if (!suivi_ || suiviOf_ != outer) {
            suivi_ = std::make_unique<phys::Suivi>(*outer);
            suiviOf_ = outer;
        }
        const double jd = 2451545.0 + years * 365.25;
        if (!suivi_->aller(jd)) return;
        phys::Vec3 moonGeo;
        const bool hasMoon = phys::lune::geocentrique(jd, moonGeo);
        Vec3 earth{0, 0, 0};
        bool hasEarth = false;
        for (size_t i = 0; i < bodies.size(); ++i) {
            const Body& b = bodies[i];
            if (b.kind != Kind::Planet || b.parent != 0 || planetValid[i]) continue;
            // Codes du calcul : centres de masse 1 à 9 (3 : Terre + Lune).
            const int code = b.naif >= 100 ? b.naif / 100 : b.naif;
            phys::Vec3 pos, vel;
            phys::Statut statut;
            if (!suivi_->etat(code, pos, vel, statut)) continue;
            if (b.naif == eph::kEarth && hasMoon) {      // Terre = centre de masse Terre-Lune moins la part de la Lune
                pos = {pos.x - phys::lune::kFractionLune * moonGeo.x, pos.y - phys::lune::kFractionLune * moonGeo.y, pos.z - phys::lune::kFractionLune * moonGeo.z};
                earth = {pos.x / kLyInKm, pos.y / kLyInKm, pos.z / kLyInKm};
                hasEarth = true;
            }
            planetPos[i] = {pos.x / kLyInKm, pos.y / kLyInKm, pos.z / kLyInKm};
            planetValid[i] = 1;
            planetComputed[i] = 1;
        }
        for (size_t i = 0; hasEarth && i < bodies.size(); ++i)
            if (bodies[i].kind == Kind::Planet && bodies[i].naif == eph::kMoon && !planetValid[i]) {
                planetPos[i] = {earth.x + moonGeo.x / kLyInKm, earth.y + moonGeo.y / kLyInKm, earth.z + moonGeo.z / kLyInKm};
                planetValid[i] = 1;
                planetComputed[i] = 1;
            }
    }
    std::unique_ptr<phys::Suivi> suivi_;
    const phys::SystemeSolaire* suiviOf_ = nullptr;

    // ---------------------------------------------------------------- temps profond et Groupe local
    // Jusqu'à 3 millions d'années d'aujourd'hui, tout est montré dans le repère du Soleil. Au-delà (vers l'avenir, jusqu'à
    // la fin du calcul de la fusion), seules les galaxies dont le mouvement est calculé sont montrées : celles du calcul
    // complet de la rencontre avec Andromède (phys::fusion::Rejeu). Le repère reste celui d'aujourd'hui, attaché au centre
    // de la Voie lactée : l'origine est l'endroit où se trouve le Soleil aujourd'hui par rapport à ce centre.
    uint64_t gaiaCount = 0;      // nombre d'étoiles du catalogue Gaia chargé (0 : absent)
    uint64_t gaiaReliableCount = 0;      // étoiles Gaia à orbite fiable (gaia.h, docs/gaia-rayons.md) : seules à avancer loin d'aujourd'hui
    double gaiaReliableLight = 0;        // part de leur lumière
    uint64_t gaiaRebalancedCount = 0;    // étoiles Gaia à l'éclat rééquilibré vu de loin (hypothèse, docs/gaia-rayons.md)
    double gaiaRebalancedShift = 0;      // part de la lumière déplacée
    bool hasGaia = false, hasGaiaAggregate = false, hasMilkyWay = false;      // catalogue Gaia et Voie lactée en volume chargés (pour les textes de l'interface)
    const phys::fusion::Rejeu* replay = nullptr;
    // Indicateur de complétude et de précision par échelle (completude.h), calculé une fois au chargement ; nul avant.
    const std::array<completude::Echelle, 5>* completeness = nullptr;
    // Astéroïde désigné : un seul à la fois occupe la place `asteroidBody` de la liste des astres (nom, fiche, suivi).
    const asteroides::Catalogue* asteroidCat = nullptr;      // à poser avant loadBodies
    int asteroidBody = -1;      // rang de cette place dans bodies ; -1 : pas de catalogue
    int asteroidSel = -1;       // rang de l'astéroïde désigné dans le catalogue ; -1 : aucun
    const std::vector<sondes::Probe>* probes = nullptr;      // trajectoires réelles des sondes (JPL Horizons) ; à poser avant loadBodies
    std::vector<int> replayRef;          // par astre : -1 aucun ; 100 + g : centre de la galaxie g du calcul ; k >= 0 : traceur k ; -2 : centre de la Voie lactée
    std::vector<Vec3> galPos;            // position de chaque galaxie à la date courante
    std::vector<char> galValid;

    bool deepTime() const { return std::fabs(years - kStartYears) > kLinearLimitYears; }
    double replayGa() const { return (years - kStartYears) / 1.0e9; }
    // Fin du temps : la plus tardive des fins du film du Groupe local et de l'ancien calcul ; sans l'un ni l'autre, la limite
    // du mouvement en ligne droite (revue F8 : le film seul ne laissait pas dépasser cette limite).
    double maxYears() const {
        double finGa = replay ? replay->finGa() : 0.0;
        if (film && film->images() >= 5) finGa = std::max(finGa, film->date(film->images() - 2));
        return kStartYears + (finGa > 0.0 ? finGa * 1.0e9 : kLinearLimitYears);
    }
    double minYears() const { return kStartYears - kOrbitLimitYears; }
    // Part des étoiles mesurées encore montrée (1 jusqu'à 800 millions d'années, 0 à 1 milliard) ; le calcul de la fusion
    // prend la part restante.
    double starShare() const {
        const double t = years - kStartYears;
        if (t < 0) return std::clamp((kOrbitLimitYears + t) / (kOrbitLimitYears - kOrbitFadeYears), 0.0, 1.0);      // passé : jusqu'à -1 milliard d'années
        return std::clamp((starEraEndYears - t) / (starEraEndYears - starEraFadeYears), 0.0, 1.0);
    }
    // Déplacement de ce qui est fixe par rapport au centre de la Galaxie : le Soleil tourne, le monde reste centré sur lui.
    // Place du Soleil (galactocentrique, kpc) à la date montrée, par le calcul de l'appli (origine du monde affiché).
    phys::Vec3 sunGalacto() const { ensureExact(); return exact.position(0, years); }

    Vec3 sunShift() const {
        ensureExact();
        const phys::Vec3 s = exact.position(0, years), s0 = phys::galaxie::soleilPos();
        return orbite::versEcliptique({-(s.x - s0.x) * orbite::kKpcLy, -(s.y - s0.y) * orbite::kKpcLy, -(s.z - s0.z) * orbite::kKpcLy});
    }

    // Repère galactocentrique de la page (kpc, relatif au centre de la Voie lactée) -> repère du simulateur (années-lumière,
    // écliptique J2000, origine : place actuelle du Soleil). Matrice DATA.M_GAL2ECL de la page (app/gen/data.js) ; place du
    // Soleil : 8,2 kpc du centre (GAL.R0), direction de Sagittarius A* (DATA.SGRA_GAL).
    static Vec3 fromGalactocentric(phys::Vec3 g) {
        static constexpr double M[3][3] = {{-0.0548756577, 0.4941094372, -0.8676661376}, {-0.993821367, -0.1109908412, -0.0003515418}, {-0.0964766946, 0.8622858559, 0.4971472117}};
        const phys::Vec3 s = phys::galaxie::soleilPos();
        const double v[3] = {g.x - s.x, g.y - s.y, g.z - s.z};
        const double kpc = 3261.5637769;
        return {(M[0][0] * v[0] + M[0][1] * v[1] + M[0][2] * v[2]) * kpc, (M[1][0] * v[0] + M[1][1] * v[1] + M[1][2] * v[2]) * kpc,
                (M[2][0] * v[0] + M[2][1] * v[1] + M[2][2] * v[2]) * kpc};
    }

    // Relie les galaxies nommées au calcul de la fusion (noms des traceurs : fusion_noms.tsv, dans l'ordre du calcul).
    void linkReplay(const phys::fusion::Rejeu* r, const std::string& namesPath) {
        replay = r;
        if (r) {      // premier passage d'Andromède : premier minimum de la distance des centres
            double prev = 1e300, before = 1e300;
            for (double t = 0; t <= r->finGa(); t += 0.005) {
                phys::Vec3 g;
                if (!r->centre(phys::fusion::kAndromede, t, g)) break;
                const double d = std::sqrt(g.x * g.x + g.y * g.y + g.z * g.z);
                if (prev < before && prev < d && prev < 400.0) {      // le pas d'avant était un minimum
                    firstPassageGa = t - 0.005;
                    break;
                }
                before = prev;
                prev = d;
            }
            if (firstPassageGa > 1.0) {
                starEraEndYears = firstPassageGa * 1.0e9;
                starEraFadeYears = starEraEndYears - 3.0e8;
            }
        }
        replayRef.assign(bodies.size(), -1);
        std::vector<std::string> names;
        std::ifstream f(namesPath);
        for (std::string line; std::getline(f, line);) names.push_back(line);
        for (size_t i = 0; i < bodies.size(); ++i) {
            const Body& b = bodies[i];
            if (b.kind != Kind::Galaxy) continue;
            if (b.name == "Centre de la Voie lactée") replayRef[i] = -2;
            else if (!r) continue;
            else if (b.name == "Andromède (M31)") replayRef[i] = 100 + phys::fusion::kAndromede;
            else if (b.name == "Galaxie du Triangle (M33)") replayRef[i] = 100 + phys::fusion::kTriangle;
            else if (b.name == "Grand Nuage de Magellan") replayRef[i] = 100 + phys::fusion::kGrandNuage;
            else
                for (size_t k = 0; k < names.size() && static_cast<int>(k) < r->nombreTraceurs(); ++k)
                    if (names[k] == b.name) replayRef[i] = static_cast<int>(k);
        }
        refreshGalaxies();
    }

    void refreshGalaxies() {
        galPos.assign(bodies.size(), {0, 0, 0});
        galValid.assign(bodies.size(), 0);
        const double tGa = replayGa();
        const bool deep = deepTime();
        const Vec3 shift = sunShift();
        for (size_t i = 0; i < bodies.size(); ++i) {
            const Body& b = bodies[i];
            if (b.kind != Kind::Galaxy) continue;
            // Centres de référence (centres_reference.h) : Andromède, Triangle, Nuages de Magellan, en bloc le long de leur
            // centre, à toute date calculée, aujourd'hui compris (mêmes valeurs que la table unique et que leurs étoiles).
            const int ci = centres && centres->ready ? CentresReference::indexOf(b.name) : -1;
            if (ci >= 0) {
                phys::Vec3 g;
                bool ok = false;
                if (filmCovers(tGa) && ci < film->galaxies() && film->centre(ci, tGa, g)) {
                    // Revue F4 : le centre du film à t = 0 n'est pas exactement le centre mesuré (decalage_a_t0 n'est pas dans
                    // l'index du film v2). L'écart à la date de départ commune est retiré, puis s'efface sur 100 Ma : plus de
                    // saut au passage référence -> film, et le film reprend seul la main loin d'aujourd'hui.
                    const double t0 = std::clamp(0.0, film->debutGa(), film->date(film->images() - 2));
                    phys::Vec3 f0, r0;
                    if (film->centre(ci, t0, f0) && centres->centre(ci, t0, r0)) {
                        const double w = std::clamp(1.0 - std::fabs(tGa - t0) / 0.1, 0.0, 1.0);
                        g = {g.x - w * (f0.x - r0.x), g.y - w * (f0.y - r0.y), g.z - w * (f0.z - r0.z)};
                    }
                    ok = true;
                } else
                    ok = centres->centre(ci, tGa, g);
                if (ok) {
                    const Vec3 w = fromGalactocentric(g);
                    galPos[i] = {w.x + shift.x, w.y + shift.y, w.z + shift.z};
                    galValid[i] = 1;
                }
                continue;
            }
            const int ref = i < replayRef.size() ? replayRef[i] : -1;
            if (ref == -2 || !deep) {      // aujourd'hui (à 3 millions d'années près) : la position mesurée
                galPos[i] = {b.fixedPos.x + shift.x, b.fixedPos.y + shift.y, b.fixedPos.z + shift.z};
                galValid[i] = 1;
                continue;
            }
            phys::Vec3 g;
            const bool ok = replay && ref >= 0 && (ref >= 100 ? replay->centre(ref - 100, tGa, g) : replay->traceur(ref, tGa, g));
            if (!ok) continue;      // mouvement non calculé : la galaxie n'est pas montrée à cette date
            const Vec3 w = fromGalactocentric(g);
            galPos[i] = {w.x + shift.x, w.y + shift.y, w.z + shift.z};
            galValid[i] = 1;
        }
    }

    // Une planète ou une lune n'est montrée que si sa position est connue à la date courante.
    // Une étoile n'est montrée qu'à moins de 3 millions d'années d'aujourd'hui (au-delà, la ligne droite ne vaut plus) ;
    // le Soleil, tant que le système solaire est suivi (10 millions d'années) ; une galaxie, si sa position est connue.
    bool visible(int i) const {
        const Body& b = bodies[static_cast<size_t>(i)];
        if (b.kind == Kind::Planet || b.kind == Kind::Probe || b.kind == Kind::Asteroid) return planetValid[static_cast<size_t>(i)] != 0;
        if (b.kind == Kind::Galaxy) return static_cast<size_t>(i) < galValid.size() && galValid[static_cast<size_t>(i)];
        if (b.kind == Kind::Sun) return starShare() > 0;      // suivi sur son orbite autour de la Galaxie, comme les étoiles
        return starShare() > 0;      // étoile : suivie sur son orbite calculée, tant que cette orbite a un sens
    }

    // Position à la date courante (années-lumière, repère écliptique centré sur le Soleil).
    Vec3 position(int i) const {
        const Body& b = bodies[static_cast<size_t>(i)];
        if (b.kind == Kind::Sun) return {0, 0, 0};
        if (b.kind == Kind::Planet || b.kind == Kind::Probe || b.kind == Kind::Asteroid) return planetPos[static_cast<size_t>(i)];
        if (b.kind == Kind::Galaxy) return static_cast<size_t>(i) < galPos.size() && galValid[static_cast<size_t>(i)] ? galPos[static_cast<size_t>(i)] : b.fixedPos;
        // Étoile : ligne droite à la vitesse mesurée, raccordée à son orbite calculée autour de la Galaxie.
        const Vec3 p0{stars->x()[b.star], stars->y()[b.star], stars->z()[b.star]};
        // Même calcul que la carte graphique (etoiles_orbite.vert) : orbite exacte relative au Soleil, raccordée à la ligne droite.
        const double kt = years * kKmsToLyPerYear, w = orbite::poidsOrbite(years);      // années depuis J2000, date des positions du catalogue
        const Vec3 lin{p0.x + stars->vel(0)[b.star] * kt, p0.y + stars->vel(1)[b.star] * kt, p0.z + stars->vel(2)[b.star] * kt};
        ensureExact();
        const int k = exactOf[static_cast<size_t>(i)];
        if (w < 1e-9 || k < 0) return lin;
        const phys::Vec3 e = exact.position(k, years), s = exact.position(0, years);
        const Vec3 orb = orbite::versEcliptique({(e.x - s.x) * orbite::kKpcLy, (e.y - s.y) * orbite::kKpcLy, (e.z - s.z) * orbite::kKpcLy});
        return {lin.x * (1.0 - w) + orb.x * w, lin.y * (1.0 - w) + orb.y * w, lin.z * (1.0 - w) + orb.z * w};
    }
    double speedKms(int i) const {
        const Body& b = bodies[static_cast<size_t>(i)];
        if (b.kind != Kind::Star) return 0;
        double s = 0;
        for (int a = 0; a < 3; ++a) s += static_cast<double>(stars->vel(a)[b.star]) * stars->vel(a)[b.star];
        return std::sqrt(s);
    }
    // Magnitude apparente d'un astre vu d'un point donné.
    // Étoiles : loi en 1/d². Planètes : lumière du Soleil renvoyée, m = H + 5 log10(r d) - 2,5 log10(phase), avec r et d
    // en UA et la phase d'une sphère mate (loi de Lambert) [approximation assumée de la vraie courbe de phase].
    double apparentMag(int i, Vec3 from) const {
        const Body& b = bodies[static_cast<size_t>(i)];
        if (b.kind == Kind::Galaxy || b.kind == Kind::Probe || b.kind == Kind::Asteroid) return 99.0;      // éclat des galaxies et des sondes : pas dans les données
        const Vec3 p = position(i), d = p - from;
        const double dist = std::max(std::sqrt(dot(d, d)), 1e-15);
        if (b.kind == Kind::Planet) {
            if (!b.hasPhotometry) return 99.0;      // éclat non renseigné : on ne l'invente pas
            const double r = std::max(std::sqrt(dot(p, p)), 1e-15);
            const double cosA = std::clamp((dot(p, d)) / (r * dist), -1.0, 1.0);      // angle Soleil-planète-observateur
            const double alpha = std::acos(cosA);
            const double phase = std::max((std::sin(alpha) + (kPi - alpha) * std::cos(alpha)) / kPi, 1e-6);
            return b.h + 5.0 * std::log10((r / kAuInLy) * (dist / kAuInLy)) - 2.5 * std::log10(phase);
        }
        const double absMag = b.kind == Kind::Sun ? kSunAbsMag : stars->mag()[b.star];
        return absMag + 5.0 * std::log10(dist / 3.2615638) - 5.0;
    }

    // ------------------------------------------------------------ caméra, vols et gestes (interface)
    // Vol vers un astre : le point visé glisse de l'ancien astre au nouveau pendant que la distance recule puis
    // avance (en échelle logarithmique), pour que l'on voie toujours d'où l'on part et où l'on va.
    static constexpr double kFlySeconds = 1.8;
    bool flying = false;
    double flyT = 0;                 // avancement du vol, de 0 à 1
    Vec3 flyFrom{0, 0, 0};           // point visé au départ du vol
    double flyFromDist = 1, flyToDist = 1, flyPeakDist = 1;
    struct View {
        int focus;
        double dist, yaw, pitch;
    };
    std::vector<View> history;      // vues précédentes, pour « Retour »

    static double ease(double s) { return s * s * s * (s * (s * 6.0 - 15.0) + 10.0); }      // départ et arrivée en douceur
    // Point visé à l'instant présent (pendant un vol : entre l'ancien astre et le nouveau).
    Vec3 target() const {
        const Vec3 to = position(focus);
        if (!flying) return to;
        const double e = ease(flyT);
        return {flyFrom.x + (to.x - flyFrom.x) * e, flyFrom.y + (to.y - flyFrom.y) * e, flyFrom.z + (to.z - flyFrom.z) * e};
    }
    Camera camera(double aspect) const {
        const Vec3 t = target();
        const Vec3 dir{std::cos(pitch) * std::cos(yaw), std::cos(pitch) * std::sin(yaw), std::sin(pitch)};
        return lookAt({t.x + dist * dir.x, t.y + dist * dir.y, t.z + dist * dir.z}, t, fovDeg, aspect);
    }
    // Distance d'arrivée près d'un astre : de quoi le voir dans son voisinage.
    double arriveDist(int i, double from) const {
        const Body& b = bodies[static_cast<size_t>(i)];
        double arrive = 50.0;                                                 // étoile : on garde ou on se rapproche à 50 années-lumière
        if (b.kind == Kind::Sun) arrive = 45.0 * kAuInLy;
        if (b.kind == Kind::Planet) arrive = 6.0 * b.radiusKm / kLyInKm;      // planète ou lune : elle remplit un bon tiers de l'écran
        if (b.kind == Kind::Planet && b.radiusKm <= 0) arrive = 1.0e6 / kLyInKm;      // lune de rayon non mesuré (un point) : à un million de km
        if (b.kind == Kind::Asteroid) arrive = 0.05 * kAuInLy;                // astéroïde (un point) : on voit ses voisins de la ceinture
        if (b.kind == Kind::Probe) arrive = 3.0e6 / kLyInKm;                  // sonde (un point) : on voit son voisinage, à 3 millions de km
        double d = std::clamp(std::min(from, arrive), minDist(i), kMaxDist);
        if (b.kind == Kind::Galaxy) d = std::max(d, 3.0e5);                  // une galaxie se regarde de loin
        return d;
    }
    void remember() {
        if (!history.empty() && history.back().focus == focus && std::fabs(std::log(history.back().dist / dist)) < 0.05) return;
        history.push_back({focus, dist, yaw, pitch});
        if (history.size() > 40) history.erase(history.begin());
    }
    // Vol fluide vers l'astre i, arrivée à la distance `toDist` (0 : distance d'arrivée habituelle).
    void flyTo(int i, double toDist = 0) {
        if (i < 0 || i >= static_cast<int>(bodies.size()) || !visible(i)) return;
        remember();
        flyFrom = target();
        flyFromDist = dist;
        focus = i;
        flyToDist = toDist > 0 ? std::clamp(toDist, minDist(i), kMaxDist) : arriveDist(i, dist);
        const Vec3 gap = position(i) - flyFrom;
        const double sep = std::sqrt(dot(gap, gap));
        // Au milieu du vol, on recule assez pour voir les deux astres à la fois.
        flyPeakDist = std::max({flyFromDist, flyToDist, 0.9 * sep});
        flyT = 0;
        flying = true;
        touched = true;
    }
    void back() {
        if (history.empty()) return;
        const View v = history.back();
        history.pop_back();
        if (!visible(v.focus)) return;
        flyFrom = target();
        flyFromDist = dist;
        focus = v.focus;
        flyToDist = v.dist;
        const Vec3 gap = position(v.focus) - flyFrom;
        flyPeakDist = std::max({flyFromDist, flyToDist, 0.9 * std::sqrt(dot(gap, gap))});
        flyT = 0;
        flying = true;
        touched = true;
    }
    void stepFlight(double dt) {
        if (!flying) return;
        flyT = std::min(1.0, flyT + dt / kFlySeconds);
        // Distance : courbe de Bézier en logarithme, départ -> sommet -> arrivée.
        const double s = ease(flyT), a = std::log(flyFromDist), m = std::log(flyPeakDist), b = std::log(flyToDist);
        dist = std::exp((1 - s) * (1 - s) * a + 2 * s * (1 - s) * m + s * s * b);
        if (flyT >= 1.0) {
            flying = false;
            dist = flyToDist;
        }
    }

    // Les étoiles pâlissent en 1/d² : loin de tout, on multiplie leur éclat pour qu'elles restent visibles, et on le dit.
    double brightnessBoost() const {
        // Jusqu'à 300 années-lumière l'éclat est multiplié pour compenser la distance (au plus 100 fois), puis il reste à
        // 100. À partir de là, chaque pixel additionne de plus en plus d'étoiles : l'image passe d'elle-même des étoiles une
        // à une à leur lumière regroupée, à éclat par pixel constant, et l'ensemble rapetisse en s'éloignant, comme une vraie
        // galaxie. Demande de Marc (12 novembre 2026) : « quand on augmente les distances on généralise au fur et à mesure ».
        // Ce qu'on voit de loin est donc la somme des étoiles MESURÉES (rien d'ajouté) : un nuage autour du Soleil, parce que
        // Gaia ne mesure bien les distances que dans notre région de la Galaxie.
        const double k = std::clamp(dist / 30.0, 1.0, 10.0);
        return k * k;
    }
    // Astéroïdes : un point chacun de près ; au-delà de 2,5 fois la distance Terre-Soleil, l'éclat de chaque point baisse
    // comme l'inverse du carré de la distance, si bien que la ceinture garde le même éclat par pixel pendant que ses
    // points se fondent en un anneau, puis en une tache (même principe que pour les étoiles : on regroupe en s'éloignant).
    // Montrés seulement à moins de 300 ans de la date de leurs orbites : au-delà, l'orbite simple ne vaut plus.
    double asteroidGain(double epochJd) const {
        const double au = dist / kAuInLy;
        const double fade = std::min(1.0, (2.5 / std::max(au, 1e-9)) * (2.5 / std::max(au, 1e-9)));      // 2,5 : avec 1,58 million d'astéroïdes, la ceinture blanchissait au-delà (capture)
        const double epochYears = (epochJd - 2451545.0) / 365.25;
        return std::fabs(years - epochYears) < 300.0 ? 0.30 * fade : 0.0;
    }
    // Éclat donné à chaque galaxie des relevés : nul tant qu'on est dans la Voie lactée, plein au-delà de 3 millions d'années-lumière.
    double galaxyGain() const {
        const double t = std::clamp((std::log10(std::max(dist, 1.0)) - 4.5) / 2.0, 0.0, 1.0);
        return 0.10 * t * t * (3.0 - 2.0 * t);
    }

    void advance(double dt) {
        const double before = years;
        if (!paused) years += (backward ? -1.0 : 1.0) * yearsPerSecond() * dt;
        years = std::clamp(years, minYears(), maxYears());
        lastAdvance = years - before;
        if (!touched) yaw += 0.035 * dt;      // lent tour d'horizon, 2 degrés par seconde
        refreshEphemeris();
        refreshGalaxies();
        stepFlight(dt);
        if (!visible(focus)) {                // l'astre suivi n'a plus de position connue : retour au Soleil, ou au centre de la Voie lactée
            focus = 0;
            if (!visible(0))
                for (size_t i = 0; i < bodies.size(); ++i)
                    if (i < replayRef.size() && replayRef[i] == -2) {
                        focus = static_cast<int>(i);
                        dist = std::max(dist, 3.0e5);
                    }
            flying = false;
        }
    }
    double minDist(int i) const {      // on s'arrête un peu au-dessus de la surface (1,25 rayon du centre)
        if (bodies[static_cast<size_t>(i)].kind == Kind::Galaxy) return 1.0e3;
        if (bodies[static_cast<size_t>(i)].kind == Kind::Probe || bodies[static_cast<size_t>(i)].kind == Kind::Asteroid) return 1.0e-10;      // environ 1 000 km
        return std::max(1.25 * bodies[static_cast<size_t>(i)].radiusKm / kLyInKm, 2.0e-10);
    }
    static constexpr double kMaxDist = 9.0e10;      // un peu plus que la distance des objets les plus lointains (z = 7)
    // Champ de vision (Ctrl + molette) : de 60° à 0,5°. Grossit ce qui n'a pas de profondeur (cartes du ciel « Lumière »,
    // ciel lointain), comme une lunette ; la molette seule rapproche la caméra.
    static constexpr double kFovMax = 60.0, kFovMin = 0.5;
    double fovDeg = kFovMax;
    // Grossir, c'est aussi poser plus longtemps, comme à la lunette : l'éclat de tout ce qui est dessiné est multiplié par
    // le carré du grossissement (au plus 10 000, soit 10 magnitudes de plus). Réglage d'affichage, dit à l'écran ; les
    // mesures ne changent pas.
    double fieldGain() const { return std::min(std::pow(kFovMax / fovDeg, 2.0), 1.0e4); }
    void zoomField(double notches) {
        if (notches != 0) fovDeg = std::clamp(fovDeg * std::pow(0.8, notches), kFovMin, kFovMax);
    }
    void zoom(double notches) {
        if (notches == 0) return;
        if (flying) {      // molette pendant un vol : on corrige la distance d'arrivée, sans casser le vol
            flyToDist = std::clamp(flyToDist * std::pow(0.8, notches), minDist(focus), kMaxDist);
            return;
        }
        dist = std::clamp(dist * std::pow(0.8, notches), minDist(focus), kMaxDist);
    }
    void orbit(double dx, double dy) {
        yaw -= dx * 0.005;
        pitch = std::clamp(pitch + dy * 0.005, -1.55, 1.55);
    }
    // Suivre l'astre i tout de suite, sans vol (départ du programme, contrôles).
    // Désigne l'astéroïde de rang k du catalogue : il prend la place `asteroidBody` (nom, position) et peut être suivi.
    // Rend le rang de cette place dans bodies, ou -1 s'il n'y a pas de catalogue.
    int selectAsteroid(int k) {
        if (!asteroidCat || asteroidBody < 0 || k < 0 || static_cast<uint64_t>(k) >= asteroidCat->n) return -1;
        asteroidSel = k;
        bodies[static_cast<size_t>(asteroidBody)].name = asteroidCat->label(static_cast<size_t>(k));
        bodies[static_cast<size_t>(asteroidBody)].natureText = asteroidCat->isComet(static_cast<size_t>(k)) ? "comète" : "astéroïde";
        refreshEphemeris();
        return asteroidBody;
    }

    // L'astéroïde le plus proche d'un point de l'écran (clic), à moins de maxPx pixels ; -1 si aucun.
    int nearestAsteroid(const Camera& cam, double px, double py, double w, double h, double maxPx) const {
        if (!asteroidCat) return -1;
        const double jd = 2451545.0 + years * 365.25 + kTdbMinusUtc / 86400.0;
        if (std::fabs(jd - asteroidCat->epochJd) >= 300.0 * 365.25) return -1;
        // Partagé entre les cœurs du processeur : 1,58 million d'orbites prenaient 140 ms sur un seul (mesuré).
        const unsigned nt = std::max(1u, std::min(32u, std::thread::hardware_concurrency()));
        std::vector<int> bests(nt, -1);
        std::vector<double> bestDs(nt, maxPx * maxPx);
        std::vector<std::thread> workers;
        const uint64_t n = asteroidCat->n;
        for (unsigned t = 0; t < nt; ++t)
            workers.emplace_back([&, t] {
                for (uint64_t k = n * t / nt; k < n * (t + 1) / nt; ++k) {
                    double au[3], x = 0, y = 0;
                    asteroidCat->position(k, jd, au);
                    if (!cam.project({au[0] * kAuInLy, au[1] * kAuInLy, au[2] * kAuInLy}, w, h, x, y)) continue;
                    const double d = (x - px) * (x - px) + (y - py) * (y - py);
                    if (d < bestDs[t]) {
                        bestDs[t] = d;
                        bests[t] = static_cast<int>(k);
                    }
                }
            });
        for (std::thread& th : workers) th.join();
        int best = -1;
        double bestD = maxPx * maxPx;
        for (unsigned t = 0; t < nt; ++t)
            if (bests[t] >= 0 && bestDs[t] < bestD) {
                bestD = bestDs[t];
                best = bests[t];
            }
        return best;
    }

    void follow(int i) {
        if (!visible(i)) return;
        flying = false;
        dist = arriveDist(i, dist);
        focus = i;
    }
};

// ---------------------------------------------------------------- textes en français
std::string frNum(double v, int digits = 3) {
    char buf[64];
    const double a = std::fabs(v);
    const int dec = a < 1e-12 ? 0 : std::clamp(digits - 1 - static_cast<int>(std::floor(std::log10(a))), 0, 6);
    std::snprintf(buf, sizeof(buf), "%.*f", dec, v);
    std::string s(buf);
    const size_t dot = s.find('.');
    const std::string intPart = s.substr(0, dot), frac = dot == std::string::npos ? "" : s.substr(dot + 1);
    std::string out;
    const size_t start = (!intPart.empty() && intPart[0] == '-') ? 1 : 0;
    for (size_t i = 0; i < intPart.size(); ++i) {
        out += intPart[i];
        const size_t left = intPart.size() - 1 - i;
        if (i >= start && left > 0 && left % 3 == 0) out += "\xC2\xA0";      // espace insécable entre les milliers
    }
    if (!frac.empty()) out += "," + frac;
    return out;
}
std::string frInt(double v) { return frNum(std::round(v), 1 + static_cast<int>(std::floor(std::log10(std::max(1.0, std::fabs(v)))))); }

// Une longueur donnée en années-lumière, écrite dans l'unité qui parle.
std::string frDistance(double ly) {
    const double km = ly * kLyInKm, au = ly / kAuInLy;
    if (ly >= 1.0e9) return frNum(ly / 1.0e9) + " milliards d'années-lumière";
    if (ly >= 1.0e6) return frNum(ly / 1.0e6) + " millions d'années-lumière";
    if (ly >= 0.1) return frNum(ly) + (ly >= 2 ? " années-lumière" : " année-lumière");
    if (au >= 0.1) return frNum(au) + " fois la distance Terre-Soleil";
    if (km >= 1.0e6) return frNum(km / 1.0e6) + " millions de km";
    return frInt(km) + " km";
}

// Date : jour, mois, année tant que le calendrier a un sens ; sinon l'année seule.
std::string frDate(double years, bool withTime = false) {
    static const char* months[] = {"janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"};
    if (std::fabs(years) > 6000.0) {      // hors de la plage où le calcul du calendrier est sûr
        const double y = 2000.0 + years;
        return y >= 0 ? "An " + frInt(y) : frInt(-y) + " ans avant notre ère";
    }
    // Jour julien -> calendrier grégorien (Fliegel et Van Flandern 1968).
    const double jd = 2451545.0 + years * 365.25;
    const long long J = static_cast<long long>(std::floor(jd + 0.5));
    long long l = J + 68569, n = 4 * l / 146097;
    l = l - (146097 * n + 3) / 4;
    const long long i = 4000 * (l + 1) / 1461001;
    l = l - 1461 * i / 4 + 31;
    const long long j = 80 * l / 2447, day = l - 2447 * j / 80;
    l = j / 11;
    const long long month = j + 2 - 12 * l, year = 100 * (n - 49) + i + l;
    char buf[96];
    if (withTime) {
        const double frac = jd + 0.5 - std::floor(jd + 0.5);
        const int minutes = static_cast<int>(frac * 1440.0);
        std::snprintf(buf, sizeof(buf), "%lld %s %lld, %02d h %02d (temps universel)", day, months[std::clamp<long long>(month, 1, 12) - 1], year, minutes / 60, minutes % 60);
    } else {
        std::snprintf(buf, sizeof(buf), "%lld %s %lld", day, months[std::clamp<long long>(month, 1, 12) - 1], year);
    }
    return buf;
}

}  // namespace
