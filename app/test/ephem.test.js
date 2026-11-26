/* Éphémérides VSOP87 + Lune (Meeus) contre DE440 (70 dates 1851-2149),
   bascule de régime à |T| = 40 siècles, et petits corps (AST/TNO). */
const fs = require('fs');
const path = require('path');
const { loadUnivers } = require('./_load');

const {
  DATA, AU, DEG, solarSystemAt, decodeBodies, updateBodies,
} = loadUnivers({
  gen: ['data.js', 'data2.js', 'ephem.js'],
  src: ['20_physics.js', '30_gen.js'],
});

const R = JSON.parse(fs.readFileSync(path.join(__dirname, 'ref_de440.json'), 'utf8'));
let fail = 0;
const check = (cond, msg) => {
  console.log((cond ? 'OK    ' : 'ÉCHEC ') + msg);
  if (!cond) fail++;
};

const norm = v => Math.hypot(v[0], v[1], v[2]);
const sep = (a, b) =>
  Math.acos(Math.max(-1, Math.min(1, (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (norm(a) * norm(b))))) / DEG * 3600;

check(R.T.length === 70, `fixture DE440 complète : ${R.T.length} dates (1851-2149)`);

const worst = {};
const wd = {};
R.T.forEach((T, i) => {
  const st = solarSystemAt(T, null, 0);
  const mine = {
    mercury: st.planets.mercury.pos,
    venus: st.planets.venus.pos,
    earth: st.earth,
    mars: st.planets.mars.pos,
    jupiter: st.planets.jupiter.pos,
    saturn: st.planets.saturn.pos,
    uranus: st.planets.uranus.pos,
    neptune: st.planets.neptune.pos,
    moon: st.moonGeo,
  };
  for (const k in mine) {
    const s = sep(mine[k], R.ref[k][i]);
    const dk = Math.abs(norm(mine[k]) - norm(R.ref[k][i])) * AU / 1e3;
    worst[k] = worst[k] === undefined ? s : Math.max(worst[k], s);
    wd[k] = wd[k] === undefined ? dk : Math.max(wd[k], dk);
  }
});

console.log(
  'JS vs DE440, 70 dates 1851-2149 — écart angulaire max (″) :',
  Object.fromEntries(Object.entries(worst).map(([k, v]) => [k, +v.toFixed(3)]))
);
console.log(
  'écart de distance max (km) :',
  Object.fromEntries(Object.entries(wd).map(([k, v]) => [k, +v.toFixed(1)]))
);

const ANG_LIM = {
  mercury: 0.5, venus: 0.5, earth: 0.5, mars: 0.6,
  jupiter: 1.0, saturn: 1.1, uranus: 1.7, neptune: 2.6, moon: 7.6,
};
const KM_LIM = {
  mercury: 200, venus: 350, earth: 300, mars: 750,
  jupiter: 2000, saturn: 5000, uranus: 15000, neptune: 15000, moon: 9.5,
};
for (const k of Object.keys(ANG_LIM)) {
  check(
    Number.isFinite(worst[k]) && worst[k] < ANG_LIM[k] && Number.isFinite(wd[k]) && wd[k] < KM_LIM[k],
    `DE440 ${k.padEnd(7)} : angle max ${worst[k].toFixed(3)}″ (< ${ANG_LIM[k]}″), Δr max ${wd[k].toFixed(2)} km (< ${KM_LIM[k]} km)`
  );
}

let t0 = Date.now();
let st = null;
for (let i = 0; i < 2000; i++) st = solarSystemAt(0.27 + i * 1e-5, st);
console.log(`coût solarSystemAt : ${((Date.now() - t0) / 2000).toFixed(3)} ms par image`);

let regimeOk = true;
for (const T of [-45, -35, -29, 0.27, 29, 35, 45, 1e4]) {
  const s2 = solarSystemAt(T);
  const rE = norm(s2.earth);
  const rM = norm(s2.moonGeo) * AU / 1e3;
  const expectedPrecise = Math.abs(T) < 40;
  if (s2.precise !== expectedPrecise || !(rE > 0.94 && rE < 1.06) || !(rM > 350000 && rM < 415000)) {
    regimeOk = false;
  }
  console.log(`T=${T} précis=${s2.precise} Terre r=${rE.toFixed(5)} UA, Lune ${Math.round(rM)} km`);
}
check(regimeOk, 'bascule de régime (|T| < 40) : s2.precise exact, r_Terre ∈ (0,94..1,06) UA, r_Lune ∈ (350..415) Mm');

const MED_RANGE = { AST: [2.2, 3.5], TNO: [30, 50] };
for (const tag of ['AST', 'TNO']) {
  const B = decodeBodies(tag);
  t0 = Date.now();
  for (let i = 0; i < 20; i++) updateBodies(B, 2461355.5 + i);
  const msPerUpdate = ((Date.now() - t0) / 20).toFixed(2);
  const r = new Array(B.N);
  let nanCount = 0;
  let outOfEnv = 0;
  for (let i = 0; i < B.N; i++) {
    const ri = Math.hypot(B.pos[i * 3], B.pos[i * 3 + 1], B.pos[i * 3 + 2]);
    r[i] = ri;
    if (!Number.isFinite(ri)) {
      nanCount++;
    } else {
      const qMin = B.a[i] * (1 - B.e[i]) * 0.999;
      const qMax = B.a[i] * (1 + B.e[i]) * 1.001;
      if (ri < qMin || ri > qMax) outOfEnv++;
    }
  }
  const med = r.slice().sort((a, b) => a - b)[B.N >> 1];
  const lab = DATA[tag + '_LABELS'].map(l => l.n + ' ' + r[l.i].toFixed(2) + ' UA').join(', ');
  console.log(`${tag} ${B.N} corps, ${msPerUpdate} ms par mise à jour, r médian ${med.toFixed(2)} UA, NaN: ${nanCount} | ${lab}`);
  const [lo, hi] = MED_RANGE[tag];
  check(
    B.N === DATA[tag + '_N'] && nanCount === 0 && outOfEnv === 0 && med >= lo && med <= hi,
    `${tag} : ${B.N} corps, ${nanCount} NaN, ${outOfEnv} hors enveloppe [a(1-e), a(1+e)], médiane ${med.toFixed(3)} UA ∈ [${lo}, ${hi}]`
  );
}

console.log(fail ? `\n${fail} échec(s)` : '\néphémérides DE440 & petits corps : tout est vert');
process.exit(fail ? 1 : 0);
