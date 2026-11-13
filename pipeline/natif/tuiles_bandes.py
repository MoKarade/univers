#!/usr/bin/env python3
"""Tuiles fines d'un relevé du ciel pour l'appli PC (format UNIVTIL2) : la carte à pleine finesse (ordre HiPS 6, pixel de
6,4 secondes d'arc pour des tuiles de 512 px), lue tuile par tuile pendant le vol.

Source : les tuiles FITS du relevé telles que publiées (valeurs mesurées ; seuls BSCALE et BZERO appliqués ; tuiles
compressées en gzip acceptées), via la même fiche et les mêmes copies de secours que ciel_bandes.py. Contrôle fait le
12/11/2026 : chez l'IRSA, la tuile WISE W1 d'ordre 6 est exactement la moyenne de ses 16 tuiles d'ordre 8 (écart 0,000 %
pixel par pixel sur 3 tuiles). Les ordres plus grossiers (5 et 4) sont recalculés ici par moyenne des 4 enfants mesurés
(np.nanmean), pas pris du serveur : le 12/11/2026 les tuiles d'ordre 2 de WISE à l'IRSA étaient fausses. L'ordre 3
(Nside 4096 pour 512 px) est la carte entière ciel_<nom>.bin ; les tuiles commencent à l'ordre 4.

Format UNIVTIL2 :
- Index, petit, sur le PC : <index>/<nom>/ordre_K.idx = « UNIVTIL2 », '<IIII' (K, w, 12·4^K, g=3), puis 12·4^K uint32 :
  position de la tuile dans son paquet + 1, 0 si la tuile est absente.
- Paquets : <paquets>/<nom>/ordre_K/p######.bin, ###### = numéro de tuile >> (2g) sur 6 chiffres. Un paquet met bout à
  bout, sans en-tête, les tuiles présentes de son groupe de 64, par numéro croissant ; une tuile = w² float16 en ordre
  emboîté local (valeur i de la tuile n = pixel emboîté n·w² + i de la carte Nside w·2^K), NaN = pas de mesure.
- float16 ne va que de 6e-8 à 65504 : chaque valeur est stockée multipliée par facteur_float16 (puissance de 10 choisie
  d'après les valeurs du relevé, écrite dans fiche.json) ; valeur mesurée = valeur lue / facteur_float16. Les valeurs qui
  dépasseraient 65504 sont comptées (« depassements ») et écrites à ±65504.
- <index>/<nom>/fiche.json : fiche de ciel_<nom>.bin, plus ordre_max, largeur, ordres, groupe, facteur, comptes.

Travail par morceaux : un groupe de 64 tuiles d'ordre 4 = 1024 tuiles d'ordre 6 (environ 1 Go de FITS, 0,5 Go de float16),
écrits puis oubliés ; reprise possible (etat.npz dans le dossier des paquets). Les FITS d'origine ne sont gardés que si
--brut est donné.

Usage : python tuiles_bandes.py <sortie> <nom> [--index D] [--paquets D] [--brut D] [--simultanes 12] [--avancement F --rang i/n]
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')
import argparse, concurrent.futures as cf, datetime, json, math, os, struct, time, urllib.error, urllib.request, warnings
import numpy as np

_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ciel_bandes as cb      # fiches RELEVES, lecture des fiches HiPS et des FITS, pose des tuiles

SOURCES = {'erosita': 'eROSITA-DR1-024', 'galexfuv': 'GALEX-GR6-FUV', 'galexnuv': 'GALEX-GR6-NUV',
           'wise3': 'AllWISE-W1', 'wise46': 'AllWISE-W2', 'wise12': 'AllWISE-W3', 'wise22': 'AllWISE-W4'}
F16_MAX = 65504.0
G = 3                # 4^3 = 64 tuiles par paquet
K_FIN = 6            # ordre le plus fin (pixel de 6,4″ pour 512 px)
K_BAS = 4            # ordre le plus grossier en tuiles (l'ordre 3 est la carte entière)
K_ZONE = 8           # finesse maximale publiée (pixel de 1,6″ pour 512 px), seulement sur quelques zones
# Zones à finesse maximale (validées par Marc le 12/11/2026) : centre en équatorial J2000 (degrés) et rayon du disque.
ZONES = {'M31': (10.6847, 41.2690, 1.6), 'M101': (210.8023, 54.3489, 0.5),
         'Orion': (84.0, -3.5, 3.0), 'centre galactique': (266.4168, -29.0078, 1.0)}


def choisir_source(nom):
    """Relevé principal puis copies de secours, comme ciel_bandes.main() ; renvoie (fiche du relevé, fiche HiPS)."""
    base = cb.RELEVES[nom]
    for r in [base] + [dict(base, **s) for s in base.get('secours', [])]:
        r = dict(r)
        r.pop('secours', None)
        if r.get('fichiers'):
            continue
        try:
            return r, cb.proprietes(r['hips'], r.get('adresse'))
        except (Exception, SystemExit) as e:
            print(f'  {e} ; copie suivante', flush=True)
    raise SystemExit(f'{nom} : aucune copie en tuiles ne répond')


def telecharger(adresse, ordre, n, brut):
    """Tuile FITS telle que publiée ; b'' si le serveur dit qu'elle n'existe pas (404). Gardée sur disque si brut."""
    rel = os.path.join(f'Norder{ordre}', f'Dir{(n // 10000) * 10000}', f'Npix{n}.fits')
    if brut and os.path.exists(os.path.join(brut, rel)):
        with open(os.path.join(brut, rel), 'rb') as f:
            return f.read()
    url = f'{adresse}/Norder{ordre}/Dir{(n // 10000) * 10000}/Npix{n}.fits'
    for k in range(6):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                octets = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return b''
            if k == 5:
                raise
        except Exception:
            if k == 5:
                raise
        time.sleep(2 ** k)
    if octets[:6] != b'SIMPLE' and octets[:2] != bytes([0x1F, 0x8B]):      # FITS, ou FITS compressé en gzip (IRSA)
        raise RuntimeError(f'tuile {n} : ni FITS ni gzip')
    if brut:
        chemin = os.path.join(brut, rel)
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(chemin + '.part', 'wb') as f:
            f.write(octets)
        os.replace(chemin + '.part', chemin)
    return octets


def facteur_float16(stats):
    """Puissance de 10 : le 99,9e centile vers 1000, et le maximum de la carte Nside 4096 au moins 20 fois sous 65504
    (les pixels fins montent plus haut que leur moyenne)."""
    if not stats.get('p999'):
        return 1.0
    f = 1000.0 / abs(stats['p999'])
    if stats.get('max'):
        f = min(f, F16_MAX / (20.0 * abs(stats['max'])))
    return 10.0 ** math.floor(math.log10(f))


class Avancement:
    """Fichier lu par l'appli : écrit dans un .tmp puis renommé."""
    def __init__(self, chemin, nom, total, unite):
        self.chemin, self.nom, self.total, self.unite = chemin, nom, total, unite
        self.debut = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        self.dernier = 0.0

    def ecrire(self, fait, etat, detail, force=False):
        if not self.chemin or (not force and time.time() - self.dernier < 15):
            return
        self.dernier = time.time()
        txt = (f'nom={self.nom}\nfait={fait}\ntotal={self.total}\nunite={self.unite}\ndebut={self.debut}\n'
               f"maj={datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\netat={etat}\ndetail={detail}\n")
        tmp = self.chemin[:-4] + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(txt)
        os.replace(tmp, self.chemin)


def ecrire_paquets(dossier, ordre, blocs, idx):
    """blocs : dict numéro de tuile -> tableau (w² valeurs, déjà multipliées par le facteur). Un paquet par groupe de 64
    tuiles présentes, dans l'ordre croissant ; remplit idx (position + 1)."""
    os.makedirs(os.path.join(dossier, f'ordre_{ordre}'), exist_ok=True)
    for g in sorted({n >> (2 * G) for n in blocs}):
        rang = 0
        chemin = os.path.join(dossier, f'ordre_{ordre}', f'p{g:06d}.bin')
        with open(chemin + '.part', 'wb') as f:
            for n in range(g << (2 * G), (g + 1) << (2 * G)):
                if n in blocs:
                    f.write(blocs[n].astype('<f2').tobytes())
                    rang += 1
                    idx[n] = rang
        os.replace(chemin + '.part', chemin)


def moyenne_enfants(blocs_fins, n, w):
    """Tuile n de l'ordre K depuis ses 4 enfants 4n..4n+3 de l'ordre K+1 (moyenne des pixels mesurés) ; None si aucun."""
    if not any((4 * n + k) in blocs_fins for k in range(4)):
        return None
    fin = np.full(4 * w * w, np.nan, dtype=np.float32)
    for k in range(4):
        b = blocs_fins.get(4 * n + k)
        if b is not None:
            fin[k * w * w:(k + 1) * w * w] = b
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)      # pixel sans enfant mesuré : reste NaN
        return np.nanmean(fin.reshape(-1, 4), axis=1)


def ecrire_idx(chemin, ordre, w, idx):
    with open(chemin + '.part', 'wb') as f:
        f.write(b'UNIVTIL2')
        f.write(struct.pack('<IIII', ordre, w, idx.size, G))
        f.write(idx.astype('<u4').tobytes())
    os.replace(chemin + '.part', chemin)


class ArchiveBrut:
    """Archive du brut morceau par morceau : les FITS d'un morceau (gardés dans `brut`) sont copiés dans `dest` avec
    l'arborescence HiPS (Norder/Dir/Npix), vérifiés (même nombre, mêmes tailles), puis supprimés en local. Tous les
    ~20 Go, on attend que la file d'envoi de Drive pour ordinateur soit vide (sa base lue en lecture seule) : le
    téléchargement attend avec, le transitoire local reste petit. C: doit garder au moins 150 Go libres."""
    LOT = 20e9
    LIBRE_MIN = 150e9
    DB = os.path.expandvars(r'%LOCALAPPDATA%\Google\DriveFS\101439376997532179266\metadata_sqlite_db')

    def __init__(self, brut, dest, adresse, reference, premier_morceau):
        self.brut, self.dest, self.depuis_lot = brut, dest, 0.0
        os.makedirs(dest, exist_ok=True)
        lisez = os.path.join(dest, 'LISEZMOI.txt')
        if not os.path.exists(lisez):
            with open(lisez, 'w', encoding='utf-8') as f:
                f.write(f'{os.path.basename(dest)}\nAdresse d\'origine : {adresse}\nRéférence : {reference}\n'
                        f'Tuiles HiPS telles que servies (certaines compressées en gzip), rangées en Norder<k>/Dir<d>/Npix<n>.fits.\n')
        with open(lisez, 'a', encoding='utf-8') as f:
            f.write(f'{time.strftime("%Y-%m-%d %H:%M")} : ordre {K_FIN} archivé à partir du morceau {premier_morceau + 1} '
                    f'sur 48 (morceaux de 1024 tuiles ; les morceaux précédents ont été faits sans garder le brut).\n')

    def file_envoi(self):
        import sqlite3
        c = sqlite3.connect(f'file:{self.DB}?mode=ro', uri=True)
        try:
            return c.execute('select count(*) from operations').fetchone()[0]
        finally:
            c.close()

    def attendre(self):
        import shutil
        while True:
            ops, libre = self.file_envoi(), shutil.disk_usage('C:\\').free
            if ops == 0 and libre >= self.LIBRE_MIN:
                return
            if ops == 0:
                raise SystemExit(f'C: n\'a plus que {libre / 1e9:.0f} Go libres (minimum 150) : arrêt')
            print(f'  archive : attente de l\'envoi vers Google ({ops} opérations, C: {libre / 1e9:.0f} Go libres)', flush=True)
            time.sleep(30)

    def morceau(self, ordre, ns):
        import shutil
        liste = []
        for n in ns:
            rel = os.path.join(f'Norder{ordre}', f'Dir{(n // 10000) * 10000}', f'Npix{n}.fits')
            if os.path.exists(os.path.join(self.brut, rel)):
                liste.append((rel, os.path.getsize(os.path.join(self.brut, rel))))
        taille = sum(t for _, t in liste)
        if self.depuis_lot + taille > self.LOT:
            self.attendre()
            self.depuis_lot = 0.0
        for rel, t in liste:
            cible = os.path.join(self.dest, rel)
            os.makedirs(os.path.dirname(cible), exist_ok=True)
            if not (os.path.exists(cible) and os.path.getsize(cible) == t):
                shutil.copyfile(os.path.join(self.brut, rel), cible)
        ko = [rel for rel, t in liste if not os.path.exists(os.path.join(self.dest, rel))
              or os.path.getsize(os.path.join(self.dest, rel)) != t]
        if ko:
            raise SystemExit(f'archive : {len(ko)} fichiers différents sur la destination ({ko[:5]}) ; brut local gardé')
        for rel, _ in liste:
            os.remove(os.path.join(self.brut, rel))
        self.depuis_lot += taille
        return len(liste), taille


def ecrire_fiche(dossier_idx, fiche):
    """fiche.json écrite d'un coup (.part puis renommage)."""
    chemin = os.path.join(dossier_idx, 'fiche.json')
    with open(chemin + '.part', 'w', encoding='utf-8') as f:
        json.dump(fiche, f, ensure_ascii=False, indent=1)
    os.replace(chemin + '.part', chemin)


def lire_fiche(sortie, nom, r):
    """Fiche de la carte entière ciel_<nom>.bin si elle existe (mêmes textes et statistiques), sinon celle du relevé."""
    carte = os.path.join(sortie, f'ciel_{nom}.bin')
    if not os.path.exists(carte):
        return dict(r)
    with open(carte, 'rb') as f:
        f.read(8)
        _, _, lj, _ = struct.unpack('<IIII', f.read(16))
        return json.loads(f.read(lj))


def tuiles_disque(ra, de, rayon, nside, pas=0.02):
    """Pixels emboîtés (Nside donné) qui touchent un disque : le disque est échantillonné tous les `pas` degrés
    (environ un dixième de tuile d'ordre 8), chaque point converti par ang2pix_nest de ciel_bandes (même calcul que
    healpy, vérifié). healpy n'existe pas sous Windows : c'est l'équivalent de query_disc(inclusive=True) à
    l'échantillonnage près."""
    n = int(math.ceil(rayon / pas))
    u = np.arange(-n, n + 1) * math.radians(pas)
    X, Y = np.meshgrid(u, u)
    m = X ** 2 + Y ** 2 <= math.radians(rayon) ** 2
    x, y = X[m], Y[m]
    a0, d0 = math.radians(ra), math.radians(de)
    rho = np.hypot(x, y)
    c = np.arctan(rho)
    sur = np.where(rho > 0, rho, 1.0)
    dec = np.arcsin(np.cos(c) * math.sin(d0) + np.where(rho > 0, y * np.sin(c) * math.cos(d0) / sur, 0.0))
    asc = a0 + np.arctan2(x * np.sin(c), rho * math.cos(d0) * np.cos(c) - y * math.sin(d0) * np.sin(c))
    return set(np.asarray(cb.ang2pix_nest(nside, np.pi / 2 - dec, np.mod(asc, 2 * np.pi))).tolist())


def morceau(ex, adresse, w, table, facteur, premier, nombre, brut, ordre=K_FIN, liste=None):
    """Télécharge les tuiles [premier, premier + nombre) de l'ordre donné (ou celles de `liste`) ; renvoie (blocs,
    absentes, dépassements)."""
    ns = liste if liste is not None else range(premier, premier + nombre)
    futurs = {ex.submit(telecharger, adresse, ordre, n, brut): n for n in ns}
    blocs, echecs, absentes, depass = {}, [], 0, 0
    for fu in cf.as_completed(futurs):
        n = futurs[fu]
        try:
            octets = fu.result()
        except Exception as e:
            echecs.append(n)
            print(f'  tuile {n} : {e}', flush=True)
            continue
        if not octets:
            absentes += 1
            continue
        img = cb.lire_fits(octets)
        if img.shape != (w, w):
            raise SystemExit(f'tuile {n} : {img.shape}, attendu {w} × {w}')
        v = np.full(w * w, np.nan, dtype=np.float32)
        v[table] = img.astype(np.float32).ravel()
        v *= facteur
        trop = np.abs(v) > F16_MAX
        depass += int(trop.sum())
        v[trop] = np.sign(v[trop]) * F16_MAX
        blocs[n] = v
    if echecs:
        raise SystemExit(f'{len(echecs)} tuiles en échec réseau ({echecs[:10]}) ; relancer, la reprise part de ce morceau')
    return blocs, absentes, depass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sortie', help='dossier des cartes entières (ciel_<nom>.bin)')
    ap.add_argument('nom')
    ap.add_argument('--index', default=r'C:\tmp\natif\donnees\tuiles', help='dossier des .idx et de fiche.json')
    ap.add_argument('--paquets', help='dossier des paquets (défaut : <sortie>/tuiles_paquets)')
    ap.add_argument('--brut', help="garder les FITS d'origine dans ce dossier (Norder/Dir/Npix), pour l'archive")
    ap.add_argument('--simultanes', type=int, default=12)
    ap.add_argument('--avancement', help="fichier d'avancement lu par l'appli")
    ap.add_argument('--rang', default='1/1', help="place de ce relevé dans le lot, « i/n »")
    ap.add_argument('--zones', action='store_true', help="ajoute les ordres 7 et 8 sur les seules zones de ZONES")
    ap.add_argument('--archive', help="dossier d'archive du brut (Drive), rempli morceau par morceau ; demande --brut")
    a = ap.parse_args()
    if a.zones:
        return main_zones(a)

    r, p = choisir_source(a.nom)
    adresse = p['hips_service_url'].rstrip('/')
    w = int(p.get('hips_tile_width', 512))
    ordre_max = int(p.get('hips_order', K_FIN))
    if ordre_max < K_FIN:
        raise SystemExit(f'{a.nom} : publié jusqu’à l’ordre {ordre_max} seulement')
    ordres = list(range(K_BAS, K_FIN + 1))
    dossier_idx = os.path.join(a.index, a.nom)
    dossier_paq = os.path.join(a.paquets or os.path.join(a.sortie, 'tuiles_paquets'), a.nom)
    os.makedirs(dossier_idx, exist_ok=True)
    os.makedirs(dossier_paq, exist_ok=True)
    fiche = lire_fiche(a.sortie, a.nom, r)
    facteur = facteur_float16(fiche.get('stats', {}))
    etat = os.path.join(dossier_paq, 'etat.npz')
    if os.path.exists(etat):
        # reprise : les morceaux déjà écrits l'ont été avec un facteur ; on garde CELUI-LÀ (12/11/2026 : une reprise
        # lancée sans la carte entière à côté recalculait 1 au lieu de 10 000 pour eROSITA)
        e = np.load(etat)
        if 'facteur' not in e.files:
            raise SystemExit(f'{etat} : facteur absent ; le mettre avant de reprendre (voir fiche.json)')
        if float(e['facteur']) != facteur:
            print(f'  reprise : facteur {float(e["facteur"]):g} des morceaux déjà faits gardé (calculé ici : {facteur:g})', flush=True)
        facteur = float(e['facteur'])
    if not fiche.get('stats') and not os.path.exists(etat):
        raise SystemExit(f'ciel_{a.nom}.bin absent de {a.sortie} : pas de statistiques pour choisir le facteur float16')
    table = cb.orientations(w)[0].ravel()
    print(f'{r["libelle"]} : serveur {adresse}, tuiles {w} px, ordres {ordres} (publié jusqu\'à {ordre_max}), '
          f'Nside {w << K_FIN}, facteur float16 {facteur:g}', flush=True)

    # fiche écrite dès le départ avec le facteur : le moteur lit facteur_float16 et prendrait 1 sans elle
    ecrire_fiche(dossier_idx, dict(fiche, ordre_max=K_FIN, largeur=w, ordres=ordres, groupe=G, serveur=adresse,
                                   facteur_float16=facteur, format='UNIVTIL2', en_cours=True,
                                   outil_tuiles='pipeline/natif/tuiles_bandes.py'))
    # état de reprise : index déjà remplis et morceaux faits
    idx = {k: np.zeros(12 * 4 ** k, dtype=np.uint32) for k in ordres}
    faits, depass, absentes = set(), 0, 0
    if os.path.exists(etat):
        e = np.load(etat)
        idx = {k: e[f'idx{k}'] for k in ordres}
        faits, depass, absentes = set(e['faits'].tolist()), int(e['depass']), int(e['absentes'])

    i_r, n_r = (int(x) for x in a.rang.split('/'))
    av = Avancement(a.avancement, 'Tuiles fines du ciel (ordre 6, pixel de 6,4″)', 100 * n_r, '%')
    n_morceaux = (12 * 4 ** K_BAS) >> (2 * G)          # groupes de 64 tuiles d'ordre 4 : 48
    par_morceau = 1 << (2 * (G + K_FIN - K_BAS))       # tuiles d'ordre 6 par morceau : 1024
    archive = None
    if a.archive:
        if not a.brut:
            raise SystemExit('--archive demande --brut (dossier local où garder le brut d’un morceau)')
        premier_m = min([m for m in range(n_morceaux) if m not in faits] or [n_morceaux])
        archive = ArchiveBrut(a.brut, a.archive, adresse, fiche.get('reference', ''), premier_m)
    t0 = time.time()
    with cf.ThreadPoolExecutor(a.simultanes) as ex:
        for m in range(n_morceaux):
            if m in faits:
                continue
            premier = m * par_morceau
            blocs, ab, de = morceau(ex, adresse, w, table, facteur, premier, par_morceau, a.brut)
            absentes += ab
            depass += de
            ecrire_paquets(dossier_paq, K_FIN, blocs, idx[K_FIN])
            for k in range(K_FIN - 1, K_BAS - 1, -1):      # ordres 5 puis 4, depuis les blocs de l'ordre au-dessus
                deb = premier >> (2 * (K_FIN - k))
                fins, blocs = blocs, {}
                for n in range(deb, deb + (par_morceau >> (2 * (K_FIN - k)))):
                    b = moyenne_enfants(fins, n, w)
                    if b is not None:
                        blocs[n] = b
                ecrire_paquets(dossier_paq, k, blocs, idx[k])
            faits.add(m)
            np.savez(etat[:-4] + '_part.npz', faits=np.array(sorted(faits)), depass=depass, absentes=absentes, facteur=facteur,
                     **{f'idx{k}': idx[k] for k in ordres})
            os.replace(etat[:-4] + '_part.npz', etat)
            print(f'  morceau {m + 1}/{n_morceaux} fait, {time.time() - t0:.0f} s', flush=True)
            if archive:
                nb, taille = archive.morceau(K_FIN, range(premier, premier + par_morceau))
                print(f'  morceau {m + 1} : brut archivé, {nb} fichiers, {taille / 1e9:.2f} Go', flush=True)
            av.ecrire(100 * (i_r - 1) + int(100 * len(faits) / n_morceaux), 'en cours',
                      f'{r["libelle"]} : morceau {len(faits)} sur {n_morceaux} (relevé {i_r} sur {n_r})', True)

    for k in ordres:
        ecrire_idx(os.path.join(dossier_idx, f'ordre_{k}.idx'), k, w, idx[k])
    comptes = {str(k): int((idx[k] > 0).sum()) for k in ordres}
    fiche = dict(fiche, ordre_max=K_FIN, largeur=w, ordres=ordres, groupe=G, serveur=adresse, facteur_float16=facteur,
                 depassements=depass, tuiles_presentes=comptes, tuiles_absentes_ordre_max=absentes,
                 source_archive=SOURCES.get(a.nom, a.nom), format='UNIVTIL2', date_tuiles=time.strftime('%Y-%m-%d'),
                 outil_tuiles='pipeline/natif/tuiles_bandes.py')
    ecrire_fiche(dossier_idx, fiche)
    taille = sum(os.path.getsize(os.path.join(d, x)) for d, _, fs in os.walk(dossier_paq) for x in fs if x.startswith('p'))
    print(f'Écrit {dossier_idx} (index) et {dossier_paq} (paquets, {taille / 1e9:.2f} Go) : tuiles présentes {comptes}, '
          f'{absentes} absentes à l\'ordre {K_FIN}, {depass} valeurs au-delà de float16', flush=True)
    av.ecrire(100 * i_r, 'terminé' if i_r == n_r else 'en cours',
              f'{r["libelle"]} fait : {comptes[str(K_FIN)]} tuiles, {taille / 1e9:.1f} Go (relevé {i_r} sur {n_r})', True)


def main_zones(a):
    """Ordres 7 et 8 sur les zones de ZONES : l'ordre 8 tel que publié, l'ordre 7 recalculé (moyenne des 4 enfants).
    Index clairsemés (0 hors des zones) ; la fiche existante (ordres 4 à 6) est complétée, pas remplacée."""
    r, p = choisir_source(a.nom)
    adresse = p['hips_service_url'].rstrip('/')
    w = int(p.get('hips_tile_width', 512))
    if int(p.get('hips_order', 0)) < K_ZONE:
        raise SystemExit(f"{a.nom} : publié jusqu’à l’ordre {p.get('hips_order')} seulement")
    if not p.get('hips_frame', 'equatorial').startswith('equ'):
        raise SystemExit(f"{a.nom} : repère {p.get('hips_frame')} ; les zones sont données en équatorial")
    dossier_idx = os.path.join(a.index, a.nom)
    dossier_paq = os.path.join(a.paquets or os.path.join(a.sortie, 'tuiles_paquets'), a.nom)
    fiche_p = os.path.join(dossier_idx, 'fiche.json')
    if not os.path.exists(fiche_p):
        raise SystemExit(f'{fiche_p} absent : faire d’abord les ordres {K_BAS} à {K_FIN}')
    with open(fiche_p, encoding='utf-8') as f:
        fiche = json.load(f)
    facteur = float(fiche['facteur_float16'])      # le même facteur que les ordres 4 à 6
    table = cb.orientations(w)[0].ravel()
    t8 = set()
    for nom_z, (ra, de, ray) in ZONES.items():
        z = tuiles_disque(ra, de, ray, 1 << K_ZONE)
        print(f'  zone {nom_z} : {len(z)} tuiles d’ordre {K_ZONE}', flush=True)
        t8 |= z
    t8 = sorted(t8)
    print(f"{r['libelle']} : {len(t8)} tuiles d’ordre {K_ZONE} à télécharger, facteur float16 {facteur:g}", flush=True)
    t0 = time.time()
    with cf.ThreadPoolExecutor(a.simultanes) as ex:
        blocs8, absentes, depass = morceau(ex, adresse, w, table, facteur, 0, 0, a.brut, ordre=K_ZONE, liste=t8)
    idx8 = np.zeros(12 * 4 ** K_ZONE, dtype=np.uint32)
    ecrire_paquets(dossier_paq, K_ZONE, blocs8, idx8)
    blocs7 = {}
    for n in sorted({t >> 2 for t in t8}):
        b = moyenne_enfants(blocs8, n, w)
        if b is not None:
            blocs7[n] = b
    idx7 = np.zeros(12 * 4 ** (K_ZONE - 1), dtype=np.uint32)
    ecrire_paquets(dossier_paq, K_ZONE - 1, blocs7, idx7)
    ecrire_idx(os.path.join(dossier_idx, f'ordre_{K_ZONE - 1}.idx'), K_ZONE - 1, w, idx7)
    ecrire_idx(os.path.join(dossier_idx, f'ordre_{K_ZONE}.idx'), K_ZONE, w, idx8)
    comptes = dict(fiche.get('tuiles_presentes', {}), **{str(K_ZONE - 1): len(blocs7), str(K_ZONE): len(blocs8)})
    fiche = dict(fiche, ordre_max=K_ZONE, ordres=list(range(K_BAS, K_ZONE + 1)), tuiles_presentes=comptes,
                 zones_fines={k: dict(ra=v[0], dec=v[1], rayon_deg=v[2]) for k, v in ZONES.items()},
                 zones_tuiles_absentes=absentes, depassements=int(fiche.get('depassements', 0)) + depass,
                 note_zones=f'ordres {K_ZONE - 1} et {K_ZONE} seulement sur les zones (index clairsemés, 0 ailleurs)')
    with open(fiche_p + '.part', 'w', encoding='utf-8') as f:
        json.dump(fiche, f, ensure_ascii=False, indent=1)
    os.replace(fiche_p + '.part', fiche_p)
    taille = sum(os.path.getsize(os.path.join(dossier_paq, f'ordre_{k}', x)) for k in (K_ZONE - 1, K_ZONE)
                 for x in os.listdir(os.path.join(dossier_paq, f'ordre_{k}')))
    print(f'Écrit zones : ordre {K_ZONE} {len(blocs8)} tuiles ({absentes} absentes), ordre {K_ZONE - 1} {len(blocs7)} '
          f'tuiles, {taille / 1e9:.2f} Go de paquets, {depass} valeurs au-delà de float16, {time.time() - t0:.0f} s',
          flush=True)


if __name__ == '__main__':
    main()
