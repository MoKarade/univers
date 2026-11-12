# Appli PC « Univers »

Plan et jalons : `docs/plan-natif.md`.

## Outils (sans droits d'administrateur)

Dossier `C:\dev\outils-natif`, archives officielles décompressées, rien d'installé dans Windows :

| Outil | Source | Rôle |
|---|---|---|
| llvm-mingw 20261104 (ucrt, x86_64) | github.com/mstorsjo/llvm-mingw | compilateur C++20 (clang 23) |
| CMake 4.4.5 | github.com/Kitware/CMake | recette de fabrication |
| Ninja 1.13.2 | github.com/ninja-build/ninja | exécution de la recette |
| glslang (main-tot) | github.com/KhronosGroup/glslang | shaders GLSL vers SPIR-V |

Les en-têtes Vulkan (Khronos) et volk sont récupérés par CMake à la première fabrication. `vulkan-1.dll` vient du
pilote NVIDIA déjà installé.

## Essai N0

`src/essai_vulkan.cpp` : dessine un triangle hors écran (aucune fenêtre), relit l'image, vérifie deux pixels et
affiche ce que la carte sait faire (rendu dynamique, mesh shaders, double précision).

Fabriquer et lancer (Git Bash) :

```bash
T=/c/dev/outils-natif; export PATH="$T/llvm-mingw-20261104-ucrt-x86_64/bin:$T/cmake-4.4.5-windows-x86_64/bin:$T:$T/glslang/bin:$PATH"
cmake -S natif -B /c/tmp/natif/build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
cmake --build /c/tmp/natif/build && /c/tmp/natif/build/essai_vulkan.exe
```

Résultat du 12 novembre 2026 sur le PC de Marc (accord de Marc pour lancer ces outils) [Certain] : PASSE.
RTX 5080, Vulkan 1.4.357 ; rendu dynamique, ressources sans liaison fixe, dessin indirect compté, mesh shaders et
double précision dans les shaders : tous disponibles. Pixel du centre 255 127 0, pixel du coin 0 0 51.

## Appli « Univers » (jalon N1)

- `src/commun.h` : fichier d'étoiles projeté en mémoire, couleur, caméra, Vulkan, dessin des étoiles.
- `src/univers.cpp` : image hors écran et contrôles (`--verifie`, `--images`), aiguillage vers la fenêtre.
- `src/fenetre.cpp` : fenêtre interactive. Glisser la souris pour tourner la tête ; W A S D ou les flèches pour
  se déplacer ; E / Q pour monter et descendre ; molette pour la vitesse ; Origine pour revenir au Soleil ;
  Échap pour quitter. Le titre donne la cadence, la distance au Soleil et la vitesse.
- `installer.ps1` : range le programme, ses shaders et `etoiles.bin` dans `C:\dev\Univers-PC` et pose le raccourci
  « Univers PC » sur le Bureau.

Contrôles (PC seulement, aucune fenêtre visible) :

```bash
univers.exe etoiles.bin image.ppm --regarde <i> --verifie <i,j,k> --images 200   # image hors écran, éclat et place de chaque étoile
univers.exe etoiles.bin --fenetre-test 300                                      # chemin complet de la fenêtre, fenêtre cachée
```

Résultats du 12 novembre 2026 [Certain] : 523 images par seconde hors écran en 1920 × 1080 et 514 par la fenêtre
cachée en 1600 × 900, pour 6 153 611 étoiles (la carte calculait la fusion en même temps) ; cinq étoiles à leur
place, éclat à 1 % près. **Pas vérifié : la fenêtre réellement affichée à l'écran** (aucune fenêtre n'est ouverte
par Claude sur le PC) : c'est Marc qui la voit en premier.

## Interface et prise en main (`src/interface.h`, `src/interface_outils.h`)

- Premier lancement : un mot d'accueil propose une **visite guidée** (9 étapes, de la Terre à l'univers lointain,
  environ une minute et demie) ou d'explorer seul. Un clic, la molette ou un glisser sur l'image arrête la visite.
- **Cliquer sur un astre** (son point ou son nom) y fait voler la caméra en 1,8 s : recul, glissement, approche
  (`Sim::flyTo`). Encore un clic sur l'astre suivi : on s'en approche. **Retour arrière** refait le chemin inverse.
- **Taper un nom** n'importe quand ouvre la recherche (sans tenir compte des accents) ; flèches et Entrée choisissent.
- **Aller à…** : échelles (touches 1 à 5), système solaire et lunes, étoiles et galaxies nommées avec leur distance.
- Temps : lecture/pause, sens, plus lent / plus rapide (aussi Page suiv. / Page préc.), « Maintenant », « Date… »
  (« 1969 », « 21/07/1969 », « -3000 »).
- F1 ou « ? » : toutes les commandes. L'interface grandit avec la fenêtre (police chargée pour l'écran du PC).
- Contrôles sans fenêtre : `UNIVERS_ECRAN=accueil|aide|menu|recherche:<texte>|visite:<étape>|vol:<nom>:<0 à 1>`
  avec `--fenetre-test 20 --capture f.ppm`. `essai_interface.exe` vérifie la recherche et la lecture des dates.
