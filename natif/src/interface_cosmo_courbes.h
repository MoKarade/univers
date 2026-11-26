// Appli PC « Univers » : histoire de l'expansion pour le panneau et la frise, recalculée avec les réglages en cours.
//
// Mêmes équations que cosmologie.h (Friedmann ; énergie noire w(a) = w0 + wa (1 - a)) :
//   passé : t(a) = intégrale de 0 à a de da' / (a' H(a')), sur une grille en ln a (règle des trapèzes, 6 000 points de
//           a = 1e-12 à 1) ; c'est la même intégrale que cosmo::ageGyr ;
//   avenir : da/dt = a H(a) par Runge-Kutta d'ordre 4 au pas de 10 millions d'années, jusqu'à +60 milliards d'années, ou
//           jusqu'à ce que l'univers retombe sur lui-même (a qui redescend sous 1e-3) ou se déchire (a au-delà de 1e6).
// Tout ce qui sort d'ici est « calculé » : jamais une mesure.
#pragma once
#include <algorithm>
#include <cmath>
#include <vector>

#include "cosmologie.h"

namespace univers {

struct CosmoHistory {
    cosmo::Params p;
    bool valid = false;
    double ageGa = 0;                       // âge aujourd'hui
    std::vector<double> lnA, tPast;         // passé : ln a et temps depuis le Big Bang (Ga)
    std::vector<double> tFuture, aFuture;   // avenir : temps depuis aujourd'hui (Ga) et a
    double endGa = -1;                      // fin de l'univers depuis aujourd'hui (Ga), -1 si aucune avant +60 Ga
    bool crunch = false, rip = false;

    static bool same(const cosmo::Params& a, const cosmo::Params& b) {
        return a.h0 == b.h0 && a.om == b.om && a.ode == b.ode && a.w0 == b.w0 && a.wa == b.wa;
    }

    void update(const cosmo::Params& np) {
        if (valid && same(np, p)) return;
        p = np;
        valid = true;
        const double hGa = p.h0 / 977.7922216807891;      // H0 en 1/Ga
        auto H = [&](double a) { return hGa * p.e(1.0 / a - 1.0); };
        // Passé : grille en ln a.
        constexpr int n = 6000;
        const double l0 = std::log(1e-12);
        lnA.assign(n + 1, 0);
        tPast.assign(n + 1, 0);
        double t = 0, prev = 0;
        for (int i = 0; i <= n; ++i) {
            const double la = l0 * (1.0 - static_cast<double>(i) / n), a = std::exp(la);
            const double f = 1.0 / H(a);      // dt/d(ln a)
            if (i == 0) t = f * 0.5;      // de a = 0 à 1e-12 : univers de rayonnement, t = 1 / (2H)
            else t += 0.5 * (f + prev) * (la - lnA[i - 1]);
            lnA[i] = la;
            tPast[i] = t;
            prev = f;
        }
        ageGa = tPast.back();
        // Avenir.
        tFuture.clear();
        aFuture.clear();
        crunch = rip = false;
        endGa = -1;
        double a = 1.0;
        const double dt = 0.01;
        auto fa = [&](double x) { return x * H(x); };
        bool falling = false;
        for (int i = 0; i <= 6000; ++i) {
            tFuture.push_back(i * dt);
            aFuture.push_back(a);
            // Univers qui retombe : la vitesse d'expansion s'annule puis change de signe. H(a) est toujours positive dans
            // cette formule (racine carrée) : le retournement se voit quand E² devient nul ; on le cherche à part.
            const double x = 1.0 / a - 1.0, ap = 1.0 / (1.0 + x);
            const double de = p.ode * std::pow(ap, -3.0 * (1.0 + p.w0 + p.wa)) * std::exp(-3.0 * p.wa * (1.0 - ap));
            const double e2 = p.omegaR() * std::pow(1 + x, 4) + p.om * std::pow(1 + x, 3) + p.omegaK() * (1 + x) * (1 + x) + de;
            if (e2 <= 1e-8) falling = true;      /* vitesse d'expansion presque nulle : retournement */
            if (falling) {
                // Après le retournement : symétrie du temps (a(t_max + s) = a(t_max - s)), suffisante pour dire la date de la fin.
                const double tMax = i * dt;
                const double untilEnd = tMax + (tMax + ageGa);
                crunch = true;
                endGa = untilEnd;
                const int back = static_cast<int>(tFuture.size()) - 1;
                for (int k = back - 1; k >= 0 && tFuture.size() < 12000; --k) {
                    tFuture.push_back(tMax + (tMax - tFuture[static_cast<size_t>(k)]));
                    aFuture.push_back(aFuture[static_cast<size_t>(k)]);
                }
                break;
            }
            const double k1 = fa(a), k2 = fa(a + 0.5 * dt * k1), k3 = fa(a + 0.5 * dt * k2), k4 = fa(a + dt * k3);
            a += dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4);
            if (!std::isfinite(a) || a > 1e6) {
                rip = true;
                endGa = (i + 1) * dt;
                break;
            }
        }
    }

    // Facteur d'échelle à `ga` milliards d'années depuis le Big Bang ; -1 si hors du calcul.
    double aAtSinceBigBang(double ga) const {
        if (ga <= 0) return -1;
        if (ga <= ageGa) {
            const auto it = std::lower_bound(tPast.begin(), tPast.end(), ga);
            if (it == tPast.begin()) return std::exp(lnA.front());
            if (it == tPast.end()) return 1.0;
            const size_t i = static_cast<size_t>(it - tPast.begin());
            const double u = (ga - tPast[i - 1]) / (tPast[i] - tPast[i - 1]);
            return std::exp(lnA[i - 1] + u * (lnA[i] - lnA[i - 1]));
        }
        const double f = ga - ageGa;
        if (tFuture.empty() || f > tFuture.back()) return -1;
        const size_t i = std::min(static_cast<size_t>(f / 0.01), aFuture.size() - 2);
        const double u = (f - tFuture[i]) / (tFuture[i + 1] - tFuture[i]);
        return aFuture[i] + u * (aFuture[i + 1] - aFuture[i]);
    }

    // Accélération de l'expansion aujourd'hui : paramètre de décélération q0 = Ωr + Ωm / 2 + ΩΛ (1 + 3 w0) / 2.
    double q0() const { return p.omegaR() + 0.5 * p.om + 0.5 * p.ode * (1.0 + 3.0 * p.w0); }
};

}  // namespace univers