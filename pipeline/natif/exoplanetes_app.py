#!/usr/bin/env python3
"""Planètes des autres étoiles pour l'appli PC : chaque étoile hôte est reliée à son étoile du catalogue de l'appli.

Demande de Marc (20/11/2026) : « on ne voit jamais de planètes ». Entrée : exoplanetes.tsv (pipeline/natif/exoplanetes.py,
table pscomppars de la NASA Exoplanet Archive, DOI 10.26133/NEA13 ; une ligne par planète confirmée, valeurs mesurées,
cases vides gardées vides) et etoiles.bin de l'appli (colonnes x, y, z en années-lumière, écliptique J2000).

Appariement : l'hôte (ascension droite, déclinaison, distance mesurées) est ramené dans le repère de l'appli ; l'étoile
retenue est la plus proche à moins de 1 minute d'arc sur le ciel ET dont la distance diffère de moins de 10 %. Sinon l'hôte
n'est pas relié (pas d'étoile inventée) ; le nombre de non reliés est imprimé.

Sorties :
  etoiles_planetes_noms.tsv : rang de l'étoile dans etoiles.bin, nom de l'hôte, distance (al), nombre de planètes
                              (lu par Sim::loadBodies : étoiles cherchables, nom montré de près).
  exoplanetes_app.tsv       : rang de l'étoile, nom de la planète, demi-grand axe (UA), excentricité, inclinaison (°),
                              période (jours), rayon (rayons terrestres), masse (masses terrestres), sorte de masse
                              (Mass, Msini, M-R relationship : cette dernière est un MODÈLE), argument du périastre (°),
                              passage devant l'étoile (jour julien), méthode de découverte, année ; cases vides gardées.
Usage : python exoplanetes_app.py <exoplanetes.tsv> <etoiles.bin> <dossier de sortie>
"""
import csv
import math
import os
import struct
import sys

import numpy as np
from scipy.spatial import cKDTree

EPS = math.radians(84381.448 / 3600.0)
RX = np.array([[1, 0, 0], [0, math.cos(EPS), math.sin(EPS)], [0, -math.sin(EPS), math.cos(EPS)]])
PC_LY = 3.2615637771674333
ALIGN = 64


def lire_etoiles(chemin):
    with open(chemin, 'rb') as f:
        tete = f.read(16)
        assert tete[:8] == b'UNIVSTR1'
        n = struct.unpack_from('<Q', tete, 8)[0]
        col = (n * 4 + ALIGN - 1) // ALIGN * ALIGN
        xyz = np.empty((n, 3), dtype=np.float64)
        for k in range(3):
            f.seek(ALIGN + k * col)
            xyz[:, k] = np.frombuffer(f.read(n * 4), dtype='<f4')
    return xyz


def main(tsv, etoiles_bin, sortie):
    lignes = list(csv.DictReader(open(tsv, encoding='utf-8'), delimiter='\t'))
    xyz = lire_etoiles(etoiles_bin)
    dist = np.linalg.norm(xyz, axis=1)
    unit = xyz / np.maximum(dist, 1e-12)[:, None]
    arbre = cKDTree(unit)
    hotes, sans = {}, set()
    for r in lignes:
        h = r['hostname']
        if h in hotes or h in sans:
            continue
        try:
            ra, dec, d = math.radians(float(r['ra'])), math.radians(float(r['dec'])), float(r['sy_dist']) * PC_LY
        except ValueError:
            sans.add(h)
            continue
        u = RX @ np.array([math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)])
        cand = arbre.query_ball_point(u, 2 * math.sin(math.radians(1 / 60) / 2))
        best, bestd = -1, 1e9
        for i in cand:
            ecart = abs(dist[i] - d) / d
            if ecart < 0.10 and ecart < bestd:
                best, bestd = i, ecart
        if best < 0:
            sans.add(h)
        else:
            hotes[h] = (best, dist[best])
    n_par = {}
    with open(os.path.join(sortie, 'exoplanetes_app.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('# etoile\tplanete\ta_UA\texcentricite\tinclinaison_deg\tperiode_jours\trayon_terre\tmasse_terre\tsorte_masse\tperiastre_deg\ttransit_jd\tmethode\tannee\n')
        for r in lignes:
            if r['hostname'] not in hotes:
                continue
            i = hotes[r['hostname']][0]
            n_par[r['hostname']] = n_par.get(r['hostname'], 0) + 1
            f.write('\t'.join([str(i), r['pl_name'], r['pl_orbsmax'], r['pl_orbeccen'], r['pl_orbincl'], r['pl_orbper'], r['pl_rade'],
                               r['pl_bmasse'], r['pl_bmassprov'], r['pl_orblper'], r['pl_tranmid'], r['discoverymethod'], r['disc_year']]) + '\n')
    with open(os.path.join(sortie, 'etoiles_planetes_noms.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        for h, (i, d) in sorted(hotes.items(), key=lambda kv: kv[1][1]):
            f.write(f'{i}\t{h}\t{d:.3f}\t{n_par.get(h, 0)}\n')
    n_pl = sum(n_par.values())
    print(f'hôtes reliés : {len(hotes)} ({n_pl} planètes) ; hôtes sans étoile de l’appli : {len(sans)} '
          f'({sum(1 for r in lignes if r["hostname"] in sans)} planètes)')


if __name__ == '__main__':
    main(*sys.argv[1:4])
