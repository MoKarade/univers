# Tableau de la cadence mesurée par natif/mesure_cadence.sh : pour chaque date et chaque échelle regardée, durée médiane
# d'une image et des étapes qui pèsent (plus de 0,5 ms en médiane), sur la carte et sur le processeur.
# Usage : python natif/resume_cadence.py <dossier> [--seuil 0.5]
import csv
import glob
import os
import statistics
import sys
from collections import defaultdict


def main():
    dossier = sys.argv[1]
    seuil = float(sys.argv[sys.argv.index("--seuil") + 1]) if "--seuil" in sys.argv else 0.5
    for f in sorted(glob.glob(os.path.join(dossier, "*.csv"))):
        par = defaultdict(lambda: defaultdict(list))      # distance -> étape -> durées
        lignes = csv.reader(open(f, encoding="utf-8"))
        next(lignes)
        for r in lignes:      # image, genre, étape (entre guillemets), ms, distance, année
            par[float(r[-2])][(r[1], ",".join(r[2:-3]))].append(float(r[-3]))
        print(f"\n== {os.path.basename(f)[:-4]}")
        for d in sorted(par):
            e = par[d]
            img = e.get(("image", "image"), [0])
            img = img[5:] or img      # les premières images d'une vue rattrapent le changement de distance
            med = statistics.median(img)
            pire = sorted(img)[int(0.95 * (len(img) - 1))]
            gros = sorted(((statistics.median(v[5:] or v), k) for k, v in e.items() if k[0] in ("cpu", "gpu") and k[1] != "total"), reverse=True)
            detail = ", ".join(f"{k[0]}:{k[1]} {m:.1f}" for m, k in gros if m >= seuil)
            gt = statistics.median(e.get(("gpu", "total"), [0]))
            print(f"{d:10.3g} al  image {med:6.1f} ms (95 % : {pire:6.1f})  {1000 / med:5.0f} im/s  carte {gt:5.1f}  | {detail}")


if __name__ == "__main__":
    main()
