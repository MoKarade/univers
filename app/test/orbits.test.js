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
  const r = msgs.pop(), Xr = Float64Array.from(K.gx0.subarray(0, n * 3)), Vr = Float64Array.from(K.gv0.subarray(0, n * 3)), S50 = orbSub(P, Xr, Vr, n); orbSteps(P, Xr, Vr, n, ORB_DT, 250, S50);
  let d = 0; for (let k = 0; k < n * 3; k++) d = Math.max(d, Math.abs(r.pos[k] - Xr[k]));
  check(Math.abs(r.t - 0.25) < 1e-9 && d < 1e-4, `Worker : réponse à +250 Ma, écart au calcul direct ${(d * 1e3).toFixed(4)} pc`);
  ctx.onmessage({ data: { goto: -0.1 } }); const r2 = msgs.pop(); const Xb = Float64Array.from(K.gx0.subarray(0, n * 3)), Vb = Float64Array.from(K.gv0.subarray(0, n * 3)); orbSteps(P, Xb, Vb, n, -ORB_DT, 100, S50);
  let d2 = 0; for (let k = 0; k < n * 3; k++) d2 = Math.max(d2, Math.abs(r2.pos[k] - Xb[k]));
  check(Math.abs(r2.t + 0.1) < 1e-9 && d2 < 1e-3, `Worker : retour à −100 Ma depuis le point de contrôle de départ, écart ${(d2 * 1e3).toFixed(4)} pc`); }

/* 4. Branchement : sans résultat exact, la page garde les épicycles ; avec, elle prend l'orbite exacte */
{ const g = [0, 0, 0], e = [0, 0, 0]; starOrbPos(K, 7, 0.3, g); epicyclePos(K.epi, 70, 0.3, e, 0); check(g.every((v, k) => v === e[k]), 'sans résultat exact : position identique aux épicycles (aucun changement pour les vieux navigateurs)');
  const pos = new Float32Array((N + 1) * 3), vel = new Float32Array((N + 1) * 3); pos[21] = 1; pos[22] = 2; pos[23] = 3; vel[21] = 100;
  K.orb = { on: true, n: N, res: { t: 0.3, pos, vel } }; starOrbPos(K, 7, 0.31, g);
  check(Math.abs(g[0] - (1 + 100 * 0.01 * ORB_KV)) < 1e-6 && g[1] === 2, 'avec résultat exact : position exacte, prolongée sur 10 Ma par la vitesse');
  starOrbPos(K, 7, 0.5, g); epicyclePos(K.epi, 70, 0.5, e, 0); check(g.every((v, k) => v === e[k]), 'résultat trop ancien (200 Ma d\'écart) : retour aux épicycles');
  K.orb.on = false; starOrbPos(K, 7, 0.3, g); epicyclePos(K.epi, 70, 0.3, e, 0); check(g.every((v, k) => v === e[k]), 'matière noire retirée : épicycles (le temps affiché n\'est plus le temps réel)'); K.orb = null; }

console.log(fails ? `\n${fails} échec(s)` : '\norbites exactes : tout est vert');
process.exit(fails ? 1 : 0);
