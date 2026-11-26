#!/usr/bin/env python3
"""Références JPL Horizons pour les lunes galiléennes (lot G, lunes) : app/test/lunes_ref.json.
États (km, km/s) relatifs au centre de Jupiter (500@599), écliptique J2000, TDB, à l'époque de départ et à des dates de contrôle."""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

_PIPE_DIR = str(Path(__file__).resolve().parents[1])
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import APP_TEST  # noqa: E402

H = 'https://ssd.jpl.nasa.gov/api/horizons.api'
EPOCH, CHECKS = '2026-11-10', ['1976-11-10', '2016-11-10', '2021-11-10', '2024-11-10', '2027-11-10', '2029-11-10', '2031-11-10', '2034-11-10', '2036-11-10', '2076-11-10']


def state(cmd, date, center='500@599'):
    q = {'format': 'text', 'COMMAND': f"'{cmd}'", 'OBJ_DATA': "'NO'", 'MAKE_EPHEM': "'YES'", 'EPHEM_TYPE': "'VECTORS'", 'CENTER': f"'{center}'",
         'TLIST': f"'{date}'", 'TLIST_TYPE': "'CAL'", 'TIME_TYPE': "'TDB'", 'REF_PLANE': "'ECLIPTIC'", 'REF_SYSTEM': "'ICRF'", 'VEC_TABLE': "'2'", 'OUT_UNITS': "'KM-S'", 'CSV_FORMAT': "'YES'"}
    for k in range(4):
        try:
            with urllib.request.urlopen(H + '?' + urllib.parse.urlencode(q), timeout=60) as resp:
                t = resp.read().decode('utf-8')
            m = re.search(r'\$\$SOE\s*(.*?)\$\$EOE', t, re.S)
            if not m:
                raise RuntimeError(t[:300])
            r = [s.strip() for s in m.group(1).strip().split('\n')[0].split(',')]
            return {'jd': float(r[0]), 'r': [float(x) for x in r[2:5]], 'v': [float(x) for x in r[5:8]]}
        except Exception as e:
            err = e; time.sleep(2 ** k)
    raise SystemExit(f'{cmd} {date} : {err}')


def main(dst=None):
    out = {'source': 'JPL Horizons, centre de Jupiter, écliptique J2000, TDB, km et km/s', 'epoch': {}, 'checks': {}}
    for n, c in [('io', '501'), ('europa', '502'), ('ganymede', '503'), ('callisto', '504')]:
        out['epoch'][n] = state(c, EPOCH)
        for d in CHECKS: out['checks'].setdefault(d, {})[n] = state(c, d)
        print(n, 'ok', flush=True)
    target = Path(dst) if dst else APP_TEST / 'lunes_ref.json'
    with open(target, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=0)
    print('écrit', target)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
