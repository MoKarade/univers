// Appli PC « Univers », bibliothèque univers_physique : ce que la simulation lit d'un film du Groupe local, qu'il soit au
// format 2 (film_v2.h) ou 3 (film_v3.h) : ses bornes et le centre de chaque galaxie.
//
// finSureGa : dernière date où tout le film est là. Format 2 : l'avant-dernière image (la dernière peut être en cours
// d'écriture). Format 3 : la dernière image P, que le lecteur n'accepte que complète.
// centreEtoiles : le centre auquel les positions écrites des étoiles sont relatives. Format 2 : la courbe des centres
// passée par les images (film_v2.h). Format 3 : le centre de l'index par Hermite, le même que centre().
#pragma once
#include "film_v2.h"
#include "film_v3.h"

namespace phys::film {

struct FilmVue {
    const FilmV2* v2 = nullptr;
    const FilmV3* v3 = nullptr;

    explicit operator bool() const { return v2 || v3; }
    // Assez d'images pour que le film mène (format 2 : cinq images, pour les quatre voisines de Catmull-Rom).
    bool pret() const { return v2 ? v2->images() >= 5 : v3 != nullptr; }
    int galaxies() const { return v2 ? v2->galaxies() : v3 ? v3->galaxies() : 0; }
    double debutGa() const { return v2 ? v2->debutGa() : v3 ? v3->debutGa() : 0; }
    double finSureGa() const {
        if (v2) return v2->images() >= 2 ? v2->date(v2->images() - 2) : v2->debutGa();
        return v3 ? v3->finGa() : 0;
    }
    bool couvre(double tGa) const { return pret() && tGa >= debutGa() && tGa <= finSureGa(); }
    bool centre(int g, double tGa, Vec3& out) const { return v2 ? v2->centre(g, tGa, out) : v3 && v3->centre(g, tGa, out); }
    bool centreEtoiles(int g, double tGa, Vec3& out) const { return v2 ? v2->centreEtoiles(g, tGa, out) : v3 && v3->centre(g, tGa, out); }
};

}  // namespace phys::film
