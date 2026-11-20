# Lumière stable à toutes les échelles (appli PC, 20/11/2026)

Demande de Marc : « parfois trop clair, parfois trop sombre, surtout quand je zoome, dézoome ou fais défiler » ; et la
nébuleuse planétaire du Soleil, en fin de vie, ne se voyait pas.

Labels : [Certain] mesuré ici ; [Probable] publié ; [Supposition] réglage d'affichage.

## Ce qui n'allait pas (mesuré)

Outils ajoutés pour mesurer, dans `fenetre.cpp` (contrôle sans fenêtre) :
- `UNIVERS_BALAYAGE_LACET=<deg début>:<deg fin>:<n>:<dossier>` : n vues en tournant la tête, à distance fixe.
- `UNIVERS_GESTE=<zoom|lacet>:<début>:<fin>:<secondes>:<journal>` : rejoue un geste à 60 images par seconde, avec la pose
  automatique à sa vraie vitesse, et écrit une ligne par image (distance, lacet, pose photo, pose automatique, éclat
  moyen, part saturée).

Constats [Certain] :
1. **Bascule de la pose « photo »** : dès qu'une galaxie de plus de 40 pixels existait (même hors de l'image), la pose
   sautait vers sa valeur « photo » et la courbe de l'écran passait d'un coup de Reinhard à asinh. Défilement à
   30 millions d'al : ×3 d'éclat d'un degré au suivant.
2. **Pose qui garde la mémoire du chemin** : des règles par paliers (zone morte entre « trop clair » et « trop sombre »)
   laissaient la pose là où elle s'était arrêtée. Au-dessus de la Voie lactée (30 000 al), elle restait à ×0,26 alors
   que rien ne l'y obligeait ; le même endroit sortait plus clair ou plus sombre selon le geste.
3. **Mesure sur 9 216 points fixes** alors qu'une étoile fait un pixel : la mesure dépendait des étoiles tombées sur ces
   points.
4. **Nébuleuse du Soleil** : sa brillance de surface est celle de la nébuleuse de l'Hélice (vers 23 mag par seconde d'arc
   carrée, calcul ci-dessous) : invisible à la pose normale. Le premier essai de pose « photo » sur elle (fil du cycle de
   vie) blanchissait tout, parce que la mesure jugeait la saturation en Reinhard alors que l'écran montrait de l'asinh.

## Ce qui change

- **Mesure** (`shaders/pose.comp`) : histogramme de la luminance de **tous** les pixels (128 cases de 0,375 IL), sans
  la pose. Méthode des posemètres et des moteurs de jeu (histogramme en logarithme, Unreal Engine « Auto Exposure
  Histogram ») [Probable].
- **Pose visée sans mémoire** (`pose_auto.h`, `cible`) : calculée sur l'histogramme ; la même vue donne la même pose.
  Règles gardées : au plus 0,5 % de l'image blanche ; éclat moyen entre 0,003 et 0,05 (0,010 aux échelles des galaxies) ;
  relevée au plus ×4 aux échelles des étoiles, jusqu'à ×1 000 aux échelles des galaxies. Les seuils glissent avec la
  distance au lieu de basculer. La mesure suit la courbe réellement montrée (Reinhard fondue avec asinh).
- **Adaptation dans le temps** (`suivante`) : en logarithme, demi-temps 0,1 s vers le sombre (au plus 16 IL/s) et
  0,4 s vers le clair (au plus 4 IL/s) : l'œil s'adapte plus vite à la lumière qu'à l'obscurité (Pattanaik et al. 2000,
  « Time-dependent visual adaptation for fast realistic image display », SIGGRAPH) [Probable].
- **Pose « photo » progressive** (`galaxies_formes.h`, `cycle_appli.h`, `fenetre.cpp`, `ecran.frag`) : chaque galaxie
  résolue (40 à 160 pixels) et chaque nébuleuse (3 à 30 pixels de rayon) pèse de 0 à 1 selon sa taille et sa part dans
  l'image ; la pose photo et la courbe asinh (Lupton et al. 2004) se fondent avec ce poids.
- **Nébuleuses** : seules celles qui brillent (nuage de naissance, nébuleuse planétaire et ce qui en reste, reste de
  supernova, au moins 0,01 L☉) règlent la pose ; plafond ×10⁴ ; 2 % d'étoiles du fond saturées tolérées, comme sur les
  photos de nébuleuses [Supposition : réglages d'affichage].

## Pourquoi la nébuleuse du Soleil est si faible (calcul)

Modèle de l'appli (`essai_cycle`) : 4 000 ans après son début, 0,82 L☉ de lumière visible, coquille de 0,37 al. Une
sphère qui émet L sur un rayon R a une brillance moyenne L / (4π² R²) ; pour 1 L☉ et R = 0,25 pc, cela fait environ
24,6 mag par seconde d'arc carrée [Certain : calcul]. La nébuleuse de l'Hélice (magnitude 7,6 sur 25′) fait environ
23,2 [Probable : valeurs de catalogue]. Le fond du ciel nocturne le plus noir est vers 21 à 22. La nébuleuse du Soleil
ne se voit donc qu'en longue pose, comme sur les photos de l'Hélice : c'est ce que fait maintenant la pose « photo ».

## Mesures avant / après

Rejeu des gestes (carte graphique partagée, occupée à 99 % par le grand calcul et d'autres essais pendant les mesures) :

| Geste | Avant | Après |
|---|---|---|
| Zoom 0,01 al -> 10 Gal en 40 s : pire pas de la pose d'une image à l'autre | ×1,25 | ×1,08 |
| Tour complet autour d'Andromède (200 000 al) : écart d'éclat max / min | ×10,6 | ×3,7 |
| Tour complet à 30 millions d'al : écart d'éclat max / min | ×3,1 | ×2,6 |
| Tour complet à 30 millions d'al : pire saut d'une image à l'autre | ×1,33 | ×1,53 (une galaxie qui entre : contenu, pose à ×1,08 au plus) |

Les rejeux « après » ont été faits avec le premier réglage (éclat moyen visé 0,15) ; le réglage final (0,05) ne change
que les vues trop claires, vérifiées sur les captures ci-dessous. Le dernier rejeu complet a été arrêté pour rendre la
carte graphique au grand calcul.

Restent des sauts d'éclat au zoom vers 3, 13 et 80 millions d'al, présents avant comme après, avec une pose qui ne bouge
pas : ce sont des couches de l'image qui changent (à suivre par le fil des corrections de la vue), pas la pose.

Captures (`docs/captures-exposition/`, avant à gauche, après à droite) :

| Vue | Éclat moyen avant | Après |
|---|---|---|
| Nébuleuse du Soleil, +4 000 ans, à 1,2 al | 26 / 255, anneau invisible | 118 / 255, anneau visible |
| Nébuleuse du Soleil, +12 000 ans, à 3 al | 19 / 255 | 86 / 255, coquille verte ([O III]) visible |
| Soleil à 10 al | 12,0 | 12,0 |
| Voie lactée vue à 30 000 al | 68,5 | 67,6 |
| Andromède à 200 000 al | 14,4 (1,8 % blanc) | 9,2 (0,25 % blanc) |
| Andromède à 60 000 al | 75,4 (4,5 % blanc) | 46,8 (0 % blanc) |
| Soleil à 300 millions d'al | 37,4 | 37,4 |
| Terre de près | 8,6 | 7,7 |

Contrôle sans carte graphique : `essai_pose` (dans `controle.sh`), 19 vérifications.

## Limites

- Autour de la nébuleuse, le fond d'étoiles est relevé avec elle (pose longue) : il est plus chargé qu'à l'œil nu.
- La nébuleuse du modèle reste environ 10 fois plus faible que l'Hélice à taille égale (voir `cycle-vie-etoiles.md`).
- Les seuils d'éclat (0,003, 0,05, 0,010) sont des réglages d'affichage, choisis sur les balayages du 20/11.
