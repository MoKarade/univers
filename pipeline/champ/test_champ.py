#!/usr/bin/env python3
"""Contrôle de précision de champ_bfe.py contre des potentiels EXACTS (pas contre une somme directe, trop bruitée près
des particules).

Galaxie d'essai, tirée en particules :
- halo de Hernquist (1 × 10¹² M☉, a = 20 kpc), tiré jusqu'à 400 kpc (au-dedans, la coupure ne change pas la force) ;
- bulbe de Hernquist (1 × 10¹⁰ M☉, a = 0,6 kpc) ;
- disque de Miyamoto–Nagai (6 × 10¹⁰ M☉, a = 3 kpc, b = 0,3 kpc), tiré sans coupure utile (100 Mpc) ;
- cas « décentré » : un second disque de Miyamoto–Nagai (1 × 10¹⁰, a = 1,5, b = 0,3) décalé de 2 kpc dans le plan et
  incliné de 20° : il excite toutes les harmoniques m et l (barre, dissymétrie, gauchissement).
Le disque est donné dans un repère tourné (son axe n'est pas z) : la fonction doit le retrouver par l'axe passé.

Points d'essai : 3 000 dans le disque (R de 0,5 à 30 kpc, |z| < 1 kpc), 2 000 dans le halo (r de 1 à 300 kpc).
Mesure : écart relatif de la force, |F_bfe − F_exact| / |F_exact|. Il contient le bruit du tirage lui-même (un nombre
fini de particules n'a pas exactement le champ du modèle lisse) : cet écart baisse comme 1/√N (halo seul, de 1 à 5 kpc :
6,9 % à 200 000 particules, 3,6 % à 800 000, 2,0 % à 3,2 M), c'est donc le tirage et non la méthode qui le fixe.

Usage : python test_champ.py [particules par composante, défaut 500000] [--reference dossier]
  --reference : écrit aussi champ.chp et points.txt pour l'essai C++ (natif/physique/essais/essai_champ_bfe.cpp).
"""
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import champ_bfe as C      # noqa: E402

G = C.G


def tirer_hernquist(M, a, rmax, n, rng):
    u = rng.uniform(0, (rmax / (rmax + a)) ** 2, n)
    r = a * np.sqrt(u) / (1 - np.sqrt(u))
    v = rng.normal(size=(n, 3)); v /= np.linalg.norm(v, axis=1)[:, None]
    return r[:, None] * v, np.full(n, M * (rmax / (rmax + a)) ** 2 / n)


def rho_mn(R, z, M, a, b):
    s = np.sqrt(z * z + b * b)
    return b * b * M / (4 * math.pi) * (a * R * R + (a + 3 * s) * (a + s) ** 2) / ((R * R + (a + s) ** 2) ** 2.5 * s ** 3)


def tirer_mn(M, a, b, rmax, n, rng):
    """Rejet : proposition R de Kuzmin (échelle a + b), z de Cauchy (échelle b)."""
    out = []
    c = a + b
    while sum(len(o) for o in out) < n:
        k = 4 * n
        u = rng.uniform(0, 1, k)
        R = c * np.sqrt(1 / (1 - u) ** 2 - 1)
        z = b * np.tan(rng.uniform(-math.pi / 2, math.pi / 2, k))
        q_prop = (R * c / (R * R + c * c) ** 1.5) * (b / (math.pi * (z * z + b * b)))   # densités des propositions
        cible = 2 * math.pi * R * rho_mn(R, z, 1.0, a, b)
        rap = cible / q_prop
        if not out:
            borne = 1.2 * np.max(rap)
        ok = (rng.uniform(0, 1, k) * borne < rap) & (R * R + z * z < rmax * rmax)
        ph = rng.uniform(0, 2 * math.pi, ok.sum())
        out.append(np.stack([R[ok] * np.cos(ph), R[ok] * np.sin(ph), z[ok]], 1))
    p = np.concatenate(out)[:n]
    return p, np.full(n, M / n)


def force_hernquist(x, M, a):
    r = np.linalg.norm(x, axis=1)
    return -(G * M / (r * (r + a) ** 2))[:, None] * x


def force_mn(x, M, a, b):
    R2 = x[:, 0] ** 2 + x[:, 1] ** 2
    s = np.sqrt(x[:, 2] ** 2 + b * b)
    D = (R2 + (a + s) ** 2) ** 1.5
    fR = -G * M / D
    return np.stack([fR * x[:, 0], fR * x[:, 1], fR * x[:, 2] * (a + s) / s], 1)


def rot(axe, ang):
    axe = np.asarray(axe, float) / np.linalg.norm(axe)
    K = np.array([[0, -axe[2], axe[1]], [axe[2], 0, -axe[0]], [-axe[1], axe[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


def essai(n, decentre, rng):
    ph, mh = tirer_hernquist(1e12, 20.0, 400.0, n, rng)
    pb, mb = tirer_hernquist(1e10, 0.6, 400.0, n // 4, rng)
    pd, md = tirer_mn(6e10, 3.0, 0.3, 1e5, n, rng)
    comp = [(ph, mh, 0), (pb, mb, 2), (pd, md, 1)]
    M2 = rot([0, 1, 0], math.radians(20)); dec = np.array([2.0, 0, 0])
    if decentre:
        p2, m2 = tirer_mn(1e10, 1.5, 0.3, 1e5, n // 4, rng)
        comp.append((p2 @ M2.T + dec, m2, 1))
    pos = np.concatenate([c[0] for c in comp]); m = np.concatenate([c[1] for c in comp])
    kind = np.concatenate([np.full(len(c[0]), c[2]) for c in comp])
    # le tout tourné : l'axe du disque n'est plus z
    Rg = rot([1, 2, 0.5], math.radians(35))
    axe = Rg @ np.array([0, 0, 1.0])
    t0 = time.time()
    coef = C.coefficients(pos @ Rg.T, m, kind, axe=axe)
    duree = time.time() - t0
    # points d'essai (repère du disque, puis tournés)
    k = 3000
    R = rng.uniform(0.5, 30, k); phi = rng.uniform(0, 2 * math.pi, k); z = rng.uniform(-1, 1, k)
    xd = np.stack([R * np.cos(phi), R * np.sin(phi), z], 1)
    v = rng.normal(size=(2000, 3)); v /= np.linalg.norm(v, axis=1)[:, None]
    xh = v * np.exp(rng.uniform(0, math.log(300), 2000))[:, None]
    res = {}
    for nom, x in (('disque', xd), ('halo', xh)):
        Fex = force_hernquist(x, 1e12, 20.0) + force_hernquist(x, 1e10, 0.6) + force_mn(x, 6e10, 3.0, 0.3)
        if decentre:
            Fex += force_mn((x - dec) @ M2, 1e10, 1.5, 0.3) @ M2.T
        _, F = C.evaluer(coef, x @ Rg.T)
        F = F @ Rg      # retour au repère du disque
        e = np.linalg.norm(F - Fex, axis=1) / np.linalg.norm(Fex, axis=1)
        res[nom] = (np.median(e), np.quantile(e, 0.95), np.max(e))
    return res, duree, coef


def ecrire_reference(dossier, coef, rng):
    """Fichiers pour natif/physique/essais/essai_champ_bfe.cpp : le champ en binaire et 2 000 points avec la valeur de
    Python, calculée sur les tableaux arrondis en 32 bits comme ceux du fichier."""
    os.makedirs(dossier, exist_ok=True)
    c32 = C.charger(_npz(coef, dossier))
    C.sauver_bin(c32, os.path.join(dossier, 'champ.chp'))
    x = np.concatenate([rng.normal(size=(1000, 3)) * np.array([8, 8, 0.5]), rng.normal(size=(1000, 3)) * 60,
                        [[0.0, 0, 0.01], [500, 0, 0], [0, 0, 3000]]])
    phi, F = C.evaluer(c32, x)
    np.savetxt(os.path.join(dossier, 'points.txt'), np.column_stack([x, phi, F]), fmt='%.17g')
    print('référence écrite dans', dossier)


def _npz(coef, dossier):
    chemin = os.path.join(dossier, 'champ.npz')
    C.sauver(coef, chemin)
    return chemin


def essai_noyau():
    """Q_{m−1/2}(χ) contre la série hypergéométrique (de 1,5 à 10⁸) et contre la quadrature (près de 1)."""
    from scipy.special import gamma, hyp2f1
    chi = np.geomspace(1.5, 1e8, 2000)
    q = C.noyau_Q(chi, 6)
    ref = lambda nu, x: math.sqrt(math.pi) * gamma(nu + 1) / (gamma(nu + 1.5) * (2 * x) ** (nu + 1)) * hyp2f1((nu + 2) / 2, (nu + 1) / 2, nu + 1.5, 1 / x ** 2)
    e1 = max(np.max(np.abs(q[m] / ref(m - 0.5, chi) - 1)) for m in range(7))
    ph = np.linspace(0, math.pi, 200001)
    e2 = 0.0
    for x in (1.001, 1.05, 1.4):
        qq = C.noyau_Q(np.array([x]), 6)[:, 0]
        for m in range(7):
            r = np.trapezoid(np.cos(m * ph) / np.sqrt(x - np.cos(ph)), ph) / math.sqrt(2)
            e2 = max(e2, abs(qq[m] / r - 1))
    print(f'noyau Q_(m-1/2) : écart au plus {e1:.1e} (série, χ ≥ 1,5), {e2:.1e} (quadrature, χ < 1,5)')
    return e1 < 1e-10 and e2 < 1e-6


def main():
    args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] != '--reference']
    n = int(args[0]) if args else 500_000
    rng = np.random.default_rng(7)
    echec = not essai_noyau()
    for decentre in (False, True):
        res, duree, coef = essai(n, decentre, rng)
        nom = 'galaxie décentrée (deuxième disque incliné et décalé)' if decentre else 'galaxie symétrique'
        print(f'{nom} : {n} particules par composante, coefficients en {duree:.1f} s')
        for zone, (med, q95, mx) in res.items():
            print(f'   {zone:7s} écart de force : médiane {100 * med:.2f} %, 95 % des points sous {100 * q95:.2f} %, pire {100 * mx:.1f} %')
            echec |= med > 0.01 or q95 > 0.03      # critère [Supposition] : médiane < 1 %, 95 % des points < 3 % (bruit des particules compris)
    # aller-retour par fichier (float32)
    chemin = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'champ_essai.npz')
    C.sauver(coef, chemin)
    c2 = C.charger(chemin)
    x = rng.normal(size=(500, 3)) * 5
    d = np.linalg.norm(C.evaluer(coef, x)[1] - C.evaluer(c2, x)[1], axis=1) / np.linalg.norm(C.evaluer(coef, x)[1], axis=1)
    print(f'fichier : {os.path.getsize(chemin) / 1e6:.2f} Mo ; écart dû au passage en float32 : au plus {100 * d.max():.4f} %')
    if '--reference' in sys.argv:
        ecrire_reference(sys.argv[sys.argv.index('--reference') + 1], coef, rng)
    print('PASSE' if not echec else 'ECHEC')
    return 1 if echec else 0


if __name__ == '__main__':
    sys.exit(main())
