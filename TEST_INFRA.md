# Test Infrastructure — `MoKarade/univers` (Opaque-Box 4-Tier E2E Suite)

- **Owner Track**: E2E Testing Track (`e2e_orch_1`, parallel to Implementation Track M1–M6)
- **Repository Root**: `/home/antigravity/MoKarade/univers`
- **Canonical Entrypoint**: `python3 tests/e2e/run_e2e.py --tier <1|2|3|4|all> [--format text|json] [--feature F1..F7] [--test <ID_FILTER>] [--fail-fast] [--list]`
- **Date (UTC)**: `2026-11-26`

---

## 1. Overview & Design Principles

This document specifies the independent, requirement-driven, **opaque-box** 4-tier E2E verification infrastructure for `MoKarade/univers` derived from `.agents/teamwork/ORIGINAL_REQUEST.md`, `CLAUDE.md`, and `PROJECT.md § Feature Inventory`.

1. **Requirement-Driven, Not Module-Mirrored**: Tests are organized around **7 cohesive user-requirement feature areas (`F1–F7`)** and **4 progressive verification tiers**, testing public CLI commands, built standalone HTML artifacts, live browser runtime (`window.__U` + DOM + WebGL2), compiled C++20 executables, Python pipeline entrypoints, and repository configuration contracts.
2. **Dual-Track Honesty (Zero Weakened Assertions)**: Because this suite is built in parallel while Milestones M1–M6 remediate defects, tests **never** weaken thresholds, skip failing checks, or hardcode passes. Any unfixed defect MUST fail deterministically (`status: "FAIL"`, non-zero exit code `1`) with clear diagnostic output and optional informational `expected_milestone` metadata, and turn `PASS` once the owning milestone fixes the underlying requirement.
3. **Zero Repo Pollution & Zero Temp Leaks**: Every build artifact (HTML bundle, CMake build tree, ASan probe binary, synthetic fixture, screenshot) is written strictly inside a session-scoped `tempfile.mkdtemp(prefix="univers_e2e_")` (`chmod 0o700`) and cleaned up in `try/finally` + `atexit`. `dist/index.html` is NEVER overwritten.
4. **Opaque-Box Resilience to Refactors**: Tests never assume whether `app/src/60_app.js` is monolithic or split into `60_state.js..65_main.js`, never slice source lines by brittle line numbers or single-line regexes, and work cleanly across both legacy `window.__*` and unified `window.__ASSETS` overrides.

---

## 2. Verified Environment & Tool Matrix (`[Certain]`)

All tools below were verified directly on this Linux VM (`Ubuntu 24.04`, 2 vCPUs):

| Tool / Runtime | Verified Version | Usage in `tests/e2e/` | Constraints / Notes |
|---|---|---|---|
| `python3` | `3.12.16` | Runner, `tomllib` (TOML), `ast.parse`, `ThreadingHTTPServer`, Playwright client | **`PyYAML` and `numpy` are NOT installed** — never `import yaml` or `import numpy` in `tests/e2e/` |
| `ruby` | `3.2.3` | Zero-dependency YAML parser (`ruby -ryaml -rjson`, `YAML.safe_load(..., aliases: true)`) | Normalizes YAML 1.1 boolean key `true -> "on"` for GitHub Actions workflows |
| `node` | `v22.23.5` | `node --check`, Node `vm` `DATA` deep-equality & Proxy overwrite checks, `app/test/*.test.js` | Native `vm` & `assert` stdlib only |
| `eslint` | `v10.15.0` | F1 JS correctness linting (`eslint app/src/`) | Global CLI `/opt/nvm/current/bin/eslint`; requires repo `eslint.config.mjs` (M3) |
| `prettier` | `3.10.1` | F1 formatting & inline-`//` elimination (`prettier --check "app/src/*.js"`) | Global CLI `/opt/nvm/current/bin/prettier`; requires repo `.prettierrc` (M3) |
| `playwright` + `PIL` | `Playwright 1.65.2`, `Chromium 159`, `PIL 13.0.0` | F1/F3/F4/T3/T4 headless WebGL2 HDR rendering, UI layout, XSS & offline probes | Launches with `['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']` |
| `g++` / `clang++` | `GCC 13.3.0`, `Clang 18.1.3` | F5/T3/T4 dual-compiler C++20 builds (`-Werror`), ASan/UBSan probes, parity driver | Both compilers installed in `/usr/bin/` |
| `cmake` / `ninja` | `CMake 3.28.3`, `Ninja 1.11.1` | F5/T3/T4 out-of-source CMake builds in `/tmp` | `glslang` and `mingw-w64` are **NOT installed** locally |
| `valgrind` | `3.22.0` | F5/T4 memory/leak checks (`--leak-check=full --error-exitcode=1`) | Run only on fast data-free binaries (`essai_cosmologie`, `essai_interface`, `essai_systeme_solaire --noyau`) |

---

## 3. Suite Layout & Feature Mapping (`N = 7` Features × `4` Tiers = `109` Tests)

### 3.1 Directory Layout (`tests/e2e/`)
```text
tests/e2e/
├── run_e2e.py                   # Deterministic CLI runner (text/JSON, exit codes 0/1/2, hygiene check)
├── lib/
│   ├── __init__.py
│   ├── harness.py               # TempWorkspace, temp HTML builder, ThreadingHTTPServer, PlaywrightSession,
│   │                            #   run_cmd (timeout + process-group kill), yaml_load (ruby), JS // lexer
│   └── cpp_cache.py             # Session-scoped /tmp CMake (GCC+Clang) & ASan/UBSan probe build cache
├── tier1_f1_build_truth.py      # 6 tests: T1-F1-01..06
├── tier1_f2_physics.py          # 7 tests: T1-F2-01..07
├── tier1_f3_web_runtime.py      # 6 tests: T1-F3-01..06
├── tier1_f4_security_offline.py # 6 tests: T1-F4-01..06
├── tier1_f5_native_cpp.py       # 7 tests: T1-F5-01..07
├── tier1_f6_pipeline.py         # 6 tests: T1-F6-01..06
├── tier1_f7_ci_infra_docs.py    # 6 tests: T1-F7-01..06
├── tier2_f1_build_truth.py      # 6 tests: T2-F1-01..06
├── tier2_f2_physics.py          # 7 tests: T2-F2-01..07
├── tier2_f3_web_runtime.py      # 6 tests: T2-F3-01..06
├── tier2_f4_security_offline.py # 6 tests: T2-F4-01..06
├── tier2_f5_native_cpp.py       # 7 tests: T2-F5-01..07
├── tier2_f6_pipeline.py         # 6 tests: T2-F6-01..06
├── tier2_f7_ci_infra_docs.py    # 6 tests: T2-F7-01..06
├── tier3_cross_feature.py       # 14 tests: T3-CF-01..14
└── tier4_workflows.py           # 7 tests: T4-E2E-01..07
```

### 3.2 Coverage Matrix & Threshold Verification
| Feature / Tier | Scope | Tier 1 (min ≥ 5/feat) | Tier 2 (min ≥ 5/feat) | Tier 3 (min ≥ 10) | Tier 4 (min ≥ 6) | Total |
|---|---|---:|---:|---:|---:|---:|
| **F1** | Standalone Web Build, Bundle Integrity & Scientific Truth Guardrails | 6 | 6 | — | — | 12 |
| **F2** | Astronomical Physics Accuracy & Speed Contracts | 7 | 7 | — | — | 14 |
| **F3** | Interactive Web Runtime, WebGL2 Rendering & UI UX (Playwright) | 6 | 6 | — | — | 12 |
| **F4** | Web Security, DOM Hygiene & Offline / External Asset Resilience | 6 | 6 | — | — | 12 |
| **F5** | Portable Native C++20 Physics & Build Contracts | 7 | 7 | — | — | 14 |
| **F6** | Reproducible Data Pipeline Contracts | 6 | 6 | — | — | 12 |
| **F7** | CI/CD, Infrastructure, Attribution & Documentation Consistency | 6 | 6 | — | — | 12 |
| **Cross-Feature** | Pairwise interactions across `F1–F7` (`T3-CF-01..14`) | — | — | 14 | — | 14 |
| **Workflows** | Full multi-feature end-user scenarios (`T4-E2E-01..07`) | — | — | — | 7 | 7 |
| **TOTAL** | **All 7 Feature Areas × 4 Tiers** | **44** (≥ 35) | **44** (≥ 35) | **14** (≥ 10) | **7** (≥ 6) | **109** (≥ 86) |

---

## 4. CLI Runner Usage & Output Contract (`tests/e2e/run_e2e.py`)

### 4.1 Invocation & Flags
```bash
# Run a specific tier or all tiers (text report to stdout)
python3 tests/e2e/run_e2e.py --tier 1
python3 tests/e2e/run_e2e.py --tier 2
python3 tests/e2e/run_e2e.py --tier 3
python3 tests/e2e/run_e2e.py --tier 4
python3 tests/e2e/run_e2e.py --tier all

# Machine-parseable JSON output (stdout = pure valid JSON; diagnostics on stderr)
python3 tests/e2e/run_e2e.py --tier all --format json

# Scoped feature or test-ID execution & test catalog listing
python3 tests/e2e/run_e2e.py --tier 1 --feature F1,F5
python3 tests/e2e/run_e2e.py --tier all --test T2-F4-01
python3 tests/e2e/run_e2e.py --list
```

### 4.2 Strict Exit Codes
- **`0`**: Every selected test returned `PASS`, `errors == 0`, `temp_dirs_remaining == 0`, and `dist_sha256_unchanged == true`.
- **`1`**: One or more selected tests returned `FAIL` (genuine requirement failure, zero harness errors).
- **`2`**: Invalid CLI arguments, zero tests matched selection, harness/infrastructure crash (`ERROR`), or repo/temp hygiene violation.

### 4.3 JSON Report Schema (`--format json`)
```json
{
  "schema_version": "1.0",
  "timestamp_utc": "2026-11-26T15:30:00Z",
  "git_head": "<sha>",
  "cli": { "tier": "all", "features": ["F1","F2","F3","F4","F5","F6","F7"], "format": "json" },
  "summary": {
    "total": 109, "passed": 0, "failed": 0, "errors": 0, "duration_s": 0.0,
    "by_tier": { "1": {}, "2": {}, "3": {}, "4": {} },
    "by_feature": { "F1": {}, "F2": {}, "F3": {}, "F4": {}, "F5": {}, "F6": {}, "F7": {} }
  },
  "hygiene": {
    "temp_dirs_created": 1,
    "temp_dirs_remaining": 0,
    "dist_sha256_unchanged": true
  },
  "results": [
    {
      "id": "T1-F1-01",
      "tier": 1,
      "features": ["F1"],
      "title": "Standalone temp HTML build & placeholder elimination",
      "status": "PASS",
      "duration_s": 1.4,
      "expected_milestone": null,
      "message": "Built 16,636,755 B; markers absent; dist/index.html unchanged",
      "details": {}
    }
  ]
}
```

---

## 5. Harness Fixtures, Caching & Isolation Guarantees

1. **Session Temp Workspace (`TempWorkspace`)**:
   - Created once per `run_e2e.py` invocation via `tempfile.mkdtemp(prefix="univers_e2e_")` (`chmod 0o700`).
   - Removed strictly via `shutil.rmtree(self.root, ignore_errors=True)` in `finally:` + `atexit`. Never globs or deletes sibling `/tmp/teamwork_probe.*` directories.
   - Records `sha256(dist/index.html)` before and after execution to guarantee zero modification of `dist/index.html`.
2. **Cached Temp Web Build (`build_temp_html`)**:
   - Builds `python3 app/build.py <tmpdir>/web/index.html` once per session for read-only consumers (F3/F4/T3/T4), while F1 build tests (`T1-F1-01`, `T1-F1-02`, `T2-F1-02`, `T2-F1-03`) invoke `app/build.py` directly into dedicated sub-paths.
3. **Shared Local Loopback Server & Playwright SwiftShader Session (`PlaywrightSession`)**:
   - Runs one `http.server.ThreadingHTTPServer(('127.0.0.1', 0), ...)` serving the temp-built HTML + dynamic mock endpoints (`/mock/evil_ngc.json`, `/mock/fusion_centres.json`, `/mock/fusion_images.json`, etc.).
   - Launches **one** headless Chromium instance (`['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']`) torn down strictly in `finally:` + `atexit` (guaranteeing 0 orphaned Chromium processes).
   - Uses `window.__TIER = 0; window.__NOADAPT = true; window.__TILES = []; window.__PHOTOS = [];` and targeted regex route `re.compile(r'^https?://fonts\.(googleapis|gstatic)\.com/')` to abort Google Fonts (cutting boot time from ~26s to ~12–14s). Never uses a catch-all `**/*` route over the 16 MB HTML page.
   - Reuses a warm desktop page across read-only F3/F1/T3/T4 navigation/truth/UI tests (resetting state cleanly via `window.__U`), switches viewport for mobile tests, and uses dedicated isolated contexts for destructive tests (XSS, 404 storm, `WEBGL_lose_context` reload, CDN-blocked offline boot).
   - Triggers DOM interactions cleanly without SwiftShader main-thread click hangs (pausing `S.playing = false` and verifying hit-targets via `document.elementFromPoint`).
4. **Session-Scoped C++20 Build Cache (`tests/e2e/lib/cpp_cache.py`)**:
   - Lazily builds inside `<tmpdir>/cpp/`: `gcc_phys/`, `gcc_natif/`, `clang_phys/`, and `asan_probes/` (ASan+UBSan test driver for `LongTable`, `Rejeu`, `Spk`, `cosmologie`, `interface_outils`, plus JS↔C++ parity driver). Compiles once per session (~6–10s total) instead of recompiling per test.
5. **Subprocess Timeout & Process-Group Cleanup (`run_cmd`)**:
   - Every subprocess runs in its own session (`start_new_session=True`) with an explicit timeout (`15–90s`); on timeout, the entire process group is terminated (`SIGKILL`) cleanly and converted into an explicit test `FAIL` (when enforcing a performance SLA) or `ERROR` (unexpected crash).

---

## 6. Dual-Track Resilience Contract

- **No `60_app.js` Path Assumption**: Always discover JS files via `sorted(Path("app/src").glob("*.js"))` or `6*.js` and test via the built HTML / `window.__U` hooks.
- **Real Parsers Over Fragile Regexes**: `node --check`, Node `vm.Script` + ES6 `Proxy`, `eslint`, `prettier --check`, stateful JS lexer (ignoring strings/templates/block comments/regex literals) for `//` hazards, `ruby -ryaml -rjson` for YAML, Python `tomllib` for TOML, `ast.parse` for Python.
- **Asset Override Compatibility**: Non-F4 Playwright tests isolate external fetches via targeted regex routes; F4 explicitly tests both `window.__ASSETS` and legacy `window.__*` overrides plus URL scheme rejection.
- **Concurrent M1–M6 Workspace Safety**: `run_e2e.py` checks `dist/index.html` SHA-256 and its own temp-dir cleanup rather than spuriously failing when sibling Implementation Track milestones legitimately modify `app/`, `natif/`, `pipeline/`, `.github/`, `infra/`, or `docs/`.

---

## 7. Execution Time Budgets & Troubleshooting

| Run Command | Baseline (Pre-M1..M6) | Post-M1..M6 Target | Notes |
|---|---:|---:|---|
| `python3 tests/e2e/run_e2e.py --tier 1` | ~60–90 s | ~35–50 s | C++ build + fast JS tests + 1 warm Playwright boot + F4/F6/F7 |
| `python3 tests/e2e/run_e2e.py --tier 2` | ~70–100 s | ~40–55 s | Bounded SLA timeouts (15s) + ASan probes + context-loss & XSS |
| `python3 tests/e2e/run_e2e.py --tier 3` | ~45–65 s | ~30–45 s | Reuses session HTML/Playwright/C++ caches |
| `python3 tests/e2e/run_e2e.py --tier 4` | ~90–120 s | ~50–80 s | Includes 26-test parallel JS SLA (`65s` per-test cap) + dual-compiler C++ + Valgrind |
| `python3 tests/e2e/run_e2e.py --tier all` | ~2.5–3.5 min | ~1.5–2.0 min | Single shared HTML build, Chromium instance & C++ cache across all 109 tests |

**Troubleshooting**:
- Verify zero leftover Chromium processes: `pgrep -af chrom || true`
- Verify zero leftover E2E temp dirs: `ls -d /tmp/univers_e2e_* 2>/dev/null || echo clean`
- Verify `dist/index.html` unchanged: `git diff --stat dist/index.html`
