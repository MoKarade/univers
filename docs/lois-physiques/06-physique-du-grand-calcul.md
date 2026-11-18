# Annexe 6 — Physique du grand calcul (film du Groupe local, branche film-3)

Lecture seule de `/home/claude/film-3` le 18/11/2026. Aucun calcul GPU lancé, aucun fichier du dépôt modifié. Les
chiffres « calculés ici » viennent de petites formules évaluées sur processeur (masses de particules, fréquences,
ordres de grandeur). Labels : [Certain] lu aujourd'hui dans le code ou la source ; [Probable] publié, cité de mémoire ;
[Supposition] mon raisonnement ; [À vérifier] non vérifié.

## Résumé

- **Le gaz n'est pas dans le film.** `gaz_gpu.py` / `gaz_galaxie.py` ne sont appelés que par `stabilite_tir.py --gaz=1`
  (galaxie seule). `rencontre.py`, qui fait le film des cinq galaxies, n'a ni pression, ni chocs, ni naissance
  d'étoiles : les particules « gaz » (sorte 3) y restent des étoiles froides sans collision. [Certain]
- **Gravité** : arbre de Barnes-Hut binaire (Karras 2012) avec quadripôles, θ = 0,7, adoucissement de Plummer par
  particule (≈ 32 pc pour les étoiles, ≈ 130 pc pour la matière noire de la Voie lactée), forces en simple précision,
  positions et vitesses en double. Saute-mouton KDK à pas **fixe et unique** de 0,25 Ma. Énergie tenue à 0,04–0,055 %.
  La quantité de mouvement et le moment cinétique ne sont pas conservés exactement (arbre non symétrique) et ne sont
  pas suivis dans le journal. [Certain]
- **Énergie noire** : a = H0² Ω_Λ (x − x_cm), K = 3,1118 × 10⁻³ (km/s)²/kpc², coordonnées physiques, repère du centre
  de masse. La formule est exacte pour w = −1 et K est alors constant dans le temps. Elle manque dans
  `stabilite_tir.py` (mûrissement des galaxies seules) : effet ≤ 0,9 % au bord du halo, mais la règle « jamais
  négligée » n'y est pas tenue. [Certain]
- **Alerte de mesure à lever avant toute physique** : avec un relevé tous les 50 Ma (valeur par défaut de
  `stabilite_tir.py`), une barre à 39 km/s/kpc se lit 22,4 km/s/kpc par repliement (limite de lecture : 30,7 km/s/kpc),
  et `bulletin.py` prend la valeur absolue de la pente. Les « 17 à 28 » mesurés correspondraient à 33–44 vrais.
  À vérifier sur les images à 10 Ma du film ; la taille de la barre (jusqu'à 8 kpc) plaide plutôt pour une barre
  réellement lente. [Certain pour l'arithmétique ; À vérifier pour ce qui a été réellement mesuré]
- **Barre lente et qui grossit : c'est le comportement attendu de ce code.** Halo vivant sans rotation, pas de gaz
  dissipatif, barre née d'un centre à Q ≈ 0,9 sans bulbe sphérique : le halo freine la barre par frottement dynamique
  (Debattista & Sellwood 2000), et rien ne lui rend de moment cinétique. Beane et al. 2023 : −43 % de vitesse en 4 Ga
  sans gaz, vitesse stable avec ~5 % de gaz. Long, Shlosman & Heller 2014 : le freinage et la croissance s'éteignent
  quand le halo tourne (λ ≳ 0,03). [Certain pour le code ; Certain pour les deux résumés relus]
- **Chauffage numérique** : m_DM ≈ 5,6 × 10⁵ M☉ pour la Voie lactée, juste à la limite de Ludlow et al. 2021
  (≤ 5,9 × 10⁵ pour Δσ_z ≤ 16 km/s en 10 Ga). Petit pour les vieilles étoiles (accord avec l'essai n° 4 de
  `deuxieme-film.md`), **pas petit pour les étoiles jeunes** (σ_z ≈ 5–7 km/s) : il explique une part de leur
  épaississement. Le critère du code (« rapport de masses < 10 ») n'est pas le bon : c'est la masse absolue de la
  particule de matière noire qui compte. [Certain pour le code et la source ; Supposition pour la part chiffrée]
- **Gaz tel qu'écrit** : SPH classique (spline cubique, η = 1,2, viscosité de Monaghan α = 1, β = 2, Balsara),
  isotherme à 10 km/s, plancher de Jeans, naissance d'étoiles à 1 % par temps de chute libre au-dessus de
  n_H = 0,1 cm⁻³, masse conservée par changement de sorte. Pas de refroidissement, pas de rétroaction, pas de retour
  de masse, pas d'accrétion. Trois défauts sérieux : le gaz de départ a 31 km/s d'agitation (Mach 3) ; le nombre de
  Courant n'est que affiché, jamais respecté ; l'épaisseur du disque de gaz n'est pas résolue (h ≈ 130 pc pour 85 pc).
- **Lecture du film** : une image tous les 10 Ma, positions seules sur 16 bits, courbe de Catmull-Rom. Sous ~0,6 kpc
  du centre, la période orbitale (10–20 Ma) est sous-échantillonnée : les orbites du bulbe sont repliées à l'écran.
- Les valeurs publiées des modèles de galaxies sont fidèlement recopiées (McMillan 2017, Tamm 2012, Corbelli 2014,
  Erkal 2019). Écarts de modèle : gaz de la Voie lactée sans son trou central, halos sphériques non contractés et
  sans rotation, pas de trou noir central, pas de Sagittaire, pas de gaz chaud.

---

## 1. Ce qui tourne réellement

| Étape | Fichier | Physique |
|---|---|---|
| Galaxies de départ | `modeles_v2.py` (AGAMA) | équilibre sans collision ; « gaz » = disque froid sans collision |
| Mûrissement, galaxie seule | `stabilite_tir.py` | gravité ; option `--guide` (barre guide), `--halo-tourne`, `--gaz=1` ; **pas d'énergie noire** |
| Passé −1 Ga → 0, puis futur 0 → +10 Ga | `rencontre.py` (`lancer_rencontre.sh`) | gravité + énergie noire ; **pas de gaz** |
| Ancien calcul (R9) | `calcul.py`, `modeles.py`, `conditions.json` | falcON ou arbre GPU + énergie noire ; gardé pour refaire l'ancien |
| Lecture | `film_v2.py`, `natif/physique/film_v2.h`, `natif/src/film_etoiles.h` | interpolation |

Le seul appel à `gaz_galaxie` de tout le dépôt est `stabilite_tir.py:144`. `rencontre.py:119-126` (`Calcul.forces`)
n'appelle que `gravite_gpu.gravity` et l'énergie noire. [Certain] La phrase du brief « désormais gaz, naissance
d'étoiles » ne vaut donc, dans cette branche, que pour une galaxie seule mûrie avec `--gaz=1` ; les étoiles nées
(sorte 5) sont alors portées dans le `.npz` d'arrivée (`stabilite_tir.py:204-205`) mais redeviennent de simples
particules sans collision dans le film, et le gaz restant aussi.

## 2. Gravité

### 2.1 Algorithme [Certain, `gravite_gpu.py`]

| Point | Ce que fait le code | Ligne |
|---|---|---|
| Méthode | arbre binaire sur codes de Morton 63 bits (Karras 2012), parcours par particule (Barnes & Hut 1986) | 26-57, 105-142 |
| Ouverture | groupe accepté si r > taille/θ + \|centre de masse − centre de boîte\| (Barnes 1994) ; taille = plus grand côté de la boîte ajustée | 81-88, 120 |
| θ | 0,7 dans `rencontre.py:105` et `stabilite_tir.py:108` ; 0,5 par défaut dans la fonction | 191 |
| Multipôles | monopôle + quadripôle (somme m dx dx, trace non retirée, formule cohérente) | 89-94, 126-136 |
| Adoucissement | Plummer, s² = r² + (ε_i² + ε_j²)/2 ; pour un groupe, ε² moyen pondéré par la masse | 98, 123 |
| Précision | forces et potentiel en float32, positions recentrées sur la médiane avant conversion ; sommes du nœud en double | 206-208, 78-98 |
| Boîte de Morton | 3 × le rayon contenant 99,5 % des particules, autour de la médiane ; le reste est rangé au bord | 200-203 |
| Pile de parcours | 160 entrées ; au-delà de 158, les enfants sont **abandonnés sans message** | 113, 138 |

Contrôle fourni (`test_gravite_gpu.py`) : erreur médiane de force < 0,4 % et 99ᵉ centile < 2 % exigés à θ = 0,7 avec
quadripôles ; le commentaire de `calcul.py` donne 0,1 % en médiane mesurée. [Certain pour les seuils ; la mesure
elle-même n'a pas été refaite ici]

Jugement :

- La méthode est saine et standard. La précision de force (≈ 10⁻³) est du même ordre que celle de GADGET-4 en usage
  courant. [Probable]
- L'auto-attraction est exclue correctement : avec le terme de décalage, une particule ne peut pas accepter un groupe
  qui la contient tant que θ < 1,15. [Supposition : borne géométrique calculée ici, (√3/2)·taille + décalage <
  taille/θ + décalage]
- La pile de 160 suffit : la profondeur d'un arbre de Karras est bornée par 63 bits + 32 bits de départage = 95.
  Le garde-fou silencieux de la ligne 138 devrait néanmoins compter les abandons : une force tronquée ne se verrait
  que par l'énergie. [Supposition]
- Simple précision : à 400–800 kpc de la médiane, le pas d'un float32 vaut 3–6 × 10⁻⁵ kpc, soit 0,03–0,06 pc, mille
  fois moins que l'adoucissement (32 pc). Erreur relative sur une paire séparée de ε : ~10⁻³. Acceptable.
  Le commentaire de `gaz_gpu.py:20-21` (« à 800 kpc la simple précision ne distingue plus 60 pc ») se trompe d'un
  facteur 1 000 : c'est 0,06 pc. La contrainte « galaxie par galaxie » du gaz est donc plus lâche qu'annoncé.
  [Certain : 800 / 2²⁴ = 4,8 × 10⁻⁵ kpc]
- Un commentaire (lignes 195-199) parle de particules de halo parties « à des millions de kpc ». En 11 Ga, cela
  demanderait 10⁵ km/s : aucune physique newtonienne du Groupe local ne le donne, l'énergie noire non plus (temps de
  doublement 1/√K ≈ 17,5 Ga). Soit c'est une façon de parler (des milliers de kpc), soit il y a eu un vrai défaut
  numérique à retrouver. [À vérifier]

### 2.2 Adoucissement et résolution [calculé ici depuis `modeles_v2.py:152-158`, avec 70 % de particules au halo]

ε_étoiles = 0,1 kpc × (36 000 / N_étoiles)^(1/3) ; ε_halo = 4 ε_étoiles.

| Galaxie (film 1 : particules) | m_DM (M☉) | m_étoile (M☉) | rapport | ε étoiles | ε halo |
|---|---|---|---|---|---|
| Voie lactée (3,5 M) | 5,6 × 10⁵ | 6,4 × 10⁴ | 8,7 | 32 pc | 130 pc |
| Andromède (4 M) | 3,7 × 10⁵ | 7,7 × 10⁴ | 4,8 | 31 pc | 124 pc |
| Triangle (1 M) | 5,7 × 10⁵ | 2,6 × 10⁴ | 22 | 49 pc | 197 pc |
| Grand Nuage (1 M) | 1,9 × 10⁵ | 9,0 × 10³ | 21 | 49 pc | 197 pc |

- 32 pc est petit devant la hauteur du disque mince (300 pc) et devant l'épaisseur mesurée de la barre (180 pc) :
  l'adoucissement ne gonfle pas le disque et ne retarde pas la barre. Il est inférieur à l'écart moyen entre
  particules d'étoiles au Soleil (≈ 90 pc) : le calcul n'est pas « sur-adouci ». [Supposition, calcul ici]
- Les traceurs (étoiles visibles, sorte 9) ont une masse de 1 M☉ et ε = 50 pc (`rencontre.py:519`). Ils s'attirent
  et attirent : 8,5 × 10⁶ M☉ ajoutés d'un coup à t = 0 (3 × 10⁻⁶ de la masse totale). Sans effet dynamique, mais
  c'est une entorse à « la masse est conservée » qu'un facteur 10⁻⁶ sur leur masse ferait disparaître. [Certain]

### 2.3 Intégrateur et pas de temps [Certain]

- Saute-mouton « coup-glissement-coup » (KDK), symplectique, ordre 2 : `rencontre.py:132-136`,
  `stabilite_tir.py:189-192`. Pas fixe **0,25 Ma pour toutes les particules** (`rencontre.py:199`), soit
  2,557 × 10⁻⁴ kpc/(km/s) ; 40 000 pas pour 10 Ga.
- Unité de temps : `T_UNIT = 0.9778` Ga (`rencontre.py:38`) ; la valeur exacte est 0,977792 (celle de
  `film_v2.py:24`, 1/1,0227121650456). Écart 8 × 10⁻⁶, soit 80 000 ans sur 10 Ga : négligeable mais deux constantes
  pour la même chose.
- Suffisance du pas [calculé ici] :

| Lieu | Temps propre | Pas par temps propre |
|---|---|---|
| orbite à 2 kpc (210 km/s) | 58 Ma | 234 |
| orbite à 0,5 kpc | 17 Ma | 68 |
| orbite à 0,2 kpc (bulbe de McMillan, r0 = 75 pc) | 10 Ma | 40 |
| traversée de ε = 32 pc à 200 km/s | 0,16 Ma | **0,6** |
| critère usuel 0,2 √(ε/a) à 0,1 kpc | 0,11 Ma | **0,45** |

  Le pas est bon pour le disque et la barre, **deux fois trop long au cœur** (r < 0,2 kpc) selon le critère usuel
  η√(ε/|a|) (Power et al. 2003, MNRAS 338, 14) [Probable]. L'énergie globale ne le voit pas : le cœur pèse peu.
  Conséquence attendue : cœur un peu gonflé, cuspide du bulbe adoucie. [Supposition]

### 2.4 Lois de conservation

| Grandeur | État | Preuve dans le code |
|---|---|---|
| Masse | conservée exactement pendant un calcul ; +8,5 × 10⁶ M☉ de traceurs à t = 0 | aucun terme source ; `rencontre.py:519` |
| Énergie | suivie : E = ½Σmv² + ½Σmφ − ½KΣm d² ; écart 0,04 % (film 2), 0,055 % (film 1) | `rencontre.py:128-130`, docs |
| Quantité de mouvement | **non conservée exactement** : parcours par particule, paires non symétriques. Non journalisée dans `rencontre.py` ; `stabilite_tir.py` écrit le déplacement du centre de masse | `stabilite_tir.py:171` |
| Moment cinétique | non conservé exactement, **non suivi** | — |

Le bilan d'énergie de `rencontre.py` est correct : le potentiel extérieur −½K d² est compté une fois, le potentiel
mutuel avec le facteur ½. Celui de `calcul.py:120, 146` (φ + 2 φ_Λ, puis ½) est équivalent. [Certain]

Avec `--gaz=1`, le bilan de `stabilite_tir.py:163-164` (cinétique + gravité seulement) **n'a plus de sens** : un gaz
isotherme rayonne ce que la viscosité dissipe, l'énergie doit baisser. Le chiffre « énergie » affiché n'est alors
plus un contrôle. [Certain]

## 3. Énergie noire

### 3.1 Formule de référence

Pour un fluide d'équation d'état w, l'accélération relative de deux points dans un milieu homogène est
r̈ = −(4πG/3)(ρ + 3p/c²) r. Pour l'énergie noire seule : r̈ = −(4πG/3)(1 + 3w) ρ_DE r. Avec w = −1 et
ρ_Λ = 3 Ω_Λ H0² / (8πG) : **a_Λ = + Ω_Λ H0² r**, constante dans le temps. [Certain : dérivation standard ; même
formule dans Peñarrubia et al. 2014, MNRAS 443, 2204, et Partridge, Lahav & Hoffman 2013, MNRAS 436, L45 — Probable
pour les références, citées par le code et non relues ici]

### 3.2 Ce que fait le code [Certain]

- `energie_noire.py:20-23` : H0 = 67,4 km/s/Mpc, Ω_Λ = 0,685 (Planck 2018 VI, A&A 641, A6), K = (0,0674)² × 0,685 =
  3,11179 × 10⁻³ (km/s)²/kpc². Même valeur dans `univers.json` (`cosmologie.K_lambda`), lue par
  `rencontre.py:113`.
- `rencontre.py:122-125` : acc += K (x − x_cm), x_cm = centre de masse des particules de masse, recalculé à chaque
  pas. Coordonnées **physiques** (pas comobiles), pas de facteur d'échelle, pas de fond de matière : le Groupe local
  est traité comme isolé dans le vide avec Λ. Par symétrie sphérique, la matière extérieure homogène n'agit pas ;
  les marées des voisins (Centaurus A, M81, Virgo) sont absentes. [Certain pour le code ; Probable pour la
  justification]
- La somme des forces de Λ sur les particules de masse est nulle par construction : Λ ne déplace pas le centre de
  masse.
- Ordres de grandeur [calculé ici] : 13,8 % de l'attraction à 770 kpc pour 2,4 × 10¹² M☉ ; 0,9 % à 250 kpc ;
  0,007 % au Grand Nuage ; 4 × 10⁻⁶ au Soleil. Rayon où Λ équilibre la gravité : (GM/K)^(1/3) ≈ 1,49 Mpc.

### 3.3 Écarts

| Écart | Où | Impact |
|---|---|---|
| Pas d'énergie noire dans le mûrissement des galaxies seules | `stabilite_tir.py:147-156` | faible (≤ 0,9 % au bord du halo), mais contraire à la règle de Marc ; deux lignes à ajouter |
| Les équilibres AGAMA sont construits sans Λ | `modeles_v2.py:111-136` | faible : léger déséquilibre du halo externe au départ |
| w = −1 figé | `energie_noire.py:15` (dit à l'écran) | selon le modèle : pour w(a) ≠ −1, K devient K(t) = −½(1 + 3w) Ω_DE(a) H0² ; DESI DR2 préfère w0 > −1, wa < 0 [Probable, non relu ici] |
| Pas de champ de marée extérieur | — | faible sur 10 Ga pour la paire VL–M31 [Supposition] |

## 4. Référentiel

- Calcul : centre de masse au repos à l'assemblage (`rencontre.py:97-98`), non recentré ensuite. Axes : repère
  `phys::galaxie` de l'appli. [Certain]
- Sorties : centres et vitesses **relatifs à la Voie lactée** (`rencontre.py:208`), étoiles **relatives au centre de
  leur galaxie d'origine** (`rencontre.py:556`). Centre = sphère qui rétrécit sur les étoiles (sortes 1, 2, 4),
  `rencontre.py:138-152`.
- Deux retouches de repère à t = 0, documentées : rotation de chaque galaxie de départ autour de son axe pour caler
  la barre (`--angles`), et rotation d'un bloc de la Voie lactée (halo compris) pour remettre le disque dans le plan
  mesuré (`caler_plan.py:36-43`, 1,6°). La seconde crée une petite incohérence : les Nuages ne tournent pas avec
  elle (1,6° à 50 kpc = 1,4 kpc). [Certain pour le code ; Supposition pour le chiffre]

## 5. Gaz (tel qu'écrit, utilisé seulement en galaxie seule)

### 5.1 Méthode [Certain, `gaz_gpu.py`]

| Élément | Choix du code | Ligne | Référence |
|---|---|---|---|
| Schéma | SPH « densité-énergie » classique, sans termes de gradient de h | 7-15 | Monaghan 1992, ARA&A 30, 543 |
| Noyau | spline cubique M4, support 2h | 36-48 | Monaghan & Lattanzio 1985 |
| Longueur de lissage | h = 1,2 (m/ρ)^(1/3), ~58 voisines ; moyenne ½(ancien + cible), 2 passes par pas en production | 30, 188-194 ; `gaz_galaxie.py:55` | — |
| Symétrie | noyau moyen ½[∇W(h_i) + ∇W(h_j)], forces égales et opposées | 131, 141 | — |
| Viscosité | Monaghan α = 1, β = 2, μ = h̄ v·r/(r² + 0,01 h̄²) | 31, 135-139 | Monaghan 1992 |
| Interrupteur | Balsara : \|∇·v\| / (\|∇·v\| + \|∇×v\| + 10⁻⁴ c/h) | 204 | Balsara 1995 |
| Vitesse de signal | c̄ − 3 v·r/r | 139 | — |
| Voisines | même arbre que la gravité, boîtes + h maximal par nœud | 56-74, 121-122 | — |
| Précision | float32, positions depuis la médiane du gaz, vitesses depuis la moyenne | 165-167 | — |

Contrôles (`essai_gaz.py`) : gradient connu à 4 %, tube à choc isotherme à 6 %, effondrement d'Evrard avec énergie
à 3 %. Seuils raisonnables pour ce schéma. [Certain pour les seuils]

Conservation : quantité de mouvement et moment cinétique du gaz conservés par paire (forces centrales symétriques)
à la précision simple. Sans les termes de gradient de h (Springel & Hernquist 2002, MNRAS 333, 649 [Probable]),
l'énergie et l'entropie ne le sont pas exactement à h variable ; sans importance en isotherme. [Supposition]

### 5.2 Équation d'état, refroidissement [Certain, `gaz_galaxie.py`]

- Isotherme, c_s = 10 km/s (l. 29) : P = ρ c_s². Ni chauffage ni refroidissement calculés ; `dudt` est calculé puis
  ignoré. Une seule phase tiède ; pas de phase froide (où naissent réellement les étoiles), pas de gaz chaud.
- Plancher de Jeans (l. 30, 58-60) : c² ≥ Gρ(4h)²/π. [calculé ici] Comme h ∝ ρ^(−1/3), ce plancher ne dépasse
  10 km/s que lorsque h bute sur `H_MIN` = 20 pc (ρ ≳ 1,4 × 10¹⁰ M☉/kpc³, n_H ≳ 400 cm⁻³). Il est donc presque
  toujours inactif ; l'équation d'état effective est isotherme.
- À c_s = 10 km/s et n_H = 10 cm⁻³, la masse de Jeans vaut ~1,8 × 10⁷ M☉, soit ~280 particules de 6,4 × 10⁴ M☉ :
  résolue au sens de Bate & Burkert 1997 (≥ 2 × 58 particules). [Supposition, calcul ici]

### 5.3 Naissance d'étoiles [Certain, `gaz_galaxie.py:65-80`]

- Critère : densité seule, n_H > 0,1 cm⁻³ (ρ > 3,25 × 10⁶ M☉/kpc³). Pas de critère de convergence, de température,
  de liaison gravitationnelle.
- Taux : loi de Schmidt, probabilité 1 − exp(−0,01 dt / t_chute) par pas, t_chute = √(3π/(32Gρ)).
  [calculé ici] t_chute = 142, 45, 14, 4,5 Ma pour n_H = 0,1, 1, 10, 100 ; temps d'épuisement 14, 4,5, 1,4, 0,45 Ga.
- Conversion : la particule entière change de sorte (3 → 5), même masse, même position, même vitesse, même ε.
  **Masse conservée exactement.** La date de naissance est gardée.
- Conversion d'unités vérifiée : 1 M☉/pc³ = 40,46 protons/cm³, × 0,76 d'hydrogène. [Certain]
- Référence de taux : Voie lactée 1,65 ± 0,19 M☉/an (Licquia & Newman 2015, dans `mesures_voie_lactee.json`).
  Avec 1,22 × 10¹⁰ M☉ de gaz à n_H ~ 1, le modèle donne ~2,7 M☉/an : bon ordre de grandeur. [Supposition]

### 5.4 Ce qui manque ou cloche

| # | Constat | Où | Conséquence |
|---|---|---|---|
| G1 | **Gaz de départ agité à ~31 km/s** : la sorte 3 est tirée comme un disque d'étoiles à Q ≥ 1,5 contre tous les disques (σ_R = 1,5 × 3,36 G Σ_tot/κ = 31 km/s au Soleil, plus au centre) | `modeles_v2.py:43, 202-205` | à l'allumage de la pression, mouvements à Mach 3 : chocs partout, dissipation brutale, effondrement vertical et flambée de naissances. Un gaz doit partir sur des orbites circulaires corrigées de la pression, sans agitation |
| G2 | Nombre de Courant **affiché mais jamais imposé** ; pas fixe 0,25 Ma. Pour h = 20 pc et v_sig = 100 km/s : dt v_sig/h = 1,3 (il faut < 0,3) | `gaz_galaxie.py:52, 62` ; `stabilite_tir.py:179` | instabilité ou chocs faux dans les zones denses |
| G3 | Viscosité calculée avec la vitesse du demi-pas (v_{n+½}), alors que `essai_gaz.py:70, 108` prédit la vitesse au pas entier | `stabilite_tir.py:151, 189-192` | erreur du premier ordre sur la dissipation ; le code de production n'est pas celui qui a passé les contrôles |
| G4 | Épaisseur du gaz non résolue : h ≈ 0,13 kpc à 10 M☉/pc², 0,32 kpc au seuil de naissance, pour un disque de 0,085 kpc | calcul ici | densité au plan sous-estimée ; le seuil de naissance porte sur une densité lissée |
| G5 | Pas de rétroaction (supernovas, vents, rayonnement) | reconnu l. 17 | sans elle, un disque isotherme auto-gravitant se fragmente en gros grumeaux qui migrent vers le centre et chauffent les étoiles [Probable : résultat classique] |
| G6 | Pas de retour de masse des étoiles (~30–40 % en 10 Ga), pas d'accrétion (~1 M☉/an) | — | le gaz s'épuise en ~4–5 Ga : plus de naissances dans la seconde moitié du film |
| G7 | Pas de trou central dans le gaz de la Voie lactée (McMillan : HI troué à 4 kpc, H2 à 12 kpc) ; ici exponentielle pure de 7 kpc, 40 M☉/pc² au centre | `modeles_v2.py:43` | trop de gaz au centre, dans la zone de la barre |
| G8 | Les étoiles nées (5) ne sont comptées ni dans les relevés de barre et d'épaisseur de `stabilite_tir.py:40`, ni comme porteuses des étoiles jeunes dans `rencontre.py:354, 383` | — | les plus jeunes étoiles du calcul ne servent pas à poser les étoiles jeunes visibles |
| G9 | État du gaz non sauvegardé pour une reprise (h, tirage aléatoire) ; `stabilite_tir.py` n'a pas de reprise | — | à prévoir avant de brancher le gaz sur le film |
| G10 | Adoucissement de gravité du gaz = celui des étoiles (32 pc, équivalent spline ~90 pc) ≠ lissage hydrodynamique | — | l'effondrement est freiné sous ~90 pc : côté sûr [Supposition] |

## 6. Conditions initiales

### 6.1 Construction [Certain, `modeles_v2.py`]

- AGAMA : potentiel total (halo + bulbe + disques), puis fonctions de distribution : `QuasiSpherical` pour halo et
  bulbe (l. 155, 162), `QuasiIsothermal` pour chaque disque (l. 215-222), hauteur réglée par essais (l. 209-220).
- Halo : NFW (ou Hernquist) tronqué, **sphérique, sans rotation nette, non contracté par les baryons**.
  [Certain pour sphérique et tronqué ; Probable pour isotrope, valeur par défaut d'AGAMA]
- Disques : agitation radiale σ_R(R) = σ0 exp(−R/R_σ), R_σ = 2 R_d par défaut. Pour le disque mince de la Voie
  lactée : 35 km/s au Soleil ⇒ **181 km/s au centre** (l. 200-201), d'où l'absence de barre des modèles par défaut
  et les options `--froid`, `--froid-centre`, et la variante `voie_lactee_barre` (bulbe remplacé par un disque
  compact froid, l. 48-56).
- Petit Nuage : sphère de Plummer de 1,5 kpc si le `.npz` manque (`rencontre.py:89-93`) ; `univers.json` contient
  maintenant un modèle (Hernquist 3,09 × 10⁹ M☉, signalé comme modèle).

### 6.2 Valeurs contre les publications

| Galaxie | Dans le code | Publié | Verdict |
|---|---|---|---|
| Voie lactée, halo | NFW ρ0 = 8,54 × 10⁶ M☉/kpc³, r_s = 19,6 kpc, coupé à 250 kpc ; total 1,343 × 10¹² | McMillan 2017 (MNRAS 465, 76), table 3 : identique ; M_vir = 1,30 ± 0,30 × 10¹² | fidèle [Certain selon `parametres-galaxies.md`, « lu »] |
| disques | mince 896 M☉/pc², 2,50 kpc, 0,30 kpc ; épais 183, 3,02, 0,90 | identique | fidèle |
| bulbe | 9,84 × 10¹⁰ M☉/kpc³, r0 = 75 pc, pente 1,8, coupure 2,1 kpc, q = 0,5 | identique | fidèle |
| gaz | 1,22 × 10¹⁰ M☉, exponentielle 7 kpc, 85 pc | HI 1,1 × 10¹⁰ (troué à 4 kpc) + H2 1,2 × 10⁹ (1,5 kpc, troué à 12 kpc, 45 pc) | masse fidèle, **forme simplifiée** |
| barre (cible) | 5,0 kpc, 39 km/s/kpc, 28° | Portail et al. 2017 : 39,0 ± 3,5 ; Wegg et al. 2015 : 5,0 ± 0,2 kpc | fidèle, mais mesures plus récentes plus basses (§ 7.1) |
| Andromède | NFW 1,10 × 10⁷, 16,5 kpc, coupé à 207 kpc ; disque 5,6 × 10¹⁰, 5,3 kpc ; bulbe 3,1 × 10¹⁰ | Tamm et al. 2012 ; Courteau et al. 2011 ; Blaña Díaz et al. 2018 | fidèle ; hauteurs supposées (dit) |
| Triangle | NFW 5,08 × 10⁶, 16,7 kpc ; étoiles 4,8 × 10⁹ | Corbelli et al. 2014 | fidèle |
| Grand Nuage | Hernquist réglé pour 1,38 × 10¹¹ après coupure | Erkal et al. 2019 ; van der Marel & Kallivayalil 2014 | fidèle |

Remarques de fond :

- Le halo de McMillan donne, à 2,2 longueurs de disque (5,5 kpc), v_DM ≈ 134 km/s sur ~225 : le disque fournit
  ~80 % de la vitesse. C'est un disque presque maximal ; d'après Debattista & Sellwood 2000, un tel modèle *peut*
  garder une barre rapide. La lenteur ne vient donc pas d'abord du profil de masse. [Supposition, calcul ici]
- Masse de la Voie lactée : les courbes de rotation Gaia DR3 qui déclinent donnent bien moins (Ou et al. 2024,
  MNRAS 528, 693 : M200 = 6,9 × 10¹¹ en gNFW, 1,8 × 10¹¹ en Einasto, les auteurs signalant la tension avec les
  autres traceurs). [Certain : préprint relu aujourd'hui] Le modèle du film (1,34 × 10¹²) est dans le haut de la
  fourchette actuelle ; la date de fusion en dépend.
- Andromède à 1,07 × 10¹² est dans le bas de la fourchette ; des estimations par les mouvements propres des
  satellites donnent 2,5–3 × 10¹² (Patel & Mandel 2023, ApJ 948, 104). [À vérifier : cité de mémoire]

### 6.3 Chauffage numérique : contre Ludlow et al.

Source relue aujourd'hui : Ludlow, Fall, Schaye & Obreschkow 2021, MNRAS 508, 5114 (arXiv:2105.03561,
doi:10.1093/mnras/stab2770). [Certain]

- Le chauffage dépend de la **masse de la particule de matière noire**, de la densité et de la dispersion locales
  du halo ; il est « largement insensible » à la masse des particules d'étoiles. Loi :
  σ_i²(t) = σ_DM² [1 − exp(−(t + t0)/t_vir)], t_vir ∝ σ_DM³ / (G² ρ_DM m_DM) : linéaire en m_DM au début.
- Pour un halo de ~10¹² M☉ sur 10 Ga : Δσ_z ≲ 0,03 V200 (≈ 5 km/s) demande m_DM ≲ 5,2 × 10⁴ M☉ ; Δσ_z ≲ 0,1 V200
  (≈ 16 km/s) demande m_DM ≲ 5,9 × 10⁵ M☉. Moins de ~10⁶ particules dans le halo : chauffage ≥ 0,1 V200 en un temps
  de Hubble.
- Ludlow et al. 2019 (MNRAS 488, L123) : l'équipartition entre particules d'étoiles et de matière noire de masses
  inégales gonfle les galaxies ; remède : masses égales ou voisines. [Probable, non relu aujourd'hui]

Application au film [Supposition, calcul ici] :

| | m_DM | Verdict Ludlow 2021 |
|---|---|---|
| Voie lactée, 3,5 M de particules | 5,6 × 10⁵ | à la limite « 0,1 V200 » : Δ(σ_z²) ≈ 25 (km/s)² par Ga |
| Voie lactée, essai à 10,85 M | 1,3 × 10⁵ | ≈ 6 (km/s)² par Ga |
| il faudrait, pour 5 km/s en 10 Ga | 5 × 10⁴ | ~27 M de particules de halo |

- Vieilles étoiles (σ_z ≈ 25 km/s) : +128 (km/s)² en 5 Ga ⇒ σ_z 25 → 27,4 km/s, hauteur +20 %. Petit devant le
  doublement mesuré (0,55 → 1,24 kpc). **Cohérent avec l'essai n° 4 de `deuxieme-film.md`** : le grain du halo
  n'est pas la cause principale.
- Étoiles jeunes (σ_z ≈ 5–7 km/s, soit 25–50 (km/s)²) : +75 (km/s)² en 3 Ga triple σ_z². Le grain du halo suffit à
  faire passer leur épaisseur de 0,10 à ~0,25 kpc en 3 Ga, sur les 0,64 mesurés. **Pour les jeunes, le chauffage
  numérique n'est pas négligeable.**
- Triangle et Grand Nuage : 7 × 10⁵ particules de halo chacun, sous le seuil de 10⁶ ; rapport de masses 21–22.
  Leurs disques chauffent numériquement, relativement à leur V200 plus petite.
- Le commentaire `modeles_v2.py:149-151` (« rapport à garder sous 10 ») retient le mauvais critère.

## 7. Les écarts connus, expliqués par le code

### 7.1 La barre tourne à ~20 km/s/kpc au lieu de 39

**a) D'abord vérifier la mesure.** [Certain pour l'arithmétique]
`stabilite_tir.py:135` relève tous les 50 Ma par défaut ; `bulletin.py:64-66` déroule 2 × l'angle de l'anneau 2–4 kpc
et prend la **valeur absolue** de la pente. L'angle d'un motif à deux bras est défini modulo 180° : il faut moins de
90° entre deux relevés. À 50 Ma, la limite est 30,7 km/s/kpc ; une barre à Ω vraie au-dessus se lit 61,4 − Ω :

| Ω vraie | lue à 50 Ma |
|---|---|
| 39 | 22,4 |
| 44 | 17,4 |
| 33,4 | 28,0 |

La fourchette « 17 à 28 » de `deuxieme-film.md` est exactement l'image de 33–44. L'en-tête de `stabilite_tir.py`
(l. 19) connaît le piège et demande `--releve-ma=10`. Je ne peux pas savoir quel relevé a servi. Contre-indice : une
barre à 39 km/s/kpc a sa corotation à 6 kpc et ne peut pas s'étendre jusqu'à 8 kpc, or la force à 4–8 kpc monte à
0,61 ; une barre à 20 km/s/kpc a sa corotation à 11,5 kpc, ce qui colle avec « elle occupe presque tout le disque ».
La barre est donc probablement vraiment lente, au moins en fin de film ; mais la valeur initiale mérite une relecture
sur les images à 10 Ma (limite 154 km/s/kpc). [À vérifier]

**b) La cible elle-même a bougé.** Mesures récentes relues aujourd'hui [Certain] :

| Mesure | Ω_barre (km/s/kpc) | Source |
|---|---|---|
| Portail et al. 2017 (valeur du dépôt) | 39,0 ± 3,5 | MNRAS 465, 1621 |
| Clarke & Gerhard 2022 | 33,29 ± 1,81 ; corotation 6,5–7,5 kpc | MNRAS 512, 2171 [Probable pour la revue], arXiv:2107.10875 |
| Zhang, Belokurov, Evans et al. 2024 | 34,1 ± 2,4 ; longueur dynamique ≈ 4,0 kpc ; angle ≈ 25° | arXiv:2406.06678 |
| Chiba, Friske & Schönrich 2021 | la barre **ralentit** : −4,5 ± 1,4 km/s/kpc par Ga | MNRAS 500, 4710 [Probable pour la revue], arXiv:1912.04304 |

La vraie barre ralentit donc aussi, mais lentement : ~−13 % par Ga. Le film perd ~50 % dès le départ.

**c) Hypothèses du code qui freinent la barre.**

| Hypothèse du code | Effet physique | Référence |
|---|---|---|
| Halo vivant **sans rotation** (`modeles_v2.py:155`) | frottement dynamique maximal : le halo absorbe le moment cinétique de la barre aux résonances ; la barre ralentit et s'allonge | Debattista & Sellwood 2000, ApJ 543, 704 (doi:10.1086/317148) [Certain, résumé relu] ; Athanassoula 2003, MNRAS 341, 1179 [Probable] |
| idem | avec un halo qui tourne dans le sens du disque, la croissance de la barre est étouffée au-delà de λ ≈ 0,03 et le freinage s'affaiblit jusqu'à cesser | Long, Shlosman & Heller 2014, ApJ 783, L18 [Certain, résumé relu] ; Collier, Shlosman & Heller 2018, MNRAS 476, 1331 [Probable] |
| **Pas de gaz dissipatif** dans `rencontre.py` ni dans le mûrissement du film 2 | le gaz cède du moment cinétique à la barre (couple positif) ; les résonances restent dans des zones du halo déjà vidées, le couple du halo s'effondre (−58 → −7,8 en unités de l'article). Sans gaz : −43 % de vitesse entre 1 et 5 Ga, R = R_CR/R_barre de 1,6 à 1,9. Avec ~5 % de gaz : vitesse stable | Beane et al. 2023, ApJ 953, 173 [Certain pour le contenu, arXiv:2209.03364 relu ; Probable pour la revue] |
| Barre née d'un centre à Q ≈ 0,9 (`--froid=0.9`), sans bulbe sphérique (`voie_lactee_barre`) | instabilité violente : barre forte (0,34–0,44) dès le départ ; une barre forte échange plus et flambe plus | Athanassoula 2003 [Probable] |
| Barre guide imposée puis retirée (`stabilite_tir.py --guide`) | la vitesse imposée n'est pas un équilibre : une fois le guide retiré, la barre prend la vitesse « naturelle » du modèle (c'est ce que dit `deuxieme-film.md`) | [Supposition] |
| « Gaz » = 1,22 × 10¹⁰ M☉ d'étoiles froides sans collision | masse de disque en plus qui participe à la barre au lieu de la contrarier | [Supposition] |
| Mûrissement 3 Ga + passé 1 Ga avant « aujourd'hui » | la barre a déjà 4 Ga de freinage quand le film commence | [Certain pour les durées, `deuxieme-film.md`] |

Le modèle de référence de Beane et al. est instructif pour la résolution : 25 M de particules de halo de
3,75 × 10⁴ M☉, baryons à 7,5 × 10³ M☉, adoucissement 20 pc ; barre formée sans gaz pendant 1,5 Ga, puis gaz ajouté
avec un trou central de 4 kpc. [Certain, relu]

**d) `--halo-tourne` existe mais est fragile** (`stabilite_tir.py:113-131`). Retourner v_φ garde l'équilibre
seulement dans un potentiel axisymétrique : appliqué à une galaxie déjà barrée (mûrie), ce n'en est plus un. Il faut
l'appliquer au tirage AGAMA, **avant** la naissance de la barre. La mesure de λ (Bullock) est correcte. Cible :
λ ≈ 0,035 (Bullock et al. 2001, ApJ 555, 240 [Probable]). Debattista & Sellwood 2000 préviennent que la rotation
nécessaire pour supprimer seule le freinage est « irréaliste » : la rotation du halo est un levier partiel, le gaz
est l'autre.

### 7.2 La barre grossit sans arrêt (0,25 → 0,61 entre 4 et 8 kpc en 5 Ga)

Même mécanisme : en perdant du moment cinétique vers le halo, la barre ralentit, sa corotation recule
(R_CR = v_c/Ω : 6 kpc à 39, 11,5 kpc à 20), et elle peut capturer des orbites de plus en plus loin. C'est la
croissance séculaire des calculs sans collision (Athanassoula 2003 ; Martinez-Valpuesta, Shlosman & Heller 2006,
ApJ 637, 214 [Probable]). Rien, dans le code, ne s'y oppose : pas de gaz, pas de halo en rotation, pas de masse
centrale concentrée (bulbe retiré dans la variante barre, pas de trou noir, pas de disque nucléaire) qui limiterait
la barre par une résonance interne.

### 7.3 Le disque s'épaissit trop (0,55 → 1,24 kpc en 5 Ga)

| Cause | Preuve | Part estimée |
|---|---|---|
| Flambage de la barre (instabilité verticale) puis épaississement séculaire d'une barre qui couvre tout le disque | film 1 sans barre : 0,21 → 0,28 kpc ; film 2 avec barre : 0,55 → 1,24 (`deuxieme-film.md`, écart 3) ; Raha et al. 1991, Nature 352, 411 [Probable] | dominante [Certain d'après les deux films] |
| Disque de départ déjà à 0,55 kpc (flambage pendant les 3 Ga de mûrissement) | écart 5 | point de départ |
| Grain du halo | § 6.3 | ~20 % pour les vieilles ; important pour les jeunes |
| Passages des Nuages (inclinaison de 14° en 5 Ga) | les deux films | faible sur l'épaisseur mesurée dans le plan propre |
| Aucune population froide renouvelée | pas de gaz, pas de naissances dans le film | les « jeunes » sont des traceurs sans masse dans un potentiel sans dissipation : rien ne les ramène au plan |
| Pas de temps au cœur | § 2.3 | faible, centre seulement [Supposition] |

Dans la vraie Voie lactée, le flambage a bien eu lieu (bulbe en boîte et cacahuète), mais limité à ~2 kpc ; le disque
externe reste mince parce que la barre est courte et rapide, et parce que le gaz refait sans cesse une couche mince.
Les trois écarts ont donc une racine commune : **barre trop forte, trop longue, trop lente, sans gaz**.

## 8. Lecture du film côté appli

| Constat | Où | Effet |
|---|---|---|
| Une image tous les 10 Ma, positions seules ; Catmull-Rom sur 4 images, vitesse = pente de la courbe | `film_v2.h:97-101`, `film_etoiles.h:88-100` | période orbitale 10 Ma à 0,2 kpc, 17 Ma à 0,5 kpc : sous deux images par tour en deçà de ~0,6 kpc. Les orbites du centre sont **repliées** : mouvement et vitesses faux à l'écran pour le bulbe interne [Supposition, calcul ici] |
| float16 relatif au centre de la galaxie d'origine | `rencontre.py:556` | 4 pc à 8 kpc, ~30–60 pc à 100 kpc, ~0,5 kpc pour une étoile arrachée à 700 kpc : visible seulement sur les débris lointains |
| Centre par sphère qui rétrécit, recalculé à chaque image | `rencontre.py:138-152` | son bruit (quelques pc) se reporte sur toutes les étoiles ; négligeable |
| `energie` du journal lue par l'appli (`ecartEnergie`) | `film_v2.h:75` | bon : l'écran peut dire la tenue de l'énergie |

Remède : écrire aussi les vitesses (float16) et interpoler en Hermite, comme c'est déjà fait pour les centres
(`film_v2.h:78-86`) ; ou cadence de 2,5 Ma pour les étoiles à moins de 2 kpc.

## 9. Bogues probables

| # | Fichier:ligne | Défaut | Gravité |
|---|---|---|---|
| B1 | `bulletin.py:64-66`, `stabilite_tir.py:135` | vitesse de barre repliée si relevé ≥ 40 Ma ; `abs()` masque le signe. Correction : refuser le calcul si le saut médian de 2θ dépasse π/2, relever tous les 10 Ma, ou mesurer Ω par la méthode de Tremaine-Weinberg sur un seul instantané (positions + vitesses) | forte si c'est la source du « 20 » |
| B2 | `rencontre.py:119-126` | gaz et naissances absents du calcul du film | forte (réalisme) |
| B3 | `modeles_v2.py:202-205` (sorte 3) | gaz tiré avec 31 km/s d'agitation | forte dès que le gaz est allumé |
| B4 | `gaz_galaxie.py:62` | nombre de Courant non imposé | forte avec gaz |
| B5 | `stabilite_tir.py:151` | viscosité sur v_{n+½} au lieu de la vitesse prédite | moyenne |
| B6 | `stabilite_tir.py:163-164` | bilan d'énergie sans sens avec gaz isotherme ; ajouter l'énergie dissipée cumulée (Σ m dudt dt) au bilan | moyenne (contrôle) |
| B7 | `stabilite_tir.py:147-156` | pas d'énergie noire | faible (physique), règle de Marc |
| B8 | `stabilite_tir.py:40`, `rencontre.py:354, 383` | sorte 5 oubliée dans les relevés et parmi les porteuses des jeunes | moyenne |
| B9 | `gravite_gpu.py:138`, `gaz_gpu.py:102, 144` | dépassement de pile silencieux | faible (ne devrait pas arriver), mais indétectable |
| B10 | `gaz_gpu.py:20-21` | commentaire faux d'un facteur 1 000 sur la simple précision | faible |
| B11 | `rencontre.py:519` | traceurs de 1 M☉ qui gravitent | faible |
| B12 | `rencontre.py:38` contre `film_v2.py:24` | deux valeurs de l'unité de temps (0,9778 et 0,977792) | faible |
| B13 | `stabilite_tir.py:113-131` | `--halo-tourne` appliqué après la barre n'est pas un équilibre | moyenne (essais faussés) |
| B14 | `gravite_gpu.py:195-199` | « millions de kpc » : à expliquer | à vérifier |
| B15 | `rencontre.py` (journal) | quantité de mouvement et moment cinétique non journalisés | faible (contrôle manquant) |

## 10. Améliorations classées (impact sur le réalisme, effort)

| Rang | Amélioration | Où | Impact | Effort |
|---|---|---|---|---|
| 1 | Relire la vitesse de barre sur les images à 10 Ma ; corriger B1 | `bulletin.py`, `stabilite_tir.py` | fort (décide de tout le reste) | une heure, sans GPU |
| 2 | Brancher le gaz dans le film : un objet `Gaz` par galaxie dans `Calcul.forces`, naissances après le second coup, état du gaz dans `reprise.npz` | `rencontre.py:119-136, 175-177, 222` | fort : bras refaits, disque jeune mince, barre non freinée | 2–3 jours |
| 3 | Gaz de départ à l'équilibre : orbites circulaires avec correction de pression v_φ² = v_c² + c_s² dlnρ/dlnR, épaisseur hydrostatique, trou central de McMillan | `modeles_v2.py` | fort | 1 jour |
| 4 | Pas de temps du gaz : sous-pas quand dt v_sig/h > 0,3, ou pas individuels par blocs de puissances de 2 pour tout le calcul (règle aussi le cœur, § 2.3) | `gaz_galaxie.py`, `rencontre.py:132` | fort | 2–4 jours |
| 5 | Rétroaction et phases : au minimum une équation d'état effective au-dessus du seuil (Springel & Hernquist 2003, MNRAS 339, 289) ; mieux, chauffage stochastique par supernovas (Dalla Vecchia & Schaye 2012, MNRAS 426, 140) et refroidissement tabulé ; retour de masse des étoiles vers le gaz, masse conservée [références Probable] | `gaz_galaxie.py` | fort : sans elle, grumeaux et épuisement du gaz | 1–2 semaines ; à signaler comme modèle |
| 6 | Barre : la laisser naître dans un disque avec gaz et halo en rotation (λ ≈ 0,035 posé au tirage), bulbe et disque nucléaire gardés ; viser 34–39 km/s/kpc et 4–5 kpc à t = 0 ; abandonner `--froid=0.9` + guide si la barre naît seule | `modeles_v2.py`, `stabilite_tir.py` | fort | essais d'une heure de carte chacun |
| 7 | Résolution du halo : m_DM ≤ 5 × 10⁴ M☉ pour la Voie lactée et Andromède (~25 M de particules de halo chacune), ≥ 2 M pour Triangle et Grand Nuage | `modeles_v2.py:32, 152` | moyen pour les vieilles étoiles, fort pour les jeunes | temps de carte seulement (×5 à ×6) |
| 8 | Film : écrire les vitesses et interpoler en Hermite | `rencontre.py:550-561`, `film_v2.h`, `film_etoiles.h` | moyen (centre des galaxies) | 1 jour, film ×2 en taille |
| 9 | Énergie noire dans `stabilite_tir.py` ; journal de la quantité de mouvement et du moment cinétique dans `rencontre.py` | — | faible physiquement, règle et contrôle | une heure |
| 10 | Halo contracté par les baryons, légèrement aplati ; gaz chaud du halo ; trou noir central ; naine du Sagittaire en particules | `modeles_v2.py`, `rencontre.py` | moyen | variable |
| 11 | Arbre à forces symétriques (double parcours ou méthode de Dehnen) pour conserver la quantité de mouvement | `gravite_gpu.py` | faible | élevé |
| 12 | Masses : faire du film un membre d'un ensemble (masse de la Voie lactée 0,7–1,5 × 10¹², d'Andromède 0,8–3 × 10¹²) plutôt qu'un scénario unique | `univers.json`, ensembles déjà présents dans `resultats/` | moyen (date et existence de la fusion) | temps de carte |

## Écarts avec l'appli, classés par impact sur le réalisme

**Fort**
1. Le film n'a ni gaz, ni naissance d'étoiles, ni dissipation (`rencontre.py:119-126`) : bras non refaits, disque
   jeune qui s'épaissit, barre freinée.
2. Barre : lente, longue et croissante, par construction (halo sans rotation, pas de gaz, centre à Q ≈ 0,9 sans
   bulbe). Mesure à relire d'abord (repliement à 50 Ma).
3. Disque : 0,55 kpc au départ et 1,24 kpc à +5 Ga, pour ~0,3 mesuré ; cause : la barre.
4. Le gaz, tel qu'écrit, n'est pas prêt pour le film : départ à Mach 3, Courant non tenu, pas de rétroaction,
   épuisement en 4–5 Ga.

**Moyen**
5. Grain du halo à la limite de Ludlow et al. 2021 : chauffe les étoiles jeunes ; Triangle et Grand Nuage
   sous-résolus.
6. Orbites du centre repliées à la lecture (10 Ma par image, sans vitesses).
7. Pas de temps deux fois trop long sous 0,2 kpc.
8. Halos sphériques, non contractés, sans rotation ; pas de gaz chaud, de trou noir, de Sagittaire.
9. Forme du gaz de la Voie lactée (pas de trou central) ; hauteurs d'Andromède et du Triangle supposées.
10. Un seul scénario de masses, dans le haut de la fourchette pour la Voie lactée et le bas pour Andromède.

**Faible**
11. Énergie noire absente du mûrissement des galaxies seules ; w = −1 figé (dit à l'écran).
12. Quantité de mouvement et moment cinétique non suivis ; traceurs de 1 M☉ ; deux constantes d'unité de temps ;
    rotation d'un bloc de la Voie lactée à t = 0 sans les Nuages.

## Sources relues en ligne aujourd'hui

- Ludlow, Fall, Schaye & Obreschkow 2021 : https://arxiv.org/abs/2105.03561 (doi:10.1093/mnras/stab2770)
- Beane et al. 2023 : https://arxiv.org/abs/2209.03364
- Chiba, Friske & Schönrich : https://arxiv.org/abs/1912.04304
- Clarke & Gerhard : https://arxiv.org/abs/2107.10875
- Zhang, Belokurov, Evans, Kane & Sanders 2024 : https://arxiv.org/abs/2406.06678
- Long, Shlosman & Heller 2014 : https://arxiv.org/abs/1402.1491 (doi:10.1088/2041-8205/783/1/L18)
- Debattista & Sellwood 2000 : https://arxiv.org/abs/astro-ph/0006275 (doi:10.1086/317148)
- Ou, Eilers, Necib & Frebel 2024 : https://arxiv.org/abs/2303.12838

Non relues aujourd'hui (citées de mémoire, [Probable] ou [À vérifier] dans le texte) : Ludlow et al. 2019,
Wilkinson et al. 2023, Athanassoula 2003, Martinez-Valpuesta et al. 2006, Collier et al. 2018, Raha et al. 1991,
Power et al. 2003, Springel & Hernquist 2002 et 2003, Dalla Vecchia & Schaye 2012, Bullock et al. 2001,
Patel & Mandel 2023, Bate & Burkert 1997, résultats DESI DR2. Chiba & Schönrich 2021 (structure en anneaux des
résonances), nommé dans la mission, n'a pas été relu : je m'appuie sur Chiba, Friske & Schönrich pour le
ralentissement.
