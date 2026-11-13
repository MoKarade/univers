#!/usr/bin/env python3
"""Étape 3 du plan B+ (docs/refonte-simulations-pro.md) : orbites des centres du Groupe local, ensemble Monte-Carlo et
réalisation de référence, sur les MÊMES masses et le MÊME repère que le calcul N-corps (table unique,
pipeline/constantes/univers.json).

Physique : celle de Sawala et al. 2025 (arXiv:2408.00064), reprise de groupe_local_clones.py (halos NFW 200c, forces
adoucies de 20 kpc, frottement de Chandrasekhar avec la dispersion de Zentner et Bullock 2003, fusion à moins de 20 kpc,
saute-mouton à pas de 1 Ma), avec deux ajouts :
- l'énergie noire : a = H0² Ω_Λ (x − x_cm) sur chaque galaxie (constante K_lambda de la table) ; option --sans-energie-noire ;
- le Petit Nuage de Magellan (masse ADOPTÉE, pas mesurée : voir la table) ; option --sans-petit-nuage.

Différences avec Sawala, toutes voulues (règle « mêmes masses ») : masses centrées sur celles des modèles du calcul
N-corps ; mouvements propres d'Andromède et du Triangle de Wu et al. 2025 ; repère de l'appli (R0 = 8,20 kpc,
v0 = 232,8 km/s) au lieu du repère « v4.0 » d'astropy. La variante --variante=sawala2025 remet leurs masses et leurs
mouvements propres, pour comparer avec leur résultat publié (~50 % de fusion en 10 Ga).

Sorties (dossier --sortie, par défaut pipeline/fusion/resultats/) :
- ensemble_<variante>.json : probabilité et dates de la fusion Voie lactée–Andromède, autres paires ;
- cible_aujourdhui.json : pour le fil des galaxies de départ (depart_passe.py) : position et vitesse d'AUJOURD'HUI de chaque
  galaxie (repère phys::galaxie), masse, et où la référence les place à −3 Ga ;
- centres_reference.npz : pour l'appli (fil Voie lactée) : t (Ga, 0 = aujourd'hui), position (kpc) et vitesse (km/s) du
  centre de chaque galaxie, RELATIVES AU CENTRE DE LA VOIE LACTÉE (repère phys::galaxie), un point par pas de ~1 Ma de
  −3 à +10 Ga ; en-tête JSON dans « meta ».

Usage : python pipeline/fusion/groupe_local_reference.py [--n 5000] [--variante unifie|sawala2025] [--sans-energie-noire]
        [--sans-petit-nuage] [--passe 3.0] [--futur 10.0] [--sortie dossier] [--reference-seulement]
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np
from scipy.stats import truncnorm
from scipy.special import erf
import astropy.units as u
from astropy.coordinates import SkyCoord, Distance

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(ICI), 'constantes'))
import constantes as C      # noqa: E402

G = 43007.0                                         # kpc (km/s)² / 10^10 M☉
UNITE_GA = 3.0856775814913673e16 / 3.15576e16       # kpc/(km/s) en Ga = 0,97779
RHO_C = 277.536627 * 0.674 ** 2                     # densité critique (M☉/kpc³), H0 de la table
COURT = {'voie_lactee': 'MW', 'andromede': 'M31', 'triangle': 'M33', 'grand_nuage': 'LMC', 'petit_nuage': 'SMC'}
# Variante « sawala2025 » : leurs masses (M200, 10^10 M☉) et mouvements propres (µas/an), Extended Data Table 1.
SAWALA = {'voie_lactee': dict(m=(100, 20)), 'andromede': dict(m=(130, 40), pmra=(48.9, 10.5), pmdec=(-36.9, 8.1)),
          'triangle': dict(m=(30, 10), pmra=(31, 19), pmdec=(-29, 16)), 'grand_nuage': dict(m=(15, 5)), 'petit_nuage': dict(m=(0.3, 0.1))}


def _rs_modele(g):
    h = (g.get('modele') or {}).get('halo') or {}
    return h.get('rs')


def lois(cles, variante):
    """Pour chaque galaxie et grandeur : (centre, écart type). Masses en 10^10 M☉."""
    t, out = C.charger(), {}
    for k in cles:
        g = t['galaxies'][k]
        lm = g['loi_masse']
        d = dict(m=(lm['centre'] / 1e10, lm['sigma'] / 1e10))
        # concentration : celle du modèle quand son halo est un NFW (r200 / rs), sinon 10 ± 2 (Sawala)
        rs = _rs_modele(g)
        if rs and variante == 'unifie':
            r200 = (3 * lm['centre'] / (4 * math.pi * 200 * RHO_C)) ** (1 / 3)
            d['c'] = (r200 / rs, 2.0)
        else:
            d['c'] = (t['ensemble']['concentration']['centre'], t['ensemble']['concentration']['sigma'])
        if 'observe' in g:
            o = g['observe']
            for q in ('dmod', 'pmra', 'pmdec', 'vr'):
                d[q] = (o[q], o[q + '_err'])
        if variante == 'sawala2025':
            d.update(SAWALA[k])
        out[k] = d
    return out


def tirer(loi, n, clip, graine, central):
    if central or n == 1:
        return np.full(max(n, 1), float(loi[0]))
    rng = np.random.default_rng(graine)
    return truncnorm(-clip, clip, loc=loi[0], scale=loi[1]).rvs(n, random_state=rng)


def conditions(cles, n, clip, variante, central=False):
    t = C.charger()
    L = lois(cles, variante)
    N = len(cles)
    m, c = np.zeros((n, N)), np.zeros((n, N))
    pos, vel = np.zeros((n, N, 3)), np.zeros((n, N, 3))
    rep = t['repere']
    soleil_x = np.array(rep['soleil_position']); soleil_v = np.array(rep['soleil_vitesse'])
    graine = 0
    for i, k in enumerate(cles):
        m[:, i] = tirer(L[k]['m'], n, clip, graine, central); graine += 1
        c[:, i] = tirer(L[k]['c'], n, clip, graine, central); graine += 1
        if 'dmod' not in L[k]:
            graine += 4; continue
        o = t['galaxies'][k]['observe']
        q = {}
        for nom in ('dmod', 'pmra', 'pmdec', 'vr'):
            q[nom] = tirer(L[k][nom], n, clip, graine, central); graine += 1
        sky = SkyCoord(ra=np.full(n, o['ra']) * u.deg, dec=np.full(n, o['dec']) * u.deg, distance=Distance(distmod=q['dmod'] * u.mag),
                       pm_ra_cosdec=q['pmra'] * u.uas / u.yr, pm_dec=q['pmdec'] * u.uas / u.yr, radial_velocity=q['vr'] * u.km / u.s,
                       frame='icrs').galactic
        pos[:, i] = sky.cartesian.xyz.to_value(u.kpc).T + soleil_x
        vel[:, i] = sky.velocity.d_xyz.to_value(u.km / u.s).T + soleil_v
    return m, c, pos, vel


def nfw(m, c):
    M = m * 1e10
    r200 = (3 * M / (4 * math.pi * 200 * RHO_C)) ** (1 / 3)
    rs = r200 / c
    gfun = lambda x: np.log1p(x) - x / (1 + x)
    xm = 2.1625815870646098
    vmax = np.sqrt(4.30091727e-6 * M / r200 * c * gfun(xm) / (gfun(c) * xm))
    return rs, r200, vmax


def matrice_paires(cles, valeur_sawala, rs):
    """Adoucissement ou seuil de fusion par paire : 20 kpc (Sawala) entre les quatre grandes ; pour une paire avec le Petit Nuage
    (absent de Sawala, à 24 kpc du Grand Nuage aujourd'hui), la moyenne des rayons d'échelle des deux halos [modèle]."""
    N = len(cles)
    M = np.full((N, N), float(valeur_sawala))
    for i in range(N):
        for j in range(N):
            if 'petit_nuage' in (cles[i], cles[j]):
                M[i, j] = min(valeur_sawala, 0.5 * (rs[i] + rs[j]))
    return M


def acc(pos, m, soft, K, energie_noire):
    d = pos[:, None, :, :] - pos[:, :, None, :]
    r2 = (d * d).sum(-1) + soft * soft      # soft : (N, N)
    a = G * (d * (r2 ** -1.5)[..., None] * m[:, None, :, None]).sum(2)
    if energie_noire:
        mt = m.sum(1, keepdims=True)
        cm = (m[..., None] * pos).sum(1, keepdims=True) / mt[..., None]
        a += K * np.where((m > 0)[..., None], pos - cm, 0.0)
    return a


def frottement(pos, vel, m, c, rs, r200, vmax):
    """Chandrasekhar, comme groupe_local_clones.py (Sawala 2025)."""
    n, N = m.shape
    f = np.zeros_like(pos)
    for i in range(N):
        for j in range(N):
            if i == j: continue
            ok = (m[:, i] > 0) & (m[:, j] > 0) & (m[:, j] > m[:, i])
            dr = pos[:, i] - pos[:, j]
            r = np.maximum(10.0, np.linalg.norm(dr, axis=1))
            ok &= r < r200[:, j]
            if not ok.any(): continue
            dv = vel[:, i] - vel[:, j]; v = np.linalg.norm(dv, axis=1)
            gc = np.log1p(c[:, j]) - c[:, j] / (1 + c[:, j])
            rho = m[:, j] / (4 * math.pi * gc * r * (r + rs[:, j]) ** 2)
            x = r / rs[:, j]
            sig = vmax[:, j] * 1.4393 * x ** 0.354 / (1 + 1.1756 * x ** 0.725)
            y = v / (math.sqrt(2) * sig)
            integ = erf(y) - 2 * y / math.sqrt(math.pi) * np.exp(-y * y)
            eps = np.where(rs[:, i] > 8.0, 2.2 * rs[:, i] - 14, 0.45 * rs[:, i])
            with np.errstate(invalid='ignore', divide='ignore'):
                mag = 4 * math.pi * G * G * np.log(np.maximum(r / eps, 1.0)) * m[:, i] * rho * integ / np.maximum(v, 5) ** 3
            mag = np.where(ok, mag, 0.0)
            tot = np.where(ok, m[:, i] + m[:, j], 1.0)
            f[:, i] -= dv * (mag * m[:, j] / tot)[:, None]
            f[:, j] += dv * (mag * m[:, i] / tot)[:, None]
    return f


def integre(m, c, pos, vel, duree, dt, soft, seuil, K, energie_noire, fusionner=True, garder=1):
    """duree en unités kpc/(km/s), signée (négative : vers le passé). Rend fusions (dates signées), état, trajectoires."""
    n, N = m.shape
    m, pos, vel = m.copy(), pos.copy(), vel.copy()
    rs, r200, vmax = nfw(np.maximum(m, 1e-6), c)
    h = math.copysign(dt, duree)
    a = acc(pos, m, soft, K, energie_noire) + frottement(pos, vel, m, c, rs, r200, vmax)
    existe = np.ones((n, N), bool)
    fusion = np.full((n, N, N), np.inf)
    absorbe = np.full((n, N), -1)
    Nt = int(round(abs(duree) / dt))
    tp, tv = [pos.astype(np.float64).copy()], [vel.copy()]
    for k in range(Nt):
        vel += a * h / 2
        pos += vel * h
        a = acc(pos, m, soft, K, energie_noire) + frottement(pos, vel, m, c, rs, r200, vmax)
        vel += a * h / 2
        if fusionner:
            for l in range(N):
                for q in range(l):
                    d = np.linalg.norm(pos[:, l] - pos[:, q], axis=1)
                    hit = existe[:, l] & existe[:, q] & (d < seuil[l, q])
                    if not hit.any(): continue
                    s = np.nonzero(hit)[0]
                    keep = np.where(m[s, l] > m[s, q], l, q); rem = np.where(m[s, l] > m[s, q], q, l)
                    mk, mr = m[s, keep], m[s, rem]
                    pos[s, keep] = (mk[:, None] * pos[s, keep] + mr[:, None] * pos[s, rem]) / (mk + mr)[:, None]
                    vel[s, keep] = (mk[:, None] * vel[s, keep] + mr[:, None] * vel[s, rem]) / (mk + mr)[:, None]
                    m[s, keep] = mk + mr; m[s, rem] = 0; existe[s, rem] = False; absorbe[s, rem] = keep
                    fusion[s, l, q] = np.minimum(fusion[s, l, q], (k + 1) * h); fusion[s, q, l] = fusion[s, l, q]
            for i in range(N):
                gone = ~existe[:, i]
                if gone.any():
                    s = np.nonzero(gone)[0]; pos[s, i] = pos[s, absorbe[s, i]]; vel[s, i] = vel[s, absorbe[s, i]]
        if (k + 1) % garder == 0:
            tp.append(pos.copy()); tv.append(vel.copy())
    return fusion, existe, absorbe, np.array(tp), np.array(tv)


def date_fusion_mw_m31(fusion, m, cles):
    t = fusion[:, 0, 1].copy()
    for k in range(2, len(cles)):
        t = np.minimum(t, np.where(m[:, k] > m[:, 0], fusion[:, 0, k], np.inf))
        t = np.minimum(t, np.where(m[:, k] > m[:, 1], fusion[:, 1, k], np.inf))
    return t


def ensemble(cles, n, clip, variante, energie_noire, futur_ga, reglages):
    t0 = time.time()
    m, c, pos, vel = conditions(cles, n, clip, variante)
    vel -= (m[..., None] * vel).sum(1, keepdims=True) / m.sum(1)[:, None, None]
    rs0 = nfw(m.mean(0), c.mean(0))[0]
    soft = matrice_paires(cles, reglages['adoucissement_kpc'], rs0); seuil = matrice_paires(cles, reglages['seuil_fusion_kpc'], rs0)
    fusion, existe, _, _, _ = integre(m, c, pos, vel, futur_ga / UNITE_GA, reglages['pas_ga'] / UNITE_GA, soft, seuil,
                                      C.K_lambda(), energie_noire, garder=10 ** 9)
    tf = date_fusion_mw_m31(fusion, m, cles)
    ok = np.isfinite(tf); tg = tf[ok] * UNITE_GA
    res = dict(variante=variante, energie_noire=energie_noire, galaxies=[COURT[k] for k in cles], n=n, clip=clip,
               probabilite_fusion_mw_m31=round(float(ok.mean()), 4),
               quantiles_ga={str(q): round(float(np.quantile(tg, q)), 3) for q in (0.05, 0.16, 0.5, 0.84, 0.95)} if ok.any() else None,
               duree_s=round(time.time() - t0, 1))
    for a, b in (('grand_nuage', 'voie_lactee'), ('triangle', 'andromede'), ('petit_nuage', 'grand_nuage')):
        if a in cles and b in cles:
            f = fusion[:, cles.index(a), cles.index(b)]
            res[f'probabilite_{COURT[a]}_{COURT[b]}'] = round(float(np.isfinite(f).mean()), 4)
    return res


def reference(cles, variante, energie_noire, passe_ga, futur_ga, reglages):
    """Réalisation de référence : toutes les grandeurs à leur valeur centrale. Rend t (Ga), pos, vel (relatives à la Voie lactée)."""
    m, c, pos, vel = conditions(cles, 1, 2.0, variante, central=True)
    vcm = (m[..., None] * vel).sum(1, keepdims=True) / m.sum(1)[:, None, None]
    vel = vel - vcm
    dt = reglages['pas_ga'] / UNITE_GA
    K = C.K_lambda()
    rs0 = nfw(m[0], c[0])[0]
    args = (matrice_paires(cles, reglages['adoucissement_kpc'], rs0), matrice_paires(cles, reglages['seuil_fusion_kpc'], rs0), K, energie_noire)
    # Pas de fusion « instantanée » ici : quand deux centres se rejoignent, Sawala remplace les deux galaxies par leur centre de
    # masse en un pas, ce qui fait sauter de plusieurs kpc le centre de la Voie lactée, donc tout le repère de l'affichage.
    # La référence garde les deux corps (le frottement les amène l'un sur l'autre en continu) ; la date de fusion est celle où
    # les centres passent sous le seuil pour la première fois (même critère que l'ensemble).
    _, _, _, pa, va = integre(m, c, pos, vel, futur_ga / UNITE_GA, dt, *args, fusionner=False)
    _, _, _, pp, vp = integre(m, c, pos, vel, -passe_ga / UNITE_GA, dt, *args, fusionner=False)
    na, np_ = len(pa), len(pp)
    t = np.concatenate([-np.arange(np_ - 1, 0, -1), np.arange(na)]) * reglages['pas_ga']
    P = np.concatenate([pp[:0:-1], pa])[:, 0]; V = np.concatenate([vp[:0:-1], va])[:, 0]
    seuil = args[1]
    fusions = {}
    for i in range(len(cles)):
        for j in range(i):
            d = np.linalg.norm(P[:, i] - P[:, j], axis=1)
            sous = np.nonzero((t > 0) & (d < seuil[i, j]))[0]
            if len(sous): fusions[f'{COURT[cles[i]]}+{COURT[cles[j]]}'] = round(float(t[sous[0]]), 3)
    tf = fusions.get('M31+MW', float('inf'))
    # relatif au centre de la Voie lactée (repère phys::galaxie)
    P = P - P[:, :1]; V = V - V[:, :1]
    return dict(t=t, pos=P, vel=V, m=m[0], c=c[0], fusion_mw_m31_ga=float(tf), fusions=fusions)


def distances_cles(ref, cles):
    """Premier passage au plus près de chaque galaxie à la Voie lactée (futur), et distance à −3 Ga."""
    t, P = ref['t'], ref['pos']
    out = {}
    for i, k in enumerate(cles):
        if i == 0: continue
        d = np.linalg.norm(P[:, i], axis=1)
        fut = t >= 0
        dd, tt = d[fut], t[fut]
        # premier minimum local (péricentre)
        j = next((q for q in range(1, len(dd) - 1) if dd[q] <= dd[q - 1] and dd[q] < dd[q + 1]), int(np.argmin(dd)))
        out[COURT[k]] = dict(aujourdhui_kpc=round(float(d[t == 0][0]), 1), premier_rapprochement_ga=round(float(tt[j]), 3),
                             distance_rapprochement_kpc=round(float(dd[j]), 1), distance_depart_kpc=round(float(d[0]), 1))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--n', type=int, default=5000)
    p.add_argument('--variante', default='unifie', choices=['unifie', 'sawala2025'])
    p.add_argument('--sans-energie-noire', action='store_true')
    p.add_argument('--sans-petit-nuage', action='store_true')
    p.add_argument('--passe', type=float, default=3.0)
    p.add_argument('--futur', type=float, default=10.0)
    p.add_argument('--clip', type=float, default=2.0)
    p.add_argument('--sortie', default=os.path.join(ICI, 'resultats'))
    p.add_argument('--reference-seulement', action='store_true')
    p.add_argument('--ensemble-seulement', action='store_true')
    a = p.parse_args()
    t = C.charger()
    cles = [k for k in t['ordre'] if not (a.sans_petit_nuage and k == 'petit_nuage')]
    reg = t['ensemble']
    en = not a.sans_energie_noire
    os.makedirs(a.sortie, exist_ok=True)
    suffixe = a.variante + ('' if en else '_sans_energie_noire') + ('_sans_smc' if a.sans_petit_nuage else '')
    if not a.reference_seulement:
        res = ensemble(cles, a.n, a.clip, a.variante, en, a.futur, reg)
        print(json.dumps(res, ensure_ascii=False))
        with open(os.path.join(a.sortie, f'ensemble_{suffixe}.json'), 'w', encoding='utf-8') as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1); fh.write('\n')
    if a.ensemble_seulement:
        return
    ref = reference(cles, a.variante, en, a.passe, a.futur, reg)
    resume = dict(fusion_mw_m31_ga=round(ref['fusion_mw_m31_ga'], 3) if math.isfinite(ref['fusion_mw_m31_ga']) else None,
                  fusions=ref['fusions'], passages=distances_cles(ref, cles))
    print(json.dumps(resume, ensure_ascii=False))
    if a.variante != 'unifie' or not en or a.sans_petit_nuage:
        return      # seule la variante complète écrit les fichiers de référence
    i0 = int(np.argmin(np.abs(ref['t'])))
    meta = dict(
        version=1, date='2026-11-13', genere_par='pipeline/fusion/groupe_local_reference.py',
        repere='phys::galaxie : centre de la Voie lactée à l’origine À CHAQUE DATE (positions et vitesses relatives à lui), axes galactiques, '
               f"Soleil en ({', '.join('%.4f' % x for x in t['repere']['soleil_position'])}) kpc",
        unites=dict(t='Ga (0 = aujourd’hui, positif vers le futur)', pos='kpc', vel='km/s'),
        origine_des_temps='aujourd’hui (t = 0 exactement à l’indice i_aujourdhui)', i_aujourdhui=i0,
        pas_ga=reg['pas_ga'], galaxies=cles, noms=[t['galaxies'][k]['nom'] for k in cles],
        masses=[float(x * 1e10) for x in ref['m']], concentrations=[round(float(x), 3) for x in ref['c']],
        conditions_initiales='aujourd’hui : valeurs centrales de pipeline/constantes/univers.json (table unique) ; intégration vers le passé '
                             'et vers le futur sans fusion instantanée (les deux corps restent, le frottement les rapproche en continu ; '
                             'dates de fusion = premier passage des centres sous le seuil, dans « resume »)',
        physique='Sawala et al. 2025 (halos NFW, adoucissement 20 kpc, frottement de Chandrasekhar) + énergie noire H0² Ω_Λ (x − x_cm)',
        statut='calculé : orbites des CENTRES seulement (galaxies indéformables) ; une seule histoire parmi l’ensemble (voir ensemble_unifie.json) ; '
               'remplacé par le film N-corps quand il existera',
        resume=resume)
    np.savez_compressed(os.path.join(a.sortie, 'centres_reference.npz'), t=ref['t'].astype(np.float64), pos=ref['pos'].astype(np.float32),
                        vel=ref['vel'].astype(np.float32), meta=json.dumps(meta, ensure_ascii=False))
    j_dep = 0
    cible = dict(
        version=1, date='2026-11-13', genere_par='pipeline/fusion/groupe_local_reference.py',
        repere='phys::galaxie (Voie lactée à l’origine et au repos aujourd’hui)', unites='kpc, km/s, M☉, Ga',
        source='pipeline/constantes/univers.json (valeurs centrales) ; ce sont les positions et vitesses à atteindre AUJOURD’HUI',
        galaxies={k: dict(nom=t['galaxies'][k]['nom'], masse=float(ref['m'][i] * 1e10),
                          position_aujourdhui=np.round(t['galaxies'][k]['aujourdhui']['position'], 4).tolist(),
                          vitesse_aujourdhui=np.round(t['galaxies'][k]['aujourdhui']['vitesse'], 3).tolist(),
                          position_reference_moins_passe=np.round(ref['pos'][j_dep, i], 3).tolist(),
                          vitesse_reference_moins_passe=np.round(ref['vel'][j_dep, i], 3).tolist())
                  for i, k in enumerate(cles)},
        debut_reference_ga=float(ref['t'][0]),
        note='Les positions « reference_moins_passe » viennent des orbites des centres (galaxies indéformables) : elles servent de point de '
             'départ au tir, pas de vérité ; le calcul N-corps doit retomber sur « aujourdhui » à t = 0.')
    with open(os.path.join(a.sortie, 'cible_aujourdhui.json'), 'w', encoding='utf-8') as fh:
        json.dump(cible, fh, ensure_ascii=False, indent=1); fh.write('\n')


if __name__ == '__main__':
    main()
