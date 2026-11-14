# Contrat « étoiles visibles » : une seule population, d'aujourd'hui à la fusion (13 novembre 2026)

But : qu'aucune galaxie ne change de forme quand le temps démarre. Les étoiles que l'appli montre aujourd'hui sont
**les mêmes objets** que ceux que le calcul de la rencontre fait évoluer, dans le même ordre, à toutes les dates.

Deux fils s'alignent sur ce texte :
- le fil « Montrer la Voie lactée entière » **fournit** les étoiles visibles d'aujourd'hui ;
- le fil des galaxies de départ (branche `modeles-depart`) **les fait évoluer** dans le calcul et écrit le film.

## 1. Qui porte quoi

| | Masse (gravité) | Lumière (ce qu'on voit) |
|---|---|---|
| Source | particules de `pipeline/fusion/modeles_v2.py` : halo, disques, bulbe, gaz | traceurs du fichier `etoiles_visibles_<galaxie>.npz` |
| Rôle dans le calcul | elles s'attirent toutes | sans masse : elles subissent la gravité, n'en exercent pas (`kind` 9) |
| À l'écran | jamais dessinées | toujours dessinées, et elles seules |

La barre et les bras de l'image d'aujourd'hui viennent des mesures, par les traceurs. La masse est lisse (avec sa
barre quand le modèle en aura une). Les deux doivent rester proches : même vitesse de rotation, même agitation.

## 2. Fichier fourni : `etoiles_visibles_<galaxie>.npz`

`<galaxie>` : `voie_lactee`, `andromede`, `triangle`, `grand_nuage`, `petit_nuage`. Fichier numpy compressé, N lignes.

| Champ | Type | Unité | Sens |
|---|---|---|---|
| `pos` | float64 (N, 3) | kpc | position à t = 0 |
| `vel` | float64 (N, 3) | km/s | vitesse à t = 0 |
| `lum` | float32 (N) | L☉ | lumière que le traceur représente (flux agrégé) |
| `teff` | float32 (N) | K | température de couleur (ou `couleur` : indice B−V) |
| `comp` | int8 (N) | — | 1 disque mince, 2 bulbe et barre, 4 disque épais, 5 étoiles jeunes des bras et régions HII, 6 halo d'étoiles |
| `graine` | uint32 (N) | — | graine du nuage d'étoiles que l'appli déploie autour du traceur ; le calcul ne la lit pas |
| `meta` | chaîne JSON | — | sources, date, nombre par composante, repère |

Repère : celui de l'appli, `phys::galaxie` (`natif/physique/galaxie_orbites.h`) : centre de la Voie lactée à l'origine,
Soleil à −R0 dans la direction de Sagittarius A* (environ (−8,2 ; 0 ; 0) kpc), y vers la longitude 90°, z vers le nord
galactique. Pour les autres galaxies : **le même repère**, donc leur position et leur vitesse d'ensemble mesurées sont
déjà dedans. Instant : aujourd'hui (t = 0 du simulateur).

Vitesses : mesurées quand elles existent (étoiles Gaia proches). Sinon, vitesse circulaire du modèle de masse au rayon
du traceur (elle est dans `meta.vc` de chaque `<galaxie>.npz` de `modeles_v2.py`) plus l'agitation de sa composante ;
ou la vitesse de la particule de masse la plus proche. Voie lactée : 35 km/s (disque mince) et 50 km/s (disque épais)
au Soleil, décroissance exponentielle sur 5 kpc.

L'ordre des lignes est le contrat : la ligne k du fichier est la ligne k de toutes les images du film.

## 3. Plafonds

| Galaxie | Traceurs au plus |
|---|---|
| Voie lactée | 4 millions |
| Andromède | 3 millions |
| Triangle, Grand Nuage, Petit Nuage | 0,5 million chacune |
| Total | 8,5 millions |

Raison : le film garde chaque traceur à chaque image. À 12 octets par traceur et par image, 8,5 millions de traceurs
font environ 100 Mo par image, soit environ 60 Go pour 600 images [estimation]. Au-delà, c'est la place sur le Drive et
la lecture en direct qui cèdent, pas le calcul.

## 4. Ce que le calcul rend : le film, version 2

Écrit par le fil des galaxies de départ, lu dans l'appli par un lecteur qu'il fournit aussi (remplaçant de
`phys::fusion::Rejeu` et de `FusionCloud`). L'appli n'a donc à connaître que deux appels : la position du traceur k à
la date t, et le centre de chaque galaxie à la date t.

Engagements :
- **une image exactement à t = 0**, identique au fichier fourni (au pas d'arrondi près, dit dans l'en-tête) ;
- **l'origine des temps dans l'en-tête** : le film peut commencer avant aujourd'hui ;
- les traceurs dans l'ordre du fichier, galaxie après galaxie ; aucun traceur ajouté ni retiré en route ;
- positions relatives au centre de la galaxie d'origine du traceur, en nombres à virgule sur 32 bits ;
- entre deux images : courbe, pas ligne droite (les vitesses sont gardées), et images plus serrées près des passages ;
- par image : centre et masse liée de chaque galaxie, énergie totale.

Ce que le film ne fait pas : il ne connaît ni la graine ni le nuage d'étoiles déployé autour d'un traceur.

## 5. En attendant le film

Les étoiles visibles avancent dans l'appli par le calcul d'orbites existant (`natif/shaders/orbites_pas.comp`,
potentiel de `galaxie_orbites.h`), à partir des mêmes positions et vitesses. Le jour où le film arrive, l'état de
départ est le même : rien ne saute.

Limite connue de cette attente : ce potentiel est figé et ne contient ni Andromède ni les Nuages. Il vaut pour la Voie
lactée seule, pas pour la rencontre.

## 6. Ce qui peut encore changer

- Le contenu des modèles de masse (la barre n'y est pas encore) : la vitesse circulaire peut bouger de quelques km/s.
- Le format binaire exact du film : fixé quand le lecteur sera écrit ; les engagements du § 4 ne changent pas.
