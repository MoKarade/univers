#!/usr/bin/env python3
"""Forme des Nuages de Magellan : ce que montre un film du grand calcul (format 3) ou un jeu d'étoiles visibles, mesuré
et comparé aux mesures publiées (pipeline/constantes/nuages_magellan.json).

Mesures, toutes faites vues du Soleil du film (ou du Soleil mesuré pour un jeu d'étoiles seul) :
- séparation des deux Nuages et écart de chacun à sa place mesurée ;
- Grand Nuage : plan du disque (inclinaison, ligne des nœuds, côté proche), force de la barre (m = 2) et décalage du
  point le plus dense par rapport au centre de masse du calcul ;
- Petit Nuage : profondeur le long de la ligne de visée (5e, 50e, 95e centiles, écart type robuste), côté proche sur le
  ciel, angle entre son grand axe et la ligne de visée, rotation des étoiles ;
- matière sortie des deux Nuages (gaz et étoiles), rangée en pont, courant (traîne), bras avant, d'après sa place
  dans les coordonnées du Courant magellanique (Nidever et al. 2008).

Ne lit que film.json, p_NNNNN.bin, matiere.bin et evenements.bin (disposition : pipeline/fusion/film_v3.py,
docs/format-film-v3.md) ; n'écrit rien dans le film. Processeur seulement.

Usage :
  python forme_nuages.py film <dossier du film> [--dates 0,0.1,0.5] [--etoiles <dossier des etoiles_visibles_*.npz>] [--json sortie.json] [--carte préfixe]
  python forme_nuages.py etoiles <dossier des etoiles_visibles_*.npz> [--json sortie.json]
"""
import argparse
import json
import math
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(os.path.dirname(ICI), 'constantes', 'nuages_magellan.json')
TABLE_UNIVERS = os.path.join(os.path.dirname(ICI), 'constantes', 'univers.json')
NOMS = ('voie_lactee', 'andromede', 'triangle', 'grand_nuage', 'petit_nuage')
GN, PN = 3, 4
SOLEIL_MESURE = np.array([-8.2, 0.0, 0.0])      # repère phys::galaxie (galaxie_orbites.h)

# ICRS -> galactique (Hipparcos, ESA 1997, vol. 1 § 1.5.3 ; même matrice que Gaia et astropy) : g = A_G @ icrs
A_G = np.array([[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132],
                [0.4941094278755837, -0.4448296299600112, 0.7469822444972189],
                [-0.8676661490190047, -0.1980763734312015, 0.4559837761750669]])

# Film format 3 : un enregistrement de 18 octets (positions 0,01 pc, vitesses 0,05 km/s, relatives à la galaxie d'origine)
DT_ENREG = np.dtype([('p', '<i4', 3), ('v', '<i2', 3)])
DT_MATIERE = np.dtype([('nature', 'u1'), ('sorte', 'u1'), ('galaxie', '<u2'), ('masse', '<f4')])
DT_EVENEMENT = np.dtype([('rang', '<u4'), ('nature', 'u1'), ('vide', 'u1', 3), ('date', '<f8')])
TYPE_VISIBLES, TYPE_MATIERE, TYPE_SOLEIL = 1, 2, 3

# Seuils de rangement de la matière sortie (choisis ici, pas publiés) [Supposition]
HORS_GN_KPC = 8.0       # le disque du Grand Nuage s'étend au-delà de 7 kpc (Choi et al. 2018) : en deçà, c'est le disque
HORS_PN_KPC = 4.0       # l'aile du Petit Nuage, où commence le pont, est vers 3 à 4 kpc de son centre
PONT_LARGEUR_KPC = 7.0  # distance au segment Petit Nuage -> Grand Nuage
COURANT_L_DEG = -25.0   # traîne : longitude L_MS sous -25° (au-delà du Petit Nuage, à -15,5°)
BRAS_AVANT_L_DEG = 10.0


# ---------------------------------------------------------------------------------------------------- géométrie du ciel
def unitaire(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def direction_lb(l_deg, b_deg):
    l, b = np.radians(l_deg), np.radians(b_deg)
    return np.stack([np.cos(b) * np.cos(l), np.cos(b) * np.sin(l), np.sin(b)], axis=-1)


def lb_de(d):
    d = unitaire(d)
    return np.degrees(np.arctan2(d[..., 1], d[..., 0])) % 360.0, np.degrees(np.arcsin(np.clip(d[..., 2], -1, 1)))


def axes_courant(table=None):
    """Axes du repère du Courant magellanique (Nidever et al. 2008) en galactique : (zéro, 90°, pôle)."""
    r = (table or json.load(open(TABLE, encoding='utf-8')))['repere_courant']
    pole = direction_lb(*r['pole_galactique_deg'])
    zero = direction_lb(*r['zero_galactique_deg'])
    x = unitaire(zero - np.dot(zero, pole) * pole)
    return x, np.cross(pole, x), pole


def vers_courant(d_gal, axes):
    """Directions galactiques (n, 3) -> (L_MS, B_MS) en degrés, L_MS dans [-180, 180)."""
    x, y, z = axes
    d = unitaire(d_gal)
    L = np.degrees(np.arctan2(d @ y, d @ x))
    B = np.degrees(np.arcsin(np.clip(d @ z, -1, 1)))
    return (L + 180.0) % 360.0 - 180.0, B


def ciel_local(u0_gal):
    """Est et nord sur le ciel à la direction u0 (galactique), pour les angles de position comptés du nord vers l'est."""
    pole_nord_eq = A_G @ np.array([0.0, 0.0, 1.0])       # pôle nord céleste en galactique
    u0 = unitaire(u0_gal)
    est = unitaire(np.cross(pole_nord_eq, u0))
    return est, np.cross(u0, est)


def angle_position(v, est, nord):
    return math.degrees(math.atan2(float(np.dot(v, est)), float(np.dot(v, nord)))) % 360.0


# ---------------------------------------------------------------------------------------------------- mesures de forme
def profondeur(pos, centre, soleil):
    """Décalage le long de la ligne de visée (kpc, positif = plus loin) : centiles 5/50/95 et écart type robuste."""
    u0 = unitaire(centre - soleil)
    los = (pos - soleil) @ u0 - np.linalg.norm(centre - soleil)
    p5, p50, p95 = np.percentile(los, [5, 50, 95])
    q25, q75 = np.percentile(los, [25, 75])
    return dict(p5=float(p5), p50=float(p50), p95=float(p95), sigma_robuste=float((q75 - q25) / 1.349)), los


def cote_proche(pos, los, centre, soleil):
    """Angle de position (degrés, du nord vers l'est) du côté du ciel le plus proche de nous : plan los = a·ξ + b·η + c."""
    u0 = unitaire(centre - soleil)
    est, nord = ciel_local(u0)
    rel = pos - centre
    A = np.column_stack([rel @ est, rel @ nord, np.ones(len(rel))])
    a, b, _ = np.linalg.lstsq(A, los, rcond=None)[0]
    pente = math.hypot(a, b)
    return dict(angle_deg=math.degrees(math.atan2(-a, -b)) % 360.0, pente_kpc_par_kpc=float(pente))


def plan_disque(pos, centre, soleil, poids=None):
    """Plan moyen d'un nuage de points : normale (plus petit axe), inclinaison sur le ciel, ligne des nœuds (0-180°),
    côté proche (angle de position) ; rapports des axes."""
    rel = pos - centre
    w = np.ones(len(rel)) if poids is None else np.asarray(poids, float)
    cov = (rel * w[:, None]).T @ rel / w.sum()
    val, vec = np.linalg.eigh(cov)
    n = vec[:, 0]
    u0 = unitaire(centre - soleil)
    est, nord = ciel_local(u0)
    inc = math.degrees(math.acos(min(1.0, abs(float(np.dot(n, u0))))))
    noeuds = np.cross(n, u0)
    pa_noeuds = angle_position(noeuds, est, nord) % 180.0
    s = unitaire(np.cross(u0, noeuds))          # direction du ciel perpendiculaire aux nœuds
    # point du disque au-dessus de s : profondeur z = -a (n·s)/(n·u0) ; côté proche = signe donnant z < 0
    proche = s if float(np.dot(n, s)) / float(np.dot(n, u0)) > 0 else -s
    ax = np.sqrt(np.maximum(val, 0))
    return dict(inclinaison_deg=inc, ligne_des_noeuds_deg=pa_noeuds, cote_proche_deg=angle_position(proche, est, nord),
                axes_kpc=[float(x) for x in ax[::-1]], normale=n.tolist())


def barre(pos, centre, normale, rmin=0.5, rmax=2.5):
    """Force de la barre A2 = |Σ e^{2iφ}| / N entre rmin et rmax dans le plan, et décalage (kpc) du point le plus dense
    (sphère qui rétrécit, dans le plan) par rapport au centre donné."""
    n = unitaire(normale)
    e1 = unitaire(np.cross(n, [0.0, 0.0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0.0, 0.0]))
    e2 = np.cross(n, e1)
    rel = pos - centre
    x, y = rel @ e1, rel @ e2
    R = np.hypot(x, y)
    sel = (R > rmin) & (R < rmax)
    phi = np.arctan2(y[sel], x[sel])
    a2 = float(abs(np.exp(2j * phi).sum()) / max(sel.sum(), 1))
    # point le plus dense : sphère qui rétrécit (Power et al. 2003, MNRAS 338, 14), dans le plan, à partir de 3 kpc
    cx, cy, rayon = 0.0, 0.0, 3.0
    while True:
        dedans = np.hypot(x - cx, y - cy) < rayon
        if dedans.sum() < 1000 or rayon < 0.2:
            break
        cx, cy, rayon = float(x[dedans].mean()), float(y[dedans].mean()), rayon * 0.9
    return dict(a2=a2, angle_barre_deg=float(np.degrees(np.angle(np.exp(2j * phi).sum()) / 2) % 180.0),
                decalage_point_dense_kpc=float(math.hypot(cx, cy)))


def grand_axe(pos, centre, soleil):
    """Angle (degrés) entre le grand axe d'un nuage de points et la ligne de visée ; rapports des axes."""
    rel = pos - centre
    q = np.percentile(np.linalg.norm(rel, axis=1), 95)
    rel = rel[np.linalg.norm(rel, axis=1) < q]
    val, vec = np.linalg.eigh(rel.T @ rel / len(rel))
    u0 = unitaire(centre - soleil)
    ax = np.sqrt(np.maximum(val, 0))[::-1]
    return dict(angle_ligne_de_visee_deg=math.degrees(math.acos(min(1.0, abs(float(vec[:, 2] @ u0))))),
                axes_kpc=[float(x) for x in ax])


def rotation(pos, vel, centre, vcentre, axe, rmin=1.0, rmax=3.0):
    """Vitesse moyenne autour de l'axe (km/s, positive dans le sens de l'axe) entre rmin et rmax, et agitation."""
    a = unitaire(axe)
    rel, v = pos - centre, vel - vcentre
    rp = rel - np.outer(rel @ a, a)
    R = np.linalg.norm(rp, axis=1)
    sel = (R > rmin) & (R < rmax)
    if not sel.any():
        return dict(v_rotation_kms=None, agitation_kms=None, n=0)
    t = np.cross(a[None], rp[sel]) / R[sel, None]
    vt = np.einsum('ij,ij->i', v[sel], t)
    return dict(v_rotation_kms=float(np.median(vt)), agitation_kms=float(np.std(v[sel] - np.outer(vt, np.ones(3)) * t)), n=int(sel.sum()))


def ranger_hors(pos, masse, cGN, cPN, soleil, axes):
    """Matière sortie des deux Nuages, rangée par région ; rend les masses (ou effectifs si masse = 1) par région."""
    dG, dP = np.linalg.norm(pos - cGN, axis=1), np.linalg.norm(pos - cPN, axis=1)
    hors = (dG > HORS_GN_KPC) & (dP > HORS_PN_KPC)
    seg = cGN - cPN
    s = np.clip((pos - cPN) @ seg / (seg @ seg), 0, 1)
    perp = np.linalg.norm(pos - (cPN + s[:, None] * seg), axis=1)
    L, _ = vers_courant(pos - soleil, axes)
    pont = hors & (perp < PONT_LARGEUR_KPC) & (s > 0) & (s < 1)
    courant = hors & ~pont & (L < COURANT_L_DEG)
    avant = hors & ~pont & (L > BRAS_AVANT_L_DEG)
    autre = hors & ~pont & ~courant & ~avant
    tot = float(masse.sum())
    out = {k: float(masse[m].sum()) for k, m in (('pont', pont), ('courant', courant), ('bras_avant', avant), ('autre', autre))}
    out['total_hors'] = float(masse[hors].sum())
    out['part_hors'] = out['total_hors'] / tot if tot else 0.0
    out['courant_L_min_deg'] = float(L[courant].min()) if courant.any() else None
    return out


# ---------------------------------------------------------------------------------------------------- lecture
class Film:
    """Lecteur minimal du format 3 (positions absolues, repère phys::galaxie)."""

    def __init__(self, dossier):
        self.dossier = dossier
        self.meta = json.load(open(os.path.join(dossier, 'film.json'), encoding='utf-8'))
        self.t = np.array([d['t'] for d in self.meta['dates']])
        self.p = [k for k, d in enumerate(self.meta['dates']) if d['familles'] & 1]
        mat = os.path.join(dossier, 'matiere.bin')
        self.matiere = np.fromfile(mat, DT_MATIERE) if os.path.exists(mat) else None
        ev = os.path.join(dossier, 'evenements.bin')
        self.evenements = np.fromfile(ev, DT_EVENEMENT) if os.path.exists(ev) else np.zeros(0, DT_EVENEMENT)

    def bloc(self, type_, galaxie=None):
        for b in self.meta['blocs']:
            if b['famille'] == 0 and b['type'] == type_ and (galaxie is None or b['galaxie'] == galaxie):
                return slice(b['premier'], b['premier'] + b['nombre'])
        return slice(0, 0)

    def image_proche(self, t):
        return min(self.p, key=lambda k: abs(self.t[k] - t))

    def lire(self, k):
        e = np.memmap(os.path.join(self.dossier, f'p_{k:05d}.bin'), DT_ENREG, mode='r')
        d = self.meta['dates'][k]
        C, Vc = np.array(d['centres']), np.array(d['vitesses'])
        out = dict(t=float(self.t[k]), centres=C, vitesses=Vc)
        sol = self.bloc(TYPE_SOLEIL)
        out['soleil'] = e['p'][sol][0].astype(float) * 1e-5 + C[0] if sol.stop > sol.start else SOLEIL_MESURE
        for g in (GN, PN):
            s = self.bloc(TYPE_VISIBLES, g)
            out[f'etoiles_{g}'] = (e['p'][s].astype(float) * 1e-5 + C[g], e['v'][s].astype(float) * 0.05 + Vc[g])
            if self.matiere is not None:
                sm, m0 = self.bloc(TYPE_MATIERE, g), self.bloc(TYPE_MATIERE).start
                nat = self.nature(self.t[k])[sm.start - m0:sm.stop - m0]
                out[f'gaz_{g}'] = (e['p'][sm].astype(float) * 1e-5 + C[g], self.matiere['masse'][sm.start - m0:sm.stop - m0].astype(float), nat == 0)
        return out

    def nature(self, t):
        nat = self.matiere['nature'].copy()
        ev = self.evenements[self.evenements['date'] <= t + 1e-9]
        nat[ev['rang']] = ev['nature']        # trié par date : la dernière nature l'emporte
        return nat


def lire_etoiles(dossier):
    """Jeu d'étoiles visibles seul (aujourd'hui) : centres et vitesses mesurés (meta), Soleil mesuré."""
    out = dict(t=0.0, soleil=SOLEIL_MESURE, centres=np.zeros((5, 3)), vitesses=np.zeros((5, 3)), comp={})
    for g, nom in ((GN, 'grand_nuage'), (PN, 'petit_nuage')):
        z = np.load(os.path.join(dossier, f'etoiles_visibles_{nom}.npz'))
        m = json.loads(str(z['meta']))
        out['centres'][g], out['vitesses'][g] = m['centre_kpc'], m['vitesse_kms']
        out[f'etoiles_{g}'] = (z['pos'], z['vel'])
        out['comp'][g] = z['comp']
    return out


def places_mesurees():
    t = json.load(open(TABLE_UNIVERS, encoding='utf-8'))['galaxies']
    return {GN: np.array(t['grand_nuage']['aujourdhui']['position']), PN: np.array(t['petit_nuage']['aujourdhui']['position'])}


# ---------------------------------------------------------------------------------------------------- bilan
def mesurer(etat, comp=None):
    """Toutes les mesures d'un état (dict de Film.lire ou lire_etoiles). comp : {galaxie: composantes} pour isoler les
    vieilles étoiles (1, 2, 4, 6) des jeunes (5)."""
    ref = json.load(open(TABLE, encoding='utf-8'))
    axes = axes_courant(ref)
    sol, C, V = etat['soleil'], etat['centres'], etat['vitesses']
    comp = comp or etat.get('comp') or {}
    mes = places_mesurees()
    r = dict(t_ga=etat['t'], separation_kpc=float(np.linalg.norm(C[GN] - C[PN])),
             separation_mesuree_kpc=float(np.linalg.norm(mes[GN] - mes[PN])),
             ecart_place_kpc={'grand_nuage': float(np.linalg.norm(C[GN] - mes[GN])), 'petit_nuage': float(np.linalg.norm(C[PN] - mes[PN]))})
    for g in (GN, PN):
        L, B = vers_courant((C[g] - sol)[None], axes)
        r.setdefault('place_courant_deg', {})[NOMS[g]] = [float(L[0]), float(B[0])]
    # Grand Nuage
    pG, vG = etat[f'etoiles_{GN}']
    proche = np.linalg.norm(pG - C[GN], axis=1) < 6.0
    plan = plan_disque(pG[proche], C[GN], sol)
    r['grand_nuage'] = dict(plan=plan, barre=barre(pG, C[GN], np.array(plan['normale'])), profondeur=profondeur(pG, C[GN], sol)[0])
    # Petit Nuage : toutes les étoiles visibles, puis les vieilles seules si les composantes sont connues
    pP, vP = etat[f'etoiles_{PN}']
    prof, los = profondeur(pP, C[PN], sol)
    axe_pn = unitaire(np.array(json.load(open(TABLE_UNIVERS, encoding='utf-8'))['galaxies']['petit_nuage'].get('axe_rotation') or [0.388, -0.602, -0.698]))
    r['petit_nuage'] = dict(profondeur=prof, cote_proche=cote_proche(pP, los, C[PN], sol), forme=grand_axe(pP, C[PN], sol),
                            rotation=rotation(pP, vP, C[PN], V[PN], axe_pn))
    if PN in comp:
        vieilles = np.isin(comp[PN], (1, 2, 4, 6))
        pv, lv = profondeur(pP[vieilles], C[PN], sol)
        r['petit_nuage']['vieilles'] = dict(profondeur=pv, cote_proche=cote_proche(pP[vieilles], lv, C[PN], sol),
                                            rotation=rotation(pP[vieilles], vP[vieilles], C[PN], V[PN], axe_pn), n=int(vieilles.sum()))
    # matière sortie
    for g in (GN, PN):
        p = etat[f'etoiles_{g}'][0]
        r.setdefault('etoiles_hors', {})[NOMS[g]] = ranger_hors(p, np.ones(len(p)), C[GN], C[PN], sol, axes)
        if f'gaz_{g}' in etat:
            pg, mg, gaz = etat[f'gaz_{g}']
            r.setdefault('gaz_hors', {})[NOMS[g]] = ranger_hors(pg[gaz], mg[gaz], C[GN], C[PN], sol, axes)
            r.setdefault('gaz_total_msol', {})[NOMS[g]] = float(mg[gaz].sum())
    return r


def carte(etat, chemin, largeur=1200):
    """Carte du ciel en coordonnées du Courant (L_MS de -180 à +60°, B_MS de -45 à +45°), vue du Soleil de l'état :
    gaz des deux Nuages en bleu, étoiles visibles en jaune. Aucune image mesurée n'y est collée : seules les places des
    deux Nuages mesurées (croix blanches) viennent de l'observation."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        police = ImageFont.truetype('arial.ttf', 14)      # accents ; police par défaut sinon
    except OSError:
        police = ImageFont.load_default()
    axes = axes_courant()
    h = largeur * 90 // 240
    acc = np.zeros((h, largeur, 3))

    def poser(pos, poids, couleur):
        L, B = vers_courant(pos - etat['soleil'], axes)
        x = ((L + 180.0) / 240.0 * largeur).astype(int)
        y = ((45.0 - B) / 90.0 * h).astype(int)
        ok = (x >= 0) & (x < largeur) & (y >= 0) & (y < h)
        for c in range(3):
            np.add.at(acc[..., c], (y[ok], x[ok]), poids[ok] * couleur[c])
    for g in (GN, PN):
        if f'gaz_{g}' in etat:
            p, m, gaz = etat[f'gaz_{g}']
            poser(p[gaz], m[gaz] / 1e5, (0.35, 0.6, 1.0))
        poser(etat[f'etoiles_{g}'][0], np.full(len(etat[f'etoiles_{g}'][0]), 0.05), (1.0, 0.85, 0.45))
    img = np.clip(np.log1p(acc) / np.log1p(np.percentile(acc[acc > 0], 99.5)), 0, 1) if (acc > 0).any() else acc
    im = Image.fromarray((img * 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    ref = json.load(open(TABLE, encoding='utf-8'))['repere_courant']['controle']
    for L, B in ref.values():
        x, y = (L + 180.0) / 240.0 * largeur, (45.0 - B) / 90.0 * h
        d.line([x - 6, y, x + 6, y], fill=(255, 255, 255)); d.line([x, y - 6, x, y + 6], fill=(255, 255, 255))
    for L in range(-180, 61, 30):
        x = (L + 180.0) / 240.0 * largeur
        d.line([x, h - 8, x, h], fill=(120, 120, 120)); d.text((x + 2, h - 22), f'{L}°', fill=(160, 160, 160), font=police)
    d.text((8, 6), f"t = {etat['t']:.2f} Ga ; L_MS (Nidever 2008) ; bleu : gaz du calcul ; jaune : étoiles ; croix : places mesurées", fill=(200, 200, 200), font=police)
    im.save(chemin)


def juger(r):
    """Comparaison aux mesures publiées : liste de (quoi, valeur du calcul, mesure, verdict)."""
    ref = json.load(open(TABLE, encoding='utf-8'))
    g, p = ref['grand_nuage'], ref['petit_nuage']
    out = []

    avenir = r['t_ga'] > 1e-3      # les mesures valent pour aujourd'hui, vues de la Terre : rien à comparer dans l'avenir

    def ligne(quoi, val, mesure, ok):
        verdict = 'avenir : pas de mesure' if avenir else ('conforme' if ok else 'ÉCART')
        out.append(dict(quoi=quoi, calcul=val, mesure=mesure, verdict=verdict))

    pl = r['grand_nuage']['plan']
    fi, fn = g['disque']['fourchette_inclinaison_deg'], g['disque']['fourchette_noeuds_deg']
    ligne('Grand Nuage : inclinaison du disque (°)', round(pl['inclinaison_deg'], 1), f'{fi[0]:.0f} à {fi[1]:.0f}', fi[0] <= pl['inclinaison_deg'] <= fi[1])
    ligne('Grand Nuage : ligne des nœuds (°)', round(pl['ligne_des_noeuds_deg'], 1), f'{fn[0]:.0f} à {fn[1]:.0f}', fn[0] <= pl['ligne_des_noeuds_deg'] <= fn[1])
    dcp = abs((pl['cote_proche_deg'] - g['disque']['cote_proche']['angle_deg'] + 180) % 360 - 180)
    ligne('Grand Nuage : côté proche (angle de position, °)', round(pl['cote_proche_deg']), 'nord-est (≈ 49)', dcp < 45)
    dec = r['grand_nuage']['barre']['decalage_point_dense_kpc']
    ligne('Grand Nuage : point le plus dense / centre de masse (kpc)', round(dec, 2), '0,4 (centre du disque) à plus de 1 (centre du gaz)', 0.2 <= dec <= 1.6)
    ligne('Grand Nuage : barre (A2, 0,5-2,5 kpc)', round(r['grand_nuage']['barre']['a2'], 3), 'barre nette (pas de valeur A2 publiée relue)', r['grand_nuage']['barre']['a2'] > 0.1)
    pp = r['petit_nuage'].get('vieilles', r['petit_nuage'])
    sig = pp['profondeur']['sigma_robuste']
    h = p['profondeur']['hauteur_rr_lyrae_kpc']
    ligne('Petit Nuage : profondeur des vieilles étoiles (écart type, kpc)', round(sig, 2), f"{h['valeur']} ± {h['err']} (RR Lyrae)", abs(sig - h['valeur']) <= 2 * h['err'] + 0.3)
    e = pp['profondeur']['p95'] - pp['profondeur']['p5']
    ligne('Petit Nuage : étendue le long de la visée, 5e-95e centile (kpc)', round(e, 1), 'étendue totale 25 à 30 (céphéides) ; au moins 6 ici', e >= 6.0)
    ca = pp['cote_proche']['angle_deg']
    ligne('Petit Nuage : côté proche (angle de position, °)', round(ca), 'est (≈ 90)', abs((ca - 90 + 180) % 360 - 180) < 60)
    sep = r['separation_kpc']
    ligne('Distance entre les deux Nuages (kpc)', round(sep, 1), round(r['separation_mesuree_kpc'], 1), abs(sep - r['separation_mesuree_kpc']) < 3)
    if 'gaz_hors' in r:
        gh = ref['gaz_hors_des_nuages']
        tot = gh['hi_total_msol_a_55kpc']['valeur'] * gh['helium']['facteur']
        for k, part in (('pont', 'pont_et_interface'), ('courant', 'courant'), ('bras_avant', 'bras_avant')):
            val = sum(x[k] for x in r['gaz_hors'].values())
            m = tot * gh['parts'][part]
            ligne(f'Gaz sorti des Nuages : {k.replace("_", " ")} (M☉, mesure à 55 kpc)', f'{val:.2e}', f'{m:.2e}', 0.3 * m <= val <= 3 * m)
    return out


def tableau(lignes):
    larg = max(len(x['quoi']) for x in lignes)
    return '\n'.join(f"{x['quoi']:<{larg}}  {str(x['calcul']):>10}  {x['mesure']:<40} {x['verdict']}" for x in lignes)


def main(argv=None):
    sys.stdout.reconfigure(encoding='utf-8')
    a = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    a.add_argument('mode', choices=('film', 'etoiles'))
    a.add_argument('dossier')
    a.add_argument('--dates', default='0')
    a.add_argument('--etoiles', default='')
    a.add_argument('--json', default='')
    a.add_argument('--carte', default='', help='préfixe des cartes du ciel PNG (une par date)')
    o = a.parse_args(argv)
    sortie = []
    if o.mode == 'etoiles':
        e = lire_etoiles(o.dossier)
        r = mesurer(e)
        if o.carte:
            carte(e, f'{o.carte}_aujourdhui.png')
        r['juge'] = juger(r)
        print(f"Étoiles visibles seules ({o.dossier})\n" + tableau(r['juge']))
        sortie.append(r)
    else:
        f = Film(o.dossier)
        comp = {}
        if o.etoiles:
            comp = {g: np.load(os.path.join(o.etoiles, f'etoiles_visibles_{NOMS[g]}.npz'))['comp'] for g in (GN, PN)}
        for t in (float(x) for x in o.dates.split(',')):
            k = f.image_proche(t)
            etat = f.lire(k)
            r = mesurer(etat, comp)
            if o.carte:
                carte(etat, f'{o.carte}_{r["t_ga"]:.2f}Ga.png')
            r['juge'] = juger(r)
            print(f"\nFilm {o.dossier}, image {k}, t = {r['t_ga']:.3f} Ga\n" + tableau(r['juge']))
            sortie.append(r)
    if o.json:
        json.dump(sortie, open(o.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
