#!/usr/bin/env python3
"""Test à l'écran « terre-inconnue » (mission 2, tâche R6).

Juste avant le moment où les études divergent (T_DIV : l'orbite calculée de la Terre cesse de s'élargir), la Terre
est dessinée sur son orbite élargie et aucun panneau « sort inconnu » n'est affiché. Juste après : la Terre et la
Lune ne sont plus dessinées (coupure nette, pas de fondu), le panneau cite les trois études, et le repère de la Terre
suivie dit « sort inconnu ».
Lancer : python3 app/build.py puis python3 app/test/terre_inconnue.py   (PYTHONIOENCODING=utf-8 sous Windows)
"""
import os, sys
from playwright.sync_api import sync_playwright

URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'index.html')))
STATE = """(() => { const U = __U, b = U.Rr.bodies, n = document.getElementById('notice'), fe = document.getElementById('follow');
  return { earth: !!(b.earth.grp.visible && b.earth.vis > 0.01), moon: !!(b.moon.grp.visible && b.moon.vis > 0.01),
    ratio: Math.hypot(...U.bodyPosM('earth')) / (Math.hypot(...U.F.sol.earth) * 1.495978707e11), orb: U.F.orb,
    notice: n.hidden ? '' : n.textContent, mark: fe.hidden ? '' : fe.querySelector('small').textContent }; })()"""
REFS = ('Schröder et Smith 2008', 'Rasio et al. 1996', 'Rybicki et Denis 2001')


def frames(pg, n=4):
    f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() >= {f0} + {n}', timeout=180000)


def main():
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = b.new_context(viewport={'width': 1280, 'height': 800}, color_scheme='dark', reduced_motion='reduce').new_page()
        pg.add_init_script("window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
        pg.goto(URL); pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
        tdiv = pg.evaluate('__U.T_DIV')
        print(f'T_DIV = {tdiv:.6f} milliards d\'années')
        pg.evaluate("__U.S.playing = false; __U.goStop(__U.STOPS[1], true)"); frames(pg)
        for dt, label in ((-1e-4, 'avant'), (1e-4, 'après')):
            ty = (tdiv + dt) * 1e9
            pg.evaluate(f"__U.S.ty = {ty}; __U.S.lastTy = {ty}"); frames(pg)
            st = pg.evaluate(STATE)
            if dt < 0:
                ok = st['earth'] and not st['notice'].startswith('Sort de la Terre') and st['ratio'] > 1.0
                print(f"{'PASSE' if ok else 'ÉCHEC'}  {label} : Terre dessinée {st['earth']}, à {st['ratio']:.3f} fois son orbite actuelle (élargie), pas de panneau")
            else:
                ok = not st['earth'] and not st['moon'] and all(r in st['notice'] for r in REFS)
                pg.evaluate("__U.S.anim = null; __U.S.logR = 14.0"); frames(pg)
                far = pg.evaluate(STATE)['notice']
                ok = ok and not far.startswith('Sort de la Terre')
                print(f"       au-dessus de 10^13,5 m : panneau « {far[:40]} » (attendu : pas le panneau de la Terre)")
                pg.evaluate("__U.goStop(__U.STOPS[1], true)"); frames(pg)
                print(f"{'PASSE' if ok else 'ÉCHEC'}  {label} : Terre dessinée {st['earth']}, Lune {st['moon']} ; panneau : « {st['notice'][:90]}… »")
            bad += 0 if ok else 1
        pg.evaluate("__U.focusBody('earth')"); pg.wait_for_function('!__U.S.anim', timeout=180000); frames(pg)
        st = pg.evaluate(STATE)
        ok = st['mark'] == 'sort inconnu'
        bad += 0 if ok else 1
        print(f"{'PASSE' if ok else 'ÉCHEC'}  repère de la Terre suivie : « {st['mark']} »")
        b.close()
    print('terre-inconnue :', 'PASSE' if bad == 0 else f'ÉCHEC ({bad})')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
