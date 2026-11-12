#!/usr/bin/env python3
"""TOUTES les lunes dont la NASA publie la trajectoire -> lunes.tsv pour l'appli PC.

- Quelles lunes : celles présentes dans les fichiers d'éphémérides de la NASA (NAIF, generic_kernels/spk/satellites)
  rangés dans le dossier donné : jup365, jup347, jup348, jup349, sat441, sat415, sat455, sat456, sat457, sat459,
  ura184_part-3, ura116xl, nep097, nep104, nep105, plu060, mar099s. L'appli y lit leurs positions ; rien n'est calculé ici.
- Nom : celui du résumé officiel de ces fichiers (aa_summaries.txt) ; nom français pour les lunes de lunes.py.
- Rayon moyen (km) : table « Planetary Satellite Physical Parameters » du JPL (ssd.jpl.nasa.gov/sats/phys_par),
  sinon fichier pck00011.tpc de la NASA, sinon 0 : rayon NON MESURÉ (petites lunes vues comme un point ; on ne
  l'invente pas).
Sortie lunes.tsv : code NAIF, nom, code NAIF du centre de la planète, rayon moyen en km (0 : inconnu).
Usage : python lunes_toutes.py <dossier des fichiers .bsp> <dossier de sortie>
"""
import glob
import os
import re
import struct
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lunes import LUNES, PCK      # noqa: E402

SUMMARIES = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/aa_summaries.txt'
PHYS = 'https://ssd.jpl.nasa.gov/sats/phys_par/'
TYPES_LUS = (2, 3)      # types de données que l'appli sait lire (ephemeride.h)


def fetch(url: str, name: str) -> str:
    path = os.path.join(tempfile.gettempdir(), name)
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def bodies(path: str) -> dict[int, int]:
    """Corps d'un fichier d'éphémérides : code -> type de données."""
    out = {}
    with open(path, 'rb') as d:
        head = d.read(1024)
        nd, ni = struct.unpack('<ii', head[8:16])
        rec = struct.unpack('<i', head[76:80])[0]
        size = nd * 8 + ((ni + 1) // 2) * 8
        while rec:
            d.seek((rec - 1) * 1024)
            r = d.read(1024)
            nxt, _, n = struct.unpack('<ddd', r[:24])
            for k in range(int(n)):
                ints = struct.unpack(f'<{ni}i', r[24 + k * size + nd * 8:24 + k * size + nd * 8 + ni * 4])
                out[ints[0]] = ints[3]
            rec = int(nxt)
    return out


def planet_of(code: int) -> int:
    """Centre de la planète d'une lune : 506 -> 599, 55501 -> 599, 65158 -> 699."""
    return int(str(code)[0]) * 100 + 99


def main() -> None:
    kernels, sortie = sys.argv[1], sys.argv[2]
    moons: dict[int, int] = {}
    for f in sorted(glob.glob(os.path.join(kernels, '*.bsp'))):
        for code, kind in bodies(f).items():
            if (400 < code < 1000 and code % 100 != 99) or code > 10000:
                if kind in TYPES_LUS:
                    moons[code] = kind
    names = {int(b): a.strip() for a, b in re.findall(r'^\s*(?:Bodies:)?\s*([^()\n]+?) \((\d+)\) w\.r\.t', fetch(SUMMARIES, 'aa_summaries.txt'), re.M)}
    # Lunes récentes (ex. sat480, 2026) : leurs noms sont dans le commentaire du fichier lui-même (bloc FK de la NASA).
    for f in sorted(glob.glob(os.path.join(kernels, '*.bsp'))):
        with open(f, 'rb') as d:
            texte = d.read(200_000).decode('latin-1')
        for nom, code in re.findall(r"NAIF_BODY_NAME\s*\+=\s*\(\s*'([^']+)'\s*\)\s*NAIF_BODY_CODE\s*\+=\s*\(\s*(\d+)\s*\)", texte):
            names.setdefault(int(code), nom.strip())
    fr = {code: nom for code, nom, _ in LUNES}
    radius: dict[int, float] = {}
    pck = fetch(PCK, 'pck00011.tpc')
    for code in moons:
        m = re.search(r'BODY%d_RADII\s*=\s*\(([^)]*)\)' % code, pck)
        if m:
            r = [float(x) for x in m.group(1).split()]
            radius[code] = sum(r) / 3
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', fetch(PHYS, 'sats_phys_par.html'), re.S):
        c = [re.sub(r'<[^>]+>|&nbsp;', '', x).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)]
        if len(c) >= 5 and c[2].isdigit() and c[4].split():
            try:
                radius[int(c[2])] = float(c[4].split()[0])
            except ValueError:
                pass
    with open(os.path.join(sortie, 'lunes.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        for code in sorted(moons):
            raw = names.get(code, f'Lune {code}')
            nom = fr.get(code) or (raw.replace('_', ' ') if raw.startswith('S/') else raw.title())
            f.write(f'{code}\t{nom}\t{planet_of(code)}\t{radius.get(code, 0):.2f}\n')
    mesure = sum(1 for c in moons if radius.get(c, 0) > 0)
    par = {}
    for c in moons:
        par[planet_of(c)] = par.get(planet_of(c), 0) + 1
    print(f'{len(moons)} lunes écrites ; rayon mesuré pour {mesure}, inconnu pour {len(moons) - mesure} ; par planète : {dict(sorted(par.items()))}')


if __name__ == '__main__':
    main()
