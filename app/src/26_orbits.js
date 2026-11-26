/* --------------------------------------------------------------------------
   S2 — Orbites calculées pas à pas des étoiles du catalogue principal (HYG, environ 59 000 étoiles).
   Chaque étoile, et le Soleil, est intégrée pas à pas dans le MODÈLE de la Voie lactée
   de 20_physics.js (inspiré de MWPotential2014, Bovy 2015, recalé), plus la barre centrale tournante (voir orbParams ; sans bras) (bulbe de Hernquist + disque de Miyamoto-Nagai + halo NFW, objet GAL),
   par la méthode du saut de grenouille (vitesse de Verlet), pas de 1 Ma, dans un Web Worker.
   Tant que le résultat pour l'instant affiché n'est pas prêt, on garde l'approximation des
   épicycles (25_future.js), comme avant. Les étoiles Gaia en flux (millions) restent en épicycles.
   Unités : position en kpc, vitesse en km/s, temps en milliards d'années (Ga).
   -------------------------------------------------------------------------- */
const ORB_DT = 0.001;            /* pas d'intégration : 1 Ma */
const ORB_CP = 0.1;              /* point de contrôle tous les 100 Ma */
const ORB_MAXCP = 24;            /* points de contrôle gardés au plus (Float32 : environ 34 Mo pour 59 000 étoiles) */
const ORB_EXTRA = 0.006;         /* au-delà de 6 Ma d'écart avec le dernier résultat calculé, on revient aux épicycles */
const ORB_KV = 1.0227121650456;  /* km/s -> kpc/Ga */

/* Barre centrale de la Voie lactée (lot G) : potentiel tournant de Dehnen (2000, AJ 119, 800), quadrupolaire :
   Φ_b = A cos 2(φ − φ_b(t)) U(R), U = (R/R_b)³ − 2 sous R_b, −(R_b/R)³ au-delà ; A = α v0² (R0/R_b)³ / 3.
   Mesuré : vitesse de rotation de la barre 39 ± 3,5 km/s/kpc (Portail et al. 2017 ; mesures récentes de 33, Clarke et Gerhard 2022, à 41, Sanders et al. 2019) ;
   demi-longueur 5,0 ± 0,2 kpc (Wegg et al. 2015) ;
   angle de la barre, 28° devant la direction du centre, côté proche aux longitudes positives (Wegg et Gerhard 2013).
   Modèle (évolution supposée) : force α = 0,01 (valeur de Dehnen, qui
   reproduit le courant d'étoiles d'Hercule près du Soleil). Sans bras spiraux (leur vitesse de rotation n'est pas établie). */
const BAR_ALPHA = 0.01, BAR_RB = 5.0;      /* longueur : demi-longueur mesurée 5,0 ± 0,2 kpc (Wegg et al. 2015) ; vitesse et angle : GAL.OMEGA_BAR et GAL.BAR_ANGLE, les mêmes que la barre dessinée */
/** Potentiel de la barre seule, (km/s)², pour les contrôles (intégrale de Jacobi). */
function barPhi(P, x, y, t) { const R = Math.hypot(x, y), q = R / P.Rb, U = R < P.Rb ? q * q * q - 2 : -1 / (q * q * q); return P.Ab * Math.cos(2 * (Math.atan2(y, x) - (P.Pb - P.Ob * t))) * U; }
/** Paramètres du potentiel, copiés de GAL pour le Worker (qui ne voit pas le reste de la page). */
let ORB_P_CACHE = null;
const orbParams = () => {
  if (ORB_P_CACHE) return ORB_P_CACHE;
  const v0 = 230, Rb = BAR_RB;
  ORB_P_CACHE = { G: G_KPC, Mb: GAL.Mb, ab: GAL.ab, Md: GAL.Md, ad: GAL.ad, bd: GAL.bd, rs: GAL.rs, GMs: GAL.GMs,
    Rb, Ab: BAR_ALPHA * v0 * v0 * Math.pow(GAL.R0 / Rb, 3) / 3, Ob: GAL.OMEGA_BAR * 1.0227121650456, Pb: Math.PI - GAL.BAR_ANGLE };
  return ORB_P_CACHE;
};

/** Accélération (km/s)²/kpc au point (x, y, z) kpc, écrite dans a[0..2]. */
function orbAcc(P, x, y, z, a, t) {
  const R2 = x * x + y * y, r = Math.sqrt(R2 + z * z) || 1e-9, xs = r / P.rs;
  const ar = -P.G * P.Mb / ((r + P.ab) * (r + P.ab)) - P.GMs * (Math.log(1 + xs) - xs / (1 + xs)) / (r * r);
  const B = Math.sqrt(z * z + P.bd * P.bd), adB = P.ad + B, D2 = R2 + adB * adB, D3 = D2 * Math.sqrt(D2), gm = P.G * P.Md;
  const ir = ar / r, ig = gm / D3;
  a[0] = ir * x - ig * x; a[1] = ir * y - ig * y; a[2] = ir * z - ig * z * adB / B;
  if (P.Ab && t !== undefined && R2 > 1e-8) {      /* barre : identités algébriques double-angle, cos/sin de la barre mis en cache par instant t */
    if (P._t !== t) { const ang2 = 2 * (P.Pb - P.Ob * t); P._t = t; P._cb2 = Math.cos(ang2); P._sb2 = Math.sin(ang2); }
    const R = Math.sqrt(R2), invR = 1 / R, c = x * invR, s = y * invR, c2p = c * c - s * s, s2p = 2 * c * s;
    const c2 = c2p * P._cb2 + s2p * P._sb2, s2 = s2p * P._cb2 - c2p * P._sb2, q = R / P.Rb, q2 = q * q, q3 = q2 * q;
    const U = R < P.Rb ? q3 - 2 : -1 / q3, dU = R < P.Rb ? 3 * q2 / P.Rb : 3 / (q3 * q * P.Rb);
    const aR = -P.Ab * c2 * dU, aP = 2 * P.Ab * s2 * U * invR;
    a[0] += aR * c - aP * s; a[1] += aR * s + aP * c;
  }
}

/** Énergie par unité de masse, (km/s)², pour vérifier la conservation. */
function orbEnergy(P, x, y, z, vx, vy, vz) {
  const r = Math.sqrt(x * x + y * y + z * z) || 1e-9, R2 = x * x + y * y, B = Math.sqrt(z * z + P.bd * P.bd);
  const phi = -P.G * P.Mb / (r + P.ab) - P.G * P.Md / Math.sqrt(R2 + (P.ad + B) * (P.ad + B)) - P.GMs * Math.log(1 + r / P.rs) / r;
  return 0.5 * (vx * vx + vy * vy + vz * vz) + phi;
}

/** Nombre de sous-pas de chaque étoile, fixé une fois pour toutes (un pas constant garde la méthode réversible) :
 *  péricentre estimé (moment cinétique et énergie, potentiel pris dans le plan) sous 0,7 kpc : 32 ; sous 2 kpc : 8 ; sous 4 kpc : 2 ; sinon 1. */
function orbSub(P, X, V, n) {
  const sub = new Uint8Array(n);
  for (let k = 0, j = 0; k < n; k++, j += 3) {
    const x = X[j], y = X[j + 1], z = X[j + 2], vx = V[j], vy = V[j + 1], vz = V[j + 2], E = orbEnergy(P, x, y, z, vx, vy, vz);
    const L2 = (y * vz - z * vy) ** 2 + (z * vx - x * vz) ** 2 + (x * vy - y * vx) ** 2, f = r => 2 * (E - orbEnergy(P, r, 0, 0, 0, 0, 0)) * r * r - L2;
    let lo = 1e-3, hi = Math.max(Math.hypot(x, y, z), 2e-3); if (f(lo) < 0) { for (let it = 0; it < 40; it++) { const m = 0.5 * (lo + hi); if (f(m) < 0) lo = m; else hi = m; } } else hi = lo;
    sub[k] = hi < 0.7 ? 32 : hi < 2 ? 8 : hi < 4 ? 2 : 1;
  }
  return sub;
}

/** Avance toutes les orbites de `steps` pas de durée dt (Ga, négatif pour remonter le temps). sub : sous-pas par étoile (orbSub). */
function orbSteps(P, X, V, n, dt, steps, sub, t0) {
  const a = [0, 0, 0];
  for (let s = 0; s < steps; s++) for (let k = 0, j = 0; k < n; k++, j += 3) {
    const m = sub ? sub[k] : 1, h = dt * 1.0227121650456 / m;
    for (let u = 0; u < m; u++) {
      const ta = t0 === undefined ? undefined : t0 + (s + u / m) * dt, tb = ta === undefined ? undefined : ta + dt / m;      /* heure de chaque coup (la barre tourne) */
      orbAcc(P, X[j], X[j + 1], X[j + 2], a, ta);
      V[j] += 0.5 * h * a[0]; V[j + 1] += 0.5 * h * a[1]; V[j + 2] += 0.5 * h * a[2];
      X[j] += h * V[j]; X[j + 1] += h * V[j + 1]; X[j + 2] += h * V[j + 2];
      orbAcc(P, X[j], X[j + 1], X[j + 2], a, tb);
      V[j] += 0.5 * h * a[0]; V[j + 1] += 0.5 * h * a[1]; V[j + 2] += 0.5 * h * a[2];
    }
  }
}

/* Corps du Worker : reçoit l'état initial, puis des demandes « aller à t ». Part du point de contrôle
   le plus proche (ou de l'état courant), calcule par tranches pour qu'une nouvelle demande remplace
   l'ancienne, et renvoie positions et vitesses à l'instant demandé. */
function orbWorkerMain() {
  let P, n, X, V, SUB, t = 0, goal = null, busy = false;
  const cps = new Map(), CHUNK = 20;
  const key = tt => Math.round(tt / ORB_CP);
  const save = () => { const k = key(t); if (Math.abs(k * ORB_CP - t) < ORB_DT / 2 && !cps.has(k)) { if (cps.size >= ORB_MAXCP) { let far = null; for (const q of cps.keys()) if (q !== 0 && (far === null || Math.abs(q * ORB_CP - t) > Math.abs(far * ORB_CP - t))) far = q; cps.delete(far); } cps.set(k, { X: Float32Array.from(X), V: Float32Array.from(V) }); } };
  const restore = k => { const c = cps.get(k); X = Float64Array.from(c.X); V = Float64Array.from(c.V); t = k * ORB_CP; };
  function start() {
    let best = null; for (const k of cps.keys()) { const d = Math.abs(k * ORB_CP - goal); if (best === null || d < Math.abs(best * ORB_CP - goal)) best = k; }
    if (best !== null && Math.abs(best * ORB_CP - goal) < Math.abs(t - goal) - ORB_DT) restore(best);
  }
  function run() {
    if (goal === null) { busy = false; return; }
    busy = true;
    const left = Math.round((goal - t) / ORB_DT), m = Math.min(Math.abs(left), CHUNK), dir = Math.sign(left);
    for (let s = 0; s < m; s++) { orbSteps(P, X, V, n, dir * ORB_DT, 1, SUB, t); t = Math.round((t + dir * ORB_DT) / ORB_DT) * ORB_DT; save(); }
    if (Math.abs(left) <= CHUNK) { const pos = Float32Array.from(X), vel = Float32Array.from(V); postMessage({ t, pos, vel }, [pos.buffer, vel.buffer]); goal = null; busy = false; return; }
    setTimeout(run, 0);
  }
  onmessage = e => {
    const m = e.data;
    if (m.init) { P = m.P; n = m.n; X = Float64Array.from(m.X); V = Float64Array.from(m.V); SUB = orbSub(P, X, V, n); t = 0; cps.clear(); save(); return; }
    if (m.goto !== undefined) { goal = Math.round(m.goto / ORB_DT) * ORB_DT; start(); if (!busy) run(); }
  };
}

/** Démarre le calcul pour un catalogue : K vient d'initStarKin (K.gx0, K.gv0), le Soleil est ajouté en dernier.
 *  Sans Worker (vieux navigateur, test), K.orb reste absent : les étoiles gardent les épicycles. */
function orbInit(K, sunGal0) {
  if (typeof Worker === 'undefined' || typeof Blob === 'undefined' || !K.gx0) return null;
  if (K.orb && K.orb.w) { try { K.orb.w.terminate(); } catch (e) {} K.orb = null; }
  const n = K.N + 1, X = new Float64Array(n * 3), V = new Float64Array(n * 3);
  X.set(K.gx0); V.set(K.gv0); X.set(sunGal0, K.N * 3); V.set(SUN_UVW, K.N * 3);
  const src = [orbAcc, orbEnergy, orbSub, orbSteps, 'const ORB_DT=' + ORB_DT + ', ORB_CP=' + ORB_CP + ', ORB_MAXCP=' + ORB_MAXCP + ';', '(' + orbWorkerMain.toString() + ')();'].map(String).join(String.fromCharCode(10));
  let w; try { const url = URL.createObjectURL(new Blob([src], { type: 'text/javascript' })); w = new Worker(url); URL.revokeObjectURL(url); } catch (e) { return null; }
  const O = K.orb = { w, n: K.N, P: orbParams(), res: null, acc: null, want: null, sent: null, sentAt: 0, on: true, far: false, exact: false };
  w.onmessage = e => { O.res = e.data; O.acc = new Float32Array(n * 3).fill(NaN); O.sent = null; };
  w.onerror = () => { try { w.terminate(); } catch (e) {} if (K.orb === O) K.orb = null; };
  w.postMessage({ init: true, P: O.P, n, X, V }, [X.buffer, V.buffer]);
  return O;
}

/** À chaque image, avant le dessin. on : false quand la matière noire a été retirée (le temps affiché n'est plus le temps réel) ;
 *  far : plus de 2 Ma d'aujourd'hui (en deçà, les étoiles vont en ligne droite et rien n'est demandé).
 *  Choisit aussi, une fois pour l'image, entre orbite calculée et épicycles, avec un écart de bascule pour éviter le scintillement. */
let ORB_DM_ON = true;            /* faux quand la matière noire a été retirée (temps effectif) : décidé par la page, pas par le Worker */
function orbRequest(K, tEff, on, far) {
  ORB_DM_ON = on;
  const O = K && K.orb; if (!O) return;
  O.on = on; O.far = far; O.want = tEff;
  const lag = O.res ? Math.abs(O.res.t - tEff) : Infinity;
  if (O.exact && lag > ORB_EXTRA) O.exact = false; else if (!O.exact && lag <= ORB_EXTRA / 2) O.exact = true;
  if (!on || !far || lag < ORB_DT) return;
  const now = Date.now();
  if (O.sent !== null && (Math.abs(O.sent - tEff) < ORB_DT || now - O.sentAt < 80)) return;      /* une nouvelle demande remplace l'ancienne, au plus une toutes les 80 ms */
  O.sent = tEff; O.sentAt = now; O.w.postMessage({ goto: tEff });
}

/** L'orbite calculée sert-elle à tEff ? (mode choisi pour l'image, et résultat assez proche pour le prolongement) */
const orbFresh = (K, tEff) => { const O = K.orb; return !!(O && O.on && O.exact && O.res && Math.abs(O.res.t - tEff) <= ORB_EXTRA); };

/** Position galactique (kpc) de l'étoile i à tEff : orbite calculée, prolongée au second ordre (x + v·d + a·d²/2) sur moins
 *  de 6 Ma (au-delà, écart de plus de 50 pc pour 1 % des étoiles) ; sinon épicycle. Écart du prolongement mesuré dans orbits.test.js. */
const ORB_TMP_A = [0, 0, 0];
function starOrbPos(K, i, tEff, out, j) {
  j = j || 0;
  if (!orbFresh(K, tEff)) { epicyclePos(K.epi, i * 10, tEff, out, j); return; }
  const O = K.orb, R = O.res, d = (tEff - R.t) * ORB_KV, q = i * 3, A = O.acc;
  if (Number.isNaN(A[q])) { orbAcc(O.P, R.pos[q], R.pos[q + 1], R.pos[q + 2], ORB_TMP_A, R.t); A[q] = ORB_TMP_A[0]; A[q + 1] = ORB_TMP_A[1]; A[q + 2] = ORB_TMP_A[2]; }
  for (let c = 0; c < 3; c++) out[j + c] = R.pos[q + c] + R.vel[q + c] * d + 0.5 * A[q + c] * d * d;
}

/** Soleil, pour les positions des étoiles vues du Soleil : même règle que les étoiles, pour que leur écart reste cohérent. */
function starOrbSun(K, tEff, out) {
  if (!orbFresh(K, tEff)) { epicyclePos(K.sun, 0, tEff, out, 0); return out; }
  starOrbPos(K, K.orb.n, tEff, out, 0); return out;
}

/** Soleil dans la galaxie (vue d'ensemble, calcul de la rencontre) : une seule orbite, calculée ici même, sans attendre le Worker,
 *  à toute date. Points de contrôle tous les 100 Ma. Matière noire retirée : épicycles, comme avant. */
const SUN_ORB = { X: null, V: null, t: 0, cps: new Map() };
function sunOrbAt(K, tEff, out) {
  if (!ORB_DM_ON && K) { epicyclePos(K.sun, 0, tEff, out, 0); return out; }
  const S = SUN_ORB, P = orbParams();
  if (!S.X) { S.X = Float64Array.from(DATA.SGRA_GAL.map(x => -x * GAL.R0)); S.V = Float64Array.from(SUN_UVW); S.t = 0; S.cps.set(0, [S.X.slice(), S.V.slice()]); }
  const goal = Math.round(tEff / ORB_DT) * ORB_DT;
  let best = null; for (const k of S.cps.keys()) if (best === null || Math.abs(k * ORB_CP - goal) < Math.abs(best * ORB_CP - goal)) best = k;
  if (Math.abs(best * ORB_CP - goal) < Math.abs(S.t - goal)) { const c = S.cps.get(best); S.X = c[0].slice(); S.V = c[1].slice(); S.t = best * ORB_CP; }
  while (Math.abs(goal - S.t) > ORB_DT / 2) { const dir = Math.sign(goal - S.t); orbSteps(P, S.X, S.V, 1, dir * ORB_DT, 1, null, S.t); S.t = Math.round((S.t + dir * ORB_DT) / ORB_DT) * ORB_DT; const k = Math.round(S.t / ORB_CP); if (Math.abs(k * ORB_CP - S.t) < ORB_DT / 2 && !S.cps.has(k)) { if (S.cps.size >= ORB_MAXCP) { let far = null, fd = -1; for (const q of S.cps.keys()) if (q !== 0) { const dq = Math.abs(q * ORB_CP - goal); if (dq > fd) { fd = dq; far = q; } } if (far !== null) S.cps.delete(far); } S.cps.set(k, [S.X.slice(), S.V.slice()]); } }
  const d = (tEff - S.t) * ORB_KV; for (let c = 0; c < 3; c++) out[c] = S.X[c] + S.V[c] * d;
  return out;
}

/** Ligne « Mouvement » des fiches d'étoiles. gaia : étoile du flux Gaia (épicycles seulement). */
function orbMotionText(K, i, tEff, gaia) {
  if (K.lin && K.lin[i]) return 'en ligne droite avec la vitesse mesurée (passage près du Soleil publié)';
  const base = "ligne droite avec la vitesse mesurée jusqu'à 3 millions d'années, puis orbite ";
  if (gaia || !K.orb) return base + 'approchée (épicycles) dans un modèle de la Voie lactée';
  const now = K.orb.far && K.orb.on && !orbFresh(K, tEff) ? ' ; calcul en cours, orbite approchée affichée en attendant' : '';
  return base + 'calculée pas à pas dans un modèle de la Voie lactée (bulbe, disque, halo d’après Bovy 2015, recalé sur 230 km/s, et barre centrale tournante, Dehnen 2000, vitesse mesurée par Portail et al. 2017)' + now;
}
