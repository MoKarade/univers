#!/usr/bin/env python3
"""Forme MESURÉE des galaxies -> galaxies_formes.bin (natif/src/galaxies_formes.h) et galaxies.bin marqué.

Marc, 13/11/2026 : « toujours plein de galaxies juste images ». Les galaxies doivent être faites d'étoiles. Ce script
rassemble ce qui est mesuré pour chaque galaxie qu'on peut voir en grand :
- Siena Galaxy Atlas 2020 (Moustakas et al. 2023, ApJS 269, 3 ; legacysurvey.org/sga/sga2020, fichier SGA-2020.fits,
  716 Mo, 383 620 galaxies) : position, diamètre D26 (isophote 26 mag/arcsec² en r), rapport d'axes BA, angle de
  position PA, type morphologique (MORPHTYPE, de HyperLEDA), décalage vers le rouge (Z_LEDA), magnitudes g et r dans
  l'isophote 26 (AB) ; à défaut MAG_LEDA ;
- HyperLEDA I (Paturel et al. 2003, VizieR VII/237, 983 261 galaxies) : type, log D25, log R25, PA (équinoxe B1950,
  ramené en J2000 ici) ; pas de magnitude. Pour une galaxie présente dans les deux, SGA fait foi ;
- distance : Cosmicflows-4 (galaxies_cf4.tsv, distances MESURÉES) ou galaxies nommées du Groupe local
  (galaxies_noms.tsv) quand la galaxie y est (même direction à 30″ près) ; sinon le décalage vers le rouge (d'un point
  du catalogue à 15″ près, sinon Z_LEDA), changé en distance par l'appli selon la cosmologie choisie.
Andromède, le Triangle et les deux Nuages sont exclus : ils sont déjà faits de leurs étoiles (voisines_etoiles.bin).

Sorties :
- galaxies_formes.bin : « UNIVGFM1 », n (u32), réservé jusqu'à 64 octets ; puis n fiches de 48 octets :
  direction (3 × f32, unité, écliptique J2000), z (f32 ; -1 : distance mesurée), distance (f32, années-lumière ;
  -1 : à calculer depuis z), diamètre (f32, minutes d'arc), BA (f32), PA (f32, degrés, du nord vers l'est, J2000),
  type T (f32, -5 elliptique à 10 irrégulière ; 99 inconnu), magnitude r (f32, AB, apparente ; mesurée si drapeau 1,
  sinon estimée par la taille), g - r (f32 ;
  99 inconnu), drapeaux (u32 : 1 magnitude mesurée, 2 forme mesurée, 4 type mesuré, 8 distance mesurée, 16 SGA, 32 LEDA) ;
- galaxies.bin : copie du catalogue où chaque point qui est l'une de ces galaxies (même direction à 15″ près) porte
  128 dans son 4e octet de couleur : l'appli ne le dessine plus en point, la galaxie de particules prend sa place.
Usage : python galaxies_formes.py <SGA-2020.fits> <leda_pgc.tsv> <dossier des données de l'appli> <dossier de sortie>
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')
import math, os, sys, time
import numpy as np
from astropy.io import fits
from scipy.spatial import cKDTree

EPS = math.radians(84381.448 / 3600.0)
EXCLUS_PGC = {2557, 5818, 17223, 3085}
# Galaxies de Messier et leur numéro NGC (catalogue de Messier ; M102 = NGC 5866, attribution usuelle) : noms cherchables.
MESSIER = {32: 221, 49: 4472, 51: 5194, 58: 4579, 59: 4621, 60: 4649, 61: 4303, 63: 5055, 64: 4826, 65: 3623, 66: 3627,
           74: 628, 77: 1068, 81: 3031, 82: 3034, 83: 5236, 84: 4374, 85: 4382, 86: 4406, 87: 4486, 88: 4501, 89: 4552,
           90: 4569, 91: 4548, 94: 4736, 95: 3351, 96: 3368, 98: 4192, 99: 4254, 100: 4321, 101: 5457, 102: 5866,
           104: 4594, 105: 3379, 106: 4258, 108: 3556, 109: 3992, 110: 205}
# Messier absentes de SGA, trouvées dans HyperLEDA par leur numéro PGC (M104, M86, M90, M98).
MESSIER_PGC = {104: (42407, 4594), 86: (40653, 4406), 90: (41024, 4569), 98: (39028, 4192)}       # M31, M33, Grand et Petit Nuage : déjà faits de leurs étoiles
ARCSEC = math.radians(1 / 3600)


def ecl(ra_deg, dec_deg):
    ra, de = np.radians(ra_deg), np.radians(dec_deg)
    x, y, z = np.cos(de) * np.cos(ra), np.cos(de) * np.sin(ra), np.sin(de)
    ce, se = math.cos(EPS), math.sin(EPS)
    return np.stack([x, ce * y + se * z, -se * y + ce * z], 1)


def type_T(s):
    """Type morphologique (texte HyperLEDA / RC3) -> T numérique de de Vaucouleurs ; 99 si inconnu."""
    s = (s or '').strip().replace('?', '')
    if not s: return 99.0
    for pre in ('SAB', 'SB', 'SA'):
        if s.startswith(pre): s = 'S' + s[len(pre):]
    table = [('E-S0', -3), ('S0-a', 0), ('S0', -2), ('E', -5), ('Sab', 2), ('Sbc', 4), ('Scd', 6), ('Sdm', 8), ('Sa', 1),
             ('Sb', 3), ('Sc', 5), ('Sd', 7), ('Sm', 9), ('I', 10), ('S', 3)]
    for k, t in table:
        if s.startswith(k): return float(t)
    return 99.0


def pa_b1950_vers_j2000(ra, dec, pa):
    """Rotation du nord entre B1950 et J2000 (précession) : PA_J2000 = PA_B1950 + angle entre les deux nords [astropy]."""
    import astropy.units as u
    from astropy.coordinates import SkyCoord, FK4, FK5
    c = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame=FK5(equinox='J2000'))
    b = c.transform_to(FK4(equinox='B1950'))
    nord = SkyCoord(ra=b.ra, dec=np.minimum(b.dec.deg + 0.01, 89.99) * u.deg, frame=FK4(equinox='B1950')).transform_to(FK5(equinox='J2000'))
    return (pa + c.position_angle(nord).deg) % 180.0


def sexa(s, heures):
    p = np.array([x.split() for x in s], float)
    sgn = np.where(np.char.startswith(np.array(s), '-'), -1.0, 1.0)
    v = np.abs(p[:, 0]) + p[:, 1] / 60 + p[:, 2] / 3600
    return v * 15 if heures else v * sgn


def lire_leda(chemin):
    lignes = [l.rstrip('\n').split('\t') for l in open(chemin, encoding='utf-8') if l.strip() and not l.startswith('#')]
    entete = lignes[0]; i = {k.strip(): n for n, k in enumerate(entete)}
    rows = [r for r in lignes[3:] if len(r) == len(entete) and r[i['PGC']].strip().isdigit()]
    pgc = np.array([int(r[i['PGC']]) for r in rows])
    ra = sexa([r[i['RAJ2000']] for r in rows], True); de = sexa([r[i['DEJ2000']] for r in rows], False)
    f = lambda k: np.array([float(r[i[k]]) if r[i[k]].strip() else np.nan for r in rows])
    return dict(pgc=pgc, ra=ra, dec=de, otype=np.array([r[i['OType']].strip() for r in rows]), mtype=[r[i['MType']] for r in rows],
                logd25=f('logD25'), logr25=f('logR25'), pa=f('PA'))


def ecrire_noms(chemin, S, u, dist, z, place, n_s, donnees, pgc_l=()):
    """Noms cherchables dans l'appli (Messier, NGC, IC) pour les galaxies SGA placées, s'ils ne sont pas déjà des astres
    de l'appli (galaxies_noms.tsv, galaxies_cf4.tsv). Position : direction mesurée x distance mesurée, sinon distance du
    décalage vers le rouge (Planck 2018, distance comobile, comme la table de l'appli à l'ouverture)."""
    from astropy.cosmology import FlatLambdaCDM
    cosmo = FlatLambdaCDM(H0=67.4, Om0=0.315)
    deja = set()
    for fic in ('galaxies_noms.tsv', 'galaxies_cf4.tsv'):
        ch = os.path.join(donnees, fic)
        if os.path.exists(ch): deja |= {l.split('\t')[0] for l in open(ch, encoding='utf-8')}
    messier = {f'NGC {v}': k for k, v in MESSIER.items()}
    lignes = []
    for i in range(n_s):
        if not place[i]: continue
        g = str(S['GALAXY'][i]).strip()
        nom = None
        for pre in ('NGC', 'IC'):
            if g.startswith(pre) and g[len(pre):].isdigit(): nom = f'{pre} {int(g[len(pre):])}'
        if not nom: continue
        if nom in messier:      # alias de Messier : ajouté même si la NGC est déjà un astre (sous son seul numéro NGC)
            m = f'M{messier[nom]}'
            if m in deja or any(f'({m})' in x for x in deja): continue
            nom = f'{m} ({nom})'
        elif nom in deja: continue
        d = dist[i] if dist[i] > 0 else cosmo.comoving_distance(z[i]).to_value('Mpc') * 3.2615637769e6
        p = u[i] * d
        mes = 'distance mesurée (Cosmicflows-4)' if dist[i] > 0 else f'distance d\'après z = {z[i]:.4f}'
        lignes.append(f'{nom}\t{p[0]:.6g}\t{p[1]:.6g}\t{p[2]:.6g}\tgalaxie ; forme mesurée (SGA-2020) ; {mes}\t{3 if nom.startswith("M") else 9}')
    pgc_l = np.asarray(pgc_l)
    for m, (pgc, ngc) in MESSIER_PGC.items():      # Messier absentes de SGA : trouvées dans HyperLEDA par leur PGC
        k = np.nonzero(pgc_l == pgc)[0]
        if not len(k) or f'M{m}' in deja or any(f'(M{m})' in x for x in deja): continue
        i = n_s + int(k[0])
        if not place[i]: continue
        d = dist[i] if dist[i] > 0 else cosmo.comoving_distance(z[i]).to_value('Mpc') * 3.2615637769e6
        p = u[i] * d
        mes = 'distance mesurée (Cosmicflows-4)' if dist[i] > 0 else f'distance d\'après z = {z[i]:.4f}'
        lignes.append(f'M{m} (NGC {ngc})\t{p[0]:.6g}\t{p[1]:.6g}\t{p[2]:.6g}\tgalaxie ; forme mesurée (HyperLEDA) ; {mes}\t3')
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f: f.write('\n'.join(lignes) + '\n')
    print(f'{len(lignes)} noms cherchables (Messier, NGC, IC) -> {chemin}')


def main():
    sga_f, leda_f, donnees, sortie = sys.argv[1:5]
    t0 = time.time()
    s = fits.open(sga_f, memmap=True)['ELLIPSE'].data
    pgc_s = np.asarray(s['PGC']).astype(np.int64)
    garde = ~np.isin(pgc_s, list(EXCLUS_PGC)) & (np.asarray(s['D26']) > 0)
    S = {k: np.asarray(s[k])[garde] for k in ('RA', 'DEC', 'D26', 'BA', 'PA', 'MORPHTYPE', 'Z_LEDA', 'R_MAG_SB26', 'G_MAG_SB26', 'MAG_LEDA', 'PGC', 'GALAXY')}
    print(f'SGA : {garde.sum()} galaxies ({time.time() - t0:.0f} s)')
    L = lire_leda(leda_f)
    lg = (L['otype'] == 'G') & ~np.isin(L['pgc'], list(EXCLUS_PGC)) & ~np.isin(L['pgc'], S['PGC']) & np.isfinite(L['logd25'])
    L = {k: (np.asarray(v)[lg] if not isinstance(v, list) else [v[j] for j in np.nonzero(lg)[0]]) for k, v in L.items()}
    pa_l = np.where(np.isfinite(L['pa']), pa_b1950_vers_j2000(L['ra'], L['dec'], np.nan_to_num(L['pa'])), np.nan)
    print(f'HyperLEDA : {lg.sum()} galaxies de plus que SGA ({time.time() - t0:.0f} s)')

    n_s, n_l = len(S['RA']), len(L['pgc'])
    u = np.concatenate([ecl(S['RA'], S['DEC']), ecl(L['ra'], L['dec'])])
    diam = np.concatenate([S['D26'], 0.1 * 10 ** L['logd25']])      # minutes d'arc
    ba = np.concatenate([S['BA'], np.where(np.isfinite(L['logr25']), 10 ** -L['logr25'], np.nan)])
    pa = np.concatenate([S['PA'], pa_l])
    T = np.array([type_T(x) for x in list(S['MORPHTYPE']) + list(L['mtype'])])
    rmag = np.concatenate([np.where(S['R_MAG_SB26'] > 0, S['R_MAG_SB26'], np.where(S['MAG_LEDA'] > 0, S['MAG_LEDA'], 99.0)), np.full(n_l, 99.0)])
    gr = np.concatenate([np.where((S['R_MAG_SB26'] > 0) & (S['G_MAG_SB26'] > 0), S['G_MAG_SB26'] - S['R_MAG_SB26'], 99.0), np.full(n_l, 99.0)])
    z = np.concatenate([np.where(S['Z_LEDA'] > 0, S['Z_LEDA'], -1.0), np.full(n_l, -1.0)])
    dist = np.full(n_s + n_l, -1.0)
    drap = np.zeros(n_s + n_l, np.uint32)
    drap[:n_s] |= 16; drap[n_s:] |= 32
    drap |= np.where(rmag < 90, 1, 0).astype(np.uint32)
    drap |= np.where(np.isfinite(ba) & np.isfinite(pa), 2, 0).astype(np.uint32)
    drap |= np.where(T < 90, 4, 0).astype(np.uint32)

    arbre = cKDTree(u)
    # distances mesurées : Cosmicflows-4 et galaxies nommées (positions en années-lumière, Soleil au centre)
    for fic, rayon in (('galaxies_cf4.tsv', 30.0), ('galaxies_noms.tsv', 60.0)):
        ch = os.path.join(donnees, fic)
        if not os.path.exists(ch): continue
        p = np.array([[float(x) for x in l.split('\t')[1:4]] for l in open(ch, encoding='utf-8') if l.count('\t') >= 4])
        dl = np.linalg.norm(p, axis=1); up = p / dl[:, None]
        dd, j = arbre.query(up, distance_upper_bound=rayon * ARCSEC)
        ok = np.isfinite(dd)
        dist[j[ok]] = dl[ok]; drap[j[ok]] |= 8
        print(f'{fic} : {ok.sum()} distances mesurées reprises')
    # catalogue de l'appli : décalage vers le rouge des points, et points à ne plus dessiner
    gb = os.path.join(donnees, 'galaxies.bin')
    with open(gb, 'rb') as f: head = f.read(64)
    n = int(np.frombuffer(head, '<u8', 1, 8)[0]); col = (n * 4 + 63) // 64 * 64
    brut = np.fromfile(gb, np.uint8)
    cols = [np.frombuffer(brut, '<f4', n, 64 + k * col) for k in range(4)]
    pts = np.stack(cols[:3], 1).astype(np.float64)
    dd, j = arbre.query(pts, distance_upper_bound=15.0 * ARCSEC, workers=-1)
    ok = np.isfinite(dd)
    sans_z = (z < 0)[j[ok]] & (dist[j[ok]] < 0)
    z[j[ok][sans_z]] = cols[3][ok][sans_z]
    couleur = brut[64 + 4 * col:64 + 4 * col + 4 * n].reshape(n, 4).copy()
    couleur[ok & (couleur[:, 3] != 255), 3] = 128      # dessiné par galaxies_formes.h (jamais un quasar)
    print(f'catalogue de l\'appli : {ok.sum()} points sont l\'une de ces galaxies ({time.time() - t0:.0f} s)')

    # magnitude manquante : relation taille-éclat calée ici sur les galaxies SGA mesurées (r = a + b log10 D26) [supposé]
    mes = (rmag < 90) & (diam > 0)
    b, a = np.polyfit(np.log10(diam[mes]), rmag[mes], 1)
    rmag = np.where(rmag < 90, rmag, a + b * np.log10(np.maximum(diam, 1e-3)))
    print(f'magnitude estimée par la taille (supposée) : r = {a:.2f} {b:+.2f} log10(D26 en arcmin), pour {int((~mes).sum())} galaxies')
    place = (dist > 0) | (z > 0)
    print(f'galaxies placées : {place.sum()} sur {n_s + n_l} (sans distance ni z : {(~place).sum()}, écartées)')
    rec = np.zeros(int(place.sum()), np.dtype([('u', '<f4', 3), ('z', '<f4'), ('d', '<f4'), ('diam', '<f4'), ('ba', '<f4'), ('pa', '<f4'),
                                               ('T', '<f4'), ('r', '<f4'), ('gr', '<f4'), ('f', '<u4')]))
    rec['u'] = u[place]; rec['z'] = np.where(dist[place] > 0, -1.0, z[place]); rec['d'] = dist[place]
    rec['diam'] = diam[place]; rec['ba'] = np.nan_to_num(ba[place], nan=-1.0); rec['pa'] = np.nan_to_num(pa[place], nan=-1.0)
    rec['T'] = T[place]; rec['r'] = rmag[place]; rec['gr'] = gr[place]; rec['f'] = drap[place]
    os.makedirs(sortie, exist_ok=True)
    with open(os.path.join(sortie, 'galaxies_formes.bin'), 'wb') as f:
        h = b'UNIVGFM1' + np.uint32(len(rec)).tobytes()
        f.write(h + b'\0' * (64 - len(h))); f.write(rec.tobytes())
    ecrire_noms(os.path.join(sortie, 'galaxies_formes_noms.tsv'), S, u, dist, z, place, n_s, donnees, L['pgc'])
    out = bytearray(brut.tobytes()); out[64 + 4 * col:64 + 4 * col + 4 * n] = couleur.tobytes()
    with open(os.path.join(sortie, 'galaxies.bin'), 'wb') as f: f.write(out)
    print(f'-> {sortie} : {len(rec)} galaxies ; magnitude mesurée {int((rec["f"] & 1 > 0).sum())}, forme {int((rec["f"] & 2 > 0).sum())}, '
          f'type {int((rec["f"] & 4 > 0).sum())}, distance mesurée {int((rec["f"] & 8 > 0).sum())} ({time.time() - t0:.0f} s)')


if __name__ == '__main__':
    main()
