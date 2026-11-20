"""Tables d'environnement de la paire Voie lactée / Andromède pour le grand calcul (raccord, demande du 20/11/2026).

Lit les instantanés et catalogues SUBFIND d'un calcul contraint (zoom fin v17, sorties tous les 0,1 Ga de −2,4 à +10 Ga)
et écrit, dans le repère galactique de l'appli (phys::galaxie : x vers le centre galactique vu du Soleil, y vers l = 90°,
z vers le nord galactique ; les axes du calcul sont supergalactiques, tournés par ROT_SG_GAL calculée avec astropy) :

  masse_t.csv        t_ga, galaxie, M200 [M☉], r200 [kpc physiques], concentration NFW c = 2,163 r200 / r_max (r_max = rayon du pic de la vitesse circulaire) ; repli Vmax/V200
  orbite_paire.csv   t_ga, séparation [kpc], v_radiale, v_tangentielle [km/s] (flot de Hubble compris)
  maree.csv          t_ga, T_xx … T_zz [(km/s/kpc)²] : tenseur de marée EXTÉRIEUR au centre de masse de la paire,
                     T_ij = G Σ m (3 r_i r_j − r² δ_ij) / r⁵ sur toutes les particules entre R_INT et R_EXT
                     (une couche uniforme ne crée aucune marée à l'intérieur : seul l'écart à la moyenne compte).
                     Le terme de l'énergie noire (+Ω_Λ H0² δ_ij) n'est PAS inclus : le grand calcul l'a déjà.
  spin.csv           t_ga, galaxie, λ' (Bullock 2001) et direction du moment cinétique (vecteur unité)

Modèles et limites [À vérifier] : convention des unités de SubhaloSpin (supposée longueur comobile × vitesse
particulière, convertie en physique par a) ; suivi des halos par proximité ; la marée des particules grossières
(1e13 M☉) a un bruit de grain, d'où R_INT = 1,5 Mpc.
Usage (WSL, python3 + numpy + h5py) : python3 environnement_paire.py DOSSIER_SORTIE DOSSIER_TABLES
"""
import glob
import os
import sys

import h5py
import numpy as np

H = 0.6766
OM = 0.3111
G = 4.30091e-6                       # kpc (km/s)² / M☉
R_INT_KPC = 1500.0
R_EXT_KPC = 50000.0
ROT_SG_GAL = np.array([[-7.35742575e-01, -7.45537784e-02, 6.73145302e-01],
                       [6.77261296e-01, -8.09914713e-02, 7.31271166e-01],
                       [-6.08602059e-17, 9.93922590e-01, 1.10081262e-01]])
M31_DIR_SG = np.array([0.893, -0.394, 0.2174])     # direction d'Andromède vue de chez nous (repère supergalactique)


def age_ga(a):
    ol = 1.0 - OM
    return 2.0 / (3.0 * np.sqrt(ol)) * np.arcsinh(np.sqrt(ol / OM) * a ** 1.5) * 977.8 / (100.0 * H)


def hubble(a):
    return 100.0 * H * np.sqrt(OM / a ** 3 + 1.0 - OM)          # km/s/Mpc


def concentration(vmax, v200):
    """Résout Vmax/V200 = sqrt(0,216 c / f(c)), f(c) = ln(1+c) − c/(1+c) (NFW)."""
    cible = (vmax / v200) ** 2
    cs = np.logspace(0, 2, 4000)
    f = np.log(1 + cs) - cs / (1 + cs)
    return float(np.interp(cible, 0.216 * cs / f, cs))


def charger_particules(snap):
    f = h5py.File(snap, 'r')
    tab = f['Header'].attrs['MassTable']
    pos, mas = [], []
    for t in range(1, 6):
        g = f.get(f'PartType{t}')
        if g is None:
            continue
        pos.append(g['Coordinates'][:].astype(np.float64))
        mas.append(g['Masses'][:] if 'Masses' in g else np.full(len(g['Coordinates']), tab[t]))
    return np.concatenate(pos), np.concatenate(mas) * 1e10 / H


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    os.makedirs(sortie, exist_ok=True)
    t0 = age_ga(1.0)
    cats = sorted(glob.glob(f'{dossier}/fof_subhalo_tab_*.hdf5'))
    lignes_m, lignes_o, lignes_t, lignes_s = [], [], [], []
    centre_prec = None
    for cat in cats:
        g = h5py.File(cat, 'r')
        a = float(g['Header'].attrs['Time'])
        t = round(age_ga(a) - t0, 2)
        if t < -2.45 or g['Header'].attrs['Ngroups_Total'] == 0:
            continue
        m200 = g['Group/Group_M_Crit200'][:] * 1e10 / H
        r200 = g['Group/Group_R_Crit200'][:] * a / H * 1000.0          # kpc physiques
        gpos = g['Group/GroupPos'][:].astype(np.float64)
        gvel = g['Group/GroupVel'][:].astype(np.float64)
        premier = g['Group/GroupFirstSub'][:]
        ref = centre_prec if centre_prec is not None else np.median(gpos[m200 > 1e12], axis=0)
        d = np.linalg.norm(gpos - ref, axis=1)
        cand = np.where((d < 2.0) & (m200 > 5e11) & (m200 < 1e13))[0]
        if len(cand) < 2:
            continue
        i, j = cand[np.argsort(-m200[cand])[:2]]
        # Andromède = celui placé du côté de sa direction réelle
        if np.dot(gpos[j] - gpos[i], M31_DIR_SG) < 0:
            i, j = j, i
        noms = {'voie_lactee': i, 'andromede': j}
        dx = (gpos[j] - gpos[i]) * a / H * 1000.0
        r = np.linalg.norm(dx)
        dv = gvel[j] - gvel[i] + hubble(a) * dx / 1000.0
        vr = dv @ dx / r
        lignes_o.append(f'{t},{r:.1f},{vr:.2f},{np.linalg.norm(dv - vr * dx / r):.2f}')
        cm = (m200[i] * gpos[i] + m200[j] * gpos[j]) / (m200[i] + m200[j])
        centre_prec = cm
        for nom, k in noms.items():
            v200 = np.sqrt(G * m200[k] / r200[k])
            s = premier[k]
            rmax = float(g['Subhalo/SubhaloVmaxRad'][s]) * a / H * 1000.0             # kpc physiques
            c = 2.163 * r200[k] / rmax if rmax > 0 else concentration(float(g['Subhalo/SubhaloVmax'][s]), v200)
            j_spec = g['Subhalo/SubhaloSpin'][s].astype(np.float64) * a / H * 1000.0     # kpc km/s [À vérifier]
            lam = np.linalg.norm(j_spec) / (np.sqrt(2.0) * v200 * r200[k])
            u = ROT_SG_GAL @ (j_spec / np.linalg.norm(j_spec))
            lignes_m.append(f'{t},{nom},{m200[k]:.4e},{r200[k]:.1f},{c:.2f}')
            lignes_s.append(f'{t},{nom},{lam:.4f},{u[0]:.4f},{u[1]:.4f},{u[2]:.4f}')
        snap = cat.replace('fof_subhalo_tab', 'snap')
        if os.path.exists(snap):
            pos, mas = charger_particules(snap)
            rel = (pos - cm) * a / H * 1000.0
            rr = np.linalg.norm(rel, axis=1)
            sel = (rr > R_INT_KPC) & (rr < R_EXT_KPC)
            x, m, q = rel[sel], mas[sel], rr[sel]
            tt = G * np.einsum('n,ni,nj->ij', m / q ** 5, 3.0 * x, x) - G * np.eye(3) * np.sum(m / q ** 3)
            tg = ROT_SG_GAL @ tt @ ROT_SG_GAL.T
            lignes_t.append(f'{t},' + ','.join(f'{v:.4e}' for v in tg.ravel()))
        print(t, f'{m200[i]:.2e} {m200[j]:.2e} sép {r:.0f} kpc vr {vr:.0f}', flush=True)
    ent = {'masse_t.csv': 't_ga,galaxie,m200_msun,r200_kpc,concentration',
           'orbite_paire.csv': 't_ga,separation_kpc,v_radiale_kms,v_tangentielle_kms',
           'maree.csv': 't_ga,Txx,Txy,Txz,Tyx,Tyy,Tyz,Tzx,Tzy,Tzz  # (km/s/kpc)^2, repère galactique de l appli',
           'spin.csv': 't_ga,galaxie,lambda_bullock,jx,jy,jz  # direction unité, repère galactique de l appli'}
    for nom, lignes in (('masse_t.csv', lignes_m), ('orbite_paire.csv', lignes_o), ('maree.csv', lignes_t),
                        ('spin.csv', lignes_s)):
        open(os.path.join(sortie, nom), 'w').write(ent[nom] + '\n' + '\n'.join(lignes) + '\n')
    print('écrit dans', sortie)


if __name__ == '__main__':
    main()
