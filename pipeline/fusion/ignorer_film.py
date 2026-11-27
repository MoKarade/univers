#!/usr/bin/env python3
"""Liste des traceurs d'un film (format 3) que l'appli ne doit pas dessiner : étoiles visibles du bulbe d'Andromède
posées sur des particules de masse aberrantes (bulbe de Hernquist sans coupure : queue jusqu'à des mégaparsecs).
Corrigé à la source pour les prochains films (etoiles_visibles_voisines_masse.py, RAYON_BULBE_KPC) ; ce script rattrape
les films déjà calculés. Écrit <film>/ignorer.bin : rangs dans P (entiers 32 bits non signés, triés), et le note dans
film.json (clé « ignorer »).
Usage : python ignorer_film.py <dossier du film> <dossier des étoiles visibles> [rayon en kpc, 10 par défaut]"""
import json
import os
import sys

import numpy as np

import film_v3 as F

film, etoiles = sys.argv[1], sys.argv[2]; rayon = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
f = F.Film(film); m = f.meta; p0, _ = f.image(0)
g = m['galaxies'].index('andromede'); sl = f.bloc(F.FAM_P, F.TYPE_VISIBLES, g)
comp = np.load(os.path.join(etoiles, 'etoiles_visibles_andromede.npz'))['comp']
r = np.linalg.norm(p0[sl], axis=1)
rangs = (sl.start + np.where((comp == 2) & (r > rayon))[0]).astype('<u4')
F.ecrire_fichier(os.path.join(film, 'ignorer.bin'), rangs)
m['ignorer'] = dict(fichier='ignorer.bin', nombre=int(len(rangs)), raison=f"étoiles du bulbe d'Andromède posées à plus de {rayon:g} kpc du centre (modèle de bulbe sans coupure) : ne pas dessiner")
json.dump(m, open(os.path.join(film, 'film.json.tmp'), 'w', encoding='utf-8'), ensure_ascii=False); os.replace(os.path.join(film, 'film.json.tmp'), os.path.join(film, 'film.json'))
print(f"{len(rangs)} traceurs à ignorer sur {int((comp == 2).sum())} étoiles du bulbe d'Andromède (au-delà de {rayon:g} kpc ; le plus loin : {r[comp == 2].max():.0f} kpc)")
