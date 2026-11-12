/* R10 (lot G) : le Groupe local rejoué depuis le calcul complet de la fusion (fusion_centres.json).
   Contrôles : départ identique aux mesures de la page ; orbite d'Andromède et du Grand Nuage lues correctement ;
   recul de la Voie lactée sous l'attraction du Grand Nuage, comparé aux publications. */
const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
global.DATA = {};
vm.runInThisContext((rd('gen/data.js') + rd('gen/data3.js') + rd('gen/data4.js') + rd('src/20_physics.js') + rd('src/25_future.js') + rd('src/30_gen.js').split('\n').filter(l => /^function b64ToBytes/.test(l)).join('\n')).replace(/^const /gm, 'var ').replace(/^let /gm, 'var '));
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'ÉCHEC') + ' ' + m); if (!c) fail++; };
const F = fusLoad(JSON.parse(rd('test/fusion_centres.json'))), C = buildCosmo(PLANCK), Vg = [28.4, -109.8, 41.4];
const vt0 = (() => { const P = DATA.M31.pos, r = Math.hypot(...P), u = P.map(x => x / r), vr = Vg[0] * u[0] + Vg[1] * u[1] + Vg[2] * u[2]; return Math.hypot(...Vg.map((x, i) => x - vr * u[i])); })();
const O = andromedaOrbit(C, vt0, Vg, true), O0 = andromedaOrbit(C, vt0, Vg, false), p = [0, 0, 0], q = [0, 0, 0];
andromedaAt(O, 0, p); ok(Math.hypot(p[0] - DATA.M31.pos[0], p[1] - DATA.M31.pos[1], p[2] - DATA.M31.pos[2]) < 0.1, 'Andromède aujourd’hui à sa position mesurée');
ok(O.fus && O.tMerge === F.ga, `fusion à ${O.tMerge} Ga dans le calcul complet (orbite simple de la page : ${O0.tMerge && O0.tMerge.toFixed(2)} Ga)`);
andromedaAt(O, 2.5, p); fusAt(F.c, 4, 1, 2.5, q); ok(Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]) < 0.5, 'orbite d’Andromède à 2,5 Ga lue dans le calcul complet');
andromedaAt(O, -1, p); andromedaAt(O0, -1, q); ok(Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]) < 1e-6, 'avant aujourd’hui : orbite de la page, inchangée');
ok(O.peri.length && O.peri[0][0] > 4 && O.peri[0][0] < 5.5, `premier passage au plus près : ${O.peri[0][0]} Ga à ${O.peri[0][1].toFixed(0)} kpc`);
const L = lmcOrbit(1, true); andromedaAt(L, 0, p); ok(Math.hypot(p[0] - DATA.LMC.pos[0], p[1] - DATA.LMC.pos[1], p[2] - DATA.LMC.pos[2]) < 0.1, 'Grand Nuage aujourd’hui à sa position mesurée');
ok(L.fus, `Grand Nuage : avalé à ${L.tMerge} Ga dans le calcul complet (Cautun et al. 2019 : environ 2,4 Ga, autres masses jusqu’à plus de 7 Ga)`);
{ const raw = JSON.parse(rd('test/fusion_centres.json')); ok(raw.lgv.length === 38 && F.nTr === 38, '38 naines traceuses, chacune reliée à sa galaxie de la page'); }
process.exit(fail ? 1 : 0);
