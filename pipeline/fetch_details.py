import requests, re, json, time, threading, os
UA = {'User-Agent': 'UniversArtifactBuilder/1.6 (educational visualization)'}; out = {}; LOCK = threading.Lock()
def page(name, url):
    try:
        r = requests.get(url, headers=UA, timeout=60); open('raw/' + name, 'wb').write(r.content); out[name] = (r.status_code, len(r.content))
    except Exception as e: out[name] = ('ERR', str(e)[:100])
MOONS = [('Phobos', 401, 499), ('Deimos', 402, 499), ('Io', 501, 599), ('Europe', 502, 599), ('Ganymède', 503, 599), ('Callisto', 504, 599), ('Mimas', 601, 699), ('Encelade', 602, 699), ('Téthys', 603, 699), ('Dioné', 604, 699), ('Rhéa', 605, 699), ('Titan', 606, 699), ('Japet', 608, 699),
         ('Ariel', 701, 799), ('Umbriel', 702, 799), ('Titania', 703, 799), ('Obéron', 704, 799), ('Miranda', 705, 799), ('Triton', 801, 899)]
JD0 = 2461355.5; EL = {}
def hz(name, mid, cen):
    try:
        p = {'format': 'text', 'COMMAND': "'%d'" % mid, 'OBJ_DATA': 'NO', 'MAKE_EPHEM': 'YES', 'EPHEM_TYPE': 'ELEMENTS', 'CENTER': "'500@%d'" % cen, 'REF_PLANE': 'ECLIPTIC', 'TLIST': "'%.1f'" % JD0, 'CSV_FORMAT': 'YES', 'OUT_UNITS': "'KM-D'"}
        t = requests.get('https://ssd.jpl.nasa.gov/api/horizons.api', params=p, headers=UA, timeout=90).text; row = t.split('$$SOE')[1].split('$$EOE')[0].strip().split('\n')[0].split(',')
        # JDTDB, date, EC, QR, IN, OM, W, Tp, N, MA, TA, A, AD, PR
        e = {'ec': float(row[2]), 'qr': float(row[3]), 'inc': float(row[4]), 'om': float(row[5]), 'w': float(row[6]), 'n': float(row[8]), 'ma': float(row[9]), 'a': float(row[11]), 'pr': float(row[13])}
        p2 = dict(p); p2.update({'EPHEM_TYPE': 'VECTORS', 'TLIST': "'%.1f,%.1f,%.1f'" % (JD0 + 5, JD0 + 30, JD0 + 365), 'VEC_TABLE': '1'}); p2.pop('OUT_UNITS'); p2['OUT_UNITS'] = "'KM-D'"
        t2 = requests.get('https://ssd.jpl.nasa.gov/api/horizons.api', params=p2, headers=UA, timeout=90).text; vs = [[float(x) for x in l.split(',')[2:5]] for l in t2.split('$$SOE')[1].split('$$EOE')[0].strip().split('\n') if l.strip()]
        with LOCK: EL[name] = {'id': mid, 'cen': cen, 'el': e, 'chk': vs}
    except Exception as ex:
        with LOCK: EL[name] = {'err': str(ex)[:120]}
th = [threading.Thread(target=page, args=a, daemon=True) for a in (('factsheet.html', 'https://nssdc.gsfc.nasa.gov/planetary/factsheet/'), ('sunfact.html', 'https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html'), ('moonfact.html', 'https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html'))]
[t.start() for t in th]
for k in range(0, len(MOONS), 4):
    tt = [threading.Thread(target=hz, args=m, daemon=True) for m in MOONS[k:k + 4]]; [t.start() for t in tt]; [t.join(120) for t in tt]
[t.join(60) for t in th]
json.dump({'jd0': JD0, 'moons': EL, 'order': [m[0] for m in MOONS]}, open('raw/moons.json', 'w'), ensure_ascii=False)
print(out); print('lunes reçues :', sum(1 for v in EL.values() if 'el' in v), '/', len(MOONS), '| erreurs :', {k: v['err'] for k, v in EL.items() if 'err' in v})
for k in ('Io', 'Titan', 'Triton'):
    if 'el' in EL.get(k, {}): print(k, EL[k]['el'])
