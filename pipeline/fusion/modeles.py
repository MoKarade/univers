#!/usr/bin/env python3
"""Modèles des galaxies pour le calcul de la fusion (docs/fusion-methode.md, § 2), mis à l'équilibre avec AGAMA.

Unités : M☉, kpc, km/s (G = 4,30091e-6). Chaque galaxie est échantillonnée seule, centrée sur l'origine, disque dans
le plan xy tournant dans le sens direct autour de +z ; `placer` la tourne vers son axe et la déplace.
"""
import math
import numpy as np
import agama

agama.setUnits(mass=1, length=1, velocity=1)
G = 4.30091e-6

# Voie lactée de la page (20_physics.js, GAL) : halo NFW de masse d'échelle GMs/G, coupé à 220 kpc
V0, R0, MB, AB, MD = 230.0, 8.2, 0.5e10, 0.5, 6.8e10
RS, RCUT = 16.0, 220.0


def _v2_baryons(r):
    return G * MB * r / (r + AB) ** 2 + G * MD * r * r / (r * r + (3.0 + 0.28) ** 2) ** 1.5


def _nfw_shape(r):
    x = r / RS
    return (math.log(1 + x) - x / (1 + x)) / r


MS_NFW = (V0 * V0 - _v2_baryons(R0)) / _nfw_shape(R0) / G     # ≈ 5,60e11 M☉, comme GAL.GMs / G dans la page


def galaxie(nom, nh, nd, nb, k_mass=1.0, k_r=1.0, halo='nfw', mh=None, ah=None, md=None, rd=None, mb=None, ab=None):
    """Échantillonne une galaxie à l'équilibre. Rend un dict de tableaux : pos, vel, m, eps, kind (0 halo, 1 disque, 2 bulbe)."""
    comps, dens = [], []
    if halo == 'nfw':
        rho0 = MS_NFW * k_mass / (4 * math.pi * (RS * k_r) ** 3)
        ph = agama.Potential(type='Spheroid', densityNorm=rho0, gamma=1, beta=3, alpha=1, scaleRadius=RS * k_r,
                             outerCutoffRadius=RCUT * k_r, cutoffStrength=4)
    else:   # Hernquist
        ph = agama.Potential(type='Dehnen', gamma=1, mass=mh, scaleRadius=ah)
    md = MD * k_mass if md is None else md
    rd = 2.6 * k_r if rd is None else rd
    pdk = agama.Potential(type='Disk', surfaceDensity=md / (2 * math.pi * rd * rd), scaleRadius=rd, scaleHeight=0.3 * k_r)
    pots = [ph, pdk]
    if nb:
        mb = MB * k_mass if mb is None else mb
        ab = AB * k_r if ab is None else ab
        pb = agama.Potential(type='Dehnen', gamma=1, mass=mb, scaleRadius=ab)
        pots.append(pb)
    pot = agama.Potential(*pots)
    out = []
    dfh = agama.DistributionFunction(type='QuasiSpherical', potential=pot, density=ph)
    xv, m = agama.GalaxyModel(pot, dfh).sample(nh)
    out.append((xv, m, 0.4 * k_r, 0))
    vc = float(np.sqrt(-pot.force(np.array([[2 * rd, 0, 0]]))[0, 0] * 2 * rd))
    dfd = agama.DistributionFunction(type='QuasiIsothermal', potential=pot, Sigma0=md / (2 * math.pi * rd * rd), Rdisk=rd,
                                     Hdisk=0.3 * k_r, sigmar0=0.35 * vc, Rsigmar=2 * rd)
    xv, m = agama.GalaxyModel(pot, dfd).sample(nd)
    out.append((xv, m, 0.1 * k_r, 1))
    if nb:
        dfb = agama.DistributionFunction(type='QuasiSpherical', potential=pot, density=pb)
        xv, m = agama.GalaxyModel(pot, dfb).sample(nb)
        out.append((xv, m, 0.1 * k_r, 2))
    pos = np.concatenate([o[0][:, :3] for o in out]); vel = np.concatenate([o[0][:, 3:] for o in out])
    mass = np.concatenate([o[1] for o in out])
    eps = np.concatenate([np.full(len(o[1]), o[2]) for o in out]); kind = np.concatenate([np.full(len(o[1]), o[3], dtype=np.int8) for o in out])
    print(f'{nom} : {len(mass)} particules, masse {mass.sum():.3e} M☉, vitesse circulaire à 2 Rd : {vc:.0f} km/s')
    return dict(pos=pos, vel=vel, m=mass, eps=eps, kind=kind)


def rotation_vers(axe):
    """Matrice qui envoie +z sur l'axe donné (vecteur unitaire)."""
    a = np.asarray(axe, float); a /= np.linalg.norm(a)
    z = np.array([0.0, 0.0, 1.0]); v = np.cross(z, a); c = float(z @ a)
    if np.linalg.norm(v) < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))


def placer(g, axe, pos0, vel0):
    R = rotation_vers(axe)
    return dict(pos=g['pos'] @ R.T + np.asarray(pos0), vel=g['vel'] @ R.T + np.asarray(vel0), m=g['m'], eps=g['eps'], kind=g['kind'])


def assembler(*gs):
    return {k: np.concatenate([g[k] for g in gs]) for k in ('pos', 'vel', 'm', 'eps', 'kind')}
