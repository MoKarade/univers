# Annexe 4 — Gaz, formation d'étoiles, rétroaction, poussière, rayonnement et lumière

Rapport de recherche (lecture seule du code, aucun calcul GPU lancé, aucun fichier du dépôt modifié). Date : 18/11/2026.

Labels : **[Certain]** = lu aujourd'hui dans la source ou dans le code ; **[Probable]** = publié, cité de mémoire avec une
source connue ; **[Supposition]** = mon raisonnement ou mon calcul ; **[À vérifier]** = non vérifié.

## Résumé

- **Le gaz du film est un bon premier étage, mais c'est un gaz à une seule phase.** `gaz_gpu.py` est une SPH classique
  correcte et contrôlée (gradient, tube à choc, Evrard). `gaz_galaxie.py` la fait tourner en **isotherme à 10 km/s**, avec
  un plancher de Jeans et une loi de Schmidt à 1 % par temps de chute libre. Il n'y a **ni refroidissement, ni chauffage, ni
  rétroaction, ni gaz chaud, ni métaux, ni retour de masse des étoiles, ni accrétion** (le fichier le dit lui-même,
  `gaz_galaxie.py:17`). [Certain]
- **Le manque le plus lourd est la rétroaction des supernovæ** : sans elle, tous les calculs publiés forment trop d'étoiles,
  trop vite, en grumeaux. C'est la première chose à ajouter, avant le refroidissement. [Probable]
- **À la résolution du film, le seuil de 0,1 atome/cm³ et le plancher de Jeans ne font presque rien** : à 10 km/s, la
  longueur de Jeans vaut 1,5 kpc à 1 atome/cm³ et 150 pc à 100 atomes/cm³, donc le plancher ne s'active qu'au-delà de
  ~100 atomes/cm³ ; et la longueur de lissage au seuil (160 à 320 pc selon le nombre de particules) dépasse l'épaisseur du
  disque de gaz (85 pc). [Supposition, calcul fait aujourd'hui]
- **Le gaz s'épuise** : 1,22 × 10¹⁰ M☉ à 1,65–2 M☉/an durent 6 à 7 Ga, alors que la vraie Voie lactée reçoit du gaz
  (accrétion de l'ordre de 1 M☉/an, plus ~40 % de la masse des étoiles rendue au gaz). Sur un film de 10 Ga, c'est un
  écart visible. [Probable pour les mesures, Supposition pour la conséquence]
- **La poussière de l'appli est mesurée près du Soleil (Edenhofer 2024, jusqu'à 1,25 kpc) et modélisée au-delà (Drimmel &
  Spergel 2001)** ; le choix est sain et signalé. Trois écarts : la **lueur diffuse est éteinte en gris** (pas de
  rougissement, `voie_lactee.frag:64`) alors que les étoiles du modèle rougissent (`gaia.vert:144`) ; la **diffusion**
  (environ 60 % de l'extinction visible) est absente ; la poussière **ne suit pas le gaz du film** (elle reste figée dans
  le repère d'aujourd'hui). [Certain pour le code]
- **Des cartes plus étendues existent** : extension d'Edenhofer à 2 kpc, DECaPS (plan sud jusqu'à ~10 kpc), Bayestar19
  (3/4 du ciel), Vergely/Lallement 2022 (3 kpc), et une carte du plan vu de face jusqu'à 7 kpc (Zhang, Chen et al.,
  prépublication de juillet 2026). [Certain pour l'existence, lu aujourd'hui]
- **Le lien gaz → poussière tient en une ligne** : A_V par parsec ≈ 1,65 × 10⁻³ × n_H × (Z/Z☉) (Bohlin et al. 1978). Il
  permettrait de tirer la poussière des galaxies du film directement de leur gaz, comme le font les faux relevés
  professionnels (Ananke). [Probable]
- **Aucun effet de vitesse finie de la lumière, d'aberration ni de décalage Doppler n'est dans le rendu** (recherche dans
  `natif/shaders` et `natif/src` : rien). Aux échelles du Groupe local c'est négligeable (M31 est vue telle qu'elle était
  il y a 2,5 Ma : 0,3 kpc de déplacement) ; pour un observateur rapide c'est un mode à part, à signaler comme tel.
  [Certain pour le code, Supposition pour l'importance]
- **Le ciel multi-longueurs d'onde est déjà riche** (408 MHz, 21 cm HI4PI, Planck 30–857 GHz, AKARI, WISE, 2MASS, Hα
  Finkbeiner, GALEX, ROSAT, eROSITA, INTEGRAL, Fermi). Il manque le **CO** (gaz moléculaire, Dame 2001 ou Planck) et une
  carte de rougissement intégrée (SFD/Planck). [Certain, `pipeline/natif/ciel_bandes.py:29-224`]

---

## 1. Hydrodynamique du milieu interstellaire

### 1.1 Équations

Équations d'Euler d'un gaz parfait auto-gravitant avec sources (forme utilisée par tous les codes) [Certain, manuel] :

- masse : ∂ρ/∂t + ∇·(ρ**v**) = −ρ̇★ + ρ̇_retour
- quantité de mouvement : ∂(ρ**v**)/∂t + ∇·(ρ**v**⊗**v** + P 𝟙) = −ρ∇Φ (+ force magnétique, pression des rayons cosmiques, pression de rayonnement)
- énergie : ∂E/∂t + ∇·[(E + P)**v**] = −ρ**v**·∇Φ + n_H Γ − n_H² Λ(T, Z) + injection des étoiles
- fermeture : P = (γ − 1) ρ u, γ = 5/3 ; T = (γ − 1) u μ m_p / k_B, μ ≈ 1,22 (neutre), 0,59 (ionisé)
- gravité : ∇²Φ = 4πG ρ_tot − Λc² (le terme d'énergie noire, déjà dans `energie_noire.py`)

Version à particules (SPH) codée dans `gaz_gpu.py:7-15` : densité par somme sur le noyau, force symétrisée
P_i/ρ_i² + P_j/ρ_j², viscosité artificielle de Monaghan (α = 1, β = 2) avec l'interrupteur de Balsara. Références :
Monaghan 1992 (ARA&A 30, 543), Springel 2005 (MNRAS 364, 1105, GADGET-2), Balsara 1995 (J. Comput. Phys. 121, 357).
[Certain pour le code ; Probable pour les références]

Ce que les codes professionnels ont ajouté depuis cette formulation « classique » [Probable] :

| Amélioration | Pourquoi | Référence |
|---|---|---|
| Termes « grad-h » (formulation entropie ou énergie conservée avec h variable) | conserve énergie ET entropie quand h varie | Springel & Hernquist 2002, MNRAS 333, 649 |
| SPH « pression-entropie » | supprime la tension de surface artificielle aux discontinuités de contact (mélange des phases) | Hopkins 2013, MNRAS 428, 2840 |
| Conduction artificielle | idem, pour les instabilités de Kelvin-Helmholtz | Price 2008, J. Comput. Phys. 227, 10040 |
| Viscosité à interrupteur temporel | moins de viscosité hors des chocs | Cullen & Dehnen 2010, MNRAS 408, 669 |
| Noyaux de Wendland, ~100–200 voisines | évite l'appariement des particules | Dehnen & Aly 2012, MNRAS 425, 1068 |
| Méthodes sans maillage MFM/MFV (GIZMO), maillage mobile (AREPO) | chocs et mélange plus nets | Hopkins 2015, MNRAS 450, 53 ; Springel 2010, MNRAS 401, 791 |
| Pas de temps individuels + limiteur | une explosion voisine ne doit pas « surprendre » une particule froide | Saitoh & Makino 2009, ApJ 697, L99 ; Durier & Dalla Vecchia 2012, MNRAS 419, 465 |

Ces raffinements comptent surtout **dès qu'il y a plusieurs phases** (gaz chaud contre gaz froid). En isotherme, la SPH
classique du film suffit. [Supposition]

### 1.2 Phases du milieu interstellaire

Valeurs de référence au voisinage du Soleil [Probable : Draine 2011, *Physics of the Interstellar and Intergalactic
Medium*, table 1.3 ; Ferrière 2001, Rev. Mod. Phys. 73, 1031 ; les fourchettes varient d'un auteur à l'autre] :

| Phase | T (K) | n_H (cm⁻³) | Part du volume | Remarque |
|---|---|---|---|---|
| Moléculaire (H₂) | 10–50 | 10² – 10⁶ | < 1 % | où naissent les étoiles ; hauteur ~45–75 pc |
| Atomique froid (CNM) | 50–100 | 20–50 | ~1 % | nuages et feuillets |
| Atomique tiède (WNM) | 5 000–8 000 | 0,2–0,6 | ~30–40 % | porte l'essentiel de la masse de HI |
| Ionisé tiède (WIM, couche de Reynolds) | ~8 000 | 0,1–0,5 (par paquets) | ~10–25 % | hauteur ~1 kpc ; ~10⁹ M☉ |
| Ionisé chaud (HIM, coronal) | 10⁵·⁵ – 10⁶ | ~0,004 | ~50 % (incertain) | bulles de supernovæ, se prolonge en couronne |
| Régions HII | ~10⁴ | 1 – 10⁴ | très faible | autour des étoiles O et B |

Équilibre de pression approché : pression thermique P/k ≈ 3 800 K cm⁻³ (Jenkins & Tripp 2011, ApJ 734, 65) [Probable] ;
pression totale au plan médian ≈ 2–3 × 10⁴ K cm⁻³, dont thermique, turbulente, magnétique et rayons cosmiques à parts
comparables (Boulares & Cox 1990, ApJ 365, 544) [Probable].

Modèles fondateurs : instabilité thermique à deux phases (Field 1965, ApJ 142, 531 ; Wolfire et al. 1995, ApJ 443, 152 ;
2003, ApJ 587, 278) ; trois phases réglées par les supernovæ (McKee & Ostriker 1977, ApJ 218, 148). [Probable]

**Ce que fait le film** : une seule phase, isotherme, c_s = 10 km/s, soit ~10⁴ K (`gaz_galaxie.py:29`). C'est la phase
tiède, celle qui porte la masse : choix défendable et signalé. Conséquence : pas de nuages froids (donc pas de vrai site
de naissance), pas de bulles chaudes, pas de fontaine. [Certain pour le code]

### 1.3 Refroidissement et chauffage

Fonction de refroidissement Λ(T, Z), en erg cm³ s⁻¹ (perte = n_H² Λ) [Probable pour les ordres de grandeur] :

| T | Λ (métallicité solaire) | Processus dominant |
|---|---|---|
| 10–10⁴ K | 10⁻²⁷ – 10⁻²⁵ | raies fines [C II] 158 µm, [O I] 63 µm, H₂, CO, poussière |
| ~1,5 × 10⁴ K | montée brutale vers 10⁻²² | Lyman α (H), puis He |
| ~10⁵ K | pic ~10⁻²¹ | raies de C, O, Ne ionisés |
| 10⁶ – 10⁷ K | ~2–5 × 10⁻²³ | raies du fer |
| > 10⁷·⁵ K | ∝ T¹ᐟ² | rayonnement de freinage |

Tables de référence :

| Table | Contenu | Usage | Référence |
|---|---|---|---|
| Sutherland & Dopita 1993 | équilibre collisionnel, 10⁴–10⁸·⁵ K, plusieurs métallicités | codes des années 1995–2010 | ApJS 88, 253 [Probable] |
| Wiersma, Schaye & Smith 2009 | 11 éléments un par un, avec photo-ionisation par le fond UV | OWLS, EAGLE | MNRAS 393, 99 [Probable] |
| Ploeckinger & Schaye 2020 | 10 K à 10⁹ K, auto-écrantage, champ de rayonnement interstellaire, rayons cosmiques, poussière, H₂ | COLIBRE | MNRAS 497, 4857 [Probable] |
| Grackle | bibliothèque libre (chimie hors équilibre H, He, H₂ + tables de métaux) | AGORA, Enzo, GIZMO, SWIFT | Smith et al. 2017, MNRAS 466, 2217 [Probable] |

Chauffage : effet photo-électrique sur la poussière, Γ_pe ≈ 1,3 × 10⁻²⁴ ε G₀ erg s⁻¹ par atome H, ε ≈ 0,05 (Bakes &
Tielens 1994, ApJ 427, 822 ; Wolfire et al. 2003) ; fond UV extragalactique (Haardt & Madau 2012, ApJ 746, 125 ;
Faucher-Giguère 2020, MNRAS 493, 1614) ; rayons cosmiques (taux d'ionisation ζ ~ 10⁻¹⁶ s⁻¹) ; photo-ionisation par les
étoiles O/B. [Probable]

**Recette minimale utilisable telle quelle sur GPU** : la loi analytique de Koyama & Inutsuka 2002 (ApJ 564, L97), très
employée pour le milieu à deux phases : Γ = 2 × 10⁻²⁶ erg s⁻¹ ; Λ/Γ = 10⁷ exp[−118 400/(T + 1 000)] + 1,4 × 10⁻² √T
exp(−92/T) cm³. Deux lignes de code, donne les phases froide et tiède. [Probable ; coefficients à relire dans l'article
avant de coder — la version corrigée est dans Vázquez-Semadeni et al. 2007, ApJ 657, 870] [À vérifier]

Temps de refroidissement : t_refr = (3/2) n k_B T / (n_H² Λ). À n_H = 1 cm⁻³ et 10⁶ K : ~1 Ma ; à 10⁵ K : ~10⁴ ans. C'est
plus court que le pas du film (0,25 Ma, `stabilite_tir.py:107`) : il faut une intégration implicite ou sous-cyclée de
l'énergie, pas un pas explicite. [Supposition, calcul d'ordre de grandeur]

**Ce que fait le film** : rien de tout cela ; « on suppose qu'ils s'équilibrent à cette température »
(`gaz_galaxie.py:8-9`). L'énergie dissipée dans les chocs disparaît (isotherme) ; le relevé d'énergie de
`stabilite_tir.py:159` ne compte que cinétique + potentielle, donc **l'écart d'énergie affiché ne peut plus servir de
contrôle de justesse dès que `--gaz=1`** (une dérive est attendue et physique). [Certain pour le code, Supposition pour la
remarque]

### 1.4 Champ magnétique et rayons cosmiques (ordres de grandeur)

Densités d'énergie locales [Probable : Draine 2011, table 1.5 ; Beck 2015, A&A Rev. 24, 4 ; Cummings et al. 2016,
ApJ 831, 18 pour Voyager 1] :

| Réservoir | Densité d'énergie (eV/cm³) |
|---|---|
| Thermique (P/k = 3 800 K cm⁻³) | ~0,5 |
| Turbulence (σ ≈ 7–10 km/s) | ~0,2–1 |
| Champ magnétique (B_tot ≈ 6 µG au Soleil ; composante ordonnée 2–3 µG) | ~0,9 |
| Rayons cosmiques | ~0,8–1 |
| Lumière des étoiles | ~0,5 |
| Fond diffus cosmologique | 0,26 |

Tout est du même ordre : champ magnétique et rayons cosmiques **ne sont pas négligeables pour la structure verticale du
gaz et pour les vents** (les rayons cosmiques poussent des vents plus froids et plus chargés : Hopkins et al. 2020,
MNRAS 492, 3465 ; Ruszkowski & Pfrommer 2023, A&A Rev. 31, 4) [Probable]. Mais leur effet sur la **forme d'ensemble** d'un
disque et sur son taux de naissance d'étoiles reste de second ordre devant la rétroaction des supernovæ [Probable].
Recommandation : ne pas les calculer ; les **dire absents** ; tenir compte de leur pression en relevant le plancher de
pression effectif si besoin (modèle). [Supposition]

### 1.5 Masse et distribution du gaz de la Voie lactée

| Grandeur | Valeur | Source | Statut |
|---|---|---|---|
| Masse de HI | 7,7 × 10⁹ M☉ (rapportée à R₀ récent) ; fourchette publiée 3,3 à 8 × 10⁹ ; moyenne de quatre estimations 5,55 ± 1,74 × 10⁹ | Kalberla & Kerp 2009 (ARA&A 47, 27), repris par Licquia, Newman & Bershady 2016 (arXiv:1610.05769) | [Certain, lu aujourd'hui dans arXiv:1610.05769] |
| Masse de H₂ | 1,0 ± 0,3 × 10⁹ M☉ | Heyer & Dame 2015 (ARA&A 53, 583) | [Probable] |
| Gaz total (atomique + moléculaire, hélium et métaux compris) | 1,18 × 10¹⁰ M☉ | McGaugh 2016 (ApJ 816, 42), cité dans arXiv:1610.05769 | [Certain, lu aujourd'hui] |
| Modèle de McMillan 2017 | HI 1,1 × 10¹⁰ (trou 4 kpc, longueur 7 kpc, hauteur 85 pc) ; H₂ 1,2 × 10⁹ (trou 12 kpc, longueur 1,5 kpc, hauteur 45 pc) | MNRAS 465, 76, table 3 | [Certain, `docs/parametres-galaxies.md:28-29`] |
| Gaz ionisé tiède | ~10⁹ M☉ (disque) ; ~10⁸ M☉ à l'interface disque-halo | Draine 2011 ; Richter 2017 (arXiv:1612.00449) | [Probable] / [Certain pour 10⁸] |
| Densité de surface de gaz au Soleil | ~10–13 M☉/pc² (hélium compris) | McKee, Parravano & Hollenbach 2015, ApJ 814, 13 | [Probable] |
| Anneau moléculaire | pic de H₂ vers 4–6 kpc ; zone moléculaire centrale (CMZ) : ~3–5 × 10⁷ M☉ dans 200 pc | Heyer & Dame 2015 | [Probable] |
| Gauchissement et évasement de HI | hauteur ~150 pc au Soleil, > 1 kpc à 25 kpc ; gauchissement dès ~12 kpc | Kalberla & Kerp 2009 ; Levine, Blitz & Heiles 2006, ApJ 643, 881 | [Probable] |
| Relevés | HI4PI (résolution 16,2′, tout le ciel, 21 cm) ; CO : Dame, Hartmann & Thaddeus 2001 (115 GHz, 1/8°) | A&A 594, A116 (2016) ; ApJ 547, 792 | [Probable] |

Le chiffre de la mission (« HI ~8 × 10⁹, H₂ ~1 × 10⁹ ») est donc bon ; les 1,1 × 10¹⁰ de McMillan sont très probablement
ces mêmes 8 × 10⁹ multipliés par ~1,36 pour l'hélium [Supposition].

**Ce que fait le film** : `modeles_v2.py:43` met **1,22 × 10¹⁰ M☉ dans un seul disque exponentiel de longueur 7 kpc et de
hauteur 85 pc, sans trou central et sans composante moléculaire séparée**. [Certain] Écarts :

1. masse totale : conforme (1,18–1,22 × 10¹⁰) ;
2. forme : le trou central de 4 kpc du HI et l'anneau moléculaire (longueur 1,5 kpc, trou « 12 kpc » dans la formule de
   McMillan) sont perdus ; le gaz du film est trop abondant au centre côté atomique et **trop peu concentré vers 4–6 kpc**
   où naît l'essentiel des étoiles (voir § 2.1 : 84 % de la naissance d'étoiles est à l'intérieur du cercle solaire) ;
3. vitesses de départ : le gaz est tiré de la même fonction de distribution que des étoiles froides (`q_min=1.5`), donc
   avec une agitation de plusieurs km/s à dizaines de km/s que le gaz réel n'a pas (σ_HI ≈ 7–10 km/s) ; les chocs la
   dissipent dans les premières dizaines de Ma — prévoir un **transitoire de départ** (flambée artificielle) [Supposition].

### 1.6 Couronne chaude, fontaine, accrétion

| Grandeur | Valeur | Source | Statut |
|---|---|---|---|
| Couronne chaude : température | ~2 × 10⁶ K (kT ≈ 0,2 keV), plus une composante ~0,7 keV | Kaaret et al. 2020, Nat. Astron. 4, 1072 ; Ponti et al. 2023, A&A 674, A195 | [Probable] |
| Couronne : masse dans ~250 kpc | 3–6 × 10¹⁰ M☉ (forte incertitude : métallicité supposée ~0,3 Z☉) | Miller & Bregman 2015, ApJ 800, 14 ; Bregman et al. 2018, ApJ 862, 3 | [Probable] |
| Couronne : uniformité | température constante à 4 % près sur 2–20° ; ~12 % d'écart nord-sud | Zheng et al. 2024, A&A 689, A328 (eROSITA) | [Certain, résumé lu aujourd'hui] |
| Nuages à grande vitesse (HI) | 2,5 × 10⁸ M☉, dont Courant magellanique 1,6 × 10⁸ M☉ à 55 kpc ; ionisé/neutre ≈ 3 dans le Courant | Richter 2017 (arXiv:1612.00449) | [Certain, lu aujourd'hui] |
| HI total du halo (Nuages et Pont compris) | 1,3 × 10⁹ M☉ | idem | [Certain] |
| Accrétion actuelle | « quelques M☉/an » au total, assez pour entretenir la naissance d'étoiles ; ≥ 4 × 10⁹ M☉ accrétés en 8 Ga | idem | [Certain] |
| Accrétion par les nuages HI seuls | ~0,08 M☉/an | Putman, Peek & Joung 2012, ARA&A 50, 491 | [Probable] |
| Fontaine galactique | gaz soulevé par les supernovæ à ~1–2 kpc, retombe en ~50–100 Ma en entraînant du gaz de la couronne | Shapiro & Field 1976, ApJ 205, 762 ; Fraternali & Binney 2008, MNRAS 386, 935 | [Probable] |
| Bulles de Fermi / eROSITA | ±8–14 kpc au-dessus du centre ; énergie ~10⁵⁵–10⁵⁶ erg, âge de quelques Ma | Su et al. 2010, ApJ 724, 1044 ; Predehl et al. 2020, Nature 588, 227 | [Probable] |

**Ce que fait le film** : aucune couronne, aucune fontaine, aucune accrétion. La couronne (3–6 × 10¹⁰ M☉) pèse autant que
tout le disque d'étoiles ; elle est comptée (ou non) dans le halo — à vérifier avec le rapport sur les masses. Pour le
gaz, l'important est le **bilan** : voir § 2.5. [Certain pour le code]

---

## 2. Formation d'étoiles

### 2.1 Taux de la Voie lactée

| Valeur (M☉/an) | Méthode | Source | Statut |
|---|---|---|---|
| 1,65 ± 0,19 | combinaison bayésienne des mesures antérieures (loi de Kroupa) | Licquia & Newman 2015, ApJ 806, 96 | [Certain, repris dans arXiv:2501.14471] |
| 1,9 ± 0,4 | synthèse des méthodes | Chomiuk & Povich 2011, AJ 142, 197 | [Certain, idem] |
| 2,0 ± 0,7 (1,7 ± 0,6 pour les grumeaux à distance sûre) | grumeaux de Herschel Hi-GAL | Elia et al. 2022, ApJ 941, 162 (arXiv:2211.05573) | [Certain, lu aujourd'hui] |
| 1,65 ± 0,61 ; 1,42 (+0,63/−0,44) ; 1,47 | trois méthodes Hi-GAL révisées (rapport gaz/poussière variable, 70 µm) | Elia et al. 2025, arXiv:2501.14471 | [Certain, lu aujourd'hui] |

Répartition (Elia 2022) [Certain] : pic dans la zone moléculaire centrale, second pic vers R ≈ 5 kpc, puis décroissance
exponentielle (pente −0,28 ± 0,01 dex/kpc en log) ; **84 % à l'intérieur du cercle solaire**, 16 % dehors, ~1 % au-delà de
13,5 kpc. Pour R > 3 kpc, la densité de naissance suit une loi de puissance de la densité de gaz (type Kennicutt-Schmidt).

Le fichier de mesures du film porte bien 1,65 ± 0,19 avec la mention « l'incertitude réelle peut atteindre 50 % »
(`resultats/mesures_voie_lactee.json`) [Certain]. Recommandation : y ajouter la **répartition radiale** d'Elia 2022 comme
seconde cible (le total seul peut être bon pour de mauvaises raisons). [Supposition]

### 2.2 Loi de Kennicutt-Schmidt

| Loi | Formule | Source | Statut |
|---|---|---|---|
| Schmidt | ρ̇★ ∝ ρ_gaz^n, n ≈ 1–2 | Schmidt 1959, ApJ 129, 243 | [Probable] |
| Kennicutt-Schmidt (galaxies entières) | Σ_SFR = (2,5 ± 0,7) × 10⁻⁴ (Σ_gaz / 1 M☉ pc⁻²)^(1,4 ± 0,15) M☉ an⁻¹ kpc⁻² | Kennicutt 1998, ApJ 498, 541 | [Probable] |
| Révision | n = 1,41 ± 0,07 (spirales) | de los Reyes & Kennicutt 2019, ApJ 872, 16 | [Probable] |
| Résolue (< 1 kpc), gaz moléculaire | Σ_SFR = 10^(−2,1 ± 0,2) (Σ_H₂ / 10 M☉ pc⁻²)^(1,0 ± 0,2) : temps d'épuisement de H₂ ≈ 2 Ga, constant | Bigiel et al. 2008, AJ 136, 2846 ; Leroy et al. 2008, AJ 136, 2782 ; 2013, AJ 146, 19 (2,2 Ga) | [Probable] |
| Saturation du HI | Σ_HI plafonne vers 9–10 M☉/pc² ; au-dessus, le gaz est moléculaire | Bigiel et al. 2008 | [Probable] |
| Bords des disques | sous ~3–10 M☉/pc², l'efficacité s'effondre (seuil) | Kennicutt 1989, ApJ 344, 685 ; Schaye 2004, ApJ 609, 667 | [Probable] |
| Suivi sur 13 Ga dans les simulations récentes | la relation de KS émerge du modèle à gaz froid | COLIBRE, arXiv:2512.11309 | [À vérifier : titre vu, non lu] |

Avec un facteur 1,6 de moins pour passer de la loi de masses de Salpeter (Kennicutt 1998) à Kroupa/Chabrier. [Probable]

### 2.3 Efficacité par temps de chute libre

- Définition : ρ̇★ = ε_ff ρ / t_ff, t_ff = √(3π / 32Gρ). [Certain, c'est la formule de `gaz_galaxie.py:71`]
- ε_ff ≈ 0,01, presque indépendant de la densité de 10² à 10⁵ cm⁻³ : Krumholz & Tan 2007 (ApJ 654, 304) ; Krumholz, Dekel
  & McKee 2012 (ApJ 745, 69). [Probable]
- Mesures récentes à l'échelle des nuages dans les galaxies proches : ε_ff ≈ 0,7 % (Utomo et al. 2018, ApJ 861, L18) ;
  0,5 (+0,7/−0,3) % (Sun et al. 2023, ApJ 945, L19, PHANGS). Dispersion d'un facteur ~3. [Probable]
- Table de valeurs utiles (calcul d'aujourd'hui, X = 0,76) [Supposition, calcul] :

| n_H (cm⁻³) | t_ff (Ma) | λ_Jeans à 10 km/s (pc) | M_Jeans à 10 km/s (M☉) |
|---|---|---|---|
| 0,1 | 142 | 4 740 | 1,8 × 10⁸ |
| 1 | 45 | 1 500 | 5,7 × 10⁷ |
| 10 | 14 | 474 | 1,8 × 10⁷ |
| 100 | 4,5 | 150 | 5,7 × 10⁶ |

Formules : λ_J = c_s √(π / Gρ) ; M_J = (π/6) ρ λ_J³ ; critère de Truelove et al. 1997 (ApJ 489, L179) : résoudre λ_J par au
moins 4 éléments ; critère SPH de Bate & Burkert 1997 (MNRAS 288, 1060) : M_J > 2 N_voisines m_particule. Stabilité d'un
disque : Q = σ κ / (π G Σ) pour le gaz, σ_R κ / (3,36 G Σ) pour les étoiles (Toomre 1964, ApJ 139, 1217) ; à deux
composantes : Romeo & Wiegert 2011 (MNRAS 416, 1191). [Probable]

### 2.4 Critères de seuil des codes professionnels

| Code | Critère de naissance | Efficacité | Source |
|---|---|---|---|
| Springel & Hernquist 2003 (Illustris, TNG) | n_H > ~0,1–0,13 cm⁻³ (déduit du modèle à deux phases) ; équation d'état effective | temps caractéristique t★ ≈ 2,1–2,2 Ga au seuil, ∝ ρ⁻¹ᐟ² | MNRAS 339, 289 [Probable] |
| EAGLE | n_H★ = 0,1 cm⁻³ (Z/0,002)^(−0,64) (Schaye 2004), T près du plancher ; loi de pression : ṁ★ = m_g A (1 M☉ pc⁻²)^(−n) (γ f_g P / G)^((n−1)/2), A = 1,515 × 10⁻⁴ M☉ an⁻¹ kpc⁻², n = 1,4 | reproduit Kennicutt-Schmidt par construction | Schaye & Dalla Vecchia 2008, MNRAS 383, 1210 ; Schaye et al. 2015, MNRAS 446, 521 [Probable] |
| EAGLE : plancher de pression | P ∝ ρ^(4/3), normalisé à 8 000 K à n_H = 0,1 cm⁻³ | évite la fragmentation numérique | idem [Probable] |
| AGORA (disque isolé type Voie lactée) | n_H > 10 cm⁻³, ε = 1 % par temps de chute libre ; plancher de Jeans ; résolution 80 pc, particules de gaz de 8,6 × 10⁴ M☉ | comparaison de 9 codes | Kim et al. 2016, ApJ 833, 202 [Probable ; chiffres à relire] |
| FIRE-2 | n > 1 000 cm⁻³, gaz auto-gravitant (viriel), moléculaire (auto-écranté), instable de Jeans | 100 % par t_ff localement ; ~1 % émerge de la rétroaction | Hopkins et al. 2018, MNRAS 480, 800 [Probable] |
| SMUGGLE (AREPO) | n > 100 cm⁻³, gaz lié, part moléculaire | ε = 1 % | Marinacci et al. 2019, MNRAS 489, 4233 [Probable] |
| COLIBRE (2025) | critère d'instabilité gravitationnelle sur le gaz froid, gaz jusqu'à ~10 K, poussière et chimie couplées ; particules 10⁵–10⁷ M☉ | calibré sur fonction de masse et tailles | Chaikin et al. 2025, arXiv:2509.04067 ; Schaye et al. 2025 [Certain pour les résolutions et l'existence du gaz froid, lu aujourd'hui ; le reste À vérifier] |

**Ce que fait le film** (`gaz_galaxie.py`) [Certain] :

- seuil n_H > 0,1 cm⁻³ (ligne 31, « ordre de grandeur EAGLE ») ; ε = 0,01 (ligne 34) ; tirage au sort
  p = 1 − exp(−ε dt / t_ff) (ligne 72) : formule standard (Katz 1992, ApJ 391, 502 ; Springel & Hernquist 2003), correcte ;
- la particule de gaz devient entière une particule d'étoiles (sorte 5), sa date de naissance est gardée : la masse est
  conservée exactement (règle de Marc respectée) ;
- conversion d'unités : 1 M☉/pc³ = 40,46 protons/cm³, × 0,76 : exact à 0,1 % [Supposition, recalculé].

**Écarts** :

1. **Mélange de deux recettes.** Le seuil 0,1 cm⁻³ d'EAGLE va avec une **loi de pression** calée sur Kennicutt-Schmidt
   (ou, chez Springel-Hernquist, avec t★ = 2,1 Ga), **pas** avec ε_ff = 1 % sur la densité brute. Les deux ne sont pas
   équivalentes : à 0,1 cm⁻³, ε/t_ff donne un temps d'épuisement de 14 Ga ; à 1 cm⁻³, 4,5 Ga ; à 10 cm⁻³, 1,4 Ga. Le taux
   global dépend donc de la **distribution de densité que la résolution permet**, pas d'une loi observée. [Supposition]
2. **Résolution au seuil.** Pour ~3,5 M de particules dont 30 % hors halo (hypothèse tirée de `PART_HALO = 0.7`,
   `modeles_v2.py:32`), une particule de gaz pèse ~6 × 10⁴ M☉ et sa longueur de lissage vaut ~320 pc à 0,1 cm⁻³, 150 pc à
   1 cm⁻³, 70 pc à 10 cm⁻³ ; avec 10,85 M de particules : 220, 100 et 48 pc. **La longueur de lissage au seuil dépasse la
   hauteur du disque de gaz (85 pc)** : la densité volumique mesurée par la SPH est alors sous-estimée (lissée en
   hauteur), et le disque de gaz est gonflé par la pression à l'échelle h. [Supposition, calcul]
3. **Plancher de Jeans quasi inactif.** Il ne joue que si λ_J < 4 h ; à 10 km/s, λ_J = 150 pc à 100 cm⁻³, à comparer à
   4 h = 130 pc (3,5 M) : il ne s'allume qu'au-delà de ~100 cm⁻³. Ce n'est pas faux (le gaz à 10 km/s est déjà « chaud »
   pour ces échelles), mais il faut savoir que c'est **la pression isotherme, pas le plancher**, qui règle la
   fragmentation. Les grumeaux viendront de l'instabilité du disque (Q du gaz), pas de Jeans. [Supposition, calcul]
4. **Adoucissement gravitationnel fixe** (`eps` de `modeles_v2.py`) contre lissage hydrodynamique variable (H_MIN = 20 pc,
   `gaz_galaxie.py:35`). Les codes prennent ε_grav ≈ h pour le gaz (Bate & Burkert 1997) ; sinon, fragmentation
   artificielle (ε < h) ou étouffée (ε > h). À vérifier dans `modeles_v2.py`. [À vérifier]
5. **Pas de temps global** de 0,25 Ma : nombre de Courant dt × v_sig / h = 0,13 à 0,4 pour h = 20 pc et v_sig = 10–30 km/s
   — à la limite de 0,3 dite dans le code (ligne 52) ; le relevé `courant` le surveille, c'est bien. Avec de la
   rétroaction (gaz à 10⁷ K, c_s ≈ 500 km/s), ce pas serait 20 à 50 fois trop long : **pas de temps individuels
   obligatoires**. [Supposition, calcul]
6. **Étoiles nées à la vitesse du gaz, sans populations** : correct ; mais l'appli ne lit pas encore la date de naissance
   (aucune trace de `naissance` ni de la sorte 5 dans `natif/src/fusion_nuage.h` ni `natif/shaders/fusion_nuage.vert`)
   [Certain, recherche faite aujourd'hui]. La couleur et l'éclat par âge existent pourtant côté appli
   (`docs/vieillissement-lumiere.md`, régime `naissance_continue` « recommandé tant que le film n'a pas de gaz »). Le
   raccord est à faire : une étoile de sorte 5 doit briller bleu puis vieillir selon sa vraie date.

### 2.5 Bilan de gaz : le film s'épuise, la Galaxie non

- Temps d'épuisement : 1,22 × 10¹⁰ / (1,65 à 2,0) = 6 à 7,4 Ga. [Supposition, calcul]
- Retour de masse des étoiles : une population rend ~40 % de sa masse au gaz en 10 Ga pour la loi de Chabrier (~30 % pour
  Salpeter), dont la moitié dans le premier Ga (Leitner & Kravtsov 2011, ApJ 734, 48) [Probable]. Soit ~0,7 M☉/an rendus
  pour 1,65 formés, **plus** le retour des vieilles étoiles déjà là (~1 M☉/an pour 6 × 10¹⁰ M☉ : même article)
  [Probable].
- Accrétion : quelques M☉/an (§ 1.6).
- Dans le film : ni retour ni accrétion. Sur 3 Ga vers le passé et 7 Ga vers l'avenir, le gaz baisserait de façon
  monotone ; en partant d'aujourd'hui vers le passé, il faudrait au contraire **plus** de gaz à −3 Ga. [Supposition]

Recommandation (modèle, à signaler) : retour de masse par particule d'étoile selon son âge (table de Wiersma et al. 2009b,
MNRAS 399, 574, ou formule de Leitner & Kravtsov) — la masse totale est conservée, elle change de nature dans l'autre sens
— et, pour l'accrétion, soit une couronne chaude en particules de gaz (cohérente avec la conservation de la masse), soit
rien, en le disant. [Supposition]

---

## 3. Rétroaction

### 3.1 Bilan énergétique des étoiles

| Grandeur | Valeur | Source | Statut |
|---|---|---|---|
| Supernovæ à effondrement de cœur | ~1 pour 100 M☉ formées (Kroupa/Chabrier, 8–100 M☉) ; 10⁵¹ erg chacune ; entre 3 et 40 Ma après la naissance | Leitherer et al. 1999, ApJS 123, 3 (Starburst99) | [Probable] |
| Supernovæ Ia | ~1,3 × 10⁻³ par M☉ formée, délai ∝ t⁻¹ à partir de ~40 Ma | Maoz & Mannucci 2012, PASA 29, 447 ; Maoz & Graur 2017, ApJ 848, 25 | [Probable] |
| Taux dans la Voie lactée | 1,63 ± 0,46 par siècle | Rozwadowska, Vissani & Cappellaro 2021, New Astron. 83, 101498 | [Probable] |
| Vents d'étoiles massives | énergie comparable aux supernovæ sur les 3 premiers Ma (à métallicité solaire) | Starburst99 | [Probable] |
| Rayonnement | ~100 fois l'énergie des supernovæ, mais peu couplé ; quantité de mouvement L/c ; photo-ionisation à 10⁴ K | Murray, Quataert & Thompson 2010, ApJ 709, 191 | [Probable] |
| Quantité de mouvement finale d'un reste | p ≈ 3 × 10⁵ M☉ km/s × n^(−0,16) (presque indépendant du milieu) | Kim & Ostriker 2015, ApJ 802, 99 ; Martizzi et al. 2015, MNRAS 450, 504 | [Probable] |
| Rayon de refroidissement | ~23 pc × n^(−0,42) | Kim & Ostriker 2015 | [Probable] |

**Le problème de résolution** : à 10⁵ M☉ par particule, 10⁵¹ erg répartis sur ~60 voisines ne chauffent le gaz que de
quelques milliers de kelvins, et l'énergie est rayonnée aussitôt (« sur-refroidissement », Katz 1992). Le rayon de
refroidissement (23 pc) est très en dessous des 50–300 pc du film. Toutes les recettes ci-dessous sont des façons de
contourner cela. [Probable]

### 3.2 Recettes sous-maille professionnelles

| Modèle | Supernovæ / vents | Paramètres | Source | Statut |
|---|---|---|---|---|
| **Springel & Hernquist 2003** | équation d'état effective d'un milieu à deux phases (pas de gaz froid explicite) ; vents lancés à la main, découplés de l'hydrodynamique | charge en masse η = 2 ; v_vent = 484 km/s ; T_SN = 10⁸ K ; A₀ = 1 000 ; t★ = 2,1 Ga | MNRAS 339, 289 | [Probable] |
| **IllustrisTNG** | même équation d'état ; vents isotropes, vitesse liée à la dispersion de la matière noire locale, avec plancher ; 10 % en chaleur ; énergie dépendant de la métallicité | v_vent = max[7,4 σ_DM (H₀/H)^(1/3), 350 km/s] | Pillepich et al. 2018, MNRAS 473, 4077 | [Probable] |
| **EAGLE** | chauffage **thermique stochastique** : on chauffe peu de particules mais fort, pour que le refroidissement soit lent | ΔT = 10^7,5 K ; fraction d'énergie f_th de 0,3 à 3 selon densité et métallicité | Dalla Vecchia & Schaye 2012, MNRAS 426, 140 ; Schaye et al. 2015 ; Crain et al. 2015, MNRAS 450, 1937 | [Probable] |
| **FIRE-2 / FIRE-3** | supernovæ une à une : énergie si le rayon de refroidissement est résolu, sinon quantité de mouvement finale ; + vents stellaires, pression de rayonnement, photo-ionisation, chauffage photo-électrique ; refroidissement de 10 à 10¹⁰ K | particules de 7 070 M☉ (Latte) ; pas de paramètre de vent réglé | Hopkins et al. 2018, MNRAS 480, 800 ; 2023, MNRAS 519, 3154 | [Probable] |
| **SMUGGLE** | comme FIRE en esprit, sur AREPO, pour disques isolés | — | Marinacci et al. 2019 | [Probable] |
| **Rétroaction mécanique** | injection de quantité de mouvement p(n, Z) tabulée quand le reste n'est pas résolu | — | Kimm & Cen 2014, ApJ 788, 121 ; Hopkins et al. 2018b, MNRAS 477, 1578 | [Probable] |
| **Refroidissement retardé (« blastwave »)** | on coupe le refroidissement des voisines pendant ~quelques Ma | — | Stinson et al. 2006, MNRAS 373, 1074 | [Probable] |
| **COLIBRE** | thermique stochastique + cinétique ; gaz froid et poussière suivis ; ~200 simulations de calibrage | m7/m6/m5 = 10⁷/10⁶/10⁵ M☉ | Chaikin et al. 2025, arXiv:2509.04067 | [Certain pour ce qui est cité, lu aujourd'hui] |

**Choix recommandé pour le film** (≈ 10⁴–10⁵ M☉ par particule, gaz jusqu'ici isotherme), par ordre de simplicité
[Supposition] :

1. **Niveau « équation d'état »** (le plus proche de l'existant) : garder un gaz sans thermodynamique explicite, mais
   remplacer l'isotherme par l'équation d'état effective de Springel & Hernquist 2003 (ou le plancher P ∝ ρ^(4/3)
   d'EAGLE) et la loi de naissance par la loi de pression de Schaye & Dalla Vecchia 2008. Avantage : Kennicutt-Schmidt est
   reproduite **par construction** ; pas de pas de temps court. Inconvénient : pas de fontaine, pas de bulles, un disque
   de gaz lisse. C'est ce que font TNG et EAGLE pour des milliers de galaxies.
2. **Niveau « quantité de mouvement »** : chaque particule d'étoile jeune dépose, entre 3 et 40 Ma, la quantité de
   mouvement finale de ses supernovæ (3 × 10⁵ M☉ km/s par supernova, 1 supernova par 100 M☉) sur ses voisines de gaz.
   Avantage : reste valable en isotherme (pas besoin d'énergie interne), règle la turbulence et l'épaisseur du disque,
   auto-régule la naissance d'étoiles (Ostriker & Shetty 2011, ApJ 731, 41). C'est **le meilleur rapport réalisme/effort**
   pour l'état actuel du code.
3. **Niveau « multiphase »** : énergie interne + refroidissement tabulé (Grackle ou Ploeckinger & Schaye) + thermique
   stochastique ΔT = 10^7,5 K + pas de temps individuels. Donne gaz chaud, fontaine, bulles. Exige une SPH modernisée
   (§ 1.1) — c'est le chantier « GIZMO/AREPO » déjà identifié dans `docs/refonte-simulations-pro.md:300`.

### 3.3 Noyaux actifs

| Grandeur | Valeur | Source | Statut |
|---|---|---|---|
| Sgr A* : masse | 4,30 × 10⁶ M☉ | GRAVITY Collaboration 2022, A&A 657, L12 | [Probable] |
| Sgr A* : accrétion actuelle | ~10⁻⁸–10⁻⁷ M☉/an ; luminosité ~10³⁶ erg/s (10⁻⁹ d'Eddington) | Yuan & Narayan 2014, ARA&A 52, 529 | [Probable] |
| M31* : masse | ~1,4 × 10⁸ M☉ | Bender et al. 2005, ApJ 631, 280 | [Probable] |
| Accrétion de Bondi | Ṁ = 4π G² M² ρ / (c_s² + v²)^(3/2), plafonnée à Eddington | Bondi 1952 ; Springel, Di Matteo & Hernquist 2005, MNRAS 361, 776 | [Probable] |
| Efficacités | rayonnement ε_r = 0,1 (0,2 dans TNG) ; couplage thermique ε_f = 0,05–0,15 ; EAGLE : ΔT = 10^8,5 K ; TNG : mode cinétique à bas taux d'accrétion | Booth & Schaye 2009, MNRAS 398, 53 ; Weinberger et al. 2017, MNRAS 465, 3291 | [Probable] |

Aujourd'hui, la rétroaction de Sgr A* est **négligeable** pour le disque. Elle ne l'a pas toujours été (bulles de Fermi),
et la fusion Voie lactée–Andromède amènera du gaz au centre : un épisode actif y est plausible mais non prévisible
(Cox & Loeb 2008, MNRAS 386, 461 ; Schiavi et al. 2020, A&A 642, A30) [Probable]. Recommandation : ne pas le calculer ;
le dire. [Supposition]

---

## 4. Enrichissement chimique

| Grandeur | Valeur | Source | Statut |
|---|---|---|---|
| Métallicité solaire (masse) | Z☉ = 0,0134 (2009) ; 0,0139 (2021) ; 0,0165 (Magg et al. 2022) | Asplund et al. 2009, ARA&A 47, 481 ; 2021, A&A 653, A141 ; Magg et al. 2022, A&A 661, A140 | [Probable] |
| Rendements des supernovæ à effondrement | O, Mg, Si… : tables par masse et métallicité | Nomoto, Kobayashi & Tominaga 2013, ARA&A 51, 457 ; Limongi & Chieffi 2018, ApJS 237, 13 | [Probable] |
| Supernovæ Ia | ~0,6–0,7 M☉ de fer par explosion | Iwamoto et al. 1999, ApJS 125, 439 (W7) | [Probable] |
| Étoiles AGB | C, N, éléments s | Karakas 2010, MNRAS 403, 1413 | [Probable] |
| Fraction rendue R et rendement net y | R ≈ 0,3 (Salpeter) à 0,4–0,45 (Chabrier) ; y ≈ 0,02–0,06 selon loi de masses et tables | Vincenzo et al. 2016, MNRAS 455, 4183 | [À vérifier pour les chiffres exacts] |
| Gradient radial du disque | ≈ −0,04 à −0,07 dex/kpc (O/H du gaz, [Fe/H] des étoiles jeunes) | Méndez-Delgado et al. 2022, MNRAS 510, 4436 ; Lemasle et al. 2018 | [À vérifier] |
| Mise en œuvre dans les codes | 9 à 11 éléments suivis par particule ; libération selon l'âge de la population | Wiersma et al. 2009b, MNRAS 399, 574 | [Probable] |

**Film : rien.** Impact sur l'image : la métallicité règle le refroidissement (négligeable tant qu'il est absent), le
rapport poussière/gaz (§ 5.4) et la couleur des étoiles nées (une population pauvre en métaux est plus bleue de ~0,1 à
0,2 mag en B−V à âge égal [Probable]). Version minimale suffisante : **un seul scalaire Z par particule**, initialisé par
le gradient mesuré, augmenté par le rendement net à chaque naissance voisine (modèle « boîte » local). [Supposition]

---

## 5. Poussière

### 5.1 Cartes 3D disponibles

| Carte | Étendue | Finesse | Grandeur | Source | Statut |
|---|---|---|---|---|---|
| **Edenhofer et al. 2024** | 69 pc à 1,25 kpc, tout le ciel ; **carte supplémentaire jusqu'à 2 kpc** | ~parsec en distance, 14′ | extinction en unités de Zhang, Green & Rix 2023 ; A_V = 2,8 × E | A&A 685, A82 ; arXiv:2308.01295 ; Zenodo 10.5281/zenodo.10658339 | [Certain : étendue et extension lues aujourd'hui (dustmaps) ; facteur 2,8 lu dans `build_dust.py:6`] |
| Bayestar19 | déclinaison > −30° (3/4 du ciel), jusqu'à quelques kpc | ~3,4′–13,7′, 120 tranches de distance | rougissement en unité propre (coefficients de la table 1 de l'article) | Green et al. 2019, ApJ 887, 93 | [Certain pour la couverture ; Probable pour le reste] |
| DECaPS 3D | plan sud, 239° < l < 6°, bande de 20°, **fiable jusqu'à ~10 kpc** | ~1′ | E(B−V) ; A_V = 3,32 E(B−V) | Zucker et al. 2025 | [Certain pour étendue et unité (dustmaps) ; référence À vérifier] |
| Lallement / Vergely 2022 | cube 6 × 6 × 0,8 kpc autour du Soleil (jusqu'à 3 kpc ; version 5 kpc plus grossière) | 10 à 50 pc | densité d'extinction A₀ (550 nm) en mag/pc | Lallement et al. 2022, A&A 661, A147 ; Vergely et al. 2022, A&A 664, A174 | [Probable] |
| Leike, Glatzle & Enßlin 2020 | boîte 740 × 740 × 540 pc | 1 pc | — | A&A 639, A138 | [Certain pour la boîte] |
| Marshall et al. 2006 | plan, −100° < l < 100°, bande de 20° | 15′ | A_Ks (2MASS) | A&A 453, 635 | [Certain pour la couverture] |
| Dharmawardena et al. 2024 | tout le ciel jusqu'à 2,8 kpc | — | — | MNRAS 532, 3480 | [À vérifier] |
| **Zhang, Chen et al. 2026** | **plan galactique vu de face (|Z| < 25 pc), 360°, jusqu'à ~7 kpc** | 10, 50 et 100 pc | densité de poussière ; longueur d'échelle du disque de poussière 2,90 kpc ; bras, éperons, cavités | arXiv:2607.06016 (prépublication du 7 juillet 2026) | [Certain, résumé lu aujourd'hui ; non encore publié dans une revue] |
| Zhang & Green 2025 | carte 3D de la **forme** de la loi d'extinction (R_V) ; ~130 millions d'étoiles (spectres basse résolution) | — | R_V(x, y, z) | arXiv:2407.14594 ; Science 387, 1209 | [Certain pour 130 M et le contenu ; Probable pour la référence de revue] |
| 2D : SFD ; Planck GNILC | tout le ciel, intégré | 6′ ; 5′ | E(B−V) | Schlegel et al. 1998, ApJ 500, 525 (recalibré × 0,86 : Schlafly & Finkbeiner 2011, ApJ 737, 103) ; Planck 2016 | [Probable] |
| Modèles lisses | toute la Galaxie | — | — | Drimmel & Spergel 2001, ApJ 556, 181 ; Drimmel et al. 2003, A&A 409, 205 | [Certain pour l'usage dans l'appli] |

**Ce que fait l'appli** [Certain] :

- `pipeline/build_dust.py` : carte d'Edenhofer moyennée sur 160 × 160 × 52 cases de 15,625 pc (|x|,|y| ≤ 1 250 pc,
  |z| ≤ 406 pc), 27 points par case, un octet en log de 10⁻⁵ à 10⁻¹ mag/pc (lignes 28-30, 82-84) ; A_V = 2,8 × E
  (ligne 29) ; en deçà de la première sphère (68,8 pc), la moyenne publiée de la bulle intérieure (ligne 62).
- `pipeline/natif/voie_lactee.py:33-35, 265-279` : au-delà de 1,25 kpc, forme de Drimmel & Spergel 2001, amplitude calée
  sur la moyenne mesurée dans le plan (1,49 mag jusqu'à 1,25 kpc, d'où 1,18 mag/kpc au Soleil,
  `docs/gaia-voie-lactee.md:74-75`), plus des **bandes sombres ×(1 + 3) sur le bord intérieur des bras [modèle]**.
- Grande grille : 320 × 320 × 80 cases de 100 pc × 50 pc (ligne 51).

**Écarts** :

1. **Étendue mesurée** : l'appli s'arrête à 1,25 kpc alors que la carte supplémentaire d'Edenhofer va à 2 kpc, que
   Vergely 2022 va à 3 kpc, DECaPS à ~10 kpc dans le plan sud, et que la carte de Zhang, Chen et al. 2026 donne **le plan
   entier jusqu'à 7 kpc à 100 pc** — exactement la taille des cases de la grande grille. Cette dernière remplacerait le
   modèle de bandes sombres supposées par une mesure sur ~40 % de la surface du disque. [Supposition pour l'intérêt ;
   prépublication à surveiller]
2. **Quantification** : un octet sur 4 décades = pas de 3,7 % par niveau : sans effet visible. Mais le **plafond à
   0,1 mag/pc** écrête les cœurs de nuages (A_V de plusieurs mag sur 15 pc) [Supposition] ; le script imprime « A_V max par
   case » (ligne 89), à regarder.
3. **Hauteur de la boîte locale** : |z| ≤ 406 pc alors que la carte couvre toute la sphère de 1,25 kpc ; les nuages de
   haute latitude au-delà de 400 pc de hauteur sont rares : écart faible. [Supposition]
4. **Longueur d'échelle** : Drimmel & Spergel donnent h_r = 2,26 kpc (`voie_lactee.py:33`) ; la nouvelle mesure donne
   2,90 kpc [Certain, lu aujourd'hui]. Écart de 28 % sur la décroissance radiale de la poussière.
5. **La poussière ne bouge pas avec le film** : elle est écrite dans le repère de la Galaxie d'aujourd'hui. Quand le temps
   avance de centaines de Ma (bras qui tournent, rencontre avec Andromède), les bandes sombres restent figées. Avec du gaz
   dans le film, la poussière devrait en être tirée (§ 5.4). [Certain pour le code ; Supposition pour le remède]

### 5.2 Loi d'extinction

| Loi | Domaine | Forme | Source | Statut |
|---|---|---|---|---|
| Cardelli, Clayton & Mathis 1989 | 0,125–3,5 µm | A(λ)/A_V = a(x) + b(x)/R_V, x = 1/λ | ApJ 345, 245 | [Probable ; polynômes recalculés aujourd'hui] |
| Fitzpatrick 1999 | 0,1–3,5 µm | spline + profil de Drude pour la bosse à 2 175 Å | PASP 111, 63 | [Probable] |
| **Gordon et al. 2023** | **912 Å à 32 µm**, R_V de 2,3 à 5,6 ; quatre échantillons spectroscopiques réunis | une seule relation fonction de R_V | ApJ 950, 86 ; DOI 10.3847/1538-4357/accb59 ; arXiv:2304.01991 | [Certain, lu aujourd'hui] |
| Moyenne galactique | R_V = A_V / E(B−V) = 3,1 ; dispersion σ ≈ 0,18 ; 2,5 (diffus) à ~5,5 (nuages denses) | — | Schlafly et al. 2016, ApJ 821, 78 | [Probable] |
| Variation 3D de R_V | R_V baisse dans le gaz modérément dense (accrétion sur les grains), remonte dans le très dense (coagulation) ; courbe plus plate dans les régions de formation d'étoiles | — | Zhang & Green 2025 (arXiv:2407.14594) | [Certain, résumé lu aujourd'hui] |

Valeurs de A(λ)/A_V selon CCM89 (calculées aujourd'hui avec les polynômes optiques) [Supposition, calcul] :

| λ (nm) | R_V = 3,1 | R_V = 2,5 | R_V = 5,0 |
|---|---|---|---|
| 440 (B) | 1,325 | 1,402 | 1,201 |
| 465 (bleu d'écran sRGB, pic) | 1,234 | 1,288 | 1,149 |
| 486 (Hβ) | 1,164 | 1,200 | 1,108 |
| 501 ([O III]) | 1,120 | 1,145 | 1,081 |
| 530 (vert d'écran) | 1,043 | 1,051 | 1,031 |
| 550 (V) | 1,000 | 1,000 | 1,000 |
| 610 (rouge d'écran) | 0,890 | 0,875 | 0,914 |
| 656 (Hα) | 0,818 | 0,796 | 0,852 |
| 700 (R) | 0,750 | 0,722 | 0,795 |

Infrarouge (CCM, R_V = 3,1) : I 0,48 ; J 0,28 ; H 0,19 ; K 0,11 [Probable].

**Ce que fait l'appli** :

- `natif/shaders/gaia.vert:134-144` : étoiles du **modèle** seulement (drapeau 16), 16 pas le long du rayon dans la grande
  grille, puis `vCol *= 10^(−0,4 A_V × (0,75 ; 1,0 ; 1,32))`, « CCM89, R_V = 3,1 » [Certain].
  **Écart** : 0,75 et 1,32 sont les coefficients des **bandes R (700 nm) et B (440 nm) de Johnson**, pas ceux des trois
  couleurs d'un écran sRGB (pics ~610, ~530–550, ~465 nm), qui seraient environ **(0,89 ; 1,02 ; 1,23)**. Le
  rougissement affiché est donc ~2 fois trop fort en écart de couleur : (1,32 − 0,75) = 0,57 contre (1,23 − 0,89) = 0,34
  par magnitude de A_V. Le commentaire dit « [approché] » ; c'est un écart moyen, facile à corriger. [Supposition, calcul ;
  le bon calcul intègre la loi sur les courbes des trois primaires et le spectre de l'étoile]
- `natif/shaders/voie_lactee.frag:64` : la lueur diffuse est atténuée par `pow(10, −0,4 × A_V)` **identique sur les trois
  couleurs** [Certain]. **Écart fort sur l'aspect** : la vraie Voie lactée rougit vers le centre et le long des bandes
  sombres (c'est ce qui donne le brun-orangé des photos) ; ici les bandes sont grises. Correction en une ligne (même
  vecteur que pour les étoiles).
- Les étoiles **mesurées** ne sont pas ré-éteintes (`voie_lactee.h:8`, `gaia.h:321`) : leur magnitude contient déjà la
  poussière vue du Soleil. C'est exact **vu du Soleil** ; dès que la caméra s'éloigne, l'extinction devrait être
  recalculée sur le nouveau trajet (dé-rougir avec la carte Soleil → étoile, puis ré-éteindre caméra → étoile). Dans la
  sphère de 1,25 kpc où la carte est mesurée, c'est faisable honnêtement ; au-delà c'est du modèle. Gaia DR3 fournit
  aussi une extinction par étoile (A_G, GSP-Phot) pour ~470 millions d'étoiles (Andrae et al. 2023, A&A 674, A27)
  [Probable]. [Supposition pour le remède]
- Les galaxies voisines sont hors carte (`gaia.vert:136`) : Andromède, le Triangle et les Nuages n'ont **aucune
  poussière** dans le rendu en particules, alors que les bandes sombres d'Andromède sont son trait le plus
  reconnaissable. [Certain pour le code]

### 5.3 Diffusion

- Albédo de la poussière dans le visible ≈ 0,6–0,7 ; asymétrie g = ⟨cos θ⟩ ≈ 0,5–0,6 (diffusion vers l'avant) ; fonction de
  phase de Henyey & Greenstein 1941 (ApJ 93, 70). Draine 2003, ApJ 598, 1017 ; Weingartner & Draine 2001, ApJ 548, 296.
  [Probable]
- Conséquences : nébuleuses par réflexion (bleues : la diffusion croît vers le bleu) ; lumière galactique diffuse ; une
  bande sombre vue de l'extérieur est moins noire que e^(−τ) car elle renvoie de la lumière. [Probable]
- Appli : absorption pure. Une approximation classique sans lancer de rayons secondaires : remplacer τ par
  τ √(1 − ω) (ω albédo) dans les milieux mélangés (approximation des deux flux) [À vérifier : forme exacte], ou ajouter
  un terme source ω κ J avec J tiré de la grille de lumière floutée. [Supposition]

### 5.4 Rapport poussière/gaz et lien avec le gaz du film

| Grandeur | Valeur | Source | Statut |
|---|---|---|---|
| N_H / E(B−V) | 5,8 × 10²¹ cm⁻² mag⁻¹ | Bohlin, Savage & Drake 1978, ApJ 224, 132 | [Probable] |
| N_H / A_V | 1,87 × 10²¹ (R_V = 3,1) ; révisions : 2,08 × 10²¹ (Zhu et al. 2017, MNRAS 471, 3494) ; plus haut à faible colonne (Lenz, Hensley & Doré 2017, ApJ 846, 38 : 8,8 × 10²¹ par E(B−V)) | — | [Probable] |
| **A_V par parsec** | **1,65 × 10⁻³ × n_H [cm⁻³] × (Z/Z☉)** mag/pc, soit 1,65 mag/kpc pour 1 atome/cm³ | dérivé de Bohlin et al. | [Supposition, calcul : 3,086 × 10¹⁸ / 1,87 × 10²¹] |
| Rapport de masse poussière/gaz | ~1/100 à 1/160 dans la Voie lactée | Draine & Li 2007, ApJ 657, 810 ; Draine 2011 | [Probable] |
| Dépendance en métallicité | ∝ Z près de Z☉ ; chute plus rapide sous ~0,2 Z☉ | Rémy-Ruyer et al. 2014, A&A 563, A31 | [Probable] |
| Rapport gaz/poussière croissant avec le rayon galactique | utilisé pour réviser le taux de naissance | Elia et al. 2025, arXiv:2501.14471 | [Certain, lu aujourd'hui] |

Contrôle croisé : le modèle de l'appli donne 1,18 mag/kpc au Soleil ; avec la formule, cela correspond à n_H ≈ 0,7 cm⁻³
en moyenne dans le plan — cohérent avec la densité moyenne du milieu interstellaire local (~1 cm⁻³). [Supposition]

Le gaz du film (1,22 × 10¹⁰ M☉) et la poussière de l'appli sont **deux objets indépendants**. Les faux relevés
professionnels tirent la poussière du gaz simulé (Ananke : Sanderson et al. 2020, ApJS 246, 6, déjà cité dans
`docs/refonte-simulations-pro.md:113`). Pour le film : A_V/pc = 1,65 × 10⁻³ n_H Z/Z☉ appliqué à la densité SPH, en ne
comptant que le gaz froid/tiède (T < ~10⁴·⁵ K ; ici tout le gaz, puisqu'il est isotherme). [Supposition]

### 5.5 Émission infrarouge de la poussière

- Corps gris : I_ν = τ_ν B_ν(T_d), τ_ν ∝ ν^β ; moyenne du ciel : T_d ≈ 19,7 K, β ≈ 1,6 (Planck 2013 XI, A&A 571, A11)
  [Probable]. Pic vers 150 µm.
- Bandes des hydrocarbures aromatiques (PAH) : 3,3 ; 6,2 ; 7,7 ; 8,6 ; 11,3 µm — c'est ce que montre WISE 12 µm
  [Probable].
- Bilan : environ un quart à un tiers de la lumière des étoiles d'une spirale est absorbé puis réémis en infrarouge
  (Viaene et al. 2016, A&A 586, A13 ; Bianchi et al. 2018, A&A 620, A112) [Probable].
- Appli : cartes mesurées AKARI 90/140 µm, WISE 12/22 µm, Planck 353–857 GHz (`ciel_bandes.py:94-139`) : **mesuré, vu de
  la Terre seulement** (le menu le dit : « vues depuis la Terre », `interface_lumiere.h:38`) [Certain]. Vu d'ailleurs,
  on pourrait calculer l'émission à partir de la grille 3D (j_ν ∝ ρ_poussière B_ν(T_d)) : modèle, à signaler.

---

## 6. Rayonnement et lumière pour le rendu

### 6.1 Transfert radiatif

- Équation : dI_ν/ds = −(κ_abs + κ_diff) ρ I_ν + j_ν + κ_diff ρ ∫ Φ(Ω, Ω′) I_ν(Ω′) dΩ′. [Certain, manuel]
- Solution sans diffusion (celle de l'appli) : I = ∫ j(s) e^(−τ(s)) ds, τ = 0,921 × A (A en mag).
  `voie_lactee.frag:52-66` l'intègre en 192 pas avec décalage aléatoire, extinction prise au milieu du pas (ligne 64) :
  schéma correct au second ordre [Certain].
- Outils professionnels pour fabriquer des images de simulations : SKIRT (Camps & Baes 2015, Astron. Comput. 9, 20 ;
  2020, 31, 100381), Sunrise (Jonsson 2006, MNRAS 372, 2), Powderday (Narayanan et al. 2021, ApJS 252, 12), RADMC-3D ;
  populations stellaires : Bruzual & Charlot 2003 (MNRAS 344, 1000), FSPS (Conroy, Gunn & White 2009, ApJ 699, 486).
  Images synthétiques de TNG : Rodriguez-Gomez et al. 2019, MNRAS 483, 4140. [Probable]
- Recette intermédiaire très utilisée : Charlot & Fall 2000 (ApJ 539, 718) — les étoiles de moins de 10 Ma sont derrière
  leur nuage natal (τ_V ≈ 1,0) en plus du milieu diffus (τ_V ≈ 0,3), loi en λ^(−0,7). Simple à appliquer aux étoiles de
  sorte 5 du film. [Probable]
- Pas d'échantillonnage : 192 pas répartis sur toute la traversée de la **grande** grille (jusqu'à ~45 kpc), soit ~100 à
  235 pc par pas, plus que les cases de 100 pc × 50 pc et bien plus que les 15,6 pc de la carte locale. Le décalage
  aléatoire transforme l'erreur en bruit, ce qui est honnête, mais **vu du Soleil les nuages mesurés à 15 pc ne sont
  échantillonnés que tous les ~100–200 pc**. Remède : pas plus fin dans la boîte locale. [Supposition, lecture du code]

### 6.2 Régions HII, Hα, [O III]

| Grandeur | Valeur | Source | Statut |
|---|---|---|---|
| Raies visibles | Hα 656,28 nm ; Hβ 486,13 ; [O III] 495,9 et 500,7 ; [N II] 654,8 et 658,3 ; [S II] 671,6 et 673,1 ; [O II] 372,7 | Osterbrock & Ferland 2006 | [Probable] |
| Recombinaison, cas B, 10⁴ K | α_B = 2,59 × 10⁻¹³ cm³/s ; Hα/Hβ = 2,86 ; L(Hα) = 1,37 × 10⁻¹² erg × Q (photons ionisants/s) | idem | [Probable] |
| Rayon de Strömgren | R_S = [3Q / (4π n² α_B)]^(1/3) : 68 pc pour Q = 10⁴⁹ s⁻¹ (étoile O7) et n = 1 cm⁻³ ; 3,2 pc à n = 100 | Strömgren 1939, ApJ 89, 526 | [Supposition, calcul] |
| Mesure d'émission | I(Hα) = 1 rayleigh pour EM = 2,25 pc cm⁻⁶ à 8 000 K ; 1 R = 10⁶/4π photons cm⁻² s⁻¹ sr⁻¹ | Haffner et al. 2003, ApJS 149, 405 (WHAM) | [Probable] |
| Taux de naissance ↔ Hα | SFR = 7,9 × 10⁻⁴² L(Hα) [erg/s] (Salpeter) ; 5,4 × 10⁻⁴² (Kroupa) | Kennicutt 1998, ARA&A 36, 189 ; Kennicutt & Evans 2012, ARA&A 50, 531 | [Probable] |
| Photons ionisants de la Voie lactée | Q ≈ 2,6 × 10⁵³ s⁻¹ → L(Hα) ≈ 3,6 × 10⁴¹ erg/s ≈ 10⁸ L☉ | McKee & Williams 1997, ApJ 476, 144 | [Probable ; conversion = Supposition] |
| Carte du ciel | composite VTSS + SHASSA + WHAM, 6′ | Finkbeiner 2003, ApJS 146, 407 | [Certain pour l'usage, `ciel_bandes.py:167`] |
| Catalogue | ~8 400 régions HII et candidates (WISE) | Anderson et al. 2014, ApJS 212, 1 | [Certain pour l'usage, `voie_lactee.py:22`] |

Couleur vraie : une région HII ordinaire est **rose-rouge** (Hα rouge + Hβ et Hγ bleues) ; les zones de haute excitation
et les nébuleuses planétaires tirent vers le **vert-bleu** ([O III] 501 nm) ; à l'œil nu, sans couleur ou verdâtre (l'œil
de nuit est sensible à 507 nm, pas à 656). [Probable]

**Appli** : régions HII du catalogue WISE à leur place mesurée, **éclat [modèle]** (`HII_ECLAT = 6`, « plus grande, plus
lumineuse jusqu'à ×3 », `voie_lactee.py:96, 258`), couleur (1,0 ; 0,30 ; 0,50) (`voie_lactee.h:76`) [Certain]. Écarts :

1. L'éclat pourrait être **mesuré** au lieu de supposé : le catalogue WISE donne des flux radio/infrarouge pour une
   partie des régions, et le continu radio libre-libre donne Q directement, sans poussière (Q ∝ S_ν D²) [Probable pour
   la physique ; À vérifier pour ce que contient la table VizieR].
2. Canal unique : la lueur HII est une couleur fixe ; Hα (656 nm) est moins éteinte que la lumière des étoiles (A = 0,82
   A_V) — avec l'extinction grise actuelle, pas de différence.
3. Régions HII absentes à moins de 1–2 kpc du Soleil (`HII_LOIN_DU_SOLEIL`) : choix justifié (elles couvriraient le
   ciel), mais **Orion, la Rosette, la Lagune, λ Orionis, Gum, la boucle de Barnard** sont précisément dans cette zone.
   La carte Hα de Finkbeiner pourrait servir de texture de ciel additionnelle vue du Soleil (mesuré), en fondu avec le
   modèle 3D quand on s'éloigne. [Supposition]
4. Avec le film : chaque particule de sorte 5 de moins de ~10 Ma devrait porter une région HII (Q ≈ 5 × 10⁴⁶ photons/s
   par M☉ pendant ~3–5 Ma pour une population de Kroupa [Probable, Starburst99]) : le rose des bras suivrait alors la
   naissance d'étoiles calculée.

### 6.3 Raie à 21 cm, CO, synchrotron, fond diffus

| Rayonnement | Physique | Référence | Dans l'appli |
|---|---|---|---|
| **21 cm** | transition hyperfine de H, 1 420,405752 MHz, A = 2,88 × 10⁻¹⁵ s⁻¹ (durée de vie ~11 Ma) ; N_HI = 1,823 × 10¹⁸ ∫T_B dv cm⁻² (optiquement mince) | HI4PI 2016, A&A 594, A116 | carte de densité de colonne HI4PI (`ciel_bandes.py:35`) [Certain] ; pas de cube en vitesse |
| **CO (1–0)** | 115,271 GHz ; N_H₂ = X_CO W_CO, X_CO = 2 × 10²⁰ cm⁻² (K km/s)⁻¹ ± 30 % | Dame et al. 2001 ; Bolatto, Wolfire & Leroy 2013, ARA&A 51, 207 | **absent** [Certain] |
| **Synchrotron** | électrons relativistes dans B : j ∝ n_CR B_⊥^((p+1)/2) ν^(−(p−1)/2), p ≈ 3 ; T_B ∝ ν^(−β), β ≈ 2,7–3,1 | Haslam et al. 1982 ; Remazeilles et al. 2015, MNRAS 451, 4311 ; Planck 2015 X, A&A 594, A10 | 408 MHz Haslam + Planck 30–70 GHz [Certain] |
| **Libre-libre** | même gaz que Hα ; j ∝ n_e² T^(−0,35) ν^(−0,1) | Draine 2011 | implicite dans Planck 30–100 GHz |
| **Fond diffus cosmologique** | corps noir T₀ = 2,7255 ± 0,0006 K ; dipôle 3,3621 ± 0,0010 mK → 369,82 ± 0,11 km/s vers (l, b) = (264,02°, 48,25°) ; anisotropies ~±100–300 µK | Fixsen 2009, ApJ 707, 916 ; Planck 2018 I, A&A 641, A1 | carte SMICA (`ciel_bandes.py:44`) [Certain] |
| **Fond de lumière extragalactique** | visible : ~11 nW m⁻² sr⁻¹ (New Horizons, compatible avec la somme des galaxies) | Postman et al. 2024, ApJ 972, 95 | sans objet [Probable ; chiffre À vérifier] |
| **X mous** | couronne à 0,2 keV, bulle locale, bulles eROSITA | Predehl et al. 2020 ; Zheng et al. 2024 | ROSAT + eROSITA DR1 (moitié ouest du ciel) [Certain] |
| **Gamma** | π⁰ des rayons cosmiques sur le gaz (trace gaz × rayons cosmiques), Compton inverse | Ackermann et al. 2012, ApJ 750, 3 | Fermi-LAT 3 bandes [Certain] |

Remarques :

- Le **CO manque** : c'est le traceur du gaz moléculaire, donc des lieux de naissance d'étoiles ; la carte de Dame 2001
  (ou la carte CO de Planck, tout le ciel : Planck 2013 XIII, A&A 571, A13) est au format HiPS au CDS [À vérifier pour
  l'identifiant HiPS].
- Les cubes en vitesse (HI4PI, CO) contiennent la **troisième dimension cinématique** : avec une courbe de rotation, ils
  donnent la distribution 3D du gaz dans tout le disque (Nakanishi & Sofue 2016, PASJ 68, 5 ; Mertsch & Vittino 2021,
  A&A 655, A64 ; Söding et al. 2025 pour une reconstruction récente [À vérifier]). C'est la source **mesurée** naturelle
  pour remplacer le disque de gaz exponentiel lisse du départ du film par la vraie carte (bras, trou central, anneau
  moléculaire, gauchissement). [Probable pour les deux premières références]
- Toutes ces cartes sont **des ciels vus de la Terre** : hors du Soleil elles n'ont pas de sens géométrique. L'appli le
  dit (`interface_lumiere.h:38`). Les montrer en se déplaçant demanderait un modèle 3D d'émission par bande (le modèle
  de ciel de Planck, PySM : Thorne et al. 2017, MNRAS 469, 2821, n'est lui aussi qu'un ciel 2D). [Probable]

### 6.4 Luminosité de surface et couleurs réelles

- La **luminosité de surface ne dépend pas de la distance** (conservation de l'étendue), à (1 + z)⁻⁴ près (Tolman). Une
  galaxie vue de près n'est pas plus brillante par unité d'angle solide : elle est plus grande. [Certain, manuel]
- Conversion : μ [mag/arcsec²] = M☉ + 21,572 − 2,5 log₁₀ Σ [L☉/pc²]. Avec M☉,V = 4,81 (Willmer 2018, ApJS 236, 47 ;
  l'appli prend 4,83, `voie_lactee.py:54`, écart de 2 %) [Probable].
- Loi de Freeman : brillance centrale des disques μ₀(B) = 21,65 ± 0,30 mag/arcsec² (Freeman 1970, ApJ 160, 811)
  [Probable].
- Disque de la Voie lactée au rayon du Soleil, vu de face : ~24 L☉/pc² en V → **μ_V ≈ 23 mag/arcsec²**, plus faible que
  le ciel nocturne terrestre le plus noir (~21,8–22) [Supposition, calcul ; Σ_L d'après Flynn et al. 2006, MNRAS 372,
  1149, Probable]. De l'extérieur, à l'œil nu adapté à la nuit, la Voie lactée serait une lueur **pâle et sans couleur**,
  comme Andromède vue de la Terre ; les couleurs saturées sont celles de la photographie à longue pose.
- Voie lactée entière : M_V ≈ −20,7, M_B ≈ −20,05, M_r ≈ −21,0 (Licquia, Newman & Brinchmann 2015, ApJ 809, 96 ;
  Licquia, Newman & Bershady 2016, table relue aujourd'hui dans arXiv:1610.05769, valeurs partiellement illisibles dans
  l'extraction) ; couleur (g − r) ≈ 0,68 : la Voie lactée est dans la « vallée verte », entre spirales bleues et
  elliptiques rouges [Probable].
- **Appli** : `voie_lactee.h:69-70` prend « B−V = 0,744 (Licquia, Newman et Bershady 2015, table 3) ». La table relue
  aujourd'hui donnerait B − V ≈ 0,66 (−20,05 − (−20,71)) ; et l'article des couleurs de 2015 est signé Licquia, Newman &
  **Brinchmann** (Bershady est coauteur de celui de 2016). **Valeur et référence à relire** [À vérifier — l'extraction
  automatique de la table était abîmée, je ne tranche pas].
- En format v2 (4 canaux), cette couleur mesurée est **remplacée** par quatre teintes fixes « saturation renforcée comme
  sur les photos » (`voie_lactee.h:73-77`) et la part des bras est supposée (`PART_BRAS = 0,5`, `voie_lactee.py:93`) :
  signalé comme modèle, bien. Contrôle possible : la somme pondérée des quatre teintes devrait redonner la couleur
  intégrée mesurée. [Supposition]
- Compression `ln(1 + Y)` sur la luminance (`voie_lactee.frag:67-72`) puis c/(1 + c) et sRGB (`ecran.frag:19-20`) : choix
  d'affichage déclarés [Certain]. Un mode « œil nu » (seuil de couleur de l'œil vers ~21–22 mag/arcsec² : en dessous,
  vision sans couleur) serait la version « ce à quoi ça ressemble vraiment » ; le mode actuel est « photo longue pose ».
  Les deux sont légitimes s'ils sont nommés. [Supposition]
- Couleur des étoiles : `gaia.vert:33` utilise l'approximation de corps noir « de Tanner Helland » (ajustement graphique,
  non colorimétrique). La référence physique est l'intégration du spectre de Planck sur les fonctions colorimétriques
  CIE 1931 puis conversion en sRGB (D65) ; les écarts sont de quelques % sur les teintes, plus aux extrêmes (< 2 000 K,
  > 20 000 K) [Probable]. Écart faible.

### 6.5 Vitesse finie de la lumière, aberration, Doppler

| Effet | Formule | Ordre de grandeur | Source |
|---|---|---|---|
| Temps de trajet | on voit l'objet là où il était à t − d/c | Soleil 8,3 min ; Jupiter 33–53 min ; centre galactique 26 700 ans ; M31 2,5 Ma ; un objet à 220 km/s parcourt 0,74 pc en 1 000 ans | [Certain, calcul] |
| Aberration (observateur de vitesse β = v/c) | cos θ′ = (cos θ + β) / (1 + β cos θ) ; les étoiles se resserrent vers l'avant | Terre : constante d'aberration 20,4955″ (v = 29,78 km/s) ; Soleil dans la Galaxie : ~2,6′ (fixe, non observable directement) | Einstein 1905 ; IAU 2000 [Probable] |
| Dérive séculaire d'aberration | accélération du Soleil vers le centre : 2,32 × 10⁻¹⁰ m/s² → 5,05 ± 0,35 µas/an | mesurée par Gaia | Gaia Collaboration, Klioner et al. 2021, A&A 649, A9 [Probable] |
| Doppler relativiste | D = 1 / [γ (1 − β cos θ′)] ; ν_obs = D ν | 300 km/s → 0,1 % : invisible à l'œil | [Certain, manuel] |
| Intensité | I_ν/ν³ invariant : I_obs(ν_obs) = D³ I(ν) ; bolométrique ∝ D⁴ ; un corps noir reste un corps noir à T′ = D T ; angles solides ∝ D⁻² | à β = 0,5 vers l'avant : D = 1,73, une étoile de 5 800 K paraît à 10 000 K | Rybicki & Lightman 1979, ch. 4 ; McKinley 1979, Am. J. Phys. 47, 602 [Probable] |
| Décalage cosmologique | 1 + z = a₀/a ; brillance de surface ∝ (1 + z)⁻⁴ ; correction K | z = 0,03 → −12 % | Tolman 1930 ; Hogg 1999, astro-ph/9905116 [Probable] |
| Dipôle du fond diffus pour l'observateur | T(θ) = T₀ / [γ (1 − β cos θ)] | 3,36 mK pour 370 km/s | Planck 2018 I [Probable] |

**Appli** : aucun de ces effets dans `natif/shaders` ni `natif/src` (recherche « doppler, aberr, relativ, temps de
trajet » : seules occurrences = relativité générale du Soleil dans l'intégrateur planétaire, `nbody_noyau.h:6,121`, et
décalage vers le rouge des galaxies pour la distance) [Certain]. `HANDOVER.md:133` note que l'assombrissement de Tolman
n'est pas appliqué, avec justification (points non résolus ; z < 0,03 pour les galaxies photographiées) [Certain].

Appréciation [Supposition] :

1. **Temps de trajet dans le Groupe local** : négligeable à l'échelle du film (M31 : 0,3 kpc de mouvement propre et ~2°
   de rotation en 2,5 Ma, pour 765 kpc de distance). Impact faible. Mais la **phrase** « vous voyez Andromède telle
   qu'elle était il y a 2,5 Ma » est vraie et pourrait être dite.
2. **Temps de trajet dans le système solaire** : les positions apparentes des planètes vues de la Terre diffèrent des
   positions géométriques de ~v/c ≈ 20″ à 1′ (aberration planétaire). Invisible à l'écran sauf en mode « ciel vu de la
   Terre » très zoomé ou pour les éclipses et occultations (un `essai_eclipse.cpp` existe : à vérifier que le temps de
   lumière y est pris en compte) [À vérifier].
3. **Observateur rapide** : la caméra de l'appli traverse la Galaxie en secondes, soit des vitesses apparentes de
   millions de fois c ; aucune physique relativiste ne s'y applique. Un mode « vaisseau » (β < 1 choisi par
   l'utilisateur) avec aberration + T′ = D T + flux ∝ D⁴ est simple à écrire dans les shaders d'étoiles (ils ont déjà une
   teinte par température, `gaia.vert:131`) et physiquement exact ; à présenter comme un mode à part, pas comme le rendu
   normal.
4. **Vitesse radiale des étoiles** (jusqu'à ~500 km/s) : décalage de couleur < 0,2 %, invisible. Aucun besoin.

---

## 7. Ce que le film fait du gaz : récapitulatif de lecture

| Élément | Fichier:ligne | Constat | Statut |
|---|---|---|---|
| SPH classique, noyau spline cubique, ~58 voisines (η = 1,2) | `gaz_gpu.py:8-10, 30` | conforme à Monaghan 1992 ; pas de termes grad-h | [Certain] |
| Force symétrisée par moyenne des noyaux | `gaz_gpu.py:131, 141` | quantité de mouvement conservée par paire, à condition que la recherche de voisines soit symétrique : elle l'est (h_max par nœud, ligne 121-122) | [Certain] |
| Viscosité α = 1, β = 2, Balsara | `gaz_gpu.py:31, 134-139, 204` | standard ; le terme 10⁻⁴ c_s/h évite la division par zéro | [Certain] |
| Mise à jour de h : moyenne ancien/cible, 2 passes en production | `gaz_gpu.py:191-194` ; `gaz_galaxie.py:55` | h n'est pas convergé à chaque pas (2 passes) : le nombre de voisines fluctue ; acceptable en isotherme | [Certain / Supposition] |
| Pile de 128, test `sp < 126` | `gaz_gpu.py:85, 102, 144` | si la pile déborde, des sous-arbres sont **ignorés en silence** (voisines manquantes) ; improbable avec un arbre de Karras équilibré (profondeur ≤ ~63) mais sans alarme | [Certain pour le code ; Supposition pour le risque] |
| Simple précision, positions centrées sur la médiane | `gaz_gpu.py:159-166` | « à utiliser galaxie par galaxie » (ligne 20-21) ; or `stabilite_tir.py:150` passe **toutes** les particules de sorte 3 d'un coup : correct pour une galaxie seule, **à découper par galaxie pour la rencontre** (à 800 kpc, la simple précision ne distingue plus 60 pc) | [Certain] |
| Isotherme 10 km/s, plancher de Jeans N = 4 | `gaz_galaxie.py:29-30, 58-60` | voir § 2.4, points 1 à 3 | [Certain] |
| Naissance : seuil 0,1 cm⁻³, ε = 1 % | `gaz_galaxie.py:31, 34, 65-80` | voir § 2.4 | [Certain] |
| Gaz branché seulement dans le tir de stabilité | `stabilite_tir.py:141-145, 150-153, 193` (option `--gaz`) | ni `rencontre.py` ni `film_v2.py` ni `calcul.py` n'appellent `gaz_galaxie` : **le film de la rencontre n'a pas encore de gaz** ; `rencontre.py:370` le dit (« il n'y a pas de gaz froid dans le calcul ») | [Certain, recherche faite aujourd'hui] |
| Schéma temporel : saute-mouton, viscosité évaluée avec la vitesse du pas précédent | `stabilite_tir.py:187-193` | la force de viscosité dépend de v ; dans le saute-mouton elle est calculée avec v à mi-pas « décalée » (pas de prédiction comme dans `essai_gaz.py:70`) : erreur du premier ordre sur la dissipation, sans gravité en isotherme | [Certain pour le code ; Supposition pour l'effet] |
| Bulletin | `bulletin.py:60, 67-68` | compare masse de gaz et taux de naissance aux mesures (1,65 ± 0,19 ; 1,22 ± 0,3 × 10¹⁰) | [Certain] |
| Contrôles | `essai_gaz.py` | gradient (4 %), tube à choc isotherme (6 %), Evrard (énergie à 3 %) : bons tests ; **manquent** : disque en rotation képlérienne (transport de moment par la viscosité artificielle), Kelvin-Helmholtz, explosion de Sedov (indispensable avant toute rétroaction) | [Certain / Supposition] |

---

## 8. Écarts avec l'appli, classés par impact sur le réalisme

### Fort

1. **Pas de rétroaction des étoiles** (`gaz_galaxie.py:17`). Sans elle, la naissance d'étoiles n'est pas auto-régulée :
   grumeaux massifs, flambées, disque de gaz trop mince ou effondré. Remède le plus simple compatible avec l'isotherme :
   dépôt de quantité de mouvement des supernovæ (§ 3.2, niveau 2) ; ou, plus simple encore, équation d'état effective +
   loi de pression (niveau 1). À signaler comme modèle.
2. **Le film de la rencontre n'a pas de gaz du tout** : le gaz n'est branché que dans `stabilite_tir.py`. Les bras ne se
   reforment donc pas dans le film montré (écart 7 de `docs/deuxieme-film.md:45`, toujours ouvert). Avant de le
   brancher : découper par galaxie (simple précision), et prévoir le transitoire de départ.
3. **Poussière de la lueur diffuse grise** (`voie_lactee.frag:64`) : pas de rougissement des bandes sombres ni du bulbe.
   Une ligne à changer ; effet immédiat sur « ce à quoi ça ressemble vraiment ».
4. **Aucune poussière dans Andromède, le Triangle, les Nuages** (`gaia.vert:136`) ni dans les galaxies du film : leurs
   bandes sombres sont absentes. Remède : A_V/pc = 1,65 × 10⁻³ n_H Z/Z☉ tiré du gaz du calcul.
5. **Poussière et régions HII figées dans le présent** : elles ne suivent ni la rotation des bras ni la rencontre. Avec le
   gaz et les étoiles de sorte 5 du film, les deux peuvent être dérivées du calcul (poussière ∝ gaz ; HII ∝ étoiles de
   moins de 10 Ma).
6. **Bilan de gaz ouvert** : ni retour de masse des étoiles (~40 %), ni accrétion (~1 M☉/an et plus) ; le gaz s'épuise en
   6–7 Ga. Sur un film de −3 à +7 Ga, la naissance d'étoiles s'éteindrait artificiellement.

### Moyen

7. **Recette de naissance hybride** (seuil d'EAGLE + efficacité par chute libre) à une résolution où h au seuil dépasse
   l'épaisseur du disque : le taux obtenu dépend du nombre de particules. Choisir une recette cohérente (loi de pression
   de Schaye & Dalla Vecchia 2008, ou seuil ≥ 10 cm⁻³ avec ε = 1 % comme AGORA si la résolution le permet) et **vérifier
   la convergence** à 3,5 M / 10,85 M de particules.
8. **Forme du gaz de départ** : un seul disque exponentiel sans trou central ni anneau moléculaire
   (`modeles_v2.py:43`), contre deux disques troués chez McMillan 2017 ; vitesses de départ d'étoiles froides. La
   répartition radiale de la naissance d'étoiles (pic à 5 kpc, 84 % dans le cercle solaire, Elia 2022) ne peut pas en
   sortir juste.
9. **Coefficients de rougissement des étoiles du modèle** : (0,75 ; 1 ; 1,32) = bandes R/V/B de Johnson, pas les
   primaires de l'écran (~0,89 ; 1,02 ; 1,23) : rougissement ~1,7 fois trop marqué (`gaia.vert:144`).
10. **Diffusion absente** (albédo ~0,6) : bandes sombres trop noires vues de l'extérieur, pas de nébuleuses par
    réflexion.
11. **Carte de poussière mesurée limitée à 1,25 kpc** alors qu'existent 2 kpc (Edenhofer, extension), 3 kpc (Vergely
    2022), ~10 kpc dans le plan sud (DECaPS) et le plan entier à 7 kpc (Zhang, Chen et al. 2026, prépublication) ;
    longueur d'échelle du modèle 2,26 kpc contre 2,90 kpc mesurés récemment.
12. **Étoiles mesurées non ré-éteintes quand la caméra quitte le Soleil** (`voie_lactee.h:8`) : exact vu d'ici, faux vu
    d'ailleurs (une étoile derrière un nuage vu du Soleil reste sombre vue de côté).
13. **Éclat des régions HII supposé** (`HII_ECLAT`) alors qu'il est mesurable (flux radio → photons ionisants) ; régions
    proches (Orion, etc.) non montrées en lueur.
14. **L'appli ne lit pas encore la date de naissance des étoiles nées** (sorte 5) : pas de bleu jeune ni de
    vieillissement individuel dans le nuage du film.
15. **Pas de carte du CO** dans les lumières du ciel (gaz moléculaire, lieux de naissance).
16. **Échantillonnage du lancer de rayons** : 192 pas sur toute la grande grille, donc ~100–235 pc par pas même dans la
    boîte locale mesurée à 15,6 pc.

### Faible

17. Pas de refroidissement/chauffage, pas de gaz chaud, pas de couronne ni de fontaine : invisible en lumière visible,
    important seulement si l'on veut montrer les X ou la physique du gaz elle-même (et pour l'accrétion, point 6).
18. Pas de champ magnétique ni de rayons cosmiques : second ordre pour la forme ; à dire.
19. Pas de noyau actif : négligeable aujourd'hui ; incertain pendant la fusion ; à dire.
20. Pas d'enrichissement chimique : effet de ~0,1–0,2 mag sur la couleur des étoiles nées ; un scalaire Z suffirait.
21. Pas d'aberration, de Doppler ni de temps de trajet : négligeable dans le Groupe local ; mode « observateur rapide »
    facultatif et à part.
22. SPH sans termes grad-h, sans pas de temps individuels, viscosité non prédite dans le saute-mouton, débordement de
    pile silencieux : sans conséquence en isotherme, **bloquants pour un gaz multiphase**.
23. Relevé d'énergie de `stabilite_tir.py` non pertinent avec `--gaz` (énergie dissipée non comptée) : ajouter le travail
    de la pression isotherme (c_s² ln ρ) ou ne plus l'afficher comme contrôle.
24. M☉,V = 4,83 contre 4,81 (Willmer 2018) ; couleur de corps noir « Tanner Helland » au lieu de CIE ; référence et
    valeur de la couleur intégrée B − V = 0,744 à relire (`voie_lactee.h:69`).
25. Plafond de 0,1 mag/pc et hauteur ±406 pc de la boîte locale de poussière (`build_dust.py:28-30`).

### Ordre de travail suggéré [Supposition]

1. Deux lignes de shader : rougissement de la lueur diffuse ; coefficients (0,89 ; 1,02 ; 1,23).
2. Essai de Sedov + dépôt de quantité de mouvement des supernovæ dans `gaz_galaxie.py` ; convergence du taux de
   naissance à deux résolutions ; comparaison au bulletin (taux total **et** profil radial).
3. Gaz de départ en deux disques troués (McMillan 2017), vitesses de gaz (σ ≈ 8 km/s) ; retour de masse des étoiles.
4. Brancher le gaz par galaxie dans la rencontre ; exporter densité de gaz et dates de naissance ; poussière et régions
   HII du rendu dérivées du calcul.
5. Carte de poussière mesurée étendue (2 kpc, puis plan à 7 kpc quand l'article sera publié).
6. Plus tard : gaz multiphase (refroidissement tabulé, thermique stochastique, pas de temps individuels) — le chantier
   « GIZMO/AREPO » de `docs/refonte-simulations-pro.md`.

---

## Sources consultées en ligne aujourd'hui

- Elia et al. 2022, « The Star Formation Rate of the Milky Way as seen by Herschel », arXiv:2211.05573,
  DOI 10.3847/1538-4357/aca27d
- Elia et al. 2025, « Measuring Star Formation Rates in the Milky Way from Hi-GAL 70 µm Observations », arXiv:2501.14471
- Zhang & Green, « Unveiling the Milky Way dust extinction curve in 3D », arXiv:2407.14594
- Gordon et al. 2023, « One Relation for All Wavelengths… », arXiv:2304.01991, DOI 10.3847/1538-4357/accb59
- Richter 2017, « Gas Accretion onto the Milky Way », arXiv:1612.00449
- Licquia, Newman & Bershady 2016, « Does the Milky Way Obey Spiral Galaxy Scaling Relations? », arXiv:1610.05769
- Zheng et al. 2024, « eROSITA narrowband maps at the energies of soft X-ray emission lines », A&A 689, A328,
  arXiv:2401.17310
- Chaikin et al. 2025, « COLIBRE: calibrating subgrid feedback… », arXiv:2509.04067
- Zhang, Chen et al. 2026, « A Face-on View of Interstellar Dust in the Galactic Plane », arXiv:2607.06016
- Documentation `dustmaps` (liste des cartes 3D et 2D) : https://dustmaps.readthedocs.io/en/latest/maps.html
- Edenhofer et al. 2024, arXiv:2308.01295 (référence confirmée ; contenu non relu aujourd'hui au-delà de l'étendue)

Tout le reste des références est cité de mémoire ([Probable]) ou marqué [À vérifier] ; aucun DOI n'a été inventé.
