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
