#!/usr/bin/env python3
"""Fiches des astéroïdes et des comètes -> fiches/petits_corps.tsv (variante compacte « tableau », docs/fiches-format.md).

Clés : le libellé de asteroides::Catalogue::label (natif/src/asteroides_catalogue.h), reproduit à l'identique à partir
de asteroides_noms.txt (lignes « Nom~désignation », comètes terminées par « ~c ») :
  astéroïde nommé « Ceres (1) », sans nom « Astéroïde 2000 CM104 » ; comète nommée « 1P/Halley », sans nom
  « Comète 2026 T1 ».
Sources (cache brut dans C:\\tmp\\fiches\\cache\\petits_corps) :
  1. JPL Small-Body Database Query API (https://ssd-api.jpl.nasa.gov/doc/sbdb_query.html), en masse, pleine précision,
     par pages de 100 000 objets (limit / limit-from), une requête à la fois : éléments d'orbite et leurs incertitudes
     1 sigma, époque, classe, MOID, NEO/PHA, qualité de l'orbite, H, G, diamètre, albédo, rotation, GM, densité, taille,
     types spectraux, couleurs ; comètes : M1, M2, K1, K2, PC, paramètres non gravitationnels A1, A2, A3, DT.
  2. JPL SBDB API objet par objet (https://ssd-api.jpl.nasa.gov/doc/sbdb.html) seulement pour les astéroïdes numérotés
     1 à 1000 et les comètes périodiques numérotées (« 1P »…) : découverte (date, lieu, découvreurs, référence, origine
     du nom quand la base l'a) et incertitudes des paramètres physiques (albédo, période, GM, densité) que l'API en masse ne donne pas.
Statuts : toute valeur de la base = « mesuré » (valeur ajustée sur des observations et publiée par le JPL) ; noms,
classes, types = « publié ». Rien n'est déduit ici : pas de diamètre tiré de H (si la base n'en a pas, la case reste
vide). Une case vide de la base reste vide.
Usage : python fiches_petits_corps.py [--sans-decouverte] [dossier de asteroides_noms.txt] [sortie.tsv]
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

APPLI = r'C:\dev\Univers-PC'
SORTIE = r'C:\tmp\fiches\petits_corps.tsv'
CACHE = r'C:\tmp\fiches\cache\petits_corps'
UA = {'User-Agent': 'Univers-fiches/1.0 (usage personnel, educatif)'}
TAILLE_MAX = 2 * 1024 ** 3      # au-delà de ~2 Go on s'arrête (pas de stockage énorme sans accord de Marc)
PAGE = 100_000
QUERY = 'https://ssd-api.jpl.nasa.gov/sbdb_query.api'
OBJET = 'https://ssd-api.jpl.nasa.gov/sbdb.api'
SRC = 'JPL SBDB, API de requête (ssd-api.jpl.nasa.gov), lue le {date}'
SRC_OBJ = 'JPL SBDB, API objet (ssd-api.jpl.nasa.gov/sbdb.api), lue le {date}'

# Classes d'orbite du JPL (liste publiée dans la documentation de l'API, paramètre sb-class), en français.
CLASSES = {
    'IEO': 'Atira (orbite entièrement à l\'intérieur de celle de la Terre)', 'ATE': 'Aten (géocroiseur, a < 1 UA)',
    'APO': 'Apollo (géocroiseur, a > 1 UA, q < 1,017 UA)', 'AMO': 'Amor (géocroiseur extérieur à la Terre)',
    'MCA': 'Aréocroiseur (croise l\'orbite de Mars)', 'IMB': 'Ceinture principale intérieure',
    'MBA': 'Ceinture principale', 'OMB': 'Ceinture principale extérieure', 'TJN': 'Troyen de Jupiter',
    'CEN': 'Centaure', 'TNO': 'Objet transneptunien', 'PAA': 'Orbite parabolique', 'HYA': 'Orbite hyperbolique',
    'AST': 'Astéroïde (autre)', 'JFc': 'Comète de la famille de Jupiter', 'JFC': 'Comète de la famille de Jupiter',
    'HTC': 'Comète de type Halley', 'ETc': 'Comète de type Encke', 'CTc': 'Comète de type Chiron',
    'COM': 'Comète', 'PAR': 'Comète à orbite parabolique', 'HYP': 'Comète à orbite hyperbolique',
}
OUI_NON = {'Y': 'oui', 'N': 'non'}

# Colonnes du tableau : (champ de la base, champ de son incertitude ou None, groupe, libellé, unité, statut, source).
# Source « Q » = API de requête ; « O » = API objet (seulement le sous-ensemble 1-1000 et comètes périodiques).
COLONNES = [
    ('full_name', None, 'Identité', 'Désignation complète (JPL)', '', 'publié', 'Q'),
    ('spkid', None, 'Identité', 'Identifiant SPK (JPL)', '', 'publié', 'Q'),
    ('prefix', None, 'Identité', 'Préfixe de comète (P périodique, C non périodique, I interstellaire)', '', 'publié', 'Q'),
    ('class', None, 'Identité', 'Classe orbitale (code JPL)', '', 'publié', 'Q'),
    ('class_fr', None, 'Identité', 'Classe orbitale', '', 'publié', 'Q'),
    ('neo', None, 'Identité', 'Géocroiseur (NEO)', '', 'publié', 'Q'),
    ('pha', None, 'Identité', 'Potentiellement dangereux (PHA)', '', 'publié', 'Q'),
    ('H', 'H_sigma', 'Physique', 'Magnitude absolue H', 'mag', 'mesuré', 'Q'),
    ('G', None, 'Physique', 'Paramètre de pente G', '', 'mesuré', 'Q'),
    ('diameter', 'diameter_sigma', 'Physique', 'Diamètre', 'km', 'mesuré', 'Q'),
    ('extent', 'extent_sig', 'Physique', 'Dimensions (axes)', 'km', 'mesuré', 'Q'),
    ('albedo', 'albedo_sig', 'Physique', 'Albédo géométrique', '', 'mesuré', 'Q'),
    ('GM', 'GM_sig', 'Physique', 'Paramètre gravitationnel GM', 'km³/s²', 'mesuré', 'Q'),
    ('density', 'density_sig', 'Physique', 'Masse volumique', 'g/cm³', 'mesuré', 'Q'),
    ('sats', None, 'Physique', 'Nombre de satellites connus', '', 'mesuré', 'Q'),
    ('epoch', None, 'Orbite', 'Époque des éléments (jour julien, TDB)', 'j', 'mesuré', 'Q'),
    ('equinox', None, 'Orbite', 'Repère des angles (équinoxe)', '', 'publié', 'Q'),
    ('a', 'sigma_a', 'Orbite', 'Demi-grand axe a', 'UA', 'mesuré', 'Q'),
    ('e', 'sigma_e', 'Orbite', 'Excentricité e', '', 'mesuré', 'Q'),
    ('q', 'sigma_q', 'Orbite', 'Distance au périhélie q', 'UA', 'mesuré', 'Q'),
    ('ad', 'sigma_ad', 'Orbite', 'Distance à l\'aphélie Q', 'UA', 'mesuré', 'Q'),
    ('i', 'sigma_i', 'Orbite', 'Inclinaison i (écliptique)', '°', 'mesuré', 'Q'),
    ('om', 'sigma_om', 'Orbite', 'Longitude du nœud ascendant Ω', '°', 'mesuré', 'Q'),
    ('w', 'sigma_w', 'Orbite', 'Argument du périhélie ω', '°', 'mesuré', 'Q'),
    ('ma', 'sigma_ma', 'Orbite', 'Anomalie moyenne M à l\'époque', '°', 'mesuré', 'Q'),
    ('tp', 'sigma_tp', 'Orbite', 'Date du passage au périhélie (jour julien, TDB)', 'j', 'mesuré', 'Q'),
    ('per', 'sigma_per', 'Orbite', 'Période orbitale', 'j', 'mesuré', 'Q'),
    ('moid', None, 'Orbite', 'Distance minimale à l\'orbite de la Terre (MOID)', 'UA', 'mesuré', 'Q'),
    ('moid_jup', None, 'Orbite', 'Distance minimale à l\'orbite de Jupiter (MOID)', 'UA', 'mesuré', 'Q'),
    ('t_jup', None, 'Orbite', 'Paramètre de Tisserand par rapport à Jupiter', '', 'mesuré', 'Q'),
    ('A1', 'A1_sigma', 'Orbite', 'Accélération non gravitationnelle A1 (radiale)', 'UA/j²', 'mesuré', 'Q'),
    ('A2', 'A2_sigma', 'Orbite', 'Accélération non gravitationnelle A2 (transverse)', 'UA/j²', 'mesuré', 'Q'),
    ('A3', 'A3_sigma', 'Orbite', 'Accélération non gravitationnelle A3 (normale)', 'UA/j²', 'mesuré', 'Q'),
    ('DT', 'DT_sigma', 'Orbite', 'Décalage du pic d\'activité DT', 'j', 'mesuré', 'Q'),
    ('two_body', None, 'Orbite', 'Orbite à deux corps seulement (T = oui)', '', 'publié', 'Q'),
    ('condition_code', None, 'Orbite', 'Code de qualité de l\'orbite (0 excellente … 9 très incertaine)', '', 'mesuré', 'Q'),
    ('data_arc', None, 'Orbite', 'Durée couverte par les observations', 'j', 'mesuré', 'Q'),
    ('first_obs', None, 'Orbite', 'Première observation utilisée', '', 'mesuré', 'Q'),
    ('last_obs', None, 'Orbite', 'Dernière observation utilisée', '', 'mesuré', 'Q'),
    ('n_obs_used', None, 'Orbite', 'Nombre d\'observations utilisées', '', 'mesuré', 'Q'),
    ('n_del_obs_used', None, 'Orbite', 'Mesures radar de distance utilisées', '', 'mesuré', 'Q'),
    ('n_dop_obs_used', None, 'Orbite', 'Mesures radar Doppler utilisées', '', 'mesuré', 'Q'),
    ('rms', None, 'Orbite', 'Écart quadratique moyen des résidus (normalisé)', '', 'mesuré', 'Q'),
    ('orbit_id', None, 'Orbite', 'Solution d\'orbite (identifiant JPL)', '', 'publié', 'Q'),
    ('soln_date', None, 'Orbite', 'Date de la solution d\'orbite', '', 'publié', 'Q'),
    ('producer', None, 'Orbite', 'Auteur de la solution d\'orbite', '', 'publié', 'Q'),
    ('rot_per', 'rot_per_sig', 'Rotation', 'Période de rotation', 'h', 'mesuré', 'Q'),
    ('pole', 'pole_sig', 'Rotation', 'Direction du pôle (ascension droite / déclinaison)', '°', 'mesuré', 'O'),
    ('BV', 'BV_sig', 'Lumière et couleur', 'Couleur B-V', 'mag', 'mesuré', 'Q'),
    ('UB', 'UB_sig', 'Lumière et couleur', 'Couleur U-B', 'mag', 'mesuré', 'Q'),
    ('IR', None, 'Lumière et couleur', 'Couleur I-R', 'mag', 'mesuré', 'Q'),
    ('spec_T', None, 'Lumière et couleur', 'Type spectral (Tholen)', '', 'publié', 'Q'),
    ('spec_B', None, 'Lumière et couleur', 'Type spectral (SMASS II, Bus et Binzel)', '', 'publié', 'Q'),
    ('M1', None, 'Lumière et couleur', 'Comète : magnitude totale M1', 'mag', 'mesuré', 'Q'),
    ('K1', None, 'Lumière et couleur', 'Comète : pente de la magnitude totale K1', '', 'mesuré', 'Q'),
    ('M2', None, 'Lumière et couleur', 'Comète : magnitude du noyau M2', 'mag', 'mesuré', 'Q'),
    ('K2', None, 'Lumière et couleur', 'Comète : pente de la magnitude du noyau K2', '', 'mesuré', 'Q'),
    ('PC', None, 'Lumière et couleur', 'Comète : coefficient de phase du noyau PC', 'mag/°', 'mesuré', 'Q'),
    ('disc_date', None, 'Découverte', 'Date de découverte', '', 'mesuré', 'O'),
    ('disc_loc', None, 'Découverte', 'Lieu de découverte', '', 'publié', 'O'),
    ('disc_who', None, 'Découverte', 'Découvreur(s)', '', 'publié', 'O'),
    ('disc_ref', None, 'Découverte', 'Référence de la découverte', '', 'publié', 'O'),
]
# Champs demandés à l'API de requête (les champs internes « class_fr », « *_sig », « disc_* » n'en font pas partie).
CHAMPS_Q = ['pdes', 'name'] + [c for c, s, *_, src in COLONNES if c != 'class_fr' and src == 'Q'] + \
           [s for _, s, *_ in COLONNES if s and not s.endswith('_sig')]
CHAMPS_Q = list(dict.fromkeys(CHAMPS_Q))
# Paramètres physiques de l'API objet : nom -> champ du tableau (pour l'incertitude « *_sig »).
PHYS_OBJ = {k: k for k in ('albedo', 'rot_per', 'GM', 'density', 'extent', 'BV', 'UB', 'pole')}


def label(ligne: str) -> tuple:
    """(clé, désignation, comète ?) : copie exacte de asteroides::Catalogue::label (asteroides_catalogue.h, l. 44-54)."""
    comete = len(ligne) >= 2 and ligne[-2:] == '~c'
    cut = ligne.find('~')
    nom = ligne if cut < 0 else ligne[:cut]
    ident = '' if cut < 0 else ligne[cut + 1:]
    if comete:
        ident = ident[:-2]
        return (('Comète ' + ident) if not nom else ident + '/' + nom), ident, True
    if not nom:
        return ('Astéroïde' if not ident else 'Astéroïde ' + ident), ident, False
    return (nom if not ident else nom + ' (' + ident + ')'), ident, False


def cles(dossier: str) -> tuple:
    """Désignation -> clé, séparément pour les astéroïdes et les comètes, et le nombre de lignes du catalogue."""
    ast, com, n = {}, {}, 0
    with open(os.path.join(dossier, 'asteroides_noms.txt'), encoding='utf-8') as f:
        for ligne in f:
            ligne = ligne.rstrip('\r\n')
            n += 1
            cle, ident, comete = label(ligne)
            (com if comete else ast).setdefault(ident, cle)
    return ast, com, n


def http_json(url: str, essais: int = 5):
    """Lecture JSON avec reprises espacées (le JPL limite les rafales)."""
    for k in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as ex:
            if ex.code in (400, 404):
                try:
                    return json.loads(ex.read().decode('utf-8'))
                except ValueError:
                    return None
            time.sleep(5 * (k + 1))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(5 * (k + 1))
    raise SystemExit(f'JPL injoignable : {url[:120]}')


def pages(kind: str):
    """Pages de l'API de requête (cache : une page = un fichier JSON), dans l'ordre de la base."""
    k = 0
    while True:
        chemin = os.path.join(CACHE, f'sbdb_{kind}_{k:03d}.json')
        if not os.path.exists(chemin):
            q = {'fields': ','.join(CHAMPS_Q), 'sb-kind': kind, 'full-prec': 'true', 'limit': PAGE, 'limit-from': k * PAGE}
            d = http_json(QUERY + '?' + urllib.parse.urlencode(q))
            if 'fields' not in d:
                raise SystemExit(f'réponse inattendue du JPL : {str(d)[:300]}')
            with open(chemin, 'w', encoding='utf-8') as f:
                json.dump(d, f)
            time.sleep(2)
        with open(chemin, encoding='utf-8') as f:
            d = json.load(f)
        yield d['fields'], d.get('data') or [], int(d.get('count', 0))
        if (k + 1) * PAGE >= int(d.get('count', 0)) or not d.get('data'):
            return
        k += 1


def detail(sstr: str, spk: str = '') -> dict:
    """Fiche objet du JPL (découverte, paramètres physiques), en cache ; une requête par seconde au plus.
    Comètes : demandées par identifiant SPK (« 51P » seul désigne aussi les fragments 51P-A, 51P-D : réponse multiple)."""
    dossier = os.path.join(CACHE, 'objets')
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, re.sub(r'[^A-Za-z0-9_-]', '_', sstr) + '.json')
    if not os.path.exists(chemin):
        q = {'spk': spk} if spk else {'sstr': sstr}
        d = http_json(OBJET + '?' + urllib.parse.urlencode({**q, 'discovery': '1', 'phys-par': '1'}))
        with open(chemin, 'w', encoding='utf-8') as f:
            json.dump(d or {}, f)
        time.sleep(1.0)
    with open(chemin, encoding='utf-8') as f:
        return json.load(f)


def sous_ensemble(ast: dict, com: dict) -> dict:
    """Clé -> champs « disc_* » et « *_sig » lus dans l'API objet, pour les numéros 1-1000 et les comètes « nP »."""
    spk = {}
    for champs, data, _ in pages('c'):
        i, j = champs.index('pdes'), champs.index('spkid')
        spk.update({r[i]: str(r[j]) for r in data})
    cibles = [('a:', str(n)) for n in range(1, 1001) if str(n) in ast]
    cibles += [('c:', p) for p in com if re.fullmatch(r'\d+[PD]', p)]
    extra = {}
    for k, (pre, ident) in enumerate(cibles):
        d = detail(ident, spk.get(ident, '') if pre == 'c:' else '')
        if (d.get('object') or {}).get('des') != ident:
            print(f'  API objet : {ident} rend un autre objet ou rien, ignoré', flush=True)
            continue
        if k % 100 == 0:
            print(f'  API objet : {k}/{len(cibles)}', flush=True)
        if not d or 'object' not in d:
            continue
        x = {}
        disc = d.get('discovery') or {}
        # « site » et « citation » existent dans l'API mais sont vides pour tout ce sous-ensemble (vérifié le 20/11/2026).
        for cle_api, champ in (('date', 'disc_date'), ('who', 'disc_who'), ('location', 'disc_loc'), ('ref', 'disc_ref')):
            if disc.get(cle_api):
                x[champ] = date_iso(disc[cle_api]) if champ == 'disc_date' else disc[cle_api]
        for p in d.get('phys_par') or []:
            if p.get('name') == 'pole' and p.get('value'):
                x['pole'] = p['value']
            if p.get('name') in PHYS_OBJ and p.get('sigma'):
                x[PHYS_OBJ[p['name']] + '_sig'] = (p.get('value'), p['sigma'])
        extra[pre + ident] = x
    return extra


MOIS = {m: k + 1 for k, m in enumerate(('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'))}


def date_iso(t: str) -> str:
    """« 1801-Jan-01 » (écriture du JPL) -> « 1801-01-01 » ; toute autre écriture est gardée telle quelle."""
    m = re.fullmatch(r'(\d{4})-([A-Z][a-z]{2})-(\d{2})', str(t).strip())
    return f'{m.group(1)}-{MOIS[m.group(2)]:02d}-{m.group(3)}' if m and m.group(2) in MOIS else str(t)


def propre(v) -> str:
    """Valeur de la base en texte d'une case : None/vide -> '' ; tabulations et retours à la ligne -> espace."""
    if v is None:
        return ''
    s = re.sub(r'\s+', ' ', str(v)).strip()
    # « .0797 » (écriture du JPL) -> « 0.0797 » : même nombre, écrit comme le format l'attend.
    return re.sub(r'^([-+]?)\.(?=\d)', r'\g<1>0.', s)


def egal(a, b) -> bool:
    """Même valeur dans les deux API (nombre, ou texte identique comme « 964.4 x 964.2 x 891.8 »)."""
    if propre(a) == propre(b):
        return True
    try:
        return abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(float(a)))
    except (TypeError, ValueError):
        return False


def ligne_objet(cle: str, r: dict, x: dict) -> str:
    """Une ligne du tableau : clé puis (valeur, incertitude) pour chaque colonne d'en-tête."""
    cases = [cle]
    for champ, sig, *_ in COLONNES:
        if champ == 'class_fr':
            v = CLASSES.get(r.get('class') or '', '')
        elif champ in ('neo', 'pha'):
            v = OUI_NON.get(r.get(champ) or '', '')
        elif champ.startswith('disc_') or champ == 'pole':
            v = propre(x.get(champ))
        else:
            v = propre(r.get(champ))
        u = ''
        if v and sig:
            if sig.endswith('_sig'):
                vs = x.get(sig)      # incertitude de l'API objet, gardée seulement si sa valeur est la même
                u = propre(vs[1]) if vs and egal(vs[0], v) else ''
            else:
                u = propre(r.get(sig))
        if u and not re.fullmatch(r'[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?', u):
            v, u = f'{v} (± {u})', ''      # incertitude non numérique (« 0.2 x 0.2 x 0.2 ») : gardée dans le texte
        cases += [v, u if v else '']
    return '\t'.join(cases)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dossier = args[0] if args else APPLI
    sortie = args[1] if len(args) > 1 else SORTIE
    os.makedirs(CACHE, exist_ok=True)
    jour = datetime.date.today().isoformat()
    ast, com, n_cat = cles(dossier)
    print(f'catalogue de l\'appli : {n_cat} lignes ({len(ast)} astéroïdes, {len(com)} comètes, clés uniques)')
    extra = {} if '--sans-decouverte' in sys.argv else sous_ensemble(ast, com)
    src_q, src_o = SRC.format(date=jour), SRC_OBJ.format(date=jour)
    trouves, total_base = set(), 0
    tmp = sortie + '.part'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'# fiches_petits_corps.py, {jour} : JPL Small-Body Database (API de requête en masse, pleine précision ;\n')
        f.write('# API objet pour la découverte des numéros 1 à 1000 et des comètes périodiques numérotées). Incertitudes : 1 sigma.\n')
        for champ, sig, groupe, lib, unite, statut, s in COLONNES:
            source = src_o if s == 'O' else src_q
            if sig and sig.endswith('_sig'):
                source += ' ; incertitude : API objet (numéros 1 à 1000 et comètes périodiques)'
            f.write('\t'.join(['@', groupe, lib, unite, statut, source]) + '\n')
        for kind, table, pre in (('a', ast, 'a:'), ('c', com, 'c:')):
            for champs, data, count in pages(kind):
                for row in data:
                    r = dict(zip(champs, row))
                    ident = r.get('pdes') or ''
                    cle = table.get(ident)
                    if cle is None or pre + ident in trouves:
                        continue
                    trouves.add(pre + ident)
                    f.write(ligne_objet(cle, r, extra.get(pre + ident, {})) + '\n')
                total_base += len(data)
                print(f'  base {kind} : {total_base} lus, {len(trouves)} fiches, {f.tell() / 1e6:.0f} Mo', flush=True)
                if f.tell() > TAILLE_MAX:
                    raise SystemExit('ARRÊT : la sortie dépasse 2 Go, accord de Marc nécessaire avant d\'aller plus loin')
    os.replace(tmp, sortie)
    manque_a = [k for k in ast if 'a:' + k not in trouves]
    manque_c = [k for k in com if 'c:' + k not in trouves]
    print(f'fiches : {len(trouves)} / {len(ast) + len(com)} clés du catalogue ; sans fiche : {len(manque_a)} astéroïdes, '
          f'{len(manque_c)} comètes ; taille {os.path.getsize(sortie) / 1e6:.0f} Mo -> {sortie}')
    if manque_a or manque_c:
        print('  exemples sans fiche :', (manque_a[:5] + manque_c[:5]))


if __name__ == '__main__':
    main()
