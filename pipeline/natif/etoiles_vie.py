"""Place chaque étoile de l'appli sur sa trajectoire d'évolution MIST -> vie_a.bin, vie_b.bin, vie_principal.bin.

Lu par natif/src/vie_etoiles.h. L'appli n'ajoute à l'éclat et à la couleur MESURÉS que la différence calculée par le
modèle entre aujourd'hui et la date affichée : à la date d'aujourd'hui, rien ne change.

Trois façons de placer une étoile, dans cet ordre (drapeau « source ») :
1. Gaia FLAME (masse et âge publiés par Gaia DR3, solutions sans alerte : flags_flame commençant par 0) : trajectoire de
   la masse FLAME, au point de l'âge FLAME. Fourchette : bornes 16e-84e centiles publiées.
2. Diagramme éclat-couleur : position mesurée (magnitude absolue et couleur), débarrassée de la poussière mesurée (Gaia
   GSP-Phot : A_G, E(BP-RP) ; catalogue principal : carte 3D d'Edenhofer et al. 2024) ; sinon telle quelle (drapeau).
   Tous les points des trajectoires sont pesés par le nombre d'étoiles attendu (fonction de masse initiale de Kroupa 2001
   × temps passé au point, naissances à rythme constant depuis 13,8 Ga), rangés par case (0,02 mag en couleur, 0,05 en
   éclat) et par âge, puis lissés (0,03 et 0,15 mag : incertitudes de mesure et de composition). On retient l'âge médian
   de la case (fourchette : 16e et 84e centiles) et l'état du modèle le plus proche de (case, âge médian). [Probable :
   méthode classique des « isochrones bayésiennes », ici réduite à une table]
3. Rien ne convient (couleur non mesurée, case hors du modèle lissé, naines blanches que MIST ne suit pas) :
   « inconnu », l'étoile ne change pas avec le temps et sa fiche le dit.

Format vie_*.bin : « UNIVVIE1 », n (u64), puis n enregistrements de 8 octets, dans l'ordre exact du fichier d'étoiles :
  trace (u16), point d'évolution × 32 (u16), drapeaux (u8 : bits 0-1 source 0 inconnu, 1 FLAME, 2 diagramme dérougi,
  3 diagramme sans correction de poussière), fourchette basse et haute (u8 chacune : log10(âge / borne) × 100,
  plafonné à 255), réservé (u8).

Usage :
  python etoiles_vie.py gaia <mist_traces.bin> <gaia.bin> <gaia_ids.bin> <dossier ap> <sortie vie_a.bin>
  python etoiles_vie.py principal <mist_traces.bin> <etoiles.bin> <sortie vie_principal.bin>
"""
import glob
import os
import sys

import numpy as np
import pyarrow as pa
import pyarrow.compute as pcp
import pyarrow.parquet as pq
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gaia_ids as gi
import mist_lecture as ml

AGE_UNIVERS = 13.8e9
SOUS_PAS = 4      # points interpolés entre deux EEP pour remplir les cases
D_C, D_M = 0.02, 0.05
C0, C1, M0, M1 = -0.8, 5.0, -12.0, 18.0
LA0, D_LA, N_LA = 4.0, 0.05, 124      # cases d'âge : log10(âge / an) de 4 à 10,2
SIG_C, SIG_M, SIG_A = 0.03, 0.15, 0.05      # lissage : incertitudes typiques en couleur et en éclat (parallaxe, composition) [Supposition]
SEUIL_POIDS = 1e-12      # case « couverte » si son poids dépasse cette fraction du maximum
INCONNU, FLAME, DIAG, DIAG_BRUT = 0, 1, 2, 3
BPRP0, BPRP_PAS = -0.6, 0.03      # gaia_convertir.py


def kroupa(m: np.ndarray) -> np.ndarray:
    return np.where(m < 0.5, m ** -1.3, 0.5 * m ** -2.3)


def nuage(T: ml.Traces, bande: str) -> dict:
    """Tous les points des trajectoires (et SOUS_PAS points entre deux EEP), avec leur poids."""
    mag, coul = ('G', 'C') if bande == 'gaia' else ('V', 'BV')
    morceaux = {k: [] for k in ('tr', 'eep', 'age', 'mag', 'coul', 'poids', 'masse')}
    dm = T.masses * T.lpas      # largeur en masse de chaque trace
    for k in range(T.n):
        n = T.utiles[k]
        e = np.arange(0, n - 1, 1.0 / SOUS_PAS)
        tr = np.full(len(e), k)
        age = T.valeur('age', tr, e)
        da = np.gradient(age)
        garde = age <= AGE_UNIVERS
        if not garde.any():
            continue
        for nom, v in (('tr', tr), ('eep', e), ('age', age), ('mag', T.valeur(mag, tr, e)),
                       ('coul', T.valeur(coul, tr, e)), ('poids', kroupa(T.masses[k]) * dm[k] * np.maximum(da, 0)),
                       ('masse', np.full(len(e), T.masses[k]))):
            morceaux[nom].append(v[garde])
    return {k: np.concatenate(v) for k, v in morceaux.items()}


def table_cases(nu: dict) -> dict:
    """Pour chaque case : distribution des âges (lissée), d'où âge médian, 16e et 84e centiles, et masse moyenne à cet âge.

    Lissage gaussien dans le diagramme (SIG_C en couleur, SIG_M en éclat) : il tient compte des incertitudes de mesure et
    de composition. Sans lui, une naine un peu à côté de la séquence principale du modèle tombait dans une case où seuls
    passent des points de très jeunes étoiles, et recevait un âge de quelques milliers d'années (vu le 13/11/2026 sur
    61 du Cygne et Gliese 710).
    """
    nc, nm = int(round((C1 - C0) / D_C)), int(round((M1 - M0) / D_M))
    ic = np.floor((nu['coul'] - C0) / D_C).astype(np.int64)
    im = np.floor((nu['mag'] - M0) / D_M).astype(np.int64)
    ia = np.floor((np.log10(np.maximum(nu['age'], 1.0)) - LA0) / D_LA).astype(np.int64)
    ok = (ic >= 0) & (ic < nc) & (im >= 0) & (im < nm) & (ia >= 0) & (ia < N_LA) & (nu['poids'] > 0)
    cle = ((ic * nm + im) * N_LA + ia)[ok]
    w = nu['poids'][ok]
    taille = nc * nm * N_LA
    H = np.bincount(cle, w, taille).reshape(nc, nm, N_LA)
    H = ndimage.gaussian_filter(H, (SIG_C / D_C, SIG_M / D_M, 0), mode='constant', truncate=3.0)
    tot = H.sum(2)
    cum = np.cumsum(H, 2) / np.maximum(tot, 1e-300)[..., None]
    out = {'nc': nc, 'nm': nm, 'connu': (tot > SEUIL_POIDS * tot.max()).ravel()}
    for q, nom in ((0.5, 'age'), (0.16, 'lo'), (0.84, 'hi')):
        j = np.minimum((cum < q).sum(2), N_LA - 1)      # case d'âge où la fraction cumulée atteint q
        avant = np.take_along_axis(cum, np.maximum(j - 1, 0)[..., None], 2)[..., 0] * (j > 0)
        dans = np.take_along_axis(cum, j[..., None], 2)[..., 0] - avant
        f = np.clip((q - avant) / np.maximum(dans, 1e-30), 0, 1)
        out[nom] = (10 ** (LA0 + D_LA * (j + f))).ravel()
    # État du modèle retenu pour chaque case : le point de trajectoire le plus proche de (centre de la case, âge médian),
    # distances comptées en incertitudes (SIG_C, SIG_M, SIG_A). Une masse moyenne prise à part de l'âge donnait des
    # couples masse-âge incohérents (Arcturus placé en fin de vie, vu le 13/11/2026).
    c = np.nonzero(out['connu'])[0]
    arbre = cKDTree(np.stack([nu['coul'] / SIG_C, nu['mag'] / SIG_M, np.log10(np.maximum(nu['age'], 1.0)) / SIG_A], 1))
    q = np.stack([(C0 + D_C * (c // nm + 0.5)) / SIG_C, (M0 + D_M * (c % nm + 0.5)) / SIG_M, np.log10(out['age'][c]) / SIG_A], 1)
    _, j = arbre.query(q, workers=-1)
    out['tr'], out['eep'] = np.full(nc * nm, -1, np.int64), np.zeros(nc * nm)
    out['tr'][c], out['eep'][c] = nu['tr'][j], nu['eep'][j]
    out['age'][c] = nu['age'][j]
    print(f'  {len(c)} cases du diagramme couvertes par le modèle (lissé)')
    return out


def par_cases(T: ml.Traces, tab: dict, coul: np.ndarray, mag: np.ndarray) -> tuple:
    ic = np.floor((coul - C0) / D_C).astype(np.int64)
    im = np.floor((mag - M0) / D_M).astype(np.int64)
    ok = np.isfinite(coul) & np.isfinite(mag) & (ic >= 0) & (ic < tab['nc']) & (im >= 0) & (im < tab['nm'])
    case = np.where(ok, ic * tab['nm'] + im, 0)
    ok &= tab['connu'][case]
    return np.where(ok, tab['tr'][case], -1), tab['eep'][case], tab['age'][case], tab['lo'][case], tab['hi'][case]


def fourchette(age: np.ndarray, borne: np.ndarray) -> np.ndarray:
    with np.errstate(divide='ignore', invalid='ignore'):
        q = np.abs(np.log10(age / borne)) * 100
    return np.clip(np.nan_to_num(q, nan=255), 0, 255).astype(np.uint8)


def flame(T: ml.Traces, masse: np.ndarray, age: np.ndarray, serrer: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Trace et point d'évolution ; trace -1 si l'âge tombe hors de la trace MIST (serrer : ramené dans la trace)."""
    tr = T.trace(masse)
    eep = np.full(len(tr), np.nan)
    o = np.argsort(tr, kind='stable')
    bornes = np.r_[0, np.nonzero(np.diff(tr[o]))[0] + 1, len(o)]
    ages = T.champ('age')
    for a, b in zip(bornes[:-1], bornes[1:]):
        s = o[a:b]
        k = tr[s[0]]
        n = T.utiles[k]
        x = age[s]
        j = np.clip(np.searchsorted(ages[k, :n], x, side='right') - 1, 0, n - 2)
        f = (x - ages[k, j]) / np.maximum(ages[k, j + 1] - ages[k, j], 1e-30)
        dedans = (x >= ages[k, 0]) & (x <= ages[k, n - 1]) | serrer
        eep[s] = np.where(dedans, j + np.clip(f, 0, 1), np.nan)
    return np.where(np.isfinite(eep), tr, -1), eep


def ecrire(chemin: str, tr: np.ndarray, eep: np.ndarray, source: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> None:
    rec = np.zeros(len(tr), np.dtype([('tr', '<u2'), ('eep', '<u2'), ('f', 'u1'), ('lo', 'u1'), ('hi', 'u1'), ('r', 'u1')]))
    connu = tr >= 0
    rec['tr'] = np.where(connu, tr, 0)
    rec['eep'] = np.where(connu, np.clip(np.rint(np.nan_to_num(eep) * 32), 0, 65535), 0)
    rec['f'] = np.where(connu, source, INCONNU)
    rec['lo'], rec['hi'] = np.where(connu, lo, 255), np.where(connu, hi, 255)
    with open(chemin + '.partiel', 'wb') as f:
        f.write(b'UNIVVIE1' + np.uint64(len(rec)).tobytes())
        f.write(rec.tobytes())
    os.replace(chemin + '.partiel', chemin)
    noms = {INCONNU: 'inconnu', FLAME: 'âge Gaia FLAME', DIAG: 'diagramme, poussière retirée', DIAG_BRUT: 'diagramme, poussière comprise'}
    print(f'-> {chemin} : ' + ', '.join(f'{noms[s]} {int((rec["f"] == s).sum())}' for s in noms))


def lire_ap(dossier: str, ids: np.ndarray) -> dict:
    """Colonnes Gaia (gaia_ap.py) remises dans l'ordre de ids ; NaN pour une étoile absente de la table."""
    cols = ['source_id', 'mass_flame', 'age_flame', 'age_flame_lower', 'age_flame_upper', 'flags_flame', 'ag_gspphot', 'ebpminrp_gspphot']
    tb = pa.concat_tables([pq.read_table(f, columns=cols) for f in sorted(glob.glob(os.path.join(dossier, '*.parquet')))])
    sid = tb.column('source_id').to_numpy()
    o = np.argsort(sid)
    j = np.clip(np.searchsorted(sid, ids, sorter=o), 0, len(sid) - 1)
    k = o[j]
    trouve = sid[k] == ids
    out = {'trouve': trouve}
    for c in cols[1:]:
        if c == 'flags_flame':
            fl = pcp.starts_with(pcp.fill_null(tb.column(c), 'x'), '0').to_numpy(zero_copy_only=False)
            out['flame_ok'] = np.where(trouve, fl[k], False)
        else:
            v = tb.column(c).to_numpy(zero_copy_only=False).astype(np.float64)
            out[c] = np.where(trouve, v[k], np.nan)
    print(f'  {int(trouve.sum())} étoiles sur {len(ids)} trouvées dans la table Gaia')
    return out


def gaia(T: ml.Traces, gaia_bin: str, ids_bin: str, dossier_ap: str, sortie: str) -> None:
    rec = gi.enregistrements(gaia_bin)
    b = np.fromfile(ids_bin, np.uint8)
    ids = b[16:].view('<u8').astype(np.int64)
    if len(ids) != len(rec):
        sys.exit('gaia_ids.bin ne correspond pas à ce fichier d\'étoiles')
    M = rec['m'].astype(np.float64)
    c = rec['c'].astype(np.int64)
    C = np.where(c < 254, BPRP0 + BPRP_PAS * (c + 0.5), np.nan)
    ap = lire_ap(dossier_ap, ids)
    print('  table des cases (Gaia G, BP-RP)')
    tab = table_cases(nuage(T, 'gaia'))
    poussiere = np.isfinite(ap['ag_gspphot']) & np.isfinite(ap['ebpminrp_gspphot'])
    tr, eep, age, alo, ahi = par_cases(T, tab, np.where(poussiere, C - ap['ebpminrp_gspphot'], C),
                                       np.where(poussiere, M - ap['ag_gspphot'], M))
    source = np.where(poussiere, DIAG, DIAG_BRUT)
    lo, hi = fourchette(age, alo), fourchette(age, ahi)
    f_ok = ap['flame_ok'] & np.isfinite(ap['mass_flame']) & np.isfinite(ap['age_flame'])
    ftr, feep = flame(T, np.where(f_ok, ap['mass_flame'], 1.0), np.where(f_ok, ap['age_flame'] * 1e9, 1.0))
    f_ok &= ftr >= 0
    print(f'  FLAME : {int(f_ok.sum())} étoiles placées par leur âge Gaia')
    tr, eep = np.where(f_ok, ftr, tr), np.where(f_ok, feep, eep)
    source = np.where(f_ok, FLAME, source)
    lo = np.where(f_ok, fourchette(ap['age_flame'], ap['age_flame_lower']), lo)
    hi = np.where(f_ok, fourchette(ap['age_flame'], ap['age_flame_upper']), hi)
    ecrire(sortie, tr, eep, source, lo, hi)


def extinction_edenhofer(xyz_ly: np.ndarray) -> np.ndarray:
    """A_V (mag) du Soleil à chaque étoile, mesurée par la carte 3D d'Edenhofer et al. 2024 (grille de la page,
    app/gen/data20.js, pipeline/build_dust.py) ; NaN au-delà de la carte (1,25 kpc). Positions : repère écliptique J2000
    héliocentrique de l'appli, en années-lumière. Même trajet que la page : 64 points du Soleil à l'étoile."""
    import base64
    import json
    import re
    from astropy.coordinates import SkyCoord, GeocentricTrueEcliptic, Galactic, BarycentricMeanEcliptic
    import astropy.units as u
    racine = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    s = open(os.path.join(racine, 'app', 'gen', 'data20.js'), encoding='utf-8').read()
    m = re.search(r'"DUST":', s)
    D = json.JSONDecoder().raw_decode(s, m.end())[0]
    q = np.frombuffer(base64.b64decode(D['q']), np.uint8).reshape(D['nz'], D['ny'], D['nx'])
    dens = np.where(q > 0, 10 ** (D['lo'] + (q.astype(np.float64) - 1) / 254 * D['span']), 0.0)
    # écliptique J2000 -> galactique : trois axes passés par astropy (écliptique moyen J2000 = repère de l'appli)
    axes = SkyCoord(lon=[0, 90, 0] * u.deg, lat=[0, 0, 90] * u.deg,
                    frame=BarycentricMeanEcliptic(equinox='J2000')).transform_to(Galactic())
    R = np.stack([axes.cartesian.x.value, axes.cartesian.y.value, axes.cartesian.z.value], 1)      # lignes : axes écl. en galactique
    g = (xyz_ly / 3.26156) @ R
    av = np.zeros(len(g))
    cell, nx, ny, nz = D['cell'], D['nx'], D['ny'], D['nz']
    for t in (np.arange(64) + 0.5) / 64:
        p = g * t
        i = np.floor(p[:, 0] / cell + nx / 2).astype(np.int64)
        j = np.floor(p[:, 1] / cell + ny / 2).astype(np.int64)
        k = np.floor(p[:, 2] / cell + nz / 2).astype(np.int64)
        ok = (i >= 0) & (i < nx) & (j >= 0) & (j < ny) & (k >= 0) & (k < nz)
        av += np.where(ok, dens[np.clip(k, 0, nz - 1), np.clip(j, 0, ny - 1), np.clip(i, 0, nx - 1)], 0.0)
    av *= np.linalg.norm(g, axis=1) / 64
    return np.where(np.linalg.norm(g, axis=1) <= D['rmax'], av, np.nan)


def principal(T: ml.Traces, etoiles_bin: str, sortie: str) -> None:
    b = np.fromfile(etoiles_bin, np.uint8)
    n = int(b[8:16].view('<u8')[0])
    n_main = int(b[16:20].view('<u4')[0])
    col = (n * 4 + 63) // 64 * 64
    mag = b[64 + 3 * col:64 + 3 * col + 4 * n].view('<f4').astype(np.float64)
    bv = b[64 + 4 * col:64 + 4 * col + 4 * n].view('<f4').astype(np.float64)
    # Seul le catalogue principal (V, B-V) est dessiné à côté de gaia.bin (commun.h, mainOnly) ; le reste du fichier
    # (catalogue Gaia de la page, déjà dans gaia.bin) est laissé « inconnu ».
    print(f'  {n} étoiles, dont {n_main} du catalogue principal (V, B-V) ; table des cases (Johnson V, B-V)')
    tab_v = table_cases(nuage(T, 'johnson'))
    xyz = np.stack([b[64 + a * col:64 + a * col + 4 * n_main].view('<f4').astype(np.float64) for a in range(3)], 1)
    av = extinction_edenhofer(xyz)
    mesure = np.isfinite(av)
    av = np.nan_to_num(av)
    print(f'  poussière Edenhofer : {int(mesure.sum())} étoiles dans la carte, A_V médiane {np.median(av[mesure]):.3f}, '
          f'maximale {av.max():.2f}')
    # Cardelli et al. 1989 : E(B-V) = A_V / 3,1
    tr, eep, age, alo, ahi = par_cases(T, tab_v, bv[:n_main] - av / 3.1, mag[:n_main] - av)
    pad = n - n_main
    tr = np.r_[tr, np.full(pad, -1)]
    eep, age, alo, ahi = (np.r_[v, np.zeros(pad)] for v in (eep, age, alo, ahi))
    source = np.r_[np.where(mesure, DIAG, DIAG_BRUT), np.full(pad, DIAG_BRUT)]
    ecrire(sortie, tr, eep, source, fourchette(age, alo), fourchette(age, ahi))


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    mode = sys.argv[1]
    T = ml.Traces(sys.argv[2])
    if mode == 'gaia':
        gaia(T, *sys.argv[3:7])
    elif mode == 'principal':
        principal(T, *sys.argv[3:5])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
