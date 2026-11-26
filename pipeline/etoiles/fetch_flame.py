#!/usr/bin/env python3
"""Âges et masses mesurés par Gaia DR3 (module FLAME, Gaia Collaboration, Creevey et al. 2023) pour les étoiles Hipparcos,
par la table de correspondance gaiadr3.hipparcos2_best_neighbour. Archive de l'ESA (TAP).
Écrit pipeline/raw/flame_hip.csv : hip, age_flame (Ga) et bornes à 16 % et 84 %, mass_flame (M☉) et bornes, flags_flame, evolstage_flame."""
import sys, urllib.parse, urllib.request
from pathlib import Path

_PIPE_DIR = str(Path(__file__).resolve().parents[1])
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import PIPELINE_RAW  # noqa: E402

Q = ("SELECT h.original_ext_source_id AS hip, a.age_flame, a.age_flame_lower, a.age_flame_upper, a.mass_flame, a.mass_flame_lower, "
     "a.mass_flame_upper, a.flags_flame, a.evolstage_flame FROM gaiadr3.hipparcos2_best_neighbour AS h "
     "JOIN gaiadr3.astrophysical_parameters AS a ON a.source_id = h.source_id WHERE a.age_flame IS NOT NULL")


def main():
    d = urllib.parse.urlencode({'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'csv', 'MAXREC': 200000, 'QUERY': Q}).encode()
    with urllib.request.urlopen(urllib.request.Request('https://gea.esac.esa.int/tap-server/tap/sync', data=d), timeout=600) as r:
        t = r.read().decode('utf-8')
    dst = PIPELINE_RAW / 'flame_hip.csv'
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, 'w', encoding='utf-8', newline='\n') as f:
        f.write(t)
    print('écrit', dst, t.count('\n') - 1, 'étoiles')


if __name__ == '__main__':
    main()
