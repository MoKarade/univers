#!/usr/bin/env python3
"""Fiches complètes des galaxies, amas, trous noirs centraux et grandes structures de l'appli PC -> C:\\tmp\\fiches\\galaxies*.tsv

Demande de Marc (20/11/2026) : la fiche d'un objet montre TOUTES les grandeurs publiques, avec incertitudes, source et
statut (format : docs/fiches-format.md). Aucune valeur inventée : une case vide de la source n'est pas écrite.

Astres couverts (clé = 1re colonne, nom exact) : galaxies_noms.tsv, galaxies_cf4.tsv, galaxies_formes_noms.tsv,
structures_noms.tsv, superstructures_noms.tsv, et « Centre de la Voie lactée » (Sgr A*).

Sources (cache brut : C:\\tmp\\fiches\\cache\\galaxies, téléchargé une fois, poliment) :
- Cosmicflows-4, Tully et al. 2023 (ApJ 944, 94 ; VizieR J/ApJ/944/94) : table 2 (galaxies) et table des groupes
  (fichiers déjà sur le PC, %LOCALAPPDATA%\\univers-raw\\cf4_table2.tsv et cf4groupes\\groupes.tsv) ;
- Kourkchi & Tully 2017 (ApJ 843, 16 ; VizieR J/ApJ/843/16), groupes à moins de 3 500 km/s (univers-raw\\kt17) ;
- HyperLEDA (Makarov et al. 2014, A&A 570, A13), table « meandata » interrogée par lots de 2 000 PGC
  (atlas.obs-hp.fr/hyperleda/fG.cgi, sortie CSV) ;
- Siena Galaxy Atlas 2020 (Moustakas et al. 2023, ApJS 269, 3), fichier SGA-2020.fits (C:\\tmp\\natif\\galaxies-formes) ;
- Local Volume Database (Pace 2024, arXiv:2411.07424), pipeline/raw/dwarf_all.csv (références d'origine par colonne) ;
- McConnachie 2012 (AJ 144, 4 ; VizieR J/AJ/144/4) ; Karachentsev et al. 2013, UNGC (AJ 145, 101 ; VizieR J/AJ/145/101) ;
- SIMBAD (Wenger et al. 2000), miroir CfA : résolveur Sesame et service TAP (type, décalage vers le rouge, dimensions,
  magnitudes, autres noms) pour les astres nommés de galaxies_noms.tsv ;
- MCXC, Piffaretti et al. 2011 (A&A 534, A109 ; VizieR J/A+A/534/A109) et Abell, Corwin & Olowin 1989 (ApJS 70, 1 ;
  VizieR VII/110A) pour les amas ;
- trous_noirs.tsv de l'appli (van den Bosch 2016, GRAVITY 2022, EHT 2019 : sources ligne par ligne) ;
- superstructures.tsv (C:\\tmp\\vue-sources, écrit par superstructures.py : Dupuy & Courtois 2023 et articles cités) ;
- Malandrino et al. 2026 (A&A 705, A160), catalogue de 100 vides (univers-raw\\vides_locaux).

Statuts : « mesuré » (valeur publiée ajustée sur des observations) ; « calculé » (déduit ici ou par le catalogue, la
formule est dans la source) ; « modèle » (distance d'après z, masse d'après une relation, reconstruction) ; « publié »
(nom, type, classement).

Sorties (l'appli concatène les lignes d'un même astre ; fichiers lus dans l'ordre alphabétique) :
- galaxies.tsv : format long, astres nommés, amas, structures, trous noirs ;
- galaxies_1_leda.tsv, galaxies_2_cf4.tsv, galaxies_3_sga.tsv : format « tableau » (une ligne par astre).

Usage : python fiches_galaxies.py [dossier des données de l'appli] [dossier de sortie]
        (par défaut C:\\dev\\Univers-PC et C:\\tmp\\fiches)
"""
import csv
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date

import numpy as np
from scipy.spatial import cKDTree

sys.stdout.reconfigure(encoding='utf-8')
csv.field_size_limit(10 ** 8)

ICI = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'univers-raw')
CACHE = r'C:\tmp\fiches\cache\galaxies'
SGA = r'C:\tmp\natif\galaxies-formes\SGA-2020.fits'
SUPERSTRUCT = r'C:\tmp\vue-sources\superstructures.tsv'
LVDB = os.path.join(ICI, '..', 'raw', 'dwarf_all.csv')
LEDA_URL = 'http://atlas.obs-hp.fr/hyperleda/fG.cgi'
SESAME = 'https://vizier.cfa.harvard.edu/viz-bin/nph-sesame/-oxp/S?'
TAP = 'https://simbad.cfa.harvard.edu/simbad/sim-tap/sync'
EPS = math.radians(84381.448 / 3600.0)
MPC_LY = 3.2615637771674333e6
ORDRE = ['Identité', 'Position', 'Mouvement', 'Physique', 'Trou noir central', 'Lumière et couleur', 'Âge et évolution',
         'Groupe et amas', 'Autres noms', 'Modèles et hypothèses']
S_CF4 = 'Cosmicflows-4 (Tully et al. 2023, ApJ 944, 94)'
S_LEDA = 'HyperLEDA (Makarov et al. 2014)'
S_SGA = 'SGA-2020 (Moustakas et al. 2023, ApJS 269, 3)'
S_LVDB = 'Local Volume Database (Pace 2024)'
S_MC = 'McConnachie 2012 (AJ 144, 4)'
S_UNGC = 'UNGC (Karachentsev et al. 2013, AJ 145, 101)'
S_KT = 'Kourkchi & Tully 2017 (ApJ 843, 16)'
S_SIM = 'SIMBAD (CDS)'


# ------------------------------------------------------------------ petits outils

def val(s) -> str:
    """Case de la source, telle quelle (chiffre pour chiffre) ; '' si vide."""
    s = ('' if s is None else str(s)).strip().replace('\t', ' ')
    return '' if s.lower() in ('', 'nan', 'none', 'null', '--', 'inf', '-inf') else s


def fl(s):
    try:
        x = float(val(s))
        return x if math.isfinite(x) else None
    except ValueError:
        return None


def g(x, n=4) -> str:
    """Nombre calculé ici, n chiffres significatifs."""
    return '' if x is None or not math.isfinite(x) else f'{x:.{n}g}'


def asym(ep, em) -> str:
    """Incertitude « +ep/-em », ou symétrique si égales."""
    ep, em = val(ep), val(em)
    if not ep and not em:
        return ''
    if ep == em or not em:
        return ep
    if not ep:
        return em
    return f'+{ep}/-{em}'


def direction(ra, dec) -> np.ndarray:
    a, d = np.radians(ra), np.radians(dec)
    return np.stack([np.cos(d) * np.cos(a), np.cos(d) * np.sin(a), np.sin(d)], -1)


def ecl_vers_radec(x, y, z):
    ye = y * math.cos(EPS) - z * math.sin(EPS)
    ze = y * math.sin(EPS) + z * math.cos(EPS)
    d = math.sqrt(x * x + y * y + z * z)
    if d == 0:
        return 0.0, 0.0, 0.0
    return math.degrees(math.atan2(ye, x)) % 360, math.degrees(math.asin(ze / d)), d


def lire_vizier(chemin):
    """Tables TSV de VizieR (plusieurs tables possibles) -> liste de listes de dict."""
    tables, ent, avant = [], None, False
    for l in open(chemin, encoding='utf-8', errors='replace'):
        l = l.rstrip('\n')
        if ent is not None and avant and not l.startswith('#'):
            avant = not re.fullmatch(r'[-\t ]+', l) or '-' not in l
            continue
        if l.startswith('#') or not l.strip():
            ent = None if not l.strip() else ent
            continue
        if ent is None:
            ent = [c.strip() for c in l.split('\t')]
            tables.append([])
            avant = True      # unités éventuelles jusqu'à la ligne de tirets
            continue
        c = l.split('\t')
        if len(c) == len(ent):
            tables[-1].append({k: v.strip() for k, v in zip(ent, c)})
    return tables


def telecharger(url, chemin, data=None, pause=1.0):
    if os.path.exists(chemin) and os.path.getsize(chemin) > 0:
        return open(chemin, encoding='utf-8', errors='replace').read()
    req = urllib.request.Request(url, data=data, headers={'User-Agent': 'univers-fiches/1.0'})
    with urllib.request.urlopen(req, timeout=300) as r:
        txt = r.read().decode('utf-8', errors='replace')
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
        f.write(txt)
    time.sleep(pause)
    return txt


class Fiches:
    """Format long : cle, groupe, libellé, valeur, incertitude, unité, statut, source."""

    def __init__(self):
        self.l: dict[str, list] = {}

    def add(self, cle, groupe, lib, v, inc='', unite='', statut='mesuré', source=''):
        v = val(v)
        if not v:
            return
        self.l.setdefault(cle, []).append((groupe, lib, v, val(inc), unite, statut, source.replace('\t', ' ')))

    def ecrire(self, chemin, entete):
        with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
            f.write(entete)
            for cle, lignes in self.l.items():
                vus = set()
                for li in sorted(lignes, key=lambda t: ORDRE.index(t[0]) if t[0] in ORDRE else 99):
                    if li in vus:
                        continue
                    vus.add(li)
                    f.write(cle + '\t' + '\t'.join(li) + '\n')


class Tableau:
    """Format « tableau » : en-têtes @ (groupe, libellé, unité, statut, source), puis cle + (valeur, incertitude) × n."""

    def __init__(self, colonnes):
        self.col = colonnes
        self.idx = {c[1]: i for i, c in enumerate(colonnes)}
        self.lignes: dict[str, list] = {}

    def mettre(self, cle, lib, v, inc=''):
        v = val(v)
        if not v:
            return
        r = self.lignes.setdefault(cle, [('', '')] * len(self.col))
        r = list(r)
        r[self.idx[lib]] = (v, val(inc))
        self.lignes[cle] = r

    def ecrire(self, chemin, entete):
        with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
            f.write(entete)
            for c in self.col:
                f.write('@\t' + '\t'.join(c) + '\n')
            for cle, r in self.lignes.items():
                f.write(cle + '\t' + '\t'.join(f'{a}\t{b}' for a, b in r) + '\n')


# ------------------------------------------------------------------ astres de l'appli

def lire_appli(donnees):
    def tsv(nom):
        out = []
        for l in open(os.path.join(donnees, nom), encoding='utf-8'):
            c = l.rstrip('\n').split('\t')
            if len(c) >= 5 and not l.startswith('#'):
                ra, dec, d = ecl_vers_radec(float(c[1]), float(c[2]), float(c[3]))
                out.append(dict(cle=c[0], ra=ra, dec=dec, d_ly=d, texte=c[4]))
        return out
    return {f: tsv(f + '.tsv') for f in ('galaxies_noms', 'galaxies_cf4', 'galaxies_formes_noms', 'structures_noms',
                                          'superstructures_noms')}


def noms_openngc():
    """Nom -> PGC, exactement comme galaxies_cf4.py nomme ses galaxies (OpenNGC, M. Verga)."""
    out: dict[str, list[int]] = {}
    for f in ('NGC.csv', 'addendum.csv'):
        ch = os.path.join(RAW, 'openngc', f)
        if not os.path.exists(ch):
            continue
        for r in csv.DictReader(open(ch, encoding='utf-8'), delimiter=';'):
            p = re.search(r'PGC (\d+)', r.get('Identifiers') or '')
            if not p:
                continue
            m = re.match(r'(NGC|IC)0*(\d+)(.*)', r['Name'])
            nom = f'{m.group(1)} {m.group(2)}{m.group(3)}' if m else r['Name']
            if r.get('M'):
                nom = f'M{int(r["M"])} ({nom})'
            out.setdefault(nom, []).append(int(p.group(1)))
    return out


# ------------------------------------------------------------------ SIMBAD (astres nommés)

FR_SIMBAD = {
    'Grand Nuage de Magellan': ['LMC'], 'Petit Nuage de Magellan': ['SMC'], 'Andromède (M31)': ['M31'],
    'Galaxie du Triangle (M33)': ['M33'], 'Naine du Sagittaire': ['NAME Sagittarius Dwarf Spheroidal Galaxy', 'Sgr dSph'],
    'Naine du Dragon': ['NAME Draco Dwarf Galaxy', 'Draco dSph'], 'Naine de la Petite Ourse': ['NAME UMi Dwarf Galaxy', 'Ursa Minor dSph'],
    'Naine du Sculpteur': ['NAME Sculptor Dwarf Galaxy', 'Sculptor dSph'], 'Naine du Sextant': ['NAME Sextans dSph', 'Sextans dSph'],
    'Naine de la Carène': ['NAME Carina Dwarf Galaxy', 'Carina dSph'], 'Naine du Fourneau': ['NAME Fornax Dwarf Galaxy', 'Fornax dSph'],
    'Naine du Phénix': ['NAME Phoenix Dwarf Galaxy', 'Phoenix Dwarf'], 'Canis Major': ['NAME Canis Major Dwarf Galaxy'],
    'Segue (I)': ['NAME Segue 1', 'Segue 1'], 'Bootes (I)': ['NAME Bootes Dwarf Spheroidal Galaxy', 'Bootes I'],
    'Ursa Major (I)': ['NAME UMa I Galaxy', 'Ursa Major I'], 'Canes Venatici (I)': ['NAME Canes Venatici I Dwarf Galaxy', 'CVn I'],
    'Hercules': ['NAME Hercules Dwarf Galaxy', 'Hercules dSph'], 'Coma Berenices': ['NAME Coma Dwarf Galaxy', 'Coma Berenices dSph'],
    'Cetus': ['NAME Cetus Dwarf Galaxy', 'Cetus Dwarf'], 'Tucana': ['NAME Tucana Dwarf Galaxy', 'Tucana Dwarf'],
    'Aquarius': ['DDO 210'], 'Antlia': ['NAME Antlia Dwarf Galaxy', 'Antlia Dwarf'], 'Pegasus dIrr': ['DDO 216'],
    'Sagittarius dIrr': ['NAME Sagittarius Dwarf Irregular Galaxy', 'SagDIG'], 'LGS 3 (Local Group Suspect 3)': ['LGS 3'],
    'WLM (Wolf-Lundmark-Melotte)': ['WLM'], 'HIZSS 3(A)': ['HIZSS 3A', 'HIZSS 3'], 'Galaxie du Sculpteur': ['NGC 253'],
    'Galaxie du Tourbillon (M51)': ['M51'], 'Galaxie du Sombrero': ['M104'], 'Centaurus A': ['NGC 5128'],
    'Amas de la Vierge': ['NAME Virgo Cluster'], 'Amas du Fourneau': ['NAME Fornax Cluster'], 'Amas du Centaure': ['ACO 3526'],
    'Amas de l’Hydre': ['ACO 1060'], 'Amas de Persée': ['ACO 426'], 'Amas de Coma': ['ACO 1656'], 'Amas du Lion': ['ACO 1367'],
    'Amas d’Hercule': ['ACO 2151'], 'Abell 2199': ['ACO 2199'], 'Amas de la Couronne boréale': ['ACO 2065'],
    'Grand Attracteur': ['NAME Great Attractor'], 'Superamas de Shapley': ['NAME Shapley Supercluster'],
    'Vide du Bouvier': ['NAME Bootes Void'], 'Leo K': [], 'Leo M': [], 'Pegasus W': ['Pegasus W'],
}
AMAS = {  # clé -> (nom MCXC [colonne OName/AName], numéro ACO)
    'Amas de la Vierge': ('Virgo', None), 'Amas du Fourneau': ('FORNAX', None), 'Amas du Centaure': ('A3526', 3526),
    'Amas de l’Hydre': ('A1060', 1060), 'Amas de Persée': ('A0426', 426), 'Amas de Coma': ('Coma', 1656),
    'Amas du Lion': ('A1367', 1367), 'Amas d’Hercule': ('A2151a', 2151), 'Abell 2199': ('A2199', 2199),
    'Amas de la Couronne boréale': ('A2065', 2065)}
NON_GALAXIE = set(AMAS) | {'Grand Attracteur', 'Superamas de Shapley', 'Vide du Bouvier'}


def candidats(cle):
    if cle in FR_SIMBAD:
        return FR_SIMBAD[cle]
    c = re.sub(r'\s*\((I)\)', ' I', cle).strip()
    return [c, re.sub(r'\s*\(.*\)', '', cle).strip()]


def sesame(noms_pos):
    """Nom de l'appli -> (identifiant SIMBAD, ra, dec), contrôlé : à moins de 1° de la position de l'appli."""
    ch = os.path.join(CACHE, 'sesame.json')
    cache = json.load(open(ch, encoding='utf-8')) if os.path.exists(ch) else {}
    out = {}
    for cle, ra0, dec0 in noms_pos:
        for c in candidats(cle):
            if c not in cache:
                try:
                    with urllib.request.urlopen(SESAME + urllib.parse.quote(c), timeout=60) as r:
                        x = r.read().decode('utf-8', errors='replace')
                except OSError:
                    continue      # panne passagère : pas mise en cache
                m = {k: re.search(f'<{k}>(.*?)</{k}>', x) for k in ('oname', 'jradeg', 'jdedeg')}
                cache[c] = [m['oname'].group(1), float(m['jradeg'].group(1)), float(m['jdedeg'].group(1))] \
                    if all(m.values()) else None
                time.sleep(0.3)
            r = cache[c]
            if r and float(direction(ra0, dec0) @ direction(r[1], r[2])) > math.cos(math.radians(1.0)):
                out[cle] = tuple(r)
                break
    json.dump(cache, open(ch, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return out


def cone_simbad(cibles):
    """Repli quand Sesame ne connaît pas le nom : galaxie SIMBAD la plus proche (à moins de 3′) d'une position mesurée
    (LVDB si la naine y est, sinon position de l'appli)."""
    ch = os.path.join(CACHE, 'simbad_cones.json')
    cache = json.load(open(ch, encoding='utf-8')) if os.path.exists(ch) else {}
    out = {}
    for cle, ra, dec in cibles:
        k = f'{ra:.5f} {dec:.5f}'
        if k not in cache:
            q = ("SELECT TOP 1 main_id, ra, dec, DISTANCE(POINT('ICRS', ra, dec), POINT('ICRS', %f, %f)) AS d FROM basic "
                 "WHERE otype = 'G..' AND CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', %f, %f, 0.05)) = 1 ORDER BY d"
                 % (ra, dec, ra, dec))
            data = urllib.parse.urlencode({'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'tsv', 'QUERY': q}).encode()
            try:
                with urllib.request.urlopen(urllib.request.Request(TAP, data=data), timeout=120) as r:
                    lignes = [l.split('	') for l in r.read().decode('utf-8').splitlines() if l.strip()]
            except OSError:
                continue
            cache[k] = [lignes[1][0].strip('"'), float(lignes[1][1]), float(lignes[1][2])] if len(lignes) > 1 else None
            time.sleep(0.5)
        if cache[k]:
            out[cle] = tuple(cache[k])
    json.dump(cache, open(ch, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return out


def tap(requete, fichier):
    data = urllib.parse.urlencode({'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'tsv', 'QUERY': requete}).encode()
    txt = telecharger(TAP, os.path.join(CACHE, fichier), data)
    lignes = [l.split('\t') for l in txt.splitlines() if l.strip()]
    ent = [c.strip('"') for c in lignes[0]]
    return [{k: v.strip().strip('"') for k, v in zip(ent, l)} for l in lignes[1:]]


def simbad(ids):
    liste = ','.join("'" + i.replace("'", "''") + "'" for i in sorted(set(ids)))
    base = tap('SELECT main_id,otype,morph_type,ra,dec,rvz_radvel,rvz_redshift,rvz_err,rvz_type,rvz_qual,rvz_bibcode,'
               'galdim_majaxis,galdim_minaxis,galdim_angle,galdim_bibcode FROM basic WHERE main_id IN (' + liste + ')',
               'simbad_basic.tsv')
    ids_ = tap('SELECT b.main_id,i.id FROM ident i JOIN basic b ON i.oidref=b.oid WHERE b.main_id IN (' + liste + ')',
               'simbad_ids.tsv')
    flux = tap('SELECT b.main_id,f.filter,f.flux,f.flux_err,f.bibcode FROM flux f JOIN basic b ON f.oidref=b.oid '
               'WHERE b.main_id IN (' + liste + ')', 'simbad_flux.tsv')
    return base, ids_, flux


# ------------------------------------------------------------------ HyperLEDA

def hyperleda(pgcs):
    ch, ch_abs = os.path.join(CACHE, 'leda_meandata.csv'), os.path.join(CACHE, 'leda_absents.txt')
    rows = {}
    if os.path.exists(ch):
        for r in csv.DictReader(open(ch, encoding='utf-8')):
            rows[int(r['pgc'])] = r
    absents = set(int(x) for x in open(ch_abs).read().split()) if os.path.exists(ch_abs) else set()
    manque = sorted(set(pgcs) - set(rows) - absents)
    ent = None
    for i in range(0, len(manque), 2000):
        lot = manque[i:i + 2000]
        data = urllib.parse.urlencode({'n': 'meandata', 'c': 'o', 'of': '1,leda,simbad', 'nra': 'l', 'nakd': '1',
                                       'd': '*', 'sql': 'pgc in (' + ','.join(map(str, lot)) + ')', 'ob': '',
                                       'a': 'csv[,]'}).encode()
        for essai in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(LEDA_URL, data=data), timeout=600) as r:
                    txt = r.read().decode('utf-8', errors='replace')
                break
            except OSError as e:
                print('HyperLEDA : nouvel essai', e)
                time.sleep(10)
        else:
            raise SystemExit('HyperLEDA injoignable : rien écrit')
        lignes = [l for l in txt.splitlines() if l and not l.startswith('#')]
        recus = list(csv.DictReader(lignes))
        for r in recus:
            rows[int(r['pgc'])] = r
        absents |= set(lot) - {int(r['pgc']) for r in recus}
        ent = list(recus[0].keys()) if recus else ent
        print(f'HyperLEDA : lot {i // 2000 + 1}/{(len(manque) + 1999) // 2000}, {len(recus)} lignes')
        time.sleep(1.5)
    if manque:
        cols = ent or list(next(iter(rows.values())).keys())
        with open(ch, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, cols, extrasaction='ignore')
            w.writeheader()
            w.writerows(rows.values())
        open(ch_abs, 'w').write('\n'.join(map(str, sorted(absents))))
    return rows


LEDA_COLS = [  # (champ, champ d'erreur, groupe, libellé, unité, statut, précision de la source)
    ('objname', '', 'Identité', 'Nom principal HyperLEDA', '', 'publié', ''),
    ('objtype', '', 'Identité', 'Nature de l’objet (code HyperLEDA)', '', 'publié', 'G = galaxie, M = multiple'),
    ('type', '', 'Identité', 'Type morphologique', '', 'publié', 'classement de Hubble'),
    ('t', 'e_t', 'Identité', 'Indice de type morphologique T', '', 'publié', 'de -5 (elliptique) à 10 (irrégulière)'),
    ('bar', '', 'Identité', 'Barre', '', 'publié', 'B = barrée'),
    ('ring', '', 'Identité', 'Anneau', '', 'publié', 'R = anneau'),
    ('multiple', '', 'Identité', 'Système multiple', '', 'publié', 'M = membre d’un système multiple'),
    ('compactness', '', 'Identité', 'Compacité', '', 'publié', 'C = compacte, D = diffuse'),
    ('agnclass', '', 'Identité', 'Noyau actif (classe)', '', 'publié', 'S = Seyfert, L = LINER, Q = quasar'),
    ('al2000', '', 'Position', 'Ascension droite (J2000)', '°', 'mesuré', 'colonne al2000 (heures) × 15'),
    ('de2000', '', 'Position', 'Déclinaison (J2000)', '°', 'mesuré', ''),
    ('mod0', 'e_mod0', 'Position', 'Module de distance (moyenne des mesures indépendantes du décalage)', 'mag', 'mesuré', ''),
    ('dist0', '', 'Position', 'Distance d’après ce module', 'Mpc', 'calculé', 'calculé ici : 10^((mod0 − 25)/5)'),
    ('modz', 'e_modz', 'Position', 'Module de distance d’après la vitesse', 'mag', 'modèle',
     'loi de Hubble de HyperLEDA (H0 = 70), vitesse corrigée de la chute vers la Vierge'),
    ('v', 'e_v', 'Mouvement', 'Vitesse radiale héliocentrique (moyenne)', 'km/s', 'mesuré', ''),
    ('vopt', 'e_vopt', 'Mouvement', 'Vitesse radiale héliocentrique (optique)', 'km/s', 'mesuré', ''),
    ('vrad', 'e_vrad', 'Mouvement', 'Vitesse radiale héliocentrique (radio, raie 21 cm)', 'km/s', 'mesuré', ''),
    ('vlg', '', 'Mouvement', 'Vitesse par rapport au Groupe local', 'km/s', 'calculé', 'calculé par HyperLEDA depuis v'),
    ('vgsr', '', 'Mouvement', 'Vitesse par rapport au centre galactique', 'km/s', 'calculé', 'calculé par HyperLEDA depuis v'),
    ('v3k', '', 'Mouvement', 'Vitesse par rapport au fond diffus cosmologique', 'km/s', 'calculé', 'calculé par HyperLEDA depuis v'),
    ('vvir', '', 'Mouvement', 'Vitesse corrigée de la chute vers l’amas de la Vierge', 'km/s', 'modèle', 'modèle de chute de HyperLEDA'),
    ('vmaxg', 'e_vmaxg', 'Physique', 'Vitesse de rotation maximale apparente (gaz)', 'km/s', 'mesuré', ''),
    ('vmaxs', 'e_vmaxs', 'Physique', 'Vitesse de rotation maximale apparente (étoiles)', 'km/s', 'mesuré', ''),
    ('vrot', 'e_vrot', 'Physique', 'Vitesse de rotation corrigée de l’inclinaison', 'km/s', 'modèle', 'corrigée avec l’inclinaison incl'),
    ('vdis', 'e_vdis', 'Physique', 'Dispersion centrale des vitesses', 'km/s', 'mesuré', ''),
    ('logd25', 'e_logd25', 'Physique', 'log du diamètre D25 (en 0,1′)', '', 'mesuré', 'isophote 25 mag/arcsec² en B'),
    ('d25', '', 'Physique', 'Diamètre apparent D25', '′', 'calculé', 'calculé ici : 0,1 × 10^logd25'),
    ('logr25', 'e_logr25', 'Physique', 'log du rapport des axes (grand/petit)', '', 'mesuré', ''),
    ('ba', '', 'Physique', 'Rapport des axes b/a', '', 'calculé', 'calculé ici : 10^(−logr25)'),
    ('pa', '', 'Physique', 'Angle de position du grand axe', '°', 'mesuré', 'du nord vers l’est'),
    ('incl', '', 'Physique', 'Inclinaison', '°', 'modèle', 'déduite de logr25 avec une épaisseur intrinsèque supposée selon le type'),
    ('logdc', '', 'Physique', 'log du diamètre corrigé (inclinaison, extinction)', '', 'modèle', ''),
    ('mg2', 'e_mg2', 'Physique', 'Indice de raie Mg2', 'mag', 'mesuré', ''),
    ('bt', 'e_bt', 'Lumière et couleur', 'Magnitude totale B', 'mag', 'mesuré', ''),
    ('ut', 'e_ut', 'Lumière et couleur', 'Magnitude totale U', 'mag', 'mesuré', ''),
    ('vt', 'e_vt', 'Lumière et couleur', 'Magnitude totale V', 'mag', 'mesuré', ''),
    ('it', 'e_it', 'Lumière et couleur', 'Magnitude totale I', 'mag', 'mesuré', ''),
    ('kt', 'e_kt', 'Lumière et couleur', 'Magnitude totale K', 'mag', 'mesuré', ''),
    ('ube', '', 'Lumière et couleur', 'Couleur U − B effective', 'mag', 'mesuré', ''),
    ('bve', '', 'Lumière et couleur', 'Couleur B − V effective', 'mag', 'mesuré', ''),
    ('brief', 'e_brief', 'Lumière et couleur', 'Brillance de surface moyenne dans le rayon effectif (B)', 'mag/arcsec²', 'mesuré', ''),
    ('m21', 'e_m21', 'Lumière et couleur', 'Magnitude de la raie 21 cm (hydrogène neutre)', 'mag', 'mesuré', ''),
    ('mfir', '', 'Lumière et couleur', 'Magnitude infrarouge lointain', 'mag', 'mesuré', ''),
    ('ag', '', 'Lumière et couleur', 'Extinction par la Voie lactée (B)', 'mag', 'modèle', 'd’après une carte de poussière galactique'),
    ('ai', '', 'Lumière et couleur', 'Extinction interne (B)', 'mag', 'modèle', 'd’après l’inclinaison et le type'),
    ('btc', '', 'Lumière et couleur', 'Magnitude B corrigée (extinctions, décalage)', 'mag', 'modèle', ''),
    ('itc', '', 'Lumière et couleur', 'Magnitude I corrigée', 'mag', 'modèle', ''),
    ('ubtc', '', 'Lumière et couleur', 'Couleur U − B corrigée', 'mag', 'modèle', ''),
    ('bvtc', '', 'Lumière et couleur', 'Couleur B − V corrigée', 'mag', 'modèle', ''),
    ('bri25', '', 'Lumière et couleur', 'Brillance de surface moyenne dans D25 (corrigée)', 'mag/arcsec²', 'modèle', ''),
    ('m21c', '', 'Lumière et couleur', 'Magnitude 21 cm corrigée de l’autoabsorption', 'mag', 'modèle', ''),
    ('hic', '', 'Lumière et couleur', 'Indice hydrogène neutre (m21c − btc)', 'mag', 'calculé', 'calculé par HyperLEDA'),
    ('mabs', 'e_mabs', 'Lumière et couleur', 'Magnitude absolue B', 'mag', 'modèle',
     'btc − modbest : dépend de la distance retenue par HyperLEDA (mesurée si connue, sinon d’après la vitesse)'),
]


def leda_tableau(cle_pgc, rows):
    t = Tableau([(c[2], c[3], c[4], c[5], S_LEDA + (' ; ' + c[6] if c[6] else '')) for c in LEDA_COLS])
    for cle, pgc in cle_pgc.items():
        r = rows.get(pgc)
        if not r:
            continue
        r = dict(r)
        if fl(r.get('al2000')) is not None:
            r['al2000'] = f"{float(r['al2000']) * 15:.6f}"
        if fl(r.get('mod0')) is not None:
            r['dist0'] = g(10 ** ((float(r['mod0']) - 25) / 5))
        if fl(r.get('logd25')) is not None:
            r['d25'] = g(0.1 * 10 ** float(r['logd25']))
        if fl(r.get('logr25')) is not None:
            r['ba'] = g(10 ** -float(r['logr25']), 3)
        for c in LEDA_COLS:
            t.mettre(cle, c[3], r.get(c[0]), r.get(c[1]) if c[1] else '')
    return t


# ------------------------------------------------------------------ Cosmicflows-4, groupes

METHODES = [('DMsnIa', 'supernovas Ia'), ('DMtf', 'Tully-Fisher'), ('DMfp', 'plan fondamental'),
            ('DMsbf', 'fluctuations de brillance de surface'), ('DMsnII', 'supernovas II'),
            ('DMtrgb', 'pointe des géantes rouges (TRGB)'), ('DMceph', 'céphéides'), ('DMmas', 'masers')]


def dist_mpc(dm, e):
    d = 10 ** ((dm - 25) / 5)
    if e is None:
        return g(d), ''
    hi, lo = 10 ** ((dm + e - 25) / 5) - d, d - 10 ** ((dm - e - 25) / 5)
    a, b = g(hi, 2), g(lo, 2)
    return g(d), a if a == b else f'+{a}/-{b}'


def cf4_tableau(cle_pgc, cf4, groupes, kt_gal, kt_grp):
    S_G = 'Cosmicflows-4, groupes (Tully et al. 2023, tables 3-4)'
    cols = [('Position', 'Module de distance Cosmicflows-4 (toutes méthodes)', 'mag', 'mesuré', S_CF4),
            ('Position', 'Distance Cosmicflows-4', 'Mpc', 'calculé', S_CF4 + ' ; calculé ici : 10^((DM − 25)/5), échelle H0 = 75')]
    cols += [('Position', f'Module de distance ({t})', 'mag', 'mesuré', S_CF4) for _, t in METHODES]
    cols += [('Mouvement', 'Vitesse systémique par rapport au fond diffus (CF4)', 'km/s', 'mesuré', S_CF4),
             ('Groupe et amas', 'Galaxie principale du groupe (CF4)', '', 'publié', S_CF4),
             ('Groupe et amas', 'Groupe de Tempel et al. 2017 (numéro)', '', 'publié', S_CF4 + ' ; Tempel et al. 2017, A&A 602, A100'),
             ('Groupe et amas', 'Nombre de galaxies du groupe (CF4)', '', 'publié', S_G),
             ('Groupe et amas', 'Module de distance du groupe (CF4)', 'mag', 'mesuré', S_G + ' ; DMzp'),
             ('Groupe et amas', 'Distance du groupe (CF4)', 'Mpc', 'calculé', S_G + ' ; distance de luminosité de DMzp, publiée'),
             ('Groupe et amas', 'Vitesse héliocentrique du groupe', 'km/s', 'mesuré', S_G),
             ('Groupe et amas', 'Vitesse du groupe par rapport au fond diffus', 'km/s', 'calculé', S_G + ' ; V3k'),
             ('Groupe et amas', 'Vitesse particulière du groupe', 'km/s', 'modèle', S_G + ' ; Vpec, éq. 11, avec H0 = 75 supposé'),
             ('Groupe et amas', 'Groupe de Kourkchi & Tully 2017 (galaxie principale)', '', 'publié', S_KT),
             ('Groupe et amas', 'Nombre de galaxies du groupe (KT17)', '', 'publié', S_KT),
             ('Groupe et amas', 'Distance du groupe (KT17)', 'Mpc', 'mesuré', S_KT + ' ; incertitude calculée ici depuis le % publié'),
             ('Groupe et amas', 'Dispersion des vitesses du groupe', 'km/s', 'mesuré', S_KT + ' ; sigmaV'),
             ('Groupe et amas', 'Rayon viriel projeté du groupe', 'Mpc', 'mesuré', S_KT + ' ; Rg'),
             ('Groupe et amas', 'Rayon du second retournement du groupe', 'Mpc', 'modèle', S_KT + ' ; R2t, d’après la luminosité K'),
             ('Groupe et amas', 'log de la masse dynamique du groupe', 'log masses solaires', 'modèle', S_KT + ' ; théorème du viriel'),
             ('Groupe et amas', 'log de la masse du groupe d’après sa luminosité K', 'log masses solaires', 'modèle', S_KT + ' ; logMK'),
             ('Groupe et amas', 'log de la luminosité K du groupe', 'log luminosités solaires', 'calculé', S_KT + ' ; logK')]
    t = Tableau(cols)
    for cle, pgc in cle_pgc.items():
        r = cf4.get(pgc)
        if r:
            dm, e = fl(r['DM']), fl(r['e_DM'])
            t.mettre(cle, cols[0][1], r['DM'], r['e_DM'])
            if dm is not None:
                t.mettre(cle, cols[1][1], *dist_mpc(dm, e))
            for k, tx in METHODES:
                t.mettre(cle, f'Module de distance ({tx})', r.get(k), r.get('e_' + k))
            t.mettre(cle, 'Vitesse systémique par rapport au fond diffus (CF4)', r['Vcmb'])
            if val(r['1PGC']) and r['1PGC'] != str(pgc):
                t.mettre(cle, 'Galaxie principale du groupe (CF4)', 'PGC ' + r['1PGC'])
            t.mettre(cle, 'Groupe de Tempel et al. 2017 (numéro)', r['T17'])
            gr = groupes.get(fl(r['1PGC']) and int(r['1PGC']))
            if gr:
                t.mettre(cle, 'Nombre de galaxies du groupe (CF4)', gr['Ngal'])
                t.mettre(cle, 'Module de distance du groupe (CF4)', gr['DMzp'], gr['e_DMzp'])
                t.mettre(cle, 'Distance du groupe (CF4)', gr['Dist'])
                t.mettre(cle, 'Vitesse héliocentrique du groupe', gr['Vh'])
                t.mettre(cle, 'Vitesse du groupe par rapport au fond diffus', gr['V3k'])
                t.mettre(cle, 'Vitesse particulière du groupe', gr['Vpec'])
        p1 = kt_gal.get(pgc)
        k = kt_grp.get(p1) if p1 else None
        if k:
            t.mettre(cle, 'Groupe de Kourkchi & Tully 2017 (galaxie principale)', f'PGC {p1}')
            t.mettre(cle, 'Nombre de galaxies du groupe (KT17)', k['Nm'])
            d, e = fl(k['Dist']), fl(k['e_Dist'])
            t.mettre(cle, 'Distance du groupe (KT17)', k['Dist'], g(d * e / 100, 2) if d and e else '')
            t.mettre(cle, 'Dispersion des vitesses du groupe', k['sigmaV'])
            t.mettre(cle, 'Rayon viriel projeté du groupe', k['Rg'])
            t.mettre(cle, 'Rayon du second retournement du groupe', k['R2t'])
            t.mettre(cle, 'log de la masse dynamique du groupe', k['logMd'])
            t.mettre(cle, 'log de la masse du groupe d’après sa luminosité K', k['logMK'])
            t.mettre(cle, 'log de la luminosité K du groupe', k['logK'])
    return t


# ------------------------------------------------------------------ SGA-2020

def sga_tableau(cle_sga, S):
    from astropy.cosmology import FlatLambdaCDM
    cosmo = FlatLambdaCDM(H0=67.4, Om0=0.315)
    cols = [('Identité', 'Nom dans le Siena Galaxy Atlas', '', 'publié', S_SGA),
            ('Identité', 'Groupe SGA', '', 'publié', S_SGA),
            ('Identité', 'Type morphologique (SGA, d’après HyperLEDA)', '', 'publié', S_SGA),
            ('Position', 'Ascension droite (SGA, J2000)', '°', 'mesuré', S_SGA),
            ('Position', 'Déclinaison (SGA, J2000)', '°', 'mesuré', S_SGA),
            ('Position', 'Décalage vers le rouge z (HyperLEDA, repris par SGA)', '', 'mesuré', S_SGA),
            ('Position', 'Distance d’après z (Planck 2018, distance comobile)', 'Mpc', 'modèle',
             S_SGA + ' ; calculé ici avec H0 = 67,4, Ωm = 0,315 (sans correction de vitesse propre)'),
            ('Physique', 'Diamètre D26 (isophote 26 mag/arcsec², r)', '′', 'mesuré', S_SGA),
            ('Physique', 'Origine du diamètre', '', 'publié', S_SGA + ' ; SB26 = mesuré à 26 mag/arcsec², sinon repris d’un catalogue'),
            ('Physique', 'Angle de position (SGA)', '°', 'mesuré', S_SGA + ' ; du nord vers l’est'),
            ('Physique', 'Rapport des axes b/a (SGA)', '', 'mesuré', S_SGA),
            ('Physique', 'Demi-grand axe contenant la moitié de la lumière (r)', '″', 'mesuré', S_SGA),
            ('Lumière et couleur', 'Magnitude g dans l’isophote 26', 'mag (AB)', 'mesuré', S_SGA + ' ; erreur statistique'),
            ('Lumière et couleur', 'Magnitude r dans l’isophote 26', 'mag (AB)', 'mesuré', S_SGA + ' ; erreur statistique'),
            ('Lumière et couleur', 'Magnitude z dans l’isophote 26', 'mag (AB)', 'mesuré', S_SGA + ' ; erreur statistique'),
            ('Lumière et couleur', 'Couleur g − r (isophote 26)', 'mag', 'calculé', S_SGA + ' ; calculé ici'),
            ('Lumière et couleur', 'Magnitude totale g (courbe de croissance)', 'mag (AB)', 'modèle', S_SGA + ' ; extrapolée par un modèle'),
            ('Lumière et couleur', 'Magnitude totale r (courbe de croissance)', 'mag (AB)', 'modèle', S_SGA + ' ; extrapolée par un modèle'),
            ('Lumière et couleur', 'Magnitude totale z (courbe de croissance)', 'mag (AB)', 'modèle', S_SGA + ' ; extrapolée par un modèle')]
    t = Tableau(cols)
    L = [c[1] for c in cols]
    for cle, i in cle_sga.items():
        r = S[i]
        pos = lambda x: g(float(x), 6) if x is not None and np.isfinite(x) and x > 0 else ''
        t.mettre(cle, L[0], str(r['GALAXY']).strip())
        if r['GROUP_MULT'] > 1:
            t.mettre(cle, L[1], str(r['GROUP_NAME']).strip())
        t.mettre(cle, L[2], str(r['MORPHTYPE']).strip())
        t.mettre(cle, L[3], f"{r['RA']:.6f}")
        t.mettre(cle, L[4], f"{r['DEC']:.6f}")
        z = float(r['Z_LEDA'])
        if np.isfinite(z) and z > 0:
            t.mettre(cle, L[5], g(z, 5))
            t.mettre(cle, L[6], g(cosmo.comoving_distance(z).to_value('Mpc')))
        t.mettre(cle, L[7], pos(r['D26']))
        t.mettre(cle, L[8], str(r['D26_REF']).strip())
        if r['BA'] > 0:
            t.mettre(cle, L[9], g(float(r['PA']), 4))
            t.mettre(cle, L[10], g(float(r['BA']), 3))
        t.mettre(cle, L[11], pos(r['R_SMA50']))
        m = {}
        for b, lib in (('G', L[12]), ('R', L[13]), ('Z', L[14])):
            x, e = float(r[f'{b}_MAG_SB26']), float(r[f'{b}_MAG_SB26_ERR'])
            if np.isfinite(x) and x > 0:
                m[b] = x
                t.mettre(cle, lib, f'{x:.3f}', g(float(e), 2) if np.isfinite(e) and e > 0 else '')
        if 'G' in m and 'R' in m:
            t.mettre(cle, L[15], f"{m['G'] - m['R']:.3f}")
        for b, lib in (('G', L[16]), ('R', L[17]), ('Z', L[18])):
            x = float(r[f'{b}_COG_PARAMS_MTOT'])
            if np.isfinite(x) and x > 0:
                t.mettre(cle, lib, f'{x:.3f}')
    return t


# ------------------------------------------------------------------ format long : catalogues du Volume local

LVDB_COLS = [  # (colonne, groupe, libellé, unité, statut, colonne de référence, note)
    ('host', 'Identité', 'Galaxie hôte (LVDB)', '', 'publié', '', 'mw = Voie lactée, m31 = Andromède'),
    ('distance_modulus', 'Position', 'Module de distance', 'mag', 'mesuré', 'ref_distance', ''),
    ('distance', 'Position', 'Distance', 'kpc', 'calculé', 'ref_distance', 'calculé par la base depuis le module de distance'),
    ('distance_measurement_method', 'Position', 'Méthode de la distance', '', 'publié', 'ref_distance', ''),
    ('distance_gc', 'Position', 'Distance au centre de la Voie lactée', 'kpc', 'calculé', '', 'calculé par la base'),
    ('distance_m31', 'Position', 'Distance à Andromède', 'kpc', 'calculé', '', 'calculé par la base'),
    ('vlos_systemic', 'Mouvement', 'Vitesse radiale héliocentrique', 'km/s', 'mesuré', 'ref_vlos', ''),
    ('vlos_sigma', 'Mouvement', 'Dispersion des vitesses des étoiles', 'km/s', 'mesuré', 'ref_vlos', ''),
    ('pmra', 'Mouvement', 'Mouvement propre en ascension droite (μα cos δ)', 'mas/an', 'mesuré', 'ref_proper_motion', ''),
    ('pmdec', 'Mouvement', 'Mouvement propre en déclinaison', 'mas/an', 'mesuré', 'ref_proper_motion', ''),
    ('velocity_gsr', 'Mouvement', 'Vitesse par rapport au centre galactique', 'km/s', 'calculé', '', 'calculé par la base'),
    ('velocity_lg', 'Mouvement', 'Vitesse par rapport au Groupe local', 'km/s', 'calculé', '', 'calculé par la base'),
    ('rhalf', 'Physique', 'Rayon de demi-lumière (grand axe)', '′', 'mesuré', 'ref_structure', ''),
    ('rhalf_physical', 'Physique', 'Rayon de demi-lumière', 'pc', 'calculé', 'ref_structure', 'calculé par la base avec la distance'),
    ('ellipticity', 'Physique', 'Ellipticité (1 − b/a)', '', 'mesuré', 'ref_structure', ''),
    ('position_angle', 'Physique', 'Angle de position', '°', 'mesuré', 'ref_structure', 'du nord vers l’est'),
    ('rcore', 'Physique', 'Rayon de cœur (profil de King)', '′', 'mesuré', 'ref_structure_king', ''),
    ('rking', 'Physique', 'Rayon de marée (profil de King)', '′', 'mesuré', 'ref_structure_king', ''),
    ('rad_sersic', 'Physique', 'Rayon de Sérsic', '′', 'mesuré', 'ref_structure_sersic', ''),
    ('n_sersic', 'Physique', 'Indice de Sérsic', '', 'mesuré', 'ref_structure_sersic', ''),
    ('mass_dynamical_wolf', 'Physique', 'log de la masse dynamique dans le rayon de demi-lumière', 'log masses solaires', 'modèle',
     'ref_vlos', 'estimateur de Wolf et al. 2010 appliqué par la base'),
    ('mass_stellar', 'Physique', 'log de la masse stellaire', 'log masses solaires', 'modèle', 'ref_m_v',
     'rapport masse/luminosité supposé par la base'),
    ('mass_HI', 'Physique', 'log de la masse d’hydrogène neutre', 'log masses solaires', 'calculé', 'ref_flux_HI',
     'calculé par la base depuis le flux HI'),
    ('apparent_magnitude_v', 'Lumière et couleur', 'Magnitude apparente V', 'mag', 'mesuré', 'ref_m_v', ''),
    ('M_V', 'Lumière et couleur', 'Magnitude absolue V', 'mag', 'calculé', 'ref_m_v', 'calculé par la base : V − module de distance'),
    ('surface_brightness_rhalf', 'Lumière et couleur', 'Brillance de surface moyenne dans le rayon de demi-lumière', 'mag/arcsec²',
     'calculé', 'ref_m_v', 'calculé par la base'),
    ('flux_HI', 'Lumière et couleur', 'Flux de la raie 21 cm (HI)', 'Jy km/s', 'mesuré', 'ref_flux_HI', ''),
    ('metallicity_spectroscopic', 'Âge et évolution', 'Métallicité [Fe/H] (spectroscopie)', 'dex', 'mesuré',
     'ref_metallicity_spectroscopic', ''),
    ('metallicity_spectroscopic_sigma', 'Âge et évolution', 'Dispersion de la métallicité (spectroscopie)', 'dex', 'mesuré',
     'ref_metallicity_spectroscopic', ''),
    ('metallicity_photometric', 'Âge et évolution', 'Métallicité [Fe/H] (photométrie)', 'dex', 'mesuré',
     'ref_metallicity_photometric', ''),
    ('metallicity_isochrone', 'Âge et évolution', 'Métallicité d’après les isochrones', 'dex', 'modèle', 'ref_metallicity_isochrone', ''),
    ('age', 'Âge et évolution', 'Âge moyen des étoiles', 'milliards d’années', 'modèle', 'ref_age', 'ajusté sur des isochrones'),
]


def lvdb_lignes(F, cle, r):
    for c, grp, lib, u, st, ref, note in LVDB_COLS:
        v, ul = val(r.get(c)), val(r.get(c + '_ul'))
        if not v and ul:
            v = '<' + ul
        src = S_LVDB + (' ; réf. ' + r[ref] if ref and val(r.get(ref)) else '') + (' ; ' + note if note else '')
        F.add(cle, grp, lib, v, asym(r.get(c + '_ep'), r.get(c + '_em')), u, st, src)


def mcc_lignes(F, cle, r, refs):
    def src(*cols):
        bib = [refs.get(x.strip(), x.strip()) for c in cols for x in val(r.get(c)).split(',') if x.strip()]
        return S_MC + (' ; réf. ' + ', '.join(bib) if bib else '')

    def a(col, grp, lib, u, st, ref, note='', lim=''):
        v = val(r.get(col))
        if v and lim and val(r.get(lim)):
            v = r[lim].strip() + v
        flag = val(r.get('u_' + col)) or val(r.get('f_' + col))
        n = (' ; ' + note if note else '') + (f' ; drapeau « {flag} » du catalogue' if flag else '')
        F.add(cle, grp, lib, v, asym(r.get('E_' + col), r.get('e_' + col)), u, st, src(ref) + n)

    F.add(cle, 'Identité', 'Type morphologique (McConnachie 2012)', r.get('MType'), '', '', 'publié', S_MC)
    F.add(cle, 'Identité', 'Sous-groupe du Groupe local', r.get('SubG'), '', '', 'publié', S_MC)
    a('(m-M)', 'Position', 'Module de distance (McConnachie 2012)', 'mag', 'mesuré', 'Ref2')
    a('D', 'Position', 'Distance (McConnachie 2012)', 'kpc', 'calculé', 'Ref2', 'calculé par le catalogue depuis le module')
    a('HRV', 'Mouvement', 'Vitesse radiale héliocentrique (McConnachie 2012)', 'km/s', 'mesuré', 'Ref2')
    a('E(B-V)', 'Lumière et couleur', 'Rougissement par la Voie lactée E(B−V)', 'mag', 'modèle', 'Ref2', 'carte de poussière')
    a('Vmag', 'Lumière et couleur', 'Magnitude apparente V (McConnachie 2012)', 'mag', 'mesuré', 'Ref3')
    a('VMag', 'Lumière et couleur', 'Magnitude absolue V (McConnachie 2012)', 'mag', 'calculé', 'Ref3', 'V − module de distance')
    a('muV', 'Lumière et couleur', 'Brillance de surface centrale V', 'mag/arcsec²', 'mesuré', 'Ref3')
    a('R1', 'Physique', 'Rayon de demi-lumière (McConnachie 2012)', '′', 'mesuré', 'Ref3')
    a('R2', 'Physique', 'Rayon de demi-lumière physique (McConnachie 2012)', 'pc', 'calculé', 'Ref3', 'calculé avec la distance')
    a('PA', 'Physique', 'Angle de position (McConnachie 2012)', '°', 'mesuré', 'Ref3')
    a('Ell', 'Physique', 'Ellipticité (McConnachie 2012)', '', 'mesuré', 'Ref3')
    a('Mass', 'Physique', 'Masse stellaire', 'millions de masses solaires', 'modèle', 'Ref3', 'rapport masse/luminosité = 1 supposé')
    a('sigma*', 'Physique', 'Dispersion des vitesses des étoiles (McConnachie 2012)', 'km/s', 'mesuré', 'Ref4', lim='l_sigma*')
    a('vsini*', 'Physique', 'Rotation des étoiles (v sin i)', 'km/s', 'mesuré', 'Ref4')
    a('M.HI', 'Physique', 'Masse d’hydrogène neutre', 'millions de masses solaires', 'calculé', 'Ref4', 'flux HI et distance')
    a('sigHI', 'Physique', 'Dispersion des vitesses du gaz HI', 'km/s', 'mesuré', 'Ref4', lim='l_sigHI')
    a('v.HI', 'Physique', 'Vitesse de rotation du gaz HI', 'km/s', 'mesuré', 'Ref4', lim='l_v.HI')
    a('Mdyn', 'Physique', 'Masse dynamique', 'millions de masses solaires', 'modèle', 'Ref4', 'estimateur du catalogue')
    a('[Fe/H]', 'Âge et évolution', 'Métallicité [Fe/H] (McConnachie 2012)', 'dex', 'mesuré', 'Ref5')
    F.add(cle, 'Âge et évolution', 'Méthode de la métallicité', r.get('Meth'), '', '', 'publié', src('Ref5'))
    F.add(cle, 'Autres noms', 'Noms (McConnachie 2012)', ', '.join(x for x in (val(r.get('Name')), val(r.get('OName'))) if x),
          '', '', 'publié', S_MC)


UNGC_COLS = [  # (colonne, groupe, libellé, unité, statut, note)
    ('Dist', 'Position', 'Distance (UNGC)', 'Mpc', 'mesuré', ''),
    ('HRV', 'Mouvement', 'Vitesse radiale héliocentrique (UNGC)', 'km/s', 'mesuré', ''),
    ('Vlg', 'Mouvement', 'Vitesse par rapport au Groupe local (UNGC)', 'km/s', 'calculé', 'calculé par le catalogue'),
    ('TT', 'Identité', 'Indice de type morphologique T (UNGC)', '', 'publié', ''),
    ('Mcl', 'Identité', 'Classe de galaxie naine (UNGC)', '', 'publié', ''),
    ('a26', 'Physique', 'Diamètre apparent (Holmberg, 26,5 mag/arcsec²)', '′', 'mesuré', ''),
    ('b/a', 'Physique', 'Rapport des axes b/a (UNGC)', '', 'mesuré', ''),
    ('A26', 'Physique', 'Diamètre linéaire', 'kpc', 'calculé', 'calculé par le catalogue avec la distance'),
    ('i', 'Physique', 'Inclinaison (UNGC)', '°', 'modèle', 'déduite du rapport des axes'),
    ('W50', 'Physique', 'Largeur de la raie HI à mi-hauteur', 'km/s', 'mesuré', ''),
    ('vAmp', 'Physique', 'Amplitude de la rotation', 'km/s', 'modèle', 'W50 corrigée de l’inclinaison'),
    ('M26', 'Physique', 'log de la masse dans le rayon de Holmberg', 'log masses solaires', 'modèle', 'estimateur du catalogue'),
    ('MHI', 'Physique', 'log de la masse d’hydrogène neutre (UNGC)', 'log masses solaires', 'calculé', 'calculé par le catalogue'),
    ('KLum', 'Physique', 'log de la luminosité en bande K', 'log luminosités solaires', 'calculé', 'calculé par le catalogue'),
    ('FUV', 'Lumière et couleur', 'Magnitude ultraviolet lointain (GALEX FUV)', 'mag', 'mesuré', ''),
    ('Bmag', 'Lumière et couleur', 'Magnitude B (UNGC)', 'mag', 'mesuré', ''),
    ('Kmag', 'Lumière et couleur', 'Magnitude Ks (UNGC)', 'mag', 'mesuré', ''),
    ('Hamag', 'Lumière et couleur', 'Magnitude de la raie Hα', 'mag', 'mesuré', ''),
    ('HImag', 'Lumière et couleur', 'Magnitude de la raie 21 cm (UNGC)', 'mag', 'mesuré', ''),
    ('BMag', 'Lumière et couleur', 'Magnitude absolue B (UNGC)', 'mag', 'calculé', 'calculé par le catalogue'),
    ('<Bmu>', 'Lumière et couleur', 'Brillance de surface moyenne B', 'mag/arcsec²', 'calculé', 'calculé par le catalogue'),
    ('AB', 'Lumière et couleur', 'Extinction par la Voie lactée (B, UNGC)', 'mag', 'modèle', 'carte de poussière'),
    ('Ti1', 'Groupe et amas', 'Indice de marée Θ1', '', 'modèle', 'calculé par le catalogue (masses d’après la luminosité)'),
    ('MD', 'Groupe et amas', 'Voisin dominant (marées)', '', 'publié', ''),
    ('Ti5', 'Groupe et amas', 'Indice de marée Θ5', '', 'modèle', 'calculé par le catalogue'),
]


def ungc_lignes(F, cle, r):
    for c, grp, lib, u, st, note in UNGC_COLS:
        v = val(r.get(c))
        if v and val(r.get('l_' + c)):
            v = r['l_' + c].strip() + v
        if c == 'Dist' and val(r.get('f_Dist')):
            note = 'méthode : ' + r['f_Dist']
        if c == 'Kmag' and val(r.get('f_Kmag')):
            st, note = 'modèle', 'estimée par le catalogue (drapeau *)'
        F.add(cle, grp, lib, v, '', u, st, S_UNGC + (' ; ' + note if note else ''))


# ------------------------------------------------------------------ SIMBAD, amas, trous noirs

PREFIXES = ('M ', 'NGC', 'IC ', 'UGC', 'PGC', 'ESO', 'DDO', 'NAME', 'ACO', 'MCG', 'KK', 'Arp', 'CGCG', 'LEDA', 'Holm',
            'HIPASS', 'MCXC', 'Z ')


def simbad_lignes(F, cle, b, ids, flux):
    S = S_SIM + ' ; ' + b['main_id']
    F.add(cle, 'Identité', 'Identifiant SIMBAD', b['main_id'], '', '', 'publié', S_SIM)
    F.add(cle, 'Identité', 'Nature (code SIMBAD)', b['otype'], '', '', 'publié', S_SIM)
    F.add(cle, 'Identité', 'Type morphologique (SIMBAD)', b['morph_type'], '', '', 'publié', S_SIM)
    F.add(cle, 'Position', 'Ascension droite (SIMBAD, ICRS)', g(fl(b['ra']), 9), '', '°', 'mesuré', S)
    F.add(cle, 'Position', 'Déclinaison (SIMBAD, ICRS)', g(fl(b['dec']), 9), '', '°', 'mesuré', S)
    rs = S + (' ; réf. ' + b['rvz_bibcode'] if val(b['rvz_bibcode']) else '') + \
        (' ; qualité ' + b['rvz_qual'] if val(b.get('rvz_qual')) else '')
    if b['rvz_type'] == 'v':
        F.add(cle, 'Mouvement', 'Vitesse radiale (SIMBAD)', b['rvz_radvel'], b['rvz_err'], 'km/s', 'mesuré', rs)
    elif b['rvz_type'] == 'z':
        F.add(cle, 'Position', 'Décalage vers le rouge z (SIMBAD)', b['rvz_redshift'], b['rvz_err'], '', 'mesuré', rs)
    gs = S + (' ; réf. ' + b['galdim_bibcode'] if val(b['galdim_bibcode']) else '')
    F.add(cle, 'Physique', 'Grand axe apparent (SIMBAD)', b['galdim_majaxis'], '', '′', 'mesuré', gs)
    F.add(cle, 'Physique', 'Petit axe apparent (SIMBAD)', b['galdim_minaxis'], '', '′', 'mesuré', gs)
    if b['galdim_angle'] != '32767':      # 32767 = case vide dans SIMBAD
        F.add(cle, 'Physique', 'Angle de position (SIMBAD)', b['galdim_angle'], '', '°', 'mesuré', gs)
    for f in sorted(flux, key=lambda x: 'UBVRIJHKugriz'.find(x['filter']) % 99):
        F.add(cle, 'Lumière et couleur', f"Magnitude {f['filter']} (SIMBAD)", f['flux'], f['flux_err'], 'mag', 'mesuré',
              S_SIM + (' ; réf. ' + f['bibcode'] if val(f['bibcode']) else ''))
    noms = sorted({re.sub(r'\s+', ' ', i).replace('NAME ', '') for i in ids if i.startswith(PREFIXES)})
    F.add(cle, 'Autres noms', 'Autres noms (SIMBAD)', ', '.join(noms[:30]), '', '', 'publié', S_SIM)


def amas_lignes(F, cle, mcxc, aco, prefixe=''):
    S = 'MCXC (Piffaretti et al. 2011, A&A 534, A109)'
    if mcxc:
        F.add(cle, 'Identité', prefixe + 'Nom MCXC', 'MCXC J' + mcxc['MCXC'].lstrip('J'), '', '', 'publié', S)
        F.add(cle, 'Position', prefixe + 'Décalage vers le rouge z (MCXC)', mcxc['z'], '', '', 'mesuré', S)
        F.add(cle, 'Lumière et couleur', prefixe + 'Luminosité X dans R500 (0,1-2,4 keV)', mcxc['L500'], '', '10^44 erg/s', 'mesuré',
              S + ' ; catalogue d’origine ' + mcxc['Cat'])
        F.add(cle, 'Physique', prefixe + 'Masse M500', mcxc['M500'], '', '10^14 masses solaires', 'modèle',
              S + ' ; d’après la luminosité X (relation luminosité-masse)')
        F.add(cle, 'Physique', prefixe + 'Rayon R500', mcxc['R500'], '', 'Mpc', 'modèle', S + ' ; d’après M500')
    S = 'Abell, Corwin & Olowin 1989 (ApJS 70, 1)'
    if aco:
        F.add(cle, 'Identité', prefixe + 'Nom Abell', 'Abell ' + aco['ACO'].lstrip('0'), '', '', 'publié', S)
        F.add(cle, 'Identité', prefixe + 'Classe de richesse (Abell)', aco['Rich'], '', '', 'publié', S)
        F.add(cle, 'Identité', prefixe + 'Type de Bautz-Morgan', aco['BMtype'], '', '', 'publié', S)
        F.add(cle, 'Position', prefixe + 'Classe de distance (Abell)', aco['Dclass'], '', '', 'publié', S)
        F.add(cle, 'Physique', prefixe + 'Nombre de galaxies comptées (Abell)', aco['Count'], '', '', 'mesuré', S)
        F.add(cle, 'Lumière et couleur', prefixe + 'Magnitude de la 10e galaxie la plus brillante', aco['m10'], '', 'mag', 'mesuré', S)
        F.add(cle, 'Position', prefixe + 'Décalage vers le rouge z (Abell)', aco['z'], '', '', 'mesuré', S)


def trou_noir_lignes(F, cle, r):
    q = 'valeur retenue' if r['prefere'] == '1' else 'autre mesure'
    S = r['source']
    lm, eh, eb = fl(r['log_masse']), fl(r['err_haut_dex']), fl(r['err_bas_dex'])
    lim = r['limite_sup'] == '1'
    F.add(cle, 'Trou noir central', f'Nom du trou noir ({q})', r['nom'], '', '', 'publié', S)
    F.add(cle, 'Trou noir central', f'log de la masse ({q})', ('<' if lim else '') + r['log_masse'],
          '' if lim else asym(r['err_haut_dex'], r['err_bas_dex']), 'log masses solaires', 'mesuré', S)
    if lm is not None:
        m = 10 ** lm
        inc = '' if lim or eh is None else f'+{g(10 ** (lm + eh) - m, 2)}/-{g(m - 10 ** (lm - (eb if eb is not None else eh)), 2)}'
        F.add(cle, 'Trou noir central', f'Masse ({q})', ('<' if lim else '') + g(m, 3), inc, 'masses solaires', 'calculé',
              S + ' ; calculé ici : 10^log')
    F.add(cle, 'Trou noir central', f'Méthode de mesure ({q})', r['methode'], '', '', 'publié', S)
    if fl(r['dist_mpc']):      # « 0.0 » = arrondi de la table (Voie lactée) : pas affiché
        F.add(cle, 'Trou noir central', f'Distance adoptée par la mesure ({q})', r['dist_mpc'], r['e_dist_mpc'], 'Mpc', 'mesuré', S)
    ls = fl(r['log_sigma_kms'])
    if ls is not None:
        F.add(cle, 'Trou noir central', 'log de la dispersion des vitesses du bulbe σe', r['log_sigma_kms'], '', 'log km/s', 'mesuré', S)
        F.add(cle, 'Trou noir central', 'Dispersion des vitesses du bulbe σe', g(10 ** ls, 3), '', 'km/s', 'calculé', S + ' ; 10^log')


# ------------------------------------------------------------------ grandes structures

BASSINS = {'Laniakea': 'Laniakea (bassin CF4)', 'Bassin de Apus': 'Apus (bassin CF4)', 'Bassin de Hercule': 'Hercules (bassin CF4)',
           'Bassin de Lepus': 'Lepus (bassin CF4)', 'Bassin de Persée-Poissons': 'Perseus-Pisces (bassin CF4)',
           'Bassin de Shapley': 'Shapley (bassin CF4)'}
SUPER = {'Superamas de Coma': 'Coma Supercluster', 'Superamas d’Hercule': 'Hercules Supercluster',
         'Superamas de Persée-Poissons': 'Perseus-Pisces Supercluster',
         'Superamas Horloge-Réticule': 'Horologium-Reticulum Supercluster', 'Grand Mur CfA2': 'CfA2 Great Wall',
         'Grand Mur de Sloan': 'Sloan Great Wall', 'Superamas Saraswati': 'Saraswati Supercluster', 'Grand Mur BOSS': 'BOSS Great Wall',
         'Mur du pôle Sud': 'South Pole Wall', 'Superamas de Vela': 'Vela Supercluster', 'Superamas de Shapley': 'Shapley Supercluster',
         'Grand Attracteur': 'Great Attractor (Norma, A3627)'}
S_DC = 'Dupuy & Courtois 2023 (A&A 678, A176 ; arXiv:2305.02339), table 1'
NATURES = {'supercluster': 'superamas', 'wall': 'mur de galaxies', 'basin': 'bassin d’attraction',
           'supercluster-complex': 'complexe de superamas'}


def bassin_lignes(F, cle, r):
    F.add(cle, 'Identité', 'Nature', 'bassin d’attraction (superamas défini par le flot des galaxies)', '', '', 'publié', S_DC)
    m = re.search(r'attracteur \(([-\d.]+), ([-\d.]+), ([-\d.]+)\) Mpc/h ; volume ([\d.e+]+)', r['taille_publiee'])
    if m:
        S = S_DC + ' ; reconstruction du champ de vitesses Cosmicflows-4'
        xyz = [float(m.group(k)) for k in (1, 2, 3)]
        for k, ax in enumerate('XYZ'):
            F.add(cle, 'Position', f'Attracteur, coordonnée supergalactique SG{ax}', m.group(k + 1), '', 'Mpc/h', 'modèle', S)
        F.add(cle, 'Position', 'Distance de l’attracteur', g(math.dist((0, 0, 0), xyz), 3), '', 'Mpc/h', 'calculé',
              S_DC + ' ; calculé ici : √(SGX² + SGY² + SGZ²)')
        F.add(cle, 'Physique', 'Volume du bassin d’attraction', m.group(4), '', '(Mpc/h)³', 'modèle', S)
        F.add(cle, 'Physique', 'Diamètre de la sphère de même volume', g(2 * (3 * float(m.group(4)) / (4 * math.pi)) ** (1 / 3), 3),
              '', 'Mpc/h', 'calculé', S_DC + ' ; calculé ici : 2 (3V/4π)^(1/3) ; le bassin n’est pas une sphère')
    t = re.search(r'Tully et al\. 2014.*?~(\d+) Mpc, ~(\S+) Msun', r['taille_publiee'])
    if t:
        S14 = 'Tully, Courtois, Hoffman & Pomarède 2014 (Nature 513, 71)'
        F.add(cle, 'Physique', 'Diamètre (définition de 2014)', 'environ ' + t.group(1), '', 'Mpc', 'publié', S14)
        F.add(cle, 'Physique', 'Masse (définition de 2014)', 'environ ' + t.group(2), '', 'masses solaires', 'publié', S14)


def superstructure_lignes(F, cle, r):
    S, conv = r['source'], r['conversion']
    st = 'mesuré' if r['statut'].startswith('mesure') else 'modèle'
    F.add(cle, 'Identité', 'Nature', NATURES.get(r['type'], r['type']), '', '', 'publié', S)
    F.add(cle, 'Position', 'Ascension droite du centre adopté', r['ra_deg'], '', '°', st, S + ' ; ' + conv)
    F.add(cle, 'Position', 'Déclinaison du centre adopté', r['dec_deg'], '', '°', st, S + ' ; ' + conv)
    F.add(cle, 'Position', 'Décalage vers le rouge z du centre', r['z'], '', '', st, S + ' ; ' + conv)
    F.add(cle, 'Position', 'Distance du centre d’après z', r['dist_mpc'], '', 'Mpc', 'modèle',
          'superstructures.py : distance comobile, H0 = 74,6, Ωm = 0,3 (choix de modèle)')
    F.add(cle, 'Physique', 'Taille publiée', r['taille_publiee'], '', '', 'publié', S)
    F.add(cle, 'Physique', 'Taille adoptée pour l’affichage', r['taille_mpc'], '', 'Mpc', 'modèle', S + ' ; ' + conv)
    if val(r['membres_sg']):
        F.add(cle, 'Physique', 'Nombre d’amas membres publiés', str(len(r['membres_sg'].split(';'))), '', '', 'publié', S)
    F.add(cle, 'Modèles et hypothèses', 'Statut du centre', {'derive': 'centre dérivé (voir la conversion)', 'debattu': 'existence débattue',
                                                            'mesure': 'centre mesuré'}.get(r['statut'], r['statut']),
          '', '', 'publié', S)
    F.add(cle, 'Modèles et hypothèses', 'Conversion appliquée', conv, '', '', 'publié', 'superstructures.py')


def vide_lignes(F, cle, r):
    S = ('Malandrino et al. 2026 (A&A 705, A160), 100 vides du voisinage (reconstructions Manticore-Local du relevé 2M++) ; '
         'moyenne ± écart type a posteriori')
    h = 0.681
    F.add(cle, 'Identité', 'Nature', 'vide cosmique', '', '', 'publié', S)
    for k, ax in ((0, 'x'), (2, 'y'), (4, 'z')):
        F.add(cle, 'Position', f'Centre, coordonnée équatoriale {ax} (boîte du catalogue, observateur en 340,5)',
              g(float(r[k]), 5), g(float(r[k + 1]), 2), 'Mpc/h', 'modèle', S)
    F.add(cle, 'Position', 'Ascension droite du centre', g(float(r[9]), 6), '', '°', 'modèle', S)
    F.add(cle, 'Position', 'Déclinaison du centre', g(float(r[10]), 6), '', '°', 'modèle', S)
    F.add(cle, 'Position', 'Distance du centre', g(float(r[11]), 4), '', 'Mpc/h', 'modèle', S)
    F.add(cle, 'Position', 'Distance du centre (Mpc)', g(float(r[11]) / h, 4), '', 'Mpc', 'calculé',
          S + ' ; calculé ici avec h = 0,681 (cosmologie du catalogue)')
    for k, lib in ((12, 'bord proche'), (13, 'centre'), (14, 'bord lointain')):
        F.add(cle, 'Position', f'Décalage vers le rouge du {lib}', g(float(r[k]), 4), '', '', 'modèle', S + ' ; Ωm = 0,306, h = 0,681')
        F.add(cle, 'Position', f'Vitesse de récession du {lib}', g(float(r[k + 3]), 5), '', 'km/s', 'modèle', S + ' ; c z')
    F.add(cle, 'Physique', 'Rayon effectif', g(float(r[6]), 4), g(float(r[7]), 2), 'Mpc/h', 'modèle', S)
    F.add(cle, 'Physique', 'Rayon effectif (Mpc)', g(float(r[6]) / h, 4), g(float(r[7]) / h, 2), 'Mpc', 'calculé',
          S + ' ; calculé ici avec h = 0,681')
    F.add(cle, 'Physique', 'Rayon effectif (années-lumière)', g(float(r[6]) / h * MPC_LY / 1e6, 4), g(float(r[7]) / h * MPC_LY / 1e6, 2),
          'millions d’années-lumière', 'calculé', S + ' ; calculé ici avec h = 0,681')


def structures(F, app):
    rows = list(csv.DictReader(open(SUPERSTRUCT, encoding='utf-8'), delimiter='\t'))
    nommees = {r['nom']: r for r in rows if r['catalogue'] == 'nommee'}
    vides = [l.rstrip('\n').split(',') for l in open(os.path.join(RAW, 'vides_locaux', 'LocalVoids-master', 'voids_catalog.csv'),
                                                     encoding='utf-8')][1:]
    for o in app['structures_noms'] + app['superstructures_noms'] + [o for o in app['galaxies_noms'] if o['cle'] in SUPER]:
        cle = o['cle']
        if cle in BASSINS and BASSINS[cle] in nommees:
            bassin_lignes(F, cle, nommees[BASSINS[cle]])
        elif cle in SUPER and SUPER[cle] in nommees:
            superstructure_lignes(F, cle, nommees[SUPER[cle]])
        elif cle == 'Vide local':
            vide_lignes(F, cle, vides[10])
        elif (m := re.fullmatch(r'Vide (\d+) du voisinage', cle)):
            vide_lignes(F, cle, vides[int(m.group(1))])
        elif cle == 'Univers observable':
            S = 'calculé avec la cosmologie Planck 2018 (Planck Collaboration 2020, A&A 641, A6), astropy Planck18'
            m = re.search(r': ([\d.]+) milliards.*?partie de ([\d.]+) milliards.*?z = ([\d ,]+)\)', o['texte'])
            if m:
                F.add(cle, 'Identité', 'Nature', 'bord de l’univers observable (horizon des particules)', '', '', 'publié', S)
                F.add(cle, 'Physique', 'Rayon comobile de l’horizon aujourd’hui', m.group(1), '', 'milliards d’années-lumière', 'modèle', S)
                F.add(cle, 'Physique', 'Distance comobile de la surface d’émission du fond diffus', m.group(2), '',
                      'milliards d’années-lumière', 'modèle', S)
                F.add(cle, 'Physique', 'Décalage vers le rouge de cette surface', m.group(3).replace(' ', '').replace(',', '.'), '', '',
                      'modèle', 'Planck Collaboration 2020 (A&A 641, A6)')
        if cle == 'Grand Attracteur':
            t = re.search(r'Abell 3627, cz = ([\d ]+) km/s, (Woudt et al\. \d+)', o['texte'])
            if t:
                F.add(cle, 'Mouvement', 'Vitesse de récession de l’amas de la Règle (A3627), au cœur', t.group(1).replace(' ', ''), '',
                      'km/s', 'mesuré', t.group(2))
            F.add(cle, 'Modèles et hypothèses', 'Position affichée', 'placé sur l’amas de la Règle (Abell 3627) ; à 36 Mpc/h de '
                  'l’attracteur de Laniakea calculé par Dupuy et Courtois 2023', '', '', 'publié', 'structures_noms.tsv')


# ------------------------------------------------------------------ assemblage

def plus_proche(cles, pos, cat_pos, rayon_arcmin):
    """Pour chaque objet d'un catalogue, la clé la plus proche à moins du rayon (une seule correspondance par clé)."""
    if not cles:
        return {}
    arbre = cKDTree(direction(*np.array(pos).T))
    d, i = arbre.query(direction(*np.array(cat_pos).T))
    lim = 2 * math.sin(math.radians(rayon_arcmin / 60) / 2)
    meilleur = {}
    for k, (dd, ii) in enumerate(zip(d, i)):
        if dd < lim and (ii not in meilleur or dd < meilleur[ii][0]):
            meilleur[ii] = (dd, k)
    return {cles[ii]: k for ii, (dd, k) in meilleur.items()}


def sexa(s, heures):
    p = [float(x) for x in s.replace(':', ' ').split()]
    v = abs(p[0]) + p[1] / 60 + (p[2] if len(p) > 2 else 0) / 3600
    return v * 15 if heures else (-v if s.strip().startswith('-') else v)


def main():
    donnees = sys.argv[1] if len(sys.argv) > 1 else r'C:\dev\Univers-PC'
    sortie = sys.argv[2] if len(sys.argv) > 2 else r'C:\tmp\fiches'
    os.makedirs(CACHE, exist_ok=True)
    app = lire_appli(donnees)

    # Cosmicflows-4 et groupes
    cf4 = {int(r['PGC']): r for r in lire_vizier(os.path.join(RAW, 'cf4_table2.tsv'))[0]}
    groupes = {int(r['1PGC']): r for r in lire_vizier(os.path.join(RAW, 'cf4groupes', 'groupes.tsv'))[0]}
    kt_gal = {int(r['PGC']): int(r['PGC1']) for r in lire_vizier(os.path.join(RAW, 'kt17', 'galaxies.tsv'))[0] if val(r['PGC1'])}
    telecharger('https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?-source=J/ApJ/843/16/table2&-out.max=unlimited&-out.all',
                os.path.join(CACHE, 'kt17_groupes.tsv'))      # toutes les colonnes (sigmaV, Rg, R2t…)
    kt_grp = {int(r['PGC1']): r for r in lire_vizier(os.path.join(CACHE, 'kt17_groupes.tsv'))[0]}
    ngc = noms_openngc()
    cle_pgc, pos = {}, {}
    for o in app['galaxies_cf4']:
        m = re.fullmatch(r'PGC (\d+)', o['cle'])
        cands = [int(m.group(1))] if m else [p for p in ngc.get(o['cle'], []) if p in cf4]
        u = direction(o['ra'], o['dec'])
        best = max(cands, key=lambda p: float(u @ direction(float(cf4[p]['RAJ2000']), float(cf4[p]['DEJ2000']))), default=None)
        if best in cf4:
            cle_pgc[o['cle']] = best
            pos[o['cle']] = (float(cf4[best]['RAJ2000']), float(cf4[best]['DEJ2000']))

    # SGA-2020
    from astropy.io import fits
    S = fits.getdata(SGA, 'ELLIPSE')
    gal = np.char.strip(S['GALAXY'].astype(str))
    par_nom = {}      # « NGC 4486 » -> rangée SGA, comme galaxies_formes.py nomme ses galaxies (NGC0224 -> NGC 224)
    for i, n in enumerate(gal):
        m = re.fullmatch(r'(NGC|IC)(\d+)', n)
        if m:
            par_nom.setdefault(f'{m.group(1)} {int(m.group(2))}', i)
    sga_pgc = {}
    for i, p in enumerate(S['PGC']):
        if p > 0:
            sga_pgc.setdefault(int(p), i)
    messier_pgc = {'M104 (NGC 4594)': 42407, 'M86 (NGC 4406)': 40653, 'M90 (NGC 4569)': 41024, 'M98 (NGC 4192)': 39028}
    cle_sga = {}
    for o in app['galaxies_formes_noms']:
        m = re.search(r'(NGC|IC) (\d+)\)?$', o['cle'])
        i = par_nom.get(f'{m.group(1)} {m.group(2)}') if m else None
        if o['cle'] in messier_pgc:
            cle_pgc[o['cle']] = messier_pgc[o['cle']]
            pos[o['cle']] = (o['ra'], o['dec'])
        elif i is not None:
            cle_sga[o['cle']] = i
            if S['PGC'][i] > 0:
                cle_pgc[o['cle']] = int(S['PGC'][i])
            pos[o['cle']] = (float(S['RA'][i]), float(S['DEC'][i]))

    # Astres nommés : SIMBAD
    noms = {o['cle']: o for o in app['galaxies_noms']}
    ses = sesame([(k, o['ra'], o['dec']) for k, o in noms.items()])
    lv = [r for r in csv.DictReader(open(LVDB, encoding='utf-8'))]
    sys.path.insert(0, ICI)
    from naines import cle as cle_naine
    idx = {}
    for i, r in enumerate(lv):
        idx.setdefault(cle_naine(r['name']), i)
    lv_cle = {k: idx[cle_naine(k)] for k in noms if cle_naine(k) in idx}
    reste = [(k, float(lv[lv_cle[k]]['ra']), float(lv[lv_cle[k]]['dec'])) if k in lv_cle else (k, o['ra'], o['dec'])
             for k, o in noms.items() if k not in ses and k not in NON_GALAXIE]
    ses.update(cone_simbad(reste))
    base, ids, flux = simbad([v[0] for v in ses.values()])
    base = {b['main_id']: b for b in base}
    ids_par, flux_par = {}, {}
    for r in ids:
        ids_par.setdefault(r['main_id'], []).append(r['id'])
    for r in flux:
        flux_par.setdefault(r['main_id'], []).append(r)
    for k, o in noms.items():
        sid = ses.get(k, [None])[0]
        pos[k] = (ses[k][1], ses[k][2]) if k in ses else (o['ra'], o['dec'])
        for i in ids_par.get(sid, []):
            m = re.fullmatch(r'(?:PGC|LEDA)\s+(\d+)', i)
            if m and k not in NON_GALAXIE:
                cle_pgc.setdefault(k, int(m.group(1)))

    for k, p in cle_pgc.items():      # SGA par numéro PGC pour toutes les galaxies
        if k not in cle_sga and p in sga_pgc:
            cle_sga[k] = sga_pgc[p]
    leda = hyperleda(cle_pgc.values())
    for k, p in cle_pgc.items():
        r = leda.get(p)
        if k not in pos and r and fl(r.get('al2000')) is not None:
            pos[k] = (float(r['al2000']) * 15, float(r['de2000']))

    F = Fiches()
    for k in noms:
        if k in ses and ses[k][0] in base:
            simbad_lignes(F, k, base[ses[k][0]], ids_par.get(ses[k][0], []), flux_par.get(ses[k][0], []))
        if k in cle_pgc:
            F.add(k, 'Identité', 'Numéro PGC (HyperLEDA)', f'PGC {cle_pgc[k]}', '', '', 'publié', S_SIM + ' (identifiants)')

    # Volume local : LVDB (nom, puis position), McConnachie 2012 et UNGC (position)
    galaxies = [k for k in pos if k not in NON_GALAXIE and not k.startswith(('Vide', 'Bassin', 'Superamas', 'Grand '))]
    gpos = [pos[k] for k in galaxies]
    for k, i in plus_proche(galaxies, gpos, [(float(r['ra']), float(r['dec'])) for r in lv], 2.0).items():
        lv_cle.setdefault(k, i)
    for k, i in lv_cle.items():
        lvdb_lignes(F, k, lv[i])
    mc, mc_refs = lire_vizier(os.path.join(CACHE, 'mcconnachie2012.tsv'))
    refs = {r['Ref']: r['BibCode'] for r in mc_refs}
    mc = [r for r in mc if val(r['RAJ2000'])]
    mc_cle = plus_proche(galaxies, gpos, [(sexa(r['RAJ2000'], True), sexa(r['DEJ2000'], False)) for r in mc], 3.0)
    for k, i in mc_cle.items():
        mcc_lignes(F, k, mc[i], refs)
    ungc = lire_vizier(os.path.join(CACHE, 'ungc2013.tsv'))[0]
    ungc_cle = plus_proche(galaxies, gpos, [(float(r['_RAJ2000']), float(r['_DEJ2000'])) for r in ungc], 1.0)
    for k, i in ungc_cle.items():
        ungc_lignes(F, k, ungc[i])

    # Amas : MCXC, Abell
    mcxc = lire_vizier(os.path.join(CACHE, 'mcxc2011.tsv'))[0]
    par_mcxc = {n.strip(): r for r in mcxc for n in (r['OName'], r['AName']) if n.strip()}
    aco = {int(r['ACO']): r for t in ('table3', 'table4') for r in lire_vizier(os.path.join(CACHE, f'abell_{t}.tsv'))[0]}
    for k, (mn, an) in AMAS.items():
        amas_lignes(F, k, par_mcxc.get(mn), aco.get(an))
    amas_lignes(F, 'Grand Attracteur', par_mcxc.get('A3627'), aco.get(3627), 'Amas de la Règle (A3627) : ')

    # Trous noirs centraux (masses mesurées), reliés par position à la galaxie hôte
    tn = [r for r in csv.DictReader(open(os.path.join(donnees, 'trous_noirs.tsv'), encoding='utf-8'), delimiter='\t')
          if r['type'] == 'smbh']
    vl = [r for r in tn if r['galaxie_hote'] == 'Voie lactee']
    autres = [r for r in tn if r['galaxie_hote'] != 'Voie lactee']
    tn_cle = {}
    for k, i in plus_proche(galaxies, gpos, [(float(r['ra_deg']), float(r['dec_deg'])) for r in autres], 1.5).items():
        tn_cle[k] = i
    for r in sorted(vl, key=lambda r: r['prefere'] != '1'):
        trou_noir_lignes(F, 'Centre de la Voie lactée', r)
    F.add('Centre de la Voie lactée', 'Position', 'Ascension droite de Sgr A* (J2000)', vl[0]['ra_deg'] if vl else '', '', '°', 'mesuré',
          'Reid & Brunthaler 2004 (ApJ 616, 872)')
    F.add('Centre de la Voie lactée', 'Position', 'Déclinaison de Sgr A* (J2000)', vl[0]['dec_deg'] if vl else '', '', '°', 'mesuré',
          'Reid & Brunthaler 2004 (ApJ 616, 872)')
    # plusieurs mesures pour une même galaxie : toutes les lignes de trous_noirs.tsv à moins de 1,5′ de la même clé
    kpos = {k: direction(*pos[k]) for k in tn_cle}
    for k in tn_cle:
        for r in sorted(autres, key=lambda r: r['prefere'] != '1'):
            if float(kpos[k] @ direction(float(r['ra_deg']), float(r['dec_deg']))) > math.cos(math.radians(1.5 / 60)):
                trou_noir_lignes(F, k, r)

    structures(F, app)

    # Écriture
    os.makedirs(sortie, exist_ok=True)
    ent = (f'# Écrit par pipeline/natif/fiches_galaxies.py le {date.today().isoformat()} (format : docs/fiches-format.md)\n'
           '# Sources : voir la docstring du script et la colonne source de chaque ligne.\n')
    F.ecrire(os.path.join(sortie, 'galaxies.tsv'), ent)
    t_leda = leda_tableau(cle_pgc, leda)
    t_leda.ecrire(os.path.join(sortie, 'galaxies_1_leda.tsv'), ent + '# Format tableau : HyperLEDA (meandata), par numéro PGC.\n')
    t_cf4 = cf4_tableau(cle_pgc, cf4, groupes, kt_gal, kt_grp)
    t_cf4.ecrire(os.path.join(sortie, 'galaxies_2_cf4.tsv'), ent + '# Format tableau : Cosmicflows-4 et groupes, par numéro PGC.\n')
    t_sga = sga_tableau(cle_sga, S)
    t_sga.ecrire(os.path.join(sortie, 'galaxies_3_sga.tsv'), ent + '# Format tableau : Siena Galaxy Atlas 2020.\n')

    # Contrôle : astres couverts par fichier de l'appli
    couverts = set(F.l) | set(t_leda.lignes) | set(t_cf4.lignes) | set(t_sga.lignes)
    print('\nfichier de l’appli : astres, avec fiche, sans rien')
    for f, objs in app.items():
        cles = {o['cle'] for o in objs}
        sans = sorted(cles - couverts)
        print(f'  {f}.tsv : {len(cles)}, {len(cles) - len(sans)}, {len(sans)}' + (f'  ex. {sans[:8]}' if sans else ''))
    print(f'  Centre de la Voie lactée : {"oui" if "Centre de la Voie lactée" in couverts else "non"}')
    print(f'\npar source : HyperLEDA {len(t_leda.lignes)}, CF4 {len(t_cf4.lignes)}, SGA {len(t_sga.lignes)}, LVDB {len(lv_cle)}, '
          f'McConnachie {len(mc_cle)}, UNGC {len(ungc_cle)}, SIMBAD {sum(1 for k in noms if k in ses)}, trous noirs '
          f'{len(tn_cle) + bool(vl)} astres, PGC connus {len(cle_pgc)} (absents de HyperLEDA : '
          f'{sum(1 for p in cle_pgc.values() if p not in leda)})')
    print('noms sans identifiant SIMBAD :', sorted(set(noms) - set(ses)))
    for f in os.listdir(sortie):
        if f.startswith('galaxies') and f.endswith('.tsv'):
            print(f'  {f} : {os.path.getsize(os.path.join(sortie, f)) / 1e6:.1f} Mo')


if __name__ == '__main__':
    main()
