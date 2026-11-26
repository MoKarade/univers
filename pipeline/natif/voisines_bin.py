#!/usr/bin/env python3
"""voisines_etoiles.bin (étoiles visibles d'Andromède, du Triangle et des Nuages pour l'appli PC) refait depuis les fichiers
du contrat déjà écrits, sans retirer les étoiles : même écriture que la fin de etoiles_visibles_photos.py (drapeaux 1, 2,
16 modèle et 32 galaxie voisine ; 4e champ de la vitesse : rang de la galaxie + 16 × composante).

Sert quand les étoiles ont été déplacées après leur tirage, par exemple posées sur la masse du calcul
(etoiles_visibles_voisines_masse.py) : le film du Groupe local les suit alors dans cet état, et l'appli doit montrer
les mêmes à t = 0.

Usage : python voisines_bin.py <dossier des etoiles_visibles_<galaxie>.npz> <gaia.bin (table des couleurs)> <sortie.bin>
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voie_lactee as v
from etoiles_visibles import ecrire_gaia

ORDRE = ['andromede', 'triangle', 'grand_nuage', 'petit_nuage']      # ordre du film et de voisines_etoiles.ordre


def main():
    dossier, gaia_bin, sortie = sys.argv[1:4]
    tous = []
    for nom in ORDRE:
        with np.load(os.path.join(dossier, f'etoiles_visibles_{nom}.npz')) as z:
            tous.append((z['pos'].astype(np.float64), z['vel'].astype(np.float64), z['lum'].astype(np.float64), z['teff'].astype(np.float64), z['comp'].astype(np.int16)))
        print(f'{nom} : {len(tous[-1][0])} étoiles')
    D = v.data_keys(['M_GAL2ECL', 'SGRA_GAL'])
    gal2ecl = np.array(D['M_GAL2ECL'])
    sgra = np.array(D['SGRA_GAL']) / np.linalg.norm(D['SGRA_GAL']); sun = -v.R0 * sgra
    P, V, L, T, C = (np.concatenate([t[k] for t in tous]) for k in range(5))
    rang = np.concatenate([np.full(len(t[0]), k, np.int16) for k, t in enumerate(tous)]) + 16 * C
    ecrire_gaia(sortie, P, V, L, T, sun, gal2ecl, gaia_bin, drapeaux=1 | 2 | 16 | 32, aux=rang)      # écrit .partiel puis remplace
    print('->', sortie, os.path.getsize(sortie), 'octets')


if __name__ == '__main__':
    main()
