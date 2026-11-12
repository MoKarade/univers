/* --------------------------------------------------------------------------
   S5 — Poussière mesurée en 3D autour du Soleil (Edenhofer et al. 2024, DATA.DUST, pipeline/build_dust.py).
   Positions en parsecs, repère galactique héliocentrique (x vers le centre, y vers l = 90°, z vers le pôle nord).
   L'extinction d'un trajet est intégrée sur 32 points, dans le niveau de finesse dont la case vaut à peu près
   le pas (cases de 15,6, 31, 62 ou 125 pc, moyennes exactes des cases fines) : un long trajet reste juste
   sans lire des milliers de cases. Même calcul en JS (fiches, tests) et dans le shader des étoiles (DUST_GLSL).
   -------------------------------------------------------------------------- */
const DUST_NS = 64;                       /* points par trajet */
const DUST_AW = 1280;                     /* largeur de l'atlas */
let DUST_L = null;

/** Niveaux de finesse (densités dA_V/ds en mag/pc) et atlas d'octets pour la carte graphique. */
function dustLevels() {
  if (DUST_L) return DUST_L;
  const D = DATA.DUST, q = b64ToBytes(D.q), dec = v => v ? Math.pow(10, D.lo + (v - 1) / 254 * D.span) : 0;
  const enc = x => x < Math.pow(10, D.lo) ? 0 : 1 + Math.min(254, Math.max(0, Math.round((Math.log10(x) - D.lo) / D.span * 254)));
  let cur = { nx: D.nx, ny: D.ny, nz: D.nz, cell: D.cell, d: Float32Array.from(q, dec) };
  const L = [cur];
  for (let l = 1; l < 4; l++) {      /* moyenne de 2 × 2 × 2 cases (une case hors grille compte pour 0) */
    const p = cur, n = { nx: p.nx / 2, ny: p.ny / 2, nz: Math.ceil(p.nz / 2), cell: p.cell * 2 }; n.d = new Float32Array(n.nx * n.ny * n.nz);
    for (let k = 0; k < n.nz; k++) for (let j = 0; j < n.ny; j++) for (let i = 0; i < n.nx; i++) { let s = 0;
      for (let c = 0; c < 8; c++) { const ii = 2 * i + (c & 1), jj = 2 * j + (c >> 1 & 1), kk = 2 * k + (c >> 2); if (kk < p.nz) s += p.d[(kk * p.ny + jj) * p.nx + ii]; }
      n.d[(k * n.ny + j) * n.nx + i] = s / 8; }
    L.push(cur = n);
  }
  /* atlas : chaque niveau en bandes de tranches, l'une sous l'autre */
  let y0 = 0; for (const l of L) { l.cols = Math.floor(DUST_AW / l.nx); l.y0 = y0; y0 += Math.ceil(l.nz / l.cols) * l.ny; l.z0 = -(D.nz / 2) * D.cell; }
  const H = y0, A = new Uint8Array(DUST_AW * H);
  for (const l of L) for (let k = 0; k < l.nz; k++) { const c0 = (k % l.cols) * l.nx, r0 = l.y0 + Math.floor(k / l.cols) * l.ny;
    for (let j = 0; j < l.ny; j++) for (let i = 0; i < l.nx; i++) A[(r0 + j) * DUST_AW + c0 + i] = enc(l.d[(k * l.ny + j) * l.nx + i]); }
  for (const l of L) l.q = l.d.map(x => { const v = enc(x); return dec(v); });      /* valeurs telles que la carte graphique les lit */
  DUST_L = { levels: L, atlas: A, w: DUST_AW, h: H, half: [D.nx / 2 * D.cell, D.ny / 2 * D.cell, D.nz / 2 * D.cell] };
  return DUST_L;
}

/** Densité au point g (pc) dans le niveau l. */
function dustDensL(l, g) { const x = Math.floor(g[0] / l.cell + l.nx / 2), y = Math.floor(g[1] / l.cell + l.ny / 2), z = Math.floor((g[2] - l.z0) / l.cell);
  return x < 0 || y < 0 || z < 0 || x >= l.nx || y >= l.ny || z >= l.nz ? 0 : l.q[(z * l.ny + y) * l.nx + x]; }
/** Densité dA_V/ds (mag/pc) au point g, niveau le plus fin ; 0 hors de la carte. */
function dustDens(g) { return dustDensL(dustLevels().levels[0], g); }

/** Partie d'un trajet de l'étoile s vers x (paramètre u : 0 à l'étoile, 1 en x) qui traverse la boîte de la carte. */
function dustClip(s, x) {
  const h = dustLevels().half, d = [x[0] - s[0], x[1] - s[1], x[2] - s[2]]; let u0 = 0, u1 = 1;
  for (let c = 0; c < 3; c++) { if (Math.abs(d[c]) < 1e-9) { if (s[c] < -h[c] || s[c] > h[c]) return null; continue; }
    const p = (-h[c] - s[c]) / d[c], q = (h[c] - s[c]) / d[c]; u0 = Math.max(u0, Math.min(p, q)); u1 = Math.min(u1, Math.max(p, q)); }
  return u1 > u0 ? [u0, u1, Math.hypot(d[0], d[1], d[2])] : null;
}
/** Somme de l'extinction de l'étoile s vers x, points espacés de st à partir de l'étoile (même grille pour tous les trajets d'une étoile). */
function dustSum(l, s, x, cl, st) {
  if (!cl) return 0; const [u0, u1, L] = cl, k0 = Math.max(0, Math.ceil(u0 * L / st - 0.5)); let sum = 0;
  for (let k = k0; k < k0 + DUST_NS + 2; k++) { const r = (k + 0.5) * st; if (r > u1 * L) break; const u = r / L; sum += dustDensL(l, [s[0] + (x[0] - s[0]) * u, s[1] + (x[1] - s[1]) * u, s[2] + (x[2] - s[2]) * u]); }
  return sum * st;
}
/** Extinctions A_V (mag) de la caméra c et du Soleil (origine) jusqu'à l'étoile s : même pas, même grille, ancrée sur l'étoile.
 *  Le pas vaut la plus longue des deux traversées de la carte divisée par 64 ; niveau de finesse dont la case vaut ce pas.
 *  Quand la caméra rejoint le Soleil, les deux sommes se confondent : pas de saut. */
function dustPair(c, s) {
  const W = dustLevels(), a = dustClip(s, c), b = dustClip(s, [0, 0, 0]), len = Math.max(a ? (a[1] - a[0]) * a[2] : 0, b ? (b[1] - b[0]) * b[2] : 0);
  if (len <= 0) return [0, 0];
  const st = len / DUST_NS, l = W.levels[Math.min(3, Math.max(0, Math.round(Math.log2(st / W.levels[0].cell))))];
  return [dustSum(l, s, c, a, st), dustSum(l, s, [0, 0, 0], b, st)];
}
/** Extinction A_V (mag) de a à b (pc, galactique). */
function dustAv(a, b) { return dustPair(a, b)[0]; }

/** Repère écliptique héliocentrique en années-lumière -> galactique en parsecs. */
function eclLyToGalPc(v) { const M = DATA.M_GAL2ECL; return [0, 1, 2].map(c => (M[0][c] * v[0] + M[1][c] * v[1] + M[2][c] * v[2]) / 3.26156); }

/** Code GLSL du même calcul (atlas tDust, dimensions tirées de dustLevels). */
function dustGlsl() {
  const W = dustLevels(), f = x => x.toFixed(4), L = W.levels;
  const pick = L.map((l, i) => `${i ? 'else ' : ''}if(lev<${i}.5){ n=vec3(${f(l.nx)},${f(l.ny)},${f(l.nz)}); cell=${f(l.cell)}; cols=${f(l.cols)}; y0=${f(l.y0)}; }`).join(' ');
  return `uniform sampler2D tDust;
float dustL(vec3 g,float lev){ vec3 n; float cell,cols,y0; ${pick}
  vec3 c=floor(vec3(g.x/cell+n.x*0.5,g.y/cell+n.y*0.5,(g.z+${f(W.half[2])})/cell)); if(c.x<0.0||c.y<0.0||c.z<0.0||c.x>=n.x||c.y>=n.y||c.z>=n.z) return 0.0;
  float b=texture2D(tDust,vec2((mod(c.z,cols)*n.x+c.x+0.5)/${f(W.w)},(y0+floor(c.z/cols)*n.y+c.y+0.5)/${f(W.h)})).r*255.0; return b<0.5?0.0:pow(10.0,${f(DATA.DUST.lo)}+(b-1.0)/254.0*${f(DATA.DUST.span)}); }
vec3 dustClip(vec3 s,vec3 x){ vec3 d=x-s, h=vec3(${f(W.half[0])},${f(W.half[1])},${f(W.half[2])}); float u0=0.0,u1=1.0;
  for(int c=0;c<3;c++){ float dc=d[c], sc=s[c], hc=h[c]; if(abs(dc)<1e-9){ if(sc<-hc||sc>hc) return vec3(1.0,0.0,1.0); } else { float p=(-hc-sc)/dc, q=(hc-sc)/dc; u0=max(u0,min(p,q)); u1=min(u1,max(p,q)); } }
  return vec3(u0,u1,length(d)); }
float dustSum(float lev,vec3 s,vec3 x,vec3 cl,float st){ if(cl.y<=cl.x) return 0.0; float k0=max(0.0,ceil(cl.x*cl.z/st-0.5)), sum=0.0;
  for(int k=0;k<${DUST_NS + 2};k++){ float r=(k0+float(k)+0.5)*st; if(r>cl.y*cl.z) break; sum+=dustL(s+(x-s)*(r/cl.z),lev); } return sum*st; }
vec2 dustPair(vec3 c,vec3 s){ vec3 a=dustClip(s,c), b=dustClip(s,vec3(0.0)); float len=max(max(a.y-a.x,0.0)*a.z,max(b.y-b.x,0.0)*b.z); if(len<=0.0) return vec2(0.0);
  float st=len/${f(DUST_NS)}, lev=clamp(floor(log2(st/${f(L[0].cell)})+0.5),0.0,3.0); return vec2(dustSum(lev,s,c,a,st),dustSum(lev,s,vec3(0.0),b,st)); }
`;
}
