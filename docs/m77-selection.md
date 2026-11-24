# M77 et objets impossibles à choisir (20 novembre 2026, soir)

Retours de Marc : « M77 se balade, pas de physique » (deuxième fois) et « des objets que je ne peux pas sélectionner ».
Les traînées sur le Grand Nuage, l'éclairage et les galaxies sont traités dans d'autres fils.

## M77 (NGC 1068)

| | Avant (mesuré sur les fichiers installés) | Après |
|---|---|---|
| Distance | 55,2 millions d'al, tirée du décalage vers le rouge z = 0,0038 | **44,0 millions d'al (13,5 Mpc ± 13 %)**, distance MESURÉE de son groupe |
| Source | aucune mesure : NGC 1068 n'a pas de distance à elle dans Cosmicflows-4 (table 2), c'est une Seyfert vue de face | Cosmicflows-4, table 3 (Tully et al. 2023, ApJ 944, 94 ; VizieR J/ApJ/944/94), groupe de 1PGC 10266 : module DMzp = 30,645 ± 0,286, moyenne des 2 galaxies mesurées du groupe (PGC 10208 et 10496, Tully-Fisher), vitesse propre du groupe −30 km/s |
| Mouvement | la forme suivait l'expansion par pas d'un million d'années, le nom restait fixe puis sautait à ±3 Ma : le nom et la caméra glissaient sur la forme | nom, caméra, forme et points suivent le **même facteur d'échelle** (équations de Friedmann, cosmologie choisie), recalculé tous les 100 000 ans (M77 avance d'environ 300 al par pas) ; plus de saut à ±3 Ma |
| Fiche | « Position : calcul complet de la rencontre avec Andromède » (faux pour M77) | « direction et distance d'aujourd'hui, puis l'expansion de l'univers calculée ici ; vitesse propre non suivie » ; ligne « Mouvement » avec le facteur ; source de la forme (SGA-2020) |

[Certain] La vitesse propre (−30 km/s ± quelques centaines) n'est pas suivie : sur 1 milliard d'années elle déplacerait M77
d'environ 0,1 million d'al, contre 3 millions par l'expansion. [Certain] La compilation de van den Bosch 2016 (déjà
citée pour son trou noir, `trous_noirs.tsv`) donne 15,9 ± 9,4 Mpc : compatible, mais bien moins précise ; Cosmicflows-4 fait
foi ici, comme pour toutes les galaxies de l'appli.

Même correction pour toutes les galaxies dans le même cas : 697 galaxies dominantes de groupe nommées (NGC, IC, Messier)
reçoivent la distance mesurée de leur groupe (`pipeline/natif/galaxies_cf4.py`).

## Inventaire : ce qui se dessine et ce qui se choisit

Inventaire fait en lisant le code de chaque couche dessinée (fenetre.cpp) puis mesuré par `essai_selection` (chaque galaxie
nommée vue de côté à 8 fois son rayon dessiné, clic au centre et à mi-rayon).

| Couche | Avant | Après |
|---|---|---|
| Galaxies de forme mesurée nommées (4 201) | cliquables seulement au point central (16 px), et 4 180 seulement à moins de 3 millions d'al | cliquables sur toute leur forme dessinée, dès que la forme fait 6 px ; 3 sur 4 201 restent prises par une voisine qui les recouvre (NGC 4436 sous NGC 4440 : le clic prend le point le plus proche, voulu) |
| Nom posé sur la mauvaise forme | le nom allait à la forme la plus proche en angle : une petite galaxie de fond posée sur une grande prenait son nom (IC 3546 nommée sur une galaxie à z = 0,17, à 2,4 milliards d'al au lieu de 282 millions) | le nom va à la forme la plus proche en unités de son propre rayon, et dont le z ou la distance mesurée concorde ; les 636 formes à distance mesurée sont dessinées à la distance de leur nom |
| Noms en double (25, dont M77, M106, M49, IC 342) | deux points, deux fiches, deux fois dans la recherche | fondus : 3 restent (homonymes réels du catalogue, pas la même galaxie) |
| Grandes structures (121 : vides, bassins) | 100 impossibles à cliquer (filtre des 55 000 galaxies Cosmicflows-4) | cliquables ; leur repère passe après une galaxie réellement sous la souris |
| Galaxies proches (moins de 10 millions d'al) loin d'aujourd'hui | forme dessinée à sa place d'aujourd'hui, nom caché : impossible à cliquer | forme cachée elle aussi (pas de place calculée à cette date) |
| Galaxies de Cosmicflows-4 (nom seul, 55 834) | cliquables | inchangé (0 échec) |

Reste non cliquable, connu et non traité ici (dit tel quel) :
- étoiles Gaia (192 millions de points) : seules celles aussi dans `etoiles.bin` (6,15 millions) se choisissent ;
- étoiles du catalogue au-delà de ±100 000 ans (dessinées jusqu'à ±3 Ma sur leur orbite exacte) ;
- étoiles dans le système solaire (choix de conception : on y clique les planètes) ;
- nébuleuses (317 : pas de nom dans `nebuleuses.bin`), étoiles du modèle de la Voie lactée, nuage d'Oort, clones : pas de fiche ;
- Andromède, le Triangle et les Nuages : cliquables au centre seulement (pas de rayon dessiné publié chargé).

## Vérifications

- `essai_selection` (nouveau, dans `controle.sh`) : PASSE sur les données avec le nouveau `galaxies_cf4.tsv`.
- `controle.sh` complet : PASSE (18 essais, 28 cassures de continuité, référence 29).
- Pas vérifié à l'écran : la carte graphique est prise par le grand calcul.

## Suite (même soir) : étoiles Gaia et nébuleuses

| Couche | Avant | Après |
|---|---|---|
| Étoiles Gaia (gaia.bin 98 M, gaia_b.bin 94 M) | non cliquables (seules celles aussi dans etoiles.bin) | un clic choisit l'étoile Gaia la plus brillante sous le curseur (12 px), si elle paraît plus brillante que l'étoile du catalogue trouvée ; fiche « Étoile Gaia n° … » : magnitude absolue G, couleur → température, vitesse radiale mesurée ou non, rayon calculé (approché) |
| Nébuleuses (223 planétaires, 94 nuages moléculaires) | dessinées, sans nom ni fiche ni clic | astres nommés (nebuleuses_noms.tsv, qui existait sans être lu), cliquables sur toute leur tache dessinée, fiche avec la source (Chornay et Walton 2021 ; Zucker et al. 2020) |

Coût : rien par image. La recherche Gaia ne tourne qu'au clic et ne lit que les feuilles de l'arbre traversées par la ligne
de visée : mesuré sur 610 clics, 1,2 ms en moyenne, 8,2 ms au pire (`essai_selection`).

Limites dites telles quelles : une étoile Gaia se choisit à 100 000 ans au plus d'aujourd'hui (comme les étoiles du catalogue)
et suit alors une ligne droite ; pas de nom au survol pour elle (seulement au clic). Une nébuleuse au-delà de 30 000 al du
Soleil n'est pas dessinée, donc pas cliquable (PM 1-308, à 34 000 al).
