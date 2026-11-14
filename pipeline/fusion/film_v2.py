#!/usr/bin/env python3
"""Lecteur du film version 2 écrit par rencontre.py (mode « futur ») : les étoiles visibles suivies par le calcul.

    from film_v2 import Film
    f = Film('C:/tmp/natif/groupe-local/film', traceurs='C:/tmp/natif/donnees/etoiles-visibles')
    f.t                       # dates des images, Ga (0 = aujourd'hui)
    f.galaxies                # ['voie_lactee', 'andromede', 'triangle', 'grand_nuage', 'petit_nuage']
    f.centre(g, i)            # centre de la galaxie g à l'image i, relatif à la Voie lactée, kpc
    f.vitesse_centre(g, i)    # km/s
    f.positions(g, i)         # (n_g, 3) float32, kpc, RELATIVES AU CENTRE DE LA GALAXIE g
    f.vitesses(g, i)          # (n_g, 3) km/s, par différence entre les images voisines (le film ne garde pas les vitesses)
    f.poids(g)                # lumière de chaque étoile visible (champ « lum » du fichier fourni), si `traceurs` est donné
    f.position_a(g, t)        # positions à une date quelconque : courbe passant par les quatre images voisines

Le fichier d'une image, img_NNNNN.f16, contient pour chaque étoile visible, dans l'ordre des fichiers
etoiles_visibles_<galaxie>.npz (docs/contrat-etoiles-visibles.md), galaxie après galaxie, trois nombres à virgule sur
16 bits : sa position relative au centre de sa galaxie d'origine. Une étoile arrachée reste rapportée à sa galaxie d'origine.
"""
import json
import os

import numpy as np

KPC_GA_EN_KMS = 1.0 / 1.0227121650456      # 1 kpc/Ga = 0,9778 km/s


class Film:
    def __init__(self, dossier, traceurs=None):
        self.dossier, self.traceurs = dossier, traceurs
        meta = json.load(open(os.path.join(dossier, 'film.json'), encoding='utf-8'))
        journal = json.load(open(os.path.join(dossier, 'journal.json'), encoding='utf-8'))
        self.meta = meta
        self.galaxies = meta['galaxies']
        self.n = list(meta['traceurs'])
        self.debut = np.concatenate([[0], np.cumsum(self.n)])
        k = min(len(meta['t']), len(journal['t']))
        self.t = np.array(meta['t'][:k])
        self._centres = np.array(journal['centres'][:k]); self._vitesses = np.array(journal['vitesses'][:k])
        self.energie = np.array(journal['energie'][:k])
        self._lum = {}

    def __len__(self):
        return len(self.t)

    def centre(self, g, i):
        return self._centres[i, g]

    def vitesse_centre(self, g, i):
        return self._vitesses[i, g]

    def _image(self, i):
        return np.memmap(os.path.join(self.dossier, f'img_{i:05d}.f16'), dtype=np.float16, mode='r').reshape(-1, 3)

    def positions(self, g, i):
        return np.asarray(self._image(i)[self.debut[g]:self.debut[g + 1]], dtype=np.float32)

    def vitesses(self, g, i):
        a, b = max(i - 1, 0), min(i + 1, len(self.t) - 1)
        return (self.positions(g, b) - self.positions(g, a)) / (self.t[b] - self.t[a]) * KPC_GA_EN_KMS

    def poids(self, g):
        if g not in self._lum:
            with np.load(os.path.join(self.traceurs, f'etoiles_visibles_{self.galaxies[g]}.npz')) as z:
                self._lum[g] = z['lum'][:self.n[g]].astype(np.float32)
        return self._lum[g]

    def position_a(self, g, t):
        """Positions à la date t (Ga) : courbe de Catmull-Rom par les quatre images voisines (pas de ligne droite)."""
        i = int(np.clip(np.searchsorted(self.t, t) - 1, 0, len(self.t) - 2))
        u = (t - self.t[i]) / (self.t[i + 1] - self.t[i])
        p0, p1, p2, p3 = (self.positions(g, int(np.clip(k, 0, len(self.t) - 1))) for k in (i - 1, i, i + 1, i + 2))
        return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


def ecrire_index(dossier):
    """Index binaire pour l'appli (qui ne lit pas le JSON) : film_index.bin, petit-boutiste.
    « UNIVFLM2 » (8 octets), nombre d'images (u32), nombre de galaxies (u32), puis par galaxie le nombre d'étoiles visibles
    (u64), puis par image : date en Ga (f64), centre de chaque galaxie relatif à la Voie lactée (3 f64 chacun, kpc),
    vitesse de chaque centre (3 f64 chacun, km/s), écart d'énergie (f64)."""
    import struct
    f = Film(dossier)
    g = len(f.galaxies)
    out = [b'UNIVFLM2', struct.pack('<II', len(f), g), struct.pack(f'<{g}Q', *f.n)]
    for i in range(len(f)):
        out.append(struct.pack('<d', float(f.t[i])) + np.asarray(f._centres[i], '<f8').tobytes() + np.asarray(f._vitesses[i], '<f8').tobytes() + struct.pack('<d', float(f.energie[i])))
    tmp = os.path.join(dossier, 'film_index.bin.tmp')
    with open(tmp, 'wb') as fh: fh.write(b''.join(out))
    os.replace(tmp, os.path.join(dossier, 'film_index.bin'))


if __name__ == '__main__':
    import sys
    f = Film(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(len(f), 'images, de', f.t[0], 'à', f.t[-1], 'Ga ; étoiles visibles par galaxie :', dict(zip(f.galaxies, f.n)))
    for g, nom in enumerate(f.galaxies):
        if f.n[g]:
            p = f.positions(g, len(f) - 1)
            print(f'  {nom:12s} centre {np.round(f.centre(g, len(f) - 1), 1)} kpc ; rayon médian des étoiles {np.median(np.linalg.norm(p, axis=1)):.2f} kpc')
