#!/usr/bin/env python3
"""La carte graphique est-elle prise par Marc ? (jeu, ou son appli Univers)

Le taux d'occupation ne suffit pas : le bureau seul (vidéo, outils) fait varier la carte entre 20 et 40 % sans que Marc
joue (mesuré le 19/11/2026 : l'essai du groupe a attendu deux heures pour rien). On regarde donc QUI utilise la carte :
un programme d'un dossier de jeux (steamapps), Call of Duty, ou l'appli Univers ; et, en secours, une mémoire graphique
prise par les autres programmes au-delà de MEMOIRE_AUTRES_MO.
"""
import os
import subprocess

# L'appli de Marc est UniversPC.exe (raccourci du Bureau, sans console). univers.exe (avec console) sert aux essais en fenêtre
# cachée des autres fils : il ne compte PAS comme « Marc utilise la carte », sinon ces essais affament le calcul (constaté le
# 20/11 : six tirs d'orbites refusés d'affilée).
JEUX = (r'steamapps\common', 'cod.exe', 'universpc.exe', 'epic games', 'riot games', 'battle.net')
MEMOIRE_AUTRES_MO = 7000
PAUSE = 'C:/tmp/natif/pause_carte.txt'


def _smi(args):
    return subprocess.run(['nvidia-smi'] + args, capture_output=True, text=True, timeout=20,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout


def memoire_de(pid):
    """Mémoire graphique dédiée d'un processus (Mo), lue dans les compteurs de Windows. None si la lecture échoue.
    nvidia-smi ne donne pas ce chiffre par programme sous Windows, et la réserve de CuPy sous-estime la part du calcul
    (constaté le 20/11 : un tir de réglage se mettait en pause à cause de sa propre mémoire)."""
    try:
        cmd = (r"$s = (Get-Counter '\GPU Process Memory(pid_%d*)\Dedicated Usage' -ErrorAction Stop).CounterSamples; "
               "($s | Measure-Object CookedValue -Sum).Sum") % pid
        out = subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, text=True, timeout=30,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.strip().replace(',', '.')
        return float(out) / 2 ** 20
    except Exception:
        return None


def memoire_des_essais():
    """Mémoire graphique (Mo) des essais en fenêtre cachée des autres fils (univers.exe) : ce n'est pas Marc, elle ne doit
    pas mettre le calcul en pause (constaté le 20/11 : un essai de 10 Go bloquait les tirs d'orbites). 0 si illisible."""
    try:
        cmd = (r"$t = 0; (Get-Counter '\GPU Process Memory(*)\Dedicated Usage' -ErrorAction Stop).CounterSamples | ForEach-Object { "
               r"$p = [int]($_.InstanceName -replace 'pid_(\d+)_.*', '$1'); "
               r"if ((Get-Process -Id $p -ErrorAction SilentlyContinue).ProcessName -eq 'univers') { $t += $_.CookedValue } }; $t")
        out = subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, text=True, timeout=30,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.strip().replace(',', '.')
        return float(out) / 2 ** 20
    except Exception:
        return 0.0


def prise(memoire_a_moi_mo=0.0):
    """Rend la raison (texte) si Marc utilise la carte, sinon None. memoire_a_moi_mo : mémoire graphique de ce calcul."""
    if os.path.exists(PAUSE): return 'pause demandée (' + PAUSE + ')'      # créneau cédé à un autre fil : supprimer le fichier pour reprendre
    try:
        noms = _smi(['--query-compute-apps=name', '--format=csv,noheader']).lower()
        for j in JEUX:
            if j in noms: return f'programme de Marc sur la carte ({j})'
        # Un essai caché d'un autre fil (univers.exe, jusqu'à 10 Go) est sur la carte : la règle de mémoire ne dit plus rien de
        # Marc, on ne l'applique pas (20/11 : sept retraits d'affilée, le compteur Windows par programme répondait trop tard).
        if 'univers.exe' in noms: return None
        utilisee = float(_smi(['--query-gpu=memory.used', '--format=csv,noheader,nounits']).split()[0])
        exacte = memoire_de(os.getpid())
        if exacte is not None: memoire_a_moi_mo = max(memoire_a_moi_mo, exacte)
        if utilisee - memoire_a_moi_mo > MEMOIRE_AUTRES_MO: memoire_a_moi_mo += memoire_des_essais()
        if utilisee - memoire_a_moi_mo > MEMOIRE_AUTRES_MO: return f'{utilisee - memoire_a_moi_mo:.0f} Mo de mémoire graphique pris par d\'autres programmes'
    except Exception:
        return None
    return None


if __name__ == '__main__':
    r = prise()
    print(r or 'libre')
    raise SystemExit(1 if r else 0)
