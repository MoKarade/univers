#!/usr/bin/env python3
"""Test à l'écran « suivi-temps » (mission 2, tâche R2).

1. Mars suivi pendant 1 000 ans simulés, temps lancé à 100 ans par seconde (1 000 ans en dix secondes sur un écran
   fluide ; en rendu logiciel les images sont plus lentes, le test attend donc d'avoir parcouru les 1 000 ans).
   À chaque image : Mars à moins de 10 % de la demi-largeur du centre, et le repère affiché sur lui à 3 px près.
2. États dits par le repère : Mars avant la formation du système solaire → « pas encore formée » ;
   Mercure à +8 milliards d'années (après la date d'engloutissement calculée par la page) → « engloutie… » ;
   Terre au-delà de cette date → « sort inconnu » (décision 3 de Marc) ; Mars aujourd'hui → aucun état.

Lancer : python3 app/build.py puis python3 app/test/suivi_temps.py   (PYTHONIOENCODING=utf-8 sous Windows)
"""
import os, sys
from playwright.sync_api import sync_playwright

URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'index.html')))
W, H, LIMIT = 1280, 800, 0.10
MEASURE = r"""(() => { const U = __U, F = U.F, R = U.Rr, p = U.bodyPosM(U.S.focus), sc = [0, 0, 0];
  if (!R.project(p, F, sc)) return { off: 9, mark: 999, ty: U.S.ty };
  const fe = document.getElementById('follow'), mt = /translate\(([-\d.]+)px,\s*([-\d.]+)px/.exec(fe.style.transform || '');
  return { off: Math.hypot(sc[0] - R.cssW / 2, sc[1] - R.cssH / 2) / (R.cssW / 2), mark: !fe.hidden && mt ? Math.hypot(+mt[1] - sc[0], +mt[2] - sc[1]) : 999,
    st: fe.querySelector('small').hidden ? '' : fe.querySelector('small').textContent, name: fe.querySelector('b').textContent, ty: U.S.ty, frame: U.frame() }; })()"""


def frames(pg, n=1):
    f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() >= {f0} + {n}', timeout=180000)


def main():
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = b.new_context(viewport={'width': W, 'height': H}, color_scheme='dark', reduced_motion='reduce').new_page()
        pg.add_init_script("window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
        pg.goto(URL); pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
        pg.evaluate("__U.S.playing = false; __U.focusBody('mars')"); pg.wait_for_function('!__U.S.anim', timeout=180000); frames(pg, 3)
        # 1. 1 000 ans à 100 ans par seconde
        pg.evaluate("__U.S.ty = 0; __U.setSpeed(100 * 365.25 * 86400); __U.S.dir = 1; __U.S.playing = true")
        worst, wmark, n, seen = 0.0, 0.0, 0, set()
        while True:
            frames(pg)
            m = pg.evaluate(MEASURE); n += 1
            if m['frame'] in seen: continue
            seen.add(m['frame']); worst = max(worst, m['off']); wmark = max(wmark, m['mark'])
            if m['ty'] >= 1000: break
        pg.evaluate("__U.S.playing = false")
        ok = worst <= LIMIT and wmark <= 3
        bad += 0 if ok else 1
        print(f"{'PASSE' if ok else 'ÉCHEC'}  Mars suivi 0 → {m['ty']:.0f} ans, {len(seen)} images : écart max {worst * 100:.1f} % (limite 10 %), repère à {wmark:.1f} px au pire")
        # 2. états
        cases = [('mars', -4.6e9, 'pas encore formée'), ('mars', 0, ''), ('mercury', 8e9, 'engloutie par le Soleil (calculé)'), ('earth', 9e9, 'sort inconnu')]
        for key, ty, want in cases:
            pg.evaluate(f"__U.S.ty = {ty}; __U.focusBody('{key}')"); pg.wait_for_function('!__U.S.anim', timeout=180000); frames(pg, 3)
            m = pg.evaluate(MEASURE)
            ok = m['st'] == want and m['mark'] <= 3
            bad += 0 if ok else 1
            print(f"{'PASSE' if ok else 'ÉCHEC'}  {m['name']} à {ty / 1e9:+.1f} milliard(s) d'années : état « {m['st']} » (attendu « {want} »), repère à {m['mark']:.1f} px")
        b.close()
    print('suivi-temps :', 'PASSE' if bad == 0 else f'ÉCHEC ({bad})')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
