#!/usr/bin/env python3
"""Test à l'écran « recherche NGC/IC » (lot S, A5 par contournement : catalogue OpenNGC déposé à part de la page).

- en ouvrant « Aller à », le catalogue se charge ; « NGC4594 » (la Sombrero, déjà dans la page) renvoie à sa fiche de la page ;
- NGC 4889 (amas de Coma) est placée dans la bonne direction et à la même distance que le point de relevé voisin, la vue y va,
  et la vue cône de lumière change sa distance et son libellé comme pour les relevés ;
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
            res = chercher(pg, 'NGC4594')
            if any('NGC 4594' in r for r in res):
                break
            pg.wait_for_timeout(500)
        # 1) la Sombrero est déjà dans la page (galaxies proches à distance mesurée) : renvoi à sa fiche, pas de seconde fiche
        check(any('NGC 4594' in r and 'fiche de la page' in r for r in res), '« NGC4594 » renvoie à la fiche de la page : %s' % res[:2])
        pg.evaluate("[...document.querySelectorAll('#find-res button')].find(b => /NGC 4594/.test(b.textContent)).click()")
        pg.wait_for_function("!document.getElementById('card').hidden", timeout=60000)
        sub = pg.evaluate("document.getElementById('card-sub').textContent")
        check('Galaxie proche' in sub, 'fiche ouverte : « %s »' % sub)

        # 2) NGC 4889 (amas de Coma, z ≈ 0,02, absente des galaxies proches) : placée comme les relevés.
        #    Contrôle indépendant : le point 2MRS le plus proche dans cette direction est à la même distance (3 %).
        pg.evaluate("__U.select(null); document.getElementById('b-find').click()")
        chercher(pg, 'NGC 4889')
        pg.evaluate("[...document.querySelectorAll('#find-res button')].find(b => /^NGC 4889/.test(b.textContent) && /catalogue NGC/.test(b.textContent)).click()")
        pg.wait_for_function("!document.getElementById('card').hidden", timeout=60000)
        r = pg.evaluate("""(() => { const o = __U.S.sel, F = __U.F, P = __U.Rr.pick, v = o.get().map((x, k) => (x - F.gcRel[k]) / 3.0856775814913673e22 / F.cos.a), d = Math.hypot(...v), u = v.map(x => x / d);
            let best = null; for (let i = 0; i < P.svN; i++) { const c = u[0] * P.svDir[i * 3] + u[1] * P.svDir[i * 3 + 1] + u[2] * P.svDir[i * 3 + 2]; if (!best || c > best.c) best = { c, d: P.svDist[i] }; }
            const e = 23.4392911 * Math.PI / 180, ra = 195.03387 * Math.PI / 180, de = 27.977 * Math.PI / 180, ex = Math.cos(de) * Math.cos(ra), ey = Math.cos(de) * Math.sin(ra), ez = Math.sin(de);
            const w = [ex, Math.cos(e) * ey + Math.sin(e) * ez, -Math.sin(e) * ey + Math.cos(e) * ez];
            return { d, dir: Math.acos(Math.min(1, u[0] * w[0] + u[1] * w[1] + u[2] * w[2])) * 180 / Math.PI, voisin: Math.acos(Math.min(1, best.c)) * 180 / Math.PI, dv: best.d, lr: o.lr }; })()""")
        check(r['dir'] < 0.01, 'direction de NGC 4889 : écart %.4f° (attendu < 0,01°)' % r['dir'])
        check(r['voisin'] < 0.2 and abs(r['d'] / r['dv'] - 1) < 0.03, 'même distance que le point de relevé voisin (%.2f° d’écart) : %.1f contre %.1f Mpc' % (r['voisin'], r['d'], r['dv']))
        pg.wait_for_function(f"Math.abs(__U.S.logR - {r['lr']}) < 0.15", timeout=120000)
        pg.wait_for_function("!__U.S.anim", timeout=120000)      # fin du vol
        f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() > {f0} + 20', timeout=180000)
        # projection à l'écran, même calcul que app/test/zoom_objet.py (PROJ)
        cen = pg.evaluate("""(() => { const U = window.__U, F = U.F, R = U.Rr, p = U.S.sel.get();
            const PM = new THREE.Matrix4().multiplyMatrices(R.camera.projectionMatrix, R.camera.matrixWorldInverse), e = PM.elements;
            const X = (p[0] - F.tg[0]) * F.s, Y = (p[1] - F.tg[1]) * F.s, Z = (p[2] - F.tg[2]) * F.s, w = e[3] * X + e[7] * Y + e[11] * Z + e[15];
            if (w <= 0) return null; const sx = ((e[0] * X + e[4] * Y + e[8] * Z + e[12]) / w * 0.5 + 0.5) * R.cssW, sy = (0.5 - (e[1] * X + e[5] * Y + e[9] * Z + e[13]) / w * 0.5) * R.cssH;
            return { off: Math.hypot(sx - R.cssW / 2, sy - R.cssH / 2) / (R.cssW / 2), centre: U.S.center ? U.S.center.name : null }; })()""")
        check(cen and cen['off'] < 0.1 and cen['centre'] == 'NGC 4889', 'arrivée : NGC 4889 au centre (écart %.3f de la demi-largeur), centre = %s' % ((cen or {}).get('off', 9), (cen or {}).get('centre')))
        pg.screenshot(path='/tmp/lot_s_ngc_%s_ngc4889.png' % MODE)
        lab0 = pg.evaluate("document.getElementById('card').innerText")
        pg.evaluate("__U.S.opts.lightcone = true")
        f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() > {f0} + 6', timeout=180000)
        d1 = pg.evaluate("(() => { const o = __U.S.sel, F = __U.F; return Math.hypot(...o.get().map((x, k) => (x - F.gcRel[k]))) / 3.0856775814913673e22 / F.cos.a; })()")
        lab1 = pg.evaluate("__U.select(__U.S.sel); document.getElementById('card').innerText")
        check(d1 < r['d'] * 0.995 and 'au moment de l’émission' in lab1 and 'à cet instant' in lab0, 'vue cône de lumière : %.1f → %.1f Mpc, libellé changé' % (r['d'], d1))
        pg.evaluate("__U.S.opts.lightcone = false")
        check(not logs, 'aucune erreur de page (%d)' % len(logs))

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
