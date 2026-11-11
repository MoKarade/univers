import sys, json, time
from playwright.sync_api import sync_playwright
from PIL import Image
import os
url = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'index.html')))
mode = sys.argv[1] if len(sys.argv) > 1 else 'desk'
W, H, tier = (1280, 800, 1) if mode == 'desk' else (390, 780, 0)
shots = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
logs = []
with sync_playwright() as p:
    b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    ctx = b.new_context(viewport={'width': W, 'height': H}, device_scale_factor=1 if mode == 'desk' else 2, color_scheme='dark', reduced_motion='reduce', has_touch=(mode != 'desk'), is_mobile=(mode != 'desk'))
    pg = ctx.new_page()
    pg.add_init_script(f"window.__TIER={tier}; window.__NOADAPT=true;" + os.environ.get("U_INIT", ""))
    pg.on('console', lambda m: logs.append(f'[{m.type}] {m.text}') if m.type in ('error', 'warning') else None)
    pg.on('pageerror', lambda e: logs.append('[pageerror] ' + str(e)))
    t0 = time.time(); pg.goto(url)
    try:
        pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=120000)
    except Exception as e:
        print('TIMEOUT', e); print('\n'.join(logs)); print(pg.evaluate("document.getElementById('lmsg') && document.getElementById('lmsg').textContent")); sys.exit(1)
    print('prêt en %.1f s' % (time.time() - t0), '| hdr:', pg.evaluate('__U.Rr.hdr'), '| point max:', pg.evaluate('__U.Rr.maxPointRadius'))
    default = [['stop', i, None] for i in range(8)]
    files = []
    for k, spec in enumerate(shots or default):
        kind, arg, extra = spec
        f0 = pg.evaluate('__U.frame()')
        if kind == 'stop': pg.evaluate(f'__U.S.playing=false; __U.goStop(__U.STOPS[{arg}], true)')
        elif kind == 'js': pg.evaluate(arg)
        if extra: pg.evaluate(extra)
        t1 = time.time()
        pg.wait_for_function(f'__U.frame() > {f0} + 3', timeout=120000)
        dt = (time.time() - t1) / 4
        pg.wait_for_timeout(350)
        fn = f'/tmp/shot_{mode}_{k}.png'; pg.screenshot(path=fn); files.append(fn)
        print(k, kind, str(arg)[:60], '| %.2f s/image |' % dt, pg.evaluate("[document.getElementById('place').textContent, document.getElementById('field').textContent, document.getElementById('date').textContent, document.getElementById('notice').textContent].join(' | ')"), '\n      étiquettes:', pg.evaluate("[...document.querySelectorAll('.lb')].filter(e=>e.style.visibility==='visible').map(e=>e.textContent).slice(0,14).join(', ')"), '| fiche:', pg.evaluate("document.getElementById('card').hidden ? '' : document.getElementById('card').innerText.replace(/\\n/g,' / ').slice(0,330)"))
    b.close()
cols = 2 if mode == 'desk' else 4
tw, th = (960, 600) if mode == 'desk' else (390, 780)
rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (cols * tw, rows * th), (30, 30, 30))
for i, fn in enumerate(files):
    sheet.paste(Image.open(fn).convert('RGB').resize((tw, th), Image.LANCZOS), ((i % cols) * tw, (i // cols) * th))
sheet.save(f'/tmp/sheet_{mode}.png')
print('console:', len(logs)); print('\n'.join(logs[:25]))
