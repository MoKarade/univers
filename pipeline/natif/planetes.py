#!/usr/bin/env python3
"""Éclat et teinte des planètes vues comme des points -> planetes.tsv pour l'appli PC.

Rien n'est recopié de mémoire :
- magnitude V(1,0) (éclat à 1 UA du Soleil et de l'observateur, pleine phase) : lue dans les fiches de la NASA,
  https://nssdc.gsfc.nasa.gov/planetary/factsheet/<planète>fact.html, ligne « V-band magnitude V(1,0) » ;
- teinte : moyenne de la carte de surface de l'astre (Solar System Scope, CC BY 4.0), calculée en lumière linéaire
  et pondérée par la surface réelle de chaque ligne de la carte (cosinus de la latitude). Sans carte : pas de teinte.

Sortie : planetes.tsv, une ligne par astre : code NAIF, magnitude V(1,0), rouge, vert, bleu (0 à 255, valeurs d'écran ;
-1 -1 -1 si pas de carte).
Usage : python planetes.py <dossier des cartes> <dossier de sortie>
"""
import math, os, re, sys, urllib.request
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ASTRES = [('mercury', 199, '8k_mercury.jpg'), ('venus', 299, '4k_venus_atmosphere.jpg'), ('earth', 399, '8k_earth_daymap.jpg'), ('moon', 301, '8k_moon.jpg'),
          ('mars', 4, '8k_mars.jpg'), ('jupiter', 5, '8k_jupiter.jpg'), ('saturn', 6, '8k_saturn.jpg'), ('uranus', 7, '2k_uranus.jpg'),
          ('neptune', 8, '2k_neptune.jpg'), ('pluto', 9, None)]


def magnitude(nom):
    with urllib.request.urlopen(f'https://nssdc.gsfc.nasa.gov/planetary/factsheet/{nom}fact.html', timeout=60) as resp:
        txt = resp.read().decode('latin-1')
    m = re.search(r'V-band magnitude V\(1,0\)(.*?)(-?\d+\.\d+)', txt, re.S)
    if not m: raise SystemExit(f'{nom} : magnitude V(1,0) introuvable dans la fiche de la NASA')
    return float(m.group(2))


def teinte(path):
    with Image.open(path) as img:
        im = np.asarray(img.convert('RGB').resize((1024, 512), Image.BOX), dtype=np.float64) / 255
    lin = np.where(im <= 0.04045, im / 12.92, ((im + 0.055) / 1.055) ** 2.4)
    w = np.cos((np.arange(512) + 0.5) / 512 * math.pi - math.pi / 2)[:, None, None]
    mean = (lin * w).sum(axis=(0, 1)) / (w.sum() * 1024)
    mean = mean / mean.max()      # seule la teinte est gardée ; l'éclat vient de la magnitude
    srgb = np.where(mean <= 0.0031308, 12.92 * mean, 1.055 * mean ** (1 / 2.4) - 0.055)
    return [int(round(255 * float(c))) for c in srgb]


def main():
    cartes, sortie = sys.argv[1], sys.argv[2]
    os.makedirs(sortie, exist_ok=True)
    with open(os.path.join(sortie, 'planetes.tsv'), 'w', encoding='ascii', newline='\n') as f:
        for nom, naif, carte in ASTRES:
            h = magnitude(nom); rgb = teinte(os.path.join(cartes, carte)) if carte else [-1, -1, -1]
            f.write(f'{naif}\t{h}\t{rgb[0]}\t{rgb[1]}\t{rgb[2]}\n')
            print(f'{nom:8s} V(1,0) = {h:+.2f}   teinte {rgb}')


if __name__ == '__main__':
    main()
