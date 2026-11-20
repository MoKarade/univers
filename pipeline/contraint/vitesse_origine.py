"""Contrôle physique : vitesse du Groupe local reconstruite (origine) contre le dipôle du fond diffus.

Référence : vitesse du Groupe local dans le repère du fond diffus, 627 ± 22 km/s vers l = 276° ± 3, b = +30° ± 3
(Kogut et al. 1993) [Certain]. Le filtre n'a que les sources à cz < CZ_MAX : il en retrouve une partie seulement.
Usage : python vitesse_origine.py [CZ_MAX]
"""
import sys
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as un
import cf4_wiener as w
from cosmo_lineaire import CorrelationVitesses, Spectre, taux_croissance
from scipy.linalg import cho_factor, cho_solve

cz = float(sys.argv[1]) if len(sys.argv) > 1 else 16000.0
g = w.lire_groupes(cz)
corr = CorrelationVitesses(Spectre(), taux_croissance(), lissage=w.LISSAGE)
cov = w.covariance_donnees(g, corr)
cov[np.diag_indices_from(cov)] += g['err'] ** 2 + w.SIGMA_NL ** 2
wt = cho_solve(cho_factor(cov, lower=True), g['u'])
v = w.vitesses_grille(np.array([[1e-3, 0.0, 0.0]]), g, wt, corr)[0]
c = SkyCoord(sgx=v[0], sgy=v[1], sgz=v[2], frame='supergalactic', representation_type='cartesian').galactic
c.representation_type = 'spherical'
print(f'cz<{cz:.0f} : |v| = {np.linalg.norm(v):.0f} km/s vers l = {c.l.deg:.0f}°, b = {c.b.deg:+.0f}°  (fond diffus : 627 km/s, l = 276°, b = +30°)')
