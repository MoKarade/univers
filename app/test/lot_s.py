#!/usr/bin/env python3
"""Test à l'écran « ondes » et « fond diffus » (lot S, tâches S1 et S2).

Ondes : la page contient autant de détections que le fichier GWOSC (moins GW150914 et GW170817, déjà présents) ;
la catégorie est masquée par défaut ; l'allumer ajoute exactement ces lignes à la chronologie ; deux fiches de contrôle
portent la date et les valeurs publiées.
Fond diffus : la carte vient de Planck ; capture de la vue la plus lointaine dans /tmp/lot_s_cmb.png.

Lancer : python3 app/build.py puis python3 app/test/lot_s.py   (PYTHONIOENCODING=utf-8 sous Windows)
"""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'index.html')))
DEJA = 2   # GW150914 et GW170817 ont leur propre événement


def check(ok, msg, bad):
    print(('OK   ' if ok else 'ÉCHEC ') + msg)
    return bad + (0 if ok else 1)


def main():
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = b.new_context(viewport={'width': 1280, 'height': 800}, color_scheme='dark', reduced_motion='reduce').new_page()
        logs = []
        pg.on('pageerror', lambda e: logs.append(str(e)))
        pg.add_init_script("window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
        pg.goto(URL)
        pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)

        n_fichier = pg.evaluate('DATA.GW.length')
        n_page = pg.evaluate("__U.EVL.filter(e => e.cat === 'O').length")
        bad = check(n_page == n_fichier - DEJA, 'détections dans la page : %d (fichier : %d, moins %d déjà présentes)' % (n_page, n_fichier, DEJA), bad)

        avant = pg.evaluate("document.querySelectorAll('#events button.ev').length")
        btn = pg.evaluate("[...document.querySelectorAll('#ev-cats button')].findIndex(b => /Ondes/.test(b.textContent))")
        bad = check(btn >= 0, 'bouton « Ondes gravitationnelles » présent', bad)
        presse = pg.evaluate(f"document.querySelectorAll('#ev-cats button')[{btn}].getAttribute('aria-pressed')")
        bad = check(presse == 'false', 'catégorie masquée par défaut (aria-pressed=%s)' % presse, bad)
        pg.evaluate(f"document.querySelectorAll('#ev-cats button')[{btn}].click()")
        apres = pg.evaluate("document.querySelectorAll('#events button.ev').length")
        bad = check(apres - avant == n_page, 'lignes ajoutées en allumant : %d' % (apres - avant), bad)

        for nom, attendu in (('GW190521', ['2019', 'masses solaires', 'GWTC']), ('GW200115_042309', ['2020', 'masses solaires'])):
            txt = pg.evaluate(f"""(() => {{ const e = __U.EVL.find(q => q.n.endsWith('{nom}')); if (!e) return null;
                __U.evGo(e); return document.getElementById('card').innerText; }})()""")
            ok = bool(txt) and all(a in txt for a in attendu)
            bad = check(ok, 'fiche %s : %s' % (nom, (txt or 'absente').replace('\n', ' / ')[:220]), bad)

        src = pg.evaluate('DATA.CMB_SRC || ""')
        bad = check('Planck' in src, 'source du fond diffus : %s' % src, bad)
        pg.evaluate("__U.select(null); __U.S.playing = false; __U.goStop(__U.STOPS.find(s => /observable/.test(s.name)), true)")
        pg.wait_for_function("document.getElementById('prov').textContent.indexOf('Quasars') >= 0", timeout=180000)
        f0 = pg.evaluate('__U.frame()')
        pg.wait_for_function(f'__U.frame() > {f0} + 6', timeout=180000)
        pg.screenshot(path='/tmp/lot_s_cmb.png')
        notice = pg.evaluate("document.getElementById('prov').textContent")
        bad = check('Planck' in notice, 'bandeau de la vue lointaine : %s' % notice, bad)
        bad = check(not logs, 'aucune erreur de page (%d)' % len(logs), bad)
        for l in logs[:5]:
            print('   ', l)
        b.close()
    print('RÉSULTAT :', 'PASSE' if bad == 0 else '%d échec(s)' % bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
