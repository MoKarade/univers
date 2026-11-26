#!/usr/bin/env python3
"""Met à plat app/test/nbody_ref.json (JPL Horizons) pour le contrôle du lecteur d'éphémérides de l'appli PC :
une ligne « nom jour_julien x y z vx vy vz » par corps et par date. Usage : python ref_ephem.py <sortie.txt>"""
import json, sys
from pathlib import Path

_PIPE_DIR = str(Path(__file__).resolve().parents[1])
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import APP_TEST, REPO_ROOT  # noqa: E402

ROOT = str(REPO_ROOT)


def main():
    with open(APP_TEST / 'nbody_ref.json', encoding='utf-8') as fh:
        d = json.load(fh)
    groups = [d['epoch']] + list(d['checks'].values())
    with open(sys.argv[1], 'w', encoding='ascii', newline='\n') as f:
        n = 0
        for g in groups:
            for name, s in g.items():
                if not isinstance(s, dict) or 'r' not in s: continue
                f.write(' '.join([name, repr(s['jd'])] + [repr(x) for x in s['r'] + s['v']]) + '\n'); n += 1
    print(n, 'lignes')


if __name__ == '__main__':
    main()
