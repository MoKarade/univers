#!/usr/bin/env python3
"""Contrôle : les galaxies du film partent-elles à l'équilibre ?

Marc, 18/11/2026 : « les étoiles des nuages alentours sont toutes attirées, pas normal ». Mesuré dans le film 2 : en
20 Ma, une étoile sur cinq change de rayon de plus de 20 % et la Voie lactée se contracte (rayon médian 4,75 -> 4,35 kpc
en 50 Ma) : le départ n'était pas à l'équilibre. À l'équilibre, les étoiles bougent (orbites allongées, barre, bulbe),
mais la RÉPARTITION ne bouge pas. Critères, fixés avec le fil du grand calcul, sur les 100 premiers Ma, pour chaque
galaxie et à chaque image :
  1. les rayons qui contiennent 10, 25, 50, 75 et 90 % des étoiles restent à 2 % de leur valeur de départ (3 % pour 10
     et 90 %) ;
  2. autant d'étoiles se rapprochent du centre qu'il s'en éloignent, à 2 points près ;
  3. l'épaisseur médiane (|z| sur le plan du disque de départ, étoiles sous le rayon à 90 %) reste à 5 % près ;
  4. la force de la barre (|<exp(2iφ)>| des étoiles sous le rayon à 50 %) reste à 0,03 près.

Lit le film version 2 (natif/physique/film_v2.h : film_index.bin « UNIVFLM2 », img_NNNNN.f16, positions relatives au
centre de chaque galaxie, film.json pour les noms). Usage :
  python equilibre_depart.py <dossier du film> [--duree-ma 100] [--json sortie.json]
Code de sortie : 0 réussi, 1 un critère au moins raté, 2 film illisible ou trop court.
"""
import argparse
import json
import os
import struct
import sys

import numpy as np

FRACTIONS = (10, 25, 50, 75, 90)
TOL_RAYON = {10: 0.03, 25: 0.02, 50: 0.02, 75: 0.02, 90: 0.03}
TOL_EQUILIBRE_POINTS = 2.0
TOL_EPAISSEUR = 0.05
TOL_BARRE = 0.03


def lire_index(dossier: str):
    """Nombre d'images, étoiles par galaxie, dates (Ga). None si l'index n'est pas un film version 2."""
    try:
        b = open(os.path.join(dossier, 'film_index.bin'), 'rb').read()
    except OSError:
        return None
    if len(b) < 16 or b[:8] != b'UNIVFLM2':
        return None
    n, g = struct.unpack_from('<II', b, 8)
    cnt = [int(x) for x in np.frombuffer(b, '<u8', g, 16)]
    tete, par_image = 16 + 8 * g, 8 + 48 * g + 8
    if len(b) < tete + par_image * n:
        return None
    dates = [struct.unpack_from('<d', b, tete + par_image * i)[0] for i in range(n)]
    return n, cnt, dates


def lire_image(dossier: str, i: int, total: int) -> np.ndarray | None:
    chemin = os.path.join(dossier, f'img_{i:05d}.f16')
    if not os.path.exists(chemin) or os.path.getsize(chemin) != total * 6:
        return None
    return np.fromfile(chemin, '<f2').astype(np.float32).reshape(-1, 3)


def mesures(p: np.ndarray, normale: np.ndarray, r_ref: dict) -> dict:
    """Rayons à 10..90 %, épaisseur médiane et force de la barre d'une galaxie (positions relatives à son centre)."""
    r = np.linalg.norm(p, axis=1)
    z = p @ normale
    plan = p - np.outer(z, normale)
    e1 = plan[np.argmax(np.linalg.norm(plan, axis=1))]
    e1 = e1 / np.linalg.norm(e1)
    e2 = np.cross(normale, e1)
    phi = np.arctan2(plan @ e2, plan @ e1)
    dedans = r < r_ref[50]
    return dict(rayons={f: float(np.percentile(r, f)) for f in FRACTIONS},
                epaisseur=float(np.median(np.abs(z[r < r_ref[90]]))),
                barre=float(abs(np.exp(2j * phi[dedans]).mean())) if dedans.any() else 0.0)


def normale_disque(p: np.ndarray, r90: float) -> np.ndarray:
    """Normale du plan du disque : direction de moindre dispersion des étoiles sous le rayon à 90 %."""
    m = p[np.linalg.norm(p, axis=1) < r90]
    _, v = np.linalg.eigh(np.cov(m.T.astype(np.float64)))
    return v[:, 0]


def controler(dossier: str, duree_ma: float = 100.0) -> tuple[int, dict]:
    idx = lire_index(dossier)
    if idx is None:
        return 2, {'erreur': 'film_index.bin absent ou pas au format UNIVFLM2'}
    n, cnt, dates = idx
    try:
        noms = json.load(open(os.path.join(dossier, 'film.json'), encoding='utf-8'))['galaxies']
    except (OSError, ValueError, KeyError):
        noms = [f'galaxie_{k}' for k in range(len(cnt))]
    t0 = dates[0]
    images = [i for i in range(n) if dates[i] - t0 <= duree_ma / 1000 + 1e-9]
    if len(images) < 2 or dates[images[-1]] - t0 < 0.9 * duree_ma / 1000:
        return 2, {'erreur': f'film trop court : {1000 * (dates[-1] - t0):.0f} Ma pour {duree_ma:.0f} Ma demandés'}
    deb = np.concatenate([[0], np.cumsum(cnt)]).astype(int)
    a0 = lire_image(dossier, images[0], sum(cnt))
    if a0 is None:
        return 2, {'erreur': 'image de départ absente'}
    depart, normales, r0 = {}, {}, {}
    for k in range(len(cnt)):
        p = a0[deb[k]:deb[k + 1]]
        r0[k] = np.linalg.norm(p, axis=1)
        r_ref = {f: float(np.percentile(r0[k], f)) for f in FRACTIONS}
        normales[k] = normale_disque(p, r_ref[90])
        depart[k] = mesures(p, normales[k], r_ref)
    rapport = {noms[k]: dict(depart=depart[k], pire={}, reussi=True, echecs=[]) for k in range(len(cnt))}
    for i in images[1:]:
        a = lire_image(dossier, i, sum(cnt))
        if a is None:
            return 2, {'erreur': f'image {i} absente'}
        t_ma = 1000 * (dates[i] - t0)
        for k in range(len(cnt)):
            p = a[deb[k]:deb[k + 1]]
            m = mesures(p, normales[k], depart[k]['rayons'])
            r = np.linalg.norm(p, axis=1)
            ecarts = {f'rayon_{f}': (abs(m['rayons'][f] / depart[k]['rayons'][f] - 1), TOL_RAYON[f]) for f in FRACTIONS}
            ecarts['rapprochees_moins_eloignees_points'] = (abs(100 * (np.mean(r < r0[k]) - np.mean(r > r0[k]))), TOL_EQUILIBRE_POINTS)
            ecarts['epaisseur'] = (abs(m['epaisseur'] / max(depart[k]['epaisseur'], 1e-9) - 1), TOL_EPAISSEUR)
            ecarts['barre'] = (abs(m['barre'] - depart[k]['barre']), TOL_BARRE)
            rk = rapport[noms[k]]
            for nom, (v, tol) in ecarts.items():
                if v > rk['pire'].get(nom, (-1,))[0]:
                    rk['pire'][nom] = (float(v), tol, round(t_ma, 1))
                if v > tol and nom not in rk['echecs']:
                    rk['echecs'].append(nom)
                    rk['reussi'] = False
    code = 0 if all(v['reussi'] for v in rapport.values()) else 1
    return code, rapport


def afficher(rapport: dict) -> None:
    for nom, v in rapport.items():
        print(f"\n{nom} : {'RÉUSSI' if v['reussi'] else 'RATÉ'}")
        for crit, (ecart, tol, t) in v['pire'].items():
            unite = ' points' if crit.endswith('points') else ('' if crit == 'barre' else ' (fraction)')
            print(f"  {crit:38s} pire écart {ecart:8.4f}{unite}  tolérance {tol}  à {t:6.1f} Ma  {'ok' if ecart <= tol else 'RATÉ'}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dossier')
    ap.add_argument('--duree-ma', type=float, default=100.0)
    ap.add_argument('--json')
    a = ap.parse_args()
    code, rapport = controler(a.dossier, a.duree_ma)
    if 'erreur' in rapport:
        print('Illisible :', rapport['erreur'])
    else:
        afficher(rapport)
        print('\nRésultat :', 'réussi' if code == 0 else 'raté')
    if a.json:
        json.dump(dict(code=code, rapport=rapport), open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return code


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
