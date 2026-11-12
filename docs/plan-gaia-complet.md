# Gaia complet dans l'appli PC (1 811 709 771 sources) — plan du 12/11/2026

Demande de Marc (12/11) : « toutes les données ». Règle de place (Marc, 12/11, confirmée) : environ 100 Go pour Univers
sur C:, tout le reste sur le Drive, lu à la demande par G: (Drive pour ordinateur, en diffusion), avec un petit écran de
chargement. Pas de cache maison : Drive garde déjà ce qu'il télécharge. Racine du Drive : réglable (pas écrite dans le
code), même mécanisme que les cartes du ciel (tuiles_dossier.txt, fil longueurs d'onde, commit c76ae1a).

## Source
- Fichiers complets de l'ESA (CDN, 3 386 CSV compressés, ~650 Go) : le service TAP anonyme coupe à 60 s (mesuré),
  inutilisable pour 1,7 milliard de lignes. Débit mesuré : ~50 Mo/s, 6 fichiers en 24 s → environ 4 h (estimation).
- `pipeline/natif/gaia_cdn.py` : chaque fichier est contrôlé (MD5 publié), réduit à 14 colonnes (position, parallaxe,
  mouvements propres, vitesse radiale, leurs erreurs, magnitude G, couleur BP-RP, RUWE), écrit en Parquet zstd
  (~31 Mo par fichier, ~105 Go en tout), puis le CSV est effacé. Plafond de 22 Go sur le PC : le téléchargement attend
  que les lots partent au Drive (archives/gaia_dr3).

## Ce qui va où

| Classe | Combien (à compter) | Ce qu'on sait | Où | Affichage |
|---|---|---|---|---|
| A. parallaxe > 10σ | 98 346 986 | distance à 10 % | PC (gaia.bin, déjà là) | une à une en 3D, orbites |
| B. parallaxe 5 à 10σ | ~94 M (192 208 838 − A) | distance à 10-20 % | PC (gaia_b.bin, ~2,3 Go) | une à une en 3D, marquée « distance à ±20 % » |
| C. le reste | ~1,62 G | direction exacte ; distance non mesurée (parallaxe < 5σ ou absente) | Drive (tuiles, ~26 Go à 16 octets) | une à une SUR LE CIEL vu du Soleil (direction mesurée, pas de profondeur inventée) ; de loin, toujours leur somme par case (gaia_agrege.bin) |
| Archive | 1,81 G × 14 colonnes | tout | Drive (archives/gaia_dr3, ~105 Go) | relue seulement pour refaire les tuiles |

## Lecteur à la demande (classe C)
- Tuiles HEALPix emboîtées, façon catalogue HiPS : l'ordre 3 garde les plus brillantes de chaque case, chaque ordre
  plus fin ajoute les plus faibles ; dans une tuile, tri par magnitude. Paquets de ~32 Mo de tuiles voisines, index
  sur le PC (quelques Mo), 4 lectures en parallèle.
- Ce qui se voit d'abord : le niveau grossier (déjà sur le PC) ; les tuiles fines arrivent dans le champ de vue,
  des plus brillantes aux plus faibles, seulement près du Soleil (au-delà, la direction seule ne place rien).
- Écran de chargement : petit bandeau « Chargement depuis le Drive : n paquets, x Mo » tant qu'un paquet est attendu ;
  rien ne fige l'image.
- Fiche au clic : identifiant Gaia, magnitude, couleur, parallaxe ± erreur (« distance non mesurée »).

## Impossible ou limité (dit tel quel)
- Placer en 3D les 1,62 G sources de la classe C : leur distance n'est pas mesurée (les distances de Bailer-Jones
  utilisent un modèle de la Galaxie comme a priori : contraire à « seulement du mesuré »).
- Faire évoluer dans le temps les classes B et C comme la classe A : sans distance sûre, l'orbite n'est pas calculable.
- Débit : la première visite d'une région du ciel attend le Drive (quelques secondes par paquet, à mesurer).

## Ordre
1. Téléchargement et archive (en cours).
2. Compter A/B/C sur les vrais fichiers, écrire gaia_b.bin (format de gaia.bin) et l'installer.
3. Tuiles de la classe C, index, lecteur, bandeau de chargement, fiche.
