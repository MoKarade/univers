/* Contrôle JPL Horizons (2026-11-10 TDB) : gros astéroïdes, objets transneptuniens, Mars, Jupiter et Lune. */
const fs = require('fs');
const path = require('path');
const { loadUnivers } = require('./_load');

const {
  DATA, AU, DEG, solarSystemAt, decodeBodies, updateBodies,
} = loadUnivers({
  gen: ['data.js', 'data2.js', 'ephem.js'],
  src: ['20_physics.js', '30_gen.js'],
});

const H = JSON.parse(fs.readFileSync(path.join(__dirname, 'horizons.json'), 'utf8'));
let fail = 0;
const check = (cond, msg) => {
  console.log((cond ? 'OK    ' : 'ÉCHEC ') + msg);
  if (!cond) fail++;
};

const norm = v => Math.hypot(v[0], v[1], v[2]);
const sep = (a, b) =>
  Math.acos(Math.max(-1, Math.min(1, (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (norm(a) * norm(b))))) / DEG * 3600;

const AST_LIM = { Vesta: 6, Pallas: 6, 'Cérès': 10, Hygie: 15 };
const B = { AST: decodeBodies('AST'), TNO: decodeBodies('TNO') };
let checked = 0;

for (const tag of ['AST', 'TNO']) {
  for (const l of DATA[tag + '_LABELS']) {
    const h = H[l.n];
    if (!h || !h.pos) continue;
    checked++;
    updateBodies(B[tag], h.jd);
    const p = [B[tag].pos[l.i * 3], B[tag].pos[l.i * 3 + 1], B[tag].pos[l.i * 3 + 2]];
    const s = sep(p, h.pos);
    const rp = norm(p);
    const rh = norm(h.pos);
    const drRel = Math.abs(rp - rh) / rh;
    const angLim = tag === 'AST' ? (AST_LIM[l.n] || 15) : 1.0;
    const relLim = tag === 'AST' ? 5e-4 : 1e-5;
    check(
      p.every(Number.isFinite) && Number.isFinite(s) && s < angLim && Number.isFinite(drRel) && drRel < relLim,
      `${l.n.padEnd(9)} (${tag}) : écart ${s.toFixed(2)}″ (< ${angLim}″), Δr/r ${drRel.toExponential(2)} (< ${relLim}), r=${rp.toFixed(4)} vs ${rh.toFixed(4)} UA`
    );
  }
}

const jd0 = (H.Jupiter && H.Jupiter.jd) || 2461354.5;
const st = solarSystemAt((jd0 - 2451545) / 36525, null, 0);
const PLANET_LIM = {
  Mars: { ang: 1.0, km: 500 },
  Jupiter: { ang: 1.0, km: 1500 },
  Lune: { ang: 7.5, km: 9.5 },
};
for (const [n, p] of [['Mars', st.planets.mars.pos], ['Jupiter', st.planets.jupiter.pos], ['Lune', st.moonGeo]]) {
  const h = H[n];
  if (!h || !h.pos) {
    check(false, `${n} : référence Horizons absente`);
    continue;
  }
  checked++;
  const s = sep(p, h.pos);
  const dkm = Math.abs(norm(p) - norm(h.pos)) * AU / 1e3;
  const lim = PLANET_LIM[n];
  check(
    p.every(Number.isFinite) && Number.isFinite(s) && s < lim.ang && Number.isFinite(dkm) && dkm < lim.km,
    `${n.padEnd(9)} : écart ${s.toFixed(2)}″ (< ${lim.ang}″), |Δr| ${dkm.toFixed(2)} km (< ${lim.km} km)`
  );
}

const totalRef = Object.keys(H).length;
check(
  checked === totalRef && checked === 12,
  `couverture exhaustive de horizons.json : ${checked} / ${totalRef} corps vérifiés`
);

console.log(fail ? `\n${fail} échec(s)` : '\nHorizons : tout est vert');
process.exit(fail ? 1 : 0);
