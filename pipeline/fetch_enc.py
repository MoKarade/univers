# Étoiles de Gaia DR3 dont la trajectoire rectiligne passe à moins d'un parsec du Soleil. La requête est découpée par tranches de distance.
import requests, time, io, csv, json, sys
UA = {'User-Agent': 'UniversArtifactBuilder/2.2 (educational visualization)'}; TAP = 'https://gea.esac.esa.int/tap-server/tap'; T0 = time.time()
COLS = "g.source_id, g.ra, g.dec, g.parallax, g.parallax_error, g.pmra, g.pmdec, g.pm, g.radial_velocity, g.radial_velocity_error, g.phot_g_mean_mag, g.bp_rp, g.ruwe, g.rv_expected_sig_to_noise, g.rv_nb_transits"
def q(lo, hi):
    return ("SELECT " + COLS + " FROM gaiadr3.gaia_source AS g WHERE g.parallax > %s AND g.parallax <= %s AND g.radial_velocity IS NOT NULL AND g.parallax_over_error > 5 AND g.pm < 0.0844 * g.parallax * g.parallax "
            "AND (1000.0/g.parallax) * (4.74047*g.pm/g.parallax) / SQRT(POWER(4.74047*g.pm/g.parallax, 2) + POWER(g.radial_velocity, 2)) < 1.0") % (lo, hi)
R = [(20, 1000), (8, 20), (4, 8), (2.5, 4), (1.6, 2.5)]; jobs = {}
for lo, hi in R:
    try:
        r = requests.post(TAP + '/async', data={'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'csv', 'PHASE': 'RUN', 'QUERY': q(lo, hi)}, headers=UA, timeout=60, allow_redirects=False); jobs[(lo, hi)] = r.headers.get('Location') or r.url
    except Exception as e: print('soumission', lo, hi, 'ERR', str(e)[:60])
rows = []; done = {}
while time.time() - T0 < 215 and len(done) < len(jobs):
    for k, job in jobs.items():
        if k in done: continue
        try: ph = requests.get(job + '/phase', headers=UA, timeout=30).text.strip()
        except Exception: continue
        if ph == 'COMPLETED':
            t = requests.get(job + '/results/result', headers=UA, timeout=120).text; rr = list(csv.DictReader(io.StringIO(t))); rows += rr; done[k] = len(rr); print('parallaxe %s a %s : %d etoiles (%.0f s)' % (k[0], k[1], len(rr), time.time() - T0))
        elif ph in ('ERROR', 'ABORTED'): done[k] = ph; print('parallaxe %s a %s : %s (%.0f s)' % (k[0], k[1], ph, time.time() - T0))
    time.sleep(5)
json.dump(rows, open('raw/enc_gaia.json', 'w')); print('total :', len(rows), '| tranches finies :', len(done), 'sur', len(jobs))
