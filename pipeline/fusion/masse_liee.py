#!/usr/bin/env python3
"""Masse liée de chaque galaxie, image par image (demande de Marc, 13/11/2026 : « si de la masse est prise du nuage vers
la galaxie, alors la masse doit augmenter »).

Dans le calcul, aucune particule ne disparaît ni n'apparaît : la masse totale est conservée exactement. Ce qui change, c'est
à QUI chaque particule appartient. Une particule appartient à une galaxie si elle lui est liée (énergie relative négative)
et se trouve dans son rayon de marée (rayon de Jacobi). On part de la plus petite galaxie : une étoile du Grand Nuage est
aussi liée à la Voie lactée, mais elle reste au Nuage tant qu'elle est dans son rayon de marée et liée à lui.

- Potentiel de chaque galaxie : sphérique, calculé sur ses membres de l'image précédente (masse dans r et couches
  extérieures), deux passes par image.
- Rayon de Jacobi de k dans j (plus massive) : d (M_k / (3 M_j(<d)))^(1/3) (Binney et Tremaine 2008, éq. 8.106).
- Énergie : ½ |v − v_k|² + Φ_k(|x − c_k|), v_k = vitesse moyenne des membres à moins de 5 kpc du centre.

Rend, pour chaque galaxie : masse liée totale (matière noire comprise), masse d'étoiles liée, et la part venue d'autres
galaxies ; plus la masse libre (liée à aucune). Unités : M☉, kpc, km/s.
"""
import numpy as np

G = 4.30091e-6


def _potentiel(r_membres, m_membres):
    """Fonction r -> Φ(r) d'une distribution sphérique (couches) : -G [M(<r)/r + Σ_{r_i > r} m_i / r_i]."""
    o = np.argsort(r_membres)
    r, m = np.maximum(r_membres[o], 1e-3), m_membres[o]
    dedans = np.cumsum(m)
    dehors = np.cumsum((m / r)[::-1])[::-1] - m / r      # couches strictement plus loin
    phi = -G * (dedans / r + dehors)
    total = dedans[-1] if len(dedans) else 0.0

    def f(x):
        if len(r) == 0: return np.zeros_like(x)
        i = np.clip(np.searchsorted(r, x), 0, len(r) - 1)
        loin = x > r[-1]
        return np.where(loin, -G * total / np.maximum(x, 1e-3), phi[i])

    def masse(x):
        return np.interp(x, r, dedans, left=0.0, right=total) if len(r) else 0.0
    return f, masse, total


def appartenance(pos, vel, m, etoile, membre, centres, n_passes=2):
    """membre : appartenance de l'image précédente (gid au départ), -1 = libre. Rend la nouvelle appartenance."""
    ng = len(centres)
    c = np.asarray(centres, float)
    for _ in range(n_passes):
        pots, masses_r, tot, vk = [], [], np.zeros(ng), np.zeros((ng, 3))
        for k in range(ng):
            s = membre == k
            r = np.linalg.norm(pos[s] - c[k], axis=1)
            f, mr, t = _potentiel(r, m[s])
            pots.append(f); masses_r.append(mr); tot[k] = t
            pres = s.copy(); pres[s] = r < 5.0
            vk[k] = np.average(vel[pres], axis=0, weights=m[pres]) if pres.any() else 0.0
        # rayon de marée de chaque galaxie dans les plus massives (le plus petit l'emporte)
        rj = np.full(ng, np.inf)
        for k in range(ng):
            for j in range(ng):
                if j == k or tot[j] <= tot[k] or tot[k] <= 0: continue
                d = max(np.linalg.norm(c[k] - c[j]), 1e-3)
                rj[k] = min(rj[k], d * (tot[k] / (3.0 * max(float(masses_r[j](d)), 1.0))) ** (1 / 3))
        nouveau = np.full(len(m), -1, np.int8)
        meilleur = np.full(len(m), np.inf)
        for k in np.argsort(tot):      # de la plus petite à la plus grande
            if tot[k] <= 0: continue
            r = np.linalg.norm(pos - c[k], axis=1)
            e = 0.5 * np.sum((vel - vk[k]) ** 2, axis=1) + pots[k](r)
            libre = nouveau < 0
            prend = libre & (e < 0) & (r < rj[k])
            nouveau[prend] = k; meilleur[prend] = e[prend]
        membre = nouveau
    return membre


def bilan(m, etoile, gid, membre, ng):
    """Par galaxie : [masse liée, masse d'étoiles liée, masse venue d'autres galaxies] ; plus la masse libre."""
    out = []
    for k in range(ng):
        s = membre == k
        out.append([float(m[s].sum()), float(m[s & etoile].sum()), float(m[s & (gid != k)].sum())])
    return out, float(m[membre < 0].sum())


if __name__ == '__main__':      # contrôle : deux amas de Plummer, le petit à 60 kpc du grand, se partagent leurs particules
    rng = np.random.default_rng(1)

    def plummer(n, M, a, c, v):
        r = a / np.sqrt(rng.random(n) ** (-2 / 3) - 1); r = np.minimum(r, 20 * a)
        u = rng.normal(size=(n, 3)); u /= np.linalg.norm(u, axis=1)[:, None]
        sig = np.sqrt(G * M / (6 * np.sqrt(r * r + a * a)))
        return u * r[:, None] + c, rng.normal(size=(n, 3)) * sig[:, None] + v, np.full(n, M / n)
    p1, v1, m1 = plummer(40000, 1e12, 20.0, np.zeros(3), np.zeros(3))
    p2, v2, m2 = plummer(10000, 1e11, 5.0, np.array([60.0, 0, 0]), np.array([0, 150.0, 0]))
    pos, vel, m = np.concatenate([p1, p2]), np.concatenate([v1, v2]), np.concatenate([m1, m2])
    gid = np.concatenate([np.zeros(40000, np.int8), np.ones(10000, np.int8)])
    memb = appartenance(pos, vel, m, np.ones(len(m), bool), gid.copy(), [np.zeros(3), np.array([60.0, 0, 0])])
    b, libre = bilan(m, np.ones(len(m), bool), gid, memb, 2)
    print('grand :', '%.3e' % b[0][0], 'venue du petit : %.3e' % b[0][2], '| petit : %.3e' % b[1][0], '| libre : %.3e' % libre,
          '| total conservé :', abs(b[0][0] + b[1][0] + libre - m.sum()) / m.sum() < 1e-12)
