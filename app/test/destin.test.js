/* Destin des étoiles : modèles MIST (gen/mist_life.js) et âges Gaia FLAME (flame_hip.txt), tels que la page les lit. */
const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
global.DATA = {};
vm.runInThisContext((rd('gen/data.js') + rd('gen/data3.js') + rd('gen/mist_life.js') + rd('src/20_physics.js') + rd('src/25_future.js') + rd('src/30_gen.js')).replace(/^const /gm, 'var ').replace(/^let /gm, 'var '));
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'ÉCHEC') + ' ' + m); if (!c) fail++; };
/* Séquence principale du Soleil : MIST 9,9 Ga ; Schröder et Smith 2008 (modèle de la page) : fin vers 10,0 Ga d'âge */
const [ms1] = mistLife(1); ok(Math.abs(ms1 / 1000 - 10.0) < 0.3, `1 masse solaire : séquence principale ${(ms1 / 1000).toFixed(2)} Ga (Schröder et Smith 2008 : 10,0)`);
const [ms20] = mistLife(20), [ms2] = mistLife(2); ok(ms20 > 7 && ms20 < 11 && ms2 > 900 && ms2 < 1300, `20 masses solaires : ${ms20.toFixed(1)} Ma ; 2 masses solaires : ${ms2.toFixed(0)} Ma`);
const F = flameLoad(rd('test/flame_hip.txt')); ok(F.size > 38000, `${F.size} âges Gaia FLAME lus`);
/* Une étoile de la table : la date centrale et la fourchette encadrent bien la valeur centrale */
const [hip, v] = F.entries().next().value, L = starLife(4.8, 0.65, 1, hip);
ok(L[6] === 1 && Math.abs(-L[0] - v[0]) < 1e-9 && Math.min(L[7], L[8]) <= L[1] + 1e-6 && Math.max(L[7], L[8]) >= L[1] - 1e-6, `HIP ${hip} : âge ${v[0]} Ma, fin de séquence principale ${L[1].toFixed(0)} Ma dans la fourchette ${L[7].toFixed(0)} à ${L[8].toFixed(0)}`);
const N = starLife(4.8, 0.65, 1, 0); ok(N[6] === 0 && N[7] <= N[1] && N[1] <= N[8], 'sans âge mesuré : date tirée dans la fourchette, signalée inconnue');
/* Aujourd'hui, chaque étoile du catalogue garde son éclat et sa couleur mesurés : même calcul que le shader des étoiles (40_render.js) à t = 0 */
{ const aux = b64ToBytes(DATA.STARS_AUX), hipA = new Uint32Array(b64ToBytes(DATA.STARS_HIP).buffer); let bad = 0, n = 0, ex = '';
  for (let i = 0; i < DATA.STARS_N; i++) { const mag = aux[i * 2] / 8 - 10, bv = aux[i * 2 + 1] / 100 - 0.5, L = starLife(mag, bv, i, hipA[i]); if (!L[6]) continue; n++;
    const [tB, tM, tD, fate] = L, uT = 0, gNow = fate > 1.5 && fate < 3.5, sn = (fate > 0.5 && fate < 1.5) || (fate > 2.5 && fate < 3.5), x0 = Math.min(Math.max(-tB / Math.max(tM - tB, 1e-3), 0), 1); let M = mag, red = 0;
    if (uT < tM) { const x = (uT - tB) / Math.max(tM - tB, 1e-3); M = gNow ? mag + 3 + 1.5 * (1 - x) : mag - 0.7 * (x - x0); }
    else if (uT < tD) { const g = (uT - tM) / Math.max(tD - tM, 1e-3); if (gNow) { const g0 = Math.min(Math.max(-tM / Math.max(tD - tM, 1e-3), 0), 1); M = g < g0 ? mag + 3 * (1 - g / Math.max(g0, 1e-3)) : mag - 1.2 * (g - g0); } else { M = mag - 0.7 * (1 - x0) + ((mag - (sn ? 2 : 4.5)) - (mag - 0.7 * (1 - x0))) * g; red = g; } }
    if (Math.abs(M - mag) > 0.02 || red > 0.02) { bad++; if (!ex) ex = 'HIP ' + hipA[i] + ' : ' + (M - mag).toFixed(2) + ' mag'; } }
  ok(n > 17000 && bad === 0, `${n} étoiles avec âge Gaia : ${bad} changeraient d’éclat ou de couleur aujourd’hui ${ex}`); }
process.exit(fail ? 1 : 0);
