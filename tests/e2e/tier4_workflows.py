"""Tier 4 — Real-World Multi-Feature End-User Workflows (7 tests: T4-E2E-01..07)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import re
import time
from typing import Dict, List, Tuple

from PIL import Image, ImageStat

from lib.harness import (
    APP_TEST,
    DIST_HTML,
    INFRA_DIR,
    REPO_ROOT,
    E2ESession,
    TestCase,
    UI_BLOCKS,
    UI_MEASURE_JS,
    check,
    compute_ui_overlaps,
    run_cmd,
    sha256_file,
)


def t4_e2e_01_desktop_47_order_exploration(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()
    shot_dir = session.workspace.subdir("t4_e2e_01")

    # 1. Solar System HDR check + non-blank WebGL2 screenshot
    hdr = pg.evaluate("!!window.__U.Rr.hdr")
    check(hdr, "Expected HDR WebGL2 active at start of 47-order exploration")
    shot_path = shot_dir / "solar_system.png"
    pg.screenshot(path=str(shot_path))
    stat = ImageStat.Stat(Image.open(shot_path).convert("RGB"))
    max_std = max(stat.stddev)
    check(max_std > 3.0, f"Solar System WebGL2 screenshot appears blank/flat (max channel stddev={max_std:.2f})")

    # 2. Dive into Earth micro-scale: droplet -> H2O -> proton -> quark -> LMICRO (-20.0 Inconnu)
    for stop_idx in (9, 10, 13, 14, 15):
        pg.evaluate(f"window.__U.goStop(window.__U.STOPS[{stop_idx}], true);")
        session.pw.wait_frames(pg, n=1, min_ms=130)
    micro_st = pg.evaluate("() => ({ logR: __U.S.logR, place: document.getElementById('place').textContent })")
    check(abs(micro_st["logR"] - (-20.0)) < 0.05 and micro_st["place"] == "Inconnu", f"Micro dive failed at LMICRO: {micro_st}")

    # 3. Return home, search Sirius & M87 via #b-find and open cards
    pg.evaluate("window.__U.goHome();")
    session.pw.wait_frames(pg, n=2, min_ms=150)
    for q in ("Sirius", "M87"):
        pg.evaluate("document.getElementById('b-find').click();")
        pg.evaluate(
            """(q) => {
                const i = document.getElementById('find-q');
                i.value = q;
                i.dispatchEvent(new Event('input'));
                const btn = [...document.querySelectorAll('#find-res button')].find(b => b.textContent.toLowerCase().includes(q.toLowerCase()));
                if (btn) btn.click();
            }""",
            q,
        )
        session.pw.wait_frames(pg, n=1, min_ms=130)
        card_open = pg.evaluate("!document.getElementById('card').hidden")
        check(card_open, f"Card did not open after searching {q!r}")

    # 4. Traverse Milky Way -> Local Group -> Cosmic Web (#c-lc toggle) -> Observable Universe
    pg.evaluate("window.__U.select(null); window.__U.openPanel(null);")
    for stop_idx in (4, 5, 7, 8):
        pg.evaluate(f"window.__U.goStop(window.__U.STOPS[{stop_idx}], true);")
        if stop_idx == 7:
            pg.evaluate("const lc = document.getElementById('c-lc'); lc.checked = true; lc.dispatchEvent(new Event('change'));")
        session.pw.wait_frames(pg, n=1, min_ms=130)
    pg.evaluate("const lc = document.getElementById('c-lc'); lc.checked = false; lc.dispatchEvent(new Event('change'));")

    # Non-blank cosmic screenshot + 0 fatal HUD overlap
    shot2 = shot_dir / "observable_universe.png"
    pg.screenshot(path=str(shot2))
    stat2 = ImageStat.Stat(Image.open(shot2).convert("RGB"))
    check(max(stat2.stddev) > 2.0, f"Observable Universe screenshot appears blank (stddev={stat2.stddev})")

    items = pg.evaluate(UI_MEASURE_JS, UI_BLOCKS)
    ov = compute_ui_overlaps(items, tol=2.0)
    check(not ov, f"HUD overlap at Observable Universe: {ov[:4]}")

    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Uncaught pageerrors during 47-order journey: {errs[err_idx:]}")
    return f"Full 47-order exploration PASS (pixel stddev={max_std:.1f}/{max(stat2.stddev):.1f}, 0 overlaps, 0 pageerrors)", {"stddev_solar": round(max_std, 2)}


def t4_e2e_02_deep_time_cosmic_journey(session: E2ESession) -> Tuple[str, dict]:
    base_url = session.server.start()
    fusc_url = f"{base_url}/mock/fusion_centres.json"
    fusi_404 = f"{base_url}/mock/404/fusion_images_t402.json"
    init_js = (
        "window.__TIER=0; window.__NOADAPT=true; window.__TILES_ON=true; window.__TILES=[]; window.__PHOTOS=[]; "
        f"window.__FUSC='{fusc_url}'; window.__FUSI='{fusi_404}'; "
        f"window.__ASSETS={{ fusc: '{fusc_url}', fusi: '{fusi_404}' }};"
    )
    snap = session.server.snapshot_log()
    issues: List[str] = []
    with session.pw.open_isolated_page(init_script=init_js) as (pg, errs, _):
        pg.wait_for_function("window.__U.S.orbit && window.__U.S.orbit.fus && window.__U.S.tOn !== null", polling=200, timeout=30000)

        # 1. Big Bang & pre-Sun (-4.6 Ga -> F.sunAlive === 0)
        pg.evaluate("const bb = __U.EVL.find(e => e.n === 'Big Bang'); if (bb) __U.evGo(bb);")
        session.pw.wait_frames(pg, n=1, min_ms=130)
        age_bb = pg.evaluate("window.__U.F.age")
        if age_bb >= 0.01:
            issues.append(f"Big Bang age expected < 0.01 Ga, got {age_bb}")

        pg.evaluate("window.__U.setTime(-4.6e9);")
        session.pw.wait_frames(pg, n=2, min_ms=150)
        if pg.evaluate("window.__U.F.sunAlive") != 0:
            issues.append("F.sunAlive should be 0 at -4.6 Ga")

        # 2. Apollo 11 & 2026 eclipse scan
        apollo_t = pg.evaluate("window.__U.parseWhen('20/07/1969')")
        ecl = pg.evaluate("window.__U.eclipseScan(2461265.24, 2).sol[2]")
        if not (apollo_t is not None and -60 < apollo_t < -54 and ecl == "totale"):
            issues.append(f"Apollo/eclipse check failed: apollo={apollo_t}, ecl={ecl}")

        # 3. Andromeda merger (+4.66 / +5.44 Ga) -> verify <= 3 404 requests (WEB-BUG-01)
        pg.evaluate("window.__U.goStop(window.__U.STOPS[5], true); window.__U.setTime(4.66e9);")
        session.pw.wait_frames(pg, n=6, min_ms=300)
        pg.evaluate("window.__U.setTime(5.44e9);")
        session.pw.wait_frames(pg, n=6, min_ms=300)
        reqs = session.server.requests_since(snap)
        fusi_hits = [r for r in reqs if "/mock/404/fusion_images_t402.json" in r[1]]
        if len(fusi_hits) > 3:
            issues.append(f"Merger 404 fetch storm: {len(fusi_hits)} requests (max 3; WEB-BUG-01)")

        # 4. T_DIV + 0.01 Ga & +9 Ga AST/TNO scaling check & SYS_END + 2 Ga
        pg.evaluate("window.__U.goTo(11.5, { focus: 'sun', instant: true }); window.__U.setTime((window.__U.T_DIV + 0.01) * 1e9);")
        session.pw.wait_frames(pg, n=1, min_ms=130)
        if "Sort de la Terre inconnu" not in pg.evaluate("document.getElementById('notice').textContent"):
            issues.append("Missing T_DIV notice")

        pg.evaluate("window.__U.setTime((window.__U.SYS_END + 2.0) * 1e9);")
        session.pw.wait_frames(pg, n=1, min_ms=130)
        se = pg.evaluate("() => ({ sysK: __U.F.sysK, n: document.getElementById('notice').textContent })")
        if se["sysK"] != 0 or "Inconnu" not in se["n"]:
            issues.append(f"SYS_END + 2 Ga check failed: {se}")

        # 5. Click #b-now -> S.ty ≈ 0 AND S.evCur cleared (WEB-BUG-14)
        pg.evaluate("const bb = __U.EVL.find(e => e.n === 'Big Bang'); if (bb) __U.evGo(bb);")
        session.pw.wait_frames(pg, n=1, min_ms=130)
        pg.evaluate("window.__U.S.playing = false; document.getElementById('b-now').click();")
        session.pw.wait_frames(pg, n=1, min_ms=130)
        now_st = pg.evaluate("() => ({ ty: __U.S.ty, evCur: __U.S.evCur ? __U.S.evCur.n : null })")
        if abs(now_st["ty"]) > 1e-3:
            issues.append(f"#b-now did not reset S.ty=0 (got {now_st['ty']})")
        if now_st["evCur"] is not None:
            issues.append(f"#b-now left stale S.evCur={now_st['evCur']!r} (WEB-BUG-14)")
        if errs:
            issues.append(f"pageerrors: {errs}")

    # Also enforce WEB-BUG-04 red-giant AST/TNO label scaling on the warm page
    from tier2_f3_web_runtime import t2_f3_04_red_giant_ast_tno_labels_scaled
    try:
        t2_f3_04_red_giant_ast_tno_labels_scaled(session)
    except Exception as exc:
        issues.append(str(exc))

    check(not issues, "; ".join(issues[:6]), {"issues": issues})
    return "Deep-time cosmic journey (Big Bang -> -4.6 Ga -> 1969 -> +5.44 Ga -> T_DIV -> SYS_END -> Today) PASS", {}


def t4_e2e_03_mobile_touch_panels_and_context_loss(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []
    with session.pw.open_isolated_page(
        viewport=(390, 780),
        device_scale_factor=2,
        has_touch=True,
        is_mobile=True,
        color_scheme="dark",
    ) as (pg, errs, _):
        # Open mobile drawer #b-more and exercise all 5 panels
        pg.evaluate("document.getElementById('b-more').click();")
        pg.wait_for_timeout(150)
        for pkey, pid in (("chrono", "p-chrono"), ("cosmo", "p-cosmo"), ("view", "p-view"), ("find", "p-find"), ("about", "p-about")):
            pg.evaluate(f"window.__U.openPanel('{pkey}');")
            session.pw.wait_frames(pg, n=1, min_ms=120)
            st = pg.evaluate(
                f"""() => ({{
                    hidden: document.getElementById('{pid}').hidden,
                    overflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
                }})"""
            )
            if st["hidden"]:
                issues.append(f"Mobile panel #{pid} did not open")
            if st["overflowX"]:
                issues.append(f"Horizontal scroll overflow on mobile panel #{pid}")

        about_txt = pg.evaluate("document.getElementById('p-about').textContent")
        if "180 événements" in about_txt:
            issues.append("Mobile #p-about still contains stale '180 événements' copy (WEB-SIMP-06)")

        # Trigger WebGL context-loss recovery on mobile micro-scale
        pg.evaluate("window.__U.openPanel(null); window.__U.goTo(-20.0, { focus: 'earth', instant: true }); window.__U.S.logR = -20.0;")
        session.pw.wait_frames(pg, n=1, min_ms=130)
        with pg.expect_navigation(wait_until="domcontentloaded", timeout=30000):
            pg.evaluate("window.__U.onLost();")
        pg.wait_for_function("window.__U && window.__U.frame() > 2", polling=200, timeout=150000)
        session.pw.wait_frames(pg, n=1, min_ms=130)
        rec = pg.evaluate("() => ({ resumed: !!__U.S.resumed, logR: __U.S.logR, reprise: sessionStorage.getItem('univers-reprise') })")
        if not rec["resumed"]:
            issues.append("Mobile onLost did not set S.resumed")
        if abs(rec["logR"] - (-20.0)) > 0.2:
            issues.append(f"Mobile micro-scale lost on context-loss reload: logR={rec['logR']:.2f} (WEB-BUG-06)")
        if rec["reprise"] is not None:
            issues.append("Mobile sessionStorage['univers-reprise'] not cleared after resume")
        if errs:
            issues.append(f"pageerrors: {errs}")

    check(not issues, "; ".join(issues[:6]), {"issues": issues})
    return "Mobile 390x780 touch workflow: all 5 panels, 0 X-overflow, accurate copy & context-loss recovery PASS", {}


def t4_e2e_04_private_deployment_and_untrusted_feed(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []

    # 1. Validate infra/* configs & render temp storage.rules in workspace
    from tier1_f7_ci_infra_docs import t1_f7_03_infra_firebase_and_deploy_template
    try:
        t1_f7_03_infra_firebase_and_deploy_template(session)
    except Exception as exc:
        issues.append(f"infra/* validation: {exc}")

    tpl = (INFRA_DIR / "storage.rules.tpl").read_text(encoding="utf-8")
    tmp_rules = session.workspace.subdir("t4_e2e_04") / "storage.rules"
    tmp_rules.write_text(tpl.replace("__AUTHORIZED_EMAIL__", "marc+verify@example.com"), encoding="utf-8")
    check("marc+verify@example.com" in tmp_rules.read_text(encoding="utf-8"), "Temp storage.rules render failed")

    # 2. Serve built temp HTML with window.__ASSETS pointing to hostile XSS feed while blocking ALL external origins except local Three.js proxy
    base_url = session.server.start()
    init_js = (
        "window.__TIER=0; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[]; "
        f"window.__ASSETS={{ ngc: '{base_url}/mock/evil_ngc.json', fusc: '', fusi: '', nbl: '', flame: '' }};"
    )
    snap = session.server.snapshot_log()
    with session.pw.open_isolated_page(
        init_script=init_js,
        block_all_external=True,
        proxy_three_local=True,
        abort_fonts=True,
    ) as (pg, errs, _):
        pg.evaluate("document.getElementById('b-find').click();")
        loaded = False
        for _ in range(15):
            btns = pg.evaluate(
                """() => {
                    const i = document.getElementById('find-q');
                    i.value = 'NGC 999903';
                    i.dispatchEvent(new Event('input'));
                    return [...document.querySelectorAll('#find-res button')].map(b => b.textContent);
                }"""
            )
            if any("999903" in b for b in btns):
                loaded = True
                break
            pg.wait_for_timeout(150)
        if not loaded:
            issues.append("window.__ASSETS.ngc did not load custom/hostile feed (WEB-SEC-04)")
        else:
            pg.evaluate("[...document.querySelectorAll('#find-res button')].find(b => b.textContent.includes('999903')).click();")
            pg.wait_for_timeout(300)

        xss = pg.evaluate("() => ({ svg: window.__XSS_SVG || null, card: window.__XSS_CARD || null, injectedSvg: document.querySelectorAll('#card-dl svg[onload], #find-res svg[onload]').length })")
        if xss["svg"] or xss["card"] or xss["injectedSvg"] > 0:
            issues.append(f"XSS executed/injected under untrusted feed: {xss} (WEB-SEC-01)")

        # Verify interactive navigation works + 0 /_blob/* requests leaked
        nav_ok = pg.evaluate("window.__U.goName('Jupiter')")
        if not nav_ok:
            issues.append("goName('Jupiter') failed in self-hosted offline proxy mode")
        reqs = session.server.requests_since(snap)
        blob_reqs = [r[1] for r in reqs if "/_blob/" in r[1]]
        if blob_reqs:
            issues.append(f"Leaked hardcoded /_blob/* request(s): {blob_reqs[:5]} (WEB-SEC-04)")
        if errs:
            issues.append(f"pageerrors: {errs}")

    check(not issues, "; ".join(issues[:6]), {"issues": issues})
    return "Private self-hosted Firebase/loopback deployment: infra valid, 0 /_blob/* leaks, 0 XSS, full nav PASS", {}


_ASSERT_GATE_RE = re.compile(r"\b(process\.exit\s*\(|process\.exitCode\b|assert\s*[\.(]|throw\s+new\s+Error\b)")


def t4_e2e_05_full_26_js_physics_certification_sla(session: E2ESession) -> Tuple[str, dict]:
    test_files = sorted(APP_TEST.glob("*.test.js"))
    check(len(test_files) >= 26, f"Expected >= 26 JS test files, got {len(test_files)}")

    false_green = [p.name for p in test_files if not _ASSERT_GATE_RE.search(p.read_text(encoding="utf-8"))]

    # Run all 26 tests in parallel (4 workers) with strict 65.0s per-test SLA cap!
    t0 = time.monotonic()

    def _run_one(p):
        r = run_cmd(["node", str(p)], cwd=REPO_ROOT, timeout=65.0)
        return p.name, r.rc, r.duration_s, r.timed_out

    results: Dict[str, Tuple[int, float, bool]] = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for name, rc, dur, to in ex.map(_run_one, test_files):
            results[name] = (rc, dur, to)
    total_wall = time.monotonic() - t0

    issues: List[str] = []
    if false_green:
        issues.append(f"{len(false_green)} false-green tests without exit/assert gates: {', '.join(false_green)}")

    failed_tests = [f"{k}(rc={rc},{'TIMEOUT' if to else f'{dur:.1f}s'})" for k, (rc, dur, to) in sorted(results.items()) if rc != 0 or to]
    if failed_tests:
        issues.append(f"{len(failed_tests)}/{len(test_files)} JS tests failed/timed out (>65s): {', '.join(failed_tests)}")

    ev_rc, ev_dur, ev_to = results.get("evenements.test.js", (-1, 999.0, True))
    if ev_to or ev_dur >= 5.0:
        issues.append(f"evenements.test.js SLA missed: {'TIMEOUT(65s)' if ev_to else f'{ev_dur:.2f}s'} (max 5.0s)")

    if total_wall >= 120.0:
        issues.append(f"Total 4-worker parallel wall time {total_wall:.1f}s >= 120.0s SLA")

    details = {
        "total_tests": len(test_files),
        "passed_count": sum(1 for rc, _, to in results.values() if rc == 0 and not to),
        "total_wall_s": round(total_wall, 2),
        "slowest": sorted(((k, round(dur, 2), to) for k, (_, dur, to) in results.items()), key=lambda x: -x[1])[:6],
        "false_green": false_green,
    }
    check(not issues, "; ".join(issues[:6]), details)
    return f"All {len(test_files)}/{len(test_files)} JS physics tests PASS in {total_wall:.1f}s (0 false-green, evenements={ev_dur:.2f}s)", details


def t4_e2e_06_native_dual_compiler_and_valgrind_cert(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []
    from tier1_f5_native_cpp import (
        t1_f5_01_cmake_physique_gcc,
        t1_f5_02_cmake_natif_linux_portable,
        t1_f5_03_cmake_physique_clang,
        t1_f5_04_essai_cosmologie_valgrind,
        t1_f5_05_essai_interface_valgrind,
        t1_f5_06_essai_galaxie_accuracy_perf,
        t1_f5_07_essai_systeme_solaire_noyau,
    )
    from tier2_f5_native_cpp import t2_f5_07_headers_raii_stb_and_truth

    for label, fn in (
        ("GCC CMake physique", t1_f5_01_cmake_physique_gcc),
        ("GCC CMake natif portable", t1_f5_02_cmake_natif_linux_portable),
        ("Clang CMake physique", t1_f5_03_cmake_physique_clang),
        ("essai_cosmologie+VG", t1_f5_04_essai_cosmologie_valgrind),
        ("essai_interface+VG", t1_f5_05_essai_interface_valgrind),
        ("essai_galaxie perf", t1_f5_06_essai_galaxie_accuracy_perf),
        ("essai_systeme_solaire --noyau+VG", t1_f5_07_essai_systeme_solaire_noyau),
        ("Headers/RAII/stb", t2_f5_07_headers_raii_stb_and_truth),
    ):
        try:
            fn(session)
        except Exception as exc:
            issues.append(f"[{label}] {str(exc)[:180]}")

    check(not issues, "; ".join(issues[:6]), {"issues": issues})
    return "Dual-compiler GCC+Clang C++20 (-Werror), all native tests, perf SLA & Valgrind certification PASS", {}


def t4_e2e_07_complete_pre_merge_release_gate(session: E2ESession) -> Tuple[str, dict]:
    before_dist = sha256_file(DIST_HTML)
    issues: List[str] = []

    from tier1_f1_build_truth import t1_f1_01_standalone_build, t1_f1_06_static_quality_gates
    from tier1_f5_native_cpp import t1_f5_01_cmake_physique_gcc, t1_f5_02_cmake_natif_linux_portable
    from tier1_f6_pipeline import (
        t1_f6_01_pipeline_syntax,
        t1_f6_02_test_build_gw_stdlib,
        t1_f6_03_test_pipeline_stdlib,
        t1_f6_04_pyproject_and_requirements,
        t1_f6_05_paths_helper_contract,
    )
    from tier1_f7_ci_infra_docs import (
        t1_f7_01_workflows_yaml_and_least_privilege,
        t1_f7_02_ci_multistack_and_supply_chain,
        t1_f7_03_infra_firebase_and_deploy_template,
        t1_f7_04_git_hygiene_contracts,
        t1_f7_05_credits_attribution_completeness,
        t1_f7_06_docs_sync_and_github_audit,
    )
    from tier3_cross_feature import t3_cf_10_clean_gen_dead_keys_and_bundle

    gates = (
        ("F6 syntax", t1_f6_01_pipeline_syntax),
        ("F6 pyproject", t1_f6_04_pyproject_and_requirements),
        ("F6 _paths", t1_f6_05_paths_helper_contract),
        ("F6 gw test", t1_f6_02_test_build_gw_stdlib),
        ("F6 stdlib tests", t1_f6_03_test_pipeline_stdlib),
        ("F1xF6 dead keys", t3_cf_10_clean_gen_dead_keys_and_bundle),
        ("F1 temp build", t1_f1_01_standalone_build),
        ("F1 lint/prettier", t1_f1_06_static_quality_gates),
        ("F5 CMake physique", t1_f5_01_cmake_physique_gcc),
        ("F5 CMake natif", t1_f5_02_cmake_natif_linux_portable),
        ("F7 workflows YAML", t1_f7_01_workflows_yaml_and_least_privilege),
        ("F7 CI coverage", t1_f7_02_ci_multistack_and_supply_chain),
        ("F7 infra", t1_f7_03_infra_firebase_and_deploy_template),
        ("F7 git hygiene", t1_f7_04_git_hygiene_contracts),
        ("F7 CREDITS", t1_f7_05_credits_attribution_completeness),
        ("F7 docs & audit", t1_f7_06_docs_sync_and_github_audit),
    )
    for label, fn in gates:
        try:
            fn(session)
        except Exception as exc:
            issues.append(f"[{label}] {str(exc)[:150]}")

    check(sha256_file(DIST_HTML) == before_dist, "dist/index.html changed during pre-merge release gate!")
    check(not issues, f"Pre-merge gate failed {len(issues)}/{len(gates)} checks: {'; '.join(issues[:6])}", {"failed_count": len(issues), "issues": issues})
    return f"All {len(gates)}/{len(gates)} cross-stack pre-merge professional release gates PASS (dist unchanged)", {}


def get_tests() -> List[TestCase]:
    return [
        TestCase("T4-E2E-01", 4, ["F1", "F2", "F3", "F4"], "Desktop 47-order-of-magnitude exploration (10^-20 m -> Cosmic Horizon) + WebGL frames", t4_e2e_01_desktop_47_order_exploration),
        TestCase("T4-E2E-02", 4, ["F1", "F2", "F3", "F4"], "Deep-time cosmic journey (Big Bang -> 1969 -> +5.44 Ga -> T_DIV -> SYS_END -> Today)", t4_e2e_02_deep_time_cosmic_journey, expected_milestone="M2"),
        TestCase("T4-E2E-03", 4, ["F1", "F3", "F4"], "Mobile touch UX (390x780), all 5 panels, copy accuracy & context-loss recovery", t4_e2e_03_mobile_touch_panels_and_context_loss, expected_milestone="M2"),
        TestCase("T4-E2E-04", 4, ["F1", "F3", "F4", "F7"], "Private self-hosted Firebase/loopback deployment & untrusted XSS feed simulation", t4_e2e_04_private_deployment_and_untrusted_feed, expected_milestone="M2/M6"),
        TestCase("T4-E2E-05", 4, ["F1", "F2"], "Full 26-test quantitative physics certification & parallel speed SLA (<120s, ev<5s)", t4_e2e_05_full_26_js_physics_certification_sla, expected_milestone="M1/M2"),
        TestCase("T4-E2E-06", 4, ["F5", "F2"], "Portable native C++20 dual-compiler (GCC + Clang), 0-warning & Valgrind certification", t4_e2e_06_native_dual_compiler_and_valgrind_cert, expected_milestone="M4"),
        TestCase("T4-E2E-07", 4, ["F1", "F5", "F6", "F7"], "Complete pre-merge cross-stack professional release gate", t4_e2e_07_complete_pre_merge_release_gate, expected_milestone="M3-M6"),
    ]
