// Contrôle de robustesse de la bibliothèque univers_physique face à des entrées hostiles ou limites (autonome :
// fichiers de synthèse écrits dans un dossier temporaire, aucune donnée de la NASA ni du calcul de fusion requise).
// Chaque bloc reproduit un défaut relevé par la vérification adverse du jalon M4 (itération 1) :
//   C1  Orbites::avance(NaN / ±Inf / 1e20) : dépassement d'entier signé puis abandon du programme.
//   C2  Rejeu::charger : réservation de plusieurs téraoctets à partir d'un fichier de 117 Ko (nf = 0).
//   C3  LongTable::load et Rejeu::charger sur un dossier : ftell() = LONG_MAX puis allocation de 8 Eo.
//   C4  Rejeu::charger : nom d'image « ../secret.bin » lu hors du dossier des images.
//   C5  Integrator::advanceTo(1e300) ou pas minuscule : conversion double -> long hors limites.
//   C6  LongTable::position : true avec des coordonnées infinies ou NaN.
//   C7  Bornes à 1 ULP près : centre(g, finGa()), etoilesA(finGa()) et position(b, lastJd()) refusées.
// Imprime PASSE ou ECHEC par ligne ; code de sortie 0 si tout passe, 1 sinon.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <limits>
#include <string>
#include <vector>

#include "galaxie_orbites.h"
#include "groupe_local.h"
#include "nbody_noyau.h"

namespace fs = std::filesystem;
static int g_fail = 0;

#if defined(__GNUC__) || defined(__clang__)
__attribute__((format(printf, 2, 3)))
#endif
static void
ok(bool c, const char* fmt, ...) {
    std::printf("%s ", c ? "PASSE" : "ECHEC");
    std::va_list ap;
    va_start(ap, fmt);
    std::vprintf(fmt, ap);
    va_end(ap);
    std::putchar('\n');
    if (!c)
        ++g_fail;
}

static void put(std::vector<uint8_t>& b, const void* p, size_t n) {
    const auto* c = static_cast<const uint8_t*>(p);
    b.insert(b.end(), c, c + n);
}
static void putD(std::vector<uint8_t>& b, double v) {
    put(b, &v, sizeof(v));
}
static void putF(std::vector<uint8_t>& b, float v) {
    put(b, &v, sizeof(v));
}

static bool writeFile(const fs::path& p, const std::vector<uint8_t>& b) {
    std::ofstream f(p, std::ios::binary | std::ios::trunc);
    f.write(reinterpret_cast<const char*>(b.data()), static_cast<std::streamsize>(b.size()));
    return static_cast<bool>(f);
}

// fusion_centres.bin de synthèse (format de pipeline/natif/fusion_bin.py) : n images, T traceurs, nGal étoiles,
// centres en ligne droite, puis la liste des fichiers d'images (nom sur 16 octets, nombre d'images).
struct KfName {
    std::string nom;
    double k;
};
static std::vector<uint8_t> fusionCentres(long n, double dt, int T, const double nGal[4],
                                          const std::vector<KfName>& kf) {
    std::vector<uint8_t> b;
    const double h[12] = {
        1.0,    static_cast<double>(n), dt, 4.0, static_cast<double>(T), 0.025, 5.44, 0.001, nGal[0], nGal[1], nGal[2],
        nGal[3]};
    for (double v : h)
        putD(b, v);
    for (long i = 0; i < n; ++i) {
        for (int g = 0; g < 4; ++g) {
            for (int c = 0; c < 3; ++c)
                putD(b, static_cast<double>(g * 100 + c) + 0.5 * static_cast<double>(i));
        }
    }
    for (long i = 0; i < n * T * 3; ++i)
        putD(b, 0.0);
    putD(b, static_cast<double>(kf.size()));
    for (const auto& e : kf) {
        char nom[16] = {};
        std::memcpy(nom, e.nom.data(), std::min<size_t>(e.nom.size(), 16));
        put(b, nom, 16);
        putD(b, e.k);
    }
    return b;
}

// Table des orbites longues de synthèse (version 1 : sans nœuds intermédiaires), un corps, éléments constants.
static std::vector<uint8_t> longTable(double dd, long nP, long nF, int sl, float a, float e, float I, float lam0) {
    std::vector<uint8_t> b;
    const long n = nP + nF + 1, nS = (n - 1) / sl + 1;
    const double h[7] = {
        1.0, 2451545.0, dd, static_cast<double>(nP), static_cast<double>(nF), 1.0, static_cast<double>(sl)};
    for (double v : h)
        putD(b, v);
    for (long k = 0; k < n; ++k)
        putF(b, lam0 + 0.01f * static_cast<float>(k));
    for (long k = 0; k < nS; ++k) {
        putF(b, a);
        putF(b, e);
        putF(b, I);
        putF(b, 0.3f);
        putF(b, 0.7f);
    }
    return b;
}

int main() {
    const double kNan = std::numeric_limits<double>::quiet_NaN();
    const double kInf = std::numeric_limits<double>::infinity();
    const fs::path dir =
        fs::temp_directory_path() /
        ("essai_robustesse_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    std::error_code ec;
    fs::create_directories(dir / "images", ec);
    if (ec) {
        std::fprintf(stderr, "ECHEC : dossier temporaire %s\n", dir.string().c_str());
        return 1;
    }

    // C1 : Orbites::avance sur des dates non finies ou démesurées : rien ne bouge, pas d'abandon.
    {
        using namespace phys::galaxie;
        const phys::Vec3 sp[1] = {soleilPos()}, sv[1] = {soleilVit()};
        Orbites o(sp, sv);
        const phys::Vec3 p0 = o.position(0);
        for (double t : {kNan, kInf, -kInf, 1e20, -1e20})
            o.avance(t, 2);
        const phys::Vec3 p1 = o.position(0);
        ok(o.temps() == 0.0 && p1.x == p0.x && p1.y == p0.y && p1.z == p0.z,
           "C1 Orbites::avance(NaN, ±Inf, ±1e20) : refusé sans abandon, temps %.1f Ga inchangé", o.temps());
        o.avance(0.01, 2);
        ok(std::fabs(o.temps() - 0.01) < 1e-12, "C1 Orbites::avance(0,01) fonctionne toujours après (%.3f Ga)",
           o.temps());
    }

    // C5 : Integrator::advanceTo hors limites : état inchangé et fini.
    {
        phys::nb::Integrator it;
        const phys::nb::State s0 = it.state();
        it.advanceTo(1e300);
        it.advanceTo(-1e300);
        it.advanceTo(s0.jd + 10.0, 1e-300);
        it.advanceTo(s0.jd + 10.0, kInf);
        it.advanceTo(s0.jd + 10.0, -4.0);
        it.advanceTo(kNan);
        bool same = it.state().jd == s0.jd;
        for (size_t i = 0; i < s0.Q.size(); ++i)
            same = same && it.state().Q[i] == s0.Q[i] && it.state().V[i] == s0.V[i];
        ok(same, "C5 Integrator::advanceTo(±1e300, pas 1e-300, pas infini ou négatif, NaN) : refusé, état inchangé");
        it.advanceTo(s0.jd + 40.0);
        ok(it.state().jd == s0.jd + 40.0 && std::isfinite(it.state().Q[0]),
           "C5 Integrator::advanceTo(+40 j) fonctionne toujours");
    }

    // C3 : un dossier n'est pas un fichier.
    {
        phys::nb::LongTable lt;
        phys::fusion::Rejeu r;
        ok(!lt.load(dir.string()) && !lt.loaded(), "C3 LongTable::load(dossier) : refusé sans allocation géante");
        ok(!r.charger(dir.string(), ""), "C3 Rejeu::charger(dossier) : refusé sans allocation géante");
        ok(!lt.load((dir / "absent.bin").string()) && !r.charger((dir / "absent.bin").string(), ""),
           "C3 fichiers absents : refusés");
    }

    // C6 et C7 pour LongTable.
    {
        const fs::path p = dir / "table.bin";
        phys::nb::LongTable lt;
        int tried = 0, failures = 0;
        for (double dd : {0.1, 0.3, 1.7, 7.3, 135.1375, 365.25, 1000.1, 3652.5}) {
            for (long nF : {1L, 2L, 3L, 7L, 10L, 29L, 57L, 113L, 250L}) {
                for (long nP : {0L, 3L, 11L}) {
                    if (!writeFile(p, longTable(dd, nP, nF, 1, 1.0f, 0.05f, 0.02f, 0.1f)) || !lt.load(p.string())) {
                        ++failures;
                        continue;
                    }
                    double out[3] = {};
                    ++tried;
                    const bool good = lt.position(0, lt.lastJd(), out) && lt.position(0, lt.firstJd(), out) &&
                                      std::isfinite(out[0]) && std::isfinite(out[1]) && std::isfinite(out[2]);
                    const bool outside = !lt.position(0, std::nextafter(lt.lastJd(), kInf) + dd, out) &&
                                         !lt.position(0, lt.firstJd() - dd, out);
                    if (!good || !outside)
                        ++failures;
                }
            }
        }
        ok(failures == 0 && tried == 216,
           "C7 LongTable::position aux bornes firstJd()/lastJd() : %d échecs sur %d tables", failures, tried);

        const float fInf = std::numeric_limits<float>::infinity(), fNan = std::numeric_limits<float>::quiet_NaN();
        struct Bad {
            const char* what;
            float a, e, I, lam;
        };
        for (const Bad& c :
             {Bad{"a = +Inf", fInf, 0.05f, 0.02f, 0.1f}, Bad{"i = NaN", 1.0f, 0.05f, fNan, 0.1f},
              Bad{"lambda = NaN", 1.0f, 0.05f, 0.02f, fNan}, Bad{"lambda = +Inf", 1.0f, 0.05f, 0.02f, fInf},
              Bad{"a minuscule (mouvement infini)", 1e-30f, 0.05f, 0.02f, 0.1f}}) {
            double out[3] = {0.0, 0.0, 0.0};
            const bool loaded = writeFile(p, longTable(10.0, 2, 8, 3, c.a, c.e, c.I, c.lam)) && lt.load(p.string());
            const bool pos = loaded && lt.position(0, 2451545.0 + 5.0, out);
            ok(loaded && (!pos || (std::isfinite(out[0]) && std::isfinite(out[1]) && std::isfinite(out[2]))),
               "C6 LongTable::position avec %s : jamais true avec des coordonnées non finies (rendu %s)", c.what,
               pos ? "true fini" : "false");
        }
    }

    // C2 : 120 104 octets décrivant 4 × 178 956 970 étoiles et aucune image : refus sans réserver la mémoire.
    {
        const double nGal[4] = {178956970.0, 178956970.0, 178956970.0, 178956970.0};
        const fs::path p = dir / "bombe.bin";
        const auto b = fusionCentres(1000, 0.02, 1, nGal, {});
        phys::fusion::Rejeu r;
        ok(writeFile(p, b) && b.size() == 120104 && !r.charger(p.string(), (dir / "images").string()),
           "C2 Rejeu::charger : fichier de %d octets annonçant des To d'images, nf = 0 : refusé",
           static_cast<int>(b.size()));
        const auto b2 = fusionCentres(1000, 0.02, 1, nGal, {{"kf_000.bin", 1000.0}});
        ok(writeFile(p, b2) && !r.charger(p.string(), (dir / "images").string()),
           "C2 Rejeu::charger : image annoncée absente ou de mauvaise taille : refusé avant toute réservation");
    }

    // C4 : noms d'images qui sortent du dossier, et témoin positif avec un nom valide.
    {
        const double nGal[4] = {1.0, 1.0, 0.0, 0.0};                      // 2 étoiles
        const std::vector<uint8_t> image(2 * 2 * 3 * sizeof(int16_t), 7); // 2 images × 2 étoiles × 3 coordonnées
        ok(writeFile(dir / "secret.bin", image) && writeFile(dir / "images" / "kf_000.bin", image),
           "C4 préparation des images de synthèse");
        phys::fusion::Rejeu r;
        for (const char* nom : {"../secret.bin", ".", "..", "a/b.bin", "a\\b.bin", "c:x.bin"}) {
            const fs::path p = dir / "images" / "centres.bin";
            ok(writeFile(p, fusionCentres(2, 0.02, 1, nGal, {{nom, 2.0}})) &&
                   !r.charger(p.string(), (dir / "images").string()),
               "C4 Rejeu::charger : nom d'image « %s » refusé", nom);
        }
        const fs::path p = dir / "images" / "centres.bin";
        std::vector<phys::Vec3> e(2);
        ok(writeFile(p, fusionCentres(2, 0.02, 1, nGal, {{"kf_000.bin", 2.0}})) &&
               r.charger(p.string(), (dir / "images").string()) && r.etoilesA(0.0, e),
           "C4 témoin : nom valide « kf_000.bin » accepté et images lues");
    }

    // C7 pour Rejeu : centre(g, finGa()) pour n = 2..400 au pas réel de 0,02 Ga, et etoilesA(finGa()).
    {
        const double nGal[4] = {1.0, 1.0, 0.0, 0.0};
        const fs::path p = dir / "c7.bin";
        phys::fusion::Rejeu r;
        int failures = 0;
        for (long n = 2; n <= 400; ++n) {
            phys::Vec3 c;
            if (!writeFile(p, fusionCentres(n, 0.02, 1, nGal, {})) || !r.charger(p.string(), "") ||
                !r.centre(phys::fusion::kAndromede, r.finGa(), c) || !r.centre(phys::fusion::kAndromede, 0.0, c) ||
                r.centre(phys::fusion::kAndromede, std::nextafter(r.finGa(), kInf) + 0.02, c)) {
                ++failures;
            }
        }
        ok(failures == 0, "C7 Rejeu::centre(g, finGa()) pour n = 2..400, dt = 0,02 Ga : %d échecs", failures);

        const long n = 8; // finGa() / dt = 7,000000000000001 : cas relevé par la vérification adverse
        const std::vector<uint8_t> image(static_cast<size_t>(n) * 2 * 3 * sizeof(int16_t), 3);
        std::vector<phys::Vec3> e(2);
        const fs::path pc = dir / "images" / "c7.bin";
        ok(writeFile(dir / "images" / "kf_c7.bin", image) &&
               writeFile(pc, fusionCentres(n, 0.02, 1, nGal, {{"kf_c7.bin", static_cast<double>(n)}})) &&
               r.charger(pc.string(), (dir / "images").string()) && r.etoilesA(r.finGa(), e) && std::isfinite(e[0].x),
           "C7 Rejeu::etoilesA(finGa()) avec n = 8 images : accepté");
    }

    fs::remove_all(dir, ec);
    std::printf(g_fail ? "ECHEC (%d)\n" : "PASSE\n", g_fail);
    return g_fail ? 1 : 0;
}
