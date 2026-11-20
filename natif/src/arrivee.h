// Appli PC « Univers » : distance d'arrivée de la caméra sur une grande structure (audit B3, 20/11/2026).
// Sans dépendance au reste de l'appli, pour être contrôlée par essai_interface.
#pragma once
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <string>

namespace arrivee {

constexpr double kMpcLy = 3.2615638e6;      // années-lumière par mégaparsec
constexpr double kH = 0.674;                // h de Planck 2018, comme cosmologie.h
constexpr double kDefautLy = 3.0e8;         // taille supposée d'une structure dont la description ne donne pas la taille

// Diamètre d'une structure (années-lumière), lu dans sa description (structures_noms.tsv, superstructures_noms.tsv) :
// « N millions de (Mpc/h)³ » (volume d'un bassin : diamètre de la sphère de même volume), « rayon N Mpc/h » (vide), ou,
// après « taille publiée : », « N milliard(s) d'années-lumière » ou la plus grande valeur « N h^-1 Mpc ». Le nombre
// « N milliards d’années-lumière » placé plus loin dans les superstructures est leur DISTANCE, jamais lu ici. Sinon kDefautLy.
inline double structureSizeLy(const std::string& text) {
    // nombre (chiffres et point) collé avant la position k, espaces sautés ; 0 si aucun
    auto numberEndingAt = [&](size_t k) {
        while (k > 0 && text[k - 1] == ' ') --k;
        size_t a = k;
        while (a > 0 && (std::isdigit(static_cast<unsigned char>(text[a - 1])) || text[a - 1] == '.')) --a;
        return a < k ? std::atof(text.substr(a, k - a).c_str()) : 0.0;
    };
    if (const size_t k = text.find("millions de (Mpc/h)"); k != std::string::npos) {
        const double v = numberEndingAt(k);
        if (v > 0) return 2.0 * std::cbrt(3.0 * v * 1.0e6 / (4.0 * 3.14159265358979)) / kH * kMpcLy;
    }
    if (const size_t k = text.find("rayon "); k != std::string::npos) {
        char* end = nullptr;
        const double v = std::strtod(text.c_str() + k + 6, &end);
        if (v > 0 && end && std::string(end).rfind(" Mpc/h", 0) == 0) return 2.0 * v / kH * kMpcLy;
    }
    const size_t t = text.find("taille publiée :");
    if (t != std::string::npos) {
        const size_t stop = text.find(';', t);
        const std::string part = text.substr(t, stop == std::string::npos ? std::string::npos : stop - t);
        if (const size_t k = part.find(" milliard"); k != std::string::npos) {
            const size_t a = t + k;
            const double v = numberEndingAt(a);
            if (v > 0) return v * 1.0e9;
        }
        double best = 0;
        for (size_t k = part.find("h^-1 Mpc"); k != std::string::npos; k = part.find("h^-1 Mpc", k + 1)) best = std::max(best, numberEndingAt(t + k));
        if (best > 0) return best / kH * kMpcLy;
        // « 420 Mpc », « au moins 200 Mpc » (sans h) : nombre précédé d'une espace, suivi de « Mpc »
        for (size_t k = part.find(" Mpc"); k != std::string::npos; k = part.find(" Mpc", k + 1)) {
            size_t a = k;
            while (a > 0 && (std::isdigit(static_cast<unsigned char>(part[a - 1])) || part[a - 1] == '.')) --a;
            if (a < k && a > 0 && part[a - 1] == ' ') best = std::max(best, std::atof(part.substr(a, k - a).c_str()));
        }
        if (best > 0) return best * kMpcLy;
    }
    return kDefautLy;
}

}  // namespace arrivee
