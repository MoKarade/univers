# Préparation des données

Ces scripts ont été écrits au fil d'une conversation, chacun pour une étape. Ils ne forment pas une chaîne rejouable d'un seul geste : chemins codés en dur, dossier `raw/` de 1,2 Go non versé ici, serveurs parfois injoignables. Ils servent de référence pour les requêtes, les formats et les sources.

- `build_data*.py`, `build_ephem.py` : fabriquent `app/gen/data*.js` et `ephem.js`.
- `fetch_gaia.py`, `fetch_tiles*.py`, `build_tiles.py`, `get_stars.py` : étoiles Gaia en flux.
- `try_desi.py`, `fetch_far.py`, `get_galaxies.py` : galaxies des grands relevés.
- `fetch_gal.py` : photos de galaxies (Legacy Survey, DSS).
- `fetch_probes2.py`, `build_probes2.py` : trajectoires des sondes (JPL Horizons).
- `fetch_details.py`, `fetch_prec.py`, `fetch_more.py`, `simbad*.py` : compléments (lunes, comètes, étoiles nommées).
- `tex/` : cartes des planètes et panorama de la Voie lactée d'origine.

Pour la mission 2, mieux vaut réécrire une chaîne propre en s'appuyant sur ces requêtes que tenter de rejouer ces fichiers.
