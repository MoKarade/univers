#!/usr/bin/env python3
"""Refait la lumière des étoiles du MODÈLE (vl_etoiles.bin) sans compter deux fois la lumière Gaia (lumiere_hors_gaia.py).

Rien d'autre ne change : mêmes étoiles, mêmes places, mêmes vitesses, même lumière entière (vl_etoiles.lum). Seule la
lumière RANGÉE (magnitude de vl_etoiles.bin, ce que l'appli montre quand Gaia est allumé) est recalculée. Comme chaque
feuille est rangée de la plus brillante à la plus faible, l'ordre dans une feuille peut changer : vl_etoiles.ordre et
vl_etoiles.lum (un nombre par étoile, dans l'ordre de l'appli) sont permutés de la même façon.

Usage : python vl_lumiere_hors_gaia.py <dossier des données (vl_etoiles.*, gaia.bin, gaia_b.bin, etoiles.bin,
        gaia_agrege.bin)> <dossier de sortie>
Écrit dans le dossier de sortie : vl_etoiles.bin, vl_etoiles.ordre, vl_etoiles.lum, vl_lumiere_hors_gaia.json (mesures).
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')
import json, os, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voie_lactee as v
import lumiere_hors_gaia as lhg
from gaia_convertir import TRANCHES, TRANCHE0, TRANCHE_L

M_SOL_V = 4.83      # etoiles_visibles.py, film_etoiles.h
REC = np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('m', '<f2'), ('c', 'u1'), ('f', 'u1')])
FE = np.dtype([('min', '<f4', 3), ('n', '<u4'), ('max', '<f4', 3), ('r0', '<u4'), ('premier', '<u8'), ('r1', '<u8')])
RES = np.dtype([('c', '<f4', 3), ('r', '<f4'), ('lum', '<f4', TRANCHES), ('couleur', '<f4', TRANCHES)])


def lire(chemin):
    """Les quatre blocs de vl_etoiles.bin (format de etoiles_visibles.ecrire_gaia), alignés sur 64 octets."""
    raw = np.fromfile(chemin, np.uint8)
    n = int(raw[8:16].view('<u8')[0]); nf = int(raw[16:20].view('<u4')[0])
    blocs, o = [], 4096
    for dt, k in ((FE, nf), (REC, n), (np.dtype(('<i2', 4)), n), (RES, nf)):
        b = dt.itemsize * k
        blocs.append(np.frombuffer(raw[o:o + b].tobytes(), dt).copy())
        o += b + (-b % 64)
    assert o == len(raw), 'taille inattendue de vl_etoiles.bin'
    return raw[:4096].tobytes(), blocs


def cases(p_ecl_ly, ecl2gal, sun):
    g = (p_ecl_ly @ ecl2gal.T) / v.LY_PER_PC / 1e3 + sun
    i = np.floor((g[:, 0] + v.HX) / (2 * v.HX) * v.NX).astype(np.int64)
    j = np.floor((g[:, 1] + v.HX) / (2 * v.HX) * v.NY).astype(np.int64)
    k = np.floor((g[:, 2] + v.HZ) / (2 * v.HZ) * v.NZ).astype(np.int64)
    ok = (i >= 0) & (i < v.NX) & (j >= 0) & (j < v.NY) & (k >= 0) & (k < v.NZ)
    return np.where(ok, (k * v.NY + j) * v.NX + i, -1), g


def anneaux(sun, G, Mf, Mv):
    """Bilan dans le plan (|z| < 300 pc) par anneau autour du Soleil : (Gaia + modèle montré) / modèle entier."""
    x, y, z = v.axes(v.NX, v.HX), v.axes(v.NY, v.HX), v.axes(v.NZ, v.HZ)
    Z, Y, X = np.meshgrid(z, y, x, indexing='ij')
    d = np.hypot(X - sun[0], Y - sun[1]).ravel(); plan = (np.abs(Z) < 0.3).ravel()
    out = []
    for a, b in ((0, .5), (.5, 1), (1, 2), (2, 3), (3, 4), (4, 6), (6, 10)):
        s = plan & (d >= a) & (d < b)
        out.append(dict(kpc=[a, b], rapport=float((G[s].sum() + Mv[s].sum()) / max(Mf[s].sum(), 1e-30))))
    return out


def main():
    src, sortie = sys.argv[1:3]
    t0 = time.time()
    head, (fe, rec, vel, res) = lire(os.path.join(src, 'vl_etoiles.bin'))
    n = len(rec)
    lum = np.fromfile(os.path.join(src, 'vl_etoiles.lum'), '<f4').astype(np.float64)
    ordre = np.fromfile(os.path.join(src, 'vl_etoiles.ordre'), '<u4')
    assert len(lum) == n and len(ordre) == n, 'vl_etoiles.lum / .ordre ne correspondent pas à vl_etoiles.bin'
    comp = (vel[:, 3].astype(np.int32) >> 4) & 15
    D = v.data_keys(['M_GAL2ECL', 'SGRA_GAL'])
    ecl2gal = np.array(D['M_GAL2ECL']).T
    sgra = np.array(D['SGRA_GAL']) / np.linalg.norm(D['SGRA_GAL']); sun = -v.R0 * sgra
    N = v.NX * v.NY * v.NZ
    c, _ = cases(np.stack([rec['x'], rec['y'], rec['z']], 1).astype(np.float64), ecl2gal, sun)
    retirable = (c >= 0) & (comp != 6)      # halo d'étoiles : rien n'est retiré (comme etoiles_visibles.py)
    Mf = np.bincount(c[retirable], lum[retirable], N)
    avant = 10 ** (-0.4 * (rec['m'].astype(np.float64) - M_SOL_V))
    Mv_avant = np.bincount(c[retirable], avant[retirable], N)
    print(f'{n} étoiles du modèle lues ; lumière entière {lum.sum():.4e} L☉, rangée avant {avant.sum():.4e} ({time.time() - t0:.0f} s)')

    x, y, z = v.axes(v.NX, v.HX), v.axes(v.NY, v.HX), v.axes(v.NZ, v.HZ)
    gaia = ','.join(os.path.join(src, f) for f in ('gaia.bin', 'gaia_b.bin') if os.path.exists(os.path.join(src, f)))
    cat, ng = v.lumiere_cataloguee(gaia, os.path.join(src, 'etoiles.bin'), ecl2gal, sun, x, y, z, os.path.join(src, 'gaia_agrege.bin'))
    Gm = cat * (100.0 * 100.0 * 50.0)      # L☉ par case, telle que mesurée (poussière comprise)
    G = Gm.ravel()      # telle que mesurée (lumiere_hors_gaia.py dit pourquoi pas désassombrie)
    print(f'{ng} étoiles Gaia ; lumière mesurée {Gm.sum():.4e} L☉ ({time.time() - t0:.0f} s)')

    ancien_exces = float(np.maximum(G - Mf, 0).sum())
    retrait, reste = lhg.retrait_lisse(Mf.reshape(v.NZ, v.NY, v.NX), G.reshape(v.NZ, v.NY, v.NX))
    part = lhg.part_gardee(Mf, retrait.ravel())
    lum_vue = np.where(retirable, lum * part[np.maximum(c, 0)], lum)
    Mv = np.bincount(c[retirable], lum_vue[retirable], N)
    print(f'excès sans retrait lissé : {ancien_exces:.3e} L☉ ({ancien_exces / G.sum():.1%} de Gaia) ; après : {reste:.3e} '
          f'({reste / G.sum():.2%}) ({time.time() - t0:.0f} s)')

    M = M_SOL_V - 2.5 * np.log10(np.maximum(lum_vue, 1e-6))
    # rangement dans chaque feuille, de la plus brillante à la plus faible (gaia.h lit les premières de chaque feuille)
    num = np.repeat(np.arange(len(fe)), fe['n'].astype(np.int64))
    assert np.array_equal(fe['premier'].astype(np.int64), np.concatenate([[0], np.cumsum(fe['n'].astype(np.int64))[:-1]]))
    o = np.lexsort((M, num))
    rec, vel, M, ordre, lum = rec[o], vel[o], M[o], ordre[o], lum[o]
    rec['m'] = M
    lumi = 10 ** (-0.4 * rec['m'].astype(np.float64))
    pas = rec['c'].astype(np.float64)
    tr = np.clip(np.floor((rec['m'].astype(np.float64) - TRANCHE0) / TRANCHE_L), 0, TRANCHES - 1).astype(np.int64)
    cle = num * TRANCHES + tr; nfe = len(fe) * TRANCHES
    Lc = np.bincount(cle, lumi, nfe)
    res['lum'] = Lc.reshape(-1, TRANCHES)
    res['couleur'] = np.where(Lc > 0, np.bincount(cle, lumi * pas, nfe) / np.maximum(Lc, 1e-300), 255).reshape(-1, TRANCHES)
    Lf = np.bincount(num, lumi, len(fe))
    for a, k in enumerate('xyz'): res['c'][:, a] = np.bincount(num, lumi * rec[k].astype(np.float64), len(fe)) / np.maximum(Lf, 1e-300)

    os.makedirs(sortie, exist_ok=True)
    chemin = os.path.join(sortie, 'vl_etoiles.bin')
    with open(chemin + '.partiel', 'wb') as f:
        f.write(head)
        for b in (fe.tobytes(), rec.tobytes(), vel.tobytes(), res.tobytes()): f.write(b + b'\0' * (-len(b) % 64))
    os.replace(chemin + '.partiel', chemin)
    ordre.astype('<u4').tofile(os.path.join(sortie, 'vl_etoiles.ordre'))
    lum.astype('<f4').tofile(os.path.join(sortie, 'vl_etoiles.lum'))
    bilan = dict(date=time.strftime('%Y-%m-%d'), etoiles_modele=n, etoiles_gaia=ng,
                 lumiere_entiere=float(lum.sum()), lumiere_rangee_avant=float(avant.sum()), lumiere_rangee_apres=float(lum_vue.sum()),
                 gaia_mesuree=float(Gm.sum()),
                 exces_avant=ancien_exces, exces_apres=reste,
                 anneaux_avant=anneaux(sun, G, Mf, Mv_avant), anneaux_apres=anneaux(sun, G, Mf, Mv))
    with open(os.path.join(sortie, 'vl_lumiere_hors_gaia.json'), 'w', encoding='utf-8') as f: json.dump(bilan, f, ensure_ascii=False, indent=1)
    for a, b in zip(bilan['anneaux_avant'], bilan['anneaux_apres']):
        print(f"  {a['kpc'][0]:>4}-{a['kpc'][1]:<4} kpc : affiché / attendu {a['rapport']:.3f} -> {b['rapport']:.3f}")
    print(f'-> {sortie} ({time.time() - t0:.0f} s)')


if __name__ == '__main__':
    main()
