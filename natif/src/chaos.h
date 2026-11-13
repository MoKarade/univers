// Appli PC « Univers » : la Terre au-delà de la table des orbites (±10 millions d'années), d'après le calcul du chaos du
// système solaire du fil physique (natif/physique/essais/chaos_systeme_solaire.cpp, docs/plan-precalcul.md).
//
// Fichier chaos_futur_60ma.bin (« UNIVCHA1 ») : 32 copies du système solaire parties de l'état JPL du 10/11/2026, la
// Terre-Lune écartée de 15 m dans 31 d'entre elles, suivies 60 millions d'années ; un échantillon tous les 10 000 ans :
// excentricité e, longitude du périhélie ϖ, longitude héliocentrique λ et inclinaison de la Terre-Lune (écliptique J2000).
// Ce qu'on en tire, sans rien ajouter :
//  - forme et orientation de l'orbite de la Terre-Lune (e, ϖ) d'après la copie 0 (départ exact), tracée dans le plan
//    de l'écliptique avec a = 1 UA [demi-grand axe non stocké ; nœud non stocké : plan incliné de quelques degrés au plus,
//    dit à l'écran] ; la position sur l'orbite n'est PAS donnée (un échantillon tous les 10 000 ans seulement) ;
//  - incertitude : écart (moyenne circulaire) de λ entre les 32 copies à cette date ;
//  - horizon : au-delà de 45 millions d'années, la position sur l'orbite n'est plus prévisible (écart ≥ 1 rad, mesuré) ;
//    au-delà d'environ 60 millions d'années, l'orbite elle-même non plus.
#pragma once
#include <cmath>
#include <cstdint>
#include <fstream>
#include <string>
#include <vector>

namespace chaos {

constexpr double kPositionHorizonYears = 45.0e6;      // mesuré par les copies (plan-precalcul.md)
constexpr double kOrbitHorizonYears = 60.0e6;
constexpr double kStartYears = 2026.0 + (314.0 - 0.5) / 365.25;      // 10 novembre 2026, départ du calcul (années depuis l'an 0)

class Run {
public:
    bool load(const std::string& path) {
        std::ifstream f(path, std::ios::binary);
        char magic[8];
        uint32_t n = 0, m = 0;
        int32_t sens = 0;
        double ecart = 0;
        if (!f.read(magic, 8) || std::string(magic, 8) != "UNIVCHA1") return false;
        f.read(reinterpret_cast<char*>(&n), 4).read(reinterpret_cast<char*>(&m), 4).read(reinterpret_cast<char*>(&step_), 8);
        f.read(reinterpret_cast<char*>(&sens), 4).read(reinterpret_cast<char*>(&ecart), 8);
        if (!f || n == 0 || m == 0 || step_ <= 0 || sens != 1) return false;
        data_.resize(static_cast<size_t>(n) * m * 6);
        if (!f.read(reinterpret_cast<char*>(data_.data()), static_cast<std::streamsize>(data_.size() * sizeof(double)))) return false;
        n_ = n;
        m_ = m;
        return true;
    }
    bool ready() const { return n_ > 0; }
    double spanYears() const { return (m_ - 1) * step_; }

    // Orbite de la Terre-Lune à `after` années après le départ (copie 0, interpolée entre deux échantillons : e et ϖ
    // varient lentement) et écart de sa position sur l'orbite entre les copies (rad, à l'échantillon le plus proche).
    // La position elle-même n'est pas donnée : le calcul n'en garde qu'un point tous les 10 000 ans.
    bool orbit(double after, double& e, double& w, double& spreadRad) const {
        if (!ready() || after < 0 || after > std::min(kOrbitHorizonYears, spanYears())) return false;
        const double u = after / step_;
        const size_t j0 = std::min(static_cast<size_t>(u), m_ - 1), j1 = std::min(j0 + 1, m_ - 1);
        const double f = u - static_cast<double>(j0);
        const double* a = &data_[j0 * n_ * 6];
        const double* b = &data_[j1 * n_ * 6];
        e = a[0] * (1 - f) + b[0] * f;
        double dw = std::remainder(b[1] - a[1], 2 * 3.14159265358979323846);
        w = a[1] + f * dw;
        const size_t j = f < 0.5 ? j0 : j1;
        double sx = 0, sy = 0;
        for (size_t k = 0; k < n_; ++k) {
            sx += std::cos(data_[(j * n_ + k) * 6 + 2]);
            sy += std::sin(data_[(j * n_ + k) * 6 + 2]);
        }
        const double rbar = std::sqrt(sx * sx + sy * sy) / static_cast<double>(n_);
        spreadRad = std::sqrt(std::max(0.0, -2.0 * std::log(std::max(rbar, 1e-12))));      // écart circulaire entre les copies
        return true;
    }
private:
    std::vector<double> data_;
    size_t n_ = 0, m_ = 0;
    double step_ = 0;
};

}  // namespace chaos
