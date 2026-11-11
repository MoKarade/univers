"""S3 : couleur observée des galaxies et des quasars selon leur décalage vers le rouge z.

Pour chaque z, le spectre au repos F_lambda est décalé (lambda_obs = (1+z) lambda_repos), intégré sur
l'observateur CIE 1931 2° (pipeline/ref/ciexyz31_1.csv, comme pour les étoiles en S1), puis converti en
sRGB linéaire, composante la plus forte à 1 (la couleur ne porte que la teinte).
Le facteur (1+z)^-1 commun du flux par longueur d'onde ne change pas la teinte et n'est pas appliqué ici.

Spectres :
- Galaxies : modèle Sb de l'atlas Kinney-Calzetti (Kinney et al. 1996, ApJ 467, 38), STScI CDBS grid/kc96,
  1235 à 9940 Å au repos. Un seul type pour toutes les galaxies : leur type n'est pas dans nos catalogues
  (supposé, dit dans la page). La lumière visible reçue (380 nm) vient de 1235 Å au repos jusqu'à z = 2,07 ; au-delà, z est borné.
- Quasars : spectre moyen SDSS spDR2-029 (première composante, classe QSO), 709 à 7809 Å au repos ; couvert jusqu’à z = 4,35.

Écrit app/gen/data16.js. Lancer depuis la racine du dépôt : python3 pipeline/build_zcol.py
"""
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'pipeline' / 'ref'
OUT = ROOT / 'app' / 'gen' / 'data16.js'
N = 64
ZMAX_GAL, ZMAX_QSO = 2.07, 4.35
# XYZ -> sRGB linéaire (IEC 61966-2-1, blanc D65), même matrice que pipeline/build_bbcol.py
M = ((3.2406, -1.5372, -0.4986), (-0.9689, 1.8758, 0.0415), (0.0557, -0.2040, 1.0570))


def fits_cards(b: bytes, off: int) -> tuple[dict, int]:
    """Lit un en-tête FITS (blocs de 2880 octets) ; rend les mots-clés et le début des données."""
    h = {}
    while True:
        blk = b[off:off + 2880]
        off += 2880
        for i in range(36):
            c = blk[i * 80:(i + 1) * 80].decode('ascii')
            if c[:8].strip() == 'END':
                return h, off
            if c[8:10] == '= ':
                h[c[:8].strip()] = c[10:].split('/')[0].strip().strip("'").strip()


def read_kc96(path: Path) -> list[tuple[float, float]]:
    """Table binaire STSDAS : colonnes WAVELENGTH (Å), FLUX (flam)."""
    b = path.read_bytes()
    _, off = fits_cards(b, 0)
    h, off = fits_cards(b, off)
    nrow, rowlen = int(h['NAXIS2']), int(h['NAXIS1'])
    if h['TTYPE1'] != 'WAVELENGTH' or h['TTYPE2'] != 'FLUX':
        raise SystemExit('colonnes inattendues dans ' + path.name)
    fmt = '>' + ''.join({'E': 'f', 'D': 'd'}[h['TFORM%d' % (i + 1)][-1]] for i in range(2))
    return [struct.unpack_from(fmt, b, off + r * rowlen) for r in range(nrow)]


def read_sdss(path: Path) -> list[tuple[float, float]]:
    """Image SDSS : ligne 0, longueur d'onde log10 = COEFF0 + COEFF1 * pixel (Å)."""
    b = path.read_bytes()
    h, off = fits_cards(b, 0)
    n, c0, c1 = int(h['NAXIS1']), float(h['COEFF0']), float(h['COEFF1'])
    if h['SPEC_CLN'] != '3':          # 3 = classe QSO dans SDSS
        raise SystemExit('ce fichier n\'est pas un modèle de quasar')
    row = struct.unpack_from('>%df' % n, b, off)
    return [(10 ** (c0 + c1 * i), v) for i, v in enumerate(row) if v != 0]


def interp(tab: list, lam: float) -> float | None:
    if lam < tab[0][0] or lam > tab[-1][0]:
        return None
    lo, hi = 0, len(tab) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if tab[m][0] <= lam:
            lo = m
        else:
            hi = m
    (l0, f0), (l1, f1) = tab[lo], tab[hi]
    return f0 + (f1 - f0) * (lam - l0) / (l1 - l0) if l1 > l0 else f0


def rgb(tab: list, z: float, cmf: list) -> list[float]:
    X = Y = Z = 0.0
    for lnm, x, y, zz in cmf:
        f = interp(tab, lnm * 10 / (1 + z))
        if f is None:
            if x + y + zz < 1e-4:          # bords de l'œil (au-delà de 780 nm) : sans effet
                continue
            raise ValueError('hors du spectre à z=%.3f, %d nm' % (z, lnm))
        X += f * x
        Y += f * y
        Z += f * zz
    v = [max(0.0, r[0] * X + r[1] * Y + r[2] * Z) for r in M]
    m = max(v)
    return [c / m for c in v]


def table(tab: list, zmax: float, cmf: list) -> list[float]:
    out = []
    for i in range(N):
        z = math.exp(i / (N - 1) * math.log(1 + zmax)) - 1      # pas régulier en log(1+z)
        out.extend(round(c, 4) for c in rgb(tab, z, cmf))
    return out


def main() -> None:
    cmf = [tuple(float(v) for v in l.split(',')) for l in (REF / 'ciexyz31_1.csv').read_text().strip().splitlines()]
    cmf = [c for c in cmf if 380 <= c[0] <= 780]          # visible : 380 à 780 nm (en deçà de 380 nm, x+y+z < 0,002 : négligeable)
    gal, qso = read_kc96(REF / 'kc96_sb_template.fits'), read_sdss(REF / 'sdss_spDR2-029_qso.fit')
    data = {'ZCOL': {'n': N, 'zg': ZMAX_GAL, 'zq': ZMAX_QSO, 'gal': table(gal, ZMAX_GAL, cmf), 'qso': table(qso, ZMAX_QSO, cmf),
                     'src': 'Galaxies : modèle Sb, Kinney et al. 1996 ; quasars : spectre moyen SDSS spDR2-029 ; CIE 1931 2°'}}
    OUT.write_text('Object.assign(DATA, ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ');\n', encoding='utf-8')
    print('écrit', OUT)


if __name__ == '__main__':
    main()
