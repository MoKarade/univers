#!/usr/bin/env python3
"""Trajectoire du Soleil sur la branche des géantes rouges (R5), écrite dans app/gen/sun_rgb.js.

Problème : dans SUN_TRACK, les points entre la fin de la séquence principale (âge 10,00) et le sommet des géantes
rouges (12,167) n'étaient pas publiés ; intégrés avec la perte de masse de Schröder et Smith 2008, ils donnaient
une masse négative. On les remplace par :
- la FORME de la montée, prise sur le modèle MIST v1.2 d'une étoile de 1 masse solaire, [Fe/H] = 0, sans rotation
  (Choi et al. 2016, ApJ 823, 102 ; Dotter 2016, ApJS 222, 8 ; fichier pipeline/raw/mist_v1.2_feh0_00100M.track.eep) :
  le temps qui reste avant le sommet est gardé tel quel (la fin de la montée dépend de la croissance du cœur, pas de
  l'enveloppe) ;
- les POINTS D'ANCRAGE publiés de Schröder et Smith 2008 (table 1) : sommet à l'âge 12,167, 2 730 L☉, 256 R☉.
  L et R du modèle MIST sont corrigés en douceur (en log, proportionnellement à la montée de log L) pour tomber sur
  ces valeurs au sommet ;
- la MASSE, intégrée avec leur éq. 1 (η = 8×10⁻¹⁴ M☉/an) le long de cette trajectoire. La correction du rayon suit w^k,
  k étant ajusté pour retrouver la masse publiée au sommet (0,668 M☉) : c'est un calage sur le résultat publié, dit tel quel.
Sortie : âge (Ga), L, T, R, M, aux pas du modèle MIST. Le script affiche la masse obtenue au sommet, à comparer
aux 0,668 M☉ publiés.
"""
import os, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'raw', 'mist_v1.2_feh0_00100M.track.eep')
DST = os.path.join(HERE, '..', 'app', 'gen', 'sun_rgb.js')
TIP_AGE, TIP_L, TIP_R = 12.167, 2730.0, 256.0          # Schröder et Smith 2008, table 1
ETA = 8e-14                                           # leur éq. 1, M☉/an
G_SUN = 27400.0                                       # gravité de surface du Soleil, cgs


def track(rows, ix, k):
    tams, tip = rows[454 - 1], rows[605 - 1]                 # points de phase primaires (EEP) 454 et 605
    t_tip = tip[ix['star_age']] / 1e9
    lL0, lL1 = tams[ix['log_L']], tip[ix['log_L']]
    dL, dR = math.log10(TIP_L) - lL1, math.log10(TIP_R) - tip[ix['log_R']]
    out, M, prev = [], 1.0, None
    for r in rows[454 - 1:605]:
        age = TIP_AGE - (t_tip - r[ix['star_age']] / 1e9)
        w = (r[ix['log_L']] - lL0) / (lL1 - lL0)
        L = 10 ** (r[ix['log_L']] + w * dL); R = 10 ** (r[ix['log_R']] + (w ** k) * dR)
        T = 5772.0 * (L / (R * R)) ** 0.25
        if prev is not None:      # perte de masse, éq. 1, au milieu du pas
            dt = (age - prev[0]) * 1e9
            Lm, Rm, Tm = (L + prev[1]) / 2, (R + prev[3]) / 2, (T + prev[2]) / 2
            g = G_SUN * M / (Rm * Rm)
            M -= ETA * Lm * Rm / M * (Tm / 4000.0) ** 3.5 * (1 + G_SUN / (4300.0 * g)) * dt
        prev = (age, L, T, R)
        out.append([round(age, 7), float('%.5g' % L), round(T), float('%.5g' % R), round(M, 5)])
    return out


def main():
    lines = open(SRC).read().split('\n')
    cols = [l for l in lines if l.startswith('#')][-1][1:].split()
    ix = {c: i for i, c in enumerate(cols)}
    rows = [list(map(float, l.split())) for l in lines if l.strip() and not l.startswith('#')]
    # Le rayon publié au sommet (256 R☉) est plus grand que celui de MIST (173 R☉). La correction du rayon monte comme w^k
    # (w : part de la montée en log L déjà faite) ; k est choisi pour que la masse au sommet retombe sur les 0,668 M☉ publiés.
    lo, hi = 0.0, 60.0
    for _ in range(60):
        k = (lo + hi) / 2
        if track(rows, ix, k)[-1][4] < 0.668: lo = k
        else: hi = k
    out = track(rows, ix, k)
    print('k =', round(k, 3))
    # garder un point sur deux loin du sommet pour alléger
    print('points', len(out), '| âge de départ', out[0][0], '| masse au sommet', out[-1][4], '(publié : 0,668)')
    js = '/* généré par pipeline/build_sun_rgb.py : âge (Ga), L (L☉), T (K), R (R☉), M (M☉) */\nObject.assign(DATA, ' + json.dumps({'SUN_RGB': out}, separators=(',', ':')) + ');\n'
    open(DST, 'w', encoding='utf-8', newline='\n').write(js)


if __name__ == '__main__':
    main()
