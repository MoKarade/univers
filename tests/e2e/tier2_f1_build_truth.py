"""Tier 2 — F1: Build Boundary, Dead-Data Bloat, Strict Mode & // Lexer Contracts (6 tests)."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import List, Tuple

from lib.harness import (
    APP_SRC,
    DIST_HTML,
    REPO_ROOT,
    E2ESession,
    TestCase,
    check,
    node_eval_json,
    run_cmd,
    scan_js_slash_slash_hazards,
    sha256_file,
)

CORE_WINDOW_U_HOOKS = (
    "S", "F", "Rr", "G", "STOPS", "goName", "goStop", "goTo", "goHome", "goBack",
    "evGo", "evStep", "parseWhen", "eclipseScan", "setTime", "setSpeed", "openPanel",
    "focusBody", "select", "pickAt", "findRun", "onLost", "T_DIV", "SYS_END", "frame",
)


def t2_f1_01_zero_dead_overwritten_data(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    js = r"""
    const fs = require('fs'), vm = require('vm');
    const html = fs.readFileSync(process.env.E2E_HTML, 'utf8');
    const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
    let m, dataCode = null;
    while ((m = re.exec(html)) !== null) {
      if (!/\bsrc\s*=/i.test(m[1])) { dataCode = m[2]; break; }
    }
    const topWrites = Object.create(null);
    const texWrites = Object.create(null);
    const wrapTex = obj => new Proxy(obj, {
      set(t, k, v) {
        texWrites[k] = (texWrites[k] || 0) + 1;
        t[k] = v;
        return true;
      }
    });
    const raw = {};
    const DATA = new Proxy(raw, {
      set(t, k, v) {
        topWrites[k] = (topWrites[k] || 0) + 1;
        if (k === 'TEX' && v && typeof v === 'object') {
          const inner = {};
          const p = wrapTex(inner);
          for (const tk of Object.keys(v)) p[tk] = v[tk];
          t[k] = p;
          return true;
        }
        t[k] = v;
        return true;
      }
    });
    // Rewrite initial `const DATA = {` -> `Object.assign(DATA, {` so initial keys go through Proxy
    const patched = dataCode.replace(/^\s*(?:const|let|var)\s+DATA\s*=\s*\{/m, 'Object.assign(DATA, {');
    // Match the closing `};` of initial const DATA = { ... }; cleanly by wrapping via Object.assign
    const patched2 = patched.replace(/;\s*(?=\n?(?:Object\.assign|DATA\.|const|let|var|\/\*|$))/, ');');
    const ctx = vm.createContext({ DATA, Object });
    vm.runInContext(patched2, ctx, { filename: 'built_data.js' });
    const dupTop = Object.entries(topWrites).filter(([, c]) => c > 1).map(([k, c]) => ({ k, c }));
    const dupTex = Object.entries(texWrites).filter(([, c]) => c > 1).map(([k, c]) => ({ k, c }));
    console.log(JSON.stringify({
      topKeys: Object.keys(topWrites).length,
      texKeys: Object.keys(texWrites).length,
      dupTop,
      dupTex,
    }));
    """
    nres, info = node_eval_json(js, timeout=45.0, env={"E2E_HTML": str(html_path)})
    check(nres.rc == 0 and info is not None, f"Proxy DATA audit failed: {nres.stderr[:300]}")
    check(
        len(info["dupTop"]) == 0 and len(info["dupTex"]) == 0,
        f"Dead overwritten keys still bundled in built HTML: top={len(info['dupTop'])} "
        f"({[x['k'] for x in info['dupTop'][:8]]}), TEX={len(info['dupTex'])} ({[x['k'] for x in info['dupTex'][:8]]})",
        info,
    )
    return f"0 overwritten top-level or DATA.TEX keys across {info['topKeys']} built DATA keys", info


def t2_f1_02_build_no_resource_warning_or_data2_hack(session: E2ESession) -> Tuple[str, dict]:
    out = session.workspace.subdir("t2_f1_02") / "rw.html"
    res = session.workspace.build_fresh_html(out, extra_python_args=("-W", "error::ResourceWarning"))
    issues: List[str] = []
    if res.timed_out or res.rc != 0:
        issues.append(f"build.py exited rc={res.rc}")
    if "ResourceWarning" in res.stderr or "unclosed file" in res.stderr:
        issues.append(f"unclosed file ResourceWarning emitted on stderr: {res.stderr.strip()[:220]}")
    build_src = (REPO_ROOT / "app" / "build.py").read_text(encoding="utf-8")
    if "STARS_GEO" in build_src or "_o.pop" in build_src:
        issues.append("app/build.py still contains brittle data2.js JSON pop hack (STARS_GEO/CMB)")
    check(not issues, "; ".join(issues), {"stderr": res.stderr[:300]})
    return "app/build.py emitted 0 ResourceWarnings and contains no data2.js JSON pop hack", {}


def t2_f1_03_build_cli_path_edge_cases(session: E2ESession) -> Tuple[str, dict]:
    before_dist = sha256_file(DIST_HTML)
    base = session.workspace.subdir("t2_f1_03")
    issues: List[str] = []

    # (a) Deep nested non-existent directory path
    nested = base / "a" / "b" / "c" / "page.html"
    r1 = session.workspace.build_fresh_html(nested)
    if r1.rc != 0 or not nested.is_file() or nested.stat().st_size < 10_000_000:
        issues.append(f"nested path build failed (rc={r1.rc}): {r1.stderr.strip()[:200]}")

    # (b) Bare relative filename in temp CWD (caught FileNotFoundError: '' bug)
    bare_dir = base / "bare_cwd"
    bare_dir.mkdir(parents=True, exist_ok=True)
    r2 = session.workspace.build_fresh_html("page.html", cwd=bare_dir)
    bare_out = bare_dir / "page.html"
    if r2.rc != 0 or not bare_out.is_file() or bare_out.stat().st_size < 10_000_000:
        issues.append(f"bare relative filename build failed (rc={r2.rc}): {r2.stderr.strip()[:200]}")

    check(sha256_file(DIST_HTML) == before_dist, "dist/index.html mutated during CLI edge-case tests!")
    check(not issues, "; ".join(issues))
    return "Nested path & bare relative filename CLI builds both PASS; dist/index.html unchanged", {}


def t2_f1_04_strict_mode_window_u_and_modularity(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []

    # 1. Built bundle has "use strict" & every app/src/*.js passes node --check
    html = session.workspace.temp_html_text()
    if '"use strict";' not in html and "'use strict';" not in html:
        issues.append('Built bundle missing "use strict" directive')

    js_files = sorted(APP_SRC.glob("*.js"))
    oversized: List[str] = []
    for p in js_files:
        r = run_cmd(["node", "--check", str(p)], timeout=15.0)
        if r.rc != 0:
            issues.append(f"node --check failed on {p.name}: {r.stderr.strip()[:120]}")
        sz = p.stat().st_size
        if sz > 200_000:
            oversized.append(f"{p.name} ({sz // 1024} KB > 200 KB)")
    if oversized:
        issues.append(f"Monolithic JS file(s) not split (WEB-SIMP-01): {', '.join(oversized)}")

    # 2. Detect duplicate keys in window.__U / object literals (catches WEB-BUG-02 duplicate G)
    # Run ESLint no-dupe-keys rule directly via --no-config-lookup + inline rule OR check window.__U literal
    # Using eslint with a temporary flat config inside workspace guarantees AST-exact no-dupe-keys check even before M3!
    tmp_cfg = session.workspace.subdir("t2_f1_04") / "dupe.mjs"
    tmp_cfg.write_text(
        'export default [{ languageOptions: { ecmaVersion: 2022 }, rules: { "no-dupe-keys": "error" } }];\n',
        encoding="utf-8",
    )
    es = run_cmd(["eslint", "--config", str(tmp_cfg), *[str(p) for p in js_files]], cwd=REPO_ROOT, timeout=30.0)
    if es.rc != 0:
        dupe_lines = [ln.strip() for ln in (es.stdout + "\n" + es.stderr).splitlines() if "no-dupe-keys" in ln or "Duplicate key" in ln]
        issues.append(f"ESLint no-dupe-keys violation(s): {' | '.join(dupe_lines[:5]) or es.stdout[:200]}")

    # 3. Runtime window.__U completeness (25 core hooks)
    pg, err_idx = session.pw.reset_warm_page()
    missing_hooks = pg.evaluate(
        "(hooks) => hooks.filter(h => !(h in window.__U))",
        list(CORE_WINDOW_U_HOOKS),
    )
    if missing_hooks:
        issues.append(f"window.__U missing hooks: {missing_hooks}")
    _, errs, _ = session.pw.get_warm_desktop_page()
    if len(errs) != err_idx:
        issues.append(f"Unexpected pageerrors: {errs[err_idx:]}")

    check(not issues, "; ".join(issues), {"issues": issues})
    return f"Strict mode OK; 0 duplicate keys; all {len(CORE_WINDOW_U_HOOKS)} window.__U hooks present; all app/src/*.js <= 200 KB", {}


def t2_f1_05_exact_threshold_pairs_and_mars_clamp(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()

    # T_DIV - 1e-4 vs T_DIV + 1e-4
    pg.evaluate("window.__U.goTo(11.5, { focus: 'sun', instant: true }); window.__U.setTime((window.__U.T_DIV - 1e-4) * 1e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    td_lo = pg.evaluate("() => ({ eng: !!window.__U.F.eng.earth, n: document.getElementById('notice').textContent })")
    pg.evaluate("window.__U.setTime((window.__U.T_DIV + 1e-4) * 1e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    td_hi = pg.evaluate("() => ({ eng: !!window.__U.F.eng.earth, n: document.getElementById('notice').textContent })")
    check(not td_lo["eng"] and "Sort de la Terre inconnu" not in td_lo["n"], f"T_DIV - 1e-4 unexpectedly engulfed: {td_lo}")
    check(td_hi["eng"] and "Sort de la Terre inconnu" in td_hi["n"], f"T_DIV + 1e-4 missing Earth unknown notice: {td_hi}")

    # SYS_END - 1e-3 vs SYS_END + 1e-3
    pg.evaluate("window.__U.setTime((window.__U.SYS_END - 1e-3) * 1e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    se_lo = pg.evaluate("() => ({ sysK: window.__U.F.sysK, mars: !!window.__U.F.eng.mars, pluto: !!window.__U.F.eng.pluto })")
    pg.evaluate("window.__U.setTime((window.__U.SYS_END + 1e-3) * 1e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    se_hi = pg.evaluate("() => ({ sysK: window.__U.F.sysK, mars: !!window.__U.F.eng.mars, pluto: !!window.__U.F.eng.pluto })")
    check(se_lo["sysK"] == 1 and not se_lo["mars"] and not se_lo["pluto"], f"SYS_END - 1e-3 invalid: {se_lo}")
    check(se_hi["sysK"] == 0 and se_hi["mars"] and se_hi["pluto"], f"SYS_END + 1e-3 invalid: {se_hi}")

    # Non-Earth (Mars) micro-scale zoom attempt must clamp to >= LMIN (6.6)
    pg.evaluate("window.__U.setTime(0); window.__U.focusBody('mars');")
    session.pw.wait_frames(pg, n=1, min_ms=120)
    pg.evaluate("window.__U.S.anim = null; window.__U.S.logR = -20.0;")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    mars_lr = pg.evaluate("window.__U.S.logR")
    check(mars_lr >= 6.6 - 1e-6, f"Mars focus allowed micro-scale zoom: logR={mars_lr} (< LMIN 6.6)")

    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors: {errs[err_idx:]}")
    return f"Exact T_DIV & SYS_END boundary flips PASS; Mars micro clamp logR={mars_lr:.2f} >= 6.6", {"mars_logR": round(mars_lr, 3)}


def t2_f1_06_js_lexer_selftest_and_real_audit(session: E2ESession) -> Tuple[str, dict]:
    # 1. Self-test positive traps and negative safe constructs
    pos_1 = scan_js_slash_slash_hazards("const a = 1; b(); // tail\n")
    pos_2 = scan_js_slash_slash_hazards("a(); // b(); c();\n")
    neg_1 = scan_js_slash_slash_hazards('const u = "https://x.y";\nconst t = `http://a.b/${x}`;\n')
    neg_2 = scan_js_slash_slash_hazards("const re = /a\\/\\/b/g;\nconst x = 1; // benign single statement note\n")
    check(len(pos_1) == 1, f"Lexer self-test failed to flag multi-statement trailing //: {pos_1}")
    check(len(pos_2) == 1, f"Lexer self-test failed to flag swallowed code //: {pos_2}")
    check(len(neg_1) == 0, f"Lexer self-test false positive on URL strings/templates: {neg_1}")
    check(len(neg_2) == 0, f"Lexer self-test false positive on regex literal or clean comment: {neg_2}")

    # 2. Real audit of all app/src/*.js
    findings = {}
    total = 0
    for p in sorted(APP_SRC.glob("*.js")):
        hz = scan_js_slash_slash_hazards(p.read_text(encoding="utf-8"))
        if hz:
            findings[p.name] = len(hz)
            total += len(hz)
    check(total == 0, f"Found {total} CLAUDE.md // hazards in app/src/*.js: {findings}", {"findings": findings})
    return f"JS // lexer self-test PASS; 0 hazards across all app/src/*.js", {"total": 0}


def get_tests() -> List[TestCase]:
    return [
        TestCase("T2-F1-01", 2, ["F1"], "Zero dead overwritten DATA/TEX keys in built HTML bundle (ES6 Proxy)", t2_f1_01_zero_dead_overwritten_data, expected_milestone="M3"),
        TestCase("T2-F1-02", 2, ["F1"], "app/build.py zero ResourceWarning unclosed handles & no data2.js JSON hack", t2_f1_02_build_no_resource_warning_or_data2_hack, expected_milestone="M3"),
        TestCase("T2-F1-03", 2, ["F1"], "app/build.py CLI output-path edge cases (nested non-existent & bare relative)", t2_f1_03_build_cli_path_edge_cases, expected_milestone="M3"),
        TestCase("T2-F1-04", 2, ["F1"], "Strict-mode bundle, 0 duplicate keys, window.__U hooks & modular split <=200 KB", t2_f1_04_strict_mode_window_u_and_modularity, expected_milestone="M2/M3"),
        TestCase("T2-F1-05", 2, ["F1"], "Exact threshold pairs (T_DIV ± 1e-4, SYS_END ± 1e-3, Mars micro clamp >= LMIN)", t2_f1_05_exact_threshold_pairs_and_mars_clamp),
        TestCase("T2-F1-06", 2, ["F1"], "Stateful JS // lexer negative self-test & real app/src/*.js audit", t2_f1_06_js_lexer_selftest_and_real_audit, expected_milestone="M3"),
    ]
