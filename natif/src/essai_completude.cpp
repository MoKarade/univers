// Contrôle de completude.h sur les vraies données de l'appli, chargées comme le fait la fenêtre (fenetre.cpp).
// Valeurs attendues relevées indépendamment avec numpy et Python sur les mêmes fichiers (12/11/2026) :
// 481 points d'étoiles à moins de 10 pc, dont 11 paires de deux catalogues à moins de 0,02 al ; 41 149 étoiles du
// catalogue principal sans vitesse radiale (avant etoiles_sans_vr.txt) ; galaxies du Groupe local : completude_groupe_local.h ;
// dont 15 avec un fichier de la NASA installé (pas Uranus), plus la Lune.
// Usage : essai_completude <dossier des données de l'appli, par ex. C:\dev\Univers-PC>
#include <cstdio>
#include <fstream>

#include "simulation.h"
#include "completude.h"

using namespace univers;      // en-têtes de l'appli (natif/src), autrefois en espace de noms anonyme

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
    verifie(pourcent(1580289.0 / 1580368.0) == "99,995 %", "pourcent : presque complet n'est jamais écrit 100 %");
    verifie(pourcent(1.0) == "100 %", "pourcent : complet");
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
    for (const char* f : {"mar099s.bsp", "jup365.bsp", "sat441.bsp", "nep097.bsp", "plu060.bsp", "ura184_part-3.bsp", "ura116xl.bsp", "sat415.bsp",
                          "nep104.bsp", "nep105.bsp", "jup347.bsp", "jup348.bsp", "jup349.bsp", "sat455.bsp", "sat456.bsp", "sat457.bsp", "sat459.bsp"}) {
        std::string ignored;
        spk.add(dir + "/" + f, ignored);
    }
    std::vector<sondes::Probe> probes;
    verifie(sondes::load(dir + "/sondes.bin", probes), "sondes.bin lu");
    Sim sim;
    sim.probes = &probes;
    sim.stars = &stars;
    sim.spk = &spk;
    asteroides::Catalogue asteroidCat;
    verifie(asteroidCat.load(dir + "/asteroides.bin", dir + "/asteroides_noms.txt"), "catalogue des petits corps lu");
    sim.asteroidCat = &asteroidCat;
    {      // en-tête de asteroides.bin, lu comme asteroides.h dans l'appli
        std::ifstream af(dir + "/asteroides.bin", std::ios::binary);
        char h[16] = {};
        af.read(h, 16);
        if (af && std::memcmp(h, "UNIVAST1", 8) == 0) std::memcpy(&sim.asteroidCount, h + 8, 8);
    }
    sim.loadBodies(dir + "/etoiles_noms.tsv", dir + "/galaxies_noms.tsv", dir + "/planetes.tsv", dir + "/lunes.tsv");

    const Comptes c = compter(sim, 5566702, 0, "", "", dir);      // 5566702 : en-tête de galaxies.bin ; dir : etoiles_sans_vr.txt

    // Avec Gaia et la Voie lactée chargés (gaia.bin : en-tête lu ici comme le fait gaia.h).
    uint64_t nGaia = 0;
    {
        std::ifstream gf(dir + "/gaia.bin", std::ios::binary);
        char h[16] = {};
        gf.read(h, 16);
        if (gf && std::memcmp(h, "UNIVGAI1", 8) == 0) std::memcpy(&nGaia, h + 8, 8);
    }
    // 98 278 350 : gaia.bin réécrit le 12/11/2026 à 18 h 36, après ce contrôle (98 278 356 à la première conversion,
    // docs/gaia-voie-lactee.md) ; c'est le fichier installé et chargé par l'appli.
    verifie(nGaia == 98278350, "gaia.bin : 98 278 350 étoiles (fichier installé, 12/11/2026 18 h 36)");
    sim.hasGaia = nGaia > 0;
    sim.hasMilkyWay = true;
    const auto rg = rapport(compter(sim, 5566702, nGaia));
    verifie(std::fabs(rg[2].part - (58967.0 + 98278350.0) / 1811709771.0) < 1e-15, "Voie lactée avec Gaia : (58 967 + 98 278 350) / Gaia DR3");
    std::printf("Voie lactée avec Gaia : %s\n  %s\n  %s\n", rg[2].complet.c_str(), rg[2].precision.c_str(), rg[2].mesure.c_str());
    for (const Ligne& l : rg[2].lignes) std::printf("    - %s : %s [%s]\n", l.quoi.c_str(), l.valeur.c_str(), motNature(l.nature));
    // Choix de Marc (12/11) : lueur modèle retirée. Gaia chargé sans Voie lactée : aucune ligne « supposé » ni « ajusté ».
    sim.hasMilkyWay = false;
    const auto rs = rapport(compter(sim, 5566702, nGaia));
    bool sansModele = true;
    for (const Ligne& l : rs[2].lignes) sansModele = sansModele && l.nature != Nature::Suppose && l.nature != Nature::Ajuste;
    verifie(sansModele && rs[2].mesure.find("pas dessinée") != std::string::npos, "Gaia sans Voie lactée modèle : rien de supposé ni d'ajusté");
    // Lumière additionnée des autres sources Gaia (gaia_agrege.bin, format v2 : seules les sources à parallaxe fiable sont
    // placées en volume). Attendu (numpy, 12/11) : 93 831 724 sources dans les cases placées à leur distance, 69,7 % de la
    // lumière sans distance.
    sim.hasGaia = true;
    sim.hasMilkyWay = false;
    const Comptes ca = compter(sim, 5566702, nGaia, dir + "/gaia_agrege.bin");
    // Voisinage lu dans gaia.bin (feuilles près du Soleil). Attendu (numpy, 12/11) : 150 étoiles Gaia à moins de 10 pc, dont 77
    // avec vitesse radiale mesurée ; 317 étoiles du catalogue principal (etoiles.bin).
    const Comptes cv = compter(sim, 5566702, nGaia, "", dir + "/gaia.bin");
    verifie(cv.voisinageGaia && cv.gaia10pc == 150 && cv.gaia10pcVitesseRadiale == 77, "gaia.bin : 150 étoiles à moins de 10 pc, 77 avec vitesse radiale (numpy)");
    verifie(cv.etoiles10pcCatalogue[0] == 317, "catalogue principal : 317 étoiles à moins de 10 pc (numpy)");
    const auto rv = rapport(cv);
    verifie(std::fabs(rv[1].part - 467.0 / 540.0) < 1e-12, "voisinage avec Gaia : (317 + 150) / 540");
    std::printf("Voisinage avec Gaia : %s\n  %s\n  %s\n", rv[1].complet.c_str(), rv[1].precision.c_str(), rv[1].mesure.c_str());
    verifie(!compter(sim, 5566702, nGaia, "", dir + "/absent.bin").voisinageGaia, "gaia.bin absent : voisinage compté dans etoiles.bin");
    // Depuis le 13/11/2026 (gaia_tuiles.py), les sources à parallaxe entre 5 et 10 erreurs sont dessinées une à une
    // (gaia_b.bin) : gaia_agrege.bin n'a plus de cases placées en volume ; toute sa lumière est « sans distance ».
    verifie(ca.agrege && ca.additionneesPlacees == 0, "gaia_agrege.bin : plus de cases en volume (sources placées dans gaia_b.bin)");
    verifie(std::fabs(ca.lumiereSansDistance - 1.0) < 1e-12, "lumière additionnée : 100 % sans distance");
    uint64_t nGaiaB = 0;
    {
        std::ifstream gf(dir + "/gaia_b.bin", std::ios::binary);
        char h[16] = {};
        gf.read(h, 16);
        if (gf && std::memcmp(h, "UNIVGAI1", 8) == 0) std::memcpy(&nGaiaB, h + 8, 8);
    }
    verifie(nGaiaB == 93831436, "gaia_b.bin : 93 831 436 étoiles (fichier installé, 13/11/2026)");
    const auto ra = rapport(compter(sim, 5566702, nGaia + nGaiaB, dir + "/gaia_agrege.bin"));
    verifie(std::fabs(ra[2].part - (98278350.0 + 93831436.0 + 1707918961.0 - 93861853.0) / 1811709771.0) < 1e-15,
            "Voie lactée : (gaia.bin + gaia_b.bin + additionnées sans le jeu B) / Gaia DR3");
    std::printf("Voie lactée avec les sources additionnées : %s\n  %s\n", ra[2].complet.c_str(), ra[2].precision.c_str());
    verifie(!compter(sim, 5566702, nGaia, dir + "/absent.bin").agrege, "gaia_agrege.bin absent : rien d'additionné");
    sim.hasGaia = sim.hasMilkyWay = false;
    verifie(compter(sim, 5566702, nGaia).etoilesGaia == 0, "sans Gaia chargé : compte de gaia.bin ignoré");

    std::printf("sondes %d, planètes %d, lunes %d, étoiles %llu, à moins de 10 pc %llu, doublons %llu, sans vitesse radiale %llu, Groupe local %d\n",
                c.sondes, c.planetes, lunesPresentes(c), (unsigned long long)c.etoiles, (unsigned long long)c.etoiles10pc,
                (unsigned long long)c.doublons10pc, (unsigned long long)c.principalSansVitesseRadiale, c.galaxiesGroupeLocal);
    verifie(c.planetes == 9, "8 planètes et Pluton");
    verifie(c.asteroides == 1580289, "1 580 289 astéroïdes : toute la base du JPL (asteroides_jpl.py, 8 écartés)");
    {
        const auto rs = rapport(c);
        bool phrase = false;
        for (const std::string& m : rs[0].manques) phrase = phrase || m.find("astéroïdes de la base du JPL absents") != std::string::npos;
        verifie(phrase && rs[0].manques[1].find("79 ") == 0, "astéroïdes absents : 1 580 368 - 1 580 289 = 79");
    }
    verifie(c.cometes == 1778 && c.asteroides == 1580289, "1 778 comètes (docs/plan-natif.md) et 1 580 289 astéroïdes, séparés");
    {
        const auto rs = rapport(c);
        bool raisons = false;
        for (const std::string& m : rs[0].manques) raisons = raisons || m.find("2 310 comètes : 2 244") == 0;
        verifie(raisons, "comètes absentes : 2 310 = 2 244 orbites ouvertes + 39 disparues + 27 sans orbite à jour");
    }
    verifie(c.sondes == 5, "5 sondes : Pioneer 10 et 11, Voyager 1 et 2, New Horizons");
    // Attendu : lunes.tsv relu en Python (colonne « planète »), 12/11 19 h UTC : 437 lunes, plus la Lune.
    verifie(c.lunes[3] == 1 && c.lunes[4] == 2 && c.lunes[5] == 116 && c.lunes[6] == 290 && c.lunes[7] == 15 && c.lunes[8] == 9 && c.lunes[9] == 5,
            "lunes par système : Terre 1, Mars 2, Jupiter 116, Saturne 290, Uranus 15, Neptune 9, Pluton 5 (codes provisoires compris)");
    verifie(systemeDeLaLune(55501) == 5 && systemeDeLaLune(65067) == 6 && systemeDeLaLune(85051) == 8 && systemeDeLaLune(301) == 3, "système d'une lune : premier chiffre du code");
    verifie(lunesPresentesConnues(c) == 1 + 2 + 115 + 290 + 15 + 9 + 5, "lunes comptées au plus jusqu'au nombre reconnu (Jupiter : 116 chargées, 115 reconnues)");
    verifie(c.etoiles == 6153611, "6 153 611 étoiles");
    verifie(c.etoiles10pc == 481, "481 points à moins de 10 pc (numpy : 481)");
    // Catalogue principal à pleine précision (2e57b01) : 12 paires (numpy) ; avant, arrondi par la page : 11.
    verifie(c.doublons10pc == (c.sansVitesseRadialeLu ? 12u : 11u), "paires de deux catalogues à moins de 0,02 al (numpy : 12, ou 11 avec l'ancien fichier)");
    {      // nombre exact écrit par pipeline/natif/etoiles_hyg.py, s'il est là ; sinon l'ancien repérage (numpy : 41 149)
        std::ifstream vf(dir + "/etoiles_sans_vr.txt");
        unsigned long long attendu = 0;
        if (vf >> attendu) verifie(c.sansVitesseRadialeLu && c.principalSansVitesseRadiale == attendu, "sans vitesse radiale : nombre lu dans etoiles_sans_vr.txt");
        else verifie(!c.sansVitesseRadialeLu && c.principalSansVitesseRadiale == 41149, "sans vitesse radiale : 41 149 repérées (fichier absent, numpy : 41 149)");
    }
    verifie(c.galaxiesGroupeLocal == completude::groupe_local::kNommeesAuRecoupement,
            "galaxies nommées à moins de 1 Mpc : autant qu'au recoupement avec la LVDB (sinon relancer completude_groupe_local.py)");

    const auto r = rapport(c);
    for (const Echelle& e : r) {
        std::printf("\n%s\n  présent : %s\n  précision : %s\n  mesuré ou calculé : %s\n", e.nom, e.complet.c_str(), e.precision.c_str(), e.mesure.c_str());
        for (const Ligne& l : e.lignes) std::printf("    - %s : %s [%s] (%s)\n", l.quoi.c_str(), l.valeur.c_str(), motNature(l.nature), l.source.c_str());
        for (const std::string& m : e.manques) std::printf("    manque : %s\n", m.c_str());
    }
    std::printf("\n");
    verifie(std::fabs(r[1].part - (481.0 - double(c.doublons10pc)) / 540.0) < 1e-12, "voisinage : (481 - paires en double) / 540");
    verifie(std::fabs(r[2].part - 6153611.0 / 1811709771.0) < 1e-15, "Voie lactée : part de Gaia DR3");
    verifie(std::fabs(r[3].part - double(completude::groupe_local::kAppariees) / 113.0) < 1e-12, "Groupe local : galaxies retrouvées par recoupement / 113");
    verifie(completude::groupe_local::kManquantesN > 0 ? r[3].manques[0].find(completude::groupe_local::kManquantes[0].nom) != std::string::npos
                                                       : r[3].manques[0].find("galaxies naines") == std::string::npos,
            "Groupe local : les manquantes sont nommées, et aucune ligne vide quand il n'en manque aucune");
    {      // grandes structures et nuage d'Oort : lignes dites, avec leur nature (modèle = « supposé »)
        Comptes cs = c;
        cs.structures = true;
        cs.lignesFlot = 9297;
        cs.cometesOortModele = 1000000;
        const auto rs = rapport(cs);
        bool oort = false, vides = false, laniakea = false;
        for (const Ligne& l : rs[0].lignes) oort = oort || (l.quoi == "Nuage d'Oort" && l.nature == Nature::Suppose);
        for (const Ligne& l : rs[4].lignes) {
            vides = vides || l.quoi.find("Vides du voisinage") == 0;
            laniakea = laniakea || l.quoi.find("Laniakea") == 0;
        }
        verifie(oort, "nuage d'Oort : dit comme modèle (supposé)");
        verifie(vides && laniakea, "univers lointain : Laniakea et les vides listés quand structures.bin est chargé");
        verifie(std::fabs(rs[0].part - r[0].part) < 1e-15, "le modèle du nuage d'Oort ne compte pas dans la part des objets connus");
        bool absent = false;
        for (const std::string& m : r[4].manques) absent = absent || m.find("structures.bin absent") != std::string::npos;
        verifie(c.structures || absent, "sans structures.bin : dit comme manque");
    }
    return gEchecs ? 1 : 0;
}
