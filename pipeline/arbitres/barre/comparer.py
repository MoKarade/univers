#!/usr/bin/env python3
"""Tableau GADGET-4 (mesurer.py) face à notre tir GPU (stabilite_tir.py) aux mêmes instants.
Usage : python comparer.py <mesures_gadget.json> <tir_gpu.json>"""
import json
import sys

import numpy as np

KMS_KPC = 1.0227121650456
g = json.load(open(sys.argv[1], encoding='utf-8'))['releves']
r = json.load(open(sys.argv[2], encoding='utf-8'))['releves']


def omega_gpu(i):
    """Vitesse de la barre de notre tir : angle de l'anneau 2–4 kpc, relevés de 10 Ma, médiane sur ±50 Ma."""
    t = np.array([x['t'] for x in r]); ang = np.radians([x['anneaux'][1]['angle_deg'] if x['anneaux'][1] else np.nan for x in r])
    om = [((ang[k] - ang[k - 1] + np.pi / 2) % np.pi - np.pi / 2) / (t[k] - t[k - 1]) / KMS_KPC for k in range(1, len(r))]
    om = np.array([np.nan] + om); w = (abs(t - t[i]) <= 0.05) & (t > 0)
    return float(np.nanmedian(om[w])) if w.any() else float('nan')


def omega_g(tc):
    v = [x['vitesse_barre_kms_kpc'] for x in g if 'vitesse_barre_kms_kpc' in x and abs(x['t'] - tc) <= 0.06]
    return float(np.median(v)) if v else float('nan')


print('| t (Ga) | A2 0,5–2 / 2–4 / 4–6 kpc : GPU | GADGET-4 | Ωb (km/s/kpc) GPU | GADGET-4 | épaisseur 4–6 kpc, plan xy : GPU | GADGET-4 | GADGET-4 : A2 0,5–4, longueur, vieilles / jeunes (plan propre) |')
print('|---|---|---|---|---|---|---|---|')
for tc in (0, 0.25, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
    i = int(np.argmin([abs(x['t'] - tc) for x in r])); j = int(np.argmin([abs(x['t'] - tc) for x in g]))
    a, b = r[i]['anneaux'], g[j]['anneaux']
    f = lambda an: ' / '.join(f"{x['a2']:.2f}" for x in an[:3])
    print(f"| {tc:.2f} | {f(a)} | {f(b)} | {omega_gpu(i):.0f} | {omega_g(tc):.0f} | {a[2]['epaisseur_kpc']:.2f} | {b[2]['epaisseur_kpc']:.2f} | "
          f"{g[j]['a2_barre']:.2f}, {g[j]['longueur_barre_kpc']:.1f} kpc, {g[j]['vieilles_plan_propre_kpc']:.2f} / {g[j]['jeunes_plan_propre_kpc']:.2f} kpc |")
