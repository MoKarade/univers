"""Trous noirs supermassifs à masse mesurée -> C:\\tmp\\vue-sources\\trous_noirs.tsv

README
------
Sources (mesures) :
  1. van den Bosch R.C.E. 2016, ApJ 831, 134, « Unification of the Fundamental
     Plane and Super-Massive Black Hole Masses », doi:10.3847/0004-637X/831/2/134,
     VizieR J/ApJ/831/134 (miroir https://vizier.cfa.harvard.edu) :
       table2 = 230 galaxies avec photométrie (utilisées pour les ajustements),
       table3 = 33 objets exclus des ajustements faute de photométrie 2MASS ou
                de sigma (dont la Voie lactée et M31), f_Name = 2 ou 3,
       table4 = 15 amas globulaires (trous noirs intermédiaires « GC »,
                hors trous noirs supermassifs : type = imbh_gc).
     Positions RA/Dec = colonnes _RA/_DE ajoutées par le CDS depuis SIMBAD.
     Masse : logBHMass (log Msun), E_ = erreur haute, e_ = erreur basse (dex).
     Limites supérieures : codées dans VizieR par logBHMass = 0 et la limite
     dans E_logBHMass (ex. M33 : 0 / +3.15 -> M < 10^3.15) ; ici
     log_masse = limite et limite_sup = 1.
     Codes de méthode (Meth) : star/stars = dynamique stellaire, gas = gaz
     ionisé, CO = gaz moléculaire (CO), maser = mégamaser, reverb =
     réverbération (masse dépendante du facteur f), GC = amas globulaire.
     [À vérifier] différence exacte entre « star » et « stars » : la notice
     ReadMe du CDS n'a pas pu être téléchargée (miroirs en erreur) ; le code
     brut est gardé dans la colonne meth_code. Idem pour f_Name = 1 (15
     lignes de table2), gardé brut.
  2. Sagittarius A* : GRAVITY Collaboration 2022, A&A 657, L12 :
     M = 4.297e6 +/- 0.012e6 (stat) +/- 0.040e6 (sys) Msun, R0 = 8.277 kpc ;
     position radio Reid & Brunthaler 2004, ApJ 616, 872 :
     17h45m40.0409s, -29d00m28.118s (J2000).
  3. M87* : Event Horizon Telescope Collaboration 2019, ApJL 875, L1 :
     M = 6.5 +/- 0.7 e9 Msun, D = 16.8 +/- 0.8 Mpc.
  Les lignes van den Bosch de la Voie lactée (6.63) et de M87 (9.58, gaz,
  Walsh et al. 2013) sont gardées avec prefere = 0 ; les valeurs GRAVITY et EHT
  ont prefere = 1. Une seule ligne prefere = 1 par trou noir.

Colonnes : nom, galaxie_hote, ra_deg, dec_deg, dist_mpc, e_dist_mpc, log_masse,
  err_haut_dex, err_bas_dex, limite_sup (1 = limite supérieure), methode,
  meth_code, log_sigma_kms (sigma_e de vdB16), type (smbh / imbh_gc),
  prefere, table, refs_vdb16 (codes de la table refs de VizieR), source.
Tout est MESURÉ (publié) ; rien n'est calculé ici sauf log10 des masses
GRAVITY / EHT et la conversion de leurs erreurs en dex.

Relations publiées pour estimer une masse quand elle n'est pas mesurée (MODÈLE,
à appliquer côté C++ et à afficher comme « estimée ») :
  * M-sigma, Kormendy & Ho 2013, ARA&A 51, 511 (lu dans arXiv:1304.7762) :
      log(M/1e9 Msun) = -(0.510 +/- 0.049) + (4.377 +/- 0.290) log(sigma/200 km/s),
      dispersion intrinsèque 0.29 dex (ellipticas + bulbes classiques) ;
      forme puissance (éq. 7 de l'arXiv) : M/1e9 = 0.309 (sigma/200)^4.38.
      La consigne citait -0.509 + 4.384 : écart minime, sans doute version
      revue vs arXiv [À vérifier sur la version ARA&A].
  * M-sigma, van den Bosch 2016 (éq. 2) : log M = (8.32 +/- 0.04)
      + (5.35 +/- 0.23) log(sigma_e/200), dispersion 0.49 +/- 0.03 dex
      (toutes galaxies, 230 trous noirs).
  * M-M_bulbe, Kormendy & Ho 2013 (éq. 10) : M/1e9 = 0.49 (+0.06/-0.05)
      (M_bulbe/1e11 Msun)^(1.16 +/- 0.08), dispersion 0.29 dex.
  * M-M_* (masse stellaire totale), Reines & Volonteri 2015, ApJ 813, 82 :
      log(M) = 7.45 +/- 0.08 + (1.05 +/- 0.11) log(M_*/1e11 Msun),
      rms 0.55 dex (AGN, toutes morphologies) ;
      elliptiques/bulbes classiques : 8.95 +/- 0.09 + (1.40 +/- 0.21) log(M_*/1e11),
      dispersion intrinsèque 0.47 dex.
Où trouver sigma pour les galaxies du catalogue 2MRS / HyperLEDA (options) :
  * HyperLEDA (Makarov et al. 2014, A&A 570, A13), paramètre « vdis » (log
    dispersion centrale homogénéisée), via l'interface SQL
    http://atlas.obs-hp.fr/hyperleda/fG.cgi (répond 200 au 20/11/2026) ;
    la table VizieR VII/237 (Paturel 2003) ne contient pas vdis.
  * 6dFGS, Campbell et al. 2014, MNRAS 443, 1231, VizieR J/MNRAS/443/1231
    (~11 000 elliptiques du ciel austral, sigma spectroscopique).
  * SDSS (velDisp des spectres) pour le ciel nord jusqu'à z ~ 0.2.
  Sinon : M_* depuis la luminosité K (2MRS) avec un rapport M/L (modèle) puis
  Reines & Volonteri 2015.
"""

import csv
import math
import sys
import urllib.request
from pathlib import Path

SORTIE = Path(r"C:\tmp\vue-sources")
BRUT = SORTIE / "brut" / "vandenbosch2016"
VIZIER = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"
VDB = "van den Bosch 2016, ApJ 831, 134; VizieR J/ApJ/831/134"

METHODES = {"star": "dynamique stellaire", "stars": "dynamique stellaire",
            "gas": "dynamique du gaz", "CO": "dynamique du gaz (CO)",
            "maser": "megamaser", "reverb": "reverberation", "GC": "dynamique stellaire (amas globulaire)"}

# Noms Messier usuels (identités standard NGC <-> Messier)
MESSIER = {"NGC0224": "M31", "NGC0221": "M32", "NGC0598": "M33", "NGC0205": "M110",
           "NGC3031": "M81", "NGC4486": "M87", "NGC4594": "M104", "NGC4258": "M106",
           "NGC4472": "M49", "NGC4374": "M84", "NGC4649": "M60", "NGC5194": "M51",
           "NGC1068": "M77", "NGC5055": "M63", "NGC5457": "M101", "NGC4826": "M64",
           "NGC4736": "M94", "NGC3379": "M105", "NGC3368": "M96", "NGC3351": "M95",
           "NGC3627": "M66", "NGC4303": "M61", "NGC4321": "M100", "NGC4501": "M88",
           "NGC4579": "M58", "NGC4621": "M59", "NGC4552": "M89", "NGC4382": "M85"}
AUTRES = {"NGC5128": "Centaurus A", "MW": "Voie lactee"}

COLONNES = ["nom", "galaxie_hote", "ra_deg", "dec_deg", "dist_mpc", "e_dist_mpc",
            "log_masse", "err_haut_dex", "err_bas_dex", "limite_sup", "methode",
            "meth_code", "log_sigma_kms", "type", "prefere", "table", "refs_vdb16", "source"]


def lire(table: str) -> list:
    chemin = BRUT / f"{table}.tsv"
    if not chemin.exists():
        BRUT.mkdir(parents=True, exist_ok=True)
        url = f"{VIZIER}?-source=J/ApJ/831/134/{table}&-out.max=unlimited&-out.all&-out.add=_RA,_DE"
        with urllib.request.urlopen(url, timeout=300) as r:
            chemin.write_bytes(r.read())
    lignes = [l for l in chemin.read_text(encoding="utf-8").splitlines()
              if l and not l.startswith("#")]
    entete = lignes[0].split("\t")
    return [dict(zip(entete, [c.strip() for c in l.split("\t")])) for l in lignes[3:]]


def joli(nom: str) -> str:
    """'NGC0224' -> 'NGC 224' ; autres noms inchangés."""
    for pre in ("NGC", "UGC", "IC"):
        if nom.startswith(pre) and nom[len(pre):len(pre) + 1].isdigit():
            reste = nom[len(pre):]
            chiffres = reste.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ()").lstrip("0")
            suffixe = reste[len(reste.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ()")):]
            return f"{pre} {chiffres}{suffixe}"
    return nom


def ligne_vdb(r: dict, table: str) -> dict:
    code = r["Name"]
    hote = joli(code)
    if code in MESSIER:
        nom, hote = MESSIER[code] + "*", f"{MESSIER[code]} ({hote})"
    elif code == "MW":
        nom, hote = "Sagittarius A*", "Voie lactee"
    else:
        nom = hote + (f" ({AUTRES[code]})" if code in AUTRES else "")
        hote = nom
    logm = float(r["logBHMass"])
    limite = logm == 0.0
    meth = r["Meth"]
    pref = "0" if code in ("MW", "NGC4486") else "1"
    return {
        "nom": nom, "galaxie_hote": hote, "ra_deg": r["_RA"], "dec_deg": r["_DE"],
        "dist_mpc": r["Dist"], "e_dist_mpc": r.get("e_Dist", ""),
        "log_masse": r["E_logBHMass"] if limite else r["logBHMass"],
        "err_haut_dex": "" if limite else r["E_logBHMass"],
        "err_bas_dex": "" if limite else r["e_logBHMass"],
        "limite_sup": "1" if limite else "0",
        "methode": METHODES.get(meth, meth), "meth_code": meth,
        "log_sigma_kms": r["logsigma"], "type": "imbh_gc" if table == "table4" else "smbh",
        "prefere": pref, "table": f"vdB16/{table}" + (f" f_Name={r['f_Name']}" if r["f_Name"] else ""),
        "refs_vdb16": r["Refs"], "source": VDB,
    }


def lignes_modernes() -> list:
    m_sgr, e_sgr = 4.297e6, math.hypot(0.012e6, 0.040e6)
    m_m87, e_m87 = 6.5e9, 0.7e9
    dex = lambda m, e: f"{math.log10(1 + e / m):.3f}", lambda m, e: f"{-math.log10(1 - e / m):.3f}"
    ra_sgr = 15 * (17 + 45 / 60 + 40.0409 / 3600)
    de_sgr = -(29 + 0 / 60 + 28.118 / 3600)
    return [
        {"nom": "Sagittarius A*", "galaxie_hote": "Voie lactee", "ra_deg": f"{ra_sgr:.6f}",
         "dec_deg": f"{de_sgr:.6f}", "dist_mpc": "0.008277", "e_dist_mpc": "0.000034",
         "log_masse": f"{math.log10(m_sgr):.4f}", "err_haut_dex": dex[0](m_sgr, e_sgr),
         "err_bas_dex": dex[1](m_sgr, e_sgr), "limite_sup": "0",
         "methode": "orbites stellaires (GRAVITY)", "meth_code": "orbits", "log_sigma_kms": "",
         "type": "smbh", "prefere": "1", "table": "", "refs_vdb16": "",
         "source": "GRAVITY Collaboration 2022, A&A 657, L12 (M = 4.297e6, R0 = 8.277 kpc; "
                   "erreur = stat 0.012e6 et sys 0.040e6 combinées) ; position Reid & Brunthaler 2004, ApJ 616, 872"},
        {"nom": "M87*", "galaxie_hote": "M87 (NGC 4486)", "ra_deg": "187.705930",
         "dec_deg": "12.391123", "dist_mpc": "16.8", "e_dist_mpc": "0.8",
         "log_masse": f"{math.log10(m_m87):.4f}", "err_haut_dex": dex[0](m_m87, e_m87),
         "err_bas_dex": dex[1](m_m87, e_m87), "limite_sup": "0",
         "methode": "ombre du trou noir (EHT)", "meth_code": "EHT", "log_sigma_kms": "",
         "type": "smbh", "prefere": "1", "table": "", "refs_vdb16": "",
         "source": "Event Horizon Telescope Collaboration 2019, ApJL 875, L1 (M = 6.5 +/- 0.7 e9) ; "
                   "position = celle de M87 dans vdB16/SIMBAD"},
    ]


def main() -> int:
    lignes = lignes_modernes()
    for t in ("table2", "table3", "table4"):
        rows = lire(t)
        lignes += [ligne_vdb(r, t) for r in rows if r["Name"]]
        print(f"  vdB16 {t} : {len(rows)} lignes")
    lire("refs")  # garde la table des références à côté du brut
    with open(SORTIE / "trous_noirs.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLONNES, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(lignes)
    print(f"trous_noirs.tsv : {len(lignes)} lignes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
