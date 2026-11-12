// Contrôle des trajectoires des sondes (sondes.h) contre JPL Horizons à des dates situées ENTRE deux valeurs du fichier
// (là où l'appli interpole). Référence : pipeline/natif/ref_sondes.txt (« Nom jour_julien x y z », km, par rapport au
// Soleil, écliptique J2000), demandée à Horizons. Tolérance : 100 km, en croisière comme pendant un survol (Voyager 1 à
// Jupiter, 5 mars 1979 ; Voyager 2 à Neptune, 25 août 1989 ; New Horizons à Pluton, 14 juillet 2015), où le fichier donne
// une valeur toutes les 10 minutes (avec une valeur par jour, l'écart mesuré atteignait 168 000 km).
// Second contrôle : distance de Voyager 1 au Soleil le 12 novembre 2026, entre 165 et 175 fois la distance Terre-Soleil.
// Usage : essai_sondes <sondes.bin> <ref_sondes.txt>
#include <cmath>
#include <fstream>
#include <sstream>

#include "sondes.h"

int main(int argc, char** argv) {
    if (argc < 3) { std::fprintf(stderr, "usage : essai_sondes <sondes.bin> <ref_sondes.txt>\n"); return 2; }
    std::vector<sondes::Probe> probes;
    if (!sondes::load(argv[1], probes)) { std::fprintf(stderr, "ECHEC : fichier des sondes illisible\n"); return 1; }
    bool ok = true;
    int judged = 0;
    std::ifstream ref(argv[2]);
    std::string line;
    while (std::getline(ref, line)) {
        std::istringstream in(line);
        std::string name;
        double jd, r[3];
        if (!(in >> name >> jd >> r[0] >> r[1] >> r[2])) continue;
        for (char& c : name)
            if (c == '_') c = ' ';
        for (const auto& p : probes) {
            if (p.name != name) continue;
            double pos[3], vel[3];
            if (!p.at(jd, pos, vel)) { std::printf("%s au JJ %.1f : hors de la trajectoire\n", name.c_str(), jd); ok = false; continue; }
            const double d = std::sqrt((pos[0] - r[0]) * (pos[0] - r[0]) + (pos[1] - r[1]) * (pos[1] - r[1]) + (pos[2] - r[2]) * (pos[2] - r[2]));
            const bool flyby = std::fabs(jd - 2443938.0) < 3 || std::fabs(jd - 2447763.6) < 3 || std::fabs(jd - 2457217.0) < 3;
            const bool good = d < 100.0;
            ok &= good;
            ++judged;
            std::printf("%-13s JJ %.1f%s : ecart avec Horizons %.1f km -> %s\n", name.c_str(), jd, flyby ? " (survol)" : "", d, good ? "PASSE" : "ECHEC");
        }
    }
    if (judged < 5) { std::printf("trop peu de valeurs de reference (%d)\n", judged); ok = false; }
    for (const auto& p : probes)
        if (p.name == "Voyager 1") {
            double pos[3], vel[3];
            const bool have = p.at(2461356.5, pos, vel);
            const double au = have ? std::sqrt(pos[0] * pos[0] + pos[1] * pos[1] + pos[2] * pos[2]) / 149597870.7 : 0;
            const bool good = have && au > 165 && au < 175;
            ok &= good;
            std::printf("Voyager 1 le 12 novembre 2026 : %.1f fois la distance Terre-Soleil (attendu entre 165 et 175) -> %s\n", au, good ? "PASSE" : "ECHEC");
        }
    std::printf(ok ? "PASSE\n" : "ECHEC\n");
    return ok ? 0 : 1;
}
