# Balayage du zoom en un seul lancement de l'appli (fenêtre cachée) : n vues de d0 à d1 années-lumière autour d'un astre,
# puis, d'une vue à la suivante, le rapport d'éclat moyen de l'image (zone sans interface). Un saut est un rapport qui
# s'écarte de plus d'un facteur 1,4 de la moyenne de ses deux voisins (en logarithme) : une galaxie qui s'éloigne pâlit
# régulièrement (rapports semblables d'un pas à l'autre), ce n'est pas un saut ; une couche qui s'allume d'un coup en est
# un (audit du 20/11/2026 : « les vues changent quand je zoome »).
#
# Usage : python natif/balayage.py <univers.exe> <etoiles.bin> <dossier de sortie> [--cible Soleil] [--de 0.01] [--a 1e11]
#         [--vues 131] [--vue 30,20] [--temps --distance 2e5]
# --temps : au lieu du zoom, 71 dates de -1 Ga à +10 Ga (pas de 10^0,25 de chaque côté d'aujourd'hui), caméra à --distance
#           de l'astre (UNIVERS_BALAYAGE_DATES) : cherche les sauts dans le passé et l'avenir.
# Rend 1 s'il reste un saut, 0 sinon. Une seule appli à la fois sur la carte graphique (3 à 4 Go, 2 min environ).
import argparse
import os
import subprocess
import sys

import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("etoiles")
    ap.add_argument("sortie")
    ap.add_argument("--cible", default="Soleil")
    ap.add_argument("--de", type=float, default=0.01)
    ap.add_argument("--a", type=float, default=1e11)
    ap.add_argument("--vues", type=int, default=131)
    ap.add_argument("--vue", default="30,20")
    ap.add_argument("--images", type=int, default=12)
    ap.add_argument("--temps", action="store_true")
    ap.add_argument("--distance", default="2e5")
    o = ap.parse_args()
    os.makedirs(o.sortie, exist_ok=True)
    dossier = os.path.abspath(o.sortie).replace(os.sep, '/')
    dates = [-10 ** e for e in np.arange(9, 0.9, -0.25)] + [27.0] + [10 ** e for e in np.arange(1, 10.01, 0.25)]
    if o.temps:
        o.vues = len(dates)
        env = dict(os.environ, UNIVERS_PANNEAU="ferme", UNIVERS_BALAYAGE_DATES=dossier + "|" + ",".join(f"{y:.6g}" for y in dates))
    else:
        env = dict(os.environ, UNIVERS_PANNEAU="ferme", UNIVERS_BALAYAGE=f"{o.de}:{o.a}:{o.vues}:{dossier}")
    # Windows lit les arguments dans la page de code ANSI : un nom accentué est passé en octets UTF-8 (lus tels quels par l'appli)
    cible = o.cible.encode("utf-8").decode("cp1252") if os.name == "nt" else o.cible
    extra = ["--distance", o.distance] if o.temps else []
    r = subprocess.run([o.exe, o.etoiles, "--fenetre-test", str(o.images), "--cible", cible, "--vue", o.vue] + extra,
                       env=env, capture_output=True, text=True, errors="replace")
    open(os.path.join(o.sortie, "journal.txt"), "w", encoding="utf-8").write(r.stdout + r.stderr)
    moy = []
    for k in range(o.vues):
        p = os.path.join(o.sortie, f"b_{k:03d}.ppm")
        if not os.path.exists(p):
            print(f"ECHEC : vue {k} absente (voir journal.txt)")
            return 1
        a = np.asarray(Image.open(p).convert("L")).astype(float)
        h, w = a.shape
        moy.append(a[int(0.18 * h):int(0.78 * h), int(0.19 * w):int(0.81 * w)].mean())
    lr = [0.0] + [float(np.log(max(moy[k], 0.5) / max(moy[k - 1], 0.5))) for k in range(1, o.vues)]
    sauts = 0
    for k in range(1, o.vues):
        d = dates[k] if o.temps else o.de * (o.a / o.de) ** (k / (o.vues - 1))
        voisins = [lr[j] for j in (k - 1, k + 1) if 1 <= j < o.vues]
        ecart = lr[k] - sum(voisins) / len(voisins)
        if abs(ecart) > np.log(1.4):
            sauts += 1
            print(f"saut  vue {k:3d}  {d:9.3g} {'ans' if o.temps else 'al'}  éclat {moy[k - 1]:6.1f} -> {moy[k]:6.1f}  (x{np.exp(lr[k]):.2f}, voisins x{np.exp(sum(voisins) / len(voisins)):.2f})")
    print(f"{sauts} saut(s) sur {o.vues - 1} pas")
    print("PASSE" if sauts == 0 else "ECHEC")
    return 1 if sauts else 0


if __name__ == "__main__":
    sys.exit(main())
