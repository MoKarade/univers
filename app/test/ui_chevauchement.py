#!/usr/bin/env python3
"""Test à l'écran « ui-chevauchement » (interface épurée, 12 novembre 2026).

Définition de « fini » validée par Marc, vérifiée ici sur cinq écrans : téléphone 390 × 780, petit téléphone
360 × 640, téléphone en paysage 780 × 390, écran moyen 700 × 800 et PC 1280 × 800.
  1. Aucun texte ni bouton de l'interface n'en chevauche un autre, dans treize situations, barre des échelles
     dépliée (pire cas). Mesure à deux niveaux : les blocs entre eux (en-tête, fiche, message, barre du bas,
     panneaux, boutons, échelle, aide, noms de la barre des échelles), puis chaque texte et bouton à l'intérieur
     d'un même bloc, découpé par sa zone de défilement.
     Choix écrit : les noms posés dans la scène 3D (.lb, #follow) ne sont pas comptés, ni entre eux ni face à
     l'interface. Ils suivent les astres à chaque image et passent forcément derrière l'interface par moments.
  2. Au repos (aucun panneau ouvert ; la fiche de l'astre suivi compte), au plus deux blocs à fond opaque. L'aide
     de première visite (15 secondes, une seule fois) est testée à part, sans chevauchement, hors de ce compte.
  3. Téléphone en portrait : au repos, la barre du bas occupe au plus 15 % de la hauteur.
  4. Chaque commande existante est atteinte en au plus deux touchers depuis le repos : visible et réellement
     touchable (le point au centre est bien la commande) directement, ou après un vrai toucher sur un ouvreur.
     Exceptions écrites, sur téléphone : − et + (le pincement et la barre des échelles font la même chose) ;
     les réglages à l'intérieur des panneaux Affichage et Cosmologie (trois touchers : « Plus », le panneau,
     le réglage). Elles sont comptées et affichées.
  5. Téléphone : un toucher sur la barre des échelles rend ses arrêts touchables.
  6. Rien de caché sans défilement : boutons de la fiche entiers, liste de la fiche d'au moins deux lignes.
  7. Choix écrits, non testés comme des pertes : sur téléphone le bandeau d'événement montre son titre seul
     (coupé s'il est long ; le toucher ouvre sa fiche avec la date et la source) ; tiroir fermé, l'âge de
     l'univers laisse sa ligne au bandeau tant qu'il est affiché (7 s), et reste visible tiroir ouvert.
     La chronologie s'ouvre aussi en touchant la date : ses commandes restent à deux touchers.
  8. Fiche lisible : contraste du texte sur le fond de la fiche d'au moins 4,5, thème sombre et thème clair.

Lancer : python3 app/build.py puis python3 app/test/ui_chevauchement.py [phone small land mid desk]
Variable U_SHOTS : dossier où enregistrer une capture par situation (facultatif).
Sortie : une ligne par situation, puis « ui-chevauchement : PASSE » ou « ÉCHEC » (code de sortie 1).
"""
import os, sys
from playwright.sync_api import sync_playwright

URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'index.html')))
SHOTS = os.environ.get('U_SHOTS', '')
SIZES = {'phone': (390, 780, True), 'small': (360, 640, True), 'land': (780, 390, True), 'mid': (700, 800, False), 'desk': (1280, 800, False)}
MODES = sys.argv[1:] or list(SIZES)
BAR_MAX = 0.15
REST_BLOCKS = 2
TOL = 2
CONTRAST_MIN = 4.5

# Blocs : [sélecteur, nom, bloc opaque ?, sélecteur des éléments intérieurs ou None]
BLOCKS = [
    ('#place', 'titre', False, None), ('#field', 'champ', False, None), ('#prov', 'provenance', False, None),
    ('#findp', 'boutons de l’en-tête', False, 'button'),
    ('#notice', 'message', True, None),
    ('#card', 'fiche', True, 'h2, #card-sub, dt, dd, button'),
    ('#hint', 'aide', True, None),
    ('#time', 'barre du bas', True, 'button, #date, #age, #tape, .g-speed label, #speed-out, #speed'),
    ('#scale', 'échelle', False, None),
    ('#nav', 'boutons de déplacement', False, 'button'),
    ('.panel', 'panneau', True, 'h2, h3, p, button, label, input, .chips, .presets'),
    ('#evt', 'bandeau', True, None),
]

MEASURE_JS = r"""
(blocks) => {
  const vis = el => { for (let e = el; e && e !== document.documentElement; e = e.parentElement) { const s = getComputedStyle(e); if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity < 0.05) return false; } return true; };
  const clip = (el, r) => { let a = { l: r.left, t: r.top, r: r.right, b: r.bottom }; for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) { const s = getComputedStyle(e); if (/(auto|scroll|hidden)/.test(s.overflowY + s.overflowX)) { const q = e.getBoundingClientRect(); a = { l: Math.max(a.l, q.left), t: Math.max(a.t, q.top), r: Math.min(a.r, q.right), b: Math.min(a.b, q.bottom) }; } } a = { l: Math.max(a.l, 0), t: Math.max(a.t, 0), r: Math.min(a.r, innerWidth), b: Math.min(a.b, innerHeight) }; return a.r - a.l > 1 && a.b - a.t > 1 ? [a.l, a.t, a.r, a.b] : null; };
  const out = [];
  blocks.forEach(([sel, name, opaque, inner]) => document.querySelectorAll(sel).forEach((el, k) => {
    if (!vis(el)) return; if (sel === '#evt' && el.closest('#time')) return;      /* dans la barre du bas : mesuré avec elle */
    const r = clip(el, el.getBoundingClientRect()); if (!r) return; const id = sel + ':' + k;
    out.push({ id, name: name + (sel === '.panel' ? ' ' + el.id : ''), box: r, opaque, leaf: false });
    if (inner) el.querySelectorAll(inner).forEach(c => { if (!vis(c)) return; const q = clip(c, c.getBoundingClientRect()); if (q) { const path = []; for (let e = c; e !== el; e = e.parentElement) path.unshift([...e.parentElement.children].indexOf(e)); out.push({ id, name: name + ' › ' + (c.id || c.tagName.toLowerCase()) + ' « ' + (c.textContent || c.value || '').trim().slice(0, 24) + ' »', box: q, opaque: false, leaf: true, path: path.join('/') }); } });
  }));
  document.querySelectorAll('#rail .stop span, #rail .tick b').forEach(s => { if (!vis(s)) return; const q = clip(s, s.getBoundingClientRect()); if (q) out.push({ id: 'rail:' + out.length, name: 'échelle « ' + s.textContent + ' »', box: q, opaque: false, leaf: false }); });
  return out;
}
"""

# Contenu caché sans pouvoir défiler : boutons de la fiche coupés, liste de la fiche réduite à moins de deux lignes.
CUT_JS = r"""
() => { const c = document.getElementById('card'), bad = []; if (!c || getComputedStyle(c).display === 'none') return bad;
  const cr = c.getBoundingClientRect(), vp = r => r.top >= Math.max(cr.top, 0) - 1 && r.bottom <= Math.min(cr.bottom, innerHeight) + 1 && r.left >= cr.left - 1 && r.right <= cr.right + 1;
  c.querySelectorAll('.cbtn button').forEach(b => { if (getComputedStyle(b).display !== 'none' && !vp(b.getBoundingClientRect())) bad.push('bouton de fiche coupé : ' + b.textContent); });
  const dl = document.getElementById('card-dl'); if (dl.children.length) { const lh = parseFloat(getComputedStyle(dl).fontSize) * 1.4, r = dl.getBoundingClientRect(), h = Math.min(r.bottom, cr.bottom, innerHeight) - Math.max(r.top, cr.top, 0); if (h < Math.min(2 * lh, dl.scrollHeight) - 1) bad.push('liste de la fiche réduite à ' + Math.round(h) + ' px'); }
  return bad; }
"""

SITUATIONS = [
    ('accueil', "__U.S.playing=false; __U.select(null); __U.openPanel(null); __U.goStop(__U.STOPS[0], true)", True),
    ('fiche Jupiter', "__U.goName('Jupiter')", False),
    ('fiche Sirius + message', "__U.goName('Sirius')", False),
    ('message déplié', "document.getElementById('notice').classList.add('open')", False),
    ('fiche « Tout voir »', "document.getElementById('card-more').click()", False),
    ('tiroir « Plus » ouvert + fiche', "document.getElementById('card-more').click(); document.getElementById('b-more').click()", False),
    ('chronologie', "__U.select(null); __U.openPanel('chrono')", False),
    ('affichage', "__U.openPanel('view')", False),
    ('Voie lactée', "__U.openPanel(null); __U.select(null); if (document.getElementById('time').classList.contains('open')) document.getElementById('b-more').click(); __U.goStop(__U.STOPS[4], true)", True),
    ('recherche', "document.getElementById('b-find').click()", False),
    ('infiniment petit', "__U.openPanel(null); __U.goStop(__U.STOPS[12], true)", False),
    ('bandeau d’événement', "__U.goStop(__U.STOPS[0], true); __U.evToast(__U.EVL.find(e => e.t > __U.S.ty))", False),
    ('première visite (aide)', "document.getElementById('hint').hidden = false", False),
]

COMMANDES = ['t-date', 't-go', 'b-play', 'b-dir', 'tape', 't-prev', 't-next', 'speed', 'b-now', 'b-chrono', 'b-cosmo', 'b-view', 'b-find', 'b-about2', 'n-back', 'n-home', 'n-out', 'n-in']
REGLAGES = ['c-lab', 'c-orb', 'c-const', 'c-sky', 'c-real', 'c-lite', 'b-about', 's-om', 's-ol', 's-h0', 's-w', 'c-hz', 'c-com', 'c-sim', 'c-dm']
OUVREURS = ['b-more', 'date', 'b-view', 'b-cosmo', 'b-chrono', 'b-find']
PHONE_SANS = {'n-out', 'n-in'}

REACH_JS = r"""
id => { const el = document.getElementById(id); if (!el) return false;
  for (let e = el; e && e !== document.documentElement; e = e.parentElement) { const s = getComputedStyle(e); if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity < 0.05) return false; }
  el.scrollIntoView({ block: 'nearest' }); const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return false;
  const x = r.left + r.width / 2, y = r.top + r.height / 2; if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) return false;
  const h = document.elementFromPoint(x, y); return !!h && (h === el || el.contains(h) || (el.labels && [...el.labels].some(l => l.contains(h)))); }
"""


def overlaps(items):
    bad = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if a['id'] == b['id']:
                if a['leaf'] != b['leaf']: continue      # un bloc et son propre contenu
                if a['leaf'] and (a['path'].startswith(b['path'] + '/') or b['path'].startswith(a['path'] + '/')): continue    # l'un contient l'autre (case dans son libellé, boutons dans leur rangée)
            elif a['leaf'] or b['leaf']: continue         # contenus de blocs différents : couverts par les blocs eux-mêmes
            A, B = a['box'], b['box']
            w = min(A[2], B[2]) - max(A[0], B[0]); h = min(A[3], B[3]) - max(A[1], B[1])
            if w > TOL and h > TOL: bad.append(f"{a['name']} × {b['name']} ({int(w)}×{int(h)} px)")
    return bad


def tap(pg, touch, id_):
    loc = pg.locator('#' + id_)
    if touch: loc.tap(timeout=3000)
    else: loc.click(timeout=3000)
    pg.wait_for_timeout(250)


def rest(pg):
    pg.evaluate("__U.openPanel(null); __U.select(null); document.getElementById('time').classList.remove('open'); document.getElementById('b-more').setAttribute('aria-expanded', false); document.getElementById('hint').hidden = true; __U.goStop(__U.STOPS[1], true)")
    pg.wait_for_timeout(400)


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def contrast(pg):
    fg, bg = pg.evaluate("""() => { const p = s => s.match(/[\\d.]+/g).map(Number); const c = document.getElementById('card'), t = document.querySelector('#card dd');
        return [p(getComputedStyle(t).color), p(getComputedStyle(c).backgroundColor)]; }""")
    a = bg[3] if len(bg) > 3 else 1
    base = (2, 3, 10)                                   # la scène, presque noire (--scene)
    b = [bg[k] * a + base[k] * (1 - a) for k in range(3)]
    L1, L2 = sorted([lum(fg), lum(b)], reverse=True)
    return (L1 + 0.05) / (L2 + 0.05)


def situations(pg, mode, H):
    fails = []
    for k, (name, js, is_rest) in enumerate(SITUATIONS):
        f0 = pg.evaluate('__U.frame()')
        pg.evaluate(js)
        pg.wait_for_function(f'__U.frame() > {f0} + 3', timeout=120000)
        pg.evaluate("document.getElementById('rail').classList.add('show')")
        pg.wait_for_timeout(400)
        items = pg.evaluate(MEASURE_JS, [list(x) for x in BLOCKS])
        bad = overlaps(items)
        line = f'  {mode} · {name} : {len(items)} éléments, {len(bad)} chevauchement(s)'
        if is_rest:
            blocks = [x['name'] for x in items if x['opaque'] and not x['leaf']]
            line += f', blocs au repos {len(blocks)}'
            if len(blocks) > REST_BLOCKS: bad.append('trop de blocs au repos : ' + ', '.join(blocks))
            if mode in ('phone', 'small'):
                t = next((x for x in items if x['name'] == 'barre du bas'), None)
                part = (t['box'][3] - t['box'][1]) / H if t else 0
                line += f', barre du bas {part:.0%}'
                if part > BAR_MAX: bad.append(f'barre du bas {part:.0%} de la hauteur (max {BAR_MAX:.0%})')
        cut = pg.evaluate(CUT_JS)
        if cut: line += f', {len(cut)} coupé(s)'
        bad += cut
        if name == 'fiche Sirius + message':
            c = contrast(pg); line += f', contraste fiche {c:.1f}'
            if c < CONTRAST_MIN: bad.append(f'contraste de la fiche {c:.1f}')
        print(line)
        for x in bad[:12]: print('      ✗', x)
        fails += [f'{mode} · {name} : {x}' for x in bad]
        if SHOTS: pg.screenshot(path=os.path.join(SHOTS, f'ui_{mode}_{k}.png'))
        pg.evaluate("document.getElementById('rail').classList.remove('show')")
    return fails


def reach(pg, mode, touch):
    missing, three = [], []
    for c in COMMANDES + REGLAGES:
        if touch and c in PHONE_SANS: continue
        rest(pg)
        if pg.evaluate(f'({REACH_JS})("{c}")'): continue
        ok = False
        for o in OUVREURS:
            rest(pg)
            if not pg.evaluate(f'({REACH_JS})("{o}")'): continue
            tap(pg, touch, o)
            if pg.evaluate(f'({REACH_JS})("{c}")'): ok = True; break
        if not ok and touch and c in REGLAGES:      # exception écrite : « Plus », puis le panneau, puis le réglage
            for o in OUVREURS[2:]:
                rest(pg); tap(pg, touch, 'b-more')
                if not pg.evaluate(f'({REACH_JS})("{o}")'): continue
                tap(pg, touch, o)
                if pg.evaluate(f'({REACH_JS})("{c}")'): ok = True; three.append(c); break
        if not ok: missing.append(c)
    n = len(COMMANDES) + len(REGLAGES) - (len(PHONE_SANS) if touch else 0)
    print(f'  {mode} · commandes : {n - len(missing)} sur {n} atteintes' + (f' ({len(three)} réglages en trois touchers, exception écrite)' if three else '') + (', hors de portée : ' + ', '.join(missing) if missing else ''))
    return [f'{mode} · commande hors de portée : {c}' for c in missing]


def rail_tap(pg, mode):
    rest(pg)  # le nom est la cible du doigt : le rond est sous la bande de glissement, qui fait la même chose
    box = pg.locator('#rail-hit').bounding_box()
    stops = 0
    if box and box['height'] > 4:
        pg.touchscreen.tap(box['x'] + box['width'] / 2, box['y'] + box['height'] * 0.3); pg.wait_for_timeout(250)
        stops = pg.evaluate("[...document.querySelectorAll('#rail .stop')].filter(b => { if (getComputedStyle(b).pointerEvents === 'none') return false; const sp = b.firstChild; if (getComputedStyle(sp).display === 'none') return false; const r = sp.getBoundingClientRect(), h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!h && b.contains(h); }).length")
    print(f'  {mode} · barre des échelles touchée : {stops} arrêts touchables')
    return [] if stops >= 3 else [f'{mode} · barre des échelles : arrêts non touchables après un toucher']


def run(mode, p):
    W, H, touch = SIZES[mode]
    fails = []
    b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    for scheme in (['dark', 'light'] if mode == 'phone' else ['dark']):
        ctx = b.new_context(viewport={'width': W, 'height': H}, device_scale_factor=1, color_scheme=scheme, reduced_motion='reduce', has_touch=touch, is_mobile=touch)
        pg = ctx.new_page()
        pg.add_init_script("window.__TIER=0; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];")
        pg.goto(URL)
        pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)
        if scheme == 'light':
            pg.evaluate("__U.S.playing=false; __U.goName('Sirius')"); pg.wait_for_timeout(600)
            c = contrast(pg); print(f'  {mode} · thème clair · contraste de la fiche {c:.1f}')
            if c < CONTRAST_MIN: fails.append(f'{mode} · thème clair : contraste de la fiche {c:.1f} < {CONTRAST_MIN}')
        else:
            fails += situations(pg, mode, H)
            fails += reach(pg, mode, touch)
            if touch: fails += rail_tap(pg, mode)
        ctx.close()
    b.close()
    return fails


if __name__ == '__main__':
    allf = []
    with sync_playwright() as p:
        for m in MODES: allf += run(m, p)
    print('ui-chevauchement :', 'PASSE' if not allf else f'ÉCHEC ({len(allf)})')
    sys.exit(1 if allf else 0)
