# Corrections du zoom (20 novembre 2026)

Retour de Marc : « parfois les vues changent quand je zoome, dézoome ou scrolle, l'éclairage aussi ».

## L'outil : `natif/balayage.py`

Un seul lancement de l'appli en fenêtre cachée (`UNIVERS_BALAYAGE=<d0>:<d1>:<n>:<dossier>`, `fenetre.cpp`) : 131 vues de
0,01 al à 10¹¹ al autour du Soleil (pas de 10^0,1, environ deux crans de molette), en 2 minutes au lieu de 131 lancements.
Pour chaque pas, le rapport d'éclat moyen de l'image ; un saut est un rapport qui s'écarte de plus d'un facteur 1,4 de
celui de ses voisins (une galaxie qui s'éloigne pâlit régulièrement : ce n'est pas un saut).

## Ce qui a été trouvé et corrigé

| Endroit | Avant (mesuré) | Cause | Correction |
|---|---|---|---|
| 30 → 300 al | éclat ×13 sur une décade | renfort des étoiles en (d/30)², ×100 dès 300 al (`Sim::brightnessBoost`) | renfort en d/30, ×100 atteint à 3 000 al : deux fois moins vite |
| 100 al | −7 % d'un coup | ciel seul de Gaia coupé net à 100 al (`gaia.h`) | fondu de 100 à 200 al |
| ±3 Ma | 37 % → 0 d'une image à l'autre (code) | même couche, coupure en temps | fondu de 1 à 3 Ma |
| ±3 Ma, meilleur rendu | bras dessinés coupés net (code) | `armLayerAgrees` booléen | fondu de 1 à 3 Ma |
| 1,6 Mal | une trentaine de noms de naines d'un coup (×1,7 d'éclat moyen) | toutes les naines nommées dès 1,5 Mal | naines nommées au survol (mode détaillé : toutes) |
| 10 → 13 Mal | ×2,1 d'un cran | pose relevée d'un coup dès 10 Mal | plafond de pose qui monte comme l'échelle (×1,26 par cran au plus) |
| galaxies de forme | galaxie absente quand le budget de points est plein (code) | sa lumière « point » retirée sans particules | le point garde sa lumière si la galaxie n'est pas en particules |
| bords de l'écran | disque de planète coupé d'un bord droit (code) | marge fixe de 1,6 (perspective jusqu'à 2,06) | marge en 1 + tan²θ |
| Saturne | « Rhéa » écrit sur le disque | nom d'une lune derrière sa planète | caché |

Bilan du balayage autour du Soleil : 14 sauts au premier passage (critère simple), 2 restants au critère des voisins :
à 1 600 al la pose baisse d'un coup quand les étoiles proches saturent (dans l'appli, en ~0,3 s) ; à 3,2 Mal la caméra
passe près de la galaxie du Triangle (vrai, pas un défaut). Captures : `docs/captures-zoom/`.
