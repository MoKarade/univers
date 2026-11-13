#!/usr/bin/env python3
"""Clones du Groupe local (groupe_local_clones.py --sortie) -> clones_groupe_local.bin, lu par l'appli PC.

Format (petit-boutiste) :
  en-tête 64 octets : « UNIVCLN1 », nombre de clones n (u32), nombre de galaxies g (u32), nombre d'images k (u32),
                      pas entre images (f32, Ga), quantum des positions (f32, kpc), probabilité de fusion (f32),
                      réservé jusqu'à 64 octets
  noms des galaxies : g × 8 octets (ASCII, complétés par des zéros), dans l'ordre MW, M31, M33, LMC
  date de fusion Voie lactée–Andromède par clone : n × f32 (Ga ; NaN si pas de fusion en 10 unités = 9,78 Ga)
  masses M200 par clone et galaxie : n × g × f32 (10^10 M☉, tirées)
  (UNIVCLN2 seulement) date d'absorption par clone et galaxie : n × g × f32 (Ga ; NaN si jamais absorbée) : l'appli
              cesse de montrer le point à cette date, au lieu de le recoller au centre de la galaxie qui l'absorbe
  positions : k × n × g × 3 × i16 (pas = quantum ; image i à i × pas Ga) ; repère galactocentrique d'astropy « v4.0 »
              (Soleil à x = −8,122 kpc, y vers la longitude 90°, z vers le pôle nord galactique), centre de masse des
              quatre galaxies au repos (origine qui dérive peu) ; une galaxie absorbée suit celle qui l'a absorbée.
Usage : python clones_bin.py <clones_groupe_local.npz> <sortie.bin>
"""
import json, struct, sys
import numpy as np

QUANTUM = 0.1       # kpc ; ±3 277 kpc (des clones sans fusion s'éloignent jusqu'à 2 262 kpc)


def main():
    src, out = sys.argv[1], sys.argv[2]
    d = np.load(src)
    traj = d['traj']                        # (k, n, g, 3) float32, kpc
    k, n, g, _ = traj.shape
    q = np.round(traj / QUANTUM)
    if np.abs(q).max() > 32767: sys.exit('positions hors de la plage des entiers 16 bits')
    t = d['t_fusion'].astype(np.float32); t[~np.isfinite(t)] = np.nan
    prob = float(np.isfinite(t).mean())
    noms = [str(x) for x in d['galaxies']]
    with open(out, 'wb') as f:
        h = (b'UNIVCLN2' if 't_absorbee' in d else b'UNIVCLN1') + struct.pack('<IIIfff', n, g, k, float(d['pas_traj_ga']), QUANTUM, prob)
        f.write(h + b'\0' * (64 - len(h)))
        for s in noms: f.write(s.encode('ascii')[:8].ljust(8, b'\0'))
        f.write(t.astype('<f4').tobytes())
        f.write(d['m'].astype('<f4').tobytes())
        if 't_absorbee' in d:
            ta = d['t_absorbee'].astype(np.float32); ta[~np.isfinite(ta)] = np.nan
            f.write(ta.astype('<f4').tobytes())
        f.write(q.astype('<i2').tobytes())
    print(json.dumps(dict(clones=n, galaxies=noms, images=k, pas_ga=float(d['pas_traj_ga']), probabilite=prob, octets=k * n * g * 6)))


if __name__ == '__main__':
    main()
