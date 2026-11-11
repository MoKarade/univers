#!/usr/bin/env python3
"""Test à l'écran « zoom-point » (mission 2, tâche R3).

Sans objet touché, la molette vise le point sous le curseur. On se place dans la vue « Étoiles proches », on choisit
l'étoile nommée la plus proche de 30 % de la largeur depuis le bord gauche, on pose le curseur dessus, puis on zoome
de deux puissances de dix vers l'avant, puis vers l'arrière, avec la vraie molette (crans d'un dixième de puissance).
Après chaque cran, l'étoile doit rester sous le curseur à 3 px près. Ensuite « Accueil » doit annuler le décalage.

Témoin : U_URL=<page construite depuis main avant R3> doit échouer (l'étoile glisse hors du curseur).
Lancer : python3 app/build.py puis python3 app/test/zoom_point.py   (PYTHONIOENCODING=utf-8 sous Windows)
"""
import os, sys, time
from playwright.sync_api import sync_playwright

URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'index.html')))
W, H = 1280, 800
STEP, N = 0.1, 20                  # 20 crans d'un dixième : deux puissances de dix
WHEEL = STEP / 0.0013              # 0,0013 puissance de dix par unité de deltaY (écouteur « wheel »)
LIMIT_PX = 3.0

PICK = """(() => { const U = __U, R = U.Rr, sc = [0, 0, 0]; let best = null;
  for (const L of U.Rr.keyStars) { const o = U.selStar(L), p = o.get(); if (!R.project(p, U.F, sc)) continue;
    if (sc[0] < 60 || sc[0] > R.cssW - 260 || sc[1] < 200 || sc[1] > R.cssH - 220) continue;
    const d = Math.hypot(sc[0] - 0.3 * R.cssW, sc[1] - 0.5 * R.cssH); if (!best || d < best.d) best = { d, i: L, name: o.name, x: sc[0], y: sc[1] }; }
  if (best) window.__S = U.selStar(best.i); return best; })()"""
WHERE = """(() => { const U = __U, sc = [0, 0, 0]; const ok = U.Rr.project(window.__S.get(), U.F, sc); return ok ? { x: sc[0], y: sc[1], lr: U.S.logR } : null; })()"""


def frames(pg, n=1):
    f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() >= {f0} + {n}', timeout=180000)


def main():
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = b.new_context(viewport={'width': W, 'height': H}, color_scheme='dark', reduced_motion='reduce').new_page()
        pg.add_init_script("window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
        pg.goto(URL); pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
        pg.evaluate("__U.S.playing = false; __U.goStop(__U.STOPS.find(s => /proches/i.test(s.name)), true)")
        pg.wait_for_function('!__U.S.anim', timeout=180000); frames(pg, 4)
        st = pg.evaluate(PICK)
        if not st:
            print('ÉCHEC  aucune étoile nommée visible'); sys.exit(1)
        print(f"étoile : {st['name']} à x = {st['x']:.0f} px ({st['x'] / W * 100:.0f} % de la largeur), y = {st['y']:.0f} px ; échelle 10^{pg.evaluate('__U.S.logR'):.2f} m")
        cx, cy = st['x'], st['y']
        pg.mouse.move(cx, cy)
        for sens, mot in ((-1, 'avance'), (+1, 'recul ')):
            worst, l0 = 0.0, pg.evaluate('__U.S.logR')
            for _ in range(N):
                pg.mouse.wheel(0, sens * WHEEL); frames(pg, 1)
                m = pg.evaluate(WHERE)
                if not m: worst = 999; break
                worst = max(worst, abs(m['x'] - cx), abs(m['y'] - cy))
            l1 = pg.evaluate('__U.S.logR')
            ok = worst <= LIMIT_PX and abs(abs(l1 - l0) - N * STEP) < 0.02
            bad += 0 if ok else 1
            print(f"{'PASSE' if ok else 'ÉCHEC'}  {mot} 10^{l0:.2f} → 10^{l1:.2f} m : l'étoile s'écarte du curseur de {worst:.1f} px au pire (limite {LIMIT_PX:.0f})")
        if pg.evaluate("typeof __U.zoffReset === 'function'"):
            pg.mouse.wheel(0, -5 * WHEEL); frames(pg, 2)
            had = pg.evaluate('!!__U.S.zoff')
            pg.evaluate('__U.goHome()'); frames(pg, 2)
            ok = had and pg.evaluate('!__U.S.zoff')
            bad += 0 if ok else 1
            print(f"{'PASSE' if ok else 'ÉCHEC'}  « Accueil » annule le décalage (décalage avant : {'oui' if had else 'non'})")
        if pg.evaluate("typeof __U.zoffReset === 'function'"):      # suivre la Terre, reculer vers un point au-delà de 10^14,4 m, revenir : la Terre est au centre
            pg.evaluate("__U.focusBody('earth')"); pg.wait_for_function('!__U.S.anim', timeout=180000); frames(pg, 3)
            pg.evaluate("__U.S.anim = null; __U.S.logR = 15.0"); frames(pg, 2)
            pg.mouse.move(W * 0.62, H * 0.35)      # hors de la fiche (à gauche) et des noms
            for _ in range(5): pg.mouse.wheel(0, 2 * WHEEL); frames(pg, 1)
            had = pg.evaluate('!!__U.S.zoff')
            pg.evaluate("__U.goTo(9, { noHist: true, instant: true })"); frames(pg, 2); pg.wait_for_timeout(1500); frames(pg, 2)
            m = pg.evaluate("""(() => { const U = __U, sc = [0, 0, 0]; return U.Rr.project(U.bodyPosM('earth'), U.F, sc) ? Math.hypot(sc[0] - U.Rr.cssW / 2, sc[1] - U.Rr.cssH / 2) : 9999; })()""")
            ok = had and m < 3
            bad += 0 if ok else 1
            print(f"{'PASSE' if ok else 'ÉCHEC'}  Terre suivie, recul vers un point puis retour à 10^9 m : Terre à {m:.1f} px du centre (décalage créé : {'oui' if had else 'non'})")
        b.close()
    print('zoom-point :', 'PASSE' if bad == 0 else f'ÉCHEC ({bad})')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
