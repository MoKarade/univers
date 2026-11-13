#!/usr/bin/env python3
"""Construit la table unique (étape 0 du plan B+) à partir de table_source.py.

Écrit :
- pipeline/constantes/univers.json        (lu par constantes.py)
- natif/physique/constantes_univers.h      (lu par l'appli ; pas encore branché, voir docs/table-unique.md)

Calcule ici, et le dit dans le fichier (« calculé ») :
- la masse de chaque composante des modèles (intégrale de la densité, coupures comprises) ;
- le centre de la loi de masse de l'ensemble Monte-Carlo (= masse du modèle, pour que le film soit un tirage) ;
- la position et la vitesse d'aujourd'hui de chaque galaxie dans le repère phys::galaxie (astropy, repère galactique) ;
- l'axe de rotation de chaque disque (inclinaison, angle de position, sens vu de la Terre, côté proche ou bout en approche),
  avec un contrôle : le bout du grand axe annoncé en approche l'est bien.

Usage : python pipeline/constantes/construire.py   (aucun argument ; besoin de numpy et astropy)
"""
import json
import math
import os
import sys

import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord, Distance

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import table_source as T      # noqa: E402

RACINE = os.path.dirname(os.path.dirname(ICI))
SORTIE_JSON = os.path.join(ICI, 'univers.json')
SORTIE_H = os.path.join(RACINE, 'natif', 'physique', 'constantes_univers.h')
G = 4.30091e-6


# ------------------------------------------------------------------ masses des modèles
def _integrale_spherique(rho, rmax):
    r = np.logspace(-4, math.log10(rmax), 20000)
    return float(np.trapezoid(4 * math.pi * r * r * rho(r), r))


def masses_modele(m):
    out = {}
    h = m['halo']
    if 'hernquist' in h:
        a, M, rc = h['a'], h['hernquist'], h['coupure']
        rho0 = M / (2 * math.pi * a ** 3)
        out['halo'] = _integrale_spherique(lambda r: rho0 / ((r / a) * (1 + r / a) ** 3) * np.exp(-(r / rc) ** 4), 20 * rc)
    else:
        rho0, rs, rc = h['rho0'], h['rs'], h['coupure']
        out['halo'] = _integrale_spherique(lambda r: rho0 / ((r / rs) * (1 + r / rs) ** 2) * np.exp(-(r / rc) ** 4), 20 * rc)
    b = m.get('bulbe')
    if b:
        if 'masse' in b:
            out['bulbe'] = b['masse']
        else:      # loi de puissance tronquée de McMillan 2017, aplatie q (volume × q)
            out['bulbe'] = b['q'] * _integrale_spherique(lambda r: b['rho0'] / (1 + r / b['r0']) ** b['puissance'] * np.exp(-(r / b['coupure']) ** 2), 20 * b['coupure'])
    for k, d in enumerate(m['disques']):
        nom = {1: 'disque', 3: 'gaz', 4: 'disque_epais'}[d['kind']]
        if nom in out: nom += str(k)
        out[nom] = d['masse'] if 'masse' in d else 2 * math.pi * d['sigma0'] * d['rd'] ** 2
    out['total'] = sum(out.values())
    return out


# ------------------------------------------------------------------ géométrie du ciel
def matrice_icrs_vers_galactique():
    e = np.eye(3)
    c = SkyCoord(x=e[0], y=e[1], z=e[2], unit='kpc', representation_type='cartesian', frame='icrs').galactic
    return c.cartesian.xyz.value      # colonne k = image de e_k


def base_ciel(ra, dec):
    a, d = math.radians(ra), math.radians(dec)
    er = np.array([math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d)])
    ee = np.array([-math.sin(a), math.cos(a), 0.0])
    en = np.array([-math.sin(d) * math.cos(a), -math.sin(d) * math.sin(a), math.cos(d)])
    return er, ee, en


def axe_rotation(obs, disque, M):
    """Axe du moment cinétique (unitaire, repère galactique) et côté proche retenu (angle de position, degrés)."""
    er, ee, en = base_ciel(obs['ra'], obs['dec'])
    sur_ciel = lambda pa: math.sin(math.radians(pa)) * ee + math.cos(math.radians(pa)) * en
    i, th = math.radians(disque['inclinaison']), disque['pa_noeuds']
    signe = 1.0 if disque['sens_vu_terre'] == 'horaire' else -1.0      # horaire vu de la Terre : L s'éloigne de nous
    def L_pour(proche): return signe * (math.sin(i) * sur_ciel(proche) + math.cos(i) * er)
    def vitesse_visee(L, pa): return float(np.dot(np.cross(L, sur_ciel(pa)), er))      # > 0 : en éloignement
    if disque.get('cote_proche_pa') is not None:
        proche = disque['cote_proche_pa']
    else:      # côté proche déduit du sens et du bout du grand axe qui s'approche
        cand = [th + 90, th - 90]
        ok = [p for p in cand if vitesse_visee(L_pour(p), disque['bout_approche_pa']) < 0]
        assert len(ok) == 1, 'côté proche indéterminé'
        proche = ok[0] % 360
    L = L_pour(proche)
    if disque.get('bout_approche_pa') is not None:
        assert vitesse_visee(L, disque['bout_approche_pa']) < 0, 'contrôle du bout en approche : échec'
    return M @ L, proche


def etat_aujourdhui(obs, rep, M):
    c = SkyCoord(ra=obs['ra'] * u.deg, dec=obs['dec'] * u.deg, distance=Distance(distmod=obs['dmod'] * u.mag),
                 pm_ra_cosdec=obs['pmra'] * u.uas / u.yr, pm_dec=obs['pmdec'] * u.uas / u.yr, radial_velocity=obs['vr'] * u.km / u.s,
                 frame='icrs').galactic
    x = c.cartesian.xyz.to_value(u.kpc)
    v = c.velocity.d_xyz.to_value(u.km / u.s)
    soleil_x = -rep['R0'] * np.array(rep['sgra'])
    soleil_v = np.array(rep['soleil_particulier']) + np.array([0.0, rep['v0'], 0.0])
    return soleil_x + x, soleil_v + v, float(np.linalg.norm(x))


# ------------------------------------------------------------------ assemblage
def construire():
    rep = dict(T.REPERE)
    rep['soleil_position'] = (-rep['R0'] * np.array(rep['sgra'])).round(6).tolist()
    rep['soleil_vitesse'] = (np.array(rep['soleil_particulier']) + [0, rep['v0'], 0]).round(4).tolist()
    M = matrice_icrs_vers_galactique()
    gal = {}
    for cle in T.ORDRE:
        g = json.loads(json.dumps(T.GALAXIES[cle]))
        if g.get('modele'):
            g['masses_modele'] = {k: float('%.4g' % v) for k, v in masses_modele(g['modele']).items()}
            g['masses_modele']['statut'] = 'calculé (intégrale des densités du modèle, coupures comprises)'
        lm = g['loi_masse']
        if lm['centre'] is None:
            lm['centre'] = float('%.4g' % g['masses_modele']['total'])
            lm['centre_statut'] = 'calculé : masse totale du modèle'
        if 'observe' in g:
            x, v, d = etat_aujourdhui(g['observe'], rep, M)
            g['aujourdhui'] = dict(position=x.round(4).tolist(), vitesse=v.round(3).tolist(), distance_soleil=round(d, 3),
                                   statut='calculé depuis « observe » (astropy, repère galactique, Soleil de « repere »)')
        else:      # la Voie lactée : origine du repère, au repos par définition (son mouvement autour du centre de masse vient des calculs)
            g['aujourdhui'] = dict(position=[0.0, 0.0, 0.0], vitesse=[0.0, 0.0, 0.0], statut='origine du repère')
        if g.get('disque'):
            L, proche = axe_rotation(g['observe'], g['disque'], M)
            g['disque']['axe_rotation'] = (L / np.linalg.norm(L)).round(4).tolist()
            g['disque']['cote_proche_retenu_pa'] = round(proche, 1)
            g['disque']['axe_statut'] = 'calculé (inclinaison, angle de position, sens, côté proche) ; repère phys::galaxie'
        gal[cle] = g
    # Voie lactée : axe de rotation. Rotation dans le sens des φ décroissants (galaxie_orbites.h), soit L vers −z (pôle sud galactique).
    gal['voie_lactee']['disque'] = dict(axe_rotation=[0.0, 0.0, -1.0], src='la Voie lactée tourne vers l = 90° au Soleil : moment cinétique vers le pôle sud galactique')
    cos = dict(T.COSMOLOGIE)
    cos['K_lambda'] = float('%.6g' % ((cos['H0'] / 1000.0) ** 2 * cos['omega_lambda']))
    cos['K_lambda_unite'] = '(km/s)² / kpc² : a_Λ = K_lambda × (x − x_cm)'
    return dict(version=1, date='2026-11-13', genere_par='pipeline/constantes/construire.py depuis table_source.py — ne pas éditer',
                unites='kpc, km/s, M☉, Ga ; mouvements propres en µas/an ; angles en degrés',
                repere=rep, cosmologie=cos, ordre=T.ORDRE, galaxies=gal, ensemble=T.ENSEMBLE)


def entete_cpp(t):
    L = ['// GÉNÉRÉ par pipeline/constantes/construire.py depuis pipeline/constantes/table_source.py : ne pas éditer.',
         '// Table unique des constantes (étape 0 du plan B+, docs/refonte-simulations-pro.md ; sources dans univers.json).',
         '// Pas encore branché dans l\'appli : galaxie_orbites.h garde kR0 et kV0 (voir docs/table-unique.md).',
         '#pragma once', '', 'namespace univers::constantes {', '']
    r = t['repere']
    f = lambda v: repr(float(v))
    L += [f'constexpr double kR0 = {f(r["R0"])};', f'constexpr double kV0 = {f(r["v0"])};',
          'constexpr double kSgra[3] = {' + ', '.join(f(x) for x in r['sgra']) + '};',
          'constexpr double kSoleilPos[3] = {' + ', '.join(f(x) for x in r['soleil_position']) + '};',
          'constexpr double kSoleilVit[3] = {' + ', '.join(f(x) for x in r['soleil_vitesse']) + '};', '']
    c = t['cosmologie']
    L += [f'constexpr double kH0 = {f(c["H0"])};', f'constexpr double kOmegaM = {f(c["omega_m"])};',
          f'constexpr double kOmegaLambda = {f(c["omega_lambda"])};', f'constexpr double kKLambda = {f(c["K_lambda"])};      // (km/s)²/kpc²', '']
    L += ['struct Galaxie {', '    const char* cle;', '    double masse;            // M☉, centre de la loi de masse (= masse du modèle quand il existe)',
          '    double masseSigma;', '    double pos[3], vit[3];   // aujourd\'hui, repère phys::galaxie (kpc, km/s)',
          '    double axe[3];           // moment cinétique du disque (unitaire) ; 0 si inconnu', '};', '',
          f'constexpr int kNbGalaxies = {len(t["ordre"])};', 'constexpr Galaxie kGalaxies[kNbGalaxies] = {']
    for k in t['ordre']:
        g = t['galaxies'][k]
        ax = (g.get('disque') or {}).get('axe_rotation', [0, 0, 0])
        vec = lambda a: '{' + ', '.join(f(x) for x in a) + '}'
        L.append(f'    {{"{k}", {f(g["loi_masse"]["centre"])}, {f(g["loi_masse"]["sigma"])}, {vec(g["aujourdhui"]["position"])}, '
                 f'{vec(g["aujourdhui"]["vitesse"])}, {vec(ax)}}},')
    L += ['};', '', '}  // namespace univers::constantes', '']
    return '\n'.join(L)


def main():
    t = construire()
    with open(SORTIE_JSON, 'w', encoding='utf-8') as fh:
        json.dump(t, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    with open(SORTIE_H, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(entete_cpp(t))
    for k in t['ordre']:
        g = t['galaxies'][k]
        a = g['aujourdhui']
        print(f"{k:12s} masse {g['loi_masse']['centre']:.3g} ± {g['loi_masse']['sigma']:.2g}  pos {a['position']}  vit {a['vitesse']}  "
              f"axe {(g.get('disque') or {}).get('axe_rotation')}")


if __name__ == '__main__':
    main()
