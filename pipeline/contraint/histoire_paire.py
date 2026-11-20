"""Histoire de la paire Voie lactée / Andromède dans un calcul contraint : masse, distance, vitesse au fil du temps.

Tourne sous WSL (python3 système : numpy + h5py). On part des deux halos de la paire à z = 0 et on remonte les
instantanés : à chaque pas, on garde le groupe le plus proche de la position prédite (position − vitesse·Δt) dont
la masse ne dépasse pas 1,5 fois la masse suivante (un halo ne perd presque pas de masse en remontant… il en a moins).
Sortie : JSON (temps en Ga avant aujourd'hui, masses M200 en M☉, séparation physique en kpc, vitesses en km/s),
plus les satellites (> 1e9 M☉) à moins de 300 kpc de chaque galaxie aujourd'hui.

Usage : python3 histoire_paire.py DOSSIER_SORTIE ID_HALO_1 ID_HALO_2 SORTIE.json [h=0.6766]
"""
import glob
import json
import sys

import h5py
import numpy as np

H = float(sys.argv[5]) if len(sys.argv) > 5 else 0.6766
OM = 0.3111


def age_ga(a: float) -> float:
    """Âge de l'Univers ΛCDM plat (constante cosmologique comprise) au facteur d'échelle a, en Ga."""
    ol = 1.0 - OM
    return 2.0 / (3.0 * np.sqrt(ol)) * np.arcsinh(np.sqrt(ol / OM) * a ** 1.5) * 977.8 / (100.0 * H)


def lire(fichier: str):
    g = h5py.File(fichier, 'r')
    a = float(g['Header'].attrs['Time'])
    if 'Group' not in g or g['Header'].attrs['Ngroups_Total'] == 0:
        return a, None, None, None
    return a, g['Group/Group_M_Crit200'][:] * 1e10 / H, g['Group/GroupPos'][:], g['Group/GroupVel'][:]


def main() -> None:
    dossier, i1, i2, sortie = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    fichiers = sorted(glob.glob(f'{dossier}/fof_subhalo_tab_*.hdf5'))
    a0, m, p, v = lire(fichiers[-1])
    t0 = age_ga(a0)
    suivis = {'voie_lactee_ou_andromede_1': i1, 'voie_lactee_ou_andromede_2': i2}
    pos = {k: p[i] for k, i in suivis.items()}
    vit = {k: v[i] for k, i in suivis.items()}
    mas = {k: m[i] for k, i in suivis.items()}
    histoire = []
    for f in reversed(fichiers):
        a, m, p, v = lire(f)
        if m is None:
            break
        ligne = dict(a=a, t_ga=round(age_ga(a) - t0, 4))
        dt_s = (age_ga(a0) - age_ga(a)) * 3.156e16          # secondes (Ga → s)
        for k in suivis:
            # position prédite en remontant le temps : x_comobile − v_pec·Δt / a, en Mpc/h
            pred = pos[k] - vit[k] * dt_s / a / 3.0857e19 * H
            d = np.linalg.norm(p - pred, axis=1)
            ok = (m < 1.3 * mas[k]) & (m > 0.05 * mas[k]) & (d < 1.5)
            if not ok.any():
                continue
            score = np.where(ok, d / 0.5 + np.abs(np.log(np.maximum(m, 1.0) / mas[k])), np.inf)
            j = np.argmin(score)
            pos[k], vit[k], mas[k] = p[j], v[j], m[j]
            ligne[k] = dict(m200=float(m[j]), groupe=int(j))
        if all(k in ligne for k in suivis):
            dx = (pos['voie_lactee_ou_andromede_2'] - pos['voie_lactee_ou_andromede_1']) * a
            r = np.linalg.norm(dx)
            dv = (vit['voie_lactee_ou_andromede_2'] - vit['voie_lactee_ou_andromede_1'])
            hubble = 100.0 * np.sqrt(OM / a ** 3 + 1.0 - OM)
            dv = dv + hubble * dx
            vr = float(dv @ dx / r)
            ligne['separation_kpc'] = float(r / H * 1000.0)
            ligne['v_radiale_kms'] = vr
            ligne['v_transverse_kms'] = float(np.linalg.norm(dv - vr * dx / r))
        histoire.append(ligne)
        a0 = a
    # satellites aujourd'hui
    a, m, p, v = lire(fichiers[-1])
    sat = {}
    for k, i in suivis.items():
        d = np.linalg.norm(p - p[i], axis=1) * a / H * 1000.0
        sel = np.where((d < 300.0) & (d > 0) & (m > 1e9))[0]
        sat[k] = [dict(m200=float(m[s]), distance_kpc=float(d[s])) for s in sel]
    json.dump(dict(histoire=histoire[::-1], satellites=sat,
                   statut='modèle : un passé possible (calcul contraint), pas une mesure'),
              open(sortie, 'w'), indent=1, ensure_ascii=False)
    print(f'{len(histoire)} instantanés écrits dans {sortie}')
    for l in histoire[::-1][::3]:
        print(l.get('t_ga'), {k: f"{l[k]['m200']:.2e}" for k in suivis if k in l}, round(l.get('separation_kpc', -1)))


if __name__ == '__main__':
    main()
