"""Masse, âge et composition mesurés par Gaia DR3 pour les étoiles de l'appli (jeux A et B : parallaxe > 5 erreurs).

Source : table astrophysical_parameters de Gaia DR3 (Creevey et al. 2023 ; Fouesneau et al. 2023), fichiers publiés
par l'ESA sur son CDN (https://cdn.gea.esac.esa.int/Gaia/gdr3/Astrophysical_parameters/astrophysical_parameters/,
3 387 fichiers CSV compressés, 256 Go mesurés le 13/11/2026). Chaque fichier est téléchargé, contrôlé (MD5 publiée),
réduit aux colonnes ci-dessous et aux étoiles de l'appli (gaia_ids.bin, gaia_b_ids.bin), puis effacé : ~4 Go gardés.
Pourquoi pas le service TAP : il arrête après 60 s toute requête anonyme, même sur une petite tranche du ciel (mesuré
le 13/11/2026), ce qui rendait la récupération plus lente que les fichiers complets.

Colonnes gardées : masse et âge FLAME avec leurs bornes (16e-84e centiles), drapeaux et étape d'évolution FLAME,
composition [M/H], température, extinction A_G et rougissement E(BP-RP) de GSP-Phot, luminosité FLAME.
Aucune valeur n'est modifiée (passage en float32 seulement).

Comptage du 13/11/2026 (archive Gaia) : jeu A 97 824 925 étoiles dans la table, dont 59 451 139 avec un âge FLAME ;
jeu B 92 285 172, dont 36 690 310 avec un âge.

Usage : python gaia_ap.py <dossier de sortie> <gaia_ids.bin> [<gaia_b_ids.bin> ...] [--simultanes 6]
Reprise possible. Se met en pause tant qu'un jeu (cod.exe) tourne (règle de Marc).
"""
import argparse
import concurrent.futures as cf
import gzip
import hashlib
import os
import subprocess
import sys
import time
import urllib.request

import numpy as np
import pyarrow as pa
import pyarrow.compute as pcp
import pyarrow.csv as pc
import pyarrow.parquet as pq

CDN = 'https://cdn.gea.esac.esa.int/Gaia/gdr3/Astrophysical_parameters/astrophysical_parameters/'
COLS = ['source_id', 'mass_flame', 'mass_flame_lower', 'mass_flame_upper', 'age_flame', 'age_flame_lower',
        'age_flame_upper', 'flags_flame', 'evolstage_flame', 'mh_gspphot', 'teff_gspphot', 'ag_gspphot',
        'ebpminrp_gspphot', 'lum_flame']
JEUX_DE_PC = ('cod.exe',)


def schema() -> pa.Schema:
    types = {'source_id': pa.int64(), 'flags_flame': pa.string(), 'evolstage_flame': pa.int16()}
    return pa.schema([(c, types.get(c, pa.float32())) for c in COLS])


def jeu_en_cours() -> bool:
    sortie = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.lower()
    return any(j in sortie for j in JEUX_DE_PC)


def lire_ids(chemins: list[str]) -> np.ndarray:
    tous = []
    for c in chemins:
        b = np.fromfile(c, np.uint8)
        if bytes(b[:8]) != b'UNIVIDS1':
            sys.exit(f'{c} : en-tête inconnu')
        tous.append(b[16:].view('<u8').astype(np.int64))
    return np.unique(np.concatenate(tous))


def lignes_entete(chemin: str) -> int:
    n = 0
    with gzip.open(chemin, 'rt') as f:
        for ligne in f:
            if not ligne.startswith('#'):
                return n
            n += 1
    return n


def un_fichier(sortie: str, nom: str, attendu: str, ids: np.ndarray) -> tuple[str, int, float]:
    final = os.path.join(sortie, nom.replace('.csv.gz', '.parquet'))
    if os.path.exists(final):
        return nom, -1, 0.0
    while jeu_en_cours():
        time.sleep(120)
    gz = os.path.join(sortie, 'en_cours_' + nom)
    t = time.time()
    for essai in range(6):
        try:
            md5 = hashlib.md5()
            with urllib.request.urlopen(urllib.request.Request(CDN + nom, headers={'User-Agent': 'univers-pipeline'}),
                                        timeout=600) as r, open(gz, 'wb') as f:
                while b := r.read(1 << 22):
                    f.write(b)
                    md5.update(b)
            if md5.hexdigest() != attendu:
                raise RuntimeError('somme MD5 différente de celle publiée')
            sch = schema()
            tb = pc.read_csv(gz, read_options=pc.ReadOptions(skip_rows=lignes_entete(gz), block_size=1 << 26),
                             convert_options=pc.ConvertOptions(include_columns=COLS, null_values=['null', ''],
                                                               column_types={f.name: f.type for f in sch}))
            tb = tb.select(COLS).cast(sch)
            sid = tb.column('source_id').to_numpy()
            j = np.clip(np.searchsorted(ids, sid), 0, len(ids) - 1)
            tb = tb.filter(pa.array(ids[j] == sid))      # seulement les étoiles dessinées une à une par l'appli
            pq.write_table(tb, final + '.part', compression='zstd')
            os.replace(final + '.part', final)
            os.remove(gz)
            return nom, tb.num_rows, time.time() - t
        except Exception as e:      # coupure réseau ou fichier abîmé : on recommence ce fichier, l'erreur est dite
            print(f'{nom} essai {essai} : {str(e)[:200]}', flush=True)
            time.sleep(20 * (essai + 1))
    raise SystemExit(f'{nom} : échec après 6 essais')


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    p = argparse.ArgumentParser()
    p.add_argument('sortie')
    p.add_argument('ids', nargs='+')
    p.add_argument('--simultanes', type=int, default=6)
    a = p.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    ids = lire_ids(a.ids)
    print(f'{len(ids)} étoiles de l\'appli', flush=True)
    liste = urllib.request.urlopen(CDN + '_MD5SUM.txt', timeout=120).read().decode().split('\n')
    fichiers = [(l.split()[1], l.split()[0]) for l in liste if l.strip().endswith('.csv.gz')]
    t0, total = time.time(), 0
    with cf.ThreadPoolExecutor(a.simultanes) as ex:
        futurs = [ex.submit(un_fichier, a.sortie, n, m, ids) for n, m in fichiers]
        for k, fu in enumerate(cf.as_completed(futurs)):
            nom, lignes, duree = fu.result()
            total += max(lignes, 0)
            print(f'{k + 1}/{len(fichiers)} {nom} {"déjà là" if lignes < 0 else f"{lignes} étoiles en {duree:.0f} s"} '
                  f'(cumul {total}, {time.time() - t0:.0f} s)', flush=True)
    print('FIN', flush=True)


if __name__ == '__main__':
    main()
