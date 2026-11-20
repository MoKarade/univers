# Andromède, Triangle, Voie lactée : pourquoi pas de spirale, et comment en avoir une vraie

13 novembre 2026

## En bref

- La boule blanche et verte n'est pas Andromède : ce sont 10 000 scénarios de position, un point par scénario. [Certain, déjà établi par l'autre fil]
- Les remplacer par les disques du calcul de fusion ne donnera **pas** de spirale. Je l'ai mesuré dans le calcul lui-même : aujourd'hui, ces disques sont parfaitement lisses, sans aucun bras. [Certain, mesuré]
- Pire : dès qu'on appuie sur Play, ces disques se déforment tout seuls en 300 à 500 millions d'années (une grosse barre apparaît). C'est exactement la rupture que tu ne veux pas. [Certain, mesuré]
- Ma recommandation : dessiner chaque galaxie aujourd'hui à partir des vraies images (remises à plat par calcul), puis faire évoluer ces mêmes étoiles par la gravité, depuis un état déjà stable. Le gaz et la naissance d'étoiles viennent en deuxième étape.
- Continuité : chaque galaxie est un seul et même ensemble d'étoiles d'aujourd'hui jusqu'à la fusion. Aucun changement de représentation en route, donc aucune bascule comme celle que tu as vue vers 1 milliard d'années.

## 1. Ce que j'ai mesuré dans le calcul de fusion

Calcul examiné : celui à 3 millions de particules, 1 million d'étoiles gardées. J'ai mesuré la « force des bras » (part des étoiles rangées en motif à deux bras ou en barre ; 0 = disque lisse, 0,3 et plus = barre ou bras très marqués) et l'épaisseur du disque.

| Galaxie | Aujourd'hui | Après 0,5 milliard d'années | Après 3 milliards d'années |
|---|---|---|---|
| Andromède, entre 3 et 6 kpc | 0,002 (lisse) | 0,47 | 0,28 |
| Andromède, entre 6 et 10 kpc (là où est le vrai anneau) | 0,002 | 0,23 | 0,06 (redevenu lisse) |
| Andromède, épaisseur | 0,40 kpc | 0,40 à 0,50 | 0,61 à 0,67 |
| Voie lactée, entre 3 et 6 kpc | 0,001 (lisse, sans barre) | 0,40 | 0,51 |
| Triangle, centre | 0,003 | 0,13 | 0,24 (0,38 à 1 milliard) |

Lecture :

1. **Aujourd'hui, tout est lisse.** Les disques ont été tirés au hasard dans une formule ronde et régulière. Aucun bras, aucun anneau, aucune barre, aucune poussière. Le bruit de mesure est de 0,003 : on est en dessous.
2. **Le départ n'est pas en équilibre.** Les disques du modèle ne restent pas ronds. Une barre pousse violemment en 0,3 à 0,5 milliard d'années dans la Voie lactée et dans Andromède, et dès 0,1 milliard dans le Triangle. La vraie Voie lactée a déjà sa barre ; le vrai Triangle n'en a presque pas.
3. **Après 2 milliards d'années, il ne reste qu'une barre au centre et un disque extérieur lisse et épaissi** (+60 % d'épaisseur). Les bras ne durent pas.
4. L'inclinaison d'Andromède vue du Soleil est bonne dans le calcul : 77,0° (mesure : 77°). Le Triangle est à 49° (mesure : 54 à 56°, à corriger).

## 2. Pourquoi un disque de particules ne donne pas la vraie spirale

**Conditions de départ.** Le calcul part d'un disque « de manuel » : même forme que la Voie lactée du modèle, agrandie de 15 %. Rien n'y vient d'une image d'Andromède. Écarts avec les mesures :

| Andromède | Dans le calcul | Mesuré | Source |
|---|---|---|---|
| Longueur d'échelle du disque | 3,0 kpc | 5,3 ± 0,5 kpc | Courteau et al. 2011, ApJ 739, 20 |
| Masse du bulbe | 0,75 × 10¹⁰ M☉ | environ 3,1 × 10¹⁰ M☉ (bulbe classique 1,2 + bulbe en boîte 1,9) | Blaña Díaz et al. 2017 et 2018 |
| Barre | aucune | oui, tourne à 40 ± 5 km/s/kpc | Blaña Díaz et al. 2018 |
| Anneau de formation d'étoiles | aucun | rayon environ 10 kpc, décentré | Gordon et al. 2006 ; Block et al. 2006 (Nature) |
| Distance | 783 kpc | 761 ± 11 kpc | Li et al. 2021 (Céphéides) |
| Gaz et poussière | aucun | gaz environ 5 à 7 × 10⁹ M☉, poussière 5,4 × 10⁷ M☉ | Chemin et al. 2009 ; Braun et al. 2009 ; Draine et al. 2014 |

Le Triangle est modélisé avec un disque de 1,4 kpc sans gaz, alors que le gaz y pèse environ un tiers de la masse visible (étoiles 4,8 × 10⁹ M☉, Corbelli et al. 2014). Le Petit Nuage de Magellan n'est pas dans le calcul, alors que c'est son interaction avec le Grand Nuage qui a créé le vrai Courant magellanique (Besla et al. 2012).

**Les bras qu'on voit sur les photos sont surtout du gaz, de la poussière et des étoiles jeunes.** Les étoiles bleues massives vivent moins de 100 millions d'années et meurent près de l'endroit où elles sont nées : elles dessinent les bras. Les vieilles étoiles forment un disque presque lisse (contraste des bras de 10 à 30 % seulement en infrarouge). Un calcul sans gaz ne contient que des vieilles étoiles : même parfait, il donne un disque pâle et lisse.

**Absence de gaz : les bras s'éteignent.** Le gaz se refroidit et garde le disque « calme », ce qui permet aux bras de se reformer sans cesse. Sans gaz, les étoiles s'agitent de plus en plus et les bras s'effacent en 1 à 2 milliards d'années (Sellwood & Carlberg 1984). C'est ce que je mesure plus haut.

**Nombre de particules et chauffage numérique.** Andromède a environ 1 000 milliards d'étoiles ; le calcul en a 450 000 dans le disque, de 226 000 M☉ chacune, et des particules de matière noire 6 fois plus lourdes qui les bousculent. Il faut au moins quelques millions de particules de disque pour que les bras tiennent (Fujii et al. 2011), et 100 millions pour des bras fins et durables (D'Onghia et al. 2013). Avec 60 000 particules, le Triangle est très en dessous.

**Résolution.** L'adoucissement de la gravité est de 115 pc et le disque du modèle fait 350 pc d'épaisseur. Les vraies bandes de poussière font environ 100 pc d'épaisseur : le calcul ne peut pas les contenir.

**Même un calcul parfait donne « une » spirale, pas « la » spirale.** Les bras naissent du bruit et du passé de la galaxie (pour Andromède : le passage de M32 il y a environ 200 millions d'années, Block et al. 2006). Aucun calcul parti d'un disque rond ne retrouve les bras au bon endroit. Il faut les mettre au départ, d'après les mesures.

**Inclinaison.** À 77°, Andromède vue d'ici est un fuseau 4,4 fois plus long que large, pas une spirale de face. Ce qu'on reconnaît d'ici : le bulbe brillant, les bandes sombres de poussière et l'anneau. La spirale n'apparaît que si la caméra s'approche et passe au-dessus du disque. Il faut donc un vrai disque en 3D, pas une photo.

**Énergie noire.** Je l'ai chiffrée : à 20 kpc du centre d'Andromède, elle vaut 2 cent-millionièmes de la gravité de la galaxie. Elle ne change rien à la forme des bras. Elle sera quand même dans le calcul, puisqu'elle y est partout. [Certain, calcul fait ici]

## 3. Les solutions

| Solution | Ce que ça donne | Avantages | Inconvénients |
|---|---|---|---|
| A. Disque lisse aux profils mesurés (disque 5,3 kpc, bulbe, rotation mesurée 250 à 270 km/s) | Bonne taille, bon éclat, pas de bras | Simple, stable | Toujours pas de spirale |
| B. Photo remise à plat, collée sur un disque | Belle de face tout de suite | Très rapide | Plate, fausse de profil, ne peut ni évoluer ni fusionner. Casse à Play |
| C. Bras tracés par une formule de spirale | Schéma propre | Léger | Andromède n'est pas une spirale régulière (anneau + morceaux de bras) : ce serait un dessin |
| **D. Étoiles tirées dans les vraies images, remises à plat** | Les vrais bras, le vrai anneau, la vraie poussière, en 3D | C'est Andromède telle que mesurée, précise à environ 100 pc. Données gratuites | Le côté écrasé par l'inclinaison est moins net ; le bulbe et la barre doivent être modélisés à part |
| **E. Gravité seule, départ stable et barre déjà en place** | Évolution et fusion sans rupture à Play | Continuité garantie ; calcul déjà possible sur ton PC | Les bras s'estompent en 1 à 2 milliards d'années, pas de nouvelles étoiles |
| F. Gravité + gaz + naissance d'étoiles | Bras qui se reforment, flambée d'étoiles pendant la fusion, galaxie finale rouge | Le plus réaliste. Seule façon d'avoir le vrai Courant magellanique | Nouveau moteur de calcul à installer ; plusieurs jours de calcul (durée : je ne sais pas encore, à mesurer) |

**Recommandation : D + E maintenant, F ensuite.**

- **Aujourd'hui (D).** Vieilles étoiles d'après l'image infrarouge Spitzer à 3,6 µm (Barmby et al. 2006). Étoiles jeunes d'après l'ultraviolet GALEX (Thilker et al. 2005) et l'infrarouge à 24 µm (Gordon et al. 2006, finesse 22 pc). Poussière d'après Herschel (Draine et al. 2014) et Hubble PHAT (Dalcanton et al. 2015 ; 117 millions d'étoiles mesurées sur un tiers du disque). Gaz d'après la carte radio (Braun et al. 2009). Vitesses d'après la rotation mesurée (Chemin et al. 2009 ; Corbelli et al. 2010). Étoiles de notre galaxie et galaxies satellites (M32, NGC 205) retirées de l'image avant.
- **Quand le temps avance (E).** Ce sont ces mêmes étoiles qui partent, avec leurs vitesses. Le disque est d'abord rendu stable (masses mesurées, barre déjà formée et placée au bon angle) : rien ne change brusquement à Play. Les bras se déforment ensuite peu à peu, comme en vrai. La masse est suivie étoile par étoile.
- **Franchise.** Personne ne peut prédire la forme exacte des bras d'Andromède dans 1 milliard d'années. Au-delà de quelques centaines de millions d'années, l'écran dira « calculé, forme plausible ».

## 4. Triangle (M33)

- Mesures : inclinaison 54 à 56°, distance 840 à 860 kpc (le calcul utilise 809), rotation 120 à 130 km/s, pas de bulbe, barre très faible, disque de gaz tordu au bord (Corbelli et al. 2014 ; Kam et al. 2017).
- C'est une spirale « floconneuse » : beaucoup de petits morceaux de bras, portés par le gaz. Sans gaz, impossible de la reproduire. Référence : Dobbs et al. 2018 l'ont obtenue avec gaz et naissance d'étoiles.
- Dans le calcul actuel, elle devient une galaxie barrée en 1 milliard d'années. C'est faux.
- Même solution D + E, avec les images Spitzer, GALEX et Hubble PHATTER (22 millions d'étoiles, Williams et al. 2021). Moins inclinée, donc remise à plat plus précise (environ 30 pc). L'étape F y compte plus qu'ailleurs.

## 5. Voie lactée

- On est dedans : pas de photo de l'extérieur. Mais la structure est mesurée : barre de 5,0 ± 0,2 kpc de demi-longueur, tournée de 28 à 33° (Wegg et al. 2015), tournant à 39 ± 3,5 km/s/kpc (Portail et al. 2017), bulbe et barre de 1,9 × 10¹⁰ M☉ ; quatre bras tracés par 190 sources radio (Reid et al. 2019) ; masse d'étoiles 5 à 6 × 10¹⁰ M☉ (Licquia & Newman 2015).
- Dans le calcul actuel : pas de barre aujourd'hui, bulbe 4 fois trop léger, disque trop lourd. La barre pousse ensuite toute seule, à un angle quelconque.
- Solution : partir d'un disque déjà évolué seul (le calcul « Voie lactée seule » à 10,5 millions de particules existe), choisir l'instant et l'angle où sa barre et ses bras collent le mieux aux mesures, et prendre cet état comme « aujourd'hui ». Les étoiles Gaia restent par-dessus.
- **Grand Nuage de Magellan** : Gaia y voit environ 11 millions d'étoiles une par une (Gaia Collaboration, Luri et al. 2021). On peut donc y mettre les vraies étoiles, avec sa barre décentrée et son bras unique. Il faut ajouter le Petit Nuage au calcul.

## 6. Ce que je transmets au fil « Voie lactée entière »

- Les disques du calcul actuel ne sont pas un bon « aujourd'hui » : lisses, puis instables à Play.
- Distance d'Andromède à passer de 783 à 761 kpc et celle du Triangle à revoir : cela change un peu l'orbite.
- Le Petit Nuage de Magellan manque.

## 7. Limites de cette analyse

- Les mesures du calcul (tableau du § 1) sont faites ici, sur les fichiers. [Certain]
- Les chiffres des publications sont cités de mémoire [Probable] et seront relus dans chaque article avant d'entrer dans le code.
- Je n'ai pas encore téléchargé les images ni mesuré la durée d'un calcul avec gaz.
