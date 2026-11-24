#!/usr/bin/env python3
"""Essais de petit_nuage_profondeur.py sur des échantillons construits exprès (réponse connue), jamais affichés :
lecture des coordonnées, écarts à la relation période-Wesenheit, pose des distances avec retrait de la largeur propre.

Usage : python test_petit_nuage_profondeur.py   (rend 0 si tout est conforme)
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import petit_nuage_profondeur as P      # noqa: E402

ECHECS = []


def verifier(nom, ok, detail=''):
    print(('ok    ' if ok else 'ÉCHEC ') + nom + (f'  ({detail})' if detail else ''))
    if not ok:
        ECHECS.append(nom)


def test_sexa():
    ra, dec = P.sexa('00 52 38.00', '-72 48 01.0')
    verifier('coordonnées sexagésimales (espaces)', abs(ra - 13.1583) < 1e-3 and abs(dec + 72.8003) < 1e-3, f'{ra:.4f} {dec:.4f}')
    ra, dec = P.sexa('05:23:34.5', '-00:30:00')
    verifier('coordonnées sexagésimales (deux-points, signe sur zéro degré)', abs(ra - 80.89375) < 1e-4 and abs(dec + 0.5) < 1e-9)


def test_ecarts():
    rng = np.random.default_rng(1)
    n = 3000
    lp = rng.uniform(0, 1.2, n)
    mode = np.where(rng.uniform(size=n) < 0.5, 'F', '1O')
    vrai = rng.normal(0, 0.15, n)
    w = np.where(mode == 'F', 16.0 - 3.3 * lp, 15.5 - 3.4 * lp) + vrai
    w[:20] += 3.0                                          # 20 intrus (mauvaise classe) : doivent être écartés
    d = P.ecarts_pw(lp, w, mode)
    verifier('relation P-W : intrus écartés', np.isnan(d[:20]).all())
    ok = np.isfinite(d)
    verifier('relation P-W : écarts retrouvés', np.corrcoef(d[ok], vrai[ok])[0, 1] > 0.99 and abs(P.robuste(d[ok]) - 0.15) < 0.01, f'{P.robuste(d[ok]):.3f}')


def test_poser():
    rng = np.random.default_rng(2)
    D0 = 62.4
    ra, dec = rng.uniform(5, 25, 8000), rng.uniform(-76, -70, 8000)
    dirs = P.direction_eq(ra, dec) @ P.A_G.T
    est = (ra - 15) * math.cos(math.radians(73)) * D0 * math.pi / 180    # kpc vers l'est
    vrai = D0 - 0.5 * est                                                 # l'est plus proche
    sig_pw = 0.10                                                         # mag
    dist = vrai * 10 ** (rng.normal(0, sig_pw, len(vrai)) / 5)
    ref = dict(dir=dirs, dist=dist, sig_pw_mag=sig_pw)
    traceurs = P.direction_eq(np.array([10.0, 20.0]), np.array([-73.0, -73.0])) @ P.A_G.T
    d, sig = P.poser(traceurs, D0, ref, np.random.default_rng(3))
    attendu = D0 - 0.5 * (np.array([10.0, 20.0]) - 15) * math.cos(math.radians(73)) * D0 * math.pi / 180
    verifier('pose : distance médiane locale', np.all(np.abs(d - attendu) < 2.0 + 3 * sig), f'{d.round(2)} contre {attendu.round(2)}')
    verifier('pose : largeur propre retirée (reste la pente sur la fenêtre)', np.all(sig < 0.6), f'{sig.round(2)}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for t in (test_sexa, test_ecarts, test_poser):
        t()
    print(f'\n{len(ECHECS)} échec(s)')
    sys.exit(1 if ECHECS else 0)
