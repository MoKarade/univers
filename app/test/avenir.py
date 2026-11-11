#!/usr/bin/env python3
"""Test à l'écran « avenir » (mission 2, tâche R7).

- À +9 et +20 milliards d'années : les planètes restantes (Mars à Neptune) sont sur des orbites 1,85 fois plus larges
  qu'aujourd'hui, à 1 % près (1 / 0,5405, masse finale du Soleil, Schröder et Smith 2008).
- À +50 et +100 milliards d'années : le panneau « Inconnu » est affiché et aucune planète n'est dessinée.
- Plus aucun fondu daté : FATE_P n'existe plus (vérifié aussi par grep dans le contrôle).
Lancer : python3 app/build.py puis python3 app/test/avenir.py   (PYTHONIOENCODING=utf-8 sous Windows)
"""
import os, sys
from playwright.sync_api import sync_playwright

URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'index.html')))
PL = ['mars', 'jupiter', 'saturn', 'uranus', 'neptune']
STATE = """(() => { const U = __U, F = U.F, out = {};
  for (const k of %s) { const p = U.bodyPosM(k), q = F.sol.planets[k].pos, r = Math.hypot(...p) / (Math.hypot(...q) * 1.495978707e11), b = U.Rr.bodies[k];
    out[k] = { ratio: r, drawn: !!(b.grp.visible && b.vis > 0.01) }; }
  return { pl: out, notice: document.getElementById('notice').hidden ? '' : document.getElementById('notice').textContent }; })()""" % PL


def frames(pg, n=3):
    f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() >= {f0} + {n}', timeout=180000)


def main():
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = b.new_context(viewport={'width': 1280, 'height': 800}, color_scheme='dark', reduced_motion='reduce').new_page()
        pg.add_init_script("window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
        pg.goto(URL); pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
        pg.evaluate("__U.S.playing = false; __U.goStop(__U.STOPS[1], true)"); frames(pg)
        for ty in (9e9, 2e10, 5e10, 1e11):
            pg.evaluate(f"__U.S.ty = {ty}; __U.S.lastTy = {ty}"); frames(pg, 4)
            st = pg.evaluate(STATE)
            if ty < 3e10:
                worst = max(abs(v['ratio'] / 1.85 - 1) for v in st['pl'].values())
                ok = worst <= 0.01 and all(v['drawn'] for v in st['pl'].values())
                print(f"{'PASSE' if ok else 'ÉCHEC'}  +{ty / 1e9:.0f} Ga : orbites à {worst * 100:.2f} % de 1,85 fois l'actuel au pire ; planètes dessinées : {all(v['drawn'] for v in st['pl'].values())}")
            else:
                drawn = [k for k, v in st['pl'].items() if v['drawn']]
                ok = st['notice'].startswith('Inconnu') and not drawn
                print(f"{'PASSE' if ok else 'ÉCHEC'}  +{ty / 1e9:.0f} Ga : panneau « {st['notice'][:60]}… » ; planètes dessinées : {drawn or 'aucune'}")
            bad += 0 if ok else 1
        b.close()
    print('avenir :', 'PASSE' if bad == 0 else f'ÉCHEC ({bad})')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
