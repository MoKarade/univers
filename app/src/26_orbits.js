/* --------------------------------------------------------------------------
   S2 — Orbites exactes des étoiles du catalogue principal (HYG, environ 59 000 étoiles).
   Chaque étoile, et le Soleil, est intégrée pas à pas dans le potentiel de la Voie lactée
   de 20_physics.js (bulbe de Hernquist + disque de Miyamoto-Nagai + halo NFW, objet GAL),
   par la méthode du saut de grenouille (vitesse de Verlet), pas de 1 Ma, dans un Web Worker.
   Tant que le résultat pour l'instant affiché n'est pas prêt, on garde l'approximation des
   épicycles (25_future.js), comme avant. Les étoiles Gaia en flux (millions) restent en épicycles.
   Unités : position en kpc, vitesse en km/s, temps en milliards d'années (Ga).
   -------------------------------------------------------------------------- */
const ORB_DT = 0.001;            /* pas d'intégration : 1 Ma */
const ORB_CP = 0.1;              /* point de contrôle tous les 100 Ma */
const ORB_MAXCP = 24;            /* points de contrôle gardés au plus (Float32 : environ 34 Mo pour 59 000 étoiles) */
const ORB_EXTRA = 0.02;          /* au-delà de 20 Ma d'écart avec le dernier résultat exact, on revient aux épicycles */
const ORB_KV = 1.0227121650456;  /* km/s -> kpc/Ga */

/** Paramètres du potentiel, copiés de GAL pour le Worker (qui ne voit pas le reste de la page). */
const orbParams = () => ({ G: G_KPC, Mb: GAL.Mb, ab: GAL.ab, Md: GAL.Md, ad: GAL.ad, bd: GAL.bd, rs: GAL.rs, GMs: GAL.GMs });

/** Accélération (km/s)²/kpc au point (x, y, z) kpc, écrite dans a[0..2]. */
function orbAcc(P, x, y, z, a) {
  const R2 = x * x + y * y, r = Math.sqrt(R2 + z * z) || 1e-9, xs = r / P.rs;
  const ar = -P.G * P.Mb / ((r + P.ab) * (r + P.ab)) - P.GMs * (Math.log(1 + xs) - xs / (1 + xs)) / (r * r);
  const B = Math.sqrt(z * z + P.bd * P.bd), D2 = R2 + (P.ad + B) * (P.ad + B), D3 = D2 * Math.sqrt(D2), gm = P.G * P.Md;
  a[0] = ar * x / r - gm * x / D3; a[1] = ar * y / r - gm * y / D3; a[2] = ar * z / r - gm * z * (P.ad + B) / (B * D3);
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
function orbSteps(P, X, V, n, dt, steps, sub) {
  const a = [0, 0, 0];
  for (let s = 0; s < steps; s++) for (let k = 0, j = 0; k < n; k++, j += 3) {
    const m = sub ? sub[k] : 1, h = dt * 1.0227121650456 / m;
    for (let u = 0; u < m; u++) {
      orbAcc(P, X[j], X[j + 1], X[j + 2], a);
      V[j] += 0.5 * h * a[0]; V[j + 1] += 0.5 * h * a[1]; V[j + 2] += 0.5 * h * a[2];
      X[j] += h * V[j]; X[j + 1] += h * V[j + 1]; X[j + 2] += h * V[j + 2];
      orbAcc(P, X[j], X[j + 1], X[j + 2], a);
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
    for (let s = 0; s < m; s++) { orbSteps(P, X, V, n, dir * ORB_DT, 1, SUB); t = Math.round((t + dir * ORB_DT) / ORB_DT) * ORB_DT; save(); }
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
 *  Sans Worker (vieux navigateur, test), K.orb reste absent et rien ne change. */
function orbInit(K, sunGal0) {
  if (typeof Worker === 'undefined' || typeof Blob === 'undefined' || !K.gx0) return null;
  const n = K.N + 1, X = new Float64Array(n * 3), V = new Float64Array(n * 3);
  X.set(K.gx0); V.set(K.gv0); X.set(sunGal0, K.N * 3); V.set(SUN_UVW, K.N * 3);
  const src = [orbAcc, orbEnergy, orbSub, orbSteps, 'const ORB_DT=' + ORB_DT + ', ORB_CP=' + ORB_CP + ', ORB_MAXCP=' + ORB_MAXCP + ';', '(' + orbWorkerMain.toString() + ')();'].map(String).join('\n');
  let w; try { w = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' }))); } catch (e) { return null; }
  const O = K.orb = { w, n: K.N, res: null, want: null, busy: false, on: true };
  w.onmessage = e => { O.res = e.data; O.busy = false; if (O.want !== null && Math.abs(O.want - O.res.t) >= ORB_DT) orbRequest(K, O.want); };
  w.onerror = () => { K.orb = null; };
  w.postMessage({ init: true, P: orbParams(), n, X, V }, [X.buffer, V.buffer]);
  return O;
}

/** À chaque image : demande l'orbite exacte pour tEff (Ga). on = false quand la matière noire est retirée (temps effectif). */
function orbRequest(K, tEff, on) {
  const O = K && K.orb; if (!O) return;
  if (on !== undefined) O.on = on;
  O.want = tEff;
  if (!O.on || O.busy || (O.res && Math.abs(O.res.t - tEff) < ORB_DT)) return;
  O.busy = true; O.w.postMessage({ goto: tEff });
}

/** Le résultat exact est-il utilisable à tEff ? */
const orbFresh = (K, tEff) => { const O = K.orb; return !!(O && O.on && O.res && Math.abs(O.res.t - tEff) <= ORB_EXTRA); };

/** Position galactique (kpc) de l'étoile i à tEff : orbite exacte (prolongée en ligne droite sur moins de 20 Ma), sinon épicycle. */
function starOrbPos(K, i, tEff, out, j) {
  j = j || 0;
  if (!orbFresh(K, tEff)) { epicyclePos(K.epi, i * 10, tEff, out, j); return; }
  const R = K.orb.res, d = (tEff - R.t) * ORB_KV, q = i * 3;
  out[j] = R.pos[q] + R.vel[q] * d; out[j + 1] = R.pos[q + 1] + R.vel[q + 1] * d; out[j + 2] = R.pos[q + 2] + R.vel[q + 2] * d;
}

/** Position galactique du Soleil à tEff, de la même façon. */
function starOrbSun(K, tEff, out) {
  if (!orbFresh(K, tEff)) { epicyclePos(K.sun, 0, tEff, out, 0); return out; }
  return starOrbPos(K, K.orb.n, tEff, out, 0), out;
}
