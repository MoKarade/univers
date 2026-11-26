/* Lunes galiléennes en gravité mutuelle (24_moons.js) contre JPL Horizons, de −50 à +50 ans. */
const fs = require('fs');
const path = require('path');
const { loadUnivers } = require('./_load');

const U = loadUnivers({
  gen: ['data.js', 'lunes.js', 'data2.js', 'ephem.js'],
  src: ['20_physics.js', '21_nbody.js', '22_smallbody.js', '24_moons.js'],
});
const { DATA, MO_JUP, moStepper } = U;

const R = JSON.parse(fs.readFileSync(path.join(__dirname, 'lunes_ref.json'), 'utf8'));
let fail = 0;
const ok = (c, m) => { console.log((c ? 'ok   ' : 'ÉCHEC') + ' ' + m); if (!c) fail++; };
const N = MO_JUP.names;
const s0 = U.Float64Array.from(DATA.LUNES_JUP.s); /* départ calé sur Horizons à −10 et +10 ans (ajuste_lunes.js) ; −50, +1 et +50 ans sont des contrôles indépendants */
const jd0 = R.epoch.io.jd;
const wanted = Object.keys(R.checks).sort().filter(d => (process.argv[2] ? d === process.argv[2] : true));
const back = wanted.filter(d => R.checks[d].io.jd < jd0).sort((a, b) => R.checks[b].io.jd - R.checks[a].io.jd);
const fwd = wanted.filter(d => R.checks[d].io.jd >= jd0).sort((a, b) => R.checks[a].io.jd - R.checks[b].io.jd);

for (const branch of [back, fwd]) {
  if (!branch.length) continue;
  const y = { jd: jd0, s: U.Float64Array.from(s0) };
  for (const d of branch) {
    const t0 = Date.now();
    moStepper(MO_JUP, y, R.checks[d].io.jd).run(Infinity);
    const e = N.map((n, i) => {
      const p = R.checks[d][n].r;
      return [n, Math.hypot(y.s[i * 6] - p[0], y.s[i * 6 + 1] - p[1], y.s[i * 6 + 2] - p[2])];
    });
    const yrs = (R.checks[d].io.jd - jd0) / 365.25;
    const tol = Math.abs(yrs) <= 10.5 ? 300 : 25000; /* à ±50 ans, écart mesuré ≈ 18 000 km pour Io (2,5° sur son orbite) : un terme lent manque au modèle (non identifié) ; la page ne garde le calcul que sur ±10 ans */
    ok(e.every(([, k]) => k < tol), `${d} (${yrs.toFixed(0)} ans, ${Date.now() - t0} ms) : écart à Horizons ` + e.map(([n, k]) => n + ' ' + Math.round(k) + ' km').join(', ') + ` (tolérance ${Math.round(tol)} km)`);
  }
}

process.exit(fail ? 1 : 0);
