// Contrôle du lecteur d'éphémérides (ephemeride.h) contre JPL Horizons.
//
// Référence : app/test/nbody_ref.json (positions et vitesses publiées par Horizons, centre de masse du système
// solaire, écliptique J2000, UA et UA/jour), mise à plat par pipeline/natif/ref_ephem.py en lignes
// « nom jour_julien x y z vx vy vz ». Horizons s'appuie sur DE441, jumeau de DE440 sur cette période : l'écart
// attendu est de l'ordre du mètre pour les corps dont le fichier donne le centre.
// Usage : essai_ephem <de440.bsp> <reference.txt>
#include <cstdio>
#include <fstream>
#include <map>
#include <sstream>

#include "ephemeride.h"

int main(int argc, char** argv) {
    if (argc < 3) { std::fprintf(stderr, "usage : essai_ephem <de440.bsp> <reference.txt>\n"); return 2; }
    eph::Spk spk;
    std::string error;
    if (!spk.open(argv[1], error)) { std::fprintf(stderr, "ECHEC : %s\n", error.c_str()); return 1; }
    std::printf("plage du fichier : annees %.1f a %.1f\n", 2000.0 + spk.firstEt() / 31557600.0, 2000.0 + spk.lastEt() / 31557600.0);

    // Corps dont DE440 donne le centre même : jugés au kilomètre. Les géantes : le fichier donne le centre de masse
    // planète + lunes ; l'écart au centre de la planète (jusqu'à quelques centaines de km) est affiché, non jugé.
    const std::map<std::string, std::pair<int, bool>> bodies = {
        {"sun", {eph::kSun, true}},         {"mercury", {eph::kMercury, true}}, {"venus", {eph::kVenus, true}},      {"emb", {eph::kEmb, true}},
        {"earth", {eph::kEarth, true}},     {"moon", {eph::kMoon, true}},       {"mars", {eph::kMarsBary, true}},    {"jupiter", {eph::kJupiterBary, false}},
        {"saturn", {eph::kSaturnBary, false}}, {"uranus", {eph::kUranusBary, false}}, {"neptune", {eph::kNeptuneBary, false}}, {"pluto", {eph::kPlutoBary, false}}};
    std::ifstream ref(argv[2]);
    std::string line;
    bool ok = true;
    int judged = 0;
    std::map<std::string, double> worstPos, worstVel;
    while (std::getline(ref, line)) {
        std::istringstream in(line);
        std::string name;
        double jd, r[3], v[3];
        if (!(in >> name >> jd >> r[0] >> r[1] >> r[2] >> v[0] >> v[1] >> v[2])) continue;
        const auto it = bodies.find(name);
        if (it == bodies.end()) continue;
        eph::Vec p, w;
        if (!spk.state(it->second.first, eph::etOfJd(jd), p, w)) {
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
        if (it->second.second) {
            ++judged;
            if (dp > 1.0 || dv > 1e-5) ok = false;
        }
    }
    for (const auto& [name, dp] : worstPos)
        std::printf("%-8s : ecart maximal %.6f km, %.3e km/s%s\n", name.c_str(), dp, worstVel[name], bodies.at(name).second ? "" : "  (centre de masse planete + lunes, non juge)");
    if (judged < 10) { std::printf("trop peu de valeurs de reference (%d)\n", judged); ok = false; }
    std::printf(ok ? "PASSE\n" : "ECHEC\n");
    return ok ? 0 : 1;
}
