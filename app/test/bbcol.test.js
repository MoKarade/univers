// S1 — couleur des étoiles : corps noir de Planck vu par l'observateur standard CIE 1931 (2°).
// Références indépendantes du code testé :
//  - l'illuminant A de la CIE est, par définition, un corps noir à 2856 K : x = 0,44757 ; y = 0,40745 ;
//  - l'approximation publiée du lieu de Planck de Kim et al. 2002 (US 7 024 034), valable de 1667 à 25 000 K.
const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
vm.runInThisContext((rd('gen/data.js') + rd('gen/data15.js') + rd('src/20_physics.js') + rd('src/30_gen.js')).replace(/^const /gm, 'var '));

let fails = 0;
const check = (ok, msg) => { console.log((ok ? 'OK    ' : 'ÉCHEC ') + msg); if (!ok) fails++; };

/* ---- intégration directe, à partir de la table CIE versée dans le dépôt ---- */
const CMF = fs.readFileSync(path.join(root, '..', 'pipeline', 'ref', 'ciexyz31_1.csv'), 'utf8').trim().split(/\r?\n/).map(l => l.split(',').map(Number));
const h = 6.62607015e-34, c = 299792458, kB = 1.380649e-23;
const planck = (lnm, T) => { const l = lnm * 1e-9; return 1 / (Math.pow(l, 5) * (Math.exp(h * c / (l * kB * T)) - 1)); };
function xyzOf(T) { let X = 0, Y = 0, Z = 0; for (const [l, x, y, z] of CMF) { const b = planck(l, T); X += b * x; Y += b * y; Z += b * z; } return [X, Y, Z]; }
const xyOf = T => { const [X, Y, Z] = xyzOf(T), s = X + Y + Z; return [X / s, Y / s]; };
// XYZ -> sRGB linéaire (IEC 61966-2-1)
const toRgb = ([X, Y, Z]) => [3.2406 * X - 1.5372 * Y - 0.4986 * Z, -0.9689 * X + 1.8758 * Y + 0.0415 * Z, 0.0557 * X - 0.2040 * Y + 1.0570 * Z];
const refRgb = T => { const v = toRgb(xyzOf(T)).map(u => Math.max(u, 0)), m = Math.max(...v); return v.map(u => u / m); };

/* ---- 1. la table CIE et l'intégration retrouvent l'illuminant A ---- */
{ const [x, y] = xyOf(2856); check(Math.abs(x - 0.44757) < 5e-4 && Math.abs(y - 0.40745) < 5e-4, `illuminant A (2856 K) : x=${x.toFixed(5)} y=${y.toFixed(5)} (CIE : 0,44757 0,40745)`); }

/* ---- 2. accord avec le lieu de Planck publié (Kim et al. 2002) ---- */
function kim(T) {
  const x = T <= 4000 ? -0.2661239e9 / T ** 3 - 0.2343589e6 / T ** 2 + 0.8776956e3 / T + 0.179910 : -3.0258469e9 / T ** 3 + 2.1070379e6 / T ** 2 + 0.2226347e3 / T + 0.240390;
  const y = T <= 2222 ? -1.1063814 * x ** 3 - 1.34811020 * x ** 2 + 2.18555832 * x - 0.20219683 : T <= 4000 ? -0.9549476 * x ** 3 - 1.37418593 * x ** 2 + 2.09137015 * x - 0.16748867 : 3.0817580 * x ** 3 - 5.87338670 * x ** 2 + 3.75112997 * x - 0.37001483;
  return [x, y];
}
for (const T of [2000, 3000, 4000, 5772, 10000, 20000]) { const a = xyOf(T), b = kim(T), d = Math.hypot(a[0] - b[0], a[1] - b[1]); check(d < 3e-3, `lieu de Planck à ${T} K : écart ${d.toExponential(1)} avec Kim et al. 2002`); }

/* ---- 3. la table de la page (DATA.BBCOL) suit l'intégration directe ---- */
{ let worst = 0, wT = 0; for (let T = 3000; T <= 25000; T *= 1.037) { const a = bbRgb(T), b = refRgb(T); for (let k = 0; k < 3; k++) { const e = Math.abs(a[k] - b[k]); if (e > worst) { worst = e; wT = T; } } }
  check(worst < 0.01, `table de la page contre intégration directe, 3000 à 25 000 K : écart maximal ${worst.toFixed(4)} (à ${wT.toFixed(0)} K)`); }

/* ---- 4. la couleur des étoiles passe par la température (Ballesteros 2012) puis le corps noir ---- */
{ const T = bvToTeff(0.656); check(Math.abs(T - 5772) < 150, `Soleil, B−V = 0,656 : ${T.toFixed(0)} K (mesuré : 5772 K)`); }
{ const s = bvToRgb(0.656), r = refRgb(bvToTeff(0.656)); check(s.every((v, k) => Math.abs(v - r[k]) < 0.01), `Soleil : couleur = corps noir à sa température (${s.map(v => v.toFixed(3)).join(' ')})`);
  check(Math.min(...s) > 0.75, 'Soleil : presque blanc (aucune composante sous 0,75)'); }
{ const b = bvToRgb(1.85); check(b[0] === 1 && b[1] < 0.6 && b[2] < b[1], `Bételgeuse, B−V = 1,85 : orangée (${b.map(v => v.toFixed(3)).join(' ')})`); }
{ const r = bvToRgb(-0.03); check(r[2] === 1 && r[0] < 1, `Rigel, B−V = −0,03 : bleu-blanc (${r.map(v => v.toFixed(3)).join(' ')})`); }
{ let mono = true, prev = -1; for (let bv = -0.4; bv <= 2.0; bv += 0.01) { const q = bvToRgb(bv), ratio = q[0] / q[2]; if (ratio < prev - 1e-9) mono = false; prev = ratio; } check(mono, 'du bleu au rouge sans retour en arrière quand B−V augmente'); }
{ const q = bvToRgb(NaN); check(q.every(Number.isFinite), 'indice de couleur absent : couleur finie (pas de point noir)'); }

console.log(fails ? `\n${fails} échec(s)` : '\ncouleur des étoiles : tout est vert');
process.exit(fails ? 1 : 0);
