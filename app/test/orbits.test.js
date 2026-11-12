// S2 — orbites exactes des étoiles du catalogue principal (26_orbits.js), sur les vraies étoiles HYG.
const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
vm.runInThisContext((rd('gen/data.js') + rd('gen/data2.js') + rd('gen/ephem.js') + rd('gen/data3.js') + rd('src/20_physics.js') + rd('src/30_gen.js').split('/* ====')[1].replace(/^/, '/* ====') + rd('src/25_future.js') + rd('src/26_orbits.js')).replace(/^const /gm, 'var '));

let fails = 0;
const check = (ok, msg) => { console.log((ok ? 'OK    ' : 'ÉCHEC ') + msg); if (!ok) fails++; };

const N = DATA.STARS_N, geo = new Uint16Array(b64ToBytes(DATA.STARS_GEO).buffer), p = new Float32Array(N * 3);
for (let i = 0; i < N; i++) { const lon = geo[i * 3] / 65535 * TAU, lat = (geo[i * 3 + 1] / 65535 - 0.5) * Math.PI, d = Math.pow(10, geo[i * 3 + 2] / 65535 * 5.5 - 1), cl = Math.cos(lat); p.set([d * cl * Math.cos(lon), d * cl * Math.sin(lon), d * Math.sin(lat)], i * 3); }
const sunGal0 = DATA.SGRA_GAL.map(x => -x * GAL.R0), K = initStarKin(p, N, sunGal0), P = orbParams();
check(K.gx0 && K.gx0.length === N * 3 && Number.isFinite(K.gx0[0]), `état initial exact gardé pour les ${N} étoiles HYG`);

/* 1. Le Soleil : départ, énergie, période autour du centre */
{ const X = Float64Array.from(sunGal0), V = Float64Array.from(SUN_UVW), E0 = orbEnergy(P, ...X, ...V);
  let ang = Math.atan2(X[1], X[0]), turn = 0, tTurn = null, Emax = 0;
  for (let s = 1; s <= 1000; s++) { const a0 = Math.atan2(X[1], X[0]); orbSteps(P, X, V, 1, ORB_DT, 1); let da = Math.atan2(X[1], X[0]) - a0; if (da > Math.PI) da -= TAU; if (da < -Math.PI) da += TAU; turn += da;
    Emax = Math.max(Emax, Math.abs(orbEnergy(P, ...X, ...V) / E0 - 1)); if (tTurn === null && Math.abs(turn) >= TAU) tTurn = s * ORB_DT; }
  check(Emax < 1e-3, `Soleil : énergie conservée sur 1 Ga à ${(Emax * 100).toFixed(4)} % (seuil 0,1 %)`);
  // attendu : 2π R / v avec R0 = 8,2 kpc et v = 242 km/s, soit environ 208 Ma ; l'orbite exacte (un peu excentrique) doit en rester proche
  check(tTurn > 0.2 && tTurn < 0.25, `Soleil : un tour du centre en ${(tTurn * 1000).toFixed(0)} Ma (attendu 200 à 250 Ma : rayon guide ${K.sun[0].toFixed(2)} kpc, le Soleil allant plus vite que la vitesse circulaire)`); }

/* 2. Toutes les étoiles : énergie et aller-retour */
{ const n = N, X = Float64Array.from(K.gx0), V = Float64Array.from(K.gv0), E0 = new Float64Array(n);
  for (let k = 0; k < n; k++) E0[k] = orbEnergy(P, X[k * 3], X[k * 3 + 1], X[k * 3 + 2], V[k * 3], V[k * 3 + 1], V[k * 3 + 2]);
  const SUB = orbSub(P, X, V, n), t0 = Date.now(); orbSteps(P, X, V, n, ORB_DT, 1000, SUB); const ms = Date.now() - t0;
  const dE = []; for (let k = 0; k < n; k++) dE.push(Math.abs(orbEnergy(P, X[k * 3], X[k * 3 + 1], X[k * 3 + 2], V[k * 3], V[k * 3 + 1], V[k * 3 + 2]) / E0[k] - 1));
  dE.sort((a, b) => a - b); const q99 = dE[Math.floor(0.99 * (n - 1))], max = dE[n - 1];
  const q999 = dE[Math.floor(0.999 * (n - 1))];
  check(q999 < 1e-3 && max < 0.01, `${n} étoiles sur 1 Ga : énergie conservée à ${(q999 * 100).toFixed(4)} % pour 99,9 % d'entre elles (pire : ${(max * 100).toFixed(3)} %) ; ${ms} ms`);
  orbSteps(P, X, V, n, -ORB_DT, 1000, SUB); const back = []; for (let k = 0; k < n; k++) back.push(Math.hypot(X[k * 3] - K.gx0[k * 3], X[k * 3 + 1] - K.gx0[k * 3 + 1], X[k * 3 + 2] - K.gx0[k * 3 + 2]) * 1000); back.sort((a, b) => a - b);
  check(back[Math.floor(0.999 * (n - 1))] < 1, `aller 1 Ga puis retour : 99,9 % des étoiles reviennent à moins de 1 pc de leur départ (pire : ${back[n - 1].toFixed(1)} pc)`);
  console.log(`      sous-pas : ${SUB.filter(v => v > 1).length} étoiles découpées (2 à 32 sous-pas)`); }

/* 3. Le Worker (rejoué ici sans navigateur) : point de contrôle, demande remplacée, réponse à l'instant demandé */
{ const msgs = []; const ctx = { Uint8Array,  postMessage: m => msgs.push(m), setTimeout: f => f(), Float32Array, Float64Array, Map, Math, ORB_DT, ORB_CP, ORB_MAXCP };
  vm.createContext(ctx); vm.runInContext(String(orbAcc) + String(orbEnergy) + String(orbSub) + String(orbSteps) + '(' + orbWorkerMain.toString() + ')();', ctx);
  const n = 50, X = Float64Array.from(K.gx0.subarray(0, n * 3)), V = Float64Array.from(K.gv0.subarray(0, n * 3));
  ctx.onmessage({ data: { init: true, P, n, X, V } }); ctx.onmessage({ data: { goto: 0.25 } });
  const r = msgs.pop(), Xr = Float64Array.from(K.gx0.subarray(0, n * 3)), Vr = Float64Array.from(K.gv0.subarray(0, n * 3)), S50 = orbSub(P, Xr, Vr, n); orbSteps(P, Xr, Vr, n, ORB_DT, 250, S50, 0);
  let d = 0; for (let k = 0; k < n * 3; k++) d = Math.max(d, Math.abs(r.pos[k] - Xr[k]));
  check(Math.abs(r.t - 0.25) < 1e-9 && d < 1e-4, `Worker : réponse à +250 Ma, écart au calcul direct ${(d * 1e3).toFixed(4)} pc`);
  ctx.onmessage({ data: { goto: -0.1 } }); const r2 = msgs.pop(); const Xb = Float64Array.from(K.gx0.subarray(0, n * 3)), Vb = Float64Array.from(K.gv0.subarray(0, n * 3)); orbSteps(P, Xb, Vb, n, -ORB_DT, 100, S50, 0);
  let d2 = 0; for (let k = 0; k < n * 3; k++) d2 = Math.max(d2, Math.abs(r2.pos[k] - Xb[k]));
  check(Math.abs(r2.t + 0.1) < 1e-9 && d2 < 1e-3, `Worker : retour à −100 Ma depuis le point de contrôle de départ, écart ${(d2 * 1e3).toFixed(4)} pc`); }

/* 4. Branchement : sans résultat, épicycles ; avec résultat, orbite calculée prolongée au second ordre ; bascule avec écart */
{ const g = [0, 0, 0], e = [0, 0, 0]; starOrbPos(K, 7, 0.3, g); epicyclePos(K.epi, 70, 0.3, e, 0); check(g.every((v, k) => v === e[k]), 'sans résultat calculé : position identique aux épicycles (aucun changement pour les vieux navigateurs)');
  const n1 = N + 1, X = new Float64Array(n1 * 3), V = new Float64Array(n1 * 3); X.set(K.gx0); V.set(K.gv0); X.set(sunGal0, N * 3); V.set(SUN_UVW, N * 3);
  const SUBa = orbSub(P, X, V, n1); orbSteps(P, X, V, n1, ORB_DT, 200, SUBa, 0);      /* état calculé à +200 Ma */
  const res = { t: 0.2, pos: Float32Array.from(X), vel: Float32Array.from(V) }, posted = [];
  K.orb = { w: { postMessage: m => posted.push(m) }, n: N, P, res, acc: new Float32Array(n1 * 3).fill(NaN), want: null, sent: null, sentAt: 0, on: true, far: true, exact: false };
  orbRequest(K, 0.2, true, true); check(K.orb.exact && posted.length === 0, 'résultat à l\'instant affiché : orbite calculée choisie, aucune demande inutile');
  /* justesse du prolongement : comparé au calcul pas à pas, vu du Soleil (ce qui est dessiné) */
  for (const dMa of [2, 4, 5.9]) { const Xs = X.slice(), Vs = V.slice(); orbSteps(P, Xs, Vs, n1, ORB_DT, dMa, SUBa, 0.2); const tt = 0.2 + dMa / 1000, s = [0, 0, 0], err = []; starOrbSun(K, tt, s);
    for (let i = 0; i < N; i += 7) { starOrbPos(K, i, tt, g); err.push(Math.hypot(g[0] - s[0] - (Xs[i * 3] - Xs[N * 3]), g[1] - s[1] - (Xs[i * 3 + 1] - Xs[N * 3 + 1]), g[2] - s[2] - (Xs[i * 3 + 2] - Xs[N * 3 + 2])) * 1000); }
    err.sort((a, b) => a - b); const med = err[err.length >> 1], p99 = err[Math.floor(0.99 * (err.length - 1))];
    check(med < 10 && p99 < 60, `prolongement de ${dMa} Ma : écart vu du Soleil, médiane ${med.toFixed(1)} pc, 99 % ${p99.toFixed(0)} pc (seuils 10 et 60 pc ; épicycles à +200 Ma : ~265 pc)`); }
  orbRequest(K, 0.215, true, true); check(!K.orb.exact && posted.length === 1 && Math.abs(posted[0].goto - 0.215) < 1e-12, 'résultat à plus de 6 Ma : retour aux épicycles et nouvelle demande');
  K.orb.res = Object.assign({}, res, { t: 0.211 }); orbRequest(K, 0.215, true, true); check(!K.orb.exact, 'écart de bascule : revenu à 4 Ma, on reste en épicycles tant qu’on n’est pas sous 3 Ma (pas de scintillement)');
  K.orb.res = Object.assign({}, res, { t: 0.213 }); orbRequest(K, 0.215, true, true); check(K.orb.exact, 'écart de bascule : à 2 Ma, on repasse à l\'orbite calculée');
  orbRequest(K, 0.3, false, true); starOrbPos(K, 7, 0.3, g); epicyclePos(K.epi, 70, 0.3, e, 0); check(g.every((v, k) => v === e[k]), 'matière noire retirée : épicycles (le temps affiché n\'est plus le temps réel)');
  check(/approchée/.test(orbMotionText(K, 7, 0.3, true)) && /calculée pas à pas/.test(orbMotionText(K, 7, 0.3, false)), 'fiche : « approchée » pour Gaia, « calculée pas à pas dans un modèle » pour le catalogue principal');
  K.orb = null; }

/* 5. Référence indépendante de l'énergie : une orbite circulaire à 8,2 kpc et vCirc (formule de la courbe de rotation, 20_physics.js) reste circulaire */
{ const v = vCirc(GAL.R0, true), X = Float64Array.from([GAL.R0, 0, 0]), V = Float64Array.from([0, v, 0]); let dr = 0;
  for (let s = 0; s < 1000; s++) { orbSteps(P, X, V, 1, ORB_DT, 1); dr = Math.max(dr, Math.abs(Math.hypot(X[0], X[1]) - GAL.R0)); }
  check(dr < 0.002, `orbite circulaire à 8,2 kpc et ${v.toFixed(1)} km/s : rayon constant à ${(dr * 1000).toFixed(2)} pc près sur 1 Ga (forces et courbe de rotation d'accord)`); }

/* 6. Soleil dans la galaxie : calculé dans la page, à toute date, même résultat que le Worker */
{ const a = sunOrbAt(null, 0.2, [0, 0, 0]), X = Float64Array.from(sunGal0), V = Float64Array.from(SUN_UVW); orbSteps(P, X, V, 1, ORB_DT, 200, null, 0);
  const b = sunOrbAt(null, -0.35, [0, 0, 0]), c = sunOrbAt(null, 0.2, [0, 0, 0]);
  check(Math.hypot(a[0] - X[0], a[1] - X[1], a[2] - X[2]) < 1e-9 && Math.hypot(c[0] - a[0], c[1] - a[1], c[2] - a[2]) < 1e-6 && Number.isFinite(b[0]), `Soleil dans la galaxie à +200 Ma : (${a.map(v => v.toFixed(3)).join(', ')}) kpc, identique après un détour par −350 Ma`); }

/* 7. Rejoue la mesure de départ : à 50 Ma, l'écart des épicycles au calcul pas à pas dépasse 100 pc pour la médiane des étoiles */
{ const X = Float64Array.from(K.gx0), V = Float64Array.from(K.gv0), SB = orbSub(P, X, V, N); orbSteps(P, X, V, N, ORB_DT, 50, SB); const g = [0, 0, 0], e = [];
  for (let i = 0; i < N; i += 3) { epicyclePos(K.epi, i * 10, 0.05, g, 0); e.push(Math.hypot(g[0] - X[i * 3], g[1] - X[i * 3 + 1], g[2] - X[i * 3 + 2]) * 1000); } e.sort((a, b) => a - b);
  check(e[e.length >> 1] > 100, `épicycles contre calcul pas à pas à 50 Ma : écart médian ${e[e.length >> 1].toFixed(0)} pc (mesure de départ : 148 pc)`); }

console.log(fails ? `\n${fails} échec(s)` : '\norbites calculées : tout est vert');
/* Barre centrale (Dehnen 2000) : l'énergie n'est plus conservée, mais l'intégrale de Jacobi E − Ω_b L_z l'est (repère de la barre) */
{ const X = Float64Array.from([-4.5, 0.3, 0.05]), V = Float64Array.from([20, 180, 5]), J = (t) => { const Lz = X[0] * V[1] - X[1] * V[0]; return orbEnergy(P, X[0], X[1], X[2], V[0], V[1], V[2]) + barPhi(P, X[0], X[1], t) - (-P.Ob / 1.0227121650456) * Lz; };
  const j0 = J(0); let worst = 0, t = 0; for (let s = 0; s < 2000; s++) { orbSteps(P, X, V, 1, ORB_DT / 4, 1, null, t); t += ORB_DT / 4; worst = Math.max(worst, Math.abs(J(t) / j0 - 1)); }
  check(worst < 2e-3, `barre : intégrale de Jacobi conservée à ${worst.toExponential(1)} près sur 500 Ma (orbite à 4,5 kpc)`); }
/* Orientation : à t = 0 la barre est au plus profond à φ = 180° − 28° (bout proche aux longitudes positives) et tourne dans le sens du Soleil */
{ let best = 0, lo = Infinity; for (let d = 0; d < 360; d += 0.5) { const f = d * Math.PI / 180, v = barPhi(P, 3 * Math.cos(f), 3 * Math.sin(f), 0); if (v < lo) { lo = v; best = d; } }
  const LzSun = sunGal0[0] * SUN_UVW[1] - sunGal0[1] * SUN_UVW[0], d2 = Math.min(Math.abs(best - 152), Math.abs(best - 332));
  check(d2 < 1 && LzSun < 0 && P.Ob > 0, `barre : potentiel le plus bas à ${best}° (attendu 152° ou 332°), rotation dans le sens du disque`); }
process.exit(fails ? 1 : 0);
