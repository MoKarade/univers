# Crédits des données et des images

Univers s'appuie sur des données et des images publiées par d'autres. Ce fichier les crédite et indique leur licence quand elle est connue. Les fichiers marqués « dans le dépôt » sont versionnés ici. Les autres sont téléchargés par les scripts de `pipeline/` puis intégrés aux fichiers générés (`app/gen/`, appli native).

Une licence marquée [À vérifier] n'a pas été confirmée auprès de la source.

## Images et textures

| Source | Fichiers | Licence | Crédit à afficher |
|---|---|---|---|
| ESO, panorama de la Voie lactée (eso0932a) | `pipeline/tex/eso0932a.jpg` (dans le dépôt) | CC BY 4.0 | ESO/S. Brunier |
| Solar System Scope, textures 2k | `pipeline/tex/Solarsystemscope_texture_*` (dans le dépôt) | CC BY 4.0 | Solar System Scope (INOVE), https://www.solarsystemscope.com/textures/ |
| DESI Legacy Imaging Surveys (DR10), vignettes de galaxies | `pipeline/fetch_gal.py` | Usage libre avec mention [À vérifier] | Legacy Surveys / D. Lang (Perimeter Institute) |
| Relevés multi-longueurs d'onde : ROSAT, eROSITA, GALEX, WISE, AKARI, Planck, Fermi-LAT, Haslam 408 MHz, HI4PI, H-alpha | captures et tuiles de l'appli native | Données publiques des missions, mention requise [À vérifier relevé par relevé] | Chaque mission ou équipe de relevé, via NASA SkyView, IRSA et LAMBDA |

## Catalogues d'étoiles et de galaxies

| Source | Fichiers | Licence | Référence |
|---|---|---|---|
| ESA Gaia (DR3, FLAME, et DR4 à venir) | `pipeline/raw/flame_hip.csv`, `bj22_gaia.json`, `scholz_gaia.json` (dans le dépôt) ; extractions via les serveurs TAP Gaia | CC BY-SA 3.0 IGO | « This work has made use of data from the European Space Agency (ESA) mission Gaia (https://www.cosmos.esa.int/gaia), processed by the Gaia Data Processing and Analysis Consortium (DPAC). » |
| Rencontres stellaires, Bailer-Jones (2022) | `pipeline/raw/bj22.csv`, `bj22_figures_encounters.tex`, `bj22_names.json` (dans le dépôt) | Données d'article, citation requise | Bailer-Jones C. A. L., 2022, ApJL 935, L9 |
| Étoile de Scholz | `pipeline/raw/scholz_gaia.json` (dans le dépôt) | Données Gaia (voir plus haut) | Scholz R.-D., 2014, A&A 561, A113 ; Mamajek E. et al., 2015, ApJL 800, L17 |
| Local Volume Database (galaxies naines) | `pipeline/raw/dwarf_all.csv` (dans le dépôt) | Citation requise [À vérifier] | Pace A. B., 2024, « The Local Volume Database », https://github.com/apace7/local_volume_database |
| OpenNGC | `pipeline/sources/build_openngc.py` | CC BY-SA 4.0 | Mattia Verga, https://github.com/mattiaverga/OpenNGC |
| SIMBAD et VizieR | requêtes des scripts `pipeline/` | Citation requise | CDS, Strasbourg |
| SDSS (DR17, DR18) | requêtes des scripts `pipeline/` | Mention requise | Sloan Digital Sky Survey |
| Cosmicflows-4 | `app/gen/data17.js` | Citation requise | Tully R. B. et al., 2023, ApJ 944, 94 |
| NASA Exoplanet Archive | requêtes des scripts `pipeline/` | Mention requise | NASA Exoplanet Archive, Caltech/IPAC |
| HYG Database 4.1 (58 967 étoiles brillantes) | `app/gen/data.js`, `app/gen/data2.js` | CC BY-SA 4.0 | David Nash, https://www.astronexus.com/hyg |
| DESI DR1 (galaxies et quasars) | tuiles en flux `g1`–`g3` | Mention requise | DESI Collaboration, NOIRLab Astro Data Lab |
| 2MRS, 6dFGS, 2dFGRS (relevés de galaxies) | `app/gen/data3.js`, `app/gen/data4.js`, tuiles | Citation requise | Huchra et al. 2012 (2MRS) ; Jones et al. 2009 (6dFGS) ; Colless et al. 2001 (2dFGRS) |
| Galaxies proches (UNGC & Groupe local) | `app/gen/data.js`, `app/gen/data6.js` | Citation requise | Karachentsev et al. 2013 ; McConnachie 2012 |
| Pulsars (ATNF) | `app/gen/data4.js` | Citation requise | Manchester et al. 2005, ATNF Pulsar Catalogue |
| Amas globulaires et ouverts | `app/gen/data4.js` | Citation requise | Harris 1997 (2010) ; Cantat-Gaudin et al. 2020 |
| Trous noirs (supermassifs et stellaires) | `app/gen/data4.js` | Citation requise | van den Bosch 2016 ; Corral-Santana et al. 2016 (BlackCAT) ; Event Horizon Telescope |
| Étoiles du centre galactique (S-stars) | `app/gen/data.js` | Citation requise | Gillessen et al. 2017 |
| Limites des constellations | `app/gen/data4.js` | Domaine public / citation | Roman N. G., 1987, PASP 99, 695 |

## Système solaire

| Source | Fichiers | Licence | Référence |
|---|---|---|---|
| JPL Horizons, SBDB, éphémérides DE440 | `pipeline/build_ephem.py`, `app/gen/ephem.js`, `app/test/ref_de440.json` | Produits de la NASA, domaine public aux États-Unis [Probable] | NASA/JPL Solar System Dynamics ; Park R. S. et al., 2021, AJ 161, 105 |
| Catalogues des transits de Mercure et de Vénus | `pipeline/raw/transits/` (dans le dépôt) | Produits de la NASA, mention demandée | Fred Espenak, NASA/GSFC |
| NSSDC, fiches planétaires | `pipeline/` | Produits de la NASA | NASA Space Science Data Coordinated Archive |
| Lignes des constellations (Stellarium, culture occidentale v0.22.2) | `pipeline/fetch_far.py` | GPL-2.0 ou licence de la culture céleste [À vérifier] | Stellarium, https://stellarium.org |

## Physique

| Source | Fichiers | Licence | Référence |
|---|---|---|---|
| Traces d'évolution stellaire MIST v1.2 | `pipeline/raw/mist_v1.2_feh0_00100M.track.eep` (dans le dépôt) | Citation requise | Choi J. et al., 2016, ApJ 823, 102 ; Dotter A., 2016, ApJS 222, 8 |
| Fonctions colorimétriques CIE 1931 | `pipeline/ref/` (dans le dépôt) | Libre | Colour & Vision Research Laboratory (CVRL), UCL |
| Gabarits spectraux de galaxies Kinney-Calzetti | `pipeline/ref/kc96_*` (dans le dépôt) | Citation requise | Kinney A. L. et al., 1996, ApJ 467, 38 ; Calzetti D. et al., 1994, ApJ 429, 582 |
| Gabarit spectral de quasar SDSS (spDR2-029) | `pipeline/ref/sdss_spDR2-029_qso.fit` (dans le dépôt) | Mention requise | Sloan Digital Sky Survey |
| Carte 3D de la poussière | `pipeline/ref/edenhofer2024_readme.md` (dans le dépôt), `app/gen/data20.js` | Citation requise | Edenhofer G. et al., 2024, A&A 685, A82 |
| Densités de partons CT18NNLO | `pipeline/quantique/proton_pdf.py` | Citation requise | Hou T.-J. et al., 2021, Phys. Rev. D 103, 014013 ; LHAPDF |
| Ondes gravitationnelles | `app/gen/data18.js` | CC BY 4.0 | Gravitational Wave Open Science Center (GWOSC), LIGO, Virgo et KAGRA |
| Planck | `app/gen/data19.js` | Mention requise | ESA et Planck Collaboration |
