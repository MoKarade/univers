#!/usr/bin/env python3
"""Catalogues de sources par longueur d'onde, pour l'appli PC : chaque source à sa direction MESURÉE sur le ciel, avec sa
grandeur mesurée et sa nature quand l'équipe du catalogue l'a identifiée. Fichier sources_<bande>.bin, lu par
natif/src/ciel_bandes.h et dessiné par-dessus la carte de la même bande.

Pas de distance ici : la plupart de ces sources n'en ont pas de mesurée. Une source n'est placée en 3D que si sa distance
est mesurée (autre étape) ; sur la carte du ciel, sa direction suffit et elle est exacte.

Catalogue pris en charge :
  4fgl : Fermi-LAT, 4e catalogue, 4e publication (4FGL-DR4, 14 ans d'observation), Ballet et al. 2023, arXiv:2307.12546.
         Fichier gll_psc_v35.fit du centre de science de Fermi (NASA), 7 194 sources.

Usage : python sources_bandes.py <dossier_sortie> 4fgl|erass1cl
Format : « UNIVSRC1 », 4 entiers 32 bits (nombre de sources, longueur de la fiche JSON, 0, 0), fiche JSON (UTF-8), des zéros
jusqu'à un multiple de 16 octets, puis par source 8 nombres de 32 bits : x, y, z (direction, équatorial ICRS, flottants),
grandeur (flottant), groupe (entier), 3 entiers à zéro.
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')
import json, math, os, struct, time, urllib.request
import numpy as np

CATALOGUES = {
    '4fgl': dict(
        urls=['https://fermi.gsfc.nasa.gov/ssc/data/access/lat/14yr_catalog/gll_psc_v35.fit',
              'https://heasarc.gsfc.nasa.gov/FTP/fermi/data/lat/catalogs/4FGL-DR4/gll_psc_v35.fit'],
        bande='gamma', libelle='Sources gamma du catalogue Fermi-LAT 4FGL-DR4',
        reference='Ballet et al. 2023, arXiv:2307.12546 (4FGL-DR4) ; Abdollahi et al. 2022, ApJS 260, 53 (4FGL-DR3)',
        grandeur="Flux d'énergie de 100 MeV à 100 GeV", unite='erg/cm²/s',
        cartes=['fermi1', 'fermi2', 'fermi3'],
        colonnes=dict(ra='RAJ2000', dec='DEJ2000', grandeur='Energy_Flux100', classe='CLASS1'),
        # Groupes de la classe donnée par l'équipe de Fermi (CLASS1 ; majuscules = identifiée, minuscules = associée).
        groupes=['non identifiée', 'pulsar', 'noyau actif de galaxie (blazar, radiogalaxie…)',
                 'objet de notre Galaxie (reste de supernova, nébuleuse de pulsar, binaire, amas…)', 'autre galaxie'],
        classes={'psr': 1, 'msp': 1,
                 'bll': 2, 'fsrq': 2, 'bcu': 2, 'rdg': 2, 'agn': 2, 'ssrq': 2, 'css': 2, 'nlsy1': 2, 'sey': 2,
                 'snr': 3, 'pwn': 3, 'hmb': 3, 'lmb': 3, 'bin': 3, 'nov': 3, 'sfr': 3, 'glc': 3, 'gc': 3, 'spp': 3,
                 'gal': 4, 'sbg': 4}),
    'erass1': dict(
        # Catalogue principal des sources X de la DR1 (bande 0,2–2,3 keV), environ 930 000 sources. Publié seulement en
        # archive .fits.tar.gz (643 Mo le 12/11/2026) ; lien relevé sur la page, la recherche (motif « Main ») en secours.
        page='https://erosita.mpe.mpg.de/dr1/AllSkySurveyData_dr1/Catalogues_dr1/', motif=('eRASS1', 'Main'),
        urls=['https://erosita.mpe.mpg.de/dr1/AllSkySurveyData_dr1/Catalogues_dr1/MerloniA_DR1/eRASS1_Main.v1.2.fits.tar.gz'],
        bande='X', libelle="Sources X d'eROSITA (eRASS1, catalogue principal, 0,2 à 2,3 keV)",
        reference='Merloni et al. 2024, A&A 682, A34 (eROSITA-DE DR1, catalogue principal eRASS1)',
        grandeur='flux X de 0,2 à 2,3 keV', unite='erg/cm²/s',
        cartes=['rass', 'erosita'],
        colonnes=dict(ra=['RA', 'RA_CORR'], dec=['DEC', 'DEC_CORR'], grandeur=['ML_FLUX_1', 'ML_FLUX_P1', 'ML_FLUX'], classe=None),
        groupes=['source X ponctuelle ou peu étendue'], classes={}),
    'erass1cl': dict(
        # Le nom exact du fichier n'est pas connu d'avance : il est lu sur la page des catalogues de la DR1 (lien vers un
        # .fits dont le nom contient « cl » et « primary »). Le 12/11/2026 la page ne donnait qu'une archive .fits.tgz :
        # lien relevé à la main sur la page (catalogue primaire de Bulbul et al., version 3.2), la recherche reste en secours.
        page='https://erosita.mpe.mpg.de/dr1/AllSkySurveyData_dr1/Catalogues_dr1/', motif=('cl', 'primary'),
        urls=['https://erosita.mpe.mpg.de/dr1/AllSkySurveyData_dr1/Catalogues_dr1/BulbulE_DR1/erass1cl_primary_v3.2.fits.tgz'],
        bande='X', libelle="Amas et groupes de galaxies d'eROSITA (eRASS1, confirmés en optique)",
        reference='Bulbul et al. 2024, A&A 685, A106 (eRASS1, amas primaires) ; Merloni et al. 2024, A&A 682, A34',
        grandeur='décalage vers le rouge', unite='z', taille='fixe',
        cartes=['rass', 'erosita'],
        colonnes=dict(ra=['RA', 'RA_XFIT', 'RA_X'], dec=['DEC', 'DEC_XFIT', 'DEC_X'], grandeur=['BEST_Z', 'Z_BEST', 'Z'], classe=None),
        groupes=['amas ou groupe de galaxies'], classes={}),
}


def trouver_url(page, motif):
    """Lien vers un fichier .fits de la page dont le nom contient tous les mots du motif (le plus récent en premier)."""
    import re, urllib.parse
    html = urllib.request.urlopen(page, timeout=60).read().decode('utf-8', 'replace')
    liens = [urllib.parse.urljoin(page, h) for h in re.findall(r'href=["\']([^"\']+\.fits(?:\.gz|\.tgz|\.tar\.gz)?)["\']', html, re.I)]
    bons = [l for l in liens if all(m.lower() in l.rsplit('/', 1)[-1].lower() for m in motif)]
    print('  liens trouvés : ' + (', '.join(bons) or 'aucun'), flush=True)
    return sorted(bons, reverse=True)


def colonne(t, noms):
    for n in ([noms] if isinstance(noms, str) else noms):
        if n in t:
            return n
    raise SystemExit(f'colonne absente : {noms} (colonnes du fichier : {", ".join(list(t)[:40])}…)')


def telecharger(urls, chemin):
    if os.path.exists(chemin):
        return chemin
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    for url in urls:
        try:
            print(f'  {url}', flush=True)
            with urllib.request.urlopen(url, timeout=120) as r:
                octets = r.read()
            # FITS (SIMPLE), gzip (1f 8b : .gz ou .tgz) ; une page d'erreur HTML n'est ni l'un ni l'autre
            if octets[:6] != b'SIMPLE' and octets[:2] != bytes([0x1F, 0x8B]):
                print('  pas un fichier FITS ni une archive gzip', flush=True)
                continue
            with open(chemin + '.part', 'wb') as f:
                f.write(octets)
            os.replace(chemin + '.part', chemin)
            return chemin
        except Exception as e:
            print(f'  échec : {e}', flush=True)
    raise SystemExit('aucune adresse ne répond')


def lire_table(chemin):
    """1re extension d'un FITS (table binaire) : dictionnaire colonne -> tableau numpy. Chaînes décodées en ASCII."""
    with open(chemin, 'rb') as f:
        def entete():
            h = {}
            while True:
                bloc = f.read(2880)
                if len(bloc) < 2880:
                    raise SystemExit('FITS tronqué')
                for j in range(0, 2880, 80):
                    carte = bloc[j:j + 80].decode('ascii', 'replace')
                    cle = carte[:8].strip()
                    if cle == 'END':
                        return h
                    if carte[8:10] == '= ':
                        h.setdefault(cle, carte[10:].split('/')[0].strip().strip("'").strip())
        h0 = entete()
        n0 = 1
        for k in range(1, int(h0.get('NAXIS', 0)) + 1):
            n0 *= int(h0[f'NAXIS{k}'])
        taille0 = abs(int(h0.get('BITPIX', 8))) // 8 * n0 if int(h0.get('NAXIS', 0)) else 0
        f.seek((taille0 + 2879) // 2880 * 2880, 1)
        h = entete()
        debut = f.tell()
    codes = {'E': '>f4', 'D': '>f8', 'J': '>i4', 'I': '>i2', 'K': '>i8', 'B': 'u1', 'L': 'S1', 'X': 'u1'}
    champs, noms = [], []
    for c in range(1, int(h['TFIELDS']) + 1):
        tf = h[f'TFORM{c}'].strip()
        i = 0
        while i < len(tf) and tf[i].isdigit():
            i += 1
        n = int(tf[:i]) if i else 1
        code = tf[i]
        if code == 'A':
            champs.append((f'c{c}', f'S{n}'))
        elif code == 'X':
            champs.append((f'c{c}', 'u1', ((n + 7) // 8,)))
        elif code in ('P', 'Q'):
            champs.append((f'c{c}', 'u1', (8 if code == 'P' else 16,)))
        else:
            champs.append((f'c{c}', codes[code], (n,)) if n != 1 else (f'c{c}', codes[code]))
        noms.append(h.get(f'TTYPE{c}', f'c{c}'))
    dt = np.dtype(champs)
    if dt.itemsize != int(h['NAXIS1']):
        raise SystemExit(f'largeur de ligne {dt.itemsize} au lieu de {h["NAXIS1"]}')
    t = np.memmap(chemin, dtype=dt, mode='r', offset=debut, shape=(int(h['NAXIS2']),))
    return {nom: np.asarray(t[f'c{c + 1}']) for c, nom in enumerate(noms)}


def main():
    if len(sys.argv) < 3 or sys.argv[2] not in CATALOGUES:
        raise SystemExit('usage : sources_bandes.py <dossier_sortie> ' + '|'.join(CATALOGUES))
    sortie, nom = sys.argv[1], sys.argv[2]
    c = CATALOGUES[nom]
    urls = c['urls'] or trouver_url(c['page'], c['motif'])
    if not urls:
        raise SystemExit('fichier du catalogue introuvable sur la page')
    c = dict(c, urls=urls)
    chemin = telecharger(urls, os.path.join(sortie, 'cache_catalogues', urls[0].rsplit('/', 1)[1]))
    if chemin.endswith(('.tgz', '.tar.gz')):      # archive : on n'en sort que le fichier .fits, sous son seul nom
        import tarfile, shutil
        with tarfile.open(chemin) as tar:
            membre = next(m for m in tar.getmembers() if m.isfile() and m.name.lower().endswith(('.fits', '.fit')))
            sortie_fits = os.path.join(os.path.dirname(chemin), os.path.basename(membre.name))
            with tar.extractfile(membre) as fi, open(sortie_fits, 'wb') as fo:
                shutil.copyfileobj(fi, fo)
        chemin = sortie_fits
    elif chemin.endswith('.gz'):
        import gzip, shutil
        with gzip.open(chemin) as fi, open(chemin[:-3], 'wb') as fo:
            shutil.copyfileobj(fi, fo)
        chemin = chemin[:-3]
    t = lire_table(chemin)
    col = c['colonnes']
    ra = np.radians(t[colonne(t, col['ra'])].astype(np.float64))
    de = np.radians(t[colonne(t, col['dec'])].astype(np.float64))
    g = t[colonne(t, col['grandeur'])].astype(np.float64)
    cl = [s.decode('ascii', 'replace').strip().lower() for s in t[col['classe']]] if col['classe'] else [''] * len(ra)
    groupe = np.array([c['classes'].get(x, 0) for x in cl], dtype=np.uint32)
    n = len(ra)
    rec = np.zeros((n, 8), dtype=np.float32)
    rec[:, 0] = np.cos(de) * np.cos(ra)
    rec[:, 1] = np.cos(de) * np.sin(ra)
    rec[:, 2] = np.sin(de)
    rec[:, 3] = g
    rec.view(np.uint32)[:, 4] = groupe
    ok = np.isfinite(g) & (g > 0)
    comptes = {c['groupes'][k]: int(np.sum(groupe == k)) for k in range(len(c['groupes']))}
    meta = dict(nom=nom, cartes=c['cartes'], taille=c.get('taille', 'grandeur'), bande=c['bande'], libelle=c['libelle'], reference=c['reference'], grandeur=c['grandeur'],
                unite=c['unite'], nombre=n, groupes=c['groupes'], comptes=comptes, source=c['urls'][0],
                grandeur_min=float(np.min(g[ok])), grandeur_max=float(np.max(g[ok])),
                grandeur_p50=float(np.median(g[ok])), date=time.strftime('%Y-%m-%d'), outil='pipeline/natif/sources_bandes.py')
    js = json.dumps(meta, ensure_ascii=False).encode('utf-8')
    dest = os.path.join(sortie, f'sources_{nom}.bin')
    with open(dest + '.part', 'wb') as f:
        f.write(b'UNIVSRC1')
        f.write(struct.pack('<IIII', n, len(js), 0, 0))
        f.write(js)
        f.write(b'\0' * ((-f.tell()) % 16))
        f.write(rec.tobytes())
    os.replace(dest + '.part', dest)
    # contrôles : quelques sources connues retrouvées à leur place
    noms = [s.decode('ascii', 'replace').strip() for s in t['Source_Name']] if 'Source_Name' in t else []
    assoc = [s.decode('ascii', 'replace').strip() for s in t['ASSOC1']] if 'ASSOC1' in t else []
    # le catalogue nomme les pulsars par leur numéro PSR : Vela = PSR J0835-4510, Geminga = PSR J0633+1746
    for nom_c, cherche in (('Vela', 'PSR J0835-4510'), ('Vela X', 'Vela X'), ('Crab', 'Crab'),
                           ('Geminga', 'PSR J0633+1746'), ('3C 454.3', '3C 454.3'), ('LMC', 'LMC')):
        for i, a in enumerate(assoc):
            if cherche.lower() in a.lower():
                print(f'  {nom_c:9s} : {noms[i] if noms else i} ({a}), ra {math.degrees(ra[i]):.3f}°, dec {math.degrees(de[i]):.3f}°, '
                      f'{g[i]:.3g} {c["unite"]}, classe {cl[i]!r}')
                break
    if nom == 'erass1cl':      # contrôle : quelques amas connus de la moitié ouest (Coma n'y est pas : l = 58°)
        for nm, r0, d0 in (('Virgo (M87)', 187.706, 12.391), ('Fornax (NGC 1399)', 54.621, -35.450), ('Abell 3627 (Norma)', 243.894, -60.866)):
            dd = np.degrees(np.arccos(np.clip(np.sin(de) * math.sin(math.radians(d0)) + np.cos(de) * math.cos(math.radians(d0)) * np.cos(ra - math.radians(r0)), -1, 1)))
            i = int(np.argmin(dd))
            print(f'  {nm:20s} : plus proche à {dd[i]:.2f}°, z = {g[i]:.4f}')
    if nom == 'erass1':        # contrôle : sources X brillantes connues de la moitié ouest du ciel (position SIMBAD, ICRS)
        for nm, r0, d0 in (('Sco X-1', 244.9795, -15.6402), ('LMC X-1', 84.9116, -69.7433), ('M87', 187.7059, 12.3911)):
            dd = np.degrees(np.arccos(np.clip(np.sin(de) * math.sin(math.radians(d0)) + np.cos(de) * math.cos(math.radians(d0)) * np.cos(ra - math.radians(r0)), -1, 1)))
            i = int(np.argmin(dd))
            print(f'  {nm:20s} : plus proche à {dd[i] * 3600:.1f}", flux {g[i]:.3g} {c["unite"]}')
    print(f'Écrit {dest} : {n} sources ; ' + ', '.join(f'{k} {v}' for k, v in comptes.items()))


if __name__ == '__main__':
    import sys
    main()
