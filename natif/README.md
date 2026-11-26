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

## Validation Vulkan : obligatoire pour tout essai de nouveau code carte (26 novembre 2026)

Le 26/11/2026 à 6 h 00, un contrôle de fin d'essai (`--controle-film`, PR 151) a relu un tampon de la carte déjà libéré.
La carte a fait une faute mémoire (nvlddmkm ID 13, « MMU Fault »), et le pilote est resté bloqué jusqu'au redémarrage,
8 heures plus tard. La couche de validation de Khronos signale ce genre d'erreur avant que la carte ne la subisse. [Probable]

- `univers <etoiles.bin> --fenetre-test n ... --validation` : couche `VK_LAYER_KHRONOS_validation` allumée. Chaque
  message va dans la console et dans `univers-validation.log` à côté du programme. À la sortie, le bilan
  « validation Vulkan : N erreur(s) ... -> PASSE/ECHEC » s'affiche, et le code de sortie vaut 3 s'il y a eu une erreur.
- `--validation-gpu` : en plus, la carte contrôle les bornes de chaque accès des shaders (validation assistée par la carte).
  C'est bien plus lent : à réserver aux essais courts d'un shader nouveau ou modifié.
- Autres programmes (essais, précalculs) : variable `UNIVERS_VALIDATION=1` (ou `gpu`).
- Sans la couche, l'essai échoue tout de suite. Il n'y a jamais d'essai « validé » sans elle. Elle vient du SDK Vulkan de
  LunarG. Hors installation, on peut aussi pointer `VK_ADD_LAYER_PATH` vers le dossier `Bin` qui contient
  `VkLayer_khronos_validation.json`.
- Règle : un essai de code qui touche la carte (shader, tampon, libération, relecture) passe d'abord une fois en
  `--validation`, et en `--validation-gpu` si un shader change. Il est fait seul sur la carte.
- Les contrôles qui relisent la carte (`readBack`) se font AVANT toute libération (`release`).

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
- Contrôles sans fenêtre : `UNIVERS_ECRAN=accueil|aide|menu|completude|eclipse[:<rang>]|voyager|recherche:<texte>|visite:<étape>|vol:<nom>:<0 à 1>`
  avec `--fenetre-test 20 --capture f.ppm`. `essai_interface.exe` vérifie la recherche et la lecture des dates.

## Bac à sable : panneau, frise, réglages, orbites (18 novembre 2026)

Demande de Marc : interface retravaillée, informative (images, explications, courbes, analyses), frise du temps de
l'univers, paramètres modifiables, orbite de n'importe quel objet.

- `src/interface_panneau.h` : panneau à droite, trois onglets. **Astre** : carte de surface (textures déjà installées,
  Solar System Scope CC BY 4.0, `src/interface_images.h`), explication sourcée (`src/interface_savoir.h`), courbe de
  l'orbite et analyse (durée d'un tour, rayons extrêmes, prochain passage), valeurs de l'ancienne fiche. **Univers** :
  époque choisie sur la frise, taille de l'univers dans le temps (tes réglages contre Planck 2018), composition, destin
  (expansion sans fin, Grande Déchirure ou retombée), tout « calculé ». **Réglages** : vitesse d'expansion, matière,
  énergie noire (w0, wa), essais rapides ; matière noire et barre de la Voie lactée, énergie noire dans la galaxie.
  Fermé (×), il laisse une colonne de trois boutons.
- `src/interface_frise.h` : frise en bas. À gauche, toute l'histoire en échelle logarithmique, colorée par la
  température du rayonnement (calculée) ; un clic l'explique. À droite, le temps simulé (−1 Ga à la fin du film),
  logarithmique des deux côtés d'aujourd'hui ; clic ou glisser pose la date (`sim.years`, bornée par
  `minYears`/`maxYears`).
- `src/orbites_objet.h` : orbite de l'astre suivi. Étoiles et Soleil : même modèle et même départ que `Sim::exact`,
  ±250 Ma ; variante « et si… » (pointillé bleu) avec les réglages. Galaxies du Groupe local : film puis centres de
  référence (même règle que `refreshGalaxies`). Sondes : trajectoire JPL. Astéroïdes : orbite JPL.
- `physique/galaxie_orbites.h` : `Potentiel::lambda` (énergie noire locale), valeur par défaut inchangée.
- `src/interface_cosmo_courbes.h` : histoire de l'expansion. Contrôle `essai_bac_a_sable` : âge identique à
  `cosmo::ageGyr` ; univers fermé (Ωm = 2) contre la solution exacte, 0,04 % ; Grande Déchirure (w = −1,5) contre la
  formule approchée de Caldwell 2003, 3 % ; 1/a = 1076 à 380 000 ans (Planck : z* = 1090).
- Contrôle sans fenêtre : `UNIVERS_PANNEAU=astre | univers[:<époque>] | reglages | ferme`, suivi au besoin de
  `,halo:<x>`, `,w0:<x>`, `,ode:<x>`, `,om:<x>`.
- `src/groupe_local_scenario.h` (19/11/2026) : la rencontre du Groupe local rejouée en direct avec les réglages
  (énergie noire, matière noire des halos) : même physique que `pipeline/fusion/groupe_local_reference.py`, départ
  d'aujourd'hui lu dans `centres_reference.bin`, 10 Ga en quelques dizaines de ms. Contrôle : rejouée avec les valeurs
  mesurées, elle retombe sur la référence (passage d'Andromède 5,543 Ga et 29,8 kpc, fusion 6,902 Ga, écart de position
  0,006 kpc sur 0 à 5 Ga). Montrée : date de fusion et chemin « et si… » de la galaxie suivie.
- Ne change pas : les formes des galaxies pendant la rencontre (film calculé à l'avance) et le mouvement des millions
  d'étoiles affichées. Le panneau le dit.
- Pas vérifié : la fenêtre réellement affichée (captures en fenêtre cachée seulement), la souris sur la frise.

## Grandes structures et nuage d'Oort (19 novembre 2026)

Demande de Marc : il manquait le nuage d'Oort, Laniakea avec le Grand Attracteur et les vides cosmiques.

- `pipeline/natif/structures.py` écrit `structures.bin` (44 Mo) et `structures_noms.tsv` (données dans
  `%LOCALAPPDATA%\univers-raw`, installées par `installer.ps1`). Sources : bassins d'attraction de Dupuy et Courtois 2023
  et champ de vitesses Cosmicflows-4 (frontière de Laniakea, 9 297 lignes de courant vers les six attracteurs) ; vides du
  voisinage de Malandrino et al. 2026 (100, forme publiée, dont le Vide local, < 200 Mpc/h) ; vides SDSS DR7 de Douglass
  et al. 2023 (VoidFinder, 200 à 330 Mpc/h) ; vides BOSS DR12 de Mao et al. 2017 (z = 0,2 à 0,7, sphère de même volume).
  On généralise en s'éloignant : forme publiée près, union de sphères plus loin, sphère au plus loin.
- Ordre des axes des grilles 64³ de Cosmicflows-4 (densité, vitesses) établi sur les données : (SGX, SGY, SGZ), à
  l'inverse des grilles 128³ des bassins. Unité des vitesses déduite de la relation linéaire (57,7 km/s par unité) et
  vérifiée sur le mouvement mesuré du Groupe local (610 contre 627 km/s, même direction à 20° près) [Probable].
- `src/structures.h` dessine les trois couches en repères additifs (pas de la lumière ; l'interface le dit) :
  surfaces vues en voile (plus vives de biais), flot en tirets qui avancent dans le sens de la chute, nuage d'Oort.
  Montrées à partir de ~20 millions d'al regardés (structures) et entre ~1 000 UA et ~30 al du Soleil (Oort) ; ce qui
  est bien plus loin que l'échelle regardée s'estompe. Menu : deux cases pour les cacher.
- Nuage d'Oort : MODÈLE (aucune comète vue sur place) : un million de comètes, densité en r^-3,5 de 3 000 à 100 000 UA
  (Duncan, Quinn et Tremaine 1987), extérieur isotrope, intérieur aplati [supposé], chacune sur son orbite képlérienne
  calculée à la date montrée (`shaders/oort.vert`). Ignorés : marée galactique, étoiles qui passent.
- Contrôle `essai_structures` (dans `controle.sh`) : surfaces fermées ; volume de Laniakea retrouvé (1,945 million de
  (Mpc/h)³) ; 3 lignes sur 4 du flot de Laniakea au même puits (les autres s'arrêtent sur des cols) ; Vide local à
  38,8 Mpc/h ; modèle d'Oort : pente -3,36 mesurée sur 200 000 tirages, extérieur isotrope, intérieur aplati.
- Pas vérifié : la fenêtre réellement affichée (captures en fenêtre cachée seulement), la cadence avec Gaia chargé.

## Interface refondue (20 novembre 2026)

Demande de Marc : l'interface n'était « pas du tout user friendly, pas du tout belle ».

- `src/interface_theme.h` : toute l'apparence au même endroit (couleurs, polices Segoe UI et Segoe UI Semibold, icônes
  Segoe Fluent Icons de Windows, petits éléments). Couleur du statut d'une valeur, la même partout : mesuré ou publié
  vert, calculé bleu, modèle violet, supposé orange.
- `row(libellé, valeur, statut)` (fiche) : le premier mot du statut devient une pastille de couleur, le reste (source,
  méthode) est écrit en petit sous la valeur. Aucun texte retiré. Le fil « fiche complète » s'en sert tel quel.
- En haut à gauche : barre d'outils (recherche avec raccourcis et résultats illustrés, retour, aller à, afficher,
  lumière, exposition, visite guidée, aide). En haut au milieu : « tu regardes ». En haut à droite : sélecteur
  « 100 % mesuré | Meilleur rendu » (F4), ses hypothèses, puis la complétude.
- En bas, au-dessus de la frise : le temps comme un lecteur vidéo (reculer, lecture, avancer, date, maintenant, date
  au choix, bouton « i » pour ce qui est mesuré, calculé ou supposé à cette date ; vitesse en curseur libre).
- À gauche : échelle de zoom à cinq crans (`src/interface_echelle.h`), le repère ambre montre où est la vue.
- Astre suivi : repère en quatre coins ; survol : anneau et bulle (nom, nature, distance).
- Contrôle : `essai_interface` vérifie aussi la lecture du statut et la position sur l'échelle.
- Pas vérifié : la fenêtre réellement affichée et la souris (captures en fenêtre cachée seulement).
