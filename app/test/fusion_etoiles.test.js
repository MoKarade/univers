/* R10 (lot G) : images des étoiles du calcul complet, telles que la page les lit (fusImagesInit, fusFrame, fusFill).
   Fixture : le dernier paquet (image de 10 Ga) et la liste des paquets ; centres : fusion_centres.json. */
const fs = require('fs'), vm = require('vm'), path = require('path'), root = path.join(__dirname, '..');
const rd = f => fs.readFileSync(path.join(root, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
global.DATA = {};
vm.runInThisContext((rd('gen/data.js') + rd('gen/data3.js') + rd('gen/data4.js') + rd('src/20_physics.js') + rd('src/25_future.js') + rd('src/30_gen.js').split('\n').filter(l => /^function b64ToBytes/.test(l)).join('\n')).replace(/^const /gm, 'var ').replace(/^let /gm, 'var '));
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'ÉCHEC') + ' ' + m); if (!c) fail++; };
const F = fusLoad(JSON.parse(rd('test/fusion_centres.json'))), I = fusImagesInit(JSON.parse(rd('test/fusion_images.json')));
ok(I.n === F.n && I.NS === 30000 && I.cnt.mw === 12000, `${I.n} images, ${I.NS} étoiles (${Object.entries(I.cnt).map(([k, v]) => k + ' ' + v).join(', ')})`);
let got = null; fusWant(F.tEnd, pk => { got = pk; return Promise.resolve(rd('test/' + pk.fichier)); });
setTimeout(() => {
  const k = I.n - 1, a = fusFrame(k); ok(!!a && got && got.premiere === 500, 'dernier paquet demandé et décodé');
  /* centre de chaque galaxie : médiane de ses étoiles, contre le centre du calcul (les étoiles sont relatives à la Voie lactée) */
  const med = (o, n, c) => { const v = []; for (let i = o; i < o + n; i++) v.push(a[i * 3 + c] * I.Q); v.sort((x, y) => x - y); return v[n >> 1]; };
  let o = 0; const p = [0, 0, 0];
  for (const [g, gi] of [['mw', 0], ['m31', 1], ['m33', 2], ['lmc', 3]]) { const n = I.cnt[g], m = [0, 1, 2].map(c => med(o, n, c)); fusAt(F.c, 4, gi, F.tEnd, p);
    const d = Math.hypot(m[0] - p[0], m[1] - p[1], m[2] - p[2]); let near = 0; for (let i = o; i < o + n; i++) if (Math.hypot(a[i * 3] * I.Q - p[0], a[i * 3 + 1] * I.Q - p[1], a[i * 3 + 2] * I.Q - p[2]) < 10) near++;
    /* grandes galaxies : la médiane tombe sur le centre ; Triangle et Grand Nuage, en partie arrachés, gardent un cœur autour du centre calculé */
    if (g === 'mw' || g === 'm31') ok(d < 3, `${g} : centre médian de ses étoiles à ${d.toFixed(2)} kpc du centre du calcul à 10 Ga`);
    else console.log(`info  ${g} : ${Math.round(100 * near / n)} % de ses étoiles à moins de 10 kpc du centre calculé à 10 Ga (le reste est arraché ; médiane à ${d.toFixed(0)} kpc) ; à 10 Ga, le Triangle et le Grand Nuage sont en grande partie dispersés dans le calcul`); o += n; }
  const out = new Float32Array(I.NS * 3); ok(fusFill(out, F.tEnd - 1e-6) === false, 'image manquante (499) : pas d’interpolation inventée, la page attend et le dit');
  /* Suite après 10 Ga : un appel à tailAdvance respecte son budget de temps (l'image ne gèle pas), sur les 30 000 étoiles de la dernière image */
  { global.performance = global.performance || require('perf_hooks').performance; const T = dynTables(), n = I.NS, D = { n, t: 10, x: new Float64Array(n * 3), v: new Float64Array(n * 3), out: new Float32Array(n * 3) };
    for (let j = 0; j < n * 3; j++) D.x[j] = a[j] * I.Q;
    for (let i = 0; i < n; i++) { const j = i * 3, R = Math.max(Math.hypot(D.x[j], D.x[j + 1]), 0.3), vc = vCirc(R, true) * KMS_KPC_GYR * 1.5; D.v[j] = vc * D.x[j + 1] / R; D.v[j + 1] = -vc * D.x[j] / R; }
    /* le budget est vérifié entre deux tranches de 5 Ma : un appel dure au plus le budget plus une tranche. La durée d'une tranche
       dépend de la machine (les machines de contrôle de GitHub sont plusieurs fois plus lentes que le PC) : elle est mesurée ici. */
    const ts = performance.now(); tailAdvance(D, D.t + 0.005, 1e9, T); const slice = performance.now() - ts;
    let worst = 0; for (let k = 0; k < 5; k++) { const t0 = performance.now(); tailAdvance(D, 12, 14, T); worst = Math.max(worst, performance.now() - t0); }
    ok(worst <= 14 + 2 * slice + 5, `tailAdvance : appel le plus long ${worst.toFixed(1)} ms pour un budget de 14 ms et une tranche de 5 Ma de ${slice.toFixed(1)} ms sur cette machine`); }
  process.exit(fail ? 1 : 0);
}, 50);
