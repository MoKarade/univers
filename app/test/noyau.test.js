// Test de calcul « noyau » (mission 2, tâche R16) : répartition de charge de l'oxygène 16 mesurée par diffusion d'électrons
// (oscillateur harmonique de de Vries, de Jager et de Vries 1987) et rayon affiché.
const fs = require('fs'), path = require('path'), root = path.join(__dirname, '..');
const R = fs.readFileSync(path.join(root, 'src/40_render.js'), 'utf8'), A = fs.readFileSync(path.join(root, 'src/60_app.js'), 'utf8');
let bad = 0; const check = (ok, m) => { console.log((ok ? 'PASSE  ' : 'ÉCHEC  ') + m); if (!ok) bad++; };
const a = +R.match(/NUC_A = ([\d.]+)/)[1], al = +R.match(/NUC_AL = ([\d.]+)/)[1];
// rayon quadratique moyen de la densité, intégré numériquement
let n = 0, d = 0; for (let r = 0; r < 20; r += 1e-3) { const w = r * r * (1 + al * r * r / (a * a)) * Math.exp(-r * r / (a * a)); n += w * r * r; d += w; }
const rms = Math.sqrt(n / d);
check(Math.abs(rms - 2.6991) / 2.6991 < 0.02, 'rayon de la répartition de charge : ' + rms.toFixed(3) + ' fm (mesuré : 2,6991 fm, Angeli et Marinova 2013), écart ' + (100 * (rms / 2.6991 - 1)).toFixed(1) + ' %');
check(/\['Rayon de charge', '2,70 fm/.test(A), 'fiche du noyau : rayon affiché 2,70 fm');
check(!/TET = \[\[1, 1, 1\]/.test(R), 'arrangement en quatre groupes retiré');
if (bad) { console.log('noyau : ÉCHEC (' + bad + ')'); process.exit(1); } else console.log('noyau : PASSE');
