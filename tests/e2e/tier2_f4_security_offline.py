"""Tier 2 — F4: Advanced Asset Manifest, Packet Storm, URL Safety & Worker Hygiene (6 tests)."""
from __future__ import annotations

import re
from typing import List, Tuple
from urllib.parse import urlparse

from lib.harness import (
    APP_SRC,
    E2ESession,
    TestCase,
    check,
    node_eval_json,
)
from tier1_f2_physics import _NODE_LOAD_PHYSICS_PREAMBLE


def t2_f4_01_no_404_storm_fusion_packets(session: E2ESession) -> Tuple[str, dict]:
    base_url = session.server.start()
    fusc_url = f"{base_url}/mock/fusion_centres.json"
    fusi_url = f"{base_url}/mock/fusion_images_404pk.json"
    init_js = (
        "window.__TIER=0; window.__NOADAPT=true; window.__TILES_ON=true; window.__TILES=[]; window.__PHOTOS=[]; "
        f"window.__FUSC='{fusc_url}'; window.__FUSI='{fusi_url}'; "
        f"window.__ASSETS={{ fusc: '{fusc_url}', fusi: '{fusi_url}' }};"
    )
    snap = session.server.snapshot_log()
    with session.pw.open_isolated_page(init_script=init_js) as (pg, errs, _):
        pg.wait_for_function("window.__U.S.orbit && window.__U.S.orbit.fus && window.__U.S.tOn !== null", polling=200, timeout=30000)
        pg.evaluate("window.__U.setTime((window.__U.S.tOn - 0.3) * 1e9);")
        session.pw.wait_frames(pg, n=8, min_ms=450)
        reqs = session.server.requests_since(snap)
        pk_hits = [r for r in reqs if "/mock/404/fusion_images_" in r[1]]
        check(len(errs) == 0, f"Unexpected pageerrors during fusion packet 404 test: {errs}")
        check(
            len(pk_hits) <= 4,
            f"Fusion packet 404 fetch storm detected: {len(pk_hits)} requests in 8 frames (max allowed: 4; WEB-BUG-01)",
            {"packet_404_requests": len(pk_hits)},
        )
        return f"Zero fusion packet 404 storm ({len(pk_hits)} packet request(s) across 8 frames)", {"packet_404_requests": len(pk_hits)}


def t2_f4_02_unified_assets_manifest_override(session: E2ESession) -> Tuple[str, dict]:
    base_url = session.server.start()
    custom_ngc = f"{base_url}/mock/custom_ngc.json"
    # Use ONLY window.__ASSETS (no legacy window.__NGC!) to test the unified ASSETS manifest contract
    init_js = (
        "window.__TIER=0; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[]; "
        f"window.__ASSETS={{ ngc: '{custom_ngc}', fusc: '', fusi: '', nbl: '', flame: '' }};"
    )
    snap = session.server.snapshot_log()
    with session.pw.open_isolated_page(init_script=init_js) as (pg, errs, _):
        pg.evaluate("document.getElementById('b-find').click();")
        found = False
        for _ in range(15):
            res = pg.evaluate(
                """() => {
                    const i = document.getElementById('find-q');
                    i.value = 'GalaxieTestAssets';
                    i.dispatchEvent(new Event('input'));
                    return [...document.querySelectorAll('#find-res button')].map(b => b.textContent);
                }"""
            )
            if any("GalaxieTestAssets" in x for x in res):
                found = True
                break
            pg.wait_for_timeout(150)
        reqs = session.server.requests_since(snap)
        blob_reqs = [r[1] for r in reqs if "/_blob/" in r[1]]
        check(len(errs) == 0, f"Unexpected pageerrors: {errs}")
        check(found, f"window.__ASSETS.ngc override was ignored (custom NGC entry not loaded; blob_reqs={blob_reqs}; WEB-SEC-04)", {"blob_reqs": blob_reqs})
        check(not blob_reqs, f"Hardcoded /_blob/* requests leaked despite window.__ASSETS override: {blob_reqs}")
        return "window.__ASSETS unified manifest override loaded custom NGC with 0 /_blob/* leaks", {}


def t2_f4_03_unsafe_url_schemes_rejected(session: E2ESession) -> Tuple[str, dict]:
    base_url = session.server.start()
    fusc_url = f"{base_url}/mock/fusion_centres.json"
    evil_fusi = f"{base_url}/mock/evil_url_fusion_images.json"
    init_js = (
        "window.__TIER=0; window.__NOADAPT=true; window.__TILES_ON=true; window.__TILES=[]; window.__PHOTOS=[]; "
        "window.__NGC='javascript:window.__XSS_URL=1'; "
        f"window.__FUSC='{fusc_url}'; window.__FUSI='{evil_fusi}'; "
        f"window.__ASSETS={{ ngc: 'data:application/json,{{\"o\":[]}}', fusc: '{fusc_url}', fusi: '{evil_fusi}' }};"
    )
    with session.pw.open_isolated_page(init_script=init_js) as (pg, errs, reqs):
        pg.evaluate("document.getElementById('b-find').click();")
        pg.wait_for_function("window.__U.S.orbit && window.__U.S.orbit.fus && window.__U.S.tOn !== null", polling=200, timeout=30000)
        pg.evaluate("window.__U.setTime((window.__U.S.tOn - 0.3) * 1e9);")
        session.pw.wait_frames(pg, n=6, min_ms=350)
        xss_url = pg.evaluate("window.__XSS_URL || null")
        unsafe_reqs = [u for u in reqs if u.startswith(("javascript:", "data:"))]
        check(not xss_url, f"Unsafe URL scheme executed script: window.__XSS_URL={xss_url}")
        check(not unsafe_reqs, f"Browser attempted to fetch unsafe URL scheme(s): {unsafe_reqs} (WEB-SEC-04)", {"unsafe_reqs": unsafe_reqs})
        # Also verify an explicit URL-scheme sanitizer exists in app/src/6*.js (so rejection isn't merely accidental browser rejection)
        src_6 = "\n".join(p.read_text(encoding="utf-8") for p in sorted(APP_SRC.glob("6*.js")))
        has_scheme_guard = bool(
            re.search(r"safeUrl|checkUrl|validUrl|https?:|^\s*/|protocol\s*===\s*['\"]https?:", src_6, re.IGNORECASE)
            and re.search(r"__ASSETS", src_6)
        )
        check(has_scheme_guard, "Missing explicit safe URL scheme validation on ASSETS/dynamic URLs (WEB-SEC-04)")
        check(len(errs) == 0, f"Unexpected pageerrors: {errs}")
        return "javascript:/data: URLs rejected cleanly without fetch or execution", {}


def t2_f4_04_zero_scattered_blob_urls(session: E2ESession) -> Tuple[str, dict]:
    # All '/_blob/' URLs in app/src/*.js MUST be centralized in ONE ASSETS manifest block/module (WEB-SEC-04)
    hits_by_file = {}
    scattered_lines = []
    for p in sorted(APP_SRC.glob("*.js")):
        txt = p.read_text(encoding="utf-8")
        lines = txt.splitlines()
        blob_lines = [i + 1 for i, ln in enumerate(lines) if "/_blob/" in ln]
        if blob_lines:
            hits_by_file[p.name] = blob_lines
            # Check if scattered across wide line spans (> 120 lines apart) or without ASSETS manifest
            if max(blob_lines) - min(blob_lines) > 120:
                scattered_lines.append(f"{p.name}: span lines {min(blob_lines)}..{max(blob_lines)} ({len(blob_lines)} hits)")

    src_all = "\n".join(p.read_text(encoding="utf-8") for p in sorted(APP_SRC.glob("*.js")))
    has_assets = bool(re.search(r"\b(?:const|let|var)\s+ASSETS\b", src_all) and "__ASSETS" in src_all)

    issues: List[str] = []
    if not has_assets:
        issues.append("Missing centralized ASSETS manifest supporting window.__ASSETS (WEB-SEC-04)")
    if len(hits_by_file) > 1:
        issues.append(f"/_blob/ URLs scattered across {len(hits_by_file)} files: {list(hits_by_file)}")
    if scattered_lines:
        issues.append(f"/_blob/ URLs scattered across file: {'; '.join(scattered_lines)}")

    check(not issues, "; ".join(issues), {"hits_by_file": hits_by_file})
    return f"All /_blob/ URLs centralized inside single ASSETS manifest ({list(hits_by_file)})", {"hits_by_file": hits_by_file}


def t2_f4_05_zero_external_tracking_or_leaks(session: E2ESession) -> Tuple[str, dict]:
    _, errs, reqs = session.pw.get_warm_desktop_page()
    allowed_hosts = {"127.0.0.1", "localhost", "cdnjs.cloudflare.com"}
    unexpected = []
    for u in reqs:
        if u.startswith(("data:", "blob:", "about:")):
            continue
        host = (urlparse(u).hostname or "").lower()
        # Google Fonts are intentionally aborted by PlaywrightSession; exclude fonts.* from leak check
        if host in ("fonts.googleapis.com", "fonts.gstatic.com"):
            continue
        if host not in allowed_hosts:
            unexpected.append(u)
    check(not unexpected, f"Unexpected external host request(s): {unexpected[:8]}", {"unexpected": unexpected[:10]})
    return f"0 unexpected external requests across {len(reqs)} recorded runtime requests", {"total_reqs": len(reqs)}


def t2_f4_06_worker_onerror_and_sun_orb_cap(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    js = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    // 1. Test orbInit worker onerror terminates worker & clears K.orb (WEB-BUG-12)
    let workerInstance = null;
    ctx.Blob = function(parts, opts) { this.parts = parts; this.opts = opts; };
    ctx.URL = { createObjectURL: () => 'blob:mock', revokeObjectURL: () => {} };
    ctx.Worker = function(url) {
      this.url = url;
      this.terminated = false;
      this.posted = [];
      this.postMessage = m => this.posted.push(m);
      this.terminate = () => { this.terminated = true; };
      workerInstance = this;
    };
    const K = { N: 2, gx0: new Float32Array(6), gv0: new Float32Array(6) };
    ctx.orbInit(K, [0, 0, 0]);
    let hadWorker = !!workerInstance;
    let terminatedOnError = false;
    let orbCleared = false;
    if (workerInstance && typeof workerInstance.onerror === 'function') {
      workerInstance.onerror(new Error('synthetic worker failure'));
      terminatedOnError = !!workerInstance.terminated;
      orbCleared = K.orb === null;
    }

    // 2. Test SUN_ORB.cps memory cap under distant time jumps (0 -> 20 Ga = 200 checkpoints if uncapped!)
    const out = [0, 0, 0];
    ctx.SUN_ORB.cps.clear();
    ctx.SUN_ORB.X = null;
    ctx.sunOrbAt(null, 20.0, out);
    const cpsAfter20Ga = ctx.SUN_ORB.cps.size;
    console.log(JSON.stringify({
      hadWorker, terminatedOnError, orbCleared, cpsAfter20Ga,
      maxCpConst: typeof ctx.ORB_MAXCP === 'number' ? ctx.ORB_MAXCP : null,
    }));
    """
    nres, info = node_eval_json(js, timeout=25.0, env={"E2E_HTML": str(html_path), "E2E_SRC_DIR": str(APP_SRC)})
    check(nres.rc == 0 and info is not None, f"26_orbits worker/SUN_ORB probe failed: {nres.stderr[:300]}")
    issues = []
    if not info["hadWorker"]:
        issues.append("orbInit failed to construct mock Worker")
    if not info["terminatedOnError"]:
        issues.append("26_orbits worker.onerror did not call w.terminate() (WEB-BUG-12)")
    if not info["orbCleared"]:
        issues.append("26_orbits worker.onerror did not clear K.orb")
    # Uncapped 20 Ga at ORB_CP=0.1 produces 201 entries; capped should stay <= 128 (or <= ORB_MAXCP)
    cap_limit = max(64, int(info["maxCpConst"] or 64))
    if info["cpsAfter20Ga"] > cap_limit:
        issues.append(f"SUN_ORB.cps grew unbounded to {info['cpsAfter20Ga']} entries at 20 Ga (expected <= {cap_limit}; WEB-BUG-12)")
    check(not issues, "; ".join(issues), info)
    return f"Worker terminated cleanly on error & SUN_ORB.cps capped at {info['cpsAfter20Ga']} (<= {cap_limit})", info


def get_tests() -> List[TestCase]:
    return [
        TestCase("T2-F4-01", 2, ["F4"], "Zero 404 fetch storm on merger packet files (fusWant)", t2_f4_01_no_404_storm_fusion_packets, expected_milestone="M2"),
        TestCase("T2-F4-02", 2, ["F4"], "Unified window.__ASSETS manifest override without /_blob/* leaks", t2_f4_02_unified_assets_manifest_override, expected_milestone="M2"),
        TestCase("T2-F4-03", 2, ["F4"], "Unsafe URL schemes (javascript:, data:) rejected in dynamic asset URLs", t2_f4_03_unsafe_url_schemes_rejected, expected_milestone="M2"),
        TestCase("T2-F4-04", 2, ["F4"], "Zero scattered hardcoded /_blob/ URLs outside centralized ASSETS manifest", t2_f4_04_zero_scattered_blob_urls, expected_milestone="M2"),
        TestCase("T2-F4-05", 2, ["F4"], "Zero unexpected external tracking/host leaks during runtime boot", t2_f4_05_zero_external_tracking_or_leaks),
        TestCase("T2-F4-06", 2, ["F4"], "Orbit worker onerror terminates worker & SUN_ORB.cps size is capped", t2_f4_06_worker_onerror_and_sun_orb_cap, expected_milestone="M2"),
    ]
