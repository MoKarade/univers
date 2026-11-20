# Peaufinage, deuxième passe (20 novembre 2026, soir)

Retours de Marc sur la version installée. Ma part : éclairage, sélection, galaxies qui se baladent, espace trop vide.
L'interface, les fiches complètes, la vie des étoiles et les 60 images par seconde sont traités dans d'autres fils.

| Retour | Cause trouvée | Correction | Preuve |
|---|---|---|---|
| « Des astres que je ne peux pas sélectionner » | seules les étoiles nommées (34) et les hôtes de planètes se cliquaient ; les 6,15 millions d'étoiles dessinées, non ; et depuis l'éclat réel des astéroïdes, un clic pouvait choisir un astéroïde invisible | clic sur n'importe quelle étoile dessinée : la plus brillante à moins de 12 px parmi celles qui se voient à la pose du moment (10 ms sur 6,15 millions) ; fiche « Étoile sans nom n° … » avec sa source (catalogue principal ou Gaia DR3), son orbite, son rayon calculé ; astéroïdes cliquables seulement s'ils se voient | `captures-peaufinage2/etoile_cliquee.jpg` ; mesure au clic : étoile 200123 retrouvée |
| « Parfois trop de lumière, parfois pas assez » | la pose ne faisait que baisser contre la saturation, et ne remontait qu'au-delà de 10 Mal | pose qui s'adapte dans les deux sens : baisse si l'éclat moyen dépasse 0,15 (Y/(1+Y)), remonte jusqu'à ×4 (×1 000 aux échelles des galaxies) si rien ne se voit ; zone morte entre les deux (pas de pompage) ; dite à l'écran | `gaz_voie_lactee.jpg` (avant : surexposé) |
| « M77 se balade, pas de physique » | le nom (et la caméra) visait un point à ~20 000 al du centre de la forme ; et la forme à distance mesurée ne suivait pas l'expansion alors que son nom oui | noms posés au centre de leur forme au chargement (4 208 galaxies) ; formes à distance mesurée agrandies par l'expansion au-delà de 10 Mal, comme leur nom ; noms sans le déplacement du Soleil (comme le dessin) | `m77.jpg` |
| « Pas assez de gaz, de nébuleuses » | la grille de la Voie lactée contient le gaz ionisé des régions HII (catalogue WISE, Anderson et al. 2014, avec distances publiées) mais n'était plus dessinée depuis les étoiles du modèle | gaz HII dessiné par-dessus les étoiles, éteint par la poussière de la grille, autour d'aujourd'hui (fondu de 1 à 3 Ma) ; case du menu | `gaz_voie_lactee.jpg` |

Pas vérifié : le balayage complet du zoom avec la nouvelle pose (carte graphique partagée avec le grand calcul) ; à faire
au prochain créneau avec `natif/balayage.py`.
