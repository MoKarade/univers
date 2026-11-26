// Contrôle de l'orientation des astres (orientation.h) avec les éphémérides de la NASA.
//
// 1. Terre : le point où le Soleil est au zénith. Le 12 novembre 2026 à 12 h 00 TU, il doit être à la latitude
//    de la déclinaison du Soleil (-17,7° à -17,9°) et à la longitude donnée par l'équation du temps (le Soleil
//    passe au méridien de Greenwich environ 15 min 50 s avant midi, donc le point est vers 3,9° ouest).
//    Valeurs attendues tirées des tables usuelles de déclinaison et d'équation du temps [Probable : de mémoire] ;
//    tolérance 0,5°.
// 2. Terre, 20 mars 2026 à 14 h 46 TU (équinoxe de mars, heure publiée) : latitude du point à 0° ± 0,1°.
// 3. Lune : le point tourné vers la Terre reste près du centre de la face visible (librations : ± 8,5°), sur
//    60 dates réparties sur 2 ans.
// Usage : essai_orientation <de440.bsp>
#include <algorithm>
#include <cstdio>

#include "orientation.h"

namespace {
double daysOf(int y, int m, int d, double hoursUtc) {      // jours TDB depuis J2000,0 (calendrier grégorien)
    const int a = (14 - m) / 12, yy = y + 4800 - a, mm = m + 12 * a - 3;
    const long jdn = d + (153 * mm + 2) / 5 + 365L * yy + yy / 4 - yy / 100 + yy / 400 - 32045;
    return (static_cast<double>(jdn) - 2451545.0) - 0.5 + hoursUtc / 24.0 + 69.184 / 86400.0;
}
}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "usage : essai_orientation <de440.bsp>\n"); return 2; }
    eph::Spk spk;
    std::string error;
    if (!spk.open(argv[1], error)) { std::fprintf(stderr, "ECHEC : %s\n", error.c_str()); return 1; }
    bool ok = true;
    auto direction = [&](int from, int to, double days, double out[3]) {
        eph::Vec a, b, v;
        spk.state(from, days * 86400.0, a, v);
        spk.state(to, days * 86400.0, b, v);
        const eph::Vec e = eph::toEcliptic({b.x - a.x, b.y - a.y, b.z - a.z});
        out[0] = e.x; out[1] = e.y; out[2] = e.z;
    };
    {
        const double days = daysOf(2026, 11, 12, 12.0);
        ori::Mat3 m;
        ori::eclipticToBody(eph::kEarth, days, m);
        double d[3], lon, lat;
        direction(eph::kEarth, eph::kSun, days, d);
        ori::subPoint(m, d[0], d[1], d[2], lon, lat);
        const bool good = std::fabs(lat + 17.8) < 0.5 && std::fabs(lon + 3.95) < 0.5;
        ok &= good;
        std::printf("Terre, 12 novembre 2026, 12 h TU : Soleil au zenith a la latitude %.2f (attendu -17,8), longitude %.2f (attendu -3,95) -> %s\n", lat, lon,
                    good ? "PASSE" : "ECHEC");
    }
    {
        const double days = daysOf(2026, 3, 20, 14.0 + 46.0 / 60.0);
        ori::Mat3 m;
        ori::eclipticToBody(eph::kEarth, days, m);
        double d[3], lon, lat;
        direction(eph::kEarth, eph::kSun, days, d);
        ori::subPoint(m, d[0], d[1], d[2], lon, lat);
        const bool good = std::fabs(lat) < 0.1;
        ok &= good;
        std::printf("Terre, equinoxe du 20 mars 2026 : latitude du Soleil au zenith %.3f (attendu 0) -> %s\n", lat, good ? "PASSE" : "ECHEC");
    }
    {
        double worstLon = 0, worstLat = 0;
        for (int k = 0; k < 60; ++k) {
            const double days = daysOf(2026, 1, 1, 0) + k * 12.37;
            ori::Mat3 m;
            ori::eclipticToBody(eph::kMoon, days, m);
            double d[3], lon, lat;
            direction(eph::kMoon, eph::kEarth, days, d);
            ori::subPoint(m, d[0], d[1], d[2], lon, lat);
            worstLon = std::max(worstLon, std::fabs(lon));
            worstLat = std::max(worstLat, std::fabs(lat));
        }
        const bool good = worstLon < 12.0 && worstLat < 9.0;      // librations (8°) + termes périodiques non repris (jusqu'à 3,6°)
        ok &= good;
        std::printf("Lune, 60 dates : point tourne vers la Terre a moins de %.1f degres en longitude et %.1f en latitude du centre de la face visible -> %s\n",
                    worstLon, worstLat, good ? "PASSE" : "ECHEC");
    }
    std::printf(ok ? "PASSE\n" : "ECHEC\n");
    return ok ? 0 : 1;
}
