#!/usr/bin/env python3
"""Étoiles visibles de la Voie lactée posées SUR LA MASSE du calcul du Groupe local (suite de etoiles_visibles.py).

Pourquoi : dans le premier film, les étoiles visibles étaient tirées de formules (disques lisses, barre dessinée) et le
calcul les emportait dans une masse qui n'avait pas exactement cette forme ni ces vitesses. Résultat mesuré : la barre
changeait de force et le disque gonflait dans les 50 premiers millions d'années (docs/premier-film.md, défaut 3). La
règle « un objet, une histoire » demande que l'image d'aujourd'hui soit déjà un état du calcul.

Ce script reprend le fichier du contrat et remplace, pour les populations vieilles, la position et la vitesse de chaque
étoile par celles d'une particule d'étoiles de la masse à t = 0 (aujourdhui.npz de rencontre.py), décalée d'une fraction
de la distance à ses voisines pour ne pas empiler les étoiles :
- 1 disque mince : particules du disque mince ; 2 bulbe et barre : particules du disque compact central et du bulbe
  (reconnues à leur rang dans la galaxie de départ, pas à leur place d'aujourd'hui) ;
- 4 disque épais : particules du disque épais (sorte 4).
Ne changent pas : 5 étoiles jeunes (bras MESURÉS et régions HII : leurs positions sont des mesures ; rencontre.py leur
donne la vitesse de la masse voisine) et 6 halo d'étoiles. Lumières, couleurs, graines : inchangées.
La barre de la masse est calée sur la barre mesurée par rencontre.py (mode « barre »), pas ici.

Usage : python etoiles_visibles_masse.py <contrat.npz> <aujourdhui.npz> <gaia.bin[,gaia_b.bin]> <etoiles.bin> <gaia_agrege.bin> <dossier de sortie>
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')
import json, math, os, sys, time
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voie_lactee as v
import etoiles_visibles as ev

GRAINE = 20261116
RD_MINCE, S0_MINCE = 2.50, 896e6            # disque mince de la table (M☉/kpc²)
RD_COMPACT, M_COMPACT = 1.0, 9.23e9         # disque compact central de la variante « barre » (modeles_v2.py)
DECALAGE = 0.5                              # part de la distance à la 4e voisine, écart type du décalage [choix]


def centre_des_etoiles(pos, vel):
    """Centre (sphère qui se resserre) et vitesse d'ensemble des étoiles d'une galaxie."""
    c = np.median(pos, 0)
    for r in (10.0, 5.0, 2.0, 1.0):
        d = np.linalg.norm(pos - c, axis=1); c = pos[d < r].mean(0)
    d = np.linalg.norm(pos - c, axis=1)
    return c, vel[d < 1.0].mean(0)


def tirer(rng, pos, vel, n, poids=None):
    """n étoiles tirées des particules (avec remise, au prorata de poids), décalées dans le plan d'une fraction de la
    distance à la 4e voisine (et de 0,3 fois cela en hauteur) ; vitesse de la particule."""
    d4 = cKDTree(pos).query(pos, k=5, workers=-1)[0][:, 4]
    p = None if poids is None else poids / poids.sum()
    k = rng.choice(len(pos), size=n, replace=True, p=p)
    saut = rng.normal(0.0, 1.0, (n, 3)) * (DECALAGE * d4[k])[:, None] * np.array([1.0, 1.0, 0.3])
    return pos[k] + saut, vel[k]


def main():
    contrat, auj, gaia_bin, etoiles_bin, agrege, sortie = sys.argv[1:7]
    t0 = time.time()
    rng = np.random.default_rng(GRAINE)
    with np.load(contrat) as z:
        pos, vel, lum, teff, comp, graine = z['pos'].astype(np.float64), z['vel'].astype(np.float64), z['lum'].astype(np.float64), z['teff'], z['comp'], z['graine']
        meta = json.loads(str(z['meta']))
    with np.load(auj) as z:
        s = (z['gid'] == 0) & (z['kind'] != 0) & (z['kind'] != 9)
        mp, mv, mk = z['pos'][s].astype(np.float64), z['vel'][s].astype(np.float64), z['kind'][s]
    c, cv = centre_des_etoiles(mp[(mk == 1) | (mk == 2) | (mk == 4)], mv[(mk == 1) | (mk == 2) | (mk == 4)])
    mp -= c; mv -= cv      # repère de l'appli : Voie lactée à l'origine, au repos (mêmes axes que le calcul)
    print(f'{len(mp)} particules d\'étoiles de la Voie lactée à t = 0 ; sortes : ' + ', '.join(f'{k}: {int((mk == k).sum())}' for k in np.unique(mk)))

    # Barre ou disque ? On le lit dans l'ORDRE des particules, pas dans leur place d'aujourd'hui : dans la galaxie de départ
    # (modeles_v2.py) le disque mince vient avant le disque épais, le disque compact central (la masse de la barre) après,
    # et le calcul garde cet ordre. Choisir d'après le rayon d'aujourd'hui serait faux : on prendrait pour « barre » des
    # étoiles du disque de passage près du centre, qui repartent aussitôt (mesuré sur le film 2 : rayon médian de la barre
    # + 13 % en 10 Ma, du disque - 3 % en 40 Ma).
    vieux = (mk == 1) | (mk == 2)
    rang = np.arange(len(mk)); premier_epais = int(rang[mk == 4].min()) if (mk == 4).any() else len(mk)
    compact = ((mk == 1) & (rang > premier_epais)) | (mk == 2)
    mince = (mk == 1) & (rang < premier_epais)
    n1, n2, n4 = int((comp == 1).sum()), int((comp == 2).sum()), int((comp == 4).sum())
    if compact.sum() < 1000: compact = vieux      # galaxie de départ sans disque compact : toute la vieille population
    print(f'disque mince : {int(mince.sum())} particules ; disque compact et bulbe : {int(compact.sum())}')
    p2, v2 = tirer(rng, mp[compact], mv[compact], n2)
    p1, v1 = tirer(rng, mp[mince], mv[mince], n1)
    epais = mk == 4
    p4, v4 = tirer(rng, mp[epais], mv[epais], n4)
    for cc, p_, v_ in ((1, p1, v1), (2, p2, v2), (4, p4, v4)):
        pos[comp == cc] = p_; vel[comp == cc] = v_
    print(f'{n1} + {n2} + {n4} étoiles posées sur la masse ({time.time() - t0:.0f} s)')

    # Étoiles jeunes : leur place dans le plan est mesurée (bras, régions HII), mais le disque du calcul ondule de quelques
    # centaines de pc autour du plan (flambage de la barre, passage des Nuages). Leur hauteur est donc comptée à partir du
    # milieu LOCAL du disque de la masse (médiane des 1 024 particules voisines dans le plan), sinon elles oscillent autour
    # de lui et la couche jeune s'épaissit en 100 Ma (mesuré le 16/11 : 49 -> 255 pc).
    j = np.where(comp == 5)[0]
    froid = (mk == 1) | (mk == 3)
    arbre = cKDTree(mp[froid, :2]); zf = mp[froid, 2]
    milieu = np.zeros(len(j))
    for a in range(0, len(j), 100000):
        _, v_ = arbre.query(pos[j[a:a + 100000], :2], k=1024, workers=-1)
        milieu[a:a + 100000] = np.median(zf[v_], axis=1)
    pos[j, 2] += milieu
    print(f'{len(j)} étoiles jeunes remises sur le milieu du disque : décalage médian {np.median(np.abs(milieu)) * 1000:.0f} pc, au plus {np.abs(milieu).max() * 1000:.0f} pc ({time.time() - t0:.0f} s)')

    # Gaia montre déjà les étoiles mesurées près du Soleil : comme etoiles_visibles.py, chaque étoile ne garde que ce qui manque.
    D = v.data_keys(['M_GAL2ECL', 'SGRA_GAL'])
    gal2ecl = np.array(D['M_GAL2ECL']); ecl2gal = gal2ecl.T
    sgra = np.array(D['SGRA_GAL']) / np.linalg.norm(D['SGRA_GAL']); sun = -v.R0 * sgra
    x, y, zz = v.axes(v.NX, v.HX), v.axes(v.NY, v.HX), v.axes(v.NZ, v.HZ)
    cat, _ = v.lumiere_cataloguee(gaia_bin, etoiles_bin, ecl2gal, sun, x, y, zz, agrege)
    i = np.floor((pos[:, 0] + v.HX) / (2 * v.HX) * v.NX).astype(np.int64)
    j = np.floor((pos[:, 1] + v.HX) / (2 * v.HX) * v.NY).astype(np.int64)
    k = np.floor((pos[:, 2] + v.HZ) / (2 * v.HZ) * v.NZ).astype(np.int64)
    dans = (i >= 0) & (i < v.NX) & (j >= 0) & (j < v.NY) & (k >= 0) & (k < v.NZ)
    case = np.where(dans, (k * v.NY + j) * v.NX + i, 0)
    Ltr = np.bincount(case[dans], lum[dans], v.NX * v.NY * v.NZ) / (100.0 * 100.0 * 50.0)
    part = np.clip((Ltr - cat.ravel()) / np.maximum(Ltr, 1e-30), 0.0, 1.0)
    lum_vue = lum * np.where(dans & (comp != 6), part[case], 1.0)
    print(f'Gaia montre déjà {1 - lum_vue.sum() / lum.sum():.1%} de la lumière des étoiles visibles ({time.time() - t0:.0f} s)')

    meta['date'] = '2026-11-16'
    meta['jeunes_sur_le_milieu_du_disque'] = True
    meta['posees_sur_la_masse'] = [1, 2, 4]      # rencontre.py garde leurs vitesses ; les autres prennent celle de la masse voisine
    meta['masse'] = os.path.abspath(auj)
    meta['lumiere_montree_hors_Gaia'] = float(lum_vue.sum())
    os.makedirs(sortie, exist_ok=True)
    np.savez_compressed(os.path.join(sortie, 'etoiles_visibles_voie_lactee.npz'), pos=pos, vel=vel, lum=lum.astype(np.float32),
                        teff=teff, comp=comp, graine=graine, meta=json.dumps(meta, ensure_ascii=False))
    ev.ecrire_gaia(os.path.join(sortie, 'vl_etoiles.bin'), pos, vel, lum_vue, teff, sun, gal2ecl, gaia_bin.split(',')[0], aux=16 * comp.astype(np.int16))
    print(f'-> {sortie} ({time.time() - t0:.0f} s)')


if __name__ == '__main__':
    main()
