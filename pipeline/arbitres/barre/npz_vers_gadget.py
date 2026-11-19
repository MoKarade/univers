#!/usr/bin/env python3
"""Convertit un départ .npz de modeles_v2.py / stabilite_tir.py (M☉, kpc, km/s) en conditions de départ GADGET-4
(HDF5, ICFormat 3 ; unités kpc, km/s, 1e10 M☉). Un type GADGET par sorte (kind) : 0 → type 1 (matière noire),
1 → type 2 (disque mince), 3 → type 3 (« gaz » froid traité en étoiles), 4 → type 4 (disque épais). Le type 0 (gaz SPH)
reste vide. Le centre de masse est ramené à l'origine, au repos (la barre guide est centrée sur l'origine).
Option --sous-echantillon=N : tirage au hasard de N particules, mêmes proportions par sorte, masses multipliées d'autant.
Usage : python3 npz_vers_gadget.py <depart.npz> <sortie.hdf5> [--sous-echantillon=N] [--graine=1]"""
import json
import sys

import h5py
import numpy as np

TYPE_DE_KIND = {0: 1, 1: 2, 3: 3, 4: 4}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--'))
    z = np.load(args[0])
    pos, vel, m, eps, kind = z['pos'], z['vel'], z['m'], z['eps'], z['kind']
    if 'sous-echantillon' in opts:
        rng = np.random.default_rng(int(opts.get('graine', 1)))
        n_vise = int(opts['sous-echantillon']); garde = []
        m = m.copy()
        for k in np.unique(kind):
            idx = np.flatnonzero(kind == k)
            nk = max(1, round(len(idx) * n_vise / len(kind)))
            choix = rng.choice(idx, nk, replace=False)
            m[choix] *= m[idx].sum() / m[choix].sum()      # masse de la sorte conservée exactement
            garde.append(choix)
        g = np.sort(np.concatenate(garde))
        pos, vel, m, eps, kind = pos[g], vel[g], m[g], eps[g], kind[g]
    c = np.average(pos, axis=0, weights=m); v0 = np.average(vel, axis=0, weights=m)
    pos = pos - c; vel = vel - v0
    npart = np.zeros(6, dtype=np.int64); adouc = {}
    with h5py.File(args[1], 'w') as f:
        ident = 1
        for k, t in TYPE_DE_KIND.items():
            s = kind == k
            if not s.any():
                continue
            g = f.create_group(f'PartType{t}')
            g['Coordinates'] = pos[s]
            g['Velocities'] = vel[s]
            g['Masses'] = m[s] / 1e10
            g['ParticleIDs'] = np.arange(ident, ident + s.sum(), dtype=np.uint32)
            ident += s.sum(); npart[t] = s.sum(); adouc[t] = sorted(set(np.round(eps[s], 6)))
        h = f.create_group('Header')
        h.attrs['NumPart_ThisFile'] = npart; h.attrs['NumPart_Total'] = npart
        h.attrs['NumPart_Total_HighWord'] = np.zeros(6, dtype=np.int64)
        h.attrs['MassTable'] = np.zeros(6); h.attrs['Time'] = 0.0; h.attrs['Redshift'] = 0.0
        h.attrs['BoxSize'] = 0.0; h.attrs['NumFilesPerSnapshot'] = 1
    print(json.dumps(dict(particules=int(npart.sum()), par_type=npart.tolist(), adoucissement_par_type=adouc,
                          centre_retire=c.round(4).tolist()), ensure_ascii=False))


if __name__ == '__main__':
    main()
