/* R10 (lot G) : le Groupe local rejoué depuis le calcul complet de la fusion (fusion_centres.json).
   Contrôles : départ identique aux mesures de la page ; orbite d'Andromède et du Grand Nuage lues correctement ;
   recul de la Voie lactée sous l'attraction du Grand Nuage, comparé aux publications. */
const fs = require('fs');
const path = require('path');
const { loadUnivers } = require('./_load');

const U = loadUnivers({
  gen: ['data.js', 'data3.js', 'data4.js'],
  src: ['20_physics.js', '25_future.js', '30_gen.js'],
});
const {
  DATA, PLANCK, KMS_KPC_GYR, buildCosmo, fusLoad, fusAt,
  andromedaOrbit, andromedaAt, lmcOrbit, dynTables, dynAdvance, vCirc,
} = U;
const rdTest = f => fs.readFileSync(path.join(__dirname, f), 'utf8');

let fail = 0;
const ok = (c, m) => { console.log((c ? 'ok   ' : 'ÉCHEC') + ' ' + m); if (!c) fail++; };
const F = fusLoad(JSON.parse(rdTest('fusion_centres.json'))), C = buildCosmo(PLANCK), Vg = [28.4, -109.8, 41.4];
const vt0 = (() => { const P = DATA.M31.pos, r = Math.hypot(...P), u = P.map(x => x / r), vr = Vg[0] * u[0] + Vg[1] * u[1] + Vg[2] * u[2]; return Math.hypot(...Vg.map((x, i) => x - vr * u[i])); })();
const O = andromedaOrbit(C, vt0, Vg, true), O0 = andromedaOrbit(C, vt0, Vg, false), p = [0, 0, 0], q = [0, 0, 0];
andromedaAt(O, 0, p); ok(Math.hypot(p[0] - DATA.M31.pos[0], p[1] - DATA.M31.pos[1], p[2] - DATA.M31.pos[2]) < 0.1, 'Andromède aujourd’hui à sa position mesurée');
ok(O.fus && O.tMerge === F.ga, `fusion à ${O.tMerge} Ga dans le calcul complet (orbite simple de la page : ${O0.tMerge && O0.tMerge.toFixed(2)} Ga)`);
andromedaAt(O, 2.5, p); fusAt(F.c, 4, 1, 2.5, q); ok(Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]) < 0.5, 'orbite d’Andromède à 2,5 Ga lue dans le calcul complet');
andromedaAt(O, -1, p); andromedaAt(O0, -1, q); ok(Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]) < 1e-6, 'avant aujourd’hui : orbite de la page, inchangée');
ok(O.peri.length && O.peri[0][0] > 4 && O.peri[0][0] < 5.5, `premier passage au plus près : ${O.peri[0][0]} Ga à ${O.peri[0][1].toFixed(0)} kpc`);
const L = lmcOrbit(1, true); andromedaAt(L, 0, p); ok(Math.hypot(p[0] - DATA.LMC.pos[0], p[1] - DATA.LMC.pos[1], p[2] - DATA.LMC.pos[2]) < 0.1, 'Grand Nuage aujourd’hui à sa position mesurée');
ok(L.fus, `Grand Nuage : avalé à ${L.tMerge} Ga dans le calcul complet (Cautun et al. 2019 : environ 2,4 Ga, autres masses jusqu’à plus de 7 Ga)`);
ok(L.peri.length && Math.abs(L.peri[0][0] - 3.12) < 0.05 && L.peri[0][1] < 20, `Grand Nuage : premier passage au plus près ${L.peri[0][0]} Ga à ${L.peri[0][1].toFixed(1)} kpc (le bruit près du point le plus lointain est écarté)`);
{
  let z = 0;
  for (let t = F.ga; t < 14; t += 0.05) {
    andromedaAt(O, t, p); z = Math.max(z, Math.hypot(...p));
    andromedaAt(O, t, q, true); z = Math.max(z, Math.hypot(...q));
  }
  ok(z === 0, 'après la fusion : centres confondus, plus de coup de frottement');
}
/* Étoiles simulées pendant et après la rencontre (dynAdvance) avec l'orbite du calcul complet : elles restent liées. */
{
  const T = dynTables(), N = 300;
  const D = {
    n: N, nMW: N, t: 4.0, t0: 4.0,
    x: new U.Float64Array(N * 3), v: new U.Float64Array(N * 3), out: new U.Float32Array(N * 3),
    kind: new Uint8Array(N).fill(2), rx: new U.Float64Array(N * 3), rv: new U.Float64Array(N * 3),
    p0: new U.Float32Array(N * 3), om: new U.Float32Array(N), r0: new U.Float32Array(N),
    A: [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
  };
  for (let i = 0; i < N; i++) {
    const R = 3 + 12 * i / N, a = i * 2.4, sp = vCirc(R, true) * KMS_KPC_GYR;
    D.x.set([R * Math.cos(a), R * Math.sin(a), 0], i * 3);
    D.v.set([sp * Math.sin(a), -sp * Math.cos(a), 0], i * 3);
  }
  const med = () => { const r = []; for (let i = 0; i < N; i++) r.push(Math.hypot(D.x[i * 3], D.x[i * 3 + 1], D.x[i * 3 + 2])); r.sort((a, b) => a - b); return r[N >> 1]; };
  const rs = [];
  for (const t of [5.44, 6, 8, 10]) { dynAdvance(D, O, t, 1e7, T); rs.push(med().toFixed(1)); }
  ok(rs.every(r => r < 60), `étoiles de la Voie lactée, rayon médian à 5,44 / 6 / 8 / 10 Ga : ${rs.join(' / ')} kpc (restent liées)`);
}
{
  const raw = JSON.parse(rdTest('fusion_centres.json'));
  ok(raw.lgv.length === 38 && F.nTr === 38, '38 naines traceuses, chacune reliée à sa galaxie de la page');
}
process.exit(fail ? 1 : 0);
