# Trajectoires réelles des sondes (JPL Horizons) : croisière vue du Soleil, survols vus de la planète survolée.
import requests, json, time, re, sys, base64, numpy as np
UA = {'User-Agent': 'UniversArtifactBuilder/2.0 (educational visualization)'}; API = 'https://ssd.jpl.nasa.gov/api/horizons.api'; T0 = time.time()
def vec(cmd, center, start, stop, step):
    p = {'format': 'text', 'COMMAND': "'%s'" % cmd, 'OBJ_DATA': "'NO'", 'MAKE_EPHEM': "'YES'", 'EPHEM_TYPE': "'VECTORS'", 'CENTER': "'%s'" % center, 'START_TIME': "'%s'" % start, 'STOP_TIME': "'%s'" % stop, 'STEP_SIZE': "'%s'" % step,
         'REF_PLANE': "'ECLIPTIC'", 'REF_SYSTEM': "'ICRF'", 'VEC_TABLE': "'2'", 'OUT_UNITS': "'AU-D'", 'CSV_FORMAT': "'YES'", 'VEC_LABELS': "'NO'"}
    for k in range(3):
        try:
            r = requests.get(API, params=p, headers=UA, timeout=60); t = r.text
            if '$$SOE' in t:
                rows = [l.split(',') for l in t.split('$$SOE')[1].split('$$EOE')[0].strip().split('\n')]; return np.array([[float(q[0])] + [float(x) for x in q[2:8]] for q in rows])
            m = re.search(r'prior to A\.D\. (\d{4}-[A-Z]{3}-\d{2} \d{2}:\d{2})', t)
            if m: return ('early', m.group(1))
            print('  réponse inattendue', cmd, start, t[-300:].replace('\n', ' ')[:200]); return None
        except Exception as e: time.sleep(2)
    return None
PR = [('Voyager 1', '-31', '1977-09-06', '1981-03-01', '2 d', [('jupiter', '599', '1979-03-05 12:05'), ('saturn', '699', '1980-11-12 23:46')]),
      ('Voyager 2', '-32', '1977-08-21', '1990-01-01', '3 d', [('jupiter', '599', '1979-07-09 22:29'), ('saturn', '699', '1981-08-26 03:24'), ('uranus', '799', '1986-01-24 17:59'), ('neptune', '899', '1989-08-25 03:56')]),
      ('Pioneer 10', '-23', '1972-03-04', '1974-06-01', '2 d', [('jupiter', '599', '1973-12-04 02:26')]),
      ('Pioneer 11', '-24', '1973-04-07', '1980-03-01', '3 d', [('jupiter', '599', '1974-12-03 05:22'), ('saturn', '699', '1979-09-01 16:31')]),
      ('New Horizons', '-98', '2006-01-20', '2016-03-01', '4 d', [('jupiter', '599', '2007-02-28 05:43'), ('pluto', '999', '2015-07-14 11:49')])]
from datetime import datetime, timedelta
OUT = {}; f = lambda d: d.strftime('%Y-%m-%d %H:%M')
for name, cmd, s, e, step, enc in PR:
    base = vec(cmd, '500@10', s, e, step)
    if isinstance(base, tuple): s2 = datetime.strptime(base[1].title(), '%Y-%b-%d %H:%M') + timedelta(hours=1); base = vec(cmd, '500@10', f(s2), e, step); print('  début réel des données :', f(s2))
    if base is None or isinstance(base, tuple): print(name, 'ÉCHEC croisière'); continue
    ent = {'jd0': float(base[0, 0]), 'n': int(len(base)), 'base': base, 'enc': []}
    for body, bid, when in enc:
        t = datetime.strptime(when, '%Y-%m-%d %H:%M'); a = vec(cmd, '500@' + bid, f(t - timedelta(days=4)), f(t + timedelta(days=4)), '1 h'); b = vec(cmd, '500@' + bid, f(t - timedelta(hours=8)), f(t + timedelta(hours=8)), '10 m')
        if a is None or b is None or isinstance(a, tuple) or isinstance(b, tuple): print(name, body, 'ÉCHEC survol'); continue
        m = np.vstack([a[(a[:, 0] < b[0, 0]) | (a[:, 0] > b[-1, 0])], b]); m = m[np.argsort(m[:, 0])]
        # passage au plus près : interpolation fine autour du minimum des points à 10 minutes
        d = np.linalg.norm(b[:, 1:4], axis=1); i = int(np.argmin(d)); i = min(max(i, 1), len(b) - 2); tt = np.linspace(b[i - 1, 0], b[i + 1, 0], 4001); dt = (b[i + 1, 0] - b[i - 1, 0]) / 2
        def herm(t):
            k = i - 1 if t < b[i, 0] else i; h = b[k + 1, 0] - b[k, 0]; u = (t - b[k, 0]) / h; return (2*u**3 - 3*u**2 + 1) * b[k, 1:4] + (u**3 - 2*u**2 + u) * h * b[k, 4:7] + (-2*u**3 + 3*u**2) * b[k + 1, 1:4] + (u**3 - u**2) * h * b[k + 1, 4:7]
        dd = np.array([np.linalg.norm(herm(t)) for t in tt]); j = int(np.argmin(dd)); jd = float(tt[j]); dkm = float(dd[j] * 149597870.7)
        cal = datetime(2000, 1, 1, 12) + timedelta(days=jd - 2451545.0) - timedelta(seconds=69.184 if jd > 2451545 else 50)
        ent['enc'].append({'body': body, 'm': m, 'jd': jd, 'km': dkm}); print('%-13s %-8s au plus près le %s TU, à %s km du centre (NASA : %s)' % (name, body, cal.strftime('%Y-%m-%d %H:%M'), format(int(round(dkm)), ','), when))
    OUT[name] = ent; print('%-13s croisière : %d points de %s à %s | %.0f s' % (name, len(base), s, e, time.time() - T0))
import pickle; pickle.dump(OUT, open('raw/probes2.pkl', 'wb'))
# distance Terre – Voyager 1 : date où elle atteint un jour-lumière (25 902 068 371 km)
try:
    v = vec('-31', '500@399', '2026-10-01', '2027-03-01', '1 d'); d = np.linalg.norm(v[:, 1:4], axis=1) * 149597870.7; LD = 299792.458 * 86400; k = np.where((d[:-1] < LD) & (d[1:] >= LD))[0]
    for i in k: jd = v[i, 0] + (LD - d[i]) / (d[i + 1] - d[i]); cal = datetime(2000, 1, 1, 12) + timedelta(days=jd - 2451545.0); print('Voyager 1 à un jour-lumière de la Terre : JD %.3f = %s TU' % (jd, cal.strftime('%Y-%m-%d %H:%M')))
    print('   distances (jours-lumière) : 1er oct. 2026 %.5f | 11 nov. 2026 %.5f | 1er mars 2027 %.5f | nombre de franchissements : %d' % (d[0] / LD, d[41] / LD, d[-1] / LD, len(k)))
    json.dump({'cross': [float(v[i, 0] + (LD - d[i]) / (d[i + 1] - d[i])) for i in k]}, open('raw/v1_lightday.json', 'w'))
except Exception as ex: print('jour-lumière : échec', ex)
