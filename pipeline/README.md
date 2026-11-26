# Pipeline de préparation et de contrôle des données (`pipeline/`)

Ce dossier regroupe les scripts Python et Node.js qui préparent, convertissent et vérifient les données astronomiques, cosmologiques, quantiques et N-corps consommées par l'application web (`app/gen/`) et l'application native PC (`natif/`).

## 1. Chemins portables (`pipeline/_paths.py` et `UNIVERS_RAW`)

Tous les scripts actifs et les scripts historiques mis à jour résolvent les chemins du dépôt via [`pipeline/_paths.py`](_paths.py) (100 % bibliothèque standard), indépendamment du répertoire courant (CWD) et du système d'exploitation :

- `REPO_ROOT`, `PIPELINE_DIR`, `PIPELINE_RAW` (`pipeline/raw/`), `PIPELINE_REF` (`pipeline/ref/`)
- `APP_DIR` (`app/`), `APP_GEN` (`app/gen/`), `APP_SRC` (`app/src/`), `APP_TEST` (`app/test/`)
- `raw_dir(cli_arg=None)` pour les données brutes volumineuses hors dépôt (Cosmicflows-4, Planck SMICA, GWOSC, Laniakea FITS, OpenNGC, tuiles), résolues dans cet ordre de priorité :
  1. argument CLI explicite (ex. `python3 pipeline/sources/build_cf4.py /chemin/vers/raw`) ;
  2. variable d'environnement `UNIVERS_RAW` ;
  3. repli portable `<racine_du_dépôt>/univers-raw`.
- `read_tile_manifest()` : lit `/*__TILES__*/` dans `app/src/6*.js` (tolère le formatage multi-lignes, guillemets simples/doubles, virgules finales et découpage des fichiers source).
- `data_keys()` & `RETIRE_DATA2` : lit les clés de `DATA` dans `app/gen/data*.js` dans l'ordre exact de `app/build.py`, en ignorant de manière idempotente les 5 clés héritées de `data2.js` (`STARS_N`, `STARS_GEO`, `STARS_AUX`, `STAR_LABELS`, `CMB`).

## 2. Profils de dépendances (`pyproject.toml` et `requirements-ci.txt`)

Les dépendances sont déclarées dans [`pipeline/pyproject.toml`](pyproject.toml) (`requires-python = ">=3.10"`).

| Profil | Paquets | Scripts couverts |
|---|---|---|
| **Stdlib seule** (`requirements-ci.txt`) | *aucun paquet tiers* | Tests CI (`test_pipeline_stdlib.py`, `sources/test_build_gw.py`), `build_{bbcol,zcol,sun_rgb,enc,lgv}.py`, `sources/{build_cf4,build_gw,build_openngc,test_build_cf4,test_build_gw}.py`, `etoiles/*.py`, `gravite/*.py`, `natif/{controle_orientation,fusion_bin,lunes,nbody_donnees,ref_asteroides,ref_ephem}.py`, `fusion/{exporter_images,exporter_page}.py` |
| `core` | `numpy`, `pillow`, `requests`, `pandas` | `natif/{etoiles,asteroides,galaxies,planetes,test_etoiles}.py`, `quantique/proton_pdf.py`, scripts de collecte et tuiles (`fetch*`, `get_*`, `simbad*`, `build_tiles.py`, `build_probes2.py`) |
| `astro` | `numpy`, `pillow`, `pandas`, `astropy`, `astropy-healpix`, `scipy`, `scikit-image`, `pymeeus`, `jplephem` | `build_dust.py`, `sources/build_{cmb_planck,laniakea}.py`, `build_data{,2,3,4}.py`, `build_ephem.py` |
| `quantum` | `numpy`, `pyscf` | `quantique/eau_pyscf.py` |
| `fusion-cpu` | `numpy`, `scipy`, `agama`, `pyfalcon`, `playwright` | `fusion/{exporter_conditions,modeles,essai,calcul}.py` *(note : `agama` et `pyfalcon` sont compilés depuis leurs dépôts GitHub en CI — voir `.github/workflows/fusion-*.yml`)* |
| `fusion-gpu` | `numpy`, `scipy`, `agama`, `cupy-cuda12x[ctk]`, `playwright` | `fusion/{calcul.py --gpu,gravite_gpu.py,test_gravite_gpu.py,exporter_conditions.py}` |

## 3. Pipelines de production actifs

- **Tables physiques et optiques (racine `pipeline/`)** :
  - `build_bbcol.py` → `app/gen/data15.js` (corps noir CIE 1931, rejouable hors ligne via `pipeline/ref/ciexyz31_1.csv`)
  - `build_zcol.py` → `app/gen/data16.js` (couleurs galaxies/quasars selon *z*, rejouable via `pipeline/ref/`)
  - `build_dust.py` → `app/gen/data20.js` (carte 3D poussière Edenhofer 2024, profil `astro`)
  - `build_sun_rgb.py` → `app/gen/sun_rgb.js` (branche des géantes rouges MIST v1.2, rejouable via `pipeline/raw/mist_v1.2_feh0_00100M.track.eep`)
- **`pipeline/sources/`** (catalogues cosmologiques et recherche) : `build_cf4.py` (`data17.js`), `build_gw.py` (`data18.js`), `build_cmb_planck.py` (`data19.js`), `build_laniakea.py` (`laniakea.js`), `build_openngc.py` (`<raw>/openngc.json`), tests `test_build_cf4.py` et `test_build_gw.py`.
- **`pipeline/natif/`** (convertisseurs binaires et références pour l'appli PC `natif/`) : `etoiles.py` (+ `test_etoiles.py`), `asteroides.py` (+ `ref_asteroides.py`), `galaxies.py`, `planetes.py`, `lunes.py`, `fusion_bin.py`, `nbody_donnees.py`, `ref_ephem.py`, `controle_orientation.py`.
- **`pipeline/fusion/`** (simulation N-corps Voie lactée – Andromède – Triangle – LMC) : `exporter_conditions.py` → `conditions.json`, `modeles.py`, `essai.py`, `calcul.py`, `gravite_gpu.py` (+ `test_gravite_gpu.py`), `exporter_page.py`, `exporter_images.py`.
- **`pipeline/quantique/`** (échelles subatomiques) : `eau_pyscf.py` → `app/gen/water_qm.js` (`quantum`), `proton_pdf.py` → `app/gen/proton_pdf.js` (`core` / NumPy 1.x et 2.x).
- **`pipeline/gravite/`** (gravité N-corps, table longue ±10 Ma, transits, références JPL Horizons) : 6 scripts Node.js (`ajuste.js`, `ajuste_lunes.js`, `build_long.js`, `build_transits.js`, `compare_la2004.js`, `long.js`) + 4 scripts Python stdlib (`build_transits_ref.py`, `fetch_horizons.py`, `fetch_lunes.py`, `fetch_petits.py`).
- **`pipeline/etoiles/`** (âges/masses Gaia FLAME & durées de vie MIST) : `fetch_flame.py`, `build_flame.py`, `build_mist_life.py`.
- **Données locales suivies** : `pipeline/raw/` (11 fichiers légers versionnés), `pipeline/ref/` (5 spectres/CMFs de référence), `pipeline/tex/` (12 textures planètes et Voie lactée).

## 4. Scripts historiques (phase initiale — référence conservée)

Ces scripts proviennent de la construction initiale et restent conservés comme référence pour les requêtes, formats et sources :

- `build_data.py`, `build_data2.py`, `build_data3.py`, `build_data4.py`, `build_ephem.py`, `build_enc.py`, `build_lgv.py`, `build_probes2.py`, `build_tiles.py` (mis à jour vers `pipeline/_paths.py`, sans chemins obsolètes ni exécution dynamique de code ; la plupart nécessitent le dossier brut historique non versionné de ~1,2 Go).
- `fetch2.py`, `fetch3.py`, `fetch_all.py`, `fetch_details.py`, `fetch_enc.py`, `fetch_esa.py`, `fetch_far.py`, `fetch_gaia.py`, `fetch_gal.py`, `fetch_more.py`, `fetch_prec.py`, `fetch_probes2.py`, `fetch_tiles.py`, `fetch_tiles2.py`, `get_galaxies.py`, `get_stars.py`, `simbad.py`, `simbad2.py`, `simbad_dist.py`, `try_desi.py`.
- *Transparence* : 7 modules `app/gen/data{5,6,7,8,9,11,12}.js` issus de cette première étape n'ont pas de script générateur dédié dans `pipeline/`.

## 5. Tests CI sans dépendance tierce

Exécutables depuis n'importe quel répertoire courant avec Python 3.10+ (0 paquet tiers, 0 accès réseau) :

```bash
python3 pipeline/sources/test_build_gw.py
python3 pipeline/test_pipeline_stdlib.py
```
