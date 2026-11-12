#!/usr/bin/env python3
"""Test à l'écran « recherche NGC/IC » (lot S, A5 par contournement : catalogue OpenNGC déposé à part de la page).

- en ouvrant « Aller à », le catalogue se charge ; « M104 » trouve NGC 4594 (la Sombrero) ;
- la toucher ouvre sa fiche (z tel que donné par OpenNGC, distance calculée comme les galaxies des relevés : à si faible z,
  c·z/H0 à 3 % près avec H0 = 67,4) et y va ;
- « M42 » (nébuleuse d'Orion, sans décalage vers le rouge) ouvre sa fiche sans déplacement, distance « inconnue ici » ;
- sans le fichier, la recherche des noms de la page marche encore et la page n'a pas d'erreur.
Lancer : python3 app/build.py puis python -X utf8 app/test/lot_s_ngc.py [desk|phone]
"""
import functools
import http.server
import os
import shutil
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright

ICI = os.path.dirname(os.path.abspath(__file__))
RAW = os.environ.get('U_RAW', os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'univers-raw'))
MODE = sys.argv[1] if len(sys.argv) > 1 else 'desk'
NB = ' '


def main():
    bad = 0

    def check(ok, msg):
        nonlocal bad
        print(('OK    ' if ok else 'ÉCHEC ') + msg)
        bad += 0 if ok else 1

    d = tempfile.mkdtemp()
    shutil.copy(os.path.join(ICI, '..', '..', 'dist', 'index.html'), d)
    shutil.copy(os.path.join(RAW, 'openngc.json'), d)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=d))
    srv.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = 'http://127.0.0.1:%d/index.html' % srv.server_address[1]
    phone = MODE != 'desk'
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        ctx = b.new_context(viewport={'width': 390, 'height': 780} if phone else {'width': 1280, 'height': 800},
                            device_scale_factor=2 if phone else 1, has_touch=phone, is_mobile=phone, color_scheme='dark', reduced_motion='reduce')

        def ouvrir(ngc):
            pg = ctx.new_page()
            logs = []
            pg.on('pageerror', lambda e: logs.append(str(e)))
            pg.add_init_script("window.__TIER=%d; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[]; window.__NGC=%s;" % (0 if phone else 1, ngc))
            pg.goto(url)
            pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
            pg.evaluate("__U.S.playing = false; document.getElementById('b-find').click()")
            return pg, logs

        def chercher(pg, q):
            pg.evaluate("q => { const i = document.getElementById('find-q'); i.value = q; i.dispatchEvent(new Event('input')); }", q)
            return pg.evaluate("[...document.querySelectorAll('#find-res button')].map(b => b.textContent)")

        pg, logs = ouvrir("'openngc.json'")
        res = []
        for _ in range(60):            # le fichier se charge en arrière-plan à l'ouverture du panneau
            res = chercher(pg, 'M104')
            if any('NGC 4594' in r for r in res):
                break
            pg.wait_for_timeout(500)
        check(any('NGC 4594' in r and 'catalogue NGC/IC' in r for r in res), '« M104 » trouve NGC 4594 : %s' % res[:3])
        lr0 = pg.evaluate('__U.S.logR')
        pg.evaluate("[...document.querySelectorAll('#find-res button')].find(b => /NGC 4594/.test(b.textContent)).click()")
        pg.wait_for_function("!document.getElementById('card').hidden", timeout=60000)
        txt = pg.evaluate("(() => { const m = document.getElementById('card-more'); if (m && !m.hidden && /^Plus/.test(m.textContent)) m.click(); return document.getElementById('card').innerText; })()").replace(NB, ' ').replace(' ', ' ')
        z = [o for o in __import__('json').load(open(os.path.join(RAW, 'openngc.json'), encoding='utf-8'))['o'] if o[0].startswith('NGC 4594 ')][0][6]
        zs = ('%.3g' % z).replace('.', ',')
        manque = [a for a in ('NGC 4594', 'z = ' + zs, 'calculée d’après z', 'OpenNGC') if a not in txt]
        check(not manque, 'fiche de la Sombrero%s' % ((' : manque %s dans « %s »' % (manque, txt.replace(chr(10), ' / ')[:300])) if manque else ''))
        dist = pg.evaluate("(() => { const o = __U.S.sel; return o ? Math.hypot(...o.get().map((v, k) => v - __U.F.gcRel[k])) / 3.0856775814913673e22 / __U.F.cos.a : null; })()")
        att = 299792.458 * z / 67.4
        check(dist is not None and abs(dist / att - 1) < 0.03, 'distance calculée : %.2f Mpc (c·z/H0 = %.2f Mpc)' % (dist or 0, att))
        pg.wait_for_function(f"Math.abs(__U.S.logR - {lr0}) > 3", timeout=120000)
        check(True, 'la vue part vers la galaxie (échelle %.1f → %.1f)' % (lr0, pg.evaluate('__U.S.logR')))
        pg.screenshot(path='/tmp/lot_s_ngc_%s_m104.png' % MODE)

        pg.evaluate("__U.select(null); __U.goStop(__U.STOPS.find(s => /Système solaire/.test(s.name)), true); document.getElementById('b-find').click()")
        pg.wait_for_function("__U.S.logR < 14", timeout=120000)
        lr1 = pg.evaluate('__U.S.logR')
        res = chercher(pg, 'M42')
        pg.evaluate("[...document.querySelectorAll('#find-res button')].find(b => /NGC 1976/.test(b.textContent)).click()")
        pg.wait_for_function("!document.getElementById('card').hidden", timeout=60000)
        txt = pg.evaluate("document.getElementById('card').innerText")
        f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() > {f0} + 6', timeout=180000)
        check('inconnue ici' in txt and abs(pg.evaluate('__U.S.logR') - lr1) < 0.01, 'M42 : fiche sans déplacement, distance « inconnue ici »')
        check(not logs, 'aucune erreur de page (%d)' % len(logs))
        pg.close()

        pg, logs = ouvrir("'absent.json'")
        res = chercher(pg, 'Sirius')
        pg.wait_for_timeout(1500)
        check(any('Sirius' in r for r in res) and not logs, 'sans le fichier : « Sirius » trouvé, aucune erreur (%s)' % logs[:1])
        b.close()
    srv.shutdown()
    print('RÉSULTAT (%s) :' % MODE, 'PASSE' if bad == 0 else '%d échec(s)' % bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
