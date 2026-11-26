"""Tier 1 — F3: Interactive Web Runtime, WebGL2 Rendering & UI UX (Playwright, 6 tests)."""
from __future__ import annotations

from typing import List, Tuple

from lib.harness import (
    E2ESession,
    TestCase,
    UI_BLOCKS,
    UI_CUT_JS,
    UI_MEASURE_JS,
    check,
    compute_card_contrast,
    compute_ui_overlaps,
)


def t1_f3_01_webgl2_hdr_boot(session: E2ESession) -> Tuple[str, dict]:
    pg, errs, _ = session.pw.get_warm_desktop_page()
    info = pg.evaluate(
        r"""() => {
            const c = document.getElementById('gl');
            const ld = document.getElementById('loader');
            return {
                hasU: !!window.__U,
                frames: window.__U ? window.__U.frame() : 0,
                hdr: !!(window.__U && window.__U.Rr && window.__U.Rr.hdr),
                cw: c ? c.width : 0,
                ch: c ? c.height : 0,
                loaderGone: !ld || ld.classList.contains('out') || getComputedStyle(ld).opacity === '0',
            };
        }"""
    )
    check(info["hasU"] and info["frames"] > 2, f"WebGL2 app did not render frames: {info}")
    check(info["hdr"] is True, f"Expected HDR WebGL2 pipeline active (Rr.hdr===true), got {info}")
    check(info["cw"] > 0 and info["ch"] > 0, f"Canvas has zero dimensions: {info}")
    check(info["loaderGone"], f"Loader overlay still blocking after boot: {info}")
    check(len(errs) == 0, f"Uncaught pageerrors during boot: {errs}")
    return f"WebGL2 HDR booted cleanly ({info['cw']}×{info['ch']}, frame={info['frames']}, 0 pageerrors)", info


def t1_f3_02_nav_search_parsewhen_eclipse(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()

    # goName('Jupiter')
    jup = pg.evaluate(
        r"""() => {
            const ok = window.__U.goName('Jupiter');
            return { ok, focus: window.__U.S.focus };
        }"""
    )
    session.pw.wait_frames(pg, n=1, min_ms=130)
    jup_dom = pg.evaluate(
        r"""() => ({
            place: (document.getElementById('place') || {}).textContent || '',
            cardHidden: !!(document.getElementById('card') || {}).hidden,
            cardSub: (document.getElementById('card-sub') || {}).textContent || '',
        })"""
    )
    check(jup["ok"] and jup["focus"] == "jupiter", f"goName('Jupiter') failed: {jup}")
    check(not jup_dom["cardHidden"], f"Jupiter card did not open: {jup_dom}")

    # goName('Sirius')
    pg.evaluate("window.__U.goName('Sirius');")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    sirius = pg.evaluate(
        r"""() => ({
            cardHidden: !!(document.getElementById('card') || {}).hidden,
            title: (document.getElementById('card-title') || {}).textContent || '',
            dl: (document.getElementById('card-dl') || {}).textContent || '',
        })"""
    )
    check(not sirius["cardHidden"] and "Sirius" in sirius["title"], f"Sirius card invalid: {sirius}")
    check("Distance" in sirius["dl"], f"Sirius card missing Distance row: {sirius['dl'][:120]}")

    # parseWhen & eclipseScan
    helpers = pg.evaluate(
        r"""() => ({
            apollo: window.__U.parseWhen('20/07/1969'),
            future5: window.__U.parseWhen('dans 5 Ga'),
            invalid: window.__U.parseWhen('pas_une_date_du_tout'),
            eclipse2026: window.__U.eclipseScan(2461265.24, 2).sol[2],
        })"""
    )
    check(helpers["apollo"] is not None and -60 < helpers["apollo"] < -54, f"parseWhen('20/07/1969') bad: {helpers}")
    check(helpers["future5"] is not None and abs(helpers["future5"] - 5e9) < 1e7, f"parseWhen('dans 5 Ga') bad: {helpers}")
    check(helpers["invalid"] is None, f"parseWhen invalid string should return null, got {helpers['invalid']!r}")
    check(helpers["eclipse2026"] == "totale", f"2026-08-12 eclipse expected 'totale', got {helpers['eclipse2026']!r}")

    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors: {errs[err_idx:]}")
    return "goName(Jupiter/Sirius), parseWhen & 2026 total eclipse scan PASS", helpers


def t1_f3_03_macro_to_micro_stops(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()
    visited = []
    for idx, expected_sub in ((1, "Système solaire"), (4, "Voie lactée"), (8, "Univers"), (15, "Inconnu")):
        pg.evaluate(f"window.__U.goStop(window.__U.STOPS[{idx}], true);")
        session.pw.wait_frames(pg, n=1, min_ms=130)
        st = pg.evaluate(
            r"""() => ({
                logR: window.__U.S.logR,
                place: (document.getElementById('place') || {}).textContent || '',
            })"""
        )
        check(expected_sub.lower() in st["place"].lower(),
              f"STOPS[{idx}] expected #place containing {expected_sub!r}, got {st['place']!r} (logR={st['logR']:.2f})")
        visited.append((idx, round(st["logR"], 2), st["place"]))

    # Confirm STOPS[15] is LMICRO = -20.0
    check(abs(visited[-1][1] - (-20.0)) < 0.05, f"STOPS[15] logR expected -20.0, got {visited[-1]}")
    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors: {errs[err_idx:]}")
    return f"Traversed 47 orders of magnitude cleanly: {visited}", {"visited": visited}


def t1_f3_04_events_and_evgo(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()
    info = pg.evaluate(
        r"""() => {
            const U = window.__U;
            const bb = U.EVL.find(e => e.n === 'Big Bang');
            if (bb) U.evGo(bb);
            return { evCount: U.EVL.length, foundBB: !!bb };
        }"""
    )
    check(info["evCount"] >= 700, f"Expected >= 700 real astronomical events, got {info['evCount']}")
    check(info["foundBB"], "Big Bang event not found in EVL")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    bb = pg.evaluate(
        r"""() => ({
            age: window.__U.F.age,
            title: (document.getElementById('card-title') || {}).textContent || '',
            dl: (document.getElementById('card-dl') || {}).textContent || '',
            cardHidden: !!(document.getElementById('card') || {}).hidden,
        })"""
    )
    check(bb["age"] < 0.001, f"evGo(Big Bang) expected F.age < 0.001 Ga, got {bb['age']}")
    check(not bb["cardHidden"] and "Big Bang" in bb["title"], f"Big Bang card did not open: {bb}")
    check("Certitude" in bb["dl"] and "Source" in bb["dl"], f"Big Bang card missing Certitude/Source rows: {bb['dl'][:160]}")
    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors: {errs[err_idx:]}")
    return f"EVL={info['evCount']} events; evGo('Big Bang') age={bb['age']:.5f} Ga with Certitude & Source", info


def t1_f3_05_truth_cutoffs_and_about_copy(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()
    # T_DIV + 1e-4 Ga
    pg.evaluate("window.__U.goTo(11.5, { focus: 'sun', instant: true }); window.__U.setTime((window.__U.T_DIV + 1e-4) * 1e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    tdiv = pg.evaluate(
        r"""() => ({
            engEarth: !!window.__U.F.eng.earth,
            notice: (document.getElementById('notice') || {}).textContent || '',
        })"""
    )
    check(tdiv["engEarth"] and "Schröder" in tdiv["notice"] and "Rasio" in tdiv["notice"] and "Rybicki" in tdiv["notice"],
          f"T_DIV truth notice incomplete: {tdiv}")

    # +50 Ga > SYS_END
    pg.evaluate("window.__U.setTime(50e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    far = pg.evaluate(
        r"""() => ({
            sysK: window.__U.F.sysK,
            notice: (document.getElementById('notice') || {}).textContent || '',
        })"""
    )
    check(far["sysK"] == 0 and far["notice"].startswith("Inconnu"), f"+50 Ga truth rule failed: {far}")

    # About panel copy truthfulness (WEB-SIMP-06: must not claim stale "180 événements" when EVL=738)
    about_txt = pg.evaluate("document.getElementById('p-about').textContent")
    ev_count = pg.evaluate("window.__U.EVL.length")
    check("180 événements" not in about_txt, f"Stale UI copy '180 événements' still present in #p-about (actual EVL={ev_count})")
    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors: {errs[err_idx:]}")
    return f"Truth cutoffs PASS & #p-about copy synchronized (no stale '180 événements', EVL={ev_count})", {"evCount": ev_count}


def t1_f3_06_desktop_ui_non_overlap_contrast(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()
    situations = [
        ("accueil", "__U.S.playing=false; __U.select(null); __U.openPanel(null); __U.goStop(__U.STOPS[0], true)", True),
        ("fiche Jupiter", "__U.goName('Jupiter')", False),
        ("fiche Sirius", "__U.goName('Sirius')", False),
        ("chronologie", "__U.select(null); __U.openPanel('chrono')", False),
        ("affichage", "__U.openPanel('view')", False),
        ("recherche", "document.getElementById('b-find').click()", False),
        ("infiniment petit", "__U.openPanel(null); __U.goStop(__U.STOPS[12], true)", False),
    ]
    fails: List[str] = []
    sirius_contrast = 0.0
    for name, js, is_rest in situations:
        pg.evaluate(js)
        session.pw.wait_frames(pg, n=1, min_ms=130)
        pg.evaluate("document.getElementById('rail').classList.add('show')")
        pg.wait_for_timeout(120)
        items = pg.evaluate(UI_MEASURE_JS, UI_BLOCKS)
        ov = compute_ui_overlaps(items, tol=2.0)
        for o in ov:
            fails.append(f"{name}: overlap {o}")
        if is_rest:
            opaque_blocks = [x["name"] for x in items if x["opaque"] and not x["leaf"]]
            if len(opaque_blocks) > 2:
                fails.append(f"{name}: {len(opaque_blocks)} opaque rest blocks (>2): {opaque_blocks}")
        cut = pg.evaluate(UI_CUT_JS)
        for c in cut:
            fails.append(f"{name}: {c}")
        if name == "fiche Sirius":
            sirius_contrast = compute_card_contrast(pg)
            if sirius_contrast < 4.5:
                fails.append(f"fiche Sirius contrast {sirius_contrast:.2f} < 4.5")
        pg.evaluate("document.getElementById('rail').classList.remove('show')")

    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors: {errs[err_idx:]}")
    check(not fails, f"Desktop UI layout issues ({len(fails)}): {'; '.join(fails[:6])}", {"fails": fails[:12]})
    return f"7 desktop situations: 0 overlaps, <=2 rest blocks, 0 cut buttons, contrast={sirius_contrast:.1f}", {"contrast": round(sirius_contrast, 2)}


def get_tests() -> List[TestCase]:
    return [
        TestCase("T1-F3-01", 1, ["F3"], "WebGL2 HDR clean boot in Playwright SwiftShader", t1_f3_01_webgl2_hdr_boot),
        TestCase("T1-F3-02", 1, ["F3"], "Navigation, search (goName), date parser (parseWhen) & eclipseScan", t1_f3_02_nav_search_parsewhen_eclipse),
        TestCase("T1-F3-03", 1, ["F3"], "Macro-to-micro scale traversal (Solar System -> Observable Universe -> LMICRO)", t1_f3_03_macro_to_micro_stops),
        TestCase("T1-F3-04", 1, ["F3"], "Real events catalog (EVL >= 700) & evGo('Big Bang') card provenance", t1_f3_04_events_and_evgo),
        TestCase("T1-F3-05", 1, ["F3"], "Live scientific truth cutoffs & #p-about event count copy accuracy", t1_f3_05_truth_cutoffs_and_about_copy, expected_milestone="M2"),
        TestCase("T1-F3-06", 1, ["F3"], "Desktop (1280x800) UI non-overlap, rest-block budget & WCAG card contrast", t1_f3_06_desktop_ui_non_overlap_contrast),
    ]
