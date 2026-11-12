// S5 — carte de poussière 3D réduite (pipeline/build_dust.py -> app/gen/data20.js), d'après Edenhofer et al. 2024.
// Références indépendantes de la carte (autres méthodes) :
//  - nuage du Taureau à 141 pc environ (Zucker et al. 2019 ; Galli et al. 2019 : 126 à 165 pc selon les sous-régions) ;
//  - Orion A à 390–470 pc (Großschedl et al. 2018, parallaxes Gaia des étoiles jeunes) ;
//  - vers les pôles galactiques, peu de poussière : A_V de quelques centièmes de magnitude (Schlegel et al. 1998 donnent E(B−V) ≈ 0,01–0,02).
const fs = require('fs'), path = require('path'), root = path.join(__dirname, '..');
const DATA = {}; eval(fs.readFileSync(path.join(root, 'gen/data20.js'), 'utf8'));
let fails = 0; const check = (ok, msg) => { console.log((ok ? 'OK    ' : 'ÉCHEC ') + msg); if (!ok) fails++; };
const D = DATA.DUST, q = Buffer.from(D.q, 'base64'), DEG = Math.PI / 180;
check(q.length === D.nx * D.ny * D.nz, `grille de ${D.nx} × ${D.ny} × ${D.nz} cases de ${D.cell} pc`);
const dens = (x, y, z) => { const i = Math.floor(x / D.cell + D.nx / 2), j = Math.floor(y / D.cell + D.ny / 2), k = Math.floor(z / D.cell + D.nz / 2);
  if (i < 0 || j < 0 || k < 0 || i >= D.nx || j >= D.ny || k >= D.nz) return 0; const v = q[(k * D.ny + j) * D.nx + i]; return v ? Math.pow(10, D.lo + (v - 1) / 254 * D.span) : 0; };
const dir = (l, b) => [Math.cos(b * DEG) * Math.cos(l * DEG), Math.cos(b * DEG) * Math.sin(l * DEG), Math.sin(b * DEG)];
const av = (l, b, d0, d1) => { const u = dir(l, b); let s = 0; for (let d = d0; d < d1; d += 1) s += dens(u[0] * d, u[1] * d, u[2] * d); return s; };      /* mag, pas de 1 pc */
const peak = (l, b, d0, d1) => { const u = dir(l, b); let best = [0, -1]; for (let d = d0; d < d1; d += 2) { const v = dens(u[0] * d, u[1] * d, u[2] * d); if (v > best[1]) best = [d, v]; } return best[0]; };

{ const d = peak(172, -15, 70, 400); check(d > 115 && d < 175, `Taureau (l = 172°, b = −15°) : poussière la plus dense à ${d} pc (attendu 126 à 165 pc)`); }
{ const d = peak(211, -19.5, 200, 800); check(d > 370 && d < 490, `Orion A (l = 211°, b = −19,5°) : poussière la plus dense à ${d} pc (attendu 390 à 470 pc)`); }
{ const n = av(0, 90, 0, 400), s = av(0, -90, 0, 400); check(n < 0.15 && s < 0.15, `pôles galactiques : A_V = ${n.toFixed(3)} (nord) et ${s.toFixed(3)} (sud) mag jusqu'à 400 pc`); }
{ const g = av(0, 0, 0, 1240); check(g > 1, `vers le centre galactique, dans le plan : A_V = ${g.toFixed(2)} mag jusqu'à 1,24 kpc`); }
{ const o = dens(1500, 0, 0) === 0 && dens(0, 0, 900) === 0; check(o, 'hors de la carte (au-delà de 1,25 kpc ou de 406 pc du plan) : aucune poussière inventée'); }

/* la fonction de la page (28_dust.js, même calcul que le shader) : même densité que ce test, et trajets justes */
{ const vm = require('vm'), ctx = { DATA, Math, Float32Array, Uint8Array, b64ToBytes: b => Uint8Array.from(Buffer.from(b, 'base64')) }; vm.createContext(ctx); vm.runInContext(fs.readFileSync(path.join(root, 'src/28_dust.js'), 'utf8'), ctx);
  let worst = 0; for (let k = 0; k < 2000; k++) { const g = [Math.sin(k * 1.7) * 1300, Math.cos(k * 2.3) * 1300, Math.sin(k * 0.7) * 450], r = dens(...g); worst = Math.max(worst, Math.abs(ctx.dustDens(g) - r) / Math.max(r, 1e-12)); }
  check(worst < 1e-6, `page : même densité que la carte en 2000 points (écart relatif ${worst.toExponential(1)})`);
  /* 1000 trajets tirés au hasard (caméra et étoile dans ou hors de la carte) : 32 points au niveau adapté contre une intégration au pas de 1 pc */
  let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647, fine = (a, b2) => { const d = [0, 1, 2].map(k => b2[k] - a[k]), L = Math.hypot(...d), n = Math.ceil(L); let s2 = 0; for (let i = 0; i < n; i++) { const t = (i + 0.5) / n; s2 += dens(a[0] + d[0] * t, a[1] + d[1] * t, a[2] + d[2] * t); } return s2 * L / n; };
  const err = []; for (let k = 0; k < 1000; k++) { const R1 = rnd() < 0.5 ? 300 : 4000, a = [(rnd() - 0.5) * 2 * R1, (rnd() - 0.5) * 2 * R1, (rnd() - 0.5) * 600], b2 = [(rnd() - 0.5) * 2500, (rnd() - 0.5) * 2500, (rnd() - 0.5) * 700]; err.push(Math.abs(ctx.dustAv(a, b2) - fine(a, b2))); }
  err.sort((x, y) => x - y); const p99 = err[989], p50 = err[500];
  check(p50 < 0.03 && p99 < 0.6, `1000 trajets : écart à l'intégration fine, médiane ${p50.toFixed(3)} mag, 99 % sous ${p99.toFixed(3)} mag (seuils 0,03 et 0,6 : limite assumée de 64 points par trajet)`);
  /* seuil d'allumage (caméra à 3 années-lumière du Soleil) : la différence avec la vue de la Terre reste négligeable */
  const c3 = [0.92, 0, 0], jumps = []; for (let k = 0; k < 500; k++) { const st = [(rnd() - 0.5) * 2400, (rnd() - 0.5) * 2400, (rnd() - 0.5) * 700]; const pr = ctx.dustPair(c3, st); jumps.push(Math.abs(pr[0] - pr[1])); }
  jumps.sort((x, y) => x - y); check(jumps[494] < 0.15, `allumage à 3 années-lumière : saut d'éclat sous ${jumps[494].toFixed(3)} mag pour 99 % des étoiles`); }

console.log(fails ? `\n${fails} échec(s)` : '\npoussière 3D : tout est vert');
process.exit(fails ? 1 : 0);
