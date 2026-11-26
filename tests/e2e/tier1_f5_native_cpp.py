"""Tier 1 — F5: Portable Native C++20 Physics & Build Contracts (7 tests)."""
from __future__ import annotations

import re
from typing import List, Tuple

from lib.harness import E2ESession, TestCase, check, run_cmd


def _run_valgrind(binary_path: str, args: List[str] = (), timeout: float = 45.0):
    return run_cmd(
        ["valgrind", "--leak-check=full", "--errors-for-leak-kinds=all", "--error-exitcode=1", binary_path, *args],
        timeout=timeout,
    )


def t1_f5_01_cmake_physique_gcc(session: E2ESession) -> Tuple[str, dict]:
    art = session.cpp.build_cmake_phys_gcc()
    expected = ("univers_physique", "essai_galaxie", "essai_fusion", "essai_systeme_solaire")
    missing = [t for t in expected if t not in art.binaries]
    check(
        art.ok and not missing,
        f"CMake GCC build of natif/physique (-Werror) failed ({art.note}, rc={art.rc}, missing={missing}): "
        f"{(art.stderr or art.stdout).strip()[:400]}",
        {"rc": art.rc, "missing": missing},
    )
    return f"CMake Ninja GCC C++20 build of natif/physique PASS (0 warnings, 4 targets)", {"targets": list(art.binaries)}


def t1_f5_02_cmake_natif_linux_portable(session: E2ESession) -> Tuple[str, dict]:
    art = session.cpp.build_cmake_natif_gcc()
    expected = ("essai_cosmologie", "essai_interface", "essai_ephem", "essai_orientation")
    missing = [t for t in expected if t not in art.binaries]
    check(
        art.ok and not missing,
        f"CMake Linux portable build of natif/ (-Werror) failed ({art.note}, rc={art.rc}, missing={missing}): "
        f"{(art.stderr or art.stdout).strip()[:400]}",
        {"rc": art.rc, "missing": missing},
    )
    return "CMake Ninja Linux portable build of natif/ PASS (0 warnings, 4 portable test targets)", {"targets": list(art.binaries)}


def t1_f5_03_cmake_physique_clang(session: E2ESession) -> Tuple[str, dict]:
    art = session.cpp.build_cmake_phys_clang()
    expected = ("univers_physique", "essai_galaxie", "essai_fusion", "essai_systeme_solaire")
    missing = [t for t in expected if t not in art.binaries]
    check(
        art.ok and not missing,
        f"CMake Clang 18 build of natif/physique (-Werror) failed ({art.note}, rc={art.rc}, missing={missing}): "
        f"{(art.stderr or art.stdout).strip()[:400]}",
        {"rc": art.rc, "missing": missing},
    )
    return "CMake Ninja Clang++ C++20 build of natif/physique PASS (0 warnings, 4 targets)", {"targets": list(art.binaries)}


def t1_f5_04_essai_cosmologie_valgrind(session: E2ESession) -> Tuple[str, dict]:
    art = session.cpp.get_binary("essai_cosmologie", compiler="g++", allow_direct_fallback=True)
    check(art.ok and "essai_cosmologie" in art.binaries, f"Failed to build essai_cosmologie: {art.stderr[:300]}")
    exe = str(art.binaries["essai_cosmologie"])
    res = run_cmd([exe], timeout=15.0)
    check(not res.timed_out and res.rc == 0, f"essai_cosmologie failed (rc={res.rc}): {res.stdout[:300]}")
    passe_lines = [ln for ln in res.stdout.splitlines() if "PASSE" in ln]
    check(len(passe_lines) >= 7 and "ECHEC" not in res.stdout, f"Unexpected essai_cosmologie output: {res.stdout[:300]}")
    check("13.79" in res.stdout or "13,79" in res.stdout, f"Missing age ~13.79 Ga in output: {res.stdout[:300]}")

    vg = _run_valgrind(exe, timeout=30.0)
    check(not vg.timed_out and vg.rc == 0, f"Valgrind failed on essai_cosmologie (rc={vg.rc}): {vg.stderr[-400:]}")
    return f"essai_cosmologie PASS ({res.duration_s:.3f}s, {len(passe_lines)} PASSE lines, Valgrind 0 errors)", {"duration_s": round(res.duration_s, 3)}


def t1_f5_05_essai_interface_valgrind(session: E2ESession) -> Tuple[str, dict]:
    art = session.cpp.get_binary("essai_interface", compiler="g++", allow_direct_fallback=True)
    check(art.ok and "essai_interface" in art.binaries, f"Failed to build essai_interface: {art.stderr[:300]}")
    exe = str(art.binaries["essai_interface"])
    res = run_cmd([exe], timeout=15.0)
    check(not res.timed_out and res.rc == 0, f"essai_interface failed (rc={res.rc}): {res.stdout[:300]}")
    check("ECHEC" not in res.stdout and res.stdout.strip().endswith("PASSE"), f"Unexpected essai_interface output: {res.stdout[:300]}")

    vg = _run_valgrind(exe, timeout=30.0)
    check(not vg.timed_out and vg.rc == 0, f"Valgrind failed on essai_interface (rc={vg.rc}): {vg.stderr[-400:]}")
    return f"essai_interface PASS ({res.duration_s:.3f}s, Valgrind 0 errors)", {"duration_s": round(res.duration_s, 3)}


def t1_f5_06_essai_galaxie_accuracy_perf(session: E2ESession) -> Tuple[str, dict]:
    art = session.cpp.get_binary("essai_galaxie", compiler="g++", allow_direct_fallback=True)
    check(art.ok and "essai_galaxie" in art.binaries, f"Failed to build essai_galaxie: {art.stderr[:300]}")
    exe = str(art.binaries["essai_galaxie"])
    res = run_cmd([exe], timeout=60.0)
    check(not res.timed_out and res.rc == 0, f"essai_galaxie failed (rc={res.rc}, timed_out={res.timed_out}): {res.stdout[:300]}")
    check("ECHEC" not in res.stdout and res.stdout.strip().endswith("PASSE"), f"essai_galaxie reported ECHEC: {res.stdout[:400]}")
    m = re.search(r"100\s*000\s+étoiles\s+sur\s+100\s+Ma\s*:\s*(\d+(?:\.\d+)?)\s*ms", res.stdout)
    check(m is not None, f"Could not parse 100k stars/100 Ma timing from essai_galaxie output: {res.stdout}")
    ms = float(m.group(1))
    check(
        ms < 3000.0,
        f"essai_galaxie 100k stars/100 Ma took {ms:.0f} ms (SLA target: < 3000 ms, CPP-PERF-01)",
        {"ms_100k_100ma": ms, "wall_s": round(res.duration_s, 2)},
    )
    return f"essai_galaxie PASS: 100k stars/100 Ma in {ms:.0f} ms (< 3000 ms SLA; wall {res.duration_s:.2f}s)", {"ms_100k_100ma": ms}


def t1_f5_07_essai_systeme_solaire_noyau(session: E2ESession) -> Tuple[str, dict]:
    art = session.cpp.get_binary("essai_systeme_solaire", compiler="g++", allow_direct_fallback=True)
    check(
        art.ok and "essai_systeme_solaire" in art.binaries,
        f"essai_systeme_solaire failed to compile on Linux (ephemeride.h windows.h?): {art.stderr[:350]}",
    )
    exe = str(art.binaries["essai_systeme_solaire"])

    # Run with --noyau (must validate 6 Horizons 1650-2450 epochs data-free)
    res = run_cmd([exe, "--noyau"], timeout=30.0)
    check(not res.timed_out and res.rc == 0,
          f"essai_systeme_solaire --noyau failed (rc={res.rc}): {(res.stderr or res.stdout)[:350]}")
    passe_cnt = sum(1 for ln in res.stdout.splitlines() if ln.strip().startswith("PASSE"))
    check(passe_cnt >= 6 and "ECHEC" not in res.stdout,
          f"Expected >= 6 Horizons PASSE lines, got {passe_cnt}: {res.stdout[:400]}")

    # Also verify no-arg mode per PROJECT.md Contract §3
    res_noarg = run_cmd([exe], timeout=30.0)
    check(not res_noarg.timed_out and res_noarg.rc == 0,
          f"essai_systeme_solaire (no args) should run --noyau and exit 0 (got rc={res_noarg.rc}): {res_noarg.stderr[:250]}")

    vg = _run_valgrind(exe, ["--noyau"], timeout=60.0)
    check(not vg.timed_out and vg.rc == 0, f"Valgrind failed on essai_systeme_solaire --noyau (rc={vg.rc}): {vg.stderr[-400:]}")
    return f"essai_systeme_solaire --noyau PASS ({res.duration_s:.2f}s, {passe_cnt} PASSE, Valgrind 0 errors)", {"passe": passe_cnt}


def get_tests() -> List[TestCase]:
    return [
        TestCase("T1-F5-01", 1, ["F5"], "Standalone CMake GCC C++20 build of natif/physique (-Werror)", t1_f5_01_cmake_physique_gcc, expected_milestone="M4"),
        TestCase("T1-F5-02", 1, ["F5"], "Linux portable CMake GCC build of natif/ without glslang/Win32 (-Werror)", t1_f5_02_cmake_natif_linux_portable, expected_milestone="M4"),
        TestCase("T1-F5-03", 1, ["F5"], "Standalone CMake Clang 18 C++20 build of natif/physique (-Werror)", t1_f5_03_cmake_physique_clang, expected_milestone="M4"),
        TestCase("T1-F5-04", 1, ["F5"], "essai_cosmologie CLI accuracy & Valgrind 0-error check", t1_f5_04_essai_cosmologie_valgrind),
        TestCase("T1-F5-05", 1, ["F5"], "essai_interface CLI accuracy & Valgrind 0-error check", t1_f5_05_essai_interface_valgrind),
        TestCase("T1-F5-06", 1, ["F5"], "essai_galaxie accuracy, reversibility & 100k-star perf SLA (< 3000 ms)", t1_f5_06_essai_galaxie_accuracy_perf, expected_milestone="M4"),
        TestCase("T1-F5-07", 1, ["F5"], "essai_systeme_solaire --noyau Horizons 1650-2450 & Valgrind check", t1_f5_07_essai_systeme_solaire_noyau, expected_milestone="M4"),
    ]
