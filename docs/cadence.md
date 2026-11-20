# Cadence de l'appli PC (20 novembre 2026)

Demande de Marc : « 60 images par seconde constantes, faire les calculs en amont pour libérer l'affichage ».

## Comment c'est mesuré

- `src/chrono.h` : chronomètre par image, allumé seulement par `UNIVERS_CHRONO=<fichier.csv>`. Côté processeur, temps entre
  repères posés dans la boucle (`fenetre.cpp`) ; côté carte, horodatages Vulkan posés entre les étapes du dessin, lus à
  l'image suivante sans attente. Éteint, il ne coûte rien.
- `natif/mesure_cadence.sh` : balayage du zoom de 10 µal à 10 Gal autour du Soleil (16 vues, 40 images chacune), à quatre
  dates (aujourd'hui, +1 Ma, +100 Ma, +4 Ga). `natif/resume_cadence.py` fait le tableau ; `--saccades` liste les images
  au-dessus de 25 ms et les étapes qui pèsent dans chacune.
- Zoom continu (une distance par image) : `UNIVERS_BALAYAGE="1e-5:1e10:900:-"` (le « - » n'écrit aucune image).
- Temps qui défile : `--date 500000027 --trajet 27,0 --vitesse 1e8 --horloge-reelle` (100 Ma par seconde, 5 s).
- Fenêtre cachée 1600 × 900 [Certain]. L'appli n'est pas déclarée « consciente de l'échelle d'affichage » : sur l'écran 4K de
  Marc (échelle 225 %), Windows lui donne une fenêtre agrandie d'environ 1711 × 941 points, agrandie ensuite à l'écran. La
  taille mesurée est donc proche de la vraie [Probable].
- Carte graphique seule (grand calcul en pause) pour les mesures de carte : avec lui, une étape de 1 ms en pèse 350.

## Ce qui ralentissait (mesuré) et ce qui a été fait

| Goulot mesuré | Avant | Correction | Après |
|---|---|---|---|
| Choix des étoiles Gaia et Gaia B (processeur, un seul cœur), vu de loin | jusqu'à 30 ms | tranches de feuilles sur 16 cœurs, remises dans l'ordre (`parallele.h`, `gaia.h`) ; fait avant d'attendre la carte | ~2 ms, en temps masqué |
| Étoiles visibles du modèle, vues de près, dans le futur (carte) | 30 à 47 ms | partie propre à chaque étoile (orbite, 16 lectures de poussière, vieillissement) calculée une fois par image et par étoile dessinée (`gaia_traceur.comp`), au lieu de 16 fois (une par étoile du sous-nuage) | 4 à 7 ms |
| Orbite multipliée par zéro (près d'aujourd'hui, film à la date exacte) | 2 accélérations par étoile | sautée quand son poids vaut exactement zéro | identique |
| Calcul des états du film refait à chaque image, temps arrêté | 2 à 4 ms | sauté quand date, Soleil et film n'ont pas changé | 0 |
| Naines : points retirés au hasard à chaque image quand le temps défile | 15 ms | tirés une fois, puis seulement replacés | ~1 ms |
| Orbites des étoiles nommées (un seul cœur), refaites deux fois par image près d'une limite de pas (aujourd'hui en est à 27 ans) | 3 à 16 ms | 16 cœurs et deux pas gardés | < 0,5 ms |
| Formes des galaxies (processeur) | 1,4 ms | 16 cœurs, mêmes plafonds dans le même ordre | ~0,7 ms |
| Affichage : attendait la fin du dessin, puis tout le travail du processeur venait après | — | l'image est affichée après le travail suivant du processeur qui ne touche pas à la carte | 3 à 5 ms gagnées |

## Images par seconde (carte seule, médiane)

Avant (`appli-pc` du 20/11) puis après les corrections mesurées sur carte seule (avant le report de l'affichage).

| Date | Pire échelle avant | Pire échelle après | Meilleure après |
|---|---|---|---|
| Aujourd'hui | 20 (10⁵ al) | 42 (10⁴ al) | 84 |
| +1 Ma | 20 (10⁹ al) | 37 (10⁴ al) | 70 |
| +100 Ma | 23 (10⁴ al) | 91 | 123 |
| +4 Ga | 17 (près) | 36 (10⁵ al) | 114 |
| Temps qui défile à 100 Ma/s | 9 à 12 | 43 (carte partagée) | — |

## Image inchangée

Captures comparées à l'appli d'avant, mêmes vues (3 dates × 3 distances) :
- tri sur plusieurs cœurs, calculs sautés : identiques au pixel près aux dates futures ;
- précalcul des étoiles du modèle : même lumière moyenne (à 0,001 près sur 255) ; au plus 29 pixels sur 1,44 million changent
  de plus de 1 %, un point qui tombe dans le pixel voisin (arrondi d'un calcul fait ailleurs) ;
- aujourd'hui : seuls l'heure affichée et un trait de l'interface qui suit l'horloge réelle changent.

## Ce qui reste

- Vers 10 000 al d'aujourd'hui, la carte dessine 140 millions de points Gaia (79 M + 62 M) : 11 ms, autant à 800 × 450 qu'à
  1600 × 900, donc limité par le nombre de points, pas par les pixels. Piste : dessiner ces points par un calcul (somme exacte
  par pixel) au lieu du tracé de points de la carte.
- Vers 10⁵ al dans 4 Ga : 6 millions d'étoiles du modèle sur peu de pixels, l'addition par pixel sature (16 ms).
- Le processeur garde ~5 ms après l'attente de la carte (interface, préparation des couches) : seules deux images en vol
  le masqueraient entièrement.
