#!/usr/bin/env python3
"""Grandes structures pour l'appli PC : Laniakea et son flot, les vides cosmiques -> structures.bin + structures_noms.tsv.

Demande de Marc (19/11/2026) : il manque le superamas Laniakea avec le Grand Attracteur et tous les vides cosmiques. Le
mesuré passe en premier ; de vraies structures 3D dans lesquelles on vole ; on généralise en s'éloignant.

Sources (toutes publiques, fichiers dans %LOCALAPPDATA%\\univers-raw) :
- Laniakea : bassins d'attraction de Dupuy et Courtois 2023 (A&A 678, A176) sur le champ de vitesses Cosmicflows-4
  (Courtois et al. 2023, A&A 670, L15), cf4grid/CF4_new_128-z008_BoA.fits. Même orientation, mêmes contrôles et même
  surface que pipeline/sources/build_laniakea.py (la page web).
- Flot : champ de vitesses Cosmicflows-4 64³ (cf4grid/CF4_new_64-z008_velocity.fits) et son champ de densité
  (CF4_new_64-z008_delta.fits). Ordre des axes établi ici sur les données : ces deux grilles sont rangées (SGX, SGY, SGZ)
  (seule orientation sur 48 où la densité est positive sur les six attracteurs publiés et sur Coma et la Vierge ; les
  grilles 128³ des bassins sont, elles, rangées (SGZ, SGY, SGX)) et les composantes (vx, vy, vz), seule disposition sur
  48 où la densité suit -div v (corrélation 0,997). Unité des vitesses :
  non écrite dans le fichier ; déduite de la relation linéaire delta = -div v / (H0 f), f = 0,3^0,55, puis comparée au
  mouvement mesuré du Groupe local (627 km/s, dipôle du fond cosmologique) : contrôle plus bas.
  Lignes de courant : départ sur une cellule sur deux de chaque bassin, intégrées dans le sens du flot (Runge-Kutta 4,
  interpolation trilinéaire) jusqu'à l'arrêt. Contrôle : toutes les lignes d'un bassin doivent finir au même puits du
  flot, et ce puits près de l'attracteur publié (grille deux fois plus grossière que celle de l'article).
- Vides du voisinage (moins de 200 Mpc/h, tout le ciel) : Malandrino et al. 2026 (A&A 705, A160), github.com/RosaMalandrino/
  LocalVoids : 100 vides de la reconstruction Manticore-Local du relevé 2M++, forme publiée (nuages de Voronoi), dont le
  Vide local. (Essai écarté le 19/11/2026 : les zones sous-denses du champ Cosmicflows-4, trop lisse à 15 Mpc/h, ne
  recouvraient les vides SDSS qu'à 36 %.)
- Vides SDSS DR7 (27 à 330 Mpc/h) : Douglass, Veyrat et BenZvi 2023 (ApJS 265, 7), VizieR J/ApJS/265/7 table2 :
  sphères de VoidFinder (cosmologie Planck 2018), dont l'union EST la forme publiée de chaque vide. Surface tirée de
  cette union (distance signée sur une grille de 2,5 Mpc/h).
- Vides lointains BOSS DR12 (z = 0,2 à 0,7) : Mao et al. 2017 (ApJ 835, 161), VizieR J/ApJ/835/161 : centre et rayon
  effectif seulement (VIDE). Montrés comme la sphère de même volume : forme généralisée, dite telle quelle.

Repère et unités de sortie : écliptique J2000, années-lumière, comme etoiles.bin et galaxies_cf4.tsv. Mpc/h -> Mpc avec
h = 0,674 (Planck 2018, cosmologie des catalogues de vides et de la page).

Usage : python structures.py <dossier univers-raw> <dossier de sortie>   (venv avec astropy, scipy, scikit-image)
"""
import math
import os
import struct
import sys

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.cosmology import Planck18
from astropy.io import fits
from scipy.ndimage import gaussian_filter, map_coordinates
from skimage.measure import marching_cubes

H = 0.674
MPC_LY = 3.2615637771674333e6
EPS = math.radians(84381.448 / 3600.0)      # obliquité J2000, comme pipeline/natif/galaxies_cf4.py
RX = np.array([[1, 0, 0], [0, math.cos(EPS), math.sin(EPS)], [0, -math.sin(EPS), math.cos(EPS)]])
COTE = 1000.0
LIMITE_VOISINAGE = 200.0        # Mpc/h : portée du catalogue des vides du voisinage (Malandrino et al. 2026, figure 1)
# Dupuy et Courtois 2023, table 1 (reconstruction « galaxies ») : étiquette -> nom, attracteur SGX, SGY, SGZ (Mpc/h), volume
ATTRACTEURS = {1: ('Laniakea', (-62, -8, 39), 1.9), 2: ('Apus', (-125, -23, -31), 9.5), 3: ('Hercule', (-39, 70, 78), 3.1),
               4: ('Lepus', (-62, -39, -109), 8.1), 5: ('Persée-Poissons', (47, -23, -31), 4.8), 6: ('Shapley', (-141, 62, -16), 7.9)}
V_GROUPE_LOCAL = 627.0          # km/s, mouvement du Groupe local dans le repère du fond cosmologique (Planck 2018 I, dipôle)
F_CROISSANCE = 0.3 ** 0.55      # taux de croissance f = Omega_m^0,55 (Omega_m = 0,3 : valeur de Cosmicflows-4) [Probable]


def sg_vers_ly(xyz):
    """Cartésien supergalactique (Mpc/h) -> écliptique J2000 (années-lumière)."""
    xyz = np.atleast_2d(np.asarray(xyz, dtype=float))
    c = SkyCoord(sgx=xyz[:, 0], sgy=xyz[:, 1], sgz=xyz[:, 2], unit=u.Mpc, frame='supergalactic', representation_type='cartesian')
    eq = c.icrs.cartesian.xyz.to_value(u.Mpc).T
    return (RX @ eq.T).T / H * MPC_LY


def eq_vers_ly(xyz):
    """Cartésien équatorial J2000 (Mpc/h) -> écliptique J2000 (années-lumière)."""
    return (RX @ np.atleast_2d(xyz).T).T / H * MPC_LY


def normales(som, tri):
    n = np.zeros_like(som)
    fn = np.cross(som[tri[:, 1]] - som[tri[:, 0]], som[tri[:, 2]] - som[tri[:, 0]])
    for k in range(3):
        np.add.at(n, tri[:, k], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-30)


# ---------------------------------------------------------------- Cosmicflows-4

def lire_cf4(raw):
    d = os.path.join(raw, 'cf4grid')
    boa = np.transpose(fits.getdata(os.path.join(d, 'CF4_new_128-z008_BoA.fits')).astype(int), (2, 1, 0))
    delta = fits.getdata(os.path.join(d, 'CF4_new_64-z008_delta.fits')).astype(float)      # (SGX, SGY, SGZ) : contrôle plus bas
    vel = fits.getdata(os.path.join(d, 'CF4_new_64-z008_velocity.fits')).astype(float)      # (vx, vy, vz) supergalactiques
    return boa, delta, vel


def controle_orientation_densite(delta):
    """La grille de densité doit être surdense sur les six attracteurs publiés, Coma et la Vierge, et c'est la seule
    orientation (sur 48) à l'être."""
    import itertools
    pts = [p for _, p, _ in ATTRACTEURS.values()] + [(-2.6, 70.0, 10.7), (-3.0, 15.0, -1.0)]      # Coma, Vierge (de mémoire, à 5 Mpc/h)
    pas = COTE / 64
    bonnes = []
    for perm in itertools.permutations(range(3)):
        for fl in itertools.product((False, True), repeat=3):
            b = np.transpose(delta, perm)
            for k in range(3):
                if fl[k]:
                    b = np.flip(b, k)
            if all(b[tuple(int(math.floor(p[k] / pas + 32)) for k in range(3))] > 0.3 for p in pts):
                bonnes.append((perm, fl))
    print('densité : orientations surdenses sur les 8 structures :', bonnes)
    if bonnes != [((0, 1, 2), (False, False, False))]:
        raise SystemExit('orientation de la densité non unique ou différente : rien écrit')


def controle_axes(delta, vel):
    pas = COTE / 64
    div = sum(np.gradient(vel[a], pas, axis=a) for a in range(3))
    c = np.corrcoef(delta.ravel(), -div.ravel())[0, 1]
    pente = np.polyfit(div.ravel(), delta.ravel(), 1)[0]
    unite = -pente * 100.0 * F_CROISSANCE      # km/s par unité du fichier (H0 = 100 h km/s/Mpc, distances en Mpc/h)
    o = np.array([vel[k][31:33, 31:33, 31:33].mean() for k in range(3)]) * unite
    lg = SkyCoord(l=276.4 * u.deg, b=29.3 * u.deg, frame='galactic').supergalactic.cartesian.xyz.value      # Planck 2018 I
    cos = float(o @ lg / np.linalg.norm(o))
    print('axes : corrélation densité / -div v %.4f ; unité déduite %.1f km/s ; vitesse au centre %.0f km/s (Groupe local %.0f), '
          'cos(direction) %.2f' % (c, unite, np.linalg.norm(o), V_GROUPE_LOCAL, cos))
    if c < 0.99 or cos < 0.8 or abs(np.linalg.norm(o) / V_GROUPE_LOCAL - 1) > 0.25:
        raise SystemExit('axes ou unité des vitesses non confirmés : rien écrit')
    return unite


def controle_bassins(boa):
    pas = COTE / 128
    for lab, (nom, p, vol) in ATTRACTEURS.items():
        ici = int(boa[tuple(int(math.floor(p[k] / pas + 64)) for k in range(3))])
        v = (boa == lab).sum() * pas ** 3 / 1e6
        print('  %-16s attracteur dans le bassin %d (attendu %d) ; volume %.2f (table %.1f)' % (nom, ici, lab, v, vol))
        if ici != lab or abs(v - vol) > 0.03 * vol + 0.05:
            raise SystemExit('bassins non confirmés : rien écrit')


def surface_laniakea(boa):
    """Même surface que build_laniakea.py : masque sur-échantillonné, lissé d'une cellule, niveau qui garde le volume."""
    pas = COTE / 128
    lan = boa == 1
    c = 64
    SUR = 2
    fin = np.repeat(np.repeat(np.repeat(np.pad(lan, 2), SUR, 0), SUR, 1), SUR, 2).astype(float)
    lisse = gaussian_filter(fin, sigma=float(SUR))
    vol_cel = lan.sum() * pas ** 3

    def surface(niveau):
        som, tr, _, _ = marching_cubes(lisse, level=niveau)
        som = (som + 0.5) / SUR - 2
        a0, a1, a2 = (som[tr[:, k]] - c for k in range(3))
        return som, tr, abs(np.einsum('ij,ij->i', a0, np.cross(a1, a2)).sum()) / 6 * pas ** 3

    bas, haut = 0.2, 0.5
    for _ in range(30):
        mil = 0.5 * (bas + haut)
        if surface(mil)[2] > vol_cel:
            bas = mil
        else:
            haut = mil
    som, tri, vs = surface(0.5 * (bas + haut))
    print('Laniakea : %d sommets, %d triangles, volume %.3f (cellules %.3f) millions (Mpc/h)^3' % (len(som), len(tri), vs / 1e6, vol_cel / 1e6))
    if abs(vs / vol_cel - 1) > 0.01:
        raise SystemExit('surface de Laniakea trop éloignée des cellules : rien écrit')
    sg = (som - c) * pas
    p = sg_vers_ly(sg)
    return p, tri.astype(np.uint32), normales(p, tri)


def lignes_de_courant(boa, vel, unite):
    """Lignes de courant du champ de vitesses, une cellule sur deux de chaque bassin publié (étiquettes 1 à 6)."""
    pas64 = COTE / 64

    def v_at(p):      # p : (n, 3) en Mpc/h -> vitesse (km/s) par interpolation trilinéaire
        idx = (p / pas64 + 32 - 0.5).T
        return np.stack([map_coordinates(vel[k], idx, order=1, mode='nearest') for k in range(3)], axis=1) * unite

    graines, bassin = [], []
    pas128 = COTE / 128
    for lab in ATTRACTEURS:
        cells = np.argwhere(boa == lab)
        cells = cells[(cells % 2 == 0).all(axis=1)]
        graines.append((cells + 0.5 - 64) * pas128)
        bassin.append(np.full(len(cells), lab))
    p = np.concatenate(graines)
    bas = np.concatenate(bassin)
    # pas d'intégration : 1,5 Mpc/h par pas pour la vitesse typique (300 km/s) ; temps fictif, seul le chemin compte
    dt = 1.5 / 300.0
    chemins = [p.copy()]
    vitesses = [np.linalg.norm(v_at(p), axis=1)]
    actif = np.ones(len(p), bool)
    for _ in range(3000):
        k1 = v_at(p)
        k2 = v_at(p + 0.5 * dt * k1)
        k3 = v_at(p + 0.5 * dt * k2)
        k4 = v_at(p + dt * k3)
        step = dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        # arrêt : flot presque nul (cœur d'un attracteur) ou sortie du cube
        actif &= (np.linalg.norm(step, axis=1) > 0.05) & (np.abs(p).max(axis=1) < COTE / 2 - pas64)
        p = np.where(actif[:, None], p + step, p)
        chemins.append(p.copy())
        vitesses.append(np.linalg.norm(v_at(p), axis=1))
        if not actif.any():
            break
    chemins = np.stack(chemins, axis=1)      # (lignes, pas, 3)
    vitesses = np.stack(vitesses, axis=1)
    # contrôle : chaque bassin finit en un seul puits, près de son attracteur publié
    puits = {}
    for lab, (nom, att, _) in ATTRACTEURS.items():
        fin = chemins[bas == lab, -1]
        med = np.median(fin, axis=0)
        etal = float(np.median(np.linalg.norm(fin - med, axis=1)))
        ecart = float(np.linalg.norm(med - np.array(att, float)))
        puits[lab] = (med, ecart)
        print('  flot de %-16s %4d lignes, puits SG %s Mpc/h, étalement %.1f, à %.0f Mpc/h de l’attracteur publié'
              % (nom, len(fin), np.round(med), etal, ecart))
        if etal > 5 or ecart > 40:
            raise SystemExit('le flot ne converge pas vers l’attracteur publié : rien écrit')
    lignes = []
    for i in range(len(chemins)):
        c = chemins[i]
        # points gardés tous les 1,5 Mpc/h de chemin (lignes lisses, taille raisonnable)
        keep = [0]
        for j in range(1, len(c)):
            if np.linalg.norm(c[j] - c[keep[-1]]) > 1.5:
                keep.append(j)
        if keep[-1] != len(c) - 1:
            keep.append(len(c) - 1)      # le point d'arrivée (le puits) est toujours gardé
        if len(keep) < 4:
            continue
        xyz = sg_vers_ly(c[keep])
        lignes.append((int(bas[i]), np.column_stack([xyz, vitesses[i][keep]]).astype(np.float32)))
    return lignes, puits


# ---------------------------------------------------------------- vides

def lire_vizier(chemin):
    lignes = [l.rstrip('\n') for l in open(chemin, encoding='utf-8', errors='replace') if l.strip() and not l.startswith('#')]
    ent = lignes[0].split('\t')
    out = []
    for l in lignes[3:]:
        c = l.split('\t')
        if len(c) == len(ent):
            out.append(dict(zip(ent, (x.strip() for x in c))))
    return out


def trous_sdss(raw):
    t = [r for r in lire_vizier(os.path.join(raw, 'vides_sdss', 'table2.tsv')) if r['Cosmo'] == 'Planck2018']
    a = np.array([[float(r['x']), float(r['y']), float(r['z']), float(r['Rad'])] for r in t])
    ids = np.array([int(r['void']) for r in t])
    print('SDSS DR7 VoidFinder (Planck 2018) : %d sphères, %d vides' % (len(a), len(np.unique(ids))))
    if len(np.unique(ids)) < 1100:
        raise SystemExit('catalogue SDSS incomplet : rien écrit')
    # Partage des distances : en deçà de LIMITE_VOISINAGE, les vides du voisinage (tout le ciel, une seule méthode) ;
    # au-delà, ceux du SDSS. Un vide SDSS est gardé si sa plus grande sphère (table1) est centrée au-delà.
    t1 = [r for r in lire_vizier(os.path.join(raw, 'vides_sdss', 'table1.tsv')) if r['Cosmo'] == 'Planck2018']
    loin = {int(r['void']) for r in t1 if float(r['s']) > LIMITE_VOISINAGE}
    garde = np.isin(ids, list(loin))
    print('  vides SDSS gardés (plus grande sphère au-delà de %.0f Mpc/h) : %d sur %d' % (LIMITE_VOISINAGE, len(loin), len(np.unique(ids))))
    return a[garde], ids[garde]


def champ_union(trous, pas):
    """Distance signée à l'union des sphères (positive dedans), sur une grille de `pas` Mpc/h (équatorial)."""
    lo = (trous[:, :3] - trous[:, 3:4]).min(axis=0) - 2 * pas
    hi = (trous[:, :3] + trous[:, 3:4]).max(axis=0) + 2 * pas
    n = np.ceil((hi - lo) / pas).astype(int) + 1
    f = np.full(n, -3.0 * pas, np.float32)
    for x, y, z, r in trous:
        a = np.maximum(np.floor((np.array([x, y, z]) - r - lo) / pas).astype(int) - 1, 0)
        b = np.minimum(np.ceil((np.array([x, y, z]) + r - lo) / pas).astype(int) + 2, n)
        gx, gy, gz = (lo[k] + pas * np.arange(a[k], b[k]) for k in range(3))
        d = r - np.sqrt((gx[:, None, None] - x) ** 2 + (gy[None, :, None] - y) ** 2 + (gz[None, None, :] - z) ** 2)
        s = f[a[0]:b[0], a[1]:b[1], a[2]:b[2]]
        np.maximum(s, d, out=s)
    return f, lo


def surface_sdss(trous, pas=2.5):
    f, lo = champ_union(trous, pas)
    som, tri, _, _ = marching_cubes(f, level=0.0)
    eq = lo + som * pas
    p = eq_vers_ly(eq)
    print('vides SDSS : surface %d sommets, %d triangles' % (len(p), len(tri)))
    return p, tri.astype(np.uint32), normales(p, tri)


def vides_proches(raw):
    """Vides du voisinage (moins de 200 Mpc/h, tout le ciel) : Malandrino et al. 2026 (A&A 705, A160), 100 vides
    trouvés par VIDE dans 50 reconstructions Manticore-Local du relevé 2M++ et gardés à 5 sigma. Forme de chaque vide :
    son « nuage de Voronoi » publié (grille 32³ du taux de recouvrement), surface au seuil 0,37 que les auteurs
    recommandent parce qu'il conserve le volume statistique du vide. Repère du catalogue : équatorial, observateur en
    (340,5 ; 340,5 ; 340,5) Mpc/h."""
    d = os.path.join(raw, 'vides_locaux', 'LocalVoids-master')
    cat = [l.rstrip('\n').split(',') for l in open(os.path.join(d, 'voids_catalog.csv'), encoding='utf-8')][1:]
    if len(cat) != 100:
        raise SystemExit('catalogue des vides locaux incomplet : rien écrit')
    obs = np.array([340.5, 340.5, 340.5])
    som, tri, nor, noms = [], [], [], []
    n0 = 0
    for i, row in enumerate(cat):
        g = np.load(os.path.join(d, 'VoronoiClouds', 'Voronoi_cloud_void_%d_N32.npy' % i), allow_pickle=False).reshape(32, 32, 32, 4)
        champ = np.pad(g[..., 3], 1)      # bord à zéro : surface fermée
        s, t, _, _ = marching_cubes(champ, level=0.37)
        s = s - 1.0
        # indices -> coordonnées : interpolation linéaire des colonnes x, y, z de la grille (son ordre d'axes est lu ici)
        xyz = np.stack([map_coordinates(g[..., k], s.T, order=1, mode='nearest') for k in range(3)], axis=1)
        eq = xyz - obs
        p = eq_vers_ly(eq)
        som.append(p)
        tri.append(t.astype(np.uint32) + n0)
        nor.append(normales(p, t))
        n0 += len(p)
        cen = np.array([float(row[0]), float(row[2]), float(row[4])]) - obs
        ra, de, dist, rayon = float(row[9]), float(row[10]), float(row[11]), float(row[6])
        if i == 10:      # article, table 1 : vide 10 = Vide local (18 h 05, -16,2°, 38,8 Mpc/h, rayon 33,9)
            if abs(ra - 271.25) > 3 or abs(de + 16.2) > 3 or abs(dist - 38.8) > 3:
                raise SystemExit('le vide 10 n’est pas le Vide local de l’article : rien écrit')
            noms.append(('Vide local', eq_vers_ly(cen)[0],
                         'vide ; rayon %.0f Mpc/h, centre à %.0f Mpc/h, commence aux portes du Groupe local (Malandrino et al. 2026, '
                         'reconstruction Manticore du relevé 2M++ ; Tully et al. 2019)' % (rayon, dist), 3))
        else:
            noms.append(('Vide %d du voisinage' % i, eq_vers_ly(cen)[0],
                         'vide ; rayon %.0f Mpc/h, centre à %.0f Mpc/h (Malandrino et al. 2026, reconstruction Manticore du relevé 2M++)' % (rayon, dist), 9))
    som, tri, nor = np.concatenate(som), np.concatenate(tri), np.concatenate(nor)
    print('vides du voisinage : 100 vides, %d sommets, %d triangles' % (len(som), len(tri)))
    return som, tri, nor, noms


def vides_boss(raw):
    t = lire_vizier(os.path.join(raw, 'vides_boss', 'table1.tsv'))
    z = np.array([float(r['z']) for r in t])
    ra = np.radians([float(r['RAJ2000']) for r in t])
    de = np.radians([float(r['DEJ2000']) for r in t])
    reff = np.array([float(r['Reff']) for r in t])
    dc = Planck18.comoving_distance(z).to_value(u.Mpc) * Planck18.h      # Mpc/h, comme Reff
    eq = np.column_stack([dc * np.cos(de) * np.cos(ra), dc * np.cos(de) * np.sin(ra), dc * np.sin(de)])
    print('BOSS DR12 : %d vides, z %.2f à %.2f, rayon effectif %.0f à %.0f Mpc/h' % (len(t), z.min(), z.max(), reff.min(), reff.max()))
    if len(t) < 1200:
        raise SystemExit('catalogue BOSS incomplet : rien écrit')
    # icosphère à 2 subdivisions (162 sommets, 320 triangles) par vide
    t0 = (1 + 5 ** 0.5) / 2
    v = np.array([[-1, t0, 0], [1, t0, 0], [-1, -t0, 0], [1, -t0, 0], [0, -1, t0], [0, 1, t0], [0, -1, -t0], [0, 1, -t0],
                  [t0, 0, -1], [t0, 0, 1], [-t0, 0, -1], [-t0, 0, 1]], float)
    f = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
         [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    v = list(v / np.linalg.norm(v, axis=1, keepdims=True))
    for _ in range(2):
        cache, nf = {}, []
        for a, b, c in f:
            def mid(i, j):
                k = (min(i, j), max(i, j))
                if k not in cache:
                    m = v[i] + v[j]
                    v.append(m / np.linalg.norm(m))
                    cache[k] = len(v) - 1
                return cache[k]
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        f = nf
    v = np.array(v)
    f = np.array(f, np.uint32)
    som, tri, nor = [], [], []
    for i in range(len(t)):
        som.append(eq_vers_ly(eq[i] + v * reff[i]))
        nor.append((RX @ v.T).T)
        tri.append(f + i * len(v))
    return np.concatenate(som), np.concatenate(tri).astype(np.uint32), np.concatenate(nor)


# ---------------------------------------------------------------- écriture

def ecrire(out, sections, lignes):
    """structures.bin : « UNIVSTR1 », nombre de sections ; puis par section : genre, sommets, indices (u32 chacun),
    sommets en float32 (x, y, z, nx, ny, nz), indices u32. Puis le flot : nombre de lignes, et par ligne bassin, points,
    puis les points en float32 (x, y, z, vitesse km/s)."""
    with open(out, 'wb') as f:
        f.write(b'UNIVSTR1')
        f.write(struct.pack('<I', len(sections)))
        for genre, p, tri, nor in sections:
            f.write(struct.pack('<III', genre, len(p), tri.size))
            f.write(np.column_stack([p, nor]).astype('<f4').tobytes())
            f.write(tri.astype('<u4').tobytes())
        f.write(struct.pack('<I', len(lignes)))
        for bas, pts in lignes:
            f.write(struct.pack('<II', bas, len(pts)))
        for _, pts in lignes:
            f.write(pts.astype('<f4').tobytes())
    print('écrit', out, os.path.getsize(out), 'octets')


def main(raw, sortie):
    boa, delta, vel = lire_cf4(raw)
    controle_bassins(boa)
    controle_orientation_densite(delta)
    unite = controle_axes(delta, vel)
    lan = surface_laniakea(boa)
    lignes, puits = lignes_de_courant(boa, vel, unite)
    trous, _ = trous_sdss(raw)
    sdss = surface_sdss(trous)
    proches = vides_proches(raw)
    boss = vides_boss(raw)
    ecrire(os.path.join(sortie, 'structures.bin'),
           [(1, *lan), (2, *proches[:3]), (3, *sdss[:3]), (4, *boss)], lignes)
    # noms : attracteurs publiés, Grand Attracteur, Vide local
    noms = []
    for lab, (nom, p, vol) in ATTRACTEURS.items():
        x = sg_vers_ly(p)[0]
        if lab == 1:
            noms.append(('Laniakea', x, 'superamas ; bassin d’attraction de la Voie lactée, %.1f millions de (Mpc/h)³ (Dupuy et Courtois 2023, '
                         'champ de vitesses Cosmicflows-4) ; nom placé sur son attracteur' % vol, 2))
        else:
            noms.append(('Bassin de ' + nom, x, 'bassin d’attraction voisin de Laniakea, %.1f millions de (Mpc/h)³ (Dupuy et Courtois 2023) ; '
                         'nom placé sur son attracteur' % vol, 4))
    # Grand Attracteur : région de l'amas de la Règle (Abell 3627), son cœur visible (Woudt et al. 2008 : cz = 4 871 km/s)
    zn = 4871.0 / 299792.458
    dn = Planck18.comoving_distance(zn).to_value(u.Mpc) * Planck18.h
    c = SkyCoord(ra='16h15m03s', dec='-60d54m26s').cartesian.xyz.value * dn
    gx = eq_vers_ly(c)[0]
    att = sg_vers_ly(ATTRACTEURS[1][1])[0]
    ecart = np.linalg.norm(gx - att) / MPC_LY * H
    print('Grand Attracteur (amas de la Règle) à %.0f Mpc/h de l’attracteur de Laniakea' % ecart)
    noms.append(('Grand Attracteur', gx, 'concentration de masse vers laquelle s’écoulent les galaxies proches ; placé sur l’amas de la Règle '
                 '(Abell 3627, cz = 4 871 km/s, Woudt et al. 2008), à %.0f Mpc/h de l’attracteur de Laniakea calculé par Dupuy et Courtois 2023' % ecart, 2))
    noms += proches[3]
    with open(os.path.join(sortie, 'structures_noms.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        for nom, x, txt, prio in noms:
            f.write('%s\t%.6g\t%.6g\t%.6g\t%s\t%d\n' % (nom, x[0], x[1], x[2], txt, prio))
    # résumé pour l'indicateur de complétude (natif/src/completude.h)
    print('RESUME lignes=%d puits_laniakea=%.0f unite=%.1f' % (len(lignes), puits[1][1], unite))


if __name__ == '__main__':
    raw = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'univers-raw')
    main(raw, sys.argv[2] if len(sys.argv) > 2 else '.')
