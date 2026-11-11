# Lot S — Les sources de référence (11 novembre 2026)

Origine : deux documents de Marc (sources de données astronomiques ; relevés et cosmologie), « implémente tout ça ». Cadrage et vérification des chiffres : https://claude.ai/artifact/Y8L4ysuL8aP5AuuPLwaZVi

## Décisions de Marc (11 novembre 2026 : « oui » à toutes les recommandations)

| N° | Sujet | Décision |
|---|---|---|
| Q1 | Ajouts retenus | A1, A2, A3, A6, A8 d'abord ; A4, A5, A7 ensuite |
| Q2 | Calendrier | Données préparées tout de suite, dans des scripts à part ; branchement dans la page après le lot C ; A2 rejoint le lot E |
| Q3 | Où vivent les données | Copiées dans le dépôt (puis Firebase) ; seule la recherche par nom (A5) interroge le CDS en direct |
| Q4 | Cosmologie | Le calcul garde Planck 2018 (H0 = 67,4) ; tension sur H0 et résultat de DESI expliqués dans les fiches |
| Q5 | Terre plus fine (Copernicus) | Pas maintenant : mission « surfaces plus fines » |
| Q6 | Fini quand | Chaque ajout : visible avec source et licence, prouvé par un test à l'écran, quatre critiques à PASSE, confirmé par Marc sur son téléphone |

Chiffres des documents écartés : SIMBAD compte 20,27 millions d'objets (juin 2025), pas plus de 30 ; SH0ES publie H0 = 73,0 ± 1,0, pas 76. Toute valeur affichée vient de sa source d'origine, jamais des documents.

## Tâches

Les scripts de données sont dans `pipeline/sources/`. Les fichiers bruts (2 Go pour Planck) restent hors dépôt, dans `%LOCALAPPDATA%\univers-raw`. Chaque script écrit son propre fichier `app/gen/dataNN.js`, branché dans `app/build.py` seulement à l'étape « page ».

### S1 — Fond diffus de Planck (A3)
- Avant : carte WMAP 9 ans (ILC), 720 × 360.
- Après : carte Planck PR3 SMICA, version comblée sur le plan galactique si l'archive la fournit, en coordonnées galactiques ; fiche « Planck 2018, ESA ».
- Données : `pipeline/sources/build_cmb_planck.py` → `app/gen/data16.js` (`DATA.CMB`, `DATA.CMB_SRC`).
- Fait (données) : colonne comblée `I_STOKES_INP` utilisée ; écart-type hors du plan galactique (|b| > 30°) : 105,4 µK, ordre de grandeur attendu pour le fond diffus [Probable] ; image 2048 × 1024, 880 ko dans la page (contre une carte WMAP 720 × 360).
- Fini quand : capture à l'écran à l'horizon cosmique ; critiques PASSE.

### S2 — Ondes gravitationnelles (A6)
- Après : chaque fusion détectée a un événement daté dans la chronologie, avec masses et distance telles que publiées.
- Données : `pipeline/sources/build_gw.py` → `app/gen/data15.js` (`DATA.GW`). Fait : 391 événements des catalogues GWTC officiels, 282 avec masses et distance ; les 161 du GWTC-5.0 n'ont pas encore de paramètres dans l'interface de GWOSC et le disent.
- Pas fait : la zone probable sur le ciel (cartes de localisation, une par événement, lourdes). À trancher au branchement.
- Fini quand : test `ondes` : nombre d'événements affichés égal à celui du fichier ; GW170817 porte sa date (17 août 2017, 12:41:04 UTC) ; critiques PASSE.

### S3 — Méthode de mesure des distances (A1)
- Après : la fiche de chaque galaxie de Cosmicflows-4 dit comment sa distance a été mesurée (Céphéides, TRGB, Tully-Fisher, plan fondamental, supernova, fluctuations de brillance de surface…), avec l'incertitude.
- Données : Cosmicflows-4, Tully et al. 2023, ApJ 944, 94 (VizieR J/ApJ/944/94, 55 874 galaxies). `pipeline/sources/build_cf4.py`.
- État : serveurs du CDS injoignables le 11/11/2026 à 21 h 50 UTC ; à relancer.
- Fini quand : test `distances` : 20 galaxies tirées au hasard ont la ligne « Distance mesurée par » ; M31 et NGC 4258 donnent la méthode publiée.

### S4 — Mouvements à grande échelle et Laniakea (A2, rejoint le lot E)
- Après : les galaxies de Cosmicflows-4 portent leur vitesse particulière mesurée ; la frontière de Laniakea est tracée d'après la reconstruction publiée.
- Fini quand : défini avec le lot E (R18).

### S5 — Cosmologie débattue (A8)
- Après : fiches « Expansion » et « Énergie noire » : H0 de Planck 2018 (67,4 ± 0,5) et de SH0ES (73,0 ± 1,0) ; DESI DR2 et DES Y6 (w0 = −0,84, wa = −0,53, écart de 2,3 σ au modèle standard). Le calcul de la page ne change pas.
- Fini quand : le critique de vérité confirme chaque valeur sur sa source.

### Ensuite (A4, A5, A7)
Ciel réel en zoom continu (HiPS), recherche par nom (Sesame, SIMBAD), zones couvertes par chaque relevé (MOC). Attendent la mission 1 (Firebase) pour A4.
