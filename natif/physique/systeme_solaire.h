// Appli PC « Univers », bibliothèque univers_physique : positions du système solaire HORS de la plage des éphémérides
// DE440 (1550-2650), où l'appli lit directement les fichiers de la NASA (natif/src/ephemeride.h).
//
// 1. De part et d'autre de la plage DE440, sur `ansDirects` années : calcul à N corps (nbody_noyau.h, port de la page,
//    app/src/21_nbody.js) qui PART de l'état DE440 aux bornes (continuité exacte avec les fichiers de la NASA) ;
//    vitesses multipliées par les facteurs de calage du pas de 4 jours (calés sur DE440 de 1650 à 2450,
//    pipeline/gravite/ajuste.js). Points de reprise tous les 20 ans, construits par construire() ; une requête repart
//    du plus proche (au plus 10 ans de calcul, sur la pile, sans état partagé : sûre depuis plusieurs fils).
// 2. Au-delà, jusqu'à ±10 millions d'années d'aujourd'hui : table des orbites (LongTable, fichier
//    orbites_planetes.bin), contrôlée contre La2004 ; positions des 8 planètes et de Pluton seulement.
// 3. Plus loin : false (le système solaire est chaotique ; la position est inconnue).
#pragma once
#include <functional>
#include <span>
#include <string>
#include <vector>

#include "nbody_noyau.h"
#include "phys.h"

namespace phys {

// Plage des éphémérides DE440 (fichier de440.bsp du NAIF) : 1549-12-31 à 2650-01-25 TDB.
constexpr double kDe440Debut = 2287184.5, kDe440Fin = 2688976.5;

// Source des états DE440 : position et vitesse barycentriques (km, km/s, écliptique J2000) du corps NAIF à jd.
using SourceDe440 = std::function<bool(int naif, double jd, Vec3& pos, Vec3& vit)>;

class SystemeSolaire {
public:
    // Prépare les états de départ aux deux bornes de DE440 et construit les points de reprise sur `ansDirects` années de
    // chaque côté (environ 0,2 s par siècle). À appeler une fois, éventuellement depuis un fil à part, avant toute requête.
    bool construire(const SourceDe440& de440, double ansDirects = 20000.0);
    // Charge la table des orbites sur des millions d'années (facultatif). false si le fichier manque ou est illisible.
    bool chargerTable(const std::string& chemin);

    // Plages couvertes : calcul direct avant et après DE440, table au-delà.
    Plage plageAvant() const { return {debutDirect_, kDe440Debut}; }
    Plage plageApres() const { return {kDe440Fin, finDirect_}; }
    Plage plageTable() const;

    // État héliocentrique (km, km/s) du corps à jd. false si jd est dans DE440 (l'appli lit alors la NASA), hors des plages,
    // ou si le corps n'est pas dans le calcul (la table ne donne que les planètes et Pluton).
    bool etat(int naif, double jd, Vec3& pos, Vec3& vit, Statut& statut) const;
    // Positions héliocentriques (km) de tous les corps du calcul, dans l'ordre de corps() ; false si inconnues. Dans la plage
    // de la table, les quatre astéroïdes valent NaN (inconnus).
    bool positions(double jd, std::span<Vec3> out) const;
    // Codes NAIF des corps, dans l'ordre de positions().
    static std::span<const int> corps();
    // Point de reprise k (0 = à la borne) du côté choisi, pour les essais ; nullptr s'il n'existe pas.
    const nb::State* reprise(bool apres, size_t k) const { const auto& c = apres ? apres_ : avant_; return k < c.size() ? &c[k] : nullptr; }

private:
    std::vector<nb::State> avant_, apres_;      // points de reprise, du plus proche de DE440 au plus loin
    double debutDirect_ = 0, finDirect_ = 0;
    nb::LongTable table_;
    static constexpr double kPasReprise = 20 * 365.25;
    bool etatDirect(double jd, nb::State& s) const;
};

}  // namespace phys
