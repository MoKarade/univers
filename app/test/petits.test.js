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

/* Trajectoire par morceaux (celle de la page) : mêmes positions que le calcul d'un seul tenant, rapprochement d'Apophis retrouvé. */
{ const A = R.neo.find(n => n.des === '99942'), y = st(A.state), T = sbTrack(y.jd, y.s, 3 * 365.25); let k = 0; const t0 = Date.now();
  while (!T.tick(8) && ++k < 1e5); let worst = 0;
  for (const dj of [-1000, -333.3, -1.7, 0.4, 500.25, 880.123, A.hz_min_jd_tdb - y.jd, A.hz_min_jd_tdb - y.jd + 0.01]) {
    const q = sbPropagate({ jd: y.jd, s: Float64Array.from(y.s) }, y.jd + dj), p = T.posAt(y.jd + dj);
    worst = Math.max(worst, Math.hypot(p[0] - q.s[0], p[1] - q.s[1], p[2] - q.s[2]) * KM); }
  const a = T.app.find(x => Math.abs(x.jd - A.hz_min_jd_tdb) < 0.01);
  ok(worst < 5 && a && Math.abs(a.dist * KM - A.hz_min_km) < 50, `trajectoire par morceaux (${k} tranches de 8 ms, ${Date.now() - t0} ms) : écart d'interpolation ${worst.toFixed(2)} km ; Apophis ${a ? Math.round(a.dist * KM) + ' km' : 'non trouvé'}`); }

/* État tiré des éléments (P, Q, e, M, n) : retrouve la position de Kepler. */
{ const e = 0.3, P = [1.2, 0.1, 0.05], Q = [-0.1, 1.1, 0.2], M = 1.1, n = 0.01, s0 = sbStateFromPQ(P, Q, e, M, n), s1 = sbStateFromPQ(P, Q, e, M + n * 1e-3, n), sm = sbStateFromPQ(P, Q, e, M - n * 1e-3, n);
  const E = keplerE(M, e), x = Math.cos(E) - e, yy = Math.sin(E), pos = [0, 1, 2].map(c => P[c] * x + Q[c] * yy), vfd = [0, 1, 2].map(c => (s1[c] - sm[c]) / 2e-3);
  ok(Math.hypot(...pos.map((v, c) => v - s0[c])) < 1e-12 && Math.hypot(...vfd.map((v, c) => v - s0[3 + c])) < 1e-8, 'état à partir des éléments : position et vitesse cohérentes'); }

/* Éléments osculateurs : ils redonnent l'état ; vitesse d'Hermite cohérente avec la position. */
{ const A = R.neo[0], s0 = Float64Array.from(A.state.r.concat(A.state.v)), o = sbOsc(s0), s1 = sbStateFromPQ(o.P, o.Q, o.e, o.M, o.n);
  ok(Math.hypot(s1[0] - s0[0], s1[1] - s0[1], s1[2] - s0[2]) * KM < 1e-3 && Math.hypot(s1[3] - s0[3], s1[4] - s0[4], s1[5] - s0[5]) < 1e-12, 'éléments osculateurs : retour à l’état de départ'); }

process.exit(fail ? 1 : 0);
