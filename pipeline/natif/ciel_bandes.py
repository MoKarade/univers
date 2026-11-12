#!/usr/bin/env python3
"""Cartes du ciel dans toutes les longueurs d'onde : télécharge un relevé publié (tuiles HiPS en FITS, valeurs mesurées)
et l'écrit en une carte HEALPix emboîtée pour l'appli PC (fichier ciel_<nom>.bin, lu par natif/src/ciel_bandes.h).

Pourquoi HiPS : c'est le format commun des relevés du ciel entier (norme IVOA HiPS 1.0, Fernique et al. 2017). Les
tuiles FITS gardent la valeur mesurée (kelvins, MJy/sr, coups par seconde...), pas une image retouchée. Chaque niveau
de tuiles est la moyenne des quatre pixels du niveau en dessous : la vue lointaine est déjà la somme du mesuré.

Aucune valeur n'est modifiée : seuls BSCALE et BZERO du fichier sont appliqués. Un pixel vide (NaN ou BLANK) reste vide :
c'est un trou de couverture du relevé, montré comme tel à l'écran. Les tuiles absentes du serveur (relevé partiel, par
exemple eROSITA DR1 qui ne couvre que la moitié ouest de la Galaxie) sont des trous aussi.

Usage : python ciel_bandes.py <dossier_sortie> <nom> [--ordre 2] [--simultanes 8] [--cache <dossier>]
        python ciel_bandes.py <dossier_sortie> --liste
Le <nom> est une clé de RELEVES ci-dessous. --ordre 2 donne Nside 2048 pour des tuiles de 512 pixels (1,7 minute d'arc).
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')
import argparse, concurrent.futures as cf, json, math, os, struct, sys, time, urllib.error, urllib.parse, urllib.request
import numpy as np

MOC = 'https://alasky.cds.unistra.fr/MocServer/query'

# Chaque relevé : identifiant HiPS (liste du CDS, https://aladin.cds.unistra.fr/hips/list, lue le 12 novembre 2026),
# bande, ce qu'il mesure, unité, résolution native, couverture, référence. La résolution et la couverture sont celles
# publiées par l'équipe du relevé ; la couverture réelle est recomptée sur les pixels téléchargés.
RELEVES = {
    'haslam408': dict(
        hips='ESAVO/P/Haslam408', bande='radio', libelle='Radio 408 MHz',
        mesure='Température de brillance à 408 MHz (rayonnement synchrotron des électrons de la Galaxie)',
        unite='K', resolution_arcmin=56.0, longueur_onde='73 cm',
        reference='Haslam et al. 1982, A&AS 47, 1 ; carte retraitée de Remazeilles et al. 2015, MNRAS 451, 4311',
        couverture_publiee='tout le ciel', echelle='log'),
    'hi4pi': dict(
        hips='CDS/P/HI4PI/NHI', bande='radio', libelle='Radio 21 cm (hydrogène)',
        mesure="Colonne d'hydrogène neutre intégrée sur la ligne de visée (raie à 21 cm, de -600 à +600 km/s)",
        unite='atomes/cm²', resolution_arcmin=16.2, longueur_onde='21 cm',
        reference='HI4PI Collaboration, Ben Bekhti et al. 2016, A&A 594, A116 (relevés EBHIS et GASS)',
        couverture_publiee='tout le ciel', echelle='log'),
}


def lire_texte(url, essais=4):
    for k in range(essais):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:      # coupure réseau : on réessaie, de plus en plus lentement
            if k == essais - 1:
                raise
            time.sleep(2 ** k)


def proprietes(hips_id):
    """Fiche du relevé (fichier properties) : adresse du serveur, repère, largeur des tuiles, ordre maximal."""
    rec = lire_texte(MOC + '?' + urllib.parse.urlencode({'ID': hips_id, 'get': 'record'}))
    p = {}
    for ligne in rec.splitlines():
        if '=' in ligne and not ligne.lstrip().startswith('#'):
            k, v = ligne.split('=', 1)
            k, v = k.strip(), v.strip()
            p.setdefault(k, v)
    # hips_service_url, _1, _2... sont des miroirs : on garde le premier qui répond vraiment (le 12/11/2026 le serveur
    # du CDS répondait 404 à toutes les tuiles, ce qui faisait croire à un ciel vide).
    adresses = [p[k] for k in sorted(p) if k.startswith('hips_service_url')]
    for adr in adresses:
        try:
            with urllib.request.urlopen(adr.rstrip('/') + '/properties', timeout=30) as r:
                if r.status == 200:
                    p['hips_service_url'] = adr
                    break
        except Exception:
            continue
    else:
        raise SystemExit(f'{hips_id} : aucun serveur ne répond ({", ".join(adresses) or "aucune adresse dans la fiche"})')
    if 'fits' not in p.get('hips_tile_format', ''):
        raise SystemExit(f'{hips_id} : pas de tuiles FITS (formats : {p.get("hips_tile_format")})')
    return p


def lire_fits(octets):
    """Image FITS d'une tuile : tableau [ligne][colonne] en float64, NaN là où rien n'est mesuré. Ligne 0 = bas de l'image
    (premier pixel écrit dans le fichier, convention FITS)."""
    entete, i = {}, 0
    while True:
        bloc = octets[i:i + 2880]
        i += 2880
        fin = False
        for j in range(0, 2880, 80):
            carte = bloc[j:j + 80].decode('ascii', 'replace')
            cle = carte[:8].strip()
            if cle == 'END':
                fin = True
                break
            if carte[8:10] == '= ':
                v = carte[10:].split('/')[0].strip().strip("'").strip()
                entete[cle] = v
        if fin:
            break
    bitpix, nx, ny = int(entete['BITPIX']), int(entete['NAXIS1']), int(entete['NAXIS2'])
    typ = {8: '>u1', 16: '>i2', 32: '>i4', 64: '>i8', -32: '>f4', -64: '>f8'}[bitpix]
    a = np.frombuffer(octets, dtype=typ, count=nx * ny, offset=i).reshape(ny, nx).astype(np.float64)
    if bitpix > 0 and 'BLANK' in entete:
        a[a == float(entete['BLANK'])] = np.nan
    a = a * float(entete.get('BSCALE', 1)) + float(entete.get('BZERO', 0))
    return a


def tuile_vers_emboite(w):
    """Pour une tuile de w × w pixels : index HEALPix emboîté (dans la tuile) de chaque pixel [ligne][colonne].

    Norme HiPS 1.0, § 4.2 et code d'Aladin (cds.tools.pixtools) : le numéro emboîté du sous-pixel s'obtient en
    entrelaçant les bits de x (bits pairs) et de y (bits impairs). Placement retenu : la ligne FITS comptée depuis le
    haut est x, la colonne FITS est y. Mesuré le 12/11/2026 sur Haslam 408 MHz et HI4PI : c'est la seule des huit
    poses de tuile qui donne un ciel continu aux bords des tuiles (voir continuite() ; l'ancienne pose, ligne = y et
    colonne = x, laissait des coutures nettes à l'écran)."""
    n = np.arange(w * w, dtype=np.int64)
    x = np.zeros_like(n)
    y = np.zeros_like(n)
    for b in range(int(math.log2(w))):
        x |= ((n >> (2 * b)) & 1) << b
        y |= ((n >> (2 * b + 1)) & 1) << b
    table = np.empty((w, w), dtype=np.int64)
    table[w - 1 - x, y] = n      # ligne FITS comptée depuis le bas dans le tableau
    return table


def telecharger(adresse, ordre, n, cache):
    chemin = os.path.join(cache, f'Norder{ordre}', f'Npix{n}.fits')
    if os.path.exists(chemin):
        with open(chemin, 'rb') as f:
            return f.read()
    url = f'{adresse}/Norder{ordre}/Dir{(n // 10000) * 10000}/Npix{n}.fits'
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                octets = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:      # tuile absente : le relevé ne couvre pas ce morceau de ciel
                return b''         # pas mise en cache : un 404 passager du serveur ne doit pas devenir un trou permanent
            if k == 4:
                raise
            time.sleep(2 ** k)
        except Exception:
            if k == 4:
                raise
            time.sleep(2 ** k)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin + '.part', 'wb') as f:
        f.write(octets)
    os.replace(chemin + '.part', chemin)
    return octets


# --- HEALPix : direction vers numéro de pixel emboîté (Górski et al. 2005, ApJ 622, 759 ; même calcul que le shader
# natif/shaders/ciel_bandes.frag). Vérifié identique à healpy.ang2pix(nest=True) sur 2 millions de directions tirées au
# hasard, Nside 1 à 4096 (12 novembre 2026).
def spread(v):
    r = np.zeros_like(v)
    for b in range(30): r |= ((v >> b) & 1) << (2*b)
    return r
def ang2pix_nest(nside, theta, phi):
    z = np.cos(theta); za = np.abs(z)
    tt = np.mod(phi, 2*np.pi) / (np.pi/2)
    face = np.zeros(z.shape, np.int64); ix = np.zeros_like(face); iy = np.zeros_like(face)
    eq = za <= 2/3
    t1 = nside*(0.5+tt); t2 = nside*z*0.75
    jp = (t1-t2).astype(np.int64); jm = (t1+t2).astype(np.int64)
    ifp = jp // nside; ifm = jm // nside
    f_eq = np.where(ifp == ifm, ifp | 4, np.where(ifp < ifm, ifp, ifm + 8))
    ix_eq = jm & (nside-1); iy_eq = nside - (jp & (nside-1)) - 1
    ntt = np.minimum(tt.astype(np.int64), 3); tp = tt - ntt
    tmp = nside*np.sqrt(3*(1-za))
    jp2 = np.minimum((tp*tmp).astype(np.int64), nside-1); jm2 = np.minimum(((1-tp)*tmp).astype(np.int64), nside-1)
    f_p = np.where(z >= 0, ntt, ntt+8)
    ix_p = np.where(z >= 0, nside-jm2-1, jp2); iy_p = np.where(z >= 0, nside-jp2-1, jm2)
    face = np.where(eq, f_eq, f_p); ix = np.where(eq, ix_eq, ix_p); iy = np.where(eq, iy_eq, iy_p)
    return face*nside*nside + spread(ix) + 2*spread(iy)


# Équatorial (ICRS) vers galactique : matrice de Hipparcos (ESA 1997, vol. 1, § 1.5.3).
GAL = np.array([[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132],
                [+0.4941094278755837, -0.4448296299600112, +0.7469822444972189],
                [-0.8676661490190047, -0.1980763734312015, +0.4559837761750669]])


def contraste_plan(carte, nside, galactique):
    """Rapport entre la médiane des pixels près du plan de la Galaxie (|b| < 3°) et loin de lui (|b| > 40°). Pour une carte
    bien assemblée d'un relevé qui voit la Galaxie, le plan ressort nettement ; mal orientée, il se brouille."""
    rng = np.random.default_rng(0)
    l = rng.uniform(0, 2 * np.pi, 400_000)
    sb = rng.uniform(-1, 1, 400_000)
    b = np.arcsin(sb)
    v = np.stack([np.cos(b) * np.cos(l), np.cos(b) * np.sin(l), sb])
    if not galactique:
        v = GAL.T @ v      # galactique vers équatorial
    th = np.arccos(np.clip(v[2], -1, 1))
    ph = np.arctan2(v[1], v[0])
    val = carte[ang2pix_nest(nside, th, ph)]
    pres, loin = val[np.abs(b) < np.radians(3)], val[np.abs(b) > np.radians(40)]
    pres, loin = pres[np.isfinite(pres)], loin[np.isfinite(loin)]
    if len(pres) < 100 or len(loin) < 100:
        return float('nan')
    return float(np.median(pres) / np.median(loin))


def continuite(carte, nside):
    """Saut moyen du logarithme entre pixels voisins, face HEALPix par face. Le relevé est lissé à sa finesse (bien plus
    large qu'un pixel de la carte) : une tuile mal posée crée des coutures à ses bords et fait monter ce saut."""
    i = np.arange(nside, dtype=np.int64)
    ix, iy = np.meshgrid(i, i, indexing='ij')
    sous = spread(ix) + 2 * spread(iy)
    lg = np.log(np.maximum(carte.astype(np.float64), 1e-30))
    total = 0.0
    for f in range(12):
        im = lg[f * nside * nside + sous]
        total += np.nanmean(np.abs(np.diff(im, axis=0))) + np.nanmean(np.abs(np.diff(im, axis=1)))
    return total / 12


def orientations(w):
    """Les huit façons de poser une tuile (miroirs et transposée) ; 0 = celle de la norme."""
    t0 = tuile_vers_emboite(w)
    res = []
    for o in range(8):
        t = t0
        if o & 1: t = t[::-1, :]
        if o & 2: t = t[:, ::-1]
        if o & 4: t = t.T
        res.append(np.ascontiguousarray(t))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sortie')
    ap.add_argument('nom', nargs='?')
    ap.add_argument('--ordre', type=int, default=2)
    ap.add_argument('--simultanes', type=int, default=8)
    ap.add_argument('--cache')
    ap.add_argument('--liste', action='store_true')
    a = ap.parse_args()
    if a.liste or not a.nom:
        for k, r in RELEVES.items():
            print(f'{k:12s} {r["libelle"]:28s} {r["hips"]}')
        return
    r = RELEVES[a.nom]
    p = proprietes(r['hips'])
    adresse = p['hips_service_url'].rstrip('/')
    w = int(p.get('hips_tile_width', 512))
    ordre_max = int(p.get('hips_order', a.ordre))
    ordre = min(a.ordre, ordre_max)
    repere = p.get('hips_frame', 'equatorial')
    nside = w << ordre
    ntuiles = 12 * 4 ** ordre
    cache = a.cache or os.path.join(a.sortie, 'cache_hips', a.nom)
    print(f'{r["libelle"]} : {r["hips"]}, serveur {adresse}, repère {repere}, tuiles {w} px, ordre {ordre} '
          f'(maximum {ordre_max}), Nside {nside}, {ntuiles} tuiles')

    tables = orientations(w)
    table = tables[0]
    carte = np.full(12 * nside * nside, np.nan, dtype=np.float32)
    absentes = 0
    t0 = time.time()
    with cf.ThreadPoolExecutor(a.simultanes) as ex:
        futurs = {ex.submit(telecharger, adresse, ordre, n, cache): n for n in range(ntuiles)}
        for k, fu in enumerate(cf.as_completed(futurs)):
            n = futurs[fu]
            octets = fu.result()
            if not octets:
                absentes += 1
                continue
            img = lire_fits(octets)
            if img.shape != (w, w):
                raise SystemExit(f'tuile {n} : {img.shape}, attendu {w} × {w}')
            carte[n * w * w + table] = img.astype(np.float32)
            if k % 50 == 0:
                print(f'  {k + 1}/{ntuiles} tuiles, {time.time() - t0:.0f} s', flush=True)

    if absentes == ntuiles:
        raise SystemExit('toutes les tuiles sont absentes : serveur en panne ? (vider le cache avant de relancer)')
    mesure = np.isfinite(carte)
    couverture = float(mesure.mean())
    vals = carte[mesure]
    stats = dict(min=float(vals.min()), max=float(vals.max()),
                 p01=float(np.percentile(vals, 1)), p50=float(np.percentile(vals, 50)), p99=float(np.percentile(vals, 99)),
                 p999=float(np.percentile(vals, 99.9)))
    # contrôle d'assemblage : le plan de la Galaxie doit ressortir mieux avec la convention de la norme qu'avec les sept
    # autres orientations des tuiles (réécrites ici à partir de la carte, sans retélécharger).
    galactique = repere.startswith('gal')
    contrastes, sauts = [], []
    t0r = tables[0].ravel()
    for o, t in enumerate(tables):
        if o == 0:
            c = carte
        else:
            c = np.empty_like(carte).reshape(ntuiles, w * w)
            c[:, t.ravel()] = carte.reshape(ntuiles, w * w)[:, t0r]
            c = c.ravel()
        contrastes.append(contraste_plan(c, nside, galactique))
        sauts.append(continuite(c, nside))
    print('  contraste plan / hautes latitudes, orientations 0 à 7 : ' + ', '.join(f'{x:.3g}' for x in contrastes))
    print('  saut moyen entre pixels voisins (log), orientations 0 à 7 : ' + ', '.join(f'{x:.4f}' for x in sauts))
    if int(np.argmin(sauts)) != 0:
        print(f'  ATTENTION : la pose {int(np.argmin(sauts))} est plus continue que la pose retenue (0) : tuiles mal posées')

    meta = dict(r, nom=a.nom, repere=repere, nside=nside, ordre_hips=ordre, ordre_hips_max=ordre_max,
                largeur_tuile=w, serveur=adresse, couverture_mesuree=couverture, tuiles_absentes=absentes,
                stats=stats, contraste_plan=contrastes, resolution_carte_arcmin=math.degrees(math.sqrt(4 * math.pi / (12 * nside * nside))) * 60,
                date=time.strftime('%Y-%m-%d'), outil='pipeline/natif/ciel_bandes.py')
    js = json.dumps(meta, ensure_ascii=False).encode('utf-8')
    os.makedirs(a.sortie, exist_ok=True)
    chemin = os.path.join(a.sortie, f'ciel_{a.nom}.bin')
    with open(chemin + '.part', 'wb') as f:
        f.write(b'UNIVSKY1')
        f.write(struct.pack('<IIII', nside, 1 if repere.startswith('gal') else 0, len(js), 0))
        f.write(js)
        f.write(b'\0' * ((-f.tell()) % 16))
        f.write(carte.tobytes())
    os.replace(chemin + '.part', chemin)
    print(f'Écrit {chemin} : Nside {nside}, couverture {couverture * 100:.2f} %, tuiles absentes {absentes}, '
          f'valeurs {stats["p01"]:.4g} à {stats["p999"]:.4g} {r["unite"]} (1 % à 99,9 %), contraste du plan {contrastes[0]:.3g}')


if __name__ == '__main__':
    main()
