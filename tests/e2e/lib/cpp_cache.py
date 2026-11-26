"""Session-scoped /tmp C++20 build cache (CMake GCC/Clang, direct binaries, ASan/UBSan probes, parity driver).

All compilation outputs live strictly inside TempWorkspace (<tmpdir>/cpp/) and are
never written inside the repository. Compile failures return structured BuildArtifact
objects (never crashing the test harness with unhandled exceptions).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .harness import NATIF_DIR, TempWorkspace, run_cmd


@dataclass
class BuildArtifact:
    ok: bool
    rc: int
    stdout: str
    stderr: str
    build_dir: Path
    binaries: Dict[str, Path] = field(default_factory=dict)
    compiler: str = "g++"
    note: str = ""


_ASAN_PROBE_SRC = r"""
#include <cmath>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#include "cosmologie.h"
#include "groupe_local.h"
#include "interface_outils.h"
#include "nbody_noyau.h"

static int mode_longtable(const char* path) {
    phys::nb::LongTable lt;
    const bool ok = lt.load(path);
    std::printf("{\"ok\":%s,\"loaded\":%s}\n", ok ? "true" : "false", lt.loaded() ? "true" : "false");
    return 0;
}

static int mode_rejeu(const char* centres, const char* dir) {
    phys::fusion::Rejeu r;
    const bool ok = r.charger(centres, dir);
    std::printf("{\"ok\":%s,\"n_stars\":%d}\n", ok ? "true" : "false", r.nombreEtoiles());
    return 0;
}

static int mode_rejeu_rt(const char* centres, const char* dir) {
    phys::fusion::Rejeu r;
    if (!r.charger(centres, dir)) {
        std::printf("{\"ok\":false}\n");
        return 0;
    }
    phys::Vec3 m31_0{}, lmc_0{}, m31_mid{}, oob_lo{}, oob_hi{};
    const bool ok0 = r.centre(phys::fusion::kAndromede, 0.0, m31_0);
    const bool ok_lmc = r.centre(phys::fusion::kGrandNuage, 0.0, lmc_0);
    const bool ok_mid = r.centre(phys::fusion::kAndromede, 0.01, m31_mid);
    const bool bad_lo = r.centre(phys::fusion::kAndromede, -0.05, oob_lo);
    const bool bad_hi = r.centre(phys::fusion::kAndromede, r.finGa() + 0.05, oob_hi);
    std::vector<phys::Vec3> stars(static_cast<size_t>(r.nombreEtoiles()));
    const bool ok_st = r.etoilesA(0.01, stars);
    const double s0x = (!stars.empty() ? stars[0].x : 0.0);
    std::printf(
        "{\"ok\":true,\"fusionGa\":%.6f,\"finGa\":%.6f,\"ok0\":%s,\"ok_lmc\":%s,\"ok_mid\":%s,"
        "\"bad_lo\":%s,\"bad_hi\":%s,\"ok_st\":%s,"
        "\"m31_0\":[%.6f,%.6f,%.6f],\"lmc_0\":[%.6f,%.6f,%.6f],\"m31_mid\":[%.6f,%.6f,%.6f],"
        "\"s0x\":%.6f,\"n_stars\":%d}\n",
        r.fusionGa(), r.finGa(),
        ok0 ? "true" : "false", ok_lmc ? "true" : "false", ok_mid ? "true" : "false",
        bad_lo ? "true" : "false", bad_hi ? "true" : "false", ok_st ? "true" : "false",
        m31_0.x, m31_0.y, m31_0.z,
        lmc_0.x, lmc_0.y, lmc_0.z,
        m31_mid.x, m31_mid.y, m31_mid.z,
        s0x, r.nombreEtoiles());
    return 0;
}

static int mode_cosmo() {
    auto test_param = [](const char* name, cosmo::Params p) {
        const double age = cosmo::ageGyr(p);
        const double ts[3] = {-age, -age - 1.0, -20.0};
        bool all_ok = std::isfinite(age) && age > 0.0;
        double vals[3] = {};
        for (int i = 0; i < 3; ++i) {
            vals[i] = cosmo::scaleFactorAt(p, ts[i]);
            if (!std::isfinite(vals[i]) || vals[i] < 0.0) all_ok = false;
        }
        std::printf(
            "{\"case\":\"%s\",\"age\":%.6f,\"all_ok\":%s,\"a0_fin\":%s,\"a1_fin\":%s,\"a2_fin\":%s,"
            "\"a0\":%.6g,\"a1\":%.6g,\"a2\":%.6g}",
            name, age, all_ok ? "true" : "false",
            std::isfinite(vals[0]) ? "true" : "false",
            std::isfinite(vals[1]) ? "true" : "false",
            std::isfinite(vals[2]) ? "true" : "false",
            std::isfinite(vals[0]) ? vals[0] : -999.0,
            std::isfinite(vals[1]) ? vals[1] : -999.0,
            std::isfinite(vals[2]) ? vals[2] : -999.0);
    };
    cosmo::Params p1;
    cosmo::Params p2; p2.w0 = -0.9;
    cosmo::Params p3; p3.w0 = -0.8; p3.wa = 0.5;
    std::printf("{\"cases\":[");
    test_param("planck", p1); std::printf(",");
    test_param("w0_-0.9", p2); std::printf(",");
    test_param("w0_-0.8_wa_0.5", p3);
    // Test distanceTable edge cases: steps=0, zMax=0
    const auto dt0 = cosmo::distanceTable(p1, 0.0, 10);
    bool dt0_ok = !dt0.empty();
    for (double v : dt0) if (!std::isfinite(v) || v < 0.0) dt0_ok = false;
    const auto dts0 = cosmo::distanceTable(p1, 1.0, 0);
    bool dts0_ok = !dts0.empty();
    for (double v : dts0) if (!std::isfinite(v) || v < 0.0) dts0_ok = false;
    std::printf("],\"dt_z0_ok\":%s,\"dt_steps0_ok\":%s}\n",
                dt0_ok ? "true" : "false", dts0_ok ? "true" : "false");
    return 0;
}

static std::string json_escape(const std::string& s) {
    std::string o;
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') { o += '\\'; o += static_cast<char>(c); }
        else if (c < 0x20 || c >= 0x80) { char buf[8]; std::snprintf(buf, sizeof(buf), "\\u%04x", c); o += buf; }
        else o += static_cast<char>(c);
    }
    return o;
}

static int mode_interface() {
    const std::string f_yd = ui_outils::fold("\xC3\xBF");       // ÿ
    const std::string f_oe = ui_outils::fold("\xC5\x93");       // œ
    const std::string f_OE = ui_outils::fold("\xC5\x92");       // Œ
    const std::string f_ss = ui_outils::fold("\xC3\x9F");       // ß
    double y1 = 0, y2 = 0, y3 = 0, y4 = 0, y5 = 0;
    const bool p_over = ui_outils::parseDate("99999999999999999999", y1);
    const bool p_min = ui_outils::parseDate("-9223372036854775808", y2);
    const bool p_feb29 = ui_outils::parseDate("29/02/2021", y3);
    const bool p_apr31 = ui_outils::parseDate("31/04/2020", y4);
    const bool p_leap = ui_outils::parseDate("29/02/2024", y5);
    std::printf(
        "{\"fold_yd\":\"%s\",\"fold_oe\":\"%s\",\"fold_OE\":\"%s\",\"fold_ss\":\"%s\","
        "\"parse_over\":%s,\"parse_llmin\":%s,\"parse_feb29_2021\":%s,\"parse_apr31_2020\":%s,\"parse_leap_2024\":%s}\n",
        json_escape(f_yd).c_str(), json_escape(f_oe).c_str(), json_escape(f_OE).c_str(), json_escape(f_ss).c_str(),
        p_over ? "true" : "false", p_min ? "true" : "false",
        p_feb29 ? "true" : "false", p_apr31 ? "true" : "false", p_leap ? "true" : "false");
    return 0;
}

int main(int argc, char** argv) {
    if (argc < 3 || std::strcmp(argv[1], "--mode") != 0) return 2;
    const std::string m = argv[2];
    if (m == "longtable" && argc >= 4) return mode_longtable(argv[3]);
    if (m == "rejeu" && argc >= 5) return mode_rejeu(argv[3], argv[4]);
    if (m == "rejeu_rt" && argc >= 5) return mode_rejeu_rt(argv[3], argv[4]);
    if (m == "cosmo") return mode_cosmo();
    if (m == "interface") return mode_interface();
    return 2;
}
"""

_SPK_PROBE_SRC = r"""
#include <cstdio>
#include <string>
#include "ephemeride.h"

int main(int argc, char** argv) {
    if (argc < 2) return 2;
    eph::Spk spk;
    std::string err;
    const bool ok = spk.open(argv[1], err);
    std::printf("{\"ok\":%s}\n", ok ? "true" : "false");
    return 0;
}
"""

_PARITY_DRIVER_SRC = r"""
#include <cmath>
#include <cstdio>
#include <vector>

#include "cosmologie.h"
#include "galaxie_orbites.h"
#include "nbody_noyau.h"

int main() {
    // 1. Galactic orbit: Sun +200 Ma (bar ON & OFF)
    const phys::Vec3 sp[1] = {phys::galaxie::soleilPos()};
    const phys::Vec3 sv[1] = {phys::galaxie::soleilVit()};
    phys::galaxie::Orbites o_on(sp, sv);
    o_on.avance(0.2);
    const auto p_on = o_on.position(0);

    phys::galaxie::Potentiel pot_off;
    pot_off.barre = false;
    phys::galaxie::Orbites o_off(sp, sv, pot_off);
    o_off.avance(0.2);
    const auto p_off = o_off.position(0);

    // 2. Planck 2018 cosmology: ageGyr + d_M(z) at z = [0.1, 0.5, 1.0, 2.0, 3.0]
    cosmo::Params par;
    const double age = cosmo::ageGyr(par);
    const double zs[5] = {0.1, 0.5, 1.0, 2.0, 3.0};
    double dms[5] = {};
    for (int i = 0; i < 5; ++i) {
        const auto tab = cosmo::distanceTable(par, zs[i], 256);
        dms[i] = tab.back();
    }

    // 3. 13-body N-body at J2000 (JD 2451544.5): heliocentric Mercury (i=0) & Jupiter (i=4) in km
    phys::nb::Integrator it;
    it.advanceTo(2451544.5);
    double b[42];
    it.barycentric(b);
    const double au_km = 149597870.7;
    double merc[3], jup[3];
    for (int c = 0; c < 3; ++c) {
        merc[c] = (b[3 * 1 + c] - b[c]) * au_km;
        jup[c]  = (b[3 * 5 + c] - b[c]) * au_km;
    }

    std::printf(
        "{\"sun_on\":[%.12f,%.12f,%.12f],\"sun_off\":[%.12f,%.12f,%.12f],"
        "\"age\":%.10f,\"dm\":[%.8f,%.8f,%.8f,%.8f,%.8f],"
        "\"merc_km\":[%.6f,%.6f,%.6f],\"jup_km\":[%.6f,%.6f,%.6f]}\n",
        p_on.x, p_on.y, p_on.z,
        p_off.x, p_off.y, p_off.z,
        age, dms[0], dms[1], dms[2], dms[3], dms[4],
        merc[0], merc[1], merc[2],
        jup[0], jup[1], jup[2]);
    return 0;
}
"""


class CppCache:
    """Session-scoped lazy C++20 compiler/CMake cache inside TempWorkspace."""

    def __init__(self, workspace: TempWorkspace) -> None:
        self.workspace = workspace
        self.root = workspace.subdir("cpp")
        self._cmake_phys_gcc: Optional[BuildArtifact] = None
        self._cmake_phys_clang: Optional[BuildArtifact] = None
        self._cmake_natif_gcc: Optional[BuildArtifact] = None
        self._direct: Dict[str, BuildArtifact] = {}
        self._asan_probe: Optional[BuildArtifact] = None
        self._spk_probe: Optional[BuildArtifact] = None
        self._parity_driver: Optional[BuildArtifact] = None

    def _run_cmake_build(
        self,
        src_dir: Path,
        build_subdir: str,
        compiler: str,
        targets: Sequence[str],
        extra_cmake_args: Sequence[str] = (),
        werror: bool = True,
    ) -> BuildArtifact:
        bdir = self.root / build_subdir
        bdir.mkdir(parents=True, exist_ok=True)
        cxx_flags = "-Wall -Wextra -Wpedantic -Wshadow -Werror" if werror else "-Wall -Wextra"
        cfg_cmd = [
            "cmake",
            "-G",
            "Ninja",
            "-S",
            str(src_dir),
            "-B",
            str(bdir),
            f"-DCMAKE_CXX_COMPILER={compiler}",
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_CXX_FLAGS={cxx_flags}",
            *extra_cmake_args,
        ]
        cfg = run_cmd(cfg_cmd, timeout=45.0)
        if cfg.timed_out or cfg.rc != 0:
            return BuildArtifact(
                ok=False,
                rc=cfg.rc,
                stdout=cfg.stdout,
                stderr=cfg.stderr,
                build_dir=bdir,
                compiler=compiler,
                note="cmake configure failed",
            )
        bld_cmd = ["cmake", "--build", str(bdir), "-j", str(max(1, (Path("/proc/cpuinfo").read_text().count("processor") if Path("/proc/cpuinfo").is_file() else 2)))]
        if targets:
            bld_cmd.extend(["--target", *targets])
        bld = run_cmd(bld_cmd, timeout=90.0)
        bins: Dict[str, Path] = {}
        for t in targets:
            for cand in (bdir / t, bdir / "physique" / t, bdir / f"lib{t}.a"):
                if cand.is_file():
                    bins[t] = cand
                    break
        return BuildArtifact(
            ok=(not bld.timed_out and bld.rc == 0),
            rc=bld.rc,
            stdout=cfg.stdout + "\n" + bld.stdout,
            stderr=cfg.stderr + "\n" + bld.stderr,
            build_dir=bdir,
            binaries=bins,
            compiler=compiler,
            note="ok" if (not bld.timed_out and bld.rc == 0) else "cmake build failed",
        )

    def build_cmake_phys_gcc(self) -> BuildArtifact:
        if self._cmake_phys_gcc is None:
            self._cmake_phys_gcc = self._run_cmake_build(
                NATIF_DIR / "physique",
                "gcc_phys",
                "g++",
                targets=("univers_physique", "essai_galaxie", "essai_fusion", "essai_systeme_solaire"),
                werror=True,
            )
        return self._cmake_phys_gcc

    def build_cmake_phys_clang(self) -> BuildArtifact:
        if self._cmake_phys_clang is None:
            self._cmake_phys_clang = self._run_cmake_build(
                NATIF_DIR / "physique",
                "clang_phys",
                "clang++",
                targets=("univers_physique", "essai_galaxie", "essai_fusion", "essai_systeme_solaire"),
                werror=True,
            )
        return self._cmake_phys_clang

    def build_cmake_natif_gcc(self) -> BuildArtifact:
        if self._cmake_natif_gcc is None:
            self._cmake_natif_gcc = self._run_cmake_build(
                NATIF_DIR,
                "gcc_natif",
                "g++",
                targets=("essai_cosmologie", "essai_interface", "essai_ephem", "essai_orientation"),
                werror=True,
            )
        return self._cmake_natif_gcc

    def get_binary(self, name: str, compiler: str = "g++", allow_direct_fallback: bool = True) -> BuildArtifact:
        """Return a compiled executable (from CMake cache if available, else optional direct compile)."""
        if compiler == "g++":
            if name in ("essai_galaxie", "essai_fusion", "essai_systeme_solaire"):
                art = self.build_cmake_phys_gcc()
                if art.ok and name in art.binaries:
                    return art
            if name in ("essai_cosmologie", "essai_interface", "essai_ephem", "essai_orientation"):
                art = self.build_cmake_natif_gcc()
                if art.ok and name in art.binaries:
                    return art
        elif compiler == "clang++":
            if name in ("essai_galaxie", "essai_fusion", "essai_systeme_solaire"):
                art = self.build_cmake_phys_clang()
                if art.ok and name in art.binaries:
                    return art

        if not allow_direct_fallback:
            return BuildArtifact(ok=False, rc=1, stdout="", stderr="CMake build unavailable", build_dir=self.root, compiler=compiler)

        cache_key = f"{compiler}:{name}"
        if cache_key in self._direct:
            return self._direct[cache_key]

        ddir = self.root / f"direct_{compiler.replace('+', 'p')}"
        ddir.mkdir(parents=True, exist_ok=True)
        out_bin = ddir / name

        sources: List[str]
        includes = [f"-I{NATIF_DIR / 'physique'}", f"-I{NATIF_DIR / 'src'}"]
        if name == "essai_cosmologie":
            sources = [str(NATIF_DIR / "src" / "essai_cosmologie.cpp")]
        elif name == "essai_interface":
            sources = [str(NATIF_DIR / "src" / "essai_interface.cpp")]
        elif name == "essai_ephem":
            sources = [str(NATIF_DIR / "src" / "essai_ephem.cpp")]
        elif name == "essai_orientation":
            sources = [str(NATIF_DIR / "src" / "essai_orientation.cpp")]
        elif name == "essai_galaxie":
            sources = [str(NATIF_DIR / "physique" / "essais" / "essai_galaxie.cpp")]
        elif name == "essai_fusion":
            sources = [str(NATIF_DIR / "physique" / "essais" / "essai_fusion.cpp")]
        elif name == "essai_systeme_solaire":
            sources = [
                str(NATIF_DIR / "physique" / "essais" / "essai_systeme_solaire.cpp"),
                str(NATIF_DIR / "physique" / "systeme_solaire.cpp"),
            ]
        else:
            raise ValueError(f"Unknown native binary: {name}")

        cmd = [compiler, "-std=c++20", "-O2", "-pthread", *includes, *sources, "-o", str(out_bin)]
        res = run_cmd(cmd, timeout=45.0)
        art = BuildArtifact(
            ok=(not res.timed_out and res.rc == 0 and out_bin.is_file()),
            rc=res.rc,
            stdout=res.stdout,
            stderr=res.stderr,
            build_dir=ddir,
            binaries={name: out_bin} if out_bin.is_file() else {},
            compiler=compiler,
            note="direct fallback",
        )
        self._direct[cache_key] = art
        return art

    def build_asan_probe(self) -> BuildArtifact:
        if self._asan_probe is not None:
            return self._asan_probe
        pdir = self.root / "asan_probes"
        pdir.mkdir(parents=True, exist_ok=True)
        src = pdir / "asan_probe.cpp"
        out_bin = pdir / "asan_probe"
        src.write_text(_ASAN_PROBE_SRC, encoding="utf-8")
        cmd = [
            "g++",
            "-std=c++20",
            "-O1",
            "-g",
            "-fsanitize=address,undefined",
            "-fno-omit-frame-pointer",
            f"-I{NATIF_DIR / 'physique'}",
            f"-I{NATIF_DIR / 'src'}",
            str(src),
            "-o",
            str(out_bin),
        ]
        res = run_cmd(cmd, timeout=45.0)
        self._asan_probe = BuildArtifact(
            ok=(not res.timed_out and res.rc == 0 and out_bin.is_file()),
            rc=res.rc,
            stdout=res.stdout,
            stderr=res.stderr,
            build_dir=pdir,
            binaries={"asan_probe": out_bin} if out_bin.is_file() else {},
            compiler="g++",
            note="asan_probe",
        )
        return self._asan_probe

    def build_spk_probe(self) -> BuildArtifact:
        if self._spk_probe is not None:
            return self._spk_probe
        pdir = self.root / "asan_probes"
        pdir.mkdir(parents=True, exist_ok=True)
        src = pdir / "spk_probe.cpp"
        out_bin = pdir / "spk_probe"
        src.write_text(_SPK_PROBE_SRC, encoding="utf-8")
        cmd = [
            "g++",
            "-std=c++20",
            "-O1",
            "-g",
            "-fsanitize=address,undefined",
            "-fno-omit-frame-pointer",
            f"-I{NATIF_DIR / 'src'}",
            str(src),
            "-o",
            str(out_bin),
        ]
        res = run_cmd(cmd, timeout=45.0)
        self._spk_probe = BuildArtifact(
            ok=(not res.timed_out and res.rc == 0 and out_bin.is_file()),
            rc=res.rc,
            stdout=res.stdout,
            stderr=res.stderr,
            build_dir=pdir,
            binaries={"spk_probe": out_bin} if out_bin.is_file() else {},
            compiler="g++",
            note="spk_probe",
        )
        return self._spk_probe

    def build_parity_driver(self) -> BuildArtifact:
        if self._parity_driver is not None:
            return self._parity_driver
        pdir = self.root / "parity"
        pdir.mkdir(parents=True, exist_ok=True)
        src = pdir / "parity_driver.cpp"
        out_bin = pdir / "parity_driver"
        src.write_text(_PARITY_DRIVER_SRC, encoding="utf-8")
        cmd = [
            "g++",
            "-std=c++20",
            "-O2",
            "-pthread",
            f"-I{NATIF_DIR / 'physique'}",
            f"-I{NATIF_DIR / 'src'}",
            str(src),
            "-o",
            str(out_bin),
        ]
        res = run_cmd(cmd, timeout=45.0)
        self._parity_driver = BuildArtifact(
            ok=(not res.timed_out and res.rc == 0 and out_bin.is_file()),
            rc=res.rc,
            stdout=res.stdout,
            stderr=res.stderr,
            build_dir=pdir,
            binaries={"parity_driver": out_bin} if out_bin.is_file() else {},
            compiler="g++",
            note="parity_driver",
        )
        return self._parity_driver
