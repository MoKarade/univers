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
Usage : python calcul.py <de_Ga> <a_Ga> [N_total] [--gpu]
        python calcul.py depart <N_total>        (conditions de départ seules, écrit sortie/depart.npz)
        python calcul.py reprise <a_Ga> [--gpu]  (repart du dernier instantané)
--gpu : gravité sur la carte graphique (gravite_gpu.py) au lieu de falcON ; si sortie/depart.npz existe, il sert de départ.
--theta=0.5 : angle d'ouverture de l'arbre (0,7 par défaut ; 0,5 : erreur médiane de force 0,03 % au lieu de 0,1 %).
--sortie=<dossier> : dossier des sorties (par défaut pipeline/fusion/sortie).
--toutes : garde à chaque image TOUTES les étoiles (disque et bulbe, environ 1 million sur 3 millions de particules) au lieu de
           l'échantillon de 30 000 du départ ; environ 6 Mo par image. --echantillon=N avec --toutes : N étoiles tirées au hasard.
"""
import os, sys, json, time, math
import numpy as np
import energie_noire as EN      # énergie noire (w = -1), jamais négligée : energie_noire.py
import masse_liee as ML         # à quelle galaxie appartient chaque particule, image par image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'sortie')
G = 4.30091e-6                       # comme modeles.G (M☉, kpc, km/s)
T_UNIT = 0.9778                       # Ga par unité de temps kpc/(km/s)
DT_MA, KF_MA, KF_PER_FILE = 0.25, 20.0, 25
DT = DT_MA * 1e-3 / T_UNIT
Q = 0.025                             # kpc par unité des entiers 16 bits (± 819 kpc)
N_SHOW = {'mw': 12000, 'm31': 15000, 'm33': 2000, 'lmc': 1000}
EQ2GAL = np.array([[-0.0548755604, -0.8734370902, -0.4838350155],      # équatorial J2000 → galactique (Hipparcos, ESA 1997)
                   [0.4941094279, -0.4448296300, 0.7469822445],
                   [-0.8676661490, -0.1980763734, 0.4559837762]])


def construire_voie_lactee(n_disque):
    """Voie lactée seule, très résolue, pour que les bras et la barre naissent de sa propre gravité (option 1 de Marc,
    12/11/2026). Même modèle que dans le calcul de la fusion ; halo, disque et bulbe vivants dans le rapport 1 : 1 : 0,1 ;
    adoucissement réduit comme N^(-1/3) par rapport au calcul à 300 000 (Fujii et al. 2011 : au moins 1 M de particules
    dans le disque pour que les bras ne soient pas noyés dans le bruit)."""
    import modeles as M
    ci = json.load(open(os.path.join(HERE, 'conditions.json'), encoding='utf-8'))
    k_eps = (36000 / n_disque) ** (1 / 3)
    mw = M.galaxie('Voie lactée', n_disque, n_disque, n_disque // 10, k_eps=k_eps)
    p = M.placer(mw, [0, 0, -1], [0, 0, 0], [0, 0, 0])
    gid = np.zeros(len(p['m']), dtype=np.int8)
    tr = [('Soleil', ci['sun']['pos'], ci['sun']['vel'])]
    p['pos'] = np.concatenate([p['pos'], np.array([t[1] for t in tr], float)]); p['vel'] = np.concatenate([p['vel'], np.array([t[2] for t in tr], float)])
    p['m'] = np.concatenate([p['m'], np.full(len(tr), 1.0)]); p['eps'] = np.concatenate([p['eps'], np.full(len(tr), 0.1)])
    p['kind'] = np.concatenate([p['kind'], np.full(len(tr), 9, dtype=np.int8)]); gid = np.concatenate([gid, np.full(len(tr), -1, dtype=np.int8)])
    m = p['m'][:, None]; cm = (p['pos'] * m).sum(0) / m.sum(); vm = (p['vel'] * m).sum(0) / m.sum()
    p['pos'] -= cm; p['vel'] -= vm
    show = np.where((p['kind'] > 0) & (p['kind'] < 9))[0][:1]      # remplacé par --toutes
    meta = dict(galaxies=['mw', 'm31', 'm33', 'lmc'], traceurs=[t[0] for t in tr], cm0=cm.tolist(), vm0=vm.tolist(), affichees=[1, 0, 0, 0], quantum_kpc=Q, pas_ma=DT_MA,
                image_ma=KF_MA, vitesse_m31=None, modele='Voie lactée seule (bras et barre)', adoucissement_facteur=k_eps)
    return p, gid, show, meta


def construire(n_total):
    import modeles as M      # AGAMA : seulement pour tirer les conditions de départ
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


def centre(pos, m):
    """Centre par sphère qui rétrécit (Power et al. 2003), sur les étoiles d'une galaxie."""
    c = np.average(pos, axis=0, weights=m); r = np.percentile(np.linalg.norm(pos - c, axis=1), 90)
    while r > 0.5:
        sel = np.linalg.norm(pos - c, axis=1) < r
        if sel.sum() < 100: break
        c = np.average(pos[sel], axis=0, weights=m[sel]); r *= 0.85
    return c


class Processeur:
    """Gravité par falcON (pyfalcon), sur le processeur : le calcul d'origine (R9)."""
    nom = 'falcON (processeur), theta 0,6'

    def __init__(self, p):
        import pyfalcon
        self.f = pyfalcon; self.p = p

    def forces(self):
        p = self.p
        acc, phi = self.f.gravity(p['pos'].astype(np.float32), (p['m'] * G).astype(np.float32), p['eps'].astype(np.float32), theta=0.6)
        if not ENERGIE_NOIRE: return acc.astype(np.float64), phi.astype(np.float64)
        # potentiel extérieur compté deux fois dans phi : l'énergie l'additionne avec un facteur ½ (energie)
        return acc.astype(np.float64) + EN.acceleration(p['pos']), phi.astype(np.float64) + 2 * EN.potentiel(p['pos'])

    def energie(self, phi):
        p = self.p
        return 0.5 * float(np.sum(p['m'] * np.sum(p['vel'] ** 2, axis=1))) + 0.5 * float(np.sum(p['m'] * phi))

    def pos(self): return self.p['pos']
    def vel(self): return self.p['vel']
    def etat(self): return self.p
    def attendre(self): pass


class Carte:
    """Gravité par arbre sur la carte graphique (gravite_gpu.py, jalon A1). Positions et vitesses restent sur la carte."""
    nom = 'arbre de Barnes-Hut avec quadripôles (carte graphique), theta 0,7'
    THETA = 0.7

    def __init__(self, p):
        import cupy as cp, gravite_gpu
        self.cp, self.gg, self.np_p = cp, gravite_gpu, p
        self.p = {k: cp.asarray(p[k], dtype=cp.float64) for k in ('pos', 'vel', 'm', 'eps')}
        self.mg = self.p['m'] * G
        self.t_check = time.time()

    def forces(self):
        acc, phi = self.gg.gravity(self.p['pos'], self.mg, self.p['eps'], theta=self.THETA, quad=True)
        if not ENERGIE_NOIRE: return acc, phi
        return acc + EN.acceleration(self.p['pos']), phi + 2 * EN.potentiel(self.p['pos'], xp=self.cp)

    def energie(self, phi):
        cp, p = self.cp, self.p
        return 0.5 * float(cp.sum(p['m'] * cp.sum(p['vel'] ** 2, axis=1))) + 0.5 * float(cp.sum(p['m'] * phi))

    def pos(self): return self.cp.asnumpy(self.p['pos'])
    def vel(self): return self.cp.asnumpy(self.p['vel'])

    def etat(self):
        out = dict(self.np_p); out['pos'] = self.cp.asnumpy(self.p['pos']); out['vel'] = self.cp.asnumpy(self.p['vel'])
        return out

    def attendre(self):
        """Laisse la carte à Marc : toutes les 30 s, on s'arrête une seconde ; si la carte reste occupée par un
        autre programme (un jeu), on attend qu'elle se libère. Aucune fenêtre n'est ouverte."""
        if time.time() - self.t_check < 30: return
        import subprocess
        self.cp.cuda.Stream.null.synchronize()
        while True:
            time.sleep(1.0)
            try:
                u = int(subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                                       capture_output=True, text=True, timeout=20, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.split()[0])
            except Exception as e:      # mesure impossible : on le dit et on continue
                print(f'  (occupation de la carte illisible : {e})', flush=True); break
            if u < SEUIL_OCCUPATION: break
            print(f'  carte graphique occupée à {u} % par un autre programme : pause de 60 s', flush=True)
            time.sleep(60)
        self.t_check = time.time()


ENERGIE_NOIRE = True      # --sans-energie-noire : pour comparer seulement
SEUIL_OCCUPATION = 35      # % d'occupation de la carte, mesurée pendant notre pause, au-delà duquel on attend


def main():
    global OUT
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    gpu = '--gpu' in sys.argv
    for a in sys.argv[1:]:
        if a.startswith('--theta='): Carte.THETA = float(a.split('=', 1)[1])
        if a.startswith('--sortie='): OUT = a.split('=', 1)[1]
    global ENERGIE_NOIRE
    ENERGIE_NOIRE = '--sans-energie-noire' not in sys.argv
    os.makedirs(OUT, exist_ok=True)
    jpath, spath, dpath = os.path.join(OUT, 'fusion.json'), os.path.join(OUT, 'etat.npz'), os.path.join(OUT, 'depart.npz')
    if args[0] in ('depart', 'depart_vl'):      # conditions de départ seules (AGAMA) : python calcul.py depart <N> | depart_vl <N disque>
        p, gid, show, meta = construire(int(args[1])) if args[0] == 'depart' else construire_voie_lactee(int(args[1]))
        np.savez_compressed(dpath, gid=gid, show=show, meta=json.dumps(meta, ensure_ascii=False), **p)
        print('départ écrit :', len(p['m']), 'particules'); return
    reprise = args[0] == 'reprise'
    membre_repris = None      # python calcul.py reprise <a_Ga> : repart du dernier instantané
    t_to = float(args[1])
    if not reprise and float(args[0]) <= 0:      # départ : aujourd'hui (0) ou dans le passé (depart_passe.py, meta['debut_ga'])
        if os.path.exists(dpath):
            with np.load(dpath) as z:
                p = {k: z[k] for k in ('pos', 'vel', 'm', 'eps', 'kind')}; gid, show = z['gid'], z['show']; meta = json.loads(str(z['meta']))
        else:
            p, gid, show, meta = construire(int(args[2]) if len(args) > 2 else 300000)
        if '--toutes' in sys.argv:      # toutes les étoiles, dans l'ordre des galaxies (le tirage du départ est remplacé)
            etoiles = (p['kind'] > 0) & (p['kind'] < 9)
            par = [np.where((gid == k) & etoiles)[0] for k in range(len(meta['galaxies']))]
            for a in sys.argv:      # --echantillon=N : N étoiles tirées au hasard (graine fixe), au prorata de chaque galaxie
                if a.startswith('--echantillon='):
                    n_tot, tous = int(a.split('=', 1)[1]), sum(len(x) for x in par)
                    rng = np.random.default_rng(20261112)
                    par = [np.sort(rng.choice(x, size=min(len(x), round(n_tot * len(x) / tous)), replace=False)) if len(x) else x for x in par]
            show = np.concatenate(par)
            meta['affichees'] = [int(len(x)) for x in par]
            meta['composantes'] = 'kind de chaque étoile affichée : composantes.bin (int8, 1 disque, 2 bulbe)'
            p['kind'][show].astype(np.int8).tofile(os.path.join(OUT, 'composantes.bin'))
        meta.update(t=[], centres=[], traceurs_pos=[], energie=[], e0=None, fusion_ga=None, fichiers=[])
        t = float(meta.get('debut_ga', 0.0)); debut = True
        assert abs(t - float(args[0])) < 1e-6, ('le départ est à', t, 'Ga, pas', args[0])
    else:
        with np.load(spath) as z:      # fermé tout de suite : sous Windows, un fichier ouvert ne peut pas être remplacé
            p = {k: z[k] for k in ('pos', 'vel', 'm', 'eps', 'kind')}; gid, show = z['gid'], z['show']; t = float(z['t'])
            membre_repris = z['membre'] if 'membre' in z else None
        meta = json.load(open(jpath, encoding='utf-8')); debut = False
        if not reprise: assert abs(t - float(args[0])) < 1e-6, (t, args[0])
    S = Carte(p) if gpu else Processeur(p)
    meta['energie_noire'] = f'constante cosmologique, H0 {EN.H0_KMS_MPC} km/s/Mpc, Omega_Lambda {EN.OMEGA_LAMBDA}' if ENERGIE_NOIRE else 'absente (comparaison)'
    meta['gravite'] = S.nom if not gpu else f'arbre de Barnes-Hut avec quadripôles (carte graphique), theta {Carte.THETA}'; meta['particules'] = int((p['kind'] < 9).sum())
    stars = (p['kind'] > 0) & (p['kind'] < 9); trac = np.where(p['kind'] == 9)[0]
    star_idx = [np.where((gid == k) & stars)[0] for k in range(len(meta['galaxies']))]
    acc, phi = S.forces()
    if meta['e0'] is None: meta['e0'] = S.energie(phi)
    frames, t0 = [], time.time()
    # Appartenance de chaque particule (masse_liee.py) : au départ, sa galaxie d'origine ; les traceurs n'en ont pas.
    massive = p['kind'] < 9
    membre = gid[massive].astype(np.int8).copy()
    if not debut and membre_repris is not None: membre = membre_repris
    meta.setdefault('masse_liee', []); meta.setdefault('masse_libre', [])
    meta['masse_liee_colonnes'] = 'par image et par galaxie : masse liée (M☉, matière noire comprise), étoiles liées, masse venue d’autres galaxies'
    steps = int(round((t_to - t) * 1000 / DT_MA)); every = int(round(KF_MA / DT_MA))

    def image():
        pos = S.pos(); cs = []
        for sel in star_idx: cs.append(centre(pos[sel], p['m'][sel]).round(3).tolist() if len(sel) else [0.0, 0.0, 0.0])      # galaxie absente : 0
        meta['t'].append(round(t, 4)); meta['centres'].append(cs); meta['traceurs_pos'].append(pos[trac].round(3).tolist())
        e = S.energie(phi); meta['energie'].append(e / meta['e0'] - 1)
        nonlocal membre
        mp = p['m'][massive]; et = (p['kind'][massive] > 0)
        membre = ML.appartenance(pos[massive], S.vel()[massive], mp, et, membre, cs)
        b, libre = ML.bilan(mp, et, gid[massive], membre, len(cs))
        meta['masse_liee'].append([[float('%.5g' % x) for x in g] for g in b]); meta['masse_libre'].append(float('%.5g' % libre))
        d = math.dist(cs[0], cs[1]) if len(star_idx[1]) else 0.0      # Voie lactée seule : pas de séparation
        if len(star_idx[1]) and meta['fusion_ga'] is None and d < 10 and t > 1: meta['fusion_ga'] = round(t, 3)
        if meta['fusion_ga'] is not None and d > 30: meta['fusion_ga'] = None      # séparés de nouveau : pas encore la fusion
        frames.append(np.clip(np.round(pos[show] / Q), -32767, 32767).astype(np.int16))
        print(f'  t = {t:6.3f} Ga | séparation des centres {d:7.1f} kpc | dérive d’énergie {100 * meta["energie"][-1]:+.3f} % | {time.time() - t0:6.0f} s', flush=True)
        if len(frames) == KF_PER_FILE: vider()

    def vider():
        """Écrit les images en attente, puis un instantané complet : un arrêt brutal ne perd que le morceau en cours."""
        if frames:
            name = f'kf_{len(meta["fichiers"]):03d}.bin'
            np.concatenate(frames).tofile(os.path.join(OUT, name)); meta['fichiers'].append([name, len(frames)]); frames.clear()
        meta['derive_max'] = max(abs(x) for x in meta['energie'])
        np.savez(spath + '.tmp.npz', t=t, gid=gid, show=show, membre=membre, **S.etat()); os.replace(spath + '.tmp.npz', spath)
        json.dump(meta, open(jpath + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False); os.replace(jpath + '.tmp', jpath)

    if debut: image()
    P = S.p
    for s in range(steps):
        P['vel'] += 0.5 * DT * acc
        P['pos'] += DT * P['vel']
        acc, phi = S.forces()
        P['vel'] += 0.5 * DT * acc
        t = round(t + DT_MA * 1e-3, 6)
        if (s + 1) % every == 0: image()
        S.attendre()
    vider()
    print(json.dumps({k: meta[k] for k in ('fusion_ga', 'derive_max', 'affichees', 'gravite', 'particules')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
