/* --------------------------------------------------------------------------
   S6 — Lumière déviée par un trou noir (métrique de Schwarzschild, sans rotation : la rotation de
   Sagittarius A* et de M87* n'est pas mesurée de façon sûre). Unités géométriques : M = GM/c² = 1.
   Pour un observateur immobile à la distance r, un rayon de vue faisant l'angle ψ avec la direction du
   trou noir a le paramètre d'impact b = r sin ψ / √(1 − 2/r). On suit ce rayon à rebours jusqu'à l'infini
   et on rend l'angle Δφ balayé autour du trou noir (−1 s'il tombe dedans : l'ombre).
   Équation de l'orbite des photons : (du/dφ)² = 1/b² − u²(1 − 2u), avec u = 1/r.
   Valable pour r > 3 (hors de la sphère des photons) ; la page coupe l'image en deçà de LENS_RMIN.
   -------------------------------------------------------------------------- */
const LENS_N = 1200;                 /* pas d'intégration (écart au développement publié < 2 % du second ordre) */
const LENS_MAXPHI = 4 * Math.PI;     /* au-delà de deux tours, la valeur est plafonnée (anneaux trop fins pour l'écran) */
const LENS_RMIN = 3.1;               /* en deçà, hors du domaine du calcul : image coupée, « inconnu » */
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

/** Rayon angulaire de l'ombre vu depuis r : b = √27 M. */
const lensPsiC = r => Math.asin(Math.min(1, Math.sqrt(27) * Math.sqrt(1 - 2 / r) / r));

/** Table pour le shader : n angles ψ = ψc + e^l, l régulier de l0 à l1 (dense près du bord de l'ombre, à toutes les échelles) ;
 *  on garde la déviation α = Δφ − (π − ψ), petite loin du trou noir, pour qu'elle reste précise. */
function lensLut(r, n) {
  const psiC = lensPsiC(r), l0 = Math.log(1e-6 * Math.max(psiC, 1e-9)), l1 = Math.log(Math.PI - psiC), a = new Float32Array(n);
  for (let i = 0; i < n; i++) { const psi = psiC + Math.exp(l0 + i / (n - 1) * (l1 - l0)), d = lensDphi(r, psi); a[i] = d < 0 ? 0 : d - (Math.PI - psi); }
  return { psiC, l0, l1, alpha: a, n };
}

/** Lecture de la table, comme le shader final (40_render.js, lensed) : −1 dans l'ombre. */
function lensLookup(T, psi) {
  if (psi <= T.psiC) return -1;
  const x = Math.min(Math.max((Math.log(psi - T.psiC) - T.l0) / (T.l1 - T.l0), 0), 1) * (T.n - 1), i = Math.min(Math.floor(x), T.n - 2), f = x - i;
  return (Math.PI - psi) + T.alpha[i] * (1 - f) + T.alpha[i + 1] * f;
}

/** Direction d'où vient la lumière vue dans la direction v (unitaire), le trou noir étant dans la direction c (unitaire) :
 *  s = cos Δφ · r̂ + sin Δφ · t̂, r̂ = −c (du trou noir vers la caméra), t̂ dans le plan (v, c). Même calcul que le shader. */
function lensSource(T, v, c) {
  const cp = v[0] * c[0] + v[1] * c[1] + v[2] * c[2], x = [v[1] * c[2] - v[2] * c[1], v[2] * c[0] - v[0] * c[2], v[0] * c[1] - v[1] * c[0]], sp = Math.hypot(x[0], x[1], x[2]);
  const d = lensLookup(T, Math.atan2(sp, cp)); if (d < 0) return null;
  const t = [0, 1, 2].map(k => (v[k] + cp * -c[k]) / Math.max(sp, 1e-12));
  return [0, 1, 2].map(k => Math.cos(d) * -c[k] + Math.sin(d) * t[k]);
}
