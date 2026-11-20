"""Incertitude du tenseur de marée extérieur : dispersion entre réalisations contraintes (graines et réglages différents).

Pour chaque calcul : tenseur T_ij = −∂²Φ/∂x_i∂x_j (même formule que environnement_paire.py) au centre de masse de la paire
(calculs sans paire écartés : leur environnement n'est pas celui d'un Groupe local), à aujourd'hui et à a = 0,909 (−1,27 Ga) quand
l'instantané existe. Repère galactique de l'appli. Sortie : CSV par calcul + moyenne et écart-type par composante.
Usage (WSL) : python3 maree_dispersion.py SORTIE.csv DOSSIER_CALCUL [DOSSIER_CALCUL ...]
"""
import os
import sys

import h5py
import numpy as np

from environnement_paire import G, H, R_EXT_KPC, R_INT_KPC, ROT_SG_GAL, age_ga, charger_particules


def maree(snap):
    f = h5py.File(snap, 'r')
    a = float(f['Header'].attrs['Time'])
    zone = np.median(f['PartType1/Coordinates'][:].astype(np.float64), axis=0)
    # centre de masse de la paire (deux halos de 5e11 à 1e13 M☉ à moins de 2 Mpc/h de la zone fine) ; sinon on écarte
    g = h5py.File(snap.replace('snap_', 'fof_subhalo_tab_'), 'r')
    if g['Header'].attrs['Ngroups_Total'] == 0:
        return None
    m = g['Group/Group_M_Crit200'][:] * 1e10 / H
    p = g['Group/GroupPos'][:].astype(np.float64)
    c = np.where((np.linalg.norm(p - zone, axis=1) < 2.0) & (m > 5e11) & (m < 1e13))[0]
    if len(c) < 2:
        return None
    i, j = c[np.argsort(-m[c])[:2]]
    if np.linalg.norm(p[i] - p[j]) * a / H > 1.6:          # pas une paire (plus de 1,6 Mpc)
        return None
    centre = (m[i] * p[i] + m[j] * p[j]) / (m[i] + m[j])
    pos, mas = charger_particules(snap)
    rel = (pos - centre) * a / H * 1000.0
    rr = np.linalg.norm(rel, axis=1)
    sel = (rr > R_INT_KPC) & (rr < R_EXT_KPC)
    x, m, q = rel[sel], mas[sel], rr[sel]
    t = G * np.einsum('n,ni,nj->ij', m / q ** 5, 3.0 * x, x) - G * np.eye(3) * np.sum(m / q ** 3)
    return round(age_ga(a) - age_ga(1.0), 2), ROT_SG_GAL @ t @ ROT_SG_GAL.T


def main():
    sortie, dossiers = sys.argv[1], sys.argv[2:]
    par_date = {}
    lignes = ['calcul,t_ga,Txx,Txy,Txz,Tyx,Tyy,Tyz,Tzx,Tzy,Tzz']
    for d in dossiers:
        for snap in ('snap_005.hdf5', 'snap_004.hdf5', 'snap_029.hdf5', 'snap_025.hdf5'):
            chemin = os.path.join(d, snap)
            if not os.path.exists(chemin):
                continue
            r = maree(chemin)
            if r is None:
                continue
            t, tg = r
            if t < -1.4:
                continue
            par_date.setdefault(t, []).append(tg)
            lignes.append(f'{os.path.basename(os.path.dirname(d.rstrip("/")))},{t},' + ','.join(f'{v:.4e}' for v in tg.ravel()))
    lignes.append('# résumé : t_ga, nombre de calculs, moyenne puis écart-type des 9 composantes')
    for t, liste in sorted(par_date.items()):
        a = np.array(liste)
        lignes.append(f'# {t},{len(a)},' + ','.join(f'{v:.4e}' for v in a.mean(0).ravel()) + ','
                      + ','.join(f'{v:.4e}' for v in a.std(0, ddof=1).ravel()))
        print(t, len(a), 'moyenne Txx', f'{a[:, 0, 0].mean():.2e}', 'écart-type', f'{a[:, 0, 0].std(ddof=1):.2e}')
    open(sortie, 'w').write('\n'.join(lignes) + '\n')


if __name__ == '__main__':
    main()
