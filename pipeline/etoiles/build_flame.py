#!/usr/bin/env python3
"""Fichier joint flame_hip.txt (base64) : âges et masses Gaia FLAME des étoiles Hipparcos (pipeline/raw/flame_hip.csv).
Ligne de 16 octets par étoile, triée par numéro Hipparcos : Int32 hip ; Uint16 âge, âge bas, âge haut (millions d'années) ;
Uint16 masse, masse basse, masse haute (millièmes de masse solaire). Seules les solutions sans alerte (flags_flame commençant par 0).
Usage : python build_flame.py <sortie.txt>"""
import base64, csv, os, struct, sys
src = os.path.join(os.path.dirname(__file__), '..', 'raw', 'flame_hip.csv')
rows = []
for r in csv.DictReader(open(src)):
    try:
        if not r['flags_flame'].startswith('0'): continue
        v = [float(r[k]) for k in ('age_flame', 'age_flame_lower', 'age_flame_upper', 'mass_flame', 'mass_flame_lower', 'mass_flame_upper')]
        rows.append((int(r['hip']), [min(65535, round(x * 1000)) for x in v]))
    except (ValueError, KeyError):
        continue
rows.sort()
b = b''.join(struct.pack('<i6H', h, *v) for h, v in rows)
open(sys.argv[1], 'w').write(base64.b64encode(b).decode())
print(len(rows), 'étoiles', os.path.getsize(sys.argv[1]), 'octets')
