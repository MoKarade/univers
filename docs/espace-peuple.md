# Peupler l'espace : galaxies visibles aux grandes échelles et fond diffus (20/11/2026)

Demande de Marc : « Laniakea, quasi aucune galaxie, c'est vide » ; « je vois des boules » ; « le superamas c'est une seule
galaxie » ; « je veux voir le CMB ».

## Ce qui a été mesuré avant
- Les données étaient déjà là [Certain] : `galaxies.bin` = 18 343 142 galaxies et quasars (2MRS, 6dF, 2dF, SDSS, DESI,
  quasars SDSS ; z mesuré). Compté : 60 614 galaxies à z < 0,02 (Laniakea), 141 993 à z < 0,03, 369 057 à z < 0,05.
  Aucun nouveau catalogue n'était nécessaire : 2MRS (tout le ciel) et 6dF (ciel austral, Shapley) y sont déjà.
- Le problème était l'éclat [Certain, captures] : chaque galaxie a son éclat réel en 1/d² sous la pose des étoiles. Vue de
  100 millions d'années-lumière, une galaxie comme la Voie lactée est de magnitude ~11 : un point presque noir.
- Les « boules » (sphères approchées des vides et superstructures) étaient déjà cachées par défaut (PR 125).
- Le fond diffus (carte Planck SMICA, Nside 256) était déjà posé sur sa sphère, mais n'avait pas de nom propre : on ne
  pouvait ni le chercher ni le visiter.

## Ce qui change
1. `natif/src/galaxies_pose.h` : pose propre aux galaxies (« longue pose »), ×(d/10 Mal)², plafonnée à ×150, où d est la
   distance de vue. Les éclats relatifs restent les vrais ; seule la pose change, et elle est écrite à l'écran
   (« Galaxies en longue pose ×N », `interface_bas.h`). Quand la pose de l'écran baisse (image saturée), les galaxies
   baissent avec elle.
2. `natif/shaders/galaxies.vert` : la longue pose est pleine jusqu'à 1,5 fois la distance de vue et s'efface jusqu'à 4 fois.
   Sans cela, les millions de galaxies du SDSS loin derrière Laniakea faisaient un brouillard orange (capture). La taille
   des points est calculée SANS la longue pose : mêmes points qu'avant, donc même coût pour la carte.
3. Les galaxies de forme mesurée (`galaxies_formes.h`, 532 427 galaxies proches) reçoivent la même pose.
4. « Fond diffus cosmologique » : nom à part (`pipeline/natif/superstructures_bin.py` → `superstructures_noms.tsv`),
   fiche (`interface_savoir.h`), rayon 45,3 milliards d'al (z = 1 090, calculé Planck 2018), dernier arrêt de la visite
   « Les galaxies ». Le superamas de Shapley y est aussi ajouté.

## Réglage (captures en fenêtre cachée, 1600×900)
Gains essayés à la main : 30, 100, 300, 1 000 (Laniakea, 1e9 al) ; 300, 3 000, 30 000 (1e10 et 1e11 al). ×100-150 montre
les filaments sans saturer ; ×300 et plus sature en blanc. Planche avant/après : `captures/espace-peuple-avant-apres.jpg`.
Essai rejeté : pose ×(d/3 Mal)² sans plafond, avec division par la pose de l'écran → boucle (pose de l'écran ×0,001,
galaxies ×134 000).

## Vitesse (images par seconde, fenêtre cachée, même série avant/après)
| vue | avant | après |
|---|---|---|
| Soleil 3e7 al | 18,0 | 18,2 |
| Soleil 1e8 al | 18,0 | 18,7 |
| Soleil 3e8 al | 17,3 | 18,1 |
| Soleil 1e9 al | 17,4 | 17,9 |
| Soleil 1e10 al | 17,9 | 18,3 |
| Soleil 1e11 al | 12,9 | 18,4 |
| Laniakea | 11,7 | 17,6 |
Mesures bruitées [Probable] : d'autres essais utilisaient la carte en même temps. Conclusion : pas de coût mesurable. Un
premier essai qui grossissait les points avec la pose coûtait ~20 % (14,6 au lieu de 18,0 à 1e8 al) : écarté.

## Limites
- La longue pose n'est pas la vue de l'œil : elle est dite à l'écran.
- Les galaxies sont placées par leur décalage vers le rouge : les amas s'allongent vers nous (« doigts de Dieu ») [Certain,
  effet connu des relevés en z].
- Le fond diffus ne se voit que de loin (au-delà de ~2 milliards d'al de vue), comme avant : de près il couvrirait les galaxies.
