// S6 — lumière déviée par un trou noir sans rotation (Schwarzschild), app/src/27_lens.js.
// Références indépendantes : déviation en champ faible α = 4M/b + 15πM²/(4b²) + 128M³/(3b³) (développement publié, p. ex. Keeton et Petters 2005) ;
// ombre de rayon apparent b = √27 M ; taille de l'ombre de M87* comparée à l'anneau mesuré par l'EHT (42 ± 3 microsecondes d'arc, EHT 2019, papier I).
const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
vm.runInThisContext(fs.readFileSync(path.join(root, 'src/27_lens.js'), 'utf8').replace(/^const /gm, 'var '));
let fails = 0; const check = (ok, msg) => { console.log((ok ? 'OK    ' : 'ÉCHEC ') + msg); if (!ok) fails++; };

/* 1. sans masse, la lumière va droit : Δφ = π − ψ */
{ let worst = 0; for (const psi of [0.3, 1.0, 1.5707, 2.0, 3.0]) worst = Math.max(worst, Math.abs(lensDphi(1e12, psi) - (Math.PI - psi)));
  check(worst < 1e-6, `trou noir très loin (r = 10¹² M) : trajet droit à ${worst.toExponential(1)} rad près`); }

/* 2. champ faible : la déviation suit le développement publié jusqu'au second ordre */
for (const b of [100, 1000]) { const r = 1e9, psi = Math.asin(b * Math.sqrt(1 - 2 / r) / r), got = lensDphi(r, psi) - (Math.PI - psi), ref = 4 / b + 15 * Math.PI / (4 * b * b) + 128 / (3 * b ** 3);
  check(Math.abs(got - ref) < 0.02 * 15 * Math.PI / (4 * b * b), `paramètre d'impact ${b} M : déviation ${got.toExponential(5)} rad, attendu ${ref.toExponential(5)}`); }

/* 3. l'ombre : capturé sous b = √27 M, libre au-dessus */
{ const r = 1000, pc = Math.asin(Math.sqrt(27) * Math.sqrt(1 - 2 / r) / r);
  check(lensDphi(r, pc * 0.999) < 0 && lensDphi(r, pc * 1.001) > 0, `ombre vue de 1000 M : rayon apparent ${(pc * 1000).toFixed(4)} mrad (√27·√(1−2/r)/r)`);
  check(lensDphi(r, pc * 1.001) > 2 * Math.PI, 'juste au bord de l\'ombre, la lumière fait au moins un tour (anneau de photons)'); }

/* 4. M87* : diamètre de l'ombre comparé à l'anneau mesuré par l'EHT */
{ const M = 6.5e9, D = 16.8 * 3.0857e22, GM_C2 = 1476.625 * M, r = D / GM_C2, d = 2 * Math.asin(Math.sqrt(27) * Math.sqrt(1 - 2 / r) / r) * 206264.806e6;
  check(d > 36 && d < 45, `M87* (6,5 milliards de masses solaires, 16,8 Mpc) : ombre de ${d.toFixed(1)} microsecondes d'arc ; anneau EHT 42 ± 3`); }

/* 5. table pour le shader : finie, croissante hors de l'ombre, et l'ombre au bon endroit */
{ const r = 200, T = lensLut(r, 512), pc = Math.asin(Math.sqrt(27) * Math.sqrt(1 - 2 / r) / r); let ok = true, prev = Infinity;
  for (let i = 0; i < 512; i++) { const psi = i / 511 * Math.PI, v = T[i]; if (psi < pc * 0.999) ok = ok && v < 0; else if (psi > pc * 1.001) { ok = ok && Number.isFinite(v) && v >= 0 && v <= prev + 1e-9; prev = v; } }
  check(ok, 'table de 512 angles : ombre au centre, déviation qui décroît en s\'éloignant du trou noir');
  const enc = lensLutBytes(T); let worst = 0; for (let i = 0; i < 512; i++) if (T[i] >= 0) worst = Math.max(worst, Math.abs(lensDecode(enc, i) - Math.min(T[i], LENS_MAXPHI)));
  check(worst < 2e-4, `codage sur 16 bits pour la carte graphique : écart ${worst.toExponential(1)} rad`); }

console.log(fails ? `\n${fails} échec(s)` : '\nlentille gravitationnelle : tout est vert');
process.exit(fails ? 1 : 0);
