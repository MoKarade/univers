"""Trajectoires d'évolution MIST v1.2 vues dans les bandes de Gaia -> mist_traces.bin (lu par natif/src/vie_etoiles.h).

Sources (modèles publiés, rien d'ajusté ici) :
- trajectoires MIST v1.2, [Fe/H] = 0, rotation v/vcrit = 0,4 (Choi et al. 2016, ApJ 823, 102 ; Dotter 2016,
  ApJS 222, 8), fichiers « EEP » de https://mist.science (196 masses de 0,1 à 300 masses solaires) ;
- corrections bolométriques MIST v1 « UBVRIplus » (Gaia EDR3 G, BP, RP ; Johnson B, V), sans poussière (A_V = 0).

Composition solaire pour toutes les étoiles : c'est aussi l'hypothèse des âges FLAME de Gaia DR3 (Creevey et al. 2023),
et la composition [M/H] de GSP-Phot porte de forts écarts connus (Andrae et al. 2023). [Probable] Dit à l'écran.

Calcul :
- magnitude absolue M_x = 4,74 - 2,5 log L - BC_x(Teff, log g) (4,74 = magnitude bolométrique du Soleil, convention MIST) ;
  couleur BP-RP = BC_RP - BC_BP ; B-V = BC_V - BC_B ;
- 2000 trajectoires à masses régulières en logarithme (pas de 0,4 %), interpolées entre les deux trajectoires MIST
  voisines à point d'évolution égal (EEP), comme le font les isochrones MIST (âge en log, le reste linéaire en log masse) ;
- pour chaque point, la plage d'âge où l'éclat G change de moins de 0,01 mag et BP-RP de moins de 0,015 (« fenêtre
  calme ») : l'appli n'y recalcule rien.

Format mist_traces.bin (petit-boutiste) :
  « UNIVMST1 », nTraces (u32), nEep (u32)
  masse initiale (f32 × nTraces), points utiles (u32 × nTraces), fin (u8 × nTraces : 0 = naine blanche, 1 = supernova)
  puis, pour chaque trace, 3 tableaux de nEep f64 : âge (ans), début et fin de la fenêtre calme (âges) ; 6 tableaux de
  nEep f32 : G, BP-RP, V, B-V, log L, log Teff ; puis nEep octets de phase MIST (-1 jeunesse, 0 séquence principale, 2 géante, 3 hélium au cœur,
  4-5 branche asymptotique, 6 vers naine blanche, 9 Wolf-Rayet ; 255 = au-delà de la fin)

Usage : python mist_gaia.py <dossier des trajectoires EEP [Fe/H]=0> <fichier fehp000.UBVRIplus> <sortie mist_traces.bin>
"""
import glob
import os
import sys

import numpy as np
from scipy.interpolate import RegularGridInterpolator

N_EEP = 1710
N_TRACES = 2000
M_MIN, M_MAX = 0.1, 300.0
MBOL_SOLEIL = 4.74
SEUIL_G, SEUIL_C = 0.01, 0.015
MASSE_SUPERNOVA = 8.0      # au-delà de cette masse initiale, la trace finit en supernova (fin du carbone au cœur) [Probable]


def lire_trace(chemin: str) -> tuple[float, str, np.ndarray]:
    with open(chemin) as f:
        lignes = f.readlines()
    entete = lignes[7].split()      # « # masse N_pts N_EEP N_col phase type »
    masse, genre = float(entete[1]), entete[-1]
    noms = lignes[11].split()[1:]
    d = np.loadtxt(lignes[12:])
    col = {n: d[:, i] for i, n in enumerate(noms)}
    return masse, genre, np.stack([col['star_age'], col['log_L'], col['log_Teff'], col['log_g'], col['phase']], 1)


def correcteur(chemin: str):
    """BC(Teff, log g) pour G, BP, RP, B, V (A_V = 0), interpolation linéaire sur la grille complète 70 × 26."""
    with open(chemin) as f:
        lignes = [l for l in f if not l.startswith('#')]
    d = np.loadtxt(lignes)
    d = d[d[:, 3] == 0.0]
    teff, logg = np.unique(d[:, 0]), np.unique(d[:, 1])
    if len(teff) * len(logg) != len(d):
        sys.exit('grille des corrections bolométriques incomplète')
    o = np.lexsort((d[:, 1], d[:, 0]))
    d = d[o]
    colonnes = {'G': 26, 'BP': 27, 'RP': 28, 'B': 6, 'V': 7}      # indices (base 0) : Gaia_*_EDR3, Bessell_B, Bessell_V
    fonctions = {k: RegularGridInterpolator((teff, logg), d[:, c].reshape(len(teff), len(logg))) for k, c in colonnes.items()}

    def bc(log_teff: np.ndarray, log_g: np.ndarray) -> dict:
        p = np.stack([np.clip(10 ** log_teff, teff[0], teff[-1]), np.clip(log_g, logg[0], logg[-1])], 1)
        return {k: f(p) for k, f in fonctions.items()}
    return bc


def interpoler(masse: float, grille: list) -> tuple[np.ndarray, int, int]:
    """Trace à la masse voulue entre les deux voisines, à EEP égal. Renvoie (N_EEP × 5, points utiles, fin)."""
    masses = np.array([g[0] for g in grille])
    j = int(np.clip(np.searchsorted(masses, masse) - 1, 0, len(masses) - 2))
    (m1, g1, t1), (m2, g2, t2) = grille[j], grille[j + 1]
    w = (np.log(masse) - np.log(m1)) / (np.log(m2) - np.log(m1))
    n = min(len(t1), len(t2))
    a, b = t1[:n], t2[:n]
    out = np.full((N_EEP, 5), np.nan)
    out[:n, 0] = 10 ** ((1 - w) * np.log10(a[:, 0]) + w * np.log10(b[:, 0]))
    out[:n, 1:4] = (1 - w) * a[:, 1:4] + w * b[:, 1:4]
    out[:n, 4] = np.where(w < 0.5, a[:, 4], b[:, 4])
    # l'âge doit croître : une interpolation peut créer un pas nul ou négatif aux EEP très rapprochés
    out[:n, 0] = np.maximum.accumulate(out[:n, 0])
    fin = 1 if masse >= MASSE_SUPERNOVA else 0
    return out, n, fin


def fenetres(age: np.ndarray, G: np.ndarray, C: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Pour chaque point k, plus vieil âge (et plus jeune) où |G - G_k| < SEUIL_G et |C - C_k| < SEUIL_C sans interruption."""
    # Les âges peuvent se répéter (pas très rapides) : la fenêtre s'arrête STRICTEMENT avant l'âge du premier point hors
    # seuil, sinon un âge égal désignerait un point déjà hors fenêtre.
    lo, hi = np.full(N_EEP, np.nan), np.full(N_EEP, np.nan)
    a = age[:n]
    for k in range(n):
        ok = (np.abs(G[:n] - G[k]) < SEUIL_G) & (np.abs(C[:n] - C[k]) < SEUIL_C)
        apres = np.nonzero(~ok[k:])[0]
        avant = np.nonzero(~ok[:k + 1][::-1])[0]
        if len(apres):
            mauvais = a[k + apres[0]]
            dedans = a[k:k + apres[0]]
            dedans = dedans[dedans < mauvais]
            hi[k] = dedans[-1] if len(dedans) else a[k]
        else:
            hi[k] = a[n - 1]      # calme jusqu'à la fin de la trace (la suite est traitée à part)
        if len(avant):
            mauvais = a[k - avant[0]]
            dedans = a[k - avant[0] + 1:k + 1]
            dedans = dedans[dedans > mauvais]
            lo[k] = dedans[0] if len(dedans) else a[k]
        else:
            lo[k] = a[0]      # calme depuis la naissance (avant : pas encore née)
    return lo, hi


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    dossier, fichier_bc, sortie = sys.argv[1:4]
    grille = sorted(lire_trace(c) for c in glob.glob(os.path.join(dossier, '*M.track.eep')))
    print(f'{len(grille)} trajectoires MIST, {grille[0][0]} à {grille[-1][0]} masses solaires')
    bc = correcteur(fichier_bc)
    masses = np.exp(np.linspace(np.log(M_MIN), np.log(M_MAX), N_TRACES))
    tableaux = np.full((N_TRACES, 9, N_EEP), np.nan, np.float64)
    phases = np.full((N_TRACES, N_EEP), 255, np.uint8)
    utiles = np.zeros(N_TRACES, np.uint32)
    fins = np.zeros(N_TRACES, np.uint8)
    for i, m in enumerate(masses):
        t, n, fin = interpoler(m, grille)
        b = bc(t[:n, 2], t[:n, 3])
        mbol = MBOL_SOLEIL - 2.5 * t[:n, 1]
        G, C = mbol - b['G'], b['RP'] - b['BP']
        V, BV = mbol - b['V'], b['V'] - b['B']
        G, C = G.astype(np.float32).astype(np.float64), C.astype(np.float32).astype(np.float64)
        lo, hi = fenetres(t[:n, 0], G, C, n)
        for r, v in enumerate((t[:n, 0], G, C, V, BV, t[:n, 1], t[:n, 2], lo[:n], hi[:n])):
            tableaux[i, r, :n] = v
        phases[i, :n] = np.where(t[:n, 4] < 0, 255 - 1, t[:n, 4]).astype(np.int16).astype(np.uint8)      # -1 -> 254 (jeunesse)
        utiles[i], fins[i] = n, fin
        if i % 200 == 0:
            print(f'  {m:8.3f} M☉ : {n} points, fin à {t[n - 1, 0] / 1e9:.3f} Ga, G {G[0]:+.2f} -> {G[n - 1]:+.2f}', flush=True)
    with open(sortie + '.partiel', 'wb') as f:
        f.write(b'UNIVMST1' + np.uint32(N_TRACES).tobytes() + np.uint32(N_EEP).tobytes())
        f.write(masses.astype('<f4').tobytes() + utiles.astype('<u4').tobytes() + fins.tobytes())
        f.write(b'\0' * (-f.tell() % 16))
        for i in range(N_TRACES):
            f.write(tableaux[i, [0, 7, 8]].astype('<f8').tobytes())      # âge et fenêtres en double précision
            f.write(tableaux[i, 1:7].astype('<f4').tobytes())
            f.write(phases[i].tobytes())
    os.replace(sortie + '.partiel', sortie)
    print(f'-> {sortie} ({os.path.getsize(sortie) / 1e6:.0f} Mo)')


if __name__ == '__main__':
    main()
