#!/usr/bin/env python3
"""Bilan court d'un tir GADGET-4 (mesures de mesurer.py) : vitesse de la barre à 0,5 / 1 / 1,5 Ga (médiane ±60 Ma),
A2 0,5–4 kpc, longueur, épaisseur 4–6 kpc (plan xy, comme stabilite_tir.py), au Soleil épaisseur du disque mince et
agitation radiale. Usage : python bilan.py <mesures.json> [<tir_gpu.json> pour la même ligne côté GPU]"""
import json
import sys

import numpy as np

g = json.load(open(sys.argv[1], encoding='utf-8'))['releves']
for tc in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
    if tc > g[-1]['t'] + 0.01:
        break
    j = int(np.argmin([abs(x['t'] - tc) for x in g])); x = g[j]
    om = [y['vitesse_barre_kms_kpc'] for y in g if 'vitesse_barre_kms_kpc' in y and abs(y['t'] - tc) <= 0.06]
    print(f"t={tc:.1f} Ga | Ωb={np.median(om) if om else float('nan'):.1f} km/s/kpc | A2(0,5–4)={x['a2_barre']:.2f} | L={x['longueur_barre_kpc']:.1f} kpc"
          f" | ép.4–6={x['anneaux'][2]['epaisseur_kpc']:.2f} kpc | Soleil : ép. mince={x['soleil_epaisseur_mince_kpc']:.2f} kpc, σR={x['soleil_sigma_r_kms']:.0f} km/s")
