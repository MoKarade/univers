/* ============================================================================
   AVENIR — ce que deviennent le Soleil, les étoiles et la galaxie quand le temps passe.
   ============================================================================ */
const hash01 = i => ((Math.imul(i + 7, 2246822519) >>> 0) / 4294967296);
const interp = (xs, ys, x) => { if (x <= xs[0]) return ys[0]; const n = xs.length; if (x >= xs[n - 1]) return ys[n - 1]; let i = 1; while (xs[i] < x) i++; return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1]); };

/* --------------------------------------------------------------------------
   Soleil : modèle de Schröder & Smith (2008). Les lignes marquées * sont les
   valeurs publiées ; les autres dessinent l'allure de la courbe entre elles
   (montée des géantes, puis refroidissement de la naine blanche).
   Colonnes : âge (Ga), luminosité, température (K), rayon, masse (en unités solaires).
   -------------------------------------------------------------------------- */
const SUN_NOW = 4.58, R_SUN_AU = 695700 / 149597870.7;
/* Naine blanche (R7) : refroidissement par la loi de Mestel (1952), t = 8,8 Myr · (A/12)⁻¹ · M^(5/7) · (μ/2)^(-2/7) · L^(-5/7), avec A = 14 (carbone et
   oxygène), μ = 2 et M = 0,5405 (masse finale publiée par Schröder et Smith 2008). Calculé, approché : sans cristallisation ni neutrinos.
   Température tirée de L et du rayon 0,0125 (Stefan-Boltzmann). t en milliards d'années depuis la naissance de la naine blanche (âge 12,30). */
const WD_K = 8.8e-3 * (12 / 14) * Math.pow(0.5405, 5 / 7), WD_L = t => Math.pow(t / WD_K, -7 / 5), WD_T = L => 5772 * Math.pow(L / (0.0125 * 0.0125), 0.25);
const SUN_TRACK = [
  [0.00, 0.70, 5596, 0.89, 1.000], /* * naissance */ [4.58, 1.00, 5774, 1.00, 1.000], /* * aujourd'hui */ [7.13, 1.26, 5820, 1.11, 1.000], /* * */ [10.00, 1.84, 5751, 1.37, 1.000], /* * fin de séquence principale */
  /* de 10,00 à 12,167 : branche des géantes rouges tirée de DATA.SUN_RGB (pipeline/build_sun_rgb.py : forme MIST, ancrages et perte de masse de Schröder et Smith 2008) */
  [12.167, 2730, 2602, 256, 0.668], /* * sommet de la branche des géantes rouges */ [12.1675, 53.7, 4667, 11.2, 0.668], /* * fusion de l'hélium */
  [12.27, 62, 4600, 12.4, 0.665], [12.293, 520, 3700, 56, 0.62], [12.30, 2090, 3200, 149, 0.546], /* * sommet de la branche asymptotique */ [12.3001, 4170, 3467, 179, 0.544], /* * pic du dernier pulse thermique (« AGB:tip-TP », âge 12,30 à l'arrondi de la table) */
  [12.3003, 2000, 8000, 23.3, 0.542], [12.3006, 1500, 30000, 1.43, 0.541], [12.301, 300, 100000, 0.058, 0.5405], [12.31, 0.88, 50000, 0.0125, 0.5405],
  [12.40, WD_L(0.1), WD_T(WD_L(0.1)), 0.0125, 0.5405], /* raccord à la loi de Mestel ; au-delà, voir sunState */
];
const SUN_PHASES = [[10.0, 'étoile de la séquence principale'], [11.6, 'sous-géante'], [12.167, 'géante rouge'], [12.27, 'géante en fusion d’hélium'], [12.3003, 'géante asymptotique'], [12.31, 'naine blanche en formation'], [1e9, 'naine blanche']];
let SUN_RGB_C = null; const SUN_RGB_T = () => SUN_RGB_C || (SUN_RGB_C = [SUN_TRACK[3]].concat(DATA.SUN_RGB.map(r => [r[0], r[1], r[2], r[3], r[4]]), [SUN_TRACK[4]]));      /* fin de séquence principale, montée calculée, sommet publié */
function sunState(tGyr, o) {
  o = o || {}; const age = SUN_NOW + tGyr; const T = age > 10.0 && age < 12.167 && typeof DATA !== 'undefined' && DATA.SUN_RGB ? SUN_RGB_T() : SUN_TRACK; let i = 1;
  if (age <= T[0][0]) i = 1; else if (age >= T[T.length - 1][0]) i = T.length - 1; else while (T[i][0] < age) i++;
  const a = T[i - 1], b = T[i], f = clamp((age - a[0]) / (b[0] - a[0]), 0, 1);
  o.age = age; o.L = Math.exp(lerp(Math.log(a[1]), Math.log(b[1]), f)); o.T = Math.exp(lerp(Math.log(a[2]), Math.log(b[2]), f)); o.R = Math.exp(lerp(Math.log(a[3]), Math.log(b[3]), f)); o.M = lerp(a[4], b[4], f);
  if (age > 12.40) { o.L = WD_L(age - 12.30); o.T = WD_T(o.L); o.R = 0.0125; o.M = 0.5405; }      /* naine blanche : loi de Mestel au-delà du raccord */
  o.phase = SUN_PHASES.find(p => age < p[0])[1]; return o;
}
/** Instant (Ga depuis aujourd'hui) où le Soleil géant avale une planète d'orbite actuelle a0 (UA). Seuil calé sur le résultat publié : il faut partir d'au moins 1,15 UA pour survivre. */
function engulfTime(a0) {
  if (a0 >= 1.15) return Infinity; const s = {};
  for (let age = 11.6; age <= 12.167; age += 0.00002) { sunState(age - SUN_NOW, s); if (s.R * R_SUN_AU >= 0.69 * a0 / s.M) return age - SUN_NOW; }
  return Infinity;
}
/* --------------------------------------------------------------------------
   R5 : orbite d'une planète pendant que le Soleil devient géant, méthode de Schröder et Smith 2008 (MNRAS 386, 155, § 4).
   On suit le moment cinétique Λ = m √(G M a) :
   - perte de masse du Soleil : Λ se conserve, donc a = Λ² / (m² G M) grandit quand M baisse (leur éq. 3) ;
   - marées (Zahn 1977, 1989 ; leur éq. 4) : dΛ/dt = 6 (λ₂ / t_f) q² M R² (R/a)⁶ (Ω − ω), Ω = 0, ω = √(G M / a³),
     q = m / M, t_f = (M R² / L)^(1/3), λ₂ = 0,019 α^(4/3), α = 2,0 pour log g ≥ 1,94, réduit linéairement à 1,67 à log g = 0 ;
   - frottement dans l'atmosphère étendue (Ostriker 1999 ; leurs éq. 5-6) : F = 3 · 4π ρ (G m / c_s)², c_s = 8 km/s,
     dΛ/dt = −F a, avec ρ = 4×10⁻⁹ kg/m³ à 5×10⁶ km de la surface et une hauteur d'échelle de 5×10⁶ km (leur § 4.3).
   La planète est engloutie quand a ≤ R. Le Soleil (L, R, T, M) vient de sunState : points publiés de la table 1 et, sur la branche des géantes rouges,
   la trajectoire DATA.SUN_RGB (forme du modèle MIST v1.2, Choi et al. 2016, ancrée sur le sommet publié, rayon calé sur la masse publiée au sommet).
   α : l'article écrit « α = 2.0 for log g < 1.94, reduced to 1.67 at log g = 0.0 » ; seule lecture cohérente, retenue ici : 2,0 au-dessus de log g = 1,94,
   puis réduction linéaire jusqu'à 1,67 à log g = 0 ; au sommet (log g ≈ −0,55) on retrouve λ₂ ≈ 0,038 publié.
   Rend une table [temps (Ga depuis aujourd'hui), a/a0] et la date d'engloutissement (Infinity si la planète survit).
   -------------------------------------------------------------------------- */
const TIDE = { G: 6.674e-11, MS: 1.98847e30, RS: 6.957e8, LS: 3.828e26, AU: 1.495978707e11, YR: 3.15576e7 };
function tideLambda2(M, R) { const lg = Math.log10(27400 * M / (R * R)), a = lg >= 1.94 ? 2.0 : 1.67 + 0.33 * Math.max(lg, 0) / 1.94; return 0.019 * Math.pow(a, 4 / 3); }
function planetTide(a0AU, mKg, tEnd) {
  const C = TIDE, s = {}, m = mKg, out = [0, 1]; let t = 0, M = C.MS, a = a0AU * C.AU, Lam = m * Math.sqrt(C.G * M * a), tEng = Infinity;
  tEnd = tEnd === undefined ? 12.31 - SUN_NOW : tEnd;
  while (t < tEnd) {
    sunState(t, s); M = s.M * C.MS; const R = s.R * C.RS, L = s.L * C.LS, age = s.age;
    a = Lam * Lam / (m * m * C.G * M); if (a <= R) { tEng = t; out.push(t, a / (a0AU * C.AU)); break; }
    const q = m / M, tf = Math.cbrt(M * R * R / L), om = Math.sqrt(C.G * M / (a * a * a)), lam2 = tideLambda2(s.M, s.R);
    const dTide = -6 * (lam2 / tf) * q * q * M * R * R * Math.pow(R / a, 6) * om, rho = 4e-9 * Math.exp(-(a - R - 5e9) / 5e9), dDrag = -3 * 4 * Math.PI * rho * Math.pow(C.G * m / 8e3, 2) * a, dL = dTide + dDrag;
    let dtY = age < 11.6 ? 2e6 : age < 12.1 ? 2e4 : 500;      /* pas en années : plus fin quand le Soleil enfle vite */
    if (dL < 0) dtY = Math.min(dtY, 0.002 * Lam / -dL / C.YR);
    dtY = Math.max(dtY, 0.01); Lam += dL * dtY * C.YR; t += dtY / 1e9;
    if (out.length < 2 || t - out[out.length - 2] > (age < 11.6 ? 0.05 : 2e-6)) out.push(t, a / (a0AU * C.AU));
  }
  return { tab: out, tEng };
}
/** Facteur d'orbite a/a0 à la date t (Ga) d'après une table de planetTide. */
function tideAt(P, t) { const T = P.tab, n = T.length / 2; if (t <= T[0]) return T[1]; if (t >= T[(n - 1) * 2]) return T[(n - 1) * 2 + 1];
  let lo = 0, hi = n - 1; while (hi - lo > 1) { const k = (lo + hi) >> 1; if (T[k * 2] <= t) lo = k; else hi = k; }
  const f = (t - T[lo * 2]) / (T[hi * 2] - T[lo * 2]); return T[lo * 2 + 1] + f * (T[hi * 2 + 1] - T[lo * 2 + 1]); }

/** Couleur (linéaire) d'un corps noir de température T. */
function tempRgb(T) { const t = clamp(T, 1500, 40000) / 100; let r, g, b;
  if (t <= 66) { r = 255; g = 99.4708025861 * Math.log(t) - 161.1195681661; b = t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307; } else { r = 329.698727446 * Math.pow(t - 60, -0.1332047592); g = 288.1221695283 * Math.pow(t - 60, -0.0755148492); b = 255; }
  const f = x => Math.pow(clamp(x, 0, 255) / 255, 2.2); return [f(r), f(g), f(b)]; }

/* --------------------------------------------------------------------------
   Autres étoiles : type, masse et durée de vie estimés à partir de l'éclat et de la
   couleur mesurés. L'âge réel d'une étoile isolée est mal connu : on lui tire une
   place au hasard dans sa vie (toujours la même pour une étoile donnée). C'est donc
   un modèle statistique, pas une prédiction étoile par étoile.
   Temps en millions d'années depuis aujourd'hui : [naissance, fin de séquence principale, mort].
   -------------------------------------------------------------------------- */
const MS_BV = [-0.33, -0.30, -0.20, -0.10, 0.0, 0.15, 0.30, 0.44, 0.58, 0.65, 0.74, 0.81, 1.15, 1.40, 1.60, 1.90];
const MS_MASS = [40, 17, 7, 3.5, 2.5, 1.9, 1.5, 1.3, 1.1, 1.0, 0.9, 0.85, 0.7, 0.55, 0.3, 0.1];
const MS_MV = [-5.5, -4.0, -1.5, 0.0, 1.0, 1.9, 2.6, 3.5, 4.4, 4.8, 5.5, 5.9, 7.3, 8.8, 11.5, 15.0];
const STAR_CLASS = ['naine (séquence principale)', 'géante', 'supergéante', 'naine blanche'];
const STAR_FATE_OVERRIDE = { 27989: 0.1 };     // Bételgeuse : explosion attendue d'ici 100 000 ans environ (ordre de grandeur)
/* --------------------------------------------------------------------------
   Durée de vie des étoiles : modèles d'évolution MIST v1.2 (Choi et al. 2016 ; Dotter 2016), [Fe/H] = 0 (gen/mist_life.js).
   Âge : mesuré par Gaia DR3 (FLAME, Creevey et al. 2023) pour 38 987 étoiles Hipparcos (fichier joint, flameLoad) ; la date
   montrée est celle de l'âge et de la masse centraux, la fiche donne la fourchette. Sans âge mesuré : âge tiré dans la
   fourchette possible (statistique), et la fiche dit « inconnu » avec la fourchette.
   -------------------------------------------------------------------------- */
let FLAME = null;
function flameLoad(txt) { const b = b64ToBytes(txt.trim()), dv = new DataView(b.buffer, b.byteOffset, b.length), n = b.length / 16, m = new Map();
  for (let k = 0; k < n; k++) { const o = k * 16, u = q => dv.getUint16(o + 4 + q * 2, true); m.set(dv.getInt32(o, true), [u(0), u(1), u(2), u(3) / 1000, u(4) / 1000, u(5) / 1000]); }      /* âges en Ma, masses en M☉ */
  FLAME = m; return m; }
/** Fin de la séquence principale et fin de vie (Ma) pour une masse (M☉), interpolées en log dans la grille MIST. */
function mistLife(m) {
  const R = DATA.MIST_LIFE ? DATA.MIST_LIFE.rows.filter(r => r[1]) : null; if (!R) return [1e4 * Math.pow(m, -2.5), 1.12e4 * Math.pow(m, -2.5)];
  const x = clamp(m, R[0][0], R[R.length - 1][0]); let k = 0; while (k < R.length - 2 && R[k + 1][0] < x) k++;
  const f = Math.log(x / R[k][0]) / Math.log(R[k + 1][0] / R[k][0]), L = (a, b) => Math.exp(Math.log(a) + (Math.log(b) - Math.log(a)) * f);
  return [L(R[k][1], R[k + 1][1]), L(R[k][2], R[k + 1][2])];
}
/* Destin selon la masse initiale : supernova au-dessus de 9 M☉, naine blanche sous 7 ; entre les deux, inconnu (limite
   discutée, Doherty et al. 2017) : montrée comme une naine blanche, et dit dans la fiche. */
const SN_MIN = 9, SN_UNC = 7;
function starLife(MV, bv, i, hip) {
  const h = hash01(i), h2 = hash01(i * 31 + 5), msMv = interp(MS_BV, MS_MV, bv), F = FLAME && hip ? FLAME.get(hip) : null;
  let cls = 0, mass, tMS, tB, tM, tD, src = 0, lo = 0, hi = 0;
  if (MV < -3.5) cls = 2; else if (MV > msMv + 3.5 && bv < 1.0) cls = 3; else if (MV < msMv - 2.2 && bv > 0.45) cls = 1;
  if (F && cls !== 3) {      /* âge et masse mesurés : dates centrales ; fourchette de la fin de séquence principale par les bornes à 16 et 84 % */
    src = 1; mass = F[3]; const age = F[0], [ms, end] = mistLife(mass); tMS = ms; tB = -age; tM = ms - age; tD = end - age;
    lo = mistLife(F[5])[0] - F[2]; hi = mistLife(F[4])[0] - F[1];
    /* l'aspect d'aujourd'hui reste celui mesuré : une étoile vue géante est géante maintenant (fin de séquence principale passée) ;
       une étoile que les modèles donnent déjà sortie de la séquence principale (âge FLAME, modèles BaSTI, plus grand que la durée MIST)
       est traitée de même, à partir de son éclat mesuré */
    if (cls === 1 || cls === 2 || tM < 0) { const dur = Math.max(end - ms, 1); if (tM >= 0) tM = -1e-3; tD = Math.max(tD, tM + 1e-3); if (tD - tM > dur) tD = tM + dur; if (cls === 0) cls = 1; }
  } else if (cls === 0) { mass = interp(MS_BV, MS_MASS, bv); const [ms, end] = mistLife(mass); tMS = Math.max(ms, 3); const amax = Math.min(tMS, 12000), age = (0.03 + 0.94 * h) * amax; tB = -age; tM = tB + tMS; tD = tB + Math.max(end, tMS * 1.12); lo = tMS - 0.97 * amax; hi = tMS - 0.03 * amax; }
  else if (cls === 1) { mass = 1.2 + 1.3 * h2; const [ms, end] = mistLife(mass); tMS = ms; const dur = end - ms; tM = -h * dur; tD = tM + dur; tB = tM - tMS; lo = 0; hi = dur; }
  else if (cls === 2) { mass = clamp(9 + (-3.5 - MV) * 3.5, 9, 40); const [ms, end] = mistLife(mass); tMS = Math.max(ms, 3); const dur = Math.max(end - ms, 0.1 * tMS); tM = -h * dur; tD = tM + dur; tB = tM - tMS; lo = 0; hi = dur; }
  else { mass = 0.6; tD = -(100 + 5000 * h); tM = tD - 300; tB = tD - 3000; }
  if (STAR_FATE_OVERRIDE[hip] !== undefined) { const d = STAR_FATE_OVERRIDE[hip] - tD; tD += d; tM += d; tB += d; }
  const sn = cls !== 3 && mass >= SN_MIN;
  return [tB, tM, tD, cls === 3 ? 4 : (cls === 0 ? 0 : 2) + (sn ? 1 : 0), mass, cls, src, lo, hi];
}
const bvTemp = bv => 4600 * (1 / (0.92 * bv + 1.7) + 1 / (0.92 * bv + 0.62));
const bvSpectral = bv => bv < -0.30 ? 'O' : bv < -0.02 ? 'B' : bv < 0.30 ? 'A' : bv < 0.58 ? 'F' : bv < 0.81 ? 'G' : bv < 1.40 ? 'K' : 'M';

/* --------------------------------------------------------------------------
   Mouvement des étoiles. Jusqu'à 3 millions d'années : ligne droite avec la vitesse
   mesurée (suffisant pour retrouver les passages proches publiés). Au-delà : chaque
   étoile suit son orbite dans la galaxie (approximation des épicycles : une rotation
   autour du centre, plus une oscillation radiale et une oscillation verticale).
   -------------------------------------------------------------------------- */
const SUN_UVW = [11.1, 242.24, 7.25];            // vitesse du Soleil dans la galaxie (km/s) : vers le centre, dans le sens de rotation, vers le nord
const KMS_LY_YR = 1 / 299792.458, KPC_LY = 3261.5637769, KMS_KPC_GYR = 1.0227121650456;
function epicycle(X, Y, Z, vX, vY, vZ) {
  const R = Math.hypot(X, Y), vR = (X * vX + Y * vY) / R, vt = Math.max(-(X * vY - Y * vX) / R, 40);
  let Rg = R; for (let k = 0; k < 4; k++) Rg = clamp(R * vt / vCirc(Rg, true), 0.8, 60);
  const vc = vCirc(Rg, true), Og = vc / Rg * KMS_KPC_GYR, beta = (Math.log(vCirc(Rg * 1.02, true)) - Math.log(vCirc(Rg * 0.98, true))) / (Math.log(1.02) - Math.log(0.98));
  const kap = Og * Math.sqrt(Math.max(2 * (1 + beta), 0.5)), nu = 73.5 * KMS_KPC_GYR * Math.exp(-(Rg - 8.2) / 5.2), lim = 0.6 * Rg;
  return [Rg, Og, kap, clamp(R - Rg, -lim, lim), clamp(vR * KMS_KPC_GYR / kap, -lim, lim), 2 * Og / (Rg * kap), Math.atan2(Y, X), nu, Z, vZ * KMS_KPC_GYR / nu];
}
function epicyclePos(e, o, t, out, j) {          // e : tableau de constantes, o : décalage, t : Ga
  const kt = e[o + 2] * t, ck = Math.cos(kt), sk = Math.sin(kt), x = e[o + 3] * ck + e[o + 4] * sk, R = e[o] + x;
  const phi = e[o + 6] - (e[o + 1] * t - e[o + 5] * (e[o + 3] * sk + e[o + 4] * (1 - ck))), nt = e[o + 7] * t;
  out[j] = R * Math.cos(phi); out[j + 1] = R * Math.sin(phi); out[j + 2] = e[o + 8] * Math.cos(nt) + e[o + 9] * Math.sin(nt);
}
function initStarKin(posEclLy, N, sunGal0, vqIn, vdiv, ecl) {      // ecl : vitesses fournies dans le repère écliptique (Gaia), sinon galactique (HYG)
  const M = DATA.M_GAL2ECL, vq = vqIn || new Int16Array(b64ToBytes(DATA.STARS_VEL).buffer), vd = vdiv || 20, K = { N, p0: posEclLy.slice(), ve: new (ecl ? Float32Array : Float64Array)(N * 3), epi: new (ecl ? Float32Array : Float64Array)(N * 10), sun: null, tmp: [0, 0, 0], ts: [0, 0, 0], vkms: new Float32Array(N), M };
  K.sun = Float64Array.from(epicycle(sunGal0[0], sunGal0[1], sunGal0[2], SUN_UVW[0], SUN_UVW[1], SUN_UVW[2]));
  for (let i = 0; i < N; i++) {
    let v = [vq[i * 3] / vd, vq[i * 3 + 1] / vd, vq[i * 3 + 2] / vd]; const ve = ecl ? v : mulM(M, v); if (ecl) v = [M[0][0] * ve[0] + M[1][0] * ve[1] + M[2][0] * ve[2], M[0][1] * ve[0] + M[1][1] * ve[1] + M[2][1] * ve[2], M[0][2] * ve[0] + M[1][2] * ve[1] + M[2][2] * ve[2]];
    const p = [posEclLy[i * 3], posEclLy[i * 3 + 1], posEclLy[i * 3 + 2]];
    K.ve.set([ve[0] * KMS_LY_YR, ve[1] * KMS_LY_YR, ve[2] * KMS_LY_YR], i * 3); K.vkms[i] = Math.hypot(v[0], v[1], v[2]);
    const g = [(M[0][0] * p[0] + M[1][0] * p[1] + M[2][0] * p[2]) / KPC_LY, (M[0][1] * p[0] + M[1][1] * p[1] + M[2][1] * p[2]) / KPC_LY, (M[0][2] * p[0] + M[1][2] * p[1] + M[2][2] * p[2]) / KPC_LY];
    K.epi.set(epicycle(sunGal0[0] + g[0], sunGal0[1] + g[1], sunGal0[2] + g[2], SUN_UVW[0] + v[0], SUN_UVW[1] + v[1], SUN_UVW[2] + v[2]), i * 10);
    if (!ecl) { if (!K.gx0) { K.gx0 = new Float64Array(N * 3); K.gv0 = new Float64Array(N * 3); } for (let c = 0; c < 3; c++) { K.gx0[i * 3 + c] = sunGal0[c] + g[c]; K.gv0[i * 3 + c] = SUN_UVW[c] + v[c]; } }      /* S2 : état initial exact, pour le calcul des orbites (26_orbits.js) */
  }
  return K;
}
/** Position du Soleil dans la galaxie (kpc, repère galactique centré sur le centre galactique) au temps t (Ga). */
function sunGalAt(K, t, out) { return sunOrbAt(K, t, out); }
/** Positions des étoiles par rapport au Soleil (années-lumière, repère écliptique) à l'instant tYears ; tEff (Ga) pour les orbites galactiques. */
function starPositions(K, tYears, tEff, out, i0, i1) {
  const at = Math.abs(tYears), w = smoothstep(3e6, 1.5e7, at), M = K.M, p0 = K.p0, ve = K.ve, g = K.tmp, s = K.ts;
  if (w > 0) starOrbSun(K, tEff, s);
  for (let i = i0 === undefined ? 0 : i0, n = i1 === undefined ? K.N : i1; i < n; i++) {
    const j = i * 3; let x = p0[j] + ve[j] * tYears, y = p0[j + 1] + ve[j + 1] * tYears, z = p0[j + 2] + ve[j + 2] * tYears;
    if (w > 0 && !(K.lin && K.lin[i])) { starOrbPos(K, i, tEff, g, 0); /* orbite exacte si prête (26_orbits.js), sinon épicycle. K.lin : étoile gardée en ligne droite (passage près du Soleil publié) */ const a = (g[0] - s[0]) * KPC_LY, b = (g[1] - s[1]) * KPC_LY, c = (g[2] - s[2]) * KPC_LY;
      const ex = M[0][0] * a + M[0][1] * b + M[0][2] * c, ey = M[1][0] * a + M[1][1] * b + M[1][2] * c, ez = M[2][0] * a + M[2][1] * b + M[2][2] * c;
      if (w >= 1) { x = ex; y = ey; z = ez; } else { x = lerp(x, ex, w); y = lerp(y, ey, w); z = lerp(z, ez, w); } }
    out[j] = x; out[j + 1] = y; out[j + 2] = z;
  }
}

/* --------------------------------------------------------------------------
   Andromède et la Voie lactée : problème à deux corps étendus, à partir de la position
   et de la vitesse mesurées. Chaque galaxie attire l'autre avec la masse contenue dans
   la distance qui les sépare ; l'énergie noire les écarte ; le frottement dynamique
   (formule de Chandrasekhar) freine les halos quand ils se pénètrent.
   Retourne la trajectoire d'Andromède vue du centre de la Voie lactée (kpc), tous les 10 Ma.
   -------------------------------------------------------------------------- */
const M31_MASS_RATIO = 1.5, HALO_EDGE = 220;
const mwMass = r => { const rr = Math.min(Math.max(r, 0.3), HALO_EDGE); return (v2Baryons(rr) + GAL.GMs * nfwShape(rr)) * rr / G_KPC; };
/* --------------------------------------------------------------------------
   R10 (lot G) : le calcul complet de la fusion (R9 : 300 000 particules qui s'attirent toutes, pipeline/fusion/calcul.py),
   rejoué pour le Groupe local. Fichier joint fusion_centres.json (pipeline/fusion/exporter_page.py) : centres de la
   Voie lactée, d'Andromède, du Triangle et du Grand Nuage, et 38 naines traceuses, toutes les 20 Ma de 0 à 10 Ga,
   dans le repère centré sur la Voie lactée. Valable seulement pour la vitesse d'Andromède « Gaia, 2025 » et la
   cosmologie de Planck, celles du calcul ; sinon la page garde ses propres orbites.
   -------------------------------------------------------------------------- */
let FUSC = null;
function fusLoad(j) {
  const dec = s => { const b = b64ToBytes(s); return new Float32Array(b.buffer, b.byteOffset, b.length / 4); };
  FUSC = { t: j.t, n: j.t.length, dt: j.t[1] - j.t[0], c: dec(j.c), sun: dec(j.sun), tr: dec(j.tr), lgv: j.lgv, nTr: j.lgv.length, ga: j.fusion_ga, drift: j.derive_max, vName: j.vitesse_m31, src: j.source };
  FUSC.tEnd = FUSC.t[FUSC.n - 1];
  return FUSC;
}
/** Position (kpc, repère centré sur la Voie lactée) lue dans le calcul complet : tableau arr, stride corps par date, corps k, date t (Ga). */
function fusAt(arr, stride, k, t, out) {
  const F = FUSC, x = clamp(t / F.dt, 0, F.n - 1.0001), i = x | 0, f = x - i, a = (i * stride + k) * 3, b = ((i + 1) * stride + k) * 3;
  out[0] = lerp(arr[a], arr[b], f); out[1] = lerp(arr[a + 1], arr[b + 1], f); out[2] = lerp(arr[a + 2], arr[b + 2], f); return out;
}
/* Extrema de la distance entre deux corps du calcul complet : [[t, d, 'min'|'max'], …]. */
function fusExtrema(k) { const F = FUSC, d = [], out = [], W = 10;      /* extremum vrai : le plus petit (ou grand) sur ±0,2 Ga, et d'au moins 2 kpc ; écarte le bruit du calcul */
  for (let i = 0; i < F.n; i++) { const a = i * 12 + k * 3; d.push(Math.hypot(F.c[a], F.c[a + 1], F.c[a + 2])); }
  for (let i = 1; i < F.n - 1; i++) { const w = d.slice(Math.max(0, i - W), Math.min(F.n, i + W + 1)), lo = Math.min(...w), hi = Math.max(...w);
    if (d[i] === lo && hi - lo > 2 && (!out.length || out[out.length - 1][2] !== 'min')) out.push([F.t[i], d[i], 'min']);
    else if (d[i] === hi && hi - lo > 2 && out.length && out[out.length - 1][2] !== 'max') out.push([F.t[i], d[i], 'max']); }
  return out; }

/* R10 : les étoiles du calcul complet (30 000 étoiles affichées : 12 000 de la Voie lactée, 15 000 d'Andromède, 2 000 du
   Triangle, 1 000 du Grand Nuage), une image toutes les 20 Ma, relatives au centre de la Voie lactée, en paquets de 25 images
   (pipeline/fusion/exporter_images.py), chargés à la demande. Entre deux images, chaque étoile va en ligne droite :
   pour les étoiles du centre (un tour en 50 à 100 Ma), c'est une corde de leur orbite. */
let FUSI = null;
function fusImagesInit(meta) { FUSI = { meta, packs: [], n: meta.t.length, dt: meta.t[1] - meta.t[0], NS: meta.etoiles, Q: meta.quantum_kpc, cnt: meta.par_galaxie, per: meta.paquets[0].images }; return FUSI; }
const fusPackOf = k => Math.floor(k / FUSI.per);
function fusFrame(k) { const P = FUSI.packs[fusPackOf(k)]; if (!P || !P.data) return null; const o = (k - P.first) * FUSI.NS * 3; return P.data.subarray(o, o + FUSI.NS * 3); }
/** Demande les paquets des images k et k + 1 (et le suivant, à l'avance) ; libère les paquets éloignés. fetcher(paquet) → Promise du texte base64. */
function fusWant(t, fetcher) {
  const k = clamp(Math.floor(t / FUSI.dt), 0, FUSI.n - 1), want = new Set([fusPackOf(k), fusPackOf(Math.min(k + 1, FUSI.n - 1)), fusPackOf(Math.min(k + FUSI.per, FUSI.n - 1))]);
  FUSI.packs.forEach((P, p) => { if (P && !want.has(p) && Math.abs(p - fusPackOf(k)) > 1) FUSI.packs[p] = null; });
  for (const p of want) if (!FUSI.packs[p]) { const pk = FUSI.meta.paquets[p], P = FUSI.packs[p] = { first: pk.premiere, data: null };
    fetcher(pk).then(txt => { const b = b64ToBytes(txt.trim()); P.data = new Int16Array(b.buffer, b.byteOffset, b.length / 2); }).catch(e => { console.warn('Image du calcul de la fusion non chargée :', e.message); if (FUSI.packs[p] === P) FUSI.packs[p] = null; }); }
}
/** Positions (kpc, centrées sur la Voie lactée) à la date t, interpolées entre deux images ; false si elles ne sont pas encore chargées. */
function fusFill(out, t, off) {
  const x = clamp(t / FUSI.dt, 0, FUSI.n - 1.0001), k = x | 0, f = x - k, a = fusFrame(k), b = fusFrame(k + 1), q = FUSI.Q, o = (off || 0) * 3; if (!a || !b) return false;
  for (let j = 0; j < a.length; j++) out[o + j] = (a[j] + (b[j] - a[j]) * f) * q;
  return true;
}
/** Après la dernière image (10 Ga) : chaque étoile continue dans la galaxie résultante, immobile et sphérique (les deux
    halos de la page confondus, cœur de 0,3 kpc à densité constante). Pas propre à chaque étoile (2 % de son temps de
    traversée, sans descendre sous 0,5 Ma) ; le cœur à densité constante évite le coup de fouet d'un centre ponctuel, qui faisait gonfler la galaxie.
    Avance par tranches de 5 Ma tant que ms millisecondes ne sont pas écoulées ; renvoie true quand tTarget est atteint. */
function tailAdvance(D, tTarget, ms, T) {
  const t0p = performance.now(), ta = T.a, tb = T.b, nt = T.n - 2, x = D.x, v = D.v, ga = r => { const rr = Math.max(r, 0.3) * 10, q = Math.min(rr | 0, nt), f = Math.min(rr, nt) - q; return (ta[q] + (ta[q + 1] - ta[q]) * f) + (tb[q] + (tb[q + 1] - tb[q]) * f); };
  while (Math.abs(tTarget - D.t) > 1e-9 && performance.now() - t0p < ms) {
    const H = clamp(tTarget - D.t, -0.005, 0.005);      /* tranches de 5 Ma : l'heure est vérifiée souvent, l'image ne gèle pas */
    for (let j = 0; j < D.n * 3; j += 3) {
      let left = H;
      while (Math.abs(left) > 1e-12) {
        const r = Math.max(Math.hypot(x[j], x[j + 1], x[j + 2]), 0.3), vc = Math.sqrt(ga(r)) * r, h = Math.sign(left) * Math.min(Math.abs(left), Math.max(0.02 * r / Math.max(vc, 1), 0.0005));      /* au plus fin 0,5 Ma : le cœur à densité constante reste stable à ce pas */
        let g = ga(Math.hypot(x[j], x[j + 1], x[j + 2])); v[j] -= g * x[j] * h / 2; v[j + 1] -= g * x[j + 1] * h / 2; v[j + 2] -= g * x[j + 2] * h / 2;
        x[j] += v[j] * h; x[j + 1] += v[j + 1] * h; x[j + 2] += v[j + 2] * h;
        g = ga(Math.hypot(x[j], x[j + 1], x[j + 2])); v[j] -= g * x[j] * h / 2; v[j + 1] -= g * x[j + 1] * h / 2; v[j + 2] -= g * x[j + 2] * h / 2;
        left -= h;
      }
    }
    D.t += H;
  }
  for (let j = 0; j < D.n * 3; j++) D.out[j] = x[j];
  return Math.abs(tTarget - D.t) <= 1e-9;
}
/** Part des images nécessaires à la date t déjà chargées (0 à 1). */
function fusReady(t) { const k = clamp(Math.floor(t / FUSI.dt), 0, FUSI.n - 2); return (fusFrame(k) ? 0.5 : 0) + (fusFrame(k + 1) ? 0.5 : 0); }

function andromedaOrbit(C, vtKms, Vin, fus) {
  const P = DATA.M31.pos, V = Vin || DATA.M31.vel, r0 = Math.hypot(P[0], P[1], P[2]), u = [P[0] / r0, P[1] / r0, P[2] / r0], vr = V[0] * u[0] + V[1] * u[1] + V[2] * u[2];
  const vt = [V[0] - vr * u[0], V[1] - vr * u[1], V[2] - vr * u[2]], vt0 = Math.hypot(vt[0], vt[1], vt[2]), sc = vtKms === undefined ? 1 : vtKms / vt0;
  const h2 = C.h * C.h, w = C.par.w, OL = C.par.OL, tmp = {};
  const acc = (r, v, t, friction, o) => {
    const d = Math.max(Math.hypot(r[0], r[1], r[2]), 1e-3), m1 = mwMass(d), m2 = M31_MASS_RATIO * mwMass(d / 1.15);
    let g = -G_KPC * (m1 + m2) / (d * d * d) * 1.0459, de = 0;
    if (OL > 0) { const a = cosmoAt(C, clamp(t, C.tStart, C.tEnd), tmp).a; de = -0.5 * h2 * OL * (1 + 3 * w) * Math.pow(a, -3 * (1 + w)); }
    o[0] = (g + de) * r[0]; o[1] = (g + de) * r[1]; o[2] = (g + de) * r[2];
    if (friction && d < 2 * HALO_EDGE) {
      const dr = d * 0.02, rho = M31_MASS_RATIO * (mwMass((d + dr) / 1.15) - mwMass((d - dr) / 1.15)) / (2 * dr) / (4 * Math.PI * d * d);      // densité du halo le plus massif à cette distance
      const vk = Math.max(Math.hypot(v[0], v[1], v[2]) / KMS_KPC_GYR, 1), vc = Math.sqrt(G_KPC * m2 / d), X = vk / vc, F = erf(X) - 2 * X / Math.sqrt(Math.PI) * Math.exp(-X * X);
      const k = -4 * Math.PI * G_KPC * G_KPC * mwMass(Math.min(d, 60)) * rho * 2.5 * F / (vk * vk * vk) * 1.0459 / KMS_KPC_GYR;
      o[0] += k * v[0]; o[1] += k * v[1]; o[2] += k * v[2]; o[3] = k * v[0]; o[4] = k * v[1]; o[5] = k * v[2];
    } else { o[3] = 0; o[4] = 0; o[5] = 0; }
    return o;
  };
  const DT = 0.002, T0 = -2, T1 = 14, n = Math.round((T1 - T0) / 0.01) + 1, tab = new Float32Array(n * 3), tabF = new Float32Array(n * 3), res = { t0: T0, dt: 0.01, n, r: tab, f: tabF, peri: [], tMerge: null, vt: vt0 * sc, vr };
  const run = (dir) => {
    let r = [P[0], P[1], P[2]], v = [(vr * u[0] + vt[0] * sc) * KMS_KPC_GYR, (vr * u[1] + vt[1] * sc) * KMS_KPC_GYR, (vr * u[2] + vt[2] * sc) * KMS_KPC_GYR], t = 0, merged = false, dPrev = r0, dPrev2 = r0;
    const k1 = [0, 0, 0, 0, 0, 0], k2 = [0, 0, 0, 0, 0, 0], k3 = [0, 0, 0, 0, 0, 0], k4 = [0, 0, 0, 0, 0, 0], h = DT * dir, steps = Math.round((dir > 0 ? T1 : -T0) / DT);
    for (let s = 0; s <= steps; s++) {
      if (s % 5 === 0) { const idx = Math.round((t - T0) / 0.01); if (idx >= 0 && idx < n) tab.set(merged ? [0, 0, 0] : r, idx * 3); }
      if (merged) { t += h; continue; }
      const fr = dir > 0;
      acc(r, v, t, fr, k1); if (s % 5 === 0) { const idx = Math.round((t - T0) / 0.01); if (idx >= 0 && idx < n) tabF.set([k1[3], k1[4], k1[5]], idx * 3); }
      const r2 = [r[0] + 0.5 * h * v[0], r[1] + 0.5 * h * v[1], r[2] + 0.5 * h * v[2]], v2 = [v[0] + 0.5 * h * k1[0], v[1] + 0.5 * h * k1[1], v[2] + 0.5 * h * k1[2]]; acc(r2, v2, t + 0.5 * h, fr, k2);
      const r3 = [r[0] + 0.5 * h * v2[0], r[1] + 0.5 * h * v2[1], r[2] + 0.5 * h * v2[2]], v3 = [v[0] + 0.5 * h * k2[0], v[1] + 0.5 * h * k2[1], v[2] + 0.5 * h * k2[2]]; acc(r3, v3, t + 0.5 * h, fr, k3);
      const r4 = [r[0] + h * v3[0], r[1] + h * v3[1], r[2] + h * v3[2]], v4 = [v[0] + h * k3[0], v[1] + h * k3[1], v[2] + h * k3[2]]; acc(r4, v4, t + h, fr, k4);
      for (let i = 0; i < 3; i++) { r[i] += h / 6 * (v[i] + 2 * v2[i] + 2 * v3[i] + v4[i]); v[i] += h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]); }
      t += h; const d = Math.hypot(r[0], r[1], r[2]);
      if (dir > 0) { if (dPrev < dPrev2 && dPrev <= d && res.peri.length < 12) res.peri.push([t - h, dPrev]); if (dPrev > dPrev2 && dPrev >= d && dPrev < 10 && res.peri.length) { merged = true; res.tMerge = t; } }
      dPrev2 = dPrev; dPrev = d;
    }
  };
  run(1); run(-1);
  if (fus && FUSC && Math.abs(vt0 * sc - vt0) < 0.5) {      /* R10 : de 0 à la fusion, l'orbite vient du calcul complet ; avant aujourd'hui, du calcul de la page (même départ) ; après la fusion, centres confondus */
    const p = [0, 0, 0], o = [0, 0, 0, 0, 0, 0], H = 0.1, aF = t => { const a = [0, 0, 0], b = [0, 0, 0], c = [0, 0, 0]; fusAt(FUSC.c, 4, 1, t - H, a); fusAt(FUSC.c, 4, 1, t, b); fusAt(FUSC.c, 4, 1, t + H, c); return [0, 1, 2].map(i => (a[i] - 2 * b[i] + c[i]) / (H * H)); };
    for (let idx = 0; idx < n; idx++) { const t = T0 + idx * 0.01; if (t < 0) continue;
      if (t >= FUSC.ga) { tab.set([0, 0, 0], idx * 3); tabF.set([0, 0, 0], idx * 3); continue; }
      fusAt(FUSC.c, 4, 1, t, p); tab.set(p, idx * 3);
      /* tabF : ce que le calcul complet ajoute à l'attraction du modèle (frottement, Grand Nuage, Triangle), accélération lissée sur ±0,1 Ga, pour que les étoiles d'Andromède suivent son centre */
      const af = t > H && t < FUSC.ga - H ? aF(t) : null; acc(p, [0, 0, 0], t, false, o);
      tabF.set(af ? [af[0] - o[0], af[1] - o[1], af[2] - o[2]] : [0, 0, 0], idx * 3); }
    res.peri = fusExtrema(1).filter(e => e[2] === 'min' && e[0] < FUSC.ga).map(e => [e[0], e[1]]); res.tMerge = FUSC.ga; res.fus = true;
  }
  return res;
}
function erf(x) { const s = x < 0 ? -1 : 1, a = Math.abs(x), t = 1 / (1 + 0.3275911 * a); return s * (1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-a * a)); }
function andromedaAt(O, t, out, fric) { const x = clamp((t - O.t0) / O.dt, 0, O.n - 1.001), i = x | 0, f = x - i, r = fric ? O.f : O.r; out[0] = lerp(r[i * 3], r[i * 3 + 3], f); out[1] = lerp(r[i * 3 + 1], r[i * 3 + 4], f); out[2] = lerp(r[i * 3 + 2], r[i * 3 + 5], f); return out; }

/* --------------------------------------------------------------------------
   Rencontre rapprochée : N-corps restreint, à la manière de Toomre (1972). Chaque
   étoile-test subit l'attraction des deux galaxies (masse contenue dans son rayon)
   pendant que leurs centres suivent la trajectoire calculée plus haut. Les étoiles ne
   s'attirent pas entre elles : c'est ce qui permet le calcul en direct, et cela suffit
   à faire naître ponts et queues de marée. Repère : centre de la Voie lactée, axes
   galactiques. Unités : kpc et Ga. Intégration saute-mouton, pas de 2 millions d'années.
   -------------------------------------------------------------------------- */
const DYN_DT = 0.002;
function dynTables() {      // G·M(<r)/r³ pour chaque galaxie, tous les 0,1 kpc
  const n = 6002, a = new Float64Array(n), b = new Float64Array(n);
  for (let i = 0; i < n; i++) { const r = Math.max(i * 0.1, 0.15); a[i] = G_KPC * mwMass(r) / (r * r * r) * 1.0459; b[i] = G_KPC * M31_MASS_RATIO * mwMass(r / 1.15) / (r * r * r) * 1.0459; }
  return { a, b, n };
}
function dynInit(gal, nStars, m31, O, tOn, sunPos, A, nMW, n31, lumRef) {
  const a = Math.min(nMW, nStars), glow = 0, b = Math.min(n31, m31.N - 70), n = a + glow + b;
  const D = { n, nMW: a + glow, t: tOn, t0: tOn, x: new Float64Array(n * 3), v: new Float64Array(n * 3), out: new Float32Array(n * 3), col: new Float32Array(n * 3), look: new Float32Array(n * 2), boost: clamp(Math.sqrt(nStars / a), 1, 2.4) };
  // Pour chaque étoile, une copie « témoin » suit la même orbite sans l'autre galaxie. L'écart entre l'étoile et son témoin est l'effet de la rencontre ;
  // à l'affichage, cet écart est ajouté à la place que l'étoile aurait dans le modèle au repos (bras tournant d'un bloc), ce qui évite l'enroulement des bras.
  D.p0 = new Float32Array(n * 3); D.om = new Float32Array(n); D.kind = new Uint8Array(n); D.rx = new Float64Array(n * 3); D.rv = new Float64Array(n * 3); D.r0 = new Float32Array(n); D.A = A;
  const c = [0, 0, 0], c1 = [0, 0, 0], c2 = [0, 0, 0]; andromedaAt(O, tOn, c); andromedaAt(O, tOn - 0.005, c1); andromedaAt(O, tOn + 0.005, c2);
  const cv = [(c2[0] - c1[0]) / 0.01, (c2[1] - c1[1]) / 0.01, (c2[2] - c1[2]) / 0.01];
  let k = 0;
  const putMW = i => {
    const om = gal.om[i * 2], ang = -om * tOn, ca = Math.cos(ang), sa = Math.sin(ang), x0 = gal.pos[i * 3], y0 = gal.pos[i * 3 + 1], z = gal.pos[i * 3 + 2], x = ca * x0 - sa * y0, y = sa * x0 + ca * y0;
    const sp = vCirc(Math.max(Math.hypot(x, y, z), 0.3), true) * KMS_KPC_GYR, R = Math.max(Math.hypot(x, y), 1e-3); let vx, vy, vz = 0;
    if (om !== 0) { vx = sp * y / R; vy = -sp * x / R; }                    // rotation dans le sens des aiguilles d'une montre, vue du nord galactique
    else { const h = hash01(i * 3 + 1) * TAU, w = vnorm(vcross([x, y, z], [Math.cos(h), Math.sin(h), 2 * hash01(i * 7 + 2) - 1])); vx = w[0] * sp; vy = w[1] * sp; vz = w[2] * sp; }   // halo : orbites en tous sens
    D.x.set([x, y, z], k * 3); D.v.set([vx, vy, vz], k * 3); D.col.set(gal.col.subarray(i * 3, i * 3 + 3), k * 3); D.look.set(gal.look.subarray(i * 2, i * 2 + 2), k * 2);
    D.p0.set([x0, y0, z], k * 3); D.om[k] = om; D.kind[k] = om !== 0 ? 0 : 2; D.rx.set([x, y, z], k * 3); D.rv.set([vx, vy, vz], k * 3); D.r0[k] = Math.hypot(x, y, z); k++;
  };
  for (let i = 0; i < a; i++) putMW(i);
  for (let i = 0; i < glow; i++) putMW(nStars + i);
  { const R = Math.max(Math.hypot(sunPos[0], sunPos[1]), 1e-3), sp = vCirc(Math.hypot(sunPos[0], sunPos[1], sunPos[2]), true) * KMS_KPC_GYR;      // la particule 0 est le Soleil
    D.x.set(sunPos, 0); D.v.set([sp * sunPos[1] / R, -sp * sunPos[0] / R, 0], 0); D.look[1] = 0; D.kind[0] = 2; }
  for (let j = 0; j < b; j++) {
    const i = j, om = m31.om[i * 2], ang = -om * tOn, ca = Math.cos(ang), sa = Math.sin(ang), x0 = m31.pos[i * 3], y0 = m31.pos[i * 3 + 1], z = m31.pos[i * 3 + 2], x = ca * x0 - sa * y0, y = sa * x0 + ca * y0;
    const r3 = Math.max(Math.hypot(x, y, z), 0.3), sp = Math.sqrt(G_KPC * M31_MASS_RATIO * mwMass(r3 / 1.15) / r3) * KMS_KPC_GYR, R = Math.max(Math.hypot(x, y), 1e-3), vl = [sp * y / R, -sp * x / R, 0];
    D.x.set([A[0][0] * x + A[0][1] * y + A[0][2] * z + c[0], A[1][0] * x + A[1][1] * y + A[1][2] * z + c[1], A[2][0] * x + A[2][1] * y + A[2][2] * z + c[2]], k * 3);
    D.v.set([A[0][0] * vl[0] + A[0][1] * vl[1] + cv[0], A[1][0] * vl[0] + A[1][1] * vl[1] + cv[1], A[2][0] * vl[0] + A[2][1] * vl[1] + cv[2]], k * 3);
    D.col.set(m31.col.subarray(i * 3, i * 3 + 3), k * 3); D.look[k * 2] = m31.look[i * 2]; D.look[k * 2 + 1] = m31.look[i * 2 + 1] * Math.min(1, (lumRef || b) / b);
    D.p0.set([x0, y0, z], k * 3); D.om[k] = om; D.kind[k] = om !== 0 ? 1 : 2; D.r0[k] = r3;
    D.rx.set([A[0][0] * x + A[0][1] * y + A[0][2] * z, A[1][0] * x + A[1][1] * y + A[1][2] * z, A[2][0] * x + A[2][1] * y + A[2][2] * z], k * 3); D.rv.set([A[0][0] * vl[0] + A[0][1] * vl[1], A[1][0] * vl[0] + A[1][1] * vl[1], A[2][0] * vl[0] + A[2][1] * vl[1]], k * 3); k++;
  }
  for (let j = 0; j < n * 3; j++) D.out[j] = D.x[j];
  return D;
}
function dynAdvance(D, O, tTarget, maxSteps, T) {
  const x = D.x, v = D.v, n = D.n, ta = T.a, tb = T.b, nt = T.n - 2, c = [0, 0, 0], fr = [0, 0, 0], j31 = D.nMW * 3, kind = D.kind, rx = D.rx, rv = D.rv; let steps = 0;
  while (steps < maxSteps && Math.abs(tTarget - D.t) > 1e-9) {
    const h = clamp(tTarget - D.t, -DYN_DT, DYN_DT), hh = 0.5 * h; andromedaAt(O, D.t + hh, c); andromedaAt(O, D.t + hh, fr, true);
    const cx = c[0], cy = c[1], cz = c[2], d = Math.hypot(cx, cy, cz), di = Math.min(d * 10, nt), i0 = di | 0, gi = d > 1e-6 ? tb[i0] + (tb[i0 + 1] - tb[i0]) * (di - i0) : 0;
    const ix = -gi * cx, iy = -gi * cy, iz = -gi * cz;          // la Voie lactée tombe elle aussi vers Andromède : on retranche son accélération
    for (let j = 0; j < n * 3; j += 3) {
      const px = x[j] + v[j] * hh, py = x[j + 1] + v[j + 1] * hh, pz = x[j + 2] + v[j + 2] * hh;
      let r = Math.sqrt(px * px + py * py + pz * pz) * 10; if (r > nt) r = nt; let q = r | 0; const g1 = ta[q] + (ta[q + 1] - ta[q]) * (r - q);
      const dx = px - cx, dy = py - cy, dz = pz - cz; r = Math.sqrt(dx * dx + dy * dy + dz * dz) * 10; if (r > nt) r = nt; q = r | 0; const g2 = tb[q] + (tb[q + 1] - tb[q]) * (r - q);
      let ax = ix - g1 * px - g2 * dx, ay = iy - g1 * py - g2 * dy, az = iz - g1 * pz - g2 * dz;
      if (j >= j31) { const w = Math.exp(-(dx * dx + dy * dy + dz * dz) / 5000); ax += w * fr[0]; ay += w * fr[1]; az += w * fr[2]; }      // étoiles encore liées à Andromède : freinées avec elle
      const vx = v[j] + ax * h, vy = v[j + 1] + ay * h, vz = v[j + 2] + az * h;
      v[j] = vx; v[j + 1] = vy; v[j + 2] = vz; x[j] = px + vx * hh; x[j + 1] = py + vy * hh; x[j + 2] = pz + vz * hh;
      const kd = kind[j / 3]; if (kd < 2) { const qx = rx[j] + rv[j] * hh, qy = rx[j + 1] + rv[j + 1] * hh, qz = rx[j + 2] + rv[j + 2] * hh; let rr = Math.sqrt(qx * qx + qy * qy + qz * qz) * 10; if (rr > nt) rr = nt; const q2 = rr | 0, tt = kd ? tb : ta, gg = tt[q2] + (tt[q2 + 1] - tt[q2]) * (rr - q2);      /* témoin : même pas de calcul, attraction de sa seule galaxie */
        const ux = rv[j] - gg * qx * h, uy = rv[j + 1] - gg * qy * h, uz = rv[j + 2] - gg * qz * h; rv[j] = ux; rv[j + 1] = uy; rv[j + 2] = uz; rx[j] = qx + ux * hh; rx[j + 1] = qy + uy * hh; rx[j + 2] = qz + uz * hh; }
    }
    D.t += h; steps++;
  }
  if (steps) { const o = D.out, p0 = D.p0, A = D.A; andromedaAt(O, D.t, c);
    for (let i = 0, j = 0; i < n; i++, j += 3) { const kd = kind[i]; if (kd === 2) { o[j] = x[j]; o[j + 1] = x[j + 1]; o[j + 2] = x[j + 2]; continue; }
      const ang = -D.om[i] * D.t, ca = Math.cos(ang), sa = Math.sin(ang), lx = ca * p0[j] - sa * p0[j + 1], ly = sa * p0[j] + ca * p0[j + 1], lz = p0[j + 2]; let sx = lx, sy = ly, sz = lz, dx = x[j] - rx[j], dy = x[j + 1] - rx[j + 1], dz = x[j + 2] - rx[j + 2];
      if (kd === 1) { sx = A[0][0] * lx + A[0][1] * ly + A[0][2] * lz; sy = A[1][0] * lx + A[1][1] * ly + A[1][2] * lz; sz = A[2][0] * lx + A[2][1] * ly + A[2][2] * lz; dx -= c[0]; dy -= c[1]; dz -= c[2]; }
      const w = 1 - smoothstep(0.25, 0.6, Math.sqrt(dx * dx + dy * dy + dz * dz) / Math.max(D.r0[i], 2));      // étoile peu dérangée : elle reste sur le motif de sa galaxie ; étoile arrachée : sa position calculée, telle quelle
      o[j] = x[j] + w * (sx - rx[j]); o[j + 1] = x[j + 1] + w * (sy - rx[j + 1]); o[j + 2] = x[j + 2] + w * (sz - rx[j + 2]); } }
  return steps;
}

/* --------------------------------------------------------------------------
   Grand Nuage de Magellan : orbite autour de la Voie lactée à partir de sa position et
   de sa vitesse mesurées (Kallivayalil et al. 2013). Même méthode que pour Andromède :
   masse contenue dans la distance, frottement dynamique dans le halo, et le Nuage perd
   ce qui dépasse son rayon de marée. Masse du Nuage : 1,8 × 10¹¹ masses solaires,
   au milieu des estimations publiées ; le résultat y est très sensible. Le Petit Nuage est supposé l'accompagner.
   -------------------------------------------------------------------------- */
const LMC_MASS = 1.8e11, LMC_A = 12;      // les estimations publiées vont de 1,3 à 2,5 × 10¹¹ masses solaires
const lmcMass = r => LMC_MASS * r * r / ((r + LMC_A) * (r + LMC_A));
function lmcOrbit(massScale, fus) {
  const T0 = -1, T1 = 10, DT = 0.005, H = 0.0005, n = Math.round((T1 - T0) / DT) + 1, tab = new Float32Array(n * 3), res = { t0: T0, dt: DT, n, r: tab, peri: [], apo: [], tMerge: null }, ms0 = massScale || 1;
  const acc = (r, v, fr, o) => {
    const d = Math.max(Math.hypot(r[0], r[1], r[2]), 0.5), Mh = mwMass(d), g = -G_KPC * (Mh + ms0 * lmcMass(d)) / (d * d * d) * 1.0459; o[0] = g * r[0]; o[1] = g * r[1]; o[2] = g * r[2];
    if (fr) { const vs = Math.hypot(v[0], v[1], v[2]), vv = vs / KMS_KPC_GYR, dr = 0.05 * d, rho = Math.max(mwMass(d + dr) - mwMass(d - dr), 0) / (4 * Math.PI * d * d * 2 * dr);
      const rt = d * Math.cbrt(ms0 * lmcMass(d) / (3 * Mh)), ms = ms0 * lmcMass(Math.min(rt, d)), X = vv / Math.sqrt(G_KPC * Mh / d);
      const k = -4 * Math.PI * G_KPC * G_KPC * ms * rho * 2.5 * (erf(X) - 2 * X / Math.sqrt(Math.PI) * Math.exp(-X * X)) / (vv * vv) * 1.0459 / Math.max(vs, 1e-6);
      o[0] += k * v[0]; o[1] += k * v[1]; o[2] += k * v[2]; }
    return o; };
  for (const dir of [1, -1]) {
    const r = DATA.LMC.pos.slice(), v = DATA.LMC.vel.map(x => x * KMS_KPC_GYR), h = H * dir, a = [0, 0, 0], steps = Math.round((dir > 0 ? T1 : -T0) / H); let t = 0, merged = false, dP = Math.hypot(r[0], r[1], r[2]), dPP = dP;
    for (let s = 0; s <= steps; s++) {
      if (s % 10 === 0) { const idx = Math.round((t - T0) / DT); if (idx >= 0 && idx < n) tab.set(merged ? [0, 0, 0] : r, idx * 3); }
      if (!merged) {
        acc(r, v, dir > 0, a); v[0] += a[0] * h / 2; v[1] += a[1] * h / 2; v[2] += a[2] * h / 2; r[0] += v[0] * h; r[1] += v[1] * h; r[2] += v[2] * h; acc(r, v, dir > 0, a); v[0] += a[0] * h / 2; v[1] += a[1] * h / 2; v[2] += a[2] * h / 2;
        const d = Math.hypot(r[0], r[1], r[2]);
        if (dir > 0) { if (dP < dPP && dP <= d && res.peri.length < 12) res.peri.push([t, dP]); if (dP > dPP && dP >= d) { if (res.apo.length < 12) res.apo.push([t, dP]); if (res.peri.length && dP < 15) { merged = true; res.tMerge = t; } } if (d < 2.5) { merged = true; res.tMerge = t; } }
        dPP = dP; dP = d;
      }
      t += h;
    }
  }
  if (fus && FUSC) {      /* R10 : de 0 à 10 Ga, le Grand Nuage du calcul complet (il y a sa masse, et la Voie lactée recule sous son attraction) */
    const ex = fusExtrema(3); res.peri = []; res.apo = []; res.tMerge = null;
    for (const e of ex) { if (e[2] === 'min') res.peri.push([e[0], e[1]]); else { res.apo.push([e[0], e[1]]); if (res.peri.length && e[1] < 15 && res.tMerge === null) res.tMerge = e[0]; } }
    if (res.tMerge === null) { const m = ex.find(e => e[2] === 'min' && e[1] < 5); if (m) res.tMerge = m[0]; }
    const p = [0, 0, 0];
    for (let idx = 0; idx < n; idx++) { const t = T0 + idx * DT; if (t < 0) continue; if (t > FUSC.tEnd) { tab.set([0, 0, 0], idx * 3); continue; }      /* après l'absorption, il reste où le calcul le met (pas de saut au centre) */ fusAt(FUSC.c, 4, 3, t, p); tab.set(p, idx * 3); }
    res.fus = true;
  }
  return res;
}

/* --------------------------------------------------------------------------
   Nuage d'Oort : chaque comète suit une orbite de Kepler autour du Soleil.
   Quand une étoile passe, elle donne un coup de vitesse à chaque comète
   (approximation impulsionnelle, la méthode classique pour ce problème) :
   la comète reçoit 2GM/(V b) vers la route de l'étoile, le Soleil reçoit le sien,
   et c'est la différence qui change l'orbite de la comète autour du Soleil.
   Unités : UA, années, masses solaires.
   -------------------------------------------------------------------------- */
const MU_SUN = 4 * Math.PI * Math.PI;
/** Orbite (ellipse ou hyperbole) passant par la position r avec la vitesse v à l'instant tA. */
function orbFromState(r, v, tA, mu) {
  const rr = Math.hypot(r[0], r[1], r[2]), v2 = v[0] * v[0] + v[1] * v[1] + v[2] * v[2], rv = r[0] * v[0] + r[1] * v[1] + r[2] * v[2];
  const hx = r[1] * v[2] - r[2] * v[1], hy = r[2] * v[0] - r[0] * v[2], hz = r[0] * v[1] - r[1] * v[0], hh = Math.hypot(hx, hy, hz) || 1e-12;
  let ex = (v[1] * hz - v[2] * hy) / mu - r[0] / rr, ey = (v[2] * hx - v[0] * hz) / mu - r[1] / rr, ez = (v[0] * hy - v[1] * hx) / mu - r[2] / rr, e = Math.hypot(ex, ey, ez);
  if (e < 1e-8) { ex = r[0] / rr; ey = r[1] / rr; ez = r[2] / rr; e = 1e-8; } else { ex /= e; ey /= e; ez /= e; }
  const qx = (hy * ez - hz * ey) / hh, qy = (hz * ex - hx * ez) / hh, qz = (hx * ey - hy * ex) / hh;
  let inva = 2 / rr - v2 / mu; if (Math.abs(inva) < 1e-12) inva = -1e-12;
  const a = 1 / inva, hyp = a < 0, A = Math.abs(a), B = A * Math.sqrt(Math.abs(1 - e * e)), sma = Math.sqrt(mu * A), n = Math.sqrt(mu / (A * A * A)); let M0;
  if (!hyp) { const E = Math.atan2(rv / (e * sma), (1 - rr / a) / e); M0 = E - e * Math.sin(E); } else { const H = Math.asinh(rv / (e * sma)); M0 = e * Math.sinh(H) - H; }
  return { hyp, e, n, M0, tA, A, sma, q: A * Math.abs(1 - e), P: [ex * A, ey * A, ez * A], Q: [qx * B, qy * B, qz * B] };
}
function orbAnom(o, t) { let M = o.M0 + o.n * (t - o.tA); if (!o.hyp) return keplerE(wrapPi(M), o.e);
  M = clamp(M, -500, 500); let H = Math.asinh(M / o.e); for (let i = 0; i < 40; i++) { const d = (o.e * Math.sinh(H) - H - M) / (o.e * Math.cosh(H) - 1); H -= d; if (Math.abs(d) < 1e-11) break; } return H; }
/** Position à l'instant t, écrite dans out[k..k+2]. */
function orbPos(o, t, out, k) { const E = orbAnom(o, t), x = o.hyp ? o.e - Math.cosh(E) : Math.cos(E) - o.e, y = o.hyp ? Math.sinh(E) : Math.sin(E);
  out[k] = o.P[0] * x + o.Q[0] * y; out[k + 1] = o.P[1] * x + o.Q[1] * y; out[k + 2] = o.P[2] * x + o.Q[2] * y; }
/** Position (out[0..2]) et vitesse (out[3..5]) à l'instant t. */
function orbState(o, t, out) { const E = orbAnom(o, t), c = o.hyp ? Math.cosh(E) : Math.cos(E), s = o.hyp ? Math.sinh(E) : Math.sin(E), x = o.hyp ? o.e - c : c - o.e, rr = o.A * Math.abs(1 - o.e * c) || 1e-9, k = o.sma / (rr * o.A);
  for (let j = 0; j < 3; j++) { out[j] = o.P[j] * x + o.Q[j] * s; out[3 + j] = k * (-s * o.P[j] + c * o.Q[j]); } return out; }
/** Coup de vitesse reçu par une comète en rc quand l'étoile `en` passe. Renvoie le décalage (années) entre le passage de l'étoile au plus près du Soleil et au plus près de la comète.
    en : { bS : point de sa route le plus proche du Soleil (UA), u : direction de sa vitesse, V : vitesse (UA/an), M : masse (masses solaires) }. */
function starKick(rc, en, out) { const dx = rc[0] - en.bS[0], dy = rc[1] - en.bS[1], dz = rc[2] - en.bS[2], al = dx * en.u[0] + dy * en.u[1] + dz * en.u[2];
  const bx = en.u[0] * al - dx, by = en.u[1] * al - dy, bz = en.u[2] * al - dz, e2 = 150 * 150, b2 = bx * bx + by * by + bz * bz + e2, s2 = en.bS[0] * en.bS[0] + en.bS[1] * en.bS[1] + en.bS[2] * en.bS[2] + e2, k = 2 * MU_SUN * en.M / en.V;
  out[0] = k * (bx / b2 - en.bS[0] / s2); out[1] = k * (by / b2 - en.bS[1] / s2); out[2] = k * (bz / b2 - en.bS[2] / s2); return al / en.V; }
