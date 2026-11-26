// Contrôle de groupe_local.h (rejeu du calcul complet de la fusion).
// Départ conforme aux mesures de la page (Andromède, Grand Nuage), fusion à 5,44 Ga, images lues correctement (centre des
// étoiles de chaque grande galaxie sur son centre calculé), « inconnu » hors du calcul.
// Usage : essai_fusion <fusion_centres.bin> <dossier des kf_NNN.bin>
#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <vector>

#include "groupe_local.h"

using namespace phys::fusion;
static int g_fail = 0;

#if defined(__GNUC__) || defined(__clang__)
__attribute__((format(printf, 2, 3)))
#endif
static void ok(bool c, const char* fmt, ...) {
    std::printf("%s ", c ? "PASSE" : "ECHEC");
    std::va_list ap;
    va_start(ap, fmt);
    std::vprintf(fmt, ap);
    va_end(ap);
    std::putchar('\n');
    if (!c) ++g_fail;
}

int main(int argc, char** argv) {
    if (argc < 3) {
        std::fprintf(stderr, "usage : essai_fusion <fusion_centres.bin> <dossier des images>\n");
        return 2;
    }
    Rejeu r;
    ok(r.charger(argv[1], argv[2]), "chargement des centres et des images");
    phys::Vec3 c;
    {
        const bool found = r.centre(kAndromede, 0.0, c);
        const double d = std::hypot(c.x + 385.352, c.y - 623.003, c.z + 287.592);
        ok(found && d < 0.1, "Andromède aujourd'hui à sa position mesurée (écart %.3f kpc)", d);
    }
    {
        const bool found = r.centre(kGrandNuage, 0.0, c);
        const double d = std::hypot(c.x + 1.0, c.y + 41.0, c.z + 27.8);
        ok(found && d < 0.2, "Grand Nuage aujourd'hui à sa position mesurée (écart %.3f kpc)", d);
    }
    ok(std::fabs(r.fusionGa() - 5.44) < 1e-9 && r.deriveEnergie() < 0.01,
       "fusion à %.2f Ga, dérive d'énergie %.3f %%", r.fusionGa(), 100.0 * r.deriveEnergie());
    ok(!r.centre(kAndromede, -0.1, c) && !r.centre(kAndromede, r.finGa() + 0.1, c),
       "hors du calcul (avant aujourd'hui, après %.0f Ga) : « inconnu »", r.finGa());
    if (r.nombreEtoiles() <= 0) {
        ok(false, "nombre d'étoiles nul");
    } else {
        std::vector<phys::Vec3> e(static_cast<size_t>(r.nombreEtoiles()));
        for (double t : {0.0, 4.0, 10.0}) {
            ok(r.etoilesA(t, e), "images lues à %.0f Ga", t);
            size_t o = 0;
            for (int g : {kVoieLactee, kAndromede}) {
                const size_t cnt = static_cast<size_t>(std::max(r.etoiles(g), 0));
                std::vector<double> x, y, z;
                x.reserve(cnt);
                y.reserve(cnt);
                z.reserve(cnt);
                for (size_t i = o; i < o + cnt && i < e.size(); ++i) {
                    x.push_back(e[i].x);
                    y.push_back(e[i].y);
                    z.push_back(e[i].z);
                }
                auto med = [](std::vector<double>& v) {
                    if (v.empty()) return 0.0;
                    const size_t mid = v.size() / 2;
                    std::nth_element(v.begin(), v.begin() + static_cast<std::ptrdiff_t>(mid), v.end());
                    return v[mid];
                };
                const bool found = r.centre(g, t, c);
                const double d = std::hypot(med(x) - c.x, med(y) - c.y, med(z) - c.z);
                ok(found && !x.empty() && d < 3.0,
                   g == kVoieLactee ? "%.0f Ga : étoiles de la Voie lactée centrées sur leur centre calculé (%.2f kpc)"
                                    : "%.0f Ga : étoiles d'Andromède centrées sur leur centre calculé (%.2f kpc)",
                   t, d);
                o += cnt;
            }
        }
    }
    std::printf(g_fail ? "ECHEC (%d)\n" : "PASSE\n", g_fail);
    return g_fail ? 1 : 0;
}
