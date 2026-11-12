#!/usr/bin/env python3
"""Voie lactée de l'appli PC : lumière du disque et poussière sur une grille 3D -> voie_lactee.bin (natif/src/voie_lactee.h).

Ce que l'on ne voit pas une à une (étoiles trop lointaines ou trop faibles pour Gaia) est rendu comme une lueur, d'après
un modèle de la Galaxie ajusté par d'autres sur des mesures. Chaque paramètre a sa source ; ce qui est supposé est dit.

Repère de la grille : axes galactiques (x vers l = 0°, y vers l = 90°, z vers le pôle nord galactique), origine au centre
galactique, placé à R0 du Soleil dans la direction de Sgr A* (DATA.SGRA_GAL de la page). Kiloparsecs.

Lumière (bande V, en luminosités solaires par pc³) :
- luminosité totale : M_V = -20,74 + 5 log10(0,7) = -21,51 (Licquia, Newman et Bershady 2015, ApJ 809, 96, table 3 ; h = 0,7) ;
- partage entre composantes au prorata des masses stellaires de Bland-Hawthorn et Gerhard 2016 (ARA&A 54, 529) :
  disque mince 3,5e10, disque épais 6e9, bulbe en cacahuète 1,55e10 (1,4 à 1,7), barre longue mince 7e9, barre très mince 3e9
  [Supposition : même rapport masse sur lumière pour toutes les composantes] ;
- disque mince : exp(-R / 2,6 kpc) exp(-|z| / 300 pc) ; disque épais : exp(-R / 2,0 kpc) exp(-|z| / 900 pc) (même source) ;
- bras spiraux : tracés mesurés de Reid et al. 2019 (ApJ 885, 131, table 2 : spirales logarithmiques par parallaxes de
  masers), sur l'étendue d'azimut mesurée seulement, largeur de la table. Ce que les bras ajoutent en lumière n'est pas mesuré
  ici : le disque mince y est doublé [Supposition, dite à l'écran] ;
- les étoiles déjà dessinées une à une (Gaia DR3 et catalogue principal) sont retirées case par case : la grille ne garde que
  la lumière qui manque (jamais négative).
Le bulbe et la barre (qui tournent) ne sont pas dans la grille : le shader les calcule avec l'angle du moment
(constantes écrites dans l'en-tête).

Poussière (extinction visuelle A_V par pc) :
- à moins de 1,25 kpc du Soleil : la carte mesurée d'Edenhofer et al. 2024 (DATA.DUST de la page, cases de 15,625 pc),
  rangée aussi telle quelle dans le fichier pour le détail ;
- au-delà : forme du disque de poussière de Drimmel et Spergel 2001 (ApJ 556, 181, éq. 13-14 ; h_r = 2,26 kpc,
  h_d = 134,4 pc + 14,8 pc/kpc au-delà de 4,4 kpc, creux central sous 0,5 R0), dont l'amplitude est fixée par la carte
  mesurée : même extinction moyenne dans le plan jusqu'à 1,25 kpc, sur toutes les longitudes.

Usage : python voie_lactee.py <gaia.bin> <etoiles.bin> <dossier de sortie>
Format voie_lactee.bin (petit-boutiste) : en-tête de 1024 octets (« UNIVMW01 » puis valeurs f32 décrites dans ENTETE),
puis la grande grille NX×NY×NZ de paires f16 (lumière manquante, poussière), x le plus rapide, puis la grille locale de
poussière 160×160×52 en f16 (A_V par pc).
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')      # accents lisibles dans la console Windows
import json, math, os, re, sys, time
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LY_PER_PC = 3.2615638
R0 = 8.2                     # kpc, Bland-Hawthorn et Gerhard 2016, § 3.2.4
NX, NY, NZ = 320, 320, 80    # grande grille : |x|, |y| ≤ 16 kpc par 100 pc ; |z| ≤ 2 kpc par 50 pc
HX, HZ = 16.0, 2.0
M_V_TOTAL = -20.74 + 5 * math.log10(0.7)
M_SUN_V = 4.83               # magnitude absolue V du Soleil [Probable : valeur usuelle, Willmer 2018 donne 4,81]
MASSES = dict(mince=3.5e10, epais=6e9, bulbe=1.55e10, barre=7e9, barre_fine=3e9)
BRAS = [  # Reid et al. 2019, table 2 : nom, beta min, beta max, beta_kink (°), R_kink (kpc), psi<, psi> (°), largeur (kpc)
    ('3-kpc', 15, 18, 15, 3.52, -4.2, -4.2, 0.18), ('Norma', 5, 54, 18, 4.46, -1.0, 19.5, 0.14),
    ('Sct-Cen', 0, 104, 23, 4.91, 14.1, 12.1, 0.23), ('Sgr-Car', 2, 97, 24, 6.04, 17.1, 1.0, 0.27),
    ('Local', -8, 34, 9, 8.26, 11.4, 11.4, 0.31), ('Perseus', -23, 115, 40, 8.87, 10.3, 8.7, 0.35),
    ('Outer', -16, 71, 18, 12.24, 3.0, 9.4, 0.65)]
CONTRASTE_BRAS = 1.0         # [Supposition] lumière ajoutée au disque mince sur l'axe d'un bras (1 = doublée)


def data_keys(keys):
    out = {}
    for f in sorted(os.listdir(os.path.join(ROOT, 'app', 'gen'))):
        if not f.startswith('data'): continue
        s = open(os.path.join(ROOT, 'app', 'gen', f), encoding='utf-8').read()
        for k in keys:
            m = re.search(r'"%s":' % re.escape(k), s)
            if m: out[k] = json.JSONDecoder().raw_decode(s, m.end())[0]
    return out


def axes(n, h):
    return (np.arange(n) - n / 2 + 0.5) * (2 * h / n)


def disque(R, z):
    """Lumière du disque mince et du disque épais (L_sol/pc³), bras compris."""
    L = 10 ** (-0.4 * (M_V_TOTAL - M_SUN_V))
    tot = sum(MASSES.values())
    def norme(hr, hz): return 2 * math.pi * (hr * 1e3) ** 2 * 2 * (hz * 1e3)      # intégrale de exp(-R/hr - |z|/hz), en pc³
    mince = L * MASSES['mince'] / tot / norme(2.6, 0.3) * np.exp(-R / 2.6 - np.abs(z) / 0.3)
    epais = L * MASSES['epais'] / tot / norme(2.0, 0.9) * np.exp(-R / 2.0 - np.abs(z) / 0.9)
    return mince, epais


def bras(x, y):
    """Somme des profils gaussiens des bras mesurés (0 à 1 sur l'axe d'un bras)."""
    R = np.hypot(x, y)
    theta = np.degrees(np.arctan2(y, x))
    beta0 = (180.0 - theta) % 360.0                       # azimut de Reid : 0 vers le Soleil, croissant dans le sens de rotation
    out = np.zeros_like(R)
    for _, bmin, bmax, bk, rk, pin, pout, w in BRAS:
        for tour in (-360.0, 0.0, 360.0):
            beta = beta0 + tour
            ok = (beta >= bmin) & (beta <= bmax)
            if not ok.any(): continue
            psi = np.radians(np.where(beta <= bk, pin, pout))
            Rb = rk * np.exp(-np.radians(beta - bk) * np.tan(psi))
            d = (R - Rb) * np.cos(psi)
            out = np.maximum(out, np.where(ok, np.exp(-0.5 * (d / w) ** 2), 0.0))
    return out


def poussiere_drimmel(R, z):
    """Forme du disque de poussière de Drimmel et Spergel 2001 (sans unité)."""
    hd = np.where(R > 4.4, 0.1344 + 0.0148 * (R - 4.4), 0.1344)
    rho = np.exp(-R / 2.26) / np.cosh(z / hd) ** 2
    r = R / R0
    return np.where(r < 0.5, rho * np.exp(-((r - 0.5) / 0.25) ** 2), rho)


def poussiere_locale(D):
    q = np.frombuffer(__import__('base64').b64decode(D['q']), np.uint8).reshape(D['nz'], D['ny'], D['nx']).astype(np.float64)
    return np.where(q > 0, 10 ** (D['lo'] + (q - 1) / 254 * D['span']), 0.0)      # A_V par pc


def lumiere_cataloguee(gaia_bin, etoiles_bin, ecl2gal, sun, x, y, z):
    """Lumière V des étoiles dessinées une à une, rangée dans la grande grille (L_sol/pc³). Magnitude G de Gaia prise pour V
    [Probable : écart de quelques dixièmes selon la couleur], poussière comprise (magnitudes telles que mesurées)."""
    grille = np.zeros((NZ, NY, NX))
    def ranger(p_ecl_ly, M):
        g = (p_ecl_ly @ ecl2gal.T) / LY_PER_PC / 1e3 + sun
        i = np.floor((g[:, 0] + HX) / (2 * HX) * NX).astype(np.int64)
        j = np.floor((g[:, 1] + HX) / (2 * HX) * NY).astype(np.int64)
        k = np.floor((g[:, 2] + HZ) / (2 * HZ) * NZ).astype(np.int64)
        ok = (i >= 0) & (i < NX) & (j >= 0) & (j < NY) & (k >= 0) & (k < NZ) & np.isfinite(M)
        grille.ravel()[:] += np.bincount((k[ok] * NY + j[ok]) * NX + i[ok], 10 ** (-0.4 * (M[ok] - M_SUN_V)), NX * NY * NZ)
    if gaia_bin == '-':      # essai sans Gaia : seulement le catalogue principal
        n = 0
    else:
        lire_gaia(gaia_bin, ranger)
        n = int(np.fromfile(gaia_bin, np.uint8, 16)[8:16].view('<u8')[0])
    with open(etoiles_bin, 'rb') as f: h = f.read(64)
    ne = int(np.frombuffer(h, '<i8', 1, 8)[0]); n0 = int(np.frombuffer(h, '<i4', 1, 16)[0]); col = (ne * 4 + 63) // 64 * 64
    mm = np.memmap(etoiles_bin, '<f4', 'r', 64, (col // 4 * 4,))
    c = [np.array(mm[k * col // 4:k * col // 4 + n0], np.float64) for k in range(4)]
    ranger(np.stack(c[:3], 1), c[3])
    return grille / (100.0 * 100.0 * 50.0), n


def lire_gaia(gaia_bin, ranger):
    head = np.fromfile(gaia_bin, np.uint8, 4096)
    n = int(head[8:16].view('<u8')[0]); nf = int(head[16:20].view('<u4')[0])
    debut = 4096 + (nf * 48 + 63) // 64 * 64
    rec = np.memmap(gaia_bin, np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('m', '<f2'), ('c', 'u1'), ('f', 'u1')]), 'r', debut, (n,))
    for a in range(0, n, 10_000_000):
        r = np.array(rec[a:a + 10_000_000])
        ranger(np.stack([r['x'], r['y'], r['z']], 1).astype(np.float64), r['m'].astype(np.float64))


def main():
    gaia_bin, etoiles_bin, sortie = sys.argv[1:4]
    t0 = time.time()
    D = data_keys(['M_GAL2ECL', 'SGRA_GAL', 'DUST'])
    gal2ecl = np.array(D['M_GAL2ECL']); ecl2gal = gal2ecl.T
    sgra = np.array(D['SGRA_GAL']) / np.linalg.norm(D['SGRA_GAL'])
    sun = -R0 * sgra                                          # Soleil dans le repère de la grille (kpc)
    x, y, z = axes(NX, HX), axes(NY, HX), axes(NZ, HZ)
    Z, Y, X = np.meshgrid(z, y, x, indexing='ij')
    R = np.hypot(X, Y)

    mince, epais = disque(R, Z)
    b = bras(X, Y)
    moy = np.sum(mince * b) / np.sum(mince)                 # les bras ajoutent de la lumière à masse de disque constante
    lum = mince * (1 + CONTRASTE_BRAS * b) / (1 + CONTRASTE_BRAS * moy) + epais

    # poussière : forme de Drimmel et Spergel, amplitude fixée sur la carte mesurée (plan galactique, 0 à 1,25 kpc)
    loc = poussiere_locale(D['DUST'])
    cl = D['DUST']['cell']
    nxl, nyl, nzl = D['DUST']['nx'], D['DUST']['ny'], D['DUST']['nz']
    s = np.arange(0.5, 1240.0, 5.0)                          # pc
    mes, mod = [], []
    for l in np.radians(np.arange(0, 360, 2)):
        px, py = s * math.cos(l), s * math.sin(l)
        i = np.floor(px / cl + nxl / 2).astype(int); j = np.floor(py / cl + nyl / 2).astype(int); k = int(nzl / 2)
        mes.append(np.sum(0.5 * (loc[k - 1, j, i] + loc[k, j, i])) * 5.0)
        g = sun[None, :] + np.stack([px, py, np.zeros_like(px)], 1) / 1e3
        mod.append(np.sum(poussiere_drimmel(np.hypot(g[:, 0], g[:, 1]), g[:, 2])) * 5.0)
    amp = np.mean(mes) / np.mean(mod)
    pous = amp * poussiere_drimmel(R, Z)
    print(f'poussière : A_V moyen mesuré dans le plan jusqu’à 1,25 kpc = {np.mean(mes):.3f} mag ; amplitude du modèle '
          f'{amp:.3e} mag/pc (au Soleil : {amp * poussiere_drimmel(np.hypot(*sun[:2]), sun[2]) * 1e3:.2f} mag/kpc)')
    # dans le volume de la carte mesurée, la grande grille prend la moyenne mesurée (pas le modèle)
    gx, gy, gz = (X - sun[0]) * 1e3, (Y - sun[1]) * 1e3, (Z - sun[2]) * 1e3
    il = np.floor(gx / cl + nxl / 2).astype(int); jl = np.floor(gy / cl + nyl / 2).astype(int); kl = np.floor(gz / cl + nzl / 2).astype(int)
    dans = (il >= 0) & (il < nxl) & (jl >= 0) & (jl < nyl) & (kl >= 0) & (kl < nzl) & (np.sqrt(gx ** 2 + gy ** 2 + gz ** 2) < D['DUST']['rmax'])
    pous[dans] = loc[kl[dans], jl[dans], il[dans]]
    print(f'grilles prêtes ({time.time() - t0:.0f} s)')

    cat, ngaia = lumiere_cataloguee(gaia_bin, etoiles_bin, ecl2gal, sun, x, y, z)
    manque = np.maximum(lum - cat, 0.0)
    ks, js, is_ = (int(np.floor((sun[a] + h) / (2 * h) * nn)) for a, h, nn in ((2, HZ, NZ), (1, HX, NY), (0, HX, NX)))
    print(f'case du Soleil : modèle {lum[ks, js, is_]:.4f} L_sol/pc³, étoiles cataloguées {cat[ks, js, is_]:.4f} ; '
          f'lumière du modèle {lum.sum() * 5e5:.3e} L_sol, cataloguée dans la grille {cat.sum() * 5e5:.3e}, manquante {manque.sum() * 5e5:.3e}')

    L = 10 ** (-0.4 * (M_V_TOTAL - M_SUN_V)); tot = sum(MASSES.values())
    head = np.array([NX, NY, NZ, HX, HZ, R0, *sun, *gal2ecl.ravel(), L * MASSES['bulbe'] / tot, 0.70, 0.44, 0.18,
                     L * (MASSES['barre'] + MASSES['barre_fine']) / tot, 5.0, 0.18, 0.045, MASSES['barre_fine'] / (MASSES['barre'] + MASSES['barre_fine']),
                     math.radians(152.0), 39.0, CONTRASTE_BRAS, nxl, nyl, nzl, cl], '<f4')
    os.makedirs(sortie, exist_ok=True)
    chemin = os.path.join(sortie, 'voie_lactee.bin')
    with open(chemin, 'wb') as f:
        h = b'UNIVMW01' + head.tobytes()
        f.write(h + b'\0' * (1024 - len(h)))
        f.write(np.stack([manque, pous], -1).astype('<f2').tobytes())
        f.write(loc.astype('<f2').tobytes())
    print(f'-> {chemin} ({os.path.getsize(chemin) / 1e6:.1f} Mo, {time.time() - t0:.0f} s)')


ENTETE = ('nx ny nz, demi-côté xy (kpc), demi-hauteur z (kpc), R0 (kpc), Soleil x y z (kpc), matrice galactique -> écliptique '
          '(9, lignes), bulbe : luminosité (L_sol), h_x h_y h_z (kpc) ; barre longue : luminosité, demi-longueur, hauteur '
          'mince, hauteur très mince, part très mince ; angle de la barre à J2000 (rad, depuis +x vers +y), vitesse (km/s/kpc), '
          'contraste des bras ; grille locale nx ny nz, côté d’une case (pc)')

if __name__ == '__main__':
    main()
