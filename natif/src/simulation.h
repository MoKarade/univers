// Appli PC « Univers » : l'état du simulateur (temps, astres, objet suivi, caméra), sans rien qui dépende de l'affichage.
#pragma once
#include "asteroides_catalogue.h"
#include <climits>
#include <functional>
#include <thread>
#include "avancement.h"
#include "arrivee.h"
#include "rayon_etoile.h"
#include "doublons.h"
#include "centres_reference.h"
#include "film_v2.h"
#include "film_ancres.h"
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

namespace univers {

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
    bool emptySlot = false;     // place réservée (étoile désignée au clic) encore vide : ni dessinée ni nommée
    bool nebula = false;        // nébuleuse planétaire ou nuage moléculaire (nebuleuses_noms.tsv), rangée avec les galaxies
    bool gaiaStar = false;      // étoile de Gaia désignée au clic (star = -1) : place en ligne droite depuis la mesure
    Vec3 gaiaPos{0, 0, 0}, gaiaVel{0, 0, 0};      // place en J2000 (al) et vitesse (al par an)
    double gaiaAbsMag = 0;      // magnitude absolue G mesurée
    double drawnRadiusLy = 0;   // galaxie de forme mesurée : rayon de sa forme dessinée (D26 du SGA-2020 × distance), pour le clic
    bool merged = false;        // même galaxie, même nom, déjà dans une autre fiche (galaxies_cf4.tsv et formes) : ni dessinée ni nommée
    bool unplaced = false;      // galaxie de distance inconnue (z trop faible, aucune mesure) : ni placée ni nommée
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
    int dwarfModel = -1;        // galaxie naine dessinée d'après ses paramètres mesurés (galaxies_naines.h) ; -1 : non
    std::vector<std::string> planetLines;      // étoile : ses planètes connues, une ligne chacune (exoplanetes.h)
    double planetsReachLy = 0;  // étoile : plus grand demi-grand axe de ses planètes (années-lumière)
    int blackHole = -1;         // trou noir central de masse mesurée (trous_noirs.h) ; -1 : aucun relié
    double blackHoleRsLy = 0;   // son rayon de Schwarzschild (années-lumière)
    std::string blackHoleText;  // sa masse mesurée, la méthode et la source (panneau)
    double shapeRadiusLy = 0;   // rayon de demi-lumière mesuré, si la forme est dessinée d'après lui (galaxies_naines.h)
    std::string shapeNote;      // ce qui est dessiné de sa forme, et d'où viennent les valeurs (galaxies_naines.h)
    bool structure = false;     // repère de structures_noms.tsv (superamas, attracteur, vide) : pas une galaxie
    bool cluster = false;       // amas de galaxies (galaxies_noms.tsv) : pas une galaxie
    // Cycle de vie à la date montrée (cycle_appli.h) ; lifeOn faux : l'astre garde radiusKm et bv.
    bool lifeOn = false;
    double lifeRadiusKm = 0;    // 0 : rien à dessiner en sphère (pas née, éteinte)
    double lifeTeff = 0, lifeBv = 0.65;
    double lifeAbsMag = 99;     // magnitude absolue V à la date montrée (99 : rien de visible)
    bool lifeBlack = false;     // trou noir : disque noir de son ombre
    bool lifeMapped = true;     // c'est encore l'étoile elle-même (le Soleil garde sa carte de surface, teintée)
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
        prevIdx = LONG_MIN;      // les pas gardés ne valent plus (une étoile de plus)
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
    // Les deux derniers pas calculés sont gardés : autour d'une limite de pas (aujourd'hui en est à 27 ans), la vitesse du Soleil
    // prise par différence sur ±1 000 ans demandait les deux pas tour à tour, et toutes les orbites étaient refaites deux fois
    // par image (cadence, 20/11/2026 : ~3 ms).
    mutable long prevIdx = LONG_MIN;
    mutable std::vector<phys::Vec3> ppa, pva, ppb, pvb;
    void ensure(double years) const {
        const long n = static_cast<long>(std::floor(years / 1.0e6));
        if (built && n == idx) return;
        if (built && n == prevIdx) {
            std::swap(pa, ppa); std::swap(va, pva); std::swap(pb, ppb); std::swap(vb, pvb);
            std::swap(idx, prevIdx);
            return;
        }
        if (built) { ppa = pa; pva = va; ppb = pb; pvb = vb; prevIdx = idx; }
        if (!built || std::labs(n) + 1 < std::labs(n - at)) {      // premier appel, ou plus court en repartant d'aujourd'hui
            o = phys::galaxie::Orbites(g0, v0);
            at = 0;
            built = true;
        }
        // Étoiles indépendantes (potentiel fixe) : partagées entre les cœurs, mêmes résultats (cadence, 20/11/2026 : 16 ms par image
        // sur un seul cœur quand le temps défile à 100 Ma/s).
        const unsigned fils = std::clamp(std::thread::hardware_concurrency() / 2, 1u, 16u);
        o.avance(static_cast<double>(n) * 1.0e-3, fils);
        read(pa, va);
        o.avance(static_cast<double>(n + 1) * 1.0e-3, fils);
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
            if (bodies[i].kind == Kind::Star && stars && bodies[i].star >= 0)
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
    const FilmAnchors* anchors = nullptr;      // ancres des voisines dans le film (film_ancres.h) ; nul sans fichier
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
    double photoWeight = 0;      // (suite) photoNebula : la part de ce poids qui vient d'une nébuleuse autour d'une étoile
    double photoNebula = 0;      // poids des objets qui règlent la pose « photo » (0 à 1) : fond la courbe de l'écran (ecran.frag)
    double metreSat = 0, metreVis = 0, metreMoy = 0;      // dernière mesure de l'image (pose_auto.h), pour les balayages de contrôle
    double autoPose = 1;      // pose automatique contre la saturation (pose_auto.h) : 1 = aucune baisse
    double galaxyPose = 1;    // pose propre aux galaxies aux grandes échelles (galaxies_pose.h) : 1 = la même que les étoiles
    // Gaz ionisé de la Voie lactée (régions HII de voie_lactee.bin) montré par-dessus les étoiles (Marc, 20/11/2026 soir :
    // « l'espace paraît trop vide, il manque du gaz, des nébuleuses, de la poussière ») ; case du menu.
    bool showGas = true;
    bool showNebulae = true;      // nébuleuses planétaires et nuages moléculaires (nebuleuses.h) ; case du menu
    double gasShare = 0;      // part montrée à cette image (0 à 1)
    uint32_t galaxyShapeCount = 0, galaxyShapesShown = 0;      // galaxies de forme mesurée (galaxies_formes.h), montrées en particules
    uint64_t neighbourStarCount = 0;   // étoiles des galaxies voisines (voisines_etoiles.bin), montrées à toute date
    // Grandes structures (Laniakea et son flot, vides cosmiques) et nuage d'Oort (modèle) : structures.h. Repères dessinés,
    // pas de la lumière ; montrés par défaut (Marc, 19/11/2026), cachables dans le Menu.
    struct StructuresState {
        bool loaded = false;           // structures.bin lu
        bool showLarge = true, showOort = true;
        // Formes approchées en sphères (vides SDSS et BOSS, superamas SDSS, superstructures « une bulle par amas » ou « sphère
        // de la taille publiée ») : cachées par défaut (Marc, 20/11/2026 : « je vois des boules, c'est bizarre ») ; Laniakea,
        // les vides du voisinage (formes publiées), l'univers observable et le fond diffus restent.
        bool showSpheres = false;
        double largeShare = 0, oortShare = 0;      // parts montrées à la dernière image
        uint32_t oortComets = 0, flowLines = 0;
        uint32_t triangles[9] = {};    // par genre : 1 Laniakea, 2 vides du voisinage, 3 vides SDSS, 4 vides BOSS, 5 superamas SDSS, 6 superstructures nommées, 7 univers observable, 8 fond diffus
    } structures;
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
    bool sunAlways = false;      // le Soleil reste montré au-delà de l'ère des étoiles mesurées (cycle_appli.h)
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
                body.radiusKm = rayon_etoile::rayonKm(stars->mag()[body.star], body.bv);      // calculé (audit E3)
                bodies.push_back(body);
            }
        }
        // Place de l'étoile désignée au clic (Marc, 20/11/2026 : « des astres que je ne peux pas sélectionner ») : n'importe
        // quelle étoile dessinée du catalogue (6,15 millions) peut être choisie ; elle prend cette place (nom, fiche, suivi).
        {
            Body s;
            s.name = "Étoile";
            s.nature = "étoile";
            s.star = 0;
            s.priority = 9;
            s.emptySlot = true;
            bodies.push_back(s);
            pickedStarBody = static_cast<int>(bodies.size()) - 1;
            // Même chose pour une étoile de Gaia (192 millions, gaia.bin et gaia_b.bin) : sa place à elle.
            Body gs = s;
            gs.name = "Étoile Gaia";
            gs.star = -1;
            gs.gaiaStar = true;
            bodies.push_back(gs);
            gaiaStarBody = static_cast<int>(bodies.size()) - 1;
        }
        // Étoiles qui ont des planètes connues (pipeline/natif/exoplanetes_app.py, NASA Exoplanet Archive) : cherchables par
        // le nom de l'hôte ; une étoile déjà nommée garde son nom.
        {
            const std::string hostsPath = namesPath.substr(0, namesPath.find_last_of("/\\") + 1) + "etoiles_planetes_noms.tsv";
            starDoubles = doublons::hotes(stars->x(), stars->y(), stars->z(), stars->mag(), stars->n, hostsPath);      // doublons.h
            std::ifstream hf(hostsPath);
            for (std::string hl; std::getline(hf, hl);) {
                std::vector<std::string> c;
                size_t from = 0;
                for (size_t tab; (tab = hl.find('\t', from)) != std::string::npos; from = tab + 1) c.push_back(hl.substr(from, tab - from));
                c.push_back(hl.substr(from));
                if (c.size() < 4) continue;
                int64_t idx = std::strtoll(c[0].c_str(), nullptr, 10);
                if (idx < 0 || static_cast<uint64_t>(idx) >= stars->n) continue;
                if (const auto d = starDoubles.find(idx); d != starDoubles.end()) idx = d->second;      // le double : l'étoile du catalogue principal
                bool known = false;
                for (const Body& b : bodies) known = known || (b.kind == Kind::Star && !b.emptySlot && b.star == idx);
                if (known) continue;
                Body body;
                body.star = idx;
                body.name = c[1];
                body.nature = "étoile";
                body.natureText = "étoile avec " + c[3] + (c[3] == "1" ? " planète connue" : " planètes connues") + " (NASA Exoplanet Archive)";
                body.priority = 9;
                body.bv = stars->bv()[idx];
                body.radiusKm = rayon_etoile::rayonKm(stars->mag()[idx], body.bv);      // calculé (audit E3)
                bodies.push_back(body);
            }
        }
        // Étoiles massives nommées pour leur cycle de vie (etoiles_cycle.tsv, cycle_appli.h) : une étoile déjà nommée garde son nom.
        {
            std::ifstream cf(namesPath.substr(0, namesPath.find_last_of("/\\") + 1) + "etoiles_cycle.tsv");
            for (std::string cl; std::getline(cf, cl);) {
                if (cl.empty() || cl[0] == '#') continue;
                const size_t t1 = cl.find('	'), t2 = cl.find('	', t1 + 1);
                if (t1 == std::string::npos || t2 == std::string::npos) continue;
                const int64_t idx = std::strtoll(cl.substr(0, t1).c_str(), nullptr, 10);
                if (idx < 0 || static_cast<uint64_t>(idx) >= stars->n) continue;
                bool known = false;
                for (const Body& b : bodies) known = known || (b.kind == Kind::Star && b.star == idx);
                if (known) continue;
                Body body;
                body.star = idx;
                body.name = cl.substr(t1 + 1, t2 - t1 - 1);
                body.nature = "étoile";
                body.natureText = "étoile massive";
                body.bv = stars->bv()[idx];
                body.radiusKm = rayon_etoile::rayonKm(stars->mag()[idx], body.bv);      // calculé (audit E3)
                bodies.push_back(body);
            }
        }
        // Galaxies nommées (galaxies_noms.tsv : nom, x, y, z en années-lumière, genre, priorité).
        // Puis, s'il est à côté, galaxies_cf4.tsv : 55 637 galaxies à distance mesurée (Cosmicflows-4, noms OpenNGC),
        // écrit par pipeline/natif/galaxies_cf4.py ; priorité 9 : nom montré seulement de près ou au survol.
        const std::string cf4Path = galaxiesPath.substr(0, galaxiesPath.find_last_of("/\\") + 1) + "galaxies_cf4.tsv";
        // Puis galaxies_formes_noms.tsv : Messier, NGC et IC de forme mesurée (pipeline/natif/galaxies_formes.py), cherchables.
        const std::string formesPath = galaxiesPath.substr(0, galaxiesPath.find_last_of("/\\") + 1) + "galaxies_formes_noms.tsv";
        // Puis structures_noms.tsv : Laniakea, Grand Attracteur, bassins voisins, Vide local et vides du voisinage
        // (pipeline/natif/structures.py).
        const std::string structuresPath = galaxiesPath.substr(0, galaxiesPath.find_last_of("/\\") + 1) + "structures_noms.tsv";
        // Puis superstructures_noms.tsv : murs et superamas nommés des articles, bord de l'univers observable
        // (pipeline/natif/superstructures_bin.py).
        const std::string superPath = galaxiesPath.substr(0, galaxiesPath.find_last_of("/\\") + 1) + "superstructures_noms.tsv";
        for (const std::string& path : {galaxiesPath, cf4Path, formesPath, structuresPath, superPath})
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
            body.structure = path == structuresPath || path == superPath;
            // galaxies_noms.tsv range aussi des amas, des superamas et le Grand Attracteur sous « galaxie » : on les nomme
            // pour ce qu'ils sont (fiche, distance d'arrivée), sans rien changer à leur place.
            if (!body.structure && body.natureText == "galaxie") {
                if (body.name.rfind("Superamas ", 0) == 0) { body.natureText = "superamas de galaxies"; body.structure = true; }
                else if (body.name == "Grand Attracteur") { body.natureText = "concentration de masse au cœur de Laniakea"; body.structure = true; }
                else if (body.name.rfind("Amas ", 0) == 0) { body.natureText = "amas de galaxies"; body.cluster = true; }
            }
            bodies.push_back(body);
        }
        // Galaxies de forme placées d'après z : distance remplacée par une distance MESURÉE (Cosmicflows-4) dans deux cas, comme
        // leur forme (galaxies_formes.h, fixNearbyDistances) :
        // - la même galaxie, sous le même nom, est dans galaxies_cf4.tsv (moins de 0,2°), à tout z : M77 (NGC 1068), M106… ;
        // - proche (z < 0,005), une galaxie de Cosmicflows-4 est dans la même direction (moins de 0,1°) : sous cz ≈ 1 500 km/s,
        //   la vitesse propre domine z. Avant : NGC 2976 à 68 000 al, IC 2574 et IC 3658 à 2 Mal (essai_completude).
        // Le double de galaxies_cf4.tsv est alors fondu dans la fiche de la forme : un seul nom, une seule fiche, un seul clic.
        {
            struct Cf4 { Vec3 u; double d; size_t i; };
            std::vector<Cf4> cf4;
            std::unordered_map<std::string, std::vector<size_t>> byName;      // galaxies nommées hors galaxies_cf4.tsv
            // origine galaxies_cf4.tsv, notée une fois avant toute retouche des fiches
            std::vector<char> fromCf4(bodies.size(), 0);
            for (size_t i = 0; i < bodies.size(); ++i) {
                const Body& b = bodies[i];
                if (b.kind != Kind::Galaxy) continue;
                fromCf4[i] = b.priority >= 9 && b.natureText.find("Cosmicflows-4") != std::string::npos && b.natureText.find("SGA-2020") == std::string::npos;
                if (b.natureText.find("Cosmicflows-4") != std::string::npos) {
                    const double n = std::sqrt(dot(b.fixedPos, b.fixedPos));
                    if (n > 0) cf4.push_back({{b.fixedPos.x / n, b.fixedPos.y / n, b.fixedPos.z / n}, n, i});
                }
                if (!fromCf4[i]) byName[b.name].push_back(i);
            }
            auto cosTo = [](const Body& a, const Body& b) {
                const double na = std::sqrt(dot(a.fixedPos, a.fixedPos)), nb = std::sqrt(dot(b.fixedPos, b.fixedPos));
                return na > 0 && nb > 0 ? dot(a.fixedPos, b.fixedPos) / (na * nb) : -1.0;
            };
            for (Body& b : bodies) {
                const size_t k = b.natureText.find("distance d'après z = ");
                if (b.kind != Kind::Galaxy || k == std::string::npos) continue;
                const double z = std::atof(b.natureText.c_str() + k + 21);
                const double n = std::sqrt(dot(b.fixedPos, b.fixedPos));
                if (n <= 0) continue;
                double best = 0.99999847691, d = 0;      // cos(0,1°)
                size_t src = 0;
                for (const Cf4& c4 : cf4) {
                    const double c = (c4.u.x * b.fixedPos.x + c4.u.y * b.fixedPos.y + c4.u.z * b.fixedPos.z) / n;
                    const bool same = c > 0.99999390766 && bodies[c4.i].name == b.name;      // moins de 0,2°, même nom
                    if (same) { best = 2.0; d = c4.d; src = c4.i; break; }
                    if (z < 0.005 && c > best) { best = c; d = c4.d; src = c4.i; }
                }
                if (d <= 0) {
                    // ni distance mesurée dans la même direction, ni z exploitable (sous 0,001) : distance inconnue, la galaxie
                    // n'est pas placée (même règle que sa forme, galaxies_formes.h)
                    if (z < 0.001) b.unplaced = true;
                    continue;
                }
                b.fixedPos = {b.fixedPos.x / n * d, b.fixedPos.y / n * d, b.fixedPos.z / n * d};
                // La fiche reprend la mesure elle-même (valeur, erreur, méthode, source).
                Body& m = bodies[src];
                const size_t km = m.natureText.find("distance mesurée");
                const std::string mesure = km == std::string::npos ? "distance mesurée (Cosmicflows-4, même direction)" : m.natureText.substr(km);
                const size_t zEnd = b.natureText.find(" ;", k);
                const std::string zText = b.natureText.substr(k + std::string("distance d'après ").size(), zEnd == std::string::npos ? std::string::npos : zEnd - k - std::string("distance d'après ").size());
                b.natureText.replace(k, zEnd == std::string::npos ? std::string::npos : zEnd - k, mesure + " ; décalage vers le rouge " + zText + " (non utilisé pour la distance)");
            }
            // Doubles : une galaxie de galaxies_cf4.tsv qui porte le nom d'une galaxie déjà nommée ailleurs (Groupe local,
            // formes), à moins de 0,2°, est la même : elle est fondue (inventaire du 20/11 : 25 noms en double, cliquables deux
            // fois, deux fois dans la recherche).
            for (size_t i = 0; i < bodies.size(); ++i) {
                Body& m = bodies[i];
                if (!fromCf4[i]) continue;
                const auto it = byName.find(m.name);
                if (it == byName.end()) continue;
                for (size_t j : it->second)
                    if (cosTo(m, bodies[j]) > 0.99999390766) { m.merged = true; break; }
            }
        }
        // Nébuleuses (nebuleuses_noms.tsv et nebuleuses.bin, pipeline/natif/nebuleuses.py, même ordre) : 223 nébuleuses
        // planétaires et 94 nuages moléculaires à distance publiée. Dessinées depuis le 20/11 mais sans fiche ni clic
        // (inventaire du 20/11/2026) : elles deviennent des astres nommés, à leur place d'aujourd'hui, avec leur rayon dessiné.
        {
            const std::string dir = galaxiesPath.substr(0, galaxiesPath.find_last_of("/\\") + 1);
            std::vector<float> radii;
            {
                std::ifstream nb(dir + "nebuleuses.bin", std::ios::binary);
                char magic[8] = {};
                uint32_t hd[2] = {};
                nb.read(magic, 8);
                nb.read(reinterpret_cast<char*>(hd), sizeof(hd));
                if (nb && std::memcmp(magic, "UNIVNEB1", 8) == 0 && hd[0] > 0 && hd[0] < 1000000) {
                    std::vector<float> raw(static_cast<size_t>(hd[0]) * 8);
                    if (nb.read(reinterpret_cast<char*>(raw.data()), static_cast<std::streamsize>(raw.size() * 4)))
                        for (uint32_t k = 0; k < hd[0]; ++k) radii.push_back(raw[k * 8 + 3]);
                }
            }
            size_t k = 0;
            for (std::ifstream nf(dir + "nebuleuses_noms.tsv"); std::getline(nf, line); ++k) {
                std::vector<std::string> cols;
                size_t from = 0;
                for (size_t tab; (tab = line.find('\t', from)) != std::string::npos; from = tab + 1) cols.push_back(line.substr(from, tab - from));
                cols.push_back(line.substr(from));
                if (cols.size() < 6) continue;
                Body body;
                body.name = cols[0];
                body.kind = Kind::Galaxy;      // place fixe d'aujourd'hui, comme les galaxies ; `nebula` dit ce qu'elle est
                body.nebula = true;
                body.fixedPos = {std::atof(cols[1].c_str()), std::atof(cols[2].c_str()), std::atof(cols[3].c_str())};
                body.natureText = cols[4];
                body.priority = std::atoi(cols[5].c_str());
                if (k < radii.size()) body.drawnRadiusLy = radii[k];
                body.shapeNote = "Dessin : une tache ronde de la taille mesurée, tournée vers la caméra (" +
                                 std::string(body.natureText.rfind("nuage", 0) == 0 ? "poussière qui assombrit ce qui est derrière ; opacité supposée)" : "repère lumineux ; son éclat n'est pas dans les données retenues)");
                bodies.push_back(body);
            }
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

    // Centre d'une voisine dans le film, en kpc relatifs à la Voie lactée. follow = true : le point que suivent l'étiquette
    // et la caméra (ancre, film_ancres.h, si le fichier la couvre) ; false : le centre écrit, par la courbe de ses étoiles
    // (base où gaia.vert pose leurs positions relatives). Revue F4 : le centre du film à t = 0 n'est pas exactement le
    // centre mesuré ; l'écart à la date de départ commune est retiré, puis s'efface sur 100 Ma (même décalage pour l'ancre
    // et pour la base des étoiles : la galaxie ne se décolle pas de son étiquette).
    bool filmCentre(int ci, double tGa, phys::Vec3& g, bool follow) const {
        if (!film || !centres || !centres->ready) return false;
        auto raw = [&](double t, phys::Vec3& o) {
            if (follow && anchors && anchors->at(*film, ci, t, o)) return true;
            return follow ? film->centre(ci, t, o) : film->centreEtoiles(ci, t, o);
        };
        if (!raw(tGa, g)) return false;
        const double t0 = std::clamp(0.0, film->debutGa(), film->date(film->images() - 2));
        phys::Vec3 f0, r0;
        if (raw(t0, f0) && centres->centre(ci, t0, r0)) {
            const double w = std::clamp(1.0 - std::fabs(tGa - t0) / 0.1, 0.0, 1.0);
            g = {g.x - w * (f0.x - r0.x), g.y - w * (f0.y - r0.y), g.z - w * (f0.z - r0.z)};
        }
        return true;
    }
    // Base des étoiles d'une voisine quand le film les mène (repère du simulateur, années-lumière) : centre écrit par la
    // courbe des étoiles, pour que centre + position relative redonne exactement la position calculée de chaque étoile.
    bool filmStarBase(const std::string& name, Vec3& out) const {
        const int ci = CentresReference::indexOf(name);
        phys::Vec3 g;
        const double tGa = replayGa();
        if (ci < 0 || !filmCovers(tGa) || ci >= film->galaxies() || !filmCentre(ci, tGa, g, false)) return false;
        const Vec3 w = fromGalactocentric(g), shift = sunShift();
        out = {w.x + shift.x, w.y + shift.y, w.z + shift.z};
        return true;
    }
    // Part des étoiles d'une voisine encore groupées autour de son cœur à la date montrée (film_ancres.h) ; -1 : inconnue.
    double groupedShare(const std::string& name) const {
        const int ci = CentresReference::indexOf(name);
        phys::Vec3 o;
        double f = -1;
        if (ci < 0 || !anchors || !film || !filmCovers(replayGa()) || !anchors->at(*film, ci, replayGa(), o, &f)) return -1;
        return f;
    }

    // Facteur d'échelle de l'univers avec lequel les galaxies sont dessinées (posé par la fenêtre avec la table des distances,
    // galaxies.h setCosmology) ; 0 : pas de dessin, calculé ici à la date montrée.
    double galaxyScale = 0;
    // Galaxie placée par sa mesure d'aujourd'hui puis l'expansion seule (au-delà de 10 Mal, hors calcul de la rencontre).
    bool expandsOnly(int i) const {
        const Body& b = bodies[static_cast<size_t>(i)];
        const int ref = static_cast<size_t>(i) < replayRef.size() ? replayRef[static_cast<size_t>(i)] : -1;
        return b.kind == Kind::Galaxy && ref == -1 && CentresReference::indexOf(b.name) < 0 && std::sqrt(dot(b.fixedPos, b.fixedPos)) > 1.0e7;
    }
    // Rayon de ce qui est dessiné pour l'astre i (années-lumière) : disque d'une planète ou d'une étoile, forme d'une galaxie
    // (agrandie comme son dessin par le facteur d'échelle), nuage d'une naine. Sert au clic et à « vu de près ».
    double drawnRadiusLy(int i) const {
        const Body& b = bodies[static_cast<size_t>(i)];
        double r = b.radiusKm / kLyInKm;
        if (b.kind == Kind::Galaxy) r = std::max({r, b.drawnRadiusLy * (galaxyScale > 0 && !b.nebula ? galaxyScale : 1.0), b.shapeRadiusLy});
        return r;
    }
    void refreshGalaxies() {
        galPos.assign(bodies.size(), {0, 0, 0});
        galValid.assign(bodies.size(), 0);
        const double tGa = replayGa();
        const bool deep = deepTime();
        const Vec3 shift = sunShift();
        // audit C1 : au-delà de ±3 Ma, les galaxies sans mouvement calculé (relevés, Cosmicflows-4, amas, structures) gardent une
        // place : celle d'aujourd'hui agrandie par l'expansion (même facteur que leur dessin, galaxies.h), au-delà de 10 Mal
        // seulement ; plus près (Groupe local), leur mouvement n'est pas calculé et elles restent cachées comme avant.
        // Avant, toutes devenaient impossibles à cliquer et à nommer.
        // M77 « se balade » (Marc, 20/11/2026, deux fois) : le dessin des galaxies (formes, points des relevés) suit le facteur
        // d'échelle posé par la fenêtre (galaxyScale, mis à jour tous les 100 000 ans), aussi entre -3 et +3 Ma, alors que le
        // nom restait à sa place d'aujourd'hui puis sautait à 3 Ma. Le nom et la caméra prennent maintenant le même facteur, à
        // toute date : une seule place, celle de l'expansion calculée (Hubble), partie de la distance mesurée d'aujourd'hui.
        const double scale = galaxyScale > 0 ? galaxyScale : deep ? cosmo::scaleFactorAt(cosmology, tGa) : 1.0;
        for (size_t i = 0; i < bodies.size(); ++i) {
            const Body& b = bodies[i];
            if (b.kind != Kind::Galaxy) continue;
            if (b.nebula) {      // nébuleuse : dessinée à sa place d'aujourd'hui (nebuleuses.h), autour d'aujourd'hui seulement
                galPos[i] = b.fixedPos;
                galValid[i] = !deep;
                continue;
            }
            // Centres de référence (centres_reference.h) : Andromède, Triangle, Nuages de Magellan, en bloc le long de leur
            // centre, à toute date calculée, aujourd'hui compris (mêmes valeurs que la table unique et que leurs étoiles).
            const int ci = centres && centres->ready ? CentresReference::indexOf(b.name) : -1;
            if (ci >= 0) {
                phys::Vec3 g;
                bool ok = false;
                if (filmCovers(tGa) && ci < film->galaxies() && filmCentre(ci, tGa, g, true)) {
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
            if (ref == -1 && std::sqrt(dot(b.fixedPos, b.fixedPos)) > 1.0e7) {
                // au-delà de 10 Mal, sans mouvement calculé à part : place mesurée × facteur d'échelle, sans le déplacement du
                // Soleil dans la Galaxie, exactement comme leur dessin (galaxies.vert, galaxies_formes.h), à toute date
                galPos[i] = {b.fixedPos.x * scale, b.fixedPos.y * scale, b.fixedPos.z * scale};
                galValid[i] = 1;
                continue;
            }
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
        if (b.emptySlot || b.unplaced || b.merged) return false;
        if (b.kind == Kind::Planet || b.kind == Kind::Probe || b.kind == Kind::Asteroid) return planetValid[static_cast<size_t>(i)] != 0;
        if (b.kind == Kind::Galaxy) return static_cast<size_t>(i) < galValid.size() && galValid[static_cast<size_t>(i)];
        // suivi sur son orbite autour de la Galaxie, comme les étoiles ; avec le cycle de vie, montré à toute date (sunAlways)
        if (b.kind == Kind::Sun) return starShare() > 0 || sunAlways;
        // étoile de Gaia désignée : en ligne droite seulement (pas d'orbite calculée pour elle), à 100 000 ans au plus
        if (b.gaiaStar) return starShare() > 0 && std::fabs(years - kStartYears) <= kGaiaPickYears;
        return starShare() > 0;      // étoile : suivie sur son orbite calculée, tant que cette orbite a un sens
    }

    // Position à la date courante (années-lumière, repère écliptique centré sur le Soleil).
    Vec3 position(int i) const {
        const Body& b = bodies[static_cast<size_t>(i)];
        if (b.kind == Kind::Sun) return {0, 0, 0};
        if (b.kind == Kind::Planet || b.kind == Kind::Probe || b.kind == Kind::Asteroid) return planetPos[static_cast<size_t>(i)];
        if (b.kind == Kind::Galaxy) return static_cast<size_t>(i) < galPos.size() && galValid[static_cast<size_t>(i)] ? galPos[static_cast<size_t>(i)] : b.fixedPos;
        if (b.star < 0) return {b.gaiaPos.x + b.gaiaVel.x * years, b.gaiaPos.y + b.gaiaVel.y * years, b.gaiaPos.z + b.gaiaVel.z * years};
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
        if (b.star < 0) return std::sqrt(dot(b.gaiaVel, b.gaiaVel)) / kKmsToLyPerYear;
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
        const double absMag = b.kind == Kind::Sun ? kSunAbsMag : b.star < 0 ? b.gaiaAbsMag : stars->mag()[b.star];
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
        // Étoile (rayon non lu ici) : jamais plus près que 50 UA en arrivant, même en venant de plus près (audit B2 :
        // une recherche « Sirius » depuis la Terre arrivait à 28 000 km du centre de l'étoile, dans l'étoile).
        if (b.kind == Kind::Star) d = std::max(d, 50.0 * kAuInLy);
        if (b.kind == Kind::Galaxy) d = std::max(d, 3.0e5);                  // une galaxie se regarde de loin
        if (b.kind == Kind::Galaxy && b.structure) d = std::max(d, 1.5 * arrivee::structureSizeLy(b.natureText));
        if (b.kind == Kind::Galaxy && b.cluster) d = std::max(d, 2.0e7);      // un amas (quelques Mpc) : vu entier avec ses galaxies      // audit B3 : la structure entière dans le champ
        if (b.kind == Kind::Galaxy && b.structure && (b.name == "Univers observable" || b.name == "Fond diffus cosmologique")) d = 1.1e11;      // la sphère entière dans le champ
        if (b.kind == Kind::Galaxy && b.shapeRadiusLy > 0) d = std::clamp(12.0 * b.shapeRadiusLy, 1.0e3, 3.0e5);
        if (b.nebula) d = std::clamp(12.0 * b.drawnRadiusLy, 3.0, 3.0e3);      // nébuleuse : vue entière, dans son voisinage d'étoiles      // naine dessinée : on la voit entière
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
        lostName.clear();
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
        // Jusqu'à 3 000 années-lumière l'éclat est multiplié pour compenser la distance (au plus 100 fois), puis il reste à
        // 100. À partir de là, chaque pixel additionne de plus en plus d'étoiles : l'image passe d'elle-même des étoiles une
        // à une à leur lumière regroupée, à éclat par pixel constant, et l'ensemble rapetisse en s'éloignant, comme une vraie
        // galaxie. Demande de Marc (12 novembre 2026) : « quand on augmente les distances on généralise au fur et à mesure ».
        // Ce qu'on voit de loin est donc la somme des étoiles MESURÉES (rien d'ajouté) : un nuage autour du Soleil, parce que
        // Gaia ne mesure bien les distances que dans notre région de la Galaxie.
        // Audit du zoom (20/11/2026, « les vues changent quand je zoome, l'éclairage aussi ») : le renfort montait en (d/30)²,
        // ×100 sur une seule décade (30 à 300 al), soit ×13 d'éclat moyen mesuré entre deux crans de molette. Il monte
        // maintenant en d/30, sur deux décades (×100 atteint à 3 000 al) : la même lumière au bout, deux fois moins vite.
        return std::clamp(dist / 30.0, 1.0, 100.0);
    }
    // Astéroïdes : un point chacun de près ; au-delà de 2,5 fois la distance Terre-Soleil, l'éclat de chaque point baisse
    // comme l'inverse du carré de la distance, si bien que la ceinture garde le même éclat par pixel pendant que ses
    // points se fondent en un anneau, puis en une tache (même principe que pour les étoiles : on regroupe en s'éloignant).
    // Montrés seulement à moins de 300 ans de la date de leurs orbites : au-delà, l'orbite simple ne vaut plus.
    // Audit A6 et C4 (20/11/2026) : l'éclat de chaque astéroïde est maintenant sa vraie lumière (asteroides.vert,
    // magnitude H mesurée, distance au Soleil et à la caméra), sous la même pose que les étoiles ; avant, chacun des
    // 1,58 million de points avait le même éclat et la ceinture faisait une neige autour de la Terre. Reste ici le
    // fondu en temps : plein jusqu'à 250 ans de la date des orbites, nul à 350 ans (avant : coupure nette à 300 ans).
    double asteroidGain(double epochJd) const {
        const double epochYears = (epochJd - 2451545.0) / 365.25;
        const double gap = std::fabs(years - epochYears);
        return std::clamp((350.0 - gap) / 100.0, 0.0, 1.0);
    }
    // Éclat donné à chaque galaxie des relevés : nul tant qu'on est dans la Voie lactée, plein au-delà de 3 millions d'années-lumière.
    // Vue d'assez loin pour que les galaxies lointaines se mêlent aux étoiles : la ligne de provenance dit ce que sont ces points.
    bool galaxyNote() const { return dist > 3.0e4; }

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
            lostName = bodies[static_cast<size_t>(focus)].name;
            focus = 0;
            if (!visible(0))
                for (size_t i = 0; i < bodies.size(); ++i)
                    if (i < replayRef.size() && replayRef[i] == -2) {
                        focus = static_cast<int>(i);
                        dist = std::max(dist, 3.0e5);
                    }
            flying = false;
            // audit B4 : la distance est reprise pour le nouvel astre (on suivait une lune à 10⁻⁹ al : sans cela, la
            // caméra se retrouvait dans le Soleil), et on peut revenir en arrière.
            dist = std::clamp(dist, minDist(focus), kMaxDist);
            if (focus == 0) dist = std::max(dist, 45.0 * kAuInLy);
            lostFallback = focus;
        }
    }
    std::string lostName;      // astre suivi qui n'a plus de position à cette date (dit en bas de l'écran tant qu'on reste sur le repli)
    int lostFallback = -1;     // astre de repli choisi à ce moment
    double minDist(int i) const {      // on s'arrête un peu au-dessus de la surface (1,25 rayon du centre)
        if (bodies[static_cast<size_t>(i)].kind == Kind::Galaxy && bodies[static_cast<size_t>(i)].blackHole >= 0)
            return 3.0 * bodies[static_cast<size_t>(i)].blackHoleRsLy;      // on peut descendre jusqu'à son trou noir central
        if (bodies[static_cast<size_t>(i)].kind == Kind::Galaxy) return bodies[static_cast<size_t>(i)].shapeRadiusLy > 0 ? std::min(1.0e3, bodies[static_cast<size_t>(i)].shapeRadiusLy) : 1.0e3;
        if (bodies[static_cast<size_t>(i)].kind == Kind::Probe || bodies[static_cast<size_t>(i)].kind == Kind::Asteroid) return 1.0e-10;      // environ 1 000 km
        return std::max(1.25 * bodies[static_cast<size_t>(i)].radiusKm / kLyInKm, 2.0e-10);
    }
    static constexpr double kMaxDist = 1.2e11;      // de quoi voir tout l'univers observable (rayon comobile 46 milliards d'al)
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
    // ---------------------------------------------------------------- étoile désignée au clic
    int pickedStarBody = -1;
    // Étoiles en double (partie Gaia -> catalogue principal), repérées par les hôtes d'exoplanètes (doublons.h) : le point
    // Gaia n'est pas dessiné (commun.h), et ses planètes sont rangées sous l'étoile du catalogue principal (exoplanetes.h).
    std::unordered_map<int64_t, int64_t> starDoubles;
    // L'étoile du catalogue la plus brillante dessinée à moins de maxPx pixels d'un point de l'écran ; -1 si aucune.
    // mLim : magnitude apparente au-delà de laquelle l'étoile n'est pas visible à l'écran (elle n'est pas proposée).
    // Seulement à moins de 100 000 ans d'aujourd'hui (ligne droite, même place que le dessin) ; partagé entre les cœurs.
    int64_t nearestCatalogStar(const Camera& cam, double px, double py, double w, double h, double maxPx, double mLim) const {
        if (!stars || std::fabs(years - kStartYears) > 1.0e5) return -1;
        const double kt = years * kKmsToLyPerYear;
        const unsigned nt = std::max(1u, std::min(32u, std::thread::hardware_concurrency()));
        std::vector<int64_t> bests(nt, -1);
        std::vector<double> bestM(nt, mLim);
        std::vector<std::thread> workers;
        const uint64_t n = stars->n;
        for (unsigned t = 0; t < nt; ++t)
            workers.emplace_back([&, t] {
                for (uint64_t k = n * t / nt; k < n * (t + 1) / nt; ++k) {
                    const Vec3 p{stars->x()[k] + stars->vel(0)[k] * kt, stars->y()[k] + stars->vel(1)[k] * kt, stars->z()[k] + stars->vel(2)[k] * kt};
                    double x = 0, y = 0;
                    if (!cam.project(p, w, h, x, y) || (x - px) * (x - px) + (y - py) * (y - py) > maxPx * maxPx) continue;
                    const Vec3 d = p - cam.pos;
                    const double m = stars->mag()[k] + 5.0 * std::log10(std::max(std::sqrt(dot(d, d)), 1e-12) / 3.2615638) - 5.0;
                    if (m < bestM[t]) {
                        bestM[t] = m;
                        bests[t] = static_cast<int64_t>(k);
                    }
                }
            });
        for (auto& th : workers) th.join();
        int64_t best = -1;
        double m = mLim;
        for (unsigned t = 0; t < nt; ++t)
            if (bests[t] >= 0 && bestM[t] < m) {
                m = bestM[t];
                best = bests[t];
            }
        return best;
    }
    // L'étoile k du catalogue prend la place de l'étoile désignée ; rend son rang dans bodies (ou l'astre nommé qui est déjà
    // cette étoile).
    int selectCatalogStar(int64_t k) {
        if (pickedStarBody < 0 || !stars || k < 0 || static_cast<uint64_t>(k) >= stars->n) return -1;
        for (int i = 0; i < static_cast<int>(bodies.size()); ++i)
            if (i != pickedStarBody && bodies[static_cast<size_t>(i)].kind == Kind::Star && bodies[static_cast<size_t>(i)].star == k) return i;
        Body& b = bodies[static_cast<size_t>(pickedStarBody)];
        b.star = k;
        b.emptySlot = false;
        b.bv = stars->bv()[k];
        b.radiusKm = rayon_etoile::rayonKm(stars->mag()[k], b.bv);
        // trois parties du fichier d'étoiles (etoiles.json) : catalogue principal, 200 000 étoiles Gaia, puis les autres
        const char* from = k < 58967 ? "catalogue principal (Hipparcos et Gaia)" : k < 258967 ? "Gaia DR3, 200 000 étoiles les plus brillantes"
                                                                                  : "Gaia DR3";
        b.name = "Étoile sans nom n° " + std::to_string(k);
        b.natureText = std::string("étoile sans nom propre, ") + from;
        exactOf.clear();      // son orbite exacte est recalculée (ensureExact)
        return pickedStarBody;
    }

    // ---------------------------------------------------------------- étoile de Gaia désignée au clic
    static constexpr double kGaiaPickYears = 1.0e5;      // comme les étoiles du catalogue (nearestCatalogStar)
    int gaiaStarBody = -1;
    // Recherche dans gaia.bin et gaia_b.bin (posée par la fenêtre) : setB dit si l'étoile vient du jeu B.
    std::function<bool(const Camera&, double, double, double, double, double, double, GaiaHit&, bool&)> gaiaPick;
    // L'étoile de Gaia `hit` prend la place de l'étoile Gaia désignée ; rend son rang dans bodies.
    int selectGaiaStar(const GaiaHit& hit, bool setB) {
        if (gaiaStarBody < 0) return -1;
        Body& b = bodies[static_cast<size_t>(gaiaStarBody)];
        b.emptySlot = false;
        b.gaiaPos = hit.posJ2000;
        b.gaiaVel = hit.velLy;
        b.gaiaAbsMag = hit.absMagG;
        // indice B-V tel que la formule de la fiche (Ballesteros 2012) redonne la température du pas de couleur BP-RP mesuré
        b.bv = 0.65;
        if (hit.teffK > 0) {
            double lo = -0.4, hi = 3.0;
            for (int k = 0; k < 60; ++k) {
                const double mid = 0.5 * (lo + hi), t = 4600.0 * (1.0 / (0.92 * mid + 1.7) + 1.0 / (0.92 * mid + 0.62));
                (t > hit.teffK ? lo : hi) = mid;
            }
            b.bv = 0.5 * (lo + hi);
        }
        b.radiusKm = hit.teffK > 0 ? rayon_etoile::rayonKm(hit.absMagG, b.bv) : 0.0;
        const std::string jeu = setB ? "gaia_b.bin, distance à 10-20 % près" : "gaia.bin, distance à mieux que 10 %";
        b.name = "Étoile Gaia n° " + std::to_string(hit.index) + (setB ? " (jeu B)" : "");
        b.natureText = "étoile sans nom propre, Gaia DR3 (" + jeu + ") ; magnitude absolue G " + std::to_string(hit.absMagG).substr(0, 5) +
                       (hit.flags & 1 ? " ; vitesse radiale mesurée" : " ; sans vitesse radiale (comptée nulle)") +
                       " ; place en ligne droite depuis la mesure, à 100 000 ans au plus d'aujourd'hui" +
                       (hit.teffK > 0 ? " ; rayon calculé d'après G et la couleur (approché : G n'est pas V)" : "");
        return gaiaStarBody;
    }

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
    // mLim : magnitude apparente au-delà de laquelle il n'est pas visible à l'écran (depuis leur vrai éclat, audit A6) ; 99 : tous
    int nearestAsteroid(const Camera& cam, double px, double py, double w, double h, double maxPx, double mLim = 99.0) const {
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
                    if (mLim < 90.0) {      // vraie lumière : m = H + 5 log10(r Δ), comme asteroides.vert
                        const double r = std::sqrt(au[0] * au[0] + au[1] * au[1] + au[2] * au[2]);
                        const double dx = au[0] - cam.pos.x / kAuInLy, dy = au[1] - cam.pos.y / kAuInLy, dz = au[2] - cam.pos.z / kAuInLy;
                        if (asteroidCat->cols[9][k] + 5.0 * std::log10(std::max(r * std::sqrt(dx * dx + dy * dy + dz * dz), 1e-12)) > mLim) continue;
                    }
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
inline std::string frNum(double v, int digits = 3) {
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
inline std::string frInt(double v) { return frNum(std::round(v), 1 + static_cast<int>(std::floor(std::log10(std::max(1.0, std::fabs(v)))))); }

// Une longueur donnée en années-lumière, écrite dans l'unité qui parle.
inline std::string frDistance(double ly) {
    const double km = ly * kLyInKm, au = ly / kAuInLy;
    if (ly >= 1.0e9) return frNum(ly / 1.0e9) + " milliards d'années-lumière";
    if (ly >= 1.0e6) return frNum(ly / 1.0e6) + " millions d'années-lumière";
    if (ly >= 0.1) return frNum(ly) + (ly >= 2 ? " années-lumière" : " année-lumière");
    if (au >= 0.1) return frNum(au) + " fois la distance Terre-Soleil";
    if (km >= 1.0e6) return frNum(km / 1.0e6) + " millions de km";
    return frInt(km) + " km";
}

// Date : jour, mois, année tant que le calendrier a un sens ; sinon l'année seule.
inline std::string frDate(double years, bool withTime = false) {
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

}  // namespace univers