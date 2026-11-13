// Contrôle de galaxie_orbites.h (orbites des étoiles dans la Voie lactée, barre comprise).
// 1. Même résultat que la page (app/src/26_orbits.js) : Soleil à +200 Ma, avec et sans barre (valeurs de la page, Node).
// 2. Intégrale de Jacobi conservée (repère de la barre), tour du Soleil 220 à 240 Ma, aller-retour réversible.
// 3. Plusieurs fils : mêmes positions qu'un seul ; durée pour 100 000 étoiles sur 100 Ma.
// Imprime PASSE ou ECHEC par ligne ; code de sortie 0 si tout passe.
#include <chrono>
#include <cmath>
#include <cstdio>
#include <random>
#include <vector>

#include "galaxie_orbites.h"

using namespace phys::galaxie;
static int g_fail = 0;
static void ok(bool c, const char* fmt, double a = 0, double b = 0, double d = 0) { std::printf("%s ", c ? "PASSE" : "ECHEC"); std::printf(fmt, a, b, d); std::printf("\n"); if (!c) g_fail++; }

int main() {
    const phys::Vec3 sp[1] = {soleilPos()}, sv[1] = {soleilVit()};
    {
        Orbites o(sp, sv); o.avance(0.2); const auto p = o.position(0);
        const double d = std::sqrt(std::pow(p.x + 5.078895720, 2) + std::pow(p.y + 6.208048454, 2) + std::pow(p.z - 0.085053558, 2));
        /* La page web n'a pas l'énergie noire ; ici elle y est (2e-6 de l'attraction au Soleil) : 0,24 pc d'écart attendu à 200 Ma. */
        ok(d < 5e-4, "Soleil à +200 Ma : écart à la page %.2g kpc (énergie noire en plus ici)", d);
        Potentiel P; P.barre = false; Orbites q(sp, sv, P); q.avance(0.2); const auto r = q.position(0);
        const double e = std::sqrt(std::pow(r.x + 5.710272466, 2) + std::pow(r.y + 5.915890796, 2) + std::pow(r.z - 0.095103441, 2));
        ok(e < 5e-4, "Soleil à +200 Ma sans barre : écart à la page %.2g kpc (énergie noire en plus ici)", e);
    }
    {      // tour du Soleil autour du centre
        Orbites o(sp, sv); double turn = 0, a0 = std::atan2(sp[0].y, sp[0].x), tTurn = 0;
        for (int s = 1; s <= 400 && tTurn == 0; s++) { o.avance(s * kDtGa, 1); const auto p = o.position(0); double a = std::atan2(p.y, p.x), d = a - a0; if (d > kPi) d -= 2 * kPi; if (d < -kPi) d += 2 * kPi; turn += d; a0 = a; if (std::fabs(turn) >= 2 * kPi) tTurn = s; }
        ok(tTurn >= 220 && tTurn <= 240, "Soleil : un tour du centre en %.0f Ma", tTurn);
    }
    {      // Jacobi : E + Φ_barre + Ω_b L_z constant (la barre tourne dans le sens du disque)
        const phys::Vec3 p0[1] = {{-4.5, 0.3, 0.05}}, v0[1] = {{20, 180, 5}}; Orbites o(p0, v0); const auto& P = o.potentiel();
        auto J = [&] { const auto p = o.position(0), v = o.vitesse(0); return P.energie(p.x, p.y, p.z, v.x, v.y, v.z) + P.phiBarre(p.x, p.y, o.temps()) + kBarOmegaKmsKpc * (p.x * v.y - p.y * v.x); };
        const double j0 = J(); double w = 0; for (int s = 1; s <= 500; s++) { o.avance(s * kDtGa, 1); w = std::fmax(w, std::fabs(J() / j0 - 1)); }
        ok(w < 2e-3, "intégrale de Jacobi conservée à %.1e près sur 500 Ma", w);
    }
    {      // 100 000 étoiles du disque : plusieurs fils = un fil ; aller-retour
        std::mt19937_64 g(20261112); std::uniform_real_distribution<double> U(0, 1); std::vector<phys::Vec3> p(100000), v(100000);
        for (size_t k = 0; k < p.size(); k++) { const double R = 2 + 13 * U(g), f = 2 * kPi * U(g), vc = std::sqrt(v2Baryons(R) + gmHalo() * nfwShape(R));
            p[k] = {R * std::cos(f), R * std::sin(f), 0.3 * (U(g) - 0.5)}; v[k] = {vc * std::sin(f) + 20 * (U(g) - 0.5), -vc * std::cos(f) + 20 * (U(g) - 0.5), 10 * (U(g) - 0.5)}; }
        Orbites a(p, v), b(p, v); const auto t0 = std::chrono::steady_clock::now(); a.avance(0.1); const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
        b.avance(0.1, 1); double d = 0; for (size_t k = 0; k < p.size(); k += 97) { const auto x = a.position(k), y = b.position(k); d = std::fmax(d, std::hypot(x.x - y.x, x.y - y.y, x.z - y.z)); }
        ok(d == 0, "plusieurs fils d'exécution : mêmes positions qu'un seul (écart %.2g kpc)", d);
        ok(ms < 60000, "100 000 étoiles sur 100 Ma : %.0f ms", ms);
        a.avance(0); double back = 0; for (size_t k = 0; k < p.size(); k += 97) { const auto x = a.position(k); back = std::fmax(back, std::hypot(x.x - p[k].x, x.y - p[k].y, x.z - p[k].z)); }
        ok(back < 1e-6, "aller 100 Ma puis retour : écart %.2g kpc", back);
    }
    {   // Fréquences analytiques contre différences finies de Potentiel::acc (sans barre), de 0,5 à 30 kpc.
        Potentiel P; P.barre = false; double worst = 0;
        auto aR = [&](double R) { double a[3]; P.acc(R, 0, 0, 0, a); return -a[0]; };      // Φ'(R)
        auto az = [&](double R, double z) { double a[3]; P.acc(R, 0, z, 0, a); return -a[2]; };
        for (double R = 0.5; R <= 30; R *= 1.15) {
            const auto f = frequences(R); const double h = 1e-4 * R, hz = 1e-5;
            const double vc = std::sqrt(R * aR(R)), om2 = aR(R) / R, k2 = (aR(R + h) - aR(R - h)) / (2 * h) + 3 * om2, n2 = (az(R, hz) - az(R, -hz)) / (2 * hz);
            worst = std::fmax(worst, std::fmax(std::fmax(std::fabs(f.vc / vc - 1), std::fabs(f.omega / std::sqrt(om2) - 1)), std::fmax(std::fabs(f.kappa / std::sqrt(k2) - 1), std::fabs(f.nu / std::sqrt(n2) - 1))));
        }
        ok(worst < 1e-5, "fréquences (vc, Ω, κ, ν) : écart relatif %.1e aux dérivées de acc", worst);
        const auto s = frequences(kR0);
        /* halo calé sur 230 km/s sans l'énergie noire, qui en retire 0,0003 km/s au Soleil */ ok(std::fabs(s.vc - kV0) < 1e-3, "au Soleil : vc %.3f km/s, κ %.2f, ν %.1f km/s/kpc", s.vc, s.kappa, s.nu);
    }
    std::printf(g_fail ? "ECHEC (%d)\n" : "PASSE\n", g_fail);
    return g_fail ? 1 : 0;
}
