# Plan « simulateur scientifique » (11 novembre 2026, décisions prises)

Source : document de Marc « Ingénierie des simulateurs astrophysiques professionnels ». Cadrage complet, comparaison avec l'existant et erreurs relevées : https://claude.ai/artifact/L2AbryMzFnzcRjaiTGxZvk

Décision de Marc (11/11/2026) : toutes les recommandations du cadrage (« oui »).

## Tâches, dans l'ordre

| N° | Tâche | Fini quand | Attend |
|---|---|---|---|
| S1 | Couleur vraie des étoiles : température (Ballesteros 2012), puis corps noir de Planck intégré sur l'observateur CIE 1931 | `app/test/bbcol.test.js` vert (illuminant A, lieu de Planck de Kim et al. 2002, Soleil, Bételgeuse, Rigel) ; quatre critiques PASSE | Rien |
| S2 | Vraies orbites des étoiles dans un modèle publié de la Galaxie, calculées à l'avance | Le Soleil fait un tour en 220 à 240 millions d'années ; énergie conservée à 1 % ; les 42 passages d'étoiles gardent leurs dates publiées | Rien |
| S3 | Galaxies lointaines : assombrissement de Tolman et K-correction | À z = 1, éclat de surface bolométrique divisé par 16 ; fiche « calculé » | Lot C (zoom) fini |
| S4 | Fond du ciel en tuiles HiPS | Laissé au fil des sources astro (ajout A4) ; repris ici seulement s'il est abandonné | Stockage en ligne |
| S5 | Poussière mesurée en 3D (Edenhofer et al. 2024, jusqu'à 1,25 kpc) | Nuages du Taureau et d'Orion au bon endroit ; fluidité mesurée sur le téléphone de Marc | Stockage en ligne ; R12 |
| S6 | Lumière déviée par les trous noirs (Sagittarius A*, M87*) | Ombre de M87* au diamètre mesuré par l'EHT [à vérifier] | S1 à S5 |

Écartés : relativité restreinte (la caméra n'a pas de vitesse physique), extension Gaia Sky ou OpenSpace, passage à WebGPU, filtres et aigrettes d'instruments. La mesure du tremblement et de la profondeur s'ajoute aux tests du zoom (R1 à R3) ; une correction n'est faite que si un défaut se voit.

## S1 — état
- `pipeline/build_bbcol.py` écrit `app/gen/data15.js` (`DATA.BBCOL`, 256 températures de 1000 à 40 000 K) à partir de `pipeline/ref/ciexyz31_1.csv` (CIE 1931 2°, copie CVRL).
- `30_gen.js` : `bvToTeff` (Ballesteros 2012), `bbRgb` (table), `bvToRgb` les enchaîne. Tous les appels existants passent par `bvToRgb`.
- Retiré : l'ancien ajustement empirique RVB et l'éclaircissement vers le blanc (`× 0,72 + 0,28`), qui n'étaient pas de la physique.
- Limites connues : pour les étoiles Gaia, B−V vient de `0,78 × (BP−RP)` (approximation des scripts d'origine, `pipeline/get_stars.py`), pas d'une relation publiée. La composante la plus forte vaut 1 : à magnitude égale, une étoile rouge paraît un peu moins lumineuse qu'une blanche ; c'était déjà le cas avant.
- Retiré aussi : le gonflement de saturation du shader des étoiles (`mix(lum, col, 1.55)`, `40_render.js`), qui compensait l'éclaircissement. La couleur affichée est celle du corps noir, encodée en sRGB par la passe finale (`pow(1/2,2)` après ACES).
- Preuves : `bbcol.test.js` compare la chaîne entière à des références indépendantes du code (illuminant A de la CIE ; lieu de Planck de Kim et al. 2002 converti par la définition de sRGB, primaires et blanc D65, matrice recalculée dans le test). La table de Mitchell Charity (vendian.org) n'est pas utilisée : elle emploie les corrections de Judd-Vos, écarts de 1 à 3 %.
- Critiques (11/11) : réel, rendu, usage PASSE ; preuves BLOQUE puis corrigé (référence sRGB indépendante, contrôle des bornes de la table, captures au même instant, PC et téléphone).

## S2 — mesure de départ (11/11)
`app/test/orbits_measure.js` compare l'approximation des épicycles (`25_future.js`) à une intégration exacte (saut de grenouille, pas de 0,5 Ma) dans le même potentiel, pour les 58 967 étoiles HYG : écart médian 148 pc à 50 Ma, 403 pc à 200 Ma, 2,3 kpc à 1 Ga ; 63 % des étoiles à plus de 100 pc dès 50 Ma. Le Soleil lui-même dérive de 108 pc en 50 Ma. L'intégration exacte des 58 967 étoiles sur 1 Ga prend 2 s sous Node sur le PC : faisable dans la page pour ce catalogue, pas pour les millions d'étoiles Gaia.

## S2 — conception retenue (à construire sur sa propre branche)
- Portée : orbite exacte pour le catalogue principal (`K`, 58 967 étoiles HYG, `initStarKin` dans `40_render.js`). Les étoiles Gaia en flux (`K2`, millions) gardent les épicycles, et leur fiche le dit (« orbite approchée »).
- Où : nouveau fichier `app/src/26_orbits.js` (ajouté à la liste de `app/build.py`), pour ne pas croiser le lot A de la mission 2 qui modifie `25_future.js`.
- Calcul : saut de grenouille, pas de 0,5 Ma, dans le potentiel `GAL` existant (Hernquist + Miyamoto-Nagai + NFW), dans un Web Worker (créé depuis un Blob) pour ne pas bloquer l'image. État courant gardé ; on avance ou recule depuis le point de contrôle le plus proche (un point tous les 100 Ma, Float32, au plus 20 gardés : 28 Mo).
- Branchement : `starPositions` prend la position exacte quand elle existe pour `tEff` (à 1 Ma près), sinon l'épicycle, sans saut visible (fondu interdit : on attend la fin du calcul et on le dit, « calcul des orbites »). Le Soleil (`sunGalAt`) suit la même orbite exacte, pour que tout reste cohérent.
- Piège : `tEff` n'est pas le temps réel quand la matière noire est retirée (`S.dmMix`, `oSunNo / oSunDM`) ; dans ce mode, le potentiel sans halo doit être utilisé, ou l'orbite exacte coupée et le dire.
- Fini quand : énergie de chaque orbite conservée à 0,1 % sur 1 Ga ; période du Soleil 220 à 240 Ma ; les 42 passages d'étoiles gardent leurs dates publiées (pris en ligne droite sous 3 Ma, inchangé) ; temps par image sous deux fois la référence pendant la lecture à vitesse maximale ; quatre critiques PASSE.
