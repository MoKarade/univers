/* Compléments physiques : solveurs de Kepler haute/basse excentricité, comètes (1P/Halley vs JPL Horizons + 1 658 comètes),
   orbite du Grand Nuage de Magellan (frottement dynamique) et cinématique des 200 000 étoiles Gaia. */
const fs = require('fs');
const path = require('path');
const { loadUnivers } = require('./_load');

const {
  DATA, TAU, DEG, GAL, KMS_LY_YR, b64ToBytes,
  keplerHigh, keplerE, decodeComets, updateComets,
  lmcOrbit, andromedaAt, initStarKin, starPositions,
} = loadUnivers({
  gen: ['data.js', 'data3.js', 'data4.js', 'data8.js'],
  src: ['20_physics.js', '25_future.js', '26_orbits.js', '30_gen.js'],
});

const petitsRef = JSON.parse(fs.readFileSync(path.join(__dirname, 'petits_ref.json'), 'utf8'));
let fail = 0;
const check = (cond, msg) => {
  console.log((cond ? 'OK    ' : 'ÉCHEC ') + msg);
  if (!cond) fail++;
};

const norm = v => Math.hypot(v[0], v[1], v[2]);
const sepArcsec = (a, b) =>
  Math.acos(Math.max(-1, Math.min(1, (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (norm(a) * norm(b))))) / DEG * 3600;

/* 1) Solveurs de Kepler */
let worst = 0;
for (const e of [0.31, 0.6, 0.9, 0.97, 0.995, 0.9995]) {
  for (let k = -2000; k <= 2000; k++) {
    const M = k * 0.0031 + (k % 7) * 1e-5;
    const E = keplerHigh(M, e);
    let m = M % TAU;
    if (m > Math.PI) m -= TAU;
    if (m < -Math.PI) m += TAU;
    const err = Math.abs(E - e * Math.sin(E) - m);
    if (!Number.isFinite(err)) worst = Infinity;
    else if (err > worst) worst = err;
  }
}
let worstE = 0;
for (const e of [0, 0.1, 0.29]) {
  for (let k = -500; k <= 500; k++) {
    const M = k * 0.012;
    const E = keplerE(M, e);
    const err = Math.abs(E - e * Math.sin(E) - M);
    if (!Number.isFinite(err)) worstE = Infinity;
    else if (err > worstE) worstE = err;
  }
}
const parityOk = keplerHigh(0, 0.9995) === 0 && Math.abs(keplerHigh(-0.5, 0.99) + keplerHigh(0.5, 0.99)) < 1e-14;
check(
  Number.isFinite(worst) && worst < 1e-12 && Number.isFinite(worstE) && worstE < 1e-12 && parityOk,
  `équation de Kepler : résidu max keplerHigh ${worst.toExponential(1)} rad, keplerE ${worstE.toExponential(1)} rad (< 1e-12), parité OK`
);

/* 2) Comètes : 1P/Halley contre JPL Horizons (COM_FIX) + 3 nommées périhélie/aphélie + 1 658 comètes */
const C = decodeComets();
const nm = DATA.COM_NAMES.split('|');
check(C.N === DATA.COM_N && C.N > 1600, `catalogue comètes décodé : ${C.N} comètes`);

const hRef = petitsRef.comets['1P/Halley'].state;
const iHal = nm.indexOf('1P/Halley');
updateComets(C, hRef.jd - 2451545);
const pHal = iHal >= 0 ? [C.pos[iHal * 3], C.pos[iHal * 3 + 1], C.pos[iHal * 3 + 2]] : [NaN, NaN, NaN];
const halSep = sepArcsec(pHal, hRef.r);
const halDr = Math.abs(norm(pHal) - norm(hRef.r));
check(
  iHal >= 0 && Number.isFinite(halSep) && halSep < 1.0 && Number.isFinite(halDr) && halDr < 1e-4,
  `1P/Halley vs JPL Horizons (COM_FIX, JD ${hRef.jd}) : écart ${halSep.toFixed(3)}″ (< 1″), |Δr| ${halDr.toExponential(2)} UA (< 1e-4 UA)`
);

for (const k of ['1P/Halley', '2P/Encke', '67P/Churyumov-Gerasimenko']) {
  const i = nm.indexOf(k);
  if (i < 0) {
    check(false, `comète introuvable : ${k}`);
    continue;
  }
  const qExp = C.a[i] * (1 - C.e[i]);
  const QExp = C.a[i] * (1 + C.e[i]);
  updateComets(C, C.tp[i]);
  const rPeri = Math.hypot(C.pos[i * 3], C.pos[i * 3 + 1], C.pos[i * 3 + 2]);
  updateComets(C, C.tp[i] + Math.PI / C.n[i]);
  const rApo = Math.hypot(C.pos[i * 3], C.pos[i * 3 + 1], C.pos[i * 3 + 2]);
  const ePeri = Math.abs(rPeri - qExp);
  const eApo = Math.abs(rApo - QExp);
  check(
    Number.isFinite(ePeri) && ePeri < 1e-5 && Number.isFinite(eApo) && eApo < 1e-4,
    `${k} : périhélie Δq=${ePeri.toExponential(1)} UA (< 1e-5), aphélie ΔQ=${eApo.toExponential(1)} UA (< 1e-4)`
  );
}

const days = 2461355.5 - 2451545;
updateComets(C, days);
let nanCom = 0;
let outCom = 0;
for (let i = 0; i < C.N; i++) {
  const ri = Math.hypot(C.pos[i * 3], C.pos[i * 3 + 1], C.pos[i * 3 + 2]);
  const qMin = C.a[i] * (1 - C.e[i]) * 0.999;
  const qMax = C.a[i] * (1 + C.e[i]) * 1.001;
  if (!Number.isFinite(ri)) nanCom++;
  else if (ri < qMin || ri > qMax) outCom++;
}
check(nanCom === 0 && outCom === 0, `${C.N} comètes à JD 2461355.5 : ${nanCom} NaN, ${outCom} hors enveloppe [q, Q]`);

/* 3) Grand Nuage de Magellan (lmcOrbit) */
const lmcByMs = {};
const p0 = [0, 0, 0];
for (const ms of [0.5, 1, 1.8]) {
  const L = lmcOrbit(ms);
  lmcByMs[ms] = L;
  andromedaAt(L, 0, p0);
  const d0Err = Math.hypot(p0[0] - DATA.LMC.pos[0], p0[1] - DATA.LMC.pos[1], p0[2] - DATA.LMC.pos[2]);
  let finOk = true;
  for (let i = 0; i < L.r.length; i++) if (!Number.isFinite(L.r[i])) finOk = false;
  let decPeri = L.peri.length >= 3;
  for (let k = 1; k < L.peri.length; k++) if (!(L.peri[k][1] < L.peri[k - 1][1])) decPeri = false;
  let decApo = L.apo.length >= 3;
  for (let k = 1; k < L.apo.length; k++) if (!(L.apo[k][1] < L.apo[k - 1][1])) decApo = false;
  console.log(`Grand Nuage (masse × ${ms}) : passages ${L.peri.slice(0, 4).map(p => '+' + p[0].toFixed(2) + ' Ga à ' + p[1].toFixed(0) + ' kpc').join(', ') || 'aucun avant 10 Ga'} | éloignements max ${L.apo.slice(0, 3).map(p => '+' + p[0].toFixed(2) + ' Ga à ' + p[1].toFixed(0) + ' kpc').join(', ')} | absorption ${L.tMerge ? '+' + L.tMerge.toFixed(2) + ' Ga' : 'pas avant 10 Ga'}`);
  check(
    d0Err < 1e-3 && finOk && decPeri && decApo,
    `LMC (masse × ${ms}) : départ à ${d0Err.toExponential(1)} kpc, fini, péricentres (${L.peri.length}) et apocentres (${L.apo.length}) décroissants`
  );
}
const L05 = lmcByMs[0.5];
const L10 = lmcByMs[1];
const L18 = lmcByMs[1.8];
check(
  L18.peri[0][0] < L10.peri[0][0] && L10.peri[0][0] < L05.peri[0][0] &&
  L18.peri[0][1] < L10.peri[0][1] && L10.peri[0][1] < L05.peri[0][1] &&
  L18.apo[0][1] < L10.apo[0][1] && L10.apo[0][1] < L05.apo[0][1] &&
  L18.tMerge > 1 && L18.tMerge < L10.tMerge && L10.tMerge < 7 && L05.tMerge === null,
  `LMC monotonicité en masse : 1er péricentre ${L18.peri[0][0].toFixed(2)} < ${L10.peri[0][0].toFixed(2)} < ${L05.peri[0][0].toFixed(2)} Ga, fusion ${L18.tMerge.toFixed(2)} < ${L10.tMerge.toFixed(2)} Ga / null`
);

/* 4) Cinématique Gaia (200 000 étoiles) */
const N = DATA.GAIA_N;
const geo = new Uint16Array(b64ToBytes(DATA.GAIA_GEO).buffer);
const vel = new Int8Array(b64ToBytes(DATA.GAIA_VEL).buffer);
const pos = new Float32Array(N * 3);
for (let i = 0; i < N; i++) {
  const lon = geo[i * 3] / 65535 * TAU;
  const lat = (geo[i * 3 + 1] / 65535 - 0.5) * Math.PI;
  const d = Math.pow(10, geo[i * 3 + 2] / 65535 * 5);
  pos.set([d * Math.cos(lat) * Math.cos(lon), d * Math.cos(lat) * Math.sin(lon), d * Math.sin(lat)], i * 3);
}
let t0 = Date.now();
const K = initStarKin(pos, N, DATA.SGRA_GAL.map(x => -x * GAL.R0), vel, 0.5, true);
const ti = Date.now() - t0;
const o = new Float32Array(N * 3);

starPositions(K, 0, 0, o);
let nonFin0 = 0;
let maxDiff0 = 0;
for (let j = 0; j < N * 3; j++) {
  if (!Number.isFinite(o[j])) nonFin0++;
  else maxDiff0 = Math.max(maxDiff0, Math.abs(o[j] - pos[j]));
}

t0 = Date.now();
starPositions(K, 1e5, 1e-4, o);
const t1 = Date.now() - t0;
let nonFin1 = 0;
let maxLinRel = 0;
for (let i = 0; i < N; i++) {
  const j = i * 3;
  const ox = o[j];
  const oy = o[j + 1];
  const oz = o[j + 2];
  if (!Number.isFinite(ox) || !Number.isFinite(oy) || !Number.isFinite(oz)) {
    nonFin1++;
    continue;
  }
  const ex = pos[j] + (vel[j] / 0.5) * KMS_LY_YR * 1e5;
  const ey = pos[j + 1] + (vel[j + 1] / 0.5) * KMS_LY_YR * 1e5;
  const ez = pos[j + 2] + (vel[j + 2] / 0.5) * KMS_LY_YR * 1e5;
  const refMag = Math.max(Math.hypot(ex, ey, ez), 1);
  const rel = Math.hypot(ox - ex, oy - ey, oz - ez) / refMag;
  if (rel > maxLinRel) maxLinRel = rel;
}

t0 = Date.now();
starPositions(K, 2e8, 0.2, o);
const t2 = Date.now() - t0;
let nonFin2 = 0;
let moved100 = 0;
for (let i = 0; i < N; i++) {
  const j = i * 3;
  if (!Number.isFinite(o[j]) || !Number.isFinite(o[j + 1]) || !Number.isFinite(o[j + 2])) {
    nonFin2++;
    continue;
  }
  if (Math.hypot(o[j] - pos[j], o[j + 1] - pos[j + 1], o[j + 2] - pos[j + 2]) > 100) moved100++;
}

const v = Array.from(K.vkms).sort((a, b) => a - b);
const vMin = v[0];
const vMed = v[N >> 1];
console.log(`Gaia : ${N} étoiles | préparation ${ti} ms | déplacement en ligne droite ${t1} ms, sur orbites galactiques ${t2} ms | vitesse médiane ${vMed.toFixed(1)} km/s`);
check(
  N === 200000 && nonFin0 === 0 && maxDiff0 === 0,
  `Gaia t=0 : ${N} étoiles, 0 non-fini, identité exacte (maxDiff=${maxDiff0})`
);
check(
  nonFin1 === 0 && maxLinRel < 1e-5,
  `Gaia t=+100 ka : 0 non-fini, mouvement rectiligne exact à ${maxLinRel.toExponential(2)} près (< 1e-5)`
);
check(
  nonFin2 === 0 && moved100 / N > 0.9 && vMin >= 0 && vMed > 20 && vMed < 70,
  `Gaia t=+200 Ma : 0 non-fini, ${(moved100 / N * 100).toFixed(1)} % déplacées > 100 al, vMed=${vMed.toFixed(1)} km/s (20..70)`
);

console.log(fail ? `\n${fail} échec(s)` : '\nKepler, comètes, LMC & Gaia : tout est vert');
process.exit(fail ? 1 : 0);
