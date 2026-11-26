"""Tier 1 — F6: Reproducible Data Pipeline Contracts (6 tests)."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import tomllib
from typing import List, Tuple

from lib.harness import (
    APP_GEN,
    NATIF_DIR,
    PIPELINE_DIR,
    REPO_ROOT,
    E2ESession,
    TestCase,
    check,
    run_cmd,
)


def t1_f6_01_pipeline_syntax(session: E2ESession) -> Tuple[str, dict]:
    py_files = sorted(p for p in PIPELINE_DIR.rglob("*.py") if "__pycache__" not in p.parts)
    js_files = sorted(p for p in PIPELINE_DIR.rglob("*.js") if "__pycache__" not in p.parts)
    check(len(py_files) >= 60, f"Expected >= 60 Python pipeline files, got {len(py_files)}")

    py_errs: List[str] = []
    for p in py_files:
        try:
            ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except SyntaxError as exc:
            py_errs.append(f"{p.relative_to(REPO_ROOT)}:{exc.lineno}: {exc.msg}")

    js_errs: List[str] = []
    for p in js_files:
        r = run_cmd(["node", "--check", str(p)], timeout=15.0)
        if r.rc != 0:
            js_errs.append(f"{p.relative_to(REPO_ROOT)}: {r.stderr.strip()[:120]}")

    check(not py_errs and not js_errs, f"Syntax errors: py={py_errs}, js={js_errs}")
    return f"0 syntax errors across {len(py_files)} Python and {len(js_files)} JS pipeline files", {"py": len(py_files), "js": len(js_files)}


def t1_f6_02_test_build_gw_stdlib(session: E2ESession) -> Tuple[str, dict]:
    script = PIPELINE_DIR / "sources" / "test_build_gw.py"
    check(script.is_file(), f"Missing {script}")
    res = run_cmd(["python3", str(script)], timeout=20.0)
    check(not res.timed_out and res.rc == 0, f"test_build_gw.py failed (rc={res.rc}): {(res.stderr or res.stdout)[:300]}")
    check("RÉSULTAT : PASSE" in res.stdout and "ÉCHEC" not in res.stdout, f"Unexpected test_build_gw output: {res.stdout[:300]}")
    return f"pipeline/sources/test_build_gw.py PASS ({res.duration_s:.2f}s)", {}


def t1_f6_03_test_pipeline_stdlib(session: E2ESession) -> Tuple[str, dict]:
    script = PIPELINE_DIR / "test_pipeline_stdlib.py"
    check(script.is_file(), "Missing pipeline/test_pipeline_stdlib.py (M5 deliverable)")
    res = run_cmd(["python3", str(script)], timeout=30.0)
    check(not res.timed_out and res.rc == 0,
          f"pipeline/test_pipeline_stdlib.py failed (rc={res.rc}): {(res.stderr or res.stdout)[:400]}")
    return f"pipeline/test_pipeline_stdlib.py PASS ({res.duration_s:.2f}s)", {}


def t1_f6_04_pyproject_and_requirements(session: E2ESession) -> Tuple[str, dict]:
    toml_path = PIPELINE_DIR / "pyproject.toml"
    req_path = PIPELINE_DIR / "requirements-ci.txt"
    issues: List[str] = []
    if not toml_path.is_file():
        issues.append("missing pipeline/pyproject.toml")
    if not req_path.is_file():
        issues.append("missing pipeline/requirements-ci.txt")
    check(not issues, "; ".join(issues))

    try:
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except Exception as exc:
        check(False, f"Invalid TOML in pipeline/pyproject.toml: {exc}")
        return "", {}

    proj = data.get("project") or {}
    check(bool(proj.get("name")), "pipeline/pyproject.toml missing [project].name")
    opt = proj.get("optional-dependencies") or {}
    opt_keys = {k.lower() for k in opt.keys()}
    # Check 4 dependency profiles: core (either in dependencies or optional-dependencies['core']), astro, quantum, fusion (or fusion-cpu/fusion-gpu)
    has_core = "core" in opt_keys or bool(proj.get("dependencies"))
    has_astro = "astro" in opt_keys
    has_quantum = "quantum" in opt_keys
    has_fusion = any(k in opt_keys for k in ("fusion", "fusion-cpu", "fusion-gpu"))
    missing_profiles = [
        name for name, ok in (("core", has_core), ("astro", has_astro), ("quantum", has_quantum), ("fusion", has_fusion)) if not ok
    ]
    check(not missing_profiles, f"pipeline/pyproject.toml missing dependency profiles: {missing_profiles} (found {sorted(opt_keys)})")

    req_lines = [ln.strip() for ln in req_path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith("#")]
    check(len(req_lines) > 0 or len(req_path.read_text(encoding="utf-8").strip()) > 0, "pipeline/requirements-ci.txt is empty")
    return f"pipeline/pyproject.toml valid TOML (profiles={sorted(opt_keys)}); requirements-ci.txt present", {"profiles": sorted(opt_keys)}


def t1_f6_05_paths_helper_contract(session: E2ESession) -> Tuple[str, dict]:
    paths_py = PIPELINE_DIR / "_paths.py"
    check(paths_py.is_file(), "Missing pipeline/_paths.py (M5 deliverable)")
    probe = r"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ["E2E_PIPE_DIR"])
import _paths
res = {
    "repo_root": str(Path(_paths.REPO_ROOT).resolve()),
    "app_gen": str(Path(_paths.APP_GEN).resolve()),
    "app_src": str(Path(_paths.APP_SRC).resolve()),
    "pipeline_dir": str(Path(_paths.PIPELINE_DIR).resolve()),
    "raw_default": str(Path(_paths.raw_dir()).resolve()),
    "raw_cli": str(Path(_paths.raw_dir("/custom/cli/raw")).resolve()),
}
os.environ["UNIVERS_RAW"] = "/custom/env/raw"
res["raw_env"] = str(Path(_paths.raw_dir()).resolve())
res["raw_cli_over_env"] = str(Path(_paths.raw_dir("/custom/cli/raw")).resolve())
print(json.dumps(res))
"""
    clean_env = {"E2E_PIPE_DIR": str(PIPELINE_DIR)}
    # Ensure UNIVERS_RAW isn't already set in parent env
    r = run_cmd(["python3", "-c", probe], timeout=15.0, env={**clean_env, "UNIVERS_RAW": ""})
    check(r.rc == 0, f"pipeline/_paths.py probe failed: {r.stderr[:300]}")
    info = json.loads(r.stdout.strip())
    check(Path(info["repo_root"]) == REPO_ROOT.resolve(), f"REPO_ROOT mismatch: {info}")
    check(Path(info["app_gen"]) == APP_GEN.resolve(), f"APP_GEN mismatch: {info}")
    check(Path(info["app_src"]) == (REPO_ROOT / "app" / "src").resolve(), f"APP_SRC mismatch: {info}")
    check(Path(info["pipeline_dir"]) == PIPELINE_DIR.resolve(), f"PIPELINE_DIR mismatch: {info}")
    check(Path(info["raw_default"]) == (REPO_ROOT / "univers-raw").resolve(), f"Default raw_dir mismatch: {info['raw_default']}")
    check(info["raw_env"] == "/custom/env/raw", f"UNIVERS_RAW override ignored: {info['raw_env']}")
    check(info["raw_cli_over_env"] == "/custom/cli/raw", f"CLI arg did not override UNIVERS_RAW: {info['raw_cli_over_env']}")
    src_txt = paths_py.read_text(encoding="utf-8")
    for forbidden in ("/mnt/user-data", "LOCALAPPDATA"):
        check(forbidden not in src_txt, f"Forbidden hardcoded path token {forbidden!r} in pipeline/_paths.py")
    return "pipeline/_paths.py contract & raw_dir precedence (CLI > UNIVERS_RAW > univers-raw) PASS", info


def t1_f6_06_stdlib_generators_reproducible(session: E2ESession) -> Tuple[str, dict]:
    tmp = session.workspace.subdir("t1_f6_06")

    # 1. ref_ephem.py writes directly to CLI arg <tmp>/ref_ephem.txt
    ref_out = tmp / "ref_ephem.txt"
    r_ref = run_cmd(["python3", str(PIPELINE_DIR / "natif" / "ref_ephem.py"), str(ref_out)], timeout=20.0)
    check(r_ref.rc == 0 and ref_out.is_file(), f"ref_ephem.py failed: {r_ref.stderr[:250]}")
    ref_lines = [ln for ln in ref_out.read_text(encoding="ascii").splitlines() if ln.strip()]
    check(len(ref_lines) == 112, f"Expected 112 ref_ephem lines, got {len(ref_lines)}")

    # 2. Run pure-stdlib generators redirected strictly into <tmp> (ZERO repo writes!)
    repro_script = r"""
import importlib.util, json, os, sys
from pathlib import Path

repo = Path(os.environ["E2E_REPO"])
tmp = Path(os.environ["E2E_TMP"])
sys.path.insert(0, str(repo / "pipeline"))

def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

checks = {}

# build_zcol.py -> data16.js
m_z = load_mod("build_zcol", repo / "pipeline" / "build_zcol.py")
out_z = tmp / "data16.js"
m_z.OUT = out_z
m_z.main()
checks["data16.js"] = (out_z.read_bytes() == (repo / "app" / "gen" / "data16.js").read_bytes(), out_z.stat().st_size)

# build_bbcol.py -> data15.js
m_b = load_mod("build_bbcol", repo / "pipeline" / "build_bbcol.py")
out_b = tmp / "data15.js"
m_b.OUT_FILE = out_b
m_b.main()
checks["data15.js"] = (out_b.read_bytes() == (repo / "app" / "gen" / "data15.js").read_bytes(), out_b.stat().st_size)

# build_sun_rgb.py -> sun_rgb.js
m_s = load_mod("build_sun_rgb", repo / "pipeline" / "build_sun_rgb.py")
out_s = tmp / "sun_rgb.js"
m_s.DST = out_s
if hasattr(m_s, "main"):
    m_s.main()
checks["sun_rgb.js"] = (out_s.is_file() and out_s.read_bytes() == (repo / "app" / "gen" / "sun_rgb.js").read_bytes(),
                        out_s.stat().st_size if out_s.is_file() else 0)

# natif/nbody_donnees.py -> nbody_donnees.h & essais/nbody_ref.h
fake_repo = tmp / "fake_repo"
(fake_repo / "natif" / "physique" / "essais").mkdir(parents=True, exist_ok=True)
m_n = load_mod("nbody_donnees", repo / "pipeline" / "natif" / "nbody_donnees.py")
m_n.REPO_ROOT = fake_repo
if hasattr(m_n, "ROOT"):
    m_n.ROOT = str(fake_repo)
m_n.main()
h1 = fake_repo / "natif" / "physique" / "nbody_donnees.h"
h2 = fake_repo / "natif" / "physique" / "essais" / "nbody_ref.h"
checks["nbody_donnees.h"] = (h1.is_file() and h1.read_bytes() == (repo / "natif" / "physique" / "nbody_donnees.h").read_bytes(),
                             h1.stat().st_size if h1.is_file() else 0)
checks["nbody_ref.h"] = (h2.is_file() and h2.read_bytes() == (repo / "natif" / "physique" / "essais" / "nbody_ref.h").read_bytes(),
                         h2.stat().st_size if h2.is_file() else 0)

print(json.dumps(checks))
"""
    r_rep = run_cmd(
        ["python3", "-c", repro_script],
        timeout=30.0,
        env={"E2E_REPO": str(REPO_ROOT), "E2E_TMP": str(tmp)},
    )
    check(r_rep.rc == 0, f"Stdlib generator reproduction script failed: {r_rep.stderr[:400]}")
    last_line = [ln for ln in r_rep.stdout.strip().splitlines() if ln.strip().startswith("{")][-1]
    checks = json.loads(last_line)
    bad = [k for k, (eq, _) in checks.items() if not eq]
    check(not bad, f"Byte-exact reproducibility mismatch for: {bad}", checks)
    return f"All 5 pure-stdlib generators byte-exact + ref_ephem.py ({len(ref_lines)} lines) PASS", checks


def get_tests() -> List[TestCase]:
    return [
        TestCase("T1-F6-01", 1, ["F6"], "Full pipeline syntax validity (ast.parse on .py & node --check on .js)", t1_f6_01_pipeline_syntax),
        TestCase("T1-F6-02", 1, ["F6"], "Existing pure-stdlib GW test (pipeline/sources/test_build_gw.py)", t1_f6_02_test_build_gw_stdlib),
        TestCase("T1-F6-03", 1, ["F6"], "Stdlib pipeline unit test suite (pipeline/test_pipeline_stdlib.py)", t1_f6_03_test_pipeline_stdlib, expected_milestone="M5"),
        TestCase("T1-F6-04", 1, ["F6"], "Dependency manifests (pipeline/pyproject.toml 4 profiles + requirements-ci.txt)", t1_f6_04_pyproject_and_requirements, expected_milestone="M5"),
        TestCase("T1-F6-05", 1, ["F6"], "Shared path resolver contract (pipeline/_paths.py & raw_dir precedence)", t1_f6_05_paths_helper_contract, expected_milestone="M5"),
        TestCase("T1-F6-06", 1, ["F6"], "Pure-stdlib generator byte-exact reproducibility in temp dir", t1_f6_06_stdlib_generators_reproducible),
    ]
