"""Numéro de source Gaia de chaque étoile de gaia.bin / gaia_b.bin, dans l'ordre du fichier -> gaia_ids.bin.

Pourquoi : gaia.bin ne garde pas les numéros de source ; il en faut un pour rattacher à chaque étoile sa masse, son âge
et sa composition mesurés par Gaia (gaia_ap.py, etoiles_vie.py).

Méthode : on refait exactement le tri de gaia_convertir.py (mêmes fonctions, mêmes entrées), puis on CONTRÔLE que
positions, magnitudes et couleurs obtenues sont identiques, octet pour octet, à celles du gaia.bin existant.
Rien n'est écrit si une seule étoile diffère.

Format gaia_ids.bin : « UNIVIDS1 », n (u64), puis n numéros de source (u64, petit-boutiste).

Usage : python gaia_ids.py <parts ou gaia_b.parquet> <etoiles.bin> <gaia.bin existant> <sortie gaia_ids.bin> [--parquet oui]
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gaia_convertir as gc


def ordre(G: dict, etoiles_bin: str) -> tuple[np.ndarray, np.ndarray]:
    """Indices des étoiles gardées, dans l'ordre du fichier, et leurs enregistrements (x, y, z, m, c)."""
    ra, de, plx = np.radians(G['ra']), np.radians(G['dec']), G['parallax']
    ca, sa, cd, sd = np.cos(ra), np.sin(ra), np.cos(de), np.sin(de)
    ce, se = math.cos(gc.EPS), math.sin(gc.EPS)
    u = np.stack([cd * ca, ce * (cd * sa) + se * sd, -se * (cd * sa) + ce * sd], 1)
    d_ly = 1000.0 / plx * gc.LY_PER_PC
    g = G['phot_g_mean_mag'].astype(np.float64)
    M = g + 5 * np.log10(plx / 100.0)
    u_main, v_main, _ = gc.principal(etoiles_bin)
    retire, _ = gc.doublons(u, g, u_main, v_main)
    garde = np.isfinite(g) & np.isfinite(plx) & (plx > 0)
    garde[retire] = False
    bprp = G['bp_rp'].astype(np.float64)
    pas = np.where(np.isfinite(bprp), np.clip(np.floor((bprp - gc.BPRP0) / gc.BPRP_PAS), 0, 254), 255).astype(np.uint8)
    k = np.nonzero(garde)[0]
    p = u[k] * d_ly[k, None]
    R = float(np.abs(p).max()) * 1.0001
    q = np.floor((p + R) / (2 * R) * (1 << 21)).clip(0, (1 << 21) - 1)
    cles = gc.morton(q)
    o = np.argsort(cles, kind='stable')
    k, p, cles = k[o], p[o], cles[o]
    fs = gc.feuilles(cles)
    num = np.zeros(len(k), np.int64)
    for i, (lo, hi) in enumerate(fs):
        num[lo:hi] = i
    o = np.lexsort((M[k], num))
    k, p = k[o], p[o]
    rec = np.zeros(len(k), np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('m', '<f2'), ('c', 'u1'), ('f', 'u1')]))
    rec['x'], rec['y'], rec['z'] = p[:, 0], p[:, 1], p[:, 2]
    rec['m'], rec['c'] = M[k], pas[k]
    return k, rec


def enregistrements(chemin: str) -> np.ndarray:
    """Section des étoiles d'un gaia.bin existant (format de gaia_convertir.py)."""
    with open(chemin, 'rb') as f:
        tete = f.read(4096)
    n = int(np.frombuffer(tete, '<u8', 1, 8)[0])
    nf = int(np.frombuffer(tete, '<u4', 1, 16)[0])
    debut = 4096 + nf * 48 + (-(nf * 48) % 64)
    return np.memmap(chemin, np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('m', '<f2'), ('c', 'u1'), ('f', 'u1')]),
                     'r', debut, (n,))


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    source, etoiles_bin, existant, sortie = sys.argv[1:5]
    opt = dict(zip(sys.argv[5::2], sys.argv[6::2]))
    G = gc.lire_parquet(source) if opt.get('--parquet', 'non') == 'oui' else gc.lire_parts(source)
    k, rec = ordre(G, etoiles_bin)
    ref = enregistrements(existant)
    if len(ref) != len(rec):
        sys.exit(f'{len(rec)} étoiles recalculées, {len(ref)} dans {existant} : ordre non retrouvé, rien écrit')
    for champ in ('x', 'y', 'z', 'm', 'c'):
        diff = int((ref[champ].view(np.uint32 if champ in 'xyz' else np.uint16 if champ == 'm' else np.uint8)
                    != rec[champ].view(np.uint32 if champ in 'xyz' else np.uint16 if champ == 'm' else np.uint8)).sum())
        if diff:
            sys.exit(f'champ {champ} : {diff} étoiles différentes de {existant} : ordre non retrouvé, rien écrit')
    ids = np.asarray(G['source_id'], np.int64)[k].astype('<u8')
    with open(sortie + '.partiel', 'wb') as f:
        f.write(b'UNIVIDS1' + np.uint64(len(ids)).tobytes())
        f.write(ids.tobytes())
    os.replace(sortie + '.partiel', sortie)
    print(f'{len(ids)} numéros écrits dans {sortie} ; positions, magnitudes et couleurs identiques à {existant}')


if __name__ == '__main__':
    main()
