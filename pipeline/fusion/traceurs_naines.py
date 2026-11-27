#!/usr/bin/env python3
"""Galaxies naines suivies par le film (bloc « naine » de la famille P, docs/format-film-v3.md) : un point par galaxie.

Source : Local Volume Database (Pace 2024, github.com/apace7/local_volume_database, fichier comb_all.csv) : galaxies
confirmées dont la place ET la vitesse complète sont mesurées (distance, vitesse radiale, mouvement propre), satellites
de la Voie lactée (colonne host) à l'incertitude de vitesse transverse d'au plus 150 km/s. Les deux Nuages de Magellan
sont exclus : le calcul les porte déjà. Rien d'inventé : mesures converties, vitesse du Soleil de la table unique.
Les naines sont des traceurs SANS masse : leur attraction sur le disque (Sagittaire) n'est pas dans le calcul.

Écrit <sortie>.npz : nom, pos (kpc), vel (km/s) dans le repère de l'appli (Voie lactée à l'origine, au repos),
incertitude (km/s), masse d'étoiles (M☉, pour mémoire), version du fichier lu.
Usage : python traceurs_naines.py <comb_all.csv> <sortie.npz>
"""
import csv
import math
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'constantes'))
import constantes as C      # noqa: E402

# ICRS -> axes de la Galaxie (x vers le centre, y dans le sens de la rotation, z vers le pôle nord galactique) : matrice de Hipparcos (ESA 1997)
ICRS_VERS_GAL = np.array([[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132],
                          [0.4941094278755837, -0.4448296299600112, 0.7469822444972189],
                          [-0.8676661490190047, -0.1980763734312015, 0.4559837761750669]])
K = 4.74047      # km/s par (mas/an x kpc)
INCERTITUDE_MAX = 150.0
EXCLUES = ('lmc', 'smc')


def main():
    source, sortie = sys.argv[1:3]
    rep = C.charger()['repere']; soleil_p, soleil_v = np.array(rep['soleil_position']), np.array(rep['soleil_vitesse'])
    noms, pos, vel, inc, masse = [], [], [], [], []
    for r in csv.DictReader(open(source, encoding='utf-8')):
        if r.get('confirmed_galaxy') != '1' or not r.get('host', '').startswith('mw') or r['key'] in EXCLUES: continue
        try:
            ra, de, d, vl, pa, pd = (float(r[c]) for c in ('ra', 'dec', 'distance', 'vlos_systemic', 'pmra', 'pmdec'))
        except ValueError:
            continue      # place ou vitesse incomplète : pas suivie
        f = lambda c: abs(float(r[c] or 0))
        e = K * d * math.hypot(max(f('pmra_em'), f('pmra_ep')), max(f('pmdec_em'), f('pmdec_ep')))
        if e > INCERTITUDE_MAX: continue
        a, b = math.radians(ra), math.radians(de)
        rh = np.array([math.cos(b) * math.cos(a), math.cos(b) * math.sin(a), math.sin(b)])
        e1 = np.array([-math.sin(a), math.cos(a), 0.0]); e2 = np.array([-math.sin(b) * math.cos(a), -math.sin(b) * math.sin(a), math.cos(b)])
        v = vl * rh + K * d * (pa * e1 + pd * e2)
        noms.append(r['name']); pos.append(ICRS_VERS_GAL @ (d * rh) + soleil_p); vel.append(ICRS_VERS_GAL @ v + soleil_v); inc.append(e)
        try: masse.append(10 ** float(r['mass_stellar']))
        except ValueError: masse.append(float('nan'))
    pos, vel = np.array(pos), np.array(vel)
    np.savez(sortie, nom=np.array(noms), pos=pos, vel=vel.astype(np.float32), incertitude=np.array(inc, np.float32), masse_etoiles=np.array(masse, np.float32),
             source=os.path.basename(source))
    print(f'{len(noms)} naines suivies')
    for n, p, v_, e in zip(noms, pos, vel, inc):
        print(f'  {n:22s} à {np.linalg.norm(p):6.1f} kpc du centre ; vitesse {np.linalg.norm(v_):5.0f} km/s (± {e:3.0f})')


if __name__ == '__main__':
    main()
