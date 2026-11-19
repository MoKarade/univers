#!/usr/bin/env python3
"""Résumé de notre tir GPU (json de stabilite_tir.py) aux mêmes instants que le tir GADGET-4 : A2 par anneau, épaisseur
(anneau 4–6 kpc, plan xy, sortes 1+4), vitesse de la barre (angle de l'anneau 2–4 kpc, relevés de 10 Ma, moyenne sur 100 Ma).
Usage : python resume_gpu.py <tir.json>"""
import json
import sys

import numpy as np

KMS_KPC = 1.0227121650456
r = json.load(open(sys.argv[1], encoding='utf-8'))['releves']
t = np.array([x['t'] for x in r])
ang = np.radians([x['anneaux'][1]['angle_deg'] if x['anneaux'][1] else np.nan for x in r])
om = np.full(len(r), np.nan)
for i in range(1, len(r)):
    d = (ang[i] - ang[i - 1] + np.pi / 2) % np.pi - np.pi / 2
    om[i] = d / (t[i] - t[i - 1]) / KMS_KPC
for tc in (0, 0.25, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
    i = int(np.argmin(abs(t - tc))); a = r[i]['anneaux']; w = (abs(t - tc) <= 0.05) & (t > 0)
    print(f"t={t[i]:.2f} A2=" + ' '.join(f"{x['a2']:.3f}" if x else '-' for x in a)
          + f" | ép.4-6={a[2]['epaisseur_kpc']} ép.6-9={a[3]['epaisseur_kpc']} | Ωb≈{np.nanmedian(om[w]) if w.any() else float('nan'):.1f} km/s/kpc | E={r[i]['energie']:+.2e}")
