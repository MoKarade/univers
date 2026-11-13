# Paramètres publiés des galaxies du Groupe local, relus le 13 novembre 2026

But : remplacer les modèles de départ du calcul de la rencontre (`pipeline/fusion/modeles.py`), qui sont instables et
faux (`docs/revue-detaillee.md`, G1 à G5 et G10), par des valeurs relues dans les articles.

Statut de chaque valeur : **[lu]** texte de l'article lu tel quel ce jour (version arXiv) ; **[résumé]** tiré d'un résumé
automatique de la partie non lue, à relire avant d'entrer dans le code ; **[calculé]** calculé ici.

## 1. Ce que mesurent les modèles actuels (`pipeline/fusion/stabilite.py`) [calculé]

| Galaxie | Stabilité du disque Q (minimum) | Il faut | Remarque |
|---|---|---|---|
| Voie lactée | 0,74 | plus de 1,5 | 252 km/s au Soleil au lieu de 230 ; disque de 68 M☉/pc² |
| Andromède | 0,74 | plus de 1,5 | même forme que la Voie lactée, agrandie |
| Triangle | 0,61 | plus de 1,5 | 81 km/s de rotation au lieu de 100 à 125 |
| Grand Nuage | 2,37 | plus de 1,5 | stable, mais halo non coupé |

Chauffer le disque ne suffit pas (il faudrait doubler l'agitation, bien au-delà des mesures) : **le disque est trop
lourd**. Avec le modèle publié de la Voie lactée et l'agitation mesurée au Soleil (30 à 40 km/s), on obtient Q = 1,7 à
2,3 : stable, sans rien forcer.

## 2. Voie lactée : McMillan 2017 (MNRAS 465, 76 ; arXiv:1608.00971), meilleur modèle, table 3 [lu]

| Composante | Forme | Valeurs |
|---|---|---|
| Disque mince | exponentiel, hauteur 300 pc | 896 M☉/pc², longueur 2,50 kpc, soit 3,52 × 10¹⁰ M☉ [calculé] |
| Disque épais | exponentiel, hauteur 900 pc | 183 M☉/pc², longueur 3,02 kpc, soit 1,05 × 10¹⁰ M☉ [calculé] |
| Gaz atomique | disque troué (4 kpc), longueur 7 kpc, hauteur 85 pc | 1,1 × 10¹⁰ M☉ |
| Gaz moléculaire | disque troué (12 kpc), longueur 1,5 kpc, hauteur 45 pc | 1,2 × 10⁹ M☉ |
| Bulbe | loi de puissance 1,8, coupure 2,1 kpc, aplati 0,5 | 9,23 × 10⁹ M☉ |
| Halo | NFW | 0,00854 M☉/pc³, rayon 19,6 kpc ; masse 1,37 × 10¹² M☉, concentration 15,4 |
| Soleil | | R0 = 8,21 kpc ; vitesse circulaire 233,1 km/s ; matière noire locale 0,0101 M☉/pc³ |
| Total des étoiles | | 5,43 × 10¹⁰ M☉ |

À ajouter (hors de cet article, à relire) : barre de 5,0 kpc, 28°, 39 km/s/kpc, masse du bulbe et de la barre
1,9 × 10¹⁰ M☉ (Wegg et al. 2015 ; Portail et al. 2017) [non relu ce jour]. Le bulbe de McMillan (0,9 × 10¹⁰) est
axisymétrique et ne compte pas la barre longue.

## 3. Andromède

| Grandeur | Valeur | Source |
|---|---|---|
| Distance | 785 ± 25 kpc adoptée par les trois articles ci-dessous [lu] ; 761 ± 11 kpc (Li et al. 2021, Céphéides) [non relu] | à trancher : une seule valeur partout |
| Inclinaison, angle de position | 77° ; 38° (ou 74° et 37,7° en cinématique) | Blaña Díaz 2018 § 2.2 [lu] ; Chemin 2009 [lu / résumé] |
| Longueur du disque | 5,3 ± 0,5 kpc (3,6 µm, sans poussière) | Courteau et al. 2011, résumé de l'article [lu] |
| Bulbe classique | 1,18 (+0,06 −0,07) × 10¹⁰ M☉ | Blaña Díaz et al. 2018 [lu] |
| Bulbe en boîte (barre) | 1,91 ± 0,06 × 10¹⁰ M☉ | idem [lu] |
| Bulbe total | 3,09 × 10¹⁰ M☉ | idem [lu] |
| Barre | 40 ± 5 km/s/kpc ; angle 54,7 ± 3,8° ; demi-longueur 4,0 kpc | idem [lu] |
| Masse sur lumière à 3,6 µm | 0,72 ± 0,02 | idem [lu] |
| Matière noire dans 3,2 kpc | 1,2 × 10¹⁰ M☉ ; halo d'Einasto 1,29 × 10⁷ M☉/kpc³, 7,8 kpc, α = 0,51 | idem [lu] ; paramètres [résumé] |
| Rotation | 340 km/s au centre, creux à 202 km/s vers 4 kpc, 275 km/s au bord | Chemin, Carignan et Foster 2009 [lu] |
| Gaz atomique | 4,23 × 10⁹ M☉ | idem [lu] |
| Bulbe de Sersic | indice 2,2 ± 0,3 ; rayon 1,0 ± 0,2 kpc ; lumière : 23 % bulbe, 73 % disque, 4 % halo | Courteau et al. 2011 [lu] |
| Masse du disque d'étoiles, masse totale du halo | **non trouvées** dans ces lectures | à chercher (Tamm et al. 2012 ; Kafle et al. 2018) |

Dans `modeles.py` aujourd'hui : disque de 3,0 kpc, bulbe de 0,75 × 10¹⁰ M☉, pas de barre.

## 4. Triangle (M33)

| Grandeur | Valeur | Source |
|---|---|---|
| Distance | 840 kpc | Corbelli et al. 2014 ; Kam et al. 2017 [lu] |
| Inclinaison | 52 ± 3° (optique) ; 53 à 58° selon le rayon | Kam et al. 2017, table 1 [lu] ; table 4 [résumé] |
| Angle de position | 22,5 ± 1° ; cinématique 202° au centre, 165° au bord (disque tordu) | Kam et al. 2017 [lu] |
| Étoiles | 4,8 ± 0,6 × 10⁹ M☉ [résumé] ; 5,5 × 10⁹ M☉ [lu] | Corbelli 2014 ; Kam 2017 |
| Longueur du disque | 1,8 ± 0,1 kpc ; 1,6 kpc | Corbelli 2014 [lu] ; Kam 2017 [lu] |
| Gaz atomique | 1,53 × 10⁹ [résumé] ; 1,95 ± 0,36 × 10⁹ M☉ [lu] ; × 1,33 pour l'hélium | Corbelli ; Kam |
| Gaz moléculaire | 3,0 × 10⁸ M☉ | Corbelli 2014 [lu] |
| Rotation | 100 km/s à 4 kpc, 120 à 130 km/s au-delà ; maximum 125 km/s | Corbelli 2014 [lu] ; Kam 2017 [lu] |
| Halo | NFW 4,3 ± 1,0 × 10¹¹ M☉, concentration ≈ 10 | Corbelli 2014 [lu] |
| Masse dans 23 kpc | 8 × 10¹⁰ M☉ ; 5 × 10¹¹ au rayon du viriel | Kam 2017 [lu] |

Dans `modeles.py` aujourd'hui : halo de Plummer de 2,5 × 10¹¹ à cœur de 21 kpc (81 km/s seulement), disque de 1,4 kpc,
pas de gaz, 809 kpc, 49°.

## 5. Grand Nuage de Magellan

| Grandeur | Valeur | Source |
|---|---|---|
| Distance | 50,1 ± 2,5 kpc | van der Marel et Kallivayalil 2014, table 1 [lu] |
| Inclinaison | 39,6 ± 4,5° (mouvements propres), 34,0 ± 7,0° (avec vieilles étoiles), 26,2 ± 5,9° (avec jeunes) | idem [lu] |
| Ligne des nœuds | 147,4 ± 10,0° ; 139,1 ± 4,1° ; 154,5 ± 2,1° | idem [lu] |
| Rotation | 91,7 ± 18,8 km/s ; masse dans 8,7 kpc : 1,7 ± 0,7 × 10¹⁰ M☉ | idem [lu] |
| Centre | 78,76 ± 0,52°, −69,19 ± 0,25° | idem [lu] |
| Mouvement propre | −1,910 ± 0,020 ; 0,229 ± 0,047 mas/an | idem [lu] |
| Masse totale | 1,38 (+0,27 −0,24) × 10¹¹ M☉ | Erkal et al. 2019 [lu] |
| Étoiles | 2,7 × 10⁹ M☉ | van der Marel 2006, cité par Erkal 2019 [lu] |

## 6. Petit Nuage de Magellan (absent du calcul aujourd'hui)

| Grandeur | Valeur | Source |
|---|---|---|
| Mouvement propre | −0,82 ± 0,02 (± 0,10) ; −1,21 ± 0,01 (± 0,03) mas/an | Zivick et al. 2018 [lu] |
| Vitesse radiale | 145,6 ± 0,6 km/s | Harris et Zaritsky 2006, cité [lu] |
| Distance | module 18,99 ± 0,1, soit environ 63 kpc [calculé] | Cioni et al. 2000, cité [lu] |
| Centre | 16,25°, −72,42° (gaz) | Stanimirović et al. 2004, cité [lu] |
| Masse | 3 × 10⁹ M☉ : valeur adoptée, pas mesurée [résumé] | à chercher |

## 7. Ce qui reste à relire avant d'écrire le nouveau `modeles.py`

- Andromède : masse du disque d'étoiles et masse totale du halo.
- Voie lactée : barre et bulbe (Portail et al. 2017).
- Petit Nuage : masse totale.
- Trancher la distance d'Andromède (761 ou 785 kpc) et l'utiliser partout, scénarios compris.
- Toutes les valeurs [résumé].
