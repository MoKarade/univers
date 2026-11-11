# S6 : essai à l’écran (Playwright, rendu logiciel) : rayon de l’ombre près de Sagittarius A*, raccord à 3000 M, coupure sous 3,1 M.
# Lancer : U_URL=file:///…/dist/index.html python app/test/lens_screen.py
import time, os, math
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops, ImageStat
def shadow(fn, H):
    im = Image.open(fn).convert('L'); W = im.size[0]; cx, cy = W // 2, H // 2; rs = []
    for a in range(0, 360, 10):
        for r in range(30, 300):
            x = int(cx + r * math.cos(math.radians(a))); y = int(cy + r * math.sin(math.radians(a)))
            if im.getpixel((x, y)) > 25: rs.append(r); break
    rs.sort(); return rs[len(rs) // 2]
with sync_playwright() as p:
    b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']); pg = b.new_page(viewport={'width': 1000, 'height': 700})
    logs = []; pg.on('pageerror', lambda e: logs.append(str(e)))
    pg.goto(os.environ['U_URL']); pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=120000)
    pg.evaluate('__U.S.playing=false; __U.goName("Sagittarius A*")'); time.sleep(8); pg.evaluate('__U.S.anim=null; __U.S.logR=12.3'); time.sleep(2)
    for r in [60, 200, 2900, 3100, 1e6, 2]:
        pg.evaluate(f'__U.Rr.lensForceR = {r}'); time.sleep(2.5); fn = f'l_{int(r)}.png'; pg.screenshot(path=fn)
        pc = math.asin(math.sqrt(27) * math.sqrt(1 - 2 / r) / r) if r > 3 else 0
        print(r, pg.evaluate('JSON.stringify({on:__U.Rr.lens.on, inside:__U.Rr.lens.inside})'), 'ombre px mesurée', shadow(fn, 700) if r < 300 else '-', 'calculée', round(math.tan(pc) / math.tan(math.radians(20)) * 350, 1), '| prov :', pg.evaluate("document.getElementById('prov').textContent")[-70:])
    d = ImageStat.Stat(ImageChops.difference(Image.open('l_2900.png').convert('L'), Image.open('l_3100.png').convert('L'))).mean[0]
    print('écart moyen 2900 / 3100 M :', round(d, 2))
    print('erreurs :', logs[:5]); b.close()
