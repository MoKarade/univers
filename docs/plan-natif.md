# Plan « appli PC en plus de la page » (12 novembre 2026)

Demande de Marc : un cahier des charges d'appli native (C++20, Vulkan, CUDA, AVX-512). Cadrage et critique :
https://claude.ai/artifact/TKi5ysK8kYomGNXqmxC3x3. Confiance : [Certain] vérifié ; [Probable] ; [À vérifier].

## Décisions de Marc (12 novembre 2026)

| N° | Question | Réponse |
|---|---|---|
| 1 | La page sur téléphone reste-t-elle le produit principal ? | **Les deux** : la page reste, une appli PC s'ajoute |
| 2 | Ce qui manque le plus | **Tout** : plus beau et plus vrai, plus d'objets et plus fluide, réglages recalculés en direct |
| 3 | Fusion avec Andromède | **Rejouée**, calculée à l'avance sur la carte graphique du PC, plus fine |
| 4 | Énergie noire réglable dans la page | **Oui** |
| 5 | Installer environ 20 Go d'outils gratuits sur le PC | **Oui** |

## Matériel et outils du PC (lus le 12 novembre 2026) [Certain]

- Ryzen 9 9950X3D (16 cœurs), 62 Go, NVIDIA RTX 5080 16 Go (pilote 621.14, Vulkan 1.4), 484 Go libres.
- Absents : compilateur Microsoft, outils CUDA, outils Vulkan, CMake. Leur installation classique demande des droits
  d'administrateur (geste de Marc). À essayer d'abord sans administrateur (voir N0).
- Les calculs sur la carte graphique ne demandent **aucune installation en administrateur** : environnement Python
  `%LOCALAPPDATA%\univers-gpu-venv` (pip `cupy-cuda12x[ctk]`), noyaux CUDA compilés à la volée.

## Règles propres à ce lot

- La page reste la référence : tout calcul fait pour l'appli sort dans un format que la page sait rejouer.
- Un calcul long sur le PC n'ouvre aucune fenêtre et cède la carte graphique dès qu'un autre programme (un jeu)
  l'occupe (`Carte.attendre` dans `pipeline/fusion/calcul.py`).
- Les contrôles qui ont besoin de la carte graphique ne tournent que sur le PC : ils sont dits tels quels, jamais
  comptés comme contrôles automatiques du dépôt.
- Écartés du cahier des charges, avec la raison (détail dans le cadrage) : positions « 128 bits » (imprécises à
  3 000 km), relativité 2PN, AVX-512 pour quinze corps, freinage de Chandrasekhar ajouté à un calcul où toutes les
  particules s'attirent (double compte), partage mémoire CUDA-Vulkan (la fusion est rejouée), interface Dear ImGui
  telle quelle, extraction depuis le fichier HTML (on part de `app/gen` et `pipeline`).

## Jalons

### Côté calcul et page (profitent au téléphone)

| Jalon | Après | Fini quand |
|---|---|---|
| A1. Fusion sur la carte graphique | Rencontre avec Andromède à environ 3 millions de particules (300 000 aujourd'hui), mêmes modèles, mêmes fichiers pour la page | Arbre contre somme directe : erreur médiane < 0,4 % ; dérive d'énergie < 1 % sur 10 Ga ; date de fusion comparée au calcul à 300 000 ; la page rejoue sans changement de code ; fluidité mesurée sur l'Android de Marc |
| A2. Atmosphères (Bruneton) | Ciel de la Terre, Mars, Vénus, Titan vus de près | Couleur du ciel terrestre comparée à une mesure publiée ; « inconnu » là où rien n'est mesuré ; fluide sur téléphone |
| A3. Énergie noire réglable (w0, wa), courbure, rayonnement | Deux curseurs de plus dans Cosmologie | < 0,5 % d'écart avec astropy pour 5 réglages, dont DESI |
| A4. Trou noir en rotation, avec disque | Sagittarius A* et M87* avec leur anneau | Ombre conforme aux formules publiées pour 3 rotations ; rotation marquée « supposée » |
| A5. Planètes contre DE441 | Rien de visible, écart affiché | Écart mesuré sur 30 000 ans, dit dans « Ce qui est vrai ici » |

### Côté appli PC

| Jalon | Après | Fini quand |
|---|---|---|
| N0. Outils | De quoi fabriquer une appli Windows | Un programme d'essai se compile et affiche un triangle par Vulkan, sans geste de Marc si possible ; sinon un seul geste, écrit dans `docs/gestes-marc.md` |
| N1. Les étoiles | Une fenêtre avec les 6,15 millions d'étoiles de la page, à leur place, caméra libre | Mêmes positions que la page pour 20 étoiles nommées ; images par seconde mesurées ; **durée réelle du jalon mesurée**, elle sert à estimer la suite |
| N2. Données communes | Fichiers binaires partagés entre page et appli, écrits par `pipeline/` | Un seul script produit les deux ; contrôle octet pour octet |
| N3 et suite | Galaxies, système solaire (calcul existant porté), temps, fiches, recherche | À détailler après la mesure de N1 |

Ordre : A1, N0, N1, puis A2 à A5 et N2 en alternance selon les mesures.

## A1 : état

- `pipeline/fusion/gravite_gpu.py` : arbre de Barnes-Hut binaire (Karras 2012), quadripôles, critère d'ouverture de
  Barnes 1994, adoucissement de Plummer par particule. `pipeline/fusion/test_gravite_gpu.py` (PC seulement).
- Mesuré sur la RTX 5080, contre la somme directe (4 000 particules tirées au hasard) [Certain] :

| Particules | theta | Quadripôles | Erreur médiane | 99ᵉ centile | Temps par calcul |
|---|---|---|---|---|---|
| 200 000 | 0,5 | non | 0,235 % | 0,94 % | 0,027 s |
| 200 000 | 0,5 | oui | 0,039 % | 0,23 % | 0,033 s |
| 200 000 | 0,7 | oui | 0,120 % | 0,46 % | 0,017 s |
| 3 000 000 | 0,5 | oui | 0,028 % | 0,20 % | 0,63 s |
| 3 000 000 | 0,7 | oui | 0,096 % | 0,40 % | 0,24 s |

- Retenu : theta 0,7 avec quadripôles. 40 000 pas de 0,25 Ma à 0,24 s : environ 2,7 heures pour 10 Ga
  [Probable : mesuré sur un tirage d'essai, pas sur les galaxies ; à confirmer par le calcul].
- `calcul.py --gpu` : même sortie que le calcul d'origine (`fusion.json`, `kf_NNN.bin`), instantané à chaque paquet
  d'images, `reprise` après un arrêt. Essai de reprise sur un état réel à 6 000 particules : 4,0 → 5,0 Ga en 6 s,
  centres à 80,5 kpc contre 80,0 pour falcON [Certain].
- Différence connue avec falcON : le noyau d'adoucissement n'est pas le même. L'énergie n'est donc comparable qu'à
  l'intérieur d'un même calcul.
- Conditions de départ : AGAMA ne s'installe pas sur le PC sans compilateur ; elles sont tirées par la tâche GitHub
  « Fusion - conditions de départ » (`calcul.py depart N`), puis téléchargées dans `pipeline/fusion/sortie/`.
- À surveiller (note du fil gravité) : le traceur du Soleil migre vers le centre à cause d'une barre du disque
  modèle ; la page ne prend pas le Soleil du calcul.

## N0 : fait (12 novembre 2026)

Outils portables dans `C:\dev\outils-natif`, aucun droit d'administrateur, aucun geste de Marc (`natif/README.md`).
`natif/src/essai_vulkan.cpp` fabriqué et lancé : PASSE, sans fenêtre. La carte offre tout ce que le cahier des
charges demande à Vulkan [Certain : lu par le programme].

## N1 : état (12 novembre 2026)

- `pipeline/natif/etoiles.py` : les 6 153 611 étoiles de la page (58 967 + 200 000 + 5 894 644 en flux) dans
  `etoiles.bin`, colonnes alignées sur 64 octets, 196,9 Mo. Les fichiers en flux sont ceux publiés avec la page.
  `pipeline/natif/test_etoiles.py` : Sirius, Véga, Rigel, Bételgeuse, Arcturus à moins de 0,002° de leurs
  coordonnées Hipparcos ; 33 distances conformes à la page [Certain].
- `natif/src/univers.cpp` : fichier projeté en mémoire, cinq colonnes envoyées telles quelles à la carte, points
  additionnés en grande dynamique, image hors écran. Vue du Soleil vers Orion, 1920 × 1080 :
  **524 images par seconde** pour les 6,15 millions d'étoiles (mesuré pendant que la carte calculait aussi la
  fusion) ; lumière mesurée dans l'image à 1 % de la valeur attendue pour 5 étoiles ; constellation reconnue à
  l'œil sur la capture [Certain].
- Couleur : Planck + observateur CIE par l'ajustement de Wyman et al. 2013, température par Ballesteros 2012.
  [À faire : reprendre les tables CIE de la page (S1) pour une couleur identique.]
- Pas fait : la fenêtre et la caméra libre, le mouvement propre (vitesses déjà dans le fichier), la poussière,
  les étoiles frôleuses éteintes en double (`isPasser`).
- Durée mesurée : N0 et N1 hors écran, de la décision de Marc à ce point, environ 30 minutes de travail (14 h 10 à 14 h 37 UTC).

## Décision de Marc, 12 novembre 2026, 15 h 06 UTC : tout réécrire en natif (chemin 2)

Marc a rejeté la fenêtre d'étoiles (« je veux un vrai simulateur comme la version en ligne mais beaucoup plus
précis ») puis choisi, entre « le simulateur de la page dans une fenêtre PC d'abord » (recommandé) et « tout réécrire
pour le PC », le second. Dit à Marc : environ dix fois le travail du 12 novembre avant d'égaler la page (600 ko de
code dans la page, 60 ko écrits ce jour-là), durée inconnue. La page en ligne continue de vivre à côté.

Étapes, chacune visible dans « Univers PC » (elles remplacent N2 et N3) :

| Étape | Ce que Marc voit | Reprend de la page |
|---|---|---|
| E1. Socle | Zoom continu du Soleil aux étoiles autour de l'objet choisi, temps qui défile (pause, vitesses, date), recherche, fiche de l'objet, noms à l'écran, étoiles qui se déplacent | `60_app.js` (navigation, temps, fiches), mouvements propres |
| E2. Système solaire | Soleil, planètes et Lune à leur place à toute date, orbites, surfaces, lunes | `20_physics.js`, `21_nbody.js`, `gen/ephem.js`, textures |
| E3. Petits corps et sondes | 123 530 astéroïdes, comètes, 5 sondes et leurs survols | `22_smallbody.js`, tuiles `a1`, `data10.js` |
| E4. Galaxies | 5,57 millions de galaxies et quasars, Groupe local, photos, Voie lactée | tuiles `g1` à `g3`, `data3/4/14.js` |
| E5. Temps profond | Orbites des étoiles dans la Galaxie, vie du Soleil, avenir lointain | `25_future.js`, `26_orbits.js` |
| E6. Fusion avec Andromède | Le calcul à 3 millions de particules, toutes affichées | A1 (en cours), `fusion.json` |
| E7. Cosmologie | Expansion, énergie noire réglable recalculée en direct, cône de lumière, fond diffus | `20_physics.js`, `29_cone.js`, `data19.js` |
| E8. Trous noirs et poussière | Lumière déviée (avec rotation), poussière mesurée en 3D | `27_lens.js`, `28_dust.js` |
| E9. Infiniment petit | Du mètre au proton | `initMicro`, `water_qm.js`, `proton_pdf.js` |
| E10. Frise et événements | Les 190 événements, éclipses, passages | `EV_RAW`, `23_events.js` |

Règles : chaque calcul porté de la page garde ses contrôles (mêmes références NASA et JPL que `app/test`). Interface :
Dear ImGui (demandé par le cahier des charges), habillée aux couleurs de la page, tout expliqué à l'écran (Marc ne
lit pas les commandes dans le chat ; la molette est un zoom). Contrôle sans fenêtre visible : l'appli rend son image
finale, interface comprise, dans un fichier (`--fenetre-test`), relu à l'œil et par des mesures.
