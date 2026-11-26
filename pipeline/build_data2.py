#!/usr/bin/env python3
"""Deuxième lot de données réelles -> app/gen/data2.js (complète et remplace une partie de app/gen/data.js)."""
import base64, csv, io, json, math, re, sys, time
from collections import Counter
from pathlib import Path
import numpy as np

_PIPE_DIR = str(Path(__file__).resolve().parent)
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import APP_GEN, PIPELINE_DIR, PIPELINE_RAW, raw_dir  # noqa: E402

HERE = PIPELINE_DIR
RAW = PIPELINE_RAW
OUT = APP_GEN
EPS = math.radians(84381.448 / 3600.0); PC_LY = 3.2615637769; CKMS = 299792.458
A_GAL = np.array([[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132], [0.4941094278755837, -0.4448296299600112, 0.7469822444972189], [-0.8676661490190047, -0.1980763734312015, 0.4559837761750669]])
RX = np.array([[1, 0, 0], [0, math.cos(EPS), math.sin(EPS)], [0, -math.sin(EPS), math.cos(EPS)]])
M_G2E = RX @ A_GAL.T
b64 = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def eq_unit(ra, dec):
    ra, dec = np.radians(ra), np.radians(dec); return np.stack([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)], -1)


def gal_unit(l, b):
    l, b = np.radians(l), np.radians(b); return np.stack([np.cos(b) * np.cos(l), np.cos(b) * np.sin(l), np.sin(b)], -1)


def lonlat16(v):   # vecteurs unitaires écliptiques -> (lon, lat) sur 16 bits
    lon = np.arctan2(v[:, 1], v[:, 0]) % (2 * np.pi); lat = np.arcsin(np.clip(v[:, 2], -1, 1))
    return np.stack([np.round(lon / (2 * np.pi) * 65535), np.round((lat / np.pi + 0.5) * 65535)], -1).astype('<u2')


def sex(s, hours):
    p = s.split(); sg = -1 if s.strip().startswith('-') else 1
    v = abs(float(p[0])) + float(p[1]) / 60 + float(p[2]) / 3600
    return sg * v * (15 if hours else 1)


def tables(path):
    """Découpe une sortie VizieR asu-tsv en tables : [(colonnes, lignes)]."""
    with open(path, encoding='utf-8', errors='replace') as fh:
        L = fh.read().split('\n')
    out = []; i = 0
    while i < len(L) - 2:
        if L[i] and not L[i].startswith('#') and L[i + 2].startswith('-'):
            cols = [c.strip() for c in L[i].split('\t')]; j = i + 3; rows = []
            while j < len(L) and L[j].strip() and not L[j].startswith('#'): rows.append(L[j].split('\t')); j += 1
            out.append((cols, rows)); i = j
        else: i += 1
    return out


def table(path, *need):
    return max((t for t in tables(path) if all(n in t[0] for n in need)), key=lambda t: len(t[1]))


def fl(x, d=float('nan')):
    try: return float(x)
    except Exception: return d


def sb(files, keep, quality=False, always=(), data_dir=None):
    base = RAW if data_dir is None else Path(data_dir)
    rows = []
    for f in files:
        with open(base / f, encoding='utf-8') as fh:
            d = json.load(fh)
        F = {k: i for i, k in enumerate(d['fields'])}
        for r in d['data']:
            try: a, e, inc, om, w, ma, ep = [float(r[F[k]]) for k in ('a', 'e', 'i', 'om', 'w', 'ma', 'epoch')]
            except Exception: continue
            H = fl(r[F['H']], 20.0)
            if not (0 < a < 700 and 0 <= e < 0.975): continue
            if quality:
                cc, arc = fl(r[F['condition_code']], 9), fl(r[F['data_arc']], 0)
                if (cc > 5 or arc < 400) and r[F['pdes']] not in always: continue
            rows.append((a, e, inc, om, w, ma, ep, H, r[F['pdes']], r[F['name']] or '', r[F['class']]))
    po = base / 'pluto_el.json'
    if po.exists():      # l'orbite de Pluton fournie par la base est ancienne : on prend ses éléments à l'époque commune (JPL Horizons)
        with open(po, encoding='utf-8') as fh:
            q = json.load(fh)
        rows = [(q['a'], q['e'], q['i'], q['om'], q['w'], q['ma'], q['ep']) + r[7:] if r[8] == '134340' else r for r in rows]
    rows.sort(key=lambda r: r[7]); return rows[:keep]


def main():
    from PIL import Image
    from astropy.io import fits
    from astropy_healpix import HEALPix
    import astropy.units as u

    T0 = time.time()
    rng = np.random.default_rng(20261110); D = {}

    # ------------------------------------------------------------------ étoiles (HYG 4.1, magnitude <= 8,5 ou à moins de 10 pc)
    STAR_LABELS = {70890: ('Proxima du Centaure', 2), 71683: ('Alpha du Centaure', 1), 87937: ('Étoile de Barnard', 2), 54035: ('Lalande 21185', 3), 32349: ('Sirius', 1), 92403: ('Ross 154', 3), 16537: ('Epsilon Eridani', 2), 114046: ('Lacaille 9352', 3), 37279: ('Procyon', 1), 104214: ('61 du Cygne', 2), 8102: ('Tau Ceti', 2), 97649: ('Altaïr', 1), 91262: ('Véga', 1), 113368: ('Fomalhaut', 2), 37826: ('Pollux', 2), 69673: ('Arcturus', 1), 24608: ('Capella', 1), 36850: ('Castor', 3), 21421: ('Aldébaran', 1), 49669: ('Régulus', 2), 30438: ('Canopus', 1), 65474: ('Spica', 2), 27989: ('Bételgeuse', 1), 80763: ('Antarès', 1), 24436: ('Rigel', 1), 11767: ('Étoile polaire', 1), 102098: ('Deneb', 1), 7588: ('Achernar', 2), 26311: ('Alnilam, dans la ceinture d’Orion', 3), 68702: ('Hadar', 3), 60718: ('Acrux', 3)}
    xyz, aux, labels = [], [], []
    with open(HERE / 'hygdata_v41.csv', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['id'] == '0': continue
            d, mag = fl(r['dist']), fl(r['mag'])
            if not (d > 0) or d >= 100000 or not (mag <= 8.5 or d <= 10): continue
            am, ci = fl(r['absmag'], 10.0), fl(r['ci'])
            if math.isnan(ci): ci = {'O': -0.3, 'B': -0.15, 'A': 0.1, 'F': 0.45, 'G': 0.65, 'K': 1.1, 'M': 1.6, 'D': 0.0}.get((r['spect'] or '').strip().upper()[:1], 1.4 if mag > 8 else 0.6)
            hip = int(r['hip']) if r['hip'] else None; lab = STAR_LABELS.get(hip) or ({'Wolf 359': ('Wolf 359', 3)}.get(r['proper']))
            if lab: labels.append({'i': len(xyz), 'n': lab[0], 'p': lab[1], 'd': round(d * PC_LY, 3)})
            xyz.append((fl(r['x']), fl(r['y']), fl(r['z']))); aux.append((min(255, max(0, round((am + 10) * 8))), min(255, max(0, round((ci + 0.5) * 100)))))
    xyz = np.array(xyz) @ RX.T * PC_LY; dist = np.linalg.norm(xyz, axis=1)
    ll = lonlat16(xyz / dist[:, None]); ld = np.round(np.clip((np.log10(dist) + 1) / 5.5, 0, 1) * 65535).astype('<u2')
    D['STARS_N'] = len(xyz); D['STARS_GEO'] = b64(np.concatenate([ll, ld[:, None]], 1)); D['STARS_AUX'] = b64(np.array(aux, dtype=np.uint8)); D['STAR_LABELS'] = labels
    print('étoiles : %d (étiquettes %d), distance médiane %.0f al, max %.0f al' % (len(xyz), len(labels), np.median(dist), dist.max()))

    # ------------------------------------------------------------------ amas globulaires (Harris) et amas ouverts (Cantat-Gaudin 2020)
    cl = []
    cols, rows = table(RAW / 'harris.tsv', 'Rsun', 'MVt'); ix = {c: i for i, c in enumerate(cols)}
    ngc = 0
    for r in rows:
        l, b, rs, mv, bv = fl(r[ix['GLON']]), fl(r[ix['GLAT']]), fl(r[ix['Rsun']]), fl(r[ix['MVt']], -7.0), fl(r[ix['(B-V)t']], 0.75)
        if not (rs > 0): continue
        p = (M_G2E @ gal_unit(l, b)) * rs * 1000 * PC_LY; cl.append((p[0], p[1], p[2], mv, bv)); ngc += 1
    cols, rows = max(tables(RAW / 'openclusters.tsv'), key=lambda t: len(t[1])); ix = {c: i for i, c in enumerate(cols)}
    noc = 0
    for r in rows:
        l, b, dpc, age, n = fl(r[ix['GLON']]), fl(r[ix['GLAT']]), fl(r[ix['DistPc']]), fl(r[ix['AgeNN']], 8.5), fl(r[ix['nbstars07']], 50)
        if not (dpc > 0): continue
        p = (M_G2E @ gal_unit(l, b)) * dpc * PC_LY
        mv = -3.0 - 2.0 * math.log10(max(n, 10) / 50.0) - 1.2 * max(0, 8.3 - age)       # éclat intégré approché : plus riche et plus jeune = plus lumineux
        cl.append((p[0], p[1], p[2], mv, float(np.interp(age, [6.5, 8, 9, 10], [-0.15, 0.1, 0.6, 0.9])))); noc += 1
    cl = np.array(cl, dtype='<f4'); D['CLUSTERS'] = b64(cl); D['CLUSTERS_N'] = [ngc, noc]
    print('amas : %d globulaires, %d ouverts' % (ngc, noc))

    # ------------------------------------------------------------------ petits corps (JPL SBDB), éléments ramenés à une époque commune
    def pack(rows, tag, names):
        ep = np.array([r[6] for r in rows]); EP0 = float(np.bincount((ep * 2).astype(int)).argmax()) / 2
        a = np.array([r[0] for r in rows]); n = np.degrees(0.01720209895) / a ** 1.5
        M0 = (np.array([r[5] for r in rows]) + n * (EP0 - ep)) % 360

        el = np.stack([a, np.array([r[1] for r in rows]), np.radians([r[2] for r in rows]), np.radians([r[3] % 360 for r in rows]), np.radians([r[4] % 360 for r in rows]), np.radians(M0)], 1).astype('<f4')
        D[tag + '_EL'] = b64(el); D[tag + '_H'] = b64(np.clip(np.round((np.array([r[7] for r in rows]) + 2) * 10), 0, 255).astype(np.uint8)); D[tag + '_N'] = len(rows); D[tag + '_EPOCH'] = EP0
        lab = []
        for i, r in enumerate(rows):
            if r[8] in names: lab.append({'i': i, 'n': names[r[8]][0], 'p': names[r[8]][1]})
        print('%s : %d objets, époque JD %.1f, H max %.1f, classes %s, étiquettes %s' % (tag, len(rows), EP0, rows[-1][7], dict(Counter(r[10] for r in rows).most_common(6)), [l['n'] for l in lab]))
        return lab

    D['AST_LABELS'] = pack(sb(['sbdb_ast_fp.json', 'sbdb_ast2_fp.json'], 14000), 'AST', {'1': ('Cérès', 1), '4': ('Vesta', 2), '2': ('Pallas', 3), '10': ('Hygie', 3)})
    D['TNO_LABELS'] = pack(sb(['sbdb_tno_fp.json'], 6500, quality=True, always=('134340',)), 'TNO', {'134340': ('Pluton', 1), '136199': ('Éris', 1), '136108': ('Hauméa', 2), '136472': ('Makémaké', 2), '90377': ('Sedna', 2), '50000': ('Quaoar', 3), '225088': ('Gonggong', 3), '90482': ('Orcus', 3), '2060': ('Chiron', 3)})

    # ------------------------------------------------------------------ Groupe local (McConnachie 2012) et voisinage (Karachentsev 2013)
    FR = {'andromeda': ('Andromède (M31)', 1, 'spiral', 23.0), 'triangulum': ('Galaxie du Triangle (M33)', 1, 'spiral', 9.0), 'lmc': ('Grand Nuage de Magellan', 1, 'irr', 4.5), 'smc': ('Petit Nuage de Magellan', 2, 'irr', 2.6),
          'fornax': ('Naine du Fourneau', 3), 'sculptor': ('Naine du Sculpteur', 3), 'draco': ('Naine du Dragon', 3), 'ursa minor': ('Naine de la Petite Ourse', 3), 'carina': ('Naine de la Carène', 3), 'sextans (i)': ('Naine du Sextant', 3), 'sagittarius dsph': ('Naine du Sagittaire', 3),
          'ngc 6822': ('NGC 6822', 3), 'ic 10': ('IC 10', 3), 'ic 1613': ('IC 1613', 3), 'wlm': ('WLM', 3), 'leo i': ('Leo I', 3), 'leo ii': ('Leo II', 3), 'm32': ('M32', 4), 'ngc 205': ('M110', 4), 'ngc 185': ('NGC 185', 4), 'ngc 147': ('NGC 147', 4), 'leo a': ('Leo A', 4), 'ngc 3109': ('NGC 3109', 4), 'phoenix': ('Naine du Phénix', 4)}
    cols, rows = table(RAW / 'mcconnachie.tsv', 'Name', 'D', 'VMag'); ix = {c: i for i, c in enumerate(cols)}
    local = []
    with open(OUT / 'data.js', encoding='utf-8') as fh:
        m31n = json.loads(re.search(r'"normal":(\[[^\]]+\])', fh.read()).group(1))
    for r in rows:
        name, dk = r[ix['Name']].strip(), fl(r[ix['D']])
        if name.lower().startswith('the galaxy') or not (dk > 0): continue
        ra, dec = fl(r[ix['_RAJ2000']]), fl(r[ix['_DEJ2000']]); mv = fl(r[ix['VMag']], -8.0); rh = fl(r[ix['R1']], 2.0)
        pos = (RX @ eq_unit(np.array([ra]), np.array([dec]))[0]) * dk / 1000.0
        f = FR.get(name.lower()); rkpc = dk * math.radians(rh / 60.0)
        o = {'n': f[0] if f else name, 'pos': [round(float(x), 6) for x in pos], 'k': f[2] if f and len(f) > 2 else 'dwarf', 's': f[3] if f and len(f) > 3 else round(min(max(3.0 * rkpc, 0.25), 3.0), 3), 'p': f[1] if f else 5, 'd': round(dk / 1000.0, 4), 'mv': mv}
        if o['n'].startswith('Andromède'): o['normal'] = m31n
        local.append(o)
    local.sort(key=lambda o: o['p']); D['LOCAL'] = local
    print('Groupe local : %d galaxies ; M31 à %.0f kpc, M33 à %.0f kpc, LMC à %.0f kpc ; non traduits : %s' % (len(local), *[next((o['d'] * 1000 for o in local if o['n'].startswith(k)), -1) for k in ('Andromède', 'Galaxie du Triangle', 'Grand Nuage')], [o['n'] for o in local if o['p'] == 5][:6]))
    cols, rows = table(RAW / 'ungc.tsv', 'Dist', 'A26'); ix = {c: i for i, c in enumerate(cols)}
    near = []
    for r in rows:
        d, ra, dec = fl(r[ix['Dist']]), fl(r[ix['_RAJ2000']]), fl(r[ix['_DEJ2000']])
        if not (d > 1.45) or math.isnan(ra): continue
        p = (RX @ eq_unit(np.array([ra]), np.array([dec]))[0]) * d
        near.append((p[0], p[1], p[2], min(max(fl(r[ix['A26']], 3.0), 0.5), 60.0) / 2000.0, fl(r[ix['BMag']], -13.0)))
    near = np.array(near, dtype='<f4'); D['NEAR'] = b64(near); D['NEAR_N'] = len(near)
    print('voisinage (distances mesurées) : %d galaxies de %.1f à %.1f Mpc' % (len(near), np.linalg.norm(near[:, :3], axis=1).min(), np.linalg.norm(near[:, :3], axis=1).max()))

    # ------------------------------------------------------------------ relevés de décalages vers le rouge
    def lg_frame(eq, z):   # vitesse ramenée au repère du Groupe local (Yahil et al. 1977)
        g = eq @ A_GAL.T
        return z + (-79.0 * g[:, 0] + 296.0 * g[:, 1] - 36.0 * g[:, 2]) / CKMS

    REST = []

    def take(eq, z, n, kind=1):
        k = np.isfinite(z) & (z > 0.002) & (z < 6.9); eq, z = eq[k], z[k]
        if len(z) > n: s = rng.choice(len(z), n, replace=False); m = np.ones(len(z), bool); m[s] = False; REST.append((eq[m], z[m], kind)); eq, z = eq[s], z[s]
        return eq, z

    c2, r2 = max(tables(RAW / '2mrs.tsv'), key=lambda t: len(t[1])); i2 = {c: i for i, c in enumerate(c2)}
    eq = eq_unit(np.array([fl(r[i2['_RAJ2000']]) for r in r2]), np.array([fl(r[i2['_DEJ2000']]) for r in r2])); z = lg_frame(eq, np.array([fl(r[i2['cz']]) for r in r2]) / CKMS)
    k = z > 700 / CKMS; s2 = (eq[k], z[k]); print('2MRS : %d galaxies (v > 700 km/s dans le repère du Groupe local), z médian %.3f' % (k.sum(), np.median(z[k])))

    def sexfile(name, zcol, qcol, scale):
        c, rows = max(tables(RAW / name), key=lambda t: len(t[1])); ra, de, zz = [], [], []
        for r in rows:
            try:
                if int(r[3]) not in (3, 4, 5): continue
                zz.append(float(r[2]) * scale); ra.append(sex(r[0], True)); de.append(sex(r[1], False))
            except Exception: pass
        e = eq_unit(np.array(ra), np.array(de)); return e, lg_frame(e, np.array(zz))

    e6, z6 = sexfile('6dfgs.tsv', 'cz', 'q_cz', 1 / CKMS); e2, zz2 = sexfile('2dfgrs.tsv', 'z', 'q_z', 1.0)

    def csvfile(name):
        ra, de, zz, cl = [], [], [], []
        with open(RAW / name, encoding='utf-8') as f:
            next(f)
            for line in f:
                p = line.rstrip('\n').split(',')
                if len(p) < 4: continue
                try: ra.append(float(p[0])); de.append(float(p[1])); zz.append(float(p[2])); cl.append(p[3].strip().strip('"').upper().startswith('Q'))
                except Exception: pass
        return eq_unit(np.array(ra), np.array(de)), np.array(zz), np.array(cl)

    es, zs, qs = csvfile('dl_sdss.csv'); ed, zd, qd = csvfile('dl_desi.csv')
    qq = []
    with open(RAW / 'dr16q.tsv', encoding='utf-8') as f:
        for line in f:
            p = line.split('\t')
            if len(p) == 3 and p[0][:1].isdigit():
                try: qq.append((float(p[0]), float(p[1]), float(p[2])))
                except Exception: pass
    qq = np.array(qq); eqq = eq_unit(qq[:, 0], qq[:, 1])
    print('lus : 6dF %d, 2dF %d, SDSS %d (dont %d quasars), DESI %d (dont %d quasars), DR16Q %d | %.0f s' % (len(z6), len(zz2), len(zs), qs.sum(), len(zd), qd.sum(), len(qq), time.time() - T0))
    parts_g = [take(e6, z6, 50000), take(e2, zz2, 70000), take(es[~qs], lg_frame(es[~qs], zs[~qs]), 200000), take(ed[~qd], zd[~qd], 70000)]
    parts_q = [take(eqq, qq[:, 2], 38000, 2), take(ed[qd], zd[qd], 8000, 2)]

    def cat(parts):
        e = np.concatenate([p[0] for p in parts]); z = np.concatenate([p[1] for p in parts]); s = rng.permutation(len(z)); return e[s], z[s]

    eg, zg = cat(parts_g); eqs, zq = cat(parts_q); s = rng.permutation(len(s2[1])); s2 = (s2[0][s], s2[1][s])
    ZMAX = 7.0

    def enc(e, z): return np.concatenate([lonlat16(e @ RX.T), np.round(np.log1p(np.clip(z, 0, ZMAX)) / math.log1p(ZMAX) * 65535).astype('<u2')[:, None]], 1)

    D['SURV'] = b64(np.concatenate([enc(*s2), enc(eg, zg), enc(eqs, zq)])); D['SURV_N'] = [len(s2[1]), len(zg), len(zq)]; D['SURV_ZMAX'] = ZMAX
    if REST:      # tout ce qui n'entre pas dans la page : rangé au hasard, 6 octets par objet, pour le chargement en flux
        TD = raw_dir() / 'tiles'; TD.mkdir(parents=True, exist_ok=True)
        e = np.concatenate([r[0] for r in REST]); zz = np.concatenate([r[1] for r in REST]); kk = np.concatenate([np.full(len(r[1]), r[2]) for r in REST]); s = np.random.default_rng(21).permutation(len(zz)); e, zz, kk = e[s] @ RX.T, zz[s], kk[s]
        lon = np.arctan2(e[:, 1], e[:, 0]) % (2 * np.pi); lat = np.arcsin(np.clip(e[:, 2], -1, 1))
        rec = np.zeros((len(zz), 3), '<u2'); rec[:, 0] = np.round(lon / (2 * np.pi) * 65535); rec[:, 1] = np.round((lat / np.pi + 0.5) * 32767).astype(np.uint16) | ((kk == 2).astype(np.uint16) << 15); rec[:, 2] = np.round(np.log1p(np.clip(zz, 0, ZMAX)) / math.log1p(ZMAX) * 65535)
        CAP = 2621440; man = []
        for t in range(0, len(zz), CAP):
            part = rec[t:t + CAP]; fn = 'g%d.txt' % (t // CAP + 1); fp = TD / fn
            with open(fp, 'w', encoding='utf-8') as fh:
                fh.write(base64.b64encode(part.tobytes()).decode())
            man.append({'kind': 'gal', 'file': fn, 'n': int(len(part)), 'mb': round(fp.stat().st_size / 1e6, 1)})
        with open(TD / 'gal.json', 'w', encoding='utf-8') as fh:
            json.dump(man, fh)
        print('morceaux de galaxies en flux : %s | galaxies %d, quasars %d' % (man, (kk == 1).sum(), (kk == 2).sum()))
    print('relevés retenus : 2MRS %d, galaxies profondes %d (z médian %.2f, max %.2f), quasars %d (z médian %.2f, max %.2f)' % (len(s2[1]), len(zg), np.median(zg), zg.max(), len(zq), np.median(zq), zq.max()))

    # ------------------------------------------------------------------ fond diffus cosmologique : carte WMAP 9 ans (ILC), HEALPix -> image équirectangulaire en coordonnées galactiques
    with fits.open(RAW / 'wmap_ilc.fits') as h:
        hd = h[1].header; T = np.asarray(h[1].data.field(0), dtype=float).ravel()
    hp = HEALPix(nside=int(hd['NSIDE']), order=hd['ORDERING'].strip().lower())
    W, Hh = 720, 360
    uu, vv = np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(Hh) + 0.5) / Hh)
    lon = (uu - 0.5) * 360.0; lat = (0.5 - vv) * 180.0            # u=0,5 : longitude galactique 0 ; haut de l'image : pôle nord galactique
    img = T[hp.lonlat_to_healpix((lon % 360) * u.deg, lat * u.deg)]
    print('WMAP ILC : NSIDE %s, ordre %s, unité %s, écart-type %.4f, min %.3f, max %.3f' % (hd['NSIDE'], hd['ORDERING'], hd.get('TUNIT1'), img.std(), img.min(), img.max()))
    g8 = np.clip((img / (4.0 * img.std()) * 0.5 + 0.5) * 255, 0, 255).astype(np.uint8)
    buf = io.BytesIO(); Image.fromarray(g8, 'L').save(buf, 'JPEG', quality=84, optimize=True); D['CMB'] = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
    cmb_dir = raw_dir(); cmb_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(g8, 'L').save(cmb_dir / 'cmb_check.png')

    js = 'Object.assign(DATA, ' + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + ');\n'
    with open(OUT / 'data2.js', 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(js)
    for k, v in sorted(D.items(), key=lambda kv: -len(json.dumps(kv[1])))[:9]: print('   %-10s %6.0f ko' % (k, len(json.dumps(v)) / 1024))
    print('app/gen/data2.js : %.0f ko | %.0f s' % (len(js.encode()) / 1024, time.time() - T0))


if __name__ == '__main__':
    main()
