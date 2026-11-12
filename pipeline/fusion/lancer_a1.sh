#!/usr/bin/env bash
# Calcul de particules sur la carte graphique (fusion ou Voie lactée seule) jusqu'à FIN Ga, sans surveillance : en cas
# d'arrêt (mémoire de la carte prise par un autre programme, redémarrage), repart du dernier instantané après 2 minutes,
# ou du départ s'il n'y en a pas encore. Un seul lanceur par dossier (verrou lanceur.pid).
# Usage : [FIN=10] [THETA=0.5] [EXTRA="--toutes ..."] bash lancer_a1.sh <python du venv CuPy> <dossier contenant depart.npz>
PY="$1"; OUT="$2"; cd "$(dirname "$0")"
VERROU="$OUT/lanceur.pid"
if [ -f "$VERROU" ] && kill -0 "$(cat "$VERROU")" 2>/dev/null; then echo "un lanceur tourne déjà ($(cat "$VERROU"))"; exit 1; fi
echo $$ > "$VERROU"
for essai in $(seq 1 50); do
  if [ -f "$OUT/etat.npz" ]; then
    "$PY" -u calcul.py reprise ${FIN:-10} --gpu --theta=${THETA:-0.5} --sortie="$OUT" $EXTRA && { rm -f "$VERROU"; exit 0; }
  else
    "$PY" -u calcul.py 0 ${FIN:-10} --gpu --theta=${THETA:-0.5} --sortie="$OUT" $EXTRA && { rm -f "$VERROU"; exit 0; }
  fi
  echo "arrêt, nouvel essai $essai dans 2 minutes"
  sleep 120
done
rm -f "$VERROU"; exit 1
