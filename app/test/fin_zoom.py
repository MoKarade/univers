#!/usr/bin/env python3
"""Test à l'écran « fin-du-zoom » (mission 2, tâche R13).

On plonge vers la Terre jusqu'au dernier arrêt de la barre (« Limite du connu »), puis on continue à la molette :
l'échelle s'arrête à 10⁻²⁰ m, l'écran dit « Inconnu » avec la phrase sur la longueur de Planck, et aucun arrêt de la
barre n'est plus fin que 10⁻²⁰ m. Plus de bouillonnement : aucun objet « vue d'artiste » n'est dessiné.
Lancer : python3 app/build.py puis python3 app/test/fin_zoom.py   (PYTHONIOENCODING=utf-8 sous Windows)
"""
import os, sys
from playwright.sync_api import sync_playwright

URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'index.html')))


def frames(pg, n=4):
    f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() >= {f0} + {n}', timeout=180000)


def main():
    bad = 0
    def check(ok, msg):
        nonlocal bad
        print(('PASSE  ' if ok else 'ÉCHEC  ') + msg); bad += 0 if ok else 1
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = b.new_context(viewport={'width': 1280, 'height': 800}, color_scheme='dark', reduced_motion='reduce').new_page()
        pg.add_init_script("window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
        pg.goto(URL); pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
        stops = pg.evaluate("__U.STOPS.filter(s => s.micro).map(s => [s.name, s.logR])")
        check(min(s[1] for s in stops) >= -20.0001, f"arrêts de la barre dans l'infiniment petit : {', '.join(n for n, _ in stops)} (le plus fin : 10^{min(s[1] for s in stops):.1f} m)")
        pg.evaluate("__U.S.playing = false; __U.goStop(__U.STOPS.find(s => s.name === 'Limite du connu') || __U.STOPS.filter(s => s.micro).pop(), true)"); frames(pg, 6)
        pg.mouse.move(900, 300)
        for _ in range(10): pg.mouse.wheel(0, -2000); frames(pg, 1)
        lr = pg.evaluate('__U.S.logR')
        check(abs(lr + 20.0) < 0.01, f"après dix crans de plus, l'échelle reste à 10^{lr:.3f} m (borne : 10^-20 m)")
        txt = pg.evaluate("[document.getElementById('place').textContent, document.getElementById('notice').hidden ? '' : document.getElementById('notice').textContent].join(' | ')")
        check('Inconnu' in txt and 'quinze puissances de dix' in txt and '1,616' in txt, f"écran : « {txt[:160]}… »")
        n_art = pg.evaluate("__U.Rr.scene.children.filter(o => o.visible && o.material && o.material.fragmentShader && /43758/.test(o.material.fragmentShader) && o.geometry && o.geometry.type === 'PlaneGeometry').length")
        check(n_art == 0, f"aucun plan « bouillonnement » dessiné ({n_art})")
        b.close()
    print('fin-du-zoom :', 'PASSE' if bad == 0 else f'ÉCHEC ({bad})')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
