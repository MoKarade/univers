#!/usr/bin/env python3
"""Vraies photos des galaxies voisines -> textures de l'appli PC (natif/src/galaxies_images.h).

Andromède (M31), le Triangle (M33), le Grand et le Petit Nuage de Magellan : photos du Digitized Sky Survey 2 (DSS2,
plaques photographiques du Palomar et du télescope de Schmidt du Royaume-Uni), trois bandes (bleue, rouge, proche
infrarouge) obtenues du service SkyView de la NASA (skyview.gsfc.nasa.gov, projection gnomonique, nord en haut, est à
gauche). Le service HiPS du CDS (hips2fits) ne répondait pas le 13/11/2026. Pour les deux Nuages de Magellan, le DSS2 a des
trous et des zones brûlées entre plaques : on prend la mosaïque de tout le ciel d'Axel Mellinger (2009, PASP 121, 1180 ;
rouge, vert, bleu ; aussi par SkyView), plus homogène mais moins fine (36″ par pixel environ).

Traitement, sans rien inventer :
- couleur : rouge = plaque rouge, bleu = plaque bleue, vert = leur moyenne (la plaque infrarouge, plus bruitée, avec des
  traînées de satellites, n'est pas prise) ; chaque bande est ramenée à zéro sur le fond du ciel mesuré autour de la galaxie ;
- étoiles de premier plan (Voie lactée) : un point plus brillant que la médiane locale (fenêtre de 9 pixels) de plus de
  5 écarts types est remplacé par cette médiane ; les plus brillantes laissent un halo atténué [limite connue] ;
- bord : l'image s'éteint en douceur sur une ellipse qui suit l'inclinaison et l'angle de position mesurés.
Les plaques photographiques ne sont pas linéaires : les rapports d'éclat à l'intérieur de la galaxie sont approchés
[à vérifier] ; l'éclat total est recalé dans l'appli sur la magnitude absolue publiée.

Sortie : <nom>.png (RVB 8 bits, racine carrée de la lumière : l'appli met au carré) et galaxies_images.tsv
(corps de l'appli, fichier, ascension droite et déclinaison du centre (°), champ (°), angle de position du grand axe (°),
inclinaison (°), magnitude absolue V, sources).
Usage : python galaxies_images.py <dossier des FITS téléchargés> <dossier de sortie>
"""
import math
import os
import sys

import numpy as np
from astropy.io import fits
from PIL import Image
from scipy import ndimage

# nom de fichier, corps de l'appli, RA, Dec (°), champ (°), PA (°), inclinaison (°), M_V, sources
GALAXIES = [
    ('m31', 'Andromède (M31)', 10.6847, 41.2690, 3.4, 38.0, 77.0, -21.66,
     'PA et inclinaison : de Vaucouleurs 1958 / Walterbos & Kennicutt 1987 ; M_V : composantes.json (Tamm et al. 2012, RC3)'),
    ('m33', 'Galaxie du Triangle (M33)', 23.4621, 30.6599, 1.3, 22.0, 55.0, -18.8,
     'PA et inclinaison : Corbelli & Schneider 1997 ; M_V : McConnachie 2012'),
    ('lmc', 'Grand Nuage de Magellan', 80.89, -69.76, 18.0, 139.1, 34.7, -18.1,
     'ligne des nœuds et inclinaison : van der Marel & Kallivayalil 2014 ; M_V : McConnachie 2012'),
    ('smc', 'Petit Nuage de Magellan', 13.19, -72.83, 8.0, 45.0, 0.0, -16.8,
     'forme irrégulière et épaisse : dessinée face à nous (inclinaison non définie) ; M_V : McConnachie 2012'),
]
SORTIE = 1024        # pixels de la texture
MELLINGER = {'lmc', 'smc'}
# Amas globulaires de la Voie lactée devant les Nuages (pas des Nuages) : masqués. RA, Dec, rayon (°) [Harris 1996, éd. 2010].
RAYON = {'lmc': 0.42, 'smc': 0.55}      # bord du cadre adouci, en fraction du demi-champ (0,75 sinon)
PREMIER_PLAN = {'smc': [(6.0236, -72.0813, 0.55), (15.8094, -70.8488, 0.2)]}      # le DSS2 du Grand Nuage a des trous et des zones brûlées entre plaques


def fond(d: np.ndarray, galaxie: np.ndarray, bloc: int = 64) -> np.ndarray:
    """Fond du ciel hors de la galaxie, par blocs (médiane), lissé et étendu sous la galaxie : il retire les dégradés
    et les écarts entre plaques photographiques du DSS2 autour de la galaxie (pas ceux qui la traversent)."""
    n = d.shape[0] // bloc
    g = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            b = d[i * bloc:(i + 1) * bloc, j * bloc:(j + 1) * bloc]
            m = ~galaxie[i * bloc:(i + 1) * bloc, j * bloc:(j + 1) * bloc]
            if m.sum() > bloc * bloc // 3: g[i, j] = np.median(b[m])
    while np.isnan(g).any():      # sous la galaxie : moyenne des blocs voisins connus, de proche en proche
        k = np.isnan(g)
        s = ndimage.uniform_filter(np.nan_to_num(g), 3); c = ndimage.uniform_filter((~k).astype(float), 3)
        g = np.where(k & (c > 0), s / np.maximum(c, 1e-9), g)
    g = ndimage.gaussian_filter(g, 1.0)
    return ndimage.zoom(g, d.shape[0] / n, order=1)[:d.shape[0], :d.shape[1]]


def bande(chemin: str, pa: float, incl: float, centre=None, masques=(), rayon: float = 0.75) -> np.ndarray:
    d = fits.open(chemin)[0].data.astype(np.float64)[::-1]        # FITS : première ligne au sud ; image : nord en haut
    if 'mellinger' in chemin.replace(os.sep, '/'):      # mosaïque de Mellinger : valeurs 0-255 déjà encodées pour l'écran -> lumière
        d = (np.clip(d, 0, 255) / 255.0) ** 2.2
    d = d - fond(d, fenetre(d.shape[0], pa, incl, 1.15 * rayon / 0.75) > 0)
    if masques:      # objets de premier plan : remplacés par la médiane de l'anneau qui les entoure
        ra0, dec0, champ = centre
        n = d.shape[0]
        lig, col = np.mgrid[0:n, 0:n]
        for ra, dec, r in masques:
            x = (ra - ra0) * math.cos(math.radians(dec0)) / champ * n
            y = (dec - dec0) / champ * n
            c0, l0 = (n - 1) / 2 - x, (n - 1) / 2 - y
            dist = np.hypot(col - c0, lig - l0)
            rp = r / champ * n
            d = np.where(dist < rp, np.median(d[(dist >= rp) & (dist < 1.5 * rp)]), d)
    med = ndimage.median_filter(d, size=9)
    res = d - med
    sig = 1.4826 * np.median(np.abs(res))
    etoile = ndimage.binary_dilation(res > 5 * sig, iterations=2)
    d = np.where(etoile, med, d)
    # bruit du fond (hors galaxie) : retiré une fois et demie, pour que le ciel vide ne s'additionne pas en voile
    dehors = fenetre(d.shape[0], pa, incl, 1.15 * rayon / 0.75) <= 0
    bruit = 1.4826 * np.median(np.abs(d[dehors] - np.median(d[dehors]))) if dehors.any() else 0.0
    return d, bruit      # le bruit est retiré ensuite, le même pour les trois couleurs (sinon le voile prend une teinte)


def fenetre(n: int, pa: float, incl: float, echelle: float = 1.0, rayon: float = 0.75) -> np.ndarray:
    lig, col = (np.mgrid[0:n, 0:n] - (n - 1) / 2) / (n / 2)
    y, x = -lig, -col      # y vers le nord (haut de l'image), x vers l'est (gauche de l'image)
    # grand axe à l'angle PA depuis le nord vers l'est
    a = math.radians(pa)
    u = x * math.sin(a) + y * math.cos(a)
    v = x * math.cos(a) - y * math.sin(a)
    q = max(math.cos(math.radians(incl)), 0.35)
    r = np.hypot(u, v / q) / echelle
    t = np.clip((r - rayon) / (0.27 * rayon), 0, 1)
    w = 1 - t * t * (3 - 2 * t)
    return np.where(np.hypot(x, y) < 0.97, w, 0.0)


def main() -> None:
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    lignes = []
    for nom, corps, ra, dec, champ, pa, incl, mv, source in GALAXIES:
        if nom in MELLINGER:      # Nuages de Magellan : mosaïque de Mellinger (trois couleurs, plaques homogènes)
            chemins = [os.path.join(src, 'mellinger', f'{nom}_{k}.fits') for k in ('Red', 'Green', 'Blue')]
        else:
            chemins = [os.path.join(src, f'{nom}_{k}.fits') for k in ('r', 'b')]
        if not all(os.path.exists(c) for c in chemins):
            print(f'{nom} : images absentes, passée')
            continue
        try:
            ry = RAYON.get(nom, 0.75)
            lues = [bande(c, pa, incl, (ra, dec, champ), PREMIER_PLAN.get(nom, ()), ry) for c in chemins]
            plancher = 1.5 * max(b for _, b in lues)
            bandes = [np.clip(d - plancher, 0, None) for d, _ in lues]
        except (OSError, ValueError, TypeError) as e:
            print(f'{nom} : image illisible ({e}), passée')
            continue
        rvb = np.stack(bandes if len(bandes) == 3 else [bandes[0], 0.5 * (bandes[0] + bandes[1]), bandes[1]], -1)
        n = rvb.shape[0]
        rvb *= fenetre(n, pa, incl, 1.0, ry)[..., None]
        # DSS2 : même éclat moyen dans les trois bandes (les plaques n'ont pas la même sensibilité) ; Mellinger : couleurs telles quelles
        if nom not in MELLINGER:      # le vert du DSS2 est fabriqué : pas de couleur d'ensemble mesurée, on la garde neutre
            rvb /= np.maximum(rvb.reshape(-1, 3).sum(0), 1e-30) / rvb.reshape(-1, 3).sum(0).mean()
        img = np.stack([np.array(Image.fromarray(rvb[..., k].astype(np.float32)).resize((SORTIE, SORTIE), Image.BILINEAR)) for k in range(3)], -1)
        haut = np.percentile(img, 99.97)
        png = np.sqrt(np.clip(img / haut, 0, 1)) * 255
        Image.fromarray(png.astype(np.uint8)).save(os.path.join(out, f'{nom}.png'))
        releve = 'Mellinger 2009' if nom in MELLINGER else 'DSS2'
        lignes.append(f'{corps}	{nom}.png	{ra}	{dec}	{champ}	{pa}	{incl}	{mv}	{releve} (SkyView, NASA) ; {source}')
        print(f'{nom} : {n} px -> {SORTIE} px, haut d\'échelle {haut:.4g}')
    with open(os.path.join(out, 'galaxies_images.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lignes) + '\n')


if __name__ == '__main__':
    main()
