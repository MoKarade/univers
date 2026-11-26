# Audit qualité approfondi & gouvernance GitHub (`/github`)

> **Date** : 26 novembre 2026 — **Dépôt** : `MoKarade/univers` (base `main` @ `b551bf1`, branche de travail `qualite-pro`).
> **Convention (`CLAUDE.md`)** : chaque affirmation non évidente porte `[Certain]` / `[Probable]` / `[Supposition]` / `[À vérifier]`.

---

## 1. État GitHub et gouvernance (`gh` CLI) `[Certain]`

| Indicateur | Valeur mesurée via `gh` | Risque / Action recommandée |
|---|---|---|
| Visibilité | **PUBLIC** (passé public le 20 nov. 2026 à ~15h47 UTC après épuisement des minutes Actions privées) | Contredit `docs/gestes-marc.md` (« dépôt privé ») ; expose l'absence de `LICENSE` et de Secret Scanning. |
| Licence (`licenseInfo`) | **`null` (aucun fichier `LICENSE`)** | **Critique** : dépôt public redistribuant des données CC BY 4.0, CC BY-SA 3.0 IGO, CC BY-SA 4.0 et potentiellement GPL-2.0 (Stellarium). Choisir une licence explicite pour le code et séparer les licences des données (`CREDITS.md`). |
| Branches distantes | **101 branches** (0 protégée) : 2 cœur (`main`, `appli-pc`), 6 PR brouillons actives, **81 branches déjà fusionnées non supprimées**, 3 fermées non fusionnées, 8 orphelines | Activer `deleteBranchOnMerge: true` et purger les 81 branches déjà fusionnées. |
| Divergence `main` vs `appli-pc` | `appli-pc` (`8aa80a8`+) est **+463 commits en avance** et **3 commits en retard** (`CREDITS.md`, PR #120) sur `main` (`b551bf1`) | **Critique** : `app/`, `infra/`, `CLAUDE.md`, `HANDOVER.md` sont identiques octet pour octet entre `main` et `appli-pc`, mais tout le travail `natif/` récent vit sur `appli-pc`. Réconcilier la branche canonique (et fusionner `CREDITS.md` dans `appli-pc`). |
| PR #152 (`assainir-lot1-natif`) | **FUSIONNÉE** dans `appli-pc` le 26 nov. 2026 à 14h47 UTC | Lors de la réconciliation `qualite-pro` / `main` ↔ `appli-pc`, reprendre la version `appli-pc` de `natif/` là où elle est plus avancée (format film v3, SPH gaz, naines rouges) et fusionner les durcissements de `qualite-pro` (gardes `NaN`/`Inf`, `nomValide`, `essai_robustesse`, shaders GLSL). |
| Protection de branche & Rulesets | **0 protection** sur `main` et `appli-pc`, **0 ruleset**, 42 PR fusionnées en brouillon | Ajouter un Ruleset sur `main` (et `appli-pc` tant qu'active) exigeant le succès de `Contrôles` et bloquant force-push / suppression. |
| Sécurité GitHub | `dependabot_security_updates: enabled` ; **`secret_scanning: disabled`**, **`secret_scanning_push_protection: disabled`**, pas de `SECURITY.md` | Activer Secret Scanning + Push Protection (gratuit sur dépôt public), surtout avec des clés Firebase (`*service-account*.json`). |
| Volume GitHub (`diskUsage`) | **221 Mo** (alors que le pack local de `main` ne fait que **28 Mo**) | **128,8 Mo** de captures binaires (`captures/` 115,3 Mo, `docs/captures-*` 12,8 Mo, `essai.ppm` 675 ko) ont été commitées sur `appli-pc`. Ne plus commiter de captures brutes dans Git (utiliser GitHub Releases ou artifacts Actions). |
| Variables / Environments Actions | 0 environment, **0 variable** (`FIREBASE_PROJECT_ID` absente) | Confirme que la Mission 1 T2 (Firebase) n'est pas encore déployée. |

---

## 2. Synthèse des corrections engagées sur `qualite-pro`

### A. Tests Web (`app/test/`, Jalon M1) `[Certain]`
- **6 tests faux-verts corrigés** (`physics.test.js`, `ephem.test.js`, `horizons.test.js`, `future.test.js`, `dyn.test.js`, `more.test.js`) : ajout de vraies assertions quantitatives avec code de sortie non nul en cas d'écart.
- **Chargeur partagé `app/test/_load.js`** : élimine les 20 copies de `vm.runInThisContext`, les 11 copies de `b64ToBytes` et les `eval()` dans les tests.
- **Tests Python d'écran durcis** : suppression des chemins `/home/claude` et `/mnt/user-data` et d'`eval()` dans `lost.py`, suppression de la pollution de répertoire de travail dans `dust_screen.py`.
- **Chaînage des époques** dans `lunes.test.js` et `long.test.js` sans relâcher aucune tolérance.

### B. Application Web (`app/src/`, `app/build.py`, Jalons M2 & M3) `[Certain]`
- **Correctifs de bugs** (`WEB-BUG-01..14`) : arrêt de la tempête HTTP 404 à 60 FPS (`fusiStart`, `fusWant`), suppression de la clé dupliquée `G` dans `window.__U`, `dyn.material.dispose()` dans `R.setDyn`, `* F.orb` sur `AST_LABELS`/`TNO_LABELS`, lecture dynamique de `st.life`/`st.fate` dans `selStar`, clamp `LMICRO` + nettoyage `sessionStorage` dans `onLost`, clamp `Math.acos(clamp(c, -1, 1))`, garde `q` cosmologique, suppression du `NaN` injecté dans le buffer WebGL des lunes, `bvToTeff` + fallback `SUN_PHASES`, suppression de `jdDate` (bogue grégorien pré-1582), `w.terminate()` + plafond `SUN_ORB.cps`, cube-map trou noir dès la première image.
- **Sécurité & autonomie** (`WEB-SEC-01..04`) : centralisation des 18 URLs `/_blob/<hash>` dans un manifeste configurable unique `ASSETS` (surchargeable par `window.__ASSETS` + compatibilité `window.__*`, contrôle de schéma d'URL), échappement HTML systématique (`escHtml`) sur les `innerHTML`.
- **Performances** (`WEB-PERF-01..12`) :
  - `evTransits` (`23_events.js`) : évaluation VSOP87 dédiée (Terre + planète cible) + saut par période synodique → gain > 100×.
  - `moAccel` (`24_moons.js`) : `d2 * Math.sqrt(d2)`, Jupiter seul via `vsopHelio`, paires symétriques.
  - `nbStep`/`nbGr` (`21_nbody.js`) : fusion des `nbJump` intérieurs, extraction des constantes de la boucle GR.
  - `orbAcc`/`orbInit` (`26_orbits.js`) : identités algébriques double-angle sans `atan2`/`cos`/`sin` par étoile, réutilisation des buffers.
  - `dustLevels` & shader étoiles (`28_dust.js`, `40_render.js`) : LUT 256 entrées, uniformes précalculés, `exp2`.
  - Élimination du thrashing à l'arrêt (`drawTape`, `hud`/`renderCard`, `tileStatus`, `updateMoons` hors système solaire, `bloom` FBOs).
- **Hygiène & modularité** : outil reproductible `pipeline/clean_gen_dead_keys.py` prouvant l'égalité profonde de `DATA` avant/après suppression des clés mortes, nettoyage d'`app/build.py` (retrait du patch JSON fragile sur `data2.js`, fermeture propre des fichiers), ajout de `.prettierrc` et `eslint.config.mjs`.

### C. Natif C++20 / Vulkan / GLSL (`natif/`, Jalon M4) `[Certain]`
- Migration des 9 headers `natif/src/*.h` hors des `namespace {}` anonymes vers `namespace univers` + `inline` (correction du linkage interne de `gWindowMode` et suppression de `-Wno-unused-function`).
- Wrapper RAII portable `natif/src/fichier_mappe.h` (`CreateFileA`/`MapViewOfFile` sous Windows, `mmap` sous POSIX) rendant `ephemeride.h`, `natif/physique/` et les essais sans GPU compilables et exécutables sous Linux avec **0 avertissement** sous GCC 13.3 (`5/5` CTest verts en 10,5 s).
- Épinglage de `stb` sur un commit précis dans `natif/CMakeLists.txt`, correction des `-Wmisleading-indentation`, gardes `NaN`/`Inf` et anti-traversée de chemin (`nomValide`), durcissement des shaders GLSL (`ecran.frag`, `sphere.frag`, `asteroides.vert`, `galaxies.vert`), ajout de `essai_robustesse`.

### D. Pipeline (`pipeline/`, Jalon M5) `[Certain]`
- Manifestes `pipeline/pyproject.toml` et `pipeline/requirements-ci.txt` (4 profils : `core`, `astro`, `quantum`, `fusion`).
- Résolveur de chemins partagé `pipeline/_paths.py` (suppression de `/mnt/user-data`, `/tmp`, `LOCALAPPDATA` codés en dur), suppression de `pipeline/gravite/long.test.js.brouillon`, correctifs NumPy 2.x (`proton_pdf.py`), `with open` (`calcul.py`), compteur de débordement CUDA (`gravite_gpu.py`), regex multi-ligne résiliente sur `TILE_MANIFEST`, suite `pipeline/test_pipeline_stdlib.py` (38/38 tests verts sans dépendance externe).

### E. CI/CD, Infrastructure et Documentation (Jalon M6) `[Certain]`
- `.github/workflows/controles.yml` : exécution parallèle des 26 tests JS, contrôle `FATE_P` et garde anti-`//` en milieu de ligne, nouveau job Linux C++20 (`natif/` + `natif/physique/`), nouveau job Python (`test_pipeline_stdlib.py`, `test_build_gw.py`).
- Durcissement de `infra/cors.json.tpl`, `infra/deploiement.exemple.yml`, `.gitignore` et `.gitattributes`.
- Resynchronisation de `CLAUDE.md`, `HANDOVER.md`, `CREDITS.md`, `README.md` et `docs/gestes-marc.md`.

---

## 3. Actions réservées à Marc (réglages GitHub) `[Certain]`

1. **Choisir la licence du dépôt public** (ex. MIT / Apache-2.0 pour le code original, en précisant la séparation avec les données tierces dans `CREDITS.md`) et clarifier le statut des lignes de constellations Stellarium (`GPL-2.0 [À vérifier]`).
2. **Activer dans GitHub Settings** :
   - `General → Pull Requests → Automatically delete head branches` (`deleteBranchOnMerge: true`).
   - `Code security → Secret scanning` + `Push protection`.
   - `Rules → Rulesets` sur `main` (et `appli-pc`) : exiger `Contrôles`, bloquer force-push.
3. **Réconcilier `main` et `appli-pc`** : fusionner `CREDITS.md` dans `appli-pc`, décider du sort des 128,8 Mo de `captures/` avant convergence vers une branche principale unique, puis purger les 81 branches déjà fusionnées.
