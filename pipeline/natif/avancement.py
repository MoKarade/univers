#!/usr/bin/env python3
"""Avancement des calculs de fond du fil physique, pour le panneau de l'appli PC (format fixé par le fil appli PC).

Dossier C:\\dev\\Univers-PC\\avancement\\ : un fichier NOM.txt (UTF-8) par tâche, écrit dans NOM.tmp puis renommé, toutes les
20 s. Lignes : nom=, fait=, total=, unite=, debut=, maj= (heure locale du PC, ISO, sans fuseau), etat= (en cours, en pause,
terminé, échec), detail=. Les valeurs sont LUES dans les journaux des calculs (aucune estimation).
Usage : python avancement.py   (s'arrête seul quand toutes les tâches sont terminées ou en échec)
"""
import datetime as dt, glob, os, re, sys, time

DOSSIER = r'C:\dev\Univers-PC\avancement'
NATIF = r'C:\tmp\natif'


def iso(t): return datetime_local(t).strftime('%Y-%m-%dT%H:%M:%S')
def datetime_local(t): return dt.datetime.fromtimestamp(t)


def ecrire(fichier, **v):
    os.makedirs(DOSSIER, exist_ok=True)
    txt = ''.join(f'{k}={v[k]}\n' for k in ('nom', 'fait', 'total', 'unite', 'debut', 'maj', 'etat', 'detail'))
    tmp = os.path.join(DOSSIER, fichier + ".tmp")
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f: f.write(txt)
    os.replace(tmp, os.path.join(DOSSIER, fichier + ".txt"))


def actif(chemin, secondes=600):
    return os.path.exists(chemin) and time.time() - os.path.getmtime(chemin) < secondes


def telechargement():
    j = os.path.join(NATIF, 'gaia_erreurs', 'journal.txt')
    lignes = open(j, encoding='utf-8', errors='replace').read().splitlines() if os.path.exists(j) else []
    parts = len(glob.glob(os.path.join(NATIF, 'gaia_erreurs', 'part_*.fits')))
    go = 0.0
    for l in reversed(lignes):
        m = re.search(r'cumul ([\d.]+) Go', l)
        if m: go = float(m.group(1)); break
    echec = any('en échec' in l for l in lignes)
    etat = 'terminé' if parts >= 1024 else 'échec' if echec else 'en cours' if actif(j) else 'en pause'
    ecrire('gaia_erreurs', nom='Téléchargement des marges d’erreur Gaia', fait=parts, total=1024, unite='morceaux de ciel',
           debut=iso(os.path.getctime(j)) if os.path.exists(j) else '', maj=iso(time.time()), etat=etat,
           detail=f'{go:.2f} Go reçus de l’archive Gaia (ESA)')
    return etat


def horizon():
    d = os.path.join(NATIF, 'horizon'); j = os.path.join(d, 'journal.txt')
    n = len(glob.glob(os.path.join(d, 'horizon_*.npz')))
    lignes = open(j, encoding='utf-8', errors='replace').read().splitlines() if os.path.exists(j) else []
    echec = any(l.startswith('part ') and ' : ' in l and 'étoiles' not in l for l in lignes) or any('Traceback' in l for l in lignes)
    etoiles = sum(int(m.group(1)) for l in lignes for m in [re.match(r'part \d+ : (\d+) étoiles', l)] if m)
    etat = 'terminé' if n >= 1024 else 'échec' if echec else 'en cours' if actif(j, 900) else 'en pause'
    ecrire('gaia_horizon', nom='Horizon réel de chaque étoile Gaia (32 clones, carte graphique)', fait=n, total=1024, unite='morceaux de ciel',
           debut=iso(os.path.getctime(j)) if os.path.exists(j) else '', maj=iso(time.time()), etat=etat,
           detail=f'{etoiles:,} étoiles calculées'.replace(',', ' '))
    return etat


def chaos():
    j = os.path.join(NATIF, 'chaos_futur.log')
    lignes = open(j, encoding='utf-8', errors='replace').read().splitlines() if os.path.exists(j) else []
    ma = 0.0
    for l in reversed(lignes):
        m = re.match(r'([\d.]+) Ma', l)
        if m: ma = float(m.group(1)); break
    fini = any(l.startswith('fini') for l in lignes)
    etat = 'terminé' if fini else 'en cours' if actif(j, 900) else 'en pause'
    ecrire('chaos_systeme_solaire', nom='Chaos du système solaire (32 copies écartées de 15 m)', fait=60 if fini else ma, total=60,
           unite='millions d’années', debut=iso(os.path.getctime(j)) if os.path.exists(j) else '', maj=iso(time.time()), etat=etat,
           detail='Jusqu’où la Terre reste prévisible dans le futur')
    return etat


def convertir_fusion(d):
    """Dès que le calcul a écrit un nouveau paquet d'images (fusion.json plus récent), refait les fichiers que l'appli lit."""
    import subprocess
    js, cb = os.path.join(d, 'fusion.json'), os.path.join(d, 'fusion_centres.bin')
    if not os.path.exists(js) or (os.path.exists(cb) and os.path.getmtime(cb) >= os.path.getmtime(js)): return
    ici = os.path.dirname(os.path.abspath(__file__))
    for args in ([os.path.join(ici, 'fusion_bin.py'), d, cb + '.tmp'], [os.path.join(ici, 'fusion_particules.py'), d]):
        subprocess.run([sys.executable, '-I'] + args, capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if os.path.exists(cb + '.tmp'): os.replace(cb + '.tmp', cb)


def calcul_particules(dossier, fichier, nom, total, detail):
    j = os.path.join(NATIF, dossier, 'journal.txt')
    if not os.path.exists(j): return 'terminé'
    convertir_fusion(os.path.join(NATIF, dossier))
    lignes = open(j, encoding='utf-8', errors='replace').read().splitlines()
    t = 0.0
    for l in reversed(lignes):
        m = re.search(r't =\s*([\d.]+) Ga', l)
        if m: t = float(m.group(1)); break
    fini = any(l.startswith('{') and 'fusion_ga' in l for l in lignes)
    pause = any('occupée' in l for l in lignes[-3:])
    etat = 'terminé' if fini else 'en pause' if pause else 'en cours' if actif(j, 900) else 'en pause'
    ecrire(fichier, nom=nom, fait=total if fini else t, total=total, unite='milliards d’années', debut=iso(os.path.getctime(j)), maj=iso(time.time()),
           etat=etat, detail=detail)
    return etat


def fusion():
    return calcul_particules('fusion-toutes', 'fusion_toutes_etoiles', 'Fusion Voie lactée–Andromède, 1 million d’étoiles gardées', 10,
                             '3 millions de particules qui s’attirent toutes, sur la carte graphique')


def voie_lactee():
    return calcul_particules('voie-lactee-seule', 'voie_lactee_bras', 'Voie lactée seule : naissance des bras et de la barre', 4.7,
                             '10,5 millions de particules qui s’attirent toutes, sur la carte graphique')


def main():
    while True:
        etats = [telechargement(), horizon(), chaos(), fusion(), voie_lactee()]
        if all(e in ('terminé', 'échec') for e in etats): break
        time.sleep(20)


if __name__ == '__main__':
    main()
