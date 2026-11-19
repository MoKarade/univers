"""Cosmologie linéaire pour le départ contraint (Planck 2018, énergie noire incluse).

Fournit :
  - le spectre de puissance linéaire P(k) à z = 0 (forme d'Eisenstein & Hu 1998 « sans oscillations »,
    normalisée à sigma8) [modèle publié, Certain pour la formule ; précision ~5 % sur P(k)] ;
  - le taux de croissance f = Omega_m(z)^0,55 (approximation de Linder 2005, ΛCDM) ;
  - les fonctions de corrélation des vitesses Psi_par(r) et Psi_perp(r) (Gorski 1988),
    utilisées par le filtre de Wiener des vitesses de Cosmicflows-4.

Unités : distances en Mpc/h, k en h/Mpc, vitesses en km/s (H0 = 100 h km/s/Mpc).
"""
import numpy as np

# Planck 2018 (TT,TE,EE+lowE+lensing+BAO, tableau 2, dernière colonne)
PLANCK18 = dict(omega_m=0.3111, omega_b=0.0490, h=0.6766, n_s=0.9665, sigma8=0.8102, t_cmb=2.7255)


def transfert_eh_sans_oscillations(k, c=PLANCK18):
    """Fonction de transfert d'Eisenstein & Hu 1998, éq. 26-31 (forme lissée). k en h/Mpc."""
    om, ob, h = c['omega_m'], c['omega_b'], c['h']
    theta = c['t_cmb'] / 2.7
    omh2, obh2 = om * h * h, ob * h * h
    fb = ob / om
    s = 44.5 * np.log(9.83 / omh2) / np.sqrt(1.0 + 10.0 * obh2 ** 0.75)          # Mpc
    alpha = 1.0 - 0.328 * np.log(431.0 * omh2) * fb + 0.38 * np.log(22.3 * omh2) * fb * fb
    kmpc = k * h                                                                   # 1/Mpc
    gamma_eff = om * h * (alpha + (1.0 - alpha) / (1.0 + (0.43 * kmpc * s) ** 4))
    q = k * theta * theta / gamma_eff
    l0 = np.log(2.0 * np.e + 1.8 * q)
    c0 = 14.2 + 731.0 / (1.0 + 62.5 * q)
    return l0 / (l0 + c0 * q * q)


def _fenetre_chapeau(x):
    x = np.asarray(x, dtype=float)
    out = np.ones_like(x)
    m = x > 1e-4
    xm = x[m]
    out[m] = 3.0 * (np.sin(xm) - xm * np.cos(xm)) / xm ** 3
    return out


class Spectre:
    """P(k) linéaire à z = 0, normalisé à sigma8, tabulé en log k."""

    def __init__(self, c=PLANCK18, kmin=1e-5, kmax=50.0, n=6000):
        self.c = c
        self.k = np.logspace(np.log10(kmin), np.log10(kmax), n)
        brut = self.k ** c['n_s'] * transfert_eh_sans_oscillations(self.k, c) ** 2
        s8 = np.sqrt(self._sigma2(brut, 8.0))
        self.p = brut * (c['sigma8'] / s8) ** 2

    def _sigma2(self, p, r):
        w = _fenetre_chapeau(self.k * r)
        return np.trapezoid(p * w * w * self.k ** 3, np.log(self.k)) / (2.0 * np.pi ** 2)

    def sigma(self, r):
        return np.sqrt(self._sigma2(self.p, r))

    def __call__(self, k):
        return np.exp(np.interp(np.log(k), np.log(self.k), np.log(self.p)))


def taux_croissance(c=PLANCK18, z=0.0):
    """f(z) ≈ Omega_m(z)^0,55 pour ΛCDM plat (constante cosmologique comptée)."""
    a3 = (1.0 + z) ** 3
    om_z = c['omega_m'] * a3 / (c['omega_m'] * a3 + 1.0 - c['omega_m'])
    return om_z ** 0.55


def _j0(x):
    return np.sinc(x / np.pi)


def _j1_sur_x(x):
    """j1(x)/x, développé en série près de 0 (vaut 1/3 en 0)."""
    x = np.asarray(x, dtype=float)
    out = np.full_like(x, 1.0 / 3.0)
    m = x > 1e-3
    xm = x[m]
    out[m] = (np.sin(xm) / xm - np.cos(xm)) / xm ** 2
    small = ~m
    out[small] = 1.0 / 3.0 - x[small] ** 2 / 30.0
    return out


class CorrelationVitesses:
    """Psi_par(r) et Psi_perp(r) (Gorski 1988), tabulés puis interpolés.

    <v_i(x) v_j(x+r)> = Psi_perp(r) δ_ij + (Psi_par(r) − Psi_perp(r)) r̂_i r̂_j.
    Filtre gaussien optionnel (lissage des petites échelles non linéaires), rayon en Mpc/h.
    """

    def __init__(self, spectre, f, lissage=0.0, rmax=1500.0, n=4000):
        k = spectre.k
        pk = spectre.p * np.exp(-(k * lissage) ** 2)
        pref = (100.0 * f) ** 2 / (2.0 * np.pi ** 2)
        self.r = np.concatenate([[0.0], np.logspace(-2, np.log10(rmax), n)])
        lnk = np.log(k)
        perp, par = [], []
        for r in self.r:
            kr = k * r
            j1x = _j1_sur_x(kr)
            perp.append(np.trapezoid(pk * j1x * k, lnk))
            par.append(np.trapezoid(pk * (_j0(kr) - 2.0 * j1x) * k, lnk))
        self.perp = pref * np.array(perp)
        self.par = pref * np.array(par)

    def __call__(self, r):
        r = np.asarray(r)
        return np.interp(r, self.r, self.par), np.interp(r, self.r, self.perp)


class CorrelationDensite:
    """Corrélations du contraste lissé δ_s (P_s = P·exp(−k²R²)) avec lui-même et avec la vitesse.

    xi(r) = <δ_s(x) δ_s(x+r)> = ∫ k² dk/(2π²) P_s j0(kr)
    g(r)  : <δ_s(x) v_s(x+r)> = −f H r̂ g(r),  g(r) = ∫ k dk/(2π²) P_s j1(kr)   (vitesse dirigée vers la surdensité)
    """

    def __init__(self, spectre, f, lissage=0.0, rmax=1500.0, n=4000):
        k = spectre.k
        pk = spectre.p * np.exp(-(k * lissage) ** 2)
        self.f = f
        self.r = np.concatenate([[0.0], np.logspace(-2, np.log10(rmax), n)])
        lnk = np.log(k)
        xi, gg = [], []
        for r in self.r:
            kr = k * r
            xi.append(np.trapezoid(pk * _j0(kr) * k ** 3, lnk))
            gg.append(np.trapezoid(pk * _j1_sur_x(kr) * kr * k ** 2, lnk))
        self.xi = np.array(xi) / (2.0 * np.pi ** 2)
        self.g = np.array(gg) / (2.0 * np.pi ** 2)

    def __call__(self, r):
        r = np.asarray(r)
        return np.interp(r, self.r, self.xi), np.interp(r, self.r, self.g)
