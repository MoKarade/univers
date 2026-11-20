"""Superstructures (superamas, murs, bassins) -> C:\\tmp\\vue-sources\\superstructures.tsv

README
------
Repère de sortie : coordonnées supergalactiques cartésiennes SGX, SGY, SGZ en Mpc
(repère supergalactique de de Vaucouleurs, via astropy.coordinates.Supergalactic),
origine = Soleil. Constante de Hubble : H0 = 74.6 km/s/Mpc (h = 0.746), celle de
Cosmicflows-4 (Tully et al. 2023, ApJ 944, 94) utilisée par l'appli.

Conversions (CALCUL, pas mesure) :
  * Catalogue Liivamägi : les distances publiées sont comobiles en Mpc/h
    (Omega_m = 0.27, Omega_L = 0.73, H0 = 100 h). Mpc = (Mpc/h) / 0.746.
  * Redshift publié z -> distance comobile avec astropy FlatLambdaCDM(H0=74.6,
    Om0=0.3) [choix de modèle de ce script ; Om0 = 0.3 indiqué ici, pas tiré
    de CF4]. Une vitesse cz publiée est convertie en z = cz / c (héliocentrique,
    sans correction de flot : écart de quelques % possible à cz < 5000 km/s).
  * Tailles publiées en Mpc/h -> /0.746 ; en Mpc pour H0 = 70 ou 75 ->
    multipliées par 70/74.6 ou 75/74.6.

Sources :
  1. Liivamägi L.J., Tempel E., Saar E. 2012, A&A 539, A80, « SDSS DR7
     superclusters. The catalogues », VizieR J/A+A/539/A80,
     doi:10.26093/cds/vizier.35390080 ; téléchargé par le miroir
     https://vizier.cfa.harvard.edu. Quatre tables : main50 (982, seuil fixe
     D = 5.0), mainadap (1313, seuil adaptatif), lrg44 (3761, LRG seuil 4.4),
     lrgadap (2701, LRG adaptatif). ATTENTION : ce sont quatre découpages du
     MÊME ciel : une structure apparaît dans plusieurs tables. Pour l'affichage,
     prendre mainadap (z < 0.2) + lrgadap (LRG, z jusqu'à ~0.5), pas les quatre.
     Position = centre de masse (RA2deg, DE2deg, Dist2) ; pic de densité
     (RA1, DE1, Dist1) mis dans la colonne membres_sg ; taille = Diam (Mpc/h).
  2. Structures nommées : voir la liste NOMMEES plus bas ; chaque ligne porte
     sa référence. Positions d'amas résolues par Sesame (SIMBAD) sur le miroir
     CfA, réponse brute gardée dans brut/sesame/ avec la référence du redshift.
  3. Bassins d'attraction CF4 : Dupuy A., Courtois H.M. 2023, A&A Letters
     (arXiv:2305.02339), « Dynamic cosmography of the local Universe: Laniakea
     and five more watershed superclusters », Table 1 (reconstruction galaxies
     individuelles), attracteurs en Mpc/h et volumes en 10^6 (Mpc/h)^3.
     [À vérifier] l'article dit H0 = 74.6 mais donne les positions en Mpc/h ;
     ce script applique Mpc = valeur / 0.746. Taille = diamètre de la sphère de
     même volume (CALCUL, le bassin n'est pas sphérique).

Colonnes :
  nom, type (supercluster / wall / basin / supercluster-complex / grb-cluster),
  catalogue, sgx_mpc, sgy_mpc, sgz_mpc, ra_deg, dec_deg, z, dist_mpc,
  taille_mpc (plus grande dimension, Mpc pour h=0.746), taille_publiee
  (texte tel que publié), n_gal, membres_sg (liste « x,y,z;x,y,z » en Mpc de
  points membres ou du pic de densité), source, statut, conversion.
Statut : « mesure » = catalogue publié converti ; « derive » = centre ou taille
  construit ici à partir de valeurs publiées (méthode dans « conversion ») ;
  « debattu » = existence contestée.
"""

import csv
import math
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord, Supergalactic
from astropy.cosmology import FlatLambdaCDM

SORTIE = Path(r"C:\tmp\vue-sources")
BRUT = SORTIE / "brut"
VIZIER = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"
SESAME = "https://vizier.cfa.harvard.edu/viz-bin/nph-sesame/-oxp/SNV?"
H = 0.746
H0 = 74.6
C_KMS = 299792.458
COSMO = FlatLambdaCDM(H0=H0, Om0=0.3)
TABLES_LIIVAMAGI = ["main50", "mainadap", "lrg44", "lrgadap"]
LIIVAMAGI_REF = ("Liivamagi, Tempel & Saar 2012, A&A 539, A80; VizieR J/A+A/539/A80 "
                 "doi:10.26093/cds/vizier.35390080")
DC23 = "Dupuy & Courtois 2023, A&A Letters, arXiv:2305.02339, Table 1 (CF4 galaxies)"

COLONNES = ["nom", "type", "catalogue", "sgx_mpc", "sgy_mpc", "sgz_mpc", "ra_deg",
            "dec_deg", "z", "dist_mpc", "taille_mpc", "taille_publiee", "n_gal",
            "membres_sg", "source", "statut", "conversion"]


# ---------------------------------------------------------------- outils
def sg_xyz(ra: float, dec: float, dist: float, galactique: bool = False) -> tuple:
    """(RA, Dec) ou (l, b) en degrés + distance Mpc -> SGX, SGY, SGZ en Mpc."""
    frame = "galactic" if galactique else "icrs"
    if galactique:
        c = SkyCoord(l=ra * u.deg, b=dec * u.deg, frame=frame)
    else:
        c = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame=frame)
    sg = c.transform_to(Supergalactic())
    lon, lat = sg.sgl.rad, sg.sgb.rad
    return (dist * math.cos(lat) * math.cos(lon),
            dist * math.cos(lat) * math.sin(lon),
            dist * math.sin(lat))


def dist_z(z: float) -> float:
    return float(COSMO.comoving_distance(z).to(u.Mpc).value)


def fmt(x, n: int = 2) -> str:
    return "" if x is None else f"{x:.{n}f}"


def xyz_txt(p: tuple) -> str:
    return ",".join(f"{v:.1f}" for v in p)


def get(url: str, chemin: Path) -> str:
    """Télécharge une fois, puis relit la copie brute."""
    if not chemin.exists():
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=300) as r:
            chemin.write_bytes(r.read())
    return chemin.read_text(encoding="utf-8", errors="replace")


def sesame(nom: str) -> dict:
    """Position + redshift SIMBAD (via Sesame) d'un objet, avec la référence du z."""
    fichier = BRUT / "sesame" / (re.sub(r"[^A-Za-z0-9+-]", "_", nom) + ".xml")
    t = get(SESAME + urllib.parse.quote(nom), fichier)
    ra = re.search(r"<jradeg>([^<]+)", t)
    de = re.search(r"<jdedeg>([^<]+)", t)
    z = re.search(r"<z><v>([^<]+)</v>.*?<r>([^<]*)</r>", t, re.S)
    if not (ra and de):
        raise RuntimeError(f"Sesame ne résout pas {nom}")
    return {"ra": float(ra.group(1)), "dec": float(de.group(1)),
            "z": float(z.group(1)) if z else None,
            "zref": z.group(2).replace("&amp;", "&") if z else ""}


# ---------------------------------------------------------------- Liivamägi
def lire_vizier_tsv(texte: str) -> list:
    lignes = [l for l in texte.splitlines() if l and not l.startswith("#")]
    entete = lignes[0].split("\t")
    # lignes[1] = unités, lignes[2] = tirets
    return [dict(zip(entete, [c.strip() for c in l.split("\t")])) for l in lignes[3:]]


def liivamagi() -> tuple:
    """Renvoie (lignes de sortie, index UID -> ligne mainadap)."""
    sortie, index = [], {}
    for t in TABLES_LIIVAMAGI:
        url = f"{VIZIER}?-source=J/A%2BA/539/A80/{t}&-out.max=unlimited&-out.all"
        rows = lire_vizier_tsv(get(url, BRUT / "liivamagi2012" / f"{t}.tsv"))
        for r in rows:
            d2 = float(r["Dist2"]) / H
            p = sg_xyz(float(r["RA2deg"]), float(r["DE2deg"]), d2)
            pic = sg_xyz(float(r["RA1"]), float(r["DE1"]), float(r["Dist1"]) / H)
            ligne = {
                "nom": f"SCl {r['UID']}", "type": "supercluster",
                "catalogue": f"Liivamagi2012/{t}",
                "sgx_mpc": fmt(p[0]), "sgy_mpc": fmt(p[1]), "sgz_mpc": fmt(p[2]),
                "ra_deg": r["RA2deg"], "dec_deg": r["DE2deg"], "z": r["mgz"],
                "dist_mpc": fmt(d2), "taille_mpc": fmt(float(r["Diam"]) / H),
                "taille_publiee": f"Diam {r['Diam']} Mpc/h", "n_gal": r["Ngal"],
                "membres_sg": "pic:" + xyz_txt(pic), "source": LIIVAMAGI_REF,
                "statut": "mesure" + (" (touche le bord du relevé)" if r["Edge"] == "1" else ""),
                "conversion": "centre de masse RA2/DE2/Dist2 ; Mpc/h / 0.746 ; z = redshift de la galaxie repère",
            }
            sortie.append(ligne)
            if t == "mainadap":
                index[r["UID"]] = ligne
        print(f"  Liivamägi {t} : {len(rows)} superamas")
    return sortie, index


# ---------------------------------------------------------------- structures nommées
def ligne_nommee(nom, typ, centre, taille, taille_pub, membres, source, statut, conv, z=None):
    """centre = (ra, dec, dist_mpc) ou None si non publié."""
    if centre is None:
        p, ra, dec, d = (None, None, None), None, None, None
    else:
        ra, dec, d = centre
        p = sg_xyz(ra, dec, d)
    return {"nom": nom, "type": typ, "catalogue": "nommee",
            "sgx_mpc": fmt(p[0]), "sgy_mpc": fmt(p[1]), "sgz_mpc": fmt(p[2]),
            "ra_deg": fmt(ra, 4), "dec_deg": fmt(dec, 4), "z": fmt(z, 4),
            "dist_mpc": fmt(d), "taille_mpc": fmt(taille), "taille_publiee": taille_pub,
            "n_gal": "", "membres_sg": ";".join(xyz_txt(m) for m in membres),
            "source": source, "statut": statut, "conversion": conv}


def amas(nom: str) -> tuple:
    """Amas résolu par Sesame -> (ra, dec, dist, z, ref)."""
    s = sesame(nom)
    return s["ra"], s["dec"], dist_z(s["z"]), s["z"], s["zref"]


def moyenne(points: list) -> tuple:
    return tuple(float(v) for v in np.mean(np.array(points), axis=0))


def sg_vers_radec(p: tuple) -> tuple:
    """SG cartésien -> (ra, dec, dist) pour stocker un centre dérivé."""
    x, y, z = p
    d = math.sqrt(x * x + y * y + z * z)
    c = SkyCoord(sgl=math.degrees(math.atan2(y, x)) * u.deg,
                 sgb=math.degrees(math.asin(z / d)) * u.deg, frame=Supergalactic())
    icrs = c.icrs
    return float(icrs.ra.deg), float(icrs.dec.deg), d


def nommees(index: dict) -> list:
    L = []
    sesame_note = "position + z SIMBAD via Sesame (ref. z : {})"

    # Shapley — cœur A3558 ; plan principal 30 x 75 Mpc/h (Proust et al. 2006)
    ra, de, d, z, ref = amas("Abell 3558")
    L.append(ligne_nommee(
        "Shapley Supercluster", "supercluster", (ra, de, d), 75 / H,
        "plan principal >= 30 x 75 h^-1 Mpc (limité par le relevé)", [],
        "Proust et al. 2006, A&A 447, 133 ; centre = Abell 3558 (Raychaudhury 1989, Nature 342, 251)",
        "derive", "centre = amas A3558, " + sesame_note.format(ref), z))

    # Coma — Coma (A1656) + Leo (A1367) ; Gregory & Thompson 1978
    a = amas("Abell 1656")
    b = amas("Abell 1367")
    pa, pb = sg_xyz(a[0], a[1], a[2]), sg_xyz(b[0], b[1], b[2])
    c = sg_vers_radec(moyenne([pa, pb]))
    L.append(ligne_nommee(
        "Coma Supercluster", "supercluster", c, math.dist(pa, pb),
        "non chiffrée ici ; défini par Coma (A1656) + A1367", [pa, pb],
        "Gregory & Thompson 1978, ApJ 222, 784",
        "derive", "centre = milieu A1656-A1367 ; taille = séparation des deux amas ; "
        + sesame_note.format(a[4] + " / " + b[4]), (a[3] + b[3]) / 2))

    # Hercules — A2151 (cœur) ; taille = bassin CF4 (ligne bassin à part)
    ra, de, d, z, ref = amas("Abell 2151")
    L.append(ligne_nommee(
        "Hercules Supercluster", "supercluster", (ra, de, d), None,
        "voir bassin CF4 « Hercules » (Dupuy & Courtois 2023)", [],
        "centre = amas d Hercule A2151 (amas A2147/A2151/A2152, identification classique [À vérifier]) ; taille : Dupuy & Courtois 2023",
        "derive", "centre = amas A2151, " + sesame_note.format(ref), z))

    # Perseus-Pisces — Perseus (A426) ; Haynes & Giovanelli 1986
    ra, de, d, z, ref = amas("Abell 426")
    L.append(ligne_nommee(
        "Perseus-Pisces Supercluster", "supercluster", (ra, de, d), None,
        "voir bassin CF4 « Perseus-Pisces » (Dupuy & Courtois 2023)", [],
        "Haynes & Giovanelli 1986, ApJ 306, L55 ; centre = amas de Persée A426",
        "derive", "centre = amas A426, " + sesame_note.format(ref), z))

    # Horologium-Reticulum — Fleenor et al. 2005 : centre 03h19m -50°02', 17000-22500 km/s, > 12° x 12°
    z_mid = (17000 + 22500) / 2 / C_KMS
    d = dist_z(z_mid)
    radial = dist_z(22500 / C_KMS) - dist_z(17000 / C_KMS)
    transverse = d * math.radians(12)
    L.append(ligne_nommee(
        "Horologium-Reticulum Supercluster", "supercluster",
        (15 * (3 + 19 / 60), -(50 + 2 / 60), d), max(radial, transverse),
        "> 12 deg x 12 deg sur le ciel, cz 17000-22500 km/s", [],
        "Fleenor et al. 2005, AJ 130, 957 (astro-ph/0505361)",
        "derive", "z = milieu de 17000-22500 km/s / c ; taille = max(étendue radiale, 12 deg transverse)",
        z_mid))

    # Laniakea — Tully et al. 2014 : ~160 Mpc ; attracteur CF4 = ligne bassin ; Norma A3627 au cœur
    ra, de, d, z, ref = amas("Abell 3627")
    L.append(ligne_nommee(
        "Great Attractor (Norma, A3627)", "supercluster", (ra, de, d), None, "",
        [], "Kraan-Korteweg et al. 1996, Nature 379, 519 (A3627) ; cœur de Laniakea (Tully et al. 2014, Nature 513, 71)",
        "mesure", sesame_note.format(ref), z))

    # CfA2 Great Wall — Geller & Huchra 1989 : >= 60 x 170 h^-1 Mpc ; Coma est dans le mur
    a = amas("Abell 1656")
    L.append(ligne_nommee(
        "CfA2 Great Wall", "wall", (a[0], a[1], a[2]), 170 / H,
        "étendue minimale 60 h^-1 Mpc x 170 h^-1 Mpc", [],
        "Geller & Huchra 1989, Science 246, 897",
        "derive", "centre placé sur l'amas de Coma (dans le mur) : approximation ; "
        "taille 170/0.746", a[3]))

    # Sloan Great Wall — Gott et al. 2005 (1.37 milliard a.l.) ; membres = Einasto et al. 2011 Table 1
    ids = ["184+003+007", "173+014+008", "202-001+008", "152-000+009", "187+008+008",
           "170+000+010", "175+005+009", "159+004+006", "168+002+007", "214+001+005",
           "189+003+008", "198+007+009", "157+003+007"]
    membres = []
    for pref in ids:
        trouve = [v for k, v in index.items() if k.startswith(pref)]
        if len(trouve) != 1:
            raise RuntimeError(f"SGW : membre {pref} introuvable ou ambigu")
        membres.append(tuple(float(trouve[0][k]) for k in ("sgx_mpc", "sgy_mpc", "sgz_mpc")))
    gly_mpc = 1.37e9 / 3.26156e6
    L.append(ligne_nommee(
        "Sloan Great Wall", "wall", sg_vers_radec(moyenne(membres)), gly_mpc,
        "1.37 milliard d'années-lumière (Gott et al. 2005)", membres,
        "Gott et al. 2005, ApJ 624, 463 ; membres : Einasto et al. 2011, ApJ 736, 51, Table 1",
        "derive", "centre = moyenne des 13 superamas membres (centres de masse Liivamägi mainadap, "
        "appariés par préfixe d'identifiant) ; taille = 1.37e9 al / 3.26156e6 al/Mpc (h non précisé par Gott)"))

    # Saraswati — Bagchi et al. 2017 : z ~ 0.28, >= 200 Mpc ; centre A2631 ; 48 amas WHL (Table 1)
    saraswati = [(354.41553, 0.27137, 0.2772), (355.89862, 0.33093, 0.2694),
                 (356.59955, 0.74942, 0.2746), (355.27872, 0.30925, 0.2768),
                 (354.40656, -0.67781, 0.2876), (356.86499, -0.15381, 0.2639),
                 (350.62363, -0.37294, 0.2728), (351.68036, 1.13423, 0.2774),
                 (351.88278, 0.94281, 0.2788), (356.51950, -0.18573, 0.2665),
                 (357.56891, 0.88373, 0.2767), (352.86020, 0.61525, 0.2739),
                 (357.83884, 0.61691, 0.2775), (358.78690, 0.75341, 0.2789),
                 (354.03653, -1.18347, 0.2650), (352.03851, 0.18593, 0.2768),
                 (356.45068, -1.12771, 0.2797), (356.19455, -0.08880, 0.2674),
                 (354.56683, 0.11680, 0.2711), (358.25555, -0.23089, 0.2779),
                 (356.01273, 0.22644, 0.2714), (356.86264, 0.52773, 0.2729),
                 (353.99393, -0.48434, 0.2700), (356.32980, -0.05331, 0.2665),
                 (355.10202, -0.09299, 0.2761), (358.93271, -0.00393, 0.2752),
                 (353.62631, -0.98501, 0.2772), (355.43375, -0.67539, 0.2680),
                 (357.93292, 0.56078, 0.2703), (357.23520, -0.89120, 0.2793),
                 (354.97913, -0.43282, 0.2769), (351.02548, 0.36311, 0.2780),
                 (352.66733, 0.60940, 0.2757), (356.67987, 0.83429, 0.2637),
                 (351.58939, 0.16173, 0.2870), (353.87994, -0.88882, 0.2974),
                 (352.81964, 0.72678, 0.2812), (352.17755, 0.82753, 0.2784),
                 (353.87866, -0.53116, 0.2764), (356.76236, -0.08544, 0.2655),
                 (358.12292, 0.60623, 0.2698), (355.63776, -0.28874, 0.2770),
                 (358.60349, 0.81066, 0.2805), (351.32236, 0.27741, 0.2767),
                 (351.95999, -0.64258, 0.2856), (358.44800, 0.81641, 0.2787),
                 (355.18701, 0.31234, 0.2982), (357.44406, 0.64598, 0.2705)]
    mem = [sg_xyz(r, dd, dist_z(zz)) for r, dd, zz in saraswati]
    L.append(ligne_nommee(
        "Saraswati Supercluster", "supercluster", (354.41553, 0.27137, dist_z(0.2772)), 200,
        "au moins 200 Mpc ; 43 amas riches, ~2e16 Msun", mem,
        "Bagchi et al. 2017, ApJ 844, 25 (arXiv:1707.03082), Table 1 (48 amas WHL < 90 Mpc d'A2631)",
        "derive", "centre = Abell 2631 (BCG, z 0.2772) ; membres = 48 BCG de la Table 1 (z spectro)",
        0.2772))

    # BOSS Great Wall — Lietzen et al. 2016 : z 0.47, murs 186 et 173 h^-1 Mpc, système 271 h^-1 Mpc
    planck = [(151.62, 54.78), (150.56, 58.32)]  # PSZ2 G151.62+54.78 (A), G150.56+58.32 (C)
    dz = dist_z(0.47)
    mem = [sg_xyz(l, b, dz, galactique=True) for l, b in planck]
    L.append(ligne_nommee(
        "BOSS Great Wall", "supercluster-complex", sg_vers_radec(moyenne(mem)), 271.1 / H,
        "système 271.1 h^-1 Mpc ; murs A 186.1, B 172.9 ; C 63.8, D 90.6 h^-1 Mpc ; ~2e17 h^-1 Msun",
        mem, "Lietzen et al. 2016, A&A 588, L4 ; Einasto et al. 2017, A&A 603, A5 (amas Planck PSZ2)",
        "derive", "aucune position publiée en chiffres : centre = milieu des 2 amas Planck "
        "PSZ2 G151.62+54.78 (sup. A) et G150.56+58.32 (sup. C), (l,b) lus dans leur nom, à z = 0.47",
        0.47))

    # Hercules–Corona Borealis Great Wall — Horváth et al. 2014 (GRB), débattu
    L.append(ligne_nommee(
        "Hercules-Corona Borealis Great Wall", "grb-cluster", None, 2500,
        "environ 2000-3000 Mpc, 1.6 < z < 2.1, ~1/8 du ciel (Hercule, Couronne boréale)", [],
        "Horváth, Hakkila & Bagoly 2014, A&A 561, L12 ; Horváth et al. 2015 (arXiv:1510.01933)",
        "debattu", "AUCUN centre chiffré publié (carte seulement) : position laissée vide ; "
        "taille = milieu de 2000-3000 Mpc ; existence contestée (amas de 14 sursauts gamma)",
        (1.6 + 2.1) / 2))

    # South Pole Wall — Pomarède et al. 2020 : ~0.11c ~ 420 Mpc (H0=75), pic au pôle sud céleste
    z_spw = 11800 / C_KMS
    L.append(ligne_nommee(
        "South Pole Wall", "wall", (0.0, -90.0, dist_z(z_spw)), 420 * 75 / H0,
        "bout à bout ~0.11c ~ 420 Mpc (H0 = 75)", [],
        "Pomarède et al. 2020, ApJ 897, 133 (arXiv:2007.04414)",
        "derive", "centre = pic « Chamaeleon+11.8 » au pôle sud céleste, cz pris = 11800 km/s "
        "(lu dans le nom du pic, [À vérifier]) ; taille 420 x 75/74.6", z_spw))

    # Vela — Kraan-Korteweg et al. 2017 : l=272.5, b=0, cz ~18000, 25° x 20° ~ 115 x 90 h70 Mpc
    z_v = 18000 / C_KMS
    L.append(ligne_nommee(
        "Vela Supercluster", "supercluster", sg_vers_radec(sg_xyz(272.5, 0.0, dist_z(z_v), True)),
        115 * 70 / H0, "au moins 25 deg x 20 deg ~ 115 x 90 h70^-1 Mpc, cz ~ 18000 km/s", [],
        "Kraan-Korteweg et al. 2017, MNRAS 466, L29 (arXiv:1611.04615)",
        "derive", "centre (l, b) = (272.5, 0) à cz 18000 km/s ; taille 115 x 70/74.6", z_v))
    return L


def bassins_cf4() -> list:
    """Bassins d'attraction CF4 (Dupuy & Courtois 2023, Table 1), Mpc/h -> Mpc."""
    table = [("Laniakea", (-62, -8, 39), 1.9), ("Apus", (-125, -23, -31), 9.5),
             ("Hercules", (-39, 70, 78), 3.1), ("Lepus", (-62, -39, -109), 8.1),
             ("Perseus-Pisces", (47, -23, -31), 4.8), ("Shapley", (-141, 62, -16), 7.9)]
    L = []
    for nom, p, vol in table:
        pm = tuple(v / H for v in p)
        ra, dec, d = sg_vers_radec(pm)
        diam = 2 * (3 * vol * 1e6 / (4 * math.pi)) ** (1 / 3) / H
        extra = " ; Tully et al. 2014 (Nature 513, 71) : ~160 Mpc, ~1e17 Msun" if nom == "Laniakea" else ""
        L.append(ligne_nommee(
            f"{nom} (bassin CF4)", "basin", (ra, dec, d), diam,
            f"attracteur ({p[0]}, {p[1]}, {p[2]}) Mpc/h ; volume {vol}e6 (Mpc/h)^3" + extra, [],
            DC23, "mesure (attracteur) / derive (taille)",
            "Mpc/h / 0.746 [unité À vérifier] ; taille = diamètre de la sphère de même volume"))
    return L


def main() -> int:
    lignes, index = liivamagi()
    lignes += nommees(index) + bassins_cf4()
    with open(SORTIE / "superstructures.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLONNES, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(lignes)
    print(f"superstructures.tsv : {len(lignes)} lignes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
