#!/usr/bin/env python3
"""Galaxies et quasars de la page -> fichiers de l'appli PC (étape E4, docs/plan-natif.md).

Entrées, les mêmes que la page :
- app/gen/data2.js : relevés embarqués (SURV : 2MRS, puis 6dF/2dF/SDSS/DESI, puis quasars), 6 octets par objet ;
- les fichiers de galaxies en flux (6 octets par objet, base64), tels que publiés avec la page (TILE_MANIFEST) ;
- app/gen/data16.js : couleur selon le décalage vers le rouge (ZCOL : spectre Sb de Kinney et al. 1996 pour les
  galaxies, composante moyenne SDSS pour les quasars, intégrés sur l'observateur CIE 1931) ;
- app/gen/data.js et data2.js : galaxies nommées (LOCAL : Groupe local et voisines ; FAR : galaxies plus lointaines).
Le décodage reprend exactement celui de la page (40_render.js). Chaque objet garde sa direction mesurée et son
décalage vers le rouge mesuré ; la distance n'est PAS écrite : l'appli la calcule d'après la cosmologie choisie.

Sorties :
- galaxies.bin : « UNIVGAL1 », n (entier 64 bits), puis à l'octet 64 les colonnes alignées sur 64 octets :
  dx[n], dy[n], dz[n] (float32, direction unitaire, repère écliptique J2000), z[n] (float32, décalage vers le rouge),
  couleur[n] (4 octets : rouge, vert, bleu tels que la page les affiche ; 4e octet : 255 pour un quasar, 0 sinon) ;
- galaxies_noms.tsv : nom, x, y, z (années-lumière, écliptique, centre : Soleil), genre.
Usage : python galaxies.py <dossier des fichiers en flux> <dossier de sortie>
"""
import base64, json, math, os, re, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etoiles import ROOT, ALIGN, data_keys      # noqa: E402

MAGIC = b'UNIVGAL1'
MPC_LY = 3.0856775814913673e22 / 9.4607304725808e15


def unit(lon_u16, lat):
    lon = lon_u16 / 65535 * 2 * math.pi; cl = np.cos(lat)
    return np.stack([cl * np.cos(lon), cl * np.sin(lon), np.sin(lat)], axis=1)


def embarques(D):
    sv = np.frombuffer(base64.b64decode(D['SURV']), '<u2').reshape(-1, 3).astype(np.float64)
    n1, n2 = D['SURV_N'][0], D['SURV_N'][0] + D['SURV_N'][1]
    z = np.exp(sv[:, 2] / 65535 * math.log(1 + D['SURV_ZMAX'])) - 1
    quasar = np.arange(len(sv)) >= n2
    return unit(sv[:, 0], (sv[:, 1] / 65535 - 0.5) * math.pi), z, quasar


def flux(D, dossier):
    src = open(os.path.join(ROOT, 'app', 'src', '60_app.js'), encoding='utf-8').read()
    man = re.search(r'TILE_MANIFEST = /\*__TILES__\*/(\[.*?\]);', src).group(1)
    tiles = [(m.group(1), int(m.group(2))) for m in re.finditer(r"kind: 'gal', id: '([0-9a-f]{32})', n: (\d+)", man)]
    parts = []
    for tid, n in tiles:
        r = np.frombuffer(base64.b64decode(open(os.path.join(dossier, tid + '.txt'), 'rb').read()), '<u2').reshape(-1, 3)
        if len(r) != n: raise SystemExit(f'fichier {tid} : {len(r)} objets, {n} attendus')
        parts.append(r)
    r = np.concatenate(parts).astype(np.int64)
    w = r[:, 1]
    z = np.exp(r[:, 2] / 65535 * math.log(1 + D['SURV_ZMAX'])) - 1
    return unit(r[:, 0].astype(np.float64), ((w & 32767) / 32767 - 0.5) * math.pi), z, (w >> 15) > 0


def couleurs(D, z, quasar):
    """Couleur de la page (shader « surv », zcol) : table de n pas sur log(1+z), bornée au dernier pas."""
    ZC = D['ZCOL']; n = ZC['n']
    out = np.zeros((len(z), 4), np.uint8)
    for table, zmax, sel in ((np.array(ZC['gal']).reshape(n, 3), ZC['zg'], ~quasar), (np.array(ZC['qso']).reshape(n, 3), ZC['zq'], quasar)):
        x = np.clip(np.log1p(z[sel]) / math.log(1 + zmax), 0, 1) * (n - 1)
        k = np.minimum(x.astype(int), n - 2); f = (x - k)[:, None]
        out[sel, :3] = np.round(255 * np.clip(table[k] * (1 - f) + table[k + 1] * f, 0, 1))
    out[quasar, 3] = 255
    return out


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    os.makedirs(sortie, exist_ok=True)
    D = data_keys(['SURV', 'SURV_N', 'SURV_ZMAX', 'ZCOL', 'LOCAL', 'FAR'])
    blocs = [embarques(D), flux(D, dossier)]
    d = np.concatenate([b[0] for b in blocs]); z = np.concatenate([b[1] for b in blocs]); q = np.concatenate([b[2] for b in blocs])
    n = len(z); col = couleurs(D, z, q)
    path = os.path.join(sortie, 'galaxies.bin')
    with open(path, 'wb') as f:
        head = MAGIC + np.int64(n).tobytes()
        f.write(head + b'\0' * (ALIGN - len(head)))
        for c in (d[:, 0], d[:, 1], d[:, 2], z):
            b = c.astype('<f4').tobytes(); f.write(b + b'\0' * (-len(b) % ALIGN))
        b = col.tobytes(); f.write(b + b'\0' * (-len(b) % ALIGN))
    genres = {'spiral': 'galaxie spirale', 'irr': 'galaxie irrégulière', 'ell': 'galaxie elliptique', 'dsph': 'galaxie naine sphéroïdale',
              'dwarf': 'galaxie naine', 'gal': 'galaxie'}
    with open(os.path.join(sortie, 'galaxies_noms.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        for g in D['LOCAL'] + D['FAR']:      # positions en Mpc, repère écliptique (contrôlé sur Andromède)
            x, y, zz = (c * MPC_LY for c in g['pos'])
            f.write(f"{g['n']}\t{x!r}\t{y!r}\t{zz!r}\t{genres.get(g.get('k'), 'galaxie')}\t{g.get('p', 3)}\n")
    print(f"{n} galaxies et quasars ({len(blocs[0][1])} embarqués + {len(blocs[1][1])} en flux, dont {int(q.sum())} quasars), "
          f"z de {z.min():.4f} à {z.max():.3f}, {os.path.getsize(path) / 1e6:.1f} Mo ; {len(D['LOCAL']) + len(D['FAR'])} galaxies nommées")


if __name__ == '__main__':
    main()
