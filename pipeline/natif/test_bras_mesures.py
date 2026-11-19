"""Essais de bras_mesures.py (python -m pytest pipeline/natif/test_bras_mesures.py). Aucune donnée inventée : des formes
géométriques dont la réponse est connue d'avance."""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bras_mesures as bm


def test_disque_lisse_presque_sans_part_hors_anneaux():
    rng = np.random.default_rng(1)
    n = 400_000
    R = -3.0 * np.log(rng.uniform(size=n) * rng.uniform(size=n))
    phi = rng.uniform(-math.pi, math.pi, n)
    assert bm.part_hors_anneaux(R, phi, 20.0) < 0.05      # bruit de comptage seulement


def test_deux_bras_donnent_une_part_nette():
    rng = np.random.default_rng(2)
    n = 400_000
    R = -3.0 * np.log(rng.uniform(size=n) * rng.uniform(size=n))
    phi = rng.uniform(-math.pi, math.pi, n)
    bras = rng.uniform(size=n) < 0.3      # 30 % des points sur deux bras logarithmiques
    phi[bras] = (np.pi * rng.integers(0, 2, bras.sum()) - np.log(np.maximum(R[bras], 0.3)) / math.tan(math.radians(15))
                 + 0.1 * rng.normal(size=bras.sum()) + math.pi) % (2 * math.pi) - math.pi
    part = bm.part_hors_anneaux(R, phi, 20.0)
    assert 0.15 < part < 0.35


def test_combler_satellite_sans_trou_ni_bosse():
    img = np.ones((200, 200))
    ra0, dec0, champ = 10.6847, 41.269, 3.4
    ra, dec, r = bm.SATELLITES['andromede'][1]
    x = (ra - ra0) * math.cos(math.radians(dec0)) / champ * 200
    y = (dec - dec0) / champ * 200
    lig, col = int(round(199 / 2 - y)), int(round(199 / 2 - x))
    img[lig - 2:lig + 3, col - 2:col + 3] = 50.0      # la satellite, très brillante
    out = bm.combler_satellites(img, 'andromede', ra0, dec0, champ)
    assert np.allclose(out, 1.0)
    assert img[lig, col] == 50.0      # l'original n'est pas touché


def test_ordre_suit_la_taille_du_pixel():
    assert bm.ordre_pour(3.4, 1500) == 6      # grille de 8,2″ : l'ordre 5 (12,9″) serait plus gros, l'ordre 6 (6,4″) non
    assert bm.ordre_pour(1.3, 1500) == 6
    assert bm.ordre_pour(18.0, 1500) == 4


def test_tirage_suit_la_lumiere():
    rng = np.random.default_rng(3)
    c = np.zeros((10, 10)); c[2, 7] = 1.0
    lf, cf, de = bm.tirer({'w3': c}, 1000, rng)
    assert np.all((lf >= 0.2) & (lf < 0.3) & (cf >= 0.7) & (cf < 0.8))
    assert set(de) == {'w3'}


def test_temperature_des_jeunes():
    rng = np.random.default_rng(4)
    t, hii = bm.temperature(np.array(['fuv'] * 1000 + ['w3'] * 3000), rng)
    assert np.all(t[:1000] >= 10000) and not hii[:1000].any()
    assert 0.25 < hii[1000:].mean() < 0.42 and np.all(t[1000:][hii[1000:]] == 2400.0)
