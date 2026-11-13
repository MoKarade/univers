#!/usr/bin/env python3
"""Lecture de la table unique (pipeline/constantes/univers.json, générée par construire.py).

    import sys; sys.path.insert(0, 'pipeline/constantes'); import constantes as C
    t = C.charger()
    t['repere']['R0'], C.galaxie('andromede')['aujourdhui']['position'], C.K_lambda()
"""
import json
import os

FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'univers.json')
_cache = None


def charger():
    global _cache
    if _cache is None:
        with open(FICHIER, encoding='utf-8') as fh:
            _cache = json.load(fh)
    return _cache


def galaxie(cle):
    return charger()['galaxies'][cle]


def ordre():
    return list(charger()['ordre'])


def K_lambda():
    """Constante de l'énergie noire dans le Groupe local : a = K (x − x_cm), en (km/s)²/kpc²."""
    return charger()['cosmologie']['K_lambda']


def modele_pour_modeles_v2(cle):
    """Bloc « modele » au format du dictionnaire GALAXIES de pipeline/fusion/modeles_v2.py (sans les sources)."""
    m = json.loads(json.dumps(galaxie(cle)['modele']))
    m.pop('src', None); m.pop('barre', None)
    return m
