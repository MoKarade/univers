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

/* Séparation (″) entre les centres du Soleil et de la planète vus de la Terre à la date jdUT, et rayons apparents. */
function evSep(key, jdUT, ctx) {
  const T = jd => (jd - JD_J2000) / 36525, tdb = jdUT + deltaT(T(jdUT)) / DAY_S;
  const e = solarSystemAt(T(tdb), ctx.a, 0).earth.slice();
  let p = solarSystemAt(T(tdb), ctx.b, 0).planets[key].pos, d = 0;
  for (let k = 0; k < 2; k++) { d = Math.hypot(p[0] - e[0], p[1] - e[1], p[2] - e[2]); p = solarSystemAt(T(tdb - d * EV_AU_DAY), ctx.b, 0).planets[key].pos; }
  const g = [p[0] - e[0], p[1] - e[1], p[2] - e[2]], ds = Math.hypot(e[0], e[1], e[2]), dp = Math.hypot(...g);
  const c = -(g[0] * e[0] + g[1] * e[1] + g[2] * e[2]) / (dp * ds);      /* le Soleil est en −e ; son déplacement pendant 8 min de lumière est celui de la Terre, déjà pris par l'aberration commune, négligé */
  return { sep: Math.acos(Math.max(-1, Math.min(1, c))) * 206264.806, rSun: EV_SUN_R_AS / ds, rP: EV_PLANET_R_KM[key] / (dp * AU / 1e3) * 206264.806, front: dp < ds };
}

/* Période synodique (jours) : sert seulement à régler le pas de la recherche grossière des conjonctions inférieures. */
const EV_SYNODIC_D = { mercury: 115.88, venus: 583.92 };

/* Dates (temps civil, jd) des conjonctions inférieures en longitude héliocentrique entre jd0 et jd1 : la planète
   rattrape la Terre (sa longitude héliocentrique, toujours plus rapide, dépasse celle de la Terre). Pas d'un sixième
   de période synodique (l'écart angulaire tourne de 60° en moyenne, toujours moins de 180°), puis sécante. */
function evInferiorConjunctions(key, jd0, jd1) {
  const T = jd => (jd - JD_J2000) / 36525, g = jd => {
    const st = solarSystemAt(T(jd), null, 0), e = st.earth, p = st.planets[key].pos;
    let d = Math.atan2(p[1], p[0]) - Math.atan2(e[1], e[0]);
    while (d > Math.PI) d -= 2 * Math.PI;
    while (d <= -Math.PI) d += 2 * Math.PI;
    return d;
  };
  const step = EV_SYNODIC_D[key] / 6, out = [];
  let ta = jd0 - step, ga = g(ta);
  for (let tb = ta + step; ta <= jd1 + step; ta = tb, tb += step) {
    const gb = g(tb);
    if (ga < 0 && gb >= 0 && gb - ga < Math.PI) {      /* passage par zéro (et non saut de −π à +π, qui est la conjonction supérieure) */
      let lo = ta, hi = tb, glo = ga, ghi = gb;
      for (let k = 0; k < 30 && hi - lo > 0.02; k++) {      /* au cinquantième de jour : il suffit de trouver le bon jour */
        const m = Math.min(hi - (hi - lo) * 0.05, Math.max(lo + (hi - lo) * 0.05, lo - glo * (hi - lo) / (ghi - glo))), gm = g(m);
        if (gm < 0) { lo = m; glo = gm; } else { hi = m; ghi = gm; }
      }
      out.push((lo + hi) / 2);
    }
    ga = gb;
  }
  return out;
}

/** Passages de la planète (mercury, venus) devant le Soleil entre jd0 et jd1 (temps civil) :
    [{ jd (milieu, temps civil), sep (″, distance minimale des centres), rSun (″) }].
    Même résultat que le balayage jour par jour (mêmes jours testés, même affinage), mais seulement autour des conjonctions
    inférieures : ailleurs la planète est à plus de 5° du Soleil ou derrière lui, et aucun passage n'est possible. */
function evTransits(key, jd0, jd1) {
  const ctx = {}, out = [], f = jd => evSep(key, jd, ctx).sep, memo = new Map();
  const fd = k => { let v = memo.get(k); if (v === undefined) { v = f(jd0 + k); memo.set(k, v); } return v; };      /* jour k de la grille jd0 + k */
  const kMax = Math.floor(jd1 - jd0), seen = new Set();
  for (const tc of evInferiorConjunctions(key, jd0, jd1)) {
    const kc = Math.round(tc - jd0);
    /* Conjonction lointaine : si la séparation, modelée par une parabole en carré de distance sur les trois jours qui
       l'entourent, reste au-dessus de 3600″ (1°), aucun jour de cette fenêtre ne peut donner un passage (il faut moins de
       1010″) : on ne la balaie pas. Le modèle (mouvement relatif rectiligne sur deux jours) est très en deçà de cet écart. */
    {
      const a = fd(kc - 1), b = fd(kc), c = fd(kc + 1), A = a * a, B = b * b, C = c * c, cu = (A + C) / 2 - B, li = (C - A) / 2;
      const est = cu > 0 ? B - li * li / (4 * cu) : 0;
      if (Math.min(a, b, c) > 3600 && est > 3600 * 3600) continue;
    }
    let k0 = kc - 3, k1 = kc + 3;
    while (k0 > -1 && fd(k0) < 18000) k0--;      /* fenêtre : jusqu'au premier jour de chaque côté où la planète est à plus de 5° */
    while (k1 < kMax && fd(k1) < 18000) k1++;
    for (let k = Math.max(1, k0 + 2); k <= Math.min(kMax, k1); k++) {      /* test du balayage d'origine au jour jd0 + k */
      if (seen.has(k)) continue;
      seen.add(k);
      const a = fd(k - 2), b = fd(k - 1), c = fd(k), jd = jd0 + k;
      if (!(b < a && b <= c && b < 18000)) continue;
      /* Conjonction (moins de 5°) : minimum affiné par la section dorée. Sauté si la séparation, modelée par une parabole
         en carré de distance sur les trois jours, ne descend pas sous 2000″ (un passage demande moins de 1010″ : rayon du Soleil, 976″ au plus, plus celui de la planète). */
      const A = a * a, B = b * b, C = c * c, cu = (A + C) / 2 - B, li = (C - A) / 2, est = cu > 0 ? B - li * li / (4 * cu) : 0;
      if (est > 2000 * 2000) continue;
      let lo = jd - 2, hi = jd; for (let n = 0; n < 40; n++) { const m1 = hi - (hi - lo) * 0.618, m2 = lo + (hi - lo) * 0.618; if (f(m1) < f(m2)) hi = m2; else lo = m1; }
      const t = (lo + hi) / 2, s = evSep(key, t, ctx);
      if (s.front && s.sep < s.rSun + s.rP) out.push({ jd: t, sep: s.sep, rSun: s.rSun });
    }
  }
  return out.sort((x, y) => x.jd - y.jd);
}
