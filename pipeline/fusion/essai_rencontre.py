#!/usr/bin/env python3
"""Essai A/B du pas de temps pendant une rencontre (26/11/2026).

Pourquoi : dans le film 10 M fini, l'énergie saute aux passages d'Andromède (+0,21 % -> +0,82 % au premier, jusqu'à +2,95 %
à la fusion des centres). Avant de finir le film 20 M, on vérifie que le pas réduit pendant les rencontres (rencontre.py,
--pas-rencontre-ma) et le plafond du gaz relevé (gaz_galaxie.SOUS_PAS_MAX) font disparaître ces sauts.

Méthode : on repart de la sauvegarde d'un film (reprise.npz), on garde une particule de masse sur 1/fraction (masse
multipliée d'autant, adoucissement multiplié par fraction^(-1/3), comme les tirs de réglage), sans les étoiles visibles,
et on calcule jusqu'à t_fin. Le fichier source n'est que lu ; tout est écrit dans <sortie>.

  python essai_rencontre.py <reprise.npz> <sortie> <t_fin, Ga> [--fraction=0.1] [--pas-ma=0.25] [--pas-rencontre-ma=0.0625]
                            [--rencontres=...] [--gaz=1] [--maree=<csv>] [--efficacite=0.0115] [--graine=20261126]

Sans --gaz ni --maree, l'énergie (énergie noire comprise) doit se conserver : tout écart est une erreur du calcul. Avec le gaz
et la marée, seule la DIFFÉRENCE entre deux variantes compte. Le plafond du gaz se règle par UNIVERS_SOUS_PAS_MAX.
Comparer : python essai_rencontre.py compare <sortie A> <sortie B> [...]."""
import json
import math
import os
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)


def sous_echantillon(chemin, fraction, graine):
    with np.load(chemin) as z:
        t0 = float(z['t']); kind = z['kind']
        lourd = np.where(kind != 9)[0]
        rng = np.random.default_rng(graine)
        garde = np.sort(rng.choice(lourd, size=int(len(lourd) * fraction), replace=False)) if fraction < 1 else lourd
        p = {k: z[k][garde] for k in ('pos', 'vel', 'm', 'eps', 'kind', 'gid', 'h_gaz', 'naissance', 'age0', 'u_gaz') if k in z.files}
    p['m'] = p['m'] / fraction; p['eps'] = p['eps'] * fraction ** (-1 / 3)
    return t0, p


def lancer(args, opts):
    import rencontre as R
    src, sortie, t_fin = args[0], args[1], float(args[2])
    os.makedirs(sortie, exist_ok=True)
    if 'efficacite' in opts:
        import gaz_galaxie
        gaz_galaxie.EFFICACITE = float(opts['efficacite'])
    import gaz_galaxie
    fraction = float(opts.get('fraction', 0.1))
    t0, p = sous_echantillon(src, fraction, int(opts.get('graine', 20261126)))
    reglages = dict(source=os.path.abspath(src), fraction=fraction, t0=t0, t_fin=t_fin, n=int(len(p['m'])), pas_ma=float(opts.get('pas-ma', 0.25)),
                    pas_rencontre_ma=opts.get('pas-rencontre-ma'), rencontres=opts.get('rencontres', R.RENCONTRES_DEFAUT if opts.get('pas-rencontre-ma') else None),
                    gaz=int(opts.get('gaz', 0)), maree=opts.get('maree'), sous_pas_max_gaz=gaz_galaxie.SOUS_PAS_MAX, commit=R.version_du_code())
    json.dump(reglages, open(os.path.join(sortie, 'reglages.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('essai :', reglages, flush=True)
    S = R.Calcul(p, theta=float(opts.get('theta', 0.7)), gaz=int(opts.get('gaz', 0)), maree=opts.get('maree'), t_ga=t0)
    debut = time.time()
    R.avancer(S, t0, t_fin, sortie, dt_ma=reglages['pas_ma'], releve_ma=2.0, instantane_ga=1e9, **R.options_rencontre(opts))
    print(f'essai fini en {time.time() - debut:.0f} s', flush=True)


def comparer(dossiers):
    """Énergie et distance d'Andromède, variante par variante, et le plus grand saut d'énergie sur 50 Ma."""
    res = {}
    for d in dossiers:
        j = json.load(open(os.path.join(d, 'journal.json'), encoding='utf-8'))
        r = json.load(open(os.path.join(d, 'reglages.json'), encoding='utf-8'))
        t = np.array(j['t']); e = 100 * np.array(j['energie'])
        dm31 = np.array([math.dist(c[1], c[0]) for c in j['centres']])
        pas = 25      # 50 Ma
        saut = max((e[i + pas] - e[i] for i in range(len(e) - pas)), key=abs) if len(e) > pas else float('nan')
        res[d] = dict(t=t, e=e, d=dm31)
        print(f"{os.path.basename(d.rstrip('/'))}: gaz={r['gaz']} marée={'oui' if r['maree'] else 'non'} pas={r['pas_ma']} rencontre={r['pas_rencontre_ma']} "
              f"plafond gaz={r['sous_pas_max_gaz']} | énergie finale {e[-1]:+.3f} % | plus grand saut sur 50 Ma {saut:+.3f} % | "
              f"Andromède au plus près {dm31.min():.1f} kpc à {t[dm31.argmin()]:+.3f} Ga")
    print('\ndate      ' + ' '.join(f'{os.path.basename(d.rstrip("/"))[:22]:>24}' for d in dossiers))
    t_ref = res[dossiers[0]]['t']
    for T in t_ref[::25]:
        ligne = []
        for d in dossiers:
            i = int(np.argmin(abs(res[d]['t'] - T)))
            ligne.append(f"E {res[d]['e'][i]:+.3f} % d {res[d]['d'][i]:6.1f}")
        print(f'{T:+.3f}  ' + ' '.join(f'{x:>24}' for x in ligne))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    if args and args[0] == 'compare':
        comparer(args[1:])
    else:
        lancer(args, opts)
