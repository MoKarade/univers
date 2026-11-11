#!/usr/bin/env python3
"""Télécharge un échantillon de galaxies et de quasars du relevé DESI DR1 (NOIRLab Astro Data Lab) et l'écrit en binaire pour la page.
Exemple :  python tools/get_galaxies.py --from 0.45 --to 13      (pourcentages du relevé complet ; 0 à 0,45 % est déjà dans la page)
Chaque objet = 6 octets : longitude et latitude écliptiques (16 et 15 bits, le bit restant distingue les quasars) et décalage vers le rouge (16 bits)."""
import argparse, json, math, os, io
import numpy as np, pandas as pd, requests
ap = argparse.ArgumentParser(); ap.add_argument('--from', dest='a', type=float, default=0.45); ap.add_argument('--to', dest='b', type=float, default=13.0)
ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tiles')); ap.add_argument('--per-file', type=int, default=3000000); A = ap.parse_args(); os.makedirs(A.out, exist_ok=True)
q = "SELECT mean_fiber_ra,mean_fiber_dec,z,spectype FROM desi_dr1.zpix WHERE random_id>=%s AND random_id<%s AND zwarn=0 AND z>0.002 AND z<5.5 AND spectype<>'STAR' AND zcat_primary='t'" % (A.a, A.b)
print('requête envoyée, la réponse peut prendre quelques minutes…', flush=True)
r = requests.post('https://datalab.noirlab.edu/tap/sync', data={'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'csv', 'QUERY': q}, headers={'User-Agent': 'univers-site/1.0'}, timeout=(30, 3000)); r.raise_for_status()
d = pd.read_csv(io.BytesIO(r.content)); d.columns = ['ra', 'dec', 'z', 'cls']; d = d[np.isfinite(d.z) & (d.z > 0.002) & (d.z < 6.9)].sample(frac=1, random_state=3).reset_index(drop=True)
EPS = math.radians(23.4392911); RX = np.array([[1, 0, 0], [0, math.cos(EPS), math.sin(EPS)], [0, -math.sin(EPS), math.cos(EPS)]])
ra, de = np.radians(d.ra.values), np.radians(d.dec.values); e = np.stack([np.cos(de) * np.cos(ra), np.cos(de) * np.sin(ra), np.sin(de)], 1) @ RX.T
lon = np.arctan2(e[:, 1], e[:, 0]) % (2 * np.pi); lat = np.arcsin(np.clip(e[:, 2], -1, 1)); qso = d.cls.astype(str).str.strip().str.upper().str.startswith('Q').values
rec = np.zeros((len(d), 3), '<u2'); rec[:, 0] = np.round(lon / (2 * np.pi) * 65535); rec[:, 1] = np.round((lat / np.pi + 0.5) * 32767).astype(np.uint16) | (qso.astype(np.uint16) << 15); rec[:, 2] = np.round(np.log1p(np.clip(d.z.values, 0, 7.0)) / math.log1p(7.0) * 65535)
mp = os.path.join(A.out, 'manifest.json'); man = json.load(open(mp)) if os.path.exists(mp) else []; tag = 'desi_%s_%s' % (str(A.a).replace('.', 'p'), str(A.b).replace('.', 'p')); man = [m for m in man if tag not in m['url']]
for k, t in enumerate(range(0, len(d), A.per_file)):
    fn = '%s_%d.bin' % (tag, k + 1); part = rec[t:t + A.per_file]; part.tofile(os.path.join(A.out, fn)); man.append({'kind': 'gal', 'url': 'tiles/' + fn, 'n': int(len(part)), 'mb': round(part.nbytes / 1e6, 1), 'bin': True})
json.dump(man, open(mp, 'w'), indent=1); print('%d galaxies et quasars écrits. Fichiers listés dans %s' % (len(d), mp))
