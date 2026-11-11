const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
vm.runInThisContext((rd('gen/data.js') + rd('gen/data2.js') + rd('gen/ephem.js') + rd('gen/data3.js') + rd('src/20_physics.js') + rd('src/30_gen.js').split('/* ====')[1].replace(/^/, '/* ====') + rd('src/25_future.js')).replace(/^const /gm, 'var '));
let bad = 0; const ok = (c, m) => { if (!c) { bad++; console.log('ECHEC :', m); } }, st = new Float64Array(6), st2 = new Float64Array(6), kv = [0, 0, 0];
// 1) orbite circulaire à 10 000 UA : période d'un million d'années, retour au point de départ
{ const r = [10000, 0, 0], v = [0, Math.sqrt(MU_SUN / 10000), 0], o = orbFromState(r, v, 0, MU_SUN), P = 2 * Math.PI / o.n; orbState(o, P, st); orbState(o, P / 4, st2);
  console.log('orbite circulaire a 10 000 UA : periode %s ans, retour a %s UA du depart, quart de tour en (%s, %s)', Math.round(P), Math.hypot(st[0] - 1e4, st[1], st[2]).toExponential(2), st2[0].toFixed(1), st2[1].toFixed(1));
  ok(Math.abs(P - 1e6) < 1, 'periode'); ok(Math.hypot(st[0] - 1e4, st[1], st[2]) < 1e-3, 'retour'); ok(Math.abs(st2[1] - 1e4) < 0.01 && Math.abs(st2[0]) < 0.01, 'quart de tour'); }
// 2) orbites quelconques, liées ou non : énergie et moment cinétique conservés, aller-retour dans le temps
{ const rng = makeRng(5); let dE = 0, dH = 0, dR = 0, nh = 0;
  for (let k = 0; k < 400; k++) { const d = rng.dir(), w = rng.dir(), rr = 2000 * Math.pow(50, rng()), r = [d[0] * rr, d[1] * rr, d[2] * rr], vv = Math.sqrt(MU_SUN / rr) * (0.2 + 1.6 * rng()), v = [w[0] * vv, w[1] * vv, w[2] * vv];
    const o = orbFromState(r, v, 0, MU_SUN), E0 = vv * vv / 2 - MU_SUN / rr, h0 = Math.hypot(r[1] * v[2] - r[2] * v[1], r[2] * v[0] - r[0] * v[2], r[0] * v[1] - r[1] * v[0]), t = (rng() - 0.5) * 2e6; if (o.hyp) nh++;
    orbState(o, t, st); const r1 = Math.hypot(st[0], st[1], st[2]), E1 = (st[3] * st[3] + st[4] * st[4] + st[5] * st[5]) / 2 - MU_SUN / r1, h1 = Math.hypot(st[1] * st[5] - st[2] * st[4], st[2] * st[3] - st[0] * st[5], st[0] * st[4] - st[1] * st[3]);
    dE = Math.max(dE, Math.abs(E1 / E0 - 1)); dH = Math.max(dH, Math.abs(h1 / h0 - 1)); const o2 = orbFromState([st[0], st[1], st[2]], [st[3], st[4], st[5]], t, MU_SUN); orbState(o2, 0, st2); dR = Math.max(dR, Math.hypot(st2[0] - r[0], st2[1] - r[1], st2[2] - r[2]) / rr); }
  console.log('400 orbites (%s hyperboliques) : energie conservee a %s, moment cinetique a %s, aller-retour a %s du rayon', nh, dE.toExponential(1), dH.toExponential(1), dR.toExponential(1)); ok(dE < 1e-6 && dH < 1e-6 && dR < 1e-5, 'conservation'); }
// 3) coup de vitesse : une étoile de 0,6 masse solaire à 14,5 km/s, comète à 1 000 UA de sa route, loin du Soleil
{ const en = { bS: [10000, 0, 0], u: [0, 1, 0], V: 14.5 / 4.740470, M: 0.6 }, tau = starKick([11000, 0, 0], en, kv), ms = Math.hypot(kv[0], kv[1], kv[2]) * 4740.47;
  console.log('coup de vitesse a 1 000 UA de la route d une etoile de 0,6 masse solaire a 14,5 km/s : %s m/s (vers l etoile : %s)', ms.toFixed(1), kv[0] < 0); ok(ms > 60 && ms < 90 && kv[0] < 0 && Math.abs(tau) < 1e-9, 'coup de vitesse'); }
console.log(bad ? 'ECHECS : ' + bad : 'tout est bon'); process.exit(bad ? 1 : 0);
