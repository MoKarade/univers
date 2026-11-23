#!/usr/bin/env bash
# Tire les cinq galaxies de départ avec AGAMA, HORS de GitHub (processeur seul : WSL du PC, ou Colab), à une résolution au
# choix. Mêmes modèles et mêmes options que le jeu galaxies/v25/plein du film 3 ; l'adoucissement suit N^(-1/3) tout seul
# (modeles_v2.py). Écrit <sortie>/plein/<galaxie>.npz, halo tournant compris pour la Voie lactée et Andromède.
# Usage : bash tirer_galaxies.sh <dossier de sortie> [facteur de résolution, 1 = film 3 (9,8 M) ; 2 = 19,6 M ; 5 = 49 M]
# AGAMA est installé au premier passage dans ~/agama-venv (compilation, 10 à 20 min). Relancer reprend là où ça s'est arrêté.
set -eu
SORTIE="${1:?dossier de sortie}"; F="${2:-1}"
ICI="$(cd "$(dirname "$0")" && pwd)"
VENV="${AGAMA_VENV:-$HOME/agama-venv}"
if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" -c "import agama" 2>/dev/null; then
  python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip numpy scipy setuptools wheel
  # En-têtes de Python (Python.h) : absents d'un Ubuntu nu, et sans droits d'administrateur on ne peut pas installer
  # python3-dev. On prend le paquet officiel d'Ubuntu et on le déballe dans le dossier personnel.
  V="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
  if [ ! -f "/usr/include/python$V/Python.h" ]; then
    mkdir -p "$HOME/pydev" && (cd "$HOME/pydev" && apt-get download "libpython$V-dev" > /dev/null && for d in *.deb; do dpkg -x "$d" .; done)
    export CPATH="$HOME/pydev/usr/include/python$V:$HOME/pydev/usr/include:$HOME/pydev/usr/include/x86_64-linux-gnu/python$V:${CPATH:-}"
  fi
  rm -rf /tmp/agama-src && git clone --depth 1 https://github.com/GalacticDynamics-Oxford/Agama.git /tmp/agama-src
  (cd /tmp/agama-src && "$VENV/bin/python" setup.py install --yes > /tmp/agama-install.log 2>&1) || { tail -40 /tmp/agama-install.log; exit 1; }
fi
PY="$VENV/bin/python"
mkdir -p "$SORTIE/brut" "$SORTIE/plein"
n() { "$PY" -c "print(int(round($1 * $F)))"; }
tirer() {      # tirer <nom du fichier> <modèle> <particules à la résolution 1> [options]
  local fichier="$1" modele="$2" base="$3"; shift 3
  if [ ! -f "$SORTIE/brut/$fichier.npz" ]; then
    echo "$(date '+%d/%m %H:%M') tirage de $fichier ($(n "$base") particules)"
    (cd "$ICI" && nice -n 19 "$PY" modeles_v2.py "$modele" "$(n "$base")" "$SORTIE/brut/$fichier.tmp.npz" "$@") && mv "$SORTIE/brut/$fichier.tmp.npz" "$SORTIE/brut/$fichier.npz"
  fi
}
tirer voie_lactee voie_lactee_barre 3500000 --froid-centre=0.9 --agitation=0.88 --halo-coupure=165 --disque-masse=1.06 --disque-hauteur=0.85
tirer andromede andromede_barre 4000000 --froid-centre=0.9 --halo-rho0=5.77e6 --halo-rs=23.5 --halo-coupure=260
tirer triangle triangle 1000000 --halo=0.85
tirer grand_nuage grand_nuage 1000000 --halo=0.85
tirer petit_nuage petit_nuage 300000 --halo=0.6
for g in voie_lactee andromede; do
  [ -f "$SORTIE/plein/$g.npz" ] || "$PY" "$ICI/halo_tournant.py" "$SORTIE/brut/$g.npz" "$SORTIE/plein/$g.npz" 0.35
done
for g in triangle grand_nuage petit_nuage; do [ -f "$SORTIE/plein/$g.npz" ] || cp "$SORTIE/brut/$g.npz" "$SORTIE/plein/$g.npz"; done
echo "$(date '+%d/%m %H:%M') fini : $SORTIE/plein"
