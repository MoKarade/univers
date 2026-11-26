# Simule un décrochage de la carte graphique et vérifie que la page repart au même endroit.
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

URL = os.environ.get('U_URL') or Path(__file__).resolve().parents[2].joinpath('dist', 'index.html').as_uri()
LAUNCH_ARGS = ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']


def wait_frames(pg, n=3):
    f0 = pg.evaluate('__U.frame()')
    pg.wait_for_function(f'__U.frame() >= {f0} + {n}', timeout=120000)


fails = []
with sync_playwright() as p:
    b = p.chromium.launch(args=LAUNCH_ARGS)
    pg = b.new_page(viewport={'width': 1280, 'height': 800})
    logs = []
    pageerrs = []
    pg.on(
        'console',
        lambda msg: logs.append('[%s] %s' % (msg.type, msg.text[:160]))
        if msg.type in ('error', 'warning') and 'GPU stall' not in msg.text
        else None,
    )
    pg.on('pageerror', lambda e: pageerrs.append(str(e)))
    pg.add_init_script(
        'window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];'
        + os.environ.get('U_INIT', '')
    )
    pg.goto(URL)
    pg.wait_for_function(
        'window.__U && window.__U.F && window.__U.F.age > 0 && window.__U.frame() > 2',
        timeout=120000,
    )
    wait_frames(pg, 3)

    pg.evaluate("__U.S.playing=false; __U.goName('Sirius')")
    pg.wait_for_function('!__U.S.anim', timeout=120000)
    pg.evaluate('__U.goTo(12.2,{instant:true,noHist:true,az:1.1,el:0.5})')
    pg.wait_for_function('!__U.S.anim', timeout=120000)
    wait_frames(pg, 3)

    before = pg.evaluate(
        "({lr: __U.S.logR, az: __U.S.az, el: __U.S.el, titre: document.getElementById('place').textContent})"
    )
    print('avant :', before)

    pg.evaluate('window.__BEFORE_LOST = 1')
    try:
        pg.evaluate(
            "var c=document.querySelector('canvas'), gl=c.getContext('webgl2')||c.getContext('webgl');"
            " gl.getExtension('WEBGL_lose_context').loseContext(); 0"
        )
    except Exception as e:
        print('déclenchement :', str(e)[:80])

    pg.wait_for_function(
        '!window.__BEFORE_LOST && window.__U && window.__U.F && window.__U.F.age > 0 && window.__U.frame() > 2',
        timeout=120000,
    )
    wait_frames(pg, 3)

    after = pg.evaluate(
        "({lr: __U.S.logR, az: __U.S.az, el: __U.S.el, titre: document.getElementById('place').textContent,"
        " perdu: !!__U.S.lost, resumed: !!__U.S.resumed})"
    )
    print('après :', after)
    print('journal :', logs[-4:])

    if not after['resumed']:
        fails.append('reprise non signalée (__U.S.resumed faux)')
    if after['perdu']:
        fails.append('contexte toujours perdu après rechargement')
    if abs(after['lr'] - before['lr']) > 0.05:
        fails.append(f"logR non restauré : {after['lr']} vs {before['lr']}")
    if abs(after['az'] - before['az']) > 0.05:
        fails.append(f"az non restauré : {after['az']} vs {before['az']}")
    if abs(after['el'] - before['el']) > 0.05:
        fails.append(f"el non restauré : {after['el']} vs {before['el']}")
    if after['titre'] != before['titre']:
        fails.append(f"lieu non restauré : {after['titre']!r} vs {before['titre']!r}")
    if pageerrs:
        fails.append('erreurs de page : ' + pageerrs[0])

    b.close()

print('ÉCHECS :' if fails else 'tout est vert', fails)
sys.exit(1 if fails else 0)
