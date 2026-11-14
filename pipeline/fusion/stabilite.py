#!/usr/bin/env python3
"""Stabilité des disques de départ (modeles.py), sans AGAMA ni carte graphique : calcul direct.

Pour chaque galaxie du calcul de la rencontre : vitesse circulaire, densité de surface du disque et indice de stabilité de
Toomre Q = sigma_R * kappa / (3,36 G Sigma) en fonction du rayon. Un disque d'étoiles reste calme si Q dépasse environ 1,5
partout ; sous 1, il se fragmente et forme une barre en quelques tours (Toomre 1964 ; Binney & Tremaine 2008, § 6.2.3).

Hypothèses, les mêmes que modeles.py : halo NFW tronqué (ou Plummer, Hernquist), disque exponentiel mince (formule de
Freeman 1970 pour sa vitesse circulaire ; l'épaisseur est négligée, ce qui surestime un peu la gravité du disque et donc
sous-estime Q de quelques pour cent), bulbe de Hernquist, dispersion radiale sigma_R(R) = sigmar0 * exp(-R / Rsigmar)
avec sigmar0 = k * vc(2 Rd) et Rsigmar = 2 Rd (modeles.py : k = 0,35).

Usage : python stabilite.py            (tableau des modèles actuels, puis valeur de k qui donne Q >= 1,5)
"""
import math
import sys

import numpy as np
from scipy.special import i0, i1, k0, k1

sys.stdout.reconfigure(encoding='utf-8')
G = 4.30091e-6
V0, R0, MB, AB, MD, RS = 230.0, 8.2, 0.5e10, 0.5, 6.8e10, 16.0


def _v2_baryons_page(r):      # bulbe + disque de Miyamoto-Nagai de la page : sert seulement à caler le halo (comme modeles.py)
    return G * MB * r / (r + AB) ** 2 + G * MD * r * r / (r * r + (3.0 + 0.28) ** 2) ** 1.5


MS_NFW = (V0 * V0 - _v2_baryons_page(R0)) / ((math.log(1 + R0 / RS) - (R0 / RS) / (1 + R0 / RS)) / R0) / G


def v2_halo(r, kind, mh=None, ah=None, k_mass=1.0, k_r=1.0):
    if kind == 'nfw':
        x = r / (RS * k_r)
        return G * MS_NFW * k_mass * (np.log(1 + x) - x / (1 + x)) / r      # la coupure à 220 kpc ne change rien sous 30 kpc
    if kind == 'plummer':
        return G * mh * r * r / (r * r + ah * ah) ** 1.5
    return G * mh * r / (r + ah) ** 2      # Hernquist


def v2_disque(r, md, rd):      # disque exponentiel mince (Freeman 1970)
    y = r / (2 * rd)
    return 4 * math.pi * G * (md / (2 * math.pi * rd * rd)) * rd * y * y * (i0(y) * k0(y) - i1(y) * k1(y))


def modele(nom, halo, md, rd, mb=0.0, ab=1.0, **h):
    r = np.linspace(0.05, 12 * rd, 4000)
    v2 = v2_halo(r, halo, **h) + v2_disque(r, md, rd) + (G * mb * r / (r + ab) ** 2 if mb else 0)
    vc = np.sqrt(v2)
    om2 = v2 / r ** 2
    kappa = np.sqrt(np.clip(np.gradient(om2, r) * r + 4 * om2, 1e-12, None))
    sigma = md / (2 * math.pi * rd * rd) * np.exp(-r / rd)
    return dict(nom=nom, r=r, vc=vc, kappa=kappa, sigma=sigma, rd=rd, md=md)


def q_profil(m, k):
    vc2 = float(np.interp(2 * m['rd'], m['r'], m['vc']))
    sig_r = k * vc2 * np.exp(-m['r'] / (2 * m['rd']))
    return sig_r * m['kappa'] / (3.36 * G * m['sigma'])


MODELES = [
    modele('Voie lactée', 'nfw', MD, 2.6, MB, AB),
    modele('Andromède', 'nfw', MD * 1.5, 3.0, MB * 1.5, AB * 1.15, k_mass=1.5, k_r=1.15),
    modele('Triangle', 'plummer', 4.8e9, 1.4, mh=2.5e11, ah=21.0),
    modele('Grand Nuage', 'hernquist', 2.7e9, 1.5, mh=1.8e11, ah=12.0),
]


def main():
    print('Modèles de départ actuels (pipeline/fusion/modeles.py, k = 0,35) :')
    print(f"{'galaxie':<12} {'vc à 2 Rd':>10} {'Q à 1 Rd':>9} {'Q à 2 Rd':>9} {'Q à 3 Rd':>9} {'Q minimum':>10} {'à':>6}   k pour Q >= 1,5 partout")
    for m in MODELES:
        q = q_profil(m, 0.35)
        zone = (m['r'] > 0.5 * m['rd']) & (m['r'] < 4 * m['rd'])      # là où est la masse du disque
        qmin, rmin = float(q[zone].min()), float(m['r'][zone][q[zone].argmin()])
        at = lambda x: float(np.interp(x * m['rd'], m['r'], q))
        print(f"{m['nom']:<12} {float(np.interp(2 * m['rd'], m['r'], m['vc'])):>7.0f} km/s {at(1):>8.2f} {at(2):>9.2f} {at(3):>9.2f} {qmin:>10.2f} {rmin:>4.1f} kpc   {0.35 * 1.5 / qmin:.2f}")
    mw = MODELES[0]
    print(f"\nVoie lactée au Soleil (8,2 kpc) : vitesse circulaire {float(np.interp(R0, mw['r'], mw['vc'])):.0f} km/s (mesuré : 229 à 233, Eilers et al. 2019 ; "
          f"le halo est calé pour 230 avec le disque de la page, pas avec ce disque exponentiel) ; "
          f"densité de surface du disque {float(np.interp(R0, mw['r'], mw['sigma'])) / 1e6:.0f} M☉/pc² (mesuré : étoiles 33 ± 3, McKee et al. 2015).")


if __name__ == '__main__':
    main()


def voie_lactee_mcmillan():
    """Voie lactée de McMillan 2017 (MNRAS 465, 76), meilleur modèle (table 3) : disque mince 896 M☉/pc² et 2,50 kpc, disque
    épais 183 M☉/pc² et 3,02 kpc, bulbe 9,23e9 M☉, gaz 1,1e10 + 1,2e9 M☉, halo NFW 0,00854 M☉/pc³ et 19,6 kpc ; R0 = 8,21 kpc,
    v0 = 233,1 km/s. Le bulbe (loi de puissance tronquée) est pris ici en masse ponctuelle au-delà de 2 kpc, et le gaz comme
    un disque exponentiel de 7 kpc : approximations suffisantes pour Q entre 3 et 12 kpc, pas pour le centre."""
    r = np.linspace(2.0, 16.0, 3000)
    mince, epais = 2 * math.pi * 896e6 * 2.50 ** 2, 2 * math.pi * 183e6 * 3.02 ** 2
    x = r / 19.6
    v2 = (4 * math.pi * G * 0.00854e9 * 19.6 ** 3 * (np.log(1 + x) - x / (1 + x)) / r + v2_disque(r, mince, 2.50) + v2_disque(r, epais, 3.02)
          + G * 9.23e9 / r + v2_disque(r, 1.22e10, 7.0))
    vc = np.sqrt(v2)
    om2 = v2 / r ** 2
    kappa = np.sqrt(np.clip(np.gradient(om2, r) * r + 4 * om2, 1e-12, None))
    sig_etoiles = 896e6 * np.exp(-r / 2.50) + 183e6 * np.exp(-r / 3.02)
    return r, vc, kappa, sig_etoiles, mince, epais


def compare():
    r, vc, kappa, sig, mince, epais = voie_lactee_mcmillan()
    at = lambda a: float(np.interp(8.21, r, a))
    print('\nVoie lactée publiée (McMillan 2017, meilleur modèle), recalculée ici :')
    print(f"  disque mince {mince / 1e10:.2f}e10 M☉, disque épais {epais / 1e10:.2f}e10 M☉ (contre un seul disque de 6,8e10 dans modeles.py)")
    print(f"  au Soleil : vitesse circulaire {at(vc):.0f} km/s (publié : 233,1) ; disque d'étoiles {at(sig) / 1e6:.0f} M☉/pc²")
    # Dispersion radiale mesurée au Soleil : 35 ± 5 km/s pour le disque mince vieux (Bland-Hawthorn & Gerhard 2016, § 5.4) ; profil
    # exponentiel de longueur 2 Rd, comme dans modeles.py.
    for s0 in (30.0, 35.0, 40.0):
        q = s0 * np.exp(-(r - 8.21) / (2 * 2.50)) * kappa / (3.36 * G * sig)
        zone = (r > 3) & (r < 12)
        print(f"  dispersion radiale de {s0:.0f} km/s au Soleil : Q = {float(np.interp(8.21, r, q)):.2f} au Soleil, minimum {float(q[zone].min()):.2f} à {float(r[zone][q[zone].argmin()]):.1f} kpc")


if __name__ == '__main__':
    compare()
