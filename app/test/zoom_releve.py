#!/usr/bin/env python3
"""Relevé R12 : temps par image et écart entre images successives, de 10^26,75 m à 10^-20 m (tableau de docs/r12-zoom.md).
Usage : python3 app/test/zoom_releve.py [sortie.json]   (PYTHONIOENCODING=utf-8 sous Windows)"""
import os, sys, json, time, io
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops, ImageStat
URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'index.html')))
out = []
def frames(pg, n):
    f0 = pg.evaluate('__U.frame()'); t = time.time(); pg.wait_for_function(f'__U.frame() >= {f0} + {n}', timeout=180000); return (time.time() - t) / n
with sync_playwright() as p:
    b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_context(viewport={'width': 640, 'height': 400}, color_scheme='dark', reduced_motion='reduce').new_page()
    pg.add_init_script("window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
    pg.goto(URL); pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
    pg.evaluate("__U.S.playing = false; __U.goStop(__U.STOPS.find(s => s.name === 'Terre et Lune'), true)"); frames(pg, 6)
    prev = None; lr = 26.75
    while lr >= -20.01:
        pg.evaluate(f"__U.S.anim = null; __U.S.logR = {lr}"); frames(pg, 3); ft = frames(pg, 4)
        img = Image.open(io.BytesIO(pg.screenshot())).convert('L').resize((160, 100))
        d = ImageStat.Stat(ImageChops.difference(img, prev)).mean[0] if prev else None; prev = img
        place = pg.evaluate("document.getElementById('place').textContent")
        out.append([round(lr, 2), round(ft * 1000), None if d is None else round(d, 2), place]); print(out[-1], flush=True)
        lr -= 0.25
    b.close()
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else 'zoom_releve.json', 'w', encoding='utf-8'), ensure_ascii=False)
