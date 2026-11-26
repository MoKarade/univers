#!/usr/bin/env python3
"""Troisième lot : vitesses et noms des étoiles, noms des petits corps, des amas et des galaxies, cinématique d'Andromède -> app/gen/data3.js"""
import csv, json, math, re, sys, warnings
from pathlib import Path
import numpy as np

warnings.filterwarnings('ignore')

_PIPE_DIR = str(Path(__file__).resolve().parent)
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import APP_GEN, PIPELINE_DIR, PIPELINE_RAW  # noqa: E402
from build_data2 import A_GAL, PC_LY, RX, b64, eq_unit, fl, lonlat16, sb, table  # noqa: E402

HERE = PIPELINE_DIR
RAW = PIPELINE_RAW
OUT = APP_GEN
KMS = 977792.22          # 1 pc/an en km/s
GREEK = dict(zip('Alp Bet Gam Del Eps Zet Eta The Iot Kap Lam Mu Nu Xi Omi Pi Rho Sig Tau Ups Phi Chi Psi Ome'.split(), 'α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ σ τ υ φ χ ψ ω'.split()))
STAR_LABELS = {70890: ('Proxima du Centaure', 2), 71683: ('Alpha du Centaure', 1), 87937: ('Étoile de Barnard', 2), 54035: ('Lalande 21185', 3), 32349: ('Sirius', 1), 92403: ('Ross 154', 3), 16537: ('Epsilon Eridani', 2), 114046: ('Lacaille 9352', 3), 37279: ('Procyon', 1), 104214: ('61 du Cygne', 2), 8102: ('Tau Ceti', 2), 97649: ('Altaïr', 1), 91262: ('Véga', 1), 113368: ('Fomalhaut', 2), 37826: ('Pollux', 2), 69673: ('Arcturus', 1), 24608: ('Capella', 1), 36850: ('Castor', 3), 21421: ('Aldébaran', 1), 49669: ('Régulus', 2), 30438: ('Canopus', 1), 65474: ('Spica', 2), 27989: ('Bételgeuse', 1), 80763: ('Antarès', 1), 24436: ('Rigel', 1), 11767: ('Étoile polaire', 1), 102098: ('Deneb', 1), 7588: ('Achernar', 2), 26311: ('Alnilam, dans la ceinture d’Orion', 3), 68702: ('Hadar', 3), 60718: ('Acrux', 3), 89825: ('Gliese 710', 2)}


def main():
    D = {}
    xyz, vel, aux, hips, labels, names = [], [], [], [], [], {}

    def add(p_eq_pc, v_eq_kms, am, ci, hip, name):
        i = len(xyz); xyz.append(p_eq_pc); vel.append(v_eq_kms); hips.append(hip or 0)
        aux.append((min(255, max(0, round((am + 10) * 8))), min(255, max(0, round((ci + 0.5) * 100)))))
        lab = STAR_LABELS.get(hip)
        if lab: labels.append({'i': i, 'n': lab[0], 'p': lab[1], 'd': round(float(np.linalg.norm(p_eq_pc)) * PC_LY, 3)}); names[i] = lab[0].split(',')[0]
        elif name: names[i] = name

    with open(HERE / 'hygdata_v41.csv', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['id'] == '0': continue
            d, mag = fl(r['dist']), fl(r['mag'])
            if not (d > 0) or d >= 100000 or not (mag <= 8.5 or d <= 10): continue
            hip = int(r['hip']) if r['hip'] else None
            if hip == 89825: continue
            am, ci = fl(r['absmag'], 10.0), fl(r['ci'])
            if math.isnan(ci): ci = {'O': -0.3, 'B': -0.15, 'A': 0.1, 'F': 0.45, 'G': 0.65, 'K': 1.1, 'M': 1.6, 'D': 0.0}.get((r['spect'] or '').strip().upper()[:1], 1.4 if mag > 8 else 0.6)
            v = np.array([fl(r['vx'], 0), fl(r['vy'], 0), fl(r['vz'], 0)]) * KMS
            if not np.all(np.isfinite(v)) or np.linalg.norm(v) > 500: v = np.zeros(3)
            nm = r['proper'].strip() or None
            if not nm and r['bayer'].strip(): b = re.match(r'([A-Za-z]+)-?(\d*)', r['bayer'].strip()); nm = (GREEK.get(b.group(1), b.group(1)) + ('' if not b.group(2) else chr(0x2070 + int(b.group(2))) if b.group(2) not in '123' else '¹²³'[int(b.group(2)) - 1]) + ' ' + r['con'].strip()) if b else None
            if not nm and r['flam'].strip(): nm = r['flam'].strip() + ' ' + r['con'].strip()
            if not nm and not hip and r['gl'].strip(): nm = r['gl'].strip().replace('Gl ', 'Gliese ').replace('GJ ', 'GJ ').replace('NN ', 'NN ')
            if nm == 'Wolf 359': labels.append({'i': len(xyz), 'n': 'Wolf 359', 'p': 3, 'd': round(d * PC_LY, 3)})
            add(np.array([fl(r['x']), fl(r['y']), fl(r['z'])]), v, am, ci, hip, nm)
    # Gliese 710 : astrométrie Gaia DR3 (parallaxe 52,3963 mas, mouvement propre -0,414 / -0,108 mas/an, vitesse radiale -14,42 km/s)
    ra, de, plx, pma, pmd, rv = math.radians(274.9618), math.radians(-1.9386), 52.3963e-3, -0.414e-3, -0.108e-3, -14.42
    dpc = 1 / plx; rh = np.array([math.cos(de) * math.cos(ra), math.cos(de) * math.sin(ra), math.sin(de)]); ea = np.array([-math.sin(ra), math.cos(ra), 0]); ed = np.array([-math.sin(de) * math.cos(ra), -math.sin(de) * math.sin(ra), math.cos(de)])
    add(rh * dpc, rv * rh + 4.74047 * dpc * (pma * ea + pmd * ed), 9.66 - 5 * math.log10(dpc / 10), 1.37, 89825, 'Gliese 710')
    xyz = np.array(xyz); vel = np.array(vel)
    pe = xyz @ RX.T * PC_LY; dist = np.linalg.norm(pe, axis=1)
    ll = lonlat16(pe / dist[:, None]); ld = np.round(np.clip((np.log10(dist) + 1) / 5.5, 0, 1) * 65535).astype('<u2')
    vg = vel @ A_GAL.T                                                  # km/s, axes galactiques (vers le centre, vers la rotation, vers le pôle nord), relatif au Soleil
    D['STARS_N'] = len(xyz); D['STARS_GEO'] = b64(np.concatenate([ll, ld[:, None]], 1)); D['STARS_AUX'] = b64(np.array(aux, dtype=np.uint8)); D['STAR_LABELS'] = labels
    D['STARS_VEL'] = b64(np.round(np.clip(vg * 20, -32000, 32000)).astype('<i2')); D['STARS_HIP'] = b64(np.array(hips, dtype='<u4')); D['STAR_NAMES'] = names
    # plus proches passages (mouvement rectiligne) : contrôle
    with np.errstate(all='ignore'):
        tca = -np.sum(xyz * vel, 1) / np.sum(vel * vel, 1) * (KMS / 1e6); dca = np.linalg.norm(xyz + vel / KMS * (tca * 1e6)[:, None], axis=1)
    ok = np.isfinite(tca) & (np.abs(tca) < 6) & (np.linalg.norm(vel, axis=1) > 1); o = np.argsort(np.where(ok, dca, 1e9))[:6]
    print('étoiles : %d, avec vitesse %d, nommées %d' % (len(xyz), int((np.linalg.norm(vel, axis=1) > 0).sum()), len(names)))
    for i in o: print('   passage proche : %-22s HIP %-6d dans %+.2f Ma à %.3f pc (%.0f UA)' % (names.get(int(i), '?'), hips[i], tca[i], dca[i], dca[i] * 206265))
    # ------------------------------------------------------------------ noms des petits corps (même ordre que data2)
    CLS = ['MBA', 'OMB', 'IMB', 'MCA', 'TJN', 'TNO', 'CEN', 'AMO', 'APO', 'ATE']
    FRN = {'1': 'Cérès', '134340': 'Pluton', '136199': 'Éris', '136108': 'Hauméa', '136472': 'Makémaké', '10': 'Hygie'}
    for tag, rows in (('AST', sb(['sbdb_ast_fp.json', 'sbdb_ast2_fp.json'], 14000)), ('TNO', sb(['sbdb_tno_fp.json'], 6500, quality=True, always=('134340',)))):
        D[tag + '_NAMES'] = '|'.join((FRN.get(r[8]) or r[9] or '').replace('|', ' ') + ('~' + r[8] if r[8].isdigit() else ('' if (r[9] or '') else r[8])) for r in rows)
        D[tag + '_CLS'] = b64(np.array([CLS.index(r[10]) if r[10] in CLS else 255 for r in rows], dtype=np.uint8))
        print(tag, 'noms :', D[tag + '_NAMES'][:90], '…', len(D[tag + '_NAMES']) // 1024, 'ko')
    # ------------------------------------------------------------------ noms et âges des amas, noms des galaxies proches
    cn, ca = [], []
    cols, rows = table(RAW / 'harris.tsv', 'Rsun', 'MVt'); ix = {c: i for i, c in enumerate(cols)}
    for r in rows:
        if fl(r[ix['Rsun']]) > 0: nm = r[ix['Name']].strip(); cn.append((nm + ' (' + r[ix['ID']].strip() + ')') if nm else r[ix['ID']].strip()); ca.append(0)
    cols, rows = table(RAW / 'openclusters.tsv', 'DistPc', 'AgeNN'); ix = {c: i for i, c in enumerate(cols)}
    for r in rows:
        if fl(r[ix['DistPc']]) > 0: cn.append(r[ix['Cluster']].strip().replace('_', ' ')); ca.append(int(round(min(max(fl(r[ix['AgeNN']], 8.5), 6.0), 10.2) * 20)))
    D['CLUSTER_NAMES'] = '|'.join(cn); D['CLUSTER_AGE'] = b64(np.array(ca, dtype=np.uint8)); assert len(cn) == 2012, len(cn)
    cols, rows = table(RAW / 'ungc.tsv', 'Dist', 'A26'); ix = {c: i for i, c in enumerate(cols)}
    D['NEAR_NAMES'] = '|'.join(r[ix['Name']].strip() for r in rows if fl(r[ix['Dist']]) > 1.45 and not math.isnan(fl(r[ix['_RAJ2000']])))
    print('amas nommés :', len(cn), cn[:3], cn[150:153], '| galaxies proches nommées :', D['NEAR_NAMES'].count('|') + 1)
    # ------------------------------------------------------------------ Andromède : position et vitesse dans le repère galactocentrique (mouvement propre Gaia DR3, Salomon et al. 2021)
    from astropy.coordinates import SkyCoord, Galactocentric
    import astropy.units as u
    with open(OUT / 'data2.js', encoding='utf-8') as fh:
        m31 = next(o for o in json.loads(re.search(r'"LOCAL":(\[.*?\]),"NEAR"', fh.read()).group(1)) if o['n'].startswith('Andromède'))
    c = SkyCoord(ra=10.684708 * u.deg, dec=41.26875 * u.deg, distance=m31['d'] * 1000 * u.kpc, pm_ra_cosdec=48.98e-3 * u.mas / u.yr, pm_dec=-36.85e-3 * u.mas / u.yr, radial_velocity=-301 * u.km / u.s)
    g = c.transform_to(Galactocentric(galcen_distance=8.2 * u.kpc, z_sun=6.6 * u.pc, galcen_v_sun=(11.1, 242.24, 7.25) * u.km / u.s))
    P = np.array([g.x.to_value(u.kpc), g.y.to_value(u.kpc), g.z.to_value(u.kpc)]); V = np.array([g.v_x.to_value(u.km / u.s), g.v_y.to_value(u.km / u.s), g.v_z.to_value(u.km / u.s)])
    vr = float(P.dot(V) / np.linalg.norm(P)); vt = float(np.linalg.norm(V - vr * P / np.linalg.norm(P)))
    # sens de rotation du disque d'Andromède : le côté sud-ouest s'approche, le nord-est s'éloigne
    los = eq_unit(np.array([10.684708]), np.array([41.26875]))[0]; north = np.array([0, 0, 1.0]) - los * los[2]; north /= np.linalg.norm(north); east = np.cross(north, los)
    if east.dot(np.array([-math.sin(math.radians(10.684708)), math.cos(math.radians(10.684708)), 0])) < 0: east = -east
    ne = math.cos(math.radians(35)) * north + math.sin(math.radians(35)) * east; nrm = np.array(m31['normal']) @ RX            # normale du disque, repère équatorial
    spin = nrm if np.cross(nrm, ne).dot(los) > 0 else -nrm
    D['M31'] = {'pos': [round(float(x), 3) for x in P], 'vel': [round(float(x), 3) for x in V], 'vrad': round(vr, 1), 'vtan': round(vt, 1), 'spin': [round(float(x), 5) for x in A_GAL @ spin]}
    print('Andromède : position galactocentrique', D['M31']['pos'], 'kpc | vitesse', D['M31']['vel'], 'km/s | radiale %.1f, transverse %.1f km/s' % (vr, vt))
    js = 'Object.assign(DATA, ' + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + ');\n'
    with open(OUT / 'data3.js', 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(js)
    for k, v in sorted(D.items(), key=lambda kv: -len(json.dumps(kv[1])))[:7]: print('   %-14s %5.0f ko' % (k, len(json.dumps(v, ensure_ascii=False)) / 1024))
    print('app/gen/data3.js : %.0f ko' % (len(js.encode()) / 1024))


if __name__ == '__main__':
    main()
