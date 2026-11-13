# Revue détaillée de l'appli PC : ce qu'elle propose, ce qui manque, ce qui est mal fait (13 novembre 2026)

Demande de Marc : « va beaucoup plus dans le détail, valide ce qui manque, ce qui est mal fait, analyse l'appli, voir
ce qu'elle propose ». Ce document complète `docs/analyse-architecture.md` (la cause commune et le plan).

Méthode : quatre revues de code indépendantes, en lecture seule (système solaire ; étoiles ; galaxies et rencontre ;
interface, temps et tests), sur `appli-pc` au commit `e20b55a`, puis vérification par moi des constats graves
(section 8). Gravité : **grave** (faux visible ou trompeur), **moyen**, **mineur**. Chaque constat donne le fichier et
la ligne (`sim` = `natif/src/simulation.h`, `fen` = `natif/src/fenetre.cpp`, `i_x` = `natif/src/interface_x.h`).
Limite : lecture du code ; ce qui n'a pas été vu à l'écran est dit en section 9.

## 1. Ce que l'appli propose aujourd'hui

| Élément | Ce qu'il fait | État |
|---|---|---|
| Recherche | noms sans accents, 10 astres + 6 astéroïdes ou comètes | marche ; ne cherche que ce qui est visible à la date (« Lune » en l'an 9000 : « aucun astre ») |
| Menu « Aller à » | 5 échelles (45 UA, 30 al, 300 al, 5 millions d'al, 5 milliards d'al), planètes, lunes, étoiles et galaxies nommées, sondes, 6 éclipses, visite guidée | marche ; **aucune échelle « Voie lactée »** entre 300 al et 5 millions d'al ; éclipses écrites en dur jusqu'en 2028 |
| Barre du temps | date, lecture, 10 vitesses, sens, « Maintenant », aller à une date | partiel (section 6) |
| Plage de dates | de −1 milliard d'années à la fin du calcul de la rencontre (+10 Ga) | asymétrique ; la page web allait du Big Bang à +100 Ga |
| Zoom | de 1,25 rayon d'une planète à 90 milliards d'al | marche ; une étoile reste un point même à 1 900 km |
| Champ (Ctrl + molette) | 60° à 0,5° | marche ; absent de l'aide |
| Fiche d'astre | lignes avec statut et sources | marche |
| Vue « 100 % mesuré » / « meilleur rendu » | n'agit que sur les étoiles Gaia | portée étroite |
| Ciel par longueurs d'onde | 25 cartes mesurées + tuiles fines | marche près du Soleil ; **la carte d'aujourd'hui reste affichée à +3 Ga** (fen:606) |
| Ondes gravitationnelles | tableau | marche, sans point dans l'espace |
| Complétude par échelle | pourcentage au coin | **chiffre trompeur** (section 6) |
| « Comment c'est obtenu » | tableau par famille | caché par défaut |
| Calculs de fond | barres d'avancement | marche |
| Cosmologie réglable | 5 curseurs | marche |

Ce qui existe en données : Soleil, 8 planètes, Pluton, 437 lunes, 1,58 million d'astéroïdes, 1 778 comètes, sondes ;
58 967 étoiles nommées, 98 M + 94 M d'étoiles Gaia en 3D, 1,6 milliard de sources sans distance ; 113 galaxies du
Groupe local, 55 637 galaxies à distance mesurée, 18,3 millions de galaxies et quasars en points.

**Perdu par rapport à la page web** : Big Bang et avenir lointain, frise et ~190 événements, exoplanètes (6 436),
trous noirs et lumière déviée, pulsars et amas, **photos et formes des galaxies (943)**, poussière 3D, infiniment
petit, vue « là où la lumière est partie », nuage d'Oort, étoiles frôleuses, orbites des naines dans le passé,
rotation des galaxies, vie du Soleil, 10 des 11 survols. Certains sont en cours sur des branches non installées
(vie des étoiles, lentilles).

## 2. Ce qui se voit, et où ça casse

### Selon la date

| Écart à aujourd'hui | Ce qui change | Où |
|---|---|---|
| hors 1550-2650 | planètes calculées ; lunes (sauf la Lune, −2000 à +6000) et tracés d'orbites cachés ; **les points des planètes ne seraient plus dessinés** | sim:463-505, points_planetes.h:28 |
| ±300 ans | astéroïdes et comètes coupés net | sim:790 |
| ~3 Ma | lumière des étoiles Gaia sans vitesse sûre éteinte (dont les 94 M du second jeu) | gaia.h:50 |
| ±3 Ma, net | galaxies nommées : place mesurée → film de la rencontre ; celles hors du film disparaissent | sim:533, 613-620 |
| ±10 Ma | planètes cachées ; de +10 à +60 Ma, seule l'ellipse de la Terre | i_base:350 |
| 200 → 400 Ma | traceurs des bras effacés ; Voie lactée calculée allumée (futur seulement) | traceurs_bras.h:37, fen:561 |
| −0,8 → −1 Ga | étoiles mesurées effacées, **rien ne les remplace** | sim:541 |
| 4,3 → 4,6 Ga | étoiles mesurées effacées, points du film allumés ; Soleil invisible, caméra renvoyée au centre | sim:566-582, 807-816 |

### Selon la distance de la caméra

Seuils d'apparition : noms des planètes (0,05 al), éclat des étoiles ×1 à ×100 (30 à 300 al), coupure nette des
sources Gaia sans distance (100 al), traceurs des bras (1 000 à 10 000 al), points du film (3 160 à 31 600 al),
galaxies des relevés (31 600 al à 3 millions d'al), scénarios (100 000 à 500 000 al). Références : sim:779-796,
gaia.h:238, traceurs_bras.h:92, fen:559, clones.h:80.

## 3. Étoiles

**Ce qui est proposé.** Catalogue nommé (58 967, orbite exacte sur la carte graphique) ; Gaia A (98 M, orbite exacte,
dont 23,5 M « fiables » portant 67 % de la lumière) ; Gaia B (94 M, épicycles seulement) ; 3,2 M de cases de lumière
additionnée ; 1,6 milliard de sources en direction seule ; traceurs des bras.

| # | Gravité | Constat | Où |
|---|---|---|---|
| E1 | grave | Étoiles nommées sans vitesse radiale : avancent quand même jusqu'à ±1 Ga, à plein éclat. Le drapeau est calculé puis perdu à l'écriture. Une vitesse réellement nulle est prise pour une absence ; une vitesse > 500 km/s est remplacée par 0. | `etoiles_hyg.py:63,95,114`, `etoiles_hyg_appliquer.py:18` |
| E2 | grave | Gaia B : des étoiles peuvent être marquées « fiables » et suivre des épicycles jusqu'à 1 Ga (1,1 kpc d'écart médian à 100 Ma), recalées sur un Soleil différent de celui de Gaia A : deux repères dans la même image. | `gaia_convertir.py:177,209`, `gaia.h:151,203` |
| E3 | grave | En pause loin dans le temps, tourner la caméra fait entrer des paquets d'étoiles restés en épicycles à côté de paquets exacts (écart de l'ordre du kpc). | fen:470, `gaia_orbites.h:131` |
| E4 | moyen | Double comptage possible de la lumière entre Gaia B et les cases additionnées ; l'appli ne vérifie rien. | `gaia_agrege_convertir.py:88`, fen:260 |
| E5 | moyen | Amas déchirés : dans un même amas, les membres avec vitesse radiale la gardent, les autres ont 0 (Hyades : deux paquets qui s'écartent de ~40 pc par Ma). Étoiles doubles séparées. | `gaia_convertir.py:203` |
| E6 | moyen | Distance = 1 / parallaxe brute : pas de correction du point zéro, pas de filtre de qualité ; biais de 10 à 20 % pour Gaia B, qui fausse aussi l'éclat et la vitesse. | `gaia_convertir.py:191-202` |
| E7 | moyen | Poussière figée dans l'étoile : sombre et rouge vue de partout ; aucune poussière entre la caméra et l'étoile (la page web l'avait). | `gaia_convertir.py:8` |
| E8 | moyen | Magnitudes V et G mélangées sans conversion ; à éclat égal une étoile rouge envoie moins de lumière à l'écran. | `commun.h:101` |
| E9 | moyen | Éclat qui dépend de la caméra (×100, puis jusqu'à ×10 000 au champ serré) ; commentaire faux sur le retour à 1. | sim:772-831, fen:612 |
| E10 | moyen | En « meilleur rendu », la place des étoiles dépend de la caméra (flou de 3°), et pas de la même façon selon la méthode d'orbite. | `gaia_fiable.glsl:33`, `gaia.vert:41` |
| E11 | moyen | Coupures nettes : sources sans distance à 3 Ma (alors qu'il reste 37 % de leur lumière) et à 100 al ; tuiles sans transition. | `gaia.h:238`, `gaia_ciel.h:63` |
| E12 | mineur | Doublons entre catalogues pour les étoiles rapides (Barnard) ; vitesse écrêtée à 1 638 km/s ; Soleil à 6,6 pc du plan au lieu d'environ 20 ; matrice de repère recopiée 4 fois sans test ; valeurs inventées dans le catalogue nommé (couleur devinée, magnitude 10 par défaut). | `gaia_convertir.py:131,238`, `galaxie_orbites.h:35`, `etoiles_hyg.py:61,72` |

Sain : constantes identiques entre processeur et carte graphique (contrôlées), calcul de la carte à 0,008 pc du calcul
de référence, retour en arrière correct, raccord ligne droite/orbite sans défaut (moins de 1 pc d'écart).

Manque : vie des étoiles (en cours ailleurs), bras et nuages dans le potentiel, incertitude par étoile, vitesses
radiales d'autres relevés (APOGEE, GALAH, LAMOST) pour ~72 M d'étoiles, distances statistiques, poussière depuis la
caméra, binaires et amas liés, tout ce qui est au-delà de ~4 kpc.

## 4. Système solaire

**Ce qui est proposé.** Soleil, 8 planètes, Pluton, Lune lus dans les éphémérides de la NASA (1550-2650), puis calcul
à N corps (±20 000 ans), puis table (±10 Ma) ; Lune par la théorie de Meeus de −2000 à +6000 ; 437 lunes dans la plage
de leurs fichiers ; 1,58 M d'astéroïdes et comètes sur leur ellipse (±300 ans) ; 5 sondes ; 10 cartes de surface ;
anneaux de Saturne avec ombres ; éclipses (une ombre à la fois). Les 437 autres lunes sont de simples cercles sans
surface ni éclat ; Pluton est un point blanc.

| # | Gravité | Constat | Où |
|---|---|---|---|
| S1 | grave | Jusqu'à ±10 Ma l'écran montre une place précise de chaque planète, étiquetée « calculé exactement », alors que c'est une table interpolée (corrélation 0,74 avec la référence à 10 Ma) et sans incertitude. | fen:503, `nbody_noyau.h:171` |
| S2 | grave | Orientation des planètes : formules linéaires appliquées à toute date. À des millions d'années, l'axe de la Terre (et de Mars, Jupiter, Saturne, Mercure) pointe n'importe où. | `orientation.h:30`, `spheres.h:272` |
| S3 | grave | Lune annoncée sur ±4 000 ans, contrôlée seulement de 1600 à 2600 (tolérance ≈130 km à la borne). Les éclipses anciennes sont pourtant dessinées comme vraies. | `lune.h:20-31`, `essai_lune.cpp` |
| S4 | moyen | Fiche de la Lune hors éphémérides : « calculée ici, gravité mutuelle ». Faux : c'est une série de formules. | i_temps ~303, sim:480 |
| S5 | moyen | Cérès, Vesta, Pallas, Hygie : calculés avec la gravité des planètes, mais affichés sur leur ellipse simple. Le bon calcul n'est jamais montré. | `systeme_solaire.cpp:15` |
| S6 | moyen | Disparitions nettes : tracés d'orbites en 1550 et 2650, astéroïdes à ±300 ans, lunes à la borne de leur fichier (et la planète saute alors à son centre de masse : ~2 100 km pour Pluton). | i_base:350, sim:457, sim:790 |
| S7 | moyen | Calendrier grégorien appliqué avant 1582 : une éclipse historique s'affiche 5 à 10 jours à côté des catalogues. « Temps universel » avec un écart fixe de 69 s. | sim:35, 936 |
| S8 | moyen | Fiche astéroïde : précision affichée figée (« 100 000 km après 154 jours ») quelle que soit la date. | `asteroides_jpl.py:197` |
| S9 | moyen | Raccord calcul direct → table à ±20 000 ans : jamais mesuré. | `systeme_solaire.cpp:166` |
| S10 | mineur | Deux échelles de temps mélangées de part et d'autre de la borne des éphémérides (~2 000 km sur la Terre) ; trou de 69 s en 2650 où toutes les planètes sont invalides ; astéroïdes en simple précision (sauts de ~13 000 km à 300 ans) ; Lune au quartier ~3 fois trop brillante ; lecture des fichiers NASA qui prend le premier segment au lieu du dernier. | sim:423,477, `asteroides.vert:18`, `ephemeride.h:137` |

Audit précédent : ses sept affirmations sur cette échelle sont **confirmées** ; deux sont pires que décrites
(orientation : tous les astres et jusqu'à ±10 Ma ; saut de la Lune sous-estimé).

Sain : lecture des éphémérides au mètre ; N corps avec relativité à 1 à 5″ de la NASA ; orientations conformes au
fichier officiel ; sondes à 100 km ; 6 éclipses retrouvées.

Manque : surfaces et éclat des lunes (Io, Europe, Titan…), carte de Pluton, planètes aplaties, atmosphères et nuages,
Lune rouge en éclipse, anneaux d'Uranus et de Jupiter, queues des comètes, astéroïdes tirés par les planètes, autres
sondes (Cassini, Juno, JWST, ISS), libration de la Lune, planètes naines et ceinture de Kuiper, nuage d'Oort, Terre
avant −10 Ma.

## 5. Galaxies, Groupe local, rencontre avec Andromède, univers lointain

**Ce qui est proposé.** 18,3 millions de galaxies et quasars en points tous de même éclat (distance calculée d'après
le décalage vers le rouge, multipliée par l'expansion) ; ~55 800 galaxies nommées qui sont des **étiquettes sans forme
ni éclat** ; au-delà de ±3 Ma, seules Andromède, le Triangle, le Grand Nuage et 38 naines bougent, les autres sont
cachées ; dans le passé, toutes sont cachées. Le film de la rencontre : 4 galaxies en particules (300 000, puis 3 M),
une image tous les 20 Ma, ligne droite entre deux images. Les 10 000 scénarios : 4 masses ponctuelles.

| # | Gravité | Constat | Où |
|---|---|---|---|
| G1 | grave | **Disques instables dès le départ.** Le réglage d'agitation des étoiles donne un indice de stabilité (Q de Toomre) de 0,7 à 0,86 ; il faut plus de 1,5 pour un disque calme. C'est la cause de la barre violente entre 0,1 et 0,5 Ga. Recalculé par moi : 0,68 à deux longueurs d'échelle. | `modeles.py:58` |
| G2 | grave | **Voie lactée trop lourde au Soleil** : le halo est calé pour un autre disque que celui utilisé. Rotation ~253 km/s au lieu de 230, disque 68 M☉/pc² au lieu de 35 à 50. Le Soleil-témoin part 23 km/s trop lent : c'est pourquoi il tombe vers le centre. | `modeles.py:14-27,44` |
| G3 | grave | **Ligne droite entre images de 20 Ma.** Une étoile fait un tour en 73 Ma à 2,6 kpc et ~30 Ma à 1 kpc : entre deux images elle coupe par la corde. Le centre des galaxies « respire » toutes les 20 Ma ; sous 1,5 kpc le mouvement n'a pas de sens. Documenté nulle part. | `fusion_nuage.vert:22`, `groupe_local.h:66` |
| G4 | grave | **Halo du Grand Nuage non coupé** : 35 % de sa masse est déjà dans la Voie lactée à t = 0, 2,4 % tirée à plus de 1 Mpc. Le Nuage réel du calcul pèse ~8 × 10¹⁰ et non 1,8 × 10¹¹. | `modeles.py:41` |
| G5 | grave | **Galaxies naines** : points sans masse, dont plusieurs vitesses de départ sont du bruit de mesure (Sagittarius dIrr à 569 km/s). Elles filent hors du Groupe local sous l'étiquette « calcul complet ». | `calcul.py:78`, `conditions.json` |
| G6 | grave | Étiquette « Galaxies lointaines : positions mesurées » : la distance est calculée d'après un modèle. | fen:537 |
| G7 | moyen | Pas de vitesses propres : amas étirés vers nous ; décalage ramené au repère du Groupe local et non du fond cosmologique (jusqu'à ~9 Mpc d'erreur). | `galaxies_complet.py` |
| G8 | moyen | Cosmicflows-4 à H0 = 75 contre des points à H0 = 67,4 : une même galaxie a son étiquette et son point à 11 % d'écart, et seul le point bouge avec les curseurs. | `galaxies_cf4.py:12` |
| G9 | moyen | Expansion appliquée à tout, groupes liés compris ; pas de cône de lumière ; dans le passé, des objets à z = 7 restent affichés. | `galaxies.h:148`, fen:545 |
| G10 | moyen | Paramètres : Andromède à 785 kpc dans le film, 761 dans les scénarios ; Triangle à ~60 km/s de rotation au lieu de ~100 ; Grand Nuage incliné à 53° au lieu de 26 à 40° [À vérifier] ; disque et bulbe d'Andromède faux. | `calcul.py:66-74` |
| G11 | moyen | Particules de matière noire 6,5 fois plus lourdes que les étoiles : l'épaississement du disque est en partie un défaut numérique. | `calcul.py:66` |
| G12 | moyen | Boîte de ±819 kpc : une étoile éjectée vite reste collée sur une face avant 10 Ga [À vérifier sur les fichiers]. | `calcul.py:232` |
| G13 | moyen | Premier passage à 2,4 kpc, alors que les valeurs publiées sont vers 30 kpc : non expliqué [À vérifier]. | film |
| G14 | moyen | Moteur de gravité sur la carte : la quantité de mouvement n'est pas contrôlée ; une pile pleine abandonne des calculs sans le dire. | `gravite_gpu.py:138` |
| G15 | mineur | Curseurs de cosmologie qui permettent des univers impossibles ; textes et sources périmés ; scénarios arrêtés à 9,78 Ga, film à 10. | `cosmologie.h:57` |

**La branche en attente (`galaxie-entiere`).** L'énergie noire est juste (effet ~13 % avec ces masses). Le départ à
−2 Ga est la bonne idée, mais **incomplet** : frottement coupé au plus près du passage, forces non égales et opposées
(44 % d'écart), tir correctif qui lit un fichier que rien n'écrit, témoins remontés dans un autre potentiel que celui
du calcul. **Bloquant** : le lecteur de l'appli suppose que le film commence à t = 0 ; un film parti de −2 Ga serait
rejoué décalé de 2 Ga. Le compteur de masse liée a un défaut : la Voie lactée « se dissout » au premier passage et ne
se reforme jamais.

Sain : cosmologie identique à astropy ; scénarios qui reproduisent les publications ; arbre de gravité contrôlé contre
la somme exacte ; sens de rotation et inclinaison d'Andromède (77°) corrects.

Manque : gaz et naissance d'étoiles ; Petit Nuage, M32, NGC 205, Sagittaire comme vrais corps ; barre et bras au
départ ; catalogues de groupes et vitesses propres ; cône de lumière ; **éclat et taille propres des 18 M de points**
(les magnitudes existent dans les relevés) ; forme ou photo des galaxies nommées ; passé du Groupe local ; un scénario
« pas de fusion ».

## 6. Interface, temps, honnêteté de l'écran

| # | Gravité | Constat | Où |
|---|---|---|---|
| I1 | grave | Complétude trompeuse : « 99,6 % des sources de Gaia » devient à l'écran « Voie lactée : 99,6 % de ce qui est connu », alors que Gaia couvre environ 1 % des étoiles de la Galaxie. | i_bas:275, `completude.h:62` |
| I2 | grave | Passé lointain : l'écran dit que « le calcul de la rencontre prend le relais », alors que ce calcul ne couvre que le futur. Le ciel se vide. | i_temps:127, i_bas:65 |
| I3 | grave | « Mesuré » posé sur du calculé : éphémérides futures, trajectoires prévues des sondes, étoiles à vitesse radiale nulle, galaxies lointaines dont la distance est calculée. « Calculé exactement » pour un potentiel modèle à 1,6 kpc près à 100 Ma. | fen:503-537, i_methode:44 |
| I4 | grave | Hors 1550-2650, les planètes auraient un nom mais plus de point ni d'orbite, alors que le texte dit « calculées ici ». À confirmer à l'écran. | `points_planetes.h:28` |
| I5 | grave | Le temps est bridé par image : à « 200 Ma par seconde » on obtient environ 19 Ma par seconde (107 s mesurées pour 2 Ga). Le calcul des orbites continue même quand les étoiles sont invisibles : aller à +5 Ga fait attendre des minutes pour rien. | fen:459-499, `gaia_orbites.h:27` |
| I6 | moyen | Trous dans les vitesses : rien entre 100 000 ans et 10 Ma par seconde. | sim:88 |
| I7 | moyen | Pause pendant un rattrapage : la date continue d'avancer alors que l'écran dit « temps arrêté ». | fen:461 |
| I8 | moyen | Textes en dur « 800 millions / 1 milliard d'années » alors que le relais réel est vers 4,3 à 4,6 Ga. Accueil : « tout ce que tu vois est placé d'après des mesures réelles », faux dès que le temps bouge. | i_temps:127, i_bas:168 |
| I9 | moyen | Par défaut, presque tous les avertissements sont cachés (éclat ×100, « un scénario », astéroïdes grossis). | i_bas:114 |
| I10 | moyen | Fichiers manquants ignorés en silence (sauf les éphémérides) ; chemins écrits en dur ; Échap quitte sans confirmer. | sim:294-374, fen:50, i_base:62 |
| I11 | moyen | Code : une fonction de 670 lignes qui mêle chargement, temps, étiquettes et dessin ; code mort encore appelé ; constantes recopiées (une même conversion dans 8 fichiers et 6 shaders, « 3 Ma » 4 fois, « 30 000 ans » 5 fois). | fen:111-781 |
| I12 | mineur | Décalage de 2 000 ans dans le calcul du chaos ; dates lointaines écrites « An 1 000 002 026 » ; aide et notices périmées. | `chaos.h:25`, i_temps:95 |

## 7. Tests

- **Aucun essai de l'appli PC ne tourne automatiquement.** Le contrôle GitHub ne teste que l'ancienne page web. Tout est
  lancé à la main, sur le PC.
- Essais existants, solides pour leur pièce : éphémérides contre la NASA (au mètre), orientation, 6 éclipses,
  cosmologie contre astropy, sondes, orbites sur la carte contre le calcul de référence.
- Un « essai » ne peut pas échouer (`essai_epicycles` rend toujours 0).
- **Rien ne teste** : les passages entre couches, la bride du temps, les étiquettes contre l'état réel, les textes,
  le dessin des planètes hors éphémérides, le côté passé, les fichiers absents. La preuve « même date, même image »
  est une comparaison à l'œil de 9 captures.

## 8. Ce que j'ai vérifié moi-même

| Constat | Vérification | Verdict |
|---|---|---|
| I4 : planètes sans point hors 1550-2650 | `points_planetes.h:28` : le dessin s'arrête si les éphémérides ne couvrent pas la date | confirmé dans le code, à voir à l'écran |
| I1 : complétude tronquée | `interface_bas.h:275` coupe au premier « % » et ajoute « de ce qui est connu » | confirmé |
| Aucun essai natif automatique | `controles.yml` ne lance que les tests de la page web | confirmé |
| E1 : drapeau « sans vitesse radiale » perdu | `etoiles_hyg_appliquer.py:18` écrit 8 colonnes, sans le drapeau | confirmé |
| G1 : disques instables | recalcul à la main : Q = 0,68 à 5,2 kpc | confirmé [ordre de grandeur] |
| G3 : ligne droite sur 20 Ma | période de 73 Ma à 2,6 kpc ; au milieu d'un quart de tour, le rayon tombe à ~66 % | confirmé [calcul] |
| G8 : H0 = 75 pour Cosmicflows-4 | `galaxies_cf4.py:12` | confirmé |
| I2 : rien dans le passé | `groupe_local.h` : le film refuse toute date négative | confirmé |

## 9. Ce qui n'est pas vérifié

- **Rien n'a été vu à l'écran.** Les captures aux dates clés attendent la fin du calcul « Voie lactée seule » (la carte
  graphique est prise). Tous les sauts sont lus dans le code.
- Les fichiers de données ne sont pas dans le dépôt : contenu réel des drapeaux Gaia B, double comptage effectif,
  étoiles collées au bord de la boîte, plages des fichiers de lunes.
- Les valeurs publiées citées par les revues sont de mémoire [Probable].

## 10. Corrections faites à `analyse-architecture.md`

La revue des galaxies a contesté quatre points de mon analyse, à raison :
- « Autre repère » entre film et scénarios : exagéré (78 pc, ~4 km/s). Le vrai écart est la distance d'Andromède
  (785 contre 761 kpc).
- « 5,44 contre 6,5 Ga » : les deux n'ont pas le même critère de fusion. Avec le même, le film donne 4,64 Ga, dans la
  fourchette des scénarios. La contradiction à l'écran existe, mais plus petite que je l'avais écrit.
- « Pas en équilibre » : le départ est en équilibre mais **instable** (G1, G2). Vieillir les galaxies seules ne suffit
  donc pas : il faut d'abord corriger le modèle.
- Le champ de gravité de l'étape 3 : il en faut un par galaxie, à centre mobile, plus serré que 20 Ma près des passages.

## 11. Bilan et ordre de réparation

Constats : **17 graves, 28 moyens, une vingtaine de mineurs** (regroupés en 4 lignes). Graves : étoiles 3, système
solaire 3, galaxies et rencontre 6, interface et honnêteté de l'écran 5.

Trois familles :
1. **L'écran ment** (I1, I2, I3, I4, I8, G6, S1, S4) : étiquettes « mesuré » ou « exact » fausses, complétude à
   99,6 %. Rapide à corriger, sans calcul. À faire tout de suite : c'est ce qui trompe Marc aujourd'hui.
2. **Les calculs de départ sont faux** (G1, G2, G4, G5, G10, E1, E2, E5, E6). Aucun grand calcul ne doit repartir avant
   leur correction. Plus de particules n'en corrige aucun.
3. **Les coutures** (tous les passages de la section 2, G3, I5, E3, E11, S6) : c'est la cause racine décrite dans
   `analyse-architecture.md` ; elles ne partent qu'avec l'état unique.

Ordre proposé :
- (a) vérité de l'écran ;
- (b) essais automatiques de l'appli PC, dont l'essai de continuité ;
- (c) correction des modèles de départ, avec de petits tirs de contrôle ;
- (d) lecteur du film : origine des temps, images plus serrées ou courbes entre images ;
- (e) le grand calcul ;
- (f) les étoiles dans le champ du calcul, puis le reste du plan.
