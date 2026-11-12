#!/usr/bin/env python3
"""Télécharge les étoiles de Gaia DR3 dont la distance est mesurée à mieux que 10 % (parallaxe / erreur > 10).

Source : archive Gaia de l'ESA, service TAP (https://gea.esac.esa.int/tap-server/tap), table gaiadr3.gaia_source.
Compté le 12 novembre 2026 [Certain] : 98 346 986 étoiles avec parallax_over_error > 10 (192 208 838 au-delà de 5).

Le ciel est découpé en 1024 parts égales par le numéro des sources (source_id // 2^35 = pixel HEALPix de niveau 12,
emboîté : chaque part est un morceau de ciel d'un seul tenant). Une requête asynchrone par part, au format FITS,
quatre à la fois. Une part déjà présente et complète n'est pas redemandée : on peut relancer après une coupure.

Colonnes : source_id, ra, dec (degrés, ICRS, époque J2016.0), parallax (mas), pmra, pmdec (mas/an),
radial_velocity (km/s, absente pour la plupart), phot_g_mean_mag, bp_rp (magnitudes, telles que mesurées,
poussière comprise). Aucune valeur n'est modifiée ici.

Usage : python gaia_telecharger.py <dossier> [--parts 256] [--simultanes 4]
Taille attendue : environ 6 Go.
"""
import argparse, concurrent.futures as cf, os, sys, time, urllib.parse, urllib.request

TAP = 'https://gea.esac.esa.int/tap-server/tap'
COLONNES = 'source_id, ra, dec, parallax, pmra, pmdec, radial_velocity, phot_g_mean_mag, bp_rp'
HPX12 = 12 * 4 ** 12      # pixels HEALPix de niveau 12 sur tout le ciel
MAXREC = 10_000_000      # sans ce paramètre, le service coupe à 50 000 lignes (constaté le 12 novembre 2026)
UNITE = 2 ** 35      # source_id = pixel HEALPix niveau 12 × 2^35 + numéro dans le pixel


def requete(debut, fin):
    return (f'SELECT {COLONNES} FROM gaiadr3.gaia_source '
            f'WHERE source_id >= {debut} AND source_id < {fin} AND parallax_over_error > 10')


def http(url, data=None, timeout=120):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None,
                                 headers={'User-Agent': 'univers-pipeline'})
    return urllib.request.urlopen(req, timeout=timeout)


def lignes_fits(chemin):
    from astropy.io import fits
    with fits.open(chemin) as h: return h[1].header['NAXIS2']


def une_part(dossier, k, parts):
    final = os.path.join(dossier, f'part_{k:04d}.fits')
    if os.path.exists(final): return k, 'déjà là', 0
    debut, fin = k * HPX12 // parts * UNITE, (k + 1) * HPX12 // parts * UNITE
    for essai in range(6):
        try:
            r = http(TAP + '/async', dict(REQUEST='doQuery', LANG='ADQL', FORMAT='fits', PHASE='RUN', MAXREC=str(MAXREC), QUERY=requete(debut, fin)))
            job = r.geturl() if '/async/' in r.geturl() else r.headers['Location']
            job = job.split('?')[0]
            while True:
                phase = http(job + '/phase').read().decode().strip()
                if phase == 'COMPLETED': break
                if phase in ('ERROR', 'ABORTED'): raise RuntimeError(f'part {k} : {phase} : ' + http(job + '/error').read().decode()[:400])
                time.sleep(3)
            tmp = final + '.partiel'
            with http(job + '/results/result', timeout=600) as src, open(tmp, 'wb') as dst:
                while True:
                    b = src.read(1 << 20)
                    if not b: break
                    dst.write(b)
            lignes = lignes_fits(tmp)
            if lignes >= MAXREC: raise RuntimeError(f'part {k} : {lignes} lignes, coupée par la limite')
            os.replace(tmp, final)
            try: urllib.request.urlopen(urllib.request.Request(job, data=b'ACTION=DELETE'), timeout=30)      # libère la place sur le serveur
            except Exception: pass
            return k, 'ok', os.path.getsize(final)
        except Exception as e:
            print(f'part {k} essai {essai + 1} : {e}', flush=True)
            time.sleep(10 * (essai + 1))
    return k, 'ÉCHEC', 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dossier'); ap.add_argument('--parts', type=int, default=1024); ap.add_argument('--simultanes', type=int, default=4)
    a = ap.parse_args()
    os.makedirs(a.dossier, exist_ok=True)
    t0, total, echecs = time.time(), 0, []
    with cf.ThreadPoolExecutor(a.simultanes) as ex:
        for k, etat, taille in ex.map(lambda k: une_part(a.dossier, k, a.parts), range(a.parts)):
            total += taille
            if etat == 'ÉCHEC': echecs.append(k)
            print(f'{k + 1}/{a.parts} {etat} {taille / 1e6:.1f} Mo (cumul {total / 1e9:.2f} Go, {time.time() - t0:.0f} s)', flush=True)
    if echecs: sys.exit(f'parts en échec : {echecs} (relancer : les parts déjà là sont gardées)')


if __name__ == '__main__':
    main()
