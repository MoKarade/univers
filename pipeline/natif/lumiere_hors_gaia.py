#!/usr/bin/env python3
"""Lumière que les étoiles du MODÈLE doivent encore porter là où Gaia dessine déjà les étoiles mesurées.

Problème corrigé (fil « étoiles Gaia plus claires », 18 novembre 2026). Avant, chaque case de 100 pc retirait du modèle la
lumière Gaia de la même case, bornée à zéro. Mesuré sur les fichiers installés : 1 031 096 cases contiennent des étoiles
Gaia mais AUCUN traceur du modèle (4 millions de traceurs ne remplissent pas 8 millions de cases) ; 54 % de la lumière
Gaia tombait dans des cases où il n'y avait rien à retirer. Cette lumière s'ajoutait au modèle : la zone Gaia brillait 1,2
fois trop (moyenne dans le plan à moins de 1 kpc du Soleil), davantage autour des étoiles brillantes.

Correction : retrait lissé. La lumière Gaia qui ne trouve pas de modèle dans sa case diffuse (noyau gaussien, même
largeur en parsecs sur les trois axes) vers les cases voisines et y est retirée, jusqu'à 2 kpc. Pas de cases ni de
marches : le retrait varie en douceur, et la lumière totale est gardée. Ce qui reste au-delà est une vraie différence
(les étoiles mesurées brillent plus que le modèle sur des kpc) : on garde alors la mesure, et la valeur est rendue.

Lumière comparée : telle que mesurée (poussière Soleil-étoile comprise), comme avant. Essayé et écarté (mesuré le
18 novembre 2026) : désassombrir Gaia avec la carte de poussière de l'appli. Les facteurs atteignent 7 à 17 entre 2 et
6 kpc, et la lumière Gaia « intrinsèque » dépasse alors 1,3 à 2,2 fois tout le modèle : Gaia ne voit que les étoiles des
fenêtres peu poussiéreuses, la carte moyenne les sur-corrige [Probable]. Vu de loin (au-dessus du disque), comparer la
lumière mesurée donne exactement la lumière entière du modèle ; vu du Soleil, rien ne change par rapport à avant.

[Probable] G pris pour V (écart de quelques dixièmes de magnitude selon la couleur), comme voie_lactee.lumiere_cataloguee.
"""
import math
import numpy as np
from scipy.ndimage import gaussian_filter

PAS_DIFFUSION_PC = 100.0     # écart type du noyau à chaque pas (pc)
PORTEE_PC = 2000.0           # portée totale de la diffusion (pc) : pas = (PORTEE / PAS)²
RESTE_TOLERE = 1e-4          # arrêt quand l'excès restant est sous cette part de l'excès de départ


def retrait_lisse(modele, gaia, cote_pc=(50.0, 100.0, 100.0)):
    """Lumière à retirer de chaque case du modèle pour ne pas compter deux fois la lumière Gaia.
    modele, gaia : lumière par case (mêmes unités, forme (nz, ny, nx)), gaia telle que mesurée.
    Rend (retrait par case, excès resté sans modèle à moins de PORTEE_PC). Conservation : retrait.sum() + reste = gaia.sum()
    (aux pertes près par le bord de la grille, rendues dans le reste)."""
    direct = np.minimum(modele, gaia)
    R = modele - direct
    E = gaia - direct
    e0 = E.sum()
    sig = tuple(PAS_DIFFUSION_PC / c for c in cote_pc)
    pas = int(math.ceil((PORTEE_PC / PAS_DIFFUSION_PC) ** 2))
    for _ in range(pas):
        if E.sum() <= RESTE_TOLERE * max(e0, 1e-300): break
        E = gaussian_filter(E, sig, mode='constant', truncate=3.0)
        a = np.minimum(E, R)
        E -= a; R -= a; direct += a
    return direct, float(gaia.sum() - direct.sum())


def part_gardee(modele, retrait):
    """Part de sa lumière que chaque case du modèle garde (0 à 1)."""
    return np.clip(np.where(modele > 0, (modele - retrait) / np.maximum(modele, 1e-300), 1.0), 0.0, 1.0)
