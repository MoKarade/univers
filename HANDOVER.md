# Univers — passation

## En bref
Page web unique qui simule l'univers en 3D, du système solaire à l'horizon cosmique, avec le temps qui défile du Big Bang à +100 milliards d'années. Tout ce qui peut l'être vient de catalogues réels ; le reste est marqué « généré » ou « supposé » dans la page.

Jusqu'ici elle a été construite dans une conversation Claude et publiée comme artefact : https://claude.ai/artifact/RxLfq4UzbCuCxpg6dBkAGV
Cette forme est au plafond : une page de 16 Mo au plus, des fichiers attachés de 20 Mo au plus déposés un par un, 135 Mo chargés d'un bloc, aucune mesure possible sur un vrai écran.

## Décisions de Marc (11 novembre 2026)
- Hébergement : Google Firebase. Hosting pour la page, Cloud Storage pour les données.
- Accès : privé. Connexion Google, un seul compte autorisé (secret `AUTHORIZED_EMAIL`).
- Coût : formule Blaze, alerte de budget à 10 $ par mois. Blaze n'a pas de plafond strict : rien de public tant que la consommation n'est pas mesurée.
- Volume : « le plus possible », par paliers (voir « Suite »).
- Ordre : d'abord le chargement par zone, ensuite les données.
- Construction : Claude Code sur ce dépôt. Aucune commande sur le PC de Marc.

## Arborescence
- `app/src/` : le code de la page. `app/gen/` : données générées, embarquées dans la page. `app/build.py` : assemble le tout en un seul fichier HTML. `app/test/` : tests.
- `pipeline/` : scripts qui ont produit les données. Écrits au fil de l'eau, voir `pipeline/README.md`.
- `infra/` : brouillons de configuration Firebase. Non testés.
- `docs/` : la mission en cours, les gestes de Marc, le format de tuiles proposé.
- Hors dépôt : le dossier `seed/` (135 Mo, 17 fichiers), remis à part. Ce sont les fichiers aujourd'hui attachés à l'artefact.

## Construire et tester
- `python3 app/build.py` écrit `dist/index.html`. Vérifié : ce fichier est identique, octet pour octet, à la page publiée le 11 novembre 2026.
- `for f in app/test/*.test.js; do node "$f" || exit 1; done` : sept tests de calcul, tous verts à la remise.
- `python3 app/test/shots.py desk '<spec JSON>'` : captures d'écran sans carte graphique (Playwright, rendu logiciel). La spec est une liste de pas `["js", "<code>", null]` ; le code dispose de `window.__U`.
- Variables utiles : `U_URL` (adresse de la page), `U_INIT` (script lancé avant la page, par exemple `window.__TILES=[]; window.__PHOTOS=[];` pour tester sans fichiers en flux).

## Qui fait quoi dans le code
- `20_physics.js` : positions des planètes et de la Lune, cosmologie (équations de Friedmann), mouvement des étoiles.
- `25_future.js` : évolution du Soleil, orbites d'Andromède et du Grand Nuage, rencontre des galaxies (étoiles simulées une à une).
- `30_gen.js` : formats d'affichage, calendrier, générateurs de ce qui n'est pas mesuré.
- `40_render.js` : le rendu three.js. Une couche par famille d'objets, image en grande dynamique, halo lumineux.
- `60_app.js` : l'état (`S`), l'image courante (`F`), la navigation, le temps, les événements, la frise, les fiches, et le chargement des fichiers en flux (`TL`, `loadTile`, `tilesTick`, manifeste `TILE_MANIFEST`).
- `index.html` : la structure, les styles, les panneaux.

## Données : sources et volumes actuels
| Famille | Volume | Source | Où |
|---|---|---|---|
| Étoiles | 6,15 millions | Gaia DR3 jusqu'à la magnitude 12,85 ; HYG pour les 58 967 plus brillantes | page + flux `s1` à `s6` |
| Galaxies et quasars | 5,57 millions | DESI DR1, SDSS DR16Q, 2MRS, 6dFGS, 2dFGRS | page + flux `g1` à `g3` |
| Galaxies proches | 788 + 101 | Karachentsev et al. 2013 ; McConnachie 2012 | page |
| Photos de galaxies | 943 | Legacy Survey DR10 (couleur), DSS2 (noir et blanc) | `p0` à `p2` |
| Astéroïdes | 123 530 | JPL Small-Body Database | flux `a1`, noms `a1n` |
| Lunes | 30 | JPL Horizons | page |
| Sondes | 5, avec 11 survols | JPL Horizons (trajectoires réelles) | page |
| Exoplanètes | 6 436 autour de 4 829 étoiles | NASA Exoplanet Archive | page |
| Trous noirs | 245 + 37 | van den Bosch 2016 ; BlackCAT | page |
| Pulsars, amas | 2 475 pulsars | ATNF ; Harris ; Cantat-Gaudin | page |
| Événements | environ 190 | publications citées dans chaque fiche | `60_app.js` (`EV_RAW`) |
| Surfaces, ciel | 9 astres, 1 panorama | Solar System Scope (CC BY 4.0) ; ESO/S. Brunier (CC BY 4.0) | page |
| Étoiles qui frôlent le Soleil | 27 rencontres fiables à moins de 3 millions d'années | Bailer-Jones 2022 (ApJL 935, L9), table de l'auteur ; astrométrie Gaia DR3 ; noms SIMBAD | `gen/data13.js` |

Les formats binaires des fichiers en flux sont définis par leur décodeur (`loadTile` dans `60_app.js`) et leur encodeur (`pipeline/build_tiles.py`). Il n'existe pas d'autre spécification.

## Réel, calculé, supposé
- Réel : positions et mouvements des étoiles, distances des galaxies, orbites, trajectoires des sondes, photos.
- Calculé ici : positions des planètes à toute date, éclipses, expansion, âge des époques, rapprochements d'étoiles, rencontre avec Andromède, et la réponse du nuage d'Oort aux étoiles de passage (orbites de Kepler et coups de vitesse, `oortInit` et `updateOort`).
- Supposé, et dit dans la page : l'aspect de la Voie lactée, l'épaisseur et la face cachée des galaxies reconstruites, l'orientation sur le ciel des orbites d'exoplanètes, l'ordre d'éjection des planètes dans l'avenir lointain.

## Vérifié
- Planètes contre JPL DE440, 70 dates de 1851 à 2149 : écart de 0,3 à 2,5 secondes d'arc. Lune : 7,4 secondes d'arc, 9 km.
- Sept éclipses contre les tables de la NASA : même type, même minute à une près.
- Survols recalculés depuis les trajectoires JPL : à une ou deux minutes des heures publiées.
- Orientation des galaxies mesurée sur les photos : conforme pour cinq galaxies connues sur six. NGC 4945 est fausse (77° au lieu de 43°).
- Reprise après perte du contexte graphique : testée par simulation.

## Pas vérifié
- La page sur un vrai appareil : fluidité, mémoire, toucher. Tous les essais ont été faits en rendu logiciel.
- Environ 150 dates d'événements viennent de la mémoire des publications citées, sans relecture une à une.
- La mémoire utilisée quand tous les fichiers sont chargés (estimée à 600 Mo).

## Étoiles frôleuses (ajout du 11 novembre 2026)

- Les 27 étoiles sont ajoutées au catalogue principal au démarrage (`XS` dans `40_render.js`), avec la trajectoire publiée : instant, distance et vitesse du passage. Le côté du passage vient du mouvement rectiligne actuel : moins sûr.
- Leurs copies dans le second catalogue et dans les tuiles Gaia sont éteintes (`isPasser`). Vérifié hors ligne sur les données réelles : 4 copies dans le second catalogue, 11 dans les tuiles, aucune fausse correspondance.
- Chaque passage dévie les comètes du nuage d'Oort (`oortInit`). Les passages à moins de 0,7 parsec ont un événement dans la chronologie.
- Pas fait : les 14 rencontres fiables au-delà de 3 millions d'années (le mouvement des étoiles n'y est plus rectiligne dans la page), et les 20 rencontres marquées douteuses ou binaires dans l'article.
- Reconstruire : `pipeline/fetch_enc.py` (recherche directe dans Gaia, limitée à 125 parsecs par le temps de calcul autorisé), `pipeline/build_enc.py` (table publiée, à partir de `pipeline/raw/bj22.csv`).

## Ajouts du 11 novembre 2026 (suite) : tous les passages d'étoiles, infiniment petit, forme des galaxies

- Passages d'étoiles : 42 simulés (41 sans réserve de Bailer-Jones 2022, plus l'étoile de Scholz d'après Dupuy et al. 2019), y compris 14 au-delà de 3 millions d'années. Ces étoiles restent en ligne droite à toute date (`K.lin`). Les 20 passages douteux sont des événements « Contesté », non simulés (`DATA.PASS_DUB`).
- Infiniment petit : `initMicro` dans `40_render.js`. En plongeant vers la Terre (foyer `earth`), le zoom descend jusqu'à `LMICRO` (−35,3). Le point visé glisse du centre de la Terre à sa surface entre 10^7,2 et 10^6,4 m. Sous 150 m, le décor astronomique est figé derrière un fond opaque ; les objets minuscules utilisent l'échelle vraie `F.sT` et `F.lrT`. Paliers, textes et sources : table `MLEV` dans `60_app.js`.
- Forme des galaxies pendant la rencontre avec Andromède : chaque étoile simulée a une copie témoin qui ne sent que sa propre galaxie (`D.rx`, `D.rv`). À l'affichage, l'écart étoile-témoin est ajouté à la place que l'étoile aurait dans le modèle au repos. Les bras ne s'enroulent plus en anneaux ; une étoile arrachée reprend sa position calculée.
- Erreur corrigée : un commentaire `//` placé en milieu de ligne coupait le code qui le suivait. Trois endroits touchés, dont le décodage des couleurs des tuiles d'étoiles Gaia, publié ainsi au tour précédent (ces étoiles s'affichaient en noir). Règle pour la suite : jamais de `//` ajouté dans une ligne qui continue ; utiliser `/* */`.
- Pas vérifié : chargement réel des tuiles après correction (lecture du code seulement) ; fluidité sur téléphone ; page en ligne.
- Pas fait : attraction des planètes sur les astéroïdes.

## Galaxies naines du Groupe local (ajout du 11 novembre 2026)

- 38 galaxies suivent une orbite calculée au démarrage (`lgStart`, `lgApply` dans `60_app.js`) d'après leur vitesse mesurée : `gen/data14.js`, construit par `pipeline/build_lgv.py` à partir de la Local Volume Database (Pace 2024, `pipeline/raw/dwarf_all.csv`). L'association se fait par position dans le ciel, pas par nom.
- Attraction prise en compte : Voie lactée (`mwMass`), Andromède (même profil, 1,5 fois plus massif), Grand Nuage de Magellan. Table de -2 à +12 milliards d'années, un point tous les 20 millions d'années.
- Chaque galaxie a un numéro (`aId`) ; son déplacement arrive au shader par `uSh`.
- Contrôle : Naine du Sagittaire, plus près à 12 kpc, plus loin à 48 kpc, dernier passage il y a 40 millions d'années (valeurs publiées : environ 15 et 60 à 70 kpc, passage récent). L'écart sur le point le plus lointain vient du modèle de masse sphérique.
- Pas fait : 50 galaxies sans déplacement mesuré dans le ciel et 9 trop incertaines restent en place (ou suivent Andromède) ; la galaxie du Triangle suit Andromède sans orbite propre ; aucune galaxie ne tourne sur elle-même, sauf la Voie lactée et Andromède.
- Trois fiches portaient les données d'une autre galaxie (Petite Ourse, Sextant, Andromeda VI) : nom et vitesse corrigés par `LGX_FIX`, masse et métallicité retirées faute de valeur vérifiée.

## Rotation des galaxies (ajout du 11 novembre 2026)

- Les quatre galaxies à disque du Groupe local tournent : Voie lactée et Andromède (déjà en place), Triangle et Grand Nuage de Magellan (`LG_SPIN` dans `30_gen.js`, rotation autour de l'axe de chaque galaxie dans le shader par `uAx`).
- Vitesses : Triangle, 100 km/s à 4 kpc puis 120 à 130 km/s (Corbelli et al. 2014) ; Grand Nuage, 91,7 ± 18,8 km/s (van der Marel et Kallivayalil 2014). Axes : Andrae et Jahnke 2011.
- Contrôle du sens : le Triangle et le Grand Nuage tournent dans le sens des aiguilles d'une montre vus de la Terre, Andromède dans l'autre sens (van der Marel et al. 2019 ; van der Marel et Sahlmann 2016). Le modèle donne ces trois sens. Attention : le vecteur publié par Andrae et Jahnke pour Andromède est de signe opposé à la mesure de Gaia ; il n'est pas utilisé.
- Le Triangle a maintenant sa propre orbite, d'après son déplacement mesuré (van der Marel et al. 2019) : passage à 117 kpc d'Andromède dans 1 milliard d'années, puis éloignement. Le freinage par la matière noire n'est pas calculé : l'éloignement est probablement exagéré.
- Pas fait : la rotation des 943 galaxies photographiées (affichées seulement à ±20 millions d'années) et celle des galaxies montrées comme des points. Dans le catalogue des galaxies proches, 603 sur 869 ont une vitesse de rotation mesurée ; leur sens de rotation n'est dans aucun catalogue et devrait être tiré de l'enroulement des bras sur les photos.
- Le dessin des bras du Triangle reste un schéma : il tourne d'un bloc, comme celui d'Andromède.

## Dettes connues
- Tout est chargé d'un bloc. C'est l'objet de la mission 1.
- `pipeline/` n'est pas rejouable d'un seul geste.
- Les étoiles Gaia sans nom ne sont pas reliées aux exoplanètes.
- Les étoiles d'avant-plan restent collées sur les galaxies reconstruites.
- Certaines photos de galaxies ont des défauts d'image.

## Suite
- Mission 1 : la page sur Firebase, chargée par zone, avec les données actuelles. Détail dans `docs/mission-lot1.md`.
- Mission 2 : 100 puis 500 millions d'étoiles, une vingtaine de millions de galaxies, tous les astéroïdes. Les gros traitements devront tourner dans le nuage, par lots.
- Mission 3 : toutes les étoiles Gaia ayant une distance estimée, 10 000 photos de galaxies en haute définition, surfaces plus fines.

## Orbites des étoiles calculées pas à pas (S2, 11 novembre 2026)
- `app/src/26_orbits.js` : les 58 967 étoiles du catalogue principal et le Soleil sont intégrés pas à pas (vitesse de Verlet, pas de 1 Ma, sous-pas fixes pour les orbites qui plongent vers le bulbe) dans le modèle de Voie lactée de `20_physics.js` (bulbe de Hernquist, disque de Miyamoto-Nagai, halo NFW ; sans barre ni bras ; paramètres inspirés de MWPotential2014, Bovy 2015, recalés sur 230 km/s). Le calcul tourne dans un Web Worker ; points de contrôle tous les 100 Ma.
- Au-delà de 3 Ma, chaque étoile prend sa position calculée si le dernier résultat est à moins de 6 Ma de l'instant affiché (prolongement x + v·d + a·d²/2 : écart vu du Soleil de 26 pc pour 99 % des étoiles à 5,9 Ma). Sinon, et en attendant le calcul : épicycles, comme avant ; la fiche dit « calcul en cours ». Bascule avec écart (retour au calcul sous 3 Ma) pour éviter le scintillement.
- Le Soleil dans la galaxie (`sunGalAt`, vue d'ensemble, rencontre avec Andromède) est calculé dans la page même, à toute date, sans attendre.
- Les étoiles Gaia en flux gardent les épicycles ; leur fiche dit « orbite approchée ». Matière noire retirée : épicycles partout (le temps affiché n'y est plus le temps réel).
- Mesuré : épicycles contre calcul pas à pas, écart médian 150 pc à 50 Ma, 2,3 kpc à 1 Ga (`app/test/orbits_measure.js`). Tour du Soleil : 229 Ma (rayon guide 8,67 kpc). Énergie conservée à 0,01 % pour 99,9 % des étoiles sur 1 Ga. Tests : `app/test/orbits.test.js`.
- Pas vérifié : comparaison avec un logiciel de référence (galpy) ; fluidité sur téléphone (rendu logiciel seulement) ; le saut visible (environ 250 pc à +200 Ma) quand le calcul remplace l'approximation après un saut dans le temps.

## Couleur des galaxies lointaines (S3, 11 novembre 2026)
- Avant : les galaxies des relevés passaient du blanc bleuté à l'orange selon z par une rampe choisie à la main ; les quasars avaient une couleur fixe.
- Après : `pipeline/build_zcol.py` décale un vrai spectre au repos de (1+z) et l'intègre sur l'œil CIE 1931 : galaxies, modèle Sb de l'atlas Kinney-Calzetti (Kinney et al. 1996) ; quasars, première composante principale du modèle SDSS spDR2-029 (positive partout : la forme moyenne). Table `DATA.ZCOL` (`app/gen/data16.js`), lue par le shader `surv` (`zcol`) pour les galaxies embarquées et en flux. Fiche : ligne « Couleur ».
- Supposé, et dit dans la fiche : toutes les galaxies ont le spectre d'une spirale Sb (leur type n'est pas dans nos catalogues). Au-delà de z = 2,07 (galaxies) et 4,35 (quasars), le spectre manque dans le visible : couleur du bord.
- Pas appliqué : l'assombrissement de Tolman, (1+z)⁻⁴, ne concerne que les objets résolus ; les galaxies des relevés sont des points de taille fixe, et les galaxies photographiées sont à z < 0,03 (moins de 12 %). Pas pris en compte : l'absorption par le gaz intergalactique devant les quasars lointains (forêt Lyman-α) au-delà de ce que contient le spectre moyen [À vérifier].
- Incertain : vers z = 2, la couleur (rose-lavande) vient de la partie ultraviolette du modèle Sb, mesurée par IUE avec une grande incertitude [À vérifier].
- Tests : `app/test/zcol.test.js` (Hα et Lyα à leur longueur d'onde, vert des quasars vers z = 3,3, rougissement des galaxies, recherche du shader).

## Lumière déviée par les trous noirs (S6, 11 novembre 2026)
- `app/src/27_lens.js` : pour un trou noir sans rotation (Schwarzschild), chaque rayon de vue est suivi à rebours jusqu'à l'infini (équation de l'orbite des photons, intégrée numériquement). Table de 512 angles, espacés en log(ψ − ψc) (dense près du bord de l'ombre à toute distance), recalculée quand la distance change ; bord de l'ombre exact (b = √27 M), passé au shader.
- `40_render.js` (`R.lensUpdate`, passe finale `lensed`) : actif à moins de 10⁷ GM/c² de Sagittarius A* (4,3 millions de masses solaires, valeur de la page) ou de M87* (6,5 milliards, EHT 2019) ; au-delà, la déviation fait moins d'un pixel. Source dans l'image : l'image elle-même ; source hors de l'image : vue tout autour (cube 128 ou 256 pixels) sous 3000 GM/c² seulement, refaite quand la caméra ou l'échelle bougent, deux fois par seconde au plus quand la date défile. Sous 3,1 GM/c² : image coupée (hors du domaine du calcul).
- Dit à l'écran (ligne de provenance) et dans les fiches : calculée, sans rotation (non mesurée sûrement), sans disque (l'anneau de l'image EHT est la lumière du disque, absent ici), noms non déviés.
- Tests : `app/test/lens.test.js` (trajet droit sans masse ; champ faible conforme au développement publié au second ordre ; champ fort conforme à Bozza 2002 ; ombre trouvée par les rayons ; M87* avec la masse dynamique de Gebhardt 2011 : 40,3 microsecondes d'arc, anneau EHT 42 ± 3 ; table lue à mieux que 0,1 % ; direction de la source, y compris l'image venant de l'autre côté).
- Pas vérifié : la convention d'orientation du cube (uFlip) au-delà de l'essai visuel ; fluidité sur téléphone ; WebGL1 : lentille absente (non dit).

## Poussière mesurée en 3D (S5, 11 novembre 2026)
- Source : carte 3D d'Edenhofer et al. 2024 (A&A 685, A82), moyenne, jusqu'à 1,25 kpc ; fichier de 3,25 Go non versé (Zenodo 10.5281/zenodo.10658339), réduit par `pipeline/build_dust.py` (numpy, astropy, astropy-healpix) en `app/gen/data20.js` : 160 × 160 × 52 cases de 15,6 pc (coupée à 406 pc du plan), densité dA_V/ds codée en log sur un octet (1,8 Mo). Conversion de l'article : A_V = 2,8 × unité ZGR23. Bulle intérieure (< 68,8 pc) : moyenne intégrée publiée, que les auteurs jugent douteuse (annexe C ; effet ≈ 0,02 mag).
- `28_dust.js` : niveaux de finesse (cases de 15,6 à 125 pc, moyennes exactes), atlas pour la carte graphique (format rouge en WebGL2 : three 0.149 refuse LUMINANCE), et intégrale d'un trajet sur 64 points au niveau dont la case vaut le pas. Caméra-étoile et Soleil-étoile partagent la même grille ancrée sur l'étoile (`dustPair`) : pas de saut quand la caméra rejoint le Soleil. Le même code produit le GLSL du shader des étoiles (`dustGlsl`).
- Page : l'éclat mesuré depuis la Terre contient déjà la poussière Soleil-étoile ; le shader la remplace par la poussière caméra-étoile (A_V pour les magnitudes V, A_G = 0,79 A_V pour Gaia), rougissement Cardelli et al. 1989 (A_R/A_V = 0,748, A_B/A_V = 1,324). Actif entre 3 et 60 000 années-lumière du Soleil. Fiche : « Poussière devant elle » en « N fois moins lumineuse ». Ligne de provenance : « Étoiles assombries par la poussière mesurée ».
- Vérifié (`app/test/dust.test.js`) : Taureau au plus dense à 148 pc (126–165, Zucker 2019, Galli 2019), Orion A à 422 pc (390–470, Großschedl 2018), pôles A_V ≈ 0,04 mag ; 1000 trajets au hasard contre une intégration au pas de 1 pc : médiane 0,014 mag, 99 % sous 0,5 mag (limite assumée de 64 points) ; allumage à 3 années-lumière : saut sous 0,13 mag pour 99 % des étoiles. À l'écran (`app/test/dust_screen.py`) : vu de 790 années-lumière, 9 étoiles sur 10 placées derrière un nuage sont plus faibles avec la poussière, sans erreur WebGL.
- Coût : 2 × 66 lectures de texture par étoile ; en rendu logiciel, images/s de 11–20 à 9–10 avec la poussière (59 000 étoiles). Étoiles Gaia en flux : non mesuré (millions de points, à surveiller sur téléphone).
- Pas fait : les nuages eux-mêmes ne brillent pas (pas de lumière diffusée ni d'émission) ; fond (Voie lactée en points, panorama) non assombri ; au-delà de 1,25 kpc ou de 406 pc du plan : poussière inconnue ici.
