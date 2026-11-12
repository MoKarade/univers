/* Lot G (G2) : table des orbites sur des millions d'années (build_long.js), lue par la page (nbLongState), contre :
   1) l'intégration directe du même calcul (21_nbody.js) à des dates prises entre deux points de la table ;
   2) les séries VSOP87 de la page vers ±3 500 ans, où la page passe de l'une à l'autre.
   Extrait de la table : app/test/long_extrait.bin (±200 000 ans, mêmes données que le fichier chargé par la page). */
const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
global.DATA = {};
vm.runInThisContext((rd('gen/data.js') + rd('gen/data2.js') + rd('gen/ephem.js') + rd('gen/nbody.js') + rd('src/20_physics.js') + rd('src/21_nbody.js') + "function b64ToBytes(s) { const bin = atob(s), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }").replace(/^const /gm, 'var ').replace(/^let NB_LONG/m, 'var NB_LONG'));
const b = fs.readFileSync(path.join(root, 'test/long_extrait.bin')), buf = b.buffer.slice(b.byteOffset, b.byteOffset + b.length);
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'ÉCHEC') + ' ' + m); if (!c) fail++; };
const lon = p => Math.atan2(p[1], p[0]), dAng = (a, c) => Math.abs(Math.atan2(Math.sin(a - c), Math.cos(a - c))) / DEG;
const KEYS = ['mercury', 'venus', 'emb', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune'];

/* 1) contre l'intégration directe, entre deux points de la table */
const TOL = { mercury: 0.5, venus: 0.5, emb: 0.5, mars: 0.5, jupiter: 0.6, saturn: 1.2, uranus: 0.5, neptune: 0.5 };
for (const yrs of [-61234.5, -3499.2, 4321.7, 47777.7]) {
  const S = nbFromData(), jd = S.jd + yrs * 365.25; nbAdvanceTo(S, jd, S.dt); const bb = nbBary(S), sun = [bb[0], bb[1], bb[2]];
  nbLongLoad(buf); const T = (jd - JD_J2000) / 36525, worst = [];
  for (const k of KEYS) { const i = S.names.indexOf(k), p = [bb[(i + 1) * 3] - sun[0], bb[(i + 1) * 3 + 1] - sun[1], bb[(i + 1) * 3 + 2] - sun[2]], q = nbLongState(k, T).pos; worst.push([k, dAng(lon(p), lon(q))]); }
  ok(worst.every(([k, d]) => d < TOL[k]), `${yrs} ans : longitude lue dans la table contre le calcul direct : ` + worst.map(([k, d]) => k + ' ' + d.toFixed(2) + '°').join(', '));
}
/* 2) raccord avec VSOP87 (la page passe de l'un à l'autre entre 3 000 et 4 000 ans) */
for (const yrs of [-3000, 3000]) {
  const T = yrs / 100 + 0.27, st = solarSystemAt(T, null, 0); nbLongLoad(buf); const w = [];
  for (const k of KEYS.filter(k => k !== 'emb')) w.push([k, dAng(lon(st.planets[k].pos), lon(nbLongState(k, T).pos))]);
  ok(w.every(([, d]) => d < 1.5), `${yrs} ans : table contre VSOP87 : ` + w.map(([k, d]) => k + ' ' + d.toFixed(2) + '°').join(', '));
}
process.exit(fail ? 1 : 0);
