#!/usr/bin/env python3
"""Envoie au Drive de Marc (Drive pour ordinateur, lecteur G:) les fichiers finis d'un dossier de travail, puis les
efface du PC. Règle de Marc (12/11/2026) : le maximum sur le Drive, peu de place prise sur le PC.

Un fichier est « fini » quand il a l'extension voulue (les fichiers en cours portent un autre nom : .part, en_cours_).
Copie, contrôle de la taille, puis effacement local. S'arrête quand le fichier témoin (ex. le journal du téléchargement
contenant « FIN ») est là et qu'il ne reste plus rien à envoyer.
Usage : python vers_drive.py <dossier local> <dossier Drive> <extension> <journal à surveiller>
"""
import os
import shutil
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')


def main() -> None:
    local, drive, ext, journal = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    os.makedirs(drive, exist_ok=True)
    envoye = 0
    while True:
        fichiers = sorted(e.path for e in os.scandir(local) if e.is_file() and e.name.endswith(ext) and not e.name.startswith('en_cours_'))
        for p in fichiers:
            dst = os.path.join(drive, os.path.basename(p))
            taille = os.path.getsize(p)
            shutil.copyfile(p, dst + '.part')
            if os.path.getsize(dst + '.part') != taille:
                raise SystemExit(f'{p} : taille différente après copie')
            os.replace(dst + '.part', dst)
            os.remove(p)
            envoye += taille
            print(f'{os.path.basename(p)} envoyé ({envoye / 1e9:.1f} Go en tout)', flush=True)
        fini = os.path.exists(journal) and 'FIN' in open(journal, encoding='utf-8', errors='replace').read()[-2000:]
        if fini and not fichiers:
            print('FIN', flush=True)
            return
        time.sleep(30)


if __name__ == '__main__':
    main()
