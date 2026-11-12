/* ==========================================================================
   Petits corps tirés par les planètes (lot G, niveau G3).

   Un astéroïde ou une comète est une « particule test » : il subit l'attraction
   du Soleil, des planètes, de la Terre et de la Lune séparément, sans les tirer
   en retour (sa masse est des millions de fois trop faible pour compter).
   Positions des planètes : celles de la page (VSOP87, Lune de Meeus), à toute date
   de ±3 000 ans. Relativité générale du Soleil comprise.

   Intégrateur : Dormand et Prince 5(4) à pas adaptatif (Dormand et Prince 1980,
   J. Comput. Appl. Math. 6, 19) : le pas se raccourcit tout seul près d'une
   planète, ce qu'un pas fixe ne sait pas faire (rencontre d'Apophis en 2029).

   Non calculé, et dit : la poussée du gaz des comètes (forces non
   gravitationnelles) et l'effet Yarkovsky des astéroïdes (poussée de la chaleur
   réémise), présents dans les solutions du JPL.
   Unités : UA, jour ; repère héliocentrique, écliptique J2000 ; temps TDB.
   ========================================================================== */
const SB_GM = { mercury: 4.9125001948893182e-11, venus: 7.2434524861627027e-10, earth: 8.8876924467071033e-10, moon: 1.0931894624024351e-11,
  mars: 9.5495488297258119e-11, jupiter: 2.8253458252257917e-7, saturn: 8.4597059933762903e-8, uranus: 1.2920265649682399e-8, neptune: 1.5243573478851939e-8 };
const SB_PL = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune'];

/** Positions héliocentriques des corps qui tirent (UA) à la date jd (TDB). Renvoie un tableau [gm, x, y, z]×n. */
function sbField(jd, ctx) {
  const st = ctx.st = solarSystemAt((jd - 2451545) / 36525, ctx.st, 0), f = ctx.f || (ctx.f = new Float64Array(9 * 4));
  let k = 0; const put = (g, p) => { f[k] = g; f[k + 1] = p[0]; f[k + 2] = p[1]; f[k + 3] = p[2]; k += 4; };
  for (const n of SB_PL) put(SB_GM[n], st.planets[n].pos);
  put(SB_GM.earth, st.earth); put(SB_GM.moon, st.moon);
  return f;
}

/** Accélération (UA/jour²) d'un petit corps en (x, v) à la date jd. */
function sbAccel(jd, y, out, ctx) {
  const f = sbField(jd, ctx), x = y[0], yy = y[1], z = y[2], r2 = x * x + yy * yy + z * z, r = Math.sqrt(r2), mu = NB_GM_SUN;
  let ax = -mu * x / (r2 * r), ay = -mu * yy / (r2 * r), az = -mu * z / (r2 * r);
  for (let k = 0; k < f.length; k += 4) {
    const g = f[k], px = f[k + 1], py = f[k + 2], pz = f[k + 3], dx = px - x, dy = py - yy, dz = pz - z;
    const d2 = dx * dx + dy * dy + dz * dz, d3 = d2 * Math.sqrt(d2), p2 = px * px + py * py + pz * pz, p3 = p2 * Math.sqrt(p2);
    ax += g * (dx / d3 - px / p3); ay += g * (dy / d3 - py / p3); az += g * (dz / d3 - pz / p3);      /* attraction directe − attraction sur le Soleil */
  }
  const vx = y[3], vy = y[4], vz = y[5], v2 = vx * vx + vy * vy + vz * vz, rv = x * vx + yy * vy + z * vz, c2 = NB_C_AU_DAY * NB_C_AU_DAY, kg = mu / (c2 * r2 * r), a1 = 4 * mu / r - v2;
  ax += kg * (a1 * x + 4 * rv * vx); ay += kg * (a1 * yy + 4 * rv * vy); az += kg * (a1 * z + 4 * rv * vz);
  out[0] = vx; out[1] = vy; out[2] = vz; out[3] = ax; out[4] = ay; out[5] = az;
  return out;
}

/* Coefficients de Dormand et Prince 5(4). */
const DP_C = [0, 1 / 5, 3 / 10, 4 / 5, 8 / 9, 1, 1];
const DP_A = [[], [1 / 5], [3 / 40, 9 / 40], [44 / 45, -56 / 15, 32 / 9], [19372 / 6561, -25360 / 2187, 64448 / 6561, -212 / 729],
  [9017 / 3168, -355 / 33, 46732 / 5247, 49 / 176, -5103 / 18656], [35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84]];
const DP_E = [71 / 57600, 0, -71 / 16695, 71 / 1920, -17253 / 339200, 22 / 525, -1 / 40];

/** Intègre de y.jd à jd1. y = { jd, s: Float64Array(6) }. onStep(jd, s) est appelé à chaque pas accepté.
    tol : erreur tolérée par pas, relative à la distance au Soleil (1e-12 par défaut). */
function sbPropagate(y, jd1, onStep, tol) {
  tol = tol || 1e-12;
  const ctx = {}, K = [0, 1, 2, 3, 4, 5, 6].map(() => new Float64Array(6)), tmp = new Float64Array(6), s = y.s, dir = jd1 >= y.jd ? 1 : -1;
  let t = y.jd, h = dir * 0.5, n = 0;
  sbAccel(t, s, K[0], ctx);
  while ((jd1 - t) * dir > 1e-9 && n < 2e6) {
    if ((t + h - jd1) * dir > 0) h = jd1 - t;
    for (let i = 1; i < 7; i++) {
      for (let c = 0; c < 6; c++) { let a = s[c]; for (let j = 0; j < i; j++) a += h * DP_A[i][j] * K[j][c]; tmp[c] = a; }
      sbAccel(t + DP_C[i] * h, tmp, K[i], ctx);
    }
    let err = 0; for (let c = 0; c < 3; c++) { let e = 0; for (let j = 0; j < 7; j++) e += DP_E[j] * K[j][c]; err = Math.max(err, Math.abs(h * e)); }
    const scale = tol * Math.max(Math.hypot(s[0], s[1], s[2]), 1e-3);
    if (err <= scale) {
      t += h; s.set(tmp); n++; const k0 = K[0]; K[0] = K[6]; K[6] = k0;      /* propriété FSAL : la dernière dérivée sert au pas suivant */
      if (onStep) onStep(t, s, ctx);
    }
    h *= Math.min(4, Math.max(0.2, 0.9 * Math.pow(scale / Math.max(err, 1e-300), 0.2)));
  }
  y.jd = t; return y;
}

/* Distance à la Terre et vitesse d'approche (UA, UA/jour) d'un état s à la date t.
   Vitesse de la Terre par différence centrée sur ±0,01 jour (l'éphéméride de la page ne donne que des positions). */
function sbRange(t, s, ctx) {
  const T = jd => (jd - 2451545) / 36525, e = solarSystemAt(T(t), ctx.e, 0).earth.slice(), a = solarSystemAt(T(t + 0.01), ctx.e, 0).earth.slice(), b = solarSystemAt(T(t - 0.01), ctx.e, 0).earth;
  const dx = s[0] - e[0], dy = s[1] - e[1], dz = s[2] - e[2], d = Math.hypot(dx, dy, dz);
  return [d, (dx * (s[3] - (a[0] - b[0]) / 0.02) + dy * (s[4] - (a[1] - b[1]) / 0.02) + dz * (s[5] - (a[2] - b[2]) / 0.02)) / d];
}

/** Plus courtes distances à la Terre entre deux dates : liste de { jd, dist } (UA, centre à centre), sous dMax.
    Un minimum est encadré quand la vitesse d'approche change de signe entre deux pas, puis affiné par la sécante
    en repartant du pas précédent (trois itérations). */
function sbApproaches(y0, jd1, dMax) {
  const y = { jd: y0.jd, s: Float64Array.from(y0.s) }, out = [], cr = {};
  let prev = null;
  sbPropagate(y, jd1, (t, s, ctx) => {
    const e = ctx.st.earth, d = Math.hypot(s[0] - e[0], s[1] - e[1], s[2] - e[2]);
    if (d > dMax * 4) { prev = null; return; }
    const cur = { t, s: Float64Array.from(s), r: sbRange(t, s, cr) };
    if (prev && prev.r[1] < 0 && cur.r[1] >= 0) {
      let a = prev, b = cur, m = null;
      for (let k = 0; k < 3; k++) {
        const tm = a.t + (b.t - a.t) * a.r[1] / (a.r[1] - b.r[1]), q = { jd: a.t, s: Float64Array.from(a.s) };
        sbPropagate(q, tm, null); m = { t: tm, s: q.s, r: sbRange(tm, q.s, cr) };
        if (m.r[1] < 0) a = m; else b = m;
      }
      if (m.r[0] < dMax) out.push({ jd: m.t, dist: m.r[0] });
    }
    prev = cur;
  });
  return out;
}
