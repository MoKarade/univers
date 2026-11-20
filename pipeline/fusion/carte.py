#!/usr/bin/env python3
"""La carte graphique est-elle prise par Marc ? (jeu, ou son appli Univers)

Le taux d'occupation ne suffit pas : le bureau seul (vidéo, outils) fait varier la carte entre 20 et 40 % sans que Marc
joue (mesuré le 19/11/2026 : l'essai du groupe a attendu deux heures pour rien). On regarde donc QUI utilise la carte :
un programme d'un dossier de jeux (steamapps), Call of Duty, ou l'appli Univers ; et, en secours, une mémoire graphique
prise par les autres programmes au-delà de MEMOIRE_AUTRES_MO.
"""
import subprocess

# L'appli de Marc est UniversPC.exe (raccourci du Bureau, sans console). univers.exe (avec console) sert aux essais en fenêtre
# cachée des autres fils : il ne compte PAS comme « Marc utilise la carte », sinon ces essais affament le calcul (constaté le
# 20/11 : six tirs d'orbites refusés d'affilée).
JEUX = (r'steamapps\common', 'cod.exe', 'universpc.exe', 'epic games', 'riot games', 'battle.net')
MEMOIRE_AUTRES_MO = 7000


def _smi(args):
    return subprocess.run(['nvidia-smi'] + args, capture_output=True, text=True, timeout=20,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout


def prise(memoire_a_moi_mo=0.0):
    """Rend la raison (texte) si Marc utilise la carte, sinon None. memoire_a_moi_mo : mémoire graphique de ce calcul."""
    try:
        noms = _smi(['--query-compute-apps=name', '--format=csv,noheader']).lower()
        for j in JEUX:
            if j in noms: return f'programme de Marc sur la carte ({j})'
        utilisee = float(_smi(['--query-gpu=memory.used', '--format=csv,noheader,nounits']).split()[0])
        if utilisee - memoire_a_moi_mo > MEMOIRE_AUTRES_MO: return f'{utilisee - memoire_a_moi_mo:.0f} Mo de mémoire graphique pris par d\'autres programmes'
    except Exception:
        return None
    return None


if __name__ == '__main__':
    r = prise()
    print(r or 'libre')
    raise SystemExit(1 if r else 0)
