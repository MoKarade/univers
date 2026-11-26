#!/usr/bin/env python3
"""Canonical opaque-box 4-tier E2E test runner for MoKarade/univers.

Usage:
    python3 tests/e2e/run_e2e.py --tier <1|2|3|4|all> [--format text|json]
                                 [--feature F1..F7] [--test <ID_FILTER>]
                                 [--fail-fast] [--list]

Exit codes:
    0 : All selected tests PASS, errors == 0, temp_dirs_remaining == 0, dist_sha256_unchanged == true.
    1 : >= 1 genuine requirement FAIL, errors == 0, hygiene clean.
    2 : Invalid CLI arguments, zero tests selected, harness ERROR, or hygiene failure.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Dict, List, Optional

# Ensure tests/e2e is importable regardless of CWD
E2E_DIR = Path(__file__).resolve().parent
if str(E2E_DIR) not in sys.path:
    sys.path.insert(0, str(E2E_DIR))

from lib.harness import E2ESession, REPO_ROOT, TestCase, TestFailure, TestResult, run_cmd

VALID_FEATURES = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")

TEST_MODULES = (
    "tier1_f1_build_truth",
    "tier1_f2_physics",
    "tier1_f3_web_runtime",
    "tier1_f4_security_offline",
    "tier1_f5_native_cpp",
    "tier1_f6_pipeline",
    "tier1_f7_ci_infra_docs",
    "tier2_f1_build_truth",
    "tier2_f2_physics",
    "tier2_f3_web_runtime",
    "tier2_f4_security_offline",
    "tier2_f5_native_cpp",
    "tier2_f6_pipeline",
    "tier2_f7_ci_infra_docs",
    "tier3_cross_feature",
    "tier4_workflows",
)


def load_all_tests() -> List[TestCase]:
    tests: List[TestCase] = []
    seen_ids: set[str] = set()
    for mod_name in TEST_MODULES:
        mod = importlib.import_module(mod_name)
        mod_tests: List[TestCase] = mod.get_tests()
        for tc in mod_tests:
            if tc.id in seen_ids:
                raise RuntimeError(f"Duplicate test ID registered: {tc.id}")
            seen_ids.add(tc.id)
            tests.append(tc)
    return tests


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="run_e2e.py",
        description="Opaque-box 4-tier E2E test suite for MoKarade/univers",
    )
    p.add_argument(
        "--tier",
        choices=("1", "2", "3", "4", "all"),
        default=None,
        help="Tier to execute (1, 2, 3, 4, or all). Required unless --list is used.",
    )
    p.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text; json writes pure valid JSON to stdout).",
    )
    p.add_argument(
        "--feature",
        action="append",
        default=[],
        help="Filter by feature F1..F7 (comma-separated or repeatable).",
    )
    p.add_argument(
        "--test",
        default=None,
        help="Substring or exact test ID filter (e.g. T2-F4-01).",
    )
    p.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop executing remaining tests after first FAIL or ERROR.",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="List matching tests without executing them and exit 0.",
    )
    args = p.parse_args(argv)

    # Parse and validate --feature
    features: List[str] = []
    for raw in args.feature:
        for tok in raw.split(","):
            tok = tok.strip().upper()
            if not tok:
                continue
            if tok not in VALID_FEATURES:
                p.error(f"Unknown feature '{tok}'. Valid values: {', '.join(VALID_FEATURES)}")
            if tok not in features:
                features.append(tok)
    args.features = features

    if not args.list and args.tier is None:
        p.error("--tier <1|2|3|4|all> is required unless --list is specified.")
    return args


def filter_tests(
    all_tests: List[TestCase],
    tier: Optional[str],
    features: List[str],
    test_filter: Optional[str],
) -> List[TestCase]:
    out: List[TestCase] = []
    tf_up = test_filter.strip().upper() if test_filter else None
    for tc in all_tests:
        if tier is not None and tier != "all" and str(tc.tier) != tier:
            continue
        if features and not any(f in features for f in tc.features):
            continue
        if tf_up and tf_up not in tc.id.upper():
            continue
        out.append(tc)
    return out


def git_head_sha() -> str:
    res = run_cmd(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, timeout=10.0)
    return res.stdout.strip() if res.rc == 0 else "unknown"


def run_selected(selected: List[TestCase], fail_fast: bool, quiet_stderr: bool) -> tuple[List[TestResult], Dict[str, Any]]:
    session = E2ESession()
    results: List[TestResult] = []
    hygiene: Dict[str, Any] = {
        "temp_dirs_created": session.workspace.created_count,
        "temp_dirs_remaining": 1,
        "dist_sha256_unchanged": False,
    }
    try:
        total = len(selected)
        for idx, tc in enumerate(selected, 1):
            t0 = time.monotonic()
            try:
                ret = tc.fn(session)
                dur = time.monotonic() - t0
                if isinstance(ret, tuple) and len(ret) == 2 and isinstance(ret[1], dict):
                    msg, details = str(ret[0]), ret[1]
                elif isinstance(ret, str):
                    msg, details = ret, {}
                else:
                    msg, details = "OK", {}
                tr = TestResult(
                    id=tc.id,
                    tier=tc.tier,
                    features=list(tc.features),
                    title=tc.title,
                    status="PASS",
                    duration_s=dur,
                    expected_milestone=tc.expected_milestone,
                    message=msg,
                    details=details,
                )
            except TestFailure as tf:
                dur = time.monotonic() - t0
                tr = TestResult(
                    id=tc.id,
                    tier=tc.tier,
                    features=list(tc.features),
                    title=tc.title,
                    status="FAIL",
                    duration_s=dur,
                    expected_milestone=tc.expected_milestone,
                    message=str(tf),
                    details=tf.details,
                )
            except Exception as exc:
                dur = time.monotonic() - t0
                tb = traceback.format_exc()
                tr = TestResult(
                    id=tc.id,
                    tier=tc.tier,
                    features=list(tc.features),
                    title=tc.title,
                    status="ERROR",
                    duration_s=dur,
                    expected_milestone=tc.expected_milestone,
                    message=f"{type(exc).__name__}: {exc}",
                    details={"traceback": tb[-2000:]},
                )
            finally:
                session.pw.park_background_pages()
            results.append(tr)
            if not quiet_stderr:
                sys.stderr.write(f"[{idx:3d}/{total:3d}] {tr.status:5s} {tr.id:10s} ({tr.duration_s:5.2f}s) {tr.title}\n")
                sys.stderr.flush()
            if fail_fast and tr.status != "PASS":
                break
    finally:
        dist_ok = session.workspace.dist_sha256_unchanged()
        session.close()
        hygiene = {
            "temp_dirs_created": session.workspace.created_count,
            "temp_dirs_remaining": session.workspace.remaining_count(),
            "dist_sha256_unchanged": dist_ok,
        }
    return results, hygiene


def build_report(
    args: argparse.Namespace,
    results: List[TestResult],
    hygiene: Dict[str, Any],
    total_duration_s: float,
) -> Dict[str, Any]:
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    errors = sum(1 for r in results if r.status == "ERROR")

    by_tier: Dict[str, Dict[str, int]] = {}
    for t in ("1", "2", "3", "4"):
        tr_list = [r for r in results if str(r.tier) == t]
        by_tier[t] = {
            "total": len(tr_list),
            "passed": sum(1 for r in tr_list if r.status == "PASS"),
            "failed": sum(1 for r in tr_list if r.status == "FAIL"),
            "errors": sum(1 for r in tr_list if r.status == "ERROR"),
        }

    by_feature: Dict[str, Dict[str, int]] = {}
    for f in VALID_FEATURES:
        fr_list = [r for r in results if f in r.features]
        by_feature[f] = {
            "total": len(fr_list),
            "passed": sum(1 for r in fr_list if r.status == "PASS"),
            "failed": sum(1 for r in fr_list if r.status == "FAIL"),
            "errors": sum(1 for r in fr_list if r.status == "ERROR"),
        }

    return {
        "schema_version": "1.0",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_head": git_head_sha(),
        "cli": {
            "tier": args.tier or "all",
            "features": args.features if args.features else list(VALID_FEATURES),
            "format": args.format,
        },
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "duration_s": round(total_duration_s, 3),
            "by_tier": by_tier,
            "by_feature": by_feature,
        },
        "hygiene": hygiene,
        "results": [r.to_dict() for r in results],
    }


def print_text_report(report: Dict[str, Any]) -> None:
    s = report["summary"]
    h = report["hygiene"]
    print("=" * 88)
    print(
        f"MoKarade/univers E2E Report | tier={report['cli']['tier']} | "
        f"HEAD={report['git_head'][:10]} | {report['timestamp_utc']}"
    )
    print("=" * 88)
    for r in report["results"]:
        ms = f" [{r['expected_milestone']}]" if r["expected_milestone"] and r["status"] != "PASS" else ""
        print(f"{r['status']:5s}  {r['id']:10s}  T{r['tier']}  {','.join(r['features']):11s}  {r['duration_s']:6.2f}s  {r['title']}{ms}")
        if r["status"] != "PASS":
            print(f"       -> {r['message']}")
    print("-" * 88)
    print(
        f"Summary: total={s['total']} passed={s['passed']} failed={s['failed']} "
        f"errors={s['errors']} duration={s['duration_s']:.2f}s"
    )
    tier_parts = [f"T{t}={s['by_tier'][t]['passed']}/{s['by_tier'][t]['total']}" for t in ("1", "2", "3", "4") if s["by_tier"][t]["total"]]
    feat_parts = [f"{f}={s['by_feature'][f]['passed']}/{s['by_feature'][f]['total']}" for f in VALID_FEATURES if s["by_feature"][f]["total"]]
    print("By tier:    " + "  ".join(tier_parts))
    print("By feature: " + "  ".join(feat_parts))
    print(
        f"Hygiene:    temp_created={h['temp_dirs_created']} "
        f"temp_remaining={h['temp_dirs_remaining']} "
        f"dist_unchanged={h['dist_sha256_unchanged']}"
    )


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        all_tests = load_all_tests()
    except Exception as exc:
        sys.stderr.write(f"ERROR loading test modules: {exc}\n")
        traceback.print_exc(file=sys.stderr)
        return 2

    selected = filter_tests(all_tests, args.tier, args.features, args.test)

    if args.list:
        if args.format == "json":
            payload = [
                {
                    "id": tc.id,
                    "tier": tc.tier,
                    "features": tc.features,
                    "title": tc.title,
                    "expected_milestone": tc.expected_milestone,
                }
                for tc in selected
            ]
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            by_t = {1: 0, 2: 0, 3: 0, 4: 0}
            for tc in selected:
                by_t[tc.tier] += 1
                print(f"{tc.id:10s}  T{tc.tier}  {','.join(tc.features):11s}  {tc.title}")
            print(f"\nTotal: {len(selected)} (T1={by_t[1]}, T2={by_t[2]}, T3={by_t[3]}, T4={by_t[4]})")
        return 0

    if not selected:
        sys.stderr.write("ERROR: zero tests matched the requested filters.\n")
        return 2

    t0 = time.monotonic()
    results, hygiene = run_selected(selected, fail_fast=args.fail_fast, quiet_stderr=(args.format == "json"))
    total_dur = time.monotonic() - t0
    report = build_report(args, results, hygiene, total_dur)

    if args.format == "json":
        sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    else:
        print_text_report(report)

    s = report["summary"]
    hygiene_ok = hygiene["temp_dirs_remaining"] == 0 and hygiene["dist_sha256_unchanged"] is True
    if s["errors"] > 0 or not hygiene_ok:
        return 2
    if s["failed"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
