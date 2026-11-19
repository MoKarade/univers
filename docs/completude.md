# Complétude de l'appli PC, échelle par échelle

Code : `natif/src/completude.h`. Contrôle : `natif/src/essai_completude.cpp` (sur les vraies données de l'appli).
Relevé le 12 novembre 2026. À chaque échelle, trois chiffres : la part des objets connus présents, la précision des
positions, et ce qui est mesuré ou calculé. Règle de Marc : une estimation publiée n'est jamais présentée comme une
mesure ; elle est écrite « estimation publiée, non mesurée ».

## Méthode

- **Présent** : compté par l'appli au chargement, dans ce qu'elle a vraiment chargé (une lune dont le fichier de la
  NASA manque n'est pas comptée). Les nombres de galaxies et d'astéroïdes viennent de l'en-tête de leurs fichiers.
- **Connu** : un total publié et daté (tableau ci-dessous). Quand seul un ordre de grandeur existe (étoiles de la Voie
  lactée, galaxies de l'univers observable), la part est donnée en fourchette et marquée « estimation ».
- **Précision** : écarts mesurés par nos contrôles contre JPL Horizons (`docs/plan-natif.md`), erreurs de sélection des
  catalogues, et arrondi de nos fichiers (entiers de 16 bits, calculé exactement).
- **Doublons** près du Soleil : deux points de catalogues différents à moins de 0,02 année-lumière sont comptés comme
  une seule étoile probable [Probable : seuil choisi ici, une étoile double serrée peut y tomber].
- **Vitesse radiale absente** : une étoile du catalogue principal dont la vitesse le long de la ligne de visée est
  inférieure à 0,2 km/s est comptée « sans vitesse radiale » (le fichier la met à zéro) [Probable]. Pour Gaia, l'arrondi
  du fichier (pas de 2 km/s) ne permet pas de les distinguer.

## Totaux de référence

| Quoi | Valeur | Source |
|---|---|---|
| Lunes connues | 460 + la Lune (Jupiter 115, Saturne 293, Uranus 29, Neptune 16, Mars 2, Pluton 5) | JPL, [Planetary Satellite Discovery Circumstances](https://ssd.jpl.nasa.gov/sats/discovery.html), lu le 12/11/2026 |
| Astéroïdes | 1 580 368 | JPL SBDB, requête `sb-kind=a` du 12/11/2026, 18 h 25 UTC |
| Comètes | 4 088 | JPL SBDB, requête `sb-kind=c` du 12/11/2026 |
| Sondes qui quittent le système solaire | 5 (Pioneer 10 et 11, Voyager 1 et 2, New Horizons) | NASA |
| Objets à moins de 10 pc | 540 (étoiles, naines brunes, exoplanètes) | Reylé et al. 2021, [A&A 650, A201](https://arxiv.org/abs/2104.14972) |
| Sources Gaia DR3 | 1 811 709 771 | [ESA, Gaia DR3](https://www.cosmos.esa.int/web/gaia/dr3) |
| Sources Gaia additionnées par case | 1 707 918 961 (toutes les autres sources avec magnitude G) | gaia_agreger.py, archive de l'ESA, 12/11/2026 (docs/gaia-voie-lactee.md) |
| Étoiles de la Voie lactée | 100 à 400 milliards (estimation) | NASA Goddard, Blueshift |
| Galaxies à moins de 1 Mpc | 113 confirmées | [Local Volume Database](https://github.com/apace7/local_volume_database) v1.1.2 (Pace, 04/11/2026), module de distance |
| Galaxies de l'univers observable | 200 milliards à 2 000 milliards (estimation) | Lauer et al. 2021 ; Conselice et al. 2016 |

## Résultat sur l'appli installée (12/11/2026)

| Échelle | Présent | Précision | Mesuré ou calculé |
|---|---|---|---|
| Système solaire | 99,7 % (9 planètes et Pluton, 16 lunes sur 461, 1 580 289 astéroïdes sur 1 580 368, 0 comète, 5 sondes sur 5) | planètes < 1 mm, Lune 282 m, Triton 255 km, sondes 0,7 km au plus, astéroïdes < 300 000 km (10 corps dont Cérès et Vesta) | éphémérides de la NASA ; astéroïdes calculés ici |
| Étoiles voisines | avec gaia.bin : 86 % (467 sur 540 : 150 Gaia + 317 du catalogue principal) | Gaia : distance à mieux que 10 % ; catalogue principal : pas de 198 UA | positions mesurées ; vitesse radiale mesurée pour 77 des 150 étoiles Gaia |
| Voie lactée | avec gaia.bin et gaia_agrege.bin : 99,6 % des sources de Gaia DR3 (98 278 356 vues une à une, 1 707 918 961 additionnées par case, non vues une à une ; 920 197 143 de celles-ci placées à leur distance) | une à une : distance à mieux que 10 % ; additionnées : 31 % de leur lumière sans distance mesurée | étoiles et sommes mesurées ; aucun modèle de la galaxie (choix de Marc, 12/11) |
| Groupe local | 61 % (69 sur 113, recoupées une à une par direction ; Canis Major montrée mais absente de la LVDB) | erreur par galaxie non gardée | mesuré aujourd'hui ; calculé dans le temps profond |
| Univers lointain | 5 566 702 objets ; 0,00028 à 0,0028 % de l'estimation | décalage arrondi à 9,5 km/s × (1 + z) | distance 100 % calculée |

## Ce qui manque, pour monter ces chiffres

Système solaire
- 445 lunes : absentes des fichiers légers du NAIF ; les 5 grandes lunes d'Uranus sont dans un fichier de 5,6 Go.
- 2 310 comètes (2 244 sur une orbite ouverte, 39 disparues, 27 sans orbite à jour) ; 79 astéroïdes (8 à orbite non elliptique, les autres découverts depuis le téléchargement).
- Les autres sondes (en orbite autour des planètes, en route).
- Attraction des planètes sur les astéroïdes (écart actuel jusqu'à 300 000 km).
- Triton : mesurer l'écart avec un fichier plus récent.

Étoiles voisines
- Retirer les doublons entre catalogues (garder la mesure Gaia).
- Naines brunes et exoplanètes du recensement de Reylé et al.
- Garder la direction complète dans le fichier (l'arrondi à 20″ est des milliers de fois plus grossier que Gaia).
- Marquer les étoiles sans vitesse radiale mesurée (aujourd'hui mise à zéro, donc supposée dans le temps).

Voie lactée
- Le reste de Gaia DR3 ; l'erreur de distance de chaque étoile dans le fichier ; remplacer les trois hypothèses du modèle
  de la galaxie par des mesures (docs/gaia-voie-lactee.md).

Groupe local
- 44 galaxies naines de la Local Volume Database, nommées dans l'appli (liste : `natif/src/completude_groupe_local.h`, refaite par `pipeline/natif/completude_groupe_local.py <galaxies_noms.tsv>`) ; l'erreur de distance de chaque galaxie ; leurs formes.

Univers lointain
- Distances mesurées sans le décalage (Cosmicflows) ; éclat et forme ; relevés plus récents ; chiffrer l'effet du
  mouvement propre des galaxies sur leur distance.

## Grandes structures et nuage d'Oort (19/11/2026)

- Système solaire : ligne « Nuage d'Oort », nature « supposé » (modèle d'un million de comètes ; 100 à 1 000 milliards
  estimées). Il ne compte pas dans la part des objets connus.
- Univers lointain : Laniakea et ses 5 bassins voisins (6 sur 6, ajusté sur des mesures), flot (calculé), vides du
  voisinage (100 sur 100), SDSS (899 montrés, les 264 plus proches déjà dans le voisinage), BOSS (1 228 sur 1 228).
- Manques dits : vides entre 330 Mpc/h et z = 0,2 et dans le ciel du Sud au-delà de 200 Mpc/h ; superamas au-delà des
  bassins voisins ; forme réelle des vides BOSS.

## Mettre à jour

Changer une valeur de référence : la constante dans `completude.h`, avec sa source et sa date, puis ce fichier.
Contrôle : `essai_completude C:\dev\Univers-PC` (les valeurs attendues sont relevées à part, avec numpy et Python).
