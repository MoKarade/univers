// Essai d'ENSEMBLE, sans fenêtre : la continuité des astres nommés à travers le temps.
//
// Règle visée (docs/analyse-architecture.md, § 5.2) : « un objet, une histoire ». Un astre ne doit ni apparaître ni
// disparaître quand la date change (sauf s'il naît ou meurt), et sa place ne doit pas sauter. Les autres essais contrôlent
// chaque pièce seule ; celui-ci parcourt toute la plage de dates de l'appli avec le même état que la fenêtre (Sim) et
// relève chaque cassure : la date, la famille d'astres, combien, et le saut de position quand l'astre existe des deux côtés.
//
// Ce qu'il ne voit pas : ce qui n'est pas un astre nommé (nuages d'étoiles Gaia, points des calculs de galaxies, scénarios,
// galaxies des relevés) ; leurs fondus sont décidés dans fenetre.cpp et ne sont pas des états de Sim.
//
// Usage : essai_continuite <etoiles.bin> [--max N]
//   Sans --max : imprime les cassures, rend 1 s'il y en a.
//   Avec --max N : rend 0 tant que le nombre de cassures ne dépasse pas N (référence qui ne doit que baisser).
#include "commun.h"

#include <atomic>
#include <filesystem>
#include <map>
#include <thread>

#include "simulation.h"

namespace {

const char* famille(const Sim& sim, size_t i) {
    const Body& b = sim.bodies[i];
    switch (b.kind) {
    case Kind::Sun: return "Soleil";
    case Kind::Star: return "étoiles nommées";
    case Kind::Probe: return "sondes";
    case Kind::Asteroid: return "astéroïde désigné";
    case Kind::Planet:
        if (b.naif == eph::kMoon) return "Lune";
        return b.parent == 0 ? "planètes" : "lunes des autres planètes";
    case Kind::Galaxy:
        if (b.name == "Centre de la Voie lactée") return "centre de la Voie lactée";
        return b.priority >= 9 ? "galaxies à distance mesurée (Cosmicflows-4)" : "galaxies du Groupe local et voisines";
    }
    return "?";
}

std::string duree(double years) {      // écart à aujourd'hui, en mots
    const double a = std::fabs(years);
    char b[64];
    if (a < 1.0e4) std::snprintf(b, sizeof(b), "%.0f ans", a);
    else if (a < 1.0e6) std::snprintf(b, sizeof(b), "%.0f milliers d'années", a / 1.0e3);
    else if (a < 1.0e9) std::snprintf(b, sizeof(b), "%.1f millions d'années", a / 1.0e6);
    else std::snprintf(b, sizeof(b), "%.2f milliards d'années", a / 1.0e9);
    return std::string(years < 0 ? "il y a " : "dans ") + b;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) { std::printf("usage : essai_continuite <etoiles.bin> [--max N]\n"); return 2; }
    long maxBreaks = -1;
    for (int k = 2; k + 1 < argc; ++k)
        if (std::string(argv[k]) == "--max") maxBreaks = std::atol(argv[k + 1]);
    const std::string chemin = argv[1], dossier = chemin.substr(0, chemin.find_last_of("\\/"));
    const Stars stars = openStars(chemin.c_str());
    eph::Set spk;
    std::string err;
    if (!spk.add(dossier + "/de440.bsp", err)) { std::printf("ECHEC : %s\n", err.c_str()); return 1; }
    for (const char* f : {"mar099s.bsp", "jup365.bsp", "sat441.bsp", "nep097.bsp", "plu060.bsp", "ura184_part-3.bsp", "ura116xl.bsp", "sat415.bsp", "nep104.bsp",
                          "nep105.bsp", "jup347.bsp", "jup348.bsp", "jup349.bsp", "sat455.bsp", "sat456.bsp", "sat457.bsp", "sat459.bsp"}) {
        std::string ignore;
        spk.add(dossier + "/" + f, ignore);
    }
    // Système solaire hors des éphémérides : préparé comme dans fenetre.cpp, attendu ici avant de commencer.
    phys::SystemeSolaire outer;
    const phys::SourceDe440 source = [&](int naif, double jd, phys::Vec3& p, phys::Vec3& v) {
        eph::Vec a, w;
        if (!spk.state(naif, eph::etOfJd(jd), a, w)) return false;
        a = eph::toEcliptic(a); w = eph::toEcliptic(w);
        p = {a.x, a.y, a.z}; v = {w.x, w.y, w.z};
        return true;
    };
    const std::string reserve = dossier + "/reserve_systeme_solaire.bin";
    const bool outerOk = outer.chargerReserve(reserve, source, 20000.0) || outer.construire(source, 20000.0);
    if (outerOk) outer.chargerTable(dossier + "/orbites_planetes.bin");
    std::vector<sondes::Probe> probes;
    const bool hasProbes = sondes::load(dossier + "/sondes.bin", probes);

    Sim sim;
    sim.stars = &stars;
    sim.spk = &spk;
    sim.probes = hasProbes ? &probes : nullptr;
    sim.loadBodies(dossier + "/etoiles_noms.tsv", dossier + "/galaxies_noms.tsv", dossier + "/planetes.tsv", dossier + "/lunes.tsv");
    if (outerOk) sim.outer = &outer;
    phys::fusion::Rejeu replay;      // même choix de dossier que fenetre.cpp
    const std::string fusionDir = dossier + (std::filesystem::exists(dossier + "/fusion-toutes/fusion_centres.bin") ? "/fusion-toutes"
                                             : std::filesystem::exists(dossier + "/fusion-3m/fusion_centres.bin") ? "/fusion-3m" : "/fusion");
    const bool hasReplay = replay.charger(fusionDir + "/fusion_centres.bin", "");
    sim.linkReplay(hasReplay ? &replay : nullptr, fusionDir + "/fusion_noms.tsv");
    sim.paused = true;
    sim.touched = true;

    const size_t n = sim.bodies.size();
    // État à `t` ans d'aujourd'hui : qui est montré, et où.
    auto etat = [&](double t, std::vector<char>& vu, std::vector<Vec3>* pos) {
        sim.years = kStartYears + t;
        sim.focus = 0;
        sim.advance(0.0);
        vu.resize(n);
        if (pos) pos->resize(n);
        for (size_t i = 0; i < n; ++i) {
            vu[i] = sim.visible(static_cast<int>(i)) ? 1 : 0;
            if (pos && vu[i] && sim.bodies[i].kind != Kind::Star) (*pos)[i] = sim.position(static_cast<int>(i));
        }
    };
    const double tMin = sim.minYears() - kStartYears, tMax = sim.maxYears() - kStartYears;
    std::printf("Plage de dates de l'appli : de %s à %s ; %zu astres nommés ; calcul de la rencontre : %s\n", duree(tMin).c_str(), duree(tMax).c_str(), n,
                hasReplay ? fusionDir.c_str() : "absent");

    // Dates d'essai : de 1 an à la borne, 16 par décade, de chaque côté d'aujourd'hui.
    struct Cassure { double t; std::string fam; long apparus = 0, disparus = 0; double saut = 0; std::string exemple; };
    std::vector<Cassure> cassures;
    for (int sens = -1; sens <= 1; sens += 2) {
        const double borne = sens < 0 ? -tMin : tMax;
        std::vector<double> grille{0.0};
        for (double e = 0.0; std::pow(10.0, e) < borne; e += 1.0 / 16.0) grille.push_back(std::pow(10.0, e));
        grille.push_back(borne);
        std::vector<char> avant, apres, m;
        etat(0.0, avant, nullptr);
        for (size_t g = 1; g < grille.size(); ++g) {
            etat(sens * grille[g], apres, nullptr);
            if (apres != avant) {      // quelque chose est apparu ou a disparu entre deux dates d'essai : on cherche la date
                // Plusieurs familles peuvent changer dans le même intervalle : une dichotomie par famille.
                std::map<std::string, std::pair<long, long>> fams;
                for (size_t i = 0; i < n; ++i)
                    if (avant[i] != apres[i]) (apres[i] ? fams[famille(sim, i)].first : fams[famille(sim, i)].second)++;
                for (const auto& [fam, compte] : fams) {
                    double lo = grille[g - 1], hi = grille[g];
                    size_t temoin = n;
                    for (size_t i = 0; i < n && temoin == n; ++i)
                        if (avant[i] != apres[i] && fam == famille(sim, i)) temoin = i;
                    for (int it = 0; it < 40 && hi - lo > 1e-6 * std::max(hi, 1.0); ++it) {
                        const double mid = 0.5 * (lo + hi);
                        etat(sens * mid, m, nullptr);
                        (m[temoin] == avant[temoin] ? lo : hi) = mid;
                    }
                    cassures.push_back({sens * hi, fam, compte.first, compte.second, 0, sim.bodies[temoin].name});
                }
            }
            avant = apres;
        }
    }
    // Sauts de position sans disparition : aux dates où l'appli change de source (bornes des éphémérides, ±3 millions
    // d'années pour les galaxies, ±20 000 ans et ±10 millions d'années pour les planètes) et à chaque cassure trouvée.
    std::vector<double> dates;
    for (const Cassure& c : cassures) dates.push_back(c.t);
    for (double t : {kLinearLimitYears, -kLinearLimitYears, 1550.0 - 2000.0 - kStartYears, 2650.0 - 2000.0 - kStartYears, 2.0e4, -2.0e4, 1.0e7, -1.0e7})
        dates.push_back(t);
    for (double t : dates) {
        // Trois dates serrées avant, une après : le saut est ce qui dépasse le mouvement normal sur le même écart de temps.
        const double h = std::max(std::fabs(t) * 1e-5, 1e-3), s = t < 0 ? -1.0 : 1.0;
        std::vector<char> v0, v1, v2;
        std::vector<Vec3> p0, p1, p2;
        etat(t - s * 2 * h, v0, &p0);
        etat(t - s * h, v1, &p1);
        etat(t + s * h, v2, &p2);
        std::map<std::string, std::pair<double, std::string>> pire;
        for (size_t i = 0; i < n; ++i) {
            if (!v0[i] || !v1[i] || !v2[i] || sim.bodies[i].kind == Kind::Star || sim.bodies[i].kind == Kind::Sun) continue;
            const Vec3 a = p1[i] - p0[i], b = p2[i] - p1[i];
            const double normal = std::sqrt(dot(a, a)) * 2.0, vrai = std::sqrt(dot(b, b));      // l'intervalle d'après est deux fois plus long
            const double saut = vrai - 3.0 * normal;      // marge : le mouvement peut tourner
            const double grandeur = std::sqrt(dot(p1[i], p1[i]));
            if (saut > 1e-9 * std::max(grandeur, 1e-12) && saut > pire[famille(sim, i)].first) pire[famille(sim, i)] = {saut, sim.bodies[i].name};
        }
        for (const auto& [fam, w] : pire) {
            bool joint = false;
            for (Cassure& c : cassures)
                if (c.fam == fam && std::fabs(c.t - t) <= 4 * h) { c.saut = std::max(c.saut, w.first); joint = true; }
            if (!joint) cassures.push_back({t, fam, 0, 0, w.first, w.second});
        }
    }
    std::sort(cassures.begin(), cassures.end(), [](const Cassure& a, const Cassure& b) { return a.t < b.t; });
    std::printf("\n%-30s %-46s %9s %9s  %s\n", "date", "famille", "apparus", "disparus", "saut de position (exemple)");
    for (const Cassure& c : cassures) {
        char saut[96] = "";
        if (c.saut > 0) {
            if (c.saut * kLyInKm < 1.0e9) std::snprintf(saut, sizeof(saut), "%.0f km", c.saut * kLyInKm);
            else std::snprintf(saut, sizeof(saut), "%.3g années-lumière", c.saut);
        }
        std::printf("%-30s %-46s %9ld %9ld  %s (%s)\n", duree(c.t).c_str(), c.fam.c_str(), c.apparus, c.disparus, saut, c.exemple.c_str());
    }
    const long total = static_cast<long>(cassures.size());
    std::printf("\n%ld cassures de continuité relevées.\n", total);
    const bool ok = maxBreaks >= 0 ? total <= maxBreaks : total == 0;
    if (maxBreaks >= 0) std::printf("Référence : au plus %ld. %s\n", maxBreaks, ok ? "Pas de nouvelle cassure." : "NOUVELLES CASSURES.");
    std::printf(ok ? "PASSE\n" : "ECHEC\n");
    return ok ? 0 : 1;
}
