#!/usr/bin/env python3
"""Étoiles visibles d'Andromède, du Triangle et des Nuages posées SUR LA MASSE du calcul (pendant de
etoiles_visibles_masse.py, qui fait la Voie lactée).

Entrées : les fichiers du contrat des quatre voisines (etoiles_visibles_<galaxie>.npz, par exemple ceux à bras
reconstruits du fil « vraie forme spirale »), l'instantané d'aujourd'hui du calcul (aujourdhui.npz de rencontre.py) et le
dossier des galaxies de départ (pour savoir, par son rang, à quelle composante appartient chaque particule).

Pour chaque galaxie :
- 1 disque vieux, 2 bulbe et barre, 4 disque épais : position et vitesse REMPLACÉES par celles d'une particule de la masse
  de la même composante (reconnue à son rang dans la galaxie de départ, jamais à sa place d'aujourd'hui), décalée d'une
  fraction de la distance à ses voisines. Mesuré sur le film 2 : sans cela l'épaisseur d'Andromède triple en 30 Ma.
- 5 étoiles jeunes, bras reconstruits : place gardée dans le plan du disque ; hauteur comptée depuis le milieu local du disque
  de la masse ; rencontre.py leur donne ensuite la vitesse du courant moyen local.
- autres composantes : inchangées.
Lumières, couleurs, graines, composantes : inchangées. Repère de sortie : celui de l'appli (galaxie à sa place mesurée).

Usage : python etoiles_visibles_voisines_masse.py <dossier des contrats> <aujourdhui.npz> <dossier des galaxies de départ> <dossier de sortie>
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')
import json, math, os, sys, time
import numpy as np
from scipy.spatial import cKDTree

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'constantes'))
import constantes as C

ORDRE = ['voie_lactee', 'andromede', 'triangle', 'grand_nuage', 'petit_nuage']
GRAINE = 20261119
DECALAGE = 0.5


def rotation_vers(axe):
    """Matrice qui envoie +z sur l'axe donné (la même que pipeline/fusion/rencontre.py)."""
    a = np.asarray(axe, float); a /= np.linalg.norm(a)
    z = np.array([0.0, 0.0, 1.0]); v = np.cross(z, a); c = float(z @ a)
    if np.linalg.norm(v) < 1e-12: return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))


def centre_des_etoiles(pos, vel):
    c = np.median(pos, 0)
    for r in (10.0, 5.0, 2.0, 1.0):
        d = np.linalg.norm(pos - c, axis=1)
        if (d < r).sum() > 100: c = pos[d < r].mean(0)
    d = np.linalg.norm(pos - c, axis=1)
    return c, vel[d < max(1.0, np.percentile(d, 10))].mean(0)


def blocs(meta, n):
    """Rang de début et de fin de chaque composante de la galaxie de départ, dans l'ordre du fichier."""
    out, a = [], 0
    for c in meta['composantes']:
        out.append((c['nom'], a, a + int(c['particules']))); a += int(c['particules'])
    if a != n: raise SystemExit(f'ECHEC : {a} particules annoncées, {n} dans le calcul (galaxie de départ différente ?)')
    return out


def tirer(rng, pd, vd, n):
    """n étoiles tirées des particules (repère du disque), décalées dans le plan de DECALAGE x la distance à la 4e voisine."""
    d4 = cKDTree(pd).query(pd, k=5, workers=-1)[0][:, 4]
    k = rng.choice(len(pd), size=n, replace=True)
    return pd[k] + rng.normal(0.0, 1.0, (n, 3)) * (DECALAGE * d4[k])[:, None] * np.array([1.0, 1.0, 0.3]), vd[k]


def main():
    contrats, auj, depart, sortie = sys.argv[1:5]
    t0 = time.time()
    cible = json.load(open(os.path.join(ICI, '..', 'fusion', 'resultats', 'cible_aujourdhui.json'), encoding='utf-8'))
    with np.load(auj) as z: P = {k: z[k] for k in ('pos', 'vel', 'kind', 'gid')}
    os.makedirs(sortie, exist_ok=True)
    for g, nom in enumerate(ORDRE):
        if g == 0: continue
        f = os.path.join(contrats, f'etoiles_visibles_{nom}.npz')
        if not os.path.exists(f): print(nom, ': pas de contrat, sauté'); continue
        rng = np.random.default_rng(GRAINE + g)
        with np.load(f) as z: E = {k: z[k] for k in z.files}
        pos, vel, comp = E['pos'].astype(np.float64), E['vel'].astype(np.float64), E['comp']
        meta = json.loads(str(E['meta'])) if 'meta' in E else {}
        s = np.where((P['gid'] == g) & (P['kind'] != 9))[0]
        mp, mv, mk = P['pos'][s].astype(np.float64), P['vel'][s].astype(np.float64), P['kind'][s]
        fd = os.path.join(depart, nom + '.npz')
        with np.load(fd) as z: md = json.loads(str(z['meta']))
        B = blocs(md, len(s))
        et = (mk == 1) | (mk == 2) | (mk == 4)
        c, cv = centre_des_etoiles(mp[et], mv[et])
        axe = (C.galaxie(nom).get('disque') or {}).get('axe_rotation') or [0.0, 0.0, 1.0]
        Rm = rotation_vers(axe)
        pd, vd = (mp - c) @ Rm, (mv - cv) @ Rm      # repère du disque
        mes_p = np.array(cible['galaxies'][nom]['position_aujourdhui']); mes_v = np.array(cible['galaxies'][nom]['vitesse_aujourdhui'])
        # composantes de la masse, par rang : premier disque d'étoiles = disque vieux ; les disques d'étoiles suivants (compacts) et
        # le bulbe = bulbe et barre ; disque épais
        disques = [(a, b) for n_, a, b in B if n_ == 'disque mince']
        rang = np.arange(len(s)); etoile = (mk == 1) | (mk == 2) | (mk == 4)      # encore étoile aujourd'hui (pas rendue au gaz)
        dans = lambda ab: (rang >= ab[0]) & (rang < ab[1]) & etoile
        vieux = dans(disques[0]) if disques else etoile
        barre = np.zeros(len(s), bool)
        for ab in disques[1:]: barre |= dans(ab)
        for n_, a, b in B:
            if n_ == 'bulbe': barre |= dans((a, b))
        epais = np.zeros(len(s), bool)
        for n_, a, b in B:
            if n_ == 'disque épais': epais |= dans((a, b))
        if barre.sum() < 1000: barre = vieux
        if epais.sum() < 1000: epais = vieux
        ed = (pos - mes_p) @ Rm      # étoiles du contrat dans le repère du disque
        fait = {}
        for cc, masque in ((1, vieux), (2, barre), (4, epais)):
            q = np.where(comp == cc)[0]
            if not len(q): continue
            p_, v_ = tirer(rng, pd[masque], vd[masque], len(q))
            pos[q] = p_ @ Rm.T + mes_p; vel[q] = v_ @ Rm.T + mes_v
            fait[str(cc)] = int(len(q))
        j = np.where(comp == 5)[0]
        if len(j):
            froid = vieux | (mk == 3)
            arbre = cKDTree(pd[froid, :2]); zf = pd[froid, 2]
            k = min(1024, int(froid.sum()))
            for a in range(0, len(j), 100000):
                _, v_ = arbre.query(ed[j[a:a + 100000], :2], k=k, workers=-1)
                ed[j[a:a + 100000], 2] += np.median(zf[v_], axis=1)
            pos[j] = ed[j] @ Rm.T + mes_p
            fait['5'] = int(len(j))
        meta['posees_sur_la_masse'] = [1, 2, 4]; meta['jeunes_sur_le_milieu_du_disque'] = True
        meta['masse'] = os.path.abspath(auj); meta['date_pose'] = '2026-11-19'
        E['pos'], E['vel'], E['meta'] = pos, vel, np.array(json.dumps(meta, ensure_ascii=False))
        np.savez_compressed(os.path.join(sortie, f'etoiles_visibles_{nom}.npz'), **E)
        print(f'{nom} : {fait} étoiles posées ; particules de la masse : disque {int(vieux.sum())}, barre et bulbe {int(barre.sum())}, épais {int(epais.sum())} ({time.time() - t0:.0f} s)')


if __name__ == '__main__':
    main()
