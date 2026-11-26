"""Tier 1 — F4: Web Security, DOM Hygiene & Offline / External Asset Resilience (6 tests)."""
from __future__ import annotations

from typing import List, Tuple

from lib.harness import (
    E2ESession,
    TestCase,
    check,
    extract_html_scripts,
)


def t1_f4_01_threejs_sri_cors(session: E2ESession) -> Tuple[str, dict]:
    html = session.workspace.temp_html_text()
    ext, _ = extract_html_scripts(html)
    three_tags = [s for s in ext if "three" in s.get("src", "").lower()]
    check(len(three_tags) == 1, f"Expected exactly 1 Three.js external script tag, got {len(three_tags)}")
    t = three_tags[0]
    check("0.149.0" in t.get("src", ""), f"Three.js not pinned to 0.149.0: {t.get('src')}")
    check(t.get("integrity", "").startswith("sha512-") and len(t["integrity"]) > 60,
          f"Missing/short sha512 integrity hash: {t.get('integrity')!r}")
    check(t.get("crossorigin") == "anonymous", f"Expected crossorigin='anonymous', got {t.get('crossorigin')!r}")
    check(t.get("referrerpolicy") == "no-referrer", f"Expected referrerpolicy='no-referrer', got {t.get('referrerpolicy')!r}")
    return "Three.js 0.149.0 pinned with sha512 SRI, crossorigin=anonymous, referrerpolicy=no-referrer", t


def t1_f4_02_offline_cdn_blocked_graceful(session: E2ESession) -> Tuple[str, dict]:
    with session.pw.open_isolated_page(
        block_cdnjs=True,
        proxy_three_local=False,
        abort_fonts=True,
        wait_ready=False,
    ) as (pg, errs, _):
        pg.wait_for_function(
            "() => { const h = document.querySelector('#loader h2'); return h && h.textContent.includes('impossible'); }",
            polling=100,
            timeout=30000,
        )
        st = pg.evaluate(
            r"""() => {
                const h2 = document.querySelector('#loader h2');
                const msg = document.getElementById('lmsg');
                const bar = document.getElementById('lbar');
                return {
                    h2: h2 ? h2.textContent.trim() : '',
                    msg: msg ? msg.textContent.trim() : '',
                    barHidden: !bar || bar.hidden || getComputedStyle(bar).display === 'none',
                };
            }"""
        )
        check(len(errs) == 0, f"Offline CDN block threw uncaught pageerrors: {errs}")
        check(st["h2"] == "Affichage impossible", f"Unexpected offline heading: {st['h2']!r}")
        check("bibliothèque 3D" in st["msg"] or "connexion" in st["msg"], f"Unexpected offline French notice: {st['msg']!r}")
        check(st["barHidden"], f"Progress bar #lbar should be hidden on CDN failure: {st}")
        return f"Offline CDN failure handled gracefully (0 pageerrors, '{st['h2']}')", st


def t1_f4_03_missing_optional_blobs(session: E2ESession) -> Tuple[str, dict]:
    # LoopbackServer returns HTTP 404 for all /_blob/* paths (including FUS_URL at boot)
    pg, err_idx = session.pw.reset_warm_page()
    ok = pg.evaluate("window.__U.goName('Mars')")
    session.pw.wait_frames(pg, n=2, min_ms=140)
    focus = pg.evaluate("window.__U.S.focus")
    _, errs, _ = session.pw.get_warm_desktop_page()
    reqs = session.server.requests_since(0)
    blob_404s = [r for r in reqs if "/_blob/" in r[1] and r[2] == 404]
    check(len(errs) == err_idx and len(errs) == 0, f"404 /_blob/* caused uncaught pageerrors: {errs}")
    check(len(blob_404s) >= 1, f"Expected at least one /_blob/* 404 request during boot, saw: {reqs[:10]}")
    check(ok and focus == "mars", f"Built-in navigation broken under 404 /_blob/*: ok={ok}, focus={focus}")
    return f"Boot & goName('Mars') succeeded cleanly with {len(blob_404s)} /_blob/* HTTP 404(s) & 0 pageerrors", {"blob_404s": len(blob_404s)}


def t1_f4_04_xss_openngc_card_blocked(session: E2ESession) -> Tuple[str, dict]:
    pg, errs = session.pw.get_evil_ngc_page()
    err_start = len(errs)
    pg.evaluate("window.__U.select(null); window.__U.openPanel(null); document.getElementById('b-find').click();")
    pg.wait_for_function(
        """() => {
            const i = document.getElementById('find-q');
            i.value = 'NGC 999901';
            i.dispatchEvent(new Event('input'));
            return [...document.querySelectorAll('#find-res button')].some(b => b.textContent.includes('999901'));
        }""",
        polling=100,
        timeout=25000,
    )
    pg.evaluate("[...document.querySelectorAll('#find-res button')].find(b => b.textContent.includes('999901')).click();")
    pg.wait_for_function("!document.getElementById('card').hidden", polling=100, timeout=20000)
    pg.wait_for_timeout(350)
    st = pg.evaluate(
        r"""() => ({
            xss: window.__XSS_CARD || null,
            imgCount: document.querySelectorAll('#card-dl img').length,
            dlText: (document.getElementById('card-dl') || {}).textContent || '',
        })"""
    )
    check(not st["xss"], f"XSS EXECUTED via OpenNGC card renderCard innerHTML (window.__XSS_CARD={st['xss']})", st)
    check(st["imgCount"] == 0, f"Unescaped <img> tag injected into #card-dl (count={st['imgCount']})", st)
    check("<img" in st["dlText"], f"Expected escaped literal '<img' text in #card-dl, got: {st['dlText'][:200]}")
    check(len(errs) == err_start, f"Unexpected pageerrors: {errs[err_start:]}")
    return "OpenNGC card constellation XSS neutralized (0 execution, 0 <img> nodes, literal text escaped)", st


def t1_f4_05_xss_search_and_svg_preserved(session: E2ESession) -> Tuple[str, dict]:
    pg, errs = session.pw.get_evil_ngc_page()
    err_start = len(errs)
    pg.evaluate("window.__U.select(null); window.__U.openPanel(null); document.getElementById('b-find').click();")
    pg.wait_for_function(
        """() => {
            const i = document.getElementById('find-q');
            i.value = 'NGC 999902';
            i.dispatchEvent(new Event('input'));
            return [...document.querySelectorAll('#find-res button')].some(b => b.textContent.includes('999902'));
        }""",
        polling=100,
        timeout=25000,
    )
    pg.wait_for_timeout(350)
    st = pg.evaluate(
        r"""() => ({
            xssSearch: window.__XSS_SEARCH || null,
            xssType: window.__XSS_TYPE || null,
            imgCount: document.querySelectorAll('#find-res img').length,
            resHtml: (document.getElementById('find-res') || {}).innerHTML.slice(0, 300),
        })"""
    )
    check(not st["xssSearch"] and not st["xssType"],
          f"XSS EXECUTED via #find-res search sink (search={st['xssSearch']}, type={st['xssType']})", st)
    check(st["imgCount"] == 0, f"Unescaped <img> injected into #find-res (count={st['imgCount']})", st)

    # Also verify legitimate UI SVG & water/hydrogen quantum card still render properly
    pg.evaluate("__U.openPanel(null); __U.goStop(__U.STOPS[11], true);")
    session.pw.wait_frames(pg, n=2, min_ms=140)
    pg.evaluate("() => { const m = document.getElementById('card-more'); if (m && !m.hidden) m.click(); }")
    pg.wait_for_timeout(120)
    svg_info = pg.evaluate(
        r"""() => ({
            uiSvgs: document.querySelectorAll('footer svg').length,
            cardSvgs: document.querySelectorAll('#card-dl svg').length,
            cardHidden: document.getElementById('card').hidden,
        })"""
    )
    check(svg_info["uiSvgs"] >= 3, f"Legitimate UI SVGs missing: {svg_info}")
    check(not svg_info["cardHidden"] and svg_info["cardSvgs"] >= 1,
          f"Legitimate quantum orbital SVG in H2O card missing/broken: {svg_info}")
    check(len(errs) == err_start, f"Unexpected pageerrors: {errs[err_start:]}")
    return f"Search XSS blocked (0 injected <img>) & legitimate SVGs intact (cardSvgs={svg_info['cardSvgs']})", svg_info


def t1_f4_06_no_404_fetch_storm_fusi(session: E2ESession) -> Tuple[str, dict]:
    base_url = session.server.start()
    fusc_url = f"{base_url}/mock/fusion_centres.json"
    fusi_404 = f"{base_url}/mock/404/fusion_images_missing.json"
    init_js = (
        "window.__TIER=0; window.__NOADAPT=true; window.__TILES_ON=true; window.__TILES=[]; window.__PHOTOS=[]; "
        f"window.__FUSC='{fusc_url}'; window.__FUSI='{fusi_404}'; "
        f"window.__ASSETS={{ fusc: '{fusc_url}', fusi: '{fusi_404}' }};"
    )
    snap = session.server.snapshot_log()
    with session.pw.open_isolated_page(init_script=init_js) as (pg, errs, _):
        # Wait until fusion_centres.json is loaded and S.orbit.fus === true & S.tOn != null
        pg.wait_for_function("window.__U.S.orbit && window.__U.S.orbit.fus && window.__U.S.tOn !== null", polling=200, timeout=30000)
        # Enter pre-encounter window [tOn - 0.5, tOn) to exercise fusiStart() cleanly without 30k-particle fallback stall
        pg.evaluate("window.__U.setTime((window.__U.S.tOn - 0.3) * 1e9);")
        session.pw.wait_frames(pg, n=8, min_ms=450)
        reqs = session.server.requests_since(snap)
        fusi_hits = [r for r in reqs if "/mock/404/fusion_images_missing.json" in r[1]]
        check(len(errs) == 0, f"Unexpected pageerrors during 404 check: {errs}")
        check(len(fusi_hits) <= 2,
              f"404 fetch storm detected on FUSI_URL: {len(fusi_hits)} requests in 8 frames (max allowed: 2)",
              {"fusi_requests": len(fusi_hits)})
        return f"Zero FUSI_URL 404 storm ({len(fusi_hits)} request(s) across 8 frames)", {"fusi_requests": len(fusi_hits)}


def get_tests() -> List[TestCase]:
    return [
        TestCase("T1-F4-01", 1, ["F4"], "Three.js 0.149.0 SRI, crossorigin & referrerpolicy attributes", t1_f4_01_threejs_sri_cors),
        TestCase("T1-F4-02", 1, ["F4"], "Offline CDN-blocked graceful failure with French notice & 0 pageerrors", t1_f4_02_offline_cdn_blocked_graceful),
        TestCase("T1-F4-03", 1, ["F4"], "Missing optional /_blob/* assets at t=0 boot cleanly with 0 pageerrors", t1_f4_03_missing_optional_blobs),
        TestCase("T1-F4-04", 1, ["F4"], "OpenNGC card constellation XSS injection blocked", t1_f4_04_xss_openngc_card_blocked, expected_milestone="M2"),
        TestCase("T1-F4-05", 1, ["F4"], "Search/rank XSS sinks escaped while preserving legitimate quantum SVGs", t1_f4_05_xss_search_and_svg_preserved, expected_milestone="M2"),
        TestCase("T1-F4-06", 1, ["F4"], "Zero 404 fetch storm on merger FUSI_URL across 12 animation frames", t1_f4_06_no_404_fetch_storm_fusi, expected_milestone="M2"),
    ]
