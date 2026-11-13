# Audit physique de l'appli PC, échelle par échelle (13 novembre 2026)

Demande de Marc (13/11) : « le plus proche possible de la réalité », modèles physiques compris, ne jamais rien négliger,
énergie noire comprise. Puis deux critères ajoutés : **aucune cassure quand le temps démarre** (tout part d'un état
cohérent, qui avait déjà une direction avant qu'on appuie sur « lecture ») et **la masse et l'énergie se conservent**
quand des objets échangent de la matière.

Code lu : branche `appli-pc` au commit `e20b55a` (appli native, `natif/` et `pipeline/`). La page web n'est pas auditée.
Labels : [Certain] lu dans le code ou calculé ; [Probable] ordre de grandeur publié ou estimé ; [À vérifier] non mesuré.
Les chiffres « à l'écran » sont des ordres de grandeur, calculés le 13/11 (script dans la section 9).

## 1. La règle proposée

« Ne rien négliger » au pied de la lettre est impossible : il faudrait suivre chaque atome. La règle proposée est mesurable :

> **Un effet est inclus s'il déplace ou change quelque chose de plus d'un pixel, dans la vue la plus serrée où l'on
> regarde cet objet, à une date que l'appli permet d'afficher. Il est écarté seulement s'il reste aussi sous le tiers de
> l'incertitude qui existe déjà à cette date (mesure ou chaos). Exception : un effet qui change l'issue (fusion ou non,
> collision, éjection, amas qui tient ou se défait) est toujours inclus. L'énergie noire est toujours incluse.**

Chaque effet écarté reste listé ici, chiffré. Repères de taille : au champ normal (60°), un pixel vaut 100″ ; au champ le
plus serré (0,5°, Ctrl + molette), 0,8″. Un effet de 1″ est donc visible quand on resserre le champ. [Certain]

## 2. Tableau des manques, par impact

| # | Manque | Échelle | Ce qu'on voit de faux, ordre de grandeur | Code |
|---|---|---|---|---|
| 1 | Galaxies lointaines placées à leur distance d'aujourd'hui, pas là où était leur lumière | Cosmologie | À z = 1, distance doublée (3 400 Mpc au lieu de 1 700) ; à z = 3, quadruplée. La page web a ce mode, pas l'appli. [Certain] | `galaxies.h:151` |
| 2 | Toutes les galaxies grossissent avec l'expansion, y compris les amas liés | Grandes structures | Dans 10 Ga, a = 1,87 : l'amas de Coma paraît 1,9 fois plus grand, alors qu'un amas lié ne grandit pas. [Certain] | `galaxies.h:151`, `fenetre.cpp:546` |
| 3 | Les étoiles ne s'attirent pas entre elles : étoiles doubles et amas se défont dès qu'on lance le temps | Étoiles proches | Alpha du Centaure A et B partent en ligne droite au lieu de tourner (période 80 ans, écart 2 à 22″). Un amas comme les Pléiades s'étale de 1 pc par Ma par km/s d'erreur de vitesse : défait en quelques Ma au lieu d'environ 100. C'est le cas de Marc : « pas possible que pile au moment où je mets play ça se désagrège ». [Certain] code, [Probable] chiffres | `orbites_pas.comp:5` |
| 4 | Étoiles Gaia sans vitesse radiale : mise à zéro | Étoiles proches | Environ deux tiers des 98 M étoiles de `gaia.bin` [Probable : Gaia DR3 donne 33 M vitesses radiales]. Erreur typique 20 à 40 km/s, soit 20 à 40 pc par Ma. Le drapeau « orbite fiable » le dit, mais l'étoile bouge quand même mal. [Certain] code | `gaia_convertir.py:203` |
| 5 | Astéroïdes et comètes : Kepler pur, sans les planètes, sans force non gravitationnelle | Système solaire | Ceinture principale : écart d'environ 1° en 10 ans, 10° par siècle [Probable]. Comètes proches de Jupiter et géocroiseurs (Apophis 2029) : orbite fausse après la rencontre. Halley : environ 4 jours d'écart par tour sans les jets de gaz [Probable]. La page web faisait mieux (astéroïde touché tiré par les planètes). | `asteroides.vert:2`, `asteroides_catalogue.h` |
| 6 | Orientation de la Terre : pôle et rotation linéaires (UAI), sans ΔT ni précession au long cours | Système solaire | Aujourd'hui : 69 s de ΔT, carte décalée de 0,3° (32 km à l'équateur). En −500 : 72°. Dans 13 000 ans le pôle doit viser Véga ; la formule linéaire part dans le décor (axe de 14° faux par millier d'années). Pas d'oscillation de l'inclinaison (22 à 24,5° sur 41 000 ans). [Certain] code, [Probable] chiffres | `orientation.h:30` |
| 7 | Perte de masse du Soleil (lumière et vent, environ 10⁻¹³ par an) | Système solaire | Les planètes s'éloignent et ralentissent. Terre : 0,4° de retard sur son orbite à 100 000 ans, 36° à 1 Ma ; Mercure : 150° à 1 Ma. Le taux est connu à ± 70 % près : au-delà de ~300 000 ans, la place de la Terre sur son orbite devient incertaine, et l'écran devrait le dire. [Probable] | absent de `nbody_noyau.h` |
| 8 | Énergie noire absente du calcul de la rencontre avec Andromède | Groupe local | 7 à 14 % de la force Voie lactée–Andromède à 770 kpc selon la masse. **Fil « Voie lactée et énergie noire » : ne pas refaire ici.** [Certain] code | `calcul.py`, `groupe_local_clones.py` |
| 9 | Voie lactée des orbites d'étoiles : sans bras spiraux, sans nuages moléculaires, sans Grand Nuage ni Sagittaire | Voie lactée | Migration radiale due aux bras : 1 à 3 kpc par Ga ; échauffement par les nuages : quelques km/s par Ga ; le Grand Nuage décale le centre de la Voie lactée de dizaines de km/s pour le halo lointain [Probable]. Déjà dominé par l'incertitude du modèle (1,6 kpc à 100 Ma, mesuré par `essai_epicycles`). | `galaxie_orbites.h:9` |
| 10 | Vitesses propres des galaxies (hors expansion) absentes, et galaxies étirées vers nous | Grandes structures | Vers l'amas de la Vierge : 200 à 300 km/s ignorés. Les amas apparaissent étirés de ~10 Mpc le long de la ligne de visée (« doigts de Dieu ») : ils ne le sont pas. Les 55 637 distances Cosmicflows-4 corrigent une partie. [Probable] | `galaxies.h:2` |
| 11 | Gaz, formation d'étoiles, trou noir central, rétroaction : absents de la fusion | Groupe local | Le reste de la fusion est juste en gros (forme d'elliptique), mais il manque la flambée d'étoiles bleues, les queues de gaz, l'activité du trou noir. Le gaz pèse ~10 à 15 % des disques. [Probable] | `modeles.py` (disque, bulbe, halo seulement) |
| 12 | Nuage d'Oort absent de l'appli PC (il existait dans la page web) | Système solaire | Rien à l'écran. Jamais observé : seul un modèle peut le montrer, avec les étoiles de passage et la marée galactique. [Certain] | aucun |
| 13 | Planètes et lumière : temps de trajet et aberration non appliqués quand on regarde depuis la Terre | Système solaire | Jupiter : ~11″ ; Mars au plus près : ~16″ ; aberration annuelle : 20″. Invisible au champ normal, 13 à 25 pixels au champ serré. [Certain] code | aucun |
| 14 | Dérive des continents et paysages anciens | Système solaire | Carte d'aujourd'hui à toute date : 1 000 à 5 000 km d'écart à 100 Ma. [Probable] | `spheres.h` |
| 15 | Avenir lointain des galaxies : rougissement et affaiblissement | Cosmologie | Dans 10 Ga, les galaxies lointaines devraient être plus rouges et plus pâles qu'aujourd'hui ; elles gardent leur éclat. [À vérifier : pas trouvé de réglage d'éclat avec a(t)] | `galaxies.h` |
| 16 | Neutrinos sans masse dans la cosmologie | Cosmologie | Somme minimale 0,06 eV : ~0,1 à 0,3 % sur les distances. Sous la règle (sous l'incertitude de H0). [Probable] | `cosmologie.h:4` |
| 17 | Aplatissement du Soleil (J2), effet Lense-Thirring | Système solaire | Périhélie de Mercure : 0,03″ par siècle ; ~0,03° de position à 1 Ma. Sous la règle. [Probable] | absent |
| 18 | Pression de radiation, effet Yarkovsky | Système solaire | Yarkovsky : dérive de 10 à 1 000 km par an pour les petits astéroïdes (Bennu : 280 m/an en demi-grand axe), décisif pour un impact futur, sous le pixel à l'échelle du système. À inclure seulement avec le point 5. [Probable] | absent |
| 19 | Étoiles qui frôlent le Soleil, effet sur les planètes | Système solaire | Change la route de la Terre au-delà de ~50 Ma (Kaib et Raymond 2024) ; déjà au-delà de la table de ±10 Ma. Sous la règle tant que la table reste à ±10 Ma. [Probable] | absent |

## 3. Ce qui est déjà pris en compte

| Effet | Où | Qualité |
|---|---|---|
| Relativité générale du Soleil (précession de Mercure, 43″ par siècle) | `natif/physique/nbody_noyau.h:122` | Premier ordre post-newtonien. [Certain] |
| Gravité mutuelle : 8 planètes, Pluton, Cérès, Vesta, Pallas, Hygie | `nbody_noyau.h:4` | Wisdom-Holman, pas de 4 jours, calé sur DE440. [Certain] |
| Lune moyennée en anneau autour de la Terre | `nbody_noyau.h:139` | Quinn et al. 1991. [Certain] |
| Éphémérides de la NASA (DE440) de 1550 à 2650, lunes (fichiers NAIF) | `ephemeride.h` | Au mètre près. [Certain] |
| Lune hors DE440 : théorie de Meeus, ±4 000 ans, accélération de marée incluse dans ses termes | `natif/physique/lune.h:4` | Au-delà : cachée. [Probable] |
| Chaos du système solaire (32 copies) | `natif/src/chaos.h` | Incertitude montrée. [Certain] |
| Orbites des étoiles dans la Galaxie, avec barre tournante | `galaxie_orbites.h`, `orbites_pas.comp` | Bulbe + disque + halo + barre (39 km/s/kpc). [Certain] |
| Freinage par la matière noire (frottement dynamique) | `calcul.py` (halos vivants) ; `groupe_local_clones.py:98` (Chandrasekhar) | [Certain] |
| Incertitude de la rencontre (10 000 scénarios) | `clones.h`, `groupe_local_clones.py` | Wu et al. 2026 : 90 % de fusion. [Certain] |
| Expansion : matière, rayonnement, courbure, énergie noire (w0, wa réglables) | `natif/src/cosmologie.h` | Identique à astropy. [Certain] |
| Poussière, couleurs, lentilles des trous noirs, vie des étoiles | autres fils | Hors de cet audit. |

## 4. Critère de Marc n° 1 : aucune cassure quand le temps démarre

| Échelle | Ce qui se passe à t = 0 ou à une frontière | Verdict |
|---|---|---|
| Planètes | DE440 couvre aujourd'hui. Aux bornes 1550 et 2650, le calcul part de l'état exact de la NASA (`systeme_solaire.cpp:40`) : pas de saut de position. [Certain] | Bon |
| Planètes, à ±`ansDirects` | Le calcul direct cède la place à la table longue, partie d'un autre état (10/11/2026) : un saut est probable, de taille non mesurée (`systeme_solaire.cpp:166`). [À vérifier] | À mesurer |
| Lune | Saut DE440 → Meeus en 1550 et 2650 (erreur de Meeus : quelques secondes d'arc, soit des dizaines de km) ; disparition au-delà de ±4 000 ans. Autres lunes : disparaissent hors de leurs fichiers (`simulation.h:472`). [Probable] | Cassure |
| Étoiles | Ligne droite mesurée puis orbite, raccord sans seuil (`orbite_galactique.h`). [Certain] Mais : vitesses radiales mises à zéro (point 4) et pas d'attraction entre étoiles (point 3) : doubles et amas se défont dès le départ. | **Cassure physique** |
| Voie lactée | Le modèle de galaxie n'entre qu'entre 200 et 400 Ma. **Fil « Voie lactée » : ne pas refaire.** | Traité ailleurs |
| Rencontre avec Andromède | Chaque galaxie du calcul est à l'équilibre seule (AGAMA), puis posée près des autres : pas d'état cohérent commun. Le disque modèle forme une barre et le Soleil-témoin migre vers le centre (`groupe_local.h:10`) : ce disque n'est pas notre Voie lactée. Relais étoiles mesurées → particules au premier passage (`simulation.h:566`) : des étoiles s'effacent, d'autres apparaissent. [Certain] | Cassure, en partie traitée par le fil Voie lactée |
| Nuage des scénarios (Grand Nuage) | Point recollé au centre en une image à l'absorption. **Fil Voie lactée.** | Traité ailleurs |
| Galaxies lointaines | Seule l'expansion les fait bouger : à t = 0 leur vraie vitesse (vers la Vierge, le Grand Attracteur) n'existe pas (point 10). [Certain] | Direction fausse au départ |

Règle proposée pour la suite : **chaque objet a, à t = 0, sa position ET sa vitesse (mesurées, sinon tirées d'un modèle
et dites « modèle »), et un seul calcul le fait évoluer de part et d'autre**. Pas de relais d'un calcul à un autre
sans raccord mesuré (écart affiché < 1 pixel), et pas d'objet qui apparaît ou disparaît sauf s'il naît ou meurt
réellement.

## 5. Critère de Marc n° 2 : masse et énergie conservées

| Calcul | Masse | Énergie | Verdict |
|---|---|---|---|
| Système solaire (N corps) | Constante, alors que le Soleil perd 10⁻¹³ par an (point 7) | Conservée (schéma symplectique) | Masse fausse au long cours |
| Rencontre avec Andromède (particules) | Exacte (chaque particule garde sa masse : ce qui quitte le Grand Nuage s'ajoute bien à la Voie lactée) | Dérive 0,11 % sur 10 Ga (R9) | Bon, sans énergie noire (point 8) |
| Scénarios du Groupe local | Exacte à la fusion : la masse absorbée s'ajoute (`groupe_local_clones.py:154`), quantité de mouvement conservée | Perdue en chaleur interne à la fusion et par le freinage, comme dans la réalité | Bon dans le calcul ; **l'écran ne montre pas la galaxie qui grossit** |
| Étoiles qui meurent | Gaz rendu à la galaxie non suivi (30 à 40 % de la masse des étoiles en 10 Ga) | — | Fil « vie des étoiles » ; effet faible sur le mouvement (halo dominant) [Probable] |
| Galaxies lointaines | Aucun échange (pas de fusions futures entre galaxies) | — | Manque (point 2) |

## 6. Priorités proposées (rien n'est codé avant l'accord de Marc)

1. **Étoiles qui s'attirent localement** : doubles en orbite (catalogue ORB6, déjà sur le PC), amas tenus par leur propre
   gravité, vitesses radiales manquantes tirées de la dispersion locale (dit « modèle »). Règle les points 3 et 4 et le
   critère n° 1 pour les étoiles. Le plus visible pour Marc.
2. **Galaxies lointaines** : mode « là où était la lumière » (comme la page), amas liés qui ne grandissent pas, vitesses
   propres tirées du champ Cosmicflows-4. Points 1, 2, 10.
3. **Astéroïdes et comètes tirés par les planètes** (calcul à l'avance par décennie, sur la carte graphique), forces non
   gravitationnelles des comètes publiées par le JPL. Point 5.
4. **Terre** : ΔT mesuré puis modèle, précession et inclinaison au long cours (Laskar), continents anciens (cartes
   publiées), perte de masse du Soleil dans le calcul avec son incertitude. Points 6, 7, 14.
5. Temps de trajet de la lumière et aberration en vue depuis la Terre ; nuage d'Oort modèle ; gaz dans la fusion. Points
   11 à 13.

Mesurer d'abord (sans rien changer) : le saut table longue / calcul direct des planètes, et le saut DE440 → Meeus.

## 7. Laissés aux autres fils

- Énergie noire dans la rencontre et cohérence de la Voie lactée à t = 0, Grand Nuage : fil « Voie lactée et énergie
  noire dans la rencontre ».
- Vie et perte de masse des étoiles, lentilles : fil « étoiles qui vieillissent et lumière déviée ».

## 8. Limites de cet audit

Lecture du code et calculs d'ordre de grandeur ; aucun essai lancé dans l'appli. Les chiffres [Probable] viennent de
valeurs publiées connues, pas d'une nouvelle mesure.

## 9. Calculs

Pixels : champ × 3 600 / 2 160 lignes. Perte de masse : n ∝ M², donc Δλ = ½ × 2 × 10⁻¹³ × n × t². ΔT : formule de
Morrison et Stephenson. Distances cosmologiques : ΛCDM (H0 67,4, Ωm 0,315). a(+10 Ga) par intégration de da/dt = a H(a).
Énergie noire : a_Λ = ΩΛ H0² r contre G M / r², M = 2,3 à 4,5 × 10¹² M☉.
