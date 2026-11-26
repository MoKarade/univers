#!/usr/bin/env python3
"""Construit gen/data.js : toutes les données réelles embarquées dans l'artefact.

Repère de travail de l'application : écliptique J2000 héliocentrique
(x vers le point vernal, z vers le pôle nord écliptique).
"""
import base64, csv, io, json, math, os, sys
from pathlib import Path
import numpy as np
from PIL import Image
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.cosmology import Planck18

_PIPE_DIR = str(Path(__file__).resolve().parent)
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import APP_GEN, PIPELINE_DIR, PIPELINE_RAW  # noqa: E402

HERE = PIPELINE_DIR
RAW = PIPELINE_RAW
OUT = APP_GEN
OUT.mkdir(parents=True, exist_ok=True)

EPS = math.radians(84381.448 / 3600.0)  # obliquité moyenne J2000 (IAU 1976), celle du repère JPL
PC_LY = 3.2615637769

def eq_to_ecl(v):
    x, y, z = v
    c, s = math.cos(EPS), math.sin(EPS)
    return np.array([x, c * y + s * z, -s * y + c * z])

def radec_unit(ra_deg, dec_deg):
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    return np.array([math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)])

def radec_ecl(ra_deg, dec_deg):
    return eq_to_ecl(radec_unit(ra_deg, dec_deg))

# ---------------------------------------------------------------- repères
def gal_unit_eq(l, b):
    c = SkyCoord(l=l * u.deg, b=b * u.deg, frame='galactic').icrs
    return radec_unit(c.ra.deg, c.dec.deg)

# colonnes = axes galactiques (vers le centre, vers l=90°, vers le pôle nord) exprimés en écliptique
M = np.column_stack([eq_to_ecl(gal_unit_eq(0, 0)), eq_to_ecl(gal_unit_eq(90, 0)), eq_to_ecl(gal_unit_eq(0, 90))])
assert abs(np.linalg.det(M) - 1) < 1e-9
# contrôle croisé avec la matrice Hipparcos (équatorial -> galactique)
A = np.array([[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132],
              [+0.4941094278755837, -0.4448296299600112, +0.7469822444972189],
              [-0.8676661490190047, -0.1980763734312015, +0.4559837761750669]])
Rx = np.array([[1, 0, 0], [0, math.cos(EPS), math.sin(EPS)], [0, -math.sin(EPS), math.cos(EPS)]])
M2 = Rx @ A.T
print('écart matrice gal->ecl astropy vs Hipparcos :', np.abs(M - M2).max())
ngp = M[:, 2]
print('pôle nord galactique en écliptique : lon %.3f lat %.3f' % (math.degrees(math.atan2(ngp[1], ngp[0])) % 360, math.degrees(math.asin(ngp[2]))))
gc = M[:, 0]
print('centre galactique en écliptique : lon %.3f lat %.3f' % (math.degrees(math.atan2(gc[1], gc[0])) % 360, math.degrees(math.asin(gc[2]))))

# Sgr A* (SIMBAD) : direction réelle du centre
SGRA = (266.41681662, -29.00782497)
sgra_ecl = radec_ecl(*SGRA)
sgra_gal = M.T @ sgra_ecl
print('Sgr A* en galactique (unitaire) :', sgra_gal, ' l=%.4f b=%.4f' % (math.degrees(math.atan2(sgra_gal[1], sgra_gal[0])) % 360, math.degrees(math.asin(sgra_gal[2]))))

# ---------------------------------------------------------------- étoiles (HYG v4.1)
def f(x):
    try:
        return float(x)
    except Exception:
        return float('nan')

with open(HERE / 'hygdata_v41.csv', encoding='utf-8') as fh:
    rows = list(csv.DictReader(fh))
MAG_LIM = 7.0
sel = []
for r in rows:
    if r['id'] == '0':
        continue
    d = f(r['dist'])
    if not (d > 0) or d >= 100000:
        continue
    mag = f(r['mag'])
    if mag <= MAG_LIM or d <= 10.0:
        sel.append(r)
print('étoiles retenues :', len(sel))

STAR_LABELS = {  # HIP -> (nom français, priorité 1..3)
    70890: ('Proxima du Centaure', 2), 71683: ('Alpha du Centaure', 1), 87937: ('Étoile de Barnard', 2),
    54035: ('Lalande 21185', 3), 32349: ('Sirius', 1), 92403: ('Ross 154', 3), 16537: ('Epsilon Eridani', 2),
    114046: ('Lacaille 9352', 3), 37279: ('Procyon', 1), 104214: ('61 du Cygne', 2), 8102: ('Tau Ceti', 2),
    97649: ('Altaïr', 1), 91262: ('Véga', 1), 113368: ('Fomalhaut', 2), 37826: ('Pollux', 2), 69673: ('Arcturus', 1),
    24608: ('Capella', 1), 36850: ('Castor', 3), 21421: ('Aldébaran', 1), 49669: ('Régulus', 2), 30438: ('Canopus', 1),
    65474: ('Spica', 2), 27989: ('Bételgeuse', 1), 80763: ('Antarès', 1), 24436: ('Rigel', 1), 11767: ('Étoile polaire', 1),
    102098: ('Deneb', 1), 7588: ('Achernar', 2), 26311: ('Alnilam, dans la ceinture d’Orion', 3), 68702: ('Hadar', 3), 60718: ('Acrux', 3),
}
by_proper = {'Wolf 359': ('Wolf 359', 3)}

pos = np.zeros((len(sel), 3), dtype='<f4')
aux = np.zeros((len(sel), 2), dtype=np.uint8)
labels = []
for i, r in enumerate(sel):
    v = eq_to_ecl(np.array([f(r['x']), f(r['y']), f(r['z'])])) * PC_LY  # années-lumière
    pos[i] = v
    am = f(r['absmag'])
    if math.isnan(am):
        am = 10.0
    ci = f(r['ci'])
    if math.isnan(ci):
        sp = (r['spect'] or '').strip().upper()[:1]
        ci = {'O': -0.3, 'B': -0.15, 'A': 0.1, 'F': 0.45, 'G': 0.65, 'K': 1.1, 'M': 1.6, 'D': 0.0}.get(sp, 1.4 if f(r['mag']) > 8 else 0.6)
    aux[i, 0] = int(round(min(255, max(0, (am + 10.0) * 8.0))))
    aux[i, 1] = int(round(min(255, max(0, (ci + 0.5) * 100.0))))
    hip = int(r['hip']) if r['hip'] else None
    lab = STAR_LABELS.get(hip) or by_proper.get(r['proper'])
    if lab:
        labels.append({'i': i, 'n': lab[0], 'p': lab[1], 'd': round(float(np.linalg.norm(v)), 3)})
found = {l['n'] for l in labels}
missing = [v[0] for v in list(STAR_LABELS.values()) + list(by_proper.values()) if v[0] not in found]
print('étiquettes étoiles :', len(labels), 'manquantes :', missing)
for l in sorted(labels, key=lambda l: l['d'])[:8]:
    print('   ', l)

# ---------------------------------------------------------------- repères du ciel profond (dans la Voie lactée)
def at(ra, dec, d_ly):
    return [round(float(x), 4) for x in radec_ecl(ra, dec) * d_ly]

DEEP = [  # nom, RA, Dec (SIMBAD), distance en années-lumière, priorité
    {'n': 'Les Pléiades', 'pos': at(56.6008, 24.1139, 135.0 * PC_LY), 'p': 2},
    {'n': 'Les Hyades', 'pos': at(67.4471, 16.9481, 47.0 * PC_LY), 'p': 3},
    {'n': 'Nébuleuse d’Orion', 'pos': at(83.8201, -5.3876, 414.0 * PC_LY), 'p': 1},
    {'n': 'Nébuleuse du Crabe', 'pos': at(83.6324, 22.0174, 2000.0 * PC_LY), 'p': 2},
    {'n': 'Nébuleuse de la Carène', 'pos': at(161.2593, -59.6999, 2500.0 * PC_LY), 'p': 2},
    {'n': 'Amas Oméga du Centaure', 'pos': at(201.6970, -47.4795, 5200.0 * PC_LY), 'p': 2},
]

# ---------------------------------------------------------------- galaxies du Groupe local (positions actuelles, Mpc)
with open(HERE / 'simbad_gal.json', encoding='utf-8') as fh:
    simbad = {' '.join(r['id'].split()): r for r in json.load(fh)}
def sb(name):
    r = simbad[name]
    return float(r['ra']), float(r['dec'])

def gal(name_fr, key, d_mpc, kind, size_kpc, prio, **kw):
    ra, dec = sb(key)
    p = radec_ecl(ra, dec) * d_mpc
    o = {'n': name_fr, 'pos': [round(float(x), 6) for x in p], 'k': kind, 's': size_kpc, 'p': prio, 'd': d_mpc}
    o.update(kw)
    return o

# normale du disque d'Andromède : inclinaison 77°, angle de position du grand axe 35° (SIMBAD), côté nord-ouest le plus proche
def disk_normal(ra, dec, pa_deg, inc_deg, near_pa_deg):
    los = radec_unit(ra, dec)
    north = np.array([0, 0, 1.0]) - los * los[2]
    north /= np.linalg.norm(north)
    east = np.cross(north, los)  # vers les RA croissantes
    east = east if np.dot(east, np.array([-math.sin(math.radians(ra)), math.cos(math.radians(ra)), 0])) > 0 else -east
    k = math.cos(math.radians(near_pa_deg)) * north + math.sin(math.radians(near_pa_deg)) * east  # petit axe, côté proche
    n = math.cos(math.radians(inc_deg)) * los + math.sin(math.radians(inc_deg)) * k
    major = math.cos(math.radians(pa_deg)) * north + math.sin(math.radians(pa_deg)) * east
    assert abs(np.dot(n, major)) < 1e-9
    return [round(float(x), 5) for x in eq_to_ecl(n)]

m31_ra, m31_dec = sb('M 31')
LOCAL = [
    gal('Andromède (M31)', 'M 31', 0.77, 'spiral', 23.0, 1, normal=disk_normal(m31_ra, m31_dec, 35.0, 77.0, 35.0 - 90.0)),
    gal('Galaxie du Triangle (M33)', 'M 33', 0.85, 'spiral', 9.0, 1),
    gal('Grand Nuage de Magellan', 'NAME LMC', 0.050, 'irr', 4.5, 1),
    gal('Petit Nuage de Magellan', 'NAME SMC', 0.062, 'irr', 2.6, 2),
    gal('M32', 'M 32', 0.775, 'dwarf', 1.2, 4), gal('M110', 'M 110', 0.80, 'dwarf', 2.2, 4),
    gal('NGC 6822', 'NGC 6822', 0.48, 'dwarf', 1.6, 3), gal('IC 10', 'IC 10', 0.74, 'dwarf', 1.2, 3),
    gal('IC 1613', 'IC 1613', 0.74, 'dwarf', 1.6, 3), gal('WLM', 'NAME WLM Galaxy', 0.98, 'dwarf', 1.4, 3),
    gal('NGC 185', 'NGC 185', 0.66, 'dwarf', 1.0, 4), gal('NGC 147', 'NGC 147', 0.73, 'dwarf', 1.0, 4),
    gal('Leo A', 'NAME Leo A', 0.78, 'dwarf', 0.8, 4), gal('NGC 3109', 'NGC 3109', 1.33, 'dwarf', 1.6, 4),
    gal('Naine du Fourneau', 'NAME Fornax Dwarf Spheroidal', 0.14, 'dwarf', 0.9, 3),
    gal('Naine du Sculpteur', 'NAME Sculptor Dwarf Galaxy', 0.082, 'dwarf', 0.6, 4),
    gal('Naine du Dragon', 'NAME Draco Dwarf Galaxy', 0.080, 'dwarf', 0.5, 4),
    gal('Naine de la Petite Ourse', 'NAME UMi Galaxy', 0.070, 'dwarf', 0.5, 4),
    gal('Naine de la Carène', 'NAME Carina dSph', 0.105, 'dwarf', 0.5, 4),
    gal('Naine du Sextant', 'NAME Sextans Dwarf Galaxy', 0.090, 'dwarf', 0.6, 4),
    gal('Leo I', 'NAME Leo I', 0.26, 'dwarf', 0.6, 4), gal('Leo II', 'NAME Leo II', 0.24, 'dwarf', 0.5, 4),
    gal('Naine du Sagittaire', 'NAME Sgr dSph', 0.024, 'dwarf', 1.5, 4),
]

# ---------------------------------------------------------------- galaxies et amas dans le flot de Hubble (distances comobiles actuelles, Mpc)
def dz(z):
    return float(Planck18.comoving_distance(z).to_value(u.Mpc))

def far(name_fr, ra, dec, d_mpc, kind, prio, well=0.0, sigma=0.0):
    p = radec_ecl(ra, dec) * d_mpc
    return {'n': name_fr, 'pos': [round(float(x), 3) for x in p], 'k': kind, 'p': prio, 'd': round(d_mpc, 2), 'w': well, 'sg': sigma}

FAR = [
    far('M81', *sb('M 81'), 3.63, 'gal', 2), far('Centaurus A', *sb('NGC 5128'), 3.73, 'gal', 2),
    far('Galaxie du Sculpteur', *sb('NGC 253'), 3.70, 'gal', 3), far('IC 342', *sb('IC 342'), 3.28, 'gal', 4),
    far('M83', *sb('M 83'), 4.66, 'gal', 3), far('M101', *sb('M 101'), 6.95, 'gal', 3),
    far('Galaxie du Tourbillon (M51)', *sb('M 51'), 7.66, 'gal', 3), far('Galaxie du Sombrero', *sb('M 104'), 11.27, 'gal', 4),
    far('Amas de la Vierge', 187.6991, 12.3852, 16.5, 'cluster', 1, well=0.92, sigma=4.5),
    far('Amas du Fourneau', 54.6225, -35.4522, 19.6, 'cluster', 2, well=0.75, sigma=3.0),
    far('Amas du Centaure', 192.2051, -41.3047, dz(0.0114), 'cluster', 3, well=0.85, sigma=8.0),
    far('Amas de l’Hydre', 159.15, -27.5178, dz(0.0129), 'cluster', 3, well=0.8, sigma=7.0),
    far('Grand Attracteur', 243.59375, -60.8686, dz(0.01628), 'cluster', 1, well=0.95, sigma=13.0),
    far('Amas de Persée', 49.9482, 41.515, 73.0, 'cluster', 2, well=0.92, sigma=10.0),
    far('Amas de Coma', 194.935, 27.9125, 102.5, 'cluster', 1, well=0.95, sigma=12.0),
    far('Amas du Lion', 176.1858, 19.6997, dz(0.0225), 'cluster', 4, well=0.8, sigma=9.0),
    far('Amas d’Hercule', 241.3125, 17.7486, dz(0.0352), 'cluster', 2, well=0.9, sigma=14.0),
    far('Abell 2199', 247.1439, 39.5405, dz(0.0309), 'cluster', 4, well=0.85, sigma=11.0),
    far('Superamas de Shapley', 202.0135, -31.5265, dz(0.0474), 'cluster', 1, well=0.97, sigma=24.0),
    far('Amas de la Couronne boréale', 230.5944, 27.7389, dz(0.0731), 'cluster', 3, well=0.92, sigma=22.0),
    far('Vide du Bouvier', 222.9458, 45.7955, dz(0.05), 'void', 2, well=-0.55, sigma=42.0),
]
for g in FAR:
    print('   %-30s d=%7.1f Mpc' % (g['n'], g['d']))

# ---------------------------------------------------------------- textures (Solar System Scope, CC BY 4.0)
def tex(name, w, h, q=74):
    im = Image.open(os.path.join(HERE, 'tex', 'Solarsystemscope_texture_2k_%s.jpg' % name)).convert('RGB').resize((w, h), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, 'JPEG', quality=q, optimize=True, progressive=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()

def ring():
    im = Image.open(os.path.join(HERE, 'tex', 'Solarsystemscope_texture_2k_saturn_ring_alpha.png')).convert('RGBA')
    row = im.resize((1024, 125), Image.LANCZOS).crop((0, 60, 1024, 64))
    b = io.BytesIO()
    row.save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()

TEX = {
    'mercury': tex('mercury', 1024, 512, 62), 'venus': tex('venus_atmosphere', 512, 256, 70),
    'earth': tex('earth_daymap', 2048, 1024, 70), 'moon': tex('moon', 1024, 512, 62),
    'mars': tex('mars', 1024, 512, 68), 'jupiter': tex('jupiter', 1536, 768, 70),
    'saturn': tex('saturn', 1024, 512, 72), 'uranus': tex('uranus', 256, 128, 72),
    'neptune': tex('neptune', 512, 256, 72), 'ring': ring(),
}
for k, v in TEX.items():
    print('   texture %-8s %6.0f ko (base64)' % (k, len(v) / 1024))


# ---------------------------------------------------------------- éléments orbitaux JPL (lus dans la page officielle, pas retapés)
import re as _re, html as _html
with open(HERE / 'approx_pos.html', encoding='utf-8') as fh:
    _page = fh.read()
_pres = [_html.unescape(_re.sub(r'<[^>]+>', '', p)) for p in _re.findall(r'<pre[^>]*>(.*?)</pre>', _page, flags=_re.S)]
def _parse_el(txt):
    out, cur = {}, None
    for line in txt.splitlines():
        m = _re.match(r'^(Mercury|Venus|EM Bary|Mars|Jupiter|Saturn|Uranus|Neptune)\s+(.*)$', line)
        nums = _re.findall(r'[-+]?\d+\.\d+', m.group(2) if m else line)
        if m and len(nums) == 6:
            cur = {'EM Bary': 'emb'}.get(m.group(1), m.group(1).lower())
            out[cur] = [float(x) for x in nums]
        elif cur and len(nums) == 6 and not line.strip().startswith('-'*5) and _re.match(r'^\s+[-\d]', line):
            out[cur] += [float(x) for x in nums]
            cur = None
    return out
JPL1, JPL2 = _parse_el(_pres[0]), _parse_el(_pres[1])
JPL2X = {}
for line in _pres[2].splitlines():
    m = _re.match(r'^(Jupiter|Saturn|Uranus|Neptune)\s+(.*)$', line)
    if m:
        JPL2X[m.group(1).lower()] = [float(x) for x in _re.findall(r'[-+]?\d+\.\d+', m.group(2))]
assert len(JPL1) == 8 and len(JPL2) == 8 and all(len(v) == 12 for v in list(JPL1.values()) + list(JPL2.values())), (JPL1, JPL2)
assert len(JPL2X) == 4 and all(len(v) == 4 for v in JPL2X.values())
print('JPL table 1, Terre-Lune :', JPL1['emb'])
print('JPL table 2b, Saturne   :', JPL2X['saturn'])

# ---------------------------------------------------------------- sortie
data = {
    'M_GAL2ECL': [[round(float(x), 10) for x in row] for row in M],
    'SGRA_GAL': [round(float(x), 8) for x in sgra_gal],
    'STARS_N': len(sel),
    'STARS_POS': '',
    'STARS_AUX': '',
    'JPL1': JPL1, 'JPL2': JPL2, 'JPL2X': JPL2X,
    'STAR_LABELS': labels, 'DEEP': DEEP, 'LOCAL': LOCAL, 'FAR': FAR, 'TEX': TEX,
}
js = 'const DATA = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n'
with open(OUT / 'data.js', 'w', encoding='utf-8', newline='\n') as fh:
    fh.write(js)
print('app/gen/data.js : %.0f ko' % (len(js.encode()) / 1024))
