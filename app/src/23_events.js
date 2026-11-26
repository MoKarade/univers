/* ==========================================================================
   Événements calculés par la page à partir de ses propres positions (lot G) :
   passages de Mercure et de Vénus devant le Soleil.

   Vu du centre de la Terre, avec le temps de trajet de la lumière (le Soleil et
   la planète sont vus où ils étaient quand leur lumière est partie). Rayon du
   Soleil : 959,63″ à 1 UA (Auwers, rayon adopté par les éphémérides).
   Contrôle : catalogue de la NASA (Espenak), app/test/evenements.test.js.
   ========================================================================== */
const EV_SUN_R_AS = 959.63, EV_AU_DAY = 1 / 173.1446326846693;      /* temps de lumière : jours par UA */
const EV_PLANET_R_KM = { mercury: 2439.7, venus: 6051.8 };

function evBodyPos(key, Tt, ctx, out) {
  if (Math.abs(Tt) < 30 && DATA.VSOP) {
    const M = ctx.M || (ctx.M = new Array(9));
    if (ctx.Mt !== Tt) { dateToJ2000(Tt, M); ctx.Mt = Tt; }
    return vsopHelio(key, Tt, M, out);
  }
  const st = ctx.st = solarSystemAt(Tt, ctx.st, 0);
  const src = key === 'earth' ? st.earth : st.planets[key].pos;
  out[0] = src[0]; out[1] = src[1]; out[2] = src[2];
  return out;
}

/* Séparation (″) entre les centres du Soleil et de la planète vus de la Terre à la date jdUT, et rayons apparents. */
function evSep(key, jdUT, ctx) {
  const T = jd => (jd - JD_J2000) / 36525, tdb = jdUT + deltaT(T(jdUT)) / DAY_S, Tt = T(tdb);
  const e = evBodyPos('earth', Tt, ctx, ctx.e || (ctx.e = [0, 0, 0]));
  const p = evBodyPos(key, Tt, ctx, ctx.p || (ctx.p = [0, 0, 0]));
  for (let k = 0; k < 2; k++) {
    const d = Math.hypot(p[0] - e[0], p[1] - e[1], p[2] - e[2]);
    evBodyPos(key, T(tdb - d * EV_AU_DAY), ctx, p);
  }
  const gx = p[0] - e[0], gy = p[1] - e[1], gz = p[2] - e[2];
  const ds = Math.hypot(e[0], e[1], e[2]), dp = Math.hypot(gx, gy, gz);
  const c = -(gx * e[0] + gy * e[1] + gz * e[2]) / (dp * ds);      /* le Soleil est en −e ; son déplacement pendant 8 min de lumière est celui de la Terre, déjà pris par l'aberration commune, négligé */
  return { sep: Math.acos(clamp(c, -1, 1)) * 206264.806, rSun: EV_SUN_R_AS / ds, rP: EV_PLANET_R_KM[key] / (dp * AU / 1e3) * 206264.806, front: dp < ds };
}

/** Passages de la planète (mercury, venus) devant le Soleil entre jd0 et jd1 (temps civil) :
    [{ jd (milieu, temps civil), sep (″, distance minimale des centres), rSun (″) }]. */
function evTransits(key, jd0, jd1) {
  const ctx = {}, out = [], f = jd => evSep(key, jd, ctx).sep;
  const jump = key === 'mercury' ? 88 : key === 'venus' ? 540 : 0;      /* borne inférieure stricte sous la période synodique (Mercure ≥ 104 j, Vénus ≥ 580 j) */
  let a = f(jd0 - 1), b = f(jd0);
  for (let jd = jd0 + 1; jd <= jd1; jd++) {
    const c = f(jd);
    if (b < a && b <= c && b < 18000) {      /* conjonction (moins de 5° au pas d’un jour) : minimum affiné par la section dorée */
      let lo = jd - 2, hi = jd;
      for (let k = 0; k < 40; k++) {
        const m1 = hi - (hi - lo) * 0.618, m2 = lo + (hi - lo) * 0.618;
        if (f(m1) < f(m2)) hi = m2; else lo = m1;
      }
      const t = (lo + hi) / 2, s = evSep(key, t, ctx);
      if (s.front) {
        if (s.sep < s.rSun + s.rP) out.push({ jd: t, sep: s.sep, rSun: s.rSun });
        if (jump > 0 && jd + jump <= jd1) {
          jd += jump;
          a = f(jd - 1); b = f(jd);
          continue;
        }
      }
    }
    a = b; b = c;
  }
  return out;
}
