// Contrôle de groupe_local.h (rejeu du calcul complet de la fusion).
// Départ conforme aux mesures de la page (Andromède, Grand Nuage), fusion à 5,44 Ga, images lues correctement (centre des
// étoiles de chaque grande galaxie sur son centre calculé), « inconnu » hors du calcul.
// Usage : essai_fusion <fusion_centres.bin> <dossier des kf_NNN.bin>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <vector>

#include <cstdlib>

#include "groupe_local.h"

using namespace phys::fusion;
static int g_fail = 0;
static void ok(bool c, const char* fmt, double a = 0, double b = 0, double d = 0) { std::printf("%s ", c ? "PASSE" : "ECHEC"); std::printf(fmt, a, b, d); std::printf("\n"); if (!c) g_fail++; }

int main(int argc, char** argv) {
    if (argc < 3) { std::fprintf(stderr, "usage : essai_fusion <fusion_centres.bin> <dossier des images> [date de fusion attendue, Ga]\n"); return 2; }
    Rejeu r; ok(r.charger(argv[1], argv[2]), "chargement des centres et des images");
    phys::Vec3 c;
    ok(r.centre(kAndromede, 0, c) && std::hypot(c.x + 385.352, c.y - 623.003, c.z + 287.592) < 0.1, "Andromède aujourd'hui à sa position mesurée (écart %.3f kpc)", std::hypot(c.x + 385.352, c.y - 623.003, c.z + 287.592));
    ok(r.centre(kGrandNuage, 0, c) && std::hypot(c.x + 1.0, c.y + 41.0, c.z + 27.8) < 0.2, "Grand Nuage aujourd'hui à sa position mesurée (écart %.3f kpc)", std::hypot(c.x + 1.0, c.y + 41.0, c.z + 27.8));
    const double attendue = argc > 3 ? std::atof(argv[3]) : 5.44;      // R9 : 5,44 ; calcul à 3 M de particules : 5,42
    ok(std::fabs(r.fusionGa() - attendue) < 1e-9 && r.deriveEnergie() < 0.01, "fusion à %.2f Ga, dérive d'énergie %.3f %%", r.fusionGa(), 100 * r.deriveEnergie());
    ok(!r.centre(kAndromede, -0.1, c) && !r.centre(kAndromede, r.finGa() + 0.1, c), "hors du calcul (avant aujourd'hui, après %.0f Ga) : « inconnu »", r.finGa());
    std::vector<phys::Vec3> e(r.nombreEtoiles());
    for (double t : {0.0, 4.0, 10.0}) {
        ok(r.etoilesA(t, e), "images lues à %.0f Ga", t);
        int o = 0;
        for (int g : {kVoieLactee, kAndromede}) {
            std::vector<double> x, y, z; for (int i = o; i < o + r.etoiles(g); i++) { x.push_back(e[i].x); y.push_back(e[i].y); z.push_back(e[i].z); }
            auto med = [](std::vector<double>& v) { std::nth_element(v.begin(), v.begin() + v.size() / 2, v.end()); return v[v.size() / 2]; };
            r.centre(g, t, c); const double d = std::hypot(med(x) - c.x, med(y) - c.y, med(z) - c.z);
            ok(d < 3, g == kVoieLactee ? "%.0f Ga : étoiles de la Voie lactée centrées sur leur centre calculé (%.2f kpc)" : "%.0f Ga : étoiles d'Andromède centrées sur leur centre calculé (%.2f kpc)", t, d);
            o += r.etoiles(g);
        }
    }
    std::printf(g_fail ? "ECHEC (%d)\n" : "PASSE\n", g_fail);
    return g_fail ? 1 : 0;
}
