import importlib.util, json, os, sys, threading, time, urllib.parse
from pathlib import Path

_PIPE_DIR = str(Path(__file__).resolve().parent)
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import PIPELINE_RAW  # noqa: E402

RAW = PIPELINE_RAW
UA = {'User-Agent': 'UniversArtifactBuilder/1.1 (educational visualization)'}
ASTRO_DEPS = ('jplephem', 'astropy_healpix', 'pymeeus')
T0 = time.time()
status = {}
requests = None


def check_deps():
    missing = [m for m in ('requests', *ASTRO_DEPS) if importlib.util.find_spec(m) is None]
    if missing:
        raise ImportError(
            f"Dépendances manquantes ({', '.join(missing)}). "
            "Installez les profils 'core' et 'astro' déclarés dans pipeline/pyproject.toml."
        )


def save(name, url, method='get', timeout=200, **kw):
    path = os.path.join(RAW, name)
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        status[name] = ('cache', os.path.getsize(path)); return True
    try:
        r = requests.request(method, url, headers=UA, timeout=(15, timeout), stream=True, **kw)
        if r.status_code != 200:
            status[name] = ('HTTP %d' % r.status_code, r.text[:160].replace('\n', ' ')); return False
        n = 0
        with open(path + '.part', 'wb') as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk); n += len(chunk)
                if time.time() - T0 > 255: raise TimeoutError('délai global')
        os.replace(path + '.part', path); status[name] = ('ok', n); return True
    except Exception as e:
        status[name] = ('ERR', str(e)[:160]); return False


def vizier(name, source, extra=''):
    for host in ('vizier.cds.unistra.fr', 'vizier.cfa.harvard.edu'):
        url = f'https://{host}/viz-bin/asu-tsv?-source={urllib.parse.quote(source, safe="/")}&-out.max=unlimited&-out.all&-out.add=_RAJ,_DEJ{extra}'
        if save(name, url, timeout=150): return


def sbdb(name, params):
    save(name, 'https://ssd-api.jpl.nasa.gov/sbdb_query.api?' + urllib.parse.urlencode(params), timeout=150)


def sky(name, sql):
    save(name, 'https://skyserver.sdss.org/dr17/SkyServerWS/SearchTools/SqlSearch?' + urllib.parse.urlencode({'cmd': sql, 'format': 'csv'}), timeout=200)


def desi():
    tap = 'https://datalab.noirlab.edu/tap/sync'
    try:
        r = requests.post(tap, data={'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'csv', 'QUERY': "SELECT column_name FROM tap_schema.columns WHERE table_name='desi_dr1.zpix'"}, headers=UA, timeout=(15, 60))
        cols = [c.strip().strip('"') for c in r.text.splitlines()[1:]]
        status['desi_schema'] = (r.status_code, len(cols), ' '.join(cols)[:400])
        if r.status_code != 200 or not cols: return
        ra = next((c for c in ('target_ra', 'mean_fiber_ra', 'ra') if c in cols), None); dec = next((c for c in ('target_dec', 'mean_fiber_dec', 'dec') if c in cols), None)
        if not ra or 'z' not in cols: return
        where = ["zwarn=0", "z>0.002", "z<5.5", "spectype<>'STAR'"]
        if 'zcat_primary' in cols: where.append("zcat_primary='t'")
        if 'random_id' in cols: where.append('random_id<1.1')
        q = f"SELECT {ra},{dec},z,spectype FROM desi_dr1.zpix WHERE " + ' AND '.join(where)
        status['desi_query'] = q
        save('desi.csv', tap, method='post', timeout=200, data={'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'csv', 'QUERY': q})
    except Exception as e:
        status['desi'] = ('ERR', str(e)[:200])


def head(name, n=3, skip='#'):
    p = os.path.join(RAW, name)
    if not os.path.exists(p): return
    with open(p, encoding='utf-8', errors='replace') as f:
        lines = [l.rstrip('\n') for l in f if not l.startswith(skip) and l.strip()]
    print('---', name, len(lines), 'lignes'); [print('   ', l[:420]) for l in lines[:n]]


def main():
    global requests, T0
    check_deps()
    import requests as _requests
    requests = _requests
    T0 = time.time()
    RAW.mkdir(parents=True, exist_ok=True)
    jobs = [
        (save, ('de440s.bsp', 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp')),
        (save, ('wmap_ilc.fits', 'https://lambda.gsfc.nasa.gov/data/map/dr5/dfp/ilc/wmap_ilc_9yr_v5.fits')),
        (sbdb, ('sbdb_ast.json', {'fields': 'pdes,name,a,e,i,om,w,ma,epoch,H,class', 'sb-kind': 'a', 'sb-cdata': json.dumps({'AND': ['H|LT|12.6', 'a|LT|6.6', 'e|LT|0.9']})})),
        (sbdb, ('sbdb_tno.json', {'fields': 'pdes,name,a,e,i,om,w,ma,epoch,H,class,data_arc,condition_code', 'sb-kind': 'a', 'sb-class': 'TNO,CEN'})),
        (vizier, ('2mrs.tsv', 'J/ApJS/199/26/table3')),
        (vizier, ('ungc.tsv', 'J/AJ/145/101')),
        (vizier, ('mcconnachie.tsv', 'J/AJ/144/4')),
        (vizier, ('harris.tsv', 'VII/202')),
        (vizier, ('openclusters.tsv', 'J/A+A/640/A1/table1')),
        (sky, ('sdss_gal.csv', "SELECT ra,dec,z FROM SpecObj WHERE class='GALAXY' AND zWarning=0 AND z>0.003 AND z<1.3 AND fiberID%8=0")),
        (sky, ('sdss_qso.csv', "SELECT ra,dec,z FROM SpecObj WHERE class='QSO' AND zWarning=0 AND z>0.2 AND z<6 AND fiberID%16=0")),
        (desi, ()),
    ]
    th = [threading.Thread(target=f, args=a, daemon=True) for f, a in jobs]
    for t in th: t.start()
    for t in th: t.join(max(1, 262 - (time.time() - T0)))
    for k, v in status.items(): print('%-18s %s' % (k, v))
    for nme in ('2mrs.tsv', 'openclusters.tsv', 'sdss_gal.csv', 'sdss_qso.csv', 'desi.csv'): head(nme)
    for nme in ('ungc.tsv', 'mcconnachie.tsv', 'harris.tsv'):
        p = os.path.join(RAW, nme)
        if os.path.exists(p):
            with open(p, encoding='utf-8', errors='replace') as fh:
                txt = fh.read().split('\n')
            print('---', nme, len(txt), 'lignes')
            for i, l in enumerate(txt):
                if l.startswith('#Name:') or l.startswith('#Title'): print('   ', l[:150])
                if l.startswith('#Name:'):
                    j = i
                    while j < len(txt) and (txt[j].startswith('#') or not txt[j].strip()): j += 1
                    print('    COLS', txt[j][:520]); print('    ROW ', txt[j + 3][:300] if j + 3 < len(txt) else '')
    for nme in ('sbdb_ast.json', 'sbdb_tno.json'):
        p = os.path.join(RAW, nme)
        if os.path.exists(p):
            try:
                with open(p, encoding='utf-8') as fh:
                    d = json.load(fh)
                print('---', nme, d.get('count'), d.get('fields'), d['data'][0] if d.get('data') else d)
            except Exception as e:
                with open(p, encoding='utf-8', errors='replace') as fh:
                    snippet = fh.read()[:300]
                print(nme, 'ERR', e, snippet)


if __name__ == '__main__':
    main()
