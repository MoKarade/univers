#!/usr/bin/env bash
# Lance un calcul contraint complet pour une graine, sous WSL : genetIC (départ zoom) puis GADGET-4 (z=99 -> 0).
# Usage : bash lancer_graine.sh PREFIXE GRAINE [FILS=8] [CENTRE="324.30 309.60 326.65"]
#   PREFIXE : rc (vitesses CF4) ou rcj (vitesses CF4 + densité 2MRS) ; le fichier
#   pipeline/contraint/resultats/<PREFIXE>_<GRAINE>_genetic_128.npy doit exister (exporter_genetic.py).
# Durée mesurée : 30 min sur 8 fils (graine rc 1, 19/11/2026).
set -euo pipefail
PREFIXE=$1; GRAINE=$2; FILS=${3:-8}; CENTRE=${4:-"324.30 309.60 326.65"}
DEPOT=/mnt/c/dev/univers-contraint/pipeline/contraint
TRAVAIL=$HOME/contraint/rc
NOM=${PREFIXE}${GRAINE}
mkdir -p "$TRAVAIL/$NOM" && cd "$TRAVAIL/$NOM"
cp "$DEPOT/resultats/${PREFIXE}_${GRAINE}_genetic_128.npy" champ.npy
# graine des petites échelles (non contraintes) des niveaux de zoom : déduite de la graine
sed -e "s|^outname .*|outname ${NOM}|" \
    -e "s|^random_seed_real_space .*|random_seed_real_space $((1000 + GRAINE))|" \
    -e "s|^import_level 0 .*|import_level 0 champ.npy|" \
    -e "s|^camb .*|camb $TRAVAIL/transfert_planck18_eh.dat|" \
    -e "s|^centre .*|centre ${CENTRE}|" \
    "$DEPOT/calcul/genetic_rc1_zoom.txt" | tr -d '\r' > genetic.txt
# Modifications genetIC facultatives (ajustement du Groupe local) : lignes insérées avant « done »
if [ -n "${MODS:-}" ] && [ -f "$MODS" ]; then
  python3 - "$MODS" <<'EOF'
import sys
mods = open(sys.argv[1]).read().replace('\r', '').strip() + '\n'
s = open('genetic.txt').read().replace('\ndone', '\n' + mods + 'done', 1)
open('genetic.txt', 'w').write(s)
EOF
fi
"$HOME/contraint/genetIC/genetIC/genetIC" genetic.txt > genetic.log 2>&1
tr -d '\r' < "$DEPOT/calcul/gadget_param_rc1.txt" \
  | sed -e "s|^InitCondFile .*|InitCondFile ./${NOM}.gadget3|" -e "s|^OutputDir .*|OutputDir ./sortie|" \
        -e "s|^OutputListFilename .*|OutputListFilename ./sorties.txt|" > gadget.txt
tr -d '\r' < "$DEPOT/calcul/gadget_sorties.txt" > sorties.txt
mkdir -p sortie
date +%s > debut.txt
mpirun -np "$FILS" "$TRAVAIL/gadget/Gadget4-zoom" gadget.txt > gadget.log 2>&1
date +%s > fin.txt
python3 "$DEPOT/analyser_paire.py" sortie/fof_subhalo_tab_005.hdf5 > bilan.txt 2>&1 || true
rm -f sortie/snap_00[0-3].hdf5 sortie/restartfiles/* 2>/dev/null || true   # on garde aujourd'hui et a=0,91
echo "fini ${NOM} en $(( $(cat fin.txt) - $(cat debut.txt) )) s"
