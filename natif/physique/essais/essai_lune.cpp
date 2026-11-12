// Contrôle de lune.h : la Lune de Meeus (celle de la page) contre DE440, de 1600 à 2600 ; « inconnu » au-delà de ±4 000 ans.
// Usage : essai_lune <de440.bsp>
#include <cmath>
#include <cstdio>

#include "ephemeride.h"
#include "lune.h"

static int g_fail = 0;
static void ok(bool c, const char* fmt, double a = 0, double b = 0, double d = 0) { std::printf("%s ", c ? "PASSE" : "ECHEC"); std::printf(fmt, a, b, d); std::printf("\n"); if (!c) g_fail++; }

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "usage : essai_lune <de440.bsp>\n"); return 2; }
    eph::Set spk; std::string err; if (!spk.add(argv[1], err)) { std::fprintf(stderr, "ECHEC : %s\n", err.c_str()); return 1; }
    for (double an : {1600.0, 1800.0, 2000.0, 2026.9, 2300.0, 2600.0}) {
        const double jd = 2451545.0 + (an - 2000.0) * 365.25; eph::Vec m, mv, e, ev;
        spk.state(eph::kMoon, eph::etOfJd(jd), m, mv); spk.state(eph::kEarth, eph::etOfJd(jd), e, ev);
        const eph::Vec g = eph::toEcliptic({m.x - e.x, m.y - e.y, m.z - e.z}); phys::Vec3 l; phys::lune::geocentrique(jd, l);
        const double nl = std::hypot(l.x, l.y, l.z), ng = std::hypot(g.x, g.y, g.z), c = (l.x * g.x + l.y * g.y + l.z * g.z) / (nl * ng), as = std::acos(std::fmin(1.0, c)) * 206264.806;
        const double tol = 15 + 0.12 * std::fabs(an - 2000.0);      // ″ : 7″ près de 2000 (page), l'écart grandit avec le temps (marées non suivies par la théorie tronquée)
        ok(as < tol && std::fabs(nl - ng) < 50, "an %.0f : Lune de Meeus à %.1f″ et %.1f km de DE440", an, as, nl - ng);
    }
    phys::Vec3 l; ok(!phys::lune::geocentrique(2451545.0 + 4100 * 365.25, l), "dans 4 100 ans : « inconnu »");
    std::printf(g_fail ? "ECHEC (%d)\n" : "PASSE\n", g_fail); return g_fail ? 1 : 0;
}
