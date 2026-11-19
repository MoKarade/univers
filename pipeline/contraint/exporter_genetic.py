"""Exporte une réalisation contrainte (resultats/rc_<graine>.npz) vers genetIC (commande import_level).

Convention de genetIC mesurée le 19/11 (essai rc/norm, grille 64³ dans 640 Mpc/h) : la grille importée/exportée
est le contraste de densité linéaire À z_in, pas à z = 0 (rapport des spectres constant = D(z_in)², 1,62e-4 pour
z_in = 99) [Certain, mesuré]. Repère : case [i, j, k] de genetIC = coin à 0, donc notre observateur
(centre de notre grille) est au milieu de la boîte ; axes x, y, z = SGX, SGY, SGZ.

Usage : python exporter_genetic.py GRAINE N_SORTIE [Z_IN=99]
  N_SORTIE : taille de la grille de base genetIC (≤ grille de la réalisation ; réduite par coupure en Fourier).
"""
import sys

import numpy as np
from scipy.integrate import quad

from cosmo_lineaire import PLANCK18
import os
PREFIXE = os.environ.get('PREFIXE', 'rc')          # rc = vitesses seules ; rcj = vitesses + densité 2MRS


def croissance(z: float, om: float = PLANCK18['omega_m']) -> float:
    """Facteur de croissance linéaire D(z)/D(0) en ΛCDM plat (constante cosmologique), intégrale de Heath 1977."""
    def d(a):
        e = np.sqrt(om / a ** 3 + 1.0 - om)
        return e * quad(lambda x: 1.0 / (x * np.sqrt(om / x ** 3 + 1.0 - om)) ** 3, 1e-8, a)[0]
    return d(1.0 / (1.0 + z)) / d(1.0)


def reduire(dk: np.ndarray, n: int, m: int) -> np.ndarray:
    """Coupe en Fourier une grille n³ (rfft) vers m³, même boîte."""
    if m == n:
        return dk
    h = m // 2
    idx = np.r_[0:h, n - h:n]
    out = dk[np.ix_(idx, idx, np.arange(h + 1))]
    return out * (m / n) ** 3


def main() -> None:
    graine, m = int(sys.argv[1]), int(sys.argv[2])
    z_in = float(sys.argv[3]) if len(sys.argv) > 3 else 99.0
    r = np.load(f'resultats/{PREFIXE}_{graine}.npz')
    n, cote = int(r['n']), float(r['cote'])
    dk = reduire(r['delta_k'].astype(np.complex128), n, m)
    delta = np.fft.irfftn(dk, s=(m,) * 3, axes=(0, 1, 2)) * croissance(z_in)
    sortie = f'resultats/{PREFIXE}_{graine}_genetic_{m}.npy'
    np.save(sortie, delta.astype(np.float64))
    print(f'{sortie} : boîte {cote:.0f} Mpc/h, {m}³, z_in {z_in:g}, D = {croissance(z_in):.5f}, écart-type {delta.std():.5f}')


if __name__ == '__main__':
    main()
