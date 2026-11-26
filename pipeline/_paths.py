"""Résolution centralisée des chemins du dépôt, des données brutes, de DATA et de TILE_MANIFEST.

Module 100 % bibliothèque standard garantissant l'indépendance vis-à-vis du répertoire courant (CWD)
et l'absence de chemins codés en dur spécifiques à une machine ou à un système d'exploitation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re

PIPELINE_DIR: Path = Path(__file__).resolve().parent
REPO_ROOT: Path = PIPELINE_DIR.parent
APP_DIR: Path = REPO_ROOT / 'app'
APP_GEN: Path = APP_DIR / 'gen'
APP_SRC: Path = APP_DIR / 'src'
APP_TEST: Path = APP_DIR / 'test'
PIPELINE_RAW: Path = PIPELINE_DIR / 'raw'
PIPELINE_REF: Path = PIPELINE_DIR / 'ref'

# Clés héritées de data2.js écrasées par des modules plus récents (aligné sur app/build.py).
RETIRE_DATA2: frozenset[str] = frozenset((
    'STARS_N',
    'STARS_GEO',
    'STARS_AUX',
    'STAR_LABELS',
    'CMB',
))


def raw_dir(cli_arg: str | os.PathLike[str] | None = None) -> Path:
    """Résout le dossier externe de données brutes (univers-raw) :
    1. argument CLI explicite (cli_arg) s'il est fourni et non vide ;
    2. variable d'environnement UNIVERS_RAW si définie et non vide ;
    3. repli portable : <racine_du_dépôt>/univers-raw.
    """
    if cli_arg is not None:
        text = os.fspath(cli_arg).strip()
        if text:
            return Path(text).expanduser()
    env = os.environ.get('UNIVERS_RAW', '').strip()
    if env:
        return Path(env).expanduser()
    return REPO_ROOT / 'univers-raw'


_TILES_MARKER = '/*__TILES__*/'
_REGEX_PREFIX_KW: frozenset[str] = frozenset((
    'return', 'case', 'throw', 'in', 'instanceof', 'typeof',
    'void', 'delete', 'new', 'else', 'do', 'of', 'yield', 'await',
))
_DATA_DECL_RE = re.compile(r'(?:const|let|var)\s+DATA\s*=')
_DATA_ASSIGN_RE = re.compile(
    r'Object\.assign\s*\(\s*DATA(?:\.([A-Za-z_$][A-Za-z0-9_$]*))?\s*,'
)
_IDENT_RE = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')

_JS_TOK_RE = re.compile(
    r"""
    (?P<ws>\s+)
    | (?P<comment>//[^\n]*|/\*.*?\*/)
    | (?P<dstr>"(?:\\.|[^"\\])*")
    | (?P<sstr>'(?:\\.|[^'\\])*')
    | (?P<num>-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)
    | (?P<ident>[A-Za-z_$][A-Za-z0-9_$]*)
    | (?P<punct>[\[\]{}:,])
    """,
    re.VERBOSE | re.S,
)


def _skip_ws_and_comments(text: str, pos: int) -> int:
    """Avance au-delà des espaces, commentaires // et commentaires /* ... */."""
    n = len(text)
    while pos < n:
        ch = text[pos]
        if ch.isspace():
            pos += 1
        elif ch == '/' and pos + 1 < n and text[pos + 1] == '/':
            nl = text.find('\n', pos + 2)
            pos = n if nl == -1 else nl + 1
        elif ch == '/' and pos + 1 < n and text[pos + 1] == '*':
            end = text.find('*/', pos + 2)
            if end == -1:
                raise ValueError("Commentaire /* non fermé")
            pos = end + 2
        else:
            break
    return pos


def _skip_js_string(text: str, pos: int) -> int:
    """Avance au-delà d'une chaîne JS délimitée par ' ou \" en respectant les échappements."""
    quote = text[pos]
    pos += 1
    n = len(text)
    while pos < n:
        ch = text[pos]
        if ch == '\\':
            pos += 2
        elif ch == quote:
            return pos + 1
        elif ch in ('\n', '\r'):
            return pos + 1
        else:
            pos += 1
    return n


def _scan_template_part(text: str, pos: int) -> tuple[int, bool]:
    """Scanne un segment de template literal JS depuis le caractère suivant ` ou }.

    Renvoie (nouvelle_pos, True) si '${' est atteint, sinon (nouvelle_pos, False) après '`' ou EOF.
    """
    n = len(text)
    while pos < n:
        ch = text[pos]
        if ch == '\\':
            pos += 2
        elif ch == '`':
            return pos + 1, False
        elif ch == '$' and pos + 1 < n and text[pos + 1] == '{':
            return pos + 2, True
        else:
            pos += 1
    return n, False


def _skip_js_regex(text: str, pos: int) -> int:
    """Avance au-delà d'un littéral d'expression régulière JS /.../flags ; repli sur pos+1 sinon."""
    n = len(text)
    i = pos + 1
    in_class = False
    while i < n:
        ch = text[i]
        if ch == '\\':
            if i + 1 >= n or text[i + 1] in ('\n', '\r'):
                return pos + 1
            i += 2
            continue
        if ch in ('\n', '\r'):
            return pos + 1
        if ch == '[':
            in_class = True
        elif ch == ']' and in_class:
            in_class = False
        elif ch == '/' and not in_class:
            i += 1
            while i < n and text[i].isalpha():
                i += 1
            return i
        i += 1
    return pos + 1


def _extract_delimited_block(
    text: str,
    start: int,
    open_ch: str = '[',
    close_ch: str = ']',
) -> tuple[str, int]:
    if start < 0 or start >= len(text) or text[start] != open_ch:
        raise ValueError(f"Attendu {open_ch!r} à l'index {start}")
    n, i, depth, quote = len(text), start, 0, None
    while i < n:
        ch = text[i]
        if quote is not None:
            if ch == '\\':
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch == '/' and i + 1 < n:
            nxt = text[i + 1]
            if nxt == '/':
                nl = text.find('\n', i + 2)
                i = n if nl == -1 else nl + 1
                continue
            if nxt == '*':
                end = text.find('*/', i + 2)
                if end == -1:
                    raise ValueError("Commentaire /* non fermé dans le littéral JS")
                i = end + 2
                continue
        if ch in ("'", '"'):
            quote = ch
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1], i + 1
        i += 1
    raise ValueError(f"Délimiteur {open_ch!r} non fermé dans le littéral JS")


def _extract_bracket_block(text: str, start: int) -> str:
    return _extract_delimited_block(text, start, '[', ']')[0]


def _decode_js_single_string(raw: str) -> str:
    inner = re.sub(
        r'\\(.)|(")',
        lambda m: '\\"' if m.group(2) else ("'" if m.group(1) == "'" else '\\' + m.group(1)),
        raw[1:-1],
        flags=re.S,
    )
    return json.loads('"' + inner + '"')


def _decode_js_double_string(raw: str) -> str:
    inner = re.sub(
        r'\\(.)',
        lambda m: "'" if m.group(1) == "'" else '\\' + m.group(1),
        raw[1:-1],
        flags=re.S,
    )
    return json.loads('"' + inner + '"')


def _parse_js_literal(text: str):
    tokens: list[tuple[str, str]] = []
    pos, n = 0, len(text)
    while pos < n:
        m = _JS_TOK_RE.match(text, pos)
        if not m:
            raise ValueError(f"Jeton JS inattendu à l'offset {pos}: {text[pos:pos + 24]!r}")
        kind, val = m.lastgroup, m.group()
        pos = m.end()
        if kind not in ('ws', 'comment'):
            tokens.append((kind, val))

    idx = 0

    def peek() -> tuple[str | None, str | None]:
        return tokens[idx] if idx < len(tokens) else (None, None)

    def take() -> tuple[str, str]:
        nonlocal idx
        if idx >= len(tokens):
            raise ValueError("Fin inattendue de TILE_MANIFEST")
        tok = tokens[idx]
        idx += 1
        return tok

    def parse_val():
        kind, val = peek()
        if kind == 'punct' and val == '[':
            take()
            arr = []
            while True:
                k2, v2 = peek()
                if k2 == 'punct' and v2 == ']':
                    take()
                    return arr
                arr.append(parse_val())
                k2, v2 = peek()
                if k2 == 'punct' and v2 == ',':
                    take()
                elif k2 == 'punct' and v2 == ']':
                    take()
                    return arr
                else:
                    raise ValueError(f"Attendu ',' ou ']' dans tableau, reçu {v2!r}")
        if kind == 'punct' and val == '{':
            take()
            obj = {}
            while True:
                k2, v2 = peek()
                if k2 == 'punct' and v2 == '}':
                    take()
                    return obj
                if k2 == 'ident':
                    take()
                    key = v2
                elif k2 == 'dstr':
                    take()
                    key = _decode_js_double_string(v2)
                elif k2 == 'sstr':
                    take()
                    key = _decode_js_single_string(v2)
                else:
                    raise ValueError(f"Clé d'objet attendue, reçu {k2}={v2!r}")
                ck, cv = take()
                if ck != 'punct' or cv != ':':
                    raise ValueError(f"':' attendu après {key!r}, reçu {cv!r}")
                obj[key] = parse_val()
                k2, v2 = peek()
                if k2 == 'punct' and v2 == ',':
                    take()
                elif k2 == 'punct' and v2 == '}':
                    take()
                    return obj
                else:
                    raise ValueError(f"Attendu ',' ou '}}' dans objet, reçu {v2!r}")
        if kind == 'dstr':
            take()
            return _decode_js_double_string(val)
        if kind == 'sstr':
            take()
            return _decode_js_single_string(val)
        if kind == 'num':
            take()
            return int(val) if re.fullmatch(r'-?\d+', val) else float(val)
        if kind == 'ident':
            take()
            if val == 'true':
                return True
            if val == 'false':
                return False
            if val == 'null':
                return None
            raise ValueError(f"Identifiant JS non littéral : {val!r}")
        raise ValueError(f"Valeur attendue, reçu {kind}={val!r}")

    res = parse_val()
    if idx != len(tokens):
        raise ValueError(f"Jetons superflus après la valeur : {tokens[idx]!r}")
    return res


def _decode_js_object(text: str, brace_idx: int, decoder: json.JSONDecoder) -> tuple[dict, int]:
    try:
        obj, end_idx = decoder.raw_decode(text, brace_idx)
    except json.JSONDecodeError:
        raw_obj, end_idx = _extract_delimited_block(text, brace_idx, '{', '}')
        obj = _parse_js_literal(raw_obj)
    if not isinstance(obj, dict):
        raise ValueError(f"Objet JSON/JS attendu à l'offset {brace_idx}")
    return obj, end_idx


def _iter_data_assignments(text: str, decoder: json.JSONDecoder):
    """Itère les affectations DATA de premier niveau :
    - `const DATA = {...}`
    - `Object.assign(DATA, {...})`
    - `Object.assign(DATA.<subkey>, {...})`

    Ignore BOM UTF-8, espaces, commentaires JS et chaînes littérales, et saute directement
    au-delà de chaque objet JSON/JS décodé afin de ne jamais scanner l'intérieur d'une valeur.
    """
    n = len(text)
    pos = 1 if text.startswith('\ufeff') else 0
    template_braces: list[int] = []
    while pos < n:
        pos = _skip_ws_and_comments(text, pos)
        if pos >= n:
            break
        ch = text[pos]
        if ch in ("'", '"'):
            pos = _skip_js_string(text, pos)
            continue
        if ch == '`':
            pos, in_expr = _scan_template_part(text, pos + 1)
            if in_expr:
                template_braces.append(0)
            continue
        if template_braces:
            if ch == '{':
                template_braces[-1] += 1
                pos += 1
                continue
            if ch == '}':
                if template_braces[-1] == 0:
                    template_braces.pop()
                    pos, in_expr = _scan_template_part(text, pos + 1)
                    if in_expr:
                        template_braces.append(0)
                else:
                    template_braces[-1] -= 1
                    pos += 1
                continue

        m = _DATA_DECL_RE.match(text, pos)
        if m:
            val_pos = _skip_ws_and_comments(text, m.end())
            if val_pos < n and text[val_pos] == '{':
                obj, end_idx = _decode_js_object(text, val_pos, decoder)
                yield None, obj
                pos = end_idx
                continue

        m = _DATA_ASSIGN_RE.match(text, pos)
        if m:
            subkey = m.group(1)
            cur = m.end()
            while True:
                val_pos = _skip_ws_and_comments(text, cur)
                if val_pos >= n or text[val_pos] != '{':
                    break
                obj, end_idx = _decode_js_object(text, val_pos, decoder)
                yield subkey, obj
                cur = _skip_ws_and_comments(text, end_idx)
                if cur < n and text[cur] == ',':
                    cur += 1
                    continue
                break
            pos = cur
            continue

        if ch.isalpha() or ch in '_$':
            m_id = _IDENT_RE.match(text, pos)
            pos = m_id.end() if m_id else pos + 1
            continue
        pos += 1


def data_keys(keys, gen_dir: str | os.PathLike[str] | None = None) -> dict:
    """Lit des clés de DATA dans app/gen/data*.js dans l'ordre exact de app/build.py.

    Parse structurellement les affectations de premier niveau (`const DATA = {...}`,
    `Object.assign(DATA, {...})`, `Object.assign(DATA.<clé>, {...})`) sans jamais
    confondre une clé imbriquée, un commentaire ou une chaîne littérale avec une clé DATA.
    Ignore les clés RETIRE_DATA2 dans data2.js afin de rester 100 % idempotent quel que soit
    le sous-ensemble (0..5) de ces clés encore présent dans data2.js.
    """
    keys = tuple(keys)
    gen_path = Path(APP_GEN if gen_dir is None else gen_dir)
    files: list[tuple[int, Path]] = []
    for path in gen_path.glob('data*.js'):
        m = re.fullmatch(r'data(\d*)\.js', path.name)
        if m:
            files.append((int(m.group(1) or 1), path))
    files.sort(key=lambda pair: pair[0])

    decoder = json.JSONDecoder()
    out: dict = {}
    for _, path in files:
        is_data2 = path.name == 'data2.js'
        wanted = [k for k in keys if not (is_data2 and k in RETIRE_DATA2)]
        if not wanted:
            continue
        s = path.read_text(encoding='utf-8')
        if not any(f'"{k}"' in s or f"'{k}'" in s or f'DATA.{k}' in s for k in wanted):
            continue
        wanted_set = set(wanted)
        for subkey, obj in _iter_data_assignments(s, decoder):
            if subkey is None:
                for k in wanted:
                    if k in obj:
                        out[k] = obj[k]
            elif subkey in wanted_set:
                if isinstance(out.get(subkey), dict):
                    out[subkey] = {**out[subkey], **obj}
                else:
                    out[subkey] = obj

    missing = [k for k in keys if k not in out]
    if missing:
        raise SystemExit(f'clés absentes de {gen_path} : {missing}')
    return out


def _find_tiles_array_start(text: str) -> int | None:
    """Localise l'index du '[' suivant un jeton authentique /*__TILES__*/ hors chaînes et commentaires."""
    if _TILES_MARKER not in text:
        return None
    n = len(text)
    i = 1 if text.startswith('\ufeff') else 0
    regex_allowed = True
    after_dot = False
    template_braces: list[int] = []

    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in ("'", '"'):
            i = _skip_js_string(text, i)
            regex_allowed = False
            after_dot = False
            continue
        if ch == '`':
            i, in_expr = _scan_template_part(text, i + 1)
            if in_expr:
                template_braces.append(0)
                regex_allowed = True
            else:
                regex_allowed = False
            after_dot = False
            continue
        if ch == '/' and i + 1 < n:
            nxt = text[i + 1]
            if nxt == '/':
                nl = text.find('\n', i + 2)
                i = n if nl == -1 else nl + 1
                continue
            if nxt == '*':
                if text.startswith(_TILES_MARKER, i):
                    after = _skip_ws_and_comments(text, i + len(_TILES_MARKER))
                    if after < n and text[after] == '[':
                        return after
                    i += len(_TILES_MARKER)
                    continue
                end = text.find('*/', i + 2)
                if end == -1:
                    return None
                i = end + 2
                continue
            if regex_allowed:
                i = _skip_js_regex(text, i)
                regex_allowed = False
                after_dot = False
            else:
                i += 1
                regex_allowed = True
                after_dot = False
            continue
        if ch == '{' and template_braces:
            template_braces[-1] += 1
            regex_allowed = True
            after_dot = False
            i += 1
            continue
        if ch == '}' and template_braces:
            if template_braces[-1] == 0:
                template_braces.pop()
                i, in_expr = _scan_template_part(text, i + 1)
                if in_expr:
                    template_braces.append(0)
                    regex_allowed = True
                else:
                    regex_allowed = False
                after_dot = False
                continue
            template_braces[-1] -= 1
            regex_allowed = True
            after_dot = False
            i += 1
            continue
        if ch.isalpha() or ch in '_$':
            m_id = _IDENT_RE.match(text, i)
            j = m_id.end() if m_id else i + 1
            word = text[i:j]
            regex_allowed = (not after_dot) and (word in _REGEX_PREFIX_KW)
            after_dot = False
            i = j
            continue
        if ch.isdigit():
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] in '._'):
                j += 1
            regex_allowed = False
            after_dot = False
            i = j
            continue
        if ch == '.':
            after_dot = True
            regex_allowed = False
        elif ch in ')]':
            after_dot = False
            regex_allowed = False
        else:
            after_dot = False
            regex_allowed = True
        i += 1
    return None


def read_tile_manifest(app_src_dir: str | os.PathLike[str] | None = None) -> list[dict]:
    """Localise et décode le tableau littéral marqué /*__TILES__*/ dans app/src/6*.js.

    Résiste au formatage Prettier (espaces/retours ligne, guillemets simples ou doubles,
    virgules finales, commentaires, tableaux imbriqués), aux commentaires ou chaînes
    mentionnant /*__TILES__*/ en amont, ainsi qu'au découpage de 60_app.js.
    """
    src_dir = Path(APP_SRC if app_src_dir is None else app_src_dir)
    for path in sorted(src_dir.glob('6*.js')):
        text = path.read_text(encoding='utf-8')
        arr_start = _find_tiles_array_start(text)
        if arr_start is not None:
            raw_array = _extract_bracket_block(text, arr_start)
            data = _parse_js_literal(raw_array)
            if not isinstance(data, list):
                raise ValueError(f"TILE_MANIFEST dans {path} n'est pas une liste")
            return data
    raise FileNotFoundError(f"Marqueur /*__TILES__*/ introuvable dans {src_dir}/6*.js")
