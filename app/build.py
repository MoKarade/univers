#!/usr/bin/env python3
"""Assemble la page autonome dist/index.html à partir de app/src/ et app/gen/."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent

SRC_ORDER = [
    "20_physics.js", "21_nbody.js", "22_smallbody.js", "23_events.js",
    "24_moons.js", "25_future.js", "26_orbits.js", "27_lens.js",
    "28_dust.js", "29_cone.js", "30_gen.js", "40_render.js", "60_app.js",
]

GEN_ORDER = [
    "data.js", "data2.js", "ephem.js", "data3.js", "data4.js", "data5.js",
    "data6.js", "data7.js", "data8.js", "data9.js", "data10.js", "data11.js",
    "data12.js", "data13.js", "data14.js", "sun_rgb.js", "data15.js",
    "data16.js", "data17.js", "data18.js", "data19.js", "proton_pdf.js",
    "water_qm.js", "laniakea.js", "data20.js", "nbody.js", "transits.js",
    "mist_life.js", "lunes.js",
]


def read_text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def main() -> int:
    html = read_text("src/index.html")
    data_js = "".join(read_text(f"gen/{name}") for name in GEN_ORDER)
    app_js = "\n".join(read_text(f"src/{name}") for name in SRC_ORDER)
    out = html.replace("/*__DATA__*/", data_js).replace("/*__JS__*/", app_js)
    if "/*__DATA__*/" in out or "/*__JS__*/" in out:
        raise AssertionError("Marqueur /*__DATA__*/ ou /*__JS__*/ non remplacé")
    dst = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "dist" / "index.html"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(out, encoding="utf-8")
    print("écrit", dst, round(len(out.encode("utf-8")) / 1024), "ko")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
