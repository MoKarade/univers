#!/usr/bin/env python3
"""Catalogue principal des étoiles à pleine précision, avec les vitesses radiales manquantes -> hyg_principal.npz.

Pourquoi : l'appli PC reprenait le catalogue principal de la page, arrondi pour tenir dans la page (distance à 0,02 %
près, vitesse à 0,05 km/s près), et les étoiles sans vitesse radiale dans le catalogue HYG y étaient comptées avec une
vitesse radiale nulle. Ici :
- mêmes étoiles, même ordre que la page (mêmes règles que pipeline/build_data3.py), relues dans le catalogue HYG v4.1
  (hygdata_v41.csv, astronexus) à pleine précision ;
- vitesse radiale : celle de SIMBAD quand elle existe (mesures plus récentes que HYG), sinon celle de HYG ; absente de HYG : prise dans SIMBAD (CDS, table basic, rvz_radvel, par numéro Hipparcos) quand elle y
  est MESURÉE ; sinon elle reste inconnue, et l'étoile est notée (colonne sans_vr) : rien n'est inventé ;
- la dernière étoile de la page (Gliese 710, ajoutée à la main d'après Gaia DR3) est gardée telle quelle.
Contrôles (le script s'arrête si l'un échoue) : même nombre d'étoiles que la page ; chaque position retombe sur celle
de la page à l'arrondi de la page près ; pour les étoiles dont HYG donne la vitesse radiale, la vitesse recalculée ici
(mouvement propre + vitesse radiale) retombe sur celle de HYG, à l'arrondi de HYG près.
Usage : python etoiles_hyg.py <hygdata_v41.csv> <simbad_hip_rv.csv> <dossier de sortie>
"""
import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etoiles import data_keys, principal      # noqa: E402

PC_LY = 3.2615637769
KMS = 977792.22      # 1 pc/an en km/s
OBLIQUITE = math.radians(23.4392911)


def fl(x: str, default: float = float('nan')) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def eq_to_ecl(v: np.ndarray) -> np.ndarray:
    c, s = math.cos(OBLIQUITE), math.sin(OBLIQUITE)
    return np.stack([v[:, 0], c * v[:, 1] + s * v[:, 2], -s * v[:, 1] + c * v[:, 2]], axis=1)


def main() -> None:
    hyg_path, simbad_path, sortie = sys.argv[1:4]
    with open(simbad_path, encoding='utf-8') as f:
        simbad = {int(r['id'].split()[1]): float(r['rvz_radvel']) for r in csv.DictReader(f) if r['id'].split()[1].isdigit()}
    pos, v_hyg, rhat, rv, hips, am, ci, pm = [], [], [], [], [], [], [], []
    with open(hyg_path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['id'] == '0':
                continue
            d, mag = fl(r['dist']), fl(r['mag'])
            if not (d > 0) or d >= 100000 or not (mag <= 8.5 or d <= 10):
                continue
            hip = int(r['hip']) if r['hip'] else 0
            if hip == 89825:
                continue
            c = fl(r['ci'])
            if math.isnan(c):
                c = {'O': -0.3, 'B': -0.15, 'A': 0.1, 'F': 0.45, 'G': 0.65, 'K': 1.1, 'M': 1.6, 'D': 0.0}.get((r['spect'] or '').strip().upper()[:1], 1.4 if mag > 8 else 0.6)
            v = np.array([fl(r['vx'], 0), fl(r['vy'], 0), fl(r['vz'], 0)]) * KMS
            if not np.all(np.isfinite(v)) or np.linalg.norm(v) > 500:
                v = np.zeros(3)
            p = np.array([fl(r['x']), fl(r['y']), fl(r['z'])])
            pos.append(p)
            v_hyg.append(v)
            rhat.append(p / np.linalg.norm(p))
            rv.append(fl(r['rv'], 0.0))
            pm.append((fl(r['rarad'], 0), fl(r['decrad'], 0), fl(r['pmra'], 0), fl(r['pmdec'], 0), d))
            hips.append(hip)
            am.append(fl(r['absmag'], 10.0))
            ci.append(c)
    pos, v_hyg, rhat, rv, hips = np.array(pos), np.array(v_hyg), np.array(rhat), np.array(rv), np.array(hips)
    n = len(pos)

    # La page, pour comparer.
    D = data_keys(['STARS_N', 'STARS_GEO', 'STARS_AUX', 'STARS_VEL', 'M_GAL2ECL'])
    p_page, am_page, ci_page, v_page = principal(D)
    if n != len(p_page) - 1:
        raise SystemExit(f'ÉCHEC : {n} étoiles relues dans HYG, {len(p_page) - 1} attendues (page, hors Gliese 710)')
    p_ecl = eq_to_ecl(pos) * PC_LY
    ecart = np.linalg.norm(p_ecl - p_page[:n], axis=1) / np.linalg.norm(p_ecl, axis=1)
    if ecart.max() > 5e-4:
        raise SystemExit(f'ÉCHEC : position à {ecart.max():.2e} de celle de la page (étoile {int(ecart.argmax())})')

    # Vitesse : recalculée ici à pleine précision à partir du mouvement propre (millièmes de seconde d'arc par an), de la
    # distance et de la vitesse radiale ; HYG publie la sienne arrondie (mesuré : jusqu'à 4 km/s d'arrondi).
    pm = np.array(pm)
    ra, de, pmra, pmde, dpc = pm.T
    ea = np.stack([-np.sin(ra), np.cos(ra), np.zeros(n)], axis=1)
    ed = np.stack([-np.sin(de) * np.cos(ra), -np.sin(de) * np.sin(ra), np.cos(de)], axis=1)
    v_tan = 4.74047 * dpc[:, None] * (pmra[:, None] * ea + pmde[:, None] * ed) / 1000.0
    # Vitesse radiale : HYG, sinon SIMBAD, sinon inconnue.
    sans = rv == 0.0
    trouve = np.array([s_ and h in simbad for s_, h in zip(sans, hips)])
    rv_simbad = np.array([simbad.get(int(h), 0.0) for h in hips])
    lent = np.linalg.norm(v_hyg, axis=1) == 0      # vitesse écartée par la page (absente ou > 500 km/s) : gardée nulle
    # Contrôle : la vitesse recalculée avec la vitesse radiale de HYG retombe sur la vitesse publiée par HYG, à son
    # arrondi près (médiane sous 0,05 km/s, 99,9 % sous 1,5 km/s).
    e = np.linalg.norm(v_tan + rv[:, None] * rhat - v_hyg, axis=1)[~lent]
    # Une étoile connue fait exception (HIP 17851 : la vitesse publiée par HYG, 0,24 km/s, contredit son propre
    # mouvement propre, qui donne 28 km/s) : on tolère 3 exceptions au plus.
    if np.median(e) > 0.05 or np.percentile(e, 99.9) > 1.5 or int((e > 1.5).sum()) > 3:
        raise SystemExit(f'ÉCHEC : vitesse recalculée à {np.median(e):.3f} km/s (médiane), {e.max():.2f} km/s (maximum) de celle de HYG')
    # Contrôle croisé : là où HYG et SIMBAD ont tous deux une vitesse radiale, elles s'accordent (médiane de l'écart).
    both = ~sans & np.array([h in simbad for h in hips])
    med = float(np.median(np.abs(rv[both] - rv_simbad[both])))
    if med > 3.0:      # mesuré : 1,26 km/s (HYG reprend d'anciennes mesures, souvent arrondies au km/s)
        raise SystemExit(f'ÉCHEC : HYG et SIMBAD diffèrent de {med:.2f} km/s en médiane')
    dans_simbad = np.array([h in simbad for h in hips])
    v = v_tan + np.where(dans_simbad, rv_simbad, rv)[:, None] * rhat      # SIMBAD d'abord (mesures plus récentes), sinon HYG
    v[lent] = 0
    sans_vr = (sans & ~trouve) | lent
    v_ecl = eq_to_ecl(v)
    # Gliese 710, dernière étoile de la page, gardée telle quelle.
    out = dict(pos=np.vstack([p_ecl, p_page[n:]]), vel=np.vstack([v_ecl, v_page[n:]]),
               absmag=np.concatenate([am, am_page[n:]]), ci=np.concatenate([ci, ci_page[n:]]),
               sans_vr=np.concatenate([sans_vr, [False]]), hip=np.concatenate([hips, [89825]]))
    np.savez(os.path.join(sortie, 'hyg_principal.npz'), **out)
    with open(os.path.join(sortie, 'etoiles_sans_vr.txt'), 'w', encoding='ascii', newline='\n') as f:
        f.write(f"{int(out['sans_vr'].sum())}\n")
    print(f'{n + 1} étoiles ; position : écart maximal avec la page {ecart.max():.1e} (arrondi de la page) ; '
          f'vitesse radiale : {int((~sans).sum())} dans HYG, {int(trouve.sum())} ajoutées depuis SIMBAD, '
          f'{int(out["sans_vr"].sum())} toujours inconnues ; vitesse recalculée : {np.median(e):.3f} km/s de HYG en médiane, {e.max():.2f} au pire ; accord HYG-SIMBAD : {med:.2f} km/s en médiane sur {int(both.sum())} étoiles')


if __name__ == '__main__':
    main()
