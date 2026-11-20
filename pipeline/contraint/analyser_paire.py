"""Lit le catalogue de halos (GADGET-4, SUBFIND) d'un calcul contraint et cherche notre Groupe local.

Tourne sous WSL (python3 système : numpy + h5py). Unités du calcul : Mpc/h, 1e10 M☉/h, km/s.
Critères HESTIA (Libeskind et al. 2020) [Certain] : deux halos de 0,8 à 3 × 10¹² M☉, séparés de 0,5 à 1,2 Mpc,
qui se rapprochent, rapport des masses > 0,5, pas de troisième halo plus lourd que le petit dans 2 Mpc ;
Vierge > 2 × 10¹⁴ M☉ à moins de 7,5 Mpc de sa place.
Mesures visées [Certain] : 785 ± 25 kpc, vitesse radiale −110 km/s, transverse < 60 km/s.

Usage : python3 analyser_paire.py CATALOGUE.hdf5 [h=0.6766] [boite=640]
"""
import json
import sys

import h5py
import numpy as np

H = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6766
BOITE = float(sys.argv[3]) if len(sys.argv) > 3 else 640.0
CENTRE = np.full(3, BOITE / 2.0)
# Vierge : 16,5 Mpc (échelle de CF4, H0 = 74,6 → 12,3 Mpc/h), SGL 102,9°, SGB −2,3° ; axes de la boîte = repère supergalactique [Probable]
_l, _b = np.radians(102.9), np.radians(-2.3)
VIERGE = CENTRE + 16.5 * 0.746 * np.array([np.cos(_b) * np.cos(_l), np.cos(_b) * np.sin(_l), np.sin(_b)])


def periodique(dx: np.ndarray) -> np.ndarray:
    return dx - BOITE * np.round(dx / BOITE)


def vierge_depuis_particules(instantane: str) -> dict:
    """La Vierge est hors de la zone fine : on la cherche dans TOUTES les particules (grossières comprises).

    Masse dans des cases de 2 Mpc/h (blocs de 2×2×2 = sphère d'environ 2,5 Mpc) dans 7,5 Mpc autour de sa place ;
    on garde le bloc le plus lourd. Mesure : masse viriale de la Vierge ~1,2 × 10¹⁵ M☉ [Probable, ordre de grandeur].
    """
    f = h5py.File(instantane, 'r')
    tab = f['Header'].attrs['MassTable']
    cote = 16.0 * H
    pos, mas = [], []
    for t in (1, 2, 3, 4, 5):
        g = f.get(f'PartType{t}')
        if g is None:
            continue
        p = periodique(g['Coordinates'][:] - VIERGE)
        dedans = np.all(np.abs(p) < cote / 2, axis=1)
        pos.append(p[dedans])
        mas.append(g['Masses'][:][dedans] if 'Masses' in g else np.full(dedans.sum(), tab[t]))
    pos, mas = np.concatenate(pos), np.concatenate(mas)
    nb = int(cote / 2.0)
    h3, _ = np.histogramdd(pos, bins=nb, range=[(-cote / 2, cote / 2)] * 3, weights=mas)
    bloc = h3[:-1, :-1, :-1] + h3[1:, :-1, :-1] + h3[:-1, 1:, :-1] + h3[:-1, :-1, 1:] \
        + h3[1:, 1:, :-1] + h3[1:, :-1, 1:] + h3[:-1, 1:, 1:] + h3[1:, 1:, 1:]
    i = np.unravel_index(np.argmax(bloc), bloc.shape)
    centre = (np.array(i) + 1.0) * (cote / nb) - cote / 2
    moyenne = 0.3111 * 27.75 * (2 * cote / nb) ** 3                     # 1e10 M☉/h dans un bloc moyen
    return dict(masse_bloc_msun=float(bloc[i] * 1e10 / H), surdensite=float(bloc[i] / moyenne),
                ecart_mpc=float(np.linalg.norm(centre) / H))


def main() -> None:
    f = h5py.File(sys.argv[1], 'r')
    a = f['Header'].attrs['Time']
    m200 = f['Group/Group_M_Crit200'][:] * 1e10 / H                     # M☉
    pos = f['Group/GroupPos'][:]
    vel = f['Group/GroupVel'][:]                                       # km/s [À vérifier : convention GADGET-4]
    # la zone fine (particules de type 1) est l'endroit où le Groupe local a pu se former : on y cherche la paire
    snap = h5py.File(sys.argv[1].replace('fof_subhalo_tab', 'snap'), 'r')
    zone = CENTRE + np.median(periodique(snap['PartType1/Coordinates'][:] - CENTRE), axis=0)
    print(f'zone fine à {np.linalg.norm(zone - CENTRE) / H:.1f} Mpc du centre (place de l observateur)')
    d_centre = np.linalg.norm(periodique(pos - zone), axis=1)
    proches = np.where((d_centre < 5.0 * H) & (m200 > 3e11))[0]
    proches = proches[np.argsort(-m200[proches])]
    print(f'a = {a:.3f} ; {len(m200)} groupes ; halos > 3e11 M☉ à moins de 5 Mpc de la zone fine : {len(proches)}')
    for i in proches[:8]:
        print(f'  #{i:6d}  M200 {m200[i]:.2e} M☉  à {d_centre[i] / H:5.2f} Mpc de la zone fine')

    meilleure = None
    for ii, i in enumerate(proches):
        for j in proches[ii + 1:]:
            mi, mj = m200[i], m200[j]
            if not (0.8e12 <= mj and mi <= 3e12 and mj / mi > 0.5):
                continue
            dx = periodique(pos[j] - pos[i]) * a                         # Mpc/h physiques
            r = np.linalg.norm(dx)
            sep_kpc = r / H * 1000.0
            if not 500.0 <= sep_kpc <= 1200.0:
                continue
            dv = vel[j] - vel[i] + 100.0 * dx                            # flot de Hubble inclus (a = 1)
            vr = np.dot(dv, dx / r)
            vt = np.linalg.norm(dv - vr * dx / r)
            milieu = pos[i] + periodique(pos[j] - pos[i]) / 2.0
            autres = [k for k in proches if k not in (i, j)
                      and np.linalg.norm(periodique(pos[k] - milieu)) / H < 2.0 and m200[k] > mj]
            score = abs(sep_kpc - 785) / 25 + abs(vr + 110) / 30 + max(vt - 60, 0) / 30
            cand = dict(halos=[int(i), int(j)], m200=[float(mi), float(mj)], separation_kpc=float(sep_kpc),
                        v_radiale=float(vr), v_transverse=float(vt), isolee=not autres,
                        decalage_centre_mpc=float(np.linalg.norm(periodique(milieu - CENTRE)) / H), score=float(score))
            if cand['isolee'] and (meilleure is None or score < meilleure['score']):
                meilleure = cand
    vierge = vierge_depuis_particules(sys.argv[1].replace('fof_subhalo_tab', 'snap'))
    bilan = dict(a=float(a), paire=meilleure, vierge=vierge)
    print(json.dumps(bilan, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
