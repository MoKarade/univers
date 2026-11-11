// Test de calcul « orbitales » (mission 2, tâche R14) : forme de l'hydrogène contre la solution exacte, eau contre les mesures, fiche réelle.
const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8');
vm.runInThisContext((rd('gen/data.js') + '\n' + rd('gen/water_qm.js') + '\n' + rd('src/20_physics.js') + '\n' + '/* ====' + rd('src/30_gen.js').split('/* ====').slice(1).join('/* ====')).replace('const DATA', 'var DATA').replace(/^const /gm, 'var ').replace(/^let /gm, 'var '));
const W = DATA.WATER_QM; let bad = 0; const check = (ok, m) => { console.log((ok ? 'PASSE  ' : 'ÉCHEC  ') + m); if (!ok) bad++; };
// forme : P(r) calculée (PySCF) contre 4 r² e^(−2r), à chaque rayon de la grille
let worst = 0; W.H.r.forEach((r, k) => { worst = Math.max(worst, Math.abs(W.H.P[k] - 4 * r * r * Math.exp(-2 * r)) / (4 * Math.exp(-2))); });
check(worst < 0.01, 'hydrogène : densité radiale calculée sur ' + W.H.r.length + ' rayons, écart maximal ' + (100 * worst).toFixed(3) + ' % du maximum exact (limite 1 %)');
check(Math.abs(W.H.E / -0.5 - 1) < 0.01 && Math.abs(W.H.r2 / 3 - 1) < 0.01, 'hydrogène : énergie et ⟨r²⟩ à 1 % de la solution exacte');
check(Math.abs(W.eau.electrons_grille / 10 - 1) < 0.01, 'eau : ' + W.eau.electrons_grille + ' électrons intégrés sur les grilles (10 attendus)');
// énergies : l'approximation de Koopmans écarte −ε des mesures de quelques % à ~15 % (relaxation et corrélation négligées)
const e = W.eau.eps_eV.map(x => -x);
check(e.length === 5 && e.every((x, k) => Math.abs(x / IE_EXP[k] - 1) < 0.15), 'eau : 5 orbitales, −ε à moins de 15 % des mesures (limite de l’approximation de Koopmans)');
// la fiche réelle : une ligne par orbitale avec l'écart, et le profil de l'hydrogène
const rows = waterRows(W), orb = rows.filter(r => IE_NOM.includes(r[0]));
check(orb.length === 5 && orb.every((r, k) => r[1].includes('écart') && r[1].includes(nf(IE_EXP[k], 1))), 'fiche : 5 lignes d’orbitales, chacune avec mesure et écart');
check(rows.some(r => /forme exacte/.test(r[0]) && /<svg/.test(r[1])), 'fiche : profil de l’hydrogène dessiné (calcul et formule exacte)');
if (bad) { console.log('orbitales : ÉCHEC (' + bad + ')'); process.exit(1); } else console.log('orbitales : PASSE');
