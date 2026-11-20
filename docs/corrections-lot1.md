# Corrections, lot 1a (20 novembre 2026)

Plan : `docs/plan-corrections.md` (PR 119). Ce lot corrige les points B1 à B5, D1, A6 et C4. Captures avant/après en
fenêtre cachée dans `docs/captures-lot1/` (avant : `appli-pc` au commit 2bd66cd ; après : cette branche).

| Point | Avant | Après | Preuve |
|---|---|---|---|
| A6 astéroïdes | 1,58 million de points au même éclat : une neige autour de la Terre | chacun à sa vraie lumière (magnitude H du JPL, distances au Soleil et à la caméra, même pose que les étoiles) : seuls les gros proches se voient, Vesta la première | `terre.jpg`, `ceinture.jpg`, `vesta.jpg` |
| C4 fondu à 300 ans | coupure nette (éclat moyen 50 → 5) | fondu de 250 à 350 ans | éclat moyen 5,4 / 5,3 / 5,4 à +300, +320, +330 ans |
| B2 arrivée sur une étoile | recherche « Sirius » depuis la Terre : 28 000 km du centre (dans l'étoile) | au moins 50 UA | `sirius_arrivee.jpg` |
| B3 arrivée sur une structure | 0,3 million d'al : rien à voir | 1,5 fois sa taille, lue dans sa description (Laniakea : 1,1 milliard d'al) | `laniakea.jpg` ; `essai_interface` (4 contrôles) |
| B4 astre perdu | bascule sur le Soleil sans le dire, à la distance de l'ancien astre | distance reprise pour le Soleil, et la ligne du bas le dit | `astre_perdu.jpg` |
| B1 clic dans le vide | volait vers une galaxie invisible (55 000 de Cosmicflows-4) | une galaxie dont le nom est caché ne se clique pas | lecture du code ; pas de souris en fenêtre cachée |
| B5 « Aller à » | des astres sans position à cette date, qui ne faisaient rien | grisés, « pas à cette date » | lecture du code |
| D1 libellé | « (mesuré) » à +1 Ga | « Distance au Soleil à cette date … (calculé) » | `libelle.jpg` |

Contrôles : `natif/controle.sh` sur les données installées : tout passe sauf `completude` (comptage Gaia 98 278 350
contre 98 278 356 attendues), qui échoue de la même façon avant ce lot : lié aux données installées, pas à ce code.
