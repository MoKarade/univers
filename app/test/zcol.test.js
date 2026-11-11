// S3 — couleur observée des galaxies et des quasars selon z (pipeline/build_zcol.py -> app/gen/data16.js).
// Références indépendantes du code : longueurs d'onde de raies connues (Hα 6563 Å, Lyα 1216 Å) et pic de sensibilité de l'œil (vert, vers 540-555 nm).
const fs = require('fs'), path = require('path'), root = path.join(__dirname, '..'), ref = path.join(root, '..', 'pipeline', 'ref');
const DATA = {}; eval(fs.readFileSync(path.join(root, 'gen/data16.js'), 'utf8'));
let fails = 0; const check = (ok, msg) => { console.log((ok ? 'OK    ' : 'ÉCHEC ') + msg); if (!ok) fails++; };
const Z = DATA.ZCOL, zAt = (i, zm) => Math.exp(i / (Z.n - 1) * Math.log(1 + zm)) - 1;

/* 1. tables bien formées */
for (const k of ['gal', 'qso']) { const a = Z[k]; let ok = a.length === Z.n * 3; for (let i = 0; i < Z.n && ok; i++) { const c = a.slice(i * 3, i * 3 + 3); ok = c.every(v => Number.isFinite(v) && v >= 0 && v <= 1) && Math.abs(Math.max(...c) - 1) < 1e-3; }
  check(ok, `table ${k} : ${Z.n} couleurs finies entre 0 et 1, composante la plus forte à 1`); }

/* 2. lecture des fichiers : Hα de la galaxie Sb à 6563 Å, Lyα du quasar à 1216 Å (vérifie l'échelle des longueurs d'onde) */
function cards(b, off) { const h = {}; for (;;) { const blk = b.subarray(off, off + 2880); off += 2880; for (let i = 0; i < 36; i++) { const c = blk.subarray(i * 80, i * 80 + 80).toString('ascii'); if (c.slice(0, 8).trim() === 'END') return [h, off]; if (c.slice(8, 10) === '= ') h[c.slice(0, 8).trim()] = c.slice(10).split('/')[0].trim().replace(/'/g, '').trim(); } } }
{ const b = fs.readFileSync(path.join(ref, 'kc96_sb_template.fits')); let [, off] = cards(b, 0); const [h, o2] = cards(b, off), n = +h.NAXIS2, w = +h.NAXIS1, rows = [];
  for (let r = 0; r < n; r++) rows.push([b.readFloatBE(o2 + r * w), b.readFloatBE(o2 + r * w + 4)]);
  const near = rows.filter(r => r[0] > 6300 && r[0] < 6800).sort((a, c) => c[1] - a[1])[0];
  check(Math.abs(near[0] - 6563) < 25, `galaxie Sb : raie la plus forte entre 6300 et 6800 Å à ${near[0]} Å (Hα : 6563 Å)`); }
{ const b = fs.readFileSync(path.join(ref, 'sdss_spDR2-029_qso.fit')), [h, off] = cards(b, 0), n = +h.NAXIS1; let best = [0, 0];
  for (let i = 0; i < n; i++) { const l = Math.pow(10, +h.COEFF0 + +h.COEFF1 * i), v = b.readFloatBE(off + i * 4); if (l > 1100 && l < 1400 && v > best[1]) best = [l, v]; }
  check(Math.abs(best[0] - 1216) < 10, `quasar : raie la plus forte entre 1100 et 1400 Å à ${best[0].toFixed(0)} Å (Lyα : 1216 Å)`); }

/* 3. physique : le vert domine quand Lyα tombe au pic de l'œil (z ≈ 540/121,6 − 1 ≈ 3,4) ; le rouge domine quand Lyα passe dans le rouge (z ≈ 4,3) */
{ let best = [0, -1]; for (let i = 0; i < Z.n; i++) { const c = Z.qso.slice(i * 3, i * 3 + 3), g = c[1] - Math.max(c[0], c[2]); if (g > best[1]) best = [zAt(i, Z.zq), g]; }
  check(best[0] > 3.0 && best[0] < 3.8, `quasar : vert le plus marqué à z = ${best[0].toFixed(2)} (attendu 3,0 à 3,8)`);
  const last = Z.qso.slice((Z.n - 1) * 3); check(last[0] === 1 && last[2] < 0.5, `quasar à z = ${Z.zq} : rouge (${last.join(' ')})`); }

/* 4. galaxie au repos plus rouge que bleue (lumière dominée par des étoiles plus froides que le Soleil) ; puis plus rouge à z = 0,3 qu'à z = 0 */
{ const c0 = Z.gal.slice(0, 3); let i3 = 0; while (zAt(i3, Z.zg) < 0.3) i3++; const c3 = Z.gal.slice(i3 * 3, i3 * 3 + 3);
  check(c0[0] === 1 && c0[2] < 0.75, `galaxie Sb à z = 0 : ${c0.join(' ')}`);
  check(c3[2] / c3[0] < c0[2] / c0[0], `galaxie Sb à z = ${zAt(i3, Z.zg).toFixed(2)} : plus rouge qu'au repos (bleu/rouge ${(c3[2] / c3[0]).toFixed(2)} contre ${(c0[2] / c0[0]).toFixed(2)})`); }

/* 5. la recherche du shader (copie fidèle de zcol en GLSL) retombe sur les points de la table */
{ const zcol = (z, q) => { const zm = Math.log(1 + (q ? Z.zq : Z.zg)), u = Math.min(Math.max(Math.log(1 + z) / zm, 0), 1) * 63, i = Math.min(Math.floor(u), 62), f = u - i, a = q ? Z.qso : Z.gal; return [0, 1, 2].map(k => a[i * 3 + k] * (1 - f) + a[(i + 1) * 3 + k] * f); };
  let worst = 0; for (const q of [0, 1]) for (let i = 0; i < Z.n; i++) { const c = zcol(zAt(i, q ? Z.zq : Z.zg), q), t = (q ? Z.qso : Z.gal).slice(i * 3, i * 3 + 3); for (let k = 0; k < 3; k++) worst = Math.max(worst, Math.abs(c[k] - t[k])); }
  check(worst < 1e-3, `recherche par z comme dans le shader : écart ${worst.toExponential(1)} aux points de la table`);
  const far = zcol(9, 0), edge = Z.gal.slice((Z.n - 1) * 3); check(far.every((v, k) => Math.abs(v - edge[k]) < 1e-9), 'au-delà du spectre (z = 9) : couleur du bord, pas de valeur inventée'); }

/* 6. chaîne CIE -> sRGB de build_zcol.py : un spectre plat (illuminant E de la CIE, x = y = 1/3) donne le sRGB linéaire connu
   (1,2049 ; 0,9483 ; 0,9086), ramené à 1 ; et la table versée est bien celle que produit le script (aucune édition à la main) */
{ const { spawnSync } = require('child_process'), py = ['python3', 'python'].find(c => spawnSync(c, ['--version']).status === 0), pdir = path.join(root, '..', 'pipeline');
  if (!py) check(false, 'Python introuvable pour rejouer build_zcol.py');
  else {
    const code = "import sys, json; sys.path.insert(0, r'" + pdir + "'); import build_zcol as b; cmf=[tuple(float(v) for v in l.split(',')) for l in (b.REF/'ciexyz31_1.csv').read_text().strip().splitlines()]; cmf=[c for c in cmf if 380<=c[0]<=780]; print(json.dumps(b.rgb([(100.0,1.0),(20000.0,1.0)], 0, cmf)))";
    const r = spawnSync(py, ['-c', code], { encoding: 'utf8' }), e = JSON.parse(r.stdout || '[0,0,0]'), ref = [1, 0.9483 / 1.2049, 0.9086 / 1.2049], d = Math.max(...e.map((v, k) => Math.abs(v - ref[k])));
    check(d < 0.01, `spectre plat (illuminant E) : ${e.map(v => v.toFixed(3)).join(' ')} (attendu ${ref.map(v => v.toFixed(3)).join(' ')})`);
    const before = fs.readFileSync(path.join(root, 'gen/data16.js'), 'utf8'), g = spawnSync(py, [path.join(pdir, 'build_zcol.py')], { encoding: 'utf8' }), after = fs.readFileSync(path.join(root, 'gen/data16.js'), 'utf8');
    check(g.status === 0 && before.replace(/\r/g, '') === after.replace(/\r/g, ''), 'data16.js est exactement ce que produit pipeline/build_zcol.py');
  } }

console.log(fails ? `\n${fails} échec(s)` : '\ncouleur des galaxies lointaines : tout est vert');
process.exit(fails ? 1 : 0);
