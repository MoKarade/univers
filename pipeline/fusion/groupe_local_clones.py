#!/usr/bin/env python3
"""Clones du Groupe local : probabilité et date de la fusion Voie lactée–Andromède, d'après les MESURES et leurs erreurs.

Reprise fidèle de Sawala et al. 2025 (Nature Astronomy, « No certainty of a Milky Way–Andromeda collision »), code public
https://github.com/TillSawala/MW-M31 (galaxies.ipynb), mais vectorisée sur les tirages (numpy) au lieu d'une boucle Python.
Rien n'est changé dans la physique :
- tirages : loi normale tronquée à ±2σ, une graine par grandeur (0, 1, 2, ... dans l'ordre du carnet de Sawala) ;
- valeurs : leur Extended Data Table 1 (masses M200, concentrations, modules de distance, mouvements propres, vitesses
  radiales) ; directions des galaxies données par le service Sesame (SkyCoord.from_name), relevées le 12/11/2026 ;
  repère galactocentrique d'astropy « v4.0 » (R0 = 8,122 kpc, Soleil (12,9 ; 245,6 ; 7,78) km/s) ;
- halos NFW (200 × densité critique, Planck 2018) ; forces adoucies de 20 kpc ; frottement dynamique de Chandrasekhar
  « proportionnel » ; fusion quand deux centres passent à moins de 20 kpc ; saut de grenouille, pas de 0,001 unité.
- Unités du carnet : kpc, km/s, 10^10 masses solaires, G = 43007 ; l'unité de temps est donc kpc/(km/s) = 0,9778 Ga
  (le carnet l'appelle « Gyr »). Les dates écrites ici sont converties en vrais milliards d'années (Ga).

Usage : python groupe_local_clones.py [--variante wu2026|sawala2025] [--n 5000] [--galaxies MW,M31,M33,LMC] [--sortie dossier]
"""
import argparse, json, math, os, sys, time
import numpy as np
from scipy.stats import truncnorm
from scipy.special import erf
import astropy.units as u
from astropy.coordinates import SkyCoord, Distance, Galactocentric, galactocentric_frame_defaults
import energie_noire as EN      # énergie noire (w = -1), ajoutée au carnet de Sawala : energie_noire.py

sys.stdout.reconfigure(encoding='utf-8')
G = 43007.0                       # kpc (km/s)² / 10^10 M☉ (valeur du carnet)
UNITE_GA = 3.0856775814913673e16 / 3.15576e16      # kpc/(km/s) en Ga = 0,97779
H = 0.6766                        # Planck 2018 (colossus « planck18 »)
RHO_C = 277.536627 * H * H        # densité critique, M☉/kpc³ (colossus : 2,77536627e2 h² M☉ kpc⁻³)

# Extended Data Table 1 (Sawala et al. 2025) : M200 [10^10 M☉], c, module de distance, µα* et µδ [µas/an], v_los [km/s]
TABLE = {
    'MW':  dict(m=(100, 20), c=(10, 2)),
    'M31': dict(m=(130, 40), c=(10, 2), dmod=(24.407, 0.032), pmra=(48.9, 10.5), pmdec=(-36.9, 8.1), vr=(-301, 1)),
    'M33': dict(m=(30, 10), c=(10, 2), dmod=(24.67, 0.07), pmra=(31, 19), pmdec=(-29, 16), vr=(-179.2, 1.8)),
    'LMC': dict(m=(15, 5), c=(10, 2), dmod=(18.477, 0.026), pmra=(1910, 20), pmdec=(229, 47), vr=(262.2, 3.4)),
}
# Variante « wu2026 » : Wu, Huang, Zhang, Sun & Shao 2026 (arXiv:2603.22863, « The Fate of the Milky Way–Andromeda System:
# To Merge or Not? »), tableau 1 : mouvement propre de M31 de Wu et al. 2025 (A&A 701, A265, supergéantes, Gaia DR3) ;
# M33 : moyenne pondérée Wu et al. 2025 et VLBA (Brunthaler) ; concentration de M31 15 ± 2,5 ; le reste comme Sawala.
# Leur résultat publié : fusion dans 90 % des cas, médiane 6,5 (+1,3 −1,5) Ga (10 000 tirages).
VARIANTES = {
    'sawala2025': {},
    'wu2026': {('M31', 'pmra'): (45.9, 8.1), ('M31', 'pmdec'): (-20.5, 6.6), ('M31', 'c'): (15.0, 2.5),
               ('M33', 'pmra'): (30.6, 5.7), ('M33', 'pmdec'): (19.0, 5.7)},
}
# Directions (ICRS, degrés) renvoyées par SkyCoord.from_name le 12/11/2026 (service Sesame).
DIRECTION = {'M31': (10.6847083, 41.26875), 'M33': (23.46206906218, 30.66017511198), 'LMC': (80.89417, -69.75611)}
# Ordre des graines du carnet (CreateICs) : MW m,c ; M31 dmod,pmra,pmdec,vr,m,c ; LMC ... ; M33 ... (6 chacune).
ORDRE_GRAINES = [('MW', 'm'), ('MW', 'c')] + [(g, k) for g in ('M31', 'LMC', 'M33') for k in ('dmod', 'pmra', 'pmdec', 'vr', 'm', 'c')]


def tirages(n, clip, variante='sawala2025'):
    out = {}
    for seed, (gal, k) in enumerate(ORDRE_GRAINES):
        mu, s = VARIANTES[variante].get((gal, k), TABLE[gal][k])
        np.random.seed(seed)
        out[(gal, k)] = truncnorm(-clip, clip, loc=mu, scale=s).rvs(n)
    return out


def conditions_initiales(galaxies, n, clip, variante='sawala2025'):
    t = tirages(n, clip, variante)
    galactocentric_frame_defaults.set('v4.0')
    N = len(galaxies)
    pos, vel = np.zeros((n, N, 3)), np.zeros((n, N, 3))
    m, c = np.zeros((n, N)), np.zeros((n, N))
    for i, g in enumerate(galaxies):
        m[:, i], c[:, i] = t[(g, 'm')], t[(g, 'c')]
        if g == 'MW': continue
        ra, dec = DIRECTION[g]
        sky = SkyCoord(ra=np.full(n, ra) * u.deg, dec=np.full(n, dec) * u.deg, frame='icrs', distance=Distance(distmod=t[(g, 'dmod')] * u.mag),
                       pm_ra_cosdec=t[(g, 'pmra')] * u.uas / u.yr, pm_dec=t[(g, 'pmdec')] * u.uas / u.yr, radial_velocity=t[(g, 'vr')] * u.km / u.s)
        gc = sky.transform_to(Galactocentric())
        pos[:, i] = np.stack([gc.x.to_value(u.kpc), gc.y.to_value(u.kpc), gc.z.to_value(u.kpc)], 1)
        vel[:, i] = np.stack([gc.v_x.to_value(u.km / u.s), gc.v_y.to_value(u.km / u.s), gc.v_z.to_value(u.km / u.s)], 1)
    return m, c, pos, vel


def nfw(m, c):
    """r_s (kpc), r_200 (kpc), v_max (km/s) des halos NFW 200c (comme colossus, Planck 2018, z = 0)."""
    M = m * 1e10
    r200 = (3 * M / (4 * math.pi * 200 * RHO_C)) ** (1 / 3)
    rs = r200 / c
    gfun = lambda x: np.log1p(x) - x / (1 + x)
    xm = 2.1625815870646098      # maximum de la vitesse circulaire NFW, en r / r_s
    vmax = np.sqrt(4.30091727e-6 * M / r200 * c * gfun(xm) / (gfun(c) * xm))
    return rs, r200, vmax


ENERGIE_NOIRE = True      # --sans-energie-noire : reproduire le carnet de Sawala tel quel


def acc(pos, m, soft):
    d = pos[:, None, :, :] - pos[:, :, None, :]           # d[s, i, j] = x_j − x_i
    r2 = (d * d).sum(-1) + soft * soft
    inv = r2 ** -1.5
    a = G * (d * inv[..., None] * m[:, None, :, None]).sum(2)
    if ENERGIE_NOIRE:      # poussée de l'énergie noire depuis le centre de masse de chaque scénario
        cm = (m[..., None] * pos).sum(1, keepdims=True) / m.sum(1)[:, None, None]
        a = a + EN.acceleration(pos, cm)
    return a


def frottement(pos, vel, m, c, rs, r200, vmax):
    n, N = m.shape
    f = np.zeros_like(pos)
    for i in range(N):
        for j in range(N):
            if i == j: continue
            ok = (m[:, i] > 0) & (m[:, j] > 0) & (m[:, j] > m[:, i])
            dr = pos[:, i] - pos[:, j]
            r = np.maximum(10.0, np.linalg.norm(dr, axis=1))
            ok &= r < r200[:, j]
            if not ok.any(): continue
            dv = vel[:, i] - vel[:, j]; v = np.linalg.norm(dv, axis=1)
            gc = np.log1p(c[:, j]) - c[:, j] / (1 + c[:, j])
            rho = m[:, j] / (4 * math.pi * gc * r * (r + rs[:, j]) ** 2)
            x = r / rs[:, j]
            sig = vmax[:, j] * 1.4393 * x ** 0.354 / (1 + 1.1756 * x ** 0.725)      # Zentner & Bullock 2003
            y = v / (math.sqrt(2) * sig)
            integ = erf(y) - 2 * y / math.sqrt(math.pi) * np.exp(-y * y)
            eps = np.where(rs[:, i] > 8.0, 2.2 * rs[:, i] - 14, 0.45 * rs[:, i])
            with np.errstate(invalid='ignore', divide='ignore'):
                mag = 4 * math.pi * G * G * np.log(r / eps) * m[:, i] * rho * integ / np.maximum(v, 5) ** 3
            mag = np.where(ok, mag, 0.0)
            tot = np.where(ok, m[:, i] + m[:, j], 1.0)      # évite 0/0 quand les deux ont déjà été absorbées
            f[:, i] -= dv * (mag * m[:, j] / tot)[:, None]
            f[:, j] += dv * (mag * m[:, i] / tot)[:, None]
    return f


def integre(m, c, pos, vel, t_fin=10.0, dt=0.001, soft=20.0, seuil=20.0, garder=10):
    """Renvoie les dates (unités du carnet) de fusion par paire (inf si aucune) et les trajectoires tous les `garder` pas."""
    n, N = m.shape
    m, pos, vel = m.copy(), pos.copy(), vel.copy()
    rs, r200, vmax = nfw(m, c)
    vel -= (m[..., None] * vel).mean(1, keepdims=True) / m.mean(1)[:, None, None]      # comme le carnet
    a = acc(pos, m, soft) + frottement(pos, vel, m, c, rs, r200, vmax)
    existe = np.ones((n, N), bool)
    fusion = np.full((n, N, N), np.inf)          # fusion[s, i, j] : date où i ou j a disparu dans un regroupement de i et j
    absorbe = np.full((n, N), -1)                # qui a absorbé chaque galaxie
    t_absorbee = np.full((n, N), np.inf)         # date (unités du carnet) où chaque galaxie a été absorbée
    Nt = int(math.ceil(t_fin / dt))
    traj = np.zeros((Nt // garder + 1, n, N, 3), np.float32); traj[0] = pos
    for k in range(Nt):
        vel += a * dt / 2
        pos += vel * dt
        a = acc(pos, m, soft)
        a += frottement(pos, vel, m, c, rs, r200, vmax)
        vel += a * dt / 2
        for l in range(N):
            for q in range(l):
                d = np.linalg.norm(pos[:, l] - pos[:, q], axis=1)
                hit = existe[:, l] & existe[:, q] & (d < seuil)
                if not hit.any(): continue
                s = np.nonzero(hit)[0]
                keep = np.where(m[s, l] > m[s, q], l, q); rem = np.where(m[s, l] > m[s, q], q, l)
                mk, mr = m[s, keep], m[s, rem]
                pos[s, keep] = (mk[:, None] * pos[s, keep] + mr[:, None] * pos[s, rem]) / (mk + mr)[:, None]
                vel[s, keep] = (mk[:, None] * vel[s, keep] + mr[:, None] * vel[s, rem]) / (mk + mr)[:, None]
                m[s, keep] = mk + mr; m[s, rem] = 0; existe[s, rem] = False; absorbe[s, rem] = keep; t_absorbee[s, rem] = (k + 1) * dt
                fusion[s, l, q] = np.minimum(fusion[s, l, q], k * dt); fusion[s, q, l] = fusion[s, l, q]
        # la galaxie absorbée suit celle qui l'a absorbée (pour les trajectoires)
        for i in range(N):
            gone = ~existe[:, i]
            if gone.any():
                s = np.nonzero(gone)[0]; pos[s, i] = pos[s, absorbe[s, i]]; vel[s, i] = vel[s, absorbe[s, i]]
        if (k + 1) % garder == 0: traj[(k + 1) // garder] = pos
    return fusion, existe, traj, t_absorbee


def date_fusion_paire(fusion, existe_hist_idx, i, j):
    return fusion[:, i, j]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--n', type=int, default=5000)
    p.add_argument('--galaxies', default='MW,M31,M33,LMC')
    p.add_argument('--clip', type=float, default=2.0)
    p.add_argument('--sortie', default='')
    p.add_argument('--variante', default='wu2026', choices=sorted(VARIANTES))
    p.add_argument('--sans-energie-noire', action='store_true')
    a = p.parse_args()
    global ENERGIE_NOIRE
    ENERGIE_NOIRE = not a.sans_energie_noire
    gals = a.galaxies.split(',')
    t0 = time.time()
    m, c, pos, vel = conditions_initiales(gals, a.n, a.clip, a.variante)
    fusion, existe, traj, t_absorbee = integre(m, c, pos, vel)
    # Date de la fusion MW–M31 comme le carnet : premier pas où la Voie lactée OU Andromède n'existe plus.
    # (Une absorption de M31 par la Voie lactée, ou l'inverse ; M33 absorbée par M31 ne compte pas.)
    t_mw_m31 = fusion[:, 0, 1]
    for k in range(2, len(gals)):       # MW ou M31 absorbée par une autre (cas rares) : compte aussi, comme le carnet
        t_mw_m31 = np.minimum(t_mw_m31, np.where(m[:, k] > m[:, 0], fusion[:, 0, k], np.inf))
        t_mw_m31 = np.minimum(t_mw_m31, np.where(m[:, k] > m[:, 1], fusion[:, 1, k], np.inf))
    ok = np.isfinite(t_mw_m31)
    tg = t_mw_m31[ok] * UNITE_GA
    res = dict(variante=a.variante, energie_noire=ENERGIE_NOIRE, galaxies=gals, n=a.n, clip=a.clip, probabilite_fusion=float(ok.mean()),
               mediane_unites_carnet=float(np.median(t_mw_m31[ok])) if ok.any() else None,
               mediane_ga=float(np.median(tg)) if ok.any() else None,
               quantiles_ga={q: float(np.quantile(tg, q)) for q in (0.05, 0.16, 0.5, 0.84, 0.95)} if ok.any() else None,
               duree_s=round(time.time() - t0, 1))
    for nom, (i, j) in (('LMC_MW', ('LMC', 'MW')), ('M33_M31', ('M33', 'M31'))):
        if i in gals and j in gals:
            f = fusion[:, gals.index(i), gals.index(j)]; res['probabilite_' + nom] = float(np.isfinite(f).mean())
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if a.sortie:
        os.makedirs(a.sortie, exist_ok=True)
        np.savez_compressed(os.path.join(a.sortie, 'clones_groupe_local.npz'), galaxies=gals, m=m, c=c, pos0=pos, vel0=vel,
                            t_fusion=t_mw_m31 * UNITE_GA, t_absorbee=t_absorbee * UNITE_GA, fusion_paires=fusion * UNITE_GA, traj=traj, pas_traj_ga=10 * 0.001 * UNITE_GA)
        json.dump(res, open(os.path.join(a.sortie, 'clones_groupe_local.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
