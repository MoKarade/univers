"""Exoplanètes confirmées -> C:\\tmp\\vue-sources\\exoplanetes.tsv

README
------
Source   : NASA Exoplanet Archive, table « Planetary Systems Composite Parameters »
           (pscomppars) : une ligne par planète confirmée, paramètres combinés
           par l'archive (chaque valeur vient d'une publication citée dans
           les colonnes *_reflink de l'archive, non recopiées ici).
Accès    : TAP https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=...&format=csv
Citation : NASA Exoplanet Archive, Planetary Systems Composite Parameters,
           DOI 10.26133/NEA13 (vérifié sur exoplanetarchive.ipac.caltech.edu/docs/doi.html) ;
           article de l'archive : Christiansen et al. 2025, Planetary Science
           Journal, DOI 10.3847/PSJ/ade3c2 (page « acknowledge » de l'archive).
           Mentionner l'archive et la date
           de requête (écrite dans le fichier .meta à côté du .tsv).
Colonnes (unités de l'archive) :
  pl_name, hostname, hd_name, hip_name,
  gaia_dr2_id, gaia_dr3_id   (chaînes « Gaia DR2 <id> » / « Gaia DR3 <id> »),
  ra, dec                    (deg, ICRS J2000),
  sy_dist                    (pc),
  pl_orbsmax                 (au, demi-grand axe),
  pl_orbeccen                (excentricité),
  pl_orbincl                 (deg),
  pl_orbper                  (jours),
  pl_rade                    (rayons terrestres),
  pl_bmasse                  (masses terrestres ; « best mass » = masse,
                              M sin i ou masse issue d'une relation M-R
                              selon pl_bmassprov — ajoutée aussi),
  pl_bmassprov               (provenance de pl_bmasse : Mass / Msini / M-R relationship),
  pl_orblper                 (deg, argument du périastre),
  pl_tranmid                 (jours, BJD, instant de mi-transit),
  discoverymethod, disc_year,
  st_rad                     (rayons solaires), st_teff (K).
Mesuré vs modèle : tout est publié. ATTENTION : dans pscomppars, l'archive
  remplit certains trous par calcul (ex. pl_orbsmax via la 3e loi de Kepler,
  pl_rade ou pl_bmasse via une relation masse-rayon) ; pl_bmassprov dit
  quand la masse vient d'une relation M-R (= modèle). Les valeurs vides
  restent vides (aucun remplissage ici).
"""

import csv
import datetime
import io
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SORTIE = Path(r"C:\tmp\vue-sources")
BRUT = SORTIE / "brut" / "exoplanetes"
TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

COLONNES = [
    "pl_name", "hostname", "hd_name", "hip_name", "gaia_dr2_id", "gaia_dr3_id",
    "ra", "dec", "sy_dist", "pl_orbsmax", "pl_orbeccen", "pl_orbincl",
    "pl_orbper", "pl_rade", "pl_bmasse", "pl_bmassprov", "pl_orblper",
    "pl_tranmid", "discoverymethod", "disc_year", "st_rad", "st_teff",
]


def telecharger() -> str:
    """Interroge le TAP et garde la réponse brute sur disque."""
    requete = f"select {','.join(COLONNES)} from pscomppars order by pl_name"
    url = TAP + "?" + urllib.parse.urlencode({"query": requete, "format": "csv"})
    with urllib.request.urlopen(url, timeout=300) as r:
        texte = r.read().decode("utf-8")
    if texte.lstrip().startswith("<"):
        raise RuntimeError("Réponse TAP en erreur :\n" + texte[:500])
    BRUT.mkdir(parents=True, exist_ok=True)
    (BRUT / "pscomppars.csv").write_text(texte, encoding="utf-8")
    return texte


def main() -> int:
    quand = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lignes = list(csv.DictReader(io.StringIO(telecharger())))
    if not lignes or list(lignes[0].keys()) != COLONNES:
        raise RuntimeError("Colonnes inattendues dans la réponse TAP")
    with open(SORTIE / "exoplanetes.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(COLONNES)
        for ligne in lignes:
            # Valeurs vides gardées vides ; tabulations éventuelles neutralisées
            w.writerow([(ligne[c] or "").replace("\t", " ") for c in COLONNES])
    (SORTIE / "exoplanetes.meta").write_text(
        f"source=NASA Exoplanet Archive pscomppars (TAP {TAP})\n"
        f"requete_utc={quand}\nlignes={len(lignes)}\n", encoding="utf-8")
    print(f"exoplanetes.tsv : {len(lignes)} planètes (requête {quand})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
