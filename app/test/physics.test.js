/* Contrôle physique : repli képlérien JPL Standish Table 1 + Lune basse précision,
   cosmologie Friedmann RK4 (vs astropy / scipy + cas limites), et courbe de rotation galactique. */
const fs = require('fs');
const path = require('path');
const { loadUnivers } = require('./_load');

const {
  AU, DEG, TAU, GAL, KMS_KPC_RADGYR,
  solarSystemAt, buildCosmo, cosmoAt, vCirc, omegaGal,
} = loadUnivers({
  gen: ['data.js'],
  src: ['20_physics.js'],
});

const ref = JSON.parse(fs.readFileSync(path.join(__dirname, 'ref.json'), 'utf8'));
const ref2 = JSON.parse(fs.readFileSync(path.join(__dirname, 'ref2.json'), 'utf8'));

let fail = 0;
const check = (cond, msg) => {
  console.log((cond ? 'OK    ' : 'ÉCHEC ') + msg);
  if (!cond) fail++;
};

const norm = v => Math.hypot(v[0], v[1], v[2]);
const angSep = (a, b) =>
  Math.acos(Math.max(-1, Math.min(1, (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (norm(a) * norm(b))))) / DEG;

check(
  ref.planets.length === 5 && ref.cosmo.length === 6 && ref2.length === 6,
  `références chargées : ${ref.planets.length} dates planètes, ${ref.cosmo.length} modèles cosmologiques`
);

console.log("--- Planètes (repli Standish Table 1) : écart angulaire héliocentrique vs astropy (″) et distance");
const worst = {};
const worstRel = {};
let worstMoonKm = 0;
let allFinite = true;
let allFallback = true;

for (const r of ref.planets) {
  const T = (r.jd - 2451545.0) / 36525;
  const st = solarSystemAt(T);
  if (st.precise !== false) allFallback = false;
  const mine = {
    mercury: st.planets.mercury.pos,
    venus: st.planets.venus.pos,
    earth: st.earth,
    mars: st.planets.mars.pos,
    jupiter: st.planets.jupiter.pos,
    saturn: st.planets.saturn.pos,
    uranus: st.planets.uranus.pos,
    neptune: st.planets.neptune.pos,
  };
  let line = r.date.slice(0, 10) + ' ';
  for (const k in mine) {
    const p = mine[k];
    const rb = r.bodies[k];
    const np = norm(p);
    const nr = norm(rb);
    if (!p.every(Number.isFinite) || !(np > 0)) allFinite = false;
    const sep = angSep(p, rb) * 3600;
    const rel = Math.abs(np - nr) / nr;
    worst[k] = Math.max(worst[k] || 0, sep);
    worstRel[k] = Math.max(worstRel[k] || 0, rel);
    line += `${k.slice(0, 3)} ${sep.toFixed(0)}″ `;
  }
  const mg = [
    r.bodies.moon[0] - r.bodies.earth[0],
    r.bodies.moon[1] - r.bodies.earth[1],
    r.bodies.moon[2] - r.bodies.earth[2],
  ];
  if (!st.moonGeo.every(Number.isFinite) || !(norm(st.moonGeo) > 0)) allFinite = false;
  const ms = angSep(st.moonGeo, mg);
  const md = Math.abs(norm(st.moonGeo) - norm(mg)) * AU / 1e3;
  worst.moon = Math.max(worst.moon || 0, ms);
  worstMoonKm = Math.max(worstMoonKm, md);
  line += `| Lune ${ms.toFixed(2)}° |Δr| ${md.toFixed(0)} km`;
  console.log(line);
}

console.log(
  'pire écart (″) :',
  Object.fromEntries(Object.entries(worst).map(([k, v]) => [k, k === 'moon' ? v.toFixed(2) + '°' : +v.toFixed(1)]))
);
check(allFinite && allFallback, 'repli Standish + Lune : 5 dates × 9 corps finis, st.precise === false');

const ANG_TOL = {
  mercury: 60, venus: 60, earth: 60, mars: 60,
  jupiter: 400, saturn: 650, uranus: 100, neptune: 100,
};
const REL_TOL = {
  mercury: 5e-4, venus: 5e-4, earth: 5e-4, mars: 5e-4,
  jupiter: 2.5e-3, saturn: 2.5e-3, uranus: 2.5e-3, neptune: 2.5e-3,
};
for (const k of Object.keys(ANG_TOL)) {
  check(
    Number.isFinite(worst[k]) && worst[k] < ANG_TOL[k] && Number.isFinite(worstRel[k]) && worstRel[k] < REL_TOL[k],
    `Standish ${k} : angle max ${worst[k].toFixed(2)}″ (< ${ANG_TOL[k]}″), Δr/r max ${worstRel[k].toExponential(2)} (< ${REL_TOL[k]})`
  );
}
check(
  Number.isFinite(worst.moon) && worst.moon < 0.35 && Number.isFinite(worstMoonKm) && worstMoonKm < 1000,
  `Lune basse précision : angle max ${worst.moon.toFixed(3)}° (< 0.35°), |Δr| max ${worstMoonKm.toFixed(1)} km (< 1000 km)`
);

console.log('\n--- Cosmologie vs astropy / scipy');
const D0 = [];
ref.cosmo.forEach((r, i) => {
  const t0 = Date.now();
  const C = buildCosmo({ H0: r.H0, Om: r.Om, OL: r.OL, w: r.w });
  const ms = Date.now() - t0;
  const now = cosmoAt(C, 0);
  const tAt = z => {
    const at = 1 / (1 + z);
    let lo = 0;
    let hi = C.n - 1;
    for (let j = 0; j < C.n; j++) {
      if (C.a[j] >= at) {
        hi = j;
        lo = j - 1;
        break;
      }
    }
    const f = (at - C.a[lo]) / (C.a[hi] - C.a[lo]);
    return C.t[lo] + f * (C.t[hi] - C.t[lo]);
  };
  const s1 = cosmoAt(C, tAt(1));
  const chiTo = z => now.chiPH - cosmoAt(C, tAt(z)).chiPH;
  const lb1 = -tAt(1);
  const lb5 = -tAt(5);
  const chi1 = chiTo(1);
  const chi1100 = chiTo(1100);
  const qExp = 0.5 * r.Om + C.Or + 0.5 * r.OL * (1 + 3 * r.w);
  const rHubExp = 299792.458 / r.H0;
  const tag = `H0=${r.H0} Ωm=${r.Om} ΩΛ=${r.OL} w=${r.w}`;

  console.log(`${tag}  [${C.n} pas, ${ms} ms, début=${C.startKind}, fin=${C.endKind}]`);
  console.log(`   âge ${C.age.toFixed(4)} vs ${r.age.toFixed(4)} Ga | a(0)=${now.a.toFixed(6)} | regard z=1 ${lb1.toFixed(4)} vs ${r.lookback_z1.toFixed(4)} | z=5 ${lb5.toFixed(4)} vs ${r.lookback_z5.toFixed(4)} | H(z=1) ${s1.Hkms.toFixed(2)} vs ${r.H_z1.toFixed(2)}`);
  console.log(`   χ(z=1) ${chi1.toFixed(1)} vs ${r.chi_z1.toFixed(1)} | χ(z=1100) ${chi1100.toFixed(1)} vs ${r.chi_z1100.toFixed(1)} | horizon particules ${now.chiPH.toFixed(1)} vs ${ref2[i].chi_ph.toFixed(1)} | horizon événements ${now.chiEH === null ? '—' : now.chiEH.toFixed(1)} vs ${ref2[i].chi_eh === null ? '—' : ref2[i].chi_eh.toFixed(1)} Mpc`);

  const anchorsOk =
    C.startKind === 'bang' &&
    C.endKind === 'limit' &&
    Math.abs(now.a - 1) < 1e-8 &&
    Math.abs(now.Hkms / r.H0 - 1) < 1e-8 &&
    Math.abs(now.q - qExp) < 1e-8 &&
    Math.abs(now.rHubble / rHubExp - 1) < 1e-6 &&
    Math.abs(now.fr + now.fm + now.fde - 1) < 1e-12;
  check(anchorsOk, `cosmo[${i}] (${tag}) : identités analytiques à t=0 (a, H0, q0, rHubble, Σf=1)`);

  const astropyOk =
    Math.abs(C.age / r.age - 1) < 1e-5 &&
    Math.abs(lb1 / r.lookback_z1 - 1) < 1e-3 &&
    Math.abs(lb5 / r.lookback_z5 - 1) < 1e-3 &&
    Math.abs(s1.Hkms / r.H_z1 - 1) < 1e-3 &&
    Math.abs(chi1 / r.chi_z1 - 1) < 1e-3 &&
    Math.abs(chi1100 / r.chi_z1100 - 1) < 1e-4;
  check(astropyOk, `cosmo[${i}] (${tag}) : accord astropy (âge, regard z=1/5, H(1), χ(1/1100))`);

  const phOk = Number.isFinite(now.chiPH) && Math.abs(now.chiPH / ref2[i].chi_ph - 1) < 1e-5;
  let ehOk = false;
  if (ref2[i].chi_eh !== null) {
    ehOk = Number.isFinite(now.chiEH) && Math.abs(now.chiEH / ref2[i].chi_eh - 1) < 1e-5;
  } else if (r.OL === 0) {
    ehOk = now.chiEH === null;
  } else if (r.w === -0.8) {
    ehOk = Number.isFinite(now.chiEH) && Math.abs(now.chiEH - 7340.31) / 7340.31 < 1e-3;
  }
  check(phOk && ehOk, `cosmo[${i}] (${tag}) : horizons particules et événements vs scipy / analytique`);
  D0.push(now.D);
});

check(
  Number.isFinite(D0[3]) && Number.isFinite(D0[0]) && Number.isFinite(D0[2]) &&
  D0[3] < D0[0] && D0[0] < D0[2] && D0[2] < 1.01,
  `croissance linéaire D(0) : ouvert (${D0[3].toFixed(4)}) < Planck (${D0[0].toFixed(4)}) < EdS (${D0[2].toFixed(4)}) < 1,01`
);

console.log('\n--- Cas limites cosmologiques');
const EDGE_CASES = [
  { p: { H0: 67.4, Om: 3, OL: 0, w: -1 }, start: 'bang', end: 'crunch', extra: C => Math.abs(C.age - 7.446) < 0.05 && Math.abs(C.tEnd - 40.895) < 0.1 },
  { p: { H0: 67.4, Om: 0.315, OL: 0.685, w: -1.5 }, start: 'bang', end: 'rip', extra: C => C.tEnd > 10 && C.tEnd < 40 },
  { p: { H0: 67.4, Om: 0.1, OL: 1.5, w: -1 }, start: 'bounce', end: 'limit', extra: C => C.age === null && Number.isFinite(C.tBounce) && C.tBounce < 0 },
  { p: { H0: 67.4, Om: 0, OL: 1, w: -1 }, start: 'bang', end: 'limit', extra: C => Number.isFinite(C.age) && C.age > 30 },
  { p: { H0: 67.4, Om: 0, OL: 0, w: -1 }, start: 'bang', end: 'limit', extra: C => Math.abs(C.age - 14.369) < 0.05 },
  { p: { H0: 50, Om: 2, OL: 1.5, w: -0.34 }, start: 'bang', end: 'crunch', extra: C => Number.isFinite(C.tEnd) && C.tEnd > 0 },
  { p: { H0: 90, Om: 0.01, OL: 0.01, w: -2 }, start: 'bang', end: 'rip', extra: C => Number.isFinite(C.tEnd) && C.tEnd > 0 },
];
for (const ec of EDGE_CASES) {
  const C = buildCosmo(ec.p);
  const now = cosmoAt(C, 0);
  const finite = [now.a, now.H, now.q, now.D].every(Number.isFinite);
  const good =
    C.startKind === ec.start &&
    C.endKind === ec.end &&
    C.n > 100 &&
    Math.abs(now.a - 1) < 1e-4 &&
    finite &&
    ec.extra(C);
  check(
    good,
    `cas limite ${JSON.stringify(ec.p)} : ${C.startKind}/${C.endKind}, n=${C.n}, âge=${C.age === null ? '—' : C.age.toFixed(2)}, tEnd=${C.tEnd.toFixed(2)} Ga`
  );
}

console.log('\n--- Rotation galactique (km/s) : rayon, avec halo, sans halo');
let galOk = true;
for (const r of [1, 2, 4, 8.2, 12, 16, 20, 25]) {
  const vw = vCirc(r, true);
  const vn = vCirc(r, false);
  if (!Number.isFinite(vw) || !Number.isFinite(vn) || !(vw > vn) || !(vn > 0)) galOk = false;
  console.log(`   r=${r} kpc : ${vw.toFixed(1)} | ${vn.toFixed(1)}`);
}
const vR0 = vCirc(GAL.R0, true);
const v25w = vCirc(25, true);
const v25n = vCirc(25, false);
const v82n = vCirc(GAL.R0, false);
const tGal = TAU / omegaGal(GAL.R0, true) * 1000;
const tGalExp = TAU * GAL.R0 / (GAL.V0 * KMS_KPC_RADGYR) * 1000;
check(
  Math.abs(vR0 - GAL.V0) < 1e-12 && galOk,
  `calage Soleil vCirc(${GAL.R0}) = ${vR0.toFixed(6)} km/s (= ${GAL.V0}) et vWith > vNo > 0 sur 1..25 kpc`
);
check(
  v25w > 190 && v25w < 235 && v25n < 0.7 * v82n,
  `courbe plate à 25 kpc : ${v25w.toFixed(1)} km/s avec halo (190..235), déclin képlérien ${v25n.toFixed(1)} km/s sans halo`
);
check(
  Math.abs(tGal - tGalExp) < 1e-9 && tGal > 200 && tGal < 250,
  `année galactique au Soleil : ${tGal.toFixed(2)} Ma (attendu ${tGalExp.toFixed(2)} Ma)`
);

console.log(fail ? `\n${fail} échec(s)` : '\nphysique de base : tout est vert');
process.exit(fail ? 1 : 0);
