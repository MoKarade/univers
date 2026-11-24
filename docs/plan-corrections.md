# Plan de corrections de l'appli PC : les erreurs visibles (20 novembre 2026)

Demande de Marc : « y a d'autres erreurs comme ça, trouve-les et prépare un plan pour tout corriger ». Ce document
fait l'audit et le plan. **Rien n'est corrigé ici.**

## En bref

- **25 nouveaux bugs visibles** trouvés, en plus des 6 que Marc a déjà signalés (corrigés dans le fil « Corriger les
  saccades et afficher les grandes structures », dit ici **fil correcteur**).
- Les trois plus graves : **(1)** de près, une étoile n'est pas là où la caméra la vise, et l'écart grandit avec sa distance au Soleil et avec la date ;
  **(2)** l'éclat de tout le ciel dépend du zoom (×100 dès qu'on recule de 300 années-lumière de l'astre suivi), ce qui
  blanchit Andromède de près ; **(3)** de très loin (univers observable) l'écran est noir, et la Voie lactée disparaît
  plus loin que 10 milliards d'années-lumière.
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

**A1. De près, l'étoile n'est pas sous son cercle de visée : la caméra vise le vide.**
- Mesuré (section 6) : écart entre le centre de l'écran (où la caméra vise) et le point de l'étoile, aujourd'hui :
  Proxima et Sirius < 0,02 UA ; Bételgeuse (498 al) **0,7 à 1,1 UA** ; Alnilam (1 977 al) **1,6 UA** ; Deneb
  (1 412 al) hors du champ à 0,0001 al. Dans le temps, Sirius : 0 à +1 000 ans, **17 UA à +100 000 ans, 25 UA à
  +1 Ma**, hors du champ à +10 Ma. Images : `m_betelgeuse_zoom.jpg`, `m_sirius_dates.jpg`, `27`, `28`, `49`.
- Quand on zoome de 2 % en 2 %, le point se déplace de 4 à 8 px au lieu de rester au centre (`m_betelgeuse_zoom`) :
  c'est le « gigotement » signalé par Marc.
- Cause aujourd'hui [Certain] : la place de chaque étoile est rangée en simple précision, en années-lumière depuis le
  Soleil (`etoiles.vert`, `inX/inY/inZ`) ; arrondi = |x| × 6 × 10⁻⁸, soit 1,9 UA à 500 al (mesuré : 0,7 à 1,1 UA,
  c'est bien la moitié d'un pas). La soustraction de la caméra en deux temps (`camHi`/`camLo`) ne rattrape pas une
  place déjà arrondie. La caméra suit la place en double (`Sim::position`).
- Cause dans le temps [Certain] code, [Probable] part de chacune : orbites intégrées et rangées en simple précision
  en kpc autour du centre de la Galaxie (`orbites_pas.comp`), puis différence étoile − Soleil en simple précision
  (`gaia.vert:99`, `gaia_agrege.vert:57`, `etoiles_orbite.vert:41`, `orbite_galactique.glsl:77`) : pas d'environ
  200 UA à 8 kpc.
- Correctif : (a) l'astre suivi est dessiné à part, à sa place en double calculée par le processeur, et son point
  dans le nuage est masqué (règle aussi le zoom) ; (b) places rangées en paires haute/basse précision ;
  (c) orbites intégrées dans un repère centré sur le Soleil. (a) seul : 3 h et règle ce que Marc voit ; (b)+(c) :
  10 à 12 h. **Recoupe « étoile qui gigote » : à voir avec le fil correcteur (PR 118 fusionnée).**

**A2. L'éclat de tout le ciel dépend du zoom : Andromède devient un écran blanc de près.**
- Mesuré (section 6) : éclat moyen de l'image, Soleil suivi, vue fixe : 6,1 à 30 al, 22,5 à 100 al, **77,8 à
  300 al** (×13). Andromède suivie : **47 % de l'image saturée en blanc à 20 000 al**, 42 % à 50 000 al, 31 % à
  100 000 al, 3 % à 300 000 al. Images : `m_eclat_zoom.jpg`, `m_andromede_sature.jpg`.
- Cause [Certain] : `Sim::brightnessBoost()` (`simulation.h:865`) multiplie l'éclat de **toutes** les étoiles par
  (distance caméra → astre suivi / 30 al)², au plus ×100 ; et `fieldGain()` (`simulation.h:922`) multiplie encore par
  (60° / champ)², jusqu'à ×10 000 quand on grossit au Ctrl + molette. La pose dépend donc du zoom, pas de la lumière
  à l'écran : à 20 000 al d'Andromède, ses étoiles reçoivent ×100 et saturent.
- Correctif : pose automatique mesurée sur l'image précédente (moyenne en logarithme des pixels éclairés), lissée sur
  ~1 s, bornée ; on garde le réglage à la main par crans. Plus une borne des valeurs avant la conversion
  (`ecran.frag`). 6 à 8 h.

**A3. La Voie lactée vue de loin est bien plus pâle qu'Andromède.** (rétrogradé après mesure)
- Captures : `18_soleil_5e6`, `41_gl_4ga`, puis `m4_vl_5e6` (vue fixe, interface fermée) : elle est là, mais en
  petite tache bien plus faible qu'Andromède à distance comparable. Ma première lecture (« elle disparaît ») était
  trop forte.
- Cause [À vérifier] : ses étoiles affichées sont la somme Gaia + modèle « ce qui manque » ; sa lumière totale n'a
  jamais été comparée à sa magnitude publiée (M_V ≈ −20,9). Correctif : mesurer cette somme, puis corriger
  l'éclat du modèle si elle est trop basse. 2 h de mesure, puis 2 à 4 h.

**A4. Univers observable : l'image s'éteint en s'éloignant.**
- Mesuré : éclat moyen 40 à 1 milliard d'al, 17 à 3, 8,6 à 10, 2,5 à 30, **0,5 à 90 milliards d'al** (noir), alors
  que le cadre annonce 18,3 millions de galaxies. Image : `m_univers_loin.jpg`, captures `22`, `23`.
- Cause [Certain] code, [Probable] part : chaque galaxie lointaine est un point dont l'éclat baisse en 1/d² vu de la
  caméra (`galaxies.vert`, `(dCom / dc)²`), et le renfort d'éclat s'arrête à ×100 dès 300 al (`brightnessBoost`) ;
  rien ne compense ensuite. Les mêmes 18 millions de points éclairent donc de moins en moins, en 1/d.
- Correctif : la pose automatique d'A2 règle l'essentiel ; plus la lumière regroupée par cellule (comme
  `gaia_agrege`) pour les relevés lointains, et le fond diffus (`ciel_cmb.bin`) au bord. 4 à 6 h après A2.
  **Recoupe le fil correcteur.**

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
Mesuré : de 99 à 101 al du Soleil l'image perd 7 % d'éclat d'un coup (24,4 → 22,8) ; de 2,99 à 3,01 Ma, aucun écart
mesurable dans cette vue : la coupure en temps n'est pas vue, seulement lue dans le code.

**C3. La lueur des étoiles faibles s'éteint par plaques quand on grossit (Ctrl + molette).** [Certain] ligne,
[Probable] effet. `gaia.h:618` (et `gaia_agrege.vert:76`) : au-delà de 512 px, la lumière de la feuille est jetée.
Correctif : étaler avec une taille plafonnée en gardant la lumière. 3 h.

**C4. Les astéroïdes disparaissent d'un coup à ±300 ans.** [Certain] `simulation.h:883`. Mesuré : éclat moyen 50,4 à
+320 ans, 5,4 à +330 ans (image `m_asteroides_300ans.jpg`). Rampe de 250 à 350 ans.
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

- Les causes marquées [À vérifier] (A3, E4) demandent une petite enquête avant le correctif.
- Rien n'a été vu à la souris. Le temps qui défile a été essayé sur trois trajets (section 6) : même image qu'en
  sautant à la date.
- Les efforts sont des estimations sans mesure de cas semblables.

## 6. Mesures du 20 novembre après-midi

Demande de Marc : « va voir plus loin, plus précis ». 65 captures de plus, vue fixe (`--vue 30,20` ou `30,40`),
panneau fermé (`UNIVERS_PANNEAU=ferme`), mesurées par programme : place des points blancs près du centre de l'écran
(`blobs.py`) et éclat moyen de la zone sans interface (`lum.py`), dans `C:	mp
atifudit-cap`.
Conversion : 60° pour 900 px, soit 1,16 × 10⁻³ radian par pixel.

| Mesure | Résultat | Conclusion |
|---|---|---|
| Écart étoile / visée, 8 étoiles de 4 à 1 977 al, caméra à 10⁻³ et 10⁻⁴ al | < 0,02 UA jusqu'à 25 al ; 0,7 à 1,1 UA à 498 al ; 1,6 UA à 1 977 al ; Deneb hors champ | A1 confirmé, écart proportionnel à la distance au Soleil |
| Sirius à +10³, +10⁵, +10⁶, +10⁷, +10⁸ ans | 0 ; 17 UA ; 25 UA ; hors champ ; hors champ | A1 s'aggrave avec la date |
| Bételgeuse, zoom par pas de 2 % | le point bouge de 4 à 8 px à chaque pas | c'est le « gigotement » |
| Éclat moyen, Soleil vu de 10 à 1 000 al | 11,7 ; 6,1 ; 12,5 ; 22,5 ; 77,8 ; 88,6 | A2 confirmé (×13 de 30 à 300 al) |
| Andromède vue de 3 × 10⁵ à 2 × 10⁴ al | 3 % ; 31 % ; 42 % ; 47 % de pixels saturés | A2 confirmé |
| Univers de 3 × 10⁸ à 9 × 10¹⁰ al | 38,9 ; 40,1 ; 17,1 ; 8,6 ; 2,5 ; 0,5 | A4 confirmé, baisse en 1/d |
| Astéroïdes à +320 et +330 ans | 50,4 puis 5,4 | C4 confirmé |
| Ciel à 99 et 101 al ; à 2,99 et 3,01 Ma | −7 % d'un coup ; aucun écart | C2 en distance vu ; en temps, non vu |
| Saut à la date contre temps qui défile (Voie lactée +100 Ma, Soleil +5 Ma, Grand Nuage +300 Ma) | écart moyen 0 ; 1,6 ; 0 (sur 255) | pas de bug de ce côté |
| Voie lactée et Andromède vues de 1 à 20 Mal | Voie lactée présente mais pâle | A3 rétrogradé |

Correction d'une erreur du premier jet : les « deux points » de Sirius n'ont pas été confirmés. Sur Arcturus et
Canopus, le cercle orange de l'interface coupait le point en deux dans ma mesure ; ce n'étaient pas deux étoiles.

## 7. Avancement et nouveaux retours de Marc (20 novembre, fin d'après-midi)

Fait :
- PR 121 (fusionnée) : B1 à B5, D1, A6, C4.
- PR 122 : A2 (pose automatique contre la saturation), relève de pose aux échelles des galaxies (A4, A5), fond diffus de
  Planck sur le bord de l'univers observable, sphères approchées cachées par défaut, amas et superamas nommés comme tels,
  rayon de l'univers observable, remarques de relecture du lot 1a.
- En cours (branche `corrections-zoom`) : C2 (fondus du ciel seul), C5 (fondu des bras), C6 (galaxie de forme non
  dessinée), D2 (noms derrière les planètes), E1 (disques coupés), renfort d'éclat en d/30 au lieu de (d/30)², et un
  outil de balayage du zoom en un seul lancement (`UNIVERS_BALAYAGE`).

Nouveaux retours de Marc, avec ce qui a été trouvé :

| Retour | Mesure ou cause | Statut |
|---|---|---|
| « Les vues changent quand je zoome, l'éclairage aussi » | zoom complet en 41 vues : éclat ×13 de 30 à 300 al (renfort en (d/30)²), coupure du ciel seul à 100 al (−7 %), bras dessinés qui apparaissent de 1 000 à 10 000 al, Voie lactée qui s'efface vers 1 Mal | renfort adouci, fondus ajoutés ; balayage fin de contrôle |
| « Laniakea quasi aucune galaxie, c'est vide » | galaxies des relevés au vrai éclat en 1/d², rien ne compensait au-delà de 300 al ; voiles des vides plus brillants que les galaxies | pose relevée (×10 à ×100 mesuré), repères à éclat fixe (PR 122) |
| « Des boules » au-delà de Laniakea | sphères « forme généralisée » des vides SDSS/BOSS et des superstructures | cachées par défaut (PR 122) |
| « Je veux voir le CMB » | la sphère du fond diffus était unie | carte SMICA de Planck posée dessus (PR 122) |
| « Le superamas c'est une seule galaxie » | `galaxies_noms.tsv` range 11 amas et superamas sous « galaxie » | nommés et décrits comme amas ou superamas, sources citées (PR 122) |

## 8. Avancement (20 novembre, soir)

| Point | Statut |
|---|---|
| A1 étoile sous son cercle | fait (fil correcteur, PR 118) et vérifié : Sirius à +10⁵, +10⁶, +10⁷ ans et Bételgeuse au centre exact |
| A2, A4, A5 éclat | PR 122 (pose automatique) et PR 123 (rampe) |
| A3 Voie lactée lointaine pâle | mesurée de nouveau à 3 Mal : pas plus pâle qu'Andromède (lumière au centre 3 480 contre 284) : retiré |
| A6, B1 à B5, C4, D1 | PR 121 |
| C1, C7, E3 | PR 124 |
| C2, C5, C6, D2, E1, sauts du zoom | PR 123 |
| E4 Nuages de Magellan | Grand Nuage : traits allongés [Probable] = cases de lumière Gaia additionnée (morceau de ciel × tranche de parallaxe) étirées le long de la ligne de visée ; Petit Nuage : ovale lisse = forme du modèle du grand calcul (pas de forme mesurée). À traiter avec le fil du grand calcul |
| E2 points cachés par les sphères | à faire |
| E5 simple précision des galaxies | sans effet visible tant qu'on ne peut s'approcher à moins de 1 000 al : laissé |

## 9. État final (24 novembre 2026)

Toutes les corrections de ce plan sont fusionnées dans `appli-pc` (PR 121 à 126, 128, 130, 131, 134, 135), et elles sont
toujours dans le code au commit `ff4cab4`.

| Point | PR | Point | PR |
|---|---|---|---|
| A1 étoile sous son cercle | 118 (fil correcteur), vérifié | C1 galaxies lointaines à toute date | 124 |
| A2 pose automatique | 122, 123, 126, 128 (puis 142, autre fil) | C2, C5, C6 fondus et coupures | 123 |
| A3 Voie lactée pâle de loin | mesurée : pas pâle, retiré | C4 astéroïdes à 300 ans | 121 |
| A4, A5 univers lointain | 122, 126, 128 (puis 141, autre fil) | C7 comètes d'Oort | 124 |
| A6 neige d'astéroïdes | 121 | D1, D2, D3 libellés et noms | 121, 123 |
| B1 à B5 caméra et clic | 121, 122 | E1, E2, E3 disques et étoiles | 123, 124, 125 |
| Retours de Marc du 20/11 (zoom, boules, fond diffus, amas, sélection, M77, gaz, nébuleuses, poussière, doublons) | 122, 123, 126, 128, 130, 134, 135 | E4 Nuages de Magellan | fil « forme des Nuages » (PR 148) |

Outils laissés pour les contrôles : `natif/balayage.py` (zoom en un lancement ; `--temps` pour le passé et l'avenir),
`UNIVERS_ECRAN=etoile:<rang>`.
