"""Core opaque-box E2E harness for MoKarade/univers.

Provides:
- TempWorkspace: session-scoped chmod 0o700 /tmp dir with atexit + finally cleanup
  and dist/index.html SHA-256 immutability tracking.
- LoopbackServer: ThreadingHTTPServer serving temp-built HTML + dynamic mock endpoints.
- PlaywrightSession: ONE shared Chromium SwiftShader instance with warm desktop page
  reuse and isolated contexts for destructive/mobile/XSS/offline tests.
- run_cmd: subprocess runner with start_new_session=True and process-group SIGKILL.
- yaml_load: zero-dependency YAML parser via ruby -ryaml -rjson (no PyYAML).
- scan_js_slash_slash_hazards: stateful JS lexer flagging multi-statement // traps.
"""
from __future__ import annotations

import atexit
import base64
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import urllib.request
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
DIST_HTML = REPO_ROOT / "dist" / "index.html"
APP_DIR = REPO_ROOT / "app"
APP_SRC = APP_DIR / "src"
APP_GEN = APP_DIR / "gen"
APP_TEST = APP_DIR / "test"
NATIF_DIR = REPO_ROOT / "natif"
PIPELINE_DIR = REPO_ROOT / "pipeline"
INFRA_DIR = REPO_ROOT / "infra"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


class TestFailure(AssertionError):
    """Genuine requirement assertion failure (maps to status FAIL, exit code 1)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.details = details or {}


def fail(message: str, details: Optional[Dict[str, Any]] = None) -> None:
    raise TestFailure(message, details=details)


def check(cond: bool, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    if not cond:
        raise TestFailure(message, details=details)


@dataclass
class TestCase:
    id: str
    tier: int
    features: List[str]
    title: str
    fn: Callable[["E2ESession"], Any]
    expected_milestone: Optional[str] = None


@dataclass
class TestResult:
    id: str
    tier: int
    features: List[str]
    title: str
    status: str  # PASS | FAIL | ERROR
    duration_s: float
    expected_milestone: Optional[str]
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tier": self.tier,
            "features": self.features,
            "title": self.title,
            "status": self.status,
            "duration_s": round(self.duration_s, 3),
            "expected_milestone": self.expected_milestone,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class CmdResult:
    rc: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False


def sha256_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(
    cmd: Sequence[str],
    cwd: Optional[Path | str] = None,
    timeout: float = 60.0,
    env: Optional[Dict[str, str]] = None,
    stdin_text: Optional[str] = None,
) -> CmdResult:
    """Execute a subprocess in its own process group with guaranteed SIGKILL on timeout."""
    t0 = time.monotonic()
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    proc = subprocess.Popen(
        list(cmd),
        cwd=str(cwd) if cwd is not None else str(REPO_ROOT),
        stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=full_env,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(input=stdin_text, timeout=timeout)
        return CmdResult(
            rc=proc.returncode,
            stdout=out,
            stderr=err,
            duration_s=time.monotonic() - t0,
            timed_out=False,
        )
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            out, err = proc.communicate(timeout=5)
        except Exception:
            out, err = "", ""
        return CmdResult(
            rc=-9,
            stdout=out,
            stderr=err,
            duration_s=time.monotonic() - t0,
            timed_out=True,
        )


def node_eval_json(
    js_code: str,
    timeout: float = 30.0,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[CmdResult, Any]:
    """Run a Node script passed on stdin that prints a single JSON value on the last line."""
    res = run_cmd(["node", "-"], cwd=cwd or REPO_ROOT, timeout=timeout, env=env, stdin_text=js_code)
    if res.timed_out or res.rc != 0:
        return res, None
    text = res.stdout.strip()
    if not text:
        return res, None
    try:
        return res, json.loads(text)
    except json.JSONDecodeError:
        # Try last non-empty line if code logged something earlier
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if lines:
            try:
                return res, json.loads(lines[-1])
            except json.JSONDecodeError:
                pass
        return res, None


_RUBY_YAML_SCRIPT = r"""
require 'date'
require 'yaml'
require 'json'
def norm(v)
  case v
  when Hash
    out = {}
    v.each do |k, val|
      nk = k.equal?(true) ? 'on' : (k.equal?(false) ? 'off' : k.to_s)
      out[nk] = norm(val)
    end
    out
  when Array
    v.map { |x| norm(x) }
  else
    v
  end
end
data = YAML.safe_load(STDIN.read, permitted_classes: [Date, Time, Symbol], aliases: true)
puts JSON.generate(norm(data))
"""


def yaml_load(path: Path) -> Any:
    """Parse YAML via Ruby stdlib YAML.safe_load (no PyYAML required), normalizing YAML 1.1 `on`."""
    content = path.read_text(encoding="utf-8")
    res = run_cmd(["ruby", "-e", _RUBY_YAML_SCRIPT], timeout=15.0, stdin_text=content)
    if res.rc != 0:
        raise ValueError(f"YAML parse failed for {path}: {res.stderr.strip()}")
    return json.loads(res.stdout)


def extract_html_scripts(html_text: str) -> Tuple[List[Dict[str, str]], List[str]]:
    """Return (external_scripts_attrs, inline_script_bodies) from built HTML."""
    external: List[Dict[str, str]] = []
    inline: List[str] = []
    tag_re = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.IGNORECASE | re.DOTALL)
    attr_re = re.compile(r'([a-zA-Z0-9_-]+)(?:\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\'=<>`]+)))?')
    for m in tag_re.finditer(html_text):
        raw_attrs, body = m.group(1), m.group(2)
        attrs: Dict[str, str] = {}
        for am in attr_re.finditer(raw_attrs):
            k = am.group(1).lower()
            v = am.group(2) if am.group(2) is not None else (am.group(3) if am.group(3) is not None else (am.group(4) or ""))
            attrs[k] = v
        if "src" in attrs:
            external.append(attrs)
        else:
            inline.append(body)
    return external, inline


_REGEX_PRECEDING_KEYWORDS = {
    "return", "case", "throw", "in", "of", "typeof", "void",
    "delete", "new", "else", "do", "yield", "await",
}
_REGEX_PRECEDING_PUNCT = set("([{,;:=!?&|^~+-*%<>")

_SWALLOWED_CODE_RE = re.compile(
    r"(?:^|\s)(?:(?:const|let|var|function|return|if|for|while)\s+[A-Za-z_$(\[]|[A-Za-z_$][\w$]*\s*\([^)]*\)\s*;)"
)


def scan_js_slash_slash_hazards(source: str) -> List[Dict[str, Any]]:
    """Stateful JS lexer detecting CLAUDE.md `//` comment traps without false positives on strings/regexes.

    Flags two classes of hazard on any line where code precedes `//`:
    1. `multi_stmt_trailing_comment`: >= 2 statements before `//` on the same line
       (i.e. a statement semicolon `;` followed by more non-whitespace code before `//`,
       or >= 2 semicolons outside `for(...)` parens before `//`).
    2. `swallowed_code_comment`: code before `//`, and the `//` comment text itself
       contains JS statement syntax (e.g. `a(); // b(); c();`).
    """
    hazards: List[Dict[str, Any]] = []
    n = len(source)
    i = 0
    line_no = 1
    # Per-line tracking
    code_before_comment = False
    semis_outside_for = 0
    saw_semi_then_code = False
    had_semi = False

    # Lexer state
    in_block_comment = False
    in_string: Optional[str] = None
    tmpl_brace_depths: List[int] = []
    brace_depth = 0
    paren_depth = 0
    for_paren_depth: Optional[int] = None
    expect_for_paren = False
    last_token_type = "start"  # 'start' | 'punct' | 'ident' | 'keyword' | 'num' | 'close'
    last_punct = ""
    last_ident = ""

    def reset_line() -> None:
        nonlocal code_before_comment, semis_outside_for, saw_semi_then_code, had_semi
        code_before_comment = False
        semis_outside_for = 0
        saw_semi_then_code = False
        had_semi = False

    def regex_allowed() -> bool:
        if last_token_type in ("start", "keyword"):
            return True
        if last_token_type == "punct":
            return last_punct in _REGEX_PRECEDING_PUNCT or last_punct == "=>"
        return False

    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            if ch == "\n":
                line_no += 1
                reset_line()
            i += 1
            continue

        if in_string is not None:
            if ch == "\\" and i + 1 < n:
                if nxt == "\n":
                    line_no += 1
                    reset_line()
                i += 2
                continue
            if in_string == "`" and ch == "$" and nxt == "{":
                tmpl_brace_depths.append(brace_depth)
                brace_depth += 1
                in_string = None
                last_token_type = "punct"
                last_punct = "{"
                i += 2
                continue
            if ch == in_string:
                in_string = None
                last_token_type = "close"
                i += 1
                continue
            if ch == "\n":
                line_no += 1
                reset_line()
            i += 1
            continue

        # Not in comment or string
        if ch == "\n":
            line_no += 1
            reset_line()
            i += 1
            continue

        if ch in " \t\r":
            i += 1
            continue

        # Block comment start
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        # Single-line comment start
        if ch == "/" and nxt == "/":
            eol = source.find("\n", i)
            if eol == -1:
                eol = n
            comment_text = source[i + 2 : eol]
            if code_before_comment:
                if saw_semi_then_code or semis_outside_for >= 2:
                    hazards.append(
                        {
                            "line": line_no,
                            "kind": "multi_stmt_trailing_comment",
                            "comment": comment_text.strip()[:120],
                        }
                    )
                elif _SWALLOWED_CODE_RE.search(comment_text):
                    hazards.append(
                        {
                            "line": line_no,
                            "kind": "swallowed_code_comment",
                            "comment": comment_text.strip()[:120],
                        }
                    )
            i = eol
            continue

        # Regex literal vs division operator
        if ch == "/" and regex_allowed():
            code_before_comment = True
            if had_semi:
                saw_semi_then_code = True
            i += 1
            in_class = False
            while i < n and source[i] != "\n":
                rc = source[i]
                if rc == "\\" and i + 1 < n:
                    i += 2
                    continue
                if rc == "[":
                    in_class = True
                elif rc == "]":
                    in_class = False
                elif rc == "/" and not in_class:
                    i += 1
                    while i < n and source[i].isalpha():
                        i += 1
                    break
                i += 1
            last_token_type = "close"
            continue

        # String or template literal
        if ch in ("'", '"', "`"):
            code_before_comment = True
            if had_semi:
                saw_semi_then_code = True
            in_string = ch
            i += 1
            continue

        # Code token
        code_before_comment = True
        if ch != ";" and had_semi:
            saw_semi_then_code = True

        if ch.isalpha() or ch in ("_", "$"):
            j = i + 1
            while j < n and (source[j].isalnum() or source[j] in ("_", "$")):
                j += 1
            ident = source[i:j]
            last_ident = ident
            if ident in _REGEX_PRECEDING_KEYWORDS:
                last_token_type = "keyword"
            else:
                last_token_type = "ident"
            expect_for_paren = ident == "for"
            i = j
            continue

        if ch.isdigit():
            j = i + 1
            while j < n and (source[j].isalnum() or source[j] in (".", "_")):
                j += 1
            last_token_type = "num"
            expect_for_paren = False
            i = j
            continue

        # Punctuation
        if ch == "{":
            brace_depth += 1
            last_token_type = "punct"
            last_punct = "{"
            expect_for_paren = False
            i += 1
            continue
        if ch == "}":
            brace_depth = max(0, brace_depth - 1)
            if tmpl_brace_depths and brace_depth == tmpl_brace_depths[-1]:
                tmpl_brace_depths.pop()
                in_string = "`"
            last_token_type = "close"
            expect_for_paren = False
            i += 1
            continue
        if ch == "(":
            if expect_for_paren:
                for_paren_depth = paren_depth
            paren_depth += 1
            expect_for_paren = False
            last_token_type = "punct"
            last_punct = "("
            i += 1
            continue
        if ch == ")":
            paren_depth = max(0, paren_depth - 1)
            if for_paren_depth is not None and paren_depth == for_paren_depth:
                for_paren_depth = None
            last_token_type = "close"
            expect_for_paren = False
            i += 1
            continue
        if ch == "]":
            last_token_type = "close"
            expect_for_paren = False
            i += 1
            continue
        if ch == ";":
            if for_paren_depth is None:
                semis_outside_for += 1
                had_semi = True
            last_token_type = "punct"
            last_punct = ";"
            expect_for_paren = False
            i += 1
            continue
        if ch == "=" and nxt == ">":
            last_token_type = "punct"
            last_punct = "=>"
            expect_for_paren = False
            i += 2
            continue

        last_token_type = "punct"
        last_punct = ch
        expect_for_paren = False
        i += 1

    return hazards


class TempWorkspace:
    """Session-scoped isolated /tmp workspace with guaranteed cleanup and dist immutability check."""

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="univers_e2e_"))
        os.chmod(self.root, 0o700)
        self.created_count = 1
        self._cleaned = False
        self.initial_dist_sha256 = sha256_file(DIST_HTML)
        self._cached_html: Optional[Path] = None
        self._cached_html_text: Optional[str] = None
        self._three_bytes: Optional[bytes] = None
        self._three_checked = False
        atexit.register(self.cleanup)

    def subdir(self, name: str) -> Path:
        p = self.root / name
        p.mkdir(parents=True, exist_ok=True)
        return p

    def build_fresh_html(
        self,
        dest: Path | str,
        cwd: Optional[Path] = None,
        extra_python_args: Sequence[str] = (),
        timeout: float = 45.0,
    ) -> CmdResult:
        cmd = [
            "python3",
            *extra_python_args,
            str(REPO_ROOT / "app" / "build.py"),
            str(dest),
        ]
        return run_cmd(cmd, cwd=cwd or REPO_ROOT, timeout=timeout)

    def build_temp_html(self) -> Path:
        if self._cached_html is not None and self._cached_html.is_file():
            return self._cached_html
        out = self.subdir("web") / "index.html"
        res = self.build_fresh_html(out)
        if res.rc != 0 or not out.is_file():
            raise RuntimeError(
                f"Failed to build session temp HTML (rc={res.rc}): {res.stderr[:500]}"
            )
        self._cached_html = out
        return out

    def temp_html_text(self) -> str:
        if self._cached_html_text is None:
            self._cached_html_text = self.build_temp_html().read_text(encoding="utf-8")
        return self._cached_html_text

    def three_min_js_bytes(self) -> Optional[bytes]:
        """Fetch Three.js once per session into temp cache and validate SHA-512 SRI."""
        if self._three_checked:
            return self._three_bytes
        self._three_checked = True
        cache_path = self.subdir("web") / "three.min.js"
        if cache_path.is_file():
            self._three_bytes = cache_path.read_bytes()
            return self._three_bytes
        html = self.temp_html_text()
        ext, _ = extract_html_scripts(html)
        three_tag = next((s for s in ext if "three" in s.get("src", "").lower()), None)
        if not three_tag:
            return None
        url = three_tag["src"]
        sri = three_tag.get("integrity", "")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "univers-e2e/1.0"})
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                data = resp.read()
            if sri.startswith("sha512-"):
                digest = base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")
                if f"sha512-{digest}" != sri:
                    return None
            cache_path.write_bytes(data)
            self._three_bytes = data
        except Exception:
            self._three_bytes = None
        return self._three_bytes

    def dist_sha256_unchanged(self) -> bool:
        return sha256_file(DIST_HTML) == self.initial_dist_sha256

    def remaining_count(self) -> int:
        return 1 if self.root.exists() else 0

    def cleanup(self) -> None:
        if not self._cleaned:
            self._cleaned = True
            shutil.rmtree(self.root, ignore_errors=True)


# Synthetic OpenNGC fixtures for XSS & custom asset override tests
EVIL_NGC_PAYLOAD = {
    "o": [
        # o[6]=null -> 4 rows so Constellation renders immediately on card open without clicking #card-more
        [
            'NGC 999901 · EvilCardGalaxy',
            'G',
            10.68,
            41.27,
            12.3,
            3.5,
            None,
            'And<img src=x onerror="window.__XSS_CARD=1">',
            None,
        ],
        # XSS in object name & type for #find-res search sink
        [
            'NGC 999902 · EvilSearch<img src=x onerror="window.__XSS_SEARCH=1">',
            'G<img src=x onerror="window.__XSS_TYPE=1">',
            12.50,
            22.10,
            13.0,
            2.1,
            None,
            'And',
            None,
        ],
        # SVG onload variant for T4-E2E-04
        [
            'NGC 999903 · EvilSvg<svg onload="window.__XSS_SVG=1">',
            'G',
            15.00,
            -10.00,
            11.5,
            2.0,
            None,
            'Ori<svg onload="window.__XSS_SVG=1">',
            None,
        ],
    ]
}

CUSTOM_NGC_PAYLOAD = {
    "o": [
        [
            "NGC 888801 · GalaxieTestAssets",
            "G",
            180.0,
            20.0,
            11.2,
            2.5,
            None,
            "Vir",
            None,
        ]
    ]
}


class LoopbackServer:
    """Thread-safe local HTTP server serving temp-built HTML + dynamic mock routes."""

    def __init__(self, workspace: TempWorkspace) -> None:
        self.workspace = workspace
        self._lock = threading.Lock()
        self._requests: List[Tuple[str, str, int]] = []
        self._httpd: Optional[http.server.ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.port: int = 0
        self._closed = False
        atexit.register(self.close)

    def start(self) -> str:
        if self._httpd is not None:
            return self.base_url
        html_path = self.workspace.build_temp_html()
        html_bytes = html_path.read_bytes()
        fusion_centres_bytes = (APP_TEST / "fusion_centres.json").read_bytes()
        fusion_images_raw = json.loads((APP_TEST / "fusion_images.json").read_text(encoding="utf-8"))
        evil_ngc_bytes = json.dumps(EVIL_NGC_PAYLOAD).encode("utf-8")
        custom_ngc_bytes = json.dumps(CUSTOM_NGC_PAYLOAD).encode("utf-8")
        server_ref = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt: str, *args: Any) -> None:
                return

            def _send(self, code: int, content_type: str, body: bytes, cors: bool = False) -> None:
                server_ref._record(self.command, self.path, code)
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                if cors:
                    self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                if self.command != "HEAD":
                    try:
                        self.wfile.write(body)
                    except (BrokenPipeError, ConnectionResetError):
                        pass

            def do_HEAD(self) -> None:
                self.do_GET()

            def do_GET(self) -> None:
                path = self.path.split("?", 1)[0]
                if path in ("/", "/index.html"):
                    self._send(200, "text/html; charset=utf-8", html_bytes)
                    return
                if path == "/mock/evil_ngc.json":
                    self._send(200, "application/json; charset=utf-8", evil_ngc_bytes, cors=True)
                    return
                if path == "/mock/custom_ngc.json":
                    self._send(200, "application/json; charset=utf-8", custom_ngc_bytes, cors=True)
                    return
                if path == "/mock/fusion_centres.json":
                    self._send(200, "application/json; charset=utf-8", fusion_centres_bytes, cors=True)
                    return
                if path == "/mock/fusion_images_404pk.json":
                    # Rewrite packet URLs to 404 loopback paths
                    mod = json.loads(json.dumps(fusion_images_raw))
                    pks = mod.get("paquets") or mod.get("packets") or []
                    for idx, pk in enumerate(pks):
                        pk["url"] = f"{server_ref.base_url}/mock/404/fusion_images_{idx}.txt"
                    self._send(200, "application/json; charset=utf-8", json.dumps(mod).encode("utf-8"), cors=True)
                    return
                if path == "/mock/evil_url_fusion_images.json":
                    mod = json.loads(json.dumps(fusion_images_raw))
                    pks = mod.get("paquets") or mod.get("packets") or []
                    for idx, pk in enumerate(pks):
                        pk["url"] = (
                            "javascript:window.__XSS_URL=1"
                            if idx % 2 == 0
                            else "data:text/html,<script>window.__XSS_URL=1</script>"
                        )
                    self._send(200, "application/json; charset=utf-8", json.dumps(mod).encode("utf-8"), cors=True)
                    return
                if path == "/mock/three.min.js":
                    tb = server_ref.workspace.three_min_js_bytes()
                    if tb is not None:
                        self._send(200, "application/javascript; charset=utf-8", tb, cors=True)
                        return
                # Everything else (/_blob/*, /mock/404/*, /x) -> 404
                self._send(404, "text/plain; charset=utf-8", b"Not Found", cors=True)

        self._httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._httpd.daemon_threads = True
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self.base_url

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def _record(self, method: str, path: str, status: int) -> None:
        with self._lock:
            self._requests.append((method, path, status))

    def snapshot_log(self) -> int:
        with self._lock:
            return len(self._requests)

    def requests_since(self, idx: int) -> List[Tuple[str, str, int]]:
        with self._lock:
            return list(self._requests[idx:])

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            if self._httpd is not None:
                try:
                    self._httpd.shutdown()
                    self._httpd.server_close()
                except Exception:
                    pass
                self._httpd = None


# Shared UI overlap / contrast helpers (aligned with app/test/ui_chevauchement.py)
UI_BLOCKS = [
    ["#place", "titre", False, None],
    ["#field", "champ", False, None],
    ["#prov", "provenance", False, None],
    ["#findp", "boutons de l’en-tête", False, "button"],
    ["#notice", "message", True, None],
    ["#card", "fiche", True, "h2, #card-sub, dt, dd, button"],
    ["#hint", "aide", True, None],
    ["#time", "barre du bas", True, "button, #date, #age, #tape, .g-speed label, #speed-out, #speed"],
    ["#scale", "échelle", False, None],
    ["#nav", "boutons de déplacement", False, "button"],
    [".panel", "panneau", True, "h2, h3, p, button, label, input, .chips, .presets"],
    ["#evt", "bandeau", True, None],
]

UI_MEASURE_JS = r"""
(blocks) => {
  const vis = el => { for (let e = el; e && e !== document.documentElement; e = e.parentElement) { const s = getComputedStyle(e); if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity < 0.05) return false; } return true; };
  const clip = (el, r) => { let a = { l: r.left, t: r.top, r: r.right, b: r.bottom }; for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) { const s = getComputedStyle(e); if (/(auto|scroll|hidden)/.test(s.overflowY + s.overflowX)) { const q = e.getBoundingClientRect(); a = { l: Math.max(a.l, q.left), t: Math.max(a.t, q.top), r: Math.min(a.r, q.right), b: Math.min(a.b, q.bottom) }; } } a = { l: Math.max(a.l, 0), t: Math.max(a.t, 0), r: Math.min(a.r, innerWidth), b: Math.min(a.b, innerHeight) }; return a.r - a.l > 1 && a.b - a.t > 1 ? [a.l, a.t, a.r, a.b] : null; };
  const out = [];
  blocks.forEach(([sel, name, opaque, inner]) => document.querySelectorAll(sel).forEach((el, k) => {
    if (!vis(el)) return; if (sel === '#evt' && el.closest('#time')) return;
    const r = clip(el, el.getBoundingClientRect()); if (!r) return; const id = sel + ':' + k;
    out.push({ id, name: name + (sel === '.panel' ? ' ' + el.id : ''), box: r, opaque, leaf: false });
    if (inner) el.querySelectorAll(inner).forEach(c => { if (!vis(c)) return; const q = clip(c, c.getBoundingClientRect()); if (q) { const path = []; for (let e = c; e !== el; e = e.parentElement) path.unshift([...e.parentElement.children].indexOf(e)); out.push({ id, name: name + ' › ' + (c.id || c.tagName.toLowerCase()) + ' « ' + (c.textContent || c.value || '').trim().slice(0, 24) + ' »', box: q, opaque: false, leaf: true, path: path.join('/') }); } });
  }));
  document.querySelectorAll('#rail .stop span, #rail .tick b').forEach(s => { if (!vis(s)) return; const q = clip(s, s.getBoundingClientRect()); if (q) out.push({ id: 'rail:' + out.length, name: 'échelle « ' + s.textContent + ' »', box: q, opaque: false, leaf: false }); });
  return out;
}
"""

UI_CUT_JS = r"""
() => { const c = document.getElementById('card'), bad = []; if (!c || getComputedStyle(c).display === 'none') return bad;
  const cr = c.getBoundingClientRect(), vp = r => r.top >= Math.max(cr.top, 0) - 1 && r.bottom <= Math.min(cr.bottom, innerHeight) + 1 && r.left >= cr.left - 1 && r.right <= cr.right + 1;
  c.querySelectorAll('.cbtn button').forEach(b => { if (getComputedStyle(b).display !== 'none' && !vp(b.getBoundingClientRect())) bad.push('bouton de fiche coupé : ' + b.textContent); });
  const dl = document.getElementById('card-dl'); if (dl.children.length) { const lh = parseFloat(getComputedStyle(dl).fontSize) * 1.4, r = dl.getBoundingClientRect(), h = Math.min(r.bottom, cr.bottom, innerHeight) - Math.max(r.top, cr.top, 0); if (h < Math.min(2 * lh, dl.scrollHeight) - 1) bad.push('liste de la fiche réduite à ' + Math.round(h) + ' px'); }
  return bad; }
"""


def compute_ui_overlaps(items: List[Dict[str, Any]], tol: float = 2.0) -> List[str]:
    bad: List[str] = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if a["id"] == b["id"]:
                if a["leaf"] != b["leaf"]:
                    continue
                if a["leaf"] and (
                    a["path"].startswith(b["path"] + "/")
                    or b["path"].startswith(a["path"] + "/")
                ):
                    continue
            elif a["leaf"] or b["leaf"]:
                continue
            A, B = a["box"], b["box"]
            w = min(A[2], B[2]) - max(A[0], B[0])
            h = min(A[3], B[3]) - max(A[1], B[1])
            if w > tol and h > tol:
                bad.append(f"{a['name']} × {b['name']} ({int(w)}×{int(h)} px)")
    return bad


def _rel_luminance(rgb: Sequence[float]) -> float:
    def ch(v: float) -> float:
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2])


def compute_card_contrast(pg: Any) -> float:
    fg, bg = pg.evaluate(
        r"""() => {
            const p = s => s.match(/[\d.]+/g).map(Number);
            const c = document.getElementById('card'), t = document.querySelector('#card dd');
            return [p(getComputedStyle(t).color), p(getComputedStyle(c).backgroundColor)];
        }"""
    )
    a = bg[3] if len(bg) > 3 else 1.0
    base = (2.0, 3.0, 10.0)
    blended = [bg[k] * a + base[k] * (1.0 - a) for k in range(3)]
    l1, l2 = sorted([_rel_luminance(fg), _rel_luminance(blended)], reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


_FONTS_RE = re.compile(r"^https?://fonts\.(googleapis|gstatic)\.com/")
_CDNJS_THREE_RE = re.compile(r"^https?://cdnjs\.cloudflare\.com/ajax/libs/three\.js/")

# Simulates standard Chromium background-tab rAF throttling (which Playwright's
# --disable-renderer-backgrounding disables) so parked cached tabs burn 0% SwiftShader CPU.
_PARK_RAF_INIT_SCRIPT = """(() => {
  const _raf = window.requestAnimationFrame.bind(window);
  let _paused = false, _q = [];
  window.requestAnimationFrame = cb => _paused ? (_q.push(cb), 0) : _raf(cb);
  window.__e2ePauseTab = p => {
    _paused = !!p;
    if (!_paused && _q.length) {
      const q = _q; _q = [];
      q.forEach(cb => _raf(cb));
    }
  };
})();"""


class PlaywrightSession:
    """Manages ONE shared Chromium SwiftShader browser for the entire E2E session."""

    def __init__(self, workspace: TempWorkspace, server: LoopbackServer) -> None:
        self.workspace = workspace
        self.server = server
        self._pw_cm: Any = None
        self._pw: Any = None
        self._browser: Any = None
        self._warm_ctx: Any = None
        self._warm_page: Any = None
        self._warm_pageerrors: List[str] = []
        self._warm_requests: List[str] = []
        self._evil_ctx: Any = None
        self._evil_page: Any = None
        self._evil_pageerrors: List[str] = []
        self._closed = False
        atexit.register(self.close)

    def _ensure_browser(self) -> Any:
        if self._browser is not None:
            return self._browser
        from playwright.sync_api import sync_playwright

        self._pw_cm = sync_playwright()
        self._pw = self._pw_cm.__enter__()
        self._browser = self._pw.chromium.launch(
            args=["--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
        )
        return self._browser

    def _attach_standard_routes(
        self,
        pg: Any,
        abort_fonts: bool = True,
        proxy_three_local: bool = True,
        block_cdnjs: bool = False,
        block_all_external: bool = False,
    ) -> None:
        if abort_fonts:
            pg.route(_FONTS_RE, lambda r: r.abort())
        if block_cdnjs:
            pg.route(_CDNJS_THREE_RE, lambda r: r.abort())
        elif proxy_three_local:
            tb = self.workspace.three_min_js_bytes()
            if tb is not None:
                pg.route(
                    _CDNJS_THREE_RE,
                    lambda r: r.fulfill(
                        status=200,
                        content_type="application/javascript; charset=utf-8",
                        headers={"Access-Control-Allow-Origin": "*"},
                        body=tb,
                    ),
                )
        if block_all_external:
            # Targeted regex matching any http(s) NOT on 127.0.0.1 / localhost (and NOT cdnjs if proxied)
            ext_re = re.compile(r"^https?://(?!(?:127\.0\.0\.1|localhost)(?::|/)|cdnjs\.cloudflare\.com/ajax/libs/three\.js/)")
            pg.route(ext_re, lambda r: r.abort())

    def wait_frames(self, pg: Any, n: int = 1, min_ms: int = 130, timeout_ms: int = 75000) -> None:
        """Advance at least `n` real animation frames and guarantee `hud()` (>110ms) refreshed."""
        pg.evaluate(
            r"""async ([n, minMs, maxMs]) => {
                const U = window.__U;
                if (!U) return 0;
                const hasPark = typeof window.__e2ePauseTab === 'function';
                if (hasPark) {
                    if (minMs > 0) await new Promise(r => setTimeout(r, minMs));
                    window.__e2ePauseTab(false);
                }
                const f0 = U.frame();
                const t0 = performance.now();
                const deadline = t0 + maxMs;
                try {
                    while (true) {
                        const f = U.frame();
                        const elapsed = performance.now() - t0;
                        if (f >= f0 + n && (hasPark || elapsed >= minMs)) {
                            return f;
                        }
                        if (performance.now() > deadline) {
                            throw new Error('wait_frames timeout after ' + maxMs + 'ms (f=' + f + ', target=' + (f0 + n) + ')');
                        }
                        await new Promise(r => setTimeout(r, 30));
                    }
                } finally {
                    if (U.Rr && U.Rr.K && U.Rr.K.orb && U.Rr.K.orb.w) {
                        try { U.Rr.K.orb.w.postMessage({ goto: 0 }); } catch (e) {}
                    }
                    if (hasPark) window.__e2ePauseTab(true);
                }
            }""",
            [int(n), int(min_ms), int(timeout_ms)],
        )

    def _set_tab_paused(self, pg: Any, paused: bool) -> None:
        if pg is None:
            return
        try:
            pg.evaluate(
                """p => {
                    if (p && window.__U && window.__U.Rr && window.__U.Rr.K && window.__U.Rr.K.orb && window.__U.Rr.K.orb.w) {
                        try { window.__U.Rr.K.orb.w.postMessage({ goto: 0 }); } catch (e) {}
                    }
                    if (window.__e2ePauseTab) window.__e2ePauseTab(p);
                }""",
                paused,
            )
        except Exception:
            pass

    def park_background_pages(self) -> None:
        self._set_tab_paused(self._warm_page, True)
        self._set_tab_paused(self._evil_page, True)

    def get_warm_desktop_page(self) -> Tuple[Any, List[str], List[str]]:
        self._set_tab_paused(self._evil_page, True)
        if self._warm_page is not None:
            return self._warm_page, self._warm_pageerrors, self._warm_requests
        base_url = self.server.start()
        browser = self._ensure_browser()
        self._warm_ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
            color_scheme="dark",
            reduced_motion="reduce",
        )
        pg = self._warm_ctx.new_page()
        pg.on("pageerror", lambda e: self._warm_pageerrors.append(str(e)))
        pg.on("request", lambda req: self._warm_requests.append(req.url))
        self._attach_standard_routes(pg, abort_fonts=True, proxy_three_local=True)
        pg.add_init_script(
            _PARK_RAF_INIT_SCRIPT
            + "\nwindow.__TIER=0; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];"
        )
        pg.goto(f"{base_url}/index.html", wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_function("window.__U && window.__U.frame() > 2", polling=200, timeout=150000)
        pg.evaluate("window.__U.S.playing = false; window.__e2ePauseTab(true);")
        self._warm_page = pg
        return pg, self._warm_pageerrors, self._warm_requests

    def reset_warm_page(self) -> Tuple[Any, int]:
        pg, errs, _ = self.get_warm_desktop_page()
        self._set_tab_paused(pg, True)
        pg.set_viewport_size({"width": 1280, "height": 800})
        pg.evaluate(
            r"""() => {
                const U = window.__U;
                U.S.playing = false;
                U.S.opts.dm = true;
                U.S.opts.comoving = false;
                U.S.opts.simWeb = false;
                U.S.opts.labels = true;
                U.S.opts.orbits = true;
                U.S.opts.lightcone = false;
                const lc = document.getElementById('c-lc');
                if (lc && lc.checked) { lc.checked = false; lc.dispatchEvent(new Event('change')); }
                const dm = document.getElementById('c-dm');
                if (dm && !dm.checked) { dm.checked = true; dm.dispatchEvent(new Event('change')); }
                if (U.S.par.H0 !== 67.4 || U.S.par.Om !== 0.315 || U.S.par.OL !== 0.685 || U.S.par.w !== -1) {
                    U.S.par.H0 = 67.4; U.S.par.Om = 0.315; U.S.par.OL = 0.685; U.S.par.w = -1;
                    U.rebuild();
                }
                U.openPanel(null);
                U.select(null);
                U.S.center = null;
                U.S.more = false;
                U.S.evCur = null;
                const tm = document.getElementById('time');
                if (tm) tm.classList.remove('open');
                const bm = document.getElementById('b-more');
                if (bm) bm.setAttribute('aria-expanded', 'false');
                const nt = document.getElementById('notice');
                if (nt) nt.classList.remove('open');
                const rl = document.getElementById('rail');
                if (rl) rl.classList.remove('show');
                const ht = document.getElementById('hint');
                if (ht) ht.hidden = true;
                U.setTime(0);
                U.S.lastTy = 0;
                U.S.T1 = 0; U.S.T2 = 0;
                U.S.solOff = 0; U.S.moonOff = 0; U.S.sOff = 0;
                U.setSpeed(20 * 86400);
                U.goStop(U.STOPS[1], true);
            }"""
        )
        self.wait_frames(pg, n=1, min_ms=130)
        return pg, len(errs)

    def get_evil_ngc_page(self) -> Tuple[Any, List[str]]:
        """Dedicated isolated context preconfigured with /mock/evil_ngc.json (shared by F4 XSS checks)."""
        self._set_tab_paused(self._warm_page, True)
        if self._evil_page is not None:
            return self._evil_page, self._evil_pageerrors
        base_url = self.server.start()
        browser = self._ensure_browser()
        self._evil_ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
            color_scheme="dark",
            reduced_motion="reduce",
        )
        pg = self._evil_ctx.new_page()
        pg.on("pageerror", lambda e: self._evil_pageerrors.append(str(e)))
        self._attach_standard_routes(pg, abort_fonts=True, proxy_three_local=True)
        pg.add_init_script(
            _PARK_RAF_INIT_SCRIPT
            + "\nwindow.__TIER=0; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[]; "
            + f"window.__NGC='{base_url}/mock/evil_ngc.json'; "
            + f"window.__ASSETS={{ ngc: '{base_url}/mock/evil_ngc.json' }};"
        )
        pg.goto(f"{base_url}/index.html", wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_function("window.__U && window.__U.frame() > 2", polling=200, timeout=150000)
        pg.evaluate("window.__U.S.playing = false; window.__e2ePauseTab(true);")
        self._evil_page = pg
        return pg, self._evil_pageerrors

    @contextmanager
    def open_isolated_page(
        self,
        *,
        viewport: Tuple[int, int] = (1280, 800),
        device_scale_factor: int = 1,
        has_touch: bool = False,
        is_mobile: bool = False,
        color_scheme: str = "dark",
        init_script: str = "window.__TIER=0; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];",
        abort_fonts: bool = True,
        proxy_three_local: bool = True,
        block_cdnjs: bool = False,
        block_all_external: bool = False,
        wait_ready: bool = True,
        extra_routes: Optional[List[Tuple[Any, Callable[[Any], None]]]] = None,
    ) -> Iterator[Tuple[Any, List[str], List[str]]]:
        self.park_background_pages()
        base_url = self.server.start()
        browser = self._ensure_browser()
        ctx = browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]},
            device_scale_factor=device_scale_factor,
            has_touch=has_touch,
            is_mobile=is_mobile,
            color_scheme=color_scheme,
            reduced_motion="reduce",
        )
        pg = ctx.new_page()
        pageerrors: List[str] = []
        requests: List[str] = []
        pg.on("pageerror", lambda e: pageerrors.append(str(e)))
        pg.on("request", lambda req: requests.append(req.url))
        try:
            self._attach_standard_routes(
                pg,
                abort_fonts=abort_fonts,
                proxy_three_local=proxy_three_local,
                block_cdnjs=block_cdnjs,
                block_all_external=block_all_external,
            )
            if extra_routes:
                for pattern, handler in extra_routes:
                    pg.route(pattern, handler)
            if init_script:
                pg.add_init_script(init_script)
            pg.goto(f"{base_url}/index.html", wait_until="domcontentloaded", timeout=90000)
            if wait_ready:
                pg.wait_for_function("window.__U && window.__U.frame() > 2", polling=200, timeout=150000)
                pg.evaluate("window.__U.S.playing = false;")
                self.wait_frames(pg, n=1, min_ms=130)
            yield pg, pageerrors, requests
        finally:
            try:
                ctx.close()
            except Exception:
                pass

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for obj, meth in (
            (self._evil_ctx, "close"),
            (self._warm_ctx, "close"),
            (self._browser, "close"),
        ):
            if obj is not None:
                try:
                    getattr(obj, meth)()
                except Exception:
                    pass
        if self._pw_cm is not None:
            try:
                self._pw_cm.__exit__(None, None, None)
            except Exception:
                pass
        self._evil_page = None
        self._evil_ctx = None
        self._warm_page = None
        self._warm_ctx = None
        self._browser = None
        self._pw = None
        self._pw_cm = None


class E2ESession:
    """Shared session state injected into every test case."""

    def __init__(self) -> None:
        self.workspace = TempWorkspace()
        self.server = LoopbackServer(self.workspace)
        self.pw = PlaywrightSession(self.workspace, self.server)
        from .cpp_cache import CppCache

        self.cpp = CppCache(self.workspace)

    def close(self) -> None:
        try:
            self.pw.close()
        finally:
            try:
                self.server.close()
            finally:
                self.workspace.cleanup()
