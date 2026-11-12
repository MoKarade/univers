#!/usr/bin/env python3
"""Catalogue NGC/IC (OpenNGC) pour la recherche par nom -> <raw>/openngc.json, fichier déposé à part de la page.

Source : OpenNGC, Mattia Verga, https://github.com/mattiaverga/OpenNGC (database_files/NGC.csv et addendum.csv),
licence CC BY-SA 4.0. Contournement de la recherche SIMBAD en direct : la page en ligne ne peut appeler aucun serveur
extérieur, et le CDS (Strasbourg) était en panne le 11/11/2026.

Par objet : [noms affichés, type, AD (degrés), Déc (degrés), magnitude B, grand axe (minutes d'arc), z, constellation, lien].
- z : décalage héliocentrique d'OpenNGC (NED) ramené au repère du Groupe local par la même formule que les relevés
  de la page (Yahil et al. 1977, pipeline/build_data2.py, lg_frame), pour tomber au même endroit qu'eux.
- lien : ['n', i] ou ['l', i] quand l'objet est une galaxie que la page a déjà, à distance mesurée (DATA.NEAR, Karachentsev ;
  DATA.LOCAL, Groupe local), associée par position (moins de 1,5 minute d'arc, comme pour Cosmicflows-4). La page ouvre
  alors sa fiche à elle au lieu d'en créer une seconde.
- Objets « Dup » (doublons d'un autre numéro) et « NonEx » (inexistants) écartés.
- Noms : « NGC 1300 », « IC 434 », « M 104 », puis les noms usuels du catalogue (en anglais).
- Une valeur absente reste absente (null).

Usage : python pipeline/sources/build_openngc.py <dossier_raw>
"""
import csv
import json
import math
import os
import re
import sys

import build_cf4

CKMS = 299792.458
# matrice équatorial -> galactique (même valeur que pipeline/build_data2.py, A_GAL)
A_GAL = [[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132], [0.4941094278755837, -0.4448296299600112, 0.7469822444972189], [-0.8676661490190047, -0.1980763734312015, 0.4559837761750669]]

ECARTES = {'Dup', 'NonEx'}


def sexa(s, heures):
    """« 00:08:27.05 » -> degrés (×15 pour les heures)."""
    if not s:
        return None
    sg = -1 if s.strip().startswith('-') else 1
    h, m, x = (abs(float(p)) for p in s.replace('+', '').replace('-', '').split(':'))
    v = sg * (h + m / 60 + x / 3600)
    return round(v * (15 if heures else 1), 5)


def nombre(s):
    try:
        return float(s) if s not in ('', None) else None
    except ValueError:
        return None


def nom_propre(n):
    """« NGC0224 » -> « NGC 224 », « IC0434 » -> « IC 434 », « NGC5194A » -> « NGC 5194A »."""
    m = re.match(r'^(NGC|IC)0*(\d+)(.*)$', n)
    return '%s %s%s' % (m.group(1), m.group(2), m.group(3).strip()) if m else n


def z_groupe_local(ra, dec, z):
    """Comme lg_frame de build_data2.py : z + (−79 gx + 296 gy − 36 gz) / c, g = direction en coordonnées galactiques."""
    a, d = math.radians(ra), math.radians(dec)
    e = (math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d))
    g = [sum(A_GAL[k][j] * e[j] for j in range(3)) for k in range(3)]
    return z + (-79.0 * g[0] + 296.0 * g[1] - 36.0 * g[2]) / CKMS


def lire(chemin):
    return list(csv.DictReader(open(chemin, encoding='utf-8'), delimiter=';'))


def main(raw):
    d = os.path.join(raw, 'openngc')
    lignes = lire(os.path.join(d, 'NGC.csv')) + lire(os.path.join(d, 'addendum.csv'))
    out, ecartes = [], 0
    for r in lignes:
        if r['Type'] in ECARTES:
            ecartes += 1
            continue
        ra, dec = sexa(r['RA'], True), sexa(r['Dec'], False)
        if ra is None or dec is None:
            ecartes += 1
            continue
        noms = [nom_propre(r['Name'])]
        if r.get('M'):
            noms.append('M %d' % int(r['M']))
        noms += [c.strip() for c in (r.get('Common names') or '').split(',') if c.strip()]
        z = nombre(r.get('Redshift'))
        z = None if z is None else round(z_groupe_local(ra, dec, z), 6)
        out.append([' · '.join(noms), r['Type'], ra, dec, nombre(r.get('B-Mag')), nombre(r.get('MajAx')), z, r.get('Const') or None, None])
    # liens vers les galaxies que la page a déjà (position à moins de 1,5')
    near, _, local, _ = build_cf4.galaxies_de_la_page()
    gal = [[0, o[2], o[3]] for o in out]
    galaxies = {'G', 'GPair', 'GTrpl', 'GGroup'}
    for tag, dirs in (('n', near), ('l', local)):
        for i, k in enumerate(build_cf4.associer(dirs, gal)):
            if k is not None and out[k][1] in galaxies and out[k][8] is None:
                out[k][8] = [tag, i]
    print('liens vers les galaxies de la page : %d proches, %d du Groupe local'
          % (sum(1 for o in out if o[8] and o[8][0] == 'n'), sum(1 for o in out if o[8] and o[8][0] == 'l')))
    print('OpenNGC : %d lignes lues, %d gardées, %d écartées (doublons, inexistants, sans position) ; %d avec z ; %d Messier'
          % (len(lignes), len(out), ecartes, sum(1 for o in out if o[6] is not None), sum(1 for o in out if ' · M ' in o[0] + ' ')))
    m = {o[0].split(' · ')[0]: o for o in out}
    for nom, ra, dec in (('NGC 224', 10.68, 41.27), ('NGC 4594', 189.998, -11.62), ('NGC 1976', 83.82, -5.39)):
        o = m.get(nom)
        ok = o and abs(o[2] - ra) < 0.05 and abs(o[3] - dec) < 0.05
        print('  contrôle %-9s %s' % (nom, o[:4] if o else 'absent'))
        if not ok:
            raise SystemExit('contrôle de position en échec : rien écrit')
    chemin = os.path.join(raw, 'openngc.json')
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'src': 'OpenNGC (Mattia Verga), CC BY-SA 4.0', 'cols': ['noms', 'type', 'ra', 'dec', 'bmag', 'majax', 'z_groupe_local', 'const', 'lien'], 'o': out},
                  f, ensure_ascii=False, separators=(',', ':'))
    print('écrit', chemin, os.path.getsize(chemin), 'octets')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'univers-raw'))
