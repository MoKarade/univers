# Étoiles qui frôlent le Soleil : table de Bailer-Jones 2022 (Gaia DR3). Les rencontres sans réserve sont simulées ; les douteuses sont seulement listées.
# S'y ajoute l'étoile de Scholz (Dupuy et al. 2019), absente de la table parce que Gaia n'en donne pas la vitesse.
# La trajectoire tracée reprend l'instant, la distance et la vitesse publiés (médianes) ; le côté du passage vient du mouvement rectiligne mesuré par Gaia.
import csv, json, math, re, base64, struct
rows = list(csv.DictReader(open('raw/bj22.csv'))); gaia = {g['source_id']: g for g in json.load(open('raw/bj22_gaia.json'))}; names = json.load(open('raw/bj22_names.json'))
tex = open('raw/bj22_figures_encounters.tex').read(); flag = {}
for l in tex.split('\n'):
    m = re.search(r'(\d{17,19})', l)
    if m: pre = l.split('&')[0].replace('\\hphantom{\\knownbinary}', ''); flag[m.group(1)] = ('d' if '\\dubious' in pre else '') + ('b' if '\\knownbinary' in pre else '')
good = [r for r in rows if not flag.get(r['source_id'], '')]; print('table : %d etoiles | douteuses : %d | binaires larges : %d | sans reserve : %d' % (len(rows), sum('d' in v for v in flag.values()), sum(v == 'b' for v in flag.values()), len(good)))
# catalogue principal de la page, pour reconnaître les étoiles déjà présentes
src = open('../gen/data3.js').read(); N = int(re.search(r'"STARS_N":(\d+)', src).group(1)); geo = base64.b64decode(re.search(r'"STARS_GEO":"([^"]+)"', src).group(1)); G = struct.unpack('<%dH' % (N * 3), geo[:N * 6])
T1 = []
for i in range(N):
    lon = G[i * 3] / 65535 * 2 * math.pi; lat = (G[i * 3 + 1] / 65535 - 0.5) * math.pi; d = 10 ** (G[i * 3 + 2] / 65535 * 5.5 - 1); cl = math.cos(lat); T1.append((d * cl * math.cos(lon), d * cl * math.sin(lon), d * math.sin(lat)))
EPS = math.radians(23.4392911); ce, se = math.cos(EPS), math.sin(EPS); PC = 3.2615637769; KY = 977792.2
def ecl(v): return (v[0], v[1] * ce + v[2] * se, -v[1] * se + v[2] * ce)
def massOf(mg, bp):
    if mg > 9.5 and bp < 1.2: return 0.6                      # naine blanche
    T = [(0.5, 2.6), (1.5, 2.0), (2.5, 1.6), (3.5, 1.3), (4.7, 1.0), (5.6, 0.87), (6.6, 0.72), (7.7, 0.62), (9.0, 0.50), (10.0, 0.40), (11.0, 0.28), (12.0, 0.20), (13.0, 0.15), (14.0, 0.12), (15.5, 0.09)]
    if mg <= T[0][0]: return T[0][1]
    for (a, ma), (b, mb) in zip(T, T[1:]):
        if mg <= b: return math.exp(math.log(ma) + (math.log(mb) - math.log(ma)) * (mg - a) / (b - a))
    return 0.08
SCH = {'source_id': 'scholz', 'tphmed': '-80.5', 'tph5': '-81.65', 'tph95': '-79.35', 'dphmed': str(68700 / 206264.806), 'dph5': str(65410 / 206264.806), 'dph95': str(71990 / 206264.806), 'vphmed': '83.2', 'par': '147.1', 'm_g': str(15.31 - 5 * math.log10(6.80 / 10)), 'bp_rp': '4.89', 'phot_g_mean_mag': '15.31'}
gaia['scholz'] = {'ra': '110.01336', 'dec': '-8.78107', 'pmra': '-40.3', 'pmdec': '-114.8', 'radial_velocity': '83.1', 'mass_flame': '0.1575'}; names['scholz'] = 'Étoile de Scholz'
out = []
for r in good + [SCH]:
    t = float(r['tphmed']) * 1e3
    g = gaia[r['source_id']]; a, de = math.radians(float(g['ra'])), math.radians(float(g['dec'])); par = float(r['par']); pmra, pmde, rv = float(g['pmra']), float(g['pmdec']), float(g['radial_velocity'])
    rh = (math.cos(de) * math.cos(a), math.cos(de) * math.sin(a), math.sin(de)); ea = (-math.sin(a), math.cos(a), 0.0); ed = (-math.sin(de) * math.cos(a), -math.sin(de) * math.sin(a), math.cos(de)); k = 4.74047 / par
    v = tuple(rv * rh[j] + k * (pmra * ea[j] + pmde * ed[j]) for j in range(3)); d = 1000 / par; r0 = tuple(d * x for x in rh); v2 = sum(x * x for x in v); ts = -sum(r0[j] * v[j] for j in range(3)) / v2
    b = tuple(r0[j] + v[j] * ts for j in range(3)); bl = math.sqrt(sum(x * x for x in b)); vl = math.sqrt(v2); bh = ecl(tuple(x / bl for x in b)); vh = ecl(tuple(x / vl for x in v))
    dp, vp = float(r['dphmed']), float(r['vphmed']); vly = vp / 299792.458; p0 = tuple(bh[j] * dp * PC - vh[j] * vly * t for j in range(3)); now = ecl(tuple(x * PC for x in r0))
    dn = math.sqrt(sum(x * x for x in now)); hit = -1; bestA = 9
    for i, q in enumerate(T1):                       # même direction (à 0,1 degré près) et même distance (à 15 % près)
        dq = math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2])
        if abs(dq / dn - 1) > 0.15: continue
        ang = math.sqrt(max(0.0, 2 - 2 * (q[0] * now[0] + q[1] * now[1] + q[2] * now[2]) / (dq * dn)))
        if ang < 0.0018 and ang < bestA: bestA = ang; hit = i
    mg, bp, Gm = float(r['m_g']), float(r['bp_rp'] or 1.0), float(r['phot_g_mean_mag']); gv = -0.02704 + 0.01424 * bp - 0.2156 * bp * bp + 0.01426 * bp ** 3; mv = mg - gv; bv = max(-0.2, min(1.9, 0.0981 + 0.9296 * bp - 0.2145 * bp * bp + 0.0397 * bp ** 3 if bp < 2.2 else 1.5 + 0.12 * (bp - 2.2)))
    mf = g.get('mass_flame'); mass = float(mf) if mf else massOf(mg, bp); nm = names.get(r['source_id'], 'Gaia DR3 ' + r['source_id']); nm = re.sub(r'^(NAME|\*|V\*)\s+', '', nm); nm = {'4270814637616488064': 'Gliese 710', '5853498713190525696': 'Proxima du Centaure', '1926461164913660160': 'Ross 248'}.get(r['source_id'], nm)
    out.append({'n': nm, 'g': r['source_id'], 'i': hit, 'p': [round(x, 6) for x in p0], 'v': [round(vh[j] * vp, 6) for j in range(3)], 'now': [round(x, 4) for x in now], 'mv': round(mv, 2), 'bv': round(bv, 2), 'G': round(Gm, 1), 'm': round(mass, 2), 't': round(t), 't5': round(float(r['tph5']) * 1e3), 't95': round(float(r['tph95']) * 1e3), 'd': dp, 'd5': float(r['dph5']), 'd95': float(r['dph95']), 'vk': vp, 'lma': round(bl, 4)})
    if r is SCH: out[-1].update({'src': 'Dupuy et al. 2019 (Astronomical Journal 158, 174)', 'title': 'L’étoile de Scholz frôle le système solaire', 'mv': 19.1, 'bv': 1.9})
out.sort(key=lambda o: o['d'])
dub = [{'n': re.sub(r'^(NAME|\*|V\*)\s+', '', names.get(r['source_id'], 'Gaia DR3 ' + r['source_id'])), 'g': r['source_id'], 'f': flag[r['source_id']], 't': round(float(r['tphmed']) * 1e3), 'd': float(r['dphmed']), 'd5': float(r['dph5']), 'd95': float(r['dph95']), 'vk': float(r['vphmed'])} for r in rows if flag.get(r['source_id'], '')]
print('retenues (sans reserve, plus l etoile de Scholz) :', len(out), '| deja dans le catalogue principal :', sum(o['i'] >= 0 for o in out))
for o in out[:14]: print('  %-28s %+6.0f milliers d annees | %.3f pc (%.3f a %.3f) soit %6d UA | ligne droite : %.3f pc | %5.1f km/s | %.2f masse solaire | G=%.1f | %s' % (o['n'][:28], o['t'] / 1e3, o['d'], o['d5'], o['d95'], o['d'] * 206265, o['lma'], o['vk'], o['m'], o['G'], 'catalogue principal n%d' % o['i'] if o['i'] >= 0 else 'ajoutee'))
open('../gen/data13.js', 'w', encoding='utf-8').write('Object.assign(DATA, ' + json.dumps({'PASSERS': out, 'PASS_DUB': dub, 'PASS_STATS': {'total': len(rows), 'good': len(good), 'kept': len(out), 'dub': len(dub)}}, ensure_ascii=False, separators=(',', ':')) + ');\n'); print('data13.js :', len(open('../gen/data13.js').read()), 'caracteres')
