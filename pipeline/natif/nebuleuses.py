#!/usr/bin/env python3
"""Nébuleuses en 3D pour l'appli PC -> nebuleuses.bin et nebuleuses_noms.tsv (demande de Marc, 20/11/2026 :
« l'espace paraît trop vide, il manque du gaz, des nébuleuses, de la poussière »).

Seules des nébuleuses dont la DISTANCE est publiée sont placées (aucune distance inventée) :

1. Nébuleuses planétaires : Chornay et Walton 2021 (A&A 656, A110 ; VizieR J/A+A/656/A110), étoiles centrales
   retrouvées dans Gaia EDR3. Place : direction de la nébuleuse (pnRAdeg, pnDEdeg) ; distance : rcomb (pc, combinaison
   de la parallaxe Gaia et d'un a priori de distance, article section 5) ; rayon : rayon angulaire publié (pnRad,
   secondes d'arc) × distance. Gardées : parallaxe meilleure
   que 5 fois son erreur, et association de l'étoile centrale de fiabilité au moins 0,8 (colonne Rel, probabilité publiée).
2. Nuages moléculaires (poussière) : Zucker et al. 2020 (A&A 633, A51 ; VizieR J/A+A/633/A51), distances de 326 lignes
   de visée vers les nuages du « Handbook of Star Forming Regions ». Une ligne par nuage : direction moyenne de ses
   lignes de visée, distance médiane (d50), rayon = écart angulaire moyen des lignes de visée à leur centre × distance
   (étendue couverte par les mesures, au moins 1 pc) [étendue approchée : les mesures ne couvrent pas tout le nuage].

Repère de sortie : celui de l'appli (années-lumière, écliptique J2000, centre : Soleil), comme galaxies_noms.tsv.
Format de nebuleuses.bin : « UNIVNEB1 », n (u32), 0 (u32), puis n fiches de 32 octets : x, y, z, rayon (al, f32),
genre (u32 : 1 nébuleuse planétaire, 2 nuage moléculaire), réservé (3 × u32).
nebuleuses_noms.tsv : nom, x, y, z, description (source et ce qui est mesuré), priorité, comme les autres fichiers de noms.

Usage : python nebuleuses.py <dossier de sortie>      (tables mises en cache dans %LOCALAPPDATA%/univers-raw)
"""
import math, os, struct, sys, time, urllib.request

PC_LY = 3.26156
EPS = math.radians(84381.448 / 3600)      # obliquité J2000 (UAI 1976), repère écliptique de l'appli
MIROIRS = ['https://vizier.cfa.harvard.edu', 'https://vizier.cds.unistra.fr']
CACHE = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'univers-raw')


def vizier(source, nom):
    """Table VizieR en TSV (toutes colonnes), mise en cache ; essaie les miroirs, 4 fois chacun."""
    os.makedirs(CACHE, exist_ok=True)
    chemin = os.path.join(CACHE, nom)
    if os.path.exists(chemin) and os.path.getsize(chemin) > 10000:
        return open(chemin, encoding='utf-8', errors='replace').read()
    for essai in range(4):
        for m in MIROIRS:
            url = f'{m}/viz-bin/asu-tsv?-source={source}&-out.max=unlimited&-out.all'
            try:
                t = urllib.request.urlopen(url, timeout=120).read().decode('utf-8', 'replace')
            except Exception as e:
                print(f'  {m} : {e}')
                continue
            if 'QUERY_STATUS=ERROR' in t or t.count('\n') < 20:
                print(f'  {m} : pas de réponse utile')
                continue
            open(chemin, 'w', encoding='utf-8').write(t)
            return t
        time.sleep(20 * (essai + 1))
    sys.exit(f'ECHEC : table {source} injoignable')


def lignes(t):
    """Lignes de données d'un TSV de VizieR : (en-têtes, lignes)."""
    l = [x for x in t.splitlines() if x and not x.startswith('#')]
    tetes = l[0].split('\t')
    return [c.strip() for c in tetes], [[c.strip() for c in x.split('\t')] for x in l[3:]]


def ecliptique(ra, dec, d_ly):
    """ICRS (degrés) et distance -> x, y, z (al) en écliptique J2000."""
    a, b = math.radians(ra), math.radians(dec)
    x, y, z = math.cos(b) * math.cos(a), math.cos(b) * math.sin(a), math.sin(b)
    return d_ly * x, d_ly * (math.cos(EPS) * y + math.sin(EPS) * z), d_ly * (-math.sin(EPS) * y + math.cos(EPS) * z)


def planetaires():
    tetes, rows = lignes(vizier('J/A%2bA/656/A110', 'chornay_walton_2021.tsv'))
    i = {k: tetes.index(k) for k in ('Name', 'pnRAdeg', 'pnDEdeg', 'pnRad', 'rcomb', 'plx', 'e_plx', 'Rel')}
    out = []
    for r in rows:
        try:
            plx, e = float(r[i['plx']]), float(r[i['e_plx']])
            d_pc, rad = float(r[i['rcomb']]), float(r[i['pnRad']])
            ra, dec = float(r[i['pnRAdeg']]), float(r[i['pnDEdeg']])
        except (ValueError, IndexError):
            continue
        try:
            rel = float(r[i['Rel']])
        except ValueError:
            continue
        if rel < 0.8 or not (plx > 5 * e > 0) or d_pc <= 0 or rad <= 0:
            continue
        rayon_ly = max(rad / 206264.806 * d_pc * PC_LY, 0.05)
        out.append((r[i['Name']], ecliptique(ra, dec, d_pc * PC_LY), rayon_ly, 1,
                    f'nébuleuse planétaire ; distance {d_pc:.0f} pc ({d_pc * PC_LY:.0f} al), parallaxe Gaia de son étoile '
                    f'centrale ; rayon {rad:.1f}″ mesuré (Chornay et Walton 2021) ; éclat non dessiné : repère'))
    return out


def nuages():
    tetes, rows = lignes(vizier('J/A%2bA/633/A51', 'zucker_2020.tsv'))
    i = {k: tetes.index(k) for k in ('Name', 'd50', '_RA.icrs', '_DE.icrs')}
    par_nom = {}
    for r in rows:
        try:
            par_nom.setdefault(r[i['Name']], []).append((float(r[i['_RA.icrs']]), float(r[i['_DE.icrs']]), float(r[i['d50']])))
        except (ValueError, IndexError):
            continue
    out = []
    for nom, v in sorted(par_nom.items()):
        u = [ecliptique(ra, de, 1.0) for ra, de, _ in v]
        c = [sum(p[k] for p in u) for k in range(3)]
        n = math.sqrt(sum(x * x for x in c))
        c = [x / n for x in c]
        d_pc = sorted(d for _, _, d in v)[len(v) // 2]
        ecart = sum(math.acos(max(-1.0, min(1.0, sum(p[k] * c[k] for k in range(3))))) for p in u) / len(u)
        rayon_ly = max(ecart * d_pc, 1.0) * PC_LY
        nom_lisible = nom.replace('_', ' ')
        out.append((nom_lisible, tuple(x * d_pc * PC_LY for x in c), rayon_ly, 2,
                    f'nuage moléculaire (gaz froid et poussière) ; distance {d_pc:.0f} pc ({d_pc * PC_LY:.0f} al) mesurée sur '
                    f'{len(v)} ligne(s) de visée (Zucker et al. 2020) ; étendue approchée d\'après ces lignes ; opacité supposée'))
    return out


def main():
    sortie = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(sortie, exist_ok=True)
    pn, nu = planetaires(), nuages()
    tout = pn + nu
    with open(os.path.join(sortie, 'nebuleuses.bin'), 'wb') as f:
        f.write(b'UNIVNEB1' + struct.pack('<II', len(tout), 0))
        for _, (x, y, z), r, genre, _ in tout:
            f.write(struct.pack('<4f4I', x, y, z, r, genre, 0, 0, 0))
    with open(os.path.join(sortie, 'nebuleuses_noms.tsv'), 'w', encoding='utf-8') as f:
        for nom, (x, y, z), _, genre, texte in tout:
            f.write(f'{nom}\t{x:.6g}\t{y:.6g}\t{z:.6g}\t{texte}\t{4 if genre == 1 else 3}\n')
    print(f'{len(pn)} nébuleuses planétaires, {len(nu)} nuages moléculaires -> {sortie}')


if __name__ == '__main__':
    main()
