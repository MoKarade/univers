const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
vm.runInThisContext((rd('gen/data.js') + rd('gen/data2.js') + rd('gen/ephem.js') + rd('src/20_physics.js') + "function b64ToBytes(s) { const bin = atob(s), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }").replace(/^const /gm, 'var '));
const H = JSON.parse(rd('test/horizons.json')), norm = v => Math.hypot(v[0], v[1], v[2]);
const sep = (a, b) => Math.acos(Math.max(-1, Math.min(1, (a[0]*b[0]+a[1]*b[1]+a[2]*b[2]) / (norm(a)*norm(b))))) / DEG * 3600;
const B = { AST: decodeBodies('AST'), TNO: decodeBodies('TNO') };
for (const tag of ['AST', 'TNO']) for (const l of DATA[tag + '_LABELS']) { const h = H[l.n]; if (!h || !h.pos) continue; updateBodies(B[tag], h.jd); const p = [B[tag].pos[l.i*3], B[tag].pos[l.i*3+1], B[tag].pos[l.i*3+2]];
  console.log('%s : écart %s″, distance %s vs %s UA (Horizons)', l.n.padEnd(9), sep(p, h.pos).toFixed(1), norm(p).toFixed(4), norm(h.pos).toFixed(4)); }
const jd0 = (H.Jupiter && H.Jupiter.jd) || 2461354.5, st = solarSystemAt((jd0 - 2451545) / 36525, null, 0);
for (const [n, p] of [['Mars', st.planets.mars.pos], ['Jupiter', st.planets.jupiter.pos], ['Lune', st.moonGeo]]) if (H[n] && H[n].pos) console.log('%s : écart %s″, distance %s vs %s km', n.padEnd(9), sep(p, H[n].pos).toFixed(2), Math.round(norm(p) * AU / 1e3), Math.round(norm(H[n].pos) * AU / 1e3)); else console.log(n, ': référence Horizons indisponible');
