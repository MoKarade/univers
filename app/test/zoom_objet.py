#!/usr/bin/env python3
"""Test à l'écran « zoom-objet » (mission 2, tâche R1).

Pour dix objets de types différents : on touche l'objet (même code que le toucher à l'écran : select puis centerOn),
puis on zoome de six puissances de dix dans chaque sens avec la vraie molette. À chaque image, l'objet doit rester
à moins de 10 % de la demi-largeur de l'écran du centre. Vers l'intérieur, le zoom s'arrête à la surface de l'objet
(clampZoom) : c'est la fin de la plage où il existe, et le test s'arrête là.

Les planètes (Lune, Jupiter) sont des astres « suivis » (focusBody) : on les touche, puis on zoome autour d'elles.

Lancer : python3 app/build.py puis python3 app/test/zoom_objet.py  (rendu logiciel, sans carte graphique).
Sortie : une ligne par objet et par sens, puis « zoom-objet : PASSE » ou « zoom-objet : ÉCHEC » (code de sortie 1).
"""
import os, sys, time, json
from playwright.sync_api import sync_playwright

URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'index.html')))
W, H = 1280, 800
DECADES, STEP = 6.0, 0.5      # six puissances de dix, par pas d'une demi-puissance
WHEEL = STEP / 0.0013          # molette : 0,0013 puissance de dix par unité de deltaY (60_app.js, écouteur « wheel »)
LIMIT = 0.10                   # 10 % de la demi-largeur

# (étiquette, recherche, type) ; type « body » = astre suivi, sinon objet sélectionnable
OBJETS = [
    ('Lune', 'Lune', 'body'),
    ('Jupiter', 'Jupiter', 'body'),
    ('Comète de Halley', '1P/Halley', 'obj'),
    ('Voyager 1', 'Voyager 1', 'obj'),
    ('Sirius', 'Sirius', 'obj'),
    ('Étoile Gaia sans nom', '#star2', 'obj'),
    ('Sagittarius A*', 'Sagittarius A*', 'obj'),
    ('Grand Nuage de Magellan', 'Grand Nuage de Magellan', 'obj'),
    ('Triangle', 'Galaxie du Triangle', 'obj'),
    ('Galaxie photographiée lointaine', '#near:NGC5194', 'obj')      # M51, 8,4 Mpc ; M101 n'est que dans les fichiers de photos, absents du dépôt,
]

# Projection à l'écran de la position d'un objet (même calcul que pickAt dans 60_app.js).
PROJ = """(() => { const U = window.__U, F = U.F, R = U.Rr, p = window.__P();
  if (!p || !isFinite(p[0])) return null;
  const PM = new THREE.Matrix4().multiplyMatrices(R.camera.projectionMatrix, R.camera.matrixWorldInverse), e = PM.elements;
  const X = (p[0] - F.tg[0]) * F.s, Y = (p[1] - F.tg[1]) * F.s, Z = (p[2] - F.tg[2]) * F.s, w = e[3] * X + e[7] * Y + e[11] * Z + e[15];
  if (w <= 0) return { behind: true, lr: U.S.logR };
  const sx = ((e[0] * X + e[4] * Y + e[8] * Z + e[12]) / w * 0.5 + 0.5) * R.cssW, sy = (0.5 - (e[1] * X + e[5] * Y + e[9] * Z + e[13]) / w * 0.5) * R.cssH;
  return { off: Math.hypot(sx - R.cssW / 2, sy - R.cssH / 2) / (R.cssW / 2), lr: U.S.logR, name: U.S.center ? U.S.center.name : U.S.focus }; })()"""


def wait_frames(pg, n=2):
    f0 = pg.evaluate('__U.frame()')
    pg.wait_for_function(f'__U.frame() >= {f0} + {n}', timeout=180000)


def settle(pg, extra_s=1.2):
    pg.wait_for_function('!__U.S.anim', timeout=180000)
    t = time.time()
    while time.time() - t < extra_s: wait_frames(pg, 1)


def touch(pg, label, query, kind):
    """Trouve l'objet, puis le « touche » depuis une vue qui n'est pas centrée sur lui."""
    if kind == 'body':
        key = pg.evaluate(f"(() => {{ __U.goName({json.dumps(query)}); return __U.S.focus; }})()")
        settle(pg)
        pg.evaluate(f"window.__P = () => __U.bodyPosM({json.dumps(key)})")
        return key
    if query == '#star2':      # une étoile du second catalogue (Gaia), sans nom
        ok = pg.evaluate("(() => { const st = __U.Rr.star2, sp = st.pos; let best = -1, bd = 1e9; for (let i = 0; i < st.N; i++) { const d = Math.hypot(sp[i * 3], sp[i * 3 + 1], sp[i * 3 + 2]); if (d > 300 && d < bd) { bd = d; best = i; } } if (best < 0) return null; const o = __U.selStar2(best); __U.goThere(o); window.__O = o; return o.name + ' n° ' + best + ', ' + Math.round(bd) + ' a.l.'; })()")      # la plus proche au-delà de 300 années-lumière
    elif query.startswith('#near:'):
        ok = pg.evaluate(f"(() => {{ const P = __U.Rr.pick; for (let i = 0; i < P.nN; i++) {{ const o = __U.selNear(i); if (o.name === {json.dumps(query[6:])}) {{ __U.goThere(o); window.__O = o; return o.name; }} }} return null; }})()")
    else:
        ok = pg.evaluate(f"(() => {{ const ok = __U.goName({json.dumps(query)}); window.__O = __U.S.sel; return ok && __U.S.sel ? __U.S.sel.name : null; }})()")
    if not ok: return None
    settle(pg)
    pg.evaluate("__U.select(null)")          # on quitte l'objet : le centre revient au Soleil
    settle(pg, 1.2)
    tap = "__U.select(window.__O);" + ("" if os.environ.get('U_TEMOIN') else " __U.centerOn(window.__O);")      # U_TEMOIN=1 : ancien toucher (fiche seule), le test doit échouer
    pg.evaluate(tap + " window.__P = () => window.__O.get()")      # le toucher
    settle(pg, 1.2)                          # le centre glisse vers l'objet en 0,9 s
    return ok


def zoom(pg, sens):
    """Zoome de six puissances de dix (sens +1 : reculer, -1 : avancer), mesure à chaque image."""
    worst, rows = 0.0, []
    l0 = pg.evaluate('__U.S.logR')
    for _ in range(int(DECADES / STEP)):
        before = pg.evaluate('__U.S.logR')
        pg.mouse.move(W * 0.3, H * 0.5)      # hors du centre : le nom de l'objet, au centre, intercepte la molette (voir R3)
        pg.mouse.wheel(0, sens * WHEEL)
        wait_frames(pg, 1)
        m = pg.evaluate(PROJ)
        if m is None or m.get('behind'):
            return False, 9.9, l0, before, 'objet derrière la caméra ou sans position'
        worst = max(worst, m['off'])
        if abs(m['lr'] - before) < 1e-3: break      # le zoom est borné (surface de l'objet ou limite du modèle)
    l1 = pg.evaluate('__U.S.logR')
    return worst <= LIMIT, worst, l0, l1, ''


def main():
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        ctx = b.new_context(viewport={'width': W, 'height': H}, device_scale_factor=1, color_scheme='dark', reduced_motion='reduce')
        pg = ctx.new_page()
        pg.add_init_script("window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];" + os.environ.get('U_INIT', ''))
        pg.goto(URL)
        pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
        pg.evaluate('__U.S.playing = false')
        for label, query, kind in OBJETS:
            pg.evaluate('__U.goHome()'); settle(pg, 0.5)
            name = touch(pg, label, query, kind)
            if not name:
                print(f'ÉCHEC  {label} : introuvable'); bad += 1; continue
            l_start = pg.evaluate('__U.S.logR')
            for sens in (+1, -1):
                pg.evaluate(f'__U.S.anim = null; __U.S.logR = {l_start}'); wait_frames(pg, 2)
                ok, worst, l0, l1, why = zoom(pg, sens)
                bad += 0 if ok else 1
                print(f"{'PASSE' if ok else 'ÉCHEC'}  {label:32s} ({name}) {'recul ' if sens > 0 else 'avance'} 10^{l0:.1f} → 10^{l1:.1f} m : écart max {worst * 100:.1f} % {why}")
        b.close()
    print('zoom-objet :', 'PASSE' if bad == 0 else f'ÉCHEC ({bad})')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
