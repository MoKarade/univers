// Contrôle de la bibliothèque univers_physique, système solaire hors de DE440 (systeme_solaire.h).
//
// 1. Le noyau à N corps parti de JPL Horizons (10/11/2026) retrouve Horizons de 1650 à 2450 (nbody_ref.h, généré par
//    pipeline/natif/nbody_donnees.py depuis app/test/nbody_ref.json) : mêmes seuils que la page (app/test/nbody.test.js).
// 2. Parti de l'état DE440 à une borne (2650 ou 1550), le calcul revient sur DE440 lui-même 200 et 400 ans à l'intérieur.
// 3. Continuité à la borne, réponses « inconnu » (false) aux bons endroits, table ±10 millions d'années, plusieurs fils.
// Usage : essai_systeme_solaire <de440.bsp> [orbites_planetes.bin]
// Imprime PASSE ou ECHEC par ligne ; code de sortie 0 si tout passe, 1 sinon.
#include <chrono>
#include <cmath>
#include <cstdio>
#include <thread>
#include <vector>

#include "ephemeride.h"
#include "essais/nbody_ref.h"
#include "systeme_solaire.h"

static int g_fail = 0;
static void ok(bool c, const char* fmt, double a = 0, double b = 0, double d = 0) {
    std::printf("%s ", c ? "PASSE" : "ECHEC"); std::printf(fmt, a, b, d); std::printf("\n"); if (!c) g_fail++;
}
static double sepArcsec(const double* p, const double* q) {
    const double np = std::sqrt(p[0] * p[0] + p[1] * p[1] + p[2] * p[2]), nq = std::sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2]);
    double c = (p[0] * q[0] + p[1] * q[1] + p[2] * q[2]) / (np * nq); if (c > 1) c = 1; return std::acos(c) * 206264.806;
}

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "usage : essai_systeme_solaire <de440.bsp> [orbites_planetes.bin]\n"); return 2; }
    eph::Set spk; std::string err;
    if (!spk.add(argv[1], err)) { std::fprintf(stderr, "ECHEC : %s\n", err.c_str()); return 1; }
    auto source = [&](int naif, double jd, phys::Vec3& p, phys::Vec3& v) {
        eph::Vec a, w; if (!spk.state(naif, eph::etOfJd(jd), a, w)) return false;
        a = eph::toEcliptic(a); w = eph::toEcliptic(w); p = {a.x, a.y, a.z}; v = {w.x, w.y, w.z}; return true; };

    // 1. Noyau contre Horizons (positions héliocentriques, ″ ; seuils de la page).
    const double tol[13] = {5, 2, 2, 2, 1, 1, 1, 1, 1, 3, 3, 3, 3};
    for (const auto& R : kNbRefs) {
        phys::nb::Integrator it; it.advanceTo(R.jd); double b[42]; it.barycentric(b);
        double worst = 0, wr = 0;
        for (int i = 0; i < 13; i++) {
            const double p[3] = {b[3 * (i + 1)] - b[0], b[3 * (i + 1) + 1] - b[1], b[3 * (i + 1) + 2] - b[2]};
            const double q[3] = {R.r[3 * (i + 1)] - R.r[0], R.r[3 * (i + 1) + 1] - R.r[1], R.r[3 * (i + 1) + 2] - R.r[2]};
            const double s = sepArcsec(p, q); if (s / tol[i] > wr) { wr = s / tol[i]; worst = s; }
        }
        ok(wr < 1, "noyau contre Horizons, jour julien %.1f : plus grand écart %.2f″ (%.2f du seuil)", R.jd, worst, wr);
    }

    // 2. Construction aux bornes, puis retour dans DE440.
    phys::SystemeSolaire ss;
    ok(ss.construire(source, 2000.0), "construction des points de reprise sur 2 000 ans de chaque côté");
    {   // Réserve sur disque : relue, elle donne exactement les mêmes positions ; refusée pour un autre `ansDirects`.
        const std::string res = "essai_reserve_systeme_solaire.bin";
        ok(ss.sauver(res), "réserve des points de reprise écrite");
        phys::SystemeSolaire r2, r3;
        const auto t0 = std::chrono::steady_clock::now();
        const bool lue = r2.chargerReserve(res, source, 2000.0);
        const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
        double d = 1e30; phys::Vec3 a, b, c2, d2; phys::Statut s1, s2;
        const double jd = phys::kDe440Fin + 1234.5 * 365.25;
        if (lue && ss.etat(phys::kMars, jd, a, b, s1) && r2.etat(phys::kMars, jd, c2, d2, s2)) d = std::hypot(a.x - c2.x, a.y - c2.y, a.z - c2.z);
        ok(lue && d == 0 && ms < 500, "réserve relue en %.0f ms : Mars identique (écart %.0f km)", ms, d);
        ok(!r3.chargerReserve(res, source, 20000.0), "réserve refusée quand la durée demandée diffère");
        std::remove(res.c_str());
    }
    for (int side = 0; side < 2; side++) {
        const phys::nb::State* s0 = ss.reprise(side == 1, 0);
        for (double yrs : {200.0, 400.0}) {
            phys::nb::Integrator it(*s0); const double jd = s0->jd + (side ? -1 : 1) * yrs * 365.25; it.advanceTo(jd);
            double b[42]; it.barycentric(b); double worst = 0;
            for (int i = 0; i < 8; i++) {
                phys::Vec3 p, v, ps, vs; source(i + 1, jd, p, v); source(10, jd, ps, vs);
                const double q[3] = {p.x - ps.x, p.y - ps.y, p.z - ps.z}, m[3] = {b[3 * (i + 1)] - b[0], b[3 * (i + 1) + 1] - b[1], b[3 * (i + 1) + 2] - b[2]};
                worst = std::fmax(worst, sepArcsec(m, q));
            }
            ok(worst < 10, side ? "parti de 2650, %.0f ans plus tôt : écart à DE440 %.2f″ au plus (planètes)" : "parti de 1550, %.0f ans plus tard : écart à DE440 %.2f″ au plus (planètes)", yrs, worst);
        }
    }

    // 3. Continuité à la borne et réponses inconnues.
    phys::Vec3 p, v; phys::Statut st;
    {      // à la borne même, le point de reprise est l'état DE440 (positions identiques) ; juste après, réponse « calculé »
        const phys::nb::State* s0 = ss.reprise(true, 0); phys::Vec3 a, w, s, sv; source(5, s0->jd, a, w); source(10, s0->jd, s, sv);
        const double d = std::sqrt(std::pow(s0->Q[12] * phys::kAuKm - (a.x - s.x), 2) + std::pow(s0->Q[13] * phys::kAuKm - (a.y - s.y), 2) + std::pow(s0->Q[14] * phys::kAuKm - (a.z - s.z), 2));
        ok(d < 1e-3, "continuité à la borne de 2650 : Jupiter à %.2g km de DE440", d);
        ok(ss.etat(phys::kJupiter, phys::kDe440Fin + 1, p, v, st) && st == phys::Statut::Calcule, "un jour après 2650 : Jupiter calculée, statut « calculé »");
    }
    ok(!ss.etat(phys::kMars, 2461354.5, p, v, st), "dans la plage DE440 : réponse « inconnu » (l'appli lit la NASA)");
    ok(!ss.etat(phys::kMars, phys::kDe440Fin + 3000 * 365.25, p, v, st), "au-delà du calcul direct, sans table : « inconnu »");
    if (argc > 2) {
        ok(ss.chargerTable(argv[2]), "table des orbites sur des millions d'années chargée");
        ok(ss.etat(phys::kMars, 2461354.5 + 1e6 * 365.25, p, v, st), "dans un million d'années : Mars calculée par la table");
        ok(!ss.etat(phys::kCeres, 2461354.5 + 1e6 * 365.25, p, v, st), "dans un million d'années : Cérès inconnue (absente de la table)");
        ok(!ss.etat(phys::kMars, 2461354.5 + 2e7 * 365.25, p, v, st), "dans 20 millions d'années : « inconnu » (chaos)");
    }

    // 3 bis. Suivi pas à pas (le temps qui défile) : mêmes positions que les requêtes isolées, et bien plus rapide.
    {
        phys::Suivi su(ss); double w = 0; const double j0 = phys::kDe440Fin + 900 * 365.25;
        const auto t0 = std::chrono::steady_clock::now();
        for (int k = 0; k < 400; k++) { const double jd = j0 + k * 3.0; phys::Vec3 a, b, c2, d2; phys::Statut s1, s2;
            if (su.aller(jd) && ss.etat(3, jd, c2, d2, s2) && su.etat(3, a, b, s1)) w = std::fmax(w, std::hypot(a.x - c2.x, a.y - c2.y, a.z - c2.z)); }
        const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
        ok(w < 1.0, "suivi pas à pas sur 400 dates (3 jours d'écart) : même Terre-Lune qu'une requête isolée à %.3f km près (%.0f ms en tout, requêtes isolées comprises)", w, ms);
        phys::Suivi s3(ss); const auto t1 = std::chrono::steady_clock::now(); for (int k = 0; k < 400; k++) s3.aller(j0 + 4000 + k * 3.0);
        const double ms2 = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t1).count();
        ok(ms2 < 200, "suivi seul : 400 dates en %.1f ms", ms2);
        // Temps rapide (bogue signalé par le fil appli PC) : de l'an 3000 à 5000 par pas de 167 ans, puis retour, puis 1,7 an.
        for (const double pasAns : {166.67, -166.67, 1.7, 47.3, 3000.0}) {
            phys::Suivi s4(ss); int rates = 0, faux = 0; double pire = 0;
            const double debut = pasAns > 0 ? 2461406.5 + (3000 - 2026) * 365.25 : 2461406.5 + (5000 - 2026) * 365.25;
            for (int k = 0; k < 600; k++) {
                const double jd = debut + k * pasAns * 365.25; if (jd > phys::kDe440Fin + 19990 * 365.25 || jd < phys::kDe440Fin) break;
                phys::Vec3 a, b, c2, d2; phys::Statut s1, s2;
                const bool attendu = ss.etat(phys::kMars, jd, c2, d2, s2);
                const bool eu = s4.aller(jd) && s4.etat(phys::kMars, a, b, s1);
                if (attendu && !eu) rates++;
                if (attendu && eu) { const double e = std::hypot(a.x - c2.x, a.y - c2.y, a.z - c2.z); pire = std::fmax(pire, e); if (e > 1.0) faux++; }
            }
            ok(rates == 0 && faux == 0, "suivi par pas de %.1f ans : %.0f dates sans position, écart maximal %.3f km", pasAns, rates, pire);
        }
    }

    // 4. Plusieurs fils d'exécution : mêmes réponses.
    {
        const double jd = phys::kDe440Fin + 777.7 * 365.25; phys::Vec3 ref, rv; ss.etat(phys::kVenus, jd, ref, rv, st);
        std::vector<std::thread> th; std::vector<double> d(4, 1e30);
        for (int k = 0; k < 4; k++) th.emplace_back([&, k] { phys::Vec3 q, w; phys::Statut s2; for (int r = 0; r < 20; r++) if (ss.etat(phys::kVenus, jd, q, w, s2)) d[k] = std::hypot(q.x - ref.x, q.y - ref.y, q.z - ref.z); });
        for (auto& t : th) t.join();
        double m = 0;
        for (double x : d) m = std::fmax(m, x);
        ok(m == 0, "quatre fils d'exécution : mêmes positions (écart %.3g km)", m);
    }
    std::printf(g_fail ? "ECHEC (%d)\n" : "PASSE\n", g_fail);
    return g_fail ? 1 : 0;
}
