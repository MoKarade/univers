import requests, json, time, urllib.parse, threading, math
UA = {'User-Agent': 'UniversArtifactBuilder/1.8 (educational visualization)'}; OUT = {}
def exo():
    cols = 'hostname,ra,dec,sy_dist,pl_name,pl_orbper,pl_orbsmax,pl_bmassj,pl_radj,pl_orbeccen,pl_eqt,disc_year,discoverymethod,st_spectype,st_mass,st_teff,st_rad,st_age'
    for url in ('https://exoplanetarchive.ipac.caltech.edu/TAP/sync?' + urllib.parse.urlencode({'query': 'select ' + cols + ' from pscomppars', 'format': 'csv'}),):
        try:
            r = requests.get(url, headers=UA, timeout=(15, 200)); OUT['exo'] = (r.status_code, len(r.content))
            if r.status_code == 200 and len(r.content) > 200000: open('raw/nasa_exo.csv', 'wb').write(r.content); return
        except Exception as e: OUT['exo'] = ('ERR', str(e)[:100])
JD0 = 2461355.5; COM = {}
def hz(cmd, jd):
    p = {'format': 'text', 'COMMAND': "'%s'" % cmd, 'OBJ_DATA': 'NO', 'MAKE_EPHEM': 'YES', 'EPHEM_TYPE': 'ELEMENTS', 'CENTER': "'500@10'", 'REF_PLANE': 'ECLIPTIC', 'TLIST': "'%.1f'" % jd, 'CSV_FORMAT': 'YES', 'OUT_UNITS': "'AU-D'"}
    t = requests.get('https://ssd.jpl.nasa.gov/api/horizons.api', params=p, headers=UA, timeout=90).text
    if '$$SOE' not in t: raise ValueError(t[-300:].replace('\n', ' ')[:200])
    row = t.split('$$SOE')[1].split('$$EOE')[0].strip().split('\n')[0].split(','); return {'e': float(row[2]), 'q': float(row[3]), 'i': float(row[4]), 'om': float(row[5]), 'w': float(row[6]), 'tp': float(row[7]), 'a': float(row[11]), 'pr': float(row[13])}
def comets():
    L = [('1P/Halley', 'DES=1P;CAP;NOFRAG'), ('2P/Encke', 'DES=2P;CAP;NOFRAG'), ('67P/Churyumov-Gerasimenko', 'DES=67P;CAP;NOFRAG'), ('109P/Swift-Tuttle', 'DES=109P;CAP;NOFRAG'), ('55P/Tempel-Tuttle', 'DES=55P;CAP;NOFRAG'), ('12P/Pons-Brooks', 'DES=12P;CAP;NOFRAG'), ('13P/Olbers', 'DES=13P;CAP;NOFRAG'), ('21P/Giacobini-Zinner', 'DES=21P;CAP;NOFRAG'), ('46P/Wirtanen', 'DES=46P;CAP;NOFRAG'), ('C/1995 O1 (Hale-Bopp)', 'DES=C/1995 O1;NOFRAG')]
    for nm, cmd in L:
        for attempt in range(2):
            try:
                e = hz(cmd, JD0); nxt = None
                if e['e'] < 1:
                    P = e['pr']; tp = e['tp']
                    while tp < JD0: tp += P          # prochain passage estimé, puis affiné avec des éléments calculés peu avant cette date
                    try:
                        e2 = hz(cmd, min(tp - 150, 2488000.0)); tp2 = e2['tp']
                        while tp2 < JD0 + 5: tp2 += e2['pr']
                        nxt = tp2
                    except Exception as ex2: nxt = None
                COM[nm] = {'el': e, 'next': nxt, 'next0': tp if e['e'] < 1 else None}; break
            except Exception as ex: COM[nm] = {'err': str(ex)[:120]}; time.sleep(3)
    json.dump({'jd0': JD0, 'comets': COM}, open('raw/comets_now.json', 'w'), ensure_ascii=False)
th = [threading.Thread(target=f, daemon=True) for f in (exo, comets)]; [t.start() for t in th]; [t.join(230) for t in th]
print(OUT)
def ymd(jd):
    z = int(jd + 0.5); a = int((z - 1867216.25) / 36524.25); A = z + 1 + a - a // 4; B = A + 1524; C = int((B - 122.1) / 365.25); Dd = int(365.25 * C); E = int((B - Dd) / 30.6001); d = B - Dd - int(30.6001 * E); m = E - 1 if E < 14 else E - 13; y = C - 4716 if m > 2 else C - 4715; return '%04d-%02d-%02d' % (y, m, d)
for k, v in COM.items():
    if 'el' in v: print('%-28s q %.4f e %.5f | prochain passage : %s (éléments d’aujourd’hui : %s)' % (k, v['el']['q'], v['el']['e'], ymd(v['next']) if v['next'] else '—', ymd(v['next0']) if v['next0'] else '—'))
    else: print('%-28s ÉCHEC %s' % (k, v['err']))
