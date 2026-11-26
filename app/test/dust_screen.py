# S5 : essai à l'écran (Playwright, rendu logiciel) : vu de 790 années-lumière du Soleil, les étoiles que la carte place derrière
# un nuage (ΔA > 2 mag selon dustPair) doivent être plus faibles avec la poussière que sans, sans erreur WebGL.
# Lancer : python3 app/test/dust_screen.py (ou U_URL=file:///…/dist/index.html python3 app/test/dust_screen.py)
import io
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
from PIL import Image

URL = os.environ.get('U_URL') or Path(__file__).resolve().parents[2].joinpath('dist', 'index.html').as_uri()
LAUNCH_ARGS = ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']


def wait_frames(pg, n=3):
    f0 = pg.evaluate('__U.frame()')
    pg.wait_for_function(f'__U.frame() >= {f0} + {n}', timeout=120000)


JS_SEL = '''(() => { const u = __U.Rr, cl = u.dustU.uCamLy.value, cg = eclLyToGalPc([cl.x, cl.y, cl.z]), sp = u.starPos, N = u.star.N, sc = [0,0,0], out = [];
  for (let i = 0; i < N; i++) { const s = eclLyToGalPc([sp[i*3], sp[i*3+1], sp[i*3+2]]), p = dustPair(cg, s), d = p[0] - p[1]; if (d > 2 && u.project([sp[i*3]*9.4607e15, sp[i*3+1]*9.4607e15, sp[i*3+2]*9.4607e15], __U.F, sc) && sc[0] > 420 && sc[0] < 980 && sc[1] > 60 && sc[1] < 520) out.push([i, d]); }
  return out.sort((a, b) => b[1] - a[1]).slice(0, 10); })()'''
JS_POS = '''(ids => { const u = __U.Rr, sp = u.starPos, sc = [0,0,0]; return ids.map(i => u.project([sp[i*3]*9.4607e15, sp[i*3+1]*9.4607e15, sp[i*3+2]*9.4607e15], __U.F, sc) ? [Math.round(sc[0]), Math.round(sc[1])] : null); })'''

with sync_playwright() as p:
    b = p.chromium.launch(args=LAUNCH_ARGS)
    pg = b.new_page(viewport={'width': 1000, 'height': 700})
    gl = []
    pg.on('console', lambda m: gl.append(m.text) if 'GL_INVALID' in m.text or 'ERROR' in m.text else None)
    pg.add_init_script(
        'window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];'
        + os.environ.get('U_INIT', '')
    )
    pg.goto(URL)
    pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=120000)
    pg.evaluate('__U.S.playing=false; __U.goName("Bételgeuse")')
    pg.wait_for_function('!__U.S.anim', timeout=120000)
    pg.evaluate('__U.S.anim=null; __U.S.logR=18.6')
    wait_frames(pg, 3)

    sel = pg.evaluate(JS_SEL)
    ids = [i for i, _ in sel]
    res = {}
    for f in [0, 1, 0, 1]:
        pg.evaluate(f'__U.Rr.dustForce = {f}')
        wait_frames(pg, 3)
        pos = pg.evaluate(JS_POS, ids)
        im = Image.open(io.BytesIO(pg.screenshot(timeout=120000))).convert('L')
        res.setdefault(f, []).append([
            max(
                im.getpixel((min(max(x + dx, 0), 999), min(max(y + dy, 0), 699)))
                for dx in range(-2, 3)
                for dy in range(-2, 3)
            )
            if q
            else None
            for q in pos
            for x, y in [q or (0, 0)]
        ])
    for k, (i, d) in enumerate(sel):
        print(f'étoile {i} : ΔA = +{d:.2f} mag ; sans poussière {[r[k] for r in res[0]]} ; avec {[r[k] for r in res[1]]}')
    ok = sum(
        1
        for k in range(len(sel))
        if None not in [r[k] for r in res[0] + res[1]]
        and max(r[k] for r in res[1]) < min(r[k] for r in res[0])
    )
    print(f'{ok} / {len(sel)} étoiles nettement assombries')
    b.close()
    sys.exit(0 if len(sel) >= 5 and ok >= len(sel) * 0.8 and not gl else 1)
