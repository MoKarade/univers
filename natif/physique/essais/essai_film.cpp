// Contrôle de film_v2.h (lecteur du film version 2 du Groupe local).
// Vérifie la lecture des nombres sur 16 bits, que l'image de t = 0 est rendue telle quelle (aucun mélange à une date
// d'image), que la courbe entre deux images passe bien par elles, que le centre d'une galaxie suit ses vitesses, et que
// rien n'est rendu hors du film.
// Usage : essai_film <dossier du film>      (au moins 4 images)
#include <cmath>
#include <cstdio>
#include <vector>

#include "film_v2.h"

using namespace phys::film;
static int g_fail = 0;
static void ok(bool c, const char* fmt, double a = 0, double b = 0) { std::printf("%s ", c ? "PASSE" : "ECHEC"); std::printf(fmt, a, b); std::printf("\n"); if (!c) g_fail++; }

int main(int argc, char** argv) {
    ok(demiVersFloat(0x3C00) == 1.0f && demiVersFloat(0xC000) == -2.0f && demiVersFloat(0x3800) == 0.5f && demiVersFloat(0x0000) == 0.0f && demiVersFloat(0x0001) > 0.0f,
       "nombres sur 16 bits : 1, -2, 0,5, 0 et le plus petit");
    if (argc < 2) { std::printf("usage : essai_film <dossier du film>\n"); return 2; }
    FilmV2 f;
    if (!f.charger(argv[1])) { std::printf("ECHEC : film illisible (film_index.bin) dans %s\n", argv[1]); return 1; }
    std::printf("film : %d images de %+.3f a %+.3f Ga, %d galaxies, %llu etoiles visibles\n", f.images(), f.debutGa(), f.finGa(), f.galaxies(), (unsigned long long)f.total());
    ok(f.images() >= 4 && f.galaxies() >= 1 && f.total() > 0, "au moins 4 images et des etoiles");
    if (g_fail) return 1;
    const uint64_t n = std::min<uint64_t>(f.etoiles(0), 200000);
    std::vector<float> a(3 * n), b(3 * n);
    // 1. À la date d'une image, on rend exactement cette image.
    for (int i : {0, 1, f.images() - 1}) {
        const uint16_t* brut = f.image(i);
        bool lu = brut && f.positions(0, f.date(i), a, 0, n);
        double pire = 0;
        for (size_t c = 0; lu && c < 3 * n; ++c) pire = std::fmax(pire, std::fabs(a[c] - demiVersFloat(brut[c])));
        ok(lu && pire < 1e-4, "image %g : rendue telle quelle a sa date (ecart %.2g kpc)", i, pire);
    }
    // 2. Entre deux images : la courbe reste entre les positions voisines à mieux qu'un déplacement d'image près.
    {
        const double tm = 0.5 * (f.date(1) + f.date(2));
        const bool lu = f.positions(0, tm, a, 0, n) && f.positions(0, f.date(1), b, 0, n);
        std::vector<float> c(3 * n); const bool lu2 = f.positions(0, f.date(2), c, 0, n);
        double pas = 0, ecart = 0;
        for (size_t k = 0; lu && lu2 && k < 3 * n; ++k) { pas = std::fmax(pas, std::fabs(c[k] - b[k])); ecart = std::fmax(ecart, std::fabs(a[k] - 0.5f * (b[k] + c[k]))); }
        ok(lu && lu2 && ecart <= pas, "milieu entre deux images : a moins d'un deplacement d'image de leur moyenne (%.3g contre %.3g kpc)", ecart, pas);
    }
    // 3. Centres : exacts aux dates des images, et la vitesse tirée de la courbe est celle du film.
    {
        const int g = f.galaxies() > 1 ? 1 : 0;
        phys::Vec3 c0, c1, c2;
        const double t1 = f.date(1), h = 1e-4;
        const bool lu = f.centre(g, t1, c0) && f.centre(g, t1 + h, c1) && f.centre(g, f.date(2), c2);
        const double v = std::sqrt(std::pow(c1.x - c0.x, 2) + std::pow(c1.y - c0.y, 2) + std::pow(c1.z - c0.z, 2)) / h * FilmV2::kKpcGaEnKms;
        ok(lu && std::isfinite(v) && v < 2000, "centre de la galaxie 1 : vitesse tiree de la courbe %.1f km/s", v);
        phys::Vec3 hors;
        ok(!f.centre(g, f.finGa() + 0.001, hors) && !f.centre(g, f.debutGa() - 0.001, hors) && !f.positions(0, f.finGa() + 0.001, a, 0, n), "hors du film : rien n'est rendu");
    }
    std::printf(g_fail ? "ECHEC (%d)\n" : "PASSE\n", g_fail);
    return g_fail ? 1 : 0;
}
