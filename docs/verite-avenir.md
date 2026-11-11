# Vérité de l'avenir lointain (tâche R4)

Inventaire de tout ce que la page fait changer à une date future fixée : disparitions, fondus, dates écrites à la main.
Pour chaque ligne : ce que fait le code aujourd'hui, son statut réel, la source, et ce qu'il devient (gardé, recalculé, ou coupé avec la mention « inconnu »).

Règles appliquées (décisions de Marc du 11 novembre 2026, `docs/plan-reel.md`) :
- 1 : quand la science ne donne qu'un scénario parmi d'autres, l'affichage s'arrête avec la mention « inconnu » ;
- 2 : Mercure et Vénus avalées par le Soleil, spirale calculée ;
- 3 : la Terre, « sort inconnu » ;
- 4 : la fusion avec Andromède est gardée, marquée « scénario ».

Statuts : **mesuré** (observation), **calculé** (calcul de la page ou d'une publication à partir de mesures), **estimé** (ordre de grandeur publié, sans calcul ici), **choisi** (valeur posée à la main par l'assistant, sans source qui la donne), **inconnu**.
Étiquettes de confiance : [Certain] vérifié dans le code de ce dépôt ; [Probable] source connue mais relue de mémoire ; [À vérifier] à confirmer sur la source avant tout code.

Temps : en milliards d'années (Ga) à partir d'aujourd'hui, sauf mention.

## 1. Le Soleil

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Évolution (éclat, rayon, température, masse) | `SUN_TRACK`, `sunState` (25_future.js) | Interpolation entre des points de la table ; 10 points marqués « * » sont les valeurs publiées, les autres « dessinent l'allure de la courbe » | calculé (points *) ; **choisi** (points intermédiaires) | Schröder et Smith 2008, MNRAS 386, 155 [Probable] | Gardé. R5 : comparer chaque point « * » à la table 1 de l'article [À vérifier] ; les points intermédiaires sont dits « interpolés » dans la fiche du Soleil |
| Sommet de la branche des géantes rouges | `SUN_TRACK` âge 12,167 | Rayon 256 fois l'actuel, 2 730 fois plus lumineux, masse 0,668, dans 7,59 Ga | calculé | Schröder et Smith 2008 [Probable] | Gardé |
| Naine blanche | `SUN_TRACK` après 12,31 ; événement à 7,75 Ga | Masse finale 0,5405, rayon 0,0125 | calculé (masse finale) ; la date 7,75 Ga de l'événement ne correspond à aucun point « * » (fin de la branche asymptotique : âge 12,30, soit 7,72 Ga) [Certain, d'après le code] | Schröder et Smith 2008 | Recalculé : la date de l'événement doit venir de `SUN_TRACK` (R7) |
| Refroidissement de la naine blanche | `SUN_TRACK` de 12,4 à 60 | Points d'éclat et de température jusqu'à 60 milliards d'années d'âge | **choisi** : aucune source citée pour ces points [Certain, d'après le code] | — | Recalculé avec une courbe de refroidissement publiée, ou coupé « inconnu » au-delà de la dernière valeur sourcée (R7) |

## 2. Planètes

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Orbites qui s'élargissent | `F.orb = 1 / ss.M` (60_app.js, `step`) | Rayon d'orbite multiplié par 1/M(Soleil) : perte de masse lente (invariant adiabatique) | calculé | Physique standard ; le facteur 1/0,5405 = 1,85 est celui de R7 | Gardé |
| Mercure engloutie | `ENG.mercury = engulfTime(0.387)` ; rendu : planète effacée d'un coup (`F.eng`, 40_render.js) | Coupure nette à la date où le rayon solaire atteint 0,69 a/M | calculé, mais par un seuil calé à la main sur le résultat publié (survie au-delà de 1,15 UA), pas par la méthode de l'article | Schröder et Smith 2008 [Probable] | Recalculé : spirale (marées + frottement), méthode de Schröder et Smith 2008 (R5) |
| Vénus engloutie | `ENG.venus` | Idem | idem | idem | Recalculé (R5) |
| Terre engloutie | `ENG.earth` ; repère « sort inconnu » depuis R2 | Effacée à la date calculée | **inconnu** : les études divergent | Engloutie : Schröder et Smith 2008 ; Rasio et al. 1996, ApJ 470, 1187 [Probable]. Rescapée : Rybicki et Denis 2001, Icarus 151, 130 [Probable] | Coupé « inconnu » au moment où les études divergent, avec les trois références (R6) |
| Lune | suit la Terre (`F.eng.earth`) | Effacée avec la Terre | inconnu | — | Même coupure que la Terre (R6) |
| Uranus, Pluton, Neptune, Mars, Saturne, Jupiter | `FATE_P = { uranus: 39, pluto: 40, neptune: 41, mars: 43, saturn: 45, jupiter: 95 }` | Chaque planète disparaît d'un coup à sa date | **choisi** : ordre et dates posés à la main. Mars n'est pas dans les simulations citées : 43 Ga est un choix de l'assistant [Certain, vérifié avant R4] | Zink, Batygin et Adams 2020, AJ 160, 232 : première éjection vers 30 Ga en moyenne, dissolution vers 100 Ga, ordre non certain [Probable] | Coupé : `FATE_P` supprimé ; arrêt de tout le système solaire sur « inconnu » (R7) |
| Fin de l'affichage du système | — (n'existe pas) | — | — | R7 : 10 Ga après la fin de la perte de masse du Soleil, borne de stabilité publiée [À vérifier : quelle publication donne cette borne] | Créé en R7 : panneau « inconnu » |

## 3. Lunes et anneaux

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Phobos | `FATE.phobos = 0.04` (40 Ma) ; `m.off` (60_app.js) ; événement « Mars perd Phobos » à 35 Ma | Phobos effacé d'un coup à 40 Ma | rapprochement **mesuré** (environ 1,8 cm par an) ; date de la fin **calculée** par les études (20 à 50 Ma) ; anneau ou impact : **inconnu** | Black et Mittal 2015, Nature Geoscience 8, 913 [Probable] ; deux dates différentes dans le code (35 et 40 Ma) [Certain] | Recalculé : orbite de Phobos qui descend au rythme mesuré jusqu'à la limite de Roche ; ensuite « inconnu : anneau ou impact » (R7) |
| Triton | `FATE.triton = 3.6` ; événement « Neptune détruit Triton » | Effacé d'un coup à 3,6 Ga | calculé par la publication (désintégration par les marées), avec une large incertitude | Chyba, Jankowski et Nicholson 1989, A&A 219, L23 [Probable ; fourchette à vérifier] | Gardé comme date publiée, mais disparition remplacée par une coupure « détruit par les marées (calculé, Chyba et al. 1989) » dans le repère ; pas de fondu (R7) |
| Anneaux de Saturne | `FATE.rings = 0.3` ; `F.ringsGone` ; événement à 300 Ma | Anneaux effacés d'un coup à 300 Ma | **estimé** à partir d'un débit de « pluie d'anneau » mesuré ; durée de vie contestée (100 à 300 Ma) | O'Donoghue et al. 2019, Icarus 322, 1 [Probable] | Coupé : après 100 Ma (borne basse publiée), anneaux non dessinés avec la mention « inconnu : 100 à 300 Ma selon O'Donoghue et al. 2019 » (R7) |
| Autres lunes | `m.off` quand la planète mère est engloutie, ou avant −4,5 Ga | Effacées avec leur planète | suivent la planète | — | Suivent la règle de leur planète (R7) |

## 4. Petits corps et nuage d'Oort

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Astéroïdes, objets lointains, nuage d'Oort | `F.sysK = fadeOut(tG, 38, 42)` ; rendu `sysK` (40_render.js) | **Fondu** de 38 à 42 Ga | **choisi** ; c'est un fondu qui remplace un phénomène [Certain] | — | Coupé : retiré ; ces corps s'arrêtent avec le système solaire sur « inconnu » (R7) |
| Comètes du nuage d'Oort déviées par les étoiles qui passent | `oortInit`, `updateOort` | Orbites de Kepler et coups de vitesse à chaque passage | calculé (passages publiés : Bailer-Jones 2022) | Bailer-Jones 2022, ApJL 935, L9 | Gardé |

## 5. Galaxies

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Grand Nuage de Magellan absorbé | `LMCO.tMerge` ; `F.lmcGone = smoothstep(tMerge, tMerge + 0.25, tG)` ; repère « fondue (calculé) » depuis R2 | Orbite calculée, puis **fondu** de 250 Ma qui l'efface | orbite calculée (vitesse mesurée) ; date de fusion très dépendante de sa masse ; le fondu est **choisi** | Kallivayalil et al. 2013 ; Cautun et al. 2019, MNRAS 483, 2185 (fusion vers 2,4 Ga) [Probable] | Recalculé : le Nuage est un corps du calcul de la fusion (R8, R9) ; d'ici là, le fondu est remplacé par une coupure « scénario calculé » |
| Andromède : rencontre et fusion | `dynInit`, `dynAdvance` ; calcul plafonné à `tMerge + 3` (`S.dynT`) | Calcul direct en retard sur l'horloge, puis figé | scénario **calculé** (décision 4) ; le plafond fige l'image | Sawala et al. 2025, Nature Astronomy : environ une chance sur deux de fusion en 10 Ga [À vérifier] | Recalculé : calcul fait d'avance puis rejoué (R8 à R11) |
| Galaxies lointaines qui sortent de vue | événement à 60 Ga ; horizon de la cosmologie | Calcul de l'expansion (équations de Friedmann) | calculé | Krauss et Scherrer 2007 [Probable] | Gardé |
| Galaxies naines du Groupe local | `lgStart`, `lgApply` : table de −2 à +12 Ga | Orbites calculées ; au-delà de +12 Ga, elles restent au dernier point [À vérifier dans le code] | calculé jusqu'à +12 Ga | Pace 2024 | À vérifier en R18 : au-delà de la table, dire « fin du calcul » au lieu de figer |

## 6. Étoiles

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Naissance et mort de chaque étoile | `starLife` (25_future.js) | Place dans la vie tirée au hasard (toujours la même pour une étoile) | **modèle statistique** : âge réel inconnu ; c'est dit dans la page et, depuis R2, dans le repère | — | Gardé comme modèle statistique déclaré. À reprendre plus tard : ne pas faire mourir à une date précise une étoile dont l'âge n'est pas mesuré [hors lot A] |
| Bételgeuse | `STAR_FATE_OVERRIDE = { 27989: 0.1 }` ; événement « explose » à 100 000 ans | Explosion fixée à +100 000 ans | **estimé** (ordre de grandeur), dit tel quel dans l'événement | Joyce et al. 2020, ApJ 902, 63 (environ 100 000 ans avant l'explosion) [Probable] | Gardé comme ordre de grandeur ; la fiche doit citer la source (aujourd'hui sans référence dans le code) |
| Étoiles qui frôlent le Soleil | `OO.enc`, `PASS_DUB` | Passages publiés | mesuré puis calculé | Bailer-Jones 2022 ; Dupuy et al. 2019 | Gardé |

## 7. Terre (hors orbite)

| Quoi | Code | Ce que fait la page | Statut | Source | Devenir |
|---|---|---|---|---|---|
| Perte des océans | événement à 1,1 Ga | Texte seulement, rien ne change à l'écran | estimé, dit « Estimation » | Kasting 1988 ; Wolf et Toon 2015 [Probable] | Gardé |

## Ce qui reste à décider

Aucune question pour Marc : les décisions 1 à 4 couvrent toutes les lignes. Deux points sont des recherches, pas des choix :
- la borne « 10 Ga après la fin de la perte de masse » de R7 doit être rattachée à une publication ; sinon l'arrêt se fera à la première date publiée d'instabilité (Zink et al. 2020) ;
- la fourchette de Triton et la table 1 de Schröder et Smith 2008 doivent être relues sur les articles avant R5 et R7.
