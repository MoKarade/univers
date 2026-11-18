# Revue du code de l'appli PC : bugs, approximations cachées, améliorations (18 novembre 2026)

Demande de Marc (via le coordinateur) : relire le code (physique, intégrateurs, conservation de la masse et de
l'énergie, unités, précision numérique, rendu, performances), trouver les bugs, les approximations cachées et les
améliorations, les classer par impact sur le réalisme et sur la justesse. **Rien n'est corrigé ici** : les corrections
viendront en PR vers `appli-pc`, après accord de Marc.

Code lu : `appli-pc` au commit `5e649b7` (PR 101 fusionnée). La PR 102 (gaz, halo en rotation, fil du grand calcul)
est ouverte : ses fichiers ne sont pas relus en détail et rien n'y est proposé. Les fichiers du grand calcul
(`pipeline/fusion/`) appartiennent à ce fil : les points qui les touchent sont des propositions à lui transmettre.
Rien n'a été lancé sur la carte graphique ni dans l'appli : tout vient de la lecture du code et de calculs à la main
(section 8).

Labels : [Certain] lu dans le code ou calculé ; [Probable] déduit, ordre de grandeur ; [À vérifier] demande une mesure
ou un fichier que je n'ai pas lu. Les constats déjà listés dans `audit-physique` (13/11) et `revue-detaillee` (13/11,
branche `analyse-architecture`) ne sont pas répétés, sauf quand le code a changé depuis.

## 1. Résumé

Le cœur numérique est sain : intégrateur du système solaire, forces des potentiels, énergie noire, arbre de gravité,
cosmologie, conversions d'unités ; tout ce que j'ai recalculé tombe juste (section 7). **Les problèmes sont aux
coutures entre calculs**, là où le nouveau film du Groupe local (PR 100) a remplacé une partie seulement de l'ancien
monde :

1. **Deux Voies lactées superposées dans le futur.** Les 4 M étoiles du modèle suivent le film (calcul N corps, modèle
   McMillan 2017, barre à ~20 km/s/kpc), mais les 192 M étoiles Gaia continuent sur les orbites de référence (autre
   potentiel, barre à 39 km/s/kpc). Après ~100 Ma, les deux populations divergent de l'ordre du kpc. [Certain] code,
   [Probable] ampleur.
2. **Le Soleil n'est pas dans le film.** Quand le film mène, le Soleil suit le potentiel de référence pendant que ses
   voisines suivent le calcul N corps ; à la fusion (+6,8 Ga) il reste sur un cercle tranquille au milieu d'une galaxie
   détruite. [Certain]
3. **Les 38 naines suivent encore l'ancien calcul (`calcul.py`)**, alors qu'Andromède et les Nuages suivent le
   nouveau film : NGC 147, NGC 185, And III, V, VI, IC 10 et LGS 3 se détachent d'Andromède au fil du temps. [Certain]
   code, [Probable] dizaines à centaines de kpc à quelques Ga.
4. **Saut des galaxies voisines à t = 0.** Dans le futur, leur centre vient du film (place calculée, jusqu'à 10 à 25 kpc
   de la mesure selon le seuil du lanceur) ; dans le passé, des centres de référence (place mesurée). Aujourd'hui
   même, Andromède est montrée à sa place calculée. [Certain] code, [À vérifier] écarts réels dans `film.json`.
5. **Mouvement faux au centre de la Voie lactée entre deux images du film** : avec une image tous les 10 Ma, la courbe
   de Catmull-Rom ne suit plus une orbite sous ~1,5 kpc (rayon 39 % trop petit à mi-chemin à 1 kpc, absurde à 0,5 kpc).
   C'est le bulbe vu du Soleil. [Certain] calcul.
6. **Grand calcul : pas de temps fixe de 0,25 Ma**, environ 5 fois trop long pour les étoiles du bulbe à 100 pc
   (12 pas par tour) ; la collision des deux centres à la fusion est intégrée avec ce même pas. [Probable]
7. **Arbre de gravité sur la carte : lecture concurrente non protégée** dans la remontée (pas de `volatile` ni de
   lecture qui contourne le cache L1). Erreur rare et silencieuse possible sur la masse ou le centre d'un nœud.
   Correction d'une ligne. [Probable] risque, [À vérifier] effet.
8. **Performances quand le film mène** : à chaque pas d'un million d'années montré, l'appli décode et interpole
   4 M étoiles sur un seul cœur du processeur, puis envoie 128 Mo à la carte avec une allocation neuve et une attente
   complète. Vers 20 Ma par seconde, cela fait ~2,5 Go/s de transfert. [Certain] code, [Probable] chiffres.

Ce que je recommande de faire d'abord (détail en section 6) : **(a)** mettre le Soleil et les naines dans le film,
**(b)** faire suivre le film aux étoiles Gaia aussi (ou les éteindre quand le film mène), **(c)** raccorder les
centres à t = 0, **(d)** stocker les vitesses dans le film (Hermite au lieu de Catmull-Rom), **(e)** corriger la
remontée de l'arbre et compter les piles pleines. Les points (a), (d) et (e) touchent le grand calcul : à passer au fil
qui le fait tourner, pour le prochain film. [Probable : c'est l'ordre qui enlève le plus de faux à l'écran par heure
de travail]

## 2. Tableau des constats, par impact

Impact : **R** = réalisme (ce qui se voit de faux), **J** = justesse du calcul (nombres faux même si ça ne se voit pas
encore), **P** = performances. Gravité : grave / moyen / mineur.

| # | Grav. | Impact | Constat | Où | Confiance |
|---|---|---|---|---|---|
| F1 | grave | R | Étoiles Gaia (192 M) sur orbites de référence pendant que les étoiles du modèle suivent le film : deux galaxies, deux barres | `natif/src/fenetre.cpp:555`, `fenetre.cpp:577` | [Certain] code |
| F2 | grave | R | Soleil hors du film, sur le potentiel de référence | `fenetre.cpp:582`, `film_etoiles.h:105` | [Certain] |
| F3 | grave | R | Naines sur l'ancien calcul, grandes galaxies sur le nouveau : satellites d'Andromède détachés | `natif/src/simulation.h:651-657` | [Certain] code |
| F4 | grave | R, J | Centres des voisines : film (calculé) dès t = 0, référence (mesuré) avant : saut et place d'aujourd'hui fausse | `simulation.h:643` | [Certain] code |
| F5 | moyen | R | Catmull-Rom sur 10 Ma : orbites internes (< 1,5 kpc) faussées entre les images | `film_etoiles.h:88-101`, `lancer_rencontre.sh:49` | [Certain] calcul |
| F6 | moyen | R | Positions du film en nombres sur 16 bits : jusqu'à 3,9 pc d'erreur entre 8 et 16 kpc, 7,8 pc au-delà | `rencontre.py:556` | [Certain] |
| F7 | moyen | R | Entre −1 Ma et aujourd'hui, état du film à t = 0 prolongé à partir de −1 Ma : 1 Ma de décalage | `fenetre.cpp:577-578`, `gaia.vert:74` | [Probable] |
| F8 | mineur | R | Date maximale liée à l'ancien film : sans ses fichiers, le futur s'arrête à +3 Ma même si le nouveau film est là | `simulation.h:558` | [Certain] |
| N1 | moyen | J | Pas de temps fixe 0,25 Ma pour tout le Groupe local, bulbes et fusion compris | `rencontre.py:199` | [Probable] |
| N2 | moyen | J | Remontée de l'arbre : lecture des enfants sans garantie de cohérence mémoire | `gravite_gpu.py:75-80` | [Probable] risque |
| N3 | moyen | J | Pile pleine dans la descente de l'arbre : nœuds abandonnés sans le dire | `gravite_gpu.py:138` | [Certain] code, [Probable] jamais atteint |
| N4 | mineur | J, P | Étoiles visibles de 1 M☉ chacune dans le calcul (dit « sans masse ») et sources dans l'arbre | `rencontre.py:519` | [Certain] |
| N5 | mineur | J | Galaxies de départ : fonctions de distribution tirées dans un potentiel non auto-cohérent | `modeles_v2.py:155-197` | [Probable] |
| N6 | mineur | J | Modèle simple des centres (tirs de réglage) sans énergie noire ni frottement | `rencontre.py:249-269` | [Certain] |
| N7 | mineur | J | Repli « sphère de Plummer » du Petit Nuage non tronqué (particules jusqu'à ~450 kpc) | `rencontre.py:53-64` | [Certain] calcul |
| N8 | mineur | doc | Lanceur : « d'il y a 1 Ga » ; table : départ à −3 Ga | `lancer_rencontre.sh:22`, `cible_aujourdhui.json:130` | [À vérifier] |
| O1 | moyen | R | Barre de Dehnen sans hauteur : une étoile de halo à 20 kpc au-dessus du centre sent la barre comme dans le plan | `galaxie_orbites.h:84-89`, `orbites_pas.comp:39-47`, `gaia_acc.glsl:10` | [Certain] |
| O2 | moyen | P | Saut de grenouille « vitesse-position-vitesse » : 2 calculs de force par pas, 1 suffit | `orbites_pas.comp:58-63`, `galaxie_orbites.h:149-154` | [Certain] |
| O3 | mineur | J | Épicycles sur la carte sans énergie noire ; ceux du processeur l'ont | `orbite_galactique.glsl:34-35` | [Certain] |
| O4 | mineur | R | Deux modèles de Voie lactée : référence (type MWPotential2014) et calcul N corps (McMillan 2017) | `galaxie_orbites.h:24-25`, `univers.json` | [Certain] |
| O5 | mineur | J | Sous-pas choisis une fois à t = 0, sur l'énergie sans barre | `galaxie_orbites.h:137-144` | [Certain] |
| P1 | moyen | P | Film : interpolation de 4 M étoiles sur un seul cœur, 128 Mo envoyés à chaque pas, tampon de transfert alloué à chaque fois | `film_etoiles.h:95-104`, `gaia_orbites.h:223-231` | [Certain] code |
| P2 | moyen | P | Une seule image en vol, et chaque calcul d'orbites attend la fin de la carte (`vkQueueWaitIdle`) | `fenetre.cpp:474,707,767`, `commun.h:266` | [Certain] |
| S1 | mineur | J | Kepler : échec (orbite non liée) ignoré, le corps reste figé pendant le pas | `nbody_noyau.h:48,68` | [Certain], jamais atteint pour les planètes |
| S2 | mineur | J | Départ hors DE440 : vitesses recalées (facteur par planète), pas celles de la NASA | `systeme_solaire.cpp:58-77` | [Certain], documenté dans le code |
| T1 | moyen | J | Aucune physique native dans la CI GitHub, alors que les en-têtes de `natif/physique` sont portables | `.github/workflows/controles.yml:37` | [Certain] |

## 3. Constats en détail : film du Groupe local et appli

### F1. Deux Voies lactées dans le futur
Quand le film couvre la date, `milkyWayStars` (étoiles du modèle) reçoit ses états du film (`fenetre.cpp:577-589`).
Mais `gaia.advance(...)` (`fenetre.cpp:555`) continue d'avancer les 98 M + 94 M étoiles Gaia sur
`orbites_pas.comp`, c'est-à-dire dans le potentiel de `galaxie_orbites.h` : bulbe 0,5 × 10¹⁰, disque de
Miyamoto-Nagai 6,8 × 10¹⁰, halo NFW, barre de Dehnen à 39 km/s/kpc. Le film, lui, vient d'un modèle McMillan 2017
dont la barre tourne à ~20 km/s/kpc (`docs/deuxieme-film.md`, écart 1) et dont le disque s'épaissit et penche de 14°
en 5 Ga. Les deux calages donnent 232,8 km/s au Soleil, mais pas la même courbe de rotation ailleurs.
**Effet** : près du Soleil, Gaia domine (le contrat ne donne au modèle que ce qui manque) ; plus loin, le modèle domine.
Les deux tournent à des vitesses différentes, et la barre du modèle n'est pas la barre vue par Gaia. Au bout de
quelques centaines de Ma, des bras et des amas de Gaia se retrouvent à côté de ceux du modèle. [Certain] code ;
ampleur [Probable] : une différence de 5 km/s/kpc de vitesse angulaire à 5 kpc donne ~25° en 100 Ma.
**Correction proposée** : (1) au-delà du raccord (quelques Ma), éteindre progressivement Gaia quand le film mène et
laisser les étoiles du modèle (le film) porter toute la lumière, comme le prévoit le plan B+ ; ou (2) mettre les
étoiles Gaia brillantes dans le film comme traceurs (coût : 16 bits × 3 par étoile et par image). (1) est faisable
tout de suite, sans calcul. [Probable : recommandé]

### F2. Le Soleil n'est pas dans le film
`film_etoiles.h:105-107` ajoute le Soleil en dernier état avec la place donnée par l'appelant, et l'appelant
(`fenetre.cpp:582`) prend `sim.exact.position(0, y)`, c'est-à-dire l'orbite de référence. Le monde du simulateur est
centré sur le Soleil : tout le ciel vu d'ici dépend de cette place. À +5,6 Ga (premier passage d'Andromède à 14 kpc),
le vrai Soleil serait secoué ; celui de l'appli reste sur son cercle. [Certain]
**Correction proposée** : ajouter le Soleil comme traceur de la Voie lactée dans `etoiles_visibles_voie_lactee.npz`
(une étoile de plus, à sa place et sa vitesse mesurées), et le lire dans le film. Au prochain film. Pour celui qui
existe : prendre l'étoile du film la plus proche du Soleil à t = 0 (dans l'espace des phases) comme Soleil, dit
« modèle ». [Probable]

### F3. Les naines sont restées sur l'ancien calcul
`simulation.h:651-657` : toute galaxie qui n'est pas l'une des quatre grandes passe par `replay` (film de
`calcul.py`, 300 000 particules, ligne droite entre images de 20 Ma), relative au centre de la Voie lactée de CET
ancien calcul. Dans `conditions.json`, ces 38 traceurs comprennent sept satellites d'Andromède (NGC 147, NGC 185,
Andromeda III, V, VI, IC 10, LGS 3). Andromède, elle, suit le nouveau film (fusion à +6,75 Ga) ou les centres de
référence ; l'ancien calcul la faisait fusionner à 5,44 Ga avec Andromède à 785 kpc. Les satellites suivent donc une
autre Andromède. [Certain] code ; ampleur [Probable].
Les naines restent aussi des points sans masse dont certaines vitesses de départ sont du bruit (G5 de la revue du
13/11), et elles disparaissent dans le passé (`replay` ne couvre que le futur).
**Correction proposée** : ajouter les naines au grand calcul comme points sans masse (comme les étoiles visibles), ou,
au minimum, les recalculer comme particules test dans le champ en coefficients que le film écrit déjà
(`film/champ/*.npz`, `natif/physique/champ_bfe.h`, que l'appli ne lit pas encore). La deuxième option est légère et
peut couvrir le passé avec les centres de référence. [Probable]

### F4. Centres des voisines : saut à t = 0, place d'aujourd'hui calculée
`simulation.h:643` : `filmCovers(tGa) ? film->centre(...) : centres->centre(...)`. Le film commence à t = 0 avec la
place que le calcul donne aux galaxies ; le lanceur accepte l'arrivée si elle est à moins de 10 kpc (Andromède,
Triangle), 12 kpc (Grand Nuage) et 25 kpc (Petit Nuage) de la mesure (`lancer_rencontre.sh:39`). L'écart réel est
écrit dans `film.json` (`decalage_a_t0`) mais pas dans `film_index.bin`, donc l'appli ne peut pas le retirer.
Conséquences : (1) aujourd'hui, ces galaxies sont dessinées à leur place calculée, pas mesurée ; (2) en reculant d'un
instant, elles sautent à leur place de référence. Un écart de 12 kpc pour le Grand Nuage à 50 kpc, c'est ~14° sur le
ciel vu du Soleil. [Certain] code, [À vérifier] valeurs de `decalage_a_t0` du film installé.
**Correction proposée** : écrire `decalage_a_t0` dans l'index, et l'effacer progressivement dans l'appli (par exemple
sur 100 Ma) ; ou, mieux, resserrer les tirs jusqu'à quelques kpc avant le film suivant. Même logique pour les étoiles
de ces galaxies, qui sont rapportées à leur centre.

### F5. Catmull-Rom sur des images de 10 Ma
`film_etoiles.h:88-101` interpole chaque étoile par la courbe passant par quatre images. Pour un mouvement circulaire
échantillonné tous les θ = 2π × 10 Ma / P, le rayon à mi-chemin vaut (9/8) cos(θ/2) − (1/8) cos(3θ/2) du vrai rayon :

| Période (rayon approx.) | Rayon à mi-chemin |
|---|---|
| 150 Ma (~6 kpc) | 0,999 |
| 73 Ma (~2,6 kpc) | 0,988 |
| 40 Ma (~1,3 kpc) | 0,884 |
| 28 Ma (~1 kpc) | 0,61 |
| 15 Ma (~0,5 kpc) | −0,69 (l'étoile passe de l'autre côté) |

[Certain] calcul ; périodes [Probable], tirées de ~200 à 220 km/s au centre. Le centre « respire » à la cadence des
images, et la vitesse dérivée de la courbe est fausse de la même façon (elle sert à prolonger dans le pas de 1 Ma).
**Correction proposée** : écrire aussi la vitesse de chaque étoile (6 nombres au lieu de 3 : 50 → 100 Go pour un film
de 1 000 images) et interpoler par Hermite, comme pour les centres ; ou des images plus serrées seulement pour les
étoiles à moins de 2 kpc. Hermite sur 10 Ma tient ~1 % à 1 kpc. [Probable]

### F6. Nombres sur 16 bits
`rencontre.py:556` écrit les positions relatives en `float16` (11 bits de mantisse). Écart entre deux valeurs
représentables : 1,95 pc de 2 à 4 kpc, 3,9 pc de 4 à 8 kpc, 7,8 pc de 8 à 16 kpc, 15,6 pc de 16 à 32 kpc ; erreur
maximale : la moitié. Le Soleil est à 8,2 kpc : les étoiles du modèle autour de lui sont placées à ±3,9 pc près, et
leur place saute un peu d'une image à l'autre. `docs/premier-film.md` annonce « 0,1 pc d'écart » pour l'image 0 :
incompatible avec ce format pour des étoiles à 8 kpc [À vérifier : ce qui a été mesuré]. Marc veut voler entre les
étoiles : à 10 pc de distance, 4 pc se voient. [Certain] format, [Probable] visibilité.
**Correction proposée** : entiers sur 16 bits en virgule fixe (1 pc de pas sur ±32 kpc), avec une table à part pour
les rares étoiles arrachées au-delà ; même taille de fichier.

### F7. Entre −1 Ma et aujourd'hui
Le pas montré de −1 Ma à 0 a `tRaw ≈ −1,0 × 10⁻³ Ga > −2 × 10⁻³` : le film est pris (`fenetre.cpp:577`), à
`tStep = max(tRaw, 0) = 0`. L'état est celui de t = 0, mais `gaia.vert:74` le prolonge de `frac` × 1 Ma à partir du
début du pas (−1 Ma). Les étoiles du modèle sont donc décalées de 1 Ma de mouvement dans cet intervalle. [Probable :
lecture du code, non vu à l'écran]. Correction : ne prendre le film que si `tRaw >= 0`, ou extrapoler à rebours.

### F8. Date maximale
`simulation.h:558` : `maxYears = aujourd'hui + (replay ? replay->finGa() : 3 Ma)`. La fin du temps dépend de l'ancien
calcul, pas du nouveau film ; si les fichiers de l'ancien calcul sont retirés, le futur s'arrête à +3 Ma. [Certain]

## 4. Constats en détail : le grand calcul (fichiers du fil qui le fait tourner)

### N1. Pas de temps fixe
`rencontre.py:199` : `dt_ma = 0,25` pour toutes les particules. Adoucissement des étoiles : 0,1 × (36 000 / N)^(1/3)
kpc (`modeles_v2.py:157`), ~30 pc pour 1 M d'étoiles. Au centre du bulbe de McMillan (100 pc, ~200 km/s), une orbite
dure ~3 Ma : 12 pas par tour. Le critère usuel (GADGET : Δt = √(2ηε/|a|), η = 0,025) donne ~0,05 Ma : le pas est
~5 fois trop long dans les 300 pc centraux. Même chose pendant la collision des centres à la fusion. Le contrôle
d'énergie (0,04 %) est global et ne le voit pas, car ces particules pèsent peu. [Probable]
**Correction proposée** : pas par blocs (puissances de 2 de 0,25 Ma, choisis par particule sur √(ε/|a|)), ou au
minimum un tir de contrôle à 0,0625 Ma sur une galaxie seule pour mesurer ce que le pas change au bulbe et à la barre.
Un rapport de cause possible avec l'épaississement du disque n'est pas établi (le fil l'attribue à la barre, mesure à
l'appui).

### N2. Remontée de l'arbre sans garantie de cohérence
`gravite_gpu.py:72-99` : chaque fil écrit son nœud, `__threadfence()`, puis `atomicAdd` sur le parent ; le second
arrivé relit les enfants avec des lectures ordinaires (`com[4*L+3]`…). `__threadfence` garantit l'ordre d'écriture, pas
que le cache L1 du lecteur soit à jour ; sur les cartes récentes, les lectures globales passent par L1 par défaut.
Une ligne lue plus tôt par un autre fil du même multiprocesseur peut être périmée. La pratique (Karras 2012, Apetrei
2014) : pointeurs `volatile` ou `__ldcg()` pour ces lectures. Effet possible : masse, centre ou boîte d'un nœud
légèrement faux, rarement, sans message. [Probable] risque ; `test_gravite_gpu.py` compare à la somme directe sur un
échantillon, ce qui attrape un défaut systématique mais pas forcément un défaut rare. [À vérifier]
Correction : une ligne (lectures `__ldcg` ou `volatile`), sans changement de résultat attendu.

### N3. Pile pleine
`gravite_gpu.py:138` : `if (sp < 158)` sinon les deux enfants sont abandonnés, en silence (déjà signalé G14 le 13/11,
toujours là). La profondeur d'un arbre radix de codes de 63 bits reste sous ~90 sauf codes répétés en masse ; le cas
est donc improbable, mais rien ne le dirait. Correction : compter les abandons dans un entier atomique et l'écrire au
journal.

### N4. Étoiles visibles « sans masse » qui pèsent 1 M☉
`rencontre.py:519` donne `m = 1,0` à chaque étoile visible. Elles entrent dans l'arbre comme sources. Effet sur la
dynamique : ~4 × 10⁶ M☉ en tout, négligeable [Certain]. Mais l'en-tête dit « sans masse », et elles coûtent : l'arbre
porte quelques millions de feuilles de plus à chaque pas. Correction : `m = 0` (gratuit), ou mieux, cibles séparées
des sources dans `gravity()` (gain de temps [Probable] 10 à 30 %).

### N5. Galaxies de départ non auto-cohérentes
`modeles_v2.py:155-197` tire le halo, le bulbe et les disques avec des fonctions de distribution AGAMA dans le
potentiel analytique des disques (`type='Disk'`), mais la densité réellement produite par la fonction quasi-isotherme
n'est pas exactement ce disque. Il faudrait itérer (`agama.SelfConsistentModel`) pour un départ à l'équilibre.
Le mûrissement de 3 Ga absorbe ce défaut, mais il fait aussi naître le disque trop épais (écart 5 du deuxième film).
[Probable] Amélioration à tester sur une galaxie seule.

### N6, N7, N8
- `centres_simples` (`rencontre.py:249`) n'a ni énergie noire ni frottement : il ne sert qu'à deviner et corriger
  les tirs, donc il ralentit la convergence mais ne fausse pas le résultat. [Certain]
- La sphère de Plummer de secours (`rencontre.py:55`) n'est pas tronquée : sur 60 000 particules, la plus lointaine
  est vers a√(1,5 N) ≈ 450 kpc ; 6,5 % de la masse est au-delà de 7 kpc. Sert seulement si `petit_nuage.npz` manque
  (la table donne maintenant un modèle). [Certain]
- `lancer_rencontre.sh:22` écrit « d'il y a 1 Ga » ; la date de départ réelle est celle de `etat_combine.json`, la
  table dit −3 Ga. À aligner. [À vérifier]

## 5. Constats en détail : orbites des étoiles, système solaire, rendu

### O1. Barre sans hauteur
`galaxie_orbites.h:84-89` (et ses copies `orbites_pas.comp:39-47`, `gaia_acc.glsl:10-18`) applique la barre de
Dehnen 2000 avec le rayon cylindrique R seulement : une étoile à R = 1 kpc et z = 20 kpc sent la même force de barre
qu'une étoile du plan. Les étoiles du halo et du bulbe qui passent au-dessus du centre reçoivent des couples faux.
[Certain] Correction connue : Monari et al. 2016, Φ_b ∝ (R/r)² U(r) avec r sphérique (raccord identique dans le plan).
Impact [Probable] faible pour le disque, réel pour le halo.

### O2. Deux forces par pas au lieu d'une
`orbites_pas.comp:58-63` et `galaxie_orbites.h:149-154` font demi-coup de vitesse, pas de position, demi-coup de
vitesse : deux évaluations de la force par sous-pas. Le schéma « position-vitesse-position » (demi-pas de position,
coup de vitesse au milieu, demi-pas de position) est du même ordre, symplectique, avec **une seule** évaluation.
Gain attendu : ~2 fois sur le calcul des orbites des 192 M étoiles Gaia, donc sur la vitesse maximale du temps
(bridée à ~40 M étoiles-pas par image, `gaia_orbites.h:28`). [Certain] sur le nombre de forces, [Probable] sur le
gain réel. Il faudra refaire le contrôle `--controle-orbites` (le résultat change au second ordre).

### O3. Épicycles sur la carte sans énergie noire
`orbite_galactique.glsl:34-35` : `om2 = d1 / R`, sans le terme −K R que `galaxie_orbites.h:67-68` retire. Effet
numérique ~2 × 10⁻⁶ (négligeable), mais contraire à la règle « énergie noire jamais négligée » et au commentaire
« constantes identiques ». [Certain]

### O4, O5
- Deux modèles de Voie lactée cohabitent : potentiel de référence (`galaxie_orbites.h:25`, type MWPotential2014
  recalé) et modèle du calcul (`univers.json`, McMillan 2017). Ils donnent la même vitesse au Soleil, pas la même
  ailleurs. C'est la racine de F1. À terme : un seul (le champ en coefficients du film, `champ_bfe.h`). [Certain]
- Les sous-pas (1, 2, 8, 32) sont choisis une fois, sur l'énergie sans barre : une étoile que la barre fait plonger
  plus tard garde un pas trop long. [Certain] Impact faible.

### S1, S2 (système solaire)
- `nbody_noyau.h:48` : si l'orbite n'est pas liée, `kepler()` rend `false` et `step()` (`:68`) l'ignore : le corps ne
  bouge pas pendant le pas. Impossible pour les planètes et les quatre gros astéroïdes ; à protéger avant d'y mettre
  des comètes. [Certain]
- `systeme_solaire.cpp:58-77` : aux bornes 1550 et 2650, la vitesse de chaque planète est multipliée par un facteur
  calé pour retrouver la longitude DE440 400 ans plus loin. C'est voulu et commenté, mais la fiche dit « parti des
  éphémérides de la NASA » : c'est « parti de la place de la NASA, vitesse recalée ». [Certain]
- Le reste du système solaire (raccord direct/table, Lune, orientation) est déjà décrit le 13/11 (S1 à S10) ; le code
  n'a pas changé depuis sur ces points.

### P1. Le film coûte cher à chaque pas montré
Quand le film mène et que le temps défile, chaque nouveau pas d'un million d'années déclenche :
`decoded()` (conversion de 3 × 4 M nombres sur 16 bits, un seul cœur, `film_etoiles.h:123-144`) pour chaque nouvelle
image, puis `states()` (4 M étoiles × 3 axes × 8 produits, un seul cœur, `:95-104`), puis `setExternal` qui crée un
tampon de transfert, copie 128 Mo, envoie et attend (`gaia_orbites.h:223-231`), et la même chose pour les voisines.
À ~20 Ma par seconde : ~2,5 Go/s de transfert et des dizaines de ms de processeur par image. [Certain] code,
[Probable] chiffres.
**Correction proposée** : envoyer les 4 images brutes (16 bits) une fois chacune à la carte et faire l'interpolation
dans `gaia.vert` (déjà là pour les orbites) ; garder un tampon de transfert permanent.

### P2. Une seule image en vol, calculs synchrones
`fenetre.cpp:474` crée une seule barrière, attendue à chaque image (`:707`, `:767`) ; les calculs d'orbites passent par
`beginOnce`/`endOnce` qui finit par `vkQueueWaitIdle` (`commun.h:266`). Le processeur et la carte travaillent donc à
tour de rôle. Deux images en vol et les calculs d'orbites enregistrés dans le tampon de commandes de l'image
supprimeraient ces attentes. [Certain] structure, gain [Probable] 1,3 à 2 fois quand le temps défile.

### T1. Contrôles automatiques
`controles.yml:37` ne lance que les essais de la page web. Or `nbody_noyau.h`, `galaxie_orbites.h`, `champ_bfe.h`,
`systeme_solaire.cpp` sont du C++ portable (seuls `ephemeride.h` et `film_v2.h` utilisent des fonctions Windows :
`windows.h`, `_ftelli64`). Les essais `essai_galaxie`, `essai_champ_bfe`, `essai_film` pourraient tourner sous Linux
sur GitHub à chaque PR. [Certain] Recommandé avant les corrections ci-dessus, pour qu'elles soient contrôlées.

## 6. Ordre de correction proposé

| Étape | Points | Qui | Coût | Pourquoi d'abord |
|---|---|---|---|---|
| 1 | T1 | appli | ~½ jour | les corrections suivantes seront contrôlées à chaque PR |
| 2 | F1 (éteindre Gaia quand le film mène), F7, F8, O3 | appli | ~½ jour | ce qui ment le plus à l'écran, sans calcul |
| 3 | F4 (décalage à t = 0 dans l'index, effacé sur 100 Ma) | appli + 10 lignes du grand calcul | ~½ jour | saut visible aujourd'hui même |
| 4 | N2, N3, N4 | grand calcul | ~1 h | une ligne chacun ; avant le prochain film |
| 5 | F2, F3, F5, F6 (Soleil et naines dans le film, vitesses, virgule fixe) | grand calcul + lecteur | ~2 jours | au prochain film (format version 3) |
| 6 | P1, P2, O2 | appli | ~2 jours | vitesse du temps ×2 à ×4 [Probable] |
| 7 | N1, N5, O1 | grand calcul, orbites | essais sur une galaxie seule | justesse du centre et de la barre |

Options pour F1, avec le pour et le contre :
- **Éteindre Gaia au-delà de quelques Ma quand le film mène** : immédiat, cohérent (un seul calcul) ; on perd les
  étoiles mesurées dans le futur lointain, mais leur orbite de référence n'y valait déjà plus grand-chose. Recommandé.
- **Mettre les étoiles Gaia brillantes dans le film** : le plus juste ; coûte de la place (6 octets par étoile et par
  image) et un nouveau film.
- **Garder les deux** : rien à faire, mais deux galaxies superposées. Déconseillé.

## 7. Ce qui a été vérifié et tient

- Wisdom-Holman en coordonnées héliocentriques démocratiques : ordre des sous-pas, Kepler par l'anomalie excentrique
  (fonctions f et g), énergie de contrôle (`nbody_noyau.h`). [Certain]
- Relativité (premier ordre post-newtonien, vitesse héliocentrique tirée de la quantité de mouvement) et anneau
  Terre-Lune : formules redérivées, signes et facteurs justes. [Certain]
- Forces de Hernquist, Miyamoto-Nagai, NFW, barre de Dehnen (dans le plan) et énergie noire ; constantes de la carte
  recalculées : `OP_GMH` = 2 552 189,27, `OP_ABAR` = 796,849, `OP_BAR0` = 2,652900, `OP_BARW` = 39,88577,
  `K_lambda` = 0,00311179 (km/s)²/kpc². Toutes identiques au calcul en double. [Certain]
- Épicycles : rayon de guidage, intégrale exacte de Lz/R² (formule de l'anomalie excentrique). [Certain]
- Arbre de gravité : critère d'ouverture de Barnes 1994 (aucune particule ne se compte elle-même), quadripôle
  (potentiel et accélération redérivés), adoucissement combiné. [Certain]
- Énergie noire dans le grand calcul : poussée K (x − x_cm), énergie potentielle −K d²/2 comptée. [Certain]
- Tirage de Plummer (Aarseth, Hénon et Wielen 1974), Hernquist du Grand Nuage (normalisation M/(2πa³)), Q de Toomre
  (σ κ / 3,36 G Σ) et κ² = R dΩ²/dR + 4Ω². [Certain]
- Unités du film : Hermite des centres (Ga → kpc/(km/s) par 1,0227), pente de Catmull-Rom (kpc/Ga → km/s par
  0,9778). [Certain]
- Cosmologie : E(z) avec rayonnement et courbure, Simpson en ln(1+z), Runge-Kutta 4 pour a(t). [Certain]
- Reprise du grand calcul après un arrêt : journal et images tronqués au dernier instantané, pas d'image en double.
  [Certain]

## 8. Calculs

- Catmull-Rom, mouvement circulaire, points aux angles −θ, 0, θ, 2θ ; à u = ½ les poids valent (−1, 9, 9, −1)/16, d'où
  le rayon (9/8) cos(θ/2) − (1/8) cos(3θ/2).
- Pas du bulbe : a ≈ v²/r = 200²/0,1 = 4 × 10⁵ (km/s)²/kpc ; √(2 × 0,025 × 0,03 / 4 × 10⁵) ≈ 6 × 10⁻⁵ kpc/(km/s)
  ≈ 0,06 Ma, contre 0,25 Ma.
- 16 bits : écart entre valeurs = 2^(⌊log₂ x⌋ − 10) ; à 8 kpc, 2⁻⁷ kpc = 7,8 pc.
- Plummer : r = a / √(X^(−2/3) − 1) ; pour X = 1 − 1/N, r ≈ a √(1,5 N).
- Transfert du film : (4 M + 1) × 32 octets = 128 Mo par pas ; × 20 pas/s ≈ 2,6 Go/s.

## 9. Limites

- Rien n'a été lancé : ni l'appli, ni les essais, ni la carte graphique (consigne). Les effets à l'écran sont déduits
  du code.
- Je n'ai pas lu les fichiers du film installé (`C:\tmp\natif\groupe-local`), donc ni les `decalage_a_t0` réels, ni la
  date de départ réelle, ni le nombre de particules exact.
- La PR 102 (gaz, halo en rotation) n'est pas relue ; elle touchera N1 et N5.
