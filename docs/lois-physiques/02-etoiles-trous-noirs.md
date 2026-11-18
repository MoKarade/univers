# Annexe 2 — Étoiles, évolution stellaire et trous noirs

Rapport de recherche du 18 novembre 2026. Aucun fichier du dépôt modifié, aucun calcul GPU lancé.
Code lu : `/home/claude/univers` (branche `appli-pc`) et `/home/claude/film-3` (branche `film-3`).

Labels : **[Certain]** lu aujourd'hui dans la source ou le code ; **[Probable]** publié, cité de mémoire avec source connue ; **[Supposition]** mon raisonnement ; **[À vérifier]** non vérifié.

## Résumé

- **Le vieillissement de la lumière ne suit pas le film.** L'appli applique un facteur par composante, calculé avec un rythme de naissance constant (`vieillissement.h:3`). Or le film-3 fait maintenant naître des étoiles à des dates connues (`gaz_galaxie.py:65-78`). La table `population_simple` (MIST v1.2 × Kroupa) existe déjà dans le dépôt : il suffit de l'appliquer à l'âge réel de chaque particule née. C'est l'écart le plus fort.
- **Les étoiles Gaia « à orbite fiable » ne vieillissent pas.** Elles restent affichées avec leur éclat d'aujourd'hui à +5 Ga, alors que les géantes et les étoiles A (majoritaires parmi les étoiles à vitesse radiale lointaines) seront mortes en moins de 1 à 2 Ga [Supposition sur la proportion].
- **Aucun trou noir dans l'appli native ni dans le film.** Sgr A* est une étiquette (`simulation.h:429-434`). La lentille de Schwarzschild n'existe que dans la page web (`app/src/27_lens.js`, HANDOVER.md:137). Le film n'a pas de particule « trou noir » ; la fusion Sgr A*–M31* n'est pas montrée.
- **Gaia DR4 sort le 2 décembre 2026** [Certain, ESA] : 312 millions de lignes dans la table des vitesses radiales, contre 33,8 millions dans DR3. Le problème des « vitesses radiales manquantes » change d'échelle dans deux semaines.
- **MIST v2 est publié** (Dotter et al. 2026, arXiv:2602.22012) [Certain] : [α/Fe] de −0,2 à +0,6, [Fe/H] de −3 à +0,5. Utile pour le disque épais, le bulbe et le halo, que l'appli traite avec des abondances solaires réduites.
- **Couleurs** : l'appli convertit BP−RP en température de corps noir, puis en couleur CIE (`gaia_convertir.py:95-118`, `commun.h:90-104`). C'est correct à quelques % pour les étoiles FGK, moins pour les naines M et les étoiles rougies par la poussière. Deux formules de corps noir différentes coexistent (CIE dans `commun.h`, Tanner Helland dans `gaia.vert:33`).
- **Le film ne rend pas la masse des étoiles mortes au gaz** : une population rend 30 à 45 % de sa masse en 10 Ga [Probable]. Pas de supernovæ non plus (signalé dans `gaz_galaxie.py:17`). La masse totale est conservée, mais le gaz s'épuise trop vite.
- **Les valeurs de référence de l'appli sont bonnes** : Sgr A* 4,3 × 10⁶ M☉, M87* 6,5 × 10⁹ M☉, Gliese 710, Bailer-Jones 2022. Petit écart : R0 = 8,2 kpc contre 8,277 kpc (GRAVITY 2022).
- **Supernovæ et novæ** : rien n'est montré. Taux de référence : 1,63 ± 0,46 supernova à effondrement par siècle, 26 ± 5 novæ par an dans la Voie lactée [Certain].

---

## 1. Évolution stellaire

### 1.1 Grilles de référence

| Grille | Version | Domaine | Référence | Statut |
|---|---|---|---|---|
| **MIST** | v1.2 | 0,1–300 M☉ ; [Fe/H] −4 à +0,5 ; [α/Fe] = 0 ; v/vcrit 0 et 0,4 | Dotter 2016, ApJS 222, 8 ; Choi et al. 2016, ApJ 823, 102 | [Probable] ; c'est celle de l'appli |
| **MIST** | v2 (« MIST II ») | [Fe/H] −3 à +0,5 ; **[α/Fe] = −0,2 ; 0 ; +0,2 ; +0,4 ; +0,6**, cohérent des intérieurs aux spectres synthétiques ; tables de corrections bolométriques | Dotter, Bauer, Park, Conroy, Milone, Joyce, Cantiello 2026, arXiv:2602.22012, DOI 10.3847/1538-4365/ae48f3 | [Certain] pour le résumé ; domaine de masse et rotation non lus [À vérifier] |
| **PARSEC** | v2.0 | 0,09–14 M☉ ; Z = 0,004 à 0,017 (6 valeurs) ; rotation de zéro à critique au-dessus de 1,3 M☉ | Nguyen et al. 2022, A&A 665, A126, DOI 10.1051/0004-6361/202244166 | [Certain] pour le résumé |
| **PARSEC** | v2.0, extension | 7 métallicités de plus, Z = 0,0001 à 0,03 | arXiv:2508.02393 (A&A 2025) | [Certain] pour le titre ; contenu non lu [À vérifier] |
| **BaSTI-IAC** | 2018–2021 | 0,1–15 M☉ ; solaire et α-enrichi | Hidalgo et al. 2018, ApJ 856, 125 ; Pietrinferni et al. 2021, ApJ 908, 102 | [Probable] |
| **Genève** | 2012 | 0,8–120 M☉ ; Z = 0,014 ; avec et sans rotation | Ekström et al. 2012, A&A 537, A146 | [Probable] |
| **Naines blanches** | Montréal / La Plata | séquences de refroidissement | Bédard et al. 2020, ApJ 901, 93 ; Althaus et al. 2010 | [Probable] |

**Ce que fait l'appli** [Certain] :
- `pipeline/etoiles/vieillissement_populations.py:15-16` : MIST v1.2, v/vcrit = 0,4, 15 métallicités, fichiers « basic ».
- `pipeline/etoiles/build_mist_life.py:22-25` : durées de vie par masse, [Fe/H] = 0, sans rotation, destin lu sur le nombre de points EEP (454 = fin de séquence principale, 808 = fin du carbone, 1710 = refroidissement de naine blanche).
- Les deux scripts n'utilisent pas la même rotation (0 et 0,4). Écart faible : la rotation allonge la séquence principale de quelques % à 25 % pour les étoiles massives [Probable, Ekström 2012].

**Écart** : le disque épais, le bulbe et le halo sont enrichis en éléments α ([α/Fe] ≈ +0,2 à +0,4) [Probable]. MIST v1.2 les traite en abondances solaires réduites. À [Fe/H] donné, une population α-enrichie est un peu plus rouge et moins lumineuse, comme une population de métallicité totale plus haute [Probable]. MIST v2 corrige cela. Impact faible sur l'image.

### 1.2 Durée de vie en fonction de la masse et de la métallicité

Ordre de grandeur : t_SP ≈ 10 Ga × (M/M☉)^−2,5 entre 0,5 et 10 M☉, et t ∝ M/L qui tend vers ~3 Ma aux très grandes masses (L ∝ M près de la limite d'Eddington) [Probable, manuels].

| Masse (M☉) | Séquence principale, Z solaire | Fin de vie | Label |
|---|---|---|---|
| 0,1 | ~10¹³ ans (Laughlin, Bodenheimer & Adams 1997, ApJ 482, 420) | naine blanche d'hélium, jamais géante | [Probable] |
| 0,5 | ~80–100 Ga | pas encore de mort dans l'Univers | [Probable] |
| 0,8 | ~20–25 Ga | — | [Probable] |
| 1,0 | ~9–10 Ga ; vie totale 12,3 Ga | naine blanche 0,54 M☉ | [Probable] ; l'appli a 0,5405 M☉ (`docs/verite-avenir.md:24`) |
| 2 | ~1,0–1,2 Ga | naine blanche ~0,65 M☉ | [Probable] |
| 5 | ~100 Ma | naine blanche ~1,0 M☉ | [Probable] |
| 8–10 | ~25–40 Ma | limite naine blanche / supernova | [Probable] |
| 20 | ~8–9 Ma | supernova ou effondrement direct | [Probable] |
| 60–100 | ~3–4 Ma | trou noir | [Probable] |

Effet de la métallicité : à faible métallicité, l'opacité baisse, l'étoile est plus chaude, plus lumineuse et vit moins longtemps. À 1 M☉, la séquence principale dure ~6–7 Ga à [Fe/H] = −1,5 contre ~9–10 Ga au Soleil [Probable, MIST/BaSTI ; valeurs exactes à relire dans la grille].

Ces valeurs n'ont pas été relues dans les fichiers MIST aujourd'hui : la tâche `build_mist_life.py` les produit, et ce sont ses sorties qui font foi.

### 1.3 Chemins dans le diagramme HR

Séquence [Probable, manuels et MIST] : pré-séquence principale → séquence principale (hydrogène au cœur) → sous-géante → branche des géantes rouges (hydrogène en couche) → flash de l'hélium en dessous de ~2 M☉ → branche horizontale ou « clump » rouge (~10² Ma, L ≈ 50 L☉, Teff ≈ 4 800 K) → branche asymptotique (AGB), pulsations thermiques → nébuleuse planétaire (~10⁴ ans) → naine blanche. Étoiles massives : supergéante bleue, rouge, parfois Wolf-Rayet, puis effondrement.

Pour le rendu, le point important : **une population vieille doit l'essentiel de sa lumière visible à ses géantes rouges**, pas à sa séquence principale. À 10 Ga, géantes et clump donnent plus de la moitié de la lumière V [Probable, Renzini & Buzzoni 1986]. Les traceurs de l'appli portent une lumière agrégée, donc c'est déjà inclus dans la somme sur l'isochrone (`vieillissement_populations.py:124-136`).

### 1.4 Perte de masse

| Phase | Loi | Référence | Label |
|---|---|---|---|
| Géantes rouges | Reimers : Ṁ = 4 × 10⁻¹³ η L R / M (M☉/an, unités solaires), η ≈ 0,1–0,5 | Reimers 1975 ; calibrage astérosismique η ≈ 0,1–0,3 : Miglio et al. 2012, MNRAS 419, 2077 | [Probable] |
| AGB | Blöcker 1995 (A&A 297, 727), η ≈ 0,1 dans MIST ; « supervent » jusqu'à 10⁻⁴ M☉/an | Choi et al. 2016 | [Probable] |
| Étoiles chaudes | vents radiatifs, Ṁ ∝ Z^0,7–0,85 | Vink, de Koter & Lamers 2001, A&A 369, 574 ; taux révisés à la baisse d'un facteur ~3 : Björklund et al. 2021, A&A 648, A36 | [Probable] |
| Soleil | perd ~0,3 M☉ sur la branche des géantes, finit à 0,54 M☉ | Schröder & Smith 2008, MNRAS 386, 155 | [Probable] |

**Fraction de masse rendue au gaz** par une population simple : R ≈ 0,30 (Kroupa 2001) à 0,45 (Chabrier 2003) après 10 Ga ; la moitié est rendue dans le premier milliard d'années [Probable ; Leitner & Kravtsov 2011, ApJ 734, 48 ; Vincenzo et al. 2016, MNRAS 455, 4183].

**Écart avec le film** [Certain pour le code] : `gaz_galaxie.py:16` dit « la particule change de nature, pas de masse ». La masse totale est conservée, ce qui respecte la règle de Marc. Mais le gaz rendu par les étoiles mourantes n'existe pas. Dans la Voie lactée réelle, ce retour vaut ~1 M☉/an, du même ordre que la formation d'étoiles (~1,7–2 M☉/an) [Supposition : 5 × 10¹⁰ M☉ × taux de retour tardif ~2 × 10⁻¹¹ /an]. Sans lui, le gaz du film s'épuise environ deux fois trop vite. Un retour de masse conserve aussi la masse totale : c'est compatible avec la règle.

### 1.5 Fins de vie et relation masse initiale–masse finale

**Naines blanches** — Cummings, Kalirai, Tremblay, Ramirez-Ruiz & Choi 2018, ApJ 866, 21, DOI 10.3847/1538-4357/aadfd6 [Certain pour le résumé] : 80 naines blanches de 13 amas plus Sirius B ; progéniteurs de 0,85 à 7,5 M☉ ; trois segments de pentes 0,08, 0,19 (de 2,85 à 3,6 M☉) et 0,11 ; dispersion 0,06 M☉ ; perte de masse totale de 33 % à 0,83 M☉ et 83 % à 7,5 M☉.

Forme avec isochrones MIST [Probable, corps de l'article, non relu aujourd'hui] :

```
M_f = 0,080 M_i + 0,489     pour 0,83 < M_i < 2,85
M_f = 0,187 M_i + 0,184     pour 2,85 < M_i < 3,60
M_f = 0,107 M_i + 0,471     pour 3,60 < M_i < 7,20
```

**Étoiles à neutrons et trous noirs** :

| Grandeur | Valeur | Source | Label |
|---|---|---|---|
| Masse minimale pour une supernova à effondrement | 8 ± 1 M☉ | Smartt 2009, ARA&A 47, 63 | [Probable] |
| Masse des étoiles à neutrons | 1,2–2,0 M☉, pic à 1,35 | Özel & Freire 2016, ARA&A 54, 401 | [Probable] |
| Étoile à neutrons la plus massive mesurée | 2,08 ± 0,07 M☉ (PSR J0740+6620) | Fonseca et al. 2021, ApJL 915, L12 | [Probable] |
| Explosion ou effondrement direct | pas une simple coupure en masse : « îlots d'explosabilité » entre ~15 et ~40 M☉ | Sukhbold et al. 2016, ApJ 821, 38 ; Ertl et al. 2016, ApJ 818, 124 | [Probable] |
| Recette de masse du résidu | lois « rapid » et « delayed » | Fryer et al. 2012, ApJ 749, 91 | [Probable] |
| Trou d'instabilité de paires | pas de trou noir entre ~50 et ~130 M☉ (étoiles isolées) | Woosley 2017, ApJ 836, 244 ; Farmer et al. 2019, ApJ 887, 53 | [Probable] |
| Dépendance en métallicité | à faible Z, vents faibles, trous noirs plus massifs (Gaia BH3 : 33 M☉, étoile très pauvre en métaux) | Panuzzo et al. 2024 | [Certain] |

**Ce que fait l'appli** [Certain] : `build_mist_life.py:25` classe « wd » si le modèle atteint le refroidissement, « cc » si la masse ≥ 7 M☉ et le modèle s'arrête à la fin du carbone. Pas de distinction étoile à neutrons / trou noir, pas de masse de résidu. `docs/audit-precision.md:19` dit honnêtement que le destin est statistique. Les naines blanches ne sont pas comptées dans la lumière des populations (`docs/vieillissement-lumiere.md:49`) : c'est quelques % de la lumière bolométrique à 10 Ga, moins de 1 % en visible [Supposition], donc sans conséquence à l'écran.

### 1.6 Supernovæ

| Grandeur | Valeur | Source | Label |
|---|---|---|---|
| Énergie cinétique | ~10⁵¹ erg (1 « foe ») | canonique | [Probable] |
| Énergie en neutrinos (effondrement) | ~3 × 10⁵³ erg | SN 1987A | [Probable] |
| Type Ia | ~1,3 × 10⁵¹ erg, ~0,6 M☉ de ⁵⁶Ni, M_V ≈ −19,3 au maximum | manuels | [Probable] |
| Type II-P | M_V ≈ −17 au maximum, plateau ~100 jours | manuels | [Probable] |
| **Taux d'effondrements, Voie lactée** | **1,63 ± 0,46 par siècle**, soit une tous les 61 (+24, −14) ans | Rozwadowska, Vissani & Cappellaro 2021, New Astronomy 83, 101498, arXiv:2009.03438 | [Certain] |
| Taux par ²⁶Al | 1,9 ± 1,1 par siècle | Diehl et al. 2006, Nature 439, 45 | [Probable] |
| Taux total (avec Ia) | 2,84 ± 0,60 par siècle | Li et al. 2011, MNRAS 412, 1473 | [Probable] |
| Supernovæ par masse formée | ~1 pour 100 M☉ (Kroupa, 8–100 M☉) | intégrale de la fonction de masse | [Supposition, calcul standard] |
| Quantité de mouvement injectée | ~3 × 10⁵ M☉ km/s par supernova | Kim & Ostriker 2015, ApJ 802, 99 | [Probable] |
| Délai des Ia | taux ∝ t⁻¹ à partir de ~40 Ma ; ~1,3 × 10⁻³ Ia par M☉ formée | Maoz & Graur 2017, ApJ 848, 25 | [Probable] |

**Écart** [Certain] : ni l'appli ni le film ne montrent ni ne calculent de supernova. `gaz_galaxie.py:17` le signale (« ce qui manque encore : chauffage par les explosions »). Conséquence physique attendue [Probable, cf. Hopkins et al. 2011] : sans rétroaction, le gaz s'effondre en grumeaux et forme des étoiles trop vite, surtout au passage au péricentre. Le plancher de Jeans (`N_JEANS = 4`) limite la casse mais ne remplace pas l'énergie injectée.

À l'échelle d'un film à pas de 10 Ma, une supernova (visible quelques mois) ne peut pas être une image. En revanche, à vitesse de temps lente (1 an/s à 1 000 ans/s), l'appli pourrait tirer des supernovæ au taux mesuré, placées selon la densité d'étoiles jeunes, signalées comme modèle : ~1,6 par siècle.

### 1.7 Novæ

| Estimation | Taux (par an) | Source | Label |
|---|---|---|---|
| ASAS-SN + Gaia | **26 ± 5** | Kawash et al. 2022, ApJ 937, 64, DOI 10.3847/1538-4357/ac8d5e | [Certain] |
| Infrarouge, Palomar Gattini-IR | 43,7 (+19,5, −8,7) | De et al. 2021, ApJ 912, 19, arXiv:2101.04045 | [Probable] |
| Optique historique | 50 (+31, −23) | Shafter 2017, ApJ 834, 196 | [Probable] |

Pic M_V ≈ −6 à −10, déclin en jours à mois, récurrence 10⁴–10⁵ ans (1 à 100 ans pour les novæ récurrentes comme T CrB) [Probable]. Absent de l'appli.

---

## 2. Populations : fonction de masse, binaires, âges, histoire

### 2.1 Fonction de masse initiale

**Kroupa 2001** (MNRAS 322, 231) [Probable] : ξ(m) ∝ m^−α, avec α = 0,3 ± 0,7 (0,01–0,08 M☉), α = 1,3 ± 0,5 (0,08–0,5), α = 2,3 ± 0,3 (0,5–1), α = 2,3 ± 0,7 (> 1 M☉).

**Chabrier 2003** (PASP 115, 763) [Probable] : log-normale sous 1 M☉, ξ(log m) ∝ exp[−(log m − log m_c)² / 2σ²] avec m_c = 0,079 M☉ et σ = 0,69 (étoiles individuelles du disque) ; m_c = 0,22 et σ = 0,57 (systèmes) ; loi de puissance d'exposant 2,3 au-dessus.

Les deux donnent le même rendu : masse moyenne ~0,4–0,6 M☉, ~1 supernova pour 100 M☉ formées [Probable].

**Appli** [Certain] : `vieillissement_populations.py:70-77` : Kroupa à deux pentes (1,3 et 2,3, coude à 0,5), de 0,1 à 100 M☉. Les naines brunes (< 0,08) et la tranche 0,08–0,1 sont omises : ~5 % de la masse, lumière nulle [Supposition]. Conforme.

Variations [Probable] : fonction de masse plus riche en naines dans les cœurs d'elliptiques massives (Conroy & van Dokkum 2012, ApJ 760, 71) ; plus plate dans les amas du centre galactique. Sans objet pour le Groupe local à ce niveau.

### 2.2 Multiplicité

**Moe & Di Stefano 2017**, ApJS 230, 15, DOI 10.3847/1538-4365/aa6fb6 [Certain pour le résumé] :
- nombre de compagnons par primaire (q > 0,1, log P(jours) < 8) : **0,50 ± 0,04** pour les étoiles de type solaire, **2,1 ± 0,3** pour les étoiles O ;
- périodes courtes (P < 20 jours) : excentricité < 0,4, ⟨q⟩ = 0,5, léger excès de jumelles (q > 0,95) ;
- pic de fréquence vers log P = 3,5 (a ≈ 10 UA), q = 0,2–0,3 favorisé ;
- grandes séparations (200–5 000 UA) : q compatible avec un tirage au hasard dans la fonction de masse ;
- 30 ± 10 % des binaires spectroscopiques à une raie de type solaire ont une naine blanche pour compagnon.

Fraction de systèmes multiples : ~27 % pour les naines M, ~44 % pour le type solaire, > 90 % pour les O [Probable ; Raghavan et al. 2010, ApJS 190, 1 ; Winters et al. 2019, AJ 157, 216 ; Sana et al. 2012, Science 337, 444].

**Conséquences pour l'appli** [Supposition] :
1. Rendu : aucune. Les binaires non résolues sont déjà dans le flux Gaia mesuré.
2. Vitesses : le mouvement orbital fausse la vitesse radiale d'une binaire serrée de plusieurs km/s. Le drapeau « orbite fiable » (`gaia_convertir.py:206-213`, seuil sur l'erreur 3D publiée) ne teste pas la binarité. Gaia fournit `ruwe` (> 1,4 : astrométrie perturbée) et `rv_amplitude_robust` : les ajouter au critère serait cohérent.
3. Évolution : ~70 % des étoiles O échangent de la masse avec un compagnon (Sana 2012) [Probable] ; les grilles d'étoiles isolées (MIST) ne décrivent donc pas bien la fin de vie des étoiles massives. À signaler comme limite du modèle.

### 2.3 Relation âge–métallicité

Il n'y a **pas** de relation serrée dans le voisinage solaire : la dispersion en [Fe/H] à âge donné (~0,2 dex) est comparable à toute l'évolution moyenne, à cause de la migration radiale [Probable ; Casagrande et al. 2011, A&A 530, A138 ; Feuillet et al. 2019, MNRAS 489, 1742]. La relation est serrée seulement pour la séquence riche en α (disque épais) : montée rapide de [Fe/H] ≈ −1 à 0 entre 13 et 8 Ga [Probable ; Xiang & Rix 2022].

Gradient radial du disque mince : −0,05 à −0,07 dex/kpc [Probable ; Genovali et al. 2014, A&A 566, A37].

**Appli** [Certain] : `vieillissement_populations.py:55-67` donne une métallicité unique par composante (disque mince 0,0 ; bulbe 0,0 ; disque épais −0,5 ; halo −1,5), marquée « supposé ». Raisonnable. Le bulbe réel a une distribution large et bimodale (pics vers −0,3 et +0,3) [Probable ; Ness et al. 2013, MNRAS 430, 836].

### 2.4 Histoire de formation stellaire de la Voie lactée

| Fait | Valeur | Source | Label |
|---|---|---|---|
| Début du disque épais | il y a 13 Ga (0,8 Ga après le Big Bang) ; la plupart de ses étoiles formées il y a ~11 Ga | Xiang & Rix 2022, Nature 603, 599, DOI 10.1038/s41586-022-04496-5 | [Certain] |
| Fusion Gaia-Saucisse-Encelade | il y a ~11 Ga | idem ; Helmi et al. 2018, Nature 563, 85 | [Certain] / [Probable] |
| Phase calme du disque mince | depuis ~8 Ga | Xiang & Rix 2022 | [Certain] |
| Sursauts récents du voisinage solaire | il y a ~5,7, 1,9 et 1 Ga, liés aux passages de la naine du Sagittaire | Ruiz-Lara et al. 2020, Nature Astronomy 4, 965 | [Probable] |
| Sursaut il y a 2–3 Ga | — | Mor et al. 2019, A&A 624, L1 | [Probable] |
| **Taux actuel** | **2,0 ± 0,7 M☉/an** (1,7 ± 0,6 pour les sources à distance fiable) ; 84 % à l'intérieur du cercle solaire ; pics à la zone moléculaire centrale et à 5 kpc | Elia et al. 2022, ApJ 941, 162, DOI 10.3847/1538-4357/aca27d | [Certain] |
| Taux actuel (autre méthode) | 1,65 ± 0,19 M☉/an | Licquia & Newman 2015, ApJ 806, 96 | [Probable] |
| Masse stellaire | 6,08 ± 1,14 × 10¹⁰ M☉ ; ou 5 ± 1 × 10¹⁰ | Licquia & Newman 2015 ; Bland-Hawthorn & Gerhard 2016, ARA&A 54, 529 | [Probable] |
| Part du disque épais | jusqu'à ~la moitié de la masse stellaire | Snaith et al. 2015, A&A 578, A87 | [Probable] |

**Appli** [Certain] : disque mince « rythme constant de 0 à 10 Ga », disque épais « 9 à 12 Ga », bulbe « sursaut à 10 Ga », halo « sursaut à 12 Ga », bras « 0–100 Ma ». Comparaison :
- disque épais : la mesure dit 13 → ~8 Ga avec un pic vers 11 Ga. L'appli (9–12) est un peu jeune et étroite. Effet sur le facteur de lumière : petit.
- disque mince : la mesure dit ~8 Ga, pas 10, avec des sursauts. Effet petit en régime « naissance continue » (facteur ×1,05 à +10 Ga).
- le film-3 mesure son propre taux (`bulletin.py:68`, `naissance_etoiles_msol_an`). Cible de contrôle : 1,7–2,0 M☉/an à t = 0, dont 84 % sous 8,2 kpc.

---

## 3. Couleur et luminosité

### 3.1 Constantes nominales

Résolution B3 de l'UAI (2015) [Probable ; Prša et al. 2016, AJ 152, 41] : Teff☉ = 5 772 K ; L☉ = 3,828 × 10²⁶ W ; M_bol☉ = 4,74. Soleil en bandes Gaia : M_G = 4,67, (BP−RP)☉ = 0,82 [Probable ; Casagrande & VandenBerg 2018, MNRAS 479, L102]. M_V☉ = 4,83 [Probable].

Appli : `gaia_convertir.py:115` imprime le BP−RP du corps noir à 5 772 K ; `etoiles_visibles.py:47` prend M_V☉ = 4,83 [Certain]. Conforme.

### 3.2 Corps noir contre spectres réels

Une étoile n'est pas un corps noir : raies, saut de Balmer (étoiles A), bandes de TiO (naines M). Écarts connus [Probable] :
- étoiles FGK (4 500–7 000 K) : couleur perçue à quelques % de celle du corps noir ;
- naines M : le TiO mange le visible ; BP−RP atteint 2,5 à 4, ce qu'un corps noir ne donne que vers 2 000–2 500 K, alors que la vraie température est 3 000–3 800 K. La couleur réelle perçue est **orange**, pas rouge profond (Harre & Heller 2021, Astronomische Nachrichten 342, 578, « Digital color codes of stars », calculé sur spectres PHOENIX) [Probable] ;
- étoiles chaudes : le corps noir sature vers un bleu pâle (chromaticité limite x ≈ 0,24, y ≈ 0,23) ; aucune étoile n'est bleu saturé [Probable].

Relation mesurée couleur → température : Mucciarelli, Bellazzini & Massari 2021, A&A 653, A90 (Teff en fonction de BP−RP, naines et géantes, méthode du flux infrarouge) [Probable] ; table de Pecaut & Mamajek 2013, ApJS 208, 9, tenue à jour avec les couleurs Gaia [Probable].

**Appli** [Certain] :
- `gaia_convertir.py:95-118` : BP−RP mesuré → température du corps noir de même BP−RP synthétique (bandes de Riello et al. 2021) → `commun.h:90-104` : couleur CIE 1931 (ajustement analytique à lobes gaussiens des fonctions x̄, ȳ, z̄) → sRGB linéaire, normalisé au canal le plus fort.
- Cette chaîne est en fait une approximation « même rapport bleu/rouge », pas une vraie température. C'est défendable : deux spectres de même BP−RP ont des couleurs perçues voisines. Elle évite l'erreur classique « naine M = corps noir à 3 000 K ». Label du code : « couleur à quelques % près » [Probable selon le code].
- Limite : les couleurs hors du domaine du corps noir tombent sur les bords de la grille (1 000 K ou 200 000 K, `gaia_convertir.py:112`).
- `gaia.vert:33-39` utilise une **autre** formule (approximation de Tanner Helland) pour décaler la teinte quand la population vieillit, toujours autour de 5 800 K quel que soit le traceur (`gaia.vert:131`). Deux formules de corps noir dans le même rendu : incohérence faible, visible seulement loin d'aujourd'hui.
- `commun.h:105` : B−V → T par Ballesteros 2012 (EPL 97, 34008) [Probable pour la référence] : standard.

**Mieux, sans rien supposer** : Gaia DR3 publie 219 millions de spectres BP/RP basse résolution (De Angeli et al. 2023, A&A 674, A2) et l'outil GaiaXPy calcule la photométrie synthétique dans n'importe quelle bande, donc directement X, Y, Z (Gaia Collaboration, Montegriffo et al. 2023, A&A 674, A33) [Probable]. DR4 étend cela (table `ap_xp`, ~1 milliard de lignes [Certain, page ESA DR4]). C'est la voie « couleur réellement mesurée » pour les étoiles brillantes.

### 3.3 Corrections bolométriques

BC_G(Teff) : polynôme d'Andrae et al. 2018 (A&A 616, A8, table 4), valable de 3 300 à 8 000 K, BC_G☉ = +0,06 [Probable] ; pour DR3 : Creevey et al. 2023, A&A 674, A26, et l'outil `gaiadr3-bcg` [Probable]. MIST v2 fournit ses propres tables [Certain].

**Appli** [Certain] : l'éclat d'une étoile Gaia est 10^(−0,4 M_G) (`gaia.h:414`) : lumière en bande G, sans correction bolométrique. C'est le bon choix pour un rendu visible. Mais le facteur de vieillissement des populations est **bolométrique** (`vieillissement_populations.py:136`, somme de L) et il est appliqué à une lumière en bande V (`etoiles_visibles.py:14`). Pour une population vieille, V et bolométrique baissent à peu près ensemble [Supposition]. Pour une population jeune qui s'éteint (régime « sans naissance »), la lumière bolométrique est dominée par l'ultraviolet des étoiles O et chute bien plus vite que le visible : le facteur ×0,002 des bras à +10 Ga est exagéré en visible [Supposition]. Le script calcule déjà fV (flux à 550 nm, ligne 135) : prendre fV(t)/fV(0) au lieu de L(t)/L(0) corrigerait cela sans donnée nouvelle.

### 3.4 Extinction interstellaire

| Grandeur | Valeur | Source | Label |
|---|---|---|---|
| Loi moyenne | A(λ)/A_V paramétrée par R_V = 3,1 | Cardelli, Clayton & Mathis 1989, ApJ 345, 245 ; Fitzpatrick 1999, PASP 111, 63 ; Gordon et al. 2023, ApJ 950, 86 | [Probable] |
| Bandes Gaia | A_G/A_V = 0,789 ; A_BP/A_V = 1,002 ; A_RP/A_V = 0,589 | Wang & Chen 2019, ApJ 877, 116 | [Probable] |
| Vers le centre galactique | A_V ≈ 30 mag ; A_Ks ≈ 2,5 | Fritz et al. 2011, ApJ 737, 73 | [Probable] |
| Carte 3D locale | 1,25 kpc, résolution du parsec | Edenhofer et al. 2024, A&A 685, A82 | [Certain : c'est celle de l'appli, `build_dust.py:3`] |
| Cartes 3D plus lointaines | 3 kpc : Lallement et al. 2022, A&A 661, A147 ; ciel nord jusqu'à plusieurs kpc : Green et al. 2019, ApJ 887, 93 | — | [Probable] |

**Appli** [Certain] :
- Étoiles Gaia : magnitude et couleur telles que mesurées, poussière vue du Soleil incluse (`gaia_convertir.py:8`, `gaia.h:321`). Vu de la Terre, c'est exact. Vu d'ailleurs, l'étoile garde le rougissement de la ligne de visée solaire : faux, mais c'est dit.
- Étoiles du modèle : poussière intégrée entre caméra et étoile dans la carte 3D, 16 échantillons, A_R = 0,75 A_V, A_B = 1,32 A_V (`gaia.vert:133-145`).
- Ces coefficients sont ceux des filtres R (~0,65–0,70 µm) et B (0,44 µm) de Johnson. Les primaires sRGB sont plutôt vers 610, 550 et 465 nm, ce qui donne avec Cardelli environ 0,87 ; 1,00 ; 1,25 [Supposition : lu sur la loi, non recalculé]. L'appli rougit donc un peu trop (écart de couleur R−B : 0,57 A_V au lieu de ~0,38). Faible à modéré ; visible surtout vers le centre galactique.
- Les galaxies voisines sont hors de la carte de poussière (`gaia.vert:136`) : Andromède et les Nuages n'ont pas de poussière propre sur leurs traceurs.

**Voie possible** : Gaia DR3 donne `ag_gspphot` et `ebpminrp_gspphot` par étoile (Andrae et al. 2023, A&A 674, A27) ; le pipeline les télécharge déjà (`gaia_telecharger.py:33`, jeu « poussière ») pour l'agrégat. On peut dérougir chaque étoile, puis réappliquer la poussière de la carte 3D selon la position de la caméra. Les étoiles Gaia et celles du modèle suivraient alors la même règle.

---

## 4. Trous noirs

### 4.1 Sagittarius A*

| Grandeur | Valeur | Source | Label |
|---|---|---|---|
| Masse | **4,30 × 10⁶ M☉, précision ±0,25 %** (4,297 ± 0,012 dans le corps de l'article [Probable]) | GRAVITY Collaboration 2022, A&A 657, L12, DOI 10.1051/0004-6361/202142465 | [Certain] |
| Distance R0 | 8 277 ± 9 (stat.) ± 33 (syst.) pc | idem, corps de l'article | [Probable] (non relu : le résumé ne la donne pas) |
| Masse étendue dans l'orbite de S2 | ≲ 3 000 M☉ (1σ), ~0,1 % | idem | [Certain] |
| Anneau observé | **51,8 ± 2,3 µas** de diamètre | EHT Collaboration 2022, ApJL 930, L12 (arXiv:2311.08680) | [Certain] |
| Ombre déduite | 48,7 ± 7,0 µas | idem, § 7 | [Certain] |
| Inclinaison | les modèles à i > 50° sont défavorisés | idem | [Certain] |
| Rotation | mal contrainte ; les modèles EHT retenus sont en rotation prograde modérée à forte | EHT 2022, article V | [À vérifier] |
| Mouvement propre | −6,411 ± 0,008 mas/an en longitude | Reid & Brunthaler 2020, ApJ 892, 39 | [Probable] |
| Luminosité | ~10³⁶ erg/s, soit ~10⁻⁹ de la limite d'Eddington ; accrétion ~10⁻⁹–10⁻⁷ M☉/an | Marrone et al. 2007, ApJ 654, L57 ; Genzel, Eisenhauer & Gillessen 2010, RMP 82, 3121 | [Probable] |

Contrôle [Supposition, calcul fait ici] : GM/c² = 1,4766 km × 4,297 × 10⁶ = 6,345 × 10⁶ km ; à 8 277 pc, θ_g = 5,12 µas ; diamètre de l'ombre de Schwarzschild 2√27 θ_g = **53,2 µas**. L'anneau mesuré (51,8 ± 2,3) est compatible.

**Appli** [Certain] : 4,3 × 10⁶ M☉ dans la page (HANDOVER.md:139) : conforme. R0 = 8,2 kpc (`constantes_univers.h:8`) : 0,9 % sous GRAVITY 2022, dans la barre de Bland-Hawthorn & Gerhard 2016 (8,2 ± 0,1). Conséquence [Supposition, calcul fait ici] : le mouvement propre de Sgr A* donne V☉ totale = 4,74 × 6,411 × R0 = 249 km/s à 8,2 kpc et 251,5 km/s à 8,277 kpc ; l'appli a 232,8 + 12,24 = 245,0 km/s (`clones_etoiles.py:31`), soit 2 à 3 % de moins. Sujet d'une autre mission, signalé ici.

### 4.2 M31*, M33, Nuages, M87*

| Objet | Masse | Source | Label |
|---|---|---|---|
| M31* | 1,4 (+0,9, −0,3) × 10⁸ M☉ | Bender et al. 2005, ApJ 631, 280 | [Probable] |
| M33 | pas de trou noir central détecté : < 1 500 M☉ | Gebhardt et al. 2001, AJ 122, 2469 | [Probable] |
| Grand Nuage | ~6 × 10⁵ M☉, déduit d'étoiles hypervéloces | Han et al. 2025, ApJ | [À vérifier] |
| M87* | 6,5 ± 0,7 × 10⁹ M☉ ; anneau 42 ± 3 µas ; 16,8 Mpc | EHT Collaboration 2019, ApJL 875, L1 | [Probable] ; l'appli a 6,5 × 10⁹ [Certain] |

### 4.3 Trous noirs stellaires mesurés

| Objet | Masse (M☉) | Distance | Période | Source | Label |
|---|---|---|---|---|---|
| Gaia BH1 | 9,62 ± 0,18 | 480 pc | 185,6 j | El-Badry et al. 2023, MNRAS 518, 1057 | [Probable] |
| Gaia BH2 | 8,94 ± 0,34 | 1,16 kpc | 1 277 j | El-Badry et al. 2023, MNRAS 521, 4323 | [Probable] |
| **Gaia BH3** | **32,70 ± 0,82** | **590 pc** | **11,6 ans** | Gaia Collaboration, Panuzzo et al. 2024, A&A 686, L2, arXiv:2404.10486 | [Certain] |
| Cyg X-1 | 21,2 ± 2,2 | 2,22 kpc | 5,6 j | Miller-Jones et al. 2021, Science 371, 1046 | [Probable] |

Gaia BH3 : compagnon géante très pauvre en métaux du halo [Certain]. Population totale estimée : ~10⁸ trous noirs stellaires, ~10⁹ étoiles à neutrons, ~10¹⁰ naines blanches dans la Voie lactée [Probable, modèles de population]. DR4 doit en révéler des dizaines par astrométrie [Probable].

**Appli** [Certain] : `pipeline/fetch_more.py:50` interroge SIMBAD pour Cyg X-1, V404 Cyg, Gaia BH1/BH2/BH3, etc. ; HANDOVER.md:49 : « 245 + 37 trous noirs (van den Bosch 2016 ; BlackCAT), page ». Ils sont dans la page web. Dans l'appli native, aucun code de trou noir trouvé sous `natif/` (recherche « trou », « lentille », « Schwarzschild », « Kerr ») hormis le texte de `interface_ondes.h:65` sur les fusions LIGO-Virgo-KAGRA.

### 4.4 Métriques et lentille

Schwarzschild (sans rotation) [Certain, relativité générale standard] :
- rayon de l'horizon r_s = 2GM/c² = 2,953 km × (M/M☉) ; Sgr A* : 1,27 × 10⁷ km = 0,085 UA ;
- sphère de photons à 1,5 r_s ; rayon de l'ombre b_c = (√27/2) r_s = 2,598 r_s ;
- dernière orbite stable (ISCO) à 3 r_s ;
- déviation en champ faible α = 4GM/(c² b) ; exacte par l'équation d'orbite d²u/dφ² + u = 3GM u²/c² ;
- rayon d'Einstein θ_E = √[4GM/c² × D_LS/(D_L D_S)] ;
- décalage gravitationnel 1 + z = (1 − r_s/r)^−1/2.

Kerr (rotation a* = Jc/GM²) [Probable, Bardeen 1973 ; Bardeen, Press & Teukolsky 1972] :
- horizon r₊ = (GM/c²)[1 + √(1 − a*²)] ;
- ISCO prograde de 6 GM/c² (a* = 0) à 1 GM/c² (a* = 1) ; rétrograde jusqu'à 9 ;
- ombre presque circulaire, diamètre 9,6 à 10,4 GM/c² selon rotation et inclinaison, décalée et aplatie d'un côté à forte rotation vue par la tranche ;
- entraînement des repères ; tracé de rayons avec les constantes de Carter.

Références de rendu : James, von Tunzelmann, Franklin & Thorne 2015, Class. Quantum Grav. 32, 065001 (DNGR, film Interstellar) ; Luminet 1979, A&A 75, 228 (première image d'un disque mince) ; codes publics GYOTO (Vincent et al. 2011), ipole (Mościbrodzka & Gammie 2018), RAPTOR, Blacklight [Probable].

**Appli** [Certain] : page web seulement. `app/src/27_lens.js` : Schwarzschild, rayons suivis à rebours, table de 512 angles ; actif à moins de 10⁷ GM/c² de Sgr A* ou M87* (HANDOVER.md:137-142). Plan natif : jalons A4 « trou noir en rotation, avec disque… rotation marquée supposée » et E8 (`docs/plan-natif.md:45,126`), non faits.

### 4.5 Accrétion et jets, pour le rendu

Faits à respecter pour « ce à quoi ça ressemble vraiment » :
- **Sgr A* est presque éteint.** L ≈ 10⁻⁹ L_Edd [Probable]. En visible il est invisible, et derrière ~30 magnitudes de poussière vu de la Terre. L'image EHT est à 1,3 mm : un flot d'accrétion chaud, épais, optiquement mince (RIAF), pas un disque mince brillant. Un disque à la Interstellar autour de Sgr A* serait un **modèle faux pour aujourd'hui**. Rendu honnête : ombre noire, lentille des étoiles du fond, anneau millimétrique faible en fausse couleur signalée, sursauts infrarouges (GRAVITY Collaboration 2018, A&A 618, L10 : point chaud en orbite près de l'ISCO, période ~45 min [Probable]).
- **Traces d'activité passée** : bulles de Fermi (Su, Slatyer & Finkbeiner 2010, ApJ 724, 1044) et bulles d'eROSITA (Predehl et al. 2020, Nature 588, 227), ±10 à 14 kpc de part et d'autre du plan [Probable]. Elles ont leur place dans les cartes multi-longueurs d'onde.
- **M87*** : jet de ~1,5 kpc visible en optique, facteur de Lorentz ~ quelques unités ; l'anneau est plus brillant au sud par effet Doppler relativiste [Probable, EHT 2019].
- Disque mince (quasars) : T(r) ∝ r^−3/4 (Shakura & Sunyaev 1973, A&A 24, 337 ; Novikov & Thorne 1973), efficacité radiative 5,7 % (a* = 0) à 42 % (a* = 1) ; L_Edd = 1,26 × 10³⁸ (M/M☉) erg/s. Pour le tracé de rayons, la quantité I_ν/ν³ est invariante le long du rayon : l'intensité observée vaut g³ fois l'intensité émise à la fréquence décalée, g étant le rapport des fréquences (Doppler et gravitation) [Certain, relativité standard].
- À la fusion Voie lactée–Andromède, du gaz tombera vers les centres : un épisode de quasar est plausible (Cox & Loeb 2008, MNRAS 386, 461 ; Hopkins et al. 2006) [Probable]. À montrer comme modèle.

### 4.6 Fusion des trous noirs supermassifs lors de la collision Voie lactée–Andromède

| Fait | Valeur | Source | Label |
|---|---|---|---|
| Premier passage rapproché | dans ~4,3 Ga (autres études : 4–5 Ga) ; fusion des galaxies sur ~10 Ga | Schiavi, Capuzzo-Dolcetta, Arca-Sedda & Spera 2020, A&A 642, A30, DOI 10.1051/0004-6361/202038674, arXiv:2102.10938 | [Certain] |
| Fusion des deux trous noirs | **moins de 16,6 Ma** après la fusion des galaxies ; signal détectable par LISA jusqu'à z ≤ 2 | idem | [Certain] |
| **Probabilité de collision** | **~50 %** en 10 Ga, une fois comptés le Grand Nuage, M33 et les incertitudes ; fusion Voie lactée–Grand Nuage quasi certaine d'ici ~2 Ga | Sawala et al. 2025, Nature Astronomy, DOI 10.1038/s41550-025-02563-1 | [Certain via compte rendu sci.news ; article non lu] |
| Effet de l'expansion | 108 simulations (Newton, ΛCDM, w₀wₐ) : effet < 0,3 Ga aux faibles vitesses tangentielles ; retard ~1 Ga au-dessus de ~66 km/s ; un cas où ΛCDM empêche la fusion | Zhou et al. 2026, arXiv:2610.38490 | [Certain pour le résumé lu] |

Physique des trois phases [Probable ; Begelman, Blandford & Rees 1980, Nature 287, 307] :
1. **Friction dynamique** (Chandrasekhar 1943) : chaque trou noir descend avec son noyau stellaire. Pour un trou noir nu de 4,3 × 10⁶ M☉ à 1 kpc dans un milieu à 200 km/s, t ≈ 1,17 r² v / (ln Λ GM) ≈ 2 Ga avec ln Λ = 6 [Supposition, calcul fait ici]. Avec l'amas nucléaire (2,5 × 10⁷ M☉) et le bulbe qui l'accompagnent, c'est bien plus court.
2. **Durcissement** par éjection d'étoiles, quand la binaire est liée (~1–10 pc). Le « problème du dernier parsec » ne bloque pas dans un résidu triaxial (Khan, Just & Merritt 2011, ApJ 732, 89) [Probable].
3. **Ondes gravitationnelles** (Peters 1964, Phys. Rev. 136, B1224) : t = (5/256) c⁵ a⁴ / [G³ m₁ m₂ (m₁ + m₂)] pour une orbite circulaire.

Rapport de masse q = 4,3 × 10⁶ / 1,4 × 10⁸ ≈ 0,03. Recul par ondes gravitationnelles : faible à ce rapport (quelques km/s sans rotation ; au plus ~100 km/s avec rotations défavorables [Supposition d'après les lois d'échelle en η² de Campanelli et al. 2007 et Lousto & Zlochower 2011]). Le trou noir final (~1,45 × 10⁸ M☉) reste donc au centre du résidu.

**Film** [Certain] : aucune particule de trou noir (`modeles_v2.py` : aucune occurrence ; `docs/fusion-methode.md:70` : « les trous noirs centraux ne sont pas calculés »). Dynamiquement c'est sans effet à l'échelle du film : rayon d'influence de Sgr A* r = GM/σ² ≈ 2 pc pour σ = 100 km/s [Supposition, calcul fait ici], très en dessous du lissage gravitationnel. Mais rien n'est montré.

Proposition (modèle, à signaler) : une particule traceur par galaxie, posée au minimum du potentiel, portant la masse mesurée ; elle suit le centre de sa galaxie (déjà écrit par image du film, `docs/contrat-etoiles-visibles.md:72`) ; quand les deux centres sont à moins de la résolution du film, afficher « binaire non résolue », puis « fusion » 17 Ma plus tard (Schiavi 2020), avec la masse finale.

---

## 5. Mouvements stellaires

### 5.1 Vitesses radiales manquantes

| Fait | Valeur | Source | Label |
|---|---|---|---|
| Gaia DR3 | 33,8 millions de vitesses radiales, G_RVS ≲ 14 | Katz et al. 2023, A&A 674, A5 | [Probable] |
| **Gaia DR4** | sortie le **2 décembre 2026, 12 h CET** ; données du 25 juillet 2014 au 20 janvier 2020 (66 mois) ; `gaia_source` : 2 000 033 276 lignes ; **`all_source_rvs` : 312 247 580 lignes** ; 250 millions de spectres RVS moyens ; astrométrie, photométrie et spectres par époque | ESA, cosmos.esa.int/web/gaia/dr4 (table mise à jour le 14 septembre 2026) et news-2026 | [Certain] |
| Point zéro de parallaxe DR3 | −17 µas en moyenne, dépend de la magnitude, de la couleur et de la position | Lindegren et al. 2021, A&A 649, A4 | [Probable] |
| Vitesses radiales prédites | réseau bayésien, distribution prédite pour ~185 millions d'étoiles DR3 sans mesure | Naik & Widmark 2024, MNRAS 527, 11559 | [Probable ; nombre exact à vérifier] |

Je n'ai pas vérifié si les 312 millions de lignes de `all_source_rvs` sont toutes des vitesses valides ou incluent des sources sans solution [À vérifier le 2 décembre].

**Appli** [Certain] :
- `gaia_convertir.py:200-203` : sans vitesse radiale, v_r = 0 et drapeau.
- `gaia_convertir.py:206-213` : « orbite fiable » = vitesse radiale mesurée et erreur 3D sous un seuil (10 km/s d'après `gaia.h:131`).
- `gaia.h:50-53` : les autres étoiles s'effacent en exp(−(t/3 Ma)²) loin d'aujourd'hui.
- `gaia_convertir.py:191` : distance = 1/parallaxe, sans correction du point zéro ; biais ~1 % pour les étoiles à 10 % de précision, mesuré dans `docs/gaia-rayons.md:23` (−0,8 à −2 % contre Bailer-Jones 2021).

Remarques :
1. v_r = 0 n'est pas neutre : dans le repère du Soleil, cela place l'étoile sur une orbite fausse. Le choix de l'appli (l'effacer plutôt que l'inventer) est honnête.
2. Avec 10 km/s d'erreur, l'erreur de position croît de ~10 pc par Ma, soit 1 kpc à 100 Ma et tout le disque à 1 Ga [Supposition, calcul direct]. Au-delà de quelques dizaines de Ma, même une « orbite fiable » est une orbite **statistique**. S'y ajoute la diffusion par les nuages moléculaires et les bras, absente d'un potentiel lisse : la dispersion de vitesse croît avec l'âge comme t^0,3–0,5 (Aumer & Binney 2009, MNRAS 397, 1286 ; Mackereth et al. 2019, MNRAS 489, 176) [Probable].
3. DR4 multiplie par ~3 à 9 le nombre d'étoiles à vitesse radiale. Le pipeline (`gaia_telecharger.py:31`) interroge `gaiadr3.gaia_source` : passer à `gaiadr4` est le gain le plus direct sur ce point.
4. Option modèle (à signaler) : tirer la vitesse radiale manquante dans la distribution locale conditionnée à la vitesse tangentielle mesurée (Naik & Widmark 2024). Cela garde la lumière de la Galaxie dans le film lointain au lieu de l'effacer. À mettre derrière le même interrupteur que le « meilleur rendu ».

### 5.2 Rencontres stellaires proches

| Fait | Valeur | Source | Label |
|---|---|---|---|
| Recherche DR3 | 33 millions d'étoiles à 6 dimensions ; 61 passent à moins de 1 pc, **42 fiables** | Bailer-Jones 2022, ApJL 935, L9, DOI 10.3847/2041-8213/ac816a | [Certain] |
| **Gliese 710** | 0,0636 pc (IC 90 % : 0,0595–0,0678) dans 1,3 Ma | idem | [Certain] |
| Gliese 710, mise à jour | 0,0621 ± 0,0023 pc (~12 800 UA) dans 1 344,6 ± 2,2 milliers d'années | Fernandez-Puig et al. 2026, arXiv:2605.16496 | [Certain pour le résumé lu] |
| HD 7977 | il y a 2,8 Ma ; à moins de 0,05 pc avec une probabilité d'un tiers | Bailer-Jones 2022 | [Certain] |
| UPM J0812-352 | rencontre probablement fausse (vitesse radiale DR3 erronée) | idem | [Certain] |
| Étoile de Scholz | il y a ~70 000 ans, ~0,25 pc | Mamajek et al. 2015, ApJL 800, L17 ; révisé par Dupuy et al. 2019 | [Probable] |
| Taux | 10,6 ± 4,5 passages à moins de 1 pc par Ma ; 2,6 ± 1,1 à moins de 0,5 pc | Fernandez-Puig et al. 2026 | [Certain pour le résumé lu] |
| Taux (DR2) | 19,7 ± 2,2 par Ma à moins de 1 pc | Bailer-Jones et al. 2018, A&A 616, A37 | [Probable] |
| Complétude | la plupart des rencontres connues tombent à ±6 Ma, limite de magnitude des vitesses radiales | Bailer-Jones 2022 | [Certain] |

**Appli** [Certain] : HANDOVER.md:53 et 84 : 42 passages simulés (41 de Bailer-Jones 2022 plus l'étoile de Scholz d'après Dupuy 2019). `etoiles_hyg.py:11` : Gliese 710 ajoutée à la main d'après DR3. Conforme à la référence. Deux points :
- l'appli compte « 41 sans réserve + Scholz » ; l'article dit 42 fiables sur 61 : vérifier que UPM J0812-352 est bien exclue et que HD 7977 porte son incertitude (un tiers de chance sous 0,05 pc) [À vérifier dans la table de la page] ;
- DR4 changera la liste (plus d'étoiles, vitesses radiales corrigées).

---

## 6. Comparaison détaillée avec le code

### 6.1 `natif/src/vieillissement.h` et sa table

| Point | Code | Référence | Écart |
|---|---|---|---|
| Régime appliqué | « naissance continue » seulement (`vieillissement.h:3`) | le film-3 a de vraies naissances datées (`gaz_galaxie.py:45,78`) | **fort** : la lumière ne répond ni au sursaut du péricentre ni à l'épuisement du gaz |
| Facteurs | 5 composantes × (lum, teff), pas de 50 Ma, interpolation linéaire, bornée hors plage (`vieillissement.h:39-51`) | — | correct ; au-delà de +10 Ga le facteur est gelé |
| Luminosité | bolométrique (`vieillissement_populations.py:136`) appliquée à une lumière V | bande V ou G | moyen en régime « sans naissance », faible sinon |
| Température de couleur | rapport de corps noirs à 440/550 nm (`:107-121`) | couleurs synthétiques MIST (fichiers « full » avec photométrie, ou tables BC de MIST v2) | faible |
| Teinte au rendu | décalage autour de 5 800 K pour tous les traceurs (`gaia.vert:131`), formule Tanner Helland | décalage autour de la température du traceur, même formule CIE que `commun.h` | faible |
| Histoires de formation | supposées, marquées (`:55-67`) | Xiang & Rix 2022 ; Ruiz-Lara 2020 ; Elia 2022 | faible à moyen |
| Naines blanches | non comptées, dit | < 1 % en visible | négligeable |
| Autres galaxies | modèle de la Voie lactée « par analogie » (`galaxie_formes.vert:56-58`) | chaque galaxie a son histoire ; M33 et les Nuages forment plus d'étoiles par unité de masse | faible, signalé |
| Contrôles | pente −0,71 ; 3,5 M☉ formées par L☉ à 10 Ga, marqués [À vérifier] dans le doc | pente bolométrique attendue ~−0,8 à −0,9 pour x = 1,3 (Tinsley 1980, d ln L/d ln t ≈ −1,3 + 0,3 x) ; M/L_V ≈ 2–3,5 à 10 Ga (Bruzual & Charlot 2003) | cohérent [Probable] |

### 6.2 `natif/src/film_etoiles.h`

Lecteur du film : interpolation de Catmull-Rom sur quatre images, vitesse = pente (`film_etoiles.h:88-92`). Pas de physique stellaire. Contrainte de contrat : « aucun traceur ajouté ni retiré en route » (`contrat-etoiles-visibles.md:69`). **Cette clause empêche de montrer les étoiles nées pendant le calcul** comme nouveaux points. Deux voies compatibles avec « aucune bascule de forme » :
- réserver dès t = 0 des emplacements pour les particules de gaz (sorte 3), à lumière nulle, qui s'allument à leur date de naissance avec L_pop(âge) ;
- ou écrire les particules nées dans un flux séparé du film.

Je n'ai pas trouvé dans `natif/` de code qui lise la sorte 5 ou la date de naissance [Certain pour la recherche par mots-clés ; `film_v2.h` non lu en entier].

### 6.3 `gaia*.h` et `pipeline/natif/gaia_*.py`

| Point | Code | Écart |
|---|---|---|
| Couleur | BP−RP → corps noir → CIE (`gaia_convertir.py:95-118`, `gaia.h:178-186`) | faible ; voir § 3.2 |
| Éclat | bande G mesurée, poussière solaire incluse | correct vu de la Terre |
| Distance | 1/parallaxe, sans point zéro (`gaia_convertir.py:191`) | faible (~1 %) |
| Vitesse radiale absente | 0 + drapeau + effacement à 3 Ma | honnête ; DR4 à intégrer |
| Critère « fiable » | erreur 3D < seuil, sans test de binarité | faible à moyen |
| **Vieillissement des étoiles Gaia** | **aucun** dans cette branche ; `etoiles_vie.py` cité dans `docs/vieillissement-lumiere.md:5` est sur une branche `etoiles-vie` absente du clone [Certain : `git branch -a` ne la liste pas] | **moyen à fort** loin d'aujourd'hui |
| Âges mesurés | `fetch_flame.py` : Gaia FLAME pour les étoiles Hipparcos seulement | FLAME existe pour ~128 millions d'étoiles DR3 (Creevey et al. 2023) [Probable] ; extensible aux étoiles « fiables » |

Sur le vieillissement des étoiles Gaia : entre −3 et +3 Ma (fenêtre d'effacement), seules les étoiles O-B et les supergéantes changent ; c'est négligeable. Mais les étoiles « à orbite fiable » restent affichées à toutes les dates. À +1 Ga, toute étoile de plus de ~2 M☉ sur la séquence principale est morte, et toute géante actuelle aussi (durée de la phase géante : 10⁸ à 10⁹ ans) [Probable]. L'échantillon RVS lointain est dominé par des géantes [Probable]. Une part importante de la « lumière fiable » affichée dans le futur lointain vient donc d'étoiles qui n'existeront plus [Supposition : part non chiffrée ; `reliableLight` dans `gaia.h:134` permettrait de la mesurer par classe].

Vers le passé, c'est symétrique : à −3 Ga, les étoiles de moins de 3 Ga n'étaient pas nées.

### 6.4 Film-3 : naissance d'étoiles

| Point | Code (`gaz_galaxie.py`) | Référence | Écart |
|---|---|---|---|
| Loi | probabilité 1 − exp(−ε dt/t_ff), ε = 0,01 (`:34,72`) | ε_ff ≈ 0,01 : Krumholz & Tan 2007, ApJ 654, 304 ; Krumholz, Dekel & McKee 2012, ApJ 745, 69 | conforme |
| Seuil | n_H > 0,1 cm⁻³ (`:31`) | EAGLE : seuil dépendant de la métallicité autour de 0,1 (Schaye et al. 2015, MNRAS 446, 521) | conforme [Probable] |
| Loi globale à retrouver | — | Σ_SFR = 2,5 × 10⁻⁴ (Σ_gaz / M☉ pc⁻²)^1,4 M☉ an⁻¹ kpc⁻² (Kennicutt 1998, ApJ 498, 541) ; temps d'épuisement du gaz moléculaire ~2 Ga (Bigiel et al. 2008, AJ 136, 2846 ; Leroy et al. 2013, AJ 146, 19) | à contrôler sur le film [Probable pour les valeurs] |
| Gaz | isotherme à 10 km/s, plancher de Jeans | pas de phase froide ni chaude | modèle signalé |
| Rétroaction | absente, dit (`:17`) | 10⁵¹ erg et ~3 × 10⁵ M☉ km/s par supernova, 1 par 100 M☉ | **fort** sur l'histoire de formation |
| Retour de masse | absent | 30–45 % en 10 Ga | moyen à fort sur la durée de vie du gaz |
| Enrichissement | absent, dit | rendement y ≈ 0,02–0,04 | faible pour l'image |
| Lumière des étoiles nées | date gardée (`:45`) mais pas de lumière dérivée trouvée | L_pop(âge, Z) de la table existante | **fort** |

Contrôle chiffré suggéré : taux du film à t = 0 contre 2,0 ± 0,7 M☉/an (Elia 2022) ; répartition radiale (84 % sous R0).

---

## 7. Écarts avec l'appli, classés par impact sur le réalisme

### Fort

1. **Lumière des étoiles nées dans le film non reliée à leur âge.** Le film-3 date chaque naissance ; l'appli applique un facteur global à rythme constant. Remède sans donnée nouvelle : L = masse × L_pop(t − t_naissance, [Fe/H]) avec `population_simple` de `vieillissement_populations.json`, en flux V (fV) plutôt que bolométrique. Les sursauts au péricentre, puis le rougissement du résidu après épuisement du gaz, deviendraient visibles. Demande d'assouplir la clause « aucun traceur ajouté » du contrat, ou de réserver des emplacements à lumière nulle.
2. **Pas de rétroaction ni de retour de masse dans le gaz du film.** Signalé dans le code. Sans supernovæ (10⁵¹ erg, 1 par 100 M☉) le taux de formation est mal réglé ; sans retour de masse (~30–45 %), le gaz s'épuise trop tôt. Les deux conservent la masse totale.
3. **Aucun trou noir dans l'appli native ni dans le film.** Sgr A* (4,30 × 10⁶ M☉), M31* (1,4 × 10⁸ M☉) : ni lentille, ni ombre, ni fusion. La page web a la lentille de Schwarzschild ; le natif (jalons A4, E8) non. La fusion des deux trous noirs (< 16,6 Ma après celle des galaxies, Schiavi 2020) est un événement marquant du futur que le film ne montre pas.
4. **Étoiles Gaia « fiables » jamais vieillies.** À ±1 Ga et au-delà, géantes et étoiles massives sont affichées alors qu'elles n'existent pas à ces dates. Remède : classer chaque étoile fiable par sa place dans le diagramme couleur–magnitude (ou par FLAME : `age_flame`, `mass_flame`, `evolstage_flame`), en déduire sa durée de vie restante avec `build_mist_life.py`, et l'éteindre (ou la faire passer en naine blanche) à la date voulue. Destin statistique, à signaler comme modèle.

### Moyen

5. **Gaia DR4 (2 décembre 2026).** 312 millions de lignes de vitesses radiales contre 33,8 millions ; astrométrie sur 66 mois ; paramètres astrophysiques pour ~1 milliard de sources. Le pipeline vise `gaiadr3`. C'est la plus grosse amélioration « mesurée » disponible pour les mouvements d'étoiles.
6. **Facteur de vieillissement bolométrique appliqué à du visible.** Exagère l'extinction des populations jeunes en régime « sans naissance ». Remède : fV(t)/fV(0), déjà calculé dans le script.
7. **Poussière des étoiles Gaia figée sur la ligne de visée solaire**, alors que celle des étoiles du modèle suit la caméra. Remède : dérougir avec `ag_gspphot` / `ebpminrp_gspphot` (déjà téléchargés pour l'agrégat), puis réappliquer la carte 3D.
8. **Sgr A* « tel qu'il est »** quand il sera rendu : presque éteint (10⁻⁹ Eddington), flot chaud millimétrique, pas de disque mince brillant. Un disque à la Interstellar doit être marqué « modèle, pas l'état actuel ».
9. **Probabilité de la collision.** Sawala et al. 2025 : ~50 % en 10 Ga avec le Grand Nuage et M33. Si le film montre une fusion, l'écran doit dire que c'est une issue sur deux (sujet partagé avec la mission dynamique).
10. **Orbites « exactes » au-delà de quelques dizaines de Ma.** L'erreur de 10 km/s et la diffusion par les nuages et les bras en font des orbites statistiques. Le mot « exacte » (`gaia_orbites.h:1`) désigne l'intégration, pas la prédiction : à dire à l'écran.

### Faible

11. Coefficients de rougissement à l'écran (0,75 ; 1 ; 1,32) : ceux des filtres B, V, R, pas des primaires sRGB (~0,87 ; 1 ; 1,25). Rougit un peu trop.
12. Deux formules de corps noir (CIE dans `commun.h`, Tanner Helland dans `gaia.vert`) et décalage de teinte autour de 5 800 K pour tous les traceurs.
13. MIST v1.2 à abondances solaires réduites pour le disque épais, le bulbe et le halo ; MIST v2 (α-enrichi) est disponible.
14. Histoires de formation : disque épais 9–12 Ga (mesuré : 13 → ~8 Ga, pic vers 11) ; disque mince 0–10 Ga constant (mesuré : ~8 Ga, avec sursauts à 5,7, 1,9 et 1 Ga).
15. R0 = 8,2 kpc contre 8,277 kpc (GRAVITY 2022) ; vitesse totale du Soleil 245,0 km/s contre 249–251,5 km/s d'après le mouvement propre de Sgr A*.
16. Distance = 1/parallaxe sans point zéro (−17 µas) : ~1 %.
17. Critère « orbite fiable » sans test de binarité (`ruwe`, amplitude de vitesse radiale).
18. Régions HII rendues par un corps noir à 2 400 K (`etoiles_visibles.py:147`) : orange, alors que Hα + Hβ donnent un rose-rouge [Supposition].
19. Supernovæ (1,63 ± 0,46 par siècle) et novæ (26 ± 5 par an) absentes : événements possibles à vitesse de temps lente, comme modèle statistique.
20. Naines blanches absentes de la lumière des populations : négligeable en visible.
21. Liste des rencontres proches : à revoir après DR4 ; vérifier l'exclusion de UPM J0812-352.

---

## 8. Ce qui n'a pas été vérifié

- Les valeurs de durée de vie par masse (§ 1.2) et les coefficients de la relation masse initiale–finale (§ 1.5) viennent de ma mémoire des articles, pas d'une relecture des tables.
- R0 de GRAVITY 2022, la masse de M31*, Gaia BH1/BH2, Cyg X-1, et toutes les lignes marquées [Probable] : non relues aujourd'hui.
- L'article de Sawala et al. 2025 n'a été lu qu'à travers un compte rendu de presse.
- Le contenu exact de `all_source_rvs` dans DR4 (vitesses valides ou toutes sources) : à vérifier à la sortie.
- `natif/physique/film_v2.h`, `gaia_ciel.h` et la branche `etoiles-vie` n'ont pas été lus (le dernier n'est pas dans le clone).
- Les coefficients de rougissement « sRGB » du § 3.4 sont lus sur la loi de Cardelli de mémoire, pas recalculés.
- Aucun calcul n'a été lancé : les ordres de grandeur marqués « calcul fait ici » sont des calculs à la main.
