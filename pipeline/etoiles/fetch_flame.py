#!/usr/bin/env python3
"""Âges et masses mesurés par Gaia DR3 (module FLAME, Gaia Collaboration, Creevey et al. 2023) pour les étoiles Hipparcos,
par la table de correspondance gaiadr3.hipparcos2_best_neighbour. Archive de l'ESA (TAP).
Écrit pipeline/raw/flame_hip.csv : hip, age_flame (Ga) et bornes à 16 % et 84 %, mass_flame (M☉) et bornes, flags_flame, evolstage_flame."""
import os, urllib.parse, urllib.request
Q = ("SELECT h.original_ext_source_id AS hip, a.age_flame, a.age_flame_lower, a.age_flame_upper, a.mass_flame, a.mass_flame_lower, "
     "a.mass_flame_upper, a.flags_flame, a.evolstage_flame FROM gaiadr3.hipparcos2_best_neighbour AS h "
     "JOIN gaiadr3.astrophysical_parameters AS a ON a.source_id = h.source_id WHERE a.age_flame IS NOT NULL")
d = urllib.parse.urlencode({'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'csv', 'MAXREC': 200000, 'QUERY': Q}).encode()
t = urllib.request.urlopen(urllib.request.Request('https://gea.esac.esa.int/tap-server/tap/sync', data=d), timeout=600).read().decode()
dst = os.path.join(os.path.dirname(__file__), '..', 'raw', 'flame_hip.csv')
open(dst, 'w').write(t); print('écrit', dst, t.count('\n') - 1, 'étoiles')
