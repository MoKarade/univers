# Annexe 1 — Échelle système solaire : lois réelles, valeurs de référence, et ce que fait l'appli

Date de la recherche : 18 novembre 2026. Code lu : `/home/claude/univers` (branche `appli-pc`), en lecture seule. Aucun calcul GPU lancé, aucun fichier du dépôt modifié.

Labels : **[Certain]** = lu aujourd'hui dans la source ou dans le code ; **[Probable]** = publié, cité de mémoire, source connue ; **[Supposition]** = mon raisonnement ou mon calcul ; **[À vérifier]** = non vérifié.
Réserve de méthode : les pages web ont été lues à travers un outil qui résume ; un chiffre « [Certain] » venu du web veut dire « rendu par cet outil à partir de la page citée », pas « relu caractère par caractère dans le PDF ».

---

## 0. Résumé

- **La dynamique des planètes de l'appli est saine et bien bornée.** Dans 1550–2650 elle lit DE440 tel quel (`natif/src/ephemeride.h`) ; hors de cette plage elle intègre 13 corps (Wisdom-Holman, pas de 4 jours, relativité 1PN du Soleil, Lune en anneau) sur ±20 000 ans, puis une table sur ±10 Ma, puis rien. La constante GM☉ et la formule relativiste sont exactes. [Certain]
- **Ce qui manque dans la gravité est petit** : J2 du Soleil (2,218 × 10⁻⁷), effet Lense-Thirring, 339 des 343 astéroïdes de DE440, anneau de Kuiper, termes relativistes croisés entre planètes. Effet : quelques secondes d'arc sur 20 000 ans. Impact faible.
- **Le plus gros trou dynamique est la perte de masse du Soleil**, absente du calcul long. D'après mon calcul, elle décale la position de la Terre sur son orbite d'environ 0,6 rad à 1 Ma et de 9 tours à 10 Ma. La forme de l'orbite (e, ϖ) reste bonne ; la position sur l'orbite que donne la table au-delà d'environ 1 Ma est un modèle, pas une prédiction. [Supposition]
- **L'orientation de la Terre est fausse loin d'aujourd'hui** : pôle en fonction linéaire du temps (pas un cône de précession) et écart TDB−UTC figé à 69,184 s. À l'an 0 la Terre est tournée d'environ 44° de travers ; à ±20 000 ans le pôle n'a plus de sens. Impact fort pour les dates historiques, nul aujourd'hui. [Supposition, calcul d'après le code]
- **Le rendu est le domaine le plus éloigné du réel** : tous les astres sont des sphères parfaites à surface mate (Lambert), sans atmosphère. Saturne est aplatie de 9,8 % et Jupiter de 6,5 % ; la pleine Lune n'a pas de bord assombri ; l'ombre de la Terre sur la Lune est rouge cuivre et non noire. Impact fort sur « ce à quoi ça ressemble ».
- **L'éclat des planètes en point** suit une sphère de Lambert au lieu des courbes de phase mesurées (Mallama et Hilton 2018) : la Lune au quartier sort environ 3,8 fois trop brillante, les anneaux de Saturne (jusqu'à 0,8 mag) ne comptent pas.
- **Le Soleil ne vieillit pas** dans l'appli alors que le film court sur des milliards d'années : −21 % de luminosité il y a 3 Ga, +10 % par Ga à venir, géante rouge de 256 R☉ dans 7,59 Ga (Schröder et Smith 2008), puis naine blanche de 0,54 M☉.
- **Petits corps** : 1,58 million d'orbites képlériennes sans perturbation, montrées ±300 ans. Honnête et borné. Manquent les forces non gravitationnelles des comètes, leur chevelure et leurs queues, et tout le nuage d'Oort.
- **Chaos** : l'horizon mesuré par l'appli (45 Ma pour la position, 60 Ma pour l'orbite, 32 copies écartées de 15 m) est cohérent avec la littérature (temps de Lyapunov 5 Ma ; La2010 valable 50 Ma ; limite Cérès-Vesta 60 Ma). Le résultat de Laskar et Gastineau 2009 (1 % de déstabilisation de Mercure en 5 Ga) n'est pas représenté.
- **Raccourci disponible** : DE441 couvre −13 200 à +17 191 avec la vraie Lune. Il remplacerait la théorie de Meeus (±4 000 ans) et presque toute la plage du calcul direct.

---

## 1. Ce que l'appli fait aujourd'hui (carte du code)

| Sujet | Fichier | Ce qui est fait [Certain] |
|---|---|---|
| Planètes, Soleil, Lune, 1550–2650 | `natif/src/ephemeride.h` | Lecture directe de `de440.bsp` (segments SPK types 2 et 3, Tchebychev, ICRF), vitesse par dérivation. Rotation vers l'écliptique J2000 avec ε = 84 381,448″ (l.24). Hors plage : `false`. |
| Lunes des planètes | `natif/src/fenetre.cpp:126-128` | 17 fichiers JPL (`mar099s`, `jup365`, `sat441`, `nep097`, `plu060`, `ura184_part-3`, `ura116xl`, `sat415`, `nep104/105`, `jup347-349`, `sat455-459`). Hors de leur plage : lune cachée. |
| N corps hors DE440 | `natif/physique/nbody_noyau.h` | Soleil + 8 planètes (barycentres) + Pluton + Cérès, Vesta, Pallas, Hygie. Wisdom-Holman en coordonnées héliocentriques démocratiques, pas de 4 jours, relativité 1PN du Soleil (l.121-137), Lune moyennée en anneau (l.138-146). |
| Raccord et calage | `natif/physique/systeme_solaire.cpp:32-88` | Départ de l'état DE440 aux deux bornes ; vitesses ajustées par Newton pour retrouver DE440 400 ans à l'intérieur ; points de reprise tous les 20 ans ; ±20 000 ans (`fenetre.cpp:159`). |
| Temps long | `nbody_noyau.h:149-199`, `pipeline/gravite/build_long.js` | Table λ tous les 1 000 ans, (a, e, i, Ω, ϖ) tous les 10 000 ans, ±10 Ma, contrôlée contre La2004 sur l'excentricité (`compare_la2004.js`). |
| Chaos | `natif/src/chaos.h`, `natif/physique/essais/chaos_systeme_solaire.cpp` | 32 copies, Terre-Lune écartée de 15 m, 60 Ma ; e et ϖ de la Terre montrés, horizon 45 Ma (position) et 60 Ma (orbite). |
| Lune hors DE440 | `natif/physique/lune.h` | Meeus chap. 47 (ELP-2000/82 tronquée), précession UAI 1976, ±4 000 ans. |
| Orientation | `natif/src/orientation.h` | WGCCRE 2015 (Archinal et al. 2018), termes linéaires seulement, 11 astres. |
| Astéroïdes et comètes | `natif/src/asteroides*.h`, `natif/shaders/asteroides.vert` | Kepler à deux corps sur carte graphique, éléments JPL SBDB, e < 1 seulement, visibles à ±300 ans de l'époque (`simulation.h:824-829`). |
| Sondes | `natif/src/sondes.h`, `pipeline/natif/sondes.py:22-24` | Voyager 1 et 2, Pioneer 10 et 11, New Horizons ; vecteurs Horizons, interpolation de Hermite. |
| Rendu | `natif/shaders/sphere.frag`, `natif/src/spheres.h`, `points_planetes.h` | Sphère, Lambert, anneaux de Saturne avec ombres croisées, éclipse par un seul astre (disque solaire uniforme), lumières de nuit. Éclat en point : V(1,0) + phase de Lambert (`simulation.h:702-716`). |

Note : `natif/src/orbites_gpu.h` et `shaders/orbites_pas.comp` concernent les orbites des étoiles dans la Galaxie, pas le système solaire. Ils contiennent bien le terme d'énergie noire (`OP_KL = 0,00311179 (km/s)²/kpc²`, l.32 et l.38 du shader). À l'échelle du système solaire ce terme vaut a = H₀²Ω_Λ r ≈ 5 × 10⁻²⁵ m/s² à 1 UA, soit 10⁻²² fois l'attraction du Soleil : il est légitime de ne pas l'inclure ici, à condition de le dire. [Supposition, calcul]

---

## 2. Gravité : lois et valeurs de référence

### 2.1 Newton à N corps

a_i = Σ_{j≠i} G m_j (r_j − r_i) / |r_j − r_i|³. L'appli le fait exactement pour 13 corps + Soleil (`nbody_noyau.h:107-120`), avec le Soleil traité par un mouvement de Kepler exact (l.45-57). [Certain]

Intégrateur : Wisdom et Holman 1991 (AJ 102, 1528) ; coordonnées démocratiques de Duncan, Levison et Lee 1998 (AJ 116, 2067). [Probable] Pas de 4 jours, soit 22 pas par orbite de Mercure. Référence de comparaison : Abbot et al. 2023 utilisent 3,16 jours sur 5 Ga et montrent que cela suffit pour la statistique de Mercure. [Certain, résumé arXiv:2212.14844] La2004 utilise 5 × 10⁻³ an = 1,83 jour. [Probable]

### 2.2 Relativité générale

Loi complète (Einstein-Infeld-Hoffmann, 1PN, paramètres β = γ = 1), celle des éphémérides JPL (Park et al. 2021, éq. 27 ; Moyer 2003). Pour le seul Soleil, elle se réduit à :

a = (GM/(c² r³)) · [ (4GM/r − v²) r + 4 (r·v) v ]

C'est exactement la ligne 121-133 de `nbody_noyau.h`. [Certain]

Avance du périhélie par orbite : Δϖ = 6πGM / (c² a (1−e²)). Pour Mercure (a = 0,387098 UA, e = 0,20563, 415,2 orbites par siècle) : **42,98″/siècle**. [Supposition : recalculé aujourd'hui, 5,0185 × 10⁻⁷ rad par orbite]

| Contribution au périhélie de Mercure | Valeur | Source |
|---|---|---|
| Relativité (Schwarzschild) | 42,98″/siècle | calcul ci-dessus ; Park et al. 2017, AJ 153, 121 [Probable] |
| J2 du Soleil | ≈ +0,03″/siècle | Park et al. 2017 [Probable] |
| Lense-Thirring (rotation du Soleil) | ≈ −0,002″/siècle | Park et al. 2017 [Probable] |
| Planètes (newtonien) | ≈ 532″/siècle | [Probable] |

Constantes de l'appli : `kCAuDay = 173,1446326846693` (l.29). Avec c = 299 792,458 km/s et 1 UA = 149 597 870,7 km on trouve 173,14463267424. Écart relatif 6 × 10⁻¹¹ : sans effet, mais c'est une valeur d'ancienne unité astronomique. [Certain : calculé aujourd'hui]

Ce que l'appli ne fait pas : termes 1PN croisés entre planètes, Lense-Thirring. DE440 et INPOP21a incluent Lense-Thirring. [Certain : Park 2021 et INPOP21a, résumés]

### 2.3 Aplatissement du Soleil et des planètes

| Corps | J2 | Source |
|---|---|---|
| Soleil | (2,2180 ± 0,010) × 10⁻⁷, Lense-Thirring compris dans l'ajustement | INPOP21a, Fienga et al. 2021 [Certain, résumé] ; DE440 donne une valeur voisine [Probable ; non retrouvée aujourd'hui dans le texte de Park 2021] |
| Terre | 1,08263 × 10⁻³ ; J3 = −2,53 × 10⁻⁶ | EGM2008 / IERS 2010 [Probable] |
| Mars | 1,9566 × 10⁻³ | Konopliv et al. 2016 [Probable] |
| Jupiter | 14 696,5 × 10⁻⁶ ; J4 = −586,6 × 10⁻⁶ | Juno : Iess et al. 2018, Nature 555, 220 ; Durante et al. 2020 [Probable] |
| Saturne | 16 290,6 × 10⁻⁶ | Cassini : Iess et al. 2019, Science 364, eaat2965 [Probable] |
| Uranus | ≈ 3 510 × 10⁻⁶ | Jacobson 2014, AJ 148, 76 [Probable] |
| Neptune | ≈ 3 408 × 10⁻⁶ | Jacobson 2009, AJ 137, 4322 [Probable] |

Le J2 des planètes ne compte que pour leurs lunes et leurs anneaux (précession des nœuds et des périapses). Comme l'appli lit les lunes dans les fichiers JPL, il est déjà contenu dans les positions. Il redeviendrait nécessaire si l'on prolongeait les lunes hors des fichiers (§ 6). Le J2 du Soleil manque dans le calcul N corps : environ 0,03″/siècle sur Mercure, soit 6″ en 20 000 ans. [Supposition]

### 2.4 Astéroïdes et ceinture de Kuiper comme perturbateurs

- DE440 : 343 astéroïdes (environ 90 % de la masse de la ceinture principale), 30 objets de Kuiper individuels, plus un anneau de 36 masses égales à 44 UA. [Certain, résumé de Park 2021]
- INPOP21a : anneau de 500 objets transneptuniens, masse (0,0259 ± 0,0007) M⊕. [Certain, résumé]
- Masse de la ceinture principale ≈ 4,0 × 10⁻⁴ M⊕ ; ceinture de Kuiper ≈ 2 × 10⁻² M⊕ (Pitjeva et Pitjev 2018, Celest. Mech. Dyn. Astron. 130, 57). [Probable]
- Appli : 4 astéroïdes (Cérès, Vesta, Pallas, Hygie), aucun anneau. GM recalculés aujourd'hui depuis DE440 : Cérès 1,39645 × 10⁻¹³ et Vesta 3,85480 × 10⁻¹⁴ UA³/j², conformes à `nbody_donnees.h`. [Certain]

### 2.5 Perte de masse du Soleil (absente de l'appli)

- Rayonnement : L☉/c² = 3,828 × 10²⁶ / c² = 4,26 × 10⁹ kg/s = 6,8 × 10⁻¹⁴ M☉/an. Vent solaire : environ 2 × 10⁻¹⁴ M☉/an. Total ≈ **9 × 10⁻¹⁴ M☉/an**. [Supposition pour le calcul ; ordre de grandeur publié, Pitjeva et Pitjev 2012, Solar Syst. Res. 46, 78 : d(GM☉)/dt / GM☉ = (−6,3 ± 4,3) × 10⁻¹⁴ /an — Probable]
- Perte lente (adiabatique) : a ∝ 1/M, donc n ∝ M². Dérive de longitude : Δλ = n · (Ṁ/M) · t².

| Durée | Terre | Mercure |
|---|---|---|
| 20 000 ans | 2,3 × 10⁻⁴ rad (47″, 34 000 km) | 9 × 10⁻⁴ rad |
| 1 Ma | 0,57 rad (32°) | 2,3 rad |
| 10 Ma | 56 rad (9 tours) | 230 rad |

[Supposition : mon calcul]

Conséquence : la « table précalculée » donne λ jusqu'à ±10 Ma (`nbody_noyau.h:171-194`), contrôlée contre La2004 sur l'excentricité seulement. La forme et l'orientation des orbites ne sont presque pas touchées (les rapports de fréquences changent de 10⁻⁶). La position sur l'orbite, elle, dépend d'un terme absent. Deux issues : ajouter GM☉(t) au calcul long (une ligne dans `kepler` et `kick`), ou dire à l'écran que la position sur l'orbite au-delà d'environ 1 Ma est un modèle. À ma connaissance La2004 n'inclut pas non plus la perte de masse. [À vérifier]

### 2.6 Lune en anneau

`moonRing` (l.138-146) : anneau de rayon 384 400 km corrigé de (1 + 1,5 e²), d'après Quinn, Tremaine et Duncan 1991 (AJ 101, 2287). [Certain pour le code ; Probable pour la référence] La2004 et DE440 intègrent la Lune comme un corps. L'anneau est une bonne approximation pour les planètes à long terme. Le recul de la Lune (3,8 cm/an, soit 380 km en 10 Ma, 0,1 %) est sans effet sur ce terme. [Supposition]

---

## 3. Éphémérides, constantes, échelles de temps

### 3.1 Éphémérides de référence

| Éphéméride | Référence | Plage | Notes |
|---|---|---|---|
| DE440 | Park, Folkner, Williams, Boggs 2021, AJ 161, 105, DOI 10.3847/1538-3881/abd414 | 1550–2650 | Recommandée pour l'époque moderne. [Certain] |
| DE441 | même article | **−13 200 à +17 191** | Sans amortissement noyau-manteau de la Lune, pour pouvoir intégrer vers le passé. Écart avec DE440 : moins de 1 m pour les planètes sur 1 100 ans ; moins de 2 m pour la Lune sur 1970–2020, croissant le long de l'orbite au-delà. [Certain, résumé] |
| INPOP21a | Fienga, Deram, Di Ruscio, Viswanathan, Camargo, Bernus, Gastineau, Laskar 2021, Notes Sci. Tech. IMCCE S110 | données 1924–2020,56 | Écart avec DE440 : Jupiter ≈ 150 m ; Saturne jusqu'à ≈ 1 km hors Cassini ; Uranus et Neptune < 100 mas. [Certain, résumé] |
| EPM2021 | Pitjeva, Pavlov, Aksim, Kan 2021, Proc. IAU 15 (S364) | — | [Probable ; titre vu aujourd'hui, contenu non lu] |

Précision des mesures qui contraignent DE440 [Certain, résumé de Park 2021] : Mercure 0,7 m (MESSENGER) ; Vénus 8 m ; Mars 0,7 à 2 m ; Jupiter 13 m (Juno) ; Saturne 3 m (Cassini) ; Pluton 8 à 11 mas ; Lune 1,3 cm (laser récent).

Écart d'usage : l'appli n'utilise pas DE441 comme source de positions (seulement comme contrôle, `docs/plan-natif.md:46` et `:144`). DE441 donnerait la vraie Lune et les vraies planètes sur 30 000 ans, à la place de la théorie de Meeus (±4 000 ans) et de presque toute la plage du calcul direct (±20 000 ans). Taille du fichier : de l'ordre de 3 Go en deux parties. [Probable]

### 3.2 Constantes

| Constante | Valeur | Source | Appli |
|---|---|---|---|
| Unité astronomique | 149 597 870 700 m, exacte | UAI 2012, résolution B2 [Probable] | `phys.h:20`, `ephemeride.h:23` : conforme [Certain] |
| GM☉ (TDB) | 132 712 440 041,279419 km³/s² | DE440, table 2 [Certain, résumé] | `kGmSun = 2,9591220828411956e-4 UA³/j²` : recalculé aujourd'hui, identique à 16 chiffres [Certain] |
| Constante de Gauss | k = 0,01720209895 (k² = 2,959122082856e-4) | historique ; plus une constante de définition depuis 2012 [Probable] | utilisée pour a ↔ n des astéroïdes (`asteroides_catalogue.h:62`) et dans la table (`nbody_noyau.h:179`) ; écart relatif 5 × 10⁻¹², sans effet |
| GM Terre | 398 600,435507 km³/s² | DE440 [Certain, résumé] | conforme (8,8876924467e-10) |
| GM Lune | 4 902,800118 km³/s² | DE440 [Certain, résumé] | `lune.h:17` : écart relatif 10⁻¹⁰ |
| GM Jupiter (système) | 126 712 764,1 km³/s² | DE440 [Certain, résumé] | — |
| Rapport Terre/Lune | 81,3005678 ± 0,00000095 | INPOP21a [Certain, résumé] | — |
| Obliquité J2000 | 84 381,448″ (UAI 1976), celle des repères JPL ; 84 381,406″ (UAI 2006) | Park 2021 éq. 24 [Certain, résumé] ; Capitaine et al. 2003 [Probable] | 84 381,448″ : cohérent avec JPL [Certain] |
| Valeurs nominales du Soleil | R = 695 700 km ; L = 3,828 × 10²⁶ W ; S = 1 361 W/m² | UAI 2015, résolution B3 [Probable] | rayon 695 700 km (`simulation.h:268`) : conforme |

### 3.3 Échelles de temps

- TT = TAI + 32,184 s ; TDB = TCB − L_B (JD_TCB − T₀) × 86 400 + TDB₀ avec **L_B = 1,550519768 × 10⁻⁸** et T₀ = 2 443 144,5003725 ; L_G = 6,969290134 × 10⁻¹⁰. [Certain, résumé de Park 2021 § 2.3] TDB₀ = −6,55 × 10⁻⁵ s. [Probable] TDB et TT ne diffèrent que de 1,7 ms au plus (terme annuel). [Probable]
- **ΔT = TT − UT1** n'est pas constant. Ajustement parabolique : ΔT ≈ −320 + 32,5 · ((année − 1825)/100)² s (Stephenson, Morrison, Hohenkerk 2016, Proc. R. Soc. A 472, 20160404 ; mise à jour Morrison et al. 2021). [Probable pour la formule]

Appli : `kTdbMinusUtc = 69,184 s` appliqué à toute date, avec la mention « approximation assumée » (`simulation.h:36-38`). La rotation de la Terre est donc décalée de 15,04″ par seconde d'écart :

| Année | ΔT réel (parabole, sauf mention) | Erreur de rotation de la Terre |
|---|---|---|
| 1600 | ≈ 110 s (valeur tabulée, de mémoire ; la parabole ne vaut pas ici) | 0,2° |
| 1000 | ≈ 1 890 s | 7,6° |
| 0 | ≈ 10 500 s | 44° |
| −2000 | ≈ 47 000 s | ≈ 197° |
| 2650 | ≈ 1 890 s | 7,6° |

[Supposition : mon calcul à partir de la formule ci-dessus]

Les positions des astres ne sont pas touchées (elles sont en TDB). Seul le visage que la Terre présente au Soleil l'est : le lieu d'une éclipse historique tombe du mauvais côté du globe.

- Incohérence de raccord : dans DE440, `planetAt` ajoute 69,184 s (`simulation.h:446`) ; hors DE440, `jd = 2451545 + years × 365,25` n'ajoute rien (`simulation.h:487` et `:500`). L'argument de temps saute donc de 69 s à la borne, soit environ 2 000 km pour la Terre et 3 300 km pour Mercure. [Certain pour le code ; Supposition pour l'effet] Invisible à l'échelle du système. À confirmer avec `essai_continuite.cpp`, que je n'ai pas lu.

---

## 4. Terre et Lune

### 4.1 Marées

| Grandeur | Valeur | Source |
|---|---|---|
| Recul de la Lune (demi-grand axe) | **38,20 mm/an** | Pavlov, Williams, Suvorkin 2016, Celest. Mech. Dyn. Astron. 126, 61, arXiv:1606.08376 [Certain, résumé] |
| idem | 38,30 ± 0,08 mm/an | Williams et Boggs 2016, Celest. Mech. Dyn. Astron. 126, 89 [Probable] |
| Accélération de marée de la longitude | −25,90″/siècle² (Pavlov 2016) [Certain] ; −25,97 ± 0,05 (Williams et Boggs) [Probable] | |
| Excentricité lunaire | +1,48 × 10⁻¹¹ /an | Pavlov 2016 [Certain, résumé] |
| Allongement du jour, observé | +1,78 ± 0,03 ms/siècle (720 av. J.-C. – 2015) | Stephenson et al. 2016 [Probable] |
| Allongement du jour, marées seules | ≈ +2,3 ms/siècle ; la différence vient du rebond post-glaciaire et du couplage noyau-manteau | idem [Probable] |

Le taux actuel est anormalement fort (résonance des océans). Extrapolé, il donnerait une Lune âgée d'environ 1,5 Ga. Les modèles récents (Tyler 2021, Planet. Sci. J. 2, 70 ; Daher et al. 2021, JGR Planets 126 ; Farhat et al. 2022, A&A 665, L1) reconstruisent une dissipation variable dans le passé. [Probable ; références non relues aujourd'hui]

Appli : la théorie de Meeus contient les termes en T² des arguments de la Lune (`lune.h:35-39`), donc l'accélération de marée telle qu'ELP-2000/82 l'avait ajustée. [Certain pour le code] Précision de la série tronquée : environ 10″ en longitude et 4″ en latitude près d'aujourd'hui. [Probable] Elle se dégrade à ±4 000 ans. La borne est cohérente avec l'en-tête du fichier. La distance moyenne de la Lune ne change pas dans l'appli au-delà de la plage : 38 mm/an donne 3 800 km en 100 Ma (1 %), donc invisible avant environ 100 Ma. [Supposition]

### 4.2 Précession, nutation

| Grandeur | Valeur | Source |
|---|---|---|
| Précession générale en longitude | 5 028,796195″/siècle (période ≈ 25 772 ans) | UAI 2006 : Capitaine, Wallace, Chapront 2003, A&A 412, 567 [Probable] |
| Variation de l'obliquité | −46,836769″/siècle | idem [Probable] |
| Nutation principale (18,6 ans) | Δψ = 17,2064″ ; Δε = 9,2052″ | UAI 2000A : Mathews, Herring, Buffett 2002, JGR 107, B4 [Probable] |
| Précession à long terme | valable ±200 000 ans | Vondrák, Capitaine, Wallace 2011, A&A 534, A22 [Probable] |
| Obliquité et précession sur des Ma | La2004, solution (ε, ψ) ; obliquité entre 22,1° et 24,5° sur le dernier Ma | Laskar et al. 2004, A&A 428, 261 [Probable] |

Appli : `orientation.h:30` — Terre : α₀ = 0 − 0,641 T ; δ₀ = 90 − 0,557 T ; W = 190,147 + 360,9856235 d. C'est le modèle WGCCRE à basse précision : pôle fonction linéaire du temps, pas de nutation. [Certain]

- Dans 1550–2650 : erreur inférieure à 0,3°. [Supposition]
- Hors DE440, la même fonction est appelée (`spheres.h:272`) alors que les planètes sont calculées jusqu'à ±20 000 ans. À T = 200 siècles, δ₀ = −21° : le pôle « dérive » en ligne droite au lieu de tourner sur un cône de 23,4° autour du pôle de l'écliptique. Les saisons, le terminateur et les lumières de nuit sont faux au-delà de 2 à 3 millénaires. [Supposition : calcul d'après le code]
- `lune.h:20-28` contient déjà une précession UAI 1976 rigoureuse en matrices ; le rendu de la Terre ne s'en sert pas.

Correctif naturel : précession de Vondrák 2011 (une dizaine de termes périodiques, ±200 000 ans), puis table d'obliquité et de précession de La2004 au-delà, avec un horizon affiché.

### 4.3 Libration de la Lune

- Librations optiques : ±7,9° en longitude (excentricité), ±6,7° en latitude (5,145° d'inclinaison de l'orbite + 1,54° d'inclinaison de l'équateur lunaire sur l'écliptique) ; 59 % de la surface visible depuis la Terre. Librations physiques : environ 0,03°. [Probable]
- Modèle WGCCRE de la Lune : α₀ = 269,9949 + 0,0031 T − 3,8787 sin E1 … ; δ₀ = 66,5392 + 0,0130 T + 1,5419 cos E1 … ; W = 38,3213 + 13,17635815 d − 1,4 × 10⁻¹² d² + 3,5610 sin E1 … (13 arguments E1 à E13). [Probable]

Appli : `orientation.h:31` garde les seuls termes linéaires, et le dit en tête de fichier. [Certain] Conséquence : la libration en longitude sort naturellement (rotation uniforme + orbite réelle de DE440). Le pôle lunaire est figé au lieu de précesser en 18,6 ans (loi de Cassini) : erreur jusqu'à 1,5° sur le pôle et 3,6° sur le méridien. Pour la précision maximale, le NAIF publie l'orientation intégrée de la Lune (noyau binaire PCK de DE440, repère des axes principaux). [Probable]

---

## 5. Orientation des autres corps (WGCCRE)

- Dernier rapport publié : **Archinal et al. 2018**, « Report of the IAU Working Group on Cartographic Coordinates and Rotational Elements: 2015 », Celest. Mech. Dyn. Astron. 130, 22, DOI 10.1007/s10569-017-9805-5 ; correction 2019, vol. 131, 12, DOI 10.1007/s10569-019-9925-1. [Certain : rapport triennal 2021-2024 du groupe, lu aujourd'hui]
- Il n'existe pas de « rapport 2023 » publié. D'après ce rapport triennal, la version suivante était en préparation pour 2024 ou 2025, avec des mises à jour à l'étude pour la Lune et pour Mars (Konopliv et al. 2016 ou Yseboodt et al. 2023, environ 100 m d'écart en longitude). [Certain, résumé] Parution depuis : [À vérifier].
- Appli : 11 astres, coefficients contrôlés contre `pck00011.tpc` par `pipeline/natif/controle_orientation.py`. [Certain pour l'en-tête du fichier ; contrôle non rejoué]
- Points d'attention [Probable] :
  - Jupiter, Saturne, Uranus, Neptune : la rotation du WGCCRE est celle du champ magnétique (Système III), pas celle des nuages. Les bandes de Jupiter dérivent par rapport à ce repère (Système I : 877,90°/j ; Système II : 870,27°/j ; Système III : 870,536°/j). Une carte fixe collée au Système III est une convention.
  - Saturne : 810,7939024°/j est la période radio de Voyager (10 h 39 min 22 s). La rotation interne déduite de la sismologie des anneaux vaut 10 h 33 min 38 s (Mankovich et al. 2019, ApJ 871, 1).
  - Les termes de nutation de Mars, Jupiter et Neptune sont absents : moins de 1°.
  - Les lunes (Io, Europe, Titan…) n'ont pas d'éléments dans la table de l'appli. À vérifier dans `spheres.h` : sans orientation, la rotation synchrone n'est pas rendue.

---

## 6. Lunes et anneaux

### 6.1 Catalogue

JPL SSD, « Planetary Satellite Discovery Circumstances » (https://ssd.jpl.nasa.gov/sats/discovery.html), lu aujourd'hui : Mars 2, Jupiter 115, Saturne 293, Uranus 29, Neptune 16, Pluton 5, soit **460** lunes de planètes et de Pluton, 461 avec la Lune. [Certain, résumé ; la date « dernière mise à jour » de la page est ambiguë]

Appli : seules les lunes ayant un fichier d'éphémérides chargé sont montrées, et seulement dans la plage de ce fichier (`simulation.h:314-360`). C'est honnête. Les plages sont courtes : quelques siècles autour d'aujourd'hui selon les fichiers. [Probable ; à lire dans les fichiers]

### 6.2 Dynamique à connaître si l'on prolonge les lunes

- Résonance de Laplace : λ_Io − 3 λ_Europe + 2 λ_Ganymède = 180°. [Probable]
- Théories analytiques, valables des siècles à des millénaires : L1.2 pour les galiléens (Lainey et al. 2004, A&A 420, 1171) ; TASS 1.7 pour Saturne (Vienne et Duriez 1995, A&A 297, 588) ; GUST86 pour Uranus (Laskar et Jacobson 1987, A&A 188, 212). [Probable]
- Migrations de marée : Titan s'éloigne de 11,3 ± 2,0 cm/an (Lainey et al. 2020, Nature Astronomy 4, 1053). Phobos descend d'environ 1,8 cm/an et se disloquera en anneau d'ici 20 à 40 Ma (Black et Mittal 2015, Nature Geoscience 8, 913). Triton, rétrograde, descend sur des Ga. [Probable]
- Voie « modèle signalé » : éléments moyens JPL (page « Planetary Satellite Mean Elements ») avec précession du nœud et du périapse due au J2 de la planète et au Soleil. Cela donne des lunes plausibles sur 10³ à 10⁴ ans, avec une phase orbitale qui se perd.

### 6.3 Anneaux

| Anneau de Saturne | Rayons (km du centre) |
|---|---|
| D | 66 900 – 74 500 |
| C | 74 658 – 92 000 |
| B | 92 000 – 117 580 |
| Division de Cassini | 117 580 – 122 170 |
| A | 122 170 – 136 775 |
| F | ≈ 140 180 |

[Probable : fiche NASA « Saturnian Rings Fact Sheet »]

- Appli : image radiale de 72 650 à 140 150 km, calée sur la division de Cassini et le bord de l'anneau A (`spheres.h:31-34`) : cohérent. [Certain pour le code]
- Rendu : opacité et couleur selon le rayon, ombre de la planète sur les anneaux et des anneaux sur la planète (`sphere.frag`). Manquent [Supposition, par lecture du shader] :
  - la dépendance à l'angle de phase (les anneaux sont très brillants en rétrodiffusion, effet d'opposition, et l'anneau F et les anneaux ténus brillent en diffusion avant) ;
  - la face non éclairée (lumière transmise, plus sombre et inversée : l'anneau B opaque y est noir) ;
  - la lumière de Saturne renvoyée sur les anneaux ;
  - l'ombre de la planète prise comme un cylindre de rayon moyen (ni aplatissement ni pénombre).
- Masse des anneaux de Saturne : (1,54 ± 0,49) × 10¹⁹ kg ≈ 0,4 masse de Mimas ; âge probable 10 à 100 Ma (Iess et al. 2019). [Probable] Sur les durées du film, les anneaux n'existaient sans doute pas il y a 3 Ga et auront disparu dans quelques centaines de Ma (« pluie d'anneaux », O'Donoghue et al. 2019, Icarus 322, 251). [Probable]
- Non dessinés : anneaux de Jupiter, d'Uranus (anneau ε à 51 149 km, étroit, sombre) et de Neptune (Adams, 62 932 km). [Probable]

### 6.4 Forme des planètes

| Corps | Rayon équatorial (km) | Rayon polaire (km) | Aplatissement |
|---|---|---|---|
| Terre | 6 378,137 | 6 356,752 | 1/298,257 |
| Mars | 3 396,19 | 3 376,20 | 0,00589 |
| Jupiter | 71 492 | 66 854 | **0,0649** |
| Saturne | 60 268 | 54 364 | **0,0980** |
| Uranus | 25 559 | 24 973 | 0,0229 |
| Neptune | 24 764 | 24 341 | 0,0171 |

[Probable : Archinal et al. 2018, table 4 ; niveau 1 bar pour les géantes]

Appli : sphères de rayon moyen (`simulation.h:73-83`, `sphere.frag`). [Certain] Saturne est visiblement ovale dans la réalité (10 %) : écart net à l'œil. Correctif : intersection rayon-ellipsoïde dans le shader (changement d'échelle le long du pôle, déjà connu via `rot2`).

---

## 7. Petits corps

### 7.1 Astéroïdes

- Sources : Minor Planet Center (MPCORB) et JPL Small-Body Database. L'appli lit le SBDB en pleine précision (`pipeline/natif/asteroides_jpl.py:36-38`) : environ 1,58 million d'orbites (commentaire `simulation.h:826`). [Certain pour le code]
- Appli : orbite képlérienne fixe par objet, à une époque commune. Contrôle écrit dans le code : moins de 100 000 km d'écart avec Horizons après 154 jours (`asteroides_catalogue.h:68`). Affichage ±300 ans. [Certain]
- Ce que Kepler seul ignore [Supposition] :
  - la précession séculaire due à Jupiter (périhélies de la ceinture : quelques dizaines de ″/an, donc 1 à 2° par siècle, soit environ 0,05 UA à 2,7 UA après un siècle) ;
  - les résonances : troyens de Jupiter (libration d'environ 150 ans), Hildas (3:2), lacunes de Kirkwood. Avec des éléments osculateurs figés, les essaims troyens se défont en quelques siècles. La borne de 300 ans est donc bien choisie pour l'aspect d'ensemble, large pour un objet désigné.
- Précision : le shader calcule M = M₀ + n·jours en simple précision (`asteroides.vert:18`). À 300 ans, M ≈ 400 rad, pas flottant ≈ 3 × 10⁻⁵ rad, soit environ 10 000 km : sous le seuil visible. [Supposition]

### 7.2 Yarkovsky et YORP

- Yarkovsky : dérive du demi-grand axe par recul thermique, da/dt ∝ cos(obliquité)/D ; typiquement 10⁻⁴ à 10⁻³ UA/Ma pour un objet d'un kilomètre. Bennu : −284,6 ± 0,2 m/an (Farnocchia et al. 2021, Icarus 369, 114594). [Probable] Catalogue de 247 détections : Greenberg et al. 2020, AJ 159, 92, arXiv:1708.05513. [Certain pour le titre et l'arXiv]
- Dans les orbites JPL : paramètre A2, accélération transverse a_t = A2 (1 UA/r)². [Probable]
- YORP : couple thermique qui change la rotation ; (54509) YORP accélère de 2,0 × 10⁻⁴ °/jour² (Lowry et al. 2007 et Taylor et al. 2007, Science 316). [Probable]
- Pour l'appli : sans effet visible sur ±300 ans. Ces effets comptent pour l'origine des géocroiseurs et l'étalement des familles sur 10⁸ à 10⁹ ans, donc seulement si l'on voulait montrer une ceinture « vivante » sur les durées du film (modèle).

### 7.3 Comètes

- Forces non gravitationnelles (Marsden, Sekanina, Yeomans 1973, AJ 78, 211) : a = g(r) (A1 r̂ + A2 t̂ + A3 n̂), avec g(r) = α (r/r₀)^−m [1 + (r/r₀)^n]^−k, r₀ = 2,808 UA, m = 2,15, n = 5,093, k = 4,6142, α = 0,1113. [Probable] Pour Halley, le passage au périhélie se décale d'environ 4 jours par révolution. [Probable]
- Appli : comètes en Kepler pur, e < 1 seulement ; les hyperboliques et paraboliques sont écartées et comptées (`asteroides_jpl.py:9-11` et `:55`). Affichées comme des points de la teinte des astéroïdes, l'éclat des comètes (M1) étant rangé à la place de H. [Certain pour le filtre]
- Écart d'aspect, le plus visible : une comète n'est pas un point. Chevelure de 10⁴ à 10⁵ km ; queue de poussière courbée (jusqu'à 10⁷–10⁸ km) ; queue d'ions rectiligne à l'opposé du Soleil. Éclat : m = M1 + 5 log Δ + K1 log r, avec K1 autour de 10 (paramètres M1 et K1 du SBDB). [Probable] Rien de cela n'est rendu.
- Objets interstellaires : 1I/ʻOumuamua (e = 1,20), 2I/Borisov (e = 3,36), 3I/ATLAS (découvert en juillet 2025, e ≈ 6). [Probable] Tous exclus par le filtre e < 1. Une branche hyperbolique de l'équation de Kepler suffirait.

### 7.4 Au-delà de Neptune, héliosphère, nuage d'Oort

- Ceinture de Kuiper : classiques de 42 à 48 UA, résonants (3:2, 2:1), disque épars ; masse ≈ 0,02 M⊕ (§ 2.4). Les planètes naines (Éris, Hauméa, Makémaké, Gonggong, Sedna) sont dans le SBDB, donc présentes comme points. [Probable]
- Héliopause : traversée par Voyager 1 à 121,6 UA (août 2012) et par Voyager 2 à 119 UA (novembre 2018). [Probable] L'appli a les deux sondes mais pas la frontière.
- Nuage d'Oort (jamais observé directement : **modèle**) : bord interne à 2 000–5 000 UA, bord externe à 50 000–100 000 UA et plus ; 10¹¹ à 10¹² noyaux de plus d'un kilomètre ; quelques M⊕. Rayon de marée du Soleil dans la Galaxie : environ 1 pc. [Probable] Moteurs : marée galactique (surtout verticale, densité locale ≈ 0,1 M☉/pc³) et passages d'étoiles.
- Passages d'étoiles :
  - **Gliese 710** : dans environ 1,29 Ma, à environ 0,05–0,07 pc (10 000 à 14 000 UA), à l'intérieur du nuage d'Oort (Bailer-Jones et al. 2018, A&A 616, A37, Gaia DR2 ; de la Fuente Marcos 2022, Gaia DR3). [Probable ; chiffres exacts À vérifier]
  - Étoile de Scholz : passée il y a environ 70 000 ans à environ 0,25 pc (Mamajek et al. 2015, ApJ 800, L17). [Probable]
  - Fréquence : environ 20 étoiles par Ma à moins de 1 pc (Bailer-Jones et al. 2018). [Probable]
  - Effet sur les planètes : les passages réduisent l'horizon de prédiction de l'orbite terrestre (Kaib et Raymond 2024, ApJL 962, L28 ; cas de HD 7977 il y a 2,8 Ma) et augmentent le risque d'instabilité sur 5 Ga (Kaib et Raymond 2025, Icarus). [Probable ; chiffres À vérifier]
- Pour l'appli : elle possède déjà les étoiles Gaia et leurs orbites galactiques. Montrer Gliese 710 qui traverse le nuage d'Oort dans 1,3 Ma serait du mesuré pour l'étoile et du modèle pour le nuage. C'est le pont naturel entre l'échelle du système solaire et celle de la Galaxie.

### 7.5 Sondes

Appli : 5 sondes en vecteurs Horizons, jusqu'à 2100, hors plage : absentes. [Certain] Les trajectoires Horizons contiennent déjà les survols, donc la physique réelle. Au-delà de 2100, une extrapolation hyperbolique héliocentrique serait un modèle correct (Voyager 1 : environ 3,6 UA/an). [Probable] Sondes absentes : Parker Solar Probe, Juno, JWST, Europa Clipper, JUICE, BepiColombo, Lucy, Psyche.

---

## 8. Chaos du système solaire

| Résultat | Valeur | Source |
|---|---|---|
| Temps de Lyapunov des planètes internes | ≈ 5 Ma | Laskar 1989, Nature 338, 237 [Probable] ; confirmé par Mogavero, Hoang, Laskar 2023, Phys. Rev. X 13, 021018, DOI 10.1103/PhysRevX.13.021018 [Certain, résumé arXiv:2305.01683] |
| Validité des solutions orbitales | La2004 : ≈ 40 Ma ; La2010 : ≈ 50 Ma | Laskar et al. 2004, A&A 428, 261 ; Laskar, Fienga, Gastineau, Manche 2011, A&A 532, A89 [Probable] |
| Limite absolue | ≈ 60 Ma, par les rencontres chaotiques Cérès-Vesta | Laskar, Gastineau, Delisle, Farrés, Fienga 2011, A&A 532, L4 [Probable] |
| Contrainte géologique | solution ZB18a, calée sur des sédiments jusqu'à ≈ 58 Ma | Zeebe et Lourens 2019, Science 365, 926 [Probable] |
| **Déstabilisation de Mercure** | 2 501 solutions sur 5 Ga ; **≈ 1 %** avec forte hausse de l'excentricité de Mercure (collision avec Vénus ou le Soleil) ; une solution, vers 3,34 Ga, déstabilise toutes les planètes internes, avec collisions possibles de Mercure, Mars ou Vénus avec la Terre | Laskar et Gastineau 2009, Nature 459, 817, DOI 10.1038/nature08096 [Certain, résumé] |
| Sans relativité | plus de la moitié des solutions déstabilisées | Laskar 2008, Icarus 196, 1 [Probable] |
| Reproduction indépendante | 9 601 intégrations de 5 Ga, pas de 3,16 j ; le logarithme de la fréquence des instabilités de Mercure croît linéairement entre 1,3 et 5 Ga | Abbot et al. 2023, ApJ 944, 190, DOI 10.3847/1538-4357/acb6ff [Certain, résumé] |
| Diffusion | un modèle diffusif simple sous-estime la probabilité d'un facteur 3 à 10 000 avant 5 Ga ; modèle sous-diffusif valable de 1 à 40 Ga | Abbot et al., arXiv:2306.11870 [Certain, résumé] |
| Expériences numériques | Hoang, Mogavero, Laskar, « Long-term instability of the inner Solar System: numerical experiments », arXiv:2205.04170 | [Certain pour le titre ; contenu non lu] |

Appli : 32 copies, écart de 15 m, 60 Ma, échantillon tous les 10 000 ans ; horizon de 45 Ma pour la position sur l'orbite et de 60 Ma pour l'orbite (`chaos.h:22-23`). [Certain pour le code] Cohérent avec La2010 et la limite Cérès-Vesta. L'appli inclut justement Cérès et Vesta, donc la bonne source de chaos.

Réserves :
1. L'écart entre copies mesure la sensibilité aux conditions initiales, pas l'erreur de modèle. Pour la position sur l'orbite, l'erreur de modèle domine bien avant 45 Ma (perte de masse solaire, § 2.5). L'horizon de 45 Ma est donc optimiste pour λ. Il reste raisonnable pour e et ϖ. [Supposition]
2. Seules e et ϖ de la Terre sont montrées, avec a = 1 UA et le plan de l'écliptique. C'est dit dans le fichier.
3. Le fait le plus frappant de la littérature n'est pas représenté : sur 5 Ga, environ 1 % des avenirs possibles déstabilisent Mercure. L'intégrateur à pas fixe de l'appli ne gère pas les rencontres proches. Pour le montrer, il faudrait un pas adaptatif ou un intégrateur hybride (famille MERCURIUS, TRACE, de REBOUND), ou citer le résultat publié sans le recalculer.

---

## 9. Évolution du Soleil et sort de la Terre

| Époque | État du Soleil | Source |
|---|---|---|
| Séquence principale | L(t) = L☉ / [1 + 0,4 (1 − t/t☉)], t☉ = 4,57 Ga : 70 % au départ, 79 % il y a 3 Ga, +1 % par 110 Ma, +10 % dans 1,1 Ga | Gough 1981, Solar Physics 74, 21 [Probable] ; le 79 % est mon calcul |
| +1,0 à 1,5 Ga | perte de l'eau par effet de serre humide puis emballement | Kasting 1988, Icarus 74, 472 ; Leconte et al. 2013, Nature 504, 268 ; Wolf et Toon 2015, JGR Atmos. 120, 5775 [Probable] |
| ≈ +1,1 Ga | fin de l'atmosphère riche en oxygène (1,08 ± 0,14 Ga) | Ozaki et Reinhard 2021, Nature Geoscience 14, 138 [Probable] |
| ≈ +5,4 Ga | fin de la séquence principale ; sous-géante | Schröder et Smith 2008 [Probable] |
| **+7,59 Ga** | sommet de la branche des géantes rouges : R ≈ 256 R☉ (1,2 UA), L ≈ 2 730 L☉, T ≈ 2 600 K ; **0,332 M☉ perdue** sur cette branche | Schröder et Smith 2008, MNRAS 386, 155, arXiv:0801.4031 [Certain pour 7,59 Ga et 0,332 M☉, résumé ; Probable pour R, L, T] |
| Sort de la Terre | l'orbite s'élargit mais le freinage de marée et la traînée l'emportent : **engloutie**. Rayon initial minimal pour survivre : 1,15 UA | idem [Certain, résumé] |
| Ensuite | flash de l'hélium, branche asymptotique (R ≈ 149 R☉, L ≈ 2 090 L☉), nébuleuse planétaire faible ou absente, naine blanche de 0,5405 M☉ | idem [Probable] |

Orbites : perte de masse lente, donc a × M constant. À la fin, les orbites survivantes sont multipliées par 1/0,54 ≈ 1,85 (Jupiter à ≈ 9,6 UA, Neptune à ≈ 56 UA). [Supposition : calcul]

Appli : Soleil constant. `kSunAbsMag = 4,83`, B−V = 0,653 (`commun.h:344`), carte `8k_sun.jpg`, rayon 695 700 km, quelle que soit la date. [Certain] `vieillissement.h` ne vieillit que les étoiles du modèle. [Certain] Les planètes disparaissent au-delà de ±10 Ma (60 Ma pour l'orbite de la Terre), donc l'incohérence ne touche que le Soleil vu comme étoile. Aux dates du film (−3 Ga jusqu'à la fusion), son éclat et sa couleur devraient changer : −0,26 mag il y a 3 Ga ; géante rouge puis naine blanche après +7,6 Ga. Voie simple : une piste d'évolution solaire (MIST 1 M☉, Z☉, déjà utilisée par le dépôt pour les populations) donnant L, T_eff, R en fonction du temps, signalée « modèle ».

---

## 10. Lumière : albédos, phases, éclipses, réfraction

### 10.1 Albédos

| Corps | Albédo géométrique (V) | Albédo de Bond | Source |
|---|---|---|---|
| Mercure | 0,142 | 0,088 | Mallama, Krobusek, Pavlov 2017, Icarus 282, 19, arXiv:1609.05048 |
| Vénus | 0,689 | 0,76 | Mallama 2017 ; Haus et al. 2016, Icarus 272, 178 |
| Terre | 0,434 (Mallama 2017) ; 0,24 d'après Wikipédia (fiche NASA 2024 et Robinson 2026) | 0,294 – 0,306 | **désaccord entre sources** : [À vérifier] |
| Lune | 0,12 | 0,11 | fiche NASA |
| Mars | 0,170 | 0,25 | Mallama 2017 ; fiche NASA |
| Jupiter | 0,538 | 0,503 | Mallama 2017 ; Li et al. 2018, Nature Communications 9, 3709 |
| Saturne | 0,499 | 0,342 | Mallama 2017 ; Hanel et al. 1983 |
| Uranus | 0,488 | 0,300 | Mallama 2017 ; Pearl et al. 1990 |
| Neptune | 0,442 | 0,290 | Mallama 2017 ; Pearl et al. 1991 |
| Pluton | 0,44 – 0,61 | ≈ 0,4 | Verbiscer et al. 2022 [À vérifier] |
| Encelade | ≈ 1,38 | 0,81 | Verbiscer et al. 2007 ; Howett et al. 2010 |

[Certain : tableau de Wikipédia « Geometric albedo » lu aujourd'hui, résumé ; l'attribution ligne par ligne des sources est celle de l'outil de lecture, donc Probable]

Lien entre H et l'albédo : D (km) = 1 329 · 10^(−H/5) / √p. [Probable]

### 10.2 Courbes de phase et magnitudes

Référence : **Mallama et Hilton 2018**, « Computing apparent planetary magnitudes for The Astronomical Almanac », Astronomy and Computing 25, 10, arXiv:1808.01973 ; code source public. [Certain pour le titre, les auteurs et l'arXiv ; revue : Probable] L'article ajoute des termes pour la rotation de Mars, la latitude sub-solaire d'Uranus et la variation séculaire de Neptune. [Certain, résumé] Coefficients ci-dessous cités de mémoire : [À vérifier] avant emploi, à reprendre dans le code public de l'article.

| Planète | V(1,0) + terme de phase (α en degrés) |
|---|---|
| Mercure | −0,613 + 6,328 × 10⁻² α − 1,6336 × 10⁻³ α² + … (ordre 6) |
| Vénus | −4,384 − 1,044 × 10⁻³ α + 3,687 × 10⁻⁴ α² − 2,814 × 10⁻⁶ α³ + 8,938 × 10⁻⁹ α⁴ (α < 163,7°), puis remontée en diffusion avant |
| Terre | −3,99 − 1,060 × 10⁻³ α + 2,054 × 10⁻⁴ α² |
| Mars | −1,601 + 0,02267 α − 0,0001302 α² (α ≤ 50°) + effets de rotation |
| Jupiter | −9,395 − 3,7 × 10⁻⁴ α + 6,16 × 10⁻⁴ α² (α ≤ 12°) |
| Saturne | −8,914 − 1,825 sin β + 0,026 α − 0,378 sin β · e^(−2,25 α), β = inclinaison des anneaux |
| Uranus | −7,110 + termes de latitude |
| Neptune | −7,00 après 2000 |

Appli : m = H + 5 log₁₀(r d) − 2,5 log₁₀ φ(α), avec φ de Lambert = [sin α + (π − α) cos α]/π (`simulation.h:702-716`), H lu dans les fiches NASA. Marqué « approximation assumée ». [Certain]

Écarts [Supposition, d'après valeurs Probables] :
- **Lune** : au quartier (α = 90°), Lambert donne 31,8 % de la pleine Lune ; la réalité environ 8 % (−10,0 contre −12,7 mag). La Lune de l'appli est environ 3,8 fois trop brillante au quartier. Près de la pleine Lune, l'effet d'opposition (+40 % dans les 4 derniers degrés) est absent.
- **Mercure** : comme la Lune (régolithe), Lambert surestime les croissants.
- **Saturne** : les anneaux ajoutent jusqu'à 0,83 mag (β = 27°), absents de l'éclat en point.
- **Vénus** : en fin croissant, la diffusion avant fait remonter l'éclat ; non rendu.
- Planètes géantes vues de la Terre (α ≤ 12°) : écart négligeable.

### 10.3 Surfaces (shader)

`sphere.frag:76` : loi de Lambert pour tous les astres. [Certain]
- Lune, Mercure, astéroïdes, lunes glacées : régolithe, loi de Lommel-Seeliger ou de Hapke (Hapke 2012, *Theory of Reflectance and Emittance Spectroscopy*, Cambridge). La pleine Lune est presque uniformément brillante jusqu'au bord. Avec Lambert le bord s'assombrit : la pleine Lune de l'appli a l'air d'une bille, pas d'un disque. [Probable]
- Géantes gazeuses : bord assombri, loi de Minnaert I ∝ μ₀^k μ^(k−1) avec k de 0,9 à 1,0 selon la bande. Lambert est acceptable. [Probable]
- Terre : aucune atmosphère dans le shader. Manquent la diffusion de Rayleigh (liseré bleu, bord voilé), le crépuscule (terminateur étalé sur environ 18°, alors que le shader n'adoucit que les lumières de nuit, l.97), les nuages (la carte de jour est sans nuages, ou avec des nuages figés), le reflet du Soleil sur l'océan. [Certain pour l'absence ; Supposition pour l'importance]
- Vénus et Titan : atmosphères épaisses qui prolongent les cornes du croissant. Mars : voile de poussière. Non rendus.
- Soleil : assombrissement I(μ)/I(1) = 1 − u (1 − μ), u = 0,6 (`sphere.frag:74`). Correct dans le vert. En réalité u dépend de la couleur (≈ 0,8 dans le bleu, ≈ 0,5 dans le rouge), donc le bord est plus rouge. Référence : Neckel et Labs 1994, Solar Physics 153, 91 (polynômes d'ordre 5). [Probable] Taches, granulation, couronne : absents.

### 10.4 Éclipses

- Géométrie de l'appli : part du disque solaire (uniforme) cachée par un seul astre, aire commune de deux cercles (`sphere.frag:34-43` et `:85-93`). Ombre et pénombre géométriques correctes. Contrôle `essai_eclipse.cpp` : 6 éclipses de 2026 à 2028 à moins de 1,5° du catalogue d'Espenak et Meeus. [Certain pour le code]
- Écarts :
  - **Éclipse de Lune** : l'ombre de la Terre n'est pas noire. L'atmosphère réfracte et rougit la lumière vers l'ombre ; la Lune reste visible, rouge cuivre, 10⁴ à 10⁶ fois plus faible (échelle de Danjon L = 0 à 4). L'ombre est agrandie d'environ 2 % (règle de Chauvenet 1/50, ou de Danjon 1/85). [Probable] L'appli donne une Lune noire : écart d'aspect fort.
  - Éclipse de Soleil vue de l'espace : la tache d'ombre est bien rendue. La couronne solaire (ce qu'on voit en totalité depuis le sol) n'existe pas dans l'appli. [Supposition]
  - Disque solaire uniforme dans le calcul de l'ombre (dit dans le shader) : erreur de quelques % dans la pénombre.
  - Un seul astre occultant (`ombre`) : pas de double ombre des lunes galiléennes sur Jupiter.
  - Terre sphérique de rayon moyen dans le contrôle : aplatissement ignoré, environ 0,1° sur le lieu.
  - Lumière instantanée : pas de temps de lumière (499 s du Soleil, 1,28 s de la Lune) ni d'aberration (20,5″). Choix défendable pour une vue « de l'instant ». Le décalage sur le lieu d'une éclipse est de quelques minutes d'arc, sous la tolérance de 1,5° de l'essai. [Supposition]

### 10.5 Réfraction atmosphérique

- À l'horizon : ≈ 34′ en conditions standard (1 010 hPa, 10 °C). Formule de Bennett 1982 (J. Navigation 35, 255) : R = cot(h + 7,31/(h + 4,4)) minutes d'arc, h en degrés, facteur (P/1010) · (283/T). [Probable] Le Soleil à l'horizon est aplati d'environ 6′ en hauteur.
- Extinction : ≈ 0,2 mag par masse d'air en V en bon site ; rougissement du Soleil couchant. [Probable]
- Appli : pas de vue depuis le sol d'une planète, donc rien. À prévoir seulement si un mode « depuis la Terre » est ajouté.

---

## 11. Écarts avec l'appli, classés par impact sur le réalisme

### Fort

1. **Éclipse de Lune noire, astres sans atmosphère** (`natif/shaders/sphere.frag:76-93`). Réalité : ombre rouge cuivre, liseré bleu de la Terre, crépuscule. § 10.3, § 10.4.
2. **Orientation de la Terre loin d'aujourd'hui** (`natif/src/orientation.h:30`, `natif/src/simulation.h:38`). Pôle linéaire (faux au-delà de 2 à 3 millénaires, absurde à ±20 000 ans) et ΔT figé (44° d'erreur à l'an 0). Correctif : précession de Vondrák 2011 et parabole de ΔT de Stephenson 2016. § 3.3, § 4.2.
3. **Planètes géantes sphériques** (`natif/src/simulation.h:73-83`). Saturne aplatie de 9,8 %, Jupiter de 6,5 %. § 6.4.
4. **Surface de la Lune en Lambert** : pleine Lune à bord sombre, quartier 3,8 fois trop brillant en point. Correctif : Lommel-Seeliger ou Hapke pour les corps sans atmosphère, courbes de Mallama et Hilton 2018 pour l'éclat en point. § 10.2, § 10.3.

### Moyen

5. **Le Soleil ne vieillit pas** (`natif/src/commun.h:344`) sur des durées de milliards d'années. § 9.
6. **Position sur l'orbite au-delà d'environ 1 Ma** : perte de masse solaire absente du calcul long (`natif/physique/nbody_noyau.h:28`, table ±10 Ma). À ajouter, ou à signaler comme modèle. L'horizon de 45 Ma de `chaos.h:22` est optimiste pour la position. § 2.5, § 8.
7. **Comètes en points** : ni chevelure, ni queues, ni forces non gravitationnelles ; hyperboliques et objets interstellaires exclus. § 7.3.
8. **Lunes cachées hors de la plage de leurs fichiers** : prolongeables par éléments moyens et précession J2, en modèle signalé. § 6.2.
9. **Anneaux de Saturne** : pas de dépendance à la phase, face non éclairée identique à la face éclairée, pas d'anneaux pour Jupiter, Uranus, Neptune. § 6.3.
10. **Orientation de la Lune** : termes périodiques absents (pôle figé, jusqu'à 1,5° et 3,6°) ; lunes des autres planètes sans rotation synchrone (à vérifier dans `spheres.h`). § 4.3, § 5.
11. **Nuage d'Oort, héliopause, passage de Gliese 710** : absents, alors que l'appli possède les étoiles Gaia et leurs orbites. § 7.4.
12. **Mercure instable à 1 % en 5 Ga** (Laskar et Gastineau 2009) : non représenté ; l'intégrateur à pas fixe ne le permet pas. § 8.

### Faible

13. Gravité : J2 du Soleil, Lense-Thirring, termes 1PN entre planètes, 339 astéroïdes et anneau de Kuiper absents du calcul N corps. Quelques secondes d'arc en 20 000 ans.
14. DE441 non utilisé comme source (−13 200 à +17 191) : il remplacerait Meeus et l'essentiel du calcul direct.
15. Saut de 69 s de l'argument de temps à la borne de DE440 (`simulation.h:446` contre `:487` et `:500`) : environ 2 000 km sur la Terre.
16. `kCAuDay` (`nbody_noyau.h:29`) : valeur d'ancienne UA, écart 6 × 10⁻¹¹.
17. Astéroïdes en Kepler sans perturbation : correct sur ±300 ans pour l'aspect ; les troyens et les résonants se déforment avant.
18. Éclipses : disque solaire uniforme, un seul astre occultant, Terre sphérique, lumière instantanée.
19. Rotation des géantes : repère magnétique (Système III), carte fixe, vents zonaux absents ; période de Saturne de Voyager.
20. Sondes : 5 seulement, arrêt en 2100.
21. Énergie noire : absente de l'intégrateur planétaire, à bon droit (10⁻²² de l'attraction solaire à 1 UA). La règle « jamais négligée » demande au moins une phrase à l'écran ; le terme est en revanche bien présent dans les orbites galactiques (`orbites_pas.comp:32`).

### Ce qui est déjà conforme (à ne pas toucher)

- GM☉ identique à DE440 à 16 chiffres ; formule relativiste exacte ; mouvement de Kepler exact ; schéma réversible.
- Lecture SPK directe sans recalcul ; « inconnu » plutôt qu'extrapolation partout (`phys.h:3`).
- Présence de Cérès et Vesta dans le calcul (source du chaos à 60 Ma).
- Rayon solaire nominal UAI 2015 ; obliquité cohérente avec les repères JPL ; coefficients WGCCRE 2015, qui reste le dernier rapport publié.
- Bornes d'affichage honnêtes : astéroïdes ±300 ans, Lune de Meeus ±4 000 ans, sondes dans leurs dates.

---

## 12. Sources consultées aujourd'hui

- Park et al. 2021, DE440/DE441 : https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf ; https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440_and_de441.pdf ; https://ssd.jpl.nasa.gov/doc/de440_de441.html
- Fienga et al. 2021, INPOP21a : https://www.imcce.fr/content/medias/recherche/equipes/asd/inpop/inpop21a.pdf
- WGCCRE, rapport triennal 2021-2024 : https://www.iau.org/static/science/scientific_bodies/working_groups/100/wg-ccre-triennial-report-2021-2024.pdf
- Laskar et Gastineau 2009 (notice) : https://ideas.repec.org/a/nat/nature/v459y2009i7248d10.1038_nature08096.html
- Abbot et al. 2023 : https://arxiv.org/abs/2212.14844 ; Abbot et al. (sous-diffusion) : https://arxiv.org/abs/2306.11870
- Mogavero, Hoang, Laskar 2023 : https://arxiv.org/abs/2305.01683
- Schröder et Smith 2008 : https://arxiv.org/abs/0801.4031
- Pavlov, Williams, Suvorkin 2016 : https://arxiv.org/abs/1606.08376
- Mallama et Hilton 2018 : https://arxiv.org/abs/1808.01973
- Albédos : https://en.wikipedia.org/wiki/Geometric_albedo
- Lunes : https://ssd.jpl.nasa.gov/sats/discovery.html

Non consultées aujourd'hui (citées de mémoire, labels Probable ou À vérifier dans le texte) : Laskar et al. 2004 et 2011, Zeebe et Lourens 2019, Williams et Boggs 2016, Stephenson et al. 2016 (titre et revue vus dans les résultats de recherche seulement), Capitaine et al. 2003, Vondrák et al. 2011, Marsden et al. 1973, Farnocchia et al. 2021, Bailer-Jones et al. 2018, Kaib et Raymond 2024 et 2025, Gough 1981, Iess et al. 2018 et 2019, coefficients de Mallama et Hilton.
