#!/usr/bin/env python3
"""Modèles de départ des galaxies, version 2 : paramètres relus dans les publications (docs/parametres-galaxies.md).

Remplace modeles.py, dont les disques étaient trop lourds et instables (Q de Toomre 0,6 à 0,75 : pipeline/fusion/stabilite.py)
et dont le halo de la Voie lactée était calé pour un autre disque que celui utilisé (252 km/s au Soleil au lieu de 230).
modeles.py est gardé tel quel pour pouvoir refaire les anciens calculs.

Ce fichier ne fait que les GALAXIES SEULES, à l'équilibre (AGAMA). Leur stabilité se contrôle ensuite par un tir sur la
carte graphique (stabilite_tir.py) avant toute rencontre : une galaxie seule doit rester calme.

Unités : M☉, kpc, km/s (G = 4,30091e-6). Sortie : .npz avec pos, vel, m, eps, kind
(0 matière noire, 1 disque mince, 2 bulbe, 3 gaz traité comme des étoiles froides, 4 disque épais).

Ce qui est mesuré, et ce qui ne l'est pas :
- masses, longueurs, hauteurs, halo : publiés (source à chaque ligne) ;
- agitation radiale des étoiles au Soleil : mesurée pour la Voie lactée (35 et 50 km/s, Bland-Hawthorn & Gerhard 2016) ;
  pour les autres galaxies elle n'est pas mesurée étoile par étoile : réglée pour Q = 1,5 au minimum [modèle] ;
- la barre n'est PAS posée ici : elle doit naître en laissant vieillir la galaxie seule, puis être comparée aux mesures
  (Voie lactée : 5,0 kpc, 39 km/s/kpc ; Andromède : 4,0 kpc, 40 km/s/kpc).

Usage : python modeles_v2.py <voie_lactee|andromede|triangle|grand_nuage> <particules en tout> <sortie.npz>
"""
import json
import math
import sys

import numpy as np

G = 4.30091e-6
PART_HALO = 0.7      # part des particules donnée à la matière noire (0,5 donnait des particules de halo 22 fois plus lourdes que les étoiles)

# Chaque composante : forme, paramètres, part des particules. Les sources sont dans docs/parametres-galaxies.md.
GALAXIES = {
    # McMillan 2017 (MNRAS 465, 76), meilleur modèle, table 3. R0 = 8,21 kpc, vitesse circulaire 233,1 km/s.
    'voie_lactee': dict(
        halo=dict(rho0=8.54e6, rs=19.6, coupure=250.0),                        # NFW 0,00854 M☉/pc³, 19,6 kpc ; coupé vers le rayon du viriel
        bulbe=dict(rho0=9.84e10, r0=0.075, puissance=1.8, coupure=2.1, q=0.5),  # 9,23e9 M☉
        disques=[
            dict(kind=1, sigma0=8.96e8, rd=2.50, hz=0.30, sigma_soleil=35.0, r_soleil=8.21),   # disque mince 3,52e10 M☉
            dict(kind=4, sigma0=1.83e8, rd=3.02, hz=0.90, sigma_soleil=50.0, r_soleil=8.21),   # disque épais 1,05e10 M☉
            dict(kind=3, masse=1.22e10, rd=7.0, hz=0.085, q_min=1.5),                           # gaz (HI + H2), pris comme un disque froid
        ]),
    # Tamm et al. 2012 (A&A 546, A4), tables 2 et 4 (halo NFW) ; disque : Courteau et al. 2011 (5,3 kpc) ; bulbe : Blaña Díaz
    # et al. 2018 (3,09e10 M☉) et Courteau 2011 (rayon effectif 1,0 kpc, soit a = 0,55 kpc pour un profil de Hernquist).
    'andromede': dict(
        halo=dict(rho0=1.10e7, rs=16.5, coupure=207.0),
        bulbe=dict(masse=3.1e10, a=0.55),
        disques=[
            dict(kind=1, masse=5.6e10, rd=5.3, hz=0.6, q_min=1.5),      # hauteur : non relue [supposé]
            dict(kind=3, masse=5.6e9, rd=6.0, hz=0.15, q_min=1.5),      # gaz atomique 4,23e9 M☉ (Chemin et al. 2009) x 1,33 ; longueur [supposé]
        ]),
    # Corbelli et al. 2014 (A&A 572, A23) : étoiles 4,8e9 M☉, longueur 1,8 kpc, halo NFW 4,3e11 M☉ de concentration 9,5
    # (rayon 158,7 kpc pour H0 = 68, donc rs = 16,7 kpc et 5,08e6 M☉/kpc³ [calculé]) ; gaz : Kam et al. 2017 (1,95e9 HI) et
    # Corbelli 2014 (3,0e8 H2), x 1,33 pour l'hélium.
    'triangle': dict(
        halo=dict(rho0=5.08e6, rs=16.7, coupure=160.0),
        bulbe=None,
        disques=[
            dict(kind=1, masse=4.8e9, rd=1.8, hz=0.3, q_min=1.5),       # hauteur [supposé]
            dict(kind=3, masse=3.0e9, rd=4.0, hz=0.15, q_min=1.5),      # longueur du gaz [supposé]
        ]),
    # Masse totale 1,38e11 M☉ (Erkal et al. 2019) ; 1,7e10 M☉ dans 8,7 kpc (van der Marel & Kallivayalil 2014), ce qui fixe
    # l'échelle d'un profil de Hernquist à 16,1 kpc [calculé] ; étoiles 2,7e9 M☉ (van der Marel 2006).
    'grand_nuage': dict(
        halo=dict(hernquist=1.38e11, a=16.1, coupure=100.0),
        bulbe=None,
        disques=[dict(kind=1, masse=2.7e9, rd=1.5, hz=0.3, q_min=1.5)]),
}


def construire(nom, n_total, adoucissement=None):
    import agama
    agama.setUnits(mass=1, length=1, velocity=1)
    g = GALAXIES[nom]
    h = g['halo']
    if 'hernquist' in h:
        ph = agama.Potential(type='Spheroid', densityNorm=h['hernquist'] / (2 * math.pi * h['a'] ** 3), gamma=1, beta=4, alpha=1, scaleRadius=h['a'],
                             outerCutoffRadius=h['coupure'], cutoffStrength=4)
    else:
        ph = agama.Potential(type='Spheroid', densityNorm=h['rho0'], gamma=1, beta=3, alpha=1, scaleRadius=h['rs'], outerCutoffRadius=h['coupure'], cutoffStrength=4)
    pots, pb = [ph], None
    b = g['bulbe']
    if b:
        if 'masse' in b:
            pb = agama.Potential(type='Dehnen', gamma=1, mass=b['masse'], scaleRadius=b['a'])
        else:   # loi de puissance tronquée de McMillan 2017 (éq. 1), aplatie
            pb = agama.Potential(type='Spheroid', densityNorm=b['rho0'], gamma=0, beta=b['puissance'], alpha=1, scaleRadius=b['r0'],
                                 outerCutoffRadius=b['coupure'], cutoffStrength=2, axisRatioZ=b['q'])
        pots.append(pb)
    pds = []
    for d in g['disques']:
        if 'sigma0' not in d:
            d['sigma0'] = d['masse'] / (2 * math.pi * d['rd'] ** 2)
        d['masse'] = 2 * math.pi * d['sigma0'] * d['rd'] ** 2
        pds.append(agama.Potential(type='Disk', surfaceDensity=d['sigma0'], scaleRadius=d['rd'], scaleHeight=d['hz']))
    pot = agama.Potential(*(pots + pds))

    # Vitesse circulaire, fréquence des épicycles et densité de surface de tous les disques : pour régler et contrôler Q.
    R = np.linspace(0.2, 30, 600)
    xyz = np.column_stack([R, R * 0, R * 0])
    vc = np.sqrt(-pot.force(xyz)[:, 0] * R)
    om2 = (vc / R) ** 2
    kappa = np.sqrt(np.clip(np.gradient(om2, R) * R + 4 * om2, 1e-12, None))
    resume = dict(nom=nom, vc={f'{r:g} kpc': round(float(np.interp(r, R, vc)), 1) for r in (2, 4, 8.21, 15, 25)}, composantes=[])

    m_halo = float(ph.totalMass())
    m_bulbe = float(pb.totalMass()) if pb is not None else 0.0
    m_etoiles = sum(d['masse'] for d in g['disques']) + m_bulbe
    # Particules : PART_HALO pour la matière noire, le reste au prorata des masses. Les particules de
    # matière noire sont donc plus lourdes ; le rapport est écrit dans le résumé (à garder sous 10 : au-delà, elles
    # chauffent artificiellement le disque).
    n_halo = int(n_total * PART_HALO)
    n_reste = n_total - n_halo
    out = []
    dfh = agama.DistributionFunction(type='QuasiSpherical', potential=pot, density=ph)
    xv, m = agama.GalaxyModel(pot, dfh).sample(n_halo)
    eps_e = adoucissement or 0.1 * (36000 / max(n_reste, 1)) ** (1 / 3)      # comme calcul.py : 0,1 kpc pour 36 000 étoiles, puis N^(-1/3)
    out.append((xv, m, 4 * eps_e, 0))
    resume['composantes'].append(dict(nom='halo', masse=m_halo, particules=n_halo, masse_particule=m_halo / n_halo))
    if pb is not None:
        nb = max(1, round(n_reste * m_bulbe / m_etoiles))
        dfb = agama.DistributionFunction(type='QuasiSpherical', potential=pot, density=pb)
        xv, m = agama.GalaxyModel(pot, dfb).sample(nb)
        out.append((xv, m, eps_e, 2))
        resume['composantes'].append(dict(nom='bulbe', masse=m_bulbe, particules=nb))
    for d in g['disques']:
        nd = max(1, round(n_reste * d['masse'] / m_etoiles))
        sig = d['sigma0'] * np.exp(-R / d['rd'])
        rsig = 2 * d['rd']
        if 'sigma_soleil' in d:      # agitation mesurée au Soleil, profil exponentiel de longueur 2 Rd
            s0 = d['sigma_soleil'] * math.exp(d['r_soleil'] / rsig)
        else:                        # non mesurée : la plus petite agitation qui donne Q >= q_min entre 1 et 4 Rd [modèle]
            zone = (R > d['rd']) & (R < 4 * d['rd'])
            sig_tot = sum(x['sigma0'] * np.exp(-R / x['rd']) for x in g['disques'])
            s0 = float(np.max(d['q_min'] * 3.36 * G * sig_tot[zone] / kappa[zone] * np.exp(R[zone] / rsig)))
        sr = s0 * np.exp(-R / rsig)
        q = sr * kappa / (3.36 * G * sig)
        zone = (R > 0.5 * d['rd']) & (R < 4 * d['rd'])
        dfd = agama.DistributionFunction(type='QuasiIsothermal', potential=pot, Sigma0=d['sigma0'], Rdisk=d['rd'], Hdisk=d['hz'], sigmar0=s0, Rsigmar=rsig)
        xv, m = agama.GalaxyModel(pot, dfd).sample(nd)
        out.append((xv, m, eps_e, d['kind']))
        resume['composantes'].append(dict(nom={1: 'disque mince', 3: 'gaz (froid)', 4: 'disque épais'}[d['kind']], masse=d['masse'], particules=nd,
                                          agitation_centre=round(s0, 1), q_seul_min=round(float(q[zone].min()), 2)))
    # Q de l'ensemble des disques (étoiles et gaz ensemble, agitation moyenne pondérée par la masse) : c'est lui qui compte.
    pos = np.concatenate([o[0][:, :3] for o in out]); vel = np.concatenate([o[0][:, 3:] for o in out])
    mass = np.concatenate([o[1] for o in out])
    eps = np.concatenate([np.full(len(o[1]), o[2]) for o in out])
    kind = np.concatenate([np.full(len(o[1]), o[3], dtype=np.int8) for o in out])
    resume['masse_totale'] = float(mass.sum())
    resume['rapport_masses_particules'] = round(resume['composantes'][0]['masse_particule'] / (m_etoiles / n_reste), 1)
    resume['adoucissement_etoiles_kpc'] = round(eps_e, 4)
    return dict(pos=pos, vel=vel, m=mass, eps=eps, kind=kind), resume


def main():
    nom, n, sortie = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    p, resume = construire(nom, n)
    np.savez_compressed(sortie, meta=json.dumps(resume, ensure_ascii=False), **p)
    print(json.dumps(resume, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
