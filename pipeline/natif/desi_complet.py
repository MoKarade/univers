#!/usr/bin/env python3
"""TOUTES les galaxies et tous les quasars de DESI DR1 dont le décalage vers le rouge est sûr -> desi_NN.csv.

Pourquoi : la page (et donc l'appli PC) ne gardait que 13,5 % de DESI, tirés au hasard (random_id de 0,45 à 14), pour
tenir dans 16 Mo. Demande de Marc (12/11/2026) : « toutes les données, pas une version allégée ».
Source : Astro Data Lab de NOIRLab, table desi_dr1.zpix (DESI Collaboration 2025, DR1), même filtre que la page :
zwarn = 0 (aucun avertissement du programme d'ajustement), spectype différent de STAR, zcat_primary (un seul spectre
par objet), 0,002 < z < 5,5. Colonnes : identifiant DESI, direction mesurée (moyenne des fibres), z et son erreur, type.
Téléchargé en 50 tranches de random_id (largeur 2), reprise possible : une tranche déjà écrite n'est pas redemandée.
Usage : python desi_complet.py <dossier de sortie>
"""
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TAP = 'https://datalab.noirlab.edu/tap/sync'
UA = {'User-Agent': 'UniversPC/1.0 (visualisation personnelle)'}
REQ = ("SELECT targetid, mean_fiber_ra, mean_fiber_dec, z, zerr, spectype FROM desi_dr1.zpix "
       "WHERE random_id >= {a} AND random_id < {b} AND zwarn = 0 AND z > 0.002 AND z < 5.5 "
       "AND spectype <> 'STAR' AND zcat_primary = 't'")
LARGEUR, TRANCHES = 2, 50


def tranche(sortie: str, k: int) -> None:
    out = os.path.join(sortie, f'desi_{k:02d}.csv')
    if os.path.exists(out):
        return
    q = REQ.format(a=k * LARGEUR, b=(k + 1) * LARGEUR)
    for essai in range(6):
        t = time.time()
        try:
            corps = urllib.parse.urlencode({'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'csv', 'MAXREC': '100000000',
                                            'QUERY': q}).encode()
            n = 0
            with urllib.request.urlopen(urllib.request.Request(TAP, data=corps, headers=UA), timeout=3600) as r, \
                    open(out + '.part', 'wb') as f:
                while c := r.read(1 << 20):
                    f.write(c)
                    n += len(c)
            with open(out + '.part', 'rb') as f:
                tete = f.read(200)
            if not tete.startswith(b'targetid') or n < 100_000:
                print(f'tranche {k} essai {essai} : réponse inattendue {tete[:120]!r}', flush=True)
                time.sleep(30 * (essai + 1))
                continue
            lignes = sum(1 for _ in open(out + '.part', 'rb')) - 1
            os.replace(out + '.part', out)
            print(f'tranche {k + 1}/{TRANCHES} : {lignes} objets, {n / 1e6:.1f} Mo en {time.time() - t:.0f} s', flush=True)
            return
        except Exception as e:      # coupure réseau : on réessaie la même tranche
            print(f'tranche {k} essai {essai} : {str(e)[:160]}', flush=True)
            time.sleep(30 * (essai + 1))
    raise SystemExit(f'tranche {k} : échec après 6 essais')


def main() -> None:
    sortie = sys.argv[1]
    os.makedirs(sortie, exist_ok=True)
    for k in range(TRANCHES):
        tranche(sortie, k)
    print('FIN', flush=True)


if __name__ == '__main__':
    main()
