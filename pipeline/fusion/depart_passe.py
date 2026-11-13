#!/usr/bin/env python3
"""Départ du calcul du Groupe local dans le PASSÉ, pour qu'aujourd'hui tout soit déjà en mouvement (Marc, 13/11/2026 :
« tout a déjà une orientation et une destination avant que je presse Play »).

Pourquoi : un calcul qui part d'aujourd'hui pose des galaxies à l'équilibre, comme si elles venaient d'apparaître seules.
Au premier pas, le Grand Nuage commence à se déchirer « pile au moment où on appuie sur Play ». En vrai, il tombe vers la
Voie lactée depuis plus d'un milliard d'années et traîne déjà ses débris. Méthode publiée pour cela : remonter le temps
avec les orbites des centres (frottement dynamique compris), poser les galaxies à l'équilibre à cette date passée, puis
laisser le calcul complet ramener tout à aujourd'hui (Besla et al. 2012, MNRAS 421, 2109 ; Garavito-Camargo et al. 2019,
ApJ 884, 51). Les écarts d'aujourd'hui avec les mesures sont corrigés par tirs successifs (`--cible` : on décale le
point visé de l'écart trouvé et on recommence).

Remontée (rapide, sur le processeur) : chaque galaxie est une masse étendue dont le profil (masse dans le rayon r) est
mesuré sur ses propres particules ; attraction mutuelle ; frottement dynamique de Chandrasekhar de la plus petite dans la
plus grande ; énergie noire (energie_noire.py). Les naines (traceurs sans masse) remontent dans le champ des quatre.

Entrée : depart.npz « aujourd'hui » (calcul.py depart N, AGAMA). Sortie : depart.npz dont les galaxies sont placées à
-T Ga, meta['debut_ga'] = -T. Le calcul se lance ensuite par : calcul.py -T 10 --gpu (repart de -T).
Usage : python depart_passe.py <depart_aujourdhui.npz> <sortie.npz> [--remonter=2.0] [--reduire=10] [--cible=ecarts.json]
  --reduire=K : garde une particule sur K (masse × K, adoucissement × K^(1/3)) pour les essais rapides de tir.
"""
import json, math, sys
import numpy as np
import energie_noire as EN

G = 4.30091e-6                     # kpc (km/s)² / M☉
T_UNIT = 0.9778                    # Ga par unité kpc/(km/s)
R_GRILLE = np.logspace(-1, 3.3, 400)


def centre_vitesse(pos, vel, m):
    """Centre par sphère qui rétrécit (comme calcul.centre) et vitesse moyenne des particules à moins de 5 kpc de lui."""
    c = np.average(pos, axis=0, weights=m); r = np.percentile(np.linalg.norm(pos - c, axis=1), 90)
    while r > 1.0:
        sel = np.linalg.norm(pos - c, axis=1) < r
        if sel.sum() < 200: break
        c = np.average(pos[sel], axis=0, weights=m[sel]); r *= 0.85
    sel = np.linalg.norm(pos - c, axis=1) < 5.0
    return c, np.average(vel[sel], axis=0, weights=m[sel])


class Profil:
    """Masse dans le rayon r d'une galaxie, mesurée sur ses particules (sphérique), avec densité et vitesse circulaire."""
    def __init__(self, r, m):
        o = np.argsort(r); rs, cum = r[o], np.cumsum(m[o])
        self.M = np.interp(R_GRILLE, rs, cum, left=0.0, right=cum[-1])
        self.total = cum[-1]
        self.r_bord = float(np.interp(0.99 * cum[-1], cum, rs))
        self.a_moitie = float(np.interp(0.5 * cum[-1], cum, rs))
        dM = np.gradient(self.M, R_GRILLE)
        self.rho = np.maximum(dM, 0) / (4 * math.pi * R_GRILLE ** 2)

    def masse(self, r): return np.interp(r, R_GRILLE, self.M, right=self.total)
    def densite(self, r): return np.interp(r, R_GRILLE, self.rho, right=0.0)
    def vc(self, r): return np.sqrt(G * self.masse(r) / np.maximum(r, 1e-3))


def accelerations(X, V, prof, masses, tracers=None):
    """Accélérations des centres (N, 3) et des traceurs (T, 3) : gravité des profils, frottement, énergie noire."""
    N = len(X)
    A = np.zeros_like(X)
    for i in range(N):
        for j in range(N):
            if i == j: continue
            d = X[i] - X[j]; r = max(np.linalg.norm(d), 1e-3)
            A[i] -= G * prof[j].masse(r) * d / r ** 3
            if masses[j] > masses[i] and r < prof[j].r_bord:      # frottement dynamique (Chandrasekhar) de i dans j
                dv = V[i] - V[j]; v = max(np.linalg.norm(dv), 5.0)
                sig = prof[j].vc(r) / math.sqrt(2.0)
                x = v / (math.sqrt(2.0) * sig)
                ln_l = max(math.log(r / (1.6 * prof[i].a_moitie)), 0.0)      # Hashimoto et al. 2003 (ε = 1,6 × échelle)
                f = math.erf(x) - 2 * x / math.sqrt(math.pi) * math.exp(-x * x)
                A[i] -= 4 * math.pi * G * G * masses[i] * prof[j].densite(r) * ln_l * f / v ** 3 * dv
    cm = (masses[:, None] * X).sum(0) / masses.sum()
    A += EN.acceleration(X, cm)
    if tracers is None: return A, None
    At = np.zeros_like(tracers)
    for j in range(N):
        d = tracers - X[j]; r = np.maximum(np.linalg.norm(d, axis=1), 1e-3)
        At -= (G * prof[j].masse(r) / r ** 3)[:, None] * d
    At += EN.acceleration(tracers, cm)
    return A, At


def remonter(X, V, prof, masses, Tx, Tv, t_ga, dt_ma=0.5):
    """Saute-mouton à rebours de t_ga milliards d'années (pas négatif). Rend positions et vitesses au départ."""
    n = int(round(t_ga * 1000 / dt_ma)); h = -dt_ma * 1e-3 / T_UNIT
    X, V, Tx, Tv = X.copy(), V.copy(), Tx.copy(), Tv.copy()
    A, At = accelerations(X, V, prof, masses, Tx)
    for _ in range(n):
        V += 0.5 * h * A; Tv += 0.5 * h * At
        X += h * V; Tx += h * Tv
        A, At = accelerations(X, V, prof, masses, Tx)
        V += 0.5 * h * A; Tv += 0.5 * h * At
    return X, V, Tx, Tv


def main():
    src, out = sys.argv[1], sys.argv[2]
    T, K, cible = 2.0, 1, None
    for a in sys.argv[3:]:
        if a.startswith('--remonter='): T = float(a.split('=', 1)[1])
        if a.startswith('--reduire='): K = int(a.split('=', 1)[1])
        if a.startswith('--cible='): cible = json.load(open(a.split('=', 1)[1], encoding='utf-8'))
    z = np.load(src)
    p = {k: z[k].copy() for k in ('pos', 'vel', 'm', 'eps', 'kind')}
    gid, show, meta = z['gid'].copy(), z['show'].copy(), json.loads(str(z['meta']))
    ng = len(meta['galaxies'])
    if K > 1:      # essai rapide : une particule sur K, masse × K
        rng = np.random.default_rng(20261113)
        garde = np.where(p['kind'] == 9, True, rng.random(len(p['m'])) < 1.0 / K)
        idx = np.where(garde)[0]
        nouveau = -np.ones(len(p['m']), np.int64); nouveau[idx] = np.arange(len(idx))
        for k in p: p[k] = p[k][idx]
        gid = gid[idx]; show = nouveau[show]; show = show[show >= 0]
        etoile = p['kind'] < 9
        p['m'][etoile] *= K; p['eps'][etoile] *= K ** (1 / 3)
        meta['affichees'] = [int(np.sum((gid[show] == k))) for k in range(ng)]
    X, V, prof, masses = np.zeros((ng, 3)), np.zeros((ng, 3)), [], np.zeros(ng)
    for k in range(ng):
        s = gid == k
        X[k], V[k] = centre_vitesse(p['pos'][s], p['vel'][s], p['m'][s])
        prof.append(Profil(np.linalg.norm(p['pos'][s] - X[k], axis=1), p['m'][s]))
        masses[k] = prof[-1].total
    X0, V0 = X.copy(), V.copy()
    if cible:      # tir corrigé : viser aujourd'hui (mesure − écart trouvé au tir précédent)
        X -= np.array(cible['ecart_pos']); V -= np.array(cible['ecart_vel'])
    tr = np.where(p['kind'] == 9)[0]
    Xp, Vp, Tx, Tv = remonter(X, V, prof, masses, p['pos'][tr], p['vel'][tr], T)
    for k in range(ng):
        s = gid == k
        p['pos'][s] += Xp[k] - X0[k]; p['vel'][s] += Vp[k] - V0[k]
    p['pos'][tr], p['vel'][tr] = Tx, Tv
    m = p['m'][:, None]; cm = (p['pos'] * m).sum(0) / m.sum(); vm = (p['vel'] * m).sum(0) / m.sum()
    p['pos'] -= cm; p['vel'] -= vm
    meta['debut_ga'] = -T
    meta['depart_passe'] = dict(remonter_ga=T, reduire=K, cible=cible, methode='orbites des centres à rebours (profils mesurés sur les particules, '
                                'frottement de Chandrasekhar, énergie noire), puis calcul complet vers aujourd’hui (Besla 2012, Garavito-Camargo 2019)',
                                centres_aujourdhui=X0.round(3).tolist(), vitesses_aujourdhui=V0.round(3).tolist(),
                                centres_depart=(Xp - cm).round(3).tolist(), vitesses_depart=(Vp - vm).round(3).tolist())
    np.savez_compressed(out, gid=gid, show=show, meta=json.dumps(meta, ensure_ascii=False), **p)
    sep = lambda A, i, j: np.linalg.norm(A[i] - A[j])
    print(json.dumps(dict(particules=int((p['kind'] < 9).sum()), remonter_ga=T,
                          separations_aujourdhui_kpc={n: round(float(sep(X0, 0, k)), 1) for k, n in enumerate(meta['galaxies']) if k},
                          separations_depart_kpc={n: round(float(sep(Xp, 0, k)), 1) for k, n in enumerate(meta['galaxies']) if k},
                          m33_m31_depart_kpc=round(float(sep(Xp, 1, 2)), 1)), ensure_ascii=False))


if __name__ == '__main__':
    main()
