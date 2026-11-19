"""Contrôle croisé : vitesses reconstruites depuis Cosmicflows-4 (distances) contre 2MRS (redshifts, CORAS).

Les deux relevés sont indépendants : l'un mesure des distances, l'autre la répartition des galaxies.
Si les deux reconstructions concordent, le champ grande échelle qui servira au départ contraint est solide.
CORAS : grille 201³, coordonnées galactiques cartésiennes, -200 à +200 Mpc/h par pas de 2, repère du fond diffus,
lissage gaussien 5 Mpc/h (README de CORAS) [Certain].
Usage : python comparer_2mrs.py   (après cf4_wiener.py, qui écrit resultats/cf4_wiener_v1.npz)
"""
import os

import numpy as np
from astropy.coordinates import SkyCoord
from scipy.ndimage import map_coordinates

CORAS = r'\\wsl.localhost\Ubuntu-24.04\home\marcr\contraint\CORAS\data'


def lire_coras(nom: str, ncol: int) -> np.ndarray:
    cache = os.path.join('resultats', nom + '.npy')
    if os.path.exists(cache):
        return np.load(cache)
    a = np.loadtxt(os.path.join(CORAS, nom + '.dat'), skiprows=1, dtype=np.float32)
    a = a.reshape(201, 201, 201, ncol) if ncol > 1 else a.reshape(201, 201, 201)
    np.save(cache, a)
    return a


def sg_vers_gal(x: np.ndarray) -> np.ndarray:
    c = SkyCoord(sgx=x[:, 0], sgy=x[:, 1], sgz=x[:, 2], frame='supergalactic',
                 representation_type='cartesian').galactic
    c.representation_type = 'cartesian'
    return np.stack([c.u.value, c.v.value, c.w.value], axis=1)


def main() -> None:
    r = np.load('resultats/cf4_wiener_v1.npz')
    pts_gal = sg_vers_gal(r['points'])
    v_gal = sg_vers_gal(r['v'])
    v2 = lire_coras('cartesian_grid_velocity_zCMB', 3)
    idx = (pts_gal + 200.0) / 2.0                                     # indices de grille CORAS
    v2_pts = np.stack([map_coordinates(v2[..., a], idx.T, order=1) for a in range(3)], axis=1)
    rayon = np.linalg.norm(pts_gal, axis=1)
    for rmax in (50.0, 100.0):
        m = rayon < rmax
        cc = [np.corrcoef(v_gal[m, a], v2_pts[m, a])[0, 1] for a in range(3)]
        print(f'r < {rmax:.0f} Mpc/h ({m.sum()} cases) : corrélation CF4 / 2MRS  X {cc[0]:+.2f}  Y {cc[1]:+.2f}  Z {cc[2]:+.2f}'
              f' ; amplitude CF4 {np.std(v_gal[m]):.0f} km/s, 2MRS {np.std(v2_pts[m]):.0f} km/s')
    v0 = np.stack([map_coordinates(v2[..., a], [[100.0], [100.0], [100.0]], order=1) for a in range(3)])[:, 0]
    c = SkyCoord(u=v0[0], v=v0[1], w=v0[2], frame='galactic', representation_type='cartesian')
    c.representation_type = 'spherical'
    print(f'2MRS à l\'origine : {np.linalg.norm(v0):.0f} km/s vers l = {c.l.deg:.0f}°, b = {c.b.deg:+.0f}°')


if __name__ == '__main__':
    main()
