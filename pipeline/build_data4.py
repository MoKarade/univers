# Quatrième lot de données réelles : étoiles Gaia DR3, comètes, étoiles à planètes, pulsars, Nuages de Magellan.
import numpy as np, pandas as pd, json, base64, math, os, warnings
warnings.filterwarnings('ignore')
RAW = 'raw'; OUT = '../gen'; D = {}; rng = np.random.default_rng(11)
def b64(a): return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
EPS = math.radians(23.4392911); RX = np.array([[1, 0, 0], [0, math.cos(EPS), math.sin(EPS)], [0, -math.sin(EPS), math.cos(EPS)]])
PC_LY = 3.2615638
def eq_unit(ra, de): ra, de = np.radians(ra), np.radians(de); return np.stack([np.cos(de) * np.cos(ra), np.cos(de) * np.sin(ra), np.sin(de)], 1)
# ------------------------------------------------------------------ Gaia DR3 : toutes les étoiles jusqu'à une magnitude limite
g = pd.read_csv(os.path.join(RAW, 'gaia_noirlab.csv')).dropna(subset=['parallax', 'pmra', 'pmdec']); g = g[g.parallax > 0.3].sort_values('phot_g_mean_mag')
NG = 200000; glim = float(g.phot_g_mean_mag.iloc[NG - 1]); tot = len(g); g = g.head(NG).sample(frac=1, random_state=5)
ra, de = np.radians(g.ra.values), np.radians(g.dec.values); dpc = 1000 / g.parallax.values; u = eq_unit(g.ra.values, g.dec.values)
era = np.stack([-np.sin(ra), np.cos(ra), np.zeros(NG)], 1); ede = np.stack([-np.sin(de) * np.cos(ra), -np.sin(de) * np.sin(ra), np.cos(de)], 1)
rv = np.nan_to_num(g.radial_velocity.values, nan=0.0); v = rv[:, None] * u + (4.74047 * g.pmra.values / 1000 * dpc)[:, None] * era + (4.74047 * g.pmdec.values / 1000 * dpc)[:, None] * ede
ue, ve = u @ RX.T, v @ RX.T; lon = np.arctan2(ue[:, 1], ue[:, 0]) % (2 * np.pi); lat = np.arcsin(np.clip(ue[:, 2], -1, 1)); dly = dpc * PC_LY
geo = np.stack([np.round(lon / (2 * np.pi) * 65535), np.round((lat / np.pi + 0.5) * 65535), np.round(np.clip(np.log10(dly) / 5, 0, 1) * 65535)], 1).astype('<u2')
MG = g.phot_g_mean_mag.values + 5 * np.log10(g.parallax.values) - 10; bv = np.nan_to_num(0.78 * g.bp_rp.values, nan=0.65)
aux = np.stack([np.clip(np.round((MG + 10) * 8), 0, 255), np.clip(np.round((bv + 0.5) * 80), 0, 255)], 1).astype('u1')
D['GAIA_N'] = NG; D['GAIA_GEO'] = b64(geo); D['GAIA_AUX'] = b64(aux); D['GAIA_VEL'] = b64(np.clip(np.round(ve / 2), -127, 127).astype('i1')); D['GAIA_GLIM'] = round(glim, 2)
print('Gaia DR3 : %d étoiles retenues sur %d (magnitude G de 8,40 à %.2f) | distance médiane %.0f al, 90 %% à moins de %.0f al | avec vitesse radiale mesurée : %.0f %% | vitesse médiane %.0f km/s, > 254 km/s : %d'
      % (NG, tot, glim, np.median(dly), np.percentile(dly, 90), 100 * g.radial_velocity.notna().mean(), np.median(np.linalg.norm(ve, axis=1)), (np.abs(ve).max(1) > 254).sum()))
# ------------------------------------------------------------------ comètes (JPL SBDB)
d = json.load(open(os.path.join(RAW, 'sbdb_com.json'))); F = {k: i for i, k in enumerate(d['fields'])}; rows = []
for r in d['data']:
    try:
        e, q, i, om, w, tp = (float(r[F[k]]) for k in ('e', 'q', 'i', 'om', 'w', 'tp'))
        if not (0 <= e < 0.9996) or q / (1 - e) > 6000: continue
        nm = (r[F['pdes']] or '').strip(); n2 = (r[F['name']] or '').strip(); nm = (nm + '/' + n2) if (n2 and nm.endswith('P')) else (nm + ' (' + n2 + ')' if n2 else nm)
        rows.append((q, e, i, om, w, tp - 2451545.0, float(r[F['M1']]) if r[F['M1']] else 12.0, nm, (r[F['class']] or '').strip()))
    except Exception: pass
rows.sort(key=lambda r: (0 if r[7][:1].isdigit() else 1, r[0]))
cls = sorted(set(r[8] for r in rows)); D['COM_N'] = len(rows); D['COM_EL'] = b64(np.array([r[:6] for r in rows], '<f4')); D['COM_M1'] = b64(np.clip(np.round(np.array([r[6] for r in rows]) * 8), 0, 255).astype('u1'))
D['COM_NAMES'] = '|'.join(r[7] for r in rows); D['COM_CLS'] = b64(np.array([cls.index(r[8]) for r in rows], 'u1')); D['COM_CLSN'] = cls
a = np.array([r[0] / (1 - r[1]) for r in rows]); print('comètes : %d (classes %s) | période médiane %.1f ans | %s' % (len(rows), cls, np.median(a ** 1.5), [r[7] for r in rows[:4]]))
# ------------------------------------------------------------------ étoiles à planètes (exoplanet.eu)
x = pd.read_csv(os.path.join(RAW, 'exoeu.csv'), low_memory=False); x = x[(x.planet_status == 'Confirmed') & x.star_name.notna() & x.ra.notna() & x.dec.notna() & (x.star_distance > 0)]
h = x.groupby('star_name').agg(ra=('ra', 'first'), dec=('dec', 'first'), d=('star_distance', 'median'), n=('name', 'count'), teff=('star_teff', 'median')).reset_index(); h = h[h.d < 9000].sort_values('d')
pe = eq_unit(h.ra.values, h.dec.values) @ RX.T * (h.d.values * PC_LY)[:, None]
D['EXO_N'] = len(h); D['EXO_POS'] = b64(pe.astype('<f4')); D['EXO_NP'] = b64(np.clip(h.n.values, 0, 255).astype('u1')); D['EXO_NAMES'] = '|'.join(str(s).replace('|', ' ') for s in h.star_name)
print('étoiles à planètes : %d étoiles, %d planètes confirmées | distance médiane %.0f al | les plus riches : %s' % (len(h), h.n.sum(), np.median(h.d) * PC_LY, h.sort_values('n').tail(4)[['star_name', 'n']].values.tolist()))
# ------------------------------------------------------------------ pulsars (catalogue ATNF, via VizieR)
P = []
for line in open(os.path.join(RAW, 'psr.tsv'), errors='replace'):
    p = line.rstrip('\n').split('\t')
    if len(p) < 5 or line.startswith('#'): continue
    try: P.append((float(p[0]), float(p[1]), p[2].strip(), float(p[3]), float(p[4]) if p[4].strip() else float('nan')))
    except Exception: pass
P = [p for p in P if 0 < p[3] < 70]; pp = eq_unit(np.array([p[0] for p in P]), np.array([p[1] for p in P])) @ RX.T * (np.array([p[3] for p in P]) * 3261.5638)[:, None]
D['PSR_N'] = len(P); D['PSR_POS'] = b64(pp.astype('<f4')); D['PSR_P0'] = b64(np.array([p[4] for p in P], '<f4')); D['PSR_NAMES'] = '|'.join(p[2] for p in P)
per = np.array([p[4] for p in P]); print('pulsars : %d avec distance | distance médiane %.0f al | période médiane %.2f s, la plus courte %.4f s' % (len(P), np.median([p[3] for p in P]) * 3261.56, np.nanmedian(per), np.nanmin(per)))
# ------------------------------------------------------------------ Nuages de Magellan : position et vitesse par rapport au centre de la Voie lactée
from astropy.coordinates import SkyCoord, Galactocentric
import astropy.units as au
def gc(ra, de, dk, pma, pmd, rv):
    c = SkyCoord(ra=ra * au.deg, dec=de * au.deg, distance=dk * au.kpc, pm_ra_cosdec=pma * au.mas / au.yr, pm_dec=pmd * au.mas / au.yr, radial_velocity=rv * au.km / au.s)
    g = c.transform_to(Galactocentric(galcen_distance=8.2 * au.kpc, z_sun=6.6 * au.pc, galcen_v_sun=(11.1, 242.24, 7.25) * au.km / au.s))
    return [round(float(v), 3) for v in (g.x.value, g.y.value, g.z.value)], [round(float(v), 2) for v in (g.v_x.value, g.v_y.value, g.v_z.value)]
for k, a in (('LMC', (78.76, -69.19, 50.1, 1.910, 0.229, 262.2)), ('SMC', (13.18, -72.83, 62.8, 0.772, -1.117, 145.6))):
    p, v = gc(*a); D[k] = {'pos': p, 'vel': v}; pn = np.linalg.norm(p); vr = np.dot(p, v) / pn
    print('%s : position %s kpc (%.1f kpc du centre) | vitesse %s km/s, totale %.0f, radiale %.0f, tangentielle %.0f' % (k, p, pn, v, np.linalg.norm(v), vr, math.sqrt(np.dot(v, v) - vr * vr)))
js = 'Object.assign(DATA, ' + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + ');\n'; open(os.path.join(OUT, 'data4.js'), 'w').write(js)
print('écrit data4.js : %.0f ko' % (len(js) / 1024)); [print('   %-10s %6.0f ko' % (k, len(json.dumps(v)) / 1024)) for k, v in sorted(D.items(), key=lambda kv: -len(json.dumps(kv[1])))[:6]]
# ------------------------------------------------------------------ étoiles à planètes : Open Exoplanet Catalogue (planètes confirmées seulement), préféré s'il est assez complet
import gzip, xml.etree.ElementTree as ET
def sexa(s, hours):
    p = s.replace(':', ' ').split(); sg = -1 if p[0].startswith('-') else 1; v = abs(float(p[0])) + float(p[1]) / 60 + (float(p[2]) if len(p) > 2 else 0) / 3600; return sg * v * (15 if hours else 1)
rows = []
for sy in ET.parse(gzip.open(os.path.join(RAW, 'oec.xml.gz'))).getroot().iter('system'):
    try:
        n = sum(1 for p in sy.iter('planet') if any((l.text or '').strip() == 'Confirmed planets' for l in p.findall('list')))
        d = float(sy.findtext('distance')); ra = sexa(sy.findtext('rightascension'), True); de = sexa(sy.findtext('declination'), False)
        if n > 0 and 0 < d < 9000: rows.append((sy.findtext('name').strip(), ra, de, d, n))
    except Exception: pass
rows.sort(key=lambda r: r[3]); cnt = {r[0]: r[4] for r in rows}
print('Open Exoplanet Catalogue : %d systèmes, %d planètes confirmées | contrôles : %s' % (len(rows), sum(r[4] for r in rows), {k: cnt.get(k) for k in ('TRAPPIST-1', 'Kepler-90', 'Beta Pictoris', 'beta Pic', '51 Pegasi', 'Proxima Centauri', 'Sun')}))
if len(rows) >= 3500:
    rows = [r for r in rows if r[0] != 'Sun']; pe = eq_unit(np.array([r[1] for r in rows]), np.array([r[2] for r in rows])) @ RX.T * (np.array([r[3] for r in rows]) * PC_LY)[:, None]
    D['EXO_N'] = len(rows); D['EXO_POS'] = b64(pe.astype('<f4')); D['EXO_NP'] = b64(np.clip([r[4] for r in rows], 0, 255).astype('u1')); D['EXO_NAMES'] = '|'.join(r[0].replace('|', ' ') for r in rows); D['EXO_SRC'] = 'Open Exoplanet Catalogue'
    print('-> source retenue : Open Exoplanet Catalogue (%d étoiles, distance médiane %.0f al)' % (len(rows), np.median([r[3] for r in rows]) * PC_LY))
else: D['EXO_SRC'] = 'exoplanet.eu'
js = 'Object.assign(DATA, ' + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + ');\n'; open(os.path.join(OUT, 'data4.js'), 'w').write(js)
