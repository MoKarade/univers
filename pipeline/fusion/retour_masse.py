#!/usr/bin/env python3
"""Masse rendue au gaz par une population d'étoiles qui vieillit (vents des géantes, nébuleuses planétaires, supernovae).

Sans ce retour, le gaz d'une galaxie isolée s'épuise et les naissances d'étoiles retombent (mesuré le 18/11/2026 : 0,8 M☉/an
après 1 Ga au lieu de 1,65 ± 0,19 mesurés). Conseil de docs/monter-une-simulation-pro.md : « retour de masse des populations ».

Calcul [modèle bâti sur des tables publiées] : pour une population née d'un coup,
- répartition des masses à la naissance : Kroupa 2001 (MNRAS 322, 231), de 0,1 à 100 M☉ ;
- durée de vie de chaque masse : modèles MIST v1.2, [Fe/H] = 0 (Choi et al. 2016 ; app/gen/mist_life.js, fin du modèle) ;
- masse du reste : naine blanche selon la relation masse initiale - masse finale de Cummings et al. 2018 (ApJ 866, 21)
  [coefficients de mémoire, À RELIRE] ; étoile à neutrons de 1,4 M☉ de 8 à 25 M☉ ; trou noir de 30 % de la masse
  initiale au-delà [Supposition] ;
la part rendue à l'âge t est la masse perdue par toutes les étoiles déjà mortes, divisée par la masse de départ.
Écrit resultats/retour_masse.json : âges (ans) et part rendue. Usage : python retour_masse.py
"""
import json
import os
import re

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))


def kroupa(m):
    return np.where(m < 0.5, (m / 0.5) ** -1.3, (m / 0.5) ** -2.3)


def reste(m):
    return np.where(m < 2.85, 0.080 * m + 0.489, np.where(m < 3.60, 0.187 * m + 0.184, np.where(m < 8.0, 0.107 * m + 0.471, np.where(m < 25.0, 1.4, 0.3 * m))))


def table():
    js = open(os.path.join(ICI, '..', '..', 'app', 'gen', 'mist_life.js'), encoding='utf-8').read()
    d = json.loads(js[js.index('MIST_LIFE:') + len('MIST_LIFE:'):js.rindex('}')].strip().rstrip(',').strip())
    rows = [(r[0], r[2] * 1e6) for r in d['rows'] if r[3] in ('wd', 'cc') and r[2]]
    mm, vie = np.array([r[0] for r in rows]), np.array([r[1] for r in rows])      # masse (M☉), durée de vie (ans)
    m = np.exp(np.linspace(np.log(0.1), np.log(100.0), 20000)); dm = np.gradient(m)
    phi = kroupa(m); total = float((m * phi * dm).sum())
    vie_m = np.exp(np.interp(np.log(m), np.log(mm), np.log(vie), left=np.inf, right=np.log(vie[-1])))
    vie_m[m < mm[0]] = np.inf      # trop légères pour être mortes
    perdu = np.clip(m - np.minimum(reste(m), m), 0.0, None) * phi * dm
    ages = np.exp(np.linspace(np.log(3e6), np.log(1.4e10), 200))
    rendu = np.array([float(perdu[vie_m <= a].sum()) / total for a in ages])
    return ages, rendu


def main():
    ages, rendu = table()
    out = dict(description=__doc__.split('\n')[0], ages_ans=[float(a) for a in ages], part_rendue=[round(float(r), 5) for r in rendu],
               statut='calculé ici à partir de tables publiées ; relation masse initiale - masse finale à relire ; restes des étoiles de plus de 25 M☉ supposés')
    json.dump(out, open(os.path.join(ICI, 'resultats', 'retour_masse.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    for a in (1e7, 1e8, 1e9, 5e9, 1e10, 1.3e10): print(f'âge {a:.0e} ans : part rendue {np.interp(a, ages, rendu):.3f}')


if __name__ == '__main__':
    main()
