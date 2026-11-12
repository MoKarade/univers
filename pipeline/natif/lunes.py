#!/usr/bin/env python3
"""Lunes des planètes -> lunes.tsv pour l'appli PC, et positions de référence pour le contrôle.

- Rayon moyen : moyenne des trois demi-axes du fichier officiel de la NASA (NAIF, pck00011.tpc, BODYnnn_RADII).
- Positions : lues par l'appli dans les fichiers d'éphémérides de la NASA (jup365.bsp, sat441.bsp…), pas ici.
- Avec --reference : demande à JPL Horizons la position de chaque lune par rapport au centre de masse du système
  solaire (écliptique J2000, UA et UA/jour) au jour julien 2461354.5 et l'écrit dans ref_lunes.txt, au format lu par
  natif/src/essai_ephem.cpp (code, jour julien, x y z vx vy vz).
Sortie lunes.tsv : code NAIF, nom français, code NAIF de la planète, rayon moyen en km.
Usage : python lunes.py <dossier de sortie> [--reference]
"""
import os, re, sys, tempfile, urllib.parse, urllib.request

PCK = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc'
# code NAIF, nom français, planète (code de son centre)
LUNES = [(401, 'Phobos', 499), (402, 'Déimos', 499),
         (501, 'Io', 599), (502, 'Europe', 599), (503, 'Ganymède', 599), (504, 'Callisto', 599),
         (601, 'Mimas', 699), (602, 'Encelade', 699), (603, 'Téthys', 699), (604, 'Dioné', 699), (605, 'Rhéa', 699), (606, 'Titan', 699), (608, 'Japet', 699),
         (701, 'Ariel', 799), (702, 'Umbriel', 799), (703, 'Titania', 799), (704, 'Obéron', 799), (705, 'Miranda', 799),
         (801, 'Triton', 899), (901, 'Charon', 999)]
JD = 2461354.5


def main():
    sortie = sys.argv[1]
    path = os.path.join(tempfile.gettempdir(), 'pck00011.tpc')
    if not os.path.exists(path): urllib.request.urlretrieve(PCK, path)
    pck = open(path, encoding='latin-1').read()
    with open(os.path.join(sortie, 'lunes.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        for code, nom, planete in LUNES:
            m = re.search(r'BODY%d_RADII\s*=\s*\(([^)]*)\)' % code, pck)
            if not m: raise SystemExit(f'{nom} : rayons absents du fichier de la NASA')
            r = [float(x) for x in m.group(1).split()]
            f.write(f'{code}\t{nom}\t{planete}\t{sum(r) / 3:.2f}\n')
    print(len(LUNES), 'lunes écrites')
    if '--reference' in sys.argv:
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, 'ref_lunes.txt'), 'w', encoding='ascii', newline='\n') as f:
            for code, nom, _ in LUNES:
                q = {'format': 'text', 'COMMAND': f"'{code}'", 'OBJ_DATA': 'NO', 'MAKE_EPHEM': 'YES', 'EPHEM_TYPE': 'VECTORS', 'CENTER': "'500@0'",
                     'REF_PLANE': 'ECLIPTIC', 'REF_SYSTEM': 'ICRF', 'OUT_UNITS': 'AU-D', 'VEC_TABLE': '2', 'TLIST': f"'{JD}'"}
                txt = urllib.request.urlopen('https://ssd.jpl.nasa.gov/api/horizons.api?' + urllib.parse.urlencode(q), timeout=60).read().decode('utf-8', 'replace')
                m = re.search(r'\$\$SOE(.*?)\$\$EOE', txt, re.S)
                v = re.findall(r'[XYZ]\s*=\s*(\S+)', m.group(1)) if m else []
                if len(v) < 6: print(nom, ': pas de réponse exploitable de Horizons'); continue
                f.write(' '.join([str(code), repr(JD)] + v[:6]) + '\n')
                print(nom, v[:3])


if __name__ == '__main__':
    main()
