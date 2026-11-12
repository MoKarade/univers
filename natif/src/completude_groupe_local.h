// Généré par pipeline/natif/completude_groupe_local.py : ne pas éditer à la main.
// Local Volume Database v1.1.2 (Pace 2024), relevé le 2026-11-12 : 113 galaxies confirmées à moins de 1 Mpc,
// 69 retrouvées parmi les 70 galaxies nommées de l'appli (directions à moins de 2°).
#pragma once
namespace completude::groupe_local {
constexpr int kReference = 113;
constexpr int kAppariees = 69;
constexpr int kNommeesAuRecoupement = 70;      // galaxies de l'appli à moins de 1 Mpc lors du recoupement
struct Manquante { const char* nom; double distanceMpc; };
constexpr Manquante kManquantes[] = {{"Draco II", 0.022}, {"Hydrus I", 0.028}, {"Carina III", 0.028}, {"Triangulum II", 0.028}, {"Reticulum II", 0.032}, {"Carina II", 0.037}, {"Pictor II", 0.045}, {"Tucana IV", 0.047}, {"Tucana V", 0.055}, {"Grus II", 0.055}, {"Tucana II", 0.056}, {"Eridanus IV", 0.070}, {"DELVE 2", 0.071}, {"Horologium I", 0.079}, {"Leo Minor I", 0.082}, {"Phoenix II", 0.083}, {"Aquarius III", 0.086}, {"Pegasus IV", 0.090}, {"Reticulum III", 0.092}, {"Bootes V", 0.102}, {"Carina IV", 0.105}, {"Aquarius II", 0.108}, {"Leo VI", 0.111}, {"Crater II", 0.117}, {"Centaurus I", 0.118}, {"Antlia II", 0.124}, {"Grus I", 0.126}, {"Hydra II", 0.151}, {"Columba I", 0.183}, {"Pegasus III", 0.215}, {"Eridanus II", 0.370}, {"Leo K", 0.435}, {"Leo M", 0.459}, {"Cassiopeia II", 0.560}, {"Perseus I", 0.705}, {"Lacerta I", 0.745}, {"Pegasus VII", 0.752}, {"Pegasus V", 0.755}, {"Andromeda XXXVI", 0.776}, {"Cassiopeia III", 0.802}, {"Pegasus W", 0.916}, {"Andromeda XXXV", 0.925}, {"Pisces VII", 0.929}, {"Aquarius", 0.986}};
constexpr int kManquantesN = 44;
constexpr const char* kHorsLvdb[] = {"Canis Major"};      // dans l'appli, pas dans la LVDB à moins de 1 Mpc
constexpr int kHorsLvdbN = 1;
}
