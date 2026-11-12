#!/usr/bin/env python3
"""Contrôles de gaia.bin et de voie_lactee.bin (PC seulement : les fichiers ne sont pas dans le dépôt).

1. Format : en-tête, feuilles contiguës qui couvrent toutes les étoiles, magnitudes croissantes dans chaque feuille,
   chaque étoile dans la boîte de sa feuille.
2. Aller-retour : 2 000 étoiles tirées au hasard dans les fichiers téléchargés sont retrouvées dans gaia.bin (même
   source_id impossible : on compare position et magnitude recalculées) à 1e-6 près en relatif.
3. Étoiles connues : Étoile de Barnard et Proxima du Centaure à la distance tirée de leur parallaxe Gaia DR3
   (lue dans les fichiers téléchargés, pas recopiée).
4. Voie lactée : en-tête lisible, poussière au Soleil entre 0,1 et 10 mag/kpc, aucune valeur négative ou non finie.

Usage : python test_gaia.py <dossier des parts> <gaia.bin> [voie_lactee.bin] [gaia_agrege.bin]
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')      # accents lisibles dans la console Windows
import glob, math, os, sys
import numpy as np
from astropy.io import fits

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gaia_convertir as gc

ECHECS = []


def verifie(ok, quoi):
    print(('PASSE  ' if ok else 'ÉCHEC  ') + quoi)
    if not ok: ECHECS.append(quoi)


def lire(gaia_bin):
    head = np.fromfile(gaia_bin, np.uint8, 4096)
    verifie(bytes(head[:8]) == b'UNIVGAI1', 'signature UNIVGAI1')
    n = int(head[8:16].view('<u8')[0]); nf = int(head[16:20].view('<u4')[0])
    fe = np.memmap(gaia_bin, np.dtype([('min', '<f4', 3), ('n', '<u4'), ('max', '<f4', 3), ('r0', '<u4'), ('premier', '<u8'), ('r1', '<u8')]), 'r', 4096, (nf,))
    debut = 4096 + (nf * 48 + 63) // 64 * 64
    rec = np.memmap(gaia_bin, np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('m', '<f2'), ('c', 'u1'), ('f', 'u1')]), 'r', debut, (n,))
    return n, fe, rec


def format_(n, fe, rec):
    premier, compte = fe['premier'].astype(np.int64), fe['n'].astype(np.int64)
    verifie(premier[0] == 0 and np.all(premier[1:] == premier[:-1] + compte[:-1]) and premier[-1] + compte[-1] == n,
            f'{len(fe)} feuilles contiguës couvrant les {n} étoiles')
    verifie(int(compte.max()) <= gc.FEUILLE, f'feuilles d’au plus {gc.FEUILLE} étoiles (max {int(compte.max())})')
    mauvais_ordre, hors_boite = 0, 0
    for i in np.random.default_rng(1).choice(len(fe), min(400, len(fe)), replace=False):
        r = np.array(rec[premier[i]:premier[i] + compte[i]])
        m = r['m'].astype(np.float32)
        mauvais_ordre += int(np.sum(np.diff(m) < 0))
        p = np.stack([r['x'], r['y'], r['z']], 1)
        hors_boite += int(np.sum((p < fe['min'][i]) | (p > fe['max'][i])))
    verifie(mauvais_ordre == 0, 'magnitudes croissantes dans 400 feuilles tirées au hasard')
    verifie(hors_boite == 0, 'étoiles dans la boîte de leur feuille')


def retrouve(parts, rec, n):
    """Position recalculée depuis les fichiers téléchargés -> présente dans gaia.bin."""
    fichiers = sorted(glob.glob(os.path.join(parts, 'part_*.fits')))
    rng = np.random.default_rng(2)
    with fits.open(fichiers[rng.integers(len(fichiers))]) as h: d = h[1].data
    d = d[np.isfinite(d['phot_g_mean_mag'])]
    s = d[rng.choice(len(d), min(2000, len(d)), replace=False)]
    ra, de, plx = np.radians(s['ra']), np.radians(s['dec']), s['parallax']
    e = gc.EPS
    x, y, z = np.cos(de) * np.cos(ra), np.cos(de) * np.sin(ra), np.sin(de)
    p = np.stack([x, math.cos(e) * y + math.sin(e) * z, -math.sin(e) * y + math.cos(e) * z], 1) * (1000.0 / plx * gc.LY_PER_PC)[:, None]
    tout = np.stack([rec['x'], rec['y'], rec['z']], 1)
    from scipy.spatial import cKDTree
    arbre = cKDTree(tout)
    dist, j = arbre.query(p.astype(np.float32).astype(np.float64))
    rel = dist / np.linalg.norm(p, axis=1)
    trouves = np.sum(rel < 1e-6)
    # les étoiles retirées comme doublons du catalogue principal sont absentes : on ne compte que les plus faibles que G = 13
    faibles = s['phot_g_mean_mag'] >= 13
    verifie(np.all(rel[faibles] < 1e-6), f'aller-retour : {int(np.sum(rel[faibles] < 1e-6))}/{int(faibles.sum())} étoiles G ≥ 13 retrouvées à leur place')
    M = s['phot_g_mean_mag'] + 5 * np.log10(plx / 100.0)
    ecart = np.abs(rec['m'][j[faibles]].astype(np.float64) - M[faibles])
    verifie(np.all(ecart < 0.01), f'magnitude absolue identique (écart max {ecart.max():.4f}, codage demi-flottant)')
    return trouves


def connues(parts, rec):
    """Barnard (source_id 4472832130942575872) et Proxima (5853498713190525696) : distance d'après la parallaxe téléchargée."""
    from scipy.spatial import cKDTree
    pos = np.stack([rec['x'], rec['y'], rec['z']], 1)
    arbre = cKDTree(pos)
    for nom, sid in (('Étoile de Barnard', 4472832130942575872), ('Proxima du Centaure', 5853498713190525696)):
        k = int(sid // 2 ** 35 * 1024 // (12 * 4 ** 12))
        with fits.open(os.path.join(parts, f'part_{k:04d}.fits')) as h: d = h[1].data
        r = d[d['source_id'] == sid]
        if len(r) == 0:
            verifie(False, f'{nom} absente du téléchargement'); continue
        dl = 1000.0 / r['parallax'][0] * gc.LY_PER_PC
        voisins = arbre.query_ball_point([0, 0, 0], dl * 1.0001)
        d_bin = np.linalg.norm(pos[voisins], axis=1)
        verifie(np.any(np.abs(d_bin - dl) < 1e-4), f'{nom} à {dl:.4f} al (parallaxe {r["parallax"][0]:.3f} mas)')


def voie(chemin):
    with open(chemin, 'rb') as f: h = f.read(1024)
    verifie(h[:8] == b'UNIVMW01', 'signature UNIVMW01')
    v = np.frombuffer(h[8:8 + 4 * 34], '<f4')
    nx, ny, nz = (int(a) for a in v[:3])
    g = np.fromfile(chemin, '<f2', nx * ny * nz * 2, offset=1024).astype(np.float32).reshape(nz, ny, nx, 2)
    verifie(np.all(np.isfinite(g)) and np.all(g >= 0), 'grille de la Voie lactée : valeurs finies et positives')
    hx, hz, sun = v[3], v[4], v[6:9]
    i, j, k = (int((sun[0] + hx) / (2 * hx) * nx), int((sun[1] + hx) / (2 * hx) * ny), int((sun[2] + hz) / (2 * hz) * nz))
    a = g[k, j, i, 1] * 1e3
    verifie(0.1 < a < 10, f'poussière dans la case du Soleil : {a:.2f} mag/kpc')


def agrege(chemin):
    h = np.fromfile(chemin, np.uint8, 64)
    verifie(bytes(h[:8]) == b'UNIVGAG1', 'signature UNIVGAG1')
    nc, ns = int(h[8:16].view('<u8')[0]), int(h[16:20].view('<u4')[0])
    t = np.fromfile(chemin, np.dtype([('p', '<f4', 3), ('m', '<f4'), ('r', '<f4'), ('e', '<f4'), ('c', '<u4'), ('n', '<u4')]), nc + ns, offset=64)
    sources = int(t['n'].sum(dtype=np.int64))
    # DR3 : 1 811 709 771 sources ; ici toutes celles qui ont une magnitude G, moins les 98 346 986 dessinées une à une
    verifie(1.70e9 < sources < 1.72e9, f'{sources} sources additionnées ({nc} cases 3D, {ns} pixels de ciel seul)')
    verifie(np.all(np.isfinite(t['m'])) and np.all(t['e'][:nc] <= 0.2), 'magnitudes finies ; erreur de distance des cases 3D ≤ 20 %')


def main():
    parts, gaia_bin = sys.argv[1], sys.argv[2]
    n, fe, rec = lire(gaia_bin)
    format_(n, fe, rec)
    retrouve(parts, rec, n)
    connues(parts, rec)
    if len(sys.argv) > 3: voie(sys.argv[3])
    if len(sys.argv) > 4: agrege(sys.argv[4])
    if ECHECS: sys.exit(f'{len(ECHECS)} échec(s)')
    print('tout passe')


if __name__ == '__main__':
    main()
