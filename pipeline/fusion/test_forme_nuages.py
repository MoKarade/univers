#!/usr/bin/env python3
"""Essais de forme_nuages.py : les repères du ciel contre des valeurs publiées, et chaque mesure de forme sur une
géométrie construite exprès (disque d'inclinaison connue, nuage incliné, barre décalée), dont la bonne réponse est
connue d'avance. Aucune de ces géométries n'est montrée dans l'appli : elles ne servent qu'à vérifier le calcul.

Usage : python test_forme_nuages.py   (rend 0 si tout est conforme)
"""
import json
import math
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forme_nuages as N      # noqa: E402

ECHECS = []


def verifier(nom, ok, detail=''):
    print(('ok    ' if ok else 'ÉCHEC ') + nom + (f'  ({detail})' if detail else ''))
    if not ok:
        ECHECS.append(nom)


def ecart_angle(a, b, periode=360.0):
    return abs((a - b + periode / 2) % periode - periode / 2)


def test_reperes():
    # centre galactique (l = 0, b = 0) : α = 266,405°, δ = -28,936° (ICRS ; Reid & Brunthaler 2004 pour Sgr A*, à 0,05° près)
    icrs = N.A_G.T @ np.array([1.0, 0.0, 0.0])
    ra, dec = math.degrees(math.atan2(icrs[1], icrs[0])) % 360, math.degrees(math.asin(icrs[2]))
    verifier('ICRS -> galactique : direction du centre galactique', ecart_angle(ra, 266.405) < 0.05 and abs(dec + 28.936) < 0.05, f'{ra:.3f}, {dec:.3f}')
    # Courant magellanique : places publiées des Nuages (Belokurov et al. 2017) ; leurs coordonnées galactiques
    # dépendent du centre adopté : tolérance 0,5°
    ref = json.load(open(N.TABLE, encoding='utf-8'))
    axes = N.axes_courant(ref)
    for nom, lb in (('grand_nuage', (280.47, -32.89)), ('petit_nuage', (302.80, -44.30))):
        L, B = N.vers_courant(N.direction_lb(*lb)[None], axes)
        attendu = ref['repere_courant']['controle'][nom]
        verifier(f'coordonnées du Courant : {nom}', abs(L[0] - attendu[0]) < 0.5 and abs(B[0] - attendu[1]) < 0.5, f'{L[0]:.2f}, {B[0]:.2f} contre {attendu}')
    # est et nord : le nord est vers le pôle céleste, l'est à 90° dans le sens direct vu du ciel
    u0 = N.direction_lb(280.47, -32.89)
    est, nord = N.ciel_local(u0)
    pole = N.A_G @ np.array([0.0, 0.0, 1.0])
    verifier('ciel local : nord vers le pôle céleste', np.dot(nord, pole) > 0 and abs(np.dot(nord, u0)) < 1e-12)
    verifier('ciel local : est à gauche quand le nord est en haut (est × nord = direction visée)', np.dot(np.cross(est, nord), u0) > 0.999)


def disque_construit(i_deg, theta_deg, n=20000, centre_dist=50.0, rng=None):
    """Disque mince centré à 50 kpc dans la direction du Grand Nuage : ligne des nœuds à theta, côté proche à theta - 90."""
    rng = rng or np.random.default_rng(1)
    soleil = N.SOLEIL_MESURE
    u0 = N.direction_lb(280.47, -32.89)
    centre = soleil + centre_dist * u0
    est, nord = N.ciel_local(u0)
    t = math.radians(theta_deg)
    noeuds = math.cos(t) * nord + math.sin(t) * est
    sp = math.cos(t - math.pi / 2) * nord + math.sin(t - math.pi / 2) * est      # côté proche sur le ciel
    i = math.radians(i_deg)
    w = math.cos(i) * sp - math.sin(i) * u0
    r = rng.exponential(1.5, n)
    phi = rng.uniform(0, 2 * math.pi, n)
    pos = centre + (r * np.cos(phi))[:, None] * noeuds + (r * np.sin(phi))[:, None] * w + rng.normal(0, 0.05, n)[:, None] * np.cross(noeuds, w)
    return pos, centre, soleil


def test_plan():
    pos, c, s = disque_construit(34.7, 139.1)
    p = N.plan_disque(pos, c, s)
    verifier('plan : inclinaison retrouvée', abs(p['inclinaison_deg'] - 34.7) < 1.0, f"{p['inclinaison_deg']:.2f}")
    verifier('plan : ligne des nœuds retrouvée', ecart_angle(p['ligne_des_noeuds_deg'], 139.1, 180) < 1.0, f"{p['ligne_des_noeuds_deg']:.2f}")
    verifier('plan : côté proche retrouvé', ecart_angle(p['cote_proche_deg'], 49.1) < 2.0, f"{p['cote_proche_deg']:.1f}")
    pos, c, s = disque_construit(25.0, 60.0)
    p = N.plan_disque(pos, c, s)
    verifier('plan, autre orientation : côté proche', ecart_angle(p['cote_proche_deg'], 330.0) < 2.0 and abs(p['inclinaison_deg'] - 25) < 1, f"{p['cote_proche_deg']:.1f}")
    # le même disque vu de face : la profondeur ne dépend plus du côté
    prof, los = N.profondeur(pos, c, s)
    verifier('profondeur : médiane au centre', abs(prof['p50']) < 0.05, f"{prof['p50']:.3f}")


def test_cote_proche():
    rng = np.random.default_rng(2)
    s = N.SOLEIL_MESURE
    u0 = N.direction_lb(302.80, -44.30)
    c = s + 62.4 * u0
    est, nord = N.ciel_local(u0)
    xi, eta = rng.normal(0, 1.5, (2, 30000))
    z = -0.8 * xi + rng.normal(0, 0.5, 30000)                       # l'est est plus proche
    pos = c + xi[:, None] * est + eta[:, None] * nord + z[:, None] * u0
    prof, los = N.profondeur(pos, c, s)
    cp = N.cote_proche(pos, los, c, s)
    verifier('côté proche : est retrouvé', ecart_angle(cp['angle_deg'], 90.0) < 3.0, f"{cp['angle_deg']:.1f}")
    verifier('côté proche : pente retrouvée', abs(cp['pente_kpc_par_kpc'] - 0.8) < 0.03, f"{cp['pente_kpc_par_kpc']:.3f}")
    ga = N.grand_axe(pos, c, s)
    verifier('grand axe : incliné sur la visée', 30 < ga['angle_ligne_de_visee_deg'] < 70, f"{ga['angle_ligne_de_visee_deg']:.1f}")
    # écart type robuste d'une loi normale de 2 kpc le long de la visée
    pos2 = c + rng.normal(0, 2.0, 40000)[:, None] * u0
    verifier('profondeur : écart type robuste', abs(N.profondeur(pos2, c, s)[0]['sigma_robuste'] - 2.0) < 0.05)


def test_barre():
    rng = np.random.default_rng(3)
    n = np.array([0.0, 0.0, 1.0])
    disque = np.column_stack([rng.normal(0, 2, 40000), rng.normal(0, 2, 40000), np.zeros(40000)])
    b = N.barre(disque, np.zeros(3), n)
    verifier('barre : disque rond sans barre', b['a2'] < 0.03 and b['decalage_point_dense_kpc'] < 0.1, f"A2 {b['a2']:.3f}, décalage {b['decalage_point_dense_kpc']:.2f}")
    barre = np.column_stack([rng.normal(0.5, 0.6, 30000), rng.normal(0, 0.2, 30000), np.zeros(30000)])
    b = N.barre(np.vstack([disque, barre]), np.zeros(3), n)
    verifier('barre : barre allongée décalée de 0,5 kpc', b['a2'] > 0.2 and abs(b['decalage_point_dense_kpc'] - 0.5) < 0.2, f"A2 {b['a2']:.3f}, décalage {b['decalage_point_dense_kpc']:.2f}")


def test_rotation():
    rng = np.random.default_rng(4)
    a = np.array([0.0, 0.0, 1.0])
    p = np.column_stack([rng.uniform(-3, 3, 20000), rng.uniform(-3, 3, 20000), np.zeros(20000)])
    v = 30.0 * np.cross(a[None], N.unitaire(p))
    r = N.rotation(p, v, np.zeros(3), np.zeros(3), a)
    verifier('rotation : 30 km/s retrouvés', abs(r['v_rotation_kms'] - 30.0) < 0.5 and r['agitation_kms'] < 1.0, f"{r['v_rotation_kms']:.2f}")


def test_ranger():
    ref = json.load(open(N.TABLE, encoding='utf-8'))
    axes = N.axes_courant(ref)
    s = N.SOLEIL_MESURE
    cG = s + 50.0 * N.direction_lb(280.47, -32.89)
    cP = s + 62.4 * N.direction_lb(302.80, -44.30)
    milieu = (cG + cP) / 2
    x, y, z = axes                                   # place à L_MS = -60°, B_MS = 0, à 60 kpc du Soleil
    loin = s + 60.0 * (math.cos(math.radians(-60)) * x + math.sin(math.radians(-60)) * y)
    pres = cG + np.array([1.0, 0.0, 0.0])
    r = N.ranger_hors(np.array([milieu, loin, pres]), np.array([1.0, 2.0, 4.0]), cG, cP, s, axes)
    verifier('rangement : pont, courant, reste dans le Grand Nuage', r['pont'] == 1.0 and r['courant'] == 2.0 and r['total_hors'] == 3.0, json.dumps(r))


def test_film():
    """Film format 3 minuscule écrit à la main : positions absolues, Soleil, nature du gaz après un événement."""
    d = tempfile.mkdtemp()
    centres = [[0, 0, 0], [-375, 605, -279], [-515, 530, -447], [-0.8, -41.8, -27.3], [18.6, -38.0, -43.9]]
    blocs = [dict(famille=0, type=1, galaxie=3, premier=0, nombre=2), dict(famille=0, type=1, galaxie=4, premier=2, nombre=2),
             dict(famille=0, type=2, galaxie=3, premier=4, nombre=1), dict(famille=0, type=2, galaxie=4, premier=5, nombre=2),
             dict(famille=0, type=3, galaxie=0, premier=7, nombre=1)]
    dates = [dict(t=0.0, familles=1, centres=centres, vitesses=[[0, 0, 0]] * 5), dict(t=0.002, familles=2, centres=centres, vitesses=[[0, 0, 0]] * 5),
             dict(t=0.02, familles=1, centres=centres, vitesses=[[0, 0, 0]] * 5)]
    json.dump(dict(version=3, blocs=blocs, dates=dates), open(os.path.join(d, 'film.json'), 'w'))
    e = np.zeros(8, N.DT_ENREG)
    e['p'][0] = [100000, 0, 0]                      # 1 kpc
    e['p'][7] = [-820000, 0, 0]                     # Soleil à -8,2 kpc
    for k in (0, 2):
        e.tofile(os.path.join(d, f'p_{k:05d}.bin'))
    m = np.zeros(3, N.DT_MATIERE); m['masse'] = [1e5, 2e5, 3e5]; m.tofile(os.path.join(d, 'matiere.bin'))
    ev = np.zeros(1, N.DT_EVENEMENT); ev['rang'] = 1; ev['nature'] = 1; ev['date'] = 0.01; ev.tofile(os.path.join(d, 'evenements.bin'))
    f = N.Film(d)
    verifier('film : images P seulement', f.p == [0, 2])
    a, b = f.lire(f.image_proche(0.0)), f.lire(f.image_proche(0.02))
    verifier('film : position absolue', np.allclose(a['etoiles_3'][0][0], [0.2, -41.8, -27.3]))
    verifier('film : Soleil', np.allclose(a['soleil'], [-8.2, 0, 0]))
    verifier('film : gaz du Petit Nuage avant l’événement', a['gaz_4'][2].tolist() == [True, True])
    verifier('film : une particule devenue étoile', b['gaz_4'][2].tolist() == [False, True])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for t in (test_reperes, test_plan, test_cote_proche, test_barre, test_rotation, test_ranger, test_film):
        t()
    print(f'\n{len(ECHECS)} échec(s)')
    sys.exit(1 if ECHECS else 0)
