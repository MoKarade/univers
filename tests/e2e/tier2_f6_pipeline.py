"""Tier 2 — F6: Pipeline Edge Cases, Formatting Resilience, Portability & Hygiene (6 tests)."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
from typing import List, Tuple

from lib.harness import (
    PIPELINE_DIR,
    REPO_ROOT,
    E2ESession,
    TestCase,
    check,
    run_cmd,
)


def t2_f6_01_tile_manifest_multiline_split_resilience(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []
    converters = ("etoiles.py", "asteroides.py", "galaxies.py")
    for fname in converters:
        p = PIPELINE_DIR / "natif" / fname
        txt = p.read_text(encoding="utf-8")
        if re.search(r"['\"]60_app\.js['\"]", txt):
            issues.append(f"pipeline/natif/{fname} still hardcodes '60_app.js' (breaks on M3 split; PIPE-BUG-04)")

    # Dynamic fixture test: synthetic split + Prettier-formatted multi-line `app/src/61_assets.js`
    # with double quotes, newlines, and trailing commas!
    tmp = session.workspace.subdir("t2_f6_01")
    fake_src = tmp / "app" / "src"
    fake_src.mkdir(parents=True, exist_ok=True)
    (fake_src / "60_state.js").write_text("const S = {};\n", encoding="utf-8")
    (fake_src / "61_assets.js").write_text(
        '''const TILE_MANIFEST = /*__TILES__*/ [
  {
    kind: "ast",
    id: "02679a4195f9f4142a2a12ddcad32982",
    n: 123530,
    mb: 4.6,
    names: "37ecb71973bf22d6d05e33f12ebf5653",
  },
  {
    kind: "star",
    id: "c8120218b39b4317da101cd71ff778d5",
    n: 1300000,
    mb: 19.1,
  },
  {
    kind: "gal",
    id: "d140e2dfab0788aa99836e05d2bd9533",
    n: 928536,
    mb: 7.4,
  },
];
''',
        encoding="utf-8",
    )

    # Probe via pipeline/_paths.py helper (if M5 exposed read_tile_manifest/tile_manifest) OR via converters
    probe = r"""
import importlib, importlib.util, json, os, sys, types
from pathlib import Path

repo = Path(os.environ["E2E_REPO"])
fake_repo = Path(os.environ["E2E_FAKE_REPO"])
sys.path.insert(0, str(repo / "pipeline"))

# Minimal numpy stub so converters can be imported in stdlib-only VM
if "numpy" not in sys.modules:
    sys.modules["numpy"] = types.ModuleType("numpy")

out = {"helper_found": False, "stars": 0, "gals": 0, "asts": 0, "ast_names": None, "err": None}
try:
    import _paths
    fn = getattr(_paths, "read_tile_manifest", None) or getattr(_paths, "tile_manifest", None) or getattr(_paths, "load_tile_manifest", None)
    if callable(fn):
        out["helper_found"] = True
        try:
            tiles = fn(fake_repo / "app" / "src")
        except TypeError:
            orig = getattr(_paths, "APP_SRC", None)
            _paths.APP_SRC = fake_repo / "app" / "src"
            try:
                tiles = fn()
            finally:
                if orig is not None:
                    _paths.APP_SRC = orig
        out["stars"] = sum(1 for t in tiles if t.get("kind") == "star")
        out["gals"] = sum(1 for t in tiles if t.get("kind") == "gal")
        asts = [t for t in tiles if t.get("kind") == "ast"]
        out["asts"] = len(asts)
        out["ast_names"] = asts[0].get("names") if asts else None
except Exception as exc:
    out["err"] = str(exc)

print(json.dumps(out))
"""
    r = run_cmd(
        ["python3", "-c", probe],
        timeout=15.0,
        env={"E2E_REPO": str(REPO_ROOT), "E2E_FAKE_REPO": str(tmp)},
    )
    if r.rc != 0:
        issues.append(f"TILE_MANIFEST dynamic probe crashed: {r.stderr[:250]}")
    else:
        info = json.loads(r.stdout.strip().splitlines()[-1])
        if info.get("err"):
            issues.append(f"TILE_MANIFEST parser error on multi-line split fixture: {info['err']}")
        elif info["helper_found"]:
            if not (info["stars"] == 1 and info["gals"] == 1 and info["asts"] == 1 and info["ast_names"] == "37ecb71973bf22d6d05e33f12ebf5653"):
                issues.append(f"Multi-line split fixture parsed wrong counts: {info}")
        else:
            # Verify converters themselves use re.S/re.DOTALL & glob('6*.js')
            for fname in converters:
                txt = (PIPELINE_DIR / "natif" / fname).read_text(encoding="utf-8")
                if "re.S" not in txt and "re.DOTALL" not in txt:
                    issues.append(f"pipeline/natif/{fname} lacks re.S/re.DOTALL for multi-line TILE_MANIFEST")

    check(not issues, "; ".join(issues[:6]), {"issues": issues})
    return "pipeline/natif/{etoiles,asteroides,galaxies}.py resilient to split & multi-line Prettier TILE_MANIFEST", {}


def t2_f6_02_no_hardcoded_paths_unsafe_pip_or_brouillon(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []
    brouillons = [str(p.relative_to(REPO_ROOT)) for p in PIPELINE_DIR.rglob("*.brouillon")]
    if brouillons:
        issues.append(f"Draft .brouillon file(s) present: {brouillons}")

    bad_patterns = (
        ("/mnt/user-data", re.compile(r"/mnt/user-data")),
        ("--break-system-packages", re.compile(r"--break-system-packages")),
        ("LOCALAPPDATA", re.compile(r"\bLOCALAPPDATA\b")),
        ("stale ../gen write", re.compile(r"['\"]\.\./gen(?:/|['\"])")),
        ("hardcoded /tmp/ path", re.compile(r"['\"]/tmp/[a-zA-Z0-9_.-]+")),
    )
    for p in sorted(list(PIPELINE_DIR.rglob("*.py")) + list(PIPELINE_DIR.rglob("*.js"))):
        if "__pycache__" in p.parts or p.name == "test_pipeline_stdlib.py":
            continue
        txt = p.read_text(encoding="utf-8")
        rel = str(p.relative_to(REPO_ROOT))
        for label, pat in bad_patterns:
            if pat.search(txt):
                issues.append(f"{rel}: contains {label}")

    check(not issues, f"{len(issues)} pipeline hygiene violations: {'; '.join(issues[:8])}", {"count": len(issues), "sample": issues[:15]})
    return "0 .brouillon files and 0 hardcoded personal paths / unsafe pip flags across pipeline/", {}


def t2_f6_03_proton_pdf_no_np_trapz(session: E2ESession) -> Tuple[str, dict]:
    p = PIPELINE_DIR / "quantique" / "proton_pdf.py"
    check(p.is_file(), f"Missing {p}")
    txt = p.read_text(encoding="utf-8")
    hits = [i + 1 for i, ln in enumerate(txt.splitlines()) if "np.trapz" in ln or "numpy.trapz" in ln]
    check(not hits, f"pipeline/quantique/proton_pdf.py still calls removed NumPy 2.x np.trapz on line(s) {hits} (PIPE-BUG-01)")
    return "pipeline/quantique/proton_pdf.py free of deprecated np.trapz (NumPy 2.x safe)", {}


def t2_f6_04_fusion_bin_16byte_validation(session: E2ESession) -> Tuple[str, dict]:
    script = PIPELINE_DIR / "natif" / "fusion_bin.py"
    tmp = session.workspace.subdir("t2_f6_04")
    issues: List[str] = []

    def mk_fusion(subdir: Path, fname: str) -> Path:
        subdir.mkdir(parents=True, exist_ok=True)
        data = {
            "t": [0.0, 0.02],
            "traceurs": ["sun"],
            "quantum_kpc": 0.025,
            "fusion_ga": 5.44,
            "derive_max": 0.0011,
            "affichees": [2, 2, 0, 0],
            "centres": [
                [[0, 0, 0], [-385.352, 623.003, -287.592], [0, 0, 0], [-1.0, -41.0, -27.8]],
                [[0, 0, 0], [-380.0, 620.0, -285.0], [0, 0, 0], [-2.0, -40.0, -27.0]],
            ],
            "traceurs_pos": [[[0, 0, 0]], [[1, 0, 0]]],
            "fichiers": [[fname, 2]],
        }
        (subdir / "fusion.json").write_text(json.dumps(data), encoding="utf-8")
        return subdir

    # (a) Valid <= 16-byte filename
    d_ok = mk_fusion(tmp / "ok", "kf_000.bin")
    out_ok = tmp / "ok_out.bin"
    r_ok = run_cmd(["python3", str(script), str(d_ok), str(out_ok)], timeout=15.0)
    expected_sz = 12 * 8 + 2 * 12 * 8 + 2 * 1 * 3 * 8 + 8 + 1 * 24  # 368 bytes
    if r_ok.rc != 0 or not out_ok.is_file() or out_ok.stat().st_size != expected_sz:
        issues.append(f"valid fusion.json failed: rc={r_ok.rc}, size={out_ok.stat().st_size if out_ok.is_file() else -1} (expected {expected_sz})")

    # (b) > 16-byte filename MUST be rejected with non-zero exit (never silently corrupt!)
    d_long = mk_fusion(tmp / "longname", "kf_filename_longer_than_16_bytes.bin")
    out_long = tmp / "long_out.bin"
    r_long = run_cmd(["python3", str(script), str(d_long), str(out_long)], timeout=15.0)
    if r_long.rc == 0:
        issues.append(f"fusion_bin.py silently accepted >16-byte filename with exit 0 (wrote {out_long.stat().st_size if out_long.is_file() else 0} B; PIPE-BUG-05)")

    # (c) Missing fusion.json -> non-zero exit
    d_miss = tmp / "missing"
    d_miss.mkdir(parents=True, exist_ok=True)
    r_miss = run_cmd(["python3", str(script), str(d_miss), str(tmp / "miss.bin")], timeout=15.0)
    if r_miss.rc == 0:
        issues.append("fusion_bin.py exited 0 on missing fusion.json")

    check(not issues, "; ".join(issues))
    return f"fusion_bin.py writes exact {expected_sz} B on valid input and rejects >16-byte names & missing input", {}


def t2_f6_05_calcul_atomic_and_gpu_overflow_guards(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []

    # (a) pipeline/fusion/calcul.py must not do unclosed `json.dump(..., open(...))` before os.replace
    calc_txt = (PIPELINE_DIR / "fusion" / "calcul.py").read_text(encoding="utf-8")
    if re.search(r"json\.dump\s*\([^)]*open\s*\(", calc_txt):
        issues.append("pipeline/fusion/calcul.py still uses unclosed inline open() inside json.dump before os.replace (PIPE-BUG-02)")

    # (b) pipeline/fusion/gravite_gpu.py must track stack overflow instead of silently truncating at sp < 158
    gpu_txt = (PIPELINE_DIR / "fusion" / "gravite_gpu.py").read_text(encoding="utf-8")
    if re.search(r"if\s*\(\s*sp\s*<\s*158\s*\)", gpu_txt) and not re.search(r"overflow|debord|atomicAdd", gpu_txt, re.IGNORECASE):
        issues.append("pipeline/fusion/gravite_gpu.py silently drops CUDA tree nodes when sp >= 158 without overflow tracking (PIPE-BUG-03)")

    # (c) pipeline/natif/etoiles.py data_keys works cleanly (whether defined locally or imported from _paths.py)
    probe = r"""
import importlib.util, json, os, sys, types
from pathlib import Path
repo = Path(os.environ["E2E_REPO"])
sys.path.insert(0, str(repo / "pipeline"))
if "numpy" not in sys.modules:
    sys.modules["numpy"] = types.ModuleType("numpy")
spec = importlib.util.spec_from_file_location("natif_etoiles", repo / "pipeline" / "natif" / "etoiles.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
fn = getattr(mod, "data_keys", None)
if not callable(fn):
    print(json.dumps({"ok": False, "err": "data_keys not callable on pipeline/natif/etoiles.py"}))
else:
    d = fn(["STARS_N", "M_GAL2ECL"])
    print(json.dumps({"ok": d.get("STARS_N", 0) >= 58966 and isinstance(d.get("M_GAL2ECL"), list), "stars_n": d.get("STARS_N")}))
"""
    r_dk = run_cmd(["python3", "-c", probe], timeout=15.0, env={"E2E_REPO": str(REPO_ROOT)})
    if r_dk.rc != 0:
        issues.append(f"pipeline/natif/etoiles.py data_keys behavioral check crashed: {r_dk.stderr[:200]}")
    else:
        dk_info = json.loads(r_dk.stdout.strip().splitlines()[-1])
        if not dk_info.get("ok"):
            issues.append(f"pipeline/natif/etoiles.py data_keys failed: {dk_info}")

    check(not issues, "; ".join(issues))
    return "calcul.py Windows-safe atomic write, gravite_gpu.py overflow counter & etoiles.py data_keys PASS", {}


def t2_f6_06_build_gw_edge_cases_offline(session: E2ESession) -> Tuple[str, dict]:
    probe = r"""
import importlib.util, json, os
from pathlib import Path

spec = importlib.util.spec_from_file_location("build_gw", Path(os.environ["E2E_REPO"]) / "pipeline" / "sources" / "build_gw.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# 1. Empty dict
assert mod.select({}) == [], "empty dict failed"

# 2. p_astro=None retained; p_astro=0.49 dropped; unknown catalog dropped; version & catalog precedence
evs = {
    "a1": {"commonName": "GW1", "catalog.shortName": "GWTC-1-confident", "version": 1, "GPS": 1126259462.4, "p_astro": 0.99, "mass_1_source": None},
    "a2": {"commonName": "GW1", "catalog.shortName": "GWTC-2.1-confident", "version": 1, "GPS": 1126259462.4, "p_astro": 0.99, "mass_1_source": 35.6},
    "a3": {"commonName": "GW1", "catalog.shortName": "GWTC-2.1-confident", "version": 2, "GPS": 1126259462.4, "p_astro": 0.99, "mass_1_source": 36.0},
    "b1": {"commonName": "GW_LOW", "catalog.shortName": "GWTC-3-confident", "version": 1, "GPS": 1200000000.0, "p_astro": 0.49},
    "c1": {"commonName": "GW_NULL_PA", "catalog.shortName": "GWTC-3-confident", "version": 1, "GPS": 1200000001.0, "p_astro": None},
    "d1": {"commonName": "GW_MARGINAL", "catalog.shortName": "GWTC-3-marginal", "version": 1, "GPS": 1200000002.0, "p_astro": 0.99},
}
sel = mod.select(evs)
names = [e["commonName"] for e in sel]
assert names == ["GW1", "GW_NULL_PA"], f"Unexpected selected names: {names}"
assert sel[0]["version"] == 2 and sel[0]["mass_1_source"] == 36.0, "Version/catalog precedence failed"
assert mod.triplet({"mass_1_source": None}, "mass_1_source") is None, "Null triplet failed"

# 3. Leap second boundary (2017-01-01T00:00:00Z = GPS 1167264018 with 18s leap; 1s before uses 17s leap)
iso_before = mod.gps_to_iso(mod.LEAP_2017_GPS - 1)
iso_at = mod.gps_to_iso(mod.LEAP_2017_GPS)
assert iso_at == "2017-01-01T00:00:00Z", f"Leap boundary mismatch: {iso_at}"
assert iso_before == "2017-01-01T00:00:00Z" or iso_before.startswith("2016-12-31T23:59:59"), f"Pre-leap bad: {iso_before}"
print(json.dumps({"ok": True, "names": names, "iso_before": iso_before, "iso_at": iso_at}))
"""
    r = run_cmd(["python3", "-c", probe], timeout=15.0, env={"E2E_REPO": str(REPO_ROOT)})
    check(r.rc == 0, f"build_gw.py edge-case probe failed: {r.stderr[:300]}")
    info = json.loads(r.stdout.strip().splitlines()[-1])
    return f"build_gw.py offline edge cases PASS (empty, null fields, version rank, leap boundary {info['iso_at']})", info


def get_tests() -> List[TestCase]:
    return [
        TestCase("T2-F6-01", 2, ["F6"], "TILE_MANIFEST resilience to split files & multi-line Prettier formatting", t2_f6_01_tile_manifest_multiline_split_resilience, expected_milestone="M5"),
        TestCase("T2-F6-02", 2, ["F6"], "Zero hardcoded personal/unsafe paths, --break-system-packages or .brouillon files", t2_f6_02_no_hardcoded_paths_unsafe_pip_or_brouillon, expected_milestone="M5"),
        TestCase("T2-F6-03", 2, ["F6"], "NumPy 2.x compatibility: zero np.trapz in pipeline/quantique/proton_pdf.py", t2_f6_03_proton_pdf_no_np_trapz, expected_milestone="M5"),
        TestCase("T2-F6-04", 2, ["F6"], "pipeline/natif/fusion_bin.py 16-byte filename validation & missing-file rejection", t2_f6_04_fusion_bin_16byte_validation, expected_milestone="M5"),
        TestCase("T2-F6-05", 2, ["F6"], "calcul.py atomic write, gravite_gpu.py overflow tracking & etoiles.py data_keys", t2_f6_05_calcul_atomic_and_gpu_overflow_guards, expected_milestone="M5"),
        TestCase("T2-F6-06", 2, ["F6"], "pipeline/sources/build_gw.py offline edge cases (empty, nulls, rank, leap second)", t2_f6_06_build_gw_edge_cases_offline),
    ]
