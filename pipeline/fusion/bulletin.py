#!/usr/bin/env python3
"""Bulletin de la galaxie du calcul contre les mesures de la Voie lactée (Marc, 18/11/2026 : « sois plus précis »).

Pour chaque mesure de resultats/mesures_voie_lactee.json : la valeur du calcul, l'écart en nombre de marges d'erreur,
et le verdict (dans la marge si l'écart est sous 1, proche sous 2, hors marge au-delà).

Usage : python bulletin.py <galaxie.npz> [<tir.json de stabilite_tir.py>]
"""
import json
import math
import os
import sys

import numpy as np

R0 = 8.2
G = 4.30091e-6


def vitesse_circulaire(pos, m, r, azimuts=8, eps=0.1):
    ar = 0.0
    pos = pos.astype(np.float32); mg = (m * G).astype(np.float32)
    for a in np.arange(azimuts) * 2 * math.pi / azimuts:
        x = np.array([r * math.cos(a), r * math.sin(a), 0.0], np.float32)
        d = pos - x; d3 = ((d * d).sum(1) + np.float32(eps * eps)) ** np.float32(1.5)
        ar += float(((mg / d3) * (d[:, 0] * x[0] + d[:, 1] * x[1])).sum()) / r
    return math.sqrt(max(-ar / azimuts * r, 0.0))


def main():
    with np.load(sys.argv[1]) as z:
        pos, vel, m, kind = z['pos'].astype(float), z['vel'].astype(float), z['m'].astype(float), z['kind']
    et = (kind == 1) | (kind == 4)
    c = np.median(pos[et], 0)
    for rr in (10.0, 5.0, 2.0, 1.0):
        d = np.linalg.norm(pos[et] - c, axis=1); c = pos[et][d < rr].mean(0)
    d = np.linalg.norm(pos[et] - c, axis=1); cv = vel[et][d < 1.0].mean(0)
    x = pos - c; v = vel - cv
    R = np.hypot(x[:, 0], x[:, 1]); phi = np.arctan2(x[:, 1], x[:, 0]); vR = (x[:, 0] * v[:, 0] + x[:, 1] * v[:, 1]) / np.maximum(R, 1e-9)
    calc = {}
    # barre : phase du motif à deux bras par anneau de 0,5 kpc ; la barre finit là où la phase s'écarte de plus de 10° de
    # celle du centre ou où la force tombe sous 0,1
    etoiles = (kind == 1) | (kind == 4) | (kind == 5)
    ph0, fin = None, 0.0
    for a in np.arange(1.0, 12.0, 0.5):
        s = etoiles & (R >= a) & (R < a + 0.5)
        z2 = np.mean(np.exp(2j * phi[s])); p = math.degrees(np.angle(z2)) / 2
        if ph0 is None: ph0 = p
        ecart = (p - ph0 + 90) % 180 - 90
        if abs(z2) < 0.1 or abs(ecart) > 10: break
        fin = a + 0.5
    calc['barre_demi_longueur_kpc'] = fin
    sol = (R > R0 - 0.5) & (R < R0 + 0.5)
    for nom, k in (('disque_mince_hauteur_kpc', 1), ('disque_epais_hauteur_kpc', 4)):
        s = sol & (kind == k)
        if s.sum() > 100: calc[nom] = float(np.median(np.abs(x[s, 2] - np.median(x[s, 2]))) / math.log(2.0))      # disque exponentiel : médiane de |z| = h ln 2
    s = sol & (kind == 1)
    calc['agitation_radiale_soleil_kms'] = float(vR[s].std())
    calc['vitesse_circulaire_soleil_kms'] = vitesse_circulaire(x, m, R0)
    calc['masse_gaz_msol'] = float(m[kind == 3].sum())
    calc['masse_etoiles_msol'] = float(m[(kind == 1) | (kind == 2) | (kind == 4) | (kind == 5)].sum())
    if len(sys.argv) > 2:
        rel = json.load(open(sys.argv[2], encoding='utf-8'))['releves']
        t = np.array([r['t'] for r in rel]); ang = np.array([r['anneaux'][1]['angle_deg'] for r in rel])
        u = np.unwrap(np.radians(ang) * 2) / 2; n = min(len(t) - 1, 20)
        calc['barre_vitesse_kms_kpc'] = float(abs(np.polyfit(t[-n:], u[-n:], 1)[0]) / 1.0227121650456)
        g = [r['gaz'] for r in rel if 'gaz' in r]
        if len(g) > 11: calc['naissance_etoiles_msol_an'] = float((g[-1]['nees_msol'] - g[-11]['nees_msol']) / ((g[-1]['t'] - g[-11]['t']) * 1e9))
    M = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resultats', 'mesures_voie_lactee.json'), encoding='utf-8'))['mesures']
    print(f"{'mesure':34s} {'mesuré':>12s} {'marge':>10s} {'calcul':>12s} {'écart':>8s}  verdict")
    bilan = {}
    for nom, q in M.items():
        if nom not in calc: print(f'{nom:34s} {q["valeur"]:12.4g} {q["marge"]:10.3g} {"—":>12s}'); continue
        e = (calc[nom] - q['valeur']) / q['marge']
        verdict = 'dans la marge' if abs(e) <= 1 else ('proche' if abs(e) <= 2 else 'HORS MARGE')
        bilan[nom] = dict(calcul=calc[nom], ecart_en_marges=e, verdict=verdict)
        print(f'{nom:34s} {q["valeur"]:12.4g} {q["marge"]:10.3g} {calc[nom]:12.4g} {e:+8.1f}  {verdict}')
    return bilan


if __name__ == '__main__':
    main()
