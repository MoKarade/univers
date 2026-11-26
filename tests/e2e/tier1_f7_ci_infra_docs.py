"""Tier 1 — F7: CI/CD, Infrastructure, Attribution & Documentation Consistency (6 tests)."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple

from lib.harness import (
    APP_SRC,
    INFRA_DIR,
    REPO_ROOT,
    WORKFLOWS_DIR,
    E2ESession,
    TestCase,
    check,
    run_cmd,
    yaml_load,
)

REQUIRED_CREDITS_TOKENS = (
    ("HYG", ("hyg",)),
    ("HYG CC BY-SA 4.0", ("cc by-sa 4.0",)),
    ("Gaia", ("gaia",)),
    ("DESI", ("desi",)),
    ("SDSS", ("sdss",)),
    ("2MRS", ("2mrs",)),
    ("6dFGS", ("6dfgs",)),
    ("2dFGRS", ("2dfgrs",)),
    ("Karachentsev", ("karachentsev",)),
    ("McConnachie", ("mcconnachie",)),
    ("ATNF", ("atnf",)),
    ("Harris", ("harris",)),
    ("Cantat-Gaudin", ("cantat-gaudin",)),
    ("van den Bosch", ("van den bosch",)),
    ("BlackCAT", ("blackcat",)),
    ("Gillessen", ("gillessen",)),
    ("Roman", ("roman",)),
    ("OpenNGC", ("openngc",)),
    ("Cosmicflows-4", ("cosmicflows-4", "cosmicflows")),
    ("Planck", ("planck",)),
    ("GWOSC", ("gwosc",)),
    ("Edenhofer", ("edenhofer",)),
    ("MIST", ("mist",)),
    ("CT18NNLO", ("ct18nnlo", "ct18")),
    ("Solar System Scope", ("solar system scope",)),
    ("ESO", ("eso",)),
    ("JPL", ("jpl",)),
    ("Stellarium", ("stellarium",)),
)


def t1_f7_01_workflows_yaml_and_least_privilege(session: E2ESession) -> Tuple[str, dict]:
    wf_files = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    check(len(wf_files) >= 4, f"Expected >= 4 workflow YAML files in .github/workflows/, found {len(wf_files)}")

    issues: List[str] = []
    for p in wf_files:
        try:
            doc = yaml_load(p)
        except Exception as exc:
            issues.append(f"{p.name}: YAML parse error ({exc})")
            continue
        if not isinstance(doc, dict):
            issues.append(f"{p.name}: root is not a mapping")
            continue
        for req_key in ("name", "on", "jobs"):
            if req_key not in doc:
                issues.append(f"{p.name}: missing top-level '{req_key}'")
        perms = doc.get("permissions")
        if perms == "write-all" or (isinstance(perms, dict) and perms.get("contents") == "write"):
            issues.append(f"{p.name}: overly broad top-level permissions={perms}")
        jobs = doc.get("jobs") or {}
        for jname, job in jobs.items():
            if not isinstance(job, dict):
                continue
            has_perm = perms is not None or job.get("permissions") is not None
            if not has_perm:
                issues.append(f"{p.name}:{jname}: missing explicit permissions")
            tm = job.get("timeout-minutes")
            if not isinstance(tm, int) or not (1 <= tm <= 360):
                issues.append(f"{p.name}:{jname}: invalid timeout-minutes={tm!r}")
            for step in job.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                uses = str(step.get("uses", ""))
                if uses.startswith("actions/checkout@"):
                    w = step.get("with") or {}
                    if w.get("persist-credentials") is not False:
                        issues.append(f"{p.name}:{jname}: actions/checkout missing persist-credentials: false")
        if p.name == "controles.yml":
            conc = doc.get("concurrency") or {}
            if not (isinstance(conc, dict) and conc.get("cancel-in-progress") is True):
                issues.append("controles.yml: missing concurrency.cancel-in-progress: true")

    check(not issues, "; ".join(issues[:8]), {"issues": issues})
    return f"All {len(wf_files)} workflow YAMLs valid with least-privilege permissions, timeouts & persist-credentials: false", {"count": len(wf_files)}


def t1_f7_02_ci_multistack_and_supply_chain(session: E2ESession) -> Tuple[str, dict]:
    ctrl_path = WORKFLOWS_DIR / "controles.yml"
    check(ctrl_path.is_file(), "Missing .github/workflows/controles.yml")
    ctrl = yaml_load(ctrl_path)
    ctrl_raw = ctrl_path.read_text(encoding="utf-8")
    issues: List[str] = []

    # 1. Trigger coverage: push on main & appli-pc, pull_request, workflow_dispatch
    on_cfg = ctrl.get("on") or {}
    if isinstance(on_cfg, dict):
        push_branches = (on_cfg.get("push") or {}).get("branches") if isinstance(on_cfg.get("push"), dict) else []
        if "main" not in (push_branches or []) or "appli-pc" not in (push_branches or []):
            issues.append(f"controles.yml push.branches must cover main & appli-pc (got {push_branches!r})")
        if "pull_request" not in on_cfg:
            issues.append("controles.yml missing pull_request trigger")
        if "workflow_dispatch" not in on_cfg:
            issues.append("controles.yml missing workflow_dispatch trigger")

    # 2. Multi-stack job/step coverage in controles.yml
    all_runs = "\n".join(
        str(step.get("run", ""))
        for job in (ctrl.get("jobs") or {}).values()
        if isinstance(job, dict)
        for step in (job.get("steps") or [])
        if isinstance(step, dict)
    )
    for label, pattern in (
        ("web build (app/build.py)", r"app/build\.py"),
        ("FATE_P check", r"FATE_P"),
        ("eslint check", r"\beslint\b"),
        ("prettier check", r"\bprettier\b"),
        ("inline // guard", r"//"),
        ("Linux C++20 CMake build/test", r"\bcmake\b"),
        ("Python pipeline stdlib test", r"test_build_gw\.py|test_pipeline_stdlib\.py"),
    ):
        if not re.search(pattern, all_runs):
            issues.append(f"controles.yml missing {label}")

    # 3. Supply-chain checks across ALL workflows: deprecated Node 20 major tags & floating clones
    deprecated_tags = (
        "actions/checkout@v4",
        "actions/setup-node@v4",
        "actions/setup-python@v5",
        "actions/upload-artifact@v4",
        "actions/download-artifact@v4",
    )
    for p in sorted(WORKFLOWS_DIR.glob("*.yml")):
        txt = p.read_text(encoding="utf-8")
        for tag in deprecated_tags:
            if tag in txt:
                issues.append(f"{p.name}: deprecated Node 20 action tag '{tag}'")
        if re.search(r"git\s+clone\s+--depth\s+1\s+https://github\.com/(?:GalacticDynamics-Oxford/Agama|WalterDehnen/pyfalcon|[^/\s]+/(?:Agama|pyfalcon))", txt, re.IGNORECASE):
            issues.append(f"{p.name}: unpinned floating 'git clone --depth 1' of Agama/pyfalcon HEAD")

    check(not issues, "; ".join(issues[:10]), {"issues": issues})
    return "controles.yml covers Web/Lint/C++20/Python on main+appli-pc; workflows pinned & Node-24 ready", {}


def t1_f7_03_infra_firebase_and_deploy_template(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []

    # 1. infra/firebase.json
    fb_path = INFRA_DIR / "firebase.json"
    if not fb_path.is_file():
        issues.append("missing infra/firebase.json")
    else:
        fb = json.loads(fb_path.read_text(encoding="utf-8"))
        fb_raw = fb_path.read_text(encoding="utf-8")
        if "noindex" not in fb_raw:
            issues.append("infra/firebase.json missing X-Robots-Tag: noindex")
        if (fb.get("storage") or {}).get("rules") != "infra/storage.rules":
            issues.append(f"infra/firebase.json storage.rules mismatch: {fb.get('storage')}")

    # 2. infra/storage.rules.tpl
    sr_path = INFRA_DIR / "storage.rules.tpl"
    if not sr_path.is_file():
        issues.append("missing infra/storage.rules.tpl")
    else:
        sr = sr_path.read_text(encoding="utf-8")
        for req in ("rules_version = '2'", "request.auth != null", "email_verified == true", "__AUTHORIZED_EMAIL__", "allow write: if false"):
            if req not in sr:
                issues.append(f"infra/storage.rules.tpl missing {req!r}")

    # 3. CORS config: no hardcoded https://PROJET.web.app in live non-template infra/cors.json
    cors_live = INFRA_DIR / "cors.json"
    cors_tpl = INFRA_DIR / "cors.json.tpl"
    if cors_live.is_file() and "PROJET.web.app" in cors_live.read_text(encoding="utf-8"):
        issues.append("infra/cors.json still contains hardcoded placeholder 'https://PROJET.web.app' (should be templated infra/cors.json.tpl)")
    cors_target = cors_tpl if cors_tpl.is_file() else cors_live
    if not cors_target.is_file():
        issues.append("missing infra/cors.json.tpl (or cors.json)")
    else:
        try:
            cdata = json.loads(cors_target.read_text(encoding="utf-8"))
            methods = {m.upper() for entry in cdata for m in entry.get("method", [])}
            if not methods.issubset({"GET", "HEAD"}) or not methods:
                issues.append(f"CORS methods must be subset of GET/HEAD, got {sorted(methods)}")
        except Exception as exc:
            issues.append(f"Invalid JSON in {cors_target.name}: {exc}")

    # 4. infra/deploiement.exemple.yml
    dep_path = INFRA_DIR / "deploiement.exemple.yml"
    if not dep_path.is_file():
        issues.append("missing infra/deploiement.exemple.yml")
    else:
        dep_txt = dep_path.read_text(encoding="utf-8")
        dep = yaml_load(dep_path)
        if dep.get("permissions") is None and not any(
            isinstance(j, dict) and j.get("permissions") is not None for j in (dep.get("jobs") or {}).values()
        ):
            issues.append("deploiement.exemple.yml missing explicit permissions:")
        if not all(isinstance(j, dict) and isinstance(j.get("timeout-minutes"), int) for j in (dep.get("jobs") or {}).values()):
            issues.append("deploiement.exemple.yml missing job timeout-minutes:")
        if re.search(r'sed\s+["\']s/__AUTHORIZED_EMAIL__', dep_txt):
            issues.append("deploiement.exemple.yml still uses unsafe sed substitution for __AUTHORIZED_EMAIL__")
        if re.search(r"firebase-tools@13\b(?!\.\d)", dep_txt):
            issues.append("deploiement.exemple.yml uses unpinned major tag firebase-tools@13")
        if "403" not in dep_txt:
            issues.append("deploiement.exemple.yml missing HTTP 403 unauthenticated Storage smoke check")
        if not re.search(r"AUTHORIZED_EMAIL.*(?:empty|vide|test\s+-z|-z\s|not\s+os\.environ|strip\(\))", dep_txt, re.IGNORECASE | re.DOTALL):
            issues.append("deploiement.exemple.yml missing non-empty check for AUTHORIZED_EMAIL")

    check(not issues, "; ".join(issues[:8]), {"issues": issues})
    return "Firebase configs, CORS template & hardened deploiement.exemple.yml PASS", {}


def t1_f7_04_git_hygiene_contracts(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []
    gi = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    ga = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")

    # .gitignore required coverage
    for label, pat in (
        ("dist/", r"(?m)^dist/?$"),
        ("infra/storage.rules", r"infra/storage\.rules"),
        ("C++ build dirs (build/ or build-*/)", r"(?m)^build(?:-\*)?/?$"),
        ("*.ppm", r"\*\.ppm"),
        ("captures/", r"(?m)^captures/?$"),
        ("*.brouillon", r"\*\.brouillon"),
        (".agents/", r"(?m)^\.agents/?$"),
    ):
        if not re.search(pat, gi):
            issues.append(f".gitignore missing {label}")

    # .gitattributes required coverage
    if not re.search(r"\*\s+text=auto\s+eol=lf", ga):
        issues.append(".gitattributes missing '* text=auto eol=lf'")
    for ext in ("*.jpg", "*.png", "*.bin", "*.fits", "*.fit", "*.ppm", "*.npz"):
        if not re.search(re.escape(ext) + r"\s+binary\b", ga):
            issues.append(f".gitattributes missing '{ext} binary'")

    # Tracked index cleanliness (read-only git ls-files)
    ls = run_cmd(["git", "ls-files"], cwd=REPO_ROOT, timeout=15.0)
    check(ls.rc == 0, f"git ls-files failed: {ls.stderr[:200]}")
    tracked = ls.stdout.splitlines()
    bad_tracked = [
        f for f in tracked
        if f.endswith(".brouillon")
        or f.endswith(".ppm")
        or f.startswith(".agents/")
        or f == "infra/storage.rules"
        or "service-account" in f.lower()
    ]
    if bad_tracked:
        issues.append(f"Forbidden tracked files in git index: {bad_tracked[:6]}")

    check(not issues, "; ".join(issues[:10]), {"issues": issues})
    return ".gitignore, .gitattributes & tracked git index hygiene PASS", {}


def t1_f7_05_credits_attribution_completeness(session: E2ESession) -> Tuple[str, dict]:
    credits_path = REPO_ROOT / "CREDITS.md"
    check(credits_path.is_file(), "Missing CREDITS.md")
    txt = credits_path.read_text(encoding="utf-8").lower()
    missing: List[str] = []
    for label, variants in REQUIRED_CREDITS_TOKENS:
        if not any(v in txt for v in variants):
            missing.append(label)
    # Stellarium license explicitly noted/resolved
    if "stellarium" in txt and not any(w in txt for w in ("gpl", "licence", "license", "remplac")):
        missing.append("Stellarium license note")
    check(not missing, f"CREDITS.md missing {len(missing)} required attributions: {', '.join(missing[:12])}", {"missing": missing})
    return f"CREDITS.md covers all {len(REQUIRED_CREDITS_TOKENS)} mandatory scientific catalogs & licenses", {}


def t1_f7_06_docs_sync_and_github_audit(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []

    # 1. CLAUDE.md
    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    if "0.149.0" not in claude or "r128" in claude:
        issues.append("CLAUDE.md must reference three.js 0.149.0 (and not stale r128)")
    if not all(tag in claude for tag in ("[Certain]", "[Probable]", "[Supposition]", "[À vérifier]")):
        issues.append("CLAUDE.md missing French epistemic discipline markers")
    if "natif/" not in claude:
        issues.append("CLAUDE.md missing natif/ build/test documentation")

    # 2. HANDOVER.md
    handover = (REPO_ROOT / "HANDOVER.md").read_text(encoding="utf-8")
    for stale in ("sept tests", "−35,3", "-35,3", "sans barre ni bras"):
        if stale.lower() in handover.lower():
            issues.append(f"HANDOVER.md still contains stale claim '{stale}'")

    # 3. README.md
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    if len(readme.encode("utf-8")) < 500:
        issues.append(f"README.md is still a stub ({len(readme.encode('utf-8'))} B < 500 B)")
    for kw in ("natif", "pipeline", "CREDITS"):
        if kw.lower() not in readme.lower():
            issues.append(f"README.md missing '{kw}' section/reference")

    # 4. docs/gestes-marc.md
    gestes = (REPO_ROOT / "docs" / "gestes-marc.md").read_text(encoding="utf-8")
    if "dépôt privé" in gestes.lower():
        issues.append("docs/gestes-marc.md still contains stale 'dépôt privé' contradiction")

    # 5. docs/audit-qualite-github.md
    audit_path = REPO_ROOT / "docs" / "audit-qualite-github.md"
    if not audit_path.is_file():
        issues.append("missing docs/audit-qualite-github.md")
    else:
        audit = audit_path.read_text(encoding="utf-8")
        if len(audit.encode("utf-8")) < 2000:
            issues.append(f"docs/audit-qualite-github.md too short ({len(audit.encode('utf-8'))} B < 2000 B)")
        if "[Certain]" not in audit:
            issues.append("docs/audit-qualite-github.md missing epistemic markers ([Certain], ...)")
        for topic_label, pat in (
            ("appli-pc vs main", r"appli-pc"),
            ("PR #152", r"152"),
            ("captures/", r"captures"),
            ("LICENSE", r"LICENSE|licence"),
            ("branch protection", r"protection|protect"),
            ("deleteBranchOnMerge", r"deleteBranchOnMerge|suppression automatique"),
            ("Secret Scanning", r"secret\s*scanning"),
        ):
            if not re.search(pat, audit, re.IGNORECASE):
                issues.append(f"docs/audit-qualite-github.md missing topic '{topic_label}'")

    check(not issues, "; ".join(issues[:10]), {"issues": issues})
    return "CLAUDE.md, HANDOVER.md, README.md, docs/gestes-marc.md & docs/audit-qualite-github.md synchronized", {}


def get_tests() -> List[TestCase]:
    return [
        TestCase("T1-F7-01", 1, ["F7"], "All .github/workflows/*.yml valid YAML & least-privilege security baseline", t1_f7_01_workflows_yaml_and_least_privilege),
        TestCase("T1-F7-02", 1, ["F7"], "controles.yml multi-stack coverage & workflow supply-chain pinning", t1_f7_02_ci_multistack_and_supply_chain, expected_milestone="M6"),
        TestCase("T1-F7-03", 1, ["F7"], "Firebase infrastructure configs & hardened deploy template (infra/*)", t1_f7_03_infra_firebase_and_deploy_template, expected_milestone="M6"),
        TestCase("T1-F7-04", 1, ["F7"], "Git hygiene contracts (.gitignore, .gitattributes & clean tracked index)", t1_f7_04_git_hygiene_contracts, expected_milestone="M5/M6"),
        TestCase("T1-F7-05", 1, ["F7"], "Legal & scientific data attribution completeness (CREDITS.md <-> index.html)", t1_f7_05_credits_attribution_completeness, expected_milestone="M6"),
        TestCase("T1-F7-06", 1, ["F7"], "Documentation sync & French /github quality audit deliverable", t1_f7_06_docs_sync_and_github_audit, expected_milestone="M6"),
    ]
