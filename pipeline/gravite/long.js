#!/usr/bin/env node
/* Lot G (G2) : intégration longue du système solaire, à partir de l'état calé sur DE440 (app/gen/nbody.js).

   Usage : node pipeline/gravite/long.js <sens +1|-1> <durée en millions d'années> <sortie sans extension>
   Écrit :
     <sortie>.bin  : points de reprise tous les 10 000 ans, Float64 : jd, puis Q (N×3) et V (N×3) ;
                     la page repart du plus proche et intègre le reste (≤ 5 000 ans, < 1 s).
     <sortie>.json : éléments héliocentriques tous les 1 000 ans (a en UA, e, i en degrés) de chaque corps,
                     pour les contrôles (comparaison à Laskar et al. 2004).
     <sortie>.el   : Float32, tous les 1 000 ans, pour chaque corps : a (UA), e, i, Ω, ϖ, λ (radians, écliptique J2000),
                     λ = longitude moyenne ; sert à l'affichage des orbites dans la page (build_long.js).
     <sortie>.ljs  : Float32, λ de Jupiter puis de Saturne aux 3 quarts intermédiaires de chaque millier d'années.
   Durée : environ 3 minutes par million d'années sur le PC de Marc [mesuré : 18 ms par siècle]. */
const fs = require('fs'), vm = require('vm'), path = require('path'), app = path.join(__dirname, '..', '..', 'app');
const rd = f => fs.readFileSync(path.join(app, f), 'utf8');
global.DATA = {};
vm.runInThisContext((rd('gen/nbody.js') + rd('src/20_physics.js').split('/* ----')[0] + rd('src/21_nbody.js')).replace(/^const /gm, 'var '));
const dir = +process.argv[2] >= 0 ? 1 : -1, myr = +process.argv[3], out = process.argv[4];
if (!(myr > 0) || !out) { console.error('usage : long.js <+1|-1> <Ma> <sortie>'); process.exit(2); }
const YR = 365.25, S = nbFromData(), N = S.N, dt = dir * S.dt, CK = 10000, EL = 1000;
const QSTEPS = Math.round(EL * YR / S.dt / 4), stepsPerEl = 4 * QSTEPS, nEl = Math.round(myr * 1e6 / EL), perCk = CK / EL;
const ck = [], elb = [], lq = [], el = { names: S.names, dtYears: dir * EL, dtDays: dir * stepsPerEl * S.dt, jd0: S.jd, a: [], e: [], i: [] };

/* Longitudes moyennes de Jupiter et Saturne (mêmes formules qu'elements). */
function lamJS() { const out = []; let px = 0, py = 0, pz = 0; for (let k = 0; k < N; k++) { px += S.gm[k] * S.V[k * 3]; py += S.gm[k] * S.V[k * 3 + 1]; pz += S.gm[k] * S.V[k * 3 + 2]; }
  for (const k of [4, 5]) { const mu = NB_GM_SUN + S.gm[k], r = [S.Q[k * 3], S.Q[k * 3 + 1], S.Q[k * 3 + 2]], v = [S.V[k * 3] + px / NB_GM_SUN, S.V[k * 3 + 1] + py / NB_GM_SUN, S.V[k * 3 + 2] + pz / NB_GM_SUN];
    const rn = Math.hypot(...r), v2 = v[0] ** 2 + v[1] ** 2 + v[2] ** 2, rv = r[0] * v[0] + r[1] * v[1] + r[2] * v[2], a = 1 / (2 / rn - v2 / mu), ev = r.map((x, c) => ((v2 - mu / rn) * x - rv * v[c]) / mu), e = Math.hypot(...ev);
    const h = [r[1] * v[2] - r[2] * v[1], r[2] * v[0] - r[0] * v[2], r[0] * v[1] - r[1] * v[0]], hn = Math.hypot(...h), inc = Math.acos(h[2] / hn), Om = Math.atan2(h[0], -h[1]);
    const w = Math.atan2(ev[2] / Math.sin(inc), ev[0] * Math.cos(Om) + ev[1] * Math.sin(Om)), om = Om + w, cE = (1 - rn / a) / e, sE = rv / (e * Math.sqrt(mu * a)), Ea = Math.atan2(sE, cE);
    out.push(om + Ea - e * Math.sin(Ea)); }
  return out; }
/* Éléments héliocentriques osculateurs (vitesse héliocentrique = vitesse barycentrique − vitesse du Soleil). */
function elements() {
  let px = 0, py = 0, pz = 0; for (let k = 0; k < N; k++) { px += S.gm[k] * S.V[k * 3]; py += S.gm[k] * S.V[k * 3 + 1]; pz += S.gm[k] * S.V[k * 3 + 2]; }
  const sv = [-px / NB_GM_SUN, -py / NB_GM_SUN, -pz / NB_GM_SUN], A = [], E = [], I = [];
  for (let k = 0; k < N; k++) {
    const mu = NB_GM_SUN + S.gm[k], r = [S.Q[k * 3], S.Q[k * 3 + 1], S.Q[k * 3 + 2]], v = [S.V[k * 3] - sv[0], S.V[k * 3 + 1] - sv[1], S.V[k * 3 + 2] - sv[2]];
    const rn = Math.hypot(...r), v2 = v[0] ** 2 + v[1] ** 2 + v[2] ** 2, rv = r[0] * v[0] + r[1] * v[1] + r[2] * v[2];
    const h = [r[1] * v[2] - r[2] * v[1], r[2] * v[0] - r[0] * v[2], r[0] * v[1] - r[1] * v[0]], hn = Math.hypot(...h);
    const ev = r.map((x, c) => ((v2 - mu / rn) * x - rv * v[c]) / mu);
    const a = 1 / (2 / rn - v2 / mu), e = Math.hypot(...ev), inc = Math.acos(h[2] / hn), Om = Math.atan2(h[0], -h[1]);
    A.push(+a.toPrecision(9)); E.push(+e.toPrecision(7)); I.push(+(inc * 180 / Math.PI).toPrecision(7));
    /* longitude du périhélie ϖ = Ω + ω et longitude moyenne λ = ϖ + M */
    const nx = Math.cos(Om), ny = Math.sin(Om), w = Math.atan2((ev[2]) / Math.sin(inc || 1e-12), ev[0] * nx + ev[1] * ny), om = inc > 1e-9 ? Om + w : Math.atan2(ev[1], ev[0]);
    const cE = (1 - rn / a) / e, sE = rv / (e * Math.sqrt(mu * a)), Ea = Math.atan2(sE, cE), M = Ea - e * Math.sin(Ea);
    elb.push(a, e, inc, Om, om, om + M);
  }
  el.a.push(A); el.e.push(E); el.i.push(I);
}
const t0 = Date.now(), save = () => {
  const buf = new Float64Array(ck.length * (1 + 6 * N)); ck.forEach((c, j) => buf.set(c, j * (1 + 6 * N)));
  fs.writeFileSync(out + '.bin', Buffer.from(buf.buffer)); fs.writeFileSync(out + '.json', JSON.stringify(el)); fs.writeFileSync(out + '.el', Buffer.from(Float32Array.from(elb).buffer)); fs.writeFileSync(out + '.ljs', Buffer.from(Float32Array.from(lq).buffer));
};
const snap = () => { const c = new Float64Array(1 + 6 * N); c[0] = S.jd; c.set(S.Q, 1); c.set(S.V, 1 + 3 * N); ck.push(c); };
snap(); elements();
for (let j = 1; j <= nEl; j++) {
  for (let q = 1; q < 4; q++) { nbStep(S, dt, QSTEPS); lq.push(...lamJS()); }      /* Jupiter et Saturne tous les 250 ans : leur « grande inégalité » (≈ 900 ans) */
  nbStep(S, dt, QSTEPS);
  elements(); if (j % perCk === 0) snap();
  if (j % 1000 === 0) { save(); console.log(`${(j * EL / 1e6).toFixed(0)} Ma sur ${myr}, ${((Date.now() - t0) / 60000).toFixed(1)} min, énergie ${nbEnergy(S).toExponential(10)}`); }
}
save(); console.log('fini', out, ((Date.now() - t0) / 60000).toFixed(1), 'min');
