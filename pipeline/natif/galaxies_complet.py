#!/usr/bin/env python3
"""TOUS les relevés de galaxies et de quasars, complets et à position exacte -> galaxies.bin de l'appli PC.

Pourquoi (demande de Marc, 12/11/2026 : « toutes les données, pas une version allégée ») : galaxies.py reprenait les
relevés de la page, tirés au hasard (6dF 50 000, 2dF 70 000, SDSS 200 000 + reste en flux, DESI 13,5 %) et arrondis à
16 bits (~20″ en direction, ~0,01 % en z). Ici, chaque relevé est relu en entier à sa source, sans arrondi.

Relevés (même choix que la page, critères de qualité publiés par chaque équipe) :
- 2MRS, Huchra et al. 2012 (VizieR J/ApJS/199/26/table3) : cz ;
- 6dFGS, Jones et al. 2009 (VizieR VII/259) : cz, qualité 3 à 5 ;
- 2dFGRS, Colless et al. 2001 (VizieR VII/250) : z, qualité 3 à 5 ;
- SDSS DR17 (Astro Data Lab, sdss_dr17.specobj) : galaxies et quasars, zwarning = 0, spectre principal ;
- SDSS DR16Q, Lyke et al. 2020 (VizieR VII/289) : quasars ;
- DESI DR1 (desi_complet.py : tous les décalages sûrs, galaxies et quasars).
Doublons : un objet vu par plusieurs relevés n'est gardé qu'une fois, à moins de 1,5″, dans l'ordre DESI, SDSS, DR16Q,
2dF, 6dF, 2MRS (le spectre le plus récent d'abord). Décalage vers le rouge ramené au repère du Groupe local comme la page
(Yahil et al. 1977 : -79, 296, -36 km/s en galactique), pour tous les relevés cette fois.
Couleur : celle de la page (table ZCOL, galaxies.py). Format de sortie : celui de galaxies.py (UNIVGAL1).
Usage : python galaxies_complet.py <dossier des relevés> <dossier DESI> <dossier de sortie>
"""
import glob
import math
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etoiles import ALIGN, data_keys      # noqa: E402
from galaxies import MAGIC, couleurs      # noqa: E402

CKMS = 299792.458
VIZIER = ['vizier.cfa.harvard.edu', 'vizier.cds.unistra.fr']
TAP = 'https://datalab.noirlab.edu/tap/sync'
UA = {'User-Agent': 'UniversPC/1.0 (visualisation personnelle)'}
OBLIQ = math.radians(84381.448 / 3600)
EQ_GAL = np.array([[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132],      # ICRS -> galactique
                   [+0.4941094278755837, -0.4448296299600112, +0.7469822444972189],      # (Hipparcos, vol. 1, § 1.5.3)
                   [-0.8676661490190047, -0.1980763734312015, +0.4559837761750669]])
SEUIL = math.radians(1.5 / 3600)


def charger(url: str, chemin: str, data: dict | None = None, mini: int = 10_000) -> None:
    if os.path.exists(chemin):
        return
    for essai in range(6):
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None, headers=UA)
            with urllib.request.urlopen(req, timeout=3600) as r, open(chemin + '.part', 'wb') as f:
                while c := r.read(1 << 20):
                    f.write(c)
            if os.path.getsize(chemin + '.part') < mini:
                raise RuntimeError(open(chemin + '.part', errors='replace').read(300))
            os.replace(chemin + '.part', chemin)
            print(f'  {os.path.basename(chemin)} : {os.path.getsize(chemin) / 1e6:.1f} Mo', flush=True)
            return
        except Exception as e:
            print(f'  {os.path.basename(chemin)} essai {essai} : {str(e)[:160]}', flush=True)
            time.sleep(30 * (essai + 1))
    raise SystemExit(f'{chemin} : échec')


def vizier(dossier: str, nom: str, source: str, cols: str) -> str:
    chemin = os.path.join(dossier, nom)
    for hote in VIZIER:
        try:
            charger(f'https://{hote}/viz-bin/asu-tsv?-source={source}&-out.max=unlimited&-out={cols}', chemin, mini=100_000)
            return chemin
        except SystemExit:
            continue
    raise SystemExit(f'{nom} : aucun miroir VizieR ne répond')


def telecharger(dossier: str) -> None:
    os.makedirs(dossier, exist_ok=True)
    vizier(dossier, '2mrs.tsv', 'J/ApJS/199/26/table3', '_RAJ2000,_DEJ2000,cz')
    vizier(dossier, '6dfgs.tsv', 'VII/259/6dfgs', '_RAJ2000,_DEJ2000,cz,q_cz')
    vizier(dossier, '2dfgrs.tsv', 'VII/250/2dfgrs', '_RAJ2000,_DEJ2000,z,q_z')
    vizier(dossier, 'dr16q.tsv', 'VII/289/dr16q', '_RAJ2000,_DEJ2000,z')
    for k in range(50):      # SDSS en 50 bandes d'ascension droite (requêtes courtes)
        q = (f"SELECT ra, dec, z, class FROM sdss_dr17.specobj WHERE ra >= {k * 7.2} AND ra < {(k + 1) * 7.2} "
             "AND zwarning = 0 AND sciencePrimary = 1 AND class <> 'STAR' AND z > 0.002 AND z < 7")
        charger(TAP, os.path.join(dossier, f'sdss_{k:02d}.csv'),
                dict(REQUEST='doQuery', LANG='ADQL', FORMAT='csv', MAXREC='100000000', QUERY=q), mini=100)


def lire_tsv(chemin: str, colz: int, echelle: float, qual: int | None = None) -> tuple:
    ra, de, z = [], [], []
    for l in open(chemin, encoding='utf-8', errors='replace'):
        if l.startswith('#') or not l.strip():
            continue
        c = l.rstrip('\n').split('\t')
        try:
            if qual is not None and int(c[qual]) not in (3, 4, 5):
                continue
            ra.append(float(c[0])); de.append(float(c[1])); z.append(float(c[colz]) * echelle)
        except (ValueError, IndexError):
            continue
    return np.array(ra), np.array(de), np.array(z)


def lire_csv(fichiers: list[str], cols: tuple[int, int, int, int]) -> tuple:
    ra, de, z, q = [], [], [], []
    for f in fichiers:
        with open(f, encoding='utf-8') as h:
            next(h)
            for l in h:
                c = l.rstrip('\n').split(',')
                try:
                    ra.append(float(c[cols[0]])); de.append(float(c[cols[1]])); z.append(float(c[cols[2]]))
                    q.append(c[cols[3]].strip().strip('"').upper().startswith('Q'))
                except (ValueError, IndexError):
                    continue
    return np.array(ra), np.array(de), np.array(z), np.array(q, bool)


def unitaire(ra: np.ndarray, de: np.ndarray) -> np.ndarray:
    a, d = np.radians(ra), np.radians(de)
    return np.stack([np.cos(d) * np.cos(a), np.cos(d) * np.sin(a), np.sin(d)], axis=1)


def main() -> None:
    dossier, desi, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    t0 = time.time()
    telecharger(dossier)
    rel = []      # (nom, unitaire équatorial, z, quasar), dans l'ordre de priorité des doublons
    ra, de, z, q = lire_csv(sorted(glob.glob(os.path.join(desi, 'desi_*.csv'))), (1, 2, 3, 5))
    rel.append(('DESI DR1', unitaire(ra, de), z, q))
    ra, de, z, q = lire_csv(sorted(glob.glob(os.path.join(dossier, 'sdss_*.csv'))), (0, 1, 2, 3))
    rel.append(('SDSS DR17', unitaire(ra, de), z, q))
    ra, de, z = lire_tsv(os.path.join(dossier, 'dr16q.tsv'), 2, 1.0)
    rel.append(('DR16Q', unitaire(ra, de), z, np.ones(len(z), bool)))
    ra, de, z = lire_tsv(os.path.join(dossier, '2dfgrs.tsv'), 2, 1.0, qual=3)
    rel.append(('2dFGRS', unitaire(ra, de), z, np.zeros(len(z), bool)))
    ra, de, z = lire_tsv(os.path.join(dossier, '6dfgs.tsv'), 2, 1 / CKMS, qual=3)
    rel.append(('6dFGS', unitaire(ra, de), z, np.zeros(len(z), bool)))
    ra, de, z = lire_tsv(os.path.join(dossier, '2mrs.tsv'), 2, 1 / CKMS)
    rel.append(('2MRS', unitaire(ra, de), z, np.zeros(len(z), bool)))
    gardes_u, gardes_z, gardes_q, bilan = [], [], [], []
    arbre = None
    for nom, u, z, q in rel:
        ok = np.isfinite(z) & (z > 0.002) & (z < 7.0)
        u, z, q = u[ok], z[ok], q[ok]
        if arbre is not None:
            d, _ = arbre.query(u, distance_upper_bound=2 * math.sin(SEUIL / 2))
            neuf = ~np.isfinite(d)
            bilan.append(f'{nom} {len(z)} lus, {int((~neuf).sum())} déjà vus')
            u, z, q = u[neuf], z[neuf], q[neuf]
        else:
            bilan.append(f'{nom} {len(z)} lus')
        gardes_u.append(u); gardes_z.append(z); gardes_q.append(q)
        arbre = cKDTree(np.concatenate(gardes_u))
        print(f'  {bilan[-1]} ({time.time() - t0:.0f} s)', flush=True)
    u = np.concatenate(gardes_u); z = np.concatenate(gardes_z); q = np.concatenate(gardes_q)
    g = u @ EQ_GAL.T      # repère du Groupe local (comme la page)
    z = z + (-79.0 * g[:, 0] + 296.0 * g[:, 1] - 36.0 * g[:, 2]) / CKMS
    c, s = math.cos(OBLIQ), math.sin(OBLIQ)      # équatorial -> écliptique J2000
    d = np.stack([u[:, 0], u[:, 1] * c + u[:, 2] * s, -u[:, 1] * s + u[:, 2] * c], axis=1)
    keep = z > 0
    d, z, q = d[keep], z[keep], q[keep]
    col = couleurs(data_keys(['ZCOL']), z, q)
    os.makedirs(sortie, exist_ok=True)
    path = os.path.join(sortie, 'galaxies.bin')
    with open(path + '.part', 'wb') as f:
        head = MAGIC + np.int64(len(z)).tobytes()
        f.write(head + b'\0' * (ALIGN - len(head)))
        for colonne in (d[:, 0], d[:, 1], d[:, 2], z):
            b = colonne.astype('<f4').tobytes(); f.write(b + b'\0' * (-len(b) % ALIGN))
        b = col.tobytes(); f.write(b + b'\0' * (-len(b) % ALIGN))
    os.replace(path + '.part', path)
    print(f'{len(z)} galaxies et quasars ({int(q.sum())} quasars), z de {z.min():.4f} à {z.max():.3f}, '
          f'{os.path.getsize(path) / 1e6:.0f} Mo ; ' + ' ; '.join(bilan))


if __name__ == '__main__':
    main()
