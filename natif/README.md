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
