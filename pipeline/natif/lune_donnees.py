#!/usr/bin/env python3
"""Lot G natif : tables de la théorie lunaire de Meeus (chap. 47, d'après ELP-2000/82 de Chapront) utilisées par la page
(DATA.MOON_LR, DATA.MOON_B, app/gen/), réécrites en en-tête C++ pour natif/physique/lune.h."""
import json, os, re
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
lr = b = None
for f in os.listdir(os.path.join(root, 'app', 'gen')):
    t = open(os.path.join(root, 'app', 'gen', f), encoding='utf-8').read()
    m = re.search(r'"MOON_LR":(\[[^\]]*\])', t); n = re.search(r'"MOON_B":(\[[^\]]*\])', t)
    if m: lr = json.loads(m.group(1))
    if n: b = json.loads(n.group(1))
assert lr and b, 'tables introuvables'
out = ['// Généré par pipeline/natif/lune_donnees.py : ne pas éditer.', '#pragma once', 'namespace lune_donnees {',
       'constexpr double kLr[] = {' + ', '.join(map(str, lr)) + '};      // D, M, M\', F, Σl (1e-6 °), Σr (1e-3 km)',
       'constexpr double kB[] = {' + ', '.join(map(str, b)) + '};      // D, M, M\', F, Σb (1e-6 °)', '}']
open(os.path.join(root, 'natif', 'physique', 'lune_donnees.h'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print(len(lr) // 6, 'termes l, r ;', len(b) // 5, 'termes b')
