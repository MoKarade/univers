// Appli PC « Univers » : déviation de la lumière par une masse (relativité générale), calcul pur, sans carte graphique.
// Utilisé par lentille.h (image) et essai_lentille.cpp (contrôle).
#pragma once
#include <algorithm>
#include <cmath>

namespace lentille {

constexpr double kPiD = 3.14159265358979323846;
constexpr double kGmSunOverC2M = 1476.6250;      // G M☉ / c², mètres (IAU 2015 B3 : GM☉ nominal / c²)

// Champ faible, source à l'infini, observateur à la distance D de la masse (G M / c² en mêmes unités) : angle de déviation
// vu par l'observateur pour une direction à l'angle chi de la masse (formule utilisée par Gaia : Klioner 2003).
inline double weakDeflection(double gmOverC2, double D, double chi) { return 2.0 * gmOverC2 / D * (1.0 + std::cos(chi)) / std::sin(chi); }

// Déviation d'un rayon remonté depuis une caméra à r0 (en G M / c²), qui part à l'angle chi de la direction du trou noir.
// Rend la déviation alpha (angle d'arrivée - angle de départ, voir lentille.frag) ou -1 si la lumière est capturée.
inline double traceRay(double r0, double chi) {
    const double s = std::sin(chi);
    const double b = r0 * s / std::sqrt(1.0 - 2.0 / r0);      // paramètre d'impact (observateur immobile)
    double u = 1.0 / r0;
    const double v2 = 1.0 / (b * b) - u * u * (1.0 - 2.0 * u);
    if (v2 < 0) return -1;
    double v = (chi < kPiD / 2 ? 1.0 : -1.0) * std::sqrt(std::max(v2, 0.0));      // du/dphi : vers le trou noir si chi < 90°
    double phi = 0;
    auto f = [](double uu) { return -uu + 3.0 * uu * uu; };
    for (int it = 0; it < 2000000; ++it) {
        const double h = 0.002;      // pas en angle (radians) : erreur du schéma bien sous un millième de pixel
        const double k1u = v, k1v = f(u);
        const double k2u = v + 0.5 * h * k1v, k2v = f(u + 0.5 * h * k1u);
        const double k3u = v + 0.5 * h * k2v, k3v = f(u + 0.5 * h * k2u);
        const double k4u = v + h * k3v, k4v = f(u + h * k3u);
        const double un = u + h / 6.0 * (k1u + 2 * k2u + 2 * k3u + k4u);
        const double vn = v + h / 6.0 * (k1v + 2 * k2v + 2 * k3v + k4v);
        if (un >= 0.5) return -1;      // horizon : capturée
        if (un <= 0) {      // partie à l'infini : angle d'arrivée par interpolation
            const double esc = phi + h * u / (u - un);
            return esc - (kPiD - chi);
        }
        u = un;
        v = vn;
        phi += h;
        if (phi > 12.0 * kPiD) return -1;      // tourne sans fin autour du trou noir : compté comme capturé
    }
    return -1;
}

}  // namespace lentille
