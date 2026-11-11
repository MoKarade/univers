/* ============================================================================
   UTILITAIRES
   ============================================================================ */
function makeRng(seed) {
  let a = seed >>> 0;
  const r = function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  r.gauss = () => { let u = 0; while (u === 0) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(TAU * r()); };
  r.range = (lo, hi) => lo + (hi - lo) * r();
  r.dir = () => { const z = 2 * r() - 1, p = TAU * r(), s = Math.sqrt(1 - z * z); return [s * Math.cos(p), s * Math.sin(p), z]; };
  return r;
}
function b64ToBytes(s) { const bin = atob(s), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }
const mulM = (M, v) => [M[0][0] * v[0] + M[0][1] * v[1] + M[0][2] * v[2], M[1][0] * v[0] + M[1][1] * v[1] + M[1][2] * v[2], M[2][0] * v[0] + M[2][1] * v[1] + M[2][2] * v[2]];
const vlen = v => Math.hypot(v[0], v[1], v[2]);
const vnorm = v => { const l = vlen(v) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };
const vcross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const eqToEcl = v => { const c = Math.cos(EPS_J2000), s = Math.sin(EPS_J2000); return [v[0], c * v[1] + s * v[2], -s * v[1] + c * v[2]]; };

/** Couleur d'une étoile à partir de son indice B−V (corps noir approché), adoucie vers le blanc comme la voit l'œil. */
function bvToRgb(bv) {
  bv = clamp(bv, -0.4, 2.0);
  const T = 4600 * (1 / (0.92 * bv + 1.7) + 1 / (0.92 * bv + 0.62)), t = T / 100;
  let r, g, b;
  if (t <= 66) { r = 255; g = 99.4708025861 * Math.log(t) - 161.1195681661; b = t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307; }
  else { r = 329.698727446 * Math.pow(t - 60, -0.1332047592); g = 288.1221695283 * Math.pow(t - 60, -0.0755148492); b = 255; }
  const f = x => Math.pow(clamp(x, 0, 255) / 255, 2.2) * 0.72 + 0.28;
  return [f(r), f(g), f(b)];
}

/* ---- formats français ---- */
const NBSP = '\u00a0', NNBSP = '\u202f';
const nf = (x, d) => x.toLocaleString('fr-FR', { minimumFractionDigits: d, maximumFractionDigits: d });
function sig(x, n) {                       // n chiffres significatifs, à la française
  if (!isFinite(x)) return '∞';
  if (x === 0) return '0';
  const d = clamp(n - 1 - Math.floor(Math.log10(Math.abs(x))), 0, 6);
  return nf(x, d);
}
const SUPS = '⁰¹²³⁴⁵⁶⁷⁸⁹', supInt = k => (k < 0 ? '⁻' : '') + String(Math.abs(k)).split('').map(c => SUPS[+c]).join('');
function fmtPow(x, n, unit) { let e = Math.floor(Math.log10(x) + 1e-9), mant = x / Math.pow(10, e); if (mant >= 9.95) { mant = 1; e++; } return (Math.abs(mant - 1) > 0.05 ? sig(mant, Math.max(n, 2)) + NBSP + '×' + NBSP : '') + '10' + supInt(e) + NBSP + unit; }
/** Longueurs sous le kilomètre : m, mm, µm, nm, pm (millième de nanomètre), fm (millionième de nanomètre), puis puissances de dix. */
function fmtSmall(m, n) { n = n || 3; const U = [[1, 'm'], [1e-3, 'mm'], [1e-6, 'µm'], [1e-9, 'nm'], [1e-12, 'pm'], [1e-15, 'fm']]; for (const u of U) if (m >= u[0] * 0.9995) return sig(m / u[0], n) + NBSP + u[1]; return fmtPow(m, n, 'm'); }
function fmtDist(m, n) {                   // m en mètres
  n = n || 3;
  if (m < 1000) return fmtSmall(m, n);
  const km = m / 1e3, au = m / AU, ly = m / LY;
  if (km < 1e6) return sig(km, n) + NBSP + 'km';
  if (au < 0.05) return sig(km / 1e6, n) + NBSP + 'millions de km';
  if (au < 5000) return sig(au, n) + NBSP + 'UA';
  if (ly < 1000) return sig(ly, n) + NBSP + 'années-lumière';
  if (ly < 1e6) return sig(ly, n) + NBSP + 'années-lumière';
  if (ly < 1e9) return sig(ly / 1e6, n) + NBSP + 'millions d’années-lumière';
  return sig(ly / 1e9, n) + NBSP + 'milliards d’années-lumière';
}
function fmtDistShort(m, n) {
  n = n || 2;
  if (m < 1000) return fmtSmall(m, n);
  const km = m / 1e3, au = m / AU, ly = m / LY;
  if (km < 1e6) return sig(km, n) + NBSP + 'km';
  if (au < 0.05) return sig(km / 1e6, n) + NBSP + 'M km';
  if (au < 5000) return sig(au, n) + NBSP + 'UA';
  if (ly < 1e6) return sig(ly, n) + NBSP + 'al';
  if (ly < 1e9) return sig(ly / 1e6, n) + NBSP + 'millions d’al';
  return sig(ly / 1e9, n) + NBSP + 'milliards d’al';
}
function fmtLightTime(m) {                 // temps mis par la lumière pour parcourir m
  const s = m / C_LIGHT;
  if (s < 1) { const U = [[1e-3, 'millisecondes'], [1e-6, 'microsecondes'], [1e-9, 'nanosecondes']]; for (const u of U) if (s >= u[0] * 0.9995) return sig(s / u[0], 2) + NBSP + u[1]; return fmtPow(s, 2, 's'); }
  if (s < 90) return sig(s, 2) + NBSP + 's';
  if (s < 5400) return Math.round(s / 60) + NBSP + 'min';
  if (s < 2 * DAY_S) return sig(s / 3600, 2) + NBSP + 'h';
  if (s < 400 * DAY_S) return sig(s / DAY_S, 2) + NBSP + 'jours';
  return fmtYears(s / YEAR_S);
}
function fmtYears(y) {
  const a = Math.abs(y);
  if (a < 1e4) return sig(a, 3) + NBSP + (a >= 2 ? 'ans' : 'an');
  if (a < 1e6) return sig(a, 3) + NBSP + 'ans';
  if (a < 1e9) return sig(a / 1e6, 3) + NBSP + 'millions d’années';
  return sig(a / 1e9, 3) + NBSP + 'milliards d’années';
}
const MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
function fmtDate(ms, withTime) {
  const d = new Date(ms);
  if (isNaN(d.getTime())) return '';
  const y = d.getFullYear();
  let s = d.getDate() + (d.getDate() === 1 ? 'er' : '') + NBSP + MONTHS[d.getMonth()] + NBSP + (y > 0 ? y : (1 - y) + NBSP + 'av. J.-C.');
  if (withTime) s += ', ' + d.getHours() + NBSP + 'h' + NBSP + String(d.getMinutes()).padStart(2, '0');
  return s;
}
// Calendrier : jour julien ↔ date civile (Meeus). Avant le 15 octobre 1582, calendrier julien.
function jdFromCal(y, m, d, julian) { if (m <= 2) { y -= 1; m += 12; } let B = 0; if (!julian) { const A = Math.floor(y / 100); B = 2 - A + Math.floor(A / 4); } return Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + d + B - 1524.5; }
function calFromJd(jd) { const Z = Math.floor(jd + 0.5), f = jd + 0.5 - Z, greg = Z >= 2299161; let A = Z; if (greg) { const al = Math.floor((Z - 1867216.25) / 36524.25); A = Z + 1 + al - Math.floor(al / 4); }
  const B = A + 1524, C = Math.floor((B - 122.1) / 365.25), D = Math.floor(365.25 * C), E = Math.floor((B - D) / 30.6001), d = B - D - Math.floor(30.6001 * E), m = E < 14 ? E - 1 : E - 13, y = m > 2 ? C - 4716 : C - 4715; return { y, m, d, f, greg }; }
function fmtJd(jd, withTime) { const c = calFromJd(jd); let s = c.d + (c.d === 1 ? 'er' : '') + NBSP + MONTHS[c.m - 1] + NBSP + (c.y > 0 ? c.y : (1 - c.y) + NBSP + 'av. J.-C.');
  if (withTime) { const mn = Math.min(1439, Math.round(c.f * 1440)); s += ', ' + Math.floor(mn / 60) + NBSP + 'h' + NBSP + String(mn % 60).padStart(2, '0'); } if (!c.greg) s += ' (calendrier julien)'; return s; }
function fmtSpeed(secPerSec) {             // durée simulée écoulée par seconde réelle
  const s = secPerSec;
  if (s < 1.5) return 'temps réel';
  if (s < 90) return sig(s, 2) + NBSP + 's par seconde';
  if (s < 5400) return sig(s / 60, 2) + NBSP + 'min par seconde';
  if (s < 1.5 * DAY_S) return sig(s / 3600, 2) + NBSP + 'h par seconde';
  if (s < 45 * DAY_S) return sig(s / DAY_S, 2) + NBSP + 'jours par seconde';
  if (s < 1.5 * YEAR_S) return sig(s / (YEAR_S / 12), 2) + NBSP + 'mois par seconde';
  return fmtYears(s / YEAR_S) + ' par seconde';
}

/* ============================================================================
   GÉNÉRATEURS PROCÉDURAUX (tout ce qui n'est pas une donnée mesurée)
   ============================================================================ */

/* Rotation mesurée des galaxies à disque du Groupe local (avec la Voie lactée et Andromède, ce sont les quatre seules).
   L : direction de l'axe de rotation dans le repère équatorial, règle de la main droite (Andrae et Jahnke 2011, d'après les mesures citées).
   v(r) : vitesse de rotation en km/s à r kpc du centre. Le dessin des bras reste un schéma ; ils tournent d'un bloc, comme pour Andromède. */
const LG_SPIN = [
  { key: 'Galaxie du Triangle', L: [0.67170, -0.47655, 0.56721], v: r => 120 * (1 - Math.exp(-r / 2.2)), vTxt: '100 km/s à 4 kpc du centre, 120 à 130 km/s plus loin', turn: [5, 0], sense: 'sens des aiguilles d’une montre, vue de la Terre', src: 'Vitesse : Corbelli et al. 2014 ; axe et sens : Andrae et Jahnke 2011, Brunthaler et al. 2005' },
  { key: 'Grand Nuage de Magellan', L: [-0.29699, -0.46945, -0.83152], v: r => 91.7 * Math.min(1, r / 1.2), vTxt: '92 km/s (± 19) hors de la région centrale', turn: [3, 0], sense: 'sens des aiguilles d’une montre, vu de la Terre', src: 'van der Marel et Kallivayalil 2014 ; axe : Andrae et Jahnke 2011' },
];
LG_SPIN.forEach(s => { const r = s.turn[0]; s.turn[1] = TAU * r / (s.v(r) * KMS_KPC_RADGYR) * 1000; });      // durée d'un tour, en millions d'années, au rayon indiqué

/** Nuage d'Oort (hypothétique) : disque interne de Hills + coquille sphérique externe. Unité : UA. */
function genOort(N, seed) {
  const rng = makeRng(seed), pos = new Float32Array(N * 3), look = new Float32Array(N * 2);
  for (let i = 0; i < N; i++) {
    const inner = rng() < 0.3;
    const r = inner ? 2000 * Math.pow(10, rng()) : 20000 * Math.pow(5, Math.pow(rng(), 0.8));
    const d = rng.dir();
    if (inner) d[2] *= 0.35 + 0.65 * smoothstep(3000, 20000, r);
    const n = vnorm(d);
    pos.set([n[0] * r, n[1] * r, n[2] * r], i * 3);
    look[i * 2] = 0.7 + rng(); look[i * 2 + 1] = 0.25 + 0.75 * rng();
  }
  return { N, pos, look };
}

/* ---- Voie lactée ---- */
const ARMS = [   // rayon (kpc) sur la ligne Soleil–centre, côté Soleil ; bras majeurs partant des extrémités de la barre
  { key: 'scutum', name: 'Bras Écu-Croix', r0: 4.95, major: true, labelBeta: -60 },
  { key: 'sagittarius', name: 'Bras du Sagittaire', r0: 7.0, major: false, labelBeta: -55 },
  { key: 'perseus', name: 'Bras de Persée', r0: 9.9, major: true, labelBeta: -35 },
  { key: 'norma', name: 'Bras de la Règle', r0: 14.0, major: false, labelBeta: 40 },
];
const armR = (arm, beta) => arm.r0 * Math.exp(-beta * Math.tan(GAL.PITCH));
/** Coordonnées galactocentriques (x vers l'opposé du Soleil... voir sunGal) à partir du rayon et de l'azimut β (dans le sens de rotation). */
const galXY = (r, beta) => [r * Math.cos(Math.PI - beta), r * Math.sin(Math.PI - beta)];

function genGalaxy(N, NG, seed) {
  const rng = makeRng(seed), T = N + NG;
  const pos = new Float32Array(T * 3), om = new Float32Array(T * 2), col = new Float32Array(T * 3), look = new Float32Array(T * 2);
  const tanP = Math.tan(GAL.PITCH), oBar = GAL.OMEGA_BAR * KMS_KPC_RADGYR, oArm = GAL.OMEGA_ARMS * KMS_KPC_RADGYR;
  const sech2 = h => h * Math.atanh(clamp(2 * rng() - 1, -0.995, 0.995));
  const expR = (Rd, rmax) => { let r; do { r = -Rd * Math.log(rng() * rng()); } while (r > rmax); return r; };   // densité surfacique exponentielle
  const armLen = ARMS.map(a => ({ a, b0: Math.log(a.r0 / 4.4) / tanP, b1: Math.log(a.r0 / (a.major ? 19 : 16.5)) / tanP }));
  const clumps = [];
  for (let c = 0; c < 340; c++) { const A = armLen[(rng() * 4) | 0], beta = rng.range(A.b1, A.b0), r = armR(A.a, beta) + rng.gauss() * 0.3; clumps.push([r, beta]); }
  const barDir = galXY(1, GAL.BAR_ANGLE), barPerp = [-barDir[1], barDir[0]];
  const put = (i, x, y, z, w1, w2, c, size, bright) => { pos.set([x, y, z], i * 3); om.set([w1, w2], i * 2); col.set(c, i * 3); look.set([size, bright], i * 2); };
  const tint = (c, k) => [c[0] * (1 + rng.gauss() * k), c[1] * (1 + rng.gauss() * k), c[2] * (1 + rng.gauss() * k)];

  const sampleArm = (spread) => {
    const A = armLen[(rng() < 0.62 ? (rng() < 0.5 ? 0 : 2) : (rng() < 0.5 ? 1 : 3))];
    let beta, r;
    do { beta = rng.range(A.b1, A.b0); r = armR(A.a, beta); } while (rng() > Math.exp(-(r - 4.4) / 7.5) * (0.35 + 0.65 * smoothstep(4.2, 5.2, r)));
    const sg = (0.26 + 0.032 * r) * spread;
    return [r + rng.gauss() * sg, beta + rng.gauss() * 0.04];
  };
  const sampleLocalArm = () => { const beta = rng.range(-28, 42) * DEG, r = 8.26 * Math.exp(-(beta - 9 * DEG) * Math.tan(11.4 * DEG)) + rng.gauss() * 0.22; return [r, beta]; };

  for (let i = 0; i < N; i++) {
    const u = rng();
    if (u < 0.36) {                                    // disque de vieilles étoiles : tourne à la vitesse locale (c'est lui que la matière noire accélère)
      const thick = rng() < 0.18, r = expR(3.4, 21), phi = rng() * TAU, z = sech2(thick ? 0.85 : 0.3) * (0.6 + r / 20);
      if (r < 2.2 && rng() < 0.7) { i--; continue; }
      const edge = 1 - smoothstep(15, 21, r);
      put(i, r * Math.cos(phi), r * Math.sin(phi), z, omegaGal(r, true), omegaGal(r, false), tint([1.0, 0.84, 0.66], 0.06), rng.range(0.04, 0.085), (0.25 + 0.75 * Math.pow(rng(), 2.5)) * (0.45 + 0.55 * edge));
    } else if (u < 0.76) {                             // bras spiraux : étoiles jeunes, régions de formation d'étoiles. Motif rigide (onde de densité)
      let rb;
      const v = rng();
      if (v < 0.07) rb = sampleLocalArm();
      else if (v < 0.4) { const c = clumps[(rng() * clumps.length) | 0]; rb = [c[0] + rng.gauss() * 0.16, c[1] + rng.gauss() * 0.16 / c[0]]; }
      else rb = sampleArm(1);
      const xy = galXY(Math.max(rb[0], 0.5), rb[1]), k = rng();
      let c, size, bright;
      if (k < 0.07) { c = tint([1.0, 0.30, 0.42], 0.1); size = rng.range(0.09, 0.2); bright = 0.5 + 0.5 * rng(); }                 // nébuleuses (hydrogène ionisé)
      else if (k < 0.16) { c = tint([0.55, 0.70, 1.0], 0.05); size = rng.range(0.06, 0.11); bright = 0.9 + 0.8 * rng(); }          // amas d'étoiles bleues très lumineuses
      else { c = tint([0.72, 0.82, 1.0], 0.07); size = rng.range(0.035, 0.075); bright = 0.22 + 0.7 * Math.pow(rng(), 2); }
      put(i, xy[0], xy[1], sech2(0.13), oArm, oArm, c, size, bright * Math.exp(-Math.max(rb[0] - 6, 0) / 16));
    } else if (u < 0.955) {                            // barre et bulbe : vieilles étoiles jaunes, rotation rigide
      const bar = rng() < 0.6;
      let xi, eta, z;
      if (bar) { xi = rng.gauss() * 1.75; eta = rng.gauss() * 0.52; z = rng.gauss() * 0.3; if (Math.abs(xi) > 4.6) { i--; continue; } }
      else { xi = rng.gauss() * 0.85; eta = rng.gauss() * 0.72; z = rng.gauss() * 0.55; }
      const x = barDir[0] * xi + barPerp[0] * eta, y = barDir[1] * xi + barPerp[1] * eta;
      put(i, x, y, z, oBar, oBar, tint([1.0, 0.74, 0.44], 0.06), rng.range(0.04, 0.09), 0.2 + 0.5 * Math.pow(rng(), 2));
    } else if (u < 0.975) {                            // noyau
      put(i, rng.gauss() * 0.16, rng.gauss() * 0.16, rng.gauss() * 0.11, oBar, oBar, [1.0, 0.86, 0.62], rng.range(0.04, 0.08), 0.5 + 0.5 * rng());
    } else {                                           // halo stellaire et amas globulaires : ne participent presque pas à la rotation
      const r = 1.5 * Math.pow(rng(), -0.55), d = rng.dir();
      if (r > 45) { i--; continue; }
      const gc = false;   // les amas globulaires sont désormais les vrais (catalogue Harris)
      put(i, d[0] * r, d[1] * r, d[2] * r * 0.8, 0, 0, [1.0, 0.86, 0.68], gc ? 0.11 : 0.05, gc ? 0.9 : 0.16);
    }
  }
  for (let g = 0; g < NG; g++) {                       // lueur diffuse : grandes taches douces qui donnent le fond lumineux
    const i = N + g, u = rng();
    if (u < 0.3) {
      const xi = rng.gauss() * (u < 0.15 ? 1.6 : 0.7), eta = rng.gauss() * 0.6;
      put(i, barDir[0] * xi + barPerp[0] * eta, barDir[1] * xi + barPerp[1] * eta, rng.gauss() * 0.25, oBar, oBar, [1.0, 0.72, 0.42], rng.range(0.55, 1.2), 0.04);
    } else if (u < 0.72) {
      const rb = sampleArm(1.3), xy = galXY(Math.max(rb[0], 0.5), rb[1]);
      put(i, xy[0], xy[1], rng.gauss() * 0.1, oArm, oArm, [0.55, 0.68, 1.0], rng.range(0.5, 1.1), 0.036 * Math.exp(-Math.max(rb[0] - 6, 0) / 14));
    } else {
      const r = expR(3.6, 19), phi = rng() * TAU;
      put(i, r * Math.cos(phi), r * Math.sin(phi), rng.gauss() * 0.2, omegaGal(r, true), omegaGal(r, false), [1.0, 0.82, 0.62], rng.range(0.7, 1.3), 0.03);
    }
  }
  return { N: T, pos, om, col, look };
}

/** Galaxies du Groupe local : nuages de points à la bonne place (kpc, relatif au centre de la Voie lactée). */
function genLocalGroup(scale, seed, gcRelSunKpc) {
  const rng = makeRng(seed), P = [], C = [], L = [], CN = [], ID = [], OM = [], AX = new Float32Array(104 * 3), SPIN = {}, eps = 23.4392911 * DEG, ce = Math.cos(eps), se = Math.sin(eps);
  const basis = n => { const z = vnorm(n), t = Math.abs(z[2]) < 0.9 ? [0, 0, 1] : [1, 0, 0], x = vnorm(vcross(t, z)); return [x, vcross(z, x), z]; };
  const out = [], GR = [], m31g = DATA.LOCAL.find(x => x.n.startsWith('Andromède')), m31c = [m31g.pos[0] * 1e3 - gcRelSunKpc[0], m31g.pos[1] * 1e3 - gcRelSunKpc[1], m31g.pos[2] * 1e3 - gcRelSunKpc[2]];
  for (const g of DATA.LOCAL) {
    const c = [g.pos[0] * 1e3 - gcRelSunKpc[0], g.pos[1] * 1e3 - gcRelSunKpc[1], g.pos[2] * 1e3 - gcRelSunKpc[2]];
    const own = g === m31g, grp = !own && !(DATA.LGV && DATA.LGV[out.length]) && Math.hypot(c[0] - m31c[0], c[1] - m31c[1], c[2] - m31c[2]) < 300 ? 1 : 0;      // une galaxie dont la vitesse est mesurée suit sa propre orbite, pas le groupe d'Andromède
    out.push({ g, c, c0: c.slice(), grp: grp || own ? 1 : 0, own });
    if (own) continue;
    const sp = LG_SPIN.find(q => g.n.indexOf(q.key) === 0) || null, rnd = rng.dir();      // le tirage au hasard reste fait pour toutes, afin de ne pas changer l'aspect des autres galaxies
    const zM = sp ? [-sp.L[0], -(sp.L[1] * ce + sp.L[2] * se), -(-sp.L[1] * se + sp.L[2] * ce)] : null, R = g.s, B = basis(g.normal || zM || rnd), wp = sp ? sp.v(0.6 * R) / (0.6 * R) * KMS_KPC_RADGYR : 0;
    if (sp) { AX.set(B[2], out.length * 3); SPIN[out.length - 1] = sp; }      // le modèle tourne dans le sens des aiguilles d'une montre autour de son axe z : on oriente donc z à l'opposé de L
    const add = (x, y, z, col, size, bright, arm) => { const rr = Math.hypot(x, y), w = sp ? (arm ? wp : sp.v(Math.max(rr, 0.05)) / Math.max(rr, 0.05) * KMS_KPC_RADGYR) : 0; OM.push(w, w); P.push(c[0] + B[0][0] * x + B[1][0] * y + B[2][0] * z, c[1] + B[0][1] * x + B[1][1] * y + B[2][1] * z, c[2] + B[0][2] * x + B[1][2] * y + B[2][2] * z); C.push(col[0], col[1], col[2]); L.push(size, bright); CN.push(c[0], c[1], c[2]); GR.push(grp); ID.push(out.length); };
    if (g.k === 'spiral') {
      const n = Math.round((R > 15 ? 9000 : 3600) * scale), pitch = Math.tan(16 * DEG);
      for (let i = 0; i < n; i++) {
        const u = rng();
        if (u < 0.2) add(rng.gauss() * R * 0.07, rng.gauss() * R * 0.07, rng.gauss() * R * 0.045, [1.0, 0.76, 0.48], R * 0.012, 0.5 + rng());
        else if (u < 0.55) { const r = Math.min(-R * 0.24 * Math.log(rng() * rng()), R * 1.1), p = rng() * TAU; add(r * Math.cos(p), r * Math.sin(p), rng.gauss() * R * 0.012, [1.0, 0.85, 0.68], R * 0.01, 0.25 + 0.5 * rng()); }
        else { const th = rng.range(0.4, 9.5), arm = rng() < 0.5 ? 0 : Math.PI, r = R * 0.12 * Math.exp(th * pitch) + rng.gauss() * R * 0.03; if (r > R * 1.05) { i--; continue; } add(r * Math.cos(th + arm), r * Math.sin(th + arm), rng.gauss() * R * 0.008, rng() < 0.08 ? [1.0, 0.35, 0.45] : [0.7, 0.8, 1.0], R * 0.01, 0.3 + 0.7 * rng(), true); }
      }
      for (let i = 0; i < 60 * scale; i++) { const r = R * 0.5 * rng(), p = rng() * TAU; add(r * Math.cos(p), r * Math.sin(p), 0, [1.0, 0.8, 0.6], R * 0.3, 0.03); }
    } else if (g.k === 'irr') {
      const n = Math.round(1700 * scale * (R / 4.5));
      for (let i = 0; i < n; i++) { const bar = rng() < 0.45; add(rng.gauss() * R * (bar ? 0.3 : 0.42), rng.gauss() * R * (bar ? 0.1 : 0.42), rng.gauss() * R * 0.1, rng() < 0.1 ? [1.0, 0.35, 0.45] : rng() < 0.5 ? [0.72, 0.82, 1.0] : [1.0, 0.86, 0.7], R * 0.014, 0.25 + 0.7 * rng()); }
      for (let i = 0; i < 16; i++) add(rng.gauss() * R * 0.25, rng.gauss() * R * 0.2, 0, [0.85, 0.88, 1.0], R * 0.4, 0.035);
    } else {
      const lum = g.mv !== undefined ? clamp((-g.mv - 2) / 11, 0.1, 1) : 1, n = Math.round((46 * scale + 14) * (0.3 + 0.7 * lum));
      for (let i = 0; i < n; i++) add(rng.gauss() * R * 0.5, rng.gauss() * R * 0.4, rng.gauss() * R * 0.4, [1.0, 0.84, 0.66], R * 0.05, (0.2 + 0.4 * rng()) * lum);
      add(0, 0, 0, [1.0, 0.84, 0.66], R * 0.9, 0.05 * lum);
    }
  }
  return { N: L.length / 2, pos: new Float32Array(P), col: new Float32Array(C), look: new Float32Array(L), cen: new Float32Array(CN), grp: new Float32Array(GR), id: new Float32Array(ID), om: new Float32Array(OM), axes: AX, spin: SPIN, centers: out, m31: out.find(o => o.own) };
}

/* ---- Toile cosmique : approximation de Zel'dovich --------------------------------
   Chaque point part d'une position initiale q et se déplace de D(t)·ψ(q), où ψ dérive
   d'un champ aléatoire gaussien (somme de modes de Fourier) et D(t) est le taux de
   croissance issu des équations de Friedmann. La densité locale vaut 1/|det(I + D·∂ψ/∂q)| :
   on stocke les trois valeurs propres de ∂ψ/∂q pour la recalculer à tout instant.
   Les amas réels (Vierge, Coma…) sont ajoutés comme puits à leur position mesurée.   */
async function genWeb(N, MODES, seed, onProgress) {
  const rng = makeRng(seed);
  const RC = 16, RW = 900, RMINQ = 2.4;
  const q = new Float32Array(N * 3), psi = new Float32Array(N * 3), eig = new Float32Array(N * 3), rnd = new Float32Array(N * 4);
  const kx = new Float64Array(MODES), ky = new Float64Array(MODES), kz = new Float64Array(MODES), ux = new Float64Array(MODES), uy = new Float64Array(MODES), uz = new Float64Array(MODES), ph = new Float64Array(MODES), am = new Float64Array(MODES), ak = new Float64Array(MODES);
  let s2 = 0;
  for (let m = 0; m < MODES; m++) {
    const lam = 30 * Math.pow(760 / 30, (m + rng()) / MODES), k = TAU / lam, d = rng.dir();
    ux[m] = d[0]; uy[m] = d[1]; uz[m] = d[2]; kx[m] = d[0] * k; ky[m] = d[1] * k; kz[m] = d[2] * k; ph[m] = rng() * TAU;
    am[m] = Math.pow(lam / 60, 0.62); ak[m] = am[m] * k; s2 += ak[m] * ak[m] / 2;
  }
  const norm = 1.02 / Math.sqrt(s2);                         // écart-type de la surdensité linéaire aujourd'hui ≈ 1
  for (let m = 0; m < MODES; m++) { am[m] *= norm; ak[m] *= norm; }
  const rand = (x, y, z, o) => { let a = 0, b = 0, c = 0; for (let m = 0; m < MODES; m++) { const s = am[m] * Math.sin(kx[m] * x + ky[m] * y + kz[m] * z + ph[m]); a += ux[m] * s; b += uy[m] * s; c += uz[m] * s; } o[0] = a; o[1] = b; o[2] = c; };
  // ancrages : aux positions réelles (et chez nous), on annule le déplacement aléatoire pour que l'amas se forme au bon endroit
  const anchors = [{ c: [0, 0, 0], s: 9, B: 0.25, sg: 5, p: [0, 0, 0] }];
  for (const L of DATA.FAR) if (L.w) anchors.push({ c: L.pos, s: L.sg * 2.2, B: L.w, sg: L.sg, p: [0, 0, 0] });
  for (const A of anchors) rand(A.c[0], A.c[1], A.c[2], A.p);
  const nIn = Math.round(N * RC / (3 * (RW - RC) + RC)), tmp = [0, 0, 0];
  const CH = 5000;
  for (let i0 = 0; i0 < N; i0 += CH) {
    const i1 = Math.min(N, i0 + CH);
    for (let i = i0; i < i1; i++) {
      let r;
      if (i < nIn) { do { r = RC * Math.cbrt(rng()); } while (r < RMINQ); } else r = RC + (RW - RC) * rng();
      const d = rng.dir(), x = d[0] * r, y = d[1] * r, z = d[2] * r;
      let px = 0, py = 0, pz = 0, d00 = 0, d11 = 0, d22 = 0, d01 = 0, d02 = 0, d12 = 0;
      for (let m = 0; m < MODES; m++) {
        const th = kx[m] * x + ky[m] * y + kz[m] * z + ph[m], s = am[m] * Math.sin(th), c = ak[m] * Math.cos(th), a = ux[m], b = uy[m], e = uz[m];
        px += a * s; py += b * s; pz += e * s;
        d00 += c * a * a; d11 += c * b * b; d22 += c * e * e; d01 += c * a * b; d02 += c * a * e; d12 += c * b * e;
      }
      for (const A of anchors) {
        const rx = x - A.c[0], ry = y - A.c[1], rz = z - A.c[2], r2 = rx * rx + ry * ry + rz * rz;
        const g1 = Math.exp(-r2 / (2 * A.s * A.s));
        px -= A.p[0] * g1; py -= A.p[1] * g1; pz -= A.p[2] * g1;
        const g2 = A.B * Math.exp(-r2 / (2 * A.sg * A.sg)), is2 = 1 / (A.sg * A.sg);
        px -= g2 * rx; py -= g2 * ry; pz -= g2 * rz;
        d00 -= g2 * (1 - rx * rx * is2); d11 -= g2 * (1 - ry * ry * is2); d22 -= g2 * (1 - rz * rz * is2);
        d01 += g2 * rx * ry * is2; d02 += g2 * rx * rz * is2; d12 += g2 * ry * rz * is2;
      }
      // valeurs propres d'une matrice symétrique 3×3 (formule trigonométrique)
      const p1 = d01 * d01 + d02 * d02 + d12 * d12, qm = (d00 + d11 + d22) / 3;
      let e1, e2, e3;
      if (p1 < 1e-14) { e1 = d00; e2 = d11; e3 = d22; } else {
        const a0 = d00 - qm, a1 = d11 - qm, a2 = d22 - qm, p = Math.sqrt((a0 * a0 + a1 * a1 + a2 * a2 + 2 * p1) / 6);
        const b00 = a0 / p, b11 = a1 / p, b22 = a2 / p, b01 = d01 / p, b02 = d02 / p, b12 = d12 / p;
        const det = b00 * (b11 * b22 - b12 * b12) - b01 * (b01 * b22 - b12 * b02) + b02 * (b01 * b12 - b11 * b02);
        const phi = Math.acos(clamp(det / 2, -1, 1)) / 3;
        e1 = qm + 2 * p * Math.cos(phi); e3 = qm + 2 * p * Math.cos(phi + TAU / 3); e2 = 3 * qm - e1 - e3;
      }
      q.set([x, y, z], i * 3); psi.set([px, py, pz], i * 3); eig.set([e1, e2, e3], i * 3);
      rnd.set([rng() * Math.PI, 0.35 + 0.65 * rng(), rng(), 0.45 + 0.55 * rng()], i * 4);
    }
    if (onProgress) onProgress(i1 / N);
    await new Promise(r => setTimeout(r, 0));
  }
  return { N, q, psi, eig, rnd, RW };
}

/** Très grandes échelles : l'univers devient homogène. Points uniformes jusqu'au-delà de l'horizon. Unité : Mpc comobiles. */
function genFar(N, seed) {
  const rng = makeRng(seed), pos = new Float32Array(N * 3), rnd = new Float32Array(N * 2), RMAX = 19800, R0 = 250;
  for (let i = 0; i < N; i++) {
    const r = R0 + (RMAX - R0) * rng(), d = rng.dir();
    pos.set([d[0] * r, d[1] * r, d[2] * r], i * 3);
    rnd[i * 2] = rng(); rnd[i * 2 + 1] = 0.4 + 0.6 * rng();
  }
  return { N, pos, rnd, RMAX, R0 };
}

/** Galaxie spirale dans son propre repère (z = axe de rotation) : sert pour Andromède, qui tourne et se déplace. Unité : kpc. */
function genDiskGalaxy(R, n, seed) {
  const rng = makeRng(seed), pos = new Float32Array(n * 3), om = new Float32Array(n * 2), col = new Float32Array(n * 3), look = new Float32Array(n * 2), pitch = Math.tan(16 * DEG);
  const w = r => 250 / Math.max(r, 1.5) * KMS_KPC_RADGYR, wp = 18 * KMS_KPC_RADGYR;
  const put = (i, x, y, z, o, c, s, b) => { pos.set([x, y, z], i * 3); om.set([o, o], i * 2); col.set(c, i * 3); look.set([s, b], i * 2); };
  for (let i = 0; i < n; i++) {
    const u = rng();
    if (i >= n - 70) { const r = R * 0.5 * rng(), p = rng() * TAU; put(i, r * Math.cos(p), r * Math.sin(p), 0, w(r), [1.0, 0.8, 0.6], R * 0.3, 0.03); }
    else if (u < 0.2) { const x = rng.gauss() * R * 0.07, y = rng.gauss() * R * 0.07; put(i, x, y, rng.gauss() * R * 0.045, w(Math.hypot(x, y)), [1.0, 0.76, 0.48], R * 0.012, 0.5 + rng()); }
    else if (u < 0.55) { const r = Math.min(-R * 0.24 * Math.log(rng() * rng()), R * 1.1), p = rng() * TAU; put(i, r * Math.cos(p), r * Math.sin(p), rng.gauss() * R * 0.012, w(r), [1.0, 0.85, 0.68], R * 0.01, 0.25 + 0.5 * rng()); }
    else { const th = rng.range(0.4, 9.5), arm = rng() < 0.5 ? 0 : Math.PI, r = R * 0.12 * Math.exp(th * pitch) + rng.gauss() * R * 0.03; if (r > R * 1.05) { i--; continue; } put(i, r * Math.cos(th + arm), r * Math.sin(th + arm), rng.gauss() * R * 0.008, wp, rng() < 0.08 ? [1.0, 0.35, 0.45] : [0.7, 0.8, 1.0], R * 0.01, 0.3 + 0.7 * rng()); }
  }
  return { N: n, pos, om, col, look };
}
