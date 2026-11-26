/* S2, étape 1 : mesurer l'erreur de l'approximation des épicycles (25_future.js) contre une
   intégration exacte de l'orbite, dans LE MÊME potentiel (bulbe de Hernquist + disque de
   Miyamoto-Nagai + halo NFW, paramètres GAL de 20_physics.js), pour les étoiles réelles du
   catalogue principal (HYG). Pas un test vert/rouge : un relevé, pour décider où l'approximation suffit. */
const { loadUnivers } = require('./_load');

const {
  DATA, TAU, GAL, G_KPC, KPC_LY, SUN_UVW, b64ToBytes, initStarKin, epicyclePos,
} = loadUnivers({
  gen: ['data.js', 'data2.js', 'ephem.js', 'data3.js'],
  src: ['20_physics.js', '25_future.js', '30_gen.js'],
});

const TU = 0.9777922; /* 1 kpc/(km/s) en milliards d'années */
function acc(x, y, z, a) { /* accélération en (km/s)²/kpc */
  const R2 = x * x + y * y, r = Math.sqrt(R2 + z * z) || 1e-9;
  let ar = -G_KPC * GAL.Mb / ((r + GAL.ab) * (r + GAL.ab)); /* Hernquist */
  const xs = r / GAL.rs;
  ar += -GAL.GMs * (Math.log(1 + xs) - xs / (1 + xs)) / (r * r); /* NFW */
  const B = Math.sqrt(z * z + GAL.bd * GAL.bd), D2 = R2 + (GAL.ad + B) * (GAL.ad + B), D3 = D2 * Math.sqrt(D2), gm = G_KPC * GAL.Md;
  a[0] = ar * x / r - gm * x / D3;
  a[1] = ar * y / r - gm * y / D3;
  a[2] = ar * z / r - gm * z * (GAL.ad + B) / (B * D3);
}

const N = DATA.STARS_N, geo = new Uint16Array(b64ToBytes(DATA.STARS_GEO).buffer), p = new Float32Array(N * 3);
for (let i = 0; i < N; i++) {
  const lon = geo[i * 3] / 65535 * TAU, lat = (geo[i * 3 + 1] / 65535 - 0.5) * Math.PI, d = Math.pow(10, geo[i * 3 + 2] / 65535 * 5.5 - 1), cl = Math.cos(lat);
  p.set([d * cl * Math.cos(lon), d * cl * Math.sin(lon), d * Math.sin(lat)], i * 3);
}
const sunGal0 = DATA.SGRA_GAL.map(x => -x * GAL.R0), K = initStarKin(p, N, sunGal0), M = K.M, vq = new Int16Array(b64ToBytes(DATA.STARS_VEL).buffer);

/* conditions initiales, comme dans initStarKin (vitesses HYG : repère galactique héliocentrique, km/s) */
const STEP = 1, sel = [];
for (let i = 0; i < N; i += STEP) sel.push(i);
const n = sel.length, X = new Float64Array(n * 3), V = new Float64Array(n * 3), a = [0, 0, 0];
sel.forEach((i, k) => {
  const g = [0, 1, 2].map(c => (M[0][c] * p[i * 3] + M[1][c] * p[i * 3 + 1] + M[2][c] * p[i * 3 + 2]) / KPC_LY);
  for (let c = 0; c < 3; c++) { X[k * 3 + c] = sunGal0[c] + g[c]; V[k * 3 + c] = SUN_UVW[c] + vq[i * 3 + c] / 20; }
});
const CHECK = [0.05, 0.2, 0.5, 1.0], dt = 0.0005 / TU; /* pas de 0,5 Ma, saut de grenouille */
const res = {};
let t = 0, ci = 0;
const t0 = Date.now();
for (let k = 0; k < n; k++) {
  acc(X[k * 3], X[k * 3 + 1], X[k * 3 + 2], a);
  for (let c = 0; c < 3; c++) V[k * 3 + c] += 0.5 * dt * a[c];
}
while (ci < CHECK.length) {
  for (let k = 0; k < n; k++) {
    for (let c = 0; c < 3; c++) X[k * 3 + c] += dt * V[k * 3 + c];
    acc(X[k * 3], X[k * 3 + 1], X[k * 3 + 2], a);
    for (let c = 0; c < 3; c++) V[k * 3 + c] += dt * a[c];
  }
  t += dt * TU;
  if (t >= CHECK[ci] - 1e-9) {
    const e = [], g = [0, 0, 0];
    sel.forEach((i, k) => {
      epicyclePos(K.epi, i * 10, t, g, 0);
      e.push(Math.hypot(g[0] - X[k * 3], g[1] - X[k * 3 + 1], g[2] - X[k * 3 + 2]) * 1000);
    });
    e.sort((u, v) => u - v);
    const q = f => e[Math.floor(f * (e.length - 1))];
    res[CHECK[ci]] = { med: q(0.5), p90: q(0.9), p99: q(0.99), over100: e.filter(v => v > 100).length / e.length };
    console.log(`+${CHECK[ci]} Ga : écart épicycles / orbite exacte (pc) médiane ${q(0.5).toFixed(0)} | 90 % ${q(0.9).toFixed(0)} | 99 % ${q(0.99).toFixed(0)} | > 100 pc : ${(res[CHECK[ci]].over100 * 100).toFixed(1)} % des étoiles`);
    ci++;
  }
}
console.log(`${n} étoiles, ${((Date.now() - t0) / 1000).toFixed(0)} s`);
