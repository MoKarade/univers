#!/usr/bin/env python3
"""Affiche le contenu d'un départ GADGET-4 (depart.hdf5) : nombre de particules et masse par type. Usage : python3 info_depart.py <depart.hdf5>"""
import sys
import h5py
with h5py.File(sys.argv[1], 'r') as f:
    for k in sorted(f):
        if k.startswith('PartType'):
            print(k, len(f[k]['Masses']), '%.4e M☉' % (f[k]['Masses'][:].sum() * 1e10))
