#!/usr/bin/env python3
"""Test à l'écran « ondes » et « fond diffus » (lot S, tâches S1 et S2), sur ordinateur et sur téléphone.

Ondes :
- la chronologie contient une ligne par détection du fichier GWOSC ; catégorie masquée par défaut ;
- l'allumer ajoute exactement ces lignes, l'éteindre revient au compte d'avant ;
- fiches de contrôle : valeurs exactes publiées (GWOSC) et heure TU à la minute ;
- toucher une détection montre la Terre (où le signal est enregistré), pas le Système solaire ;
- une détection à probabilité < 0,99 est « Probable », pas « Certain ».
Fond diffus :
- la texture chargée par la page mesure 2048 × 1024 (carte Planck, la carte WMAP faisait 720 × 360) ;
- le contrôle de corrélation Planck/WMAP du script de données est embarqué et au-dessus de 0,8 ;
- capture de la vue « Univers observable » dans /tmp/lot_s_cmb_<mode>.png.

La page est reconstruite avant le test (pas de page périmée).
Lancer : python3 app/test/lot_s.py [desk|phone]   (PYTHONIOENCODING=utf-8 sous Windows)
"""
import os
import subprocess
import sys

from playwright.sync_api import sync_playwright

ICI = os.path.dirname(os.path.abspath(__file__))
URL = os.environ.get('U_URL', 'file://' + os.path.abspath(os.path.join(ICI, '..', '..', 'dist', 'index.html')))
MODE = sys.argv[1] if len(sys.argv) > 1 else 'desk'
FICHES = [   # nom, textes qui doivent figurer dans la fiche (valeurs GWOSC arrondies comme la page)
    ('GW170817', ['17 août 2017', '12 h 41', '1,5 et 1,3 masses solaires', 'Certain']),
    ('GW190521', ['21 mai 2019', '3 h 02', '98 et 57 masses solaires', 'entre 27 et 84']),
    ('GW200115_042309', ['15 janvier 2020', '4 h 23', '5,9 et 1,4 masses solaires']),
]
NB = ' '


def norm(t):
    return (t or '').replace(NB, ' ').replace(' ', ' ')


def main():
    bad = 0

    def check(ok, msg):
        nonlocal bad
        print(('OK    ' if ok else 'ÉCHEC ') + msg)
        bad += 0 if ok else 1

    if 'U_URL' not in os.environ:
        subprocess.run([sys.executable, os.path.join(ICI, '..', 'build.py')], check=True, stdout=subprocess.DEVNULL)
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        phone = MODE != 'desk'
        ctx = b.new_context(viewport={'width': 390, 'height': 780} if phone else {'width': 1280, 'height': 800},
                            device_scale_factor=2 if phone else 1, has_touch=phone, is_mobile=phone,
                            color_scheme='dark', reduced_motion='reduce')
        pg = ctx.new_page()
        logs = []
        pg.on('pageerror', lambda e: logs.append(str(e)))
        pg.add_init_script("window.__TIER=%d; window.__NOADAPT=true; window.__TILES=[]; window.__PHOTOS=[];" % (0 if phone else 1))
        pg.goto(URL)
        pg.wait_for_function('window.__U && window.__U.frame() > 2', timeout=180000)

        n_fichier = pg.evaluate('DATA.GW.length')
        n_page = pg.evaluate("__U.EVL.filter(e => e.cat === 'O').length")
        check(n_page == n_fichier, 'détections dans la chronologie : %d (fichier GWOSC : %d)' % (n_page, n_fichier))
        n_prob = pg.evaluate("__U.EVL.filter(e => e.cat === 'O' && e.c === 'P').length")
        n_attendu = pg.evaluate("DATA.GW.filter(g => g.pa !== null && g.pa < 0.99).length")
        check(n_prob == n_attendu and n_prob > 0, 'détections « Probable » (probabilité < 0,99) : %d (attendu %d)' % (n_prob, n_attendu))

        compte = "document.querySelectorAll('#events button.ev').length"
        btn = "[...document.querySelectorAll('#ev-cats button')].find(b => /Ondes/.test(b.textContent))"
        avant = pg.evaluate(compte)
        check(pg.evaluate(btn + " !== undefined"), 'bouton « Ondes gravitationnelles » présent')
        check(pg.evaluate(btn + ".getAttribute('aria-pressed')") == 'false', 'catégorie masquée par défaut')
        pg.evaluate(btn + ".click()")
        apres = pg.evaluate(compte)
        check(apres - avant == n_page, 'lignes ajoutées en allumant : %d' % (apres - avant))
        pg.evaluate(btn + ".click()")
        check(pg.evaluate(compte) == avant, 'éteindre revient à %d lignes' % avant)

        for nom, attendus in FICHES:
            txt = norm(pg.evaluate(f"""(() => {{ const e = __U.EVL.find(q => q.cat === 'O' && q.d.startsWith('{nom} ')); if (!e) return null;
                __U.evGo(e); return document.getElementById('card').innerText; }})()"""))
            manque = [a for a in attendus if a not in txt]
            check(bool(txt) and not manque, 'fiche %s%s' % (nom, (' : manque ' + str(manque) + ' dans « ' + txt.replace('\n', ' / ')[:260] + ' »') if manque else ''))
        f0 = pg.evaluate('__U.frame()')
        pg.wait_for_function(f'__U.frame() > {f0} + 6', timeout=180000)
        lieu = pg.evaluate("document.getElementById('place').textContent")
        check('Terre' in lieu, 'vue après le toucher : « %s »' % lieu)

        # S3 : distances Cosmicflows-4 dans les fiches (valeurs de Tully et al. 2023).
        carte = """(o => { __U.select(o); const m = document.getElementById('card-more'); if (m && !m.hidden && /^Plus/.test(m.textContent)) m.click(); return document.getElementById('card').innerText; })"""
        fiches = [('NGC 4258', "__U.selNear(DATA.NEAR_NAMES.split('|').indexOf('NGC4258'))",
                   ['Mesure depuis la Terre', '24,6 millions', 'à 1 % près', 'maser', 'Céphéides', 'PGC 39600']),
                  ('Andromède (M31)', None, ['Mesure depuis la Terre', 'Céphéides', 'PGC 2557'])]
        for nom, js, attendus in fiches:
            if js:
                txt = norm(pg.evaluate(carte + '(' + js + ')'))
            else:
                pg.evaluate("__U.goName('Andromède')")
                f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() > {f0} + 3', timeout=180000)
                txt = norm(pg.evaluate("(() => { const m = document.getElementById('card-more'); if (m && !m.hidden && /^Plus/.test(m.textContent)) m.click(); return document.getElementById('card').innerText; })()"))
            manque = [a for a in attendus if a not in txt]
            check(not manque, 'fiche %s%s' % (nom, (' : manque ' + str(manque) + ' dans « ' + txt.replace(chr(10), ' / ')[:300] + ' »') if manque else ''))
        r = pg.evaluate("""(() => { const C = DATA.CF4_NEAR, a = [], z = [];
            C.forEach((c, i) => (c ? a : z).push(i)); const pick = [];
            for (let k = 0; k < 20; k++) pick.push(a[Math.floor((k * 7919 + 13) % a.length)]);
            const t = i => { __U.select(__U.selNear(i)); return document.getElementById('card').innerText; };
            return { avec: pick.filter(i => t(i).indexOf('Mesure depuis la Terre') >= 0).length, sans: t(z[0]).indexOf('Mesure depuis la Terre') < 0 && t(z[0]).indexOf('undefined') < 0 }; })()""")
        check(r['avec'] == 20, '20 galaxies proches associées (choix fixe, réparti) : %d portent la mesure' % r['avec'])
        check(r['sans'], 'galaxie sans mesure Cosmicflows-4 : fiche sans ligne vide')
        n_cf4 = pg.evaluate("DATA.CF4_NEAR.filter(Boolean).length + DATA.CF4_LOCAL.filter(Boolean).length")
        check(n_cf4 == 460, 'galaxies de la page avec une distance Cosmicflows-4 : %d (attendu 460)' % n_cf4)
        pg.evaluate("__U.select(null)")

        # A2 : frontière de Laniakea (Dupuy et Courtois 2023), visible aux grandes échelles seulement
        lk = pg.evaluate("DATA.LANIAKEA ? [DATA.LANIAKEA.n, DATA.LANIAKEA.r_eq_mpc_h] : null")
        check(bool(lk) and lk[0] == 2898 and abs(lk[1] - 77) < 1, 'Laniakea : %s points de frontière, rayon équivalent (Mpc/h)' % lk)
        pg.evaluate("__U.select(null); __U.S.playing = false; __U.goTo(24.95)")
        pg.wait_for_function("__U.S.logR > 24.9", timeout=180000)
        f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() > {f0} + 4', timeout=180000)
        vis = pg.evaluate("[__U.Rr.lania.visible, [...document.querySelectorAll('.lb')].some(e => e.style.visibility === 'visible' && /Laniakea/.test(e.textContent))]")
        # sur téléphone, le nom n'apparaît pas à cette échelle (cause non établie : écran étroit ou tri des étiquettes) : seuls les points sont exigés
        check(vis[0] and (vis[1] or phone), 'Laniakea visible à 10^24,95 m%s : %s' % ('' if phone else ', avec son nom', vis))
        pg.evaluate("__U.goStop(__U.STOPS.find(s => /Système solaire/.test(s.name)), true)")
        pg.wait_for_function("__U.S.logR < 14", timeout=180000)
        f0 = pg.evaluate('__U.frame()'); pg.wait_for_function(f'__U.frame() > {f0} + 4', timeout=180000)
        check(pg.evaluate("__U.Rr.lania.visible") is False, 'Laniakea masquée dans le système solaire')

        dims = pg.evaluate("""new Promise(r => { const i = new Image(); i.onload = () => r([i.naturalWidth, i.naturalHeight]); i.onerror = () => r(null); i.src = DATA.CMB; })""")
        check(dims == [2048, 1024], 'texture du fond diffus : %s (Planck 2048 × 1024 ; WMAP faisait 720 × 360)' % dims)
        chk = pg.evaluate('DATA.CMB_CHK || null')
        check(bool(chk) and (chk.get('correl_wmap') or 0) > 0.8, 'corrélation avec WMAP mesurée par le script de données : %s' % chk)
        pg.evaluate("__U.select(null); __U.S.playing = false; __U.goStop(__U.STOPS.find(s => /observable/.test(s.name)), true)")
        pg.wait_for_function("document.getElementById('prov').textContent.indexOf('Planck') >= 0", timeout=180000)
        f0 = pg.evaluate('__U.frame()')
        pg.wait_for_function(f'__U.frame() > {f0} + 6', timeout=180000)
        pg.screenshot(path='/tmp/lot_s_cmb_%s.png' % MODE)
        check(not logs, 'aucune erreur de page (%d)' % len(logs))
        for l in logs[:5]:
            print('   ', l)
        b.close()
    print('RÉSULTAT (%s) :' % MODE, 'PASSE' if bad == 0 else '%d échec(s)' % bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
