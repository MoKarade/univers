#!/usr/bin/env python3
"""Horizon réel de chaque étoile Gaia : clones d'incertitude de mesure, suivis sur la carte graphique (plan-precalcul.md § 1).

Pour chaque étoile de Gaia DR3 gardée par l'appli (parallaxe / erreur > 10, gaia_telecharger.py) :
- K clones tirés dans les erreurs PUBLIÉES par Gaia (gaia_telecharger.py --jeu erreurs) : parallaxe et mouvements propres
  selon leur loi normale à trois dimensions (écarts types et corrélations de Gaia) ; vitesse radiale selon son erreur quand
  elle est mesurée ;
- sans vitesse radiale mesurée (la plupart des étoiles), elle est INCONNUE : chaque clone en reçoit une tirée parmi les
  vitesses radiales MESURÉES des étoiles du même morceau de ciel (même part, environ 40 degrés carrés) et de distance
  voisine (même tranche de 0,25 en log10 de la distance) ; drapeau « vitesse radiale tirée des voisines ». Une étoile
  sans voisine mesurée garde un écart inconnu (NaN).
- Passage au repère galactocentrique comme gaia_convertir.py puis orbite_galactique.h (versGalactique, Soleil de la
  bibliothèque), sous-pas comme Orbites::sousPas ; puis natif precalcul_clones ecarts (shaders/orbites_pas.comp).
Sortie, par part : horizon_NNNN.npz : source_id, ecarts (n × 22 float16, kpc : écart quadratique moyen des clones à
+10, 30, 100, 300 ka, 1, 3, 10, 30, 100, 300, 1 000 Ma, puis aux mêmes dates dans le passé), vr_tiree (bool).
Usage : python clones_etoiles.py <dossier parts de base> <dossier parts d'erreurs> <precalcul_clones.exe> <sortie> [--k 32]
        [--parts 0-1023]
"""
import argparse, math, os, subprocess, sys, time
import numpy as np
from astropy.io import fits

sys.stdout.reconfigure(encoding='utf-8')
EPS = math.radians(84381.448 / 3600.0)
KAPPA = 4.740470446
LY_PER_PC = 3.2615638
KPC_LY = 3261.5637769      # orbite::kKpcLy
# orbite::kM (repère galactocentrique -> écliptique) ; versGalactique applique la transposée
KM = np.array([[-0.0548756577, 0.4941094372, -0.8676661376], [-0.993821367, -0.1109908412, -0.0003515418], [-0.0964766946, 0.8622858559, 0.4971472117]])
SGRA = np.array([0.9999992, -0.00097327, -0.00080564]); R0 = 8.2
SOLEIL_POS = -SGRA * R0; SOLEIL_VIT = np.array([11.1, 232.8 + 12.24, 7.25])      # table unique (galaxie_orbites.h)
# Potentiel (galaxie_orbites.h), pour la règle des sous-pas
G_ = 4.30091e-6; MB, AB, MD, AD, BD, RS, V0 = 0.5e10, 0.5, 6.8e10, 3.0, 0.28, 16.0, 232.8


def gm_halo():
    v2b = G_ * MB * R0 / (R0 + AB) ** 2 + G_ * MD * R0 * R0 / (R0 * R0 + (AD + BD) ** 2) ** 1.5
    x = R0 / RS
    return (V0 * V0 - v2b) / ((math.log(1 + x) - x / (1 + x)) / R0)


GMH = gm_halo()


def phi(r, R2, z):
    B = np.sqrt(z * z + BD * BD)
    return -G_ * MB / (r + AB) - G_ * MD / np.sqrt(R2 + (AD + B) ** 2) - GMH * np.log1p(r / RS) / r


def sous_pas(x, v):
    """Règle de phys::galaxie::Orbites::sousPas (péricentre estimé dans le plan), vectorisée."""
    r = np.linalg.norm(x, axis=1) + 1e-12
    E = 0.5 * (v * v).sum(1) + phi(r, (x[:, :2] ** 2).sum(1), x[:, 2])
    L2 = (np.cross(x, v) ** 2).sum(1)
    f = lambda rr: 2 * (E - phi(rr + 1e-12, rr * rr, 0 * rr)) * rr * rr - L2
    lo = np.full(len(r), 1e-3); hi = np.maximum(r - 1e-12, 2e-3)
    plonge = f(lo) < 0
    for _ in range(40):
        m = 0.5 * (lo + hi); neg = f(m) < 0
        lo = np.where(neg, m, lo); hi = np.where(neg, hi, m)
    peri = np.where(plonge, hi, 1e-3)
    return np.where(peri < 0.7, 32.0, np.where(peri < 2, 8.0, np.where(peri < 4, 2.0, 1.0)))


def lire(chemin, cols):
    with fits.open(chemin, memmap=False) as h:
        d = h[1].data
        return {k: np.asarray(d[k]).astype(np.float64 if k != 'source_id' else np.int64) for k in cols}


def clones_part(base, err, K, rng):
    b = lire(base, ['source_id', 'ra', 'dec', 'parallax', 'pmra', 'pmdec', 'radial_velocity'])
    e = lire(err, ['source_id', 'parallax_error', 'pmra_error', 'pmdec_error', 'parallax_pmra_corr', 'parallax_pmdec_corr', 'pmra_pmdec_corr', 'radial_velocity_error'])
    ob, oe = np.argsort(b['source_id']), np.argsort(e['source_id'])
    b = {k: v[ob] for k, v in b.items()}; e = {k: v[oe] for k, v in e.items()}
    if not np.array_equal(b['source_id'], e['source_id']): raise SystemExit(f'{base} : étoiles différentes entre les deux téléchargements')
    n = len(b['source_id'])
    # Parallaxe et mouvements propres : loi normale à 3 dimensions (Cholesky de la covariance publiée)
    s = np.stack([e['parallax_error'], e['pmra_error'], e['pmdec_error']], 1)
    C = np.zeros((n, 3, 3))
    for i in range(3): C[:, i, i] = s[:, i] ** 2
    for (i, j), c in (((0, 1), 'parallax_pmra_corr'), ((0, 2), 'parallax_pmdec_corr'), ((1, 2), 'pmra_pmdec_corr')):
        C[:, i, j] = C[:, j, i] = np.nan_to_num(e[c]) * s[:, i] * s[:, j]
    L = np.linalg.cholesky(C)
    z = rng.standard_normal((n, K, 3))
    mes = np.stack([b['parallax'], b['pmra'], b['pmdec']], 1)
    tir = mes[:, None, :] + np.einsum('nij,nkj->nki', L, z)
    plx, pmra, pmdec = tir[..., 0], tir[..., 1], tir[..., 2]
    plx = np.maximum(plx, 1e-3)      # parallaxe > 10 σ : jamais atteint en pratique
    # Vitesse radiale
    rv, srv = b['radial_velocity'], e['radial_velocity_error']
    a_rv = np.isfinite(rv) & np.isfinite(srv)
    vr = np.where(a_rv[:, None], rv[:, None] + srv[:, None] * rng.standard_normal((n, K)), np.nan)
    tranche = np.floor(np.log10(1000.0 / b['parallax']) / 0.25).astype(int)
    tiree = ~a_rv
    for t in np.unique(tranche[tiree]):
        cibles = np.nonzero(tiree & (tranche == t))[0]
        pool = rv[a_rv & (tranche == t)]
        if len(pool) < 20: pool = rv[a_rv]      # trop peu dans la tranche : toutes les mesurées de la part
        if len(pool) == 0: continue
        vr[cibles] = pool[rng.integers(0, len(pool), (len(cibles), K))]
    # Position et vitesse (gaia_convertir.py), puis repère galactocentrique (orbite::versGalactique)
    ra, de = np.radians(b['ra'])[:, None], np.radians(b['dec'])[:, None]
    ca, sa, cd, sd = np.cos(ra), np.sin(ra), np.cos(de), np.sin(de)
    ce, se = math.cos(EPS), math.sin(EPS)
    ecl = lambda x, y, z: np.stack([x, ce * y + se * z, -se * y + ce * z], -1)
    u = ecl(cd * ca + 0 * plx, cd * sa + 0 * plx, sd + 0 * plx)
    pos_ly = u * (1000.0 / plx * LY_PER_PC)[..., None]
    va, vd = KAPPA * pmra / plx, KAPPA * pmdec / plx
    vel = ecl(vr * cd * ca - va * sa - vd * sd * ca, vr * cd * sa + va * ca - vd * sd * sa, vr * sd + vd * cd)
    xg = pos_ly @ KM / KPC_LY + SOLEIL_POS      # (KM^T e) en ligne = e @ KM
    vg = vel @ KM + SOLEIL_VIT
    etats = np.zeros((n, K, 8), np.float32)
    etats[..., :3] = xg; etats[..., 4:7] = vg
    ok = np.isfinite(vg).all(-1)
    etats[..., 3] = 1.0
    flat_x, flat_v, flat_ok = xg.reshape(-1, 3), vg.reshape(-1, 3), ok.reshape(-1)
    sp = np.ones(len(flat_ok)); sp[flat_ok] = sous_pas(flat_x[flat_ok], flat_v[flat_ok])
    etats[..., 3] = sp.reshape(n, K)
    etats[~ok] = 0; etats[~ok, 3] = 1.0      # étoile sans vitesse possible : clones à l'arrêt, écart rendu NaN ensuite
    connu = ok.all(1)
    return b['source_id'], etats, tiree, connu


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base'); ap.add_argument('erreurs'); ap.add_argument('exe'); ap.add_argument('sortie')
    ap.add_argument('--k', type=int, default=32); ap.add_argument('--parts', default='0-1023')
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    lo, hi = (int(x) for x in a.parts.split('-'))
    for p in range(lo, hi + 1):
        out = os.path.join(a.sortie, f'horizon_{p:04d}.npz')
        if os.path.exists(out): continue
        fe = os.path.join(a.erreurs, f'part_{p:04d}.fits')
        while not os.path.exists(fe):      # téléchargement encore en cours : on attend la part
            time.sleep(30)
        t0 = time.time()
        rng = np.random.default_rng(20261112 + p)
        sid, etats, tiree, connu = clones_part(os.path.join(a.base, f'part_{p:04d}.fits'), os.path.join(a.erreurs, f'part_{p:04d}.fits'), a.k, rng)
        tmp = os.path.join(a.sortie, 'etats.f32'); res = os.path.join(a.sortie, 'ecarts.f32')
        etats.tofile(tmp)
        t1 = time.time()
        r = subprocess.run([a.exe, 'ecarts', tmp, str(a.k), res], capture_output=True, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if r.returncode: raise SystemExit(f'part {p} : {r.stdout}{r.stderr}')
        ec = np.fromfile(res, np.float32).reshape(-1, 22)
        ec[~connu] = np.nan
        np.savez(out, source_id=sid, ecarts=ec.astype(np.float16), vr_tiree=tiree)
        med = np.nanmedian(ec, 0)
        print(f'part {p} : {len(sid)} étoiles ({tiree.mean():.0%} sans vitesse radiale mesurée), clones {t1 - t0:.1f} s, carte {time.time() - t1:.1f} s ; '
              f'écart médian 1 Ma {1000 * med[4]:.1f} pc, 100 Ma {med[8]:.3f} kpc, 1 Ga {med[10]:.2f} kpc', flush=True)
    for f in ('etats.f32', 'ecarts.f32'):
        try: os.remove(os.path.join(a.sortie, f))
        except OSError: pass


if __name__ == '__main__':
    main()
