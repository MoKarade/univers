#!/usr/bin/env python3
"""Contrôle de etoiles.bin contre des valeurs indépendantes du décodage : coordonnées équatoriales J2000 de cinq
étoiles brillantes (catalogue Hipparcos) et distances de la table STAR_LABELS de la page.
Tolérance : 0,05° sur la direction (le codage sur 16 bits vaut 0,0055°), 0,5 % sur la distance.
Usage : python test_etoiles.py <dossier de sortie de etoiles.py>
"""
import json, math, os, sys
import numpy as np

# nom dans la page, ascension droite (h, min, s), déclinaison (signe, °, ′, ″), J2000
# [Probable : valeurs Hipparcos recopiées de mémoire, à 1″ près ; la tolérance du test est de 180″]
REF = [('Sirius', (6, 45, 8.9), (-1, 16, 42, 58)), ('Véga', (18, 36, 56.3), (1, 38, 47, 1)), ('Rigel', (5, 14, 32.3), (-1, 8, 12, 6)),
       ('Bételgeuse', (5, 55, 10.3), (1, 7, 24, 25)), ('Arcturus', (14, 15, 39.7), (1, 19, 10, 57))]
EPS = math.radians(23.4392911)


def main():
    d = sys.argv[1]
    with open(os.path.join(d, 'etoiles.json'), encoding='utf-8') as fh:
        meta = json.load(fh)
    n = meta['n']
    raw = np.memmap(os.path.join(d, 'etoiles.bin'), dtype='u1', mode='r')
    assert bytes(raw[:8]) == b'UNIVSTR1' and int(np.frombuffer(raw[8:16], '<i8')[0]) == n
    col = -(-4 * n // 64) * 64
    x, y, z = (np.frombuffer(raw, '<f4', n, 64 + k * col) for k in range(3))
    lab = {l['n']: l for l in meta['nommees']}; ok = True
    for l in meta['nommees']:
        i = l['i']; dist = math.sqrt(float(x[i]) ** 2 + float(y[i]) ** 2 + float(z[i]) ** 2)
        if abs(dist / l['d'] - 1) > 0.005: ok = False; print(f'ÉCHEC distance {l["n"]} : {dist:.3f} contre {l["d"]}')
    print(f'{len(lab)} étoiles nommées : distances conformes à la page' if ok else 'distances : ÉCHEC')
    found = 0
    for name, (h, mi, s), (sg, dg, dm, ds) in REF:
        if name not in lab: print(f'{name} : absente des étoiles nommées de la page'); continue
        found += 1; i = lab[name]['i']
        ra = math.radians(15 * (h + mi / 60 + s / 3600)); de = sg * math.radians(dg + dm / 60 + ds / 3600)
        e = np.array([math.cos(de) * math.cos(ra), math.cos(de) * math.sin(ra), math.sin(de)])
        ecl = np.array([e[0], math.cos(EPS) * e[1] + math.sin(EPS) * e[2], -math.sin(EPS) * e[1] + math.cos(EPS) * e[2]])
        p = np.array([x[i], y[i], z[i]], float); p /= np.linalg.norm(p)
        ang = math.degrees(math.acos(max(-1.0, min(1.0, float(p @ ecl))))); good = ang < 0.05; ok &= good
        print(f'{name:11s} : écart de direction {ang:.4f}° -> {"PASSE" if good else "ÉCHEC"}')
    if found < 3: ok = False; print('moins de 3 étoiles de référence trouvées : ÉCHEC')
    # Vitesse le long de la ligne de visée : valeurs publiées (SIMBAD) [Probable : recopiées de mémoire], tolérance 2 km/s.
    vx, vy, vz = (np.frombuffer(raw, '<f4', n, 64 + k * col) for k in range(5, 8))
    # Sirius n'est pas jugée : le catalogue HYG de la page lui donne -9,4 km/s, la valeur publiée est -5,5 km/s.
    # Écart du catalogue source, connu, à corriger quand les vitesses viendront de Gaia ou de SIMBAD (plan-natif.md).
    for name, rv in (('Aldébaran', 54.3), ('Véga', -13.9), ('Arcturus', -5.2)):
        if name not in lab: print(f'{name} : absente'); continue
        i = lab[name]['i']; p = np.array([x[i], y[i], z[i]], float); v = np.array([vx[i], vy[i], vz[i]], float)
        got = float(v @ p / np.linalg.norm(p)); good = abs(got - rv) < 2.0; ok &= good
        print(f'{name:11s} : vitesse radiale {got:+.1f} km/s (publiée {rv:+.1f}) -> {"PASSE" if good else "ÉCHEC"}')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
