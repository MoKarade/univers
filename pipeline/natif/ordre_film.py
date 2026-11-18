#!/usr/bin/env python3
"""Ordre des étoiles visibles dans l'appli, pour suivre le film du Groupe local.

L'appli range les étoiles visibles de la Voie lactée par zones (vl_etoiles.bin, écrit par etoiles_visibles.py) ; le film
(pipeline/fusion/rencontre.py) les garde dans l'ordre du contrat (etoiles_visibles_voie_lactee.npz). Ce script retrouve,
pour chaque étoile de l'appli, son rang dans le contrat, en comparant les positions, et l'écrit dans vl_etoiles.ordre
(un entier 32 bits par étoile, dans l'ordre de l'appli). Sans ce fichier, l'appli ne peut pas suivre le film.

Galaxies voisines : même chose avec voisines_etoiles.bin et les fichiers du contrat des quatre galaxies, dans l'ordre du
film (Andromède, Triangle, Grand Nuage, Petit Nuage), séparés par des virgules ; le rang compte alors à partir de la première
étoile d'Andromède. À 2,5 millions d'années-lumière, l'appli range les positions à 0,1 pc près : deux étoiles très proches
peuvent se confondre, ce qui est toléré jusqu'à 0,5 % (elles suivent alors la même route).

Usage : python ordre_film.py <vl_etoiles.bin> <etoiles_visibles_voie_lactee.npz[,autre.npz...]> [sortie]
"""
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

KPC_LY = 3261.5637769
# Mêmes constantes que l'appli (natif/src/orbite_galactique.h : kM ; natif/physique/galaxie_orbites.h : kSgra, kR0).
GAL2ECL = np.array([[-0.0548756577, 0.4941094372, -0.8676661376], [-0.993821367, -0.1109908412, -0.0003515418], [-0.0964766946, 0.8622858559, 0.4971472117]])
SUN = -8.2 * np.array([0.9999992, -0.00097327, -0.00080564])


def main():
    chemin, npz = sys.argv[1], sys.argv[2]
    sortie = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(chemin)[0] + '.ordre'
    with open(chemin, 'rb') as f:
        tete = f.read(4096)
        if tete[:8] != b'UNIVGAI1': raise SystemExit('ECHEC : pas un fichier d\'étoiles de l\'appli')
        n = int(np.frombuffer(tete, '<u8', 1, 8)[0]); feuilles = int(np.frombuffer(tete, '<u4', 1, 16)[0])
        f.seek(4096 + (feuilles * 48 + 63) // 64 * 64)
        rec = np.frombuffer(f.read(n * 16), np.dtype([('p', '<f4', 3), ('m', '<f2'), ('c', 'u1'), ('f', 'u1')]))
    appli = (rec['p'].astype(np.float64) / KPC_LY) @ GAL2ECL + SUN      # écliptique héliocentrique (al) -> phys::galaxie (kpc)
    morceaux = []
    for chemin_npz in npz.split(','):
        with np.load(chemin_npz) as z: morceaux.append(z['pos'].astype(np.float64))
    contrat = np.concatenate(morceaux); plusieurs = len(morceaux) > 1
    if len(contrat) != n: raise SystemExit(f'ECHEC : {n} étoiles dans l\'appli, {len(contrat)} dans le contrat')
    d, rang = cKDTree(contrat).query(appli, workers=-1)
    doubles = n - len(np.unique(rang)); unique = doubles == 0
    print(f'{n} étoiles ; écart le plus grand entre une étoile de l\'appli et celle du contrat : {d.max() * 1000:.4f} pc ; médiane {np.median(d) * 1000:.5f} pc ; '
          f'chaque étoile du contrat prise une seule fois : {"oui" if unique else "NON"}')
    if plusieurs: print(f'étoiles confondues avec une voisine : {doubles} ({100 * doubles / n:.3f} %)')
    if d.max() > (3e-3 if plusieurs else 1e-3) or (doubles > 0.005 * n if plusieurs else not unique): raise SystemExit('ECHEC : les deux fichiers ne décrivent pas les mêmes étoiles')
    rang.astype('<u4').tofile(sortie + '.partiel'); os.replace(sortie + '.partiel', sortie)
    print('->', sortie)


if __name__ == '__main__':
    main()
