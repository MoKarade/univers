"""S5 : carte de poussière mesurée en 3D autour du Soleil, réduite pour la page.

Source : Edenhofer et al. 2024 (A&A 685, A82 ; arXiv 2308.01295), « A parsec-scale Galactic 3D dust map out to 1.25 kpc
from the Sun », Zenodo 10.5281/zenodo.10658339, fichier mean_and_std_healpix.fits (3,25 Go, non versé : à télécharger).
Contenu : moyenne de la densité de poussière sur 516 sphères HEALPix (nside 256, ordre NEST) à distances espacées en log,
en unités d'extinction de Zhang, Green et Rix 2023 par parsec. Conversion de l'article : A_V (540 nm) = 2,8 × E_ZGR23.

Sortie : app/gen/data20.js, DATA.DUST = grille cartésienne héliocentrique galactique (x vers le centre galactique, y vers
l = 90°, z vers le pôle nord galactique), 160 × 160 × 52 cases de 15,625 pc (|x|, |y| ≤ 1250 pc, |z| ≤ 406,25 pc).
Chaque case : moyenne de 27 points (3 × 3 × 3) de dA_V/ds en mag/pc, codée sur un octet en log :
0 = moins de 1e-5 mag/pc ou hors de la carte (au-delà de 1,25 kpc) ; k = 1..255 : 10^(-5 + (k - 1) / 254 × 4).

Lancer (Python avec numpy, astropy, astropy-healpix) depuis la racine du dépôt :
  python pipeline/build_dust.py <chemin/mean_and_std_healpix.fits>
"""
import base64
import json
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy_healpix import HEALPix
import astropy.units as u

_PIPE_DIR = str(Path(__file__).resolve().parent)
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import APP_GEN  # noqa: E402

OUT = APP_GEN / 'data20.js'
NX, NY, NZ, CELL = 160, 160, 52, 15.625
AV_PER_E = 2.8                      # Edenhofer et al. 2024, section 2 : A_V = 2,8 × E_ZGR23
LOG_LO, LOG_SPAN = -5.0, 4.0        # 1e-5 à 1e-1 mag/pc


def load(path: str):
    with fits.open(path, memmap=False) as h:
        mean = h['MEAN'].data.astype(np.float32)           # (516 rayons, 786432 pixels)
        nside = h['MEAN'].header['NSIDE']
        nest = h['MEAN'].header['ORDERING'].strip().upper().startswith('NEST')
        radii, inner, r_in = None, None, None
        for hdu in h:
            if hdu.name.upper().startswith('MEAN OF INTEGRATED INNER'):
                r_in = float(hdu.name.split()[-2])                              # « ... INNER 68.8 PC »
                inner = hdu.data.astype(np.float64) / r_in                       # densité moyenne en deçà de r_in

            if isinstance(hdu, fits.BinTableHDU) and hdu.data.names == ['radial pixel centers']:
                radii = np.asarray(hdu.data['radial pixel centers'], dtype=np.float64)
    if radii is None or radii.size != mean.shape[0]:
        raise SystemExit('rayons introuvables ou incohérents')
    if inner is None:
        raise SystemExit('extension « integrated inner » introuvable')
    return mean, radii, inner, r_in, HEALPix(nside=nside, order='nested' if nest else 'ring')


def sample(mean, radii, inner, hp, x, y, z):
    """dA_V/ds (mag/pc) aux points (pc, repère galactique héliocentrique) ; 0 hors de la carte."""
    r = np.sqrt(x * x + y * y + z * z)
    lon = np.degrees(np.arctan2(y, x)) % 360.0
    lat = np.degrees(np.arctan2(z, np.sqrt(x * x + y * y)))
    pix = hp.lonlat_to_healpix(lon * u.deg, lat * u.deg)
    i = np.clip(np.searchsorted(radii, r) - 1, 0, radii.size - 2)
    w = np.clip((r - radii[i]) / (radii[i + 1] - radii[i]), 0.0, 1.0)
    v = (1 - w) * mean[i, pix] + w * mean[i + 1, pix]
    v = np.where(r < radii[0], inner[pix], np.where(r > radii[-1], 0.0, v))      # en deçà de la première sphère : moyenne publiée de la bulle intérieure
    return v * AV_PER_E


def main(path: str) -> None:
    mean, radii, inner, r_in, hp = load(path)
    print('carte :', mean.shape, 'rayons', radii[0], 'à', radii[-1], 'pc ; intérieur intégré jusqu’à', r_in, 'pc')
    cx = (np.arange(NX) - NX / 2 + 0.5) * CELL
    cy = (np.arange(NY) - NY / 2 + 0.5) * CELL
    cz = (np.arange(NZ) - NZ / 2 + 0.5) * CELL
    off = (np.arange(3) - 1) * CELL / 3
    grid = np.zeros((NZ, NY, NX), dtype=np.float64)
    for k, z0 in enumerate(cz):
        X, Y = np.meshgrid(cx, cy, indexing='xy')
        acc = np.zeros_like(X)
        for dx in off:
            for dy in off:
                for dz in off:
                    acc += sample(mean, radii, inner, hp, X + dx, Y + dy, np.full_like(X, z0 + dz))
        grid[k] = acc / 27
    q = np.zeros(grid.shape, dtype=np.uint8)
    ok = grid >= 10 ** LOG_LO
    q[ok] = 1 + np.clip(np.round((np.log10(grid[ok]) - LOG_LO) / LOG_SPAN * 254), 0, 254).astype(np.uint8)
    data = {'DUST': {'nx': NX, 'ny': NY, 'nz': NZ, 'cell': CELL, 'lo': LOG_LO, 'span': LOG_SPAN, 'rmax': float(radii[-1]),
                     'q': base64.b64encode(q.tobytes()).decode('ascii'),
                     'src': 'Edenhofer et al. 2024 (A&A 685, A82), moyenne de la carte 3D ; A_V = 2,8 × E_ZGR23'}}
    OUT.write_text('Object.assign(DATA, ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ');\n', encoding='utf-8', newline='\n')
    print('écrit', OUT, '| cases non vides :', int(ok.sum()), 'sur', q.size, '| A_V max par case :', float(grid.max() * CELL))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
