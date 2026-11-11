/* --------------------------------------------------------------------------
   S5 — Poussière mesurée en 3D autour du Soleil (Edenhofer et al. 2024, DATA.DUST, pipeline/build_dust.py).
   Mêmes calculs que le shader des étoiles (40_render.js, dustD / dustA) : densité de la case la plus proche,
   12 points le long du trajet. Positions en parsecs, repère galactique héliocentrique.
   -------------------------------------------------------------------------- */
let DUST_Q = null;
/** dA_V/ds (mag/pc) au point g ; 0 hors de la carte (au-delà de 1,25 kpc ou de 406 pc du plan). */
function dustDens(g) {
  const D = DATA.DUST; if (!DUST_Q) DUST_Q = b64ToBytes(D.q);
  const x = g[0] / D.cell + D.nx / 2, y = g[1] / D.cell + D.ny / 2, z = g[2] / D.cell + D.nz / 2;
  if (x < 0 || y < 0 || z < 0 || x >= D.nx || y >= D.ny || z >= D.nz) return 0;
  const v = DUST_Q[(Math.floor(z) * D.ny + Math.floor(y)) * D.nx + Math.floor(x)];
  return v ? Math.pow(10, D.lo + (v - 1) / 254 * D.span) : 0;
}
/** Extinction A_V (mag) de a à b (pc, galactique). */
function dustAv(a, b) { const d = [0, 1, 2].map(k => (b[k] - a[k]) / 12); let s = 0; for (let i = 0; i < 12; i++) s += dustDens([0, 1, 2].map(k => a[k] + d[k] * (i + 0.5))); return s * Math.hypot(d[0], d[1], d[2]); }
/** Repère écliptique héliocentrique en années-lumière -> galactique en parsecs. */
function eclLyToGalPc(v) { const M = DATA.M_GAL2ECL; return [0, 1, 2].map(c => (M[0][c] * v[0] + M[1][c] * v[1] + M[2][c] * v[2]) / 3.26156); }
