// Contrôle du mouvement des étoiles autour de la Galaxie (orbite_galactique.h et shaders/orbite_galactique.glsl).
//  1. Les constantes écrites pour la carte graphique sont celles de la bibliothèque de physique.
//  2. Aux temps courts, le déplacement est la ligne droite à la vitesse mesurée (rien ne change près d'aujourd'hui).
//  3. Aucun saut : entre deux dates voisines, à toute époque, l'étoile avance de moins que sa vitesse ne le permet.
//  4. Écart MESURÉ avec l'intégration exacte du fil physique (phys::galaxie::Orbites, sans la barre puis avec), pour le
//     Soleil et des étoiles du disque, à 10, 100, 250 millions et 1 milliard d'années.
// Usage : essai_orbite <chemin de orbite_galactique.glsl>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "orbite_galactique.h"

namespace {
int echecs = 0;
void verifie(bool ok, const std::string& quoi) {
    std::printf("%s  %s\n", ok ? "PASSE" : "ÉCHEC", quoi.c_str());
    if (!ok) ++echecs;
}
double constante(const std::string& src, const std::string& nom) {
    const size_t i = src.find(" " + nom + " = ");      // « const float A = 1, B = 2; » : chaque nom est précédé d'un espace
    return i == std::string::npos ? std::nan("") : std::stod(src.substr(i + 4 + nom.size()));
}
bool proche(double a, double b, double rel = 2e-7) { return std::fabs(a - b) <= rel * std::max(std::fabs(a), std::fabs(b)); }
double norme(phys::Vec3 a) { return std::sqrt(a.x * a.x + a.y * a.y + a.z * a.z); }
}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::printf("usage : essai_orbite <orbite_galactique.glsl>\n");
        return 2;
    }
    std::ifstream f(argv[1]);
    std::stringstream ss;
    ss << f.rdbuf();
    const std::string src = ss.str();
    namespace g = phys::galaxie;
    verifie(proche(constante(src, "OG_G"), g::kG) && proche(constante(src, "OG_MB"), g::kMb) && proche(constante(src, "OG_AB"), g::kAb) &&
                proche(constante(src, "OG_MD"), g::kMd) && proche(constante(src, "OG_AD"), g::kAd) && proche(constante(src, "OG_BD"), g::kBd) &&
                proche(constante(src, "OG_RS"), g::kRs) && proche(constante(src, "OG_GMH"), g::gmHalo()) && proche(constante(src, "OG_K"), g::kKmsKpcToRadGa) &&
                proche(constante(src, "OG_KPC_LY"), orbite::kKpcLy) && proche(constante(src, "OG_RACCORD_ANS"), orbite::kRaccordAns) &&
                proche(constante(src, "OG_AMP_MAX"), orbite::kAmplitudeMax),
            "constantes de la carte graphique = constantes de la bibliothèque de physique");
    {
        const phys::Vec3 s = g::soleilPos(), v = g::soleilVit();
        char want[160];
        std::snprintf(want, sizeof want, "OG_SOLEIL_VIT = vec3(%.1f, %.2f, %.2f)", v.x, v.y, v.z);
        const size_t i = src.find("OG_SOLEIL_POS = vec3(");
        double x = 0, y = 0, z = 0;
        const bool lu = i != std::string::npos && std::sscanf(src.c_str() + i, "OG_SOLEIL_POS = vec3(%lf, %lf, %lf)", &x, &y, &z) == 3;
        verifie(lu && std::fabs(x - s.x) < 1e-6 && std::fabs(y - s.y) < 1e-6 && std::fabs(z - s.z) < 1e-6 && src.find(want) != std::string::npos,
                "place et vitesse du Soleil de la carte graphique = celles de la bibliothèque");
    }
    // 1 bis. Le calcul exact de la carte (orbites_pas.comp, à côté du premier fichier) : mêmes constantes que la bibliothèque.
    {
        std::string dir = argv[1];
        const size_t cut = dir.find_last_of("/\\");
        dir = cut == std::string::npos ? "." : dir.substr(0, cut);
        std::ifstream fc(dir + "/orbites_pas.comp");
        std::stringstream sc;
        sc << fc.rdbuf();
        const g::Potentiel P;
        for (const char* fichier : {"orbites_pas.comp", "gaia_acc.glsl"}) {      // gaia_acc.glsl (étoiles Gaia) porte une copie du même calcul
        std::ifstream fk(dir + "/" + fichier);
        std::stringstream sk;
        sk << fk.rdbuf();
        const std::string comp = sk.str();
        verifie(proche(constante(comp, "OP_G"), g::kG) && proche(constante(comp, "OP_MB"), g::kMb) && proche(constante(comp, "OP_AB"), g::kAb) &&
                    proche(constante(comp, "OP_MD"), g::kMd) && proche(constante(comp, "OP_AD"), g::kAd) && proche(constante(comp, "OP_BD"), g::kBd) &&
                    proche(constante(comp, "OP_RS"), g::kRs) && proche(constante(comp, "OP_GMH"), P.GMs) && proche(constante(comp, "OP_K"), g::kKmsKpcToRadGa) &&
                    proche(constante(comp, "OP_RB"), P.Rb) && proche(constante(comp, "OP_ABAR"), P.Ab) && proche(constante(comp, "OP_BAR0"), g::barAngleAt(0)) &&
                    proche(constante(comp, "OP_BARW"), g::kBarOmegaKmsKpc * g::kKmsKpcToRadGa),
                std::string("constantes du calcul exact de la carte graphique (") + fichier + ") = bibliothèque de physique");
        }
    }
    // 2. Temps courts : ligne droite mesurée.
    const Vec3 pos{12.0, -30.0, 4.0}, vel{-20.0, 35.0, 8.0};
    {
        const Vec3 d = orbite::deplacement(pos, vel, 1000.0);
        const double k = 1000.0 * kKmsToLyPerYear;
        const double e = std::sqrt((d.x - vel.x * k) * (d.x - vel.x * k) + (d.y - vel.y * k) * (d.y - vel.y * k) + (d.z - vel.z * k) * (d.z - vel.z * k));
        verifie(e < 1e-5 * std::sqrt(dot(d, d)), "à 1 000 ans, le déplacement est la ligne droite à la vitesse mesurée (écart relatif " + std::to_string(e / std::sqrt(dot(d, d))) + ")");
    }
    // 3. Aucun saut, de -1 à +1 milliard d'années.
    {
        double pire = 0;
        for (double t = -1.0e9; t < 1.0e9; t += 1.7e5) {
            const Vec3 a = orbite::deplacement(pos, vel, t), b = orbite::deplacement(pos, vel, t + 1.0e3);
            pire = std::max(pire, std::sqrt(dot(a - b, a - b)) / (1.0e3 * kKmsToLyPerYear));      // vitesse apparente, km/s
        }
        verifie(pire < 700.0, "aucun saut entre -1 et +1 milliard d'années (vitesse apparente maximale " + std::to_string(pire) + " km/s)");
    }
    // 4. Écart avec l'intégration exacte.
    // Trois étoiles du disque (vitesse proche de la vitesse circulaire, écarts de 10 à 30 km/s comme les étoiles voisines),
    // le Soleil, et une étoile sur orbite allongée (dite à part : la méthode ne lui convient pas).
    std::vector<phys::Vec3> p0 = {g::soleilPos(), {-7.0, 2.0, 0.1}, {5.0, -6.0, -0.2}, {-10.0, -3.0, 0.3}, {-7.0, 2.0, 0.1}};
    std::vector<phys::Vec3> v0 = {g::soleilVit(), {73.2, 206.2, 8.0}, {-196.7, -137.2, -12.0}, {-41.1, 240.3, 5.0}, {-70.0, 215.0, 10.0}};
    const size_t disque = 4;      // les 4 premières : disque
    for (const bool barre : {false, true}) {
        g::Potentiel P;
        P.barre = barre;
        for (const double tGa : {0.01, 0.1, 0.25, 1.0}) {
            g::Orbites o(p0, v0, P);
            o.avance(tGa, 1);
            double pire = 0, allongee = 0, angle = 0;
            for (size_t k = 0; k < p0.size(); ++k) {
                const phys::Vec3 e = orbite::epicycle(p0[k], v0[k], tGa), x = o.position(k);
                const double d = norme({e.x - x.x, e.y - x.y, e.z - x.z});
                if (k < disque) {
                    pire = std::max(pire, d);
                    double a = std::fabs(std::atan2(e.y, e.x) - std::atan2(x.y, x.x));
                    if (a > g::kPi) a = 2 * g::kPi - a;
                    angle = std::max(angle, a * 180 / g::kPi);
                } else {
                    allongee = d;
                }
            }
            std::printf("  %s, %4.0f millions d'années : disque, écart maximal avec le calcul exact %.3f kpc (%.1f degrés autour du centre) ; orbite allongée : %.3f kpc\n",
                        barre ? "avec la barre" : "sans la barre", tGa * 1000, pire, angle, allongee);
            // Seuils posés d'après la mesure (12 novembre 2026 : 0,012 kpc à 10 millions d'années, 1,5 kpc et 7 degrés à 100
            // millions). Au-delà, l'écart grandit (51 degrés après 1 milliard d'années) : l'orbite est alors indicative, et
            // l'écran le dit ; le calcul exact étoile par étoile est l'étape suivante.
            if (!barre && tGa == 0.01) verifie(pire < 0.05, "disque, sans la barre : écart sous 0,05 kpc à 10 millions d'années");
            if (!barre && tGa == 0.1) verifie(pire < 2.0 && angle < 10.0, "disque, sans la barre : écart sous 2 kpc et 10 degrés à 100 millions d'années");
        }
    }
    std::printf("%s\n", echecs ? "ÉCHEC" : "PASSE");
    return echecs ? 1 : 0;
}
