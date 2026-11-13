#!/usr/bin/env python3
"""Contrôle des tuiles de gaia_tuiles.py : chaque étoile est dans sa tuile (HEALPix recalculé depuis sa direction,
indépendamment du numéro Gaia), à 0,1 % près : le numéro Gaia vient d'une position provisoire du catalogue, quelques
étoiles au bord d'une tuile tombent dans la voisine (mesuré : 0,009 %) ; les tuiles sont rangées par éclat ; les comptes
par seuil sont justes.
Usage : python test_gaia_tuiles.py <dossier des paquets> <gaia_tuiles.idx>
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ciel_bandes import ang2pix_nest      # noqa: E402
from gaia_tuiles import EPS, ETOILE, ORDRE, ORDRE_PAQUET      # noqa: E402


def main() -> None:
    paquets, idx = sys.argv[1], sys.argv[2]
    raw = open(idx, 'rb').read()
    assert raw[:8] == b'UNIVGTU1'
    ordre, nt, ns, _ = np.frombuffer(raw[8:24], '<u4')
    seuils = np.frombuffer(raw[24:24 + 4 * ns], '<f4')
    ligne = np.dtype([('off', '<u8'), ('n', '<u4'), ('c', '<u4', (ns,))])
    tab = np.frombuffer(raw[24 + 4 * ns:], ligne)
    assert len(tab) == nt and ordre == ORDRE
    vus, hors, desordre, comptes = 0, 0, 0, 0
    for n in np.flatnonzero(tab['n']):
        p = n >> (2 * (ORDRE - ORDRE_PAQUET))
        with open(os.path.join(paquets, f'p{p:03d}.bin'), 'rb') as f:
            f.seek(int(tab['off'][n]))
            e = np.frombuffer(f.read(int(tab['n'][n]) * ETOILE.itemsize), ETOILE)
        x, y, z = e['x'].astype(float), e['y'].astype(float), e['z'].astype(float)
        ye, ze = y * math.cos(EPS) - z * math.sin(EPS), y * math.sin(EPS) + z * math.cos(EPS)      # vers l'équateur
        pix = ang2pix_nest(2 ** ORDRE, np.arccos(np.clip(ze, -1, 1)), np.arctan2(ye, x))
        hors += int((pix != n).sum())
        desordre += int((np.diff(e['g'].astype(int)) < 0).sum())
        attendu = np.searchsorted(e['g'], np.round(seuils * 1000).astype(np.uint16), side='left')
        comptes += int((attendu != tab['c'][n]).sum())
        vus += len(e)
    print(f'{vus} étoiles ; hors de leur tuile : {hors} ; ordre d\'éclat rompu : {desordre} ; comptes faux : {comptes}')
    print('PASSE' if vus and desordre == 0 and comptes == 0 and hors <= vus * 1e-3 else 'ÉCHEC')


if __name__ == '__main__':
    main()
