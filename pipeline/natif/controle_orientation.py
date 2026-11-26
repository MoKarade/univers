#!/usr/bin/env python3
"""Relit les éléments d'orientation de natif/src/orientation.h contre le fichier officiel de la NASA (NAIF,
pck00011.tpc : constantes de rotation des planètes, d'après le rapport 2015 du groupe de travail de l'UAI).
Pour chaque astre : ascension droite et déclinaison du pôle (valeur et dérive par siècle), méridien d'origine
(valeur et vitesse par jour). Tolérance : 1e-6 en valeur relative ou absolue.
Usage : python controle_orientation.py [pck00011.tpc]   (sans argument : téléchargé du NAIF dans le dossier temporaire)
"""
import os, re, sys, tempfile, urllib.request
from pathlib import Path

_PIPE_DIR = str(Path(__file__).resolve().parents[1])
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import REPO_ROOT  # noqa: E402

ROOT = str(REPO_ROOT)
URL = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc'
# nom dans orientation.h -> code du corps dans le fichier de la NASA (centre de la planète)
CODES = {'kSun': 10, 'kMercury': 199, 'kVenus': 299, 'kEarth': 399, 'kMoon': 301, 'kMarsBary': 499, 'kJupiterBary': 599, 'kSaturnBary': 699,
         'kUranusBary': 799, 'kNeptuneBary': 899, 'kPlutoBary': 999}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), 'pck00011.tpc')
    if not os.path.exists(path): urllib.request.urlretrieve(URL, path)
    with open(path, encoding='latin-1') as fh:
        pck = fh.read()

    def values(code, key):
        m = re.search(r'BODY%d_%s\s*=\s*\(([^)]*)\)' % (code, key), pck)
        return [float(x.replace('D', 'E')) for x in m.group(1).split()] if m else None

    with open(REPO_ROOT / 'natif' / 'src' / 'orientation.h', encoding='utf-8') as fh:
        src = fh.read()
    ok = True; n = 0
    for name, num in re.findall(r'\{\s*eph::(\w+)\s*,\s*([^}]*)\}', src):
        mine = [float(x) for x in num.split(',')]
        code = CODES[name]; ra, dec, pm = values(code, 'POLE_RA'), values(code, 'POLE_DEC'), values(code, 'PM')
        if not (ra and dec and pm): print(f'{name} : absent du fichier de la NASA'); ok = False; continue
        want = [ra[0], ra[1], dec[0], dec[1], pm[0], pm[1]]
        bad = [(a, b) for a, b in zip(mine, want) if abs(a - b) > 1e-6 * max(1.0, abs(b))]
        n += 1; ok &= not bad
        print(f"{name:13s} : {'conforme' if not bad else 'ÉCART ' + str(bad)}")
    print('PASSE' if ok and n >= 10 else 'ÉCHEC')
    sys.exit(0 if ok and n >= 10 else 1)


if __name__ == '__main__':
    main()
