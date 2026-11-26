"""Tier 1 — F2: Astronomical Physics Accuracy & Truthfulness Contracts (7 tests)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
from typing import Dict, List, Tuple

from lib.harness import (
    APP_SRC,
    APP_TEST,
    REPO_ROOT,
    E2ESession,
    TestCase,
    check,
    node_eval_json,
    run_cmd,
)

# Shared Node snippet that loads built-HTML DATA + physics/gen modules cleanly (refactor-safe)
_NODE_LOAD_PHYSICS_PREAMBLE = r"""
const fs = require('fs'), path = require('path'), vm = require('vm');
const html = fs.readFileSync(process.env.E2E_HTML, 'utf8');
const srcDir = process.env.E2E_SRC_DIR;
const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
let m, dataCode = null;
while ((m = re.exec(html)) !== null) {
  if (!/\bsrc\s*=/i.test(m[1])) { dataCode = m[2]; break; }
}
const ctx = vm.createContext({
  console, Math, Date, Number, Array, Object, Float32Array, Float64Array, Uint8Array, Uint16Array, Uint32Array, Int8Array, Int16Array, Int32Array,
  atob: s => Buffer.from(s, 'base64').toString('binary'),
});
vm.runInContext(dataCode.replace(/^const DATA\b/m, 'var DATA'), ctx);
const physFiles = fs.readdirSync(srcDir).filter(f => /^[23]\d_.*\.js$/.test(f)).sort();
for (const f of physFiles) {
  const code = fs.readFileSync(path.join(srcDir, f), 'utf8')
    .replace(/^const /gm, 'var ')
    .replace(/^let /gm, 'var ');
  vm.runInContext(code, ctx, { filename: f });
}
"""


def _run_js_tests_parallel(names: List[str], timeout_per_test: float = 30.0) -> Dict[str, Tuple[int, float, str]]:
    def _one(name: str) -> Tuple[str, Tuple[int, float, str]]:
        p = APP_TEST / name
        res = run_cmd(["node", str(p)], cwd=REPO_ROOT, timeout=timeout_per_test)
        err_snip = (res.stderr or res.stdout).strip().splitlines()[-3:]
        return name, (res.rc if not res.timed_out else -9, res.duration_s, " | ".join(err_snip))

    out: Dict[str, Tuple[int, float, str]] = {}
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(names)))) as ex:
        for name, tup in ex.map(_one, names):
            out[name] = tup
    return out


def t1_f2_01_ephemerides_de440(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    js = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    const R = JSON.parse(fs.readFileSync(process.env.E2E_REF, 'utf8'));
    const norm = v => Math.hypot(v[0], v[1], v[2]);
    const sep = (a, b) => Math.acos(Math.max(-1, Math.min(1, (a[0]*b[0]+a[1]*b[1]+a[2]*b[2]) / (norm(a)*norm(b))))) / ctx.DEG * 3600;
    const worst = {}, wd = {};
    R.T.forEach((T, i) => {
      const st = ctx.solarSystemAt(T, null, 0);
      const mine = {
        mercury: st.planets.mercury.pos, venus: st.planets.venus.pos, earth: st.earth,
        mars: st.planets.mars.pos, jupiter: st.planets.jupiter.pos, saturn: st.planets.saturn.pos,
        uranus: st.planets.uranus.pos, neptune: st.planets.neptune.pos, moon: st.moonGeo,
      };
      for (const k in mine) {
        worst[k] = Math.max(worst[k] || 0, sep(mine[k], R.ref[k][i]));
        wd[k] = Math.max(wd[k] || 0, Math.abs(norm(mine[k]) - norm(R.ref[k][i])) * ctx.AU / 1e3);
      }
    });
    console.log(JSON.stringify({ dates: R.T.length, worst, moonDistKm: wd.moon }));
    """
    nres, data = node_eval_json(
        js,
        timeout=30.0,
        env={"E2E_HTML": str(html_path), "E2E_SRC_DIR": str(APP_SRC), "E2E_REF": str(APP_TEST / "ref_de440.json")},
    )
    check(nres.rc == 0 and data is not None, f"DE440 check failed: {nres.stderr[:300]}")
    limits = {
        "mercury": 1.0, "venus": 1.0, "earth": 1.0, "mars": 1.0,
        "jupiter": 1.0, "saturn": 1.1, "uranus": 1.7, "neptune": 2.6, "moon": 7.6,
    }
    bad = [f"{k}={data['worst'][k]:.2f}\" (max {lim}\")" for k, lim in limits.items() if data["worst"][k] > lim]
    if data["moonDistKm"] > 9.5:
        bad.append(f"moonDist={data['moonDistKm']:.2f} km (max 9.5 km)")
    check(not bad, f"DE440 tolerances exceeded: {', '.join(bad)}", data)
    return f"70 DE440 dates 1851-2149 PASS (Neptune {data['worst']['neptune']:.2f}\", Moon {data['worst']['moon']:.2f}\" / {data['moonDistKm']:.1f} km)", data


def t1_f2_02_cosmology_and_lightcone(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    js = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    const C = ctx.buildCosmo(ctx.PLANCK);
    const age = -C.tBang;
    const c0 = ctx.cosmoAt(C, 0);
    console.log(JSON.stringify({ age, H0: ctx.PLANCK.H0, a0: c0.a, H_today: c0.H }));
    """
    nres, info = node_eval_json(
        js, timeout=20.0, env={"E2E_HTML": str(html_path), "E2E_SRC_DIR": str(APP_SRC)}
    )
    check(nres.rc == 0 and info is not None, f"Cosmology probe failed: {nres.stderr[:300]}")
    check(abs(info["age"] - 13.787) <= 0.05, f"Planck age out of range: {info['age']:.4f} Ga")
    check(abs(info["H0"] - 67.4) < 1e-6, f"Expected H0=67.4, got {info['H0']}")
    check(abs(info["a0"] - 1.0) < 1e-6, f"Expected a(0)=1.0, got {info['a0']}")

    cone = run_cmd(["node", str(APP_TEST / "cone.test.js")], cwd=REPO_ROOT, timeout=20.0)
    check(not cone.timed_out and cone.rc == 0, f"cone.test.js failed (rc={cone.rc}): {(cone.stderr or cone.stdout)[-300:]}")
    return f"Planck age={info['age']:.4f} Ga, H0={info['H0']}, cone.test.js PASS ({cone.duration_s:.2f}s)", info


def t1_f2_03_lensing_and_dust(session: E2ESession) -> Tuple[str, dict]:
    res = _run_js_tests_parallel(["lens.test.js", "dust.test.js"], timeout_per_test=30.0)
    bad = [f"{k} rc={rc} ({msg})" for k, (rc, _, msg) in res.items() if rc != 0]
    check(not bad, f"Lensing/dust tests failed: {'; '.join(bad)}", res)
    return f"lens.test.js ({res['lens.test.js'][1]:.2f}s) & dust.test.js ({res['dust.test.js'][1]:.2f}s) PASS", {}


def t1_f2_04_quantum_and_micro(session: E2ESession) -> Tuple[str, dict]:
    res = _run_js_tests_parallel(["proton.test.js", "orbitales.test.js", "noyau.test.js"], timeout_per_test=25.0)
    bad = [f"{k} rc={rc} ({msg})" for k, (rc, _, msg) in res.items() if rc != 0]
    check(not bad, f"Quantum/micro tests failed: {'; '.join(bad)}", res)
    return f"proton ({res['proton.test.js'][1]:.2f}s), orbitales ({res['orbitales.test.js'][1]:.2f}s), noyau ({res['noyau.test.js'][1]:.2f}s) PASS", {}


def t1_f2_05_bary_color_fate_oort_merger(session: E2ESession) -> Tuple[str, dict]:
    names = [
        "bary.test.js", "bbcol.test.js", "zcol.test.js", "engulf.test.js",
        "destin.test.js", "oort.test.js", "fusion_rejeu.test.js", "fusion_etoiles.test.js",
    ]
    res = _run_js_tests_parallel(names, timeout_per_test=30.0)
    bad = [f"{k} rc={rc} ({msg})" for k, (rc, _, msg) in res.items() if rc != 0]
    check(not bad, f"Physics suite failures: {'; '.join(bad)}", res)
    return f"All {len(names)}/{len(names)} fast quantitative JS physics tests PASS", {k: round(v[1], 2) for k, v in res.items()}


def t1_f2_06_transit_mercury_2032(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    js = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    const R = JSON.parse(fs.readFileSync(process.env.E2E_REF, 'utf8'));
    const jdOf = (d, hm) => { const [y, m, dd] = d.split('-').map(Number), [h, mi] = hm.split(':').map(Number); return Date.UTC(y, m - 1, dd, h, mi) / 864e5 + 2440587.5; };
    const t0 = Date.now();
    const calc = ctx.evTransits('mercury', jdOf('2032-01-01', '00:00'), jdOf('2033-12-31', '00:00'));
    const ms = Date.now() - t0;
    const ref2032 = R.mercury.find(x => x.date === '2032-11-13');
    const jRef = jdOf(ref2032.date, ref2032.greatest_ut);
    const hit = calc.find(x => Math.abs(x.jd - jRef) < 1);
    console.log(JSON.stringify({
      count: calc.length, ms,
      found: !!hit,
      dm_min: hit ? (hit.jd - jRef) * 1440 : null,
      ds_arcsec: hit ? (hit.sep - ref2032.sep_arcsec) : null,
    }));
    """
    nres, info = node_eval_json(
        js,
        timeout=30.0,
        env={"E2E_HTML": str(html_path), "E2E_SRC_DIR": str(APP_SRC), "E2E_REF": str(APP_TEST / "transits_ref.json")},
    )
    check(nres.rc == 0 and info is not None, f"Mercury 2032 transit check failed: {nres.stderr[:300]}")
    check(info["found"] and info["count"] == 1, f"Expected 1 Mercury transit in 2026-2036 (2032-11-13), got {info}")
    check(abs(info["dm_min"]) < 3.0 and abs(info["ds_arcsec"]) < 5.0,
          f"2032 Mercury transit error too large: dt={info['dm_min']:.2f} min, dsep={info['ds_arcsec']:.2f}\"")
    return f"Mercury 2032-11-13 transit PASS (dt={info['dm_min']:+.2f} min, dsep={info['ds_arcsec']:+.2f}\", {info['ms']} ms)", info


_ASSERT_GATE_RE = re.compile(r"\b(process\.exit\s*\(|process\.exitCode\b|assert\s*[\.(]|throw\s+new\s+Error\b)")


def t1_f2_07_zero_false_green_and_loader(session: E2ESession) -> Tuple[str, dict]:
    test_files = sorted(APP_TEST.glob("*.test.js"))
    check(len(test_files) >= 26, f"Expected >= 26 JS test files, found {len(test_files)}")

    issues: List[str] = []
    # 1. Shared loader contract (WEB-TEST-02)
    loader = APP_TEST / "_load.js"
    if not loader.is_file():
        issues.append("missing app/test/_load.js")
    else:
        lres, linfo = node_eval_json(
            f"const L = require({json.dumps(str(loader))}); console.log(JSON.stringify({{ hasLoad: typeof L.loadUnivers === 'function' }}));",
            timeout=10.0,
        )
        if lres.rc != 0 or not (linfo and linfo.get("hasLoad")):
            issues.append("app/test/_load.js does not export function loadUnivers")

    # 2. Zero false-green tests (WEB-TEST-01) & zero eval() in *.test.js
    false_green: List[str] = []
    eval_users: List[str] = []
    for p in test_files:
        src = p.read_text(encoding="utf-8")
        if not _ASSERT_GATE_RE.search(src):
            false_green.append(p.name)
        if re.search(r"\beval\s*\(", src):
            eval_users.append(p.name)
    if false_green:
        issues.append(f"{len(false_green)} false-green print-only tests without exit/assert gate: {', '.join(false_green)}")
    if eval_users:
        issues.append(f"eval() still used in: {', '.join(eval_users)}")

    # 3. Execute all 6 former false-green tests cleanly
    six = ["physics.test.js", "ephem.test.js", "horizons.test.js", "future.test.js", "dyn.test.js", "more.test.js"]
    run_res = _run_js_tests_parallel(six, timeout_per_test=30.0)
    bad_run = [f"{k} rc={rc}" for k, (rc, _, _) in run_res.items() if rc != 0]
    if bad_run:
        issues.append(f"6 core tests failed execution: {', '.join(bad_run)}")

    check(not issues, "; ".join(issues), {"false_green": false_green, "eval_users": eval_users})
    return f"All {len(test_files)} JS tests have active fail gates; _load.js OK; 0 eval(); 6 core tests PASS", {"count": len(test_files)}


def get_tests() -> List[TestCase]:
    return [
        TestCase("T1-F2-01", 1, ["F2"], "Ephemerides DE440 accuracy across 70 dates (1851-2149)", t1_f2_01_ephemerides_de440),
        TestCase("T1-F2-02", 1, ["F2"], "Planck cosmology age/H0 & lightcone survey LUT accuracy", t1_f2_02_cosmology_and_lightcone),
        TestCase("T1-F2-03", 1, ["F2"], "Schwarzschild gravitational lensing & 3D dust atlas accuracy", t1_f2_03_lensing_and_dust),
        TestCase("T1-F2-04", 1, ["F2"], "Quantum & micro-scale physics (CT18NNLO proton, H2O orbitals, O-16 nucleus)", t1_f2_04_quantum_and_micro),
        TestCase("T1-F2-05", 1, ["F2"], "Barycenter, blackbody/z colorimetry, stellar fate, Oort & merger replay", t1_f2_05_bary_color_fate_oort_merger),
        TestCase("T1-F2-06", 1, ["F2"], "10-year Mercury 2032-11-13 transit accuracy vs NASA catalogue", t1_f2_06_transit_mercury_2032),
        TestCase("T1-F2-07", 1, ["F2"], "Zero false-green JS tests & shared app/test/_load.js contract", t1_f2_07_zero_false_green_and_loader, expected_milestone="M1"),
    ]
