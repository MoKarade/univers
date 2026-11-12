#!/usr/bin/env python3
"""Contrôle de gravite_gpu.py : l'arbre contre la somme directe (toutes les paires), sur la carte graphique.

Ne tourne que sur un PC avec carte NVIDIA (pas sur les machines GitHub). Les positions du test sont un tirage
géométrique (deux amas de Plummer et un disque mince), pas des données affichées : seul l'écart arbre - direct est jugé.
Usage : python test_gravite_gpu.py [n]
"""
import sys, time
import numpy as np
import cupy as cp
import gravite_gpu as GG


def tirage(n, rng):
    def plummer(k, a):
        r = a / np.sqrt(rng.uniform(1e-6, 1, k) ** (-2 / 3) - 1)
        u = rng.normal(size=(k, 3)); u /= np.linalg.norm(u, axis=1)[:, None]
        return r[:, None] * u
    k = n // 3
    a = plummer(k, 20.0)
    b = plummer(k, 5.0) + np.array([300.0, -150.0, 80.0])
    R = rng.exponential(3.0, n - 2 * k); f = rng.uniform(0, 2 * np.pi, n - 2 * k)
    c = np.stack([R * np.cos(f), R * np.sin(f), rng.normal(0, 0.3, n - 2 * k)], axis=1)
    pos = np.concatenate([a, b, c])
    m = np.concatenate([np.full(k, 3.0), np.full(k, 1.0), np.full(n - 2 * k, 0.2)])
    eps = np.concatenate([np.full(k, 0.4), np.full(k, 0.4), np.full(n - 2 * k, 0.1)])
    return pos, m, eps


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    rng = np.random.default_rng(1)
    pos, m, eps = (cp.asarray(x) for x in tirage(n, rng))
    idx = cp.asarray(rng.choice(n, 4000, replace=False))
    ad, pd = GG.gravity_direct(pos, m, eps, idx)
    ok = True
    for theta, quad, lim_med, lim_99 in ((0.5, False, 0.01, 0.05), (0.5, True, 0.002, 0.01), (0.7, True, 0.004, 0.02)):
        GG.gravity(pos, m, eps, theta=theta, quad=quad); cp.cuda.Stream.null.synchronize()
        t0 = time.time(); a, p = GG.gravity(pos, m, eps, theta=theta, quad=quad); cp.cuda.Stream.null.synchronize(); dt = time.time() - t0
        err = cp.asnumpy(cp.linalg.norm(a[idx] - ad, axis=1) / cp.linalg.norm(ad, axis=1))
        perr = cp.asnumpy(cp.abs(p[idx] - pd) / cp.abs(pd))
        med, p99 = float(np.median(err)), float(np.percentile(err, 99))
        # quantité de mouvement : la somme des forces doit être petite devant la somme de leurs normes
        mom = float(cp.linalg.norm((m[:, None] * a).sum(0)) / (m * cp.linalg.norm(a, axis=1)).sum())
        good = med < lim_med and p99 < lim_99 and float(np.median(perr)) < lim_med and bool(cp.isfinite(a).all())
        ok &= good
        print(f'theta {theta} quad {quad} : force médiane {100 * med:.3f} %, 99e centile {100 * p99:.3f} %, potentiel médian '
              f'{100 * float(np.median(perr)):.4f} %, somme des forces {mom:.1e}, {dt:.3f} s pour {n} particules -> {"PASSE" if good else "ÉCHEC"}')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
