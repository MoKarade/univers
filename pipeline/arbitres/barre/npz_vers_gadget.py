#!/usr/bin/env python3
"""Convertit un départ .npz de modeles_v2.py / stabilite_tir.py (M☉, kpc, km/s) en conditions de départ GADGET-4
(HDF5, ICFormat 3 ; unités kpc, km/s, 1e10 M☉). Un type GADGET par sorte (kind) : 0 → type 1 (matière noire),
1 → type 2 (disque mince), 3 → type 3 (« gaz » froid traité en étoiles), 4 → type 4 (disque épais), 2 → type 5 (bulbe).
Le type 0 (gaz SPH) reste vide. Une sorte sans type prévu arrête la conversion (le bulbe d'Andromède avait été oublié
ainsi le 19/11 : corrigé). Écrit aussi adoucissements.txt (« type eps » par ligne), relu par preparer.sh. Le centre de masse est ramené à l'origine, au repos (la barre guide est centrée sur l'origine).
Option --sous-echantillon=N : tirage au hasard de N particules, mêmes proportions par sorte, masses multipliées d'autant.
Option --npz-sortie=<fichier.npz> : écrit aussi le départ converti au format habituel (pos, vel, m en M☉, eps, kind, meta).
Usage : python3 npz_vers_gadget.py <depart.npz> <sortie.hdf5> [--sous-echantillon=N] [--graine=1] [--halo-tourne=f] [--npz-sortie=…]"""
import json
import sys

import h5py
import numpy as np

TYPE_DE_KIND = {0: 1, 1: 2, 3: 3, 4: 4, 2: 5}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--'))
    z = np.load(args[0])
    pos, vel, m, eps, kind = z['pos'], z['vel'], z['m'], z['eps'], z['kind']
    inconnues = set(np.unique(kind).tolist()) - set(TYPE_DE_KIND)
    if inconnues:
        sys.exit(f'sortes sans type GADGET : {sorted(inconnues)}')
    if 'halo-tourne' in opts:
        # Copie de stabilite_tir.py (--halo-tourne) : même tirage (graine 20261118), mêmes particules retournées.
        f = float(opts['halo-tourne']); rng = np.random.default_rng(20261118)
        x, v = pos.astype(np.float64), vel.astype(np.float64).copy()
        d = (kind == 1) | (kind == 4)
        sens = np.sign(np.sum(x[d, 0] * v[d, 1] - x[d, 1] * v[d, 0]))
        lz = x[:, 0] * v[:, 1] - x[:, 1] * v[:, 0]
        tourne = (kind == 0) & (lz * sens < 0) & (rng.uniform(size=len(kind)) < f)
        R2 = np.maximum(x[:, 0] ** 2 + x[:, 1] ** 2, 1e-12)
        vphi = lz / R2
        v[tourne, 0] += 2 * vphi[tourne] * x[tourne, 1]; v[tourne, 1] -= 2 * vphi[tourne] * x[tourne, 0]
        vel = v
        print(f'halo en rotation : {int(tourne.sum())} particules retournées', file=sys.stderr)
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
    with open('adoucissements.txt', 'w') as fa:
        for t, e in sorted(adouc.items()):
            if len(e) != 1:
                sys.exit(f'type {t} : plusieurs adoucissements {e}')
            fa.write(f'{t} {e[0]}' + chr(10))
    if 'npz-sortie' in opts:
        meta = json.loads(str(z['meta'])) if 'meta' in z.files else {}
        meta['conversion_gadget'] = dict(source=args[0], options=opts, centre_retire=c.tolist())
        np.savez_compressed(opts['npz-sortie'], pos=pos, vel=vel, m=m, eps=eps, kind=kind, meta=json.dumps(meta, ensure_ascii=False))
    print(json.dumps(dict(particules=int(npart.sum()), par_type=npart.tolist(), adoucissement_par_type=adouc,
                          centre_retire=c.round(4).tolist()), ensure_ascii=False))


if __name__ == '__main__':
    main()
