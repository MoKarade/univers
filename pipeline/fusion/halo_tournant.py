#!/usr/bin/env python3
"""Écrit dans le fichier d'une galaxie de départ la rotation de son halo de matière noire.

Une part des particules de matière noire qui tournent à l'envers du disque voient leur vitesse de rotation retournée
(même énergie, même profil : l'équilibre est gardé). Un halo qui tourne avec le disque prend moins de moment cinétique à
la barre, qui grossit et ralentit moins (Long, Shlosman & Heller 2014 ; Collier, Shlosman & Heller 2018). Les halos des
simulations cosmologiques tournent (paramètre de rotation ~0,035) ; part 0,35 -> 0,038 pour la Voie lactée.
Même règle et même graine que stabilite_tir.py --halo-tourne (essais des 18 et 19/11/2026).

Usage : python halo_tournant.py <galaxie.npz> <sortie.npz> [part=0.35]
"""
import json
import sys

import numpy as np

G = 4.30091e-6


def main():
    entree, sortie = sys.argv[1:3]; f = float(sys.argv[3]) if len(sys.argv) > 3 else 0.35
    with np.load(entree) as z: p = {k: z[k] for k in z.files}
    kind = p['kind']; rng = np.random.default_rng(20261118)
    x, v = p['pos'].astype(np.float64), p['vel'].astype(np.float64)
    d = (kind == 1) | (kind == 4)
    sens = np.sign(np.sum(x[d, 0] * v[d, 1] - x[d, 1] * v[d, 0]))
    lz = x[:, 0] * v[:, 1] - x[:, 1] * v[:, 0]
    tourne = (kind == 0) & (lz * sens < 0) & (rng.uniform(size=len(kind)) < f)
    R2 = np.maximum(x[:, 0] ** 2 + x[:, 1] ** 2, 1e-12)
    vphi = lz / R2      # vitesse angulaire ; retourner la part de rotation : v -> v - 2 vphi (-y, x)
    v[tourne, 0] += 2 * vphi[tourne] * x[tourne, 1]; v[tourne, 1] -= 2 * vphi[tourne] * x[tourne, 0]
    h = kind == 0; r = np.linalg.norm(x[h], axis=1); dans = r < 200.0
    J = abs(float(np.sum(p['m'][h][dans] * (x[h][dans, 0] * v[h][dans, 1] - x[h][dans, 1] * v[h][dans, 0])))); M = float(p['m'][h][dans].sum())
    E = abs(float(0.5 * np.sum(p['m'][h][dans] * np.sum(v[h][dans] ** 2, axis=1))))      # énergie de liaison ~ énergie cinétique (viriel)
    lam = J * np.sqrt(E) / (G * M ** 2.5)
    p['vel'] = v.astype(p['vel'].dtype)
    if 'meta' in p:
        meta = json.loads(str(p['meta'])); meta['halo_tournant'] = dict(part=f, retournees=int(tourne.sum()), parametre_de_rotation=round(lam, 4)); p['meta'] = json.dumps(meta, ensure_ascii=False)
    np.savez(sortie, **p)
    print(f"{entree} : {int(tourne.sum())} particules de halo retournées (part {f}) ; paramètre de rotation {lam:.3f} -> {sortie}")


if __name__ == '__main__':
    main()
