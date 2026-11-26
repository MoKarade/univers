// Appli PC « Univers » : ancres des galaxies voisines dans le film du Groupe local (pipeline/natif/ancres_film.py).
//
// L'ancre est le point que suivent l'étiquette et la caméra : le cœur de la galaxie tant qu'elle en a un, puis, sans
// bascule, le barycentre de ses étoiles quand elle se disperse dans la Voie lactée (choix d'affichage, dit dans le script).
// La part groupée (étoiles à moins de deux rayons médians du cœur) est montrée dans le panneau. Sans ce fichier, ou hors
// des images qu'il couvre, l'appli garde le centre écrit par le calcul.
//
// Fichier film_ancres.bin : « UNIVANC1 », images n (u32), galaxies g (u32), puis par image et par galaxie 7 f64 :
// ancre x, y, z (kpc, repère du film), part groupée, barycentre x, y, z.
#pragma once
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

#include "film_v2.h"

namespace univers {

struct FilmAnchors {
    bool ready = false;
    int n = 0, g = 0;
    std::vector<double> v;      // n x g x 7

    // Le film doit être celui des ancres : même nombre de galaxies, et les ancres ne couvrent pas plus d'images que lui.
    bool load(const std::string& path, const phys::film::FilmV2& film) {
        std::ifstream f(path, std::ios::binary);
        char head[16] = {};
        if (!f.read(head, 16) || std::memcmp(head, "UNIVANC1", 8) != 0) return false;
        uint32_t nn = 0, gg = 0;
        std::memcpy(&nn, head + 8, 4);
        std::memcpy(&gg, head + 12, 4);
        if (nn < 4 || static_cast<int>(gg) != film.galaxies() || static_cast<int>(nn) > film.images()) return false;
        v.resize(static_cast<size_t>(nn) * gg * 7);
        if (!f.read(reinterpret_cast<char*>(v.data()), static_cast<std::streamsize>(v.size() * 8))) return false;
        n = static_cast<int>(nn);
        g = static_cast<int>(gg);
        ready = true;
        return true;
    }

    // Ancre (kpc) et part groupée de la galaxie k à tGa, par la courbe des images voisines (Catmull-Rom, comme les étoiles).
    bool at(const phys::film::FilmV2& film, int k, double tGa, phys::Vec3& out, double* grouped = nullptr) const {
        if (!ready || k <= 0 || k >= g || n < 4 || tGa < film.date(0) || tGa > film.date(n - 2)) return false;
        int i = 0;
        while (i + 2 < n && film.date(i + 1) <= tGa) ++i;
        const double span = film.date(i + 1) - film.date(i), u = std::clamp((tGa - film.date(i)) / span, 0.0, 1.0);
        const double u2 = u * u, u3 = u2 * u;
        const double w[4] = {0.5 * (-u + 2 * u2 - u3), 0.5 * (2 - 5 * u2 + 3 * u3), 0.5 * (u + 4 * u2 - 3 * u3), 0.5 * (-u2 + u3)};
        const int idx[4] = {std::max(i - 1, 0), i, i + 1, std::min(i + 2, n - 1)};
        out = {0, 0, 0};
        double f = 0;
        for (int j = 0; j < 4; ++j) {
            const double* a = &v[(static_cast<size_t>(idx[j]) * g + k) * 7];
            out.x += w[j] * a[0];
            out.y += w[j] * a[1];
            out.z += w[j] * a[2];
            f += w[j] * a[3];
        }
        if (grouped) *grouped = std::clamp(f, 0.0, 1.0);
        return true;
    }
};

}  // namespace univers