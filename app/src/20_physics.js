/* ============================================================================
   PHYSIQUE — aucune dépendance au DOM, testable sous Node.
   Unités internes : mètres pour les distances de scène, années juliennes pour
   le temps de simulation (0 = maintenant), Ga et Mpc pour la cosmologie.
   ============================================================================ */
const DEG = Math.PI / 180, TAU = Math.PI * 2;
const AU = 1.495978707e11, LY = 9.4607304725808e15, PC = 3.0856775814913673e16;
const KPC = PC * 1e3, MPC = PC * 1e6;
const YEAR_S = 31557600, DAY_S = 86400;
const C_LIGHT = 299792458;
const C_MPC_GYR = 306.6013938;           // vitesse de la lumière en Mpc par Ga
const KMSMPC_GYR = 1.0227121650456e-3;   // 1 km/s/Mpc exprimé en Ga^-1
const KMS_KPC_RADGYR = 1.0227121650456;  // 1 km/s/kpc exprimé en rad/Ga
const JD_J2000 = 2451545.0;
const EPS_J2000 = 23.43929111 * DEG;

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const smoothstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const wrapPi = x => { x = (x + Math.PI) % TAU; if (x < 0) x += TAU; return x - Math.PI; };

/* --------------------------------------------------------------------------
   Planètes : éléments képlériens du JPL (Standish), repère écliptique J2000.
   Table 1 entre 1800 et 2050, table 2 entre -3000 et +3000. Au-delà, on fige
   la forme de l'orbite et on laisse la planète tourner : position indicative.
   -------------------------------------------------------------------------- */
const PLANET_KEYS = ['mercury', 'venus', 'emb', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune'];

/** Équation de Kepler pour les orbites très allongées (comètes) : Newton encadré, convergence garantie. */
function keplerHigh(M, e) {
  let m = M % TAU; if (m > Math.PI) m -= TAU; else if (m < -Math.PI) m += TAU; const sg = m < 0 ? -1 : 1; m = Math.abs(m);
  let lo = m, hi = Math.min(m + e, Math.PI), E = Math.min(hi, Math.max(lo, m + e * Math.sin(m) / (1 - Math.sin(m + e) + Math.sin(m))));
  for (let i = 0; i < 50; i++) { const f = E - e * Math.sin(E) - m; if (f > 0) hi = E; else lo = E; let En = E - f / (1 - e * Math.cos(E)); if (!(En >= lo && En <= hi)) En = 0.5 * (lo + hi); const dE = Math.abs(En - E); E = En; if (dE < 1e-14) break; }
  return sg * E;
}
function keplerE(M, e) {
  if (e > 0.3) return keplerHigh(M, e);
  let E = M + e * Math.sin(M) * (1 + e * Math.cos(M));
  for (let i = 0; i < 10; i++) {
    const d = (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E));
    E -= d;
    if (Math.abs(d) < 1e-13) break;
  }
  return E;
}

/** Retourne { a, e, E, P, Q, pos } ; pos = P·a(cosE − e) + Q·a√(1−e²)·sinE, en UA. */
function planetState(key, T, out) {
  const inT1 = T >= -2 && T <= 0.5;
  const el = inT1 ? DATA.JPL1[key] : DATA.JPL2[key];
  const Tc = inT1 ? T : clamp(T, -50, 10);
  const a = el[0] + el[6] * Tc, e = el[1] + el[7] * Tc, I = (el[2] + el[8] * Tc) * DEG;
  const peri = el[4] + el[10] * Tc, node = el[5] + el[11] * Tc;
  let Mdeg = (el[3] % 360) + ((el[9] * T) % 360) - peri;
  if (!inT1) {
    const x = DATA.JPL2X[key];
    if (x) Mdeg += x[0] * Tc * Tc + x[1] * Math.cos(x[3] * Tc * DEG) + x[2] * Math.sin(x[3] * Tc * DEG);
  }
  const M = wrapPi(Mdeg * DEG);
  const E = keplerE(M, e);
  const w = (peri - node) * DEG, O = node * DEG;
  const cw = Math.cos(w), sw = Math.sin(w), cO = Math.cos(O), sO = Math.sin(O), cI = Math.cos(I), sI = Math.sin(I);
  const o = out || {};
  o.a = a; o.e = e; o.E = E; o.M = M;
  o.P = [cw * cO - sw * sO * cI, cw * sO + sw * cO * cI, sw * sI];
  o.Q = [-sw * cO - cw * sO * cI, -sw * sO + cw * cO * cI, cw * sI];
  const xp = a * (Math.cos(E) - e), yp = a * Math.sqrt(1 - e * e) * Math.sin(E);
  o.pos = [o.P[0] * xp + o.Q[0] * yp, o.P[1] * xp + o.Q[1] * yp, o.P[2] * xp + o.Q[2] * yp];
  o.period = Math.pow(a, 1.5);   // années (3e loi de Kepler, masse de la planète négligée)
  return o;
}

/* --------------------------------------------------------------------------
   Lune : formule basse précision de l'Astronomical Almanac (≈ 0,3° en longitude,
   0,2° en latitude). Géocentrique, ramenée à l'écliptique J2000. Résultat en UA.
   -------------------------------------------------------------------------- */
const EARTH_EQ_RADIUS_KM = 6378.137;
const MOON_MASS_FRACTION = 1 / 82.30057;   // m_Lune / (m_Terre + m_Lune)

function moonGeo(T) {
  const s = x => Math.sin((x % 360) * DEG), c = x => Math.cos((x % 360) * DEG);
  const a1 = 135.0 + 477198.87 * T, a2 = 259.3 - 413335.36 * T, a3 = 235.7 + 890534.22 * T, a4 = 269.9 + 954397.74 * T;
  let lam = 218.32 + ((481267.881 * T) % 360) + 6.29 * s(a1) - 1.27 * s(a2) + 0.66 * s(a3) + 0.21 * s(a4)
          - 0.19 * s(357.5 + 35999.05 * T) - 0.11 * s(186.5 + 966404.03 * T);
  const bet = 5.13 * s(93.3 + 483202.02 * T) + 0.28 * s(228.2 + 960400.89 * T) - 0.28 * s(318.3 + 6003.15 * T) - 0.17 * s(217.6 - 407332.21 * T);
  const par = 0.9508 + 0.0518 * c(a1) + 0.0095 * c(a2) + 0.0078 * c(a3) + 0.0028 * c(a4);
  const Tp = clamp(T, -100, 100);
  lam -= 1.396971 * Tp + 0.0003086 * Tp * Tp;          // précession : écliptique de la date -> J2000
  const r = EARTH_EQ_RADIUS_KM / Math.sin(par * DEG) * 1e3 / AU;
  const l = lam * DEG, b = bet * DEG;
  return [r * Math.cos(b) * Math.cos(l), r * Math.cos(b) * Math.sin(l), r * Math.sin(b)];
}

/* --------------------------------------------------------------------------
   Haute précision (|T| < 30 siècles) : séries VSOP87 pour les planètes, théorie
   lunaire de Meeus (chap. 47) pour la Lune. Les séries donnent des coordonnées
   rapportées à l'écliptique de la date ; on les ramène à l'écliptique J2000 par
   la précession UAI 1976. Écarts mesurés contre l'éphéméride JPL DE440 (1851-2149) :
   moins de 1″ de Mercure à Saturne, 1,6″ Uranus, 2,5″ Neptune, 7″ pour la Lune.
   -------------------------------------------------------------------------- */
const AS2R = Math.PI / 648000, EPS0_76 = 84381.448 * AS2R;
function dateToJ2000(T, m) {
  const ze = (2306.2181 * T + 0.30188 * T * T + 0.017998 * T * T * T) * AS2R, z = (2306.2181 * T + 1.09468 * T * T + 0.018203 * T * T * T) * AS2R, th = (2004.3109 * T - 0.42665 * T * T - 0.041833 * T * T * T) * AS2R;
  const cz = Math.cos(ze), sz = Math.sin(ze), cZ = Math.cos(z), sZ = Math.sin(z), ct = Math.cos(th), st = Math.sin(th);
  const P = [cz * ct * cZ - sz * sZ, -sz * ct * cZ - cz * sZ, -st * cZ, cz * ct * sZ + sz * cZ, -sz * ct * sZ + cz * cZ, -st * sZ, cz * st, -sz * st, ct];
  const ed = (84381.448 - 46.8150 * T - 0.00059 * T * T + 0.001813 * T * T * T) * AS2R, ce = Math.cos(ed), se = Math.sin(ed), c0 = Math.cos(EPS0_76), s0 = Math.sin(EPS0_76);
  const A = [P[0], P[3] * ce + P[6] * se, -P[3] * se + P[6] * ce, P[1], P[4] * ce + P[7] * se, -P[4] * se + P[7] * ce, P[2], P[5] * ce + P[8] * se, -P[5] * se + P[8] * ce];
  m[0] = A[0]; m[1] = A[1]; m[2] = A[2]; m[3] = c0 * A[3] + s0 * A[6]; m[4] = c0 * A[4] + s0 * A[7]; m[5] = c0 * A[5] + s0 * A[8]; m[6] = -s0 * A[3] + c0 * A[6]; m[7] = -s0 * A[4] + c0 * A[7]; m[8] = -s0 * A[5] + c0 * A[8];
  return m;
}
function vsopSeries(S, tau) {
  let tot = 0, tp = 1;
  for (let k = 0; k < S.length; k++) { const s = S[k]; let x = 0; for (let i = 0; i < s.length; i += 3) x += s[i] * Math.cos(s[i + 1] + s[i + 2] * tau); tot += x * tp; tp *= tau; }
  return tot * 1e-8;
}
function vsopHelio(key, T, M, o) {
  const P = DATA.VSOP[key], tau = T / 10, L = vsopSeries(P.L, tau), B = vsopSeries(P.B, tau), R = vsopSeries(P.R, tau);
  const cb = Math.cos(B), x = R * cb * Math.cos(L), y = R * cb * Math.sin(L), z = R * Math.sin(B);
  o[0] = M[0] * x + M[1] * y + M[2] * z; o[1] = M[3] * x + M[4] * y + M[5] * z; o[2] = M[6] * x + M[7] * y + M[8] * z; return o;
}
function moonMeeus(T, Mx, o) {
  const T2 = T * T, T3 = T2 * T, T4 = T3 * T, r = x => (x % 360) * DEG;
  const Lp = 218.3164477 + 481267.88123421 * T - 0.0015786 * T2 + T3 / 538841 - T4 / 65194000;
  const D = 297.8501921 + 445267.1114034 * T - 0.0018819 * T2 + T3 / 545868 - T4 / 113065000;
  const M = 357.5291092 + 35999.0502909 * T - 0.0001536 * T2 + T3 / 24490000;
  const Mp = 134.9633964 + 477198.8675055 * T + 0.0087414 * T2 + T3 / 69699 - T4 / 14712000;
  const F = 93.2720950 + 483202.0175233 * T - 0.0036539 * T2 - T3 / 3526000 + T4 / 863310000;
  const A1 = 119.75 + 131.849 * T, A2 = 53.09 + 479264.290 * T, A3 = 313.45 + 481266.484 * T, E = 1 - 0.002516 * T - 0.0000074 * T2, E2 = E * E;
  const lr = DATA.MOON_LR, bt = DATA.MOON_B;
  let sl = 0, sr = 0, sb = 0;
  for (let i = 0; i < lr.length; i += 6) { const a = r(lr[i] * D + lr[i + 1] * M + lr[i + 2] * Mp + lr[i + 3] * F), m = Math.abs(lr[i + 1]), ef = m === 1 ? E : m === 2 ? E2 : 1; sl += lr[i + 4] * ef * Math.sin(a); sr += lr[i + 5] * ef * Math.cos(a); }
  for (let i = 0; i < bt.length; i += 5) { const a = r(bt[i] * D + bt[i + 1] * M + bt[i + 2] * Mp + bt[i + 3] * F), m = Math.abs(bt[i + 1]), ef = m === 1 ? E : m === 2 ? E2 : 1; sb += bt[i + 4] * ef * Math.sin(a); }
  sl += 3958 * Math.sin(r(A1)) + 1962 * Math.sin(r(Lp - F)) + 318 * Math.sin(r(A2));
  sb += -2235 * Math.sin(r(Lp)) + 382 * Math.sin(r(A3)) + 175 * Math.sin(r(A1 - F)) + 175 * Math.sin(r(A1 + F)) + 127 * Math.sin(r(Lp - Mp)) - 115 * Math.sin(r(Lp + Mp));
  const lam = r(Lp + sl / 1e6), bet = (sb / 1e6) * DEG, d = (385000.56 + sr / 1000) * 1e3 / AU, cb = Math.cos(bet);
  const x = d * cb * Math.cos(lam), y = d * cb * Math.sin(lam), z = d * Math.sin(bet);
  o[0] = Mx[0] * x + Mx[1] * y + Mx[2] * z; o[1] = Mx[3] * x + Mx[4] * y + Mx[5] * z; o[2] = Mx[6] * x + Mx[7] * y + Mx[8] * z; return o;
}
/** Écart entre le temps des éphémérides et le temps civil (secondes). 69,2 s aujourd'hui ; parabole de Morrison-Stephenson au loin. */
function deltaT(T) { const y = 2000 + T * 100, u = (y - 1820) / 100; return lerp(69.2, -20 + 32 * u * u, smoothstep(40, 160, Math.abs(y - 2026))); }

const VSOP_KEYS = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune'];
/** Positions héliocentriques (UA, écliptique J2000) de tous les corps à l'instant T (siècles juliens de temps civil depuis J2000). */
function solarSystemAt(T, st, dtSec) {
  st = st || { planets: {}, moon: [0, 0, 0], earth: [0, 0, 0], M: new Array(9), tmp: [0, 0, 0], e: [0, 0, 0], m: [0, 0, 0] };
  const Tt = T + (dtSec === undefined ? deltaT(T) : dtSec) / (DAY_S * 36525);
  st.long = false; for (const k of PLANET_KEYS) { const q = typeof NB_LONG !== 'undefined' && NB_LONG ? nbLongState(k, Tt, st.planets[k]) : null; if (q) { st.planets[k] = q; st.long = true; } else { if (st.planets[k]) st.planets[k].long = false; st.planets[k] = planetState(k, Tt, st.planets[k]); } }      /* G2 : orbites calculées sur des millions d'années (21_nbody.js), sinon éléments moyens */
  const mLow = moonGeo(Tt), emb = st.planets.emb.pos, aT = Math.abs(Tt);
  let earth = [emb[0] - mLow[0] * MOON_MASS_FRACTION, emb[1] - mLow[1] * MOON_MASS_FRACTION, emb[2] - mLow[2] * MOON_MASS_FRACTION], mg = mLow;
  st.precise = aT < 40 && !!DATA.VSOP;
  if (st.precise) {
    const w = smoothstep(30, 40, aT), M = dateToJ2000(Tt, st.M);
    for (const k of VSOP_KEYS) { const v = vsopHelio(k, Tt, M, st.tmp), p = st.planets[k].pos; p[0] = lerp(v[0], p[0], w); p[1] = lerp(v[1], p[1], w); p[2] = lerp(v[2], p[2], w); }
    const e = vsopHelio('earth', Tt, M, st.e), m = moonMeeus(Tt, M, st.m);
    earth = [lerp(e[0], earth[0], w), lerp(e[1], earth[1], w), lerp(e[2], earth[2], w)]; mg = [lerp(m[0], mLow[0], w), lerp(m[1], mLow[1], w), lerp(m[2], mLow[2], w)];
    emb[0] = earth[0] + mg[0] * MOON_MASS_FRACTION; emb[1] = earth[1] + mg[1] * MOON_MASS_FRACTION; emb[2] = earth[2] + mg[2] * MOON_MASS_FRACTION;
  }
  st.moonGeo = mg; st.earth = earth; st.moon = [earth[0] + mg[0], earth[1] + mg[1], earth[2] + mg[2]];
  return st;
}

/* --------------------------------------------------------------------------
   Petits corps réels (astéroïdes, objets transneptuniens) : éléments osculateurs
   de la base JPL, propagés par les lois de Kepler (deux corps). Exact près de
   l'époque des éléments ; les perturbations planétaires faussent le résultat
   au-delà de quelques décennies.
   -------------------------------------------------------------------------- */
function decodeBodies(tag) {
  const N = DATA[tag + '_N'], el = new Float32Array(b64ToBytes(DATA[tag + '_EL']).buffer), Hb = b64ToBytes(DATA[tag + '_H']), a = new Float32Array(N);
  const B = { N, a, inc: new Float32Array(N), e: new Float32Array(N), n: new Float64Array(N), M0: new Float64Array(N), P: new Float32Array(N * 3), Q: new Float32Array(N * 3), H: new Float32Array(N), pos: new Float32Array(N * 3), look: new Float32Array(N * 2), epoch: DATA[tag + '_EPOCH'] };
  for (let i = 0; i < N; i++) {
    const e = el[i * 6 + 1], I = el[i * 6 + 2], O = el[i * 6 + 3], w = el[i * 6 + 4]; a[i] = el[i * 6];
    B.e[i] = e; B.inc[i] = I; B.M0[i] = el[i * 6 + 5]; B.n[i] = 0.01720209895 / Math.pow(a[i], 1.5); B.H[i] = Hb[i] / 10 - 2;
    const cw = Math.cos(w), sw = Math.sin(w), cO = Math.cos(O), sO = Math.sin(O), cI = Math.cos(I), sI = Math.sin(I), b = Math.sqrt(1 - e * e);
    B.P.set([(cw * cO - sw * sO * cI) * a[i], (cw * sO + sw * cO * cI) * a[i], sw * sI * a[i]], i * 3);
    B.Q.set([(-sw * cO - cw * sO * cI) * a[i] * b, (-sw * sO + cw * cO * cI) * a[i] * b, cw * sI * a[i] * b], i * 3);
    B.look[i * 2] = clamp(2.6 - 0.16 * (B.H[i] - 4), 0.75, 2.6); B.look[i * 2 + 1] = clamp(1.15 - 0.055 * (B.H[i] - 3), 0.32, 1);
  }
  return B;
}
function updateBodies(B, jd) {
  const dd = jd - B.epoch, P = B.P, Q = B.Q, pos = B.pos, n = B.count || B.N;
  for (let i = 0, j = 0; i < n; i++, j += 3) {
    const e = B.e[i], M = wrapPi(B.M0[i] + ((B.n[i] * dd) % TAU));
    let E = e < 0.8 ? M + e * Math.sin(M) : (M > 0 ? Math.PI : -Math.PI) * 0.5 + M * 0.5;
    for (let k = 0; k < 9; k++) { const d = (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E)); E -= d; if (Math.abs(d) < 1e-9) break; }
    const x = Math.cos(E) - e, y = Math.sin(E);
    pos[j] = P[j] * x + Q[j] * y; pos[j + 1] = P[j + 1] * x + Q[j + 1] * y; pos[j + 2] = P[j + 2] * x + Q[j + 2] * y;
  }
}

/* --------------------------------------------------------------------------
   Cosmologie : équations de Friedmann intégrées numériquement (RK4, pas adaptatif).
     ä/a = −(H0²/2) Σ Ω_i (1+3w_i) a^(−3(1+w_i))        (accélération)
     (ȧ/a)² = H0² [Ω_r a⁻⁴ + Ω_m a⁻³ + Ω_k a⁻² + Ω_Λ a^(−3(1+w))]   (contrainte)
   Croissance linéaire des structures : D̈ + 2H Ḋ − (3/2) Ω_m H0² a⁻³ D = 0.
   Temps en Ga (0 = aujourd'hui, a = 1), distances en Mpc.
   -------------------------------------------------------------------------- */
const OMEGA_R_H2 = 4.1837e-5;    // photons (T = 2,7255 K) + 3,046 neutrinos sans masse
const BARYON_H2 = 0.0224;        // Planck 2018
const PLANCK = { H0: 67.4, Om: 0.315, OL: 0.685, w: -1 };
const A_MIN = 1e-5, A_GROW = 1e-3, A_MAX = 1e8, T_PAST_MAX = 400, T_FUT_MAX = 400;

function buildCosmo(par) {
  const H0 = par.H0, Om = Math.max(par.Om, 0), OL = par.OL, w = par.w;
  const h = H0 * KMSMPC_GYR;
  const Or = OMEGA_R_H2 / ((H0 / 100) * (H0 / 100));
  const Ok = 1 - Om - OL - Or;
  const nde = -3 * (1 + w);
  const E2 = a => Or / (a * a * a * a) + Om / (a * a * a) + Ok / (a * a) + OL * Math.pow(a, nde);
  const acc = a => -0.5 * h * h * (2 * Or / (a * a * a) + Om / (a * a) + OL * (1 + 3 * w) * Math.pow(a, nde + 1));
  const ETA = 0.012;
  const C = { par: { H0, Om, OL, w }, h, Or, Ok, E2, acc };

  // ---- 1) remontée dans le passé depuis aujourd'hui, pour trouver le début
  let t = 0, a = 1, v = h, startKind = 'bang', tBounce = null, guard = 0;
  let s0 = null;
  while (guard++ < 400000) {
    const rate = Math.max(Math.abs(v / a), Math.sqrt(Math.abs(acc(a) / a)), 1e-9);
    const dt = -ETA / rate;
    const k1a = v, k1v = acc(a);
    const a2 = a + 0.5 * dt * k1a; if (a2 <= 0) { s0 = { t, a, v }; break; }
    const k2a = v + 0.5 * dt * k1v, k2v = acc(a2);
    const a3 = a + 0.5 * dt * k2a; if (a3 <= 0) { s0 = { t, a, v }; break; }
    const k3a = v + 0.5 * dt * k2v, k3v = acc(a3);
    const a4 = a + dt * k3a; if (a4 <= 0) { s0 = { t, a, v }; break; }
    const k4a = v + dt * k3v, k4v = acc(a4);
    const an = a + dt / 6 * (k1a + 2 * k2a + 2 * k3a + k4a);
    let vn = v + dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v);
    if (an <= 0) { s0 = { t, a, v }; break; }
    if (v > 0 && vn <= 0 && startKind === 'bang') { startKind = 'bounce'; tBounce = t + dt; }
    t += dt; a = an; v = vn;
    if (startKind === 'bang') {
      const e2 = E2(a);
      if (e2 > 0) { const vc = h * a * Math.sqrt(e2); if (vc > 0.5 * Math.abs(v)) v = Math.sign(v || 1) * vc; }
      if (a <= A_MIN) { s0 = { t, a, v }; break; }
    } else if (a >= 3) { s0 = { t, a, v }; break; }
    if (t < -T_PAST_MAX) { if (startKind === 'bang') startKind = 'eternal'; s0 = { t, a, v }; break; }
  }
  if (!s0) s0 = { t, a, v };
  let tBang = null, chi0 = 0;
  if (startKind === 'bang') {
    const a0 = s0.a;
    const tau = Om > 1e-9
      ? (2 / (3 * h * Om * Om)) * ((Om * a0 - 2 * Or) * Math.sqrt(Or + Om * a0) + 2 * Math.pow(Or, 1.5))
      : a0 * a0 / (2 * h * Math.sqrt(Or));
    tBang = s0.t - Math.max(tau, 0);
    chi0 = Om > 1e-9 ? (2 * C_MPC_GYR / (h * Om)) * (Math.sqrt(Or + Om * a0) - Math.sqrt(Or)) : C_MPC_GYR * a0 / (h * Math.sqrt(Or));
  }

  // ---- 2) intégration vers le futur depuis ce début : a, croissance D, distance comobile parcourue par la lumière
  const Tt = [], Aa = [], Vv = [], Dd = [], Xx = [];
  t = s0.t; a = s0.a; v = s0.v;
  let D = a, Dv = v, chi = chi0, endKind = 'limit', growing = a >= A_GROW, turned = false;
  const push = () => { Tt.push(t); Aa.push(a); Vv.push(v); Dd.push(D); Xx.push(chi); };
  push();
  guard = 0;
  const gsrc = 1.5 * Om * h * h;
  while (guard++ < 400000) {
    const rate = Math.max(Math.abs(v / a), Math.sqrt(Math.abs(acc(a) / a)), 1e-9);
    let dt = ETA / rate;
    if (t < 0 && t + dt > 0) dt = -t;            // tomber exactement sur aujourd'hui
    const f = (a_, v_, D_, Dv_) => {
      const ac = acc(a_);
      return growing ? [v_, ac, Dv_, -2 * (v_ / a_) * Dv_ + gsrc * D_ / (a_ * a_ * a_), C_MPC_GYR / a_] : [v_, ac, v_, ac, C_MPC_GYR / a_];
    };
    const k1 = f(a, v, D, Dv);
    const a2 = a + 0.5 * dt * k1[0]; if (a2 <= 0) { endKind = 'crunch'; break; }
    const k2 = f(a2, v + 0.5 * dt * k1[1], D + 0.5 * dt * k1[2], Dv + 0.5 * dt * k1[3]);
    const a3 = a + 0.5 * dt * k2[0]; if (a3 <= 0) { endKind = 'crunch'; break; }
    const k3 = f(a3, v + 0.5 * dt * k2[1], D + 0.5 * dt * k2[2], Dv + 0.5 * dt * k2[3]);
    const a4 = a + dt * k3[0]; if (a4 <= 0) { endKind = 'crunch'; break; }
    const k4 = f(a4, v + dt * k3[1], D + dt * k3[2], Dv + dt * k3[3]);
    const an = a + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]);
    if (an <= 0) { endKind = 'crunch'; break; }
    const vPrev = v;
    v += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]);
    D += dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2]);
    Dv += dt / 6 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3]);
    chi += dt / 6 * (k1[4] + 2 * k2[4] + 2 * k3[4] + k4[4]);
    a = an; t += dt;
    if (vPrev > 0 && v <= 0) turned = true;
    const e2 = E2(a);
    if (e2 > 0) { const vc = h * a * Math.sqrt(e2); if (vc > 0.5 * Math.abs(v)) v = Math.sign(v || 1) * vc; }
    if (!growing) { D = a; Dv = v; if (a >= A_GROW) growing = true; }
    push();
    if (turned && a <= 1e-4) { endKind = 'crunch'; break; }
    if (a >= A_MAX) { endKind = w < -1 - 1e-9 ? 'rip' : 'limit'; break; }
    if (t > T_FUT_MAX) { endKind = 'limit'; break; }
  }
  const n = Tt.length;
  let tEnd = Tt[n - 1];
  if (endKind === 'crunch') tEnd += 0.5 * Aa[n - 1] / Math.max(Math.abs(Vv[n - 1]), 1e-12);
  C.t = Float64Array.from(Tt); C.a = Float64Array.from(Aa); C.v = Float64Array.from(Vv);
  C.D = Float64Array.from(Dd); C.chi = Float64Array.from(Xx);
  C.n = n; C.tStart = Tt[0]; C.tEnd = tEnd; C.tBang = tBang; C.tBounce = tBounce;
  C.startKind = startKind; C.endKind = endKind;
  C.age = tBang !== null ? -tBang : null;

  // horizon des événements : distance comobile que la lumière peut encore parcourir d'ici la fin
  const aE = Aa[n - 1], vE = Vv[n - 1], qE = -acc(aE) * aE / (vE * vE);
  let tail = null;
  if (endKind === 'crunch' || endKind === 'rip') tail = 0;
  else if (qE < -1e-3 && OL > 0 && w < -1 / 3) tail = C_MPC_GYR / vE * 2 / Math.abs(1 + 3 * w);
  C.chiEnd = tail === null ? null : Xx[n - 1] + tail;
  C.accelEnd = qE < 0;

  // instant où l'expansion passe du freinage à l'accélération
  C.tAccel = null;
  for (let i = 1; i < n; i++) if (acc(Aa[i - 1]) < 0 && acc(Aa[i]) >= 0) { C.tAccel = Tt[i]; break; }
  if (startKind !== 'bang') C.D.fill(1);
  C.Dtoday = cosmoAt(C, 0).D;
  return C;
}

/** État de l'univers à l'instant t (Ga, 0 = aujourd'hui), par interpolation dans la solution. */
function cosmoAt(C, t, o) {
  o = o || {};
  const T = C.t, n = C.n;
  let a, v, D, chi;
  if (t <= T[0]) {
    if (C.tBang !== null && T[0] > C.tBang) {
      const f = Math.sqrt(clamp((t - C.tBang) / (T[0] - C.tBang), 1e-12, 1));
      a = C.a[0] * f; v = C.v[0] / f; D = C.D[0] * f; chi = C.chi[0] * f;
    } else { a = C.a[0]; v = C.v[0]; D = C.D[0]; chi = C.chi[0]; }
  } else if (t >= T[n - 1]) {
    a = C.a[n - 1]; v = C.v[n - 1]; D = C.D[n - 1]; chi = C.chi[n - 1];
  } else {
    let lo = 0, hi = n - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T[m] <= t) lo = m; else hi = m; }
    const f = (t - T[lo]) / (T[hi] - T[lo]);
    a = lerp(C.a[lo], C.a[hi], f); v = lerp(C.v[lo], C.v[hi], f); D = lerp(C.D[lo], C.D[hi], f); chi = lerp(C.chi[lo], C.chi[hi], f);
  }
  o.a = a; o.v = v; o.D = D;
  o.H = v / a;                                   // Ga^-1
  o.Hkms = o.H / KMSMPC_GYR;                     // km/s/Mpc
  o.q = Math.abs(v) > 1e-12 ? -C.acc(a) * a / (v * v) : 0;   /* paramètre de décélération (négatif = accélère ; borné au rebond/retournement où v = 0) */
  o.chiPH = C.tBang !== null ? chi : null;       // horizon des particules, comobile (Mpc)
  o.chiEH = C.chiEnd !== null ? Math.max(C.chiEnd - chi, 0) : null;   // horizon des événements, comobile
  o.rHubble = Math.abs(o.H) > 1e-12 ? C_MPC_GYR / Math.abs(o.H) : Infinity;   // rayon de Hubble, physique (Mpc)
  // parts de chaque composante dans le contenu de l'univers à cet instant
  const er = C.Or / (a * a * a * a), em = C.par.Om / (a * a * a), ed = Math.max(C.par.OL, 0) * Math.pow(a, -3 * (1 + C.par.w));
  const tot = er + em + ed || 1;
  o.fr = er / tot; o.fm = em / tot; o.fde = ed / tot;
  return o;
}

/* --------------------------------------------------------------------------
   Voie lactée : courbe de rotation = bulbe (Hernquist) + disque (Miyamoto-Nagai)
   + halo de matière noire (NFW), calée sur 230 km/s au niveau du Soleil.
   -------------------------------------------------------------------------- */
const G_KPC = 4.30091e-6;                 // G en kpc·(km/s)²/masse solaire
const GAL = {
  R0: 8.2, V0: 230,                        // distance Soleil–centre (kpc), vitesse circulaire au Soleil (km/s)
  Mb: 0.5e10, ab: 0.5,                     // bulbe
  Md: 6.8e10, ad: 3.0, bd: 0.28,           // disque
  rs: 16,                                  // rayon d'échelle du halo
  OMEGA_BAR: 39, OMEGA_ARMS: 26,           // vitesses de rotation des motifs (km/s/kpc)
  BAR_ANGLE: 28 * DEG, PITCH: 12.5 * DEG,
};
const v2Baryons = r => G_KPC * GAL.Mb * r / ((r + GAL.ab) * (r + GAL.ab)) + G_KPC * GAL.Md * r * r / Math.pow(r * r + (GAL.ad + GAL.bd) * (GAL.ad + GAL.bd), 1.5);
const nfwShape = r => { const x = r / GAL.rs; return (Math.log(1 + x) - x / (1 + x)) / r; };
GAL.GMs = (GAL.V0 * GAL.V0 - v2Baryons(GAL.R0)) / nfwShape(GAL.R0);
const vCirc = (r, withDM) => { r = Math.max(r, 0.05); return Math.sqrt(v2Baryons(r) + (withDM ? GAL.GMs * nfwShape(r) : 0)); };
/** Vitesse angulaire (rad/Ga) à la distance r (kpc) du centre. */
const omegaGal = (r, withDM) => { r = Math.max(r, 0.4); return vCirc(r, withDM) / r * KMS_KPC_RADGYR; };



/* Comètes : éléments du JPL (distance au périhélie q, excentricité e, date du passage au périhélie). Orbite képlérienne pure. */
function decodeComets() {
  const N = DATA.COM_N, el = new Float32Array(b64ToBytes(DATA.COM_EL).buffer), C = { N, count: N, e: new Float32Array(N), a: new Float32Array(N), inc: new Float32Array(N), n: new Float64Array(N), tp: new Float64Array(N), P: new Float32Array(N * 3), Q: new Float32Array(N * 3), pos: new Float32Array(N * 3), look: new Float32Array(N * 2) };
  { const fx = DATA.COM_FIX || {}, nm = DATA.COM_NAMES.split('|'); for (const k in fx) { const i = nm.indexOf(k); if (i >= 0) for (let j = 0; j < 6; j++) el[i * 6 + j] = fx[k].el[j]; } }      // comètes célèbres : éléments d'aujourd'hui recalculés par le JPL
  for (let i = 0; i < N; i++) {
    const q = el[i * 6], e = el[i * 6 + 1], inc = el[i * 6 + 2] * DEG, om = el[i * 6 + 3] * DEG, w = el[i * 6 + 4] * DEG, a = q / (1 - e);
    C.e[i] = e; C.a[i] = a; C.inc[i] = inc; C.n[i] = 0.01720209895 / Math.pow(a, 1.5); C.tp[i] = el[i * 6 + 5];
    const co = Math.cos(om), so = Math.sin(om), ci = Math.cos(inc), si = Math.sin(inc), cw = Math.cos(w), sw = Math.sin(w);
    C.P.set([co * cw - so * sw * ci, so * cw + co * sw * ci, sw * si], i * 3); C.Q.set([-co * sw - so * cw * ci, -so * sw + co * cw * ci, cw * si], i * 3);
    C.look[i * 2] = 1.5; C.look[i * 2 + 1] = 0.95;
  }
  return C;
}
function updateComets(C, days) {      // days : jours depuis J2000
  for (let i = 0, j = 0; i < C.N; i++, j += 3) { const e = C.e[i], a = C.a[i], E = keplerHigh(C.n[i] * (days - C.tp[i]), e), x = a * (Math.cos(E) - e), y = a * Math.sqrt(1 - e * e) * Math.sin(E);
    C.pos[j] = C.P[j] * x + C.Q[j] * y; C.pos[j + 1] = C.P[j + 1] * x + C.Q[j + 1] * y; C.pos[j + 2] = C.P[j + 2] * x + C.Q[j + 2] * y; }
}
