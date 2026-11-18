# Annexe 5 — Cosmologie, énergie noire et grandes structures

Rapport de recherche (lecture seule, aucun calcul GPU, aucun fichier du dépôt modifié). Date : 18/11/2026.
Labels : [Certain] lu aujourd'hui dans la source ou le code ; [Probable] publié, cité de mémoire ; [Supposition] mon raisonnement ou mon calcul ; [À vérifier] non vérifié.
Les valeurs « calcul ici » viennent d'un petit script CPU (intégration numérique de Friedmann, mêmes hypothèses que `cosmologie.h`).

## Résumé

- **La formule de l'énergie noire locale de l'appli est la bonne** : a_Λ = H0² Ω_Λ (x − x_cm) = (Λc²/3) r, avec K = 3,1118 × 10⁻³ (km/s)²/kpc² pour H0 = 67,4 et Ω_Λ = 0,685 ; potentiel −½ K r² ; c'est exactement l'équation de Peñarrubia et al. 2014 (éq. 2). Les valeurs sont identiques dans les 7 endroits où elles sont recopiées. [Certain]
- **Elle est incluse dans tous les calculs du Groupe local** (calcul.py, rencontre.py, groupe_local_reference.py, groupe_local_clones.py, orbites Gaia CPU et GPU), **sauf dans `stabilite_tir.py`** (galaxie seule, avec ou sans gaz), où elle manque : c'est le seul manquement à la règle « jamais négligée ». [Certain]
- **Coordonnées physiques + terme K r, sans frottement de Hubble : c'est la façon correcte** pour un système isolé. Ce qui manque n'est pas dans Λ mais autour : les marées des voisins (Virgo, Cen A/M83, M81, IC 342) valent chacune 25 à 45 % du terme Λ à l'échelle du Groupe local [Supposition, calcul ici].
- **Les mesures récentes ne valident plus w = −1 sans réserve** : DESI DR2 + CMB + supernovæ préfère w0 > −1, wa < 0 à 2,8–4,2 σ (3,2 σ après la réanalyse DES « Dovekie ») [Certain]. Avec ces valeurs, la poussée locale aujourd'hui vaudrait 0,62 à 0,76 fois celle de Λ [Supposition, calcul ici]. Le film est calculé en w = −1 et l'écran le dit : à garder, à signaler comme modèle.
- **H0 reste en tension** : 67,4 ± 0,5 (Planck), 68,2–68,5 (ACT+Planck+DESI), 70,4 ± 1,9 (CCHP), 73,5 ± 0,8 (H0DN 2026). K varie donc de 3,1 à 3,9 × 10⁻³ selon le camp (+25 %). [Certain pour les H0 ; calcul ici pour K]
- **`cosmologie.h` est juste** (distances contrôlées contre astropy à 0,1 %, âge 13,791 Ga recalculé ici). Trois limites : la loi w0/wa est extrapolée dans l'avenir où elle n'a plus de sens physique ; Ω_k vaut −9 × 10⁻⁵ au lieu de 0 ; les neutrinos sont sans masse.
- **Écart fort côté grandes structures** : les décalages vers le rouge sont ramenés au repère du Groupe local (Yahil 1977) et non à celui du CMB, sans modèle de vitesses propres ; les distances Cosmicflows-4 (échelle H0 ≈ 75) cohabitent avec des distances par décalage en H0 = 67,4 (10 % d'écart) ; les galaxies à distance mesurée ne suivent pas l'expansion quand le temps avance, les autres oui.
- **Le « Grand Attracteur » de l'appli est placé sur l'amas de la Règle** (z = 0,01628) ; l'analyse 2026 de Manticore-Local le met à (l, b) ≈ (313°, 27°), ~41 h⁻¹ Mpc, hors de la Règle, et montre qu'aucun attracteur unique n'explique les 620 km/s du Groupe local. [Certain]
- **Avenir** : horizon des événements à 16,7 milliards d'al aujourd'hui ; a(t) = 1,87 à +10 Ga, 321 à +100 Ga, 5 561 à +150 Ga ; Virgo franchit la distance de l'horizon de de Sitter (17,5 milliards d'al) vers +100 Ga [calcul ici].

---

## 1. Paramètres cosmologiques de référence

### 1.1 Planck 2018 (ΛCDM plat, 6 paramètres)

Source : Planck Collaboration (Aghanim et al.) 2020, « Planck 2018 results. VI. Cosmological parameters », A&A 641, A6, arXiv:1807.06209. Valeurs à 68 %. [Probable : citées de mémoire, non relues aujourd'hui dans la table 2 ; l'appli prend les arrondis du résumé]

| Paramètre | TT,TE,EE+lowE+lensing | + BAO | Appli |
|---|---|---|---|
| H0 (km/s/Mpc) | 67,36 ± 0,54 | 67,66 ± 0,42 | 67,4 (`cosmologie.h:20`) |
| Ω_m | 0,3153 ± 0,0073 | 0,3111 ± 0,0056 | 0,315 (`:21`) |
| Ω_Λ | 0,6847 ± 0,0073 | 0,6889 ± 0,0056 | 0,685 (`:22`) |
| Ω_b h² | 0,02237 ± 0,00015 | 0,02242 ± 0,00014 | absent |
| Ω_c h² | 0,1200 ± 0,0012 | 0,11933 ± 0,00091 | absent |
| Ω_b (déduit) | 0,0493 | 0,0490 | absent |
| σ8 | 0,8111 ± 0,0060 | 0,8102 ± 0,0060 | absent |
| S8 = σ8 √(Ω_m/0,3) | 0,832 ± 0,013 | 0,825 ± 0,011 | absent |
| n_s | 0,9649 ± 0,0042 | 0,9665 ± 0,0038 | absent |
| τ | 0,0544 ± 0,0073 | 0,0561 ± 0,0071 | absent |
| Âge (Ga) | 13,797 ± 0,023 | 13,787 ± 0,020 | 13,791 calculé (`ageGyr`) |
| z de dernière diffusion | 1089,92 ± 0,25 | — | absent |
| Horizon sonore r_drag (Mpc) | 147,09 ± 0,26 | 147,21 ± 0,23 | absent |
| Ω_k (extension) | — | 0,0007 ± 0,0019 | −9,2 × 10⁻⁵ (voir § 6.1) |
| Σm_ν (extension, 95 %) | — | < 0,12 eV | 0 (neutrinos sans masse) |

Température du CMB : T0 = 2,7255 ± 0,0006 K (Fixsen 2009, ApJ 707, 916) [Probable] ; l'appli l'utilise via Ω_r h² = 4,1837 × 10⁻⁵ (`cosmologie.h:16`), avec N_eff = 3,046 (valeur actuelle du modèle standard : 3,044, Bennett et al. 2021 [Probable] ; différence sans effet visible).

L'appli est fidèle à Planck 2018 aux arrondis près. [Certain pour le code]

### 1.2 CMB depuis Planck : ACT DR6 et SPT-3G

| Jeu de données | H0 | σ8 | Autres | Source |
|---|---|---|---|---|
| ACT DR6 + Planck + lentilles + DESI DR1 (« P-ACT-LB ») | 68,22 ± 0,36 | 0,813 ± 0,005 | Ω_b h² = 0,0226 ± 0,0001 ; Ω_c h² = 0,118 ± 0,001 ; n_s = 0,974 ± 0,003 | Louis et al. 2025, arXiv:2503.14452 [Certain, résumé lu] |
| idem + DESI DR2 | 68,43 ± 0,27 | — | accord P-ACT / DESI DR2 à 1,6 σ | idem [Certain] |
| SPT-3G D1 seul | 66,66 ± 0,60 | — | — | Camphuis et al. 2025, arXiv:2506.20707 [Probable, non relu] |

Pas de signe de courbure ni d'excès de lentille dans ACT DR6 [Certain, résumé]. Référence de revue de l'article ACT : [À vérifier].

### 1.3 La constante de Hubble : trois familles de valeurs

| Méthode | H0 (km/s/Mpc) | Source | Confiance |
|---|---|---|---|
| CMB, ΛCDM (Planck 2018) | 67,36 ± 0,54 | A&A 641, A6 | [Probable] |
| CMB + BAO (P-ACT + DESI DR2) | 68,43 ± 0,27 | arXiv:2503.14452 | [Certain] |
| DESI DR2 BAO + nucléosynthèse | 68,51 ± 0,58 | DESI DR2, arXiv:2503.14738 (valeur lue dans un exposé de la collaboration) | [Certain, source secondaire] |
| SH0ES, céphéides + SN Ia | 73,04 ± 1,04 | Riess et al. 2022, ApJL 934, L7, arXiv:2112.04510 | [Certain, cité dans Hoyt et al. 2025] |
| H0 Distance Network (consensus de l'échelle locale) | 73,50 ± 0,81 | H0DN Collaboration 2026, A&A, DOI 10.1051/0004-6361/202557993 | [Certain, communiqué lu] |
| CCHP, TRGB (HST + JWST, 24 SN) | 70,39 ± 1,22 (stat) ± 1,33 (sys) ± 0,70 (σ_SN) | Freedman et al. 2025, arXiv:2408.06153 (ApJ [À vérifier]) | [Certain, résumé lu] |
| CCHP, TRGB JWST seul | 68,81 ± 1,79 ± 1,32 | idem | [Certain] |
| CCHP, JAGB JWST seul | 67,80 ± 2,17 ± 1,64 | idem | [Certain] |
| CCHP 2021 (TRGB) | 69,8 ± 1,8 | Freedman 2021 | [Certain, cité] |
| Cosmicflows-4 | 74,6 ± 0,8 (stat), ± 3 (sys) | Tully et al. 2023, ApJ 944, 94, arXiv:2209.11238 | [Certain, résumé lu] |

Lecture : la tension CMB / échelle locale (≈ 6 km/s/Mpc, > 5 σ pour H0DN) n'est pas résolue ; le CCHP est entre les deux et compatible avec le CMB. Le curseur de l'appli (60 à 80, `interface_bas.h:161`) couvre tout l'intervalle : bien. Le bouton « Valeurs mesurées (Planck 2018) » (`interface_bas.h:167`) pourrait proposer aussi « échelle locale 73,5 » et « DESI DR2 w0wa ».

### 1.4 Énergie noire : DESI DR2 et supernovæ

Paramétrage : w(a) = w0 + wa (1 − a) (Chevallier & Polarski 2001 ; Linder 2003), ρ_DE(a)/ρ_DE(1) = a^(−3(1+w0+wa)) exp(−3 wa (1 − a)). C'est exactement `cosmologie.h:30`. [Certain]

DESI DR2 : DESI Collaboration (Abdul Karim et al.) 2025, « DESI DR2 Results II », arXiv:2503.14738 (Phys. Rev. D [À vérifier]). Plus de 14 millions de galaxies et quasars [Probable].

| Combinaison | w0 | wa | Préférence sur ΛCDM | Confiance |
|---|---|---|---|---|
| DESI DR2 seul, ΛCDM | — | — | Ω_m = 0,2975 ± 0,0086 ; tension de 2,3 σ avec le CMB | [Certain] |
| DESI + CMB | −0,42 ± 0,21 | −1,75 ± 0,58 | 3,1 σ | [Certain, exposé DESI] |
| DESI + CMB + Pantheon+ | −0,838 ± 0,055 | −0,62 (+0,22 / −0,19) | 2,8 σ | [Certain, exposé DESI] |
| DESI + CMB + Union3 | −0,667 ± 0,088 | −1,09 (+0,31 / −0,27) | 3,8 σ | [Certain, exposé DESI] |
| DESI + CMB + DES-SN5YR | −0,752 ± 0,057 | −0,86 (+0,23 / −0,20) | 4,2 σ | [Certain, exposé DESI] |
| DESI DR2 + CMB (Planck+ACT+SPT) + DES-Dovekie | −0,803 ± 0,054 | −0,72 ± 0,21 | **3,2 σ** (au lieu de 4,2) ; rapport bayésien ≈ 5:1, « préférence faible » | [Certain, résumé lu] |

- Réanalyse DES : Popovic et al. 2025, arXiv:2511.07517 (« DES-Dovekie », ~1 600 SN DES + ~200 proches ; Ω_m = 0,330 ± 0,015 en ΛCDM plat, −0,022 par rapport à DES-SN5YR). [Certain]
- Pantheon+ : Brout et al. 2022, ApJ 938, 110 : Ω_m = 0,334 ± 0,018 (ΛCDM plat), w = −0,90 ± 0,14 (wCDM plat, SN seules). [Probable]
- DES-SN5YR d'origine : DES Collaboration 2024, ApJL 973, L14 : Ω_m = 0,352 ± 0,017. [Probable]
- Somme des masses des neutrinos (DESI DR2 + CMB, 95 %) : < 0,064 eV en ΛCDM, < 0,16 eV en w0wa. [Certain]

Ce que cela signifie : aucun seuil de découverte (5 σ) n'est atteint ; le signal dépend de l'échantillon de supernovæ et a baissé après recalibrage. Physiquement, w0 > −1 et wa < 0 décrivent une énergie noire dont la densité a culminé vers z ≈ 0,4–0,5 puis diminue ; le modèle traverse w = −1 dans le passé (« fantôme »), ce qu'un champ scalaire simple ne fait pas. **Statut à afficher : ΛCDM reste le modèle de référence ; w0/wa est une indication à ~3 σ.** [Supposition pour la synthèse]

### 1.5 Amplitude des structures (σ8, S8)

| Mesure | S8 | Source | Confiance |
|---|---|---|---|
| Planck 2018 | 0,832 ± 0,013 | A&A 641, A6 | [Probable] |
| P-ACT-LB | σ8 = 0,813 ± 0,005 | arXiv:2503.14452 | [Certain] |
| DES Y6, 3×2pt, ΛCDM | 0,789 ± 0,012 (Ω_m = 0,333 +0,023/−0,028) ; écart au CMB 2,6 σ sur S8, 1,8 σ dans tout l'espace | DES Collaboration 2026, arXiv:2601.14559 | [Certain, résumé lu] |
| DES Y6, wCDM | w = −1,12 (+0,26/−0,20) | idem | [Certain] |
| KiDS-Legacy | 0,815 (+0,016/−0,021), compatible Planck | Wright et al. 2025, arXiv:2503.19441 | [Probable, non relu] |

La « tension S8 » s'est réduite à ≤ 2,6 σ. Pour l'appli : σ8 ≈ 0,81 est la valeur à utiliser si elle génère un jour des structures (fonction de masse, § 4.5).

---

## 2. Équations de Friedmann, distances, temps

### 2.1 Équations

- (ȧ/a)² = H² = H0² E²(a), avec E²(a) = Ω_r a⁻⁴ + Ω_m a⁻³ + Ω_k a⁻² + Ω_DE f(a) ; f = 1 pour Λ. [Certain : manuels ; c'est `cosmologie.h:28-32`]
- ä/a = −(4πG/3) (ρ + 3p/c²) + Λc²/3 = −H0² [Ω_r a⁻⁴ + ½ Ω_m a⁻³ + ½ (1 + 3w) Ω_DE f(a)]. [Certain]
- Paramètre de décélération aujourd'hui : q0 = Ω_r + ½ Ω_m + ½ (1 + 3 w0) Ω_DE = −0,527 pour les valeurs de l'appli. [calcul ici]
- Début de l'accélération : 1 + z = (2 Ω_Λ/Ω_m)^(1/3) → z = 0,632 (il y a 6,1 Ga environ). Égalité matière–Λ : z = 0,296. [calcul ici]
- Λ = 3 Ω_Λ H0²/c² = 1,091 × 10⁻⁵² m⁻² ; ρ_Λ = 86,4 M☉/kpc³ (5,8 × 10⁻²⁷ kg/m³) ; ρ_crit = 126,1 M☉/kpc³ ; ρ_m = 39,7 M☉/kpc³. [calcul ici]

### 2.2 Distances (Hogg 1999, arXiv:astro-ph/9905116 [Probable])

- Comobile radiale : χ = (c/H0) ∫₀ᶻ dz′/E(z′). Transverse D_M : χ si plat, (c/H0)/√Ω_k sinh(√Ω_k χ H0/c) si ouvert, sin si fermé. C'est `cosmologie.h:46-50`. [Certain]
- Angulaire : D_A = D_M/(1 + z). Lumineuse : D_L = (1 + z) D_M (`galaxies.vert:27`, correct). [Certain]
- Temps de regard en arrière : t_L = (1/H0) ∫₀ᶻ dz′/[(1 + z′) E(z′)]. **Non calculé par l'appli** (elle ne calcule que l'âge total, `cosmologie.h:72-81`).

Valeurs de contrôle (H0 = 67,4, Ω_m = 0,315, Ω_Λ = 0,685, rayonnement compris ; calcul ici, identiques aux références astropy de `essai_cosmologie.cpp:23` à 0,2 Mpc près) :

| z | D comobile (Mpc) | D_L (Mpc) | D_A (Mpc) | Regard en arrière (Ga) |
|---|---|---|---|---|
| 0,1 | 434,1 | 477,5 | 394,6 | 1,350 |
| 0,5 | 1 951,3 | 2 927 | 1 300,9 | 5,210 |
| 1 | 3 401,0 | 6 802 | 1 700,5 | 7,950 |
| 2 | 5 311,3 | 15 934 | 1 770,4 | 10,522 |
| 3 | 6 504,8 | 26 019 | 1 626,2 | 11,653 |
| 1089 (CMB) | 13 864 (45,2 milliards d'al) | — | 12,7 | 13,791 |

Horizon des particules (univers observable) : 14 145 Mpc = 46,1 milliards d'al. [calcul ici]

Sensibilité : avec H0 = 73 (mêmes Ω), toutes les distances diminuent de 7,7 % et l'âge tombe à 12,73 Ga ; avec DESI+CMB+DESY5 (w0 = −0,752, wa = −0,86, H0 ≈ 66,7, Ω_m ≈ 0,319 [Probable pour H0 et Ω_m]), D(z = 0,5) baisse de 1,4 % et l'âge vaut 13,76 Ga. [calcul ici]

### 2.3 Facteur d'échelle et avenir

Solution analytique matière + Λ (plat, sans rayonnement) : a(t) = (Ω_m/Ω_Λ)^(1/3) sinh^(2/3)(1,5 √Ω_Λ H0 t). [Certain : manuels]

| Date | a(t) (appli, w = −1) | DESI+CMB+Pantheon+ (extrapolé) |
|---|---|---|
| −3 Ga (départ du film) | 0,803 | 0,801 |
| +1 Ga | 1,070 | 1,070 |
| +5 Ga | 1,383 | 1,365 |
| +10 Ga | 1,868 | 1,756 |
| +20 Ga | 3,34 | 2,51 |
| +50 Ga | 18,5 | 4,1 |
| +100 Ga | 321 | 5,5 |
| +150 Ga | 5 561 | 6,5 |

[calcul ici ; la colonne de droite extrapole w0wa au-delà de a = 1, voir l'avertissement du § 6.1]

- Asymptote de de Sitter : H∞ = H0 √Ω_Λ = 55,8 km/s/Mpc ; temps de doublement ln 2/H∞ = 12,2 Ga ; rayon de l'horizon de de Sitter c/H∞ = 5 374 Mpc = 17,5 milliards d'al. [calcul ici]
- **Horizon des événements aujourd'hui : 5 114 Mpc = 16,7 milliards d'al** (distance comobile maximale qu'un signal émis maintenant atteindra) ; il correspond à z ≈ 1,9 : toute galaxie vue aujourd'hui au-delà de z ≈ 1,9 est déjà hors d'atteinte. [calcul ici ; même ordre que Loeb 2002, Phys. Rev. D 65, 047301 : z ≈ 1,8 [Probable]]
- **Isolement** : les structures non liées s'éloignent exponentiellement. Virgo (16,5 Mpc) sera à 16,5 × 321 ≈ 5 300 Mpc à +100 Ga, soit la distance de l'horizon de de Sitter : sa lumière sera décalée hors de toute détection [Supposition, calcul ici]. Publications : Nagamine & Loeb 2003 (New Astronomy 8, 439 : la Voie lactée et Andromède fusionnées restent seules en ~100 Ga) ; Busha et al. 2003 (ApJ 596, 713 : les halos gardent une masse finie, critère de liaison) ; Krauss & Scherrer 2007 (Gen. Rel. Grav. 39, 1545 : dans ~100 Ga, plus aucune galaxie extérieure observable) ; Adams & Laughlin 1997 (Rev. Mod. Phys. 69, 337). [Probable, non relus]
- Analyse 2026 avec simulation contrainte : en poussant jusqu'à a = 10 (et vérifié à a = 100), l'énergie noire arrête la formation des structures ; le voisinage du Groupe local ne dérive que de 3 ± 1 h⁻¹ Mpc comobiles vers Virgo et **ne s'y lie jamais** (Stiskalek et al. 2026, arXiv:2601.08524). [Certain, extrait lu]
- Le nom « Milkomeda » (Cox & Loeb 2008, MNRAS 386, 461 [Probable]) désigne le produit de la fusion. La probabilité de fusion est le sujet d'une autre mission ; je note seulement que `resultats/ensemble_unifie.json` donne 95,9 % avec énergie noire et 96,4 % sans [Certain, lu], soit un effet de Λ de −0,5 point.

---

## 3. Énergie noire à l'échelle du Groupe local

### 3.1 L'équation

Limite newtonienne d'une masse dans un univers avec Λ (métrique de Schwarzschild–de Sitter en champ faible), en coordonnées physiques :

**r̈ = −G M/r² + (Λc²/3) r = −G M/r² + Ω_Λ H0² r**

- C'est l'équation 2 de Peñarrubia, Ma, Walker & McConnachie 2014, « A dynamical model of the local cosmic expansion », MNRAS 443, 2204, arXiv:1405.0306. [Certain, lu aujourd'hui]
- Cas général (énergie noire homogène de paramètre w) : terme = −(4πG/3)(ρ_DE + 3 p_DE/c²) r = −½ (1 + 3w) Ω_DE(a) H0² r. Pour w = −1 : + Ω_Λ H0² r. Répulsif tant que w < −1/3. [Certain : dérive de l'équation d'accélération ; suppose une énergie noire qui ne s'agglomère pas]
- Potentiel : φ_Λ = −½ Ω_Λ H0² r². Équivalent à une « densité de masse gravitationnelle effective » −2 ρ_Λ = −173 M☉/kpc³ uniforme. [Certain / calcul ici]

Valeur : K = Ω_Λ H0² = 0,685 × (0,0674 km/s/kpc)² = **3,1118 × 10⁻³ (km/s)²/kpc²**. [calcul ici ; l'appli écrit 0,00311179, identique]

### 3.2 Ordres de grandeur

| Lieu | a_Λ = K r ((km/s)²/kpc) | Gravité | Rapport |
|---|---|---|---|
| Soleil (8,2 kpc du centre) | 0,026 | ≈ 6 900 (V²/R, 238 km/s) | 4 × 10⁻⁶ |
| Grand Nuage (50 kpc, MW 10¹² M☉) | 0,156 | 1 720 | 0,009 % |
| Bord du halo (250 kpc, 1,3 × 10¹² M☉) | 0,78 | 89 | 0,9 % |
| Andromède (770 kpc), M = 2 × 10¹² M☉ | 2,40 | 14,5 | 16,5 % |
| idem, M = 3,2 × 10¹² M☉ | 2,40 | 23,2 | 10,3 % |
| idem, M = 5 × 10¹² M☉ | 2,40 | 36,3 | 6,6 % |

[calcul ici ; `energie_noire.py:9-10` annonce « environ 15 % » pour 2 × 10¹² M☉ : cohérent]

Échelles de temps : T_Λ = 2π/(c√Λ) = 63,6 Ga (Benisty, Davis & Evans 2023 donnent 63,2 Ga [Certain, résumé lu]) ; temps caractéristique 1/√K = 17,5 Ga. Λ compte quand la période képlérienne approche T_Λ : c'est le cas du couple Voie lactée–Andromède (période ≈ 15–20 Ga), pas des satellites. [Certain pour le critère, résumé de Benisty et al.]

### 3.3 Rayon de gravité nulle

R_ZG = (G M / (Ω_Λ H0²))^(1/3) = (3 G M/(Λ c²))^(1/3) : rayon où la poussée de Λ égale l'attraction d'une masse ponctuelle M. [Certain : définition, Chernin et al.]

| M (M☉) | R_ZG, H0 = 67,4 | R_ZG, H0 = 73 |
|---|---|---|
| 2 × 10¹² | 1,40 Mpc | 1,33 Mpc |
| 3 × 10¹² | 1,61 Mpc | 1,52 Mpc |
| 4 × 10¹² | 1,77 Mpc | 1,68 Mpc |
| 5 × 10¹² | 1,91 Mpc | 1,81 Mpc |

[calcul ici]. La fourchette publiée « 1,2–1,5 Mpc » correspond aux masses de 1,3 à 2,5 × 10¹² M☉ et à l'ancienne cosmologie (H0 ≈ 72, Ω_Λ ≈ 0,73) de Chernin et al. 2009 (« Local dark matter and dark energy as estimated on a scale of ~1 Mpc in a self-consistent way », A&A 507, 1271, DOI 10.1051/0004-6361/200912762 [Certain pour la référence, Probable pour les chiffres]) et Chernin et al. 2009, arXiv:0902.3871 (« Dark energy and the mass of the Local Group »).

À ne pas confondre avec la **surface de vitesse nulle** (rayon de retournement, où la vitesse radiale moyenne s'annule) : R0 = 0,96 ± 0,03 Mpc observé (Karachentsev et al. 2009, MNRAS 393, 1265 [Probable]) ; ≈ 1 Mpc observé et 1,42 Mpc dans les modèles N-corps de Peñarrubia et al. 2014 [Certain, extrait lu]. Au-delà de R_ZG, une galaxie isolée n'est plus liée au Groupe local : c'est la frontière physique du « Milkomeda » futur.

### 3.4 Résultats publiés

| Résultat | Valeur | Source | Confiance |
|---|---|---|---|
| Masse du Groupe local (flot de Hubble local + Λ) | 2,3 ± 0,7 × 10¹² M☉ | Peñarrubia et al. 2014 | [Certain] |
| Rapport de masse Voie lactée / Andromède | 0,54 (+0,23/−0,17) | idem | [Certain] |
| H0 local déduit | 67 ± 5 km/s/Mpc | idem | [Certain] |
| Ω_Λ déduit des seules données locales | 0,54 (+0,32/−0,35) : faiblement contraint | idem | [Certain] |
| Effet de Λ sur la masse par l'argument du temps | ≈ +10 % (retirer Λ abaisse la masse d'une fraction ~0,1) | idem | [Certain] |
| idem | +13 % | Partridge, Lahav & Hoffman 2013, MNRAS 436, L45, arXiv:1308.0970 | [Certain d'après `docs/refonte-simulations-pro.md:144`, non relu ici] |
| Gain de vitesse dû à Λ jusqu'à 3 Mpc | ≤ ~46 km/s | Peñarrubia et al. 2014 | [Certain] |
| Dispersion autour du flot local | σ_H = 50 ± 4 km/s (valeur lue par extraction automatique du PDF) ; souvent citée 25–30 km/s dans 3 Mpc (Karachentsev 2009) | idem | [À vérifier pour le chiffre exact] |
| Borne sur Λ par la dynamique du Groupe local | Λ < 5,44 Λ_Planck ; projeté : (1,67 ± 0,79) Λ_Planck | Benisty, Davis & Evans 2023, ApJL, DOI 10.3847/2041-8213/ace90b, arXiv:2306.14963 | [Certain, résumé lu] |
| « La masse du Groupe local : probablement pas plus que la somme de ses parties » | titre | Sawala et al. 2023, arXiv:2210.07250 | [Certain pour le titre] |

« Courant de Hubble local froid » : le flot autour du Groupe local (1–3 Mpc) est régulier, avec une faible dispersion. Chernin et coll. l'attribuent à la domination de Λ au-delà de R_ZG ; les simulations contraintes récentes l'attribuent plutôt à la géométrie (matière concentrée dans le Feuillet local, vides de part et d'autre) [Probable ; Wempe et al. 2024, A&A 691, A348, et suite 2025–2026 : références à vérifier]. Les deux effets coexistent : Λ n'est pas la seule cause.

### 3.5 La bonne façon de l'inclure dans un N-corps

**Coordonnées physiques, système isolé (ce que fait l'appli)** :
r̈_i = Σ_j G m_j (r_j − r_i)/|…|³ + Ω_Λ H0² (r_i − r_0)

- Le choix du centre r_0 ne change pas les mouvements relatifs : le déplacer ajoute la même accélération constante à toutes les particules. Prendre le centre de masse garde la quantité de mouvement totale nulle (Σ m a_Λ = 0). [Certain : algèbre]
- **Ne pas ajouter de frottement de Hubble** (−2H v) : il n'existe qu'en coordonnées comobiles. [Certain]
- **Ne pas faire grossir les positions avec a(t)** : l'expansion locale est le résultat du calcul, pas une entrée. [Certain]
- Énergie conservée : E = T + W − ½ K Σ m |r − r_0|² (K constant si w = −1). [Certain]
- Si w ≠ −1 : K(t) = −½ (1 + 3 w(a)) Ω_DE(a) H0², dépend du temps ; l'énergie n'est plus conservée. [Certain]

**Coordonnées comobiles, boîte périodique (GADGET-4, AREPO, SWIFT, RAMSES)** :
x = r/a ; ẍ + 2H ẋ = −∇_x φ/a² ; ∇²_x φ = 4πG a² (ρ − ρ̄). Λ n'apparaît que dans H(a). [Certain : Peebles 1980 ; Springel 2005, MNRAS 364, 1105]

**Équivalence** : en posant r = a x, r̈ = (ä/a) r − ∇_r φ_pec, et ä/a = −(4πG/3) ρ̄_m + Λc²/3. Le terme −(4πG/3) ρ̄_m r est la gravité newtonienne du fond homogène ; ajouté au potentiel particulier, il redonne la gravité de **toute** la matière. Les deux descriptions sont donc identiques à condition que le calcul isolé contienne toute la matière de la région. [Certain : dérivation standard]

Ce que le calcul isolé de l'appli laisse de côté [Supposition, calculs ici] :

| Terme omis | Valeur | Comparé à K = 3,11 × 10⁻³ |
|---|---|---|
| Matière moyenne du fond dans 1 Mpc | 1,7 × 10¹¹ M☉ (ρ_m = 39,7 M☉/kpc³) | ~5 % de la masse du Groupe local ; négligeable devant l'incertitude de masse |
| Marée de Virgo (6 × 10¹⁴ M☉ à 16,5 Mpc), 2GM/d³ | 1,1 × 10⁻³ | 37 % |
| Marée de Cen A / M83 (~8 × 10¹² M☉ à 3,7 Mpc) | 1,4 × 10⁻³ | 44 % |
| Marée de M81 (~5 × 10¹² M☉ à 3,6 Mpc) | 0,9 × 10⁻³ | 30 % |
| Marée d'IC 342 / Maffei (~3 × 10¹² M☉ à 3,3 Mpc) | 0,7 × 10⁻³ | 23 % |
| Marée du Grand Attracteur (~5 × 10¹⁵ M☉ à 60 Mpc) | 0,2 × 10⁻³ | 6 % |

Les masses des groupes voisins sont des ordres de grandeur [À vérifier]. Conclusion : **le champ de marée des voisins est du même ordre que le terme Λ** (étirement le long de l'axe vers chaque voisin, compression perpendiculaire, de signe et de direction variables, alors que Λ est isotrope). Si l'on tient à 10 % près la dynamique à 770 kpc, il est cohérent d'inclure les deux. C'est la raison d'être des simulations contraintes (§ 4.4).

---

## 4. Grandes structures

### 4.1 Catalogues

| Catalogue | Contenu | Source | Dans l'appli |
|---|---|---|---|
| 2MRS | 43 533 galaxies, K_s < 11,75, tout le ciel (|b| > 5°), complet à 97,6 % | Huchra et al. 2012, ApJS 199, 26 [Probable] | oui (`fetch_all.py:50`) |
| 6dFGS, 2dFGRS, SDSS, DR16Q | décalages spectroscopiques | — | oui (`build_data2.py:158-178`) |
| DESI DR1 | ~18,7 millions d'objets publics (mars 2025) [Probable] | DESI Collaboration 2025 | oui (« 18 M de galaxies ») |
| DESI DR2 | > 14 millions de décalages utilisés pour le BAO ; catalogue public non encore diffusé à ma connaissance | arXiv:2503.14738 | non [À vérifier] |
| Cosmicflows-4 | 55 877 galaxies, 38 065 groupes, 8 méthodes de distance ; H0 = 74,6 ± 0,8 ± 3 | Tully et al. 2023, ApJ 944, 94, DOI 10.3847/1538-4357/ac94d8 [Certain] | oui (`galaxies_cf4.py`, 55 637 galaxies nommées ; grilles `cf4grid`) |
| 2M++ | 69 160 galaxies, base de BORG / Manticore | Lavaux & Hudson 2011, MNRAS 416, 2840 [Probable] | non |

### 4.2 Champ de vitesse, Laniakea, Grand Attracteur

- Laniakea : bassin d'attraction contenant la Voie lactée, ~160 Mpc de diamètre, ~10¹⁷ M☉ (Tully, Courtois, Hoffman & Pomarède 2014, Nature 513, 71). [Probable]
- Avec Cosmicflows-4 : Dupuy & Courtois 2023, « Dynamic cosmography of the local Universe: Laniakea and five more watershed superclusters », arXiv:2305.02339 (A&A [À vérifier]). [Certain pour le titre]
- Valade et al. 2024, « Identification of basins of attraction in the local Universe », Nature Astronomy 8, 1610, arXiv:2409.17261 : **légère préférence probabiliste pour que Laniakea fasse partie du bassin de Shapley**, bien plus vaste ; le plus grand bassin retrouvé est celui du Grand Mur de Sloan, 15,5 × 10⁶ (h⁻¹ Mpc)³, plus du double de celui de Shapley. [Certain, résumé lu]
- Stiskalek, Desmond, McAlpine, Lavaux, Jasche & Hudson 2026, « Revisiting the Great Attractor », arXiv:2601.08524 [Certain, extrait lu] :
  - point de convergence des lignes de courant (lissage 3 h⁻¹ Mpc) à (l, b) ≈ (313°, 27°), ~41 h⁻¹ Mpc, près d'Abell 3565 ; bassin de 10^(16,4 ± 0,1) h⁻¹ M☉, **qui exclut l'amas de la Règle (Norma)** ;
  - position classique (Lynden-Bell et al. 1988) : (307°, 9°), 43,5 h⁻¹ Mpc ;
  - le résultat dépend du lissage : sans lissage la ligne de courant de la Voie lactée finit dans Virgo ; à 2–4 h⁻¹ Mpc au Grand Attracteur ; à 8 h⁻¹ Mpc près de Shapley ;
  - Virgo fournit ~200 km/s (au plus un tiers) de la vitesse du Groupe local ; aucun attracteur unique ne l'explique ;
  - la matière dans 155 h⁻¹ Mpc ne rend que 72 ± 9 % de l'amplitude du dipôle, avec 38 ± 10° d'écart de direction.
- L'appli place « Grand Attracteur » à RA 243,59°, Dec −60,87°, z = 0,01628 (`build_data.py:193`), c'est-à-dire sur l'amas de la Règle (ACO 3627). **Écart d'étiquette** : à nommer « amas de la Règle, dans la région du Grand Attracteur », et à compléter par le point de convergence ci-dessus. [Certain pour le code]

### 4.3 Mouvement par rapport au CMB

Source : Planck Collaboration 2020, « Planck 2018 results. I », A&A 641, A1, table 3. [Certain, table lue aujourd'hui]

| Vitesse | Module (km/s) | l (°) | b (°) |
|---|---|---|---|
| Soleil – CMB | 369,82 ± 0,11 | 264,021 ± 0,011 | 48,253 ± 0,005 |
| Soleil – LSR | 17,9 ± 2,0 | 48 ± 7 | 23 ± 4 |
| LSR – centre galactique | 239 ± 5 | 90 | 0 |
| Centre galactique – CMB | 565 ± 5 | 265,76 ± 0,20 | 28,38 ± 0,28 |
| Soleil – Groupe local | 299 ± 15 | 98,4 ± 3,6 | −5,9 ± 3,0 |
| **Groupe local – CMB** | **620 ± 15** | 271,9 ± 2,0 | 29,6 ± 1,4 |

Le chiffre « 627 km/s » de la mission est l'ancienne valeur 627 ± 22 km/s vers (276° ± 3°, 30° ± 3°) de Kogut et al. 1993 (ApJ 419, 1) [Probable]. **Valeur à retenir : 620 ± 15 km/s.** L'incertitude vient du mouvement du Soleil dans le Groupe local, pas du CMB.

L'appli ramène les décalages au repère du Groupe local avec le vecteur de Yahil, Tammann & Sandage 1977 (−79, +296, −36 km/s en galactique, `build_data2.py:139-141`) [Certain]. Voir l'écart au § 6.3.

### 4.4 Simulations contraintes de l'Univers local

| Projet | Méthode et contraintes | Ce qu'on y trouve | Source | Confiance |
|---|---|---|---|---|
| CLUES | conditions initiales contraintes par les vitesses propres (Cosmicflows), filtre de Wiener + réalisations contraintes | Groupes locaux simulés dans le bon environnement (Virgo, Feuillet local) | Gottlöber, Hoffman & Yepes 2010, arXiv:1005.2687 ; Carlesi et al. 2016, MNRAS 458, 900 | [Probable] |
| HESTIA | CLUES + hydrodynamique AREPO / modèle Auriga, contraintes CF2 | paires Voie lactée–Andromède avec gaz, satellites, à haute résolution | Libeskind et al. 2020, MNRAS 498, 2968 | [Probable] |
| SIBELIUS-DARK | conditions initiales BORG (2M++), rayon 200 Mpc | amas locaux à leur place, Groupe local inséré | McAlpine et al. 2022, MNRAS 512, 5823 ; Sawala et al. 2022, MNRAS 509, 1432 | [Probable] |
| Manticore-Local | inférence bayésienne au niveau du champ (BORG) sur 2M++, ensemble de réalisations a posteriori | 14 amas retrouvés à moins de 1° de leur position, à 2–4 σ ; meilleur champ de vitesses propres sur 5 jeux de données ; pas de grand vide local | McAlpine, Jasche, Ata, Lavaux, Stiskalek, Frenk & Jenkins 2025, arXiv:2505.10682 | [Certain, résumé lu] |
| Catalogue d'amas Manticore-Local | carte a posteriori des structures massives | — | arXiv:2510.16574 | [Certain pour le titre] |
| Groupe local contraint | inférence au niveau du champ sur les masses, positions, vitesses de la Voie lactée et d'Andromède et le flot à < 4 Mpc | histoires compatibles avec les mesures d'aujourd'hui | Wempe et al. 2024, A&A 691, A348 | [À vérifier] |

Taille de boîte, résolution et nombre de réalisations de Manticore-Local : non lus [À vérifier].

Intérêt pour l'appli : ces produits donnent (a) le champ de densité et de vitesse autour du Groupe local, donc le champ de marée manquant du § 3.5 ; (b) une vraie distribution de matière noire à grande échelle à montrer, signalée comme modèle. Les champs CF4 déjà téléchargés (`cf4grid`, 134 Mo) permettent déjà d'estimer la marée.

### 4.5 Croissance des structures et fonction de masse

- Perturbations linéaires : δ̈ + 2H δ̇ = 4πG ρ̄_m δ. Λ n'entre que par H : elle freine la croissance. [Certain]
- Taux de croissance f = d ln D/d ln a ≈ Ω_m(a)^0,55 (Linder 2005, Phys. Rev. D 72, 043529 [Probable]) ; aujourd'hui f ≈ 0,315^0,55 = 0,53. [calcul ici]
- Vitesse propre linéaire : v = (2 f / (3 H Ω_m)) g, avec g l'accélération particulière ; forme usuelle v = (H0 f / 4π) ∫ δ(r′) (r′ − r)/|r′ − r|³ d³r′ (Peebles 1980). [Certain]
- Effondrement sphérique : seuil linéaire δ_c ≈ 1,686 ; surdensité virielle Δ_c = 18π² + 82 x − 39 x², x = Ω_m(z) − 1 (Bryan & Norman 1998, ApJ 495, 80) → Δ_c ≈ 103 fois la densité critique à z = 0 pour Ω_m = 0,315. [formule Probable ; calcul ici]
- Fonction de masse : dn/dM = f(σ) (ρ̄_m/M) d ln σ⁻¹/dM ; Press & Schechter 1974 ; Sheth & Tormen 1999 (MNRAS 308, 119) ; Tinker et al. 2008 (ApJ 688, 709), référence usuelle calibrée sur simulations. [Probable]
- Fond de Λ et halos : dans l'avenir, la croissance s'arrête (D(a) tend vers une constante) ; la masse des halos se fige (Busha et al. 2003, 2005 [Probable] ; confirmé pour le voisinage local par Stiskalek et al. 2026 [Certain]).

---

## 5. Fond diffus cosmologique

- Corps noir à T0 = 2,7255 ± 0,0006 K (Fixsen 2009) [Probable] ; pic à 160,2 GHz (1,06 mm en fréquence) [calcul standard].
- Dipôle : amplitude 3 362,08 ± 0,99 µK [Probable] ; cohérent avec T0 v/c = 2,7255 × 369,82/299 792 = 3,362 mK [calcul ici]. Direction (l, b) = (264,021°, 48,253°) [Certain, § 4.3]. C'est un effet de notre mouvement, pas une propriété du fond.
- Anisotropies primaires : écart-type ≈ 70–110 µK selon la résolution ; premier pic acoustique à l ≈ 220 (≈ 0,8°), soit l'horizon sonore r* ≈ 144 Mpc vu à D_M ≈ 13,9 Gpc. [Probable]
- Surface de dernière diffusion : z* = 1089,9, soit ~372 000 ans après le Big Bang (l'appli écrit « 380 000 ans », arrondi courant, `ciel_bandes.py:45`) ; distance comobile 13 864 Mpc = 45,2 milliards d'al [calcul ici].
- Dans l'appli : carte Planck 2018 SMICA NSIDE 2048, 5′ (`pipeline/natif/ciel_bandes.py:43-50`) et, pour la page, WMAP 9 ans ILC (`build_data2.py:198-210`). [Certain]

Rendu conseillé [Supposition] :
- la carte SMICA est livrée **sans monopôle ni dipôle** : à dire à l'écran ; offrir un mode « ce qu'un instrument voit vraiment » = monopôle (uniforme) + dipôle 3,36 mK + anisotropies ×1, où les anisotropies sont invisibles (1 part sur 30 000), et un mode « anisotropies seules, ±300 µK » ;
- la bande du plan galactique de SMICA est reconstruite (masque d'inpainting) : la signaler comme non mesurée ;
- en 3D, placer la carte sur la sphère de rayon comobile D_M(z*) calculé par `cosmologie.h` (elle bouge donc avec les curseurs), et non à l'infini ; `kGalaxyZMax = 7` (`galaxies.h:9`) ne couvre pas z = 1090 : il faut un appel dédié.

---

## 6. Vérification du code

### 6.1 `natif/src/cosmologie.h` et `essai_cosmologie.cpp`

| Point | Constat | Verdict |
|---|---|---|
| E(z) (`:28-32`) | rayonnement, matière, courbure, énergie noire CPL : formule exacte | juste [Certain] |
| Distance transverse (`:37-53`) | Simpson en ln(1 + z), sinh/sin selon la courbure | juste ; recalculé ici : 434,1 / 1 951,3 / 3 401,0 / 5 311,3 / 6 504,8 Mpc, références de l'essai à 0,2 Mpc près [Certain] |
| Âge (`:72-81`) | 13,791 Ga recalculé ici ; l'essai attend 13,79 ± 0,05 | juste [Certain] |
| a(t) (`:57-69`) | RK4, pas de 2 Ma ; recalculé ici : a(+10 Ga) = 1,868, a(−3 Ga) = 0,803 | juste pour w = −1 [Certain] |
| Ω_k (`:26`) | 1 − 0,315 − 0,685 − Ω_r = −9,2 × 10⁻⁵ : l'univers par défaut est très légèrement **fermé** et passe par la branche `sin` | effet < 10⁻⁴, mais contraire à « plat » ; Planck plat impose Ω_Λ = 1 − Ω_m − Ω_r [Certain] |
| CPL dans l'avenir (`:30` utilisé par `:59`) | pour a > 1, w = w0 + wa (1 − a) croît sans limite : avec les valeurs DESI, w passe au-dessus de −1/3 vers a ≈ 1,5–1,8 puis devient positif ; l'expansion extrapolée ralentit (a = 5,5 à +100 Ga au lieu de 321) | **extrapolation hors du domaine de validité** de l'ajustement (z < 2,5) : à signaler à l'écran comme non physique, ou borner w [Supposition forte] |
| Neutrinos | 3,046 sans masse ; Planck suppose Σm_ν = 0,06 eV (déjà dans Ω_m) | effet < 0,05 % sur les distances à z < 7 [Supposition] |
| Temps de regard en arrière, D_L, D_A | non exposés (seul D_L est refait dans le shader) | manque d'affichage |
| `essai_cosmologie.cpp` | contrôle les distances, l'âge, le sens de variation avec w0 | ne contrôle ni `scaleFactorAt`, ni wa ≠ 0, ni la courbure ; à compléter (ex. solution analytique en sinh^(2/3), § 2.3) |

### 6.2 Énergie noire dans les calculs de gravité

| Fichier:ligne | Ce qui est fait | Verdict |
|---|---|---|
| `film-3/pipeline/fusion/energie_noire.py:20-23` | K = (H0/1000)² Ω_Λ = 3,1118 × 10⁻³ | valeur et unité justes [Certain] |
| `energie_noire.py:26-35` | a = K (x − centre) ; φ = −½ K r² | formule juste [Certain] |
| `energie_noire.py:9-12` | « 15 % à 770 kpc pour 2 × 10¹² M☉ » ; « 10 à 15 % sur la masse » | cohérent (16,5 % calculé ici ; 10 % Peñarrubia, 13 % Partridge) |
| `gravite_gpu.py` (tout le fichier) | **Λ n'y entre pas** : le module ne rend que la gravité mutuelle ; Λ est ajoutée par l'appelant, en double précision | correct ; mais tout nouvel appelant peut l'oublier (voir `stabilite_tir.py`) [Certain] |
| `calcul.py:118-120, 143-145` | acc + K × pos, **centre = origine** (pas le centre de masse) ; φ + 2 φ_Λ pour que ½ Σ m φ compte φ_Λ une fois | dynamique relative juste ; l'énergie est bien conservée (potentiel fixe) ; le centre de masse subit une accélération K × x_cm si x_cm ≠ 0 : dérive d'ensemble sans effet physique, mais différente de `rencontre.py` [Certain] |
| `rencontre.py:119-130` | centre de masse des particules massives (traceurs exclus), recalculé à chaque pas ; énergie avec −½ K Σ m d² | juste [Certain] |
| `groupe_local_reference.py:138-145` | K (pos − cm) par scénario, masses nulles exclues | juste [Certain] |
| `groupe_local_clones.py:95-102` | idem | juste [Certain] |
| **`stabilite_tir.py:147-155`** | gravité + pression du gaz + guide de barre : **aucun terme Λ** ; énergie sans φ_Λ (`:162`) | **manque** ; effet 4 × 10⁻⁶ dans le disque, 0,9 % au bord du halo à 250 kpc ; contraire à la règle « jamais négligée » [Certain] |
| `gaz_galaxie.py`, `gaz_gpu.py` | accélérations de pression seulement | normal ; Λ doit venir de l'appelant, sur le gaz comme sur le reste |
| `univers/natif/physique/galaxie_orbites.h:48, 67-68, 83, 94` | K = 0,0674² × 0,685 ; Ω² = (dΦ/dR − K R)/R ; κ² = d²Φ/dR² − K + 3 Ω² ; ν² − K ; a += K r ; φ −= ½ K r² | tout est juste, signes compris [Certain, relu] |
| `natif/shaders/orbites_pas.comp:32`, `gaia_acc.glsl:4` | OP_KL = 0,00311179 ; contrôlé par `essai_orbite.cpp:75` | juste [Certain] |
| `natif/physique/constantes_univers.h:14-17` | kH0, kOmegaLambda, kKLambda | définis, **non utilisés ailleurs dans `natif/`** d'après ma recherche [Certain pour la recherche] |
| `natif/physique/nbody_noyau.h` (système solaire) | pas de terme Λ | à 1 ua, a_Λ/a_Soleil ≈ 10⁻²² : aucun effet mesurable ; à dire dans la documentation plutôt qu'à calculer [Supposition] |
| `pipeline/constantes/univers.json:37-46` | H0, Ω_m, Ω_Λ, w0, wa, K_lambda = 0,00311179 | cohérent ; statut « mesuré » discutable pour w0 = −1, wa = 0 (c'est une hypothèse de modèle) |

Bilan : formule, signe, unité et valeur sont corrects partout où le terme est présent. Les sept copies de la valeur (cosmologie.h, galaxie_orbites.h, constantes_univers.h, deux shaders, energie_noire.py, univers.json) sont identiques aujourd'hui ; seule une partie est protégée par un essai.

Limites de modèle à afficher [Supposition] :
1. K constant suppose w = −1. Avec DESI+CMB+Pantheon+ la poussée locale vaudrait 0,76 K aujourd'hui, 1,01 K à a = 0,8 (−3 Ga), 0,20 K à a = 1,5 ; avec DESI+CMB+DESY5 : 0,62 K aujourd'hui, ~0 à a = 1,5. L'effet total de Λ sur la date de fusion étant de ~0,1 Ga (`docs/table-unique.md:49`), l'incertitude sur w déplace cette date de quelques dizaines de millions d'années au plus : inférieur aux autres incertitudes, mais à dire.
2. H0 = 73,5 au lieu de 67,4 donnerait K plus grand de 17 % à Ω_Λ égal, de 25 % si Ω_m h² est gardé (Ω_Λ ≈ 0,73).
3. Les curseurs de cosmologie déplacent les galaxies lointaines mais pas le film (déjà dit dans `energie_noire.py:15`).

### 6.3 `natif/src/galaxies.h`, `galaxies.vert` et pipeline

| Point | Constat | Impact |
|---|---|---|
| Distance d'après z (`galaxies.h:158-163`, `galaxies.vert:16-19`) | table de 257 valeurs en ln(1 + z), interpolation linéaire | juste ; erreur d'interpolation négligeable [Certain] |
| Expansion dans le temps (`fenetre.cpp:710-711`, `galaxies.h:161`) | toutes les distances par décalage sont multipliées par a(t) | juste pour des galaxies dans le flot de Hubble ; **faux pour les galaxies liées** (amas : Virgo, Coma ne grossissent pas ; ici leurs « doigts de Dieu » s'étirent avec a) [Certain pour le code, Supposition pour le jugement] |
| Galaxies à distance mesurée (`galaxies_formes.h:62`) | `r.d > 0 ? r.d : cat.distanceLy(r.z)` : celles qui ont une distance CF4 **ne suivent pas a(t)**, les autres oui | incohérence quand le temps avance : à +10 Ga (a = 1,87) les deux populations se séparent d'un facteur ~1,9 [Probable : je n'ai pas vu d'autre mise à l'échelle] |
| Échelle des distances CF4 (`galaxies_cf4.py:12`) | distances publiées sur l'échelle H0 ≈ 75 ; les distances par décalage utilisent H0 = 67,4 | **10 % d'écart systématique** entre les deux familles de points dans le même volume [Certain pour le code] |
| Repère des décalages (`build_data2.py:139-149, 157`) | ramenés au repère du Groupe local (Yahil 1977), coupe à 700 km/s ; pas de correction vers le CMB, pas de modèle de vitesses propres | la distance d'expansion se lit dans le repère du CMB ; le Groupe local s'y déplace à 620 km/s : jusqu'à ±9 Mpc d'erreur de distance selon la direction, constante en valeur absolue, donc grave à < 100 Mpc (structure de Laniakea, Virgo, Grand Attracteur), négligeable au-delà de z ≈ 0,1 [Certain pour le code ; Probable pour le chiffrage] |
| Vitesses propres | « doigts de Dieu » non corrigés (déjà noté dans `docs/audit-precision.md:24`) | connu |
| Luminosité (`galaxies.vert:27`) | D_L = D_M (1 + z) | juste ; mais comme la table est multipliée par a(t), D_L l'est aussi, ce qui n'a pas de sens observationnel hors d'aujourd'hui [Supposition, mineur] |
| `kGalaxyZMax = 7` (`galaxies.h:9`) | borne de la table | suffisant pour les relevés ; pas pour le CMB |
| Lumière et temps | les galaxies sont placées à leur distance comobile **d'aujourd'hui** mais montrées telles qu'on les voit (passé) | choix légitime, à dire à l'écran ; le temps de regard en arrière n'est pas calculé |

---

## 7. Écarts avec l'appli, classés par impact sur le réalisme

### Fort

1. **Repère des décalages vers le rouge et vitesses propres** (`build_data2.py:139-157`) : repère du Groupe local sans retour au CMB ni modèle de flot. Correction : passer au repère du CMB (vecteur Planck 2018 : 369,82 km/s vers l, b = 264,021°, 48,253°) puis soustraire un champ de vitesses propres reconstruit (grilles CF4 déjà téléchargées, ou Manticore-Local / Carrick et al. 2015). Signaler comme modèle.
2. **Deux échelles de distance dans le même volume** : CF4 (H0 ≈ 75) contre décalage (H0 = 67,4), 10 % d'écart (`galaxies_cf4.py:12` contre `cosmologie.h:20`). Choisir une échelle par défaut et recaler l'autre, ou afficher l'écart ; c'est la tension de Hubble rendue visible, à expliquer plutôt qu'à subir.
3. **Expansion appliquée de façon incohérente dans le temps** : points par décalage multipliés par a(t), galaxies à distance mesurée fixes (`galaxies_formes.h:62`), structures liées étirées. Correction : appliquer a(t) à toutes les galaxies hors du Groupe local, et laisser fixes (ou modélisées) celles des amas liés.
4. **Champ de marée extérieur absent du calcul du Groupe local** : chaque voisin (Virgo, Cen A/M83, M81, IC 342) pèse 25 à 45 % du terme Λ. Ajouter un tenseur de marée externe lentement variable (masses ponctuelles des groupes à < 20 Mpc, ou champ CF4), signalé comme modèle. [Supposition, à confirmer par un essai à peu de particules]

### Moyen

5. **`stabilite_tir.py:147-155` : énergie noire absente** (accélération et énergie). Ajouter `EN.acceleration(pos, cm)` et le terme d'énergie ; mieux : faire porter Λ par une fonction commune « gravité + Λ » pour qu'aucun appelant de `gravite_gpu.gravity` ne puisse l'oublier.
6. **w0/wa extrapolés dans l'avenir** (`cosmologie.h:30`, `:57-69`) : résultat non physique pour a > 1 avec wa < 0. Afficher un avertissement ou figer w à sa valeur d'aujourd'hui pour a > 1.
7. **Statut de l'énergie noire à l'écran** : ajouter des réglages nommés « Planck 2018 », « ACT+Planck+DESI 2025 (H0 = 68,4) », « échelle locale H0DN 2026 (73,5) », « DESI DR2 + CMB + supernovæ (w0 ≈ −0,8, wa ≈ −0,7 ; 2,8 à 4,2 σ, 3,2 σ après recalibrage) », avec le label « indication, pas découverte ».
8. **« Grand Attracteur » placé sur l'amas de la Règle** (`build_data.py:193`) : renommer et ajouter le point de convergence (313°, 27°), ~41 h⁻¹ Mpc, avec la mention qu'il dépend du lissage et que Virgo ne fournit qu'un tiers du mouvement (Stiskalek et al. 2026).
9. **Vitesse du Groupe local par rapport au CMB** : utiliser 620 ± 15 km/s vers (271,9°, 29,6°) (Planck 2018 I, table 3) plutôt que 627 km/s.
10. **Centre de l'énergie noire différent selon le script** : origine dans `calcul.py:120, 145`, centre de masse dans `rencontre.py:122-125` et les ensembles. Uniformiser sur le centre de masse.
11. **Avenir lointain non montré** : le temps s'arrête à la fin du film. Une vue « +100 à +150 Ga » calculée par `scaleFactorAt` (a = 321 à 5 561), avec l'horizon des événements (16,7 milliards d'al aujourd'hui) et la disparition des galaxies au-delà du rayon de gravité nulle (~1,4–1,9 Mpc), montrerait l'isolement de Milkomeda. À signaler comme modèle (w = −1).

### Faible

12. Ω_k = −9,2 × 10⁻⁵ par défaut au lieu de 0 (`cosmologie.h:26`) : poser Ω_Λ = 1 − Ω_m − Ω_r pour le réglage « plat ».
13. Neutrinos sans masse et N_eff = 3,046 (au lieu de Σm_ν = 0,06 eV et 3,044) : effet < 0,05 %.
14. `essai_cosmologie.cpp` ne contrôle pas `scaleFactorAt`, wa ≠ 0 ni la courbure.
15. Temps de regard en arrière, distance angulaire et distance lumineuse non affichés dans la fiche d'une galaxie.
16. Constantes cosmologiques recopiées à sept endroits ; `constantes_univers.h:14-17` non utilisé. Générer toutes les copies depuis `univers.json` (déjà fait pour K_lambda côté Python, `construire.py:144`).
17. `univers.json:44` : statut « mesuré » pour un bloc qui contient w0 = −1 et wa = 0, qui sont une hypothèse.
18. CMB : dire que la carte SMICA n'a ni monopôle ni dipôle et que la bande galactique est reconstruite ; placer la carte à D_M(z*) = 13,86 Gpc ; « 380 000 ans » → 372 000 ans si l'on veut la valeur de Planck.
19. Système solaire sans terme Λ : effet de 10⁻²², à documenter seulement.

---

## Sources consultées aujourd'hui

- DESI DR2 Results II : https://arxiv.org/pdf/2503.14738 ; exposé DESI (valeurs w0/wa) : https://cosmology.lbl.gov/talks/Cuceu_25.pdf
- DES-Dovekie (Popovic et al. 2025) : https://arxiv.org/abs/2511.07517v2
- CCHP (Freedman et al. 2025) : https://arxiv.org/abs/2408.06153v3 ; Hoyt et al. 2025 : https://www.arxiv.org/pdf/2503.11769
- H0 Distance Network 2026 : https://www.eurekalert.org/news-releases/1123728
- ACT DR6 (Louis et al. 2025) : https://arxiv.org/abs/2503.14452v2
- DES Y6 3×2pt : https://arxiv.org/abs/2601.14559
- Planck 2018 I, table 3 : https://www.aanda.org/articles/aa/full_html/2020/09/aa33880-18/T3.html
- Peñarrubia et al. 2014 : https://arxiv.org/pdf/1405.0306
- Benisty, Davis & Evans 2023 : https://arxiv.org/abs/2306.14963v1
- Chernin et al. 2009 : https://www.aanda.org/10.1051/0004-6361/200912762 (référence seulement)
- Cosmicflows-4 : https://arxiv.org/abs/2209.11238
- Valade et al. 2024 : https://ui.adsabs.harvard.edu/abs/2024NatAs...8.1610V/abstract
- Stiskalek et al. 2026 : https://arxiv.org/pdf/2601.08524
- Manticore-Local : https://arxiv.org/abs/2505.10682

Non relus aujourd'hui (cités de mémoire, [Probable] ou [À vérifier] dans le texte) : Planck 2018 VI (table 2), Pantheon+, DES-SN5YR d'origine, Union3, SPT-3G D1, KiDS-Legacy, Karachentsev 2009, Partridge 2013, Nagamine & Loeb 2003, Busha 2003, Krauss & Scherrer 2007, Tully 2014, HESTIA, SIBELIUS, CLUES, Wempe 2024, Tinker 2008, Bryan & Norman 1998, Linder 2005, Fixsen 2009, Huchra 2012.
