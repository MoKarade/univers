/* Lot G : passages de Mercure et de Vénus devant le Soleil calculés par la page (VSOP87), contre le catalogue de la NASA
   (F. Espenak, 2026 à 2200). Même nombre de passages, milieu à 3 minutes près, distance minimale des centres à 5″ près.
   Le temps universel futur dépend de ΔT, extrapolé différemment ici et par la NASA : écart attendu d'environ une minute après 2100. */
const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
vm.runInThisContext((rd('gen/data.js') + rd('gen/data2.js') + rd('gen/ephem.js') + rd('src/20_physics.js') + rd('src/23_events.js') + "function b64ToBytes(s) { const bin = atob(s), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }").replace(/^const /gm, 'var '));
const R = JSON.parse(rd('test/transits_ref.json')); let fail = 0;
const ok = (c, m) => { console.log((c ? 'ok   ' : 'ÉCHEC') + ' ' + m); if (!c) fail++; };
const jdOf = (d, hm) => { const [y, m, dd] = d.split('-').map(Number), [h, mi] = hm.split(':').map(Number); return Date.UTC(y, m - 1, dd, h, mi) / 864e5 + 2440587.5; };
for (const key of ['mercury', 'venus']) {
  const t0 = Date.now(), calc = evTransits(key, jdOf('2026-01-01', '00:00'), jdOf('2200-12-31', '00:00')), ref = R[key];
  ok(calc.length === ref.length, `${key} : ${calc.length} passages calculés de 2026 à 2200, ${ref.length} au catalogue de la NASA [${Date.now() - t0} ms]`);
  for (const r of ref) {
    const j = jdOf(r.date, r.greatest_ut), c = calc.find(x => Math.abs(x.jd - j) < 1);
    if (!c) { ok(false, `${key} ${r.date} : non trouvé`); continue; }
    const dm = (c.jd - j) * 1440, ds = c.sep - r.sep_arcsec;
    ok(Math.abs(dm) < 3 && Math.abs(ds) < 5, `${key} ${r.date} ${r.greatest_ut} : milieu à ${dm >= 0 ? '+' : ''}${dm.toFixed(1)} min, centres à ${c.sep.toFixed(1)}″ (NASA ${r.sep_arcsec}″)`);
  }
}
process.exit(fail ? 1 : 0);
