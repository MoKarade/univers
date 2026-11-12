#!/usr/bin/env python3
"""Ondes gravitationnelles détectées (GWOSC) -> ondes_gravitationnelles.tsv pour l'appli PC.

Même tri que la page (pipeline/sources/build_gw.py : catalogues officiels « confident » de LVK, le plus récent par
événement, p_astro >= 0,5), même fichier source déjà sur le PC (univers-raw/gwosc_allevents.json). Demande de Marc
(12/11/2026) : toutes les données récupérées dans l'appli.
Colonnes : nom, date UTC, catalogue, puis valeur;basse;haute (vide si absente) pour masse 1, masse 2, masse finale
(masses solaires, référentiel de la source), distance de luminosité (Mpc), décalage vers le rouge ; puis p_astro.
Usage : python ondes_gravitationnelles.py <dossier univers-raw> <dossier de sortie>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sources'))
from build_gw import record, select      # noqa: E402


def trio(t: list | None) -> str:
    return '' if not t else ';'.join('' if x is None else f'{x:.6g}' for x in t)


def main() -> None:
    raw, sortie = sys.argv[1], sys.argv[2]
    events = json.load(open(os.path.join(raw, 'gwosc_allevents.json'), encoding='utf-8'))['events']
    sel = [record(e) for e in select(events)]
    with open(os.path.join(sortie, 'ondes_gravitationnelles.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        for r in sel:
            f.write('\t'.join([r['n'], r['t'], r['cat'], trio(r['m1']), trio(r['m2']), trio(r['mf']), trio(r['dl']),
                               trio(r['z']), '' if r['pa'] is None else f'{r["pa"]:.3g}']) + '\n')
    print(f'{len(sel)} événements écrits')


if __name__ == '__main__':
    main()
