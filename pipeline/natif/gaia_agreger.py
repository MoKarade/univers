#!/usr/bin/env python3
"""Lumière de toutes les autres sources de Gaia DR3, additionnée sur le serveur de l'ESA par case de ciel et de distance.

Les 98 millions d'étoiles à distance sûre (parallaxe / erreur > 10) sont dessinées une à une (gaia.bin). Les autres
(environ 1,7 milliard) ont une distance mal mesurée ou pas de parallaxe : leur lumière G est additionnée, sans modèle,
par case :
- ciel : pixel HEALPix de niveau 7 (emboîté, 196 608 pixels de 0,21 deg²), tiré du numéro de la source ;
- distance : tranche de parallaxe, pb = floor(10 log10(parallaxe en mas)) (un dixième de décade) ;
  parallaxe nulle, négative ou absente : distance inconnue (case « ciel seul », pb = -999).
Par case : nombre de sources, somme des flux 10^(-0,4 G), somme des flux × BP-RP et des flux dont BP-RP existe (couleur
moyenne pondérée), somme des flux × erreur relative de parallaxe (incertitude moyenne de la distance de la case).

Requêtes asynchrones (une par morceau de ciel, comme gaia_telecharger.py), au format FITS, avec MAXREC (sans lui le
service coupe sans prévenir). Reprise après coupure : les parts déjà là sont gardées.

Usage : python gaia_agreger.py <dossier> [--parts 1024] [--simultanes 8]
"""
import argparse, concurrent.futures as cf, os, sys, time

import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')      # accents lisibles dans la console Windows
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gaia_telecharger as gt

NIVEAU = 7
DIV = 2 ** 35 * 4 ** (12 - NIVEAU)      # source_id // DIV = pixel HEALPix de niveau 7
F = 'POWER(10, -0.4*phot_g_mean_mag)'
AGREGATS = (f'COUNT(*) AS n, SUM({F}) AS f, SUM({F}*bp_rp) AS fc, SUM({F}*(bp_rp*0+1)) AS fcn')


def requetes(debut, fin):
    base = f'FROM gaiadr3.gaia_source WHERE source_id >= {debut} AND source_id < {fin} AND phot_g_mean_mag IS NOT NULL'
    a = (f'SELECT source_id/{DIV} AS hp, FLOOR(10*LOG10(parallax)) AS pb, {AGREGATS}, SUM({F}*parallax_error/parallax) AS fe '
         f'{base} AND parallax > 0 AND parallax_over_error <= 10 GROUP BY hp, pb')
    b = (f'SELECT source_id/{DIV} AS hp, {AGREGATS} {base} AND (parallax IS NULL OR parallax <= 0) GROUP BY hp')
    return a, b


def une_part(dossier, k, parts):
    debut, fin = k * gt.HPX12 // parts * gt.UNITE, (k + 1) * gt.HPX12 // parts * gt.UNITE
    tailles = 0
    for nom, q in zip(('distance', 'ciel'), requetes(debut, fin)):
        final = os.path.join(dossier, f'{nom}_{k:04d}.fits')
        if os.path.exists(final): continue
        for essai in range(6):
            try:
                r = gt.http(gt.TAP + '/async', dict(REQUEST='doQuery', LANG='ADQL', FORMAT='fits', PHASE='RUN', MAXREC=str(gt.MAXREC), QUERY=q))
                job = (r.geturl() if '/async/' in r.geturl() else r.headers['Location']).split('?')[0]
                while True:
                    phase = gt.http(job + '/phase').read().decode().strip()
                    if phase == 'COMPLETED': break
                    if phase in ('ERROR', 'ABORTED'): raise RuntimeError(gt.http(job + '/error').read().decode()[:300])
                    time.sleep(3)
                tmp = final + '.partiel'
                with gt.http(job + '/results/result', timeout=600) as src, open(tmp, 'wb') as dst: dst.write(src.read())
                if gt.lignes_fits(tmp) >= gt.MAXREC: raise RuntimeError('coupée par la limite')
                os.replace(tmp, final)
                break
            except Exception as e:
                print(f'part {k} {nom} essai {essai + 1} : {e}', flush=True)
                time.sleep(10 * (essai + 1))
        else:
            return k, 'ÉCHEC', tailles
        tailles += os.path.getsize(final)
    return k, 'ok', tailles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dossier'); ap.add_argument('--parts', type=int, default=1024); ap.add_argument('--simultanes', type=int, default=8)
    a = ap.parse_args()
    os.makedirs(a.dossier, exist_ok=True)
    t0, total, echecs = time.time(), 0, []
    with cf.ThreadPoolExecutor(a.simultanes) as ex:
        for k, etat, taille in ex.map(lambda k: une_part(a.dossier, k, a.parts), range(a.parts)):
            total += taille
            if etat == 'ÉCHEC': echecs.append(k)
            if (k + 1) % 64 == 0 or etat == 'ÉCHEC': print(f'{k + 1}/{a.parts} {etat} (cumul {total / 1e6:.0f} Mo, {time.time() - t0:.0f} s)', flush=True)
    if echecs: sys.exit(f'parts en échec : {echecs}')


if __name__ == '__main__':
    main()
