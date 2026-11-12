#!/usr/bin/env python3
"""Calcul complet de la rencontre Voie lactée – Andromède (R9, docs/fusion-methode.md).

Quatre galaxies à particules (Voie lactée, Andromède, Triangle, Grand Nuage), toutes s'attirent (falcON). Le Soleil et les
autres galaxies naines sont des traceurs sans masse. Saute-mouton à pas fixe de 0,25 Ma. Le calcul se fait par morceaux
(une tâche GitHub dure au plus 6 heures) : chaque morceau reprend l'instantané du précédent.

Sorties (dossier `sortie/`) :
- kf_NNN.bin : images clés, 25 par fichier ; pour chaque image, les étoiles affichées en entiers 16 bits (pas 0,025 kpc,
  relatifs au centre de masse total) ;
- fusion.json : temps des images, centres des galaxies, traceurs (Soleil, naines), énergie, date de la fusion, liste des
  étoiles affichées par galaxie ;
- etat.npz : instantané pour reprendre.
Usage : python calcul.py <de_Ga> <a_Ga> [N_total]
"""
import os, sys, json, time, math
import numpy as np
import pyfalcon
import agama
import modeles as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'sortie')
G = M.G
T_UNIT = 0.9778                       # Ga par unité de temps kpc/(km/s)
DT_MA, KF_MA, KF_PER_FILE = 0.25, 20.0, 25
DT = DT_MA * 1e-3 / T_UNIT
Q = 0.025                             # kpc par unité des entiers 16 bits (± 819 kpc)
N_SHOW = {'mw': 12000, 'm31': 15000, 'm33': 2000, 'lmc': 1000}
EQ2GAL = np.array([[-0.0548755604, -0.8734370902, -0.4838350155],      # équatorial J2000 → galactique (Hipparcos, ESA 1997)
                   [0.4941094279, -0.4448296300, 0.7469822445],
                   [-0.8676661490, -0.1980763734, 0.4559837762]])


def construire(n_total):
    ci = json.load(open(os.path.join(HERE, 'conditions.json'), encoding='utf-8'))
    f = n_total / 300000
    mw = M.galaxie('Voie lactée', int(80000 * f), int(36000 * f), int(4000 * f))
    m31 = M.galaxie('Andromède', int(100000 * f), int(45000 * f), int(5000 * f), k_mass=1.5, k_r=1.15)
    m33 = M.galaxie('Triangle', int(12000 * f), int(6000 * f), 0, halo='plummer', mh=2.5e11, ah=21.0, md=4.8e9, rd=1.4)
    lmc = M.galaxie('Grand Nuage', int(8000 * f), int(4000 * f), 0, halo='hernquist', mh=1.8e11, ah=12.0, md=2.7e9, rd=1.5)
    tri = next(d for d in ci['dwarfs'] if 'Triangle' in d['name'])
    gals = [('mw', M.placer(mw, [0, 0, -1], [0, 0, 0], [0, 0, 0])),
            ('m31', M.placer(m31, ci['m31']['spin'], ci['m31']['pos'], ci['m31']['vel'])),
            ('m33', M.placer(m33, EQ2GAL @ np.array(ci['m33_spin']), tri['pos'], tri['vel'])),
            ('lmc', M.placer(lmc, EQ2GAL @ np.array(ci['lmc_spin']), ci['lmc']['pos'], ci['lmc']['vel']))]
    p = M.assembler(*[g for _, g in gals])
    gid = np.concatenate([np.full(len(g['m']), k, dtype=np.int8) for k, (_, g) in enumerate(gals)])
    # traceurs sans masse : le Soleil, puis les naines (sauf le Triangle, qui a ses particules)
    tr = [('Soleil', ci['sun']['pos'], ci['sun']['vel'])] + [(d['name'], d['pos'], d['vel']) for d in ci['dwarfs'] if 'Triangle' not in d['name']]
    p['pos'] = np.concatenate([p['pos'], np.array([t[1] for t in tr], float)]); p['vel'] = np.concatenate([p['vel'], np.array([t[2] for t in tr], float)])
    p['m'] = np.concatenate([p['m'], np.full(len(tr), 1.0)]);      # 1 M☉ : falcON refuse les masses nulles (NaN) ; attraction négligeable devant 10⁶ M☉ par particule
    p['eps'] = np.concatenate([p['eps'], np.full(len(tr), 0.1)])
    p['kind'] = np.concatenate([p['kind'], np.full(len(tr), 9, dtype=np.int8)]); gid = np.concatenate([gid, np.full(len(tr), -1, dtype=np.int8)])
    # repère du centre de masse (les traceurs n'ont pas de masse)
    m = p['m'][:, None]; cm = (p['pos'] * m).sum(0) / m.sum(); vm = (p['vel'] * m).sum(0) / m.sum()
    p['pos'] -= cm; p['vel'] -= vm
    rng = np.random.default_rng(20261111)
    show = []
    for k, (key, _) in enumerate(gals):
        idx = np.where((gid == k) & (p['kind'] > 0) & (p['kind'] < 9))[0]
        show.append(np.sort(rng.choice(idx, size=min(N_SHOW[key], len(idx)), replace=False)))
    meta = dict(galaxies=[k for k, _ in gals], traceurs=[t[0] for t in tr], cm0=cm.tolist(), vm0=vm.tolist(),
                affichees=[len(s) for s in show], quantum_kpc=Q, pas_ma=DT_MA, image_ma=KF_MA, vitesse_m31=ci['m31']['vel_name'])
    return p, gid, np.concatenate(show), meta


def forces(p):
    acc, phi = pyfalcon.gravity(p['pos'].astype(np.float32), (p['m'] * G).astype(np.float32), p['eps'].astype(np.float32), theta=0.6)
    return acc.astype(np.float64), phi.astype(np.float64)


def energie(p, phi):
    return 0.5 * float(np.sum(p['m'] * np.sum(p['vel'] ** 2, axis=1))) + 0.5 * float(np.sum(p['m'] * phi))


def centre(pos, m):
    """Centre par sphère qui rétrécit (Power et al. 2003), sur les étoiles d'une galaxie."""
    c = np.average(pos, axis=0, weights=m); r = np.percentile(np.linalg.norm(pos - c, axis=1), 90)
    while r > 0.5:
        sel = np.linalg.norm(pos - c, axis=1) < r
        if sel.sum() < 100: break
        c = np.average(pos[sel], axis=0, weights=m[sel]); r *= 0.85
    return c


def main():
    t_from, t_to = float(sys.argv[1]), float(sys.argv[2])
    n_total = int(sys.argv[3]) if len(sys.argv) > 3 else 300000
    os.makedirs(OUT, exist_ok=True)
    jpath, spath = os.path.join(OUT, 'fusion.json'), os.path.join(OUT, 'etat.npz')
    if t_from == 0:
        p, gid, show, meta = construire(n_total)
        meta.update(t=[], centres=[], traceurs_pos=[], energie=[], e0=None, fusion_ga=None, fichiers=[])
        t = 0.0
    else:
        z = np.load(spath); p = {k: z[k] for k in ('pos', 'vel', 'm', 'eps', 'kind')}; gid, show = z['gid'], z['show']; t = float(z['t'])
        meta = json.load(open(jpath, encoding='utf-8'))
        assert abs(t - t_from) < 1e-6, (t, t_from)
    stars = (p['kind'] > 0) & (p['kind'] < 9); trac = np.where(p['kind'] == 9)[0]
    acc, phi = forces(p)
    if meta['e0'] is None: meta['e0'] = energie(p, phi)
    frames, t0 = [], time.time()
    steps = int(round((t_to - t) * 1000 / DT_MA)); every = int(round(KF_MA / DT_MA))

    def image():
        cs = []
        for k in range(len(meta['galaxies'])):
            sel = np.where((gid == k) & stars)[0]; cs.append(centre(p['pos'][sel], p['m'][sel]).round(3).tolist())
        meta['t'].append(round(t, 4)); meta['centres'].append(cs); meta['traceurs_pos'].append(p['pos'][trac].round(3).tolist())
        e = energie(p, phi); meta['energie'].append(e / meta['e0'] - 1)
        d = math.dist(cs[0], cs[1])
        if meta['fusion_ga'] is None and d < 10 and t > 1: meta['fusion_ga'] = round(t, 3)
        if meta['fusion_ga'] is not None and d > 30: meta['fusion_ga'] = None      # séparés de nouveau : pas encore la fusion
        frames.append(np.clip(np.round(p['pos'][show] / Q), -32767, 32767).astype(np.int16))
        print(f'  t = {t:6.3f} Ga | séparation des centres {d:7.1f} kpc | dérive d’énergie {100 * meta["energie"][-1]:+.3f} % | {time.time() - t0:6.0f} s', flush=True)
        if len(frames) == KF_PER_FILE: vider()

    def vider():
        if not frames: return
        name = f'kf_{len(meta["fichiers"]):03d}.bin'
        np.concatenate(frames).tofile(os.path.join(OUT, name)); meta['fichiers'].append([name, len(frames)]); frames.clear()

    if t_from == 0: image()
    for s in range(steps):
        p['vel'] += 0.5 * DT * acc
        p['pos'] += DT * p['vel']
        acc, phi = forces(p)
        p['vel'] += 0.5 * DT * acc
        t = round(t + DT_MA * 1e-3, 6)
        if (s + 1) % every == 0: image()
    vider()
    meta['derive_max'] = max(abs(x) for x in meta['energie'])
    json.dump(meta, open(jpath, 'w', encoding='utf-8'), ensure_ascii=False)
    np.savez(spath, t=t, gid=gid, show=show, **p)
    print(json.dumps({k: meta[k] for k in ('fusion_ga', 'derive_max', 'affichees')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
