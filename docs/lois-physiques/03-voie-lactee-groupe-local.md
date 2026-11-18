# Annexe 3 — Dynamique de la Voie lactée et du Groupe local : mesures de référence et écarts avec l'appli

Rédigé le 18 novembre 2026. Recherche seule : aucun fichier du dépôt modifié, aucun calcul GPU lancé.

Labels : **[Certain]** lu aujourd'hui dans la source (page arXiv / ar5iv) ou dans le code ; **[Probable]** publié, cité de mémoire avec source connue ; **[Supposition]** mon raisonnement ou mon calcul fait ici ; **[À vérifier]** non vérifié.
Les numéros de ligne renvoient aux fichiers tels qu'ils sont aujourd'hui dans `/home/claude/film-3` (pipeline) et `/home/claude/univers` (natif).

## Résumé

- **Le halo de la Voie lactée du calcul est lourd au-delà de 30 kpc.** Le modèle McMillan 2017 utilisé (`modeles_v2.py:38`) enferme 3,5 × 10¹¹ M☉ dans 32 kpc, 5,1 × 10¹¹ dans 50 kpc et 8,5 × 10¹¹ dans 100 kpc [Supposition : calculé ici], contre 2,85 ± 0,1 (Koposov 2023), 3,80 (+0,14 −0,11) (Erkal 2019) et 5,6 ± 0,4 (Vasiliev 2021) mesurés avec les courants d'étoiles [Certain]. Écart de +23 %, +34 % et +52 %.
- **La Voie lactée du calcul pèse plus qu'Andromède** (1,34 contre 1,07 × 10¹² M☉), à l'inverse de presque toute la littérature (rapport Voie lactée / Andromède = 0,54 (+0,23 −0,17), Peñarrubia 2014 ; Andromède 1,1 à 3,0 × 10¹² selon la méthode) [Certain]. C'est l'inconnue qui pèse le plus sur la date de la fusion et sur le sort du Triangle.
- **Le Triangle n'est pas lié à Andromède dans la table** : vitesse relative 248 km/s à 230 kpc, pour une vitesse de libération de 235 km/s avec les masses du calcul [Supposition : calculé ici]. Il « s'échappe » dans le film (`docs/deuxieme-film.md:24`). Avec une Andromède de 2 à 3 × 10¹² M☉, il serait lié (vitesse de libération ≈ 357 km/s).
- **La barre du film est deux fois trop lente et hors de la plage observée** : 20 km/s/kpc donne une corotation à 11,4 kpc, soit 2,3 fois la longueur de la barre ; les mesures donnent 33 à 41 km/s/kpc, corotation 6 à 7,5 kpc, rapport 1,2 à 1,4 [Certain pour les mesures, Supposition pour le rapport]. Trois causes physiques connues : halo sans rotation, pas de gaz dans ce film, halo trop dense au centre par rapport aux étoiles.
- **La courbe de rotation au-delà de 15 kpc est en débat** : la chute « képlérienne » (Jiao 2023, Ou 2024 : masse totale ≈ 2 × 10¹¹ M☉) n'est pas robuste (Koop 2024 : biais de 10 à 15 % de la méthode de Jeans) et contredit les courants, les amas et les satellites [Certain]. Garder un halo de ≈ 1 × 10¹² M☉ est défendable ; 1,3 à 1,4 est en haut de la fourchette.
- **L'énergie noire est bien traitée** (a = H0² Ω_Λ (x − x_cm), `rencontre.py:120-124`, `galaxie_orbites.h:48`) : 11 à 13 % de l'attraction à la distance d'Andromède [Supposition : calculé]. Sawala 2025 ne la met pas [Certain] : le calcul de l'appli est plus complet sur ce point.
- **Mouvement propre d'Andromède** : la table suit Wu 2025 (vitesse tangentielle 28 km/s [calculé ici]) ; Salomon 2021 donne 82 ± 31 km/s, van der Marel 2019 57 (+35 −31), van der Marel 2012 17 (< 34) [Certain]. La probabilité de fusion passe de ≈ 50 % (Sawala 2025) à ≈ 90 % (Wu 2026) selon ce seul choix [Certain]. Le film unique est donc un scénario parmi deux familles.
- **Repère du Soleil** : R0 = 8,2 kpc est correct à 1 % (GRAVITY : 8,178 ± 0,013 ± 0,022 en 2019, 8,275 après correction des aberrations en 2021). La vitesse totale du Soleil, 245,0 km/s, est 4 km/s sous la valeur tirée du mouvement propre de Sgr A* (249,2 km/s à 8,2 kpc) [Supposition : calculé]. La hauteur du Soleil vaut 6,6 pc dans l'appli contre 20,8 ± 0,3 pc mesurés.
- **Absents du modèle** : rotation et forme du halo, contraction du halo par les étoiles, gauchissement et évasement du disque, bras spiraux dans les orbites d'étoiles, ralentissement de la barre, reflux de la Voie lactée vers le Grand Nuage dans les orbites d'étoiles, Petit Nuage sous-pesé (3 × 10⁹ M☉).
- **Lecture du film** : avec une image tous les 10 Ma, le centre des galaxies (période orbitale sous 20 Ma en dessous de 0,5 kpc) est sous-échantillonné [Supposition].

---

## 1. Voie lactée

### 1.1 Position et vitesse du Soleil

| Grandeur | Valeur de référence | Source | Appli | Écart |
|---|---|---|---|---|
| R0 | 8 178 ± 13 (stat) ± 22 (syst) pc [Certain] | GRAVITY Collab. 2019, A&A 625, L10, arXiv:1904.05721 | 8,2 kpc (`galaxie_orbites.h:24`, `bulletin.py:16`, `univers.json` repere.R0) | +0,3 % |
| R0 (révisé) | 8 275 ± 9 ± 33 pc [Probable : valeur citée dans la mission et dans la littérature ; la page arXiv lue ne donne pas le chiffre] | GRAVITY Collab. 2021, A&A 647, A59, doi 10.1051/0004-6361/202040208, arXiv:2101.12098 (correction des aberrations optiques) | idem | −0,9 % |
| R0 (masers) | 8,15 ± 0,15 kpc [Certain] | Reid et al. 2019, ApJ 885, 131, arXiv:1910.03357 | idem | +0,6 % |
| R0 (revue) | 8,2 ± 0,1 kpc ; valeurs récentes 8,1 à 8,3 ; 8,23 ± 0,12 (Leung 2023) [Certain] | Hunt & Vasiliev 2025, arXiv:2501.04075 (revue) | idem | conforme |
| z0 (hauteur du Soleil) | 20,8 ± 0,3 pc [Certain] | Bennett & Bovy 2019, MNRAS 482, 1417, arXiv:1809.03507 | +6,6 pc (`univers.json` soleil_position z = 0,006606 kpc) | −14 pc |
| z0 (masers) | 5,5 ± 5,8 pc [Certain] ; 7 ± 2 pc selon la revue | Reid et al. 2019 | idem | compatible |
| Mouvement propre du Soleil (U, V, W) | (11,1 ; 12,24 ; 7,25) km/s ; erreurs stat ≈ (0,7 ; 0,5 ; 0,4), syst ≈ (1 ; 2 ; 0,5) [Probable] | Schönrich, Binney & Dehnen 2010, MNRAS 403, 1829 | identique (`galaxie_orbites.h:36`) | conforme |
| Vitesse circulaire au Soleil | 229,0 ± 0,2 km/s (formel), syst 2 à 5 % [Certain] | Eilers et al. 2019, ApJ 871, 120, arXiv:1810.09466 | 232,8 (`galaxie_orbites.h:24`) ; 233,1 (cible `mesures_voie_lactee.json`) | +1,7 % |
| idem | 236 ± 7 km/s [Certain] | Reid et al. 2019 | idem | −1,4 % |
| idem | 232,8 ± 3,0 km/s [Certain : docs du dépôt, lu dans l'article le 13/11] | McMillan 2017, MNRAS 465, 76, arXiv:1608.00971 | idem | source |
| Vitesse totale du Soleil Θ0 + V☉ | 247 ± 4 km/s ; (Θ0 + V☉)/R0 = 30,32 ± 0,27 km/s/kpc [Certain] | Reid et al. 2019 | 245,04 km/s, soit 29,88 km/s/kpc | −1,5 % |
| idem, par Sgr A* | mouvement propre de Sgr A* le long du plan −6,411 ± 0,008 mas/an [Probable], soit 30,39 km/s/kpc : 248,5 km/s à 8,178 kpc, 249,2 à 8,2, 251,5 à 8,275 [Supposition : calculé] | Reid & Brunthaler 2020, ApJ 892, 39 | 245,04 | −4,2 km/s |
| idem | 251,31 ± 1,95 km/s [Certain] | Clarke & Gerhard 2022, MNRAS 512, 2171, arXiv:2107.10875 | 245,04 | −6,3 km/s |
| idem (astropy v4.0) | (12,9 ; 245,6 ; 7,78) km/s à R0 = 8,122 kpc [Certain : revue et `groupe_local_clones.py:9`] | Drimmel & Poggio 2018 | 245,04 | conforme |

Remarques.
- La hauteur de 6,6 pc de l'appli n'est pas une mesure : c'est la conséquence géométrique de garder le plan b = 0 des coordonnées galactiques avec Sgr A* à b = −0,046° [Supposition]. L'origine des coordonnées galactiques est à ≈ 4′ (≈ 10 pc) de Sgr A* [Certain, Hunt & Vasiliev 2025]. L'effet visible est nul à l'échelle de la Galaxie ; il compte seulement si l'on dessine le disque mince (300 pc) autour du Soleil à mieux que 5 %.
- Le couple cohérent le mieux contraint aujourd'hui est R0 ≈ 8,2 kpc, vitesse totale ≈ 249 km/s, donc vitesse circulaire ≈ 237 km/s si V☉ = 12,24 [Supposition]. L'appli est à 232,8 : 1,7 % sous cette valeur, dans la marge de McMillan (± 3,0).
- `conditions.json` (ancien calcul) garde l'ancienne vitesse (11,1 ; 242,24 ; 7,25), donc v0 = 230 [Certain]. Le grand livre le signale déjà (`docs/grand-livre-masses.md:13-15`).

### 1.2 Courbe de rotation et « chute képlérienne »

| Étude | Traceurs, rayon | Pente externe (km/s/kpc) | Masse déduite | Source |
|---|---|---|---|---|
| Eilers et al. 2019 | géantes rouges, 5–25 kpc | −1,7 ± 0,1 (syst 0,46) | M_vir = 7,25 ± 0,26 × 10¹¹ M☉ (NFW, c = 12,8) ; ρ_DM locale 0,30 ± 0,03 GeV/cm³ | ApJ 871, 120 [Certain] |
| Mróz et al. 2019 | Céphéides, 4–20 kpc | −1,34 ± 0,21 | — | ApJL 870, L10 [Certain via la revue Melchiorri & Ruchika 2026] |
| Wang et al. 2023 | Gaia DR3, 9,5–27,5 kpc | −2,3 ± 0,2 ; ≈ 175 km/s à 27,5 kpc | — | ApJ 942, 12 [Certain via Jiao 2023 et la revue] |
| Jiao et al. 2023 | Gaia DR3, 9,5–26,5 kpc | −2,18 ± 0,23 ; loi de puissance −0,47 ± 0,15 au-delà de 19 kpc | M_tot = 2,06 (+0,24 −0,13) × 10¹¹ M☉ ; borne haute 5,4 × 10¹¹ | A&A 678, A208 [Certain via la revue] |
| Ou et al. 2024 | géantes rouges, 6–27 kpc | −2,22 ± 0,20 | M_200 = 1,81 (+0,06 −0,05) × 10¹¹ M☉ (Einasto à cœur, α = 0,91) ; 6,94 × 10¹¹ (NFW généralisé, moins bon) | MNRAS 528, 693, arXiv:2303.12838 [Certain] |
| Koop et al. 2024 | Gaia DR3 + simulations | — | la méthode de Jeans axisymétrique s'écarte de la vraie vitesse circulaire de ≈ 10 % (jusqu'à 15 %) ; une densité de traceurs tronquée fabrique une fausse chute | A&A, doi 10.1051/0004-6361/202450911, arXiv:2405.19028 [Certain] |
| Melchiorri & Ruchika 2026 (revue) | — | — | les estimations par la courbe de rotation vont de 1,8 à 8 × 10¹¹ M☉ ; la chute « repose sur des hypothèses délicates » ; courants, amas, satellites et argument de temps « favorisent un halo nettement plus lourd » | arXiv:2608.10189 [Certain] |

Conclusion [Probable] : entre 5 et 15 kpc la courbe est plate à faiblement décroissante (−1,3 à −1,7 km/s/kpc) ; c'est robuste. Au-delà de 15 à 20 kpc, la chute plus raide est mesurée mais son interprétation en masse (2 × 10¹¹ M☉) ne l'est pas. Ou et al. écrivent eux-mêmes que leur masse basse vient de la forme de profil extrapolée et qu'elle est en tension avec les amas, les naines et les courants [Certain].

Ce que fait l'appli :
- `galaxie_orbites.h:25-43` (orbites des étoiles Gaia) : bulbe de Hernquist + disque de Miyamoto-Nagai + halo NFW (r_s = 16 kpc) recalé sur 232,8 km/s. Calculé ici [Supposition] : 229,8 km/s à 4 kpc ; 235,4 à 6 ; 232,8 au Soleil ; 223,0 à 15 ; 218,3 à 20 ; 214,6 à 25 ; pente moyenne 5–25 kpc = −1,0 km/s/kpc. Halo : M_200 = 1,03 × 10¹² M☉, c = 13,3 ; matière noire locale 0,0098 M☉/pc³. La pente est plus faible que les mesures (−1,3 à −1,7) : écart faible, 5 à 8 km/s à 20–25 kpc.
- `modeles_v2.py:38` (N-corps) : NFW de McMillan, ρ0 = 8,54 × 10⁶ M☉/kpc³, r_s = 19,6 kpc, coupé à 250 kpc. Calculé ici [Supposition] : M_200c = 1,32 × 10¹² M☉ à 232 kpc (c = 11,8) ; 1,37 × 10¹² dans 250 kpc ; `univers.json` donne 1,276 × 10¹² après coupure.

### 1.3 Masse totale et masse enfermée

| Mesure | Valeur | Source | Modèle N-corps (halo McMillan + 6,6 × 10¹⁰ de baryons) [Supposition : calculé] | Écart |
|---|---|---|---|---|
| M(< 32,4 kpc) | 2,85 ± 0,1 × 10¹¹ M☉ [Certain] | Koposov et al. 2023, MNRAS 521, 4936, arXiv:2211.04495 (courant Orphan-Chenab, avec le Grand Nuage) | 3,51 × 10¹¹ | +23 % |
| M(< 50 kpc) | 3,80 (+0,14 −0,11) × 10¹¹ M☉ [Certain] | Erkal et al. 2019, MNRAS 487, 2685, arXiv:1812.08192 | 5,10 × 10¹¹ | +34 % |
| M(< 100 kpc) | 5,6 ± 0,4 × 10¹¹ M☉ [Certain] | Vasiliev, Belokurov & Erkal 2021, MNRAS 501, 2279, arXiv:2009.10726 (courant du Sagittaire) | 8,52 × 10¹¹ | +52 % |
| M_200 total | 1,08 (+0,20 −0,14) × 10¹² M☉ ; halo 0,97 (+0,24 −0,19) ; c = 9,4 (+1,9 −2,6) avant contraction ; étoiles 5,04 (+0,43 −0,52) × 10¹⁰ ; ρ_DM locale 8,8 ± 0,5 × 10⁻³ M☉/pc³ [Certain] | Cautun et al. 2020, MNRAS 494, 4291, arXiv:1911.04557 | 1,32 × 10¹² (M_200c) | +22 % |
| M_vir | 1,30 ± 0,30 × 10¹² M☉ [Certain : docs du dépôt] | McMillan 2017 | source du modèle | — |
| M_200 adoptée par Sawala | 1,0 ± 0,2 × 10¹² M☉, Grand Nuage exclu [Certain] | Sawala et al. 2025, Nat. Astron., doi 10.1038/s41550-025-02563-1 | 1,34 | +1,1 σ (déjà noté dans le grand livre) |
| Avant Gaia | 0,5 à 3 × 10¹² M☉ [Certain via la revue 2026] | — | — | — |
| Baryons | 0,6 à 1,0 × 10¹¹ M☉ ; étoiles 4 à 6 × 10¹⁰ [Certain] | Bland-Hawthorn & Gerhard 2016, ARA&A 54, 529 ; Hunt & Vasiliev 2025 | étoiles 5,46 × 10¹⁰, gaz 1,22 × 10¹⁰ | conforme |

Lecture [Supposition] : le modèle McMillan 2017 est antérieur à Gaia DR2 et aux mesures par courants qui tiennent compte du Grand Nuage. Erkal et al. 2020 montrent que négliger le Grand Nuage gonfle la masse de la Voie lactée jusqu'à 50 % [Certain via Chandra et al. 2025]. Le halo du calcul est correct au Soleil (matière noire locale 0,0101 M☉/pc³) et trop lourd de 25 à 50 % entre 30 et 100 kpc. Conséquences sur le film : orbite du Grand Nuage plus serrée et frottement plus fort que dans la réalité (absorption trop rapide), Sagittaire et courants plus liés.

Remède fondé sur la physique [modèle] : le halo NFW contracté de Cautun et al. 2020 (M_200 = 1,08 × 10¹², c = 9,4 puis contraction par les baryons : ×1,3 de matière noire à 20 kpc, ×2 à 8 kpc, ×4 à 1 kpc [Certain]). Il garde la vitesse au Soleil, baisse la masse externe et donne un centre plus dominé par… la matière noire contractée ; point à contrôler pour la barre (§ 1.5).

### 1.4 Disques, bulbe, gaz

| Grandeur | Référence | Source | Appli (`modeles_v2.py:41-43`, `univers.json`) | Écart |
|---|---|---|---|---|
| Disque mince, hauteur | 300 ± 50 pc [Probable] | Bland-Hawthorn & Gerhard 2016 § 5 ; Jurić et al. 2008 | 0,30 kpc | conforme au départ |
| Disque épais, hauteur | 900 ± 180 pc [Probable] | idem | 0,90 kpc | conforme au départ |
| Disque mince, longueur | 2,6 ± 0,5 kpc [Probable] | Bland-Hawthorn & Gerhard 2016 | 2,50 kpc (McMillan) | conforme |
| Disque épais, longueur | 2,0 ± 0,2 kpc [Certain : docs du dépôt, § 7] | idem | 3,02 kpc (McMillan) | +50 % : le disque épais du calcul est trop étendu |
| Disque épais, masse | 6 ± 3 × 10⁹ M☉ [Certain : docs] ; disque riche en α ≈ 2 × 10¹⁰ (Xiang & Rix 2022) [Certain via la revue] | idem ; Hunt & Vasiliev 2025 | 1,05 × 10¹⁰ | dans la fourchette (large) |
| Étoiles, total | 5 ± 1 × 10¹⁰ (BHG16) ; 6,08 ± 1,14 × 10¹⁰ (Licquia & Newman 2015) ; 5,04 (Cautun 2020) | — | 5,46 × 10¹⁰ | conforme |
| Barre + bulbe (étoiles) | 1,88 ± 0,12 × 10¹⁰, dont barre longue 0,54 [Certain : docs § 7] | Portail et al. 2017, MNRAS 465, 1621 | bulbe 0,89 à 0,92 × 10¹⁰ | −50 % dans la variante avec bulbe de McMillan |
| Agitation au Soleil | mince : σ_R 35 ± 5, σ_z 25 ± 5 ; épais : 50 ± 5 et 50 ± 5 km/s | Bland-Hawthorn & Gerhard 2016 § 5.4 | 35 et 50 (radiale) | conforme |
| Gaz | HI 1,1 × 10¹⁰ (troué à 4 kpc, 7 kpc, 85 pc) ; H2 1,2 × 10⁹ (troué à 12 kpc, 1,5 kpc, 45 pc) | McMillan 2017 | un seul disque exponentiel de 7 kpc, 85 pc, sans trou | forme simplifiée : trop de gaz au centre |
| Naissance d'étoiles | 1,65 ± 0,19 M☉/an | Licquia & Newman 2015, ApJ 806, 96 | cible du bulletin | — |

Écart connu du film (`docs/deuxieme-film.md:36-43`) : le disque vieux part à 0,55 kpc et atteint 0,91 kpc en 3 Ga, 1,24 kpc en 5 Ga. Référence : voir § 1.7.

### 1.5 Barre

| Grandeur | Valeur | Source |
|---|---|---|
| Demi-longueur | 5,0 ± 0,2 kpc [Certain : docs ; confirmé par la revue] | Wegg, Gerhard & Portail 2015, MNRAS 450, 4050 |
| Longueur dynamique | ≈ 4,0 kpc (cinématique) ; 3,8 kpc (orbites x1) [Certain] | Zhang et al. 2024, arXiv:2406.06678 |
| Angle avec la ligne Soleil-centre | 28° (Wegg & Gerhard 2013) ; 25° (Bovy 2019, Zhang 2024) ; 20° à 45° selon les traceurs [Certain] | Hunt & Vasiliev 2025 |
| Vitesse du motif | 39,0 ± 3,5 km/s/kpc ; corotation 6,1 ± 0,5 kpc [Certain : docs] | Portail et al. 2017 |
| idem | 41 ± 3 [Certain via Zhang 2024] | Sanders, Smith & Evans 2019 (révisé à ≈ 31 avec les deux côtés) ; Bovy et al. 2019 |
| idem | 33,29 ± 1,81 ; corotation 6,5 à 7,5 kpc [Certain] | Clarke & Gerhard 2022 |
| idem | 40,1 ± 1,8 [Certain via Zhang 2024] | Leung et al. 2023 |
| idem | 34,1 ± 2,4 (stat 0,6) [Certain] | Zhang et al. 2024 |
| idem | 35,2 ± 1,0 (Binney 2020) ; 35,5 ± 0,8 (Chiba & Schönrich 2021) ; 35 à 40 (Dillamore 2023, 2024) [Certain via Zhang 2024] | — |
| Ralentissement | −4,5 ± 1,4 km/s/kpc par Ga [Certain] | Chiba, Friske & Schönrich 2021, MNRAS 500, 4710, arXiv:1912.04304 |
| Statut | « consensus déplacé vers une barre longue et lente (30–40) ; débat non clos » [Certain] | Hunt & Vasiliev 2025 |

Fourchette à retenir : **33 à 41 km/s/kpc**, centre ≈ 36 à 37 [Supposition]. La valeur 39 ± 3,5 de l'appli reste dans la fourchette ; les mesures de 2020 à 2024 tirent vers 34 à 36.

Rapport ℛ = rayon de corotation / demi-longueur, avec la courbe de rotation de l'appli [Supposition : calculé] :

| Ω (km/s/kpc) | Corotation (kpc) | ℛ (barre de 5,0 kpc) |
|---|---|---|
| 41 | 5,7 | 1,15 |
| 39 | 6,0 | 1,21 |
| 33,3 | 7,0 | 1,41 |
| **20 (film 2)** | **11,4** | **2,28** |

Les barres observées ont ℛ entre 1,0 et 1,4 (« rapides ») [Probable : Aguerri et al. 2015 ; Cuomo et al. 2020]. Le film à 20 km/s/kpc est hors de tout ce qui est observé ; c'est aussi pourquoi la barre « occupe presque tout le disque » (`docs/deuxieme-film.md:34`) : une barre peut s'étendre jusqu'à sa corotation.

Causes physiques connues, et ce que fait le code :
1. **Frottement dynamique de la barre sur le halo** (Debattista & Sellwood 2000 ; Athanassoula 2003) [Probable]. Un halo dense au centre freine la barre. Le halo du calcul est tiré par `agama` en « QuasiSpherical » sans rotation (`modeles_v2.py:155`) [Certain].
2. **Rotation du halo** : les halos cosmologiques ont un paramètre de spin λ ≈ 0,035 à 0,04 (Bullock et al. 2001 ; Bett et al. 2007) [Probable]. Un halo en rotation prograde fait naître la barre plus vite mais peut ensuite l'affaiblir ; l'effet sur le freinage dépend du spin (Saha & Naab 2013 ; Long, Shlosman & Heller 2014 ; Collier, Shlosman & Heller 2018 ; Kataria & Shen 2022) [Probable]. Ce n'est donc pas un remède garanti : à essayer, comme le propose déjà `docs/deuxieme-film.md:49-51`.
3. **Gaz** : dans un disque avec gaz, le gaz cède du moment cinétique à la barre et elle ne ralentit pas (Beane et al. 2023, ApJ 953, 173) [Probable]. Le deuxième film n'avait pas de gaz ; le calcul de film-3 en a : la vitesse de la barre doit être remesurée là avant toute autre correction.
4. **Rapport baryons / matière noire au centre** : les simulations qui donnent des barres rapides sont celles où les étoiles dominent le centre (Fragkoudi et al. 2021, A&A 650, L16) [Probable]. Portail 2017 mesure seulement 0,32 ± 0,05 × 10¹⁰ M☉ de matière noire dans la boîte du bulbe pour 1,32 d'étoiles [Certain : docs § 7].
5. **Âge de la barre** : le mûrissement de 3 Ga seul puis 3 Ga de trajet laisse 6 Ga de freinage sans gaz. La barre réelle a ≈ 8 Ga (Sanders et al. 2024 ; Bovy et al. 2019) [À vérifier] mais elle a vécu avec du gaz.

`galaxie_orbites.h:28-32, 72-90` (orbites des étoiles Gaia) : barre quadripolaire de Dehnen 2000, α = 0,01, vitesse constante 39 km/s/kpc. Limite [Supposition] : avec une incertitude de ± 3,5 km/s/kpc, la phase de la barre est inconnue à ± 20° après 100 Ma et à plus d'un tour après 2 Ga ; avec le ralentissement mesuré (−4,5 par Ga), l'erreur de phase d'une barre à vitesse constante atteint 2,3 rad à 1 Ga. L'orientation de la barre affichée au-delà de ± 100 à 200 Ma est un modèle, à signaler comme tel.

### 1.6 Bras spiraux

- Reid et al. 2019 (≈ 200 parallaxes de masers) : spirale à quatre bras, bras logarithmiques ajustés par segments, angles d'enroulement de ≈ 7° à 20° selon les bras ; bras Norma-Extérieur, Écu-Centaure, Sagittaire-Carène, Persée, plus le bras local (segment isolé) [Certain pour « quatre bras » et la méthode ; Probable pour les angles].
- Vitesse du motif spiral : non établie ; valeurs publiées 20 à 28 km/s/kpc pour un motif rigide, ou bras transitoires qui tournent avec la matière (Hunt & Vasiliev 2025 discutent les deux) [Probable].
- Appli : pas de bras dans le potentiel des orbites (`galaxie_orbites.h:10`, « vitesse non établie ») [Certain]. Choix honnête. Dans le N-corps avec gaz, les bras naissent d'eux-mêmes ; le deuxième film sans gaz ne les refaisait pas (`docs/deuxieme-film.md:45`).

### 1.7 Chauffage du disque (relation âge-agitation)

- Forme : σ(τ) ∝ τ^β. Au voisinage solaire, β_R ≈ 0,3 et β_z ≈ 0,45 à 0,5 (Aumer & Binney 2009 : 0,31 et 0,45 ; Mackereth et al. 2019, MNRAS 489, 176 ; Sharma et al. 2021, MNRAS 506, 1761) [Probable].
- Ordres de grandeur au Soleil : σ_z ≈ 8 à 10 km/s à 1 Ga, ≈ 20 à 25 km/s à 8–10 Ga pour le disque mince ; ≈ 40 à 50 km/s pour le disque épais ancien [Probable].
- Hauteur associée : le disque mince reste à ≈ 0,3 kpc après ≈ 8 Ga de chauffage réel.
- Film 2 : vieilles étoiles 0,55 → 0,91 kpc en 3 Ga, jeunes 0,10 → 0,64 kpc en 3 Ga [Certain, `docs/deuxieme-film.md:36-39`]. C'est un chauffage 5 à 10 fois trop rapide [Supposition]. Le dépôt a déjà écarté le grain du halo (essai à particules 4 fois plus légères) ; la cause est la barre lente et géante (§ 1.5), dont le flambage épaissit normalement seulement l'intérieur (bulbe en cacahuète, |z| ≲ 1 kpc à R ≲ 2,5 kpc ; Ness & Lang 2016 : X jusqu'à 2,4 kpc [Certain via la revue]).
- Chauffage numérique : Ludlow et al. 2021 (MNRAS 508, 5114) donnent le chauffage parasite du disque par les particules de halo en fonction de leur masse [Probable]. Le calcul vise un rapport de masse halo/étoile < 10 (`modeles_v2.py:150`) : bonne pratique.

### 1.8 Gauchissement et évasement

| Grandeur | Valeur | Source |
|---|---|---|
| Début du gauchissement | R ≈ 9 à 11 kpc ; amplitude ≈ 1 kpc vers 14–16 kpc (étoiles), jusqu'à 3–4 kpc à 25 kpc (HI) [Probable] | Chen et al. 2019, Nat. Astron. 3, 320 (Céphéides) ; Levine, Blitz & Heiles 2006 (HI) |
| Précession | 10,86 ± 0,03 (stat) ± 3,20 (syst) km/s/kpc, dans le sens de la rotation [Certain] | Poggio et al. 2020, Nat. Astron. 4, 590, arXiv:1912.10471 |
| idem, plus récent | valeurs plus faibles ou dépendant du rayon (Cabrera-Gadea et al. 2024 ; Jónsson & McMillan 2024) [À vérifier] | — |
| Évasement | la hauteur des populations jeunes double entre 8 et ≈ 14–16 kpc ; le HI passe de ≈ 0,1–0,15 kpc à ≈ 1 kpc à 25–30 kpc [Probable] | Kalberla & Kerp 2009 ; Mackereth et al. 2017 |
| Ondes verticales locales | creux de comptage à 0,4 ; 0,9 ; 1,5 kpc ; spirale de phase (Antoja et al. 2018) [Certain pour Bennett & Bovy] | Bennett & Bovy 2019 |

Appli : rien dans `galaxie_orbites.h` (potentiel plat, axisymétrique plus barre) [Certain]. Dans le N-corps le plan du disque « penche de 14° en 5 Ga sous l'effet des Nuages » (`docs/deuxieme-film.md:36`) : c'est le bon mécanisme (Laporte et al. 2018) mais l'état d'aujourd'hui (ligne des nœuds proche de la direction anticentre, amplitude 1 kpc à 15 kpc) n'est pas une cible du bulletin.

### 1.9 Halo stellaire, Gaia-Encelade, Sagittaire

| Objet | Valeur | Source |
|---|---|---|
| Halo stellaire, masse | 1,4 ± 0,4 × 10⁹ M☉ [Probable] | Deason, Belokurov & Sanders 2019, MNRAS 490, 3426 |
| Profil | loi de puissance brisée, cassure vers 25–30 kpc (apocentres des débris de Gaia-Encelade) [Probable] | Deason et al. 2018 ; Naidu et al. 2021 |
| Gaia-Saucisse-Encelade | fusion il y a 8 à 11 Ga ; masse stellaire 5 × 10⁸ à quelques 10⁹ M☉ ; rapport de masses ≈ 1:4 (1:2,5 chez Naidu 2021) ; orbites très radiales (anisotropie β ≈ 0,9) [Probable] | Belokurov et al. 2018, MNRAS 478, 611 ; Helmi et al. 2018, Nature 563, 85 ; Naidu et al. 2021, ApJ 923, 92 |
| Sagittaire, reste | ≈ 4 × 10⁸ M☉ dans ≈ 5 kpc ; distance 26,5 kpc ; péricentre ≈ 16 kpc, apocentre ≈ 50 à 70 kpc selon le modèle ; passage au péricentre il y a quelques dizaines de Ma [Probable] | Vasiliev & Belokurov 2020, MNRAS 497, 4162 ; Vasiliev et al. 2021 |
| Sagittaire, masse à l'arrivée | ≳ 6 × 10¹⁰ M☉ (Gibbons, Belokurov & Evans 2017) ; débat [À vérifier] | — |
| Courant du Sagittaire | désalignement du bras de tête expliqué par le passage récent du Grand Nuage ; « indices d'une forme et d'une orientation du halo variables avec le rayon » [Certain] | Vasiliev, Belokurov & Erkal 2021 |

Appli : la naine du Sagittaire est un traceur sans masse (`conditions.json`, dwarfs[1], à 18,2 kpc du centre) ; contrôle du HANDOVER : péricentre 12 kpc, apocentre 48 kpc (publié ≈ 15 et 60 à 70) [Certain]. Le halo stellaire et Gaia-Encelade n'ont pas de dynamique propre ; « le halo d'étoiles garde ses vitesses » (`rencontre.py:368`).

### 1.10 Matière noire : profil, forme, rotation

| Grandeur | Référence | Source | Appli |
|---|---|---|---|
| Profil NFW | ρ = ρ0 / [(r/r_s)(1 + r/r_s)²] | Navarro, Frenk & White 1997, ApJ 490, 493 | utilisé partout (`modeles_v2.py:120`, `galaxie_orbites.h:42`) |
| Profil d'Einasto | ρ ∝ exp{−(2/α)[(r/r_−2)^α − 1]}, α ≈ 0,16 à 0,18 pour un halo de 10¹² M☉ [Probable] | Navarro et al. 2004 ; Gao et al. 2008 | non utilisé |
| Concentration c_200 à 10¹² M☉ | ≈ 8 à 9, dispersion 0,11 dex (soit 6 à 11) [Probable] | Dutton & Macciò 2014, MNRAS 441, 3359 | Voie lactée 11,8 ; Andromède 13,1 ; Triangle 9,6 [Supposition : calculé] |
| Contraction par les baryons | matière noire ×1,3 à 20 kpc, ×2 à 8 kpc, ×4 à 1 kpc par rapport au NFW non contracté [Certain] | Cautun et al. 2020 | absente (NFW pur) |
| Matière noire locale | 0,0088 ± 0,0005 M☉/pc³ (Cautun 2020) ; 0,30 ± 0,03 GeV/cm³ (Eilers 2019) ; 0,0101 (McMillan 2017) [Certain] | — | 0,0101 (N-corps) ; 0,0098 (orbites) |
| Forme du halo interne | proche de sphérique, q ≈ 0,8 à 1,0 dans 20 kpc (Koposov, Rix & Hogg 2010 : GD-1 ; Bovy et al. 2016 ; Hattori et al. 2021) ; q ≈ 1,3 (Posti & Helmi 2019) [Probable] | — | sphérique |
| Forme du halo externe | variable avec le rayon, triaxiale et tordue au-delà de ≈ 50 kpc ; déformée par le Grand Nuage [Certain pour l'énoncé] | Vasiliev et al. 2021 | sphérique au départ ; se déforme dans le N-corps |
| Rotation du halo | λ ≈ 0,035 à 0,04 dans les simulations ; non mesurée pour la Voie lactée [Probable] | Bullock et al. 2001, ApJ 555, 240 | λ = 0 |

Les concentrations du calcul (11,8 et 13,1) sont au-dessus de la médiane cosmologique (8 à 9), à +1 σ environ ; pour un NFW non contracté ajusté sur des données, c'est le résultat attendu puisque la concentration élevée imite la contraction [Supposition].

### 1.11 Frottement dynamique et résolution numérique

- **Chandrasekhar (1943)** : dv/dt = −4π G² M ρ lnΛ [erf(X) − 2X e^(−X²)/√π] v / v³, X = v / (√2 σ) (Binney & Tremaine 2008, éq. 8.7) [Probable]. Valable pour un corps compact dans un milieu infini homogène ; pour un satellite étendu, lnΛ ≈ ln(r / 1,4 ε) (Hashimoto, Funato & Makino 2003) [Probable].
- Sawala 2025 : Chandrasekhar modifié pour satellites étendus, appliqué sous r_200 de l'hôte, dispersion NFW de Zentner & Bullock 2003, force répartie entre satellite et hôte au prorata des masses, adoucissement 20 kpc, fusion sous 20 kpc, saut de grenouille de 1 Ma [Certain]. `groupe_local_clones.py:9-11` le reproduit [Certain].
- N-corps de l'appli : le frottement n'est pas une formule, il sort des particules (`rencontre.py:102-134`). C'est le traitement le plus fidèle, à condition que le halo hôte ait assez de particules et le bon profil de densité à 30–100 kpc (voir § 1.3 : densité trop forte de 25 à 50 %, donc frottement trop fort d'autant [Supposition]).
- **Relaxation à deux corps** : t_relax ≈ [N / (8 ln N)] t_traversée (Binney & Tremaine 2008, éq. 1.38). Rayon de convergence : celui où t_relax dépasse l'âge du système (Power et al. 2003, MNRAS 338, 14) [Probable].
- **Adoucissement** : optimum ε ∝ N^(−1/3) (Dehnen 2001, MNRAS 324, 273) ; le code fait ε = 0,1 (36 000 / N)^(1/3) kpc pour les étoiles et 4 fois plus pour le halo (`modeles_v2.py:157-158`) [Certain]. Noyau de Plummer, ε_ij² = (ε_i² + ε_j²)/2 (`gravite_gpu.py:14, 123`) : le Plummer biaise la force jusqu'à ≈ 10 ε ; un noyau spline compact (Springel 2005) est exact au-delà de 2,8 ε [Probable]. Effet : faible.
- **Pas de temps** : fixe, 0,25 Ma pour toutes les particules (`rencontre.py:199`) [Certain]. Critère usuel : dt ≤ η √(ε / |a|), η ≈ 0,2 (Power et al. 2003). Au centre (r ≈ 0,1 kpc, v ≈ 150 km/s, ε ≈ 0,03 kpc) : dt ≲ 0,07 Ma [Supposition : calculé]. Le pas est donc 3 fois trop long pour les 100 pc centraux ; correct au-delà de ≈ 0,5 kpc. L'énergie tenue à 0,04 % ne prouve pas que le centre est bien intégré.
- **Arbre** : Barnes-Hut, θ = 0,7 dans les tirs (`rencontre.py:105`), quadripôles, forces en simple précision (`gravite_gpu.py:18`) [Certain]. Erreur de force typique ≈ 0,1 à 0,5 % avec quadripôles à θ = 0,7 [Probable]. L'arbre ne conserve pas exactement la quantité de mouvement ; le recentrage par galaxie masque une dérive éventuelle du centre de masse [Supposition].

---

## 2. Groupe local

### 2.1 Andromède (M31)

| Grandeur | Valeur | Source | Appli (`univers.json`) |
|---|---|---|---|
| Distance | 761 ± 11 kpc (module 24,407 ± 0,032) [Certain] | Li et al. 2021, ApJ 920, 84, arXiv:2107.08029 (Céphéides, HST) | 761,0 (table) ; 783–787 dans `conditions.json` (ancien) |
| idem | 785 ± 25 kpc (McConnachie et al. 2005, pointe des géantes rouges) ; 765 à 785 selon les méthodes [Probable] | — | — |
| Vitesse radiale héliocentrique | −301 ± 1 km/s [Certain via Sawala] | — | −301,0 |
| Vitesse radiale / Voie lactée | −109,3 ± 4,4 km/s [Certain] | van der Marel et al. 2012, ApJ 753, 8, arXiv:1205.6864 | −113,8 [calculé ici depuis la table] |
| Mouvement propre (HST) | vitesse héliocentrique transverse (v_W, v_N) = (−125,2 ± 30,8 ; −73,8 ± 28,4) km/s ; V_tan = 17,0 km/s, < 34,3 à 1 σ [Certain] | van der Marel et al. 2012 | — |
| Mouvement propre (Gaia DR2) | (65 ± 18 ; −57 ± 15) µas/an, syst 16 ; V_tan = 57 (+35 −31) km/s avec HST [Certain] | van der Marel et al. 2019, ApJ 872, 24, arXiv:1805.04079 | — |
| Mouvement propre (Gaia EDR3) | 61,9 ± 9,7 µas/an (module, corrigé) ; V_tan = 82,4 ± 31,2 km/s [Certain] | Salomon et al. 2021, MNRAS 507, 2592, arXiv:2012.09204 | variante « sawala2025 » : (48,9 ± 10,5 ; −36,9 ± 8,1) |
| Mouvement propre (Gaia DR3, supergéantes) | (45,9 ± 8,1 ; −20,5 ± 6,6) µas/an [Certain : valeur dans la table ; article non relu par moi] | Wu et al. 2025, A&A 701, A265 | valeur centrale : V_tan = 27,6 km/s [calculé ici] |
| Orbite purement radiale | (38,03 ; −21,37) µas/an [Certain] | Sawala et al. 2025 | à 1 σ de la valeur de la table |
| Masse (courbe de rotation) | M_vir = 1,14 (+0,51 −0,35) × 10¹² M☉ dans 220 ± 25 kpc ; rotation ≈ 220 km/s jusqu'à 25 kpc puis ≈ 170 km/s vers 125 kpc [Certain] | Zhang et al. 2024, arXiv:2401.01517 | 1,065 × 10¹² |
| Masse (vitesse d'échappement) | 0,8 ± 0,1 × 10¹² M☉ [Certain : docs] | Kafle et al. 2018, arXiv:1801.03949 | — |
| Masse (mouvements propres des satellites) | 2,85 (+1,47 −0,77) × 10¹² (HST) ; 3,02 (+1,30 −0,69) × 10¹² (HST + Gaia) [Certain] | Patel & Mandel 2023, ApJ 948, 104, arXiv:2211.15928 | — |
| Masse (halo NFW ajusté) | 1,04 × 10¹² dans 207 kpc [Certain : docs] | Tamm et al. 2012, A&A 546, A4 | source du modèle |
| Masse adoptée par Sawala | 1,3 ± 0,4 × 10¹² M☉ [Certain] | Sawala et al. 2025 | — |
| Rapport Voie lactée / Andromède | 0,54 (+0,23 −0,17) ; Voie lactée plus lourde exclue à ≈ 95 % [Certain] | Peñarrubia et al. 2014, MNRAS 443, 2204, arXiv:1405.0306 | **1,26** |
| Étoiles | 10 à 15 × 10¹⁰ M☉ [Certain : docs] | Tamm et al. 2012 | 8,7 × 10¹⁰ (borne basse) |

Lecture [Supposition] : le modèle d'Andromède est construit sur les bornes basses (disque « borne basse » de Tamm, halo de Tamm) et la Voie lactée sur une valeur haute (McMillan). Résultat : Voie lactée 26 % plus lourde qu'Andromède, alors qu'Andromède a environ deux fois plus d'étoiles et que le seul rapport de masses mesuré dynamiquement donne l'inverse. Un couple plus central serait Voie lactée ≈ 1,0 à 1,1 et Andromède ≈ 1,3 à 1,6 × 10¹² M☉ (somme inchangée ≈ 2,4 à 2,7).

### 2.2 Fusion Voie lactée – Andromède

| Étude | Résultat | Méthode | Source |
|---|---|---|---|
| van der Marel et al. 2012 (III) | premier péricentre dans 3,87 (+0,42 −0,32) Ga ; fusion dans 5,86 (+1,61 −0,72) Ga ; choc direct (< 25 kpc) 41 % ; Triangle : heurte la Voie lactée en premier 9 %, éjecté 7 % ; Soleil plus loin du centre qu'aujourd'hui 85 % [Certain] | N-corps et orbites, mouvement propre HST | ApJ 753, 9, arXiv:1205.6865 |
| van der Marel et al. 2019 | orbite moins radiale ; premier péricentre plus tardif (≈ 4,5 Ga) et plus lointain (≈ 130 kpc) [Probable : non dans la page lue] | Gaia DR2 + HST | ApJ 872, 24 |
| Sawala et al. 2025 | à 10 Ga : deux corps « un peu moins de la moitié » ; avec le Triangle ≈ 2/3 ; avec le Grand Nuage seul « un peu plus de 1/3 » ; les quatre : « juste au-dessus de 50 % » ; temps médian de fusion 7,6 Ga (seuil 20 kpc), 8,0 Ga (seuil 10 kpc) ; distribution bimodale (fusion, ou distance minimale > 200 kpc) ; le Grand Nuage fusionne à coup sûr avec la Voie lactée (période ≈ 1,5 Ga) [Certain] | points massifs à halos NFW, frottement de Chandrasekhar, Monte-Carlo sur les mesures ; **pas d'énergie noire** | Nat. Astron. 2025, doi 10.1038/s41550-025-02563-1, arXiv:2408.00064 |
| Wu et al. 2026 | fusion dans ≈ 90 % des cas, médiane 6,5 (+1,3 −1,5) Ga ; 64,7 % à 100 % dans la zone à 2 σ du mouvement propre : « non concluant » [Certain] | méthode de Sawala, mouvement propre de Wu 2025 | arXiv:2603.22863 |
| Film 2 de l'appli | premier passage à +5,63 Ga à 14 kpc ; centres réunis après +6,75 Ga ; Triangle s'échappe ; Nuages absorbés [Certain, `docs/deuxieme-film.md:23-24`] | N-corps complet, énergie noire | — |

Le film tombe près de la médiane de Wu 2026 (6,5 Ga) : cohérent avec son mouvement propre d'entrée. Il doit rester étiqueté « scénario » (règle 4 de `docs/verite-avenir.md`) avec la probabilité de l'ensemble (`ensemble_unifie.json`) [Supposition].

### 2.3 Triangle (M33)

| Grandeur | Valeur | Source | Appli |
|---|---|---|---|
| Distance | 859 kpc (module 24,67 ± 0,07, Ou et al. 2023 via Sawala) ; 794 à 968 kpc dans la littérature ; 840 (Corbelli 2014) [Certain pour les deux premières sources citées] | — | 859 (table) ; 809 (`conditions.json`) |
| Mouvement propre | (31 ± 19 ; −29 ± 16) µas/an (Gaia DR2) [Certain] ; VLBA des masers (Brunthaler et al. 2005, Science 307, 1440) [Probable] | van der Marel et al. 2019 | (30,6 ± 5,7 ; +19,0 ± 5,7) : moyenne Wu 2025 + VLBA |
| Masse du halo | 4,3 ± 1,0 × 10¹¹ M☉ (Corbelli 2014) ; 3 ± 1 × 10¹¹ (Sawala) [Certain] | — | 4,08 × 10¹¹ |
| Lien avec Andromède | lié à 95 % (van der Marel 2012) ; « premier passage » probable (Patel, Besla & Sohn 2017 ; van der Marel 2019) [Certain pour 2012 et 2019] | — | **non lié** [calculé ici] |

Calcul fait ici [Supposition] à partir de `univers.json` : Triangle par rapport à Andromède, distance 230 kpc, vitesse relative 248 km/s (dont −151 km/s radiale). Vitesse de libération de deux masses ponctuelles de 1,065 et 0,408 × 10¹² M☉ à 230 kpc : 235 km/s. Le signe de la composante en déclinaison du mouvement propre change entre les deux variantes (−29 et +19 µas/an) : le sort du Triangle dépend de cette seule mesure et de la masse d'Andromède. Avec 3,0 × 10¹² M☉ pour Andromède, la vitesse de libération monte à 357 km/s et le Triangle reste lié.

### 2.4 Grand Nuage de Magellan

| Grandeur | Valeur | Source | Appli |
|---|---|---|---|
| Distance | 49,59 ± 0,09 ± 0,54 kpc (module 18,477 ± 0,026) [Probable] | Pietrzyński et al. 2019, Nature 567, 200 | 49,59 |
| Mouvement propre | (1,910 ± 0,020 ; 0,229 ± 0,047) mas/an [Certain : docs] | Kallivayalil et al. 2013, ApJ 764, 161 | identique ; vitesse 323 km/s, dont 317 tangentielle [calculé ici] ; publié 321 ± 24 km/s [Probable] |
| Masse totale | 1,38 (+0,27 −0,24) × 10¹¹ M☉ [Certain] | Erkal et al. 2019 | 1,379 × 10¹¹ |
| idem | 1,3 ± 0,3 × 10¹¹ M☉ [Certain] | Vasiliev, Belokurov & Erkal 2021 | conforme |
| Masse enfermée | 7,02 ± 0,9 × 10¹⁰ M☉ à 32,8 kpc ; halo jusqu'à 53 kpc au moins [Certain] | Koposov et al. 2023 | 7,2 × 10¹⁰ (Hernquist 2,29 × 10¹¹, a = 25,8 kpc, avant effet de la coupure) [calculé ici] : conforme |
| idem | M(< 50 kpc) = 9,2 (+1,9 −2,3) × 10¹⁰ M☉ [Certain] | Brooks et al. 2025, arXiv:2510.04735 | — |
| Rapport au halo galactique | « au moins 15 % de la Voie lactée » ; meilleur accord avec un halo de 1,8 × 10¹¹ M☉ [Certain] | Chandra et al. 2025, arXiv:2406.01676 | 10 % (1,38 / 13,4) |
| Reflux de la Voie lactée | 32 ± 4 km/s, apex (l, b) = (56 ± 9° ; −34 (+10 −9)°), halo de 40 à 120 kpc [Certain] | Petersen & Peñarrubia 2021, Nat. Astron. 5, 251, arXiv:2011.10581 | sort du N-corps ; absent des orbites d'étoiles |
| idem, révisé | 6 (+5 −4) km/s à 40 kpc, 37 ± 9 km/s à 100 kpc, 47 ± 12 à 120 kpc ; apex (l, b) ≈ (−80° ; −59°), proche de la position actuelle du Nuage ; le signal de 2021 serait contaminé par le courant du Sagittaire [Certain] | Chandra et al. 2025 | — |
| idem | 26,4 (+5,5 −4,4) km/s (moyenne sur la distance) [Certain] | Brooks et al. 2025 | — |
| Histoire orbitale | premier passage (Besla et al. 2007 ; Kallivayalil et al. 2013) ; ou second passage, le précédent il y a 5 à 10 Ga à plus de 100 kpc [Certain pour Vasiliev] | Vasiliev 2024, MNRAS 527, 437, arXiv:2306.04837 | départ à −3 Ga seulement : indifférent |
| Fusion future | dans ≈ 2,4 (+1,2 −0,8) Ga [Certain : `docs/verite-avenir.md`] | Cautun et al. 2019, MNRAS 483, 2185 | « absorbés » dans le film |

Remarque [Supposition] : c'est le rapport de masses Nuage / Voie lactée qui fixe le reflux. Avec une Voie lactée à 1,34 × 10¹² M☉, le rapport du calcul (10 %) est sous la borne « au moins 15 % » de Chandra 2025. Baisser la Voie lactée vers 1,0 à 1,1 × 10¹² M☉ corrige les deux écarts à la fois (§ 1.3).

### 2.5 Petit Nuage de Magellan

- Mesures : mouvement propre (0,772 ; −1,117) mas/an, 145,6 km/s, ≈ 62 kpc (Kallivayalil et al. 2013 ; Graczyk et al. 2020) [Certain : docs] ; masse dynamique 2,4 × 10⁹ M☉ dans 3 kpc (Stanimirović et al. 2004) ; matière noire 1 à 1,5 × 10⁹ M☉ dans 4 kpc (Di Teodoro et al. 2019) [Certain : docs].
- Masse totale avant marée : non mesurée ; les modèles de la paire des Nuages prennent ≈ 2 × 10¹⁰ M☉ à l'arrivée (Besla et al. 2012, MNRAS 421, 2109) et l'appariement d'abondance donne 1 à 5 × 10¹⁰ pour 3 à 5 × 10⁸ M☉ d'étoiles [Probable].
- Appli : 3 × 10⁹ M☉ au total, halo coupé à 10 kpc (`univers.json`, « adoptée, pas mesurée ») [Certain]. C'est la masse liée d'aujourd'hui dans ≈ 4 kpc, pas la masse du halo. Pour un départ à −3 Ga, avant les dernières rencontres avec le Grand Nuage (il y a ≈ 150 Ma et ≈ 1 à 2 Ga [Probable]), une masse de 1 à 2 × 10¹⁰ M☉ serait plus fidèle [Supposition]. Le Courant magellanique et le Pont (gaz) en dépendent.

### 2.6 Naines

- Catalogue de référence : McConnachie 2012, AJ 144, 4 (≈ 100 galaxies du Groupe local et voisines ; positions, distances, vitesses, masses, métallicités), mis à jour en ligne par l'auteur (dernière version publique 2021) [Probable]. Successeur ouvert : Pace 2024, « Local Volume Database », arXiv:2411.07424 [Probable ; déjà cité dans `docs/verite-avenir.md`].
- Mouvements propres systémiques Gaia EDR3 : McConnachie & Venn 2020 (RNAAS 4, 229) ; Battaglia et al. 2022 (A&A 657, A54) ; Pace, Erkal & Li 2022 (ApJ 940, 136) [Probable].
- Biais connu : les orbites des satellites calculées sans le Grand Nuage sont fausses pour une partie d'entre eux (Patel et al. 2020, ApJ 893, 121 ; Pace et al. 2022) [Probable].
- Appli : 8 naines en traceurs sans masse (`conditions.json`), portées par le film (`groupe_local.h:60-64`) ; leur orbite hérite donc correctement du Grand Nuage et du reflux, ce qui est mieux qu'un potentiel fixe.

### 2.7 Argument de temps, avec Λ

Sans Λ, orbite radiale képlérienne partie de r = 0 au Big Bang (Kahn & Woltjer 1959, ApJ 130, 705) :

- r = a (1 − cos η), t = (a³ / GM)^½ (η − sin η), d'où v t / r = sin η (η − sin η) / (1 − cos η)².
- Calcul fait ici [Supposition] avec t = 13,8 Ga : r = 761 kpc et v = −109,3 km/s donnent M = 4,1 × 10¹² M☉ ; avec −113,8 km/s : 4,3 × 10¹² ; à 785 kpc : 4,3 à 4,5 × 10¹².

Avec Λ : équation du mouvement r̈ = −GM / r² + H0² Ω_Λ r (Partridge, Lahav & Hoffman 2013, MNRAS 436, L45 ; Peñarrubia et al. 2014). La masse déduite monte de ≈ 10 à 15 % [Certain : `energie_noire.py:10-12` ; Probable pour le chiffre].

| Étude | Masse du Groupe local | Remarques |
|---|---|---|
| Li & White 2008, MNRAS 384, 1459 | 5,27 × 10¹² M☉ (médiane, calibrée sur Millennium) [Probable] | argument de temps calibré |
| van der Marel et al. 2012 | 3,17 ± 0,57 × 10¹² M☉ (somme des masses du viriel, combinaison de méthodes) [Certain] | — |
| Peñarrubia et al. 2014 | 2,3 ± 0,7 × 10¹² M☉ ; rapport 0,54 ; H0 local 67 ± 5 km/s/Mpc [Certain] | modèle du flot de Hubble local avec Λ, naines de 0,8 à 3 Mpc |
| Peñarrubia et al. 2016, MNRAS 456, L54 | 2,64 (+0,42 −0,38) × 10¹² M☉ ; Grand Nuage 0,25 × 10¹² [Probable] | reflux dû au Grand Nuage inclus |
| Benisty et al. 2022, ApJL 928, L5, arXiv:2202.00033 | 3,4 (+1,4 −1,1) × 10¹² M☉ (V_tan = 82) ; 3,1 (+1,3 −1,0) (a priori plat) ; facteur de biais cosmique 0,63 ± 0,2 ; somme des quatre grands membres 3,7 ± 0,5 [Certain] | avec Λ, correction du Grand Nuage, calibration sur simulations |
| Wempe et al. 2026, Nat. Astron., doi 10.1038/s41550-025-02770-w, arXiv:2601.17125 | les masses dynamiques sont réconciliées avec le champ de vitesses si la masse autour du Groupe local est concentrée dans une feuille jusqu'à 10 Mpc, avec des vides au-dessus et au-dessous [Certain] | flot « calme mais fortement anisotrope » |

Appli : somme des cinq modèles = 2,95 × 10¹² M☉ [calculé ici], dans toutes les fourchettes ci-dessus. Le calcul remonte à −3 Ga seulement (`rencontre.py`, `debut_reference_ga`) : il ne teste pas l'argument de temps. L'énergie noire y est mise par rapport au centre de masse des particules lourdes (`rencontre.py:122-124`) : forme exacte pour w = −1 [Certain]. Non modélisés : la marée des masses extérieures (feuille locale, groupes M81, Centaurus A, Maffei, amas de la Vierge) et la croissance des halos sur 3 Ga [Supposition : effets de quelques %].

### 2.8 Flot de Hubble local et rayon de retournement

| Grandeur | Valeur | Source |
|---|---|---|
| Rayon de vitesse nulle | R0 = 0,96 ± 0,03 Mpc, d'où M = 1,9 ± 0,2 × 10¹² M☉ [Probable] | Karachentsev et al. 2009, MNRAS 393, 1265 |
| Relation sans Λ | M = π² R0³ / (8 G T0²) (Lynden-Bell 1981) ; avec Λ la masse monte de ≈ 30 % à R0 fixé [Probable] | Peirani & de Freitas Pacheco 2008 |
| Calcul ici, sans Λ, T0 = 13,8 Ga | M = 2,4 × 10¹² → R0 = 1,19 Mpc ; 3,2 × 10¹² → 1,31 Mpc [Supposition] | — |
| Froideur du flot | dispersion ≈ 25 à 40 km/s autour de la loi de Hubble entre 1 et 3 Mpc [Probable] | Karachentsev et al. 2009 ; Peñarrubia et al. 2014 |
| Rayon d'équilibre gravité / Λ | r = (GM / H0² Ω_Λ)^⅓ = 1,49 Mpc pour 2,4 × 10¹² M☉ ; 1,61 Mpc pour 3,0 × 10¹² [Supposition : calculé] | — |
| Poids de Λ à 761 kpc | a_Λ / a_grav = 13 % (2,4 × 10¹²) ; 11 % (3,0 × 10¹²) ; 8 % (4,0 × 10¹²) [Supposition : calculé] | cohérent avec `energie_noire.py:9` (« environ 15 % » pour 2 × 10¹²) |

L'écart entre R0 mesuré (0,96 Mpc) et la valeur attendue pour 3 × 10¹² M☉ (1,2 à 1,3 Mpc) est précisément la tension que Wempe et al. 2026 résolvent par la géométrie en feuille [Certain pour l'énoncé de l'article]. Pour l'appli : les naines isolées entre 1 et 3 Mpc ne peuvent pas être animées correctement par un Groupe local isolé à symétrie sphérique ; leur mouvement futur est un modèle.

---

## 3. Comparaison fichier par fichier

| Fichier | Ce qu'il fait | Verdict |
|---|---|---|
| `pipeline/fusion/modeles_v2.py` | galaxies à l'équilibre (AGAMA), halo NFW sphérique sans rotation, disques exponentiels, Q réglé | disques conformes ; halo galactique lourd à 30–100 kpc ; disque épais trop long (3,02 contre 2,0 kpc) ; gaz sans trou central ; pas de contraction ; λ = 0 |
| `pipeline/fusion/conditions.json` | conditions de l'ANCIEN calcul (`calcul.py`) | périmé : Andromède à 787 kpc, Triangle à 809 kpc, v0 = 230, axes de rotation du Triangle et du Grand Nuage faux (déjà dit dans `docs/parametres-galaxies.md:170-171`). À ne plus lire nulle part |
| `pipeline/fusion/film_v2.py` | lecteur du film, Catmull-Rom entre images, vitesses par différences | correct ; sous-échantillonnage du centre (10 Ma par image, `rencontre.py:483`) ; float16 : pas de 8 pc à 8–16 kpc, 62 pc à 64–128 kpc [Supposition] |
| `pipeline/fusion/gravite_gpu.py` | arbre de Barnes-Hut, quadripôles, Plummer | conforme à l'état de l'art pour un code à arbre ; pas de temps unique, voir § 1.11 |
| `pipeline/fusion/bulletin.py` + `resultats/mesures_voie_lactee.json` | 9 mesures cibles | valeurs justes ; marge de la barre (39 ± 3,5) à élargir ou recentrer (33–41) ; manquent : masse enfermée à 30, 50, 100 kpc, pente de la courbe de rotation, rapport corotation / longueur, agitation verticale, hauteur à plusieurs rayons (évasement), gauchissement, masse du bulbe + barre |
| `natif/physique/groupe_local.h` | rejeu du PREMIER calcul (300 000 particules, fusion à 5,44 Ga) | ligne droite entre images de 20 Ma (`:9`) : à 2 kpc du centre une orbite dure ≈ 60 Ma, soit 3 images par tour ; la corde raccourcit le rayon jusqu'à 50 % à mi-chemin [Supposition]. Remplacé par `film_v2.h` (Catmull-Rom) : à retirer quand le film 2/3 est en place |
| `natif/physique/galaxie_orbites.h` | orbites des étoiles Gaia dans un potentiel fixe + barre + Λ | courbe de rotation correcte à 3 % de 4 à 25 kpc ; halo 1,03 × 10¹² (mieux que le N-corps !) ; ni Grand Nuage, ni reflux, ni bras, ni gauchissement, ni ralentissement de la barre ; deux modèles de masse différents coexistent donc dans l'appli (celui-ci et McMillan) |
| `natif/physique/champ_bfe.h` | évaluateur du champ en coefficients (multipôles + grille cylindrique), « branché nulle part » (`:12`) | c'est le bon outil pour unifier : champ du N-corps (barre, Nuage, reflux, déformation du halo compris) réutilisé pour les orbites des étoiles Gaia. Technique standard (Sanders et al. 2020 ; Garavito-Camargo et al. 2021 ; Lilleengen et al. 2023) [Probable] |
| `docs/deuxieme-film.md` | écarts connus | diagnostics justes ; ajouter le rapport ℛ = 2,3 et la piste du gaz et du rapport baryons / matière noire |
| `docs/parametres-galaxies.md` | paramètres relus | justes ; il manque les masses enfermées par courants (postérieures à McMillan 2017) et le rapport de masses de Peñarrubia 2014 |
| `docs/grand-livre-masses.md` | écarts entre fichiers | à jour sur les incohérences internes ; ne compare pas aux mesures externes de § 1.3 |

---

## 4. Écarts avec l'appli, classés par impact sur le réalisme

### Fort

1. **Barre deux fois trop lente et envahissante** (20 km/s/kpc contre 33–41 ; ℛ = 2,3 contre 1,2–1,4). Elle entraîne l'épaississement du disque (0,55 → 1,24 kpc en 5 Ga) et l'aspect de la Voie lactée à toutes les dates futures. Pistes dans l'ordre : mesurer la barre du calcul AVEC gaz (film-3) ; réduire la matière noire dans les 5 kpc centraux ou augmenter la masse stellaire du centre (Portail 2017 : 1,88 × 10¹⁰ M☉ de barre + bulbe) ; halo en rotation (λ ≈ 0,035) ; mûrissement plus court. Ajouter au bulletin : corotation / longueur.
2. **Rapport de masses Voie lactée / Andromède inversé** (1,26 contre 0,54 (+0,23 −0,17)). Change la date de fusion, le mouvement du centre de masse, le sort du Triangle. Proposition [modèle] : Voie lactée ≈ 1,0–1,1 × 10¹² (Cautun 2020), Andromède ≈ 1,3–1,6 × 10¹², et garder l'ensemble Monte-Carlo pour dire la dispersion.
3. **Halo de la Voie lactée trop lourd entre 30 et 100 kpc** (+23 % à +52 % par rapport aux courants). Fausse l'orbite et l'absorption du Grand Nuage, le Sagittaire, le reflux (rapport Nuage / Voie lactée de 10 % contre ≥ 15 %). Ajouter au bulletin les trois masses enfermées (Koposov 2023, Erkal 2019, Vasiliev 2021).
4. **Un seul film pour un avenir bimodal.** Selon le mouvement propre retenu, la fusion est probable à ≈ 50 % (Sawala 2025) ou ≈ 90 % (Wu 2026). Le film montre le cas « fusion à 6,75 Ga ». L'appli doit l'afficher comme scénario avec sa probabilité, et idéalement proposer le second scénario (passage au large, > 200 kpc).
5. **Triangle non lié à Andromède dans la table** (248 km/s pour 235 de libération), conséquence du point 2 et d'un mouvement propre dont le signe en déclinaison diffère selon les sources. À signaler dans l'appli comme incertain ; à relire dans Wu 2025.

### Moyen

6. **Deux modèles de masse de la Voie lactée** : MWPotential2014 recalé pour les étoiles Gaia (`galaxie_orbites.h`), McMillan 2017 pour le N-corps. Brancher `champ_bfe.h` sur le champ du N-corps supprime l'écart et apporte d'un coup le Grand Nuage, le reflux, la barre vivante.
7. **Orbites des étoiles Gaia sans Grand Nuage ni reflux** : au-delà de ≈ 30 kpc et de ± 200 Ma, les orbites du halo, des amas et des naines sont fausses de quelques dizaines de km/s (reflux 26 à 47 km/s).
8. **Barre à vitesse constante dans `galaxie_orbites.h`** : phase inconnue au-delà de ± 100 à 200 Ma (incertitude ± 3,5 km/s/kpc ; ralentissement −4,5 ± 1,4 km/s/kpc/Ga). À signaler comme modèle ; option : Ω(t) = 39 − 4,5 t.
9. **Petit Nuage sous-pesé** (3 × 10⁹ M☉ au lieu de ≈ 1 à 2 × 10¹⁰ à −3 Ga) : affaiblit le Pont et le Courant magellaniques, donc l'aspect du gaz autour des Nuages.
10. **Halo sphérique, sans rotation, sans contraction** : la forme mesurée varie avec le rayon ; la contraction double la matière noire à 8 kpc par rapport à un NFW de mêmes M_200 et c. À traiter avec le point 3 (modèle Cautun 2020).
11. **Disque épais trop étendu** (3,02 kpc contre 2,0 ± 0,2) et **gaz sans trou central** (McMillan : HI troué à 4 kpc, H2 à 12 kpc) : trop de gaz et d'étoiles vieilles au mauvais endroit ; pèse sur la naissance d'étoiles centrale et sur la barre.
12. **Gauchissement et évasement absents des cibles** : le N-corps penche le disque de 14° en 5 Ga mais l'état actuel (≈ 1 kpc à 15 kpc, précession 10,9 ± 3,2 km/s/kpc) n'est ni imposé ni contrôlé.
13. **Pas de temps unique de 0,25 Ma** : 3 fois trop long pour les 100 pc centraux selon le critère usuel ; touche le cœur du bulbe et la naissance de la barre. Essai simple : un tir à 0,1 Ma, comparer la barre.
14. **Échantillonnage du film** (10 Ma par image) : orbites du centre (< 0,5 kpc, période < 20 Ma) repliées. Remède : écrire aussi les vitesses (Hermite) ou une image tous les 2 à 5 Ma pour le cœur.

### Faible

15. Vitesse totale du Soleil 245,0 km/s contre 248,5 à 251,5 (Sgr A*, Clarke & Gerhard 2022) : 1,5 à 2,5 %.
16. Hauteur du Soleil 6,6 pc contre 20,8 ± 0,3 pc.
17. Pente de la courbe de rotation de `galaxie_orbites.h` : −1,0 contre −1,3 à −1,7 km/s/kpc.
18. Marge de la vitesse de barre dans `mesures_voie_lactee.json` : 39 ± 3,5 ; les mesures 2020–2024 se groupent à 33–36 et 40–41.
19. `conditions.json` et `groupe_local.h` : ancien calcul (distances et axes périmés, ligne droite entre images) ; à retirer dès que le film v2/v3 les remplace.
20. Noyau de Plummer, forces en simple précision, θ = 0,7 : standards, effet sous le pour-cent.
21. Marée des masses extérieures au Groupe local et feuille locale (Wempe 2026) non modélisées : touche les naines isolées à 1–3 Mpc, pas le cœur du film.
22. Bras spiraux absents du potentiel des orbites : choix honnête (vitesse du motif non établie), à garder signalé.

## 5. Ce qui est déjà juste et à garder

- Énergie noire dans les deux calculs, forme et constante correctes ; plus complet que Sawala 2025.
- Frottement dynamique porté par les particules et non par une formule.
- Distance d'Andromède (761 kpc, Li 2021), distance et mouvement propre du Grand Nuage, masse du Grand Nuage (conforme à Erkal 2019, Vasiliev 2021 et Koposov 2023).
- Disques mince et épais, agitation au Soleil, masse stellaire et masse de gaz de la Voie lactée.
- R0 = 8,2 kpc et mouvement propre du Soleil de Schönrich 2010.
- La table unique `univers.json` et le grand livre : la bonne structure pour appliquer les changements ci-dessus en un seul endroit.

## 6. Limites de ce rapport

- Non relus aujourd'hui dans le texte : GRAVITY 2021 (chiffre 8 275 pc), Wu et al. 2025 (mouvement propre), Sanders 2019, Reid & Brunthaler 2020, Karachentsev 2009, Peñarrubia 2016, les articles sur la relation âge-agitation, le gauchissement hors Poggio 2020, Gaia-Encelade et le Sagittaire. Ils sont marqués [Probable] ou [À vérifier].
- La revue Hunt & Vasiliev 2025 n'a pu être lue que jusqu'à sa section 4.3 ; ses sections sur le halo, le gauchissement et la masse restent à lire.
- Les masses enfermées du modèle N-corps sont calculées ici à partir de la formule NFW et d'une masse de baryons de 6,6 × 10¹⁰ M☉, sans la coupure à 250 kpc (négligeable sous 100 kpc) ; à confirmer sur les particules.
- Aucune mesure n'a été faite sur le film avec gaz (film-3) : la vitesse de sa barre n'est pas connue de moi.
