"""Essais de equilibre_depart.py : un petit film écrit au format version 2 à partir de formes dont la réponse est connue
(disque qui tourne sans changer : réussi ; disque qui se contracte : raté ; index absent : illisible)."""
import json
import os
import struct
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import equilibre_depart as ed


def ecrire_film(dossier: str, images: list[np.ndarray], dates: list[float]) -> None:
    n, total = len(images), len(images[0])
    b = b'UNIVFLM2' + struct.pack('<II', n, 1) + struct.pack('<Q', total)
    for t in dates:
        b += struct.pack('<d', t) + b'\0' * 48 + struct.pack('<d', 0.0)
    open(os.path.join(dossier, 'film_index.bin'), 'wb').write(b)
    for i, p in enumerate(images):
        p.astype('<f2').tofile(os.path.join(dossier, f'img_{i:05d}.f16'))
    json.dump({'galaxies': ['essai']}, open(os.path.join(dossier, 'film.json'), 'w'))


def disque(n: int, rng: np.random.Generator) -> np.ndarray:
    R = -3.0 * np.log(rng.uniform(size=n) * rng.uniform(size=n))
    phi = rng.uniform(0, 2 * np.pi, n)
    z = 0.3 * rng.normal(size=n)
    return np.stack([R * np.cos(phi), R * np.sin(phi), z], 1), R, phi, z


def test_disque_qui_tourne_reussit():
    rng = np.random.default_rng(1)
    p0, R, phi, z = disque(200_000, rng)
    imgs = [np.stack([R * np.cos(phi + 0.3 * k), R * np.sin(phi + 0.3 * k), z], 1) for k in range(11)]
    with tempfile.TemporaryDirectory() as d:
        ecrire_film(d, imgs, [0.01 * k for k in range(11)])
        code, rapport = ed.controler(d)
    assert code == 0, rapport


def test_disque_qui_se_contracte_rate():
    rng = np.random.default_rng(2)
    p0, R, phi, z = disque(200_000, rng)
    imgs = [p0 * (1 - 0.01 * k) for k in range(11)]      # 10 % plus petit en 100 Ma
    with tempfile.TemporaryDirectory() as d:
        ecrire_film(d, imgs, [0.01 * k for k in range(11)])
        code, rapport = ed.controler(d)
    assert code == 1
    assert 'rayon_50' in rapport['essai']['echecs'] and 'rapprochees_moins_eloignees_points' in rapport['essai']['echecs']


def test_film_absent_illisible():
    with tempfile.TemporaryDirectory() as d:
        code, rapport = ed.controler(d)
    assert code == 2 and 'erreur' in rapport
