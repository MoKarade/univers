#!/usr/bin/env python3
"""Astéroïdes de la page -> fichier de l'appli PC (étape E3, docs/plan-natif.md).

Entrée : le fichier d'astéroïdes en flux publié avec la page (TILE_MANIFEST, 28 octets par objet : demi-grand axe en
UA, excentricité, inclinaison, nœud, argument du périhélie, anomalie moyenne à l'époque — en radians —, magnitude
absolue H ; source : JPL Small-Body Database) et sa liste de noms. Époque : DATA.AST_EPOCH (jour julien).
Le décodage reprend celui de la page (40_render.js, addAstTile) : pour chaque orbite, les deux vecteurs P et Q du
plan de l'ellipse, tels que position = P (cos E - e) + Q sin E, où E est l'anomalie excentrique.

Sorties :
- asteroides.bin : « UNIVAST1 », n (entier 64 bits), époque (réel 64 bits, jour julien), puis à l'octet 64 dix
  colonnes float32 alignées sur 64 octets : Px, Py, Pz, Qx, Qy, Qz (UA, écliptique J2000, centre : Soleil),
  e, M0 (radians), n (radians par jour), H ;
- asteroides_noms.txt : un nom par ligne, même ordre.
Avec --controle : compare quelques astéroïdes à JPL Horizons (ref_asteroides.json) 154 jours après l'époque ;
l'orbite simple (sans l'attraction des planètes) doit s'en écarter de moins de 0,002 UA.
Usage : python asteroides.py <dossier des fichiers en flux> <dossier de sortie> [--controle]
"""
import base64, json, math, os, re, shutil, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etoiles import ROOT, ALIGN, data_keys      # noqa: E402

MAGIC = b'UNIVAST1'
K_GAUSS = 0.01720209895      # constante de Gauss : rad/jour pour a = 1 UA


def position(cols, i, jd, epoch):
    """Position héliocentrique (UA) de l'astéroïde i au jour julien jd, par l'équation de Kepler."""
    px, py, pz, qx, qy, qz, e, m0, n, _ = (float(c[i]) for c in cols)
    M = (m0 + n * (jd - epoch)) % (2 * math.pi); E = M
    for _ in range(30): E -= (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
    c, s = math.cos(E) - e, math.sin(E)
    return np.array([px * c + qx * s, py * c + qy * s, pz * c + qz * s])


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    os.makedirs(sortie, exist_ok=True)
    epoch = float(data_keys(['AST_EPOCH'])['AST_EPOCH'])
    src = open(os.path.join(ROOT, 'app', 'src', '60_app.js'), encoding='utf-8').read()
    man = re.search(r'TILE_MANIFEST = /\*__TILES__\*/(\[.*?\]);', src).group(1)
    m = re.search(r"kind: 'ast', id: '([0-9a-f]{32})', n: (\d+), mb: [\d.]+, names: '([0-9a-f]{32})'", man)
    tid, n, names_id = m.group(1), int(m.group(2)), m.group(3)
    f = np.frombuffer(base64.b64decode(open(os.path.join(dossier, tid + '.txt'), 'rb').read()), '<f4').reshape(-1, 7).astype(np.float64)
    if len(f) != n: raise SystemExit(f'{len(f)} astéroïdes, {n} attendus')
    a, e, inc, om, w, m0, H = f.T
    b = a * np.sqrt(1 - e * e); co, so, ci, si, cw, sw = np.cos(om), np.sin(om), np.cos(inc), np.sin(inc), np.cos(w), np.sin(w)
    cols = [a * (co * cw - so * sw * ci), a * (so * cw + co * sw * ci), a * sw * si,
            b * (-co * sw - so * cw * ci), b * (-so * sw + co * cw * ci), b * cw * si, e, m0, K_GAUSS / a ** 1.5, H]
    path = os.path.join(sortie, 'asteroides.bin')
    with open(path, 'wb') as out:
        head = MAGIC + np.int64(n).tobytes() + np.float64(epoch).tobytes()
        out.write(head + b'\0' * (ALIGN - len(head)))
        for c in cols:
            raw = c.astype('<f4').tobytes(); out.write(raw + b'\0' * (-len(raw) % ALIGN))
    shutil.copyfile(os.path.join(dossier, names_id + '.txt'), os.path.join(sortie, 'asteroides_noms.txt'))
    names = open(os.path.join(sortie, 'asteroides_noms.txt'), encoding='utf-8').read().split('\n')
    print(f'{n} astéroïdes, époque JJ {epoch}, a de {a.min():.2f} à {a.max():.1f} UA, {os.path.getsize(path) / 1e6:.1f} Mo ; {len(names)} noms')
    if '--controle' in sys.argv:
        # Référence : ref_asteroides.json (JPL Horizons, demandé par ref_asteroides.py), héliocentrique, écliptique J2000.
        ref = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ref_asteroides.json'), encoding='utf-8'))
        number = {nm.split('~')[-1]: k for k, nm in enumerate(names)}
        ok, judged = True, 0
        for num, want in ref['corps'].items():
            i = number.get(num)
            if i is None: continue
            got = position([c.astype(np.float32) for c in cols], i, ref['jd'], epoch)
            d = float(np.linalg.norm(got - np.array(want))); good = d < 0.002; ok &= good; judged += 1
            print(f"{names[i]} au JJ {ref['jd']} : écart avec JPL Horizons {d:.6f} UA ({d * 149597870.7:.0f} km) -> {'PASSE' if good else 'ÉCHEC'}")
        if judged < 3: ok = False; print('moins de 3 astéroïdes de référence trouvés : ÉCHEC')
        sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
