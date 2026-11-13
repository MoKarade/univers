#!/usr/bin/env python3
"""Cases de lumière additionnée (gaia_agreger.py) -> gaia_agrege.bin, lu par l'appli PC (natif/src/gaia_agrege.h).

Chaque case (pixel HEALPix de niveau 7 × tranche de parallaxe d'un dixième de décade) devient un point de lumière :
- direction : centre du pixel (ICRS -> écliptique J2000, comme gaia_convertir.py) ;
- distance : 1 / parallaxe au milieu de la tranche (en log) ;
- lumière : somme des flux G mesurés × (d / 10 pc)², rangée en magnitude absolue ; couleur : BP-RP moyen pondéré par le flux ;
- taille : côté du pixel à cette distance (la case est un morceau de ciel épais d'un dixième de décade en parallaxe) ;
- incertitude : erreur relative moyenne de la parallaxe, pondérée par le flux (gardée dans le fichier).
Seules les sources dont la parallaxe vaut plus de 5 fois son erreur sont placées en volume ; les autres rejoignent la lumière « ciel seul » (distance inconnue), comme les sources sans parallaxe. Cette lumière n'est
montrée que vue du voisinage du Soleil, là où seule la direction compte.

Format gaia_agrege.bin (petit-boutiste) : en-tête 64 octets (« UNIVGAG2 », nombre de cases 3D (u64), nombre de pixels du
ciel (u32), niveau HEALPix (u32), lumière totale 3D et ciel seul (f64, en 10^(-0,4 G) vu du Soleil)), puis cases 3D de
48 octets : x, y, z (f32, al), magnitude absolue G (f32, mesurée depuis la Terre), rayon (f32, al), erreur relative de distance
(f32), pas de couleur (u32 : bits 0-7 pas de couleur, même table que gaia.bin ; bit 8 vitesse radiale mesurée ; bits 16-31
décalage d'éclat vu de loin, entier signé en millièmes de magnitude, gaia_reequilibre.py), nombre de sources (u32), vitesse moyenne x, y, z (f32, km/s),
dispersion (f32, km/s) ; puis pixels du ciel de 16 octets : direction x, y, z
(f32, unité), flux G vu du Soleil (f32) ; puis le pas de couleur des pixels du ciel (u8).

Usage : python gaia_agrege_convertir.py <dossier de gaia_agreger.py> <gaia.bin> <dossier de sortie>
"""
import glob, math, os, sys
import numpy as np
from astropy.io import fits

import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')      # accents lisibles dans la console Windows
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gaia_convertir as gc
import gaia_reequilibre as gr

NIVEAU = 7
ERREUR_MAX = 0.2      # par construction (gaia_agreger.py : parallaxe > 5 erreurs) ; garde-fou


def lire(dossier, nom, parts=1024):
    fichiers = sorted(glob.glob(os.path.join(dossier, f'{nom}_*.fits')))
    if len(fichiers) != parts: sys.exit(f'{nom} : {len(fichiers)} parts sur {parts}')
    out = {}
    for p in fichiers:
        with fits.open(p) as h:
            d = h[1].data
            for c in d.columns.names: out.setdefault(c.lower(), []).append(np.asarray(d[c], np.float64))
    return {k: np.concatenate(v) for k, v in out.items()}


def radec(hp):
    from astropy_healpix import HEALPix
    import astropy.units as u
    lon, lat = HEALPix(nside=2 ** NIVEAU, order='nested').healpix_to_lonlat(hp.astype(np.int64))
    return lon.to_value(u.rad), lat.to_value(u.rad)


def ecl(x, y, z):
    e = gc.EPS
    return np.stack([x, math.cos(e) * y + math.sin(e) * z, -math.sin(e) * y + math.cos(e) * z], 1)


def directions(hp):
    ra, de = radec(hp)
    return ecl(np.cos(de) * np.cos(ra), np.cos(de) * np.sin(ra), np.sin(de))


def vitesses(D, k):
    """Vitesse moyenne de chaque case (km/s, écliptique, par rapport au Soleil) et dispersion sur le ciel (km/s).
    Sur le ciel : moyenne des vitesses tirées des mouvements propres mesurés. Le long de la ligne de visée : moyenne des
    vitesses radiales mesurées s'il y en a dans la case ; sinon nulle [supposition, drapeau]."""
    n = D['n'][k]
    va, vd = D['sva'][k] / n, D['svd'][k] / n
    disp = np.sqrt(np.maximum(D['sva2'][k] / n - va ** 2, 0) + np.maximum(D['svd2'][k] / n - vd ** 2, 0))
    nrv = D['nrv'][k]
    vr = np.where(nrv > 0, D['srv'][k] / np.maximum(nrv, 1), 0.0)
    ra, de = radec(D['hp'][k])
    ca, sa, cd, sd = np.cos(ra), np.sin(ra), np.cos(de), np.sin(de)
    v = ecl(vr * cd * ca - va * sa - vd * sd * ca, vr * cd * sa + va * ca - vd * sd * sa, vr * sd + vd * cd)
    return v, disp, nrv > 0


def pas_couleur(fc, fcn):
    bprp = np.where(fcn > 0, fc / np.maximum(fcn, 1e-300), np.nan)
    return np.where(np.isfinite(bprp), np.clip(np.floor((bprp - gc.BPRP0) / gc.BPRP_PAS), 0, 254), 255).astype(np.uint32)


def main():
    dossier, gaia_bin, sortie = sys.argv[1:4]
    D = lire(dossier, 'distance')
    C = lire(dossier, 'ciel')
    err = D['fe'] / D['f']
    loin = err > ERREUR_MAX
    print(f'cases 3D : {len(err)} ; sources {D["n"].sum():.4e} ; lumière {D["f"].sum():.4e} ; '
          f'dont erreur > 100 % : {loin.sum()} cases, {D["f"][loin].sum() / D["f"].sum():.1%} de leur lumière')
    print(f'ciel seul (sans parallaxe positive) : {C["n"].sum():.4e} sources, lumière {C["f"].sum():.4e}')

    k = ~loin
    plx = 10 ** ((D['pb'][k] + 0.5) / 10)                       # mas, milieu de la tranche (en log)
    d_ly = 1000.0 / plx * gc.LY_PER_PC
    u = directions(D['hp'][k])
    cote = math.sqrt(4 * math.pi / (12 * 4 ** NIVEAU))          # côté d'un pixel (rad)
    M = -2.5 * np.log10(D['f'][k] * (1000.0 / plx / 10.0) ** 2)
    cases = np.zeros(int(k.sum()), np.dtype([('p', '<f4', 3), ('m', '<f4'), ('r', '<f4'), ('e', '<f4'), ('c', '<u4'), ('n', '<u4'),
                                             ('v', '<f4', 3), ('s', '<f4')]))
    cases['p'] = u * d_ly[:, None]
    cases['m'], cases['r'], cases['e'] = M, 0.5 * cote * d_ly, err[k]
    v, disp, a_rv = vitesses(D, k)
    # éclat rééquilibré vu de loin (gaia_reequilibre.py, HYPOTHÈSE dite à l'écran, vue « meilleur rendu » seulement) : la
    # lumière de chaque case est comparée à celle de ses voisines sur le ciel (15°), à même distance
    ra, de = radec(D['hp'][k])
    ui = np.stack([np.cos(de) * np.cos(ra), np.cos(de) * np.sin(ra), np.sin(de)], 1)
    w = gr.poids(gr.cles(ui, 1000.0 / plx, np.full(len(plx), -6.0)), D['n'][k])
    dm = gr.decalage_mmag(w)
    print(f'éclat rééquilibré : lumière déplacée {np.abs(w - 1) @ D["f"][k] / D["f"][k].sum():.1%}')
    ag_bits = dm.view(np.uint16).astype(np.uint32) << 16
    cases['c'], cases['n'] = pas_couleur(D['fc'][k], D['fcn'][k]) | (a_rv.astype(np.uint32) << 8) | ag_bits, D['n'][k]
    cases['v'], cases['s'] = v, disp
    poids = D['f'][k]
    o = np.argsort(disp); cum = np.cumsum(poids[o]) / poids.sum()
    disp_med = float(disp[o][np.searchsorted(cum, 0.5)])
    print(f'vitesses des cases : dispersion sur le ciel médiane (pondérée par la lumière) {disp_med:.1f} km/s ; '
          f'cases avec une vitesse radiale mesurée : {a_rv.sum()} ({poids[a_rv].sum() / poids.sum():.1%} de la lumière)')

    # ciel seul : sources sans parallaxe positive + cases trop incertaines, additionnées par pixel
    hp = np.concatenate([C['hp'], D['hp'][loin]]).astype(np.int64)
    npix = 12 * 4 ** NIVEAU
    f = np.bincount(hp, np.concatenate([C['f'], D['f'][loin]]), npix)
    fc = np.bincount(hp, np.concatenate([C['fc'], D['fc'][loin]]), npix)
    fcn = np.bincount(hp, np.concatenate([C['fcn'], D['fcn'][loin]]), npix)
    nciel = np.bincount(hp, np.concatenate([C['n'], D['n'][loin]]), npix)
    garde = f > 0
    ciel = np.zeros(int(garde.sum()), cases.dtype)
    ciel['p'], ciel['m'] = directions(np.arange(npix)[garde]), -2.5 * np.log10(f[garde])      # magnitude apparente G du pixel
    ciel['r'], ciel['e'] = 0.5 * cote, np.nan
    ciel['c'], ciel['n'] = pas_couleur(fc, fcn)[garde], nciel[garde]
    tot3, totc = float(D['f'][k].sum()), float(f.sum())
    print(f'-> {len(cases)} cases placées en 3D ({tot3 / (tot3 + totc):.1%} de la lumière), ciel seul {totc / (tot3 + totc):.1%}')

    os.makedirs(sortie, exist_ok=True)
    chemin = os.path.join(sortie, 'gaia_agrege.bin')
    head = (b'UNIVGAG2' + np.uint64(len(cases)).tobytes() + np.array([len(ciel), NIVEAU], '<u4').tobytes() + np.array([tot3, totc], '<f8').tobytes()
            + np.array([disp_med], '<f4').tobytes())
    with open(chemin, 'wb') as fo:
        fo.write(head + b'\0' * (64 - len(head)))
        fo.write(cases.tobytes()); fo.write(ciel.tobytes())
    print(f'-> {chemin} ({os.path.getsize(chemin) / 1e6:.0f} Mo)')


if __name__ == '__main__':
    main()
