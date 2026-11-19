"""Filtre de Wiener des vitesses de Cosmicflows-4 (groupes), première version, et contrôle contre Courtois 2023.

Méthode (Zaroubi et al. 1999 ; Hoffman & Ribak 1991 pour la suite) [Certain pour la méthode] :
  u_i  = vitesse radiale propre mesurée du groupe i,
  C    = <u u> du modèle ΛCDM linéaire (Gorski 1988) + bruit N (erreur de distance + agitation non linéaire),
  v(x) = <v(x) u> C^-1 ... appliqué à (C + N)^-1 u.

Limites de cette première version, à lever ensuite [Certain qu'elles existent] :
  - pas de correction du biais de Malmquist / de la loi log-normale des distances (Hoffman et al. 2021) ;
  - groupes coupés à cz < CZ_MAX ;
  - P(k) d'Eisenstein & Hu sans oscillations (~5 %).

Sortie : resultats/cf4_wiener_v1.npz (grille 64³ de Courtois, cube de 1000 Mpc/h) + bilan de corrélation.
Usage : python cf4_wiener.py [CZ_MAX]
"""
import os
import sys
import time

import numpy as np
from astropy.io import fits
from scipy.linalg import cho_factor, cho_solve

from cosmo_lineaire import PLANCK18, CorrelationVitesses, Spectre, taux_croissance

C_KMS = 299792.458
H0_CF4 = 74.6            # zéro des modules de distance de CF4 (Tully et al. 2023) [Probable]
SIGMA_NL = 150.0         # agitation non linéaire résiduelle d'un groupe, km/s [Supposition, valeur courante]
LISSAGE = 5.0            # Mpc/h, coupe les échelles non linéaires du modèle [Supposition]
COTE, NGRILLE = 1000.0, 64
RAW = os.path.join(os.environ['LOCALAPPDATA'], 'univers-raw')


def lire_groupes(cz_max: float) -> dict:
    """Lit la table des groupes (VizieR J/ApJ/944/94/groups, tsv) ; positions supergalactiques en Mpc/h."""
    chemin = os.path.join(RAW, 'cf4groupes', 'groupes.tsv')
    lignes = [l for l in open(chemin, encoding='utf-8') if not l.startswith('#') and l.strip()]
    entete = lignes[0].rstrip('\n').split('\t')
    col = {n: i for i, n in enumerate(entete)}
    dm, edm, cz, sgl, sgb = [], [], [], [], []
    for l in lignes[3:]:
        c = l.rstrip('\n').split('\t')
        try:
            vals = [float(c[col[n]]) for n in ('DMzp', 'e_DMav', 'Vcmb', 'SGL', 'SGB')]
        except ValueError:
            continue
        if vals[0] <= 0 or vals[1] <= 0:
            continue
        for lst, v in zip((dm, edm, cz, sgl, sgb), vals):
            lst.append(v)
    dm, edm, cz, sgl, sgb = map(np.array, (dm, edm, cz, sgl, sgb))
    garde = cz < cz_max
    dm, edm, cz, sgl, sgb = dm[garde], edm[garde], cz[garde], sgl[garde], sgb[garde]

    d_l = 10.0 ** ((dm - 25.0) / 5.0)                                  # Mpc, distance de luminosité
    q0 = 0.5 * PLANCK18['omega_m'] - (1.0 - PLANCK18['omega_m'])
    # d_L ≈ (c z / H0)(1 + (1 − q0) z / 2) : on résout pour z_cos (z < 0,05)
    a = (1.0 - q0) / 2.0
    x = d_l * H0_CF4 / C_KMS
    z_cos = (-1.0 + np.sqrt(1.0 + 4.0 * a * x)) / (2.0 * a)
    z_obs = cz / C_KMS
    u = C_KMS * (z_obs - z_cos) / (1.0 + z_cos)                       # Davis & Scrimgeour 2014
    d_com = d_l / (1.0 + z_cos) * H0_CF4 / 100.0                       # Mpc/h, comobile
    err = np.log(10.0) / 5.0 * edm * H0_CF4 * d_l / (1.0 + z_cos)
    l, b = np.radians(sgl), np.radians(sgb)
    n = np.stack([np.cos(b) * np.cos(l), np.cos(b) * np.sin(l), np.sin(b)], axis=1)
    return dict(pos=n * d_com[:, None], n=n, u=u, err=err, d=d_com)


def covariance_donnees(g: dict, corr: CorrelationVitesses) -> np.ndarray:
    pos, n = g['pos'], g['n']
    nb = len(pos)
    c = np.empty((nb, nb))
    for i0 in range(0, nb, 2000):
        dx = pos[i0:i0 + 2000, None, :] - pos[None, :, :]
        r = np.linalg.norm(dx, axis=2)
        par, perp = corr(r)
        with np.errstate(invalid='ignore', divide='ignore'):
            rh = np.where(r[..., None] > 0, dx / r[..., None], 0.0)
        ni = n[i0:i0 + 2000, None, :]
        nj = n[None, :, :]
        c[i0:i0 + 2000] = perp * np.sum(ni * nj, axis=2) + (par - perp) * np.sum(ni * rh, axis=2) * np.sum(nj * rh, axis=2)
    return c


def vitesses_grille(points: np.ndarray, g: dict, w: np.ndarray, corr: CorrelationVitesses) -> np.ndarray:
    v = np.zeros((len(points), 3))
    for i0 in range(0, len(points), 400):
        dx = points[i0:i0 + 400, None, :] - g['pos'][None, :, :]
        r = np.linalg.norm(dx, axis=2)
        par, perp = corr(r)
        with np.errstate(invalid='ignore', divide='ignore'):
            rh = np.where(r[..., None] > 0, dx / r[..., None], 0.0)
        rn = np.sum(rh * g['n'][None, :, :], axis=2)
        v[i0:i0 + 400] = (perp * w[None, :]) @ g['n'] + np.einsum('pj,pja->pa', (par - perp) * rn * w[None, :], rh)
    return v


def main() -> None:
    cz_max = float(sys.argv[1]) if len(sys.argv) > 1 else 8000.0
    t0 = time.time()
    g = lire_groupes(cz_max)
    print(f'groupes gardés : {len(g["u"])} (cz < {cz_max:.0f} km/s) ; vitesse moyenne {g["u"].mean():.0f} km/s')
    corr = CorrelationVitesses(Spectre(), taux_croissance(), lissage=LISSAGE)
    cov = covariance_donnees(g, corr)
    cov[np.diag_indices_from(cov)] += g['err'] ** 2 + SIGMA_NL ** 2
    w = cho_solve(cho_factor(cov, lower=True), g['u'])
    print(f'filtre résolu en {time.time() - t0:.0f} s')

    # Grille de Courtois 2023 : cube de 1000 Mpc/h, observateur au centre ; on ne calcule que r < 100 Mpc/h.
    centres = -COTE / 2 + (np.arange(NGRILLE) + 0.5) * COTE / NGRILLE
    gx, gy, gz = np.meshgrid(centres, centres, centres, indexing='ij')
    pts = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1)
    dedans = np.linalg.norm(pts, axis=1) < 100.0
    v = vitesses_grille(pts[dedans], g, w, corr)
    print(f'vitesses sur {dedans.sum()} cases en {time.time() - t0:.0f} s')

    ref = fits.getdata(os.path.join(RAW, 'cf4grid', 'CF4_new_64-z008_velocity.fits')).astype(float)
    # Ordre des axes du fichier : on teste les 6 permutations et les signes, on garde la meilleure (contrôle d'orientation).
    import itertools
    meilleur = None
    for perm in itertools.permutations(range(3)):
        refp = np.transpose(ref, (0,) + tuple(1 + p for p in perm)).reshape(3, -1)[:, dedans]
        for comp in itertools.permutations(range(3)):
            cc = [np.corrcoef(v[:, a], refp[comp[a]])[0, 1] for a in range(3)]
            s = np.mean(np.abs(cc))
            if meilleur is None or s > meilleur[0]:
                meilleur = (s, perm, comp, cc)
    s, perm, comp, cc = meilleur
    print(f'corrélation avec Courtois 2023 (r < 100 Mpc/h) : SGX {cc[0]:+.3f}  SGY {cc[1]:+.3f}  SGZ {cc[2]:+.3f}')
    print(f'  axes de grille {perm}, composantes {comp}')
    os.makedirs('resultats', exist_ok=True)
    np.savez_compressed('resultats/cf4_wiener_v1.npz', points=pts[dedans], v=v, w=w, cz_max=cz_max,
                        correlation=np.array(cc), perm=np.array(perm), comp=np.array(comp))


if __name__ == '__main__':
    main()
