#!/usr/bin/env python3
"""Écrit le catalogue principal à pleine précision (hyg_principal.npz, etoiles_hyg.py) dans un etoiles.bin existant.

Seules les étoiles du catalogue principal (les premières du fichier) sont remplacées : position, magnitude absolue,
couleur, vitesse. Les autres catalogues du fichier ne sont pas touchés. Le nombre d'étoiles doit être le même.
Usage : python etoiles_hyg_appliquer.py <hyg_principal.npz> <etoiles.bin>
"""
import sys

import numpy as np

ALIGN = 64


def main() -> None:
    npz_path, bin_path = sys.argv[1], sys.argv[2]
    with np.load(npz_path) as d:
        cols = [d['pos'][:, 0], d['pos'][:, 1], d['pos'][:, 2], d['absmag'], d['ci'], d['vel'][:, 0], d['vel'][:, 1], d['vel'][:, 2]]
    with open(bin_path, 'r+b') as f:
        head = f.read(ALIGN)
        if head[:8] != b'UNIVSTR1':
            raise SystemExit('ÉCHEC : ce fichier n\'est pas un etoiles.bin')
        n = int(np.frombuffer(head[8:16], '<i8')[0])
        principal = int(np.frombuffer(head[16:20], '<i4')[0])
        if principal != len(cols[0]):
            raise SystemExit(f'ÉCHEC : {principal} étoiles principales dans le fichier, {len(cols[0])} à écrire')
        column = (n * 4 + ALIGN - 1) // ALIGN * ALIGN
        for k, c in enumerate(cols):
            f.seek(ALIGN + k * column)
            f.write(c.astype('<f4').tobytes())
    print(f'{principal} étoiles du catalogue principal réécrites dans {bin_path}')


if __name__ == '__main__':
    main()
