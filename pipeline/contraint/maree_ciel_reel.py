"""Marée extérieure « ciel réel » sur le Groupe local, depuis les groupes de galaxies OBSERVÉS (demande du grand calcul,
20/11/2026 : le halo fantôme de 5e12 M☉ du calcul contraint faussait ~40 % de la marée).

Source unique des masses et des positions : Kourkchi & Tully 2017, ApJ 843, 16, « Galaxy groups within 3500 km/s »
(VizieR J/ApJ/843/16, table2 : 8 827 groupes, galaxies isolées comprises) [Certain : catalogue publié].
  - masse : logMK (masse du groupe déduite de sa luminosité K, relation de l'article) ; variante logMd (masse dynamique)
    quand elle existe, pour l'écart systématique ;
  - distance : Dist (distances mesurées des membres) quand Nd > 0, sinon VLS / 75 (vitesse par rapport au Feuillet local,
    H0 = 75 de l'article) [Probable : la distance de vitesse inclut les vitesses particulières] ;
  - incertitude : 300 tirages des distances (e_Dist, ou 20 % pour les distances de vitesse) et des masses (0,2 dex).
Centre : centre de masse Voie lactée + Andromède (1,34 et 1,07e12 M☉, table unique du projet ; 785 kpc vers l = 121,17°,
b = −21,57°) ; on garde les groupes entre 1,5 et 50 Mpc de ce centre.
T_ij = −∂²Φ/∂x_i∂x_j = G Σ m (3 r_i r_j − r² δ_ij) / r⁵ ; a_i = +T_ij x_j ; (km/s/kpc)² ; repère galactique de l'appli
(x vers le centre galactique, y vers l = 90°, z vers le nord). Énergie noire NON incluse.
Évolution dans le temps (modèle, signalé) : positions comobiles et masses fixes, donc T(t) = T(0) · a(t)⁻³ (ΛCDM Planck 2018).

Usage : python maree_ciel_reel.py DOSSIER_SORTIE
"""
import os
import sys

import numpy as np

G = 4.30091e-6
RAW = os.path.join(os.environ['LOCALAPPDATA'], 'univers-raw', 'kt17')
OM, H0 = 0.3111, 67.66
M_VL, M_M31, D_M31 = 1.34e12, 1.07e12, 0.785


def unitaire(l_deg, b_deg):
    l, b = np.radians(l_deg), np.radians(b_deg)
    return np.stack([np.cos(b) * np.cos(l), np.cos(b) * np.sin(l), np.sin(b)], axis=-1)


def lire_tsv(nom):
    lignes = [l.rstrip('\n') for l in open(os.path.join(RAW, nom), encoding='utf-8') if not l.startswith('#') and l.strip()]
    entete = lignes[0].split('\t')
    rangs = [dict(zip(entete, [c.strip() for c in l.split('\t')])) for l in lignes[3:]]
    return rangs


def tenseur(pos_kpc, m):
    r = np.linalg.norm(pos_kpc, axis=1)
    return G * np.einsum('n,ni,nj->ij', m / r ** 5, 3.0 * pos_kpc, pos_kpc) - G * np.eye(3) * np.sum(m / r ** 3)


def facteur_echelle(t_ga):
    """a(t) pour ΛCDM plat, t en Ga depuis aujourd'hui (inverse de l'âge analytique)."""
    ol = 1.0 - OM
    tH = 977.8 / H0
    age0 = 2.0 / (3.0 * np.sqrt(ol)) * np.arcsinh(np.sqrt(ol / OM)) * tH
    x = (age0 + t_ga) / tH * 1.5 * np.sqrt(ol)
    return (np.sqrt(OM / ol) * np.sinh(x)) ** (2.0 / 3.0)


def main():
    sortie = sys.argv[1]
    os.makedirs(sortie, exist_ok=True)
    rangs = lire_tsv('groupes.tsv')
    noms = {}
    for g in lire_tsv('galaxies.tsv'):
        if g.get('PGC') == g.get('PGC1') and g.get('Name'):
            noms[g['PGC1']] = g['Name']
    l = np.array([float(g['GLON']) for g in rangs]); b = np.array([float(g['GLAT']) for g in rangs])
    vls = np.array([float(g['VLS']) for g in rangs])
    nd = np.array([int(g['Nd'] or 0) for g in rangs])
    dist = np.array([float(g['Dist']) if g['Dist'] else np.nan for g in rangs])
    edist = np.array([float(g['e_Dist']) / 100 if g['e_Dist'] else 0.2 for g in rangs])
    mk = np.array([10 ** float(g['logMK']) if g['logMK'] else np.nan for g in rangs])
    md = np.array([10 ** float(g['logMd']) if g['logMd'] else np.nan for g in rangs])
    d = np.where((nd > 0) & np.isfinite(dist), dist, vls / 75.0)
    edist = np.where((nd > 0) & np.isfinite(dist), edist, 0.2)
    u = unitaire(l, b)
    cm = D_M31 * M_M31 / (M_VL + M_M31) * unitaire(121.17, -21.57)          # Mpc
    pos = u * d[:, None] - cm
    r = np.linalg.norm(pos, axis=1)
    garde = (r > 1.5) & (r < 50.0) & np.isfinite(mk) & (d > 0)
    p_kpc, m = pos[garde] * 1000.0, mk[garde]
    t0 = tenseur(p_kpc, m)
    # part de chaque groupe (norme de Frobenius de sa contribution), les 15 plus grandes
    contrib = G * m[:, None, None] / np.linalg.norm(p_kpc, axis=1)[:, None, None] ** 5 * (
        3.0 * np.einsum('ni,nj->nij', p_kpc, p_kpc) - np.linalg.norm(p_kpc, axis=1)[:, None, None] ** 2 * np.eye(3))
    norme = np.linalg.norm(contrib.reshape(len(m), 9), axis=1)
    ordre = np.argsort(-norme)[:15]
    pgc = np.array([g['PGC1'] for g in rangs])[garde]
    lignes_p = ['pgc1,nom,distance_centre_mpc,masse_msun,Txx,Tyy,Tzz,part_norme']
    for k in ordre:
        c = contrib[k]
        lignes_p.append(f'{pgc[k]},{noms.get(pgc[k], "")},{np.linalg.norm(p_kpc[k]) / 1000:.2f},{m[k]:.3e},'
                        f'{c[0, 0]:.3e},{c[1, 1]:.3e},{c[2, 2]:.3e},{norme[k] / np.linalg.norm(t0):.3f}')
    # incertitude : tirages des distances et des masses
    rng = np.random.default_rng(2026)
    tirages = []
    for _ in range(300):
        dd = d * np.exp(rng.standard_normal(len(d)) * edist)
        mm = mk * 10 ** (rng.standard_normal(len(d)) * 0.2)
        pp = u * dd[:, None] - cm
        rr = np.linalg.norm(pp, axis=1)
        gg = (rr > 1.5) & (rr < 50.0) & np.isfinite(mm) & (dd > 0)
        tirages.append(tenseur(pp[gg] * 1000.0, mm[gg]))
    et = np.std(tirages, axis=0, ddof=1)
    # variante masse dynamique
    mvar = np.where(np.isfinite(md), md, mk)[garde]
    tdyn = tenseur(p_kpc, mvar)
    # table dans le temps
    lignes_t = ['t_ga,Txx,Txy,Txz,Tyx,Tyy,Tyz,Tzx,Tzy,Tzz,sigma_Txx,sigma_Tyy,sigma_Tzz  # (km/s/kpc)^2, repère galactique de l appli']
    for t in np.round(np.arange(-2.0, 10.0001, 0.1), 2):
        f = facteur_echelle(t) ** -3.0
        tt = t0 * f
        lignes_t.append(f'{t},' + ','.join(f'{v:.4e}' for v in tt.ravel()) + ','
                        + ','.join(f'{et[i, i] * f:.2e}' for i in range(3)))
    open(os.path.join(sortie, 'maree_ciel_reel.csv'), 'w', encoding='utf-8').write('\n'.join(lignes_t) + '\n')
    open(os.path.join(sortie, 'maree_ciel_reel_parts.csv'), 'w', encoding='utf-8').write('\n'.join(lignes_p) + '\n')
    print('groupes gardés :', int(garde.sum()), '; trace', f'{np.trace(t0):.1e}')
    print('T aujourd hui (logMK) diag :', np.diag(t0).round(6), '± (tirages)', np.diag(et).round(6))
    print('variante masses dynamiques diag :', np.diag(tdyn).round(6))
    print('\n'.join(lignes_p[:9]))


if __name__ == '__main__':
    main()
