# Ce qui est fondamentalement faux dans l'appli PC, et l'architecture à viser (13 novembre 2026)

Demande de Marc : « quelque chose est fondamentalement faux, pas seulement des bugs isolés ». Ce document cherche la
cause commune aux symptômes du jour, propose une architecture cible et un plan de migration. **Aucun code n'est écrit.**

Code lu : branche `appli-pc`, commit `e20b55a` (`natif/`, `pipeline/fusion/`). Deux fils ont été fermés par Marc et
confiés à celui-ci ; leurs documents sont copiés à côté : `docs/audit-physique.md` (forces négligées) et
`docs/analyse-spirales.md` (Andromède, Triangle, Voie lactée). Le fil « Voir toute la Voie lactée » reste ouvert
(branche `galaxie-entiere`, non lue ici : je reprends ce qu'il a annoncé) et attend ce diagnostic avant de lancer son
grand calcul.
Labels : [Certain] lu dans le code ; [Probable] publié ou déduit, non remesuré ; [À vérifier] non mesuré.
Limite : rien n'a été lancé dans l'appli (carte graphique prise par l'appli de Marc et par le calcul en cours).

## 1. Le verdict en clair

Marc a raison. Les symptômes ne sont pas dix bugs : c'est **un seul défaut de conception, vu dix fois**.

> **L'appli n'est pas un simulateur. C'est un projecteur de calques.** À chaque image, `fenetre.cpp` superpose une
> douzaine de sources indépendantes (catalogues, formules, films calculés à l'avance), chacune avec son propre « aujourd'hui »,
> ses propres masses, son propre repère, et un **curseur d'opacité** qui dépend de la date. Il n'existe nulle part
> **un état physique unique** (positions, vitesses, masses de tout, à une date) que des lois font avancer.

Tant que c'est vrai, corriger un symptôme en fait apparaître un autre : chaque correction ajoute un calque ou un seuil.
C'est ce que font, de bonne foi, les trois fils en cours.

## 2. La preuve dans le code

### 2.1 Le temps est un mélangeur, pas une évolution [Certain]

Ce que `fenetre.cpp` décide à chaque image, calque par calque :

| Calque | Quand il est montré | Où |
|---|---|---|
| Étoiles mesurées (Gaia A, B, lumière additionnée, catalogue principal) | opacité `starShare()` : 1, puis fondu sur les 300 Ma avant le premier passage d'Andromède (4,64 Ga), 0 ensuite ; dans le passé, fondu de −0,8 à −1 Ga | `simulation.h:539`, `fenetre.cpp:610-632` |
| Lueur modèle de la Voie lactée | coupée en dur (`kShowModelledMilkyWay = false`) | `fenetre.cpp:266` |
| Traceurs mesurés des bras, tournés d'un bloc | pleins jusqu'à 200 Ma, éteints à 400 Ma | `traceurs_bras.h:37` |
| Voie lactée seule (film N-corps) | allumée de 200 à 400 Ma, multipliée par `starShare()` | `fenetre.cpp:561` |
| Étoiles de la fusion (autre film N-corps) | opacité `1 − starShare()` | `fenetre.cpp:559` |
| 10 000 scénarios | seulement dans le futur, vus de plus de 100 000 al | `clones.h:79` |
| Galaxies nommées du Groupe local | position mesurée fixe jusqu'à ±3 Ma, puis centre lu dans le film de la fusion ; **absentes dans le passé** et absentes si le film ne les contient pas | `simulation.h:533`, `603-625` |
| Galaxies des relevés | distance d'aujourd'hui multipliée par a(t), toutes pareil | `galaxies.h:151`, `fenetre.cpp:546` |

Chaque ligne est un passage de relais entre deux sources **qui ne se connaissent pas**. Les symptômes de Marc sont
exactement ces coutures :

- « La Voie lactée n'apparaît en entier qu'entre 200 et 400 Ma » : c'est la rampe `loneShare`.
- « La forme bascule d'un coup vers 1 Ga » : à 200 millions d'années par seconde, une rampe de 200 ou 300 Ma dure une
  seconde à une seconde et demie. Un fondu entre deux populations de points sans rapport se voit comme une bascule.
- « Le Nuage s'étire en arcs qui filent tout droit » : le calque des scénarios dessine une incertitude comme des astres.

Le dépôt a pourtant la bonne règle, écrite dans `CLAUDE.md` : « un fondu ne remplace jamais un phénomène ».
`fenetre.cpp` la viole cinq fois.

### 2.2 Sept Voies lactées différentes [Certain]

| # | Voie lactée | Sert à | Particularités |
|---|---|---|---|
| 1 | Étoiles Gaia mesurées (192 M avec distance) | l'image près d'aujourd'hui | une bulle autour du Soleil |
| 2 | Potentiel analytique figé (bulbe + disque Miyamoto-Nagai + halo NFW + barre) | faire tourner les étoiles | centre immobile, ne sent ni le Grand Nuage ni Andromède (`galaxie_orbites.h`) |
| 3 | Lueur modèle ajustée (`voie_lactee.bin`) | image d'ensemble | coupée, en cours de retour par le fil Voie lactée |
| 4 | Film « Voie lactée seule », 10,5 M de particules | image de 200 Ma à ~4 Ga | disque exponentiel AGAMA, sans rapport avec les étoiles Gaia |
| 5 | Voie lactée du film de la fusion, 3 M de particules | image après ~4,3 Ga | autre tirage, forme une barre où le Soleil-témoin part vers le centre (`groupe_local.h:10`) |
| 6 | Voie lactée des 10 000 scénarios | nuages d'incertitude | un point de 1,0 ± 0,2 × 10¹² M☉, **autre repère** : R0 = 8,122 kpc et Soleil à (12,9 ; 245,6 ; 7,78) km/s contre 8,2 kpc et (11,1 ; 242,24 ; 7,25) ailleurs (`groupe_local_clones.py`, `galaxie_orbites.h:24,36`) |
| 7 | Dessin mesuré des bras, tourné en bloc à 28,2 km/s/kpc | bras près d'aujourd'hui | un solide, alors que les étoiles (n° 2) tournent chacune à sa vitesse |

Même constat pour Andromède : 1,59 × 10¹² M☉ dans le film, 1,3 ± 0,4 dans les scénarios. Et pour l'issue : le film dit
« fusion à 5,44 Ga », les scénarios disent « médiane 6,5 Ga, 90 % ». Vers 5,5 Ga, l'écran peut montrer **une galaxie
déjà fusionnée et, par-dessus, des milliers de points où elle ne l'est pas**. Deux réponses contradictoires sur la même image.

### 2.3 Les étoiles et les galaxies ne vivent pas dans le même monde [Certain]

- Une étoile mesurée est un grain d'essai dans le potentiel figé n° 2. Elle n'attire rien (`orbites_pas.comp:5`) et ne
  sent ni le Grand Nuage, ni Andromède qui arrive.
- Les galaxies sont des films N-corps calculés à part, dont les particules ne sont **pas** les étoiles mesurées.
- Entre les deux : aucun échange. D'où le fondu au premier passage d'Andromède : les étoiles mesurées ne *peuvent pas*
  traverser la fusion, puisque leur monde ne contient pas Andromède. On les éteint et on allume autre chose.
- Les galaxies lointaines sont un troisième monde : un catalogue fixe multiplié par un nombre. Pas de vitesse propre,
  pas de structure liée, pas de cône de lumière (points 1, 2 et 10 de l'audit).

C'est la piste « échelles traitées par des moteurs incompatibles » : **confirmée**. Le problème n'est pas d'avoir
plusieurs moteurs (c'est inévitable), c'est qu'ils ne partagent ni état, ni masses, ni repère, ni frontière définie.

### 2.4 Aucun « aujourd'hui » cohérent [Certain]

- Le film de la fusion part de galaxies **mises à l'équilibre chacune seule**, puis posées à leur place d'aujourd'hui
  (`calcul.py`, `modeles.py`). Son instant zéro n'est donc pas notre ciel : pas de bras, pas de traînée du Grand Nuage,
  pas de Voie lactée déjà déformée par lui. Le vrai Nuage tombe depuis plus d'un milliard d'années ; celui du film
  naît intact à l'instant où Marc appuie sur lecture.
- Mesuré par le fil Andromède sur le calcul à 3 M de particules (`docs/analyse-spirales.md`) : à t = 0 les trois
  disques sont **parfaitement lisses** (force des bras 0,002, sous le bruit), puis **une barre pousse violemment entre
  0,1 et 0,5 Ga** (jusqu'à 0,4 à 0,5). Le départ n'est donc même pas en équilibre pour une galaxie seule. Et les
  paramètres d'Andromède sont faux : disque de 3,0 kpc au lieu de 5,3, bulbe quatre fois trop léger, 783 kpc au lieu
  de 761 ; Triangle incliné à 49° au lieu de 54 à 56° ; Petit Nuage de Magellan absent. [Certain pour les mesures du
  calcul, Probable pour les valeurs publiées]
- Les étoiles : deux tiers des vitesses radiales valent zéro (`gaia_convertir.py:203`). Ce n'est pas « mesuré », c'est
  un modèle, et le pire possible : l'étoile part dans une direction fausse dès la première seconde.
- Les amas et étoiles doubles n'ont pas de gravité interne : à l'équilibre dans la réalité, en chute libre dans l'appli.
- Dans le passé, les galaxies du Groupe local disparaissent au-delà de 3 Ma : le film ne commence qu'à zéro.

Piste « absence d'un état initial cohérent unique » : **confirmée**, c'est la cause directe de toutes les cassures à t = 0.

### 2.5 La règle « que du mesuré » : coupable, mais pas la racine [Certain]

Ce qu'elle a causé : la lueur de la galaxie coupée (d'où la bulle), les vitesses manquantes mises à zéro au lieu d'être
estimées, Andromède et le Triangle sans forme, et surtout **l'incertitude affichée à la place de l'objet** (les
10 000 scénarios).

Ce qu'il faut dire franchement : la règle n'a jamais été respectée, parce qu'elle ne peut pas l'être. Dès que le temps
bouge, tout est modèle. Elle a seulement poussé à cacher les modèles dans des valeurs par défaut (zéro, « fixe »,
« distance d'aujourd'hui ») qui sont des modèles faux présentés comme des mesures. Et même levée, comme depuis ce
matin, elle laisse l'architecture en calques intacte : **la lever ne suffit pas**.

### 2.6 Une incertitude n'est pas un astre [Certain]

Les scénarios sont utiles (c'est la meilleure science publiée : Sawala 2025, Wu 2026). Mais un ensemble statistique
n'est pas un état. Le dessiner avec le même pinceau que les étoiles, et recoller un scénario absorbé au centre en une
image (9 975 cas sur 10 000), fabrique de faux objets et de fausses vitesses (jusqu'à 2 400 km/s apparents).

### 2.7 D'où ça vient : la façon de construire [Probable, c'est mon diagnostic]

- L'appli est le portage d'une page web qui était une **visionneuse de catalogues avec une réglette de temps**. La
  structure a été gardée.
- Elle a été construite par une dizaine de fils en parallèle. Chaque fil a livré **son calque, son fichier, ses
  seuils, son essai « PASSE »**. `fenetre.cpp` les empile. L'architecture est la photo de l'organisation du travail.
- Les essais contrôlent chaque calque seul. **Aucun essai ne contrôle l'ensemble** : continuité d'un objet à travers
  le temps, masses identiques partout, un seul repère. Tout est vert et l'ensemble est incohérent.

C'est aussi ma responsabilité et celle des autres fils : on a optimisé « chaque pièce est sourcée », pas « l'univers
tient debout ».

## 3. Ce qui est sain et qu'on garde

Soyons justes, il y a beaucoup de solide [Certain, d'après les essais existants] :

- **Système solaire** : NASA DE440 au mètre, N-corps avec relativité au-delà, chaos montré. C'est le seul étage déjà
  bâti comme il faut : un état, une loi, une incertitude à part.
- **Cosmologie** : Friedmann avec énergie noire réglable, identique à astropy.
- **Rendu** : grande dynamique, Gaia complet (1,8 milliard de sources), tuiles, ciel par longueurs d'onde, surfaces.
- **Calcul sur la carte graphique** : intégrateur d'orbites (98 M d'étoiles, 27 ms le pas), arbre de gravité
  (`gravite_gpu.py`), modèles d'équilibre AGAMA, conservation de l'énergie à 0,11 % sur 10 Ga.
- **Toutes les données et leurs chaînes de fabrication**, l'indicateur « mesuré / calculé / précalculé / approché »,
  la complétude par échelle, la règle « même date = même image ».

Le défaut est dans **l'assemblage**, pas dans les pièces. C'est une bonne nouvelle : environ les deux tiers du travail
se réutilisent [Probable].

## 4. Ce qu'aucune architecture ne donnera (pour ne pas se mentir)

- **Un seul calcul de tout l'univers étoile par étoile est impossible.** La Voie lactée compte 100 à 400 milliards
  d'étoiles ; on en mesure 1,8 milliard, dont 192 millions avec distance. L'état unique sera forcément **hiérarchique**.
- **La place d'une étoile précise au-delà d'environ 100 Ma est imprévisible** (1,6 kpc d'écart mesuré par
  `essai_epicycles`, dû aux masses mal connues). On peut montrer *un avenir cohérent et réaliste*, pas *l'avenir*.
- **Les vrais bras spiraux dans 1 Ga sont imprévisibles.** Des bras qui naissent, se défont et se reforment, oui ; la
  carte exacte, non.
- **La fusion avec Andromède n'est pas certaine** (90 % selon Wu 2026). L'appli montrera un scénario de référence, et
  l'incertitude à part.
- **Sans gaz, pas de flambée d'étoiles ni de bras nets** comme sur les photos ; l'ajouter est un chantier en soi.

« Le plus proche possible de la réalité » veut donc dire : **un univers unique, cohérent, en équilibre, qui passe par
toutes les mesures d'aujourd'hui, et dont chaque partie non mesurée est le meilleur modèle publié, dit à l'écran.**

## 5. Architecture cible : un état unique, en étages

### 5.1 Le principe

Un **arbre de systèmes**. Chaque système est un ensemble de corps avec position, vitesse et masse dans le repère de
son parent. Le parent lui donne le champ extérieur (marées) ; lui donne au parent sa masse totale et son centre.
C'est la méthode publiée pour marier des moteurs d'échelles différentes en conservant l'énergie : le schéma « Bridge »
(Fujii et al. 2007), cœur de la boîte à outils AMUSE (Portegies Zwart et McMillan 2018) [Probable]. C'est aussi, en
plus rigoureux, ce que font Universe Sandbox ou Space Engine.

| Étage | Contenu | Loi | État de départ (aujourd'hui) |
|---|---|---|---|
| 0. Univers | facteur d'échelle a(t) | Friedmann avec énergie noire (existe) | Planck 2018, réglable |
| 1. Grandes structures | galaxies et groupes, position et **vitesse propre** | croissance des structures (approximation de Zel'dovich sur le champ Cosmicflows-4, déjà sur le PC) ; **un groupe lié ne grossit pas** | relevés + Cosmicflows-4 + catalogue de groupes (Tully 2015) ; vue « là où la lumière est partie » en option |
| 2. Groupe local | Voie lactée, Andromède, Triangle, Grand Nuage en particules ; naines | N-corps, **avec le terme d'énergie noire** | **un seul calcul parti du passé**, réglé pour passer par les positions et vitesses mesurées aujourd'hui |
| 3. Chaque galaxie | ses particules (disque, bulbe, halo) **et** les étoiles mesurées comme grains d'essai | les étoiles sentent **le champ du calcul de l'étage 2 à chaque date**, plus le potentiel figé | Gaia ; vitesse radiale manquante tirée de la dispersion locale (dit « modèle ») |
| 4. Systèmes d'étoiles | étoiles doubles, amas | orbite de Kepler (ORB6), gravité interne des amas | catalogues |
| 5. Système solaire | planètes, lunes, petits corps | DE440 puis N-corps (existe) | NASA |

### 5.2 Les cinq règles qui remplacent les calques

1. **Un objet, une histoire.** Chaque objet a une position *et* une vitesse à t = 0 et une seule loi le fait avancer,
   dans le passé comme dans le futur. Il n'apparaît ni ne disparaît, sauf s'il naît ou meurt.
2. **Jamais de fondu entre deux sources.** Le niveau de détail change la *représentation* de la même matière (étoiles
   une à une de près, leur lumière additionnée de loin), à lumière et masse conservées. Rien d'autre.
3. **Une seule table de constantes** (R0, vitesse du Soleil, masses, cosmologie) lue par tous les moteurs.
4. **Un grand livre des masses.** Par galaxie : masse liée + masse arrachée = constante ; ce que perd le Nuage, la Voie
   lactée le gagne, et la fiche l'affiche.
5. **L'incertitude se dessine comme une incertitude** (ellipse, fourchette, bouton), jamais comme des astres.

Et la pièce qui manque aujourd'hui : **ces règles deviennent des essais automatiques sur l'ensemble**. Exemple : « de
−1 Ga à +10 Ga, aucun objet ne saute de plus d'un pixel entre deux dates voisines, à aucune vitesse de défilement ».
Lancé aujourd'hui, cet essai échouerait à 3 Ma, 200 Ma, 400 Ma, 4,3 Ga et dans tout le passé.

### 5.3 Ce que ça règle, symptôme par symptôme

| Symptôme | Réglé par |
|---|---|
| Andromède et Triangle en nuages flous | étage 2 : ce sont des disques de particules dès aujourd'hui, à la bonne inclinaison ; scénarios sur bouton (règle 5). La qualité des bras dépend du fil « Andromède en vraie spirale » |
| Voie lactée entière seulement entre 200 et 400 Ma | règle 2 : la même galaxie de −2 Ga à +10 Ga, étoiles mesurées par-dessus |
| Bascule de forme vers 1 Ga | règle 1 : plus de relais entre films |
| Arcs du Nuage qui filent tout droit | règle 5, et étage 2 parti du passé : le Nuage arrive avec sa vraie traînée |
| Les étoiles ne s'attirent pas | étage 4, là où ça se voit (doubles, amas) ; ailleurs le champ moyen de la galaxie suffit |
| Vitesses radiales à zéro | étage 3 : tirées de la dispersion locale, dites « modèle » |
| Galaxies lointaines à leur distance actuelle ; amas qui gonflent | étage 1 |
| Énergie noire absente de la rencontre | étage 2 |
| Cassure quand on appuie sur lecture | règle 1 + départ dans le passé : aujourd'hui est un instant comme un autre du calcul |

## 6. Trois façons d'y aller

| | A. Continuer les rustines | **B. État unique en étages, par étapes (recommandé)** | C. Repartir d'un moteur existant |
|---|---|---|---|
| Quoi | chaque fil corrige son symptôme dans les calques | section 5, en gardant rendu, données, système solaire | AMUSE (calcul, sans affichage), Gaia Sky ou OpenSpace (affichage, sans dynamique), ou une simulation contrainte de l'univers local (HESTIA, SIBELIUS) |
| Pour | résultats visibles en heures | règle la cause ; chaque étape laisse l'appli utilisable ; ~2/3 réutilisé | méthodes éprouvées par des chercheurs |
| Contre | chaque rustine ajoute un calque et un seuil ; continuité et conservation ne seront **jamais** garanties ; on y est depuis deux jours | un à plusieurs gros calculs de carte graphique à refaire ; deux calculs en cours deviennent des essais et non des images ; discipline entre fils | aucun ne fait tout ; les simulations contraintes donnent « une galaxie qui ressemble », pas nos étoiles ; on perd l'appli actuelle |
| Verdict | à arrêter | **à faire** | à piller pour les méthodes (Bridge, conditions de départ), pas à adopter |

## 7. Plan de migration (option B)

Durées : je ne donne que ce qui est mesuré. Un calcul de 3 M de particules sur 10 Ga prend environ 9 h de carte
graphique, un de 10,5 M sur 4,7 Ga environ 18 h (annoncés par le fil physique). Le temps d'écriture : je ne sais pas
encore ; ce qui domine est le nombre de calculs à refaire à l'étape 2.

**Étape 0. Arrêter l'hémorragie et mesurer.** Plus aucun nouveau calque ni seuil de date dans `fenetre.cpp`. Écrire la
table unique de constantes. Écrire les essais d'ensemble (continuité, masses, repère) et les lancer sur l'appli
actuelle : la liste des échecs devient le tableau de bord. *Réutilise tout. Risque nul. Ne touche à aucun calcul en cours.*

**Étape 1. L'incertitude à sa place.** Scénarios sur bouton, dessinés en fourchette ; le film de référence et les
scénarios utilisent les mêmes masses et le même repère. *En partie fait par le fil Voie lactée.*

**Étape 2. Un seul calcul du Groupe local, parti du passé.** Méthode publiée pour le couple Voie lactée–Grand Nuage
(Vasiliev, Belokurov et Erkal 2021) [Probable] : remonter les orbites des centres dans le passé, relancer vers l'avant
avec toutes les particules et l'énergie noire, corriger le départ jusqu'à ce qu'aujourd'hui tombe sur les mesures.
Essais de réglage en basse résolution, puis un calcul final. Ce calcul doit aussi **écrire son champ de gravité à
chaque image** (développement en multipôles, format AGAMA) : c'est ce qui permet l'étape 3. Il remplace à la fois
« Voie lactée seule », « fusion » et les deux rampes. *Réutilise `calcul.py`, `gravite_gpu.py`, `modeles.py`, le
lecteur `fusion_nuage.h`. C'est la ligne « un seul calcul pour les 4 galaxies » déjà prévue par le fil Voie lactée :
**à spécifier selon ce document avant de la lancer**, sinon 9 à 18 h de carte seront à refaire.*

Cahier des charges de ce calcul, qui réunit ce que les fils fermés ou en attente ont trouvé :

1. **Énergie noire** : déjà branchée par le fil Voie lactée (16 % de la gravité Voie lactée–Andromède) [Certain selon ce fil].
2. **Départ dans le passé** : `depart_passe.py` du fil Voie lactée (2 Ga avant aujourd'hui) est la bonne base.
3. **Galaxies d'abord vieillies seules** jusqu'à avoir leur barre stable, puis posées sur leur orbite. Sans cela, la
   barre pousse pendant le film (mesuré). La Voie lactée est tournée pour que sa barre soit à 28° aujourd'hui.
4. **Paramètres mesurés** pour Andromède, le Triangle, le Grand Nuage ; **Petit Nuage ajouté**.
5. **Mêmes masses et même repère** que les scénarios d'incertitude.
6. **Champ de gravité écrit à chaque image**, et film couvrant le passé comme le futur.

**Les bras : la difficulté qu'il faut dire.** Deux exigences se contredisent. Partir du passé donne la continuité, mais
des bras posés il y a 2 Ga se sont effacés avant aujourd'hui. Poser les bras aujourd'hui d'après les vraies images
(proposition D du fil Andromède, la bonne) donne la vraie forme, mais pas d'histoire. Ma réponse : **deux populations
dans le même calcul**.
- La **masse** (vieilles étoiles, matière noire) vient du calcul parti du passé : elle porte l'orbite, la barre, la
  traînée du Nuage, la conservation.
- La **lumière des bras** (étoiles jeunes, gaz, poussière : quelques pour cent de la masse, presque tout le dessin)
  est tirée des vraies images **à t = 0**, avec la vitesse de rotation mesurée, puis suivie dans le champ du calcul
  **vers l'avant et vers l'arrière** depuis aujourd'hui. Aujourd'hui est le point d'ancrage ; il n'y a de cassure dans
  aucun sens. Les bras se déforment et s'enroulent peu à peu ; l'écran dit « forme mesurée aujourd'hui, calculée
  ailleurs, plausible au-delà de quelques centaines de Ma ».
- Le **gaz et la naissance d'étoiles** (proposition F) sont l'étape d'après : c'est le seul moyen d'avoir des bras qui
  se reforment et le vrai Courant magellanique. Nouveau moteur, plusieurs jours de calcul, durée non mesurée.

Les propositions du fil Andromède (1 : galaxies bâties sur les vraies images ; 2 : mêmes étoiles depuis un état
stable ; 3 : gaz ensuite) sont donc **reprises telles quelles**, à l'intérieur de cette étape. Elles attendaient le oui
de Marc ; elles l'attendent toujours, avec le reste du plan.

**Étape 3. Les étoiles mesurées dans ce même champ.** `orbites_pas.comp` lit le champ de l'étape 2 au lieu de
constantes figées. Les étoiles Gaia traversent alors la rencontre avec Andromède sans jamais s'éteindre ; `starShare`,
`loneShare`, `fusionShare` et le mélange ligne droite/orbite disparaissent. Vitesses radiales manquantes tirées du
modèle local. *Réutilise tout le calcul d'orbites sur la carte.*

**Étape 4. Systèmes liés.** Étoiles doubles sur leur orbite (ORB6, déjà téléchargé), amas tenus par leur gravité,
naines du Groupe local dans le calcul. *Priorité 1 de l'audit.*

**Étape 5. Grandes structures.** Vitesses propres (Cosmicflows-4), groupes liés qui ne gonflent pas, vue « là où la
lumière est partie ». *Priorité 2 de l'audit. Indépendante des étapes 2 à 4.*

**En parallèle, sans attendre** (étage déjà sain) : astéroïdes tirés par les planètes, rotation et précession de la
Terre, perte de masse du Soleil, raccords de la Lune (priorités 3 et 4 de l'audit).

**Étape 6. Démolition.** Retirer les calques remplacés. L'essai de continuité doit passer de bout en bout.

Les deux calculs en cours (« Voie lactée seule », « fusion-toutes ») : les laisser finir, ils servent de contrôle
(stabilité du disque, apparition de la barre). Ils ne seront plus l'image finale.

## 7 bis. Calculs beaucoup plus longs (demande de Marc, 13/11 : la précision d'abord, le temps n'est pas une limite)

Base de mesure : les deux calculs annoncés par le fil physique sur la RTX 5080 (3 M de particules, 10 Ga, environ 9 h ;
10,5 M, 4,7 Ga, environ 18 h) donnent **environ 0,35 h par million de particules et par milliard d'années** au pas de
0,25 Ma. Tout ce qui suit est une **estimation** tirée de ces deux points.

| Palier | Particules | Finesse | Durée de carte graphique | Place |
|---|---|---|---|---|
| Aujourd'hui | 3 M | 115 pc | 9 h | 6 Go |
| **1. Plafond du PC, gravité seule** | 30 M (dont ~10 M d'étoiles), de −2 à +10 Ga | ~50 pc, pas de 0,125 Ma | **10 à 11 jours**, plus 2 à 3 jours pour vieillir chaque galaxie seule avant, plus les essais de réglage (~2 h chacun à 3 M) | **~50 Go** : 36 Go d'images d'étoiles + 17 Go d'états complets, sur le Drive |
| 2. Avec gaz et naissance d'étoiles | à fixer par un essai | à fixer | **non mesurée** : semaines probables ; les codes publics (GADGET-4, GIZMO, SWIFT) tournent sur le processeur, sous Linux | non mesurée |
| 3. 100 M et plus | — | — | ne tient pas dans les 16 Go de la carte avec le code actuel [À vérifier] ; demanderait de réécrire le moteur ou de louer du calcul (payant, donc exclu) | — |

Ce qu'il faut savoir avant de dire oui au palier 1 :
- 30 M est le plafond estimé **appli fermée** (le calcul à 10,5 M prend 4,2 Go, l'appli ouverte 9 Go). Pendant ces
  jours, soit l'appli reste fermée, soit le calcul descend vers 15 M.
- Le calcul se met déjà en pause quand Marc joue ; la durée réelle sera donc plus longue que la durée de carte.
- Plus de particules ne corrige pas un mauvais départ. L'ordre reste : cahier des charges, galaxies vieillies seules,
  réglage en petit, **puis** le grand calcul. Sinon ce sont 10 jours perdus.
- Les autres calculs peuvent aussi s'allonger pour presque rien : scénarios d'incertitude (10 000 → 100 000), chaos du
  système solaire (32 copies sur 60 Ma → plus de copies, plus loin).
- 50 Go dépassent le seuil « prévenir avant » : **accord de Marc demandé** (le Drive a 20 To libres).

## 8. Recommandation

**Option B, en commençant par les étapes 0 et 2.** Le point le plus urgent n'est pas du code : c'est de **ne pas
lancer le prochain grand calcul avant d'avoir fixé son cahier des charges** (départ dans le passé, énergie noire,
constantes uniques, champ écrit à chaque image, mêmes masses que les scénarios). Et de donner à un seul fil la
responsabilité de l'état et de `fenetre.cpp`, les autres livrant des pièces qui respectent les cinq règles.

## 9. Ce que je n'ai pas vérifié

- Aucun essai lancé dans l'appli ; les sauts sont déduits du code, pas mesurés à l'écran.
- La taille du saut des galaxies nommées à ±3 Ma (position mesurée vers centre du film) [À vérifier].
- Les références (Bridge, Vasiliev 2021, Tully 2015) sont citées de mémoire, non relues aujourd'hui [Probable].
- Le coût en mémoire graphique du champ de gravité par image (étape 3) [À vérifier].
- Le nombre d'essais de réglage nécessaires à l'étape 2 [À vérifier] : c'est lui qui fixe la durée totale.
