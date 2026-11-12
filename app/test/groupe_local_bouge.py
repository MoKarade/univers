#!/usr/bin/env python3
"""Test à l'écran « groupe-local-bouge » (mission 2, suite de R18 : Marc voyait des galaxies immobiles à l'échelle du Groupe local).

Chaque galaxie du Groupe local qui a une vitesse mesurée (déplacement dans le ciel, ou seulement le long de la ligne de visée) et qui est à
plus de 50 kpc du centre de la Voie lactée doit s'être déplacée 3 milliards d'années plus tard. Celles qui restent en place doivent le dire
(« inconnu ») dans leur fiche. Celles qui bougent sans déplacement mesuré dans le ciel doivent dire que la part de côté est supposée.
Lancer : python3 app/build.py puis python3 app/test/groupe_local_bouge.py   (PYTHONIOENCODING=utf-8 sous Windows)
"""
import os, sys
from playwright.sync_api import sync_playwright

URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'index.html')))
STATE = """(() => { const U = __U, X = DATA.LG_X, out = [];
  U.G.lg.centers.forEach((c, i) => { if (c.own || c.m0 || c.grp) return; const rows = U.selLG(c).rows(), m = rows.find(r => r[0] === 'Mouvement dans la simulation'), side = rows.find(r => r[0] === 'Part de côté du mouvement');
    out.push({ n: c.g.n, vl: X[i] ? X[i][1] : null, r: Math.hypot(...c.c0), dx: Math.hypot(c.c[0] - c.c0[0], c.c[1] - c.c0[1], c.c[2] - c.c0[2]), pm: !!(DATA.LGV && DATA.LGV[i]), m: m ? m[1] : '', side: side ? side[1] : '' }); });
  return out; })()"""


def main():
    bad = 0
    def check(ok, msg):
        nonlocal bad
        print(('PASSE  ' if ok else 'ÉCHEC  ') + msg); bad += 0 if ok else 1
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = b.new_context(viewport={'width': 1280, 'height': 800}, color_scheme='dark', reduced_motion='reduce').new_page()
        pg.add_init_script("window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
        pg.goto(URL); pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
        pg.evaluate("__U.S.playing = false")
        pg.evaluate("__U.S.ty = 3e9; __U.S.lastTy = 3e9")
        pg.wait_for_function(STATE.replace('return out; })()', 'return out.filter(g => g.vl !== null && g.r >= 50).every(g => g.dx > 1); })()'), timeout=120000)
        G = pg.evaluate(STATE)
        b.close()
    mov = [g for g in G if g['vl'] is not None and g['r'] >= 50]
    still = [g for g in G if g['dx'] <= 1]
    rad = [g for g in mov if not g['pm']]
    check(all(g['dx'] > 1 for g in mov), f"{len(mov)} galaxies avec vitesse mesurée, à plus de 50 kpc : toutes déplacées à +3 Ga (de {min(g['dx'] for g in mov):.0f} à {max(g['dx'] for g in mov):.0f} kpc)")
    check(len(rad) > 0 and all('supposée' in g['side'] and 'scénario' in g['m'] for g in rad), f"{len(rad)} sans déplacement mesuré dans le ciel : la fiche dit « scénario » et « part de côté supposée »")
    check(all('inconnu' in g['m'] for g in still), f"{len(still)} restées en place ({', '.join(g['n'] for g in still)}) : la fiche dit « inconnu »")
    print('groupe-local-bouge :', 'PASSE' if bad == 0 else f'ÉCHEC ({bad})')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
