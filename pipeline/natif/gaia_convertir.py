#!/usr/bin/env python3
"""Étoiles Gaia DR3 téléchargées (gaia_telecharger.py) -> gaia.bin, lu par l'appli PC (natif/src/gaia.h).

Ce qui est fait, sans rien inventer :
- distance = 1 / parallaxe (les étoiles gardées ont une parallaxe mesurée à mieux que 10 %) ;
- position : ICRS -> repère écliptique J2000 de l'appli (obliquité 84 381,448″, comme natif/src/ephemeride.h), en
  années-lumière, centrée sur le Soleil, à l'époque des mesures de Gaia (J2016,0) ;
- magnitude absolue G = G + 5 log10(parallaxe / 100 mas), telle que mesurée : la poussière entre l'étoile et le
  Soleil est comprise (l'étoile est vue comme depuis la Terre) ;
- couleur : indice BP-RP mesuré, rangé en 255 pas ; table des températures du corps noir qui donnent cet indice
  à travers les bandes de Gaia (Riello et al. 2021, fichier passband.dat) ;
- vitesse : mouvement propre et parallaxe -> vitesse sur le ciel ; vitesse radiale de Gaia quand elle existe.
  Sans vitesse radiale mesurée, elle compte pour zéro et l'étoile le dit (drapeau) ;
- doublons : une étoile du catalogue principal de la page (étoiles brillantes, noms) retrouvée dans Gaia
  (même direction à 40″ près, magnitude à 2 près) est retirée de Gaia : l'appli la dessine une seule fois.

Rangement pour l'affichage : arbre en huit (octree) sur les positions, feuilles d'au plus 32 768 étoiles ; dans
chaque feuille, étoiles de la plus brillante à la plus faible. L'appli dessine d'une feuille seulement les étoiles
assez brillantes pour être vues de la caméra.

Format gaia.bin (petit-boutiste), sections alignées sur 64 octets :
  en-tête 4096 octets : « UNIVGAI1 », n (u64), nombre de feuilles (u32), époque (f32, 2016,0), bp_rp du pas 0 (f32),
                        largeur d'un pas (f32), 256 températures (f32, K ; NaN pour le pas 255 = couleur non mesurée)
  feuilles (48 octets) : min x,y,z (f32), nombre (u32), max x,y,z (f32), réservé (u32), première étoile (u64), réservé (u64)
  étoiles (16 octets)  : x, y, z (f32, al), magnitude absolue G (f16), pas de couleur (u8), drapeaux (u8 : 1 = vitesse radiale
                         mesurée ; 2 = orbite fiable : vitesse radiale mesurée et vitesse 3D connue à mieux que --seuil-vitesse ;
                         4 = éclat rééquilibré vu de loin, gaia_reequilibre.py)
  vitesses (8 octets)  : vx, vy, vz (i16, pas de 0,05 km/s), décalage de magnitude vu de loin (i16, millièmes de magnitude,
                         0 sans drapeau 4 ; hypothèse, voir gaia_reequilibre.py)
  résumés (528 octets par feuille) : centre de lumière x, y, z (f32), réservé (f32), lumière 10^(-0,4 M) par tranche (64 f32),
                        pas de couleur moyen par tranche (64 f32) ; tranches et bornes : en-tête, octets 1056 à 1067

Usage : python gaia_convertir.py <dossier des parts> <etoiles.bin> <passband.dat> <zeropt.dat> <dossier de sortie>
        [--erreurs <dossier du jeu erreurs>] [--seuil-vitesse 10] [--reequilibre oui|non]
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')      # accents lisibles dans la console Windows
import glob, math, os, sys, time
import numpy as np
from astropy.io import fits
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gaia_reequilibre as gr

LY_PER_PC = 3.2615638
EPS = math.radians(84381.448 / 3600.0)
KAPPA = 4.740470446      # km/s pour 1 mas/an à 1 kpc
FEUILLE = 32768
TRANCHES, TRANCHE0, TRANCHE_L = 64, -8.0, 0.5      # résumé des feuilles : magnitudes absolues -8 à +24 par 0,5
ATTENDU = 98_346_986      # COUNT(*) WHERE parallax_over_error > 10, archive Gaia, 12 novembre 2026
BPRP0, BPRP_PAS = -0.6, 0.03      # pas 0 à 253 : -0,6 à 7,0 ; 254 : au-delà ; 255 : non mesuré
V_PAS = 0.05
ERREURS = ['parallax_error', 'pmra_error', 'pmdec_error', 'radial_velocity_error']
SEUIL_VITESSE = 10.0      # km/s : incertitude de vitesse au-delà de laquelle l'orbite n'est pas fiable (docs/gaia-rayons.md)


def _aligne(ids, autre, cols):
    """Colonnes d'une part d'un autre jeu (mêmes étoiles, autre ordre) remises dans l'ordre de `ids`."""
    o = np.argsort(autre['source_id'])
    j = o[np.searchsorted(autre['source_id'], ids, sorter=o)]
    if not (autre['source_id'][j] == ids).all(): sys.exit('jeux téléchargés différents (source_id)')
    return {k: np.asarray(autre[k])[j] for k in cols}


def lire_parts(dossier, erreurs=None):
    parts = sorted(glob.glob(os.path.join(dossier, 'part_*.fits')))
    if len(parts) != 1024: sys.exit(f'{len(parts)} parts sur 1024 : finir le téléchargement')
    noms = ['source_id', 'ra', 'dec', 'parallax', 'pmra', 'pmdec', 'radial_velocity', 'phot_g_mean_mag', 'bp_rp']
    if erreurs: noms += ERREURS
    cols = {k: [] for k in noms}
    for p in parts:
        with fits.open(p, memmap=False) as h:
            d = h[1].data
            for k in noms[:9]: cols[k].append(np.asarray(d[k]))
            for extra, liste in ((erreurs, ERREURS),):
                if not extra: continue
                with fits.open(os.path.join(extra, os.path.basename(p)), memmap=False) as he:
                    for k, v in _aligne(np.asarray(d['source_id']), he[1].data, liste).items(): cols[k].append(v)
    return {k: np.concatenate(v) for k, v in cols.items()}


def temperatures(passband, zeropt):
    """Température du corps noir dont l'indice BP-RP synthétique vaut le centre de chaque pas.
    Indice synthétique (Riello et al. 2021, éq. 2) : -2,5 log10(∫ B_λ S_λ λ dλ) + point zéro ; le rapport BP/RP
    ne dépend pas de l'échelle du flux. [Probable : une étoile n'est pas un corps noir ; couleur à quelques % près.]"""
    t = np.loadtxt(passband)
    lam, bp, rp = t[:, 0], t[:, 3], t[:, 5]
    bp = np.where(bp > 99, 0, bp); rp = np.where(rp > 99, 0, rp)
    zp = open(zeropt).read().split('\n')
    vega = [l for l in zp if 'VEGAMAG' in l][0].split()
    zbp, zrp = float(vega[2]), float(vega[4])
    m = lam * 1e-9
    def indice(T):
        B = 1.0 / (m ** 5 * np.expm1(1.438776877e-2 / (m * T)))
        return -2.5 * np.log10(np.trapezoid(B * bp * lam, lam) / np.trapezoid(B * rp * lam, lam)) + zbp - zrp
    grille = np.geomspace(1000.0, 200000.0, 4000)
    ind = np.array([indice(T) for T in grille])      # décroît quand T monte
    centres = BPRP0 + BPRP_PAS * (np.arange(254) + 0.5)
    T = np.interp(-centres, -ind, grille)      # hors de ce qu'un corps noir peut donner : le plus froid ou le plus chaud de la grille
    out = np.full(256, np.nan, np.float32); out[:254] = T
    out[254] = grille[0]
    print(f'corps noir : BP-RP = {indice(5772.0):+.3f} à 5 772 K (Soleil), {indice(9600.0):+.3f} à 9 600 K ; '
          f'indice le plus bleu possible {ind[-1]:+.3f}')
    return out


def principal(etoiles_bin):
    with open(etoiles_bin, 'rb') as f: head = f.read(64)
    if head[:8] != b'UNIVSTR1': sys.exit('etoiles.bin illisible')
    n = int(np.frombuffer(head, '<i8', 1, 8)[0]); n0 = int(np.frombuffer(head, '<i4', 1, 16)[0])
    col = (n * 4 + 63) // 64 * 64
    mm = np.memmap(etoiles_bin, '<f4', 'r', 64, (col // 4 * 5,))
    x, y, z, mag = (np.array(mm[k * col // 4:k * col // 4 + n0], np.float64) for k in range(4))
    d = np.sqrt(x * x + y * y + z * z)
    return np.stack([x, y, z], 1) / d[:, None], mag + 5 * np.log10(d / LY_PER_PC) - 5, n0


def doublons(u_gaia, g, u_main, v_main):
    """Indices des étoiles Gaia déjà présentes dans le catalogue principal."""
    cand = np.nonzero(g < 13.0)[0]
    tree = cKDTree(u_main)
    r = math.radians(40.0 / 3600.0)
    dist, j = tree.query(u_gaia[cand], k=1, distance_upper_bound=r)
    ok = np.isfinite(dist)
    cand, dist, j = cand[ok], dist[ok], j[ok]
    dm = np.abs(g[cand] - v_main[j])
    ok = dm < 2.0
    cand, dist, j, dm = cand[ok], dist[ok], j[ok], dm[ok]
    score = dist / r + dm / 2.0
    o = np.lexsort((score, j))
    premier = np.ones(len(o), bool); premier[1:] = j[o][1:] != j[o][:-1]      # une seule étoile Gaia par étoile du catalogue
    return cand[o][premier], len(u_main)


def morton(q):
    def etale(v):
        v = v.astype(np.uint64) & np.uint64(0x1fffff)
        for s, m in ((32, 0x1f00000000ffff), (16, 0x1f0000ff0000ff), (8, 0x100f00f00f00f00f), (4, 0x10c30c30c30c30c3), (2, 0x1249249249249249)):
            v = (v | (v << np.uint64(s))) & np.uint64(m)
        return v
    return etale(q[:, 0]) | (etale(q[:, 1]) << np.uint64(1)) | (etale(q[:, 2]) << np.uint64(2))


def feuilles(cles):
    """Découpe l'ordre de Morton en feuilles d'au plus FEUILLE étoiles (cubes de l'arbre en huit)."""
    out, pile = [], [(0, len(cles), 0, 0)]
    while pile:
        lo, hi, niveau, prefixe = pile.pop()
        if hi - lo <= FEUILLE or niveau == 21:
            if hi > lo: out.append((lo, hi))
            continue
        dec = 3 * (20 - niveau)
        bornes = [lo] + [lo + int(np.searchsorted(cles[lo:hi], np.uint64(prefixe | (c << dec)))) for c in range(1, 8)] + [hi]
        for c in range(7, -1, -1): pile.append((bornes[c], bornes[c + 1], niveau + 1, prefixe | (c << dec)))
    out.sort()
    return out


def main():
    dossier, etoiles_bin, passband, zeropt, sortie = sys.argv[1:6]
    opt = dict(zip(sys.argv[6::2], sys.argv[7::2]))
    erreurs, reequilibre = opt.get('--erreurs'), opt.get('--reequilibre', 'oui') == 'oui'
    seuil = float(opt.get('--seuil-vitesse', SEUIL_VITESSE))
    t0 = time.time()
    G = lire_parts(dossier, erreurs)
    n_total = len(G['ra'])
    print(f'{n_total} étoiles lues ({time.time() - t0:.0f} s)')
    if n_total != ATTENDU: sys.exit(f'{n_total} étoiles lues, {ATTENDU} attendues (compte du 12 novembre 2026) : téléchargement incomplet')
    T = temperatures(passband, zeropt)

    ra, de, plx = np.radians(G['ra']), np.radians(G['dec']), G['parallax']
    ca, sa, cd, sd = np.cos(ra), np.sin(ra), np.cos(de), np.sin(de)
    ce, se = math.cos(EPS), math.sin(EPS)
    def ecl(x, y, z): return np.stack([x, ce * y + se * z, -se * y + ce * z], 1)
    u = ecl(cd * ca, cd * sa, sd)                                   # direction (vecteur unité)
    d_ly = 1000.0 / plx * LY_PER_PC
    g = G['phot_g_mean_mag'].astype(np.float64)
    M = g + 5 * np.log10(plx / 100.0)

    u_main, v_main, n_main = principal(etoiles_bin)
    retire, _ = doublons(u, g, u_main, v_main)
    garde = np.isfinite(g) & np.isfinite(plx) & (plx > 0); garde[retire] = False
    print(f'doublons avec le catalogue principal ({n_main} étoiles) : {len(retire)} retirées de Gaia')

    rv = G['radial_velocity'].astype(np.float64)
    a_rv = np.isfinite(rv)
    va, vd = KAPPA * G['pmra'] / plx, KAPPA * G['pmdec'] / plx
    vr = np.where(a_rv, rv, 0.0)
    v = ecl(vr * cd * ca - va * sa - vd * sd * ca, vr * cd * sa + va * ca - vd * sd * sa, vr * sd + vd * cd)

    # Orbite fiable (drapeau 2) : vitesse radiale mesurée et incertitude de la vitesse 3D sous le seuil, d'après les
    # erreurs publiées par Gaia (parallaxe, mouvement propre, vitesse radiale). Sans le jeu « erreurs » : aucune.
    fiable = np.zeros(len(plx), bool)
    if erreurs:
        vt = np.hypot(va, vd)
        s_vt2 = (KAPPA / plx) ** 2 * (G['pmra_error'].astype(np.float64) ** 2 + G['pmdec_error'].astype(np.float64) ** 2) + (vt * G['parallax_error'] / plx) ** 2
        s_v = np.sqrt(s_vt2 + np.where(a_rv, G['radial_velocity_error'].astype(np.float64), np.inf) ** 2)
        fiable = a_rv & (s_v < seuil)
    bprp = G['bp_rp'].astype(np.float64)
    pas = np.where(np.isfinite(bprp), np.clip(np.floor((bprp - BPRP0) / BPRP_PAS), 0, 254), 255).astype(np.uint8)

    k = np.nonzero(garde)[0]
    p = u[k] * d_ly[k, None]
    R = float(np.abs(p).max()) * 1.0001
    q = np.floor((p + R) / (2 * R) * (1 << 21)).clip(0, (1 << 21) - 1)
    cles = morton(q)
    o = np.argsort(cles, kind='stable'); k, p, cles = k[o], p[o], cles[o]
    fs = feuilles(cles)
    num = np.zeros(len(k), np.int64)
    for i, (lo, hi) in enumerate(fs): num[lo:hi] = i
    o = np.lexsort((M[k], num)); k, p = k[o], p[o]
    print(f'{len(k)} étoiles, {len(fs)} feuilles, demi-côté du cube {R:.0f} al ({time.time() - t0:.0f} s)')

    os.makedirs(sortie, exist_ok=True)
    rec = np.zeros(len(k), np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('m', '<f2'), ('c', 'u1'), ('f', 'u1')]))
    rec['x'], rec['y'], rec['z'] = p[:, 0], p[:, 1], p[:, 2]
    rec['m'], rec['c'] = M[k], pas[k]
    # Éclat rééquilibré vu de loin (drapeau 4, gaia_reequilibre.py) : HYPOTHÈSE dite à l'écran, aucune étoile ajoutée.
    uk = np.stack([cd[k] * ca[k], cd[k] * sa[k], sd[k]], 1)
    dm = gr.decalage_mmag(gr.poids(gr.cles(uk, 1000.0 / plx[k], M[k]))) if reequilibre else np.zeros(len(k), np.int16)
    rec['f'] = a_rv[k].astype(np.uint8) | (fiable[k].astype(np.uint8) << 1) | ((dm != 0).astype(np.uint8) << 2)
    vel = np.zeros((len(k), 4), '<i2')
    vel[:, :3] = np.clip(np.rint(v[k] / V_PAS), -32767, 32767)
    vel[:, 3] = dm
    fe = np.zeros(len(fs), np.dtype([('min', '<f4', 3), ('n', '<u4'), ('max', '<f4', 3), ('r0', '<u4'), ('premier', '<u8'), ('r1', '<u8')]))
    for i, (lo, hi) in enumerate(fs):
        fe['min'][i], fe['max'][i] = p[lo:hi].min(0), p[lo:hi].max(0)
        fe['n'][i], fe['premier'][i] = hi - lo, lo
    # Résumé de chaque feuille : centre de lumière et lumière par tranche de magnitude absolue (10^(-0,4 M), pas de couleur
    # moyen pondéré). L'appli y lit la lumière des étoiles qu'elle saute, pour la rendre en un seul point.
    lum = 10 ** (-0.4 * M[k])
    tr = np.clip(np.floor((M[k] - TRANCHE0) / TRANCHE_L), 0, TRANCHES - 1).astype(np.int64)
    cle = num * TRANCHES + tr
    nfe = len(fs) * TRANCHES
    res = np.zeros(len(fs), np.dtype([('c', '<f4', 3), ('r', '<f4'), ('lum', '<f4', TRANCHES), ('couleur', '<f4', TRANCHES)]))
    L_t = np.bincount(cle, lum, nfe)
    res['lum'] = L_t.reshape(-1, TRANCHES)
    mesure = pas[k] < 255      # couleur mesurée seulement
    L_c = np.bincount(cle[mesure], lum[mesure], nfe)
    res['couleur'] = np.where(L_c > 0, np.bincount(cle[mesure], lum[mesure] * pas[k][mesure].astype(np.float64), nfe) / np.maximum(L_c, 1e-300), 255).reshape(-1, TRANCHES)
    L_f = np.bincount(num, lum, len(fs))
    for a in range(3): res['c'][:, a] = np.bincount(num, lum * p[:, a], len(fs)) / L_f
    head = (b'UNIVGAI1' + np.uint64(len(k)).tobytes() + np.uint32(len(fs)).tobytes() + np.array([2016.0, BPRP0, BPRP_PAS], '<f4').tobytes()
            + T.tobytes() + np.uint32(TRANCHES).tobytes() + np.array([TRANCHE0, TRANCHE_L], '<f4').tobytes())
    chemin = os.path.join(sortie, 'gaia.bin')
    with open(chemin + '.partiel', 'wb') as f:
        f.write(head + b'\0' * (4096 - len(head)))
        for b in (fe.tobytes(), rec.tobytes(), vel.tobytes(), res.tobytes()): f.write(b + b'\0' * (-len(b) % 64))
    os.replace(chemin + '.partiel', chemin)
    print(f'-> {chemin} ({os.path.getsize(chemin) / 1e9:.2f} Go, {time.time() - t0:.0f} s) ; '
          f'vitesse radiale mesurée : {int(a_rv[k].sum())} ; orbite fiable (< {seuil:g} km/s) : {int(fiable[k].sum())} ; '
          f'éclat rééquilibré : {int((dm != 0).sum())} (lumière déplacée {np.abs(10 ** (-0.4 * dm / 1000.0) - 1) @ (10 ** (-0.4 * M[k])) / (10 ** (-0.4 * M[k])).sum():.1%}) ; couleur non mesurée : {int((pas[k] == 255).sum())}')


if __name__ == '__main__':
    main()
