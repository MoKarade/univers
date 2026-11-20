# Tir bloquant (à lancer en tâche de fond depuis Windows) : régénère param.txt puis lance GADGET-4.
# Usage : bash tir.sh <dossier> <durée Ga> <limite CPU s> [np=8] [reprise=0|1]
D=$1; DUREE=$2; TLIM=$3; NP=${4:-8}; REPRISE=${5:-0}
B=/mnt/c/dev/univers-arbitres/pipeline/arbitres/barre
cd $D || exit 1
TMAX=$(python3 -c "print(round($DUREE/0.9778, 6))")
sed -i "s|^TimeLimitCPU .*|TimeLimitCPU              $TLIM|; s|^TimeMax	.*|TimeMax	            $TMAX|" param.txt      # param.txt vient de preparer.sh (adoucissements du départ)
if [ "$REPRISE" = 1 ]; then nice -n 10 mpirun -np $NP ./Gadget4-barre param.txt 1 >> run.log 2>&1
else rm -rf output; mkdir -p output; nice -n 10 mpirun -np $NP ./Gadget4-barre param.txt > run.log 2>&1; fi
echo "fin rc=$?"
