#!/usr/bin/env python3
"""Champ de gravité d'une galaxie mis en coefficients (étape 8 du plan B+, docs/refonte-simulations-pro.md § 4.2).

But : donner aux étoiles mesurées (Gaia) la gravité du calcul N-corps à chaque image, sans rejouer ses millions de
particules. À chaque image, le film appelle `coefficients(pos, m, kind, ...)` pour chaque galaxie ; l'appli (et
`evaluer`) en tire le potentiel et la force n'importe où.

Méthode (celle d'AGAMA, Vasiliev 2019, MNRAS 482, 1525 : « Multipole » pour les composantes rondes, « CylSpline » pour
les disques ; écrite ici sans AGAMA pour tourner partout et pour que l'évaluateur C++ fasse exactement le même calcul) :
- halo, bulbe, et particules de disque hors de la boîte du disque : **développement multipolaire** jusqu'à l = lmax
  (harmoniques sphériques réelles), Φ_lm(r) et dΦ_lm/dr EXACTS aux nœuds (sommes intérieures et extérieures sur les
  particules), interpolation de Hermite cubique en ln r entre les nœuds ;
- disque (étoiles et gaz) dans sa boîte : **harmoniques azimutales** m = 0…mmax sur une grille (R, z) resserrée près
  du centre et du plan ; Φ_m(R, z) = −G Σ (masses déposées) × noyau exact de 1/|x − x'| (fonctions de Legendre
  Q_{m−1/2}, intégrales elliptiques ; adoucissement de Plummer ε) ; interpolation bicubique de Hermite ;
- hors de la boîte : le disque est pris par un second développement multipolaire.

Unités : kpc, M☉, km/s ; G = 4,30091e-6 ; potentiel en (km/s)², force en (km/s)²/kpc.

Ce qui est mesuré et ce qui ne l'est pas : rien n'est mesuré ici ; c'est une représentation du champ des particules du
calcul, dont la précision est contrôlée par test_champ.py contre des potentiels exacts et contre la somme directe.
"""
import json
import math
import os

import numpy as np
from scipy.interpolate import RectBivariateSpline
from scipy.special import ellipe, ellipk

G = 4.30091e-6
VERSION = 1

# Réglages par défaut [Supposition, contrôlés par test_champ.py]
LMAX = 8                 # multipôles du halo (déformé par les marées) et du disque vu de loin
NR_MULT = 72             # nœuds radiaux des multipôles
MMAX = 6                 # harmoniques azimutales du disque (m = 2 : barre et bras ; 1 : dissymétrie ; jusqu'à 6)
NR, NZ = 41, 41          # nœuds de la grille (R, z) du disque
NCR, NCZ = 96, 96        # cellules de dépôt des masses du disque
ALPHA_R, ALPHA_Z = 3.0, 6.0      # resserrement des nœuds près du centre et du plan
BOITE_R, BOITE_Z = 12.0, 6.0     # demi-tailles de la boîte, en unités de l'échelle λ du disque
EPS = 0.005              # adoucissement, en unités de λ (0,02 lissait trop un disque mince : 4 % d’erreur au centre)
N_MULT_MAX = 1_000_000   # particules au plus pour les multipôles (tirage fixe, masses remises à l’échelle) ; le bruit du halo suit 1/√N
DISQUE = (1, 3, 4)       # kind : 1 disque mince, 3 gaz, 4 disque épais ; 0 halo et 2 bulbe vont aux multipôles


# ------------------------------------------------------------------ harmoniques sphériques réelles
def nb_harm(lmax):
    return (lmax + 1) ** 2


def legendre(lmax, ct, st):
    """P̄_lm(cos θ) normalisés (∫ Y² dΩ = 1, sans phase de Condon–Shortley) et sin θ · dP̄_lm/dθ.
    Rend deux dictionnaires {(l, m): tableau}."""
    P, D = {}, {}
    P[(0, 0)] = np.full_like(ct, 1 / math.sqrt(4 * math.pi))
    for m in range(0, lmax + 1):
        if m > 0:
            P[(m, m)] = math.sqrt((2 * m + 1) / (2 * m)) * st * P[(m - 1, m - 1)]
        if m + 1 <= lmax:
            P[(m + 1, m)] = math.sqrt(2 * m + 3) * ct * P[(m, m)]
        for l in range(m + 2, lmax + 1):
            a = math.sqrt((4 * l * l - 1) / (l * l - m * m))
            b = math.sqrt(((l - 1) ** 2 - m * m) / (4 * (l - 1) ** 2 - 1))
            P[(l, m)] = a * (ct * P[(l - 1, m)] - b * P[(l - 2, m)])
    for l in range(lmax + 1):
        for m in range(l + 1):
            d = l * ct * P[(l, m)]
            if l > m:
                d = d - math.sqrt((2 * l + 1) / (2 * l - 1) * (l * l - m * m)) * P[(l - 1, m)]
            D[(l, m)] = d
    return P, D


def harmoniques(lmax, ct, st, phi, derivees=False):
    """Y_h, h = l² + (0 pour m = 0 ; 2m − 1 cos ; 2m sin). Avec derivees : aussi sin θ ∂Y/∂θ et ∂Y/∂φ."""
    P, D = legendre(lmax, ct, st)
    n = nb_harm(lmax)
    Y = np.empty((n,) + ct.shape)
    if derivees:
        Yt, Yp = np.empty_like(Y), np.empty_like(Y)
    r2 = math.sqrt(2)
    cs = [(np.cos(m * phi), np.sin(m * phi)) for m in range(lmax + 1)]
    for l in range(lmax + 1):
        b = l * l
        Y[b] = P[(l, 0)]
        if derivees:
            Yt[b], Yp[b] = D[(l, 0)], 0.0
        for m in range(1, l + 1):
            c, s = cs[m]
            Y[b + 2 * m - 1], Y[b + 2 * m] = r2 * P[(l, m)] * c, r2 * P[(l, m)] * s
            if derivees:
                Yt[b + 2 * m - 1], Yt[b + 2 * m] = r2 * D[(l, m)] * c, r2 * D[(l, m)] * s
                Yp[b + 2 * m - 1], Yp[b + 2 * m] = -m * r2 * P[(l, m)] * s, m * r2 * P[(l, m)] * c
    return (Y, Yt, Yp) if derivees else Y


def _l_de_h(lmax):
    return np.array([l for l in range(lmax + 1) for _ in range(2 * l + 1)])


def _spheriques(p):
    r = np.linalg.norm(p, axis=1)
    rs = np.maximum(r, 1e-30)
    ct = np.clip(p[:, 2] / rs, -1, 1)
    st = np.sqrt(np.maximum(0, 1 - ct * ct))
    return r, ct, st, np.arctan2(p[:, 1], p[:, 0])


def multipole(p, m, lmax=LMAX, nr=NR_MULT):
    """Coefficients multipolaires des particules (p : (N, 3) kpc, m : (N,) M☉). Rend dict(r, phi, dphi, lmax)."""
    out = dict(lmax=lmax)
    if len(p) == 0:
        out.update(r=np.geomspace(1e-2, 1e3, nr), phi=np.zeros((nr, nb_harm(lmax))), dphi=np.zeros((nr, nb_harm(lmax))))
        return out
    r, ct, st, ph = _spheriques(p)
    rpos = r[r > 0]
    r_lo = max(float(np.quantile(rpos, 0.001)) * 0.5, 1e-3)
    r_hi = float(r.max()) * 1.001
    rg = np.geomspace(r_lo, r_hi, nr)
    # intervalle de chaque particule entre les nœuds : 0 = sous rg[0], k = entre rg[k-1] et rg[k] ; les sommes
    # intérieures et extérieures aux nœuds sont alors exactes, sans tri (une somme par intervalle, puis cumul)
    iv = np.searchsorted(rg, r, side='right')
    Y = harmoniques(lmax, ct, st, ph)
    lh = _l_de_h(lmax)
    rr = np.maximum(r, 1e-12)
    lr = np.log(rr)
    phi = np.empty((nr, len(lh)))
    dphi = np.empty((nr, len(lh)))
    for h, l in enumerate(lh):
        w_in = np.bincount(iv, m * np.exp(l * lr) * Y[h], nr + 1)
        w_out = np.bincount(iv, m * np.exp(-(l + 1) * lr) * Y[h], nr + 1)
        s_in = np.cumsum(w_in)[:nr]                      # particules d'intervalle ≤ k : r_j < rg[k]
        s_out = np.cumsum(w_out[::-1])[::-1][1:]         # intervalle > k : r_j ≥ rg[k]
        c = -4 * math.pi * G / (2 * l + 1)
        phi[:, h] = c * (rg ** (-(l + 1)) * s_in + rg ** l * s_out)
        dphi[:, h] = c * (-(l + 1) * rg ** (-(l + 2)) * s_in + l * rg ** (l - 1) * s_out)
    out.update(r=rg, phi=phi, dphi=dphi)
    return out


def _hermite(t):
    t2, t3 = t * t, t * t * t
    return 2 * t3 - 3 * t2 + 1, t3 - 2 * t2 + t, -2 * t3 + 3 * t2, t3 - t2, \
        6 * t2 - 6 * t, 3 * t2 - 4 * t + 1, -6 * t2 + 6 * t, 3 * t2 - 2 * t


def eval_multipole(M, p):
    """Potentiel et force (N, 3) au point p (repère de la galaxie)."""
    lmax, rg, F, D = M['lmax'], M['r'], M['phi'], M['dphi']
    r, ct, st, ph = _spheriques(p)
    r = np.maximum(r, 1e-9)
    Y, Yt, Yp = harmoniques(lmax, ct, st, ph, derivees=True)
    lh = _l_de_h(lmax)
    lr, lg = np.log(r), np.log(rg)
    i = np.clip(np.searchsorted(lg, lr) - 1, 0, len(rg) - 2)
    hstep = lg[i + 1] - lg[i]
    t = (lr - lg[i]) / hstep
    h00, h10, h01, h11, d00, d10, d01, d11 = _hermite(t)
    f0, f1 = F[i], F[i + 1]                                   # (N, nh)
    g0, g1 = (D[i] * rg[i][:, None]), (D[i + 1] * rg[i + 1][:, None])     # dΦ/dln r
    hs = hstep[:, None]
    Phi_lm = h00[:, None] * f0 + h10[:, None] * hs * g0 + h01[:, None] * f1 + h11[:, None] * hs * g1
    dPhi_lm = (d00[:, None] * f0 + d10[:, None] * hs * g0 + d01[:, None] * f1 + d11[:, None] * hs * g1) / hs / r[:, None]
    dedans, dehors = r < rg[0], r > rg[-1]
    if dedans.any():      # cœur : Φ_lm ∝ r^l (l > 0) ; l = 0 : densité uniforme
        q = r[dedans][:, None] / rg[0]
        L = lh[None, :]
        Phi_lm[dedans] = np.where(L == 0, F[0] + D[0] * rg[0] * (q * q - 1) / 2, F[0] * q ** L)
        dPhi_lm[dedans] = np.where(L == 0, D[0] * q, F[0] * L * q ** np.maximum(L - 1, 0) / rg[0])
    if dehors.any():      # au-delà de la dernière particule : Φ_lm ∝ r^−(l+1), exact
        q = rg[-1] / r[dehors][:, None]
        L = lh[None, :]
        Phi_lm[dehors] = F[-1] * q ** (L + 1)
        dPhi_lm[dehors] = -(L + 1) * F[-1] * q ** (L + 2) / rg[-1]
    Phi = np.sum(Phi_lm * Y.T, axis=1)
    dr = np.sum(dPhi_lm * Y.T, axis=1)
    stc = np.maximum(st, 1e-9)
    dth = np.sum(Phi_lm * Yt.T, axis=1) / stc / r        # (1/r) ∂Φ/∂θ
    dph = np.sum(Phi_lm * Yp.T, axis=1) / stc / r        # (1/(r sin θ)) ∂Φ/∂φ
    cp, sp = np.cos(ph), np.sin(ph)
    er = np.stack([st * cp, st * sp, ct], 1)
    et = np.stack([ct * cp, ct * sp, -st], 1)
    ep = np.stack([-sp, cp, np.zeros_like(cp)], 1)
    grad = dr[:, None] * er + dth[:, None] * et + dph[:, None] * ep
    return Phi, -grad


# ------------------------------------------------------------------ disque : harmoniques azimutales sur grille (R, z)
def noyau_Q(chi, mmax):
    """Q_{m−1/2}(χ) pour m = 0…mmax, χ ≥ 1. Récurrence avant pour χ < 1,5, de Miller (arrière) au-delà
    (contrôlé à 1e-11 près contre la série hypergéométrique, test_champ.py)."""
    chi = np.asarray(chi, float)
    out = np.empty((mmax + 1,) + chi.shape)
    k2 = 2.0 / (chi + 1.0)
    K, E = ellipk(k2), ellipe(k2)
    out[0] = np.sqrt(k2) * K
    if mmax >= 1:
        out[1] = chi * np.sqrt(k2) * K - np.sqrt(2.0 * (chi + 1.0)) * E
    for m in range(1, mmax):
        out[m + 1] = (2 * m * chi * out[m] - (m - 0.5) * out[m - 1]) / (m + 0.5)
    loin = chi >= 1.5
    if loin.any():
        c = chi[loin]
        a, b = np.zeros_like(c), np.full_like(c, 1e-30)
        vals = {}
        for n in range(mmax + 60, 0, -1):
            a, b = b, (2 * n * c * b - (n + 0.5) * a) / (n - 0.5)
            if n - 1 <= mmax:
                vals[n - 1] = b.copy()
            grand = np.abs(b) > 1e200
            if grand.any():
                a[grand] *= 1e-200; b[grand] *= 1e-200
                for v in vals.values():
                    v[grand] *= 1e-200
        sc = out[0][loin] / vals[0]
        for m in range(mmax + 1):
            out[m][loin] = vals[m] * sc
    return out


def grille():
    """Nœuds et cellules, en unités de λ (la grille physique est λ fois celle-ci)."""
    uR = np.linspace(0, 1, NR)
    uz = np.linspace(-1, 1, NZ)
    R = BOITE_R * np.sinh(ALPHA_R * uR) / math.sinh(ALPHA_R)
    z = BOITE_Z * np.sinh(ALPHA_Z * uz) / math.sinh(ALPHA_Z)
    cuR = (np.arange(NCR) + 0.5) / NCR
    cuz = -1 + (np.arange(NCZ) + 0.5) * 2 / NCZ
    cR = BOITE_R * np.sinh(ALPHA_R * cuR) / math.sinh(ALPHA_R)
    cz = BOITE_Z * np.sinh(ALPHA_Z * cuz) / math.sinh(ALPHA_Z)
    return R, z, cR, cz


_CACHE_VERT = {}


def matrice_green():
    """G_m[nœud, cellule] pour λ = 1 : contribution d'une masse unité (anneau pondéré par cos ou sin mφ') au Φ_m du nœud,
    sans le facteur −G. Calculée une fois (~1 min), gardée en mémoire et dans un fichier cache."""
    cle = (NR, NZ, NCR, NCZ, MMAX, ALPHA_R, ALPHA_Z, BOITE_R, BOITE_Z, EPS)
    if cle in _CACHE_VERT:
        return _CACHE_VERT[cle]
    dossier = os.environ.get('CHAMP_CACHE', os.path.join(os.path.expanduser('~'), '.cache', 'univers_champ'))
    nom = os.path.join(dossier, 'green_%d_%d_%d_%d_%d_%g_%g_%g_%g_%g.npy' % cle)
    if os.path.exists(nom):
        Gm = np.load(nom)
    else:
        R, z, cR, cz = grille()
        nR, nZ = np.meshgrid(R, z, indexing='ij'); nR, nZ = nR.ravel(), nZ.ravel()
        cRR, cZZ = np.meshgrid(cR, cz, indexing='ij'); cRR, cZZ = cRR.ravel(), cZZ.ravel()
        Gm = np.zeros((MMAX + 1, len(nR), len(cRR)), np.float32)
        for a in range(len(nR)):
            Rn, zn = nR[a], nZ[a]
            d2 = (zn - cZZ) ** 2 + EPS ** 2
            if Rn == 0:
                Gm[0, a] = 1 / np.sqrt(cRR ** 2 + d2)
                continue
            chi = (Rn * Rn + cRR * cRR + d2) / (2 * Rn * cRR)
            q = noyau_Q(chi, MMAX)
            f = 1 / (math.pi * np.sqrt(Rn * cRR))
            Gm[0, a] = f * q[0]
            for m in range(1, MMAX + 1):
                Gm[m, a] = 2 * f * q[m]
        os.makedirs(dossier, exist_ok=True)
        np.save(nom, Gm)
    _CACHE_VERT[cle] = Gm
    return Gm


def depot(R, z, ph, m, lam):
    """Dépôt des masses en (R, z) (nuage dans la cellule, en coordonnées resserrées) : C_m, S_m par cellule."""
    uR = np.arcsinh(R / (lam * BOITE_R) * math.sinh(ALPHA_R)) / ALPHA_R
    uz = np.arcsinh(z / (lam * BOITE_Z) * math.sinh(ALPHA_Z)) / ALPHA_Z
    xR = np.clip(uR * NCR - 0.5, 0, NCR - 1)
    xz = np.clip((uz + 1) * NCZ / 2 - 0.5, 0, NCZ - 1)
    iR = np.minimum(xR.astype(int), NCR - 2); fR = xR - iR
    iz = np.minimum(xz.astype(int), NCZ - 2); fz = xz - iz
    poids = []
    for dR, wR in ((0, 1 - fR), (1, fR)):
        for dz, wz in ((0, 1 - fz), (1, fz)):
            poids.append(((iR + dR) * NCZ + (iz + dz), wR * wz))
    nc = NCR * NCZ
    C = np.zeros((MMAX + 1, nc)); S = np.zeros((MMAX + 1, nc))
    for mm in range(MMAX + 1):
        c = m * np.cos(mm * ph); s = m * np.sin(mm * ph)
        for idx, w in poids:
            C[mm] += np.bincount(idx, c * w, nc)
            if mm:
                S[mm] += np.bincount(idx, s * w, nc)
    return C, S


def _tables_bicubiques(R, z, F):
    """Φ, ∂Φ/∂R, ∂Φ/∂z, ∂²Φ/∂R∂z aux nœuds (spline bicubique passant par les nœuds)."""
    sp = RectBivariateSpline(R, z, F, kx=3, ky=3, s=0)
    return np.stack([F, sp(R, z, dx=1), sp(R, z, dy=1), sp(R, z, dx=1, dy=1)])


def cylindre(R, z, ph, m, lam):
    Gm = matrice_green()
    C, S = depot(R, z, ph, m, lam)
    gR, gz, _, _ = grille()
    gR, gz = gR * lam, gz * lam
    tab = np.zeros((2 * MMAX + 1, 4, NR, NZ))
    for mm in range(MMAX + 1):
        Fc = (-G / lam) * ((Gm[mm] @ C[mm].astype(np.float32)).astype(np.float64)).reshape(NR, NZ)
        tab[2 * mm - 1 if mm else 0] = _tables_bicubiques(gR, gz, Fc)
        if mm:
            Fs = (-G / lam) * ((Gm[mm] @ S[mm].astype(np.float32)).astype(np.float64)).reshape(NR, NZ)
            tab[2 * mm] = _tables_bicubiques(gR, gz, Fs)
    return dict(lam=lam, R=gR, z=gz, mmax=MMAX, tab=tab)


def eval_cylindre(Cy, p):
    gR, gz, tab, mmax = Cy['R'], Cy['z'], Cy['tab'], Cy['mmax']
    R = np.hypot(p[:, 0], p[:, 1]); z = p[:, 2]; ph = np.arctan2(p[:, 1], p[:, 0])
    i = np.clip(np.searchsorted(gR, R) - 1, 0, len(gR) - 2)
    k = np.clip(np.searchsorted(gz, z) - 1, 0, len(gz) - 2)
    hR = gR[i + 1] - gR[i]; hz = gz[k + 1] - gz[k]
    t = (R - gR[i]) / hR; u = (z - gz[k]) / hz
    a = _hermite(t); b = _hermite(u)
    Ha = [a[0], a[1] * hR, a[2], a[3] * hR]; dHa = [a[4] / hR, a[5], a[6] / hR, a[7]]
    Hb = [b[0], b[1] * hz, b[2], b[3] * hz]; dHb = [b[4] / hz, b[5], b[6] / hz, b[7]]
    # coins : (i, k) (i+1, k) (i, k+1) (i+1, k+1) ; valeurs F, F_R, F_z, F_Rz
    def interp(T, HA, HB):
        f = lambda di, dk, c: T[c, i + di, k + dk]
        return (HA[0] * HB[0] * f(0, 0, 0) + HA[1] * HB[0] * f(0, 0, 1) + HA[0] * HB[1] * f(0, 0, 2) + HA[1] * HB[1] * f(0, 0, 3)
                + HA[2] * HB[0] * f(1, 0, 0) + HA[3] * HB[0] * f(1, 0, 1) + HA[2] * HB[1] * f(1, 0, 2) + HA[3] * HB[1] * f(1, 0, 3)
                + HA[0] * HB[2] * f(0, 1, 0) + HA[1] * HB[2] * f(0, 1, 1) + HA[0] * HB[3] * f(0, 1, 2) + HA[1] * HB[3] * f(0, 1, 3)
                + HA[2] * HB[2] * f(1, 1, 0) + HA[3] * HB[2] * f(1, 1, 1) + HA[2] * HB[3] * f(1, 1, 2) + HA[3] * HB[3] * f(1, 1, 3))
    Phi = np.zeros(len(p)); dR = np.zeros(len(p)); dz = np.zeros(len(p)); dph = np.zeros(len(p))
    for h in range(2 * mmax + 1):
        T = tab[h]
        v, vR, vz = interp(T, Ha, Hb), interp(T, dHa, Hb), interp(T, Ha, dHb)
        if h == 0:
            ang, dang = 1.0, 0.0
        else:
            mm = (h + 1) // 2
            ang = np.cos(mm * ph) if h % 2 else np.sin(mm * ph)
            dang = -mm * np.sin(mm * ph) if h % 2 else mm * np.cos(mm * ph)
        Phi += v * ang; dR += vR * ang; dz += vz * ang; dph += v * dang
    Rs = np.maximum(R, 1e-9)
    cp, sp = np.cos(ph), np.sin(ph)
    gx = dR * cp - dph / Rs * sp
    gy = dR * sp + dph / Rs * cp
    return Phi, -np.stack([gx, gy, dz], 1)


def dans_boite(Cy, p):
    return (np.hypot(p[:, 0], p[:, 1]) < Cy['R'][-1]) & (np.abs(p[:, 2]) < Cy['z'][-1])


# ------------------------------------------------------------------ assemblage
def matrice_vers_disque(axe):
    """Rotation qui envoie `axe` sur z (repère du disque)."""
    n = np.asarray(axe, float); n = n / np.linalg.norm(n)
    ref = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = ref - np.dot(ref, n) * n; e1 /= np.linalg.norm(e1)
    return np.stack([e1, np.cross(n, e1), n])       # lignes : nouveaux axes


def rayon_jacobi(d, m_galaxie, m_hote):
    """Rayon de marée (Jacobi) d'une galaxie de masse m à la distance d d'un hôte de masse M : d (m / 3M)^(1/3)."""
    return d * (m_galaxie / (3 * m_hote)) ** (1 / 3)


def coefficients(pos, m, kind, axe=None, rayon_max=None, n_mult_max=N_MULT_MAX, graine=12345):
    """Champ d'une galaxie à une image.

    pos (N, 3) kpc, relatives au centre de la galaxie ; m (N,) M☉ ; kind (N,) : 0 halo, 1 disque mince, 2 bulbe, 3 gaz,
    4 disque épais (les traceurs sans masse, kind 9, sont ignorés).
    axe : axe de rotation du disque dans le repère des positions (le moment cinétique des étoiles) ; sans axe, il est
    calculé comme le petit axe d'inertie des particules de disque.
    rayon_max : rayon de marée ; les particules au-delà ne comptent pas dans le champ de cette galaxie (leur masse est
    rendue dans 'masse_hors'). Voir rayon_jacobi.
    Rend un dict sérialisable par sauver() (tableaux numpy + nombres)."""
    pos = np.asarray(pos, float); m = np.asarray(m, float); kind = np.asarray(kind)
    garde = kind != 9
    pos, m, kind = pos[garde], m[garde], kind[garde]
    masse_hors = 0.0
    if rayon_max is not None:
        r = np.linalg.norm(pos, axis=1)
        dedans = r <= rayon_max
        masse_hors = float(m[~dedans].sum())
        pos, m, kind = pos[dedans], m[dedans], kind[dedans]
    est_disque = np.isin(kind, DISQUE)
    if axe is None:
        if est_disque.sum() > 100:
            q = pos[est_disque]; w = m[est_disque]
            I = (q * w[:, None]).T @ q / w.sum()
            axe = np.linalg.eigh(I)[1][:, 0]
        else:
            axe = np.array([0.0, 0, 1])
    Rot = matrice_vers_disque(axe)
    p = pos @ Rot.T
    out = dict(version=VERSION, rotation=Rot, masse=float(m.sum()), masse_hors=masse_hors)
    disque = None
    if est_disque.sum() > 1000:
        pd, md = p[est_disque], m[est_disque]
        Rd = np.hypot(pd[:, 0], pd[:, 1])
        o = np.argsort(Rd); c = np.cumsum(md[o])
        lam = float(Rd[o][np.searchsorted(c, 0.5 * c[-1])])       # rayon qui contient la moitié de la masse du disque
        disque = dict(lam=lam)
        boite = (Rd < lam * BOITE_R) & (np.abs(pd[:, 2]) < lam * BOITE_Z)
        cyl = cylindre(Rd[boite], pd[boite, 2], np.arctan2(pd[boite, 1], pd[boite, 0]), md[boite], lam)
        out['cylindre'] = cyl
        rng = np.random.default_rng(graine + 1)
        sel = _sous_tirage(int(boite.sum()), n_mult_max, rng)
        out['multipole_disque'] = multipole(pd[boite][sel], md[boite][sel] * (boite.sum() / len(sel) if len(sel) else 1))
        reste_p = np.concatenate([p[~est_disque], pd[~boite]])
        reste_m = np.concatenate([m[~est_disque], md[~boite]])
    else:
        reste_p, reste_m = p, m
    rng = np.random.default_rng(graine)
    sel = _sous_tirage(len(reste_p), n_mult_max, rng)
    facteur = len(reste_p) / len(sel) if len(sel) else 1.0
    out['multipole'] = multipole(reste_p[sel], reste_m[sel] * facteur)
    out['n_particules'] = int(len(p))
    return out


def _sous_tirage(n, nmax, rng):
    if n <= nmax:
        return np.arange(n)
    return np.sort(rng.choice(n, nmax, replace=False))


def evaluer(C, x):
    """Potentiel (N,) et force (N, 3) aux points x (N, 3), dans le repère des positions données à coefficients()."""
    x = np.atleast_2d(np.asarray(x, float))
    Rot = C['rotation']
    p = x @ Rot.T
    Phi, F = eval_multipole(C['multipole'], p)
    if 'cylindre' in C:
        b = dans_boite(C['cylindre'], p)
        if b.any():
            ph, fr = eval_cylindre(C['cylindre'], p[b]); Phi[b] += ph; F[b] += fr
        if (~b).any():
            ph, fr = eval_multipole(C['multipole_disque'], p[~b]); Phi[~b] += ph; F[~b] += fr
    return Phi, F @ Rot


# ------------------------------------------------------------------ fichier
def sauver(C, chemin):
    """Un .npz par galaxie et par image (float32 pour les tableaux, ~0,3 Mo)."""
    d = dict(meta=json.dumps(dict(version=C['version'], masse=C['masse'], masse_hors=C['masse_hors'], n_particules=C['n_particules'],
                                  lmax=C['multipole']['lmax'], mmax=C['cylindre']['mmax'] if 'cylindre' in C else None,
                                  lam=C['cylindre']['lam'] if 'cylindre' in C else None,
                                  unites='kpc, M☉, km/s ; potentiel (km/s)² ; G = 4,30091e-6')),
             rotation=C['rotation'], mult_r=C['multipole']['r'], mult_phi=C['multipole']['phi'].astype(np.float32),
             mult_dphi=C['multipole']['dphi'].astype(np.float32))
    if 'cylindre' in C:
        d.update(cyl_R=C['cylindre']['R'], cyl_z=C['cylindre']['z'], cyl_tab=C['cylindre']['tab'].astype(np.float32),
                 md_r=C['multipole_disque']['r'], md_phi=C['multipole_disque']['phi'].astype(np.float32),
                 md_dphi=C['multipole_disque']['dphi'].astype(np.float32))
    np.savez(chemin, **d)


def charger(chemin):
    z = np.load(chemin)
    meta = json.loads(str(z['meta']))
    C = dict(version=meta['version'], masse=meta['masse'], masse_hors=meta['masse_hors'], n_particules=meta['n_particules'],
             rotation=z['rotation'],
             multipole=dict(lmax=meta['lmax'], r=z['mult_r'], phi=z['mult_phi'].astype(float), dphi=z['mult_dphi'].astype(float)))
    if 'cyl_tab' in z:
        C['cylindre'] = dict(lam=meta['lam'], R=z['cyl_R'], z=z['cyl_z'], mmax=meta['mmax'], tab=z['cyl_tab'].astype(float))
        C['multipole_disque'] = dict(lmax=meta['lmax'], r=z['md_r'], phi=z['md_phi'].astype(float), dphi=z['md_dphi'].astype(float))
    return C


def sauver_bin(C, chemin):
    """Format binaire lu par natif/physique/champ_bfe.h (petit-boutiste) :
    'CHMP', i32 version, f64 masse, f64 rotation[9] (lignes), multipôle, i32 a_un_disque, [disque : i32 mmax, i32 NR,
    i32 NZ, f64 R[NR], f64 z[NZ], f32 tab[(2 mmax + 1) × 4 × NR × NZ], multipôle du disque].
    Multipôle : i32 lmax, i32 nr, f64 r[nr], f32 phi[nr × (lmax+1)²], f32 dphi[nr × (lmax+1)²]."""
    import struct

    def mult(fh, M):
        fh.write(struct.pack('<ii', M['lmax'], len(M['r'])))
        fh.write(np.asarray(M['r'], '<f8').tobytes())
        fh.write(np.asarray(M['phi'], '<f4').tobytes())
        fh.write(np.asarray(M['dphi'], '<f4').tobytes())
    with open(chemin, 'wb') as fh:
        fh.write(b'CHMP')
        fh.write(struct.pack('<id', VERSION, C['masse']))
        fh.write(np.asarray(C['rotation'], '<f8').tobytes())
        mult(fh, C['multipole'])
        cy = C.get('cylindre')
        fh.write(struct.pack('<i', 1 if cy else 0))
        if cy:
            fh.write(struct.pack('<iii', cy['mmax'], len(cy['R']), len(cy['z'])))
            fh.write(np.asarray(cy['R'], '<f8').tobytes())
            fh.write(np.asarray(cy['z'], '<f8').tobytes())
            fh.write(np.asarray(cy['tab'], '<f4').tobytes())
            mult(fh, C['multipole_disque'])
