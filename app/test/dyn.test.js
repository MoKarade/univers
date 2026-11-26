/* Dynamique des marées Voie lactée / Andromède (dynInit, dynAdvance) :
   3 mesures de vitesse M31, équilibre pré-rencontre, queues de marée et cœurs liés post-fusion. */
const { loadUnivers } = require('./_load');

const {
  DATA, PLANCK, buildCosmo, andromedaOrbit, andromedaAt,
  genGalaxy, genDiskGalaxy, dynTables, dynInit, dynAdvance,
} = loadUnivers({
  gen: ['data.js', 'data3.js'],
  src: ['20_physics.js', '25_future.js', '26_orbits.js', '30_gen.js'],
});

let fail = 0;
const check = (cond, msg) => {
  console.log((cond ? 'OK    ' : 'ÉCHEC ') + msg);
  if (!cond) fail++;
};

const countNonFinite = D => {
  let n = 0;
  for (let i = 0; i < D.x.length; i++) if (!Number.isFinite(D.x[i])) n++;
  for (let i = 0; i < D.v.length; i++) if (!Number.isFinite(D.v[i])) n++;
  for (let i = 0; i < D.out.length; i++) if (!Number.isFinite(D.out[i])) n++;
  return n;
};

const C = buildCosmo(PLANCK);
const V = [28.4, -109.8, 41.4];
const P = DATA.M31.pos;
const d0 = Math.hypot(...P);
const vr = (V[0] * P[0] + V[1] * P[1] + V[2] * P[2]) / d0;
const vt = Math.hypot(V[0] - vr * P[0] / d0, V[1] - vr * P[1] / d0, V[2] - vr * P[2] / d0);

const orbits = {};
for (const [nm, v] of [['Gaia 2025', V], ['Hubble 2012', [44.1, -118.0, 3.1]], ['Gaia 2021', DATA.M31.vel]]) {
  const orb = andromedaOrbit(C, undefined, v);
  orbits[nm] = orb;
  console.log(`${nm} : v transverse ${orb.vt.toFixed(1)} km/s | passages ${orb.peri.slice(0, 3).map(q => '+' + q[0].toFixed(2) + ' Ga à ' + q[1].toFixed(0) + ' kpc').join(', ')} | fusion ${orb.tMerge ? '+' + orb.tMerge.toFixed(2) + ' Ga' : 'pas avant 14 Ga'}`);
}
const g25 = orbits['Gaia 2025'];
const h12 = orbits['Hubble 2012'];
const g21 = orbits['Gaia 2021'];
check(
  g25.vt >= 30 && g25.vt <= 38 && g25.tMerge >= 5 && g25.tMerge <= 7 &&
  h12.vt >= 45 && h12.vt <= 53 && h12.tMerge > g25.tMerge && h12.tMerge < 10 &&
  g21.vt >= 72 && g21.vt <= 79 && g21.tMerge === null &&
  g25.peri[0][1] < h12.peri[0][1] && h12.peri[0][1] < g21.peri[0][1],
  `3 mesures M31 : Gaia 2025 (vt=${g25.vt.toFixed(1)}, fusion ${g25.tMerge.toFixed(2)} Ga), Hubble 2012 (${h12.vt.toFixed(1)}, ${h12.tMerge.toFixed(2)} Ga), Gaia 2021 (${g21.vt.toFixed(1)}, sans fusion)`
);

const O = andromedaOrbit(C, vt, V);
let tOn = null;
for (let i = Math.round(-O.t0 / O.dt); i < O.n; i++) {
  if (Math.hypot(O.r[i * 3], O.r[i * 3 + 1], O.r[i * 3 + 2]) < 150) {
    tOn = Math.max(0.02, O.t0 + i * O.dt - 0.35);
    break;
  }
}

const gal = genGalaxy(30000, 3000, 21);
const m31 = genDiskGalaxy(23, 9000, 24);
const T = dynTables();
const A = [[1, 0, 0], [0, 0.3, -0.954], [0, 0.954, 0.3]];
let t0 = Date.now();
const D = dynInit(gal, 30000, m31, O, tOn, [-8.2, 0.1, 0.01], A, 30000, 9000);
console.log(`début de la simulation des marées : +${tOn.toFixed(2)} Ga | ${D.n} particules | init ${Date.now() - t0} ms`);

const measure = () => {
  const r = [];
  const q = [];
  const c = [0, 0, 0];
  andromedaAt(O, D.t, c);
  for (let i = 1; i < D.nMW; i++) r.push(Math.hypot(D.x[i * 3], D.x[i * 3 + 1], D.x[i * 3 + 2]));
  for (let i = D.nMW; i < D.n; i++) q.push(Math.hypot(D.x[i * 3] - c[0], D.x[i * 3 + 1] - c[1], D.x[i * 3 + 2] - c[2]));
  r.sort((a, b) => a - b);
  q.sort((a, b) => a - b);
  const pc = (a, f) => a[Math.floor(a.length * f)];
  return {
    t: D.t,
    sep: Math.hypot(...c),
    mw50: pc(r, 0.5), mw90: pc(r, 0.9), mw99: pc(r, 0.99),
    m31_50: pc(q, 0.5), m31_90: pc(q, 0.9), m31_99: pc(q, 0.99),
    sunR: Math.hypot(D.x[0], D.x[1], D.x[2]),
    nonFin: countNonFinite(D),
  };
};
const fmt = s =>
  `t=+${s.t.toFixed(2)} Ga | séparation ${s.sep.toFixed(0)} kpc | Voie lactée : rayon médian ${s.mw50.toFixed(1)}, 90 % dans ${s.mw90.toFixed(1)}, 99 % dans ${s.mw99.toFixed(1)} kpc | Andromède : ${s.m31_50.toFixed(1)} / ${s.m31_90.toFixed(1)} / ${s.m31_99.toFixed(1)} kpc | Soleil à ${s.sunR.toFixed(1)} kpc`;

const s0 = measure();
console.log(fmt(s0));
check(
  tOn !== null && tOn > 2.5 && tOn < O.peri[0][0] &&
  D.nMW === 30000 && D.n === 30000 + Math.min(9000, m31.N - 70) &&
  s0.nonFin === 0 &&
  Math.abs(s0.sunR - Math.hypot(-8.2, 0.1, 0.01)) < 1e-6 &&
  s0.mw50 >= 4 && s0.mw50 <= 8 && s0.m31_50 >= 5 && s0.m31_50 <= 9,
  `dynInit : tOn=+${tOn.toFixed(2)} Ga, n=${D.n} (MW ${D.nMW}), 0 non-fini, Soleil=${s0.sunR.toFixed(3)} kpc, médianes ${s0.mw50.toFixed(2)}/${s0.m31_50.toFixed(2)} kpc`
);

t0 = Date.now();
const n1 = dynAdvance(D, O, tOn + 0.2, 100, T);
console.log(`${n1} pas en ${Date.now() - t0} ms (${((Date.now() - t0) / n1).toFixed(2)} ms par pas)`);
const s1 = measure();
console.log(fmt(s1));
check(
  n1 === 100 && Math.abs(D.t - (tOn + 0.2)) < 1e-9 && s1.nonFin === 0 &&
  Math.abs(s1.mw50 / s0.mw50 - 1) < 0.05 &&
  Math.abs(s1.m31_50 / s0.m31_50 - 1) < 0.05 &&
  Math.abs(s1.sunR - 8.2) < 0.3,
  `équilibre pré-rencontre (+0,2 Ga, ${n1} pas) : disques stables (< 5 %), Soleil à ${s1.sunR.toFixed(2)} kpc`
);

const dates = [O.peri[0][0], O.peri[0][0] + 0.3, O.peri[0][0] + 0.8, (O.tMerge || 9) + 0.5, (O.tMerge || 9) + 2];
const snaps = [];
let allDatesFinite = true;
for (const t of dates) {
  dynAdvance(D, O, t, 1e6, T);
  const st = measure();
  snaps.push(st);
  console.log(fmt(st));
  if (Math.abs(D.t - t) >= 1e-6 || st.nonFin !== 0) allDatesFinite = false;
}
check(allDatesFinite, 'finitude et dates exactes aux 5 instants clés (péricentre à fusion +2 Ga)');
check(
  Math.abs(snaps[0].sep - O.peri[0][1]) < 0.5,
  `au péricentre (+${dates[0].toFixed(2)} Ga) : séparation ${snaps[0].sep.toFixed(2)} kpc vs orbite ${O.peri[0][1].toFixed(2)} kpc`
);
check(
  snaps[2].mw99 > s0.mw99 && snaps[1].m31_99 > s0.m31_99,
  `marées post-péricentre : r99 MW ${s0.mw99.toFixed(1)} → ${snaps[2].mw99.toFixed(1)} kpc, M31 ${s0.m31_99.toFixed(1)} → ${snaps[1].m31_99.toFixed(1)} kpc`
);
for (const [label, s] of [['fusion +0,5 Ga', snaps[3]], ['fusion +2 Ga', snaps[4]]]) {
  check(
    s.sep === 0 &&
    s.mw90 > 2 * s0.mw90 && s.m31_90 > 2 * s0.m31_90 && s.mw99 > 5 * s0.mw99 &&
    s.mw50 < 20 && s.m31_50 < 20 && s.sunR > 1 && s.sunR < 50,
    `${label} : sep=0, queues de marée (r90 ${s.mw90.toFixed(1)}/${s.m31_90.toFixed(1)} kpc), cœurs liés (${s.mw50.toFixed(1)}/${s.m31_50.toFixed(1)} kpc), Soleil ${s.sunR.toFixed(1)} kpc`
  );
}

console.log(fail ? `\n${fail} échec(s)` : '\ndynamique des marées : tout est vert');
process.exit(fail ? 1 : 0);
