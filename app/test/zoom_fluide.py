#!/usr/bin/env python3
"""Test à l'écran « zoom-fluide » (mission 2, tâche R12).

- Un même cran de molette change l'échelle d'autant de puissances de dix partout (grand, petit, infiniment petit), sauf dans les
  étendues vides, traversées trois fois plus vite, et alors le panneau dit « Traversée rapide ».
- Le compteur d'images par seconde s'affiche quand on le coche, avec un nombre.
- Sur téléphone (niveaux 0 et 1), les molécules d'eau sont dessinées avec au moins deux fois moins de triangles qu'en niveau ordinateur.
Lancer : python3 app/build.py puis python3 app/test/zoom_fluide.py   (PYTHONIOENCODING=utf-8 sous Windows)
"""
import os, sys, re
from playwright.sync_api import sync_playwright

URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'index.html')))


def frames(pg, n=3):
    f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() >= {f0} + {n}', timeout=180000)


def page(p, tier):
    b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_context(viewport={'width': 1280, 'height': 800}, color_scheme='dark', reduced_motion='reduce').new_page()
    pg.add_init_script(f"window.__TIER={tier}; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
    pg.goto(URL); pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
    pg.evaluate("__U.S.playing = false; __U.goStop(__U.STOPS.find(s => s.name === 'Terre et Lune'), true)"); frames(pg, 6)
    return b, pg


def tris(pg, lr):
    pg.evaluate(f"__U.S.anim = null; __U.S.logR = {lr}"); frames(pg, 4)
    return pg.evaluate("__U.Rr.scene.children.filter(o => o.visible && o.isInstancedMesh).reduce((a, o) => a + o.geometry.index.count / 3 * o.count, 0)")


def main():
    bad = 0
    def check(ok, msg):
        nonlocal bad
        print(('PASSE  ' if ok else 'ÉCHEC  ') + msg); bad += 0 if ok else 1
    with sync_playwright() as p:
        b, pg = page(p, 2)
        pg.mouse.move(640, 400); steps = {}
        for lr in [9.0, 2.5, -3.0, -10.5, -15.0, 4.5, 1.2, -1.0, -6.0, -12.8, -18.0]:
            pg.evaluate(f"__U.S.anim = null; __U.S.logR = {lr}"); frames(pg, 2)
            pg.mouse.wheel(0, -100); frames(pg, 2)
            steps[lr] = (lr - pg.evaluate('__U.S.logR'), pg.evaluate("document.getElementById('notice').hidden ? '' : document.getElementById('notice').textContent"))
        base = [steps[k][0] for k in (9.0, 2.5, -3.0, -10.5, -15.0)]
        check(max(base) - min(base) < 1e-6 and base[0] > 0, 'même cran de molette, hors étendues vides : ' + ', '.join(f'{d:.3f}' for d in base) + ' puissance de dix')
        fast = [steps[k] for k in (4.5, 1.2, -1.0, -6.0, -12.8, -18.0)]
        check(all(abs(d / base[0] - 3) < 0.01 and 'Traversée rapide' in t for d, t in fast), 'étendues vides (au-dessus de la Terre, près de la surface, approche de la goutte, eau, vide de l’atome, quark) : trois fois plus vite et « Traversée rapide » affiché : ' + ', '.join(f'{d:.3f}' for d, _ in fast))
        pg.evaluate("document.getElementById('c-fps').click()"); pg.wait_for_timeout(2500)
        txt = pg.evaluate("[document.getElementById('fps').hidden, document.getElementById('fps').textContent]")
        check(not txt[0] and re.match(r'^\d+ images/s$', txt[1]), f'compteur coché : « {txt[1]} »')
        t2 = tris(pg, -9.25); b.close()
        b, pg = page(p, 1); t1 = tris(pg, -9.25); b.close()
    check(0 < t1 * 2 <= t2, f'molécules d’eau : {t1} triangles sur téléphone, {t2} sur ordinateur')
    print('zoom-fluide :', 'PASSE' if bad == 0 else f'ÉCHEC ({bad})')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
