#!/usr/bin/env python3
"""Frontière de Laniakea (bassin d'attraction de la Voie lactée) -> app/gen/laniakea.js (clé DATA.LANIAKEA).

Source : Dupuy et Courtois 2023, A&A 678, A176 (« Dynamic cosmography of the local Universe: Laniakea and five more
watershed superclusters »), grille des bassins d'attraction calculée sur le champ de vitesses Cosmicflows-4
(Courtois et al. 2023, A&A 670, L15). Fichier CF4_new_128-z008_BoA.fits de https://projets.ip2i.in2p3.fr/cosmicflows/
(archive CF4_new_128-z008_watersheds-fits.zip). « Si vous utilisez ces données, citez l'article » (page du projet).

Géométrie, d'après la page du projet et l'article : cube de 1000 Mpc/h de côté, 128³ cellules, observateur au centre,
axes supergalactiques. L'ordre des axes du tableau n'est pas écrit sans ambiguïté : il est établi ici sur les données.
Le tableau est rangé (SGZ, SGY, SGX) : c'est la seule orientation sur 48 où les six attracteurs publiés (table 1 de
l'article : Laniakea [-62, -8, 39], Apus, Hercule, Lepus, Persée-Poissons, Shapley, en Mpc/h) tombent chacun dans le
bassin de son étiquette, et les volumes des étiquettes 1 à 6 égalent ceux de la table (1,9 ; 9,5 ; 3,1 ; 8,1 ; 4,8 ;
7,9 millions de (Mpc/h)³). Étiquette 1 = Laniakea (page du projet : « voxels filled with 1 are part of Laniakea »).

Unités : les distances en Mpc/h sont converties avec h = 0,674, le H0 de la page (Planck 2018), pour que la frontière
tombe là où la page place les galaxies d'après leur décalage vers le rouge. Avec le H0 de Cosmicflows-4 (74,6),
tout serait 10 % plus près : écart dit dans la fiche.

Usage : python pipeline/sources/build_laniakea.py <dossier_raw>   (venv avec astropy)
"""
import base64
import json
import math
import os
import sys

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits

COTE = 1000.0                        # Mpc/h
N = 128
H_PAGE = 0.674
ETIQUETTE_LANIAKEA = 1
EPS = math.radians(84381.448 / 3600.0)   # obliquité J2000, comme pipeline/build_data2.py
RX = np.array([[1, 0, 0], [0, math.cos(EPS), math.sin(EPS)], [0, -math.sin(EPS), math.cos(EPS)]])
ATTRACTEURS = {1: ('Laniakea', (-62, -8, 39), 1.9), 2: ('Apus', (-125, -23, -31), 9.5), 3: ('Hercule', (-39, 70, 78), 3.1),
               4: ('Lepus', (-62, -39, -109), 8.1), 5: ('Persée-Poissons', (47, -23, -31), 4.8), 6: ('Shapley', (-141, 62, -16), 7.9)}
# Dupuy et Courtois 2023, table 1, reconstruction « galaxies » : attracteur SGX, SGY, SGZ (Mpc/h), volume (10^6 (Mpc/h)^3)


def controle(b):
    """Chaque attracteur publié doit tomber dans son bassin, et chaque volume doit égaler la table à 3 % près."""
    pas = COTE / N
    for lab, (nom, p, vol) in ATTRACTEURS.items():
        ici = int(b[tuple(int(math.floor(p[k] / pas + N / 2)) for k in range(3))])
        v = (b == lab).sum() * pas ** 3 / 1e6
        print('  %-16s attracteur dans le bassin %d (attendu %d) ; volume %.2f (table %.1f)' % (nom, ici, lab, v, vol))
        if ici != lab or abs(v - vol) > 0.03 * vol + 0.05:
            raise SystemExit('orientation ou étiquettes non confirmées : rien écrit')


def sg_vers_page(xyz_mpc_h):
    """Cartésien supergalactique (Mpc/h) -> écliptique J2000 de la page (Mpc, h de la page)."""
    c = SkyCoord(sgx=xyz_mpc_h[:, 0], sgy=xyz_mpc_h[:, 1], sgz=xyz_mpc_h[:, 2], unit=u.Mpc,
                 frame='supergalactic', representation_type='cartesian')
    eq = c.icrs.cartesian.xyz.to_value(u.Mpc).T
    return (RX @ eq.T).T / H_PAGE


def main(raw):
    dossier = os.path.join(raw, 'cf4grid')
    b = np.transpose(fits.getdata(os.path.join(dossier, 'CF4_new_128-z008_BoA.fits')).astype(int), (2, 1, 0))   # -> (SGX, SGY, SGZ)
    controle(b)
    lan = b == ETIQUETTE_LANIAKEA
    c = N // 2
    if not lan[c, c, c]:
        raise SystemExit('l’observateur n’est pas dans Laniakea : rien écrit')
    # cellules de bord : dans Laniakea, avec au moins une voisine (6-connexité) hors de Laniakea
    p = np.pad(lan, 1)
    inter = p[2:, 1:-1, 1:-1] & p[:-2, 1:-1, 1:-1] & p[1:-1, 2:, 1:-1] & p[1:-1, :-2, 1:-1] & p[1:-1, 1:-1, 2:] & p[1:-1, 1:-1, :-2]
    bord = np.argwhere(lan & ~inter)
    pas = COTE / N
    # points de la frontière : centre de chaque face entre une cellule de Laniakea et une cellule voisine hors de Laniakea
    faces = []
    for k in range(3):
        for sgn in (-1, 1):
            vois = np.roll(lan, -sgn, axis=k)
            if sgn > 0:
                vois[(slice(None),) * k + (-1,)] = False
            else:
                vois[(slice(None),) * k + (0,)] = False
            f = np.argwhere(lan & ~vois).astype(float) + 0.5
            f[:, k] += 0.5 * sgn
            faces.append(f)
    faces = np.concatenate(faces)
    sg = (faces - c) * pas
    vol = lan.sum() * pas ** 3
    r_eq = (3 * vol / (4 * math.pi)) ** (1 / 3)
    centre_sg = (np.argwhere(lan).mean(axis=0) + 0.5 - c) * pas
    print('Laniakea : %d cellules, rayon équivalent %.0f Mpc/h, %d cellules de bord, %d faces, centre SG %s Mpc/h'
          % (lan.sum(), r_eq, len(bord), len(faces), np.round(centre_sg, 1)))
    pos = sg_vers_page(sg).astype('<f4')
    centre = sg_vers_page(centre_sg[None, :])[0]
    payload = {'LANIAKEA': {
        'pos': base64.b64encode(np.ascontiguousarray(pos).tobytes()).decode(),   # Mpc comobiles, écliptique J2000
        'n': int(len(pos)),
        'centre': [round(float(x), 2) for x in centre],
        'r_eq_mpc_h': round(float(r_eq), 1),
        'cellule_mpc_h': pas,
        'src': 'Dupuy et Courtois 2023 (A&A 678, A176), bassins d’attraction du champ de vitesses Cosmicflows-4',
    }}
    out = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'gen', 'laniakea.js')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('Object.assign(DATA, ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ');\n')
    print('écrit', os.path.normpath(out), os.path.getsize(out), 'octets')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'univers-raw'))
