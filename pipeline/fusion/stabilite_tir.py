#!/usr/bin/env python3
"""Tir de stabilité : une galaxie SEULE, toutes ses particules s'attirent, sur la carte graphique.

Entrée : le .npz écrit par modeles_v2.py. Sortie : un .json avec, tous les 50 millions d'années, ce qui dit si le disque
reste calme ou forme une barre :
- force de la barre et des bras : amplitude du motif à deux bras (A2) des étoiles du disque, par anneau ;
- angle de la barre, d'où sa vitesse de rotation entre deux relevés ;
- épaisseur (médiane de |z|) et agitation radiale des étoiles, par anneau ;
- vitesse de rotation moyenne à quelques rayons ;
- dérive d'énergie et déplacement du centre de masse (contrôles du calcul).

Même schéma que calcul.py (saute-mouton, pas fixe). La carte est rendue à Marc de la même façon : pause si un autre
programme l'occupe.

Usage : python stabilite_tir.py <depart.npz> <durée en Ga> <sortie.json> [--pas-ma=0.25] [--theta=0.7] [--releve-ma=50]
           [--guide=masse,a,omega,monte,tenue,descente[,b,c,angle0]] [--etat-final=<galaxie mûrie.npz>]
  --guide : barre « guide » qui tourne (masse en M☉, demi-longueur en kpc, vitesse en km/s/kpc, durées en Ga) : elle entraîne
            le centre du disque en barre, puis s'efface ; ce qui reste est une barre faite des étoiles elles-mêmes.
  --releve-ma=10 pour lire la vitesse de rotation d'une barre (son angle doit tourner de moins d'un quart de tour entre deux relevés).
"""
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
import cupy as cp

import gravite_gpu

G = 4.30091e-6
T_UNIT = 0.9778      # Ga par unité de temps kpc/(km/s)
ANNEAUX = [(0.5, 2), (2, 4), (4, 6), (6, 9), (9, 13)]      # kpc


def releve(pos, vel, m, kind, t, e_rel, cm):
    """Mesures sur les étoiles du disque (kind 1 et 4), dans le repère du centre de la galaxie."""
    etoiles = (kind == 1) | (kind == 4)
    p = pos[etoiles]; v = vel[etoiles]; w = m[etoiles]
    c = np.average(p, axis=0, weights=w)
    for _ in range(8):      # centre des étoiles à moins de 5 kpc, resserré
        sel = np.linalg.norm(p - c, axis=1) < 5
        c = np.average(p[sel], axis=0, weights=w[sel])
    p = p - c
    v = v - np.average(v[np.linalg.norm(p, axis=1) < 5], axis=0)
    R = np.hypot(p[:, 0], p[:, 1]); phi = np.arctan2(p[:, 1], p[:, 0])
    vR = (p[:, 0] * v[:, 0] + p[:, 1] * v[:, 1]) / np.maximum(R, 1e-9)
    vphi = (p[:, 0] * v[:, 1] - p[:, 1] * v[:, 0]) / np.maximum(R, 1e-9)
    out = dict(t=round(t, 4), energie=e_rel, centre_de_masse_kpc=cm, anneaux=[])
    for a, b in ANNEAUX:
        s = (R >= a) & (R < b)
        if s.sum() < 100:
            out['anneaux'].append(None); continue
        z2 = np.sum(w[s] * np.exp(2j * phi[s])) / np.sum(w[s])
        out['anneaux'].append(dict(r=[a, b], a2=round(float(abs(z2)), 4), angle_deg=round(float(np.degrees(np.angle(z2)) / 2), 1), n=int(s.sum()),
                                   epaisseur_kpc=round(float(np.median(np.abs(p[s, 2]))), 3), sigma_r=round(float(np.std(vR[s])), 1),
                                   v_rotation=round(float(np.mean(vphi[s])), 1)))
    return out


def guide_barre(cp, pos, t, g):
    """Accélération d'une barre « guide » : une aiguille adoucie (Long et Murali 1992, ApJ 397, 44) qui tourne à vitesse
    fixe autour de +z. Elle n'a pas de particules : elle sert à entraîner le centre du disque sur des orbites de barre,
    puis elle est retirée ; la barre qui reste alors est faite des étoiles elles-mêmes. Sa masse monte, tient, puis descend
    (g : masse en M☉, demi-longueur a, largeurs b et c en kpc, vitesse en km/s/kpc, durées de montée, tenue, descente en Ga)."""
    tm, tt, td = g['monte'], g['tenue'], g['descente']
    if t < tm: f = 0.5 * (1 - math.cos(math.pi * t / tm))
    elif t < tm + tt: f = 1.0
    elif t < tm + tt + td: f = 0.5 * (1 + math.cos(math.pi * (t - tm - tt) / td))
    else: return None, 0.0
    if f <= 0: return None, 0.0
    ang = g['angle0'] + g['omega'] * 1.0227121650456 * t      # rad ; km/s/kpc -> rad/Ga
    co, si = math.cos(ang), math.sin(ang)
    x = pos[:, 0] * co + pos[:, 1] * si; y = -pos[:, 0] * si + pos[:, 1] * co; z = pos[:, 2]
    a, b, c = g['a'], g['b'], g['c']

    def phi(x, y, z):
        q = y * y + (b + cp.sqrt(c * c + z * z)) ** 2
        tp = cp.sqrt((a + x) ** 2 + q); tn = cp.sqrt((a - x) ** 2 + q)
        return G * f * g['masse'] / (2 * a) * cp.log((x - a + tn) / (x + a + tp))
    h = 1e-3
    ax = -(phi(x + h, y, z) - phi(x - h, y, z)) / (2 * h); ay = -(phi(x, y + h, z) - phi(x, y - h, z)) / (2 * h); az = -(phi(x, y, z + h) - phi(x, y, z - h)) / (2 * h)
    return cp.stack([ax * co - ay * si, ax * si + ay * co, az], axis=1), f


def attendre(t_check):
    if time.time() - t_check < 30: return t_check
    cp.cuda.Stream.null.synchronize()
    while True:
        time.sleep(1.0)
        try:
            u = int(subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=20,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.split()[0])
        except Exception:
            break
        if u < 35: break
        print(f'  carte graphique occupée à {u} % par un autre programme : pause de 60 s', flush=True)
        time.sleep(60)
    return time.time()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    depart, duree, sortie = args[0], float(args[1]), args[2]
    dt_ma, theta = float(opts.get('pas-ma', 0.25)), float(opts.get('theta', 0.7))
    with np.load(depart) as z:
        p = {k: z[k] for k in ('pos', 'vel', 'm', 'eps', 'kind')}
        meta = json.loads(str(z['meta'])) if 'meta' in z else {}
    kind = p['kind']
    pos = cp.asarray(p['pos'], dtype=cp.float64); vel = cp.asarray(p['vel'], dtype=cp.float64)
    m = cp.asarray(p['m'], dtype=cp.float64); eps = cp.asarray(p['eps'], dtype=cp.float64); mg = m * G
    dt = dt_ma * 1e-3 / T_UNIT
    steps = int(round(duree * 1000 / dt_ma)); every = int(round(float(opts.get('releve-ma', 50.0)) / dt_ma))
    guide = None
    if 'guide' in opts:      # --guide=masse,a,omega,monte,tenue,descente[,b,c,angle0]
        v = [float(x) for x in opts['guide'].split(',')]
        guide = dict(masse=v[0], a=v[1], omega=v[2], monte=v[3], tenue=v[4], descente=v[5], b=v[6] if len(v) > 6 else 0.6, c=v[7] if len(v) > 7 else 0.35, angle0=v[8] if len(v) > 8 else 0.0)

    def forces(t):
        acc, phi = gravite_gpu.gravity(pos, mg, eps, theta=theta, quad=True)
        if guide:
            ag, f = guide_barre(cp, pos - cm_gpu(), t, guide)
            if ag is not None: acc = acc + ag
        return acc, phi

    def cm_gpu():
        return cp.sum(pos * m[:, None], axis=0) / cp.sum(m)

    acc, phi = forces(0.0)

    def energie(phi):
        return 0.5 * float(cp.sum(m * cp.sum(vel ** 2, axis=1))) + 0.5 * float(cp.sum(m * phi))

    e0 = energie(phi)
    cm0 = cp.asnumpy(cp.sum(pos * m[:, None], axis=0) / cp.sum(m))
    res = dict(depart=os.path.basename(depart), modele=meta, particules=int(len(p['m'])), pas_ma=dt_ma, theta=theta, releves=[])

    def note(t):
        cm = cp.asnumpy(cp.sum(pos * m[:, None], axis=0) / cp.sum(m)) - cm0
        r = releve(cp.asnumpy(pos), cp.asnumpy(vel), p['m'], kind, t, energie(phi) / e0 - 1, [round(float(x), 4) for x in cm])
        res['releves'].append(r)
        a = [x for x in r['anneaux'] if x]
        print(f"t = {t:5.2f} Ga | A2 par anneau : " + ' '.join(f"{x['a2']:.3f}" for x in a) + f" | épaisseur {a[2]['epaisseur_kpc']:.2f} kpc | agitation {a[3]['sigma_r']:.0f} km/s"
              f" | énergie {100 * r['energie']:+.3f} % | {time.time() - t0:5.0f} s", flush=True)
        json.dump(res, open(sortie + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False); os.replace(sortie + '.tmp', sortie)

    t0 = time.time(); t_check = time.time()
    note(0.0)
    for s in range(steps):
        vel += 0.5 * dt * acc
        pos += dt * vel
        acc, phi = forces((s + 1) * dt_ma * 1e-3)
        vel += 0.5 * dt * acc
        if (s + 1) % every == 0: note((s + 1) * dt_ma * 1e-3)
        t_check = attendre(t_check)
    # Verdict : calme si la force de la barre reste sous 0,1 partout ; la vitesse de la barre se lit entre deux relevés.
    pire = max(x['a2'] for r in res['releves'] for x in r['anneaux'] if x)
    res['a2_max'] = pire
    if guide: res['guide'] = guide
    if 'etat-final' in opts:      # la galaxie mûrie, au même format que modeles_v2.py : elle peut servir de départ à rencontre.py
        c0 = cp.asnumpy(cm_gpu()); v0 = cp.asnumpy(cp.sum(vel * m[:, None], axis=0) / cp.sum(m))
        meta2 = dict(meta); meta2['murie'] = dict(duree_ga=duree, guide=guide, depart=os.path.basename(depart))
        np.savez_compressed(opts['etat-final'], pos=cp.asnumpy(pos) - c0, vel=cp.asnumpy(vel) - v0, m=p['m'], eps=p['eps'], kind=kind, meta=json.dumps(meta2, ensure_ascii=False))
    json.dump(res, open(sortie, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f"force maximale du motif à deux bras : {pire:.3f} ({'disque calme' if pire < 0.1 else 'barre ou bras marqués'})")


if __name__ == '__main__':
    main()
