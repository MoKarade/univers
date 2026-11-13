"""Requête ADQL asynchrone sur l'archive Gaia (ESA), sans compte.

Pourquoi asynchrone : la voie synchrone anonyme coupe à 60 s ; les comptages sur 470 millions de lignes
d'astrophysical_parameters prennent plus longtemps.

Usage : python gaia_tap.py "<requête ADQL>" [sortie.csv]
Imprime le résultat (CSV) ou l'écrit dans le fichier donné.
"""
import sys
import time
import urllib.parse
import urllib.request

TAP = 'https://gea.esac.esa.int/tap-server/tap/async'
UA = {'User-Agent': 'univers-pipeline'}


def lancer(adql: str) -> str:
    data = urllib.parse.urlencode({'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'csv',
                                   'PHASE': 'RUN', 'MAXREC': '100000000',      # sans MAXREC : coupé à 50 000 lignes
                                   'QUERY': adql}).encode()
    req = urllib.request.Request(TAP, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.geturl()      # l'archive redirige vers l'adresse du travail


def attendre(job: str, pas: float = 10.0, limite: float = 6 * 3600) -> str:
    debut = time.time()
    while time.time() - debut < limite:
        with urllib.request.urlopen(urllib.request.Request(job + '/phase', headers=UA), timeout=60) as r:
            phase = r.read().decode().strip()
        if phase in ('COMPLETED', 'ERROR', 'ABORTED'):
            return phase
        time.sleep(pas)
    return 'TIMEOUT'


def main() -> None:
    adql = sys.argv[1]
    sortie = sys.argv[2] if len(sys.argv) > 2 else None
    job = lancer(adql)
    print('travail :', job, file=sys.stderr)
    phase = attendre(job)
    if phase != 'COMPLETED':
        with urllib.request.urlopen(urllib.request.Request(job + '/error', headers=UA), timeout=60) as r:
            print(phase, r.read().decode()[:2000], file=sys.stderr)
        sys.exit(1)
    with urllib.request.urlopen(urllib.request.Request(job + '/results/result', headers=UA), timeout=3600) as r:
        texte = r.read()
    if sortie:
        with open(sortie, 'wb') as f:
            f.write(texte)
    else:
        sys.stdout.write(texte.decode())


if __name__ == '__main__':
    main()
