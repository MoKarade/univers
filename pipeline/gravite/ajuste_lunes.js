#!/usr/bin/env node
/* Lot G (lunes) : calage des quatre lunes galiléennes sur JPL Horizons, puis écriture de app/gen/lunes.js.

   Comme pour les planètes (ajuste.js) et comme les théories des lunes de Jupiter (Lainey et al. 2004), on ajuste
   la vitesse de départ de chaque lune (un facteur par lune) pour que sa longitude suive Horizons à −10 et +10 ans ;
   les lunes étant liées par leur résonance, l'ajustement est fait ensemble (méthode de Newton, jacobien numérique).
   Les dates à −50, +1 et +50 ans servent de contrôle indépendant (app/test/lunes.test.js).
   Usage : node pipeline/gravite/ajuste_lunes.js */
const fs = require('fs'), vm = require('vm'), path = require('path'), app = path.join(__dirname, '..', '..', 'app');
const rd = f => fs.readFileSync(path.join(app, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
vm.runInThisContext((rd('gen/data.js') + rd('gen/data2.js') + rd('gen/ephem.js') + rd('src/20_physics.js') + rd('src/21_nbody.js') + rd('src/22_smallbody.js') + rd('src/24_moons.js') + "function b64ToBytes(s) { const bin = atob(s), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }").replace(/^const /gm, 'var ').replace(/^let /gm, 'var '));
const R = JSON.parse(rd('test/lunes_ref.json')), N = MO_JUP.names, FIT = ['2016-11-10', '2036-11-10'];
const base = N.flatMap(n => R.epoch[n].r.concat(R.epoch[n].v.map(v => v * 86400)));
const start = sc => Float64Array.from(base.map((x, c) => (c % 6) >= 3 ? x * (1 + sc[Math.floor(c / 6)]) : x));
const lon = (x, y) => Math.atan2(y, x);
/* écarts de longitude (radians) : 4 lunes × 2 dates */
function errs(sc) { const out = [];
  for (const d of FIT) { const y = { jd: R.epoch.io.jd, s: start(sc) }; moStepper(MO_JUP, y, R.checks[d].io.jd).run(Infinity);
    N.forEach((n, i) => { const p = R.checks[d][n].r, e = lon(y.s[i * 6], y.s[i * 6 + 1]) - lon(p[0], p[1]); out.push(Math.atan2(Math.sin(e), Math.cos(e))); }); }
  return out; }
let sc = [0, 0, 0, 0];
for (let it = 0; it < 4; it++) {
  const e0 = errs(sc); console.log('passe', it, e0.map(e => (e * 206265).toFixed(0) + '″').join(' '));
  /* jacobien : pente de la dérive (écart à +10 ans moins écart à −10 ans) par lune */
  const J = [0, 1, 2, 3].map(j => { const s2 = sc.slice(); s2[j] += 1e-7; const e1 = errs(s2); return [0, 1, 2, 3].map(i => ((e1[4 + i] - e1[i]) - (e0[4 + i] - e0[i])) / 1e-7); });
  const b = [0, 1, 2, 3].map(i => -(e0[4 + i] - e0[i]));
  /* résolution 4 × 4 (Gauss) de M x = b, M[i][j] = J[j][i] */
  const M = [0, 1, 2, 3].map(i => [0, 1, 2, 3].map(j => J[j][i]).concat([b[i]]));
  for (let c = 0; c < 4; c++) { let p = c; for (let r = c + 1; r < 4; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r; [M[c], M[p]] = [M[p], M[c]];
    for (let r = 0; r < 4; r++) if (r !== c) { const f = M[r][c] / M[c][c]; for (let k = c; k < 5; k++) M[r][k] -= f * M[c][k]; } }
  sc = sc.map((s, i) => s + M[i][4] / M[i][i]);
}
const out = { jd: R.epoch.io.jd, names: N, s: Array.from(start(sc), x => +x.toPrecision(15)), scale: sc.map(x => +x.toPrecision(6)),
  src: 'JPL Horizons, ' + R.epoch.io.jd + ' TDB, centre de Jupiter, écliptique J2000, km et km/jour ; vitesses calées à −10 et +10 ans (pipeline/gravite/ajuste_lunes.js)' };
fs.writeFileSync(path.join(app, 'gen', 'lunes.js'), 'Object.assign(DATA, { LUNES_JUP: ' + JSON.stringify(out) + ' });\n');
console.log('écrit app/gen/lunes.js ; facteurs', out.scale.join(' '));
