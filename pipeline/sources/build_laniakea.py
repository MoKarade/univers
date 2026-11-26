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
import itertools
import json
import math
import os
from pathlib import Path
import sys

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits

_HERE = Path(__file__).resolve().parent
_PIPELINE_DIR = _HERE.parent
for _d in (_PIPELINE_DIR, _HERE):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))
from _paths import APP_GEN, raw_dir  # noqa: E402

COTE = 1000.0                        # Mpc/h
N = 128
H_PAGE = 0.674
ETIQUETTE_LANIAKEA = 1
Q = 0.025                            # pas des sommets enregistrés, en Mpc
EPS = math.radians(84381.448 / 3600.0)   # obliquité J2000, comme pipeline/build_data2.py
RX = np.array([[1, 0, 0], [0, math.cos(EPS), math.sin(EPS)], [0, -math.sin(EPS), math.cos(EPS)]])
ATTRACTEURS = {1: ('Laniakea', (-62, -8, 39), 1.9), 2: ('Apus', (-125, -23, -31), 9.5), 3: ('Hercule', (-39, 70, 78), 3.1),
               4: ('Lepus', (-62, -39, -109), 8.1), 5: ('Persée-Poissons', (47, -23, -31), 4.8), 6: ('Shapley', (-141, 62, -16), 7.9)}
# Dupuy et Courtois 2023, table 1, reconstruction « galaxies » : attracteur SGX, SGY, SGZ (Mpc/h), volume (10^6 (Mpc/h)^3)


def place_attracteurs(b):
    """Nombre d'attracteurs publiés qui tombent dans le bassin de leur étiquette."""
    pas = COTE / N
    return sum(int(b[tuple(int(math.floor(p[k] / pas + N / 2)) for k in range(3))]) == lab for lab, (_, p, _) in ATTRACTEURS.items())


def orientation_unique(brut):
    """Parmi les 48 orientations du tableau, seule (SGZ, SGY, SGX) -> transposition (2, 1, 0) sans retournement
    doit placer les six attracteurs dans leur bassin."""
    bonnes = []
    for perm in itertools.permutations(range(3)):
        for fl in itertools.product((False, True), repeat=3):
            b = np.transpose(brut, perm)
            for k in range(3):
                if fl[k]:
                    b = np.flip(b, k)
            if place_attracteurs(b) == len(ATTRACTEURS):
                bonnes.append((perm, fl))
    print('orientations plaçant les 6 attracteurs :', bonnes)
    if bonnes != [((2, 1, 0), (False, False, False))]:
        raise SystemExit('orientation non unique ou différente : rien écrit')


def controle_conversion():
    """La conversion supergalactique -> page doit retrouver la direction des amas que la page place déjà (DATA.FAR)."""
    with open(APP_GEN / 'data.js', encoding='utf-8') as f:
        s = f.read()
    far, _ = json.JSONDecoder().raw_decode(s[s.index('"FAR":') + 6:])
    page = {f['n']: np.array(f['pos']) for f in far}
    # positions supergalactiques approchées, de mémoire [À vérifier] : elles ne servent qu'à ce contrôle à 4° près,
    # comparées aux positions que la page affiche déjà (DATA.FAR) ; une erreur de rotation donne plus de 90° d'écart
    for nom, sg in (('Amas de Coma', (-2.6, 70.0, 10.7)), ('Amas de Persée', (50.0, -10.0, -12.0)), ('Amas de la Vierge', (-3.0, 15.0, -1.0))):
        a = sg_vers_page(np.array([sg]))[0]
        g = page[nom]
        cos_a = max(-1.0, min(1.0, float(a @ g / np.linalg.norm(a) / np.linalg.norm(g))))
        ang = math.degrees(math.acos(cos_a))
        print('  %-18s écart de direction %.1f°' % (nom, ang))
        if ang > 4.0:
            raise SystemExit('conversion vers la page non confirmée : rien écrit')


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
    brut = fits.getdata(os.path.join(dossier, 'CF4_new_128-z008_BoA.fits')).astype(int)
    orientation_unique(brut)
    b = np.transpose(brut, (2, 1, 0))   # -> (SGX, SGY, SGZ)
    controle(b)
    controle_conversion()
    lan = b == ETIQUETTE_LANIAKEA
    c = N // 2
    if not lan[c, c, c]:
        raise SystemExit('l’observateur n’est pas dans Laniakea : rien écrit')
    # cellules de bord : dans Laniakea, avec au moins une voisine (6-connexité) hors de Laniakea
    p = np.pad(lan, 1)
    inter = p[2:, 1:-1, 1:-1] & p[:-2, 1:-1, 1:-1] & p[1:-1, 2:, 1:-1] & p[1:-1, :-2, 1:-1] & p[1:-1, 1:-1, 2:] & p[1:-1, 1:-1, :-2]
    bord = np.argwhere(lan & ~inter)
    pas = COTE / N
    # surface de la frontière (et non plus des points sur la grille : vus de loin, ils dessinaient le quadrillage des
    # cellules au lieu de la frontière). Le masque est sur-échantillonné 2 fois (copie des cellules), lissé d'une cellule
    # (gaussienne sigma = 1 cellule d'origine), puis on en tire l'isosurface dont le volume enfermé égale celui des
    # cellules de Laniakea (niveau trouvé par dichotomie). La grille ne connaît la frontière qu'à une cellule près :
    # le lissage enlève les marches de l'escalier, il n'ajoute aucun détail.
    from scipy.ndimage import gaussian_filter
    from skimage.measure import marching_cubes
    SUR = 2
    fin = np.repeat(np.repeat(np.repeat(np.pad(lan, 2), SUR, 0), SUR, 1), SUR, 2).astype(float)
    lisse = gaussian_filter(fin, sigma=float(SUR))
    vol_cel = lan.sum() * pas ** 3

    def surface(niveau):
        som, tr, _, _ = marching_cubes(lisse, level=niveau)
        som = (som + 0.5) / SUR - 2      # indices fins -> coordonnées en cellules d'origine (bord de cellule = entier)
        a0, a1, a2 = (som[tr[:, k]] - c for k in range(3))
        return som, tr, abs(np.einsum('ij,ij->i', a0, np.cross(a1, a2)).sum()) / 6 * pas ** 3

    bas, haut = 0.2, 0.5
    for _ in range(30):
        mil = 0.5 * (bas + haut)
        if surface(mil)[2] > vol_cel:
            bas = mil
        else:
            haut = mil
    sommets, tris, vol_surf = surface(0.5 * (bas + haut))
    print('surface : niveau %.3f, %d sommets, %d triangles, volume enfermé %.3f millions (Mpc/h)^3 (cellules %.3f)'
          % (0.5 * (bas + haut), len(sommets), len(tris), vol_surf / 1e6, vol_cel / 1e6))
    if abs(vol_surf / vol_cel - 1) > 0.01 or len(sommets) > 65535:
        raise SystemExit('surface trop éloignée des cellules ou trop grande : rien écrit')
    faces = sommets
    sg = (faces - c) * pas
    vol = lan.sum() * pas ** 3
    r_eq = (3 * vol / (4 * math.pi)) ** (1 / 3)
    centre_sg = (np.argwhere(lan).mean(axis=0) + 0.5 - c) * pas
    print('Laniakea : %d cellules, rayon équivalent %.0f Mpc/h, %d cellules de bord, centre SG %s Mpc/h'
          % (lan.sum(), r_eq, len(bord), np.round(centre_sg, 1)))
    pos = sg_vers_page(sg)
    if np.abs(pos).max() / Q > 32767:
        raise SystemExit('sommet hors de portée des entiers 16 bits : rien écrit')
    centre = sg_vers_page(centre_sg[None, :])[0]
    attracteur = sg_vers_page(np.array([ATTRACTEURS[1][1]], dtype=float))[0]
    payload = {'LANIAKEA': {
        # sommets en entiers 16 bits, pas de Q Mpc (0,025 Mpc, bien plus fin que la cellule de 11,6 Mpc) : poids de la page
        'pos': base64.b64encode(np.ascontiguousarray(np.round(pos / Q).astype('<i2')).tobytes()).decode(),   # Mpc comobiles / Q, écliptique J2000
        'q': Q,
        'tri': base64.b64encode(np.ascontiguousarray(tris.astype('<u2')).tobytes()).decode(),   # triangles (indices des sommets)
        'n': int(len(pos)), 'ntri': int(len(tris)),
        'centre': [round(float(x), 2) for x in centre],
        'attracteur': [round(float(x), 2) for x in attracteur],   # Dupuy et Courtois 2023, table 1 : [-62, -8, 39] Mpc/h
        'r_eq_mpc_h': round(float(r_eq), 1),
        'cellule_mpc_h': pas,
        'src': 'Dupuy et Courtois 2023 (A&A 678, A176), bassins d’attraction du champ de vitesses Cosmicflows-4',
    }}
    out = APP_GEN / 'laniakea.js'
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('Object.assign(DATA, ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ');\n')
    print('écrit', out, out.stat().st_size, 'octets')


if __name__ == '__main__':
    main(raw_dir(sys.argv[1] if len(sys.argv) > 1 else None))
