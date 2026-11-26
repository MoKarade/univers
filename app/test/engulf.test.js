/* Test de calcul « engloutissement » (mission 2, tâche R5) : spirale des planètes dans le Soleil géant,
   méthode de Schröder et Smith 2008 (marées + frottement), trajectoire du Soleil tirée de gen/sun_rgb.js. */
const { loadUnivers } = require('./_load');

const { DATA, SUN_NOW, SUN_TRACK, planetTide, tideAt } = loadUnivers({
  gen: ['data.js', 'sun_rgb.js'],
  src: ['20_physics.js', '25_future.js'],
});

const ME = 5.9722e24, TIP = 12.167 - SUN_NOW;
let bad = 0;
const check = (ok, msg) => { console.log((ok ? 'PASSE  ' : 'ÉCHEC  ') + msg); if (!ok) bad++; };
const P = a => planetTide(a, ME), before = p => ((TIP - p.tEng) * 1e3).toFixed(2) + ' Ma avant le sommet';
const e1 = P(1.0), e12 = P(1.2), me = planetTide(DATA.JPL1.mercury[0], 3.3011e23), ve = planetTide(DATA.JPL1.venus[0], 4.8675e24);
check(isFinite(e1.tEng), 'corps de la masse de la Terre à 1,00 UA : englouti, ' + before(e1) + ' (publié : environ 0,5 Ma avant)');
check(!isFinite(e12.tEng), 'corps de la masse de la Terre à 1,20 UA : survit (publié : survie au-delà de 1,15 UA)');
check(isFinite(me.tEng) && isFinite(ve.tEng), 'Mercure et Vénus englouties : ' + before(me) + ', ' + before(ve));
/* seuil de survie, par dichotomie */
let lo = 1.0, hi = 1.2;
for (let i = 0; i < 12; i++) { const m = (lo + hi) / 2; if (isFinite(P(m).tEng)) lo = m; else hi = m; }
console.log('       seuil de survie calculé : ' + lo.toFixed(3) + ' UA (publié : 1,15 UA)');
check(lo > 1.0 && lo < 1.2, 'seuil de survie entre 1,00 et 1,20 UA');
/* ordre et écarts publiés : Mercure 3,8 Ma puis Vénus 1,0 Ma avant la Terre */
check(me.tEng < ve.tEng && ve.tEng < e1.tEng, 'ordre : Mercure, puis Vénus, puis la Terre');
/* rayon affiché : décroît de façon continue sur au moins 30 images à la vitesse de l'événement (1,5 Ma par seconde, 60 images par seconde) */
for (const [n, p] of [['Mercure', me], ['Vénus', ve]]) {
  let mx = 0, tm = 0;
  const T = p.tab;
  for (let i = 0; i < T.length; i += 2) if (T[i + 1] > mx) { mx = T[i + 1]; tm = T[i]; }
  const frames = (p.tEng - tm) * 1e9 / 1.5e6 * 60;
  let mono = true, prev = Infinity;
  for (let k = 0; k <= 60; k++) { const f = tideAt(p, tm + (p.tEng - tm) * k / 60); if (f > prev + 1e-9) mono = false; prev = f; }
  check(frames >= 30 && mono, n + ' : orbite qui se resserre sur ' + Math.round(frames) + ' images à vitesse normale, sans remonter (au plus haut : ' + mx.toFixed(3) + ' fois l’actuelle)');
}
/* SUN_TRACK contre la table 1 de Schröder et Smith 2008 (âge, L, T, R, M) : chaque point publié doit y être */
const TABLE1 = [
  ['ZAMS', 0.00, 0.70, 5596, 0.89, 1.000], ['aujourd’hui', 4.58, 1.00, 5774, 1.00, 1.000],
  ['MS:hottest', 7.13, 1.26, 5820, 1.11, 1.000], ['MS:final', 10.00, 1.84, 5751, 1.37, 1.000],
  ['RGB:tip', 12.17, 2730, 2602, 256, 0.668], ['ZA-He', 12.17, 53.7, 4667, 11.2, 0.668],
  ['AGB:tip', 12.30, 2090, 3200, 149, 0.546], ['AGB:tip-TP', 12.30, 4170, 3467, 179, 0.544],
];
for (const [n, ...v] of TABLE1) {
  const row = SUN_TRACK.find(r => Math.abs(r[0] - v[0]) < 0.0051 && Math.abs(r[1] - v[1]) <= 1e-9 * v[1] + 1e-9 && r[2] === v[2] && r[3] === v[3] && r[4] === v[4]);
  check(!!row, 'table 1, ' + n + ' : présent dans SUN_TRACK' + (row ? ' (âge ' + row[0] + ')' : ''));
}
console.log('       marge de 1,00 UA : engloutie ' + ((TIP - e1.tEng) * 1e3).toFixed(3) + ' Ma avant le sommet, sur une montée de ' + ((TIP - (10.0 - SUN_NOW)) * 1e3).toFixed(0) + ' Ma (publié : environ 0,5 Ma avant)');
if (bad) { console.log('engloutissement : ÉCHEC (' + bad + ')'); process.exit(1); } else console.log('engloutissement : PASSE');
