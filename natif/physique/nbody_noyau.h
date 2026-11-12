// Appli PC « Univers », bibliothèque univers_physique : noyau du calcul à N corps du système solaire (interne).
// Port de app/src/21_nbody.js (page web, lot G), mêmes résultats.
//
// - Integrator : Soleil, 8 planètes (barycentres), Pluton, Cérès, Vesta, Pallas, Hygie s'attirent tous.
//   Wisdom et Holman (1991) en coordonnées héliocentriques démocratiques (Duncan, Levison et Lee 1998), pas de 4 jours ;
//   relativité générale du Soleil (premier ordre post-newtonien, Anderson et al. 1975), en deux demi-coups pour rester
//   réversible ; la Lune moyennée en anneau autour de la Terre (Quinn, Tremaine et Duncan 1991).
//   Départ : JPL Horizons (DE440) au 10/11/2026, vitesses calées sur DE440 de 1650 à 2450 (pipeline/gravite/ajuste.js) ;
//   données dans nbody_donnees.h (généré). Contrôle : essai_nbody.cpp (positions Horizons de 1650 à 2450).
// - LongTable : orbites sur ±10 millions d'années, table écrite par pipeline/gravite/build_long.js à partir du calcul
//   long (même modèle), contrôlée contre La2004 (Laskar et al. 2004) ; au-delà, la position est inconnue (chaos).
//
// Unités : UA, jour, GM en UA³/jour² ; repère écliptique J2000 ; temps TDB (jours juliens).
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>
#include "nbody_donnees.h"

namespace phys::nb {

constexpr double kGmSun = 2.9591220828411956e-4;
constexpr double kCAuDay = 173.1446326846693;
constexpr int kN = nbody_donnees::kN;
constexpr double kTwoPi = 6.283185307179586;

struct State {
    double jd = 0;
    std::array<double, 3 * kN> Q{}, V{};      // Q héliocentrique, V barycentrique (coordonnées démocratiques)
};

inline State initialState() {
    State s; s.jd = nbody_donnees::kJd0;
    for (int i = 0; i < 3 * kN; i++) { s.Q[i] = nbody_donnees::kQ[i]; s.V[i] = nbody_donnees::kV[i]; }
    return s;
}

// Mouvement de Kepler exact pendant dt (anomalie excentrique, orbites liées).
inline bool kepler(double* r, double* v, double mu, double dt) {
    const double x0 = r[0], y0 = r[1], z0 = r[2], vx = v[0], vy = v[1], vz = v[2];
    const double r0 = std::sqrt(x0 * x0 + y0 * y0 + z0 * z0), v2 = vx * vx + vy * vy + vz * vz, rv = x0 * vx + y0 * vy + z0 * vz;
    const double ia = 2 / r0 - v2 / mu; if (!(ia > 0)) return false;
    const double a = 1 / ia, sa = std::sqrt(a), n = std::sqrt(mu * ia * ia * ia), s0 = rv / std::sqrt(mu), c1 = 1 - r0 * ia, c2 = s0 / sa, M = n * dt;
    double X = M;
    for (int k = 0; k < 30; k++) { const double sx = std::sin(X), cx = std::cos(X), f = X - c1 * sx + c2 * (1 - cx) - M, fp = 1 - c1 * cx + c2 * sx, d = f / fp; X -= d; if (std::fabs(d) < 1e-14) break; }
    const double sx = std::sin(X), cx = std::cos(X), rr = a + (r0 - a) * cx + s0 * sa * sx;
    const double f = 1 - a / r0 * (1 - cx), g = dt + (sx - X) / n, fd = -std::sqrt(mu * a) * sx / (rr * r0), gd = 1 - a / rr * (1 - cx);
    r[0] = f * x0 + g * vx; r[1] = f * y0 + g * vy; r[2] = f * z0 + g * vz;
    v[0] = fd * x0 + gd * vx; v[1] = fd * y0 + gd * vy; v[2] = fd * z0 + gd * vz;
    return true;
}

class Integrator {
public:
    explicit Integrator(State s = initialState()) : s_(s) {}
    const State& state() const { return s_; }

    // Avance de n pas de dt jours (dt < 0 : vers le passé ; le schéma est réversible).
    void step(double dt, long n) {
        for (long k = 0; k < n; k++) {
            jump(dt / 2); kick(dt / 2);
            for (int i = 0; i < kN; i++) kepler(&s_.Q[3 * i], &s_.V[3 * i], kGmSun, dt);
            kick(dt / 2); jump(dt / 2);
        }
        s_.jd += dt * n;
    }
    // Avance jusqu'à jd (pas d'au plus dtMax jours, le dernier raccourci).
    void advanceTo(double jd, double dtMax = nbody_donnees::kDtDays) {
        const double span = jd - s_.jd; const long n = (long)std::ceil(std::fabs(span) / dtMax);
        if (n > 0) { step(span / n, n); s_.jd = jd; }
    }
    // Positions barycentriques (UA) : Soleil puis les kN corps (out : 3 × (kN + 1) doubles).
    void barycentric(double* out) const {
        double m = kGmSun, x = 0, y = 0, z = 0;
        for (int i = 0; i < kN; i++) { const double g = nbody_donnees::kGm[i]; m += g; x += g * s_.Q[3 * i]; y += g * s_.Q[3 * i + 1]; z += g * s_.Q[3 * i + 2]; }
        out[0] = -x / m; out[1] = -y / m; out[2] = -z / m;
        for (int i = 0; i < kN; i++) for (int c = 0; c < 3; c++) out[3 * (i + 1) + c] = s_.Q[3 * i + c] + out[c];
    }
    // Énergie newtonienne totale (contrôle).
    double energy() const {
        double px = 0, py = 0, pz = 0, E = 0;
        for (int i = 0; i < kN; i++) { const double g = nbody_donnees::kGm[i]; px += g * s_.V[3 * i]; py += g * s_.V[3 * i + 1]; pz += g * s_.V[3 * i + 2]; }
        E += (px * px + py * py + pz * pz) / (2 * kGmSun);
        for (int i = 0; i < kN; i++) {
            const double g = nbody_donnees::kGm[i], *q = &s_.Q[3 * i], *v = &s_.V[3 * i], r = std::hypot(q[0], q[1], q[2]);
            E += g * (0.5 * (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) - kGmSun / r);
            for (int j = i + 1; j < kN; j++) E -= g * nbody_donnees::kGm[j] / std::hypot(s_.Q[3 * j] - q[0], s_.Q[3 * j + 1] - q[1], s_.Q[3 * j + 2] - q[2]);
        }
        return E;
    }

private:
    State s_;

    void jump(double h) {      // déplacement dû au mouvement du Soleil
        double px = 0, py = 0, pz = 0;
        for (int i = 0; i < kN; i++) { const double g = nbody_donnees::kGm[i]; px += g * s_.V[3 * i]; py += g * s_.V[3 * i + 1]; pz += g * s_.V[3 * i + 2]; }
        const double k = h / kGmSun;
        for (int i = 0; i < kN; i++) { s_.Q[3 * i] += k * px; s_.Q[3 * i + 1] += k * py; s_.Q[3 * i + 2] += k * pz; }
    }
    void kick(double h) {      // attraction mutuelle (le Soleil est dans Kepler), relativité en deux moitiés, anneau Terre-Lune
        gr(h / 2);
        for (int i = 0; i < kN; i++) {
            const double xi = s_.Q[3 * i], yi = s_.Q[3 * i + 1], zi = s_.Q[3 * i + 2];
            for (int j = i + 1; j < kN; j++) {
                const double dx = s_.Q[3 * j] - xi, dy = s_.Q[3 * j + 1] - yi, dz = s_.Q[3 * j + 2] - zi, d2 = dx * dx + dy * dy + dz * dz, k = h / (d2 * std::sqrt(d2));
                const double ki = nbody_donnees::kGm[j] * k, kj = nbody_donnees::kGm[i] * k;
                s_.V[3 * i] += ki * dx; s_.V[3 * i + 1] += ki * dy; s_.V[3 * i + 2] += ki * dz;
                s_.V[3 * j] -= kj * dx; s_.V[3 * j + 1] -= kj * dy; s_.V[3 * j + 2] -= kj * dz;
            }
        }
        gr(h / 2);
        moonRing(h);
    }
    // Relativité : a = GM/(c² r³) [(4 GM/r − v²) r + 4 (r·v) v], v héliocentrique, point milieu (trois passes).
    void gr(double h) {
        double px = 0, py = 0, pz = 0;
        for (int i = 0; i < kN; i++) { const double g = nbody_donnees::kGm[i]; px += g * s_.V[3 * i]; py += g * s_.V[3 * i + 1]; pz += g * s_.V[3 * i + 2]; }
        const double sx = -px / kGmSun, sy = -py / kGmSun, sz = -pz / kGmSun, c2 = kCAuDay * kCAuDay, mu = kGmSun;
        for (int i = 0; i < kN; i++) {
            const double x = s_.Q[3 * i], y = s_.Q[3 * i + 1], z = s_.Q[3 * i + 2], r = std::sqrt(x * x + y * y + z * z);
            const double vx = s_.V[3 * i] - sx, vy = s_.V[3 * i + 1] - sy, vz = s_.V[3 * i + 2] - sz;
            double ax = 0, ay = 0, az = 0;
            for (int it = 0; it < 3; it++) {
                const double ux = vx + ax * h / 2, uy = vy + ay * h / 2, uz = vz + az * h / 2, v2 = ux * ux + uy * uy + uz * uz, rv = x * ux + y * uy + z * uz;
                const double k = mu / (c2 * r * r * r), a1 = 4 * mu / r - v2;
                ax = k * (a1 * x + 4 * rv * ux); ay = k * (a1 * y + 4 * rv * uy); az = k * (a1 * z + 4 * rv * uz);
            }
            s_.V[3 * i] += h * ax; s_.V[3 * i + 1] += h * ay; s_.V[3 * i + 2] += h * az;
        }
    }
    // Lune moyennée sur son orbite : anneau de masse réduite μ autour de la Terre ; U = G M☉ μ ρ² P2(r̂·n) / (2 r³), n = pôle de l'écliptique.
    void moonRing(double h) {
        constexpr int i = 2;      // barycentre Terre-Lune
        constexpr double aM = 384400.0 / 149597870.7, rho2 = aM * aM * (1 + 1.5 * 0.0549 * 0.0549);
        constexpr double mu = 8.8876924467071033e-10 * 1.0931894624024351e-11 / (8.9970116036316091e-10 * 8.9970116036316091e-10);
        const double x = s_.Q[3 * i], y = s_.Q[3 * i + 1], z = s_.Q[3 * i + 2], r2 = x * x + y * y + z * z, r = std::sqrt(r2), r5 = r2 * r2 * r, r7 = r5 * r2;
        const double k = -h * kGmSun * mu * rho2 / 4, z2 = z * z;
        s_.V[3 * i] += k * x * (3 / r5 - 15 * z2 / r7); s_.V[3 * i + 1] += k * y * (3 / r5 - 15 * z2 / r7); s_.V[3 * i + 2] += k * z * (9 / r5 - 15 * z2 / r7);
    }
};

// Orbites sur des millions d'années : table de build_long.js (version 2). λ tous les 1 000 ans (Jupiter et Saturne tous
// les 250 ans), a, e, i, Ω, ϖ tous les 10 000 ans ; entre deux dates, λ avance au mouvement moyen réel.
class LongTable {
public:
    bool load(const std::string& path) {
        FILE* f = std::fopen(path.c_str(), "rb"); if (!f) return false;
        std::fseek(f, 0, SEEK_END); const long size = std::ftell(f); std::fseek(f, 0, SEEK_SET);
        std::vector<uint8_t> b(size); const bool ok = std::fread(b.data(), 1, size, f) == (size_t)size; std::fclose(f); if (!ok || size < 56) return false;
        double h[7]; std::memcpy(h, b.data(), 56);
        jd0_ = h[1]; dd_ = h[2]; nP_ = (long)h[3]; nF_ = (long)h[4]; nk_ = (int)h[5]; sl_ = (int)h[6]; n_ = nP_ + nF_ + 1;
        const long nS = (n_ - 1) / sl_ + 1;
        lam_.resize(n_ * nk_); slow_.resize(nS * nk_ * 5); lq_.resize(h[0] >= 2 ? (n_ - 1) * 6 : 0);
        size_t o = 56; auto rd = [&](std::vector<float>& v) { std::memcpy(v.data(), b.data() + o, v.size() * 4); o += v.size() * 4; };
        rd(lam_); rd(slow_); if (!lq_.empty()) rd(lq_);
        return o <= b.size();
    }
    bool loaded() const { return n_ > 0; }
    // Années (depuis le départ) couvertes : [début, fin].
    double firstYear() const { return -nP_ * dd_ / 365.25; }
    double lastYear() const { return nF_ * dd_ / 365.25; }
    // Position héliocentrique (UA, écliptique J2000) du corps b (0 Mercure … 7 Neptune, 8 Pluton ; 2 = barycentre Terre-Lune)
    // à jd (TDB). false hors de la table.
    bool position(int b, double jd, double out[3]) const {
        if (b < 0 || b >= nk_) return false;
        const double x = (jd - jd0_) / dd_ + nP_; if (!(x >= 0 && x <= n_ - 1)) return false;
        const long k = std::min((long)std::floor(x), n_ - 2); const double f = x - k;
        const long nS = (long)slow_.size() / (nk_ * 5); const double xs = x / sl_; const long ks = std::min((long)std::floor(xs), nS - 2); const double fs = std::max(0.0, xs - ks);
        const bool has1 = ks + 1 < nS; const float* s0 = &slow_[(ks * nk_ + b) * 5]; const float* s1 = has1 ? &slow_[((ks + 1) * nk_ + b) * 5] : s0;
        auto lin = [&](int q) { return s0[q] + (s1[q] - s0[q]) * fs; };
        auto ang = [&](int q) { const double d = std::atan2(std::sin(s1[q] - s0[q]), std::cos(s1[q] - s0[q])); return s0[q] + d * fs; };
        const double a = lin(0), e = lin(1), I = lin(2), O = ang(3), om = ang(4), turn = 0.01720209895 / std::pow(a, 1.5) * dd_;
        double lam;
        const int jb = b == 4 ? 0 : b == 5 ? 1 : -1;
        if (jb >= 0 && !lq_.empty()) {
            const double u = f * 4; const int q = std::min((int)std::floor(u), 3);
            auto node = [&](int m) -> double { return m == 0 ? lam_[k * nk_ + b] : m == 4 ? lam_[(k + 1) * nk_ + b] : lq_[(k * 3 + m - 1) * 2 + jb]; };
            const double l0 = node(q), d = node(q + 1) - l0; lam = l0 + (u - q) * (d + std::round((turn / 4 - d) / kTwoPi) * kTwoPi);
        } else { const double l0 = lam_[k * nk_ + b], d = lam_[(k + 1) * nk_ + b] - l0; lam = l0 + f * (d + std::round((turn - d) / kTwoPi) * kTwoPi); }
        double M = std::remainder(lam - om, kTwoPi), E = M + e * std::sin(M);
        for (int it = 0; it < 20; it++) { const double dE = (E - e * std::sin(E) - M) / (1 - e * std::cos(E)); E -= dE; if (std::fabs(dE) < 1e-14) break; }
        const double w = om - O, cw = std::cos(w), sw = std::sin(w), cO = std::cos(O), sO = std::sin(O), cI = std::cos(I), sI = std::sin(I);
        const double P[3] = {cw * cO - sw * sO * cI, cw * sO + sw * cO * cI, sw * sI}, Q[3] = {-sw * cO - cw * sO * cI, -sw * sO + cw * cO * cI, cw * sI};
        const double xp = a * (std::cos(E) - e), yp = a * std::sqrt(1 - e * e) * std::sin(E);
        for (int c = 0; c < 3; c++) out[c] = P[c] * xp + Q[c] * yp;
        return true;
    }

private:
    double jd0_ = 0, dd_ = 0; long nP_ = 0, nF_ = 0, n_ = 0; int nk_ = 0, sl_ = 10;
    std::vector<float> lam_, slow_, lq_;
};

}  // namespace phys::nb
