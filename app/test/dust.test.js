// S5 — carte de poussière 3D réduite (pipeline/build_dust.py -> app/gen/data17.js), d'après Edenhofer et al. 2024.
// Références indépendantes de la carte (autres méthodes) :
//  - nuage du Taureau à 141 pc environ (Zucker et al. 2019 ; Galli et al. 2019 : 126 à 165 pc selon les sous-régions) ;
//  - Orion A à 390–470 pc (Großschedl et al. 2018, parallaxes Gaia des étoiles jeunes) ;
//  - vers les pôles galactiques, peu de poussière : A_V de quelques centièmes de magnitude (Schlegel et al. 1998 donnent E(B−V) ≈ 0,01–0,02).
const fs = require('fs'), path = require('path'), root = path.join(__dirname, '..');
const DATA = {}; eval(fs.readFileSync(path.join(root, 'gen/data17.js'), 'utf8'));
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

/* la fonction de la page (28_dust.js, même calcul que le shader) lit la même densité que ce test */
{ const vm = require('vm'), ctx = { DATA, Math, b64ToBytes: b => Uint8Array.from(Buffer.from(b, 'base64')) }; vm.createContext(ctx); vm.runInContext(fs.readFileSync(path.join(root, 'src/28_dust.js'), 'utf8'), ctx);
  let worst = 0; for (let k = 0; k < 2000; k++) { const g = [Math.sin(k * 1.7) * 1300, Math.cos(k * 2.3) * 1300, Math.sin(k * 0.7) * 450]; worst = Math.max(worst, Math.abs(ctx.dustDens(g) - dens(...g))); }
  const u = dir(211, -19.5), a = ctx.dustAv([0, 0, 0], [u[0] * 600, u[1] * 600, u[2] * 600]), ref = av(211, -19.5, 0, 600);
  check(worst === 0 && Math.abs(a / ref - 1) < 0.25, `page : même densité en 2000 points ; A_V vers Orion jusqu'à 600 pc ${a.toFixed(2)} (12 points) contre ${ref.toFixed(2)} mag (pas de 1 pc)`); }

console.log(fails ? `\n${fails} échec(s)` : '\npoussière 3D : tout est vert');
process.exit(fails ? 1 : 0);
