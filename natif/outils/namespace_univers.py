"""Passe les en-têtes natif/src/*.h de `namespace {` à `namespace univers {` et rend `inline` ce qui doit l'être.

Pourquoi : un espace de noms anonyme dans un en-tête donne une copie par fichier compilé (C++ Core Guidelines SF.21) ;
une variable comme gWindowMode n'était donc pas partagée entre univers.cpp et fenetre.cpp. Dans un espace nommé, toute
fonction ou variable modifiable définie dans un en-tête doit être `inline`, sinon l'édition de liens voit deux définitions.

Usage : python3 natif/outils/namespace_univers.py natif/src
Rejouable : un en-tête déjà converti n'est pas retouché. À lancer sur tout nouvel en-tête écrit en `namespace {`.
Le .cpp qui l'inclut fait `using namespace univers;`.
"""
import re, sys, glob, os

KW_SKIP = ('struct','class','enum','union','namespace','template','inline','constexpr','consteval','using','typedef',
           'extern','static_assert','friend','#','}',';','public','private','protected','typename','concept')

def scan(src):
    """Rend la liste des débuts de déclarations au niveau du namespace (profondeur 1) : (pos, texte jusqu'à { ou ; )."""
    i, n, depth, paren = 0, len(src), 0, 0
    out = []
    stmt_start = None
    def at_line_start(k):
        j = k - 1
        while j >= 0 and src[j] in ' \t': j -= 1
        return j < 0 or src[j] == '\n'
    while i < n:
        c = src[i]
        if src.startswith('//', i):
            i = src.find('\n', i); i = n if i < 0 else i; continue
        if src.startswith('/*', i):
            i = src.find('*/', i) + 2; continue
        if c == '#' and at_line_start(i):
            while True:
                e = src.find('\n', i); e = n if e < 0 else e
                if src[e-1] == '\\' if e > 0 else False: i = e + 1; continue
                i = e; break
            continue
        if src.startswith('R"', i):
            m = re.match(r'R"([^(]*)\(', src[i:]); end = ')' + m.group(1) + '"'
            i = src.find(end, i) + len(end); continue
        if c == '"' or (c == "'" and not (i > 0 and (src[i-1].isalnum()))):
            q = c; i += 1
            while i < n and src[i] != q:
                i += 2 if src[i] == '\\' else 1
            i += 1; continue
        if depth == 1 and paren == 0 and stmt_start is None and not c.isspace():
            stmt_start = i
        if c == '(': paren += 1
        elif c == ')': paren -= 1
        elif c == '{':
            if depth == 1 and paren == 0 and stmt_start is not None:
                out.append((stmt_start, src[stmt_start:i], '{')); stmt_start = None
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 1: stmt_start = None
        elif c == ';' and depth == 1 and paren == 0:
            if stmt_start is not None: out.append((stmt_start, src[stmt_start:i], ';'))
            stmt_start = None
        i += 1
    return out

def first_word(t):
    t = t.lstrip()
    m = re.match(r'(\[\[[^\]]*\]\]\s*)*', t)
    rest = t[m.end():]
    return m.end(), rest

def decide(text, end):
    """Rend (action, décalage) : 'inline' à insérer, 'static' à remplacer par inline, ou None."""
    off, rest = first_word(text)
    if not rest or rest.startswith(KW_SKIP): return None, 0
    flat = re.sub(r'\s+', ' ', rest)
    if flat.startswith('static '):
        r2 = flat[7:]
        if r2.startswith(('constexpr', 'inline')): return None, 0
        return 'static', off
    p, e = flat.find('('), flat.find('=')
    if e >= 0 and flat[e:e+2] == '==': e = -1
    if p >= 0 and (e < 0 or p < e):
        return ('inline', off) if end == '{' else (None, 0)      # définition de fonction ; déclaration laissée telle quelle
    lhs = flat if e < 0 else flat[:e]
    if lhs.startswith('constexpr'): return None, 0
    if lhs.startswith('const ') and not ('*' in lhs and not re.search(r'\*\s*const\b', lhs)): return None, 0
    return 'inline', off      # variable modifiable : une seule pour tout le programme

def convert(path, report):
    src = open(path, encoding='utf-8').read()
    if not re.search(r'^namespace \{', src, re.M): return False
    src = re.sub(r'^namespace \{', 'namespace univers {', src, flags=re.M)
    src = re.sub(r'^\}\s*//\s*namespace\s*$', '}  // namespace univers', src, flags=re.M)
    edits = []
    # profondeur 1 = dans namespace univers (les en-têtes n'ouvrent qu'un namespace de premier niveau)
    for pos, text, end in scan(src):
        act, off = decide(text, end)
        if act == 'inline': edits.append((pos + off, 0, 'inline '))
        elif act == 'static': edits.append((pos + off, 7, 'inline '))
        if act: report.append(f'{path}: {act}: ' + re.sub(r"\s+", " ", text)[:90])
    for p, ln, s in sorted(edits, reverse=True):
        src = src[:p] + s + src[p+ln:]
    open(path, 'w', encoding='utf-8').write(src)
    return True

if __name__ == '__main__':
    report = []
    files = [f for f in sorted(glob.glob(os.path.join(sys.argv[1], '*.h')))]
    done = [f for f in files if convert(f, report)]
    print(len(done), 'en-têtes convertis'); print('\n'.join(report))
