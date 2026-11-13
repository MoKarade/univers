"""Contrôles de l'évolution des étoiles contre des mesures indépendantes (lancé sur le PC, a besoin de mist_traces.bin).

Usage : python test_vie_etoiles.py <mist_traces.bin>
Chaque contrôle imprime PASSE ou ÉCHEC avec les chiffres.
"""
import sys

import numpy as np

import mist_lecture as ml

ECHECS = []


def controle(nom: str, ok: bool, detail: str) -> None:
    print(f'{"PASSE" if ok else "ÉCHEC"}  {nom} : {detail}')
    if not ok:
        ECHECS.append(nom)


def soleil(T: ml.Traces) -> None:
    """Soleil (1 masse solaire, 4,57 Ga) : M_G = 4,67 et BP-RP = 0,82 (Casagrande & VandenBerg 2018, MNRAS 479, L102)."""
    tr = T.trace(np.array([1.0]))
    e = T.eep_a_age(tr, np.array([4.57e9]))
    G, C = T.valeur('G', tr, e)[0], T.valeur('C', tr, e)[0]
    # Le modèle seul n'est pas le Soleil mesuré : c'est pourquoi l'appli n'ajoute que des DIFFÉRENCES du modèle à
    # l'éclat mesuré. On vérifie ici seulement que l'écart reste celui, connu, d'un modèle publié (< 0,2 mag).
    controle('Soleil : modèle seul contre mesure', abs(G - 4.67) < 0.2 and abs(C - 0.82) < 0.1,
             f'M_G {G:.3f} (mesuré 4,67), BP-RP {C:.3f} (mesuré 0,82)')
    for age in (0.1e9, 1e9, 4.57e9, 7e9, 9e9, 10e9, 11e9, 12e9):
        e = T.eep_a_age(tr, np.array([age]))
        print(f'       {age / 1e9:5.2f} Ga : point {e[0]:7.1f}, G {T.valeur("G", tr, e)[0]:6.2f}, BP-RP '
              f'{T.valeur("C", tr, e)[0]:5.2f}, log L {T.valeur("logL", tr, e)[0]:5.2f}, phase {T.phase[tr[0], int(e[0])]}')
    fin = T.champ('age')[tr[0], T.utiles[tr[0]] - 1]
    controle('Fin du Soleil (vers naine blanche)', 11e9 < fin < 13e9, f'{fin / 1e9:.2f} Ga')


def fenetres(T: ml.Traces) -> None:
    """La fenêtre calme contient bien son point, et l'éclat n'y bouge pas de plus de 0,01 mag."""
    pire = 0.0
    rng = np.random.default_rng(1)
    for k in rng.integers(0, T.n, 200):
        n = T.utiles[k]
        a, G = T.champ('age')[k, :n], T.champ('G')[k, :n]
        lo, hi = T.champ('calme_lo')[k, :n], T.champ('calme_hi')[k, :n]
        for j in rng.integers(0, n, 20):
            if not lo[j] < hi[j]:
                continue      # fenêtre vide (phase plus rapide que la précision des âges) : l'appli recalcule toujours
            s = (a >= lo[j]) & (a <= hi[j])
            pire = max(pire, float(np.abs(G[s] - G[j]).max()))
    controle('Fenêtres calmes', pire < 0.0100001, f'écart maximal {pire:.4f} mag')


def lire_vie(chemin: str) -> np.ndarray:
    b = np.fromfile(chemin, np.uint8)
    if bytes(b[:8]) != b'UNIVVIE1':
        raise ValueError(chemin)
    return b[16:].view(np.dtype([('tr', '<u2'), ('eep', '<u2'), ('f', 'u1'), ('lo', 'u1'), ('hi', 'u1'), ('r', 'u1')]))


def nommees(T: ml.Traces, vie: str, noms: str) -> None:
    """Étoiles nommées : masse, âge, temps restant, contre les valeurs publiées pour quelques-unes."""
    import json
    v = lire_vie(vie)
    publie = {   # masse (M☉), temps avant la fin (années) : fourchettes publiées
        'Bételgeuse': ((11.6, 24.0), (1e4, 3e5), 'Neilson et al. 2011 : 11,6 M☉ ; Dolan et al. 2016 : 17-24 M☉ ; Joyce et al. 2020 : fin dans ~100 000 ans'),
        'Antarès': ((11.0, 17.0), (1e4, 2e6), 'Ohnaka et al. 2013 ; 11-17 M☉ selon les études'),
        'Sirius': ((1.9, 2.2), (2e8, 1.5e9), 'Bond et al. 2017 : 2,06 M☉, ~240 Ma'),
        'Véga': ((2.0, 2.3), (2e8, 1.2e9), 'Yoon et al. 2010 : 2,1 M☉, ~455 Ma'),
    }
    for e in json.load(open(noms, encoding='utf-8'))['nommees']:
        r = v[e['i']]
        if r['f'] == 0:
            print(f'       {e["n"]:<34} inconnu')
            continue
        tr, eep = np.array([int(r['tr'])]), np.array([r['eep'] / 32.0])
        m = T.masses[tr[0]]
        age = T.valeur('age', tr, eep)[0]
        reste = T.champ('age')[tr[0], T.utiles[tr[0]] - 1] - age
        ligne = f'{e["n"]:<34} {m:7.2f} M☉, âge {age / 1e6:10.2f} Ma, fin dans {reste / 1e6:10.3f} Ma, phase {T.phase[tr[0], int(eep[0])]}'
        if e['n'] in publie:
            (m0, m1), (r0, r1), src = publie[e['n']]
            controle(e['n'], m0 * 0.8 <= m <= m1 * 1.2 and r0 <= reste <= r1, f'{ligne} ({src})')
        else:
            print('       ' + ligne)


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    T = ml.Traces(sys.argv[1])
    soleil(T)
    fenetres(T)
    if len(sys.argv) > 3:
        nommees(T, sys.argv[2], sys.argv[3])
    sys.exit(1 if ECHECS else 0)


if __name__ == '__main__':
    main()
