# S6 : essai à l’écran (Playwright, rendu logiciel) : rayon de l’ombre près de Sagittarius A*, raccord à 3000 M, coupure sous 3,1 M.
# Lancer : python3 app/test/lens_screen.py (ou U_URL=file:///…/dist/index.html python3 app/test/lens_screen.py)
import io
import math
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops, ImageStat

URL = os.environ.get('U_URL') or Path(__file__).resolve().parents[2].joinpath('dist', 'index.html').as_uri()
LAUNCH_ARGS = ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']


def wait_frames(pg, n=1):
    f0 = pg.evaluate('__U.frame()')
    pg.wait_for_function(f'__U.frame() >= {f0} + {n}', timeout=120000)


def shadow(im, H):
    W = im.size[0]
    cx, cy = W // 2, H // 2
    rs = []
    for a in range(0, 360, 10):
        for r in range(30, 300):
            x = int(cx + r * math.cos(math.radians(a)))
            y = int(cy + r * math.sin(math.radians(a)))
            if im.getpixel((x, y)) > 25:
                rs.append(r)
                break
    if not rs:
        return None
    rs.sort()
    return rs[len(rs) // 2]


fails = []
imgs = {}
with sync_playwright() as p:
    b = p.chromium.launch(args=LAUNCH_ARGS)
    pg = b.new_page(viewport={'width': 1000, 'height': 700})
    pg.emulate_media(reduced_motion='reduce')
    logs = []
    pg.on('pageerror', lambda e: logs.append(str(e)))
    pg.add_init_script(
        'window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];'
        + os.environ.get('U_INIT', '')
    )
    pg.goto(URL)
    pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=120000)
    pg.evaluate('__U.S.playing=false; __U.goName("Sagittarius A*")')
    pg.wait_for_function('!__U.S.anim', timeout=120000)
    pg.evaluate('__U.S.anim=null; __U.S.logR=12.3')
    pg.wait_for_function('__U.Rr.lens.on && !__U.Rr.lens.dirty', timeout=180000)

    for r in [60, 200, 2900, 3100, 1e6, 2]:
        pg.evaluate(f'__U.Rr.lensForceR = {r}')
        wait_frames(pg, 1)
        if pg.evaluate('__U.Rr.lens.on && !__U.Rr.lens.inside && __U.Rr.lens.r < 3000 && __U.Rr.lens.dirty'):
            pg.wait_for_function('!__U.Rr.lens.dirty', timeout=120000)
            wait_frames(pg, 1)
        im = Image.open(io.BytesIO(pg.screenshot(timeout=120000))).convert('L')
        imgs[int(r)] = im
        pc = math.asin(math.sqrt(27) * math.sqrt(1 - 2 / r) / r) if r > 3 else 0
        st = pg.evaluate('({on:__U.Rr.lens.on, inside:__U.Rr.lens.inside})')
        calc = math.tan(pc) / math.tan(math.radians(20)) * 350
        meas = shadow(im, 700) if 45 < calc < 300 else None
        notice = pg.evaluate("document.getElementById('notice').textContent")
        print(r, st, 'ombre px mesurée', meas, 'calculée', round(calc, 1), '| note :', notice[:60], flush=True)
        if 45 < calc < 300 and (meas is None or abs(meas / calc - 1) > 0.06):
            fails.append(f'ombre à {r} M : {meas} px pour {calc:.1f}')
        if r == 2 and not (st['inside'] and 'Inconnu' in notice):
            fails.append('sous 3,1 M : pas de message « Inconnu »')

    df = ImageChops.difference(imgs[2900], imgs[3100]).crop((350, 200, 650, 500))
    d, mx = ImageStat.Stat(df).mean[0], df.getextrema()[1]
    print('autour du trou noir, 2900 / 3100 M : écart moyen', round(d, 2), 'maximal', mx, flush=True)
    if d > 2:
        fails.append(f'saut au passage de 3000 M : écart moyen {d:.2f}')
    print('erreurs :', logs[:5], flush=True)
    b.close()
    if logs:
        fails.append('erreurs de page')

print('ÉCHECS :' if fails else 'tout est vert', fails, flush=True)
sys.exit(1 if fails else 0)
