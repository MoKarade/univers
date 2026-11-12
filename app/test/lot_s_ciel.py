#!/usr/bin/env python3
"""Test à l'écran « ciel DSS » (lot S, A4), avec un petit serveur local (les fichiers déposés à part ne se lisent pas en file://).

- par défaut, le fond reste le panorama ESO et rien du relevé DSS n'est téléchargé ;
- cocher « Ciel du relevé DSS » charge l'image 8192 × 4096 sur ordinateur (4096 × 2048 sur téléphone) et l'affiche ;
- décocher revient au panorama ESO ;
- captures : /tmp/lot_s_ciel_<mode>_eso.png et /tmp/lot_s_ciel_<mode>_dss.png (vue « Système solaire »).
Les images viennent de pipeline/sources/build_sky_dss.py (dossier %LOCALAPPDATA%/univers-raw).

Lancer : python3 app/build.py puis python -X utf8 app/test/lot_s_ciel.py [desk|phone]
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


def main():
    bad = 0

    def check(ok, msg):
        nonlocal bad
        print(('OK    ' if ok else 'ÉCHEC ') + msg)
        bad += 0 if ok else 1

    d = tempfile.mkdtemp()
    shutil.copy(os.path.join(ICI, '..', '..', 'dist', 'index.html'), d)
    for w in (8192, 4096):
        shutil.copy(os.path.join(RAW, 'sky_dss_%d.jpg' % w), d)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=d))
    srv.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = 'http://127.0.0.1:%d/index.html' % srv.server_address[1]
    phone = MODE != 'desk'
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        ctx = b.new_context(viewport={'width': 390, 'height': 780} if phone else {'width': 1280, 'height': 800},
                            device_scale_factor=2 if phone else 1, has_touch=phone, is_mobile=phone, color_scheme='dark', reduced_motion='reduce')
        pg = ctx.new_page()
        demandes = []
        pg.on('request', lambda r: demandes.append(r.url) if 'sky_dss' in r.url else None)
        pg.add_init_script("window.__TIER=%d; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[]; window.__SKY_DSS={8192:'sky_dss_8192.jpg',4096:'sky_dss_4096.jpg'};" % (0 if phone else 1))
        pg.goto(url)
        pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
        pg.evaluate("__U.S.playing = false; __U.goStop(__U.STOPS.find(s => /Système solaire/.test(s.name)), true)")
        f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() > {f0} + 6', timeout=180000)
        check(pg.evaluate('__U.Rr.skySrc') == 'eso' and not demandes, 'au départ : panorama ESO, aucun téléchargement DSS (%s)' % demandes)
        pg.screenshot(path='/tmp/lot_s_ciel_%s_eso.png' % MODE)
        pg.evaluate("const c = document.getElementById('c-dss'); c.checked = true; c.dispatchEvent(new Event('change'))")
        pg.wait_for_function("__U.Rr.skySrc !== 'eso'", timeout=120000)
        attendu = 'dss4096' if phone else 'dss8192'
        src = pg.evaluate('__U.Rr.skySrc')
        check(src == attendu, 'après la case : %s (attendu %s)' % (src, attendu))
        msg = pg.evaluate("document.getElementById('dss-msg').textContent")
        check('DSS2' in msg, 'message : %s' % msg)
        f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() > {f0} + 6', timeout=180000)
        pg.screenshot(path='/tmp/lot_s_ciel_%s_dss.png' % MODE)
        pg.evaluate("const c = document.getElementById('c-dss'); c.checked = false; c.dispatchEvent(new Event('change'))")
        check(pg.evaluate('__U.Rr.skySrc') == 'eso', 'case décochée : retour au panorama ESO')
        b.close()
    srv.shutdown()
    print('RÉSULTAT (%s) :' % MODE, 'PASSE' if bad == 0 else '%d échec(s)' % bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
