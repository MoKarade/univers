# Vérité de l'avenir lointain (tâche R4)

Inventaire de tout ce que la page fait changer à une date fixée (surtout dans l'avenir, et aussi les fondus liés à l'écart avec aujourd'hui) : disparitions, fondus, dates écrites à la main, fins de table qui figent l'image.
Pour chaque ligne : ce que fait le code, son statut réel, la source, et ce qu'il devient (gardé, recalculé, ou coupé avec la mention « inconnu »).

Règles appliquées (décisions de Marc du 11 novembre 2026, `docs/plan-reel.md`) :
- 1 : quand la science ne donne qu'un scénario parmi d'autres, l'affichage s'arrête avec la mention « inconnu » ;
- 2 : Mercure et Vénus avalées par le Soleil, spirale calculée ;
- 3 : la Terre, « sort inconnu » ;
- 4 : la fusion avec Andromède est gardée, marquée « scénario ».

Statuts : **mesuré** (observation), **calculé** (calcul de la page ou d'une publication à partir de mesures), **estimé** (ordre de grandeur publié, sans calcul ici), **choisi** (valeur posée à la main par l'assistant, qu'aucune source ne donne), **inconnu**.
Confiance : [Certain] vérifié dans le code ou sur la source (critique de vérité, 11 novembre 2026) ; [Probable] source connue, chiffre non relu ; [À vérifier].

Temps : en milliards d'années (Ga) à partir d'aujourd'hui, sauf mention.

## 1. Le Soleil

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Évolution (éclat, rayon, température, masse) | `SUN_TRACK`, `sunState` (25_future.js) | Interpolation entre les points de la table. 7 points sont marqués « * » (naissance, aujourd'hui, 7,13, 10,00, sommet des géantes rouges, fusion de l'hélium, sommet de la branche asymptotique) ; les autres « dessinent l'allure de la courbe » | calculé (points *) ; **choisi** (points intermédiaires) | Schröder et Smith 2008, MNRAS 386, 155 [Certain] — https://ar5iv.arxiv.org/html/0801.4031 | Fait (R5) : ligne « AGB tip-TP » ajoutée ; les 8 lignes de la table 1 sont vérifiées par `engulf.test.js` ; les points intermédiaires de la montée en géante sont remplacés par `DATA.SUN_RGB` (ligne suivante). Reste : marquer « interpolé » dans la fiche du Soleil |
| Montée en géante rouge (âge 10,00 à 12,167) | `DATA.SUN_RGB` (gen/sun_rgb.js, `pipeline/build_sun_rgb.py`) | Remplace les points intermédiaires choisis de `SUN_TRACK`, qui donnaient une masse négative avec la perte de masse publiée | calculé : forme du modèle MIST v1.2, 1 M☉, [Fe/H] = 0 (Choi et al. 2016 ; Dotter 2016), temps avant le sommet conservé, ancrage au sommet publié (2 730 L☉, 256 R☉), masse intégrée avec l'éq. 1 de Schröder et Smith ; la correction du rayon est calée pour retrouver la masse publiée au sommet (0,668 M☉) | Schröder et Smith 2008 ; MIST v1.2 | Fait (R5). Écart mesuré : seuil de survie calculé 1,015 UA (publié 1,15), Terre engloutie 0,05 Ma avant le sommet (publié environ 0,5 Ma) ; Mercure et Vénus 4,3 et 1,4 Ma avant le sommet (publié : 3,8 et 1,0 Ma avant la Terre) |
| Sommet de la branche des géantes rouges | `SUN_TRACK` âge 12,167 | Rayon 256 fois l'actuel, 2 730 fois plus lumineux, masse 0,668, dans 7,59 Ga | calculé | Schröder et Smith 2008 [Certain] | Gardé |
| Naine blanche | `SUN_TRACK` après 12,31 ; événement à 7,75 Ga | Masse finale 0,5405, rayon 0,0125 | masse finale calculée (publiée) [Certain] ; la date 7,75 Ga de l'événement ne correspond à aucun point « * » (fin de la branche asymptotique : âge 12,30, soit 7,72 Ga) [Certain] | Schröder et Smith 2008 | Fait (R7) : date tirée de la table (âge 12,30, soit 7,72 Ga) |
| Refroidissement de la naine blanche | `SUN_TRACK` de 12,4 à 60 | Points d'éclat et de température jusqu'à 60 Ga d'âge ; au-delà de 55,4 Ga d'aujourd'hui, la table se fige | **choisi** : aucune source citée [Certain] | — | Fait (R7) : loi de refroidissement de Mestel (1952), approchée (sans cristallisation), à partir de 0,1 Ga après la fin de la branche asymptotique ; entre 7,72 et 7,82 Ga, raccord interpolé (choisi) |
| « Le Soleil commence à enfler » | `dyn`, 5,42 Ga, écrit à la main | Événement | concorde avec `SUN_TRACK` (âge 10,0) mais la date est recopiée à la main [Certain] | Schröder et Smith 2008 | Fait (R7) : date tirée de la table (fin de séquence principale, âge 10,00, soit 5,42 Ga) |

## 2. Planètes

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Orbites qui s'élargissent | `F.orb = 1 / ss.M` (60_app.js, `step`) | Rayon multiplié par 1/M(Soleil) : perte de masse lente (invariant adiabatique) | calculé | Physique standard ; 1/0,5405 = 1,85 | Gardé |
| Mercure engloutie | `ENG.mercury = engulfTime(0.387)` ; rendu : effacée d'un coup (`F.eng`, 40_render.js) | Coupure à la date où le rayon solaire atteint 0,69 a/M | calculé, mais par un seuil calé à la main sur le résultat publié (survie au-delà de 1,15 UA), pas par la méthode de l'article | Schröder et Smith 2008 [Certain pour le seuil 1,15 UA] | Fait (R5) : spirale (marées et frottement), méthode de Schröder et Smith 2008 (`planetTide`) |
| Vénus engloutie | `ENG.venus` | Idem | idem | idem | Fait (R5) |
| Terre engloutie | `ENG.earth` ; repère « sort inconnu » depuis R2 | Effacée à la date calculée | **inconnu** : les études divergent | Engloutie : Schröder et Smith 2008 ; Rasio et al. 1996, ApJ 470, 1187 [Probable : la conclusion « probablement engloutie » est rapportée par Schröder et Smith ; le résumé ne la donne pas] — https://arxiv.org/abs/astro-ph/9605059. Pourrait survivre : Rybicki et Denis 2001, Icarus 151, 130 [Probable : confirmé par la citation de Schröder et Smith et par des sources secondaires] | Fait (R6) : la Terre suit son orbite calculée tant qu'elle s'élargit ; au moment où les marées commencent à la resserrer (`T_DIV`, 7,5868 Ga), coupure nette et panneau citant les trois études. `T_DIV` est un résultat du modèle de Schröder et Smith (marées qui l'emportent), pas un consensus. [À vérifier] l'orbite calculée atteint 1,22 fois l'actuelle à `T_DIV` ; l'article écrit qu'elle « dépasse à peine » 1 UA : à comparer à sa figure |
| Lune | suit la Terre (`F.eng.earth`) | Effacée avec la Terre | inconnu | — | Fait (R6) : même coupure que la Terre |
| Uranus, Pluton, Neptune, Mars, Saturne, Jupiter | `FATE_P = { uranus: 39, pluto: 40, neptune: 41, mars: 43, saturn: 45, jupiter: 95 }` | Chaque planète disparaît d'un coup à sa date | **choisi** : ordre et dates posés à la main. Zink et al. ne simulent que Jupiter, Saturne, Uranus et Neptune : Mars et Pluton sont des choix de l'assistant [Certain] | Zink, Batygin et Adams 2020, AJ 160, 232 : les étoiles de passage déclenchent une instabilité environ 30 Ga **après la fin de la perte de masse du Soleil** (§ III.3), soit vers 37,7 Ga d'ici ; éjections sur environ 10 Ga ; dernière planète en moyenne 100 Ga après la fin de la perte de masse (§ III.1) [Certain] — https://arxiv.org/abs/2009.07296 | Fait (R7) — coupé : `FATE_P` supprimé ; arrêt de tout le système solaire sur « inconnu » (R7) |
| Événements « Les planètes se dispersent » (38 Ga) et « Le Soleil n'a plus de planètes » (95 Ga) | `EV_RAW` | Textes | dates choisies pour coller à `FATE_P` [Certain] | Zink et al. 2020 | Remplacés par un événement « instabilité vers 30 Ga, ensuite inconnu » citant Zink et al. (R7) |
| Fin de l'affichage du système solaire | — (n'existe pas) | — | — | Aucune publication trouvée pour la borne « 10 Ga après la fin de la perte de masse » prévue dans R7 [Certain : recherche du critique de vérité ; piste non confirmée : Duncan et Lissauer 1998, Icarus 134, 303]. Seule date publiée : instabilité environ 30 Ga après la fin de la perte de masse (Zink et al. 2020), soit vers 37,7 Ga d'ici | Fait (R7) : orbites élargies jusqu'à 37,7 Ga, puis panneau « inconnu ». **Écart avec le « fini quand » de R7** (qui demandait le panneau dès +20 Ga) : on suit la seule date sourcée ; le test de R7 vérifie donc les orbites à +9 et +20 Ga, et le panneau à +50 et +100 Ga |
| Positions précises des planètes | `20_physics.js` : séries VSOP jusqu'à ±3 000 ans, puis calcul simplifié (transition de 3 000 à 4 000 ans) | Changement de modèle | calculé ; la page dit déjà qu'au-delà de 3 000 ans les positions « ne sont plus qu'indicatives » | Bretagnon et Francou (VSOP87) | Gardé |

## 3. Lunes et anneaux

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Phobos | `FATE.phobos = 0.04` (40 Ma) ; `m.off` ; événement « Mars perd Phobos » à 35 Ma | Effacé d'un coup à 40 Ma ; le texte dit « 20 à 50 Ma » | rapprochement **mesuré** ; fin **calculée** par l'étude : 20 à 40 Ma ; anneau ou impact : **inconnu**. Le texte (50 Ma) et les deux dates du code (35 et 40 Ma) sont faux ou incohérents [Certain] | Black et Mittal 2015, Nature Geoscience 8, 913, doi 10.1038/ngeo2583 [Certain] | Fait (R7) — coupé « inconnu : anneau ou impact entre 20 et 40 Ma » à 20 Ma, borne basse publiée ; texte corrigé (R7). La descente au rythme mesuré n'est pas dessinée : la position de Phobos reste celle de son orbite actuelle jusqu'à la coupure |
| Triton | `FATE.triton = 3.6` ; événement « Neptune détruit Triton » | Effacé d'un coup à 3,6 Ga | **inconnu** : l'étude donne deux dates selon l'état de rotation de Triton, environ 3,6 Ga ou environ 1,4 Ga, sans trancher [Certain] | Chyba, Jankowski et Nicholson 1989, A&A 219, L23 — https://ntrs.nasa.gov/citations/19890064536 | Fait (R7) — coupé « inconnu » à 1,4 Ga, en citant les deux dates (R7) |
| Anneaux de Saturne | `FATE.rings = 0.3` ; `F.ringsGone` ; événement à 300 Ma | Effacés d'un coup à 300 Ma | **estimé** : durée de vie au plus d'environ 292 Ma d'après la pluie d'anneau ; la borne de 100 Ma vient de l'apport mesuré par Cassini, pas de cet article ; contesté | O'Donoghue et al. 2019, Icarus 322, 251–260, doi 10.1016/j.icarus.2018.10.027 [Certain] | Fait (R7) — coupé : au-delà de 100 Ma, anneaux non dessinés avec « inconnu : au plus environ 300 Ma selon O'Donoghue et al. 2019 » (R7) |
| Autres lunes | `m.off` quand la planète mère est engloutie, ou avant −4,5 Ga | Effacées avec leur planète | suivent la planète | — | Suivent la règle de leur planète (R7) |

## 4. Petits corps et nuage d'Oort

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Astéroïdes, objets lointains, nuage d'Oort | `F.sysK = fadeOut(tG, 38, 42)` (40_render.js, `sysK`) | **Fondu** de 38 à 42 Ga | **choisi** ; fondu qui remplace un phénomène [Certain] | — | Fait (R7) — coupé : retiré ; ces corps s'arrêtent avec le système solaire sur « inconnu » (R7) |
| Naissance du système solaire (Soleil, planètes, orbites, ceintures, nuage d'Oort) | `F.sunAlive` (60_app.js) : fondu de −4,60 à −4,57 Ga | **Fondu** de 30 Ma | âge mesuré : 4,567 Ga (Connelly et al. 2012) ; fondu **choisi** [Certain] | Connelly et al. 2012, Science 338, 651 [Probable] | Fait (R7) : coupure nette à −4,567 Ga |
| Comètes du nuage d'Oort déviées par les étoiles qui passent | `oortInit`, `updateOort` | Orbites de Kepler et coups de vitesse | calculé | Bailer-Jones 2022, ApJL 935, L9 | Gardé |
| Voyager 1 : nuage d'Oort à +300 ans, traversée en 30 000 ans ; passage à 1,6 année-lumière de Gliese 445 à +40 000 ans | `EV_RAW` | Textes | estimé (NASA) pour le nuage d'Oort ; calculé (NASA/JPL) pour Gliese 445 | NASA (JPL) | Gardé |

## 5. Galaxies

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Grand Nuage de Magellan absorbé | `LMCO.tMerge` ; `F.lmcGone = smoothstep(tMerge, tMerge + 0.25, tG)` ; repère « fondue (calculé) » depuis R2 | Orbite calculée, puis **fondu** de 250 Ma qui l'efface ; la table (`lmcOrbit`) se fige après 10 Ga | orbite calculée ; date très dépendante de sa masse ; le fondu est **choisi** | Kallivayalil et al. 2013 ; Cautun et al. 2019, MNRAS 483, 2185 : fusion dans 2,4 Ga (de −0,8 à +1,2 Ga) [Certain] — https://arxiv.org/abs/1809.09116 | Recalculé : corps du calcul de la fusion (R8, R9) ; d'ici là, fondu remplacé par une coupure « scénario calculé », et « fin du calcul » au-delà de la table |
| Andromède : rencontre et fusion | `dynInit`, `dynAdvance` ; calcul plafonné à `tMerge + 3` ; table `andromedaOrbit` figée après 14 Ga | Calcul direct en retard sur l'horloge, puis figé | scénario **calculé** (décision 4) | Sawala et al. 2025, Nature Astronomy, doi 10.1038/s41550-025-02563-1 : environ une chance sur deux de fusion en 10 Ga [Certain] | Recalculé : calcul fait d'avance puis rejoué, « fin du calcul » au-delà (R8 à R11) |
| Galaxies lointaines qui sortent de vue | `dyn`, 60 Ga, écrit à la main | Événement | **choisi** : la date n'est pas calculée [Certain] ; Krauss et Scherrer 2007 donnent environ 100 Ga | Krauss et Scherrer 2007, Gen. Rel. Grav. 39, 1545 — https://arxiv.org/abs/0704.0221 [Certain] | Recalculé : date tirée de l'horizon calculé par la cosmologie de la page, comparée aux 100 Ga publiés |
| Galaxies naines du Groupe local | `lgStart`, `lgApply` : table de −2 à +12 Ga ; au-delà, elles restent au dernier point [Certain] | Orbites calculées puis figées | calculé jusqu'à +12 Ga | Pace 2024 | Au-delà de la table : « fin du calcul » au lieu de figer (R18) |
| Galaxies photographiées | `photo` : fondu de 5 à 20 Ma de part et d'autre d'aujourd'hui (`age`, 60_app.js) | La photo s'efface | la photo n'est vraie qu'aujourd'hui ; fondu **choisi** | Legacy Survey, DSS | Coupure avec mention « photo d'aujourd'hui » (R20) |

## 6. Étoiles, amas, ciel

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Naissance et mort de chaque étoile | `starLife` ; âges bornés à ±200 Ga | Place dans la vie tirée au hasard (toujours la même pour une étoile) | **modèle statistique** : âge réel inconnu ; dit dans la page et, depuis R2, dans le repère | — | Gardé comme modèle déclaré [hors lot A] |
| Bételgeuse | `STAR_FATE_OVERRIDE = { 27989: 0.1 }` ; événement à +100 000 ans | Explosion fixée à +100 000 ans | **estimé** (ordre de grandeur), dit tel quel | Joyce et al. 2020, ApJ, doi 10.3847/1538-4357/abb8db [Certain] | Gardé ; la fiche doit citer la source (absente du code) |
| Mouvement des étoiles | `starPositions` : ligne droite, puis orbite dans la galaxie (transition de 3 à 15 Ma) | Changement de modèle | calculé (vitesses mesurées) | — | Gardé |
| Amas, nébuleuses, objets du ciel profond | `still = fadeOut(|F.ty|, 3e6, 1.5e7)` (40_render.js) ; étiquettes `DATA.DEEP` | **Fondu** de 3 à 15 Ma | aucun mouvement calculé pour ces objets : fondu **choisi** | — | Coupure « position inconnue à cette date » (lot E) |
| Étoiles des tuiles Gaia | `nearT = fadeOut(|F.ty|, 3e6, 1.5e7)` | **Fondu** de 3 à 15 Ma | mouvement en ligne droite seulement : fondu **choisi** | Gaia DR3 | Coupure « hors du calcul » (lot E) |
| Figures des constellations | fondu de 30 000 à 120 000 ans | Les traits s'effacent | les figures sont celles d'aujourd'hui (convention) | Roman 1987 | Gardé, avec la mention « figures d'aujourd'hui » quand elles s'effacent |
| Panorama photographique de la Voie lactée | fondu de 300 000 à 2 millions d'années | La photo s'efface | la photo n'est vraie qu'aujourd'hui | ESO/S. Brunier | Gardé, avec la mention « photo d'aujourd'hui » |
| Étoiles qui frôlent le Soleil | `OO.enc`, `PASS_DUB` | Passages publiés | mesuré puis calculé | Bailer-Jones 2022 ; Dupuy et al. 2019 | Gardé |

## 7. Terre (hors orbite)

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Perte des océans | `dyn`, 1,1 Ga | Texte seulement | estimé : 1,1 Ga (+10 % d'éclat) vient de Kasting 1988 seul ; Wolf et Toon 2015 (JGR Atmospheres 120, 5775) placent l'effet de serre humide vers +12,5 % d'éclat, donc plus tard [Certain] | Kasting 1988 ; Wolf et Toon 2015 | Fait (R6) : texte avec les deux estimations, date réelle « inconnue » |
| Supercontinent à +250 Ma | `EV_RAW` | Texte | estimé (modèle publié) | Farnsworth et al. 2023 [Probable] | Gardé |
| Fin de la photosynthèse à +600 Ma | `EV_RAW` | Texte | estimé | Lenton et von Bloh 2001 [Probable] | Gardé |
| Éphémérides futures publiées (Voyager à un jour-lumière le 18/11/2026, éclipse du 02/08/2027, Apophis 2029, transit de Mercure 2032, Halley 2061, transit de Vénus 2117) | `EV_RAW` | Événements datés | calculé (sources publiées), recalculé par la page pour les éclipses | NASA, JPL | Gardé |

## Ce qui reste à décider

Aucune question pour Marc : les décisions 1 à 4 couvrent toutes les lignes. Un écart avec le plan est assumé et dit dans R7 : l'arrêt du système solaire se fait à la seule date publiée (instabilité environ 30 Ga après la fin de la perte de masse, soit 37,7 Ga d'ici, Zink et al. 2020), pas « 10 Ga après la fin de la perte de masse », borne qu'aucune publication trouvée ne donne.
