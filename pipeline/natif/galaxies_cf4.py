#!/usr/bin/env python3
"""Galaxies à distance MESURÉE (Cosmicflows-4) avec leur nom (OpenNGC) -> galaxies_cf4.tsv pour l'appli PC.

Pourquoi (demande de Marc, 12/11/2026 : « toutes les données récupérées dans l'application ») : la page avait ces deux
catalogues, l'appli PC non. Les points de galaxies.bin sont placés d'après leur décalage vers le rouge (distance
calculée) ; ces 55 877 galaxies ont en plus une distance mesurée sans passer par le décalage vers le rouge.

Sources (fichiers déjà sur le PC, récupérés pour la page) :
- Cosmicflows-4, Tully et al. 2023, ApJ 944, 94, table 2 (VizieR J/ApJ/944/94) : PGC, direction, module de distance DM
  toutes méthodes et son erreur, modules par méthode (SN Ia, Tully-Fisher, plan fondamental, fluctuations de brillance…) ;
- OpenNGC (Mattia Verga, github.com/mattiaverga/OpenNGC, NGC.csv) : noms NGC/IC/Messier et noms usuels, reliés par PGC.
Calcul : distance = 10^((DM - 25) / 5) Mpc, telle que publiée (échelle de CF4, H0 = 75) ; erreur relative = 0,461 × e_DM.
Repère : écliptique J2000 (obliquité IAU 1976, 84381,448″), comme etoiles.bin. Les galaxies déjà nommées par l'appli
(galaxies_noms.tsv, Groupe local) sont laissées à leur fichier : rien n'est en double à moins de 0,2° et 30 %.
Sortie : nom, x, y, z (années-lumière), texte de la fiche, priorité 9 (nom montré seulement de près ou au survol).
Usage : python galaxies_cf4.py <dossier univers-raw> <galaxies_noms.tsv existant> <dossier de sortie>
"""
import csv
import math
import os
import re
import sys

import numpy as np

MPC_LY = 3.2615637771674333e6
OBLIQ = math.radians(84381.448 / 3600)
METHODES = [('DMsnIa', 'supernovas Ia'), ('DMtf', 'Tully-Fisher'), ('DMfp', 'plan fondamental'),
            ('DMsbf', 'fluctuations de brillance'), ('DMsnII', 'supernovas II'), ('DMtrgb', 'pointe des géantes rouges'),
            ('DMceph', 'céphéides'), ('DMmas', 'maser')]
TYPES = {'G': 'galaxie', 'GPair': 'paire de galaxies', 'GTrpl': 'triplet de galaxies', 'GGroup': 'groupe de galaxies'}


def lire_cf4(chemin: str) -> list[dict]:
    lignes = [l for l in open(chemin, encoding='utf-8', errors='replace') if l.strip() and not l.startswith('#')]
    entete = lignes[0].rstrip('\n').split('\t')
    out = []
    for l in lignes[3:]:      # VizieR : noms, unités, tirets, puis les données
        c = l.rstrip('\n').split('\t')
        if len(c) != len(entete):
            continue
        out.append({k: v.strip() for k, v in zip(entete, c)})
    return out


def lire_openngc(dossier: str) -> dict[int, tuple[str, str]]:
    """PGC -> (nom à afficher, type OpenNGC)."""
    noms: dict[int, tuple[str, str]] = {}
    for f in ('NGC.csv', 'addendum.csv'):
        chemin = os.path.join(dossier, 'openngc', f)
        if not os.path.exists(chemin):
            continue
        for r in csv.DictReader(open(chemin, encoding='utf-8'), delimiter=';'):
            pgc = re.search(r'PGC (\d+)', r.get('Identifiers') or '')
            if not pgc:
                continue
            m = re.match(r'(NGC|IC)0*(\d+)(.*)', r['Name'])      # NGC0224 -> NGC 224
            nom = f'{m.group(1)} {m.group(2)}{m.group(3)}' if m else r['Name']
            if r.get('M'):
                nom = f'M{int(r["M"])} ({nom})'
            noms.setdefault(int(pgc.group(1)),(nom, TYPES.get(r['Type'], 'galaxie')))
    return noms


def lire_coords_openngc(dossier: str) -> dict[int, tuple[float, float]]:
    """PGC -> (ascension droite, déclinaison) en degrés J2000, telles qu'OpenNGC les donne pour la galaxie elle-même."""
    coords: dict[int, tuple[float, float]] = {}
    for f in ('NGC.csv', 'addendum.csv'):
        chemin = os.path.join(dossier, 'openngc', f)
        if not os.path.exists(chemin):
            continue
        for r in csv.DictReader(open(chemin, encoding='utf-8'), delimiter=';'):
            pgc = re.search(r'PGC (\d+)', r.get('Identifiers') or '')
            if not pgc or not r.get('RA') or not r.get('Dec'):
                continue
            h, m, s = (float(x) for x in r['RA'].split(':'))
            sg = -1.0 if r['Dec'].strip().startswith('-') else 1.0
            d, dm, ds = (abs(float(x)) for x in r['Dec'].split(':'))
            coords.setdefault(int(pgc.group(1)), (15.0 * (h + m / 60 + s / 3600), sg * (d + dm / 60 + ds / 3600)))
    return coords


def lire_groupes(chemin: str) -> list[dict]:
    """Cosmicflows-4, table 3 (VizieR J/ApJ/944/94/groups) : distance de chaque groupe, moyenne pondérée de ses membres."""
    if not os.path.exists(chemin):
        return []
    lignes = [l for l in open(chemin, encoding='utf-8', errors='replace') if l.strip() and not l.startswith('#')]
    entete = lignes[0].rstrip('\n').split('\t')
    rangs = (l.rstrip('\n').split('\t') for l in lignes[3:])      # VizieR : noms, unités, tirets, puis les données
    return [dict(zip(entete, (v.strip() for v in c))) for c in rangs if len(c) == len(entete)]


def ecliptique(ra: float, dec: float) -> np.ndarray:
    a, d = math.radians(ra), math.radians(dec)
    x, y, z = math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d)
    return np.array([x, y * math.cos(OBLIQ) + z * math.sin(OBLIQ), -y * math.sin(OBLIQ) + z * math.cos(OBLIQ)])


def main() -> None:
    raw, deja, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    cf4 = lire_cf4(os.path.join(raw, 'cf4_table2.tsv'))
    noms = lire_openngc(raw)
    existants = []
    for l in open(deja, encoding='utf-8'):
        c = l.rstrip('\n').split('\t')
        if len(c) >= 4:
            p = np.array([float(c[1]), float(c[2]), float(c[3])])
            existants.append(p)
    E = np.array(existants)
    En = np.linalg.norm(E, axis=1)
    lignes, doubles, nommees = [], 0, 0
    for r in cf4:
        try:
            dm, edm = float(r['DM']), float(r['e_DM'])
            ra, dec = float(r['_RAJ2000']), float(r['_DEJ2000'])
        except (KeyError, ValueError):
            continue
        d = 10 ** ((dm - 25) / 5) * MPC_LY
        p = ecliptique(ra, dec) * d
        cosang = (E @ p) / (En * d)
        if np.any((cosang > math.cos(math.radians(0.2))) & (np.abs(En / d - 1) < 0.3)):
            doubles += 1
            continue
        pgc = int(r['PGC'])
        nom, genre = noms.get(pgc, (f'PGC {pgc}', 'galaxie'))
        nommees += pgc in noms
        meth = [t for k, t in METHODES if r.get(k)]
        mpc = f'{d / MPC_LY:.1f}'.replace('.', ',')
        mal = f'{d / 1e6:,.0f}'.replace(',', ' ')
        methodes = ', '.join(meth) if meth else 'méthodes combinées'
        texte = (f'{genre} ; distance mesurée {mpc} Mpc ({mal} millions d’al) ± {max(1, round(46.1 * edm))} % '
                 f'({methodes} ; Cosmicflows-4, Tully et al. 2023)')
        lignes.append(f'{nom}\t{p[0]:.6g}\t{p[1]:.6g}\t{p[2]:.6g}\t{texte}\t9\n')
    # Galaxie dominante d'un groupe, sans distance à elle dans la table 2 (M77 = NGC 1068 : Seyfert vue de face, ni
    # Tully-Fisher ni autre mesure) : elle prend la distance MESURÉE de son groupe (table 3, moyenne pondérée des modules de
    # ses membres, échelle DMzp, la même que la table 2), dans sa propre direction (OpenNGC). Marc, 20/11/2026 : « M77 se
    # balade » ; avant, sa distance venait de son décalage vers le rouge (z = 0,0038 : 55 millions d'al au lieu de 44).
    individuelles = {int(r['PGC']) for r in cf4 if r.get('PGC', '').isdigit()}
    coords = lire_coords_openngc(raw)
    de_groupe = 0
    for g in lire_groupes(os.path.join(raw, 'cf4groupes', 'groupes.tsv')):
        try:
            pgc, ngal, dm, edm = int(g['1PGC']), int(g['Ngal']), float(g['DMzp']), float(g['e_DMzp'])
        except (KeyError, ValueError):
            continue
        if pgc in individuelles or pgc not in coords or pgc not in noms:
            continue
        d = 10 ** ((dm - 25) / 5) * MPC_LY
        p = ecliptique(*coords[pgc]) * d
        cosang = (E @ p) / (En * d)
        if np.any((cosang > math.cos(math.radians(0.2))) & (np.abs(En / d - 1) < 0.3)):
            doubles += 1
            continue
        nom, genre = noms[pgc]
        mpc = f'{d / MPC_LY:.1f}'.replace('.', ',')
        mal = f'{d / 1e6:,.0f}'.replace(',', ' ')
        vpec = f' ; vitesse propre du groupe {g["Vpec"]} km/s (Cosmicflows-4)' if g.get('Vpec') else ''
        texte = (f'{genre} ; distance mesurée du groupe {mpc} Mpc ({mal} millions d’al) ± {max(1, round(46.1 * edm))} % '
                 f'(moyenne des {ngal} galaxies mesurées de son groupe, pas d’elle-même ; Cosmicflows-4 table 3, '
                 f'Tully et al. 2023){vpec}')
        lignes.append(f'{nom}\t{p[0]:.6g}\t{p[1]:.6g}\t{p[2]:.6g}\t{texte}\t9\n')
        de_groupe += 1
    os.makedirs(sortie, exist_ok=True)
    with open(os.path.join(sortie, 'galaxies_cf4.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.writelines(lignes)
    print(f'{len(lignes)} galaxies écrites ({nommees} avec un nom OpenNGC, {de_groupe} à la distance de leur groupe) ; '
          f'{doubles} déjà nommées par l\'appli ; {len(cf4)} lignes dans CF4')


if __name__ == '__main__':
    main()
