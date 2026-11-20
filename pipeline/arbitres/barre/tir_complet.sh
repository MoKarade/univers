# Un tir complet de la file : attend qu'aucun autre GADGET ne tourne, prépare, lance (8 cœurs, 1,5 Ga), mesure, résume.
# Usage : [CFG=Config_m31.sh] bash tir_complet.sh <nom> <depart.npz> [options de npz_vers_gadget.py]
N=$1; NPZ=$2; shift 2
B=/mnt/c/dev/univers-arbitres/pipeline/arbitres/barre; D=~/arbitres/file/$N
while pgrep -x Gadget4-barre > /dev/null; do sleep 60; done
bash $B/preparer.sh $D $NPZ 1.5 300000 --sous-echantillon=1000000 "$@" > /dev/null 2>&1 || { echo "ÉCHEC préparation $N"; exit 1; }
bash $B/tir.sh $D 1.5 300000 8
grep -q "endrun called" $D/run.log && ! grep -qi "error" $D/run.log || { echo "ÉCHEC tir $N"; grep -i error $D/run.log | head -3; exit 1; }
cd $D && nice -n 15 python3 $B/mesurer.py output mesures.json > mesures.log 2>&1
cp mesures.json $B/mesures_$N.json
echo "== $N"; python3 $B/bilan.py mesures.json
