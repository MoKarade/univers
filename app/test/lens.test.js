/* S6 — lumière déviée par un trou noir sans rotation (Schwarzschild), app/src/27_lens.js.
   Références indépendantes du code :
    - champ faible : α = 4M/b + 15πM²/(4b²) + 128M³/(3b³) (développement publié, Keeton et Petters 2005) ;
    - champ fort : α = −ln(b/bc − 1) + ln(216(7 − 4√3)) − π (Bozza 2002, Schwarzschild), bc = √27 M ;
    - M87* : masse par la dynamique des étoiles, 6,6 milliards de masses solaires (Gebhardt et al. 2011, indépendante de l'image EHT),
      distance 16,8 Mpc ; anneau mesuré par l'EHT : 42 ± 3 microsecondes d'arc (EHT 2019, papier I). */
const { loadUnivers } = require('./_load');

const { GM_C2_SUN, lensDphi, lensPsiC, lensLut, lensLookup, lensSource } = loadUnivers({
  src: ['27_lens.js'],
});

let fails = 0;
const check = (ok, msg) => { console.log((ok ? 'OK    ' : 'ÉCHEC ') + msg); if (!ok) fails++; };
const psiOfB = (r, b) => Math.asin(b * Math.sqrt(1 - 2 / r) / r); /* angle de vue local pour un paramètre d'impact b */

/* 1. sans masse, la lumière va droit : Δφ = π − ψ */
{ let worst = 0; for (const psi of [0.3, 1.0, 1.5707, 2.0, 3.0]) worst = Math.max(worst, Math.abs(lensDphi(1e12, psi) - (Math.PI - psi)));
  check(worst < 1e-6, `trou noir très loin (r = 10¹² M) : trajet droit à ${worst.toExponential(1)} rad près`); }

/* 2. champ faible : la déviation suit le développement publié jusqu'au second ordre */
for (const b of [100, 1000]) { const r = 1e9, psi = psiOfB(r, b), got = lensDphi(r, psi) - (Math.PI - psi), ref = 4 / b + 15 * Math.PI / (4 * b * b) + 128 / (3 * b ** 3);
  check(Math.abs(got - ref) < 0.02 * 15 * Math.PI / (4 * b * b), `paramètre d'impact ${b} M : déviation ${got.toExponential(5)} rad, attendu ${ref.toExponential(5)}`); }

/* 3. champ fort : près de l'ombre, la déviation suit la limite logarithmique de Bozza 2002 */
{ const bc = Math.sqrt(27), r = 1e9, k = Math.log(216 * (7 - 4 * Math.sqrt(3))) - Math.PI;
  for (const e of [1e-3, 1e-4]) { const b = bc * (1 + e), psi = psiOfB(r, b), got = lensDphi(r, psi) - (Math.PI - psi), ref = -Math.log(e) + k;
    check(Math.abs(got - ref) < 0.01, `b = bc·(1 + ${e}) : déviation ${got.toFixed(4)} rad, Bozza ${ref.toFixed(4)}`); } }

/* 4. l'ombre trouvée par le calcul des rayons (et non par la formule) tombe à b = √27 M */
const shadowByRays = r => { let lo = 0, hi = Math.PI / 2; for (let k = 0; k < 60; k++) { const m = 0.5 * (lo + hi); if (lensDphi(r, m) < 0) lo = m; else hi = m; } return 0.5 * (lo + hi); };
for (const r of [8, 60, 1000]) { const s = shadowByRays(r), f = lensPsiC(r); check(Math.abs(s / f - 1) < 1e-6, `ombre vue de ${r} M : ${s.toExponential(6)} rad par les rayons, ${f.toExponential(6)} par b = √27 M`); }

/* 5. M87* : ombre obtenue par les rayons, avec la masse dynamique (indépendante de l'EHT) */
{ const M = 6.6e9, D = 16.8 * 3.0857e22, r = D / (GM_C2_SUN * M), d = 2 * shadowByRays(r) * 206264.806e6;
  check(d > 36 && d < 47, `M87* (6,6 milliards de masses solaires, Gebhardt 2011 ; 16,8 Mpc) : ombre de ${d.toFixed(1)} microsecondes d'arc ; anneau EHT 42 ± 3`); }

/* 6. table du shader : précise partout, y compris au bord de l'ombre et très loin du trou noir */
for (const r of [60, 3000, 1e6]) { const T = lensLut(r, 512); let worst = 0, wpsi = 0;
  for (const q of [1e-4, 1e-3, 0.01, 0.1, 1, 10, 100]) { const psi = T.psiC * (1 + q); if (psi >= Math.PI) continue; const d = lensDphi(r, psi), e = Math.abs(lensLookup(T, psi) - d) / Math.max(d - (Math.PI - psi), 1e-12); if (e > worst) { worst = e; wpsi = q; } }
  check(worst < 0.02, `table vue de ${r} M : déviation lue à ${(worst * 100).toFixed(2)} % près au pire (à ψ = ψc·(1 + ${wpsi}))`);
  check(lensLookup(T, T.psiC * 0.9999) === -1 && lensLookup(T, T.psiC * 1.0001) > 0, `table vue de ${r} M : bord de l'ombre exact (ψc = ${T.psiC.toExponential(4)} rad)`); }

/* 7. direction de la source (calcul du shader) : sans effet loin du trou noir ; ailleurs, la source est plus près du trou noir que l'image */
{ const T = lensLut(1e9, 512), c = [0, 0, -1], v = [Math.sin(0.3), 0, -Math.cos(0.3)], s = lensSource(T, v, c);
  check(Math.hypot(s[0] - v[0], s[1] - v[1], s[2] - v[2]) < 1e-6, 'trou noir lointain : la source est dans la direction de vue');
  const T2 = lensLut(60, 512), ang = u => Math.acos(-u[2]);
  for (const psi of [1.0, 0.2]) { const v2 = [Math.sin(psi), 0, -Math.cos(psi)], s2 = lensSource(T2, v2, c), a = lensDphi(60, psi) - (Math.PI - psi), side = psi - a; /* angle de la source : ψ − α (négatif : de l'autre côté) */
    check(s2 && Math.abs(ang(s2) - Math.abs(side)) < 2e-3 && Math.sign(s2[0]) === Math.sign(side) && Math.abs(s2[1]) < 1e-12, `vue de 60 M à ${psi} rad du trou noir (déviation ${a.toFixed(3)} rad) : source à ${ang(s2).toFixed(4)} rad, ${side > 0 ? 'du même côté, plus près du trou noir' : 'de l’autre côté du trou noir'}`); }
  check(lensSource(T2, [0, 0, -1], c) === null, 'regard droit sur le trou noir : ombre'); }

console.log(fails ? `\n${fails} échec(s)` : '\nlentille gravitationnelle : tout est vert');
process.exit(fails ? 1 : 0);
