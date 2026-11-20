#!/usr/bin/env python3
"""Ancres des galaxies voisines dans le film du Groupe local (film v2, natif/physique/film_v2.h).

Pourquoi (Marc, 20/11/2026) : « le Grand Nuage saccade et bouge sur place quand son orbite devient instable ; quand il est
absorbé, il disparaît ». Mesure faite sur le film installé (groupe-local-2) : tant que le Nuage garde un cœur, le centre
écrit par le calcul est à 0,1 kpc du centre de ses étoiles ; dès que le cœur est déchiré (vers +4 Ga, part des étoiles à
moins de 3 kpc : 0,35 -> 0,04), le centre écrit saute de 2 à 10 kpc d'une image à l'autre (10 millions d'années) et ne
s'accorde plus avec la vitesse écrite (écart jusqu'à 5 kpc par image). La caméra qui suit le Nuage sautait avec lui.

Ce script écrit, pour chaque image et chaque galaxie voisine, un point de suivi (« ancre ») tiré de SES étoiles :
  - centre de densité, par sphères qui rétrécissent (Power et al. 2003, MNRAS 338, 14, § 2.5), parti de l'ancre de
    l'image précédente ;
  - barycentre de toutes ses étoiles (toutes conservées : le film n'en retire aucune) ;
  - part groupée f : part des étoiles à moins de R_coeur du centre de densité (R_coeur = 2 x rayon médian à t = 0).
  ancre = w x centre de densité + (1 - w) x barycentre, w = lissé(f / f(t=0)) entre 0,1 et 0,5.
Tant que la galaxie a un cœur, l'ancre est ce cœur ; quand elle se disperse, l'ancre glisse sans bascule vers le
barycentre de ses étoiles, qui suit leur mélange avec la Voie lactée. C'est un CHOIX D'AFFICHAGE (où poser l'étiquette
et la caméra), pas une mesure ; les étoiles, elles, restent là où le calcul les a mises.

Format de sortie (petit-boutiste) : « UNIVANC1 », images n (u32), galaxies g (u32), puis par image et par galaxie :
ancre x, y, z (f64, kpc, repère et origine du film : centre de la Voie lactée), part groupée f (f64, 0 à 1),
barycentre x, y, z (f64). Galaxie 0 (Voie lactée) : zéros (origine du repère).

Usage : python ancres_film.py <dossier du film> <sortie film_ancres.bin>
"""
import struct
import sys

import numpy as np


def lire_index(d):
    b = open(d + '/film_index.bin', 'rb').read()
    assert b[:8] == b'UNIVFLM2', 'pas un film v2'
    n, g = struct.unpack_from('<II', b, 8)
    et = np.array(struct.unpack_from('<%dQ' % g, b, 16), dtype=np.int64)
    tete, par = 16 + 8 * g, 8 + 48 * g + 8
    t = np.array([struct.unpack_from('<d', b, tete + par * i)[0] for i in range(n)])
    c = np.array([struct.unpack_from('<%dd' % (3 * g), b, tete + par * i + 8) for i in range(n)]).reshape(n, g, 3)
    return n, g, et, t, c


def etoiles(d, i, debut, nombre):
    with open(d + '/img_%05d.f16' % i, 'rb') as f:
        f.seek(int(debut) * 6)
        raw = f.read(int(nombre) * 6)
    if len(raw) != nombre * 6:
        return None
    return np.frombuffer(raw, dtype='<f2').astype(np.float64).reshape(-1, 3)


def centre_densite(x, depart, r0, fin=1000, facteur=0.9):
    """Sphères qui rétrécissent (Power et al. 2003) : rayon multiplié par 0,9 jusqu'à ce qu'il reste `fin` étoiles."""
    c, r = depart.copy(), r0
    while True:
        m = np.einsum('ij,ij->i', x - c, x - c) < r * r
        if m.sum() < fin:
            return c
        x = x[m]      # la sphère suivante est dans celle-ci (à 10 % près) : on ne garde que ses étoiles, bien plus rapide
        c = x.mean(0)
        r *= facteur


def lisse(a, b, x):
    u = np.clip((x - a) / (b - a), 0.0, 1.0)
    return u * u * (3 - 2 * u)


def main():
    d, sortie = sys.argv[1], sys.argv[2]
    n, g, et, t, c = lire_index(d)
    debut = np.concatenate([[0], np.cumsum(et)])
    out = np.zeros((n, g, 7))
    # Réglages par galaxie, pris à t = 0 : rayon du cœur, rayon de départ des sphères, part groupée.
    regl = {}
    for k in range(1, g):
        x0 = etoiles(d, 0, debut[k], et[k]) + c[0, k]
        cd0 = centre_densite(x0, c[0, k], 2.0 * np.percentile(np.linalg.norm(x0 - c[0, k], axis=1), 90))
        r = np.linalg.norm(x0 - cd0, axis=1)
        regl[k] = [2.0 * np.median(r), 2.0 * np.percentile(r, 90), np.mean(r < 2.0 * np.median(r)), cd0]
    # Une seule lecture par image (toutes les voisines d'un coup) : les ouvertures de fichiers dominaient la durée.
    for i in range(n):
        tout = etoiles(d, i, debut[1], debut[g] - debut[1])
        if tout is None:      # image en cours d'écriture : on s'arrête là
            n = i
            break
        for k in range(1, g):
            r_coeur, r_depart, f0, precedent = regl[k]
            x = tout[debut[k] - debut[1]:debut[k + 1] - debut[1]] + c[i, k]
            cd = centre_densite(x, precedent, r_depart)
            f = float(np.mean(np.einsum('ij,ij->i', x - cd, x - cd) < r_coeur * r_coeur))
            bary = x.mean(0)
            w = float(lisse(0.1, 0.5, f / f0))
            out[i, k, :3] = w * cd + (1 - w) * bary
            out[i, k, 3] = f
            out[i, k, 4:] = bary
            regl[k][3] = cd
        if i % 100 == 0:
            print(f'  image {i}/{n}', flush=True)
    for k in range(1, g):
        print(f'galaxie {k} : {et[k]} étoiles, R_coeur {regl[k][0]:.2f} kpc, part groupée {regl[k][2]:.3f} -> {out[n - 1, k, 3]:.3f}', flush=True)
    out = out[:n]
    # Lissage dans le temps de l'ancre (gaussienne de 1,5 image = 15 Ma) là où la galaxie est dispersée : le centre de
    # densité d'un nuage sans cœur reste bruité. Poids du lissage = 1 - w (rien n'est lissé tant qu'il y a un cœur).
    k_t = np.arange(-5, 6)
    noyau = np.exp(-0.5 * (k_t / 1.5) ** 2)
    for k in range(1, g):
        a = out[:, k, :3].copy()
        sm = np.empty_like(a)
        for i in range(n):
            j = np.clip(i + k_t, 0, n - 1)
            sm[i] = (noyau[:, None] * a[j]).sum(0) / noyau.sum()
        f0 = out[0, k, 3] if out[0, k, 3] > 0 else 1.0
        w = lisse(0.1, 0.5, out[:, k, 3] / f0)[:, None]
        out[:, k, :3] = w * a + (1 - w) * sm
    with open(sortie, 'wb') as f:
        f.write(b'UNIVANC1' + struct.pack('<II', n, g))
        f.write(out.astype('<f8').tobytes())
    # contrôle : plus grande deuxième différence de l'ancre (kpc) avant et après, galaxie par galaxie
    for k in range(1, g):
        a2 = np.linalg.norm(out[2:, k, :3] - 2 * out[1:-1, k, :3] + out[:-2, k, :3], axis=1)
        c2 = np.linalg.norm(c[2:n, k] - 2 * c[1:n - 1, k] + c[:n - 2, k], axis=1)
        print(f'galaxie {k} : secousse (2e différence par image) centre écrit max {c2.max():.2f} médiane {np.median(c2):.3f} ; '
              f'ancre max {a2.max():.2f} médiane {np.median(a2):.3f} kpc')
    print('écrit', sortie, n, 'images')


if __name__ == '__main__':
    main()
