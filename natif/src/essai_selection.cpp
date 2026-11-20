// Contrôle de la sélection des galaxies et de la place de M77, sur les vraies données installées (Marc, 20/11/2026 :
// « M77 se balade, pas de physique » ; « des objets qu'on ne peut pas sélectionner »). Aucune carte graphique.
//
// Ce qui est vérifié :
// 1. M77 : un seul nom (le doublon de galaxies_cf4.tsv est fondu), distance MESURÉE de son groupe (Cosmicflows-4,
//    table 3 : DMzp = 30,645, soit 13,5 Mpc = 44,0 millions d'al), forme cliquable sur tout son disque.
// 2. Mouvement de M77 : nom et forme suivent le même facteur d'échelle, sans saut à ±3 Ma.
// 3. Inventaire : chaque galaxie nommée et placée, vue de face à 8 fois son rayon dessiné (Soleil suivi), doit se choisir
//    d'un clic sur son centre ET à mi-rayon. Les échecs sont comptés par famille et les premiers sont nommés.
// Usage : essai_selection <dossier des données de l'appli, par ex. C:\dev\Univers-PC>
#include <cstdio>
#include <map>
#include <set>

#include "interface_base.h"
#include "galaxies_formes.h"

namespace {

int gEchecs = 0;

void verifie(bool ok, const std::string& quoi) {
    std::printf("%s  %s\n", ok ? "PASSE" : "ÉCHEC", quoi.c_str());
    if (!ok) ++gEchecs;
}

// Famille d'une galaxie, d'après son fichier d'origine (texte de la fiche).
std::string famille(const Body& b) {
    if (b.structure) return "structures";
    if (b.cluster) return "amas";
    if (b.natureText.find("SGA-2020") != std::string::npos) return "formes mesurées (SGA-2020)";
    if (b.priority >= 9) return "Cosmicflows-4 (nom seul)";
    return "Groupe local et voisines";
}

}  // namespace

int main(int argc, char** argv) {
    SetConsoleOutputCP(CP_UTF8);
    if (argc < 2) {
        std::printf("Usage : essai_selection <dossier des données>\nECHEC\n");
        return 1;
    }
    const std::string dir = argv[1];
    Sim sim;
    const Stars stars = openStars((dir + "/etoiles.bin").c_str());      // chargement identique à fenetre.cpp
    sim.stars = &stars;
    eph::Set spk;
    std::string err;
    verifie(spk.add(dir + "/de440.bsp", err), "de440.bsp lu");
    sim.spk = &spk;
    sim.loadBodies(dir + "/etoiles_noms.tsv", dir + "/galaxies_noms.tsv", dir + "/planetes.tsv", dir + "/lunes.tsv");
    GalaxyShapes shapes;
    verifie(shapes.loadRecords(dir + "/galaxies_formes.bin"), "galaxies_formes.bin lu (sans carte graphique)");
    const int fixes = shapes.fixNearbyDistances(sim.bodies);
    // Fiches de forme qui ont reçu une distance mesurée : leur forme doit l'avoir reçue aussi (sinon snapNames les ramène à z)
    std::vector<std::pair<size_t, double>> mesurees;
    for (size_t i = 0; i < sim.bodies.size(); ++i) {
        const Body& b = sim.bodies[i];
        if (b.natureText.find("SGA-2020") != std::string::npos && b.natureText.find("Cosmicflows-4") != std::string::npos && !b.merged)
            mesurees.push_back({i, std::sqrt(dot(b.fixedPos, b.fixedPos))});
    }
    const cosmo::Params p;
    const int poses = shapes.snapNamesWith(sim.bodies, [&](float z) { return z > 0 ? cosmo::distanceTable(p, z, 64).back() * cosmo::kMpcInLy : 0.0; });
    std::printf("formes : distance de z remplacée par une mesure : %d ; noms posés au centre de leur forme : %d\n", fixes, poses);
    sim.refreshGalaxies();
    int ecarts = 0;
    for (const auto& [i, d0] : mesurees) {
        const double d1 = std::sqrt(dot(sim.bodies[i].fixedPos, sim.bodies[i].fixedPos));
        if (std::fabs(d1 / d0 - 1.0) > 1e-4) {
            if (++ecarts <= 5) std::printf("      forme restée à z : %s (%.4g al au lieu de %.4g)\n", sim.bodies[i].name.c_str(), d1, d0);
        }
    }
    verifie(ecarts == 0, "les " + std::to_string(mesurees.size()) + " formes à distance mesurée sont dessinées à cette distance (nom et forme ensemble)");

    // ---- 1. M77
    std::vector<int> m77;
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
        if (sim.bodies[static_cast<size_t>(i)].name == "M77 (NGC 1068)" && sim.visible(i)) m77.push_back(i);
    verifie(m77.size() == 1, "M77 : un seul nom visible (trouvés : " + std::to_string(m77.size()) + ")");
    if (m77.empty()) {
        std::printf("ECHEC (%d)\n", gEchecs + 1);
        return 1;
    }
    const int iM = m77[0];
    const Body& bM = sim.bodies[static_cast<size_t>(iM)];
    const double dM = std::sqrt(dot(bM.fixedPos, bM.fixedPos)), attendu = std::pow(10.0, (30.645 - 25.0) / 5.0) * 3.2615637771674333e6;
    std::printf("      M77 : %.4g al (attendu %.4g al) ; fiche : %s\n", dM, attendu, bM.natureText.c_str());
    verifie(std::fabs(dM / attendu - 1.0) < 0.01, "M77 : distance mesurée de son groupe, 13,5 Mpc (Cosmicflows-4 table 3), à 1 % près");
    verifie(bM.natureText.find("Cosmicflows-4 table 3") != std::string::npos && bM.natureText.find("SGA-2020") != std::string::npos,
            "M77 : la fiche cite la mesure (Cosmicflows-4 table 3) et la forme (SGA-2020)");
    verifie(bM.drawnRadiusLy > 1.0e4 && bM.drawnRadiusLy < 1.0e5, "M77 : rayon de la forme dessinée entre 10 000 et 100 000 al (" + std::to_string(static_cast<long>(bM.drawnRadiusLy)) + ")");

    // ---- 2. mouvement : même facteur pour le nom et le dessin, aucune marche à ±3 Ma
    sim.galaxyScale = 1.0002;
    sim.years = kStartYears + 2.9e6;
    sim.refreshGalaxies();
    const Vec3 avant = sim.position(iM);
    sim.years = kStartYears + 3.1e6;
    sim.refreshGalaxies();
    const Vec3 apres = sim.position(iM);
    const Vec3 attenduP{bM.fixedPos.x * 1.0002, bM.fixedPos.y * 1.0002, bM.fixedPos.z * 1.0002};
    verifie(distBetween(avant, apres) < 1.0, "M77 : pas de saut en passant 3 Ma (écart " + std::to_string(distBetween(avant, apres)) + " al)");
    verifie(distBetween(avant, attenduP) < 1.0, "M77 : nom = place mesurée × facteur d'échelle du dessin, avant comme après 3 Ma");
    sim.galaxyScale = 0;
    sim.years = kStartYears;
    sim.refreshGalaxies();

    // ---- 3. inventaire des galaxies qu'on ne peut pas choisir
    UiState ui;
    const float w = 1920, h = 1080;
    sim.focus = 0;
    std::map<std::string, std::pair<int, int>> parFamille;      // famille -> (essais, échecs)
    std::map<std::string, std::vector<std::string>> exemples;
    std::map<std::string, int> noms;
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i) {
        const Body& b = sim.bodies[static_cast<size_t>(i)];
        if (b.kind != Kind::Galaxy || !sim.visible(i) || b.name == "Centre de la Voie lactée") continue;
        ++noms[b.name];
        const Vec3 at = sim.position(i);
        const double r = sim.drawnRadiusLy(i);
        // vue : la galaxie de face, à 8 fois son rayon dessiné (forme), ou à sa distance d'arrivée (nom seul)
        const double dv = r > 0 ? 8.0 * r : sim.arriveDist(i, 1e300);
        const double na = std::sqrt(dot(at, at));
        const Vec3 u{at.x / na, at.y / na, at.z / na};
        // de côté (perpendiculaire à la ligne de visée depuis le Soleil) : le Soleil n'est jamais pile derrière ou devant
        Vec3 v{-u.y, u.x, 0.0};
        if (dot(v, v) < 1e-6) v = {1.0, 0.0, 0.0};
        const double nv = std::sqrt(dot(v, v));
        const Vec3 eye{at.x + v.x / nv * dv, at.y + v.y / nv * dv, at.z + v.z / nv * dv};
        const Camera cam = lookAt(eye, at, sim.fovDeg, w / h);
        sim.dist = std::sqrt(dot(eye, eye));      // le Soleil est suivi : l'échelle est la distance de la caméra au Soleil
        const ImVec2 centre{w * 0.5f, h * 0.5f};
        const int pris = pickBody(sim, ui, cam, w, h, centre);
        const bool okCentre = pris == i;
        const double disc = discRadiusPx(sim, cam, i, h);
        const int prisBord = disc < 16.0 ? i : pickBody(sim, ui, cam, w, h, {static_cast<float>(w * 0.5 + 0.5 * disc), h * 0.5f});
        const bool okBord = prisBord == i;
        auto& f = parFamille[famille(b)];
        ++f.first;
        if (!(okCentre && okBord)) {
            ++f.second;
            auto& ex = exemples[famille(b)];
            if (ex.size() < 5) ex.push_back(b.name + (okCentre ? " (mi-rayon : " + (prisBord < 0 ? std::string("rien") : sim.bodies[static_cast<size_t>(prisBord)].name) + ")" : " (centre : " + (pris < 0 ? std::string("rien") : sim.bodies[static_cast<size_t>(pris)].name) + ")"));
        }
    }
    int total = 0, rates = 0;
    for (const auto& [fam, c] : parFamille) {
        std::printf("      %-30s %6d essayées, %5d impossibles à choisir", fam.c_str(), c.first, c.second);
        for (const std::string& e : exemples[fam]) std::printf(" ; %s", e.c_str());
        std::printf("\n");
        total += c.first;
        rates += c.second;
    }
    // Les seules exceptions admises : une galaxie posée devant une autre (même direction à quelques pixels), où le clic
    // choisit la plus proche du point, comme prévu. Au plus 1 % du total.
    verifie(rates <= total / 100, "galaxies choisies d'un clic (centre et mi-rayon) : " + std::to_string(total - rates) + " sur " + std::to_string(total));
    int doubles = 0;
    for (const auto& [n, k] : noms)
        if (k > 1) {
            ++doubles;
            std::printf("        double : %s (%d)\n", n.c_str(), k);
        }
    std::printf("      noms de galaxies portés par plusieurs astres visibles : %d\n", doubles);
    verifie(doubles <= 3, "doublons de noms de galaxies : 3 au plus (avant : 25)");
    std::printf(gEchecs ? "ECHEC (%d)\n" : "PASSE\n", gEchecs);
    return gEchecs ? 1 : 0;
}
