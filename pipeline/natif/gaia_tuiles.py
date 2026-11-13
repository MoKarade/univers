#!/usr/bin/env python3
"""Gaia DR3 complet (Parquet de gaia_cdn.py) -> tuiles du ciel pour l'appli PC (lues à la demande sur le Drive) et
jeu « B » (parallaxe entre 5 et 10 sigma) pour gaia.bin. Plan : docs/plan-gaia-complet.md.

Trois classes, sans rien inventer :
- A : parallaxe > 10 sigma (98 346 986 étoiles) : déjà dans gaia.bin (gaia_telecharger.py) ; ignorées ici ;
- B : parallaxe entre 5 et 10 sigma : distance à 10-20 % près ; écrites telles quelles dans gaia_b.parquet ;
- C : tout le reste (parallaxe sous 5 sigma, ou absente) : direction mesurée, distance non mesurée -> tuiles du ciel.

Tuiles (classe C) : pixels HEALPix emboîtés d'ordre 6 (49 152 tuiles de 0,92°), tirés du numéro Gaia lui-même
(source_id // 2^35 = pixel d'ordre 12 ; // 4^6 de plus = ordre 6). Dans une tuile, étoiles de la plus brillante à la
plus faible : l'appli lit seulement le début d'une tuile quand elle n'a besoin que des plus brillantes.
Paquets : les 64 tuiles d'un pixel d'ordre 3 (voisines sur le ciel) bout à bout dans p###.bin (768 paquets).
Étoile (24 octets) : direction unitaire x, y, z (float32, repère écliptique J2000 de l'appli, époque J2016,0),
G (uint16, millièmes de magnitude), BP-RP (int16, millièmes ; -32768 = non mesuré), parallaxe (float32, mas, NaN si
absente), erreur de parallaxe (float16, mas), drapeaux (uint8 : 1 = vitesse radiale mesurée, 2 = mouvement propre
mesuré), réservé (uint8).
Index (sur le PC) gaia_tuiles.idx : « UNIVGTU1 », u32 ordre (6), u32 nombre de tuiles, u32 nombre de seuils (14), u32
réservé, 14 seuils G (float32 : 8 à 21), puis par tuile : décalage dans son paquet (u64), nombre d'étoiles (u32),
nombre d'étoiles plus brillantes que chaque seuil (14 × u32).
Usage : python gaia_tuiles.py <dossier des Parquet> <dossier des paquets> <index gaia_tuiles.idx> <gaia_b.parquet>
"""
import glob
import math
import os
import struct
import sys
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding='utf-8')
ORDRE, ORDRE_PAQUET = 6, 3
NTUILES = 12 * 4 ** ORDRE
DECALAGE = 35 + 2 * (12 - ORDRE)      # source_id >> DECALAGE = pixel d'ordre 6
SEUILS = np.arange(8.0, 22.0, 1.0, dtype=np.float32)
EPS = math.radians(84381.448 / 3600.0)
ETOILE = np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('g', '<u2'), ('bprp', '<i2'), ('plx', '<f4'),
                   ('eplx', '<f2'), ('drap', 'u1'), ('res', 'u1')])
assert ETOILE.itemsize == 24


def enregistrements(t: dict) -> np.ndarray:
    ra, de = np.radians(t['ra']), np.radians(t['dec'])
    cx, cy, cz = np.cos(de) * np.cos(ra), np.cos(de) * np.sin(ra), np.sin(de)
    out = np.zeros(len(ra), ETOILE)
    out['x'] = cx
    out['y'] = cy * math.cos(EPS) + cz * math.sin(EPS)
    out['z'] = -cy * math.sin(EPS) + cz * math.cos(EPS)
    g = t['phot_g_mean_mag']
    out['g'] = np.where(np.isfinite(g), np.clip(np.round(g * 1000), 0, 65535), 65535).astype('<u2')
    c = t['bp_rp']
    out['bprp'] = np.where(np.isfinite(c), np.clip(np.round(c * 1000), -32767, 32767), -32768).astype('<i2')
    out['plx'] = t['parallax']
    out['eplx'] = t['parallax_error'].astype(np.float16)
    out['drap'] = np.isfinite(t['radial_velocity']).astype(np.uint8) | (np.isfinite(t['pmra']).astype(np.uint8) << 1)
    return out


class Ecrivain:
    """Écrit les tuiles dans l'ordre ; un paquet est fermé dès que la tuile suivante appartient au paquet d'après."""

    def __init__(self, dossier: str):
        self.dossier = dossier
        os.makedirs(dossier, exist_ok=True)
        self.index = np.zeros((NTUILES, 2 + len(SEUILS)), np.uint64)
        self.paquet, self.f, self.pos = -1, None, 0

    def tuile(self, n: int, e: np.ndarray) -> None:
        p = n >> (2 * (ORDRE - ORDRE_PAQUET))
        if p != self.paquet:
            self.fermer()
            self.paquet, self.pos = p, 0
            self.f = open(os.path.join(self.dossier, f'p{p:03d}.bin.part'), 'wb')
        e = e[np.argsort(e['g'], kind='stable')]
        self.index[n, 0] = self.pos
        self.index[n, 1] = len(e)
        self.index[n, 2:] = np.searchsorted(e['g'], np.round(SEUILS * 1000).astype(np.uint16), side='left')
        self.f.write(e.tobytes())
        self.pos += e.nbytes

    def fermer(self) -> None:
        if self.f:
            self.f.close()
            nom = os.path.join(self.dossier, f'p{self.paquet:03d}.bin')
            os.replace(nom + '.part', nom)
            self.f = None


def main() -> None:
    entree, paquets, chemin_idx, chemin_b = sys.argv[1:5]
    fichiers = sorted(glob.glob(os.path.join(entree, 'GaiaSource_*.parquet')))
    ecr = Ecrivain(paquets)
    b_ecr = None
    reste, reste_n = None, -1      # étoiles de la dernière tuile d'un fichier : elle continue dans le suivant
    nA = nB = nC = 0
    t0 = time.time()
    for k, chemin in enumerate(fichiers):
        tb = pq.read_table(chemin)
        t = {c: tb.column(c).to_numpy(zero_copy_only=False) for c in tb.column_names}
        poe = t['parallax'] / t['parallax_error']
        A = poe > 10
        B = (poe > 5) & ~A
        C = ~(A | B)      # parallaxe sous 5 sigma, ou absente (NaN)
        nA += int(A.sum()); nB += int(B.sum()); nC += int(C.sum())
        if B.any():
            tb_b = tb.filter(pa.array(B))
            if b_ecr is None:
                b_ecr = pq.ParquetWriter(chemin_b + '.part', tb_b.schema, compression='zstd')
            b_ecr.write_table(tb_b)
        sid = t['source_id'][C]
        e = enregistrements({c: v[C] for c, v in t.items()})
        tu = (sid >> DECALAGE).astype(np.int64)
        if np.any(np.diff(tu) < 0):
            raise SystemExit(f'{chemin} : sources pas rangées par numéro Gaia')
        coupes = np.flatnonzero(np.diff(tu)) + 1
        debuts = np.r_[0, coupes]
        fins = np.r_[coupes, len(tu)]
        for d, f in zip(debuts, fins):
            n = int(tu[d])
            morceau = e[d:f]
            if n == reste_n:
                morceau = np.concatenate([reste, morceau])
            elif reste is not None:
                ecr.tuile(reste_n, reste)
            reste, reste_n = morceau, n
        if k % 20 == 0:
            print(f'{k + 1}/{len(fichiers)} fichiers ; A {nA}, B {nB}, C {nC} ; {time.time() - t0:.0f} s', flush=True)
    if reste is not None:
        ecr.tuile(reste_n, reste)
    ecr.fermer()
    if b_ecr:
        b_ecr.close()
        os.replace(chemin_b + '.part', chemin_b)
    with open(chemin_idx + '.part', 'wb') as f:
        f.write(b'UNIVGTU1' + struct.pack('<IIII', ORDRE, NTUILES, len(SEUILS), 0) + SEUILS.tobytes())
        for row in ecr.index:
            f.write(struct.pack('<Q', int(row[0])) + row[1:].astype('<u4').tobytes())
    os.replace(chemin_idx + '.part', chemin_idx)
    print(f'FIN : A {nA} (déjà dans gaia.bin), B {nB}, C {nC} ; total {nA + nB + nC} ; {time.time() - t0:.0f} s', flush=True)


if __name__ == '__main__':
    main()
