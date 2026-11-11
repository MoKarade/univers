const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
vm.runInThisContext((rd('gen/data.js') + rd('gen/data2.js') + rd('gen/ephem.js') + rd('gen/data3.js') + rd('src/20_physics.js') + rd('src/30_gen.js').split('/* ====')[1].replace(/^/, '/* ====') + rd('src/25_future.js')).replace(/^const /gm, 'var '));
console.log('--- Soleil');
for (const t of [0, 1.1, 5.42, 7.0, 7.5, 7.587, 7.59, 7.7, 7.72, 7.75, 8.72, 20]) { const s = sunState(t); console.log('  +%s Ga : %s | L=%s R=%s (%s UA) T=%s K M=%s', t, s.phase, +s.L.toPrecision(3), +s.R.toPrecision(3), (s.R * R_SUN_AU).toFixed(3), Math.round(s.T), s.M.toFixed(3)); }
console.log('  engloutissement (Ga depuis aujourd\'hui) : Mercure %s, Vénus %s, Terre %s, Mars %s', engulfTime(0.387).toFixed(4), engulfTime(0.723).toFixed(4), engulfTime(1.0).toFixed(4), engulfTime(1.524));
console.log('--- Étoiles (modèle)');
const N = DATA.STARS_N, aux = b64ToBytes(DATA.STARS_AUX), hip = new Uint32Array(b64ToBytes(DATA.STARS_HIP).buffer), cnt = [0, 0, 0, 0], fates = [0, 0, 0, 0, 0]; let snSoon = 0;
for (let i = 0; i < N; i++) { const L = starLife(aux[i * 2] / 8 - 10, aux[i * 2 + 1] / 100 - 0.5, i, hip[i]); cnt[L[5]]++; fates[L[3]]++; if ((L[3] === 1 || L[3] === 3) && L[2] > 0 && L[2] < 10) snSoon++; }
console.log('  classes [naines, géantes, supergéantes, naines blanches] :', cnt, '| destins [0..4] :', fates, '| supernovas dans les 10 prochains Ma :', snSoon);
for (const l of DATA.STAR_LABELS.filter(l => ['Sirius', 'Bételgeuse', 'Étoile de Barnard', 'Arcturus', 'Rigel', 'Véga', 'Alpha du Centaure'].includes(l.n))) { const L = starLife(aux[l.i * 2] / 8 - 10, aux[l.i * 2 + 1] / 100 - 0.5, l.i, hip[l.i]); console.log('  %s : %s, %s M☉, naissance %s Ma, fin séq. princ. %s Ma, mort %s Ma, destin %s', l.n.padEnd(18), STAR_CLASS[L[5]], L[4].toFixed(1), Math.round(L[0]), Math.round(L[1]), +L[2].toPrecision(3), L[3]); }
console.log('--- Mouvement des étoiles');
const geo = new Uint16Array(b64ToBytes(DATA.STARS_GEO).buffer), p = new Float32Array(N * 3);
for (let i = 0; i < N; i++) { const lon = geo[i * 3] / 65535 * TAU, lat = (geo[i * 3 + 1] / 65535 - 0.5) * Math.PI, d = Math.pow(10, geo[i * 3 + 2] / 65535 * 5.5 - 1), cl = Math.cos(lat); p.set([d * cl * Math.cos(lon), d * cl * Math.sin(lon), d * Math.sin(lat)], i * 3); }
const sunGal0 = DATA.SGRA_GAL.map(x => -x * GAL.R0); let t0 = Date.now(); const K = initStarKin(p, N, sunGal0); console.log('  init %s ms ; Soleil : rayon guide %s kpc, période épicyclique %s Ma, verticale %s Ma', Date.now() - t0, K.sun[0].toFixed(2), (TAU / K.sun[2] * 1000).toFixed(0), (TAU / K.sun[7] * 1000).toFixed(0));
const out = new Float32Array(N * 3), dist = i => Math.hypot(out[i * 3], out[i * 3 + 1], out[i * 3 + 2]);
for (const nm of ['Gliese 710', 'Alpha du Centaure', 'Étoile de Barnard']) { const l = DATA.STAR_LABELS.find(l => l.n === nm); let best = [0, 1e9]; for (let t = -5e4; t <= 2e6; t += 250) { starPositions(K, t, t / 1e9, out, l.i, l.i + 1); const d = dist(l.i); if (d < best[1]) best = [t, d]; } console.log('  %s : au plus près dans %s ans, à %s al (%s UA)', nm, Math.round(best[0]), best[1].toFixed(3), Math.round(best[1] * 63241)); }
t0 = Date.now(); starPositions(K, 1e5, 1e-4, out); const tl = Date.now() - t0; t0 = Date.now(); starPositions(K, 2e8, 0.2, out); console.log('  mise à jour de %s étoiles : %s ms (ligne droite), %s ms (orbites)', N, tl, Date.now() - t0);
let far = 0; for (let i = 0; i < N; i++) if (dist(i) > 3000) far++; console.log('  dans 200 Ma : %s %% des étoiles sont à plus de 3 000 al du Soleil', (far / N * 100).toFixed(0));
const sg = [0, 0, 0]; let rmin = 99, rmax = 0; for (let t = 0; t < 0.4; t += 0.002) { sunGalAt(K, t, sg); const R = Math.hypot(sg[0], sg[1]); rmin = Math.min(rmin, R); rmax = Math.max(rmax, R); } console.log('  orbite du Soleil : entre %s et %s kpc du centre', rmin.toFixed(2), rmax.toFixed(2));
console.log('--- Andromède');
const C = buildCosmo(PLANCK);
for (const vt of [undefined, 17, 40, 57, 100]) { t0 = Date.now(); const O = andromedaOrbit(C, vt); console.log('  v transverse %s km/s (radiale %s) : passages %s | fusion %s | %s ms', O.vt.toFixed(1), O.vr.toFixed(1), O.peri.slice(0, 3).map(q => '+' + q[0].toFixed(2) + ' Ga à ' + q[1].toFixed(0) + ' kpc').join(', ') || 'aucun', O.tMerge ? '+' + O.tMerge.toFixed(2) + ' Ga' : 'pas avant 14 Ga', Date.now() - t0); }
