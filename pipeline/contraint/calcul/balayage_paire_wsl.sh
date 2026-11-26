#!/usr/bin/env bash
# Réglage de la paire (modifications genetIC de l'essai v17) sur d'autres graines, pour mesurer la dispersion de la marée
# entre réalisations indépendantes (demande du grand calcul, 20/11/2026). Départs fabriqués côté Windows avec le préfixe rcp.
# Usage : setsid nohup bash balayage_paire_wsl.sh PREMIERE DERNIERE [FILS=8] &
set -uo pipefail
PREMIERE=$1; DERNIERE=$2; FILS=${3:-8}
DEPOT=/mnt/c/dev/univers-contraint/pipeline/contraint
JOURNAL=$HOME/contraint/rc/balayage_paire.log
for g in $(seq "$PREMIERE" "$DERNIERE"); do
  [ -f "$HOME/contraint/rc/rcp$g/bilan.txt" ] && continue
  until [ -f "$DEPOT/resultats/rcp_${g}_genetic_128.npy" ]; do sleep 30; done
  sleep 5
  while [ -f "$DEPOT/resultats/pause.txt" ]; do sleep 60; done
  echo "$(date -Is) début graine $g" >> "$JOURNAL"
  MODS=$DEPOT/calcul/mods_paire_v17.txt bash "$DEPOT/calcul/lancer_graine.sh" rcp "$g" "$FILS" >> "$JOURNAL" 2>&1
  rm -f "$DEPOT/resultats/rcp_${g}_genetic_128.npy"
done
echo "$(date -Is) fini $PREMIERE..$DERNIERE" >> "$JOURNAL"
