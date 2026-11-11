const fs = require('fs'), vm = require('vm'), path = require('path');
const root = path.join(__dirname, '..');
const code = fs.readFileSync(path.join(root, 'gen/data.js'), 'utf8').replace('const DATA', 'var DATA') + '\n' + fs.readFileSync(path.join(root, 'src/20_physics.js'), 'utf8').replace(/^const /gm, 'var ');
vm.runInThisContext(code);
const ref = JSON.parse(fs.readFileSync(path.join(__dirname, 'ref.json'))), ref2 = JSON.parse(fs.readFileSync(path.join(__dirname, 'ref2.json')));
const norm = v => Math.hypot(v[0], v[1], v[2]);
const angSep = (a, b) => Math.acos(Math.max(-1, Math.min(1, (a[0]*b[0]+a[1]*b[1]+a[2]*b[2]) / (norm(a)*norm(b))))) / DEG;
let worst = {};
console.log('--- Planètes : écart angulaire héliocentrique vs astropy (secondes d\'arc) et écart de distance (km)');
for (const r of ref.planets) {
  const T = (r.jd - 2451545.0) / 36525;
  const st = solarSystemAt(T);
  const mine = { mercury: st.planets.mercury.pos, venus: st.planets.venus.pos, earth: st.earth, mars: st.planets.mars.pos, jupiter: st.planets.jupiter.pos, saturn: st.planets.saturn.pos, uranus: st.planets.uranus.pos, neptune: st.planets.neptune.pos };
  let line = r.date.slice(0, 10) + ' ';
  for (const k in mine) {
    const sep = angSep(mine[k], r.bodies[k]) * 3600, dr = (norm(mine[k]) - norm(r.bodies[k])) * AU / 1e3;
    worst[k] = Math.max(worst[k] || 0, sep);
    line += `${k.slice(0,3)} ${sep.toFixed(0)}″ `;
  }
  // Lune : direction géocentrique
  const mg = [r.bodies.moon[0]-r.bodies.earth[0], r.bodies.moon[1]-r.bodies.earth[1], r.bodies.moon[2]-r.bodies.earth[2]];
  const ms = angSep(st.moonGeo, mg), md = (norm(st.moonGeo) - norm(mg)) * AU / 1e3;
  worst.moon = Math.max(worst.moon || 0, ms);
  line += `| Lune ${ms.toFixed(2)}° Δr ${md.toFixed(0)} km`;
  console.log(line);
}
console.log('pire écart (″) :', Object.fromEntries(Object.entries(worst).map(([k, v]) => [k, k === 'moon' ? v.toFixed(2) + '°' : +v.toFixed(0)])));

console.log('\n--- Cosmologie vs astropy / scipy');
ref.cosmo.forEach((r, i) => {
  const t0 = Date.now();
  const C = buildCosmo({ H0: r.H0, Om: r.Om, OL: r.OL, w: r.w });
  const ms = Date.now() - t0;
  const now = cosmoAt(C, 0);
  // âge de l'univers à z=1 et z=5 : chercher t où a = 1/(1+z)
  const tAt = z => { const at = 1/(1+z); let lo = 0, hi = C.n - 1; for (let j = 0; j < C.n; j++) if (C.a[j] >= at) { hi = j; lo = j - 1; break; } const f = (at - C.a[lo]) / (C.a[hi] - C.a[lo]); return C.t[lo] + f * (C.t[hi] - C.t[lo]); };
  const s1 = cosmoAt(C, tAt(1));
  const chiTo = z => now.chiPH - cosmoAt(C, tAt(z)).chiPH;
  console.log(`H0=${r.H0} Ωm=${r.Om} ΩΛ=${r.OL} w=${r.w}  [${C.n} pas, ${ms} ms, début=${C.startKind}, fin=${C.endKind}]`);
  console.log(`   âge ${C.age.toFixed(4)} vs ${r.age.toFixed(4)} Ga | a(0)=${now.a.toFixed(6)} | regard z=1 ${(-tAt(1)).toFixed(4)} vs ${r.lookback_z1.toFixed(4)} | z=5 ${(-tAt(5)).toFixed(4)} vs ${r.lookback_z5.toFixed(4)} | H(z=1) ${s1.Hkms.toFixed(2)} vs ${r.H_z1.toFixed(2)}`);
  console.log(`   χ(z=1) ${chiTo(1).toFixed(1)} vs ${r.chi_z1.toFixed(1)} | χ(z=1100) ${chiTo(1100).toFixed(1)} vs ${r.chi_z1100.toFixed(1)} | horizon particules ${now.chiPH.toFixed(1)} vs ${ref2[i].chi_ph.toFixed(1)} | horizon événements ${now.chiEH === null ? '—' : now.chiEH.toFixed(1)} vs ${ref2[i].chi_eh === null ? '—' : ref2[i].chi_eh.toFixed(1)} Mpc`);
  console.log(`   q0=${now.q.toFixed(3)} D(0)=${now.D.toFixed(4)} D/a=${(now.D/now.a).toFixed(4)} tAccel=${C.tAccel === null ? '—' : C.tAccel.toFixed(2)} tEnd=${C.tEnd.toFixed(1)} Hubble=${now.rHubble.toFixed(0)} Mpc`);
});
console.log('\n--- Cas limites');
for (const p of [{H0:67.4,Om:3,OL:0,w:-1},{H0:67.4,Om:0.315,OL:0.685,w:-1.5},{H0:67.4,Om:0.1,OL:1.5,w:-1},{H0:67.4,Om:0,OL:1,w:-1},{H0:67.4,Om:0,OL:0,w:-1},{H0:50,Om:2,OL:1.5,w:-0.34},{H0:90,Om:0.01,OL:0.01,w:-2}]) {
  const C = buildCosmo(p), now = cosmoAt(C, 0);
  console.log(JSON.stringify(p), `n=${C.n} début=${C.startKind} (${C.tStart.toFixed(2)}) âge=${C.age === null ? '—' : C.age.toFixed(2)} fin=${C.endKind} à ${C.tEnd.toFixed(2)} Ga  a(0)=${now.a.toFixed(5)} D0=${now.D.toFixed(3)} fini=${[now.a,now.H,now.q,now.D].every(Number.isFinite)}`);
}
console.log('\n--- Rotation galactique (km/s) : rayon, avec halo, sans halo');
for (const r of [1, 2, 4, 8.2, 12, 16, 20, 25]) console.log(`   r=${r} kpc : ${vCirc(r, true).toFixed(0)} | ${vCirc(r, false).toFixed(0)}`);
console.log('   année galactique au Soleil :', (TAU / omegaGal(GAL.R0, true) * 1000).toFixed(0), 'Ma');
