/* S7 — vue « telle que la lumière nous arrive » (29_cone.js) : galaxies à la distance angulaire χ / (1 + z).
   Référence indépendante : astropy (LambdaCDM, H0 = 67,4, Ωm = 0,315, ΩΛ = 0,685, photons à 2,7255 K, 3,046 neutrinos sans masse,
   mêmes paramètres que la page), calculé le 12/11/2026 : distance comobile transverse et distance angulaire (Mpc). */
const { loadUnivers } = require('./_load');

const { PLANCK, buildCosmo, surveyLutOf } = loadUnivers({
  gen: ['data.js'],
  src: ['20_physics.js', '29_cone.js'],
});

let fails = 0;
const check = (ok, msg) => { console.log((ok ? 'OK    ' : 'ÉCHEC ') + msg); if (!ok) fails++; };
const REF = [[0.1, 434.1, 394.6], [0.5, 1951.3, 1300.9], [1.0, 3401.0, 1700.5], [2.0, 5311.2, 1770.4], [3.0, 6504.6, 1626.1]];
const ZMAX = 4.5, C = buildCosmo(PLANCK), now = surveyLutOf(C, ZMAX, false), cone = surveyLutOf(C, ZMAX, true);
const at = (L, z) => { const x = Math.log(1 + z) / Math.log(1 + ZMAX) * 1024, k = Math.min(Math.floor(x), 1023), f = x - k; return L[k] * (1 - f) + L[k + 1] * f; };
for (const [z, chi, da] of REF) {
  const a = at(now, z), b = at(cone, z);
  check(Math.abs(a / chi - 1) < 0.005 && Math.abs(b / da - 1) < 0.005, `z = ${z} : à cet instant ${a.toFixed(1)} Mpc (astropy ${chi}), quand la lumière est partie ${b.toFixed(1)} Mpc (astropy ${da})`);
}
{
  let best = [0, 0];
  for (let z = 0.5; z < 3; z += 0.001) { const d = at(cone, z); if (d > best[1]) best = [z, d]; }
  check(best[0] > 1.55 && best[0] < 1.63, `distance angulaire la plus grande à z = ${best[0].toFixed(3)} (${best[1].toFixed(0)} Mpc ; astropy : z = 1,588, 1794 Mpc)`);
}
check(at(cone, 0.001) / at(now, 0.001) > 0.998, 'tout près : les deux vues se confondent');
console.log(fails ? `\n${fails} échec(s)` : '\ncône de lumière : tout est vert');
process.exit(fails ? 1 : 0);
