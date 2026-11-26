/* Test de calcul « proton » (mission 2, tâche R15) : contenu du proton d'après les distributions de partons CT18NNLO,
   exécution réelle de initMicro / M.pdfAt(lam), et vérifications de source/licence résilientes au formatage. */
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
    makeScale() { return this; }
    setPosition() { return this; }
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
      this.instanceMatrix = { setUsage() {}, needsUpdate: false };
      this.instanceColor = { needsUpdate: false };
    }
    setMatrixAt() {}
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
const allSrc = readSrcConcat();

let bad = 0;
const check = (ok, m) => {
  console.log((ok ? 'PASSE  ' : 'ÉCHEC  ') + m);
  if (!ok) bad++;
};

const rows = U.DATA.PROTON_PDF.rows;
let ws = 0;
let wu = 0;
let wd = 0;
for (const r of rows) {
  const m = r.mom;
  const s = m.uv + m.dv + m.sea + m.g;
  ws = Math.max(ws, Math.abs(s - 1));
  wu = Math.max(wu, Math.abs(r.n.u - 2));
  wd = Math.max(wd, Math.abs(r.n.d - 1));
}
check(
  ws <= 0.01,
  `somme des parts d’impulsion = 1 à ${ws.toFixed(4)} près, sur ${rows.length} finesses (de ${rows[0].lam.toExponential(1)} à ${rows[rows.length - 1].lam.toExponential(1)} m)`
);
check(
  wu <= 0.02 && wd <= 0.02,
  `compte net : 2 up à ${wu.toFixed(4)} près, 1 down à ${wd.toFixed(4)} près`
);
check(
  rows[rows.length - 1].mom.g > rows[0].mom.g && rows[rows.length - 1].mom.sea > rows[0].mom.sea,
  `plus fin : gluons ${rows[0].mom.g.toFixed(3)} → ${rows[rows.length - 1].mom.g.toFixed(3)}, paires ${rows[0].mom.sea.toFixed(3)} → ${rows[rows.length - 1].mom.sea.toFixed(3)}`
);

/* 4) Exécution réelle de M.pdfAt(lam) : bornes grossier/fin et interpolation logarithmique intermédiaire */
const pCoarse = M.pdfAt(1e-14);
const pMid = M.pdfAt(1e-17);
const pFine = M.pdfAt(1e-22);
const midSum = pMid ? pMid.mom.uv + pMid.mom.dv + pMid.mom.sea + pMid.mom.g : NaN;
check(
  !!(pCoarse && pMid && pFine) &&
  pCoarse.clamp === 'grossier' &&
  pFine.clamp === 'fin' &&
  pMid.clamp === '' &&
  Number.isFinite(pMid.Q) && pMid.Q > 0 &&
  Math.abs(midSum - 1) <= 0.01 &&
  pMid.mom.g > pCoarse.mom.g && pMid.mom.g < pFine.mom.g,
  `M.pdfAt en exécution : grossier (g=${pCoarse ? pCoarse.mom.g.toFixed(3) : '—'}) < 1e-17 m (Q=${pMid ? pMid.Q.toFixed(1) : '—'} GeV, g=${pMid ? pMid.mom.g.toFixed(3) : '—'}, Σ=${midSum.toFixed(4)}) < fin (g=${pFine ? pFine.mom.g.toFixed(3) : '—'})`
);

/* 5) Source et licence (résilient au formatage Prettier et au découpage 60..65) */
check(
  /CT18NNLO\s*\(Hou et al\.\s*2021,\s*Phys\.\s*Rev\.\s*D\s*103,\s*014013\)/.test(allSrc) &&
  /['"]Licence des données['"]\s*,\s*['"][^'"]*CC BY 4\.0/.test(allSrc) &&
  /CC BY 4\.0/.test(U.DATA.PROTON_PDF.licence),
  'source et licence citées, identiques dans la fiche et dans les données'
);

/* 6) Non-régression : anciens tubes de gluons retirés */
check(
  !/\b(?:tubeG|NSEA)\b|tubes de gluons/i.test(allSrc),
  'tubes de gluons et paires dessinés à la main retirés'
);

if (bad) {
  console.log('proton : ÉCHEC (' + bad + ')');
  process.exit(1);
} else {
  console.log('proton : PASSE');
}
