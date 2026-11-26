#!/usr/bin/env python3
"""Positions de référence de quelques astéroïdes du catalogue, demandées à JPL Horizons (https://ssd.jpl.nasa.gov/api/
horizons.api) : héliocentriques, écliptique J2000, en UA, au jour julien 2461354.5 (TDB), 154 jours après l'époque
du catalogue. Écrit ref_asteroides.json à côté de ce script ; lu par asteroides.py --controle.
Usage : python ref_asteroides.py"""
import json, os, re, urllib.parse, urllib.request

JD = 2461354.5
NUMBERS = ['719', '878', '1036', '2000', '5000', '20000']


def main():
    out = {'source': 'JPL Horizons, héliocentrique (500@10), écliptique J2000, UA', 'jd': JD, 'corps': {}}
    for num in NUMBERS:
        q = {'format': 'text', 'COMMAND': f"'{num};'", 'OBJ_DATA': 'NO', 'MAKE_EPHEM': 'YES', 'EPHEM_TYPE': 'VECTORS', 'CENTER': "'500@10'",
             'REF_PLANE': 'ECLIPTIC', 'REF_SYSTEM': 'ICRF', 'OUT_UNITS': 'AU-D', 'VEC_TABLE': '1', 'TLIST': f"'{JD}'"}
        url = 'https://ssd.jpl.nasa.gov/api/horizons.api?' + urllib.parse.urlencode(q)
        with urllib.request.urlopen(url, timeout=60) as resp:
            txt = resp.read().decode('utf-8', 'replace')
        m = re.search(r'\$\$SOE(.*?)\$\$EOE', txt, re.S)
        if not m: print(num, 'pas de réponse exploitable'); continue
        v = re.search(r'X\s*=\s*(\S+)\s+Y\s*=\s*(\S+)\s+Z\s*=\s*(\S+)', m.group(1))
        out['corps'][num] = [float(v.group(k)) for k in (1, 2, 3)]
        print(num, out['corps'][num])
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ref_asteroides.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
