#!/usr/bin/env bash
# Mesure de la cadence (20/11/2026) : temps par image et par étape, à toutes les échelles (balayage du zoom de 10 µal à
# 10 Gal autour du Soleil) et à plusieurs dates. Fenêtre cachée, taille par défaut de la fenêtre agrandie de Marc.
# Une seule appli à la fois sur la carte. Écrit <sortie>/<date>.csv (une ligne par étape et par image, chrono.h) et
# <sortie>/<date>.log ; puis python natif/resume_cadence.py <sortie> fait le tableau.
#
# Usage : bash natif/mesure_cadence.sh <univers.exe> <sortie> [dates...]
#   dates : années depuis J2000 (« maintenant » pour aujourd'hui). Défaut : maintenant 1e6 1e8 4e9.
set -u
EXE=$1; OUT=$2; shift 2
DATES=("$@"); [ ${#DATES[@]} -eq 0 ] && DATES=(maintenant 1000027 100000027 4000000027)
D=/c/dev/Univers-PC
mkdir -p "$OUT"
for d in "${DATES[@]}"; do
  args=()
  [ "$d" != maintenant ] && args=(--date "$d")
  mkdir -p "$OUT/vues_$d"; t0=$SECONDS
  UNIVERS_CHRONO="$OUT/$d.csv" UNIVERS_PANNEAU=ferme UNIVERS_BALAYAGE="1e-5:1e10:16:$(cygpath -m "$OUT")/vues_$d" \
    "$EXE" "$D/etoiles.bin" --fenetre-test 40 --cible Soleil --vue 30,20 "${args[@]}" > "$OUT/$d.log" 2>&1
  echo "date $d : code $? en $((SECONDS - t0)) s"
done
