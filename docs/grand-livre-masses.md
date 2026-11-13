# Grand livre des constantes et des masses (généré)

Généré par `pipeline/constantes/grand_livre.py` le 2026-11-13 depuis la table unique (`pipeline/constantes/univers.json`). Ne pas éditer : relancer le script. Une ligne « ÉCART » est une valeur qu’un fil doit remplacer par la lecture de la table.

## 1. Repère et cosmologie

| Grandeur | Table | Source comparée | Valeur | Fichier | Verdict |
|---|---|---|---|---|---|
| R0 (kpc) | 8.2 | appli (kR0) | 8.2 | `natif/physique/galaxie_orbites.h` | conforme |
| R0 (kpc) | 8.2 | ensemble Sawala (astropy « v4.0 ») | 8.122 | `pipeline/fusion/groupe_local_clones.py` | ÉCART |
| R0 (kpc) | 8.2 | ancien modèle de fusion | 8.2 | `pipeline/fusion/modeles.py` | conforme |
| R0 (kpc) | 8.2 | étoiles clones | 8.2 | `pipeline/natif/clones_etoiles.py` | conforme |
| v0 (vitesse circulaire au Soleil) (km/s) | 232.8 | appli (kV0) | 230 | `natif/physique/galaxie_orbites.h` | ÉCART |
| v0 (vitesse circulaire au Soleil) (km/s) | 232.8 | ancien modèle de fusion | 230 | `pipeline/fusion/modeles.py` | ÉCART |
| vitesse du Soleil, composante y (km/s) | 245 | appli (kSunUvw) | 242.2 | `natif/physique/galaxie_orbites.h` | ÉCART |
| vitesse du Soleil, composante y (km/s) | 245 | ensemble Sawala (astropy « v4.0 ») | 245.6 | `pipeline/fusion/groupe_local_clones.py` | conforme |
| H0 (km/s/Mpc) | 67.4 | appli (cosmologie.h) | 67.4 | `natif/src/cosmologie.h` | conforme |
| H0 (km/s/Mpc) | 67.4 | ensemble Sawala (densité critique) | 67.66 | `pipeline/fusion/groupe_local_clones.py` | conforme |
| Ω_Λ | 0.685 | appli (cosmologie.h) | 0.685 | `natif/src/cosmologie.h` | conforme |

## 2. Galaxies aujourd’hui

| Grandeur | Table | Source comparée | Valeur | Fichier | Verdict |
|---|---|---|---|---|---|
| distance de Andromède (M31) (kpc) | 761 | ancien calcul (conditions.json) | 783 | `pipeline/fusion/conditions.json` | ÉCART |
| distance de Triangle (M33) (kpc) | 859 | ancien calcul (conditions.json) | 809 | `pipeline/fusion/conditions.json` | ÉCART |
| distance de Grand Nuage de Magellan (kpc) | 49.59 | ancien calcul (conditions.json) | 50.1 | `pipeline/fusion/conditions.json` | ÉCART |

Vitesses d’ensemble (repère phys::galaxie, km/s ; tolérance 5 km/s) :

| Galaxie | Table | Ancien calcul (conditions.json) | Écart | Verdict |
|---|---|---|---|---|
| Andromède (M31) | [31.921, -103.866, 43.602] | [28.4, -109.8, 41.4] | 7.2 | ÉCART |
| Triangle (M33) | [3.068, 97.67, 185.697] | [39.6, 79.64000000000001, 126.05] | 72.2 | ÉCART |
| Grand Nuage de Magellan | [-39.656, -226.468, 227.159] | [-57.2, -234.53, 220.56] | 20.4 | ÉCART |

## 3. Masses totales

Table : centre et largeur de la loi de masse de l’ensemble Monte-Carlo, égal à la masse totale du modèle du calcul N-corps quand il existe (le film est donc un tirage de l’ensemble). « Écart en σ » : distance à ce centre en largeurs de la loi.

| Galaxie | Table (M☉) | σ | Source comparée | Valeur | Fichier | Écart en σ | Verdict |
|---|---|---|---|---|---|---|---|
| Voie lactée | 1.343e+12 | 3e+11 | ensemble Sawala 2025 (M200) | 1e+12 | `pipeline/fusion/groupe_local_clones.py` | 1.14 | ÉCART |
| Voie lactée | 1.343e+12 | 3e+11 | ancien modèle de fusion (halo coupé à 220 kpc) | 1.06e+12 | `docs/fusion-methode.md § 2` | 0.94 | ÉCART |
| Andromède (M31) | 1.065e+12 | 2.5e+11 | ensemble Sawala 2025 (M200) | 1.3e+12 | `pipeline/fusion/groupe_local_clones.py` | 0.94 | ÉCART |
| Andromède (M31) | 1.065e+12 | 2.5e+11 | ancien calcul de fusion | 1.59e+12 | `docs/analyse-architecture.md § 2.2` | 2.1 | ÉCART |
| Triangle (M33) | 4.081e+11 | 1e+11 | ensemble Sawala 2025 (M200) | 3e+11 | `pipeline/fusion/groupe_local_clones.py` | 1.08 | ÉCART |
| Triangle (M33) | 4.081e+11 | 1e+11 | ancien modèle (Plummer) | 2.5e+11 | `docs/fusion-methode.md § 2` | 1.58 | ÉCART |
| Grand Nuage de Magellan | 1.379e+11 | 2.5e+10 | ensemble Sawala 2025 (M200) | 1.5e+11 | `pipeline/fusion/groupe_local_clones.py` | 0.48 | ÉCART |
| Grand Nuage de Magellan | 1.379e+11 | 2.5e+10 | ancien modèle (Hernquist de la page) | 1.8e+11 | `docs/fusion-methode.md § 2` | 1.68 | ÉCART |
| Grand Nuage de Magellan | 1.379e+11 | 2.5e+10 | publié (Erkal et al. 2019) | 1.38e+11 | `table_source.py` | 0.0 | conforme |

## 4. Composition des modèles (calculé)

| Galaxie | Composante | Masse (M☉) |
|---|---|---|
| Voie lactée | halo | 1.276e+12 |
| Voie lactée | bulbe | 8.878e+09 |
| Voie lactée | disque | 3.519e+10 |
| Voie lactée | disque_epais | 1.049e+10 |
| Voie lactée | gaz | 1.22e+10 |
| Voie lactée | total | 1.343e+12 |
| Andromède (M31) | halo | 9.721e+11 |
| Andromède (M31) | bulbe | 3.1e+10 |
| Andromède (M31) | disque | 5.6e+10 |
| Andromède (M31) | gaz | 5.6e+09 |
| Andromède (M31) | total | 1.065e+12 |
| Triangle (M33) | halo | 4.003e+11 |
| Triangle (M33) | disque | 4.8e+09 |
| Triangle (M33) | gaz | 3e+09 |
| Triangle (M33) | total | 4.081e+11 |
| Grand Nuage de Magellan | halo | 1.352e+11 |
| Grand Nuage de Magellan | disque | 2.7e+09 |
| Grand Nuage de Magellan | total | 1.379e+11 |
| Petit Nuage de Magellan | halo | 2.13e+09 |
| Petit Nuage de Magellan | disque | 3.1e+08 |
| Petit Nuage de Magellan | gaz | 5.6e+08 |
| Petit Nuage de Magellan | total | 3e+09 |

## 5. Points à trancher signalés par ce livre

- **Grand Nuage** : `modeles_v2.py` (branche modeles-depart) pose un Hernquist de 1,38 × 10¹¹ M☉ et 16,1 kpc, puis le coupe à 100 kpc : il ne garde que 0,97 × 10¹¹ M☉, 30 % sous la mesure (Erkal 2019). La table corrige : 2,29 × 10¹¹ et 25,8 kpc avant coupure, soit 1.35e+11 M☉ de halo après coupure et 1,7 × 10¹⁰ M☉ dans 8,7 kpc. Le fil des galaxies de départ doit refaire le tir de stabilité du Grand Nuage (~10 min).
- **v0** : l’appli tourne avec 230 km/s, la table et le modèle de McMillan avec 232,8. Brancher `constantes_univers.h` dans `galaxie_orbites.h` change toutes les orbites d’étoiles de ~1 % : c’est un changement visible, à faire par le fil qui possède ce fichier.
- **Distance d’Andromède** : 761 kpc (table) contre 783 kpc (ancien calcul). La table suit Li et al. 2021 (Céphéides), comme Sawala 2025.
- **Triangle** : 859 kpc (table, Sawala 2025) contre 809 (ancien calcul) et 840 (Corbelli 2014, utilisé par le modèle de masse).
- **Petit Nuage** : masse totale adoptée (3 ± 1 × 10⁹ M☉), pas mesurée ; le modèle (halo, étoiles, gaz) est réglé ici sur la matière noire dans 4 kpc de Di Teodoro et al. 2019.
