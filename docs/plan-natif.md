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

## E1 et E2 : état (12 novembre 2026, 15 h 30 UTC)

- E1 fait : `natif/src/simulation.h` (temps, astres, caméra), `interface.h` (Dear ImGui v1.91.9b : recherche, date
  et vitesses, fiche avec « mesuré / calculé », noms cliquables, aide), `fenetre.cpp`, `rendu_fenetre.h`. Étoiles en
  mouvement rectiligne à leur vitesse mesurée (limite ± 3 millions d'années, dite à l'écran).
  Contrôle : Alpha du Centaure au plus près vers l'an 29 000 à 2,87 années-lumière (publié : environ 3).
  Erreur trouvée et corrigée grâce à ce contrôle : les vitesses du catalogue principal sont en repère galactique.
- E2, première partie : `natif/src/ephemeride.h` lit directement le fichier DE440 de la NASA (114 Mo, 1550 à 2650).
  `essai_ephem` contre JPL Horizons (`app/test/nbody_ref.json`, 112 valeurs de 1650 à aujourd'hui) [Certain] :
  planètes et Soleil à mieux que 1 mm, Terre 3,5 m, Lune 282 m (écart entre DE440 et DE441 dans le passé).
  À comparer aux 0,3 à 2,5 secondes d'arc de la page (des centaines à des milliers de km).
  Dans l'appli : Soleil, 8 planètes, Pluton, Lune, orbites tracées d'après les éphémérides, fiches, suivi.
  Hors de 1550-2650 : planètes masquées, « position inconnue pour l'instant », dit à l'écran.
- E2, reste à faire : les surfaces (sphères avec les cartes de la page), les lunes des autres planètes, le calcul
  des positions hors de 1550-2650 (port de `21_nbody.js`), les éclipses.
- Approximations dites dans le code : phase de Lambert pour l'éclat des planètes ; TDB − UTC fixé à 69,184 s ;
  magnitudes H, couleurs et rayons recopiés de mémoire [Probable], à relire contre les sources.
- Contrôle visuel sans fenêtre : `univers.exe etoiles.bin --fenetre-test 60 --capture f.ppm --cible Terre --distance 1e-7`.

## E2 : surfaces (12 novembre 2026, 15 h 50 UTC)

- `natif/src/orientation.h` : axe et méridien d'origine de chaque astre (modèle UAI). `essai_orientation` avec DE440
  [Certain] : Terre, 12 novembre 2026 à 12 h TU, Soleil au zénith à −17,77° de latitude et −3,87° de longitude
  (attendu −17,8° et −3,95°) ; équinoxe du 20 mars 2026 : latitude 0,002° ; Lune : le point tourné vers la Terre
  reste à moins de 7,4° et 5,2° du centre de la face visible sur 60 dates. Les autres astres : non contrôlés.
- `natif/src/spheres.h`, `shaders/sphere.frag` : sphère exacte par pixel (pas de maillage), carte de surface,
  éclairage par le Soleil (surface mate), bord adouci, Soleil avec assombrissement du bord. Cartes Solar System
  Scope (CC BY 4.0) en 8192 × 4096, décodées dans un fil à part ; installées dans `C:\dev\Univers-PC\textures`.
- Dit dans le code : l'exposition des surfaces est un réglage d'affichage (en vraie lumière l'image serait blanche).
- Reste : anneaux de Saturne, nuages et nuit de la Terre, ombres et éclipses, lunes des géantes, Pluton (pas de
  carte), dates hors 1550-2650.

## E4 et E7 : galaxies et cosmologie (12 novembre 2026, 16 h UTC)

- `pipeline/natif/galaxies.py` : 5 566 702 galaxies et quasars de la page (456 459 embarqués + 5 110 243 en flux,
  dont 1 194 643 quasars) dans `galaxies.bin` (direction, décalage vers le rouge, couleur de la page) ; 122 galaxies
  et amas nommés dans `galaxies_noms.tsv`.
- `natif/src/cosmologie.h` : distances de Friedmann avec matière, rayonnement, courbure et énergie noire variable
  (w0, wa). `essai_cosmologie` [Certain] : identique à astropy à 0,1 Mpc près pour z = 0,1 à 3 ; âge 13,791 Ga.
- `natif/src/galaxies.h`, `shaders/galaxies.vert` : la distance de chaque galaxie est lue par la carte graphique
  dans une table de 257 valeurs recalculée quand un curseur bouge : les 5,6 millions de points se replacent à
  l'image suivante. Panneau « L'univers en expansion » (H0, matière, énergie noire, w0, wa, âge, courbure).
- Dit à l'écran : éclat des galaxies supposé identique et pâlissant avec la distance ; Voie lactée non dessinée.
- Reste E4 : Voie lactée, formes et photos des galaxies proches, mouvement du Groupe local, cône de lumière.

## Règle de Marc (12 novembre 2026, transmise par le coordinateur) : rien de supposé pour l'état présent

Pour l'état présent, seulement du mesuré. Dans l'appli : la taille des points des galaxies et des astéroïdes est un
réglage d'affichage, dit comme tel à l'écran, jamais une valeur physique annoncée. À relire contre les sources avant
de les afficher comme des mesures : magnitudes H, couleurs et rayons des planètes (recopiés de mémoire), étendue de
l'image des anneaux de Saturne (calée sur deux repères mesurés).

## E2 suite et E3 (12 novembre 2026)

- Anneaux de Saturne : `shaders/sphere.frag` (disque dans le plan de l'équateur, ombre de la planète sur les anneaux
  et des anneaux sur la planète), image Solar System Scope.
- E3 : `pipeline/natif/asteroides.py` (123 530 orbites du JPL, époque JJ 2461200,5), `ref_asteroides.py` (positions de
  référence demandées à JPL Horizons), contrôle [Certain] : Albert, Mildred et IAU à 25 000, 73 000 et 93 000 km de
  Horizons après 154 jours (orbite simple, sans l'attraction des planètes). `natif/src/asteroides.h`,
  `shaders/asteroides.vert` : équation de Kepler résolue par la carte graphique à chaque image. Montrés à moins de
  300 ans de l'époque. Pas encore : noms et fiches des astéroïdes, comètes, sondes.

## Relecture contre la NASA (12 novembre 2026)

Règle de Marc, dans ses mots : « rien supposé, seulement du mesuré. le supposé c'est l'évolution dans le temps ».
Relu contre la fiche « Planetary Fact Sheet » de la NASA (nssdc.gsfc.nasa.gov/planetary/factsheet/) [Certain] :
- rayons des planètes, de la Lune et de Pluton : conformes (l'appli donne le rayon moyen, la NASA le diamètre à
  l'équateur ; écart maximal 3,4 % pour Saturne, dû à son aplatissement) ;
- durées des orbites : conformes à mieux que 0,7 % ;
- vitesses de rotation utilisées pour orienter les astres (orientation.h) : conformes aux durées de rotation de la
  NASA pour Mercure, Vénus, Mars, Jupiter, Saturne, Uranus, Neptune et Pluton.
Ensuite, le même jour :
- direction des pôles et méridiens des onze astres : conformes au fichier officiel de la NASA (NAIF, pck00011.tpc),
  contrôle automatique `pipeline/natif/controle_orientation.py` [Certain] ;
- éclat des planètes vues comme des points : plus rien de mémoire ; `pipeline/natif/planetes.py` lit la magnitude
  V(1,0) dans les fiches de la NASA et tire la teinte de la moyenne de chaque carte de surface (`planetes.tsv`).
  Deux valeurs de mémoire étaient fausses : Lune (+0,28 au lieu de −0,08) et Neptune (−7,00 au lieu de −6,94).
Reste [À vérifier] : étendue de l'image des anneaux de Saturne (calée sur deux repères mesurés, la source ne la
documente pas) ; magnitude absolue et couleur du Soleil (valeurs nominales usuelles, non relues).

## Lunes (12 novembre 2026)

- `natif/src/ephemeride.h` : segments de type 3 et lecture de plusieurs fichiers ensemble (`eph::Set`).
- Fichiers du NAIF (dossier satellites) : `mar099s.bsp` (Phobos, Déimos), `jup365.bsp` (Io, Europe, Ganymède,
  Callisto ; 1,1 Go), `sat441.bsp` (Mimas à Japet), `nep097.bsp` (Triton), `plu060.bsp` (Charon et le centre de
  Pluton). `pipeline/natif/lunes.py` : rayons moyens tirés du fichier officiel pck00011.tpc, positions de référence
  demandées à JPL Horizons (`ref_lunes.txt`).
- Contrôle `essai_ephem` [Certain] : 14 lunes à moins d'un millimètre de Horizons ; Triton à 255 km (le seul fichier
  léger qui le contient est plus ancien que la solution de Horizons : écart affiché, non jugé).
- Pas faites : les cinq grandes lunes d'Uranus (les fichiers du NAIF qui les contiennent pèsent 5,6 Go).
- À l'écran : chaque lune a son orbite tracée d'après les éphémérides, sa fiche et un repère à sa place mesurée ;
  son éclat et sa surface ne sont pas renseignés (rien n'est inventé). La planète est placée à son vrai centre quand
  le fichier des lunes le donne (important pour Pluton, dont le centre de masse avec Charon est hors de la planète).

## État au 12 novembre 2026, 16 h 50 UTC

- PR #34 versée dans `main` (accord de Marc, contrôles verts). La branche `appli-pc` continue à partir de `main`.
- Fils PC assemblés ici : interface (#45, #47), bibliothèque de physique (#46, #48 : système solaire hors DE440 avec
  suivi pas à pas, Lune de Meeus de −2000 à +6000, orbites galactiques, rejeu de la fusion).
- E6, première version : le temps va jusqu'à +10 milliards d'années (deux vitesses de plus). Au-delà de 3 millions
  d'années : étoiles mesurées cachées (ligne droite hors de validité), galaxies du Groupe local placées par le calcul
  de la fusion (`phys::fusion::Rejeu`, calcul à 300 000 particules), 30 000 étoiles du calcul affichées
  (`natif/src/fusion_points.h`), galaxies des relevés éloignées par le facteur d'échelle calculé
  (`cosmo::scaleFactorAt`). Les galaxies sans mouvement calculé ne sont pas montrées à ces dates. Nouvel astre :
  « Centre de la Voie lactée ». Captures de contrôle : aujourd'hui, +4 Ga (Andromède en approche), +6,5 Ga (fusionnées).
- À faire : remplacer les fichiers du rejeu par ceux du calcul à 3 millions de particules quand il finit
  (`pipeline/natif/fusion_bin.py`), textes d'interface du temps profond (fil interface), passé lointain.

## Éclipses et lumières de nuit (12 novembre 2026)

- `essai_eclipse` [Certain] : le 12 août 2026 à 17 h 47 min 06 s en temps dynamique (maximum du catalogue des
  éclipses de la NASA, ligne relue en ligne), l'axe de l'ombre de la Lune touche la Terre à moins de 1° du point
  donné par la NASA (65° nord, 25° ouest, au degré près ; Terre prise sphérique et lumière instantanée). L'ombre est sur la Terre une demi-heure avant et après, absente un mois plus tard.
- `shaders/sphere.frag` : pour chaque point de la surface, part du disque du Soleil cachée par l'astre le mieux aligné
  (planète, lune ou lune sœur ; un seul par image) : ombre et pénombre exactes pour un Soleil uniforme. Capture de
  contrôle : la tache d'ombre entre le Groenland et l'Islande (`--cible Terre --date 26.61256749562704 --vue 139.8,45`).
- Lumières de nuit de la Terre : carte « Black Marble » de la NASA (via Solar System Scope), montrée du côté nuit ;
  son éclat est un réglage d'affichage (dit dans le code ; à dire à l'écran par le fil interface).
- Option de contrôle ajoutée : `--vue longitude,latitude` (direction d'où l'on regarde l'astre suivi).

## Gaia et Voie lactée branchés (12 novembre 2026, 17 h 20 UTC)

- PR #54 du fil « Voie lactée et étoiles Gaia » intégrée : `GaiaRenderer` (98 278 356 étoiles Gaia DR3, niveaux de
  détail) et `MilkyWayRenderer` (lumière d'ensemble de la Galaxie, modèle ajusté sur des mesures ; trois points
  supposés, voir `docs/gaia-voie-lactee.md`). Fichiers facultatifs `gaia.bin` (2,36 Go) et `voie_lactee.bin`.
- Choix d'affichage de ce fil : la Galaxie diffuse n'a pas d'éclat multiplié ; la multiplication d'éclat des étoiles
  (au plus 100 fois) s'efface entre 3 000 et 30 000 années-lumière (sinon, tache trompeuse autour du Soleil, constatée
  par capture). Gaia et la Voie lactée ne sont montrées qu'à moins de 3 millions d'années d'aujourd'hui.
- Question posée à Marc : la Voie lactée « modèle » contient trois points supposés ; la garder affichée (dite comme
  telle) ou la retirer, au nom de sa règle « rien de supposé pour le présent ».
