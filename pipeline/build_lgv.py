# Vitesses mesurées des galaxies du Groupe local (Local Volume Database, Pace 2024) : vitesse radiale et mouvement propre -> vitesse dans les axes de la Galaxie, vue du Soleil.
import csv, json, math, re, subprocess
rows = list(csv.DictReader(open('raw/dwarf_all.csv')))
js = subprocess.run(['node', '-e', "const fs=require('fs');let s='';for(const f of ['data.js','data2.js','data3.js','data4.js','data5.js','data6.js','data7.js','data8.js','data9.js']){try{s+=fs.readFileSync('../gen/'+f,'utf8')}catch(e){}} global.atob=x=>Buffer.from(x,'base64').toString('binary'); var DATA; eval(s.replace(/const DATA\\s*=/,'DATA =')); console.log(JSON.stringify({names: DATA.LOCAL.map(g=>g.n), en: DATA.LG_X.map(x=>x[5]), pos: DATA.LOCAL.map(g=>g.pos)}));"], capture_output=True, text=True).stdout
D = json.loads(js); EN = D['en']; print('galaxies de la page :', len(EN))
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower().replace('dsph', '').replace('dwarf', '').replace('(i)', '1'))
ROM = {'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 'vi': '6', 'vii': '7', 'ix': '9', 'x': '10', 'xi': '11', 'xii': '12', 'xiii': '13', 'xiv': '14', 'xv': '15', 'xvi': '16', 'xvii': '17', 'xviii': '18', 'xix': '19', 'xx': '20', 'xxi': '21', 'xxii': '22', 'xxiii': '23', 'xxiv': '24', 'xxv': '25', 'xxvi': '26', 'xxvii': '27', 'xxviii': '28', 'xxix': '29', 'xxx': '30', 'xxxi': '31', 'xxxii': '32', 'xxxiii': '33', 'i': '1'}
def key(s):
    s = s.replace('(I)', 'I'); parts = s.split(); 
    if parts and parts[-1].lower() in ROM: parts[-1] = ROM[parts[-1].lower()]
    return norm(' '.join(parts))
ALIAS = {'triangulum': 'm33', 'sagittarius': 'sagittarius1', 'sextans': 'sextans1', 'ursamajor': 'ursamajor1', 'bootes': 'bootes1', 'canesvenatici': 'canesvenatici1', 'm110': 'ngc205', 'leot': 'leot', 'segue': 'segue1', 'pegasus': 'pegasusdirr', 'cetus': 'cetus', 'carina': 'carina1', 'draco': 'draco1', 'leo1': 'leo1', 'fornax': 'fornax1', 'sculptor': 'sculptor1', 'ursaminor': 'ursaminor1', 'hercules': 'hercules1', 'phoenix': 'phoenix1', 'tucana': 'tucana1', 'andromeda': 'm31', 'wlm': 'wlm', 'aquarius': 'aquarius1', 'pisces': 'lgs3'}
L = {}
for r in rows:
    for nm in (r['name'], r['key']): L.setdefault(key(nm.replace('_', ' ')), r)
A = [[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132], [0.4941094278755837, -0.4448296299600112, 0.7469822444972189], [-0.8676661490190047, -0.1980763734312015, 0.4559837761750669]]
EPS = math.radians(23.4392911); ce, se = math.cos(EPS), math.sin(EPS)
LV = []
for r in rows:
    try: ra, de, d = float(r['ra']), float(r['dec']), float(r['distance'])
    except ValueError: continue
    a, b = math.radians(ra), math.radians(de); LV.append((r, (d * math.cos(b) * math.cos(a), d * math.cos(b) * math.sin(a), d * math.sin(b)), d))
out = {}; miss = []; nopm = []; MATCH = {}
for i, p in enumerate(D['pos']):
    x, y, z = p[0] * 1e3, p[1] * 1e3 * ce - p[2] * 1e3 * se, p[1] * 1e3 * se + p[2] * 1e3 * ce; dn = math.sqrt(x * x + y * y + z * z); best = None
    for r, q, d in LV:
        if abs(d / dn - 1) > 0.3: continue
        ang = math.acos(max(-1, min(1, (x * q[0] + y * q[1] + z * q[2]) / (dn * d))))
        if ang < math.radians(0.6) and (best is None or ang < best[0]): best = (ang, r)
    if not best: miss.append(D['names'][i]); continue
    r = best[1]; MATCH[i] = r['name']
    try: ra, de, d, vl, pa, pd = (float(r[c]) for c in ('ra', 'dec', 'distance', 'vlos_systemic', 'pmra', 'pmdec'))
    except ValueError: nopm.append(D['names'][i]); continue
    ea = max(abs(float(r['pmra_em'] or 0)), abs(float(r['pmra_ep'] or 0))); ed = max(abs(float(r['pmdec_em'] or 0)), abs(float(r['pmdec_ep'] or 0))); evt = 4.74047 * d * math.hypot(ea, ed)
    a, b = math.radians(ra), math.radians(de); rh = (math.cos(b) * math.cos(a), math.cos(b) * math.sin(a), math.sin(b)); e1 = (-math.sin(a), math.cos(a), 0.0); e2 = (-math.sin(b) * math.cos(a), -math.sin(b) * math.sin(a), math.cos(b)); kk = 4.74047 * d
    v = [vl * rh[j] + kk * (pa * e1[j] + pd * e2[j]) for j in range(3)]; g = [sum(A[m][j] * v[j] for j in range(3)) for m in range(3)]
    out[i] = {'v': [round(x, 1) for x in g], 'e': round(evt), 'd': round(d, 1), 'vl': round(vl, 1), 'n': r['name'], 'ref': (r.get('ref_proper_motion') or '')[:40]}
EN = [MATCH.get(i, D['names'][i]) for i in range(len(D['names']))]
bad = [(D['names'][i], D['en'][i], MATCH[i]) for i in MATCH if key(D['en'][i]) != key(MATCH[i]) and ALIAS.get(key(D['en'][i])) != key(MATCH[i]) and key(D['en'][i]) + '1' != key(MATCH[i])]
print('fiches de la page dont le nom anglais ne correspond pas a la position :', bad[:12])
print('avec vitesse complete :', len(out), '| sans mouvement propre :', len(nopm), '| non retrouvees :', miss)
big = [(EN[i], o['e']) for i, o in out.items() if o['e'] > 150]; print('incertitude transverse > 150 km/s (non simulees) :', big)
keep = {i: o for i, o in out.items() if o['e'] <= 150 and EN[i] not in ('LMC', 'SMC', 'M31', 'Andromeda')}
SUN = (11.1, 242.24, 7.25)
for i in list(keep)[:60]:
    o = keep[i]
    if EN[i] in ('Draco', 'Ursa Minor', 'Sextans', 'Sextans I', 'Fornax', 'Sagittarius', 'Leo I', 'NGC 6822', 'IC 10'): print('  %-18s d=%6.1f kpc | vitesse vue du Soleil %s | par rapport au centre de la Galaxie : %d km/s | incertitude +-%d km/s' % (EN[i], o['d'], o['v'], round(math.hypot(*(o['v'][j] + SUN[j] for j in range(3)))), o['e']))
# Galaxie du Triangle : absente de la base des naines. Déplacement mesuré par interférométrie radio et Gaia (van der Marel et al. 2019, moyenne VLBA + Gaia DR2), en millièmes de seconde d'arc par an.
i33 = next(i for i, n in enumerate(D['names']) if n.startswith('Galaxie du Triangle'))
ra, de, d, vl, pa, pd, ea, ed = 23.4621, 30.6599, 840.0, -179.2, 0.024, 0.003, 0.007, 0.008
a_, b_ = math.radians(ra), math.radians(de); rh = (math.cos(b_) * math.cos(a_), math.cos(b_) * math.sin(a_), math.sin(b_)); e1 = (-math.sin(a_), math.cos(a_), 0.0); e2 = (-math.sin(b_) * math.cos(a_), -math.sin(b_) * math.sin(a_), math.cos(b_)); kk = 4.74047 * d
v = [vl * rh[j] + kk * (pa * e1[j] + pd * e2[j]) for j in range(3)]; g33 = [sum(A[m][j] * v[j] for j in range(3)) for m in range(3)]
keep[i33] = {'v': [round(x, 1) for x in g33], 'e': round(kk * math.hypot(ea, ed)), 'd': d, 'vl': vl, 'n': 'M33'}; print('Triangle : vitesse vue du Soleil', keep[i33]['v'], '| par rapport au centre de la Galaxie', round(math.hypot(*(g33[j] + SUN[j] for j in range(3)))), 'km/s | incertitude', keep[i33]['e'])
SRC = {str(i33): 'van der Marel et al. 2019 (interférométrie radio et Gaia)'}
FIX = []
for i in MATCH:
    if D['names'][i] in ('Naine de la Petite Ourse', 'Naine du Sextant', 'Andromeda VI'):
        r = next(x for x in rows if x['name'] == MATCH[i]); FIX.append([i, MATCH[i], float(r['vlos_systemic']) if r['vlos_systemic'] else None])
print('fiches corrigees :', FIX)
open('../gen/data14.js', 'w', encoding='utf-8').write('Object.assign(DATA, ' + json.dumps({'LGX_FIX': FIX, 'LGV_SRC': SRC, 'LGV': {str(i): [o['v'][0], o['v'][1], o['v'][2], o['e'], o['vl']] for i, o in keep.items()}, 'LGV_N': {'kept': len(keep), 'nopm': len(nopm) + len(big), 'miss': len(miss)}}, separators=(',', ':')) + ');\n'); print('data14.js : %d galaxies simulees' % len(keep), '|', [EN[i] for i in keep][:70])
