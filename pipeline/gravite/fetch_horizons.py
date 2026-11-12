#!/usr/bin/env python3
"""Références JPL Horizons (éphéméride DE440/DE441) pour la gravité mutuelle.

Écrit app/test/nbody_ref.json :
  - états (position UA, vitesse UA/jour), barycentre du système solaire, écliptique J2000,
    pour le Soleil, les barycentres des planètes, Pluton, et Cérès, Vesta, Pallas, Hygie ;
  - à l'époque de départ et à plusieurs dates de contrôle (1650 à 2450).
Source : https://ssd.jpl.nasa.gov/api/horizons.api (Giorgini et al., JPL).
"""
import json, re, sys, time, urllib.parse, urllib.request, os

API = 'https://ssd.jpl.nasa.gov/api/horizons.api'
BODIES = [('sun', '10'), ('mercury', '1'), ('venus', '2'), ('emb', '3'), ('earth', '399'), ('moon', '301'), ('mars', '4'), ('jupiter', '5'),
          ('saturn', '6'), ('uranus', '7'), ('neptune', '8'), ('pluto', '9'),
          ('ceres', '1;'), ('vesta', '4;'), ('pallas', '2;'), ('hygiea', '10;')]
EPOCH = '2026-11-10'
CHECKS = ['1650-01-01', '1850-01-01', '2000-01-01', '2126-11-10', '2350-01-01', '2450-01-01']


def get(cmd, date):
    q = {'format': 'text', 'COMMAND': f"'{cmd}'", 'OBJ_DATA': "'NO'", 'MAKE_EPHEM': "'YES'", 'EPHEM_TYPE': "'VECTORS'",
         'CENTER': "'500@0'", 'TLIST': f"'{date}'", 'TLIST_TYPE': "'CAL'", 'TIME_TYPE': "'TDB'", 'REF_PLANE': "'ECLIPTIC'",
         'REF_SYSTEM': "'ICRF'", 'VEC_TABLE': "'2'", 'OUT_UNITS': "'AU-D'", 'CSV_FORMAT': "'YES'"}
    for k in range(4):
        try:
            t = urllib.request.urlopen(API + '?' + urllib.parse.urlencode(q), timeout=60).read().decode()
            m = re.search(r'\$\$SOE\s*(.*?)\$\$EOE', t, re.S)
            if not m: raise RuntimeError(t[:300])
            r = [s.strip() for s in m.group(1).strip().split('\n')[0].split(',')]
            return {'jd': float(r[0]), 'r': [float(x) for x in r[2:5]], 'v': [float(x) for x in r[5:8]]}
        except Exception as e:
            err = e; time.sleep(2 ** k)
    raise SystemExit(f'Horizons {cmd} {date} : {err}')


out = {'source': 'JPL Horizons, barycentre du système solaire, écliptique J2000, TDB, UA et UA/jour', 'epoch': {}, 'checks': {}}
for name, cmd in BODIES:
    out['epoch'][name] = get(cmd, EPOCH)
    for d in CHECKS:
        out['checks'].setdefault(d, {})[name] = get(cmd, d)
    print(name, 'ok', flush=True)
dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'test', 'nbody_ref.json')
json.dump(out, open(dst, 'w'), indent=0)
print('écrit', dst)
