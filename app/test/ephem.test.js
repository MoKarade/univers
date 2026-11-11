const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8');
global.atob = s => Buffer.from(s, 'base64').toString('binary');
const b64 = "function b64ToBytes(s) { const bin = atob(s), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }";
vm.runInThisContext((rd('gen/data.js') + rd('gen/data2.js') + rd('gen/ephem.js') + rd('src/20_physics.js') + b64).replace(/^const /gm, 'var '));
const R = JSON.parse(rd('test/ref_de440.json')), norm = v => Math.hypot(v[0], v[1], v[2]);
const sep = (a, b) => Math.acos(Math.max(-1, Math.min(1, (a[0]*b[0]+a[1]*b[1]+a[2]*b[2]) / (norm(a)*norm(b))))) / DEG * 3600;
const worst = {}, wd = {};
R.T.forEach((T, i) => {
  const st = solarSystemAt(T, null, 0);
  const mine = { mercury: st.planets.mercury.pos, venus: st.planets.venus.pos, earth: st.earth, mars: st.planets.mars.pos, jupiter: st.planets.jupiter.pos, saturn: st.planets.saturn.pos, uranus: st.planets.uranus.pos, neptune: st.planets.neptune.pos, moon: st.moonGeo };
  for (const k in mine) { worst[k] = Math.max(worst[k] || 0, sep(mine[k], R.ref[k][i])); wd[k] = Math.max(wd[k] || 0, Math.abs(norm(mine[k]) - norm(R.ref[k][i])) * AU / 1e3); }
});
console.log('JS vs DE440, 70 dates 1851-2149 — écart angulaire max (″) :', Object.fromEntries(Object.entries(worst).map(([k, v]) => [k, +v.toFixed(2)])));
console.log('écart de distance max (km) :', Object.fromEntries(Object.entries(wd).map(([k, v]) => [k, Math.round(v)])));
let t0 = Date.now(), st = null; for (let i = 0; i < 2000; i++) st = solarSystemAt(0.27 + i * 1e-5, st); console.log('coût solarSystemAt : %s ms par image', ((Date.now() - t0) / 2000).toFixed(3));
for (const T of [-45, -35, -29, 0.27, 29, 35, 45, 1e4]) { const s2 = solarSystemAt(T); console.log('T=%s précis=%s Terre r=%s UA, Lune %s km', T, s2.precise, norm(s2.earth).toFixed(5), Math.round(norm(s2.moonGeo) * AU / 1e3)); }
for (const tag of ['AST', 'TNO']) { const B = decodeBodies(tag); t0 = Date.now(); for (let i = 0; i < 20; i++) updateBodies(B, 2461355.5 + i); const r = []; for (let i = 0; i < B.N; i++) r.push(Math.hypot(B.pos[i*3], B.pos[i*3+1], B.pos[i*3+2]));
  const lab = DATA[tag + '_LABELS'].map(l => l.n + ' ' + r[l.i].toFixed(2) + ' UA'); console.log(tag, B.N, 'corps, %s ms par mise à jour, r médian %s UA, NaN: %s |', ((Date.now() - t0) / 20).toFixed(2), r.slice().sort((a, b) => a - b)[B.N >> 1].toFixed(2), r.filter(x => !isFinite(x)).length, lab.join(', ')); }
