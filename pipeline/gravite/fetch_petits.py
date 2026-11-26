#!/usr/bin/env python3
"""Références pour les petits corps (lot G, G3) : app/test/petits_ref.json.

- Rapprochements de la Terre publiés par le JPL (CNEOS, https://ssd-api.jpl.nasa.gov/cad.api) : astéroïdes de
  plus de ≈ 300 m (H ≤ 21) passant à moins de 0,01 UA d'ici 2045.
- État de départ de chacun (héliocentrique, écliptique J2000, TDB, UA et UA/jour) à l'époque du calcul,
  par JPL Horizons, plus la comète de Halley et son périhélie de 2061 (éléments osculateurs Horizons).
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

_PIPE_DIR = str(Path(__file__).resolve().parents[1])
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import APP_TEST  # noqa: E402

H = 'https://ssd.jpl.nasa.gov/api/horizons.api'
EPOCH = '2026-11-10'


def fetch(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read().decode('utf-8')
        except Exception as e:
            err = e; time.sleep(2 ** k)
    raise SystemExit(f'{url[:120]} : {err}')


def horizons(cmd, **kw):
    q = {'format': 'text', 'COMMAND': f"'{cmd}'", 'OBJ_DATA': "'NO'", 'MAKE_EPHEM': "'YES'", 'CENTER': "'500@10'",
         'REF_PLANE': "'ECLIPTIC'", 'REF_SYSTEM': "'ICRF'", 'OUT_UNITS': "'AU-D'", 'CSV_FORMAT': "'YES'", 'TIME_TYPE': "'TDB'"}
    q.update({k: f"'{v}'" for k, v in kw.items()})
    t = fetch(H + '?' + urllib.parse.urlencode(q))
    m = re.search(r'\$\$SOE\s*(.*?)\$\$EOE', t, re.S)
    if not m: raise SystemExit(f'Horizons {cmd} : {t[:400]}')
    return [[s.strip() for s in l.split(',')] for l in m.group(1).strip().split('\n')]


def state(cmd):
    r = horizons(cmd, EPHEM_TYPE='VECTORS', VEC_TABLE='2', TLIST=EPOCH, TLIST_TYPE='CAL')[0]
    return {'jd': float(r[0]), 'r': [float(x) for x in r[2:5]], 'v': [float(x) for x in r[5:8]]}


def geo_min(cmd, jd):
    """Plus courte distance à la Terre selon Horizons (même solution d'orbite que l'état de départ), pas d'une minute."""
    rows = horizons(cmd, EPHEM_TYPE='VECTORS', VEC_TABLE='3', CENTER='500@399', START_TIME=f'JD{jd - 0.03:.6f}', STOP_TIME=f'JD{jd + 0.03:.6f}', STEP_SIZE='1 m', OUT_UNITS='KM-S')
    pts = [(float(r[0]), float(r[9])) for r in rows]
    k = min(range(1, len(pts) - 1), key=lambda i: pts[i][1])
    (t0, d0), (t1, d1), (t2, d2) = pts[k - 1:k + 2]
    a = ((d2 - d1) / (t2 - t1) - (d1 - d0) / (t1 - t0)) / (t2 - t0); b = (d1 - d0) / (t1 - t0) - a * (t0 + t1)
    tm = -b / (2 * a); return tm, d1 + (tm - t1) * (a * (tm + t1) + b)


def main(dst=None):
    cad = json.loads(fetch('https://ssd-api.jpl.nasa.gov/cad.api?dist-max=0.01&date-min=2026-12-01&date-max=2045-01-01&h-max=21&sort=dist'))
    f = cad['fields']
    out = {'source': 'JPL CNEOS (cad.api) et JPL Horizons ; héliocentrique, écliptique J2000, TDB', 'neo': [], 'comets': {}}
    for row in cad['data']:
        d = dict(zip(f, row)); des = d['des']
        cmd = f'{des};' if des.isdigit() else f'DES={des};'
        out['neo'].append({'des': des, 'cad_jd_tdb': float(d['jd']), 'cad_date': d['cd'], 'cad_dist_au': float(d['dist']),
                           'cad_dist_min': float(d['dist_min']), 'cad_dist_max': float(d['dist_max']), 'cad_orbit_id': d['orbit_id'], 'state': state(cmd)})
        out['neo'][-1]['hz_min_jd_tdb'], out['neo'][-1]['hz_min_km'] = geo_min(cmd, float(d['jd']))
        print(des, 'ok', flush=True)
    # Comète de Halley : solution la plus proche de 2061 (CAP), état en 2026, puis périhélie de 2061.
    hal = 'DES=1P;CAP;NOFRAG'
    el = horizons(hal, EPHEM_TYPE='ELEMENTS', TLIST='2061-07-01', TLIST_TYPE='CAL')[0]
    # colonnes ELEMENTS : JDTDB, date, EC, QR, IN, OM, W, Tp, N, MA, TA, A, AD, PR
    out['comets']['1P/Halley'] = {'state': state(hal), 'tp_2061_jd_tdb': float(el[7]), 'q_au': float(el[3]), 'e': float(el[2])}
    print('Halley ok', el[7])
    target = Path(dst) if dst else APP_TEST / 'petits_ref.json'
    with open(target, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(out, fh, indent=0)
    print('écrit', target)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
