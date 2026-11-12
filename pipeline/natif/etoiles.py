#!/usr/bin/env python3
"""Étoiles de la page -> fichier binaire de l'appli PC (jalon N1, docs/plan-natif.md).

Entrées, les mêmes que la page :
- app/gen/*.js : catalogue principal (STARS_*, HYG) et second catalogue embarqué (GAIA_*) ;
- les fichiers d'étoiles en flux (11 octets par étoile, base64), tels que publiés avec la page : dossier donné
  en argument, noms <id>.txt, liste et ordre lus dans TILE_MANIFEST (app/src/60_app.js).
Le décodage reprend exactement celui de la page (40_render.js : catalogue principal, catalogue Gaia,
addStarTile). Aucune valeur n'est inventée ni corrigée.

Sortie : etoiles.bin (format ci-dessous) et etoiles.json (étoiles nommées de la page : nom, numéro, distance).

Format etoiles.bin, petit-boutiste, tableaux en colonnes (une colonne par grandeur), chaque colonne alignée
sur 64 octets :
  octets 0-7   : « UNIVSTR1 »
  octets 8-15  : nombre d'étoiles n (entier 64 bits)
  octets 16-27 : n du catalogue principal, n du catalogue Gaia embarqué, n des fichiers en flux (3 entiers 32 bits)
  octet 64     : x[n], puis y[n], z[n] (float32, années-lumière, repère écliptique J2000 centré sur le Soleil),
                 mag[n] (float32, magnitude absolue : V pour le catalogue principal, G pour Gaia),
                 bv[n] (float32, indice de couleur B-V), vx[n], vy[n], vz[n] (float32, km/s, même repère)
Usage : python etoiles.py <dossier des fichiers en flux> <dossier de sortie>
"""
import base64, glob, json, math, os, re, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAGIC = b'UNIVSTR1'
ALIGN = 64


def data_keys(keys):
    """Lit des clés de DATA dans app/gen/data*.js, comme app/build.py les assemble : dans l'ordre des numéros, un
    fichier plus tardif remplace un plus ancien ; les étoiles de data2.js sont écartées (build.py les retire)."""
    retire_data2 = ('STARS_GEO', 'STARS_AUX', 'STAR_LABELS', 'STARS_N')
    files = glob.glob(os.path.join(ROOT, 'app', 'gen', 'data*.js'))
    files.sort(key=lambda f: int(re.search(r'data(\d*)\.js$', f).group(1) or 1))
    out = {}
    for f in files:
        s = open(f, encoding='utf-8').read()
        for k in keys:
            if os.path.basename(f) == 'data2.js' and k in retire_data2: continue
            m = re.search(r'"%s":' % re.escape(k), s)
            if m: out[k] = json.JSONDecoder().raw_decode(s, m.end())[0]
    missing = [k for k in keys if k not in out]
    if missing: raise SystemExit(f'clés absentes de app/gen : {missing}')
    return out


def sph(lon_u16, lat_u16, d):
    lon = lon_u16 / 65535 * 2 * math.pi; lat = (lat_u16 / 65535 - 0.5) * math.pi; cl = np.cos(lat)
    return np.stack([d * cl * np.cos(lon), d * cl * np.sin(lon), d * np.sin(lat)], axis=1)


def principal(D):
    n = D['STARS_N']; geo = np.frombuffer(base64.b64decode(D['STARS_GEO']), '<u2').reshape(-1, 3)[:n].astype(np.float64)
    aux = np.frombuffer(base64.b64decode(D['STARS_AUX']), 'u1').reshape(-1, 2)[:n].astype(np.float64)
    # Vitesses du catalogue principal : repère galactique (25_future.js, initStarKin : ve = M_GAL2ECL · v) ;
    # on les tourne dans le repère écliptique des positions, comme la page.
    vel = (np.frombuffer(base64.b64decode(D['STARS_VEL']), '<i2').reshape(-1, 3)[:n] / 20.0) @ np.array(D['M_GAL2ECL']).T
    pos = sph(geo[:, 0], geo[:, 1], 10 ** (geo[:, 2] / 65535 * 5.5 - 1))
    return pos, aux[:, 0] / 8 - 10, aux[:, 1] / 100 - 0.5, vel


def gaia(D):
    n = D['GAIA_N']; geo = np.frombuffer(base64.b64decode(D['GAIA_GEO']), '<u2').reshape(-1, 3)[:n].astype(np.float64)
    aux = np.frombuffer(base64.b64decode(D['GAIA_AUX']), 'u1').reshape(-1, 2)[:n].astype(np.float64)
    vel = np.frombuffer(base64.b64decode(D['GAIA_VEL']), 'i1').reshape(-1, 3)[:n] / 0.5
    pos = sph(geo[:, 0], geo[:, 1], 10 ** (geo[:, 2] / 65535 * 5))
    return pos, aux[:, 0] / 8 - 10, aux[:, 1] / 80 - 0.5, vel


def flux(dossier):
    src = open(os.path.join(ROOT, 'app', 'src', '60_app.js'), encoding='utf-8').read()
    man = re.search(r'TILE_MANIFEST = /\*__TILES__\*/(\[.*?\]);', src).group(1)
    tiles = [(m.group(1), int(m.group(2))) for m in re.finditer(r"kind: 'star', id: '([0-9a-f]{32})', n: (\d+)", man)]
    rec = np.dtype([('lon', '<u2'), ('lat', '<u2'), ('d', '<u2'), ('m', 'u1'), ('c', 'u1'), ('v', 'i1', 3)])
    parts = []
    for tid, n in tiles:
        raw = base64.b64decode(open(os.path.join(dossier, tid + '.txt'), 'rb').read())
        r = np.frombuffer(raw, rec)
        if len(r) != n: raise SystemExit(f'fichier {tid} : {len(r)} étoiles, {n} attendues')
        parts.append(r)
    r = np.concatenate(parts)
    pos = sph(r['lon'].astype(np.float64), r['lat'].astype(np.float64), 10 ** (r['d'].astype(np.float64) / 65535 * 5))
    return pos, r['m'] / 8.0 - 10, r['c'] / 80.0 - 0.5, r['v'] * 2.0      # vitesse : pas de 2 km/s (updateNear, 60_app.js)


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    os.makedirs(sortie, exist_ok=True)
    D = data_keys(['STARS_N', 'STARS_GEO', 'STARS_AUX', 'STARS_VEL', 'GAIA_N', 'GAIA_GEO', 'GAIA_AUX', 'GAIA_VEL', 'STAR_LABELS', 'M_GAL2ECL'])
    blocs = [principal(D), gaia(D), flux(dossier)]
    counts = [len(b[0]) for b in blocs]; n = sum(counts)
    cols = [np.concatenate([b[0][:, a] for b in blocs]) for a in range(3)] + [np.concatenate([b[1] for b in blocs]), np.concatenate([b[2] for b in blocs])] \
        + [np.concatenate([b[3][:, a] for b in blocs]) for a in range(3)]
    path = os.path.join(sortie, 'etoiles.bin')
    with open(path, 'wb') as f:
        head = MAGIC + np.int64(n).tobytes() + np.array(counts, '<i4').tobytes()
        f.write(head + b'\0' * (ALIGN - len(head)))
        for c in cols:
            b = c.astype('<f4').tobytes(); f.write(b + b'\0' * (-len(b) % ALIGN))
    json.dump(dict(n=n, catalogues=dict(principal=counts[0], gaia=counts[1], flux=counts[2]), nommees=D['STAR_LABELS']),
              open(os.path.join(sortie, 'etoiles.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    with open(os.path.join(sortie, 'etoiles_noms.tsv'), 'w', encoding='utf-8', newline='\n') as f:      # lu par l'appli PC
        for l in D['STAR_LABELS']: f.write(f"{l['i']}\t{l['n']}\t{l['d']}\n")
    print(f'{n} étoiles ({counts[0]} + {counts[1]} + {counts[2]}), {os.path.getsize(path) / 1e6:.1f} Mo -> {path}')


if __name__ == '__main__':
    main()
