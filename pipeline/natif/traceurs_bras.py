#!/usr/bin/env python3
"""Objets MESURÉS qui tracent les bras spiraux de la Voie lactée -> traceurs_bras.tsv pour l'appli PC.

Gaia ne mesure bien que le voisinage du Soleil ; les bras de toute la Galaxie sont tracés par d'autres mesures publiées :
- masers de régions où naissent des étoiles massives, distance par parallaxe mesurée en interférométrie radio
  (Reid et al. 2019, ApJ 885, 131, table 1 ; VizieR J/ApJ/885/131/table1) : environ 200 objets jusqu'à l'autre côté de
  la Galaxie, chacun avec le bras auquel les auteurs le rattachent ;
- amas ouverts de Gaia DR3 (Hunt & Reffert 2023, A&A 673, A114 ; VizieR J/A+A/673/A114/clusters) : distance et âge ;
  les amas jeunes (moins de 100 millions d'années) n'ont pas eu le temps de quitter le bras où ils sont nés.
Téléchargés depuis le miroir de VizieR (vizier.cfa.harvard.edu). Position : direction mesurée + distance mesurée
(masers : 1 / parallaxe ; amas : distance médiane publiée), en années-lumière, repère écliptique J2000 centré sur le
Soleil. Rien d'autre n'est calculé. Les masers dont la parallaxe vaut moins de 3 fois son erreur sont écartés (comptés).

Sortie traceurs_bras.tsv : nom, x, y, z (al), genre (maser | amas), bras (masers : code des auteurs ; amas : vide),
âge en millions d'années (amas ; -1 pour les masers), erreur relative de distance.
Usage : python traceurs_bras.py <dossier de téléchargement> <dossier de sortie>
"""
import math
import os
import sys
import urllib.request

BASE = 'https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?-out.max=unlimited&-source='
MASERS = BASE + 'J/ApJ/885/131/table1&-out.all'
AMAS = BASE + 'J/A%2BA/673/A114/clusters&-out=Name,RA_ICRS,DE_ICRS,dist50,dist16,dist84,logAge50,N,CST,pmRA,pmDE,RV,n_RV'
PC_LY = 3.2615637769
EPS = math.radians(84381.448 / 3600)      # obliquité J2000


def rows(path: str, url: str) -> tuple[list[str], list[list[str]]]:
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
    with open(path, encoding='utf-8', errors='replace') as f:
        lines = [l.rstrip('\n') for l in f if l.strip() and not l.startswith('#')]
    head = lines[0].split('\t')
    return head, [l.split('\t') for l in lines[3:] if len(l.split('\t')) == len(head)]


def ecliptic(ra_deg: float, dec_deg: float, d_ly: float) -> tuple[float, float, float]:
    a, d = math.radians(ra_deg), math.radians(dec_deg)
    x, ye, ze = math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d)
    return x * d_ly, (ye * math.cos(EPS) + ze * math.sin(EPS)) * d_ly, (-ye * math.sin(EPS) + ze * math.cos(EPS)) * d_ly


def sexa(s: str, hours: bool) -> float:
    p = s.split()
    sign = -1.0 if p[0].startswith('-') else 1.0
    v = abs(float(p[0])) + float(p[1]) / 60 + float(p[2]) / 3600
    return sign * v * (15.0 if hours else 1.0)


def main() -> None:
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(src, exist_ok=True)
    lines, ecartes = [], 0
    head, data = rows(os.path.join(src, 'masers.tsv'), MASERS)
    col = {k: i for i, k in enumerate(head)}
    for r in data:
        plx, e = float(r[col['plx']]), float(r[col['e_plx']])
        if plx <= 0 or plx < 3 * e:
            ecartes += 1
            continue
        x, y, z = ecliptic(sexa(r[col['RAJ2000']], True), sexa(r[col['DEJ2000']], False), 1000.0 / plx * PC_LY)
        lines.append(f"{r[col['Name']].strip()}\t{x!r}\t{y!r}\t{z!r}\tmaser\t{r[col['Arm']].strip()}\t-1\t{e / plx:.3f}")
    n_masers = len(lines)
    head, data = rows(os.path.join(src, 'amas.tsv'), AMAS)
    col = {k: i for i, k in enumerate(head)}
    for r in data:
        try:
            d50, d16, d84, age = float(r[col['dist50']]), float(r[col['dist16']]), float(r[col['dist84']]), float(r[col['logAge50']])
        except ValueError:
            continue
        x, y, z = ecliptic(float(r[col['RA_ICRS']]), float(r[col['DE_ICRS']]), d50 * PC_LY)
        lines.append(f"{r[col['Name']].strip()}\t{x!r}\t{y!r}\t{z!r}\tamas\t\t{10 ** age / 1e6:.1f}\t{(d84 - d16) / (2 * d50):.3f}")
    with open(os.path.join(out, 'traceurs_bras.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'{n_masers} masers ({ecartes} écartés : parallaxe sous 3 fois son erreur) et {len(lines) - n_masers} amas ouverts écrits')


if __name__ == '__main__':
    main()
