#!/usr/bin/env python3
"""Ondes gravitationnelles détectées -> app/gen/data15.js (clé DATA.GW).

Source : GWOSC, Gravitational-Wave Open Science Center (LIGO, Virgo, KAGRA),
https://gwosc.org/eventapi/json/allevents/ (téléchargé dans RAW/gwosc_allevents.json).

Règles de tri (pas d'invention) :
- seuls les catalogues cumulatifs officiels de la collaboration LVK, version « confident » :
  GWTC-1-confident, GWTC-2.1-confident, GWTC-3-confident, GWTC-4.0, GWTC-4.1, GWTC-5.0 ;
- pour un même événement présent dans plusieurs catalogues, on garde le catalogue le plus récent ;
- un événement dont la probabilité d'origine astrophysique (p_astro) publiée est < 0,5 est écarté ;
- une valeur absente du catalogue reste absente (null) : jamais remplacée.

Usage : python pipeline/sources/build_gw.py <dossier_raw>
"""
import datetime
import json
import os
import sys

CATALOGUES = ['GWTC-1-confident', 'GWTC-2.1-confident', 'GWTC-3-confident', 'GWTC-4.0', 'GWTC-4.1', 'GWTC-5.0']
P_ASTRO_MIN = 0.5
GPS_EPOCH = datetime.datetime(1980, 1, 6, tzinfo=datetime.timezone.utc)
# Secondes intercalaires GPS - UTC (IERS) : 17 s du 1er juillet 2015 au 31 décembre 2016, 18 s ensuite.
LEAP_2017_GPS = 1167264018


def gps_to_iso(gps):
    """Temps GPS -> date UTC ISO, à la seconde."""
    leap = 18 if gps >= LEAP_2017_GPS else 17
    t = GPS_EPOCH + datetime.timedelta(seconds=gps - leap)
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')


def triplet(e, key):
    """[valeur, borne basse, borne haute] telle que publiée, ou None si la valeur manque."""
    v = e.get(key)
    if v is None:
        return None
    lo, hi = e.get(key + '_lower'), e.get(key + '_upper')
    # Arrondi à 6 chiffres significatifs : efface le bruit de l'addition flottante, pas la précision publiée.
    rnd = lambda x: None if x is None else float('%.6g' % x)
    return [v, rnd(None if lo is None else v + lo), rnd(None if hi is None else v + hi)]


def select(events):
    """Un enregistrement par événement : le catalogue officiel le plus récent."""
    best = {}
    for e in events.values():
        cat = e.get('catalog.shortName')
        if cat not in CATALOGUES:
            continue
        name = e['commonName']
        rank = (CATALOGUES.index(cat), e.get('version', 0))
        if name not in best or rank > best[name][0]:
            best[name] = (rank, e)
    out = []
    for name, (_, e) in best.items():
        p = e.get('p_astro')
        if p is not None and p < P_ASTRO_MIN:
            continue
        out.append(e)
    return sorted(out, key=lambda e: e['GPS'])


def record(e):
    return {
        'n': e['commonName'],
        't': gps_to_iso(e['GPS']),
        'cat': e['catalog.shortName'],
        'm1': triplet(e, 'mass_1_source'),          # masse solaire, référentiel de la source
        'm2': triplet(e, 'mass_2_source'),
        'mf': triplet(e, 'final_mass_source'),
        'dl': triplet(e, 'luminosity_distance'),    # Mpc, distance de luminosité
        'z': triplet(e, 'redshift'),
        'pa': e.get('p_astro'),
        'far': e.get('far'),                        # fausses alertes par an
        'url': e.get('jsonurl'),
    }


def main(raw):
    events = json.load(open(os.path.join(raw, 'gwosc_allevents.json'), encoding='utf-8'))['events']
    sel = [record(e) for e in select(events)]
    with_d = sum(1 for r in sel if r['dl'])
    with_m = sum(1 for r in sel if r['m1'])
    print('GWOSC : %d enregistrements lus, %d événements gardés, %d avec distance, %d avec masses'
          % (len(events), len(sel), with_d, with_m))
    for cat in CATALOGUES:
        print('  %-20s %d' % (cat, sum(1 for r in sel if r['cat'] == cat)))
    payload = {'GW': sel, 'GW_SRC': 'GWOSC, catalogues GWTC (LIGO, Virgo, KAGRA), https://gwosc.org'}
    out = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'gen', 'data15.js')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('Object.assign(DATA, ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ');\n')
    print('écrit', os.path.normpath(out), os.path.getsize(out), 'octets')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'univers-raw'))
