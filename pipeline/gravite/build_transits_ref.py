#!/usr/bin/env python3
"""Références des passages de Mercure et Vénus devant le Soleil, 2026 à 2200 : catalogue de la NASA (F. Espenak),
https://eclipse.gsfc.nasa.gov/transit/catalog/MercuryCatalog.html et VenusCatalog.html (copies dans pipeline/raw/transits/).
Colonnes lues : date, contacts I à IV et milieu (temps universel), séparation minimale des centres (″). Écrit app/test/transits_ref.json."""
import json, re, sys
from pathlib import Path

_PIPE_DIR = str(Path(__file__).resolve().parents[1])
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import APP_TEST, PIPELINE_RAW  # noqa: E402

M = {m: i + 1 for i, m in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split())}


def main():
    raw = PIPELINE_RAW / 'transits'
    out = {'source': 'NASA GSFC, catalogues de F. Espenak (temps universel)', 'mercury': [], 'venus': []}
    for key, f in (('mercury', 'MercuryCatalog.html'), ('venus', 'VenusCatalog.html')):
        with open(raw / f, encoding='latin-1') as fh:
            t = re.sub('<[^>]+>', '', fh.read())
        for l in t.split('\n'):
            m = re.match(r'\s*(\d{4})\s+(\w{3})\s+(\d+)\s+(\d\d:\d\d)\s+(\d\d:\d\d)\s+(\d\d:\d\d)\s+(\d\d:\d\d)\s+(\d\d:\d\d)\s+([\d.]+)', l)
            if not m or not (2026 <= int(m[1]) <= 2200): continue
            out[key].append({'date': f'{m[1]}-{M[m[2]]:02d}-{int(m[3]):02d}', 'greatest_ut': m[6], 'sep_arcsec': float(m[9])})
    with open(APP_TEST / 'transits_ref.json', 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(out, fh, indent=0)
    print({k: len(v) for k, v in out.items() if isinstance(v, list)})


if __name__ == '__main__':
    main()
