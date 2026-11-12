# Appli PC : étoiles Gaia en masse et Voie lactée (12 novembre 2026)

Demande (coordinateur, pour Marc) : des dizaines puis 100 millions d'étoiles mesurées, fluides sur la RTX 5080, et le
rendu de la Voie lactée (disque, poussière, barre). Règle de Marc : rien de supposé pour l'état présent, seulement du
mesuré ; seule l'évolution dans le temps est calculée. Confiance : [Certain] vérifié ; [Probable] ; [Supposition].

Partage avec les autres fils : ce fil écrit `gaia.h`, `voie_lactee.h`, leurs shaders, `StarRenderer` (commun.h) et les
scripts `pipeline/natif/gaia_*.py`, `voie_lactee.py`. Le fil natif branche les classes dans `fenetre.cpp` et
`installer.ps1`. Le fil de la gravité fournit la barre tournante (`galaxie_orbites.h`) et les orbites au-delà de 3 Ma.

## Étoiles : Gaia DR3

- Source : archive Gaia de l'ESA, `gaiadr3.gaia_source`, toutes les étoiles dont la parallaxe vaut plus de dix fois son
  erreur (distance mesurée à mieux que 10 %). Compté le 12 novembre 2026 : **98 346 986** étoiles [Certain].
- `pipeline/natif/gaia_telecharger.py` : 1024 requêtes (une par morceau de ciel), reprise après coupure. Piège trouvé :
  sans `MAXREC`, le service coupe chaque réponse à 50 000 lignes sans erreur ; le script vérifie maintenant le nombre.
- `pipeline/natif/gaia_convertir.py` -> `gaia.bin` : distance = 1 / parallaxe ; magnitude absolue G telle que mesurée
  (poussière comprise, vue du Soleil) ; couleur par l'indice BP-RP mesuré, converti en température par le corps noir vu à
  travers les bandes de Gaia (Riello et al. 2021) [Probable : une étoile n'est pas un corps noir] ; vitesse par le
  mouvement propre, plus la vitesse radiale de Gaia quand elle existe (sinon comptée nulle, et l'étoile le dit).
- Doublons : les étoiles brillantes du catalogue principal de la page (noms, fiches) restent ; leur copie Gaia est retirée
  (même direction à 40″, magnitude à 2 près).
- Dessin (`natif/src/gaia.h`, `shaders/gaia.vert`) : arbre en huit, feuilles de 32 768 étoiles rangées de la plus brillante
  à la plus faible ; à chaque image, seules les feuilles dans le champ, et dans chacune seules les étoiles assez brillantes
  pour compter vues de la caméra (flux minimal 1e-6, l'écran montre à partir de 4e-4). Un seul appel de dessin.
  16 octets par étoile en mémoire graphique (+ 8 pour la vitesse, lue seulement si le temps bouge).
- Lumière des étoiles sautées : chaque feuille garde un résumé (lumière par tranche de magnitude, centre de lumière) ;
  ce qui est sauté est rendu en un point par feuille, étalé sur la taille de la feuille à l'écran (au plus 512 pixels).
- Pas encore : les étoiles Gaia ne suivent pas les orbites galactiques au-delà de 3 Ma (fil de la gravité) ; elles vont en
  ligne droite à leur vitesse mesurée, comme celles de la page.

### Résultats du 12 novembre 2026 (RTX 5080 partagée avec le calcul de la fusion, carte occupée à 100 %) [Certain]

- Téléchargement : 1024 parts, 5,6 Go, 17 minutes. Conversion : 98 278 356 étoiles après retrait de 57 115 doublons (sur
  58 967 étoiles du catalogue principal), 10 658 feuilles, `gaia.bin` 2,4 Go ; 25 878 867 vitesses radiales mesurées ;
  673 131 étoiles sans couleur mesurée (dessinées blanches).
- `pipeline/natif/test_gaia.py` : tout passe (feuilles contiguës et triées, 1 878/1 878 étoiles retrouvées à leur place
  depuis les fichiers téléchargés, magnitude à 0,004 près, Étoile de Barnard à 5,9629 al et Proxima à 4,2465 al d'après
  leur parallaxe, poussière au Soleil 0,40 mag/kpc : la bulle locale).
- Cadence (`essai_gaia`, 1920 × 1080, seuil 3e-5), avec la lumière totale de l'image comparée au dessin de toutes les étoiles :

| Vue | Étoiles dessinées une à une | Images/s | Images/s sans niveaux de détail | Lumière totale |
|---|---|---|---|---|
| Du Soleil vers le centre galactique, champ 90° | 16,1 M | 307 | 153 | -0,4 % |
| À 8 000 al au-dessus du Soleil | 12,1 M | 194 | 61 | +0,15 % |
| À 25 000 al, toute la bulle Gaia | 3,3 M | 227 | 39 | +1,5 % |

- Vu de loin, la bulle des étoiles Gaia montre des rayons tournés vers le Soleil : c'est l'erreur de distance (jusqu'à
  10 %) le long de la ligne de visée, telle que mesurée. Rien n'est lissé.
- Mesure indépendante : dans la case de 100 pc autour du Soleil, les étoiles cataloguées (Gaia + catalogue principal)
  donnent 0,039 L_sol/pc³ et le modèle de la Galaxie 0,042 : 7 % d'écart, sans ajustement.

## Voie lactée

`pipeline/natif/voie_lactee.py` -> `voie_lactee.bin` ; `natif/src/voie_lactee.h`, `shaders/voie_lactee.frag`.
C'est un **modèle ajusté par d'autres sur des mesures**, à présenter comme tel à l'écran :

| Élément | Source | Statut |
|---|---|---|
| Luminosité totale (M_V = -21,51) et couleur (B-V = 0,744) | Licquia, Newman et Bershady 2015, table 3 | mesuré (par comparaison à des galaxies semblables) |
| Disques mince et épais, bulbe, barres : formes et masses | Bland-Hawthorn et Gerhard 2016 | ajusté sur des mesures |
| Partage de la lumière entre composantes | prorata des masses | **supposé** (même rapport masse/lumière) |
| Tracé des bras | Reid et al. 2019, table 2 (parallaxes de masers), sur l'azimut mesuré seulement | mesuré |
| Lumière ajoutée par les bras (disque doublé sur leur axe) | — | **supposé** |
| Largeur de la barre longue dans le plan (0,5 kpc) | — | **supposé** |
| Angle et vitesse de la barre (28°, 39 km/s/kpc) | Wegg et Gerhard 2013, Portail et al. 2017 (fil de la gravité) | mesuré ; rotation calculée |
| Poussière à moins de 1,25 kpc | Edenhofer et al. 2024 (carte de la page) | mesuré |
| Poussière au-delà | forme de Drimmel et Spergel 2001, amplitude calée sur la carte mesurée | ajusté |

- Rien n'est compté deux fois : la grille ne garde que la lumière qui manque aux étoiles dessinées une à une.
- Contrôles (`pipeline/natif/test_gaia_unitaire.py`, sans données) [Certain] : bras au bon rayon à leur coude, absents hors
  de l'azimut mesuré ; luminosité totale 3,45e10 L_sol ; part du disque épais au Soleil 3,6 % (publié : 4 % ± 2, ce que
  les masses donnent sans l'avoir imposé) ; poussière en sech² avec évasement.
- Mesuré par le script : extinction moyenne dans le plan jusqu'à 1,25 kpc = 1,49 mag (carte d'Edenhofer) ; d'où
  1,18 mag/kpc au Soleil pour le modèle de poussière.

## Toutes les autres sources Gaia, additionnées (12 novembre 2026, demande de Marc : « on généralise au fur et à mesure »)

De près, chaque étoile mesurée ; en s'éloignant, des sommes de ce qui est mesuré, sans modèle.

- `pipeline/natif/gaia_agreger.py` : sur le serveur de l'ESA, la lumière G de toutes les sources qui ne sont pas dans
  `gaia.bin` est additionnée par case (pixel HEALPix de niveau 7, 0,21 deg² × tranche de parallaxe d'un dixième de
  décade), avec la couleur moyenne et l'erreur moyenne de distance de la case. Rien n'est téléchargé source par source :
  390 Mo en 12 minutes.
- `pipeline/natif/gaia_agrege_convertir.py` -> `gaia_agrege.bin` (122 Mo) : 3 623 419 cases placées à leur distance
  (erreur moyenne de distance ≤ 100 %), 68,7 % de cette lumière ; le reste (pas de parallaxe positive, ou erreur > 100 %),
  31,3 %, n'a pas de distance : il est montré comme ciel vu du Soleil seulement (à moins de 100 al du Soleil).
- Bilan [Certain] : 98 346 986 étoiles une à une + 1 707 918 961 sources additionnées = toutes les sources de Gaia DR3
  qui ont une magnitude G (1 811 709 771 sources au total, dont environ 5,4 millions sans magnitude G).
- Dessin (`gaia.h`, `shaders/gaia_agrege.vert`) : chaque case est répartie en 8 points sur son épaisseur en distance
  (sans cela, des coquilles concentriques autour du Soleil) et étalée sur sa taille à l'écran. Le modèle de la Voie lactée
  retire maintenant aussi cette lumière (`voie_lactee.py … gaia_agrege.bin`).
- Cadence (carte partagée avec le calcul de la fusion) : 94 images/s du Soleil vers le centre galactique avec la
  Voie lactée, 71 images/s vu de 25 000 al.
- Ce qui se voit de loin est la Galaxie telle que Gaia la mesure : plus de lumière vers le centre galactique, et une forme
  allongée vers le Soleil due à l'incertitude des distances.

### Correction des alignements vus par Marc (12 novembre 2026, 19 h 30 UTC)

Cause [Certain, captures avant/après à 3 000, 30 000 et 60 000 al] : la lumière additionnée était placée en 8 points
réguliers sur l'axe de chaque case (traits de 8 points), cases centrées sur le Soleil (coquilles et rayons réguliers).
Corrections :
- dans chaque case, la lumière est répartie en points tirés uniformément dans tout son volume (tirage fixe par case,
  hachage PCG) ; la tache de chaque point couvre l'écart entre points (épaisseur projetée sur l'écran) ;
- en volume, seules les sources dont la parallaxe vaut plus de 5 fois son erreur (distance à mieux que 20 %), source par
  source sur le serveur : 93,8 millions de sources, 3 181 655 cases, 30,3 % de cette lumière. Les 1,61 milliard d'autres
  sont « ciel seul » (vues du Soleil, sans profondeur) : rien n'est placé à une distance mal mesurée.

### Les étoiles Gaia sur leur orbite, à toute date (12 novembre 2026, 20 h UTC)

- `gaia.vert` : même mouvement que les étoiles du catalogue principal (`orbite_galactique.glsl` du fil natif) : ligne droite
  mesurée, raccordée sans seuil à l'orbite calculée autour de la Galaxie. Plus de coupure à 3 Ma.
- 72,4 millions d'étoiles n'ont pas de vitesse radiale mesurée : elle compte pour nulle (l'étoile ne s'éloigne ni ne
  s'approche du Soleil au départ). C'est une supposition sur l'évolution, dite à l'écran ; l'état présent reste mesuré.
- Feuilles de l'arbre : chacune suit l'orbite de son centre (vitesse moyenne de ses étoiles) et sa boîte grandit de
  100 km/s × temps (dispersion, marge large), jusqu'à couvrir la Galaxie ; la lumière sautée suit sa feuille.
- Lumière additionnée (`gaia_agrege.bin`) : sans vitesses, montrée seulement à moins de 3 Ma des mesures.
- Lueur de la Voie lactée : décalée de l'opposé du chemin du Soleil (`orbite::decalageSoleil`), la barre tourne.
- Mesuré (carte partagée avec l'appli de Marc et la fusion) : 57 images/s aujourd'hui, 58 à +50 Ma, 21 à +230 Ma (vue de
  60 000 al, toutes les étoiles dessinées une fois dispersées). Captures : C:	mp
atif\essai-mw\orbites_4dates.png.

### Orbites exactes des étoiles Gaia (12 novembre 2026, 20 h 30 UTC)

- `natif/src/gaia_orbites.h` : le shader du fil natif `orbites_pas.comp` (potentiel complet avec la barre, saut de
  grenouille, sous-pas par étoile) appliqué aux 98 278 356 étoiles Gaia + le Soleil, EN PLACE (un seul état : 3,15 Go sur
  la carte ; les états de départ, 3,15 Go, restent en mémoire vive pour revenir à aujourd'hui). États de départ calculés
  dans un fil à part au chargement (6,0 s mesurées).
- `gaia.vert` : entre deux pas d'un million d'années, prolongement au second ordre (x + h v + h² a / 2) ; raccord sans
  seuil avec la ligne droite mesurée ; épicycles tant que le calcul exact n'a pas rattrapé la date.
- Contrôle (`essai_gaia --orbites-exactes --date 1e8`) [Certain] : après 99 Ma, 20 000 étoiles comparées au calcul en double
  précision de la bibliothèque de physique : écart médian 0,008 pc, 99ᵉ centile 0,05 pc, maximum 192 pc (une orbite
  chaotique près du centre, où simple et double précision divergent).
- Coût mesuré (carte partagée avec l'appli de Marc et la fusion) : 27 ms par pas d'un million d'années pour les 98 M.
  À 10 Ma par seconde, environ 27 % de la carte. Non fait : n'avancer que les feuilles visibles (proposition 2).
- Écart connu : la lueur de la Voie lactée suit encore le Soleil des épicycles (orbite::decalageSoleil), pas le Soleil exact.
