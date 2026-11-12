// Appli PC « Univers » : l'état du simulateur (temps, astres, objet suivi, caméra), sans rien qui dépende de l'affichage.
#pragma once
#include "commun.h"
#include "cosmologie.h"
#include "ephemeride.h"

namespace {

constexpr double kLyInMeters = 9.4607304725808e15;      // année-lumière julienne (UAI)
constexpr double kLyInKm = kLyInMeters / 1000.0;
constexpr double kAuInLy = 149597870700.0 / kLyInMeters;
constexpr double kYearSeconds = 365.25 * 86400.0;
// Aujourd'hui, lu sur l'horloge du PC, en années juliennes depuis J2000,0 (1er janvier 2000, 12 h TU = 946 728 000 s Unix).
inline const double kStartYears =
    (std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count() - 946728000.0) / kYearSeconds;
constexpr double kLinearLimitYears = 3.0e6;      // au-delà, la ligne droite ne vaut plus pour les étoiles (page : épicycles puis orbites) : étape E5
// Temps des éphémérides (TDB) moins temps civil (UTC) : 69,184 s depuis 2017 (32,184 s + 37 secondes intercalaires).
// [Approximation assumée : appliquée à toute date ; l'écart réel a varié de quelques dizaines de secondes par siècle.]
constexpr double kTdbMinusUtc = 69.184;

enum class Kind { Sun, Star, Planet, Galaxy };

// Un astre que l'on peut suivre, chercher, nommer à l'écran.
struct Body {
    std::string name;
    Kind kind = Kind::Star;
    int64_t star = -1;          // étoile : numéro dans le catalogue
    int naif = 0;               // planète : code du corps dans les éphémérides de la NASA
    int parent = -1;            // lune : numéro de l'astre autour duquel elle tourne (pour le tracé de l'orbite)
    double h = 0;               // planète : magnitude à 1 UA du Soleil et de l'observateur, pleine phase
    double bv = 0.65;           // indice de couleur B-V
    double periodYears = 0;     // planète : durée d'un tour (pour tracer l'orbite)
    double radiusKm = 0;        // rayon moyen
    const char* nature = "";
    std::string natureText;     // galaxie : genre lu dans le fichier
    Vec3 fixedPos{0, 0, 0};     // galaxie : position mesurée (années-lumière), immobile pour l'instant
    int priority = 1;           // galaxie : 1 = nom montré dès qu'on sort de la Voie lactée
    const char* natureLabel() const { return natureText.empty() ? nature : natureText.c_str(); }
};

// Planètes : magnitude H et couleur B-V d'après Mallama et Hilton 2018 (Astronomy and Computing 25, 10) et
// l'Astronomical Almanac ; rayons moyens UAI 2015 ; périodes sidérales NASA (fiches « Planetary Fact Sheet »).
// [Probable : valeurs recopiées de mémoire, à relire contre les sources avant de s'en servir pour autre chose
//  que l'éclat des points et le tracé des orbites.]
struct PlanetRow {
    const char* name;
    int naif;
    double h, bv, periodYears, radiusKm;
    const char* nature;
};
constexpr PlanetRow kPlanets[] = {
    {"Mercure", eph::kMercury, -0.613, 0.93, 0.2408467, 2439.4, "planète rocheuse"},
    {"Vénus", eph::kVenus, -4.384, 0.82, 0.61519726, 6051.8, "planète rocheuse"},
    {"Terre", eph::kEarth, -3.99, 0.33, 1.0000174, 6371.0, "planète rocheuse"},
    {"Mars", eph::kMarsBary, -1.601, 1.36, 1.8808476, 3389.5, "planète rocheuse"},
    {"Jupiter", eph::kJupiterBary, -9.395, 0.83, 11.862615, 69911.0, "géante gazeuse"},
    {"Saturne", eph::kSaturnBary, -8.914, 1.04, 29.447498, 58232.0, "géante gazeuse"},
    {"Uranus", eph::kUranusBary, -7.110, 0.56, 84.016846, 25362.0, "géante de glace"},
    {"Neptune", eph::kNeptuneBary, -7.00, 0.41, 164.79132, 24622.0, "géante de glace"},
    {"Pluton", eph::kPlutoBary, -1.0, 0.82, 247.92065, 1188.3, "planète naine"},
};
constexpr PlanetRow kMoon = {"Lune", eph::kMoon, 0.28, 0.92, 27.321661 / 365.25, 1737.4, "satellite de la Terre"};

struct Rate {
    const char* label;
    double yearsPerSecond;
};
constexpr Rate kRates[] = {{"Temps réel", 1.0 / kYearSeconds},        {"1 heure par seconde", 3600.0 / kYearSeconds}, {"1 jour par seconde", 1.0 / 365.25},
                           {"1 mois par seconde", 1.0 / 12.0},         {"1 an par seconde", 1.0},                      {"100 ans par seconde", 100.0},
                           {"10 000 ans par seconde", 1.0e4},          {"100 000 ans par seconde", 1.0e5}};
constexpr int kRateCount = static_cast<int>(sizeof(kRates) / sizeof(kRates[0]));

struct Sim {
    const Stars* stars = nullptr;
    const eph::Spk* spk = nullptr;       // éphémérides de la NASA ; nul si le fichier manque
    std::vector<Body> bodies;            // 0 : le Soleil ; puis planètes et Lune ; puis les étoiles nommées de la page
    std::vector<Vec3> planetPos;         // position de chaque astre de type planète à la date courante (années-lumière, centre : Soleil)
    bool ephemValid = false;             // la date courante est dans la plage des éphémérides
    int focus = 0;
    double years = kStartYears;          // années juliennes depuis J2000,0
    int rate = 2;
    bool paused = false, backward = false;
    double yaw = -1.2, pitch = 0.55;     // direction d'où l'on regarde l'astre suivi (radians)
    double dist = 45.0 * kAuInLy;        // distance de la caméra à l'astre suivi (années-lumière) : au départ, tout le système solaire
    bool touched = false;                // quelqu'un a pris la main : fin du lent tour d'horizon
    double asteroidEpochJd = 0;          // date des orbites des astéroïdes (0 : pas d'astéroïdes)
    uint64_t asteroidCount = 0;
    cosmo::Params cosmology;             // paramètres de l'univers en expansion (réglables à l'écran)
    bool cosmologyDirty = true;          // les distances des galaxies sont à recalculer

    // Le Soleil, les planètes (si les éphémérides sont là), puis les étoiles nommées (etoiles_noms.tsv).
    void loadBodies(const std::string& namesPath, const std::string& galaxiesPath) {
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
                b.parent = parent;
                b.h = r.h;
                b.bv = r.bv;
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
        }
        std::ifstream f(namesPath);
        std::string line;
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
        std::ifstream gf(galaxiesPath);
        while (std::getline(gf, line)) {
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
        planetPos.assign(bodies.size(), {0, 0, 0});
        refreshEphemeris();
    }

    // Position héliocentrique d'un corps des éphémérides à une date donnée (années-lumière, écliptique J2000). false : hors de la plage.
    bool planetAt(int naif, double atYears, Vec3& out) const {
        if (!spk) return false;
        const double et = atYears * kYearSeconds + kTdbMinusUtc;
        eph::Vec p, v, s, sv;
        if (!spk->state(naif, et, p, v) || !spk->state(eph::kSun, et, s, sv)) return false;
        const eph::Vec e = eph::toEcliptic({p.x - s.x, p.y - s.y, p.z - s.z});
        out = {e.x / kLyInKm, e.y / kLyInKm, e.z / kLyInKm};
        return true;
    }

    void refreshEphemeris() {
        ephemValid = spk != nullptr;
        for (size_t i = 0; i < bodies.size(); ++i)
            if (bodies[i].kind == Kind::Planet && !planetAt(bodies[i].naif, years, planetPos[i])) ephemValid = false;
    }

    bool visible(int i) const { return bodies[static_cast<size_t>(i)].kind != Kind::Planet || ephemValid; }

    // Position à la date courante (années-lumière, repère écliptique centré sur le Soleil).
    Vec3 position(int i) const {
        const Body& b = bodies[static_cast<size_t>(i)];
        if (b.kind == Kind::Sun) return {0, 0, 0};
        if (b.kind == Kind::Planet) return planetPos[static_cast<size_t>(i)];
        if (b.kind == Kind::Galaxy) return b.fixedPos;
        const double k = years * kKmsToLyPerYear;      // étoile : ligne droite à la vitesse mesurée
        return {stars->x()[b.star] + stars->vel(0)[b.star] * k, stars->y()[b.star] + stars->vel(1)[b.star] * k, stars->z()[b.star] + stars->vel(2)[b.star] * k};
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
        if (b.kind == Kind::Galaxy) return 99.0;      // éclat des galaxies : pas dans les données pour l'instant
        const Vec3 p = position(i), d = p - from;
        const double dist = std::max(std::sqrt(dot(d, d)), 1e-15);
        if (b.kind == Kind::Planet) {
            const double r = std::max(std::sqrt(dot(p, p)), 1e-15);
            const double cosA = std::clamp((dot(p, d)) / (r * dist), -1.0, 1.0);      // angle Soleil-planète-observateur
            const double alpha = std::acos(cosA);
            const double phase = std::max((std::sin(alpha) + (kPi - alpha) * std::cos(alpha)) / kPi, 1e-6);
            return b.h + 5.0 * std::log10((r / kAuInLy) * (dist / kAuInLy)) - 2.5 * std::log10(phase);
        }
        const double absMag = b.kind == Kind::Sun ? kSunAbsMag : stars->mag()[b.star];
        return absMag + 5.0 * std::log10(dist / 3.2615638) - 5.0;
    }

    Camera camera(double aspect) const {
        const Vec3 target = position(focus);
        const Vec3 dir{std::cos(pitch) * std::cos(yaw), std::cos(pitch) * std::sin(yaw), std::sin(pitch)};
        return lookAt({target.x + dist * dir.x, target.y + dist * dir.y, target.z + dist * dir.z}, target, 60.0, aspect);
    }

    // Les étoiles pâlissent en 1/d² : loin de tout, on multiplie leur éclat pour qu'elles restent visibles, et on le dit.
    double brightnessBoost() const {
        const double k = std::clamp(dist / 30.0, 1.0, 70.0);      // plafonné : au-delà de 2 000 années-lumière, les étoiles mesurées se fondent en un point
        return k * k;
    }
    // Astéroïdes : montrés à l'échelle du système solaire (plein éclat jusqu'à 60 fois la distance Terre-Soleil, éteints
    // à 600), et seulement à moins de 300 ans de la date de leurs orbites : au-delà, l'orbite simple ne vaut plus.
    double asteroidGain(double epochJd) const {
        const double au = dist / kAuInLy;
        const double fade = std::clamp((std::log10(600.0) - std::log10(std::max(au, 1e-9))) / (std::log10(600.0) - std::log10(60.0)), 0.0, 1.0);
        const double epochYears = (epochJd - 2451545.0) / 365.25;
        return std::fabs(years - epochYears) < 300.0 ? 0.30 * fade : 0.0;
    }
    // Éclat donné à chaque galaxie des relevés : nul tant qu'on est dans la Voie lactée, plein au-delà de 3 millions d'années-lumière.
    double galaxyGain() const {
        const double t = std::clamp((std::log10(std::max(dist, 1.0)) - 4.5) / 2.0, 0.0, 1.0);
        return 0.10 * t * t * (3.0 - 2.0 * t);
    }

    void advance(double dt) {
        if (!paused) years += (backward ? -1.0 : 1.0) * kRates[rate].yearsPerSecond * dt;
        years = std::clamp(years, kStartYears - kLinearLimitYears, kStartYears + kLinearLimitYears);
        if (!touched) yaw += 0.035 * dt;      // lent tour d'horizon, 2 degrés par seconde
        refreshEphemeris();
        if (!visible(focus)) focus = 0;       // l'astre suivi n'a plus de position connue : retour au Soleil
    }
    double minDist(int i) const {      // on s'arrête un peu au-dessus de la surface (1,25 rayon du centre)
        if (bodies[static_cast<size_t>(i)].kind == Kind::Galaxy) return 1.0e3;
        return std::max(1.25 * bodies[static_cast<size_t>(i)].radiusKm / kLyInKm, 2.0e-10);
    }
    static constexpr double kMaxDist = 9.0e10;      // un peu plus que la distance des objets les plus lointains (z = 7)
    void zoom(double notches) { dist = std::clamp(dist * std::pow(0.8, notches), minDist(focus), kMaxDist); }
    void orbit(double dx, double dy) {
        yaw -= dx * 0.005;
        pitch = std::clamp(pitch + dy * 0.005, -1.55, 1.55);
    }
    void follow(int i) {
        if (!visible(i)) return;
        const Body& b = bodies[static_cast<size_t>(i)];
        focus = i;
        // Distance d'arrivée : de quoi voir l'astre dans son voisinage.
        double arrive = 50.0;                                                       // étoile : on garde ou on se rapproche à 50 années-lumière
        if (b.kind == Kind::Sun) arrive = 45.0 * kAuInLy;
        if (b.kind == Kind::Planet) arrive = 6.0 * b.radiusKm / kLyInKm;      // planète ou lune : elle remplit un bon tiers de l'écran
        dist = std::clamp(std::min(dist, arrive), minDist(i), kMaxDist);
        if (b.kind == Kind::Galaxy) dist = std::max(dist, 3.0e5);      // une galaxie se regarde de loin
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
