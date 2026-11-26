"""Tier 2 — F5: Native C++20 Error Handling, ASan/UBSan Memory Safety, Shaders & Header Invariants (7 tests)."""
from __future__ import annotations

import json
from pathlib import Path
import re
import struct
from typing import List, Tuple

from lib.harness import (
    NATIF_DIR,
    E2ESession,
    TestCase,
    check,
    run_cmd,
)


def t2_f5_01_essai_fusion_malformed_cli_no_crash(session: E2ESession) -> Tuple[str, dict]:
    art = session.cpp.get_binary("essai_fusion", compiler="g++", allow_direct_fallback=True)
    check(art.ok and "essai_fusion" in art.binaries, f"Could not build essai_fusion: {art.stderr[:300]}")
    exe = str(art.binaries["essai_fusion"])
    tmp = session.workspace.subdir("t2_f5_01")
    empty_bin = tmp / "empty.bin"
    empty_bin.write_bytes(b"")
    trunc_bin = tmp / "trunc64.bin"
    trunc_bin.write_bytes(b"\x00" * 64)

    issues: List[str] = []
    # (a) No args -> exit 2 + usage
    r_no = run_cmd([exe], timeout=10.0)
    if r_no.rc != 2 or "usage" not in (r_no.stderr + r_no.stdout).lower():
        issues.append(f"no-args expected rc=2 + usage, got rc={r_no.rc}")

    # (b)-(d) Missing, 0-byte, truncated 64-byte -> clean exit 1, NEVER SIGSEGV (139 or -11)
    for label, path in (
        ("missing", str(tmp / "does_not_exist.bin")),
        ("0-byte", str(empty_bin)),
        ("trunc-64B", str(trunc_bin)),
    ):
        r = run_cmd([exe, path, str(tmp)], timeout=10.0)
        if r.rc < 0 or r.rc >= 128:
            issues.append(f"essai_fusion CRASHED with signal/exit {r.rc} on {label} input (CPP-BUG)")
        elif r.rc == 0:
            issues.append(f"essai_fusion returned 0 on malformed {label} input")

    check(not issues, "; ".join(issues))
    return "essai_fusion handles missing, 0-byte & truncated inputs cleanly with non-zero exit (0 crashes)", {}


def t2_f5_02_ephem_cli_corrupt_files(session: E2ESession) -> Tuple[str, dict]:
    tmp = session.workspace.subdir("t2_f5_02")
    empty_bsp = tmp / "empty.bsp"
    empty_bsp.write_bytes(b"")
    garb_bsp = tmp / "garbage.bsp"
    garb_bsp.write_bytes(b"NOT_A_VALID_SPK_FILE" * 60)

    issues: List[str] = []
    for bin_name in ("essai_systeme_solaire", "essai_ephem", "essai_orientation"):
        art = session.cpp.get_binary(bin_name, compiler="g++", allow_direct_fallback=True)
        if not (art.ok and bin_name in art.binaries):
            issues.append(f"{bin_name} failed to compile on Linux (windows.h in ephemeride.h?): {art.stderr.strip().splitlines()[-1] if art.stderr.strip() else 'compile error'}")
            continue
        exe = str(art.binaries[bin_name])
        for label, path in (("missing", str(tmp / "nope.bsp")), ("0-byte", str(empty_bsp)), ("garbage", str(garb_bsp))):
            r = run_cmd([exe, path], timeout=10.0)
            if r.rc < 0 or r.rc >= 128:
                issues.append(f"{bin_name} crashed (rc={r.rc}) on {label} .bsp")
            elif r.rc == 0:
                issues.append(f"{bin_name} exited 0 on corrupt {label} .bsp")

    check(not issues, "; ".join(issues[:6]), {"issues": issues})
    return "essai_systeme_solaire, essai_ephem & essai_orientation reject missing/0-byte/corrupt .bsp cleanly", {}


def t2_f5_03_binary_loaders_asan_ubsan(session: E2ESession) -> Tuple[str, dict]:
    tmp = session.workspace.subdir("t2_f5_03")
    issues: List[str] = []

    art = session.cpp.build_asan_probe()
    check(art.ok and "asan_probe" in art.binaries, f"Failed to compile ASan probe: {art.stderr[:350]}")
    exe = str(art.binaries["asan_probe"])

    # 1. LongTable::load crafted truncated & hostile headers
    lt_trunc = tmp / "lt_trunc.bin"
    # Header: version=2, jd0=2451545, dd=365250, nP=10, nF=10, nk=9, sl=10 -> expects > 756 B payload, only 56 B present!
    lt_trunc.write_bytes(struct.pack("<7d", 2.0, 2451545.0, 365250.0, 10.0, 10.0, 9.0, 10.0))
    lt_neg = tmp / "lt_neg.bin"
    lt_neg.write_bytes(struct.pack("<7d", 2.0, 2451545.0, 365250.0, -5.0, 10.0, 9.0, 0.0))
    for label, p in (("LongTable truncated 56B", lt_trunc), ("LongTable neg/sl=0", lt_neg)):
        r = run_cmd([exe, "--mode", "longtable", str(p)], timeout=10.0)
        if r.timed_out or r.rc != 0 or "AddressSanitizer" in r.stderr or "runtime error:" in r.stderr:
            issues.append(f"{label} triggered ASan/UBSan/crash (rc={r.rc}): {(r.stderr or '')[:220]}")
        else:
            parsed = json.loads(r.stdout.strip().splitlines()[-1])
            if parsed.get("ok") is not False:
                issues.append(f"{label} unexpectedly returned ok=true")

    # 2. Rejeu::charger crafted truncated nf table & path traversal
    rj_trunc = tmp / "rj_trunc.bin"
    # 12 doubles header: version=1, n=2, dt=0.02, 4, T=1, q=0.025, fusion=5.44, derive=0.001, nGal=[2,2,0,0]
    hdr = struct.pack("<12d", 1, 2, 0.02, 4, 1, 0.025, 5.44, 0.001, 2, 2, 0, 0)
    centres = struct.pack("<24d", *([0.0] * 24))  # 2 * 12
    traceurs = struct.pack("<6d", *([0.0] * 6))   # 2 * 1 * 3
    nf_and_partial = struct.pack("<d", 1.0) + b"kf_000.bin"  # truncated: only 10 bytes instead of 24!
    rj_trunc.write_bytes(hdr + centres + traceurs + nf_and_partial)
    r_rj = run_cmd([exe, "--mode", "rejeu", str(rj_trunc), str(tmp)], timeout=10.0)
    if r_rj.timed_out or r_rj.rc != 0 or "AddressSanitizer" in r_rj.stderr or "runtime error:" in r_rj.stderr:
        issues.append(f"Rejeu truncated nf triggered ASan/UBSan/crash (rc={r_rj.rc}): {(r_rj.stderr or '')[:220]}")
    else:
        parsed = json.loads(r_rj.stdout.strip().splitlines()[-1])
        if parsed.get("ok") is not False:
            issues.append("Rejeu truncated nf unexpectedly returned ok=true")

    # 2b. Rejeu path traversal filename "../escape.bin"
    rj_trav = tmp / "rj_trav.bin"
    bad_entry = b"../escape.bin".ljust(16, b"\0") + struct.pack("<d", 2.0)
    rj_trav.write_bytes(hdr + centres + traceurs + struct.pack("<d", 1.0) + bad_entry)
    r_tr = run_cmd([exe, "--mode", "rejeu", str(rj_trav), str(tmp)], timeout=10.0)
    if r_tr.timed_out or r_tr.rc != 0 or "AddressSanitizer" in r_tr.stderr or "runtime error:" in r_tr.stderr:
        issues.append(f"Rejeu path traversal triggered ASan/UBSan/crash (rc={r_tr.rc})")
    else:
        parsed = json.loads(r_tr.stdout.strip().splitlines()[-1])
        if parsed.get("ok") is not False:
            issues.append("Rejeu path traversal unexpectedly returned ok=true")

    # 3. Spk::open ASan/UBSan probes (cyclic summary record & count=100 overflow)
    spk_art = session.cpp.build_spk_probe()
    if not (spk_art.ok and "spk_probe" in spk_art.binaries):
        issues.append("ephemeride.h Spk::open failed Linux ASan compilation (still includes <windows.h>?)")
    else:
        spk_exe = str(spk_art.binaries["spk_probe"])
        # Cyclic fward=2 -> rec2.next=2 (infinite loop without cycle guard!)
        spk_cyc = tmp / "spk_cyclic.bsp"
        buf = bytearray(2048)
        buf[0:7] = b"DAF/SPK"
        struct.pack_into("<ii", buf, 8, 2, 6)
        struct.pack_into("<i", buf, 76, 2)
        buf[88:96] = b"LTL-IEEE"
        struct.pack_into("<ddd", buf, 1024, 2.0, 0.0, 0.0)  # rec 2 points to itself!
        spk_cyc.write_bytes(buf)
        r_cyc = run_cmd([spk_exe, str(spk_cyc)], timeout=3.0)
        if r_cyc.timed_out:
            issues.append("Spk::open hung in infinite loop on cyclic DAF summary record (no cycle guard!)")
        elif r_cyc.rc != 0 or "AddressSanitizer" in r_cyc.stderr or "runtime error:" in r_cyc.stderr:
            issues.append(f"Spk::open cyclic record triggered ASan/UBSan/crash (rc={r_cyc.rc})")

        # Overflow count=100 in 1024-byte record (24 + 100*40 > 1024)
        spk_ovf = tmp / "spk_count100.bsp"
        buf2 = bytearray(2048)
        buf2[0:7] = b"DAF/SPK"
        struct.pack_into("<ii", buf2, 8, 2, 6)
        struct.pack_into("<i", buf2, 76, 2)
        buf2[88:96] = b"LTL-IEEE"
        struct.pack_into("<ddd", buf2, 1024, 0.0, 0.0, 100.0)
        spk_ovf.write_bytes(buf2)
        r_ovf = run_cmd([spk_exe, str(spk_ovf)], timeout=5.0)
        if r_ovf.timed_out or r_ovf.rc != 0 or "AddressSanitizer" in r_ovf.stderr or "runtime error:" in r_ovf.stderr:
            issues.append(f"Spk::open count=100 triggered ASan/UBSan/crash (rc={r_ovf.rc}): {(r_ovf.stderr or '')[:200]}")

    check(not issues, "; ".join(issues[:6]), {"issues": issues})
    return "ASan+UBSan clean on hostile LongTable, Rejeu & Spk binary loader probes (0 overflows, 0 hangs)", {}


def t2_f5_04_cosmologie_boundary_no_nan(session: E2ESession) -> Tuple[str, dict]:
    art = session.cpp.build_asan_probe()
    check(art.ok and "asan_probe" in art.binaries, f"Failed to compile ASan probe: {art.stderr[:300]}")
    r = run_cmd([str(art.binaries["asan_probe"]), "--mode", "cosmo"], timeout=15.0)
    check(not r.timed_out and r.rc == 0, f"cosmo ASan probe failed (rc={r.rc}): {r.stderr[:300]}")
    check("AddressSanitizer" not in r.stderr and "runtime error:" not in r.stderr, f"UBSan/ASan hit in cosmologie.h: {r.stderr[:300]}")
    info = json.loads(r.stdout.strip().splitlines()[-1])
    bad = [c["case"] for c in info["cases"] if not c["all_ok"]]
    if not info["dt_z0_ok"]:
        bad.append("distanceTable(zMax=0)")
    if not info["dt_steps0_ok"]:
        bad.append("distanceTable(steps=0)")
    check(not bad, f"cosmologie.h produced NaN/Inf/invalid values on boundary cases: {bad}", info)
    return "cosmo::scaleFactorAt & distanceTable finite and >=0 across all w0/wa & boundary probes", info


def t2_f5_05_interface_outils_utf8_and_llong_min(session: E2ESession) -> Tuple[str, dict]:
    art = session.cpp.build_asan_probe()
    check(art.ok and "asan_probe" in art.binaries, f"Failed to compile ASan probe: {art.stderr[:300]}")
    r = run_cmd([str(art.binaries["asan_probe"]), "--mode", "interface"], timeout=15.0)
    issues: List[str] = []
    if r.timed_out or r.rc != 0:
        issues.append(f"interface probe crashed (rc={r.rc}): {r.stderr[:220]}")
    if "runtime error:" in r.stderr or "AddressSanitizer" in r.stderr:
        issues.append(f"UBSan/ASan triggered in interface_outils.h (llabs(LLONG_MIN)?): {r.stderr.strip()[:220]}")
    info = {}
    if r.stdout.strip():
        info = json.loads(r.stdout.strip().splitlines()[-1])
        if info.get("fold_yd") != "y":
            issues.append(f"fold('ÿ') expected 'y', got {info.get('fold_yd')!r}")
        if info.get("fold_oe") != "oe" or info.get("fold_OE") != "oe":
            issues.append(f"fold('œ'/'Œ') expected 'oe', got {info.get('fold_oe')!r}/{info.get('fold_OE')!r}")
        if info.get("parse_over") is not False:
            issues.append("parseDate('99999999999999999999') returned true (ERANGE ignored)")
        if info.get("parse_feb29_2021") is not False:
            issues.append("parseDate('29/02/2021') returned true (invalid non-leap date)")
        if info.get("parse_apr31_2020") is not False:
            issues.append("parseDate('31/04/2020') returned true (invalid 31 April)")
        if info.get("parse_leap_2024") is not True:
            issues.append("parseDate('29/02/2024') rejected valid leap day")
    check(not issues, "; ".join(issues), info)
    return "ui_outils::fold (ÿ->y, œ/Œ->oe) & parseDate (ERANGE, LLONG_MIN UBSan-clean, calendar) PASS", info


def t2_f5_06_glsl_shader_static_invariants(session: E2ESession) -> Tuple[str, dict]:
    sh_dir = NATIF_DIR / "shaders"
    issues: List[str] = []

    # (a) galaxies.vert: NO double-linearization pow(inCol.rgb, vec3(2.2))
    gal = (sh_dir / "galaxies.vert").read_text(encoding="utf-8")
    if re.search(r"pow\s*\(\s*inCol\.rgb\s*,\s*vec3\s*\(\s*2\.2", gal):
        issues.append("galaxies.vert still double-linearizes linear sRGB via pow(inCol.rgb, vec3(2.2)) (GLSL-BUG)")

    # (b) sphere.frag: no dFdx/dFdy inside `if (cover > 0.0)` and use textureLod for anneau
    sph = (sh_dir / "sphere.frag").read_text(encoding="utf-8")
    m_cov = re.search(r"if\s*\(\s*cover\s*>\s*0\.0\s*\)\s*\{(.*?)\n\s*\}", sph, re.S)
    if m_cov and ("dFdx(" in m_cov.group(1) or "dFdy(" in m_cov.group(1)):
        issues.append("sphere.frag evaluates dFdx/dFdy inside non-uniform if (cover > 0.0) branch (GLSL-BUG)")
    if re.search(r"\btexture\s*\(\s*anneau\s*,", sph):
        issues.append("sphere.frag uses implicit-LOD texture(anneau, ...) instead of textureLod in non-uniform control flow")

    # (c) ecran.frag: max(..., vec3(0.0)) NaN-guard before Reinhard/pow
    ecr = (sh_dir / "ecran.frag").read_text(encoding="utf-8")
    if "max(" not in ecr:
        issues.append("ecran.frag lacks max(..., vec3(0.0)) NaN-guard before pow() (GLSL-BUG)")

    # (d) asteroides.vert: Kepler denominator guarded against <= 0
    ast_v = (sh_dir / "asteroides.vert").read_text(encoding="utf-8")
    if re.search(r"/\s*\(\s*1\.0\s*-\s*inE\s*\*\s*cos\s*\(\s*E\s*\)\s*\)", ast_v):
        issues.append("asteroides.vert divides by unguarded (1.0 - inE * cos(E)) (GLSL-BUG)")

    check(not issues, "; ".join(issues), {"issues": issues})
    return "All 4 GLSL 450 shader invariants PASS (galaxies.vert, sphere.frag, ecran.frag, asteroides.vert)", {}


def t2_f5_07_headers_raii_stb_and_truth(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []

    # (a) Zero anonymous `namespace {` across natif/src/*.h
    anon_hdrs = [
        p.name for p in sorted((NATIF_DIR / "src").glob("*.h"))
        if re.search(r"\bnamespace\s*\{", p.read_text(encoding="utf-8"))
    ]
    if anon_hdrs:
        issues.append(f"{len(anon_hdrs)} natif/src/*.h headers still use anonymous 'namespace {{' ({', '.join(anon_hdrs[:5])}...)")

    # (b) Portable RAII MappedFile header natif/src/fichier_mappe.h (Win32 + POSIX mmap)
    fm = NATIF_DIR / "src" / "fichier_mappe.h"
    if not fm.is_file():
        issues.append("missing natif/src/fichier_mappe.h (portable RAII MappedFile)")
    else:
        fsrc = fm.read_text(encoding="utf-8")
        if "_WIN32" not in fsrc or "mmap" not in fsrc:
            issues.append("natif/src/fichier_mappe.h missing Win32/POSIX mmap branches")

    # (c) natif/CMakeLists.txt pins stb to 40-hex commit SHA & removes -Wno-unused-function
    cm = (NATIF_DIR / "CMakeLists.txt").read_text(encoding="utf-8")
    if re.search(r"FetchContent_Declare\s*\(\s*stb\b[^)]*GIT_TAG\s+(?:master|main|HEAD)\b", cm, re.S):
        issues.append("natif/CMakeLists.txt still pins stb to floating master/main/HEAD")
    elif not re.search(r"FetchContent_Declare\s*\(\s*stb\b[^)]*GIT_TAG\s+[0-9a-f]{40}\b", cm, re.S):
        issues.append("natif/CMakeLists.txt does not pin stb to a 40-hex commit SHA")
    if "-Wno-unused-function" in cm:
        issues.append("natif/CMakeLists.txt still carries -Wno-unused-function workaround")

    # (d) readSpv validates size > 0 && size % 4 == 0
    commun = (NATIF_DIR / "src" / "commun.h").read_text(encoding="utf-8")
    m_spv = re.search(r"readSpv\s*\([^)]*\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}", commun, re.S)
    if m_spv and ("% 4" not in m_spv.group(1) and "& 3" not in m_spv.group(1)):
        issues.append("commun.h readSpv lacks 4-byte alignment / size validation")

    # (e) Deep-time truth in interface.h (not unconditional "mesuré" for Galaxy)
    iface = (NATIF_DIR / "src" / "interface.h").read_text(encoding="utf-8")
    m_gal = re.search(r"fb\.kind\s*==\s*Kind::Galaxy\s*\)\s*\{([^}]+)\}", iface, re.S)
    if m_gal and re.search(r'row\s*\(\s*"Distance au Soleil"\s*,\s*frDistance\(dSun\)\s*,\s*"mesuré"', m_gal.group(1)):
        issues.append("interface.h hardcodes 'mesuré' for Galaxy distance even in deepTime() (CPP-BUG)")

    # (f) points_planetes.h doesn't unconditionally return when !sim.ephemValid if outer is active
    pp = (NATIF_DIR / "src" / "points_planetes.h").read_text(encoding="utf-8")
    if re.search(r"if\s*\(\s*!sim\.ephemValid\s*\)\s*return\s*;", pp):
        issues.append("points_planetes.h hides planets whenever !sim.ephemValid (ignoring outer N-body/table; CPP-BUG-01)")

    check(not issues, "; ".join(issues[:8]), {"issues": issues})
    return "0 anonymous namespaces in headers, fichier_mappe.h, stb 40-hex SHA, readSpv & native truth PASS", {}


def get_tests() -> List[TestCase]:
    return [
        TestCase("T2-F5-01", 2, ["F5"], "essai_fusion malformed CLI & missing/0-byte/truncated files exit cleanly (no SIGSEGV)", t2_f5_01_essai_fusion_malformed_cli_no_crash, expected_milestone="M4"),
        TestCase("T2-F5-02", 2, ["F5"], "essai_systeme_solaire/ephem/orientation reject corrupt/missing .bsp cleanly", t2_f5_02_ephem_cli_corrupt_files, expected_milestone="M4"),
        TestCase("T2-F5-03", 2, ["F5"], "ASan+UBSan hostile binary loader probes (LongTable, Rejeu, Spk cyclic/overflow)", t2_f5_03_binary_loaders_asan_ubsan, expected_milestone="M4"),
        TestCase("T2-F5-04", 2, ["F5"], "cosmo::scaleFactorAt & distanceTable boundary safety (zero -nan on w0/wa)", t2_f5_04_cosmologie_boundary_no_nan, expected_milestone="M4"),
        TestCase("T2-F5-05", 2, ["F5"], "ui_outils::fold UTF-8 (ÿ, œ/Œ) & parseDate ERANGE/LLONG_MIN/calendar under UBSan", t2_f5_05_interface_outils_utf8_and_llong_min, expected_milestone="M4"),
        TestCase("T2-F5-06", 2, ["F5"], "GLSL 450 shader invariants (galaxies.vert, sphere.frag, ecran.frag, asteroides.vert)", t2_f5_06_glsl_shader_static_invariants, expected_milestone="M4"),
        TestCase("T2-F5-07", 2, ["F5"], "Header namespace hygiene, RAII MappedFile, stb SHA pin, readSpv & native deep-time truth", t2_f5_07_headers_raii_stb_and_truth, expected_milestone="M4"),
    ]
