/* Lot G (G1) : le Soleil autour du centre de masse, calculé dans la page à partir des positions des planètes (VSOP87)
   et des masses DE440, contre la position du Soleil donnée par JPL Horizons (DE440). */
const fs = require('fs');
const path = require('path');
const { loadUnivers } = require('./_load');

const { AU, solarSystemAt, sunBaryOffset } = loadUnivers({
  gen: ['data.js', 'data2.js', 'ephem.js'],
  src: ['20_physics.js', '21_nbody.js'],
});

const H = JSON.parse(fs.readFileSync(path.join(__dirname, 'nbody_ref.json'), 'utf8'));
const KM = AU / 1e3;
let fail = 0;
const all = Object.assign({ '2026-11-10': H.epoch }, H.checks);
for (const [d, R] of Object.entries(all)) {
  const st = solarSystemAt((R.sun.jd - 2451545) / 36525, null, 0), b = sunBaryOffset(st);
  /* Horizons : Soleil par rapport au barycentre ; ici les planètes sans Pluton ni astéroïdes (écart attendu : quelques centaines de km). */
  const e = Math.hypot(b[0] - R.sun.r[0], b[1] - R.sun.r[1], b[2] - R.sun.r[2]) * KM;
  const r = Math.hypot(...R.sun.r) * KM;
  const good = st.precise && e < 400;
  console.log((good ? 'ok   ' : 'ÉCHEC') + ` ${d} : Soleil à ${Math.round(Math.hypot(...b) * KM)} km du centre de masse (Horizons ${Math.round(r)} km), écart ${Math.round(e)} km`);
  if (!good) fail++;
}
process.exit(fail ? 1 : 0);
