// Précision MESURÉE de la méthode des épicycles (orbite_galactique.h, celle de la carte graphique) sur les vraies étoiles
// d'etoiles.bin : écart avec l'intégration exacte du fil physique (phys::galaxie::Orbites, même potentiel), à ±10, ±100 et
// ±500 millions d'années. Les deux calculs partent de la même position et de la même vitesse mesurées : l'écart est celui
// de la méthode seule, pas celui des mesures.
//
// Échantillon : étoiles tirées au hasard (graine fixe) parmi celles qui ont une vitesse dans le fichier.
// Classes, d'après l'écart de la vitesse de l'étoile à la vitesse circulaire de son lieu : « disque » sous 50 km/s,
// « chaud » au-delà (halo, disque épais, étoiles rapides).
// Sortie : distributions (médiane, 90 %, 99 %, maximum) de l'écart de position (kpc) et de l'écart d'angle autour du
// centre (degrés), avec et sans la barre centrale dans le calcul exact. Code de sortie 0 si le fichier a été lu.
// Usage : essai_epicycles <etoiles.bin> [taille de l'échantillon, 20000 par défaut]
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <random>
#include <string>
#include <vector>

#include "orbite_galactique.h"

namespace {
struct Etoiles {
    std::vector<float> x, y, z, vx, vy, vz;
};
bool lire(const char* chemin, Etoiles& e) {
    std::ifstream f(chemin, std::ios::binary);
    char tete[64];
    if (!f.read(tete, 64) || std::string(tete, 8) != "UNIVSTR1") return false;
    int64_t n = 0;
    std::memcpy(&n, tete + 8, 8);
    const auto col = [&](int k, std::vector<float>& out) {
        const int64_t octets = n * 4, pas = (octets + 63) / 64 * 64;
        out.resize(n);
        f.seekg(64 + k * pas);
        return bool(f.read(reinterpret_cast<char*>(out.data()), octets));
    };
    return col(0, e.x) && col(1, e.y) && col(2, e.z) && col(5, e.vx) && col(6, e.vy) && col(7, e.vz);      // 3 = mag, 4 = B-V
}
double angle(phys::Vec3 a, phys::Vec3 b) {
    double d = std::atan2(a.y, a.x) - std::atan2(b.y, b.x);
    while (d > phys::galaxie::kPi) d -= 2 * phys::galaxie::kPi;
    while (d < -phys::galaxie::kPi) d += 2 * phys::galaxie::kPi;
    return std::fabs(d) * 180 / phys::galaxie::kPi;
}
void ligne(const char* quoi, std::vector<double> v, const char* unite) {
    if (v.empty()) return;
    std::sort(v.begin(), v.end());
    const auto q = [&](double p) { return v[std::min(v.size() - 1, size_t(p * (v.size() - 1) + 0.5))]; };
    std::printf("    %-22s médiane %8.3g  90 %% %8.3g  99 %% %8.3g  max %8.3g %s\n", quoi, q(0.5), q(0.9), q(0.99), v.back(), unite);
}
}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) { std::printf("usage : essai_epicycles <etoiles.bin> [taille]\n"); return 2; }
    Etoiles e;
    if (!lire(argv[1], e)) { std::printf("ECHEC : lecture de %s\n", argv[1]); return 1; }
    const size_t taille = argc > 2 ? std::stoul(argv[2]) : 20000;
    std::vector<size_t> avecVitesse;
    for (size_t k = 0; k < e.x.size(); ++k)
        if (e.vx[k] != 0 || e.vy[k] != 0 || e.vz[k] != 0) avecVitesse.push_back(k);
    std::printf("%zu étoiles, dont %zu avec une vitesse ; échantillon de %zu\n", e.x.size(), avecVitesse.size(), std::min(taille, avecVitesse.size()));
    std::mt19937_64 hasard(20261112);
    std::shuffle(avecVitesse.begin(), avecVitesse.end(), hasard);
    avecVitesse.resize(std::min(taille, avecVitesse.size()));

    namespace g = phys::galaxie;
    const phys::Vec3 s = g::soleilPos(), sv = g::soleilVit();
    std::vector<phys::Vec3> P, V;
    std::vector<char> chaud;
    double dMax = 0;
    for (size_t k : avecVitesse) {
        const phys::Vec3 pg = orbite::versGalactique({e.x[k], e.y[k], e.z[k]}), vg = orbite::versGalactique({e.vx[k], e.vy[k], e.vz[k]});
        const phys::Vec3 p{pg.x / orbite::kKpcLy + s.x, pg.y / orbite::kKpcLy + s.y, pg.z / orbite::kKpcLy + s.z}, v{vg.x + sv.x, vg.y + sv.y, vg.z + sv.z};
        P.push_back(p); V.push_back(v);
        dMax = std::max(dMax, std::hypot(pg.x, pg.y, pg.z) / orbite::kKpcLy);
        const double R = std::max(std::hypot(p.x, p.y), 1e-6), vc = g::frequences(R).vc;
        const double vt = (p.x * v.y - p.y * v.x) / R, vr = (p.x * v.x + p.y * v.y) / R;      // vt > 0 : sens de rotation de ce repère
        chaud.push_back(std::hypot(vr, std::fabs(vt) - vc, v.z) > 50);
    }
    const size_t nChaud = std::count(chaud.begin(), chaud.end(), 1);
    std::printf("distance au Soleil jusqu'à %.2f kpc ; « disque » %zu, « chaud » %zu\n", dMax, P.size() - nChaud, nChaud);

    for (const bool barre : {false, true}) {
        g::Potentiel pot; pot.barre = barre;
        std::printf("\nCalcul exact %s la barre centrale\n", barre ? "AVEC" : "SANS");
        for (const double sens : {1.0, -1.0}) {
            g::Orbites exact(P, V, pot);
            for (const double t : {0.01, 0.1, 0.5}) {
                exact.avance(sens * t);
                std::vector<double> dr[2], da[2];
                for (size_t k = 0; k < P.size(); ++k) {
                    const phys::Vec3 a = orbite::epicycle(P[k], V[k], sens * t), b = exact.position(k);
                    dr[chaud[k]].push_back(std::hypot(a.x - b.x, a.y - b.y, a.z - b.z));
                    da[chaud[k]].push_back(angle(a, b));
                }
                std::printf("  à %+.0f millions d'années\n", sens * t * 1000);
                ligne("disque : position", dr[0], "kpc"); ligne("disque : angle", da[0], "°");
                ligne("chaud : position", dr[1], "kpc"); ligne("chaud : angle", da[1], "°");
            }
        }
    }
    return 0;
}
