#!/usr/bin/env python3
"""Centres des 49 152 tuiles du ciel de Gaia (HEALPix emboîté d'ordre 6) -> gaia_tuiles_centres.bin, pour choisir les
tuiles à l'écran dans l'appli PC (gaia_ciel.h). Direction unitaire x, y, z (float32), repère écliptique J2000 de l'appli.
Calcul : astropy_healpix (Górski et al. 2005), venv %LOCALAPPDATA%\\univers-venv.
Usage : python gaia_tuiles_centres.py <sortie.bin>
"""
import math
import sys

import numpy as np
from astropy_healpix import HEALPix
import astropy.units as u

EPS = math.radians(84381.448 / 3600.0)


def main() -> None:
    hp = HEALPix(nside=64, order='nested')
    lon, lat = hp.healpix_to_lonlat(np.arange(hp.npix))
    a, d = lon.to_value(u.rad), lat.to_value(u.rad)
    x, y, z = np.cos(d) * np.cos(a), np.cos(d) * np.sin(a), np.sin(d)
    out = np.stack([x, y * math.cos(EPS) + z * math.sin(EPS), -y * math.sin(EPS) + z * math.cos(EPS)], axis=1).astype('<f4')
    out.tofile(sys.argv[1])
    print(f'{len(out)} centres écrits')


if __name__ == '__main__':
    main()
