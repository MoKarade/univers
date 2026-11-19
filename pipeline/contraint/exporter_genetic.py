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


# Amas de la Vierge imposé (contrainte linéaire supplémentaire, même formule que les réalisations contraintes) :
# mesuré le 19/11, les contraintes de densité lissées à 5 Mpc/h donnent δ_L ≈ 0,7 à la Vierge, trop peu pour former
# un amas de ~8e14 M☉/h (rayon de Lagrange 13 Mpc/h, il faut δ_L ≳ 1,69 dans cette boule) [Probable].
# Variables : VIERGE_DL (δ linéaire à z = 0 visé dans la boule ; vide = rien), VIERGE_Q (centre de Lagrange, repère
# supergalactique, Mpc/h, observateur à l'origine), VIERGE_R (rayon, Mpc/h). Modèle signalé : la valeur visée est un choix.
_v = os.environ.get('VIERGE_DL', '')
VIERGE_DL = float(_v) if _v else None
VIERGE_Q = np.array([float(x) for x in os.environ.get('VIERGE_Q', '5.31 8.5 0.7').split()])
VIERGE_R = float(os.environ.get('VIERGE_R', '13'))


def imposer_moyenne_boule(dk: np.ndarray, m: int, cote: float, q: np.ndarray, rayon: float, cible: float) -> np.ndarray:
    """δ' = δ + C w (wᵀ C w)⁻¹ (cible − wᵀ δ), w = moyenne sur la boule (contrainte de Hoffman & Ribak à une valeur).
    Travaille à z = 0 (dk est le δ linéaire à z = 0, convention numpy, voir realisations.py)."""
    from realisations import grille_k
    from cosmo_lineaire import Spectre
    kx, ky, kz, k2 = grille_k(m, cote)
    k = np.sqrt(k2)
    pk = Spectre()(k)
    pk[0, 0, 0] = 0.0
    x = k * rayon
    wth = np.where(x > 1e-4, 3.0 * (np.sin(x) - x * np.cos(x)) / np.maximum(x, 1e-4) ** 3, 1.0)
    c = q                                                 # centre dans NOTRE repère (origine = observateur)
    ax = -cote / 2.0 + (np.arange(m) + 0.5) * cote / m    # positions de nos cases
    # boule translatée en c : phase e^{-i k (c − ax[0])} (la case 0 est en ax[0]) ; l'échelle de C w est sans
    # importance, seule la forme compte (on normalise par sa moyenne sur la boule).
    phase = np.exp(-1j * (kx * (c[0] - ax[0]) + ky * (c[1] - ax[0]) + kz * (c[2] - ax[0])))
    wk = wth * phase
    champ =np.fft.irfftn(dk, s=(m,) * 3, axes=(0, 1, 2))
    gx, gy, gz = np.meshgrid(ax, ax, ax, indexing='ij', sparse=True)
    boule = (gx - c[0]) ** 2 + (gy - c[1]) ** 2 + (gz - c[2]) ** 2 < rayon ** 2
    actuel = champ[boule].mean()
    # profil de réponse C w (champ réel) et sa valeur moyenne sur la boule
    cw = np.fft.irfftn(pk * wk, s=(m,) * 3, axes=(0, 1, 2))
    wcw = cw[boule].mean()
    champ = champ + cw * (cible - actuel) / wcw
    print(f'Vierge imposée : δ_L moyen dans la boule de {rayon:g} Mpc/h passe de {actuel:.2f} à {champ[boule].mean():.2f} '
          f'(cible {cible:g})')
    return np.fft.rfftn(champ, axes=(0, 1, 2))


def main() -> None:
    graine, m = int(sys.argv[1]), int(sys.argv[2])
    z_in = float(sys.argv[3]) if len(sys.argv) > 3 else 99.0
    r = np.load(f'resultats/{PREFIXE}_{graine}.npz')
    n, cote = int(r['n']), float(r['cote'])
    dk = reduire(r['delta_k'].astype(np.complex128), n, m)
    if VIERGE_DL is not None:
        dk = imposer_moyenne_boule(dk, m, cote, VIERGE_Q, VIERGE_R, VIERGE_DL)
    delta =np.fft.irfftn(dk, s=(m,) * 3, axes=(0, 1, 2)) * croissance(z_in)
    sortie = f'resultats/{PREFIXE}_{graine}_genetic_{m}.npy'
    np.save(sortie, delta.astype(np.float64))
    print(f'{sortie} : boîte {cote:.0f} Mpc/h, {m}³, z_in {z_in:g}, D = {croissance(z_in):.5f}, écart-type {delta.std():.5f}')


if __name__ == '__main__':
    main()
