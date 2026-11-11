#!/usr/bin/env python3
"""Tests du tri et des dates de build_gw.py, sans réseau.

Heures de référence publiées : GW150914 le 14/09/2015 à 09:50:45 UTC (Abbott et al. 2016, PRL 116, 061102),
GW170817 le 17/08/2017 à 12:41:04 UTC (Abbott et al. 2017, PRL 119, 161101).
Lancer : python pipeline/sources/test_build_gw.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_gw  # noqa: E402


def ev(name, cat, version=1, gps=1e9, pa=None, m1=None):
    return {'commonName': name, 'catalog.shortName': cat, 'version': version, 'GPS': gps, 'p_astro': pa,
            'mass_1_source': m1, 'jsonurl': ''}


def main():
    bad = 0

    def check(ok, msg):
        nonlocal bad
        print(('OK    ' if ok else 'ÉCHEC ') + msg)
        bad += 0 if ok else 1

    # Temps GPS publiés des deux événements (GWOSC) -> heure UTC à la seconde, avec 17 puis 18 secondes intercalaires.
    check(build_gw.gps_to_iso(1126259462.4) == '2015-09-14T09:50:45Z', 'GW150914 : ' + build_gw.gps_to_iso(1126259462.4))
    check(build_gw.gps_to_iso(1187008882.4) == '2017-08-17T12:41:04Z', 'GW170817 : ' + build_gw.gps_to_iso(1187008882.4))

    events = {
        'a1': ev('GWA', 'GWTC-2.1-confident', 2, m1=30.0),
        'a2': ev('GWA', 'GWTC-3-confident', 1, m1=31.0),          # plus récent : gardé
        'b1': ev('GWB', 'GWTC-4.0', 1, pa=0.9),
        'b2': ev('GWB', 'GWTC-4.1', 1, pa=0.4),                   # plus récent mais p_astro < 0,5 : écarté
        'c1': ev('GWC', 'IAS-O3a', 1, pa=0.99),                   # catalogue hors LVK : écarté
        'd1': ev('GWD', 'GWTC-1-marginal', 1),                    # marginal : écarté
    }
    sel = build_gw.select(events)
    noms = [(e['commonName'], e['catalog.shortName']) for e in sel]
    check(noms == [('GWA', 'GWTC-3-confident')], 'tri : %s' % noms)
    r = build_gw.record(dict(ev('GWE', 'GWTC-5.0'), mass_1_source=10.0, mass_1_source_lower=-1.2, mass_1_source_upper=2.1))
    check(r['m1'] == [10.0, 8.8, 12.1] and r['m2'] is None, 'intervalles : %s, masse absente laissée vide' % r['m1'])
    print('RÉSULTAT :', 'PASSE' if bad == 0 else '%d échec(s)' % bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
