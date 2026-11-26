"""Tier 2 — F3: Responsive Mobile UX, WebGL Context-Loss Recovery & Runtime Bug Guards (6 tests)."""
from __future__ import annotations

import re
from typing import List, Tuple

from lib.harness import (
    APP_SRC,
    APP_TEST,
    E2ESession,
    TestCase,
    UI_BLOCKS,
    UI_CUT_JS,
    UI_MEASURE_JS,
    check,
    compute_card_contrast,
    compute_ui_overlaps,
)


def t2_f3_01_mobile_ui_non_overlap_and_light_contrast(session: E2ESession) -> Tuple[str, dict]:
    fails: List[str] = []
    bar_ratio = 0.0
    light_contrast = 0.0

    pg, err_idx = session.pw.reset_warm_page()
    try:
        pg.set_viewport_size({"width": 390, "height": 780})
        pg.evaluate("window.dispatchEvent(new Event('resize'));")
        session.pw.wait_frames(pg, n=2, min_ms=140)
        situations = [
            ("accueil", "__U.S.playing=false; __U.select(null); __U.openPanel(null); __U.goStop(__U.STOPS[0], true)", True),
            ("fiche Jupiter", "__U.goName('Jupiter')", False),
            ("fiche Sirius", "__U.goName('Sirius')", False),
            ("chronologie", "__U.select(null); __U.openPanel('chrono')", False),
            ("recherche", "document.getElementById('b-find').click()", False),
        ]
        for name, js, is_rest in situations:
            pg.evaluate(js)
            session.pw.wait_frames(pg, n=1, min_ms=130)
            pg.evaluate("document.getElementById('rail').classList.add('show')")
            pg.wait_for_timeout(80)
            items = pg.evaluate(UI_MEASURE_JS, UI_BLOCKS)
            for o in compute_ui_overlaps(items, tol=2.0):
                fails.append(f"phone {name}: overlap {o}")
            if is_rest:
                opaque_blocks = [x["name"] for x in items if x["opaque"] and not x["leaf"]]
                if len(opaque_blocks) > 2:
                    fails.append(f"phone {name}: {len(opaque_blocks)} opaque rest blocks (>2)")
                bar = next((x for x in items if x["name"] == "barre du bas"), None)
                bar_ratio = (bar["box"][3] - bar["box"][1]) / 780.0 if bar else 0.0
                if bar_ratio > 0.15:
                    fails.append(f"phone bottom bar {bar_ratio:.1%} > 15%")
            for c in pg.evaluate(UI_CUT_JS):
                fails.append(f"phone {name}: {c}")
            pg.evaluate("document.getElementById('rail').classList.remove('show')")

        pg.emulate_media(color_scheme="light")
        pg.evaluate("__U.openPanel(null); __U.goName('Sirius');")
        session.pw.wait_frames(pg, n=1, min_ms=130)
        light_contrast = compute_card_contrast(pg)
        if light_contrast < 4.5:
            fails.append(f"phone light-theme card contrast {light_contrast:.2f} < 4.5")
        _, errs, _ = session.pw.get_warm_desktop_page()
        if len(errs) != err_idx:
            fails.append(f"pageerrors: {errs[err_idx:]}")
    finally:
        try:
            pg.emulate_media(color_scheme="dark")
            pg.set_viewport_size({"width": 1280, "height": 800})
            pg.evaluate("window.dispatchEvent(new Event('resize'));")
        except Exception:
            pass

    check(not fails, f"Mobile UI issues ({len(fails)}): {'; '.join(fails[:6])}", {"bar_ratio": round(bar_ratio, 3), "light_contrast": round(light_contrast, 2)})
    return f"Mobile 390x780 PASS (bar={bar_ratio:.1%} <= 15%, 0 overlaps, light contrast={light_contrast:.1f})", {"bar_ratio": round(bar_ratio, 3), "light_contrast": round(light_contrast, 2)}


def t2_f3_02_context_loss_micro_recovery(session: E2ESession) -> Tuple[str, dict]:
    with session.pw.open_isolated_page() as (pg, errs, _):
        pg.evaluate("window.__U.goTo(-20.0, { focus: 'earth', instant: true }); window.__U.S.logR = -20.0;")
        session.pw.wait_frames(pg, n=1, min_ms=130)
        lr_before = pg.evaluate("window.__U.S.logR")
        check(abs(lr_before - (-20.0)) < 0.05, f"Failed to reach micro-scale before context loss: logR={lr_before}")

        # Trigger real WebGL context loss (or onLost) and wait for page reload
        with pg.expect_navigation(wait_until="domcontentloaded", timeout=30000):
            pg.evaluate(
                r"""() => {
                    const gl = document.getElementById('gl').getContext('webgl2') || document.getElementById('gl').getContext('webgl');
                    const ext = gl && gl.getExtension('WEBGL_lose_context');
                    if (ext) ext.loseContext(); else window.__U.onLost();
                }"""
            )
        pg.wait_for_function("window.__U && window.__U.frame() > 2", polling=200, timeout=150000)
        session.pw.wait_frames(pg, n=1, min_ms=130)
        after = pg.evaluate(
            r"""() => ({
                resumed: !!window.__U.S.resumed,
                logR: window.__U.S.logR,
                focus: window.__U.S.focus,
                reprise: sessionStorage.getItem('univers-reprise'),
            })"""
        )
        issues: List[str] = []
        if not after["resumed"]:
            issues.append("S.resumed was not true after WebGL context-loss reload")
        if abs(after["logR"] - (-20.0)) > 0.2:
            issues.append(f"Micro-scale lost on reload: logR={after['logR']:.2f} (expected ~-20.0, not LMIN 6.6; WEB-BUG-06)")
        if after["reprise"] is not None:
            issues.append(f"sessionStorage['univers-reprise'] was not cleared after resume: {after['reprise']!r} (WEB-BUG-06)")
        if errs:
            issues.append(f"pageerrors during recovery: {errs}")
        check(not issues, "; ".join(issues), after)
        return f"Context-loss reload preserved micro logR={after['logR']:.2f} & cleared sessionStorage", after


def t2_f3_03_window_u_and_b_now_evcur(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()
    issues: List[str] = []

    # 1. Trigger an event (sets S.evCur) then click #b-now -> S.ty ≈ 0 AND S.evCur MUST be cleared (WEB-BUG-14)
    pg.evaluate(
        r"""() => {
            const U = window.__U;
            const ev = U.EVL.find(e => e.n === 'Big Bang') || U.EVL[0];
            U.evGo(ev);
        }"""
    )
    session.pw.wait_frames(pg, n=1, min_ms=130)
    before_ev = pg.evaluate("!!window.__U.S.evCur")
    pg.evaluate("window.__U.S.playing = false; document.getElementById('b-now').click();")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    after = pg.evaluate("() => ({ ty: window.__U.S.ty, evCur: window.__U.S.evCur ? window.__U.S.evCur.n : null })")
    if not before_ev:
        issues.append("evGo did not set S.evCur before clicking #b-now")
    if abs(after["ty"]) > 1e-3:
        issues.append(f"#b-now did not reset S.ty to 0 (got {after['ty']})")
    if after["evCur"] is not None:
        issues.append(f"#b-now left stale S.evCur={after['evCur']!r} (WEB-BUG-14)")

    # 2. Check no duplicate `G` key in window.__U object literal across app/src/6*.js (WEB-BUG-02)
    src_6 = "\n".join(p.read_text(encoding="utf-8") for p in sorted(APP_SRC.glob("6*.js")))
    m_u = re.search(r"window\.__U\s*=\s*\{([^;]+)\}", src_6, re.S)
    if m_u:
        body = m_u.group(1)
        has_getter_g = bool(re.search(r"\bget\s+G\s*\(\)", body))
        has_bare_g = bool(re.search(r"(?:^|,)\s*G\s*(?:,|$)", body))
        if has_getter_g and has_bare_g:
            issues.append("Duplicate property key 'G' in window.__U literal (both `get G()` and shorthand `G`, WEB-BUG-02)")

    _, errs, _ = session.pw.get_warm_desktop_page()
    if len(errs) != err_idx:
        issues.append(f"pageerrors: {errs[err_idx:]}")
    check(not issues, "; ".join(issues), after)
    return "#b-now resets S.ty=0 & clears S.evCur; window.__U has no duplicate G key", after


def t2_f3_04_red_giant_ast_tno_labels_scaled(session: E2ESession) -> Tuple[str, dict]:
    # Verify behaviorally via runtime + built bundle check: at +9 Ga (F.orb > 1.5),
    # AST/TNO labels (Cérès, Pluton) MUST track the scaled F.orb position matching selBody/CEN.pluto (WEB-BUG-04)!
    pg, err_idx = session.pw.reset_warm_page()
    pg.evaluate("window.__U.goTo(13.2, { focus: 'sun', instant: true }); window.__U.setTime(9e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    info = pg.evaluate(
        r"""() => {
            const U = window.__U;
            const orb = U.F.orb;
            const plutoBody = U.cenOf('pluto');
            // Project Pluto's scaled body position to screen pixels
            const proj = U.Rr.project(plutoBody, U.F, [0, 0, 0]);
            // Find the DOM label for 'Pluton'
            const lab = [...document.querySelectorAll('#labels .lb')].find(el => el.textContent.trim() === 'Pluton');
            const labRect = lab ? lab.getBoundingClientRect() : null;
            const labCenter = labRect ? [labRect.left + labRect.width / 2, labRect.top + labRect.height / 2] : null;
            return {
                orb,
                plutoBody,
                proj: proj ? [proj[0], proj[1]] : null,
                labCenter,
                labOpacity: lab ? parseFloat(getComputedStyle(lab).opacity) : 0,
            };
        }"""
    )
    check(info["orb"] > 1.5, f"Expected red-giant F.orb > 1.5 at +9 Ga, got {info['orb']}")
    # Also check unscaled vs scaled screen position directly if Pluto is on screen, AND check AST/TNO label get() formula
    issues: List[str] = []
    if info["proj"] and info["labCenter"] and info["labOpacity"] > 0.05:
        dx = abs(info["proj"][0] - info["labCenter"][0])
        dy = abs(info["proj"][1] - info["labCenter"][1])
        dist_px = (dx * dx + dy * dy) ** 0.5
        info["screenDistPx"] = round(dist_px, 1)
        if dist_px > 45.0:
            issues.append(f"Pluton label detached by {dist_px:.1f} px from scaled body at +9 Ga (F.orb={info['orb']:.2f}, WEB-BUG-04)")
    else:
        # Fallback if Pluto is outside frustum at current camera angle: point camera at Pluto and measure
        pg.evaluate(
            r"""() => {
                const U = window.__U;
                const p = U.cenOf('pluto');
                const d = Math.hypot(p[0], p[1], p[2]) || 1;
                const ae = U.Rr.azelFrom([-p[0]/d, -p[1]/d, -p[2]/d], 0);
                U.goTo(13.2, { focus: 'sun', az: ae[0], el: ae[1], instant: true });
            }"""
        )
        session.pw.wait_frames(pg, n=1, min_ms=130)
        info2 = pg.evaluate(
            r"""() => {
                const U = window.__U;
                const p = U.cenOf('pluto');
                const proj = U.Rr.project(p, U.F, [0, 0, 0]);
                const lab = [...document.querySelectorAll('#labels .lb')].find(el => el.textContent.trim() === 'Pluton');
                const r = lab ? lab.getBoundingClientRect() : null;
                return {
                    proj: proj ? [proj[0], proj[1]] : null,
                    lab: r ? [r.left + r.width / 2, r.top + r.height / 2] : null,
                    op: lab ? parseFloat(getComputedStyle(lab).opacity) : 0,
                };
            }"""
        )
        if info2["proj"] and info2["lab"] and info2["op"] > 0.05:
            dist_px = ((info2["proj"][0] - info2["lab"][0]) ** 2 + (info2["proj"][1] - info2["lab"][1]) ** 2) ** 0.5
            info["screenDistPx"] = round(dist_px, 1)
            if dist_px > 45.0:
                issues.append(f"Pluton label detached by {dist_px:.1f} px from scaled body at +9 Ga (F.orb={info['orb']:.2f}, WEB-BUG-04)")

    # Cross-check AST_LABELS / TNO_LABELS callback scales by F.orb across app/src/6*.js
    src_6 = "\n".join(p.read_text(encoding="utf-8") for p in sorted(APP_SRC.glob("6*.js")))
    m_ast = re.search(r"for\s*\(\s*const\s+tag\s+of\s*\[\s*['\"]AST['\"]\s*,\s*['\"]TNO['\"]\s*\]\s*\)\s*\{[^}]*addLabel\([^;]+\)", src_6, re.S)
    if m_ast and "F.orb" not in m_ast.group(0):
        issues.append("AST_LABELS/TNO_LABELS addLabel callback omits '* F.orb' (WEB-BUG-04)")

    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors: {errs[err_idx:]}")
    check(not issues, "; ".join(issues), info)
    return f"Red-giant +9 Ga (F.orb={info['orb']:.2f}) AST/TNO labels track scaled positions cleanly", info


def t2_f3_05_no_nan_moon_vertex_buffer(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()
    # Jump to -4.6 Ga (before Solar System birth) where all moons have m.off === true
    pg.evaluate("window.__U.setTime(-4.6e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    nan_info = pg.evaluate(
        r"""() => {
            const U = window.__U;
            let moonNaN = 0, totalMoonFloats = 0, kPosNaN = 0;
            // Check Three.js Points geometries in scene for NaN floats in position buffers
            let sceneNaNBuffers = 0, sceneNaNFloats = 0;
            U.Rr.scene.traverse(obj => {
                if (obj.geometry && obj.geometry.attributes && obj.geometry.attributes.position) {
                    const arr = obj.geometry.attributes.position.array;
                    let bad = 0;
                    for (let i = 0; i < arr.length; i++) {
                        if (Number.isNaN(arr[i])) bad++;
                    }
                    if (bad > 0) { sceneNaNBuffers++; sceneNaNFloats += bad; }
                }
            });
            const mp = U.moonPos;
            for (let i = 0; i < mp.length; i++) if (Number.isNaN(mp[i])) kPosNaN++;
            return { sceneNaNBuffers, sceneNaNFloats, kPosNaN };
        }"""
    )
    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors: {errs[err_idx:]}")
    check(
        nan_info["sceneNaNBuffers"] == 0 and nan_info["sceneNaNFloats"] == 0 and nan_info["kPosNaN"] == 0,
        f"NaN floats written into WebGL vertex buffers / moonPos when moons are off (WEB-BUG-09): {nan_info}",
        nan_info,
    )
    return "0 NaN floats in WebGL scene vertex buffers & moonPos at -4.6 Ga (moons off)", nan_info


def t2_f3_06_setdyn_disposal_and_screen_test_hygiene(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []

    # 1. Behavioral test of R.setDyn material disposal (WEB-BUG-03) on warm Playwright page!
    pg, err_idx = session.pw.reset_warm_page()
    disp = pg.evaluate(
        r"""() => {
            const U = window.__U;
            const mkD = () => ({
                n: 4,
                out: new Float32Array(12),
                col: new Float32Array(12),
                look: new Float32Array(8),
                boost: 1,
            });
            const before = new Set(U.Rr.scene.children);
            U.Rr.setDyn(mkD());
            const added = U.Rr.scene.children.find(c => !before.has(c));
            let matDisposed = false, geomDisposed = false;
            if (added && added.material && added.geometry) {
                const om = added.material.dispose.bind(added.material);
                const og = added.geometry.dispose.bind(added.geometry);
                added.material.dispose = () => { matDisposed = true; return om(); };
                added.geometry.dispose = () => { geomDisposed = true; return og(); };
                U.Rr.setDyn(mkD());
            }
            return { foundAdded: !!added, geomDisposed, matDisposed };
        }"""
    )
    if not disp["foundAdded"]:
        issues.append("Could not observe dyn Points object added by R.setDyn")
    elif not (disp["geomDisposed"] and disp["matDisposed"]):
        issues.append(f"R.setDyn leaks GPU resource: geomDisposed={disp['geomDisposed']}, matDisposed={disp['matDisposed']} (WEB-BUG-03)")

    # 2. Screen test hygiene (WEB-TEST-04, WEB-SEC-03): no /home/claude, /mnt/user-data, or eval(
    for fname in ("lost.py", "dust_screen.py", "cone_screen.py", "lens_screen.py"):
        p = APP_TEST / fname
        if not p.is_file():
            continue
        txt = p.read_text(encoding="utf-8")
        for bad_tok in ("/home/claude", "/mnt/user-data"):
            if bad_tok in txt:
                issues.append(f"app/test/{fname} contains hardcoded personal path '{bad_tok}'")
        if re.search(r"\beval\s*\(", txt):
            issues.append(f"app/test/{fname} uses unsafe Python eval()")

    _, errs, _ = session.pw.get_warm_desktop_page()
    if len(errs) != err_idx:
        issues.append(f"pageerrors: {errs[err_idx:]}")
    check(not issues, "; ".join(issues), disp)
    return "R.setDyn disposes both geometry & material; screen tests free of personal paths & eval()", disp


def get_tests() -> List[TestCase]:
    return [
        TestCase("T2-F3-01", 2, ["F3"], "Mobile (390x780) UI non-overlap, bottom bar <=15% & light-theme contrast >=4.5", t2_f3_01_mobile_ui_non_overlap_and_light_contrast),
        TestCase("T2-F3-02", 2, ["F3"], "WebGL context-loss recovery in micro-scale preserves logR=-20 & clears sessionStorage", t2_f3_02_context_loss_micro_recovery, expected_milestone="M2"),
        TestCase("T2-F3-03", 2, ["F3"], "#b-now clears S.evCur & window.__U has no duplicate G key", t2_f3_03_window_u_and_b_now_evcur, expected_milestone="M2"),
        TestCase("T2-F3-04", 2, ["F3"], "Red-giant (+9 Ga) AST/TNO labels track scaled F.orb body coordinates", t2_f3_04_red_giant_ast_tno_labels_scaled, expected_milestone="M2"),
        TestCase("T2-F3-05", 2, ["F3"], "Out-of-range moons write zero NaN floats into WebGL vertex buffers", t2_f3_05_no_nan_moon_vertex_buffer, expected_milestone="M2"),
        TestCase("T2-F3-06", 2, ["F3"], "R.setDyn disposes ShaderMaterial & screen tests free of personal paths/eval()", t2_f3_06_setdyn_disposal_and_screen_test_hygiene, expected_milestone="M1/M2"),
    ]
