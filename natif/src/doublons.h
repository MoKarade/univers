// Appli PC « Univers » : étoiles en double entre le catalogue principal (rangs 0 à 58 966 d'etoiles.bin) et la partie Gaia
// du même fichier, repérées par la liste des hôtes d'exoplanètes (signalé le 20/11/2026 : « Proxima du Centaure », rang
// 34 913, et « Proxima Cen », rang 73 736, étaient deux étoiles, deux points et deux fiches ; ses planètes étaient sous la
// seconde). Le repérage du pipeline (moins de 0,02 al) manque les étoiles proches à grand mouvement propre.
//
// Règle : un hôte de la partie Gaia est le double d'une étoile du catalogue principal si elle est à moins de 0,3 al de lui,
// à moins de 50 al du Soleil, et si sa magnitude Gaia (G, absolue) n'est pas plus faible que la magnitude V du catalogue
// principal + 0,3 (G est plus brillante que V pour ces étoiles rouges ; une étoile plus faible est un compagnon, comme
// ups And B). Contrôlé le 20/11 : 13 doubles parmi 2 208 hôtes (Proxima, Ross 128, GJ 15 A, YZ Cet, Wolf 1061, GJ 9066,
// GJ 876, GJ 251, GJ 896 A, GJ 625, GJ 393, Gl 686, GJ 680).
#pragma once
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <string>
#include <unordered_map>

namespace doublons {

constexpr int64_t kPrincipal = 58967;      // taille du catalogue principal (etoiles.json)

// rang Gaia du double -> rang dans le catalogue principal ; x, y, z, mag : colonnes d'etoiles.bin (n étoiles)
inline std::unordered_map<int64_t, int64_t> hotes(const float* x, const float* y, const float* z, const float* mag, uint64_t n,
                                                 const std::string& hostsPath) {
    std::unordered_map<int64_t, int64_t> out;
    std::ifstream f(hostsPath);
    for (std::string line; std::getline(f, line);) {
        const int64_t g = std::strtoll(line.c_str(), nullptr, 10);
        if (g < kPrincipal || static_cast<uint64_t>(g) >= n) continue;
        const double r = std::sqrt(double(x[g]) * x[g] + double(y[g]) * y[g] + double(z[g]) * z[g]);
        if (r > 50.0) continue;
        int64_t best = -1;
        double bd = 0.3 * 0.3;
        for (int64_t k = 0; k < kPrincipal && static_cast<uint64_t>(k) < n; ++k) {
            const double dx = double(x[k]) - x[g], dy = double(y[k]) - y[g], dz = double(z[k]) - z[g];
            const double d2 = dx * dx + dy * dy + dz * dz;
            if (d2 < bd) { bd = d2; best = k; }
        }
        if (best >= 0 && mag[g] <= mag[best] + 0.3) out[g] = best;
    }
    return out;
}

}  // namespace doublons
