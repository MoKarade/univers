# Départ cosmologique contraint (piste 2, à la manière de HESTIA/CLUES)

But : faire naître le Groupe local de l'Univers jeune (z = 99), dans son vrai environnement, au lieu de galaxies posées
à la main, puis raccorder ce passé (« modèle : un passé possible ») à notre film calé sur le ciel mesuré, vers −1 Ga.
Plan et décisions de Marc : Claude Doc https://claude.ai/artifact/GdaGuiRSS4UPi7Gc4e7YFM (19/11/2026).
Tout tourne au processeur (WSL2, GADGET-4) : la carte graphique reste au grand calcul.

## Chaîne (pipeline/contraint/)

| Étape | Fichier | Contrôle mesuré (19/11) |
|---|---|---|
| Cosmologie linéaire Planck 2018, énergie noire comprise | `cosmo_lineaire.py` (+ `test_cosmo_lineaire.py`, 7 essais) | σ8 retrouvé ; j1(x)/x exact à 1e-6 |
| Filtre de Wiener des 38 053 groupes de Cosmicflows-4 | `cf4_wiener.py`, `vitesse_origine.py` | Groupe local : 505 km/s vers l = 281°, b = +24° (fond diffus : 627 km/s, 276°, +30°) ; corrélation 0,55–0,71 avec Courtois 2023 |
| Densité et vitesses de 2MRS (outil public CORAS, Lilow & Nusser 2021) | `comparer_2mrs.py` | 623 km/s vers 268°, +28° ; CF4 et 2MRS concordent (0,55–0,70 à r < 50 Mpc/h) |
| Réalisations contraintes jointes (Hoffman & Ribak 1991) + Zel'dovich inverse | `realisations.py`, `realisations_jointes.py` | boîte 640 Mpc/h (320 fausse le filtre : 0,84–0,95 au lieu de 0,999) ; χ²/N 0,96 (vitesses), 1,03 (densités) |
| Vierge imposée (δ_L = 1,8 dans 13 Mpc/h) + passage à genetIC | `exporter_genetic.py`, `transfert_genetic.py` | genetIC importe δ à z_in (rapport D(99)² = 1,62e-4 mesuré) ; Vierge 1,1–1,5e15 M☉ à 5,3 Mpc de sa place (mesure : ~1,2e15) |
| Zoom genetIC + GADGET-4 | `calcul/lancer_graine.sh`, `calcul/genetic_*.txt`, `calcul/gadget_*` | 30 min par graine (2,1 M particules, 8 fils) |
| Ajustement de la paire (modifications genetIC) | `calcul/mods_paire_v*.txt` | voir ci-dessous |
| Lecture des résultats | `analyser_paire.py` | critères HESTIA + 785 kpc, −110 km/s, < 60 km/s |
| Balayage de graines | `calcul/balayage_windows.ps1` + `calcul/balayage_wsl.sh` | pause si le jeu de Marc tourne |

## Ajustement de la paire (graine 1, Vierge imposée)

| Essai | Réglage | Résultat à z = 0 |
|---|---|---|
| v1 | pics écartés de 2 Mpc/h | fusion : 1 halo de 3,3e12 M☉ |
| v2, v3 | 3,5 et 4,5 Mpc/h, zone recentrée | petit groupe de 1,7–3,1e13 M☉ |
| v5 | 4 Mpc/h, environnement calme (δ_L 0,3 dans 4 Mpc/h) | 1,23 et 1,16e12 M☉, mais 3,9 Mpc et s'éloignent |
| v6, v7 | 3,0 et 2,5 Mpc/h | 2,4 et 2,1 Mpc, s'éloignent encore |
| v8 | 2,5 Mpc/h, selle plus dense (1,2) | 1,6 Mpc, +30 km/s |
| **v11** | **2,0 Mpc/h, selle 1,2** | **1,73 et 1,36e12 M☉, 1 072 kpc, −40 km/s, 45 km/s transverse : passe HESTIA** |
| v12, v13 | v11 recentré | la paire se défait (déplacer la zone change les petites échelles) |
| v15 | 2,0 Mpc/h, selle 1,4, pics 1,7 | passe HESTIA : 1,85 et 1,45e12, 1 089 kpc, −50 km/s |

Modifications toujours faibles (Δχ² entre 0,5 et 3) : l'Univers jeune reste statistiquement ordinaire.

**Zoom fin de v11** (287 000 particules de 4,1e7 M☉/h, 30 instantanés de a = 0,1 à 1, 5 339 s sur 12 fils) :
Vierge 1,24e15 M☉ ; paire 1,58 et 1,72e12 M☉, 1 262 kpc, −23 km/s, 43 km/s transverse. [Certain, mesuré]
Référence HESTIA haute résolution : 675 à 866 kpc, −9 à −102 km/s (Libeskind et al. 2020, table 1).

## Modèles et limites (à dire à l'écran)
- Fonction de transfert d'Eisenstein & Hu sans oscillations (~5 % sur P(k)) : CAMB n'a pas pu être installé.
- Densité 2MRS : champ de CORAS pris comme donnée, ramené au linéaire par l'effondrement sphérique (Bernardeau 1994).
- Vierge et paire : valeurs visées choisies et ajustées (modèle), pas mesurées.
- La paire est à ~5 Mpc de la place de l'observateur, la Vierge à 5,3 Mpc de la sienne.
- Matière noire seule pour l'instant ; pas de gaz.

## Suite
1. Resserrer la paire (viser 785 kpc, −110 km/s) en gardant la zone de v11.
2. Raccord avec notre film à −1 Ga : croissance des halos, matière qui arrive, satellites, marée de la Vierge.
3. Zooms plus fins (~15 M particules) puis gaz ; stockage lourd sur le Drive (accord de Marc, ≤ 100 Go).

## Histoire de la paire (zoom fin v11) — `docs/histoire_paire_fin_v11.json`, `pipeline/contraint/histoire_paire.py`
Suivi simple (groupe le plus proche de la position prédite, masse compatible) [À vérifier : pas d'arbre de fusion complet].

| Temps | Halo 1 | Halo 2 | Séparation |
|---|---|---|---|
| −13,2 Ga | 5e9 M☉ | 2e9 M☉ | 276 kpc |
| −9,9 Ga | 2,6e11 | 1,8e11 | 896 kpc |
| −4,3 Ga | 8,2e11 | 1,4e12 | 1 319 kpc |
| −2,5 Ga | 1,52e12 | 1,60e12 | 1 314 kpc |
| −1,0 Ga (raccord) | ~1,55e12 | ~1,56e12 | ~1 287 kpc, se rapprochent à quelques km/s |
| aujourd'hui | 1,58e12 | 1,72e12 | 1 262 kpc, −23 km/s |

Pour le raccord : sur le dernier milliard d'années, les halos ne grossissent que de 2 à 10 % [Certain dans ce calcul] ;
un groupe de 3,8e13 M☉ se forme à ~10 Mpc (modèle, à comparer au groupe de Centaurus A, ~1e13 M☉ à 3,7 Mpc).

## Paire retenue : essai 17, zoom fin (20/11/2026) — `docs/histoire_paire_fin_v17.json`
Réglage arrêté à v17 (pics δ_L 2,2, selle 1,2, écart de Lagrange 2,0 Mpc/h, environnement 0,3 ; Δχ² 4,97) : la vitesse
d'approche plafonne vers −50 à −60 km/s quel que soit le réglage (v16 à v19, mesuré).
Zoom fin (5 298 s, 12 fils) : **paire 2,10 et 1,74e12 M☉, 1 028 kpc, −61 km/s, 27 km/s transverse, isolée (passe HESTIA) ;
Vierge 1,19e15 M☉ à 5,3 Mpc de sa place.** [Certain, mesuré] Mesuré dans le ciel : 785 kpc, −110 km/s, < 60 km/s.
Écart restant (modèle à dire à l'écran) : paire 30 % trop lourde et 240 kpc trop écartée ; approche deux fois trop lente.
