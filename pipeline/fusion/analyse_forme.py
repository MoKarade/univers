#!/usr/bin/env python3
"""Forme des galaxies au fil du calcul de fusion (fusion.json + kf_*.bin) : rapports d axes b/a et c/a des étoiles à moins
de 20 kpc du centre, épaisseur médiane, rayons médians, profil de Sérsic du reste final, distance finale du Soleil.
Usage : python analyse_forme.py <dossier du calcul>"""
import json, numpy as np, sys, os
d = sys.argv[1]
m = json.load(open(os.path.join(d, 'fusion.json'), encoding='utf-8'))
nshow = m['affichees']; N = sum(nshow); Q = m['quantum_kpc']
frames = []
for name, k in m['fichiers']:
    a = np.fromfile(os.path.join(d, name), np.int16).reshape(k, N, 3) * Q
    frames.append(a)
F = np.concatenate(frames); t = np.array(m['t'])
off = np.cumsum([0] + nshow)
C = np.array(m['centres'])  # n x 4 x 3
def stats(p):
    r = np.linalg.norm(p, axis=1); sel = r < 20; q = p[sel]
    I = q.T @ q / len(q); w, v = np.linalg.eigh(I); ax = np.sqrt(w[::-1])
    z = q @ v[:, 0]   # plus petit axe
    R = np.hypot(q @ v[:, 1], q @ v[:, 2])
    return ax[1] / ax[0], ax[2] / ax[0], np.median(np.abs(z)), np.median(R), np.median(r)
print('t(Ga)  galaxie  b/a  c/a  med|z|  medR  med r (étoiles < 20 kpc du centre)')
for ti in [0, 1, 2, 3, 4, 5, 5.42, 6, 6.8, 8, 10]:
    i = int(np.argmin(np.abs(t - ti)))
    for g, nom in enumerate(['mw', 'm31']):
        p = F[i, off[g]:off[g+1]] - C[i, g]
        ba, ca, hz, R, r = stats(p)
        print(f'{t[i]:5.2f}  {nom:4s}  {ba:.2f} {ca:.2f}  {hz:5.2f}  {R:5.2f}  {r:5.2f}  (sep {np.linalg.norm(C[i,0]-C[i,1]):.0f} kpc)')
# profil du reste à 10 Ga : Sérsic par ajustement de la densité projetée
i = len(t) - 1; cm = C[i, 0]
p = np.concatenate([F[i, off[0]:off[2]]]) - cm
R = np.hypot(p[:, 0], p[:, 1])
edges = np.geomspace(0.3, 60, 25); h, _ = np.histogram(R, edges); area = np.pi * (edges[1:]**2 - edges[:-1]**2); S = h / area; Rm = np.sqrt(edges[1:] * edges[:-1])
ok = h > 20
from scipy.optimize import curve_fit
def sersic(R, I0, Re, n):
    b = 2 * n - 1/3 + 0.009876 / n
    return np.log(I0) - b * ((R / Re) ** (1 / n) - 1)
popt, _ = curve_fit(sersic, Rm[ok], np.log(S[ok]), p0=[S[ok][len(S[ok])//2], 5, 4], bounds=([1e-9, 0.5, 0.5], [1e9, 50, 10]))
print('reste à %.2f Ga : Sérsic Re = %.1f kpc, n = %.2f (projection xy)' % (t[i], popt[1], popt[2]))
# Soleil (traceur 0)
S0 = np.array([tp[0] for tp in m['traceurs_pos']])
print('Soleil : distance au centre du reste à 10 Ga %.1f kpc' % np.linalg.norm(S0[-1] - cm))
