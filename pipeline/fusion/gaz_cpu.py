#!/usr/bin/env python3
"""Gaz sur le processeur : jumeau exact de gaz_gpu.sph, pour contrôler la physique du gaz sans la carte graphique.

Pourquoi : la carte graphique est prise par le grand calcul pendant des jours (24/11/2026) ; les contrôles du gaz
(explosion de Sedov, refroidissement, explosions d'étoiles) doivent pouvoir tourner à petite taille sur le processeur.
Une fois la carte libre, essai_gaz_physique.py compare ce jumeau à gaz_gpu.sph sur les mêmes particules : s'ils donnent
la même chose, les contrôles faits ici valent pour le calcul.

Mêmes équations que gaz_gpu.py (lu le 24/11/2026, branche film-3) [Certain pour la correspondance, ligne à ligne] :
- noyau spline cubique (Monaghan & Lattanzio 1985), support 2h ;
- densité rho_i = somme_j m_j W(r_ij, h_i) (la particule elle-même comprise) ; h = ETA (m / rho)^(1/3), ETA = 1,2,
  mise à jour par moyenne avec l'ancien h, bornée par h_min, h_max ;
- divergence et rotationnel de la vitesse à la manière du noyau `densite` (interrupteur de Balsara 1995) ;
- forces : a_i = - somme_j m_j (P_i/rho_i² + P_j/rho_j² + Pi_ij) grad W_ij, noyau moyen (dW(h_i) + dW(h_j)) / 2,
  paires retenues si r < 2 max(h_i, h_j) ;
- viscosité de Monaghan (alpha = 1, beta = 2), mu = hbar v.r / (r² + 0,01 hbar²), facteur de Balsara moyen ;
- du_i/dt = 1/2 somme_j m_j (P_i/rho_i² + P_j/rho_j² + Pi_ij) v_ij . grad W_ij ;
- vitesse de signal max(c_i, cbar - 3 v.r / r) sur les paires qui se rapprochent.
Différence voulue : tout est en double précision (gaz_gpu calcule en simple précision).

Coût : pour des contrôles (≤ ~50 000 particules), pas pour le calcul de production.
"""
import numpy as np
from scipy.spatial import cKDTree

ETA = 1.2
ALPHA, BETA = 1.0, 2.0


def _W(r, h):
    q = r / h
    s = 1.0 / (np.pi * h ** 3)
    return s * np.where(q < 1.0, 1.0 - 1.5 * q ** 2 + 0.75 * q ** 3, np.where(q < 2.0, 0.25 * (2.0 - q) ** 3, 0.0))


def _dW(r, h):
    q = r / h
    s = 1.0 / (np.pi * h ** 4)
    return s * np.where(q < 1.0, -3.0 * q + 2.25 * q ** 2, np.where(q < 2.0, -0.75 * (2.0 - q) ** 2, 0.0))


def _voisines(arbre, pos, rayon):
    """Paires orientées (i, j) avec |x_i - x_j| < rayon_i (i == j compris). Rend deux tableaux d'indices."""
    listes = arbre.query_ball_point(pos, rayon, return_sorted=False)
    nb = np.fromiter((len(l) for l in listes), dtype=np.int64, count=len(listes))
    i = np.repeat(np.arange(len(listes)), nb)
    j = np.fromiter((k for l in listes for k in l), dtype=np.int64, count=int(nb.sum()))
    return i, j


def _somme(i, valeurs, n):
    """Somme par particule i (valeurs scalaires ou vecteurs (k, 3))."""
    if valeurs.ndim == 1:
        return np.bincount(i, weights=valeurs, minlength=n)
    return np.stack([np.bincount(i, weights=valeurs[:, a], minlength=n) for a in range(valeurs.shape[1])], 1)


def densite(pos, vel, m, h):
    """Densité, nombre de voisines, divergence et rotationnel (comme le noyau `densite` de gaz_gpu)."""
    n = len(pos)
    arbre = cKDTree(pos)
    i, j = _voisines(arbre, pos, 2.0 * h * (1.0 - 1e-12))
    d = pos[i] - pos[j]
    r = np.sqrt((d ** 2).sum(1))
    rho = _somme(i, m[j] * _W(r, h[i]), n)
    nv = np.bincount(i, minlength=n)
    ok = r > 0
    g = np.zeros_like(r)
    g[ok] = m[j[ok]] * _dW(r[ok], h[i[ok]]) / r[ok]
    u = vel[j] - vel[i]
    dv = _somme(i, g * (u * d).sum(1), n)
    rot = _somme(i, g[:, None] * np.cross(u, d), n)
    return rho, nv, dv / rho, np.sqrt((rot ** 2).sum(1)) / rho


def sph(pos, vel, m, h, u=None, cs=None, gamma=5.0 / 3.0, h_min=0.0, h_max=np.inf, passes=3, energie='monaghan'):
    """Même interface et mêmes sorties que gaz_gpu.sph, avec des tableaux numpy en double précision.

    energie : forme de du/dt.
    - 'moyenne' (celle de gaz_gpu.py au 24/11/2026) : du_i/dt = 1/2 somme_j m_j (P_i/rho_i² + P_j/rho_j² + Pi_ij) v_ij.gradW.
      Une particule froide voisine d'une particule très chaude perd alors de l'énergie au nom de la pression de sa voisine
      et passe sous zéro ; le plancher qui la remet à zéro CRÉE de l'énergie (mesuré le 24/11 : +6,6 % sur l'explosion
      de Sedov, tout entier dû au plancher).
    - 'monaghan' (défaut) : du_i/dt = somme_j m_j (P_i/rho_i² + Pi_ij/2) v_ij.gradW (Monaghan 1992, ARA&A 30, 543 ;
      forme de GADGET-2 en énergie). L'énergie totale est conservée de la même façon (échange i <-> j), mais chaque
      particule ne travaille qu'avec sa propre pression : elle ne peut pas devenir négative par la faute d'une voisine."""
    if (u is None) == (cs is None):
        raise ValueError('donner soit u (gaz adiabatique), soit cs (gaz isotherme)')
    if energie not in ('moyenne', 'monaghan'):
        raise ValueError(f"forme d'énergie inconnue : {energie}")
    pos = np.asarray(pos, float); vel = np.asarray(vel, float); m = np.asarray(m, float)
    n = len(pos)
    hs = np.asarray(h, float).copy() * np.ones(n)
    for it in range(passes):
        rho, nv, dv, rv = densite(pos, vel, m, hs)
        if it < passes - 1:
            cible = ETA * (m / rho) ** (1.0 / 3.0)
            hs = np.clip(0.5 * (hs + cible), h_min, h_max)
    if cs is None:
        us = np.maximum(np.asarray(u, float), 0.0)
        P = (gamma - 1.0) * rho * us
        son = np.sqrt(gamma * (gamma - 1.0) * us)
    else:
        son = np.full(n, float(cs)) if np.isscalar(cs) else np.asarray(cs, float)
        P = rho * son * son
    pr = P / (rho * rho)
    bal = np.abs(dv) / (np.abs(dv) + rv + 1e-4 * son / hs)
    # paires (i, j), i != j, r < 2 max(h_i, h_j) : on prend r < 2 h_i et son symétrique, sans doublon
    arbre = cKDTree(pos)
    i, j = _voisines(arbre, pos, 2.0 * hs * (1.0 - 1e-12))
    cle = np.unique(np.concatenate([i * n + j, j * n + i]))
    i, j = cle // n, cle % n
    garde = i != j
    garde &= ((pos[i] - pos[j]) ** 2).sum(1) > 0      # deux particules confondues : sautées, comme sur la carte
    i, j = i[garde], j[garde]
    d = pos[i] - pos[j]
    r2 = (d ** 2).sum(1); r = np.sqrt(r2)
    g = 0.5 * (_dW(r, hs[i]) + _dW(r, hs[j])) / r
    uij = vel[i] - vel[j]
    vr = (uij * d).sum(1)
    hbar = 0.5 * (hs[i] + hs[j])
    mu = hbar * vr / (r2 + 0.01 * hbar ** 2)
    cbar = 0.5 * (son[i] + son[j]); rbar = 0.5 * (rho[i] + rho[j])
    proche = vr < 0
    visc = np.where(proche, (-ALPHA * cbar * mu + BETA * mu * mu) / rbar * 0.5 * (bal[i] + bal[j]), 0.0)
    f = m[j] * (pr[i] + pr[j] + visc) * g
    acc = -_somme(i, f[:, None] * d, n)
    if energie == 'moyenne':
        du = _somme(i, 0.5 * f * vr, n)
    else:
        du = _somme(i, m[j] * (pr[i] + 0.5 * visc) * g * vr, n)
    vs = son.copy()
    cand = np.where(proche, cbar - 3.0 * vr / r, -np.inf)
    np.maximum.at(vs, i, cand)
    return dict(acc=acc, dudt=du, rho=rho, h=hs, vsig=vs, divv=dv, nvois=nv)
