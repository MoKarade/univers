#!/usr/bin/env bash
# Calcul A1 (fusion à 3 M de particules, carte graphique) jusqu'à 10 Ga, sans surveillance : en cas d'arrêt (mémoire de la
# carte prise par un autre programme, redémarrage), repart du dernier instantané après 2 minutes.
# Usage : bash lancer_a1.sh <python du venv CuPy> <dossier de sortie contenant depart.npz>
PY="$1"; OUT="$2"; cd "$(dirname "$0")"
if [ ! -f "$OUT/etat.npz" ]; then "$PY" -u calcul.py 0 10 --gpu --theta=${THETA:-0.5} --sortie="$OUT" $EXTRA && exit 0; fi
for essai in $(seq 1 50); do
  sleep 120
  "$PY" -u calcul.py reprise 10 --gpu --theta=${THETA:-0.5} --sortie="$OUT" $EXTRA && exit 0
  echo "arrêt, nouvel essai $essai"
done
exit 1
