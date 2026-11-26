"""Tier 3 — Cross-Feature Pairwise Interaction Tests (14 tests: T3-CF-01..14)."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import struct
from typing import List, Tuple

from lib.harness import (
    APP_GEN,
    APP_SRC,
    APP_TEST,
    PIPELINE_DIR,
    REPO_ROOT,
    WORKFLOWS_DIR,
    E2ESession,
    TestCase,
    check,
    node_eval_json,
    run_cmd,
    scan_js_slash_slash_hazards,
    yaml_load,
)
from tier1_f1_build_truth import GEN_BUILD_ORDER
from tier1_f2_physics import _NODE_LOAD_PHYSICS_PREAMBLE


def t3_cf_01_built_html_physics_parity(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    js = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    const R = JSON.parse(fs.readFileSync(process.env.E2E_REF_DE440, 'utf8'));
    const TR = JSON.parse(fs.readFileSync(process.env.E2E_REF_TRANSITS, 'utf8'));
    const norm = v => Math.hypot(v[0], v[1], v[2]);
    const sep = (a, b) => Math.acos(Math.max(-1, Math.min(1, (a[0]*b[0]+a[1]*b[1]+a[2]*b[2]) / (norm(a)*norm(b))))) / ctx.DEG * 3600;
    let worstPlanet = 0, worstMoon = 0;
    R.T.forEach((T, i) => {
      const st = ctx.solarSystemAt(T, null, 0);
      for (const k of ['mercury', 'venus', 'earth', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune']) {
        const p = k === 'earth' ? st.earth : st.planets[k].pos;
        worstPlanet = Math.max(worstPlanet, sep(p, R.ref[k][i]));
      }
      worstMoon = Math.max(worstMoon, sep(st.moonGeo, R.ref.moon[i]));
    });
    const C = ctx.buildCosmo(ctx.PLANCK);
    const age = -C.tBang;
    const jdOf = (d, hm) => { const [y, m, dd] = d.split('-').map(Number), [h, mi] = hm.split(':').map(Number); return Date.UTC(y, m - 1, dd, h, mi) / 864e5 + 2440587.5; };
    const t0 = Date.now();
    const merc = ctx.evTransits('mercury', jdOf('2026-01-01', '00:00'), jdOf('2200-12-31', '00:00'));
    const ven = ctx.evTransits('venus', jdOf('2026-01-01', '00:00'), jdOf('2200-12-31', '00:00'));
    const transitMs = Date.now() - t0;
    let maxDm = 0;
    for (const [calc, ref] of [[merc, TR.mercury], [ven, TR.venus]]) {
      for (const r of ref) {
        const j = jdOf(r.date, r.greatest_ut);
        const h = calc.find(x => Math.abs(x.jd - j) < 1);
        maxDm = Math.max(maxDm, h ? Math.abs((h.jd - j) * 1440) : 999);
      }
    }
    const dataTransitsM = (ctx.DATA.TRANSITS && ctx.DATA.TRANSITS.mercury || []).length;
    const dataTransitsV = (ctx.DATA.TRANSITS && ctx.DATA.TRANSITS.venus || []).length;
    console.log(JSON.stringify({
      worstPlanet, worstMoon, age,
      mercCount: merc.length, refMerc: TR.mercury.length,
      venCount: ven.length, refVen: TR.venus.length,
      maxDm, transitMs, dataTransitsM, dataTransitsV,
    }));
    """
    nres, info = node_eval_json(
        js,
        timeout=20.0,
        env={
            "E2E_HTML": str(html_path),
            "E2E_SRC_DIR": str(APP_SRC),
            "E2E_REF_DE440": str(APP_TEST / "ref_de440.json"),
            "E2E_REF_TRANSITS": str(APP_TEST / "transits_ref.json"),
        },
    )
    check(not nres.timed_out, "Built HTML physics parity timed out at 20s (evTransits 175y unoptimized; WEB-PERF-01)")
    check(nres.rc == 0 and info is not None, f"Built HTML physics parity failed: {nres.stderr[:300]}")
    check(info["worstPlanet"] <= 2.5 and info["worstMoon"] <= 7.5, f"DE440 error exceeded: {info}")
    check(abs(info["age"] - 13.79) <= 0.05, f"Planck age out of range: {info['age']}")
    check(info["mercCount"] == info["refMerc"] and info["venCount"] == info["refVen"] and info["maxDm"] <= 3.0,
          f"Transit mismatch: {info}")
    return (
        f"Built HTML physics PASS: planets<={info['worstPlanet']:.2f}\", Moon<={info['worstMoon']:.2f}\", "
        f"age={info['age']:.3f} Ga, transits {info['mercCount']}+{info['venCount']} ({info['transitMs']} ms)",
        info,
    )


def t3_cf_02_temp_build_boot_and_live_truth(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()
    boot = pg.evaluate("() => ({ frame: __U.frame(), hdr: !!__U.Rr.hdr, evl: __U.EVL.length })")
    check(boot["frame"] > 2 and boot["hdr"] and boot["evl"] == 738, f"Boot invariant mismatch: {boot}")

    # Live truth DOM across T_DIV, SYS_END, LMICRO
    pg.evaluate("__U.goTo(11.5, { focus: 'sun', instant: true }); __U.setTime((__U.T_DIV + 0.05) * 1e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    n1 = pg.evaluate("document.getElementById('notice').textContent")
    check("Sort de la Terre inconnu" in n1, f"Missing T_DIV live notice: {n1!r}")

    pg.evaluate("__U.setTime((__U.SYS_END + 1.0) * 1e9);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    n2 = pg.evaluate("document.getElementById('notice').textContent")
    check("Inconnu" in n2 and "Zink" in n2, f"Missing SYS_END live notice: {n2!r}")

    pg.evaluate("__U.setTime(0); __U.goTo(-20.0, { focus: 'earth', instant: true }); __U.S.logR = -20.0;")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    n3 = pg.evaluate("() => ({ place: document.getElementById('place').textContent, notice: document.getElementById('notice').textContent })")
    check(n3["place"] == "Inconnu" and "Inconnu" in n3["notice"], f"Missing LMICRO live notice: {n3}")

    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors: {errs[err_idx:]}")
    return f"Fresh temp build -> WebGL2 HDR boot (EVL={boot['evl']}) & all 3 live truth notices PASS", boot


def t3_cf_03_built_bundle_xss_immunity(session: E2ESession) -> Tuple[str, dict]:
    pg, errs = session.pw.get_evil_ngc_page()
    err_start = len(errs)
    pg.evaluate("window.__U.select(null); window.__U.openPanel(null); document.getElementById('b-find').click();")
    pg.wait_for_function(
        """() => {
            window.__U.findRun('NGC 999901');
            return [...document.querySelectorAll('#find-res button')].some(b => b.textContent.includes('999901'));
        }""",
        polling=100,
        timeout=25000,
    )
    pg.evaluate("[...document.querySelectorAll('#find-res button')].find(b => b.textContent.includes('999901')).click();")
    pg.wait_for_function("!document.getElementById('card').hidden", polling=100, timeout=20000)
    pg.evaluate("window.__U.findRun('NGC 999902');")
    pg.wait_for_timeout(350)
    st = pg.evaluate(
        r"""() => ({
            xssCard: window.__XSS_CARD || null,
            xssSearch: window.__XSS_SEARCH || null,
            xssType: window.__XSS_TYPE || null,
            evilImgs: document.querySelectorAll('img[onerror], #card-dl img, #find-res img').length,
        })"""
    )
    check(not st["xssCard"] and not st["xssSearch"] and not st["xssType"],
          f"XSS executed in built bundle under untrusted OpenNGC feed: {st}", st)
    check(st["evilImgs"] == 0, f"Injected <img> DOM elements found ({st['evilImgs']})", st)
    check(len(errs) == err_start, f"Unexpected pageerrors: {errs[err_start:]}")
    return "Built bundle immune to untrusted OpenNGC search & card XSS (0 execution, 0 injected nodes)", st


def t3_cf_04_orbit_clock_cap_vs_pause_physics(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()
    # Engage high speed in Solar System -> S.solOff must become non-zero & slow-motion notice shown (CLAUDE.md:23)
    pg.evaluate("window.__U.goStop(window.__U.STOPS[1], true); window.__U.setSpeed(1e12); window.__U.S.playing = true;")
    session.pw.wait_frames(pg, n=5, min_ms=280)
    fast_st = pg.evaluate(
        r"""() => ({
            solOff: window.__U.S.solOff || 0,
            notice: (document.getElementById('notice') || {}).textContent || '',
            noticeHidden: !!(document.getElementById('notice') || {}).hidden,
        })"""
    )
    check(abs(fast_st["solOff"]) > 0, f"High speed (1e12 s/s) did not activate display clock cap S.solOff: {fast_st}")
    check(not fast_st["noticeHidden"] and len(fast_st["notice"]) > 10, f"Display clock cap notice missing: {fast_st}")

    # Pause -> S.solOff resets to 0 and Earth/Moon match true physics (< 1e-6 AU)
    pg.evaluate("window.__U.S.playing = false;")
    session.pw.wait_frames(pg, n=2, min_ms=140)
    paused = pg.evaluate(
        r"""() => ({
            solOff: window.__U.S.solOff || 0,
            ty: window.__U.S.ty,
            jd: window.__U.F.jd,
            earth: window.__U.F.sol.earth.slice(),
            moonGeo: window.__U.F.sol.moonGeo.slice(),
        })"""
    )
    check(paused["solOff"] == 0, f"S.solOff did not reset to 0 on pause: {paused['solOff']}")

    # Compare paused live Earth/Moon against exact Node F2 solarSystemAt(T)
    html_path = session.workspace.build_temp_html()
    verify_js = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    const P = JSON.parse(process.env.E2E_PAUSED);
    const T = (P.jd - ctx.JD_J2000) / 36525;
    const st = ctx.solarSystemAt(T);
    const dEarth = Math.hypot(st.earth[0]-P.earth[0], st.earth[1]-P.earth[1], st.earth[2]-P.earth[2]);
    const dMoon = Math.hypot(st.moonGeo[0]-P.moonGeo[0], st.moonGeo[1]-P.moonGeo[1], st.moonGeo[2]-P.moonGeo[2]);
    console.log(JSON.stringify({ dEarth, dMoon }));
    """
    nres, diff = node_eval_json(
        verify_js,
        timeout=20.0,
        env={"E2E_HTML": str(html_path), "E2E_SRC_DIR": str(APP_SRC), "E2E_PAUSED": json.dumps(paused)},
    )
    check(nres.rc == 0 and diff is not None, f"F2 reference check failed: {nres.stderr[:250]}")
    check(diff["dEarth"] < 1e-6 and diff["dMoon"] < 1e-6, f"Paused Earth/Moon diverged from F2 physics: {diff}")
    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors: {errs[err_idx:]}")
    return f"Clock cap active at 1e12 s/s (solOff={fast_st['solOff']:.1f}y) & exact F2 parity on pause (dE={diff['dEarth']:.1e} AU)", diff


def t3_cf_05_lightcone_and_dark_matter_interaction(session: E2ESession) -> Tuple[str, dict]:
    pg, err_idx = session.pw.reset_warm_page()
    # Cosmic Web STOPS[7], enable lightcone #c-lc
    pg.evaluate(
        r"""() => {
            window.__U.goStop(window.__U.STOPS[7], true);
            const lc = document.getElementById('c-lc');
            lc.checked = true;
            lc.dispatchEvent(new Event('change'));
        }"""
    )
    session.pw.wait_frames(pg, n=1, min_ms=130)
    prov_now = pg.evaluate("document.getElementById('prov').textContent")
    check("lumière est partie" in prov_now or "cône" in prov_now.lower(), f"#prov did not reflect lightcone at t=0: {prov_now!r}")

    # Jump to +100 Ma (1e8 yr > 50 Ma cutoff) -> lightcone auto-suspends with warning
    pg.evaluate("window.__U.setTime(1e8);")
    session.pw.wait_frames(pg, n=1, min_ms=130)
    prov_far = pg.evaluate("document.getElementById('prov').textContent")
    check("seulement autour d’aujourd’hui" in prov_far, f"Lightcone did not auto-suspend at +100 Ma: {prov_far!r}")

    # Toggle #c-dm off then back on -> S.dmMix transitions smoothly with 0 NaNs
    pg.evaluate("const dm = document.getElementById('c-dm'); dm.checked = false; dm.dispatchEvent(new Event('change'));")
    session.pw.wait_frames(pg, n=4, min_ms=250)
    dm_off = pg.evaluate("window.__U.S.dmMix")
    pg.evaluate("const dm = document.getElementById('c-dm'); dm.checked = true; dm.dispatchEvent(new Event('change'));")
    session.pw.wait_frames(pg, n=4, min_ms=250)
    dm_on = pg.evaluate("window.__U.S.dmMix")
    check(math.isfinite(dm_off) and math.isfinite(dm_on) and dm_off < 0.99 and dm_on > dm_off,
          f"S.dmMix transition unexpected: off={dm_off}, on={dm_on}")

    _, errs, _ = session.pw.get_warm_desktop_page()
    check(len(errs) == err_idx, f"Unexpected pageerrors: {errs[err_idx:]}")
    return f"Lightcone active at t=0, auto-suspended at +100 Ma; S.dmMix transitioned {dm_off:.2f} -> {dm_on:.2f}", {"dm_off": dm_off, "dm_on": dm_on}


def t3_cf_06_deep_future_merger_under_404(session: E2ESession) -> Tuple[str, dict]:
    base_url = session.server.start()
    fusc_url = f"{base_url}/mock/fusion_centres.json"
    fusi_404 = f"{base_url}/mock/404/fusion_images_cf06.json"
    init_js = (
        "window.__TIER=0; window.__NOADAPT=true; window.__TILES_ON=true; window.__TILES=[]; window.__PHOTOS=[]; "
        f"window.__FUSC='{fusc_url}'; window.__FUSI='{fusi_404}'; "
        f"window.__ASSETS={{ fusc: '{fusc_url}', fusi: '{fusi_404}' }};"
    )
    snap = session.server.snapshot_log()
    with session.pw.open_isolated_page(init_script=init_js) as (pg, errs, _):
        pg.wait_for_function("window.__U.S.orbit && window.__U.S.orbit.fus && window.__U.S.tOn !== null", polling=200, timeout=30000)
        # Jump directly into Andromeda merger (+4.8 Ga > tOn) under 404 FUSI_URL
        pg.evaluate("window.__U.goStop(window.__U.STOPS[5], true); window.__U.setTime(4.8e9);")
        session.pw.wait_frames(pg, n=9, min_ms=500)
        st = pg.evaluate(
            r"""() => {
                const d = window.__U.F.dyn;
                let allFin = false;
                if (d && d.out && d.out.length >= 6) {
                    allFin = Number.isFinite(d.out[0]) && Number.isFinite(d.out[1]) && Number.isFinite(d.out[2]);
                }
                return { hasDyn: !!d, allFin, mergeK: window.__U.F.mergeK };
            }"""
        )
        reqs = session.server.requests_since(snap)
        fusi_404_hits = [r for r in reqs if "/mock/404/fusion_images_cf06.json" in r[1]]
        check(len(errs) == 0, f"Unexpected pageerrors during +4.8 Ga merger fallback: {errs}")
        check(st["hasDyn"] and st["allFin"], f"Restricted N-body merger fallback did not activate cleanly: {st}")
        check(
            len(fusi_404_hits) <= 3,
            f"404 fetch storm during +4.8 Ga merger: {len(fusi_404_hits)} requests in 9 frames (max allowed: 3; WEB-BUG-01)",
            {"fusi_404_hits": len(fusi_404_hits), **st},
        )
        return f"Merger fallback active (F.dyn finite) with <= 3 404 requests ({len(fusi_404_hits)} hits)", {"fusi_404_hits": len(fusi_404_hits)}


def t3_cf_07_context_loss_proton_and_sessionstorage(session: E2ESession) -> Tuple[str, dict]:
    with session.pw.open_isolated_page(
        init_script="window.__TIER=0; window.__NOADAPT=true; window.__TILES_ON=true; window.__TILES=[]; window.__PHOTOS=[];"
    ) as (pg, errs, _):
        pg.evaluate("window.__U.goTo(-15.0, { focus: 'earth', instant: true }); window.__U.S.logR = -15.0;")
        session.pw.wait_frames(pg, n=1, min_ms=130)
        with pg.expect_navigation(wait_until="domcontentloaded", timeout=30000):
            pg.evaluate("window.__U.onLost();")
        pg.wait_for_function("window.__U && window.__U.frame() > 2", polling=200, timeout=150000)
        session.pw.wait_frames(pg, n=1, min_ms=130)
        st = pg.evaluate(
            r"""() => ({
                resumed: !!window.__U.S.resumed,
                logR: window.__U.S.logR,
                reprise: sessionStorage.getItem('univers-reprise'),
            })"""
        )
        issues: List[str] = []
        if not st["resumed"]:
            issues.append("S.resumed is false after onLost reload")
        if abs(st["logR"] - (-15.0)) > 0.2:
            issues.append(f"Proton micro-scale lost on reload: logR={st['logR']:.2f} (expected -15.0; WEB-BUG-06)")
        if st["reprise"] is not None:
            issues.append(f"sessionStorage['univers-reprise'] not cleared after resume: {st['reprise']!r}")
        if errs:
            issues.append(f"pageerrors: {errs}")
        check(not issues, "; ".join(issues), st)
        return f"onLost recovery at Proton preserved logR={st['logR']:.2f} & cleared sessionStorage", st


def t3_cf_08_offline_blocked_and_local_proxy_boot(session: E2ESession) -> Tuple[str, dict]:
    # (a) Block all external URLs incl. cdnjs -> graceful French error, 0 pageerrors
    with session.pw.open_isolated_page(
        block_cdnjs=True, proxy_three_local=False, block_all_external=True, wait_ready=False
    ) as (pg, errs_a, _):
        pg.wait_for_function(
            "() => { const h = document.querySelector('#loader h2'); return h && h.textContent.includes('impossible'); }",
            polling=100,
            timeout=30000,
        )
        h2 = pg.evaluate("document.querySelector('#loader h2').textContent.trim()")
        check(len(errs_a) == 0 and h2 == "Affichage impossible", f"Offline part (a) failed: h2={h2!r}, errs={errs_a}")

    # (b) Proxy ONLY Three.js via local cache while blocking all other external origins + 404 on /_blob/*
    with session.pw.open_isolated_page(
        block_cdnjs=False, proxy_three_local=True, block_all_external=True, wait_ready=True
    ) as (pg, errs_b, _):
        pg.evaluate("window.__U.openPanel('view');")
        session.pw.wait_frames(pg, n=2, min_ms=150)
        st = pg.evaluate("() => ({ frame: window.__U.frame(), viewOpen: !document.getElementById('p-view').hidden })")
        check(len(errs_b) == 0 and st["frame"] > 2 and st["viewOpen"], f"Local-proxy part (b) failed: {st}, errs={errs_b}")
    return "Blocked CDN -> 'Affichage impossible' (0 errors); local Three.js proxy -> full WebGL2 boot + panels PASS", {}


def t3_cf_09_cross_language_js_cpp_parity(session: E2ESession) -> Tuple[str, dict]:
    # 1. Live quantitative C++20 vs Web JS parity (galaxie_orbites, cosmologie, nbody_noyau)
    drv = session.cpp.build_parity_driver()
    check(drv.ok and "parity_driver" in drv.binaries, f"Failed to compile parity_driver: {drv.stderr[:300]}")
    r_cpp = run_cmd([str(drv.binaries["parity_driver"])], timeout=30.0)
    check(r_cpp.rc == 0, f"parity_driver failed: {r_cpp.stderr[:300]}")
    cpp = json.loads(r_cpp.stdout.strip().splitlines()[-1])

    html_path = session.workspace.build_temp_html()
    js_code = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    // 1. Galactic Sun +200 Ma (bar ON & OFF)
    const sun0 = ctx.DATA.SGRA_GAL.map(x => -x * ctx.GAL.R0);
    const P_on = ctx.orbParams();
    const X1 = Float64Array.from(sun0), V1 = Float64Array.from(ctx.SUN_UVW);
    ctx.orbSteps(P_on, X1, V1, 1, ctx.ORB_DT, Math.round(0.2 / ctx.ORB_DT), null, 0);
    const P_off = Object.assign({}, P_on, { Ab: 0 });
    const X2 = Float64Array.from(sun0), V2 = Float64Array.from(ctx.SUN_UVW);
    ctx.orbSteps(P_off, X2, V2, 1, ctx.ORB_DT, Math.round(0.2 / ctx.ORB_DT), null, 0);

    // 2. Planck 2018 age & d_M(z) at [0.1, 0.5, 1.0, 2.0, 3.0]
    const C = ctx.buildCosmo(ctx.PLANCK);
    const age = -C.tBang;
    const zmax = ctx.DATA.SURV_ZMAX;
    const lut = ctx.surveyLutOf(C, zmax, false, 1024);
    const K = lut.length - 1, lz = Math.log(1 + zmax);
    const dmAt = z => { const x = Math.log(1 + z) / lz * K, k = Math.min(x | 0, K - 1); return lut[k] + (lut[k + 1] - lut[k]) * (x - k); };
    const dm = [0.1, 0.5, 1.0, 2.0, 3.0].map(dmAt);

    // 3. 13-body N-body at J2000 (JD 2451544.5)
    const S = ctx.nbFromData();
    const span = 2451544.5 - S.jd;
    const n = Math.ceil(Math.abs(span) / ctx.DATA.NB.dt);
    ctx.nbStep(S, span / n, n);
    const AU_KM = 149597870.7;
    const merc_km = [S.Q[0]*AU_KM, S.Q[1]*AU_KM, S.Q[2]*AU_KM];
    const jup_km = [S.Q[12]*AU_KM, S.Q[13]*AU_KM, S.Q[14]*AU_KM];
    console.log(JSON.stringify({ sun_on: [...X1], sun_off: [...X2], age, dm, merc_km, jup_km }));
    """
    nres, js = node_eval_json(js_code, timeout=30.0, env={"E2E_HTML": str(html_path), "E2E_SRC_DIR": str(APP_SRC)})
    check(nres.rc == 0 and js is not None, f"JS parity driver failed: {nres.stderr[:300]}")

    dist3 = lambda a, b: math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))
    d_on = dist3(cpp["sun_on"], js["sun_on"])
    d_off = dist3(cpp["sun_off"], js["sun_off"])
    d_age = abs(cpp["age"] - js["age"])
    max_dm_rel = max(abs(cpp["dm"][i] - js["dm"][i]) / cpp["dm"][i] for i in range(5))
    d_merc = dist3(cpp["merc_km"], js["merc_km"])
    d_jup = dist3(cpp["jup_km"], js["jup_km"])

    metrics = {
        "gal_on_kpc": d_on, "gal_off_kpc": d_off, "age_diff_gyr": d_age,
        "dm_max_rel": max_dm_rel, "nbody_merc_km": d_merc, "nbody_jup_km": d_jup,
    }
    check(d_on < 1e-6 and d_off < 1e-6, f"Galactic orbit JS<->C++ diverged: {metrics}")
    check(d_age < 0.01 and max_dm_rel < 1e-3, f"Cosmology JS<->C++ diverged: {metrics}")
    check(d_merc < 1.0 and d_jup < 1.0, f"13-body N-body JS<->C++ diverged: {metrics}")

    # 2. Also verify portable CMake natif/physique essai_systeme_solaire --noyau passes alongside Node nbody.test.js
    phys_art = session.cpp.build_cmake_phys_gcc()
    check(
        phys_art.ok and "essai_systeme_solaire" in phys_art.binaries,
        f"Live parity PASS (gal={d_on:.1e} kpc, dm={max_dm_rel:.1e}, nb={d_merc:.1e} km), "
        f"but CMake natif/physique build failed (M4): {(phys_art.stderr or '')[:220]}",
        metrics,
    )
    r_ss = run_cmd([str(phys_art.binaries["essai_systeme_solaire"]), "--noyau"], timeout=30.0)
    check(r_ss.rc == 0, f"essai_systeme_solaire --noyau failed (rc={r_ss.rc}): {r_ss.stdout[:250]}")
    r_nb = run_cmd(["node", str(APP_TEST / "nbody.test.js")], cwd=REPO_ROOT, timeout=30.0)
    check(r_nb.rc == 0, f"nbody.test.js failed (rc={r_nb.rc})")
    return (
        f"JS<->C++20 parity PASS (gal={d_on:.1e} kpc, d_M={max_dm_rel:.2e}, nb={d_merc:.2e} km) & CMake --noyau + nbody.test.js PASS",
        metrics,
    )


def t3_cf_10_clean_gen_dead_keys_and_bundle(session: E2ESession) -> Tuple[str, dict]:
    cleaner = PIPELINE_DIR / "clean_gen_dead_keys.py"
    check(cleaner.is_file(), "Missing pipeline/clean_gen_dead_keys.py (M3 deliverable)")
    r_chk = run_cmd(["python3", str(cleaner), "--check"], timeout=45.0)
    check(not r_chk.timed_out and r_chk.rc == 0,
          f"pipeline/clean_gen_dead_keys.py --check failed (rc={r_chk.rc}): {(r_chk.stderr or r_chk.stdout)[:300]}")

    # Verify built temp HTML has zero overwritten DATA/TEX keys via Proxy
    from tier2_f1_build_truth import t2_f1_01_zero_dead_overwritten_data
    msg, details = t2_f1_01_zero_dead_overwritten_data(session)
    return f"clean_gen_dead_keys.py --check PASS & {msg}", details


def t3_cf_11_tile_manifest_live_and_split_converters(session: E2ESession) -> Tuple[str, dict]:
    # 1. Verify real repo app/src/6*.js contains /*__TILES__*/ with exact 10 tiles (6 star, 3 gal, 1 ast + names)
    src_6 = "\n".join(p.read_text(encoding="utf-8") for p in sorted(APP_SRC.glob("6*.js")))
    m = re.search(r"TILE_MANIFEST\s*=\s*/\*__TILES__\*/\s*(\[.*?\])\s*;", src_6, re.S)
    check(m is not None, "Could not locate TILE_MANIFEST = /*__TILES__*/[...] across app/src/6*.js")
    man = m.group(1)
    n_star = len(re.findall(r"kind\s*:\s*['\"]star['\"]", man))
    n_gal = len(re.findall(r"kind\s*:\s*['\"]gal['\"]", man))
    n_ast = len(re.findall(r"kind\s*:\s*['\"]ast['\"]", man))
    check(n_star == 6 and n_gal == 3 and n_ast == 1, f"Unexpected live TILE_MANIFEST counts: star={n_star}, gal={n_gal}, ast={n_ast}")

    # 2. Verify pipeline/natif/{etoiles,asteroides,galaxies}.py handle split & Prettier multi-line fixtures
    from tier2_f6_pipeline import t2_f6_01_tile_manifest_multiline_split_resilience
    msg, details = t2_f6_01_tile_manifest_multiline_split_resilience(session)
    return f"Live TILE_MANIFEST (6 star, 3 gal, 1 ast) verified & {msg}", details


def t3_cf_12_fusion_bin_to_cpp_rejeu_roundtrip(session: E2ESession) -> Tuple[str, dict]:
    tmp = session.workspace.subdir("t3_cf_12")
    # 1. Build synthetic 3-frame fusion.json + kf_000.bin and run fusion_bin.py -> C++ ASan Rejeu::charger()
    fusion_dir = tmp / "run"
    fusion_dir.mkdir(parents=True, exist_ok=True)
    # 4 stars total (mw=2, m31=2, m33=0, lmc=0), 3 frames (t = 0.0, 0.02, 0.04 Ga), quantum = 0.025 kpc
    n_frames, n_stars = 3, 4
    kf_vals = []
    for fr in range(n_frames):
        for s in range(n_stars):
            # Simple linear motion: star 0 x = 40*fr -> 1.0 kpc * fr
            kf_vals.extend([40 * fr + s * 10, 0, 0])
    (fusion_dir / "kf_000.bin").write_bytes(struct.pack(f"<{len(kf_vals)}h", *kf_vals))
    meta = {
        "t": [0.0, 0.02, 0.04],
        "traceurs": ["sun"],
        "quantum_kpc": 0.025,
        "fusion_ga": 5.44,
        "derive_max": 0.0011,
        "affichees": [2, 2, 0, 0],
        "centres": [
            [[0.0, 0.0, 0.0], [-385.352, 623.003, -287.592], [0.0, 0.0, 0.0], [-1.0, -41.0, -27.8]],
            [[2.0, 0.0, 0.0], [-383.352, 623.003, -287.592], [0.0, 0.0, 0.0], [1.0, -41.0, -27.8]],
            [[4.0, 0.0, 0.0], [-381.352, 623.003, -287.592], [0.0, 0.0, 0.0], [3.0, -41.0, -27.8]],
        ],
        "traceurs_pos": [[[0, 0, 0]], [[1, 0, 0]], [[2, 0, 0]]],
        "fichiers": [["kf_000.bin", n_frames]],
    }
    (fusion_dir / "fusion.json").write_text(json.dumps(meta), encoding="utf-8")
    out_bin = tmp / "centres.bin"
    r_py = run_cmd(["python3", str(PIPELINE_DIR / "natif" / "fusion_bin.py"), str(fusion_dir), str(out_bin)], timeout=15.0)
    check(r_py.rc == 0 and out_bin.is_file(), f"fusion_bin.py failed on valid 3-frame input: {r_py.stderr[:250]}")

    art = session.cpp.build_asan_probe()
    check(art.ok and "asan_probe" in art.binaries, f"Failed to build ASan probe: {art.stderr[:300]}")
    r_rt = run_cmd([str(art.binaries["asan_probe"]), "--mode", "rejeu_rt", str(out_bin), str(fusion_dir)], timeout=15.0)
    check(r_rt.rc == 0 and "AddressSanitizer" not in r_rt.stderr and "runtime error:" not in r_rt.stderr,
          f"ASan/UBSan failed on Rejeu round-trip: {r_rt.stderr[:300]}")
    rt = json.loads(r_rt.stdout.strip().splitlines()[-1])
    check(rt["ok"] and rt["ok0"] and rt["ok_lmc"] and rt["ok_mid"] and rt["ok_st"], f"Rejeu round-trip read failed: {rt}")
    check(not rt["bad_lo"] and not rt["bad_hi"], f"Rejeu must return false ('inconnu') out of range: {rt}")
    check(abs(rt["m31_0"][0] - (-385.352)) < 1e-4 and abs(rt["m31_mid"][0] - (-385.352)) < 1e-4, f"M31 relative pos mismatch: {rt}")
    check(abs(rt["s0x"] - (-0.5)) < 1e-3, f"Interpolated star 0 x expected -0.5 kpc (0.5 - MW 1.0), got {rt['s0x']}")

    # 2. Enforce BOTH negative contracts: fusion_bin.py >16-byte rejection (M5) AND essai_fusion truncated non-crash (M4)
    from tier2_f6_pipeline import t2_f6_04_fusion_bin_16byte_validation
    from tier2_f5_native_cpp import t2_f5_01_essai_fusion_malformed_cli_no_crash
    t2_f6_04_fusion_bin_16byte_validation(session)
    t2_f5_01_essai_fusion_malformed_cli_no_crash(session)
    return "fusion_bin.py -> C++20 ASan Rejeu round-trip, >16B rejection & essai_fusion bounds safety PASS", rt


def t3_cf_13_ci_gate_vs_live_build_lint_doc(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []
    ctrl = yaml_load(WORKFLOWS_DIR / "controles.yml")
    all_runs = "\n".join(
        str(step.get("run", ""))
        for job in (ctrl.get("jobs") or {}).values()
        if isinstance(job, dict)
        for step in (job.get("steps") or [])
        if isinstance(step, dict)
    )
    for tok in ("app/build.py", "FATE_P", "eslint", "prettier"):
        if tok not in all_runs:
            issues.append(f"controles.yml missing live F1 gate '{tok}'")

    # Cross-check live build, lint, // guard & doc constant parity
    for fn in (
        "t1_f1_06_static_quality_gates",
        "t2_f7_03_dynamic_cross_file_constant_parity",
    ):
        pass
    from tier1_f1_build_truth import t1_f1_06_static_quality_gates
    from tier2_f7_ci_infra_docs import t2_f7_03_dynamic_cross_file_constant_parity
    for sub in (t1_f1_06_static_quality_gates, t2_f7_03_dynamic_cross_file_constant_parity):
        try:
            sub(session)
        except Exception as exc:
            issues.append(str(exc))

    check(not issues, "; ".join(issues[:6]), {"issues": issues})
    return "CI controles.yml gates match live build, ESLint, Prettier, // lexer & cross-doc constant parity", {}


def t3_cf_14_multistack_ci_execution_parity(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []
    ctrl = yaml_load(WORKFLOWS_DIR / "controles.yml")
    all_runs = "\n".join(
        str(step.get("run", ""))
        for job in (ctrl.get("jobs") or {}).values()
        if isinstance(job, dict)
        for step in (job.get("steps") or [])
        if isinstance(step, dict)
    )
    if "cmake" not in all_runs.lower():
        issues.append("controles.yml missing Linux C++20 CMake job")
    if "test_build_gw.py" not in all_runs and "test_pipeline_stdlib.py" not in all_runs:
        issues.append("controles.yml missing Python stdlib pipeline job")

    # Execute actual C++20 CMake builds + Valgrind + Python stdlib tests locally in temp workspace
    from tier1_f5_native_cpp import (
        t1_f5_01_cmake_physique_gcc,
        t1_f5_02_cmake_natif_linux_portable,
        t1_f5_04_essai_cosmologie_valgrind,
        t1_f5_05_essai_interface_valgrind,
    )
    from tier1_f6_pipeline import t1_f6_02_test_build_gw_stdlib, t1_f6_03_test_pipeline_stdlib

    for sub in (
        t1_f5_01_cmake_physique_gcc,
        t1_f5_02_cmake_natif_linux_portable,
        t1_f5_04_essai_cosmologie_valgrind,
        t1_f5_05_essai_interface_valgrind,
        t1_f6_02_test_build_gw_stdlib,
        t1_f6_03_test_pipeline_stdlib,
    ):
        try:
            sub(session)
        except Exception as exc:
            issues.append(str(exc)[:180])

    check(not issues, "; ".join(issues[:6]), {"issues": issues})
    return "Multi-stack CI parity PASS: controles.yml + local CMake C++20 (-Werror) + Valgrind + Python stdlib tests", {}


def get_tests() -> List[TestCase]:
    return [
        TestCase("T3-CF-01", 3, ["F1", "F2"], "Built HTML physics parity (DE440, Planck age & 175y transits)", t3_cf_01_built_html_physics_parity, expected_milestone="M2"),
        TestCase("T3-CF-02", 3, ["F1", "F3"], "Fresh temp build -> WebGL2 HDR boot & live scientific truth DOM", t3_cf_02_temp_build_boot_and_live_truth),
        TestCase("T3-CF-03", 3, ["F1", "F4"], "Built bundle XSS immunity under untrusted OpenNGC search/card feed", t3_cf_03_built_bundle_xss_immunity, expected_milestone="M2"),
        TestCase("T3-CF-04", 3, ["F2", "F3"], "High-speed display clock cap (S.solOff) vs exact F2 physics on pause", t3_cf_04_orbit_clock_cap_vs_pause_physics),
        TestCase("T3-CF-05", 3, ["F2", "F3"], "Cosmology lightcone (#c-lc) auto-suspend & dark-matter (#c-dm) live interaction", t3_cf_05_lightcone_and_dark_matter_interaction),
        TestCase("T3-CF-06", 3, ["F2", "F4"], "Deep-future merger (+4.8 Ga) restricted fallback under 404 assets (zero storm)", t3_cf_06_deep_future_merger_under_404, expected_milestone="M2"),
        TestCase("T3-CF-07", 3, ["F3", "F4"], "WebGL context-loss recovery (onLost) at Proton (-15) & sessionStorage hygiene", t3_cf_07_context_loss_proton_and_sessionstorage, expected_milestone="M2"),
        TestCase("T3-CF-08", 3, ["F3", "F4"], "Offline CDN-blocked failure & local Three.js proxy full WebGL2 boot", t3_cf_08_offline_blocked_and_local_proxy_boot),
        TestCase("T3-CF-09", 3, ["F2", "F5"], "Cross-language physics parity (Web JS <-> Native C++20 + CMake --noyau)", t3_cf_09_cross_language_js_cpp_parity, expected_milestone="M4"),
        TestCase("T3-CF-10", 3, ["F1", "F6"], "Pipeline dead-key pruner (clean_gen_dead_keys.py) <-> Web bundle DATA proxy", t3_cf_10_clean_gen_dead_keys_and_bundle, expected_milestone="M3"),
        TestCase("T3-CF-11", 3, ["F1", "F6"], "Live & split/Prettier TILE_MANIFEST resilience <-> native pipeline converters", t3_cf_11_tile_manifest_live_and_split_converters, expected_milestone="M5"),
        TestCase("T3-CF-12", 3, ["F5", "F6"], "Pipeline fusion_bin.py writer <-> C++20 ASan Rejeu round-trip & bounds safety", t3_cf_12_fusion_bin_to_cpp_rejeu_roundtrip, expected_milestone="M4/M5"),
        TestCase("T3-CF-13", 3, ["F1", "F7"], "CI controles.yml gates <-> live build, ESLint, Prettier, // & doc parity", t3_cf_13_ci_gate_vs_live_build_lint_doc, expected_milestone="M3/M6"),
        TestCase("T3-CF-14", 3, ["F5", "F6", "F7"], "Multi-stack CI execution parity (C++20 CMake + Valgrind + Python stdlib)", t3_cf_14_multistack_ci_execution_parity, expected_milestone="M4/M5/M6"),
    ]
