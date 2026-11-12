#!/usr/bin/env python3
"""Orbites À JOUR des comètes, lues une par une dans JPL Horizons -> cometes_horizons.json (dans le dossier de sortie).

Pourquoi : la base SBDB donne l'orbite de chaque comète à la date de son dernier calcul, parfois vieille de dizaines
d'années. Suivie telle quelle jusqu'à aujourd'hui, elle place mal la comète (mesuré : jusqu'à 0,67 UA d'écart pour
9P/Tempel). Horizons, lui, rend l'orbite à la date demandée en tenant compte de l'attraction des planètes et des jets
de la comète. On lit donc ici, pour chaque comète elliptique de la base, ses éléments à la date commune du catalogue.

Reprise possible : les comètes déjà lues ne sont pas redemandées. Une requête à la fois (demande du JPL).
Usage : python cometes_horizons.py <dossier de sortie> <jour julien commun>
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

CLES = ('EC', 'IN', 'OM', 'W', 'MA', 'A')


def elements(des: str, jd: float) -> dict | None:
    q = {'format': 'text', 'COMMAND': f"'DES={des};CAP;NOFRAG'", 'EPHEM_TYPE': 'ELEMENTS', 'CENTER': "'@10'",
         'REF_PLANE': 'ECLIPTIC', 'TLIST': str(jd), 'OUT_UNITS': 'AU-D', 'MAKE_EPHEM': 'YES', 'OBJ_DATA': 'NO'}
    url = 'https://ssd.jpl.nasa.gov/api/horizons.api?' + urllib.parse.urlencode(q)
    for attempt in range(4):
        try:
            txt = urllib.request.urlopen(url, timeout=90).read().decode()
            break
        except Exception:      # réseau : nouvel essai, plus tard
            time.sleep(5 * (attempt + 1))
    else:
        return None
    if '$$SOE' not in txt:
        return None
    block = txt[txt.index('$$SOE'):txt.index('$$EOE')]
    out = {}
    for k in CLES:
        m = re.search(r'(?<![A-Za-z])' + k + r'\s*=\s*([-+0-9.Ee]+)', block)
        if not m:
            return None
        out[k] = float(m.group(1))
    return out


def main() -> None:
    sortie, jd = sys.argv[1], float(sys.argv[2])
    with open(os.path.join(sortie, 'sbdb_cometes.json'), encoding='utf-8') as f:
        rows = json.load(f)['data']
    path = os.path.join(sortie, 'cometes_horizons.json')
    done = {'jd': jd, 'corps': {}, 'refus': []}
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            done = json.load(f)
    todo = [r[0] for r in rows if r[2] and r[3] and float(r[3]) < 1 and float(r[2]) > 0 and r[7] and r[10] != 'D'
            and r[0] not in done['corps'] and r[0] not in done['refus']]
    for k, des in enumerate(todo):
        el = elements(des, jd)
        if el and 0 <= el['EC'] < 1 and el['A'] > 0:
            done['corps'][des] = el
        else:
            done['refus'].append(des)
        if k % 25 == 0 or k == len(todo) - 1:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(done, f)
            print(f"{k + 1} / {len(todo)} ; lues {len(done['corps'])}, refusées {len(done['refus'])}", flush=True)
        time.sleep(0.2)


if __name__ == '__main__':
    main()
