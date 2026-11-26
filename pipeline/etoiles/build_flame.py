#!/usr/bin/env python3
"""Fichier joint flame_hip.txt (base64) : âges et masses Gaia FLAME des étoiles Hipparcos (pipeline/raw/flame_hip.csv).
Ligne de 16 octets par étoile, triée par numéro Hipparcos : Int32 hip ; Uint16 âge, âge bas, âge haut (millions d'années) ;
Uint16 masse, masse basse, masse haute (millièmes de masse solaire). Seules les solutions sans alerte (flags_flame commençant par 0).
Usage : python build_flame.py <sortie.txt>"""
import base64, csv, os, struct, sys
from pathlib import Path

_PIPE_DIR = str(Path(__file__).resolve().parents[1])
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import PIPELINE_RAW  # noqa: E402


def main(dst):
    src = PIPELINE_RAW / 'flame_hip.csv'
    rows = []
    with open(src, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            try:
                if not r['flags_flame'].startswith('0'): continue
                v = [float(r[k]) for k in ('age_flame', 'age_flame_lower', 'age_flame_upper', 'mass_flame', 'mass_flame_lower', 'mass_flame_upper')]
                rows.append((int(r['hip']), [min(65535, round(x * 1000)) for x in v]))
            except (ValueError, KeyError):
                continue
    rows.sort()
    b = b''.join(struct.pack('<i6H', h, *v) for h, v in rows)
    with open(dst, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(base64.b64encode(b).decode())
    print(len(rows), 'étoiles', os.path.getsize(dst), 'octets')


if __name__ == '__main__':
    main(sys.argv[1])
