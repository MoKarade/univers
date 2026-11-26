// Contrôle sans fenêtre : les planètes restent visibles quand le temps défile très vite hors de la plage de la NASA.
// Reproduit le trajet du fil appli PC (de 2026,86 à l'an 5000 par pas de 166,7 ans, 10 000 ans par seconde à 60 images
// par seconde), avec la même suite d'appels que fenetre.cpp : Sim::advance à chaque image, calcul du système solaire
// préparé dans un fil à part et branché dès qu'il est prêt. Puis 600 images de plus à l'arrivée.
// Usage : essai_temps_rapide <etoiles.bin> [pas en années] [arrivée en années depuis J2000]
#include "commun.h"

#include <atomic>
#include <thread>

#include "simulation.h"

using namespace univers;      // en-têtes de l'appli (natif/src), autrefois en espace de noms anonyme

int main(int argc, char** argv) {
    if (argc < 2) { std::printf("usage : essai_temps_rapide <etoiles.bin> [pas en années] [arrivée]\n"); return 2; }
    const double pas = argc > 2 ? std::atof(argv[2]) : 166.67, arrivee = argc > 3 ? std::atof(argv[3]) : 3000.0;
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
    phys::SystemeSolaire outer;
    std::atomic<bool> pret{false};
    std::thread fil([&] {
        const phys::SourceDe440 source = [&](int naif, double jd, phys::Vec3& p, phys::Vec3& v) {
            eph::Vec a, w;
            if (!spk.state(naif, eph::etOfJd(jd), a, w)) return false;
            a = eph::toEcliptic(a); w = eph::toEcliptic(w);
            p = {a.x, a.y, a.z}; v = {w.x, w.y, w.z};
            return true;
        };
        const std::string reserve = dossier + "/reserve_systeme_solaire.bin";      // comme fenetre.cpp
        if (outer.chargerReserve(reserve, source, 20000.0) || (outer.construire(source, 20000.0) && (outer.sauver(reserve), true))) { outer.chargerTable(dossier + "/orbites_planetes.bin"); pret = true; }
    });
    Sim sim;
    sim.stars = &stars;
    sim.spk = &spk;
    sim.loadBodies(dossier + "/etoiles_noms.tsv", dossier + "/galaxies_noms.tsv", dossier + "/planetes.tsv", dossier + "/lunes.tsv");
    int mars = -1, jupiter = -1;
    for (size_t i = 0; i < sim.bodies.size(); ++i) {
        if (sim.bodies[i].name == "Mars") mars = static_cast<int>(i);
        if (sim.bodies[i].name == "Jupiter") jupiter = static_cast<int>(i);
    }
    sim.years = 26.86;
    sim.paused = true;      // la date est menée ici, comme le trajet de contrôle
    int image = 0, cachees = 0, branche = -1;
    auto une = [&](double y) {
        if (!sim.outer && pret) { sim.outer = &outer; branche = image; }
        sim.years = y;
        sim.advance(1.0 / 60.0);
        const bool vu = sim.planetValid[mars] && sim.planetValid[jupiter];
        if (!vu && sim.outer) ++cachees;
        if (image % 60 == 0 || (!vu && sim.outer && cachees < 5))
            std::printf("image %5d  an %8.1f  calcul %s  Mars %s  Jupiter %s  (%s)\n", image, 2000 + y, sim.outer ? "prêt" : "en préparation", sim.planetValid[mars] ? "oui" : "NON",
                        sim.planetValid[jupiter] ? "oui" : "NON", sim.planetMethod);
        ++image;
    };
    for (double y = 26.86; y < arrivee; y += pas) une(y);
    while (!pret) { une(arrivee); Sleep(16); }
    for (int k = 0; k < 600; ++k) une(arrivee);
    fil.join();
    std::printf("calcul branché à l'image %d ; images avec le calcul prêt mais Mars ou Jupiter cachée : %d\n", branche, cachees);
    std::printf(cachees ? "ECHEC\n" : "PASSE\n");
    return cachees ? 1 : 0;
}
