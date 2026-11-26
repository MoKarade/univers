/* Lot G (G1, G2) : gravité mutuelle du système solaire contre l'éphéméride JPL (Horizons, DE440/DE441).
   Références : app/test/nbody_ref.json (pipeline/gravite/fetch_horizons.py). */
const fs = require('fs');
const path = require('path');
const { loadUnivers } = require('./_load');

const U = loadUnivers({ gen: ['nbody.js'], src: ['20_physics.js', '21_nbody.js'] });
const { nbFromData, nbAdvanceTo, nbBary, nbCreate, nbEnergy, nbStep, NB_GM_SUN } = U;
const H = JSON.parse(fs.readFileSync(path.join(__dirname, 'nbody_ref.json'), 'utf8'));
const AU_KM = 149597870.7;

let fail = 0;
const ok = (c, m) => { console.log((c ? 'ok   ' : 'ÉCHEC') + ' ' + m); if (!c) fail++; };
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const nrm = a => Math.hypot(a[0], a[1], a[2]);
const sep = (a, b) => Math.acos(Math.max(-1, Math.min(1, (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (nrm(a) * nrm(b))))) * 206264.806;

/* Contrôle aux dates de référence, vers le passé et vers l'avenir, avec l'état calé (pas de 4 jours, celui de la page).
   1650 et 2450 ont servi au calage ; 1850, 2000, 2126 et 2350 sont des contrôles indépendants.
   Tolérances : écart angulaire vu du Soleil (″). */
const TOL = { mercury: 5, venus: 2, emb: 2, mars: 2, jupiter: 1, saturn: 1, uranus: 1, neptune: 1, pluto: 1, ceres: 3, vesta: 3, pallas: 3, hygiea: 3 };
const dates = Object.keys(H.checks).sort((a, b) => Math.abs(H.checks[a].sun.jd - H.epoch.sun.jd) - Math.abs(H.checks[b].sun.jd - H.epoch.sun.jd));
for (const d of dates) {
  const R = H.checks[d], S = nbFromData(), t0 = Date.now();
  nbAdvanceTo(S, R.sun.jd, S.dt);
  const b = nbBary(S), sun = [b[0], b[1], b[2]], ans = [];
  const dSun = nrm(sub(sun, R.sun.r)) * AU_KM;
  S.names.forEach((k, i) => {
    const p = [b[(i + 1) * 3], b[(i + 1) * 3 + 1], b[(i + 1) * 3 + 2]];
    const e = sep(sub(p, sun), sub(R[k].r, R.sun.r));
    ans.push([k, e]);
  });
  const worst = ans.filter(([k, e]) => !(e < TOL[k]));
  ok(worst.length === 0, `${d} (${((R.sun.jd - H.epoch.sun.jd) / 365.25).toFixed(0)} ans, ${Date.now() - t0} ms) : ` + ans.map(([k, e]) => k + ' ' + e.toFixed(1) + '″').join(', '));
  ok(dSun < 1000, `${d} : Soleil autour du centre de masse à ${dSun.toFixed(0)} km de Horizons (distance au centre ${(nrm(sun) * AU_KM).toFixed(0)} km)`);
}

/* G1 : le Soleil hors du centre de masse, plus loin que son propre rayon la plupart du temps (Jupiter domine). */
{
  const r = nrm(H.epoch.sun.r) * AU_KM;
  ok(r > 3e5 && r < 1.6e6, `Soleil à ${Math.round(r)} km du centre de masse aujourd'hui (Horizons), entre 0,4 et 2,3 rayons solaires`);
}

/* Énergie sur 100 ans (10 × 913 pas de 4 jours = 36 520 j) : symplectique, pas de dérive. */
{
  const S = nbCreate(H.epoch, H.epoch.sun.jd), E0 = nbEnergy(S);
  let m = 0;
  for (let k = 0; k < 10; k++) { nbStep(S, 4, 913); m = Math.max(m, Math.abs(nbEnergy(S) / E0 - 1)); }
  ok(m < 1e-7, `énergie conservée à ${m.toExponential(1)} près sur 100 ans`);
}

/* Réversibilité : aller 1 000 ans puis revenir. */
{
  const S = nbCreate(H.epoch, H.epoch.sun.jd), q = S.Q.slice();
  nbStep(S, 4, 91310);
  nbStep(S, -4, 91310);
  let e = 0;
  for (let i = 0; i < q.length; i++) e = Math.max(e, Math.abs(S.Q[i] - q[i]));
  ok(e * AU_KM < 100, `aller-retour 1 000 ans : écart ${(e * AU_KM).toFixed(2)} km`);
}

/* Relativité : avance du périhélie de Mercure, Mercure seule autour du Soleil, avec et sans la correction (43″/siècle). */
{
  const peri = gr => {
    const S = {
      N: 1,
      jd: 0,
      gm: new U.Float64Array([0]),
      Q: new U.Float64Array(H.epoch.mercury.r.map((x, c) => x - H.epoch.sun.r[c])),
      V: new U.Float64Array(H.epoch.mercury.v.map((x, c) => x - H.epoch.sun.v[c])),
    };
    const K = U.NB_GR_K;
    if (!gr) U.NB_GR_K = 0;
    nbStep(S, 0.5, 36525 * 2 * 10);
    U.NB_GR_K = K;
    const r = [...S.Q], v = [...S.V], mu = NB_GM_SUN;
    const rv = r[0] * v[0] + r[1] * v[1] + r[2] * v[2], rn = nrm(r), v2 = v[0] ** 2 + v[1] ** 2 + v[2] ** 2;
    const e = r.map((x, c) => ((v2 - mu / rn) * x - rv * v[c]) / mu);
    return Math.atan2(e[1], e[0]);
  };
  const d = (peri(true) - peri(false)) * 206264.806 / 10;
  ok(Math.abs(d - 43) < 1.5, `avance relativiste du périhélie de Mercure : ${d.toFixed(2)}″ par siècle (attendu 42,98″)`);
}

process.exit(fail ? 1 : 0);
