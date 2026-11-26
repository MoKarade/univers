#!/usr/bin/env python3
"""Durées de vie des étoiles d'après les modèles d'évolution MIST v1.2 ([Fe/H] = 0, sans rotation ; Choi et al. 2016,
Dotter 2016), pour toutes les masses de la grille (0,1 à 300 masses solaires).

Pour chaque masse : âge à la fin de la séquence principale (EEP 454), âge à la fin du modèle (dernier point), et destin :
naine blanche quand le modèle va jusqu'au refroidissement (EEP 1710), effondrement (supernova) quand il s'arrête à la fin de
la combustion du carbone (EEP 808) ; les étoiles de moins de 0,6 masse solaire n'ont pas fini leur séquence principale dans
l'âge de l'Univers : leur fin de modèle est un âge plafond, pas une mort.
Usage : python build_mist_life.py <dossier des fichiers .track.eep> <sortie.js>
"""
import glob, json, os, sys


def main(src, dst):
    rows = []
    for f in sorted(glob.glob(os.path.join(src, '*.track.eep'))):
        with open(f, encoding='utf-8') as fh:
            lines = fh.read().splitlines()
        hdr = next(l for l in lines if l.startswith('#') and 'star_age' in l).split()[1:]
        i_age, i_ph, i_L, i_T = hdr.index('star_age'), hdr.index('phase'), hdr.index('log_L'), hdr.index('log_Teff')
        m0 = float(lines[lines.index(next(l for l in lines if 'initial_mass' in l)) + 1].split()[1])
        data = [l.split() for l in lines if l.strip() and not l.startswith('#')]
        age = lambda k: float(data[k - 1][i_age])
        n = len(data)
        t_ms = age(454) if n >= 454 else None
        t_end = float(data[-1][i_age]); ph_end = float(data[-1][i_ph])
        fate = 'wd' if n >= 1710 else ('cc' if n >= 808 and m0 >= 7 else 'ms' if n < 454 else 'open')
        rows.append([m0, t_ms / 1e6 if t_ms else None, t_end / 1e6, fate, n])
        print(f'{m0:7.2f} M☉ : séquence principale {t_ms and t_ms / 1e9:.4g} Ga, fin du modèle {t_end / 1e9:.4g} Ga, destin {fate} ({n} points)' if t_ms else f'{m0:7.2f} M☉ : séquence principale non finie ({t_end / 1e9:.3g} Ga), {n} points')
    out = {'src': 'MIST v1.2, [Fe/H] = 0, v/vcrit = 0 (Choi et al. 2016 ; Dotter 2016)', 'cols': ['masse', 'fin_seq_principale_Ma', 'fin_modele_Ma', 'destin', 'points'], 'rows': rows}
    with open(dst, 'w', encoding='utf-8', newline='\n') as out_f:
        out_f.write('Object.assign(DATA, { MIST_LIFE: ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ' });\n')
    print('écrit', dst, os.path.getsize(dst), 'octets')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
