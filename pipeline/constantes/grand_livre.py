#!/usr/bin/env python3
"""Grand livre des constantes et des masses (étape 0 du plan B+) : compare la table unique à ce que lisent aujourd'hui
l'appli et les calculs, et écrit docs/grand-livre-masses.md.

Ne modifie rien : il relit les fichiers et signale chaque écart. Une ligne « écart » est une valeur qu'un fil devra
remplacer par la lecture de la table (pipeline/constantes/univers.json ou natif/physique/constantes_univers.h).

Usage : python pipeline/constantes/grand_livre.py
"""
import json
import math
import os
import re
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(os.path.dirname(ICI))
sys.path.insert(0, ICI)
import constantes as C      # noqa: E402

SORTIE = os.path.join(RACINE, 'docs', 'grand-livre-masses.md')


def lire(chemin):
    with open(os.path.join(RACINE, chemin), encoding='utf-8') as fh:
        return fh.read()


def cherche(chemin, motif, groupe=1, conv=float):
    m = re.search(motif, lire(chemin))
    return conv(m.group(groupe)) if m else None


def relatif(a, b):
    return abs(a - b) / abs(b) if b else float('inf')


def main():
    t = C.charger()
    rep, gal = t['repere'], t['galaxies']
    lignes = []      # (grandeur, table, autre source, valeur, chemin, tolérance relative)

    def ajoute(grandeur, ref, source, val, chemin, tol=0.005, unite=''):
        if val is None:
            lignes.append((grandeur, ref, source, 'introuvable', chemin, 'à vérifier', unite)); return
        ok = relatif(val, ref) <= tol
        lignes.append((grandeur, ref, source, val, chemin, 'conforme' if ok else 'ÉCART', unite))

    # --- repère
    gh = 'natif/physique/galaxie_orbites.h'
    ajoute('R0', rep['R0'], 'appli (kR0)', cherche(gh, r'kR0 = ([\d.]+)'), gh, unite='kpc')
    ajoute('R0', rep['R0'], 'ensemble Sawala (astropy « v4.0 »)', 8.122, 'pipeline/fusion/groupe_local_clones.py', unite='kpc')
    ajoute('R0', rep['R0'], 'ancien modèle de fusion', cherche('pipeline/fusion/modeles.py', r'V0, R0.*= [\d.]+, ([\d.]+)'), 'pipeline/fusion/modeles.py', unite='kpc')
    ajoute('R0', rep['R0'], 'étoiles clones', cherche('pipeline/natif/clones_etoiles.py', r'R0 = ([\d.]+)'), 'pipeline/natif/clones_etoiles.py', unite='kpc')
    ajoute('v0 (vitesse circulaire au Soleil)', rep['v0'], 'appli (kV0)', cherche(gh, r'kV0 = ([\d.]+)'), gh, unite='km/s')
    ajoute('v0 (vitesse circulaire au Soleil)', rep['v0'], 'ancien modèle de fusion', cherche('pipeline/fusion/modeles.py', r'V0, R0.*= ([\d.]+),'), 'pipeline/fusion/modeles.py', unite='km/s')
    ajoute('vitesse du Soleil, composante y', rep['soleil_vitesse'][1], 'appli (kSunUvw)', cherche(gh, r'kSunUvw\[3\] = \{[\d.]+, ([\d.]+)'), gh, unite='km/s')
    ajoute('vitesse du Soleil, composante y', rep['soleil_vitesse'][1], 'ensemble Sawala (astropy « v4.0 »)', 245.6, 'pipeline/fusion/groupe_local_clones.py', unite='km/s')
    # --- cosmologie
    cos = t['cosmologie']
    ajoute('H0', cos['H0'], 'appli (cosmologie.h)', cherche('natif/src/cosmologie.h', r'h0 = ([\d.]+)'), 'natif/src/cosmologie.h', unite='km/s/Mpc')
    ajoute('H0', cos['H0'], 'ensemble Sawala (densité critique)', 67.66, 'pipeline/fusion/groupe_local_clones.py', unite='km/s/Mpc')
    ajoute('Ω_Λ', cos['omega_lambda'], 'appli (cosmologie.h)', cherche('natif/src/cosmologie.h', r'ode = ([\d.]+)'), 'natif/src/cosmologie.h')

    # --- distances d'aujourd'hui (depuis le Soleil)
    cond = json.loads(lire('pipeline/fusion/conditions.json'))
    soleil = np.array([-8.2, 0, 0])
    d_ancien = {'andromede': np.linalg.norm(np.array(cond['m31']['pos']) - soleil),
                'triangle': np.linalg.norm(np.array(cond['dwarfs'][0]['pos']) - soleil),
                'grand_nuage': np.linalg.norm(np.array(cond['lmc']['pos']) - soleil)}
    for k, d in d_ancien.items():
        ajoute(f'distance de {gal[k]["nom"]}', gal[k]['aujourdhui']['distance_soleil'], 'ancien calcul (conditions.json)', round(float(d), 1),
               'pipeline/fusion/conditions.json', tol=0.01, unite='kpc')
    # vitesses d'ensemble (écart en km/s, tolérance 5 km/s)
    vit_ancien = {'andromede': cond['m31']['vel'], 'triangle': cond['dwarfs'][0]['vel'], 'grand_nuage': cond['lmc']['vel']}
    ecarts_vit = []
    for k, v in vit_ancien.items():
        dv = float(np.linalg.norm(np.array(v) - np.array(gal[k]['aujourdhui']['vitesse'])))
        ecarts_vit.append((gal[k]['nom'], gal[k]['aujourdhui']['vitesse'], v, round(dv, 1), 'conforme' if dv <= 5 else 'ÉCART'))

    # --- masses
    masses = [
        ('voie_lactee', 'ensemble Sawala 2025 (M200)', 1.0e12, 'pipeline/fusion/groupe_local_clones.py'),
        ('voie_lactee', 'ancien modèle de fusion (halo coupé à 220 kpc)', 1.06e12, 'docs/fusion-methode.md § 2'),
        ('andromede', 'ensemble Sawala 2025 (M200)', 1.3e12, 'pipeline/fusion/groupe_local_clones.py'),
        ('andromede', 'ancien calcul de fusion', 1.59e12, 'docs/analyse-architecture.md § 2.2'),
        ('triangle', 'ensemble Sawala 2025 (M200)', 3.0e11, 'pipeline/fusion/groupe_local_clones.py'),
        ('triangle', 'ancien modèle (Plummer)', 2.5e11, 'docs/fusion-methode.md § 2'),
        ('grand_nuage', 'ensemble Sawala 2025 (M200)', 1.5e11, 'pipeline/fusion/groupe_local_clones.py'),
        ('grand_nuage', 'ancien modèle (Hernquist de la page)', 1.8e11, 'docs/fusion-methode.md § 2'),
        ('grand_nuage', 'publié (Erkal et al. 2019)', 1.38e11, 'table_source.py'),
    ]
    lignes_m = []
    for k, src, val, chemin in masses:
        ref, sig = gal[k]['loi_masse']['centre'], gal[k]['loi_masse']['sigma']
        n_sig = abs(val - ref) / sig
        lignes_m.append((gal[k]['nom'], ref, sig, src, val, chemin, round(n_sig, 2), 'conforme' if n_sig <= 0.25 else 'ÉCART'))

    fmt = lambda x: x if isinstance(x, str) else ('%.4g' % x)
    out = ['# Grand livre des constantes et des masses (généré)', '',
           'Généré par `pipeline/constantes/grand_livre.py` le ' + t['date'] + ' depuis la table unique (`pipeline/constantes/univers.json`). '
           'Ne pas éditer : relancer le script. Une ligne « ÉCART » est une valeur qu’un fil doit remplacer par la lecture de la table.', '',
           '## 1. Repère et cosmologie', '', '| Grandeur | Table | Source comparée | Valeur | Fichier | Verdict |', '|---|---|---|---|---|---|']
    for g, ref, src, val, ch, verdict, unite in lignes:
        if g.startswith('distance'): continue
        out.append(f'| {g} ({unite}) | {fmt(ref)} | {src} | {fmt(val)} | `{ch}` | {verdict} |' if unite else f'| {g} | {fmt(ref)} | {src} | {fmt(val)} | `{ch}` | {verdict} |')
    out += ['', '## 2. Galaxies aujourd’hui', '', '| Grandeur | Table | Source comparée | Valeur | Fichier | Verdict |', '|---|---|---|---|---|---|']
    for g, ref, src, val, ch, verdict, unite in lignes:
        if g.startswith('distance'):
            out.append(f'| {g} ({unite}) | {fmt(ref)} | {src} | {fmt(val)} | `{ch}` | {verdict} |')
    out += ['', 'Vitesses d’ensemble (repère phys::galaxie, km/s ; tolérance 5 km/s) :', '', '| Galaxie | Table | Ancien calcul (conditions.json) | Écart | Verdict |', '|---|---|---|---|---|']
    for nom, a, b, dv, v in ecarts_vit:
        out.append(f'| {nom} | {a} | {b} | {dv} | {v} |')
    out += ['', '## 3. Masses totales', '',
            'Table : centre et largeur de la loi de masse de l’ensemble Monte-Carlo, égal à la masse totale du modèle du calcul N-corps quand il existe '
            '(le film est donc un tirage de l’ensemble). « Écart en σ » : distance à ce centre en largeurs de la loi.', '',
            '| Galaxie | Table (M☉) | σ | Source comparée | Valeur | Fichier | Écart en σ | Verdict |', '|---|---|---|---|---|---|---|---|']
    for nom, ref, sig, src, val, ch, ns, v in lignes_m:
        out.append(f'| {nom} | {fmt(ref)} | {fmt(sig)} | {src} | {fmt(val)} | `{ch}` | {ns} | {v} |')
    mm = {k: gal[k].get('masses_modele') for k in t['ordre']}
    out += ['', '## 4. Composition des modèles (calculé)', '', '| Galaxie | Composante | Masse (M☉) |', '|---|---|---|']
    for k in t['ordre']:
        if not mm[k]: continue
        for comp, v in mm[k].items():
            if comp == 'statut': continue
            out.append(f'| {gal[k]["nom"]} | {comp} | {fmt(v)} |')
    lmc = mm['grand_nuage']
    out += ['', '## 5. Points à trancher signalés par ce livre', '',
            '- **Grand Nuage** : `modeles_v2.py` (branche modeles-depart) pose un Hernquist de 1,38 × 10¹¹ M☉ et 16,1 kpc, puis le coupe à 100 kpc : '
            'il ne garde que 0,97 × 10¹¹ M☉, 30 % sous la mesure (Erkal 2019). La table corrige : 2,29 × 10¹¹ et 25,8 kpc avant coupure, soit '
            f'{lmc["halo"]:.3g} M☉ de halo après coupure et 1,7 × 10¹⁰ M☉ dans 8,7 kpc. Le fil des galaxies de départ doit refaire le tir de stabilité du Grand Nuage (~10 min).',
            '- **v0** : l’appli tourne avec 230 km/s, la table et le modèle de McMillan avec 232,8. Brancher `constantes_univers.h` dans '
            '`galaxie_orbites.h` change toutes les orbites d’étoiles de ~1 % : c’est un changement visible, à faire par le fil qui possède ce fichier.',
            '- **Distance d’Andromède** : 761 kpc (table) contre 783 kpc (ancien calcul). La table suit Li et al. 2021 (Céphéides), comme Sawala 2025.',
            '- **Triangle** : 859 kpc (table, Sawala 2025) contre 809 (ancien calcul) et 840 (Corbelli 2014, utilisé par le modèle de masse).',
            '- **Petit Nuage** : masse adoptée (3 ± 1 × 10⁹ M☉), pas mesurée. À relire : une masse dynamique publiée.', '']
    with open(SORTIE, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(out))
    n_ecart = sum(1 for l in lignes if l[5] == 'ÉCART') + sum(1 for l in lignes_m if l[7] == 'ÉCART') + sum(1 for l in ecarts_vit if l[4] == 'ÉCART')
    print(f'{SORTIE} : {n_ecart} écarts')


if __name__ == '__main__':
    main()
