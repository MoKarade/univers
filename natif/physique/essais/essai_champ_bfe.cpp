// Essai de champ_bfe.h : le lecteur C++ doit redonner exactement (à l'arrondi près) le potentiel et la force que calcule
// pipeline/champ/champ_bfe.py sur le même fichier.
//
// Usage : essai_champ_bfe <champ.chp> <points.txt>
//   Les deux fichiers sont écrits par : python pipeline/champ/test_champ.py --reference <dossier>
//   points.txt : une ligne par point, x y z phi Fx Fy Fz (valeurs de Python).
// Rend 0 si l'écart relatif de la force est partout sous 1e-5. La dernière ligne dit PASSE ou ECHEC.
#include <cmath>
#include <cstdio>
#include <string>

#include "../champ_bfe.h"

int main(int argc, char** argv) {
    if (argc < 3) { std::printf("usage : essai_champ_bfe <champ.chp> <points.txt>\n"); return 2; }
    phys::champ::Champ C;
    std::string err;
    if (!C.charger(argv[1], err)) { std::printf("ECHEC : %s\n", err.c_str()); return 1; }
    FILE* fh = std::fopen(argv[2], "r");
    if (!fh) { std::printf("ECHEC : %s introuvable\n", argv[2]); return 1; }
    double x[3], phi, F[3], e = 0, ep = 0;
    int n = 0;
    while (std::fscanf(fh, "%lf %lf %lf %lf %lf %lf %lf", &x[0], &x[1], &x[2], &phi, &F[0], &F[1], &F[2]) == 7) {
        double p, G[3];
        C.evaluer(x, p, G);
        const double nf = std::sqrt(F[0] * F[0] + F[1] * F[1] + F[2] * F[2]);
        const double d = std::sqrt((G[0] - F[0]) * (G[0] - F[0]) + (G[1] - F[1]) * (G[1] - F[1]) + (G[2] - F[2]) * (G[2] - F[2]));
        e = std::fmax(e, d / nf);
        ep = std::fmax(ep, std::fabs(p - phi) / std::fabs(phi));
        ++n;
    }
    std::fclose(fh);
    std::printf("%d points ; masse %.4g M☉ ; disque : %s ; écart relatif au plus : force %.2e, potentiel %.2e\n", n, C.masse,
                C.aDisque ? "oui" : "non", e, ep);
    const bool ok = n > 0 && e < 1e-5 && ep < 1e-5;
    std::printf("%s\n", ok ? "PASSE" : "ECHEC");
    return ok ? 0 : 1;
}
