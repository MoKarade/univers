# Étoiles Gaia au-delà de celles incluses dans la page : rangées de la plus brillante à la plus faible, 11 octets par étoile, pour le chargement en flux.
import base64, glob, json, math, sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

_PIPE_DIR = str(Path(__file__).resolve().parent)
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import PIPELINE_RAW, raw_dir  # noqa: E402

TD = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else raw_dir() / 'tiles'
TD.mkdir(parents=True, exist_ok=True)
PC_LY = 3.2615638
EPS = math.radians(23.4392911); RX = np.array([[1, 0, 0], [0, math.cos(EPS), math.sin(EPS)], [0, -math.sin(EPS), math.cos(EPS)]])
g0 = pd.read_csv(PIPELINE_RAW / 'gaia_noirlab.csv').dropna(subset=['parallax', 'pmra', 'pmdec']); g0 = g0[g0.parallax > 0.3].sort_values('phot_g_mean_mag'); glim = float(g0.phot_g_mean_mag.iloc[199999]); rest = g0.iloc[200000:]
fs = sorted(glob.glob(str(PIPELINE_RAW / 'esa' / '*.csv'))) + [str(f) for f in (PIPELINE_RAW / 'gaia_t1.csv', PIPELINE_RAW / 'gaia_t2.csv') if f.exists()]
parts = [rest] + [pd.read_csv(f) for f in fs]; g = pd.concat(parts, ignore_index=True).dropna(subset=['parallax', 'pmra', 'pmdec']); g = g[(g.parallax > 0.2) & (g.phot_g_mean_mag > glim)]
g['k'] = (g.ra * 1e5).round().astype('int64') * 100000000 + ((g.dec + 90) * 1e5).round().astype('int64'); g = g.drop_duplicates('k').sort_values('phot_g_mean_mag').reset_index(drop=True); N = len(g)
ra, de = np.radians(g.ra.values), np.radians(g.dec.values); dpc = 1000 / g.parallax.values; u = np.stack([np.cos(de) * np.cos(ra), np.cos(de) * np.sin(ra), np.sin(de)], 1)
era = np.stack([-np.sin(ra), np.cos(ra), np.zeros(N)], 1); ede = np.stack([-np.sin(de) * np.cos(ra), -np.sin(de) * np.sin(ra), np.cos(de)], 1)
rv = np.nan_to_num(g.radial_velocity.values, nan=0.0); v = rv[:, None] * u + (4.74047 * g.pmra.values / 1000 * dpc)[:, None] * era + (4.74047 * g.pmdec.values / 1000 * dpc)[:, None] * ede
ue, ve = u @ RX.T, v @ RX.T; lon = np.arctan2(ue[:, 1], ue[:, 0]) % (2 * np.pi); lat = np.arcsin(np.clip(ue[:, 2], -1, 1)); dly = dpc * PC_LY
MG = g.phot_g_mean_mag.values + 5 * np.log10(g.parallax.values) - 10; bv = np.nan_to_num(0.78 * g.bp_rp.values, nan=0.65)
rec = np.zeros(N, dtype=[('lon', '<u2'), ('lat', '<u2'), ('d', '<u2'), ('m', 'u1'), ('c', 'u1'), ('v', 'i1', 3)])
rec['lon'] = np.round(lon / (2 * np.pi) * 65535); rec['lat'] = np.round((lat / np.pi + 0.5) * 65535); rec['d'] = np.round(np.clip(np.log10(dly) / 5, 0, 1) * 65535); rec['m'] = np.clip(np.round((MG + 10) * 8), 0, 255); rec['c'] = np.clip(np.round((bv + 0.5) * 80), 0, 255); rec['v'] = np.clip(np.round(ve / 2), -127, 127)
assert rec.dtype.itemsize == 11
CAP = 1300000; man = []
for f in TD.glob('s*.txt'): f.unlink()
for t in range(0, N, CAP):
    part = rec[t:t + CAP]; fn = 's%d.txt' % (t // CAP + 1); fp = TD / fn
    with open(fp, 'w', encoding='utf-8') as fh:
        fh.write(base64.b64encode(part.tobytes()).decode())
    man.append({'kind': 'star', 'file': fn, 'n': int(len(part)), 'mb': round(fp.stat().st_size / 1e6, 1), 'g': [round(float(g.phot_g_mean_mag.iloc[t]), 2), round(float(g.phot_g_mean_mag.iloc[min(N, t + CAP) - 1]), 2)]})
with open(TD / 'star.json', 'w', encoding='utf-8') as fh:
    json.dump(man, fh)
hist = np.histogram(g.phot_g_mean_mag.values, bins=np.arange(9.5, 11.8, 0.25))[0]
print('étoiles en flux : %d (fichiers ESA lus : %d) | magnitude G de %.2f à %.2f | distance médiane %.0f al | avec vitesse radiale %.0f %% | par tranche de 0,25 mag : %s' % (N, len(fs), g.phot_g_mean_mag.min(), g.phot_g_mean_mag.max(), np.median(dly), 100 * g.radial_velocity.notna().mean(), hist.tolist())); print(man)
