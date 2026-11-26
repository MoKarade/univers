// Appli PC « Univers », bibliothèque univers_physique : orbites des étoiles dans la Voie lactée (au-delà de 3 millions
// d'années, où la ligne droite ne vaut plus). Port de app/src/26_orbits.js (page web, lots S2 et G), mêmes résultats.
//
// Repère galactocentrique de la page : centre galactique à l'origine, Soleil en −R0 · SGRA_GAL (≈ (−8,2 ; 0 ; 0) kpc),
// axe y vers la longitude galactique 90° (sens de rotation), z vers le nord galactique ; kpc et km/s ; temps en Ga.
// Potentiel : bulbe de Hernquist + disque de Miyamoto-Nagai + halo NFW (inspiré de MWPotential2014, Bovy 2015, recalé sur
// 230 km/s au Soleil) + barre centrale tournante (Dehnen 2000) :
//   mesuré : vitesse de la barre 39 km/s/kpc (Portail et al. 2017 ; fourchette récente 33 à 41), angle 28° devant la
//   direction du centre, bout proche aux longitudes positives (Wegg et Gerhard 2013), demi-longueur 5,0 kpc (Wegg et al. 2015) ;
//   modèle : force α = 0,01 (Dehnen 2000). Pas de bras spiraux (vitesse non établie).
// Intégration : saut de grenouille (vitesse de Verlet FSAL), pas de 1 Ma, sous-pas pour les orbites qui plongent vers le centre.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <span>
#include <thread>
#include <vector>

#include "phys.h"

namespace phys::galaxie {

constexpr double kG = 4.30091e-6;  // kpc·(km/s)²/masse solaire
constexpr double kR0 = 8.2, kV0 = 230.0;
constexpr double kMb = 0.5e10, kAb = 0.5, kMd = 6.8e10, kAd = 3.0, kBd = 0.28, kRs = 16.0;
constexpr double kKmsKpcToRadGa = 1.0227121650456;  // km/s/kpc -> rad/Ga ; aussi km/s -> kpc/Ga
constexpr double kPi = 3.14159265358979323846;
// Barre : constantes partagées avec le dessin (fil « Voie lactée et étoiles Gaia sur PC »).
constexpr double kBarAngleRad = 28.0 * kPi / 180.0;  // entre l'axe de la barre et la direction Soleil-centre, à t = 0
constexpr double kBarOmegaKmsKpc = 39.0;             // sens de rotation du disque (φ décroissant dans ce repère)
constexpr double kBarHalfLengthKpc = 5.0;
constexpr double kBarAlpha = 0.01;
constexpr double kDtGa = 0.001;
// Direction du centre galactique vue du Soleil dans le repère de la page (DATA.SGRA_GAL) et vitesse du Soleil (km/s).
constexpr double kSgra[3] = {0.9999992, -0.00097327, -0.00080564};
constexpr double kSunUvw[3] = {11.1, 242.24, 7.25};

// Angle de l'axe de la barre (rad, depuis l'axe x) à tGa : φ_b(t) = π − 28° − Ω_b t.
inline double barAngleAt(double tGa) { return kPi - kBarAngleRad - kBarOmegaKmsKpc * kKmsKpcToRadGa * tGa; }

inline double v2Baryons(double r) {
    const double ra = r + kAb;
    const double ab = kAd + kBd;
    const double d2 = r * r + ab * ab;
    return kG * kMb * r / (ra * ra) + kG * kMd * r * r / (d2 * std::sqrt(d2));
}
inline double nfwShape(double r) {
    const double x = r / kRs;
    return (std::log1p(x) - x / (1.0 + x)) / r;
}
inline double gmHalo() { return (kV0 * kV0 - v2Baryons(kR0)) / nfwShape(kR0); }  // calé sur 230 km/s au Soleil

struct Potentiel {
    double GMs = gmHalo();
    double Rb = kBarHalfLengthKpc;
    double Ab = kBarAlpha * kV0 * kV0 * std::pow(kR0 / kBarHalfLengthKpc, 3) / 3.0;
    bool barre = true;

    // Accélération (km/s)²/kpc en (x, y, z) kpc avec cos(2φ_b) et sin(2φ_b) précalculés.
    template <bool WithBar>
    void accTrig(double x, double y, double z, double cb2, double sb2, double a[3]) const {
        const double R2 = x * x + y * y;
        const double r = std::sqrt(R2 + z * z) + 1e-12;
        const double invR = 1.0 / r;
        const double xs = r / kRs;
        const double ra = r + kAb;
        const double ar = -kG * kMb / (ra * ra) - GMs * (std::log1p(xs) - xs / (1.0 + xs)) * invR * invR;
        const double B = std::sqrt(z * z + kBd * kBd);
        const double AdB = kAd + B;
        const double D2 = R2 + AdB * AdB;
        const double invD3 = 1.0 / (D2 * std::sqrt(D2));
        const double gmInvD3 = (kG * kMd) * invD3;
        const double arOverR = ar * invR;
        const double cXY = arOverR - gmInvD3;
        a[0] = cXY * x;
        a[1] = cXY * y;
        a[2] = arOverR * z - gmInvD3 * z * AdB / B;
        if constexpr (WithBar) {
            if (R2 > 1e-8) {  // Dehnen 2000 : a_R = −A cos2ψ U'(R), a_φ = 2A sin2ψ U(R) / R
                const double R = std::sqrt(R2);
                const double invRc = 1.0 / R;
                const double c = x * invRc, s = y * invRc;
                const double c2p = c * c - s * s, s2p = 2.0 * s * c;
                const double c2 = c2p * cb2 + s2p * sb2;
                const double s2 = s2p * cb2 - c2p * sb2;
                const double q = R / Rb;
                double U = 0.0, dU = 0.0;
                if (R < Rb) {
                    const double q2 = q * q;
                    U = q2 * q - 2.0;
                    dU = 3.0 * q2 / Rb;
                } else {
                    const double invQ3 = 1.0 / (q * q * q);
                    U = -invQ3;
                    dU = 3.0 * invQ3 * invRc;
                }
                const double aR = -Ab * c2 * dU;
                const double aP = 2.0 * Ab * s2 * U * invRc;
                a[0] += aR * c - aP * s;
                a[1] += aR * s + aP * c;
            }
        }
    }

    // Accélération (km/s)²/kpc en (x, y, z) kpc à tGa.
    void acc(double x, double y, double z, double t, double a[3]) const {
        if (barre) {
            const double twoPhi = 2.0 * barAngleAt(t);
            accTrig<true>(x, y, z, std::cos(twoPhi), std::sin(twoPhi), a);
        } else {
            accTrig<false>(x, y, z, 1.0, 0.0, a);
        }
    }

    // Énergie sans la barre (sert au choix des sous-pas et aux contrôles), (km/s)².
    double energie(double x, double y, double z, double vx, double vy, double vz) const {
        const double R2 = x * x + y * y;
        const double r = std::sqrt(R2 + z * z) + 1e-12;
        const double B = std::sqrt(z * z + kBd * kBd);
        const double phi = -kG * kMb / (r + kAb) - kG * kMd / std::sqrt(R2 + (kAd + B) * (kAd + B)) -
                           GMs * std::log1p(r / kRs) / r;
        return 0.5 * (vx * vx + vy * vy + vz * vz) + phi;
    }

    double phiBarre(double x, double y, double t) const {
        const double R = std::hypot(x, y), q = R / Rb;
        const double U = R < Rb ? q * q * q - 2.0 : -1.0 / (q * q * q);
        return Ab * std::cos(2.0 * (std::atan2(y, x) - barAngleAt(t))) * U;
    }
};

// Orbites d'un ensemble d'étoiles. Positions et vitesses galactocentriques (kpc, km/s) à t = 0 ; avance(t) les porte à t
// (sur plusieurs fils d'exécution) ; positions() les lit. Une instance n'est pas partagée entre fils pendant avance().
class Orbites {
public:
    Orbites() = default;
    Orbites(std::span<const Vec3> pos, std::span<const Vec3> vit, Potentiel P = {}) : P_(P), t_(0.0) {
        const size_t n = std::min(pos.size(), vit.size());
        X_.resize(3 * n);
        V_.resize(3 * n);
        sub_.resize(n);
        maxSub_ = 1;
        for (size_t k = 0; k < n; ++k) {
            X_[3 * k] = pos[k].x;
            X_[3 * k + 1] = pos[k].y;
            X_[3 * k + 2] = pos[k].z;
            V_[3 * k] = vit[k].x;
            V_[3 * k + 1] = vit[k].y;
            V_[3 * k + 2] = vit[k].z;
            const uint8_t m = sousPas(k);
            sub_[k] = m;
            if (m > maxSub_) maxSub_ = m;
        }
    }

    double temps() const { return t_; }
    size_t taille() const { return sub_.size(); }

    // Avance jusqu'à tGa (arrondi au pas de 1 Ma ; vers le passé si tGa < temps()).
    void avance(double tGa, unsigned fils = std::thread::hardware_concurrency()) {
        if (!std::isfinite(tGa)) return;
        const double rawSteps = (tGa - t_) / kDtGa;
        if (!std::isfinite(rawSteps) ||
            std::fabs(rawSteps) > static_cast<double>(std::numeric_limits<long>::max() / 2)) {
            return;
        }
        const long n = std::lround(rawSteps);
        if (n == 0) return;
        const double dt = n > 0 ? kDtGa : -kDtGa;
        const long totalSteps = n > 0 ? n : -n;
        const size_t N = sub_.size();
        if (N == 0) {
            t_ += static_cast<double>(totalSteps) * dt;
            return;
        }
        if (fils < 1) fils = 1;
        const unsigned workers = static_cast<unsigned>(std::min<size_t>(fils, N));
        const size_t part = (N + workers - 1) / workers;

        constexpr long kMaxBlockSteps = 1024;
        std::vector<BarTrig> barTable;
        std::vector<std::thread> th;
        if (workers > 1) th.reserve(workers - 1);

        for (long done = 0; done < totalSteps; done += kMaxBlockSteps) {
            const long chunkSteps = std::min(kMaxBlockSteps, totalSteps - done);
            const double tChunk = t_ + static_cast<double>(done) * dt;
            if (P_.barre) {
                const size_t ticks = static_cast<size_t>(chunkSteps) * maxSub_ + 1;
                barTable.resize(ticks);
                const double dtTick = dt / static_cast<double>(maxSub_);
                for (size_t j = 0; j < ticks; ++j) {
                    const double twoPhi = 2.0 * barAngleAt(tChunk + static_cast<double>(j) * dtTick);
                    barTable[j] = {std::cos(twoPhi), std::sin(twoPhi)};
                }
            }
            if (workers == 1) {
                pas(0, N, dt, chunkSteps, barTable);
            } else {
                th.clear();
                for (unsigned f = 1; f < workers; ++f) {
                    const size_t a = static_cast<size_t>(f) * part;
                    if (a >= N) break;
                    const size_t b = std::min(N, a + part);
                    th.emplace_back([this, a, b, dt, chunkSteps, &barTable] { pas(a, b, dt, chunkSteps, barTable); });
                }
                pas(0, std::min(N, part), dt, chunkSteps, barTable);
                for (auto& x : th) {
                    x.join();
                }
            }
        }
        t_ += static_cast<double>(totalSteps) * dt;
    }

    // Positions (kpc) de toutes les étoiles au temps courant.
    void positions(std::span<Vec3> out) const {
        const size_t count = std::min(sub_.size(), out.size());
        for (size_t k = 0; k < count; ++k) {
            out[k] = {X_[3 * k], X_[3 * k + 1], X_[3 * k + 2]};
        }
    }
    Vec3 position(size_t k) const { return {X_[3 * k], X_[3 * k + 1], X_[3 * k + 2]}; }
    Vec3 vitesse(size_t k) const { return {V_[3 * k], V_[3 * k + 1], V_[3 * k + 2]}; }
    const Potentiel& potentiel() const { return P_; }

private:
    struct BarTrig {
        double cb2 = 1.0;
        double sb2 = 0.0;
    };

    Potentiel P_;
    double t_ = 0.0;
    uint8_t maxSub_ = 1;
    std::vector<double> X_, V_;
    std::vector<uint8_t> sub_;

    // Sous-pas d'après le péricentre estimé (potentiel pris dans le plan) : sous 0,7 kpc : 32 ; 2 kpc : 8 ; 4 kpc : 2 ; sinon 1.
    uint8_t sousPas(size_t k) const {
        const double x = X_[3 * k], y = X_[3 * k + 1], z = X_[3 * k + 2];
        const double vx = V_[3 * k], vy = V_[3 * k + 1], vz = V_[3 * k + 2];
        const double E = P_.energie(x, y, z, vx, vy, vz);
        const double lx = y * vz - z * vy, ly = z * vx - x * vz, lz = x * vy - y * vx;
        const double L2 = lx * lx + ly * ly + lz * lz;
        auto f = [&](double r) { return 2.0 * (E - P_.energie(r, 0.0, 0.0, 0.0, 0.0, 0.0)) * r * r - L2; };
        double lo = 1e-3, hi = std::max(std::sqrt(x * x + y * y + z * z), 2e-3);
        if (f(lo) < 0.0) {
            for (int it = 0; it < 40; ++it) {
                const double m = 0.5 * (lo + hi);
                if (f(m) < 0.0) lo = m;
                else hi = m;
            }
        } else {
            hi = lo;
        }
        return hi < 0.7 ? 32 : hi < 2.0 ? 8 : hi < 4.0 ? 2 : 1;
    }

    template <bool WithBar>
    void pasImpl(size_t a, size_t b, double dt, long steps, const std::vector<BarTrig>& barTable) {
        if (steps <= 0 || dt == 0.0 || a >= b) return;
        const size_t uSteps = static_cast<size_t>(steps);
        double acc[3];
        for (size_t k = a; k < b; ++k) {
            const size_t m = sub_[k];
            const size_t total = uSteps * m;
            const size_t stride = WithBar ? static_cast<size_t>(maxSub_) / m : 0;
            const double h = dt * kKmsKpcToRadGa / static_cast<double>(m);
            const double halfH = 0.5 * h;
            double x = X_[3 * k], y = X_[3 * k + 1], z = X_[3 * k + 2];
            double vx = V_[3 * k], vy = V_[3 * k + 1], vz = V_[3 * k + 2];

            // Vitesse de Verlet FSAL : demi-coup initial, (total - 1) coups complets fusionnés, demi-coup final.
            if constexpr (WithBar) {
                P_.accTrig<true>(x, y, z, barTable[0].cb2, barTable[0].sb2, acc);
            } else {
                P_.accTrig<false>(x, y, z, 1.0, 0.0, acc);
            }
            vx += halfH * acc[0];
            vy += halfH * acc[1];
            vz += halfH * acc[2];
            x += h * vx;
            y += h * vy;
            z += h * vz;

            for (size_t j = 1; j < total; ++j) {
                if constexpr (WithBar) {
                    const BarTrig& bt = barTable[j * stride];
                    P_.accTrig<true>(x, y, z, bt.cb2, bt.sb2, acc);
                } else {
                    P_.accTrig<false>(x, y, z, 1.0, 0.0, acc);
                }
                vx += h * acc[0];
                vy += h * acc[1];
                vz += h * acc[2];
                x += h * vx;
                y += h * vy;
                z += h * vz;
            }

            if constexpr (WithBar) {
                const BarTrig& bt = barTable[total * stride];
                P_.accTrig<true>(x, y, z, bt.cb2, bt.sb2, acc);
            } else {
                P_.accTrig<false>(x, y, z, 1.0, 0.0, acc);
            }
            vx += halfH * acc[0];
            vy += halfH * acc[1];
            vz += halfH * acc[2];

            X_[3 * k] = x;
            X_[3 * k + 1] = y;
            X_[3 * k + 2] = z;
            V_[3 * k] = vx;
            V_[3 * k + 1] = vy;
            V_[3 * k + 2] = vz;
        }
    }

    void pas(size_t a, size_t b, double dt, long steps, const std::vector<BarTrig>& barTable) {
        if (P_.barre) {
            pasImpl<true>(a, b, dt, steps, barTable);
        } else {
            pasImpl<false>(a, b, dt, steps, barTable);
        }
    }
};

// Le Soleil dans ce repère, à t = 0.
inline Vec3 soleilPos() { return {-kSgra[0] * kR0, -kSgra[1] * kR0, -kSgra[2] * kR0}; }
inline Vec3 soleilVit() { return {kSunUvw[0], kSunUvw[1], kSunUvw[2]}; }

}  // namespace phys::galaxie
