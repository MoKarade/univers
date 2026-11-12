#!/usr/bin/env python3
"""Lot G natif : centres et traceurs du calcul complet de la fusion (fusion.json de pipeline/fusion/calcul.py) en binaire
pour natif/physique/groupe_local.h. Les images des étoiles (kf_NNN.bin) sont lues telles quelles.
Sortie : en-tête Float64 [version 1, n images, pas (Ga), nb galaxies 4, nb traceurs, quantum kpc, fusion_ga, dérive max,
nb étoiles mw, m31, m33, lmc], puis Float64 : centres n × 4 × 3 (repère du centre de masse, kpc), traceurs n × T × 3,
puis la liste des fichiers kf (nom sur 16 octets, nombre d'images en Float64).
Usage : python fusion_bin.py <dossier du calcul> <sortie.bin>"""
import json, os, struct, sys
src, dst = sys.argv[1], sys.argv[2]
m = json.load(open(os.path.join(src, 'fusion.json'), encoding='utf-8'))
n, T = len(m['t']), len(m['traceurs'])
hdr = [1, n, m['t'][1] - m['t'][0], 4, T, m['quantum_kpc'], float('nan') if m['fusion_ga'] is None else m['fusion_ga'], m['derive_max']] + m['affichees']      # pas de fusion (Voie lactée seule, calcul en cours) : NaN
b = struct.pack('<%dd' % len(hdr), *hdr)
b += struct.pack('<%dd' % (n * 12), *[x for c in m['centres'] for g in c for x in g])
b += struct.pack('<%dd' % (n * T * 3), *[x for c in m['traceurs_pos'] for g in c for x in g])
b += struct.pack('<d', len(m['fichiers']))
for f, k in m['fichiers']: b += f.encode().ljust(16, b'\0') + struct.pack('<d', k)
open(dst, 'wb').write(b); print('écrit', dst, len(b), 'octets ;', n, 'images,', T, 'traceurs')
