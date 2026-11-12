#!/usr/bin/env python3
"""Éclat et teinte de chaque étoile du calcul de la fusion -> particules.bin, lu par l'appli PC (fusion_nuage.h).

But (décision de Marc, 12 novembre 2026 : « que toutes les données se marient, avec les vraies équations ») : mettre
les points du calcul sur la même échelle de lumière que les étoiles mesurées. Chaque point représente une masse d'étoiles
(composantes.json, « masse_par_particule_Msol », valeurs du modèle du calcul). Sa lumière vaut cette masse divisée par
le rapport masse/lumière de sa galaxie, et sa magnitude absolue :
    M = M_soleil − 2,5 log10( masse / (rapport masse/lumière) )        (lumière en luminosités solaires, même bande)
L'appli applique ensuite la même loi en 1/d² et la même exposition qu'aux étoiles mesurées.

Rien n'est inventé : le rapport masse/lumière et l'indice de couleur B−V de chaque galaxie sont lus dans composantes.json
(clés numériques « masse_lumiere » : {galaxie: valeur}, « magnitude_soleil » : valeur de la même bande,
« bv » : {galaxie: valeur}, avec leurs sources en texte à côté). Tant que le fil physique ne les a pas fournies, le
fichier est écrit avec « physique = 0 » (l'appli garde un éclat d'affichage fixe et le dit) et sans teinte (blanc).
Les étoiles sont rangées par galaxie (fusion.json, « affichees » : MW, M31, M33, LMC) ; composantes.bin dit disque (1)
ou bulbe (2).

Format : « UNIVFPT1 », n (u32), physique (u32, 0 ou 1), zéros jusqu'à 64 octets ; magnitude absolue n × f32 ;
B−V n × f32 (NaN : pas de couleur sourcée).
Usage : python fusion_particules.py <dossier du calcul>
"""
import json
import os
import sys

import numpy as np

GALAXIES = ['MW', 'M31', 'M33', 'LMC']
COMPOSANTE = {1: 'disque', 2: 'bulbe'}


def main() -> None:
    d = sys.argv[1]
    with open(os.path.join(d, 'fusion.json'), encoding='utf-8') as f:
        counts = json.load(f)['affichees']
    n = int(sum(counts))
    comp_path = os.path.join(d, 'composantes.bin')
    comp = np.fromfile(comp_path, 'i1') if os.path.exists(comp_path) else np.ones(n, 'i1')
    meta = {}
    if os.path.exists(os.path.join(d, 'composantes.json')):
        with open(os.path.join(d, 'composantes.json'), encoding='utf-8') as f:
            meta = json.load(f)
    masses = meta.get('masse_par_particule_Msol', {})
    ml = meta.get('masse_lumiere', {})
    bv_gal = meta.get('bv', {})
    sun = meta.get('magnitude_soleil')
    mag = np.zeros(n, '<f4')
    bv = np.full(n, np.nan, '<f4')
    physique = int(bool(masses) and sun is not None and all(g in ml for g in GALAXIES))
    start = 0
    for g, c in zip(GALAXIES, counts):
        sl = slice(start, start + int(c))
        start += int(c)
        if g in bv_gal:
            bv[sl] = float(bv_gal[g])
        if physique:
            m = np.array([masses[g].get(COMPOSANTE.get(int(k), 'disque'), masses[g]['disque']) for k in (1, 2)])
            mass = np.where(comp[sl] == 2, m[1], m[0])
            mag[sl] = float(sun) - 2.5 * np.log10(mass / float(ml[g]))
    with open(os.path.join(d, 'particules.bin'), 'wb') as f:
        head = b'UNIVFPT1' + np.array([n, physique], '<u4').tobytes()
        f.write(head + b'\0' * (64 - len(head)))
        f.write(mag.tobytes())
        f.write(bv.tobytes())
    print(f'{n} étoiles ; éclat physique : {"oui" if physique else "non (rapport masse/lumière ou magnitude du Soleil absents de composantes.json)"} ; '
          f'couleur sourcée pour {int(np.isfinite(bv).sum())} étoiles')


if __name__ == '__main__':
    main()
