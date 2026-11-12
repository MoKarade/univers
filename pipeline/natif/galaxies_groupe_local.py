#!/usr/bin/env python3
"""Ajoute à galaxies_noms.tsv les galaxies du Groupe local qui manquaient à l'appli PC.

Source : Local Volume Database (Pace 2024, github.com/apace7/local_volume_database, comb_all.csv) : galaxies
confirmées à moins de 1 Mpc. Pour chacune : direction (ra, dec) et module de distance MESURÉS -> position en
années-lumière, repère écliptique J2000 centré sur le Soleil. Les galaxies déjà présentes dans l'appli (même recoupement
que completude_groupe_local.py) ne sont pas ajoutées ; relancer le script n'ajoute rien deux fois.
Usage : python galaxies_groupe_local.py <galaxies_noms.tsv> [comb_all.csv]
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from completude_groupe_local import lvdb, nos_galaxies, separation, SEUIL_FIN, SEUIL_DEG, MPC_LY, EPS      # noqa: E402


def main() -> None:
    tsv = sys.argv[1]
    ref, version = lvdb(sys.argv[2] if len(sys.argv) > 2 else '')
    nous = nos_galaxies(tsv)
    pris, trouvees = set(), set()
    for seuil in (SEUIL_FIN, SEUIL_DEG):
        paires = sorted((separation(r[1], r[2], g[1], g[2]), k, i) for k, r in enumerate(ref) if k not in trouvees
                        for i, g in enumerate(nous) if i not in pris)
        for sep, k, i in paires:
            if sep >= seuil:
                break
            if k in trouvees or i in pris:
                continue
            trouvees.add(k)
            pris.add(i)
    ajout = [r for k, r in enumerate(ref) if k not in trouvees]
    with open(tsv, 'a', encoding='utf-8', newline='\n') as f:
        for name, ra, dec, d_mpc in ajout:
            a, d = math.radians(ra), math.radians(dec)
            x, ye, ze = math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d)
            y, z = ye * math.cos(EPS) + ze * math.sin(EPS), -ye * math.sin(EPS) + ze * math.cos(EPS)      # équatorial -> écliptique
            r = d_mpc * MPC_LY
            f.write(f'{name}\t{x * r!r}\t{y * r!r}\t{z * r!r}\tgalaxie naine\t3\n')
    print(f'{len(ajout)} galaxies ajoutées (Local Volume Database {version}) ; {len(pris)} y étaient déjà')


if __name__ == '__main__':
    main()
