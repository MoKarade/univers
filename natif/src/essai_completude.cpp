// Contrôle de completude.h sur les vraies données de l'appli, chargées comme le fait la fenêtre (fenetre.cpp).
// Valeurs attendues relevées indépendamment avec numpy et Python sur les mêmes fichiers (12/11/2026) :
// 481 points d'étoiles à moins de 10 pc, dont 11 paires de deux catalogues à moins de 0,02 al ; 41 149 étoiles du
// catalogue principal sans vitesse radiale ; 70 galaxies nommées à moins de 1 Mpc du Soleil ; 20 lunes dans lunes.tsv,
// dont 15 avec un fichier de la NASA installé (pas Uranus), plus la Lune.
// Usage : essai_completude <dossier des données de l'appli, par ex. C:\dev\Univers-PC>
#include <cstdio>

#include "simulation.h"
#include "completude.h"

namespace {

int gEchecs = 0;

void verifie(bool ok, const char* quoi) {
    std::printf("%s  %s\n", ok ? "PASSE" : "ÉCHEC", quoi);
    if (!ok) ++gEchecs;
}

}  // namespace

int main(int argc, char** argv) {
    SetConsoleOutputCP(CP_UTF8);
    using namespace completude;

    verifie(entier(1580289) == "1\u202f580\u202f289", "entier : espaces fines entre milliers");
    verifie(entier(540) == "540", "entier : petit nombre");
    verifie(pourcent(0.0782) == "7,8 %", "pourcent : une décimale");
    verifie(pourcent(0.0034) == "0,34 %", "pourcent : petite part");
    verifie(pourcent(2.8e-6) == "0,00028 %", "pourcent : très petite part, sans exposant");
    verifie(echellePour(45.0 * kAuInLy) == 0 && echellePour(30) == 1 && echellePour(300) == 2 && echellePour(5e6) == 3 && echellePour(5e9) == 4,
            "echellePour : les cinq échelles de l'interface (touches 1 à 5)");
    verifie(lunesConnues() == 461, "lunes connues : 460 (JPL) + la Lune");
    if (argc < 2) {
        std::printf("Sans dossier de données : rien d'autre n'est contrôlé.\n");
        return 1;
    }

    // Chargement identique à fenetre.cpp.
    const std::string dir = argv[1];
    const Stars stars = openStars((dir + "/etoiles.bin").c_str());
    eph::Set spk;
    std::string err;
    verifie(spk.add(dir + "/de440.bsp", err), "de440.bsp lu");
    for (const char* f : {"mar099s.bsp", "jup365.bsp", "sat441.bsp", "nep097.bsp", "plu060.bsp"}) {
        std::string ignored;
        spk.add(dir + "/" + f, ignored);
    }
    std::vector<sondes::Probe> probes;
    verifie(sondes::load(dir + "/sondes.bin", probes), "sondes.bin lu");
    Sim sim;
    sim.probes = &probes;
    sim.stars = &stars;
    sim.spk = &spk;
    sim.asteroidCount = 123530;      // en-tête de asteroides.bin (lu par asteroides.h dans l'appli)
    sim.loadBodies(dir + "/etoiles_noms.tsv", dir + "/galaxies_noms.tsv", dir + "/planetes.tsv", dir + "/lunes.tsv");

    const Comptes c = compter(sim, 5566702);      // en-tête de galaxies.bin (lu par galaxies.h dans l'appli)
    std::printf("sondes %d, planètes %d, lunes %d, étoiles %llu, à moins de 10 pc %llu, doublons %llu, sans vitesse radiale %llu, Groupe local %d\n",
                c.sondes, c.planetes, lunesPresentes(c), (unsigned long long)c.etoiles, (unsigned long long)c.etoiles10pc,
                (unsigned long long)c.doublons10pc, (unsigned long long)c.principalSansVitesseRadiale, c.galaxiesGroupeLocal);
    verifie(c.planetes == 9, "8 planètes et Pluton");
    verifie(c.sondes == 5, "5 sondes : Pioneer 10 et 11, Voyager 1 et 2, New Horizons");
    verifie(c.lunes[3] == 1 && c.lunes[4] == 2 && c.lunes[5] == 4 && c.lunes[6] == 7 && c.lunes[7] == 0 && c.lunes[8] == 1 && c.lunes[9] == 1,
            "lunes par système : Terre 1, Mars 2, Jupiter 4, Saturne 7, Uranus 0 (fichier absent), Neptune 1, Pluton 1");
    verifie(c.etoiles == 6153611, "6 153 611 étoiles");
    verifie(c.etoiles10pc == 481, "481 points à moins de 10 pc (numpy : 481)");
    verifie(c.doublons10pc == 11, "11 paires de deux catalogues à moins de 0,02 al (numpy : 11)");
    verifie(c.principalSansVitesseRadiale == 41149, "41 149 étoiles du catalogue principal sans vitesse radiale (numpy : 41 149)");
    verifie(c.galaxiesGroupeLocal == 70, "70 galaxies nommées à moins de 1 Mpc du Soleil (Python : 70)");

    const auto r = rapport(c);
    for (const Echelle& e : r) {
        std::printf("\n%s\n  présent : %s\n  précision : %s\n  mesuré ou calculé : %s\n", e.nom, e.complet.c_str(), e.precision.c_str(), e.mesure.c_str());
        for (const Ligne& l : e.lignes) std::printf("    - %s : %s [%s] (%s)\n", l.quoi.c_str(), l.valeur.c_str(), motNature(l.nature), l.source.c_str());
        for (const std::string& m : e.manques) std::printf("    manque : %s\n", m.c_str());
    }
    std::printf("\n");
    verifie(std::fabs(r[1].part - 470.0 / 540.0) < 1e-12, "voisinage : (481 - 11) / 540");
    verifie(std::fabs(r[2].part - 6153611.0 / 1811709771.0) < 1e-15, "Voie lactée : part de Gaia DR3");
    verifie(std::fabs(r[3].part - 70.0 / 113.0) < 1e-12, "Groupe local : 70 / 113");
    return gEchecs ? 1 : 0;
}
