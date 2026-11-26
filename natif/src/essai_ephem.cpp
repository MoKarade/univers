// Contrôle du lecteur d'éphémérides (ephemeride.h) contre JPL Horizons.
//
// Référence : app/test/nbody_ref.json (positions et vitesses publiées par Horizons, centre de masse du système
// solaire, écliptique J2000, UA et UA/jour), mise à plat par pipeline/natif/ref_ephem.py en lignes
// « nom jour_julien x y z vx vy vz ». Horizons s'appuie sur DE441, jumeau de DE440 sur cette période : l'écart
// attendu est de l'ordre du mètre pour les corps dont le fichier donne le centre.
// Lunes : pipeline/natif/ref_lunes.txt (Horizons, demandé par lunes.py --reference), lignes « code NAIF ... » ; jugées à
// 5 km (Horizons peut s'appuyer sur une solution d'orbite plus récente que le fichier téléchargé).
// Usage : essai_ephem <fichier.bsp> [autres.bsp ...] <reference.txt>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <sstream>

#include "ephemeride.h"

int main(int argc, char** argv) {
    if (argc < 3) { std::fprintf(stderr, "usage : essai_ephem <fichier.bsp> [autres.bsp ...] <reference.txt>\n"); return 2; }
    eph::Set spk;
    std::string error;
    for (int i = 1; i < argc - 1; ++i)
        if (!spk.add(argv[i], error)) { std::fprintf(stderr, "ECHEC : %s\n", error.c_str()); return 1; }

    // Corps dont DE440 donne le centre même : jugés au kilomètre. Les géantes : le fichier donne le centre de masse
    // planète + lunes ; l'écart au centre de la planète (jusqu'à quelques centaines de km) est affiché, non jugé.
    const std::map<std::string, std::pair<int, bool>> bodies = {
        {"sun", {eph::kSun, true}},         {"mercury", {eph::kMercury, true}}, {"venus", {eph::kVenus, true}},      {"emb", {eph::kEmb, true}},
        {"earth", {eph::kEarth, true}},     {"moon", {eph::kMoon, true}},       {"mars", {eph::kMarsBary, true}},    {"jupiter", {eph::kJupiterBary, false}},
        {"saturn", {eph::kSaturnBary, false}}, {"uranus", {eph::kUranusBary, false}}, {"neptune", {eph::kNeptuneBary, false}}, {"pluto", {eph::kPlutoBary, false}}};
    std::ifstream ref(argv[argc - 1]);
    std::string line;
    bool ok = true;
    int judged = 0;
    std::map<std::string, double> worstPos, worstVel;
    while (std::getline(ref, line)) {
        std::istringstream in(line);
        std::string name;
        double jd, r[3], v[3];
        if (!(in >> name >> jd >> r[0] >> r[1] >> r[2] >> v[0] >> v[1] >> v[2])) continue;
        auto it = bodies.find(name);
        const bool moon = !name.empty() && name[0] >= '0' && name[0] <= '9';      // une lune : la ligne commence par son code
        if (it == bodies.end() && !moon) continue;
        const int code = moon ? std::atoi(name.c_str()) : it->second.first;
        // Triton (801) : le seul fichier léger du NAIF qui le contient (nep097.bsp) s'écarte d'environ 255 km de la solution
        // qu'utilise Horizons aujourd'hui (0,07 % du rayon de son orbite). Écart affiché, non jugé.
        const bool judge = moon ? std::atoi(name.c_str()) != 801 : it->second.second;
        const double tolerance = moon ? 5.0 : 1.0;
        eph::Vec p, w;
        if (!spk.state(code, eph::etOfJd(jd), p, w)) {
            std::printf("%s a JJ %.1f : hors du fichier\n", name.c_str(), jd);
            continue;
        }
        p = eph::toEcliptic(p);
        w = eph::toEcliptic(w);
        const double dx = p.x - r[0] * eph::kAuKm, dy = p.y - r[1] * eph::kAuKm, dz = p.z - r[2] * eph::kAuKm;
        const double dvx = w.x - v[0] * eph::kAuKm / 86400.0, dvy = w.y - v[1] * eph::kAuKm / 86400.0, dvz = w.z - v[2] * eph::kAuKm / 86400.0;
        const double dp = std::sqrt(dx * dx + dy * dy + dz * dz), dv = std::sqrt(dvx * dvx + dvy * dvy + dvz * dvz);
        worstPos[name] = std::max(worstPos[name], dp);
        worstVel[name] = std::max(worstVel[name], dv);
        if (judge) {
            ++judged;
            if (dp > tolerance || dv > 1e-3 * tolerance) ok = false;
        }
    }
    for (const auto& [name, dp] : worstPos)
        std::printf("%-8s : ecart maximal %.6f km, %.3e km/s%s\n", name.c_str(), dp, worstVel[name],
                    bodies.count(name) && !bodies.at(name).second ? "  (centre de masse planete + lunes, non juge)" : "");
    if (judged < 10) { std::printf("trop peu de valeurs de reference (%d)\n", judged); ok = false; }
    std::printf(ok ? "PASSE\n" : "ECHEC\n");
    return ok ? 0 : 1;
}
