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


def assembler(dossier, etat, fraction=1.0, graine=20261113, angles=None):
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
            axe = (C.galaxie(nom).get('disque') or {}).get('axe_rotation') or [0.0, 0.0, 1.0]      # Petit Nuage : sens de rotation non mesuré
            R = rotation_vers(axe)
            a = math.radians((angles or {}).get(nom, 0.0))      # tour autour de son propre axe : cale la barre de la masse sur la barre mesurée (mode « barre »)
            Z = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
            R = R @ Z
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

    def __init__(self, p, theta=0.7, gaz=False, maree=None, t_ga=0.0):
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
        # Marée extérieure au Groupe local (Vierge, grands voisins) : tenseur 3 x 3 par date au centre de masse de la paire,
        # tiré d'un départ cosmologique contraint (fil « départ contraint », tables_raccord/maree.csv : T_ij = -d²Phi_ext/dx_i dx_j,
        # a_i = T_ij x_j, (km/s/kpc)², repère de l'appli, énergie noire non comprise). Même ordre de grandeur que l'énergie
        # noire (2e-3 contre 3,1e-3). [Modèle : la paire de ce départ contraint s'écarte du ciel réel ; dispersion 20-25 % au
        # moins.] Hors des dates de la table, la valeur du bord est gardée.
        self.maree = None; self.t_ga = t_ga
        if maree:
            T = np.loadtxt(maree, delimiter=',', skiprows=1)
            self.maree = (T[:, 0], T[:, 1:10])
        # Gaz (gaz_galaxie.py) : les particules de sorte 3 sentent la pression, les chocs, et deviennent des étoiles (sorte 5).
        # Le gaz de toutes les galaxies est calculé ensemble ; il avance par sous-pas pendant le pas long de la gravité.
        self.gaz = None; self.kind_g = cp.asarray(p['kind'])
        if gaz and int((p['kind'] == 3).sum()) >= 100:
            import gaz_galaxie
            self.gaz = (gaz_galaxie.GazThermique if gaz == 2 else gaz_galaxie.Gaz)(len(p['kind']))
            if 'u_gaz' in p and hasattr(self.gaz, 'u'): self.gaz.u = cp.asarray(p['u_gaz'], dtype=cp.float64)
            if 'h_gaz' in p: self.gaz.h = cp.asarray(p['h_gaz'], dtype=cp.float64)
            if 'naissance' in p: self.gaz.naissance = np.array(p['naissance'], dtype=np.float64)
            self.gaz.ages_de_depart(p['kind'])
            if 'age0' in p: self.gaz.age0 = cp.asarray(p['age0'], dtype=cp.float64)
        self.forces()

    def forces(self):
        cp = self.cp
        acc, phi = self.gg.gravity(self.pos, self.mg, self.eps, theta=self.theta, quad=True)
        ml = self.m * self.lourd
        cm = cp.sum(self.pos * ml[:, None], axis=0) / cp.sum(ml)
        d = self.pos - cm
        self.acc = acc + self.K * d      # énergie noire : poussée H0² Ω_Λ (x − x_cm)
        if self.maree is not None:
            tt, TT = self.maree
            Tm = cp.asarray(np.array([np.interp(self.t_ga, tt, TT[:, k]) for k in range(9)]).reshape(3, 3))
            self.acc += d @ Tm.T
        self.phi, self.d2 = phi, cp.sum(d * d, axis=1)

    def energie(self):
        cp = self.cp
        return float(0.5 * cp.sum(self.m * cp.sum(self.vel ** 2, axis=1)) + 0.5 * cp.sum(self.m * self.phi) - 0.5 * self.K * cp.sum(self.m * self.d2))

    def pas(self, dt, t_ga=0.0):
        cp = self.cp
        self.t_ga = t_ga
        self.vel += 0.5 * dt * self.acc
        if self.gaz:
            est = self.kind_g == 3; qui = cp.where(est)[0]
            self.pos[~est] += dt * self.vel[~est]
            self.gaz.avancer(self.pos, self.vel, self.m, qui, dt)
        else:
            self.pos += dt * self.vel
        self.forces()
        self.vel += 0.5 * dt * self.acc
        if self.gaz:
            n1 = self.gaz.naissances(self.kind_g, cp.where(self.kind_g == 3)[0], dt, t_ga, pos=self.pos, m=self.m)
            n2 = self.gaz.retour(self.kind_g, dt, t_ga)
            if n1 or n2: self.kind = cp.asnumpy(self.kind_g)

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
        """Rend la carte à Marc : s'il joue ou ouvre son appli (carte.py), on attend, ou on se retire tout à fait."""
        if time.time() - self.t_check < 30: return
        import carte
        while True:
            raison = carte.prise(self.cp.get_default_memory_pool().total_bytes() / 2 ** 20)
            if not raison: break
            if os.environ.get('UNIVERS_CEDER') == '1':
                # Marc joue ou ouvre son appli : on rend TOUTE la carte (mémoire comprise) en s'arrêtant. Le veilleur
                # (veilleur_calcul.ps1) relance le calcul depuis la dernière sauvegarde quand la carte est de nouveau libre.
                print(f'  {raison} : le calcul se retire, reprise à la dernière sauvegarde', flush=True)
                sys.exit(3)
            print(f'  {raison} : pause de 60 s', flush=True)
            time.sleep(60)
        self.t_check = time.time()

    def etat(self):
        cp = self.cp
        e = dict(pos=cp.asnumpy(self.pos), vel=cp.asnumpy(self.vel), m=cp.asnumpy(self.m), eps=cp.asnumpy(self.eps), kind=cp.asnumpy(self.kind_g), gid=self.gid)
        if self.gaz: e.update(h_gaz=cp.asnumpy(self.gaz.h).astype(np.float32), naissance=self.gaz.naissance, age0=cp.asnumpy(self.gaz.age0).astype(np.float32))
        if self.gaz is not None and hasattr(self.gaz, 'u'): e['u_gaz'] = cp.asnumpy(self.gaz.u).astype(np.float32)
        return e


def avancement(t0, t1, t):
    """Barre d'avancement lue par l'appli (dossier donné par UNIVERS_AVANCEMENT, format clé=valeur de pipeline/natif/avancement.py)."""
    d = os.environ.get('UNIVERS_AVANCEMENT')
    if not d: return
    try:
        fini = t >= t1 - 1e-9
        lignes = ['nom=Groupe local : cinq galaxies, du passé à la fusion', f'fait={t - t0:.3f}', f'total={t1 - t0:.3f}', 'unite=milliards d’années',
                  'debut=' + DEBUT, 'maj=' + time.strftime('%Y-%m-%dT%H:%M:%S'), 'etat=' + ('terminé' if fini else 'en cours'),
                  'detail=Toutes les particules s’attirent, énergie noire comprise ; date atteinte : ' + f'{t:+.2f} milliards d’années']
        nl = chr(10)
        with open(os.path.join(d, 'groupe_local.txt.tmp'), 'w', encoding='utf-8', newline=nl) as f: f.write(nl.join(lignes) + nl)
        os.replace(os.path.join(d, 'groupe_local.txt.tmp'), os.path.join(d, 'groupe_local.txt'))
    except OSError:
        pass


DEBUT = time.strftime('%Y-%m-%dT%H:%M:%S')


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
        if S.gaz:      # masse de gaz et d'étoiles nées, par galaxie d'origine (M☉) : le taux de naissance s'en déduit
            k_, mm = S.cp.asnumpy(S.kind_g), S.cp.asnumpy(S.m)
            journal.setdefault('gaz', []).append([float(mm[(k_ == 3) & (S.gid == g)].sum()) for g in range(len(ORDRE))])
            journal.setdefault('nees', []).append([float(mm[(k_ == 5) & (S.gid == g)].sum()) for g in range(len(ORDRE))])
            journal.setdefault('sous_pas', []).append(int(S.gaz.sous_pas))
        d = np.linalg.norm(cp_ - cp_[0], axis=1)
        print(f"t = {t:+7.3f} Ga | distances au centre de la Voie lactée (kpc) : " + ' '.join(f'{x:6.1f}' for x in d[1:]) + f" | énergie {100 * journal['energie'][-1]:+.3f} % | {time.time() - debut:6.0f} s", flush=True)
        json.dump(journal, open(os.path.join(sortie, 'journal.json.tmp'), 'w', encoding='utf-8')); os.replace(os.path.join(sortie, 'journal.json.tmp'), os.path.join(sortie, 'journal.json'))
        if a_chaque_releve: a_chaque_releve(t, cp_, cv)
        avancement(t0, t1, t)

    if not journal['t']: releve(t0)
    for s in range(steps):
        S.pas(dt, t0 + (s + 1) * dt_ma * 1e-3)
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


def profils(dossier):
    """Masse enfermée de chaque galaxie en fonction du rayon, lue dans ses particules : pour le modèle simple des centres."""
    out = []
    for nom in ORDRE:
        with np.load(os.path.join(dossier, nom + '.npz')) as z:
            r = np.linalg.norm(z['pos'], axis=1); m = z['m']
        o = np.argsort(r); pas = max(1, len(r) // 3000)
        out.append((r[o][::pas], np.cumsum(m[o])[::pas]))
    return out


def centres_simples(etat, T, prof):
    """Modèle SIMPLE des cinq centres : chaque galaxie est un point attiré par la masse que les autres enferment à sa
    distance (profils des vraies particules), sans frottement ni marée. Il ne sert qu'à deux choses : deviner le départ
    en remontant depuis les mesures d'aujourd'hui, et orienter les corrections (matrice de sensibilité). L'écart, lui,
    vient toujours du vrai calcul. etat : {galaxie: {pos, vel}} relatifs à la Voie lactée ; T en kpc/(km/s), négatif pour
    remonter le temps. Rend l'état d'arrivée, relatif à la Voie lactée."""
    x = np.array([etat[n]['pos'] for n in ORDRE], float); v = np.array([etat[n]['vel'] for n in ORDRE], float)
    n = max(200, int(abs(T) / 0.001)); h = T / n

    def acc(x):
        a = np.zeros_like(x)
        for i in range(len(ORDRE)):
            for j in range(len(ORDRE)):
                if i == j: continue
                d = x[i] - x[j]; r = max(np.linalg.norm(d), 2.0)
                a[i] -= G * np.interp(r, prof[j][0], prof[j][1]) * d / r ** 3
        return a
    a = acc(x)
    for _ in range(n):
        v += 0.5 * h * a; x += h * v; a = acc(x); v += 0.5 * h * a
    return {nom: dict(pos=(x[g] - x[0]).tolist(), vel=(v[g] - v[0]).tolist()) for g, nom in enumerate(ORDRE)}


def sensibilite(etat, g, T, prof):
    """Matrice 6 x 6 : comment l'état d'arrivée de la galaxie g change avec son état de départ, dans le modèle simple."""
    nom = ORDRE[g]
    def arrivee(e):
        f = centres_simples(e, T, prof)[nom]; return np.concatenate([f['pos'], f['vel']])
    base = arrivee(etat); J = np.zeros((6, 6))
    for k in range(6):
        e = json.loads(json.dumps(etat)); pas = 1.0 if k < 3 else 0.5      # 1 kpc ou 0,5 km/s
        (e[nom]['pos'] if k < 3 else e[nom]['vel'])[k % 3] += pas
        J[:, k] = (arrivee(e) - base) / pas
    return J


def corriger(etat, ecart, t_depart, prof, amorti=0.5):
    """Départ corrigé pour le tir suivant (Newton amorti). Le changement de départ est celui qui annulerait l'écart
    d'arrivée dans le modèle simple ; il est borné : pas plus de 1,5 fois l'écart lui-même en position et en vitesse.
    (Sans borne, la matrice mal conditionnée des Nuages a fait diverger les tirs 12 à 16 du 13/11.)"""
    T = -t_depart / T_UNIT
    corrige = {}
    for g, n in enumerate(ORDRE):
        e = dict(pos=list(map(float, etat[n]['pos'])), vel=list(map(float, etat[n]['vel'])))
        if n in ecart:
            dx, dv = np.array(ecart[n]['dx'], float), np.array(ecart[n]['dv'], float)
            J = sensibilite(etat, g, T, prof)
            d = np.linalg.lstsq(J, -np.concatenate([dx, dv]), rcond=1e-3)[0] * amorti
            f = min(1.0, 1.5 * np.linalg.norm(dx) / max(np.linalg.norm(d[:3]), 1e-9), 1.5 * np.linalg.norm(dv) / max(np.linalg.norm(d[3:]), 1e-9))
            e['pos'] = (np.array(e['pos']) + f * d[:3]).tolist(); e['vel'] = (np.array(e['vel']) + f * d[3:]).tolist()
        corrige[n] = e
    return corrige


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    mode = args[0]
    cible = json.load(open(os.path.join(ICI, 'resultats', 'cible_aujourdhui.json'), encoding='utf-8'))
    t_depart = float(cible['debut_reference_ga'])
    ref = None
    if 'depart' in opts: t_depart = float(opts['depart'])
    if mode == 'corrige':      # refait la correction d'un tir déjà fait : python rencontre.py corrige <dossier galaxies> <dossier du tir>
        u = json.load(open(os.path.join(args[2], 'etat_utilise.json'), encoding='utf-8')); c0 = json.load(open(os.path.join(args[2], 'etat_corrige.json'), encoding='utf-8'))
        c0['etat'] = corriger(u['etat'], c0['ecart_du_tir'], float(u['t_depart']), profils(args[1]), float(opts.get('amorti', 0.5)))
        json.dump(c0, open(os.path.join(args[2], 'etat_corrige.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('correction refaite'); return
    if mode in ('tir', 'passe'):
        dossier, sortie = args[1], args[2]
        os.makedirs(sortie, exist_ok=True)
        if 'etat' in opts:
            precedent = json.load(open(opts['etat'], encoding='utf-8'))
            etat, t_depart = precedent['etat'], float(precedent['t_depart'])
        else:
            # Premier départ : on remonte depuis les places et vitesses mesurées aujourd'hui, dans le modèle simple des centres
            # bâti sur les masses de CE calcul. (Les orbites de la référence, avec leur frottement de formule, ne valent pas
            # pour les Nuages dans ce calcul : tirs 1 à 3 du 13/11, 120 à 250 kpc d'écart.)
            auj = {n: dict(pos=cible['galaxies'][n]['position_aujourdhui'], vel=cible['galaxies'][n]['vitesse_aujourdhui']) for n in ORDRE}
            etat = centres_simples(auj, t_depart / T_UNIT, profils(dossier))
        angles = {a.split(':')[0]: float(a.split(':')[1]) for a in opts['angles'].split(',')} if 'angles' in opts else None
        p = assembler(dossier, etat, fraction=float(opts.get('fraction', 0.2 if mode == 'tir' else 1.0)), angles=angles)
        print(f"{mode} : {len(p['m'])} particules, de {t_depart:+.2f} Ga à aujourd'hui", flush=True)
        S = Calcul(p, theta=float(opts.get('theta', 0.7)), gaz=int(opts.get('gaz', 0)), maree=opts.get('maree'), t_ga=t_depart)
        journal = avancer(S, t_depart, 0.0, sortie, releve_ma=float(opts.get('releve-ma', 50.0)))
        ecart = ecart_a_la_cible(journal, cible)
        # Correction du départ : l'écart final de vitesse est retiré de la vitesse de départ ; l'écart final de position est
        # retiré de la position de départ, compte tenu de ce que le changement de vitesse déplace sur la durée du trajet
        # (mouvement libre : une approximation, d'où les tirs successifs). Amorti pour ne pas osciller.
        corrige = corriger(etat, ecart, t_depart, profils(dossier), float(opts.get('amorti', 0.5)))
        json.dump(dict(t_depart=t_depart, etat=corrige, ecart_du_tir=ecart, particules=int(len(p['m']))), open(os.path.join(sortie, 'etat_corrige.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        json.dump(dict(t_depart=t_depart, etat=etat), open(os.path.join(sortie, 'etat_utilise.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('écart à la place mesurée aujourd\'hui :')
        for n, e in ecart.items(): print(f"  {n:12s} {e['distance_kpc']:7.1f} kpc   {e['vitesse_kms']:6.1f} km/s")
        if mode == 'passe':
            np.savez(os.path.join(sortie, 'aujourdhui.npz'), t=0.0, **S.etat())
            print('instantané d\'aujourd\'hui écrit')
    elif mode == 'barre':
        barre(args[1], opts, cible)
    elif mode == 'futur':
        futur(args[1], float(args[2]), opts, cible)
    else:
        raise SystemExit('mode inconnu : ' + mode)


# Composante des étoiles visibles (docs/contrat-etoiles-visibles.md) -> sortes de particules de masse qui la portent.
PORTEUSES = {1: (1,), 2: (1, 2), 4: (4, 1), 5: (3, 1)}
JEUNES_AGITATION = (5.0, 2.0)


def repere_disque(nom, pos, centre):
    """Positions dans le repère du disque de la galaxie (axe de rotation = +z), centre à l'origine."""
    axe = (C.galaxie(nom).get('disque') or {}).get('axe_rotation') or [0.0, 0.0, 1.0]
    return (pos - centre) @ rotation_vers(axe)


def vitesses_de_la_masse(nom, tp, tv, comp, p, g, centre, voisins=8, graine=20261116, sauf=()):
    """Donne à chaque étoile visible la vitesse d'une particule de masse voisine de la même famille (une des `voisins`
    plus proches, au hasard : l'agitation locale est ainsi celle de la masse). Les étoiles visibles sont posées d'après
    les mesures, mais leurs vitesses du contrat viennent de formules qui ne sont pas à l'équilibre dans la masse du
    calcul (docs/premier-film.md, défaut 3 : sursaut des 50 premiers Ma). Le halo d'étoiles (6) garde ses vitesses.
    La hauteur compte triple dans la distance, pour prendre une voisine de même hauteur.
    Étoiles jeunes (5) : il n'y a pas de gaz froid dans le calcul, et les particules qui en tiennent lieu sont agitées ;
    leur donner cette agitation les éparpillait en 30 Ma (mesuré le 16/11 : épaisseur 49 -> 270 pc, rayon médian + 1 kpc).
    Elles prennent donc la vitesse MOYENNE des 1 024 particules voisines dans le plan (le courant local, barre comprise),
    plus une petite agitation (JEUNES_AGITATION, km/s : dans le plan, en hauteur) [modèle]."""
    from scipy.spatial import cKDTree
    rng = np.random.default_rng(graine + g)
    tv = tv.copy(); pris = {}
    echelle = np.array([1.0, 1.0, 3.0])
    td = repere_disque(nom, tp, centre) * echelle
    for c, sortes in PORTEUSES.items():
        qui = np.where(comp == c)[0]
        if not len(qui) or c in sauf: continue      # sauf : étoiles déjà posées sur la masse, position et vitesse
        if c == 5:
            masse = np.where((p['gid'] == g) & ((p['kind'] == 1) | (p['kind'] == 3)))[0]
            if len(masse) >= 320:
                md = repere_disque(nom, p['pos'][masse], centre)
                arbre = cKDTree(md[:, :2])
                axe = (C.galaxie(nom).get('disque') or {}).get('axe_rotation') or [0.0, 0.0, 1.0]
                R = rotation_vers(axe)
                # courant moyen dans le repère du disque, sans sa part en hauteur (la moyenne de voisines agitées en garde
                # plusieurs km/s de bruit, ce qui suffisait à épaissir les jeunes : 49 -> 220 pc en 100 Ma, mesuré)
                vm = np.zeros((len(qui), 3)); vmasse = (p['vel'][masse] - p['vel'][masse].mean(0)) @ R
                for a0 in range(0, len(qui), 100000):      # 1 024 voisines : la moyenne garde ~1 km/s de bruit, y compris en hauteur (le disque ondule)
                    _, v = arbre.query(td[qui[a0:a0 + 100000], :2], k=1024, workers=-1)
                    vm[a0:a0 + 100000] = vmasse[v].mean(axis=1)
                # Les étoiles agitées tournent moins vite que la vitesse circulaire (ici 196 au lieu de ~235 km/s au Soleil) ;
                # des jeunes lancées à cette vitesse tomberaient vers le centre. Leur vitesse de rotation est donc remise à
                # l'échelle de la vitesse circulaire de la masse du calcul, rayon par rayon ; l'écart au cercle (courant de
                # la barre) est gardé.
                tous = np.where(p['gid'] == g)[0]
                rc, vc = vitesse_circulaire(repere_disque(nom, p['pos'][tous], centre), p['m'][tous])
                Rm = np.hypot(md[:, 0], md[:, 1]); vphi_m = (md[:, 0] * vmasse[:, 1] - md[:, 1] * vmasse[:, 0]) / np.maximum(Rm, 1e-6)
                k_ = np.clip(np.searchsorted(rc, Rm) , 1, len(rc) - 1)
                moy = np.array([vphi_m[k_ == i].mean() if (k_ == i).sum() > 50 else np.nan for i in range(len(rc))])
                signe = np.sign(np.nanmedian(moy))
                facteur = np.where(np.isfinite(moy) & (np.abs(moy) > 20.0), signe * vc / moy, 1.0)
                Rj = np.hypot(td[qui, 0], td[qui, 1]); fj = np.interp(Rj, rc, facteur)
                # dans la barre (moins de 6 kpc) il n'y a pas d'orbite circulaire : le courant moyen est gardé tel quel ;
                # la remise à l'échelle entre progressivement de 6 à 9 kpc (run du 16/11 : appliquée partout, elle éjectait
                # les jeunes du centre, rayon médian 5,9 -> 8,1 kpc en 50 Ma)
                u_ = np.clip((Rj - 6.0) / 3.0, 0.0, 1.0); fj = 1.0 + (fj - 1.0) * u_ * u_ * (3 - 2 * u_)
                er = td[qui, :2] / np.maximum(Rj, 1e-6)[:, None]; ep = np.stack([-er[:, 1], er[:, 0]], 1)
                vr = (vm[:, :2] * er).sum(1); vp = (vm[:, :2] * ep).sum(1) * fj
                vm[:, :2] = er * vr[:, None] + ep * vp[:, None]
                bruit = rng.normal(0.0, 1.0, (len(qui), 3)) * np.array([JEUNES_AGITATION[0], JEUNES_AGITATION[0], JEUNES_AGITATION[1]])
                tv[qui] = (vm + bruit) @ R.T + p['vel'][masse].mean(0)
                pris[str(c)] = int(len(qui))
                continue
        for sorte in sortes:
            masse = np.where((p['gid'] == g) & (p['kind'] == sorte))[0]
            if len(masse) >= 10 * voisins: break
        else:
            masse = np.where((p['gid'] == g) & (p['kind'] != 0) & (p['kind'] != 9))[0]
        arbre = cKDTree(repere_disque(nom, p['pos'][masse], centre) * echelle)
        _, v = arbre.query(td[qui], k=voisins, workers=-1)
        choix = v[np.arange(len(qui)), rng.integers(0, voisins, len(qui))]
        tv[qui] = p['vel'][masse[choix]]
        pris[str(c)] = int(len(qui))
    return tv, pris


def vitesse_circulaire(pos, m, rmax=20.0, pas=0.5, azimuts=8, eps=0.1):
    """Vitesse circulaire (km/s) de la masse d'une galaxie dans son plan, par somme directe de l'attraction de toutes
    ses particules sur des points d'essai (moyenne sur `azimuts` directions). pos : repère du disque (kpc), m : M☉."""
    rc = np.arange(pas, rmax + 1e-9, pas); vc = np.zeros(len(rc))
    pos = pos.astype(np.float32); mg = (m * G).astype(np.float32)
    for i, r in enumerate(rc):
        ar = 0.0
        for a in np.arange(azimuts) * 2 * math.pi / azimuts:
            x = np.array([r * math.cos(a), r * math.sin(a), 0.0], np.float32)
            d = pos - x; d3 = ((d * d).sum(1) + np.float32(eps * eps)) ** np.float32(1.5)
            ar += float(((mg / d3) * (d[:, 0] * x[0] + d[:, 1] * x[1])).sum()) / r      # composante radiale (vers l'extérieur)
        vc[i] = math.sqrt(max(-ar / azimuts * r, 0.0))
    return rc, vc


def phase_barre(x, y, r0=1.0, r1=4.0):
    """Force et angle (degrés, modulo 180) du motif à deux bras entre r0 et r1 kpc."""
    r = np.hypot(x, y); m = (r > r0) & (r < r1)
    c = np.mean(np.exp(2j * np.arctan2(y[m], x[m])))
    return float(abs(c)), float(np.degrees(np.angle(c)) / 2)


def barre(sortie, opts, cible):
    """Compare, à t = 0, la barre de la masse (aujourdhui.npz) à celle des étoiles visibles, galaxie par galaxie, et
    écrit l'angle dont il faut tourner la galaxie de départ autour de son axe (--angles du mode « passe »)."""
    with np.load(os.path.join(sortie, 'aujourdhui.npz')) as z:
        p = {k: z[k] for k in ('pos', 'vel', 'm', 'eps', 'kind', 'gid', 'h_gaz', 'naissance', 'age0', 'u_gaz') if k in z.files}
    S0 = Calcul(p); cp_, _ = S0.centres(); del S0
    res = {}
    for g, nom in enumerate(ORDRE):
        f = os.path.join(opts['traceurs'], f'etoiles_visibles_{nom}.npz')
        if nom not in ('voie_lactee', 'andromede') or not os.path.exists(f): continue
        with np.load(f) as z: tp = z['pos'].astype(np.float64)
        td = repere_disque(nom, tp, np.array(cible['galaxies'][nom]['position_aujourdhui']))
        md = repere_disque(nom, p['pos'][(p['gid'] == g) & (p['kind'] != 0)], cp_[g])
        r1 = 4.0 if nom == 'voie_lactee' else 5.0
        fm, am = phase_barre(md[:, 0], md[:, 1], 1.0, r1); ft, at = phase_barre(td[:, 0], td[:, 1], 1.0, r1)
        d = (at - am + 90.0) % 180.0 - 90.0
        res[nom] = dict(masse=dict(force=round(fm, 3), angle=round(am, 1)), etoiles=dict(force=round(ft, 3), angle=round(at, 1)), tourner_de=round(d, 1))
        print(f"{nom:12s} barre de la masse {fm:.3f} à {am:+6.1f}° ; des étoiles visibles {ft:.3f} à {at:+6.1f}° ; tourner le départ de {d:+.1f}°")
    json.dump(res, open(os.path.join(sortie, 'barre.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


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
            p = {k: z[k] for k in ('pos', 'vel', 'm', 'eps', 'kind', 'gid', 'h_gaz', 'naissance', 'age0', 'u_gaz') if k in z.files}; t0 = float(z['t'])
        meta = json.load(open(os.path.join(film, 'film.json'), encoding='utf-8'))
        journal = json.load(open(os.path.join(film, 'journal.json'), encoding='utf-8'))
        k = min(len(journal['t']), len(meta['t']))      # on repart du dernier instantané : les images d'après sont refaites
        while k and journal['t'][k - 1] > t0 + 1e-9: k -= 1
        for cle in ('t', 'centres', 'vitesses', 'energie', 'gaz', 'nees', 'sous_pas'):
            if cle in journal: journal[cle] = journal[cle][:k]
        meta['t'] = meta['t'][:k]
    else:
        with np.load(os.path.join(sortie, 'aujourdhui.npz')) as z:
            p = {k: z[k] for k in ('pos', 'vel', 'm', 'eps', 'kind', 'gid', 'h_gaz', 'naissance', 'age0', 'u_gaz') if k in z.files}
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
                tp = tp - mesure_p + cp_[g]; tv = tv - mesure_v + cv[g]
                if opts.get('vitesses', 'masse') == 'masse':      # vitesses prises à la masse qui porte les étoiles (pas de sursaut au départ)
                    with np.load(f) as z:
                        comp = z['comp']
                        deja = json.loads(str(z['meta'])).get('posees_sur_la_masse', []) if 'meta' in z else []      # etoiles_visibles_masse.py
                    tv, pris = vitesses_de_la_masse(nom, tp, tv, comp, p, g, cp_[g], sauf=deja)
                    meta.setdefault('vitesses_de_la_masse', {})[nom] = pris
                ajout['pos'].append(tp); ajout['vel'].append(tv)
                n = len(tp)
                # « sans masse » : 1e-6 M☉ et non 0 (un nœud de l'arbre fait de traceurs seuls diviserait par 0) ; 8,5 M de traceurs pèsent 8,5 M☉ en tout (revue du 18/11, N4)
                ajout['m'].append(np.full(n, 1e-6)); ajout['eps'].append(np.full(n, 0.05)); ajout['kind'].append(np.full(n, 9, dtype=np.int8)); ajout['gid'].append(np.full(n, g, dtype=np.int8))
                meta['traceurs'][g] = n
                meta['decalage_a_t0'][nom] = dict(position=((cp_[g] - cp_[0]) - mesure_p).round(3).tolist(), vitesse=((cv[g] - cv[0]) - mesure_v).round(3).tolist())
            nt = sum(len(x) for x in ajout['m'])
            if 'h_gaz' in p: ajout['h_gaz'] = [np.full(nt, 0.2, np.float32)]      # champs du gaz : sans objet pour les étoiles visibles
            if 'naissance' in p: ajout['naissance'] = [np.full(nt, np.nan)]
            if 'age0' in p: ajout['age0'] = [np.full(nt, np.nan, np.float32)]
            if 'u_gaz' in p: ajout['u_gaz'] = [np.zeros(nt, np.float32)]
            p = {k: np.concatenate([p[k]] + ajout[k]) for k in p}
    S = Calcul(p, theta=float(opts.get('theta', 0.7)), gaz=int(opts.get('gaz', 0)), maree=opts.get('maree'))
    cp = S.cp
    tr = [cp.asarray(np.where((p['kind'] == 9) & (p['gid'] == g))[0]) for g in range(len(ORDRE))]
    print(f"futur : {int((p['kind'] != 9).sum())} particules de masse, {int((p['kind'] == 9).sum())} étoiles visibles, de {t0:+.3f} à {t_fin:+.2f} Ga", flush=True)

    champ = None
    if 'champ' in opts:      # champ de gravité en coefficients (pipeline/champ/champ_bfe.py, docs/champ-coefficients.md), toutes les --champ images
        sys.path.insert(0, os.path.join(ICI, '..', 'champ'))
        import champ_bfe as champ
        os.makedirs(os.path.join(film, 'champ'), exist_ok=True)
    masse_de = [cp.asarray(np.where((p['kind'] != 9) & (p['gid'] == g))[0]) for g in range(len(ORDRE))]
    etoile_de = S.idx

    def ecrire_champ(k, centres, vitesses):
        m_gal = [float(cp.sum(S.m[ix])) for ix in masse_de]
        for g, nom in enumerate(ORDRE):
            ix = masse_de[g]
            pos = cp.asnumpy(S.pos[ix]) - centres[g]
            e = etoile_de[g]      # axe : moment cinétique des étoiles de la galaxie, à cette image
            L = cp.asnumpy(cp.sum(cp.cross(S.pos[e] - cp.asarray(centres[g]), S.vel[e] - cp.asarray(vitesses[g])) * S.m[e][:, None], axis=0))
            axe = (L / np.linalg.norm(L)).tolist() if np.linalg.norm(L) > 0 else None
            rmax = None
            if g >= 3:      # les Nuages : au-delà de leur rayon de marée dans la Voie lactée, leur champ propre n'a plus de sens
                rmax = champ.rayon_jacobi(float(np.linalg.norm(centres[g] - centres[0])), m_gal[g], m_gal[0])
            Cf = champ.coefficients(pos, cp.asnumpy(S.m[ix]), p['kind'][cp.asnumpy(ix)], axe=axe, rayon_max=rmax)
            champ.sauver(Cf, os.path.join(film, 'champ', f'champ_{k:05d}_{nom}.npz'))

    def image(t, centres, vitesses):
        if champ is not None and len(meta['t']) % int(opts['champ']) == 0:
            try:
                ecrire_champ(len(meta['t']), centres, vitesses)
            except Exception as err:      # le champ ne doit jamais arrêter le calcul : on le dit et on continue
                print(f'  champ non écrit à t = {t:+.3f} Ga : {err}', flush=True)
        blocs = [cp.asnumpy(S.pos[ix] - cp.asarray(centres[g])).astype(np.float16) for g, ix in enumerate(tr) if len(ix)]
        nom = f"img_{len(meta['t']):05d}.f16"
        if blocs:
            np.concatenate(blocs).tofile(os.path.join(film, nom + '.tmp')); os.replace(os.path.join(film, nom + '.tmp'), os.path.join(film, nom))
        meta['t'].append(round(t, 5))
        json.dump(meta, open(os.path.join(film, 'film.json.tmp'), 'w', encoding='utf-8'), ensure_ascii=False); os.replace(os.path.join(film, 'film.json.tmp'), os.path.join(film, 'film.json'))

    def image_et_index(t, centres, vitesses):
        image(t, centres, vitesses)
        try:      # index binaire pour l'appli, refait à chaque image (quelques dizaines de ko) ; ne doit jamais arrêter le calcul
            import film_v2
            film_v2.ecrire_index(film)
        except Exception as err:
            print(f'  index du film non écrit : {err}', flush=True)

    # Sauvegarde toutes les 5 images (50 Ma, environ 7 minutes de carte) : un arrêt ne perd jamais plus que cela.
    avancer(S, t0, t_fin, film, releve_ma=releve_ma, instantane_ga=0.05, journal=journal, a_chaque_releve=image_et_index)
    print('film terminé :', len(meta['t']), 'images')


if __name__ == '__main__':
    main()
