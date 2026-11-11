#!/usr/bin/env python3
"""Télécharge des étoiles Gaia DR3 (archive de l'ESA) et les range en fichiers binaires pour la page.
Exemple :  python tools/get_stars.py --gmin 9.52 --gmax 12.4
Chaque étoile = 11 octets : longitude et latitude écliptiques (2 x 16 bits), distance (16 bits, logarithmique),
magnitude absolue, couleur, vitesse en 3 composantes (pas de 2 km/s). Les étoiles sont rangées de la plus brillante à la plus faible.
Reprise possible : les tranches déjà téléchargées (dossier tools/cache) ne sont pas redemandées."""
import argparse, glob, json, math, os, queue, threading, time
import numpy as np, pandas as pd, requests
ap = argparse.ArgumentParser(); ap.add_argument('--gmin', type=float, default=9.52); ap.add_argument('--gmax', type=float, default=12.4)
ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tiles')); ap.add_argument('--workers', type=int, default=8); ap.add_argument('--per-file', type=int, default=2000000)
A = ap.parse_args(); CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache'); os.makedirs(CACHE, exist_ok=True); os.makedirs(A.out, exist_ok=True)
UA = {'User-Agent': 'univers-site/1.0'}; TAP = 'https://gea.esac.esa.int/tap-server/tap/async'
Q = "SELECT TOP 3000000 ra,dec,parallax,pmra,pmdec,radial_velocity,phot_g_mean_mag,bp_rp FROM gaiadr3.gaia_source WHERE phot_g_mean_mag >= %.4f AND phot_g_mean_mag < %.4f AND parallax_over_error > 5 AND parallax > 0.2"
def job(a, b, depth=0):
    out = os.path.join(CACHE, 'g_%.4f_%.4f.csv' % (a, b))
    if os.path.exists(out): return
    for attempt in range(4):
        try:
            r = requests.post(TAP, data={'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'csv', 'PHASE': 'RUN', 'MAXREC': '3000000', 'QUERY': Q % (a, b)}, headers=UA, timeout=(20, 120), allow_redirects=False)
            url = r.headers.get('Location'); ph = ''
            if not url: time.sleep(10); continue
            t = time.time()
            while time.time() - t < 900:
                ph = requests.get(url + '/phase', headers=UA, timeout=60).text.strip()
                if ph in ('COMPLETED', 'ERROR', 'ABORTED'): break
                time.sleep(3)
            if ph != 'COMPLETED': time.sleep(10); continue
            d = requests.get(url + '/results/result', headers=UA, timeout=(20, 900)).content; n = d.count(b'\n') - 1
            if n >= 50000 and n % 50000 == 0 and depth < 6: m = (a + b) / 2; job(a, m, depth + 1); job(m, b, depth + 1); return      # réponse tronquée : on coupe la tranche en deux
            open(out, 'wb').write(d); print('  tranche %.3f-%.3f : %d étoiles' % (a, b, n), flush=True); return
        except Exception as e: print('  nouvel essai (%s)' % str(e)[:60], flush=True); time.sleep(8)
bins = []; g = A.gmin
while g < A.gmax - 1e-9:
    dens = 1.01 * 358000 * 2.75 ** (g - 9.8) * 0.9; w = min(0.1, 38000 / dens); b = min(A.gmax, g + w); bins.append((g, b)); g = b
print('%d tranches de magnitude à télécharger' % len(bins), flush=True)
qu = queue.Queue(); [qu.put(x) for x in bins]
def worker():
    while True:
        try: a, b = qu.get_nowait()
        except Exception: return
        job(a, b)
th = [threading.Thread(target=worker, daemon=True) for _ in range(A.workers)]; [t.start() for t in th]; [t.join() for t in th]
fs = [f for f in sorted(glob.glob(os.path.join(CACHE, 'g_*.csv'))) if A.gmin - 1e-6 <= float(os.path.basename(f).split('_')[1]) < A.gmax]
g = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True).dropna(subset=['parallax', 'pmra', 'pmdec']); g = g[g.parallax > 0.2].sort_values('phot_g_mean_mag').reset_index(drop=True); N = len(g)
EPS = math.radians(23.4392911); RX = np.array([[1, 0, 0], [0, math.cos(EPS), math.sin(EPS)], [0, -math.sin(EPS), math.cos(EPS)]])
ra, de = np.radians(g.ra.values), np.radians(g.dec.values); dpc = 1000 / g.parallax.values; u = np.stack([np.cos(de) * np.cos(ra), np.cos(de) * np.sin(ra), np.sin(de)], 1)
era = np.stack([-np.sin(ra), np.cos(ra), np.zeros(N)], 1); ede = np.stack([-np.sin(de) * np.cos(ra), -np.sin(de) * np.sin(ra), np.cos(de)], 1)
rv = np.nan_to_num(g.radial_velocity.values, nan=0.0); v = rv[:, None] * u + (4.74047 * g.pmra.values / 1000 * dpc)[:, None] * era + (4.74047 * g.pmdec.values / 1000 * dpc)[:, None] * ede
ue, ve = u @ RX.T, v @ RX.T; lon = np.arctan2(ue[:, 1], ue[:, 0]) % (2 * np.pi); lat = np.arcsin(np.clip(ue[:, 2], -1, 1)); dly = dpc * 3.2615638
MG = g.phot_g_mean_mag.values + 5 * np.log10(g.parallax.values) - 10; bv = np.nan_to_num(0.78 * g.bp_rp.values, nan=0.65)
rec = np.zeros(N, dtype=[('lon', '<u2'), ('lat', '<u2'), ('d', '<u2'), ('m', 'u1'), ('c', 'u1'), ('v', 'i1', 3)])
rec['lon'] = np.round(lon / (2 * np.pi) * 65535); rec['lat'] = np.round((lat / np.pi + 0.5) * 65535); rec['d'] = np.round(np.clip(np.log10(dly) / 5, 0, 1) * 65535); rec['m'] = np.clip(np.round((MG + 10) * 8), 0, 255); rec['c'] = np.clip(np.round((bv + 0.5) * 80), 0, 255); rec['v'] = np.clip(np.round(ve / 2), -127, 127)
mp = os.path.join(A.out, 'manifest.json'); man = json.load(open(mp)) if os.path.exists(mp) else []; tag = 'stars_%04d_%04d' % (round(A.gmin * 100), round(A.gmax * 100)); man = [m for m in man if tag not in m['url']]
for k, t in enumerate(range(0, N, A.per_file)):
    fn = '%s_%d.bin' % (tag, k + 1); part = rec[t:t + A.per_file]; part.tofile(os.path.join(A.out, fn)); man.append({'kind': 'star', 'url': 'tiles/' + fn, 'n': int(len(part)), 'mb': round(part.nbytes / 1e6, 1), 'bin': True})
json.dump(man, open(mp, 'w'), indent=1); print('%d étoiles écrites (magnitude G de %.2f à %.2f). Fichiers listés dans %s' % (N, A.gmin, A.gmax, mp))
