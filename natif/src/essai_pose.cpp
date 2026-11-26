// Contrôle de la pose automatique (pose_auto.h) sur des histogrammes construits à la main, sans carte graphique.
// Ce qui est vérifié (Marc, 20/11/2026 : « parfois trop de lumière, parfois pas assez, quand je zoome ou défile ») :
// 1. la pose visée ne dépend que de l'image (pas du chemin) ; 2. un ciel étoilé ordinaire garde la pose de base ;
// 3. jamais plus de 0,5 % de l'image blanche ; 4. une image trop claire est baissée jusqu'à l'éclat visé ; 5. une image
// très sombre est relevée, sans dépasser le plafond ; 6. les seuils glissent avec le plafond (pas de bascule) ;
// 7. l'adaptation dans le temps est continue, en logarithme, avec les demi-temps annoncés.
// Usage : essai_pose (aucun argument). Rend 0 si tout passe.
#include <cstdio>

#include "pose_auto.h"

using namespace univers;      // en-têtes de l'appli (natif/src), autrefois en espace de noms anonyme

namespace {

int gEchecs = 0;

void verifie(bool ok, const char* quoi, double v = 0) {
    std::printf("%s  %-80s %g\n", ok ? "PASSE" : "ÉCHEC", quoi, v);
    if (!ok) ++gEchecs;
}

// case de l'histogramme qui contient la luminance y (même formule que shaders/pose.comp)
int caseDe(double y) {
    if (y < std::exp2(pose_auto::kLog2Min)) return 0;
    return static_cast<int>(std::clamp(std::floor((std::log2(y) - pose_auto::kLog2Min) / pose_auto::kPas) + 1.0, 1.0, 127.0));
}

struct Histo {
    uint32_t h[pose_auto::kCases] = {};
    void ajoute(double y, uint32_t n) { h[caseDe(y)] += n; }
};

constexpr uint32_t kPixels = 1920u * 1080u;

}  // namespace

int main() {
    SetConsoleOutputCP(CP_UTF8);
    using namespace pose_auto;

    // Ciel étoilé : fond noir, 0,3 % de pixels d'étoiles d'éclat 0,2 à 2, 0,05 % d'étoiles brillantes (10).
    Histo ciel;
    ciel.ajoute(1e-4, kPixels - 7500);
    ciel.ajoute(0.2, 3000);
    ciel.ajoute(2.0, 3500);
    ciel.ajoute(10.0, 1000);
    const double p1 = cible(ciel.h, 4.0);
    verifie(std::fabs(p1 - 1.0) < 1e-9, "ciel étoilé ordinaire : pose de base (×1)", p1);
    verifie(cible(ciel.h, 4.0) == p1, "même image, même pose visée (pas de mémoire du chemin)", cible(ciel.h, 4.0));

    // Trop d'étoiles saturées : 2 % de l'image à 100.
    Histo sature;
    sature.ajoute(1e-4, kPixels - kPixels / 50);
    sature.ajoute(100.0, kPixels / 50);
    const double ps = cible(sature.h, 4.0);
    verifie(statsPour(sature.h, ps).sat <= kPartMax + 1e-12, "image saturée : au plus 0,5 % de blanc après la pose", statsPour(sature.h, ps).sat);
    verifie(ps < 0.05 && ps > 0.02, "image saturée : pose baissée vers 3 / 100 (seuil de blanc / éclat)", ps);

    // Image trop claire (une galaxie qui remplit l'écran à 0,5) aux échelles des étoiles : baissée jusqu'à l'éclat visé.
    Histo clair;
    clair.ajoute(0.5, kPixels);
    const double pc = cible(clair.h, 4.0);
    verifie(std::fabs(statsPour(clair.h, pc).moy - kMoyHaute) < 0.01, "image trop claire : éclat moyen ramené à 0,05", statsPour(clair.h, pc).moy);
    // ... mais pas aux échelles des galaxies (plancher ×1) : la galaxie garde son éclat.
    verifie(std::fabs(cible(clair.h, 1000.0) - 1.0) < 1e-9, "galaxies : une image claire n'est pas baissée (seulement la saturation)", cible(clair.h, 1000.0));

    // Image très sombre (points de galaxies à 1e-4) : relevée, sans dépasser le plafond.
    Histo sombre;
    sombre.ajoute(1e-7, kPixels - 2000);
    sombre.ajoute(1e-4, 2000);
    const double pg = cible(sombre.h, 1000.0);
    verifie(pg > 1.0 && pg <= 1000.0, "image très sombre aux échelles des galaxies : relevée, au plus ×1 000", pg);
    verifie(cible(sombre.h, 4.0) <= 4.0 + 1e-9, "image très sombre aux échelles des étoiles : au plus ×4", cible(sombre.h, 4.0));

    // Pas de bascule : la pose visée change peu quand le plafond glisse d'un cran de molette (×1,25).
    double pire = 0;
    for (double m = 4.0; m < 1000.0; m *= 1.25) {
        const double a = cible(sombre.h, m), b = cible(sombre.h, m * 1.25);
        if (std::getenv("ESSAI_DETAIL")) std::printf("   plafond %g : %g -> %g\n", m, a, b);
        pire = std::max(pire, std::fabs(std::log(b / a)));
    }
    verifie(std::exp(pire) <= 1.3, "plafond qui glisse d'un cran (×1,25) : pose visée change au plus ×1,3", std::exp(pire));

    // Pose « photo » (asinh) : la saturation est jugée sur la courbe montrée ; la même image sature plus tôt.
    Histo neb;
    neb.ajoute(1e-4, kPixels - kPixels / 50);
    neb.ajoute(1.5, kPixels / 50);      // 2 % de l'image à 1,5 : blanc en photo (asinh), pas en Reinhard (0,6)
    verifie(std::fabs(cible(neb.h, 4.0, 0.0) - 1.0) < 1e-9, "Reinhard : 2 % de l'image à 1,5 ne sature pas (pose de base)", cible(neb.h, 4.0, 0.0));
    const double pn = cible(neb.h, 4.0, 1.0);
    verifie(statsPour(neb.h, pn, 1.0).sat <= kPartMax + 1e-12 && pn < 1.0, "photo : pose baissée jusqu'à 0,5 % de blanc au plus", pn);

    // Pose réglée sur une nébuleuse : 2 % de saturé tolérés (au lieu de 0,5 %).
    Histo fond;
    fond.ajoute(1e-4, kPixels - kPixels / 100);
    fond.ajoute(5.0, kPixels / 100);      // 1 % de l'image (étoiles du fond) à 5
    verifie(cible(fond.h, 4.0, 1.0, 0.0) < 0.5, "photo sur une galaxie : 1 % d'étoiles blanches, pose baissée", cible(fond.h, 4.0, 1.0, 0.0));
    verifie(std::fabs(cible(fond.h, 4.0, 1.0, 1.0) - 1.0) < 1e-9, "photo sur une nébuleuse : 1 % d'étoiles blanches tolérées (pose de base)", cible(fond.h, 4.0, 1.0, 1.0));

    // Adaptation : continue, en logarithme, demi-temps 0,1 s vers le sombre et 0,4 s vers le clair.
    const double up = suivante(1.0, 2.0, 0.4, false), down = suivante(1.0, 0.5, 0.1, false);
    verifie(std::fabs(up - std::sqrt(2.0)) < 1e-6, "vers le clair : moitié du chemin (en IL) en 0,4 s (×2 -> ×1,41)", up);
    verifie(std::fabs(down - std::sqrt(0.5)) < 1e-6, "vers le sombre : moitié du chemin (en IL) en 0,1 s (×1/2 -> ×0,71)", down);
    double p = 1.0, sautMax = 0;
    for (int k = 0; k < 600; ++k) {      // 10 s à 60 images/s vers ×1 000
        const double q = suivante(p, 1000.0, 1.0 / 60.0, false);
        sautMax = std::max(sautMax, q / p);
        p = q;
    }
    verifie(std::fabs(p - 1000.0) < 1.0, "vers ×1 000 : atteint en 10 s", p);
    verifie(sautMax < 1.05, "vers ×1 000 : au plus 4 IL par seconde (×1,047 d'une image à la suivante)", sautMax);
    verifie(suivante(3.0, 7.0, 0.0, true) == 7.0, "contrôle sans fenêtre : pose visée tout de suite", suivante(3.0, 7.0, 0.0, true));

    std::printf("%s\n", gEchecs ? "ECHEC" : "PASSE");
    return gEchecs ? 1 : 0;
}
