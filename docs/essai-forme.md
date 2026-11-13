# Essai de forme : la forme de chaque galaxie, d’une image du film à la suivante (étape 0 du plan B+, 13 novembre 2026)

Plan : `docs/refonte-simulations-pro.md` § 6.2, étape 0 (« essai de continuité étendu à la forme »). C’est le « fini quand »
de l’étape 4 (« aucune galaxie ne change de forme au Play ») et de l’étape 7.

Labels : [Certain] mesuré ici ; [Supposition] choix fait ici, à revoir sur le premier vrai film.

## 1. Ce qu’il mesure

`pipeline/fusion/essai_forme.py`, pour chaque galaxie et à chaque image :

| Grandeur | Règle |
|---|---|
| nombre de points | **identique** à toutes les images (rien n’apparaît, rien ne disparaît) |
| poids total (masse, ou lumière pour les traceurs) | identique à 10⁻⁶ près (masse conservée, aucun fondu) |
| rapports d’axes b/a et c/a (points à moins de 20 kpc du centre) | continus |
| plan du disque (petit axe) et axe de rotation (moment cinétique, si les vitesses sont écrites) | continus |
| barre et bras : amplitude A2 et angle du motif à deux bras (entre 0,5 et 5 kpc) | continus ; l’angle seulement là où A2 > 0,1 |
| rayon qui contient la moitié du poids, épaisseur (médiane de \|z\|) | continus |
| écart entre le centre écrit dans le film et le centre des points | continu |

« Continu » : chaque image est comparée à la droite qui joint ses deux voisines. Une évolution lisse donne un résidu de
l’ordre de x″ Δt² / 8 ; un saut s donne deux résidus de ± s/2. Une cassure : un résidu qui dépasse à la fois un plancher
physique (2 % sur les rapports d’axes et A2, 2° sur les directions, 5° sur l’angle de barre, 2 à 3 % sur les tailles,
0,2 kpc sur le centre) **et** 8 fois l’écart typique robuste de la série [Supposition]. Le pas de temps peut varier (images
resserrées près des passages).

## 2. Ce que l’essai synthétique montre [Certain : `python pipeline/fusion/test_essai_forme.py`]

| Film | Résultat |
|---|---|
| propre : disque qui tourne, barre à 40 km/s/kpc, plan qui précesse de 10° et taille qui grossit de 40 % en 2 Ga, images resserrées à 5 Ma entre 1,0 et 1,2 Ga | 0 cassure |
| même film, forme remplacée d’un coup par une autre (bascule) | vue (A2, taille) |
| disque basculé de 10° d’un coup | vu (plan) |
| 1 % des points perdus | vu (nombre, poids) |
| barre tournée de 30° d’un coup | vue (angle de barre) |
| poids divisé par deux (fondu) | vu (poids) |
| centre écrit décalé de 1 kpc | vu (centre) |
| film bruité (20 000 vraies orbites dans un potentiel aplati, agitation 30 km/s) | 0 cassure |
| même film, disque 30 % plus compact d’un coup | vu (taille) |

Seuil de détection mesuré sur le film bruité à 20 000 points : un saut de taille de ~10 % (pas 5 %), une bascule du plan de
~5° (pas 3°). Avec les millions de points du vrai film, le bruit baisse et la sensibilité monte jusqu’aux planchers.

Un départ hors d’équilibre (disque trop agité verticalement) **est vu** : son épaisseur gonfle en une image. C’est voulu :
c’est exactement le « souffle » qui se voit au Play.

## 3. Ce qui manque

- **Film v2** : lecteur écrit d’après la description du fil des galaxies de départ (`film.json` + `img_NNNNN.f16`,
  traceurs relatifs au centre de leur galaxie, poids `lum` des `etoiles_visibles_<galaxie>.npz`) et essayé sur le film
  synthétique réécrit dans ce format (float16) : 0 cassure. À recaler sur le premier vrai film (noms de champs).
  `python pipeline/fusion/essai_forme.py film2 <dossier film/> --traceurs <dossier des npz>`. Pas de vitesses dans ce
  film : l’axe de rotation n’est pas suivi, le plan l’est (petit axe d’inertie).
- **Pas encore passé sur un vrai film** : l’ancien film est sur le PC et dans les fichiers des tâches GitHub, que ce
  conteneur ne peut pas télécharger. Commande, à lancer par un fil qui a le PC :
  `python pipeline/fusion/essai_forme.py ancien <dossier du calcul> --json forme.json`.
- Les points de l’appli qui ne viennent pas d’un film (nuages Gaia, `voie_lactee.h`) ne sont pas suivis : ils relèvent de
  `essai_continuite.cpp` et du fil qui possède `fenetre.cpp`.
