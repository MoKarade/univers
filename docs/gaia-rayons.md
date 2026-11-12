# Appli PC : rayons autour du Soleil et traînée dans le temps (12 novembre 2026)

Demande (coordinateur, d'après les captures de Marc, vue depuis environ 58 000 al) : aujourd'hui, une lueur avec des rayons
autour du Soleil ; à +44,6 Ma, une longue traînée en bande. But : une Voie lactée vue de loin fiable, sans artefact, à toute
date, en restant sur du mesuré. Confiance : [Certain] mesuré ici ; [Probable] ; [Supposition].

## Ce qui a été mesuré

Scripts hors dépôt (dossier de travail `C:\tmp\rayons`), sur les 98,3 M étoiles téléchargées et leurs erreurs publiées :
carte vue de dessus (plan galactique, cases de 20 pc, lumière additionnée), puis « contraste des rayons » : écart type, sur
360 tranches d'un degré autour du Soleil, du logarithme de la lumière entre 2 et 4 kpc, une fois retirées les variations
plus larges que 15°. Référence sans rayons (mêmes étoiles, directions mélangées) : 0,011 dex.

| Sélection | Étoiles | Lumière | Contraste 2-4 kpc | 1-2 kpc |
|---|---|---|---|---|
| Actuelle (parallaxe > 10 erreurs) | 98,3 M | 100 % | 0,046 | 0,025 |
| Parallaxe > 20 erreurs | 48,9 M | 50 % | 0,050 | 0,026 |
| Parallaxe > 50 erreurs | 16,4 M | 12,5 % | (anneau presque vide) | 0,034 |
| Vitesse radiale mesurée | 25,9 M | 80,7 % | 0,038 | 0,024 |

- [Certain] Un seuil plus strict ne réduit pas les rayons et fait perdre la lumière. Dessiner chaque étoile comme une tache de la
  taille de son incertitude de distance ne les efface pas non plus (carte de dessus) : ce n'est pas le flou des distances.
- [Certain] Bailer-Jones et al. 2021 (distances géométriques), sur 21 000 étoiles du serveur de l'ESA : écart médian -0,8 à -2 %
  avec 1/parallaxe, et une incertitude de 0,94 à 0,97 fois celle de 1/parallaxe. Même flou, plus une hypothèse (modèle de la
  Galaxie comme a priori). Écarté.
- [Probable] Les rayons sont des cônes pleins et vides qui partent du Soleil : derrière la poussière proche, les étoiles
  lointaines sont trop faibles pour que Gaia mesure leur distance ; ailleurs Gaia voit plus loin. Le texte à l'écran disait
  « flou des distances » : corrigé.
- Incertitude de distance médiane (pondérée par la lumière) : 18 pc à moins de 1 kpc, 78 pc entre 1 et 2, 178 pc entre 2 et 4,
  379 pc entre 4 et 8 kpc.
- Vitesse radiale inconnue (comptée nulle) : pour les étoiles qui l'ont, la mettre à zéro déplacerait la lumière de 1,6 kpc
  (médiane) à +44,6 Ma, 35 pc par million d'années. C'est la traînée.

## Ce qui change

1. **Orbite fiable** (`gaia_convertir.py --erreurs`, drapeau 2 de gaia.bin) : vitesse radiale mesurée et vitesse 3D connue à mieux
   que 10 km/s d'après les erreurs publiées (parallaxe, mouvement propre, vitesse radiale). 23,5 M étoiles, 67 % de la lumière.
   Seules ces étoiles avancent loin d'aujourd'hui. Les autres, et toute la lumière additionnée (`gaia_agrege.bin`), s'effacent en
   exp(-(t / 3 Ma)²) : sans vitesse sûre, l'erreur de place dépasse l'erreur de distance d'aujourd'hui en 2 à 5 Ma. L'écran le dit.
   Pour le fil appli PC : `GaiaRenderer::starReliable`, `leafReliableShare`, `reliableCount`, `reliableLight`, `shownLightShare`.
2. **Poussière retirée vue de loin** (accord de Marc, 12/11/2026) : `gaia_telecharger.py --jeu poussiere` (A_G et E(BP-RP) de
   GSP-Phot, estimés par Gaia depuis le spectre BP/RP mesuré de chaque étoile et sa parallaxe, Andrae et al. 2023 : mesure +
   modèles d'étoiles). La magnitude du fichier reste celle mesurée depuis la Terre. Le shader retire la poussière Soleil-étoile en
   proportion de l'écart caméra-Soleil rapporté à la distance de l'étoile (rien au Soleil, tout au-delà) [Supposition sur la
   géométrie : la poussière caméra-étoile n'est pas ajoutée]. Même chose pour les cases de lumière additionnée (`gaia_agreger.py` :
   flux sans poussière des sources estimées, case par case).

## Résultats

Voir la section « Avant / après » (captures) ajoutée à la fin du travail.
