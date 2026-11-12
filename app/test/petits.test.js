/* Lot G (G3) : astéroïdes et comètes tirés par les planètes, contre les prédictions publiées du JPL.
   Rapprochements de la Terre : CNEOS (cad.api) ; comète de Halley : périhélie 2061 de JPL Horizons.
   Références : app/test/petits_ref.json (pipeline/gravite/fetch_petits.py). */
const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
vm.runInThisContext((rd('gen/data.js') + rd('gen/data2.js') + rd('gen/ephem.js') + rd('src/20_physics.js') + rd('src/21_nbody.js') + rd('src/22_smallbody.js') + "function b64ToBytes(s) { const bin = atob(s), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }").replace(/^const /gm, 'var '));
const R = JSON.parse(rd('test/petits_ref.json')), KM = 149597870.7; let fail = 0;
const ok = (c, m) => { console.log((c ? 'ok   ' : 'ÉCHEC') + ' ' + m); if (!c) fail++; };
const st = s => ({ jd: s.jd, s: Float64Array.from(s.r.concat(s.v)) });

/* Rapprochements : date à 3 minutes près et distance à 0,1 % près de JPL Horizons (même solution d'orbite que l'état de départ).
   La liste CNEOS est donnée pour mémoire : pour 536531, elle vient d'une solution d'orbite plus ancienne (décalage de 16 min). */
for (const n of R.neo) {
  const t0 = Date.now(), A = sbApproaches(st(n.state), n.cad_jd_tdb + 2, 0.05), best = A.reduce((b, a) => !b || Math.abs(a.jd - n.hz_min_jd_tdb) < Math.abs(b.jd - n.hz_min_jd_tdb) ? a : b, null);
  if (!best) { ok(false, `${n.des} : aucun rapprochement trouvé`); continue; }
  const dtMin = (best.jd - n.hz_min_jd_tdb) * 1440, km = best.dist * KM, dd = km / n.hz_min_km - 1, cad = (best.jd - n.cad_jd_tdb) * 1440;
  ok(Math.abs(dtMin) < 3 && Math.abs(dd) < 0.001, `${n.des.padEnd(10)} ${n.cad_date} : ${Math.round(km)} km, à ${dtMin >= 0 ? '+' : ''}${dtMin.toFixed(1)} min et ${(dd * 100).toFixed(3)} % de Horizons (${Math.round(n.hz_min_km)} km) ; CNEOS ${Math.round(n.cad_dist_au * KM)} km, ${cad >= 0 ? '+' : ''}${cad.toFixed(1)} min [${Date.now() - t0} ms]`);
}

/* Comète de Halley : périhélie de 2061 (forces du gaz non calculées : écart de quelques jours attendu). */
{ const H = R.comets['1P/Halley'], y = st(H.state); let best = [9, 0];
  sbPropagate(y, H.tp_2061_jd_tdb + 60, (t, s) => { const r = Math.hypot(s[0], s[1], s[2]); if (r < best[0]) best = [r, t]; });
  const dd = best[1] - H.tp_2061_jd_tdb;
  ok(Math.abs(dd) < 5 && Math.abs(best[0] - H.q_au) < 0.002, `Halley : périhélie calculé à ${dd >= 0 ? '+' : ''}${dd.toFixed(2)} jours de JPL Horizons, à ${best[0].toFixed(4)} UA (JPL ${H.q_au.toFixed(4)})`); }

process.exit(fail ? 1 : 0);
