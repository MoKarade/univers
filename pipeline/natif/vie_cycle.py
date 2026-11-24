#!/usr/bin/env python3
"""Cycle de vie des étoiles -> vie_cycle.bin (lu par natif/src/cycle_etoile.h).

Modèles PUBLIÉS, signalés comme modèles à l'écran :
  - Trajectoires d'évolution MIST v1.2 (Choi et al. 2016, ApJ 823, 102 ; Dotter 2016, ApJS 222, 8), [Fe/H] = 0,
    sans rotation (v/vcrit = 0), fichiers « EEP » de https://mist.science (archive
    MIST_v1.2_feh_p0.00_afe_p0.0_vvcrit0.0_EEPS.txz, 100 050 704 octets). Colonnes gardées : âge, masse, log L, log Teff,
    log R, masse du cœur de carbone-oxygène, phase.
  - Refroidissement des naines blanches : modèles de Montréal (Bédard et al. 2020, ApJ 901, 93), tables
    « Table_Mass_0.5 » à « Table_Mass_1.3 » de https://www.astro.umontreal.ca/~bergeron/CoolingModels/Tables/,
    atmosphère d'hydrogène pur. Colonnes gardées : Teff, log g, Mbol, âge de refroidissement.

Trajectoires écartées : celles que MIST n'a pas menées à leur terme alors que leurs voisines l'ont été (arrêts du calcul :
0,6 ; 0,65 ; 2,08 à 5,8 M☉ arrêtées en EEP 1409 ; 38 et 40 M☉ arrêtées en EEP 631). L'appli prend alors les voisines.
Les étoiles de moins de 0,6 M☉ restent : leur trajectoire s'arrête pendant la séquence principale, plus tard que l'âge
de l'Univers (aucune fin à montrer).

Format (petit-boutiste) :
  « UNIVCYC1 », nTraces (u32), nNaines (u32)
  pour chaque trace : m0 (f32), n (u32), fin (u8 : 0 naine blanche au bout de la trace ; 1 fin de la trace en EEP 808,
      masse < 8 M☉ (super-AGB : enveloppe à éjecter) ; 2 effondrement du cœur (EEP 808, masse >= 8 M☉) ;
      3 trace arrêtée pendant la séquence principale), 3 octets de bourrage, bourrage à 8 octets,
      âge (f64 × n, ans), masse, log L, log Teff, log R, cœur CO (f32 × n chacun), phase (i8 × n), bourrage à 8 octets.
  pour chaque naine : masse (f32), n (u32), âge (f64 × n), Teff, log g, Mbol (f32 × n), bourrage à 8 octets.

Usage : python vie_cycle.py <dossier des .track.eep> <dossier des tables de Montréal> <sortie vie_cycle.bin>
"""
import glob
import os
import struct
import sys

ECARTEES = {0.6, 0.65, 2.08, 2.58, 2.62, 3.2, 3.4, 3.8, 4.0, 4.6, 4.8, 5.8, 38.0, 40.0}
COLONNES = ('star_age', 'star_mass', 'log_L', 'log_Teff', 'log_R', 'c_core_mass', 'phase')
NAINES = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3)
SEUIL_EFFONDREMENT = 8.0      # M☉ ; Smartt 2009 (ARA&A 47, 63) : progéniteurs observés à partir de 8,5 (+1/-1,5) M☉ [Probable]


def lire_trace(chemin):
    lignes = [l for l in open(chemin) if l.strip()]
    entete = next(l for l in lignes if l.startswith('#') and 'star_age' in l).split()[1:]
    i0 = next(i for i, l in enumerate(lignes) if 'initial_mass' in l)
    m0 = float(lignes[i0 + 1].split()[1])
    idx = [entete.index(c) for c in COLONNES]
    rangs = [l.split() for l in lignes if not l.startswith('#')]
    cols = [[float(r[k]) for r in rangs] for k in idx]
    return m0, cols


def fin_de(m0, n):
    if n >= 1710:
        return 0
    if n == 808:
        return 2 if m0 >= SEUIL_EFFONDREMENT else 1
    return 3


def lire_naine(chemin):
    """Premier bloc (hydrogène pur) : Teff, log g, Mbol, âge (colonne 43)."""
    lignes = open(chemin).read().split('\n')[2:]
    pts = []
    for l in lignes:
        if not l.strip() or any(c.isalpha() and c not in 'Ee' for c in l):
            break
        v = l.split()
        pts.append((float(v[42]), float(v[0]), float(v[1]), float(v[2])))
    pts.sort()
    return pts


def bourrage(out):
    while len(out) % 8:
        out.append(0)


def main():
    src, montreal, dst = sys.argv[1:4]
    traces = []
    for f in sorted(glob.glob(os.path.join(src, '*.track.eep'))):
        m0, cols = lire_trace(f)
        if round(m0, 2) in ECARTEES:
            continue
        n = len(cols[0])
        fin = fin_de(m0, n)
        if fin == 3 and m0 >= 0.6:
            raise SystemExit(f'trace {m0} arrêtée en {n} : à écarter explicitement')
        traces.append((m0, n, fin, cols))
    naines = []
    for m in NAINES:
        pts = lire_naine(os.path.join(montreal, f'Table_Mass_{m}'))
        naines.append((m, pts))
    out = bytearray(b'UNIVCYC1')
    out += struct.pack('<II', len(traces), len(naines))
    for m0, n, fin, cols in traces:
        out += struct.pack('<fIB3x', m0, n, fin)
        bourrage(out)
        out += struct.pack(f'<{n}d', *cols[0])
        for c in cols[1:6]:
            out += struct.pack(f'<{n}f', *c)
        out += struct.pack(f'<{n}b', *[int(round(p)) for p in cols[6]])
        bourrage(out)
    for m, pts in naines:
        n = len(pts)
        out += struct.pack('<fI', m, n)
        out += struct.pack(f'<{n}d', *[p[0] for p in pts])
        for k in (1, 2, 3):
            out += struct.pack(f'<{n}f', *[p[k] for p in pts])
        bourrage(out)
    open(dst, 'wb').write(out)
    print(f'{len(traces)} traces, {len(naines)} tables de naines blanches, {len(out)} octets -> {dst}')
    for m0, n, fin, cols in traces:
        if m0 in (1.0, 20.0, 60.0):
            print(f'  {m0} M☉ : {n} points, fin {fin}, âge final {cols[0][-1] / 1e9:.4f} Ga, masse finale {cols[1][-1]:.3f}')


if __name__ == '__main__':
    main()
