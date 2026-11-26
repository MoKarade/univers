#!/usr/bin/env python3
"""Tests unitaires 100 % stdlib du pipeline (0 dépendance tierce, 0 réseau, 0 données brutes).

Exécutable depuis n'importe quel répertoire courant :
  python3 pipeline/test_pipeline_stdlib.py
"""
import ast
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 : tomli optionnel, sinon parseur stdlib interne
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]


_TOML_BARE_KEY_RE = re.compile(r'[A-Za-z0-9_-]+')


def _loads_toml_stdlib(text: str) -> dict:
    """Parseur TOML strict (sous-ensemble PEP 621 : tables, chaînes, listes de chaînes, commentaires).

    Utilisé uniquement en repli sous Python 3.10 lorsque ni tomllib ni tomli ne sont disponibles.
    """
    if text.startswith('\ufeff'):
        text = text[1:]
    n = len(text)

    def skip_ws_inline(pos: int) -> int:
        while pos < n and text[pos] in (' ', '\t'):
            pos += 1
        return pos

    def skip_ws_and_comments(pos: int) -> int:
        while pos < n:
            ch = text[pos]
            if ch in (' ', '\t', '\r', '\n'):
                pos += 1
            elif ch == '#':
                nl = text.find('\n', pos + 1)
                pos = n if nl == -1 else nl + 1
            else:
                break
        return pos

    def skip_eol(pos: int) -> int:
        pos = skip_ws_inline(pos)
        if pos < n and text[pos] == '#':
            nl = text.find('\n', pos + 1)
            return n if nl == -1 else nl + 1
        if pos == n:
            return n
        if text[pos] == '\r':
            pos += 1
        if pos < n and text[pos] == '\n':
            return pos + 1
        raise ValueError(f"Contenu inattendu en fin de ligne TOML à l'offset {pos}: {text[pos:pos + 20]!r}")

    def parse_bare_key(pos: int) -> tuple[str, int]:
        m = _TOML_BARE_KEY_RE.match(text, pos)
        if not m:
            raise ValueError(f"Clé TOML attendue à l'offset {pos}: {text[pos:pos + 20]!r}")
        return m.group(), m.end()

    def parse_basic_string(pos: int) -> tuple[str, int]:
        if pos >= n or text[pos] != '"':
            raise ValueError(f"Chaîne TOML attendue à l'offset {pos}")
        i = pos + 1
        while i < n:
            ch = text[i]
            if ch == '\\':
                if i + 1 >= n or text[i + 1] in ('\r', '\n'):
                    raise ValueError(f"Échappement TOML invalide à l'offset {i}")
                i += 2
            elif ch == '"':
                raw = text[pos : i + 1]
                return json.loads(raw), i + 1
            elif ch in ('\r', '\n'):
                raise ValueError(f"Chaîne TOML non fermée avant fin de ligne à l'offset {pos}")
            else:
                i += 1
        raise ValueError(f"Chaîne TOML non fermée à l'offset {pos}")

    def parse_value(pos: int):
        if pos >= n:
            raise ValueError("Fin de fichier inattendue lors de la lecture d'une valeur TOML")
        ch = text[pos]
        if ch == '"':
            return parse_basic_string(pos)
        if ch == '[':
            pos += 1
            items = []
            while True:
                pos = skip_ws_and_comments(pos)
                if pos >= n:
                    raise ValueError("Tableau TOML non fermé")
                if text[pos] == ']':
                    return items, pos + 1
                val, pos = parse_value(pos)
                items.append(val)
                pos = skip_ws_and_comments(pos)
                if pos >= n:
                    raise ValueError("Tableau TOML non fermé")
                if text[pos] == ',':
                    pos += 1
                    continue
                if text[pos] == ']':
                    return items, pos + 1
                raise ValueError(f"Attendu ',' ou ']' dans tableau TOML à l'offset {pos}")
        raise ValueError(f"Valeur TOML non supportée ou invalide à l'offset {pos}: {text[pos:pos + 20]!r}")

    root: dict = {}
    current = root
    defined_tables: set[tuple[str, ...]] = set()
    pos = 0
    while True:
        pos = skip_ws_and_comments(pos)
        if pos >= n:
            break
        if text[pos] == '[':
            pos += 1
            parts: list[str] = []
            while True:
                pos = skip_ws_inline(pos)
                part, pos = parse_bare_key(pos)
                parts.append(part)
                pos = skip_ws_inline(pos)
                if pos < n and text[pos] == '.':
                    pos += 1
                    continue
                break
            if pos >= n or text[pos] != ']':
                raise ValueError(f"En-tête de table TOML non fermé à l'offset {pos}")
            pos = skip_eol(pos + 1)
            tkey = tuple(parts)
            if tkey in defined_tables:
                raise ValueError(f"Table TOML dupliquée : {'.'.join(parts)}")
            defined_tables.add(tkey)
            node = root
            for part in parts:
                existing = node.get(part)
                if existing is None:
                    existing = {}
                    node[part] = existing
                elif not isinstance(existing, dict):
                    raise ValueError(f"Conflit clé/table TOML sur {part!r}")
                node = existing
            current = node
        else:
            key, pos = parse_bare_key(pos)
            pos = skip_ws_inline(pos)
            if pos >= n or text[pos] != '=':
                raise ValueError(f"'=' attendu après la clé TOML {key!r} à l'offset {pos}")
            pos = skip_ws_inline(pos + 1)
            if pos >= n or text[pos] in ('\r', '\n', '#'):
                raise ValueError(f"Valeur TOML manquante pour la clé {key!r}")
            val, pos = parse_value(pos)
            pos = skip_eol(pos)
            if key in current:
                raise ValueError(f"Clé TOML dupliquée : {key!r}")
            current[key] = val
    return root


def _load_toml_text(text: str) -> dict:
    if tomllib is not None:
        return tomllib.loads(text)
    return _loads_toml_stdlib(text)

PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parent
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

import _paths  # noqa: E402


def _load_module(name: str, path: Path, stubs: dict | None = None):
    """Charge un module Python par chemin avec stubs temporaires dans sys.modules."""
    saved = {}
    try:
        if stubs:
            for mod_name, mod_obj in stubs.items():
                saved[mod_name] = sys.modules.get(mod_name)
                sys.modules[mod_name] = mod_obj
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if stubs:
            for mod_name, prev in saved.items():
                if prev is None:
                    sys.modules.pop(mod_name, None)
                else:
                    sys.modules[mod_name] = prev


def _bare_open_calls(path: Path) -> list[int]:
    """Renvoie les numéros de ligne des appels open(...) qui ne sont pas gérés par un bloc with."""
    tree = ast.parse(path.read_text(encoding='utf-8'), str(path))
    managed_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if isinstance(item.context_expr, ast.Call):
                    managed_ids.add(id(item.context_expr))
    bare = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'open':
            if id(node) not in managed_ids:
                bare.append(node.lineno)
    return sorted(bare)


class TestPaths(unittest.TestCase):
    def test_constants(self):
        self.assertTrue(_paths.REPO_ROOT.is_absolute())
        self.assertEqual(_paths.REPO_ROOT, REPO_ROOT)
        self.assertEqual(_paths.PIPELINE_DIR, PIPELINE_DIR)
        self.assertEqual(_paths.APP_DIR, REPO_ROOT / 'app')
        self.assertEqual(_paths.APP_GEN, REPO_ROOT / 'app' / 'gen')
        self.assertEqual(_paths.APP_SRC, REPO_ROOT / 'app' / 'src')
        self.assertEqual(_paths.APP_TEST, REPO_ROOT / 'app' / 'test')
        self.assertEqual(_paths.PIPELINE_RAW, PIPELINE_DIR / 'raw')
        self.assertEqual(_paths.PIPELINE_REF, PIPELINE_DIR / 'ref')
        self.assertTrue((_paths.REPO_ROOT / 'app' / 'build.py').is_file())
        self.assertTrue(_paths.APP_GEN.is_dir())
        self.assertTrue(_paths.APP_SRC.is_dir())
        self.assertEqual(
            _paths.RETIRE_DATA2,
            frozenset(('STARS_N', 'STARS_GEO', 'STARS_AUX', 'STAR_LABELS', 'CMB')),
        )

    def test_raw_dir_precedence_and_empty_env(self):
        base = Path(tempfile.gettempdir())
        env_raw = str(base / 'univers_env_raw')
        cli_raw = str(base / 'univers_cli_raw')
        path_arg = base / 'univers_path_arg'

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('UNIVERS_RAW', None)
            self.assertEqual(_paths.raw_dir(), REPO_ROOT / 'univers-raw')
            self.assertEqual(_paths.raw_dir(None), REPO_ROOT / 'univers-raw')
            self.assertEqual(_paths.raw_dir(''), REPO_ROOT / 'univers-raw')
            self.assertEqual(_paths.raw_dir('   '), REPO_ROOT / 'univers-raw')

        with mock.patch.dict(os.environ, {'UNIVERS_RAW': ''}, clear=False):
            self.assertEqual(_paths.raw_dir(), REPO_ROOT / 'univers-raw')

        with mock.patch.dict(os.environ, {'UNIVERS_RAW': '   '}, clear=False):
            self.assertEqual(_paths.raw_dir(), REPO_ROOT / 'univers-raw')

        with mock.patch.dict(os.environ, {'UNIVERS_RAW': env_raw}, clear=False):
            self.assertEqual(_paths.raw_dir(), Path(env_raw))
            self.assertEqual(_paths.raw_dir(''), Path(env_raw))
            self.assertEqual(_paths.raw_dir('   '), Path(env_raw))
            self.assertEqual(_paths.raw_dir(cli_raw), Path(cli_raw))
            self.assertEqual(_paths.raw_dir(path_arg), path_arg)


class TestReadTileManifest(unittest.TestCase):
    def test_real_app_src(self):
        entries = _paths.read_tile_manifest()
        self.assertIsInstance(entries, list)
        self.assertEqual(len(entries), 10)
        by_kind = {'ast': [], 'star': [], 'gal': []}
        for e in entries:
            self.assertIsInstance(e, dict)
            self.assertIn(e['kind'], by_kind)
            self.assertRegex(e['id'], r'^[0-9a-f]{32}$')
            self.assertIsInstance(e['n'], int)
            self.assertGreater(e['n'], 0)
            by_kind[e['kind']].append(e)
        self.assertEqual(len(by_kind['ast']), 1)
        self.assertEqual(by_kind['ast'][0]['n'], 123530)
        self.assertRegex(by_kind['ast'][0]['names'], r'^[0-9a-f]{32}$')
        self.assertEqual(len(by_kind['star']), 6)
        self.assertEqual(sum(e['n'] for e in by_kind['star']), 5894644)
        self.assertEqual(len(by_kind['gal']), 3)
        self.assertEqual(sum(e['n'] for e in by_kind['gal']), 5110243)

    def test_synthetic_prettier_multiline_60_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            js = """
            const TILE_MANIFEST = /*__TILES__*/
            [
              // commentaire contenant ] et {
              {
                kind: "ast",
                id: "0123456789abcdef0123456789abcdef",
                n: 42,
                mb: 1.5,
                names: "fedcba9876543210fedcba9876543210",
                note: 'l\\'astéroïde "test" [1]',
              },
              /* bloc avec ] dedans */
              {
                "kind": 'star',
                'id': "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                n: 1300000,
                g: [9.5, 11.8],
                active: true,
                extra: null,
              },
            ];
            """
            (Path(tmp) / '60_app.js').write_text(js, encoding='utf-8')
            entries = _paths.read_tile_manifest(tmp)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]['kind'], 'ast')
            self.assertEqual(entries[0]['n'], 42)
            self.assertEqual(entries[0]['mb'], 1.5)
            self.assertEqual(entries[0]['names'], 'fedcba9876543210fedcba9876543210')
            self.assertEqual(entries[0]['note'], 'l\'astéroïde "test" [1]')
            self.assertEqual(entries[1]['kind'], 'star')
            self.assertEqual(entries[1]['g'], [9.5, 11.8])
            self.assertIs(entries[1]['active'], True)
            self.assertIsNone(entries[1]['extra'])

    def test_synthetic_split_60_state_and_61_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '60_state.js').write_text('const S = { t: 0 };\n', encoding='utf-8')
            (Path(tmp) / '61_assets.js').write_text(
                "const ASSETS = {\n  tiles: /*__TILES__*/ [\n"
                "    { kind: 'gal', id: 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', n: 99, mb: 0.4, },\n"
                "  ],\n};\n",
                encoding='utf-8',
            )
            entries = _paths.read_tile_manifest(tmp)
            self.assertEqual(entries, [{'kind': 'gal', 'id': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'n': 99, 'mb': 0.4}])

    def test_errors_missing_and_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                _paths.read_tile_manifest(tmp)
            (Path(tmp) / '60_state.js').write_text('const x = 1;\n', encoding='utf-8')
            with self.assertRaises(FileNotFoundError):
                _paths.read_tile_manifest(tmp)

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '60_app.js').write_text('const T = /*__TILES__*/ [{ kind: badIdent }];', encoding='utf-8')
            with self.assertRaises(ValueError):
                _paths.read_tile_manifest(tmp)

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '60_app.js').write_text('const T = /*__TILES__*/ [{ kind: "star" ', encoding='utf-8')
            with self.assertRaises(ValueError):
                _paths.read_tile_manifest(tmp)

    def test_ignores_marker_in_comments_strings_templates_and_regex(self):
        # 1. Commentaire // en amont dans le même fichier
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '60_app.js').write_text(
                "// Format: /*__TILES__*/ [{ kind: ... }]\n"
                "const T = /*__TILES__*/ [{ kind: 'star', n: 5 }];\n",
                encoding='utf-8',
            )
            self.assertEqual(_paths.read_tile_manifest(tmp), [{'kind': 'star', 'n': 5}])

        # 2. Commentaire // dans 60_state.js et vrai marqueur dans 61_assets.js
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '60_state.js').write_text(
                "// Format: /*__TILES__*/ [{ kind: ... }]\n",
                encoding='utf-8',
            )
            (Path(tmp) / '61_assets.js').write_text(
                "const T = /*__TILES__*/ [{ kind: 'star', n: 5 }];\n",
                encoding='utf-8',
            )
            self.assertEqual(_paths.read_tile_manifest(tmp), [{'kind': 'star', 'n': 5}])

        # 3. Commentaires intercalés entre /*__TILES__*/ et [
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '60_app.js').write_text(
                "const T = /*__TILES__*/ /* generated */ // note\n [{ kind: 'star', n: 5 }];\n",
                encoding='utf-8',
            )
            self.assertEqual(_paths.read_tile_manifest(tmp), [{'kind': 'star', 'n': 5}])

        # 4. Chaînes, template literals et regex contenant guillemets / marqueur avant le vrai tableau
        with tempfile.TemporaryDirectory() as tmp:
            js = (
                "const s1 = '/*__TILES__*/ [bad]';\n"
                'const s2 = "/*__TILES__*/ [bad2]";\n'
                "const s3 = `doc ${'/*__TILES__*/ [bad3]'} /*__TILES__*/ [bad4]`;\n"
                r"const esc = s => s.replace(/[&<>\"']/g, c => c).replace(/'/g, '&#39;');" + "\n"
                "const T = /*__TILES__*/ [{ kind: 'star', n: 5 }];\n"
            )
            (Path(tmp) / '60_app.js').write_text(js, encoding='utf-8')
            self.assertEqual(_paths.read_tile_manifest(tmp), [{'kind': 'star', 'n': 5}])

    def test_js_double_quoted_string_escapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            js = r"""const T = /*__TILES__*/ [{ "a\'k": "a\'b", b: "a\\'b", c: "a\"b", d: 'a\'b' }];"""
            (Path(tmp) / '60_app.js').write_text(js, encoding='utf-8')
            self.assertEqual(
                _paths.read_tile_manifest(tmp),
                [{"a'k": "a'b", 'b': "a\\'b", 'c': 'a"b', 'd': "a'b"}],
            )


class TestDataKeysAndRetireData2(unittest.TestCase):
    def test_real_app_gen(self):
        d = _paths.data_keys(['STARS_N', 'GAIA_N', 'AST_EPOCH', 'ZCOL', 'CMB'])
        self.assertEqual(d['STARS_N'], 58967)
        self.assertEqual(d['GAIA_N'], 200000)
        self.assertIsInstance(d['AST_EPOCH'], (int, float))
        self.assertIn('n', d['ZCOL'])
        self.assertIsInstance(d['CMB'], str)
        self.assertTrue(d['CMB'].startswith('data:image/jpeg;base64,'))
        d_gen = _paths.data_keys(k for k in ('STARS_N', 'GAIA_N'))
        self.assertEqual(d_gen, {'STARS_N': 58967, 'GAIA_N': 200000})
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'data.js').write_text('const DATA = {"A": 1};\n', encoding='utf-8')
            self.assertEqual(_paths.data_keys((k for k in ('A',)), gen_dir=tmp), {'A': 1})
            with self.assertRaises(SystemExit):
                _paths.data_keys((k for k in ('A', 'MISSING_KEY')), gen_dir=tmp)

    def test_idempotent_across_all_32_subsets_of_retire_data2(self):
        retire_list = sorted(_paths.RETIRE_DATA2)
        self.assertEqual(len(retire_list), 5)
        legacy_vals = {
            'STARS_N': 999999,
            'STARS_GEO': 'BAD_DATA2_GEO',
            'STARS_AUX': 'BAD_DATA2_AUX',
            'STAR_LABELS': [{'n': 'WRONG'}],
            'CMB': 'BAD_DATA2_CMB',
        }
        keep_vals = {
            'LOCAL': [{'n': 'Andromède (M31)', 'pos': [0.1, 0.2, 0.3]}],
            'NEAR': 'NEAR_B64',
            'NEAR_N': 788,
            'SURV': 'SURV_B64',
            'AST_EPOCH': 2461200.5,
        }
        wanted = retire_list + list(keep_vals.keys())
        expected = None
        for mask in range(1 << len(retire_list)):
            with tempfile.TemporaryDirectory() as tmp:
                gen = Path(tmp)
                (gen / 'data.js').write_text('const DATA = {"STARS_N": 100, "STARS_AUX": "OLD"};\n', encoding='utf-8')
                d2 = dict(keep_vals)
                for bit, key in enumerate(retire_list):
                    if mask & (1 << bit):
                        d2[key] = legacy_vals[key]
                (gen / 'data2.js').write_text(
                    'Object.assign(DATA, ' + json.dumps(d2) + ');\n',
                    encoding='utf-8',
                )
                # Avec espaces autour de ':' pour tester raw_decode
                (gen / 'data3.js').write_text(
                    'Object.assign(DATA, {"STARS_N": 58967, "STARS_GEO": "GOOD_GEO", '
                    '"STARS_AUX": "GOOD_AUX", "STAR_LABELS": [{"n": "Sirius"}]});\n',
                    encoding='utf-8',
                )
                (gen / 'data19.js').write_text(
                    'Object.assign(DATA, {"CMB": "GOOD_PLANCK_CMB"});\n',
                    encoding='utf-8',
                )
                got = _paths.data_keys(wanted, gen_dir=gen)
                if expected is None:
                    expected = got
                else:
                    self.assertEqual(got, expected)
                self.assertEqual(got['STARS_N'], 58967)
                self.assertEqual(got['STARS_GEO'], 'GOOD_GEO')
                self.assertEqual(got['STARS_AUX'], 'GOOD_AUX')
                self.assertEqual(got['STAR_LABELS'], [{'n': 'Sirius'}])
                self.assertEqual(got['CMB'], 'GOOD_PLANCK_CMB')
                for k, v in keep_vals.items():
                    self.assertEqual(got[k], v)

    def test_natif_etoiles_reexports_data_keys(self):
        fake_np = types.ModuleType('numpy')
        mod = _load_module('natif_etoiles_test', PIPELINE_DIR / 'natif' / 'etoiles.py', stubs={'numpy': fake_np})
        self.assertIs(mod.data_keys, _paths.data_keys)
        self.assertEqual(mod.RETIRE_DATA2, _paths.RETIRE_DATA2)
        self.assertEqual(mod.ROOT, str(REPO_ROOT))

    def test_structural_top_level_resists_nested_comments_and_strings(self):
        cases = [
            ('Object.assign(DATA, {"META": {"KEY": 999}, "KEY": 42});\n', 42),
            ('/* "KEY": 999 */\nObject.assign(DATA, {"KEY": 42});\n', 42),
            ('Object.assign(DATA, {"NOTE": \'see "KEY": 999\', "KEY": 42});\n', 42),
            (r'Object.assign(DATA, {"NOTE": "see \"KEY\": 999", "KEY": 42});' + '\n', 42),
        ]
        for js, expected in cases:
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / 'data.js').write_text(js, encoding='utf-8')
                self.assertEqual(_paths.data_keys(['KEY'], gen_dir=tmp), {'KEY': expected})

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'data.js').write_text(
                'Object.assign(DATA, {"META": {"KEY": 999}});\n',
                encoding='utf-8',
            )
            with self.assertRaises(SystemExit):
                _paths.data_keys(['KEY'], gen_dir=tmp)

    def test_merges_object_assign_data_subkey_and_real_tex(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'data.js').write_text('const DATA = {"TEX": {"earth": "e0", "moon": "m0"}};\n', encoding='utf-8')
            (Path(tmp) / 'data11.js').write_text(
                'Object.assign(DATA, {"SKY": "s"});\nObject.assign(DATA.TEX, {"moon": "m1", "mars": "r1"});\n',
                encoding='utf-8',
            )
            got = _paths.data_keys(['TEX'], gen_dir=tmp)
            self.assertEqual(got['TEX'], {'earth': 'e0', 'moon': 'm1', 'mars': 'r1'})

        # Vérifie le vrai app/gen/ (data.js + data11.js Object.assign(DATA.TEX, {...}))
        real_tex = _paths.data_keys(['TEX'])['TEX']
        self.assertIsInstance(real_tex, dict)
        self.assertIn('moon', real_tex)
        self.assertGreaterEqual(len(real_tex), 9)


class TestFusionBin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module('natif_fusion_bin_test', PIPELINE_DIR / 'natif' / 'fusion_bin.py')

    def _sample(self, fichiers, *, fusion_ga=4.5, n=2, affichees=None):
        return {
            't': [0.0 + 0.02 * i for i in range(n)],
            'traceurs': ['Soleil'],
            'quantum_kpc': 0.025,
            'fusion_ga': fusion_ga,
            'derive_max': 0.001,
            'affichees': [10, 20, 30, 40] if affichees is None else affichees,
            'centres': [[[float(i + g + a) for a in range(3)] for g in range(4)] for i in range(n)],
            'traceurs_pos': [[[float(i + a) for a in range(3)]] for i in range(n)],
            'fichiers': fichiers,
        }

    def test_exact_16_byte_ascii_and_convert(self):
        name = 'kf_000000001.bin'
        self.assertEqual(len(name.encode('utf-8')), 16)
        m = self._sample([[name, 2]])
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'src'
            src.mkdir()
            (src / 'fusion.json').write_text(json.dumps(m), encoding='utf-8')
            dst = Path(tmp) / 'fusion.bin'
            _, b = self.mod.convert(str(src), str(dst))
            self.assertEqual(dst.read_bytes(), b)
        # 12*8 + 2*12*8 + 2*1*3*8 + 8 + 1*24 = 96 + 192 + 48 + 8 + 24 = 368
        self.assertEqual(len(b), 368)
        self.assertEqual(b[344:360], b'kf_000000001.bin')
        self.assertEqual(struct.unpack('<d', b[360:368])[0], 2.0)

    def test_multibyte_utf8_within_16_bytes(self):
        name = 'étoile_01.bin'
        self.assertEqual(len(name), 13)
        self.assertEqual(len(name.encode('utf-8')), 14)
        b = self.mod.pack_fusion(self._sample([[name, 1]]))
        self.assertEqual(len(b), 368)
        self.assertEqual(b[344:360], name.encode('utf-8') + b'\x00\x00')
        self.assertEqual(struct.unpack('<d', b[360:368])[0], 1.0)

    def test_rejects_too_long_ascii_and_multibyte_utf8_and_nul(self):
        too_long_ascii = 'kf_0000000001.bin'
        self.assertEqual(len(too_long_ascii), 17)
        with self.assertRaises(ValueError) as cm:
            self.mod.pack_fusion(self._sample([[too_long_ascii, 1]]))
        self.assertIn(too_long_ascii, str(cm.exception))
        self.assertIn('17', str(cm.exception))

        for name, expected_bytes in (('é' * 9, '18'), ('ééééééééé.bin', '22')):
            self.assertLess(len(name), 16)
            with self.assertRaises(ValueError) as cm:
                self.mod.pack_fusion(self._sample([[name, 1]]))
            self.assertIn(name, str(cm.exception))
            self.assertIn(expected_bytes, str(cm.exception))

        with self.assertRaises(ValueError):
            self.mod.pack_fusion(self._sample([['kf_\x00.bin', 1]]))

    def test_header_validation_and_none_fusion_ga(self):
        with self.assertRaises(ValueError):
            self.mod.pack_fusion(self._sample([['kf_000.bin', 1]], n=1))
        with self.assertRaises(ValueError):
            self.mod.pack_fusion(self._sample([['kf_000.bin', 1]], affichees=[1, 2, 3]))
        b = self.mod.pack_fusion(self._sample([['kf_000.bin', 2]], fusion_ga=None))
        hdr = struct.unpack('<12d', b[:96])
        self.assertTrue(math.isnan(hdr[6]))
        # Liste fichiers vide et fusion_ga=0.0 ou NaN autorisés
        b_empty = self.mod.pack_fusion(self._sample([], fusion_ga=0.0))
        self.assertEqual(struct.unpack('<12d', b_empty[:96])[6], 0.0)
        b_nan = self.mod.pack_fusion(self._sample([], fusion_ga=float('nan')))
        self.assertTrue(math.isnan(struct.unpack('<12d', b_nan[:96])[6]))

    def test_rejects_invalid_header_and_kf_entries_matching_cpp(self):
        # Nom de fichier vide
        with self.assertRaises(ValueError):
            self.mod.pack_fusion(self._sample([['', 1]]))
        # k invalide : négatif, non entier, NaN, inf, bool, > n
        for bad_k in (-1, 1.5, float('nan'), float('inf'), True, 3):
            with self.assertRaises(ValueError, msg=f'k={bad_k!r}'):
                self.mod.pack_fusion(self._sample([['kf_000.bin', bad_k]]))
        # dt <= 0 ou non fini ou bool
        for bad_t in ([0.0, 0.0], [1.0, 0.5], [0.0, float('nan')], [0.0, float('inf')], [False, True]):
            m = self._sample([['kf_000.bin', 2]])
            m['t'] = bad_t
            with self.assertRaises(ValueError, msg=f't={bad_t!r}'):
                self.mod.pack_fusion(m)
        # T == 0
        m = self._sample([['kf_000.bin', 2]])
        m['traceurs'] = []
        m['traceurs_pos'] = [[], []]
        with self.assertRaises(ValueError):
            self.mod.pack_fusion(m)
        # quantum_kpc <= 0 ou non fini ou bool
        for bad_q in (0.0, -0.025, float('nan'), float('inf'), True):
            m = self._sample([['kf_000.bin', 2]])
            m['quantum_kpc'] = bad_q
            with self.assertRaises(ValueError, msg=f'q={bad_q!r}'):
                self.mod.pack_fusion(m)
        # fusion_ga = ±inf ou bool
        for bad_f in (float('inf'), float('-inf'), True):
            with self.assertRaises(ValueError, msg=f'fusion_ga={bad_f!r}'):
                self.mod.pack_fusion(self._sample([['kf_000.bin', 2]], fusion_ga=bad_f))
        # derive_max non fini ou bool
        for bad_d in (float('nan'), float('inf'), False):
            m = self._sample([['kf_000.bin', 2]])
            m['derive_max'] = bad_d
            with self.assertRaises(ValueError, msg=f'derive_max={bad_d!r}'):
                self.mod.pack_fusion(m)
        # affichees négatif, non entier, non fini ou bool
        for bad_a in ([-1, 0, 0, 0], [1.5, 0, 0, 0], [float('nan'), 0, 0, 0], [True, 0, 0, 0]):
            with self.assertRaises(ValueError, msg=f'affichees={bad_a!r}'):
                self.mod.pack_fusion(self._sample([['kf_000.bin', 2]], affichees=bad_a))


class TestBuildOpenNGC(unittest.TestCase):
    def test_cwd_independent_import_from_tempdir(self):
        script_path = str(PIPELINE_DIR / 'sources' / 'build_openngc.py')
        code = (
            'import importlib.util; '
            f'spec = importlib.util.spec_from_file_location("b_openngc", {script_path!r}); '
            'mod = importlib.util.module_from_spec(spec); '
            'spec.loader.exec_module(mod); '
            'assert hasattr(mod, "build_cf4") and callable(mod.main) '
            'and callable(mod.sexa) and callable(mod.nom_propre)'
        )
        res = subprocess.run(
            [sys.executable, '-c', code],
            cwd=tempfile.gettempdir(),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0, msg=res.stderr)

    def test_helpers(self):
        mod = _load_module('sources_build_openngc_test', PIPELINE_DIR / 'sources' / 'build_openngc.py')
        self.assertEqual(mod.sexa('00:42:44.33', True), 10.68471)
        self.assertEqual(mod.sexa('-11:37:23.0', False), -11.62306)
        self.assertIsNone(mod.sexa('', True))
        self.assertEqual(mod.nom_propre('NGC0224'), 'NGC 224')
        self.assertEqual(mod.nom_propre('IC0434'), 'IC 434')
        self.assertEqual(mod.nom_propre('NGC5194A'), 'NGC 5194A')
        self.assertTrue(math.isfinite(mod.z_groupe_local(10.68, 41.27, -0.001)))

    def test_no_duplicate_galaxies_call_or_loop_dict_rebuild(self):
        path = PIPELINE_DIR / 'sources' / 'build_openngc.py'
        tree = ast.parse(path.read_text(encoding='utf-8'), str(path))
        main_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        gal_calls = [
            n for n in ast.walk(main_fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == 'galaxies_de_la_page'
        ]
        self.assertEqual(len(gal_calls), 1)

        loop_dictcomps = []
        for node in ast.walk(main_fn):
            if isinstance(node, ast.For):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.DictComp):
                        loop_dictcomps.append(sub.lineno)
        self.assertEqual(loop_dictcomps, [])
        self.assertEqual(_bare_open_calls(path), [])


class TestBuildCF4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module('sources_build_cf4_test', PIPELINE_DIR / 'sources' / 'build_cf4.py')

    def test_r_zero_and_nan_guard(self):
        for vec in (
            (0.0, 0.0, 0.0),
            (float('nan'), 0.0, 0.0),
            (float('inf'), 0.0, 0.0),
            (float('-inf'), 0.0, 0.0),
            (0.0, float('inf'), 0.0),
            (0.0, 0.0, float('inf')),
            (0.0, float('inf'), float('inf')),
            (float('nan'), float('inf'), 0.0),
            (0.0, 1.5e308, 1.5e308),
        ):
            self.assertIsNone(self.mod.ecl_vers_eq(*vec), msg=f'vec={vec!r}')

    def test_known_directions(self):
        ra, dec = self.mod.ecl_vers_eq(1.0, 0.0, 0.0)
        self.assertAlmostEqual(ra, 0.0, places=12)
        self.assertAlmostEqual(dec, 0.0, places=12)
        ra, dec = self.mod.ecl_vers_eq(0.0, 0.0, 1.0)
        self.assertAlmostEqual(ra, 270.0, places=12)
        self.assertAlmostEqual(dec, 90.0 - math.degrees(self.mod.EPS), places=12)

    def test_celestial_poles_and_subnormal(self):
        s, c = math.sin(self.mod.EPS), math.cos(self.mod.EPS)
        _, dec_n = self.mod.ecl_vers_eq(0.0, s, c)
        _, dec_s = self.mod.ecl_vers_eq(0.0, -s, -c)
        self.assertEqual(dec_n, 90.0)
        self.assertEqual(dec_s, -90.0)
        _, dec_sub_n = self.mod.ecl_vers_eq(0.0, 1e-158 * s, 1e-158 * c)
        _, dec_sub_s = self.mod.ecl_vers_eq(0.0, -1e-158 * s, -1e-158 * c)
        self.assertEqual(dec_sub_n, 90.0)
        self.assertEqual(dec_sub_s, -90.0)

    def test_pole_clamp_explicit_overshoot(self):
        s, c = math.sin(self.mod.EPS), math.cos(self.mod.EPS)
        with mock.patch.object(self.mod.math, 'hypot', return_value=1.0 / (1.0 + 1e-12)):
            _, dec_pos = self.mod.ecl_vers_eq(0.0, s, c)
            _, dec_neg = self.mod.ecl_vers_eq(0.0, -s, -c)
        self.assertEqual(dec_pos, 90.0)
        self.assertEqual(dec_neg, -90.0)

    def test_parse_data_js_variants_and_errors(self):
        payload = {'A': [1, 2], 'B': 'ok'}
        raw = json.dumps(payload)
        for text in (
            f'Object.assign(DATA, {raw});\n',
            f'Object.assign(DATA, {raw});\r\n',
            f'Object.assign(DATA, {raw});',
            f'Object.assign(DATA, {raw})\n',
            f'  \nObject.assign(DATA,  {raw} ) ;  \r\n',
            f'\ufeffObject.assign(DATA, {raw});\n',
            f'Object.assign(DATA,{raw});\n',
            f'\ufeffObject.assign( DATA , {raw} )',
        ):
            self.assertEqual(self.mod.parse_data_js(text), payload)
        with self.assertRaises(ValueError):
            self.mod.parse_data_js('const DATA = {};')
        with self.assertRaises(ValueError):
            self.mod.parse_data_js('Object.assign(DATA, {"a": 1};')


class TestProtonPdfTrapzCompat(unittest.TestCase):
    def _make_fake_numpy(self, *, has_trapezoid: bool, has_trapz: bool):
        calls = {'trapezoid': 0, 'trapz': 0}

        class _Arr(list):
            def __sub__(self, other):
                if isinstance(other, _Arr):
                    return _Arr(a - b for a, b in zip(self, other))
                return _Arr(a - other for a in self)

            def __add__(self, other):
                if isinstance(other, _Arr):
                    return _Arr(a + b for a, b in zip(self, other))
                return _Arr(a + other for a in self)

            def __radd__(self, other):
                return self.__add__(other)

            def __mul__(self, other):
                if isinstance(other, _Arr):
                    return _Arr(a * b for a, b in zip(self, other))
                return _Arr(a * other for a in self)

            def __rmul__(self, other):
                return self.__mul__(other)

        def _trap(y, x, key):
            calls[key] += 1
            return sum(0.5 * (y[i] + y[i + 1]) * (x[i + 1] - x[i]) for i in range(len(x) - 1))

        np_stub = types.ModuleType('numpy')
        np_stub.log = lambda xs: _Arr(math.log(v) for v in xs)
        np_stub.exp = lambda xs: _Arr(math.exp(v) for v in xs)
        np_stub.linspace = lambda a, b, n: _Arr(a + (b - a) * i / 63 for i in range(64))

        def _interp(xs, xp, fp):
            out = []
            for v in xs:
                t = (v - xp[0]) / (xp[-1] - xp[0])
                out.append(fp[0] + t * (fp[-1] - fp[0]))
            return _Arr(out)

        np_stub.interp = _interp
        if has_trapezoid:
            np_stub.trapezoid = lambda y, x: _trap(y, x, 'trapezoid')
        if has_trapz:
            np_stub.trapz = lambda y, x: _trap(y, x, 'trapz')
        return np_stub, calls

    def test_ast_no_bare_trapz_and_no_bare_open(self):
        path = PIPELINE_DIR / 'quantique' / 'proton_pdf.py'
        tree = ast.parse(path.read_text(encoding='utf-8'), str(path))
        bare_trapz = [
            n.lineno for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and n.attr == 'trapz'
        ]
        self.assertEqual(bare_trapz, [])
        has_trapezoid = any(
            (isinstance(n, ast.Attribute) and n.attr == 'trapezoid')
            or (isinstance(n, ast.Constant) and n.value == 'trapezoid')
            for n in ast.walk(tree)
        )
        self.assertTrue(has_trapezoid)
        self.assertEqual(_bare_open_calls(path), [])

    def test_runtime_all_numpy_modes(self):
        xs = [0.01, 1.0]
        xf = {2: [1.0, 1.0], -2: [0.0, 0.0], 1: [0.5, 0.5], -1: [0.0, 0.0], 21: [1.0, 1.0]}
        path = PIPELINE_DIR / 'quantique' / 'proton_pdf.py'

        # NumPy 2.x only (trapezoid only)
        np2, c2 = self._make_fake_numpy(has_trapezoid=True, has_trapz=False)
        mod2 = _load_module('proton_pdf_np2', path, stubs={'numpy': np2})
        mom2, n2 = mod2.integrales(xs, xf)
        self.assertEqual(c2['trapezoid'], 6)
        self.assertEqual(c2['trapz'], 0)
        self.assertAlmostEqual(n2['u'], math.log(100.0), places=6)
        self.assertAlmostEqual(n2['d'], 0.5 * math.log(100.0), places=6)
        self.assertAlmostEqual(mom2['uv'], 0.99, places=2)

        # NumPy 1.x only (trapz only)
        np1, c1 = self._make_fake_numpy(has_trapezoid=False, has_trapz=True)
        mod1 = _load_module('proton_pdf_np1', path, stubs={'numpy': np1})
        mom1, n1 = mod1.integrales(xs, xf)
        self.assertEqual(c1['trapz'], 6)
        self.assertEqual(c1['trapezoid'], 0)
        self.assertAlmostEqual(n1['u'], n2['u'], places=9)
        self.assertAlmostEqual(mom1['uv'], mom2['uv'], places=9)

        # NumPy 2.0 (both present -> prefers trapezoid)
        np20, c20 = self._make_fake_numpy(has_trapezoid=True, has_trapz=True)
        mod20 = _load_module('proton_pdf_np20', path, stubs={'numpy': np20})
        mod20.integrales(xs, xf)
        self.assertEqual(c20['trapezoid'], 6)
        self.assertEqual(c20['trapz'], 0)

        # Neither present -> RuntimeError
        np_bad, _ = self._make_fake_numpy(has_trapezoid=False, has_trapz=False)
        mod_bad = _load_module('proton_pdf_np_bad', path, stubs={'numpy': np_bad})
        with self.assertRaises(RuntimeError):
            mod_bad.integrales(xs, xf)


class TestGraviteGpuOverflow(unittest.TestCase):
    def test_cuda_walk_kernel_has_atomic_overflow_counter(self):
        path = PIPELINE_DIR / 'fusion' / 'gravite_gpu.py'
        tree = ast.parse(path.read_text(encoding='utf-8'), str(path))
        src = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '_SRC':
                        src = ast.literal_eval(node.value)
        self.assertIsInstance(src, str)
        walk_src = src[src.index('void walk('):src.index('void direct(')]
        self.assertIn('unsigned int* overflow', walk_src)
        self.assertIn('sp + 2 <= WALK_STACK_SIZE', walk_src)
        self.assertIn('atomicAdd(overflow, 1u)', walk_src)

    def test_python_gravity_validation_and_overflow_runtime_error(self):
        injected = {'overflow': 0, 'walk_calls': 0}

        class _Scalar:
            def __init__(self, val):
                self._val = val

            def item(self):
                return self._val

            def __float__(self):
                return float(self._val)

        class _GpuArr:
            def __init__(self, shape, fill=0.0):
                self.shape = (shape,) if isinstance(shape, int) else tuple(shape)
                size = 1
                for dim in self.shape:
                    size *= dim
                self._data = [fill] * max(size, 0)

            def __getitem__(self, idx):
                if isinstance(idx, int):
                    return _Scalar(self._data[idx])
                return self

            def __setitem__(self, idx, val):
                if isinstance(idx, int):
                    self._data[idx] = val

            def __sub__(self, other):
                return self

            def __pow__(self, other):
                return self

            def max(self, axis=None):
                return self

            def astype(self, dtype):
                return self

            def reshape(self, *shape):
                return _GpuArr(shape)

        class _FakeRawModule:
            def __init__(self, code, options=()):
                self.code = code

            def get_function(self, name):
                def _kernel(grid, block, args):
                    if name == 'walk':
                        injected['walk_calls'] += 1
                        args[-1][0] = injected['overflow']
                return _kernel

        cp_stub = types.ModuleType('cupy')
        cp_stub.int32 = 'int32'
        cp_stub.uint32 = 'uint32'
        cp_stub.float32 = 'float32'
        cp_stub.float64 = 'float64'
        cp_stub.RawModule = _FakeRawModule
        cp_stub.ElementwiseKernel = lambda *a, **kw: (lambda *xs: _GpuArr(4))
        cp_stub.median = lambda arr, axis=0: _GpuArr(3, 0.0)
        cp_stub.abs = lambda arr: arr
        cp_stub.percentile = lambda arr, q: 1.0
        cp_stub.argsort = lambda arr: _GpuArr(4)
        cp_stub.ascontiguousarray = lambda arr: arr
        cp_stub.empty = lambda shape, dtype=None: _GpuArr(shape)
        cp_stub.zeros = lambda shape, dtype=None: _GpuArr(shape, 0)
        cp_stub.full = lambda shape, fill, dtype=None: _GpuArr(shape, fill)

        np_stub = types.ModuleType('numpy')
        np_stub.int32 = int
        np_stub.float32 = float

        mod = _load_module(
            'gravite_gpu_test',
            PIPELINE_DIR / 'fusion' / 'gravite_gpu.py',
            stubs={'cupy': cp_stub, 'numpy': np_stub},
        )

        # theta <= 0, non fini ou bool -> ValueError
        for bad_theta in (0.0, -0.5, float('nan'), float('inf'), float('-inf'), True, False):
            with self.assertRaises(ValueError, msg=f'theta={bad_theta!r}'):
                mod.gravity(_GpuArr((4, 3)), _GpuArr(4), _GpuArr(4), theta=bad_theta)

        # n <= 1 -> returns zeros without launching walk
        for n_small in (0, 1):
            a0, p0 = mod.gravity(_GpuArr((n_small, 3)), _GpuArr(n_small), _GpuArr(n_small), theta=0.5)
            self.assertEqual(a0.shape, (n_small, 3))
            self.assertEqual(p0.shape, (n_small,))
        self.assertEqual(injected['walk_calls'], 0)

        # overflow == 0 -> succeeds
        injected['overflow'] = 0
        out_a, out_p = mod.gravity(_GpuArr((4, 3)), _GpuArr(4), _GpuArr(4), theta=0.5)
        self.assertEqual(out_a.shape, (4, 3))
        self.assertEqual(out_p.shape, (4,))
        self.assertEqual(injected['walk_calls'], 1)

        # overflow > 0 -> RuntimeError
        injected['overflow'] = 3
        with self.assertRaises(RuntimeError) as cm:
            mod.gravity(_GpuArr((4, 3)), _GpuArr(4), _GpuArr(4), theta=0.5)
        self.assertIn('3', str(cm.exception))
        self.assertIn(str(mod.WALK_STACK_SIZE), str(cm.exception))


class TestCalculFetchAndLgv(unittest.TestCase):
    def test_calcul_has_no_unclosed_open_calls(self):
        self.assertEqual(_bare_open_calls(PIPELINE_DIR / 'fusion' / 'calcul.py'), [])

    def test_fetch_check_deps_raises_clear_import_error(self):
        for fname in ('fetch2.py', 'fetch_all.py'):
            mod = _load_module(f'test_{fname[:-3]}', PIPELINE_DIR / fname)
            with mock.patch.object(mod.importlib.util, 'find_spec', return_value=None):
                with self.assertRaises(ImportError) as cm:
                    mod.check_deps()
                self.assertIn('pipeline/pyproject.toml', str(cm.exception))

    def test_build_lgv_load_local_catalog(self):
        mod = _load_module('test_build_lgv', PIPELINE_DIR / 'build_lgv.py')
        cat = mod.load_local_catalog()
        self.assertEqual(len(cat['names']), 101)
        self.assertEqual(len(cat['en']), 101)
        self.assertEqual(len(cat['pos']), 101)
        self.assertTrue(any(n.startswith('Andromède') for n in cat['names']))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bom.js'
            p.write_text('\ufeff  Object.assign(DATA,{"LOCAL":[{"n":"M31","pos":[1,2,3]}]})\r\n', encoding='utf-8')
            self.assertEqual(mod._load_assign(p), {'LOCAL': [{'n': 'M31', 'pos': [1, 2, 3]}]})


class TestPyprojectAndPipelineHygiene(unittest.TestCase):
    def test_pyproject_toml_and_requirements_ci(self):
        pyproj = PIPELINE_DIR / 'pyproject.toml'
        self.assertTrue(pyproj.is_file())
        data = _load_toml_text(pyproj.read_text(encoding='utf-8'))
        proj = data['project']
        self.assertEqual(proj['requires-python'], '>=3.10')
        self.assertEqual(proj['dependencies'], [])
        opt = proj['optional-dependencies']
        self.assertEqual(set(opt.keys()), {'core', 'astro', 'quantum', 'fusion-cpu', 'fusion-gpu'})
        for grp, pkgs in opt.items():
            self.assertIsInstance(pkgs, list, msg=grp)
            self.assertTrue(pkgs and all(isinstance(p, str) and p.strip() for p in pkgs), msg=grp)
        self.assertTrue(any(p.startswith('numpy') for p in opt['core']))
        self.assertTrue(any(p.startswith('astropy') for p in opt['astro']))
        self.assertTrue(any(p.startswith('pyscf') for p in opt['quantum']))
        self.assertTrue(any(p.startswith('agama') for p in opt['fusion-cpu']))
        self.assertTrue(any(p.startswith('cupy') for p in opt['fusion-gpu']))
        self.assertTrue((PIPELINE_DIR / 'requirements-ci.txt').is_file())

    def test_toml_stdlib_fallback_parity_rejection_and_py310_sim(self):
        pyproj_text = (PIPELINE_DIR / 'pyproject.toml').read_text(encoding='utf-8')
        parsed_fallback = _loads_toml_stdlib(pyproj_text)
        if tomllib is not None:
            self.assertEqual(parsed_fallback, tomllib.loads(pyproj_text))

        for bad_toml in (
            '[unclosed\n',
            '[]\n',
            '[a..b]\n',
            'key = "unclosed\n',
            'key = ["a" "b"]\n',
            'key = ["a", , "b"]\n',
            'key = ["a",\n',
            'no_equals_line\n',
            'a = "1"\na = "2"\n',
            '[sec]\na = "1"\n[sec]\nb = "2"\n',
            'a = "1" trailing\n',
        ):
            with self.assertRaises(ValueError, msg=f'bad_toml={bad_toml!r}'):
                _loads_toml_stdlib(bad_toml)

        # Simulation Python 3.10 stdlib-only : tomllib et tomli indisponibles
        test_path = str(Path(__file__).resolve())
        sim_code = (
            'import importlib.util, sys, unittest\n'
            'class _Blocker:\n'
            '    def find_spec(self, fullname, path, target=None):\n'
            '        if fullname in ("tomllib", "tomli"):\n'
            '            raise ModuleNotFoundError(fullname)\n'
            '        return None\n'
            'sys.meta_path.insert(0, _Blocker())\n'
            'sys.modules.pop("tomllib", None)\n'
            'sys.modules.pop("tomli", None)\n'
            f'spec = importlib.util.spec_from_file_location("t_py310", {test_path!r})\n'
            'mod = importlib.util.module_from_spec(spec)\n'
            'spec.loader.exec_module(mod)\n'
            'assert mod.tomllib is None\n'
            'suite = unittest.defaultTestLoader.loadTestsFromName(\n'
            '    "TestPyprojectAndPipelineHygiene.test_pyproject_toml_and_requirements_ci", mod\n'
            ')\n'
            'res = unittest.TextTestRunner(verbosity=0).run(suite)\n'
            'assert res.wasSuccessful(), res\n'
        )
        proc = subprocess.run(
            [sys.executable, '-c', sim_code],
            cwd=tempfile.gettempdir(),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr + proc.stdout)

    def test_all_python_files_parse_cleanly(self):
        py_files = sorted(PIPELINE_DIR.rglob('*.py'))
        self.assertGreaterEqual(len(py_files), 68)
        for p in py_files:
            ast.parse(p.read_text(encoding='utf-8'), str(p))

    def test_no_forbidden_hardcoded_strings_or_dynamic_code(self):
        # Motifs construits par concaténation afin que test_pipeline_stdlib.py soit lui-même vérifié.
        forbidden = (
            '/' + 'mnt/' + 'user-data',
            '--break-' + 'system-packages',
            'LOCAL' + 'APPDATA',
            '..' + '/gen',
            '/' + 'tmp/',
            'pip ' + 'install',
        )
        hits = []
        exec_hits = []
        for p in sorted(PIPELINE_DIR.rglob('*.py')):
            text = p.read_text(encoding='utf-8')
            for lineno, line in enumerate(text.splitlines(), 1):
                for pat in forbidden:
                    if pat in line:
                        hits.append(f'{p.relative_to(REPO_ROOT)}:{lineno}: {pat}')
            tree = ast.parse(text, str(p))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'exec':
                    exec_hits.append(f'{p.relative_to(REPO_ROOT)}:{node.lineno}')
        self.assertEqual(hits, [], msg='Motifs interdits trouvés : ' + ', '.join(hits))
        self.assertEqual(exec_hits, [], msg='Appels ' + 'exec' + '() trouvés : ' + ', '.join(exec_hits))

    def test_brouillon_deleted(self):
        self.assertFalse((PIPELINE_DIR / 'gravite' / 'long.test.js.brouillon').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
