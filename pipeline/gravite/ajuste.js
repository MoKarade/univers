#!/usr/bin/env node
/* Lot G (G2) : calage du calcul à N corps sur l'éphéméride JPL DE440, puis écriture de app/gen/nbody.js.

   Pourquoi un calage : le pas de 4 jours de l'intégrateur de Wisdom et Holman déplace légèrement
   le mouvement moyen des planètes intérieures (surtout Mercure). Comme Laskar et al. 2004
   (A&A 428, 261) l'ont fait pour leur solution à long terme, on ajuste la vitesse de départ de
   chaque corps (un facteur par corps, ≈ 10⁻⁶ pour Mercure, ≤ 10⁻⁷ ailleurs) pour que la
   longitude calculée suive DE440 de 1650 à 2450. Les autres dates de nbody_ref.json servent de
   contrôle indépendant (app/test/nbody.test.js).

   Usage : node pipeline/gravite/ajuste.js   (lit app/test/nbody_ref.json, écrit app/gen/nbody.js) */
const fs = require('fs'), vm = require('vm'), path = require('path'), app = path.join(__dirname, '..', '..', 'app');
const rd = f => fs.readFileSync(path.join(app, f), 'utf8');
vm.runInThisContext((rd('src/20_physics.js').split('/* ----')[0] + rd('src/21_nbody.js')).replace(/^const /gm, 'var '));
const H = JSON.parse(rd('test/nbody_ref.json')), DT = 4, FIT = ['1650-01-01', '2450-01-01'], AS = 206264.806;
const lon = (p, s) => Math.atan2(p[1] - s[1], p[0] - s[0]);

/* État de départ : vitesses héliocentriques multipliées par (1 + s_i). */
function start(sc) {
  const S = nbCreate(H.epoch, H.epoch.sun.jd), vs = H.epoch.sun.v;
  for (let i = 0; i < S.N; i++) for (let c = 0; c < 3; c++) S.V[i * 3 + c] = vs[c] + (S.V[i * 3 + c] - vs[c]) * (1 + sc[i]);
  return S;
}
/* Écart de longitude (″) de chaque corps à une date, signé. */
function lonErr(sc, d) {
  const S = nbAdvanceTo(start(sc), H.checks[d].sun.jd, DT), b = nbBary(S);
  return S.names.map((k, i) => { const e = lon([b[(i + 1) * 3], b[(i + 1) * 3 + 1]], b) - lon(H.checks[d][k].r, H.checks[d].sun.r); return Math.atan2(Math.sin(e), Math.cos(e)) * AS; });
}
/* dλ/dt par unité de s : n ∝ a^(−3/2) et 1/a = 2/r − v²/μ donnent dn/n = −3 (a v²/μ) s. */
const gain = NB_BODIES.map(([k]) => {
  const p = H.epoch[k].r.map((x, c) => x - H.epoch.sun.r[c]), v = H.epoch[k].v.map((x, c) => x - H.epoch.sun.v[c]);
  const r = Math.hypot(...p), v2 = v.reduce((a, b) => a + b * b, 0), a = 1 / (2 / r - v2 / NB_GM_SUN);
  return 3 * Math.sqrt(NB_GM_SUN / a ** 3) * AS * a * v2 / NB_GM_SUN;
});
let sc = new Array(NB_BODIES.length).fill(0);
const span = H.checks[FIT[1]].sun.jd - H.checks[FIT[0]].sun.jd;
for (let it = 0; it < 5; it++) {
  const e0 = lonErr(sc, FIT[0]), e1 = lonErr(sc, FIT[1]);
  console.log('passe', it, NB_BODIES.map(([k], i) => `${k} ${e0[i].toFixed(1)}/${e1[i].toFixed(1)}″`).join(' '));
  sc = sc.map((s, i) => s + (e1[i] - e0[i]) / span / gain[i]);
}
const S = start(sc), r6 = x => +x.toPrecision(17);
const out = { jd: S.jd, dt: DT, names: S.names, gm: Array.from(S.gm), Q: Array.from(S.Q, r6), V: Array.from(S.V, r6), scale: sc.map(x => +x.toPrecision(6)),
  src: 'JPL Horizons (DE440), ' + H.epoch.sun.jd + ' TDB ; vitesses calées sur DE440 de 1650 à 2450 (pipeline/gravite/ajuste.js)' };
fs.writeFileSync(path.join(app, 'gen', 'nbody.js'), 'Object.assign(DATA, { NB: ' + JSON.stringify(out) + ' });\n');
console.log('écrit app/gen/nbody.js ; facteurs', out.scale.join(' '));
