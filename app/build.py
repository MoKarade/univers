#!/usr/bin/env python3
import os, sys
root = os.path.dirname(os.path.abspath(__file__))
rd = lambda p: open(os.path.join(root, p), encoding='utf-8').read()
html = rd('src/index.html')
js = '\n'.join(rd('src/' + f) for f in ['20_physics.js', '25_future.js', '26_orbits.js', '27_lens.js', '28_dust.js', '30_gen.js', '40_render.js', '60_app.js'])
import json
_d2 = rd('gen/data2.js'); _o = json.loads(_d2[len('Object.assign(DATA, '):_d2.rindex(');')])
for _k in ('STARS_GEO', 'STARS_AUX', 'STAR_LABELS', 'STARS_N', 'CMB'): _o.pop(_k, None)   # CMB : remplacée par la carte Planck de gen/data19.js
_d2 = 'Object.assign(DATA, ' + json.dumps(_o, ensure_ascii=False, separators=(',', ':')) + ');\n'
out = html.replace('/*__DATA__*/', rd('gen/data.js') + _d2 + rd('gen/ephem.js') + rd('gen/data3.js') + rd('gen/data4.js') + rd('gen/data5.js') + rd('gen/data6.js') + rd('gen/data7.js') + rd('gen/data8.js') + rd('gen/data9.js') + rd('gen/data10.js') + rd('gen/data11.js') + rd('gen/data12.js') + rd('gen/data13.js') + rd('gen/data14.js') + rd('gen/sun_rgb.js') + rd('gen/data15.js') + rd('gen/data16.js') + rd('gen/data18.js') + rd('gen/data19.js') + rd('gen/proton_pdf.js') + rd('gen/water_qm.js') + rd('gen/data20.js')).replace('/*__JS__*/', js)
assert '/*__DATA__*/' not in out and '/*__JS__*/' not in out
dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, '..', 'dist', 'index.html')
os.makedirs(os.path.dirname(dst), exist_ok=True)
open(dst, 'w', encoding='utf-8').write(out)
print('écrit', dst, round(len(out.encode()) / 1024), 'ko')
