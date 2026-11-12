/* --------------------------------------------------------------------------
   S7 — Distances des galaxies des relevés, pour deux façons de voir l'univers :
   - à cet instant (par défaut) : la distance comobile χ, celle de la galaxie aujourd'hui ;
   - telle que la lumière nous arrive (cône de lumière) : la distance de la galaxie au moment où elle a émis la
     lumière que nous recevons, a(émission) × χ = χ / (1 + z), c'est-à-dire la distance angulaire. Au-delà de
     z ≈ 1,6 elle diminue : les galaxies les plus lointaines étaient plus près de nous quand leur lumière est partie.
   Table indexée par u = ln(1 + z) / ln(1 + zmax), K + 1 points, en Mpc (unités de C.chi).
   -------------------------------------------------------------------------- */
function surveyLutOf(C, zmax, lightcone) {
  const K = 1024, lut = new Float32Array(K + 1), lz = Math.log(1 + zmax);
  let iNow = 0; while (iNow < C.n - 1 && C.t[iNow + 1] <= 1e-9) iNow++;
  let j0 = iNow; while (j0 > 0 && C.a[j0 - 1] < C.a[j0]) j0--;
  let j = iNow;
  for (let k = 0; k <= K; k++) {
    const a = Math.exp(-k / K * lz);
    while (j > j0 && C.a[j - 1] > a) j--;
    const chi = j > j0 ? lerp(C.chi[j - 1], C.chi[j], clamp((a - C.a[j - 1]) / (C.a[j] - C.a[j - 1]), 0, 1)) : C.chi[j0] * clamp(a / C.a[j0], 0, 1);
    lut[k] = Math.max(C.chi[iNow] - chi, 0) * (lightcone ? a / C.a[iNow] : 1);
  }
  return lut;
}
