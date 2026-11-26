/* Lot G (G2) : table des orbites sur des millions d'années (build_long.js), lue par la page (nbLongState), contre :
   1) l'intégration directe du même calcul (21_nbody.js) à des dates prises entre deux points de la table ;
   2) les séries VSOP87 de la page vers ±3 500 ans, où la page passe de l'une à l'autre.
   Extrait de la table : app/test/long_extrait.bin (±200 000 ans, mêmes données que le fichier chargé par la page). */
const fs = require('fs');
const path = require('path');
const { loadUnivers } = require('./_load');

const U = loadUnivers({
  gen: ['data.js', 'data2.js', 'ephem.js', 'nbody.js'],
  src: ['20_physics.js', '21_nbody.js'],
});
const {
  DEG, JD_J2000, solarSystemAt, nbFromData, nbStep, nbAdvanceTo, nbBary, nbLongLoad, nbLongState,
} = U;

const b = fs.readFileSync(path.join(__dirname, 'long_extrait.bin'));
const buf = b.buffer.slice(b.byteOffset, b.byteOffset + b.length);
nbLongLoad(buf);

let fail = 0;
const ok = (c, m) => { console.log((c ? 'ok   ' : 'ÉCHEC') + ' ' + m); if (!c) fail++; };
const lon = p => Math.atan2(p[1], p[0]);
const dAng = (a, c) => Math.abs(Math.atan2(Math.sin(a - c), Math.cos(a - c))) / DEG;
const KEYS = ['mercury', 'venus', 'emb', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune'];
const cloneS = S => ({
  N: S.N,
  jd: S.jd,
  names: S.names.slice(),
  gm: U.Float64Array.from(S.gm),
  Q: U.Float64Array.from(S.Q),
  V: U.Float64Array.from(S.V),
  dt: S.dt,
});

/* 1) contre l'intégration directe, enchaînée sur grille fixe ±S.dt (symplectique) + reste fractionnaire sur copie */
const TOL = { mercury: 0.2, venus: 0.2, emb: 0.2, mars: 0.3, jupiter: 0.6, saturn: 1.0, uranus: 1.0, neptune: 0.5 }; /* Uranus : ses oscillations avec Neptune et Saturne, plus rapides que 1 000 ans, ne sont pas dans la table */
for (const branch of [[-3499.2, -61234.5], [4321.7, 47777.7]]) {
  const S = nbFromData(), jd0 = S.jd, dir = branch[0] < 0 ? -1 : 1;
  for (const yrs of branch) {
    const jd = jd0 + yrs * 365.25;
    const whole = Math.floor(Math.abs(jd - S.jd) / S.dt);
    if (whole > 0) nbStep(S, dir * S.dt, whole);
    const snap = cloneS(S);
    nbAdvanceTo(snap, jd, S.dt);
    const bb = nbBary(snap), sun = [bb[0], bb[1], bb[2]], T = (jd - JD_J2000) / 36525, worst = [];
    for (const k of KEYS) {
      const i = snap.names.indexOf(k);
      const p = [bb[(i + 1) * 3] - sun[0], bb[(i + 1) * 3 + 1] - sun[1], bb[(i + 1) * 3 + 2] - sun[2]];
      const q = nbLongState(k, T).pos;
      worst.push([k, dAng(lon(p), lon(q))]);
    }
    ok(worst.every(([k, d]) => d < TOL[k]), `${yrs} ans : longitude lue dans la table contre le calcul direct : ` + worst.map(([k, d]) => k + ' ' + d.toFixed(2) + '°').join(', '));
  }
}

/* 2) raccord avec VSOP87 (la page passe de l'un à l'autre entre 3 000 et 4 000 ans) */
for (const yrs of [-3000, 3000]) {
  const T = yrs / 100 + 0.27, st = solarSystemAt(T, null, 0), w = [];
  for (const k of KEYS.filter(k => k !== 'emb')) w.push([k, dAng(lon(st.planets[k].pos), lon(nbLongState(k, T).pos))]);
  ok(w.every(([, d]) => d < 1.5), `${yrs} ans : table contre VSOP87 : ` + w.map(([k, d]) => k + ' ' + d.toFixed(2) + '°').join(', '));
}

process.exit(fail ? 1 : 0);
