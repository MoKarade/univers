# Appli PC « Univers »

Plan et jalons : `docs/plan-natif.md`.

## Compilation et tests portables (Linux et Windows, sans GPU)

La bibliothèque physique (`natif/physique/`) et les 8 essais CPU portables ne dépendent ni de Vulkan ni de `windows.h`
(la projection mémoire `src/fichier_mappe.h` s'adapte à Win32 et POSIX).

- **Build autonome de la bibliothèque physique** :
  ```bash
  cmake -S natif/physique -B /tmp/univers-physique-build -DCMAKE_BUILD_TYPE=Release
  cmake --build /tmp/univers-physique-build
  ctest --test-dir /tmp/univers-physique-build --output-on-failure
  ```
  Exécute `essai_galaxie` (orbites Voie lactée + barre Dehnen), `essai_systeme_solaire --noyau` (contrôle autonome
  du noyau N-corps contre JPL Horizons 1650–2450 via `essais/nbody_ref.h`, sans `de440.bsp`) et `essai_robustesse`
  (entrées hostiles ou limites sur des fichiers de synthèse : dates non finies, dossiers, noms d'images qui sortent du
  dossier, tailles démesurées, coordonnées non finies, bornes à 1 ULP). Les modes complets avec
  données restent disponibles : `essai_systeme_solaire <de440.bsp> [orbites_planetes.bin]` et
  `essai_fusion <fusion_centres.bin> <dossier_images>`.

- **Build portable complet depuis `natif/`** (sur Linux/macOS, les cibles Win32/Vulkan sont gardées par `if(WIN32)`) :
  ```bash
  cmake -S natif -B /tmp/univers-natif-build -DCMAKE_BUILD_TYPE=Release
  cmake --build /tmp/univers-natif-build
  ctest --test-dir /tmp/univers-natif-build --output-on-failure
  ```
  Construit les 8 essais portables (`essai_cosmologie`, `essai_interface`, `essai_ephem`, `essai_orientation`,
  `physique/essai_galaxie`, `physique/essai_fusion`, `physique/essai_systeme_solaire`, `physique/essai_robustesse`) et
  lance les 5 suites autonomes sans fichiers externes (`essai_cosmologie`, `essai_interface`, `essai_galaxie`,
  `essai_systeme_solaire_noyau`, `essai_robustesse`).

## Outils Windows (sans droits d'administrateur)

Dossier `C:\dev\outils-natif`, archives officielles décompressées, rien d'installé dans Windows :

| Outil | Source | Rôle |
|---|---|---|
| llvm-mingw 20261104 (ucrt, x86_64) | github.com/mstorsjo/llvm-mingw | compilateur C++20 (clang 23) |
| CMake 4.4.5 | github.com/Kitware/CMake | recette de fabrication |
| Ninja 1.13.2 | github.com/ninja-build/ninja | exécution de la recette |
| glslang (main-tot) | github.com/KhronosGroup/glslang | shaders GLSL vers SPIR-V |

Sous Windows (`WIN32`), CMake récupère les dépendances épinglées via `FetchContent` (`Vulkan-Headers` `v1.4.309`,
`volk` `1.4.304`, `imgui` `v1.91.9b`, `stb` commit `6b5799bae8a1fe3792691ef4b72ae26434c3e799`) et compile les cibles
Vulkan (`essai_vulkan`, `univers`, `UniversPC`). `vulkan-1.dll` vient du pilote graphique déjà installé.

## Essai N0

`src/essai_vulkan.cpp` : dessine un triangle hors écran (aucune fenêtre), relit l'image, vérifie deux pixels et
affiche ce que la carte sait faire (rendu dynamique, mesh shaders, double précision).

Fabriquer et lancer (Git Bash, Windows) :

```bash
T=/c/dev/outils-natif; export PATH="$T/llvm-mingw-20261104-ucrt-x86_64/bin:$T/cmake-4.4.5-windows-x86_64/bin:$T:$T/glslang/bin:$PATH"
cmake -S natif -B /c/tmp/natif/build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
cmake --build /c/tmp/natif/build && /c/tmp/natif/build/essai_vulkan.exe
```

Résultat du 12 novembre 2026 sur le PC de Marc (accord de Marc pour lancer ces outils) `[Certain]` : PASSE.
RTX 5080, Vulkan 1.4.357 ; rendu dynamique, ressources sans liaison fixe, dessin indirect compté, mesh shaders et
double précision dans les shaders : tous disponibles. Pixel du centre 255 127 0, pixel du coin 0 0 51.

## Appli « Univers » (jalon N1)

- `src/fichier_mappe.h` : projection mémoire en lecture seule portable (Win32 / POSIX), RAII (`univers::MappedFile`).
- `src/commun.h` : fichier d'étoiles projeté en mémoire, couleur, caméra, Vulkan, dessin des étoiles (`namespace univers`).
- `src/univers.cpp` : image hors écran et contrôles (`--verifie`, `--images`), aiguillage vers la fenêtre.
- `src/fenetre.cpp` : fenêtre interactive. Cliquer sur un astre pour y voler ; glisser la souris ou utiliser les
  flèches pour orbiter autour de l'astre suivi ; molette ou `+` / `−` pour zoomer ; touches `1` à `5` pour les
  échelles ; `Espace` pour lecture/pause ; `Origine` pour revenir au Soleil ; `Retour arrière` pour la vue
  précédente ; `F1` pour l'aide ; `Échap` pour fermer la recherche/menu ou quitter. Le titre donne la cadence en images
  par seconde.
- `installer.ps1` : range le programme, ses shaders et `etoiles.bin` dans `C:\dev\Univers-PC` et pose le raccourci
  « Univers PC » sur le Bureau.

Contrôles (PC seulement, aucune fenêtre visible) :

```bash
univers.exe etoiles.bin image.ppm --regarde <i> --verifie <i,j,k> --images 200   # image hors écran, éclat et place de chaque étoile
univers.exe etoiles.bin --fenetre-test 300                                      # chemin complet de la fenêtre, fenêtre cachée
```

Résultats du 12 novembre 2026 `[Certain]` : 523 images par seconde hors écran en 1920 × 1080 et 514 par la fenêtre
cachée en 1600 × 900, pour 6 153 611 étoiles (la carte calculait la fusion en même temps) ; cinq étoiles à leur
place, éclat à 1 % près. **Pas vérifié : la fenêtre réellement affichée à l'écran** (aucune fenêtre n'est ouverte
par Claude sur le PC) : c'est Marc qui la voit en premier.

## Interface et prise en main (`src/interface.h`, `src/interface_outils.h`)

- Premier lancement : un mot d'accueil propose une **visite guidée** (9 étapes, de la Terre à l'univers lointain,
  environ une minute et demie) ou d'explorer seul. Un clic, la molette ou un glisser sur l'image arrête la visite.
- **Cliquer sur un astre** (son point ou son nom) y fait voler la caméra en 1,8 s : recul, glissement, approche
  (`Sim::flyTo`). Encore un clic sur l'astre suivi : on s'en approche. **Retour arrière** refait le chemin inverse
  (position, distance et orientation de la caméra).
- **Taper un nom** n'importe quand ouvre la recherche (sans tenir compte des accents ni des ligatures `œ`/`æ`) ;
  flèches et Entrée choisissent.
- **Aller à…** : échelles (touches 1 à 5), système solaire et lunes visibles à la date courante, étoiles et galaxies
  nommées avec leur distance.
- Temps : lecture/pause, sens, plus lent / plus rapide (aussi Page suiv. / Page préc.), « Maintenant », « Date… »
  (« 1969 », « 21/07/1969 », « -3000 », « 5000000000 » si la fusion est chargée).
- F1 ou « ? » : toutes les commandes. L'interface grandit avec la fenêtre (police chargée pour l'écran du PC).
- Contrôles sans fenêtre : `UNIVERS_ECRAN=accueil|aide|menu|recherche:<texte>|visite:<étape>|vol:<nom>:<0 à 1>`
  avec `--fenetre-test 20 --capture f.ppm`. `essai_interface` vérifie la recherche et la lecture des dates.

## Parité physique Web (`app/src/`) ↔ Natif (`natif/`)

État comparé des modèles scientifiques entre la page web et l'application native `[Certain]` :

- **Système solaire N-corps** (`app/src/21_nbody.js` ↔ `natif/physique/nbody_noyau.h`) `[Certain]` : même intégrateur
  symplectique Wisdom–Holman à 13 corps (relativité générale 1PN + anneau Terre–Lune) et mêmes constantes ;
  `LongTable::position` n'inclut pas le repli `keplerHigh` ($e > 0{,}3$), sans effet pour les planètes et Pluton.
- **Orbites galactiques** (`app/src/26_orbits.js` ↔ `natif/physique/galaxie_orbites.h`) `[Certain]` : même potentiel
  Voie lactée (Hernquist + Miyamoto–Nagai + NFW) et barre tournante de Dehnen 2000 (écart mesuré
  $6{,}2 \times 10^{-10}\text{ kpc}$ sur le Soleil à $+200\text{ Ma}$) ; seule `soleilPos()` est actuellement branchée
  dans `simulation.h`.
- **Cosmologie** (`app/src/20_physics.js` + `app/src/29_cone.js` ↔ `natif/src/cosmologie.h`) `[Certain]` : le C++ gère
  l'énergie noire variable $w(a) = w_0 + w_a(1 - a)$ et la courbure $\sinh/\sin$ via $da/dt$ (sans rebond/Big Crunch,
  ni facteur de croissance $D(t)$, ni cône de lumière) ; la page web intègre $\ddot{a}/a$ à $w$ constant.
- **Temps civil → TDB** `[Certain]` : la page web applique la parabole de Morrison–Stephenson (`deltaT(T)`), tandis
  que l'appli PC applique un décalage constant de $69{,}184\text{ s}$ (partagé de manière cohérente via `jdTdb()` /
  `daysTdb()`).
- **Couleur des étoiles** `[Certain]` : tables CIE 1931 au pas de 1 nm (`pipeline/build_bbcol.py`) sur le web contre
  ajustement analytique Wyman et al. 2013 (`natif/src/commun.h`) sur PC.
- **Taille d'affichage des astéroïdes** `[Certain]` : `natif/shaders/asteroides.vert` (`2.1 - (H - 11) * 0.28`) diffère
  de `app/src/20_physics.js` (`2.6 - 0.16 * (H - 4)`).
