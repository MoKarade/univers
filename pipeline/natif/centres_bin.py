#!/usr/bin/env python3
"""Centres de référence des galaxies du Groupe local (pipeline/fusion/resultats/centres_reference.npz, PR 97, écrit par
pipeline/fusion/groupe_local_reference.py) -> centres_reference.bin, lu par l'appli PC (natif/src/centres_reference.h).

Contenu repris tel quel : dates t (Ga, 0 = aujourd'hui), positions (kpc) et vitesses (km/s) des centres, relatives au
centre de la Voie lactée, repère phys::galaxie ; ordre voie_lactee, andromede, triangle, grand_nuage, petit_nuage.
Format (petit-boutiste) : « UNIVCEN1 », n dates (u32), n galaxies (u32), rang d'aujourd'hui (u32), réservé (u32),
première date (f64, Ga), pas (f64, Ga), réservé jusqu'à 64 octets ; puis positions n × g × 3 f32, vitesses n × g × 3 f32.
Usage : python centres_bin.py <centres_reference.npz> <centres_reference.bin>
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')
import json, struct, sys
import numpy as np


def main():
    d = np.load(sys.argv[1])
    t, pos, vel = d['t'], d['pos'].astype('<f4'), d['vel'].astype('<f4')
    meta = json.loads(str(d['meta']))
    pas = np.diff(t)
    if np.abs(pas - pas.mean()).max() > 1e-9: sys.exit('dates non régulières : format à revoir')
    i0 = int(meta['i_aujourdhui'])
    if abs(t[i0]) > 1e-12: sys.exit('t = 0 absent')
    with open(sys.argv[2], 'wb') as f:
        h = b'UNIVCEN1' + struct.pack('<IIIIdd', len(t), pos.shape[1], i0, 0, float(t[0]), float(pas.mean()))
        f.write(h + b'\0' * (64 - len(h)))
        f.write(pos.tobytes()); f.write(vel.tobytes())
    print(f'{len(t)} dates de {t[0]:.3f} à {t[-1]:.3f} Ga, {pos.shape[1]} galaxies ({", ".join(map(str, meta.get("galaxies", [])))}) -> {sys.argv[2]}')


if __name__ == '__main__':
    main()
