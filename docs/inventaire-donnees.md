# Inventaire : ce que l'appli PC montre, contre ce qui est sur le disque (12/11/2026, 17 h 45 Québec)

Demande de Marc (12/11, 17 h 34) : « littéralement toutes les données que tu as récupérées dans l'application, pas
une version allégée ». Tailles mesurées sur le PC ce jour ; durées = estimations tirées de mesures semblables.

## 1. Déjà complet (rien d'allégé)

| Données | Dans l'appli | Note |
|---|---|---|
| Planètes, Lune, Soleil | DE440 entier (NASA) | contrôlé au mètre contre Horizons |
| Lunes | 437 lunes, 17 fichiers NASA | sat480 (2026) n'ajoute qu'une lune, S/2009 S 2, dans un format (type 17) que l'appli ne lit pas encore |
| Astéroïdes et comètes | 1 580 289 + 1 778, tous ceux du JPL | |
| Sondes | toutes celles de Horizons retenues | |
| Étoiles Gaia à distance sûre | 98 346 986, une à une, orbites exactes | tout ce qui a été téléchargé une à une |
| Cartes du ciel (25 lumières) | à la finesse téléchargée (HEALPix 1024 ou 2048) | lot A (8 Go) en cours, lot B (250 Go) attend Marc |
| Bras (masers, amas) | 190 + 7 167, tous | |
| Groupe local | 113/113 galaxies, clones | |

## 2. Allégé aujourd'hui, données déjà sur le disque (aucune place en plus)

| Données | Montré | Sur le disque | Action |
|---|---|---|---|
| Fusion Voie lactée-Andromède | 1 M d'étoiles tirées | calcul complet relancé avec toutes les particules (fil physique) | installer à la fin du calcul (~24 Go avec la matière noire) |
| Voie lactée seule | 2 M tirées sur 5,5 M | idem, relancé complet | idem |
| Rayons Gaia, poussière | sans poussière (choix mesuré : la retirer ajoute des grains et n'enlève pas les rayons) | conv2 (avec poussière) | rien : décision mesurée du fil rayons |

## 3. Récupéré pour la page web, absent de l'appli PC (sur le disque, demande du code)

| Données | Taille | Où |
|---|---|---|
| Fond diffus Planck SMICA (HEALPix 2048) | 1,9 Go | FAIT 12/11 : carte « Fond diffus cosmologique » dans Lumière (ciel_cmb.bin, 201 Mo) |
| Cosmicflows-4 (distances et vitesses propres, ~56 000 galaxies) | 14 Mo | univers-raw/cf4_table2.tsv |
| Courants de Laniakea (grilles CF4) | 134 Mo | univers-raw/cf4grid |
| Ondes gravitationnelles GWOSC (391 événements) | 1 Mo | univers-raw/gwosc_allevents.json |
| OpenNGC (nébuleuses, amas, galaxies nommées) | 4 Mo | univers-raw/openngc |
| Petites échelles (proton, molécule d'eau, orbitales) | < 1 Mo | app/gen |

## 4. Allégé à la source : il faut retélécharger

| Données | Montré | Complet | Coût estimé |
|---|---|---|---|
| Galaxies (tous relevés) | FAIT 13/11 : 18 343 142 galaxies et quasars, position exacte (DESI DR1 complet 15,75 M, SDSS DR17, DR16Q, 2dF, 6dF, 2MRS ; doublons à 1,5″ retirés) | — | galaxies.bin 367 Mo ; bruts sur le Drive (archives) |
| Positions des galaxies | arrondies (16 bits, ~20″) comme la page | coordonnées exactes | compris dans la ligne du dessus |
| Gaia, les 1,71 milliard d'autres sources | additionnées par case de ciel (HEALPix 7) | une à une | ~100 Go à télécharger (estimation : ~9 h au rythme mesuré de 98 M en 30 min), ~45 Go dans l'appli, et un nouveau moteur qui lit le disque au fil du vol (ne tient pas dans les 16 Go de la carte graphique) : plusieurs jours de travail |
| Poussière 3D Edenhofer 2024 | supprimée du disque | 3,25 Go | seulement utile si on remet une lueur calculée, contraire à « seulement du mesuré » |

## Ordre retenu

1. Tout de suite : fond diffus (fait), puis données du § 3 (fond diffus, ondes gravitationnelles, OpenNGC, Cosmicflows-4).
2. Galaxies DESI complètes (petit téléchargement).
3. Fusion et Voie lactée seule complètes, dès la fin des calculs.
4. Gaia une à une (100 Go + moteur sur disque) : décision de Marc.
