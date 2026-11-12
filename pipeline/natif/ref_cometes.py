#!/usr/bin/env python3
"""Positions de référence de quelques comètes, lues dans JPL Horizons -> ref_cometes.json.

Pour chaque comète : position par rapport au Soleil (UA, écliptique J2000) au jour julien JD (TDB), dernière orbite
publiée (« CAP »). Sert à mesurer l'écart de l'orbite simple de l'appli PC (asteroides_jpl.py --controle).
Usage : python ref_cometes.py
"""
import json
import os
import re
import urllib.parse
import urllib.request

JD = 2461357.5      # 12 novembre 2026
COMETES = ['1P', '2P', '4P', '29P', '67P', '109P', '81P', '9P']


def position(des: str) -> list[float]:
    q = {'format': 'text', 'COMMAND': f"'DES={des};CAP;NOFRAG'", 'EPHEM_TYPE': 'VECTORS', 'CENTER': "'@10'",
         'REF_PLANE': 'ECLIPTIC', 'TLIST': str(JD), 'VEC_TABLE': '1', 'OUT_UNITS': 'AU-D', 'MAKE_EPHEM': 'YES', 'OBJ_DATA': 'NO'}
    txt = urllib.request.urlopen('https://ssd.jpl.nasa.gov/api/horizons.api?' + urllib.parse.urlencode(q), timeout=60).read().decode()
    block = txt[txt.index('$$SOE'):txt.index('$$EOE')]
    m = re.search(r'X\s*=\s*(\S+)\s+Y\s*=\s*(\S+)\s+Z\s*=\s*(\S+)', block)
    return [float(m.group(k)) for k in (1, 2, 3)]


def main() -> None:
    out = {'jd': JD, 'source': 'JPL Horizons, vecteurs héliocentriques, écliptique J2000, UA', 'corps': {c: position(c) for c in COMETES}}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ref_cometes.json')
    json.dump(out, open(path, 'w', encoding='utf-8'), indent=1)
    for c, v in out['corps'].items():
        print(c, v)


if __name__ == '__main__':
    main()
