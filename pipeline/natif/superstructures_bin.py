#!/usr/bin/env python3
"""Superstructures et bord de l'univers observable pour l'appli PC -> superstructures.bin + superstructures_noms.tsv.

Demande de Marc (20/11/2026) : « je ne vois ni Laniakea, ni les superstructures, ni l'univers observable ».
Entrée : superstructures.tsv écrit par pipeline/natif/superstructures.py (catalogues et articles cités ligne par ligne).

Couches écrites (même format que structures.bin, pipeline/natif/structures.py, lu par natif/src/structures.h) :
  genre 5 : superamas du catalogue SDSS DR7 de Liivamägi, Tempel et Saar 2012 (A&A 539, A80 ; VizieR J/A+A/539/A80),
            découpages « adaptatifs » des galaxies principales (mainadap) et des galaxies rouges lumineuses (lrgadap) :
            centre de masse MESURÉ ; forme montrée = sphère du diamètre publié (forme généralisée, dite telle quelle).
  genre 6 : superstructures nommées des articles (Sloan Great Wall, Saraswati, BOSS Great Wall, Mur du pôle Sud, Vela,
            Horologium-Reticulum, Coma, Hercule, Persée-Poissons, Grand Mur CfA2) : amas membres publiés quand l'article
            les donne (une bulle de 6 Mpc par amas), sinon sphère de la taille publiée.
  genre 7 : bord de l'univers observable (horizon des particules) et genre 8 : surface où le fond diffus cosmologique a
            été émis (z = 1089,9), sphères CALCULÉES avec la cosmologie Planck 2018 (astropy Planck18, rayonnement compris).
Repère : écliptique J2000, années-lumière, centre = Soleil ; distances comobiles avec h = 0,674 (comme structures.py et
la table des galaxies de l'appli). Liivamägi et al. donnent leurs distances en Mpc/h : ramenées en Mpc avec h = 0,674.

Usage : python superstructures_bin.py <superstructures.tsv> <dossier de sortie>   (venv avec astropy)
"""
import csv
import math
import os
import struct
import sys

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.cosmology import Planck18

H = 0.674
MPC_LY = 3.2615637771674333e6
EPS = math.radians(84381.448 / 3600.0)
RX = np.array([[1, 0, 0], [0, math.cos(EPS), math.sin(EPS)], [0, -math.sin(EPS), math.cos(EPS)]])
H_SCRIPT_SOURCE = 0.746      # superstructures.py a ramené les Mpc/h en Mpc avec H0 = 74,6 : on revient aux Mpc/h
BULLE_MEMBRE_MPC = 6.0       # rayon d'une bulle par amas membre (ordre de grandeur d'un amas riche et de son voisinage) [supposé]

NOMS = {
    'Sloan Great Wall': ('Grand Mur de Sloan', 'Gott et al. 2005 (ApJ 624, 463) ; membres : Einasto et al. 2011'),
    'Saraswati Supercluster': ('Superamas Saraswati', 'Bagchi et al. 2017 (ApJ 844, 25), 43 amas'),
    'BOSS Great Wall': ('Grand Mur BOSS', 'Lietzen et al. 2016 (A&A 588, L4)'),
    'South Pole Wall': ('Mur du pôle Sud', 'Pomarède et al. 2020 (ApJ 897, 133)'),
    'Vela Supercluster': ('Superamas de Vela', 'Kraan-Korteweg et al. 2017 (MNRAS 466, L29)'),
    'Horologium-Reticulum Supercluster': ('Superamas Horloge-Réticule', 'catalogue cité dans superstructures.tsv'),
    'Coma Supercluster': ('Superamas de Coma', 'Gregory et Thompson 1978 ; amas Coma (A1656) et A1367'),
    'Hercules Supercluster': ('Superamas d’Hercule', 'catalogue cité dans superstructures.tsv'),
    'Perseus-Pisces Supercluster': ('Superamas de Persée-Poissons', 'Haynes et Giovanelli 1986'),
    'CfA2 Great Wall': ('Grand Mur CfA2', 'Geller et Huchra 1989 (Science 246, 897)'),
}


def sg_mpch_vers_ly(xyz_mpch):
    xyz = np.atleast_2d(np.asarray(xyz_mpch, dtype=float))
    c = SkyCoord(sgx=xyz[:, 0], sgy=xyz[:, 1], sgz=xyz[:, 2], unit=u.Mpc, frame='supergalactic', representation_type='cartesian')
    eq = c.icrs.cartesian.xyz.to_value(u.Mpc).T
    return (RX @ eq.T).T / H * MPC_LY


def icosphere(niveau):
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    v = [np.array(p, float) / np.linalg.norm(p) for p in v]
    for _ in range(niveau):
        cache, nf = {}, []

        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                m = v[a] + v[b]
                v.append(m / np.linalg.norm(m))
                cache[k] = len(v) - 1
            return cache[k]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    return np.array(v), np.array(f, dtype=np.uint32)


def spheres(centres, rayons, niveau):
    s, t = icosphere(niveau)
    P, N, T = [], [], []
    for k, (c, r) in enumerate(zip(centres, rayons)):
        P.append(c + s * r)
        N.append(s)
        T.append(t + k * len(s))
    return np.concatenate(P), np.concatenate(T), np.concatenate(N)


def ecrire(out, sections):
    with open(out, 'wb') as f:
        f.write(b'UNIVSTR1' + struct.pack('<I', len(sections)))
        for genre, p, tri, nor in sections:
            f.write(struct.pack('<III', genre, len(p), tri.size))
            f.write(np.column_stack([p, nor]).astype('<f4').tobytes())
            f.write(tri.astype('<u4').tobytes())
        f.write(struct.pack('<I', 0))      # pas de lignes de flot ici
    print('écrit', out, os.path.getsize(out), 'octets')


def main(tsv, sortie):
    lignes = list(csv.DictReader(open(tsv, encoding='utf-8'), delimiter='\t'))
    # --- genre 5 : catalogue de Liivamägi et al. 2012 (découpages adaptatifs)
    cat = [r for r in lignes if r['catalogue'] in ('Liivamagi2012/mainadap', 'Liivamagi2012/lrgadap') and r['sgx_mpc'] and r['taille_mpc']]
    xyz = np.array([[float(r['sgx_mpc']), float(r['sgy_mpc']), float(r['sgz_mpc'])] for r in cat]) * H_SCRIPT_SOURCE
    c5 = sg_mpch_vers_ly(xyz)
    r5 = np.array([float(r['taille_mpc']) * H_SCRIPT_SOURCE / H / 2 * MPC_LY for r in cat])
    sec5 = spheres(c5, r5, 1)
    print(f'superamas du catalogue : {len(cat)} ; rayon médian {np.median(r5) / MPC_LY:.1f} Mpc')
    # --- genre 6 : structures nommées
    noms, c6, r6 = [], [], []
    for r in lignes:
        if r['catalogue'] != 'nommee' or r['nom'] not in NOMS or not r['sgx_mpc']:
            continue
        fr, ref = NOMS[r['nom']]
        centre = sg_mpch_vers_ly([float(r['sgx_mpc']) * H_SCRIPT_SOURCE, float(r['sgy_mpc']) * H_SCRIPT_SOURCE, float(r['sgz_mpc']) * H_SCRIPT_SOURCE])[0]
        membres = [m for m in r['membres_sg'].split(';') if m.count(',') == 2 and not m.startswith('pic')]
        if membres:
            for m in membres:
                c6.append(sg_mpch_vers_ly([float(x) * H_SCRIPT_SOURCE for x in m.split(',')])[0])
                r6.append(BULLE_MEMBRE_MPC * MPC_LY)
            forme = f'{len(membres)} amas membres publiés, une bulle chacun'
        else:
            taille = float(r['taille_mpc']) * H_SCRIPT_SOURCE / H if r['taille_mpc'] else 30.0
            c6.append(centre)
            r6.append(taille / 2 * MPC_LY)
            forme = 'sphère de la taille publiée (forme généralisée)'
        d = np.linalg.norm(centre) / 1e9
        noms.append((fr, centre, f'superstructure ; {forme} ; taille publiée : {r["taille_publiee"] or "non chiffrée"} ; '
                     f'{d:.2f} milliards d’années-lumière ; source : {ref} ; {r["statut"]}', 3))
    sec6 = spheres(np.array(c6), np.array(r6), 2)
    # --- genres 7 et 8 : univers observable (calculé, Planck 2018)
    # horizon des particules : (c/H0) ∫ dz / E(z) de 0 à l'infini, en x = ln(1 + z) (dz = (1 + z) dx), rayonnement compris
    x = np.linspace(0.0, 40.0, 400001)
    zz = np.expm1(x)
    f = (1.0 + zz) * Planck18.inv_efunc(zz)
    horizon = float(np.sum(0.5 * (f[1:] + f[:-1]) * np.diff(x))) * Planck18.hubble_distance.to_value(u.Mpc) * MPC_LY
    lss = Planck18.comoving_distance(1089.9).to_value(u.Mpc) * MPC_LY
    sec7 = spheres(np.zeros((1, 3)), np.array([horizon]), 5)
    sec8 = spheres(np.zeros((1, 3)), np.array([lss]), 5)
    print(f'horizon des particules {horizon / 1e9:.2f} milliards d’al ; fond diffus émis à {lss / 1e9:.2f} milliards d’al (comobile)')
    noms.append(('Univers observable', np.array([0.0, 0.0, 0.0]),
                 f'bord de l’univers observable (horizon des particules) : {horizon / 1e9:.1f} milliards d’années-lumière aujourd’hui, '
                 f'distance comobile calculée avec la cosmologie Planck 2018 (Planck Collaboration 2020, A&A 641, A6) ; la lumière du fond '
                 f'diffus cosmologique est partie de {lss / 1e9:.1f} milliards d’années-lumière (z = 1 089,9) ; calculé', 1))
    ecrire(os.path.join(sortie, 'superstructures.bin'), [(5, *sec5), (6, *sec6), (7, *sec7), (8, *sec8)])
    with open(os.path.join(sortie, 'superstructures_noms.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        for nom, x, txt, prio in noms:
            f.write('%s\t%.6g\t%.6g\t%.6g\t%s\t%d\n' % (nom, x[0], x[1], x[2], txt, prio))
    print('noms :', len(noms))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
