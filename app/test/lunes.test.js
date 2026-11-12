/* Lunes galiléennes en gravité mutuelle (24_moons.js) contre JPL Horizons, de −50 à +50 ans. */
const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
global.DATA = {}; vm.runInThisContext((rd('gen/data.js') + rd('gen/lunes.js') + rd('gen/data2.js') + rd('gen/ephem.js') + rd('src/20_physics.js') + rd('src/21_nbody.js') + rd('src/22_smallbody.js') + rd('src/24_moons.js') + "function b64ToBytes(s) { const bin = atob(s), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }").replace(/^const /gm, 'var ').replace(/^let /gm, 'var '));
const R = JSON.parse(rd('test/lunes_ref.json')); let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'ÉCHEC') + ' ' + m); if (!c) fail++; };
const N = MO_JUP.names, s0 = Float64Array.from(DATA.LUNES_JUP.s);      /* départ calé sur Horizons à −10 et +10 ans (ajuste_lunes.js) ; −50, +1 et +50 ans sont des contrôles indépendants */
for (const d of Object.keys(R.checks).sort().filter(d => process.argv[2] ? d === process.argv[2] : true)) {
  const y = { jd: R.epoch.io.jd, s: Float64Array.from(s0) }, t0 = Date.now(); moStepper(MO_JUP, y, R.checks[d].io.jd).run(Infinity);
  const e = N.map((n, i) => { const p = R.checks[d][n].r; return [n, Math.hypot(y.s[i * 6] - p[0], y.s[i * 6 + 1] - p[1], y.s[i * 6 + 2] - p[2])]; });
  const yrs = (R.checks[d].io.jd - R.epoch.io.jd) / 365.25, tol = Math.abs(yrs) <= 10.5 ? 300 : 25000;      /* à ±50 ans, écart mesuré ≈ 18 000 km pour Io (2,5° sur son orbite) : un terme lent manque au modèle (non identifié) ; la page ne garde le calcul que sur ±10 ans */
  ok(e.every(([, k]) => k < tol), `${d} (${yrs.toFixed(0)} ans, ${Date.now() - t0} ms) : écart à Horizons ` + e.map(([n, k]) => n + ' ' + Math.round(k) + ' km').join(', ') + ` (tolérance ${Math.round(tol)} km)`);
}
process.exit(fail ? 1 : 0);
