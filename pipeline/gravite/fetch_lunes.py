#!/usr/bin/env python3
"""Références JPL Horizons pour les lunes galiléennes (lot G, lunes) : app/test/lunes_ref.json.
États (km, km/s) relatifs au centre de Jupiter (500@599), écliptique J2000, TDB, à l'époque de départ et à des dates de contrôle."""
import json, os, re, time, urllib.parse, urllib.request
H = 'https://ssd.jpl.nasa.gov/api/horizons.api'
EPOCH, CHECKS = '2026-11-10', ['1976-11-10', '2016-11-10', '2027-11-10', '2036-11-10', '2076-11-10']
def state(cmd, date, center='500@599'):
    q = {'format': 'text', 'COMMAND': f"'{cmd}'", 'OBJ_DATA': "'NO'", 'MAKE_EPHEM': "'YES'", 'EPHEM_TYPE': "'VECTORS'", 'CENTER': f"'{center}'",
         'TLIST': f"'{date}'", 'TLIST_TYPE': "'CAL'", 'TIME_TYPE': "'TDB'", 'REF_PLANE': "'ECLIPTIC'", 'REF_SYSTEM': "'ICRF'", 'VEC_TABLE': "'2'", 'OUT_UNITS': "'KM-S'", 'CSV_FORMAT': "'YES'"}
    for k in range(4):
        try:
            t = urllib.request.urlopen(H + '?' + urllib.parse.urlencode(q), timeout=60).read().decode()
            r = [s.strip() for s in re.search(r'\$\$SOE\s*(.*?)\$\$EOE', t, re.S).group(1).strip().split('\n')[0].split(',')]
            return {'jd': float(r[0]), 'r': [float(x) for x in r[2:5]], 'v': [float(x) for x in r[5:8]]}
        except Exception as e:
            err = e; time.sleep(2 ** k)
    raise SystemExit(f'{cmd} {date} : {err}')
out = {'source': 'JPL Horizons, centre de Jupiter, écliptique J2000, TDB, km et km/s', 'epoch': {}, 'checks': {}}
for n, c in [('io', '501'), ('europa', '502'), ('ganymede', '503'), ('callisto', '504')]:
    out['epoch'][n] = state(c, EPOCH)
    for d in CHECKS: out['checks'].setdefault(d, {})[n] = state(c, d)
    print(n, 'ok', flush=True)
dst = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'test', 'lunes_ref.json')
json.dump(out, open(dst, 'w'), indent=0); print('écrit', dst)
