// Champ de gravité d'une galaxie en coefficients : lecteur et évaluateur du format écrit par
// pipeline/champ/champ_bfe.py (sauver_bin). Étape 8 du plan B+ (docs/refonte-simulations-pro.md § 4.2).
//
// Même calcul que champ_bfe.evaluer en Python, terme à terme : multipôles (harmoniques sphériques réelles normalisées,
// Hermite cubique en ln r, prolongements r^l au centre et r^-(l+1) au-delà) pour le halo et le bulbe ; harmoniques
// azimutales sur grille (R, z), Hermite bicubique, pour le disque dans sa boîte, et multipôles du disque hors de la boîte.
// Le contrôle de l'égalité avec Python est fait par essais/essai_champ_bfe.cpp.
//
// Unités : kpc, km/s ; potentiel en (km/s)², force par unité de masse en (km/s)²/kpc. Repère : celui des positions
// données à champ_bfe.coefficients (centre de la galaxie à l'origine).
//
// Autonome (en-tête seul, sans dépendance) ; branché nulle part pour l'instant : le fil qui possède orbites_pas.comp
// décidera comment le passer à la carte graphique.
#pragma once

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace phys::champ {

struct Multipole {
    int lmax = 0;
    std::vector<double> r;       // nœuds
    std::vector<float> phi, dphi;  // [nœud][harmonique]
    int nh() const { return (lmax + 1) * (lmax + 1); }
};

struct Cylindre {
    int mmax = 0;
    std::vector<double> R, z;
    std::vector<float> tab;      // [harmonique][4 : F, dF/dR, dF/dz, d²F/dRdz][R][z]
};

namespace detail {

inline void hermite(double t, double h[8]) {
    const double t2 = t * t, t3 = t2 * t;
    h[0] = 2 * t3 - 3 * t2 + 1; h[1] = t3 - 2 * t2 + t; h[2] = -2 * t3 + 3 * t2; h[3] = t3 - t2;
    h[4] = 6 * t2 - 6 * t; h[5] = 3 * t2 - 4 * t + 1; h[6] = -6 * t2 + 6 * t; h[7] = 3 * t2 - 2 * t;
}

// premier indice i tel que v[i] <= x < v[i+1], borné à [0, n-2]
inline int intervalle(const std::vector<double>& v, double x) {
    int lo = 0, hi = static_cast<int>(v.size()) - 1;
    if (x <= v[0]) return 0;
    if (x >= v[hi]) return hi - 1;
    while (hi - lo > 1) {
        const int mid = (lo + hi) / 2;
        if (v[mid] <= x) lo = mid; else hi = mid;
    }
    return lo;
}

// Évalue un développement multipolaire en p (repère local). Ajoute à phi et g (gradient, pas la force).
inline void evalMultipole(const Multipole& M, const double p[3], double& phi, double g[3]) {
    const int L = M.lmax, nh = M.nh();
    double r = std::sqrt(p[0] * p[0] + p[1] * p[1] + p[2] * p[2]);
    const double rs = r > 1e-30 ? r : 1e-30;
    const double ct = std::fmax(-1.0, std::fmin(1.0, p[2] / rs));
    const double st = std::sqrt(std::fmax(0.0, 1 - ct * ct));
    const double ph = std::atan2(p[1], p[0]);
    r = r > 1e-9 ? r : 1e-9;
    // P̄_lm et sinθ dP̄_lm/dθ
    std::vector<double> P((L + 1) * (L + 1), 0.0), D((L + 1) * (L + 1), 0.0);
    auto at = [L](int l, int m) { return l * (L + 1) + m; };
    P[at(0, 0)] = 1 / std::sqrt(4 * M_PI);
    for (int m = 0; m <= L; ++m) {
        if (m > 0) P[at(m, m)] = std::sqrt((2.0 * m + 1) / (2.0 * m)) * st * P[at(m - 1, m - 1)];
        if (m + 1 <= L) P[at(m + 1, m)] = std::sqrt(2.0 * m + 3) * ct * P[at(m, m)];
        for (int l = m + 2; l <= L; ++l) {
            const double a = std::sqrt((4.0 * l * l - 1) / (double(l) * l - double(m) * m));
            const double b = std::sqrt((double(l - 1) * (l - 1) - double(m) * m) / (4.0 * (l - 1) * (l - 1) - 1));
            P[at(l, m)] = a * (ct * P[at(l - 1, m)] - b * P[at(l - 2, m)]);
        }
    }
    for (int l = 0; l <= L; ++l)
        for (int m = 0; m <= l; ++m) {
            double d = l * ct * P[at(l, m)];
            if (l > m) d -= std::sqrt((2.0 * l + 1) / (2.0 * l - 1) * (double(l) * l - double(m) * m)) * P[at(l - 1, m)];
            D[at(l, m)] = d;
        }
    // partie radiale
    const auto& rg = M.r;
    const int nr = static_cast<int>(rg.size());
    const bool dedans = r < rg[0], dehors = r > rg[nr - 1];
    int i = 0;
    double hc[8] = {0}, hs = 1, t = 0;
    if (!dedans && !dehors) {
        const double lr = std::log(r);
        i = intervalle(rg, r);
        const double l0 = std::log(rg[i]), l1 = std::log(rg[i + 1]);
        hs = l1 - l0;
        t = (lr - l0) / hs;
        hermite(t, hc);
    }
    double dr = 0, dth = 0, dph = 0;
    const double r2 = std::sqrt(2.0);
    for (int l = 0; l <= L; ++l) {
        for (int k = 0; k < 2 * l + 1; ++k) {
            const int h = l * l + k;
            double F, dF;
            if (dedans) {
                const double q = r / rg[0], f0 = M.phi[h], d0 = M.dphi[h];
                if (l == 0) { F = f0 + d0 * rg[0] * (q * q - 1) / 2; dF = d0 * q; }
                else { F = f0 * std::pow(q, l); dF = f0 * l * std::pow(q, l - 1) / rg[0]; }
            } else if (dehors) {
                const double q = rg[nr - 1] / r, f1 = M.phi[size_t(nr - 1) * nh + h];
                F = f1 * std::pow(q, l + 1);
                dF = -(l + 1) * f1 * std::pow(q, l + 2) / rg[nr - 1];
            } else {
                const double f0 = M.phi[size_t(i) * nh + h], f1 = M.phi[size_t(i + 1) * nh + h];
                const double g0 = M.dphi[size_t(i) * nh + h] * rg[i], g1 = M.dphi[size_t(i + 1) * nh + h] * rg[i + 1];
                F = hc[0] * f0 + hc[1] * hs * g0 + hc[2] * f1 + hc[3] * hs * g1;
                dF = (hc[4] * f0 + hc[5] * hs * g0 + hc[6] * f1 + hc[7] * hs * g1) / hs / r;
            }
            double Y, Yt, Yp;
            if (k == 0) { Y = P[at(l, 0)]; Yt = D[at(l, 0)]; Yp = 0; }
            else {
                const int m = (k + 1) / 2;
                const double c = std::cos(m * ph), s = std::sin(m * ph);
                if (k % 2) { Y = r2 * P[at(l, m)] * c; Yt = r2 * D[at(l, m)] * c; Yp = -m * r2 * P[at(l, m)] * s; }
                else { Y = r2 * P[at(l, m)] * s; Yt = r2 * D[at(l, m)] * s; Yp = m * r2 * P[at(l, m)] * c; }
            }
            phi += F * Y; dr += dF * Y; dth += F * Yt; dph += F * Yp;
        }
    }
    const double stc = st > 1e-9 ? st : 1e-9;
    dth /= stc * r; dph /= stc * r;
    const double cp = std::cos(ph), sp = std::sin(ph);
    g[0] += dr * st * cp + dth * ct * cp - dph * sp;
    g[1] += dr * st * sp + dth * ct * sp + dph * cp;
    g[2] += dr * ct - dth * st;
}

inline bool dansBoite(const Cylindre& C, const double p[3]) {
    return std::hypot(p[0], p[1]) < C.R.back() && std::fabs(p[2]) < C.z.back();
}

inline void evalCylindre(const Cylindre& C, const double p[3], double& phi, double g[3]) {
    const double R = std::hypot(p[0], p[1]), z = p[2], ph = std::atan2(p[1], p[0]);
    const int NR = static_cast<int>(C.R.size()), NZ = static_cast<int>(C.z.size());
    const int i = intervalle(C.R, R), k = intervalle(C.z, z);
    const double hR = C.R[i + 1] - C.R[i], hz = C.z[k + 1] - C.z[k];
    double a[8], b[8];
    hermite((R - C.R[i]) / hR, a);
    hermite((z - C.z[k]) / hz, b);
    const double Ha[4] = {a[0], a[1] * hR, a[2], a[3] * hR}, dHa[4] = {a[4] / hR, a[5], a[6] / hR, a[7]};
    const double Hb[4] = {b[0], b[1] * hz, b[2], b[3] * hz}, dHb[4] = {b[4] / hz, b[5], b[6] / hz, b[7]};
    const size_t plan = size_t(NR) * NZ;
    double P = 0, dR = 0, dz = 0, dph = 0;
    for (int h = 0; h < 2 * C.mmax + 1; ++h) {
        const float* T = C.tab.data() + size_t(h) * 4 * plan;
        auto f = [&](int di, int dk, int c) { return double(T[c * plan + size_t(i + di) * NZ + (k + dk)]); };
        auto interp = [&](const double* A, const double* B) {
            return A[0] * B[0] * f(0, 0, 0) + A[1] * B[0] * f(0, 0, 1) + A[0] * B[1] * f(0, 0, 2) + A[1] * B[1] * f(0, 0, 3)
                 + A[2] * B[0] * f(1, 0, 0) + A[3] * B[0] * f(1, 0, 1) + A[2] * B[1] * f(1, 0, 2) + A[3] * B[1] * f(1, 0, 3)
                 + A[0] * B[2] * f(0, 1, 0) + A[1] * B[2] * f(0, 1, 1) + A[0] * B[3] * f(0, 1, 2) + A[1] * B[3] * f(0, 1, 3)
                 + A[2] * B[2] * f(1, 1, 0) + A[3] * B[2] * f(1, 1, 1) + A[2] * B[3] * f(1, 1, 2) + A[3] * B[3] * f(1, 1, 3);
        };
        const double v = interp(Ha, Hb), vR = interp(dHa, Hb), vz = interp(Ha, dHb);
        double ang = 1, dang = 0;
        if (h > 0) {
            const int m = (h + 1) / 2;
            if (h % 2) { ang = std::cos(m * ph); dang = -m * std::sin(m * ph); }
            else { ang = std::sin(m * ph); dang = m * std::cos(m * ph); }
        }
        P += v * ang; dR += vR * ang; dz += vz * ang; dph += v * dang;
    }
    const double Rs = R > 1e-9 ? R : 1e-9, cp = std::cos(ph), sp = std::sin(ph);
    phi += P;
    g[0] += dR * cp - dph / Rs * sp;
    g[1] += dR * sp + dph / Rs * cp;
    g[2] += dz;
}

}  // namespace detail

struct Champ {
    double masse = 0;
    double rot[9] = {1, 0, 0, 0, 1, 0, 0, 0, 1};   // lignes : axes du repère du disque dans le repère des positions
    Multipole mult, multDisque;
    Cylindre cyl;
    bool aDisque = false;

    bool charger(const std::string& chemin, std::string& err) {
        FILE* fh = std::fopen(chemin.c_str(), "rb");
        if (!fh) { err = "ouverture impossible : " + chemin; return false; }
        bool ok = true;
        auto lire = [&](void* d, size_t n) { if (ok && std::fread(d, 1, n, fh) != n) ok = false; };
        auto i32 = [&]() { int32_t v = 0; lire(&v, 4); return int(v); };
        auto lireMult = [&](Multipole& M) {
            M.lmax = i32();
            const int nr = i32();
            if (!ok || M.lmax < 0 || M.lmax > 64 || nr < 2 || nr > 100000) { ok = false; return; }
            M.r.resize(nr); lire(M.r.data(), 8 * size_t(nr));
            M.phi.resize(size_t(nr) * M.nh()); lire(M.phi.data(), 4 * M.phi.size());
            M.dphi.resize(size_t(nr) * M.nh()); lire(M.dphi.data(), 4 * M.dphi.size());
        };
        char magic[4] = {0};
        lire(magic, 4);
        if (ok && std::memcmp(magic, "CHMP", 4) != 0) { std::fclose(fh); err = "pas un fichier de champ"; return false; }
        const int version = i32();
        if (ok && version != 1) { std::fclose(fh); err = "version de champ inconnue"; return false; }
        lire(&masse, 8);
        lire(rot, 72);
        lireMult(mult);
        aDisque = i32() != 0;
        if (ok && aDisque) {
            cyl.mmax = i32();
            const int NR = i32(), NZ = i32();
            if (!ok || cyl.mmax < 0 || cyl.mmax > 64 || NR < 2 || NZ < 2 || NR > 10000 || NZ > 10000) ok = false;
            if (ok) {
                cyl.R.resize(NR); lire(cyl.R.data(), 8 * size_t(NR));
                cyl.z.resize(NZ); lire(cyl.z.data(), 8 * size_t(NZ));
                cyl.tab.resize(size_t(2 * cyl.mmax + 1) * 4 * NR * NZ); lire(cyl.tab.data(), 4 * cyl.tab.size());
                lireMult(multDisque);
            }
        }
        std::fclose(fh);
        if (!ok) err = "fichier de champ tronqué ou abîmé : " + chemin;
        return ok;
    }

    // Potentiel et force (par unité de masse) au point x, dans le repère des positions.
    void evaluer(const double x[3], double& phi, double F[3]) const {
        double p[3];
        for (int a = 0; a < 3; ++a) p[a] = rot[3 * a] * x[0] + rot[3 * a + 1] * x[1] + rot[3 * a + 2] * x[2];
        double g[3] = {0, 0, 0};
        phi = 0;
        detail::evalMultipole(mult, p, phi, g);
        if (aDisque) {
            if (detail::dansBoite(cyl, p)) detail::evalCylindre(cyl, p, phi, g);
            else detail::evalMultipole(multDisque, p, phi, g);
        }
        for (int a = 0; a < 3; ++a) F[a] = -(rot[a] * g[0] + rot[3 + a] * g[1] + rot[6 + a] * g[2]);
    }
};

}  // namespace phys::champ
