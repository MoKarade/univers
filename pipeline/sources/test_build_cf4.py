#!/usr/bin/env python3
"""Tests de l'association Cosmicflows-4 <-> galaxies de la page (build_cf4.py).

Couples connus (numéros PGC de HyperLEDA) : Andromède M31 = PGC 2557, Triangle M33 = PGC 5818, NGC 4258 = PGC 39600.
Refus attendu : NGC 3274 (8 Mpc), dont le voisin sur le ciel dans CF4 est une galaxie d'arrière-plan à 458 Mpc (PGC 213714).
Besoin de la table complète téléchargée par build_cf4.py (<raw>/cf4_complet.json).
Lancer : python pipeline/sources/test_build_cf4.py [dossier_raw]
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_cf4 as b  # noqa: E402


def main(raw):
    bad = 0

    def check(ok, msg):
        nonlocal bad
        print(('OK    ' if ok else 'ÉCHEC ') + msg)
        bad += 0 if ok else 1

    gal = json.load(open(os.path.join(raw, 'cf4_complet.json'), encoding='utf-8'))
    check(len(gal) == b.NB_ATTENDU, 'table complète : %d galaxies' % len(gal))
    near, dnear, local, dlocal = b.galaxies_de_la_page()
    racine = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'gen')
    lire = lambda f: json.loads(open(os.path.join(racine, f), encoding='utf-8').read()[len('Object.assign(DATA, '):-3])
    noms_near = lire('data3.js')['NEAR_NAMES'].split('|')
    noms_local = [o['n'] for o in lire('data2.js')['LOCAL']]
    an, _ = b.coherent(gal, b.associer(near, gal), dnear)
    al, _ = b.coherent(gal, b.associer(local, gal), dlocal)
    pgc = lambda k: None if k is None else gal[k][0]
    for nom, attendu in (('Andromède (M31)', 2557), ('Galaxie du Triangle (M33)', 5818)):
        got = pgc(al[noms_local.index(nom)])
        check(got == attendu, '%s -> PGC %s (attendu %d)' % (nom, got, attendu))
    got = pgc(an[noms_near.index('NGC4258')])
    check(got == 39600, 'NGC 4258 -> PGC %s (attendu 39600)' % got)
    brut = b.associer([near[noms_near.index('NGC3274')]], gal)[0]
    garde = an[noms_near.index('NGC3274')]
    check(pgc(brut) == 213714 and garde is None, 'NGC 3274 : voisin d’arrière-plan PGC %s écarté (%s)' % (pgc(brut), garde))
    for lab, lst in (('galaxies proches', an), ('Groupe local', al)):
        dbl = [k for k, v in collections.Counter(pgc(k) for k in lst if k is not None).items() if v > 1]
        check(not dbl, '%s : aucun PGC associé deux fois %s' % (lab, dbl or ''))
    print('RÉSULTAT :', 'PASSE' if bad == 0 else '%d échec(s)' % bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'univers-raw'))
