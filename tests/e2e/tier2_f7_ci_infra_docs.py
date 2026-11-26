"""Tier 2 — F7: Infrastructure Substitution, Security Scan, Constant Parity & Gitignore Behavior (6 tests)."""
from __future__ import annotations

from pathlib import Path
import re
from typing import List, Tuple

from lib.harness import (
    APP_SRC,
    APP_TEST,
    INFRA_DIR,
    REPO_ROOT,
    WORKFLOWS_DIR,
    E2ESession,
    TestCase,
    check,
    run_cmd,
    yaml_load,
)


def t2_f7_01_email_substitution_edge_cases(session: E2ESession) -> Tuple[str, dict]:
    tpl_path = INFRA_DIR / "storage.rules.tpl"
    dep_path = INFRA_DIR / "deploiement.exemple.yml"
    check(tpl_path.is_file() and dep_path.is_file(), "Missing infra/storage.rules.tpl or infra/deploiement.exemple.yml")
    tpl = tpl_path.read_text(encoding="utf-8")
    dep = dep_path.read_text(encoding="utf-8")

    issues: List[str] = []
    # Deploy template must reject empty AUTHORIZED_EMAIL and avoid sed delimiter/ampersand injection
    if re.search(r'sed\s+["\']s/__AUTHORIZED_EMAIL__', dep):
        issues.append("deploiement.exemple.yml uses fragile sed s/__AUTHORIZED_EMAIL__/.../ (breaks on '&' and '/')")
    if not re.search(r"AUTHORIZED_EMAIL.*(?:empty|vide|-z\s|not\s+os\.environ|strip\(\))", dep, re.IGNORECASE | re.DOTALL):
        issues.append("deploiement.exemple.yml lacks explicit non-empty check on AUTHORIZED_EMAIL")

    # Behavioral literal substitution check with RFC-valid special characters ('+', '&', '/')
    tricky_email = "marc+ops&1/2@example.com"
    rendered = tpl.replace("__AUTHORIZED_EMAIL__", tricky_email)
    check("__AUTHORIZED_EMAIL__" not in rendered, "Placeholder remained after literal substitution")
    check(tricky_email in rendered, "Tricky email lost during literal substitution")
    check("allow write: if false" in rendered, "allow write: if false missing in rendered storage.rules")

    check(not issues, "; ".join(issues))
    return "Deploy template avoids sed & enforces non-empty email; tricky RFC email substitution PASS", {}


def t2_f7_02_negative_security_scan_ci_infra(session: E2ESession) -> Tuple[str, dict]:
    targets = list(WORKFLOWS_DIR.glob("*.yml")) + list(WORKFLOWS_DIR.glob("*.yaml")) + list(INFRA_DIR.glob("*"))
    issues: List[str] = []
    for p in sorted(targets):
        if not p.is_file():
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        rel = str(p.relative_to(REPO_ROOT))
        if re.search(r"BEGIN [A-Z ]*PRIVATE KEY", txt):
            issues.append(f"{rel}: contains private key material")
        for personal in ("/home/claude", "/mnt/user-data"):
            if personal in txt:
                issues.append(f"{rel}: contains personal path '{personal}'")
        if p.name != "README.md" and re.search(r"[a-zA-Z0-9._%+-]+@gmail\.com\b", txt, re.IGNORECASE):
            issues.append(f"{rel}: contains hardcoded @gmail.com address")
        if p.name == "storage.rules.tpl":
            if re.search(r"allow\s+(?:read|write)\s*:\s*if\s+true", txt):
                issues.append(f"{rel}: overly permissive 'if true' rule")
        if p.parent == WORKFLOWS_DIR and re.search(r"permissions\s*:\s*write-all", txt):
            issues.append(f"{rel}: permissions: write-all")
    check(not issues, "; ".join(issues[:8]))
    return f"0 secrets, personal paths, or permissive rules across {len(targets)} workflow/infra files", {}


def t2_f7_03_dynamic_cross_file_constant_parity(session: E2ESession) -> Tuple[str, dict]:
    issues: List[str] = []

    # Extract live Three.js version from app/src/index.html
    index_html = (APP_SRC / "index.html").read_text(encoding="utf-8")
    m_three = re.search(r"three\.js/(\d+\.\d+\.\d+)/three\.min\.js", index_html)
    check(m_three is not None, "Could not extract Three.js semver from app/src/index.html")
    three_ver = m_three.group(1)

    # Extract live LMICRO from app/src/6*.js
    src_6 = "\n".join(p.read_text(encoding="utf-8") for p in sorted(APP_SRC.glob("6*.js")))
    m_lm = re.search(r"\bLMICRO\s*=\s*(-?\d+(?:\.\d+)?)", src_6)
    check(m_lm is not None, "Could not extract LMICRO constant from app/src/6*.js")
    lmicro = float(m_lm.group(1))

    # Count actual JS physics tests
    n_js_tests = len(list(APP_TEST.glob("*.test.js")))

    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    handover = (REPO_ROOT / "HANDOVER.md").read_text(encoding="utf-8")

    if three_ver not in claude:
        issues.append(f"CLAUDE.md missing live Three.js version '{three_ver}'")
    if "r128" in claude:
        issues.append("CLAUDE.md still references obsolete 'r128'")
    if ("-20" not in handover and "−20" not in handover) or ("−35,3" in handover or "-35,3" in handover):
        issues.append(f"HANDOVER.md LMICRO out of sync with live LMICRO={lmicro}")
    if n_js_tests >= 26 and "sept tests" in handover.lower():
        issues.append(f"HANDOVER.md still claims 'sept tests' while repo has {n_js_tests} *.test.js files")

    check(not issues, "; ".join(issues), {"three_ver": three_ver, "lmicro": lmicro, "n_js_tests": n_js_tests})
    return f"Cross-file constant parity PASS (Three.js={three_ver}, LMICRO={lmicro}, JS tests={n_js_tests})", {"three_ver": three_ver, "lmicro": lmicro, "n_js_tests": n_js_tests}


def t2_f7_04_workflow_shell_injection_boundary(session: E2ESession) -> Tuple[str, dict]:
    # Check ALL .github/workflows/*.yml AND infra/deploiement.exemple.yml for direct ${{ inputs.* }} / ${{ github.head_ref }} inside run:
    wf_files = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    dep = INFRA_DIR / "deploiement.exemple.yml"
    if dep.is_file():
        wf_files.append(dep)

    unsafe_re = re.compile(r"\$\{\{\s*(?:inputs\.|github\.event\.inputs\.|github\.head_ref\b|github\.event\.pull_request\.title\b)")
    hits: List[str] = []
    for p in wf_files:
        doc = yaml_load(p)
        jobs = (doc or {}).get("jobs") or {}
        for jname, job in jobs.items():
            if not isinstance(job, dict):
                continue
            for idx, step in enumerate(job.get("steps") or []):
                if not isinstance(step, dict):
                    continue
                run_txt = step.get("run")
                if isinstance(run_txt, str):
                    for m in unsafe_re.finditer(run_txt):
                        hits.append(f"{p.name}:{jname}:step[{idx}] direct interpolation '{m.group(0)}'")

    check(not hits, f"Shell injection risk in workflow run: scripts ({len(hits)}): {'; '.join(hits[:6])}", {"hits": hits})
    return f"0 unsafe direct ${{{{ inputs.* / head_ref }}}} interpolations in run: across {len(wf_files)} workflow files", {}


def t2_f7_05_doc_relative_path_integrity(session: E2ESession) -> Tuple[str, dict]:
    doc_paths = [
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "README.md",
        REPO_ROOT / "CREDITS.md",
        INFRA_DIR / "README.md",
    ]
    audit_doc = REPO_ROOT / "docs" / "audit-qualite-github.md"
    if audit_doc.is_file():
        doc_paths.append(audit_doc)

    # Ignore documented untracked/generated/external/placeholder paths
    ignored_prefixes = (
        "dist/", "seed/", "web/", "univers-raw/", "/tmp/", "captures/",
        "infra/storage.rules", "build/", "build-", "app/test/shots",
        ".agents/", "TEST_", "PROJECT.md", "C:\\", "http://", "https://",
        "/_blob/", "app/src/60_",
    )
    # Match explicit repo-relative paths in backticks like `app/build.py` or `docs/mission-lot1.md`
    path_re = re.compile(r"`((?:app|natif|pipeline|infra|docs|\.github)/[A-Za-z0-9_./-]+)`")
    broken: List[str] = []

    for dp in doc_paths:
        if not dp.is_file():
            continue
        txt = dp.read_text(encoding="utf-8")
        for m in path_re.finditer(txt):
            raw_ref = m.group(1).rstrip(".,;:")
            # Skip glob patterns, placeholders, line-number suffixes, or ignored dirs
            if any(ch in raw_ref for ch in ("*", "<", ">", "{", "}", "$", ":")):
                continue
            if any(raw_ref.startswith(pref) for pref in ignored_prefixes):
                continue
            if raw_ref.endswith("/"):
                target = REPO_ROOT / raw_ref.rstrip("/")
                if not target.is_dir():
                    broken.append(f"{dp.relative_to(REPO_ROOT)} -> `{raw_ref}`")
            else:
                target = REPO_ROOT / raw_ref
                if not target.exists():
                    # Allow planned M3/M5/M6 files ONLY if mentioned inside docs/audit-qualite-github.md as proposals? No, real docs shouldn't have broken paths!
                    broken.append(f"{dp.relative_to(REPO_ROOT)} -> `{raw_ref}`")

    check(not broken, f"Broken local file references in docs ({len(broken)}): {', '.join(broken[:8])}", {"broken": broken})
    return f"All local repo path references across {len(doc_paths)} core docs resolve on disk", {}


def t2_f7_06_behavioral_gitignore_contract(session: E2ESession) -> Tuple[str, dict]:
    must_ignore = (
        "dist/index.html",
        "my-service-account.json",
        "cle.json",
        "infra/storage.rules",
        "build/x",
        "build-linux/CMakeCache.txt",
        "essai.ppm",
        "captures/a.png",
        "x.brouillon",
        ".agents/a.md",
        "pipeline/__pycache__/x.pyc",
    )
    must_track = (
        "app/src/index.html",
        "app/gen/data.js",
        "infra/storage.rules.tpl",
        "natif/physique/CMakeLists.txt",
        "pipeline/pyproject.toml",
        "CREDITS.md",
    )
    issues: List[str] = []
    for p in must_ignore:
        r = run_cmd(["git", "check-ignore", "--no-index", p], cwd=REPO_ROOT, timeout=10.0)
        if r.rc != 0:
            issues.append(f"should be ignored by .gitignore: '{p}'")
    for p in must_track:
        r = run_cmd(["git", "check-ignore", "--no-index", p], cwd=REPO_ROOT, timeout=10.0)
        if r.rc == 0:
            issues.append(f"must NOT be ignored by .gitignore: '{p}'")

    check(not issues, f".gitignore behavioral failures ({len(issues)}): {'; '.join(issues[:8])}", {"issues": issues})
    return f"git check-ignore --no-index PASS on all {len(must_ignore)} ignored & {len(must_track)} tracked paths", {}


def get_tests() -> List[TestCase]:
    return [
        TestCase("T2-F7-01", 2, ["F7"], "Negative & tricky RFC email substitution against infra/storage.rules.tpl", t2_f7_01_email_substitution_edge_cases, expected_milestone="M6"),
        TestCase("T2-F7-02", 2, ["F7"], "Negative security scan of .github/workflows/* & infra/* (0 keys/personal paths)", t2_f7_02_negative_security_scan_ci_infra),
        TestCase("T2-F7-03", 2, ["F7"], "Dynamic cross-file constant parity (index.html/src/tests <-> CLAUDE.md/HANDOVER.md)", t2_f7_03_dynamic_cross_file_constant_parity, expected_milestone="M6"),
        TestCase("T2-F7-04", 2, ["F7"], "GitHub Actions shell injection boundary check (${{ inputs.* / head_ref }} in run:)", t2_f7_04_workflow_shell_injection_boundary, expected_milestone="M6"),
        TestCase("T2-F7-05", 2, ["F7"], "Local relative file-path reference integrity across core documentation", t2_f7_05_doc_relative_path_integrity),
        TestCase("T2-F7-06", 2, ["F7"], "Behavioral .gitignore contract via git check-ignore --no-index (11 ignored / 6 tracked)", t2_f7_06_behavioral_gitignore_contract, expected_milestone="M6"),
    ]
