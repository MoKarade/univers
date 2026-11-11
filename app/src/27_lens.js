/* --------------------------------------------------------------------------
   S6 — Lumière déviée par un trou noir (métrique de Schwarzschild, sans rotation : la rotation de
   Sagittarius A* et de M87* n'est pas mesurée de façon sûre). Unités géométriques : M = GM/c² = 1.
   Pour un observateur immobile à la distance r, un rayon de vue faisant l'angle ψ avec la direction du
   trou noir a le paramètre d'impact b = r sin ψ / √(1 − 2/r). On suit ce rayon à rebours jusqu'à l'infini
   et on rend l'angle Δφ balayé autour du trou noir (−1 s'il tombe dedans : l'ombre).
   Équation de l'orbite des photons : (du/dφ)² = 1/b² − u²(1 − 2u), avec u = 1/r.
   -------------------------------------------------------------------------- */
const LENS_N = 1200;                 /* pas d'intégration (écart au développement publié < 2 % du second ordre) */
const LENS_MAXPHI = 4 * Math.PI;     /* au-delà de deux tours, la valeur est plafonnée (anneaux trop fins pour l'écran) */
const GM_C2_SUN = 1476.625;          /* GM☉/c² en mètres */

/** ∫ du / √F(u) de ua à u0, où F s'annule en u0 (point de rebroussement) : changement u = u0(1 − w²), sans singularité. */
function lensTurnInt(Finv, ua, u0) {
  const wa = Math.sqrt(Math.max(0, 1 - ua / u0)); let s = 0;
  for (let k = 0; k < LENS_N; k++) { const w = (k + 0.5) / LENS_N * wa, u = u0 * (1 - w * w), F = Finv(u); if (F > 0) s += 2 * u0 * w / Math.sqrt(F); }
  return s * wa / LENS_N;
}

/** Angle balayé par le rayon vu sous l'angle psi depuis la distance r (en M) ; −1 s'il est capturé. */
function lensDphi(r, psi) {
  const sp = Math.sin(psi), b = r * sp / Math.sqrt(1 - 2 / r), uo = 1 / r, ib2 = 1 / (b * b);
  const F = u => ib2 - u * u * (1 - 2 * u);
  if (psi >= Math.PI / 2) return Math.min(lensTurnInt(F, 0, uo), LENS_MAXPHI);      /* le rayon s'éloigne : de r jusqu'à l'infini (u = uo(1 − w²) traite le cas tangent) */
  if (b <= Math.sqrt(27)) return -1;                                                  /* il plonge sous la sphère des photons : capturé */
  let lo = 0, hi = 1 / 3; for (let k = 0; k < 80; k++) { const m = 0.5 * (lo + hi); if (m * m * (1 - 2 * m) < ib2) lo = m; else hi = m; }
  const u0 = 0.5 * (lo + hi);                                                         /* plus petite distance au trou noir */
  return Math.min(lensTurnInt(F, uo, u0) + lensTurnInt(F, 0, u0), LENS_MAXPHI);
}

/** Table de Δφ pour n angles ψ de 0 à π, vue depuis la distance r (en M). */
function lensLut(r, n) { const T = new Float32Array(n); for (let i = 0; i < n; i++) T[i] = lensDphi(r, i / (n - 1) * Math.PI); return T; }

/** Codage pour une texture 8 bits : Δφ / LENS_MAXPHI sur 16 bits (rouge, vert), ombre dans le bleu. */
function lensLutBytes(T) {
  const B = new Uint8Array(T.length * 4);
  for (let i = 0; i < T.length; i++) { if (T[i] < 0) { B[i * 4 + 2] = 255; continue; } const q = Math.round(Math.min(T[i], LENS_MAXPHI) / LENS_MAXPHI * 65535); B[i * 4] = q >> 8; B[i * 4 + 1] = q & 255; B[i * 4 + 3] = 255; }
  return B;
}
/** Décodage (le même calcul est fait dans le shader final). */
const lensDecode = (B, i) => (B[i * 4] * 256 + B[i * 4 + 1]) / 65535 * LENS_MAXPHI;
