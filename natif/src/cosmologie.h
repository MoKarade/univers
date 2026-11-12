// Appli PC « Univers » : distances dans l'univers en expansion (équations de Friedmann).
//
// Mêmes hypothèses que la page (20_physics.js, buildCosmo) : matière, rayonnement (photons à 2,7255 K et 3,046
// neutrinos sans masse : Omega_r h² = 4,1837e-5), courbure Omega_k = 1 - Omega_m - Omega_de - Omega_r, et énergie
// noire. En plus de la page : énergie noire qui varie, w(a) = w0 + wa (1 - a) (Chevallier et Polarski 2001 ;
// Linder 2003), dont la densité vaut rho(a) / rho(1) = a^(-3 (1 + w0 + wa)) exp(-3 wa (1 - a)).
// Distance à cet instant d'un objet de décalage vers le rouge z (distance comobile transverse) :
//   chi = (c / H0) * intégrale de 0 à z de dz' / E(z'),  puis sinus ou sinus hyperbolique si l'espace est courbe.
#pragma once
#include <cmath>
#include <vector>

namespace cosmo {

constexpr double kCKms = 299792.458;
constexpr double kOmegaRH2 = 4.1837e-5;
constexpr double kMpcInLy = 3.0856775814913673e22 / 9.4607304725808e15;

struct Params {
    double h0 = 67.4;      // km/s/Mpc (Planck 2018, comme la page)
    double om = 0.315;
    double ode = 0.685;
    double w0 = -1.0;
    double wa = 0.0;
    double omegaR() const { return kOmegaRH2 / ((h0 / 100.0) * (h0 / 100.0)); }
    double omegaK() const { return 1.0 - om - ode - omegaR(); }
    // E(z) = H(z) / H0
    double e(double z) const {
        const double a = 1.0 / (1.0 + z), x = 1.0 + z;
        const double de = ode * std::pow(a, -3.0 * (1.0 + w0 + wa)) * std::exp(-3.0 * wa * (1.0 - a));
        return std::sqrt(std::max(omegaR() * x * x * x * x + om * x * x * x + omegaK() * x * x + de, 1e-30));
    }
};

// Table de la distance comobile transverse (Mpc) pour z = exp(u * ln(1 + zMax)) - 1, u de 0 à 1 en `steps` pas égaux.
// Intégration par la règle de Simpson, variable ln(1 + z) (l'intégrande y est lisse), 8 sous-pas par pas de table.
inline std::vector<double> distanceTable(const Params& p, double zMax, int steps) {
    std::vector<double> out(static_cast<size_t>(steps) + 1, 0.0);
    const double lz = std::log(1.0 + zMax), dh = kCKms / p.h0;
    auto f = [&](double s) { const double x = std::exp(s); return x / p.e(x - 1.0); };      // dz = (1 + z) ds
    double chi = 0.0;
    const int sub = 8;
    for (int k = 1; k <= steps; ++k) {
        const double s0 = lz * (k - 1) / steps, h = lz / steps / sub;
        for (int j = 0; j < sub; j += 2) chi += h / 3.0 * (f(s0 + j * h) + 4.0 * f(s0 + (j + 1) * h) + f(s0 + (j + 2) * h));
        const double ok = p.omegaK(), c = chi * dh;
        double dm = c;
        if (ok > 1e-9) dm = dh / std::sqrt(ok) * std::sinh(std::sqrt(ok) * chi);
        else if (ok < -1e-9) dm = dh / std::sqrt(-ok) * std::sin(std::sqrt(-ok) * chi);
        out[static_cast<size_t>(k)] = dm;
    }
    return out;
}

// Âge de l'univers aujourd'hui, en milliards d'années : intégrale de da / (a H(a)) de 0 à 1.
inline double ageGyr(const Params& p) {
    const int n = 20000;
    double sum = 0.0;
    auto f = [&](double a) { return a <= 0 ? 0.0 : 1.0 / (a * p.e(1.0 / a - 1.0)); };
    for (int i = 0; i < n; i += 2) {
        const double h = 1.0 / n;
        sum += h / 3.0 * (f(i * h) + 4.0 * f((i + 1) * h) + f((i + 2) * h));
    }
    return sum * 977.7922216807891 / p.h0;      // 1 / (1 km/s/Mpc) = 977,79 milliards d'années
}

}  // namespace cosmo
