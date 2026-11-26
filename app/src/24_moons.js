/* ==========================================================================
   Lunes galiléennes en gravité mutuelle (lot G, lunes).

   Io, Europe, Ganymède et Callisto s'attirent toutes entre elles, sont tirées
   par Jupiter (masse, et son aplatissement : termes J2 et J4 du champ mesuré
   par la sonde Juno, Iess et al. 2018) et par le Soleil (effet de marée).
   C'est ce qui crée la résonance d'Io, Europe et Ganymède (1:2:4) et fait
   tourner leurs orbites, que les ellipses de Kepler ne savent pas faire.

   Repère : centré sur Jupiter, écliptique J2000 ; km et jours ; temps TDB.
   Intégrateur : Dormand et Prince 5(4), pas adaptatif.
   Masses : JPL Horizons. Pôle de Jupiter : UAI 2015 (Archinal et al. 2018).
   Contrôle : app/test/lunes.test.js contre JPL Horizons.
   ========================================================================== */
const MO_D2 = 86400 * 86400;
const MO_JUP = { gm: 126686531.900 * MO_D2, R: 71492, J2: 14696.572e-6, J4: -586.609e-6, names: ['io', 'europa', 'ganymede', 'callisto'],
  gmM: [5959.9155, 3202.7121, 9887.8328, 7179.2834].map(g => g * MO_D2) };
/* Pôle de Jupiter (UAI 2015) : ascension droite 268,056595° − 0,006499° T, déclinaison 64,495303° + 0,002413° T (T en siècles depuis J2000), passé dans l'écliptique J2000 */
function moPole(jd) { const T = (jd - JD_J2000) / 36525, a = (268.056595 - 0.006499 * T) * DEG, d = (64.495303 + 0.002413 * T) * DEG, e = 23.4392911 * DEG;
  const x = Math.cos(d) * Math.cos(a), y = Math.cos(d) * Math.sin(a), z = Math.sin(d); return [x, Math.cos(e) * y + Math.sin(e) * z, -Math.sin(e) * y + Math.cos(e) * z]; }
/* Champ de Jupiter avec J2 et J4 : a = −∇Φ, Φ = −μ/r + Σ μ Jn Rⁿ Pn(u) / rⁿ⁺¹, u = (r·k)/r ;
   ∇(Pn(u)/rⁿ⁺¹) = [Pn'(u)(k − u r̂) − (n+1) Pn(u) r̂] / rⁿ⁺². */
function moField(P, k, x, y, z, out) {
  const r2 = x * x + y * y + z * z, r = Math.sqrt(r2), ux = x / r, uy = y / r, uz = z / r, u = ux * k[0] + uy * k[1] + uz * k[2], u2 = u * u, q2 = P.R * P.R / r2;
  const P2 = (3 * u2 - 1) / 2, d2 = 3 * u, P4 = (35 * u2 * u2 - 30 * u2 + 3) / 8, d4 = (140 * u2 * u - 60 * u) / 8;
  const c2 = P.gm * P.J2 * q2 / r2, c4 = P.gm * P.J4 * q2 * q2 / r2;
  const A = c2 * d2 + c4 * d4, B = -P.gm / r2 + c2 * (u * d2 + 3 * P2) + c4 * (u * d4 + 5 * P4);      /* −∇T = −c[Pn'(k − u r̂) − (n+1)Pn r̂] */
  out[0] = B * ux - A * k[0]; out[1] = B * uy - A * k[1]; out[2] = B * uz - A * k[2]; return out;
}
const MO_GS = 1.32712440041e11 * MO_D2;
function moAccel(P, jd, s, out, ctx) {
  const n = P.names.length, k = ctx.k || (ctx.k = moPole(jd)), f3 = ctx.f3 || (ctx.f3 = [0, 0, 0]), r3 = ctx.r3 || (ctx.r3 = new Float64Array(n));
  if (!ctx.sun || Math.abs(jd - ctx.sunJd) > 0.5) {
    const T = (jd - JD_J2000) / 36525, AUK = AU / 1e3;
    let J;
    if (Math.abs(T) < 30 && DATA.VSOP) {
      const M = ctx.M || (ctx.M = new Array(9));
      dateToJ2000(T, M);
      J = vsopHelio('jupiter', T, M, ctx.j || (ctx.j = [0, 0, 0]));
    } else {
      ctx.st = solarSystemAt(T, ctx.st, 0);
      J = ctx.st.planets.jupiter.pos;
    }
    const sun = ctx.sun || (ctx.sun = [0, 0, 0]);
    sun[0] = -J[0] * AUK; sun[1] = -J[1] * AUK; sun[2] = -J[2] * AUK;
    const s2 = sun[0] * sun[0] + sun[1] * sun[1] + sun[2] * sun[2];
    ctx.s3 = s2 * Math.sqrt(s2); ctx.sunJd = jd;
  }      /* le Soleil vu de Jupiter bouge de 0,08° par jour : position mise à jour toutes les 12 heures */
  const sx = ctx.sun[0], sy = ctx.sun[1], sz = ctx.sun[2], s3 = ctx.s3, gS = MO_GS, gmM = P.gmM;
  let ix = 0, iy = 0, iz = 0;      /* accélération indirecte totale des lunes sur Jupiter */
  for (let i = 0; i < n; i++) {
    const o = i * 6, x = s[o], y = s[o + 1], z = s[o + 2], d2 = x * x + y * y + z * z, ir3 = 1 / (d2 * Math.sqrt(d2));
    r3[i] = ir3;
    const g = gmM[i] * ir3;
    ix += g * x; iy += g * y; iz += g * z;
    moField(P, k, x, y, z, f3);
    const f = 1 + gmM[i] / P.gm;
    const dx = sx - x, dy = sy - y, dz = sz - z, sd2 = dx * dx + dy * dy + dz * dz, sd3 = sd2 * Math.sqrt(sd2);
    out[o] = s[o + 3]; out[o + 1] = s[o + 4]; out[o + 2] = s[o + 5];
    out[o + 3] = f3[0] * f + gS * (dx / sd3 - sx / s3);
    out[o + 4] = f3[1] * f + gS * (dy / sd3 - sy / s3);
    out[o + 5] = f3[2] * f + gS * (dz / sd3 - sz / s3);
  }
  for (let i = 0; i < n; i++) {
    const o = i * 6, x = s[o], y = s[o + 1], z = s[o + 2], gi = gmM[i];
    out[o + 3] -= ix - gi * r3[i] * x;
    out[o + 4] -= iy - gi * r3[i] * y;
    out[o + 5] -= iz - gi * r3[i] * z;
    for (let j = i + 1; j < n; j++) {
      const p = j * 6, dx = s[p] - x, dy = s[p + 1] - y, dz = s[p + 2] - z, d2 = dx * dx + dy * dy + dz * dz, id3 = 1 / (d2 * Math.sqrt(d2));
      const gj = gmM[j] * id3, gii = gi * id3;
      out[o + 3] += gj * dx; out[o + 4] += gj * dy; out[o + 5] += gj * dz;
      out[p + 3] -= gii * dx; out[p + 4] -= gii * dy; out[p + 5] -= gii * dz;
    }
  }
  return out;
}

/** Système de lunes pas à pas, interruptible (même schéma que sbStepper, 22_smallbody.js). y = { jd, s : Float64Array(6n) } en km et km/jour. */
function moStepper(P, y, jd1, onStep, tol) {
  tol = tol || 1e-11; const D = y.s.length, ctx = {}, K = [0, 1, 2, 3, 4, 5, 6].map(() => new Float64Array(D)), tmp = new Float64Array(D), s = y.s, dir = jd1 >= y.jd ? 1 : -1;
  let h = dir * 0.02, n = 0, k0 = false;
  const step = () => {
    const t = y.jd; if (!k0) { moAccel(P, t, s, K[0], ctx); k0 = true; }
    if ((t + h - jd1) * dir > 0) h = jd1 - t;
    for (let i = 1; i < 7; i++) { for (let c = 0; c < D; c++) { let a = s[c]; for (let j = 0; j < i; j++) a += h * DP_A[i][j] * K[j][c]; tmp[c] = a; } moAccel(P, t + DP_C[i] * h, tmp, K[i], ctx); }
    let err = 0, sc = 0; for (let c = 0; c < D; c += 6) { sc = Math.max(sc, Math.hypot(s[c], s[c + 1], s[c + 2])); for (let q = 0; q < 3; q++) { let e = 0; for (let j = 0; j < 7; j++) e += DP_E[j] * K[j][c + q]; err = Math.max(err, Math.abs(h * e)); } }
    const lim = tol * sc;
    if (err <= lim) { y.jd = Math.abs(jd1 - (t + h)) < 1e-12 ? jd1 : t + h; s.set(tmp); n++; const kk = K[0]; K[0] = K[6]; K[6] = kk; if (onStep) onStep(y.jd, s); }
    h *= Math.min(4, Math.max(0.2, 0.9 * Math.pow(lim / Math.max(err, 1e-300), 0.2)));
  };
  return { y, done: () => !((jd1 - y.jd) * dir > 1e-9) || n >= 5e6,
    run(ms) { const t0 = Date.now(); let k = 0; while (!this.done()) { step(); if ((++k & 15) === 0 && Date.now() - t0 > ms) break; } return this.done(); } };
}

/** Suivi des lunes dans la page, de jd0 − span à jd0 + span : points de reprise tous les 100 jours, construits à la
    demande, puis un état courant qu'on fait avancer jusqu'à l'heure affichée. at(jd, ms) renvoie les positions (km,
    centre de Jupiter) à jd, ou null tant que le calcul n'y est pas (la page garde alors ses ellipses et le dit). */
function moTrack(P, s0, jd0, span) {
  const CP = 100, cps = new Map([[0, Float64Array.from(s0)]]), T = { jd0, span, cur: null, busy: null };
  const key = jd => Math.round((jd - jd0) / CP);
  T.at = (jd, ms) => {
    if (!(Math.abs(jd - jd0) <= span)) return null;
    const t0 = Date.now(), left = () => Math.max(1, ms - (Date.now() - t0));
    /* lecture continue : l'état courant avance jusqu'à l'heure affichée ; s'il n'y est pas encore, dernière position calculée */
    if (T.cur && Math.abs(T.cur.y.jd - jd) <= 400) { if (Math.abs(T.cur.y.jd - jd) > 1e-9 && !moStepper(P, T.cur.y, jd).run(left())) return T.last; T.last = Float64Array.from(T.cur.y.s); T.lastJd = jd; return T.last; }
    /* saut lointain : on repart du point de reprise le plus proche (construit à la demande, tous les 100 jours) */
    const k = key(jd);
    if (!cps.has(k)) {
      const dir = Math.sign(k) || 1; let j = k; while (!cps.has(j)) j -= dir;
      if (!T.busy || T.busy.from !== j) { const y = { jd: jd0 + j * CP, s: Float64Array.from(cps.get(j)) }; T.busy = { from: j, y, st: moStepper(P, y, jd0 + (j + dir) * CP) }; }
      if (T.busy.st.run(ms)) { cps.set(T.busy.from + dir, Float64Array.from(T.busy.y.s)); T.busy = null; }
      return null;
    }
    T.cur = { y: { jd: jd0 + k * CP, s: Float64Array.from(cps.get(k)) } };
    if (!moStepper(P, T.cur.y, jd).run(left())) return null;
    T.last = Float64Array.from(T.cur.y.s); return T.last;
  };
  return T;
}
