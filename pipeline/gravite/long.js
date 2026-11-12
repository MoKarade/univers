#!/usr/bin/env node
/* Lot G (G2) : intégration longue du système solaire, à partir de l'état calé sur DE440 (app/gen/nbody.js).

   Usage : node pipeline/gravite/long.js <sens +1|-1> <durée en millions d'années> <sortie sans extension>
   Écrit :
     <sortie>.bin  : points de reprise tous les 10 000 ans, Float64 : jd, puis Q (N×3) et V (N×3) ;
                     la page repart du plus proche et intègre le reste (≤ 5 000 ans, < 1 s).
     <sortie>.json : éléments héliocentriques tous les 1 000 ans (a en UA, e, i en degrés) de chaque corps,
                     pour les contrôles (comparaison à Laskar et al. 2004) et l'affichage des orbites.
   Durée : environ 3 minutes par million d'années sur le PC de Marc [mesuré : 18 ms par siècle]. */
const fs = require('fs'), vm = require('vm'), path = require('path'), app = path.join(__dirname, '..', '..', 'app');
const rd = f => fs.readFileSync(path.join(app, f), 'utf8');
global.DATA = {};
vm.runInThisContext((rd('gen/nbody.js') + rd('src/20_physics.js').split('/* ----')[0] + rd('src/21_nbody.js')).replace(/^const /gm, 'var '));
const dir = +process.argv[2] >= 0 ? 1 : -1, myr = +process.argv[3], out = process.argv[4];
if (!(myr > 0) || !out) { console.error('usage : long.js <+1|-1> <Ma> <sortie>'); process.exit(2); }
const YR = 365.25, S = nbFromData(), N = S.N, dt = dir * S.dt, CK = 10000, EL = 1000;
const stepsPerEl = Math.round(EL * YR / S.dt), nEl = Math.round(myr * 1e6 / EL), perCk = CK / EL;
const ck = [], el = { names: S.names, dtYears: dir * EL, dtDays: dir * stepsPerEl * S.dt, jd0: S.jd, a: [], e: [], i: [] };

/* Éléments héliocentriques osculateurs (vitesse héliocentrique = vitesse barycentrique − vitesse du Soleil). */
function elements() {
  let px = 0, py = 0, pz = 0; for (let k = 0; k < N; k++) { px += S.gm[k] * S.V[k * 3]; py += S.gm[k] * S.V[k * 3 + 1]; pz += S.gm[k] * S.V[k * 3 + 2]; }
  const sv = [-px / NB_GM_SUN, -py / NB_GM_SUN, -pz / NB_GM_SUN], A = [], E = [], I = [];
  for (let k = 0; k < N; k++) {
    const mu = NB_GM_SUN + S.gm[k], r = [S.Q[k * 3], S.Q[k * 3 + 1], S.Q[k * 3 + 2]], v = [S.V[k * 3] - sv[0], S.V[k * 3 + 1] - sv[1], S.V[k * 3 + 2] - sv[2]];
    const rn = Math.hypot(...r), v2 = v[0] ** 2 + v[1] ** 2 + v[2] ** 2, rv = r[0] * v[0] + r[1] * v[1] + r[2] * v[2];
    const h = [r[1] * v[2] - r[2] * v[1], r[2] * v[0] - r[0] * v[2], r[0] * v[1] - r[1] * v[0]], hn = Math.hypot(...h);
    const ev = r.map((x, c) => ((v2 - mu / rn) * x - rv * v[c]) / mu);
    A.push(+(1 / (2 / rn - v2 / mu)).toPrecision(9)); E.push(+Math.hypot(...ev).toPrecision(7)); I.push(+(Math.acos(h[2] / hn) * 180 / Math.PI).toPrecision(7));
  }
  el.a.push(A); el.e.push(E); el.i.push(I);
}
const t0 = Date.now(), save = () => {
  const buf = new Float64Array(ck.length * (1 + 6 * N)); ck.forEach((c, j) => buf.set(c, j * (1 + 6 * N)));
  fs.writeFileSync(out + '.bin', Buffer.from(buf.buffer)); fs.writeFileSync(out + '.json', JSON.stringify(el));
};
const snap = () => { const c = new Float64Array(1 + 6 * N); c[0] = S.jd; c.set(S.Q, 1); c.set(S.V, 1 + 3 * N); ck.push(c); };
snap(); elements();
for (let j = 1; j <= nEl; j++) {
  nbStep(S, dt, stepsPerEl);
  elements(); if (j % perCk === 0) snap();
  if (j % 1000 === 0) { save(); console.log(`${(j * EL / 1e6).toFixed(0)} Ma sur ${myr}, ${((Date.now() - t0) / 60000).toFixed(1)} min, énergie ${nbEnergy(S).toExponential(10)}`); }
}
save(); console.log('fini', out, ((Date.now() - t0) / 60000).toFixed(1), 'min');
