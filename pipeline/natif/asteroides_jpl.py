#!/usr/bin/env python3
"""TOUS les astéroïdes connus du JPL -> asteroides.bin et asteroides_noms.txt pour l'appli PC.

Remplace le sous-ensemble de la page (123 530 astéroïdes, sans les numéros 1 à 718 : ni Cérès, ni Vesta) par la base
complète du JPL : Small-Body Database, https://ssd-api.jpl.nasa.gov/sbdb_query.api (sb-kind=a, pleine précision).
Pour chaque astéroïde : demi-grand axe a (UA), excentricité e, inclinaison i, nœud om, argument du périhélie w,
anomalie moyenne ma (degrés), date de ces éléments (jour julien), magnitude absolue H. Ne sont gardés que ceux dont
l'orbite est une ellipse complète (a > 0, e < 1) ; les autres sont comptés et dits.
Les éléments sont ramenés à une date commune (la plus fréquente dans la base) en avançant l'anomalie moyenne à la
vitesse de l'orbite : aucun autre calcul.

Même format que asteroides.py : « UNIVAST1 », n, date commune, puis Px, Py, Pz, Qx, Qy, Qz, e, M0, n, H ; noms
« Nom~désignation », un par ligne. Un astéroïde sans magnitude H reçoit 99 (point le plus petit).
Avec --controle : compare à JPL Horizons (ref_asteroides.json, 154 jours après) et à Cérès, Pallas, Vesta, Hygie de
app/test/nbody_ref.json ; écart attendu sous 0,002 UA (orbite suivie sans l'attraction des planètes).
Usage : python asteroides_jpl.py <dossier de sortie> [--controle] [--depuis fichier.json]
"""
import json, math, os, sys, urllib.request
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etoiles import ROOT, ALIGN      # noqa: E402
from asteroides import MAGIC, K_GAUSS, position      # noqa: E402

URL = 'https://ssd-api.jpl.nasa.gov/sbdb_query.api?fields=pdes,name,a,e,i,om,w,ma,epoch,H&sb-kind=a&full-prec=true'


def main():
    sortie = sys.argv[1]
    brut = os.path.join(sortie, 'sbdb_asteroides.json')
    if '--depuis' in sys.argv: brut = sys.argv[sys.argv.index('--depuis') + 1]
    elif not os.path.exists(brut):
        urllib.request.urlretrieve(URL, brut)
    d = json.load(open(brut, encoding='utf-8'))
    rows = d['data']
    total = len(rows)

    def col(k):
        return np.array([float(r[k]) if r[k] not in (None, '') else np.nan for r in rows])
    a, e, inc, om, w, ma, ep, H = (col(k) for k in range(2, 10))
    ok = np.isfinite(a) & np.isfinite(e) & np.isfinite(inc) & np.isfinite(om) & np.isfinite(w) & np.isfinite(ma) & np.isfinite(ep) & (a > 0) & (e >= 0) & (e < 1)
    ecartes = int((~ok).sum())
    idx = np.where(ok)[0]
    a, e, inc, om, w, ma, ep, H = (x[idx] for x in (a, e, inc, om, w, ma, ep, H))
    names = [f"{rows[i][1] or ''}~{rows[i][0]}" for i in idx]
    vals, counts = np.unique(ep, return_counts=True); epoch = float(vals[counts.argmax()])
    n = K_GAUSS / a ** 1.5
    m0 = (np.radians(ma) + n * (epoch - ep)) % (2 * math.pi)
    inc, om, w = np.radians(inc), np.radians(om), np.radians(w)
    b = a * np.sqrt(1 - e * e); co, so, ci, si, cw, sw = np.cos(om), np.sin(om), np.cos(inc), np.sin(inc), np.cos(w), np.sin(w)
    H = np.where(np.isfinite(H), H, 99.0)
    cols = [a * (co * cw - so * sw * ci), a * (so * cw + co * sw * ci), a * sw * si,
            b * (-co * sw - so * cw * ci), b * (-so * sw + co * cw * ci), b * cw * si, e, m0, n, H]
    path = os.path.join(sortie, 'asteroides.bin')
    with open(path, 'wb') as out:
        head = MAGIC + np.int64(len(a)).tobytes() + np.float64(epoch).tobytes()
        out.write(head + b'\0' * (ALIGN - len(head)))
        for c in cols:
            raw = c.astype('<f4').tobytes(); out.write(raw + b'\0' * (-len(raw) % ALIGN))
    open(os.path.join(sortie, 'asteroides_noms.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(names) + '\n')
    print(f'{len(a)} astéroïdes écrits sur {total} dans la base du JPL ({ecartes} écartés : orbite non elliptique ou incomplète) ; '
          f'date commune JJ {epoch} ({int(counts.max())} astéroïdes déjà à cette date) ; {os.path.getsize(path) / 1e6:.1f} Mo')
    if '--controle' in sys.argv:
        here = os.path.dirname(os.path.abspath(__file__))
        ref = json.load(open(os.path.join(here, 'ref_asteroides.json'), encoding='utf-8'))
        nb = json.load(open(os.path.join(ROOT, 'app', 'test', 'nbody_ref.json'), encoding='utf-8'))['epoch']
        number = {nm.split('~')[-1]: k for k, nm in enumerate(names)}
        c32 = [c.astype(np.float32) for c in cols]
        tests = [(num, ref['jd'], np.array(v)) for num, v in ref['corps'].items()]
        tests += [(num, nb[key]['jd'], np.array(nb[key]['r']) - np.array(nb['sun']['r'])) for key, num in (('ceres', '1'), ('pallas', '2'), ('vesta', '4'), ('hygiea', '10'))]
        good_all, judged = True, 0
        for num, jd, want in tests:
            i = number.get(num)
            if i is None: print(f'{num} : absent du catalogue'); good_all = False; continue
            dist = float(np.linalg.norm(position(c32, i, jd, epoch) - want)); good = dist < 0.002; good_all &= good; judged += 1
            print(f"{names[i]} au JJ {jd} : écart avec JPL Horizons {dist:.6f} UA ({dist * 149597870.7:.0f} km) -> {'PASSE' if good else 'ÉCHEC'}")
        sys.exit(0 if good_all and judged >= 8 else 1)


if __name__ == '__main__':
    main()
