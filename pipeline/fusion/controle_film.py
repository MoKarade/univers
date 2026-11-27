#!/usr/bin/env python3
"""Contrôle de stabilité d'un film d'essai au format 3 : rayons de chaque famille d'étoiles visibles de chaque galaxie
(10, 25, 50, 75, 90 %) au début, au milieu et à la fin ; barre de la Voie lactée ; rayon du Soleil ; énergie.
Usage : python controle_film.py <dossier du calcul (contient film/ et etoiles/)>"""
import json
import sys

import numpy as np

import film_v3 as F
import rencontre as R

S = sys.argv[1].replace(chr(92), '/').rstrip('/') + '/'
E = (sys.argv[2].replace(chr(92), '/').rstrip('/') + '/') if len(sys.argv) > 2 else S + 'etoiles/'      # dossier des étoiles visibles, s'il est ailleurs
f = F.Film(S + 'film'); m = f.meta
dp = f.dates_de('p'); choix = [dp[0], dp[len(dp) // 2], dp[-1]]
P = [f.image(k)[0] for k in choix]
print('dates', len(f.dates), '; images P comparées :', [f.t[k] for k in choix], '; énergie finale %+.4f %%' % (100 * f.dates[-1]['energie']))
res = {}
for g, nom in enumerate(m['galaxies']):
    sl = f.bloc(0, 1, g); comp = np.load(E + f'etoiles_visibles_{nom}.npz')['comp']
    for c in np.unique(comp):
        k = comp == c; q = [np.percentile(np.linalg.norm(p[sl][k], axis=1), [10, 25, 50, 75, 90]) for p in P]
        res[f'{nom}/{c}'] = [x.tolist() for x in q]
        print(f'{nom:12s} famille {c} ({k.sum():7d}) : début {q[0].round(2)} ; milieu (%) {(100 * (q[1] / q[0] - 1)).round(1)} ; fin (%) {(100 * (q[2] / q[0] - 1)).round(1)}')
sl = f.bloc(0, 1, 0); comp = np.load(E + 'etoiles_visibles_voie_lactee.npz')['comp']; Rv = R.rotation_vers(R.C.galaxie('voie_lactee')['disque']['axe_rotation'])
for k, p in zip(choix, P):
    a = (p[sl][np.isin(comp, [1, 2, 4])]) @ Rv; r = np.hypot(a[:, 0], a[:, 1]); ph = np.arctan2(a[:, 1], a[:, 0])
    lobes = ' ; '.join(f'{lo}-{hi} kpc {abs(np.exp(2j * ph[(r >= lo) & (r < hi)]).mean()):.3f}' for lo, hi in ((1, 4), (4, 7), (7, 10)))
    fb, ab = R.phase_barre(a[:, 0], a[:, 1], 1.0, 4.0); print(f'Voie lactée à {f.t[k]:+.3f} Ga : barre {fb:.3f} à {ab:+.1f}° | part à deux lobes : {lobes}')
sl = f.bloc(0, 3); print('Soleil : rayon (kpc)', [round(float(np.hypot(p[sl][0][0], p[sl][0][1])), 2) for p in P])
json.dump(res, open(S + 'controle_film.json', 'w', encoding='utf-8'))
