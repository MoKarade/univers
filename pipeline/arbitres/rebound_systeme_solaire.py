#!/usr/bin/env python3
"""Arbitre REBOUND (processeur seul) : Soleil, 8 planètes (Terre = barycentre Terre-Lune), Pluton, Cérès, Vesta, Pallas,
Hygie, intégrés avec IAS15 sur ±200 ans autour de l'époque de natif/physique/nbody_donnees.h.

Conditions de départ : lues dans nbody_donnees.h (mêmes valeurs que le calcul natif), UA / jour, écliptique J2000, TDB.
  - kQ : positions héliocentriques ; kV : vitesses barycentriques (coordonnées « démocratiques »).
  - Soleil : position = -Σ gm·Q / (GM☉ + Σ gm), vitesse = -Σ gm·V / GM☉ (quantité de mouvement totale nulle),
    comme Integrator::barycentric et sunVel du code natif.
  - kScale n'est PAS appliqué : c'est le calage propre au pas fixe de 4 jours du schéma natif ; IAS15 n'en a pas besoin.
Unités : G = 1, masse = GM (UA³/jour²), temps en jours.

Relativité : REBOUNDx n'a pas de paquet Windows prêt (il faut un compilateur C). La correction post-newtonienne du
Soleil est donc écrite ici, en force additionnelle : formule de Schwarzschild (coordonnées harmoniques, corps d'essai),
  a = GM☉ / (c² r³) · [ (4 GM☉ / r − v²) r⃗ + 4 (r⃗·v⃗) v⃗ ],  r⃗, v⃗ héliocentriques,
la réaction opposée étant appliquée au Soleil (quantité de mouvement conservée). C'est le terme dominant de l'effet
« gr » de REBOUNDx (avance du périhélie de Mercure ≈ 43″ par siècle) ; les termes en masses planétaires sont omis.

Sortie : pipeline/arbitres/resultats/rebound_ref.json (positions et vitesses barycentriques tous les 10 ans).
Usage : python rebound_systeme_solaire.py [--sans-gr] [--depart-horizons]
"""
import ctypes
import json
import math
import os
import re
import sys
import time

import numpy as np
import rebound

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, '..', '..'))
ENTETE = os.path.join(RACINE, 'natif', 'physique', 'nbody_donnees.h')
REF_HORIZONS = os.path.join(RACINE, 'app', 'test', 'nbody_ref.json')
SORTIE = os.path.join(ICI, 'resultats', 'rebound_ref.json')

GM_SOLEIL = 2.9591220828411956e-4      # UA³/jour², même valeur que nbody_noyau.h (kGmSun)
C_UA_JOUR = 173.1446326846693           # vitesse de la lumière en UA/jour (kCAuDay)
JOURS_PAR_AN = 365.25
DUREE_ANS = 200
PAS_SORTIE_ANS = 10


def lire_entete(chemin):
    """Lit les constantes de nbody_donnees.h (fichier généré, format stable)."""
    texte = open(chemin, encoding='utf-8').read()

    def tableau(nom):
        m = re.search(r'constexpr double ' + nom + r'\[\] = \{([^}]*)\}', texte)
        if not m:
            raise ValueError(f'{nom} introuvable dans {chemin}')
        return [float(x) for x in m.group(1).split(',')]

    jd0 = float(re.search(r'kJd0 = ([0-9.eE+-]+);', texte).group(1))
    noms = re.findall(r'"([a-z]+)"', re.search(r'kNames\[\] = \{([^}]*)\}', texte).group(1))
    gm, q, v = tableau('kGm'), tableau('kQ'), tableau('kV')
    if not (len(gm) == len(noms) and len(q) == len(v) == 3 * len(noms)):
        raise ValueError('tailles incohérentes dans nbody_donnees.h')
    return jd0, noms, gm, q, v


DEPART_HORIZONS = '--depart-horizons' in sys.argv


def construire(noms, gm, q, v):
    if DEPART_HORIZONS:
        return construire_horizons(noms, gm)
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.integrator = 'ias15'
    m_tot = GM_SOLEIL + sum(gm)
    sun_r = [-sum(gm[i] * q[3 * i + c] for i in range(len(noms))) / m_tot for c in range(3)]
    sun_v = [-sum(gm[i] * v[3 * i + c] for i in range(len(noms))) / GM_SOLEIL for c in range(3)]
    sim.add(m=GM_SOLEIL, x=sun_r[0], y=sun_r[1], z=sun_r[2], vx=sun_v[0], vy=sun_v[1], vz=sun_v[2])
    for i, nom in enumerate(noms):
        sim.add(m=gm[i], x=q[3 * i] + sun_r[0], y=q[3 * i + 1] + sun_r[1], z=q[3 * i + 2] + sun_r[2],
                vx=v[3 * i], vy=v[3 * i + 1], vz=v[3 * i + 2])
    return sim


def construire_horizons(noms, gm):
    """Variante : état barycentrique JPL Horizons à la même époque (app/test/nbody_ref.json, clé « epoch »).
    Les vitesses de nbody_donnees.h sont calées pour le pas de 4 jours du schéma natif (Mercure : écart relatif ~2e-6
    à Horizons) ; un intégrateur exact parti de ces vitesses dérive. Ce départ-ci donne l'arbitre physique."""
    ep = json.load(open(REF_HORIZONS, encoding='utf-8'))['epoch']
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.integrator = 'ias15'
    for nom, m in [('sun', GM_SOLEIL)] + list(zip(noms, gm)):
        r, v = ep[nom]['r'], ep[nom]['v']
        sim.add(m=m, x=r[0], y=r[1], z=r[2], vx=v[0], vy=v[1], vz=v[2])
    return sim


def ajouter_relativite(sim):
    """Force post-newtonienne du Soleil (voir l'en-tête du fichier)."""
    c2 = C_UA_JOUR * C_UA_JOUR
    # Vue numpy directe sur le tableau C des particules (x y z vx vy vz ax ay az m …), sans copie : l'accès
    # attribut par attribut via ctypes coûtait ~26 s par année simulée.
    n_dbl = ctypes.sizeof(rebound.Particle) // 8
    p_dbl = ctypes.POINTER(ctypes.c_double)

    def force(sim_ptr):
        s = sim_ptr.contents
        a = np.ctypeslib.as_array(ctypes.cast(s._particles, p_dbl), shape=(s.N * n_dbl,)).reshape(s.N, n_dbl)
        mu = a[0, 9]
        rel = a[1:, 0:6] - a[0, 0:6]
        r_vec, v_vec = rel[:, 0:3], rel[:, 3:6]
        r2 = np.einsum('ij,ij->i', r_vec, r_vec)
        r = np.sqrt(r2)
        v2 = np.einsum('ij,ij->i', v_vec, v_vec)
        rv = np.einsum('ij,ij->i', r_vec, v_vec)
        f = mu / (c2 * r2 * r)
        acc = (f * (4.0 * mu / r - v2))[:, None] * r_vec + (4.0 * f * rv)[:, None] * v_vec
        a[1:, 6:9] += acc
        a[0, 6:9] -= (a[1:, 9:10] / mu * acc).sum(axis=0)

    sim.additional_forces = force
    sim.force_is_velocity_dependent = 1


def etat(sim, noms_tous):
    return {n: {'r': list(sim.particles[i].xyz), 'v': list(sim.particles[i].vxyz)} for i, n in enumerate(noms_tous)}


def integrer(jd0, noms, gm, q, v, avec_gr):
    """Intègre vers le futur puis vers le passé ; renvoie instantanés, erreurs d'énergie, durée."""
    noms_tous = ['sun'] + noms
    instantanes, erreurs = {}, {}
    debut = time.time()
    for sens in (1, -1):
        sim = construire(noms, gm, q, v)
        if avec_gr:
            ajouter_relativite(sim)
        sim.move_to_com()
        e0 = sim.energy()
        e_max = 0.0
        for k in range(0, DUREE_ANS // PAS_SORTIE_ANS + 1):
            t = sens * k * PAS_SORTIE_ANS * JOURS_PAR_AN
            sim.integrate(t, exact_finish_time=1)
            e_max = max(e_max, abs((sim.energy() - e0) / e0))
            instantanes[f'{jd0 + t:.1f}'] = {'jd': jd0 + t, 'annees': sens * k * PAS_SORTIE_ANS, 'corps': etat(sim, noms_tous)}
        erreurs['futur' if sens > 0 else 'passe'] = e_max
    return instantanes, erreurs, time.time() - debut


def ecarts_horizons(jd0, noms, gm, q, v, avec_gr):
    """Écart aux positions barycentriques JPL Horizons de app/test/nbody_ref.json, aux dates dans ±200 ans."""
    if not os.path.exists(REF_HORIZONS):
        return {}
    ref = json.load(open(REF_HORIZONS, encoding='utf-8'))['checks']
    noms_tous = ['sun'] + noms
    res = {}
    for date, R in sorted(ref.items()):
        jd = R['sun']['jd']
        if abs(jd - jd0) > DUREE_ANS * JOURS_PAR_AN:
            continue
        sim = construire(noms, gm, q, v)
        if avec_gr:
            ajouter_relativite(sim)
        sim.move_to_com()
        sim.integrate(jd - jd0, exact_finish_time=1)
        ecarts = {}
        for i, n in enumerate(noms_tous):
            if n in R:
                d = [sim.particles[i].xyz[c] - R[n]['r'][c] for c in range(3)]
                ecarts[n] = math.sqrt(sum(x * x for x in d)) * 1.495978707e8      # km
        res[date] = ecarts
    return res


def main():
    avec_gr = '--sans-gr' not in sys.argv
    jd0, noms, gm, q, v = lire_entete(ENTETE)
    instantanes, erreurs, duree = integrer(jd0, noms, gm, q, v, avec_gr)
    ecarts = ecarts_horizons(jd0, noms, gm, q, v, avec_gr)
    sortie = {
        'source': 'REBOUND ' + rebound.__version__ + ', IAS15, départ : ' + (
            'JPL Horizons (app/test/nbody_ref.json, epoch)' if DEPART_HORIZONS else 'natif/physique/nbody_donnees.h'),
        'unites': 'UA, UA/jour, barycentrique, écliptique J2000, TDB',
        'relativite': 'Schwarzschild 1PN du Soleil (force maison, REBOUNDx absent)' if avec_gr else 'aucune',
        'jd0': jd0,
        'erreur_energie_relative_max': erreurs,
        'note_energie': "énergie newtonienne : avec la relativité elle n'est pas exactement conservée" if avec_gr else '',
        'ecart_horizons_km': ecarts,
        'duree_calcul_s': round(duree, 1),
        'instantanes': [instantanes[k] for k in sorted(instantanes, key=float)],
    }
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    chemin = SORTIE if avec_gr else SORTIE.replace('.json', '_sans_gr.json')
    if DEPART_HORIZONS:
        chemin = chemin.replace('.json', '_depart_horizons.json')
    with open(chemin, 'w', encoding='utf-8') as fh:
        json.dump(sortie, fh, indent=1)
    print('REBOUND', rebound.__version__, '| relativité :', 'oui' if avec_gr else 'non')
    print('erreur d\'énergie relative max :', erreurs)
    print('durée :', round(duree, 1), 's')
    for date, e in ecarts.items():
        print('écart Horizons', date, {k: round(x) for k, x in e.items()})
    print('écrit', chemin)


if __name__ == '__main__':
    main()
