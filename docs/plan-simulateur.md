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
