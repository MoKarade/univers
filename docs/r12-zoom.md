# R12 — zoom fluide : mesures

Mesure faite le 12/11/2026 : contrôles dans `app/test/zoom_fluide.py`, et un relevé image par image de 10^26,75 m à 10^-20 m, par pas d’un quart de puissance de dix, vue « Terre et Lune » puis plongée dans la goutte.

**Attention [Certain] :** ce relevé est fait sans carte graphique (rendu logiciel SwiftShader, 640 × 400, niveau de détail 1, celui d’un téléphone récent ; relevé fait avant l’allègement des boules). Les temps par image ne disent rien d’un téléphone : seul le compteur d’images par seconde lu par Marc sur son Android le dira.

Colonne « écart » : écart moyen (sur 255) entre l’image et la précédente, réduite à 160 × 100 en gris. Sous 3, rien ne change à l’écran : ce sont les étendues traversées trois fois plus vite (ZFAST dans `app/src/60_app.js`).

| Échelle (log₁₀ m) | Temps par image (ms, rendu logiciel) | Écart avec l’image précédente | Lieu affiché |
|---|---|---|---|
| 26.75 | 34 |  | Univers observable |
| 26.5 | 34 | 32.62 | Univers observable |
| 26.25 | 34 | 20.84 | Univers observable |
| 26.0 | 33 | 15.28 | Univers observable |
| 25.75 | 32 | 11.27 | Toile cosmique |
| 25.5 | 32 | 9.04 | Toile cosmique |
| 25.25 | 25 | 7.91 | Toile cosmique |
| 25.0 | 27 | 8.7 | Toile cosmique |
| 24.75 | 25 | 10.8 | Toile cosmique |
| 24.5 | 31 | 14.19 | Superamas voisins |
| 24.25 | 28 | 14.64 | Superamas voisins |
| 24.0 | 32 | 10.91 | Superamas voisins |
| 23.75 | 32 | 8.79 | Superamas voisins |
| 23.5 | 47 | 6.86 | Superamas voisins |
| 23.25 | 45 | 5.04 | Superamas voisins |
| 23.0 | 42 | 6.84 | Groupe local |
| 22.75 | 22 | 4.07 | Groupe local |
| 22.5 | 20 | 1.74 | Groupe local |
| 22.25 | 19 | 1.82 | Groupe local |
| 22.0 | 19 | 1.98 | Groupe local |
| 21.75 | 22 | 3.53 | Groupe local |
| 21.5 | 18 | 7.33 | Voie lactée |
| 21.25 | 20 | 6.08 | Voie lactée |
| 21.0 | 20 | 7.03 | Voie lactée |
| 20.75 | 24 | 8.69 | Voie lactée |
| 20.5 | 36 | 9.86 | Voie lactée |
| 20.25 | 124 | 15.02 | Voie lactée |
| 20.0 | 86 | 19.72 | Voie lactée |
| 19.75 | 87 | 18.09 | Bras d’Orion |
| 19.5 | 92 | 13.07 | Bras d’Orion |
| 19.25 | 84 | 12.53 | Bras d’Orion |
| 19.0 | 75 | 12.64 | Bras d’Orion |
| 18.75 | 78 | 13.01 | Bras d’Orion |
| 18.5 | 84 | 15.75 | Étoiles voisines |
| 18.25 | 70 | 15.76 | Étoiles voisines |
| 18.0 | 72 | 15.94 | Étoiles voisines |
| 17.75 | 99 | 15.52 | Étoiles voisines |
| 17.5 | 88 | 15.56 | Étoiles voisines |
| 17.25 | 86 | 14.74 | Étoiles voisines |
| 17.0 | 75 | 16.7 | Étoiles voisines |
| 16.75 | 76 | 7.3 | Étoiles voisines |
| 16.5 | 74 | 6.48 | Nuage d’Oort |
| 16.25 | 75 | 4.07 | Nuage d’Oort |
| 16.0 | 48 | 3.23 | Nuage d’Oort |
| 15.75 | 38 | 2.76 | Nuage d’Oort |
| 15.5 | 37 | 2.16 | Nuage d’Oort |
| 15.25 | 38 | 1.47 | Nuage d’Oort |
| 15.0 | 35 | 1.27 | Nuage d’Oort |
| 14.75 | 43 | 1.28 | Nuage d’Oort |
| 14.5 | 54 | 3.64 | Confins du système solaire |
| 14.25 | 55 | 1.17 | Confins du système solaire |
| 14.0 | 56 | 1.44 | Confins du système solaire |
| 13.75 | 52 | 0.82 | Confins du système solaire |
| 13.5 | 51 | 6.57 | Confins du système solaire |
| 13.25 | 53 | 4.45 | Système solaire |
| 13.0 | 49 | 3.47 | Système solaire |
| 12.75 | 53 | 4.02 | Système solaire |
| 12.5 | 50 | 3.77 | Système solaire |
| 12.25 | 47 | 3.91 | Système solaire |
| 12.0 | 40 | 3.96 | Système solaire |
| 11.75 | 40 | 5.3 | Système solaire interne |
| 11.5 | 37 | 5.19 | Système solaire interne |
| 11.25 | 50 | 5.18 | Système solaire interne |
| 11.0 | 47 | 4.67 | Système solaire interne |
| 10.75 | 46 | 5.04 | Terre et Lune |
| 10.5 | 50 | 2.35 | Terre et Lune |
| 10.25 | 50 | 1.37 | Terre et Lune |
| 10.0 | 44 | 0.82 | Terre et Lune |
| 9.75 | 45 | 0.55 | Terre et Lune |
| 9.5 | 53 | 0.57 | Terre et Lune |
| 9.25 | 38 | 0.38 | Terre et Lune |
| 9.0 | 37 | 0.59 | Terre et Lune |
| 8.75 | 39 | 0.61 | Terre et Lune |
| 8.5 | 35 | 0.83 | Terre et Lune |
| 8.25 | 37 | 0.74 | Terre et Lune |
| 8.0 | 35 | 1.5 | Terre |
| 7.75 | 33 | 1.0 | Terre |
| 7.5 | 36 | 1.13 | Terre |
| 7.25 | 31 | 1.43 | Terre |
| 7.0 | 33 | 6.56 | Terre |
| 6.75 | 34 | 15.96 | Terre |
| 6.5 | 38 | 18.35 | Terre |
| 6.25 | 15 | 22.75 | Au-dessus de la Terre |
| 6.0 | 15 | 9.72 | Au-dessus de la Terre |
| 5.75 | 12 | 3.86 | Au-dessus de la Terre |
| 5.5 | 14 | 1.3 | Au-dessus de la Terre |
| 5.25 | 14 | 0.46 | Au-dessus de la Terre |
| 5.0 | 12 | 0.35 | Au-dessus de la Terre |
| 4.75 | 13 | 0.29 | Au-dessus de la Terre |
| 4.5 | 13 | 0.25 | Au-dessus de la Terre |
| 4.25 | 14 | 0.16 | Au-dessus de la Terre |
| 4.0 | 13 | 0.18 | Au-dessus de la Terre |
| 3.75 | 14 | 0.19 | Au-dessus de la Terre |
| 3.5 | 13 | 0.17 | Au-dessus de la Terre |
| 3.25 | 12 | 0.39 | Au-dessus de la Terre |
| 3.0 | 13 | 10.91 | Près de la surface |
| 2.75 | 13 | 12.22 | Près de la surface |
| 2.5 | 13 | 9.45 | Près de la surface |
| 2.25 | 12 | 4.28 | Près de la surface |
| 2.0 | 13 | 0.21 | Près de la surface |
| 1.75 | 15 | 0.18 | Près de la surface |
| 1.5 | 13 | 0.17 | Près de la surface |
| 1.25 | 13 | 0.12 | Près de la surface |
| 1.0 | 14 | 0.15 | Près de la surface |
| 0.75 | 14 | 0.17 | Près de la surface |
| 0.5 | 13 | 0.16 | Près de la surface |
| 0.25 | 13 | 5.43 | Gouttelette d’eau |
| 0.0 | 14 | 0.15 | Gouttelette d’eau |
| -0.25 | 14 | 0.28 | Gouttelette d’eau |
| -0.5 | 14 | 0.19 | Gouttelette d’eau |
| -0.75 | 14 | 0.12 | Gouttelette d’eau |
| -1.0 | 14 | 0.16 | Gouttelette d’eau |
| -1.25 | 13 | 0.16 | Gouttelette d’eau |
| -1.5 | 14 | 0.22 | Gouttelette d’eau |
| -1.75 | 14 | 0.2 | Gouttelette d’eau |
| -2.0 | 17 | 0.32 | Gouttelette d’eau |
| -2.25 | 16 | 0.57 | Gouttelette d’eau |
| -2.5 | 14 | 1.14 | Gouttelette d’eau |
| -2.75 | 9 | 3.56 | Gouttelette d’eau |
| -3.0 | 13 | 12.16 | Gouttelette d’eau |
| -3.25 | 13 | 12.08 | Gouttelette d’eau |
| -3.5 | 14 | 10.59 | Gouttelette d’eau |
| -3.75 | 14 | 2.99 | Gouttelette d’eau |
| -4.0 | 15 | 3.48 | Gouttelette d’eau |
| -4.25 | 14 | 7.96 | Dans la goutte |
| -4.5 | 14 | 2.9 | Dans la goutte |
| -4.75 | 14 | 0.83 | Dans la goutte |
| -5.0 | 14 | 0.95 | Dans la goutte |
| -5.25 | 13 | 0.84 | Dans la goutte |
| -5.5 | 13 | 0.95 | Dans la goutte |
| -5.75 | 14 | 0.9 | Dans la goutte |
| -6.0 | 14 | 1.03 | Dans la goutte |
| -6.25 | 14 | 0.86 | Dans la goutte |
| -6.5 | 14 | 1.1 | Dans la goutte |
| -6.75 | 15 | 1.03 | Dans la goutte |
| -7.0 | 14 | 0.96 | Dans la goutte |
| -7.25 | 15 | 1.01 | Dans la goutte |
| -7.5 | 14 | 1.16 | Dans la goutte |
| -7.75 | 14 | 2.69 | Dans la goutte |
| -8.0 | 13 | 2.86 | Dans la goutte |
| -8.25 | 14 | 3.01 | Dans la goutte |
| -8.5 | 45 | 3.31 | Dans la goutte |
| -8.75 | 40 | 11.23 | Molécules d’eau |
| -9.0 | 40 | 16.88 | Molécules d’eau |
| -9.25 | 38 | 25.84 | Molécules d’eau |
| -9.5 | 47 | 28.79 | Molécules d’eau |
| -9.75 | 45 | 27.88 | Atome d’oxygène |
| -10.0 | 42 | 21.89 | Atome d’oxygène |
| -10.25 | 12 | 54.75 | Atome d’oxygène |
| -10.5 | 14 | 4.12 | Atome d’oxygène |
| -10.75 | 12 | 3.35 | Atome d’oxygène |
| -11.0 | 14 | 2.78 | Atome d’oxygène |
| -11.25 | 13 | 2.4 | Atome d’oxygène |
| -11.5 | 14 | 1.92 | Atome d’oxygène |
| -11.75 | 14 | 1.54 | Atome d’oxygène |
| -12.0 | 14 | 1.32 | Atome d’oxygène |
| -12.25 | 12 | 0.87 | Atome d’oxygène |
| -12.5 | 14 | 5.83 | Le vide de l’atome |
| -12.75 | 14 | 0.54 | Le vide de l’atome |
| -13.0 | 13 | 0.5 | Le vide de l’atome |
| -13.25 | 14 | 0.6 | Le vide de l’atome |
| -13.5 | 14 | 0.4 | Le vide de l’atome |
| -13.75 | 14 | 3.98 | Noyau d’oxygène |
| -14.0 | 14 | 1.67 | Noyau d’oxygène |
| -14.25 | 14 | 3.86 | Noyau d’oxygène |
| -14.5 | 14 | 10.41 | Noyau d’oxygène |
| -14.75 | 12 | 33.21 | Proton |
| -15.0 | 13 | 29.58 | Proton |
| -15.25 | 14 | 32.06 | Proton |
| -15.5 | 13 | 12.13 | Proton |
| -15.75 | 14 | 6.86 | Proton |
| -16.0 | 11 | 5.67 | Proton |
| -16.25 | 14 | 2.77 | Proton |
| -16.5 | 13 | 12.39 | Proton |
| -16.75 | 12 | 6.31 | Quark |
| -17.0 | 14 | 1.62 | Quark |
| -17.25 | 14 | 1.44 | Quark |
| -17.5 | 14 | 1.41 | Quark |
| -17.75 | 14 | 1.68 | Quark |
| -18.0 | 14 | 1.28 | Quark |
| -18.25 | 14 | 1.34 | Quark |
| -18.5 | 14 | 1.14 | Quark |
| -18.75 | 14 | 0.9 | Quark |
| -19.0 | 14 | 1.19 | Quark |
| -19.25 | 14 | 1.56 | Quark |
| -19.5 | 14 | 5.16 | Inconnu |
| -19.75 | 15 | 1.17 | Inconnu |
| -20.0 | 14 | 1.11 | Inconnu |

Étendues retenues comme vides (écart sous 3 sur tout l’intervalle), traversées trois fois plus vite avec un message « Traversée rapide » : 10^5,5 à 10^3,3 m (au-dessus de la Terre : fond uni, pas d’image plus fine du sol), 10^2 à 10^0,5 m (près de la surface : rien n’est dessiné), 10^0 à 10^-2,3 m (approche de la gouttelette), 10^-4,5 à 10^-8,0 m (eau liquide), 10^-12,6 à 10^-13,4 m (vide de l’atome), 10^-17,2 à 10^-19,3 m (quark). Écarts calmes non retenus : Terre et Lune (10^10,25 à 10^8,25 m) et confins du système solaire, où des astres restent visibles et bougent.

Boules des molécules : allégées, pas remplacées. En niveaux 0 et 1 (téléphones), chaque boule a moins de facettes (12 × 8 au lieu de 20 × 14), même ombrage : environ trois fois moins de triangles (206 136 contre 638 040 à 10^-9,25 m, mesuré par app/test/zoom_fluide.py). Effet en images par seconde sur un vrai téléphone : inconnu tant que Marc n’a pas lu le compteur.
