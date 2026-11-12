#!/usr/bin/env python3
"""Remplace par un lien dur chaque fichier d'un dossier de travail identique (octet pour octet) à celui installé.

Pourquoi (Marc, 12/11/2026 : garder beaucoup de place libre sur le PC) : installer.ps1 COPIE les fichiers du dossier de
travail vers C:\\dev\\Univers-PC ; chaque donnée existait donc deux fois sur le disque. Un lien dur garde les deux noms
pour un seul contenu. Rien n'est effacé si le contenu diffère (comparaison complète par empreinte SHA-256).
Usage : python dedoublonner.py <dossier installé> <dossier de travail> [<dossier de travail> ...]
"""
import hashlib
import os
import sys


def empreinte(chemin: str) -> str:
    h = hashlib.sha256()
    with open(chemin, 'rb') as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    installe, travail = sys.argv[1], sys.argv[2:]
    index: dict[tuple[str, int], str] = {}
    for racine, _, fichiers in os.walk(installe):
        for n in fichiers:
            p = os.path.join(racine, n)
            index.setdefault((n, os.path.getsize(p)), p)
    gagne = 0
    for dossier in travail:
        for racine, _, fichiers in os.walk(dossier):
            for n in fichiers:
                p = os.path.join(racine, n)
                taille = os.path.getsize(p)
                cible = index.get((n, taille))
                if not cible or taille < 1 << 20 or os.path.samefile(p, cible):
                    continue
                if empreinte(p) != empreinte(cible):
                    continue
                tmp = p + '.lien'
                os.link(cible, tmp)
                os.replace(tmp, p)
                gagne += taille
                print(f'lien : {p} -> {cible} ({taille / 1e9:.2f} Go)', flush=True)
    print(f'place rendue : {gagne / 1e9:.2f} Go')


if __name__ == '__main__':
    main()
