"""Refroidissement des naines blanches dans les bandes de Gaia -> naines_blanches.bin (lu par natif/src/vie_etoiles.h).

Source : modèles de Montréal (Bédard et al. 2020, ApJ 901, 93 ; couleurs : Holberg & Bergeron 2006, Kowalski &
Saumon 2006, Tremblay et al. 2011, Blouin et al. 2018), tables « Table_Mass_0.5 » à « Table_Mass_1.3 » de
https://www.astro.umontreal.ca/~bergeron/CoolingModels/ ; atmosphère d'hydrogène pur (naines DA, les plus nombreuses).
Masse de la naine blanche d'après la masse initiale : relation de Cummings et al. 2018 (ApJ 866, 21), version MIST :
  0,83-2,85 M☉ : 0,080 Mi + 0,489 ; 2,85-3,60 M☉ : 0,187 Mi + 0,184 ; 3,60-7,20 M☉ : 0,107 Mi + 0,471.
(Lue dans l'article [À vérifier : coefficients recopiés de l'article, à relire contre sa table 3].)

Format naines_blanches.bin : « UNIVNBL1 », nMasses (u32), nPoints (u32), masses (f32 × nMasses), puis pour chaque masse
5 tableaux de nPoints : âge de refroidissement (f64, ans, croissant), G, BP-RP, V, B-V (f32, magnitudes absolues).

Usage : python naines_blanches.py <dossier des tables> <sortie naines_blanches.bin>
"""
import os
import sys

import numpy as np

MASSES = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3)
COL_B, COL_V, COL_G, COL_BP, COL_RP, COL_AGE = 5, 6, 37, 38, 39, 42


def lire(chemin: str) -> np.ndarray:
    """Premier bloc (hydrogène pur), lignes de données seulement."""
    lignes = open(chemin).read().split('\n')[2:]
    bloc = []
    for l in lignes:
        if not l.strip() or any(c.isalpha() and c not in 'Ee' for c in l):      # fin du bloc (ligne vide ou en-tête suivant)
            break
        bloc.append([float(x) for x in l.split()])
    d = np.array(bloc)
    return d[np.argsort(d[:, COL_AGE])]


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    dossier, sortie = sys.argv[1:3]
    tables = [lire(os.path.join(dossier, f'Table_Mass_{m}')) for m in MASSES]
    n = min(len(t) for t in tables)
    with open(sortie + '.partiel', 'wb') as f:
        f.write(b'UNIVNBL1' + np.uint32(len(MASSES)).tobytes() + np.uint32(n).tobytes())
        f.write(np.array(MASSES, '<f4').tobytes())
        for m, t in zip(MASSES, tables):
            t = t[-n:]      # mêmes nombres de points : on garde les plus vieux si une table en a plus
            f.write(t[:, COL_AGE].astype('<f8').tobytes())
            f.write(t[:, COL_G].astype('<f4').tobytes())
            f.write((t[:, COL_BP] - t[:, COL_RP]).astype('<f4').tobytes())
            f.write(t[:, COL_V].astype('<f4').tobytes())
            f.write((t[:, COL_B] - t[:, COL_V]).astype('<f4').tobytes())
            print(f'  {m} M☉ : {n} points, de {t[0, COL_AGE]:.2e} à {t[-1, COL_AGE]:.2e} ans, G {t[0, COL_G]:.2f} -> {t[-1, COL_G]:.2f}')
    os.replace(sortie + '.partiel', sortie)
    print(f'-> {sortie}')


if __name__ == '__main__':
    main()
