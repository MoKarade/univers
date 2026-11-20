// Généré par pipeline/natif/completude_groupe_local.py : ne pas éditer à la main.
// Local Volume Database v1.1.2 (Pace 2024), relevé le 2026-11-20 : 113 galaxies confirmées à moins de 1 Mpc,
// 113 retrouvées parmi les 114 galaxies nommées de l'appli (directions à moins de 2°).
#pragma once
namespace completude::groupe_local {
constexpr int kReference = 113;
constexpr int kAppariees = 113;
constexpr int kNommeesAuRecoupement = 114;      // galaxies de l'appli à moins de 1 Mpc lors du recoupement
struct Manquante { const char* nom; double distanceMpc; };
constexpr Manquante kManquantes[] = {};
constexpr int kManquantesN = 0;
constexpr const char* kHorsLvdb[] = {"Canis Major"};      // dans l'appli, pas dans la LVDB à moins de 1 Mpc
constexpr int kHorsLvdbN = 1;
}
