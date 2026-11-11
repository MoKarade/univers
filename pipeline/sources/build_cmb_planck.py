#!/usr/bin/env python3
"""Fond diffus cosmologique de Planck -> app/gen/data16.js (remplace DATA.CMB, la carte WMAP).

Source : Planck 2018 (PR3), carte CMB par séparation de composantes SMICA, NSIDE 2048,
ESA / Planck Collaboration, Planck Legacy Archive, copie IRSA :
https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/component-maps/cmb/COM_CMB_IQU-smica_2048_R3.00_full.fits
Référence : Planck Collaboration 2020, A&A 641, A4.

Même projection et même mise à l'échelle que la carte WMAP de pipeline/build_data2.py
(image équirectangulaire en coordonnées galactiques, longitude 0 au centre, pôle nord en haut,
niveaux de gris à ±4 écarts-types), pour que la page n'ait rien d'autre à changer.

Usage : python pipeline/sources/build_cmb_planck.py <dossier_raw>
"""
import base64
import io
import json
import os
import sys

import astropy.units as u
import numpy as np
from astropy.io import fits
from astropy_healpix import HEALPix
from PIL import Image

FICHIER = 'planck_smica_2048_R3.fits'
LARGEUR, HAUTEUR = 2048, 1024      # 0,18 degré par pixel, proche de la résolution de SMICA (5 minutes d'arc)
QUALITE_JPEG = 85
B_MASQUE = 30.0                    # au-delà de |b| = 30 degrés, la carte est peu touchée par la Galaxie


def colonne_temperature(table):
    """Colonne d'intensité : la version comblée sur le plan galactique si elle existe."""
    noms = [c.upper() for c in table.columns.names]
    for nom in ('I_STOKES_INP', 'I_STOKES', 'TEMPERATURE'):
        if nom in noms:
            return table.columns.names[noms.index(nom)]
    raise SystemExit('colonne de température introuvable : %s' % noms)


def main(raw):
    with fits.open(os.path.join(raw, FICHIER), memmap=True) as h:
        hd = h[1].header
        col = colonne_temperature(h[1])
        unite = hd.get('TUNIT%d' % (h[1].columns.names.index(col) + 1))
        T = np.asarray(h[1].data.field(col), dtype=np.float32).ravel()
        print('Planck SMICA : NSIDE %s, ordre %s, colonne %s, unité %s, %d pixels'
              % (hd['NSIDE'], hd['ORDERING'], col, unite, T.size))
        hp = HEALPix(nside=int(hd['NSIDE']), order=hd['ORDERING'].strip().lower())

    uu, vv = np.meshgrid((np.arange(LARGEUR) + 0.5) / LARGEUR, (np.arange(HAUTEUR) + 0.5) / HAUTEUR)
    lon = (uu - 0.5) * 360.0
    lat = (0.5 - vv) * 180.0
    img = T[hp.lonlat_to_healpix((lon % 360) * u.deg, lat * u.deg)].astype(np.float64)

    hors_plan = np.abs(lat) > B_MASQUE
    ecart_uk = img[hors_plan].std() * (1e6 if unite and unite.strip().upper().startswith('K') else 1.0)
    print('écart-type hors du plan galactique (|b| > %g°) : %.1f µK ; min %.3g, max %.3g'
          % (B_MASQUE, ecart_uk, img.min(), img.max()))

    sigma = img.std()
    g8 = np.clip((img / (4.0 * sigma) * 0.5 + 0.5) * 255, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(g8, 'L').save(buf, 'JPEG', quality=QUALITE_JPEG, optimize=True)
    payload = {
        'CMB': 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode(),
        'CMB_SRC': 'Planck 2018 (PR3), carte SMICA, ESA et collaboration Planck (A&A 641, A4)',
    }
    out = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'gen', 'data16.js')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('Object.assign(DATA, ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ');\n')
    print('écrit', os.path.normpath(out), os.path.getsize(out), 'octets')
    Image.fromarray(g8, 'L').resize((1024, 512)).save(os.path.join(raw, 'cmb_planck_controle.png'))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'univers-raw'))
