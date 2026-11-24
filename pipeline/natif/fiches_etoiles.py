#!/usr/bin/env python3
"""Fiches des ÉTOILES sélectionnables de l'appli PC « Univers » -> C:\\tmp\\fiches\\etoiles.tsv

Demande de Marc (20/11/2026) : la fiche d'une étoile montre toutes les grandeurs publiques, avec incertitudes, source et
référence ; les sorties de modèles sont dites « modèle ». Format : docs/fiches-format.md (une ligne par champ, lignes d'une
même étoile consécutives). AUCUNE valeur inventée : une case vide de la source n'est pas écrite.

Étoiles couvertes (les clés sont les noms montrés par l'appli, natif/src/simulation.h) :
  - etoiles_noms.tsv          : 33 étoiles nommées (rang, nom français, distance al). Le nom français est relié à un
                                identifiant SIMBAD par la table NOMS_SIMBAD ci-dessous ; chaque résolution est vérifiée
                                (distance d'après la parallaxe SIMBAD comparée à la 3e colonne, écart imprimé).
  - etoiles_planetes_noms.tsv : ~2 200 étoiles hôtes de planètes (rang, nom d'hôte NASA, distance, nb de planètes).
                                Une hôte dont le rang est déjà dans etoiles_noms.tsv est montrée par l'appli sous son nom
                                français : ses lignes sont écrites sous ce nom.

Sources (requêtes TAP/ADQL en lots, réponses brutes gardées dans C:\\tmp\\fiches\\cache\\etoiles\\) :
  1) SIMBAD (CDS, Wenger et al. 2000) : https://simbad.cds.unistra.fr/simbad/sim-tap/sync ; si le serveur du CDS ne répond
     pas, son miroir officiel https://simbad.harvard.edu/simbad/sim-tap/sync (mêmes tables). Tables basic (type d'objet,
     type spectral + qualité + bibcode, parallaxe ±, mouvement propre + ellipse d'erreur, vitesse radiale ±, position),
     flux (magnitudes U B V R I J H K G ± et bibcode), ids (autres noms), otypedef (libellé des types).
     Résolution d'une hôte : identifiant « Gaia DR3 » donné par la NASA, sinon nom d'hôte, « * nom », « NAME nom »,
     nom HD, nom HIP, TIC.
  2) Gaia DR3 (ESA, Gaia Collaboration, Vallenari et al. 2023) : https://gea.esac.esa.int/tap-server/tap/sync, par
     source_id lu dans SIMBAD (sinon celui de la NASA). gaiadr3.gaia_source (mesures astrométriques et photométriques,
     RUWE, non_single_star, variabilité, vbroad) et gaiadr3.astrophysical_parameters. Les sorties Apsis (GSP-Phot,
     GSP-Spec, ESP-HS, ESP-UCD, FLAME : température, gravité, métallicité, rayon, luminosité, masse, âge, distance
     photométrique, extinction…) sont des MODÈLES (statut « modèle », groupe « Modèles et hypothèses »). Bornes
     lower/upper (16e et 84e centiles) -> incertitude dissymétrique +a/-b.
     Incertitude des magnitudes G, BP, RP : calculée, σ = 1,0857 / (flux/σ_flux) combinée au point zéro
     (0,0027553 ; 0,0027901 ; 0,0037793 mag, Riello et al. 2021).
  3) NASA Exoplanet Archive, table pscomppars (DOI 10.26133/NEA13) : https://exoplanetarchive.ipac.caltech.edu/TAP/sync.
     Paramètres de l'étoile (st_*, sy_*) avec err1/err2, limites et référence (*_reflink) ; puis, dans le groupe
     « Planètes », chaque planète (libellé préfixé du nom de la planète). Statuts :
       - « Calculated Value » de l'archive (docs/pscp_calc.html) : rayon ou masse de planète tirés de la relation
         masse-rayon de Chen & Kipping 2017 -> « modèle » ; température d'équilibre (albédo nul, redistribution
         complète) -> « modèle » ; densité, luminosité, flux reçu, séparation angulaire -> « calculé » (formule en
         source), sauf densité bâtie sur une masse ou un rayon « modèle » -> « modèle » ;
       - pl_bmassprov = « M-R relationship » -> masse « modèle » ; « Msini » -> libellé « masse minimale (M sin i) » ;
       - toute température d'équilibre de planète -> « modèle » (elle suppose un albédo et une répartition de la
         chaleur) ;
       - masse et âge de l'étoile -> « modèle » (isochrones ou relations empiriques dans les articles cités) ;
       - le reste : « mesuré » (valeur publiée ajustée sur des observations).
     pscomppars peut citer des paramètres d'étoile différents selon la planète : chaque valeur distincte est écrite,
     avec en libellé la ou les planètes concernées.
  Grandeur déduite par ce script : distance d'après la parallaxe SIMBAD, d (al) = 3,2615638 / parallaxe (″),
  incertitude dissymétrique 1/(p-σ), 1/(p+σ) ; non écrite si la parallaxe vaut moins de 3 fois son incertitude.

Usage : python fiches_etoiles.py [dossier des données de l'appli (défaut C:\\dev\\Univers-PC)] [sortie (défaut
        C:\\tmp\\fiches\\etoiles.tsv)]. Relancer réutilise le cache (supprimer C:\\tmp\\fiches\\cache\\etoiles pour
        tout redemander).
"""
import csv
import datetime
import hashlib
import html
import io
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DONNEES = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\dev\Univers-PC")
SORTIE = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(r"C:\tmp\fiches\etoiles.tsv")
CACHE = Path(r"C:\tmp\fiches\cache\etoiles")

SIMBAD_TAP = ["https://simbad.cds.unistra.fr/simbad/sim-tap/sync", "https://simbad.harvard.edu/simbad/sim-tap/sync"]
GAIA_TAP = ["https://gea.esac.esa.int/tap-server/tap/sync"]
NASA_TAP = ["https://exoplanetarchive.ipac.caltech.edu/TAP/sync"]
LOT = 300                     # identifiants par requête
AL_PAR_PC = 3.2615637771674333

# Nom français affiché -> identifiant SIMBAD (vérifié par la distance, voir verifier_nommees).
NOMS_SIMBAD = {
    "Achernar": "* alf Eri", "Tau Ceti": "* tau Cet", "Étoile polaire": "* alf UMi", "Epsilon Eridani": "* eps Eri",
    "Aldébaran": "* alf Tau", "Rigel": "* bet Ori", "Capella": "* alf Aur",
    "Alnilam, dans la ceinture d’Orion": "* eps Ori", "Bételgeuse": "* alf Ori", "Canopus": "* alf Car",
    "Sirius": "* alf CMa", "Castor": "* alf Gem", "Procyon": "* alf CMi", "Pollux": "* bet Gem", "Régulus": "* alf Leo",
    "Lalande 21185": "HIP 54035", "Acrux": "* alf Cru", "Spica": "* alf Vir", "Hadar": "* bet Cen",
    "Arcturus": "* alf Boo", "Proxima du Centaure": "NAME Proxima Centauri", "Alpha du Centaure": "* alf Cen A",
    "Antarès": "* alf Sco", "Étoile de Barnard": "HIP 87937", "Véga": "* alf Lyr", "Ross 154": "HIP 92403",
    "Altaïr": "* alf Aql", "Deneb": "* alf Cyg", "61 du Cygne": "* 61 Cyg A", "Fomalhaut": "* alf PsA",
    "Lacaille 9352": "HIP 114046", "Wolf 359": "GJ 406", "Gliese 710": "HIP 89825",
}

ORDRE_GROUPES = ["Identité", "Position", "Mouvement", "Physique", "Rotation", "Lumière et couleur", "Âge et évolution",
                 "Planètes", "Autres noms", "Modèles et hypothèses"]

# Bibcodes fréquents -> référence lisible (les autres restent en bibcode, cherchable sur ADS).
BIBCODES = {
    "2020yCat.1350....0G": "Gaia EDR3 (Gaia Collaboration 2020)",
    "2022yCat.1355....0G": "Gaia DR3 (Gaia Collaboration 2022)",
    "2023A&A...674A...1G": "Gaia DR3 (Gaia Collaboration, Vallenari et al. 2023)",
    "2018yCat.1345....0G": "Gaia DR2 (Gaia Collaboration 2018)",
    "2007A&A...474..653V": "Hipparcos, nouvelle réduction (van Leeuwen 2007)",
    "2003yCat.2246....0C": "2MASS (Cutri et al. 2003)",
    "2002yCat.2237....0D": "Ducati 2002",
    "2000A&A...355L..27H": "Tycho-2 (Høg et al. 2000)",
}

# Types d'objet SIMBAD fréquents en français (sinon le libellé anglais de SIMBAD).
TYPES_FR = {
    "*": "étoile", "PM*": "étoile à grand mouvement propre", "BY*": "variable de type BY Draconis",
    "SB*": "binaire spectroscopique", "EB*": "binaire à éclipses", "V*": "étoile variable", "RG*": "géante rouge",
    "s*r": "supergéante rouge", "s*b": "supergéante bleue", "s*y": "supergéante jaune", "cC*": "céphéide classique",
    "WD*": "naine blanche", "BD*": "naine brune", "LM*": "étoile de faible masse", "Ro*": "variable par rotation",
    "Er*": "variable éruptive", "TT*": "étoile T Tauri", "YSO": "jeune objet stellaire", "**": "étoile double",
    "El*": "variable ellipsoïdale", "HB*": "étoile de la branche horizontale", "LP*": "variable à longue période",
    "Mi*": "variable de type Mira", "RS*": "variable de type RS CVn", "dS*": "variable de type delta Scuti",
    "a2*": "variable de type alpha² CVn", "Pu*": "étoile pulsante", "gD*": "variable de type gamma Doradus",
    "Be*": "étoile Be", "Em*": "étoile à raies d'émission", "Ae*": "étoile Herbig Ae/Be", "HS*": "étoile chaude sous-naine",
    "AB*": "étoile de la branche asymptotique", "C*": "étoile carbonée", "S*": "étoile de type S", "bC*": "variable de type bêta Céphée",
    "SX*": "variable de type SX Phe", "RR*": "variable de type RR Lyrae", "OH*": "étoile OH/IR", "Y*O": "jeune objet stellaire",
    "Pl": "planète", "Pl?": "candidate planète", "X": "source X", "XB*": "binaire X", "WR*": "étoile Wolf-Rayet",
}

# Préfixes d'identifiants gardés dans « Autres noms » (ordre d'affichage) et leur libellé.
AUTRES_NOMS = [("NAME ", "Nom usuel"), ("* ", "Désignation de Bayer ou de Flamsteed"), ("V* ", "Désignation de variable"),
               ("HD ", "HD"), ("HR ", "HR (Bright Star)"), ("HIP ", "Hipparcos (HIP)"), ("GJ ", "Gliese (GJ)"),
               ("Gaia DR3 ", "Gaia DR3"), ("Gaia DR2 ", "Gaia DR2"), ("2MASS ", "2MASS"), ("TYC ", "Tycho (TYC)"),
               ("TIC ", "TESS (TIC)"), ("BD", "Bonner Durchmusterung (BD)"), ("CD-", "Cordoba Durchmusterung (CD)"),
               ("LHS ", "LHS"), ("Kepler-", "Kepler"), ("KOI-", "KOI"), ("K2-", "K2"), ("TOI-", "TOI"),
               ("WASP-", "WASP"), ("HAT-P-", "HATNet"), ("KELT-", "KELT"), ("CoRoT-", "CoRoT"), ("XO-", "XO"),
               ("TrES-", "TrES"), ("Qatar-", "Qatar"), ("EPIC ", "K2 (EPIC)"), ("KIC ", "Kepler (KIC)"), ("WISE ", "WISE")]

# Point zéro des magnitudes Gaia DR3 (Riello et al. 2021, tableau 2 ; repris par la documentation Gaia DR3).
ZP_GAIA = {"g": 0.0027553202, "bp": 0.0027901700, "rp": 0.0037793818}


# --------------------------------------------------------------------------------------------------------------- TAP
def tap(serveurs, requete, nom):
    """Requête ADQL synchrone (CSV) ; réponse brute gardée en cache. Essaie chaque serveur dans l'ordre."""
    CACHE.mkdir(parents=True, exist_ok=True)
    fichier = CACHE / f"{nom}_{hashlib.md5(requete.encode()).hexdigest()[:12]}.csv"
    if fichier.exists():
        texte = fichier.read_text(encoding="utf-8")
    else:
        texte, erreurs = None, []
        for url in serveurs:
            for essai in range(3):
                try:
                    donnees = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                                      "QUERY": requete}).encode()
                    req = urllib.request.Request(url, donnees, headers={"User-Agent": "univers-fiches/1.0"})
                    texte = urllib.request.urlopen(req, timeout=300).read().decode("utf-8")
                    break
                except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                    erreurs.append(f"{url} : {e}")
                    if isinstance(e, urllib.error.HTTPError) and e.code in (400, 404):
                        break      # serveur absent ou requête refusée : pas la peine de réessayer
                    time.sleep(5 * (essai + 1))
            if texte is not None:
                with open(CACHE / "serveurs.txt", "a", encoding="utf-8") as j:      # journal : serveur qui a répondu
                    j.write(f"{datetime.date.today().isoformat()}\t{nom}\t{url}\n")
                break
        if texte is None:
            raise RuntimeError("TAP injoignable :\n" + "\n".join(erreurs))
        fichier.write_text(texte, encoding="utf-8")
    return list(csv.DictReader(io.StringIO(texte)))



def lots(valeurs, n=LOT):
    valeurs = list(valeurs)
    for i in range(0, len(valeurs), n):
        yield valeurs[i:i + n]


def chaine_adql(s):
    return "'" + s.replace("'", "''") + "'"


# --------------------------------------------------------------------------------------------------------- formats
def nombre(s, chiffres=None):
    """Texte d'un nombre sans zéros de remplissage ('12.20000000' -> '12.2') ; None si vide ou non numérique.
    chiffres : nombre de chiffres significatifs gardés (les float64 de Gaia en portent 16, bien au-delà de la mesure)."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        x = float(s)
    except ValueError:
        return None
    if math.isnan(x):
        return None
    t = repr(float(f"{x:.{chiffres}g}")) if chiffres else repr(x)
    if t.endswith(".0"):
        t = t[:-2]
    return t


def arrondi(x, chiffres=2):
    """Incertitude arrondie à quelques chiffres significatifs (bornes Gaia, σ calculées)."""
    if x is None or not math.isfinite(x):
        return None
    if x == 0:
        return "0"
    return nombre(f"{x:.{chiffres}g}")


def incertitude_err(e1, e2):
    """err1/err2 (NASA) -> '0.05' (symétrique) ou '+0.1/-0.2' ; vide si un des deux côtés manque."""
    a, b = nombre(e1), nombre(e2)
    if a is None or b is None:
        return ""
    b_abs = b.lstrip("-")
    a_abs = a.lstrip("+")
    if a_abs == b_abs:
        return a_abs
    return f"+{a_abs}/-{b_abs}"


def incertitude_bornes(v, bas, haut):
    """Valeur et bornes (16e/84e centiles Gaia) -> '+a/-b'."""
    try:
        x, lo, hi = float(v), float(bas), float(haut)
    except (TypeError, ValueError):
        return ""
    a, b = arrondi(hi - x), arrondi(x - lo)
    if a is None or b is None:
        return ""
    return a if a == b else f"+{a}/-{b}"


def reference_nasa(lien):
    """'<a refstr=... href=...>Agol et al. 2021</a>' -> 'Agol et al. 2021'."""
    m = re.search(r">(.*?)</a>", lien or "")
    texte = html.unescape(m.group(1) if m else (lien or "")).strip()
    return re.sub(r"\s+", " ", texte)


def ref_bibcode(b):
    b = (b or "").strip()
    return BIBCODES.get(b, b)


def propre(s):
    """Texte sans tabulation ni retour à la ligne, espaces simples."""
    return re.sub(r"\s+", " ", str(s)).strip()


class Fiche:
    """Lignes d'une étoile ; rangées par groupe à l'écriture (ordre d'apparition gardé dans un groupe)."""

    def __init__(self, cle):
        self.cle, self.lignes = cle, []

    def ajoute(self, groupe, libelle, valeur, incertitude="", unite="", statut="mesuré", source=""):
        if valeur is None or propre(valeur) == "":
            return
        self.lignes.append((groupe, propre(libelle), propre(valeur), propre(incertitude), unite, statut, propre(source)))

    def texte(self):
        rang = {g: i for i, g in enumerate(ORDRE_GROUPES)}
        lignes = sorted(enumerate(self.lignes), key=lambda t: (rang.get(t[1][0], 99), t[0]))
        return "".join("\t".join((self.cle,) + l) + "\n" for _, l in lignes)


# ----------------------------------------------------------------------------------------------------------- entrées
def lire_entrees():
    """Liste des étoiles : dicts {cle, rang, dist_al, simbad (id voulu ou None), hote (nom NASA ou None)}."""
    nommees, par_rang = [], {}
    for l in open(DONNEES / "etoiles_noms.tsv", encoding="utf-8"):
        c = l.rstrip("\n").split("\t")
        if len(c) < 3 or l.startswith("#"):
            continue
        e = {"cle": c[1], "rang": int(c[0]), "dist_al": float(c[2]), "simbad": NOMS_SIMBAD.get(c[1]), "hote": None}
        if e["simbad"] is None:
            print(f"ATTENTION : pas d'identifiant SIMBAD pour « {c[1]} »")
        nommees.append(e)
        par_rang[e["rang"]] = e
    hotes = []
    for l in open(DONNEES / "etoiles_planetes_noms.tsv", encoding="utf-8"):
        c = l.rstrip("\n").split("\t")
        if len(c) < 4 or l.startswith("#"):
            continue
        rang = int(c[0])
        if rang in par_rang:                 # l'appli montre le nom français : lignes NASA sous ce nom
            par_rang[rang]["hote"] = c[1]
            continue
        hotes.append({"cle": c[1], "rang": rang, "dist_al": float(c[2]), "simbad": None, "hote": c[1]})
    return nommees + hotes


# -------------------------------------------------------------------------------------------------------------- NASA
COL_NASA_ETOILE = ["st_spectype", "st_teff", "st_rad", "st_mass", "st_met", "st_metratio", "st_logg", "st_age",
                   "st_dens", "st_lum", "st_vsin", "st_rotp", "st_radv", "sy_dist", "sy_plx", "sy_pmra", "sy_pmdec",
                   "sy_snum", "sy_pnum", "sy_bmag", "sy_vmag", "sy_jmag", "sy_hmag", "sy_kmag", "sy_gaiamag",
                   "sy_tmag", "sy_kepmag"]
COL_NASA_PLANETE = ["pl_orbper", "pl_orbsmax", "pl_orbeccen", "pl_orbincl", "pl_orblper", "pl_bmasse", "pl_rade",
                    "pl_dens", "pl_eqt", "pl_insol", "pl_trandur", "pl_trandep", "pl_ratror", "pl_imppar",
                    "pl_rvamp", "pl_tranmid", "pl_projobliq", "pl_angsep"]


def colonnes_nasa():
    cols = ["pl_name", "hostname", "hd_name", "hip_name", "tic_id", "gaia_dr3_id", "pl_bmassprov", "discoverymethod",
            "disc_year", "disc_facility", "disc_refname", "pl_controv_flag"]
    sans_err = {"st_spectype", "st_metratio", "sy_snum", "sy_pnum"}
    for c in COL_NASA_ETOILE + COL_NASA_PLANETE:
        cols.append(c)
        if c in sans_err:
            if c == "st_spectype":
                cols.append("st_spectype_reflink")
            continue
        cols += [c + "err1", c + "err2"]
        if not c.startswith("sy_"):          # les colonnes sy_* n'ont pas d'indicateur de limite
            cols.append(c + "lim")
        if c in ("sy_pmra", "sy_pmdec"):     # référence commune du mouvement propre : sy_pm_reflink
            if "sy_pm_reflink" not in cols:
                cols.append("sy_pm_reflink")
        else:
            cols.append(c + "_reflink")
    return cols


def lire_nasa(hotes):
    """Toutes les lignes pscomppars (une requête), filtrées sur les hôtes de l'appli : {hostname: [lignes]}."""
    lignes = tap(NASA_TAP, "SELECT " + ", ".join(colonnes_nasa()) + " FROM pscomppars", "nasa_pscomppars")
    par_hote = {}
    for r in lignes:
        if r["hostname"] in hotes:
            par_hote.setdefault(r["hostname"], []).append(r)
    return par_hote


# ------------------------------------------------------------------------------------------------------------ SIMBAD
def candidats_simbad(e, nasa):
    if e["simbad"]:
        return [e["simbad"]]
    r = nasa.get(e["hote"], [{}])[0]
    h = e["hote"]
    c = []
    for v in (r.get("gaia_dr3_id"), h, "* " + h, "NAME " + h, r.get("hd_name"), r.get("hip_name"), r.get("tic_id")):
        v = (v or "").strip()
        if v and v not in c:
            c.append(v)
    return c


def resoudre_simbad(entrees, nasa):
    """Identifiant -> oid SIMBAD, en lots ; chaque étoile reçoit le premier candidat résolu."""
    tous = sorted({c for e in entrees for c in candidats_simbad(e, nasa)})
    trouve = {}
    for i, lot in enumerate(lots(tous)):
        req = ("SELECT i.id AS cherche, i.oidref FROM ident AS i WHERE i.id IN ("
               + ", ".join(chaine_adql(x) for x in lot) + ")")
        for r in tap(SIMBAD_TAP, req, f"simbad_ident_{i:03d}"):
            trouve[norm_id(r["cherche"])] = int(r["oidref"])
    for e in entrees:
        e["oid"] = None
        for c in candidats_simbad(e, nasa):
            if norm_id(c) in trouve:
                e["oid"], e["simbad_par"] = trouve[norm_id(c)], c
                break


def norm_id(s):
    return re.sub(r"\s+", " ", s or "").strip()


def lire_simbad(oids):
    basic, flux, ids = {}, {}, {}
    oids = sorted(oids)
    for i, lot in enumerate(lots(oids)):
        liste = ", ".join(str(o) for o in lot)
        req = ("SELECT b.oid, b.main_id, b.otype, d.label AS otype_label, d.description AS otype_desc, b.sp_type, "
               "b.sp_qual, b.sp_bibcode, b.ra, b.dec, b.coo_bibcode, b.plx_value, b.plx_err, b.plx_bibcode, b.pmra, "
               "b.pmdec, b.pm_err_maj, b.pm_err_min, b.pm_bibcode, b.rvz_radvel, b.rvz_err, b.rvz_bibcode, b.rvz_type "
               "FROM basic AS b LEFT JOIN otypedef AS d ON d.otype = b.otype WHERE b.oid IN (" + liste + ")")
        for r in tap(SIMBAD_TAP, req, f"simbad_basic_{i:03d}"):
            basic[int(r["oid"])] = r
        req = ("SELECT oidref, filter, flux, flux_err, bibcode FROM flux WHERE oidref IN (" + liste + ") AND filter IN "
               "('U','B','V','R','I','J','H','K','G')")
        for r in tap(SIMBAD_TAP, req, f"simbad_flux_{i:03d}"):
            flux.setdefault(int(r["oidref"]), []).append(r)
        for r in tap(SIMBAD_TAP, "SELECT oidref, ids FROM ids WHERE oidref IN (" + liste + ")", f"simbad_ids_{i:03d}"):
            ids[int(r["oidref"])] = [norm_id(x) for x in r["ids"].split("|")]
    return basic, flux, ids


# -------------------------------------------------------------------------------------------------------------- Gaia
COL_GAIA = ["source_id", "ra", "dec", "parallax", "parallax_error", "pmra", "pmra_error", "pmdec", "pmdec_error",
            "radial_velocity", "radial_velocity_error", "phot_g_mean_mag", "phot_g_mean_flux_over_error",
            "phot_bp_mean_mag", "phot_bp_mean_flux_over_error", "phot_rp_mean_mag", "phot_rp_mean_flux_over_error",
            "bp_rp", "ruwe", "non_single_star", "phot_variable_flag", "vbroad", "vbroad_error",
            "teff_gspphot", "teff_gspphot_lower", "teff_gspphot_upper", "logg_gspphot", "logg_gspphot_lower",
            "logg_gspphot_upper", "mh_gspphot", "mh_gspphot_lower", "mh_gspphot_upper", "distance_gspphot",
            "distance_gspphot_lower", "distance_gspphot_upper", "ag_gspphot", "ag_gspphot_lower", "ag_gspphot_upper",
            "ebpminrp_gspphot", "ebpminrp_gspphot_lower", "ebpminrp_gspphot_upper"]
COL_AP = ["source_id", "radius_gspphot", "radius_gspphot_lower", "radius_gspphot_upper",
          "teff_gspspec", "teff_gspspec_lower", "teff_gspspec_upper", "logg_gspspec", "logg_gspspec_lower",
          "logg_gspspec_upper", "mh_gspspec", "mh_gspspec_lower", "mh_gspspec_upper", "alphafe_gspspec",
          "alphafe_gspspec_lower", "alphafe_gspspec_upper", "teff_esphs", "teff_esphs_uncertainty", "logg_esphs",
          "logg_esphs_uncertainty", "vsini_esphs", "vsini_esphs_uncertainty", "spectraltype_esphs",
          "classlabel_espels", "teff_espucd", "teff_espucd_uncertainty",
          "radius_flame", "radius_flame_lower", "radius_flame_upper", "lum_flame", "lum_flame_lower",
          "lum_flame_upper", "mass_flame", "mass_flame_lower", "mass_flame_upper", "age_flame", "age_flame_lower",
          "age_flame_upper", "evolstage_flame"]


def lire_gaia(source_ids):
    src, ap = {}, {}
    ids = sorted(source_ids)
    for i, lot in enumerate(lots(ids, 500)):
        liste = ", ".join(str(s) for s in lot)
        for r in tap(GAIA_TAP, f"SELECT {', '.join(COL_GAIA)} FROM gaiadr3.gaia_source WHERE source_id IN ({liste})",
                     f"gaia_source_{i:03d}"):
            src[int(r["source_id"])] = r
        for r in tap(GAIA_TAP, f"SELECT {', '.join(COL_AP)} FROM gaiadr3.astrophysical_parameters "
                               f"WHERE source_id IN ({liste})", f"gaia_ap_{i:03d}"):
            ap[int(r["source_id"])] = r
    return src, ap


# ------------------------------------------------------------------------------------------------- écriture SIMBAD
def fiche_simbad(f, b, flux, ids):
    S = "SIMBAD (CDS)"
    f.ajoute("Identité", "Nom principal dans SIMBAD", norm_id(b["main_id"]), statut="publié", source=S)
    if b.get("otype"):
        fr = TYPES_FR.get(b["otype"]) or b.get("otype_desc") or b.get("otype_label")
        f.ajoute("Identité", "Type d'objet", f"{fr} ({b['otype']})", statut="publié", source=S)
    if b.get("sp_type"):
        q = f", qualité {b['sp_qual']} (A meilleure, E moins sûre)" if b.get("sp_qual") else ""
        f.ajoute("Identité", "Type spectral", b["sp_type"], statut="publié",
                 source=f"{S}{q} ; {ref_bibcode(b.get('sp_bibcode'))}")
    ref_coo = ref_bibcode(b.get("coo_bibcode"))
    f.ajoute("Position", "Ascension droite (ICRS, J2000)", nombre(b.get("ra"), 10), unite="°", source=f"{S} ; {ref_coo}")
    f.ajoute("Position", "Déclinaison (ICRS, J2000)", nombre(b.get("dec"), 10), unite="°", source=f"{S} ; {ref_coo}")
    plx, eplx = nombre(b.get("plx_value")), nombre(b.get("plx_err"))
    ref_plx = ref_bibcode(b.get("plx_bibcode"))
    f.ajoute("Position", "Parallaxe", plx, eplx or "", "mas", source=f"{S} ; {ref_plx}")
    distance_parallaxe(f, plx, eplx, f"parallaxe SIMBAD ({ref_plx})")
    ref_pm = ref_bibcode(b.get("pm_bibcode"))
    f.ajoute("Mouvement", "Mouvement propre en ascension droite (μα cos δ)", nombre(b.get("pmra")), unite="mas/an",
             source=f"{S} ; {ref_pm}")
    f.ajoute("Mouvement", "Mouvement propre en déclinaison (μδ)", nombre(b.get("pmdec")), unite="mas/an",
             source=f"{S} ; {ref_pm}")
    a, c = nombre(b.get("pm_err_maj")), nombre(b.get("pm_err_min"))
    if a and c and nombre(b.get("pmra")):
        f.ajoute("Mouvement", "Incertitude du mouvement propre (ellipse : grand axe × petit axe)", f"{a} × {c}",
                 unite="mas/an", source=f"{S} ; {ref_pm}")
    if b.get("rvz_type", "v") in ("v", ""):
        f.ajoute("Mouvement", "Vitesse radiale", nombre(b.get("rvz_radvel")), nombre(b.get("rvz_err")) or "", "km/s",
                 source=f"{S} ; {ref_bibcode(b.get('rvz_bibcode'))}")
    for r in sorted(flux, key=lambda r: "UBVRIJHKG".index(r["filter"])):
        f.ajoute("Lumière et couleur", f"Magnitude apparente {r['filter']}", nombre(r["flux"]),
                 nombre(r.get("flux_err")) or "", "mag", source=f"{S} ; {ref_bibcode(r.get('bibcode'))}")
    for prefixe, libelle in AUTRES_NOMS:
        vus = [x for x in ids if x.startswith(prefixe)]
        if prefixe == "* ":
            vus = [x[2:] for x in vus]
        elif prefixe in ("NAME ", "V* "):
            vus = [x[len(prefixe):] for x in vus]
        if vus:
            f.ajoute("Autres noms", libelle, " ; ".join(vus), statut="publié", source=S)


def distance_parallaxe(f, plx, eplx, origine):
    try:
        p, s = float(plx), float(eplx)
    except (TypeError, ValueError):
        return
    if p <= 0 or s <= 0 or p < 3 * s:
        return
    d = AL_PAR_PC * 1000 / p
    haut, bas = AL_PAR_PC * 1000 / (p - s) - d, d - AL_PAR_PC * 1000 / (p + s)
    chiffres = max(2, int(math.floor(math.log10(d))) - int(math.floor(math.log10(min(haut, bas)))) + 2)
    f.ajoute("Position", "Distance d'après la parallaxe", arrondi(d, chiffres),
             arrondi(haut) if arrondi(haut) == arrondi(bas) else f"+{arrondi(haut)}/-{arrondi(bas)}", "al", "calculé",
             f"calculé : d = 3,2615638 / parallaxe (″), {origine}")


# --------------------------------------------------------------------------------------------------- écriture Gaia
NSS = {1: "astrométrique", 2: "spectroscopique", 4: "à éclipses"}


def fiche_gaia(f, g, ap):
    G = "Gaia DR3 (Gaia Collaboration, Vallenari et al. 2023)"
    if g:
        f.ajoute("Identité", "Identifiant Gaia DR3", g["source_id"], statut="publié", source=G)
        ns = nombre(g.get("non_single_star"))
        if ns is not None:
            n = int(float(ns))
            txt = "non (aucun signe de compagnon dans Gaia DR3)" if n == 0 else \
                "oui : binaire " + ", ".join(v for k, v in NSS.items() if n & k)
            f.ajoute("Identité", "Étoile multiple détectée par Gaia (non_single_star)", txt, source=G)
        var = g.get("phot_variable_flag", "")
        if var:
            f.ajoute("Identité", "Variabilité de l'éclat (Gaia DR3)",
                     {"VARIABLE": "variable", "NOT_AVAILABLE": "non classée", "CONSTANT": "constante"}.get(var, var),
                     source=G)
        f.ajoute("Position", "Parallaxe (Gaia DR3)", nombre(g.get("parallax"), 8), nombre(g.get("parallax_error"), 2) or "",
                 "mas", source=G)
        f.ajoute("Position", "RUWE (qualité de l'ajustement astrométrique, ≈ 1 = bon, > 1,4 = douteux)",
                 nombre(g.get("ruwe"), 8), source=G)
        f.ajoute("Mouvement", "Mouvement propre en ascension droite (Gaia DR3)", nombre(g.get("pmra"), 8),
                 nombre(g.get("pmra_error"), 2) or "", "mas/an", source=G)
        f.ajoute("Mouvement", "Mouvement propre en déclinaison (Gaia DR3)", nombre(g.get("pmdec"), 8),
                 nombre(g.get("pmdec_error"), 2) or "", "mas/an", source=G)
        f.ajoute("Mouvement", "Vitesse radiale (Gaia DR3)", nombre(g.get("radial_velocity"), 8),
                 nombre(g.get("radial_velocity_error"), 2) or "", "km/s", source=G)
        f.ajoute("Physique", "Élargissement des raies (vbroad, Gaia DR3)", nombre(g.get("vbroad"), 8),
                 nombre(g.get("vbroad_error"), 2) or "", "km/s", source=G)
        for bande, nom in (("g", "G"), ("bp", "BP"), ("rp", "RP")):
            m = nombre(g.get(f"phot_{bande}_mean_mag"), 8)
            inc = ""
            try:
                foe = float(g.get(f"phot_{bande}_mean_flux_over_error"))
                inc = arrondi(math.hypot(2.5 / math.log(10) / foe, ZP_GAIA[bande]), 2) or ""
            except (TypeError, ValueError, ZeroDivisionError):
                pass
            f.ajoute("Lumière et couleur", f"Magnitude Gaia {nom}", m, inc, "mag",
                     source=G + (" ; incertitude calculée : 1,0857 / (flux/σ) combinée au point zéro "
                                 "(Riello et al. 2021)" if inc else ""))
        f.ajoute("Lumière et couleur", "Couleur BP − RP (Gaia DR3)", nombre(g.get("bp_rp"), 8), unite="mag", source=G)
        modeles_gaia(f, g, [("teff_gspphot", "Température de surface", "K"),
                            ("logg_gspphot", "Gravité de surface log g", "dex (cm/s²)"),
                            ("mh_gspphot", "Métallicité [M/H]", "dex"),
                            ("distance_gspphot", "Distance (photométrie + parallaxe)", "pc"),
                            ("ag_gspphot", "Extinction en bande G", "mag"),
                            ("ebpminrp_gspphot", "Rougissement E(BP − RP)", "mag")], "GSP-Phot")
    if ap:
        modeles_gaia(f, ap, [("radius_gspphot", "Rayon", "rayons solaires")], "GSP-Phot")
        modeles_gaia(f, ap, [("teff_gspspec", "Température de surface", "K"),
                             ("logg_gspspec", "Gravité de surface log g", "dex (cm/s²)"),
                             ("mh_gspspec", "Métallicité [M/H]", "dex"),
                             ("alphafe_gspspec", "Éléments alpha [α/Fe]", "dex")], "GSP-Spec")
        for col, lib, unite, module in (("teff_esphs", "Température de surface (étoile chaude)", "K", "ESP-HS"),
                                        ("logg_esphs", "Gravité de surface log g (étoile chaude)", "dex (cm/s²)", "ESP-HS"),
                                        ("vsini_esphs", "Vitesse de rotation projetée v sin i", "km/s", "ESP-HS"),
                                        ("teff_espucd", "Température de surface (naine ultra-froide)", "K", "ESP-UCD")):
            f.ajoute("Modèles et hypothèses", f"Gaia {module} : {lib}", nombre(ap.get(col), 5),
                     arrondi(float(ap[col + "_uncertainty"])) if nombre(ap.get(col + "_uncertainty")) else "",
                     unite, "modèle", f"{G}, module Apsis {module}")
        f.ajoute("Modèles et hypothèses", "Gaia ESP-HS : type spectral", ap.get("spectraltype_esphs"),
                 statut="modèle", source=f"{G}, module Apsis ESP-HS")
        f.ajoute("Modèles et hypothèses", "Gaia ESP-ELS : classe d'étoile à raies d'émission",
                 ap.get("classlabel_espels"), statut="modèle", source=f"{G}, module Apsis ESP-ELS")
        modeles_gaia(f, ap, [("radius_flame", "Rayon", "rayons solaires"),
                             ("lum_flame", "Luminosité", "luminosités solaires"),
                             ("mass_flame", "Masse (isochrones BASTI)", "masses solaires"),
                             ("age_flame", "Âge (isochrones BASTI)", "milliards d'années")], "FLAME")
        f.ajoute("Modèles et hypothèses", "Gaia FLAME : stade d'évolution (code BASTI, 100 = début de la séquence "
                 "principale)", nombre(ap.get("evolstage_flame")), statut="modèle", source=f"{G}, module Apsis FLAME")


def modeles_gaia(f, r, champs, module):
    for col, lib, unite in champs:
        f.ajoute("Modèles et hypothèses", f"Gaia {module} : {lib}", nombre(r.get(col), 5),
                 incertitude_bornes(r.get(col), r.get(col + "_lower"), r.get(col + "_upper")), unite, "modèle",
                 f"Gaia DR3 (Gaia Collaboration, Vallenari et al. 2023), module Apsis {module} ; bornes = 16e et 84e "
                 f"centiles")


# --------------------------------------------------------------------------------------------------- écriture NASA
NASA = "NASA Exoplanet Archive, pscomppars (DOI 10.26133/NEA13)"
CALCUL = "Calculated Value"

ETOILE_NASA = [  # colonne, groupe, libellé, unité, statut par défaut
    ("sy_plx", "Position", "Parallaxe", "mas", "mesuré"),
    ("sy_dist", "Position", "Distance", "pc", "mesuré"),
    ("sy_pmra", "Mouvement", "Mouvement propre en ascension droite", "mas/an", "mesuré"),
    ("sy_pmdec", "Mouvement", "Mouvement propre en déclinaison", "mas/an", "mesuré"),
    ("st_radv", "Mouvement", "Vitesse radiale", "km/s", "mesuré"),
    ("st_teff", "Physique", "Température de surface", "K", "mesuré"),
    ("st_rad", "Physique", "Rayon", "rayons solaires", "mesuré"),
    ("st_mass", "Physique", "Masse", "masses solaires", "modèle"),
    ("st_logg", "Physique", "Gravité de surface log g", "dex (cm/s²)", "mesuré"),
    ("st_dens", "Physique", "Densité moyenne", "g/cm³", "mesuré"),
    ("st_lum", "Physique", "Luminosité, log10(L / L☉)", "dex", "mesuré"),
    ("st_met", "Physique", "Métallicité", "dex", "mesuré"),
    ("st_vsin", "Rotation", "Vitesse de rotation projetée v sin i", "km/s", "mesuré"),
    ("st_rotp", "Rotation", "Période de rotation", "jours", "mesuré"),
    ("st_age", "Âge et évolution", "Âge", "milliards d'années", "modèle"),
    ("sy_bmag", "Lumière et couleur", "Magnitude B", "mag", "mesuré"),
    ("sy_vmag", "Lumière et couleur", "Magnitude V", "mag", "mesuré"),
    ("sy_jmag", "Lumière et couleur", "Magnitude J", "mag", "mesuré"),
    ("sy_hmag", "Lumière et couleur", "Magnitude H", "mag", "mesuré"),
    ("sy_kmag", "Lumière et couleur", "Magnitude K", "mag", "mesuré"),
    ("sy_gaiamag", "Lumière et couleur", "Magnitude Gaia G", "mag", "mesuré"),
    ("sy_tmag", "Lumière et couleur", "Magnitude TESS", "mag", "mesuré"),
    ("sy_kepmag", "Lumière et couleur", "Magnitude Kepler", "mag", "mesuré"),
]

PLANETE_NASA = [  # colonne, libellé, unité
    ("pl_orbper", "période orbitale", "jours"),
    ("pl_orbsmax", "demi-grand axe", "UA"),
    ("pl_orbeccen", "excentricité", ""),
    ("pl_orbincl", "inclinaison de l'orbite", "°"),
    ("pl_orblper", "argument du périastre", "°"),
    ("pl_bmasse", "masse", "masses terrestres"),
    ("pl_rade", "rayon", "rayons terrestres"),
    ("pl_dens", "densité moyenne", "g/cm³"),
    ("pl_eqt", "température d'équilibre", "K"),
    ("pl_insol", "flux reçu de l'étoile", "fois celui reçu par la Terre"),
    ("pl_trandur", "durée du transit", "heures"),
    ("pl_trandep", "profondeur du transit", "%"),
    ("pl_ratror", "rapport des rayons planète / étoile", ""),
    ("pl_imppar", "paramètre d'impact du transit", ""),
    ("pl_rvamp", "amplitude de la vitesse radiale de l'étoile", "m/s"),
    ("pl_tranmid", "milieu d'un transit (jour julien barycentrique)", "jours"),
    ("pl_projobliq", "obliquité projetée (orbite / équateur de l'étoile)", "°"),
    ("pl_angsep", "séparation angulaire planète-étoile", "mas"),
]

FORMULES = {
    "pl_dens": "ρ = 3M / (4πR³)", "st_lum": "L = 4πR²σT⁴", "pl_insol": "S/S⊕ = (L/L☉)(1 UA / a)²",
    "pl_angsep": "ρ = a / d", "pl_orbsmax": "loi de Kepler",
}


def valeur_nasa(r, col):
    """(valeur avec < ou >, incertitude, référence) d'une colonne pscomppars ; valeur None si vide."""
    v = nombre(r.get(col))
    if v is None:
        return None, "", ""
    lim = (r.get(col + "lim") or "").strip()
    if lim in ("1", "1.0"):
        v = "<" + v
    elif lim in ("-1", "-1.0"):
        v = ">" + v
    inc = incertitude_err(r.get(col + "err1"), r.get(col + "err2")) if v[0] not in "<>" else ""
    lien = r.get("sy_pm_reflink") if col in ("sy_pmra", "sy_pmdec") else r.get(col + "_reflink")
    return v, inc, reference_nasa(lien)


def statut_calcul(col, ref, statut, modeles):
    """Statut et source d'une valeur, selon que l'archive l'a calculée (docs/pscp_calc.html)."""
    if col == "pl_eqt" and ref != CALCUL:
        return "modèle", (f"{NASA} ; {ref} ; modèle : la température d'équilibre suppose un albédo et une "
                          "répartition de la chaleur (hypothèses de l'article)")
    if ref != CALCUL:
        return statut, f"{NASA} ; {ref}" if ref else NASA
    if col in ("pl_rade", "pl_bmasse"):
        return "modèle", f"{NASA} ; modèle : relation masse-rayon de Chen & Kipping 2017, calculée par l'archive"
    if col == "pl_eqt":
        return "modèle", (f"{NASA} ; modèle calculé par l'archive : Teq = T★ √(R★/a) (1/4)^(1/4), albédo nul "
                          "et chaleur répartie sur toute la planète")
    if col == "pl_dens" and modeles:
        return "modèle", f"{NASA} ; calculé par l'archive (ρ = 3M / (4πR³)) à partir d'une masse ou d'un rayon modèle"
    formule = FORMULES.get(col, "formule de l'archive")
    return "calculé", f"{NASA} ; calculé par l'archive : {formule} (docs/pscp_calc.html)"


def fiche_nasa(f, rangees):
    rangees = sorted(rangees, key=lambda r: r["pl_name"])
    noms = [r["pl_name"] for r in rangees]
    # Type spectral et nombre d'étoiles / planètes du système.
    for col, lib in (("st_spectype", "Type spectral (NASA)"),):
        for v, qui in distinctes(rangees, lambda r: (r.get(col, "").strip(), "", reference_nasa(r.get(col + "_reflink")))):
            f.ajoute("Identité", lib + qui_txt(qui, noms), v[0], statut="publié", source=f"{NASA} ; {v[2]}")
    r0 = rangees[0]
    f.ajoute("Identité", "Étoiles dans le système (NASA)", nombre(r0.get("sy_snum")), statut="publié", source=NASA)
    f.ajoute("Identité", "Planètes connues (NASA)", nombre(r0.get("sy_pnum")), statut="publié", source=NASA)
    for col, groupe, lib, unite, statut in ETOILE_NASA:
        if col == "st_met":
            ratio = r0.get("st_metratio", "").strip()
            lib = f"Métallicité {ratio}" if ratio else lib
        for (v, inc, ref), qui in distinctes(rangees, lambda r: valeur_nasa(r, col)):
            st, src = statut_calcul(col, ref, statut, False)
            f.ajoute(groupe, f"{lib} (NASA){qui_txt(qui, noms)}", v, inc, unite, st, src)
    for r in rangees:
        fiche_planete(f, r)


def distinctes(rangees, lire):
    """Valeurs distinctes d'un paramètre d'étoile sur les lignes des planètes : [((valeur, inc, ref), [planètes])]."""
    vus = {}
    for r in rangees:
        v = lire(r)
        if v[0]:
            vus.setdefault(v, []).append(r["pl_name"])
    return list(vus.items())


def qui_txt(qui, noms):
    if len(set(qui)) == len(noms):
        return ""
    return " — selon les paramètres liés à " + ", ".join(qui)


def fiche_planete(f, r):
    nom = r["pl_name"]
    prov = (r.get("pl_bmassprov") or "").strip()
    masse_modele = prov == "M-R relationship"
    modeles = masse_modele
    for col, lib, unite in PLANETE_NASA:
        v, inc, ref = valeur_nasa(r, col)
        if v is None:
            continue
        st, src = statut_calcul(col, ref, "mesuré", modeles)
        if col == "pl_bmasse":
            if prov == "Msini":
                lib = "masse minimale (M sin i)"
            elif masse_modele:
                lib, st = "masse (relation masse-rayon)", "modèle"
                if ref != CALCUL:
                    src += " ; modèle : relation masse-rayon (pl_bmassprov)"
        if st == "modèle" and col in ("pl_rade", "pl_bmasse"):
            modeles = True
        f.ajoute("Planètes", f"{nom} : {lib}", v, inc, unite, st, src)
    for col, lib in (("discoverymethod", "méthode de découverte"), ("disc_year", "année de découverte"),
                     ("disc_facility", "installation de découverte"), ("disc_refname", "article de découverte")):
        val = reference_nasa(r.get(col)) if col == "disc_refname" else (r.get(col) or "").strip()
        f.ajoute("Planètes", f"{nom} : {lib}", METHODES.get(val, val), statut="publié", source=NASA)
    if (r.get("pl_controv_flag") or "").strip() in ("1", "1.0"):
        f.ajoute("Planètes", f"{nom} : existence contestée dans la littérature", "oui", statut="publié", source=NASA)


METHODES = {
    "Radial Velocity": "vitesse radiale", "Transit": "transit", "Imaging": "imagerie directe",
    "Microlensing": "microlentille gravitationnelle", "Transit Timing Variations": "variations du temps de transit",
    "Eclipse Timing Variations": "variations du temps d'éclipse", "Astrometry": "astrométrie",
    "Pulsar Timing": "chronométrage de pulsar", "Orbital Brightness Modulation": "modulation d'éclat orbitale",
    "Pulsation Timing Variations": "variations du temps de pulsation", "Disk Kinematics": "cinématique du disque",
}


# --------------------------------------------------------------------------------------------------------- principal
def main():
    entrees = lire_entrees()
    hotes = {e["hote"] for e in entrees if e["hote"]}
    nasa = lire_nasa(hotes)
    print(f"Étoiles : {len(entrees)} ({sum(1 for e in entrees if e['simbad'])} nommées) ; "
          f"hôtes NASA trouvées dans pscomppars : {len(nasa)} / {len(hotes)}")

    resoudre_simbad(entrees, nasa)
    basic, flux, ids = lire_simbad({e["oid"] for e in entrees if e["oid"]})

    # Source Gaia DR3 : lue dans SIMBAD, sinon celle de la NASA.
    for e in entrees:
        e["gaia"] = None
        for x in ids.get(e["oid"], []):
            if x.startswith("Gaia DR3 "):
                e["gaia"] = int(x.split()[-1])
        if e["gaia"] is None and e["hote"] and nasa.get(e["hote"]):
            g = (nasa[e["hote"]][0].get("gaia_dr3_id") or "").strip()
            if g.startswith("Gaia DR3 "):
                e["gaia"] = int(g.split()[-1])
    src, ap = lire_gaia({e["gaia"] for e in entrees if e["gaia"]})

    verifier_distances(entrees, basic)

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    compte = {"simbad": 0, "gaia": 0, "ap": 0, "nasa": 0, "vide": 0, "lignes": 0}
    with open(SORTIE, "w", encoding="utf-8", newline="\n") as out:
        out.write("# fiches_etoiles.py (pipeline/natif) — " + datetime.date.today().isoformat() + "\n")
        out.write("# Sources : SIMBAD (CDS, Wenger et al. 2000) ; Gaia DR3 (Gaia Collaboration, Vallenari et al. 2023) ; "
                  "NASA Exoplanet Archive pscomppars (DOI 10.26133/NEA13)\n")
        journal = CACHE / "serveurs.txt"
        vus = [l.rstrip("\n").split("\t") for l in open(journal, encoding="utf-8")] if journal.exists() else []
        serveurs = sorted({v[2] for v in vus if len(v) == 3})
        dates = sorted({v[0] for v in vus if len(v) == 3})
        out.write("# Serveurs interrogés : " + ", ".join(serveurs) + " ; requêtes du "
                  + " au ".join(dict.fromkeys(dates[:1] + dates[-1:])) + "\n")
        out.write("# cle\tgroupe\tlibelle\tvaleur\tincertitude\tunite\tstatut\tsource\n")
        for e in entrees:
            f = Fiche(e["cle"])
            b = basic.get(e["oid"])
            if b and not e.get("rejet"):
                fiche_simbad(f, b, flux.get(e["oid"], []), ids.get(e["oid"], []))
                compte["simbad"] += 1
            g, a = src.get(e["gaia"]), ap.get(e["gaia"])
            if (g or a) and not e.get("rejet"):
                fiche_gaia(f, g, a)
                compte["gaia"] += bool(g)
                compte["ap"] += bool(a)
            if e["hote"] and nasa.get(e["hote"]):
                fiche_nasa(f, nasa[e["hote"]])
                compte["nasa"] += 1
            if not f.lignes:
                compte["vide"] += 1
                print(f"  sans données : {e['cle']}")
                continue
            compte["lignes"] += len(f.lignes)
            out.write(f.texte())
    print(f"Écrit {SORTIE} : {len(entrees) - compte['vide']} étoiles avec fiche, {compte['vide']} sans rien, "
          f"{compte['lignes']} lignes ; SIMBAD {compte['simbad']}, Gaia source {compte['gaia']}, "
          f"Gaia paramètres {compte['ap']}, NASA {compte['nasa']}")


def verifier_distances(entrees, basic):
    """Distance d'après la parallaxe SIMBAD comparée à la distance de l'appli ; écart > 30 % : identification rejetée
    pour SIMBAD et Gaia (la NASA reste, car reliée par son propre nom d'hôte)."""
    ecarts, sans = [], 0
    for e in entrees:
        b = basic.get(e["oid"])
        if b is None:
            sans += 1
            print(f"  non résolue dans SIMBAD : {e['cle']}")
            continue
        try:
            d = AL_PAR_PC * 1000 / float(b["plx_value"])
        except (TypeError, ValueError, ZeroDivisionError):
            if e["simbad"]:
                print(f"  {e['cle']:38s} -> {norm_id(b['main_id'])} : pas de parallaxe")
            continue
        ecart = d / e["dist_al"] - 1
        if e["simbad"]:
            print(f"  {e['cle']:38s} -> {norm_id(b['main_id']):28s} parallaxe : {d:9.2f} al ; appli : "
                  f"{e['dist_al']:9.2f} al ({ecart:+.1%})")
        if abs(ecart) > 0.30 and not e["simbad"]:
            e["rejet"] = True
            ecarts.append((e["cle"], norm_id(b["main_id"]), d, e["dist_al"]))
    print(f"Hôtes non résolues dans SIMBAD : {sans} ; identifications rejetées (distance > 30 % d'écart) : {len(ecarts)}")
    for x in ecarts[:30]:
        print("  rejet :", x)


if __name__ == "__main__":
    main()
