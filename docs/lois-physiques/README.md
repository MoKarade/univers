# Les vraies lois physiques à toutes les échelles, et ce que fait l'appli (18 novembre 2026)

Demande de Marc (18/11, 16 h 16 UTC) : faire regarder par des agents « les réelles lois de physique à toutes les
échelles, dans le détail, pour tous les domaines, pour améliorer l'appli ».

Ce dossier : **un recensement sourcé** des lois et des valeurs mesurées de référence, échelle par échelle, **comparé au
code** (`appli-pc` au commit `5e649b7`, et branche `film-3` au commit `4f90b63` pour le grand calcul), avec **les écarts
classés par impact sur le réalisme**. Recherche seule : aucun code modifié, aucun calcul GPU lancé.

Les six annexes sont les rapports complets (≈ 54 000 mots, avec les références, les DOI ou arXiv, et les lignes du code).
Ce fichier en est la synthèse croisée. La méthode des pros, les codes à réutiliser et l'audit général du code sont
traités par d'autres fils ; ici, on reste sur **la physique et les mesures**.

Labels : [Certain] lu dans la source ou dans le code aujourd'hui ; [Probable] publié, cité de mémoire avec une source
connue ; [Supposition] raisonnement ou calcul d'ordre de grandeur fait ici ; [À vérifier] non vérifié.

| Annexe | Échelle / domaine |
|---|---|
| [1](01-systeme-solaire.md) | Système solaire : gravité, relativité, éphémérides, temps, marées, lunes, petits corps, chaos, avenir du Soleil, lumière des planètes |
| [2](02-etoiles-trous-noirs.md) | Étoiles : évolution stellaire, fonction de masse, couleurs, extinction, trous noirs, mouvements stellaires |
| [3](03-voie-lactee-groupe-local.md) | Voie lactée et Groupe local : Soleil, rotation, masses, barre, bras, halo, Andromède, Triangle, Nuages, fusion |
| [4](04-gaz-poussiere-lumiere.md) | Gaz, formation d'étoiles, rétroaction, métaux, poussière, rayonnement et rendu |
| [5](05-cosmologie-energie-noire.md) | Cosmologie, énergie noire (globale et locale), grandes structures, fond diffus |
| [6](06-physique-du-grand-calcul.md) | Physique du grand calcul : gravité, Λ, gaz, conditions initiales, explication des écarts du deuxième film |

---

## 0. En bref

1. **L'énergie noire est juste partout où elle est.** a = H0² Ω_Λ (x − x_cm), K = 3,1118 × 10⁻³ (km/s)²/kpc², en
   coordonnées physiques : c'est l'équation de Peñarrubia et al. 2014, et la valeur se recalcule à partir de Planck 2018
   (67,4 km/s/Mpc, Ω_Λ = 0,685). Elle pèse 11 à 13 % de l'attraction à la distance d'Andromède. Le calcul de l'appli est
   plus complet sur ce point que Sawala et al. 2025, qui ne la mettent pas. [Certain] Un seul oubli :
   `stabilite_tir.py` (galaxie seule) n'a aucun terme Λ. [Certain, relu]
2. **Le plus gros écart physique est dans le film : il n'a ni gaz, ni naissance d'étoiles, ni dissipation.** Le gaz
   (SPH) existe, mais seulement dans `stabilite_tir.py --gaz=1`. `rencontre.py`, qui fait le film, n'a que la gravité
   et Λ. Ses particules « gaz » sont donc des étoiles froides sans collision. [Certain, relu dans le code poussé ; le
   code local du fil du grand calcul peut être plus récent.] Le gaz tel qu'il est écrit manque aussi de rétroaction
   des supernovæ et de retour de masse des étoiles mortes : sans eux, le gaz se met en grumeaux puis s'épuise en 5 à
   7 Ga. [Probable]
3. **Barre trop lente, barre qui grossit, disque qui s'épaissit : une seule racine physique, attendue de ce code.**
   C'est un halo vivant sans rotation, sans gaz, avec une barre née d'un centre très instable. La littérature le
   montre : Debattista & Sellwood 2000 ; Long, Shlosman & Heller 2014 ; Beane et al. 2023, où la barre perd 43 % de sa
   vitesse sans gaz et reste stable avec environ 5 % de gaz. [Certain pour les articles relus] **Mais avant de corriger
   la physique, il faut relire la mesure** : avec un relevé tous les 50 Ma, une barre à 39 km/s/kpc se lit 22,4 par
   repliement (`bulletin.py:64-66`). Le « 17 à 28 » du deuxième film est exactement l'image de 33–44. [Certain pour
   l'arithmétique, À vérifier pour le relevé utilisé] La cible elle-même a baissé : 33,3 ± 1,8 (Clarke & Gerhard 2022)
   et 34,1 ± 2,4 (Zhang et al. 2024), plutôt que 39. [Certain]
4. **Les masses du Groupe local sont dans le mauvais sens.** Le calcul a une Voie lactée de 1,34 × 10¹² M☉ et une
   Andromède de 1,07 × 10¹² M☉, soit un rapport de 1,26. La mesure du flot de Hubble local donne 0,54 (+0,23 −0,17)
   (Peñarrubia 2014). [Certain] Le halo McMillan 2017 dépasse aussi les masses mesurées par les courants d'étoiles :
   +23 % à 32 kpc, +34 % à 50 kpc, +52 % à 100 kpc. [Supposition pour les masses du modèle, calculées ici ; Certain
   pour les mesures] Ces écarts changent la date de la fusion, le sort du Triangle (qui s'échappe dans le film) et
   l'orbite du Grand Nuage.
5. **La fusion avec Andromède est un scénario, pas une certitude.** Selon le mouvement propre d'Andromède retenu, la
   probabilité de fusion en 10 Ga va d'environ 50 % (Sawala et al. 2025) à environ 90 % (Wu 2026). Le film montre un
   tirage, avec une fusion à +6,75 Ga. [Certain pour les publications, Probable pour Wu 2026] L'écran doit le dire,
   avec la probabilité.
6. **La lumière ne suit pas l'âge des étoiles.** Les étoiles nées dans le calcul ne sont pas éclairées selon leur âge.
   Les étoiles Gaia « à orbite fiable » ne vieillissent jamais. Le Soleil non plus, alors qu'il était 21 % moins
   lumineux il y a 3 Ga et sera une géante rouge dans 7,6 Ga. La table qu'il faut (MIST × Kroupa) est déjà dans le
   dépôt. [Certain]
7. **La poussière est trop simple pour « ce à quoi ça ressemble ».** La lueur diffuse de la Voie lactée s'éteint en
   gris, sans rougir (`voie_lactee.frag:64`, relu). Andromède, le Triangle et les Nuages n'ont aucune poussière. La
   poussière et les régions HII sont figées dans le présent. [Certain]
8. **Grandes structures : trois incohérences.** Les décalages vers le rouge sont ramenés au repère du Groupe local, et
   non à celui du fond diffus, sans modèle de vitesses propres. Deux échelles de distance cohabitent : H0 ≈ 75 pour
   Cosmicflows-4 et 67,4 pour les décalages, soit 10 % d'écart. Enfin, a(t) s'applique à une partie des galaxies
   seulement. [Certain pour le code, Supposition pour l'ordre de grandeur de ±9 Mpc]
9. **Système solaire : la dynamique est de qualité professionnelle**, avec DE440, la relativité 1PN et GM☉ exact à
   16 chiffres. Les écarts sont dans le rendu et dans le temps long : éclipse de Lune noire au lieu de rouge cuivre,
   Jupiter et Saturne sphériques, Lune en Lambert, orientation de la Terre fausse loin d'aujourd'hui, et pas de perte
   de masse du Soleil. [Certain]
10. **Ce que je recommande** [Probable] : d'abord les trois corrections qui ne coûtent rien, c'est-à-dire relire la
    vitesse de barre, mettre Λ dans `stabilite_tir.py` et faire rougir la poussière diffuse. Ensuite, recaler les
    masses du Groupe local et brancher dans le film un gaz avec rétroaction. Ce sont ces deux points qui décident de
    la forme de tout le reste. Le détail est en section 3.

---

## 1. Tableau des lois et des valeurs de référence, par échelle

Chaque ligne donne la loi, la valeur à retenir et l'état de l'appli. Les incertitudes, les autres mesures et les DOI
sont dans l'annexe indiquée.

### 1.1 Système solaire (annexe 1)

| Loi / quantité | Référence | Appli | Verdict |
|---|---|---|---|
| Newton à N corps + relativité 1PN (EIH) ; périhélie de Mercure 42,98″/siècle | Park et al. 2021 (DE440/441) ; Will 2014 | DE440 lu directement (1550–2650), puis N corps Wisdom-Holman à 13 corps avec 1PN du Soleil | conforme [Certain] |
| GM☉, UA, TDB | IAU 2012/2015 ; DE440 | GM☉ identique à 16 chiffres ; ΔT figé à 69,184 s loin d'aujourd'hui | écart fort loin d'aujourd'hui (≈ 44° de rotation de la Terre à l'an 0) [Supposition, calculé] |
| Précession / nutation | Capitaine 2003 (IAU 2006) ; Vondrák 2011 pour ±200 000 ans | pôle linéaire | faux au-delà de 2–3 millénaires [Certain pour le code] |
| Perte de masse du Soleil ≈ 9 × 10⁻¹⁴ /an | ordre de grandeur publié | absente du calcul long | position sur l'orbite = modèle au-delà de ≈ 1 Ma [Supposition, à confirmer] |
| Chaos : Lyapunov ≈ 5 Ma ; Mercure instable à 1 % en 5 Ga | Laskar & Gastineau 2009 | horizon 60 Ma pour l'orbite | cohérent ; le 1 % n'est pas représenté [Certain] |
| Évolution du Soleil : −21 % de luminosité il y a 3 Ga ; géante rouge à +7,59 Ga, perte de 0,332 M☉ | Schröder & Smith 2008 | Soleil fixe (`commun.h:344`) | écart moyen [Certain] |
| Aplatissement : Saturne 9,8 %, Jupiter 6,5 % | IAU / WGCCRE 2015 | sphères | écart fort de rendu [Certain] |
| Photométrie : Lommel-Seeliger / Hapke, Mallama & Hilton 2018 | — | Lambert | pleine Lune au bord sombre, quartier 3,8 fois trop brillant [Supposition, calculé] |

### 1.2 Étoiles et trous noirs (annexe 2)

| Loi / quantité | Référence | Appli | Verdict |
|---|---|---|---|
| Évolution stellaire | MIST v1.2 ; **MIST v2 (Dotter et al. 2026, [α/Fe] −0,2 à +0,6)** ; PARSEC v2.0 | MIST v1.2 à abondances solaires | v2 utile pour le disque épais, le bulbe et le halo [Certain : arXiv:2602.22012] |
| Fonction de masse initiale | Kroupa 2001 ; Chabrier 2003 | Kroupa | conforme [Certain] |
| Formation d'étoiles de la Voie lactée | 1,65 ± 0,19 (Licquia & Newman 2015) ; 2,0 ± 0,7 M☉/an (Elia 2022) | cible du bulletin | conforme [Certain] |
| Supernovæ ; novæ | 1,63 ± 0,46 par siècle ; 26 ± 5 par an | absentes | à ajouter comme modèle statistique [Certain pour les taux] |
| Sgr A* | 4,30 × 10⁶ M☉ ± 0,25 % (GRAVITY 2022) ; anneau 51,8 ± 2,3 µas (EHT 2022) | valeur dans la table, aucun rendu natif | trou noir absent du natif [Certain] |
| Trous noirs stellaires | Gaia BH3 : 32,70 ± 0,82 M☉ | absents | — |
| Fusion des trous noirs centraux après la collision | < 16,6 Ma après celle des galaxies (Schiavi 2020) | absente du film | [Probable] |
| Vitesses radiales | Gaia DR3 : 33,8 M ; **DR4 le 2 décembre 2026 : 312 M de lignes** | les deux tiers des étoiles à vitesse radiale nulle | plus gros gain « mesuré » disponible [Certain pour la date ESA] |

### 1.3 Voie lactée et Groupe local (annexe 3)

| Quantité | Référence | Calcul / appli | Verdict |
|---|---|---|---|
| R0 | 8,178–8,275 kpc (GRAVITY 2019/2021) ; 8,2 ± 0,1 (revue Hunt & Vasiliev 2025) | 8,2 kpc | conforme [Certain] |
| Vitesse totale du Soleil | 248,5–251,5 km/s (mouvement propre de Sgr A*) | 245,0 km/s | 1,5–2,5 % trop bas [Supposition, calculé] |
| Hauteur du Soleil | 20,8 ± 0,3 pc | 6,6 pc | faible [Certain] |
| M(< 32 / 50 / 100 kpc) | 2,85 (Koposov 2023) ; 3,80 (Erkal 2019) ; 5,6 × 10¹¹ M☉ (Vasiliev 2021) | 3,5 ; 5,1 ; 8,5 × 10¹¹ | halo trop lourd de 23 à 52 % [Supposition pour le modèle] |
| Rapport Voie lactée / Andromède | 0,54 (+0,23 −0,17) (Peñarrubia 2014) | 1,26 | **inversé** [Certain] |
| Vitesse de la barre | 33,3 ± 1,8 (Clarke & Gerhard 2022) ; 34,1 ± 2,4 (Zhang 2024) ; 39 ± 3,5 (Portail 2017) ; ralentit de −4,5 ± 1,4 km/s/kpc/Ga | ≈ 20 lu (repliement possible) ; corotation/longueur ≈ 2,3 au lieu de 1,2–1,4 | fort [voir 0.3] |
| Courbe de rotation externe | chute « képlérienne » (Jiao 2023, Ou 2024) non robuste (Koop 2024 : biais de 10 à 15 %) | halo ≈ 1,3 × 10¹² | garder ≈ 1,0–1,1 × 10¹² (Cautun 2020, halo contracté) [Probable] |
| Grand Nuage, reflux | 1–2 × 10¹¹ M☉ ; reflux 32 ± 4 km/s (Petersen & Peñarrubia 2021) | dans le N-corps, absent des orbites Gaia | moyen [Certain] |
| Petit Nuage | ≈ 1–2 × 10¹⁰ M☉ à −3 Ga | 3 × 10⁹ | sous-pesé [Probable] |
| Fusion avec Andromède | ≈ 50 % en 10 Ga (Sawala 2025, médiane 7,6 Ga) ; ≈ 90 % (Wu 2026, médiane 6,5 Ga) | un film, fusion à +6,75 Ga | à afficher comme scénario [Certain / Probable] |

### 1.4 Gaz, poussière, lumière (annexe 4)

| Loi / quantité | Référence | Appli / calcul | Verdict |
|---|---|---|---|
| Gaz de la Voie lactée | HI ≈ 8 × 10⁹, H₂ ≈ 1 × 10⁹ M☉ ; HI troué à 4 kpc (McMillan 2017) | 1,22 × 10¹⁰ M☉ (hélium compris), un seul disque sans trou | forme fausse au centre [Certain] |
| Naissance d'étoiles | Kennicutt 1998 ; ε ≈ 1 % par temps de chute libre (Krumholz) | 1 % par t_ff au-dessus de 0,1 cm⁻³, isotherme 10 km/s | correct dans le principe, mais h ≈ 220–320 pc au seuil, plus que l'épaisseur du disque : taux dépendant de la résolution [Supposition, calculé] |
| Rétroaction | Springel & Hernquist 2003 ; EAGLE (Dalla Vecchia & Schaye 2012) ; FIRE | aucune | **fort** [Certain] |
| Retour de masse des étoiles | ≈ 40 % en 10 Ga | aucun ; épuisement du gaz en 6–7 Ga | fort [Probable] |
| Poussière 3D mesurée | Edenhofer 2024 (1,25 kpc, extension à 2 kpc) ; Vergely 2022 (3 kpc) ; plan entier à 7 kpc (Zhang, Chen et al. 2026, prépublication) | 1,25 kpc puis modèle | extensible [Certain pour les cartes] |
| Loi d'extinction | Cardelli 1989 ; Fitzpatrick 1999 ; Gordon 2023 ; coefficients écran ≈ (0,89 ; 1,02 ; 1,23) | lueur grise ; étoiles du modèle (0,75 ; 1 ; 1,32) | rougissement absent ou ≈ 1,7 fois trop fort [Certain pour le code, Supposition pour les coefficients écran] |
| Diffusion (albédo ≈ 0,6) | — | absente | bandes sombres trop noires de l'extérieur [Probable] |
| Aberration, Doppler, temps de trajet | relativité restreinte | absents | négligeable dans le Groupe local [Certain] |

### 1.5 Cosmologie et énergie noire (annexe 5)

| Quantité | Référence | Appli | Verdict |
|---|---|---|---|
| H0 | 67,4 ± 0,5 (Planck 2018) ; 68,43 ± 0,27 (ACT + Planck + DESI DR2) ; 70,39 (CCHP 2025) ; 73,50 ± 0,81 (H0DN 2026) | 67,4 ; Cosmicflows-4 à ≈ 75 | deux échelles dans le même volume [Certain] |
| Énergie noire évolutive | DESI DR2 : w0 > −1, wa < 0 à 2,8–4,2 σ (3,2 σ après recalibrage) : une indication, pas une découverte | w0/wa disponibles, extrapolés dans l'avenir | non physique pour a > 1 : figer w au-delà d'aujourd'hui [Certain] |
| Âge de l'Univers | 13,79 Ga | 13,791 Ga | conforme [Certain] |
| Énergie noire locale | r̈ = −GM/r² + H0² Ω_Λ r ; rayon de gravité nulle 1,4–1,9 Mpc | K identique dans les 7 copies | conforme, sauf `stabilite_tir.py` [Certain] |
| Marée des voisins (Virgo, Cen A/M83, M81, IC 342) | chacune 25 à 45 % du terme Λ | absente | à tester [Supposition, calculé] |
| Mouvement par rapport au fond diffus | 620 ± 15 km/s vers (271,9° ; 29,6°) (Planck 2018 I) | 627 km/s (Kogut 1993) | faible [Certain] |
| « Grand Attracteur » | point de convergence (313° ; 27°), ≈ 41 h⁻¹ Mpc ; aucun attracteur unique (Stiskalek et al. 2026) | placé sur l'amas de la Règle | moyen [Probable] |
| Avenir | horizon des événements 16,7 milliards d'al ; a = 321 à +100 Ga | le temps s'arrête à la fin du film | vue « Milkomeda isolée » possible comme modèle [Supposition, calculé] |

---

## 2. Écarts classés par impact sur le réalisme (toutes échelles)

« Fort » : change la forme ou l'histoire de ce que Marc voit. « Moyen » : visible en regardant bien, ou faux sur une
partie du temps. « Faible » : sous le pour-cent ou invisible. Chaque ligne renvoie à son annexe.

### Fort

| # | Écart | Où | Annexe |
|---|---|---|---|
| F1 | Le film n'a ni gaz, ni naissance d'étoiles, ni dissipation : les bras ne se reforment pas, le disque jeune s'épaissit et la barre est freinée | `rencontre.py:119-126` | 6, 4 |
| F2 | Le gaz tel qu'il est écrit n'a ni rétroaction, ni retour de masse, ni accrétion. Il part agité (Mach 3) et le pas de Courant n'est pas imposé | `gaz_galaxie.py:17`, `modeles_v2.py:202-205` | 4, 6, 2 |
| F3 | La barre est lente, longue et croissante, et le disque passe de 0,55 à 1,24 kpc en 5 Ga, pour ≈ 0,3 kpc mesurés. La mesure de la vitesse est à relire d'abord | `bulletin.py:64-66`, `stabilite_tir.py:135`, `modeles_v2.py:155` | 6, 3 |
| F4 | Masses : la Voie lactée est plus lourde qu'Andromède (1,26 au lieu de 0,54), et son halo est trop lourd entre 30 et 100 kpc | `modeles_v2.py:38`, `univers.json` | 3 |
| F5 | Un seul film pour un avenir bimodal (50 à 90 % de fusion), et le Triangle n'est pas lié à Andromède | film ; `univers.json` | 3, 2 |
| F6 | La lumière des étoiles nées ne suit pas leur âge ; les étoiles Gaia fiables et le Soleil ne vieillissent pas | `vieillissement.h:3`, `commun.h:344`, `docs/contrat-etoiles-visibles.md:69` | 2, 1 |
| F7 | La poussière diffuse s'éteint en gris ; aucune poussière dans les autres galaxies ; poussière et régions HII figées | `voie_lactee.frag:64`, `gaia.vert:136` | 4 |
| F8 | Aucun trou noir dans l'appli native ni dans le film : ni ombre, ni lentille, ni fusion des trous noirs centraux | — (la page web a `27_lens.js`) | 2 |
| F9 | Grandes structures : repère des décalages, deux échelles de H0, a(t) appliqué à une partie des galaxies seulement | `build_data2.py:139-157`, `galaxies_formes.h:62` | 5 |
| F10 | Système solaire : éclipse de Lune noire, astres sans atmosphère, géantes sphériques, Lune en Lambert, orientation de la Terre fausse loin d'aujourd'hui | `sphere.frag:76-93`, `simulation.h:38, 73-83`, `orientation.h:30` | 1 |

### Moyen

| # | Écart | Annexe |
|---|---|---|
| M1 | Deux modèles de masse de la Voie lactée (MWPotential2014 pour Gaia, McMillan 2017 pour le N-corps). `champ_bfe.h`, branché nulle part, permettrait d'unifier et d'ajouter le Grand Nuage et le reflux aux orbites Gaia | 3 |
| M2 | Halos sphériques, sans rotation ni contraction ; pas de Sagittaire ni de trou noir central dans le calcul | 3, 6 |
| M3 | Grain du halo à la limite de Ludlow et al. 2021 (m_DM ≈ 5,6 × 10⁵ M☉) : chauffe les étoiles jeunes ; Triangle et Grand Nuage sous-résolus | 6 |
| M4 | Pas de temps unique de 0,25 Ma, deux à trois fois trop long sous 0,2 kpc ; film à 10 Ma par image, sans vitesses : orbites du centre repliées | 6, 3 |
| M5 | Gaia DR4 (2 décembre 2026) : 312 M de lignes de vitesses radiales, alors que le pipeline vise DR3 | 2 |
| M6 | Facteur de vieillissement bolométrique appliqué à du visible ; poussière des étoiles Gaia figée sur la ligne de visée solaire | 2, 4 |
| M7 | Carte de poussière mesurée limitée à 1,25 kpc ; pas de diffusion ; éclat des régions HII supposé alors qu'il est mesurable | 4 |
| M8 | w0/wa extrapolés dans l'avenir ; statut de l'énergie noire à afficher (Planck, DESI, H0 locale) ; marée des voisins absente | 5 |
| M9 | Perte de masse du Soleil absente ; comètes sans queue ni forces non gravitationnelles ; nuage d'Oort et passage de Gliese 710 absents | 1 |
| M10 | Barre à vitesse constante dans les orbites Gaia (`galaxie_orbites.h`) : sa phase est inconnue au-delà de ±100 à 200 Ma | 3 |

### Faible

Pour mémoire, sans détail ici : J2 du Soleil et Lense-Thirring ; DE441 non utilisé ; saut de 69 s à la borne de DE440 ;
R0 et vitesse du Soleil à 1–2 % ; deux formules de corps noir ; M☉,V = 4,83 au lieu de 4,81 ; Ω_k = −9 × 10⁻⁵ au lieu de
0 ; neutrinos sans masse ; vitesse par rapport au fond diffus de 627 au lieu de 620 km/s ; Λ absente du système solaire
(10⁻²² de l'attraction solaire à 1 UA, à dire à l'écran). Liste complète dans chaque annexe.

### Ce qui est déjà juste et à garder [Certain]

- Énergie noire : formule, valeur et coordonnées physiques, avec le frottement dynamique porté par les particules.
- Système solaire : DE440, 1PN, GM☉, bornes d'affichage honnêtes (« inconnu » plutôt qu'extrapolé).
- Fonction de masse de Kroupa, efficacité de 1 % par temps de chute libre, Sgr A*, M87*, Gliese 710.
- Valeurs publiées des modèles de galaxies (McMillan 2017, Tamm 2012, Corbelli 2014, Erkal 2019) fidèlement recopiées.
- Distance d'Andromède (761 kpc, Li 2021), Grand Nuage, disques mince et épais au Soleil.
- `cosmologie.h` : distances et âge recalculés, conformes.
- La table unique `univers.json` et le grand livre des masses : le bon endroit pour corriger en une fois.

---

## 3. Ordre de travail recommandé

Trois options pour l'ordre des corrections.

| Option | Contenu | Pour | Contre |
|---|---|---|---|
| A. Rendu d'abord | F7, F10, F6 : poussière, système solaire, vieillissement | effets visibles tout de suite, sans calcul GPU | ne touche pas à la forme des galaxies, qui est le cœur de la demande |
| B. Calcul d'abord | F3, F4, F1, F2 : barre, masses, gaz avec rétroaction, puis nouveau film | règle ce qui décide de la forme et de l'histoire de tout le reste | plusieurs jours de carte graphique ; c'est le terrain du fil du grand calcul |
| **C. Mixte (recommandé)** | corrections gratuites d'abord, puis B, avec A en parallèle sur les fils de rendu | aucun temps perdu, et pas de film refait deux fois | demande de coordonner deux fils |

**Recommandation : C** [Probable].

1. **Corrections gratuites, à faire en une heure chacune** :
   - relire la vitesse de la barre sur les images à 10 Ma (`--releve-ma=10`), avant toute correction physique ;
   - ajouter Λ dans `stabilite_tir.py`, de préférence dans une fonction commune « gravité + Λ », pour qu'aucun appelant
     ne puisse l'oublier ;
   - faire rougir l'extinction de la lueur diffuse et passer aux coefficients écran ;
   - ajouter au bulletin les masses enfermées à 32, 50 et 100 kpc et le rapport corotation / longueur de barre.
2. **Recaler les masses** dans `univers.json` : Voie lactée ≈ 1,0–1,1 × 10¹² M☉ (Cautun 2020, halo contracté) et
   Andromède ≈ 1,3–1,6 × 10¹² M☉. Ce sont des modèles calés sur les mesures, à signaler comme tels. Garder l'ensemble
   Monte-Carlo pour montrer la dispersion. [Probable]
3. **Gaz dans le film**, avec :
   - un départ à l'équilibre (deux disques troués, comme McMillan 2017) ;
   - une équation d'état effective ou la quantité de mouvement des supernovæ ;
   - le retour de masse des étoiles, la masse totale restant conservée ;
   - des pas de temps adaptés.
   Puis laisser naître la barre avec gaz et un halo légèrement en rotation (λ ≈ 0,035), et viser 33–39 km/s/kpc.
   [Probable : Beane 2023, Long 2014]
4. **Brancher le rendu sur le calcul** : lumière selon l'âge (table MIST déjà présente), poussière tirée du gaz du
   calcul (A_V/pc ≈ 1,65 × 10⁻³ n_H Z/Z☉, d'après Bohlin 1978 [Probable]) et régions HII tirées des étoiles de moins
   de 10 Ma.
5. **Afficher l'incertitude** : la fusion comme scénario avec sa probabilité, l'énergie noire évolutive comme
   indication, et le Soleil, la barre et les orbites Gaia lointaines comme modèles.
6. En parallèle, sur les fils de rendu : système solaire (F10), trous noirs (F8), grandes structures (F9), Gaia DR4
   dès le 2 décembre.

---

## 4. Limites de ce recensement

- Six agents ont lu le code et les sources ; j'ai revérifié moi-même dans le code les points qui décident du plan.
  Ce sont l'absence de gaz dans `rencontre.py`, l'absence de Λ dans `stabilite_tir.py`, le relevé à 50 Ma, la
  poussière grise et la distance fixe des galaxies mesurées. La valeur de K se recalcule à partir de Planck 2018.
  Le reste vient des annexes, avec leurs labels.
- Plusieurs références classiques sont citées de mémoire et marquées [Probable] ou [À vérifier] dans les annexes.
  Chaque annexe finit par la liste de ce qu'elle a relu en ligne et de ce qu'elle n'a pas relu.
- Les masses enfermées du modèle, le repliement de la barre, l'erreur d'orientation de la Terre et l'effet de la
  marée des voisins sont des calculs d'ordre de grandeur faits ici, pas des mesures sur le film.
- Le code lu est celui qui est poussé sur GitHub. Le fil du grand calcul peut avoir du code local plus récent,
  notamment pour le gaz dans le film.
