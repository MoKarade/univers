"""Tier 2 — F2: Physics Boundary Cases, Numerical Safety & Speed SLAs (7 tests)."""
from __future__ import annotations

from typing import List, Tuple

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
from tier1_f2_physics import _NODE_LOAD_PHYSICS_PREAMBLE


def t2_f2_01_extreme_cosmic_times_finite(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    js = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    const C = ctx.buildCosmo(ctx.PLANCK);
    const times = [-13.8, -13.78, 0, 10, 100];
    const bad = [];
    for (const tG of times) {
      const c = ctx.cosmoAt(C, tG);
      for (const k of ['a', 'v', 'D', 'H', 'Hkms', 'fr', 'fm', 'fde']) {
        if (!Number.isFinite(c[k])) bad.push(`cosmoAt(${tG}).${k}=${c[k]}`);
      }
      const s = ctx.sunState(tG);
      for (const k of ['L', 'T', 'R', 'M']) {
        if (!Number.isFinite(s[k])) bad.push(`sunState(${tG}).${k}=${s[k]}`);
      }
    }
    console.log(JSON.stringify({ ok: bad.length === 0, bad }));
    """
    nres, info = node_eval_json(js, timeout=20.0, env={"E2E_HTML": str(html_path), "E2E_SRC_DIR": str(APP_SRC)})
    check(nres.rc == 0 and info is not None, f"Extreme time probe failed: {nres.stderr[:300]}")
    check(info["ok"], f"Non-finite values at extreme cosmic times: {info['bad']}", info)
    return "cosmoAt & sunState finite across tG ∈ {-13.8, -13.78, 0, +10, +100} Ga", {}


def t2_f2_02_sunstate_far_future_no_throw(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    js = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    const out = [];
    for (const tG of [1e9, 1e12]) {
      try {
        const s = ctx.sunState(tG);
        const fin = ['L', 'T', 'R', 'M'].every(k => Number.isFinite(s[k]) && s[k] > 0);
        out.push({ tG, threw: false, fin, phase: s.phase, L: s.L, T: s.T, R: s.R, M: s.M });
      } catch (e) {
        out.push({ tG, threw: true, err: String(e) });
      }
    }
    console.log(JSON.stringify(out));
    """
    nres, rows = node_eval_json(js, timeout=20.0, env={"E2E_HTML": str(html_path), "E2E_SRC_DIR": str(APP_SRC)})
    check(nres.rc == 0 and rows is not None, f"sunState probe failed: {nres.stderr[:300]}")
    bad = [r for r in rows if r["threw"] or not r["fin"] or r.get("phase") != "naine blanche"]
    check(not bad, f"sunState far-future defect (WEB-BUG-10): {bad}", {"rows": rows})
    return "sunState(1e9) & sunState(1e12) return finite 'naine blanche' without throwing", {"rows": rows}


def t2_f2_03_bv_extreme_temp_clamped(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    js = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    const inputs = [-0.62 / 0.92, -1.0, 5.0, NaN];
    const teffRes = inputs.map(v => ({
      v: Number.isNaN(v) ? 'NaN' : v,
      t: typeof ctx.bvToTeff === 'function' ? ctx.bvToTeff(v) : null,
    }));
    let hasBadBvTemp = false, bvTempBad = [];
    if (typeof ctx.bvTemp === 'function') {
      for (const v of inputs) {
        const r = ctx.bvTemp(v);
        if (!Number.isFinite(r) || r < 2000 || r > 50000) {
          hasBadBvTemp = true;
          bvTempBad.push({ v: Number.isNaN(v) ? 'NaN' : v, r: String(r) });
        }
      }
    }
    console.log(JSON.stringify({ teffRes, hasBadBvTemp, bvTempBad }));
    """
    nres, info = node_eval_json(js, timeout=20.0, env={"E2E_HTML": str(html_path), "E2E_SRC_DIR": str(APP_SRC)})
    check(nres.rc == 0 and info is not None, f"B-V temp probe failed: {nres.stderr[:300]}")
    bad_teff = [x for x in info["teffRes"] if x["t"] is None or not (2000 <= x["t"] <= 50000)]
    check(not bad_teff, f"bvToTeff returned out-of-range/non-finite value: {bad_teff}", info)
    check(not info["hasBadBvTemp"], f"Unclamped bvTemp still returns Infinity/negative/NaN (WEB-BUG-10): {info['bvTempBad']}", info)
    return "bvToTeff clamped in [2000, 50000] K on extreme/NaN B-V and no unclamped bvTemp bug", info


def t2_f2_04_cosmo_v0_and_evsep_opposition(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    js = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    const issues = [];
    // 1. Cosmology bounce & crunch turnaround where v === 0 (WEB-BUG-08)
    for (const [label, par] of [
      ['bounce', { H0: 67.4, Om: 0.1, OL: 1.5, w: -1 }],
      ['crunch', { H0: 67.4, Om: 3.0, OL: 0.0, w: -1 }],
    ]) {
      const C = ctx.buildCosmo(par);
      // Find index where v crosses 0 and compute exact interpolated t where v === 0
      let tZero = null;
      for (let i = 0; i < C.n - 1; i++) {
        if ((C.v[i] <= 0 && C.v[i + 1] >= 0) || (C.v[i] >= 0 && C.v[i + 1] <= 0)) {
          const dv = C.v[i + 1] - C.v[i];
          const f = dv === 0 ? 0 : -C.v[i] / dv;
          tZero = C.t[i] + f * (C.t[i + 1] - C.t[i]);
          break;
        }
      }
      if (tZero !== null) {
        const o = ctx.cosmoAt(C, tZero);
        if (!Number.isFinite(o.q)) {
          issues.push(`${label} turnaround (t=${tZero.toFixed(4)} Ga, v=${o.v}): o.q=${o.q}`);
        }
      }
    }

    // 2. evSep exact opposition dot-product rounding c = -1 - 2.2e-16 (WEB-BUG-07)
    // With e = [1, 1, 1] and p = [2, 2, 2], g = [1, 1, 1]: -(g·e)/(hypot(g)*hypot(e)) = -3 / (sqrt(3)^2) = -1.0000000000000002
    const origSolar = ctx.solarSystemAt;
    ctx.solarSystemAt = () => ({
      earth: [1, 1, 1],
      planets: { mercury: { pos: [2, 2, 2] }, venus: { pos: [2, 2, 2] } },
    });
    let oppSep = null;
    try {
      oppSep = ctx.evSep('mercury', 2461355.5, {}).sep;
    } finally {
      ctx.solarSystemAt = origSolar;
    }
    if (!Number.isFinite(oppSep)) {
      issues.push(`evSep at exact opposition returned ${oppSep} (missing Math.max(-1, ...) clamp)`);
    }
    console.log(JSON.stringify({ ok: issues.length === 0, issues, oppSep: Number.isFinite(oppSep) ? oppSep : String(oppSep) }));
    """
    nres, info = node_eval_json(js, timeout=20.0, env={"E2E_HTML": str(html_path), "E2E_SRC_DIR": str(APP_SRC)})
    check(nres.rc == 0 and info is not None, f"cosmo/evSep boundary probe failed: {nres.stderr[:300]}")
    check(info["ok"], "; ".join(info["issues"]), info)
    return f"cosmoAt turnaround v=0 finite & evSep opposition clamped (sep={info['oppSep']:.1f}\")", info


def t2_f2_05_sla_transits_175y_fast(session: E2ESession) -> Tuple[str, dict]:
    res = run_cmd(["node", str(APP_TEST / "evenements.test.js")], cwd=REPO_ROOT, timeout=15.0)
    check(
        not res.timed_out,
        f"evenements.test.js exceeded hard 15.0s timeout (SLA: < 5.0s, WEB-PERF-01)",
        {"duration_s": round(res.duration_s, 2), "timed_out": True},
    )
    check(res.rc == 0, f"evenements.test.js failed (rc={res.rc}): {(res.stderr or res.stdout)[-300:]}")
    check(
        res.duration_s < 5.0,
        f"evenements.test.js took {res.duration_s:.2f}s (SLA: < 5.0s, WEB-PERF-01)",
        {"duration_s": round(res.duration_s, 2)},
    )
    return f"evenements.test.js (175y Mercury+Venus transits) PASS in {res.duration_s:.2f}s (< 5.0s SLA)", {"duration_s": round(res.duration_s, 2)}


def t2_f2_06_sla_moons_5y_fast(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    js = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    const R = JSON.parse(fs.readFileSync(process.env.E2E_REF, 'utf8'));
    const N = ctx.MO_JUP.names, s0 = Float64Array.from(ctx.DATA.LUNES_JUP.s);
    // Find a ~5-year check date (e.g. 2021-11-10 or closest ~5y epoch in R.checks)
    const dates = Object.keys(R.checks).sort();
    const target = dates.find(d => d.startsWith('2021')) || dates.find(d => {
      const yrs = Math.abs((R.checks[d].io.jd - R.epoch.io.jd) / 365.25);
      return yrs >= 4.0 && yrs <= 6.5;
    }) || dates[0];
    const y = { jd: R.epoch.io.jd, s: Float64Array.from(s0) };
    const t0 = Date.now();
    ctx.moStepper(ctx.MO_JUP, y, R.checks[target].io.jd).run(Infinity);
    const ms = Date.now() - t0;
    const errs = {};
    let maxKm = 0;
    N.forEach((n, i) => {
      const p = R.checks[target][n].r;
      const km = Math.hypot(y.s[i * 6] - p[0], y.s[i * 6 + 1] - p[1], y.s[i * 6 + 2] - p[2]);
      errs[n] = Math.round(km);
      if (km > maxKm) maxKm = km;
    });
    console.log(JSON.stringify({ target, ms, maxKm, errs }));
    """
    nres, info = node_eval_json(
        js,
        timeout=15.0,
        env={"E2E_HTML": str(html_path), "E2E_SRC_DIR": str(APP_SRC), "E2E_REF": str(APP_TEST / "lunes_ref.json")},
    )
    check(not nres.timed_out, f"moStepper 5-year SLA timed out at 15.0s (SLA: < 4.0s, WEB-PERF-02)")
    check(nres.rc == 0 and info is not None, f"moStepper 5-year probe failed: {nres.stderr[:300]}")
    check(info["maxKm"] < 300.0, f"moStepper accuracy degraded: maxKm={info['maxKm']:.1f} km >= 300 km ({info['errs']})", info)
    check(info["ms"] < 4000.0, f"moStepper 5y ({info['target']}) took {info['ms']} ms (SLA: < 4000 ms, WEB-PERF-02)", info)
    return f"moStepper 5y ({info['target']}) PASS in {info['ms']} ms (< 4000 ms SLA, max err {info['maxKm']:.1f} km)", info


def t2_f2_07_sla_nbody_and_orbits_fast(session: E2ESession) -> Tuple[str, dict]:
    html_path = session.workspace.build_temp_html()
    js = _NODE_LOAD_PHYSICS_PREAMBLE + r"""
    // 1. nbStep 5,000 years (456,550 steps of dt = 4 days) < 2.2s, energy drift < 1e-7
    const Sn = ctx.nbFromData();
    const e0 = ctx.nbEnergy(Sn);
    const t0 = Date.now();
    ctx.nbStep(Sn, 4, 456550);
    const nbMs = Date.now() - t0;
    const e1 = ctx.nbEnergy(Sn);
    const drift = Math.abs((e1 - e0) / e0);

    // 2. orbSteps 10,000 stars x 500 Ma < 0.65s
    const P = ctx.orbParams();
    const N = 10000;
    const X = new Float64Array(N * 3), V = new Float64Array(N * 3);
    for (let i = 0; i < N; i++) {
      const a = (i / N) * 6.2831853, r = 3 + (i % 12);
      X[i * 3] = r * Math.cos(a); X[i * 3 + 1] = r * Math.sin(a); X[i * 3 + 2] = ((i % 7) - 3) * 0.05;
      V[i * 3] = 220 * Math.sin(a); V[i * 3 + 1] = -220 * Math.cos(a); V[i * 3 + 2] = 5;
    }
    const steps = Math.round(0.5 / ctx.ORB_DT);
    const t1 = Date.now();
    ctx.orbSteps(P, X, V, N, ctx.ORB_DT, steps);
    const orbMs = Date.now() - t1;
    console.log(JSON.stringify({ nbMs, drift, orbMs, steps }));
    """
    nres, info = node_eval_json(js, timeout=15.0, env={"E2E_HTML": str(html_path), "E2E_SRC_DIR": str(APP_SRC)})
    check(not nres.timed_out, "nbStep/orbSteps SLA timed out at 15.0s (WEB-PERF-03/04)")
    check(nres.rc == 0 and info is not None, f"nbStep/orbSteps probe failed: {nres.stderr[:300]}")
    issues = []
    if info["drift"] >= 1e-7:
        issues.append(f"nbStep 5000y energy drift {info['drift']:.2e} >= 1e-7")
    if info["nbMs"] >= 2200:
        issues.append(f"nbStep 5000y took {info['nbMs']} ms (SLA: < 2200 ms, WEB-PERF-03)")
    if info["orbMs"] >= 650:
        issues.append(f"orbSteps 10k×500Ma took {info['orbMs']} ms (SLA: < 650 ms, WEB-PERF-04)")
    check(not issues, "; ".join(issues), info)
    return f"nbStep 5000y={info['nbMs']} ms (drift {info['drift']:.1e}) & orbSteps 10k×500Ma={info['orbMs']} ms PASS", info


def get_tests() -> List[TestCase]:
    return [
        TestCase("T2-F2-01", 2, ["F2"], "Extreme cosmic times (-13.8..+100 Ga) return finite cosmoAt & sunState", t2_f2_01_extreme_cosmic_times_finite),
        TestCase("T2-F2-02", 2, ["F2"], "sunState(1e9) & sunState(1e12) do not throw and return finite white dwarf", t2_f2_02_sunstate_far_future_no_throw, expected_milestone="M2"),
        TestCase("T2-F2-03", 2, ["F2"], "Extreme/NaN B-V star temperature clamped in [2000, 50000] K (no bvTemp Inf/neg)", t2_f2_03_bv_extreme_temp_clamped, expected_milestone="M2"),
        TestCase("T2-F2-04", 2, ["F2"], "cosmoAt turnaround v=0 finite q & evSep opposition [-1,1] acos clamp", t2_f2_04_cosmo_v0_and_evsep_opposition, expected_milestone="M2"),
        TestCase("T2-F2-05", 2, ["F2"], "Speed SLA: evenements.test.js (175y transits) exits 0 in < 5.0 s", t2_f2_05_sla_transits_175y_fast, expected_milestone="M2"),
        TestCase("T2-F2-06", 2, ["F2"], "Speed SLA: moStepper 5-year Galilean moons < 4.0 s & < 300 km", t2_f2_06_sla_moons_5y_fast, expected_milestone="M2"),
        TestCase("T2-F2-07", 2, ["F2"], "Speed SLA: nbStep 5000y < 2.2 s & orbSteps 10k×500Ma < 0.65 s", t2_f2_07_sla_nbody_and_orbits_fast, expected_milestone="M2"),
    ]
