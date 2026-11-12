#!/usr/bin/env python3
"""Références des passages de Mercure et Vénus devant le Soleil, 2026 à 2200 : catalogue de la NASA (F. Espenak),
https://eclipse.gsfc.nasa.gov/transit/catalog/MercuryCatalog.html et VenusCatalog.html (copies dans pipeline/raw/transits/).
Colonnes lues : date, contacts I à IV et milieu (temps universel), séparation minimale des centres (″). Écrit app/test/transits_ref.json."""
import re, json, os
here = os.path.dirname(os.path.abspath(__file__)); raw = os.path.join(here, '..', 'raw', 'transits')
M = {m: i + 1 for i, m in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split())}
out = {'source': 'NASA GSFC, catalogues de F. Espenak (temps universel)', 'mercury': [], 'venus': []}
for key, f in (('mercury', 'MercuryCatalog.html'), ('venus', 'VenusCatalog.html')):
    t = re.sub('<[^>]+>', '', open(os.path.join(raw, f), encoding='latin-1').read())
    for l in t.split('\n'):
        m = re.match(r'\s*(\d{4})\s+(\w{3})\s+(\d+)\s+(\d\d:\d\d)\s+(\d\d:\d\d)\s+(\d\d:\d\d)\s+(\d\d:\d\d)\s+(\d\d:\d\d)\s+([\d.]+)', l)
        if not m or not (2026 <= int(m[1]) <= 2200): continue
        out[key].append({'date': f'{m[1]}-{M[m[2]]:02d}-{int(m[3]):02d}', 'greatest_ut': m[6], 'sep_arcsec': float(m[9])})
json.dump(out, open(os.path.join(here, '..', '..', 'app', 'test', 'transits_ref.json'), 'w'), indent=0)
print({k: len(v) for k, v in out.items() if isinstance(v, list)})
