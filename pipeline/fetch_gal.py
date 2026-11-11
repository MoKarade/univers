import requests, json, math, re, os, io, time, threading, queue
from PIL import Image, ImageStat
UA = {'User-Agent': 'UniversArtifactBuilder/1.9 (educational visualization)'}; os.makedirs('raw/gal', exist_ok=True); NM = json.load(open('/tmp/names2.json')); T0 = time.time(); LIMIT = 245
def fl(s):
    try: return float(str(s).strip())
    except Exception: return None
def tsv(fn):
    L = [l.rstrip('\n').split('\t') for l in open(fn, errors='replace') if l.strip() and not l.startswith('#')]; cols = [c.strip() for c in L[0]]; return cols, [[c.strip() for c in r] + [''] * (len(cols) - len(r)) for r in L[3:]]
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower()); G = []
# Groupe local (McConnachie 2012)
cols, rows = tsv('raw/mcconnachie.tsv'); c = {k: i for i, k in enumerate(cols)}; byd = {}
for r in rows:
    if fl(r[c['D']]): byd.setdefault(round(fl(r[c['D']]) / 1000, 3), []).append(r)
OVR = {'Andromeda': 200, 'Triangulum': 72, 'LMC': 640, 'SMC': 310, 'NGC 6822': 20, 'IC 10': 9, 'NGC 205': 22, 'M32': 10, 'NGC 147': 16, 'NGC 185': 14, 'IC 1613': 20, 'WLM': 14, 'NGC 3109': 20, 'Sextans A': 8, 'Sextans B': 8, 'Leo A': 7, 'Fornax': 70, 'Sculptor': 60, 'Carina': 30, 'Draco': 40, 'Ursa Minor': 40, 'Leo I': 14, 'Leo II': 12, 'Sextans (I)': 60, 'Phoenix': 8, 'Pegasus dIrr': 7, 'IC 5152': 7, 'NGC 55': 36, 'NGC 300': 26, 'Canis Major': 0, 'Sagittarius dSph': 0}
for i, (n, d) in enumerate(NM['local']):
    cand = byd.get(round(d, 3), []); r = cand[0] if len(cand) == 1 else next((q for q in cand if norm(q[c['Name']]) in norm(n) or norm(n) in norm(q[c['Name']])), cand[0] if cand else None)
    if r is None or fl(r[c['_RAJ2000']]) is None: continue
    nm = r[c['Name']]; rh = fl(r[c['R1']]); fov = OVR.get(nm, min(max(6 * rh, 4), 45) if rh else 6)
    if fov > 0: G.append(['lg', i, n, fl(r[c['_RAJ2000']]), fl(r[c['_DEJ2000']]), fov, d])
# galaxies proches (Karachentsev et al. 2013) : taille angulaire a26
cols, rows = tsv('raw/ungc.tsv'); c = {k: i for i, k in enumerate(cols)}; U = {norm(r[c['Name']]): r for r in rows}; lgpos = [(g[3], g[4]) for g in G]
for i, n in enumerate(NM['near']):
    r = U.get(norm(n))
    if r is None or fl(r[c['_RAJ2000']]) is None: continue
    ra, de = fl(r[c['_RAJ2000']]), fl(r[c['_DEJ2000']]); a26 = fl(r[c['a26']]) or 1.5
    if any(abs(de - q[1]) < 0.25 and abs((ra - q[0] + 180) % 360 - 180) * math.cos(math.radians(de)) < 0.25 for q in lgpos): continue
    G.append(['near', i, n, ra, de, min(max(1.7 * a26, 2.5), 200), fl(r[c['Dist']]) or 5])
# galaxies hôtes d'un trou noir supermassif mesuré
L = [l.rstrip('\n').split('\t') for l in open('raw/smbh.tsv', errors='replace') if l.strip() and not l.startswith('#')]; t2 = []; started = 0
for l in open('raw/smbh.tsv', errors='replace'):
    q = [x.strip() for x in l.split('\t')]
    if len(q) > 8 and re.match(r'^\d', q[0]) and fl(q[5]) and fl(q[5]) > 0.05 and fl(q[7]) is not None: t2.append(q)
PRETTY = {'NGC4486': 'M87', 'NGC0224': 'Andromède (M31)', 'NGC3031': 'M81', 'NGC4594': 'Sombrero (M104)', 'NGC5128': 'Centaurus A', 'NGC4258': 'M106', 'NGC0221': 'M32', 'NGC4374': 'M84', 'NGC4649': 'M60', 'NGC4472': 'M49', 'NGC3115': 'NGC 3115', 'NGC4889': 'NGC 4889', 'NGC1277': 'NGC 1277'}
bn = {n: i for i, n in enumerate(NM['bhm'])}; have = [(g[3], g[4]) for g in G]
for q in t2:
    nm = PRETTY.get(q[3], re.sub(r'^(NGC|IC|UGC|Mrk|PG|ESO|Arp|Ark|3C|A)\s*0*(\d)', r'\1 \2', q[3]))
    if nm not in bn: continue
    ra, de, D = fl(q[0]), fl(q[1]), fl(q[5]); fov = min(max(math.degrees(2 * math.atan(28 / (D * 1000))) * 60, 1.6), 60)
    G.append(['bhm', bn[nm], nm, ra, de, fov, D, any(abs(de - h[1]) < 0.05 and abs((ra - h[0] + 180) % 360 - 180) * math.cos(math.radians(de)) < 0.05 for h in have)])
G.sort(key=lambda g: -g[5]); hi = set(id(g) for g in [g for g in G if g[0] != 'bhm' or not g[7]][:64])
json.dump(G, open('raw/gal/list.json', 'w'), ensure_ascii=False); print('galaxies à photographier : %d (groupe local %d, proches %d, hôtes de trous noirs %d)' % (len(G), sum(g[0] == 'lg' for g in G), sum(g[0] == 'near' for g in G), sum(g[0] == 'bhm' for g in G)))
stats = {'legacy': 0, 'dss': 0, 'fail': 0, 'cache': 0}; LOCK = threading.Lock()
def blank(b):
    try:
        im = Image.open(io.BytesIO(b)).convert('L'); st = ImageStat.Stat(im); ex = im.getextrema(); hist = im.histogram(); zero = sum(hist[:4]) / (im.size[0] * im.size[1]); return ex[1] < 28 or st.stddev[0] < 2.5 or zero > 0.30
    except Exception: return True
def get(g, px):
    fn = 'raw/gal/%s_%d_%d.jpg' % (g[0], g[1], px)
    if os.path.exists(fn):
        with LOCK: stats['cache'] += 1
        return
    if time.time() - T0 > LIMIT: return
    ra, de, fov = g[3], g[4], g[5]; b = None; src = None
    if fov * 60 / px < 30 and de > -68:
        try:
            r = requests.get('https://www.legacysurvey.org/viewer/jpeg-cutout', params={'ra': ra, 'dec': de, 'layer': 'ls-dr10', 'pixscale': round(fov * 60 / px, 3), 'size': px}, headers=UA, timeout=25)
            if r.status_code == 200 and len(r.content) > 800 and not blank(r.content): b = r.content; src = 'legacy'
        except Exception: pass
    if b is None and time.time() - T0 < LIMIT:
        try:
            r = requests.get('https://skyview.gsfc.nasa.gov/current/cgi/runquery.pl', params={'Position': '%.5f,%.5f' % (ra, de), 'Survey': 'DSS2 Red', 'Pixels': px, 'Size': round(fov / 60, 5), 'Return': 'JPEG', 'Scaling': 'Sqrt'}, headers=UA, timeout=45)
            if r.status_code == 200 and r.headers.get('content-type', '').startswith('image') and len(r.content) > 800: b = r.content; src = 'dss'
        except Exception: pass
    with LOCK: stats[src or 'fail'] += 1
    if b: open(fn, 'wb').write(b); open(fn + '.src', 'w').write(src)
qu = queue.Queue()
for g in G:
    if id(g) in hi: qu.put((g, 256))
for g in G:
    if g[0] != 'bhm' or not g[7]: qu.put((g, 96))
def worker():
    while True:
        try: g, px = qu.get_nowait()
        except Exception: return
        get(g, px)
th = [threading.Thread(target=worker, daemon=True) for _ in range(18)]; [t.start() for t in th]; [t.join(max(1, LIMIT + 10 - (time.time() - T0))) for t in th]
print('images :', stats, '| fichiers présents :', len([f for f in os.listdir('raw/gal') if f.endswith('.jpg')]), '| restantes dans la file :', qu.qsize(), '| %.0f s' % (time.time() - T0))
