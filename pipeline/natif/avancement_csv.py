#!/usr/bin/env python3
"""Fichiers d'avancement de l'appli PC (C:\\dev\\Univers-PC\\avancement\\*.txt) -> un CSV pour la page d'avancement des calculs
(tableau de bord claude.ai). Valeurs recopiées telles quelles ; le pourcentage et le temps restant sont calculés sur la page.
Usage : python avancement_csv.py <sortie.csv>
"""
import csv, glob, os, sys

DOSSIER = r'C:\dev\Univers-PC\avancement'
CHAMPS = ['tache', 'nom', 'fait', 'total', 'unite', 'debut', 'maj', 'etat', 'detail']


def main():
    lignes = []
    for f in sorted(glob.glob(os.path.join(DOSSIER, '*.txt'))):
        v = {}
        for l in open(f, encoding='utf-8').read().splitlines():
            if '=' in l:
                k, x = l.split('=', 1); v[k.strip()] = x.strip()
        v['tache'] = os.path.splitext(os.path.basename(f))[0]
        lignes.append({k: v.get(k, '') for k in CHAMPS})
    with open(sys.argv[1], 'w', encoding='utf-8', newline='') as o:
        w = csv.DictWriter(o, CHAMPS); w.writeheader(); w.writerows(lignes)
    print(len(lignes), 'tâches')


if __name__ == '__main__':
    main()
