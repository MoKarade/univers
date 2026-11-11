# Simule un décrochage de la carte graphique et vérifie que la page repart au même endroit.
import re, sys, time, json
from playwright.sync_api import sync_playwright
src = open('/home/claude/univers/test/shots.py').read(); m = re.search(r"launch\((.*)\)", src)
with sync_playwright() as p:
    b = eval('p.chromium.launch(' + m.group(1) + ')'); pg = b.new_page(viewport={'width': 1280, 'height': 800}); logs = []
    pg.on('console', lambda msg: logs.append('[%s] %s' % (msg.type, msg.text[:160])) if msg.type in ('error', 'warning') and 'GPU stall' not in msg.text else None)
    pg.add_init_script("window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
    pg.goto('file:///mnt/user-data/outputs/univers.html'); pg.wait_for_function("window.__U && window.__U.F && window.__U.F.age > 0", timeout=120000); pg.wait_for_timeout(1500)
    pg.evaluate("__U.S.playing=false; __U.goName('Sirius')"); pg.wait_for_timeout(6000); pg.evaluate("__U.goTo(12.2,{instant:true,noHist:true}); __U.S.az=1.1; __U.S.el=0.5"); pg.wait_for_timeout(1500)
    before = pg.evaluate("({lr: __U.S.logR, az: __U.S.az, el: __U.S.el, titre: document.getElementById('place').textContent})"); print('avant :', before)
    try: pg.evaluate("var c=document.querySelector('canvas'), gl=c.getContext('webgl2')||c.getContext('webgl'); gl.getExtension('WEBGL_lose_context').loseContext(); 0")
    except Exception as e: print('déclenchement :', str(e)[:80])
    pg.wait_for_timeout(400)
    try: print('message affiché :', pg.evaluate("document.getElementById('notice').textContent"))
    except Exception as e: print('page déjà en rechargement')
    pg.wait_for_timeout(2500); pg.wait_for_function("window.__U && window.__U.F && window.__U.F.age > 0", timeout=120000); pg.wait_for_timeout(2500)
    after = pg.evaluate("({lr: __U.S.logR, az: __U.S.az, el: __U.S.el, titre: document.getElementById('place').textContent, perdu: !!__U.S.lost, reprise: sessionStorage.getItem('univers-reprise')})"); print('après :', after)
    pg.screenshot(path='/tmp/lost_after.png'); print('journal :', logs[-4:]); b.close()
