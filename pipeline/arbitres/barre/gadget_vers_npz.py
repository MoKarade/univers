#!/usr/bin/env python3
"""Exporte un départ GADGET-4 (depart.hdf5 d'un dossier de tir) au format .npz habituel de pipeline/fusion :
pos (kpc), vel (km/s), m (M☉), eps (kpc, lus dans le param.txt du même tir), kind, meta.
Types → sortes : 1 → 0 (matière noire), 2 → 1, 3 → 3, 4 → 4, 5 → 2 (bulbe).
Usage : python3 gadget_vers_npz.py <dossier du tir> <sortie.npz>"""
import json
import os
import sys

import h5py
import numpy as np

KIND_DE_TYPE = {1: 0, 2: 1, 3: 3, 4: 4, 5: 2}


def adoucissements(param):
    classe, eps = {}, {}
    for ligne in open(param):
        mots = ligne.split()
        if len(mots) >= 2 and mots[0].startswith('SofteningClassOfPartType'):
            classe[int(mots[0][len('SofteningClassOfPartType'):])] = int(mots[1])
        elif len(mots) >= 2 and mots[0].startswith('SofteningComovingClass'):
            eps[int(mots[0][len('SofteningComovingClass'):])] = float(mots[1])
    return {t: eps[c] for t, c in classe.items()}


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    e = adoucissements(os.path.join(dossier, 'param.txt'))
    pos, vel, m, eps, kind = [], [], [], [], []
    with h5py.File(os.path.join(dossier, 'depart.hdf5'), 'r') as f:
        for t, k in KIND_DE_TYPE.items():
            g = f.get(f'PartType{t}')
            if g is None:
                continue
            n = len(g['Masses'])
            pos.append(g['Coordinates'][:]); vel.append(g['Velocities'][:]); m.append(g['Masses'][:] * 1e10)
            eps.append(np.full(n, e[t])); kind.append(np.full(n, k, dtype=np.int8))
    meta = dict(source=os.path.join(dossier, 'depart.hdf5'), note='export du départ GADGET-4 tel que tourné',
                adoucissement_par_type_gadget=e)
    np.savez_compressed(sortie, pos=np.concatenate(pos), vel=np.concatenate(vel), m=np.concatenate(m),
                        eps=np.concatenate(eps), kind=np.concatenate(kind), meta=json.dumps(meta, ensure_ascii=False))
    k = np.concatenate(kind); mm = np.concatenate(m)
    for s in np.unique(k):
        print(f'sorte {s} : {int((k == s).sum())} particules, {mm[k == s].sum():.4e} M☉')


if __name__ == '__main__':
    main()
