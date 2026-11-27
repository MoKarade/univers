# Film du Groupe local, format 3 (proposition du 18 novembre 2026)

> **État au 22 novembre 2026 : codé et testé.** La disposition exacte, octet par octet, est en tête de
> `pipeline/fusion/film_v3.py` (écrivain et lecteur Python) ; le lecteur de l'appli est `natif/physique/film_v3.h`.
> Ce qui a changé depuis la proposition ci-dessous, d'après les mesures du 22/11 :
> - une image tous les 20 Ma ne suffit pas près des centres (erreur d'interpolation mesurée : 0,7 à 1,2 kpc sous 1 kpc,
>   0,5 kpc entre 1 et 2 kpc, 90 à 330 pc entre 2 et 3,5 kpc). La famille C seule (2 Ma) ne couvrait que le premier kpc.
>   Il y a donc trois classes de cadence entre deux images P, choisies par fréquence de tour : **C** tous les 2 Ma
>   (740 000 traceurs, jusqu'à 1 kpc), **M** tous les 4 Ma (870 000, jusqu'à 2 kpc), **L** tous les 10 Ma (2,1 M,
>   jusqu'à 4,5 kpc) ; erreur typique restante : moins de 50 pc ;
> - taille : P 101 + C 56 + M 31 + L 19 + G 12,5 = **environ 219 Go** ;
> - 40 naines (et non 38), sans masse ; Sagittaire n'attire donc pas le disque (écart écrit dans `ecarts.txt`) ;
> - l'en-tête de l'index fait 80 octets (il compte aussi M et L) ; bits des familles : 0 P, 1 C, 2 G, 3 M, 4 L ;
> - le centre de chaque galaxie s'interpole comme les traceurs (Hermite, vitesse de centre de l'index).

Écrit par `pipeline/fusion/rencontre.py` (mode `futur`), lu par l'appli (`natif/physique/film_v3.h`, fil « Analyser le
code »). Remplace le format 2 (`film_v2.py`, `film_v2.h`), que le lecteur garde pour les anciens films.

Taille visée : **environ 175 Go** (choix de Marc le 18/11 : option B, 174 Go, cadence de 2 Ma près des centres).
Labels : [Décidé] par Marc ou par les deux fils ; [Proposé] à confirmer par le fil de l'appli avant que je code.

## 1. Ce que le film contient

Trois familles de traceurs, chacune dans un ordre FIXE du début à la fin du film (l'identifiant d'un traceur est son rang).

| Famille | Qui | Nombre | Cadence | Taille |
|---|---|---|---|---|
| **P** principaux | étoiles visibles des cinq galaxies (8,5 M) ; toutes les particules de matière ordinaire du calcul, étoiles et gaz (~2,9 M : c'est parmi elles que naissent les étoiles pendant le film) ; le Soleil ; les 38 galaxies naines (un point chacune) | ~11,4 M | une image tous les **20 Ma**, de 0 à +10 Ga (501 images) | 205 Mo par image, **103 Go** |
| **C** centraux | les 750 000 traceurs P les plus proches du centre de leur galaxie à t = 0 (Voie lactée et Andromède, au prorata) : orbites de moins de ~50 Ma | 0,75 M | aux dates intermédiaires, tous les **2 Ma** (9 images entre deux images P) | 13,5 Mo par image, 4 500 images, **61 Go** |
| **G** Gaia | les 6,89 M d'étoiles Gaia à vitesse complète à moins de 2 kpc qui portent 90 % de leur lumière | 6,89 M | tous les **10 Ma**, de 0 à **+1 Ga** (101 images) | 124 Mo par image, **12,5 Go** |

Total : environ 176 Go. [Proposé : la répartition P / C ; Décidé : le total et la présence de Gaia]

Pourquoi toutes les particules de matière ordinaire et pas seulement le gaz de départ : les étoiles qui vieillissent
rendent du gaz (retour de masse), et ce gaz forme à son tour des étoiles ; on ne sait pas d'avance lesquelles.

Limite connue, à écrire dans l'appli : hors des 750 000 traceurs centraux, une étoile à moins de ~1 kpc d'un centre est
mal interpolée entre deux images (sa période est plus courte que 2 pas d'image).

## 2. Un enregistrement (18 octets, petit-boutiste)

| Champ | Type | Unité | Portée |
|---|---|---|---|
| position x, y, z | 3 × entier 32 bits signé | 0,01 pc | ± 21 Mpc |
| vitesse x, y, z | 3 × entier 16 bits signé | 0,05 km/s | ± 1 638 km/s (saturée au-delà) |

Position et vitesse sont **relatives au centre et à la vitesse d'ensemble de la galaxie d'origine** du traceur, à la date
de l'image (centres dans l'index). Repère : `phys::galaxie` (le même que le format 2). Entre deux images : interpolation
d'Hermite (positions et vitesses aux deux bouts).

## 3. Fichiers

- `film.json` : lisible par un humain ; version 3, unités, repère, paramètres du calcul, bulletin, écarts connus.
- `film_index.bin` : en-tête `UNIVFLM3`, version, nombre de galaxies, nombres de traceurs par famille et par bloc, puis
  - table des **blocs** : pour chaque bloc, famille, galaxie d'origine, type (1 étoiles visibles, 2 matière du calcul,
    3 Soleil, 4 naine, 5 Gaia), premier rang, nombre ;
  - `decalage_a_t0` par galaxie (place et vitesse calculées moins place et vitesse mesurées), écart entre le Soleil du film
    et le Soleil mesuré à t = 0 ;
  - pour chaque date du film (5 001 dates, tous les 2 Ma) : date exacte (Ga, double), familles présentes, centre (kpc,
    double) et vitesse (km/s, double) de chaque galaxie par rapport à la Voie lactée, écart d'énergie.
- `p_NNNNN.bin` (501), `c_NNNNN.bin` (4 500), `g_NNNNN.bin` (101) : les enregistrements, sans en-tête, dans l'ordre fixe ;
  NNNNN = numéro de la date dans l'index.
- `centraux.bin` : rang dans P de chacun des 750 000 traceurs C (entiers 32 bits).
- `matiere.bin` : pour chaque particule de matière du bloc de type 2, sa nature à t = 0 (étoile ou gaz), sa masse (M☉),
  sa composante.
- `evenements.bin` : liste triée par date de (rang, date en Ga, nouvelle nature) : naissance d'une étoile (gaz → étoile)
  ou retour au gaz (étoile → gaz). L'appli ne dessine une particule de matière que lorsqu'elle est une étoile née pendant
  le film, jeune et bleue, puis vieillie comme les autres.
- `gaia.bin` : pour chaque traceur G, son rang dans `gaia.bin` de l'appli.
- `champ/` : inchangé (coefficients du champ de gravité).

## 4. Coût dans le calcul

Les traceurs coûtent autant que les autres particules dans l'arbre : 6,89 M de plus sur 18,3 M, soit environ + 38 % de
temps de carte ; le gaz ajoute environ 35 % au calme et davantage pendant la rencontre (mesuré sur une galaxie seule).
