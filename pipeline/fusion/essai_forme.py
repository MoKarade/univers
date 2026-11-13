#!/usr/bin/env python3
"""Essai de FORME (étape 0 du plan B+, docs/refonte-simulations-pro.md § 6.2) : la forme de chaque galaxie doit changer
de façon continue d'une image du film à la suivante, et rien ne doit apparaître ni disparaître.

L'essai de continuité de l'appli (natif/src/essai_continuite.cpp) suit les astres nommés ; il ne voit pas les points des
galaxies. Celui-ci suit, pour chaque galaxie et à chaque image :
- le nombre de points et leur poids total (masse ou lumière) : ils doivent rester EXACTEMENT les mêmes (règle de Marc :
  la masse est conservée, aucune bascule) ;
- la forme : rapports d'axes b/a et c/a (tenseur d'inertie des points à moins de `rayon` du centre), direction du petit
  axe (le plan du disque), axe de rotation quand les vitesses sont là ;
- la barre et les bras : amplitude A2 et angle du motif à deux bras dans le plan du disque ;
- la taille : rayon qui contient la moitié du poids (dans le plan), épaisseur (médiane de |z|) ;
- le centre : écart entre le centre écrit dans le film et le centre des points.

Ce qui compte comme une cassure : une valeur qui saute. Pour chaque série x(t), on compare chaque image à la droite qui
joint ses deux voisines (résidu r_i = x_i − interpolation linéaire de x_{i−1} et x_{i+1}). Une évolution lisse donne des
résidus de l'ordre de x'' Δt² / 8 ; un saut de s entre deux images donne deux résidus de ± s/2. Une image est une cassure
quand |r_i| dépasse À LA FOIS un plancher physique (table SEUILS) et K fois l'écart typique robuste des résidus de la
série (1,4826 × écart médian absolu). Plancher et K : [Supposition], réglés sur l'essai synthétique
(test_essai_forme.py), à revoir sur le premier vrai film.

Lecteurs : l'ancien film de fusion (fusion.json + kf_NNN.bin, sortie de calcul.py) et une suite d'instantanés .npz
(pos, vel facultatif, m ou lum, gal, t). Le film v2 (fil des galaxies de départ) n'a pas encore de format écrit : son
lecteur n'aura qu'à rendre un objet `Film` (voir plus bas).

Usage :
  python essai_forme.py ancien <dossier du calcul> [--rayon 20] [--json sortie.json]
  python essai_forme.py npz '<motif des fichiers>' [--rayon 20] [--json sortie.json]
Rend 0 si aucune cassure, 1 sinon. La dernière ligne dit PASSE ou ECHEC.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

K_MAD = 8.0          # cassure : résidu > K × écart typique robuste de la série [Supposition]
SEUILS = {           # planchers : en dessous, un résidu n'est jamais une cassure, quel que soit le bruit [Supposition]
    'b_a': 0.02, 'c_a': 0.02,
    'plan_deg': 2.0,          # direction du petit axe (plan du disque)
    'spin_deg': 2.0,          # axe de rotation (moment cinétique)
    'a2': 0.02,
    'angle_barre_deg': 5.0,   # seulement quand A2 > A2_LISIBLE (sinon l'angle n'a pas de sens)
    'r50_rel': 0.02,          # relatif
    'epaisseur_rel': 0.03,    # relatif
    'decalage_centre_kpc': 0.2,
}
A2_LISIBLE = 0.1
POIDS_REL = 1e-6     # poids total d'une galaxie : écart relatif toléré (arrondi des nombres à 32 bits)


# ------------------------------------------------------------------ lecture
class Film:
    """Ce qu'un lecteur doit rendre.

    t : dates des images (Ga, croissantes) ; noms : nom de chaque galaxie ;
    image(i) → liste, une entrée par galaxie : dict(pos=(N,3) kpc, vel=(N,3) km/s ou None, w=(N,) poids, centre=(3,) kpc).
    Les positions et le centre sont dans le même repère (peu importe lequel)."""
    def __init__(self, t, noms, image):
        self.t, self.noms, self.image = np.asarray(t, float), list(noms), image


def lire_ancien(dossier):
    """Film de fusion de calcul.py : étoiles affichées en entiers 16 bits relatifs au centre de masse total, centres par image."""
    m = json.load(open(os.path.join(dossier, 'fusion.json'), encoding='utf-8'))
    nshow, Q = m['affichees'], m['quantum_kpc']
    N = sum(nshow)
    off = np.cumsum([0] + nshow)
    paquets = [(os.path.join(dossier, nom), k) for nom, k in m['fichiers']]
    debut = np.cumsum([0] + [k for _, k in paquets])
    C = np.array(m['centres'], float)
    noms = m.get('galaxies', ['g%d' % g for g in range(len(nshow))])
    cache = {}

    def image(i):
        p = int(np.searchsorted(debut, i, side='right') - 1)
        if p not in cache:
            cache.clear()
            chemin, k = paquets[p]
            cache[p] = np.fromfile(chemin, np.int16).reshape(k, N, 3).astype(np.float64) * Q
        a = cache[p][i - debut[p]]
        return [dict(pos=a[off[g]:off[g + 1]], vel=None, w=np.ones(nshow[g]), centre=C[i, g]) for g in range(len(nshow)) if nshow[g] > 0]
    return Film(m['t'], [n for n, k in zip(noms, nshow) if k > 0], image)


def lire_npz(motif):
    """Suite d'instantanés .npz : pos (N,3), vel (N,3) facultatif, m ou lum (N,), gal (N,) entier, t (scalaire, Ga) ;
    centres (G,3) facultatif (sinon : centre des points, resserré)."""
    fichiers = sorted(glob.glob(motif))
    if not fichiers:
        raise SystemExit(f'aucun fichier pour {motif}')
    t = [float(np.load(f)['t']) for f in fichiers]
    ordre = np.argsort(t)
    fichiers = [fichiers[k] for k in ordre]
    z0 = np.load(fichiers[0])
    gals = np.unique(z0['gal'])

    def image(i):
        z = np.load(fichiers[i])
        w = z['lum'] if 'lum' in z else z['m']
        vel = z['vel'] if 'vel' in z else None
        out = []
        for k, g in enumerate(gals):
            s = z['gal'] == g
            c = z['centres'][k] if 'centres' in z else None
            out.append(dict(pos=z['pos'][s], vel=None if vel is None else vel[s], w=np.asarray(w[s], float), centre=c))
        return out
    return Film(np.array(t)[ordre], ['g%d' % g for g in gals], image)


# ------------------------------------------------------------------ mesures
def centre_resserre(p, w, depart, rayon=5.0, tours=8):
    c = np.average(p, axis=0, weights=w) if depart is None else np.asarray(depart, float)
    for _ in range(tours):
        s = np.linalg.norm(p - c, axis=1) < rayon
        if s.sum() < 10:
            break
        c = np.average(p[s], axis=0, weights=w[s])
    return c


def base_plan(n, ref):
    """Base (e1, e2) du plan de normale n, e1 = projection de `ref` (pour un angle de barre comparable d'une image à l'autre)."""
    e1 = ref - np.dot(ref, n) * n
    if np.linalg.norm(e1) < 0.3:
        e1 = np.cross(n, [0.0, 0.0, 1.0]) if abs(n[2]) < 0.9 else np.cross(n, [1.0, 0.0, 0.0])
    e1 /= np.linalg.norm(e1)
    return e1, np.cross(n, e1)


def mediane_ponderee(x, w):
    o = np.argsort(x)
    c = np.cumsum(w[o])
    return float(x[o][np.searchsorted(c, 0.5 * c[-1])])


def mesures(g, rayon, n_prec, rayon_barre):
    """Mesures d'une galaxie à une image. n_prec : petit axe de l'image précédente (pour fixer son signe)."""
    p, w = np.asarray(g['pos'], float), np.asarray(g['w'], float)
    c = centre_resserre(p, w, g['centre'])
    out = dict(n=int(len(p)), poids=float(w.sum()))
    out['decalage_centre_kpc'] = float(np.linalg.norm(c - g['centre'])) if g['centre'] is not None else 0.0
    q = p - c
    r = np.linalg.norm(q, axis=1)
    s = r < rayon
    qs, ws = q[s], w[s]
    I = (qs * ws[:, None]).T @ qs / ws.sum()
    val, vec = np.linalg.eigh(I)                    # croissant : vec[:, 0] = petit axe
    ax = np.sqrt(np.maximum(val[::-1], 0))
    out['b_a'], out['c_a'] = float(ax[1] / ax[0]), float(ax[2] / ax[0])
    nI = vec[:, 0]
    spin = None
    if g['vel'] is not None:
        v = np.asarray(g['vel'], float)[s]
        v = v - np.average(v, axis=0, weights=ws)
        L = np.sum(ws[:, None] * np.cross(qs, v), axis=0)
        if np.linalg.norm(L) > 0:
            spin = L / np.linalg.norm(L)
    ref_n = spin if spin is not None else (n_prec if n_prec is not None else np.array([0.0, 0.0, 1.0]))
    if np.dot(nI, ref_n) < 0:
        nI = -nI
    out['_n'], out['_spin'] = nI, spin
    # plan du disque : axe de rotation s'il existe (plus stable que le petit axe pendant une rencontre), sinon petit axe
    n = spin if spin is not None else nI
    e1, e2 = base_plan(n, np.array([1.0, 0.0, 0.0]))
    x, y, z = qs @ e1, qs @ e2, qs @ n
    R = np.hypot(x, y)
    out['r50_kpc'] = mediane_ponderee(R, ws)
    out['epaisseur_kpc'] = mediane_ponderee(np.abs(z), ws)
    b = (R > 0.5) & (R < rayon_barre)
    if b.sum() > 50:
        z2 = np.sum(ws[b] * np.exp(2j * np.arctan2(y[b], x[b]))) / ws[b].sum()
        out['a2'], out['angle_barre_deg'] = float(abs(z2)), float(np.degrees(np.angle(z2)) / 2)
    else:
        out['a2'], out['angle_barre_deg'] = float('nan'), float('nan')
    return out


def angle_entre(a, b):
    if a is None or b is None:
        return float('nan')
    return float(np.degrees(np.arccos(np.clip(np.dot(a, b), -1, 1))))


# ------------------------------------------------------------------ cassures
def residus(t, x):
    """r_i = x_i − interpolation linéaire de x_{i−1} et x_{i+1} (pas de temps quelconque). NaN aux bords."""
    r = np.full(len(x), np.nan)
    if len(x) < 3:
        return r
    a = (t[2:] - t[1:-1]) / (t[2:] - t[:-2])
    r[1:-1] = x[1:-1] - (a * x[:-2] + (1 - a) * x[2:])
    return r


def cassures_serie(t, x, plancher, relatif=False):
    x = np.asarray(x, float)
    r = residus(t, x)
    if relatif:
        r = r / np.maximum(np.abs(x), 1e-12)
    ok = np.isfinite(r)
    if ok.sum() < 3:
        return [], float('nan')
    sigma = 1.4826 * float(np.median(np.abs(r[ok] - np.median(r[ok]))))
    seuil = max(plancher, K_MAD * sigma)
    return [int(i) for i in np.where(ok & (np.abs(r) > seuil))[0]], seuil


def series_angulaires(vecs):
    """Angle (degrés) de chaque vecteur avec le premier : une série scalaire qui saute si la direction saute. On prend
    en fait l'angle cumulé image à image, dont la dérivée seconde est nulle pour une rotation régulière."""
    out, cumul = [], 0.0
    for k, v in enumerate(vecs):
        if v is None:
            out.append(float('nan')); continue
        if k > 0 and vecs[k - 1] is not None:
            cumul += angle_entre(vecs[k - 1], v)
        out.append(cumul)
    return np.array(out)


def analyser(film, rayon=20.0, rayon_barre=5.0, journal=print):
    nimg = len(film.t)
    par_gal = [[] for _ in film.noms]
    n_prec = [None] * len(film.noms)
    for i in range(nimg):
        im = film.image(i)
        if len(im) != len(film.noms):
            raise SystemExit(f'image {i} : {len(im)} galaxies au lieu de {len(film.noms)}')
        for g, gal in enumerate(im):
            m = mesures(gal, rayon, n_prec[g], rayon_barre)
            n_prec[g] = m['_n']
            par_gal[g].append(m)
    t = film.t
    rapport = dict(images=nimg, t_debut=float(t[0]), t_fin=float(t[-1]), rayon_kpc=rayon, K=K_MAD, seuils=SEUILS, galaxies={})
    total = 0
    for g, nom in enumerate(film.noms):
        M = par_gal[g]
        cas = []
        n = np.array([m['n'] for m in M])
        poids = np.array([m['poids'] for m in M])
        for i in np.where(n != n[0])[0]:
            cas.append(dict(image=int(i), t=float(t[i]), grandeur='nombre de points', valeur=int(n[i]), attendu=int(n[0])))
        dp = np.abs(poids / poids[0] - 1)
        for i in np.where(dp > POIDS_REL)[0]:
            cas.append(dict(image=int(i), t=float(t[i]), grandeur='poids total (masse ou lumière)', valeur=float(poids[i]), attendu=float(poids[0])))
        series = {k: np.array([m[k] for m in M]) for k in ('b_a', 'c_a', 'a2', 'r50_kpc', 'epaisseur_kpc', 'decalage_centre_kpc')}
        series['plan_deg'] = series_angulaires([m['_n'] for m in M])
        if all(m['_spin'] is not None for m in M):
            series['spin_deg'] = series_angulaires([m['_spin'] for m in M])
        ang = np.array([m['angle_barre_deg'] for m in M])
        a2 = series['a2']
        lisible = np.isfinite(ang) & (a2 > A2_LISIBLE)
        if lisible.sum() >= 3:      # angle de période 180° : déroulé, seulement là où la barre se lit
            u = np.full(len(ang), np.nan)
            u[lisible] = np.degrees(np.unwrap(np.radians(2 * ang[lisible]))) / 2
            series['angle_barre_deg'] = u
        bilan = {}
        for k, x in series.items():
            plancher = SEUILS['r50_rel'] if k == 'r50_kpc' else SEUILS['epaisseur_rel'] if k == 'epaisseur_kpc' else SEUILS[k]
            rel = k in ('r50_kpc', 'epaisseur_kpc')
            if k == 'angle_barre_deg':
                ok = np.isfinite(x)
                idx_ok = np.where(ok)[0]
                ii, seuil = cassures_serie(t[ok], x[ok], plancher)
                ii = [int(idx_ok[j]) for j in ii]
            else:
                ii, seuil = cassures_serie(t, x, plancher, relatif=rel)
            bilan[k] = dict(min=float(np.nanmin(x)), max=float(np.nanmax(x)), seuil=seuil, cassures=len(ii))
            for i in ii:
                cas.append(dict(image=i, t=float(t[i]), grandeur=k, valeur=float(x[i]), voisins=[float(x[i - 1]), float(x[i + 1])]))
        cas.sort(key=lambda c: c['image'])
        rapport['galaxies'][nom] = dict(series=bilan, cassures=cas)
        total += len(cas)
        journal(f'{nom:10s} {len(M[0]) and M[0]["n"]:>9d} points  b/a {series["b_a"].min():.2f}–{series["b_a"].max():.2f}  '
                f'c/a {series["c_a"].min():.2f}–{series["c_a"].max():.2f}  A2 max {np.nanmax(a2):.2f}  cassures {len(cas)}')
        for c in cas[:12]:
            journal(f'    image {c["image"]:4d}  t = {c["t"]:+.3f} Ga  {c["grandeur"]} : {c["valeur"]:.4g}'
                    + (f'  (voisines {c["voisins"][0]:.4g} et {c["voisins"][1]:.4g})' if 'voisins' in c else f'  (attendu {c["attendu"]:.6g})'))
        if len(cas) > 12:
            journal(f'    … et {len(cas) - 12} autres')
    rapport['cassures'] = total
    return rapport


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('lecteur', choices=['ancien', 'npz'])
    ap.add_argument('source')
    ap.add_argument('--rayon', type=float, default=20.0, help='rayon des mesures de forme, kpc')
    ap.add_argument('--rayon-barre', type=float, default=5.0, help='rayon de la zone de la barre, kpc')
    ap.add_argument('--json', help='rapport complet')
    a = ap.parse_args()
    film = lire_ancien(a.source) if a.lecteur == 'ancien' else lire_npz(a.source)
    print(f'{len(film.t)} images de {film.t[0]:+.3f} à {film.t[-1]:+.3f} Ga ; galaxies : {", ".join(film.noms)}')
    rap = analyser(film, a.rayon, a.rayon_barre)
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as fh:
            json.dump(rap, fh, ensure_ascii=False, indent=1)
    print(f'{rap["cassures"]} cassure(s) de forme')
    print('PASSE' if rap['cassures'] == 0 else 'ECHEC')
    return 0 if rap['cassures'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
