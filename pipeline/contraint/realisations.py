"""Réalisations contraintes du champ de densité linéaire (Hoffman & Ribak 1991), avec Zel'dovich inverse
(Doumler et al. 2013), à partir des vitesses de Cosmicflows-4. Cosmologie Planck 2018, énergie noire comprise.

    δ_CR = δ_hasard + δ_WF[ u − (u_hasard + bruit) ]

δ_hasard : champ gaussien tiré au sort avec le vrai P(k) ; u_hasard : ses vitesses radiales (lissées comme le modèle
des données) aux positions des groupes ; δ_WF[.] : filtre de Wiener d'un vecteur de vitesses, calculé par FFT.
Contrôles écrits dans le bilan : (1) la vitesse tirée de δ_WF retrouve le calcul direct de cf4_wiener.py ;
(2) aux positions des groupes, la réalisation reproduit les données au bruit près (χ²/N ~ 1) ;
(3) le spectre de puissance de la réalisation suit P(k).

Usage : python realisations.py GRAINE [N_GRILLE=256] [COTE=640]  (écrit resultats/rc_<graine>.npz)
Mesuré : une boîte de 320 Mpc/h fausse le filtre (corrélation 0,84-0,95, images périodiques) ; 640 donne 0,999.
"""
import os
import sys
import time

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.ndimage import map_coordinates

import cf4_wiener as w
from cosmo_lineaire import CorrelationVitesses, Spectre, taux_croissance

CZ_MAX = 10000.0
RZA = os.environ.get('RZA', '1') == '1'


def grille_k(n: int, cote: float):
    k1 = 2.0 * np.pi * np.fft.fftfreq(n, d=cote / n)
    kz = 2.0 * np.pi * np.fft.rfftfreq(n, d=cote / n)
    kx, ky, kz = np.meshgrid(k1, k1, kz, indexing='ij', sparse=True)
    k2 = kx * kx + ky * ky + kz * kz
    k2[0, 0, 0] = 1.0
    return kx, ky, kz, k2


def vitesse_depuis_densite(dk, kv, f):
    """v(k) = i f H k/k² δ(k), H = 100 (km/s)/(Mpc/h)."""
    kx, ky, kz, k2 = kv
    return [np.fft.irfftn(1j * 100.0 * f * kk / k2 * dk, s=(dk.shape[0],) * 3, axes=(0, 1, 2)) for kk in (kx, ky, kz)]


def interpoler(champ: np.ndarray, pos: np.ndarray, cote: float) -> np.ndarray:
    n = champ.shape[0]
    idx = (pos + cote / 2.0) / (cote / n) - 0.5
    return map_coordinates(champ, idx.T, order=1, mode='grid-wrap')


def deposer(pos: np.ndarray, poids: np.ndarray, n: int, cote: float) -> np.ndarray:
    """Dépôt CIC de poids ponctuels (non divisés par le volume)."""
    g = np.zeros((n, n, n))
    x = (pos + cote / 2.0) / (cote / n) - 0.5
    i0 = np.floor(x).astype(int)
    t = x - i0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                wgt = (np.where(dx, t[:, 0], 1 - t[:, 0]) * np.where(dy, t[:, 1], 1 - t[:, 1])
                       * np.where(dz, t[:, 2], 1 - t[:, 2]))
                np.add.at(g, ((i0[:, 0] + dx) % n, (i0[:, 1] + dy) % n, (i0[:, 2] + dz) % n), wgt * poids)
    return g


class Filtre:
    def __init__(self, g: dict, n: int, cote: float):
        self.g, self.n, self.cote = g, n, cote
        self.f = taux_croissance()
        self.spectre = Spectre()
        self.corr = CorrelationVitesses(self.spectre, self.f, lissage=w.LISSAGE)
        self.kv = grille_k(n, cote)
        k = np.sqrt(self.kv[3])
        self.pk = self.spectre(k)
        self.pk[0, 0, 0] = 0.0
        self.lisse = np.exp(-0.5 * (k * w.LISSAGE) ** 2)          # filtre du champ (P_lissé = P · lisse²)
        self.factoriser()

    def factoriser(self):
        cov = w.covariance_donnees(self.g, self.corr)
        cov[np.diag_indices_from(cov)] += self.g['err'] ** 2 + w.SIGMA_NL ** 2
        self.chol = cho_factor(cov, lower=True)

    def densite_wf(self, u: np.ndarray) -> np.ndarray:
        """δ_WF(k) = −i f H P(k) lisse(k) k·Ŝ(k)/k² · N/V, Ŝ = TF du dépôt de w_j n_j (voir l'en-tête)."""
        wt = cho_solve(self.chol, u)
        kx, ky, kz, k2 = self.kv
        num = 0.0
        for a, kk in enumerate((kx, ky, kz)):
            s = np.fft.rfftn(deposer(self.g['pos'], wt * self.g['n'][:, a], self.n, self.cote))
            num = num + kk * s
        return -1j * 100.0 * self.f * self.pk * self.lisse * num / k2 / self.cote ** 3 * self.n ** 3

    def hasard(self, graine: int) -> np.ndarray:
        rng = np.random.default_rng(graine)
        n, cote = self.n, self.cote
        bruit = np.fft.rfftn(rng.standard_normal((n, n, n)))
        return bruit * np.sqrt(self.pk / cote ** 3) * n ** 1.5          # δ(k) avec <|δ_k|²> = P N²·N/V… normalisé ci-dessous

    def radiales(self, dk: np.ndarray) -> np.ndarray:
        v = vitesse_depuis_densite(dk * self.lisse, self.kv, self.f)
        return sum(interpoler(v[a], self.g['pos'], self.cote) * self.g['n'][:, a] for a in range(3))


def spectre_mesure(dk: np.ndarray, kv, cote: float, n: int):
    k = np.sqrt(kv[3]).ravel()
    p = (np.abs(dk) ** 2).ravel() * cote ** 3 / n ** 6
    bords = np.logspace(np.log10(2 * np.pi / cote), np.log10(np.pi * n / cote), 15)
    i = np.digitize(k, bords)
    return np.array([[k[i == b].mean(), p[i == b].mean()] for b in range(1, len(bords)) if np.any(i == b)])


def main() -> None:
    graine = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 256
    cote = float(sys.argv[3]) if len(sys.argv) > 3 else 640.0
    t0 = time.time()
    os.environ.setdefault('MONOPOLE', '1')
    g = w.lire_groupes(CZ_MAX)
    filt = Filtre(g, n, cote)
    if RZA:
        # Zel'dovich inverse : chaque groupe est ramené à sa position de Lagrange q = x − v_WF(x)/(f H)
        v = vitesse_depuis_densite(filt.densite_wf(g['u']), filt.kv, filt.f)
        v3 = np.stack([interpoler(v[a], g['pos'], cote) for a in range(3)], axis=1)
        depl = v3 / (100.0 * filt.f)
        g = dict(g, pos=g['pos'] - depl)
        filt = Filtre(g, n, cote)
        print(f'Zel\'dovich inverse : déplacement médian {np.median(np.linalg.norm(depl, axis=1)):.1f} Mpc/h, '
              f'max {np.linalg.norm(depl, axis=1).max():.1f}')

    # Contrôle (1) : vitesse du champ moyen contre le calcul direct, aux positions des groupes
    dwf = filt.densite_wf(g['u'])
    u_fft = filt.radiales(dwf)          # vitesse lissée comme le modèle des données (P · lisse²)
    wt = cho_solve(filt.chol, g['u'])
    u_dir = w.vitesses_grille(g['pos'], g, wt, filt.corr)
    u_dir = np.sum(u_dir * g['n'], axis=1)
    print(f'contrôle 1 (FFT contre direct) : corrélation {np.corrcoef(u_fft, u_dir)[0, 1]:.4f}, '
          f'rapport des amplitudes {np.std(u_fft) / np.std(u_dir):.3f}')

    # Réalisation contrainte
    rng = np.random.default_rng(graine + 10_000)
    dh = filt.hasard(graine)
    u_h = filt.radiales(dh) + rng.standard_normal(len(g['u'])) * np.sqrt(g['err'] ** 2 + w.SIGMA_NL ** 2)
    dcr = dh + filt.densite_wf(g['u'] - u_h)
    # Contrôle (2) : la réalisation reproduit les données
    u_cr = filt.radiales(dcr)
    chi2 = np.mean((u_cr - g['u']) ** 2 / (g['err'] ** 2 + w.SIGMA_NL ** 2))
    print(f'contrôle 2 (données) : χ²/N = {chi2:.2f} ; corrélation u_CR / u {np.corrcoef(u_cr, g["u"])[0, 1]:.3f}')
    # Contrôle (3) : spectre
    pm = spectre_mesure(dcr, filt.kv, cote, n)
    rap = pm[:, 1] / filt.spectre(pm[:, 0])
    print('contrôle 3 (spectre mesuré / P(k)) :', ' '.join(f'{x:.2f}' for x in rap))
    os.makedirs('resultats', exist_ok=True)
    np.savez_compressed(f'resultats/rc_{graine}.npz', delta_k=dcr.astype(np.complex64), n=n, cote=cote,
                        graine=graine, rza=RZA)
    print(f'écrit resultats/rc_{graine}.npz en {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
