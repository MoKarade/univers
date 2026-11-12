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
| Astéroïdes | 1 580 289 | JPL SBDB, requête `sb-kind=a` du 12/11/2026 |
| Comètes | 4 088 | JPL SBDB, requête `sb-kind=c` du 12/11/2026 |
| Sondes qui quittent le système solaire | 5 (Pioneer 10 et 11, Voyager 1 et 2, New Horizons) | NASA |
| Objets à moins de 10 pc | 540 (étoiles, naines brunes, exoplanètes) | Reylé et al. 2021, [A&A 650, A201](https://arxiv.org/abs/2104.14972) |
| Sources Gaia DR3 | 1 811 709 771 | [ESA, Gaia DR3](https://www.cosmos.esa.int/web/gaia/dr3) |
| Étoiles de la Voie lactée | 100 à 400 milliards (estimation) | NASA Goddard, Blueshift |
| Galaxies à moins de 1 Mpc | 113 confirmées | [Local Volume Database](https://github.com/apace7/local_volume_database) v1.1.2 (Pace, 04/11/2026), module de distance |
| Galaxies de l'univers observable | 200 milliards à 2 000 milliards (estimation) | Lauer et al. 2021 ; Conselice et al. 2016 |

## Résultat sur l'appli installée (12/11/2026)

| Échelle | Présent | Précision | Mesuré ou calculé |
|---|---|---|---|
| Système solaire | 7,8 % (9 planètes et Pluton, 16 lunes sur 461, 123 530 astéroïdes sur 1 580 289, 0 comète, 5 sondes sur 5) | planètes < 1 mm, Lune 282 m, Triton 255 km, sondes 0,7 km au plus, astéroïdes 25 000 à 93 000 km après 154 jours | éphémérides de la NASA ; astéroïdes calculés ici |
| Étoiles voisines | 87 % (470 sur 540) | arrondi du fichier : pas de 198 UA à 10 pc | positions mesurées ; 41 149 étoiles sans vitesse radiale |
| Voie lactée | 0,34 % de Gaia DR3 ; 0,0015 à 0,0062 % de l'estimation | distance à mieux que 20 % (Gaia) | positions mesurées ; galaxie elle-même non dessinée |
| Groupe local | 62 % (70 sur 113) | erreur par galaxie non gardée | mesuré aujourd'hui ; calculé dans le temps profond |
| Univers lointain | 5 566 702 objets ; 0,00028 à 0,0028 % de l'estimation | décalage arrondi à 9,5 km/s × (1 + z) | distance 100 % calculée |

## Ce qui manque, pour monter ces chiffres

Système solaire
- 445 lunes : absentes des fichiers légers du NAIF ; les 5 grandes lunes d'Uranus sont dans un fichier de 5,6 Go.
- 1 456 759 astéroïdes et les 4 088 comètes du JPL.
- Les autres sondes (en orbite autour des planètes, en route).
- Attraction des planètes sur les astéroïdes (écart actuel jusqu'à 93 000 km en 154 jours).
- Triton : mesurer l'écart avec un fichier plus récent.

Étoiles voisines
- Retirer les doublons entre catalogues (garder la mesure Gaia).
- Naines brunes et exoplanètes du recensement de Reylé et al.
- Garder la direction complète dans le fichier (l'arrondi à 20″ est des milliers de fois plus grossier que Gaia).
- Marquer les étoiles sans vitesse radiale mesurée (aujourd'hui mise à zéro, donc supposée dans le temps).

Voie lactée
- Le reste de Gaia DR3 ; l'erreur de distance de chaque étoile dans le fichier ; le dessin de la galaxie d'après des
  cartes mesurées.

Groupe local
- 43 galaxies naines de la Local Volume Database ; l'erreur de distance de chaque galaxie ; leurs formes.

Univers lointain
- Distances mesurées sans le décalage (Cosmicflows) ; éclat et forme ; relevés plus récents ; chiffrer l'effet du
  mouvement propre des galaxies sur leur distance.

## Mettre à jour

Changer une valeur de référence : la constante dans `completude.h`, avec sa source et sa date, puis ce fichier.
Contrôle : `essai_completude C:\dev\Univers-PC` (les valeurs attendues sont relevées à part, avec numpy et Python).
