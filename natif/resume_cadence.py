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


def saccades(f, seuil_ms=25.0):
    """Images qui accrochent : durée au-dessus du seuil, et les étapes qui pèsent le plus dans chacune."""
    images = defaultdict(dict)
    lignes = csv.reader(open(f, encoding="utf-8"))
    next(lignes)
    for r in lignes:
        images[int(r[0])][(r[1], ",".join(r[2:-3]))] = (float(r[-3]), float(r[-2]))
    longues = [(k, e) for k, e in sorted(images.items()) if e.get(("image", "image"), (0, 0))[0] > seuil_ms and k > 3]
    print(f"\n-- saccades de {os.path.basename(f)} : {len(longues)} images sur {len(images)} au-dessus de {seuil_ms:.0f} ms")
    for k, e in longues[:40]:
        gros = sorted(((v[0], n) for n, v in e.items() if n[0] in ("cpu", "gpu") and n[1] not in ("total", "affichage", "envoi et affichage")), reverse=True)[:3]
        print(f"  image {k:5d}  {e[('image', 'image')][0]:7.1f} ms  à {e[('image', 'image')][1]:9.3g} al  | " + ", ".join(f"{n[0]}:{n[1]} {m:.1f}" for m, n in gros))


if __name__ == "__main__":
    if "--saccades" in sys.argv:
        for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.csv"))):
            saccades(f)
        sys.exit(0)
    main()
