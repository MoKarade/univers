#!/usr/bin/env python3
"""Galaxies naines nommées de l'appli PC qui n'ont ni forme mesurée ni photo : leurs paramètres de structure MESURÉS.

Pourquoi (Marc, 20/11/2026) : « parfois je clique sur une galaxie mais je zoome et je vois rien ». Vérifié par captures :
Segue I, NGC 185, Leo A… n'avaient aucun point à l'écran (trop faibles pour les relevés, pas dans SGA-2020).

Source : Local Volume Database, Pace (2024, arXiv:2411.07424 ; github.com/apace7/local_volume_database), fichier
pipeline/raw/dwarf_all.csv du dépôt : rayon de demi-lumière (minutes d'arc), ellipticité, angle de position (degrés, du
nord vers l'est), module de distance, magnitude V apparente, chacun avec sa référence d'origine (colonnes ref_*).

Sortie : naines.tsv, une ligne par galaxie de l'appli trouvée : nom de l'appli, rayon de demi-lumière (années-lumière),
ellipticité, angle de position (degrés), magnitude absolue V, références (structure ; distance ; magnitude).
Les galaxies déjà dessinées par leur forme mesurée (galaxies_formes_noms.tsv) sont écartées.
L'appli (natif/src/galaxies_naines.h) en tire un nuage d'étoiles : profil de Plummer de rayon de demi-lumière mesuré,
aplati selon l'ellipticité et l'angle mesurés ; épaisseur le long de la ligne de visée = petit axe [supposé].

Usage : python naines.py <dwarf_all.csv> <galaxies_noms.tsv> <galaxies_formes_noms.tsv> <sortie naines.tsv>
"""
import csv
import math
import re
import sys
import unicodedata

ROMAIN = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10}
# Noms français de l'appli (pipeline/build_data2.py, table FR) -> nom anglais de la base.
FRANCAIS = {
    'naine du sagittaire': 'sagittarius', 'naine du dragon': 'draco', 'naine de la petite ourse': 'ursa minor',
    'naine du sculpteur': 'sculptor', 'naine du sextant': 'sextans', 'naine de la carene': 'carina',
    'naine du fourneau': 'fornax', 'naine du phenix': 'phoenix', 'm110': 'ngc 205', 'm32': 'm32',
    'wlm (wolf-lundmark-melotte)': 'wlm', 'lgs 3 (local group suspect 3)': 'lgs 3', 'pegasus dirr': 'pegasus dirr',
    'sagittarius dirr': 'sagittarius dirr', 'canis major': 'canis major',
}


def cle(nom: str) -> str:
    s = unicodedata.normalize('NFKD', nom).encode('ascii', 'ignore').decode().lower().strip()
    s = FRANCAIS.get(s, s)
    s = s.replace('(', ' ').replace(')', ' ')
    mots = [str(ROMAIN.get(m, m)) for m in re.split(r'[\s_\-]+', s) if m]
    if mots and mots[-1] == '1' and len(mots) > 1 and mots[0] in ('segue', 'bootes', 'ursa', 'canes', 'sextans'):
        mots = mots[:-1]      # « Segue (I) » = « Segue 1 » = « Segue » dans certaines bases
    return ' '.join(mots)


def nombre(v: str):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def main() -> None:
    base, noms, formes, sortie = sys.argv[1:5]
    lignes = list(csv.DictReader(open(base, encoding='utf-8')))
    index = {}
    for r in lignes:
        k = cle(r['name'])
        index.setdefault(k, r)
        if k.endswith(' 1'):
            index.setdefault(k[:-2], r)
    deja = {l.split('\t')[0] for l in open(formes, encoding='utf-8') if l.strip()}
    gardees, manquees = 0, []
    with open(sortie, 'w', encoding='utf-8', newline='') as out:
        out.write('# nom\trayon_demi_lumiere_al\tellipticite\tangle_position_deg\tmagnitude_absolue_V\tref_structure\tref_distance\tref_magnitude\n')
        for l in open(noms, encoding='utf-8'):
            nom = l.split('\t')[0].strip()
            if not nom or nom in deja or nom in ('Grand Nuage de Magellan', 'Petit Nuage de Magellan', 'Andromède (M31)', 'Galaxie du Triangle (M33)'):
                continue
            r = index.get(cle(nom))
            if r is None:
                manquees.append(nom)
                continue
            rh, dm, mv = nombre(r['rhalf']), nombre(r['distance_modulus']), nombre(r['apparent_magnitude_v'])
            if rh is None or dm is None or mv is None:
                manquees.append(nom + ' (valeurs manquantes)')
                continue
            dist_pc = 10 ** (dm / 5 + 1)
            rh_al = dist_pc * math.radians(rh / 60.0) * 3.2615638
            e = nombre(r['ellipticity']) or 0.0
            pa = nombre(r['position_angle']) or 0.0
            out.write(f"{nom}\t{rh_al:.1f}\t{e:.3f}\t{pa:.1f}\t{mv - dm:.2f}\t{r['ref_structure']}\t{r['ref_distance']}\t{r['ref_m_v']}\n")
            gardees += 1
    print(f'{gardees} galaxies écrites ; sans correspondance ou sans valeur : {len(manquees)}')
    for m in manquees:
        print('   ', m)


if __name__ == '__main__':
    main()
