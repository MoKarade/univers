/* ==========================================================================
   Gravité mutuelle du système solaire (lot G, niveaux G1 et G2).

   Tous les corps massifs s'attirent entre eux : le Soleil, les huit planètes
   (barycentres planète + lunes), Pluton, et les quatre plus gros astéroïdes.
   Les petits tirent donc aussi sur les gros : c'est ce qui fait tourner le
   Soleil autour du centre de masse du système solaire.

   Méthode : intégrateur symplectique de Wisdom et Holman (1991), en
   coordonnées « héliocentriques démocratiques » (Duncan, Levison et Lee 1998,
   AJ 116, 2067) : alternance d'un mouvement de Kepler exact autour du Soleil
   et de coups de vitesse dus aux autres corps. Symplectique : l'énergie ne
   dérive pas sur des millions d'années.
   Relativité générale : terme post-newtonien du Soleil (voir nbGr), qui donne
   l'avance du périhélie de Mercure (43″ par siècle).

   Unités : UA, jour, GM en UA³/jour². Repère : écliptique J2000.
   Masses : éphéméride JPL DE440 (Park et al. 2021, AJ 161, 105) [Probable :
   valeurs recopiées, contrôlées par app/test/nbody.test.js contre Horizons].
   ========================================================================== */
const NB_GM_SUN = 2.9591220828411956e-4;
const NB_BODIES = [
  ['mercury', 4.9125001948893182e-11], ['venus', 7.2434524861627027e-10], ['emb', 8.9970116036316091e-10],
  ['mars', 9.5495488297258119e-11], ['jupiter', 2.8253458252257917e-7], ['saturn', 8.4597059933762903e-8],
  ['uranus', 1.2920265649682399e-8], ['neptune', 1.5243573478851939e-8], ['pluto', 2.1750964648933581e-12],
  ['ceres', 1.3964518123081070e-13], ['vesta', 3.8548000225257904e-14], ['pallas', 3.0471146330043200e-14],
  ['hygiea', 1.2542530761640810e-14]];
const NB_C_AU_DAY = 173.1446326846693;      // vitesse de la lumière en UA/jour
let NB_GR_K = 1;      // 0 : sans relativité (contrôles)

/** Somme des GM des planètes de PLANET_KEYS (pour le centre de masse héliocentrique). */
const NB_GM_OF = Object.fromEntries(NB_BODIES);

/** G1 : position du Soleil par rapport au centre de masse, en UA, à partir des positions
    héliocentriques des corps massifs (sol : sortie de solarSystemAt). Exact pour ces corps. */
function sunBaryOffset(sol, out) {
  out = out || [0, 0, 0];
  let m = NB_GM_SUN, x = 0, y = 0, z = 0;
  for (const k of PLANET_KEYS) {
    const g = NB_GM_OF[k], p = sol.planets[k] && sol.planets[k].pos; if (!g || !p) continue;
    x += g * p[0]; y += g * p[1]; z += g * p[2]; m += g;
  }
  out[0] = -x / m; out[1] = -y / m; out[2] = -z / m;
  return out;
}

/** Mouvement de Kepler exact pendant dt (variables d'anomalie excentrique, orbites liées).
    r, v : Float64Array, indice de départ o. Renvoie false si l'orbite n'est pas liée. */
function nbKepler(r, v, o, mu, dt) {
  const x0 = r[o], y0 = r[o + 1], z0 = r[o + 2], vx = v[o], vy = v[o + 1], vz = v[o + 2];
  const r0 = Math.sqrt(x0 * x0 + y0 * y0 + z0 * z0), v2 = vx * vx + vy * vy + vz * vz, rv = x0 * vx + y0 * vy + z0 * vz;
  const ia = 2 / r0 - v2 / mu; if (!(ia > 0)) return false;
  const a = 1 / ia, sa = Math.sqrt(a), n = Math.sqrt(mu * ia * ia * ia), s0 = rv / Math.sqrt(mu), c1 = 1 - r0 * ia, c2 = s0 / sa;
  const M = n * dt;
  let X = M;
  for (let k = 0; k < 30; k++) {
    const sx = Math.sin(X), cx = Math.cos(X), f = X - c1 * sx + c2 * (1 - cx) - M, fp = 1 - c1 * cx + c2 * sx;
    const d = f / fp; X -= d; if (Math.abs(d) < 1e-14) break;
  }
  const sx = Math.sin(X), cx = Math.cos(X), rr = a + (r0 - a) * cx + s0 * sa * sx;
  const f = 1 - a / r0 * (1 - cx), g = dt + (sx - X) / n, fd = -Math.sqrt(mu * a) * sx / (rr * r0), gd = 1 - a / rr * (1 - cx);
  r[o] = f * x0 + g * vx; r[o + 1] = f * y0 + g * vy; r[o + 2] = f * z0 + g * vz;
  v[o] = fd * x0 + gd * vx; v[o + 1] = fd * y0 + gd * vy; v[o + 2] = fd * z0 + gd * vz;
  return true;
}

/** Crée l'état à partir d'états barycentriques (r, v en UA et UA/jour) : ref[nom] = { r, v }. */
function nbCreate(ref, jd) {
  const N = NB_BODIES.length, S = { N, jd, gm: new Float64Array(N), Q: new Float64Array(N * 3), V: new Float64Array(N * 3), names: NB_BODIES.map(b => b[0]) };
  const s = ref.sun;
  NB_BODIES.forEach(([k, g], i) => { const b = ref[k]; S.gm[i] = g; for (let c = 0; c < 3; c++) { S.Q[i * 3 + c] = b.r[c] - s.r[c]; S.V[i * 3 + c] = b.v[c]; } });
  return S;
}

/* Coups de vitesse : attraction mutuelle des corps (sans le Soleil, qui est dans Kepler) + relativité. */
function nbKick(S, h) {
  const { N, Q, V, gm } = S;
  if (NB_GR_K) nbGr(S, h / 2);      /* relativité en deux moitiés autour de l'attraction : le pas reste réversible */
  for (let i = 0; i < N; i++) {
    const i3 = i * 3, xi = Q[i3], yi = Q[i3 + 1], zi = Q[i3 + 2];
    for (let j = i + 1; j < N; j++) {
      const j3 = j * 3, dx = Q[j3] - xi, dy = Q[j3 + 1] - yi, dz = Q[j3 + 2] - zi, d2 = dx * dx + dy * dy + dz * dz, k = h / (d2 * Math.sqrt(d2));
      const ki = gm[j] * k, kj = gm[i] * k;
      V[i3] += ki * dx; V[i3 + 1] += ki * dy; V[i3 + 2] += ki * dz; V[j3] -= kj * dx; V[j3 + 1] -= kj * dy; V[j3 + 2] -= kj * dz;
    }
  }
  if (NB_GR_K) nbGr(S, h / 2);
}
/* Relativité générale, premier ordre post-newtonien autour du Soleil (Schwarzschild, jauge harmonique) :
   a = GM/(c² r³) [ (4 GM/r − v²) r + 4 (r·v) v ], v vitesse héliocentrique (Anderson et al. 1975 ; c'est aussi
   le terme dominant de l'éphéméride DE440). Dépend de la vitesse : appliqué au milieu du coup, deux passes. */
function nbGr(S, h) {
  const { N, Q, V, gm } = S, c2 = NB_C_AU_DAY * NB_C_AU_DAY, mu = NB_GM_SUN;
  let px = 0, py = 0, pz = 0;
  for (let i = 0; i < N; i++) { px += gm[i] * V[i * 3]; py += gm[i] * V[i * 3 + 1]; pz += gm[i] * V[i * 3 + 2]; }
  const sx = -px / mu, sy = -py / mu, sz = -pz / mu;
  for (let i = 0; i < N; i++) {
    const i3 = i * 3, x = Q[i3], y = Q[i3 + 1], z = Q[i3 + 2], r = Math.sqrt(x * x + y * y + z * z);
    let vx = V[i3] - sx, vy = V[i3 + 1] - sy, vz = V[i3 + 2] - sz, ax = 0, ay = 0, az = 0;
    for (let it = 0; it < 3; it++) {
      const ux = vx + ax * h / 2, uy = vy + ay * h / 2, uz = vz + az * h / 2, v2 = ux * ux + uy * uy + uz * uz, rv = x * ux + y * uy + z * uz, k = mu / (c2 * r * r * r), a1 = 4 * mu / r - v2;
      ax = k * (a1 * x + 4 * rv * ux); ay = k * (a1 * y + 4 * rv * uy); az = k * (a1 * z + 4 * rv * uz);
    }
    V[i3] += h * ax; V[i3 + 1] += h * ay; V[i3 + 2] += h * az;
  }
}
/* Saut : déplacement dû au mouvement du Soleil (quantité de mouvement totale des corps). */
function nbJump(S, h) {
  const { N, Q, V, gm } = S; let px = 0, py = 0, pz = 0;
  for (let i = 0; i < N; i++) { px += gm[i] * V[i * 3]; py += gm[i] * V[i * 3 + 1]; pz += gm[i] * V[i * 3 + 2]; }
  const k = h / NB_GM_SUN;
  for (let i = 0; i < N; i++) { Q[i * 3] += k * px; Q[i * 3 + 1] += k * py; Q[i * 3 + 2] += k * pz; }
}

/** Avance de nSteps pas de dt jours (dt < 0 : vers le passé, le schéma est réversible). */
function nbStep(S, dt, nSteps) {
  for (let s = 0; s < nSteps; s++) {
    nbJump(S, dt / 2); nbKick(S, dt / 2);
    for (let i = 0; i < S.N; i++) nbKepler(S.Q, S.V, i * 3, NB_GM_SUN, dt);
    nbKick(S, dt / 2); nbJump(S, dt / 2);
  }
  S.jd += dt * nSteps;
  return S;
}

/** Avance jusqu'à la date jd (pas d'au plus dtMax jours ; le dernier est raccourci). */
function nbAdvanceTo(S, jd, dtMax) {
  dtMax = dtMax || 2;
  const span = jd - S.jd, n = Math.ceil(Math.abs(span) / dtMax);
  if (n > 0) { const jd1 = jd; nbStep(S, span / n, n); S.jd = jd1; }
  return S;
}

/** Positions barycentriques (UA) : Soleil puis chaque corps, dans out (Float64Array (N+1)*3). */
function nbBary(S, out) {
  const { N, Q, gm } = S; out = out || new Float64Array((N + 1) * 3);
  let m = NB_GM_SUN, x = 0, y = 0, z = 0;
  for (let i = 0; i < N; i++) { m += gm[i]; x += gm[i] * Q[i * 3]; y += gm[i] * Q[i * 3 + 1]; z += gm[i] * Q[i * 3 + 2]; }
  out[0] = -x / m; out[1] = -y / m; out[2] = -z / m;
  for (let i = 0; i < N; i++) for (let c = 0; c < 3; c++) out[(i + 1) * 3 + c] = Q[i * 3 + c] + out[c];
  return out;
}

/** Énergie newtonienne totale (barycentrique), pour les contrôles. */
function nbEnergy(S) {
  const { N, Q, V, gm } = S, b = nbBary(S); let px = 0, py = 0, pz = 0, E = 0;
  for (let i = 0; i < N; i++) { px += gm[i] * V[i * 3]; py += gm[i] * V[i * 3 + 1]; pz += gm[i] * V[i * 3 + 2]; }
  E += (px * px + py * py + pz * pz) / (2 * NB_GM_SUN);
  for (let i = 0; i < N; i++) {
    const i3 = i * 3, r = Math.hypot(Q[i3], Q[i3 + 1], Q[i3 + 2]);
    E += gm[i] * (0.5 * (V[i3] ** 2 + V[i3 + 1] ** 2 + V[i3 + 2] ** 2) - NB_GM_SUN / r);
    for (let j = i + 1; j < N; j++) E -= gm[i] * gm[j] / Math.hypot(Q[j * 3] - Q[i3], Q[j * 3 + 1] - Q[i3 + 1], Q[j * 3 + 2] - Q[i3 + 2]);
  }
  return E;
}

/** État de départ calé sur DE440 (app/gen/nbody.js, pipeline/gravite/ajuste.js). */
function nbFromData(D) {
  D = D || DATA.NB;
  return { N: D.names.length, jd: D.jd, names: D.names.slice(), gm: Float64Array.from(D.gm), Q: Float64Array.from(D.Q), V: Float64Array.from(D.V), dt: D.dt };
}
