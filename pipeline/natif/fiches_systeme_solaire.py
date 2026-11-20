#!/usr/bin/env python3
"""Fiches du système solaire -> systeme_solaire.tsv (format : docs/fiches-format.md).

Astres couverts (clés exactes de l'appli) : Soleil, Mercure, Vénus, Terre, Mars, Jupiter, Saturne, Uranus,
Neptune, Pluton, Lune, puis chaque lune de lunes.tsv (2e colonne). Le lien se fait par le code NAIF, jamais par le nom.

Sources (toutes publiques, officielles ; téléchargées une fois puis gardées en cache) :
- JPL SSD « Planetary Physical Parameters » (ssd.jpl.nasa.gov/planets/phys_par.html) : rayons, masse, densité,
  rotation, période orbitale, V(1,0), albédo, gravité, libération, avec incertitudes et références [A]…[Y].
- JPL SSD « Approximate Positions of the Planets » (planets/approx_pos.html, table 1, 1800-2050, Standish) :
  éléments orbitaux moyens à J2000 et leurs variations par siècle.
- JPL SSD « Planetary Satellite Physical Parameters » (sats/phys_par/) : GM, rayon moyen, densité ± (46 lunes),
  et le GM des planètes.
- JPL SSD « Planetary Satellite Mean Elements » (sats/elem/) : a, e, i, ω, M, nœud, périodes, précessions,
  pôle de Laplace, plan de référence, époque, éphéméride.
- JPL SSD « Planetary Satellite Discovery Circumstances » (sats/discovery.html) : numéro et nom UAI, désignation
  provisoire, année, découvreurs, référence. Relié au code NAIF par le nom JPL du même code (tables ci-dessus).
- NASA/NAIF pck00011.tpc (modèle UAI WGCCRE 2015, Archinal et al. 2018) : demi-axes des lunes, pôle (terme
  constant J2000) et vitesse de rotation Ẇ (période = 360°/Ẇ, « calculé »).
- JPL Horizons (API, fiche de chaque objet : OBJ_DATA=YES, MAKE_EPHEM=NO) : grandeurs physiques en plus
  (albédo, V(1,0), rotation, aplatissement, J2, températures, constante solaire, sphère de Hill…).
- NASA NSSDCA « Planetary Fact Sheets » (nssdc.gsfc.nasa.gov/planetary/factsheet/, D. R. Williams) : Soleil,
  planètes, Lune, Pluton : orbite, observation depuis la Terre, atmosphère, composition, magnétisme.
- UAI 2015 Résolution B3 (Prša et al. 2016, AJ 152, 41) : valeurs nominales solaires (statut « publié »).

Ce qui est fait : chaque grandeur garde sa source et son incertitude quand la source la donne. Une case vide de la
source n'est pas écrite. Si une même grandeur (même libellé) vient de plusieurs sources, la première dans l'ordre
ci-dessus gagne (tables JPL > NAIF > Horizons > fiches NSSDC). Grandeurs déduites par ce script (statut « calculé »,
formule dans la colonne source) : masse des lunes = GM/G (G CODATA 2018), gravité de surface = GM/R²,
vitesse de libération = sqrt(2GM/R), incertitudes propagées. Valeurs données par le JPL comme dérivées ([*]) :
« calculé » aussi. Sphère de Hill, limite de Roche, température de corps noir, valeurs au centre du Soleil :
« modèle ».

Usage :
    python fiches_systeme_solaire.py [lunes.tsv] [sortie.tsv] [dossier cache]
Défauts : C:\\dev\\Univers-PC\\lunes.tsv, C:\\tmp\\fiches\\systeme_solaire.tsv,
          C:\\tmp\\fiches\\cache\\systeme_solaire
"""
import datetime
import html
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from decimal import Decimal

LUNES_DEFAUT = r'C:\dev\Univers-PC\lunes.tsv'
SORTIE_DEFAUT = r'C:\tmp\fiches\systeme_solaire.tsv'
CACHE_DEFAUT = r'C:\tmp\fiches\cache\systeme_solaire'
SSD = 'https://ssd.jpl.nasa.gov/'
NSSDC = 'https://nssdc.gsfc.nasa.gov/planetary/factsheet/'
HORIZONS = 'https://ssd.jpl.nasa.gov/api/horizons.api'
PAUSE_S = 1.0                          # politesse envers les serveurs
G_KM = 6.67430e-20                     # G (CODATA 2018) en km^3 kg^-1 s^-2
G_TXT = 'G = 6,67430e-11 m³/(kg·s²), CODATA 2018'

PLANETES = {  # code NAIF -> (clé appli, nom anglais des sources, type)
    199: ('Mercure', 'Mercury', 'planète'), 299: ('Vénus', 'Venus', 'planète'),
    399: ('Terre', 'Earth', 'planète'), 499: ('Mars', 'Mars', 'planète'),
    599: ('Jupiter', 'Jupiter', 'planète'), 699: ('Saturne', 'Saturn', 'planète'),
    799: ('Uranus', 'Uranus', 'planète'), 899: ('Neptune', 'Neptune', 'planète'),
    999: ('Pluton', 'Pluto', 'planète naine'),
}
GROUPES = ['Identité', 'Position', 'Mouvement', 'Physique', 'Orbite', 'Rotation', 'Atmosphère et surface',
           'Champ magnétique', 'Lumière et couleur', 'Vue depuis la Terre', 'Âge et évolution', 'Planètes',
           'Découverte', 'Autres noms', 'Modèles et hypothèses']


# ----------------------------------------------------------------------------------------------- téléchargement
def fetch(cache: str, url: str, name: str) -> str:
    """Texte d'une page, téléchargée une seule fois (cache disque)."""
    path = os.path.join(cache, name)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (fiches-univers)'})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        with open(path, 'wb') as f:
            f.write(data)
        time.sleep(PAUSE_S)
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('latin-1')


def horizons(cache: str, code: int) -> str:
    q = urllib.parse.urlencode({'format': 'text', 'COMMAND': f"'{code}'", 'OBJ_DATA': 'YES', 'MAKE_EPHEM': 'NO'})
    return fetch(cache, f'{HORIZONS}?{q}', os.path.join('horizons', f'{code}.txt'))


# ----------------------------------------------------------------------------------------------- outils texte
def clean(s: str) -> str:
    s = re.sub(r'<sup>(.*?)</sup>', r'^\1', s, flags=re.I | re.S)
    s = re.sub(r'<sub>(.*?)</sub>', r'\1', s, flags=re.I | re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).replace('\xa0', ' ').strip()


def tables(page: str) -> list[list[list[str]]]:
    out = []
    for tb in re.findall(r'<table.*?</table>', page, re.S | re.I):
        rows = [[clean(c) for c in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', r, re.S | re.I)]
                for r in re.findall(r'<tr.*?</tr>', tb, re.S | re.I)]
        out.append([r for r in rows if r])
    return out


NUM = r'[-+]?(?:\d[\d,]*\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


def scaled(num: str, exp: int = 0) -> str:
    """'5.9722', 24 -> '5.9722e24' (garde les chiffres de la source)."""
    num = num.replace(',', '').strip()
    num = re.sub(r'^([-+]?)\.', r'\g<1>0.', num)       # '.07' -> '0.07'
    if num.endswith('.'):
        num = num[:-1]
    if exp == 0:
        return num
    d = Decimal(num).scaleb(exp)
    return format(d, 'e').replace('e+', 'e')


def parse_value(v: str):
    """'5.97219+-0.0006' -> (prefixe, nombre, incertitude, reste) ; None si pas de nombre en tête."""
    v = v.strip()
    m = re.match(r'^(\d+\.(\d+))\((\d+)\+-(\d+)\)(.*)$', v)          # 3.933(5+-4) : chiffres en plus
    if m:
        dec = len(m.group(2)) + len(m.group(3))
        return '', m.group(1) + m.group(3), scaled(m.group(4), -dec), m.group(5).strip()
    m = re.match(rf'^(?P<pre>[<>~≈]*)\s*(?P<num>{NUM})(?P<rest>.*)$', v)
    if not m:
        return None
    pre, num, rest = m.group('pre'), m.group('num'), m.group('rest')
    exp, unc = 0, ''
    for _ in range(3):
        rest = rest.strip()
        m2 = re.match(r'^\(10\^([-+]?\d+)\)(.*)$', rest) or re.match(r'^x\s*10\^?\s*([-+]?\d+)(.*)$', rest)
        if m2:
            exp += int(m2.group(1))
            rest = m2.group(2)
            continue
        m2 = re.match(r'^(?:\+-|\+/-|±)\s*(\d[\d.]*|\.\d+)(.*)$', rest)
        if m2:
            unc, rest = m2.group(1), m2.group(2)
            continue
        break
    pre = pre.replace('~', '≈')
    return pre, scaled(num, exp), (scaled(unc, exp) if unc else ''), rest.strip()


def with_pre(pre: str, num: str) -> str:
    """Préfixe autorisé par le format : '<' ou '>' (limite) ; '≈' pour une valeur approchée (~)."""
    if '<' in pre:
        return '<' + num
    if '>' in pre:
        return '>' + num
    return ('≈' + num) if '≈' in pre else num


UNITES = [  # unité de la source -> unité française (ordre : plus long d'abord)
    ('km^3/s^2', 'km³/s²'), ('g/cm^3', 'g/cm³'), ('kg/m^3', 'kg/m³'), ('kg/m3', 'kg/m³'), ('m/s^2', 'm/s²'),
    ('mW/m^2', 'mW/m²'), ('W/m^2', 'W/m²'), ('km/s', 'km/s'), ('m/s', 'm/s'), ('kg/s', 'kg/s'),
    ('deg/d', '°/jour'), ('dg/d', '°/jour'), ('rad/s', 'rad/s'), ('degrees', '°'), ('deg.', '°'), ('deg', '°'),
    ('microbar', 'µbar'), ('picobar', 'pbar'), ('bars', 'bar'), ('bar', 'bar'), ('mb', 'mbar'), ('Gauss', 'gauss'),
    ('hrs', 'heures'), ('hr', 'heures'), ('h', 'heures'), ('d', 'jours'), ('yr.', 'années'), ('yr', 'années'),
    ('y', 'années'), ('km', 'km'), ('kg', 'kg'), ('K', 'K'), ('s', 's'), ('"', '″'),
]


def unit_of(rest: str):
    """Unité en tête du reste du texte (« km », « d »…) -> unité française, ou None."""
    rest = rest.strip()
    for src, fr in UNITES:
        if rest.startswith(src) and (len(rest) == len(src) or not rest[len(src)].isalnum()):
            return fr
    return None


MOTS = [  # traduction minimale des textes des fiches NSSDC (composition, découvreur…)
    ('Molecular hydrogen', 'hydrogène moléculaire'), ('Hydrogen Deuteride', "deutérure d'hydrogène"),
    ('Hydrogen-Deuterium-Oxygen', 'eau semi-lourde'), ('Carbon Dioxide', 'dioxyde de carbone'),
    ('Carbon Monoxide', 'monoxyde de carbone'), ('Sulfur Dioxide', 'dioxyde de soufre'),
    ('Nitrogen Oxide', "monoxyde d'azote"), ('ammonia hydrosulfide', "hydrosulfure d'ammonium"),
    ('Ammonia ice', "glace d'ammoniac"), ('water ice', "glace d'eau"), ('methane ice', 'glace de méthane'),
    ('possible trace amounts of', 'traces possibles de'), ('trace', 'traces'), ('Trace', 'Traces'),
    ('Possible', 'Possibles'), ('Nitrogen', 'azote'), ('Oxygen', 'oxygène'), ('Hydrogen', 'hydrogène'),
    ('Helium', 'hélium'), ('Methane', 'méthane'), ('Ammonia', 'ammoniac'), ('Water', 'eau'),
    ('Argon', 'argon'), ('Neon', 'néon'), ('Krypton', 'krypton'), ('Xenon', 'xénon'), ('Sodium', 'sodium'),
    ('Magnesium', 'magnésium'), ('Potassium', 'potassium'), ('Calcium', 'calcium'), ('Iron', 'fer'),
    ('Aluminum', 'aluminium'), ('Silicon', 'silicium'), ('Phosphorus', 'phosphore'), ('Ethane', 'éthane'),
    ('hydrocarbons', 'hydrocarbures'), ('Unknown', 'inconnu'), ('Prehistoric', 'préhistoire'),
    ('based on predictions by', "d'après les prédictions de"), (' and ', ' et '),
    ('Synchronous', 'synchrone'), ('synchronous', 'synchrone'), ('Chaotic', 'chaotique'),
    ('Yes', 'oui'), ('No', 'non'),
]


def fr(text: str) -> str:
    for en, f in MOTS:
        text = re.sub(rf'(?<![A-Za-z]){re.escape(en.strip())}(?![A-Za-z])', f.strip(), text) \
            if en.strip() == en else text.replace(en, f)
    return text


def norm_name(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', s.lower())


# ----------------------------------------------------------------------------------------------- collecte
class Fiches:
    """Lignes des fiches ; une grandeur (clé, libellé) n'est écrite qu'une fois : la première source gagne."""

    def __init__(self):
        self.rows: dict[str, list[tuple]] = {}
        self.seen: set[tuple[str, str]] = set()

    def add(self, cle, groupe, libelle, valeur, incert='', unite='', statut='mesuré', source=''):
        valeur = str(valeur).strip()
        vide = valeur in ('', 'n/a', '-', 'NA', '?') or (valeur in ('inconnu', 'Unknown')
                                                          and libelle != 'Découvreur(s) ou mission')
        if vide or (cle, libelle) in self.seen:
            return
        assert groupe in GROUPES, groupe
        self.seen.add((cle, libelle))
        row = (cle, groupe, libelle, valeur, str(incert or '').strip(), unite, statut, source)
        self.rows.setdefault(cle, []).append(tuple(c.replace('\t', ' ') for c in row))

    def get(self, cle, libelle):
        for r in self.rows.get(cle, []):
            if r[2] == libelle:
                return r
        return None

    def write(self, path: str, ordre: list[str], entete: list[str]):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        n = 0
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            for line in entete:
                f.write(f'# {line}\n')
            f.write('# cle\tgroupe\tlibelle\tvaleur\tincertitude\tunite\tstatut\tsource\n')
            for cle in ordre:
                rows = sorted(self.rows.get(cle, []), key=lambda r: GROUPES.index(r[1]))  # tri stable
                for r in rows:
                    f.write('\t'.join(r) + '\n')
                    n += 1
        return n


# ----------------------------------------------------------------------------------------------- JPL planètes
def refs_planetes(page: str) -> dict[str, str]:
    """[D] -> 'Archinal et al. 2018' (références de la page JPL)."""
    txt = clean(page[page.find('id="refs"'):])
    out = {}
    for k, body in re.findall(r'\[ ?([A-Z]) ?\]\s*(.*?)(?=\[ ?[A-Z*] ?\]|Change Log|$)', txt):
        year = re.search(r'\b(1[89]\d\d|20\d\d)\b', body)
        author = re.split(r'[,.]', body.strip())[0]
        out[k] = f'{author}{" et al." if "et al" in body[:80] else ""} {year.group(1) if year else ""}'.strip()
    return out


def jpl_planetes(fiches: Fiches, cache: str):
    page = fetch(cache, SSD + 'planets/phys_par.html', 'planets_phys_par.html')
    refs = refs_planetes(page)
    by_en = {v[1]: v[0] for v in PLANETES.values()}
    cols = [  # (colonne, groupe, libellé, unité)
        (1, 'Physique', 'Rayon équatorial', 'km'), (2, 'Physique', 'Rayon moyen', 'km'),
        (3, 'Physique', 'Masse', 'kg'), (4, 'Physique', 'Masse volumique moyenne', 'g/cm³'),
        (5, 'Rotation', 'Période de rotation sidérale (négative : rétrograde)', 'jours'),
        (6, 'Orbite', 'Période orbitale sidérale', 'années'),
        (7, 'Lumière et couleur', 'Magnitude absolue V(1,0)', 'mag'),
        (8, 'Lumière et couleur', 'Albédo géométrique', ''),
        (9, 'Physique', "Gravité à l'équateur", 'm/s²'), (10, 'Physique', 'Vitesse de libération', 'km/s'),
    ]
    for tb in tables(page)[:2]:
        exp_masse = 24 if tb[0][0] == 'Planet' else 18
        for row in tb[2:]:
            cle = by_en.get(row[0])
            if not cle or len(row) < 11:
                continue
            for col, groupe, lib, unite in cols:
                m = re.match(rf'^({NUM})\s*\[\s*([A-Z*])\s*\]\s*(?:±\s*({NUM}))?', row[col])
                if not m:
                    continue
                exp = exp_masse if lib == 'Masse' else 0
                val, unc, ref = scaled(m.group(1), exp), scaled(m.group(3), exp) if m.group(3) else '', m.group(2)
                if ref == '*':
                    fiches.add(cle, groupe, lib, val, unc, unite, 'calculé',
                               'JPL SSD Planetary Physical Parameters (valeur dérivée par le JPL des autres '
                               'colonnes : densité = M/volume de la sphère de rayon moyen, gravité = GM/Rég², '
                               'libération = √(2GM/Rmoy))')
                else:
                    fiches.add(cle, groupe, lib, val, unc, unite, 'mesuré',
                               f'JPL SSD Planetary Physical Parameters ({refs.get(ref, ref)})')


def jpl_approx(fiches: Fiches, cache: str):
    page = fetch(cache, SSD + 'planets/approx_pos.html', 'planets_approx_pos.html')
    pre = clean(re.findall(r'<pre.*?</pre>', page, re.S)[0])
    by_en = {v[1]: v[0] for v in PLANETES.values()}
    by_en['EM Bary'] = 'Terre'
    noms = [('Demi-grand axe', 'UA', 'UA/siècle'), ('Excentricité', '', '/siècle'),
            ('Inclinaison sur l’écliptique', '°', '°/siècle'), ('Longitude moyenne', '°', '°/siècle'),
            ('Longitude du périhélie', '°', '°/siècle'), ('Longitude du nœud ascendant', '°', '°/siècle')]
    src = ('JPL SSD Approximate Positions of the Planets, table 1 (Standish, ajustement sur DE405, '
           'valable 1800-2050 ; écliptique et équinoxe J2000)')
    for m in re.finditer(rf'(Mercury|Venus|EM Bary|Mars|Jupiter|Saturn|Uranus|Neptune)((?:\s+{NUM}){{12}})', pre):
        cle = by_en[m.group(1)]
        nums = m.group(2).split()
        note = ' (barycentre Terre-Lune)' if m.group(1) == 'EM Bary' else ''
        for k, (lib, u, ur) in enumerate(noms):
            fiches.add(cle, 'Orbite', f'{lib} (J2000){note}', nums[k], '', u, 'mesuré', src)
            fiches.add(cle, 'Orbite', f'{lib} : variation par siècle{note}', nums[6 + k], '', ur, 'mesuré', src)


# ----------------------------------------------------------------------------------------------- JPL lunes
def jpl_sats_phys(fiches: Fiches, cache: str, cle_of: dict[int, str], noms_jpl: dict[int, str]):
    page = fetch(cache, SSD + 'sats/phys_par/', 'sats_phys_par.html')
    tbs = tables(page)
    refs = {'1': 'Archinal et al. 2018 (UAI WGCCRE 2015)', '2': 'Nimmo et al. 2017',
            '3': 'Stern et al. 2018'}
    for row in tbs[0][2:]:
        if len(row) < 6 or not row[2].isdigit():
            continue
        code = int(row[2])
        noms_jpl.setdefault(code, row[1])
        cle = cle_of.get(code)
        if not cle:
            continue
        for cell, lib, unite in ((row[3], 'Paramètre gravitationnel GM', 'km³/s²'),
                                 (row[4], 'Rayon moyen', 'km'), (row[5], 'Masse volumique moyenne', 'g/cm³')):
            p = cell.split()
            if len(p) < 3 or not re.match(NUM, p[0]) or float(p[0]) == 0:
                continue
            if p[2] == '*':
                fiches.add(cle, 'Physique', lib, p[0], p[1], unite, 'calculé',
                           'JPL SSD Satellite Physical Parameters (dérivée par le JPL : M/volume de la sphère '
                           'de rayon moyen)')
            else:
                ref = refs.get(p[2], f'éphéméride {p[2]}')
                fiches.add(cle, 'Physique', lib, p[0], p[1], unite, 'mesuré',
                           f'JPL SSD Satellite Physical Parameters ({ref})')
    # GM des planètes (table 2 de la même page)
    by_en = {v[1]: v[0] for v in PLANETES.values()}
    for row in tbs[1][1:]:
        m = re.match(rf'^({NUM})\s*±\s*({NUM})', row[1]) if len(row) > 2 else None
        if m and row[0] in by_en:
            fiches.add(by_en[row[0]], 'Physique', 'Paramètre gravitationnel GM', m.group(1), m.group(2), 'km³/s²',
                       'mesuré', f'JPL SSD Satellite Physical Parameters (éphéméride {row[2]})')


def jpl_sats_elem(fiches: Fiches, cache: str, cle_of: dict[int, str], noms_jpl: dict[int, str]):
    page = fetch(cache, SSD + 'sats/elem/', 'sats_elem.html')
    rows = tables(page)[0][1:]
    best: dict[int, list[str]] = {}
    for r in rows:                     # une ligne par lune ; si deux (Puck), la plus récente époque
        if len(r) < 20 or not r[3].isdigit():
            continue
        code = int(r[3])
        noms_jpl.setdefault(code, r[2])
        if code not in best or r[6] > best[code][6]:
            best[code] = r
    plans = {'ecliptic': 'écliptique (J2000)', 'Laplace': 'plan de Laplace de la lune',
             'equatorial': "équateur de la planète"}
    cols = [(7, 'Demi-grand axe', 'km'), (8, 'Excentricité', ''), (9, 'Argument du périastre ω', '°'),
            (10, 'Anomalie moyenne M (à l’époque)', '°'), (11, 'Inclinaison', '°'),
            (12, 'Longitude du nœud ascendant', '°'), (13, 'Période orbitale sidérale (jours)', 'jours'),
            (14, 'Période de précession du périastre', 'années'), (15, 'Période de précession des nœuds', 'années'),
            (16, 'Pôle du plan de Laplace : ascension droite', '°'),
            (17, 'Pôle du plan de Laplace : déclinaison', '°'),
            (18, 'Angle entre équateur de la planète et plan de Laplace', '°')]
    for code, r in best.items():
        cle = cle_of.get(code)
        if not cle:
            continue
        src = (f'JPL SSD Planetary Satellite Mean Elements (éphéméride {r[4]}, éléments moyens'
               f'{", réf. " + r[19] if r[19] not in ("", "n/a") else ""})')
        fiches.add(cle, 'Orbite', 'Plan de référence des éléments', plans.get(r[5], r[5]), '', '', 'publié', src)
        fiches.add(cle, 'Orbite', 'Époque des éléments (TDB)', r[6], '', '', 'publié', src)
        for col, lib, u in cols:
            if re.fullmatch(NUM, r[col] or ''):
                fiches.add(cle, 'Orbite', lib, scaled(r[col]), '', u, 'mesuré', src)


def jpl_decouverte(fiches: Fiches, cache: str, cle_of: dict[int, str], noms_jpl: dict[int, str]):
    page = fetch(cache, SSD + 'sats/discovery.html', 'sats_discovery.html')
    rows = [r for r in tables(page)[0] if len(r) >= 6 and re.fullmatch(r'\d{4}(?:, \d{4})*', r[3])]
    index: dict[str, list[list[str]]] = {}
    for r in rows:
        for n in {norm_name(r[1]), norm_name(r[2])} - {''}:
            index.setdefault(n, []).append(r)
    stats = [0, 0]
    for code, cle in cle_of.items():
        nom = noms_jpl.get(code) or cle
        if not nom:
            continue
        n = norm_name(nom)
        cand = index.get(n) or [r for r in rows if len(n) >= 10 and norm_name(r[1]).startswith(n)]
        if len(cand) != 1:     # nom JPL mal orthographié (« Magaclite ») : essai avec le nom de lunes.tsv
            cand = index.get(norm_name(cle), [])
        if len(cand) != 1:
            stats[1] += 1
            stats.append(cle)
            continue
        stats[0] += 1
        r = cand[0]
        src = f'JPL SSD Planetary Satellite Discovery Circumstances (réf. {r[5] or "n/a"})'
        if r[0]:
            fiches.add(cle, 'Identité', 'Numéro UAI', r[0], '', '', 'publié', src)
        fiches.add(cle, 'Identité', 'Nom UAI', r[1], '', '', 'publié', src)
        fiches.add(cle, 'Autres noms', 'Désignation provisoire', r[2], '', '', 'publié', src)
        fiches.add(cle, 'Découverte', 'Année de découverte', r[3], '', '', 'publié', src)
        fiches.add(cle, 'Découverte', 'Découvreur(s) ou mission', r[4], '', '', 'publié', src)
    return stats


# ----------------------------------------------------------------------------------------------- NAIF PCK
def naif_pck(fiches: Fiches, cache: str, cle_of: dict[int, str]):
    """Lunes : demi-axes, pôle et rotation du modèle UAI (fichier pck00011.tpc de la NASA/NAIF)."""
    text = fetch(cache, 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc', 'pck00011.tpc')
    data = ' '.join(re.findall(r'\\begindata(.*?)\\begintext', text, re.S))
    vals: dict[tuple[int, str], list[str]] = {}
    for m in re.finditer(r'BODY(\d+)_(RADII|POLE_RA|POLE_DEC|PM)\s*=\s*\(([^)]*)\)', data):
        vals[(int(m.group(1)), m.group(2))] = m.group(3).replace('D', 'e').split()
    src = 'NASA/NAIF pck00011.tpc (modèle UAI WGCCRE 2015, Archinal et al. 2018)'
    for code, cle in cle_of.items():
        radii = vals.get((code, 'RADII'))
        if radii and len(radii) == 3:
            fiches.add(cle, 'Physique', 'Dimensions (demi-axes)', ' × '.join(radii), '', 'km', 'publié', src)
        for key, lib in (('POLE_RA', 'Pôle nord : ascension droite (J2000)'),
                         ('POLE_DEC', 'Pôle nord : déclinaison (J2000)')):
            v = vals.get((code, key))
            if v:
                fiches.add(cle, 'Rotation', lib, v[0], '', '°', 'publié', src + ' ; terme constant, sans nutation')
        pm = vals.get((code, 'PM'))
        if pm and len(pm) > 1 and float(pm[1]) != 0:
            per = 360.0 / float(pm[1])
            fiches.add(cle, 'Rotation', 'Période de rotation du modèle UAI', sig(abs(per), 8), '', 'jours',
                       'calculé', f'P = 360°/Ẇ, Ẇ = {pm[1]} °/jour ; {src}'
                       + (' ; rotation rétrograde (Ẇ < 0)' if per < 0 else ''))


# ----------------------------------------------------------------------------------------------- Horizons
# (motif du libellé Horizons, groupe, libellé, unité par défaut, statut)
HZ = [
    (r'^gm 1-sigma', None, 'GM_SIGMA', '', ''),
    (r'^gm\b', 'Physique', 'Paramètre gravitationnel GM', 'km³/s²', 'mesuré'),
    (r'^mass\W*(?:x\s*)?10\^(\d+)\s*\(?\s*(kg|g)\b', 'Physique', 'Masse', 'kg', 'mesuré'),
    (r'^mass of atmosphere|^atmos$', 'Atmosphère et surface', "Masse de l'atmosphère", 'kg', 'mesuré'),
    (r'^oceans$', 'Physique', 'Masse des océans', 'kg', 'mesuré'),
    (r'^crust$', 'Physique', 'Masse de la croûte', 'kg', 'mesuré'),
    (r'^mantle$', 'Physique', 'Masse du manteau', 'kg', 'mesuré'),
    (r'^outer core$', 'Physique', 'Masse du noyau externe', 'kg', 'mesuré'),
    (r'^inner core$', 'Physique', 'Masse de la graine (noyau interne)', 'kg', 'mesuré'),
    (r'^land$', 'Atmosphère et surface', 'Surface des terres', 'km²', 'mesuré'),
    (r'^sea$', 'Atmosphère et surface', 'Surface des mers', 'km²', 'mesuré'),
    (r'^solar radius \(iau2015\)', 'Physique', 'Rayon nominal (UAI 2015)', 'km', 'publié'),
    (r'^radius \(photosphere\)', 'Physique', 'Rayon de la photosphère', 'km', 'mesuré'),
    (r'^radius \(iau\)', 'Physique', 'Rayon de référence UAI', 'km', 'publié'),
    (r'^radius \(gravity\)', 'Physique', 'Rayon de référence du champ de gravité', 'km', 'publié'),
    (r'^vol\. mean radius|^mean radius|^radius \(km\),mean', 'Physique', 'Rayon moyen', 'km', 'mesuré'),
    (r'^radius \(km\)$', 'Physique', 'RAYON', 'km', 'mesuré'),
    (r'^equ(?:at)?\. radius|^equatorial radius', 'Physique', 'Rayon équatorial', 'km', 'mesuré'),
    (r'^polar radius|^polar axis', 'Physique', 'Rayon polaire', 'km', 'mesuré'),
    (r'^fluid core rad', 'Physique', 'Rayon du noyau liquide', 'km', 'mesuré'),
    (r'^inner core rad', 'Physique', 'Rayon de la graine (noyau interne)', 'km', 'mesuré'),
    (r'^core radius', 'Physique', 'Rayon du noyau', 'km', 'mesuré'),
    (r'^density \(g|^density, g|^mean density, g', 'Physique', 'Masse volumique moyenne', 'g/cm³', 'mesuré'),
    (r'^mean crustal density', 'Physique', 'Masse volumique moyenne de la croûte', 'g/cm³', 'mesuré'),
    (r'^flatness|^flattening', 'Physique', 'Aplatissement', '', 'mesuré'),
    (r'^volume\W*(?:x)?10\^(\d+)\s*km\^3|^volume, km\^3', 'Physique', 'Volume', 'km³', 'mesuré'),
    (r'^mom(?:ent|\.) of inertia', 'Physique', "Moment d'inertie (I/MR²)", '', 'mesuré'),
    (r'^j2\b', 'Physique', 'J2 (aplatissement du champ de gravité)', '', 'mesuré'),
    (r'love', 'Physique', 'Nombre de Love k2', '', 'mesuré'),
    (r'^rocky core mass', 'Modèles et hypothèses', 'Masse du noyau rocheux / masse totale', '', 'modèle'),
    (r'^mass ratio \(sun/', 'Physique', 'Rapport de masse Soleil / astre', '', 'mesuré'),
    (r'^mass ratio \(mc/mp\)', 'Physique', 'Rapport de masse Charon / Pluton', '', 'mesuré'),
    (r'^earth/moon mass ratio', 'Physique', 'Rapport de masse Terre / Lune', '', 'mesuré'),
    (r'^equ\. grav|^g_e\b|^equ\. gravity', 'Physique', "Gravité à l'équateur", 'm/s²', 'mesuré'),
    (r'^pol\. grav|^g_p\b|^polar gravity', 'Physique', 'Gravité aux pôles', 'm/s²', 'mesuré'),
    (r'^g_o\b|^surface gravity|^surface accel', 'Physique', 'Gravité de surface moyenne', 'm/s²', 'mesuré'),
    (r'^escape', 'Physique', 'Vitesse de libération', 'km/s', 'mesuré'),
    (r'^geometric albedo', 'Lumière et couleur', 'Albédo géométrique', '', 'mesuré'),
    (r'v\(1,0\)$', 'Lumière et couleur', 'Magnitude absolue V(1,0)', 'mag', 'mesuré'),
    (r'^vis\. mag\. \(opposition\)', 'Lumière et couleur', "Magnitude moyenne à l'opposition", 'mag', 'mesuré'),
    (r'^luminosity, 10\^(\d+)', 'Physique', 'Luminosité', 'W', 'mesuré'),
    (r'^effective temp|^mean effect\. temp', 'Atmosphère et surface', 'Température effective', 'K', 'mesuré'),
    (r'^mass-energy conv', 'Physique', 'Masse convertie en énergie', 'kg/s', 'mesuré'),
    (r'^photospheric depth', 'Atmosphère et surface', 'Épaisseur de la photosphère', 'km', 'mesuré'),
    (r'^chromospheric depth', 'Atmosphère et surface', 'Épaisseur de la chromosphère', 'km', 'mesuré'),
    (r'^sunspot cycle', 'Physique', 'Durée du cycle des taches', 'années', 'mesuré'),
    (r'^angular diam at 1 au', 'Vue depuis la Terre', 'Diamètre apparent à 1 UA', '″', 'mesuré'),
    (r'^max\. angular diam', 'Vue depuis la Terre', 'Diamètre apparent maximal', '″', 'mesuré'),
    (r'^mean angular diameter', 'Vue depuis la Terre', 'Diamètre apparent moyen', '', 'mesuré'),
    (r'^sid(?:ereal|\.) rot\. per|^adopted sid\. rot|^mean sidereal day',
     'Rotation', 'ROTSID', 'heures', 'mesuré'),
    (r'^rotational period', 'Rotation', 'Période de rotation', 'jours', 'mesuré'),
    (r'rot\. rat|^rot\. rate', 'Rotation', 'Vitesse angulaire de rotation', 'rad/s', 'mesuré'),
    (r'^mean solar day 2000', 'Rotation', 'Jour solaire moyen (2000.0)', 's', 'mesuré'),
    (r'^mean solar day 1820', 'Rotation', 'Jour solaire moyen (1820.0)', 's', 'mesuré'),
    (r'^mean solar day', 'Rotation', 'Durée du jour solaire moyen', 'heures', 'mesuré'),
    (r'^obliquity to orbit', 'Rotation', "Obliquité (inclinaison de l'axe sur l'orbite)", '°', 'mesuré'),
    (r'^obliquity to ecliptic', 'Rotation', "Inclinaison de l'équateur sur l'écliptique", '°', 'mesuré'),
    (r'^pole \(ra,dec\)', 'Rotation', 'POLE', '°', 'mesuré'),
    (r'^sidereal orb(?:it|\.)? ?per|^mean sidereal orb per', 'Orbite', 'PERIODE', 'années', 'mesuré'),
    (r'^orbit(?:al)? period', 'Orbite', 'Période orbitale sidérale (jours)', 'jours', 'mesuré'),
    (r'^mean daily motion', 'Orbite', 'Moyen mouvement', '°/jour', 'mesuré'),
    (r'^mean motion, rad/s', 'Orbite', 'Moyen mouvement (rad/s)', 'rad/s', 'mesuré'),
    (r'orbit(?:al)? (?:speed|velocity|vel\.)|^mean orbit vel', 'Orbite', 'Vitesse orbitale moyenne', 'km/s',
     'mesuré'),
    (r'^semi-major axis', 'Orbite', 'Demi-grand axe', 'km', 'mesuré'),
    (r'^eccentricity', 'Orbite', 'Excentricité', '', 'mesuré'),
    (r'^inclination', 'Orbite', 'Inclinaison', '°', 'mesuré'),
    (r'^apsidal period', 'Orbite', 'Période de précession du périastre (jours)', 'jours', 'mesuré'),
    (r'^nodal period', 'Orbite', 'Période de précession des nœuds (jours)', 'jours', 'mesuré'),
    (r"^hill's sphere", 'Modèles et hypothèses', 'Rayon de la sphère de Hill', 'rayons de l’astre', 'modèle'),
    (r'^a_?roche\(ice\)', 'Modèles et hypothèses', 'Limite de Roche (corps glacé)', 'rayons de l’astre', 'modèle'),
    (r'^atmos\. temp\. \(1 bar\)', 'Atmosphère et surface', 'Température à 1 bar', 'K', 'mesuré'),
    (r'^atmos?\. pressure|^atm\. pressure', 'Atmosphère et surface', 'Pression en surface', 'bar', 'mesuré'),
    (r'^mean (?:surface )?temp', 'Atmosphère et surface', 'Température moyenne de surface', 'K', 'mesuré'),
    (r'^surface emissivity', 'Atmosphère et surface', 'Émissivité de surface', '', 'mesuré'),
    (r'^heat flow, apollo (\d+)', 'Atmosphère et surface', 'FLUX', 'mW/m²', 'mesuré'),
    (r'^farside crust', 'Physique', 'Épaisseur de la croûte (face cachée)', 'km', 'mesuré'),
    (r'^nearside crust', 'Physique', 'Épaisseur de la croûte (face visible)', 'km', 'mesuré'),
    (r'^magnetic moment', 'Champ magnétique', 'Moment magnétique', '', 'mesuré'),
]
SPLIT_RIGHT = (r'\s(?=(?:Density|Geometric Albedo|Mean orbit|Orbital period|Rotational period|Escape|'
               r'Obliquity|Hill|V\(1,0\)|Mass|Local)\b)')


def hz_pairs(text: str):
    """Paires (libellé, valeur) d'une fiche Horizons (deux colonnes « libellé = valeur »)."""
    out = []
    body = text.split('*' * 40)
    body = body[1] if len(body) > 1 else ''
    for line in body.splitlines():
        if '=' not in line or line.strip().startswith(('Motion relative', 'PHYSICAL', 'Pre-computed')):
            continue
        chunks = re.split(r'(?<=\S)\s{2,}(?=[A-Za-z_][^=]*=)', line.strip())
        for ch in chunks:
            parts = re.split(SPLIT_RIGHT, ch) if ch.count('=') > 1 else [ch]
            for p in parts:
                if '=' in p:
                    lab, val = p.split('=', 1)
                    out.append((re.sub(r'\s+', ' ', lab.strip()), val.strip()))
    return out


def hz_solar_constant(text: str):
    """Constante solaire au périhélie / aphélie / moyenne (W/m²)."""
    m = re.search(r'Solar Constant \(W/m\^2\)\s+(' + NUM + r')(?:\+-\d+)?\s+(' + NUM + r')(?:\+-\d+)?\s+(' + NUM + ')',
                  text)
    if m:
        return {'périhélie': m.group(1), 'aphélie': m.group(2), 'moyenne': m.group(3)}
    m = re.search(r'Solar Constant \(W/m\^2\)\s*=\s*(' + NUM + r') \(mean\), (' + NUM + r') \(perihelion\), ('
                  + NUM + r') \(aphelion\)', text)
    if m:
        return {'moyenne': m.group(1), 'périhélie': m.group(2), 'aphélie': m.group(3)}
    m = re.search(r'Solar constant \(1 AU\)\s*=\s*(' + NUM + ')', text)
    return {'à 1 UA': m.group(1)} if m else {}


def hz_one(fiches: Fiches, cle: str, lab: str, val: str, src: str, sigma: dict):
    low = lab.lower()
    for pat, groupe, lib, unite, statut in HZ:
        m = re.search(pat, low)
        if not m:
            continue
        if lib == 'GM_SIGMA':
            p = parse_value(val.replace('+-', '').strip())
            if p:
                sigma['gm'] = p[1]
            return
        if lib == 'POLE':
            m2 = re.match(rf'\(\s*({NUM}),\s*({NUM})\)', val)
            if m2:
                fiches.add(cle, groupe, 'Pôle nord : ascension droite (J2000)', m2.group(1), '', '°', statut, src)
                fiches.add(cle, groupe, 'Pôle nord : déclinaison (J2000)', m2.group(2), '', '°', statut, src)
            return
        if lib == 'FLUX':
            lib = f'Flux de chaleur interne (site Apollo {m.group(1)})'
        txt = val.strip()
        if lib == 'RAYON':
            lib = 'Dimensions (demi-axes)' if re.search(r'\dx|\sx\s?\d', txt) else 'Rayon moyen'
        if lib == 'PERIODE':
            u = 'jours' if re.search(r'(^|[ ,])d\b|, d$', low + ' ' + txt[-2:]) else 'années'
            lib = 'Période orbitale sidérale' + (' (jours)' if u == 'jours' else '')
            unite = u
        if lib == 'ROTSID':
            u_rot = 'h min s' if re.match(r'^\d+h', txt) else (unit_of(re.sub(r'^[\d.,+\- ]+', '', txt)) or unite)
            lib = f'Période de rotation sidérale ({u_rot})'
        if lib == 'Dimensions (demi-axes)':
            fiches.add(cle, groupe, lib, re.sub(r'\s*x\s*', ' × ', txt), '', 'km', statut, src)
            return
        if re.match(r'^1/\d', txt) or re.match(r'^\d+h\s', txt) or re.search(r"\d'", txt):
            fiches.add(cle, groupe, lib, txt.replace('+/-', '±'), '', '', statut, src)
            return
        p = parse_value(txt)
        if p is None:
            if re.fullmatch(r'[A-Za-z]+', txt):
                fiches.add(cle, groupe, lib, fr(txt), '', '', statut, src)
            return
        pre, num, unc, rest = p
        if lib in ('Masse', 'Luminosité', 'Volume') and m.groups() and m.group(1):
            exp = int(m.group(1)) - (3 if lib == 'Masse' and m.group(2) == 'g' else 0)
            num, unc = scaled(num, exp), scaled(unc, exp) if unc else ''
        if lib.startswith('Masse ') and lib != 'Masse volumique moyenne' and 'x 10^' in val:
            pass  # déjà mis à l'échelle par parse_value
        u = unite if unite == 'km²' else (unit_of(rest) or unite)
        if lib == 'Moment magnétique':
            fiches.add(cle, groupe, lib, txt.replace('Rp^3', 'Rp³'), '', '', statut, src)
            return
        if lib == 'Rotation' or lib == 'Période de rotation' and unit_of(rest) is None and rest:
            return
        val_out = with_pre(pre, num)
        fiches.add(cle, groupe, lib, val_out, unc, u, statut, src)
        return


def jpl_horizons(fiches: Fiches, cache: str, codes: dict[int, str]):
    sans = []
    for code, cle in codes.items():
        text = horizons(cache, code)
        if 'Revised' not in text:
            sans.append(cle)
            continue
        rev = re.search(r'Revised:\s*([A-Za-z]+\.? \d+, \d{4})', text)
        src = f'JPL Horizons, fiche de l’objet {code}' + (f' (révisée {rev.group(1)})' if rev else '')
        sigma: dict[str, str] = {}
        for lab, val in hz_pairs(text):
            hz_one(fiches, cle, lab, val, src, sigma)
        gm = fiches.get(cle, 'Paramètre gravitationnel GM')
        if sigma.get('gm') and gm and gm[7] == src and not gm[4]:
            rows = fiches.rows[cle]
            rows[rows.index(gm)] = gm[:4] + (sigma['gm'],) + gm[5:]
        for k, v in hz_solar_constant(text).items():
            fiches.add(cle, 'Lumière et couleur', f'Éclairement solaire reçu ({k})', v, '', 'W/m²', 'mesuré', src)
    return sans


# ----------------------------------------------------------------------------------------------- NSSDC
NS = {  # libellé normalisé (minuscules, sans espaces ni *) -> (groupe, libellé, unité, puissance de 10, statut)
    'mass(10^24kg)': ('Physique', 'Masse', 'kg', 24, 'mesuré'),
    'mass(10^15kg)': ('Physique', 'Masse', 'kg', 15, 'mesuré'),
    'gm(x10^6km^3/s^2)': ('Physique', 'Paramètre gravitationnel GM', 'km³/s²', 6, 'mesuré'),
    'volume(10^10km^3)': ('Physique', 'Volume', 'km³', 10, 'mesuré'),
    'volume(10^12km^3)': ('Physique', 'Volume', 'km³', 12, 'mesuré'),
    'equatorialradius(km)': ('Physique', 'Rayon équatorial', 'km', 0, 'mesuré'),
    'equatorialradius(1barlevel)(km)': ('Physique', 'Rayon équatorial', 'km', 0, 'mesuré'),
    'polarradius(km)': ('Physique', 'Rayon polaire', 'km', 0, 'mesuré'),
    'polarradius(1barlevel)(km)': ('Physique', 'Rayon polaire', 'km', 0, 'mesuré'),
    'volumetricmeanradius(km)': ('Physique', 'Rayon moyen', 'km', 0, 'mesuré'),
    'coreradius(km)': ('Physique', 'Rayon du noyau', 'km', 0, 'mesuré'),
    'ellipticity(flattening)': ('Physique', 'Aplatissement', '', 0, 'mesuré'),
    'ellipticity': ('Physique', 'Aplatissement', '', 0, 'mesuré'),
    'meandensity(kg/m^3)': ('Physique', 'Masse volumique moyenne', 'kg/m³', 0, 'mesuré'),
    'surfacegravity(mean)(m/s^2)': ('Physique', 'Gravité de surface moyenne', 'm/s²', 0, 'mesuré'),
    'surfacegravity(m/s^2)': ('Physique', 'Gravité de surface moyenne', 'm/s²', 0, 'mesuré'),
    'gravity(mean,1bar)(m/s^2)': ('Physique', 'Gravité de surface moyenne', 'm/s²', 0, 'mesuré'),
    'surfacegravity(eq.)(m/s^2)': ('Physique', "Gravité à l'équateur", 'm/s²', 0, 'mesuré'),
    'surfaceacceleration(eq)(m/s^2)': ('Physique', "Gravité à l'équateur", 'm/s²', 0, 'mesuré'),
    'surfaceacceleration(eq.)(m/s^2)': ('Physique', "Gravité à l'équateur", 'm/s²', 0, 'mesuré'),
    'acceleration(eq.,1bar)(m/s^2)': ('Physique', "Gravité à l'équateur", 'm/s²', 0, 'mesuré'),
    'surfaceacceleration(pole)(m/s^2)': ('Physique', 'Gravité aux pôles', 'm/s²', 0, 'mesuré'),
    'acceleration(pole,1bar)(m/s^2)': ('Physique', 'Gravité aux pôles', 'm/s²', 0, 'mesuré'),
    'surfaceacceleration(m/s^2)': ('Physique', 'Gravité de surface moyenne', 'm/s²', 0, 'mesuré'),
    'escapevelocity(km/s)': ('Physique', 'Vitesse de libération', 'km/s', 0, 'mesuré'),
    'bondalbedo': ('Lumière et couleur', 'Albédo de Bond', '', 0, 'mesuré'),
    'geometricalbedo': ('Lumière et couleur', 'Albédo géométrique', '', 0, 'mesuré'),
    'v-bandmagnitudev(1,0)': ('Lumière et couleur', 'Magnitude absolue V(1,0)', 'mag', 0, 'mesuré'),
    'visualmagnitudev(1,0)': ('Lumière et couleur', 'Magnitude absolue V(1,0)', 'mag', 0, 'mesuré'),
    'absolutemagnitude': ('Lumière et couleur', 'Magnitude absolue (étoile, MV)', 'mag', 0, 'mesuré'),
    'apparentvisualmagnitude(v0)': ('Lumière et couleur', "Magnitude moyenne à l'opposition", 'mag', 0, 'mesuré'),
    'solarirradiance(w/m^2)': ('Lumière et couleur', 'Éclairement solaire reçu (moyenne)', 'W/m²', 0, 'mesuré'),
    'black-bodytemperature(k)': ('Modèles et hypothèses', "Température d'équilibre (corps noir)", 'K', 0,
                                 'modèle'),
    'topographicrange(km)': ('Atmosphère et surface', 'Dénivelé du relief', 'km', 0, 'mesuré'),
    'momentofinertia(i/mr^2)': ('Physique', "Moment d'inertie (I/MR²)", '', 0, 'mesuré'),
    'j2(x10^-6)': ('Physique', 'J2 (aplatissement du champ de gravité)', '', -6, 'mesuré'),
    'numberofnaturalsatellites': ('Identité', 'Lunes connues (fiche NSSDC)', '', 0, 'publié'),
    'planetaryringsystem': ('Identité', "Système d'anneaux", '', 0, 'publié'),
    'luminosity(10^24j/s)': ('Physique', 'Luminosité', 'W', 24, 'mesuré'),
    'massconversionrate(10^6kg/s)': ('Physique', 'Masse convertie en énergie', 'kg/s', 6, 'mesuré'),
    'meanenergyproduction(10^-3j/kgs)': ('Physique', "Production moyenne d'énergie", 'W/kg', -3, 'mesuré'),
    'surfaceemission(10^6j/m^2s)': ('Physique', 'Émission en surface', 'W/m²', 6, 'mesuré'),
    'spectraltype': ('Lumière et couleur', 'Type spectral', '', 0, 'publié'),
    'speedrelativetonearbystars(km/s)': ('Mouvement', 'Vitesse par rapport aux étoiles proches', 'km/s', 0,
                                         'mesuré'),
    'obliquitytoecliptic(deg.)': ('Rotation', "Inclinaison de l'équateur sur l'écliptique", '°', 0, 'mesuré'),
    'semimajoraxis(10^6km)': ('Orbite', 'Demi-grand axe (km)', 'km', 6, 'mesuré'),
    'siderealorbitperiod(days)': ('Orbite', 'Période orbitale sidérale (jours)', 'jours', 0, 'mesuré'),
    'revolutionperiod(days)': ('Orbite', 'Période orbitale sidérale (jours)', 'jours', 0, 'mesuré'),
    'tropicalorbitperiod(days)': ('Orbite', 'Période orbitale tropicale', 'jours', 0, 'mesuré'),
    'tropicalorbitperiod^(days)': ('Orbite', 'Période orbitale tropicale', 'jours', 0, 'mesuré'),
    'perihelion(10^6km)': ('Orbite', 'Distance au périhélie', 'km', 6, 'mesuré'),
    'aphelion(10^6km)': ('Orbite', "Distance à l'aphélie", 'km', 6, 'mesuré'),
    'perigee(10^6km)': ('Orbite', 'Distance au périgée', 'km', 6, 'mesuré'),
    'apogee(10^6km)': ('Orbite', "Distance à l'apogée", 'km', 6, 'mesuré'),
    'synodicperiod(days)': ('Orbite', 'Période synodique', 'jours', 0, 'mesuré'),
    'meanorbitalvelocity(km/s)': ('Orbite', 'Vitesse orbitale moyenne', 'km/s', 0, 'mesuré'),
    'max.orbitalvelocity(km/s)': ('Orbite', 'Vitesse orbitale maximale', 'km/s', 0, 'mesuré'),
    'min.orbitalvelocity(km/s)': ('Orbite', 'Vitesse orbitale minimale', 'km/s', 0, 'mesuré'),
    'orbitinclination(deg)': ('Orbite', 'Inclinaison sur l’écliptique', '°', 0, 'mesuré'),
    'inclinationtoecliptic(deg)': ('Orbite', 'Inclinaison sur l’écliptique', '°', 0, 'mesuré'),
    'inclinationtoearthequator(deg)': ('Orbite', "Inclinaison sur l'équateur terrestre", '°', 0, 'mesuré'),
    'orbiteccentricity': ('Orbite', 'Excentricité', '', 0, 'mesuré'),
    'recessionratefromearth(cm/yr)': ('Orbite', 'Éloignement annuel de la Terre', 'cm/an', 0, 'mesuré'),
    'siderealrotationperiod(hrs)': ('Rotation', 'Période de rotation sidérale (heures)', 'heures', 0, 'mesuré'),
    'lengthofday(hrs)': ('Rotation', 'Durée du jour solaire moyen', 'heures', 0, 'mesuré'),
    'obliquitytoorbit(deg)': ('Rotation', "Obliquité (inclinaison de l'axe sur l'orbite)", '°', 0, 'mesuré'),
    'inclinationofequator(deg)': ('Rotation', "Inclinaison de l'équateur sur l'orbite", '°', 0, 'mesuré'),
    # éléments moyens J2000 (texte) et observation depuis la Terre
    'semimajoraxis(au)': ('Orbite', 'Demi-grand axe (J2000)', 'UA', 0, 'mesuré'),
    'orbitaleccentricity': ('Orbite', 'Excentricité (J2000)', '', 0, 'mesuré'),
    'orbitalinclination(deg)': ('Orbite', 'Inclinaison sur l’écliptique (J2000)', '°', 0, 'mesuré'),
    'longitudeofascendingnode(deg)': ('Orbite', 'Longitude du nœud ascendant (J2000)', '°', 0, 'mesuré'),
    'longitudeofperihelion(deg)': ('Orbite', 'Longitude du périhélie (J2000)', '°', 0, 'mesuré'),
    'meanlongitude(deg)': ('Orbite', 'Longitude moyenne (J2000)', '°', 0, 'mesuré'),
    'distancefromearth/minimum(10^6km)': ('Vue depuis la Terre', 'Distance minimale à la Terre', 'km', 6,
                                          'mesuré'),
    'distancefromearth/maximum(10^6km)': ('Vue depuis la Terre', 'Distance maximale à la Terre', 'km', 6,
                                          'mesuré'),
    'distancefromearth/mean(10^6km)': ('Vue depuis la Terre', 'Distance moyenne à la Terre', 'km', 6, 'mesuré'),
    'apparentdiameterfromearth/maximum(secondsofarc)': ('Vue depuis la Terre', 'Diamètre apparent maximal', '″',
                                                        0, 'mesuré'),
    'apparentdiameterfromearth/minimum(secondsofarc)': ('Vue depuis la Terre', 'Diamètre apparent minimal', '″',
                                                        0, 'mesuré'),
    'apparentdiameterfromearth/at1a.u.(secondsofarc)': ('Vue depuis la Terre', 'Diamètre apparent à 1 UA', '″',
                                                        0, 'mesuré'),
    'meanvaluesatoppositionfromearth/distancefromearth(10^6km)':
        ('Vue depuis la Terre', "Distance moyenne à l'opposition", 'km', 6, 'mesuré'),
    'meanvaluesatoppositionfromearth/distancefromearth(equator,km)':
        ('Vue depuis la Terre', 'Distance moyenne à la Terre (depuis l’équateur)', 'km', 0, 'mesuré'),
    'meanvaluesatoppositionfromearth/apparentdiameter(secondsofarc)':
        ('Vue depuis la Terre', "Diamètre apparent moyen à l'opposition", '″', 0, 'mesuré'),
    'meanvaluesatoppositionfromearth/apparentvisualmagnitude':
        ('Lumière et couleur', "Magnitude moyenne à l'opposition", 'mag', 0, 'mesuré'),
    'meanvaluesatoppositionincludingrings/apparentvisualmagnitude':
        ('Lumière et couleur', "Magnitude moyenne à l'opposition (avec les anneaux)", 'mag', 0, 'mesuré'),
    'meanvaluesatinferiorconjunctionwithearth/distancefromearth(10^6km)':
        ('Vue depuis la Terre', 'Distance moyenne à la conjonction inférieure', 'km', 6, 'mesuré'),
    'meanvaluesatinferiorconjunctionwithearth/apparentdiameter(secondsofarc)':
        ('Vue depuis la Terre', 'Diamètre apparent moyen à la conjonction inférieure', '″', 0, 'mesuré'),
    'maximumapparentvisualmagnitude': ('Lumière et couleur', 'Magnitude apparente la plus brillante', 'mag', 0,
                                       'mesuré'),
    'maximumvisualmagnitude': ('Lumière et couleur', 'Magnitude apparente la plus brillante', 'mag', 0, 'mesuré'),
}
NS_DEUX_POINTS = [  # « Libellé: valeur » -> (motif, groupe, libellé, statut)
    (r'^discoverer$', 'Découverte', 'Découvreur(s) ou mission', 'publié'),
    (r'^discovery date$', 'Découverte', 'Date de découverte', 'publié'),
    (r'^right ascension$', 'Rotation', 'Pôle nord : ascension droite (J2000)', 'mesuré'),
    (r'^declination$', 'Rotation', 'Pôle nord : déclinaison (J2000)', 'mesuré'),
    (r'^dipole field strength$', 'Champ magnétique', 'Moment dipolaire', 'mesuré'),
    (r'^dipole tilt to rotational axis$', 'Champ magnétique', "Inclinaison du dipôle sur l'axe de rotation",
     'mesuré'),
    (r'^longitude of tilt$', 'Champ magnétique', "Longitude de l'inclinaison du dipôle", 'mesuré'),
    (r'^dipole offset$', 'Champ magnétique', 'Décalage du dipôle par rapport au centre', 'mesuré'),
    (r'^surface \(1 r.\) field strength$', 'Champ magnétique', 'Champ magnétique en surface', 'mesuré'),
    (r'^polar field$', 'Champ magnétique', 'Champ aux pôles', 'mesuré'),
    (r'^sunspots$', 'Champ magnétique', 'Champ dans les taches', 'mesuré'),
    (r'^prominences$', 'Champ magnétique', 'Champ dans les protubérances', 'mesuré'),
    (r'^chromospheric plages$', 'Champ magnétique', 'Champ dans les plages chromosphériques', 'mesuré'),
    (r'^bright chromospheric network$', 'Champ magnétique', 'Champ du réseau chromosphérique brillant', 'mesuré'),
    (r'^ephemeral \(unipolar\) active regions$', 'Champ magnétique', 'Champ des régions actives éphémères',
     'mesuré'),
    (r'^surface (?:gas )?pressure(?: \(top of photosphere\))?$', 'Atmosphère et surface', 'Pression en surface',
     'mesuré'),
    (r'^surface pressure \(night\)$', 'Atmosphère et surface', 'Pression en surface (nuit)', 'mesuré'),
    (r'^pressure at bottom of photosphere', 'Atmosphère et surface', 'Pression à la base de la photosphère',
     'mesuré'),
    (r'^surface density$', 'Atmosphère et surface', "Masse volumique de l'air en surface", 'mesuré'),
    (r'^scale height$', 'Atmosphère et surface', "Hauteur d'échelle", 'mesuré'),
    (r'^total mass of atmosphere$', 'Atmosphère et surface', "Masse de l'atmosphère", 'mesuré'),
    (r'^total mass of hydrosphere$', 'Atmosphère et surface', "Masse de l'hydrosphère", 'mesuré'),
    (r'^average temperature$', 'Atmosphère et surface', 'Température moyenne de surface', 'mesuré'),
    (r'^surface temperature$', 'Atmosphère et surface', 'Température de surface', 'mesuré'),
    (r'^diurnal temperature range', 'Atmosphère et surface', 'Écart de température jour-nuit', 'mesuré'),
    (r'^wind speeds$', 'Atmosphère et surface', 'Vitesse des vents', 'mesuré'),
    (r'^mean molecular weight$', 'Atmosphère et surface', 'Masse molaire moyenne (g/mol)', 'mesuré'),
    (r'^temperature at 1 bar$', 'Atmosphère et surface', 'Température à 1 bar', 'mesuré'),
    (r'^temperature at 0\.1 bar$', 'Atmosphère et surface', 'Température à 0,1 bar', 'mesuré'),
    (r'^density at 1 bar$', 'Atmosphère et surface', 'Masse volumique à 1 bar', 'mesuré'),
    (r'^abundance at surface$', 'Atmosphère et surface', 'Densité de particules en surface', 'mesuré'),
    (r'^effective temperature$', 'Atmosphère et surface', 'Température effective', 'mesuré'),
    (r'^temperature at top of photosphere$', 'Atmosphère et surface', 'Température au sommet de la photosphère',
     'mesuré'),
    (r'^temperature at bottom of photosphere$', 'Atmosphère et surface',
     'Température à la base de la photosphère', 'mesuré'),
    (r'^temperature at top of chromosphere$', 'Atmosphère et surface', 'Température au sommet de la chromosphère',
     'mesuré'),
    (r'^photosphere thickness$', 'Atmosphère et surface', 'Épaisseur de la photosphère', 'mesuré'),
    (r'^chromosphere thickness$', 'Atmosphère et surface', 'Épaisseur de la chromosphère', 'mesuré'),
    (r'^sun spot cycle$', 'Physique', 'Durée du cycle des taches', 'mesuré'),
    (r'^central pressure$', 'Modèles et hypothèses', 'Pression au centre (modèle solaire)', 'modèle'),
    (r'^central temperature$', 'Modèles et hypothèses', 'Température au centre (modèle solaire)', 'modèle'),
    (r'^central density$', 'Modèles et hypothèses', 'Masse volumique au centre (modèle solaire)', 'modèle'),
]
COMPO_FIN = (r'^(Numbers do not|Water is|Note that|Composition of the|For information|\(The atmosphere|Jovian|'
             r'Saturnian|Uranian|Neptunian|Charon|Satellites of|Other Moons|If no sub|Moon Home|.*Home Page)')


def ns_lines(page: str) -> list[str]:
    """Page NSSDC -> lignes : une ligne « a | b | c » par rangée de tableau, sinon les lignes du texte."""
    page = re.sub(r'<sup>(.*?)</sup>', r'^\1', page, flags=re.I | re.S)
    page = re.sub(r'<sub>(.*?)</sub>', r'\1', page, flags=re.I | re.S)
    page = re.sub(r'<tr.*?</tr>', lambda m: '\n' + ' | '.join(clean(c) for c in re.findall(
        r'<t[hd][^>]*>(.*?)</t[hd]>', m.group(0), re.S | re.I)) + '\n', page, flags=re.S | re.I)
    page = re.sub(r'<(?:p|br|h\d|/h\d|li)[^>]*>', '\n', page, flags=re.I)
    text = html.unescape(re.sub(r'<[^>]+>', '', page)).replace('\xa0', ' ').replace('\t', '    ')
    return [line.rstrip() for line in text.splitlines()]


def ns_value(fiches, cle, spec, raw, src):
    groupe, lib, unite, exp, statut = spec
    raw = raw.strip()
    p = parse_value(raw)
    if p is None or p[3] not in ('', '*', '**'):
        if raw and raw not in ('-', '?'):
            fiches.add(cle, groupe, lib, fr(raw), '', '', statut, src)
        return
    pre, num, unc, _ = p
    val = scaled(num, exp)
    val = with_pre(pre, val)
    fiches.add(cle, groupe, lib, val, scaled(unc, exp) if unc else '', unite, statut, src)


def ns_colon(fiches, cle, lab, val, src):
    for pat, groupe, lib, statut in NS_DEUX_POINTS:
        if re.search(pat, lab.lower().strip()):
            val = re.sub(r'\s+', ' ', val).strip()
            if lib.startswith('Pôle nord'):
                u = '° (T : siècles depuis J2000)' if 'T' in val else '°'
                fiches.add(cle, groupe, lib, val, '', u, statut, src)
                return
            p = parse_value(val)
            u = unit_of(p[3]) if p else None
            if p and u and re.fullmatch(r'[A-Za-z^\d/.]*\s*(\(.*\))?', p[3]) and '-' not in p[3][:3]:
                v = with_pre(p[0], p[1])
                fiches.add(cle, groupe, lib, v, p[2], u, statut, src)
            else:
                fiches.add(cle, groupe, lib, fr(val.replace('+/-', '±')), '', '', statut, src)
            return


def ns_composition(fiches, cle, block: list[str], src):
    parts: dict[str, list[str]] = {}
    cur = 'Composition de l’atmosphère'
    for line in block:
        s = line.strip()
        m = re.match(r'^(Major(?: elements)?|Minor(?: elements)? \(ppm\)|Aerosols)\s*:\s*(.*)$', s)
        if m:
            cur = {'Aerosols': 'Aérosols'}.get(m.group(1), 'Composition : éléments majeurs'
                                               if m.group(1).startswith('Major') else
                                               'Composition : éléments mineurs (ppm)')
            s = m.group(2)
        if s:
            parts.setdefault(cur, []).append(s)
    for lib, txt in parts.items():
        fiches.add(cle, 'Atmosphère et surface', lib, fr(' '.join(txt)), '', '', 'mesuré', src)


def nssdc_page(fiches: Fiches, cache: str, cle: str, page_name: str, nom_en: str):
    page = fetch(cache, NSSDC + page_name, os.path.join('nssdc', page_name))
    maj = re.search(r'Last Updated:\s*([^<\n]+?\d{4})', page)
    src = f'NASA NSSDCA {nom_en} Fact Sheet (D. R. Williams' + (f', mise à jour {maj.group(1).strip()})'
                                                                 if maj else ')')
    lines = ns_lines(page)
    in_table, parent, i = False, '', 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        i += 1
        if not s:
            continue
        if re.match(r'^(Charon \(P1\)|Satellites of|Other Moons|Author/Curator)', s):
            break
        if ' | ' in s or s in (nom_en,):
            cells = [c.strip() for c in line.split('|')]
            if not cells[0] and len(cells) > 1:          # en-tête : la 1re colonne est-elle notre astre ?
                in_table = cells[1].startswith(nom_en)
                continue
            if in_table and len(cells) >= 2:
                spec = NS.get(re.sub(r'[\s*]', '', cells[0].lower()))
                if spec:
                    ns_value(fiches, cle, spec, cells[1], src)
            continue
        if re.match(r'^(Atmospheric composition|Estimated Composition|Photosphere Composition)', s):
            head, _, rest = s.partition(':')
            block = [rest] if rest.strip() else []
            while i < len(lines) and lines[i].strip() and not re.match(COMPO_FIN, lines[i].strip()):
                block.append(lines[i])
                i += 1
            ns_composition(fiches, cle, block, src)
            continue
        m = re.match(r'^(.+?)\s{2,}([-+<>~]?\s*[\d.,]+)\s*$', s)
        if m:
            lab = m.group(1).strip()
            key = re.sub(r'[\s*]', '', ((parent + '/') if line.startswith('    ') else '') + lab).lower()
            spec = NS.get(key)
            if spec:
                ns_value(fiches, cle, spec, m.group(2), src)
                continue
        m = re.match(r'^([^:]{2,60}?)\s*:\s*(.+)$', s)
        if m:
            val = m.group(2)
            if m.group(1).lower() == 'discoverer':      # suite sur la ligne suivante (Neptune)
                while i < len(lines) and lines[i].startswith('      ') and ':' not in lines[i]:
                    val += ' ' + lines[i].strip()
                    i += 1
            ns_colon(fiches, cle, m.group(1), val, src)
            continue
        if not line.startswith(' '):
            parent = s


# ----------------------------------------------------------------------------------------------- calculs
def fnum(row):
    try:
        return float(row[3]), (float(row[4]) if row[4] else 0.0)
    except (TypeError, ValueError):
        return None


def sig(x: float, n: int = 4) -> str:
    return f'{x:.{n}g}'.replace('e+', 'e')


def calculs_lunes(fiches: Fiches, cles: list[str]):
    """Masse = GM/G, gravité = GM/R², libération = √(2GM/R) à partir des valeurs JPL mesurées."""
    for cle in cles:
        gm_r, r_r = fiches.get(cle, 'Paramètre gravitationnel GM'), fiches.get(cle, 'Rayon moyen')
        gm = fnum(gm_r) if gm_r else None
        if not gm or gm[0] <= 0 or (gm[1] and gm[1] > 0.5 * gm[0]):
            continue
        src_gm = gm_r[7]
        m, dm = gm[0] / G_KM, gm[1] / G_KM
        fiches.add(cle, 'Physique', 'Masse', sig(m, 6), sig(dm, 2) if dm else '', 'kg', 'calculé',
                   f'M = GM/G ; GM : {src_gm} ; {G_TXT}')
        r = fnum(r_r) if r_r else None
        if not r or r[0] <= 0 or r_r[6] != 'mesuré':
            continue
        rel_gm = gm[1] / gm[0] if gm[1] else 0.0
        rel_r = r[1] / r[0] if r[1] else 0.0
        g = gm[0] / r[0] ** 2 * 1000.0                  # km/s² -> m/s²
        dg = g * math.hypot(rel_gm, 2 * rel_r)
        fiches.add(cle, 'Physique', 'Gravité de surface moyenne', sig(g), sig(dg, 2) if dg else '', 'm/s²',
                   'calculé', f'g = GM/R² (GM et R moyen du JPL : {src_gm} ; {r_r[7]})')
        v = math.sqrt(2 * gm[0] / r[0])
        dv = v * 0.5 * math.hypot(rel_gm, rel_r)
        fiches.add(cle, 'Physique', 'Vitesse de libération', sig(v), sig(dv, 2) if dv else '', 'km/s', 'calculé',
                   f'v = √(2GM/R) (GM et R moyen du JPL : {src_gm} ; {r_r[7]})')


def iau_soleil(fiches: Fiches):
    src = 'UAI 2015 Résolution B3 (Prša et al. 2016, AJ 152, 41) : valeur nominale de conversion'
    for lib, val, u in (('Rayon nominal (UAI 2015)', '695700', 'km'),
                        ('Éclairement solaire total nominal à 1 UA (UAI 2015)', '1361', 'W/m²'),
                        ('Luminosité nominale (UAI 2015)', '3.828e26', 'W'),
                        ('Température effective nominale (UAI 2015)', '5772', 'K'),
                        ('GM nominal (UAI 2015)', '1.3271244e11', 'km³/s²')):
        fiches.add('Soleil', 'Physique', lib, val, '', u, 'publié', src)


# ----------------------------------------------------------------------------------------------- principal
def lire_lunes(path: str) -> list[tuple[int, str, int]]:
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            p = line.rstrip('\n').split('\t')
            if len(p) >= 3 and p[0].strip().isdigit():
                out.append((int(p[0]), p[1], int(p[2])))
    return out


def identite(fiches: Fiches, lunes):
    src = 'Code NAIF (NASA/JPL) ; planète centrale d’après lunes.tsv (code NAIF du centre)'
    fiches.add('Soleil', 'Identité', 'Type', 'étoile', '', '', 'publié', 'NASA NSSDCA Sun Fact Sheet')
    fiches.add('Soleil', 'Identité', 'Code NAIF', '10', '', '', 'publié', 'NASA/JPL NAIF')
    for code, (cle, _, typ) in PLANETES.items():
        fiches.add(cle, 'Identité', 'Type', typ, '', '', 'publié',
                   'JPL SSD (Pluton : planète naine, UAI 2006 Résolution B5/B6)' if code == 999 else 'JPL SSD')
        fiches.add(cle, 'Identité', 'Code NAIF', str(code), '', '', 'publié', 'NASA/JPL NAIF')
    fiches.add('Lune', 'Identité', 'Type', 'satellite naturel', '', '', 'publié', 'JPL SSD')
    fiches.add('Lune', 'Identité', 'Code NAIF', '301', '', '', 'publié', 'NASA/JPL NAIF')
    fiches.add('Lune', 'Identité', 'Astre central', 'Terre', '', '', 'publié', 'NASA/JPL NAIF')
    for code, cle, centre in lunes:
        fiches.add(cle, 'Identité', 'Type', 'satellite naturel', '', '', 'publié', src)
        fiches.add(cle, 'Identité', 'Code NAIF', str(code), '', '', 'publié', src)
        if centre in PLANETES:
            fiches.add(cle, 'Identité', 'Astre central', PLANETES[centre][0], '', '', 'publié', src)


def main():
    lunes_path = sys.argv[1] if len(sys.argv) > 1 else LUNES_DEFAUT
    sortie = sys.argv[2] if len(sys.argv) > 2 else SORTIE_DEFAUT
    cache = sys.argv[3] if len(sys.argv) > 3 else CACHE_DEFAUT
    lunes = lire_lunes(lunes_path)
    cle_of = {code: cle for code, cle, _ in lunes}
    cle_of[301] = 'Lune'
    noms_jpl: dict[int, str] = {}
    fiches = Fiches()

    identite(fiches, lunes)
    jpl_planetes(fiches, cache)
    jpl_sats_phys(fiches, cache, cle_of, noms_jpl)
    jpl_sats_elem(fiches, cache, cle_of, noms_jpl)
    jpl_approx(fiches, cache)
    decouv = jpl_decouverte(fiches, cache, cle_of, noms_jpl)
    codes = {10: 'Soleil', **{c: v[0] for c, v in PLANETES.items()}, **cle_of}
    naif_pck(fiches, cache, cle_of)
    sans_hz = jpl_horizons(fiches, cache, codes)
    for cle, page, en in (('Soleil', 'sunfact.html', 'Sun'), ('Mercure', 'mercuryfact.html', 'Mercury'),
                          ('Vénus', 'venusfact.html', 'Venus'), ('Terre', 'earthfact.html', 'Earth'),
                          ('Lune', 'moonfact.html', 'Moon'), ('Mars', 'marsfact.html', 'Mars'),
                          ('Jupiter', 'jupiterfact.html', 'Jupiter'), ('Saturne', 'saturnfact.html', 'Saturn'),
                          ('Uranus', 'uranusfact.html', 'Uranus'), ('Neptune', 'neptunefact.html', 'Neptune'),
                          ('Pluton', 'plutofact.html', 'Pluto')):
        nssdc_page(fiches, cache, cle, page, en)
    iau_soleil(fiches)
    calculs_lunes(fiches, [cle for _, cle, _ in lunes] + ['Lune'])

    ordre = ['Soleil'] + [v[0] for v in PLANETES.values()] + ['Lune'] + [cle for _, cle, _ in lunes]
    entete = [f'systeme_solaire.tsv : écrit par pipeline/natif/fiches_systeme_solaire.py le '
              f'{datetime.date.today().isoformat()}',
              'Sources : JPL SSD (planets/phys_par, planets/approx_pos, sats/phys_par, sats/elem, sats/discovery), '
              'NASA/NAIF pck00011.tpc, JPL Horizons (fiches objets), NASA NSSDCA Planetary Fact Sheets, UAI 2015 Résolution B3']
    n = fiches.write(sortie, ordre, entete)
    vides = [c for c in ordre if len(fiches.rows.get(c, [])) <= 3]
    print(f'{len(ordre)} astres, {n} lignes -> {sortie}')
    print(f'découverte reliée : {decouv[0]} lunes, non reliée : {decouv[1]} {decouv[2:]}')
    print(f'sans fiche Horizons : {len(sans_hz)} {sans_hz[:10]}')
    print(f'astres sans aucune grandeur (identité seule) : {len(vides)} {vides[:15]}')


if __name__ == '__main__':
    main()
