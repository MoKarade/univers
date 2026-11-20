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

# Lot 1b (20 novembre 2026, après-midi)

Remarques de relecture du lot 1a corrigées, et nouveaux retours de Marc (« les vues changent quand je zoome »,
« Laniakea quasi aucune galaxie », « des boules », « je veux voir le CMB », « le superamas c'est une seule galaxie »).
Captures dans `docs/captures-lot1b/`.

| Point | Avant | Après | Preuve |
|---|---|---|---|
| A2 saturation | Andromède vue de 20 000 al : 47 % de l'image blanche | pose automatique qui baisse quand plus de 0,5 % de l'écran sature (`pose_auto.h`, `shaders/pose.comp`), dite à l'écran : 0,6 % ; à 100 000 al : 31 % → 8 % ; vues d'étoiles inchangées | `andromede_2e4.jpg`, `andromede_1e5.jpg` |
| A4/A5 galaxies lointaines | galaxies presque invisibles de 10⁷ à 10¹¹ al | au-delà de 10⁷ al regardés, la pose se relève (jusqu'à ×1000) tant que moins de 0,1 % de l'écran est bien visible, comme une longue pose photo, dite à l'écran ; les repères (voiles, flot, Oort, fond diffus) gardent le même éclat | `galaxies_1e8.jpg`, `laniakea_1e9.jpg` |
| « Boules » | sphères des vides SDSS et BOSS, superamas SDSS, superstructures « une bulle par amas » | cachées par défaut ; case du menu « Vides et superamas lointains (formes approchées en sphères) » | `boules.jpg` |
| Fond diffus | sphère unie | carte mesurée par Planck (SMICA 2018, Nside 256 moyennée depuis 2048), fausses couleurs ±300 µK, vue de dedans et de dehors | `fond_diffus.jpg` |
| Amas et superamas | « galaxie », « Galaxie. Sa distance… » | « amas de galaxies » / « superamas » / « concentration de masse », textes sourcés (Vierge, Coma, Fourneau, Persée, Shapley, Grand Attracteur), distance d'arrivée adaptée | `fiche_vierge.jpg` |
| Univers observable | « Distance au Soleil : 1 392 UA » | « Rayon aujourd'hui : 46,2 milliards d'al (calculé, Planck 2018) » | capture `G_univ_fiche` |
| Relecture 1a | taille des superstructures lue sur leur distance ; galaxies nommées non cliquables de près ; message d'astre perdu collant | taille lue après « taille publiée : » (contrôlée : Sloan 1,37 Gal, CfA2 170 Mpc/h, Saraswati 200 Mpc) ; filtre du clic limité à Cosmicflows-4 ; message tant qu'on reste sur l'astre de repli | `essai_interface` (10 contrôles) |

Zoom complet mesuré (41 vues de 10⁻⁹ à 10¹¹ al, vue fixe) : les changements de vue restants sont à 100 et 300 al (éclat
des étoiles multiplié selon la distance à l'astre suivi), vers 10 000 al (bras dessinés qui apparaissent) et vers
10 millions d'al (la Voie lactée s'efface) : lot suivant.

Contrôles : `natif/controle.sh` : tout passe sauf `completude`, identique avant ce lot (données installées).
