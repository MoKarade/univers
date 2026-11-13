#!/usr/bin/env python3
"""TOUTES les sources de Gaia DR3 (1 811 709 771), une à une -> un fichier Parquet par fichier publié par l'ESA.

Pourquoi (demande de Marc, 12/11/2026 : « toutes les données ») : l'appli montre une à une les 98 M étoiles à distance
sûre ; les 1,71 milliard d'autres n'y sont qu'additionnées par case de ciel. Le service TAP de l'ESA coupe les requêtes
anonymes à 60 s (constaté le 12/11/2026) : on lit donc les fichiers complets publiés sur le CDN de l'ESA
(https://cdn.gea.esac.esa.int/Gaia/gdr3/gaia_source/, 3 386 fichiers CSV compressés, ~650 Go, débit mesuré ~50 Mo/s).

Chaque fichier est téléchargé, contrôlé (somme MD5 publiée), lu (pyarrow), réduit aux colonnes ci-dessous puis effacé :
on garde un Parquet compressé (zstd). Aucune valeur n'est modifiée ; les colonnes de mesure passent en float32
(précision de Gaia bien au-dessus), ra et dec restent en float64. Reprise possible : un Parquet présent n'est pas refait.
Colonnes : source_id, ra, dec (ICRS, J2016.0), parallax, parallax_error, pmra, pmra_error, pmdec, pmdec_error,
radial_velocity, radial_velocity_error, phot_g_mean_mag, bp_rp, ruwe.
Usage : python gaia_cdn.py <dossier de sortie> [--simultanes 6]
"""
import argparse
import concurrent.futures as cf
import hashlib
import os
import sys
import time
import urllib.request

import pyarrow as pa
import pyarrow.csv as pc
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding='utf-8')
CDN = 'https://cdn.gea.esac.esa.int/Gaia/gdr3/gaia_source/'
COLS = ['source_id', 'ra', 'dec', 'parallax', 'parallax_error', 'pmra', 'pmra_error', 'pmdec', 'pmdec_error',
        'radial_velocity', 'radial_velocity_error', 'phot_g_mean_mag', 'bp_rp', 'ruwe']
PLAFOND = 22e9      # octets gardés sur le PC en attendant l'envoi au Drive
DEJA_ENVOYES: set[str] = set()      # Parquet déjà rangés sur le Drive (--drive) : pas retéléchargés


def telecharger(url: str, chemin: str) -> str:
    md5 = hashlib.md5()
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'univers-pipeline'}), timeout=600) as r, \
            open(chemin, 'wb') as f:
        while b := r.read(1 << 22):
            f.write(b)
            md5.update(b)
    return md5.hexdigest()


def un_fichier(sortie: str, nom: str, attendu: str) -> tuple[str, int, float]:
    final = os.path.join(sortie, nom.replace('.csv.gz', '.parquet'))
    if os.path.exists(final) or os.path.basename(final) in DEJA_ENVOYES:      # déjà là, ou déjà parti sur le Drive
        return nom, -1, 0.0
    # Place sur le PC (Marc, 12/11/2026) : au-delà de PLAFOND octets en attente dans le dossier, on attend que les lots
    # partent sur le Drive (déplacés par un autre script) avant de télécharger la suite.
    while sum(e.stat().st_size for e in os.scandir(sortie) if e.is_file()) > PLAFOND:
        time.sleep(60)
    gz = os.path.join(sortie, 'en_cours_' + nom)      # finit par .csv.gz : pyarrow décompresse d'après l'extension
    t = time.time()
    for essai in range(6):
        try:
            if telecharger(CDN + nom, gz) != attendu:
                raise RuntimeError('somme MD5 différente de celle publiée')
            tb = pc.read_csv(gz, read_options=pc.ReadOptions(skip_rows=1000, block_size=1 << 26),      # 1000 lignes d'en-tête ECSV
                             convert_options=pc.ConvertOptions(include_columns=COLS, null_values=['null', '']))
            tb = tb.cast(pa.schema([(c, pa.float64() if c in ('ra', 'dec') else pa.int64() if c == 'source_id' else pa.float32())
                                    for c in COLS]))
            pq.write_table(tb, final + '.part', compression='zstd')
            os.replace(final + '.part', final)
            os.remove(gz)
            return nom, tb.num_rows, time.time() - t
        except Exception as e:      # coupure réseau ou fichier abîmé : on recommence ce fichier
            print(f'{nom} essai {essai} : {str(e)[:160]}', flush=True)
            time.sleep(20 * (essai + 1))
    raise SystemExit(f'{nom} : échec après 6 essais')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('sortie')
    ap.add_argument('--simultanes', type=int, default=6)
    ap.add_argument('--drive', help='dossier du Drive où les Parquet finis sont envoyés (vers_drive.py)')
    a = ap.parse_args()
    if a.drive and os.path.isdir(a.drive):
        DEJA_ENVOYES.update(n for n in os.listdir(a.drive) if n.endswith('.parquet'))
        print(f'{len(DEJA_ENVOYES)} fichiers déjà sur le Drive', flush=True)
    os.makedirs(a.sortie, exist_ok=True)
    liste = urllib.request.urlopen(CDN + '_MD5SUM.txt', timeout=120).read().decode().split('\n')
    fichiers = [(l.split()[1], l.split()[0]) for l in liste if l.strip().endswith('.csv.gz')]
    t0, total = time.time(), 0
    with cf.ThreadPoolExecutor(a.simultanes) as ex:
        futurs = [ex.submit(un_fichier, a.sortie, n, m) for n, m in fichiers]
        for k, fu in enumerate(cf.as_completed(futurs)):
            nom, lignes, duree = fu.result()
            total += max(lignes, 0)
            print(f'{k + 1}/{len(fichiers)} {nom} {"déjà là" if lignes < 0 else f"{lignes} sources en {duree:.0f} s"} '
                  f'(cumul {total} sources, {time.time() - t0:.0f} s)', flush=True)
    print('FIN', flush=True)


if __name__ == '__main__':
    main()
