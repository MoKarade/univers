"""Réalisations contraintes JOINTES : vitesses de Cosmicflows-4 + densité de 2MRS (CORAS).

Pourquoi : mesuré le 19/11 (graine 1), les vitesses seules laissent l'amas de la Vierge trop faible
(δ = 0,48 dans la réalisation contre 1,56 pour le champ moyen) et le calcul n'en fait pas d'amas.
La densité de 2MRS fixe directement la masse des amas.

Données de densité (modèle signalé) :
  - champ de CORAS (Lilow & Nusser 2021), « contraste normalisé » δ/σ8 lissé 5 Mpc/h, repère galactique [Certain, README] ;
    converti en δ = valeur × σ8 [À vérifier : convention exacte du facteur] ;
  - ramené au régime linéaire par l'effondrement sphérique inversé (Bernardeau 1994) :
    δ_L = 3/2 [1 − (1 + δ)^(−2/3)] [Probable : approximation publiée, bonne à ~10 % pour |δ_L| < 1,5] ;
  - points tous les PAS_D Mpc/h dans r < R_D, bruit SIGMA_D [Supposition : réglage, mesuré par le contrôle χ²].
Le champ de CORAS est lui-même une estimation (filtre de Wiener) : l'utiliser comme donnée est une approximation.

Usage : python realisations_jointes.py GRAINE [N_GRILLE=256] [COTE=640]   (écrit resultats/rcj_<graine>.npz)
"""
import os
import sys
import time

import numpy as np
from scipy.linalg import cho_factor, cho_solve

import cf4_wiener as w
import realisations as r
from comparer_2mrs import lire_coras
from cosmo_lineaire import PLANCK18, CorrelationDensite

PAS_D = float(os.environ.get('PAS_D', '8'))
R_D = float(os.environ.get('R_D', '80'))
SIGMA_D = float(os.environ.get('SIGMA_D', '0.3'))


def gal_vers_sg(x: np.ndarray) -> np.ndarray:
    from astropy.coordinates import SkyCoord
    c = SkyCoord(u=x[:, 0], v=x[:, 1], w=x[:, 2], frame='galactic', representation_type='cartesian').supergalactic
    c.representation_type = 'cartesian'
    return np.stack([c.sgx.value, c.sgy.value, c.sgz.value], axis=1)


def donnees_densite() -> dict:
    d = lire_coras('cartesian_grid_density_zCMB', 1) * PLANCK18['sigma8']
    ax = np.arange(-R_D, R_D + 1e-6, PAS_D)
    gx, gy, gz = np.meshgrid(ax, ax, ax, indexing='ij')
    p_gal = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1)
    p_gal = p_gal[np.linalg.norm(p_gal, axis=1) <= R_D]
    i = np.round((p_gal + 200.0) / 2.0).astype(int)
    dnl = d[i[:, 0], i[:, 1], i[:, 2]].astype(float)
    dl = 1.5 * (1.0 - np.maximum(1.0 + dnl, 0.05) ** (-2.0 / 3.0))
    return dict(pos=gal_vers_sg(p_gal), delta=dl, delta_nl=dnl)


class FiltreJoint(r.Filtre):
    def __init__(self, g: dict, dens: dict, n: int, cote: float):
        self.dens = dens
        super().__init__(g, n, cote)

    def factoriser(self):
        self.cd = CorrelationDensite(self.spectre, self.f, lissage=w.LISSAGE)
        g, dd = self.g, self.dens
        nv, nd = len(g['u']), len(dd['delta'])
        cov = np.empty((nv + nd, nv + nd))
        cvv = w.covariance_donnees(g, self.corr)
        cvv[np.diag_indices_from(cvv)] += g['err'] ** 2 + w.SIGMA_NL ** 2
        cov[:nv, :nv] = cvv
        # densité-densité
        rr = np.linalg.norm(dd['pos'][:, None, :] - dd['pos'][None, :, :], axis=2)
        cdd = self.cd(rr)[0]
        cdd[np.diag_indices_from(cdd)] += SIGMA_D ** 2
        cov[nv:, nv:] = cdd
        # densité (x_k) - vitesse radiale (x_j) : −f H (n_j · r̂) g(r), r = x_j − x_k
        dx = g['pos'][None, :, :] - dd['pos'][:, None, :]
        rn = np.linalg.norm(dx, axis=2)
        with np.errstate(invalid='ignore', divide='ignore'):
            proj = np.where(rn > 0, np.sum(dx * g['n'][None, :, :], axis=2) / rn, 0.0)
        cdv = -100.0 * self.f * proj * self.cd(rn)[1]
        cov[nv:, :nv] = cdv
        cov[:nv, nv:] = cdv.T
        self.nv = nv
        self.chol = cho_factor(cov, lower=True)

    def vecteur(self, u: np.ndarray, d: np.ndarray) -> np.ndarray:
        return np.concatenate([u, d])

    def densite_wf(self, donnees: np.ndarray) -> np.ndarray:
        wt = cho_solve(self.chol, donnees)
        wv, wd = wt[:self.nv], wt[self.nv:]
        kx, ky, kz, k2 = self.kv
        num = 0.0
        for a, kk in enumerate((kx, ky, kz)):
            s = np.fft.rfftn(r.deposer(self.g['pos'], wv * self.g['n'][:, a], self.n, self.cote))
            num = num + kk * s
        part_v = -1j * 100.0 * self.f * self.pk * self.lisse * num / k2
        part_d = self.pk * self.lisse * np.fft.rfftn(r.deposer(self.dens['pos'], wd, self.n, self.cote))
        return (part_v + part_d) / self.cote ** 3 * self.n ** 3

    def densites(self, dk: np.ndarray) -> np.ndarray:
        champ = np.fft.irfftn(dk * self.lisse, s=(self.n,) * 3, axes=(0, 1, 2))
        return r.interpoler(champ, self.dens['pos'], self.cote)


def main() -> None:
    graine = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 256
    cote = float(sys.argv[3]) if len(sys.argv) > 3 else 640.0
    t0 = time.time()
    os.environ.setdefault('MONOPOLE', '1')
    g = w.lire_groupes(r.CZ_MAX)
    dd = donnees_densite()
    print(f'{len(g["u"])} vitesses + {len(dd["delta"])} densités (pas {PAS_D:g}, r < {R_D:g} Mpc/h, bruit {SIGMA_D:g})')
    filt = FiltreJoint(g, dd, n, cote)
    donnees = filt.vecteur(g['u'], dd['delta'])
    # Zel'dovich inverse pour les deux jeux de points
    v = r.vitesse_depuis_densite(filt.densite_wf(donnees), filt.kv, filt.f)
    depl_g = np.stack([r.interpoler(v[a], g['pos'], cote) for a in range(3)], axis=1) / (100.0 * filt.f)
    depl_d = np.stack([r.interpoler(v[a], dd['pos'], cote) for a in range(3)], axis=1) / (100.0 * filt.f)
    g = dict(g, pos=g['pos'] - depl_g)
    dd = dict(dd, pos=dd['pos'] - depl_d)
    filt = FiltreJoint(g, dd, n, cote)
    print(f'Zel\'dovich inverse : médiane {np.median(np.linalg.norm(depl_g, axis=1)):.1f} Mpc/h ; '
          f'filtre prêt en {time.time() - t0:.0f} s')

    rng = np.random.default_rng(graine + 10_000)
    dh = filt.hasard(graine)
    bruit_v = rng.standard_normal(len(g['u'])) * np.sqrt(g['err'] ** 2 + w.SIGMA_NL ** 2)
    bruit_d = rng.standard_normal(len(dd['delta'])) * SIGMA_D
    pred_h = filt.vecteur(filt.radiales(dh) + bruit_v, filt.densites(dh) + bruit_d)
    dcr = dh + filt.densite_wf(donnees - pred_h)
    u_cr, d_cr = filt.radiales(dcr), filt.densites(dcr)
    chi_v = np.mean((u_cr - g['u']) ** 2 / (g['err'] ** 2 + w.SIGMA_NL ** 2))
    chi_d = np.mean((d_cr - dd['delta']) ** 2 / SIGMA_D ** 2)
    print(f'contrôle données : χ²/N vitesses {chi_v:.2f}, densités {chi_d:.2f} ; corrélation densité CR / 2MRS '
          f'{np.corrcoef(d_cr, dd["delta"])[0, 1]:.3f}')
    # Vierge : position de Lagrange approchée (même déplacement que les groupes voisins)
    h = 0.746
    lv, bv = np.radians(102.9), np.radians(-2.3)
    vierge = 16.5 * h * np.array([np.cos(bv) * np.cos(lv), np.cos(bv) * np.sin(lv), np.sin(bv)])
    vv = np.array([r.interpoler(v[a], vierge[None], cote)[0] for a in range(3)]) / (100.0 * filt.f)
    champ = np.fft.irfftn(dcr * filt.lisse, s=(n,) * 3, axes=(0, 1, 2))
    print(f'Vierge (Lagrange) : δ_L lissé de la réalisation {r.interpoler(champ, (vierge - vv)[None], cote)[0]:.2f}')
    pm = r.spectre_mesure(dcr, filt.kv, cote, n)
    print('spectre mesuré / P(k) :', ' '.join(f'{x:.2f}' for x in pm[:, 1] / filt.spectre(pm[:, 0])))
    np.savez_compressed(f'resultats/rcj_{graine}.npz', delta_k=dcr.astype(np.complex64), n=n, cote=cote,
                        graine=graine, rza=True, sigma_d=SIGMA_D, pas_d=PAS_D, r_d=R_D)
    print(f'écrit resultats/rcj_{graine}.npz en {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
