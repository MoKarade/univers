"""S1 : table de couleur des corps noirs, pour la couleur des étoiles.

Pour chaque température (1000 à 40 000 K, pas logarithmique), on intègre la loi de Planck
sur les fonctions colorimétriques de l'observateur standard CIE 1931 (2°), puis on passe
de XYZ à sRGB linéaire (IEC 61966-2-1). La composante la plus forte vaut 1 : la couleur
ne porte que la teinte, l'éclat vient de la magnitude.

Source des fonctions colorimétriques : CVRL (UCL), fichier ciexyz31_1.csv, 360 à 830 nm au pas de 1 nm,
http://www.cvrl.org/database/data/cmfs/ciexyz31_1.csv — copie dans pipeline/ref/.

Écrit app/gen/data15.js. Lancer depuis la racine du dépôt : python3 pipeline/build_bbcol.py
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CMF_FILE = ROOT / 'pipeline' / 'ref' / 'ciexyz31_1.csv'
OUT_FILE = ROOT / 'app' / 'gen' / 'data15.js'

T_MIN, T_MAX, N = 1000.0, 40000.0, 256
H, C, KB = 6.62607015e-34, 299792458.0, 1.380649e-23   # valeurs exactes du SI 2019

# XYZ -> sRGB linéaire (IEC 61966-2-1, blanc D65)
M = ((3.2406, -1.5372, -0.4986), (-0.9689, 1.8758, 0.0415), (0.0557, -0.2040, 1.0570))


def load_cmf():
    rows = []
    for line in CMF_FILE.read_text().strip().splitlines():
        l, x, y, z = (float(v) for v in line.split(','))
        rows.append((l, x, y, z))
    if len(rows) != 471 or rows[0][0] != 360 or rows[-1][0] != 830:
        raise SystemExit('table CIE inattendue : %d lignes' % len(rows))
    return rows


def planck(lnm, t):
    l = lnm * 1e-9
    return 1.0 / (l ** 5 * math.expm1(H * C / (l * KB * t)))


def rgb_of(t, cmf):
    X = Y = Z = 0.0
    for l, x, y, z in cmf:
        b = planck(l, t)
        X += b * x; Y += b * y; Z += b * z
    rgb = [max(0.0, r[0] * X + r[1] * Y + r[2] * Z) for r in M]
    m = max(rgb)
    return [v / m for v in rgb]


def main():
    cmf = load_cmf()
    table = []
    for i in range(N):
        t = T_MIN * (T_MAX / T_MIN) ** (i / (N - 1))
        table.extend(round(v, 4) for v in rgb_of(t, cmf))
    data = {'BBCOL': {'t0': T_MIN, 't1': T_MAX, 'n': N, 'rgb': table,
                      'src': 'Loi de Planck intégrée sur CIE 1931 2° (CVRL), sRGB linéaire IEC 61966-2-1'}}
    OUT_FILE.write_text('Object.assign(DATA, ' + json.dumps(data, separators=(',', ':')) + ');\n', encoding='utf-8')
    print('écrit', OUT_FILE, len(table) // 3, 'températures')


if __name__ == '__main__':
    main()
