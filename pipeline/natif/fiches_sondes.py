#!/usr/bin/env python3
"""Fiches des sondes -> fiches/sondes.tsv (format long, voir docs/fiches-format.md).

Clés : les noms des sondes de sondes.bin (lus dans le fichier, « UNIVSON2 », 32 octets par nom ; pipeline/natif/sondes.py).
Sources, toutes officielles, lues telles quelles (cache brut dans C:\\tmp\\fiches\\cache\\sondes) :
  1. NSSDCA (NASA Space Science Data Coordinated Archive), fiche de la sonde par son identifiant COSPAR :
     https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=<COSPAR> : « Facts in Brief » (date, lanceur, lieu,
     masse, puissance nominale), agence, disciplines, autres noms, responsables.
  2. NSSDCA, page « Launch/Orbital information » (displayTrajectory.action) : heure du lancement, puis chaque tronçon du
     vol (croisière autour du Soleil, survols) avec ses paramètres d'orbite et l'heure du passage au plus près.
  3. NASA Science, page de la mission (https://science.nasa.gov/mission/...) : encadré « In Depth » (masse, puissance,
     objectifs, conception) et liste « Key Dates » (dates clés publiées par la NASA, texte anglais d'origine).
Statuts : nombres publiés par la NASA/NSSDCA = « mesuré » (consigne de Marc) ; noms, textes, lieux = « publié » ;
conversions faites ici = « calculé », avec la formule dans la colonne source. Rien n'est inventé : un champ absent de la
page n'est pas écrit. Les textes anglais sont recopiés tels quels (citation de la source), sans traduction inventée.
Usage : python fiches_sondes.py [sondes.bin] [sortie.tsv]
"""
import datetime
import html
import math
import os
import re
import struct
import sys
import time
import urllib.request

SONDES_BIN = r'C:\dev\Univers-PC\sondes.bin'
SORTIE = r'C:\tmp\fiches\sondes.tsv'
CACHE = r'C:\tmp\fiches\cache\sondes'
UA = {'User-Agent': 'Mozilla/5.0 (Univers fiches; usage personnel)'}

# Identifiant COSPAR (NSSDCA) et page NASA Science de chaque sonde de l'appli. Ces correspondances sont des faits
# publics (les fiches NSSDCA les donnent en en-tête « NSSDCA/COSPAR ID ») ; le script vérifie que le nom de la sonde
# apparaît bien dans chaque page lue.
IDENTITES = {
    'Voyager 1': ('1977-084A', 'voyager/voyager-1'),
    'Voyager 2': ('1977-076A', 'voyager/voyager-2'),
    'Pioneer 10': ('1972-012A', 'pioneer-10'),
    'Pioneer 11': ('1973-019A', 'pioneer-11'),
    'New Horizons': ('2006-001A', 'new-horizons'),
}
NSSDCA = 'NSSDCA (NASA), fiche {id}'
NSSDCA_TRAJ = 'NSSDCA (NASA), Launch/Orbital information {id}'
NASA_SCI = 'NASA Science, science.nasa.gov/mission/{p}'
# Rayons de référence publiés par la NSSDCA dans « Apside Definitions » (lus dans la page, pas supposés ici).
MOIS = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}


def noms_sondes(chemin: str) -> list:
    """Noms des sondes dans sondes.bin, dans l'ordre du fichier (format de natif/src/sondes.h)."""
    noms = []
    with open(chemin, 'rb') as f:
        if f.read(8) != b'UNIVSON2':
            raise SystemExit('sondes.bin : en-tête inattendu')
        n = struct.unpack('<q', f.read(8))[0]
        for _ in range(n):
            noms.append(f.read(32).split(b'\0')[0].decode('utf-8'))
            for _ in range(struct.unpack('<q', f.read(8))[0]):
                _, _, c = struct.unpack('<ddq', f.read(24))
                f.seek(c * 48, 1)
    return noms


def page(url: str, fichier: str) -> str:
    """Page lue dans le cache, sinon téléchargée une fois (une seconde de pause : poli envers le serveur)."""
    chemin = os.path.join(CACHE, fichier)
    if not os.path.exists(chemin) or os.path.getsize(chemin) < 2000:
        os.makedirs(CACHE, exist_ok=True)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            data = r.read()
        with open(chemin, 'wb') as f:
            f.write(data)
        time.sleep(1)
    with open(chemin, encoding='utf-8', errors='replace') as f:
        # Espaces insécables (NSSDCA : « Launch&nbsp;Vehicle ») ramenés à des espaces simples pour la lecture.
        return f.read().replace('\xa0', ' ').replace('&#xa0;', ' ').replace('&nbsp;', ' ')


def jetons(txt: str) -> list:
    """Texte de la page découpé en cases (une par élément HTML), sans scripts ni styles."""
    txt = re.sub(r'<script.*?</script>|<style.*?</style>', '', txt, flags=re.S)
    txt = html.unescape(re.sub(r'<[^>]+>', '|', txt)).replace('\xa0', ' ')
    return [t.strip() for t in re.split(r'\s*\|\s*', txt) if t.strip()]


def de(nom: str) -> str:
    """« de Jupiter », « d'Uranus » : élision devant une voyelle."""
    return ("d'" if nom[:1] in 'AEIOUÉ' else 'de ') + nom


def arrondi(x: float, chiffres: int) -> str:
    """x arrondi à « chiffres » chiffres significatifs (pas plus de précision que la valeur publiée)."""
    return str(int(round(x, chiffres - 1 - int(math.floor(math.log10(abs(x)))))))


def nombre(txt: str):
    m = re.match(r'^\s*([-+]?[\d,]*\.?\d+)', txt)
    return m.group(1).replace(',', '') if m else None


class Fiche:
    """Lignes d'une sonde, dans l'ordre des groupes conseillés."""

    def __init__(self, cle):
        self.cle, self.lignes = cle, []

    def add(self, groupe, libelle, valeur, unite='', statut='mesuré', source='', incertitude=''):
        if valeur is None or str(valeur).strip() == '':
            return
        v = re.sub(r'[\t\r\n]+', ' ', str(valeur)).strip()
        self.lignes.append((self.cle, groupe, libelle, v, incertitude, unite, statut, source))


def facts_nssdca(fi: Fiche, cospar: str, txt: str) -> None:
    """« Facts in Brief », agence, disciplines, autres noms et responsables de la fiche NSSDCA."""
    src = NSSDCA.format(id=cospar)
    fi.add('Identité', 'Identifiant COSPAR (NSSDCA)', cospar, statut='publié', source=src)
    faits = dict(re.findall(r'<strong>([^<:]+):</strong>\s*([^<]+)<br', txt))
    fi.add('Identité', 'Date de lancement', faits.get('Launch Date', '').strip(), statut='mesuré', source=src)
    fi.add('Identité', 'Lanceur', faits.get('Launch Vehicle', '').strip(), statut='publié', source=src)
    fi.add('Identité', 'Lieu de lancement', faits.get('Launch Site', '').strip(), statut='publié', source=src)
    m = re.match(r'([\d.,]+)\s*kg', faits.get('Mass', ''))
    if m:
        fi.add('Physique', 'Masse (champ « Mass » de la NSSDCA)', m.group(1).replace(',', ''), 'kg', source=src)
    m = re.match(r'([\d.,]+)\s*W', faits.get('Nominal Power', ''))
    if m:
        fi.add('Physique', 'Puissance nominale', m.group(1).replace(',', ''), 'W', source=src)
    for titre, libelle, groupe in (('Funding Agency', 'Agence', 'Identité'), ('Disciplines?', 'Discipline', 'Identité'),
                                   ('Alternate Names', 'Autre nom', 'Autres noms')):
        bloc = re.search(r'<h2>' + titre + r'</h2>\s*<ul>(.*?)</ul>', txt, re.S)
        for li in re.findall(r'<li>(.*?)</li>', bloc.group(1), re.S) if bloc else []:
            fi.add(groupe, libelle, html.unescape(re.sub(r'<[^>]+>', '', li)), statut='publié', source=src)
    desc = re.search(r'<h2>Description</h2>\s*<p>(.*?)</p>', txt, re.S)
    if desc:
        phrase = re.split(r'(?<=\.)\s', html.unescape(re.sub(r'<[^>]+>', '', desc.group(1))).strip())[0]
        fi.add('Identité', 'Objectif (texte NSSDCA, en anglais)', phrase, statut='publié', source=src)
    for nom, role in re.findall(r'<tr><td>([^<]+)</td><td>([^<]+)</td><td>[^<]*</td><td>', txt):
        fi.add('Identité', f'Responsable ({role.strip()})', nom.strip(), statut='publié', source=src)


def trajectoire_nssdca(fi: Fiche, cospar: str, txt: str) -> None:
    """Heure du lancement et tronçons du vol (croisières, survols) de la page « Launch/Orbital information »."""
    src = NSSDCA_TRAJ.format(id=cospar)
    m = re.search(r'Launch Date/Time:</strong>\s*([^<]+)<', txt)
    if m:
        fi.add('Identité', 'Date et heure du lancement (TU)', m.group(1).strip(), statut='mesuré', source=src)
    rayons = {u: float(km.replace(',', '')) for u, km in re.findall(r'<td>(R[A-Z])</td>\s*<td>[^<(]*\(1 R[A-Z] = ([\d,]+) km\)', txt)}
    corps = {'Jupiter': 'Jupiter', 'Saturn': 'Saturne', 'Uranus': 'Uranus', 'Neptune': 'Neptune', 'Sun': 'Soleil', 'Pluto': 'Pluton'}
    for k, table in enumerate(re.findall(r'<table[^>]*class="alternate">(.*?)</table>', txt, re.S), start=1):
        typ = re.search(r'Type: ([^<]+)<', table)
        cen = re.search(r'Central Body: ([^<]+)<', table)
        if not typ or not cen:
            continue
        typ, cen = typ.group(1).strip(), cen.group(1).strip()
        nom_c = corps.get(cen, cen)
        g = 'Mouvement'
        if typ == 'Flyby':
            t = re.search(r'Closest approach time \(UTC\): ([^<]+)<', table)
            fi.add(g, f'Survol {de(nom_c)} : passage au plus près (TU)', t.group(1).strip() if t else '', source=src)
        else:
            lib = {'Interplanetary cruise': 'Croisière', 'Solar system escape': 'Sortie du système solaire'}.get(typ, typ)
            for quand, cle in (('début', 'Epoch start'), ('fin', 'Epoch stop')):
                t = re.search(cle + r' \(UTC\): ([^<]*)<', table)
                fi.add(g, f'Tronçon {k} ({lib}, autour {'du Soleil' if nom_c == 'Soleil' else 'de ' + nom_c}) : {quand} (TU)', t.group(1).strip() if t else '', source=src)
        cases = re.findall(r'<tr><td>([^<]*)</td><td>([^<]*)</td><td>([^<]*)</td><td>([^<]*)</td><td>([^<]*)</td></tr>', table)
        if not cases:
            continue
        peri, apo, per, inc, exc = (c.strip() for c in cases[0])
        prefixe = f'Survol {de(nom_c)}' if typ == 'Flyby' else f'Tronçon {k} autour {'du Soleil' if nom_c == 'Soleil' else 'de ' + nom_c}'
        for lib, val in (('périapside', peri), ('apoapside', apo)):
            m = re.match(r'([\d.]+)\s*(\S+)', val)
            if not m:
                continue
            unite = {'AU': 'UA'}.get(m.group(2), m.group(2))
            if unite in rayons:
                corps_r = {'RJ': 'Jupiter', 'RS': 'Saturne', 'RU': 'Uranus', 'RN': 'Neptune'}.get(unite, unite)
                fi.add(g, f'{prefixe} : {lib}', m.group(1), f'rayons {de(corps_r)}', source=src)
                fi.add(g, f'{prefixe} : {lib} (en km)', arrondi(float(m.group(1)) * rayons[unite], len(m.group(1).replace('.', '').lstrip('0'))), 'km', 'calculé',
                       f'{m.group(1)} × {rayons[unite]:.0f} km (1 {unite} selon la même page NSSDCA), arrondi au même nombre de chiffres significatifs')
            else:
                fi.add(g, f'{prefixe} : {lib}', m.group(1), unite, source=src)
        fi.add(g, f'{prefixe} : période', nombre(per), '', source=src)
        fi.add(g, f'{prefixe} : inclinaison', nombre(inc), '°', source=src)
        fi.add(g, f'{prefixe} : excentricité', nombre(exc), '', source=src)


INFOBOX = ['Nation', 'Objective(s)', 'Spacecraft', 'Spacecraft Mass', 'Spacecraft Power', 'Mission Design and Management',
           'Launch Vehicle', 'Launch Date and Time', 'Launch Site', 'Scientific Instruments', 'Firsts', 'Key Dates']
DATE_RE = re.compile(r'^((?:Mid-|Early |Late )?(?:Jan|Feb|March|April|May|June|July|Aug|Sept|Oct|Nov|Dec)[a-z]*\.?\s*(?:\d{1,2})?,?\s*\d{4})\s*:?\s*(.*)$')


def date_iso(txt: str) -> str:
    """« Sept. 5, 1977 » -> « 1977-09-05 » ; date incomplète (mois seul, « Mid-March ») : rendue telle quelle."""
    m = re.match(r'^([A-Za-z]+)\.?\s*(\d{1,2}),\s*(\d{4})$', txt.strip())
    if m and m.group(1)[:3].lower() in MOIS:
        return f'{int(m.group(3)):04d}-{MOIS[m.group(1)[:3].lower()]:02d}-{int(m.group(2)):02d}'
    return txt.strip()


def nasa_science(fi: Fiche, chemin: str, txt: str) -> None:
    """Encadré « In Depth » et « Key Dates » de la page NASA Science de la mission."""
    src = NASA_SCI.format(p=chemin)
    tj = jetons(txt)
    try:
        i0 = tj.index('Nation')
    except ValueError:
        return
    champs, cur = {}, None
    for t in tj[i0:i0 + 120]:
        if t in INFOBOX:
            cur = t
            champs.setdefault(cur, [])
            continue
        if t.startswith('In Depth') or (cur == 'Key Dates' and len(t) > 220):
            break
        if cur:
            champs[cur].append(t)
    fi.add('Identité', 'Objectifs (NASA, en anglais)', ' '.join(champs.get('Objective(s)', [])), statut='publié', source=src)
    fi.add('Identité', 'Pays', ' '.join(champs.get('Nation', [])), statut='publié', source=src)
    fi.add('Identité', 'Conception et conduite de la mission', ' '.join(champs.get('Mission Design and Management', [])), statut='publié', source=src)
    m = re.search(r'\(([\d,.]+) kilograms\)', ' '.join(champs.get('Spacecraft Mass', [])))
    if m:
        fi.add('Physique', 'Masse (NASA, « Spacecraft Mass »)', m.group(1).replace(',', ''), 'kg', source=src)
    fi.add('Physique', 'Alimentation électrique (NASA, en anglais)', ' '.join(champs.get('Spacecraft Power', [])), statut='publié', source=src)
    fi.add('Identité', 'Lancement, date et heure (NASA)', ' '.join(champs.get('Launch Date and Time', [])), statut='mesuré', source=src)
    fi.add('Identité', 'Pas de tir (NASA)', ' '.join(champs.get('Launch Site', [])), statut='publié', source=src)
    fi.add('Identité', 'Lanceur (NASA, détail)', ' '.join(champs.get('Launch Vehicle', [])), statut='publié', source=src)
    # Dates clés : une date puis son évènement (dans la même case ou la suivante).
    kd, k = champs.get('Key Dates', []), 0
    while k < len(kd):
        m = DATE_RE.match(kd[k])
        if not m:
            k += 1
            continue
        quand, quoi = m.group(1), m.group(2).strip()
        if not quoi and k + 1 < len(kd) and not DATE_RE.match(kd[k + 1]):
            quoi, k = kd[k + 1].lstrip(': ').strip(), k + 1
        fi.add('Découverte', f'Date clé : {quoi} (NASA, en anglais)', date_iso(quand), statut='mesuré', source=src)
        k += 1


def main() -> None:
    bin_path = sys.argv[1] if len(sys.argv) > 1 else SONDES_BIN
    sortie = sys.argv[2] if len(sys.argv) > 2 else SORTIE
    noms = noms_sondes(bin_path)
    fiches, manques = [], []
    for nom in noms:
        if nom not in IDENTITES:
            manques.append(nom)
            continue
        cospar, chemin = IDENTITES[nom]
        fi = Fiche(nom)
        t1 = page(f'https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id={cospar}', f'{cospar}.html')
        t2 = page(f'https://nssdc.gsfc.nasa.gov/nmc/spacecraft/displayTrajectory.action?id={cospar}', f'traj_{cospar}.html')
        t3 = page(f'https://science.nasa.gov/mission/{chemin}/', f'nasa_{os.path.basename(chemin)}.html')
        for t, quoi in ((t1, 'NSSDCA'), (t2, 'NSSDCA trajectoire'), (t3, 'NASA Science')):
            if nom not in t.replace('\xa0', ' '):
                raise SystemExit(f'{nom} : la page {quoi} ne parle pas de cette sonde')
        facts_nssdca(fi, cospar, t1)
        trajectoire_nssdca(fi, cospar, t2)
        nasa_science(fi, chemin, t3)
        ordre = ['Identité', 'Physique', 'Mouvement', 'Découverte', 'Autres noms']
        fiches.extend(sorted(fi.lignes, key=lambda r: ordre.index(r[1]) if r[1] in ordre else 99))
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    with open(sortie, 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'# fiches_sondes.py, {datetime.date.today().isoformat()} : NSSDCA (nssdc.gsfc.nasa.gov/nmc) et NASA Science (science.nasa.gov)\n')
        f.write('# cle\tgroupe\tlibelle\tvaleur\tincertitude\tunite\tstatut\tsource\n')
        for r in fiches:
            f.write('\t'.join(r) + '\n')
    print(f'{len(noms)} sondes dans sondes.bin, {len(noms) - len(manques)} fiches, {len(fiches)} lignes -> {sortie}')
    if manques:
        print('sans fiche (identifiant COSPAR inconnu du script) :', ', '.join(manques))


if __name__ == '__main__':
    main()
