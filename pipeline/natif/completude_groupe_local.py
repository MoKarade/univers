#!/usr/bin/env python3
"""Galaxies du Groupe local : lesquelles manquent à l'appli PC ? -> natif/src/completude_groupe_local.h

Recoupe les galaxies nommées de l'appli (galaxies_noms.tsv : x, y, z en années-lumière, écliptique J2000, centre : Soleil)
avec la Local Volume Database (Pace 2024, github.com/apace7/local_volume_database, fichier comb_all.csv de la dernière
version) : galaxies confirmées (confirmed_galaxy = 1) à moins de 1 Mpc du Soleil d'après leur module de distance.
Deux objets sont la même galaxie si leurs directions sont à moins de 0,3°, puis, pour ce qui reste, de 2° (les Nuages de
Magellan s'étendent sur plusieurs degrés) ; chaque galaxie sert au plus une fois, les paires les plus serrées d'abord.

Sortie : la liste des galaxies de la LVDB absentes de l'appli, et celles de l'appli absentes de la LVDB (nature débattue,
ou hors de 1 Mpc pour la LVDB), avec la version de la LVDB et la date.
Usage : python completude_groupe_local.py <galaxies_noms.tsv> [comb_all.csv]   (sans le second : téléchargé)
"""
import csv, datetime, json, math, os, sys, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SORTIE = os.path.join(ROOT, 'natif', 'src', 'completude_groupe_local.h')
REPO = 'apace7/local_volume_database'
MPC_LY = 3.26156e6
SEUIL_DEG = 2.0
SEUIL_FIN = 0.3
EPS = math.radians(84381.448 / 3600)      # obliquité J2000 (UAI 1976), celle du repère écliptique de l'appli


def lvdb(chemin):
    version = 'inconnue'
    if not chemin:
        rel = json.load(urllib.request.urlopen(f'https://api.github.com/repos/{REPO}/releases/latest', timeout=60))
        version = rel['tag_name']
        chemin = os.path.join(tempfile.gettempdir(), 'lvdb_comb_all.csv')
        urllib.request.urlretrieve(f'https://github.com/{REPO}/releases/download/{version}/comb_all.csv', chemin)
    out = []
    for x in csv.DictReader(open(chemin, encoding='utf-8')):
        if x['confirmed_galaxy'] != '1' or not x['distance_modulus']: continue
        d = 10 ** ((float(x['distance_modulus']) + 5) / 5) / 1e6
        if d < 1.0: out.append((x['name'], float(x['ra']), float(x['dec']), d))
    return out, version


def nos_galaxies(tsv):
    out = []
    for l in open(tsv, encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        x, y, z = map(float, r[1:4]); d = math.sqrt(x * x + y * y + z * z)
        if r[4].startswith('centre') or d <= 0 or d >= MPC_LY: continue
        ye = y * math.cos(EPS) - z * math.sin(EPS); ze = y * math.sin(EPS) + z * math.cos(EPS)      # écliptique -> équatorial
        out.append((r[0], math.degrees(math.atan2(ye, x)) % 360, math.degrees(math.asin(ze / d))))
    return out


def separation(a1, d1, a2, d2):
    a1, d1, a2, d2 = map(math.radians, (a1, d1, a2, d2))
    return math.degrees(math.acos(min(1.0, math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(a1 - a2))))


def main():
    ref, version = lvdb(sys.argv[2] if len(sys.argv) > 2 else '')
    nous = nos_galaxies(sys.argv[1])
    # Deux passes : d'abord les directions à moins de SEUIL_FIN (presque toutes les naines), puis jusqu'à SEUIL_DEG pour les
    # grandes galaxies étendues ; ainsi un satellite d'Andromède n'emprunte pas la place d'un voisin.
    pris, trouvees = set(), set()
    for seuil in (SEUIL_FIN, SEUIL_DEG):
        paires = sorted((separation(r[1], r[2], g[1], g[2]), k, i) for k, r in enumerate(ref) if k not in trouvees
                        for i, g in enumerate(nous) if i not in pris)
        for sep, k, i in paires:
            if sep >= seuil: break
            if k in trouvees or i in pris: continue
            trouvees.add(k); pris.add(i)
    manquantes = sorted(((r[0], r[3]) for k, r in enumerate(ref) if k not in trouvees), key=lambda t: t[1])
    hors_lvdb = [nous[i][0] for i in range(len(nous)) if i not in pris]
    c = lambda s: '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    lignes = ['// Généré par pipeline/natif/completude_groupe_local.py : ne pas éditer à la main.',
              f'// Local Volume Database {version} (Pace 2024), relevé le {datetime.date.today().isoformat()} : {len(ref)} galaxies confirmées à moins de 1 Mpc,',
              f'// {len(pris)} retrouvées parmi les {len(nous)} galaxies nommées de l\'appli (directions à moins de {SEUIL_DEG:g}°).',
              '#pragma once', '#include <array>', '', 'namespace completude::groupe_local {',
              f'constexpr int kReference = {len(ref)};',
              f'constexpr int kAppariees = {len(pris)};',
              f'constexpr int kNommeesAuRecoupement = {len(nous)};      // galaxies de l\'appli à moins de 1 Mpc lors du recoupement',
              'struct Manquante { const char* nom; double distanceMpc; };',
              # std::array : une liste vide reste valide (un tableau C de taille nulle ne l'est pas).
              f'constexpr std::array<Manquante, {len(manquantes)}> kManquantes{{{{' + ', '.join(f'{{{c(n)}, {d:.3f}}}' for n, d in manquantes) + '}};',
              f'constexpr int kManquantesN = {len(manquantes)};',
              f'constexpr std::array<const char*, {len(hors_lvdb)}> kHorsLvdb{{{{' + ', '.join(c(n) for n in hors_lvdb) + '}};      // dans l\'appli, pas dans la LVDB à moins de 1 Mpc',
              f'constexpr int kHorsLvdbN = {len(hors_lvdb)};', '}', '']
    open(SORTIE, 'w', encoding='utf-8', newline='\n').write('\n'.join(lignes))
    print(f'{len(pris)} sur {len(ref)} retrouvées ; {len(manquantes)} manquantes ; hors LVDB : {hors_lvdb} -> {SORTIE}')


if __name__ == '__main__':
    main()
