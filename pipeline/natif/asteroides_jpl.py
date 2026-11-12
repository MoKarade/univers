#!/usr/bin/env python3
"""TOUS les astéroïdes et les comètes connus du JPL -> asteroides.bin et asteroides_noms.txt pour l'appli PC.

Remplace le sous-ensemble de la page (123 530 astéroïdes, sans les numéros 1 à 718 : ni Cérès, ni Vesta) par la base
complète du JPL : Small-Body Database, https://ssd-api.jpl.nasa.gov/sbdb_query.api (pleine précision), astéroïdes
(sb-kind=a) puis comètes (sb-kind=c).
Pour chaque corps : demi-grand axe a (UA), excentricité e, inclinaison i, nœud om, argument du périhélie w,
anomalie moyenne ma (degrés), date de ces éléments (jour julien), magnitude absolue H. Ne sont gardés que ceux dont
l'orbite est une ellipse complète (a > 0, e < 1) ; les autres sont comptés et dits. Comètes : les comètes disparues ou
détruites (préfixe « D ») sont écartées, elles n'existent plus ; celles passées une seule fois sur une orbite ouverte
(e >= 1) aussi, cette orbite simple ne les suit pas.
Les éléments sont ramenés à une date commune (la plus fréquente dans la base) en avançant l'anomalie moyenne à la
vitesse de l'orbite : aucun autre calcul.

Même format que asteroides.py : « UNIVAST1 », n, date commune, puis Px, Py, Pz, Qx, Qy, Qz, e, M0, n, H ; noms
« Nom~désignation », un par ligne, les comètes à la fin avec « ~c » en plus (« Halley~1P~c »). Sans magnitude H
(toutes les comètes) : 99, le point le plus petit.
Avec --controle : astéroïdes comparés à JPL Horizons (ref_asteroides.json, 154 jours après) et à Cérès, Pallas, Vesta,
Hygie de app/test/nbody_ref.json ; comètes comparées à ref_cometes.json ; écart exigé sous 0,002 UA.
Comètes : l'orbite de la base date parfois de dizaines d'années (écart mesuré jusqu'à 0,67 UA) ; on prend donc l'orbite
à jour lue dans Horizons par cometes_horizons.py, et on écarte les comètes pour lesquelles Horizons n'en rend pas.
Usage : python asteroides_jpl.py <dossier de sortie> [--controle]
"""
import json
import math
import os
import sys
import urllib.request

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etoiles import ROOT, ALIGN      # noqa: E402
from asteroides import MAGIC, K_GAUSS, position      # noqa: E402

BASE = 'https://ssd-api.jpl.nasa.gov/sbdb_query.api?full-prec=true&fields='
URL_AST = BASE + 'pdes,name,a,e,i,om,w,ma,epoch,H&sb-kind=a'
URL_COM = BASE + 'pdes,name,a,e,i,om,w,ma,epoch,M1,prefix&sb-kind=c'


def lire(sortie: str, fichier: str, url: str) -> list:
    brut = os.path.join(sortie, fichier)
    if not os.path.exists(brut):
        urllib.request.urlretrieve(url, brut)
    with open(brut, encoding='utf-8') as f:
        return json.load(f)['data']


def elements(rows: list, comet: bool):
    """Rend (a, e, i, om, w, ma, date, H, noms, nombre écarté) pour les orbites elliptiques complètes."""
    def col(k):
        return np.array([float(r[k]) if r[k] not in (None, '') else np.nan for r in rows])
    a, e, inc, om, w, ma, ep = (col(k) for k in range(2, 9))
    H = np.full(len(rows), np.nan) if comet else col(9)
    ok = np.isfinite(a) & np.isfinite(e) & np.isfinite(inc) & np.isfinite(om) & np.isfinite(w) & np.isfinite(ma) & np.isfinite(ep) & (a > 0) & (e >= 0) & (e < 1)
    if comet:
        ok &= np.array([r[10] != 'D' for r in rows])
    idx = np.where(ok)[0]
    names = [f"{rows[i][1] or ''}~{rows[i][0]}" + ('~c' if comet else '') for i in idx]
    return [x[idx] for x in (a, e, inc, om, w, ma, ep, H)], names, int((~ok).sum())


def main() -> None:
    sortie = sys.argv[1]
    ast, names, ecartes_a = elements(lire(sortie, 'sbdb_asteroides.json', URL_AST), False)
    com, names_c, ecartes_c = elements(lire(sortie, 'sbdb_cometes.json', URL_COM), True)
    # Comètes : orbite à jour lue dans Horizons (cometes_horizons.py) quand elle existe, sinon celle de la base.
    a_jour = 0
    hz_path = os.path.join(sortie, 'cometes_horizons.json')
    if os.path.exists(hz_path):
        with open(hz_path, encoding='utf-8') as f:
            hz = json.load(f)
        for k, nm in enumerate(names_c):
            el = hz['corps'].get(nm.split('~')[1])
            if el:
                for col, key in zip(range(6), ('A', 'EC', 'IN', 'OM', 'W', 'MA')):
                    com[col][k] = el[key]
                com[6][k] = hz['jd']
                a_jour += 1
        # Sans orbite à jour (Horizons n'en rend pas) : la comète serait mal placée (mesuré : jusqu'à 0,67 UA), on l'écarte.
        garde = np.array([nm.split('~')[1] in hz['corps'] for nm in names_c])
        ecartes_c += int((~garde).sum())
        com = [x[garde] for x in com]
        names_c = [nm for nm, g in zip(names_c, garde) if g]
    n_ast, n_com = len(names), len(names_c)
    a, e, inc, om, w, ma, ep, H = (np.concatenate([x, y]) for x, y in zip(ast, com))
    names += names_c
    vals, counts = np.unique(ep, return_counts=True)
    epoch = float(vals[counts.argmax()])
    n = K_GAUSS / a ** 1.5
    m0 = (np.radians(ma) + n * (epoch - ep)) % (2 * math.pi)
    inc, om, w = np.radians(inc), np.radians(om), np.radians(w)
    b = a * np.sqrt(1 - e * e)
    co, so, ci, si, cw, sw = np.cos(om), np.sin(om), np.cos(inc), np.sin(inc), np.cos(w), np.sin(w)
    H = np.where(np.isfinite(H), H, 99.0)
    cols = [a * (co * cw - so * sw * ci), a * (so * cw + co * sw * ci), a * sw * si,
            b * (-co * sw - so * cw * ci), b * (-so * sw + co * cw * ci), b * cw * si, e, m0, n, H]
    path = os.path.join(sortie, 'asteroides.bin')
    with open(path, 'wb') as out:
        head = MAGIC + np.int64(len(a)).tobytes() + np.float64(epoch).tobytes()
        out.write(head + b'\0' * (ALIGN - len(head)))
        for c in cols:
            raw = c.astype('<f4').tobytes()
            out.write(raw + b'\0' * (-len(raw) % ALIGN))
    with open(os.path.join(sortie, 'asteroides_noms.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(names) + '\n')
    print(f'{n_ast} astéroïdes écrits ({ecartes_a} écartés : orbite non elliptique ou incomplète) et {n_com} comètes '
          f'({ecartes_c} écartées : disparues, passées une seule fois sur une orbite ouverte, ou sans orbite à jour) ; '
          f'{a_jour} comètes avec une orbite à jour (Horizons) ; date commune JJ {epoch} ; {os.path.getsize(path) / 1e6:.1f} Mo')
    if '--controle' in sys.argv:
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, 'ref_asteroides.json'), encoding='utf-8') as f:
            ref = json.load(f)
        with open(os.path.join(here, 'ref_cometes.json'), encoding='utf-8') as f:
            refc = json.load(f)
        with open(os.path.join(ROOT, 'app', 'test', 'nbody_ref.json'), encoding='utf-8') as f:
            nb = json.load(f)['epoch']
        number = {nm.split('~')[1]: k for k, nm in enumerate(names)}
        c32 = [c.astype(np.float32) for c in cols]
        tests = [(num, ref['jd'], np.array(v), 0.002) for num, v in ref['corps'].items()]
        tests += [(num, nb[key]['jd'], np.array(nb[key]['r']) - np.array(nb['sun']['r']), 0.002)
                  for key, num in (('ceres', '1'), ('pallas', '2'), ('vesta', '4'), ('hygiea', '10'))]
        tests += [(num, refc['jd'], np.array(v), 0.0021) for num, v in refc['corps'].items()]
        good_all, judged = True, 0
        for num, jd, want, limit in tests:
            i = number.get(num)
            if limit > 0.002:      # comète : chercher parmi les comètes (« 1P » et l'astéroïde 1 ne se confondent pas, mais par sûreté)
                i = next((k for k in range(n_ast, len(names)) if names[k].split('~')[1] == num), None)
            if i is None:
                print(f'{num} : absent du catalogue')
                good_all = False
                continue
            dist = float(np.linalg.norm(position(c32, i, jd, epoch) - want))
            good = dist < limit
            good_all &= good
            judged += 1
            print(f"{names[i]} au JJ {jd} : écart avec JPL Horizons {dist:.6f} UA ({dist * 149597870.7:.0f} km), "
                  f"date des éléments JJ {ep[i]:.1f} -> {'PASSE' if good else 'ÉCHEC'}")
        sys.exit(0 if good_all and judged >= 16 else 1)


if __name__ == '__main__':
    main()
