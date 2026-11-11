#!/usr/bin/env python3
"""Distances Cosmicflows-4 et méthode de mesure -> app/gen/data17.js (clés DATA.CF4_NEAR, DATA.CF4_LOCAL).

Source : Tully et al. 2023, ApJ 944, 94, table 2 « Distances of individual galaxies »
(55 874 galaxies), VizieR J/ApJ/944/94 (CDS), doi:10.26093/cds/vizier.19440094.
Libre d'usage avec citation de l'article et de l'Extragalactic Distance Database (Tully et al. 2009).

Pour chaque galaxie : numéro PGC, position, vitesse dans le référentiel du fond diffus,
module de distance moyen et, méthode par méthode, le module publié et son incertitude.
Une méthode sans valeur publiée est simplement absente.

La table complète (3,6 Mo) ne tient pas dans la page (limite de 16 Mo). On n'embarque que les galaxies qui ont une
fiche dans la page : les galaxies proches (DATA.NEAR, catalogue de Karachentsev) et celles du Groupe local
(DATA.LOCAL), associées par position sur le ciel à moins de ASSOC_ARCMIN minutes d'arc. La table complète est
écrite hors dépôt (<dossier_raw>/cf4_complet.json) pour un chargement à part plus tard.

Usage : python pipeline/sources/build_cf4.py <dossier_raw>   (télécharge la table si absente)
"""
import base64
import json
import math
import os
import struct
import sys
import urllib.request

SERVEURS = ['https://vizier.cds.unistra.fr', 'https://vizier.cfa.harvard.edu']
REQUETE = ('/viz-bin/asu-tsv?-source=J/ApJ/944/94/table2&-out.max=unlimited&-out.all'
           '&-out.add=_RAJ2000,_DEJ2000&-out.form=mini')
FICHIER = 'cf4_table2.tsv'
ASSOC_ARCMIN = 1.5    # rayon d'association ; les positions des catalogues concordent à mieux qu'une minute d'arc [Probable]
RAPPORT_MAX = 3.0      # au-delà, la galaxie CF4 voisine sur le ciel est sans doute une autre galaxie (avant- ou arrière-plan)
EPS = math.radians(84381.448 / 3600.0)   # obliquité J2000, comme pipeline/build_data2.py
NB_ATTENDU = 55877   # lignes de la table VizieR (l'EDD en annonce 55 874 : édition du 02/05/2023 légèrement différente)


def telecharger(chemin):
    for s in SERVEURS:
        try:
            with urllib.request.urlopen(s + REQUETE, timeout=300) as r:
                txt = r.read().decode('utf-8')
        except OSError as err:
            print('échec', s, err)
            continue
        lignes_donnees = sum(1 for l in txt.split('\n') if l and not l.startswith('#'))
        if 'QUERY_STATUS=ERROR' in txt or lignes_donnees < NB_ATTENDU:
            print('réponse incomplète depuis %s (%d lignes)' % (s, lignes_donnees))
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


def ecl_vers_eq(x, y, z):
    """Inverse de RX de pipeline/build_data2.py : écliptique J2000 -> équatorial J2000, puis (ra, dec) en degrés."""
    c, s = math.cos(EPS), math.sin(EPS)
    xe, ye, ze = x, c * y - s * z, s * y + c * z
    r = math.sqrt(xe * xe + ye * ye + ze * ze)
    return math.degrees(math.atan2(ye, xe)) % 360.0, math.degrees(math.asin(ze / r))


def sep_arcmin(a, b):
    ra1, de1, ra2, de2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    c = math.sin(de1) * math.sin(de2) + math.cos(de1) * math.cos(de2) * math.cos(ra1 - ra2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 60.0


def galaxies_de_la_page():
    """Directions (ra, dec) des galaxies proches et du Groupe local, lues dans app/gen/data2.js."""
    s = open(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'gen', 'data2.js'), encoding='utf-8').read()
    d = json.loads(s[len('Object.assign(DATA, '):s.rindex(');')])
    brut = base64.b64decode(d['NEAR'])
    xyz = [struct.unpack_from('<3f', brut, i * 20) for i in range(d['NEAR_N'])]
    near = [ecl_vers_eq(*v) for v in xyz]
    dnear = [math.sqrt(sum(c * c for c in v)) for v in xyz]          # Mpc
    local = [ecl_vers_eq(*o['pos']) if any(o['pos']) else None for o in d['LOCAL']]
    dlocal = [o['d'] for o in d['LOCAL']]                            # Mpc
    return near, dnear, local, dlocal


def coherent(gal, idx, dpage):
    """Écarte une association dont la distance CF4 diffère de plus de RAPPORT_MAX fois de la distance déjà affichée."""
    out, rejet = [], 0
    for k, dp in zip(idx, dpage):
        if k is not None and gal[k][4] is not None and dp > 0:
            r = 10 ** (gal[k][4] / 5 + 1) / 1e6 / dp
            if not (1 / RAPPORT_MAX < r < RAPPORT_MAX):
                k, rejet = None, rejet + 1
        out.append(k)
    return out, rejet


def associer(dirs, gal):
    """Pour chaque direction de la page : indice CF4 le plus proche à moins de ASSOC_ARCMIN, sinon None."""
    grille = {}
    for k, g in enumerate(gal):
        grille.setdefault((int(g[2] + 90) // 1), []).append(k)
    out = []
    for p in dirs:
        best, bd = None, ASSOC_ARCMIN
        if p is not None:
            for bande in (int(p[1] + 90) - 1, int(p[1] + 90), int(p[1] + 90) + 1):
                for k in grille.get(bande, ()):
                    dd = sep_arcmin(p, (gal[k][1], gal[k][2]))
                    if dd < bd:
                        best, bd = k, dd
        out.append(best)
    return out


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
    with open(os.path.join(raw, 'cf4_complet.json'), 'w', encoding='utf-8') as f:
        json.dump(gal, f, separators=(',', ':'))
    near, dnear, local, dlocal = galaxies_de_la_page()
    an, rn = coherent(gal, associer(near, gal), dnear)
    al, rl = coherent(gal, associer(local, gal), dlocal)
    print('associations écartées (distance incohérente) : %d galaxies proches, %d du Groupe local' % (rn, rl))
    garde = lambda k: None if k is None else [gal[k][0], gal[k][4], gal[k][5], gal[k][6]]
    print('associées : %d galaxies proches sur %d, %d du Groupe local sur %d'
          % (sum(k is not None for k in an), len(an), sum(k is not None for k in al), len(al)))
    payload = {
        'CF4_COLS': ['pgc', 'dm', 'e_dm', 'methodes'],
        'CF4_NEAR': [garde(k) for k in an],      # même ordre que DATA.NEAR
        'CF4_LOCAL': [garde(k) for k in al],     # même ordre que DATA.LOCAL
        'CF4_SRC': 'Cosmicflows-4, Tully et al. 2023 (ApJ 944, 94), VizieR J/ApJ/944/94',
    }
    out = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'gen', 'data17.js')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('Object.assign(DATA, ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ');\n')
    print('écrit', os.path.normpath(out), os.path.getsize(out), 'octets')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'univers-raw'))
