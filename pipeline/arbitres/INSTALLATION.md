# Codes arbitres — installation du 18/11/2026 (processeur seul)

Carte graphique jamais touchée : pas de CUDA, pas de nvidia-smi, aucun processus arrêté, code d'Univers non modifié.
Rien de commité ni poussé.

## 1. WSL — [Certain]

```
wsl --status   → Default Version: 2
wsl --version  → WSL 2.7.13.0, noyau 6.18.33.2-2, WSLg 1.0.73.2
wsl -l -v      → « Windows Subsystem for Linux has no installed distributions. »
```

Au premier passage (vers 11 h 45, heure du Québec), WSL 2 était présent, mais **aucune distribution n'était installée**.

**Mise à jour 13 h 09–13 h 25 (heure du Québec)** : Marc a installé Ubuntu, puis les paquets (lui seul a le mot de passe sudo).
```
wsl -l -v                          → * Ubuntu-24.04    Running    2
wsl -d Ubuntu-24.04 -- whoami      → marcr
wsl -d Ubuntu-24.04 -- sudo -n true → « sudo: a password is required »  (donc paquets tapés par Marc)
lsb_release -d                     → Ubuntu 24.04.5 LTS ; 32 cœurs logiques visibles ; 953 Go libres sur /
```
Ligne tapée par Marc : `sudo apt update && sudo apt install -y build-essential gfortran libopenmpi-dev openmpi-bin
libgsl-dev libfftw3-dev libhdf5-dev libhdf5-openmpi-dev cmake git python3-numpy python3-h5py`
Vérifié par `dpkg -l` : OpenMPI 4.1.6, HDF5 1.10.10, GSL 2.7.1, FFTW 3.3.10, cmake 3.28.3, gfortran 13.2, h5py 3.10.

## 2. REBOUND sous Windows

### Installé

| Quoi | Où | Taille |
|---|---|---|
| venv Python 3.14.7 | `%LOCALAPPDATA%\univers-arbitres-venv` (voir note) | 67 Mo |
| rebound 5.2.3 (roue officielle win_amd64), numpy 2.5.5 | dans ce venv | (compris) |
| script + résultats | `C:\dev\univers-natif\pipeline\arbitres\` | 0,55 Mo |

Commandes :
```
py -3 -m venv %LOCALAPPDATA%\univers-arbitres-venv
python -m pip install --only-binary=:all: rebound numpy
```

**Note [Certain]** : l'app Claude est empaquetée (MSIX) ; Windows a redirigé le venv vers
`%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\univers-arbitres-venv`. Il n'est visible à l'adresse
`%LOCALAPPDATA%\univers-arbitres-venv` que pour les processus lancés depuis Claude. `univers-gpu-venv` n'a pas été touché.

### Échec : REBOUNDx — [Certain]

`pip install reboundx` → `error: Microsoft Visual C++ 14.0 or greater is required`. Aucune roue Windows publiée
(ni 3.12, ni 3.13, ni 3.14) et pas de compilateur C sur le PC. Installer « Microsoft C++ Build Tools » demande
les droits administrateur → non fait.

**Remplacement** : la relativité du Soleil est codée dans le script, en force additionnelle REBOUND (vue numpy sur le
tableau C des particules) : formule de Schwarzschild 1PN, corps d'essai, coordonnées harmoniques,
`a = GM☉/(c²r³)·[(4GM☉/r − v²) r⃗ + 4(r⃗·v⃗) v⃗]`, réaction opposée sur le Soleil. C'est le terme dominant de l'effet
« gr » de REBOUNDx ; les termes en masses planétaires sont omis [Probable : négligeable à ±200 ans].

### Le script

`pipeline/arbitres/rebound_systeme_solaire.py` — Soleil + Mercure, Vénus, Terre-Lune (barycentre), Mars, Jupiter,
Saturne, Uranus, Neptune, Pluton, Cérès, Vesta, Pallas, Hygie. IAS15, G = 1, masses = GM (DE440), UA / jour,
écliptique J2000. Sortie tous les 10 ans sur ±200 ans (41 instantanés, positions et vitesses barycentriques).

```
python -I rebound_systeme_solaire.py                       → resultats/rebound_ref.json
python -I rebound_systeme_solaire.py --sans-gr             → resultats/rebound_ref_sans_gr.json
python -I rebound_systeme_solaire.py --depart-horizons     → resultats/rebound_ref_depart_horizons.json
python -I rebound_systeme_solaire.py --depart-horizons --sans-gr
```

Départ par défaut : lu dans `natif/physique/nbody_donnees.h` (Q héliocentrique, V barycentrique, Soleil reconstitué
comme `Integrator::barycentric` et `sunVel`). `kScale` n'est pas appliqué (calage propre au pas de 4 jours).
Chaque tir compare aussi aux positions JPL Horizons de `app/test/nbody_ref.json` aux dates dans ±200 ans.

### Résultats mesurés

| Tir | Erreur d'énergie relative max | Durée |
|---|---|---|
| départ nbody_donnees.h, avec relativité | 1,5 × 10⁻⁹ (*) | 40 s |
| départ nbody_donnees.h, newtonien | 1,8 × 10⁻¹⁵ | 1,8 s |
| départ Horizons, avec relativité | 1,5 × 10⁻⁹ (*) | 40 s |
| départ Horizons, newtonien | 3,0 × 10⁻¹⁵ | 1,4 s |

(*) énergie newtonienne : avec la relativité elle n'est pas censée être conservée exactement, ce n'est pas une erreur
d'intégration. Le chiffre qui juge IAS15 est celui du tir newtonien : ~10⁻¹⁵ [Certain].

Écart aux positions JPL Horizons, en km (avec relativité) :

| Date | Départ | Mercure | Vénus | Terre-Lune | Mars | Jupiter | Neptune | Pluton | Cérès |
|---|---|---|---|---|---|---|---|---|---|
| 1850-01-01 | nbody_donnees.h | 2 115 672 | 93 826 | 49 133 | 10 730 | 146 | 95 | 1 133 | 3 635 |
| 1850-01-01 | Horizons | **147** | 133 | 15 821 | 112 | 180 | 1 441 | 1 749 | 200 |
| 2126-11-10 | nbody_donnees.h | 1 380 657 | 52 929 | 27 663 | 5 887 | 147 | 222 | 1 185 | 1 664 |
| 2126-11-10 | Horizons | **125** | 110 | 8 994 | 131 | 66 | 917 | 963 | 338 |

Constats :
1. **Les vitesses de `nbody_donnees.h` ne sont pas l'état physique** [Certain, mesuré] : elles sont calées pour le
   schéma natif à pas de 4 jours (Mercure : écart relatif 1,9 × 10⁻⁶ à Horizons, la valeur de `kScale`). Un intégrateur
   exact parti de là dérive de 2 millions de km sur Mercure en 177 ans. Pour arbitrer, **utiliser
   `rebound_ref_depart_horizons.json`** (départ JPL Horizons, même époque JD 2461354.5).
2. Avec le départ Horizons et la relativité, Mercure reste à ~150 km de JPL sur 177 ans [Certain] ; sans relativité,
   72 000 km [Certain] : la correction relativiste maison fait bien son travail.
3. Terre-Lune 9 000 à 16 000 km : la Lune est fondue dans un point [Probable : le couple Terre-Lune et les marées ne
   sont pas modélisés]. Neptune et Pluton ~1 000 km, Soleil ~120 km partout : corps absents du modèle (autres
   astéroïdes, ceinture de Kuiper) [Probable].

## 3. GADGET-4 et GIZMO (Ubuntu 24.04 sous WSL2, processeur seul, 4 processus MPI)

Tout est dans `~/arbitres` côté Ubuntu (`\\wsl$\Ubuntu-24.04\home\marcr\arbitres`). Les scripts de compilation et
d'essai sont copiés dans `pipeline/arbitres/wsl/` (`gadget4_g2.sh`, `gizmo_isodisk.sh`).

### GADGET-4 — compilé et testé [Certain]

- Source : `git clone http://gitlab.mpcdf.mpg.de/vrs/gadget4` → version 4.0, révision c64a4a2 du 09/11/2026.
- Fichiers de départ officiels : `https://wwwmpa.mpa-garching.mpg.de/gadget4/example_ics.tar` (192 Mo), dans `~/arbitres/ics`.
- Exemple **G2-galaxy** : galaxie isolée sans collisions, 60 000 corps, gravité seule (arbre), double précision, sans PM ni GPU.
- Compilation (SYSTYPE Generic-gcc ; `python` relié à python3 dans `~/arbitres/bin`) :
  `make -j8 CONFIG=examples/G2-galaxy/Config.sh BUILD_DIR=build-g2 EXEC=Gadget4-g2 HDF5_INCL="-I/usr/include/hdf5/serial" HDF5_LIBS="-L/usr/lib/x86_64-linux-gnu/hdf5/serial -lhdf5 -lz"`
- Essai : `mpirun -np 4 ./Gadget4-g2 param.txt`, avec `TimeLimitCPU 60`.
  - Sortie : « reaching time-limit. stopping. », 602 pas synchronisés, temps simulé 0,88 sur 3,0. Instantanés
    `snapshot_000/001.hdf5` et fichiers de reprise écrits.
  - Énergie totale (energy.txt) : −316 464 au départ, −316 776 à t = 0,855, soit une dérive relative de 1,0 × 10⁻³
    [Certain, calculé à partir d'energy.txt]. C'est le comportement attendu d'un code en arbre à ces réglages [Probable].

### GIZMO public — compilé et testé [Certain]

- Source : `git clone https://github.com/pfhopkins/gizmo-public gizmo` → « GIZMO version 2026 », révision 78b66ffc du 04/10/2026.
- SYSTYPE `github-ubuntu` (fourni par GIZMO). Config.sh retenu, le minimum qui compile :
  `HYDRO_MESHLESS_FINITE_MASS` (MFM), `ADAPTIVE_GRAVSOFT_FORGAS`, `COOLING`, `GALSF` (formation d'étoiles),
  `OUTPUT_IN_DOUBLEPRECISION`. La gravité (arbre) est active par défaut.
- **Écarté** : `BOX_PERIODIC` + `PMGRID=64` (réglage du test officiel). Il demande `fftw3-mpi.h`, donc le paquet
  `libfftw3-mpi-dev`, absent de la ligne apt. Pour l'ajouter : `sudo apt install -y libfftw3-mpi-dev` (mot de passe de Marc).
- Essai : test officiel **isodisk** (disque galactique isolé, Hopkins 2015 : 35 000 cellules de gaz, 80 000 étoiles et
  matière noire, 1 trou noir), fichier `http://www.tapir.caltech.edu/~phopkins/sims/isodisk_ics.hdf5`, `TREECOOL` du dépôt.
  Ajouts à `isodisk.params` : `CritPhysDensity 100` et `SfEffPerFreeFall 1.0` (exigés par GALSF ; valeurs courantes de
  la doc GIZMO [Probable]), `TimeLimitCPU 60`. Le réglage `Softening_Type5 0` (trou noir central sans adoucissement)
  bloquait le pas de temps à 10⁻¹⁹ ; je l'ai mis à 0,05 kpc.
  - Sortie : « reaching time-limit. stopping. », 3 532 pas, temps simulé 0,057 (≈ 56 Ma). Des étoiles se forment :
    sfr.txt passe de 0 à 14,8 unités de code. Ce taux élevé est le transitoire de départ, sans rétroaction stellaire
    [Probable] : ce n'est pas une mesure physique.

## Place disque

- Windows : ~68 Mo (venv REBOUND 67 Mo, script et résultats 0,55 Mo). Cache pip non compté.
- Ubuntu : 660 Mo dans `~/arbitres` (fichiers de départ 367 Mo, GIZMO 119 Mo, essais 122 Mo, GADGET-4 53 Mo).
  Ubuntu entier : 2,9 Go sur son disque virtuel, paquets compris.
