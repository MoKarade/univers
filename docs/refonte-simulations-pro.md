# Comment font les simulations professionnelles, et le plan de refonte de l'appli PC (13 novembre 2026)

Demande de Marc (13/11, 18 h 13 UTC) : « ça marche pas du tout, rien du tout, collision marche pas, étoiles non plus,
fais une longue veille sur comment les simulations professionnelles fonctionnent et propose un plan ».

Ce document : **une veille sourcée** (simulations scientifiques, logiciels de visualisation, raccord entre calcul à
l'avance et lecture en temps réel), **une comparaison** avec l'appli telle qu'elle est sur `appli-pc` (commit
`b08ef01`), et **un plan de refonte** par étapes vérifiables, avec options, recommandation, effort et charge de carte
graphique. **Aucun code n'est écrit.**

Il prolonge `docs/analyse-architecture.md` (PR 90), dont je partage le diagnostic. Ce qu'il ajoute : ce que les pros
font concrètement à chaque endroit où l'appli casse, et un plan qui en découle pièce par pièce.

Labels : [Certain] lu dans le code ou dans le texte d'un article ce jour, ou calculé ici ; [Probable] publié, lu dans
un résumé ou cité de mémoire avec une source connue ; [Supposition] mon raisonnement ; [À vérifier] non vérifié.

---

## 0. En bref

1. **Personne, chez les pros, ne fait ce que fait l'appli** : passer d'une source à une autre selon la date avec un
   fondu. Partout, il y a **une seule matière** (des particules) qui évolue par **une seule loi**, et **plusieurs façons
   de la dessiner** selon la distance. La forme ne peut pas basculer, parce que c'est la même matière. [Probable]
2. **La collision ne marche pas** parce que l'appli n'a pas de Voie lactée ni d'Andromède *aujourd'hui* : elle a des
   étoiles Gaia (une bulle de quelques kpc), des nuages de scénarios, et un film N-corps qui ne commence vraiment
   qu'à la rencontre. Les pros partent de **galaxies en équilibre, construites sur les mesures**, et les font
   évoluer **d'un seul calcul**. [Certain pour l'appli, `docs/etat-des-lieux-1311.md`]
3. **Les étoiles ne marchent pas** parce que 192 M d'étoiles mesurées autour du Soleil ne font pas une galaxie vue de
   loin (on voit « un trait »). Les logiciels pros (OpenSpace, SpaceEngine, Gaia Sky) **ajoutent toujours un modèle
   pour la lumière non mesurée**, et le cachent là où le catalogue est complet. [Certain pour OpenSpace et SpaceEngine,
   d'après leur documentation]
4. **Recommandation : option B+** (section 6). Un **squelette dynamique unique** (un calcul N-corps du Groupe local
   parti du passé, avec énergie noire, réglé pour tomber sur les mesures d'aujourd'hui), **écrit sous deux formes** :
   les particules d'étoiles (pour le dessin) et le **champ de gravité compressé** (pour faire bouger les étoiles Gaia
   dans le même monde). Puis **un seul moteur de dessin à trois niveaux** (étoiles une à une, points, volume) qui lit
   ces mêmes particules.
5. Coût estimé [Supposition, extrapolé des calculs déjà faits] : **environ 3 à 5 jours de carte graphique** au total
   pour la version à 10 M de particules, **25 à 50 Go** de stockage (accord de Marc requis), et **une dizaine
   d'étapes de travail** de fil. Première image « une galaxie entière qui ne change pas de forme en appuyant sur
   lecture » : après l'étape 4, sans attendre le grand calcul.

---

## 1. Le constat, en une page

Je ne refais pas l'analyse de la PR 90 ; je la résume avec ce que j'ai relu.

| Symptôme de Marc | Cause dans le code | Où |
|---|---|---|
| « La collision ne marche pas » | Andromède n'existe comme galaxie qu'entre ~4 et 6 Ga ; avant, ce sont 10 000 scénarios (un trait, une boule, un brouillard) ; le film part de galaxies **instables** (Q ≈ 0,7, barre violente entre 0,1 et 0,5 Ga) et **s'arrête à 5,98 Ga** | `docs/etat-des-lieux-1311.md` ; `docs/revue-detaillee.md` G1–G5 ; `docs/continuite-1311.txt` [Certain] |
| « Les étoiles ne marchent pas » | Vue de loin, seule la bulle Gaia est dessinée (la lueur modèle est coupée : `kShowModelledMilkyWay = false`, `fenetre.cpp:266`) ; les étoiles s'éteignent avant 4,64 Ga (`starShare`) et avant −1 Ga ; les deux tiers n'ont pas de vitesse radiale (prise nulle) | `fenetre.cpp:266`, `:630-650` ; `simulation.h` [Certain] |
| Changement de forme quand on lance la lecture | sept Voies lactées différentes, reliées par des fondus de 200 à 300 Ma (`starShare`, `loneShare`, `fusionShare`) | `fenetre.cpp:308-315`, `:577-585` [Certain] |
| Le passé est vide | le film commence à t = 0 ; les galaxies nommées disparaissent avant −3 Ma | `continuite-1311.txt` : 29 cassures [Certain] |

Le travail en cours ailleurs, que je ne touche pas :
- **branche `modeles-depart`** (fil « Trouver ce qui est fondamentalement faux ») : modèles de départ v2 pris dans
  les articles (McMillan 2017, Tamm 2012, Blaña Díaz 2018, Corbelli 2014, Kam 2017…), **stables** sur 2 Ga
  (déformation 0,02 à 0,06 au lieu de 0,4–0,5), mais **sans barre** pour l'instant. C'est exactement l'étape 1 du
  plan ci-dessous : bonne direction. [Certain, `docs/parametres-galaxies.md` de cette branche]
- **PR 93 et 94** (fil « Montrer la Voie lactée entière ») : galaxie entière dès t = 0 et photos des voisines. C'est
  une amélioration de l'écran d'aujourd'hui ; elle ne règle pas l'évolution. Ce plan la reprend à l'étape 6.

---

## 2. Veille A : comment les chercheurs simulent les galaxies

### 2.1 Les galaxies de départ : toujours en équilibre, toujours construites sur des mesures

Un calcul N-corps ne vaut que ce que vaut son départ. Tous les groupes utilisent un **générateur de conditions
initiales en équilibre** :

| Outil | Méthode | Référence |
|---|---|---|
| **MakeNewDisk** | disque exponentiel + bulbe + halo ; vitesses tirées des équations de Jeans dans le potentiel total | Springel, Di Matteo et Hernquist 2005 (MNRAS 361, 776) ; utilisé dans les fusions de galaxies de Hernquist et Springel [Probable, de mémoire] |
| **GalIC** | itératif : on tire des vitesses, on intègre les orbites dans le potentiel cible, on garde les changements qui rapprochent la densité moyennée dans le temps de la cible ; donne des disques à vitesses réalistes « stables pour des modèles composés » | Yurin et Springel 2014, MNRAS (DOI 10.1093/mnras/stu1421) [Certain, résumé lu] |
| **AGAMA** | fonctions de distribution en variables d'action ; construit des modèles **auto-cohérents** à plusieurs composantes ; prépare des conditions initiales N-corps ; calcule le potentiel d'un profil ou d'un instantané N-corps ; C++ avec interface Python ; couplé à AMUSE, galpy, NEMO | Vasiliev 2019, MNRAS 482, 1525 [Certain, résumé lu] |
| GalactICS, DICE, MAGI | autres générateurs (fonctions de distribution analytiques, ou sur carte graphique pour MAGI) | [Probable, de mémoire] |

Ce qui compte pour nous [Probable] :
- **L'équilibre ne suffit pas, il faut la stabilité** : paramètre de Toomre Q > ~1,5 dans le disque, halo et disque
  calés sur la **même** courbe de rotation. C'est exactement l'erreur des modèles actuels (Q ≈ 0,7), que la branche
  `modeles-depart` corrige.
- **Les barres et les bras ne se posent pas, ils naissent.** Les études de la Voie lactée font d'abord évoluer la
  galaxie seule jusqu'à une barre stable, puis choisissent l'instant où la barre a le bon angle. Portail et al. 2017,
  source de la barre de l'appli (39 km/s/kpc, 28°), vont plus loin : ils **ajustent les poids des particules** d'un
  modèle N-corps barré pour qu'il reproduise les comptages d'étoiles mesurés (méthode « made-to-measure », Syer et
  Tremaine 1996). [Probable : méthode citée de mémoire, valeurs lues dans `parametres-galaxies.md`]

### 2.2 Les moteurs de gravité

| Code | Type | Particularité | Matériel | Référence |
|---|---|---|---|---|
| **GADGET-4** | arbre / TreePM, ou FMM qui conserve la quantité de mouvement ; SPH | groupes et sous-structures à la volée, arbres de fusion, conditions cosmologiques 2LPT | processeurs (MPI + mémoire partagée) | Springel et al. 2021, MNRAS (DOI 10.1093/mnras/stab1855) [Certain, résumé lu] |
| **AREPO** | gaz sur maillage mobile (Voronoi) + gravité arbre/PM | moteur d'IllustrisTNG, Auriga, HESTIA | processeurs | Springel 2010 [Probable] |
| **GIZMO** | gaz « sans maillage » (MFM/MFV) | moteur de FIRE | processeurs | Hopkins 2015 [Probable] |
| **ChaNGa** | arbre, parallélisme Charm++ | simulations de galaxies et cosmologiques | processeurs, partie GPU | [Probable] |
| **falcON / gyrfalcON** | multipôles rapides, O(N) | utilisé pour la Voie lactée + Grand Nuage + Sagittaire | processeurs | Dehnen 2000 ; utilisé par Vasiliev et al. 2021 [Certain pour l'usage, lu] |
| **Bonsai** | arbre de Barnes-Hut **entièrement sur carte graphique** | **Voie lactée à 51 milliards de particules sur 6 Ga** (barre et bras apparaissent) ; essai à 242 milliards sur 18 600 cartes (Titan) | cartes graphiques | Bédorf et al. 2014, SC14 (arXiv:1412.0659) [Certain, résumé lu] |
| HiGPUs | somme directe, Hermite d'ordre 6 | utilisé pour la fusion Voie lactée–Andromède de Schiavi et al. | cartes graphiques | [Certain, lu dans Schiavi 2020] |
| **Ce que l'appli a** : `gravite_gpu.py` | arbre de Barnes-Hut sur carte graphique (construction Karras 2012), quadripôles, CuPy | 3 M de particules sur 10 Ga en ~9 h ; énergie à 0,11 % | RTX 5080 | [Certain, code lu] |

Conclusion [Probable] : **le moteur de gravité de l'appli est du même type que Bonsai** (le seul code « pro » taillé
pour une carte graphique). Ce n'est pas lui qui est en cause. Changer de moteur n'apporterait rien tant qu'on ne fait
pas de gaz ; pour le gaz, il faudrait GIZMO ou AREPO, qui tournent sur processeur sous Linux.

### 2.3 Les simulations cosmologiques : ce qu'elles donnent, ce qu'elles ne donnent pas

| Projet | Ce que c'est | Ce qu'on peut en tirer |
|---|---|---|
| **IllustrisTNG** (AREPO), **EAGLE** (GADGET modifié), **FIRE** (GIZMO), **Auriga** (AREPO) | des boîtes d'univers ou des zooms sur des galaxies « comme la Voie lactée », gaz et formation d'étoiles compris | des **galaxies qui ressemblent**, pas *nos* galaxies ; de bons modèles de **populations** (âge, métallicité selon la position) et de gaz [Probable] |
| **HESTIA** (AREPO + modèle Auriga) | **simulations contraintes** du Groupe local : départs cosmologiques choisis pour reproduire les vitesses mesurées des galaxies proches (CosmicFlows-2, 4 837 points) ; 13 calculs intermédiaires et 3 à haute résolution (matière noire 1,5 × 10⁵ M☉ par particule) | la meilleure façon connue d'avoir *un* Groupe local plausible **avec son histoire** ; mais la Voie lactée qui en sort n'est pas la nôtre étoile par étoile [Certain, lu : Libeskind et al. 2020, MNRAS 498, 2968] |
| **SIBELIUS-DARK** (SWIFT) | univers local contraint jusqu'à 200 Mpc, 131 milliards de particules de matière noire, galaxies par modèle semi-analytique (GALFORM), un analogue du Groupe local choisi parmi 60 000 calculs | grandes structures **avec vitesses propres** cohérentes autour de nous [Certain, lu : McAlpine et al. 2022, arXiv:2202.04099] |
| **Ananke** (FIRE) | **faux relevés Gaia** tirés de simulations : chaque particule d'étoile (7 070 M☉) est une population d'étoiles d'un seul âge, échantillonnée en étoiles ; poussière tirée du gaz simulé ; pointeur vers la particule d'origine | **exactement le pont qu'il manque à l'appli** entre « particules d'un calcul » et « étoiles qu'on voit » [Certain, résumé lu : Sanderson et al. 2020, ApJS 246, 6] |
| **Galaxia** | fabrique un catalogue d'étoiles synthétique de la Voie lactée à partir d'un modèle analytique (Besançon) **ou d'une réalisation N-corps**, par isochrones | même usage, plus simple [Certain, résumé lu : Sharma et al. 2011, ApJ 730, 3] |

### 2.4 La rencontre Voie lactée–Andromède : ce qu'ont fait les équipes publiées

| Étude | Méthode | Résultat |
|---|---|---|
| Cox et Loeb 2008 | N-corps + gaz, une réalisation | fusion en quelques Ga [Probable, de mémoire] |
| **van der Marel et al. 2012** (ApJ 753, 9) | **deux outils séparés** : N-corps sans collisions pour la forme, **orbites semi-analytiques en Monte-Carlo** pour les probabilités | premier passage à 3,87 (+0,42 −0,32) Ga, fusion à 5,86 (+1,61 −0,72) Ga ; choc direct (péricentre < 25 kpc) 41 % ; M33 percute d'abord la Voie lactée 9 %, éjectée 7 % ; le Soleil finit plus loin du centre qu'aujourd'hui 85 % [Certain, résumé lu] |
| **van der Marel et al. 2019** (ApJ 872, 24) | mouvements propres Gaia DR2 d'Andromède et du Triangle | vitesse transverse d'Andromède 57 (−31 +35) km/s, « un peu moins radiale qu'on ne pensait » ; premier passage ≈ 4,5 Ga selon la citation qu'en fait Schiavi [Certain pour la vitesse ; Probable pour la date] |
| **Schiavi et al. 2020** (A&A 642, A30) | **N-corps direct** (HiGPUs), 2,6 × 10⁵ particules (6,5 × 10⁴ pour les variantes) ; disque exponentiel, bulbe, halo de Hernquist coupé au rayon de marée ; Voie lactée 1,0 × 10¹², Andromède 1,6 × 10¹² M☉ ; séparation 780 kpc, vitesse radiale −115,7 km/s | premier passage dans 4,3 Ga, fusion étalée sur 10 Ga ; trous noirs fusionnés < 16,6 Ma après [Certain, texte lu] |
| **Sawala et al. 2025** (Nature Astronomy ; arXiv:2408.00064) | **pas de N-corps** : saute-mouton à pas de 1 Ma sur les centres, halos NFW adoucis à 20 kpc, **frottement dynamique analytique** (Chandrasekhar modifié) ; 50 000 tirages Monte-Carlo sur 22 paramètres ; Voie lactée 1,0 ± 0,2, Andromède 1,3 ± 0,4, Triangle 0,3 ± 0,1, Grand Nuage 0,15 ± 0,05 × 10¹² M☉ | **fusion dans les 10 Ga : un peu plus de 50 %** avec quatre corps ; ~2/3 avec le Triangle seul, ~1/3 avec le Grand Nuage seul ; choc frontal dans 4–5 Ga ≈ 2 % [Certain, texte lu] |

Les deux leçons pour l'appli [Probable, c'est la pratique commune de ces articles] :
1. **Les pros séparent toujours deux produits.** Un **ensemble d'orbites de centres** (rapide, des dizaines de
   milliers de tirages) pour dire « quelle probabilité ». Et **un ou quelques calculs N-corps** pour dire « à quoi ça
   ressemble ». Les deux utilisent **les mêmes masses et le même départ**. L'appli a les deux, mais avec des masses
   différentes (`analyse-architecture.md` § 2.2) et en dessinant l'ensemble comme des astres.
2. **Aucun article ne montre l'incertitude comme une galaxie.** Elle est dans des figures (nuages de points du
   péricentre, histogrammes de dates), à côté.

### 2.5 Matière noire, énergie noire, évolution des étoiles

**Matière noire.** Dans tous les calculs ci-dessus, elle est en **particules** (halo vivant), pas en potentiel figé,
dès que deux galaxies interagissent : c'est elle qui freine (frottement dynamique) et fait fusionner. Les codes qui
n'ont que les centres (Sawala) remplacent cela par une **formule de frottement**. [Certain pour Schiavi et Sawala, lu]

**Énergie noire.** Calcul ici [Certain] : l'accélération due à la constante cosmologique entre deux corps séparés de
r vaut Ω_Λ H₀² r. Avec H₀ = 67,7 km/s/Mpc et Ω_Λ = 0,69, à 770 kpc : 2,44 (km/s)²/kpc, contre G M/r² = 16,7 pour
M = 2,3 × 10¹² M☉ (masse du Groupe local de Peñarrubia et al. 2014). **Soit 15 % de la force aujourd'hui, 1 % à
300 kpc, rien sous 100 kpc.** Elle compte donc pour la **date du premier passage**, pas pour la forme de la fusion.
Publié : la masse du Groupe local déduite de l'« argument du temps » augmente de **13 %** quand on ajoute Λ
(Partridge, Lahav et Hoffman 2013, arXiv:1308.0970) [Certain, résumé lu] ; Peñarrubia et al. 2014 trouvent que Λ
change peu le flot de Hubble local [Certain, résumé lu]. Sawala 2025 ne la mentionne pas [Certain, pas trouvée dans
le texte lu]. **Pour l'appli : un terme de plus dans la force de chaque particule (Ω_Λ H₀² × position par rapport au
centre de masse du Groupe local), coût nul.** C'est ce que demande Marc (« jamais négligée ») et c'est cohérent avec
la pratique la plus soigneuse.

**Évolution des étoiles.** Les simulations ne suivent pas les étoiles une à une : chaque particule d'étoiles est une
**population d'un seul âge et d'une seule métallicité**, dont la lumière vient de modèles de populations (isochrones
MIST ou PARSEC) [Probable]. C'est ce que fait Ananke. Le fil « vie des étoiles » prépare déjà MIST : il peut fournir
cette brique.

### 2.6 Comment les pros font tomber un calcul sur « aujourd'hui »

C'est le cœur du problème « pas de bascule au Play ». Trois méthodes publiées :

| Méthode | Principe | Exemple | Pour nous |
|---|---|---|---|
| **Simulation contrainte** | on choisit le départ cosmologique pour que le présent ressemble aux mesures | HESTIA, SIBELIUS | trop cher et trop flou étoile par étoile [Probable] |
| **Remontée puis tir** | on remonte les **centres** dans le passé (orbites + frottement), on relance **vers l'avant** avec toutes les particules, on corrige le départ jusqu'à ce que le présent tombe sur les mesures | Vasiliev, Belokurov et Erkal 2021 (MNRAS 501, 2279), Voie lactée vivante + Grand Nuage + Sagittaire, gyrfalcON, 10⁶ particules de disque et bulbe, 4 × 10⁶ de halo [Certain pour le code et les nombres ; Probable pour le détail du réglage, non lu en entier] | **c'est la bonne méthode pour l'étage Groupe local** |
| **Made-to-measure** | on garde les orbites du calcul mais on **ajuste le poids** de chaque particule pour que la densité à t = 0 reproduise une carte mesurée | Portail et al. 2017 pour la barre [Probable] | **c'est la bonne méthode pour que les bras et la barre d'aujourd'hui soient les vrais** |

---

## 3. Veille B : comment les logiciels de visualisation dessinent la Voie lactée

| Logiciel | De l'intérieur | De l'extérieur | Données et modèles | Niveaux de détail |
|---|---|---|---|---|
| **Gaia Sky** | le catalogue Gaia en points | pas de dynamique ; la galaxie n'est que le catalogue (plus des éléments de décor) [À vérifier : la partie du texte sur la Voie lactée n'a pas été lue mot à mot] | catalogue seul | **arbre en huit trié par magnitude** (« MS-LOD ») : la racine contient les plus brillantes ; une case n'est dessinée que si son angle apparent dépasse un seuil θ, avec un fondu linéaire entre θ et θ + r ; **caméra flottante** (caméra à l'origine, calcul en précision arbitraire sur le processeur) [Certain, article lu : Sagristà et al. 2019, IEEE TVCG] |
| **OpenSpace** | points d'étoiles + Gaia en arbre en huit | **un volume** 1024 × 1024 × 128 (couleur + absorption) tiré d'**une simulation N-corps + gaz de l'observatoire du Japon**, traversé par lancer de rayons (pas réglable), **plus** un nuage de points posé par-dessus | modèle volumique + catalogue superposés, deux couches indépendantes | Gaia : cases de 1 000 à 150 000 étoiles, chargées autour de la caméra [Certain, documentation v0.22 lue] |
| **SpaceEngine** | catalogues (Hipparcos…) + étoiles **procédurales** | **sprites** répartis selon un modèle de galaxie ; nébuleuses en lancer de rayons | **les objets procéduraux plus brillants que la magnitude 8,1 sont supprimés près du Soleil** (`SolFade`) : le modèle comble ce que le catalogue n'a pas, sans doublon | sprites en arbre en huit, densité réglable [Certain, manuel et blog 2019 lus] |
| **Celestia** | catalogue Hipparcos | galaxies en gabarits de points | catalogue + gabarits | [Supposition, de mémoire, non vérifié] |
| **Universe Sandbox** | — | particules « nébuleuses » qui **ne s'attirent pas** ; la seule gravité de la galaxie est son trou noir ; l'ancien halo de matière noire en particules a été **retiré pour raisons de performance** | jeu, pas de données | [Certain, blog 2019 lu] |

Ce que ça apprend [Probable, synthèse] :
1. **Tous les logiciels sérieux dessinent la galaxie vue de loin avec un modèle**, jamais avec le seul catalogue. La
   « bulle » de l'appli est le résultat attendu quand on s'interdit le modèle.
2. **Le bon mariage catalogue + modèle est une soustraction** : le modèle ne dessine que ce que le catalogue **ne
   peut pas** contenir (SpaceEngine le fait par une coupure en magnitude ; la façon rigoureuse est la **fonction de
   sélection de Gaia** : la probabilité qu'une étoile donnée soit dans le catalogue selon sa position, sa magnitude
   et sa couleur, projet GaiaUnlimited, Castro-Ginard et al. 2023, arXiv:2303.17738 [Certain, résumé lu]). Le
   `voie_lactee.h` de l'appli fait déjà ce principe (« la grille ne contient que la lumière qui manque aux étoiles
   dessinées ») : il est juste éteint.
3. **Aucun logiciel grand public ne fait évoluer une galaxie réaliste.** Universe Sandbox a renoncé à la matière
   noire en particules ; Gaia Sky, OpenSpace et SpaceEngine sont figés. Ce que Marc demande (mesuré + dynamique +
   réaliste + continu) **n'existe pas sur étagère** : c'est le croisement de la pratique des chercheurs (§ 2) et de
   celle des logiciels (§ 3).
4. **OpenSpace montre le défaut à éviter** : volume et points sont deux couches indépendantes. Si l'un bouge et pas
   l'autre, on retrouve les coutures de l'appli.

---

## 4. Veille C : calcul à l'avance et lecture en temps réel, sans bascule

C'est la partie où il n'y a pas de logiciel de référence ; ce qui suit assemble des techniques publiées.

### 4.1 Une matière, plusieurs dessins (pas plusieurs matières)

Règle : **le niveau de détail change la représentation, jamais la source** (déjà écrit dans
`analyse-architecture.md` § 5.2). Concrètement, à partir des **mêmes particules du calcul** :

| Distance de la caméra | Dessin | Technique |
|---|---|---|
| loin (galaxie entière, Groupe local) | **volume** : la lumière et la poussière des particules sont déposées dans une grille 3D à chaque image, puis traversées par des rayons | dépôt sur carte graphique (calcul « nuage dans une grille ») + le lancer de rayons de `voie_lactee.h`, qui existe |
| moyen (quelques kpc) | **points** : une particule = un point dont l'éclat est celui de sa population | `fusion_nuage.h`, qui existe |
| près (moins de ~1 kpc d'une particule) | **étoiles une à une** : chaque particule est échantillonnée en étoiles (masses tirées d'une loi de Kroupa, éclat et couleur par isochrones), avec une **graine fixe par particule** pour que ce soient les mêmes étoiles à chaque image | Ananke, Galaxia (§ 2.3) |

Les passages entre niveaux se font **à lumière totale conservée**, selon la taille à l'écran : c'est un niveau de
détail, comme Gaia Sky (§ 3), et non un fondu entre deux mondes.

### 4.2 Le champ de gravité écrit en même temps que le calcul

Pour que les étoiles mesurées vivent dans le même monde que le calcul, il faut **leur donner la gravité du calcul à
chaque date**, sans rejouer les millions de particules. La technique : écrire le potentiel de chaque galaxie, à
chaque image, sous forme de **développement en fonctions de base** (multipôles pour les halos, « CylSpline » pour les
disques, dans AGAMA ; code EXP, Petersen, Weinberg et Katz 2022, MNRAS, DOI 10.1093/mnras/stab3639, « aussi précis
qu'un arbre et bien moins coûteux ») [Certain pour EXP et l'existence des potentiels d'instantanés dans AGAMA,
résumés lus ; Probable pour le choix des bases]. Quelques centaines de coefficients par galaxie et par image, que le
shader `orbites_pas.comp` peut lire. C'est le couplage « Bridge » de la PR 90, sous sa forme la plus légère.

### 4.3 L'interpolation entre images

L'appli trace **la ligne droite** entre deux images séparées de **20 Ma** (`fusion_nuage.h`). Calcul ici [Certain] :
une étoile à 2 kpc du centre fait le tour en ~61 Ma ; en 20 Ma elle parcourt 1/3 de tour, et la corde coupe l'arc de
**~1 kpc**. Le centre des galaxies « se contracte » entre deux images, et respire à chaque image. Pratique propre
[Probable] : écrire **positions et vitesses** et interpoler par **Hermite cubique** (erreur ~10 fois plus petite à
même écart d'images [Supposition, ordre de grandeur]), et resserrer à 5 Ma près des passages.

### 4.4 L'ancrage sur aujourd'hui

Trois exigences qui se contredisent en apparence : continuité (un seul calcul), réalité (le ciel d'aujourd'hui),
physique (des galaxies qui évoluent seules). Solution proposée [Supposition, assemblée à partir du § 2.6] :
- **Les centres** : remontée puis tir (§ 2.6), pour que le calcul passe par les positions et vitesses mesurées des
  galaxies à t = 0.
- **La forme** : made-to-measure sur la population lumineuse à t = 0 (bras et barre mesurés de la Voie lactée, image
  d'Andromède et du Triangle). Les poids changent la **lumière** des particules, pas leur **masse** : la dynamique
  reste celle du calcul, rien ne casse.
- **Les étoiles mesurées** : grains d'essai dans le champ du § 4.2, partant de leur position et vitesse Gaia à t = 0,
  intégrés **vers l'avant et vers l'arrière**. Le modèle (§ 4.1) ne dessine que ce que Gaia n'a pas vu. Quand le
  temps passe, les étoiles Gaia se mélangent à la galaxie du calcul **sans changer de source**.

---

## 5. L'appli comparée aux pratiques pros

| Pratique | Pros | Appli aujourd'hui | Écart |
|---|---|---|---|
| Départ en équilibre **stable** | GalIC, AGAMA, Q > 1,5, barre née d'elle-même | Q ≈ 0,7, barre violente ; corrigé sur `modeles-depart` (stable, sans barre encore) | **en cours de correction** |
| Un seul calcul pour tout le Groupe local | Schiavi, Vasiliev 2021 | deux films sans rapport (« Voie lactée seule », « fusion ») + 10 000 scénarios dessinés | **grave** |
| Calcul qui passe par aujourd'hui | remontée + tir ; made-to-measure | film qui *commence* à aujourd'hui avec des galaxies lisses | **grave** |
| Mêmes masses pour l'ensemble et pour la forme | toujours | non (Andromède 1,59 contre 1,3 × 10¹²) | moyen |
| Incertitude en figure, pas en astres | toujours | dessinée comme des galaxies (en partie caché par la PR 93) | en cours |
| Énergie noire | dans les calculs soignés de l'argument du temps | absente du film en place ; branchée sur la branche `galaxie-entiere` | moyen, facile |
| Particule = population d'étoiles | Ananke, Galaxia | particule = point blanc ou couleur moyenne de la galaxie | moyen |
| Modèle pour la lumière non mesurée | OpenSpace, SpaceEngine | `voie_lactee.h` existe, **éteint** | **grave pour « les étoiles »**, facile |
| Une source, plusieurs dessins | Gaia Sky (LOD), principe général | sept sources, fondus selon la date | **grave** |
| Interpolation qui respecte les orbites | positions + vitesses, Hermite | ligne droite sur 20 Ma | moyen |
| Moteur de gravité sur carte graphique | Bonsai | `gravite_gpu.py`, même famille | **bon** |
| Précision des positions loin de l'origine | caméra flottante (Gaia Sky) | position relative soustraite en deux temps | **bon** |
| Essais d'ensemble | (les logiciels n'en publient pas) | essai de continuité, 29 cassures | **bon outil**, à étendre |

---

## 6. Plan de refonte

### 6.1 Les options

| | **A. Rustines dans les calques** | **B+. Squelette unique, dessins multiples (recommandé)** | **C. Galaxies « restreintes »** | **D. Adopter un logiciel existant** |
|---|---|---|---|---|
| Quoi | chaque fil corrige son symptôme | un calcul N-corps du Groupe local parti du passé, réglé sur aujourd'hui, avec énergie noire ; champ écrit à chaque image ; un moteur de dessin à trois niveaux sur les mêmes particules ; étoiles Gaia dans le même champ | chaque galaxie = potentiel analytique qui suit l'orbite de son centre (ensemble à la Sawala) ; ses étoiles sont des grains d'essai qui sentent les autres (méthode de Toomre et Toomre 1972) | OpenSpace ou Gaia Sky pour le dessin, AMUSE ou GADGET-4 pour le calcul |
| Pour | visible en heures | règle la cause ; suit la pratique des articles du § 2 ; réutilise moteur de gravité, AGAMA, rendu, Gaia, `voie_lactee.h`, `fusion_nuage.h`, essai de continuité | **très peu cher** (minutes de carte) ; bras de marée corrects jusqu'au premier passage ; continuité garantie | méthodes éprouvées |
| Contre | ne garantit jamais continuité ni masse ; c'est ce qui a mené ici | 3 à 5 jours de carte graphique, 25 à 50 Go ; une dizaine d'étapes ; discipline : un seul fil possède l'état | **faux à la fusion** : pas de frottement réel, pas de masse échangée, galaxies indéformables ; ne peut pas montrer « Milkomeda » | aucun ne fait la dynamique avec les données (§ 3) ; on perd l'appli, ses 192 M d'étoiles en orbite, le système solaire au mètre |
| Verdict | à arrêter | **à faire** | **utile comme filet** : voir ci-dessous | à piller, pas à adopter |

L'option C n'est pas à jeter : c'est exactement ce que montre l'appli **pendant que le grand calcul tourne**, et ce
qui sert à **régler les centres** (étape 3). Elle sert de brouillon, puis disparaît.

### 6.2 Étapes de l'option B+

Chaque étape a son « fini quand » vérifiable par un essai ou une capture. Durées de carte graphique : estimées à
partir de la mesure de la PR 90 (≈ 0,35 h par million de particules et par milliard d'années) et des tirs de
`modeles-depart` (2 M sur 2 Ga en 19 min, soit ~0,08 h/M/Ga : **quatre fois plus rapide**, sans doute grâce à un pas
plus grand pour une galaxie seule [Supposition]). J'utilise la plus prudente.

| # | Étape | Fini quand | Carte graphique | Stockage | Travail [Supposition] |
|---|---|---|---|---|---|
| **0** | **Contrats** : une table unique de constantes (R0, vitesse du Soleil, masses, cosmologie, distance d'Andromède **tranchée**) lue par tous ; un grand livre des masses ; essai de continuité étendu à la **forme** (moments d'inertie et force du motif à deux bras de chaque galaxie, d'une image à la suivante) ; batterie de 20 captures fixes (vues × dates) | essais qui tournent par `natif/controle.sh` ; table unique utilisée par `modeles_v2.py` et l'appli | 0 | 0 | 1 à 2 jours de fil |
| **1** | **Galaxies de départ** (= branche `modeles-depart`, à finir par son fil) : stables (déformation < 0,1 sur 2 Ga), **barre née seule** pour la Voie lactée et Andromède, Petit Nuage ajouté, gaz compté en masse | rotation à ±10 % des mesures sur tout le rayon ; barre de la Voie lactée à 4–5 kpc de demi-longueur ; aucune particule de matière noire plus de 10 fois plus lourde qu'une étoile | ~20 min par galaxie et par essai ; ~5 h au total | < 5 Go | en cours |
| **2** | **Vieillir chaque galaxie seule** 1 à 2 Ga, puis **choisir l'instant** où la barre a le bon angle (28° pour la Voie lactée, 54,7° pour Andromède) | barre à ±5° de l'angle publié à l'instant choisi | ~2 à 4 h | ~5 Go | 1 jour |
| **3** | **Orbites des centres** (option C) : ensemble Monte-Carlo **avec les masses de la table unique**, frottement analytique, **énergie noire** ; on en tire une réalisation de référence (proche de la médiane) et sa position à t = −T (T = 3 Ga proposé) | ensemble qui redonne Sawala 2025 à ±10 points avec leurs masses ; réalisation de référence qui passe à moins de 1 σ des mesures d'aujourd'hui | secondes à minutes | < 1 Go | 1 à 2 jours |
| **4** | **Brouillon visible** : l'appli dessine les galaxies de l'étape 2 posées sur les orbites de l'étape 3 (option C), avec **un seul moteur de dessin** (volume + points + étoiles une à une, § 4.1) et le modèle de lumière rallumé ; Gaia par-dessus, modèle masqué là où Gaia est complet | de −3 à +10 Ga, **aucune galaxie ne disparaît, aucune ne change de forme au Play** (essai de forme de l'étape 0) ; vue de 150 000 al : un disque avec barre, pas un trait | dessin seulement | 0 | 3 à 5 jours |
| **5** | **Réglage en petit** : N-corps complet à 1–3 M de particules, de −T à 0, avec énergie noire ; on corrige le départ (tir) jusqu'à ce que t = 0 tombe sur les mesures (distances, vitesses radiales, mouvements propres d'Andromède, du Triangle, des Nuages) | écart à t = 0 < 1 σ pour chaque galaxie | 3 M × 3 Ga ≈ 3 h par tir ; 3 à 6 tirs : **10 à 20 h** | ~5 Go par tir, gardé : le dernier | 2 à 3 jours |
| **6** | **Forme d'aujourd'hui** : made-to-measure sur la lumière à t = 0 (bras mesurés de la Voie lactée de `voie_lactee.bin` et de la PR 94, images d'Andromède et du Triangle) ; populations (âge, métallicité) attachées aux particules avec MIST (fil « vie des étoiles ») | image de synthèse à t = 0 comparée aux images mesurées : corrélation à fixer à l'étape 0 ; ciel vu du Soleil inchangé | ~1 h | < 1 Go | 3 à 4 jours |
| **7** | **Grand calcul de référence** : de −T à +10 Ga (+13 si Marc veut voir l'après-fusion), **10 M** de particules (palier recommandé) ; écrit à chaque image : particules d'étoiles (positions + vitesses, 16 bits) toutes les 20 Ma, resserrées à 5 Ma près des passages, **plus** le champ de chaque galaxie en coefficients tous les 5 Ma | énergie conservée < 0,5 % ; t = 0 dans 1 σ ; essai de continuité et de forme verts sur toute la plage | 10 M × 13 Ga × 0,35 ≈ **45 h** (~2 jours) ; palier 30 M : ~6 jours | **~25 Go** (10 M) à ~75 Go (30 M) : **accord de Marc** | 1 jour + attente |
| **8** | **Étoiles mesurées dans le même champ** : `orbites_pas.comp` lit les coefficients au lieu du potentiel figé ; intégration vers l'avant **et** vers l'arrière ; vitesses radiales manquantes tirées de la dispersion locale du modèle (dit « modèle ») | à +4,5 Ga, les étoiles Gaia traversent la rencontre **sans s'éteindre** ; `starShare`, `loneShare`, `fusionShare` supprimés | quelques heures de précalcul (98 M d'étoiles × 10 Ga, pas de 1 Ma ; 27 ms le pas mesuré ⇒ ~5 min par Ga et par sens, à remesurer avec le champ) | ~10 Go de points de contrôle | 3 à 5 jours |
| **9** | **Démolition** : retirer les sept Voies lactées et les fondus ; scénarios seulement en figure (fourchette de date, ellipse) | `essai_continuite` : **0 cassure** sur les galaxies et les étoiles ; les 20 captures cohérentes | 0 | libère ~15 Go (anciens films) | 2 jours |
| plus tard | **Gaz et naissance d'étoiles** (bras qui se reforment, Courant magellanique) | — | **semaines**, sur processeur (GIZMO, AREPO, sous Linux) | non mesuré | chantier à part |

Ordre : 0 → 1 → 2 → 3 → **4 (première image juste)** → 5 → 6 → 7 → 8 → 9. Les étapes 3–4 et 5–6 peuvent se
chevaucher. Les grandes structures (vitesses propres Cosmicflows-4, groupes liés) et le système solaire suivent leur
propre route (`analyse-architecture.md` § 7), indépendante.

### 6.3 Charge et mémoire de la carte graphique

| | Mesuré ou estimé | Source |
|---|---|---|
| Calcul 10 M, appli fermée | ~4 Go de mémoire graphique (10,5 M en prenait 4,2) | PR 90 [Probable] |
| Appli ouverte, tout chargé | 9 à 15,3 Go sur 16,3 | mémoire du projet [Probable] |
| Lecture du film à 10 M dans l'appli | deux images encadrantes, positions + vitesses en 16 bits : ~3 M d'étoiles × 12 octets × 2 ≈ **70 Mo** ; la matière noire n'est pas lue (seulement ses coefficients) | calcul ici [Certain] |
| Volume de dessin | grille 512 × 512 × 64 en demi-flottants, 4 canaux : **134 Mo** [Certain, calcul] ; à remesurer en images par seconde | — |
| Grand calcul pendant que Marc joue | le calcul se met déjà en pause ; durée réelle plus longue que 45 h | PR 90 [Probable] |

### 6.4 Ce que le plan ne donnera pas (pour ne pas promettre)

- La position d'**une** étoile précise au-delà d'environ 100 Ma : imprévisible (masses mal connues) [Probable].
- **Les vrais bras dans 1 Ga** : on aura des bras plausibles, pas la carte future.
- **La certitude de la fusion** : Sawala 2025 dit ~50 % en 10 Ga. Le film montre **une** histoire de référence, et
  la fiche dit sa probabilité.
- **Des bras aussi nets que sur les photos** sans le gaz.

---

## 7. Recommandation

**Option B+, en commençant par les étapes 0, 3 et 4** pendant que le fil `modeles-depart` finit l'étape 1. Pourquoi
cet ordre [Supposition, mon jugement] :
- l'étape 4 donne **en quelques jours**, sans grand calcul, ce que Marc demande à l'écran : une Voie lactée et une
  Andromède entières aujourd'hui, qui ne changent pas de forme au Play, dans le passé comme dans l'avenir ;
- elle installe **le moteur de dessin unique** qui servira tel quel au grand calcul : rien n'est jeté ;
- elle permet de **régler les centres pour presque rien** avant de dépenser 45 h de carte.

Et une règle d'organisation, déjà proposée par la PR 90, que je confirme : **un seul fil possède `fenetre.cpp` et
l'état** ; les autres livrent des pièces qui respectent les contrats de l'étape 0.

## 8. Questions à trancher par Marc (toutes d'un coup)

| # | Question | Ma recommandation |
|---|---|---|
| 1 | Option B+ et l'ordre 0 → 3 → 4 d'abord ? | oui |
| 2 | Départ du calcul dans le passé : −3 Ga ? (plus loin = plus de passé visible, mais plus d'incertitude sur les orbites) | −3 Ga ; le passé plus ancien en « orbites seulement » |
| 3 | Palier du grand calcul : 10 M (~2 jours, ~25 Go) ou 30 M (~6 jours, ~75 Go) ? | 10 M d'abord ; 30 M seulement si l'image le réclame |
| 4 | Stockage de 25 à 75 Go sur le Drive (`physique\`) : d'accord ? | oui, sur le Drive |
| 5 | Les étoiles synthétiques (là où Gaia n'a rien vu) affichées comme « modèle », avec la même tache que les étoiles mesurées et un marquage dans la fiche ? | oui |
| 6 | Distance d'Andromède unique pour tout : 761 kpc (Céphéides, Li 2021) ou 785 kpc (valeur des articles de dynamique) ? | **761**, la plus récente et la plus précise [Probable, non relue ce jour] ; garder 785 comme variante dans l'ensemble des orbites |
| 7 | Après la fusion : jusqu'à +10 Ga ou +13 Ga ? | +10 Ga (comme Sawala) |
| 8 | Le gaz : chantier à ouvrir après l'étape 9, ou jamais ? | après, en le disant à l'écran d'ici là |

---

## 9. Sources lues pour ce document

Simulations :
- Yurin et Springel 2014, GalIC : https://arxiv.org/abs/1402.1623
- Vasiliev 2019, AGAMA : https://arxiv.org/abs/1802.08239
- Springel et al. 2021, GADGET-4 : https://arxiv.org/abs/2010.03567
- Bédorf et al. 2014, Bonsai : https://arxiv.org/abs/1412.0659
- Petersen, Weinberg et Katz 2022, EXP : https://arxiv.org/abs/2104.14577
- Vasiliev, Belokurov et Erkal 2021, « Tango for three » : https://arxiv.org/abs/2009.10726
- van der Marel et al. 2012, III : https://arxiv.org/abs/1205.6865
- van der Marel et al. 2019 : https://ui.adsabs.harvard.edu/abs/2019ApJ...872...24V/abstract
- Schiavi et al. 2020, A&A 642, A30 : https://www.aanda.org/10.1051/0004-6361/202038674
- Sawala et al. 2025 : https://arxiv.org/abs/2408.00064 ; communiqué ESA : https://www.esa.int/Science_Exploration/Space_Science/Hubble_and_Gaia_revisit_fate_of_our_galaxy
- Partridge, Lahav et Hoffman 2013 : https://arxiv.org/abs/1308.0970
- Peñarrubia et al. 2014 : https://arxiv.org/abs/1405.0306
- Libeskind et al. 2020, HESTIA : https://researchonline.ljmu.ac.uk/id/eprint/19297/
- McAlpine et al. 2022, SIBELIUS-DARK : https://arxiv.org/abs/2202.04099
- Sanderson et al. 2020, Ananke : https://arxiv.org/abs/1806.10564
- Sharma et al. 2011, Galaxia : https://arxiv.org/abs/1101.3561
- Castro-Ginard et al. 2023, fonction de sélection Gaia : https://arxiv.org/abs/2303.17738

Logiciels :
- Sagristà et al. 2019, Gaia Sky : https://vcg.iwr.uni-heidelberg.de/static/publications/Sagrista2019gaiaSky.pdf ; https://gaia.ari.uni-heidelberg.de/gaiasky/docs/3.5.3/LOD-catalogs.html
- OpenSpace : https://docs.openspaceproject.com/releases-v0.22/content/milky-way/galaxy/milky-way-volume/index.html ; https://docs.openspaceproject.com/releases-v0.22/reference/asset-components/Renderable/RenderableGalaxy.html ; https://docs.openspaceproject.com/releases-v0.22/building-content/gaia.html
- SpaceEngine : https://spaceengine.org/manual/making-addons/creating-a-dso/ ; https://spaceengine.org/news/blog190217/
- Universe Sandbox : https://universesandbox.com/blog/2019/06/dark-matter-galaxies/

Cités de mémoire, non relus ce jour [Probable] : Springel, Di Matteo et Hernquist 2005 (MakeNewDisk) ; Springel 2010
(AREPO) ; Hopkins 2015 (GIZMO) ; Cox et Loeb 2008 ; Syer et Tremaine 1996 et Portail et al. 2017 (made-to-measure) ;
Toomre et Toomre 1972 ; Li et al. 2021 (distance d'Andromède) ; Celestia.

## 10. Limites de ce document

- Rien n'a été lancé dans l'appli ni sur la carte graphique ; le constat s'appuie sur les captures et essais du
  13/11 (`etat-des-lieux-1311.md`, `continuite-1311.txt`) et sur la lecture du code.
- Les durées de carte sont **extrapolées** de deux ou trois mesures ; l'écart entre elles (facteur 4) montre qu'il
  faut remesurer à l'étape 5.
- Les durées de travail sont des suppositions.
- Plusieurs articles n'ont été lus qu'en résumé (indiqué à chaque ligne).
