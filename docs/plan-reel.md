# Plan « le réel seulement » (11 novembre 2026, décisions prises)

## Constats de Marc, vérifiés

| Constat | Vérification | Cause |
|---|---|---|
| La fusion ne forme pas une nouvelle galaxie | Reproduit : à 6,1 milliards d'années (fusion annoncée à 5,85), l'image montre encore Andromède intacte ; ensuite, un petit amas lumineux, les étiquettes « Voie lactée » et « Andromède » inchangées, le Triangle figé | Calcul approché fait en direct, en retard sur l'horloge (26 à 66 % pendant la rencontre) ; aucun objet « galaxie résultante » |
| Le temps ne passe plus | Probable : le calcul des étoiles s'arrête 3 milliards d'années après la fusion (`dynT` plafonné), tout se fige alors que l'horloge continue. Blocage de l'horloge elle-même : pas reproduit | Plafond volontaire du calcul |
| Les planètes s'effacent | Confirmé dans le code : `FATE_P` éteint chaque planète à une date fixe (Uranus 39, Pluton 40, Neptune 41, Mars 43, Saturne 45, Jupiter 95 milliards d'années). Mars à 43 est un choix, pas un résultat | Fondu à la place d'une trajectoire |
| Zoomer sur un objet ne le garde pas à l'écran | Confirmé : le zoom se fait autour du Soleil ou de l'astre suivi, pas autour de l'objet touché | Conception du zoom |
| Des galaxies ne bougent pas ou ne tournent pas | Fait : 39 galaxies locales sur leur orbite, dont le Triangle ; les quatre galaxies à disque du Groupe local tournent à leur vitesse et dans leur sens mesurés. Restent : 59 galaxies locales sans vitesse mesurée ; la rotation des 943 galaxies photographiées et des galaxies lointaines | Sens de rotation absent des catalogues ; galaxies lointaines dessinées comme des points |
| Les petites échelles : pas fluide, zoom pénible, rien de quantique | Fluidité jamais mesurée sur téléphone. 42 puissances de dix au même geste. Seul le nuage d'électrons est quantique ; le reste est fait de billes | Conception |

## Lots proposés

Chaque lot suit la boucle de `CLAUDE.md` : construire, puis les quatre critiques, puis le résumé.

- Lot C, zoom centré sur l'objet. Fini quand : pour 10 objets de types différents, l'objet touché reste à l'écran sur toute la plage de zoom où il existe.
- Lot A, fin des planètes et du Soleil. Fini quand : plus aucun fondu ne remplace un phénomène ; chaque disparition est soit une trajectoire calculée, soit un arrêt avec la mention « inconnu ».
- Lot B, fusion. Fini quand : l'image correspond à l'horloge à chaque instant ; le résultat est une galaxie nommée, avec sa fiche ; le Triangle est traité ; rien ne se fige.
- Lot D, petites échelles. Fini quand : le zoom est continu et mesuré ; chaque palier montre du mesuré ou du calculé quantique, pas des billes.
- Lot E, galaxies figées. Fini quand : chaque galaxie affichée dit pourquoi elle bouge ou pourquoi elle ne bouge pas.
- Lot E2, rotation des galaxies photographiées. Vitesse mesurée pour 603 des 869 galaxies proches (catalogue de Karachentsev). Sens : à mesurer sur l'enroulement des bras de chaque photo, avec contrôle sur les galaxies dont le sens est publié. Fini quand : chaque galaxie à bras visibles tourne dans le sens mesuré, les autres disent pourquoi elles ne tournent pas.

Ordre décidé : C, A, B, D, E, puis E2.

## Décisions de Marc (11 novembre 2026 : toutes les recommandations)

| N° | Sujet | Décision |
|---|---|---|
| 1 | Quand la science ne donne qu'un scénario parmi d'autres | Arrêt de l'affichage et mention « inconnu » |
| 2 | Mercure et Vénus avalées par le Soleil | Spirale calculée |
| 3 | La Terre | « Sort inconnu » |
| 4 | Fusion avec Andromède | Gardée, marquée « scénario » (exception voulue à la décision 1) |
| 5 | Calcul de la fusion | Fait à l'avance avec une vraie attraction mutuelle, puis rejoué |
| 6 | Zoom avec un objet touché | Autour de cet objet, dès qu'il est touché |
| 7 | Zoom sans objet touché | Vers le point sous les doigts |
| 8 | Quantique | D'abord les vraies formes calculées, ensuite des images réelles de laboratoire |
| 9 | Proton | Tel que mesuré : plus de gluons quand on regarde plus fin |
| 10 | Sous 10⁻²⁰ m | Arrêt, écran « inconnu ». La longueur de Planck n'est plus qu'un chiffre cité |
| 11 | Point de chute du zoom | L'eau |
| 14 | Galaxie sans vitesse mesurée | En place, raison affichée |
| 15 | Où travailler | Sur le dépôt, avec Claude Code et les quatre critiques |
| 16 | Ordre des lots | C, A, B, D, E, puis E2 |

Encore ouvert (pas de recommandation possible) :
- 12 : le téléphone et le navigateur de Marc, et l'endroit où il voit des saccades. À demander au début de R12.
- 13 : l'échelle où Marc voit encore des galaxies figées. À demander au début de R18.

Le détail des tâches est dans `docs/mission-reel.md`.
