// Test de calcul « proton » (mission 2, tâche R15) : contenu du proton d'après les distributions de partons CT18NNLO.
const fs = require('fs'), path = require('path'), vm = require('vm'), root = path.join(__dirname, '..');
global.DATA = {}; vm.runInThisContext(fs.readFileSync(path.join(root, 'gen/proton_pdf.js'), 'utf8'));
const A = fs.readFileSync(path.join(root, 'src/60_app.js'), 'utf8'), R = fs.readFileSync(path.join(root, 'src/40_render.js'), 'utf8');
let bad = 0; const check = (ok, m) => { console.log((ok ? 'PASSE  ' : 'ÉCHEC  ') + m); if (!ok) bad++; };
const rows = DATA.PROTON_PDF.rows; let ws = 0, wu = 0, wd = 0;
for (const r of rows) { const m = r.mom, s = m.uv + m.dv + m.sea + m.g; ws = Math.max(ws, Math.abs(s - 1)); wu = Math.max(wu, Math.abs(r.n.u - 2)); wd = Math.max(wd, Math.abs(r.n.d - 1)); }
check(ws <= 0.01, 'somme des parts d’impulsion = 1 à ' + ws.toFixed(4) + ' près, sur ' + rows.length + ' finesses (de ' + rows[0].lam.toExponential(1) + ' à ' + rows[rows.length - 1].lam.toExponential(1) + ' m)');
check(wu <= 0.02 && wd <= 0.02, 'compte net : 2 up à ' + wu.toFixed(4) + ' près, 1 down à ' + wd.toFixed(4) + ' près');
check(rows[rows.length - 1].mom.g > rows[0].mom.g && rows[rows.length - 1].mom.sea > rows[0].mom.sea, 'plus fin : gluons ' + rows[0].mom.g.toFixed(3) + ' → ' + rows[rows.length - 1].mom.g.toFixed(3) + ', paires ' + rows[0].mom.sea.toFixed(3) + ' → ' + rows[rows.length - 1].mom.sea.toFixed(3));
check(/CT18NNLO \(Hou et al\. 2021, Phys\. Rev\. D 103, 014013\)/.test(A) && /Licence des données/.test(A), 'source et licence citées dans la fiche du proton');
check(!/tubeG|NSEA|tubes de gluons/.test(R + A), 'tubes de gluons et paires dessinés à la main retirés');
if (bad) { console.log('proton : ÉCHEC (' + bad + ')'); process.exit(1); } else console.log('proton : PASSE');
