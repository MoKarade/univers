#!/usr/bin/env python3
"""Retire de app/gen/data2.js les 5 clés que build_data2.py n'écrit plus (DATA2_CLES_MORTES), sans relancer le calcul.

Pourquoi : les sources brutes de build_data2.py (dr16q.tsv, wmap_ilc.fits...) ne sont pas dans le dépôt. Ce script applique
au fichier existant exactement la modification faite au générateur : mêmes clés retirées, même écriture JSON (ordre des
clés gardé). Le reste du fichier est inchangé octet pour octet (aller-retour vérifié). Lancé une fois le 26/11/2026.
Usage : python3 pipeline/data2_sans_cles_mortes.py
"""
import json, os
CLES = ('STARS_GEO', 'STARS_AUX', 'STAR_LABELS', 'STARS_N', 'CMB')      # = DATA2_CLES_MORTES de build_data2.py
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app', 'gen', 'data2.js')
s = open(p, encoding='utf-8').read(); tete = 'Object.assign(DATA, '
o = json.loads(s[len(tete):s.rindex(');')])
assert tete + json.dumps(o, ensure_ascii=False, separators=(',', ':')) + ');\n' == s, 'data2.js ne suit pas le format de build_data2.py'
for k in CLES: o.pop(k, None)
open(p, 'w', encoding='utf-8').write(tete + json.dumps(o, ensure_ascii=False, separators=(',', ':')) + ');\n')
print('data2.js :', len(s), '->', os.path.getsize(p), 'octets')
