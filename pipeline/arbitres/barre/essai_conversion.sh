# Essai rapide de la conversion (sans tir) dans un dossier temporaire d'Ubuntu. Usage : bash essai_conversion.sh <depart.npz> [options]
B=/mnt/c/dev/univers-arbitres/pipeline/arbitres/barre; NPZ=$1; shift
D=$(mktemp -d) && cd $D && python3 $B/npz_vers_gadget.py $NPZ depart.hdf5 --sous-echantillon=1000000 "$@" && cat adoucissements.txt && python3 $B/info_depart.py depart.hdf5
