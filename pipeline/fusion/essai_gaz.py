#!/usr/bin/env python3
"""Contrôles du gaz (gaz_gpu.py) contre trois problèmes dont la réponse est connue.

1. Gradient connu : gaz uniforme, énergie interne qui croît le long de x, dilatation le long de x.
2. Tube à choc isotherme : densité et vitesse exactes entre la détente et le choc.
3. Effondrement d'Evrard (1988, MNRAS 235, 911) : sphère de gaz froid (masse 1, rayon 1, G = 1, rho en 1/r,
   u = 0,05) qui s'effondre sous son poids, rebondit sur un choc et se met à l'équilibre. Gravité et gaz ensemble :
   l'énergie totale doit rester constante.

Usage : python essai_gaz.py [gradient] [sod] [evrard]      (code de sortie 0 si tout passe)
"""
import sys
import time

import numpy as np
import cupy as cp

import gaz_gpu
import gravite_gpu


def verre(nx, ny, nz, pas, graine):
    """Bloc de particules sans réseau : réseau agité, puis détendu par les forces de pression (descente amortie).
    Un réseau régulier fausse ces essais : étiré dans une seule direction, il n'a plus qu'un plan de voisines de chaque
    côté et la force de pression y est mal estimée (mesuré le 18/11 : détente 24 % trop rapide)."""
    rng = np.random.default_rng(graine)
    a = [np.arange(k) * pas for k in (nx, ny, nz)]
    X, Y, Z = np.meshgrid(*a, indexing='ij')
    p = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1) + rng.normal(0, 0.25 * pas, (nx * ny * nz, 3))
    pos = cp.asarray(p); n = len(p); m = cp.full(n, pas ** 3); h = cp.full(n, 1.2 * pas); vel = cp.zeros((n, 3))
    for _ in range(60):
        r = gaz_gpu.sph(pos, vel, m, h, cs=1.0); h = r['h']
        pos += r['acc'] * (0.15 * pas) ** 2
    return cp.asnumpy(pos)


def gradient():
    """Gaz uniforme dont l'énergie interne croît le long de x et qui se dilate le long de x : accélération, divergence et
    refroidissement connus exactement."""
    d = 0.02; a = np.arange(-0.5 + d / 2, 0.5, d)
    X, Y, Z = np.meshgrid(a, a, a, indexing='ij'); p = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1); n = len(p)
    u = cp.asarray(1.0 + 0.5 * p[:, 0]); vel = cp.asarray(np.stack([0.3 * p[:, 0], 0 * p[:, 0], 0 * p[:, 0]], 1))
    r = gaz_gpu.sph(cp.asarray(p), vel, cp.full(n, d ** 3), cp.full(n, 1.2 * d), u=u, gamma=1.4)
    c = (np.abs(p) < 0.2).all(1)
    mes = dict(acc_x=float(cp.asnumpy(r['acc'])[c, 0].mean()), divergence=float(cp.asnumpy(r['divv'])[c].mean()),
               refroidissement=float((cp.asnumpy(r['dudt']) / cp.asnumpy(u))[c].mean()))
    exact = dict(acc_x=-0.2, divergence=0.3, refroidissement=-0.12)
    ok = True
    print('Gradient connu :')
    for k in exact:
        e = mes[k] / exact[k] - 1; bon = abs(e) < 0.04; ok &= bon
        print(f'  {k:16s} {mes[k]:+.4f}  (exact {exact[k]:+.4f}, écart {100 * e:+.1f} %)  {"bon" if bon else "MAUVAIS"}')
    return ok


def sod():
    """Tube à choc isotherme (vitesse du son 1) : rho 1 à gauche, 0,125 à droite. Solution exacte : entre la détente et le
    choc, densité 0,3445 et vitesse 1,064 (ln(1/rho) = sqrt(rho/0,125) - sqrt(0,125/rho)) ; choc à la vitesse 1,660."""
    d = 0.0125; marge = 8
    B = verre(48 + 2 * marge, 24 + 2 * marge, 24 + 2 * marge, d, 1) - np.array([marge * d, (marge + 12) * d, (marge + 12) * d])
    G = B[(B[:, 0] > 0) & (B[:, 0] < 48 * d) & (np.abs(B[:, 1]) < 12 * d) & (np.abs(B[:, 2]) < 12 * d)]
    pl = G - np.array([0.6, 0, 0]); gr = G * 2.0
    pr = gr[(gr[:, 0] < 0.6) & (np.abs(gr[:, 1]) < 0.15) & (np.abs(gr[:, 2]) < 0.15)]
    pos = np.concatenate([pl, pr]); n = len(pos)
    m = cp.full(n, d ** 3); h = cp.asarray(np.concatenate([np.full(len(pl), 1.2 * d), np.full(len(pr), 2.4 * d)]))
    pos = cp.asarray(pos); vel = cp.zeros((n, 3))
    r = gaz_gpu.sph(pos, vel, m, h, cs=1.0); h = r['h']; dt, t = 0.0005, 0.0
    while t < 0.08 - 1e-9:
        vel += 0.5 * dt * r['acc']; pos += dt * vel
        r = gaz_gpu.sph(pos, vel + 0.5 * dt * r['acc'], m, h, cs=1.0); h = r['h']
        vel += 0.5 * dt * r['acc']; t += dt
    x = cp.asnumpy(pos); v = cp.asnumpy(vel); rho = cp.asnumpy(r['rho'])
    q = (np.abs(x[:, 1]) < 0.05) & (np.abs(x[:, 2]) < 0.05) & (x[:, 0] > 0.03) & (x[:, 0] < 0.10)      # plateau, loin des bords
    mes = dict(densite=float(np.median(rho[q])), vitesse=float(np.median(v[q, 0]))); exact = dict(densite=0.3445, vitesse=1.064)
    ok = True
    print(f'Tube à choc isotherme, {n} particules, t = {t:.2f} ; {int(q.sum())} particules mesurées')
    for k in exact:
        e = mes[k] / exact[k] - 1; bon = abs(e) < 0.06; ok &= bon
        print(f'  {k:8s} {mes[k]:.4f}  (exact {exact[k]:.4f}, écart {100 * e:+.1f} %)  {"bon" if bon else "MAUVAIS"}')
    return ok


def evrard(n=40000):
    rng = np.random.default_rng(1)
    r = rng.uniform(0, 1, n)        # rho en 1/r : masse dans r proportionnelle à r²  ->  r = sqrt(u) ... ici M(<r) = r², donc r = sqrt(u)
    r = np.sqrt(r)
    d = rng.normal(0, 1, (n, 3)); d /= np.linalg.norm(d, axis=1)[:, None]
    pos = cp.asarray(d * r[:, None]); vel = cp.zeros((n, 3)); m = cp.full(n, 1.0 / n)
    u = cp.full(n, 0.05); h = cp.full(n, 0.1); eps = cp.full(n, 0.02)
    g = 5.0 / 3.0

    def tout(pos, vel, u, h):
        s = gaz_gpu.sph(pos, vel, m, h, u=u, gamma=g, passes=4)
        a, phi = gravite_gpu.gravity(pos, m, eps, theta=0.5)
        return s, a, phi
    s, ag, phi = tout(pos, vel, u, h); h = s['h']

    def energies(vel, u, phi):
        return float(0.5 * (m * (vel ** 2).sum(1)).sum()), float((m * u).sum()), float(0.5 * (m * phi).sum())
    K, U, Wp = energies(vel, u, phi); E0 = K + U + Wp
    print(f'Evrard, {n} particules ; énergie au départ : cinétique {K:.3f}, interne {U:.3f}, potentielle {Wp:.3f}, totale {E0:.4f}')
    dt, t, pire, Umax = 0.002, 0.0, 0.0, 0.0
    debut = time.time()
    while t < 3.0 - 1e-9:
        a = s['acc'] + ag
        vel += 0.5 * dt * a; u_demi = u + 0.5 * dt * s['dudt']
        pos += dt * vel
        s, ag, phi = tout(pos, vel + 0.5 * dt * a, u_demi + 0.5 * dt * s['dudt'], h); h = s['h']
        vel += 0.5 * dt * (s['acc'] + ag); u = cp.maximum(u_demi + 0.5 * dt * s['dudt'], 1e-6)
        t += dt
        if round(t / dt) % 100 == 0:
            K, U, Wp = energies(vel, u, phi); e = (K + U + Wp) / E0 - 1; pire = max(pire, abs(e)) if np.isfinite(e) else float('nan'); Umax = max(Umax, U)
            print(f'  t = {t:.1f} : cinétique {K:.3f}, interne {U:.3f}, potentielle {Wp:.3f}, écart d\'énergie {100 * e:+.2f} %', flush=True)
    print(f'  plus grand écart d\'énergie : {100 * pire:.2f} % ; énergie interne au plus fort : {Umax:.3f} ; {time.time() - debut:.0f} s')
    return bool(np.isfinite(pire)) and np.isfinite(K + U + Wp) and pire < 0.03


def main():
    quoi = sys.argv[1:] or ['gradient', 'sod', 'evrard']
    ok = True
    if 'gradient' in quoi: ok &= gradient()
    if 'sod' in quoi: ok &= sod()
    if 'evrard' in quoi: ok &= evrard()
    print('PASSE' if ok else 'ECHEC')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
