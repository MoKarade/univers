# Corrections, lot 4 (20 novembre 2026)

| Point | Avant | Après | Preuve |
|---|---|---|---|
| C1 galaxies lointaines à toute date | au-delà de ±3 Ma, plus nommées ni cliquables | place d'aujourd'hui agrandie par l'expansion (même facteur que leur dessin), au-delà de 10 Mal | `captures-lot4/C1_1ga_1e8.jpg` (+1 Ga, 100 Mal) |
| C7 comètes d'Oort | saut de toutes les comètes à chaque milliard d'années (date réduite modulo 10⁹ ans) | date passée en deux morceaux (millions entiers, puis le reste) : aucun modulo sur la date | lecture du code ; `essai_structures` passe |
| E2 lune devant sa planète | cachée par le disque (les sphères étaient dessinées après tous les points) | les lunes et planètes plus proches que la sphère la plus proche sont dessinées après elle | capture de contrôle Saturne et Jupiter : rien de changé là où rien n'est devant |
| E3 étoiles de près | un point de 14 px même à 1 000 km | disque de son rayon calculé (éclat V, couleur B-V, correction bolométrique de Flower 1996 / Torres 2010, Stefan-Boltzmann), sa couleur, sans carte de surface (aucune n'est mesurée) ; la fiche donne le rayon « calculé, approché » | `E3_sirius_3e-7.jpg`, `E3_betel_2e-4.jpg` ; `essai_interface` : Soleil 1,00 R☉, Sirius A 1,70 (publié 1,71), Véga 2,51 (2,36 à 2,82), Arcturus 27,3 (25,4) |

Limite : la couleur B-V donne mal la température des supergéantes rouges ; Bételgeuse sort à environ 300 R☉ alors que les
mesures donnent 640 à 760 R☉. La fiche dit « approché ».
