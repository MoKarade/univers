# Comment les équipes pro montent une simulation de galaxies, et ce que ça dit de notre calcul (18 novembre 2026)

Demande (coordinateur, 18/11) : étudier comment les équipes professionnelles montent ce genre de simulation (conditions
initiales contraintes, recettes de sous-maille, résolution, pas de temps, calibration, validation), puis comparer à notre
plan et dire ce qu'on fait mal ou ce qui manque. **Aucun calcul lancé, aucun code modifié.**

Ce document complète `docs/refonte-simulations-pro.md` (PR 95), qui couvrait déjà les moteurs de gravité, les
générateurs de galaxies, les logiciels de visualisation et les études de la rencontre Voie lactée–Andromède. Ici, je
regarde **la fabrication** : comment une équipe passe d'une idée à un calcul dont elle peut défendre les résultats.

État de notre calcul pris comme référence : branche `film-3` (PR 102, ouverte), `rencontre.py`, `modeles_v2.py`,
`stabilite_tir.py`, `gaz_gpu.py`, `gaz_galaxie.py`, et les contrôles `docs/premier-film.md` et `docs/deuxieme-film.md`.

Labels : **[Certain]** lu dans le texte d'un article ou dans notre code ce jour, ou calculé ici ; **[Probable]** lu dans
un résumé, ou cité de mémoire avec une source connue ; **[Supposition]** mon raisonnement ; **[À vérifier]** non vérifié.

---

## 0. En bref

1. **Notre façon de caler le calcul sur aujourd'hui est la bonne pour notre but, et elle fait mieux que les
   simulations contraintes pro sur ce point précis.** HESTIA, la meilleure simulation contrainte du Groupe local, tombe
   à 675–866 kpc de séparation et 54 à 137 km/s de vitesse transverse, pour 785 kpc et 0 à 60 km/s mesurés. Notre film
   tombe à 2,3 kpc et 10 km/s d'Andromède. La raison : eux partent du Big Bang et reproduisent un Groupe local
   *plausible* ; nous partons de nos galaxies mesurées et ne remontons qu'1 Ga. Ce sont deux métiers. [Certain pour les
   chiffres ; Supposition pour le jugement]
2. **Le gros manque n'est pas la physique, c'est le protocole.** Toutes les équipes séparent ce qu'on **règle**
   (calibration, une courte liste d'observations déclarée d'avance) de ce qu'on **vérifie** (validation, des
   observations jamais utilisées pour régler). Notre `bulletin.py` compare à 9 mesures, et on règle sur toutes. Si on
   règle tout, plus rien ne prouve que le calcul est juste. [Certain pour EAGLE, Auriga ; Certain pour notre code]
3. **Notre gaz ne tiendra pas avec un pas de temps unique.** Le calcul avance toutes les particules au même pas de
   0,25 Ma. Pour le gaz, la condition de Courant (que `gaz_galaxie.py` mesure mais n'impose pas) demande 0,12 Ma au
   repos et environ 0,02 Ma dans les chocs de la rencontre. Tous les codes pro (GADGET-4, AREPO, GIZMO) utilisent des
   **pas individuels hiérarchiques**. C'est la correction technique la plus urgente. [Certain, calcul ici]
4. **Notre gaz est un gaz « sans rétroaction », ce que plus aucune équipe ne fait depuis ~2003.** Sans énergie rendue
   par les étoiles qui naissent, le gaz s'effondre en grumeaux et forme ses étoiles trop vite. Les pros ont deux écoles :
   **pression effective** (Springel et Hernquist 2003, utilisée par Auriga ; EAGLE) qui coûte presque rien, ou
   **rétroaction explicite** (FIRE) qui demande une résolution que nous n'avons pas. Pour nous : la pression effective.
   [Certain pour Auriga, EAGLE, FIRE ; Supposition pour le choix]
5. **La barre trop lente (20 km/s/kpc contre 39) est un défaut connu de toutes les simulations, pas seulement des
   nôtres.** Roshan et al. 2021 trouvent des barres trop lentes dans IllustrisTNG et EAGLE, à 10–13 σ des observations.
   Le halo en rotation (PR 102) est un levier publié, mais à double tranchant : Collier et al. 2018 trouvent aussi des
   barres plus faibles qui peuvent se dissoudre après le flambage. [Certain, résumés lus]
6. **Un seul film ne dit pas ce qui est robuste.** Genel et al. 2019 : deux calculs identiques à 10⁻⁷ pc près divergent
   de 2 à 25 % sur les propriétés des galaxies. Les pros lancent des **ensembles** ; nous en avons pour les centres
   (orbites), pas pour les particules. [Certain, résumé lu]
7. **Recommandation**, dans l'ordre (détail et coût au § 7) : protocole calibration/validation (0 h de carte) ; pas de
   temps individuels et essai de convergence en pas (1–2 h) ; gaz à pression effective, retour de masse des étoiles,
   naissance d'étoiles réglée sur une seule mesure (3–6 h) ; barre : essai « centre dominé par les étoiles » à côté du
   halo en rotation (2–4 h) ; ensemble de 4 à 6 films en petit (1 à 2 jours) ; puis seulement le film 4 avec gaz
   (2 à 4 jours). **Total avant le film 4 : environ 2 jours de carte**, au lieu d'un film de 3 jours qu'on risque de
   jeter.

---

## 1. Les simulations de référence, en une table

| Projet | But | Départ | Code et gaz | Résolution (masse par particule ; adoucissement) | Recette de sous-maille |
|---|---|---|---|---|---|
| **CLUES** (Carlesi et al. 2016) | « usine à Groupes locaux » : beaucoup de candidats | contraint par Cosmicflows-2 (filtre de Wiener + réalisations contraintes + Zel'dovich inverse) | GADGET-2, matière noire seule | 6,57 × 10⁸ h⁻¹ M☉ dans la zone zoomée | aucune |
| **HESTIA** (Libeskind et al. 2020) | Groupe local réaliste dans son environnement réel (Virgo, vide local) | idem, ~1 000 départs basse résolution, 13 en résolution moyenne, 3 en haute | AREPO (maillage mobile, champ magnétique) | haute : matière noire 1,5 × 10⁵, gaz 2,2 × 10⁴ M☉ ; 220 pc | modèle Auriga |
| **APOSTLE** (Sawala et al. 2016 ; Fattahi et al. 2016) | 12 paires « type Groupe local » | **non contraint** : paires choisies dans une boîte de 100 Mpc selon leur orbite | EAGLE (GADGET-3 modifié, SPH « Anarchy ») | L1 : gaz 1,0 × 10⁴, matière noire 5,0 × 10⁴ M☉ ; 134 pc | modèle EAGLE de référence, inchangé à toutes les résolutions |
| **Auriga** (Grand et al. 2017) | 30 Voies lactées isolées | zooms sur des halos de 1 à 2 × 10¹² M☉ tirés au sort parmi les plus isolés | AREPO, champ magnétique | niveau 4 : matière noire ~3 × 10⁵, baryons ~5 × 10⁴ M☉ ; 369 pc max | Springel–Hernquist 2003, seuil 0,13 cm⁻³ ; vents ; trous noirs |
| **FIRE-2** (Hopkins et al. 2018) | physique « sans réglage » à très haute résolution | zooms cosmologiques | GIZMO (sans maillage) | m12 : gaz ~7 000 M☉, matière noire ~5 fois plus | naissance seulement dans le gaz dense, auto-gravitant, moléculaire ; rétroaction explicite (supernovae, vents, rayonnement) |
| **EAGLE** (Schaye et al. 2015 ; Crain et al. 2015) | populations de galaxies dans 100 Mpc | boîte cosmologique | GADGET-3 modifié | gaz 1,81 × 10⁶, matière noire 9,70 × 10⁶ M☉ ; 0,70 kpc | pression effective γ = 4/3 ; loi de Kennicutt–Schmidt en pression ; supernovae thermiques stochastiques ; trous noirs |
| **IllustrisTNG** (Pillepich et al. 2018) | idem, 35 à 300 Mpc | boîte cosmologique | AREPO | TNG50 : ~8 × 10⁴ M☉ de baryons [Probable, de mémoire] | dérivé d'Illustris : vents revus, trous noirs à deux modes, champ magnétique |
| **NIVARIA-LG** (Contreras-Santos et al. 2026) | naines du Groupe local | un départ HESTIA | Gasoline2 (SPH) | matière noire 1,6 × 10⁶, gaz 3,0 × 10⁵ M☉ ; 488 pc | NIHAO : seuil 10 cm⁻³ |
| **Notre film** | **nos** cinq galaxies, ciel d'aujourd'hui, avenir | modèles publiés à l'équilibre (AGAMA), centres réglés par tirs depuis −1 Ga | arbre sur carte graphique ; gaz SPH en essai | Voie lactée : matière noire ~5,6 × 10⁵, étoiles ~6,5 × 10⁴ M☉ [calculé, voir § 4] ; 33 pc (étoiles), 130 pc (halo) | gaz isotherme 10 km/s, plancher de Jeans, seuil 0,1 cm⁻³, 1 % par temps de chute libre, **sans rétroaction** |

Sources : § 9. [Certain pour toutes les lignes, sauf TNG50 [Probable] ; les chiffres de NIVARIA viennent de l'article
d'octobre 2026, lu ce jour.]

**Notre résolution n'est pas ridicule.** Nos particules d'étoiles sont aussi fines que celles d'Auriga (et 3 fois plus lourdes que
celles de HESTIA haute résolution), et notre matière noire est entre les deux. Ce qui nous distingue, ce n'est pas le grain, c'est ce qui manque
autour (gaz, rétroaction, environnement) et la façon de vérifier. [Certain pour les chiffres ; Supposition pour la
conclusion]

---

## 2. Les conditions initiales contraintes : comment ils font, et pourquoi ce n'est pas notre chemin

### 2.1 La méthode CLUES / HESTIA [Certain, articles lus]

1. **Données** : Cosmicflows-2, plus de 8 000 distances directes jusqu'à ~250 Mpc, regroupées en 4 837 points.
2. **Correction des biais** (Malmquist, chute vers les amas) par une méthode itérative (Sorce 2015).
3. **Filtre de Wiener + réalisations contraintes** : on reconstruit le champ de densité le plus probable compatible avec
   les vitesses mesurées, et on ajoute du bruit aléatoire là où les données ne contraignent rien.
4. **Zel'dovich inverse** : on ramène chaque structure à l'endroit d'où elle est partie au début de l'univers.
5. **Balayage des graines** : les petites échelles (celles qui font les galaxies) ne sont **pas** contraintes. On tire
   des centaines de graines. CLUES : 300 calculs → 146 paires passent les critères de base (masse, séparation,
   isolement), 51 le second niveau (moment cinétique et énergie de l'orbite), **6** le troisième (phase de l'orbite).
   HESTIA : ~1 000 départs basse résolution → 13 en résolution moyenne → 3 en haute.
6. **Critères HESTIA** : amas de la Vierge de plus de 2 × 10¹⁴ M☉ au bon endroit (à 7,5 Mpc près) ; paire de 8 × 10¹¹ à
   3 × 10¹² M☉ chacune, séparée de 0,5 à 1,2 Mpc, qui se rapproche, rapport de masses > 0,5, pas de troisième halo
   plus lourd que la petite dans 2 Mpc.

Résultat obtenu pour les trois calculs haute résolution [Certain, table 1 de Libeskind et al. 2020] :

| | Séparation | Vitesse radiale | Vitesse transverse |
|---|---|---|---|
| mesuré (référence de l'article) | 785 ± 25 kpc | −110 km/s | 0 à 60 km/s |
| HESTIA 09_18 | 866 kpc | −74 km/s | 54 km/s |
| HESTIA 17_11 | 675 kpc | −102 km/s | 137 km/s |
| HESTIA 37_11 | 850 kpc | −9 km/s | 71 km/s |
| **notre premier film** | **à 2,3 kpc et 10 km/s de la place mesurée** | | |

### 2.2 APOSTLE : la voie « on choisit dans le catalogue » [Certain]

Pas de contrainte : dans une boîte de 100 Mpc (DOVE), on garde les paires séparées de 600 à 1 000 kpc, qui se
rapprochent à 0–250 km/s avec moins de 100 km/s de vitesse transverse, de masse totale 10^12,2 à 10^12,6 M☉, isolées
dans 2,5 Mpc, avec un flot de Hubble calme jusqu'à 4 Mpc. Douze paires. Leçon importante pour nous : les mêmes auteurs
(Fattahi 2016) montrent que l'**argument du temps** seul favorise ~5 × 10¹² M☉, mais qu'en ajoutant la vitesse
transverse et le flot de Hubble, on retombe vers 2 × 10¹². Notre table unique (Voie lactée 1,34, Andromède 1,07,
total ~2,4 × 10¹² avec les Nuages et le Triangle) est dans la zone. Makarov et al. 2025 trouvent 2,47 ± 0,15 × 10¹² M☉
par le flot de Hubble froid autour du Groupe local. [Certain, résumé lu]

### 2.3 Ce que ça veut dire pour nous

- **On a raison de ne pas faire du CLUES/HESTIA.** Ces méthodes donnent *un* Groupe local plausible, avec son histoire
  cosmologique. Elles ne donnent ni nos bras, ni notre barre, ni la vraie orbite d'Andromède. Le chemin pro qui
  correspond à notre but est celui de Vasiliev, Belokurov et Erkal 2021 (remontée puis tir), qu'on suit déjà.
  [Probable]
- **Ce qu'on perd en ne partant pas du cosmologique, et qu'il faut dire à l'écran ou compenser** [Supposition, sauf
  mention] :
  1. **L'arrivée continue de matière** : un halo de 10¹² M☉ grossit encore aujourd'hui par accrétion. Sur 10 Ga,
     c'est quelques dizaines de pour cent de masse [À vérifier : ordre de grandeur, non relu]. Nous avons des halos de
     masse fixe.
  2. **Le gaz chaud du halo** (couronne), qui alimente le disque en gaz neuf. Sans lui, le gaz du disque s'épuise :
     1,22 × 10¹⁰ M☉ de gaz pour 1,65 M☉/an de naissances, soit ~7 Ga sans retour de masse (calcul ici, voir § 3.4).
  3. **Les petits satellites**. Sagittaire, que Vasiliev 2021 inclut et qui perturbe le disque de la Voie lactée, est
     absent. M32 et NGC 205 près d'Andromède aussi. [Certain pour Vasiliev 2021 ; Probable pour l'effet sur le disque]
  4. **Le passé** : on ne remonte qu'à −1 Ga (au-delà, les Nuages n'arrivent pas à leur place, PR 100). HESTIA a tout le
     passé, mais faux dans le détail.
- **L'environnement lointain** (Vierge, feuillet local) : effet de marée négligeable sur 10 Ga à l'échelle du Groupe
  local [Supposition, non calculé ici]. L'énergie noire, elle, est déjà dans notre calcul.

---

## 3. Les recettes de sous-maille du gaz

### 3.1 Les deux écoles [Certain pour les recettes, articles lus]

| | « Pression effective » (Auriga, EAGLE, TNG) | « Rétroaction explicite » (FIRE) | **Nous (PR 102)** |
|---|---|---|---|
| Où naissent les étoiles | gaz au-dessus de ~0,1 cm⁻³ (Auriga 0,13 ; EAGLE 0,1 × (Z/0,002)^−0,64) | gaz > 1 000 cm⁻³, auto-gravitant, moléculaire, instable de Jeans | gaz > 0,1 cm⁻³ |
| Taux | Auriga : temps caractéristique 2,2 Ga (modèle en deux phases) ; EAGLE : loi de Kennicutt–Schmidt écrite en pression | ~100 % par temps de chute libre à la limite de résolution, régulé ensuite par la rétroaction | 1 % par temps de chute libre |
| Ce qui empêche le gaz de s'effondrer en grumeaux | une **pression imposée** qui croît avec la densité (EAGLE : P ∝ ρ^4/3, ce qui rend la masse de Jeans indépendante de la densité) : elle tient lieu des supernovae non résolues | les supernovae, vents et rayonnement, calculés explicitement | un **plancher de Jeans** (pression minimale pour que la longueur de Jeans fasse 4 longueurs de lissage) et un gaz isotherme à 10 km/s |
| Rétroaction | vents (Auriga : 3,46 × la dispersion de la matière noire), supernovae thermiques stochastiques à 10^7,5 K (EAGLE), trous noirs | supernovae Ia et II, vents d'étoiles, pression de radiation, photo-ionisation | **aucune** |
| Résolution nécessaire | ~10⁴ à 10⁶ M☉ | ~10³ à 10⁴ M☉ | — |

### 3.2 Ce qui est juste dans notre gaz

- **La formulation SPH** (Monaghan, Balsara) avec ~58 voisines est classique et contrôlée par trois essais à réponse
  connue (gradient, tube à choc, effondrement d'Evrard) : c'est la bonne pratique. [Certain, code lu]
- **Le plancher de Jeans** est une technique publiée (Bate et Burkert 1997 ; Robertson et Kravtsov 2008) et empêche la
  fragmentation numérique. [Probable]
- **Le seuil de 0,1 cm⁻³** est celui d'EAGLE et d'Auriga. [Certain]
- **La masse est conservée** (la particule change de nature). [Certain]

### 3.3 Ce qui ne va pas

1. **Pas de rétroaction ni de pression effective** [Certain pour le code ; Probable pour l'effet]. Le plancher de Jeans
   empêche les grumeaux *numériques*, pas la surproduction d'étoiles : rien ne repousse le gaz après une naissance.
   Historiquement, c'est le « problème du refroidissement excessif » qui a mené Springel et Hernquist 2003 à leur
   modèle. L'efficacité de 1 % compense en partie, mais elle ne se comporte pas comme une rétroaction (elle ne réagit
   pas aux chocs de la rencontre, où le gaz se comprime d'un coup). **Risque concret** : à la fusion, un sursaut de
   naissances bien plus fort que dans les articles, et un centre trop dense. [Supposition]
2. **SPH « classique »** : on connaît ses défauts depuis 2007 (mauvais mélange aux interfaces, instabilités de cisaillement
   étouffées, comparaison d'Agertz et al. 2007). Les pros sont passés à la SPH en pression-entropie (Hopkins 2013,
   EAGLE « Anarchy »), à la viscosité variable (Cullen et Dehnen 2010), ou aux méthodes sans maillage et à maillage
   mobile. [Probable, de mémoire] Pour un disque froid isotherme, l'effet est modéré ; pour les queues de marée et le
   choc des gaz de deux galaxies, il compte. [Supposition]
3. **Gaz isotherme à 10 km/s partout** : pas de gaz chaud, donc pas de couronne, pas de chauffage par choc à la fusion
   (le gaz choqué à des centaines de km/s devrait chauffer à des millions de degrés et cesser de former des étoiles).
   [Supposition, physique standard]
4. **Pas de retour de masse des étoiles** : une population d'étoiles rend ~40 % de sa masse en gaz sur quelques Ga (vents,
   supernovae, nébuleuses planétaires) [Probable, de mémoire : Leitner et Kravtsov 2011]. Sans ce retour et sans couronne,
   le gaz de la Voie lactée s'épuise en ~7 Ga ; avec, la naissance d'étoiles continue. Sur 10 Ga, ça change l'image.
5. **Une erreur de chiffre dans le commentaire de `gaz_gpu.py`** : « à 800 kpc du centre, la simple précision ne
   distingue plus 60 pc ». Calcul ici [Certain] : en simple précision, l'écart entre deux nombres voisins vers 800 est
   2⁻¹⁴ ≈ 6,1 × 10⁻⁵ kpc, soit **0,06 pc**, pas 60 pc. C'est probablement un mélange d'unités. Conséquence : rien
   n'empêche de calculer le gaz des deux galaxies **ensemble** dans le repère du calcul pendant la rencontre, ce que le
   commentaire semble exclure. [Probable : je n'ai pas cherché d'autre raison dans le code]

### 3.4 Chiffres de contrôle utiles

- Voie lactée : naissances 1,65 ± 0,19 M☉/an, gaz 1,22 × 10¹⁰ M☉ (déjà dans `mesures_voie_lactee.json`). [Certain]
- Temps de vidage du gaz : 1,22 × 10¹⁰ / 1,65 ≈ **7,4 Ga** sans apport ni retour. [Certain, calcul]
- Andromède : ~0,3 à 0,7 M☉/an ; Triangle : ~0,2 à 0,45 M☉/an [À vérifier : de mémoire, valeurs selon l'indicateur].
  Ce sont de **bons témoins de validation** : on ne les règle pas, on regarde si le calcul tombe dessus.

---

## 4. Résolution et adoucissement

### 4.1 Nos chiffres [calculé à partir de `modeles_v2.py` et du premier film]

Voie lactée, 3,5 M de particules, 70 % en matière noire (`PART_HALO = 0.7`) : 2,45 M de particules de halo pour
~1,37 × 10¹² M☉, soit **~5,6 × 10⁵ M☉** par particule ; ~1,05 M de particules d'étoiles et de gaz pour ~6,8 × 10¹⁰ M☉,
soit **~6,5 × 10⁴ M☉**. Rapport ~8,6 (le document du premier film dit 8). Adoucissement : 0,1 × (36 000/N)^(1/3)
≈ **33 pc** pour les étoiles, 4 fois plus (**~130 pc**) pour le halo. [Certain pour le code ; calculé pour les valeurs]

### 4.2 Ce que disent les pros

- **Chauffage parasite par la matière noire** (Ludlow et al. 2021 ; Wilkinson et al. 2023) : les particules de halo
  trop lourdes agitent les étoiles du disque, l'épaississent et le grossissent. Le chauffage est proportionnel à la masse
  des particules de halo, presque indépendant de celle des étoiles et de l'adoucissement (tant que l'adoucissement est
  plus petit que l'épaisseur du disque). Un halo de moins d'environ 10⁶ particules chauffe le disque de façon visible en
  un temps de Hubble ; à 10⁶ M☉ par particule, l'agitation verticale à 5 Ga est multipliée par ~1,5. [Certain, résumé lu]
- **Nous avons fait le bon essai** : halo 4 fois plus fin (10,85 M de particules) → même épaississement
  (`deuxieme-film.md`, écart 4). Avec 2,45 M de particules de halo à 5,6 × 10⁵ M☉, nous sommes juste sous le seuil de
  Ludlow ; c'est cohérent avec l'essai. **Le grain n'est pas le coupable principal.** [Certain pour l'essai ; Probable
  pour l'interprétation]
- **Particules de même masse** : Ludlow recommande μ ≈ 1 (matière noire et étoiles de même masse) pour éviter la
  ségrégation de masse. Nous sommes à 8,6. Coût de passer à μ ≈ 2 : ~4 fois plus de particules de halo. Pas prioritaire
  vu l'essai ci-dessus. [Certain pour la recommandation ; Supposition pour la priorité]
- **Adoucissement** : la règle de Power et al. 2003 (ε ≈ 4 r200 √(m/M200)) donne quelques centaines de pc pour une
  Voie lactée cosmologique, ce qu'utilise Auriga. Nos 33 pc pour les étoiles sont **plus petits** que ce que la règle
  donnerait [Supposition, non calculé exactement] : c'est permis tant que le pas de temps suit (voir § 5). FIRE adapte
  l'adoucissement du gaz à sa longueur de lissage ; nous non, et c'est un point à régler quand le gaz entre dans le
  grand calcul : un gaz à h = 20 pc avec un adoucissement gravitaire fixe différent est incohérent. [Probable]

---

## 5. Pas de temps : notre défaut technique le plus net

### 5.1 Ce que font les pros [Certain pour FIRE (résumé de l'article) ; Probable pour GADGET et AREPO, de mémoire]

**Tous** utilisent des pas **individuels**, rangés en puissances de deux (pas hiérarchiques) : chaque particule avance
au pas que demande sa situation, et les voisines ne diffèrent pas de plus d'un facteur 4 (FIRE). Critères :
- gravité : Δt < √(2 η ε / |a|), η ≈ 0,025 (GADGET) ; FIRE : Δt < 0,2 √(h/|a|) ;
- gaz : condition de Courant Δt < 0,3–0,4 h / v_signal ;
- convergence et divergence de l'écoulement (FIRE : Δt < 0,25/|∇·v|).

### 5.2 Ce que fait notre calcul [Certain, code lu]

Un **saute-mouton à pas unique** de 0,25 Ma pour toutes les particules (`rencontre.py`, `stabilite_tir.py`). Pour le gaz,
`gaz_galaxie.py` **mesure** le nombre de Courant mais ne l'**impose** pas.

### 5.3 Ce que ça donne, calcul ici [Certain pour les nombres ; Supposition pour les conséquences]

| Cas | Pas demandé | Pas utilisé | Verdict |
|---|---|---|---|
| Étoile à 100 pc du centre de la Voie lactée (a ≈ v²/r avec v ≈ 150 km/s), adoucissement 33 pc, η = 0,025 | ~0,06 Ma | 0,25 Ma | 4 fois trop grand au cœur |
| Étoile au rayon du Soleil | quelques Ma | 0,25 Ma | largement bon |
| Gaz au repos, h = 20 pc, v_signal ≈ 50 km/s, Courant 0,3 | ~0,12 Ma | 0,25 Ma | **2 fois trop grand** |
| Gaz choqué à la rencontre, v_signal ≈ 300 km/s | ~0,02 Ma | 0,25 Ma | **12 fois trop grand** : le gaz explose numériquement |

Conséquences :
1. **Pour le gaz, c'est bloquant.** Soit on divise le pas par 12 pour tout le monde (calcul 12 fois plus long : le futur
   passerait de ~22 h à ~11 jours), soit on fait des pas individuels (le coût monte seulement de ~1,5 à 3 fois, selon la
   part de particules au petit pas). [Supposition pour les facteurs]
2. **Pour les étoiles, c'est un suspect de plus** pour l'épaississement et le cœur qui « respire » : le pas est trop grand
   dans le centre (barre comprise). Il faut un **essai de convergence en pas** : même galaxie seule, 1 Ga, à 0,25 et à
   0,0625 Ma ; si l'épaississement change, c'est le pas. [Supposition, essai à faire]
3. **L'ouverture de l'arbre** (θ = 0,7 avec quadripôles) est dans la plage usuelle (Bonsai, GADGET en critère
   géométrique) [Probable] ; à contrôler dans le même essai (θ = 0,5), coût identique.

---

## 6. Calibration et validation : comment ils prouvent que c'est juste

### 6.1 La pratique [Certain pour EAGLE, Auriga, FIRE, Genel ; Probable pour TNG, de mémoire]

- **EAGLE** : les paramètres de rétroaction sont **réglés** sur la fonction de masse des galaxies à z ≈ 0,1, en tenant
  compte de leur taille (et de la relation trou noir–galaxie). Sont gardés **pour la validation** : la relation de
  Tully–Fisher, la relation masse–métallicité, les absorbeurs CIV et OVI. Définitions :
  **convergence forte** = même résultat à plus haute résolution **sans** toucher aux paramètres ; **convergence faible**
  = même résultat **après** re-réglage. EAGLE ne vise que la faible et le dit.
- **Auriga** : mêmes paramètres à tous les niveaux de résolution (3 à 5, facteur 64 en masse) ; c'est un test de
  convergence forte.
- **FIRE** : revendique **aucun réglage** (rétroaction tirée directement des modèles d'évolution des étoiles) et fait
  un article entier sur « physique contre numérique » : masses d'étoiles et profils sont robustes ; morphologie moins ;
  vents et gaz du halo le moins ; les concentrations centrales des grosses galaxies dépendent de la numérique.
- **IllustrisTNG** : réglé sur l'histoire du taux de naissance cosmique, la fonction de masse, la relation masse
  d'étoiles–masse du halo, la masse des trous noirs, le gaz des groupes et la taille des galaxies [Probable, de mémoire ;
  l'article n'a été lu qu'en résumé, qui ne les liste pas].
- **Chaos** (Genel et al. 2019) : deux calculs identiques à un déplacement de 10⁻⁷ pc près donnent des galaxies qui
  diffèrent de **2 à 25 %** selon la grandeur ; avec rétroaction, l'écart atteint un plancher qui ne baisse plus avec la
  résolution. Toute conclusion sur **une** galaxie doit être testée sur plusieurs graines.
- **Barres** : Roshan et al. 2021 trouvent que les barres d'IllustrisTNG et d'EAGLE sont trop lentes (rapport rayon de
  corotation / longueur de barre) à 10–13 σ des observations ; Auriga a 26 galaxies barrées sur 39 (Fragkoudi et al.
  2024). **La vitesse de la barre est une mesure de validation dure que la plupart des simulations ratent.**

### 6.2 Notre situation [Certain, code lu]

`bulletin.py` compare la galaxie du calcul à 9 mesures de la Voie lactée (naissances, masse d'étoiles, longueur et
vitesse de la barre, vitesse circulaire au Soleil, épaisseur des deux disques, agitation au Soleil, masse de gaz). C'est
exactement l'outil qu'il faut. Ce qui manque :
1. **La séparation** : rien ne dit lesquelles on règle et lesquelles on garde pour vérifier. Les fils règlent, en
   pratique, sur toutes. [Certain pour l'absence ; Supposition pour la pratique]
2. **Les autres galaxies** : aucun bulletin pour Andromède, le Triangle, les Nuages.
3. **La dimension temporelle** : les mesures sont « aujourd'hui ». Les pros valident aussi des **relations** (âge contre
   agitation des étoiles, profil vertical selon l'âge) qui disent si l'histoire est plausible. [Probable]
4. **Les graines** : un film = une graine.
5. **La convergence** : faite pour le grain du halo (bien), pas pour le pas de temps, pas pour le gaz.

### 6.3 Proposition de partage [Supposition, mon jugement]

| Rôle | Mesures | Pourquoi |
|---|---|---|
| **Imposées par construction** (pas des tests) | positions et vitesses d'aujourd'hui des cinq galaxies ; vitesse circulaire au Soleil ; masses (table unique) | ce sont les entrées |
| **Réglage (calibration)** | naissances de la Voie lactée (1,65 M☉/an) → efficacité de naissance ; longueur et vitesse de la barre → départ du centre | un paramètre par mesure, déclaré d'avance |
| **Vérification (validation)**, jamais réglées | épaisseur des disques mince et épais ; agitation au Soleil ; relation âge–agitation ; naissances d'Andromède et du Triangle ; masse de gaz restante ; courbes de rotation d'Andromède et du Triangle ; longueur et angle de la barre d'Andromède ; date de fusion comparée à l'ensemble d'orbites | ce sont elles qui disent si le calcul est juste |

Règle, comme EAGLE : **si on règle sur une mesure de vérification, elle passe dans la colonne réglage et on le dit**.

---

## 7. Recommandations ordonnées, avec leur coût

Base de coût [Certain, mesurée] : le futur du premier film (9,8 M de particules de masse, 8,5 M de traceurs, 10 Ga) a pris
~22 h de carte, soit **~0,22 h par million de particules et par Ga** ; un essai de Voie lactée seule (3,5 M) sur 5 Ga
prend ~1 h (PR 102). Les coûts du gaz sont des **suppositions** (SPH ~3 à 5 fois plus cher par particule que la gravité
seule, à mesurer au premier essai).

| # | Quoi | Pourquoi (pratique pro) | Fini quand | Carte graphique | Travail de fil |
|---|---|---|---|---|---|
| **1** | **Protocole écrit** : tableau réglage / vérification (§ 6.3) dans `mesures_voie_lactee.json` (champ `role`), bulletins pour Andromède et le Triangle, verdict publié avec chaque film | EAGLE, Auriga, FIRE | `bulletin.py` sort deux colonnes et refuse un film sans bulletin | **0 h** | ½ à 1 jour |
| **2** | **Essai de convergence en pas et en ouverture** : Voie lactée seule, 1 Ga, pas 0,25 / 0,125 / 0,0625 Ma, θ 0,7 / 0,5 | Power 2003 ; FIRE « physique contre numérique » | on sait si l'épaississement et la barre dépendent du pas | **~1 à 2 h** (5 tirs courts, le plus fin coûte 4 fois plus) | ½ jour |
| **3** | **Pas individuels hiérarchiques** dans `rencontre.py` et `stabilite_tir.py` (puissances de deux, critère gravité + Courant + divergence pour le gaz) | tous les codes pro | essai d'Evrard et galaxie seule identiques à pas fin unique, en moins de temps | essais **~2 h** | 2 à 3 jours (le plus gros morceau de code) |
| **4** | **Gaz à pression effective** à la place de l'isotherme + plancher : P ∝ ρ^4/3 au-dessus du seuil (EAGLE), ou modèle en deux phases (Springel–Hernquist, Auriga) ; **naissance réglée sur une seule mesure** (1,65 M☉/an) ; **retour de masse** des populations (MIST, déjà dans le projet) ; gaz chaud permis (énergie interne suivie, refroidissement par une table simple) | Auriga, EAGLE | Voie lactée seule 2 Ga : naissances dans la marge, gaz restant cohérent ; validation sur Andromède et le Triangle sans re-réglage | **~3 à 6 h** (quelques tirs de 2 Ga avec gaz) | 3 à 4 jours |
| **5** | **Barre : deux leviers en parallèle**, sur la Voie lactée seule : (a) halo en rotation (PR 102, déjà mesuré : 25–33 km/s/kpc) ; (b) centre plus dominé par les étoiles (moins de matière noire dans 3 kpc, en restant sur la courbe de rotation ; Portail 2017 trouve un centre très dominé par les étoiles [À vérifier : non relu]) ; garder celui qui tient 39 ± 3,5 km/s **sans** épaissir. Attention : Collier 2018 trouve que le halo en rotation peut aussi affaiblir puis dissoudre la barre après le flambage | Roshan 2021, Collier 2018, Li 2022 | barre à 39 ± 7 km/s/kpc et 5 kpc à t = 0, qui ne grossit plus de 50 % en 5 Ga | **~2 à 4 h** (4 tirs de 5 Ga) | 1 jour |
| **6** | **Ensemble de films en petit** : 4 à 6 graines à 20 % de résolution (~2 M de particules), du passé à +10 Ga, avec le meilleur réglage | Genel 2019 | on sait quelles formes (barre, queues, date de fusion, sort du Triangle) sont robustes ; l'appli peut dire « robuste » ou « varie selon le tirage » | **~1 à 2 jours** (~4 à 5 h par graine sans gaz ; double avec gaz) | ½ jour |
| **7** | **Sagittaire** (et M32 pour Andromède) comme sixième et septième corps | Vasiliev 2021 | la rotation du disque de la Voie lactée garde ses ondulations mesurées [Probable] | ~10 % de plus sur chaque film | 1 jour |
| **8** | **Film 4 avec gaz** à pleine résolution, seulement après 1 à 6 | — | bulletin complet vert sur la colonne vérification | **~2 à 4 jours** (10 M de particules, gaz compris, pas individuels) [Supposition] | attente |
| plus tard | couronne de gaz chaud, accrétion cosmique, SPH moderne (pression-entropie), particules de même masse (μ ≈ 1) | HESTIA, Auriga, Ludlow 2021 | — | facteur 2 à 4 sur chaque film | chantiers à part |

**Total des étapes 1 à 7 : environ 2 à 3 jours de carte**, dont l'essentiel est l'ensemble (6). Les étapes 1, 2 et 5
peuvent commencer tout de suite ; 2 et 5 se partagent la carte avec le calcul en cours (veilleur).

### Ce que je déconseille [Supposition, mon jugement]

- **Lancer le film 4 avec le gaz actuel** (isotherme, sans rétroaction, pas unique) : le gaz sera faux dans les chocs, et
  on paiera 2 à 4 jours de carte pour un film qu'on ne pourra pas défendre.
- **Passer aux conditions initiales cosmologiques** (HESTIA) : ça donnerait un Groupe local plausible mais pas le nôtre ;
  c'est contraire à la consigne de Marc (le ciel d'aujourd'hui) et ça coûterait des semaines.
- **Chercher FIRE** (rétroaction explicite) : il faut ~10³ M☉ par particule de gaz, soit ~100 fois plus de particules
  que nous ; hors de portée d'une carte.
- **Régler la barre à la main jusqu'à 39 km/s/kpc par n'importe quel moyen** : les simulations pro ne l'obtiennent pas
  non plus ; si on la force (barre guide permanente), il faut l'afficher comme modèle.

---

## 8. Ce que ce document ne règle pas

- Je n'ai pas relu tout le code du calcul : les remarques portent sur `rencontre.py`, `modeles_v2.py`, `stabilite_tir.py`,
  `gaz_gpu.py`, `gaz_galaxie.py`, `essai_gaz.py`, `bulletin.py` et les deux documents de contrôle.
- Les pas de temps « demandés » du § 5.3 sont des ordres de grandeur ; l'essai 2 les remplace par des mesures.
- Plusieurs articles n'ont été lus qu'en résumé, et certaines sections longues n'ont été lues qu'en partie (indiqué).
- Les coûts du gaz sont des suppositions jusqu'au premier essai.

---

## 9. Sources

Lues ce jour (texte ou résumé, indiqué dans le corps) :
- Carlesi et al. 2016, CLUES, « A Local Group factory » : https://arxiv.org/abs/1602.03919
- Libeskind et al. 2020, HESTIA (MNRAS 498, 2968) : https://researchonline.ljmu.ac.uk/id/eprint/19297/
- Sawala et al. 2016, APOSTLE : https://arxiv.org/abs/1511.01098
- Fattahi et al. 2016, APOSTLE, sélection des paires (MNRAS 457, 844) : https://researchonline.ljmu.ac.uk/id/eprint/3669/
- Grand et al. 2017, Auriga : https://arxiv.org/abs/1610.01159
- Fragkoudi et al. 2024, barres dans Auriga : https://arxiv.org/abs/2406.09453
- Hopkins et al. 2018, FIRE-2, physique contre numérique : https://arxiv.org/abs/1702.06148
- Furlong et al. 2015, EAGLE (calibration et recette résumées, d'après Schaye 2015 et Crain 2015) : https://arxiv.org/abs/1410.3485
- Pillepich et al. 2018, modèle IllustrisTNG (résumé seulement) : https://arxiv.org/abs/1703.02970
- Ludlow et al. 2021, chauffage parasite des disques : https://arxiv.org/abs/2105.03561
- Wilkinson et al. 2023, effet sur la morphologie : https://arxiv.org/abs/2208.07623
- Genel et al. 2019, effet papillon : https://arxiv.org/abs/1807.07084
- Roshan et al. 2021, barres trop lentes dans TNG et EAGLE : https://arxiv.org/abs/2106.10304
- Collier, Shlosman et Heller 2018, barres dans des halos en rotation : https://arxiv.org/abs/1712.02802
- Li, Shlosman, Heller et Pfenniger 2023, barres sans ralentissement dans des halos en rotation : https://arxiv.org/abs/2211.04484
- Makarov et al. 2025, masse du Groupe local par le flot de Hubble : https://arxiv.org/abs/2505.06642
- Contreras-Santos et al. 2026, NIVARIA-LG : https://arxiv.org/abs/2610.15071

Citées de mémoire, non relues ce jour [Probable] : Springel et Hernquist 2003 (modèle en deux phases) ; Schaye et Dalla
Vecchia 2008 (loi de Kennicutt–Schmidt en pression) ; Dalla Vecchia et Schaye 2012 (supernovae thermiques stochastiques) ;
Power et al. 2003 (adoucissement et pas) ; Agertz et al. 2007 (défauts de la SPH) ; Hopkins 2013 (SPH pression-entropie) ;
Cullen et Dehnen 2010 (viscosité variable) ; Leitner et Kravtsov 2011 (retour de masse) ; Bate et Burkert 1997, Robertson
et Kravtsov 2008 (plancher de Jeans) ; Vasiliev, Belokurov et Erkal 2021 (déjà dans la PR 95) ; Portail et al. 2017 ;
Licquia et Newman 2015 (déjà relu par le fil du calcul).
