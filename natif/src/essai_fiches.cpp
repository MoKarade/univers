// Contrôle des fiches complètes des astres (fiches.h) : lecture des deux formats, astre réparti sur plusieurs fichiers,
// écriture des nombres en français. Aucune carte graphique.
#include <cstdio>
#include <filesystem>
#include <chrono>
#include <fstream>

#include "fiches.h"

namespace {
int failures = 0;
void expect(bool ok, const char* what) {
    std::printf("%s  %s\n", ok ? "ok   " : "ECHEC", what);
    if (!ok) ++failures;
}
}  // namespace

int main() {
    using namespace fiches;
    // Nombres : chiffres de la source gardés, virgule, milliers, puissances de dix, signes.
    expect(nombreFr("6371.0084") == "6\xC2\xA0" "371,0084", "6371.0084");
    expect(nombreFr("2007") == "2007", "année sans espace");
    expect(nombreFr("12345") == "12\xC2\xA0" "345", "milliers");
    expect(nombreFr("1.989e30") == "1,989 \xC3\x97 10^30", "puissance de dix");
    expect(nombreFr("-2.5e-05") == "\xE2\x88\x92" "2,5 \xC3\x97 10^\xE2\x88\x92" "5", "négatif, exposant négatif");
    expect(nombreFr(".5") == "0,5", ".5");
    expect(nombreFr("≈" "0.5") == "≈" "0,5", "valeur approchée");
    expect(nombreFr("G2V") == "G2V", "texte gardé");
    expect(nombreFr("1.2.3") == "1,2,3", "suite de nombres : virgules");
    expect(nombreFr("1829.4 Ã 1819.4") == "1829,4 Ã 1819,4", "dimensions");
    expect(nombreFr("2005MNRAS.356") == "2005MNRAS.356", "référence gardée");
    expect(incertitudeFr("0.05") == " \xC2\xB1 0,05", "incertitude symétrique");
    expect(incertitudeFr("+0.1/-0.2") == " +0,1 / \xE2\x88\x92" "0,2", "incertitude dissymétrique");
    expect(incertitudeFr("+0.1/-0.1") == " \xC2\xB1 0,1", "dissymétrique égale");
    Ligne l{"Physique", "Rayon", "<3.2", "", "km", "mesuré", "JPL"};
    expect(valeurFr(l) == "moins de 3,2 km", "limite supérieure");
    expect(statutFr(l) == "mesuré \xE2\x80\x94 JPL", "statut et source");

    // Fichiers : un au format long, un au format tableau ; « Terre » est dans les deux.
    const std::filesystem::path dir = std::filesystem::temp_directory_path() / "univers_essai_fiches";
    std::filesystem::remove_all(dir);
    std::filesystem::create_directories(dir / "fiches");
    {
        std::ofstream a(dir / "fiches" / "a.tsv", std::ios::binary);
        a << "\xEF\xBB\xBF# essai\r\n"
             "Terre\tPhysique\tRayon moyen\t6371.0084\t0.0001\tkm\tmesuré\tJPL SSD\r\n"
             "Terre\tPhysique\tMasse\t5.9722e24\t0.0006e24\tkg\tmesuré\tJPL SSD\r\n"
             "Terre\tPhysique\tCase vide\t\t\t\t\t\r\n"
             "Mars\tOrbite\tExcentricité\t0.0934\t\t\tmesuré\tJPL SSD\n";
        std::ofstream b(dir / "fiches" / "b.tsv", std::ios::binary);
        b << "# tableau\n@\tOrbite\tDemi-grand axe\tUA\tmesuré\tSBDB\n@\tPhysique\tAlbédo\t\tmesuré\tSBDB\n"
             "Ceres (1)\t2.77\t1e-9\t0.09\t0.003\n"
             "Terre\t1.00000261\t\t\t\n";
    }
    Index idx;
    idx.demarrer(dir.string());
    while (!idx.pret()) std::this_thread::sleep_for(std::chrono::milliseconds(5));
    expect(idx.nombreAstres() == 4, "4 entrées (Terre ×2, Mars, Ceres)");
    const auto terre = idx.lire("Terre");
    expect(terre.size() == 3, "Terre : 2 lignes longues (case vide ignorée) + 1 du tableau");
    expect(terre.size() == 3 && terre[0].libelle == "Rayon moyen" && terre[0].incertitude == "0.0001" && terre[0].unite == "km", "Terre : rayon, incertitude, unité");
    expect(terre.size() == 3 && terre[2].libelle == "Demi-grand axe" && terre[2].source == "SBDB", "Terre : ligne du tableau");
    const auto ceres = idx.lire("Ceres (1)");
    expect(ceres.size() == 2 && ceres[1].valeur == "0.09" && ceres[1].incertitude == "0.003", "Ceres : deux colonnes du tableau");
    expect(idx.lire("Mars").size() == 1, "Mars");
    expect(idx.lire("Vénus").empty(), "astre sans fiche : rien");
    std::filesystem::remove_all(dir);

    Index vide;
    vide.demarrer((std::filesystem::temp_directory_path() / "univers_pas_de_dossier").string());
    while (!vide.pret()) std::this_thread::sleep_for(std::chrono::milliseconds(5));
    expect(vide.nombreAstres() == 0 && vide.lire("Terre").empty(), "pas de dossier fiches : rien, sans erreur");

    std::printf("%s\n", failures ? "DES CONTROLES ECHOUENT" : "tout est bon");
    return failures ? 1 : 0;
}
