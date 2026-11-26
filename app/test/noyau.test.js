/* Test de calcul « noyau » (mission 2, tâche R16) : répartition de charge de l'oxygène 16 mesurée par diffusion d'électrons
   (oscillateur harmonique de de Vries, de Jager et de Vries 1987), exécution réelle de initMicro (R.nucRms, 8p+8n, cœur dur)
   et rayon affiché dans la fiche. */
const { loadUnivers, readSrcConcat } = require('./_load');

function makeThreeMock() {
  class Vector3 {
    constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
    set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
    setScalar(s) { this.x = s; this.y = s; this.z = s; return this; }
    copy(v) { this.x = v.x; this.y = v.y; this.z = v.z; return this; }
    clone() { return new Vector3(this.x, this.y, this.z); }
    add(v) { this.x += v.x; this.y += v.y; this.z += v.z; return this; }
    cross(v) {
      const ax = this.x, ay = this.y, az = this.z;
      this.x = ay * v.z - az * v.y;
      this.y = az * v.x - ax * v.z;
      this.z = ax * v.y - ay * v.x;
      return this;
    }
    normalize() {
      const n = Math.hypot(this.x, this.y, this.z) || 1;
      this.x /= n; this.y /= n; this.z /= n;
      return this;
    }
    multiplyScalar(s) { this.x *= s; this.y *= s; this.z *= s; return this; }
    addScaledVector(v, s) { this.x += v.x * s; this.y += v.y * s; this.z += v.z * s; return this; }
    applyQuaternion(q) {
      const ix = q.w * this.x + q.y * this.z - q.z * this.y;
      const iy = q.w * this.y + q.z * this.x - q.x * this.z;
      const iz = q.w * this.z + q.x * this.y - q.y * this.x;
      const iw = -q.x * this.x - q.y * this.y - q.z * this.z;
      this.x = ix * q.w + iw * -q.x + iy * -q.z - iz * -q.y;
      this.y = iy * q.w + iw * -q.y + iz * -q.x - ix * -q.z;
      this.z = iz * q.w + iw * -q.z + ix * -q.y - iy * -q.x;
      return this;
    }
  }
  class Quaternion {
    constructor(x = 0, y = 0, z = 0, w = 1) { this.x = x; this.y = y; this.z = z; this.w = w; }
    setFromAxisAngle(ax, ang) {
      const h = ang * 0.5, s = Math.sin(h);
      this.x = ax.x * s; this.y = ax.y * s; this.z = ax.z * s; this.w = Math.cos(h);
      return this;
    }
    copy(q) { this.x = q.x; this.y = q.y; this.z = q.z; this.w = q.w; return this; }
    multiply(q) {
      const ax = this.x, ay = this.y, az = this.z, aw = this.w;
      this.x = ax * q.w + aw * q.x + ay * q.z - az * q.y;
      this.y = ay * q.w + aw * q.y + az * q.x - ax * q.z;
      this.z = az * q.w + aw * q.z + ax * q.y - ay * q.x;
      this.w = aw * q.w - ax * q.x - ay * q.y - az * q.z;
      return this;
    }
  }
  class Matrix4 {
    constructor() { this.px = 0; this.py = 0; this.pz = 0; }
    makeScale() { return this; }
    setPosition(x, y, z) { this.px = x; this.py = y; this.pz = z; return this; }
  }
  class Color {
    constructor(r = 0, g = 0, b = 0) { this.r = r; this.g = g; this.b = b; }
    setRGB(r, g, b) { this.r = r; this.g = g; this.b = b; return this; }
  }
  class Obj3D {
    constructor() {
      this.position = new Vector3();
      this.scale = new Vector3(1, 1, 1);
      this.quaternion = new Quaternion();
      this.visible = true;
      this.renderOrder = 0;
      this.frustumCulled = true;
    }
  }
  class Mesh extends Obj3D {
    constructor(geometry, material) { super(); this.geometry = geometry; this.material = material; }
  }
  class Points extends Obj3D {
    constructor(geometry, material) { super(); this.geometry = geometry; this.material = material; }
  }
  class Line extends Obj3D {
    constructor(geometry, material) { super(); this.geometry = geometry; this.material = material; }
  }
  class InstancedMesh extends Obj3D {
    constructor(geometry, material, count) {
      super();
      this.geometry = geometry;
      this.material = material;
      this.count = count;
      this.matrices = new Array(count);
      this.instanceMatrix = { setUsage() {}, needsUpdate: false };
      this.instanceColor = { needsUpdate: false };
    }
    setMatrixAt(i, m) { this.matrices[i] = [m.px, m.py, m.pz]; }
    setColorAt() {}
  }
  class BufferGeometry {
    constructor() { this.attributes = {}; }
    setAttribute(k, v) { this.attributes[k] = v; }
  }
  class BufferAttribute {
    constructor(array, itemSize) { this.array = array; this.itemSize = itemSize; this.needsUpdate = false; }
  }
  function Material(opts) {
    Object.assign(this, { opacity: 1 }, opts, { color: new Color() });
  }
  function ShaderMaterial(opts) {
    Object.assign(this, { uniforms: {} }, opts);
  }
  return {
    Vector3, Quaternion, Matrix4, Color, Mesh, Points, Line, InstancedMesh,
    BufferGeometry, BufferAttribute,
    SphereGeometry: function () {},
    CanvasTexture: function () { this.colorSpace = ''; },
    MeshBasicMaterial: Material,
    MeshMatcapMaterial: Material,
    ShaderMaterial,
    LineBasicMaterial: Material,
    BackSide: 1, AdditiveBlending: 2, DynamicDrawUsage: 35048, SRGBColorSpace: 'srgb',
  };
}

const doc = {
  createElement: () => ({
    width: 0,
    height: 0,
    getContext: () => ({
      createRadialGradient: () => ({ addColorStop() {} }),
      fillStyle: null,
      fillRect() {},
    }),
  }),
};

const U = loadUnivers({
  gen: ['data.js', 'data20.js', 'proton_pdf.js'],
  src: ['20_physics.js', '28_dust.js', '30_gen.js', '40_render.js'],
  globals: { document: doc },
});

const THREE = makeThreeMock();
const scene = { children: [], add(o) { this.children.push(o); } };
const camera = { position: new THREE.Vector3(0, 0, 1), quaternion: new THREE.Quaternion() };
const R = { dpr: 1 };
const M = U.initMicro(THREE, scene, camera, R, { oort: 0, dynN: 0 });

const renderSrc = readSrcConcat(['40_render.js']);
const allSrc = readSrcConcat();

let bad = 0;
const check = (ok, m) => {
  console.log((ok ? 'PASSE  ' : 'ÉCHEC  ') + m);
  if (!ok) bad++;
};

/* 1) Répartition de charge (oscillateur harmonique de Vries 1987) intégrée numériquement */
const mA = renderSrc.match(/\bNUC_A\s*=\s*([\d.]+)/);
const mAl = renderSrc.match(/\bNUC_AL\s*=\s*([\d.]+)/);
const a = mA ? +mA[1] : NaN;
const al = mAl ? +mAl[1] : NaN;
let num = 0;
let den = 0;
for (let r = 0; r < 20; r += 1e-3) {
  const w = r * r * (1 + al * r * r / (a * a)) * Math.exp(-r * r / (a * a));
  num += w * r * r;
  den += w;
}
const rms = Math.sqrt(num / den);
check(
  !!(mA && mAl) && Number.isFinite(rms) && Math.abs(rms - 2.6991) / 2.6991 < 0.01,
  `rayon de la répartition de charge : ${rms.toFixed(3)} fm (mesuré : 2,6991 fm, Angeli et Marinova 2013), écart ${(100 * (rms / 2.6991 - 1)).toFixed(1)} %`
);

/* 2) Exécution réelle de R.nucRms() contre la formule analytique avec neutron et Darwin-Foldy */
const rp = 0.84075;
const target = Math.sqrt(2.6991 ** 2 - rp ** 2 + 0.1161 - 0.0331);
const liveRms = typeof R.nucRms === 'function' ? R.nucRms() : NaN;
check(
  typeof R.nucRms === 'function' &&
  Number.isFinite(liveRms) &&
  Math.abs(liveRms - target) < 1e-6 &&
  Math.abs(target - 2.581) < 0.002,
  `rayon des centres de protons (R.nucRms) : ${liveRms.toFixed(6)} fm (cible ${target.toFixed(6)} fm, formule avec neutron et Darwin-Foldy)`
);

/* 3) Géométrie réelle des 16 nucléons (8 protons + 8 neutrons) et cœur dur (> 0,5 fm) */
M.update({ lrT: -14.5, sT: 1e15, wall: 0 });
const inst = scene.children.filter(o => o.renderOrder === 5040);
const p0 = scene.children.find(o => o.renderOrder === 5041);
const pM = inst[0];
const nM = inst[1];
const pts = [];
if (pM && nM && p0) {
  for (const q of pM.matrices) if (q) pts.push(q);
  for (const q of nM.matrices) if (q) pts.push(q);
  pts.push([
    p0.position.x - pM.position.x,
    p0.position.y - pM.position.y,
    p0.position.z - pM.position.z,
  ]);
}
let minSep = Infinity;
for (let i = 0; i < pts.length; i++) {
  for (let j = i + 1; j < pts.length; j++) {
    const d = Math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1], pts[i][2] - pts[j][2]);
    if (d < minSep) minSep = d;
  }
}
check(
  inst.length === 2 && pM.count === 7 && nM.count === 8 && !!p0 &&
  pts.length === 16 && pts.every(q => q.every(Number.isFinite)) &&
  Number.isFinite(minSep) && minSep > 0.5,
  `nucléons instanciés : ${pM ? pM.count + 1 : 0} protons + ${nM ? nM.count : 0} neutrons = ${pts.length}, séparation min ${minSep.toFixed(3)} fm (> 0,5 fm)`
);

/* 4) Fiche du noyau (résilient au formatage Prettier et au découpage 60..65) */
check(
  /\[\s*['"]Rayon de charge['"]\s*,\s*['"]2,70[\s\u00a0]fm/.test(allSrc),
  'fiche du noyau : rayon affiché 2,70 fm'
);

/* 5) Non-régression : ancien arrangement tétraédrique retiré */
check(
  !/\bTET\s*=\s*\[\s*\[\s*1\s*,\s*1\s*,\s*1\s*\]/.test(allSrc) &&
  !/quatre\s+groupes\s+de\s+2/i.test(allSrc),
  'arrangement en quatre groupes retiré'
);

if (bad) {
  console.log('noyau : ÉCHEC (' + bad + ')');
  process.exit(1);
} else {
  console.log('noyau : PASSE');
}
