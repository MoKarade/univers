// Test de calcul « orbitales » (mission 2, tâche R14) : hydrogène contre la solution exacte, eau contre les mesures.
const fs = require('fs'), path = require('path'), vm = require('vm'), root = path.join(__dirname, '..');
global.DATA = {}; vm.runInThisContext(fs.readFileSync(path.join(root, 'gen/water_qm.js'), 'utf8'));
const A = fs.readFileSync(path.join(root, 'src/60_app.js'), 'utf8'), W = DATA.WATER_QM;
let bad = 0; const check = (ok, m) => { console.log((ok ? 'PASSE  ' : 'ÉCHEC  ') + m); if (!ok) bad++; };
// hydrogène : énergie −1/2 hartree et ⟨r²⟩ = 3 a₀² pour l'état fondamental exact (solution de l'équation de Schrödinger)
check(Math.abs(W.H.E / -0.5 - 1) < 0.01, 'hydrogène : énergie ' + W.H.E.toFixed(6) + ' hartree (exacte −0,5 ; écart ' + (100 * (W.H.E / -0.5 - 1)).toFixed(3) + ' %)');
check(Math.abs(W.H.r2 / 3 - 1) < 0.01, 'hydrogène : ⟨r²⟩ = ' + W.H.r2.toFixed(4) + ' a₀² (exacte 3 ; écart ' + (100 * (W.H.r2 / 3 - 1)).toFixed(3) + ' %)');
// forme exacte de l'état 1s : ⟨r²⟩ = 3 a₀² se vérifie aussi en intégrant |ψ|² = e^{−2r}/π
let n = 0, d = 0; for (let r = 0; r < 40; r += 1e-3) { const w = 4 * r * r * Math.exp(-2 * r); n += w * r * r; d += w; }
check(Math.abs(n / d / 3 - 1) < 0.001, 'formule exacte 1s : ⟨r²⟩ intégré = ' + (n / d).toFixed(4) + ' a₀²');
// eau : 10 électrons sur la grille, 16 000 points, énergies comparées aux mesures, écart affiché dans la fiche
check(Math.abs(W.eau.electrons_grille / 10 - 1) < 0.01, 'eau : ' + W.eau.electrons_grille + ' électrons intégrés sur la grille (10 attendus)');
const IE = [539.9, 32.2, 18.51, 14.74, 12.62], e = W.eau.eps_eV.map(x => -x);
check(e.length === 5 && e.every((x, k) => Math.abs(x / IE[k] - 1) < 0.15), 'eau : 5 orbitales occupées, −ε à moins de 15 % des énergies d’ionisation mesurées : ' + e.map((x, k) => x.toFixed(1) + '/' + IE[k]).join(', ') + ' eV');
check(/IE_EXP = \[539\.9, 32\.2, 18\.51, 14\.74, 12\.62\]/.test(A) && /mesuré \('/.test(A), 'fiche : énergies calculées et mesurées, écart affiché');
if (bad) { console.log('orbitales : ÉCHEC (' + bad + ')'); process.exit(1); } else console.log('orbitales : PASSE');
