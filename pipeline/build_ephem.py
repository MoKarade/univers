#!/usr/bin/env python3
"""Tronque les séries VSOP87 (source : PyMeeus, séries complètes) et valide planètes + Lune contre l'éphéméride JPL DE440."""
import json, math, sys, importlib, numpy as np, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
from astropy.time import Time
from astropy.coordinates import get_body_barycentric, solar_system_ephemeris
import astropy.units as u

_PIPE_DIR = str(Path(__file__).resolve().parent)
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import APP_GEN, APP_TEST, PIPELINE_DIR, PIPELINE_RAW  # noqa: E402

HERE = PIPELINE_DIR; RAW = PIPELINE_RAW; OUT = APP_GEN
AS = math.pi / 648000; EPS0 = 84381.448 * AS; AU_KM = 149597870.7
PL = [('mercury', 'Mercury', 0.387), ('venus', 'Venus', 0.723), ('earth', 'Earth', 1.0), ('mars', 'Mars', 1.524), ('jupiter', 'Jupiter', 5.203), ('saturn', 'Saturn', 9.537), ('uranus', 'Uranus', 19.19), ('neptune', 'Neptune', 30.07)]
FULL = {k: {c: [np.array(s, dtype=float).reshape(-1, 3) for s in getattr(importlib.import_module('pymeeus.' + m), 'VSOP87_' + c)] for c in 'LBR'} for k, m, a in PL}
def trunc(thr):
    out = {}
    for k, m, a in PL:
        out[k] = {}
        for c in 'LBR':
            t = thr * (a if c == 'R' else 1.0)
            out[k][c] = [s[np.abs(s[:, 0]) >= t] for s in FULL[k][c]]
    return out
count = lambda V: sum(len(s) for p in V.values() for c in p.values() for s in c)
def lbr(P, tau):
    r = []
    for c in 'LBR':
        tot, tp = 0.0, 1.0
        for s in P[c]:
            if len(s): tot += tp * float(np.sum(s[:, 0] * np.cos(s[:, 1] + s[:, 2] * tau)))
            tp *= tau
        r.append(tot * 1e-8)
    return r
def m_date_to_j2000(T):      # écliptique moyen de la date -> écliptique J2000 (précession UAI 1976)
    ze = (2306.2181 * T + 0.30188 * T * T + 0.017998 * T ** 3) * AS; z = (2306.2181 * T + 1.09468 * T * T + 0.018203 * T ** 3) * AS; th = (2004.3109 * T - 0.42665 * T * T - 0.041833 * T ** 3) * AS
    cz, sz, cZ, sZ, ct, st = math.cos(ze), math.sin(ze), math.cos(z), math.sin(z), math.cos(th), math.sin(th)
    P = np.array([[cz * ct * cZ - sz * sZ, -sz * ct * cZ - cz * sZ, -st * cZ], [cz * ct * sZ + sz * cZ, -sz * ct * sZ + cz * cZ, -st * sZ], [cz * st, -sz * st, ct]])
    ed = (84381.448 - 46.8150 * T - 0.00059 * T * T + 0.001813 * T ** 3) * AS
    e2q = np.array([[1, 0, 0], [0, math.cos(ed), -math.sin(ed)], [0, math.sin(ed), math.cos(ed)]]); q2e = np.array([[1, 0, 0], [0, math.cos(EPS0), math.sin(EPS0)], [0, -math.sin(EPS0), math.cos(EPS0)]])
    return q2e @ P.T @ e2q
def helio(P, T):
    L, B, R = lbr(P, T / 10.0)
    return m_date_to_j2000(T) @ np.array([R * math.cos(B) * math.cos(L), R * math.cos(B) * math.sin(L), R * math.sin(B)])
import pymeeus.Moon as Mo
LRT = np.array(Mo.PERIODIC_TERMS_LR_TABLE, dtype=float); BT = np.array(Mo.PERIODIC_TERMS_B_TABLE, dtype=float)
def moon(T):                 # Meeus, chap. 47 : géocentrique, écliptique de la date -> J2000, en UA
    d = math.radians
    Lp = 218.3164477 + 481267.88123421 * T - 0.0015786 * T * T + T ** 3 / 538841 - T ** 4 / 65194000
    Dm = 297.8501921 + 445267.1114034 * T - 0.0018819 * T * T + T ** 3 / 545868 - T ** 4 / 113065000
    M = 357.5291092 + 35999.0502909 * T - 0.0001536 * T * T + T ** 3 / 24490000
    Mp = 134.9633964 + 477198.8675055 * T + 0.0087414 * T * T + T ** 3 / 69699 - T ** 4 / 14712000
    F = 93.2720950 + 483202.0175233 * T - 0.0036539 * T * T - T ** 3 / 3526000 + T ** 4 / 863310000
    A1, A2, A3 = 119.75 + 131.849 * T, 53.09 + 479264.290 * T, 313.45 + 481266.484 * T
    E = 1 - 0.002516 * T - 0.0000074 * T * T
    ef = lambda m: np.where(np.abs(m) == 1, E, np.where(np.abs(m) == 2, E * E, 1.0))
    a = np.radians(LRT[:, 0] * Dm + LRT[:, 1] * M + LRT[:, 2] * Mp + LRT[:, 3] * F); e = ef(LRT[:, 1])
    sl = float(np.sum(LRT[:, 4] * e * np.sin(a))); sr = float(np.sum(LRT[:, 5] * e * np.cos(a)))
    a = np.radians(BT[:, 0] * Dm + BT[:, 1] * M + BT[:, 2] * Mp + BT[:, 3] * F); sb = float(np.sum(BT[:, 4] * ef(BT[:, 1]) * np.sin(a)))
    sl += 3958 * math.sin(d(A1)) + 1962 * math.sin(d(Lp - F)) + 318 * math.sin(d(A2))
    sb += -2235 * math.sin(d(Lp)) + 382 * math.sin(d(A3)) + 175 * math.sin(d(A1 - F)) + 175 * math.sin(d(A1 + F)) + 127 * math.sin(d(Lp - Mp)) - 115 * math.sin(d(Lp + Mp))
    lam, bet, r = d(Lp + sl / 1e6), d(sb / 1e6), (385000.56 + sr / 1000.0) / AU_KM
    return m_date_to_j2000(T) @ np.array([r * math.cos(bet) * math.cos(lam), r * math.cos(bet) * math.sin(lam), r * math.sin(bet)])
# --- référence DE440
solar_system_ephemeris.set(str(RAW / 'de440s.bsp'))
rng = np.random.default_rng(7); years = np.sort(rng.uniform(1851, 2149, 70))
tt = Time(years, format='jyear', scale='tdb'); Tc = (tt.jd - 2451545.0) / 36525.0
q2e = np.array([[1, 0, 0], [0, math.cos(EPS0), math.sin(EPS0)], [0, -math.sin(EPS0), math.cos(EPS0)]])
sun = get_body_barycentric('sun', tt).xyz.to_value(u.au).T
REF = {k: (get_body_barycentric(k, tt).xyz.to_value(u.au).T - sun) @ q2e.T for k, m, a in PL}
earth_b = get_body_barycentric('earth', tt).xyz.to_value(u.au).T
REF['moon'] = (get_body_barycentric('moon', tt).xyz.to_value(u.au).T - earth_b) @ q2e.T
sep = lambda a, b: math.degrees(math.acos(max(-1, min(1, float(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b)))))) * 3600
def errors(V):
    return {k: max(sep(helio(V[k], Tc[i]), REF[k][i]) for i in range(len(Tc))) for k, m, a in PL}
full = errors(FULL); print('séries complètes (%d termes) vs DE440, écart max en secondes d\'arc :' % count(FULL), {k: round(v, 2) for k, v in full.items()})
best = None
for thr in (20, 40, 70, 110, 170, 260, 400):
    V = trunc(thr); n = count(V); e = errors(V)
    print('seuil %3d : %5d termes | ' % (thr, n) + ' '.join('%s %.1f' % (k[:3], v) for k, v in e.items()))
    if best is None and n <= 3400: best = (thr, V, e)
thr, V, e = best
me = [sep(moon(Tc[i]), REF['moon'][i]) for i in range(len(Tc))]; md = [abs(np.linalg.norm(moon(Tc[i])) - np.linalg.norm(REF['moon'][i])) * AU_KM for i in range(len(Tc))]
print('retenu : seuil %d, %d termes' % (thr, count(V))); print('Lune (Meeus) vs DE440 : écart max %.1f″, moyen %.1f″ ; distance : max %.0f km' % (max(me), sum(me) / len(me), max(md)))
# hors période moderne : cohérence séries tronquées / complètes
for y in (-1000, 0, 1000, 3000, 4000):
    T = (y - 2000) / 100.0
    print('   an %5d : écart tronqué/complet (″)' % y, ' '.join('%s %.1f' % (k[:3], sep(helio(V[k], T), helio(FULL[k], T))) for k, m, a in PL))
rnd = lambda x: float('%.12g' % x)
E = {'VSOP': {k: {c: [[rnd(x) for x in s.ravel()] for s in V[k][c]] for c in 'LBR'} for k, m, a in PL}, 'MOON_LR': [x for row in Mo.PERIODIC_TERMS_LR_TABLE for x in row], 'MOON_B': [x for row in Mo.PERIODIC_TERMS_B_TABLE for x in row],
     'EPHEM_ERR': {k: round(v, 1) for k, v in e.items()}, 'MOON_ERR': round(max(me), 1)}
with open(OUT / 'ephem.js', 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('Object.assign(DATA, ' + json.dumps(E, separators=(',', ':')) + ');\n')
with open(APP_TEST / 'ref_de440.json', 'w', encoding='utf-8', newline='\n') as fh:
    json.dump({'T': Tc.tolist(), 'ref': {k: v.tolist() for k, v in REF.items()}}, fh)
# data2.js sans les séries complètes
p = OUT / 'data2.js'
with open(p, encoding='utf-8') as fh:
    s = fh.read()
d = json.loads(s[len('Object.assign(DATA, '):s.rindex(');')])
for k in ('VSOP', 'MOON_LR', 'MOON_B'): d.pop(k, None)
with open(p, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('Object.assign(DATA, ' + json.dumps(d, ensure_ascii=False, separators=(',', ':')) + ');\n')
print('ephem.js %.0f ko | data2.js %.0f ko' % ((OUT / 'ephem.js').stat().st_size / 1024, p.stat().st_size / 1024))
