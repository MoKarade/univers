/* Lot G (G1) : le Soleil autour du centre de masse, calculé dans la page à partir des positions des planètes (VSOP87)
   et des masses DE440, contre la position du Soleil donnée par JPL Horizons (DE440). */
const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
vm.runInThisContext((rd('gen/data.js') + rd('gen/data2.js') + rd('gen/ephem.js') + rd('src/20_physics.js') + rd('src/21_nbody.js') + "function b64ToBytes(s) { const bin = atob(s), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }").replace(/^const /gm, 'var '));
const H = JSON.parse(rd('test/nbody_ref.json')), KM = AU / 1e3; let fail = 0;
const all = Object.assign({ '2026-11-10': H.epoch }, H.checks);
for (const [d, R] of Object.entries(all)) {
  const st = solarSystemAt((R.sun.jd - 2451545) / 36525, null, 0), b = sunBaryOffset(st);
  /* Horizons : Soleil par rapport au barycentre ; ici les planètes sans Pluton ni astéroïdes (écart attendu : quelques centaines de km). */
  const e = Math.hypot(b[0] - R.sun.r[0], b[1] - R.sun.r[1], b[2] - R.sun.r[2]) * KM, r = Math.hypot(...R.sun.r) * KM, good = st.precise ? e < 400 : true;
  console.log((good ? 'ok   ' : 'ÉCHEC') + ` ${d} : Soleil à ${Math.round(Math.hypot(...b) * KM)} km du centre de masse (Horizons ${Math.round(r)} km), écart ${Math.round(e)} km`);
  if (!good) fail++;
}
process.exit(fail ? 1 : 0);
