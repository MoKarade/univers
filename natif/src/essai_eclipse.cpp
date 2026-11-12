// Contrôle de la chaîne « éphémérides de la NASA + orientation de la Terre » sur une éclipse de Soleil.
//
// Éclipse totale du 12 août 2026. Catalogue de la NASA « Five Millennium Catalog of Solar Eclipses » (Espenak et Meeus,
// https://eclipse.gsfc.nasa.gov/SEcat5/SE2001-2100.html, ligne 09566, relue le 12 novembre 2026) : maximum à
// 17 h 47 min 06 s en temps dynamique (celui des éphémérides), au point 65° nord, 25° ouest (donné au degré près).
// Ici : à cet instant, l'axe de l'ombre (droite Soleil-Lune prolongée) doit toucher la Terre à moins de 1° de ce point.
// La Terre est prise sphérique (rayon moyen), la lumière instantanée.
// Second contrôle, sans valeur recopiée : une demi-heure avant et une demi-heure après, l'axe de l'ombre touche encore
// la Terre (il la balaie pendant environ une heure et demie), et un mois plus tard il la manque.
// Usage : essai_eclipse <de440.bsp>
#include <cstdio>

#include "orientation.h"

namespace {
double daysOf(int y, int m, int d, double hoursUtc) {      // jours TDB depuis J2000,0 (calendrier grégorien)
    const int a = (14 - m) / 12, yy = y + 4800 - a, mm = m + 12 * a - 3;
    const long jdn = d + (153 * mm + 2) / 5 + 365L * yy + yy / 4 - yy / 100 + yy / 400 - 32045;
    return (static_cast<double>(jdn) - 2451545.0) - 0.5 + hoursUtc / 24.0 + 69.184 / 86400.0;
}

// Point de la Terre touché par l'axe de l'ombre de la Lune ; false si l'axe manque la Terre.
bool shadowPoint(const eph::Spk& spk, double days, double& lonDeg, double& latDeg) {
    eph::Vec s, m, e, v;
    const double et = days * 86400.0;
    if (!spk.state(eph::kSun, et, s, v) || !spk.state(eph::kMoon, et, m, v) || !spk.state(eph::kEarth, et, e, v)) return false;
    s = eph::toEcliptic(s);
    m = eph::toEcliptic(m);
    e = eph::toEcliptic(e);
    double d[3] = {m.x - s.x, m.y - s.y, m.z - s.z};      // direction de l'ombre
    const double n = std::sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
    for (double& c : d) c /= n;
    const double o[3] = {m.x - e.x, m.y - e.y, m.z - e.z};      // Lune vue du centre de la Terre
    const double b = o[0] * d[0] + o[1] * d[1] + o[2] * d[2];
    const double c = o[0] * o[0] + o[1] * o[1] + o[2] * o[2] - 6371.0 * 6371.0;
    const double disc = b * b - c;
    if (disc < 0) return false;
    const double t = -b - std::sqrt(disc);
    if (t < 0) return false;
    ori::Mat3 rot;
    ori::eclipticToBody(eph::kEarth, days, rot);
    ori::subPoint(rot, o[0] + t * d[0], o[1] + t * d[1], o[2] + t * d[2], lonDeg, latDeg);
    return true;
}
}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "usage : essai_eclipse <de440.bsp>\n"); return 2; }
    eph::Spk spk;
    std::string error;
    if (!spk.open(argv[1], error)) { std::fprintf(stderr, "ECHEC : %s\n", error.c_str()); return 1; }
    bool ok = true;
    const double t0 = daysOf(2026, 8, 12, 17.0 + 47.0 / 60.0 + 6.0 / 3600.0 - 69.184 / 3600.0);      // 17 h 47 min 06 s en temps dynamique
    double lon = 0, lat = 0;
    const bool hit = shadowPoint(spk, t0, lon, lat);
    const double dLat = lat - 65.0, dLon = (lon + 25.0) * std::cos(65.0 * ori::kDeg);
    const bool good = hit && std::sqrt(dLat * dLat + dLon * dLon) < 1.0;
    ok &= good;
    std::printf("12 aout 2026, 17 h 47 min 06 s (temps dynamique) : axe de l'ombre a la latitude %.2f, longitude %.2f (NASA : 65 et -25, au degre pres) -> %s\n", lat, lon,
                good ? "PASSE" : "ECHEC");
    double a, b2;
    const bool before = shadowPoint(spk, t0 - 0.5 / 24.0, a, b2), after = shadowPoint(spk, t0 + 0.5 / 24.0, a, b2), later = shadowPoint(spk, t0 + 30.0, a, b2);
    const bool span = before && after && !later;
    ok &= span;
    std::printf("une demi-heure avant : %s ; une demi-heure apres : %s ; un mois plus tard : %s -> %s\n", before ? "ombre sur la Terre" : "rien", after ? "ombre sur la Terre" : "rien",
                later ? "ombre sur la Terre" : "rien", span ? "PASSE" : "ECHEC");
    std::printf(ok ? "PASSE\n" : "ECHEC\n");
    return ok ? 0 : 1;
}
