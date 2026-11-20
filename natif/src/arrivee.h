// Appli PC « Univers » : distance d'arrivée de la caméra sur une grande structure (audit B3, 20/11/2026).
// Sans dépendance au reste de l'appli, pour être contrôlée par essai_interface.
#pragma once
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <string>

namespace arrivee {

constexpr double kMpcLy = 3.2615638e6;      // années-lumière par mégaparsec
constexpr double kH = 0.674;                // h de Planck 2018, comme cosmologie.h
constexpr double kDefautLy = 3.0e8;         // taille supposée d'une structure dont la description ne donne pas la taille

// Diamètre d'une structure (années-lumière), lu dans sa description (structures_noms.tsv, superstructures_noms.tsv) :
// « N millions de (Mpc/h)³ » (volume d'un bassin : diamètre de la sphère de même volume), « rayon N Mpc/h » (vide),
// « N milliards d’années-lumière » (superstructure). Sinon kDefautLy.
inline double structureSizeLy(const std::string& text) {
    auto numberBefore = [&](const std::string& key, double& v) {
        const size_t k = text.find(key);
        if (k == std::string::npos || k == 0) return false;
        size_t a = k;
        while (a > 0 && (std::isdigit(static_cast<unsigned char>(text[a - 1])) || text[a - 1] == '.' || text[a - 1] == ' ')) --a;
        v = std::atof(text.substr(a, k - a).c_str());
        return v > 0;
    };
    double v = 0;
    if (numberBefore("millions de (Mpc/h)", v)) return 2.0 * std::cbrt(3.0 * v * 1.0e6 / (4.0 * 3.14159265358979)) / kH * kMpcLy;
    if (const size_t k = text.find("rayon "); k != std::string::npos) {
        v = std::atof(text.c_str() + k + 6);
        if (v > 0 && text.find("Mpc/h", k) != std::string::npos) return 2.0 * v / kH * kMpcLy;
    }
    if (numberBefore("milliards d", v)) return v * 1.0e9;
    return kDefautLy;
}

}  // namespace arrivee
