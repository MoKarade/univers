// Appli PC « Univers », bibliothèque univers_physique : noyau du calcul à N corps du système solaire (interne).
// Port de app/src/21_nbody.js (page web, lot G), mêmes résultats.
//
// - Integrator : Soleil, 8 planètes (barycentres), Pluton, Cérès, Vesta, Pallas, Hygie s'attirent tous.
//   Wisdom et Holman (1991) en coordonnées héliocentriques démocratiques (Duncan, Levison et Lee 1998), pas de 4 jours ;
//   relativité générale du Soleil (premier ordre post-newtonien, Anderson et al. 1975), en deux demi-coups pour rester
//   réversible ; la Lune moyennée en anneau autour de la Terre (Quinn, Tremaine et Duncan 1991).
//   Départ : JPL Horizons (DE440) au 10/11/2026, vitesses calées sur DE440 de 1650 à 2450 (pipeline/gravite/ajuste.js) ;
//   données dans nbody_donnees.h (généré). Contrôle : essai_systeme_solaire.cpp (positions Horizons de 1650 à 2450).
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
#include <filesystem>
#include <limits>
#include <new>
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
    std::array<double, 3 * static_cast<size_t>(kN)> Q{}, V{};  // Q héliocentrique, V barycentrique (coordonnées démocratiques)
};

inline State initialState() {
    State s;
    s.jd = nbody_donnees::kJd0;
    for (size_t i = 0; i < 3 * static_cast<size_t>(kN); ++i) {
        s.Q[i] = nbody_donnees::kQ[i];
        s.V[i] = nbody_donnees::kV[i];
    }
    return s;
}

// Mouvement de Kepler exact pendant dt (anomalie excentrique, orbites liées).
inline bool kepler(double* r, double* v, double mu, double dt) {
    const double x0 = r[0], y0 = r[1], z0 = r[2], vx = v[0], vy = v[1], vz = v[2];
    const double r0 = std::sqrt(x0 * x0 + y0 * y0 + z0 * z0);
    const double v2 = vx * vx + vy * vy + vz * vz;
    const double rv = x0 * vx + y0 * vy + z0 * vz;
    const double ia = 2.0 / r0 - v2 / mu;
    if (!(ia > 0.0)) return false;
    const double a = 1.0 / ia, sa = std::sqrt(a), n = std::sqrt(mu * ia * ia * ia);
    const double s0 = rv / std::sqrt(mu), c1 = 1.0 - r0 * ia, c2 = s0 / sa, M = n * dt;
    double X = M;
    for (int k = 0; k < 30; ++k) {
        const double sx = std::sin(X), cx = std::cos(X);
        const double f = X - c1 * sx + c2 * (1.0 - cx) - M;
        const double fp = 1.0 - c1 * cx + c2 * sx;
        const double d = f / fp;
        X -= d;
        if (std::fabs(d) < 1e-14) break;
    }
    const double sx = std::sin(X), cx = std::cos(X);
    const double rr = a + (r0 - a) * cx + s0 * sa * sx;
    const double f = 1.0 - a / r0 * (1.0 - cx);
    const double g = dt + (sx - X) / n;
    const double fd = -std::sqrt(mu * a) * sx / (rr * r0);
    const double gd = 1.0 - a / rr * (1.0 - cx);
    r[0] = f * x0 + g * vx;
    r[1] = f * y0 + g * vy;
    r[2] = f * z0 + g * vz;
    v[0] = fd * x0 + gd * vx;
    v[1] = fd * y0 + gd * vy;
    v[2] = fd * z0 + gd * vz;
    return true;
}

class Integrator {
public:
    explicit Integrator(State s = initialState()) : s_(s) {}
    const State& state() const { return s_; }

    // Avance de n pas de dt jours (dt < 0 : vers le passé ; le schéma est réversible).
    void step(double dt, long n) {
        if (n <= 0 || !std::isfinite(dt)) return;
        for (long k = 0; k < n; ++k) {
            jump(dt / 2.0);
            kick(dt / 2.0);
            for (size_t i = 0; i < static_cast<size_t>(kN); ++i) {
                kepler(&s_.Q[3 * i], &s_.V[3 * i], kGmSun, dt);
            }
            kick(dt / 2.0);
            jump(dt / 2.0);
        }
        s_.jd += dt * static_cast<double>(n);
    }

    // Avance jusqu'à jd (pas d'au plus dtMax jours, le dernier raccourci).
    void advanceTo(double jd, double dtMax = nbody_donnees::kDtDays) {
        if (!std::isfinite(jd) || !std::isfinite(dtMax) || !(dtMax > 0.0)) return;
        const double span = jd - s_.jd;
        if (!std::isfinite(span) || span == 0.0) return;
        const double stepsD = std::ceil(std::fabs(span) / dtMax);
        if (!std::isfinite(stepsD) || stepsD > static_cast<double>(std::numeric_limits<long>::max() / 2)) return;
        const long n = static_cast<long>(stepsD);
        if (n > 0) {
            step(span / static_cast<double>(n), n);
            s_.jd = jd;
        }
    }

    // Positions barycentriques (UA) : Soleil puis les kN corps (out : 3 × (kN + 1) doubles).
    void barycentric(double* out) const {
        double m = kGmSun, x = 0.0, y = 0.0, z = 0.0;
        for (size_t i = 0; i < static_cast<size_t>(kN); ++i) {
            const double g = nbody_donnees::kGm[i];
            m += g;
            x += g * s_.Q[3 * i];
            y += g * s_.Q[3 * i + 1];
            z += g * s_.Q[3 * i + 2];
        }
        out[0] = -x / m;
        out[1] = -y / m;
        out[2] = -z / m;
        for (size_t i = 0; i < static_cast<size_t>(kN); ++i) {
            for (size_t c = 0; c < 3; ++c) {
                out[3 * (i + 1) + c] = s_.Q[3 * i + c] + out[c];
            }
        }
    }

    // Énergie newtonienne totale (contrôle).
    double energy() const {
        double px = 0.0, py = 0.0, pz = 0.0, E = 0.0;
        for (size_t i = 0; i < static_cast<size_t>(kN); ++i) {
            const double g = nbody_donnees::kGm[i];
            px += g * s_.V[3 * i];
            py += g * s_.V[3 * i + 1];
            pz += g * s_.V[3 * i + 2];
        }
        E += (px * px + py * py + pz * pz) / (2.0 * kGmSun);
        for (size_t i = 0; i < static_cast<size_t>(kN); ++i) {
            const double g = nbody_donnees::kGm[i];
            const double* q = &s_.Q[3 * i];
            const double* v = &s_.V[3 * i];
            const double r = std::hypot(q[0], q[1], q[2]);
            E += g * (0.5 * (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) - kGmSun / r);
            for (size_t j = i + 1; j < static_cast<size_t>(kN); ++j) {
                E -= g * nbody_donnees::kGm[j] /
                     std::hypot(s_.Q[3 * j] - q[0], s_.Q[3 * j + 1] - q[1], s_.Q[3 * j + 2] - q[2]);
            }
        }
        return E;
    }

private:
    State s_;

    // Déplacement dû au mouvement du Soleil.
    void jump(double h) {
        double px = 0.0, py = 0.0, pz = 0.0;
        for (size_t i = 0; i < static_cast<size_t>(kN); ++i) {
            const double g = nbody_donnees::kGm[i];
            px += g * s_.V[3 * i];
            py += g * s_.V[3 * i + 1];
            pz += g * s_.V[3 * i + 2];
        }
        const double k = h / kGmSun;
        for (size_t i = 0; i < static_cast<size_t>(kN); ++i) {
            s_.Q[3 * i] += k * px;
            s_.Q[3 * i + 1] += k * py;
            s_.Q[3 * i + 2] += k * pz;
        }
    }

    // Attraction mutuelle (le Soleil est dans Kepler), relativité en deux moitiés, anneau Terre-Lune.
    void kick(double h) {
        gr(h / 2.0);
        for (size_t i = 0; i < static_cast<size_t>(kN); ++i) {
            const double xi = s_.Q[3 * i], yi = s_.Q[3 * i + 1], zi = s_.Q[3 * i + 2];
            for (size_t j = i + 1; j < static_cast<size_t>(kN); ++j) {
                const double dx = s_.Q[3 * j] - xi, dy = s_.Q[3 * j + 1] - yi, dz = s_.Q[3 * j + 2] - zi;
                const double d2 = dx * dx + dy * dy + dz * dz;
                const double k = h / (d2 * std::sqrt(d2));
                const double ki = nbody_donnees::kGm[j] * k, kj = nbody_donnees::kGm[i] * k;
                s_.V[3 * i] += ki * dx;
                s_.V[3 * i + 1] += ki * dy;
                s_.V[3 * i + 2] += ki * dz;
                s_.V[3 * j] -= kj * dx;
                s_.V[3 * j + 1] -= kj * dy;
                s_.V[3 * j + 2] -= kj * dz;
            }
        }
        gr(h / 2.0);
        moonRing(h);
    }

    // Relativité : a = GM/(c² r³) [(4 GM/r − v²) r + 4 (r·v) v], v héliocentrique, point milieu (trois passes).
    void gr(double h) {
        double px = 0.0, py = 0.0, pz = 0.0;
        for (size_t i = 0; i < static_cast<size_t>(kN); ++i) {
            const double g = nbody_donnees::kGm[i];
            px += g * s_.V[3 * i];
            py += g * s_.V[3 * i + 1];
            pz += g * s_.V[3 * i + 2];
        }
        const double sx = -px / kGmSun, sy = -py / kGmSun, sz = -pz / kGmSun;
        const double c2 = kCAuDay * kCAuDay, mu = kGmSun;
        for (size_t i = 0; i < static_cast<size_t>(kN); ++i) {
            const double x = s_.Q[3 * i], y = s_.Q[3 * i + 1], z = s_.Q[3 * i + 2];
            const double r = std::sqrt(x * x + y * y + z * z);
            const double vx = s_.V[3 * i] - sx, vy = s_.V[3 * i + 1] - sy, vz = s_.V[3 * i + 2] - sz;
            const double k = mu / (c2 * r * r * r);
            const double fourMuOverR = 4.0 * mu / r;
            double ax = 0.0, ay = 0.0, az = 0.0;
            for (int it = 0; it < 3; ++it) {
                const double ux = vx + ax * h / 2.0, uy = vy + ay * h / 2.0, uz = vz + az * h / 2.0;
                const double v2 = ux * ux + uy * uy + uz * uz;
                const double rv = x * ux + y * uy + z * uz;
                const double a1 = fourMuOverR - v2;
                ax = k * (a1 * x + 4.0 * rv * ux);
                ay = k * (a1 * y + 4.0 * rv * uy);
                az = k * (a1 * z + 4.0 * rv * uz);
            }
            s_.V[3 * i] += h * ax;
            s_.V[3 * i + 1] += h * ay;
            s_.V[3 * i + 2] += h * az;
        }
    }

    // Lune moyennée sur son orbite : anneau de masse réduite μ autour de la Terre ; U = G M☉ μ ρ² P2(r̂·n) / (2 r³), n = pôle de l'écliptique.
    void moonRing(double h) {
        constexpr size_t i = 2;  // barycentre Terre-Lune
        constexpr double aM = 384400.0 / 149597870.7;
        constexpr double rho2 = aM * aM * (1.0 + 1.5 * 0.0549 * 0.0549);
        constexpr double mu = 8.8876924467071033e-10 * 1.0931894624024351e-11 /
                              (8.9970116036316091e-10 * 8.9970116036316091e-10);
        const double x = s_.Q[3 * i], y = s_.Q[3 * i + 1], z = s_.Q[3 * i + 2];
        const double r2 = x * x + y * y + z * z, r = std::sqrt(r2), r5 = r2 * r2 * r, r7 = r5 * r2;
        const double k = -h * kGmSun * mu * rho2 / 4.0, z2 = z * z;
        s_.V[3 * i] += k * x * (3.0 / r5 - 15.0 * z2 / r7);
        s_.V[3 * i + 1] += k * y * (3.0 / r5 - 15.0 * z2 / r7);
        s_.V[3 * i + 2] += k * z * (9.0 / r5 - 15.0 * z2 / r7);
    }
};

// Orbites sur des millions d'années : table de build_long.js (version 2). λ tous les 1 000 ans (Jupiter et Saturne tous
// les 250 ans), a, e, i, Ω, ϖ tous les 10 000 ans ; entre deux dates, λ avance au mouvement moyen réel.
class LongTable {
public:
    bool load(const std::string& path) {
        reset();
        if (path.empty()) return false;
        std::error_code ec;
        if (!std::filesystem::is_regular_file(path, ec) || ec) return false;
        static constexpr uintmax_t kMaxTableBytes = 2ULL * 1024ULL * 1024ULL * 1024ULL;
        const uintmax_t fsz = std::filesystem::file_size(path, ec);
        if (ec || fsz < 56 || fsz > kMaxTableBytes ||
            fsz > static_cast<uintmax_t>(std::numeric_limits<size_t>::max())) {
            return false;
        }
        FILE* f = std::fopen(path.c_str(), "rb");
        if (!f) return false;
        const size_t size = static_cast<size_t>(fsz);
        std::vector<uint8_t> b;
        try {
            b.resize(size);
        } catch (const std::bad_alloc&) {
            std::fclose(f);
            return false;
        }
        const bool readOk = std::fread(b.data(), 1, size, f) == size;
        std::fclose(f);
        if (!readOk) return false;

        double h[7];
        std::memcpy(h, b.data(), sizeof(h));
        if (!std::all_of(std::begin(h), std::end(h), [](double v) { return std::isfinite(v); })) return false;
        const double ver = h[0], jd0 = h[1], dd = h[2];
        if (ver < 1.0 || !(dd > 0.0)) return false;
        auto validInt = [](double v, double lo, double hi) {
            return v >= lo && v <= hi && std::floor(v) == v;
        };
        if (!validInt(h[3], 0.0, 1e9) || !validInt(h[4], 0.0, 1e9) ||
            !validInt(h[5], 1.0, 1024.0) || !validInt(h[6], 1.0, 1e9)) {
            return false;
        }
        const long nP = static_cast<long>(h[3]);
        const long nF = static_cast<long>(h[4]);
        const int nk = static_cast<int>(h[5]);
        const int sl = static_cast<int>(h[6]);
        if (nP > std::numeric_limits<long>::max() - nF - 1) return false;
        if (!std::isfinite(jd0 - static_cast<double>(nP) * dd) ||
            !std::isfinite(jd0 + static_cast<double>(nF) * dd)) {
            return false;
        }
        const long n = nP + nF + 1;
        if (n < 2) return false;
        const long nS = (n - 1) / sl + 1;
        if (nS < 2) return false;

        auto mulChecked = [](size_t a, size_t c, size_t& res) {
            if (a != 0 && c > std::numeric_limits<size_t>::max() / a) return false;
            res = a * c;
            return true;
        };
        auto addChecked = [](size_t a, size_t c, size_t& res) {
            if (c > std::numeric_limits<size_t>::max() - a) return false;
            res = a + c;
            return true;
        };

        size_t lamCount = 0, slowTmp = 0, slowCount = 0, lqCount = 0;
        size_t totalFloats = 0, payloadBytes = 0, totalBytes = 0;
        if (!mulChecked(static_cast<size_t>(n), static_cast<size_t>(nk), lamCount) ||
            !mulChecked(static_cast<size_t>(nS), static_cast<size_t>(nk), slowTmp) ||
            !mulChecked(slowTmp, 5, slowCount)) {
            return false;
        }
        if (ver >= 2.0) {
            if (!mulChecked(static_cast<size_t>(n - 1), 6, lqCount)) return false;
        }
        if (!addChecked(lamCount, slowCount, totalFloats) ||
            !addChecked(totalFloats, lqCount, totalFloats) ||
            !mulChecked(totalFloats, sizeof(float), payloadBytes) ||
            !addChecked(56, payloadBytes, totalBytes) ||
            totalBytes > b.size()) {
            return false;
        }

        try {
            lam_.resize(lamCount);
            slow_.resize(slowCount);
            lq_.resize(lqCount);
        } catch (const std::bad_alloc&) {
            reset();
            return false;
        }
        size_t o = 56;
        auto rd = [&](std::vector<float>& v) {
            if (!v.empty()) {
                const size_t bytes = v.size() * sizeof(float);
                std::memcpy(v.data(), b.data() + o, bytes);
                o += bytes;
            }
        };
        rd(lam_);
        rd(slow_);
        rd(lq_);
        jd0_ = jd0;
        dd_ = dd;
        nP_ = nP;
        nF_ = nF;
        n_ = n;
        nk_ = nk;
        sl_ = sl;
        return true;
    }

    bool loaded() const { return n_ >= 2; }
    // Années (depuis le départ) et jours juliens TDB couverts : [début, fin].
    double firstYear() const { return -static_cast<double>(nP_) * dd_ / 365.25; }
    double lastYear() const { return static_cast<double>(nF_) * dd_ / 365.25; }
    double firstJd() const { return jd0_ - static_cast<double>(nP_) * dd_; }
    double lastJd() const { return jd0_ + static_cast<double>(nF_) * dd_; }

    // Position héliocentrique (UA, écliptique J2000) du corps b (0 Mercure … 7 Neptune, 8 Pluton ; 2 = barycentre Terre-Lune)
    // à jd (TDB). false hors de la table.
    bool position(int b, double jd, double out[3]) const {
        if (!loaded() || !out || b < 0 || b >= nk_ || sl_ <= 0 || !(dd_ > 0.0) || !std::isfinite(jd)) return false;
        if (jd < firstJd() || jd > lastJd()) return false;
        const double xRaw = (jd - jd0_) / dd_ + static_cast<double>(nP_);
        if (!std::isfinite(xRaw)) return false;
        const double x = std::clamp(xRaw, 0.0, static_cast<double>(n_ - 1));
        const long k = std::clamp(static_cast<long>(std::floor(x)), 0L, n_ - 2);
        const double f = x - static_cast<double>(k);
        const size_t uNk = static_cast<size_t>(nk_);
        const size_t uB = static_cast<size_t>(b);
        const size_t slowStride = uNk * 5;
        const long nS = static_cast<long>(slow_.size() / slowStride);
        if (nS < 2) return false;
        const double xs = x / static_cast<double>(sl_);
        const long ks = std::clamp(static_cast<long>(std::floor(xs)), 0L, nS - 2);
        const double fs = std::max(0.0, xs - static_cast<double>(ks));
        const size_t uKs = static_cast<size_t>(ks);
        const float* s0 = &slow_[(uKs * uNk + uB) * 5];
        const float* s1 = &slow_[((uKs + 1) * uNk + uB) * 5];
        auto lin = [&](int q) { return s0[q] + (s1[q] - s0[q]) * fs; };
        auto ang = [&](int q) {
            const double d = std::atan2(std::sin(s1[q] - s0[q]), std::cos(s1[q] - s0[q]));
            return s0[q] + d * fs;
        };
        const double a = lin(0), e = lin(1), I = lin(2), O = ang(3), om = ang(4);
        if (!std::isfinite(a) || !(a > 0.0) || !(e >= 0.0 && e < 1.0) || !std::isfinite(I) || !std::isfinite(O) ||
            !std::isfinite(om)) {
            return false;
        }
        const double turn = 0.01720209895 / std::pow(a, 1.5) * dd_;
        if (!std::isfinite(turn)) return false;
        double lam = 0.0;
        const size_t uK = static_cast<size_t>(k);
        const int jb = b == 4 ? 0 : b == 5 ? 1 : -1;
        if (jb >= 0 && lq_.size() >= static_cast<size_t>(n_ - 1) * 6) {
            const double u = f * 4.0;
            const int q = std::clamp(static_cast<int>(std::floor(u)), 0, 3);
            auto node = [&](int m) -> double {
                if (m == 0) return lam_[uK * uNk + uB];
                if (m == 4) return lam_[(uK + 1) * uNk + uB];
                return lq_[(uK * 3 + static_cast<size_t>(m - 1)) * 2 + static_cast<size_t>(jb)];
            };
            const double l0 = node(q), d = node(q + 1) - l0;
            lam = l0 + (u - q) * (d + std::round((turn / 4.0 - d) / kTwoPi) * kTwoPi);
        } else {
            const double l0 = lam_[uK * uNk + uB], d = lam_[(uK + 1) * uNk + uB] - l0;
            lam = l0 + f * (d + std::round((turn - d) / kTwoPi) * kTwoPi);
        }
        if (!std::isfinite(lam)) return false;
        const double M = std::remainder(lam - om, kTwoPi);
        double E = M + e * std::sin(M);
        for (int it = 0; it < 20; ++it) {
            const double dE = (E - e * std::sin(E) - M) / (1.0 - e * std::cos(E));
            E -= dE;
            if (std::fabs(dE) < 1e-14) break;
        }
        const double w = om - O, cw = std::cos(w), sw = std::sin(w);
        const double cO = std::cos(O), sO = std::sin(O), cI = std::cos(I), sI = std::sin(I);
        const double P[3] = {cw * cO - sw * sO * cI, cw * sO + sw * cO * cI, sw * sI};
        const double Q[3] = {-sw * cO - cw * sO * cI, -sw * sO + cw * cO * cI, cw * sI};
        const double xp = a * (std::cos(E) - e), yp = a * std::sqrt(1.0 - e * e) * std::sin(E);
        double res[3];
        for (int c = 0; c < 3; ++c) {
            res[c] = P[c] * xp + Q[c] * yp;
        }
        if (!std::isfinite(res[0]) || !std::isfinite(res[1]) || !std::isfinite(res[2])) return false;
        out[0] = res[0];
        out[1] = res[1];
        out[2] = res[2];
        return true;
    }

private:
    double jd0_ = 0, dd_ = 0;
    long nP_ = 0, nF_ = 0, n_ = 0;
    int nk_ = 0, sl_ = 10;
    std::vector<float> lam_, slow_, lq_;

    void reset() {
        jd0_ = 0;
        dd_ = 0;
        nP_ = 0;
        nF_ = 0;
        n_ = 0;
        nk_ = 0;
        sl_ = 10;
        lam_.clear();
        slow_.clear();
        lq_.clear();
    }
};

}  // namespace phys::nb
