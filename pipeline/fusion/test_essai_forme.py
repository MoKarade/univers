#!/usr/bin/env python3
"""Essai synthétique de essai_forme.py : un film propre doit passer, chaque défaut injecté doit être vu.

Film propre : une galaxie à disque (orbites circulaires, courbe de rotation plate 220 km/s, oscillation verticale) avec une
barre rigide qui tourne à 40 km/s/kpc, dont l'axe précesse lentement (10° en 2 Ga) et qui grossit lentement (+40 % en
2 Ga : une évolution réelle, rapide mais continue, ne doit PAS être prise pour une cassure) ; plus une galaxie sphéroïdale
qui s'approche. Une image toutes les 20 Ma, resserrée à 5 Ma entre 1,0 et 1,2 Ga (comme le film près d'un passage).

Défauts injectés (un par cas, à partir d'une image donnée) : forme remplacée par une autre (bascule), disque basculé
de 10°, 1 % des points perdus, barre tournée d'un coup de 30°, poids divisé par deux (fondu), centre décalé de 1 kpc.

Usage : python test_essai_forme.py   (rend 0 si tout est conforme)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import essai_forme as E      # noqa: E402

KPC_KMS_GA = 1.0227          # 1 km/s ≈ 1,0227 kpc/Ga


def rot(axe, ang):
    axe = np.asarray(axe, float) / np.linalg.norm(axe)
    K = np.array([[0, -axe[2], axe[1]], [axe[2], 0, -axe[0]], [-axe[1], axe[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


def fabriquer(defaut=None, i_defaut=60, n=40000, graine=1):
    rng = np.random.default_rng(graine)
    t = np.concatenate([np.arange(0, 1.0, 0.02), np.arange(1.0, 1.2, 0.005), np.arange(1.2, 2.0001, 0.02)])
    # disque : R exponentiel (Rd 3 kpc), phase, hauteur
    R0 = rng.gamma(2.0, 3.0, n)
    phi0 = rng.uniform(0, 2 * np.pi, n)
    zamp, zph = rng.exponential(0.3, n), rng.uniform(0, 2 * np.pi, n)
    nb = n // 5      # barre : points sur une ellipse 4 × 1,2 kpc qui tourne d'un bloc
    xb, yb = rng.normal(0, 1.6, nb), rng.normal(0, 0.5, nb)
    # sphéroïde compagnon
    ns = n // 4
    sph = rng.normal(0, 2.0, (ns, 3))
    images = []
    for k, tk in enumerate(t):
        echelle = 1 + 0.2 * tk                                   # grossit de 40 % en 2 Ga (continu)
        om = 220 * KPC_KMS_GA / np.maximum(R0 * echelle, 0.3)    # rad/Ga
        phi = phi0 + om * tk
        x, y = R0 * echelle * np.cos(phi), R0 * echelle * np.sin(phi)
        z = zamp * np.sin(zph + 2 * np.pi * tk / 0.08)
        ang_b = 40 * KPC_KMS_GA * tk                             # barre : 40 km/s/kpc
        if defaut == 'barre' and k >= i_defaut:
            ang_b += np.radians(30)
        cb, sb = np.cos(ang_b), np.sin(ang_b)
        bar = np.stack([xb * cb - yb * sb, xb * sb + yb * cb, rng.normal(0, 0.2, nb) * 0 + zamp[:nb] * 0.5], axis=1)
        disque = np.concatenate([np.stack([x, y, z], axis=1), bar])
        if defaut == 'bascule' and k >= i_defaut:               # autre tirage, plus compact : la forme change d'un coup
            r2 = np.random.default_rng(99).gamma(2.0, 2.0, len(disque))
            p2 = np.random.default_rng(98).uniform(0, 2 * np.pi, len(disque))
            disque = np.stack([r2 * np.cos(p2), r2 * np.sin(p2), disque[:, 2]], axis=1)
        tilt = np.radians(10) * tk / 2.0
        if defaut == 'basculement' and k >= i_defaut:
            tilt += np.radians(10)
        M = rot([1, 0.3, 0], tilt)
        disque = disque @ M.T
        vel = None
        c_d = np.array([0.0, 0.0, 0.0])
        w = np.ones(len(disque))
        if defaut == 'fondu' and k >= i_defaut:
            w = w * 0.5
        centre_ecrit = c_d.copy()
        if defaut == 'centre' and k >= i_defaut:
            centre_ecrit = c_d + np.array([1.0, 0, 0])
        if defaut == 'perte' and k >= i_defaut:
            garde = np.arange(len(disque)) % 100 != 0
            disque, w = disque[garde], w[garde]
        c_s = np.array([300.0 - 100 * tk, 50.0, 0.0])
        images.append([dict(pos=disque, vel=vel, w=w, centre=centre_ecrit),
                       dict(pos=sph + c_s, vel=None, w=np.ones(ns), centre=c_s)])
    return E.Film(t, ['disque', 'spheroide'], lambda i: images[i])


def fabriquer_bruite(defaut=None, i_defaut=60, n=20000, graine=2):
    """Film BRUITÉ : vraies orbites (saute-mouton, pas 1 Ma) de points d'essai agités (30 km/s) dans un potentiel
    logarithmique aplati (v0 220 km/s, q 0,9). Le bruit des mesures est celui d'un vrai tirage de 20 000 points :
    il ne doit pas déclencher de fausse cassure, et une bascule doit rester visible au-dessus de lui."""
    rng = np.random.default_rng(graine)
    v0, rc, q = 220.0, 0.5, 0.9
    def acc(x):
        d = rc ** 2 + x[:, 0] ** 2 + x[:, 1] ** 2 + (x[:, 2] / q) ** 2
        return -v0 ** 2 * np.stack([x[:, 0], x[:, 1], x[:, 2] / q ** 2], axis=1) / d[:, None]
    R = rng.gamma(2.0, 2.5, n); ph = rng.uniform(0, 2 * np.pi, n)
    x = np.stack([R * np.cos(ph), R * np.sin(ph), rng.normal(0, 0.3, n)], axis=1)
    vc = v0 * R / np.sqrt(rc ** 2 + R ** 2)
    v = np.stack([-vc * np.sin(ph), vc * np.cos(ph), np.zeros(n)], axis=1) + rng.normal(0, 30.0, (n, 3)) * np.array([1, 1, 0])
    nu = v0 / (q * np.sqrt(rc ** 2 + R ** 2))     # fréquence verticale près du plan : agitation verticale à l'équilibre
    v[:, 2] = rng.normal(0, 1, n) * 0.3 * nu
    dt = 0.001 / KPC_KMS_GA * 1.0      # 1 Ma en unités kpc/(km/s)
    t, images = [], []
    pas_par_image = 20
    for k in range(101):
        if k:
            for _ in range(pas_par_image):
                v += 0.5 * dt * acc(x); x += dt * v; v += 0.5 * dt * acc(x)
        pos, w = x.copy(), np.ones(n)
        if defaut == 'bascule' and k >= i_defaut:     # même nombre de points, autre forme (disque 30 % plus compact)
            pos = pos * np.array([0.7, 0.7, 1.0])
        images.append([dict(pos=pos, vel=v.copy(), w=w, centre=np.zeros(3))])
        t.append(k * 0.02)
    return E.Film(np.array(t), ['disque'], lambda i: images[i])


def main():
    silence = lambda *a: None
    for defaut, attendu in ((None, False), ('bascule', True)):
        rap = E.analyser(fabriquer_bruite(defaut), journal=silence)
        vu = rap['galaxies']['disque']['cassures']
        ok = (len(vu) > 0) == attendu and (not attendu or any(c['image'] in (59, 60) for c in vu))
        print(f'{"conforme" if ok else "NON CONFORME":12s} film bruité, défaut {defaut or "aucun":12s} cassures {len(vu):3d}  '
              + ", ".join(sorted({c['grandeur'] for c in vu})) + ('' if ok else '  ' + str(vu[:3])))
        if not ok:
            return 1
    cas = [(None, False)] + [(d, True) for d in ('bascule', 'basculement', 'perte', 'barre', 'fondu', 'centre')]
    echecs = 0
    for defaut, attendu in cas:
        film = fabriquer(defaut)
        rap = E.analyser(film, journal=silence)
        vu = rap['galaxies']['disque']['cassures']
        n = len(vu)
        grandeurs = sorted({c['grandeur'] for c in vu})
        ok = (n > 0) == attendu and rap['galaxies']['spheroide']['cassures'] == []
        if attendu and ok:      # la cassure doit être vue à l'image du défaut (ou juste avant : résidu partagé)
            ok = any(c['image'] in (59, 60) for c in vu)
        print(f'{"conforme" if ok else "NON CONFORME":12s} défaut {defaut or "aucun":12s} cassures {n:3d}  {", ".join(grandeurs)}')
        echecs += not ok
    print('PASSE' if echecs == 0 else f'ECHEC : {echecs} cas')
    return 1 if echecs else 0


if __name__ == '__main__':
    sys.exit(main())
