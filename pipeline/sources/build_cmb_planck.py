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
NSIDE_IMAGE = 512                  # pixels de 6,9 minutes d'arc : un point de l'image (10,5') couvre environ un pixel
NSIDE_CONTROLE = 32                # grande échelle, pour comparer à WMAP
CORREL_MIN = 0.8                   # Planck et WMAP voient le même ciel : corrélation attendue au-dessus


def degrader(T, nside, nside_cible):
    """Moyenne des pixels enfants en ordre NESTED : chaque pixel parent regroupe (nside/nside_cible)² enfants contigus."""
    k = (nside // nside_cible) ** 2
    return T.reshape(-1, k).mean(axis=1)


def controle_wmap(raw, T, nside):
    """Corrélation de pixel à pixel avec la carte WMAP ILC à grande échelle, hors du plan galactique, et témoin retourné."""
    chemin = os.path.join(raw, 'wmap_ilc.fits')
    if not os.path.exists(chemin):
        print('contrôle WMAP sauté : wmap_ilc.fits absent'); return None
    with fits.open(chemin) as h:
        hd = h[1].header
        W = np.asarray(h[1].data.field(0), dtype=np.float64).ravel()
        if hd['ORDERING'].strip().upper() != 'NESTED':
            hw = HEALPix(nside=int(hd['NSIDE']), order='ring')
            W = W[hw.nested_to_ring(np.arange(W.size))]
    p = degrader(T.astype(np.float64), nside, NSIDE_CONTROLE)
    w = degrader(W, int(hd['NSIDE']), NSIDE_CONTROLE)
    hc = HEALPix(nside=NSIDE_CONTROLE, order='nested')
    lon, lat = hc.healpix_to_lonlat(np.arange(p.size))
    lat = lat.to_value(u.deg)
    m = np.abs(lat) > B_MASQUE
    r = np.corrcoef(p[m], w[m])[0, 1]
    # témoin : la carte de Planck lue au point opposé du ciel ne doit plus ressembler à WMAP
    opp = hc.lonlat_to_healpix(lon + 180 * u.deg, -lat * u.deg)
    r_t = np.corrcoef(p[opp][m], w[m])[0, 1]
    print('corrélation Planck/WMAP hors du plan (NSIDE %d) : %.3f ; témoin retourné : %.3f' % (NSIDE_CONTROLE, r, r_t))
    if r < CORREL_MIN or abs(r_t) > 0.3:
        raise SystemExit('contrôle WMAP en échec : rien écrit')
    return round(float(r), 3)


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
        nside = int(hd['NSIDE'])
        if hd['ORDERING'].strip().upper() != 'NESTED':
            raise SystemExit('ordre RING non prévu')
    correl = controle_wmap(raw, T, nside)
    T = degrader(T, nside, NSIDE_IMAGE)
    hp = HEALPix(nside=NSIDE_IMAGE, order='nested')

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
        'CMB_CHK': {'largeur': LARGEUR, 'hauteur': HAUTEUR, 'correl_wmap': correl},
    }
    out = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'gen', 'data16.js')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('Object.assign(DATA, ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ');\n')
    print('écrit', os.path.normpath(out), os.path.getsize(out), 'octets')
    Image.fromarray(g8, 'L').resize((1024, 512)).save(os.path.join(raw, 'cmb_planck_controle.png'))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'univers-raw'))
