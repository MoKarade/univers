#!/usr/bin/env python3
"""Exporte les conditions de départ du calcul de la fusion depuis la page construite (R9).

La page est la source : positions et vitesses d'Andromède, du Grand Nuage, du Triangle, des galaxies naines et du Soleil,
dans le repère galactocentrique de son orbite d'Andromède (`__U.fusionCI`, 60_app.js). Écrit pipeline/fusion/conditions.json.
Lancer : python3 app/build.py puis python3 pipeline/fusion/exporter_conditions.py (Playwright, rendu logiciel).
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
URL = HERE.parents[1].joinpath('dist', 'index.html').as_uri()


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = b.new_page()
        pg.add_init_script("window.__TIER=1; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
        pg.goto(URL); pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
        ci = pg.evaluate('__U.fusionCI()')
        b.close()
    with open(HERE / 'conditions.json', 'w', encoding='utf-8', newline='\n') as f:
        json.dump(ci, f, ensure_ascii=False, indent=1)
    print('galaxies naines :', len(ci['dwarfs']), '| Triangle :', [d['name'] for d in ci['dwarfs'] if 'Triangle' in d['name']], '| Soleil :', ci['sun'])


if __name__ == '__main__':
    main()
