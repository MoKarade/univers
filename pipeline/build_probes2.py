from datetime import datetime, timedelta
import base64, json, pickle, sys, time
from pathlib import Path
import numpy as np

_PIPE_DIR = str(Path(__file__).resolve().parent)
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import APP_GEN, PIPELINE_RAW  # noqa: E402
from fetch_probes2 import vec  # noqa: E402

f = lambda d: d.strftime('%Y-%m-%d %H:%M')


def encounter(cmd, body, bid, when):
    t = datetime.strptime(when, '%Y-%m-%d %H:%M'); a = vec(cmd, '500@' + bid, f(t - timedelta(days=4)), f(t + timedelta(days=4)), '1 h'); b = vec(cmd, '500@' + bid, f(t - timedelta(hours=8)), f(t + timedelta(hours=8)), '10 m')
    if a is None or b is None or isinstance(a, tuple) or isinstance(b, tuple): return None
    m = np.vstack([a[(a[:, 0] < b[0, 0]) | (a[:, 0] > b[-1, 0])], b]); m = m[np.argsort(m[:, 0])]; d = np.linalg.norm(b[:, 1:4], axis=1); i = min(max(int(np.argmin(d)), 1), len(b) - 2); tt = np.linspace(b[i - 1, 0], b[i + 1, 0], 4001)
    def herm(t):
        k = i - 1 if t < b[i, 0] else i; h = b[k + 1, 0] - b[k, 0]; u = (t - b[k, 0]) / h; return (2*u**3 - 3*u**2 + 1) * b[k, 1:4] + (u**3 - 2*u**2 + u) * h * b[k, 4:7] + (-2*u**3 + 3*u**2) * b[k + 1, 1:4] + (u**3 - u**2) * h * b[k + 1, 4:7]
    dd = np.array([np.linalg.norm(herm(t)) for t in tt]); j = int(np.argmin(dd)); return {'body': body, 'm': m, 'jd': float(tt[j]), 'km': float(dd[j] * 149597870.7)}


def cal(jd):
    return (datetime(2000, 1, 1, 12) + timedelta(days=jd - 2451545.0) - timedelta(seconds=60)).strftime('%Y-%m-%d %H:%M')


def main():
    pkl_path = PIPELINE_RAW / 'probes2.pkl'
    with open(pkl_path, 'rb') as fh:
        OUT = pickle.load(fh)
    for k in range(3):
        if 'Pioneer 10' in OUT and not OUT['Pioneer 10']['enc']:
            e = encounter('-23', 'jupiter', '599', '1973-12-04 02:26')
            if e: OUT['Pioneer 10']['enc'].append(e); print('Pioneer 10    jupiter  au plus près le %s TU, à %s km du centre (NASA : 1973-12-04 02:26)' % (cal(e['jd']), format(int(round(e['km'])), ',')))
        if 'New Horizons' not in OUT:
            base = vec('-98', '500@10', '2006-01-20', '2016-03-01', '4 d')
            if isinstance(base, tuple): base = vec('-98', '500@10', f(datetime.strptime(base[1].title(), '%Y-%b-%d %H:%M') + timedelta(hours=1)), '2016-03-01', '4 d')
            if base is not None and not isinstance(base, tuple):
                ent = {'jd0': float(base[0, 0]), 'n': int(len(base)), 'base': base, 'enc': []}
                for body, bid, when in [('jupiter', '599', '2007-02-28 05:43'), ('pluto', '999', '2015-07-14 11:49')]:
                    e = encounter('-98', body, bid, when)
                    if e: ent['enc'].append(e); print('New Horizons  %-8s au plus près le %s TU, à %s km du centre (NASA : %s)' % (body, cal(e['jd']), format(int(round(e['km'])), ','), when))
                OUT['New Horizons'] = ent; print('New Horizons  croisière : %d points' % len(base))
        if OUT.get('Pioneer 10', {}).get('enc') and 'New Horizons' in OUT and len(OUT['New Horizons']['enc']) == 2: break
        time.sleep(4)
    with open(pkl_path, 'wb') as fh:
        pickle.dump(OUT, fh)
    b64 = lambda a: base64.b64encode(np.ascontiguousarray(a, dtype='<f4').tobytes()).decode(); D = {}
    for name, ent in OUT.items():
        b = ent['base'].copy(); b[:, 0] -= ent['jd0']; D[name] = {'jd0': ent['jd0'], 'jd1': float(ent['base'][-1, 0]), 'b': b64(b), 'enc': []}
        for e in ent['enc']:
            m = e['m'].copy(); m[:, 0] -= e['jd']; D[name]['enc'].append({'body': e['body'], 'jdc': e['jd'], 'km': round(e['km']), 't0': float(e['m'][0, 0]), 't1': float(e['m'][-1, 0]), 'b': b64(m)})
    v1_path = PIPELINE_RAW / 'v1_lightday.json'
    if v1_path.exists():
        with open(v1_path, encoding='utf-8') as fh:
            LD = json.load(fh)['cross']
    else:
        LD = []
    out_path = APP_GEN / 'data10.js'
    with open(out_path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('Object.assign(DATA, ' + json.dumps({'PTRAJ': D, 'V1_LIGHTDAY': LD[0] if LD else None}, separators=(',', ':')) + ');\n')
    print('data10.js : %.0f ko | sondes : %s' % (out_path.stat().st_size / 1024, ', '.join('%s (%d survols)' % (k, len(v['enc'])) for k, v in D.items())))


if __name__ == '__main__':
    main()
