#!/usr/bin/env python3
"""Bras et anneaux MESURÉS des galaxies voisines (Andromède, Triangle, Grand et Petit Nuage), pour les étoiles jeunes
(composante 5) de etoiles_visibles_photos.py.

Pourquoi (Marc, 18/11/2026 : « Andromède ne ressemble pas à une spirale mais à un amas ») : les étoiles des voisines
étaient tirées de leur photo en lumière visible, puis remises à plat. Andromède est vue à 77° : la remise à plat étire
l'image 4,4 fois le long du petit axe et la poussière y cache les bras, si bien que le disque de départ était un ovale
lisse (amplitude des bras m = 2 : 0,10 dans le film v2, mesuré le 18/11/2026).

Ce module prend la forme des bras sur deux cartes qui suivent la formation d'étoiles et que la poussière ne cache pas :
- WISE 12 µm (bande W3 ; Wright et al. 2010) : poussière chauffée par les étoiles jeunes (bandes des PAH) ;
- GALEX ultraviolet lointain (Martin et al. 2005) : lumière des étoiles jeunes elles-mêmes.
Les deux sont lues dans les tuiles fines déjà faites pour l'appli (tuiles_bandes.py : pixel de 6,4″ à 26″ selon le
champ ; index sur le PC, paquets sur le Drive), dans le même champ que la photo (galaxies_images.tsv). Une carte absente
est ignorée ; sans aucune carte, rien ne change. (Le 18/11/2026, SkyView ne servait plus WISE et hips2fits du CDS était
hors service : d'où les tuiles.)

Ce qui est mesuré : la place des bras (dans le ciel, puis dans le plan du disque d'après l'angle de position et
l'inclinaison publiés) et la part de lumière qui n'est pas répartie en anneau lisse (mesurée sur la photo).
Ce qui est supposé [modèle] : l'épaisseur des bras, la température des étoiles jeunes, la part de régions HII.
"""
import math
import os

import numpy as np
from scipy import ndimage

# clé, relevé des tuiles fines (tuiles_bandes.py), description
CARTES = (('w3', 'wise12', 'WISE 12 µm (AllWISE, Wright et al. 2010)'),
          ('fuv', 'galexfuv', 'GALEX ultraviolet lointain (GR6, Martin et al. 2005)'))
PIXELS = 1500      # grille de la carte lue, sur le champ de la photo
COUVERTURE_MIN = 0.98      # part de la galaxie que le relevé doit couvrir pour servir (GALEX ne couvre qu'une partie de M31 et des Nuages)
# Galaxies satellites vues devant Andromède : ce ne sont pas des étoiles de son disque. RA, Dec, rayon (°)
# [positions NED ; rayons : un peu plus que le diamètre visible sur la photo DSS2].
SATELLITES = {'andromede': [(10.6743, 40.8652, 0.07), (10.0921, 41.6853, 0.17)]}      # M32, NGC 205 (M110)


TUILE_LARGEUR = 512      # tuiles_bandes.py : 512 × 512 pixels HEALPix par tuile
TUILE_GROUPE = 3         # 4^3 = 64 tuiles par paquet


def ordre_pour(champ: float, pixels: int) -> int:
    """Ordre de tuile (4 à 6) dont le pixel est le plus proche du pixel de la grille, sans être plus gros."""
    grille = champ * 3600 / pixels                         # secondes d'arc
    for k in (4, 5, 6):
        if 58.63 * 3600 / (TUILE_LARGEUR * 2 ** k) <= grille:
            return k
    return 6


def lire_tuiles(index: str, paquets: str, releve: str, ra0: float, dec0: float, champ: float, pixels: int) -> np.ndarray | None:
    """Carte du relevé (tuiles fines UNIVTIL2 de tuiles_bandes.py : index sur le PC, paquets sur le Drive) sur une grille
    gnomonique centrée en (ra0, dec0), champ en degrés, nord en haut, est à gauche (mêmes conventions que la photo).
    Valeurs en unité du relevé multipliée par le facteur float16 (sans effet ici : seule la forme compte).
    None si l'index ou les paquets manquent."""
    from astropy_healpix import HEALPix
    import astropy.units as u
    k = ordre_pour(champ, pixels)
    chemin_idx = os.path.join(index, releve, f'ordre_{k}.idx')
    if not os.path.exists(chemin_idx):
        return None
    b = open(chemin_idx, 'rb').read()
    if b[:8] != b'UNIVTIL2':
        return None
    pos = np.frombuffer(b, '<u4', offset=24)
    w2 = TUILE_LARGEUR ** 2
    # direction de chaque pixel de la grille
    ra, dec = math.radians(ra0), math.radians(dec0)
    u0 = np.array([math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)])
    est = np.array([-math.sin(ra), math.cos(ra), 0.0]); nord = np.cross(u0, est)
    demi = math.tan(math.radians(champ) / 2)
    c = (np.arange(pixels) + 0.5) / pixels
    eta, xi = np.meshgrid((0.5 - c) * 2 * demi, (0.5 - c) * 2 * demi, indexing='ij')
    d = u0[None, None] + xi[..., None] * est + eta[..., None] * nord
    d /= np.linalg.norm(d, axis=-1)[..., None]
    lon, lat = np.arctan2(d[..., 1], d[..., 0]), np.arcsin(np.clip(d[..., 2], -1, 1))
    ipix = HEALPix(nside=TUILE_LARGEUR * 2 ** k, order='nested').lonlat_to_healpix(lon * u.rad, lat * u.rad)
    tuile, dedans = ipix // w2, ipix % w2
    out = np.full(ipix.shape, np.nan, np.float64)
    for t in np.unique(tuile):
        p = int(pos[t])
        if p == 0:
            continue      # tuile absente du relevé
        chemin = os.path.join(paquets, releve, f'ordre_{k}', f'p{t >> (2 * TUILE_GROUPE):06d}.bin')
        try:
            with open(chemin, 'rb') as f:
                f.seek((p - 1) * w2 * 2)
                v = np.frombuffer(f.read(w2 * 2), '<f2').astype(np.float64)
        except OSError:
            return None
        if len(v) != w2:
            return None
        m = tuile == t
        out[m] = v[dedans[m]]
    return out


def nettoyer(d: np.ndarray) -> np.ndarray | None:
    """Fond retiré, sources ponctuelles (étoiles de la Voie lactée) effacées. None si rien d'utilisable."""
    d = np.nan_to_num(d, nan=0.0)
    if not np.any(d):
        return None
    med = ndimage.median_filter(d, size=9)
    res = d - med
    sig = 1.4826 * np.median(np.abs(res)) + 1e-30
    d = np.where(ndimage.binary_dilation(res > 5 * sig, iterations=2), med, d)
    bord = np.concatenate([d[:40].ravel(), d[-40:].ravel(), d[:, :40].ravel(), d[:, -40:].ravel()])
    fond = np.median(bord)
    bruit = 1.4826 * np.median(np.abs(bord - fond))
    d = np.clip(d - fond - 2.0 * bruit, 0, None)
    return d if d.sum() > 0 else None


def combler_satellites(img: np.ndarray, nom: str, ra0: float, dec0: float, champ: float) -> np.ndarray:
    """Copie de l'image (nord en haut, est à gauche ; 2 ou 3 dimensions) où chaque galaxie satellite vue devant le disque
    est remplacée par la médiane de l'anneau qui l'entoure (même geste que galaxies_images.py pour les amas devant les
    Nuages) : le disque continue derrière elle, sans trou."""
    out = img.copy()
    h, w = img.shape[:2]
    lig, col = np.mgrid[0:h, 0:w]
    for ra, dec, r in SATELLITES.get(nom, ()):
        x = (ra - ra0) * math.cos(math.radians(dec0)) / champ * w
        y = (dec - dec0) / champ * h
        dist = np.hypot(col - ((w - 1) / 2 - x), lig - ((h - 1) / 2 - y))
        rp = r / champ * w
        dedans, anneau = dist < rp, (dist >= rp) & (dist < 1.5 * rp)
        out[dedans] = np.median(img[anneau], axis=0)
    return out


def part_hors_anneaux(R: np.ndarray, phi: np.ndarray, rmax: float) -> float:
    """Part des traceurs (tirés de la photo, déjà dans le plan du disque) qui n'est pas répartie en anneau lisse :
    par anneau de rayon, ce qui dépasse la médiane des secteurs d'angle. C'est la lumière des bras, des anneaux
    irréguliers et des amas jeunes, mesurée sur la photo elle-même."""
    if len(R) == 0:
        return 0.0
    H, _, _ = np.histogram2d(R, phi, bins=[np.linspace(0, rmax, 41), np.linspace(-math.pi, math.pi, 37)])
    exces = np.clip(H - np.median(H, axis=1, keepdims=True), 0, None)
    return float(exces.sum() / max(len(R), 1))


def tirer(cartes: dict[str, np.ndarray], n: int, rng: np.random.Generator):
    """n points tirés au prorata de la lumière des cartes (chaque carte compte pour moitié quand les deux sont là).
    Rend (ligne, colonne) en fractions de la hauteur et de la largeur, et le nom de la carte de chaque point."""
    noms = [k for k in cartes]
    parts = rng.multinomial(n, [1.0 / len(noms)] * len(noms))
    lig, col, de = [], [], []
    for k, m in zip(noms, parts):
        c = cartes[k]
        h, w = c.shape
        idx = rng.choice(h * w, m, p=(c / c.sum()).ravel())
        lig.append((idx // w + rng.uniform(0, 1, m)) / h)
        col.append((idx % w + rng.uniform(0, 1, m)) / w)
        de.append(np.full(m, k))
    return np.concatenate(lig), np.concatenate(col), np.concatenate(de)


def temperature(de: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Température des étoiles jeunes [modèle] : ultraviolet lointain -> étoiles O et B (10 000 à 25 000 K) ; 12 µm ->
    une sur trois en région HII (2400 K, convention de l'appli pour le rouge Hα), les autres étoiles A et B (8000 à
    15 000 K). Rend (température, est_HII)."""
    n = len(de)
    t = np.where(de == 'fuv', rng.uniform(10000, 25000, n), rng.uniform(8000, 15000, n))
    hii = (de == 'w3') & (rng.uniform(0, 1, n) < 1 / 3)
    return np.where(hii, 2400.0, t), hii
