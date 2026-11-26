"""Tier 1 — F1: Standalone Web Build, Bundle Integrity & Scientific Truth Guardrails (6 tests)."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, List, Tuple

from lib.harness import (
    APP_GEN,
    APP_SRC,
    DIST_HTML,
    REPO_ROOT,
    E2ESession,
    TestCase,
    check,
    extract_html_scripts,
    fail,
    node_eval_json,
    run_cmd,
    scan_js_slash_slash_hazards,
    sha256_file,
)

GEN_BUILD_ORDER = [
    "data.js", "data2.js", "ephem.js", "data3.js", "data4.js", "data5.js", "data6.js",
    "data7.js", "data8.js", "data9.js", "data10.js", "data11.js", "data12.js", "data13.js",
    "data14.js", "sun_rgb.js", "data15.js", "data16.js", "data17.js", "data18.js", "data19.js",
    "proton_pdf.js", "water_qm.js", "laniakea.js", "data20.js", "nbody.js", "transits.js",
    "mist_life.js", "lunes.js",
]

REQUIRED_DATA_KEYS = (
    "M_GAL2ECL", "JPL1", "JPL2", "VSOP", "MOON_LR", "STARS_N", "STARS_GEO", "STARS_AUX",
    "CMB", "EXO_N", "EXO_PL", "MOONS", "PROBES", "LOCAL", "LGV", "ZCOL", "CF4_LOCAL", "CF4_NEAR", "GW",
    "PROTON_PDF", "WATER_QM", "LANIAKEA", "DUST", "NB", "TRANSITS", "MIST_LIFE",
    "LUNES_JUP", "TEX", "BBCOL", "M31", "LMC",
)


def t1_f1_01_standalone_build(session: E2ESession) -> Tuple[str, dict]:
    out = session.workspace.subdir("t1_f1_01") / "index.html"
    before_dist = sha256_file(DIST_HTML)
    res = session.workspace.build_fresh_html(out)
    check(not res.timed_out and res.rc == 0, f"app/build.py failed (rc={res.rc}): {res.stderr[:300]}")
    check(out.is_file(), f"Output file not created: {out}")
    size = out.stat().st_size
    check(size > 10_000_000, f"Built HTML unexpectedly small: {size} B (expected > 10,000,000 B)")
    text = out.read_text(encoding="utf-8")
    check("/*__DATA__*/" not in text, "Unreplaced /*__DATA__*/ placeholder in built HTML")
    check("/*__JS__*/" not in text, "Unreplaced /*__JS__*/ placeholder in built HTML")
    check("<!doctype html>" in text.lower()[:200], "Missing <!doctype html> header")
    check('<html lang="fr">' in text[:400], 'Missing <html lang="fr"> root tag')
    check(str(out) in res.stdout and "ko" in res.stdout, f"Unexpected build stdout: {res.stdout.strip()!r}")
    check(sha256_file(DIST_HTML) == before_dist, "dist/index.html was modified during temp build!")
    return f"Built {size:,} B in {res.duration_s:.2f}s; markers absent; dist/index.html unchanged", {"size_bytes": size}


def t1_f1_02_determinism_syntax_sri(session: E2ESession) -> Tuple[str, dict]:
    d = session.workspace.subdir("t1_f1_02")
    a, b = d / "a.html", d / "b.html"
    ra = session.workspace.build_fresh_html(a)
    rb = session.workspace.build_fresh_html(b)
    check(ra.rc == 0 and rb.rc == 0, f"Determinism builds failed: rc_a={ra.rc}, rc_b={rb.rc}")
    ha, hb = sha256_file(a), sha256_file(b)
    check(ha == hb and ha is not None, f"Non-deterministic build: {ha} != {hb}")

    html = a.read_text(encoding="utf-8")
    ext, inline = extract_html_scripts(html)
    check(len(inline) >= 2, f"Expected >= 2 inline <script> blocks, got {len(inline)}")

    # Parse both inline <script> blocks via Node vm.Script (zero SyntaxError)
    node_code = r"""
    const fs = require('fs'), vm = require('vm');
    const html = fs.readFileSync(process.env.E2E_HTML, 'utf8');
    const blocks = [];
    const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
    let m;
    while ((m = re.exec(html)) !== null) {
      if (!/\bsrc\s*=/i.test(m[1])) blocks.push(m[2]);
    }
    const errs = [];
    blocks.forEach((code, idx) => {
      try { new vm.Script(code, { filename: `inline_${idx}.js` }); }
      catch (e) { errs.push({ idx, msg: String(e) }); }
    });
    console.log(JSON.stringify({ count: blocks.length, errs }));
    """
    nres, parsed = node_eval_json(node_code, timeout=30.0, env={"E2E_HTML": str(a)})
    check(nres.rc == 0 and parsed is not None, f"Node vm.Script check failed: {nres.stderr[:300]}")
    check(parsed["count"] >= 2 and not parsed["errs"], f"Inline JS syntax errors: {parsed['errs']}")

    three_tag = next((s for s in ext if "three" in s.get("src", "").lower()), None)
    check(three_tag is not None, "Missing external Three.js <script> tag")
    check("0.149.0" in three_tag.get("src", ""), f"Three.js version not pinned to 0.149.0: {three_tag.get('src')}")
    check(three_tag.get("integrity", "").startswith("sha512-") and len(three_tag.get("integrity", "")) > 40,
          f"Missing/invalid sha512 SRI on Three.js: {three_tag.get('integrity')!r}")
    check(three_tag.get("crossorigin") == "anonymous", f"Missing crossorigin=anonymous: {three_tag}")
    check(three_tag.get("referrerpolicy") == "no-referrer", f"Missing referrerpolicy=no-referrer: {three_tag}")
    return f"Deterministic SHA-256 ({ha[:12]}…); {parsed['count']} inline scripts parsed; Three.js 0.149.0 SRI verified", {"sha256": ha}


def t1_f1_03_data_deep_equality(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    existing = {p.name for p in APP_GEN.glob("*.js")}
    ordered = [f for f in GEN_BUILD_ORDER if f in existing] + sorted(existing - set(GEN_BUILD_ORDER))
    node_code = r"""
    const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');
    const html = fs.readFileSync(process.env.E2E_HTML, 'utf8');
    const genDir = process.env.E2E_GEN_DIR;
    const order = JSON.parse(process.env.E2E_GEN_ORDER);
    const reqKeys = JSON.parse(process.env.E2E_REQ_KEYS);
    const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
    let m, dataCode = null;
    while ((m = re.exec(html)) !== null) {
      if (!/\bsrc\s*=/i.test(m[1])) { dataCode = m[2]; break; }
    }
    if (!dataCode) { console.log(JSON.stringify({ ok: false, err: 'No inline DATA script found' })); process.exit(0); }

    const ctxBuilt = vm.createContext({});
    vm.runInContext(dataCode.replace(/^const DATA\b/m, 'var DATA'), ctxBuilt);
    const built = ctxBuilt.DATA;

    const ctxGen = vm.createContext({});
    let genCode = '';
    for (const f of order) genCode += fs.readFileSync(path.join(genDir, f), 'utf8') + '\n';
    vm.runInContext(genCode.replace(/^const DATA\b/m, 'var DATA'), ctxGen);
    const gen = ctxGen.DATA;

    let eqOk = true, eqErr = '';
    try { assert.deepStrictEqual(structuredClone(built), structuredClone(gen)); } catch (e) { eqOk = false; eqErr = String(e).slice(0, 300); }
    const keys = Object.keys(built || {});
    const missing = reqKeys.filter(k => !(k in built));
    console.log(JSON.stringify({
      ok: eqOk && missing.length === 0,
      eqOk, eqErr,
      keyCount: keys.length,
      missing,
      starsN: built.STARS_N || 0,
      exoN: built.EXO_N || 0,
      localN: Array.isArray(built.LOCAL) ? built.LOCAL.length : 0,
    }));
    """
    nres, info = node_eval_json(
        node_code,
        timeout=45.0,
        env={
            "E2E_HTML": str(html_path),
            "E2E_GEN_DIR": str(APP_GEN),
            "E2E_GEN_ORDER": json.dumps(ordered),
            "E2E_REQ_KEYS": json.dumps(list(REQUIRED_DATA_KEYS)),
        },
    )
    check(nres.rc == 0 and info is not None, f"DATA deep-equality Node check failed: {nres.stderr[:300]}")
    check(info["eqOk"], f"Built DATA != app/gen/*.js DATA: {info.get('eqErr')}")
    check(not info["missing"], f"Missing required DATA keys: {info['missing']}")
    check(info["keyCount"] >= 115, f"Expected >= 115 DATA keys, got {info['keyCount']}")
    check(info["starsN"] >= 58966, f"STARS_N too low: {info['starsN']}")
    check(info["exoN"] >= 4800, f"EXO_N too low: {info['exoN']}")
    check(info["localN"] >= 100, f"LOCAL count too low: {info['localN']}")
    return (
        f"deepStrictEqual PASS across {info['keyCount']} keys (STARS_N={info['starsN']}, EXO_N={info['exoN']}, LOCAL={info['localN']})",
        info,
    )


def t1_f1_04_scientific_truth_cutoffs(session: E2ESession) -> Tuple[str, dict]:
    # 1. Static FATE_P ban across all app/src/*.js
    fate_hits: List[str] = []
    for p in sorted(APP_SRC.glob("*.js")):
        txt = p.read_text(encoding="utf-8")
        if "FATE_P" in txt:
            fate_hits.append(p.name)
    check(not fate_hits, f"Forbidden FATE_P found in: {fate_hits}")

    # 2. Live runtime cutoffs (T_DIV, SYS_END, SS_BORN) — zero fades!
    pg, err_idx = session.pw.reset_warm_page()
    pg.evaluate(
        r"""() => {
            const U = window.__U;
            U.goTo(11.5, { focus: 'sun', instant: true });
            U.setTime((U.T_DIV + 0.05) * 1e9);
        }"""
    )
    session.pw.wait_frames(pg, n=1, min_ms=130)
    earth_state = pg.evaluate(
        r"""() => ({
            engEarth: !!window.__U.F.eng.earth,
            notice: (document.getElementById('notice') || {}).textContent || '',
            noticeHidden: !!(document.getElementById('notice') || {}).hidden,
        })"""
    )
    check(earth_state["engEarth"] is True, f"F.eng.earth should be true past T_DIV: {earth_state}")
    check(not earth_state["noticeHidden"], "Earth divergence #notice is hidden past T_DIV")
    for tok in ("Sort de la Terre inconnu", "Schröder", "Rasio", "Rybicki"):
        check(tok in earth_state["notice"], f"Missing '{tok}' in T_DIV #notice: {earth_state['notice']!r}")

    # SYS_END binary step (before vs after)
    pg.evaluate("window.__U.goTo(12.5, { focus: 'sun', instant: true }); window.__U.setTime((window.__U.SYS_END - 1.0) * 1e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    sys_before = pg.evaluate("window.__U.F.sysK")
    pg.evaluate("window.__U.setTime((window.__U.SYS_END + 1.0) * 1e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    sys_after = pg.evaluate(
        r"""() => ({
            sysK: window.__U.F.sysK,
            notice: (document.getElementById('notice') || {}).textContent || '',
        })"""
    )
    check(sys_before == 1 and sys_after["sysK"] == 0, f"F.sysK must binary-step 1->0 across SYS_END (got {sys_before} -> {sys_after['sysK']})")
    check("Inconnu" in sys_after["notice"] and "Zink" in sys_after["notice"], f"Missing Inconnu/Zink in SYS_END notice: {sys_after['notice']!r}")

    # Sun birth binary step
    pg.evaluate("window.__U.setTime(-4.6e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    sun_before = pg.evaluate("window.__U.F.sunAlive")
    pg.evaluate("window.__U.setTime(-4.5e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    sun_after = pg.evaluate("window.__U.F.sunAlive")
    check(sun_before == 0 and sun_after == 1, f"F.sunAlive must binary-step 0->1 at SS_BORN (got {sun_before} -> {sun_after})")

    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors during truth cutoff checks: {errs[err_idx:]}")
    return "0 FATE_P; T_DIV, SYS_END (1->0) & SS_BORN (0->1) sharp cutoffs verified live", {}


def t1_f1_05_micro_scale_hard_stop(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()
    pg.evaluate(
        r"""() => {
            const U = window.__U;
            U.goTo(-25.0, { focus: 'earth', instant: true });
            U.S.logR = -25.0;
        }"""
    )
    session.pw.wait_frames(pg, n=1, min_ms=130)
    st = pg.evaluate(
        r"""() => ({
            logR: window.__U.S.logR,
            place: (document.getElementById('place') || {}).textContent || '',
            notice: (document.getElementById('notice') || {}).textContent || '',
        })"""
    )
    check(abs(st["logR"] - (-20.0)) < 1e-6, f"Expected hard clamp at LMICRO=-20.0, got logR={st['logR']}")
    check(st["place"] == "Inconnu", f"Expected #place == 'Inconnu' at LMICRO, got {st['place']!r}")
    check("Inconnu" in st["notice"], f"Missing 'Inconnu' in LMICRO notice: {st['notice']!r}")
    check("1,616" in st["notice"] and "Planck" in st["notice"], f"Missing Planck citation in LMICRO notice: {st['notice']!r}")
    check("arrête" in st["notice"] or "10⁻²⁰" in st["notice"], f"Missing stop explanation in LMICRO notice: {st['notice']!r}")
    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors: {errs[err_idx:]}")
    return f"Micro-scale hard-stopped at logR={st['logR']:.2f}, #place='Inconnu', Planck cited as text only", st


def t1_f1_06_static_quality_gates(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []
    prettier_cfg = REPO_ROOT / ".prettierrc"
    eslint_cfg = REPO_ROOT / "eslint.config.mjs"
    if not prettier_cfg.is_file():
        issues.append("missing .prettierrc")
    if not eslint_cfg.is_file():
        issues.append("missing eslint.config.mjs")

    js_files = [str(p) for p in sorted(APP_SRC.glob("*.js"))]
    pr = run_cmd(["prettier", "--check", *js_files], cwd=REPO_ROOT, timeout=45.0)
    if pr.timed_out or pr.rc != 0:
        issues.append(f"prettier --check failed (rc={pr.rc})")

    es = run_cmd(["eslint", *js_files], cwd=REPO_ROOT, timeout=45.0)
    if es.timed_out or es.rc != 0:
        first_err = (es.stdout + "\n" + es.stderr).strip().splitlines()[:3]
        issues.append(f"eslint failed (rc={es.rc}): {' | '.join(first_err)}")

    total_hazards = 0
    hazard_files: List[str] = []
    for p in sorted(APP_SRC.glob("*.js")):
        hz = scan_js_slash_slash_hazards(p.read_text(encoding="utf-8"))
        if hz:
            total_hazards += len(hz)
            hazard_files.append(f"{p.name}({len(hz)})")
    if total_hazards > 0:
        issues.append(f"{total_hazards} multi-statement/swallowed // hazards in {', '.join(hazard_files)}")

    check(not issues, "; ".join(issues), {"issues": issues, "slash_slash_hazards": total_hazards})
    return f"Prettier & ESLint PASS (0 errors); 0 // hazards across {len(js_files)} app/src/*.js files", {"files": len(js_files)}


def get_tests() -> List[TestCase]:
    return [
        TestCase("T1-F1-01", 1, ["F1"], "Standalone temp HTML build & placeholder elimination", t1_f1_01_standalone_build),
        TestCase("T1-F1-02", 1, ["F1"], "Build determinism, inline JS syntax parse & Three.js SRI", t1_f1_02_determinism_syntax_sri),
        TestCase("T1-F1-03", 1, ["F1"], "Built DATA deep-equality vs app/gen/*.js", t1_f1_03_data_deep_equality),
        TestCase("T1-F1-04", 1, ["F1"], "Scientific truth guardrails: FATE_P ban & zero-fade cutoffs", t1_f1_04_scientific_truth_cutoffs),
        TestCase("T1-F1-05", 1, ["F1"], "Micro-scale hard stop (LMICRO = -20.0, 'Inconnu')", t1_f1_05_micro_scale_hard_stop),
        TestCase("T1-F1-06", 1, ["F1"], "Static quality & formatting gates (ESLint + Prettier + zero // hazard)", t1_f1_06_static_quality_gates, expected_milestone="M3"),
    ]
