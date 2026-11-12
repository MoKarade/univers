// Appli PC « Univers » : l'état du simulateur (temps, objet suivi, caméra), sans rien qui dépende de l'affichage.
#pragma once
#include "commun.h"

namespace {

constexpr double kLyInMeters = 9.4607304725808e15;      // année-lumière julienne (UAI)
constexpr double kAuInLy = 149597870700.0 / kLyInMeters;
// Aujourd'hui, lu sur l'horloge du PC, en années juliennes depuis J2000,0 (1er janvier 2000, 12 h TU = 946 728 000 s Unix).
inline const double kStartYears =
    (std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count() - 946728000.0) / (365.25 * 86400.0);
constexpr double kLinearLimitYears = 3.0e6;              // au-delà, la ligne droite ne vaut plus (page : épicycles puis orbites) : étape E5

// Un objet que l'on peut suivre, chercher, nommer à l'écran.
struct Body {
    std::string name;
    int64_t star = -1;      // numéro dans le catalogue ; -1 : le Soleil
};

struct Rate {
    const char* label;
    double yearsPerSecond;
};
constexpr Rate kRates[] = {{"Temps réel", 1.0 / (365.25 * 86400.0)}, {"1 jour par seconde", 1.0 / 365.25}, {"1 an par seconde", 1.0},
                           {"100 ans par seconde", 100.0},           {"10 000 ans par seconde", 1.0e4},    {"100 000 ans par seconde", 1.0e5}};
constexpr int kRateCount = static_cast<int>(sizeof(kRates) / sizeof(kRates[0]));

struct Sim {
    const Stars* stars = nullptr;
    std::vector<Body> bodies;      // 0 : le Soleil, puis les étoiles nommées de la page
    int focus = 0;
    double years = kStartYears;    // années juliennes depuis J2000,0 (époque des positions du catalogue, comme dans la page)
    int rate = 0;
    bool paused = false, backward = false;
    double yaw = 0, pitch = 0.3;   // direction d'où l'on regarde l'objet suivi (radians)
    double dist = 6.0;             // distance de la caméra à l'objet suivi (années-lumière)
    bool touched = false;          // quelqu'un a pris la main : fin du lent tour d'horizon

    // Lit etoiles_noms.tsv (numéro, nom, distance), écrit par pipeline/natif/etoiles.py.
    void loadBodies(const std::string& path) {
        bodies.clear();
        bodies.push_back({"Soleil", -1});
        std::ifstream f(path);
        std::string line;
        while (std::getline(f, line)) {
            const size_t a = line.find('\t'), b = line.find('\t', a + 1);
            if (a == std::string::npos) continue;
            Body body;
            body.star = std::strtoll(line.substr(0, a).c_str(), nullptr, 10);
            body.name = line.substr(a + 1, b == std::string::npos ? std::string::npos : b - a - 1);
            if (body.star >= 0 && static_cast<uint64_t>(body.star) < stars->n) bodies.push_back(body);
        }
    }

    // Position à la date courante (années-lumière, repère écliptique centré sur le Soleil) : ligne droite à la vitesse mesurée.
    Vec3 position(int i) const {
        const int64_t s = bodies[static_cast<size_t>(i)].star;
        if (s < 0) return {0, 0, 0};
        const double k = years * kKmsToLyPerYear;
        return {stars->x()[s] + stars->vel(0)[s] * k, stars->y()[s] + stars->vel(1)[s] * k, stars->z()[s] + stars->vel(2)[s] * k};
    }
    double absMag(int i) const { return bodies[static_cast<size_t>(i)].star < 0 ? kSunAbsMag : stars->mag()[bodies[static_cast<size_t>(i)].star]; }
    double bv(int i) const { return bodies[static_cast<size_t>(i)].star < 0 ? kSunBv : stars->bv()[bodies[static_cast<size_t>(i)].star]; }
    double speedKms(int i) const {
        const int64_t s = bodies[static_cast<size_t>(i)].star;
        if (s < 0) return 0;
        return std::sqrt(static_cast<double>(stars->vel(0)[s]) * stars->vel(0)[s] + static_cast<double>(stars->vel(1)[s]) * stars->vel(1)[s] +
                         static_cast<double>(stars->vel(2)[s]) * stars->vel(2)[s]);
    }
    // Magnitude apparente d'un objet vu d'un point donné.
    double apparentMag(int i, Vec3 from) const {
        const Vec3 d = position(i) - from;
        const double dist = std::max(std::sqrt(dot(d, d)), 1e-12);
        return absMag(i) + 5.0 * std::log10(dist / 3.2615638) - 5.0;
    }

    Camera camera(double aspect) const {
        const Vec3 target = position(focus);
        const Vec3 dir{std::cos(pitch) * std::cos(yaw), std::cos(pitch) * std::sin(yaw), std::sin(pitch)};
        return lookAt({target.x + dist * dir.x, target.y + dist * dir.y, target.z + dist * dir.z}, target, 60.0, aspect);
    }

    // Les étoiles pâlissent en 1/d² : loin de tout, on multiplie leur éclat pour qu'elles restent visibles, et on le dit.
    double brightnessBoost() const {
        const double k = std::max(1.0, dist / 30.0);
        return k * k;
    }

    void advance(double dt) {
        if (!paused) years += (backward ? -1.0 : 1.0) * kRates[rate].yearsPerSecond * dt;
        years = std::clamp(years, kStartYears - kLinearLimitYears, kStartYears + kLinearLimitYears);
        if (!touched) yaw += 0.035 * dt;      // lent tour d'horizon, 2 degrés par seconde
    }
    void zoom(double notches) { dist = std::clamp(dist * std::pow(0.8, notches), 2.0e-9, 4.0e5); }
    void orbit(double dx, double dy) {
        yaw -= dx * 0.005;
        pitch = std::clamp(pitch + dy * 0.005, -1.55, 1.55);
    }
    void follow(int i) {
        focus = i;
        dist = std::clamp(dist, 2.0e-9, 50.0);      // on se rapproche si l'on était parti très loin
    }
};

// ---------------------------------------------------------------- textes en français
std::string frNum(double v, int digits = 3) {
    char buf[64];
    const double a = std::fabs(v);
    int dec = 0;
    if (a < 1e-12) dec = 0;
    else dec = std::clamp(digits - 1 - static_cast<int>(std::floor(std::log10(a))), 0, 6);
    std::snprintf(buf, sizeof(buf), "%.*f", dec, v);
    std::string s(buf);
    const size_t dot = s.find('.');
    std::string intPart = s.substr(0, dot), frac = dot == std::string::npos ? "" : s.substr(dot + 1);
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

// Une longueur donnée en années-lumière, écrite dans l'unité qui parle.
std::string frDistance(double ly) {
    const double m = ly * kLyInMeters, au = ly / kAuInLy;
    if (ly >= 0.1) return frNum(ly) + (ly >= 2 ? " années-lumière" : " année-lumière");
    if (au >= 0.01) return frNum(au) + " fois la distance Terre-Soleil";
    if (m >= 1.0e9) return frNum(m / 1.0e9) + " millions de km";
    return frNum(m / 1000.0) + " km";
}

// Date : jour, mois, année tant que le calendrier a un sens ; sinon l'année seule.
std::string frDate(double years) {
    static const char* months[] = {"janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"};
    if (std::fabs(years) > 6000.0) {      // hors de la plage où le calcul du calendrier est sûr
        const double y = 2000.0 + years;
        return y >= 0 ? "An " + frNum(std::round(y), 1 + static_cast<int>(std::floor(std::log10(std::max(1.0, std::fabs(y))))))
                      : frNum(std::round(-y), 1 + static_cast<int>(std::floor(std::log10(std::max(1.0, std::fabs(y)))))) + " ans avant notre ère";
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
    char buf[80];
    std::snprintf(buf, sizeof(buf), "%lld %s %lld", day, months[std::clamp<long long>(month, 1, 12) - 1], year);
    return buf;
}

}  // namespace
