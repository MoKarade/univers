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


DRIVE = 'G:/My Drive/Univers/archives/physique'      # règle de Marc (12/11/2026) : le maximum sur le Drive


def separer(d, nom):
    """Règle de Marc (12/11/2026) et accord du fil appli PC : sur le PC, seulement les ÉTOILES (disque, bulbe), dans
    C:/tmp/natif/donnees/<calcul> ; le paquet complet (avec le halo de matière noire) part sur le Drive, dans
    archives/physique/<calcul>, puis quitte le PC. Fait pour chaque paquet complet listé dans fusion.json.
    Dans le dossier d'affichage : mêmes noms de fichiers, « affichees » ne compte que les étoiles, composantes.bin ne
    garde que 1 (disque) et 2 (bulbe)."""
    import json, shutil
    import numpy as np
    js = os.path.join(d, 'fusion.json'); cb = os.path.join(d, 'composantes.bin')
    if not os.path.exists(js) or not os.path.exists(cb): return
    aff = os.path.join(NATIF, 'donnees', nom); drive = os.path.join(DRIVE, nom)
    fait = os.path.join(aff, 'fusion.json')
    if os.path.exists(fait) and os.path.getmtime(fait) >= os.path.getmtime(js): return      # rien de neuf depuis le dernier passage
    try: m = json.load(open(js, encoding='utf-8'))
    except Exception: return
    os.makedirs(aff, exist_ok=True)
    drive_ok = os.path.isdir(os.path.dirname(DRIVE))
    if drive_ok: os.makedirs(drive, exist_ok=True)
    comp = np.fromfile(cb, np.int8); etoile = comp > 0
    counts = m['affichees']; bornes = np.cumsum([0] + counts)
    m_aff = dict(m); m_aff['affichees'] = [int(etoile[bornes[k]:bornes[k + 1]].sum()) for k in range(len(counts))]
    m_aff['composantes'] = 'composantes.bin : 1 disque, 2 bulbe (le halo de matière noire est sur le Drive : archives/physique/' + nom + ')'
    n_all, n_et = int(len(comp)), int(etoile.sum())
    for f, k in m['fichiers']:
        a, b = os.path.join(d, f), os.path.join(aff, f)
        if os.path.exists(b) and os.path.getsize(b) == k * n_et * 6 and not os.path.exists(a): continue
        if not os.path.exists(a): continue
        if os.path.getsize(a) != k * n_all * 6: continue      # paquet incomplet
        x = np.fromfile(a, np.int16).reshape(k, n_all, 3)
        x[:, etoile].tofile(b + '.tmp'); os.replace(b + '.tmp', b)
        if drive_ok:
            shutil.copyfile(a, os.path.join(drive, f) + '.partiel'); os.replace(os.path.join(drive, f) + '.partiel', os.path.join(drive, f))
            os.remove(a)      # le paquet complet n'est plus que sur le Drive
    comp[etoile].tofile(os.path.join(aff, 'composantes.bin.tmp')); os.replace(os.path.join(aff, 'composantes.bin.tmp'), os.path.join(aff, 'composantes.bin'))
    for f in ('composantes.json', 'fusion_noms.tsv'):
        if os.path.exists(os.path.join(d, f)): shutil.copyfile(os.path.join(d, f), os.path.join(aff, f))
    json.dump(m_aff, open(os.path.join(aff, 'fusion.json.tmp'), 'w', encoding='utf-8'), ensure_ascii=False)
    os.replace(os.path.join(aff, 'fusion.json.tmp'), os.path.join(aff, 'fusion.json'))
    if drive_ok:
        for f in ('fusion.json', 'composantes.bin', 'composantes.json'):
            shutil.copyfile(os.path.join(d, f), os.path.join(drive, f))
    if os.path.exists(os.path.join(d, 'etat.npz')) and os.path.exists(os.path.join(d, 'depart.npz')):
        os.remove(os.path.join(d, 'depart.npz'))      # déjà sur le Drive
    convertir_fusion(aff)


def calcul_particules(dossier, fichier, nom, total, detail):
    j = os.path.join(NATIF, dossier, 'journal.txt')
    if not os.path.exists(j): return 'terminé'
    try: separer(os.path.join(NATIF, dossier), dossier)
    except OSError as e: print('séparation :', e, flush=True)
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
