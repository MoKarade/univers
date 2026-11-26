/* Évolution future : Soleil (Schröder & Smith 2008, Mestel 1952), population stellaire (HYG + MIST v1.2),
   cinématique stellaire (épicycles + passages proches), et orbite d'Andromède. */
const { loadUnivers } = require('./_load');

const {
  DATA, TAU, GAL, R_SUN_AU, SUN_NOW, STAR_CLASS, b64ToBytes,
  sunState, engulfTime, starLife, initStarKin, starPositions,
  sunGalAt, buildCosmo, PLANCK, andromedaOrbit, andromedaAt,
} = loadUnivers({
  gen: ['data.js', 'data2.js', 'ephem.js', 'data3.js', 'sun_rgb.js', 'mist_life.js'],
  src: ['20_physics.js', '25_future.js', '26_orbits.js', '30_gen.js'],
});

let fail = 0;
const check = (cond, msg) => {
  console.log((cond ? 'OK    ' : 'ÉCHEC ') + msg);
  if (!cond) fail++;
};

console.log('--- Soleil');
const sunDates = [0, 1.1, 5.42, 7.0, 7.5, 7.587, 7.59, 7.7, 7.72, 7.75, 8.72, 20];
const sunByT = {};
let sunFiniteMono = true;
let prevM = Infinity;
for (const t of sunDates) {
  const s = sunState(t);
  sunByT[t] = s;
  if (![s.L, s.R, s.T, s.M].every(x => Number.isFinite(x) && x > 0) || s.M > prevM + 1e-9) {
    sunFiniteMono = false;
  }
  prevM = s.M;
  console.log(`  +${t} Ga : ${s.phase} | L=${+s.L.toPrecision(3)} R=${+s.R.toPrecision(3)} (${(s.R * R_SUN_AU).toFixed(3)} UA) T=${Math.round(s.T)} K M=${s.M.toFixed(3)}`);
}
check(sunFiniteMono, 'Soleil : L, R, T, M finis > 0 et masse monotone décroissante sur 0..20 Ga');

const s0 = sunByT[0];
const s542 = sunByT[5.42];
const sTip = sunByT[7.587];
const sHe = sunByT[7.59];
const sAgb = sunByT[7.72];
const sWd0 = sunByT[7.75];
const sWd1 = sunByT[8.72];
const sWd2 = sunByT[20];
check(
  s0.phase === 'étoile de la séquence principale' &&
  Math.abs(s0.L - 1) < 1e-6 && Math.abs(s0.R - 1) < 1e-6 &&
  Math.abs(s0.T - 5774) < 1 && Math.abs(s0.M - 1) < 1e-6,
  'Soleil t=0 : séquence principale, L=1, R=1, T=5774 K, M=1'
);
check(
  Math.abs(s542.L - 1.84) < 1e-3 && Math.abs(s542.R - 1.37) < 1e-3 &&
  Math.abs(sTip.L - 2730) < 1 && Math.abs(sTip.R - 256) < 0.5 && Math.abs(sTip.M - 0.668) < 1e-3 &&
  sHe.R < 20 && sHe.T > 4000 &&
  Math.abs(sAgb.L - 2090) < 1 && Math.abs(sAgb.R - 149) < 0.5,
  'Soleil : ancres Schröder & Smith (2008) MS final, sommet RGB, flash He, sommet AGB'
);
check(
  [sWd0, sWd1, sWd2].every(w => w.phase === 'naine blanche' && Math.abs(w.R - 0.0125) < 1e-6 && Math.abs(w.M - 0.5405) < 1e-4) &&
  sWd0.L > sWd1.L && sWd1.L > sWd2.L,
  'Soleil naine blanche (7,75..20 Ga) : R=0,0125, M=0,5405, refroidissement monotone'
);

const mestelRatio = Math.pow((SUN_NOW + 20 - 12.30) / (SUN_NOW + 8.72 - 12.30), -7 / 5);
const errMestel = Math.abs((sWd2.L / sWd1.L) / mestelRatio - 1);
const errSB = Math.abs(sWd2.L / (sWd2.R * sWd2.R * Math.pow(sWd2.T / 5772, 4)) - 1);
check(
  errMestel < 1e-12 && errSB < 1e-12,
  `naine blanche : loi de Mestel (${errMestel.toExponential(1)}) et Stefan-Boltzmann (${errSB.toExponential(1)}) < 1e-12`
);

const eMer = engulfTime(0.387);
const eVen = engulfTime(0.723);
const eEar = engulfTime(1.0);
const e115 = engulfTime(1.15);
const eMar = engulfTime(1.524);
console.log(`  engloutissement (Ga depuis aujourd'hui) : Mercure ${eMer.toFixed(4)}, Vénus ${eVen.toFixed(4)}, Terre ${eEar.toFixed(4)}, Mars ${eMar}`);
check(
  eMer > 6.5 && eMer < eVen && eVen < eEar && eEar > 7.55 && eEar < 7.587 &&
  e115 === Infinity && eMar === Infinity,
  `engloutissement : Mercure (${eMer.toFixed(4)}) < Vénus (${eVen.toFixed(4)}) < Terre (${eEar.toFixed(4)}) < 7,587 Ga ; 1,15 UA et Mars survivent`
);

console.log('--- Étoiles (modèle)');
const N = DATA.STARS_N;
const aux = b64ToBytes(DATA.STARS_AUX);
const hip = new Uint32Array(b64ToBytes(DATA.STARS_HIP).buffer);
const cnt = [0, 0, 0, 0];
const fates = [0, 0, 0, 0, 0];
let snSoon = 0;
let badLife = 0;
for (let i = 0; i < N; i++) {
  const L = starLife(aux[i * 2] / 8 - 10, aux[i * 2 + 1] / 100 - 0.5, i, hip[i]);
  if (
    !L.slice(0, 6).every(Number.isFinite) ||
    !(L[0] < L[1] && L[1] < L[2]) ||
    !(L[4] > 0) ||
    L[5] < 0 || L[5] > 3 ||
    L[3] < 0 || L[3] > 4
  ) {
    badLife++;
  }
  cnt[L[5]]++;
  fates[L[3]]++;
  if ((L[3] === 1 || L[3] === 3) && L[2] > 0 && L[2] < 10) snSoon++;
}
console.log('  classes [naines, géantes, supergéantes, naines blanches] :', cnt, '| destins [0..4] :', fates, '| supernovas dans les 10 prochains Ma :', snSoon);
check(
  N === 58967 && badLife === 0 && cnt.every(c => c > 0) && cnt[0] > 25000 && snSoon > 50 && snSoon < 500,
  `population starLife (${N} étoiles HYG) : ${badLife} incohérence, 4 classes peuplées, ${snSoon} supernovas < 10 Ma`
);

const namedTargets = {
  Rigel: L => L[5] === 2 && L[3] === 3 && L[4] > 15,
  'Bételgeuse': L => L[5] === 2 && L[3] === 3 && Math.abs(L[2] - 0.1) < 1e-9,
  Sirius: L => L[5] === 0 && L[3] === 0 && L[4] >= 1.8 && L[4] <= 3.0 && L[1] > 0,
  'Véga': L => L[5] === 0 && L[3] === 0 && L[4] >= 1.8 && L[4] <= 3.0 && L[1] > 0,
  Arcturus: L => L[5] === 1 && L[3] === 2 && L[1] < 0 && L[2] > 0,
  'Alpha du Centaure': L => L[5] === 0 && L[3] === 0 && L[4] >= 0.8 && L[4] <= 1.2 && L[1] > 5000,
  'Étoile de Barnard': L => L[5] === 0 && L[3] === 0 && L[4] < 0.5 && L[2] > 1e5,
};
let namedChecked = 0;
for (const nm of Object.keys(namedTargets)) {
  const l = DATA.STAR_LABELS.find(x => x.n === nm);
  if (!l) {
    check(false, `étoile de référence introuvable : ${nm}`);
    continue;
  }
  namedChecked++;
  const L = starLife(aux[l.i * 2] / 8 - 10, aux[l.i * 2 + 1] / 100 - 0.5, l.i, hip[l.i]);
  console.log(`  ${l.n.padEnd(18)} : ${STAR_CLASS[L[5]]}, ${L[4].toFixed(1)} M☉, naissance ${Math.round(L[0])} Ma, fin MS ${Math.round(L[1])} Ma, mort ${+L[2].toPrecision(3)} Ma, destin ${L[3]}`);
  check(namedTargets[nm](L), `étoile de référence ${nm} : classe ${STAR_CLASS[L[5]]}, destin ${L[3]}, ${L[4].toFixed(1)} M☉`);
}
check(namedChecked === 7, `7 / 7 étoiles nommées vérifiées (${namedChecked})`);

console.log('--- Mouvement des étoiles');
const geo = new Uint16Array(b64ToBytes(DATA.STARS_GEO).buffer);
const p = new Float32Array(N * 3);
for (let i = 0; i < N; i++) {
  const lon = geo[i * 3] / 65535 * TAU;
  const lat = (geo[i * 3 + 1] / 65535 - 0.5) * Math.PI;
  const d = Math.pow(10, geo[i * 3 + 2] / 65535 * 5.5 - 1);
  const cl = Math.cos(lat);
  p.set([d * cl * Math.cos(lon), d * cl * Math.sin(lon), d * Math.sin(lat)], i * 3);
}
const sunGal0 = DATA.SGRA_GAL.map(x => -x * GAL.R0);
let t0 = Date.now();
const K = initStarKin(p, N, sunGal0);
const tKap = TAU / K.sun[2] * 1000;
const tNu = TAU / K.sun[7] * 1000;
console.log(`  init ${Date.now() - t0} ms ; Soleil : rayon guide ${K.sun[0].toFixed(2)} kpc, période épicyclique ${tKap.toFixed(0)} Ma, verticale ${tNu.toFixed(0)} Ma`);
check(
  K.sun[0] > 8.3 && K.sun[0] < 9.0 && tKap > 150 && tKap < 195 && tNu > 75 && tNu < 105,
  `épicycle solaire : Rg=${K.sun[0].toFixed(2)} kpc (8,3..9,0), T_kap=${tKap.toFixed(0)} Ma (150..195), T_nu=${tNu.toFixed(0)} Ma (75..105)`
);

const out = new Float32Array(N * 3);
const dist = i => Math.hypot(out[i * 3], out[i * 3 + 1], out[i * 3 + 2]);
const PASSAGES = [
  ['Gliese 710', [1.20e6, 1.38e6], [0.10, 0.30]],
  ['Alpha du Centaure', [2.2e4, 3.3e4], [2.5, 3.3]],
  ['Étoile de Barnard', [7e3, 1.3e4], [3.3, 4.1]],
];
for (const [nm, tWin, dWin] of PASSAGES) {
  const l = DATA.STAR_LABELS.find(x => x.n === nm);
  if (!l) {
    check(false, `passage stellaire introuvable : ${nm}`);
    continue;
  }
  let best = [0, 1e9];
  for (let t = -5e4; t <= 2e6; t += 250) {
    starPositions(K, t, t / 1e9, out, l.i, l.i + 1);
    const d = dist(l.i);
    if (d < best[1]) best = [t, d];
  }
  console.log(`  ${nm} : au plus près dans ${Math.round(best[0])} ans, à ${best[1].toFixed(3)} al (${Math.round(best[1] * 63241)} UA)`);
  check(
    best[0] >= tWin[0] && best[0] <= tWin[1] && best[1] >= dWin[0] && best[1] <= dWin[1],
    `passage ${nm} : +${Math.round(best[0])} ans ∈ [${tWin[0]}, ${tWin[1]}], d=${best[1].toFixed(3)} al ∈ [${dWin[0]}, ${dWin[1]}]`
  );
}

t0 = Date.now();
starPositions(K, 1e5, 1e-4, out);
const tl = Date.now() - t0;
t0 = Date.now();
starPositions(K, 2e8, 0.2, out);
console.log(`  mise à jour de ${N} étoiles : ${tl} ms (ligne droite), ${Date.now() - t0} ms (orbites)`);
let far = 0;
let nonFin = 0;
for (let i = 0; i < N; i++) {
  const x = out[i * 3];
  const y = out[i * 3 + 1];
  const z = out[i * 3 + 2];
  if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) nonFin++;
  else if (Math.hypot(x, y, z) > 3000) far++;
}
console.log(`  dans 200 Ma : ${(far / N * 100).toFixed(0)} % des étoiles sont à plus de 3 000 al du Soleil`);
check(
  nonFin === 0 && far / N > 0.5 && far / N < 0.98,
  `cinématique à +200 Ma : ${nonFin} non-fini, ${(far / N * 100).toFixed(1)} % au-delà de 3 000 al`
);

const sg = [0, 0, 0];
let rmin = 99;
let rmax = 0;
for (let t = 0; t < 0.4; t += 0.002) {
  sunGalAt(K, t, sg);
  const R = Math.hypot(sg[0], sg[1]);
  rmin = Math.min(rmin, R);
  rmax = Math.max(rmax, R);
}
console.log(`  orbite du Soleil : entre ${rmin.toFixed(2)} et ${rmax.toFixed(2)} kpc du centre`);
check(
  rmin > 7.5 && rmin <= 8.21 && rmax >= 8.19 && rmax < 10.2,
  `sunGalAt (0..0,4 Ga) : orbite liée dans [${rmin.toFixed(2)}, ${rmax.toFixed(2)}] kpc autour de R0=8,2`
);

console.log('--- Andromède');
const C = buildCosmo(PLANCK);
const m31List = [17, 40, 57, undefined, 100];
const m31Res = [];
const m31P0 = [0, 0, 0];
let m31InitOk = true;
for (const vt of m31List) {
  t0 = Date.now();
  const O = andromedaOrbit(C, vt);
  andromedaAt(O, 0, m31P0);
  const d0Err = Math.hypot(m31P0[0] - DATA.M31.pos[0], m31P0[1] - DATA.M31.pos[1], m31P0[2] - DATA.M31.pos[2]);
  if (!(Math.abs(O.vr + 116) < 1) || !(d0Err < 1e-3) || !O.peri.length) m31InitOk = false;
  m31Res.push(O);
  console.log(`  v transverse ${O.vt.toFixed(1)} km/s (radiale ${O.vr.toFixed(1)}) : passages ${O.peri.slice(0, 3).map(q => '+' + q[0].toFixed(2) + ' Ga à ' + q[1].toFixed(0) + ' kpc').join(', ') || 'aucun'} | fusion ${O.tMerge ? '+' + O.tMerge.toFixed(2) + ' Ga' : 'pas avant 14 Ga'} | ${Date.now() - t0} ms`);
}
check(m31InitOk, 'Andromède (5 vitesses) : vr ≈ -116 km/s, départ t=0 à < 1e-3 kpc de DATA.M31.pos');

let monoPeriD = true;
let monoPeriT = true;
for (let k = 1; k < m31Res.length; k++) {
  if (!(m31Res[k].peri[0][1] > m31Res[k - 1].peri[0][1])) monoPeriD = false;
  if (!(m31Res[k].peri[0][0] > m31Res[k - 1].peri[0][0])) monoPeriT = false;
}
check(monoPeriD && monoPeriT, 'Andromède : distance et date du 1er péricentre strictement croissantes avec vt');
check(
  m31Res[0].tMerge > 4 &&
  m31Res[0].tMerge < m31Res[1].tMerge &&
  m31Res[1].tMerge < m31Res[2].tMerge &&
  m31Res[2].tMerge < 14 &&
  m31Res[3].tMerge === null &&
  m31Res[4].tMerge === null,
  `Andromède : fusions ordonnées (${m31Res[0].tMerge.toFixed(2)} < ${m31Res[1].tMerge.toFixed(2)} < ${m31Res[2].tMerge.toFixed(2)} Ga), aucune avant 14 Ga à 75,6 et 100 km/s`
);

console.log(fail ? `\n${fail} échec(s)` : '\névolution future : tout est vert');
process.exit(fail ? 1 : 0);
