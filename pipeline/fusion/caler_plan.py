#!/usr/bin/env python3
"""Remet le disque de la Voie lactée du calcul dans le plan mesuré de la Galaxie, à t = 0.

Après le trajet d'il y a 1 milliard d'années à aujourd'hui, le disque de la masse est penché d'environ 1,5° par rapport
au plan galactique mesuré (mesuré le 16/11/2026 : axe du moment cinétique (-0,02 ; 0,02 ; -1,00)). À 8 kpc, 1,5° font
200 pc : les étoiles posées d'après les mesures ne sont alors plus dans le disque qui les porte. Comme pour l'angle de la
barre (mode « barre » de rencontre.py), c'est un choix de repère : on tourne la Voie lactée entière (étoiles, gaz, matière
noire), d'un bloc autour de son centre, pour que l'axe de son disque soit l'axe mesuré. Les autres galaxies ne bougent pas.
L'instantané d'origine est gardé (aujourdhui_brut.npz).

Usage : python caler_plan.py <dossier du calcul>
"""
import os
import sys

import numpy as np

sys.argv, _argv = ['x'], sys.argv
import rencontre as r      # noqa: E402
sys.argv = _argv


def main():
    sortie = sys.argv[1]
    f = os.path.join(sortie, 'aujourdhui.npz'); brut = os.path.join(sortie, 'aujourdhui_brut.npz')
    if not os.path.exists(brut): os.replace(f, brut)
    with np.load(brut) as z: p = {k: z[k] for k in z.files}
    g = p['gid'] == 0
    et = g & ((p['kind'] == 1) | (p['kind'] == 4))
    c = np.median(p['pos'][et], 0)
    for rr in (10.0, 5.0, 2.0, 1.0):
        d = np.linalg.norm(p['pos'][et] - c, axis=1); c = p['pos'][et][d < rr].mean(0)
    d = np.linalg.norm(p['pos'][et] - c, axis=1); cv = p['vel'][et][d < 1.0].mean(0)
    x = p['pos'][g] - c; w = p['vel'][g] - cv
    k = p['kind'][g]; R = np.hypot(x[:, 0], x[:, 1])
    q = ((k == 1) | (k == 3)) & (R > 4.0) & (R < 12.0)
    L = np.cross(x[q], w[q]).sum(0); L /= np.linalg.norm(L)
    axe = np.asarray(r.C.galaxie('voie_lactee')['disque']['axe_rotation'], float); axe /= np.linalg.norm(axe)
    v = np.cross(L, axe); s = np.linalg.norm(v); co = float(L @ axe)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    M = np.eye(3) + vx + vx @ vx * ((1 - co) / (s * s)) if s > 1e-12 else np.eye(3)
    print(f'axe du disque de la masse : {L.round(4).tolist()} ; axe mesuré : {axe.tolist()} ; écart {np.degrees(np.arcsin(min(s, 1.0))):.2f}°')
    p['pos'][g] = x @ M.T + c; p['vel'][g] = w @ M.T + cv
    x2 = p['pos'][g][q] - c; w2 = p['vel'][g][q] - cv
    L2 = np.cross(x2, w2).sum(0); L2 /= np.linalg.norm(L2)
    print(f'après : {L2.round(5).tolist()}')
    np.savez(f, **p)
    print('->', f)


if __name__ == '__main__':
    main()
