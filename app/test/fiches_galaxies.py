#!/usr/bin/env python3
"""Test à l'écran « fiches-galaxies » (mission 2, tâche R18).

Pour chaque famille de galaxies (Groupe local, galaxies proches, galaxies photographiées, galaxies lointaines), vingt
galaxies : leur fiche doit avoir une ligne « Mouvement dans la simulation » et une ligne de rotation (« Rotation… »), chacune
avec sa raison. Les galaxies photographiées sont prises dans la liste des photos (pipeline/raw/gal/list.json, entrées
« near ») : les fichiers de photos ne sont pas dans le dépôt, la fiche est donc testée sans la photo chargée.
Lancer : python3 app/build.py puis python3 app/test/fiches_galaxies.py   (PYTHONIOENCODING=utf-8 sous Windows)
"""
import os, sys, json
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(HERE, '..', '..', 'dist', 'index.html')))
PHOTO_NEAR = [x[1] for x in json.load(open(os.path.join(HERE, '..', '..', 'pipeline', 'raw', 'gal', 'list.json'), encoding='utf-8')) if x[0] == 'near'][:20]
CHECK = """(fams) => { const U = __U, out = {};
  const ok = o => { const r = o.rows(), m = r.find(x => x[0] === 'Mouvement dans la simulation'), t = r.find(x => /^Rotation/.test(x[0]));
    return m && t && m[1].length > 20 && t[1].length > 20 ? null : o.name; };
  out['Groupe local'] = U.G.lg.centers.filter(c => !c.gone).slice(0, 20).map(c => ok(U.selLG(c)));
  out['galaxies proches'] = Array.from({ length: 20 }, (_, k) => ok(U.selNear(k * 37)));
  out['galaxies photographiées'] = fams.photo.map(i => ok(U.selNear(i)));
  out['galaxies lointaines'] = Array.from({ length: 20 }, (_, k) => ok(U.selSurv(k * 97)));
  return out; }"""


def main():
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = b.new_context(viewport={'width': 1280, 'height': 800}, color_scheme='dark', reduced_motion='reduce').new_page()
        pg.add_init_script("window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
        pg.goto(URL); pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
        res = pg.evaluate(CHECK, {'photo': PHOTO_NEAR})
        b.close()
    for fam, lst in res.items():
        miss = [x for x in lst if x]
        ok = len(lst) >= 20 and not miss
        bad += 0 if ok else 1
        print(f"{'PASSE' if ok else 'ÉCHEC'}  {fam} : {len(lst) - len(miss)} fiches sur {len(lst)} avec les deux lignes" + (f" ; manquent : {', '.join(miss[:5])}" if miss else ''))
    print('fiches-galaxies :', 'PASSE' if bad == 0 else f'ÉCHEC ({bad})')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
