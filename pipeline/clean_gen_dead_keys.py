#!/usr/bin/env python3
"""Élagage reproductible des clés écrasées/mortes dans app/gen/ (Jalon M3).

Vérifie avant et après élagage via Node.js que l'objet DATA final produit par
l'évaluation de tous les fichiers app/gen/*.js dans l'ordre de app/build.py est
strictement identique (égalité profonde JSON canonique).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
APP_GEN = REPO_ROOT / "app" / "gen"

GEN_ORDER = [
    "data.js", "data2.js", "ephem.js", "data3.js", "data4.js", "data5.js",
    "data6.js", "data7.js", "data8.js", "data9.js", "data10.js", "data11.js",
    "data12.js", "data13.js", "data14.js", "sun_rgb.js", "data15.js",
    "data16.js", "data17.js", "data18.js", "data19.js", "proton_pdf.js",
    "water_qm.js", "laniakea.js", "data20.js", "nbody.js", "transits.js",
    "mist_life.js", "lunes.js",
]

# Clés écrasées plus tard dans GEN_ORDER (ou supprimées auparavant par app/build.py)
PRUNE_TOP = {
    "data.js": ["LOCAL", "STAR_LABELS", "STARS_N", "STARS_AUX"],
    "data2.js": ["STARS_GEO", "STARS_AUX", "STAR_LABELS", "STARS_N", "CMB"],
    "data4.js": ["EXO_POS", "EXO_NAMES", "EXO_NP", "EXO_N", "EXO_SRC"],
    "data5.js": ["EXO_PL"],
    "data6.js": ["EXO_PL", "EXO_ST", "EXO_METH", "MOONS"],
}
PRUNE_SUB = {
    "data.js": {"TEX": ["moon", "mars", "mercury"]},
}


def eval_data_hash(strip_data2_like_legacy_build: bool = False) -> str:
    node_code = r"""
const fs = require('fs'), vm = require('vm'), path = require('path'), crypto = require('crypto');
const genDir = process.argv[1];
const order = JSON.parse(process.argv[2]);
const legacy = process.argv[3] === '1';
const ctx = vm.createContext({});
for (const name of order) {
  let src = fs.readFileSync(path.join(genDir, name), 'utf8');
  if (legacy && name === 'data2.js') {
    const o = JSON.parse(src.slice('Object.assign(DATA, '.length, src.lastIndexOf(');')));
    for (const k of ['STARS_GEO', 'STARS_AUX', 'STAR_LABELS', 'STARS_N', 'CMB']) delete o[k];
    src = 'Object.assign(DATA, ' + JSON.stringify(o) + ');\n';
  }
  vm.runInContext(src, ctx, { filename: name });
}
const canon = v => {
  if (v === null || typeof v !== 'object') return v;
  if (Array.isArray(v)) return v.map(canon);
  const out = {};
  for (const k of Object.keys(v).sort()) out[k] = canon(v[k]);
  return out;
};
const dataObj = vm.runInContext('DATA', ctx);
const h = crypto.createHash('sha256').update(JSON.stringify(canon(dataObj))).digest('hex');
console.log(h);
"""
    res = subprocess.run(
        ["node", "-e", node_code, str(APP_GEN), json.dumps(GEN_ORDER), "1" if strip_data2_like_legacy_build else "0"],
        capture_output=True, text=True, check=True,
    )
    return res.stdout.strip()


def prune_file(name: str, top_keys: list[str], sub_keys: dict[str, list[str]]) -> int:
    path = APP_GEN / name
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("const DATA = ") and raw.rstrip().endswith(";"):
        prefix, suffix = "const DATA = ", ";\n"
        body = raw[len(prefix):raw.rindex(";")]
    elif raw.startswith("Object.assign(DATA, ") and raw.rstrip().endswith(");"):
        prefix, suffix = "Object.assign(DATA, ", ");\n"
        body = raw[len(prefix):raw.rindex(");")]
    else:
        raise ValueError(f"Format inattendu dans {name}")

    obj = json.loads(body)
    removed = 0
    for k in top_keys:
        if k in obj:
            obj.pop(k)
            removed += 1
    for parent, children in sub_keys.items():
        if isinstance(obj.get(parent), dict):
            for ck in children:
                if ck in obj[parent]:
                    obj[parent].pop(ck)
                    removed += 1

    if removed > 0:
        out = prefix + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + suffix
        saved = len(raw.encode("utf-8")) - len(out.encode("utf-8"))
        path.write_text(out, encoding="utf-8")
        print(f"élagué {name} : {removed} clé(s), -{saved / 1024:.1f} ko")
        return saved
    print(f"inchangé {name}")
    return 0


def main() -> int:
    before = eval_data_hash(strip_data2_like_legacy_build=True)
    total_saved = 0
    for name in sorted(set(PRUNE_TOP) | set(PRUNE_SUB)):
        total_saved += prune_file(name, PRUNE_TOP.get(name, []), PRUNE_SUB.get(name, {}))
    after = eval_data_hash(strip_data2_like_legacy_build=False)
    if before != after:
        print(f"ÉCHEC : empreinte DATA modifiée ({before} != {after})", file=sys.stderr)
        return 1
    print(f"OK : empreinte DATA strictement identique ({after[:16]}…), gain total {total_saved / 1024:.1f} ko")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
