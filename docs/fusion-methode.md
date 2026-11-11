# Fusion avec Andromède : méthode et conditions de départ (tâche R8)

But (décisions 4 et 5 de Marc) : la rencontre et la fusion de la Voie lactée et d'Andromède sont **gardées, marquées « scénario »**, et **calculées à l'avance avec une vraie attraction mutuelle** (toutes les particules s'attirent), puis rejouées par la page (R10). Ce document fixe la méthode avant tout calcul. Confiance : [Certain] vérifié ; [Probable] source connue, chiffre non relu ; [À vérifier].

## 1. Logiciels (libres et éprouvés)

| Rôle | Logiciel | Pourquoi | Référence |
|---|---|---|---|
| Conditions initiales : galaxies à l'équilibre (halo, disque, bulbe) | **AGAMA** (pip `agama`) | Fonctions de distribution publiées, utilisé pour les modèles de la Voie lactée et du Grand Nuage | Vasiliev 2019, MNRAS 482, 1525 [Probable] |
| Gravité entre toutes les particules | **falcON** par **pyfalcon** (pip `pyfalcon`) | Méthode multipolaire rapide en O(N), utilisée dans les simulations Voie lactée + Grand Nuage de Vasiliev et al. 2021 | Dehnen 2000, ApJ 536, L39 ; Dehnen 2002, J. Comp. Phys. 179, 27 [Probable] |
| Intégration du temps | Saute-mouton (leapfrog « kick-drift-kick »), pas fixe | Symplectique : l'énergie ne dérive pas | — |

Unités : masse en masses solaires, longueur en kpc, vitesse en km/s (G = 4,30091 × 10⁻⁶) ; temps en kpc/(km/s) = 0,9778 Ga.

## 2. Modèles des galaxies (cohérents avec la page)

La page calcule l'orbite d'Andromède avec `mwMass` (20_physics.js, 25_future.js) : bulbe de Hernquist, disque de Miyamoto-Nagai, halo NFW calé sur 230 km/s au Soleil, coupé à 220 kpc ; Andromède = 1,5 fois cette masse, rayons × 1,15 (`M31_MASS_RATIO`). Le calcul reprend ces masses pour que la fusion et l'orbite de la page soient comparables.

| Galaxie | Halo | Disque (étoiles) | Bulbe | Sources |
|---|---|---|---|---|
| Voie lactée | NFW, masse d'échelle 5,60 × 10¹¹, r_s = 16 kpc, coupé à 220 kpc : 1,06 × 10¹² M☉ dans 220 kpc [Certain : calcul du modèle de la page] | 6,8 × 10¹⁰ M☉, exponentiel R_d = 2,6 kpc, épaisseur 0,3 kpc (le Miyamoto-Nagai de la page n'a pas de fonction de distribution simple : on garde sa masse) | Hernquist 0,5 × 10¹⁰ M☉, a = 0,5 kpc | Page (`GAL`) ; R_d : Bland-Hawthorn et Gerhard 2016 [Probable] |
| Andromède | même forme, masse × 1,5, rayons × 1,15 | 1,02 × 10¹¹ M☉, R_d = 3,0 kpc | 0,75 × 10¹⁰ M☉, a = 0,58 kpc | Page (`M31_MASS_RATIO`) |
| Triangle (M33), corps étendu | Hernquist 2,5 × 10¹¹ M☉, a = 20 kpc | 4,8 × 10⁹ M☉, R_d = 1,4 kpc | — | Patel, Besla et Sohn 2017 [À vérifier] ; Corbelli et al. 2014 [À vérifier] |
| Grand Nuage, corps étendu | Hernquist 1,8 × 10¹¹ M☉, a = 12 kpc (valeur de la page ; publiées : 1,3 à 2,5 × 10¹¹) | 2,7 × 10⁹ M☉, R_d = 1,5 kpc | — | Page (`LMC_MASS`) ; disque : van der Marel et al. 2002 [À vérifier] |

Chaque galaxie est d'abord mise à l'équilibre seule (AGAMA : halo et bulbe en fonction de distribution quasi sphérique, disque en quasi-isotherme, dans le potentiel total de la galaxie), puis placée à sa position et sa vitesse de départ.

## 3. Positions et vitesses de départ (aujourd'hui, repère galactocentrique de la page, kpc et km/s)

| Corps | Position | Vitesse | Source |
|---|---|---|---|
| Andromède | (−385,4 ; 623,0 ; −287,6), 785 kpc | **Retenue : « Gaia, 2025 »** (28,4 ; −109,8 ; 41,4), la mesure par défaut de la page. Les deux autres de la page (Hubble 2012 : 44,1 ; −118,0 ; 3,1 ; Gaia 2021) sont gardées pour des essais | `DATA.M31` (data3.js) ; `M31_MEAS` (60_app.js) [Certain : valeurs du code] ; mouvement propre : Wu et al. 2025 ; van der Marel et al. 2012 ; Salomon et al. 2021 [Probable] |
| Axe de rotation d'Andromède | `DATA.M31.spin` (−0,445 ; −0,766 ; −0,464) | — | data3.js [Certain : valeur du code] |
| Grand Nuage | (−1,0 ; −41,0 ; −27,8) | (−57,2 ; −234,5 ; 220,6) | `DATA.LMC` (data4.js) ; Kallivayalil et al. 2013 [Probable] |
| Triangle | position et vitesse de la page | | `DATA.LGV` (data14.js) ; van der Marel et al. 2019 [Probable] |
| 38 autres galaxies naines | positions et vitesses de la page | | `DATA.LGV` ; Pace 2024 |
| Soleil | 8,2 kpc du centre, dans le plan, vitesse circulaire du modèle (230 km/s) | | Page (`GAL.R0`, `GAL.V0`) |

**Incertitude, dite telle quelle dans la page** : Sawala et al. 2025 (Nature Astronomy) trouvent environ une chance sur deux de fusion dans les 10 milliards d'années, en propageant les incertitudes des mesures [Certain, vérifié en R4]. Le calcul ne montre qu'**un** scénario, celui de la vitesse retenue : la page le marque « scénario calculé ». Les deux autres vitesses donnent d'autres dates, ou pas de fusion ; le panneau Chronologie les garde pour l'orbite simple de la page.

## 4. Traceurs

Le Soleil et les 38 galaxies naines sont des **traceurs sans masse** : ils subissent l'attraction de toutes les particules, sans en exercer. Le Triangle et le Grand Nuage, eux, ont leur masse (corps étendus).

## 5. Nombre de particules, pas de temps, budget

| | Valeur | Raison |
|---|---|---|
| Particules (calcul complet, R9) | ≈ 600 000 : halos 400 000, disques et bulbes 200 000 | Masse d'une particule de halo ≈ 8 × 10⁶ M☉, d'étoile ≈ 5 × 10⁵ M☉ (rapport < 20, pratique courante) |
| Adoucissement | 0,1 kpc (étoiles), 0,4 kpc (halos) | Résolution des disques sans collisions artificielles |
| Pas de temps | 1 Ma, fixe | Un tour au centre d'un disque dure plus de 50 Ma [Probable] |
| Durée | 0 à 10 Ga | La fusion de la page tombe vers 5,85 Ga ; on va jusqu'à ce que le reste se calme |
| Budget de calcul | moins de 6 heures sur une machine de GitHub (ubuntu, 4 cœurs) ; contrôlé par l'essai réduit (temps par pas mesuré) | Contrainte du lot |
| Images clés | toutes les 20 Ma (500 images) : 30 000 étoiles affichées, positions en entiers 16 bits relatifs au centre de masse, plus les centres des galaxies et les traceurs | |
| Taille des fichiers | ≈ 90 Mo pour les images clés, découpées en paquets de 25 images (≈ 3,6 Mo chacun), chargés à la demande depuis Storage (T2, T6 de la mission 1) | Budget : moins de 100 Mo en tout |

## 6. Contrôles

- **Essai réduit (fin de R8)** : 15 000 particules par grande galaxie, sur 1 milliard d'années, même code. Fini quand la dérive d'énergie totale est inférieure à 1 % (`pipeline/fusion/essai.py`, tâche GitHub `fusion-essai`).
  **Résultat (11 novembre 2026, tâche GitHub « Fusion - essai », exécution 43114 et suivantes)** : 30 000 particules, 1 milliard d'années, pas de 1 Ma : dérive maximale **0,52 %** → PASSE. Masse de la Voie lactée échantillonnée : 9,87 × 10¹¹ M☉ (la coupure douce du halo retire une partie des 1,06 × 10¹² de la page) ; vitesse circulaire à 2 R_d : 246 km/s (Voie lactée), 280 km/s (Andromède). Temps : 0,032 s par pas pour 30 000 particules, soit environ 1,8 heure pour le calcul complet si le temps croît comme N [Probable : falcON est en O(N)].
  **Conséquence pour R9** : la dérive croît régulièrement (environ 0,5 % par milliard d'années) ; sur 10 milliards d'années elle dépasserait 1 %. Le calcul complet utilise donc un pas de 0,25 Ma (dérive attendue divisée par environ 16 si elle vient du pas, à vérifier sur un second essai), ce qui porte l'estimation à environ 7 heures : au-delà des 6 heures permises, le calcul est découpé en deux tâches enchaînées (reprise depuis un instantané).
- **Calcul complet (R9)** : dérive d'énergie inférieure à 1 % sur tout le calcul ; date de la fusion (centres à moins de 10 kpc, puis plus de séparation) comparée aux 5,85 Ga de l'estimation à deux corps de la page et aux valeurs publiées (Sawala et al. 2025 ; van der Marel et al. 2019 : environ 4,5 Ga pour le premier passage [À vérifier]).

## 7. Ce qui reste supposé, et dit

- Les profils des halos (NFW, Hernquist) et les masses viennent de la page ou de publications citées ; le calcul ne les mesure pas.
- Le gaz, la formation d'étoiles et les trous noirs centraux ne sont pas calculés.
- Un seul scénario (une vitesse d'Andromède) est montré.
