#!/usr/bin/env bash
# Balayage des graines, côté WSL : pour chaque départ prêt (rcj_<g>_genetic_128.npy), lance le calcul complet
# (lancer_graine.sh, ~30 min sur 8 fils mesurées), puis efface le départ copié. Respecte resultats/pause.txt (jeu de Marc).
# Usage : setsid nohup bash balayage_wsl.sh PREMIERE DERNIERE [FILS=8] &
set -uo pipefail
PREMIERE=$1; DERNIERE=$2; FILS=${3:-8}
DEPOT=/mnt/c/dev/univers-contraint/pipeline/contraint
JOURNAL=$HOME/contraint/rc/balayage.log
for g in $(seq "$PREMIERE" "$DERNIERE"); do
  [ -f "$HOME/contraint/rc/rcj$g/bilan.txt" ] && continue
  until [ -f "$DEPOT/resultats/rcj_${g}_genetic_128.npy" ]; do sleep 30; done
  sleep 5                                                     # laisse finir l'écriture
  while [ -f "$DEPOT/resultats/pause.txt" ]; do sleep 60; done
  echo "$(date -Is) début graine $g" >> "$JOURNAL"
  bash "$DEPOT/calcul/lancer_graine.sh" rcj "$g" "$FILS" >> "$JOURNAL" 2>&1
  rm -f "$DEPOT/resultats/rcj_${g}_genetic_128.npy"
  python3 - "$HOME/contraint/rc/rcj$g/bilan.txt" >> "$JOURNAL" <<'EOF'
import json, sys
t = open(sys.argv[1]).read(); b = json.loads(t[t.index('{'):])
p = b['paire']; v = b['vierge']
print(f"  paire: {'non' if not p else f'{p[\"separation_kpc\"]:.0f} kpc, vr {p[\"v_radiale\"]:.0f}, vt {p[\"v_transverse\"]:.0f}, M {p[\"m200\"][0]:.1e}/{p[\"m200\"][1]:.1e}'}"
      f" ; Vierge: {v['masse_bloc_msun']:.1e} M☉ (×{v['surdensite']:.0f}) à {v['ecart_mpc']:.1f} Mpc")
EOF
done
echo "$(date -Is) balayage fini $PREMIERE..$DERNIERE" >> "$JOURNAL"
