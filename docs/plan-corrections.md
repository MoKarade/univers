# Plan de corrections de l'appli PC : les erreurs visibles (20 novembre 2026)

Demande de Marc : « y a d'autres erreurs comme ça, trouve-les et prépare un plan pour tout corriger ». Ce document
fait l'audit et le plan. **Rien n'est corrigé ici.**

## En bref

- **25 nouveaux bugs visibles** trouvés, en plus des 6 que Marc a déjà signalés (corrigés dans le fil « Corriger les
  saccades et afficher les grandes structures », dit ici **fil correcteur**).
- Les trois plus graves : **(1)** de près, une étoile n'est pas là où la caméra la vise, et parfois elle est en double ;
  **(2)** l'éclat de tout le ciel dépend du zoom (×100 dès qu'on recule de 300 années-lumière de l'astre suivi), ce qui
  blanchit Andromède de près ; **(3)** de très loin (univers observable) l'écran est noir, et la Voie lactée disparaît
  vue d'au-delà de quelques millions d'années-lumière.
- Plan en 5 lots, du plus visible au moins visible (section 4). Effort total estimé : environ 60 à 80 heures de
  travail de Claude, [Supposition] : chiffres tirés de la taille des changements, pas d'une mesure de cas semblables.

## 1. Méthode

- Code lu : `appli-pc` au commit `2bd66cd` (PR 115 et 116 fusionnées, donc avec Laniakea et le nuage d'Oort).
  L'appli a été fabriquée à part (`C:\tmp\natif\build-audit`), avec les données installées dans `C:\dev\Univers-PC`
  plus `structures.bin` (absent de l'appli installée).
- 48 captures en fenêtre cachée (`--fenetre-test 20 --capture`), une à la fois, de 9 500 km de la Lune à
  100 milliards d'années-lumière, et de −500 Ma à +9 Ga. Les plus parlantes sont dans `docs/captures-audit-2011/`
  (nom = échelle ; « al » = années-lumière).
- Lecture du code du rendu, de la caméra, de la sélection et du temps.
- **Pas fait** : la souris et la fenêtre réellement affichée (les captures sont en fenêtre cachée, identiques à
  l'écran d'après `fenetre.cpp:5`) ; un temps qui défile en direct (les captures sautent à la date).
- Déjà couvert ailleurs et non répété : `docs/revue-code-1811.md` (F1 à F8, N1 à N8, O1 à O5, P1, P2, S1, S2, T1).

Labels : [Certain] lu dans le code ou vu sur une capture ; [Probable] déduit ; [À vérifier] demande une mesure.

## 2. Ce que le fil correcteur fait déjà, et ce que cet audit lui apporte

| Bug signalé par Marc | Ce que l'audit ajoute | À transmettre |
|---|---|---|
| Une étoile gigote quand on zoome | Cause trouvée et vue : voir **A1**. C'est le même défaut qui place l'étoile à côté de son cercle, même aujourd'hui | oui, A1 entier |
| Univers observable absent | Toujours noir avec le code du jour et `structures.bin` (captures `22`, `23`) : voir **A4** | oui |
| Laniakea absent | Avec `structures.bin`, Laniakea s'affiche bien (capture `21_soleil_3e9`). Il manque seulement d'installer le fichier | non |
| Clic sur une galaxie + zoom n'affiche rien | Trois causes possibles trouvées : **A2** (écran blanc à 20 000 al d'Andromède), **B3** (arrivée à 0,3 Mal d'une structure de centaines de Mpc), **C6** (galaxie sautée quand le budget de points est plein) | oui |
| Nuage de Magellan qui saccade puis disparaît | Piste : bord du film qui avance par à-coups (relu toutes les 5 s, `FilmStars::reload`) et Petit Nuage qui peut basculer sur l'autre source si le film n'a que 4 galaxies (`simulation.h`, `refreshGalaxies`, test `ci < film->galaxies()`) [À vérifier] | oui |
| Pas de planètes / pas de trou noir central | Rien de plus | non |

**Pour éviter le doublon** : les lots 1 et 2 ci-dessous touchent `gaia.vert`, `orbites_pas.comp`, `simulation.h`
(éclat, `arriveDist`) et `galaxies.h`. À faire **après** la fusion du fil correcteur, sur sa branche à jour.

## 3. Les bugs, du plus visible au moins visible

Effort en heures de travail de Claude [Supposition], hors attente des contrôles.

### Lot A : ce qui casse la crédibilité au premier coup d'œil

**A1. De près, l'étoile n'est pas sous son cercle ; parfois deux points ; la caméra vise le vide.**
- Captures : `27_sirius_proche`, `28_betelgeuse_proche`, `33_sirius_a` et `34_sirius_b` (même étoile à 9,46 puis
  9,93 millions de km : un des deux points a bougé), `49_proxima` (le cercle est vide).
- Cause [Certain] code, [Probable] lien avec la capture : les états d'orbite des étoiles sont en nombres simple
  précision, en kpc, autour du centre de la Galaxie (`shaders/orbites_pas.comp`), puis la place relative au Soleil
  est la différence de deux grands nombres en simple précision (`gaia.vert:99`, `gaia_agrege.vert:57`,
  `etoiles_orbite.vert:41`, `orbite_galactique.glsl:77`). Pas d'environ 200 UA à 8 kpc. La caméra, elle, suit la
  place calculée en double (`Sim::position`). L'étoile du catalogue brillant et sa copie Gaia sont deux points à deux
  places arrondies différemment : d'où le doublon [Probable].
- Correctif : intégrer et stocker les orbites dans un repère centré sur le Soleil (Soleil avancé en double sur le
  processeur), ou en paires haute/basse précision ; pour l'astre suivi, dessiner son point à la place double du
  processeur et masquer sa copie Gaia. 10 à 14 h. **Recoupe « étoile qui gigote » : à faire par le fil correcteur.**

**A2. L'éclat de tout le ciel dépend du zoom : Andromède devient un écran blanc de près.**
- Captures : `25_andromede_2e4` (écran blanc, aucune forme), `12_soleil_100al` et `13_soleil_1000al` (le ciel se
  remplit d'étoiles en reculant de 30 à 1 000 al du Soleil).
- Cause [Certain] : `Sim::brightnessBoost()` (`simulation.h:865`) multiplie l'éclat de **toutes** les étoiles par
  (distance à l'astre suivi / 30 al)², jusqu'à ×100 dès 300 al. La distance utilisée est celle de la caméra à l'astre
  suivi, pas celle des étoiles : à 20 000 al d'Andromède, ses étoiles proches reçoivent ×100 et saturent. Les
  nombres de l'image (16 bits) peuvent alors déborder (au-delà de 65 504) et donner des points noirs
  (`ecran.frag:20`) [À vérifier].
- Correctif : régler la pose sur la lumière réellement à l'écran (pose automatique mesurée sur l'image de la frame
  précédente, lissée sur ~1 s, comme un appareil photo), et borner les valeurs avant la conversion. 6 à 8 h.

**A3. La Voie lactée disparaît vue de loin.**
- Captures : `17_soleil_1e6` (petit trait visible), `18_soleil_5e6` et `41_gl_4ga` (rien à la place du Soleil,
  alors qu'Andromède, plus loin de la caméra, est visible).
- Cause [À vérifier] : aucune forme de secours pour notre galaxie quand ses couches d'étoiles (Gaia, modèle) passent
  sous un pixel ; Andromède, elle, a une forme dans `galaxies_formes.bin`.
- Correctif : donner à la Voie lactée la même forme lointaine qu'aux autres galaxies, avec la lumière totale de ses
  étoiles (raccord d'éclat contrôlé à 1 et 5 Mal). 4 à 6 h.

**A4. Univers observable : écran noir.**
- Captures : `22_soleil_3e10`, `23_soleil_1e11` (une tache au centre, le reste noir, alors que le cadre annonce
  18,3 millions de galaxies et quasars).
- Cause [À vérifier] : les galaxies lointaines sont des points d'un pixel dont l'éclat baisse en 1/d², sans lumière
  regroupée au-delà d'une taille d'écran (contrairement aux étoiles). Pas non plus de fond diffus cosmologique à
  cette échelle (`ciel_cmb.bin` existe).
- Correctif : lumière regroupée par cellule (comme `gaia_agrege`) pour les relevés lointains, et sphère du fond
  diffus au bord de l'univers observable. 8 à 10 h. **Recoupe le fil correcteur.**

**A5. Des noms sans rien dessous entre 3 et 100 millions d'al.**
- Captures : `19_soleil_3e7`, `46_vierge_3e7` (Amas de la Vierge vu de 30 Mal), `47_soleil_1e8`.
  Des dizaines de noms (M81, M87, Sombrero…), presque aucune galaxie visible.
- Cause [Probable] : même éclat trop faible que A4 ; galaxies de forme montrées seulement à partir de 2 px.
- Correctif : dans le même lot que A4, puis ne nommer que ce qui se voit. 2 h de plus.

**A6. Une neige d'astéroïdes autour de la Terre.**
- Captures : `01_terre_proche` (bande de points blancs en haut), `05_soleil_1ua` (la moitié de l'image).
- Cause [Certain] : `asteroidGain()` (`simulation.h:879`) donne le même éclat (0,30) à chacun des 1,58 million
  d'astéroïdes sous 2,5 UA, quelle que soit leur taille. En vrai, seule Vesta se voit à l'œil nu.
- Correctif : éclat tiré de la magnitude absolue H de chaque astéroïde (déjà dans le catalogue JPL [À vérifier]) ;
  la « ceinture repère » devient une option du menu, dite comme telle. 3 h.

### Lot B : la caméra et le clic

**B1. Un clic dans le ciel vide fait voler vers une galaxie invisible.** [Certain] code.
`pickBody` (`interface_base.h:401`) prend tout astre à moins de 16 px, y compris les 55 000 galaxies
Cosmicflows-4 dont le nom est caché ; environ une cible tous les 16 px. Correctif : même règle que les noms
(`labelWanted`) et priorité à l'astre le plus important. 1 h.

**B2. Recherche « Sirius » depuis la Terre : arrivée dans l'étoile.** [Certain] code.
`arriveDist` (`simulation.h:804`) garde la distance précédente si elle est plus petite (Terre : 28 000 km) ; Sirius
fait 1,2 million de km de rayon. Correctif : pour une étoile, au moins quelques rayons et au moins 50 UA par
défaut. 0,5 h.

**B3. Laniakea, le Grand Attracteur ou un vide cliqué : on arrive à 0,3 million d'al, dans le noir.** [Certain]
code. `arriveDist` met toute « galaxie » à au moins 3 × 10⁵ al, alors que ces structures se voient à partir de
3 × 10⁸ al. Correctif : distance d'arrivée selon la taille de la structure. 1 h.

**B4. L'astre suivi disparaît (fin des éphémérides, lune, astéroïde) : bascule sans prévenir.**
Capture `35_terre_1e9ans` : on demande la Terre dans 1 Ga, on obtient « Soleil » à 1,9 UA, sans message.
[Certain] `simulation.h:898-907`. Correctif : vol vers le Soleil à une distance qui lui convient, et une ligne
« la Terre n'a plus de position connue à cette date ». 1 h.

**B5. « Aller à » propose des étoiles et galaxies qui ne font rien à cette date.** [Certain]
`interface_recherche.h:157-166` sans test `visible(i)`. Correctif : griser, comme les sondes. 0,5 h.

**B6. « Retour » ne revient pas à la même vue.** [Certain] `back()` ne remet ni l'angle ni la hauteur du regard ;
pour un astéroïde, l'historique pointe un emplacement réutilisé. 1 h.

**B7. Vol pendant que le temps file vite : la caméra balaie le vide.** [Probable] `flyFrom` est gardé dans le repère
du Soleil, qui se déplace pendant les 1,8 s du vol. 1,5 h.

**B8. Origine (touche Début) : saut sans vol ni retour possible.** [Certain] `fenetre.cpp:565`. 0,5 h.

### Lot C : ce qui saute ou s'éteint d'un coup

**C1. Toutes les galaxies lointaines deviennent impossibles à cliquer ou nommer au-delà de ±3 Ma.** [Certain]
`refreshGalaxies` ne leur donne une place que près d'aujourd'hui ; leurs points restent dessinés. Correctif : place
fixe (plus l'expansion) à toute date. 1 h.

**C2. Le ciel d'ici s'éteint d'un coup à ±3 Ma et à 100 al du Soleil.** [Certain] `gaia.h:246` : la lumière des
1,6 milliard de sources sans distance passe de 37 % à 0 en une image ; et elle est retirée de tout le ciel dès que
les tuiles fines s'activent, avant qu'elles soient lues [Probable]. Correctif : fondus en distance (100 → 200 al)
et en temps (1 → 3 Ma) ; garder l'ancien ciel tant que les tuiles ne sont pas toutes lues. 3 à 4 h.

**C3. La lueur des étoiles faibles s'éteint par plaques quand on grossit (Ctrl + molette).** [Certain] ligne,
[Probable] effet. `gaia.h:618` (et `gaia_agrege.vert:76`) : au-delà de 512 px, la lumière de la feuille est jetée.
Correctif : étaler avec une taille plafonnée en gardant la lumière. 3 h.

**C4. Les astéroïdes disparaissent d'un coup à ±300 ans.** [Certain] `simulation.h:883`. Rampe de 250 à 350 ans.
0,5 h.

**C5. Les bras dessinés disparaissent d'un coup à ±3 Ma en « meilleur rendu ».** [Certain] `fenetre.cpp:827`.
0,5 h.

**C6. Une galaxie de forme disparaît quand le budget de points est plein.** [Probable] `galaxies_formes.h:100,112`
saute la galaxie, et le shader a déjà retiré sa lumière « point » : personne ne la dessine. Correctif : ne retirer
la lumière point que si la galaxie est vraiment admise. 2 h.

**C7. Les comètes d'Oort font un petit saut à chaque milliard d'années.** [Certain] `structures.h` :
`fmod(years, 1e9)` n'est pas un multiple des périodes. 0,5 h.

### Lot D : ce qui est faux dans le panneau

**D1. « (mesuré) » sur des places calculées.** Capture `38_vl_1ga` : à +1 Ga, « Distance à la place actuelle du
Soleil 27 756 al (mesuré) ». [Certain] Le libellé et la valeur ne collent pas : c'est la distance au Soleil de la
date montrée (`interface_temps.h:336`), et elle est calculée. 0,5 h.

**D2. Des noms visibles à travers les planètes.** Capture `04_saturne` : « Rhéa » écrit sur le disque de Saturne
alors que la lune est derrière. [Certain] vu. Correctif : cacher le nom d'un astre masqué par une sphère. 1 h.

**D3. Seuils du chaos décalés de 2000 ans.** [Certain] `interface_base.h:360`, `interface_temps.h:95` mélangent
« années depuis J2000 » et « année 2026 ». Invisible à l'œil. 0,2 h.

### Lot E : finitions de rendu

**E1. Disque des planètes coupé net au bord de l'écran.** [Probable] `spheres.h:322` : marge 1,6 alors que la
perspective étire jusqu'à 2,06 dans les coins. 1 h.

**E2. Une lune ou une sonde devant une planète est cachée par elle.** [Certain] les sphères sont dessinées après
tous les points, sans profondeur. 2 h.

**E3. Les étoiles n'ont jamais de disque : à 1 000 km de Sirius, un point de 14 px.** [Certain] `spheres.h`, seules
les étoiles « Soleil » ont une sphère. Correctif : sphère d'étoile (couleur, rayon publié quand il existe, sinon
« rayon inconnu »). 4 à 6 h.

**E4. Petit Nuage de Magellan : un ovale lisse ; Grand Nuage : rayures rectangulaires.** Captures `32_pnm_3e4`,
`26_gnm_5e4`. [À vérifier] modèle du film (Petit Nuage sans forme mesurée) et sous-nuages repliés (« 14 sous-nuages
repliés » au journal). 2 h d'enquête avant correctif.

**E5. Points des galaxies et des structures en simple précision.** [Probable] invisible aujourd'hui (on ne peut pas
s'approcher à moins de 1 000 al), à corriger avec A1. 1 h.

## 4. Ordre proposé

| Lot | Contenu | Effort [Supposition] | Pourquoi dans cet ordre |
|---|---|---|---|
| 0 | Installer `structures.bin` (fait par le fil correcteur) et attendre sa fusion | 0 | évite de toucher les mêmes fichiers |
| 1 | A2 (pose automatique), A6 (astéroïdes), B1 à B5, C1, D1 | ~14 h | le plus visible, petits changements sûrs |
| 2 | A1 (précision des étoiles) et E5 | ~12 h | gros changement de calcul, contrôle d'orbite à refaire (`--controle-orbites`) |
| 3 | A3, A4, A5 (galaxies vues de loin, univers observable) | ~16 h | remplit les échelles vides |
| 4 | C2 à C7, B6 à B8 | ~13 h | sauts et coupures |
| 5 | D2, D3, E1 à E4 | ~12 h | finitions |

Chaque lot : une PR vers `appli-pc`, avec des captures avant/après aux mêmes échelles (script
`C:\tmp\natif\audit-cap\tirer.py`, à ranger dans `natif/` au lot 1 pour qu'il serve de contrôle).

## 5. Limites

- Les causes marquées [À vérifier] (A3, A4, E4) demandent une petite enquête avant le correctif.
- Rien n'a été vu en direct à la souris, ni avec le temps qui défile : les sauts de C2, C4, C5 sont déduits du code.
- Les efforts sont des estimations sans mesure de cas semblables.
