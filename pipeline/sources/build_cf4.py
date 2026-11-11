#!/usr/bin/env python3
"""Distances Cosmicflows-4 et méthode de mesure -> app/gen/data17.js (clé DATA.CF4).

Source : Tully et al. 2023, ApJ 944, 94, table 2 « Distances of individual galaxies »
(55 874 galaxies), VizieR J/ApJ/944/94 (CDS), doi:10.26093/cds/vizier.19440094.
Libre d'usage avec citation de l'article et de l'Extragalactic Distance Database (Tully et al. 2009).

Pour chaque galaxie : numéro PGC, position, vitesse dans le référentiel du fond diffus,
module de distance moyen et, méthode par méthode, le module publié et son incertitude.
Une méthode sans valeur publiée est simplement absente.

Usage : python pipeline/sources/build_cf4.py <dossier_raw>   (télécharge la table si absente)
"""
import json
import os
import sys
import urllib.request

SERVEURS = ['https://vizier.cds.unistra.fr', 'https://vizier.cfa.harvard.edu']
REQUETE = ('/viz-bin/asu-tsv?-source=J/ApJ/944/94/table2&-out.max=unlimited&-out.all'
           '&-out.add=_RAJ2000,_DEJ2000&-out.form=mini')
FICHIER = 'cf4_table2.tsv'
NB_ATTENDU = 55874


def telecharger(chemin):
    for s in SERVEURS:
        try:
            with urllib.request.urlopen(s + REQUETE, timeout=300) as r:
                txt = r.read().decode('utf-8')
        except OSError as err:
            print('échec', s, err)
            continue
        if 'QUERY_STATUS=ERROR' in txt or '\nPGC' not in txt and '\t' not in txt:
            print('réponse en erreur depuis', s)
            continue
        with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
            f.write(txt)
        print('téléchargé depuis', s)
        return
    raise SystemExit('Cosmicflows-4 injoignable sur tous les serveurs VizieR : réessayer plus tard.')


def lire(chemin):
    """Table TSV de VizieR : en-tête, ligne d'unités, ligne de tirets, puis les données."""
    lignes = [l for l in open(chemin, encoding='utf-8').read().split('\n') if l and not l.startswith('#')]
    entete = [c.strip() for c in lignes[0].split('\t')]
    donnees = [l.split('\t') for l in lignes[3:]]
    return entete, donnees


def nombre(x):
    x = x.strip()
    return float(x) if x else None


def main(raw):
    chemin = os.path.join(raw, FICHIER)
    if not os.path.exists(chemin) or 'QUERY_STATUS=ERROR' in open(chemin, encoding='utf-8').read():
        telecharger(chemin)
    entete, donnees = lire(chemin)
    print('colonnes :', entete)
    i = {c: k for k, c in enumerate(entete)}
    # Colonnes de module de distance par méthode : « DMxxx » avec leur erreur « e_DMxxx ».
    methodes = [c for c in entete if c.startswith('DM') and c != 'DM']
    print('méthodes :', methodes)
    gal = []
    for r in donnees:
        if len(r) < len(entete):
            continue
        m = {}
        for c in methodes:
            v = nombre(r[i[c]])
            if v is not None:
                e = nombre(r[i['e_' + c]]) if 'e_' + c in i else None
                m[c[2:]] = [v, e]
        gal.append([int(r[i['PGC']]), round(float(r[i['_RAJ2000']]), 5), round(float(r[i['_DEJ2000']]), 5),
                    int(r[i['Vcmb']]), nombre(r[i['DM']]), nombre(r[i['e_DM']]), m])
    print('galaxies lues : %d (attendu %d)' % (len(gal), NB_ATTENDU))
    if len(gal) != NB_ATTENDU:
        raise SystemExit('nombre de galaxies inattendu : rien écrit')
    payload = {
        'CF4_COLS': ['pgc', 'ra', 'dec', 'vcmb', 'dm', 'e_dm', 'methodes'],
        'CF4': gal,
        'CF4_SRC': 'Cosmicflows-4, Tully et al. 2023 (ApJ 944, 94), VizieR J/ApJ/944/94',
    }
    out = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'gen', 'data17.js')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('Object.assign(DATA, ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ');\n')
    print('écrit', os.path.normpath(out), os.path.getsize(out), 'octets')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'univers-raw'))
