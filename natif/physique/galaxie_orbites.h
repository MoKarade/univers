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
// Intégration : saut de grenouille (vitesse de Verlet), pas de 1 Ma, sous-pas pour les orbites qui plongent vers le centre.
#pragma once
#include <cmath>
#include <cstdint>
#include <span>
#include <thread>
#include <vector>

#include "phys.h"

namespace phys::galaxie {

constexpr double kG = 4.30091e-6;      // kpc·(km/s)²/masse solaire
constexpr double kR0 = 8.2, kV0 = 230;
constexpr double kMb = 0.5e10, kAb = 0.5, kMd = 6.8e10, kAd = 3.0, kBd = 0.28, kRs = 16;
constexpr double kKmsKpcToRadGa = 1.0227121650456;      // km/s/kpc -> rad/Ga ; aussi km/s -> kpc/Ga
constexpr double kPi = 3.14159265358979323846;
// Barre : constantes partagées avec le dessin (fil « Voie lactée et étoiles Gaia sur PC »).
constexpr double kBarAngleRad = 28 * kPi / 180;          // entre l'axe de la barre et la direction Soleil-centre, à t = 0
constexpr double kBarOmegaKmsKpc = 39;                   // sens de rotation du disque (φ décroissant dans ce repère)
constexpr double kBarHalfLengthKpc = 5.0;
constexpr double kBarAlpha = 0.01;
constexpr double kDtGa = 0.001;
// Direction du centre galactique vue du Soleil dans le repère de la page (DATA.SGRA_GAL) et vitesse du Soleil (km/s).
constexpr double kSgra[3] = {0.9999992, -0.00097327, -0.00080564};
constexpr double kSunUvw[3] = {11.1, 242.24, 7.25};

// Angle de l'axe de la barre (rad, depuis l'axe x) à tGa : φ_b(t) = π − 28° − Ω_b t.
inline double barAngleAt(double tGa) { return kPi - kBarAngleRad - kBarOmegaKmsKpc * kKmsKpcToRadGa * tGa; }

inline double v2Baryons(double r) { return kG * kMb * r / ((r + kAb) * (r + kAb)) + kG * kMd * r * r / std::pow(r * r + (kAd + kBd) * (kAd + kBd), 1.5); }
inline double nfwShape(double r) { const double x = r / kRs; return (std::log(1 + x) - x / (1 + x)) / r; }
inline double gmHalo() { return (kV0 * kV0 - v2Baryons(kR0)) / nfwShape(kR0); }      // calé sur 230 km/s au Soleil

// Fréquences du potentiel SANS la barre, dans le plan (z = 0), à R kpc ; en km/s/kpc (× kKmsKpcToRadGa pour des rad/Ga).
// Formules exactes (dérivées analytiques du même potentiel que Potentiel::acc) ; contrôlées dans essai_galaxie contre des
// différences finies de acc. Approximation des épicycles valable pour les orbites presque circulaires du disque seulement :
// pour suivre une étoile à toute date sans approximation, intégrer Potentiel::acc (c'est ce que fait Orbites).
struct Frequences {
    double vc;      // vitesse circulaire (km/s)
    double omega;   // fréquence de rotation Ω = vc / R
    double kappa;   // fréquence radiale des épicycles κ (κ² = Φ'' + 3 Ω²)
    double nu;      // fréquence verticale ν (ν² = ∂²Φ/∂z² en z = 0)
};
inline Frequences frequences(double R) {
    const double gb = kG * kMb, gd = kG * kMd, gh = gmHalo(), c2 = (kAd + kBd) * (kAd + kBd), D2 = R * R + c2, D = std::sqrt(D2), x = R / kRs;
    const double m = std::log(1 + x) - x / (1 + x);
    const double d1 = gb / ((R + kAb) * (R + kAb)) + gd * R / (D2 * D) + gh * m / (R * R);                                   // Φ'(R)
    const double d2 = -2 * gb / std::pow(R + kAb, 3) + gd * (c2 - 2 * R * R) / (D2 * D2 * D) + gh * (x / ((1 + x) * (1 + x) * kRs * R * R) - 2 * m / (R * R * R));      // Φ''(R)
    const double nu2 = gb / (R * (R + kAb) * (R + kAb)) + gd * (kAd + kBd) / (kBd * D2 * D) + gh * m / (R * R * R);
    const double om2 = d1 / R;
    return {std::sqrt(R * d1), std::sqrt(om2), std::sqrt(d2 + 3 * om2), std::sqrt(nu2)};
}

struct Potentiel {
    double GMs = gmHalo(), Rb = kBarHalfLengthKpc, Ab = kBarAlpha * kV0 * kV0 * std::pow(kR0 / kBarHalfLengthKpc, 3) / 3;
    double omegaBarre = kBarOmegaKmsKpc;      // km/s/kpc ; modifiable pour mesurer l'effet de son incertitude (33 à 41)
    double angleBarre(double t) const { return kPi - kBarAngleRad - omegaBarre * kKmsKpcToRadGa * t; }
    bool barre = true;
    // Accélération (km/s)²/kpc en (x, y, z) kpc à tGa.
    void acc(double x, double y, double z, double t, double a[3]) const {
        const double R2 = x * x + y * y, r = std::sqrt(R2 + z * z) + 1e-12, xs = r / kRs;
        const double ar = -kG * kMb / ((r + kAb) * (r + kAb)) - GMs * (std::log(1 + xs) - xs / (1 + xs)) / (r * r);
        const double B = std::sqrt(z * z + kBd * kBd), D2 = R2 + (kAd + B) * (kAd + B), D3 = D2 * std::sqrt(D2), gm = kG * kMd;
        a[0] = ar * x / r - gm * x / D3; a[1] = ar * y / r - gm * y / D3; a[2] = ar * z / r - gm * z * (kAd + B) / (B * D3);
        if (barre && R2 > 1e-8) {      // Dehnen 2000 : a_R = −A cos2ψ U'(R), a_φ = 2A sin2ψ U(R) / R
            const double R = std::sqrt(R2), c = x / R, s = y / R, psi = std::atan2(y, x) - angleBarre(t), c2 = std::cos(2 * psi), s2 = std::sin(2 * psi), q = R / Rb;
            const double U = R < Rb ? q * q * q - 2 : -1 / (q * q * q), dU = R < Rb ? 3 * q * q / Rb : 3 / (q * q * q * q * Rb);
            const double aR = -Ab * c2 * dU, aP = 2 * Ab * s2 * U / R;
            a[0] += aR * c - aP * s; a[1] += aR * s + aP * c;
        }
    }
    // Énergie sans la barre (sert au choix des sous-pas et aux contrôles), (km/s)².
    double energie(double x, double y, double z, double vx, double vy, double vz) const {
        const double r = std::sqrt(x * x + y * y + z * z) + 1e-12, R2 = x * x + y * y, B = std::sqrt(z * z + kBd * kBd);
        const double phi = -kG * kMb / (r + kAb) - kG * kMd / std::sqrt(R2 + (kAd + B) * (kAd + B)) - GMs * std::log(1 + r / kRs) / r;
        return 0.5 * (vx * vx + vy * vy + vz * vz) + phi;
    }
    double phiBarre(double x, double y, double t) const {
        const double R = std::hypot(x, y), q = R / Rb, U = R < Rb ? q * q * q - 2 : -1 / (q * q * q);
        return Ab * std::cos(2 * (std::atan2(y, x) - angleBarre(t))) * U;
    }
};

// Orbites d'un ensemble d'étoiles. Positions et vitesses galactocentriques (kpc, km/s) à t = 0 ; avance(t) les porte à t
// (sur plusieurs fils d'exécution) ; positions() les lit. Une instance n'est pas partagée entre fils pendant avance().
class Orbites {
public:
    Orbites() = default;
    Orbites(std::span<const Vec3> pos, std::span<const Vec3> vit, Potentiel P = {}) : P_(P), t_(0) {
        const size_t n = pos.size(); X_.resize(3 * n); V_.resize(3 * n); sub_.resize(n);
        for (size_t k = 0; k < n; k++) { X_[3 * k] = pos[k].x; X_[3 * k + 1] = pos[k].y; X_[3 * k + 2] = pos[k].z; V_[3 * k] = vit[k].x; V_[3 * k + 1] = vit[k].y; V_[3 * k + 2] = vit[k].z; sub_[k] = sousPas(k); }
    }
    double temps() const { return t_; }
    size_t taille() const { return sub_.size(); }
    // Avance jusqu'à tGa (arrondi au pas de 1 Ma ; vers le passé si tGa < temps()).
    void avance(double tGa, unsigned fils = std::thread::hardware_concurrency()) {
        const long n = std::lround((tGa - t_) / kDtGa); if (n == 0) return;
        const double dt = n > 0 ? kDtGa : -kDtGa; const long steps = n > 0 ? n : -n;
        if (fils < 1) fils = 1; const size_t N = sub_.size(), part = (N + fils - 1) / fils;
        std::vector<std::thread> th;
        for (unsigned f = 0; f < fils; f++) { const size_t a = f * part, b = std::min(N, a + part); if (a >= b) break; th.emplace_back([=, this] { pas(a, b, dt, steps, t_); }); }
        for (auto& x : th) x.join();
        t_ += steps * dt;
    }
    // Positions (kpc) de toutes les étoiles au temps courant.
    void positions(std::span<Vec3> out) const { for (size_t k = 0; k < sub_.size() && k < out.size(); k++) out[k] = {X_[3 * k], X_[3 * k + 1], X_[3 * k + 2]}; }
    Vec3 position(size_t k) const { return {X_[3 * k], X_[3 * k + 1], X_[3 * k + 2]}; }
    Vec3 vitesse(size_t k) const { return {V_[3 * k], V_[3 * k + 1], V_[3 * k + 2]}; }
    const Potentiel& potentiel() const { return P_; }

private:
    Potentiel P_;
    double t_ = 0;
    std::vector<double> X_, V_;
    std::vector<uint8_t> sub_;

    // Sous-pas d'après le péricentre estimé (potentiel pris dans le plan) : sous 0,7 kpc : 32 ; 2 kpc : 8 ; 4 kpc : 2 ; sinon 1.
    uint8_t sousPas(size_t k) const {
        const double x = X_[3 * k], y = X_[3 * k + 1], z = X_[3 * k + 2], vx = V_[3 * k], vy = V_[3 * k + 1], vz = V_[3 * k + 2], E = P_.energie(x, y, z, vx, vy, vz);
        const double L2 = std::pow(y * vz - z * vy, 2) + std::pow(z * vx - x * vz, 2) + std::pow(x * vy - y * vx, 2);
        auto f = [&](double r) { return 2 * (E - P_.energie(r, 0, 0, 0, 0, 0)) * r * r - L2; };
        double lo = 1e-3, hi = std::max(std::sqrt(x * x + y * y + z * z), 2e-3);
        if (f(lo) < 0) { for (int it = 0; it < 40; it++) { const double m = 0.5 * (lo + hi); if (f(m) < 0) lo = m; else hi = m; } } else hi = lo;
        return hi < 0.7 ? 32 : hi < 2 ? 8 : hi < 4 ? 2 : 1;
    }
    void pas(size_t a, size_t b, double dt, long steps, double t0) {
        double acc[3];
        for (long s = 0; s < steps; s++) for (size_t k = a; k < b; k++) {
            const int m = sub_[k]; const double h = dt * kKmsKpcToRadGa / m; double* X = &X_[3 * k]; double* V = &V_[3 * k];
            for (int u = 0; u < m; u++) {
                const double ta = t0 + (s + double(u) / m) * dt, tb = ta + dt / m;
                P_.acc(X[0], X[1], X[2], ta, acc); for (int c = 0; c < 3; c++) V[c] += 0.5 * h * acc[c];
                for (int c = 0; c < 3; c++) X[c] += h * V[c];
                P_.acc(X[0], X[1], X[2], tb, acc); for (int c = 0; c < 3; c++) V[c] += 0.5 * h * acc[c];
            }
        }
    }
};

// Le Soleil dans ce repère, à t = 0.
inline Vec3 soleilPos() { return {-kSgra[0] * kR0, -kSgra[1] * kR0, -kSgra[2] * kR0}; }
inline Vec3 soleilVit() { return {kSunUvw[0], kSunUvw[1], kSunUvw[2]}; }

}  // namespace phys::galaxie
