#!/usr/bin/env python3
"""Étoiles jeunes et régions HII de la Voie lactée, en points 3D -> jeunes_vl.bin (natif/src/voie_lactee_etoiles.h).

La Voie lactée de l'appli est faite d'étoiles : Gaia là où il mesure, et au-delà les particules du calcul de la Galaxie
(fusion-toutes, les mêmes qui évoluent quand on avance le temps). Ces particules forment un disque lisse : les bras d'une
galaxie spirale sont surtout de la LUMIÈRE d'étoiles jeunes et bleues, peu de masse. Ce script place ces étoiles jeunes :
- le long des bras MESURÉS de Reid et al. 2019 (masers à parallaxe), et de leurs prolongements EXTRAPOLÉS (atténués),
  même géométrie que voie_lactee.py (bras_geometrie) ;
- dans et autour des 1 413 régions HII du catalogue WISE qui ont une distance (Anderson et al. 2014), à leur place et à
  leur taille mesurées : quelques étoiles bleues et la lueur rose du gaz ionisé.
Part de la lumière du disque portée par ces étoiles jeunes : PART_JEUNES [Supposition dans la fourchette publiée en
bande V, 10 à 20 %] ; la lumière des particules du disque est diminuée d'autant dans l'appli (rien n'est compté deux fois).
Près du Soleil, Gaia mesure déjà les étoiles jeunes : rien n'est placé à moins de 1,5 kpc, en fondu jusqu'à 3 kpc.
Tirage déterministe (graine fixe).

Repère : galactocentrique (x du Soleil vers le centre, y vers la longitude 90°, z vers le pôle nord), kpc, centre à
l'origine, Soleil en (-R0, 0, 0) comme le calcul de la fusion.
Format (petit-boutiste) : « UNIVYNG1 », n (u32), part de la lumière du disque portée (f32), réservé jusqu'à 64 octets ;
puis n × (x, y, z en f32 kpc ; magnitude absolue V en f32 ; couleur RVBA en 4 octets).
Usage : python voie_lactee_jeunes.py <wise_hii.tsv> <sortie.bin>
"""
import math
import struct
import sys

import numpy as np

import voie_lactee as v

PART_JEUNES = 0.15            # part de la lumière du disque des particules portée par les étoiles jeunes [Supposition]
N_BRAS = 300_000              # étoiles jeunes le long des bras
N_PAR_HII = 24                # points par région HII (étoiles bleues et gaz rose)
PART_HII = 0.12               # part de la lumière jeune montrée en gaz rose des régions HII [modèle d'affichage]
H_Z = 0.07                    # kpc : épaisseur des étoiles jeunes (50 à 100 pc publiés)
PRES_DU_SOLEIL = (1.5, 3.0)   # kpc : Gaia mesure déjà les étoiles jeunes ici
L_DISQUE_V = 3.45e10 * 0.9    # L_sol : lumière V du disque (Licquia et al. 2015, M_V = -21,51 ; bulbe et barre retirés ~10 %)
M_SOL_V = 4.83
BLEU = (150, 185, 255, 255)
BLEU_BLANC = (205, 220, 255, 255)
ROSE = (255, 80, 135, 255)


def tirer_bras(rng, n):
    """Points le long des bras (mesurés et extrapolés), densité = poids du bras x disque mince exp(-R/2,6 kpc)."""
    cand = []
    for nom, bmin, bmax, bk, rk, pin, pout, w in v.BRAS:
        beta = np.arange(-400.0, 400.0, 0.02)
        Rb, psi, larg, poids, mesure = v.bras_geometrie(nom, bmin, bmax, bk, rk, pin, pout, w, beta)
        poids = np.where(mesure, poids, v.PART_PROLONGE * poids)
        ok = (poids > 0.01) & (Rb > 2.5) & (Rb < 16.0)
        ds = np.radians(0.02) * Rb / np.cos(psi)          # longueur d'arc de chaque pas
        p = np.where(ok, poids * np.exp(-Rb / 2.6) * ds * larg, 0.0)
        cand.append((beta[ok], Rb[ok], psi[ok], larg[ok], p[ok]))
    beta = np.concatenate([c[0] for c in cand]); R = np.concatenate([c[1] for c in cand])
    larg = np.concatenate([c[3] for c in cand]); p = np.concatenate([c[4] for c in cand])
    k = rng.choice(len(p), n, p=p / p.sum())
    th = np.radians(180.0 - beta[k])
    r = R[k] + rng.normal(0.0, 1.0, n) * larg[k]
    th = th + rng.normal(0.0, 1.0, n) * 0.6 * larg[k] / np.maximum(R[k], 1.0)      # un peu de grain le long du bras
    return np.stack([r * np.cos(th), r * np.sin(th), rng.laplace(0.0, H_Z, n)], 1)


def main():
    wise, sortie = sys.argv[1], sys.argv[2]
    rng = np.random.default_rng(2019)
    sun = np.array([-v.R0, 0.0, 0.0])
    pos_b = tirer_bras(rng, N_BRAS)
    regions = v.regions_hii(wise, sun)
    pos_h, rose = [], []
    for x, y, z, rk in regions:
        n = N_PAR_HII
        pos_h.append(np.array([x, y, z]) + rng.normal(0.0, 1.0, (n, 3)) * max(rk, 0.03))
        rose.append(np.arange(n) < n // 2)        # moitié gaz rose, moitié étoiles bleues
    pos_h = np.concatenate(pos_h); rose = np.concatenate(rose)
    pos = np.concatenate([pos_b, pos_h])
    # lumière : partagée entre les points ; chaque point jeune un peu différent (fonction de luminosité raide) [modèle]
    l_tot = PART_JEUNES * L_DISQUE_V
    w = rng.pareto(1.5, len(pos)) + 1.0
    w[len(pos_b):][rose] *= 3.0
    dsun = np.linalg.norm(pos - sun, axis=1)
    attenue = v._rampe(dsun, *PRES_DU_SOLEIL)                 # Gaia mesure déjà ici
    L = l_tot * w / w.sum()
    L *= attenue
    garde = L > 0
    pos, L = pos[garde], L[garde]
    col = np.array([BLEU] * N_BRAS + [ROSE if r else BLEU_BLANC for r in rose], np.uint8)[garde]
    col[:min(N_BRAS, len(col))][rng.uniform(size=min(N_BRAS, len(col))) < 0.3] = BLEU_BLANC
    mag = M_SOL_V - 2.5 * np.log10(L)
    with open(sortie, 'wb') as f:
        h = b'UNIVYNG1' + struct.pack('<If', len(pos), PART_JEUNES)
        f.write(h + b'\0' * (64 - len(h)))
        rec = np.zeros(len(pos), np.dtype([('p', '<f4', 3), ('m', '<f4'), ('c', 'u1', 4)]))
        rec['p'] = pos; rec['m'] = mag; rec['c'] = col
        f.write(rec.tobytes())
    print(f'{len(pos)} points jeunes ({N_BRAS} le long des bras, {len(regions)} régions HII), lumière {L.sum():.3e} L_sol '
          f'sur {l_tot:.3e} (le reste est mesuré par Gaia près du Soleil) -> {sortie}')


if __name__ == '__main__':
    main()
