#!/usr/bin/env python3
"""Profondeur MESURÉE du Petit Nuage de Magellan : chaque étoile visible du Petit Nuage reste à sa place sur le ciel
(photo), mais sa distance vient des étoiles variables d'OGLE-IV autour d'elle, au lieu d'un disque mince.

Données (VizieR, miroir vizier.cfa.harvard.edu ; le serveur du CDS refuse) :
- céphéides classiques : Soszyński et al. 2015 (AcA 65, 297), tables smccep / lmccep et smcident / lmcident ;
- RR Lyrae : Soszyński et al. 2016 (AcA 66, 131), tables smcrrabc / lmcrrabc et smcident / lmcident.
Méthode, comme Jacyszyn-Dobrzeniecka et al. 2016 et 2017 (distances relatives) :
- indice de Wesenheit W_I = I - 1,55 (V - I) (insensible à la poussière ; convention OGLE) ;
- relation période-Wesenheit ajustée ICI, par Nuage et par mode (céphéides F et 1O, RR Lyrae RRab), écrêtée à 3 σ ;
- écart à la relation -> distance relative 10^(δ/5) ; zéro : la médiane du Petit Nuage est mise à la distance de
  Graczyk et al. 2020 (module 18,977, pipeline/constantes/univers.json) ;
- largeur propre de la relation : écart type robuste dans le Grand Nuage, disque mince (majorant : sa propre épaisseur y
  est comptée) ; retirée en quadrature de la dispersion locale du Petit Nuage.
Pose des traceurs : étoiles jeunes (composante 5) d'après les céphéides (100 à 300 Ma), les autres d'après les RR Lyrae
(plus de 10 Ga). Pour chaque traceur : décalage médian des 60 variables les plus proches sur le ciel, plus un tirage
normal de largeur la dispersion propre locale. Vitesses inchangées [modèle : non recalculées pour la nouvelle place].

Usage : python petit_nuage_profondeur.py <dossier OGLE> <etoiles_visibles_petit_nuage.npz> <sortie.npz> [univers.json]
"""
import json
import math
import os
import sys

import numpy as np

R_WES = 1.55
VOISINS = 60
ICI = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(os.path.dirname(ICI), 'constantes', 'univers.json')
SOLEIL = np.array([-8.2, 0.0, 0.0])
A_G = np.array([[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132],
                [0.4941094278755837, -0.4448296299600112, 0.7469822444972189],
                [-0.8676661490190047, -0.1980763734312015, 0.4559837761750669]])


def lire_tsv(chemin):
    """Table VizieR asu-tsv -> liste de dict (lignes de données seulement)."""
    lignes = [l.rstrip('\n') for l in open(chemin, encoding='utf-8', errors='replace') if l.strip() and not l.startswith('#')]
    tete = lignes[0].split('\t')
    return [dict(zip(tete, (c.strip() for c in l.split('\t')))) for l in lignes[3:]]


def sexa(ra, dec):
    h, m, s = (float(x) for x in ra.replace(':', ' ').split())
    sg = -1.0 if dec.strip().startswith('-') else 1.0
    d, dm, ds = (abs(float(x)) for x in dec.replace(':', ' ').split())
    return 15.0 * (h + m / 60 + s / 3600), sg * (d + dm / 60 + ds / 3600)


def charger(dossier, cat, nuage):
    """Variables d'un Nuage : ra, dec (degrés), log P, W_I, mode. cat : 'cep' ou 'rrl'."""
    pre = 'J_AcA_65_297_' if cat == 'cep' else 'J_AcA_66_131_'
    phot = lire_tsv(os.path.join(dossier, f'{pre}{nuage}{"cep" if cat == "cep" else "rrabc"}.tsv'))
    ident = {r['Star']: r for r in lire_tsv(os.path.join(dossier, f'{pre}{nuage}ident.tsv'))}
    out = []
    for r in phot:
        mode = r.get('Mode') or r.get('Type') or ''
        mode = mode.strip()
        if (cat == 'cep' and mode not in ('F', '1O')) or (cat == 'rrl' and mode != 'RRab'):
            continue
        if not r.get('<Imag>') or not r.get('<Vmag>') or r['Star'] not in ident:
            continue
        I, V, P = float(r['<Imag>']), float(r['<Vmag>']), float(r['Per'])
        ra, dec = sexa(ident[r['Star']]['RAJ2000'], ident[r['Star']]['DEJ2000'])
        out.append((ra, dec, math.log10(P), I - R_WES * (V - I), mode))
    ra, dec, lp, w, m = zip(*out)
    return np.array(ra), np.array(dec), np.array(lp), np.array(w), np.array(m)


def ecarts_pw(lp, w, mode):
    """Écart de chaque étoile à la relation période-Wesenheit de son mode (ajustée, écrêtée à 3 σ)."""
    d = np.full(len(w), np.nan)
    for md in np.unique(mode):
        s = mode == md
        garde = np.ones(s.sum(), bool)
        for _ in range(10):
            b, a = np.polyfit(lp[s][garde], w[s][garde], 1)
            r = w[s] - (a + b * lp[s])
            sig = 1.4826 * np.median(np.abs(r[garde] - np.median(r[garde])))
            neuf = np.abs(r - np.median(r[garde])) < 3 * sig
            if (neuf == garde).all():
                break
            garde = neuf
        d[np.flatnonzero(s)] = np.where(garde, r - np.median(r[garde]), np.nan)
    return d


def robuste(x):
    q25, q75 = np.nanpercentile(x, [25, 75])
    return float((q75 - q25) / 1.349)


def direction_eq(ra, dec):
    ra, dec = np.radians(ra), np.radians(dec)
    return np.stack([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)], axis=-1)


def mesures(dossier, cat, D0):
    """Variables du Petit Nuage : direction galactique, distance (kpc) ; largeur propre de la relation (mag)."""
    ra, dec, lp, w, m = charger(dossier, cat, 'smc')
    d = ecarts_pw(lp, w, m)
    ok = np.isfinite(d)
    _, _, lpL, wL, mL = charger(dossier, cat, 'lmc')
    sig_lmc = robuste(ecarts_pw(lpL, wL, mL))
    dist = D0 * 10 ** (d[ok] / 5.0)
    return dict(dir=direction_eq(ra[ok], dec[ok]) @ A_G.T, dist=dist, sig_pw_mag=sig_lmc, n=int(ok.sum()),
                sig_smc_mag=robuste(d[ok]))


def poser(dirs, D0, ref, rng):
    """Distances des traceurs (directions galactiques depuis le Soleil) d'après les variables voisines sur le ciel."""
    idx = np.empty((len(dirs), VOISINS), np.int64)      # plus proches voisines sur le ciel (cosinus le plus grand)
    for a in range(0, len(dirs), 4000):
        c = dirs[a:a + 4000] @ ref['dir'].T
        idx[a:a + 4000] = np.argpartition(-c, VOISINS, axis=1)[:, :VOISINS]
    voisines = ref['dist'][idx]
    med = np.median(voisines, axis=1)
    q25, q75 = np.percentile(voisines, [25, 75], axis=1)
    sig_obs = (q75 - q25) / 1.349
    sig_pw_kpc = med * math.log(10) / 5 * ref['sig_pw_mag']
    sig = np.sqrt(np.maximum(sig_obs ** 2 - sig_pw_kpc ** 2, 0.0))
    return med + rng.normal(0, 1, len(med)) * sig, sig


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    dossier, entree, sortie = sys.argv[1:4]
    table = json.load(open(sys.argv[4] if len(sys.argv) > 4 else TABLE, encoding='utf-8'))
    D0 = 10 ** (table['galaxies']['petit_nuage']['observe']['dmod'] / 5 + 1) / 1000.0
    z = np.load(entree)
    meta = json.loads(str(z['meta']))
    pos, comp = z['pos'].copy(), z['comp']
    rng = np.random.default_rng(7919 * 4)
    dirs = pos - SOLEIL
    dirs /= np.linalg.norm(dirs, axis=1)[:, None]
    infos = {}
    for cat, sel in (('cep', comp == 5), ('rrl', comp != 5)):
        ref = mesures(dossier, cat, D0)
        d, sig = poser(dirs[sel], D0, ref, rng)
        pos[sel] = SOLEIL + dirs[sel] * d[:, None]
        infos[cat] = dict(variables=ref['n'], largeur_relation_lmc_mag=round(ref['sig_pw_mag'], 4), largeur_smc_mag=round(ref['sig_smc_mag'], 4),
                          dispersion_propre_mediane_kpc=round(float(np.median(sig)), 3), traceurs=int(sel.sum()))
        print(f"{cat} : {ref['n']} variables, largeur de la relation (Grand Nuage) {ref['sig_pw_mag']:.3f} mag, Petit Nuage {ref['sig_smc_mag']:.3f} mag ; "
              f"{sel.sum()} traceurs posés, dispersion propre médiane {np.median(sig):.2f} kpc")
    meta['profondeur'] = dict(statut='mesurée (distances relatives des variables OGLE-IV, relation période-Wesenheit ajustée ici)',
                              sources='Soszyński et al. 2015 (AcA 65, 297) ; Soszyński et al. 2016 (AcA 66, 131) ; zéro : Graczyk et al. 2020',
                              methode=f'médiane des {VOISINS} variables les plus proches sur le ciel + dispersion propre locale ; jeunes : céphéides, autres : RR Lyrae',
                              vitesses='inchangées (modèle du disque) : non recalculées pour la nouvelle place', details=infos, date='2026-11-24')
    np.savez_compressed(sortie, pos=pos, vel=z['vel'], lum=z['lum'], teff=z['teff'], comp=comp, graine=z['graine'], meta=json.dumps(meta, ensure_ascii=False))


if __name__ == '__main__':
    main()
