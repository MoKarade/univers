#!/usr/bin/env python3
"""Vrai ciel en fond : relevé photographique DSS2 en couleur -> image équirectangulaire galactique, hors de la page.

Source : Digitized Sky Survey 2 (STScI/NASA), colorisé et découpé en HiPS par le CDS (CNRS/Unistra),
copie servie par l'ESA : https://skies.esac.esa.int/DSSColor/ (ordre 3 téléchargé, 768 tuiles JPEG de 512 px,
dans <raw>/hips_dss/DSSColor/Norder3/Dir0/NpixN.jpg). Crédit : « DSS2 (STScI/NASA), couleurs et HiPS : CDS ».
Conditions d'usage du DSS : http://archive.stsci.edu/dss/copyright.html

Méthode : chaque tuile d'ordre 3 couvre un pixel HEALPix (repère équatorial, numérotation « nested ») ; ses
512 × 512 pixels sont les sous-pixels d'ordre 12 (nside 4096). L'ordre des sous-pixels dans l'image (lignes,
colonnes, sens) n'est pas relu ici dans la norme HiPS : il est établi sur les données, en essayant les 8 dispositions
possibles et en gardant celle où les étoiles les plus brillantes tombent sur les pixels les plus brillants (contrôle
bloquant, avec un écart net sur la deuxième disposition). La carte d'ordre 12 est ensuite lue en coordonnées
galactiques sur une grille plate carrée.

Sortie (hors dépôt, à déposer à part de la page) : <raw>/sky_dss_8192.jpg, convention de la texture de ciel de
la page (shader de skyMesh, 40_render.js) : u = 0,5 − l/360°, v = 0,5 + b/180°, ligne du haut de l'image = b = +90°.

Usage : python pipeline/sources/build_sky_dss.py <dossier_raw>   (venv avec astropy et astropy-healpix)
"""
import os
import sys

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy_healpix import HEALPix
from PIL import Image

ORDRE = 3
TUILE = 512
NSIDE = (2 ** ORDRE) * TUILE          # 4096
LARGEUR, HAUTEUR = 8192, 4096
QUALITE = 88
# Étoiles brillantes (ICRS, degrés), positions Hipparcos arrondies au centième de degré.
ETOILES = {'Sirius': (101.29, -16.72), 'Canopus': (95.99, -52.70), 'Arcturus': (213.92, 19.18), 'Véga': (279.23, 38.78),
           'Capella': (79.17, 46.00), 'Rigel': (78.63, -8.20), 'Procyon': (114.83, 5.22), 'Achernar': (24.43, -57.24),
           'Bételgeuse': (88.79, 7.41), 'Altaïr': (297.70, 8.87), 'Aldébaran': (68.98, 16.51), 'Antarès': (247.35, -26.43),
           'Spica': (201.30, -11.16), 'Pollux': (116.33, 28.03), 'Fomalhaut': (344.41, -29.62), 'Deneb': (310.36, 45.28)}


def entrelace(x, y):
    """Indice « nested » dans une face à partir de (x, y) : bits de x aux rangs pairs, de y aux rangs impairs."""
    r = np.zeros_like(x)
    for b in range(9):
        r |= ((x >> b) & 1) << (2 * b)
        r |= ((y >> b) & 1) << (2 * b + 1)
    return r


def dispositions():
    """Les 8 façons de lire une tuile : échange lignes/colonnes, retournement de chacune."""
    j, i = np.mgrid[0:TUILE, 0:TUILE]          # j : ligne depuis le haut, i : colonne
    out = {}
    for swap in (False, True):
        for fx in (False, True):
            for fy in (False, True):
                a, b = (j, i) if swap else (i, j)
                a = TUILE - 1 - a if fx else a
                b = TUILE - 1 - b if fy else b
                out[(swap, fx, fy)] = entrelace(a.astype(np.int64), b.astype(np.int64))
    return out


def charger_tuiles(dossier):
    tuiles = {}
    for n in range(12 * 4 ** ORDRE):
        p = os.path.join(dossier, 'Norder%d' % ORDRE, 'Dir0', 'Npix%d.jpg' % n)
        if os.path.exists(p):
            tuiles[n] = np.asarray(Image.open(p).convert('RGB'))
    print('tuiles lues : %d sur %d' % (len(tuiles), 12 * 4 ** ORDRE))
    if len(tuiles) != 12 * 4 ** ORDRE:
        raise SystemExit('tuiles manquantes : rien écrit')
    return tuiles


def carte(tuiles, sous):
    m = np.zeros((12 * NSIDE * NSIDE, 3), dtype=np.uint8)
    base = TUILE * TUILE
    for n, t in tuiles.items():
        m[n * base + sous.ravel()] = t.reshape(-1, 3)
    return m


def score(m, hp):
    """Éclat moyen (0-255) au pixel de chaque étoile brillante, moins l'éclat médian de la carte."""
    c = SkyCoord([v[0] for v in ETOILES.values()] * u.deg, [v[1] for v in ETOILES.values()] * u.deg, frame='icrs')
    idx = hp.skycoord_to_healpix(c)
    lum = m[idx].astype(float).mean(axis=1)
    return lum.mean() - np.median(m[::997].astype(float).mean(axis=1)), lum


def main(raw):
    tuiles = charger_tuiles(os.path.join(raw, 'hips_dss', 'DSSColor'))
    hp = HEALPix(nside=NSIDE, order='nested', frame='icrs')
    essais = []
    for cle, sous in dispositions().items():
        s, lum = score(carte(tuiles, sous), hp)
        essais.append((s, cle, lum))
        print('disposition échange=%s retournement x=%s y=%s : %.1f' % (cle[0], cle[1], cle[2], s))
    essais.sort(key=lambda e: -e[0])
    meilleur, second = essais[0], essais[1]
    print('retenue :', meilleur[1], 'score %.1f (suivante %.1f)' % (meilleur[0], second[0]))
    print('éclat aux étoiles :', {k: int(v) for k, v in zip(ETOILES, meilleur[2])})
    if meilleur[0] < 2 * max(second[0], 1) or (meilleur[2] < 120).sum() > 2:
        raise SystemExit('disposition des tuiles non établie : rien écrit')
    m = carte(tuiles, dispositions()[meilleur[1]])

    # grille plate carrée galactique : colonne -> l (0 au centre, croît vers la gauche), ligne -> b (+90 en haut)
    l = (0.5 - (np.arange(LARGEUR) + 0.5) / LARGEUR) * 360.0
    b = 90.0 - (np.arange(HAUTEUR) + 0.5) / HAUTEUR * 180.0
    img = np.empty((HAUTEUR, LARGEUR, 3), dtype=np.uint8)
    hpg = HEALPix(nside=NSIDE, order='nested', frame='galactic')
    for r0 in range(0, HAUTEUR, 256):
        L, B = np.meshgrid(l, b[r0:r0 + 256])
        c = SkyCoord(L.ravel() * u.deg, B.ravel() * u.deg, frame='galactic')
        img[r0:r0 + 256] = m[hp.skycoord_to_healpix(c)].reshape(B.shape + (3,))
    del hpg
    for w in (8192, 4096):
        out = os.path.join(raw, 'sky_dss_%d.jpg' % w)
        Image.fromarray(img).resize((w, w // 2), Image.LANCZOS).save(out, 'JPEG', quality=QUALITE, optimize=True)
        print('écrit', out, os.path.getsize(out), 'octets')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'univers-raw'))
