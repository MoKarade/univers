// Horizon du chaos du système solaire, MESURÉ avec notre calcul à N corps (nbody_noyau.h) : clones écartés de quelques
// mètres au départ, suivis sur des dizaines de millions d'années. Au-delà de l'instant où les clones divergent, la
// position (et l'excentricité) de la Terre ne se prédit plus, quelle que soit la puissance de calcul.
//
// Départ : état du 10/11/2026 (nbody_donnees.h, JPL Horizons). Clone 0 = départ exact ; clones 1..n−1 : position du
// barycentre Terre-Lune déplacée de `ecart` mètres dans une direction tirée au hasard (graine fixe). Laskar et al. 2011
// (La2010) utilisent 1e-10 UA ≈ 15 m, de l'ordre de la précision des éphémérides.
// Sortie binaire : en-tête « UNIVCHA1 », n clones (u32), m échantillons (u32), pas (f64, années), sens (i32), écart (f64,
// mètres) ; puis pour chaque échantillon et chaque clone 6 f64 : e et ϖ (rad) de la Terre-Lune, λ (rad, longitude
// héliocentrique) de la Terre-Lune, e de Mercure, e de Mars, inclinaison de la Terre-Lune (rad, écliptique J2000).
// Usage : chaos_systeme_solaire <+1|-1> <millions d'années> <clones> <écart en m> <sortie.bin> [pas en milliers d'années]
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <random>
#include <thread>
#include <vector>

#include "nbody_noyau.h"

namespace {
using phys::nb::State;
constexpr int kTerre = 2, kMercure = 0, kMars = 3;

void elements(const State& s, int i, double out[3]) {      // e, ϖ, i (osculateurs héliocentriques)
    const double mu = phys::nb::kGmSun + nbody_donnees::kGm[i];
    const double* r = &s.Q[3 * i];
    // vitesse héliocentrique = vitesse barycentrique − vitesse barycentrique du Soleil
    double ps[3] = {0, 0, 0};
    for (int k = 0; k < phys::nb::kN; k++) for (int c = 0; c < 3; c++) ps[c] += nbody_donnees::kGm[k] * s.V[3 * k + c];
    double v[3]; for (int c = 0; c < 3; c++) v[c] = s.V[3 * i + c] + ps[c] / phys::nb::kGmSun;
    const double h[3] = {r[1] * v[2] - r[2] * v[1], r[2] * v[0] - r[0] * v[2], r[0] * v[1] - r[1] * v[0]};
    const double rn = std::sqrt(r[0] * r[0] + r[1] * r[1] + r[2] * r[2]);
    double ev[3]; for (int c = 0; c < 3; c++) ev[c] = 0;
    ev[0] = (v[1] * h[2] - v[2] * h[1]) / mu - r[0] / rn; ev[1] = (v[2] * h[0] - v[0] * h[2]) / mu - r[1] / rn; ev[2] = (v[0] * h[1] - v[1] * h[0]) / mu - r[2] / rn;
    out[0] = std::sqrt(ev[0] * ev[0] + ev[1] * ev[1] + ev[2] * ev[2]);
    out[1] = std::atan2(ev[1], ev[0]);
    out[2] = std::atan2(std::hypot(h[0], h[1]), h[2]);
}
}  // namespace

int main(int argc, char** argv) {
    if (argc < 6) { std::printf("usage : chaos_systeme_solaire <+1|-1> <Ma> <clones> <écart m> <sortie.bin> [pas ka]\n"); return 2; }
    const int sens = std::atoi(argv[1]) < 0 ? -1 : 1;
    const double ma = std::atof(argv[2]), ecartM = std::atof(argv[4]), pasKa = argc > 6 ? std::atof(argv[6]) : 10.0;
    const int n = std::atoi(argv[3]);
    const long m = std::lround(ma * 1000 / pasKa) + 1;
    const double ecartUa = ecartM / 1000.0 / 149597870.7;
    std::vector<State> s(n, phys::nb::initialState());
    std::mt19937_64 g(20261112); std::normal_distribution<double> N(0, 1);
    for (int k = 1; k < n; k++) {
        double d[3] = {N(g), N(g), N(g)}; const double l = std::sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
        for (int c = 0; c < 3; c++) s[k].Q[3 * kTerre + c] += ecartUa * d[c] / l;
    }
    std::vector<double> sortie((size_t)m * n * 6);
    const double pasJours = sens * pasKa * 1000 * 365.25;
    const auto t0 = std::chrono::steady_clock::now();
    std::vector<std::thread> fils;
    for (int k = 0; k < n; k++) fils.emplace_back([&, k] {
        phys::nb::Integrator it(s[k]);
        for (long j = 0; j < m; j++) {
            if (j) it.advanceTo(s[k].jd + j * pasJours);
            const State& st = it.state(); double e[3], em[3], ea[3];
            elements(st, kTerre, e); elements(st, kMercure, em); elements(st, kMars, ea);
            double* o = &sortie[((size_t)j * n + k) * 6];
            o[0] = e[0]; o[1] = e[1]; o[2] = std::atan2(st.Q[3 * kTerre + 1], st.Q[3 * kTerre]); o[3] = em[0]; o[4] = ea[0]; o[5] = e[2];
            if (k == 0 && j % 100 == 0) {
                const double s_ = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
                std::printf("%.2f Ma  e Terre %.5f  (%.0f s)\n", j * pasKa / 1000, e[0], s_); std::fflush(stdout);
            }
        }
    });
    for (auto& f : fils) f.join();
    std::ofstream f(argv[5], std::ios::binary);
    f.write("UNIVCHA1", 8);
    const uint32_t nn = n, mm = m; const double pasAns = pasKa * 1000; const int32_t ss = sens;
    f.write((const char*)&nn, 4); f.write((const char*)&mm, 4); f.write((const char*)&pasAns, 8); f.write((const char*)&ss, 4); f.write((const char*)&ecartM, 8);
    f.write((const char*)sortie.data(), sortie.size() * sizeof(double));
    std::printf("fini : %d clones, %ld échantillons, %.0f s\n", n, m, std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
    return 0;
}
