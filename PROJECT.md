# Project: Univers — Audit Qualité Approfondi (`/github`) & Refonte Professionnelle (`/goal`)

## Architecture

`MoKarade/univers` is a multi-component scientific 3D universe simulation spanning 47 orders of magnitude ($10^{-20}\text{ m}$ to the cosmic horizon) and deep cosmic time (Big Bang to $+100\text{ Ga}$):

1. **Web Application (`app/`)**:
   - **Physics & Astronomy Modules (`app/src/20_physics.js` .. `29_cone.js`)**: VSOP87/JPL ephemerides, 13-body Wisdom-Holman symplectic integrator (1PN GR + Moon ring), Dormand-Prince small-body & Galilean moon propagators, Mercury/Venus transit scanner, stellar/solar evolution & M31 merger replay, Milky Way rotating Dehnen-bar orbits (Web Worker), Schwarzschild black hole gravitational lensing LUT, Edenhofer 2024 3D dust atlas/raymarcher, comoving/angular-diameter lightcone LUT.
   - **Procedural/Formatting Utilities (`app/src/30_gen.js`)**: PRNG, `b64ToBytes`, vector math, Planck CIE 1931 `bbRgb`, French formatters, procedural catalogs, water/hydrogen SVG helpers.
   - **WebGL2 / Three.js `0.149.0` Renderer (`app/src/40_render.js`)**: HDR HalfFloat pipeline, selective bloom, micro-scale rendering (`LMICRO = -20.0`), multi-scale double-precision CPU repositioning, shader suite (`SH`).
   - **Application Shell & Controller (`app/src/index.html`, `app/src/60_app.js` → refactored into `60_state.js` .. `65_main.js`)**: Central configurable asset manifest (`ASSETS`), UI cards (safe DOM / escaped HTML), 738 real astronomical events, timeline tape, search/OpenNGC, WebGL context-loss recovery (`onLost`), animation loop, `window.__U` test hooks.
   - **Generated Payloads (`app/gen/*.js`) & Bundler (`app/build.py`)**: Concatenates `app/gen/*.js` and `app/src/*.js` into standalone `dist/index.html` while keeping `app/gen/` strictly pipeline-generated (`CLAUDE.md:11`).
   - **Test Suites (`app/test/`)**: Shared loader (`_load.js`), 26 quantitative Node.js physics tests (`*.test.js`, all with real pass/fail assertions), and Playwright headless Chromium/SwiftShader WebGL2 visual/UI tests (`*.py`).

2. **Native C++20 / Vulkan / GLSL Application (`natif/`)**:
   - **Portable Physics Library (`natif/physique/`)**: Standalone CMake C++20 `univers_physique` (`phys.h`, `nbody_noyau.h`, `systeme_solaire.{h,cpp}`, `galaxie_orbites.h`, `groupe_local.h`) + portable tests (`essai_galaxie`, `essai_fusion`, `essai_systeme_solaire`).
   - **Core & Renderer Headers (`natif/src/`)**: Named `namespace univers` (eliminating `namespace {}` internal-linkage bugs), portable RAII `MappedFile` (`fichier_mappe.h`) for Win32/POSIX, `ephemeride.h`, `orientation.h`, `cosmologie.h`, `interface_outils.h`, `commun.h`, `simulation.h`, `interface.h`, `asteroides.h`, `galaxies.h`, `spheres.h`, `points_planetes.h`, `fusion_points.h`, `rendu_fenetre.h`, `fenetre.{h,cpp}`, `univers.cpp`.
   - **GLSL 450 Shaders (`natif/shaders/*.{vert,frag}`)**: Uniform-derivative-safe `sphere.frag`, NaN-safe `ecran.frag`, linear-color-consistent `galaxies.vert`, fast `etoiles.vert`, guarded `asteroides.vert`.

3. **Data Generation & Conversion Pipeline (`pipeline/`)**:
   - Reproducible Python dependency manifest (`pipeline/pyproject.toml` + `pipeline/requirements-ci.txt` across 4 profiles: `core`, `astro`, `quantum`, `fusion`), shared path helper (`pipeline/_paths.py`), reproducible `app/gen/` dead-key pruning tool (`pipeline/clean_gen_dead_keys.py`), NumPy 2.x / Windows-safe / regex-resilient scripts, stdlib unit tests.

4. **CI/CD, Infrastructure, Governance & Documentation (`.github/workflows/`, `infra/`, root docs, `docs/`)**:
   - Multi-job hardened `.github/workflows/controles.yml` (parallel JS tests + ESLint + Prettier + `FATE_P` & `//` checks + Linux C++20 CMake build/tests + Python pipeline tests), hardened cloud workflows, safe `infra/` Firebase templates, tightened `.gitignore`/`.gitattributes`, synchronized `CLAUDE.md`/`HANDOVER.md`/`CREDITS.md`/`README.md`/`docs/gestes-marc.md`, and complete French deep code-quality & `/github` governance report (`docs/audit-qualite-github.md`).

5. **Opaque-Box E2E Verification Suite (`tests/e2e/`, `TEST_INFRA.md`, `TEST_READY.md`)**:
   - Requirement-driven 4-tier E2E suite (Tiers 1–4) verifying Web build/bundle/runtime/Playwright UI, physics accuracy & speed, security/offline resilience, C++20 portable physics CLI, pipeline CLI/reproducibility, and CI/config contracts — followed by Tier 5 white-box adversarial hardening.

### Branch & Conflict Coordination Note (`[Certain]` from `/github` Survey)
- GitHub `MoKarade/univers` has a branch split: `appli-pc` (`8aa80a8`) is `+463/-3` commits vs `main` (`b551bf1`), and draft PR #152 (`assainir-lot1-natif -> appli-pc`) is active on `natif/`. Meanwhile `app/`, `infra/`, `CLAUDE.md`, `HANDOVER.md`, `.gitignore`, `.gitattributes` are byte-for-byte identical between both branches.
- All local work executes cleanly against this checkout (`main` base) without touching `main`, `appli-pc`, or PR #152 on GitHub. At final completion (after M7 + Whole-Project Forensic Audit pass), deliverables are packaged into clean modular commits on a dedicated feature branch (`qualite-professionnelle`) with a Draft PR targeting `main` and full reconciliation guidance for `appli-pc` / PR #152 documented in `docs/audit-qualite-github.md`.

---

## Feature Inventory

Every finding and requirement from Step 0 Survey (`spec_miner_survey_1`, `explorer_survey_1`, `explorer_survey_2`) is assigned a Milestone (0 unassigned):

| # | Feature / Finding ID | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | `WEB-TEST-01` | Add real quantitative pass/fail assertions to all 6 false-green JS tests (`physics`, `ephem`, `horizons`, `future`, `dyn`, `more`) | M1 | `explorer_survey_1` |
| 2 | `WEB-TEST-02` | Create shared `app/test/_load.js` eliminating 20 `vm.runInThisContext` copies, 11 `b64ToBytes` copies, 2 `eval()`s, and 10 raw source-scraping tests | M1 | `explorer_survey_1` |
| 3 | `WEB-TEST-04`, `WEB-SEC-03` | Fix `lost.py` (remove `/home/claude`, `/mnt/user-data`, `eval()`), `dust_screen.py` (no CWD pollution), default `U_URL` in screen tests | M1 | `explorer_survey_1` |
| 4 | `WEB-TEST-05` | Fix `nbody.test.js` misleading "10 000 ans" label & `ephem.test.js` `%s` log format bug | M1 | `explorer_survey_1` |
| 5 | `WEB-PERF-02` (test), `WEB-PERF-03` (test) | Chain incremental epoch checkpoints in `lunes.test.js` & `long.test.js` without loosening any tolerances | M1 | `explorer_survey_1` |
| 6 | `WEB-BUG-01` | Fix infinite 60 FPS 404 fetch storm on `/_blob/` past `+4 Ga` (`fusiStart` & `fusWant`) | M2 | `explorer_survey_1` |
| 7 | `WEB-BUG-02` | Remove duplicate property key `G` in `window.__U` (`60_app.js:1628`) | M2 | `explorer_survey_1` |
| 8 | `WEB-BUG-03` | Fix WebGL `ShaderMaterial` leak in `R.setDyn` (`40_render.js:412`) | M2 | `explorer_survey_1` |
| 9 | `WEB-BUG-04` | Fix detached `AST_LABELS`/`TNO_LABELS` missing `* F.orb` during red-giant phase (`60_app.js:216`) | M2 | `explorer_survey_1` |
| 10 | `WEB-BUG-05` | Fix stale `selStar` life snapshot after async `FLAME` load (`60_app.js:549-551`) | M2 | `explorer_survey_1` |
| 11 | `WEB-BUG-06` | Fix `onLost` micro-scale clamp (`LMICRO`) and clear `REPRISE` from `sessionStorage` (`60_app.js:1514-1517`) | M2 | `explorer_survey_1` |
| 12 | `WEB-BUG-07..14` | Fix `Math.acos` lower clamp, cosmology `q` div-by-zero, WebGL `NaN` vertex position, `bvTemp`→`bvToTeff` + `SUN_PHASES` fallback, delete buggy `jdDate`→`fmtJd`, worker `onerror` terminate + `SUN_ORB.cps` cap, BH cube-map initial frame flash, `b-now`/`evCross`/`ngcGo`/`hudBox`/`qI` TDZ/LG slots | M2 | `explorer_survey_1` |
| 13 | `WEB-SEC-01` | Escape/sanitize all 9 `innerHTML` sinks via `escHtml` & safe DOM construction (preserving trusted SVG / Unicode superscripts) | M2 | `explorer_survey_1` |
| 14 | `WEB-SEC-02`, `INF-05` | Preserve SRI, add non-blocking graceful CDN/offline handling & document offline/CSP posture cleanly | M2 | `explorer_survey_1`, `spec_miner_survey_1` |
| 15 | `WEB-SEC-04`, `INF-04` | Centralize all 18 hardcoded `/_blob/` URLs into one configurable `ASSETS` manifest (`window.__ASSETS` + legacy `window.__*` overrides + safe URL scheme check) | M2 | `explorer_survey_1`, `spec_miner_survey_1` |
| 16 | `WEB-PERF-01` | Optimize `evTransits`/`evSep` (single-planet VSOP87 + synodic jump: 133s → <0.5s, exact same 94 Mercury & 12 Venus transits) | M2 | `explorer_survey_1`, `spec_miner_survey_1` |
| 17 | `WEB-PERF-02` (src) | Optimize `moAccel`/`moTrack` (`r2*Math.sqrt(r2)`, Jupiter-only VSOP87, symmetric pair kicks, stepper reuse) | M2 | `explorer_survey_1`, `spec_miner_survey_1` |
| 18 | `WEB-PERF-03` (src) | Optimize `nbStep`/`nbGr` (merged interior `nbJump(dt)`, hoisted `k`/`4*mu/r`, precomputed `SQRT_GM_SUN`) | M2 | `explorer_survey_1`, `spec_miner_survey_1` |
| 19 | `WEB-PERF-04` | Optimize `orbAcc`/`orbInit` (algebraic double-angle trig, precomputed bar angle, buffer reuse, cached `orbParams`) | M2 | `explorer_survey_1`, `spec_miner_survey_1` |
| 20 | `WEB-PERF-05` | Optimize `dustLevels` (256-entry LUT) & `SH.star.v`/`dustGlsl` (precomputed `uCamGalPc`, hoisted params, `exp2`) | M2 | `explorer_survey_1` |
| 21 | `WEB-PERF-06`, `WEB-PERF-09` | Eliminate idle/paused DOM/canvas/GPU thrashing (`drawTape`, `hud`/`renderCard`, `tileStatus`, `updateLabels`, `cons`/`moonSets`/`dyn`/`quarks`, unused bloom FBOs) | M2 | `explorer_survey_1` |
| 22 | `WEB-PERF-08`, `WEB-PERF-10..12` | Cache `mistLife`, zero-alloc `initStarKin`, 3-float `starPosOne` for `closest()`/`OO`, `sbRange` `ctx.e` cache, pre-scaled comets, `pickAt` wheel skip + `sbTrack` cache, `tailAdvance` chunked <14ms budget, in-place `Uint32Array.sort` | M2 | `explorer_survey_1` |
| 23 | `WEB-SIMP-02..08` | Consolidate 6 duplicate helpers, delete all dead code/vars, merge duplicate CSS rules in `index.html`, fix stale UI copy ("180"→"738", etc.), trim 5 over-precise float64 literals, simplify `selLine` if safe | M2 | `explorer_survey_1` |
| 24 | `WEB-PERF-07`, `HYG-03`, `PIPE-HYG-01`, `WEB-SIMP-05` | Reproducible `pipeline/clean_gen_dead_keys.py` pruning 1.43 MiB dead overwritten keys in `app/gen/` (proven `DATA` deep equality), remove brittle `data2.js` JSON hack & unclosed file handles in `app/build.py` | M3 | `explorer_survey_1`, `explorer_survey_2`, `spec_miner_survey_1` |
| 25 | `WEB-SIMP-01` | Split 301 KB `60_app.js` into 6 focused files (`60_state.js`..`65_main.js`), format ALL `app/src/*.js` with Prettier (eliminating 1,566 multi-statement lines & 136 `//` traps), add `.prettierrc` & `eslint.config.mjs` (0 errors) | M3 | `explorer_survey_1`, `spec_miner_survey_1` |
| 26 | `CPP-PORT-01..04`, `HYG-07` | Portable RAII `MappedFile` (`natif/src/fichier_mappe.h`) in `ephemeride.h`/`commun.h`/`asteroides.h`/`galaxies.h`, fix `natif/physique/CMakeLists.txt` (`cxx_std_20`, standalone `project()`, conditional `-static`), pin `stb` SHA & modernize `natif/CMakeLists.txt` (Linux-configurable portable tests), missing `<algorithm>`, `essai_systeme_solaire --noyau` without `de440.bsp` | M4 | `explorer_survey_2`, `spec_miner_survey_1` |
| 27 | `CPP-BUG-01..05` | Fix `points_planetes.h` hidden planets outside DE440, `simulation.h` missing TDB offset (`jdTdb()`), replace `namespace {}` across 9 headers with `namespace univers` + `inline` (`gWindowMode`) & remove `-Wno-unused-function`, `std::jthread` RAII in `fenetre.cpp`, fix planet/galaxy color-space bugs | M4 | `explorer_survey_2`, `spec_miner_survey_1` |
| 28 | `CPP-BUG-06..12`, `GLSL-BUG-01..03` | Bounds-check binary loaders (`LongTable`, `groupe_local.h` strict aliasing, `Spk` Rule-of-5/cycle guard, `readSpv`), per-image Vulkan `rendered` semaphores, fix `interface.h` truth/dateJump/relativeToToday/menu bugs, edge-case clamps (`cosmologie.h`, `orientation.h`, `interface_outils.h`, CRLF, `frNum`, Ballesteros), fix GLSL `sphere.frag`/`ecran.frag`/`asteroides.vert` UB | M4 | `explorer_survey_2` |
| 29 | `CPP-PERF-01..06`, `CPP-SIMP-01..02`, `CPP-PAR-01` | Optimize `galaxie_orbites.h` (FSAL + loop order + algebraic trig, 4–6× speedup), cache `ageGyr`, filter `OrbitCache`, gate `FusionPoints` upload, simplify `etoiles.vert`, direct `positions()` lookup, clean 0-warning C++20 formatting (`.clang-format`) & document JS↔C++ parity | M4 | `explorer_survey_2` |
| 30 | `PIPE-DEP-01` | Add `pipeline/pyproject.toml` & `pipeline/requirements-ci.txt` covering all 4 Python dependency profiles | M5 | `explorer_survey_2`, `spec_miner_survey_1` |
| 31 | `PIPE-BUG-01..05` | Fix `np.trapz` NumPy 2.x (`proton_pdf.py`), `with open` before `os.replace` (`calcul.py`), CUDA stack overflow counter (`gravite_gpu.py`), resilient `TILE_MANIFEST` regex (`re.S` + split files) & safe `retire_data2` (`pipeline/natif/`), `fusion_bin` 16-byte validation, `build_cf4`/`build_openngc` fixes | M5 | `explorer_survey_2` |
| 32 | `PIPE-HYG-02..04` | Delete `pipeline/gravite/long.test.js.brouillon`, add `pipeline/_paths.py` removing `/mnt/user-data`, `/tmp`, stale `../gen`, `LOCALAPPDATA`, remove embedded `pip install --break-system-packages`, add stdlib pipeline tests & refresh `pipeline/README.md` | M5 | `explorer_survey_2`, `spec_miner_survey_1` |
| 33 | `CI-01..10`, `WEB-TEST-03` | Upgrade `.github/workflows/controles.yml` (triggers on `main` & `appli-pc`, parallel JS tests, `eslint`, `prettier --check`, `FATE_P` & inline `//` guards, real CMake Linux C++20 job with `-Werror`, Python pipeline job) + harden `fusion-*.yml` & `quantique.yml` (Node 24 actions, pinned SHAs/deps, caching, least-privilege permissions) | M6 | `spec_miner_survey_1`, `explorer_survey_1`, `explorer_survey_2` |
| 34 | `INF-01..03`, `INF-06` | Harden `infra/cors.json.tpl`, `infra/deploiement.exemple.yml` (safe Python substitution, non-empty checks, pinned `firebase-tools`, `permissions`, `timeout-minutes`, HTTP 403 smoke check), document Blaze guardrails | M6 | `spec_miner_survey_1` |
| 35 | `HYG-04..06` | Harden `.gitignore` (build dirs, binaries, `*.ppm`, `captures/`, `*.brouillon`, `infra/storage.rules`, `.agents/`) & `.gitattributes` (binary formats) | M6 | `spec_miner_survey_1` |
| 36 | `DOC-01..06`, `GH-01..07`, `HYG-01` | Complete `CREDITS.md` (+14 missing sources incl. HYG CC BY-SA 4.0, Stellarium flag), resync `CLAUDE.md`, `HANDOVER.md`, `README.md`, `docs/gestes-marc.md`, and write deep French `/github` + code-quality report `docs/audit-qualite-github.md` (covering branch split, PR #152 reconciliation, `captures/` 128.8 MB bloat, `LICENSE` decision, branch protection, `deleteBranchOnMerge`, Secret Scanning, 81 merged branches) | M6 | `spec_miner_survey_1` |
| 37 | E2E Suite (Tiers 1–4) | Independent opaque-box 4-tier E2E test suite (`tests/e2e/`, `TEST_INFRA.md`, `TEST_READY.md`) covering all user-facing requirements & contracts | E2E Track | Project Pattern |
| 38 | Final Pass + Tier 5 + Packaging | Pass 100% E2E Tiers 1–4 → Tier 5 white-box adversarial hardening until 0 gaps → Whole-Project Forensic Audit → clean feature branch & Draft PR | M7 | Project Pattern, `ORIGINAL_REQUEST.md` |

---

## Milestones

| # | Name | Scope | Exclusive File Ownership | Dependencies | Status | Sub-Orchestrator Conv ID |
|---|---|---|---|---|---|---|
| **M1** | Web Test Harness & Truthfulness | Shared `app/test/_load.js`, real assertions in 6 false-green tests, remove source-scraping & `eval()`, fix Python screen test paths, chain `lunes`/`long` epochs | `app/test/_load.js`, `app/test/*.test.js`, `app/test/orbits_measure.js`, `app/test/lost.py`, `app/test/dust_screen.py`, `app/test/cone_screen.py`, `app/test/lens_screen.py` | none | IN_PROGRESS | `f1d186d941c1f870d6d16b9315ae9076` |
| **M2** | Web Bugs, Security & Perf | Fix `WEB-BUG-01..14`, `WEB-SEC-01..04`, `WEB-PERF-01..06,08..12`, `WEB-SIMP-02..08` (incl. `ASSETS` manifest, safe DOM/XSS, 10×+ physics speedups, idle/GPU/shader opts) | `app/src/*` | M1 | PLANNED | — |
| **M3** | Web Build, Dead-Data Cleanup & Modular Formatting | Reproducible `pipeline/clean_gen_dead_keys.py` pruning 1.43 MiB dead keys (proven `DATA` equality), clean `app/build.py`, split `60_app.js` → `60_state.js..65_main.js`, Prettier format all `app/src/*.js`, add `.prettierrc` + `eslint.config.mjs` | `app/build.py`, `app/gen/*.js`, `app/src/*`, `app/test/_load.js` (if path list updates), `pipeline/clean_gen_dead_keys.py`, `.prettierrc`, `eslint.config.mjs` | M2 | PLANNED | — |
| **M4** | Native C++20 / Vulkan / GLSL Overhaul | Portable `MappedFile`, CMake portability & `stb` pin, fix `CPP-BUG-01..12` & `GLSL-BUG-01..03`, `CPP-PERF-01..06` (4–6× `galaxie_orbites`), 0-warning GCC+Clang+Valgrind clean | `natif/**` | none | IN_PROGRESS | `75524fe091e87be36de4741bd542ee19` |
| **M5** | Pipeline Reproducibility & Hygiene | `pipeline/pyproject.toml` + `requirements-ci.txt`, `pipeline/_paths.py`, fix `PIPE-BUG-01..05` & `PIPE-HYG-02..04`, delete `.brouillon`, add stdlib pipeline tests | `pipeline/**` (excl. `pipeline/clean_gen_dead_keys.py`) | none | DONE (5/5 Gate PASS; 38 stdlib tests, 70/70 AST, `ruff` clean, CUDA/C++20 ASan probes PASS) | `1473bb13b6d35bdb660e9c100205aef6` |
| **M6** | CI/CD, Infra, Hygiene & Docs/GitHub Report | Upgraded `.github/workflows/*`, hardened `infra/*`, `.gitignore`/`.gitattributes`, synced `CLAUDE.md`/`HANDOVER.md`/`CREDITS.md`/`README.md`/`docs/gestes-marc.md`, deep report `docs/audit-qualite-github.md` | `.github/**`, `infra/**`, `.gitignore`, `.gitattributes`, `CLAUDE.md`, `HANDOVER.md`, `CREDITS.md`, `README.md`, `docs/**` | M3, M4, M5 | PLANNED | — |
| **E2E** | E2E Testing Track (Parallel) | Requirement-driven opaque-box 4-tier E2E test suite (`TEST_INFRA.md`, `tests/e2e/**`, `TEST_READY.md`) | `TEST_INFRA.md`, `TEST_READY.md`, `tests/e2e/**` | none | IN_PROGRESS | `07077dfa17a4547f8ddaab5622b94281` |
| **M7** | Final Milestone (Tiers 1–4 + Tier 5 + Packaging) | Phase 1: 100% E2E Tiers 1–4 pass; Phase 2: Tier 5 white-box adversarial hardening until 0 gaps; Whole-Project Forensic Audit; clean feature branch + Draft PR | Full repo (sequential final gate) | M6, E2E (`TEST_READY.md`) | PLANNED | — |

---

## Interface Contracts

### 1. `app/build.py` ↔ `app/src/` ↔ `app/gen/` ↔ `app/test/_load.js`
- **Build invocation**: `python3 app/build.py [optional_output_path]` (default `dist/index.html`).
  - Loads all `app/gen/*.js` in deterministic order (`data.js`, `data2.js`..`data20.js`, then named generated modules) and all `app/src/*.js` in lexicographic order (`20_physics.js` .. `65_main.js`) into `app/src/index.html` replacing `/*__DATA__*/` and `/*__JS__*/`.
  - Asserts neither placeholder remains in output. Closes all file handles with `with open(...)`.
- **Shared JS test loader (`app/test/_load.js`)**:
  - Exports `loadUnivers({ gen = [], src = [], globals = {} })` returning a Node `vm` context with `DATA` initialized and requested `app/gen/*.js` + `app/src/*.js` evaluated cleanly (transforming top-level `const`/`let` in sandboxed VM only once in `_load.js`), plus `listSrcFiles()`, `readSrcConcat()`, and `REPO_ROOT`.
  - Any split of `60_app.js` into `60_state.js`..`65_main.js` MUST preserve all `window.__U` properties (without duplicate `G`), all legacy `window.__*` overrides (`__TIER`, `__FUSC`, `__FUSI`, `__NBL`, `__FLAME`, `__PHOTOS`, `__NGC`, `__TILES_URL`, `__TILES`, `__NOADAPT`, `__TILES_ON`, `__SS`), AND support unified `window.__ASSETS`.
- **Generated Data Equivalence Contract**:
  - `pipeline/clean_gen_dead_keys.py` MUST verify before exiting `0` that evaluating all `app/gen/*.js` in build order produces an **exact deep-equal `DATA` object** before and after dead-key pruning.

### 2. `app/src/` (`TILE_MANIFEST`) ↔ `pipeline/natif/{etoiles,asteroides,galaxies}.py`
- `TILE_MANIFEST` remains marked with `/*__TILES__*/` in the `app/src/6*.js` module containing the asset manifest (and may be multi-line formatted by Prettier).
- `pipeline/natif/{etoiles,asteroides,galaxies}.py` MUST locate `TILE_MANIFEST` across `sorted((REPO_ROOT / 'app' / 'src').glob('6*.js'))` using `re.S` so formatting or splitting `60_app.js` never breaks native converters.

### 3. `natif/physique/` ↔ `natif/src/` ↔ CI
- `natif/src/fichier_mappe.h`: header-only RAII `univers::MappedFile` (`open(const char*)`, `close()`, `data()`, `size()`, `valid()`, non-copyable, movable) implemented via Win32 `CreateFileA`/`MapViewOfFile` under `#ifdef _WIN32` and POSIX `open`/`fstat`/`mmap` otherwise.
- `natif/physique/CMakeLists.txt`: standalone-buildable via `cmake -S natif/physique -B <build_dir>` on both Linux (GCC/Clang) and Windows (MinGW/MSVC), declaring `cxx_std_20` and exposing targets `univers_physique`, `essai_galaxie`, `essai_fusion`, `essai_systeme_solaire`.
- `essai_systeme_solaire`: running with `--noyau` (or no args) executes the self-contained Horizons 1650–2450 N-body validation (`nbody_ref.h`) and exits `0` on pass; passing `<de440.bsp> [table_longue.bin]` runs the full ephemeris suite.
- `natif/src/` portable tests (`essai_cosmologie`, `essai_interface`, `essai_ephem`, `essai_orientation`): compile cleanly on Linux with `-std=c++20 -Wall -Wextra -Wpedantic -Wshadow`; `essai_cosmologie` and `essai_interface` run data-free and exit `0` with 0 Valgrind errors.

### 4. `pipeline/` ↔ CI
- `pipeline/_paths.py`: exposes `REPO_ROOT`, `APP_GEN`, `APP_SRC`, `PIPELINE_DIR`, and `raw_dir(cli_arg=None)` resolving `cli_arg` → `os.environ.get("UNIVERS_RAW")` → `REPO_ROOT / "univers-raw"` (never `/mnt/user-data`, `/tmp`, or hardcoded `LOCALAPPDATA`).
- `pipeline/pyproject.toml` + `pipeline/requirements-ci.txt`: authoritative dependency profiles (`core`, `astro`, `quantum`, `fusion-cpu`, `fusion-gpu`).
- Stdlib-only pipeline tests (`pipeline/sources/test_build_gw.py`, `pipeline/test_pipeline_stdlib.py`) MUST run cleanly with plain `python3` (0 third-party packages) and exit `0`.

### 5. Scientific Truth & Safety Invariants (`CLAUDE.md`)
- Zero occurrences of `FATE_P` in `app/src/`.
- Every displayed astronomical value preserves `mesuré` / `calculé` / `supposé` / `inconnu` (`CLAUDE.md:10,47`), including deep-time galaxy distances in `natif/src/interface.h` (`sim.deepTime() ? "calculé" : "mesuré"`).
- `LMICRO = -20.0`, Earth tidal divergence `"Sort inconnu"`, 37.7 Ga chaos cutoff `"Inconnu"`, zero fades replacing phenomena.
- Zero mid-line `//` comment hazards anywhere in `app/src/*.js` (enforced by Prettier + static CI check).
- `.agents/teamwork/`, `PROJECT.md`, `TEST_INFRA.md`, `TEST_READY.md` stay strictly out of git commits.

---

## Code Layout

```
/home/antigravity/MoKarade/univers/
├── app/
│   ├── build.py                  # Clean standalone HTML bundler (no data2 hack)
│   ├── gen/                      # Pipeline-generated DATA payloads (pruned of dead keys)
│   ├── src/
│   │   ├── index.html            # Shell HTML + deduplicated CSS + Three.js 0.149.0 (SRI)
│   │   ├── 20_physics.js .. 29_cone.js  # Physics/astronomy modules (Prettier-formatted)
│   │   ├── 30_gen.js             # Shared math/color/format/procedural helpers
│   │   ├── 40_render.js          # WebGL2/Three.js renderer & shaders
│   │   └── 60_state.js .. 65_main.js    # Clean modular split of 60_app.js
│   └── test/
│       ├── _load.js              # Shared Node VM loader for JS tests
│       ├── *.test.js             # 26 quantitative physics tests (all with assertions)
│       └── *.py                  # Playwright WebGL2 screen/UI tests
├── natif/
│   ├── CMakeLists.txt            # Pinned stb SHA, Linux-safe portable tests + Win32/Vulkan app
│   ├── .clang-format             # Consistent C++20 formatting
│   ├── physique/                 # Standalone CMake C++20 physics lib & tests
│   ├── src/                      # Named `namespace univers`, RAII `fichier_mappe.h`
│   └── shaders/                  # GLSL 450 shaders (UB-free, color-space-correct)
├── pipeline/
│   ├── pyproject.toml            # 4 Python dependency profiles
│   ├── requirements-ci.txt       # Minimal CI requirements
│   ├── _paths.py                 # Shared repo/raw path resolver
│   ├── clean_gen_dead_keys.py    # Deterministic app/gen dead-key pruner w/ VM proof
│   ├── test_pipeline_stdlib.py   # Stdlib unit tests for pipeline contracts
│   └── {sources,natif,fusion,quantique,gravite,etoiles}/
├── tests/
│   └── e2e/                      # Requirement-driven opaque-box E2E suite (Tiers 1-4 + Tier 5)
├── infra/                        # Hardened Firebase config/deploy templates
├── .github/workflows/            # Hardened, fast, multi-language CI workflows
├── docs/                         # Synchronized docs + `audit-qualite-github.md`
├── eslint.config.mjs             # Minimal JS correctness linter config
├── .prettierrc                   # JS formatter config (eliminates // hazard)
├── CLAUDE.md / HANDOVER.md / CREDITS.md / README.md
└── dist/index.html               # Built standalone web application
```
