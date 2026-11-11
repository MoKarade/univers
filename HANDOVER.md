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

## Lumière déviée par les trous noirs (S6, 11 novembre 2026)
- `app/src/27_lens.js` : pour un trou noir sans rotation (Schwarzschild), chaque rayon de vue est suivi à rebours jusqu'à l'infini (équation de l'orbite des photons, intégrée numériquement) ; table de 512 angles recalculée quand la distance change.
- `40_render.js` (`R.lensUpdate`, passe finale) : quand la caméra est à moins de 3000 GM/c² de Sagittarius A* (4,3 millions de masses solaires, valeur de la page) ou de M87* (6,5 milliards, EHT 2019), chaque pixel prend la lumière venant de sa direction déviée : ombre, anneau de photons, images doubles. Source dans l'image : l'image elle-même ; source hors de l'image : une vue tout autour (cube 128 ou 256 pixels, refaite quand la caméra, l'échelle ou la date bougent), moins fine.
- Tests : `app/test/lens.test.js` (trajet droit sans masse ; déviation en champ faible conforme au développement publié jusqu'au second ordre ; ombre à b = √27 M ; M87* : 39,7 microsecondes d'arc, anneau EHT 42 ± 3). À l'écran (rendu logiciel) : ombre vue de 60 M de 85 pixels de rayon pour 82 calculés.
- Supposé et dit dans les fiches : pas de rotation (non mesurée de façon sûre). Pas de disque d'accrétion (aucun n'est dessiné dans la page). Les étiquettes et repères restent à leur position non déviée.
- Coût : une passe finale plus lourde, et six rendus de plus quand la vue tout autour doit être refaite. Fluidité sur téléphone non mesurée.
