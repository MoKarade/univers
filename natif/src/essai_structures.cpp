// Contrôle des grandes structures et du modèle du nuage d'Oort (structures.h), sans fenêtre ni carte graphique.
//
// 1. structures.bin (pipeline/natif/structures.py) : quatre surfaces, indices valides, surfaces fermées ; volume enfermé
//    par la frontière de Laniakea = volume publié par Dupuy et Courtois 2023 (1,9 million de (Mpc/h)³, 1,945 sur leur grille) ;
//    lignes de courant de Laniakea qui finissent toutes au même endroit.
// 2. structures_noms.tsv : Laniakea, Grand Attracteur et Vide local présents ; Vide local à 38,8 Mpc/h (Malandrino et al. 2026).
// 3. Modèle du nuage d'Oort : densité en r^-3,5 retrouvée sur les positions tirées, nuage extérieur isotrope, intérieur aplati.
//
// Usage : essai_structures.exe <dossier des données>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

#include <algorithm>

#include "structures.h"

using namespace univers;      // en-têtes de l'appli (natif/src), autrefois en espace de noms anonyme

static int gEchecs = 0;
static void verifie(bool ok, const char* quoi) {
    std::printf("  %s  %s\n", ok ? "ok    " : "ECHEC ", quoi);
    if (!ok) ++gEchecs;
}

static constexpr double kMpcLy = 3.2615637771674333e6, kH = 0.674;

// Volume enfermé (al³) par une surface triangulée : somme des tétraèdres depuis l'origine (valeur absolue).
static double volume(const structures::Mesh& m) {
    double v = 0;
    for (size_t t = 0; t + 2 < m.idx.size(); t += 3) {
        const float* a = &m.verts[m.idx[t] * 6];
        const float* b = &m.verts[m.idx[t + 1] * 6];
        const float* c = &m.verts[m.idx[t + 2] * 6];
        v += (double(a[0]) * (double(b[1]) * c[2] - double(b[2]) * c[1]) - double(a[1]) * (double(b[0]) * c[2] - double(b[2]) * c[0]) +
              double(a[2]) * (double(b[0]) * c[1] - double(b[1]) * c[0])) / 6.0;
    }
    return std::fabs(v);
}

// Surface fermée : chaque arête partagée par un nombre pair de triangles.
static bool fermee(const structures::Mesh& m) {
    std::vector<std::pair<uint64_t, int>> edges;
    edges.reserve(m.idx.size());
    for (size_t t = 0; t + 2 < m.idx.size(); t += 3)
        for (int k = 0; k < 3; ++k) {
            uint64_t a = m.idx[t + k], b = m.idx[t + (k + 1) % 3];
            if (a > b) std::swap(a, b);
            edges.push_back({(a << 32) | b, 1});
        }
    std::sort(edges.begin(), edges.end());
    size_t i = 0;
    while (i < edges.size()) {
        size_t j = i;
        while (j < edges.size() && edges[j].first == edges[i].first) ++j;
        if ((j - i) % 2) return false;
        i = j;
    }
    return true;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::printf("usage : essai_structures <dossier des données>\n");
        return 2;
    }
    const std::string dir = argv[1];
    std::printf("Grandes structures (%s)\n", dir.c_str());
    structures::File f;
    verifie(structures::readFile(dir + "/structures.bin", f), "structures.bin lu (en-tête, tailles, indices dans les bornes)");
    verifie(f.meshes.size() == 4, "quatre surfaces : Laniakea, vides du voisinage, SDSS, BOSS");
    for (const auto& m : f.meshes) {
        char q[160];
        std::snprintf(q, sizeof(q), "surface %u : %zu triangles, fermée", m.kind, m.idx.size() / 3);
        verifie(!m.idx.empty() && m.idx.size() % 3 == 0 && fermee(m), q);
    }
    if (!f.meshes.empty() && f.meshes[0].kind == 1) {
        const double vol = volume(f.meshes[0]) / std::pow(kMpcLy / kH, 3) / 1e6;
        std::printf("    Laniakea : volume enfermé %.3f millions de (Mpc/h)³ (grille de l'article : 1,945 ; table : 1,9)\n", vol);
        verifie(std::fabs(vol / 1.945 - 1) < 0.01, "Laniakea : volume publié retrouvé à 1 % près");
    }
    {      // les lignes de Laniakea finissent au même point (médiane de leurs arrivées)
        std::vector<double> ex, ey, ez;
        for (const auto& l : f.lines)
            if (l.basin == 1 && l.pts.size() >= 4) {
                const float* e = &l.pts[l.pts.size() - 4];
                ex.push_back(e[0]); ey.push_back(e[1]); ez.push_back(e[2]);
            }
        const size_t n = ex.size();
        auto med = [](std::vector<double> v) { std::nth_element(v.begin(), v.begin() + v.size() / 2, v.end()); return v[v.size() / 2]; };
        const double mx = n ? med(ex) : 0, my = n ? med(ey) : 0, mz = n ? med(ez) : 0;
        size_t pres = 0;
        for (size_t i = 0; i < n; ++i)
            pres += std::sqrt(std::pow(ex[i] - mx, 2) + std::pow(ey[i] - my, 2) + std::pow(ez[i] - mz, 2)) < 3.0 * kMpcLy;
        std::printf("    flot : %zu lignes, dont %zu de Laniakea ; %zu finissent à moins de 3 Mpc de leur point médian\n", f.lines.size(), n, pres);
        /* les autres s'arrêtent là où le flot est presque nul sans être un puits (cols entre deux bassins) */
        verifie(n > 100 && pres > 0.75 * n, "flot de Laniakea : au moins 3 lignes sur 4 finissent sur un seul attracteur");
    }
    {      // noms
        std::ifstream t(dir + "/structures_noms.tsv");
        std::string line;
        bool lan = false, ga = false, vl = false;
        double dvl = 0;
        while (std::getline(t, line)) {
            const std::string nom = line.substr(0, line.find('\t'));
            lan = lan || nom == "Laniakea";
            ga = ga || nom == "Grand Attracteur";
            if (nom == "Vide local") {
                double x, y, z;
                if (std::sscanf(line.c_str() + nom.size() + 1, "%lf\t%lf\t%lf", &x, &y, &z) == 3) dvl = std::sqrt(x * x + y * y + z * z) / kMpcLy * kH;
                vl = true;
            }
        }
        std::printf("    Vide local à %.1f Mpc/h (article : 38,8)\n", dvl);
        verifie(lan && ga, "noms : Laniakea et Grand Attracteur");
        verifie(vl && std::fabs(dvl - 38.8) < 1.0, "noms : Vide local à sa distance publiée");
    }

    std::printf("Modèle du nuage d'Oort\n");
    const auto el = structures::oortModel(200000);
    // position à une date quelconque (anomalie moyenne au hasard : déjà tirée), même calcul que oort.vert
    std::vector<double> r;
    double zOut = 0, zIn = 0;
    int nOut = 0, nIn = 0;
    for (const auto& o : el) {
        double E = o.e < 0.8 ? o.m0 : 3.14159265;
        for (int k = 0; k < 30; ++k) E -= (E - o.e * std::sin(E) - o.m0) / (1.0 - o.e * std::cos(E));
        const double xo = o.a * (std::cos(E) - o.e), yo = o.a * std::sqrt(1.0 - o.e * o.e) * std::sin(E);
        const double z = std::sin(o.peri) * std::sin(o.inc) * xo + std::cos(o.peri) * std::sin(o.inc) * yo;
        const double rr = std::sqrt(xo * xo + yo * yo);
        r.push_back(rr);
        if (rr > 30000) { zOut += z * z / (rr * rr); ++nOut; }
        if (rr > 3000 && rr < 6000) { zIn += z * z / (rr * rr); ++nIn; }
    }
    // pente de la densité entre 5 000 et 40 000 UA : n(r) ∝ N(coquille) / r² dr
    auto shell = [&](double a, double b) { int n = 0; for (double x : r) n += x >= a && x < b; return n / (4.18879 * (b * b * b - a * a * a)); };
    const double slope = std::log(shell(36000, 44000) / shell(4500, 5500)) / std::log(40000.0 / 5000.0);
    std::printf("    pente de la densité entre 5 000 et 40 000 UA : %.2f (modèle : -3,5)\n", slope);
    verifie(std::fabs(slope + 3.5) < 0.25, "densité en r^-3,5 (Duncan, Quinn et Tremaine 1987)");
    std::printf("    <(z/r)²> au-delà de 30 000 UA : %.3f (isotrope : 0,333) ; entre 3 000 et 6 000 UA : %.3f\n", zOut / nOut, zIn / nIn);
    verifie(std::fabs(zOut / nOut - 1.0 / 3.0) < 0.02, "nuage extérieur isotrope");
    verifie(zIn / nIn < 0.2, "nuage intérieur aplati vers l'écliptique");
    int dehors = 0;
    for (double x : r) dehors += x > 2.0 * structures::kOortAMax;
    verifie(dehors == 0, "aucune comète au-delà de deux fois le bord (aphélie)");
    std::printf(gEchecs ? "ECHEC : %d\n" : "PASSE\n", gEchecs);
    return gEchecs ? 1 : 0;
}
