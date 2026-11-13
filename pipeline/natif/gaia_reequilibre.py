"""Rééquilibrage de l'éclat d'une direction à l'autre, vu de loin (docs/gaia-rayons.md, accord demandé à Marc le 12/11/2026).

Pourquoi : Gaia ne mesure pas la distance aussi loin dans toutes les directions (poussière proche, balayage du satellite). Vu de
loin, ces différences dessinent des rayons autour du Soleil. Mesuré : ni un tri plus strict, ni les distances de Bailer-Jones,
ni la poussière estimée par Gaia, ni un tri en volume ne les retirent.

Ce qui est fait : aucune étoile n'est ajoutée ni déplacée. Pour chaque case (tranche de magnitude absolue d'une magnitude,
coquille de 250 pc autour du Soleil, degré de longitude galactique, toutes latitudes ensemble), le nombre de sources est
comparé à sa moyenne glissante sur 61° de longitude. Le poids de chaque source
est ce rapport, borné entre 0,25 et 4.
HYPOTHÈSE (dite à l'écran) : à même distance et même type d'étoile, le nombre d'étoiles varie lentement d'une direction à l'autre.
Elle efface aussi les vraies structures plus petites que 60° à une distance donnée (amas : éclat ramené à la moyenne locale,
au plus 4 fois moins).
Mesuré sur les 98,3 M étoiles (scripts de mesure hors dépôt, eval_reeq.py et eval2.py), entre 2 et 4 kpc : rayons fins (1 à 15°)
0,046 -> 0,006 dex (hasard : 0,010), rayons larges (15 à 90°) 0,072 -> 0,030 ; 18 % de la lumière change de place (moitié en
plus, moitié en moins). Fenêtre de 15° : les rayons larges restaient (0,063), invisibles en moins dans l'appli ; 121° : 23 %.
Des cases plus fines (latitude découpée) bruitent le résultat : 33 à 39 % de la lumière bougerait, pour un gain nul.

Le poids est rangé en décalage de magnitude, Δm = -2,5 log10(poids), en millièmes de magnitude (entier 16 bits signé).
"""
import numpy as np
from scipy.ndimage import uniform_filter

LY_PER_PC = 3.2615638
# ICRS -> galactique (Hipparcos, ESA 1997, matrice A_G transposée)
A_GAL = np.array([[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132],
                  [+0.4941094278755837, -0.4448296299600112, +0.7469822444972189],
                  [-0.8676661490190047, -0.1980763734312015, +0.4559837761750669]])
N_L, N_B, N_SH, N_M = 360, 1, 40, 20
COQUILLE_PC, LISSAGE_L, LISSAGE_B = 250.0, 61, 1
POIDS_MIN, POIDS_MAX = 0.25, 4.0


def cles(u_icrs, d_pc, M):
    """Case de chaque source. u_icrs : directions (n, 3) dans le repère ICRS ; d_pc : distance ; M : magnitude absolue."""
    g = u_icrs @ A_GAL.T
    il = np.minimum((np.degrees(np.arctan2(g[:, 1], g[:, 0])) % 360).astype(np.int64), N_L - 1)
    ib = np.clip(((g[:, 2] + 1.0) * 0.5 * N_B).astype(np.int64), 0, N_B - 1)
    sh = np.clip((d_pc / COQUILLE_PC).astype(np.int64), 0, N_SH - 1)
    mb = np.clip(np.floor(M + 6.0).astype(np.int64), 0, N_M - 1)
    return ((mb * N_SH + sh) * N_B + ib) * N_L + il


def poids(cle, masse=None):
    """Poids de chaque source : (moyenne glissante de la case) / (contenu de la case), borné. masse : ce qu'on compte
    (None : le nombre de sources ; sinon par exemple la lumière d'une case de lumière additionnée)."""
    n = np.bincount(cle, masse, N_M * N_SH * N_B * N_L).reshape(N_M * N_SH, N_B, N_L).astype(np.float64)
    att = uniform_filter(n, size=(1, LISSAGE_B, LISSAGE_L), mode=('nearest', 'nearest', 'wrap'))
    w = np.where(n > 0, att / np.maximum(n, 1e-300), 1.0).ravel()[cle]
    return np.clip(w, POIDS_MIN, POIDS_MAX)


def decalage_mmag(w):
    """Δm en millièmes de magnitude (int16)."""
    return np.clip(np.rint(-2500.0 * np.log10(w)), -32767, 32767).astype(np.int16)
