# S7 : essai dans la page (Playwright, rendu logiciel).
# Lancer : python3 app/test/cone_screen.py (ou U_URL=file:///…/dist/index.html python3 app/test/cone_screen.py)
# Vérifie : la case déplace les galaxies des relevés de χ à χ/(1+z) ; la fiche donne la même distance ; le toucher retrouve la galaxie ;
# la vue ne s'applique pas loin d'aujourd'hui.
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
    pg = b.new_page(viewport={'width': 1000, 'height': 700})
    logs = []
    pg.on('pageerror', lambda e: logs.append(str(e)))
    # Ne pas fixer __TIER=1 ici : Q.keep=1 doit rester actif pour que pickAt retrouve la galaxie 43327.
    pg.add_init_script(
        'window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];'
        + os.environ.get('U_INIT', '')
    )
    pg.goto(URL)
    pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=120000)
    pg.evaluate('__U.S.playing=false; __U.goStop(__U.STOPS[7], true)')
    wait_frames(pg, 3)

    i = pg.evaluate(
        '(() => { const P = __U.Rr.pick; let best = -1; for (let k = 0; k < P.svN; k++)'
        ' if (P.svInfo[k*3+2] < 1.5 && P.svInfo[k*3] > 0.45 && P.svInfo[k*3] < 0.55) { best = k; break; } return best; })()'
    )
    z, d0 = pg.evaluate(f'[__U.Rr.pick.svInfo[{i}*3], __U.Rr.pick.svDist[{i}]]')
    pg.evaluate('document.getElementById("c-lc").click()')
    wait_frames(pg, 3)
    d1 = pg.evaluate(f'__U.Rr.pick.svDist[{i}]')
    print(f'galaxie {i}, z = {z:.3f} : {d0:.1f} Mpc -> {d1:.1f} Mpc (attendu {d0 / (1 + z):.1f})')
    if abs(d1 / (d0 / (1 + z)) - 1) > 0.002:
        fails.append('distance déplacée fausse')
    rows = pg.evaluate(f'__U.selSurv({i}).rows().map(r => r.join(" : "))')
    print('\n'.join('   ' + r for r in rows[:6]))
    if not any(r.startswith('Distance quand sa lumière est partie') for r in rows):
        fails.append('fiche : ligne de distance absente')
    if not any(r.startswith('S’éloigne aujourd’hui') for r in rows):
        fails.append('fiche : vitesse sans « aujourd’hui »')
    hit = pg.evaluate(
        f'''(() => {{ const P = __U.Rr.pick, F = __U.F, k = 3.0857e22 * F.cos.a, w = [0,1,2].map(c => F.gcRel[c] + P.svDir[{i}*3+c] * P.svDist[{i}] * k), sc = [0,0,0];
      if (!__U.Rr.project(w, F, sc)) return null; const q = __U.pickAt(sc[0], sc[1], true); return q ? Math.hypot(q[0]-w[0], q[1]-w[1], q[2]-w[2]) / Math.hypot(...w) : -1; }})()'''
    )
    print('toucher : écart relatif', hit)
    if hit is None or hit < 0 or hit > 0.02:
        fails.append('le toucher ne retrouve pas la galaxie déplacée')
    pg.evaluate('__U.setTime(1e9)')
    wait_frames(pg, 3)
    d2 = pg.evaluate(f'__U.Rr.pick.svDist[{i}]')
    prov = pg.evaluate("document.getElementById('prov').textContent")
    print(f'dans 1 milliard d’années : {d2:.1f} Mpc ; provenance : …{prov[-70:]}')
    if abs(d2 / d0 - 1) > 0.002 or 'seulement autour d’aujourd’hui' not in prov:
        fails.append('loin d’aujourd’hui : la vue devrait être coupée et le dire')
    rows2 = pg.evaluate(f'__U.selSurv({i}).rows().map(r => r.join(" : "))')
    v2 = [r for r in rows2 if r.startswith('S’éloigne')]
    print('   fiche loin d’aujourd’hui :', [r for r in rows2 if r.startswith('Distance')][:1], v2)
    if not any(r.startswith('Distance à cet instant') for r in rows2) or not v2 or not v2[0].startswith('S’éloigne à'):
        fails.append('fiche loin d’aujourd’hui : devrait parler de la distance à cet instant')
    if logs:
        fails.append('erreurs de page : ' + logs[0])
    b.close()

print('ÉCHECS :' if fails else 'tout est vert', fails)
sys.exit(1 if fails else 0)
