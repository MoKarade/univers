"""Contrôles de cosmo_lineaire.py (python -m pytest pipeline/contraint)."""
import numpy as np

from cosmo_lineaire import PLANCK18, CorrelationVitesses, Spectre, taux_croissance


def test_sigma8_normalise():
    s = Spectre()
    assert abs(s.sigma(8.0) - PLANCK18['sigma8']) < 1e-3


def test_taux_croissance_planck():
    # Omega_m^0,55 avec Omega_m = 0,3111 : 0,526 [calcul direct]
    assert abs(taux_croissance() - 0.3111 ** 0.55) < 1e-12


def test_correlation_isotrope_en_zero():
    c = CorrelationVitesses(Spectre(), taux_croissance())
    par, perp = c(0.0)
    assert abs(par - perp) / perp < 1e-3          # en r = 0 la corrélation est isotrope
    sigma_1d = np.sqrt(perp)
    # dispersion linéaire d'une composante : quelques centaines de km/s en ΛCDM [Probable : ~250-350]
    assert 200.0 < sigma_1d < 450.0


def test_j1_sur_x_exact():
    from cosmo_lineaire import _j1_sur_x
    from scipy.special import spherical_jn
    x = np.array([1e-4, 0.01, 0.5, 3.0, 40.0])
    assert np.allclose(_j1_sur_x(x), spherical_jn(1, x) / x, rtol=1e-6, atol=1e-12)


def test_correlation_bornee():
    # |Psi(r)| ne peut pas dépasser Psi(0) (inégalité de Cauchy-Schwarz)
    c = CorrelationVitesses(Spectre(), taux_croissance())
    r = np.array([0.5, 5.0, 30.0, 100.0, 500.0])
    par, perp = c(r)
    p0 = c(0.0)[1]
    assert np.all(np.abs(par) <= p0 * 1.0001) and np.all(np.abs(perp) <= p0 * 1.0001)


def test_correlation_decroit():
    c = CorrelationVitesses(Spectre(), taux_croissance())
    par, perp = c(np.array([1.0, 50.0, 200.0]))
    assert perp[0] > perp[1] > perp[2]


def test_densite_variance_lissee():
    # xi(0) avec lissage gaussien 8 Mpc/h doit être proche de sigma8² (fenêtres différentes : ±20 %) [Probable]
    from cosmo_lineaire import CorrelationDensite
    c = CorrelationDensite(Spectre(), taux_croissance(), lissage=8.0 / np.sqrt(5.0))
    xi0, g0 = c(0.0)
    assert 0.6 < xi0 / PLANCK18['sigma8'] ** 2 < 1.4
    assert abs(g0) < 1e-6                     # pas de corrélation densité-vitesse à distance nulle
