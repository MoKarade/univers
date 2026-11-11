#!/usr/bin/env python3
"""Essai réduit de la fusion (fin de R8, docs/fusion-methode.md § 6).

Voie lactée et Andromède, environ 15 000 particules chacune, sur 1 milliard d'années, avec le même code que le calcul
complet (AGAMA pour l'équilibre, falcON pour la gravité, saute-mouton à pas fixe, 1 Ma par défaut, réglable). Affiche la dérive
d'énergie totale (fini quand < 1 %) et le temps par pas, d'où une estimation du temps du calcul complet.
"""
import time, json, sys
import numpy as np
import pyfalcon
import modeles as M

G = M.G
N_COMPLET = 300000                         # particules du calcul complet (docs/fusion-methode.md § 5)
T_UNIT_GYR = 0.9778                       # kpc/(km/s) en milliards d'années
DT_MA = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0   # pas en millions d'années
DT = DT_MA * 0.001 / T_UNIT_GYR
M31_POS = [-385.352, 623.003, -287.592]   # data3.js, DATA.M31.pos
M31_VEL = [28.4, -109.8, 41.4]            # 60_app.js, M31_MEAS « Gaia, 2025 »
M31_SPIN = [-0.44498, -0.76618, -0.46362] # data3.js, DATA.M31.spin
MW_SPIN = [0.0, 0.0, -1.0]                # la Voie lactée tourne dans le sens rétrograde autour du pôle nord galactique


def forces(p):
    acc, phi = pyfalcon.gravity(p['pos'].astype(np.float32), (p['m'] * G).astype(np.float32), p['eps'].astype(np.float32), theta=0.6)
    return acc.astype(np.float64), phi.astype(np.float64)


def energie(p, phi):
    return 0.5 * float(np.sum(p['m'] * np.sum(p['vel'] ** 2, axis=1))) + 0.5 * float(np.sum(p['m'] * phi))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    t_gyr = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    mw = M.galaxie('Voie lactée', int(n * 0.6), int(n * 0.33), int(n * 0.07))
    m31 = M.galaxie('Andromède', int(n * 0.6), int(n * 0.33), int(n * 0.07), k_mass=1.5, k_r=1.15)
    p = M.assembler(M.placer(mw, MW_SPIN, [0, 0, 0], [0, 0, 0]), M.placer(m31, M31_SPIN, M31_POS, M31_VEL))
    cm = np.sum(p['pos'] * p['m'][:, None], axis=0) / p['m'].sum(); vm = np.sum(p['vel'] * p['m'][:, None], axis=0) / p['m'].sum()
    p['pos'] -= cm; p['vel'] -= vm
    acc, phi = forces(p); e0 = energie(p, phi)
    steps = int(round(t_gyr / (DT_MA * 0.001))); t0 = time.time(); worst = 0.0
    for s in range(steps):
        p['vel'] += 0.5 * DT * acc
        p['pos'] += DT * p['vel']
        acc, phi = forces(p)
        p['vel'] += 0.5 * DT * acc
        if (s + 1) % int(round(100 / DT_MA)) == 0:
            e = energie(p, phi); worst = max(worst, abs(e / e0 - 1))
            print(f'  t = {(s + 1) * DT_MA * 0.001:.2f} Ga : dérive d’énergie {100 * (e / e0 - 1):+.3f} %', flush=True)
    dt_step = (time.time() - t0) / steps
    N = len(p['m'])
    full = dt_step * (N_COMPLET / N) * (10.0 / (DT_MA * 0.001)) / 3600
    res = dict(particules=N, duree_ga=t_gyr, pas_ma=DT_MA, derive_max_pourcent=100 * worst, secondes_par_pas=dt_step, estimation_calcul_complet_heures=full)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print('essai :', 'PASSE' if worst < 0.01 else 'ÉCHEC', f'(dérive maximale {100 * worst:.3f} %, limite 1 %)')
    sys.exit(0 if worst < 0.01 else 1)


if __name__ == '__main__':
    main()
