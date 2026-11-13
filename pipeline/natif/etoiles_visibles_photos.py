#!/usr/bin/env python3
"""Étoiles visibles d'aujourd'hui (contrat docs/contrat-etoiles-visibles.md) : Andromède, Triangle, Grand et Petit Nuage,
tirées de leurs VRAIES photos (galaxies_images.py).

Pour qu'une galaxie ne change pas de forme quand le temps démarre, elle doit être faite des mêmes traceurs que ceux que
le calcul fait évoluer. Ici, chaque traceur est un point de la photo :
- tirage : pixels tirés au prorata de leur lumière (photo préparée, lumière = valeur²), placés au hasard dans le pixel ;
- position : direction du pixel vue du Soleil, prolongée jusqu'au plan du disque (angle de position et inclinaison
  publiés, galaxies_images.tsv), à la distance mesurée (module de distance) ; épaisseur du disque [modèle] ;
- couleur : rapport bleu/rouge du pixel -> température [approchée] ; pixels nettement rouges dans les bras : régions HII ;
- lumière : magnitude absolue V publiée, partagée entre les traceurs (loi de Pareto, indice 1,5) [modèle] ;
- vitesse : vitesse d'ensemble MESURÉE (module de distance, mouvement propre, vitesse radiale : mêmes valeurs que
  pipeline/fusion/groupe_local_clones.py, variante wu2026 ; Petit Nuage : Zivick et al. 2018, Graczyk et al. 2020),
  plus la rotation du disque (courbe de rotation publiée) et l'agitation ; sens de rotation : côté du grand axe qui
  s'approche [M31 : nord-est, certain ; les autres : à vérifier].
Repère phys::galaxie de l'appli : centre de la Voie lactée à l'origine, Soleil à (-8,2 ; 0 ; 0) kpc, vitesse du Soleil
(11,1 ; 245,04 ; 7,25) km/s (galaxie_orbites.h, table unique).
Usage : python etoiles_visibles_photos.py <dossier galaxies-images> <dossier de sortie> [univers.json] [gaia.bin de référence (table des couleurs)]
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')
import json, math, os, sys
import numpy as np

PARETO_MAX = 10.0      # un traceur porte au plus 10 fois la lumière du plus faible : pas de point démesuré [modèle]
from PIL import Image
import astropy.units as u
from astropy.coordinates import SkyCoord, Galactocentric, CartesianDifferential, Distance

SOLEIL_R0 = 8.2
SOLEIL_V = (11.1, 232.8 + 12.24, 7.25)      # km/s, galaxie_orbites.h (kSunUvw, table unique) ; sert seulement au contrôle astropy
# Table unique (pipeline/constantes/univers.json, branche table-unique, PR 97) : source unique pour la place, la vitesse
# d'ensemble et l'axe de rotation d'aujourd'hui (galaxies.<nom>.aujourdhui, galaxies.<nom>.disque.axe_rotation).
TABLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'constantes', 'univers.json')
# nom : fichier, nombre de traceurs (plafonds du contrat), module de distance, µα* et µδ (µas/an), v_los (km/s),
#       vitesse de rotation (km/s) et rayon où elle est atteinte (kpc), agitation (km/s), épaisseur (kpc), bulbe (kpc)
GALAXIES = {
    'andromede':   ('m31', 3_000_000, 24.407, 45.9, -20.5, -301.0, 250.0, 6.0, 30.0, 0.30, 1.5),
    'triangle':    ('m33', 500_000, 24.67, 30.6, 19.0, -179.2, 120.0, 8.0, 15.0, 0.20, 0.0),
    'grand_nuage': ('lmc', 500_000, 18.477, 1910.0, 229.0, 262.2, 92.0, 4.0, 20.0, 0.40, 0.0),
    'petit_nuage': ('smc', 500_000, 18.977, 772.0, -1117.0, 145.6, 25.0, 3.0, 26.0, 1.50, 0.0),
}
SOURCES = ('Sawala et al. 2025 et Wu et al. 2026 (distances, mouvements propres, vitesses radiales, comme '
           'groupe_local_clones.py) ; Petit Nuage : Kallivayalil et al. 2013, Graczyk et al. 2020 ; rotation : Chemin et al. '
           '2009 (M31), Corbelli et al. 2014 (M33), van der Marel & Kallivayalil 2014 (Grand Nuage), Stanimirović 2004 (Petit Nuage)')


def lire_tsv(dossier):
    out = {}
    for l in open(os.path.join(dossier, 'galaxies_images.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if len(r) >= 8: out[r[1][:-4]] = dict(ra=float(r[2]), dec=float(r[3]), champ=float(r[4]), pa=float(r[5]), incl=float(r[6]), mv=float(r[7]))
    return out


def eq_vers_gal():
    """Matrice ICRS -> galactique (astropy), pour orienter le disque dans le repère de l'appli."""
    c = SkyCoord(x=[1, 0, 0], y=[0, 1, 0], z=[0, 0, 1], representation_type='cartesian', frame='icrs')
    g = c.galactic.cartesian.xyz.value       # colonnes : images des axes
    return np.array(g)


def main():
    src, sortie = sys.argv[1:3]
    geo = lire_tsv(src)
    table = json.load(open(sys.argv[3] if len(sys.argv) > 3 else TABLE, encoding='utf-8'))
    E2G = eq_vers_gal()
    gc_frame = Galactocentric(galcen_distance=SOLEIL_R0 * u.kpc, z_sun=0 * u.pc,
                              galcen_v_sun=CartesianDifferential(list(SOLEIL_V) * u.km / u.s))
    os.makedirs(sortie, exist_ok=True)
    tous = []
    for nom, (fic, n, dmod, pmra, pmdec, vr, vrot, rrot, sig, hz, rbulbe) in GALAXIES.items():
        if fic not in geo: print(f'{nom} : photo absente'); continue
        g = geo[fic]
        rng = np.random.default_rng(sum(map(ord, nom)) * 7919)      # graine fixe par galaxie
        img = np.asarray(Image.open(os.path.join(src, fic + '.png'))).astype(np.float64)[..., :3] / 255.0
        lin = img ** 2
        L = lin @ np.array([0.2126, 0.7152, 0.0722])
        h, w = L.shape
        k = rng.choice(h * w, n, p=L.ravel() / L.sum())
        lig, col = k // w + rng.uniform(0, 1, n), k % w + rng.uniform(0, 1, n)
        # direction de chaque point (équatorial), comme galaxies_images.h
        ra, dec, pa, inc = (math.radians(g[x]) for x in ('ra', 'dec', 'pa', 'incl'))
        u0 = np.array([math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)])
        est = np.array([-math.sin(ra), math.cos(ra), 0.0]); nord = np.cross(u0, est)
        grand = math.cos(pa) * nord + math.sin(pa) * est; petit = -math.sin(pa) * nord + math.cos(pa) * est
        nrm = np.cross(grand, math.cos(inc) * petit + math.sin(inc) * u0); nrm /= np.linalg.norm(nrm)
        demi = math.tan(math.radians(g['champ']) / 2)
        xi, eta = (0.5 - col / w) * 2 * demi, (0.5 - lig / h) * 2 * demi
        d = u0[None] + xi[:, None] * est[None] + eta[:, None] * nord[None]
        d /= np.linalg.norm(d, axis=1)[:, None]
        D = 10 ** (dmod / 5 + 1) / 1000.0                      # kpc
        centre_eq = u0 * D
        t = (centre_eq @ nrm) / np.where(np.abs(d @ nrm) > 1e-3, d @ nrm, 1e-3)
        off = d * t[:, None] - centre_eq[None]                 # dans le plan du disque (kpc, équatorial)
        off += nrm[None] * np.arctanh(rng.uniform(-0.999, 0.999, n))[:, None] * hz      # épaisseur [modèle]
        R = np.linalg.norm(off, axis=1)
        # rotation : côté +grand axe qui s'approche (vitesse vers le Soleil, -u0)
        vphi = vrot * np.clip(R / rrot, 0, 1)
        # vitesse d'ensemble mesurée -> phys::galaxie
        sky = SkyCoord(ra=g['ra'] * u.deg, dec=g['dec'] * u.deg, distance=D * u.kpc, pm_ra_cosdec=pmra / 1000 * u.mas / u.yr,
                       pm_dec=pmdec / 1000 * u.mas / u.yr, radial_velocity=vr * u.km / u.s)
        gc = sky.transform_to(gc_frame)
        c_pos = np.array([gc.x.to_value(u.kpc), gc.y.to_value(u.kpc), gc.z.to_value(u.kpc)])
        c_vel = np.array([gc.v_x.to_value(u.km / u.s), gc.v_y.to_value(u.km / u.s), gc.v_z.to_value(u.km / u.s)])
        source_ens = 'module de distance, mouvement propre et vitesse radiale mesurés (voir sources), astropy'
        spin_g = None
        t_gal = table['galaxies'].get(nom, {})
        if t_gal.get('aujourdhui'):
            ecart_pos = float(np.linalg.norm(np.array(t_gal['aujourdhui']['position']) - c_pos))
            ecart_vel = float(np.linalg.norm(np.array(t_gal['aujourdhui']['vitesse']) - c_vel))
            c_pos, c_vel = np.array(t_gal['aujourdhui']['position']), np.array(t_gal['aujourdhui']['vitesse'])
            source_ens = f'pipeline/constantes/univers.json (table unique ; écart avec le calcul astropy de ce script : {ecart_pos:.3f} kpc, {ecart_vel:.2f} km/s)'
        if (t_gal.get('disque') or {}).get('axe_rotation'):
            spin_g = np.array(t_gal['disque']['axe_rotation'])
        # rotation du disque dans le repère de l'appli : axe du calcul quand il existe, sinon côté du grand axe qui s'approche
        off_g = off @ E2G.T
        if spin_g is None:
            spin_g = E2G @ (nrm * (1.0 if np.dot(np.cross(nrm, grand), -u0) > 0 else -1.0))
        spin_g = spin_g / np.linalg.norm(spin_g)
        n_photo = E2G @ nrm
        accord = abs(float(np.dot(spin_g, n_photo)))      # le plan de la photo et l'axe de rotation doivent concorder
        axe_calcul = spin_g.copy()
        if accord < 0.95:
            # L'axe du calcul ne tombe pas sur la normale du disque mesuré (angle de position et inclinaison publiés) :
            # on garde le plan MESURÉ et seulement le SENS de rotation du calcul ; l'écart est écrit dans meta.
            spin_g = n_photo * (1.0 if np.dot(axe_calcul, n_photo) >= 0 else -1.0)

        tang = np.cross(spin_g[None], off_g); tang /= np.maximum(np.linalg.norm(tang, axis=1), 1e-9)[:, None]
        vel_int = tang * vphi[:, None] + rng.normal(0, sig, (n, 3))
        pos = c_pos[None] + off_g
        vel = c_vel[None] + vel_int
        # contrôle : vitesse le long de la ligne de visée (vue du Soleil) du côté +grand axe (vers l'angle de position)
        ligne = E2G @ u0
        cote = (off @ grand) > 0.3 * np.percentile(np.abs(off @ grand), 90)
        v_cote = float(np.mean(vel_int[cote] @ ligne))
        # couleur et composante
        pix = img[np.clip(lig.astype(int), 0, h - 1), np.clip(col.astype(int), 0, w - 1)]
        r_br = (pix[:, 2] + 0.02) / (pix[:, 0] + 0.02)
        teff = np.clip(5000.0 * r_br ** 1.5, 3200.0, 25000.0)
        rouge = (pix[:, 0] > 1.25 * pix[:, 2]) & (pix[:, 0] > 1.2 * pix[:, 1]) & (R > 2.0)
        comp = np.where(R < rbulbe, 2, 1).astype(np.int8)
        comp[rouge | (teff > 9000)] = 5
        teff[rouge] = 2400.0
        lv = 10 ** (-0.4 * (g['mv'] - 4.83))
        wts = np.minimum(rng.pareto(1.5, n) + 1.0, PARETO_MAX)
        lum = (lv * wts / wts.sum()).astype(np.float32)
        graine = rng.integers(0, 2 ** 32, n, dtype=np.uint64).astype(np.uint32)
        meta = dict(galaxie=nom, date='2026-11-13', repere='phys::galaxie (galaxie_orbites.h), kpc, km/s, t = 0',
                    photo=f'{fic}.png ({"Mellinger 2009" if fic in ("lmc", "smc") else "DSS2"}, SkyView)', distance_kpc=D,
                    centre_kpc=c_pos.tolist(), vitesse_kms=c_vel.tolist(), source_ensemble=source_ens,
                    axe_rotation=spin_g.tolist(), axe_du_calcul=axe_calcul.tolist(), accord_axe_plan_photo=accord, vitesse_visee_cote_angle_position_kms=v_cote, nombre={str(c): int((comp == c).sum()) for c in (1, 2, 5)},
                    sources=SOURCES, modele='épaisseur, lumière par traceur, couleur depuis la photo, sens de rotation hors M31')
        np.savez_compressed(os.path.join(sortie, f'etoiles_visibles_{nom}.npz'), pos=pos, vel=vel, lum=lum, teff=teff.astype(np.float32),
                            comp=comp, graine=graine, meta=json.dumps(meta, ensure_ascii=False))
        sens = "s'éloigne" if v_cote > 0 else "s'approche"
        tous.append((pos, vel, lum, teff, comp))
        print(f"{nom} : {n} traceurs, centre {np.round(c_pos, 1)} kpc, vitesse {np.round(c_vel, 1)} km/s ({source_ens}) ; "
              f"axe {np.round(spin_g, 3)} (accord avec le plan de la photo {accord:.3f}) ; côté de l'angle de position : {v_cote:+.0f} km/s ({sens})")

    # Pour l'appli : les mêmes traceurs au format gaia.bin (voisines_etoiles.bin), drapeaux 16 (modèle) et 32 (galaxie voisine,
    # rang de la galaxie dans le 4e champ de la vitesse) : à toute date, chaque galaxie se déplace en bloc le long de son
    # centre de référence et ses étoiles tournent autour (gaia.vert) ; pas d'orbite dans le potentiel de la Voie lactée.
    if tous and len(sys.argv) > 4:
        import voie_lactee as v
        from etoiles_visibles import ecrire_gaia
        D = v.data_keys(['M_GAL2ECL', 'SGRA_GAL'])
        gal2ecl = np.array(D['M_GAL2ECL'])
        sgra = np.array(D['SGRA_GAL']) / np.linalg.norm(D['SGRA_GAL']); sun = -v.R0 * sgra
        P, V, L, T, C = (np.concatenate([t[k] for t in tous]) for k in range(5))
        # rang de la galaxie (0 Andromède, 1 Triangle, 2 Grand, 3 Petit Nuage) + 16 x composante (vieillissement de la lumière)
        rang = np.concatenate([np.full(len(t[0]), k, np.int16) for k, t in enumerate(tous)]) + 16 * C.astype(np.int16)
        ecrire_gaia(os.path.join(sortie, 'voisines_etoiles.bin'), P, V, L, T, sun, gal2ecl, sys.argv[4], drapeaux=1 | 2 | 16 | 32, aux=rang)


if __name__ == '__main__':
    main()
