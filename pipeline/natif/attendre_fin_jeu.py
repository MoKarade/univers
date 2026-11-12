#!/usr/bin/env python3
"""Pendant que Marc joue : toutes les 30 min, regarde s'il joue encore (application en plein écran au premier plan, ou carte
graphique occupée alors que nos calculs sont suspendus). Dès qu'il a fini, reprend les calculs (pause_calculs.py reprise)
et s'arrête. Aucune fenêtre n'est ouverte.
Usage : python attendre_fin_jeu.py [minutes entre deux regards, 30 par défaut]
"""
import os, subprocess, sys, time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'fusion'))
SANS_FENETRE = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def occupation_carte(secondes=60):
    vals = []
    for _ in range(secondes // 5):
        try:
            out = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'], capture_output=True, text=True,
                                 timeout=20, creationflags=SANS_FENETRE).stdout
            vals.append(int(out.split()[0]))
        except Exception:
            pass
        time.sleep(5)
    return sum(vals) / len(vals) if vals else 0.0


def main():
    minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 30
    from calcul import plein_ecran
    while True:
        time.sleep(minutes * 60)
        occ, pe = occupation_carte(), plein_ecran()
        print(time.strftime('%H:%M'), f'carte occupée {occ:.0f} %, plein écran {pe}', flush=True)
        if occ < 15 and not pe:
            subprocess.run([sys.executable, '-I', os.path.join(ICI, 'pause_calculs.py'), 'reprise'], creationflags=SANS_FENETRE)
            print(time.strftime('%H:%M'), 'Marc ne joue plus : calculs repris', flush=True)
            return


if __name__ == '__main__':
    main()
