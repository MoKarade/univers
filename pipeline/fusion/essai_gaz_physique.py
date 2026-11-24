#!/usr/bin/env python3
"""Contrôles de la physique du gaz (gaz_physique.py) et du jumeau sur processeur (gaz_cpu.py). Sans carte graphique,
sauf `gpu` (comparaison au code de la carte, à lancer quand elle est libre).

Usage : python essai_gaz_physique.py [refroid] [etoiles] [reserve] [gradient] [sod] [sedov] [bilan] [gpu]
Sans argument : tout sauf gpu. Code de sortie 0 si tout passe. Chaque ligne dit la valeur mesurée et la référence.
"""
import math
import sys
import time

import numpy as np

import gaz_cpu
import gaz_physique as gp


def _ligne(nom, mesure, ref, tol, unite=''):
    e = mesure / ref - 1 if ref else mesure
    bon = abs(e) <= tol
    print(f'  {nom:44s} {mesure:.6g}{unite}  (référence {ref:.6g}{unite}, écart {100 * e:+.3f} %, tolérance {100 * tol:g} %)'
          f'  {"bon" if bon else "MAUVAIS"}')
    return bon


# ---------------------------------------------------------------------------------------------------------------
def refroid():
    """Le refroidissement exact contre une intégration très fine (Runge-Kutta 4 en log T, pas adaptatif)."""
    print('Refroidissement exact (Townsend 2009) contre intégration très fine :')
    R = gp.Refroidissement()
    ok = True

    def fin(T0, rho, dt_s):
        A = R.coefficient_A(rho)
        y, t = math.log(T0), 0.0

        def f(y):
            T = math.exp(y)
            return -A * float(gp.lambda_cie(T)) / T if T > gp.T_PLANCHER else 0.0
        while t < dt_s:
            T = math.exp(y)
            if T <= gp.T_PLANCHER * (1 + 1e-12):
                break
            h = min(dt_s - t, 1e-3 / max(abs(f(y)), 1e-300))
            k1 = f(y); k2 = f(y + 0.5 * h * k1); k3 = f(y + 0.5 * h * k2); k4 = f(y + h * k3)
            y += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6; t += h
        return max(math.exp(y), gp.T_PLANCHER)

    rho_nh1 = 1.0 / (gp.X / gp.M_P * gp.RHO_CGS)          # M☉/kpc³ pour n_H = 1 cm^-3
    for T0 in (2e4, 3e5, 1e6, 10 ** 7.5, 1e8, 3.2e9, 1e10):
        for nh in (0.01, 1.0):
            tc = R.temps_de_refroidissement(T0, nh * rho_nh1)
            for frac in (0.1, 0.5, 2.0):
                dt = frac * tc
                T_ex = float(R.refroidir(np.array([T0 / gp.K_PAR_U]), np.array([nh * rho_nh1]), dt)[0] * gp.K_PAR_U)
                T_rk = fin(T0, nh * rho_nh1, dt * gp.UNITE_TEMPS_S)
                if T_rk <= gp.T_PLANCHER * 1.0001 and T_ex <= gp.T_PLANCHER * 1.0001:
                    continue
                ok &= _ligne(f'T0={T0:.3g} K, n_H={nh:g}, dt={frac:g} t_refr', T_ex, T_rk, 1e-4, ' K')
    # valeur absolue de la courbe et rapport des deux normalisations (n² Cholla contre n_e n_i)
    ok &= _ligne("L(10^6 K) de l'ajustement", float(gp.lambda_cie(1e6)), 10 ** (0.7 * 1.1 ** 2 - 22.8), 1e-12, ' erg cm³/s')
    Rc = gp.Refroidissement('cholla')
    ok &= _ligne('rapport des normalisations n² / (n_e n_i)', Rc.coefficient_A(1.0) / R.coefficient_A(1.0),
                 (1 / 0.6) ** 2 / ((gp.X + gp.Y / 2) * (gp.X + gp.Y / 4)), 1e-12)
    # propriété de semi-groupe : un grand pas = mille petits
    u0 = np.array([10 ** 7.5 / gp.K_PAR_U, 3e5 / gp.K_PAR_U]); rho = np.array([rho_nh1, 0.1 * rho_nh1])
    dt = 0.3 * R.temps_de_refroidissement(10 ** 7.5, rho_nh1)
    u1 = R.refroidir(u0, rho, dt)
    u2 = u0.copy()
    for _ in range(1000):
        u2 = R.refroidir(u2, rho, dt / 1000)
    ok &= _ligne('un pas contre mille pas (gaz à 10^7,5 K)', float(u1[0]), float(u2[0]), 1e-6, ' (km/s)²')
    ok &= _ligne('un pas contre mille pas (gaz à 3e5 K)', float(u1[1]), float(u2[1]), 1e-6, ' (km/s)²')
    # plancher : un très long pas ramène exactement à 10^4 K, et un gaz déjà au plancher ne bouge pas
    u3 = R.refroidir(np.array([1e8 / gp.K_PAR_U, 5e3 / gp.K_PAR_U]), np.array([rho_nh1, rho_nh1]), 1.0)
    ok &= _ligne('très long pas : plancher', float(u3[0] * gp.K_PAR_U), gp.T_PLANCHER, 1e-9, ' K')
    ok &= _ligne('gaz sous le plancher inchangé', float(u3[1] * gp.K_PAR_U), 5e3, 1e-12, ' K')
    return ok


# ---------------------------------------------------------------------------------------------------------------
def etoiles():
    """Nombre de supernovæ par masse formée contre la valeur publiée ; durées de vie ; énergie totale."""
    print('Étoiles et supernovæ :')
    ok = _ligne('supernovæ 6-100 M☉ par M☉ formée (Chabrier)', gp.nombre_sn_par_masse(6.0, 100.0), 1.736e-2, 0.005)
    print('    (référence : Dalla Vecchia & Schaye 2012, éq. 1, Chabrier 0,1-100 M☉)')
    t = gp.duree_de_vie(np.logspace(math.log10(0.8), 2, 200))
    croissant = bool(np.all(np.diff(t) < 0))
    print(f'  durée de vie décroissante avec la masse : {"bon" if croissant else "MAUVAIS"} ;'
          f' 8 M☉ : {gp.duree_de_vie(8) / 1e6:.1f} Ma, 100 M☉ : {gp.duree_de_vie(100) / 1e6:.2f} Ma')
    ok &= croissant
    e = gp.Explosions()
    tot = float(e.energie_cumulee(1.37e10)) / gp.E51
    ok &= _ligne('supernovæ par M☉ en un temps de Hubble (II + Ia)', tot, gp.nombre_sn_par_masse() + gp.NIA_PAR_MSOL, 1e-6)
    # contrôle indépendant de la table : à l'âge où meurt une étoile de masse m0, toutes les étoiles plus lourdes ont
    # explosé (intégrale directe de la répartition des masses)
    for m0 in (9.0, 15.0, 40.0):
        attendu = gp.nombre_sn_par_masse(m0, gp.M_SN_HAUT)
        ok &= _ligne(f"supernovæ à la mort d'une étoile de {m0:g} M☉", float(e.n_ii_cumule(gp.duree_de_vie(m0))), attendu, 2e-3)
    ok &= _ligne('aucune supernova avant 3,3 Ma', float(e.energie_cumulee(3.0e6)) + 1.0, 1.0, 0.0)
    return ok


# ---------------------------------------------------------------------------------------------------------------
def reserve():
    """La réserve d'énergie : énergie déposée + restante = énergie libérée, exactement ; masses inchangées."""
    print('Réserve d\'énergie des explosions (bilan exact) :')
    rng = np.random.default_rng(1)
    e = gp.Explosions()
    n_et, n_gaz = 200, 5000
    m_et = rng.uniform(5e3, 5e4, n_et); age = rng.uniform(0, 5e7, n_et)
    m_gaz = rng.uniform(5e3, 5e4, n_gaz); u = np.full(n_gaz, gp.T_PLANCHER / gp.K_PAR_U)
    m_avant = m_gaz.sum() + m_et.sum()
    res = np.zeros(n_et); libere = depose = 0.0
    for _ in range(400):
        dE = m_et * e.energie_liberee(age, 2.5e5)
        res += dE; libere += dE.sum(); age += 2.5e5
        vois = rng.integers(0, n_gaz, (n_et, 16))
        _, d = gp.deposer(res, vois, m_gaz, u, rng)
        depose += d
    u_depose = float(((u - gp.T_PLANCHER / gp.K_PAR_U) * m_gaz).sum()) * gp.M_SOL * 1e10     # erg
    # énergie d'un saut de 10^7,5 K écrite à la main : 3/2 k ΔT par particule, m / (mu m_p) particules
    q = 1.5 * 1.380649e-16 * 10 ** 7.5 * 1e4 * 1.98841e33 / (0.59906 * 1.67262192e-24)
    ok = _ligne("énergie d'un saut de 10^7,5 K pour 10^4 M☉", gp.energie_quantum(1e4), q, 1e-4, ' erg')
    ok &= _ligne('énergie déposée + réserve / libérée', (depose + res.sum()) / libere, 1.0, 1e-12)
    ok &= _ligne('énergie reçue par le gaz / déposée', u_depose / depose, 1.0, 1e-9)
    ok &= _ligne('masse totale', m_gaz.sum() + m_et.sum(), m_avant, 0.0)
    print(f'    {libere / gp.E51:.0f} supernovæ libérées, {100 * depose / libere:.1f} % déjà déposés, le reste en réserve')
    return ok


# ---------------------------------------------------------------------------------------------------------------
def verre(nx, ny, nz, pas, graine):
    """Bloc de particules sans réseau (comme essai_gaz.verre, sur processeur)."""
    rng = np.random.default_rng(graine)
    a = [np.arange(k) * pas for k in (nx, ny, nz)]
    Xg, Yg, Zg = np.meshgrid(*a, indexing='ij')
    p = np.stack([Xg.ravel(), Yg.ravel(), Zg.ravel()], 1) + rng.normal(0, 0.25 * pas, (nx * ny * nz, 3))
    n = len(p); m = np.full(n, pas ** 3); h = np.full(n, 1.2 * pas); v = np.zeros((n, 3))
    for _ in range(30):
        r = gaz_cpu.sph(p, v, m, h, cs=1.0, passes=2); h = r['h']
        p = p + r['acc'] * (0.15 * pas) ** 2
    return p


def gradient():
    """Même contrôle que essai_gaz.gradient : accélération, divergence et refroidissement connus exactement."""
    d = 0.04; a = np.arange(-0.5 + d / 2, 0.5, d)
    Xg, Yg, Zg = np.meshgrid(a, a, a, indexing='ij'); p = np.stack([Xg.ravel(), Yg.ravel(), Zg.ravel()], 1); n = len(p)
    u = 1.0 + 0.5 * p[:, 0]; vel = np.stack([0.3 * p[:, 0], 0 * p[:, 0], 0 * p[:, 0]], 1)
    r = gaz_cpu.sph(p, vel, np.full(n, d ** 3), np.full(n, 1.2 * d), u=u, gamma=1.4)
    c = (np.abs(p) < 0.2).all(1)
    print('Gradient connu (jumeau processeur) :')
    ok = _ligne('accélération x', float(r['acc'][c, 0].mean()), -0.2, 0.04)
    ok &= _ligne('divergence', float(r['divv'][c].mean()), 0.3, 0.04)
    ok &= _ligne('du/dt / u', float((r['dudt'] / u)[c].mean()), -0.12, 0.04)
    return ok


def sod():
    """Tube à choc isotherme (comme essai_gaz.sod), en plus petit."""
    d = 0.6 / 36; marge = 4
    B = verre(36 + 2 * marge, 18 + 2 * marge, 18 + 2 * marge, d, 1) - np.array([marge * d, (marge + 9) * d, (marge + 9) * d])
    G = B[(B[:, 0] > 0) & (B[:, 0] < 36 * d) & (np.abs(B[:, 1]) < 9 * d) & (np.abs(B[:, 2]) < 9 * d)]
    pl = G - np.array([0.6, 0, 0]); gr = G * 2.0
    pr = gr[(gr[:, 0] < 0.6) & (np.abs(gr[:, 1]) < 0.15) & (np.abs(gr[:, 2]) < 0.15)]
    pos = np.concatenate([pl, pr]); n = len(pos)
    m = np.full(n, d ** 3); h = np.concatenate([np.full(len(pl), 1.2 * d), np.full(len(pr), 2.4 * d)])
    vel = np.zeros((n, 3))
    r = gaz_cpu.sph(pos, vel, m, h, cs=1.0); h = r['h']; dt, t = 0.001, 0.0
    while t < 0.08 - 1e-9:
        vel += 0.5 * dt * r['acc']; pos = pos + dt * vel
        r = gaz_cpu.sph(pos, vel + 0.5 * dt * r['acc'], m, h, cs=1.0); h = r['h']
        vel += 0.5 * dt * r['acc']; t += dt
    q = (np.abs(pos[:, 1]) < 0.06) & (np.abs(pos[:, 2]) < 0.06) & (pos[:, 0] > 0.03) & (pos[:, 0] < 0.10)
    print(f'Tube à choc isotherme (jumeau processeur, 2/3 de la finesse de essai_gaz.sod), {n} particules, t = {t:.2f}, {int(q.sum())} mesurées :')
    ok = _ligne('densité du plateau', float(np.median(r['rho'][q])), 0.3445, 0.06)
    ok &= _ligne('vitesse du plateau', float(np.median(vel[q, 0])), 1.064, 0.06)
    return ok


def _avancer_adiabatique(pos, vel, u, m, h, t_fin, cs_fac=0.25, refroid=None, rho_unite=None, journal=None):
    """Saute-mouton avec pas de Courant commun ; refroidissement optionnel (opérateur séparé, à densité fixée).
    Rend aussi l'énergie rayonnée."""
    g = 5.0 / 3.0
    r = gaz_cpu.sph(pos, vel, m, h, u=u, gamma=g); h = r['h']; t = 0.0; perdu = 0.0
    while t < t_fin - 1e-12:
        dt = min(cs_fac * float((r['h'] / r['vsig']).min()), t_fin - t)
        vel = vel + 0.5 * dt * r['acc']; ud = np.maximum(u + 0.5 * dt * r['dudt'], 1e-9)
        pos = pos + dt * vel
        r = gaz_cpu.sph(pos, vel + 0.5 * dt * r['acc'], m, h, u=np.maximum(ud + 0.5 * dt * r['dudt'], 1e-9), gamma=g)
        h = r['h']
        vel = vel + 0.5 * dt * r['acc']; u = np.maximum(ud + 0.5 * dt * r['dudt'], 1e-9)
        if refroid is not None:
            u2 = refroid.refroidir(u, r['rho'] * rho_unite, dt)
            perdu += float((m * (u - u2)).sum()); u = u2
        t += dt
        if journal is not None:
            journal(t, pos, vel, u, r)
    return pos, vel, u, r, perdu


def sedov(nx=32):
    """Explosion de Sedov-Taylor (gamma 5/3) : R = 1,1527 (E t² / rho)^(1/5) ; énergie conservée."""
    d = 1.0 / nx; marge = 3
    B = verre(nx + 2 * marge, nx + 2 * marge, nx + 2 * marge, d, 3) - (marge + nx / 2) * d
    p = B[(np.abs(B) < 0.5).all(1)]; n = len(p)
    r0 = np.linalg.norm(p, axis=1)
    m = np.full(n, d ** 3); u = np.full(n, 1e-5)
    centre = np.argsort(r0)[:32]
    u[centre] += 1.0 / (32 * d ** 3)
    debut = time.time()
    pos, vel, u, r, _ = _avancer_adiabatique(p, np.zeros((n, 3)), u, m, np.full(n, 1.2 * d), 0.06)
    rr = np.linalg.norm(pos, axis=1); rho = r['rho']
    bords = np.linspace(0.05, 0.48, 30); mil = 0.5 * (bords[1:] + bords[:-1])
    prof = np.array([np.median(rho[(rr >= a) & (rr < b)]) if ((rr >= a) & (rr < b)).sum() > 10 else 0
                     for a, b in zip(bords[:-1], bords[1:])])
    R_calc = float(mil[int(np.argmax(prof))]); R_ex = 1.1527 * (0.06 ** 2) ** 0.2
    E = float((m * u).sum() + 0.5 * (m * (vel ** 2).sum(1)).sum())
    print(f'Explosion de Sedov (jumeau processeur), {n} particules, {time.time() - debut:.0f} s :')
    ok = _ligne('rayon du choc', R_calc, R_ex, 0.06)
    ok &= _ligne('énergie totale', E, 1.0 + float((np.full(n, d ** 3) * 1e-5).sum()), 0.03)
    print(f'    densité au choc {prof.max():.2f} (exacte 4, lissée par la méthode)')
    return ok and prof.max() > 1.8


def bilan():
    """Explosion d'étoiles dans du gaz qui rayonne (unités du calcul) : cinétique + interne + rayonnée = départ +
    déposé. C'est le contrôle de l'assemblage : SPH + refroidissement exact + réserve d'énergie."""
    nx = 20; L = 0.4                                     # boîte de 400 pc
    d = L / nx
    nh = 1.0; rho_kpc = nh / (gp.X / gp.M_P * gp.RHO_CGS)  # M☉/kpc³
    B = verre(nx + 4, nx + 4, nx + 4, d, 5) - (nx / 2 + 2) * d
    p = B[(np.abs(B) < L / 2).all(1)]; n = len(p)
    m = np.full(n, rho_kpc * d ** 3)                       # M☉ par particule (~ 7e3 à n_H = 1)
    u = np.full(n, gp.T_PLANCHER / gp.K_PAR_U)
    E0 = float((m * u).sum())
    # une particule d'étoiles de 10^5 M☉ née au centre : sa réserve est vidée sur ses 32 plus proches voisines
    e = gp.Explosions(); m_et = 1e5
    res = np.array([m_et * float(e.energie_cumulee(4e7))])  # supernovæ des 40 premiers Ma, d'un coup
    vois = np.argsort(np.linalg.norm(p, axis=1))[:32][None, :]
    rng = np.random.default_rng(2)
    _, depose = gp.deposer(res, vois, m, u, rng)
    dep_u = depose / (gp.M_SOL * 1e10)                     # M☉ (km/s)²
    R = gp.Refroidissement()
    pos, vel, u2, r, perdu = _avancer_adiabatique(p, np.zeros((n, 3)), u, m, np.full(n, 1.2 * d), 0.002,
                                                  refroid=R, rho_unite=1.0)
    K = float(0.5 * (m * (vel ** 2).sum(1)).sum()); U = float((m * u2).sum())
    print(f'Explosions d\'étoiles dans du gaz qui rayonne, {n} particules de {m[0]:.0f} M☉, '
          f'{2e-3 * gp.UNITE_TEMPS_AN / 1e6:.2f} Ma :')
    print(f'    déposé {depose / gp.E51:.0f} × 10^51 erg ; rayonné {100 * perdu / (E0 + dep_u):.1f} % ; '
          f'cinétique {100 * K / (E0 + dep_u):.1f} % ; reste {res[0] / gp.E51:.2f} × 10^51 erg en réserve')
    return _ligne('cinétique + interne + rayonnée / départ + déposé', (K + U + perdu) / (E0 + dep_u), 1.0, 0.02)


def gpu():
    """Jumeau processeur contre gaz_gpu.sph sur les mêmes particules (à lancer seulement quand la carte est libre)."""
    import cupy as cp
    import gaz_gpu
    rng = np.random.default_rng(4)
    n = 20000
    p = rng.normal(0, 1, (n, 3)) * np.array([1.0, 1.0, 0.3]); v = rng.normal(0, 0.3, (n, 3))
    m = rng.uniform(0.5, 1.5, n) / n; u = rng.uniform(0.5, 2.0, n); h = np.full(n, 0.1)
    a = gaz_cpu.sph(p, v, m, h, u=u)
    b = gaz_gpu.sph(cp.asarray(p), cp.asarray(v), cp.asarray(m), cp.asarray(h), u=cp.asarray(u))
    print('Jumeau processeur contre carte graphique (simple précision sur la carte) :')
    ok = True
    for k in ('rho', 'h', 'dudt', 'vsig'):
        x, y = a[k], cp.asnumpy(b[k])
        e = float(np.median(np.abs(x - y) / (np.abs(x) + 1e-30)))
        ok &= _ligne(f'{k} (écart médian relatif)', e, 0.0, 1e-3)
    acc_e = float(np.median(np.linalg.norm(a['acc'] - cp.asnumpy(b['acc']), axis=1) / np.linalg.norm(a['acc'], axis=1)))
    ok &= _ligne('accélération (écart médian relatif)', acc_e, 0.0, 1e-3)
    return ok


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    quoi = sys.argv[1:] or ['refroid', 'etoiles', 'reserve', 'gradient', 'sod', 'sedov', 'bilan']
    ok = True
    for nom in quoi:
        ok &= bool(globals()[nom]())
    print('TOUT BON' if ok else 'ÉCHEC')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
