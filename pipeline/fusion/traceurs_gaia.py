#!/usr/bin/env python3
"""Étoiles Gaia suivies par le film (famille G, docs/format-film-v3.md) : celles dont la vitesse est complète et sûre
(drapeau 2 de gaia.bin : vitesse radiale mesurée, vitesse 3D connue à mieux que le seuil), à moins de 2 kpc du Soleil,
de la plus lumineuse à la moins lumineuse jusqu'à porter 90 % de la lumière de cet ensemble.

Écrit <sortie>.npz : rang (rang de l'étoile dans gaia.bin, u32), pos (kpc) et vel (km/s) dans le repère de l'appli
(Voie lactée à l'origine et au repos), taille et crc32 du gaia.bin lu (l'appli refuse un film fait sur un autre fichier).
Rien d'inventé : positions et vitesses mesurées, vitesse du Soleil de la table unique ajoutée.

Usage : python traceurs_gaia.py <gaia.bin> <sortie.npz> [--rayon-kpc 2] [--part 0.9]
"""
import os
import sys
import zlib

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'natif')); sys.path.insert(0, os.path.join(ICI, '..', 'constantes'))
import constantes as C      # noqa: E402
import voie_lactee as v     # noqa: E402

DT_ETOILE = np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('m', '<f2'), ('c', 'u1'), ('f', 'u1')])
DT_VITESSE = np.dtype([('v', '<i2', 3), ('dm', '<i2')])
ORBITE_FIABLE = 2


def main():
    gaia_bin, sortie = sys.argv[1:3]
    opts = dict(zip(sys.argv[3::2], sys.argv[4::2]))
    rayon, part = float(opts.get('--rayon-kpc', 2.0)), float(opts.get('--part', 0.9))
    tete = np.fromfile(gaia_bin, np.uint8, 4096)
    assert bytes(tete[:8]) == b'UNIVGAI1', 'gaia.bin non reconnu'
    n = int(tete[8:16].view('<u8')[0]); nf = int(tete[16:20].view('<u4')[0])
    debut = 4096 + (nf * 48 + 63) // 64 * 64; debut_v = debut + (n * 16 + 63) // 64 * 64
    etoiles = np.memmap(gaia_bin, DT_ETOILE, 'r', debut, (n,)); vitesses = np.memmap(gaia_bin, DT_VITESSE, 'r', debut_v, (n,))
    D = v.data_keys(['M_GAL2ECL', 'SGRA_GAL']); ecl2gal = np.array(D['M_GAL2ECL']).T
    rep = C.charger()['repere']; soleil_p, soleil_v = np.array(rep['soleil_position']), np.array(rep['soleil_vitesse'])
    rangs, lum = [], []
    for a in range(0, n, 20_000_000):      # passe 1 : qui est fiable et proche, avec sa lumière
        e = np.array(etoiles[a:a + 20_000_000])
        d = np.sqrt(e['x'].astype(np.float64) ** 2 + e['y'].astype(np.float64) ** 2 + e['z'].astype(np.float64) ** 2) / v.LY_PER_PC / 1e3
        ok = ((e['f'] & ORBITE_FIABLE) != 0) & (d <= rayon) & np.isfinite(e['m'])
        rangs.append(a + np.where(ok)[0]); lum.append(10 ** (-0.4 * e['m'][ok].astype(np.float64)))
    rangs, lum = np.concatenate(rangs), np.concatenate(lum)
    o = np.argsort(-lum); cumul = np.cumsum(lum[o]); garde = np.sort(rangs[o[:int(np.searchsorted(cumul, part * cumul[-1])) + 1]])
    e = etoiles[garde]; w = vitesses[garde]
    pos = (np.stack([e['x'], e['y'], e['z']], 1).astype(np.float64) @ ecl2gal.T) / v.LY_PER_PC / 1e3 + soleil_p
    vel = (w['v'].astype(np.float64) * 0.05) @ ecl2gal.T + soleil_v
    crc = 0
    with open(gaia_bin, 'rb') as f:
        while True:
            bloc = f.read(1 << 26)
            if not bloc: break
            crc = zlib.crc32(bloc, crc)
    np.savez(sortie, rang=garde.astype('<u4'), pos=pos, vel=vel.astype(np.float32), taille=os.path.getsize(gaia_bin), crc32=crc & 0xFFFFFFFF)
    print(f"{n} étoiles dans {os.path.basename(gaia_bin)} ; fiables à moins de {rayon:g} kpc : {len(rangs)} ; gardées ({100 * part:.0f} % de leur lumière) : {len(garde)}")
    print(f"vitesse médiane par rapport au Soleil : {np.median(np.linalg.norm(vel - soleil_v, axis=1)):.1f} km/s ; taille {os.path.getsize(gaia_bin)} octets, CRC32 {crc & 0xFFFFFFFF:08x}")


if __name__ == '__main__':
    main()
