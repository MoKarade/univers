#!/usr/bin/env python3
"""Vieillissement de la lumière des populations (pipeline/etoiles/vieillissement_populations.json, PR 97,
docs/vieillissement-lumiere.md) -> vieillissement.tsv, lu par l'appli PC (natif/src/vieillissement.h).

Régime « naissance_continue » (recommandé par la doc : les composantes qui forment des étoiles aujourd'hui continuent).
Une ligne par date t_ga (-3 à +10 Ga, pas de 50 Ma) : t_ga, puis pour les composantes 1, 2, 4, 5, 6 le facteur de lumière,
puis pour les mêmes le facteur de température. Modèle : MIST v1.2, Kroupa 2001, histoires de formation supposées, naines
blanches non comptées.
Usage : python vieillissement_tsv.py <vieillissement_populations.json> <vieillissement.tsv>
"""
import json, sys

d = json.load(open(sys.argv[1], encoding='utf-8'))
comps = ['1', '2', '4', '5', '6']
c = d['composantes']
with open(sys.argv[2], 'w', encoding='utf-8', newline='\n') as f:
    f.write('t_ga\t' + '\t'.join(f'lum{k}' for k in comps) + '\t' + '\t'.join(f'teff{k}' for k in comps) + '\n')
    for i, t in enumerate(d['t_ga']):
        f.write(f'{t:.4f}\t' + '\t'.join(f"{c[k]['naissance_continue']['lum'][i]:.6f}" for k in comps) + '\t'
                + '\t'.join(f"{c[k]['naissance_continue']['teff'][i]:.6f}" for k in comps) + '\n')
print(f"{len(d['t_ga'])} dates -> {sys.argv[2]}")
