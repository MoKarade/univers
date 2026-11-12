#!/usr/bin/env python3
"""Lot G natif : état de départ du calcul à N corps (app/gen/nbody.js, calé sur DE440 par pipeline/gravite/ajuste.js) et
références JPL Horizons (app/test/nbody_ref.json), réécrits en en-têtes C++ pour natif/physique/nbody_noyau.h et son essai."""
import json, os
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.join(here, '..', '..')
t = open(os.path.join(root, 'app', 'gen', 'nbody.js'), encoding='utf-8').read()
nb = json.loads(t[t.index('{ NB: ') + 6:t.rindex(' });')])
ref = json.load(open(os.path.join(root, 'app', 'test', 'nbody_ref.json')))
f = lambda xs: ', '.join(repr(float(x)) for x in xs)
out = ['// Généré par pipeline/natif/nbody_donnees.py : ne pas éditer à la main.', '#pragma once', 'namespace nbody_donnees {',
       f'constexpr double kJd0 = {nb["jd"]!r};      // TDB', f'constexpr double kDtDays = {nb["dt"]!r};',
       f'constexpr int kN = {len(nb["names"])};', 'constexpr const char* kNames[] = {' + ', '.join(f'"{n}"' for n in nb['names']) + '};',
       f'constexpr double kGm[] = {{{f(nb["gm"])}}};      // UA³/jour² (DE440)',
       f'constexpr double kQ[] = {{{f(nb["Q"])}}};      // héliocentrique, UA, écliptique J2000',
       f'constexpr double kV[] = {{{f(nb["V"])}}};      // barycentrique, UA/jour (vitesses calées sur DE440, 1650-2450)',
       f'constexpr double kScale[] = {{{f(nb["scale"])}}};      // facteur de calage des vitesses héliocentriques (biais du pas de 4 jours)', '}']
open(os.path.join(root, 'natif', 'physique', 'nbody_donnees.h'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
names = ['sun'] + nb['names']
rows = []
for d, R in sorted(ref['checks'].items()):
    rows.append('  {"%s", %r, {%s}},' % (d, R['sun']['jd'], ', '.join(f(R[n]['r']) for n in names)))
out = ['// Généré par pipeline/natif/nbody_donnees.py : positions barycentriques JPL Horizons (UA, écliptique J2000) pour essai_nbody.', '#pragma once',
       'struct NbRef { const char* date; double jd; double r[%d]; };' % (3 * len(names)), 'constexpr NbRef kNbRefs[] = {'] + rows + ['};']
open(os.path.join(root, 'natif', 'physique', 'essais', 'nbody_ref.h'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('écrit nbody_donnees.h et nbody_ref.h')
