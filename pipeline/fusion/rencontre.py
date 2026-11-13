#!/usr/bin/env python3
"""Le calcul unique du Groupe local (plan B+) : Voie lactée, Andromède, Triangle, Grand et Petit Nuage en particules qui
s'attirent toutes, avec l'énergie noire, parti du PASSÉ et réglé pour passer par les mesures d'aujourd'hui.

Entrées :
- les galaxies seules à l'équilibre tirées par modeles_v2.py (<dossier>/<galaxie>.npz), déjà contrôlées par stabilite_tir.py ;
- la table unique (pipeline/constantes/univers.json) : axes de rotation, constante de l'énergie noire, masse du Petit Nuage ;
- la cible (pipeline/fusion/resultats/cible_aujourdhui.json) : où chaque galaxie doit être AUJOURD'HUI, et un premier
  point de départ à −3 Ga (orbites de centres indéformables : un point de départ, pas une vérité) ;
- plus tard, les étoiles visibles (docs/contrat-etoiles-visibles.md), ajoutées à t = 0 comme traceurs sans masse.

Trois usages :
  python rencontre.py tir   <dossier galaxies> <sortie> [--fraction=0.2] [--etat=etat.json]
      Part de −3 Ga (état donné, ou celui de la cible), va jusqu'à aujourd'hui, mesure l'écart de chaque galaxie à sa
      place mesurée, et écrit <sortie>/etat_corrige.json : le départ corrigé pour le tir suivant.
  python rencontre.py passe <dossier galaxies> <sortie> --etat=etat.json
      Le même trajet à pleine résolution ; écrit l'instantané d'aujourd'hui (<sortie>/aujourdhui.npz).
  python rencontre.py futur <sortie> <jusqu'à, Ga> [--traceurs=<dossier des étoiles visibles>]
      Repart de l'instantané d'aujourd'hui, ajoute les étoiles visibles, écrit le film (film_v2.py).

Repère du calcul : centre de masse au repos. Les sorties sont rendues RELATIVES AU CENTRE DE LA VOIE LACTÉE, dans le
repère phys::galaxie de l'appli. Unités : kpc, km/s, M☉ ; temps en Ga, 0 = aujourd'hui.
"""
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'constantes'))
import constantes as C      # noqa: E402

G = 4.30091e-6
T_UNIT = 0.9778      # Ga par unité de temps kpc/(km/s)
ORDRE = ['voie_lactee', 'andromede', 'triangle', 'grand_nuage', 'petit_nuage']
ETOILES = (1, 2, 4)      # composantes qui servent à trouver le centre d'une galaxie (disques et bulbe)


def rotation_vers(axe):
    """Matrice qui envoie +z sur l'axe donné."""
    a = np.asarray(axe, float); a /= np.linalg.norm(a)
    z = np.array([0.0, 0.0, 1.0]); v = np.cross(z, a); c = float(z @ a)
    if np.linalg.norm(v) < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))


def plummer(masse, a, n, rng):
    """Sphère de Plummer à l'équilibre (Aarseth, Hénon et Wielen 1974) : pour le Petit Nuage, qui n'a pas de modèle mesuré."""
    r = a / np.sqrt(rng.random(n) ** (-2 / 3) - 1)
    def direction(k):
        u = rng.normal(size=(k, 3)); return u / np.linalg.norm(u, axis=1)[:, None]
    q = np.empty(n); todo = np.arange(n)
    while len(todo):
        x = rng.random(len(todo)); y = rng.random(len(todo)) * 0.1
        ok = y < x * x * (1 - x * x) ** 3.5
        q[todo[ok]] = x[ok]; todo = todo[~ok]
    v = q * np.sqrt(2 * G * masse / np.sqrt(r * r + a * a))
    return r[:, None] * direction(n), v[:, None] * direction(n)


def assembler(dossier, etat, fraction=1.0, graine=20261113):
    """Pose chaque galaxie à sa place de départ. etat : {galaxie: {pos, vel}} relatifs à la Voie lactée."""
    rng = np.random.default_rng(graine)
    parts = {k: [] for k in ('pos', 'vel', 'm', 'eps', 'kind', 'gid')}
    for g, nom in enumerate(ORDRE):
        e = etat[nom]
        chemin = os.path.join(dossier, nom + '.npz')
        if os.path.exists(chemin):
            with np.load(chemin) as z:
                p = {k: z[k] for k in ('pos', 'vel', 'm', 'eps', 'kind')}
            n = len(p['m'])
            if fraction < 1.0:      # basse résolution pour les tirs de réglage : une particule sur 1/fraction, masse d'autant plus grande
                s = np.sort(rng.choice(n, size=int(n * fraction), replace=False))
                p = {k: v[s] for k, v in p.items()}
                p['m'] = p['m'] / fraction; p['eps'] = p['eps'] * fraction ** (-1 / 3)
            R = rotation_vers(C.galaxie(nom)['disque']['axe_rotation'])
            pos, vel = p['pos'] @ R.T, p['vel'] @ R.T
            m, eps, kind = p['m'], p['eps'], p['kind']
        else:      # Petit Nuage : masse adoptée de la table, sphère de Plummer de 1,5 kpc [modèle]
            masse = C.galaxie(nom)['loi_masse']['centre']
            n = max(2000, int(60000 * fraction))
            pos, vel = plummer(masse, 1.5, n, rng)
            m, eps, kind = np.full(n, masse / n), np.full(n, 0.2 * fraction ** (-1 / 3)), np.full(n, 1, dtype=np.int8)
        parts['pos'].append(pos + np.asarray(e['pos'], float)); parts['vel'].append(vel + np.asarray(e['vel'], float))
        parts['m'].append(m); parts['eps'].append(eps); parts['kind'].append(kind.astype(np.int8)); parts['gid'].append(np.full(len(m), g, dtype=np.int8))
    p = {k: np.concatenate(v) for k, v in parts.items()}
    w = p['m'][:, None]; cm = (p['pos'] * w).sum(0) / w.sum(); vm = (p['vel'] * w).sum(0) / w.sum()
    p['pos'] -= cm; p['vel'] -= vm
    return p


class Calcul:
    """Saute-mouton sur la carte graphique : gravité de toutes les particules (gravite_gpu) + énergie noire."""

    def __init__(self, p, theta=0.7):
        import cupy as cp
        import gravite_gpu
        self.cp, self.gg, self.theta = cp, gravite_gpu, theta
        self.pos = cp.asarray(p['pos'], dtype=cp.float64); self.vel = cp.asarray(p['vel'], dtype=cp.float64)
        self.m = cp.asarray(p['m'], dtype=cp.float64); self.eps = cp.asarray(p['eps'], dtype=cp.float64)
        self.kind, self.gid = p['kind'], p['gid']
        self.mg = self.m * G
        self.K = C.K_lambda()
        self.lourd = cp.asarray(p['kind'] != 9)      # les traceurs (9) ne comptent pas dans le centre de masse
        self.idx = [cp.asarray(np.where((p['gid'] == g) & np.isin(p['kind'], ETOILES))[0]) for g in range(len(ORDRE))]
        self.t_check = time.time()
        self.forces()

    def forces(self):
        cp = self.cp
        acc, phi = self.gg.gravity(self.pos, self.mg, self.eps, theta=self.theta, quad=True)
        ml = self.m * self.lourd
        cm = cp.sum(self.pos * ml[:, None], axis=0) / cp.sum(ml)
        d = self.pos - cm
        self.acc = acc + self.K * d      # énergie noire : poussée H0² Ω_Λ (x − x_cm)
        self.phi, self.d2 = phi, cp.sum(d * d, axis=1)

    def energie(self):
        cp = self.cp
        return float(0.5 * cp.sum(self.m * cp.sum(self.vel ** 2, axis=1)) + 0.5 * cp.sum(self.m * self.phi) - 0.5 * self.K * cp.sum(self.m * self.d2))

    def pas(self, dt):
        self.vel += 0.5 * dt * self.acc
        self.pos += dt * self.vel
        self.forces()
        self.vel += 0.5 * dt * self.acc

    def centres(self):
        """Centre (sphère qui rétrécit, Power et al. 2003) et vitesse d'ensemble de chaque galaxie, sur ses étoiles."""
        cp = self.cp; out_p, out_v = [], []
        for ix in self.idx:
            p = self.pos[ix]; w = self.m[ix]
            c = cp.sum(p * w[:, None], axis=0) / cp.sum(w)
            r = float(cp.percentile(cp.linalg.norm(p - c, axis=1), 90))
            while r > 0.5:
                sel = cp.linalg.norm(p - c, axis=1) < r
                if int(sel.sum()) < 100: break
                c = cp.sum(p[sel] * w[sel][:, None], axis=0) / cp.sum(w[sel]); r *= 0.85
            sel = cp.linalg.norm(p - c, axis=1) < max(r, 2.0)
            v = cp.sum(self.vel[ix][sel] * w[sel][:, None], axis=0) / cp.sum(w[sel])
            out_p.append(cp.asnumpy(c)); out_v.append(cp.asnumpy(v))
        return np.array(out_p), np.array(out_v)

    def attendre(self):
        """Rend la carte à Marc : si un autre programme l'occupe (son appli, un jeu), on attend."""
        if time.time() - self.t_check < 30: return
        self.cp.cuda.Stream.null.synchronize()
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
        self.t_check = time.time()

    def etat(self):
        cp = self.cp
        return dict(pos=cp.asnumpy(self.pos), vel=cp.asnumpy(self.vel), m=cp.asnumpy(self.m), eps=cp.asnumpy(self.eps), kind=self.kind, gid=self.gid)


def avancer(S, t0, t1, sortie, dt_ma=0.25, releve_ma=20.0, instantane_ga=0.5, journal=None, a_chaque_releve=None):
    """Avance de t0 à t1 (Ga). Écrit journal.json (centres relatifs à la Voie lactée, énergie) et des instantanés."""
    dt = dt_ma * 1e-3 / T_UNIT
    steps = int(round((t1 - t0) * 1000 / dt_ma)); every = int(round(releve_ma / dt_ma)); snap = int(round(instantane_ga * 1000 / dt_ma))
    journal = journal or dict(t=[], centres=[], vitesses=[], energie=[], e0=S.energie(), galaxies=ORDRE)
    debut = time.time()

    def releve(t):
        cp_, cv = S.centres()
        journal['t'].append(round(t, 5)); journal['centres'].append((cp_ - cp_[0]).round(4).tolist()); journal['vitesses'].append((cv - cv[0]).round(3).tolist())
        journal['energie'].append(S.energie() / journal['e0'] - 1)
        d = np.linalg.norm(cp_ - cp_[0], axis=1)
        print(f"t = {t:+7.3f} Ga | distances au centre de la Voie lactée (kpc) : " + ' '.join(f'{x:6.1f}' for x in d[1:]) + f" | énergie {100 * journal['energie'][-1]:+.3f} % | {time.time() - debut:6.0f} s", flush=True)
        json.dump(journal, open(os.path.join(sortie, 'journal.json.tmp'), 'w', encoding='utf-8')); os.replace(os.path.join(sortie, 'journal.json.tmp'), os.path.join(sortie, 'journal.json'))
        if a_chaque_releve: a_chaque_releve(t, cp_, cv)

    if not journal['t']: releve(t0)
    for s in range(steps):
        S.pas(dt)
        t = t0 + (s + 1) * dt_ma * 1e-3
        if (s + 1) % every == 0: releve(t)
        if (s + 1) % snap == 0 and s + 1 < steps:
            np.savez(os.path.join(sortie, 'reprise.tmp.npz'), t=t, **S.etat()); os.replace(os.path.join(sortie, 'reprise.tmp.npz'), os.path.join(sortie, 'reprise.npz'))
        S.attendre()
    return journal


def ecart_a_la_cible(journal, cible):
    """Écart de chaque galaxie, au dernier relevé, à sa place et sa vitesse mesurées (relatives à la Voie lactée)."""
    out = {}
    for g, nom in enumerate(ORDRE[1:], start=1):
        c = cible['galaxies'][nom]
        dx = np.array(journal['centres'][-1][g]) - np.array(c['position_aujourdhui'])
        dv = np.array(journal['vitesses'][-1][g]) - np.array(c['vitesse_aujourdhui'])
        out[nom] = dict(dx=dx.round(2).tolist(), dv=dv.round(2).tolist(), distance_kpc=round(float(np.linalg.norm(dx)), 2), vitesse_kms=round(float(np.linalg.norm(dv)), 2))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    mode = args[0]
    cible = json.load(open(os.path.join(ICI, 'resultats', 'cible_aujourdhui.json'), encoding='utf-8'))
    t_depart = float(cible['debut_reference_ga'])
    if mode in ('tir', 'passe'):
        dossier, sortie = args[1], args[2]
        os.makedirs(sortie, exist_ok=True)
        if 'etat' in opts:
            etat = json.load(open(opts['etat'], encoding='utf-8'))['etat']
        else:
            etat = {n: dict(pos=cible['galaxies'][n]['position_reference_moins_passe'], vel=cible['galaxies'][n]['vitesse_reference_moins_passe']) for n in ORDRE}
        p = assembler(dossier, etat, fraction=float(opts.get('fraction', 0.2 if mode == 'tir' else 1.0)))
        print(f"{mode} : {len(p['m'])} particules, de {t_depart:+.2f} Ga à aujourd'hui", flush=True)
        S = Calcul(p, theta=float(opts.get('theta', 0.7)))
        journal = avancer(S, t_depart, 0.0, sortie, releve_ma=float(opts.get('releve-ma', 50.0)))
        ecart = ecart_a_la_cible(journal, cible)
        # Correction du départ : l'écart final de vitesse est retiré de la vitesse de départ ; l'écart final de position est
        # retiré de la position de départ, compte tenu de ce que le changement de vitesse déplace sur la durée du trajet
        # (mouvement libre : une approximation, d'où les tirs successifs). Amorti pour ne pas osciller.
        amorti, T = float(opts.get('amorti', 0.8)), -t_depart / T_UNIT
        corrige = {}
        for n in ORDRE:
            e = dict(pos=list(map(float, etat[n]['pos'])), vel=list(map(float, etat[n]['vel'])))
            if n in ecart:
                dx, dv = np.array(ecart[n]['dx']), np.array(ecart[n]['dv'])
                e['vel'] = (np.array(e['vel']) - amorti * dv).tolist()
                e['pos'] = (np.array(e['pos']) - amorti * (dx - dv * T)).tolist()
            corrige[n] = e
        json.dump(dict(t_depart=t_depart, etat=corrige, ecart_du_tir=ecart, particules=int(len(p['m']))), open(os.path.join(sortie, 'etat_corrige.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        json.dump(dict(t_depart=t_depart, etat=etat), open(os.path.join(sortie, 'etat_utilise.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('écart à la place mesurée aujourd\'hui :')
        for n, e in ecart.items(): print(f"  {n:12s} {e['distance_kpc']:7.1f} kpc   {e['vitesse_kms']:6.1f} km/s")
        if mode == 'passe':
            np.savez(os.path.join(sortie, 'aujourdhui.npz'), t=0.0, **S.etat())
            print('instantané d\'aujourd\'hui écrit')
    elif mode == 'futur':
        futur(args[1], float(args[2]), opts, cible)
    else:
        raise SystemExit('mode inconnu : ' + mode)


def futur(sortie, t_fin, opts, cible):
    """D'aujourd'hui à t_fin, avec les étoiles visibles comme traceurs sans masse ; écrit le film (version 2).

    Film (dossier <sortie>/film) : film.json (dates des images, centre et vitesse de chaque galaxie relatifs à la Voie
    lactée, énergie, nombre de traceurs par galaxie, décalage appliqué à t = 0) et une image par date, img_NNNNN.f16 :
    pour chaque traceur, dans l'ordre des fichiers fournis (galaxie après galaxie), sa position RELATIVE AU CENTRE DE SA
    GALAXIE D'ORIGINE, trois nombres à virgule sur 16 bits, en kpc (précision relative 5e-4 : 4 pc à 8 kpc)."""
    reprise = os.path.join(sortie, 'film', 'reprise.npz')
    film = os.path.join(sortie, 'film'); os.makedirs(film, exist_ok=True)
    releve_ma = float(opts.get('releve-ma', 10.0))
    if os.path.exists(reprise) and os.path.exists(os.path.join(film, 'film.json')):      # reprise après un arrêt
        with np.load(reprise) as z:
            p = {k: z[k] for k in ('pos', 'vel', 'm', 'eps', 'kind', 'gid')}; t0 = float(z['t'])
        meta = json.load(open(os.path.join(film, 'film.json'), encoding='utf-8'))
        journal = json.load(open(os.path.join(film, 'journal.json'), encoding='utf-8'))
        k = min(len(journal['t']), len(meta['t']))      # on repart du dernier instantané : les images d'après sont refaites
        while k and journal['t'][k - 1] > t0 + 1e-9: k -= 1
        for cle in ('t', 'centres', 'vitesses', 'energie'): journal[cle] = journal[cle][:k]
        meta['t'] = meta['t'][:k]
    else:
        with np.load(os.path.join(sortie, 'aujourdhui.npz')) as z:
            p = {k: z[k] for k in ('pos', 'vel', 'm', 'eps', 'kind', 'gid')}
        t0, journal = 0.0, None
        S0 = Calcul(p, theta=float(opts.get('theta', 0.7)))
        cp_, cv = S0.centres(); del S0
        meta = dict(version=2, unites="kpc, Ga ; positions relatives au centre de la galaxie d'origine, float16", galaxies=ORDRE, t=[], traceurs=[0] * len(ORDRE),
                    pas_image_ma=releve_ma, decalage_a_t0={})
        if 'traceurs' in opts:      # étoiles visibles (docs/contrat-etoiles-visibles.md), posées sur le centre que le calcul donne à leur galaxie
            ajout = {k: [] for k in ('pos', 'vel', 'm', 'eps', 'kind', 'gid')}
            for g, nom in enumerate(ORDRE):
                f = os.path.join(opts['traceurs'], f'etoiles_visibles_{nom}.npz')
                if not os.path.exists(f): continue
                with np.load(f) as z: tp, tv = z['pos'].astype(np.float64), z['vel'].astype(np.float64)
                mesure_p = np.array(cible['galaxies'][nom]['position_aujourdhui']); mesure_v = np.array(cible['galaxies'][nom]['vitesse_aujourdhui'])
                # du repère de l'appli (Voie lactée à l'origine, au repos) au repère du calcul ; l'écart entre la place mesurée
                # de la galaxie et celle que le calcul lui donne à t = 0 est retiré, pour que les étoiles restent sur leur masse.
                ajout['pos'].append(tp - mesure_p + cp_[g]); ajout['vel'].append(tv - mesure_v + cv[g])
                n = len(tp)
                ajout['m'].append(np.full(n, 1.0)); ajout['eps'].append(np.full(n, 0.05)); ajout['kind'].append(np.full(n, 9, dtype=np.int8)); ajout['gid'].append(np.full(n, g, dtype=np.int8))
                meta['traceurs'][g] = n
                meta['decalage_a_t0'][nom] = dict(position=((cp_[g] - cp_[0]) - mesure_p).round(3).tolist(), vitesse=((cv[g] - cv[0]) - mesure_v).round(3).tolist())
            p = {k: np.concatenate([p[k]] + ajout[k]) for k in p}
    S = Calcul(p, theta=float(opts.get('theta', 0.7)))
    cp = S.cp
    tr = [cp.asarray(np.where((p['kind'] == 9) & (p['gid'] == g))[0]) for g in range(len(ORDRE))]
    print(f"futur : {int((p['kind'] != 9).sum())} particules de masse, {int((p['kind'] == 9).sum())} étoiles visibles, de {t0:+.3f} à {t_fin:+.2f} Ga", flush=True)

    def image(t, centres, vitesses):
        blocs = [cp.asnumpy(S.pos[ix] - cp.asarray(centres[g])).astype(np.float16) for g, ix in enumerate(tr) if len(ix)]
        nom = f"img_{len(meta['t']):05d}.f16"
        if blocs:
            np.concatenate(blocs).tofile(os.path.join(film, nom + '.tmp')); os.replace(os.path.join(film, nom + '.tmp'), os.path.join(film, nom))
        meta['t'].append(round(t, 5))
        json.dump(meta, open(os.path.join(film, 'film.json.tmp'), 'w', encoding='utf-8'), ensure_ascii=False); os.replace(os.path.join(film, 'film.json.tmp'), os.path.join(film, 'film.json'))

    avancer(S, t0, t_fin, film, releve_ma=releve_ma, journal=journal, a_chaque_releve=image)
    print('film terminé :', len(meta['t']), 'images')


if __name__ == '__main__':
    main()
