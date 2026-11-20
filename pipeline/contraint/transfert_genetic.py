"""Écrit la fonction de transfert de cosmo_lineaire (Eisenstein & Hu 1998 sans oscillations, Planck 2018)
au format CAMB à 7 colonnes lu par genetIC (k [h/Mpc], CDM, baryons, photons, neutrinos, neutrinos massifs, total).
genetIC renormalise à sigma8 : seule la forme compte. Modèle signalé : ~5 % d'écart à CAMB sur P(k) [Probable].
CAMB lui-même n'a pas pu être installé (garde-fou), d'où ce fichier.
Usage : python transfert_genetic.py SORTIE
"""
import sys
import numpy as np
from cosmo_lineaire import transfert_eh_sans_oscillations

k = np.logspace(-5, np.log10(200.0), 800)
t = transfert_eh_sans_oscillations(k)          # CAMB donne δ/k² ∝ T(k) (constant à petit k)
t = t / t[0] * 2.0e8
cols = np.stack([k, t, t, t, t, np.zeros_like(k), t], axis=1)
np.savetxt(sys.argv[1], cols, fmt='%14.6E')
