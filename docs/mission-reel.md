# Mission 2 — Le réel seulement

But : plus rien à l'écran qui ne soit mesuré, calculé à partir de mesures, ou déclaré inconnu. Et un zoom qui suit l'objet que l'on regarde.

Décisions de Marc : voir `docs/plan-reel.md`. Ordre des lots : C, A, B, D, E, E2.

Mission finie quand : les quatre critiques rendent PASSE sur chaque lot, et Marc a confirmé à l'écran, sur son téléphone, les six constats du 11 novembre 2026.

Chaque tâche vise 400 lignes modifiées au plus et suit la boucle de `CLAUDE.md`. Avant la tâche R1 : la tâche T1 de la mission 1 (contrôles automatiques du dépôt). Les lots C et A n'ont besoin d'aucun geste Firebase. Les lots B et D ont besoin du stockage (T2 et T6 de la mission 1).

Les valeurs marquées [à vérifier] viennent de la mémoire de l'assistant : le critique de vérité doit les confirmer sur la source avant usage.

## Lot C — Le zoom suit l'objet

### R1 — Le zoom se fait autour de l'objet touché
- Avant : toucher un objet ouvre sa fiche ; le zoom continue de se faire autour du Soleil ou de l'astre suivi. Seul « Y aller » pose `S.center`.
- Après : toucher un objet le prend pour centre, sans changer l'échelle. Molette, pincement, boutons et barre des échelles zooment autour de lui. « Y aller » ne règle plus que l'échelle. Fermer la fiche rend le centre en douceur.
- Fini quand, test à l'écran `zoom-objet` : pour dix objets (Lune, Jupiter, comète de Halley, Voyager 1, Sirius, une étoile Gaia sans nom, Sagittarius A*, Grand Nuage de Magellan, Triangle, une galaxie photographiée lointaine), après un toucher puis un zoom de six puissances de dix dans chaque sens, l'objet reste à moins de 10 % de la demi-largeur de l'écran du centre, à chaque image.
- Fichiers touchés : `app/src/60_app.js` (`select`, `flyTo`, `clampZoom`, calcul de la cible dans `step`), `app/test/`.
- Pièges : la cible glisse déjà du Soleil vers le centre de la Galaxie aux grandes échelles ; le zoom vers l'infiniment petit vise la surface de la Terre. Garder ces deux comportements.

### R2 — L'objet suivi reste repérable, à toute échelle et quand le temps défile
- Avant : une étoile suivie disparaît quand la couche des étoiles s'éteint ; rien ne dit qu'un objet n'existe plus à la date affichée.
- Après : un repère (anneau et nom) accompagne l'objet suivi à toutes les échelles. Si l'objet n'existe pas à la date affichée, le repère le dit (« pas encore né », « englouti », « sort inconnu »).
- Fini quand : dans le test `zoom-objet`, le repère est présent à chaque image ; test `suivi-temps` : Mars suivi pendant 1 000 ans simulés en dix secondes reste centré.
- Fichiers touchés : `app/src/60_app.js`, `app/src/40_render.js`.

### R3 — Sans objet touché, le zoom vise le point sous les doigts
- Avant : le zoom vise toujours le centre de l'écran.
- Après : molette, le point sous le curseur ; pincement, le milieu des deux doigts. Ce point reste fixe à l'écran pendant le zoom. Le décalage s'annule sur « Accueil », sur un arrêt de la barre, ou quand on touche un objet.
- Fini quand, test `zoom-point` : une étoile nommée placée sous le curseur, à 30 % du bord, reste sous le curseur à 3 pixels près pendant un zoom de deux puissances de dix.
- Fichiers touchés : `app/src/60_app.js`.

## Lot A — La fin des planètes et du Soleil

### R4 — Inventaire de vérité de l'avenir lointain (aucun code)
- Avant : `FATE`, `FATE_P`, `ENG`, `F.sysK` et plusieurs événements font disparaître des astres à des dates fixées à la main.
- Après : `docs/verite-avenir.md` liste chaque changement programmé dans l'avenir (Soleil, planètes, lunes, anneaux, nuage d'Oort, Grand Nuage, fusion), son statut (mesuré, calculé, inconnu), sa source, et ce qu'il devient : gardé, recalculé, ou coupé avec la mention « inconnu ».
- Fini quand : le critique de vérité rend PASSE sur ce tableau ; chaque fondu et chaque date fixée à la main y figure.
- Déjà vérifié : Mars n'est pas dans les simulations de Zink, Batygin et Adams 2020 ; son départ à 43 milliards d'années était un choix de l'assistant.

### R5 — Mercure et Vénus : la spirale calculée
- Avant : la planète disparaît d'un coup à la date `ENG`.
- Après : à chaque pas du modèle solaire, l'orbite s'élargit avec la perte de masse du Soleil, puis se resserre sous l'effet des marées et du frottement dans l'enveloppe de la géante. La planète descend en spirale et entre dans le Soleil. La fiche dit : calculé, avec la méthode et sa source.
- Méthode : celle de Schröder et Smith 2008 (marées et frottement à chaque pas), avec leurs paramètres. Le modèle solaire de la page (`SUN_TRACK`) doit être comparé à leur table 1 [à vérifier].
- Fini quand, test de calcul `engloutissement` : avec cette méthode, un corps placé aujourd'hui à 1,00 UA est englouti et un corps placé à 1,2 UA survit (résultat publié : seuil vers 1,15 UA) ; Mercure et Vénus sont englouties ; le rayon d'orbite affiché décroît de façon continue sur au moins 30 images à vitesse normale.
- Fichiers touchés : `app/src/25_future.js`, `app/src/40_render.js`, `app/test/`.

### R6 — La Terre : sort inconnu
- Avant : la Terre est engloutie à la date calculée par la page.
- Après : jusqu'au moment où les études divergent, la Terre est dessinée sur son orbite élargie. À ce moment, elle n'est plus dessinée et un panneau dit : « Sort inconnu : engloutie selon Schröder et Smith 2008 et Rasio et al. 1996, rescapée selon Rybicki et Denis 2001. » Pas de fondu : une coupure nette, expliquée.
- Fini quand : test `terre-inconnue` ; le critique de vérité confirme chaque référence sur la source.
- Fichiers touchés : `app/src/60_app.js`, `app/src/40_render.js`.

### R7 — Après la mort du Soleil : orbites élargies, puis « inconnu »
- Avant : Uranus, Pluton, Neptune, Mars, Saturne et Jupiter s'éteignent à 39, 40, 41, 43, 45 et 95 milliards d'années.
- Après : les planètes restantes tournent sur des orbites 1,85 fois plus larges (calculé). Dix milliards d'années après la fin de la perte de masse du Soleil, borne publiée de stabilité, l'affichage du système solaire s'arrête sur un panneau : « Inconnu : des étoiles de passage finiront par défaire le système. Les simulations donnent une première éjection vers 30 milliards d'années en moyenne et une dissolution complète vers 100 milliards, sans ordre certain. »
- Lunes et anneaux : même règle. Phobos (rapprochement mesuré, donc calculable), anneaux de Saturne et Triton sont tranchés dans R4.
- Fini quand : `grep -n "FATE_P" app/src` ne trouve rien ; aucun fondu d'opacité lié à une date pour un astre ; test `avenir` : à +9 milliards d'années les orbites valent 1,85 fois l'actuel à 1 % près ; à +20, +50 et +100 milliards d'années, le panneau « inconnu » est affiché et aucune planète n'est dessinée.
- Fichiers touchés : `app/src/60_app.js`, `app/src/40_render.js`, textes de la chronologie.

## Lot B — La fusion avec Andromède

Marc garde la fusion, marquée « scénario », calculée à l'avance avec une vraie attraction mutuelle, puis rejouée.

### R8 — Méthode et conditions de départ (aucun code de page)
- Après : `docs/fusion-methode.md` fixe le logiciel de calcul (libre et éprouvé), les modèles de galaxies (masses et profils, cohérents avec `mwMass`), les positions et vitesses de départ avec leurs sources, le Triangle et le Grand Nuage comme corps étendus, les 39 galaxies naines comme traceurs, le nombre de particules, le budget de calcul (moins de six heures sur les machines du dépôt) et la taille des fichiers produits.
- Fini quand : le critique de vérité rend PASSE ; un essai réduit conserve l'énergie à 1 % près sur un milliard d'années.
- À trancher dans ce document : quelle mesure de la vitesse d'Andromède sert de départ (la page en propose trois), et ce que l'on dit de l'incertitude (environ une chance sur deux de fusion en dix milliards d'années selon Sawala et al. 2025 [à vérifier]).

### R9 — Calcul et images clés
- Après : une tâche du dépôt lance le calcul et écrit des images clés (positions des particules affichées à intervalle fixe), les centres des galaxies et le trajet d'un traceur placé à la position du Soleil.
- Fini quand : dérive d'énergie inférieure à 1 % sur tout le calcul ; date de la fusion écrite et comparée à l'estimation à deux corps de la page (5,85 milliards d'années) et aux valeurs publiées ; taille totale sous le budget fixé en R8.
- Fichiers touchés : `pipeline/fusion/`, tâche du dépôt.

### R10 — La page rejoue le calcul
- Avant : `dynInit` et `dynAdvance` calculent en direct, en retard sur l'horloge, puis se figent trois milliards d'années après la fusion.
- Après : la page interpole entre les images clés. L'image correspond toujours à l'heure affichée, dans les deux sens du temps. Après la dernière image, un panneau dit « fin du calcul ».
- Fini quand, test `fusion-horloge` : à vingt dates tirées au hasard, l'image affichée correspond à l'horloge à un intervalle près ; le message « Calcul de la rencontre » n'existe plus ; le temps par image reste sous deux fois la référence.
- Fichiers touchés : `app/src/25_future.js`, `app/src/60_app.js`, `app/src/40_render.js`.
- Attend : R9, et T2 et T6 de la mission 1.

### R11 — La galaxie résultante
- Après : une fois la fusion faite, un seul nom, une seule fiche, avec ce que le calcul donne (taille, forme) et la mention « scénario calculé » partout. Le sort du Triangle et du Grand Nuage est celui du calcul.
- Fini quand : test `fusion-resultat` ; le critique d'usage rend PASSE.
- Fichiers touchés : `app/src/60_app.js`.

## Lot D — Les petites échelles

Décisions : on reste dans l'eau ; d'abord les vraies formes calculées, ensuite des images réelles de laboratoire ; le proton tel que mesuré ; arrêt à 10⁻²⁰ m.

### R12 — Un zoom fluide et mesuré
- Avant : quarante puissances de dix au même geste, des paliers vides, aucune mesure sur téléphone.
- Après : vitesse de zoom constante par puissance de dix ; les étendues où rien ne change sont traversées vite et le disent ; compteur d'images par seconde affichable ; boules remplacées par un rendu léger.
- Fini quand : tableau du critique de rendu sur toute la plage ; Marc lit le compteur sur son téléphone et confirme.
- À demander à Marc au début de la tâche : son téléphone et son navigateur ; où il voit des saccades.
- Fichiers touchés : `app/src/40_render.js` (`initMicro`), `app/src/60_app.js`.

### R13 — Arrêt à 10⁻²⁰ m
- Avant : cercles repères jusqu'à la longueur de Planck, et un bouillonnement « vue d'artiste ».
- Après : le zoom s'arrête vers 10⁻²⁰ m sur un écran « Inconnu : aucune expérience n'a sondé plus fin. Il reste quinze puissances de dix jusqu'à la longueur de Planck, 1,616 × 10⁻³⁵ m. » Plus de bouillonnement.
- Fini quand : `clampZoom` borne à 10⁻²⁰ m ; test `fin-du-zoom` ; arrêts de la barre mis à jour.

### R14 — Orbitales calculées
- Après : atome d'hydrogène, formes exactes (solution de l'équation de Schrödinger) ; molécule d'eau, densité d'électrons et orbitales occupées calculées par un logiciel de chimie quantique dans `pipeline/`, exportées sur une grille compacte.
- Fini quand, test `orbitales` : les formes de l'hydrogène correspondent aux formules à 1 % près ; pour l'eau, les énergies calculées sont comparées aux énergies d'ionisation mesurées [à vérifier], avec l'écart affiché ; le critique de vérité rend PASSE.
- Fichiers touchés : `pipeline/quantique/`, `app/src/40_render.js`, `app/gen/`.

### R15 — Le proton tel que mesuré
- Avant : trois points, des tubes et des paires dessinés à la main.
- Après : le contenu du proton vient d'un jeu public de mesures (distributions de partons). Plus on regarde fin, plus la part des gluons et des paires augmente. Les tubes dessinés sont retirés.
- Fini quand, test `proton` : à chaque finesse, la somme des parts d'impulsion vaut 1 à 0,01 près et le compte net donne deux quarks up et un down à 0,02 près ; la source et sa licence sont citées.

### R16 — Le noyau tel que mesuré
- Après : la répartition de charge du noyau d'oxygène vient des mesures de diffusion d'électrons. L'arrangement en quatre groupes est retiré, ou gardé avec la mention « schéma » si le critique de vérité le juge sourcé.
- Fini quand : rayon affiché égal à la valeur publiée, 2,70 fm [à vérifier] ; test `noyau`.

### R17 — Images réelles de laboratoire
- Après : à chaque palier où elle existe, une image réelle avec son crédit (microscope à force atomique, microscope à effet tunnel, collision enregistrée). Chaque image a une licence qui permet de l'afficher.
- Fini quand : `docs/images-reelles.md` liste image, source, licence, crédit ; le critique de vérité rend PASSE.
- Attend : T2 et T6 de la mission 1.

## Lot E — Les galaxies figées

### R18 — Chaque galaxie dit pourquoi elle bouge ou non
- Décision : sans vitesse mesurée, une galaxie reste en place et sa fiche le dit.
- Après : pour chaque famille (Groupe local, galaxies proches, galaxies photographiées, galaxies lointaines), la fiche a une ligne « Mouvement » et une ligne « Rotation » avec leur statut.
- Fini quand, test `fiches-galaxies` : vingt galaxies de chaque famille ont ces deux lignes.
- À demander à Marc : à quelle échelle il voit encore des galaxies figées.

## Lot E2 — La rotation des galaxies photographiées

### R19 — Mesurer le sens de rotation sur les photos
- Après : un outil lit l'enroulement des bras sur chaque photo. Il est d'abord contrôlé sur des galaxies dont le sens est publié.
- Fini quand : au moins 90 % d'accord sur le jeu de contrôle. Sinon la tâche s'arrête et ces galaxies restent « sens inconnu ».
- Connu : 603 des 869 galaxies proches du catalogue de Karachentsev ont une vitesse de rotation mesurée.

### R20 — Les faire tourner
- Après : les galaxies dont la vitesse et le sens sont connus tournent. Leur image reste affichée pendant un tour au plus. Les autres disent pourquoi elles ne tournent pas.
- Fini quand : test `rotation-photos` ; critiques de vérité et de rendu PASSE.
