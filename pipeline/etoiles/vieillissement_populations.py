#!/usr/bin/env python3
"""Vieillissement de la lumière des étoiles visibles (traceurs) : table (âge, métallicité) → luminosité, température.

Pourquoi : les traceurs de `etoiles_visibles_<galaxie>.npz` (docs/contrat-etoiles-visibles.md) portent la lumière
MESURÉE aujourd'hui (`lum`, `teff`). Quand le film avance, les étoiles qu'ils représentent vieillissent : les plus
massives meurent, la lumière baisse et rougit. Comme `pipeline/natif/etoiles_vie.py` (fil « vie des étoiles ») pour les
étoiles une à une, l'appli garde la mesure d'aujourd'hui et n'y applique que la VARIATION calculée par le modèle :

    lum(t)  = lum_mesurée  × L_pop(t) / L_pop(0)
    teff(t) = teff_mesurée × T_pop(t) / T_pop(0)

À t = 0, rien ne change.

Modèle (rien d'ajusté ici) :
- isochrones MIST v1.2, rotation v/vcrit = 0,4, 15 métallicités de [Fe/H] = −4 à +0,5 (Choi et al. 2016, ApJ 823, 102 ;
  Dotter 2016, ApJS 222, 8), fichiers « basic » de https://mist.science ;
- fonction de masse initiale de Kroupa 2001 (pentes 1,3 et 2,3, coude à 0,5 M☉), de 0,1 à la plus grande masse vivante ;
- population simple (une date de naissance) : L(τ) = Σ ξ(m) Δm L(m, τ) par masse solaire formée ; les naines blanches
  (absentes des isochrones) ne sont pas comptées : quelques % de la lumière bolométrique d'une population de 10 Ga
  [Probable], dit dans la table ;
- couleur : chaque point de l'isochrone rayonne comme un corps noir (rayon tiré de L et Teff) ; T_pop est la
  température du corps noir qui a le même rapport de flux à 440 et 550 nm (bandes B et V) que la somme [Supposition :
  approximation, suffisante pour une teinte] ;
- populations composées (histoire de formation par composante du traceur, `comp`) : moyenne des populations simples
  pondérée par la masse formée à chaque âge. Les histoires sont des HYPOTHÈSES d'usage, sourcées quand c'est possible,
  et marquées « supposé » dans la table.

Deux régimes pour le futur et le passé :
- « sans_naissance » : ce que fait le film N-corps (sans gaz, rien ne naît) ; les étoiles nées après t ne comptent pas
  dans le passé, aucune ne naît dans le futur ;
- « naissance_continue » : les composantes qui forment des étoiles aujourd'hui (disque mince, bras) continuent au rythme
  d'aujourd'hui, dans le passé comme dans le futur [Supposition : la Voie lactée forme ~1 à 2 M☉ par an, et son gaz en
  a pour quelques Ga] ; c'est le régime recommandé tant que le film n'a pas de gaz.

Usage :
  python vieillissement_populations.py <dossier des fichiers MIST *.iso> <sortie.json>
  python vieillissement_populations.py --essai <sortie.json>      (contrôles sur une table déjà écrite)
"""
import glob
import json
import math
import os
import re
import sys

import numpy as np

H, C, KB = 6.62607015e-34, 2.99792458e8, 1.380649e-23
LAMBDA_B, LAMBDA_V = 440e-9, 550e-9
LOG_AGES = np.round(np.arange(5.0, 10.30001, 0.05), 2)     # grille d'âge de MIST (log10 âge / an)
T_FILM = np.round(np.arange(-3.0, 10.0001, 0.05), 3)        # dates du film, Ga (−3 à +10, comme le plan B+)

# Histoires de formation par composante du traceur (docs/contrat-etoiles-visibles.md : comp).
# âges en Ga AUJOURD'HUI ; 'forme' : 'uniforme' (rythme constant entre a0 et a1) ou 'sursaut' (tout à a0).
COMPOSANTES = {
    1: dict(nom='disque mince', forme='uniforme', a0=0.0, a1=10.0, feh=0.0, forme_aujourdhui=True,
            src='rythme de formation à peu près constant depuis ~10 Ga, composition solaire en moyenne [Supposition ; '
                'ordre de grandeur de Bland-Hawthorn et Gerhard 2016, Probable]'),
    2: dict(nom='bulbe et barre', forme='sursaut', a0=10.0, feh=0.0, forme_aujourdhui=False,
            src='étoiles surtout vieilles (~10 Ga), métallicité moyenne proche du Soleil [Supposition ; Probable en ordre de grandeur]'),
    4: dict(nom='disque épais', forme='uniforme', a0=9.0, a1=12.0, feh=-0.5, forme_aujourdhui=False,
            src='9 à 12 Ga, [Fe/H] ≈ −0,5 [Supposition ; Probable en ordre de grandeur]'),
    5: dict(nom='étoiles jeunes des bras et régions HII', forme='uniforme', a0=0.0, a1=0.1, feh=0.0, forme_aujourdhui=True, fenetre_jeune=True,
            src='nées dans les 100 derniers Ma [Supposition]'),
    6: dict(nom="halo d'étoiles", forme='sursaut', a0=12.0, feh=-1.5, forme_aujourdhui=False,
            src='~12 Ga, [Fe/H] ≈ −1,5 [Supposition ; Probable en ordre de grandeur]'),
}


def kroupa(m):
    m = np.asarray(m, float)
    return np.where(m < 0.5, (m / 0.5) ** -1.3, (m / 0.5) ** -2.3)


def _norme_kroupa():
    m = np.geomspace(0.1, 100, 20001)
    return 1.0 / np.trapezoid(kroupa(m) * m, m)      # par masse solaire formée (0,1 à 100 M☉)


def lire_iso(chemin):
    """Fichier MIST « basic » : blocs d'isochrones ; rend {log âge arrondi : (masse initiale, log L, log Teff)} et [Fe/H]."""
    blocs, cols, cur = {}, None, None
    feh = None
    with open(chemin) as fh:
        for ligne in fh:
            if ligne.startswith('#'):
                mots = ligne[1:].split()
                if 'EEP' in mots and 'log_L' in mots:
                    cols = mots
                if '[Fe/H]' in mots and feh is None and len(mots) >= 5 and mots[0].startswith('Yinit'):
                    pass
                continue
            v = ligne.split()
            if not v or cols is None:
                continue
            la = round(float(v[cols.index('log10_isochrone_age_yr')]), 2)
            blocs.setdefault(la, []).append((float(v[cols.index('initial_mass')]), float(v[cols.index('log_L')]),
                                             float(v[cols.index('log_Teff')])))
            if feh is None and '[Fe/H]_init' in cols:
                feh = float(v[cols.index('[Fe/H]_init')])
    if feh is None:
        m = re.search(r'feh_([mp])(\d+\.\d+)', os.path.basename(chemin))
        feh = (-1 if m.group(1) == 'm' else 1) * float(m.group(2))
    return {k: np.array(b) for k, b in blocs.items()}, feh


def planck(lam, T):
    x = H * C / (lam * KB * T)
    return 1.0 / (lam ** 5 * np.expm1(np.minimum(x, 700)))


def t_couleur(rapport):
    """Température du corps noir dont B(440)/B(550) vaut `rapport` (dichotomie)."""
    lo, hi = 1000.0, 200000.0
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        if planck(LAMBDA_B, mid) / planck(LAMBDA_V, mid) < rapport:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def population_simple(iso, norme):
    """iso : (N, 3) masse initiale, log L, log Teff, triés par masse. Rend L (L☉ par M☉ formée), fB, fV (unités relatives)."""
    o = np.argsort(iso[:, 0])
    m, logL, logT = iso[o, 0], iso[o, 1], iso[o, 2]
    m, idx = np.unique(m, return_index=True)
    logL, logT = logL[idx], logT[idx]
    bords = np.concatenate([[max(0.1, m[0] - (m[1] - m[0]) / 2)], (m[1:] + m[:-1]) / 2, [m[-1] + (m[-1] - m[-2]) / 2]])
    dn = np.array([np.trapezoid(kroupa(np.linspace(a, b, 9)), np.linspace(a, b, 9)) for a, b in zip(bords[:-1], bords[1:])]) * norme
    L, T = 10 ** logL, 10 ** logT
    R2 = L / T ** 4
    fB = np.sum(dn * R2 * planck(LAMBDA_B, T))
    fV = np.sum(dn * R2 * planck(LAMBDA_V, T))
    return float(np.sum(dn * L)), float(fB), float(fV)


def construire(dossier):
    fichiers = sorted(glob.glob(os.path.join(dossier, '*.iso')))
    if not fichiers:
        raise SystemExit(f'aucun fichier .iso dans {dossier}')
    norme = _norme_kroupa()
    grille = {}
    for f in fichiers:
        blocs, feh = lire_iso(f)
        L, fB, fV = [], [], []
        for la in LOG_AGES:
            b = blocs.get(round(float(la), 2))
            if b is None or len(b) < 3:
                L.append(float('nan')); fB.append(float('nan')); fV.append(float('nan')); continue
            l, b_, v = population_simple(b, norme)
            L.append(l); fB.append(b_); fV.append(v)
        grille[feh] = dict(L=L, fB=fB, fV=fV)
        print(f'[Fe/H] = {feh:+.2f} : {sum(np.isfinite(L))} âges', flush=True)
    fehs = sorted(grille)
    simple = dict(feh=fehs, log_age=LOG_AGES.tolist(),
                  L=[grille[f]['L'] for f in fehs], fB=[grille[f]['fB'] for f in fehs], fV=[grille[f]['fV'] for f in fehs])
    out = dict(
        version=1,
        description='Vieillissement de la lumière des populations d’étoiles (traceurs) : facteurs à appliquer à la lumière '
                    'et à la température MESURÉES aujourd’hui. Généré par pipeline/etoiles/vieillissement_populations.py.',
        sources='isochrones MIST v1.2, v/vcrit 0,4 (Choi et al. 2016 ; Dotter 2016) ; fonction de masse de Kroupa 2001 ; '
                'naines blanches non comptées ; couleur par somme de corps noirs (440 et 550 nm)',
        statut='calculé ici à partir de modèles publiés ; histoires de formation par composante : supposées',
        population_simple=simple,
        t_ga=T_FILM.tolist(),
        composantes={},
    )
    for comp, d in COMPOSANTES.items():
        bloc = dict(nom=d['nom'], feh=d['feh'], src=d['src'], statut='supposé (histoire de formation) ; calculé (évolution)')
        for regime in ('sans_naissance', 'naissance_continue'):
            fl, ft = facteurs(simple, d, regime)
            bloc[regime] = dict(lum=[round(x, 6) for x in fl], teff=[round(x, 6) for x in ft])
        out['composantes'][str(comp)] = bloc
    return out


# ------------------------------------------------------------------ calculs sur la table (aussi pour l'appli, même formule)
def _interp_pop(simple, feh, age_ans):
    """L, fB, fV d'une population simple d'âge donné (ans) : linéaire en log âge et en [Fe/H] ; hors grille : bord
    (avant 10⁵ ans, la population est prise à 10⁵ ans)."""
    fehs = np.array(simple['feh']); la = np.array(simple['log_age'])
    x = np.clip(np.log10(np.maximum(age_ans, 1.0)), la[0], la[-1])
    j = int(np.clip(np.searchsorted(fehs, feh) - 1, 0, len(fehs) - 2))
    wf = float(np.clip((feh - fehs[j]) / (fehs[j + 1] - fehs[j]), 0, 1))
    res = []
    for cle in ('L', 'fB', 'fV'):
        g = np.array(simple[cle])
        a = np.interp(x, la, np.where(np.isfinite(g[j]), g[j], np.nan))
        b = np.interp(x, la, np.where(np.isfinite(g[j + 1]), g[j + 1], np.nan))
        res.append((1 - wf) * a + wf * b)
    return res


def lumiere_composee(simple, d, t_ga, regime, n=400):
    """Lumière (L, fB, fV) à la date t (Ga, 0 = aujourd'hui) des étoiles de la composante d.

    sans_naissance : les étoiles d'aujourd'hui, vieillies de t (celles qui ne sont pas encore nées à t < 0 sont ôtées).
    naissance_continue (composantes qui forment des étoiles aujourd'hui) : même rythme de naissance à toute date ;
    - fenêtre jeune (bras) : à toute date, des âges de 0 à a1 (les étoiles meurent et sont remplacées) ;
    - disque : des âges de 0 à a1 + t (la formation a commencé il y a a1 ; à t < 0 le disque est plus jeune)."""
    continu = regime == 'naissance_continue' and d['forme_aujourdhui']
    if d['forme'] == 'sursaut':
        ages = np.array([d['a0'] + t_ga]); w = np.array([1.0])
    elif continu:
        haut = d['a1'] if d.get('fenetre_jeune') else d['a1'] + t_ga
        haut = max(haut, 1e-4)
        ages = (np.arange(n) + 0.5) / n * haut; w = np.full(n, haut / n)       # poids : durée (rythme constant)
    else:
        ages = d['a0'] + (np.arange(n) + 0.5) / n * (d['a1'] - d['a0']) + t_ga; w = np.full(n, (d['a1'] - d['a0']) / n)
    w = np.where(ages > 0, w, 0.0)
    L = fB = fV = 0.0
    for a, wk in zip(ages, w):
        if wk == 0:
            continue
        l, b, v = _interp_pop(simple, d['feh'], a * 1e9)
        L += wk * l; fB += wk * b; fV += wk * v
    return float(L), float(fB), float(fV)


def facteurs(simple, d, regime):
    L0, B0, V0 = lumiere_composee(simple, d, 0.0, regime)
    T0 = t_couleur(B0 / V0)
    fl, ft = [], []
    for t in T_FILM:
        L, B, V = lumiere_composee(simple, d, float(t), regime)
        fl.append(L / L0)
        ft.append((t_couleur(B / V) if V > 0 else 0.0) / T0)      # 0 : plus aucune étoile (pas encore née)
    return fl, ft


def essai(chemin):
    """Contrôles d'ordre de grandeur contre des valeurs publiées [Probable : valeurs classiques, non relues ce jour]."""
    t = json.load(open(chemin, encoding='utf-8'))
    s = t['population_simple']
    ok = True
    j = s['feh'].index(0.0)
    la = np.array(s['log_age']); L = np.array(s['L'][j])
    i1, i10 = int(np.argmin(abs(la - 9.0))), int(np.argmin(abs(la - 10.0)))
    pente = (math.log10(L[i10]) - math.log10(L[i1])) / (la[i10] - la[i1])
    print(f'population simple solaire : L(1 Ga) = {L[i1]:.3g}, L(10 Ga) = {L[i10]:.3g} L☉/M☉ ; pente d log L / d log t = {pente:.2f} '
          '(valeur classique d’environ −0,8, de mémoire [À vérifier] ; tolérance −0,7 à −1,1)')
    ok &= -1.1 < pente < -0.7
    ml = 1 / L[i10]
    print(f'rapport masse formée / lumière bolométrique à 10 Ga : {ml:.2f} (attendu : quelques unités, de mémoire [À vérifier] ; '
          'tolérance 0,5 à 5)')
    ok &= 0.5 < ml < 5
    for comp, b in t['composantes'].items():
        for reg in ('sans_naissance', 'naissance_continue'):
            fl = np.array(b[reg]['lum']); ft = np.array(b[reg]['teff']); tt = np.array(t['t_ga'])
            i0 = int(np.argmin(abs(tt)))
            ok &= abs(fl[i0] - 1) < 1e-9 and abs(ft[i0] - 1) < 1e-9
            sauts = np.max(np.abs(np.diff(np.log(np.maximum(fl, 1e-12)))))
            print(f'  {b["nom"]:38s} {reg:18s} lum ×{fl[-1]:.3f} à +10 Ga, ×{fl[0]:.3f} à −3 Ga ; teff ×{ft[-1]:.3f} à +10 Ga ; '
                  f'plus grand pas {sauts:.3f} (log, tous les 50 Ma)')
    print('PASSE' if ok else 'ECHEC')
    return 0 if ok else 1


if __name__ == '__main__':
    if sys.argv[1] == '--essai':
        sys.exit(essai(sys.argv[2]))
    table = construire(sys.argv[1])
    with open(sys.argv[2], 'w', encoding='utf-8') as fh:
        json.dump(table, fh, ensure_ascii=False, separators=(',', ':'))
    print('écrit', sys.argv[2], os.path.getsize(sys.argv[2]), 'octets')
    sys.exit(essai(sys.argv[2]))
