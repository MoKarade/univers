#!/usr/bin/env python3
"""Étoiles visibles d'aujourd'hui (contrat docs/contrat-etoiles-visibles.md, branche modeles-depart) : Voie lactée.

Une seule population d'étoiles, de t = 0 à la fusion : ces traceurs sont ce que l'appli dessine, et ce que le calcul de
la rencontre fait évoluer (sans masse, kind 9). Ce script écrit :
- etoiles_visibles_voie_lactee.npz : pos (kpc), vel (km/s), lum (L☉), teff (K), comp, graine, meta (contrat § 2) ;
- vl_etoiles.bin : les mêmes traceurs au format gaia.bin (natif/src/gaia.h : arbre en huit, niveaux de détail,
  orbites sur la carte graphique en attendant le film), lu par l'appli PC.

Repère phys::galaxie (natif/physique/galaxie_orbites.h) : centre à l'origine, Soleil à -R0 vers Sgr A* (≈ (-8,2 ; 0 ; 0)),
y vers la longitude 90°, z vers le nord galactique ; rotation dans le sens des φ décroissants (le Soleil va vers +y).

Composantes (masses : docs/parametres-galaxies.md de modeles-depart ; lumière = masse / rapport masse-lumière de la
population, ML_V [Supposition] ; lumière V totale : M_V = -21,51, Licquia et al. 2015) :
- 1 disque mince : Σ0 = 896 M☉/pc², Rd = 2,50 kpc, hz = 0,30 kpc (exponentiel en z) ; lisse (la masse est lisse) ;
- 4 disque épais : Σ0 = 183 M☉/pc², Rd = 3,02 kpc, hz = 0,90 kpc ;
- 2 bulbe et barre (lumière) : bulbe en cacahuète exponentiel triaxial 0,70 × 0,44 × 0,18 kpc et barre longue de 5 kpc
  de demi-longueur, hauteurs 180 et 45 pc (Wegg & Gerhard 2013, Wegg et al. 2015 ; Bland-Hawthorn & Gerhard 2016),
  angle de 28° avec la ligne Soleil-centre (galaxie_orbites.h) ;
- 5 étoiles jeunes : le long des bras MESURÉS de Reid et al. 2019 (masers) et de leurs prolongements EXTRAPOLÉS
  (atténués), et dans les 1 413 régions HII WISE avec distance (Anderson et al. 2014) [modèle : part de lumière] ;
- 6 halo d'étoiles : 1e9 M☉, densité r^-3,5 aplatie 0,6, de 1 à 50 kpc (Deason et al. 2011) [modèle].
Vitesses : vitesse circulaire de McMillan 2017 (198, 222, 234, 227, 221 km/s à 2, 4, 8,21, 15, 25 kpc) et agitation
(disque mince 35 km/s au Soleil, épais 50 km/s, croissance exponentielle vers le centre sur 5 kpc, bornée à 60 et 90 km/s ; bulbe 100 km/s ; halo 120 km/s ;
jeunes 10 km/s) ; barre : rotation d'ensemble à 39 km/s/kpc dans la limite de la vitesse circulaire.
Lumière de chaque traceur : tirée d'une loi de Pareto (indice 1,5), somme égale à la lumière de sa composante
[modèle : les traceurs portent la lumière de toutes les étoiles faibles qui les entourent].
Près du Soleil, Gaia dessine déjà les étoiles mesurées : la lumière de chaque traceur est réduite de ce que Gaia
montre dans sa case (100 pc), d'après la lumière cataloguée de voie_lactee.py ; rien n'est compté deux fois.
Tirage déterministe (graine fixe).
Usage : python etoiles_visibles.py <gaia.bin[,gaia_b.bin]> <etoiles.bin> <gaia_agrege.bin> <wise_hii.tsv> <dossier de sortie>
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')
import json, math, os, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voie_lactee as v
import voie_lactee_jeunes as vj
from gaia_convertir import morton, feuilles, TRANCHES, TRANCHE0, TRANCHE_L, BPRP0, BPRP_PAS, V_PAS

N_TOTAL = 4_000_000
PARTS = {1: 0.40, 4: 0.10, 2: 0.18, 5: 0.29, 6: 0.03}      # part des traceurs par composante (choix de résolution)
M_SOL_V = 4.83
L_V = 10 ** (-0.4 * (-21.51 - M_SOL_V))
MASSE = {1: 2 * math.pi * 896 * 2500.0 ** 2, 4: 2 * math.pi * 183 * 3020.0 ** 2, 2: 1.55e10 + 1.0e10, 6: 1.0e9}
ML_V = {1: 1.2, 4: 2.5, 2: 3.0, 6: 3.0}      # M☉/L☉ en V par population (vieilles plus sombres) [Supposition, ordres publiés]
PART_JEUNES = 0.30            # part de la lumière du disque mince portée par les jeunes et les bras [Supposition : 20 à 40 % en bleu, moins en V]
VC = ([0.0, 2.0, 4.0, 8.21, 15.0, 25.0, 60.0], [0.0, 198.0, 222.0, 234.0, 227.0, 221.0, 200.0])      # McMillan 2017
SUN_UVW = np.array([11.1, 242.24, 7.25])        # galaxie_orbites.h, kSunUvw
OMEGA_BARRE = 39.0            # km/s/kpc
ANGLE_BARRE = math.radians(180.0 - 28.0)        # axe de la barre depuis +x (bout proche du côté l > 0)
KPC_LY = 3261.5637769


def vc(R): return np.interp(R, *VC)


def tourner(R, x, y, vphi):
    """Vitesse de rotation (φ décroissants) pour des positions (x, y)."""
    R = np.maximum(R, 1e-6)
    return np.stack([vphi * y / R, -vphi * x / R], 1)


def disque(rng, n, Rd, hz, s0, smax, rmax=15.0):
    # bord du disque d'étoiles mesuré vers 13,9 kpc (Minniti et al. 2011) : coupure adoucie entre 13 et 16 kpc
    R = rng.gamma(2.0, Rd, n * 3)
    R = R[rng.uniform(size=len(R)) < np.clip((16.0 - R) / 3.0, 0.0, 1.0)][:n]
    th = rng.uniform(0, 2 * math.pi, n)
    z = rng.laplace(0.0, hz, n)      # densité exponentielle exp(-|z| / hz) (McMillan 2017) : médiane de |z| = hz ln 2
    p = np.stack([R * np.cos(th), R * np.sin(th), z], 1)
    # agitation : s0 au Soleil, croissance exponentielle vers le centre sur 5 kpc, bornée (disque intérieur mesuré à
    # 50-60 km/s pour le disque mince, APOGEE ; ce n'est pas le bulbe, qui a sa propre agitation de 100 km/s, BRAVA)
    s = np.minimum(s0 * np.exp(-(R - 8.21) / 5.0), smax)
    vt = tourner(R, p[:, 0], p[:, 1], np.maximum(vc(R) - s ** 2 / np.maximum(vc(R), 1.0), 0.5 * vc(R)))       # retard de rotation des étoiles agitées (dérive asymétrique, ordre de grandeur)
    vel = np.zeros((n, 3))
    vel[:, :2] = vt
    er = p[:, :2] / np.maximum(R, 1e-6)[:, None]; ep = np.stack([er[:, 1], -er[:, 0]], 1)
    vel[:, :2] += er * rng.normal(0, 1, (n, 1)) * s[:, None] + ep * rng.normal(0, 1, (n, 1)) * 0.7 * s[:, None]
    vel[:, 2] = rng.normal(0, 1, n) * 0.5 * s
    return p, vel


def bulbe_barre(rng, n):
    nb = int(n * 0.6); nl = n - nb
    s = rng.gamma(3.0, 1.0, nb)                       # densité exp(-s) : volume ∝ s² ds
    d = rng.normal(0, 1, (nb, 3)); d /= np.linalg.norm(d, axis=1)[:, None]
    q = d * s[:, None] * np.array([0.70, 0.44, 0.18])
    along = rng.uniform(-5.0, 5.0, nl) + rng.normal(0, 0.25, nl)
    across = rng.laplace(0.0, 0.5, nl)
    z = np.where(rng.uniform(size=nl) < 0.3, rng.laplace(0, 0.045, nl), rng.laplace(0, 0.18, nl))
    q = np.concatenate([q, np.stack([along, across, z], 1)])
    c, sn = math.cos(ANGLE_BARRE), math.sin(ANGLE_BARRE)
    p = np.stack([q[:, 0] * c - q[:, 1] * sn, q[:, 0] * sn + q[:, 1] * c, q[:, 2]], 1)
    R = np.hypot(p[:, 0], p[:, 1])
    vel = np.zeros((n, 3))
    vel[:, :2] = tourner(R, p[:, 0], p[:, 1], np.minimum(OMEGA_BARRE * R, vc(R)))
    vel += rng.normal(0, 100.0, (n, 3))
    return p, vel


def halo(rng, n):
    r = (1.0 ** -2.5 - rng.uniform(0, 1, n) * (1.0 ** -2.5 - 50.0 ** -2.5)) ** (-1 / 2.5)      # ρ ∝ r^-3,5 entre 1 et 50 kpc
    d = rng.normal(0, 1, (n, 3)); d /= np.linalg.norm(d, axis=1)[:, None]
    p = d * r[:, None] * np.array([1.0, 1.0, 0.6])
    return p, rng.normal(0, 120.0, (n, 3))


def jeunes(rng, n, wise):
    sun = np.array([-v.R0, 0.0, 0.0])
    regions = v.regions_hii(wise, sun)
    nh = min(len(regions) * vj.N_PAR_HII, n // 5)
    pb = vj.tirer_bras(rng, n - nh)
    k = rng.integers(0, len(regions), nh)
    reg = np.array(regions)
    ph = reg[k, :3] + rng.normal(0, 1, (nh, 3)) * np.maximum(reg[k, 3], 0.03)[:, None]
    p = np.concatenate([pb, ph])
    R = np.hypot(p[:, 0], p[:, 1])
    vel = np.zeros((n, 3)); vel[:, :2] = tourner(R, p[:, 0], p[:, 1], vc(R))
    vel += rng.normal(0, 10.0, (n, 3))
    hii = np.zeros(n, bool); hii[n - nh:] = rng.uniform(size=nh) < 0.5      # moitié gaz ionisé (rouge-rose), moitié étoiles
    return p, vel, hii


def main():
    gaia_bin, etoiles_bin, agrege, wise, sortie = sys.argv[1:6]
    t0 = time.time()
    rng = np.random.default_rng(20261113)
    nb = {c: int(N_TOTAL * f) for c, f in PARTS.items()}
    nb[1] += N_TOTAL - sum(nb.values())
    pos, vel, comp, teff = [], [], [], []
    L_comp = {}
    # lumière : masse / rapport masse-lumière de la population (bande V), remise à l'échelle de la lumière totale mesurée
    poids = {c: MASSE[c] / ML_V[c] for c in (1, 4, 2, 6)}
    for c in poids: L_comp[c] = L_V * poids[c] / sum(poids.values())
    L_comp[5] = PART_JEUNES * L_comp[1]; L_comp[1] *= 1 - PART_JEUNES
    p, u = disque(rng, nb[1], 2.50, 0.30, 35.0, 60.0); pos.append(p); vel.append(u); comp.append(np.full(nb[1], 1, np.int8))
    teff.append(np.clip(rng.normal(5200, 700, nb[1]), 3300, 9000))
    p, u = disque(rng, nb[4], 3.02, 0.90, 50.0, 90.0); pos.append(p); vel.append(u); comp.append(np.full(nb[4], 4, np.int8))
    teff.append(np.clip(rng.normal(4900, 400, nb[4]), 3300, 7000))
    p, u = bulbe_barre(rng, nb[2]); pos.append(p); vel.append(u); comp.append(np.full(nb[2], 2, np.int8))
    teff.append(np.clip(rng.normal(4400, 300, nb[2]), 3300, 6000))
    p, u, hii = jeunes(rng, nb[5], wise); pos.append(p); vel.append(u); comp.append(np.full(nb[5], 5, np.int8))
    t5 = np.exp(rng.uniform(math.log(9000), math.log(30000), nb[5])); t5[hii] = 2400.0      # gaz ionisé : couleur rouge (Hα)
    teff.append(t5)
    p, u = halo(rng, nb[6]); pos.append(p); vel.append(u); comp.append(np.full(nb[6], 6, np.int8))
    teff.append(np.clip(rng.normal(5000, 500, nb[6]), 3500, 7000))
    pos, vel, comp, teff = np.concatenate(pos), np.concatenate(vel), np.concatenate(comp), np.concatenate(teff)
    lum = np.zeros(len(pos))
    for c, Lc in L_comp.items():
        m = comp == c
        w = rng.pareto(1.5, m.sum()) + 1.0
        lum[m] = Lc * w / w.sum()
    print(f'{len(pos)} traceurs tirés ({time.time() - t0:.0f} s) ; lumière par composante : ' +
          ', '.join(f'{c}: {L_comp[c]:.2e}' for c in sorted(L_comp)))

    # Gaia montre déjà les étoiles mesurées près du Soleil : chaque traceur ne garde que ce qui manque dans sa case.
    D = v.data_keys(['M_GAL2ECL', 'SGRA_GAL'])
    gal2ecl = np.array(D['M_GAL2ECL']); ecl2gal = gal2ecl.T
    sgra = np.array(D['SGRA_GAL']) / np.linalg.norm(D['SGRA_GAL']); sun = -v.R0 * sgra
    x, y, z = v.axes(v.NX, v.HX), v.axes(v.NY, v.HX), v.axes(v.NZ, v.HZ)
    cat, _ = v.lumiere_cataloguee(gaia_bin, etoiles_bin, ecl2gal, sun, x, y, z, agrege)      # L☉/pc³ par case
    i = np.floor((pos[:, 0] + v.HX) / (2 * v.HX) * v.NX).astype(np.int64)
    j = np.floor((pos[:, 1] + v.HX) / (2 * v.HX) * v.NY).astype(np.int64)
    k = np.floor((pos[:, 2] + v.HZ) / (2 * v.HZ) * v.NZ).astype(np.int64)
    dans = (i >= 0) & (i < v.NX) & (j >= 0) & (j < v.NY) & (k >= 0) & (k < v.NZ)
    case = np.where(dans, (k * v.NY + j) * v.NX + i, 0)
    Ltr = np.bincount(case[dans], lum[dans], v.NX * v.NY * v.NZ) / (100.0 * 100.0 * 50.0)
    part = np.clip((Ltr - cat.ravel()) / np.maximum(Ltr, 1e-30), 0.0, 1.0)
    reste = np.where(dans & (comp != 6), part[case], 1.0)
    lum_vue = lum * reste
    print(f'Gaia montre déjà {1 - lum_vue.sum() / lum.sum():.1%} de la lumière des traceurs ({time.time() - t0:.0f} s)')

    graine = rng.integers(0, 2 ** 32, len(pos), dtype=np.uint64).astype(np.uint32)
    meta = dict(galaxie='voie_lactee', date='2026-11-13', repere='phys::galaxie (galaxie_orbites.h), kpc, km/s, t = 0',
                nombre={str(c): int((comp == c).sum()) for c in sorted(set(comp.tolist()))},
                lumiere_V_Lsol=float(lum.sum()), lumiere_montree_hors_Gaia=float(lum_vue.sum()),
                sources='docs/parametres-galaxies.md (modeles-depart), McMillan 2017, Wegg & Gerhard 2013, Wegg et al. 2015, '
                        'Bland-Hawthorn & Gerhard 2016, Reid et al. 2019, Anderson et al. 2014, Licquia et al. 2015, Deason et al. 2011',
                rotation='axe -z (φ décroissants), McMillan 2017', vitesse_ensemble_kms=[0, 0, 0],
                modele='bras prolongés au-delà des portions mesurées, lumière par traceur (Pareto), couleurs par composante, halo')
    os.makedirs(sortie, exist_ok=True)
    np.savez_compressed(os.path.join(sortie, 'etoiles_visibles_voie_lactee.npz'), pos=pos, vel=vel, lum=lum.astype(np.float32),
                        teff=teff.astype(np.float32), comp=comp, graine=graine, meta=json.dumps(meta, ensure_ascii=False))
    ecrire_gaia(os.path.join(sortie, 'vl_etoiles.bin'), pos, vel, lum_vue, teff, sun, gal2ecl, gaia_bin.split(',')[0])
    print(f'-> {sortie} ({time.time() - t0:.0f} s)')


def ecrire_gaia(chemin, pos, vel, lum, teff, sun, gal2ecl, gaia_ref):
    """Au format gaia.bin (gaia_convertir.py) : écliptique héliocentrique en al, vitesse héliocentrique en km/s."""
    T = np.fromfile(gaia_ref, np.float32, 256, offset=32)          # même table de couleurs que gaia.bin
    ok = np.isfinite(T)
    pas_t = np.arange(256)[ok]
    o = np.argsort(T[ok])
    pas = pas_t[o][np.clip(np.searchsorted(T[ok][o], teff), 0, ok.sum() - 1)].astype(np.uint8)
    p = ((pos - sun) @ gal2ecl.T) * KPC_LY
    u = (vel - SUN_UVW) @ gal2ecl.T
    M = M_SOL_V - 2.5 * np.log10(np.maximum(lum, 1e-6))
    Rc = float(np.abs(p).max()) * 1.0001
    q = np.floor((p + Rc) / (2 * Rc) * (1 << 21)).clip(0, (1 << 21) - 1)
    cles = morton(q)
    o = np.argsort(cles, kind='stable'); p, u, M, pas, cles = p[o], u[o], M[o], pas[o], cles[o]
    fs = feuilles(cles)
    num = np.zeros(len(p), np.int64)
    for i, (lo, hi) in enumerate(fs): num[lo:hi] = i
    o = np.lexsort((M, num)); p, u, M, pas = p[o], u[o], M[o], pas[o]
    rec = np.zeros(len(p), np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('m', '<f2'), ('c', 'u1'), ('f', 'u1')]))
    rec['x'], rec['y'], rec['z'], rec['m'], rec['c'] = p[:, 0], p[:, 1], p[:, 2], M, pas
    rec['f'] = 1 | 2 | 16      # vitesse complète, orbite exacte ; 16 = étoile du MODÈLE (pas mesurée)
    vel16 = np.zeros((len(p), 4), '<i2'); vel16[:, :3] = np.clip(np.rint(u / V_PAS), -32767, 32767)
    fe = np.zeros(len(fs), np.dtype([('min', '<f4', 3), ('n', '<u4'), ('max', '<f4', 3), ('r0', '<u4'), ('premier', '<u8'), ('r1', '<u8')]))
    for i, (lo, hi) in enumerate(fs):
        fe['min'][i], fe['max'][i] = p[lo:hi].min(0), p[lo:hi].max(0)
        fe['n'][i], fe['premier'][i] = hi - lo, lo
    lumi = 10 ** (-0.4 * M)
    tr = np.clip(np.floor((M - TRANCHE0) / TRANCHE_L), 0, TRANCHES - 1).astype(np.int64)
    cle = num * TRANCHES + tr; nfe = len(fs) * TRANCHES
    res = np.zeros(len(fs), np.dtype([('c', '<f4', 3), ('r', '<f4'), ('lum', '<f4', TRANCHES), ('couleur', '<f4', TRANCHES)]))
    res['lum'] = np.bincount(cle, lumi, nfe).reshape(-1, TRANCHES)
    Lc = np.bincount(cle, lumi, nfe)
    res['couleur'] = np.where(Lc > 0, np.bincount(cle, lumi * pas.astype(np.float64), nfe) / np.maximum(Lc, 1e-300), 255).reshape(-1, TRANCHES)
    Lf = np.bincount(num, lumi, len(fs))
    for a in range(3): res['c'][:, a] = np.bincount(num, lumi * p[:, a], len(fs)) / np.maximum(Lf, 1e-300)
    head = (b'UNIVGAI1' + np.uint64(len(p)).tobytes() + np.uint32(len(fs)).tobytes() + np.array([2016.0, BPRP0, BPRP_PAS], '<f4').tobytes()
            + T.tobytes() + np.uint32(TRANCHES).tobytes() + np.array([TRANCHE0, TRANCHE_L], '<f4').tobytes())
    with open(chemin + '.partiel', 'wb') as f:
        f.write(head + b'\0' * (4096 - len(head)))
        for b in (fe.tobytes(), rec.tobytes(), vel16.tobytes(), res.tobytes()): f.write(b + b'\0' * (-len(b) % 64))
    os.replace(chemin + '.partiel', chemin)
    print(f'{chemin} : {len(p)} traceurs, {len(fs)} feuilles, {os.path.getsize(chemin) / 1e6:.0f} Mo')


if __name__ == '__main__':
    main()
