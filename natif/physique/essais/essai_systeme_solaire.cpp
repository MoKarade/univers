// Contrôle de la bibliothèque univers_physique, système solaire hors de DE440 (systeme_solaire.h).
//
// 1. Le noyau à N corps parti de JPL Horizons (10/11/2026) retrouve Horizons de 1650 à 2450 (nbody_ref.h, généré par
//    pipeline/natif/nbody_donnees.py depuis app/test/nbody_ref.json) : mêmes seuils que la page (app/test/nbody.test.js).
// 2. Parti de l'état DE440 à une borne (2650 ou 1550), le calcul revient sur DE440 lui-même 200 et 400 ans à l'intérieur.
// 3. Continuité à la borne, réponses « inconnu » (false) aux bons endroits, table ±10 millions d'années, plusieurs fils.
// Usage : essai_systeme_solaire [--noyau | <de440.bsp> [orbites_planetes.bin]]
// Imprime PASSE ou ECHEC par ligne ; code de sortie 0 si tout passe, 1 sinon.
#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string_view>
#include <thread>
#include <vector>

#include "ephemeride.h"
#include "essais/nbody_ref.h"
#include "systeme_solaire.h"

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

static double sepArcsec(const double* p, const double* q) {
    const double np = std::sqrt(p[0] * p[0] + p[1] * p[1] + p[2] * p[2]);
    const double nq = std::sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2]);
    if (np == 0.0 || nq == 0.0) return 0.0;
    const double c = std::clamp((p[0] * q[0] + p[1] * q[1] + p[2] * q[2]) / (np * nq), -1.0, 1.0);
    return std::acos(c) * 206264.806;
}

int main(int argc, char** argv) {
    bool noyauOnly = (argc < 2);
    if (argc >= 2) {
        const std::string_view arg1(argv[1]);
        if (arg1 == "--noyau") {
            if (argc > 2) {
                std::fprintf(stderr, "usage : essai_systeme_solaire [--noyau | <de440.bsp> [orbites_planetes.bin]]\n");
                return 2;
            }
            noyauOnly = true;
        } else if (arg1 == "--help" || arg1 == "-h") {
            std::printf("usage : essai_systeme_solaire [--noyau | <de440.bsp> [orbites_planetes.bin]]\n");
            return 0;
        } else if (arg1.starts_with("--")) {
            std::fprintf(stderr,
                         "option inconnue : %s\nusage : essai_systeme_solaire [--noyau | <de440.bsp> [orbites_planetes.bin]]\n",
                         argv[1]);
            return 2;
        }
    }

    // Ouvrir DE440 tôt en mode complet pour échouer immédiatement si le chemin est invalide.
    eph::Set spk;
    if (!noyauOnly) {
        std::string err;
        if (!spk.add(argv[1], err)) {
            std::fprintf(stderr, "ECHEC : %s\n", err.c_str());
            return 1;
        }
    }

    // 1. Noyau contre Horizons (positions héliocentriques, ″ ; seuils de la page ; autonome via nbody_ref.h).
    const double tol[13] = {5, 2, 2, 2, 1, 1, 1, 1, 1, 3, 3, 3, 3};
    for (const auto& R : kNbRefs) {
        phys::nb::Integrator it;
        it.advanceTo(R.jd);
        double b[42];
        it.barycentric(b);
        double worst = 0.0, wr = 0.0;
        for (int i = 0; i < 13; ++i) {
            const double p[3] = {b[3 * (i + 1)] - b[0], b[3 * (i + 1) + 1] - b[1], b[3 * (i + 1) + 2] - b[2]};
            const double q[3] = {R.r[3 * (i + 1)] - R.r[0], R.r[3 * (i + 1) + 1] - R.r[1], R.r[3 * (i + 1) + 2] - R.r[2]};
            const double s = sepArcsec(p, q);
            if (s / tol[i] > wr) {
                wr = s / tol[i];
                worst = s;
            }
        }
        ok(wr < 1.0, "noyau contre Horizons, jour julien %.1f : plus grand écart %.2f″ (%.2f du seuil)", R.jd, worst, wr);
    }

    if (noyauOnly) {
        std::printf(g_fail ? "ECHEC (%d)\n" : "PASSE\n", g_fail);
        return g_fail ? 1 : 0;
    }

    auto source = [&](int naif, double jd, phys::Vec3& p, phys::Vec3& v) {
        eph::Vec a, w;
        if (!spk.state(naif, eph::etOfJd(jd), a, w)) return false;
        a = eph::toEcliptic(a);
        w = eph::toEcliptic(w);
        p = {a.x, a.y, a.z};
        v = {w.x, w.y, w.z};
        return true;
    };

    // 2. Construction aux bornes, puis retour dans DE440.
    phys::SystemeSolaire ss;
    ok(ss.construire(source, 2000.0), "construction des points de reprise sur 2 000 ans de chaque côté");
    for (int side = 0; side < 2; ++side) {
        const phys::nb::State* s0 = ss.reprise(side == 1, 0);
        if (!s0) {
            ok(false, "point de reprise absent");
            continue;
        }
        for (double yrs : {200.0, 400.0}) {
            phys::nb::Integrator it(*s0);
            const double jd = s0->jd + (side ? -1.0 : 1.0) * yrs * 365.25;
            it.advanceTo(jd);
            double b[42];
            it.barycentric(b);
            double worst = 0.0;
            for (int i = 0; i < 8; ++i) {
                phys::Vec3 p, v, ps, vs;
                source(i + 1, jd, p, v);
                source(10, jd, ps, vs);
                const double q[3] = {p.x - ps.x, p.y - ps.y, p.z - ps.z};
                const double m[3] = {b[3 * (i + 1)] - b[0], b[3 * (i + 1) + 1] - b[1], b[3 * (i + 1) + 2] - b[2]};
                worst = std::fmax(worst, sepArcsec(m, q));
            }
            ok(worst < 10.0,
               side ? "parti de 2650, %.0f ans plus tôt : écart à DE440 %.2f″ au plus (planètes)"
                    : "parti de 1550, %.0f ans plus tard : écart à DE440 %.2f″ au plus (planètes)",
               yrs, worst);
        }
    }

    // 3. Continuité à la borne et réponses inconnues.
    phys::Vec3 p, v;
    phys::Statut st;
    {  // à la borne même, le point de reprise est l'état DE440 (positions identiques) ; juste après, réponse « calculé »
        const phys::nb::State* s0 = ss.reprise(true, 0);
        if (!s0) {
            ok(false, "point de reprise 2650 absent");
        } else {
            phys::Vec3 a, w, s, sv;
            source(5, s0->jd, a, w);
            source(10, s0->jd, s, sv);
            const double dx = s0->Q[12] * phys::kAuKm - (a.x - s.x);
            const double dy = s0->Q[13] * phys::kAuKm - (a.y - s.y);
            const double dz = s0->Q[14] * phys::kAuKm - (a.z - s.z);
            const double d = std::sqrt(dx * dx + dy * dy + dz * dz);
            ok(d < 1e-3, "continuité à la borne de 2650 : Jupiter à %.2g km de DE440", d);
            ok(ss.etat(phys::kJupiter, phys::kDe440Fin + 1.0, p, v, st) && st == phys::Statut::Calcule,
               "un jour après 2650 : Jupiter calculée, statut « calculé »");
        }
    }
    ok(!ss.etat(phys::kMars, 2461354.5, p, v, st), "dans la plage DE440 : réponse « inconnu » (l'appli lit la NASA)");
    ok(!ss.etat(phys::kMars, phys::kDe440Fin + 3000.0 * 365.25, p, v, st),
       "au-delà du calcul direct, sans table : « inconnu »");
    if (argc > 2) {
        ok(ss.chargerTable(argv[2]), "table des orbites sur des millions d'années chargée");
        ok(ss.etat(phys::kMars, 2461354.5 + 1e6 * 365.25, p, v, st),
           "dans un million d'années : Mars calculée par la table");
        ok(!ss.etat(phys::kCeres, 2461354.5 + 1e6 * 365.25, p, v, st),
           "dans un million d'années : Cérès inconnue (absente de la table)");
        ok(!ss.etat(phys::kMars, 2461354.5 + 2e7 * 365.25, p, v, st),
           "dans 20 millions d'années : « inconnu » (chaos)");
    }

    // 4. Plusieurs fils d'exécution : mêmes réponses.
    {
        const double jd = phys::kDe440Fin + 777.7 * 365.25;
        phys::Vec3 ref, rv;
        ss.etat(phys::kVenus, jd, ref, rv, st);
        std::vector<std::thread> th;
        std::vector<double> d(4, 1e30);
        for (size_t k = 0; k < 4; ++k) {
            th.emplace_back([&, k] {
                phys::Vec3 q, w;
                phys::Statut s2;
                for (int r = 0; r < 20; ++r) {
                    if (ss.etat(phys::kVenus, jd, q, w, s2)) {
                        d[k] = std::hypot(q.x - ref.x, q.y - ref.y, q.z - ref.z);
                    }
                }
            });
        }
        for (auto& t : th) {
            t.join();
        }
        const double m = *std::max_element(d.begin(), d.end());
        ok(m == 0.0, "quatre fils d'exécution : mêmes positions (écart %.3g km)", m);
    }
    std::printf(g_fail ? "ECHEC (%d)\n" : "PASSE\n", g_fail);
    return g_fail ? 1 : 0;
}
