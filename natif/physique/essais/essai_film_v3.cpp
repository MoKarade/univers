// Essai du lecteur du film version 3 (film_v3.h).
//   essai_film_v3 <dossier> : lit l'index et une date au milieu (film réel, contrôles de forme seulement) ;
//   avec <dossier>/reference.txt (lignes : t, rang, x, y, z de l'interpolation de film_v3.py, puis x, y, z vrais), compare
//   chaque position au lecteur Python du fil du calcul (même Hermite, même centre) et mesure l'écart à la vérité.
#include <array>
#include <cmath>
#include <cstdio>
#include <map>
#include <string>
#include <vector>

#include "film_v3.h"

namespace {
int echecs = 0;
void ok(bool c, const char* m) { std::printf("%s %s\n", c ? "PASSE" : "ECHEC", m); if (!c) ++echecs; }
}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) { std::printf("usage : essai_film_v3 <dossier du film>\n"); return 2; }
    const std::string dossier = argv[1];
    phys::film::FilmV3 f; std::string err;
    if (!f.charger(dossier, err)) { std::printf("ECHEC lecture : %s\n", err.c_str()); return 1; }
    using F = phys::film::FilmV3;
    std::printf("film v3 : %d galaxies, %d dates de %.4f à %.4f Ga (pas de base %.1f Ma), P %llu, C %llu, M %llu, L %llu, G %llu, %zu blocs\n",
                f.galaxies(), f.dates(), f.date(0), f.date(f.dates() - 1), f.pasBaseMa(), (unsigned long long)f.traceursP(),
                (unsigned long long)f.traceursClasse(F::C), (unsigned long long)f.traceursClasse(F::M), (unsigned long long)f.traceursClasse(F::L),
                (unsigned long long)f.traceursG(), f.blocs().size());
    for (int g = 0; g < f.galaxies(); ++g) {
        const auto& d = f.decalageAT0(g);
        std::printf("  décalage à t = 0, galaxie %d : %.4g %.4g %.4g kpc, %.4g %.4g %.4g km/s\n", g, d.position.x, d.position.y, d.position.z, d.vitesse.x, d.vitesse.y, d.vitesse.z);
    }
    {
        const auto s = f.bloc(F::Soleil);
        std::printf("  Soleil : %s (rang %llu) ; Gaia : gaia.bin de %llu octets, CRC32 %08x\n", s.nombre ? "dans le film" : "absent", (unsigned long long)s.premier,
                    (unsigned long long)f.gaiaTaille(), f.gaiaCrc32());
    }
    ok(f.couvre(f.debutGa()) && f.couvre(f.finGa()) && !f.couvre(f.finGa() + 1e-6), "couverture de la première à la dernière image P");
    {   // la Voie lactée reste à l'origine ; les centres sont continus de part et d'autre de chaque date
        double saut = 0, mw = 0;
        for (int k = 1; k + 1 < f.dates(); ++k)
            for (int g = 0; g < f.galaxies(); ++g) {
                phys::Vec3 a, b; f.centre(g, f.date(k) - 1e-9, a); f.centre(g, f.date(k) + 1e-9, b);
                saut = std::fmax(saut, std::hypot(a.x - b.x, a.y - b.y, a.z - b.z));
                if (g == 0) mw = std::fmax(mw, std::hypot(a.x, a.y, a.z));
            }
        ok(saut < 1e-6 && mw < 1e-9, "centres : continus aux dates, Voie lactée à l'origine");
    }
    std::vector<float> etats(f.traceursP() * 6);
    const double tm = 0.5 * (f.debutGa() + f.finGa());
    ok(f.etats(tm, 0, f.traceursP(), etats.data()), "états de tous les traceurs P au milieu du film");
    {   // une plage partielle donne les mêmes états que la lecture complète
        const uint64_t a = f.traceursP() / 3, n = std::min<uint64_t>(f.traceursP() - a, 1000);
        std::vector<float> part(n * 6);
        bool same = f.etats(tm, a, n, part.data());
        for (uint64_t s = 0; same && s < n * 6; ++s) same = part[s] == etats[a * 6 + s];
        ok(same, "plage partielle = lecture complète");
    }
    if (FILE* nt = std::fopen((dossier + "/nature.txt").c_str(), "r")) {      // naissances et retours au gaz, contre film_v3.py
        std::string e2; bool lu = f.chargerMatiere(e2), pareil = lu; double tt; int lignes = 0;
        std::vector<uint8_t> nat;
        while (lu && std::fscanf(nt, "%lf", &tt) == 1) {
            f.natureA(tt, nat); ++lignes;
            for (size_t k = 0; k < nat.size(); ++k) { int v = 0; if (std::fscanf(nt, "%d", &v) != 1 || v != nat[k]) pareil = false; }
        }
        std::fclose(nt);
        std::printf("matière : %zu particules, %zu changements de nature, %d dates comparées%s%s\n", f.matiere().size(), f.evenements().size(), lignes,
                    lu ? "" : " ; ", lu ? "" : e2.c_str());
        ok(pareil && lignes > 0, "nature (étoile ou gaz) de chaque particule = film_v3.py");
    }
    {   // galaxies naines : bloc P de type Naine, noms dans film.json
        std::vector<std::string> noms; std::string e4;
        const bool lu = f.nomsNaines(noms, e4);
        std::printf("naines : %llu dans P%s", (unsigned long long)f.bloc(F::Naine, 0).nombre, lu ? "" : " ; ");
        if (!lu) std::printf("%s", e4.c_str());
        for (const auto& n : noms) std::printf(" [%s]", n.c_str());
        std::printf("\n");
        ok(lu && noms.size() == f.bloc(F::Naine, 0).nombre, "naines : un nom par point du bloc");
        if (FILE* ne = std::fopen((dossier + "/naines_attendues.txt").c_str(), "rb")) {   // film d'essai : noms attendus, un par ligne
            std::string tout; char c[256]; size_t k; while ((k = std::fread(c, 1, sizeof c, ne)) > 0) tout.append(c, k);
            std::fclose(ne);
            std::string lus; for (const auto& n : noms) lus += n + "\n";
            ok(tout == lus, "naines : noms = film.json (guillemets, barre oblique inverse, hors du plan de base)");
        }
    }
    {   // CRC32 : valeur connue de zlib pour « 123456789 »
        const char* s = "123456789";
        ok((F::crc32(0xFFFFFFFFu, (const uint8_t*)s, 9) ^ 0xFFFFFFFFu) == 0xCBF43926u, "CRC32 = celui de zlib");
    }
    if (f.traceursG()) {   // famille G (Gaia)
        std::printf("Gaia : %llu étoiles suivies, de %.4f à %.4f Ga\n", (unsigned long long)f.traceursG(), f.debutGaGaia(), f.finGaGaia());
        ok(f.aGaia() && f.couvreGaia(f.debutGaGaia()) && f.couvreGaia(f.finGaGaia()) && !f.couvreGaia(f.finGaGaia() + 1e-6), "famille G : couverture");
        std::vector<uint32_t> rangsG; std::string e3;
        ok(f.chargerRangsGaia(rangsG, e3) && rangsG.size() == f.traceursG(), "famille G : rangs dans le gaia.bin de l'appli");
        std::vector<float> eg(f.traceursG() * 6);
        ok(f.etatsGaia(0.5 * (f.debutGaGaia() + f.finGaGaia()), 0, f.traceursG(), eg.data()), "famille G : états au milieu");
        if (FILE* ga = std::fopen((dossier + "/gaia_appli.bin").c_str(), "rb")) {     // film d'essai : faux gaia.bin de l'appli
            std::fclose(ga);
            ok(f.gaiaCorrespond(dossier + "/gaia_appli.bin"), "famille G : taille et CRC32 du gaia.bin de l'appli reconnus");
            ok(!f.gaiaCorrespond(dossier + "/gaia.bin"), "famille G : un autre fichier est refusé");
        }
        if (FILE* rg = std::fopen((dossier + "/reference_g.txt").c_str(), "r")) {
            double t, i, x, y, z, X, Y, Z, pire = 0, vrai = 0; size_t n = 0; bool lu = true;
            while (std::fscanf(rg, "%lf %lf %lf %lf %lf %lf %lf %lf", &t, &i, &x, &y, &z, &X, &Y, &Z) == 8) {
                if (!f.etatsGaia(t, (uint64_t)i, 1, eg.data())) { lu = false; continue; }
                pire = std::fmax(pire, std::hypot(eg[0] - x, eg[1] - y, eg[2] - z) / (1e-4 + 2e-7 * std::hypot(x, y, z)));
                vrai = std::fmax(vrai, std::hypot(eg[0] - X, eg[1] - Y, eg[2] - Z)); ++n;
            }
            std::fclose(rg);
            std::printf("famille G : %zu positions comparées à film_v3.py, pire écart %.2f ; écart à la vérité au plus %.3g kpc\n", n, pire, vrai);
            ok(lu && n > 0 && pire <= 1.0, "famille G : mêmes positions que le lecteur Python");
        }
    }
    FILE* r = std::fopen((dossier + "/reference.txt").c_str(), "r");
    if (!r) { std::printf("(pas de reference.txt : contrôles de forme seulement)\n"); std::printf("%s\n", echecs ? "ECHEC" : "PASSE"); return echecs ? 1 : 0; }
    std::map<double, std::vector<std::array<double, 7>>> lignes;
    double t, i, x, y, z, X, Y, Z;
    while (std::fscanf(r, "%lf %lf %lf %lf %lf %lf %lf %lf", &t, &i, &x, &y, &z, &X, &Y, &Z) == 8) lignes[t].push_back({i, x, y, z, X, Y, Z});
    std::fclose(r);
    double pirePy = 0; double pireVrai[5] = {}; size_t n = 0;
    for (const auto& [tt, ls] : lignes) {
        if (!f.etats(tt, 0, f.traceursP(), etats.data())) { std::printf("ECHEC états à %.4f Ga\n", tt); ++echecs; continue; }
        for (const auto& l : ls) {
            const uint64_t k = (uint64_t)l[0]; const float* e = &etats[k * 6];
            const double ref = std::hypot(l[1], l[2], l[3]);
            const double dpy = std::hypot(e[0] - l[1], e[1] - l[2], e[2] - l[3]) / (1e-4 + 2e-7 * ref);
            pirePy = std::fmax(pirePy, dpy);
            const int c = f.classe(k);
            pireVrai[c] = std::fmax(pireVrai[c], std::hypot(e[0] - l[4], e[1] - l[5], e[2] - l[6]));
            ++n;
        }
    }
    std::printf("%zu positions comparées à film_v3.py : pire écart %.2f (1 = 0,1 pc + précision du flottant 32 bits)\n", n, pirePy);
    ok(pirePy <= 1.0, "mêmes positions que le lecteur Python du fil du calcul");
    std::printf("écart à la vérité (orbites du film d'essai), au plus : P seuls %.3g kpc, C %.3g kpc, M %.3g kpc, L %.3g kpc\n",
                pireVrai[F::P], pireVrai[F::C], pireVrai[F::M], pireVrai[F::L]);
    std::printf("%s\n", echecs ? "ECHEC" : "PASSE");
    return echecs ? 1 : 0;
}
